from contextlib import contextmanager

import json
from types import SimpleNamespace

import pytest

from app.computer_use import (
    ComputerUseError,
    ComputerUseService,
    normalize_executor_payload,
)


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.outputs.pop(0)


class FakeOpenAI:
    def __init__(self, outputs):
        self.responses = FakeResponses(outputs)


def function_call(call_id="call_1", code="log('hello')"):
    return SimpleNamespace(
        type="function_call",
        name="exec_py",
        call_id=call_id,
        arguments=json.dumps({"code": code}),
    )


def response(response_id, output, text=""):
    return SimpleNamespace(
        id=response_id,
        status="completed",
        output=output,
        output_text=text,
    )


def configured_settings():
    return SimpleNamespace(
        openai_api_key="test-openai-key",
        openai_computer_use_model="gpt-6-astra",
        computer_use_enabled=True,
        computer_use_runtime_url="http://127.0.0.1:8765/execute",
        computer_use_runtime_token="test-runtime-token",
        computer_use_allowed_origins=["http://127.0.0.1:8000"],
        computer_use_runtime_timeout_seconds=30,
        computer_use_max_code_chars=20000,
        computer_use_max_output_images=4,
    )


def test_tool_loop_preserves_runtime_session_and_responses_state():
    openai = FakeOpenAI([
        response("resp_1", [function_call()]),
        response("resp_2", [], "Заголовок страницы: MARSEL ROAPP"),
    ])
    executions = []

    def executor(session_id, code, policy):
        executions.append((session_id, code, policy))
        return {"policy_enforced": True, "output": [{"type": "input_text", "text": "title=MARSEL ROAPP"}]}

    service = ComputerUseService(
        settings_obj=configured_settings(),
        openai_client=openai,
        sandbox_executor=executor,
    )

    result = service.run_task("Открой локальную страницу и прочитай заголовок.")

    assert result["final_text"] == "Заголовок страницы: MARSEL ROAPP"
    assert result["turns"] == 2
    assert len(executions) == 1
    assert executions[0][0] == result["session_id"]
    assert executions[0][1] == "log('hello')"
    assert executions[0][2]["allowed_origins"] == ["http://127.0.0.1:8000"]
    assert openai.responses.calls[1]["previous_response_id"] == "resp_1"
    tool_output = openai.responses.calls[1]["input"][0]
    assert tool_output["type"] == "function_call_output"
    assert tool_output["call_id"] == "call_1"
    assert tool_output["output"] == [{"type": "input_text", "text": "title=MARSEL ROAPP"}]


def test_computer_use_fails_closed_when_runtime_is_not_configured():
    config = configured_settings()
    config.computer_use_enabled = False
    service = ComputerUseService(settings_obj=config)

    with pytest.raises(ComputerUseError, match="not enabled"):
        service.run_task("Open the local page")


def test_computer_use_requires_a_configured_origin_allowlist():
    config = configured_settings()
    config.computer_use_allowed_origins = []
    service = ComputerUseService(settings_obj=config)

    with pytest.raises(ComputerUseError, match="allowlist"):
        service.run_task("Open the local page")


def test_executor_must_confirm_that_runtime_policy_was_enforced():
    with pytest.raises(ComputerUseError, match="policy"):
        normalize_executor_payload({
            "policy_enforced": False,
            "output": [{"type": "input_text", "text": "not isolated"}],
        })


def test_executor_output_accepts_screenshots_as_original_data_images():
    output = normalize_executor_payload({
        "policy_enforced": True,
        "output": [
            {"type": "input_text", "text": "page loaded"},
            {
                "type": "input_image",
                "image_url": "data:image/png;base64,aGVsbG8=",
                "detail": "original",
            },
        ],
    })

    assert output[1]["type"] == "input_image"
    assert output[1]["detail"] == "original"


def test_executor_rejects_non_data_image_urls():
    with pytest.raises(ComputerUseError, match="data:image"):
        normalize_executor_payload({
            "policy_enforced": True,
            "output": [{
                "type": "input_image",
                "image_url": "https://example.com/screenshot.png",
                "detail": "original",
            }],
        })


def test_tool_loop_stops_after_configured_turn_limit():
    config = configured_settings()
    openai = FakeOpenAI([
        response("resp_1", [function_call("call_1")]),
        response("resp_2", [function_call("call_2")]),
    ])
    service = ComputerUseService(
        settings_obj=config,
        openai_client=openai,
        sandbox_executor=lambda *_: {"policy_enforced": True, "output": [{"type": "input_text", "text": "ok"}]},
    )

    with pytest.raises(ComputerUseError, match="turn limit"):
        service.run_task("Run a bounded local task.", max_turns=1)


def test_non_local_http_origin_is_rejected():
    config = configured_settings()
    config.computer_use_allowed_origins = ["http://example.com"]
    service = ComputerUseService(settings_obj=config)

    with pytest.raises(ComputerUseError, match="HTTPS"):
        service.run_task("Open a page")


def test_origin_entries_must_be_exact_origins():
    config = configured_settings()
    config.computer_use_allowed_origins = ["http://127.0.0.1:8000/private"]
    service = ComputerUseService(settings_obj=config)

    with pytest.raises(ComputerUseError, match="exact HTTP"):
        service.run_task("Open a page")


def test_requested_turn_limit_is_capped_by_server_configuration():
    config = configured_settings()
    config.computer_use_max_turns = 1
    openai = FakeOpenAI([
        response("resp_1", [function_call()]),
        response("resp_2", [], "should not be reached"),
    ])
    executions = []
    service = ComputerUseService(
        settings_obj=config,
        openai_client=openai,
        sandbox_executor=lambda *args: executions.append(args) or {"policy_enforced": True, "output": [
            {"type": "input_text", "text": "ok"}
        ]},
    )

    with pytest.raises(ComputerUseError, match="turn limit"):
        service.run_task("Run a bounded task.", max_turns=8)

    assert executions == []
    assert len(openai.responses.calls) == 1


def test_tool_call_count_is_bounded_before_any_script_executes():
    config = configured_settings()
    config.computer_use_max_tool_calls = 1
    openai = FakeOpenAI([
        response("resp_1", [function_call("call_1"), function_call("call_2")]),
    ])
    executions = []
    service = ComputerUseService(
        settings_obj=config,
        openai_client=openai,
        sandbox_executor=lambda *args: executions.append(args) or {"policy_enforced": True, "output": [
            {"type": "input_text", "text": "ok"}
        ]},
    )

    with pytest.raises(ComputerUseError, match="tool-call limit"):
        service.run_task("Run a bounded task.")

    assert executions == []


def test_tool_loop_rejects_executor_without_policy_confirmation():
    openai = FakeOpenAI([
        response("resp_1", [function_call()]),
        response("resp_2", [], "must not reach this response"),
    ])
    service = ComputerUseService(
        settings_obj=configured_settings(),
        openai_client=openai,
        sandbox_executor=lambda *_: {
            "policy_enforced": False,
            "output": [{"type": "input_text", "text": "not isolated"}],
        },
    )

    with pytest.raises(ComputerUseError, match="policy"):
        service.run_task("Run a bounded local task.")

    assert len(openai.responses.calls) == 1


class FakeSandboxRuntime:
    def __init__(self, connection_origins=None):
        self.closed = False
        self.origins = None
        self.connection_origins = connection_origins

    @contextmanager
    def open(self, allowed_origins):
        self.origins = list(allowed_origins)
        try:
            yield SimpleNamespace(
                url="https://sandbox.example.test/execute",
                token="ephemeral-runtime-token",
                allowed_origins=tuple(self.connection_origins or allowed_origins),
            )
        finally:
            self.closed = True


def test_computer_use_uses_one_disposable_sandbox_for_the_full_task():
    openai = FakeOpenAI([
        response("resp_1", [function_call()]),
        response("resp_2", [], "Task completed."),
    ])
    runtime = FakeSandboxRuntime()
    service = ComputerUseService(
        settings_obj=configured_settings(),
        openai_client=openai,
        sandbox_runtime=runtime,
    )
    executions = []

    def execute(**kwargs):
        executions.append(kwargs)
        return [{"type": "input_text", "text": "page title: MARSEL"}]

    service._execute_in_sandbox = execute
    result = service.run_task("Read the page title.")

    assert result["final_text"] == "Task completed."
    assert runtime.origins == ["http://127.0.0.1:8000"]
    assert runtime.closed is True
    assert len(executions) == 1
    assert executions[0]["runtime_url"] == "https://sandbox.example.test/execute"
    assert executions[0]["runtime_token"] == "ephemeral-runtime-token"
    assert executions[0]["policy"]["filesystem_access"] == "sandbox_only"


class FakeStreamResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def raise_for_status(self):
        return None

    def iter_bytes(self):
        yield json.dumps({
            "policy_enforced": True,
            "output": [{"type": "input_text", "text": "ok"}],
        }).encode()


class FakeStreamingHTTPClient:
    def __init__(self):
        self.request = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def stream(self, method, url, *, headers, json):
        self.request = {
            "method": method,
            "url": url,
            "headers": headers,
            "json": json,
        }
        return FakeStreamResponse()


def test_runtime_http_request_matches_strict_execute_schema(monkeypatch):
    from app import computer_use

    http_client = FakeStreamingHTTPClient()
    monkeypatch.setattr(computer_use.httpx, "Client", lambda **kwargs: http_client)
    service = ComputerUseService(settings_obj=configured_settings())

    output = service._execute_in_sandbox(
        session_id="00000000-0000-4000-8000-000000000001",
        code="log('ok')",
        runtime_url="https://sandbox.example.test/execute",
        runtime_token="runtime-token",
        policy={"allowed_origins": ["https://example.com"]},
    )

    assert output == [{"type": "input_text", "text": "ok"}]
    assert http_client.request["method"] == "POST"
    assert http_client.request["url"] == "https://sandbox.example.test/execute"
    assert http_client.request["headers"]["Authorization"] == "Bearer runtime-token"
    assert http_client.request["json"] == {
        "session_id": "00000000-0000-4000-8000-000000000001",
        "code": "log('ok')",
        "policy": {"allowed_origins": ["https://example.com"]},
    }


def test_managed_sandbox_normalized_origins_are_used_by_runtime_policy():
    config = configured_settings()
    config.computer_use_allowed_origins = ["https://example.com:443"]
    openai = FakeOpenAI([
        response("resp_1", [function_call()]),
        response("resp_2", [], "Task completed."),
    ])
    runtime = FakeSandboxRuntime(connection_origins=["https://example.com"])
    service = ComputerUseService(
        settings_obj=config,
        openai_client=openai,
        sandbox_runtime=runtime,
    )
    executions = []
    service._execute_in_sandbox = lambda **kwargs: (
        executions.append(kwargs)
        or [{"type": "input_text", "text": "ok"}]
    )

    service.run_task("Read the page title.")

    assert runtime.origins == ["https://example.com:443"]
    assert executions[0]["policy"]["allowed_origins"] == ["https://example.com"]
