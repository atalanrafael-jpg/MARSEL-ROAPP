import asyncio
import sys
from types import ModuleType, SimpleNamespace

from runtime.computer_use_runtime.playwright_executor import PlaywrightExecutor


class FakePage:
    def __init__(self):
        self.route_calls = []

    async def route(self, pattern, handler):
        self.route_calls.append((pattern, handler))


class FakeContext:
    def __init__(self, page):
        self.page = page
        self.route_calls = []
        self.new_page_options = None

    async def new_page(self):
        return self.page

    async def route(self, pattern, handler):
        self.route_calls.append((pattern, handler))


class FakeBrowser:
    def __init__(self, context):
        self.context = context
        self.new_context_options = None

    async def new_context(self, **kwargs):
        self.new_context_options = kwargs
        return self.context


class FakeChromium:
    def __init__(self, browser):
        self.browser = browser
        self.launch_options = None

    async def launch(self, **kwargs):
        self.launch_options = kwargs
        return self.browser


class FakePlaywright:
    def __init__(self, chromium):
        self.chromium = chromium
        self.stopped = False

    async def stop(self):
        self.stopped = True


class FakePlaywrightManager:
    def __init__(self, playwright):
        self.playwright = playwright

    async def start(self):
        return self.playwright


def test_browser_launch_uses_empty_environment_and_context_wide_origin_guard(monkeypatch):
    page = FakePage()
    context = FakeContext(page)
    browser = FakeBrowser(context)
    chromium = FakeChromium(browser)
    playwright = FakePlaywright(chromium)
    async_api = ModuleType("playwright.async_api")
    async_api.async_playwright = lambda: FakePlaywrightManager(playwright)
    playwright_module = ModuleType("playwright")
    playwright_module.async_api = async_api
    monkeypatch.setitem(sys.modules, "playwright", playwright_module)
    monkeypatch.setitem(sys.modules, "playwright.async_api", async_api)

    executor = PlaywrightExecutor()
    session = asyncio.run(executor._new_session("session-1", ["https://example.com"]))

    assert chromium.launch_options["env"] == {}
    assert chromium.launch_options["chromium_sandbox"] is True
    assert "--disable-extensions" in chromium.launch_options["args"]
    assert "--disable-file-system" in chromium.launch_options["args"]
    assert context.route_calls and context.route_calls[0][0] == "**/*"
    assert page.route_calls == []
    assert "page" in session.namespace
    assert "context" not in session.namespace
    assert "browser" not in session.namespace
    assert session.allowed_origins == frozenset({"https://example.com"})
