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
        return [{"type": "input_text", "text": "title=MARSEL ROAPP"}]

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
        sandbox_executor=lambda *_: [{"type": "input_text", "text": "ok"}],
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
        sandbox_executor=lambda *args: executions.append(args) or [
            {"type": "input_text", "text": "ok"}
        ],
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
        sandbox_executor=lambda *args: executions.append(args) or [
            {"type": "input_text", "text": "ok"}
        ],
    )

    with pytest.raises(ComputerUseError, match="tool-call limit"):
        service.run_task("Run a bounded task.")

    assert executions == []
