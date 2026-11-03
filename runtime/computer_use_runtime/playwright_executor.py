from __future__ import annotations

import ast
import asyncio
import base64
import inspect
import io
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit


class RuntimeExecutionError(RuntimeError):
    pass


def _origin_for_url(value: str) -> str | None:
    parsed = urlsplit(value)
    if parsed.scheme in {"data", "blob", "about"}:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return "BLOCKED"
    try:
        port = parsed.port
    except ValueError:
        return "BLOCKED"
    default_port = 443 if parsed.scheme == "https" else 80
    suffix = f":{port}" if port and port != default_port else ""
    return f"{parsed.scheme}://{parsed.hostname.lower()}{suffix}"


@dataclass
class BrowserSession:
    playwright: Any
    browser: Any
    context: Any
    page: Any
    allowed_origins: frozenset[str]
    namespace: dict[str, Any]
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    created_at: float = field(default_factory=time.monotonic)


class PlaywrightExecutor:
    """Persistent Playwright sessions inside one disposable Vercel microVM.

    This executor is not a host-level sandbox by itself. Its security boundary
    is the Vercel Sandbox microVM and its enforced network policy. Never pass
    application credentials, RO App keys, or Vercel credentials into that VM.
    """

    def __init__(self, *, max_sessions: int = 1, execution_timeout_seconds: float = 30, max_text_chars: int = 20_000, max_images: int = 4, max_image_bytes: int = 8_000_000) -> None:
        self.max_sessions = max_sessions
        self.execution_timeout_seconds = execution_timeout_seconds
        self.max_text_chars = max_text_chars
        self.max_images = max_images
        self.max_image_bytes = max_image_bytes
        self._sessions: dict[str, BrowserSession] = {}
        self._lock = asyncio.Lock()

    async def _new_session(self, session_id: str, allowed_origins: list[str]) -> BrowserSession:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeExecutionError("Playwright is not installed in the sandbox.") from exc
        playwright = await async_playwright().start()
        browser = None
        try:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(service_workers="block")
            page = await context.new_page()
            allowed = frozenset(allowed_origins)

            async def guard_request(route: Any) -> None:
                origin = _origin_for_url(route.request.url)
                if origin is None or origin in allowed:
                    await route.continue_()
                else:
                    await route.abort("blockedbyclient")

            await page.route("**/*", guard_request)
            namespace: dict[str, Any] = {"__builtins__": __builtins__, "page": page, "context": context, "browser": browser}
            return BrowserSession(playwright, browser, context, page, allowed, namespace)
        except Exception:
            if browser is not None:
                await browser.close()
            await playwright.stop()
            raise

    async def _get_session(self, session_id: str, allowed_origins: list[str]) -> BrowserSession:
        async with self._lock:
            existing = self._sessions.get(session_id)
            if existing is not None:
                if existing.allowed_origins != frozenset(allowed_origins):
                    raise RuntimeExecutionError("A session cannot expand or change its origin allowlist.")
                return existing
            if len(self._sessions) >= self.max_sessions:
                raise RuntimeExecutionError("The sandbox session limit has been reached.")
            session = await self._new_session(session_id, allowed_origins)
            self._sessions[session_id] = session
            return session

    def _encode_image(self, value: Any) -> str:
        if isinstance(value, (bytes, bytearray)):
            image_bytes = bytes(value)
        elif hasattr(value, "save"):
            stream = io.BytesIO()
            value.save(stream, format="PNG")
            image_bytes = stream.getvalue()
        else:
            raise RuntimeExecutionError("display() accepts screenshot bytes or a PIL image.")
        if not image_bytes or len(image_bytes) > self.max_image_bytes:
            raise RuntimeExecutionError("Screenshot is empty or exceeds the image size limit.")
        return "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii")

    async def execute(self, session_id: str, code: str, allowed_origins: list[str]) -> list[dict[str, str]]:
        session = await self._get_session(session_id, allowed_origins)
        async with session.lock:
            output: list[dict[str, str]] = []
            text_size = 0
            image_count = 0

            def log(value: Any) -> None:
                nonlocal text_size
                remaining = self.max_text_chars - text_size
                if remaining <= 0:
                    return
                text = str(value)[:remaining]
                text_size += len(text)
                output.append({"type": "input_text", "text": text})

            def display(value: Any) -> None:
                nonlocal image_count
                if image_count >= self.max_images:
                    raise RuntimeExecutionError("Screenshot count limit exceeded.")
                image_count += 1
                output.append({"type": "input_image", "image_url": self._encode_image(value), "detail": "original"})

            session.namespace.update({"log": log, "display": display})
            compiled = compile(code, "<marsel-computer-use>", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT, dont_inherit=True)

            async def run_code() -> None:
                result = eval(compiled, session.namespace, session.namespace)
                if inspect.isawaitable(result):
                    await result

            try:
                await asyncio.wait_for(run_code(), timeout=self.execution_timeout_seconds)
            except asyncio.TimeoutError as exc:
                log("Execution stopped: time limit exceeded.")
                raise RuntimeExecutionError("Execution time limit exceeded.") from exc
            except Exception as exc:
                log(f"Execution error: {type(exc).__name__}: {str(exc)[:1000]}")

            if image_count == 0:
                display(await session.page.screenshot(type="png"))
            if not output:
                log("Execution completed.")
            return output

    async def close(self, session_id: str) -> None:
        async with self._lock:
            session = self._sessions.pop(session_id, None)
        if session is None:
            return
        await session.browser.close()
        await session.playwright.stop()

    async def close_all(self) -> None:
        for session_id in list(self._sessions):
            await self.close(session_id)
