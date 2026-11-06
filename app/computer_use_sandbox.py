from __future__ import annotations

import posixpath
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from secrets import token_urlsafe
from time import sleep
from typing import Any, Iterator
from urllib.parse import urlsplit


class ComputerUseSandboxError(RuntimeError):
    """Raised when an isolated Computer Use sandbox cannot be prepared safely."""


@dataclass(frozen=True)
class SandboxConnection:
    """Trusted connection details for one disposable runtime."""

    url: str
    token: str
    allowed_origins: tuple[str, ...]
    port: int


def _normalize_origin(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ComputerUseSandboxError("An allowed origin must be a non-empty URL.")
    try:
        parsed = urlsplit(value.strip())
        port = parsed.port
    except ValueError as exc:
        raise ComputerUseSandboxError("An allowed origin contains an invalid port.") from exc

    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme not in {"http", "https"}
        or not host
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ComputerUseSandboxError("Allowed origins must be exact HTTP(S) origins.")
    if parsed.scheme == "http" and host not in {"localhost", "127.0.0.1", "::1"}:
        raise ComputerUseSandboxError("Non-local allowed origins must use HTTPS.")

    default_port = 443 if parsed.scheme == "https" else 80
    suffix = f":{port}" if port and port != default_port else ""
    return f"{parsed.scheme}://{host}{suffix}"


class VercelSandboxRuntime:
    """Launch a disposable Vercel Sandbox and attest its restricted egress.

    Runtime dependencies are installed before egress is narrowed. The runtime
    bearer token and policy attestation are injected only after the policy
    update succeeds. Exiting the open context destroys the disposable sandbox.
    """

    PORT = 8765
    REMOTE_ROOT = "/vercel/sandbox/marsel-computer-use"

    def __init__(
        self,
        *,
        settings_obj: Any = None,
        sandbox_api: Any = None,
        network_policy_factory: Any = None,
        http_client_factory: Any = None,
        runtime_root: str | Path | None = None,
        sleep: Any = sleep,
        session_factory: Any = None,
    ) -> None:
        if settings_obj is None:
            from .config import settings

            settings_obj = settings
        self.settings = settings_obj
        self.runtime_root = (
            Path(runtime_root)
            if runtime_root is not None
            else Path(__file__).resolve().parents[1] / "runtime"
        )
        self.sleep = sleep

        if sandbox_api is None:
            try:
                from vercel.api import session as vercel_session
                from vercel.sandbox import NetworkPolicy
                from vercel.sandbox import sync as vercel_sandbox
            except ImportError as exc:
                raise ComputerUseSandboxError(
                    "The Vercel Sandbox Python SDK is not installed."
                ) from exc
            sandbox_api = vercel_sandbox
            network_policy_factory = network_policy_factory or NetworkPolicy
            session_factory = session_factory or vercel_session
        else:
            # Injected clients are used by isolated unit tests.
            session_factory = session_factory or nullcontext

        if network_policy_factory is None:
            raise ComputerUseSandboxError("A Vercel network policy factory is required.")

        if http_client_factory is None:
            try:
                import httpx
            except ImportError as exc:
                raise ComputerUseSandboxError("httpx is required for runtime health checks.") from exc
            http_client_factory = httpx.Client

        self.sandbox_api = sandbox_api
        self.network_policy_factory = network_policy_factory
        self.http_client_factory = http_client_factory
        self.session_factory = session_factory

    @staticmethod
    def _normalize_origins(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        if not isinstance(values, (list, tuple)) or not values:
            raise ComputerUseSandboxError("Computer Use requires a non-empty origin allowlist.")
        normalized: list[str] = []
        for value in values:
            origin = _normalize_origin(value)
            if origin not in normalized:
                normalized.append(origin)
        return tuple(normalized)

    def _network_policy(self, origins: tuple[str, ...]) -> tuple[Any, str, frozenset[str]]:
        hosts = frozenset(
            parsed.hostname
            for origin in origins
            if (parsed := urlsplit(origin)).hostname
            and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        )
        if not hosts:
            return self.network_policy_factory.deny_all(), "deny-all", hosts
        policy = self.network_policy_factory.custom(allow={host: () for host in sorted(hosts)})
        return policy, "custom", hosts

    def _upload_runtime(self, box: Any) -> None:
        package_dir = self.runtime_root / "computer_use_runtime"
        requirements = self.runtime_root / "requirements.txt"
        if not package_dir.is_dir() or not requirements.is_file():
            raise ComputerUseSandboxError("The isolated runtime package or requirements file is missing.")

        box.fs.mkdir(self.REMOTE_ROOT, recursive=True)
        for source in sorted(self.runtime_root.rglob("*")):
            if source.is_symlink() or "__pycache__" in source.parts or source.suffix == ".pyc":
                continue
            relative = source.relative_to(self.runtime_root).as_posix()
            destination = posixpath.join(self.REMOTE_ROOT, relative)
            if source.is_dir():
                box.fs.mkdir(destination, recursive=True)
            elif source.is_file():
                box.fs.write_text(destination, source.read_text(encoding="utf-8"))

    @staticmethod
    def _run_checked(box: Any, command: str, args: list[str], **kwargs: Any) -> Any:
        result = box.run_process(command, args, capture_output=True, **kwargs)
        if getattr(result, "returncode", 1) != 0:
            stderr = getattr(result, "stderr", "") or ""
            raise ComputerUseSandboxError(
                f"Sandbox command failed ({command}): {str(stderr)[-1200:]}"
            )
        return result

    def _install_runtime(self, box: Any) -> None:
        self._run_checked(box, "uv", ["--version"])
        requirements_path = posixpath.join(self.REMOTE_ROOT, "requirements.txt")
        self._run_checked(
            box,
            "python",
            [
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                "-r",
                requirements_path,
            ],
        )
        # Install Chromium and its OS libraries while setup egress is still open.
        self._run_checked(
            box,
            "python",
            ["-m", "playwright", "install", "--with-deps", "chromium"],
            sudo=True,
        )

    def _apply_network_policy(
        self,
        box: Any,
        policy: Any,
        expected_mode: str,
        expected_hosts: frozenset[str],
    ) -> None:
        # Current SDK update() persists the policy and applies it to the active
        # session. The deprecated helper remains a compatibility fallback.
        updater = getattr(box, "update", None)
        if callable(updater):
            updater(network_policy=policy)
        else:
            box.update_network_policy(policy)

        readback = getattr(box, "network_policy", None)
        if readback is not None:
            if getattr(readback, "mode", None) != expected_mode:
                raise ComputerUseSandboxError("Vercel did not confirm the requested network policy.")
            actual_hosts = frozenset(getattr(readback, "allowed_domains", ()) or ())
            if actual_hosts != expected_hosts:
                raise ComputerUseSandboxError("Vercel network-policy readback does not match the origin allowlist.")

    def _start_runtime(self, box: Any, token: str, origins: tuple[str, ...]) -> None:
        environment = {
            "COMPUTER_USE_RUNTIME_TOKEN": token,
            "COMPUTER_USE_ALLOWED_ORIGINS": ",".join(origins),
            # Set only after the Vercel API accepts the restrictive policy.
            "COMPUTER_USE_NETWORK_POLICY_ENFORCED": "true",
            "PYTHONUNBUFFERED": "1",
        }
        command = (
            "nohup python -m uvicorn computer_use_runtime.server:app "
            f"--host 0.0.0.0 --port {self.PORT} "
            ">/tmp/marsel-computer-use-runtime.log 2>&1 </dev/null &"
        )
        self._run_checked(
            box,
            "bash",
            ["-lc", command],
            cwd=self.REMOTE_ROOT,
            env=environment,
        )

    def _wait_for_health(self, route_url: str) -> None:
        health_url = route_url.rstrip("/") + "/health"
        last_error: Exception | None = None
        attempts = 30
        for attempt in range(attempts):
            try:
                with self.http_client_factory(timeout=3.0, trust_env=False) as client:
                    response = client.get(health_url)
                payload = response.json()
                if (
                    getattr(response, "status_code", 0) == 200
                    and isinstance(payload, dict)
                    and payload.get("network_policy_enforced") is not True
                ):
                    raise ComputerUseSandboxError(
                        "Runtime health check failed: network policy is not enforced."
                    )
                if (
                    getattr(response, "status_code", 0) == 200
                    and isinstance(payload, dict)
                    and payload.get("status") == "ready"
                ):
                    return
                last_error = ComputerUseSandboxError("Runtime health endpoint is not ready.")
            except ComputerUseSandboxError:
                raise
            except Exception as exc:
                last_error = exc
            if attempt < attempts - 1:
                self.sleep(0.25)

        raise ComputerUseSandboxError("The isolated runtime failed its health check.") from last_error

    @contextmanager
    def open(self, allowed_origins: list[str] | tuple[str, ...]) -> Iterator[SandboxConnection]:
        origins = self._normalize_origins(allowed_origins)
        policy, expected_mode, expected_hosts = self._network_policy(origins)
        region = getattr(self.settings, "computer_use_sandbox_region", "fra1")
        timeout = int(getattr(self.settings, "computer_use_sandbox_timeout_seconds", 600))
        if timeout < 60:
            raise ComputerUseSandboxError("Sandbox timeout must be at least 60 seconds.")

        # Context exit stops and destroys the disposable microVM.
        with self.session_factory():
            with self.sandbox_api.create_sandbox(
                ports=[self.PORT],
                region=region,
                execution_time_limit=timeout,
                persistent=False,
                destroy=True,
            ) as box:
                self._upload_runtime(box)
                self._install_runtime(box)
                self._apply_network_policy(box, policy, expected_mode, expected_hosts)

                token = token_urlsafe(32)
                self._start_runtime(box, token, origins)

                route = next(
                    (item for item in box.routes if getattr(item, "port", None) == self.PORT),
                    None,
                )
                route_url = getattr(route, "url", "") if route is not None else ""
                if not isinstance(route_url, str) or not route_url.startswith("https://"):
                    raise ComputerUseSandboxError("Vercel did not return a secure runtime URL.")

                self._wait_for_health(route_url)
                yield SandboxConnection(
                    url=route_url.rstrip("/") + "/execute",
                    token=token,
                    allowed_origins=origins,
                    port=self.PORT,
                )
