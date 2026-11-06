from pathlib import Path
import re
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app, require_supabase_user


@pytest.mark.parametrize(
    ("path", "payload", "write_target"),
    [
        (
            "/repairs",
            {"client_id": "client-test", "description": "Test repair"},
            "app.main.repair_service.create_repair",
        ),
        (
            "/repairs/repair-test/status",
            {"status": "in_progress"},
            "app.main.repair_service.update_status",
        ),
        (
            "/repairs/repair-test/quality",
            {"result": "passed"},
            "app.main.quality_service.add_check",
        ),
        (
            "/repairs/repair-test/notify",
            {"channel": "email", "message": "Test"},
            "app.main.notification_service.send",
        ),
        (
            "/materials",
            {"name": "Test gold", "category": "metal"},
            "app.main.material_catalog.create_material",
        ),
        (
            "/customers",
            {"full_name": "Test customer"},
            "app.main.customer_service.register_customer",
        ),
        (
            "/api/v1/payments/create",
            {"amount_minor": 1000, "currency": "RUB"},
            "app.main.payment_gateway.create_payment",
        ),
    ],
)
def test_mutation_endpoints_fail_closed_when_production_write_is_disabled(
    monkeypatch, path, payload, write_target
):
    monkeypatch.setattr(
        "app.main.settings",
        SimpleNamespace(production_write_enabled=False),
    )

    def unexpected_write(*args, **kwargs):
        raise AssertionError("Mutation service must not run while production WRITE is disabled")

    monkeypatch.setattr(write_target, unexpected_write)
    previous = app.dependency_overrides.get(require_supabase_user)
    app.dependency_overrides[require_supabase_user] = lambda: {
        "id": "user-test",
        "app_role": "owner",
    }
    try:
        response = TestClient(app, raise_server_exceptions=False).post(path, json=payload)
    finally:
        if previous is None:
            app.dependency_overrides.pop(require_supabase_user, None)
        else:
            app.dependency_overrides[require_supabase_user] = previous

    assert response.status_code == 403
    assert response.json()["detail"] == "Production WRITE is disabled by policy"


def test_production_write_is_disabled_by_default():
    assert getattr(settings, "production_write_enabled", None) is False


def test_owner_app_config_reports_production_write_disabled(monkeypatch):
    monkeypatch.setattr(
        "app.main.settings",
        SimpleNamespace(
            production_write_enabled=False,
            supabase_url="https://example.supabase.co",
            supabase_publishable_key="test-publishable-key",
        ),
    )
    previous = app.dependency_overrides.get(require_supabase_user)
    app.dependency_overrides[require_supabase_user] = lambda: {"id": "user-test"}
    try:
        response = TestClient(app).get("/app/config")
    finally:
        if previous is None:
            app.dependency_overrides.pop(require_supabase_user, None)
        else:
            app.dependency_overrides[require_supabase_user] = previous

    assert response.status_code == 200
    assert response.json()["production_write_enabled"] is False


def test_owner_app_write_handlers_check_the_server_write_policy():
    html = Path("web/index.html").read_text(encoding="utf-8")
    assert "production_write_enabled" in html
    assert "function ensureWriteEnabled()" in html

    for handler in (
        "createClientRow",
        "createRepairRow",
        "changeStatus",
        "writeAudit",
        "addAttachment",
        "createPayment",
    ):
        match = re.search(rf"async function {handler}\\([^)]*\\)\\{{([^}}]*)", html)
        assert match, f"Missing browser write handler: {handler}"
        assert match.group(1).startswith("if(!ensureWriteEnabled())return;"), (
            f"{handler} must check the server write policy before doing any work"
        )
