from __future__ import annotations

import secrets
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from .agents.repair_estimator import RepairEstimator
from .ai_assistant import MarselAI
from .computer_use import ComputerUseError, ComputerUseService
from .payments import PaymentGateway
from .automation import get_automation_status, validate_automation_request
from .audit import audit_order_pages
from .business_models import Client, Item, RepairStatus
from .config import settings
from .mcp_auth import JWTTokenVerifier
from .mcp_server import create_mcp_server
from .observability import observability_middleware
from .roapp_client import RoAppClient
from .services.customer_service import CustomerService
from .services.dashboard_service import DashboardService
from .services.material_service import MaterialCatalog
from .services.notification_service import NotificationService
from .services.quality_service import QualityService
from .services.repair_service import RepairService


mcp_http = None
repair_service = RepairService()
material_catalog = MaterialCatalog()
dashboard_service = DashboardService()
quality_service = QualityService()
notification_service = NotificationService()
customer_service = CustomerService(repair_service)
repair_estimator = RepairEstimator()
ai_assistant = MarselAI()
computer_use_service = ComputerUseService()
payment_gateway = PaymentGateway()

if settings.mcp_http_enabled:
    missing = [
        name
        for name, value in (
            ("MCP_RESOURCE_SERVER_URL", settings.mcp_resource_server_url),
            ("MCP_AUTH_ISSUER", settings.mcp_auth_issuer),
            ("MCP_AUTH_JWKS_URL", settings.mcp_auth_jwks_url),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "MCP HTTP mode requires: " + ", ".join(missing)
        )

    verifier = JWTTokenVerifier(
        jwks_url=settings.mcp_auth_jwks_url,
        issuer=settings.mcp_auth_issuer,
        audience=settings.mcp_resource_server_url,
    )
    mcp_http = create_mcp_server(verifier)
    mcp_http.settings.streamable_http_path = "/"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if mcp_http is None:
        yield
        return

    async with mcp_http.session_manager.run():
        yield


app = FastAPI(
    title="MARSEL ROAPP Connector",
    version="0.5.0",
    lifespan=lifespan,
)
app.middleware("http")(observability_middleware)

if mcp_http is not None:
    app.mount("/mcp", mcp_http.streamable_http_app())


def require_internal_auth(x_marsel_api_key: str | None = Header(default=None)) -> None:
    """Authorize callers to the MARSEL connector without exposing RO App credentials."""
    configured = settings.marsel_internal_api_key
    if not configured:
        raise HTTPException(status_code=503, detail="MARSEL connector authentication is not configured")
    if not x_marsel_api_key or not secrets.compare_digest(x_marsel_api_key, configured):
        raise HTTPException(status_code=401, detail="Unauthorized")


async def require_supabase_user(authorization: str | None = Header(default=None)) -> dict:
    """Verify the caller's Supabase Auth access token against the Auth service."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(status_code=503, detail="Supabase authentication is not configured")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
                headers={
                    "apikey": settings.supabase_publishable_key,
                    "Authorization": f"Bearer {token}",
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Authentication service unavailable") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired authentication")

    data = response.json()
    user_id = data.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid authentication")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            profile_response = await client.get(
                f"{settings.supabase_url.rstrip('/')}/rest/v1/profiles",
                params={"id": f"eq.{user_id}", "select": "role,active"},
                headers={
                    "apikey": settings.supabase_publishable_key,
                    "Authorization": f"Bearer {token}",
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Authorization service unavailable") from exc

    if profile_response.status_code != 200:
        raise HTTPException(status_code=403, detail="Application access is not available")

    profiles = profile_response.json()
    profile = profiles[0] if profiles else None
    if not profile or profile.get("active") is not True:
        raise HTTPException(status_code=403, detail="Application access is not available")

    role = profile.get("role")
    if role not in {"owner", "admin", "employee"}:
        raise HTTPException(status_code=403, detail="Insufficient application role")

    data["app_role"] = role
    return data


def require_admin_user(user: dict = Depends(require_supabase_user)) -> dict:
    if user.get("app_role") not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


@app.get("/api/v1/admin/overview")
def admin_overview(user: dict = Depends(require_admin_user)):
    return {
        "role": user.get("app_role"),
        "production_write": False,
        "roapp_mode": "READ_ONLY",
        "ai": ai_assistant.health(),
        "payments": payment_gateway.health(),
        "auth": "supabase",
    }


@app.get("/api/v1/platform/health", dependencies=[Depends(require_supabase_user)])
def platform_health():
    return {"ai": ai_assistant.health(), "payments": payment_gateway.health(), "roapp": {"mode": "READ_ONLY", "write_enabled": False}}


class ComputerUseRequest(BaseModel):
    task: str = Field(min_length=1, max_length=6000)
    max_turns: int = Field(default=8, ge=1, le=8)


@app.post("/api/v1/computer-use/run")
def computer_use_run(
    payload: ComputerUseRequest,
    user: dict = Depends(require_admin_user),
):
    """Run one bounded Computer Use task in a separate isolated runtime."""
    try:
        result = computer_use_service.run_task(payload.task, max_turns=payload.max_turns)
    except ComputerUseError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return result


@app.post("/api/v1/ai/advise", dependencies=[Depends(require_supabase_user)])
def ai_advise(payload: dict):
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt or len(prompt) > 6000:
        raise HTTPException(status_code=400, detail="prompt is required and must be <= 6000 characters")
    result = ai_assistant.advise(prompt, payload.get("context") if isinstance(payload.get("context"), dict) else None)
    return {"text": result.text, "model": result.model, "enabled": result.enabled}


@app.post("/api/v1/payments/create", dependencies=[Depends(require_supabase_user)])
async def create_payment(payload: dict, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    try:
        amount_minor = int(payload.get("amount_minor") or 0)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="amount_minor must be an integer") from exc
    if amount_minor <= 0:
        raise HTTPException(status_code=400, detail="amount_minor must be positive")
    try:
        result = await payment_gateway.create_payment(
            amount_minor=amount_minor,
            currency=str(payload.get("currency") or "RUB"),
            description=str(payload.get("description") or "MARSEL"),
            return_url=str(payload.get("return_url") or "/app"),
            metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else None,
            idempotency_key=idempotency_key,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"provider": result.provider, "payment_id": result.payment_id,
            "confirmation_url": result.confirmation_url, "status": result.status,
            "configured": result.configured}


@app.get("/automation/status")
def automation_status():
    return get_automation_status().as_dict()


@app.post("/automation/run")
def automation_run():
    try:
        validate_automation_request()
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    status = get_automation_status().as_dict()
    return {
        "status": "accepted",
        "read_only": True,
        "allow_write": False,
        "mode": status["mode"],
        "message": "Production WRITE remains disabled; automation execution is read-only and evidence-driven.",
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "marsel-roapp-connector", "version": app.version}


@app.get("/ready")
def ready():
    """Non-sensitive service readiness check; never reports secret presence."""
    return {
        "status": "ready" if settings.roapp_base_url else "not_configured",
        "service": "marsel-roapp-connector",
        "version": app.version,
        "mcp_http_enabled": settings.mcp_http_enabled,
    }


@app.get("/repairs", dependencies=[Depends(require_supabase_user)])
def list_repairs():
    return [repair.to_dict() for repair in repair_service.list_repairs()]


@app.get("/repairs/{repair_id}", dependencies=[Depends(require_supabase_user)])
def get_repair(repair_id: str):
    return repair_service.get_repair(repair_id).to_dict()


@app.post("/repairs", dependencies=[Depends(require_supabase_user)])
def create_repair(payload: dict):
    client = Client(
        id=payload.get("client_id") or "client-1",
        full_name=payload.get("client_name") or "Unknown client",
        phone=payload.get("client_phone") or "",
        email=payload.get("client_email") or "",
        notes=payload.get("client_notes") or "",
    )
    item = Item(
        id=payload.get("item_id") or "item-1",
        client_id=client.id,
        category=payload.get("category") or "jewelry",
        subtype=payload.get("subtype") or "ring",
        material=payload.get("material") or "gold",
        stones=payload.get("stones") or "",
        description=payload.get("description") or "",
        condition_received=payload.get("condition") or "",
        serial_number=payload.get("serial_number") or "",
    )
    repair = repair_service.create_repair(
        client=client,
        item=item,
        status=payload.get("status") or RepairStatus.RECEIVED,
        description=payload.get("description") or "",
        due_at=payload.get("due_at"),
        estimate_cost=payload.get("estimate_cost"),
    )
    return repair.to_dict()


@app.post("/repairs/{repair_id}/status", dependencies=[Depends(require_supabase_user)])
def update_repair_status(repair_id: str, payload: dict):
    repair = repair_service.update_status(
        repair_id,
        status=payload.get("status") or RepairStatus.ASSESSED,
        note=payload.get("note") or "Status updated",
    )
    return repair.to_dict()


@app.post("/repairs/{repair_id}/estimate", dependencies=[Depends(require_supabase_user)])
def repair_estimate(repair_id: str, payload: dict):
    repair = repair_service.get_repair(repair_id)
    estimate = repair_estimator.estimate(
        category=repair.item.category,
        material=repair.item.material,
        description=payload.get("description") or repair.description,
    )
    return estimate.to_dict()


@app.post("/repairs/{repair_id}/quality", dependencies=[Depends(require_supabase_user)])
def add_quality_check(repair_id: str, payload: dict):
    check = quality_service.add_check(
        repair_id,
        result=payload.get("result") or "review_required",
        notes=payload.get("notes") or "",
        checked_by=payload.get("checked_by") or "owner",
    )
    return check.to_dict()


@app.get("/repairs/{repair_id}/quality", dependencies=[Depends(require_supabase_user)])
def list_quality_checks(repair_id: str):
    return [check.to_dict() for check in quality_service.list_checks(repair_id)]


@app.post("/repairs/{repair_id}/notify", dependencies=[Depends(require_supabase_user)])
def send_notification(repair_id: str, payload: dict):
    note = notification_service.send(
        repair_id=repair_id,
        channel=payload.get("channel") or "email",
        template=payload.get("template") or "status_update",
        message=payload.get("message") or "Repair status updated.",
    )
    return note.to_dict()


@app.get("/repairs/summary", dependencies=[Depends(require_supabase_user)])
def repairs_summary():
    return dashboard_service.build_summary(repair_service.list_repairs(), material_catalog.list_materials())


@app.get("/materials", dependencies=[Depends(require_supabase_user)])
def list_materials():
    return [m.to_dict() for m in material_catalog.list_materials()]


@app.post("/materials", dependencies=[Depends(require_supabase_user)])
def create_material(payload: dict):
    material = material_catalog.create_material(
        name=payload.get("name") or "Material",
        category=payload.get("category") or "metal",
        unit=payload.get("unit") or "g",
        stock=payload.get("stock") or 0,
        reorder_level=payload.get("reorder_level") or 0,
        cost_per_unit=payload.get("cost_per_unit") or 0,
    )
    return material.to_dict()


@app.get("/customers", dependencies=[Depends(require_supabase_user)])
def list_customers():
    return [
        {"client_id": repair.client.id, "full_name": repair.client.full_name, "email": repair.client.email}
        for repair in repair_service.list_repairs()
    ]


@app.post("/customers", dependencies=[Depends(require_supabase_user)])
def create_customer(payload: dict):
    customer = customer_service.register_customer(
        client_id=payload.get("client_id") or "client-1",
        full_name=payload.get("full_name") or "Unknown client",
        phone=payload.get("phone") or "",
        email=payload.get("email") or "",
    )
    return customer.to_dict()


@app.get("/customers/{client_id}/status", dependencies=[Depends(require_supabase_user)])
def customer_status(client_id: str):
    return customer_service.customer_status(client_id)


@app.get("/app", response_class=HTMLResponse)
def owner_app():
    from pathlib import Path
    path = Path(__file__).resolve().parent.parent / "web" / "index.html"
    return HTMLResponse(path.read_text(encoding="utf-8"))


@app.get("/app/config", response_class=JSONResponse)
def owner_app_config():
    return {"supabase_url": settings.supabase_url, "supabase_publishable_key": settings.supabase_publishable_key}


@app.get("/app/manifest.json", response_class=JSONResponse)
def owner_app_manifest():
    return {
        "name": "MARSEL ROAPP",
        "short_name": "MARSEL",
        "start_url": "/app",
        "display": "standalone",
        "background_color": "#080a0c",
        "theme_color": "#0b0d0f",
        "lang": "ru",
        "description": "Premium Control Center Ювелирной студии MARSEL.",
    }


@app.get("/app/session", response_class=JSONResponse)
async def owner_app_session(user: dict = Depends(require_supabase_user)):
    return {
        "authenticated": True,
        "user": {
            "id": user.get("id"),
            "email": user.get("email"),
            "role": user.get("app_role"),
        },
    }


@app.get("/roapp/orders", dependencies=[Depends(require_internal_auth)])
async def orders(page: int = Query(1, ge=1)):
    try:
        return await RoAppClient().get_orders(page)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="RO App API temporarily unavailable") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="RO App API request failed") from exc


@app.get("/roapp/audit/orders", dependencies=[Depends(require_internal_auth)])
async def audit_orders(max_pages: int = Query(10, ge=1, le=100)):
    try:
        pages = await RoAppClient().get_orders_pages(max_pages)
        return audit_order_pages(pages)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="RO App API temporarily unavailable") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="RO App API audit failed") from exc
