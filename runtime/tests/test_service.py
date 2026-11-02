from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from computer_use_runtime.service import create_app


POLICY = {
    "allowed_origins": ["http://127.0.0.1:8000"],
    "network_egress": "allowlist_only",
    "filesystem_access": "disabled",
    "host_environment": "not_inherited",
    "production_write": False,
    "require_approval_for_consequential_actions": True,
}


class FakeExecutor:
    def __init__(self):
        self.calls = []
        self.closed = []

    def execute(self, session_id, code, allowed_origins):
        self.calls.append((session_id, code, tuple(allowed_origins)))
        return [
            {"type": "input_text", "text": f"call={len(self.calls)}"},
            {
                "type": "input_image",
                "image_url": "data:image/png;base64,aGVsbG8=",
                "detail": "original",
            },
        ]

    def close(self, session_id):
        self.closed.append(session_id)


def client_for(executor=None, *, enabled=True, allowed_origins=None):
    app = create_app(
        auth_token="test-runtime-token",
        allowed_origins=allowed_origins or ["http://127.0.0.1:8000"],
        network_policy_enforced=enabled,
        executor=executor or FakeExecutor(),
    )
    return TestClient(app)


def test_execute_requires_bearer_authentication():
    client = client_for()
    response = client.post(
        "/execute",
        json={"session_id": str(uuid4()), "code": "log('hello')", "policy": POLICY},
    )
    assert response.status_code == 401


def test_runtime_fails_closed_without_network_policy_attestation():
    client = client_for(enabled=False)
    response = client.post(
        "/execute",
        headers={"Authorization": "Bearer test-runtime-token"},
        json={"session_id": str(uuid4()), "code": "log('hello')", "policy": POLICY},
    )
    assert response.status_code == 503


def test_execute_rejects_origin_not_in_runtime_allowlist():
    executor = FakeExecutor()
    client = client_for(executor, allowed_origins=["http://127.0.0.1:8000"])
    policy = {**POLICY, "allowed_origins": ["https://example.com"]}
    response = client.post(
        "/execute",
        headers={"Authorization": "Bearer test-runtime-token"},
        json={"session_id": str(uuid4()), "code": "log('hello')", "policy": policy},
    )
    assert response.status_code == 403
    assert executor.calls == []


def test_execute_preserves_session_and_returns_original_screenshot():
    executor = FakeExecutor()
    client = client_for(executor)
    session_id = str(uuid4())
    headers = {"Authorization": "Bearer test-runtime-token"}

    first = client.post(
        "/execute",
        headers=headers,
        json={"session_id": session_id, "code": "log('first')", "policy": POLICY},
    )
    second = client.post(
        "/execute",
        headers=headers,
        json={"session_id": session_id, "code": "log('second')", "policy": POLICY},
    )

    assert first.status_code == second.status_code == 200
    assert first.json()["policy_enforced"] is True
    assert first.json()["output"][1]["detail"] == "original"
    assert first.json()["output"][1]["image_url"].startswith("data:image/png;base64,")
    assert [call[0] for call in executor.calls] == [session_id, session_id]
    assert [call[1] for call in executor.calls] == ["log('first')", "log('second')"]


def test_delete_session_closes_runtime_worker():
    executor = FakeExecutor()
    client = client_for(executor)
    session_id = str(uuid4())
    response = client.delete(
        f"/sessions/{session_id}",
        headers={"Authorization": "Bearer test-runtime-token"},
    )
    assert response.status_code == 200
    assert executor.closed == [session_id]


def test_execute_rejects_invalid_session_identifier_and_oversized_code():
    executor = FakeExecutor()
    client = client_for(executor)
    headers = {"Authorization": "Bearer test-runtime-token"}

    invalid_session = client.post(
        "/execute",
        headers=headers,
        json={"session_id": "not-a-uuid", "code": "log('hello')", "policy": POLICY},
    )
    oversized = client.post(
        "/execute",
        headers=headers,
        json={"session_id": str(uuid4()), "code": "x" * 20001, "policy": POLICY},
    )

    assert invalid_session.status_code == 422
    assert oversized.status_code == 413
    assert executor.calls == []
