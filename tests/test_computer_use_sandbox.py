from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from app.computer_use_sandbox import ComputerUseSandboxError, VercelSandboxRuntime


class FakePolicy:
    @staticmethod
    def custom(*, allow):
        return {"mode": "custom", "allow": allow}

    @staticmethod
    def deny_all():
        return {"mode": "deny-all"}


class FakeFilesystem:
    def __init__(self):
        self.directories = []
        self.files = {}

    def mkdir(self, path, recursive=True):
        self.directories.append(path)

    def write_text(self, path, content, **kwargs):
        self.files[path] = content


class FakeBox:
    def __init__(self, health_status="ready"):
        self.fs = FakeFilesystem()
        self.routes = [SimpleNamespace(port=8765, url="https://sandbox.example.test")]
        self.health_status = health_status
        self.processes = []
        self.policies = []
        self.network_policy = None

    def run_process(self, command, args, **kwargs):
        self.processes.append((command, args, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def update_network_policy(self, policy):
        self.policies.append(policy)
        self.network_policy = SimpleNamespace(
            mode=policy["mode"],
            allowed_domains=tuple(policy.get("allow", {}).keys()),
        )


class FakeSandboxContext:
    def __init__(self, box):
        self.box = box
        self.closed = False

    def __enter__(self):
        return self.box

    def __exit__(self, exc_type, exc, tb):
        self.closed = True


class FakeSandboxAPI:
    def __init__(self, box):
        self.box = box
        self.options = None
        self.context = FakeSandboxContext(box)

    def create_sandbox(self, **kwargs):
        self.options = kwargs
        return self.context


class FakeResponse:
    status_code = 200

    def __init__(self, status="ready", policy=True):
        self.payload = {"status": status, "network_policy_enforced": policy}

    def json(self):
        return self.payload


class FakeHTTPClient:
    def __init__(self, response):
        self.response = response

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url):
        return self.response


def test_sandbox_runtime_uploads_files_narrows_egress_and_starts_runtime(tmp_path):
    runtime_root = tmp_path / "runtime"
    package = runtime_root / "computer_use_runtime"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("from .service import create_app\n")
    (package / "service.py").write_text("runtime = True\n")
    (package / "playwright_executor.py").write_text("class PlaywrightExecutor: pass\n")
    (package / "server.py").write_text("app = None\n")
    (runtime_root / "requirements.txt").write_text("fastapi\n")

    box = FakeBox()
    api = FakeSandboxAPI(box)
    manager = VercelSandboxRuntime(
        settings_obj=SimpleNamespace(
            computer_use_sandbox_region="fra1",
            computer_use_sandbox_timeout_seconds=600,
        ),
        sandbox_api=api,
        network_policy_factory=FakePolicy,
        http_client_factory=lambda **kwargs: FakeHTTPClient(FakeResponse()),
        runtime_root=runtime_root,
        sleep=lambda _: None,
    )

    with manager.open(["https://example.com"]) as connection:
        assert connection.url == "https://sandbox.example.test/execute"
        assert connection.token
        assert connection.url.startswith("https://")
        assert box.policies[-1] == {"mode": "custom", "allow": {"example.com": ()}}

    assert api.context.closed is True
    assert api.options["persistent"] is False
    assert api.options["image"] == VercelSandboxRuntime.IMAGE
    assert api.options["ports"] == [8765]
    assert api.options["region"] == "fra1"
    assert any(path.endswith("computer_use_runtime/service.py") for path in box.fs.files)
    assert any(command == "uv" for command, _, _ in box.processes)
    assert any(command == "python" and "install" in args for command, args, _ in box.processes)


def test_sandbox_runtime_fails_closed_when_network_policy_is_not_attested(tmp_path):
    runtime_root = tmp_path / "runtime"
    package = runtime_root / "computer_use_runtime"
    package.mkdir(parents=True)
    for name in ("__init__.py", "service.py", "playwright_executor.py", "server.py"):
        (package / name).write_text("")
    (runtime_root / "requirements.txt").write_text("fastapi\n")

    box = FakeBox()
    api = FakeSandboxAPI(box)
    manager = VercelSandboxRuntime(
        settings_obj=SimpleNamespace(
            computer_use_sandbox_region="fra1",
            computer_use_sandbox_timeout_seconds=600,
        ),
        sandbox_api=api,
        network_policy_factory=FakePolicy,
        http_client_factory=lambda **kwargs: FakeHTTPClient(FakeResponse(status="blocked", policy=False)),
        runtime_root=runtime_root,
        sleep=lambda _: None,
    )

    with pytest.raises(ComputerUseSandboxError, match="policy"):
        with manager.open(["https://example.com"]):
            pytest.fail("Runtime must not be yielded without policy attestation")

    assert api.context.closed is True


def test_sandbox_runtime_uses_deny_all_for_local_only_origins(tmp_path):
    runtime_root = tmp_path / "runtime"
    package = runtime_root / "computer_use_runtime"
    package.mkdir(parents=True)
    for name in ("__init__.py", "service.py", "playwright_executor.py", "server.py"):
        (package / name).write_text("")
    (runtime_root / "requirements.txt").write_text("fastapi\n")

    box = FakeBox()
    api = FakeSandboxAPI(box)
    manager = VercelSandboxRuntime(
        settings_obj=SimpleNamespace(
            computer_use_sandbox_region="fra1",
            computer_use_sandbox_timeout_seconds=600,
        ),
        sandbox_api=api,
        network_policy_factory=FakePolicy,
        http_client_factory=lambda **kwargs: FakeHTTPClient(FakeResponse()),
        runtime_root=runtime_root,
        sleep=lambda _: None,
    )

    with manager.open(["http://127.0.0.1:8000"]):
        pass

    assert box.policies[-1] == {"mode": "deny-all"}


def test_official_vercel_sandbox_sdk_import_contract():
    from vercel.api import session
    from vercel.sandbox import NetworkPolicy
    from vercel.sandbox import sync as vercel_sandbox

    assert callable(session)
    assert callable(vercel_sandbox.create_sandbox)
    assert NetworkPolicy.custom(allow={"example.com": ()}).mode == "custom"
    assert NetworkPolicy.deny_all().mode == "deny-all"
