from __future__ import annotations

import hmac
import inspect
import os
from typing import Any, Protocol
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field


class Executor(Protocol):
    def execute(self, session_id: str, code: str, allowed_origins: list[str]) -> Any: ...
    def close(self, session_id: str) -> Any: ...


class ExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=36, max_length=36)
    code: str = Field(min_length=1, max_length=20_000)
    policy: dict[str, Any]


def _normalize_origin(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Origin must be a non-empty URL.")
    parsed = urlsplit(value.strip())
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Origin contains an invalid port.") from exc
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
        raise ValueError("Origin must be an exact HTTP(S) origin.")
    host = parsed.hostname.lower()
    if parsed.scheme == "http" and host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Non-local origins must use HTTPS.")
    default_port = 443 if parsed.scheme == "https" else 80
    suffix = f":{port}" if port and port != default_port else ""
    return f"{parsed.scheme}://{host}{suffix}"


def _validate_policy(policy: dict[str, Any], runtime_origins: list[str]) -> list[str]:
    requested = policy.get("allowed_origins")
    if not isinstance(requested, list) or not requested:
        raise HTTPException(status_code=422, detail="A non-empty origin allowlist is required.")
    try:
        normalized = list(dict.fromkeys(_normalize_origin(item) for item in requested))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid allowed origin.") from exc
    if not set(normalized).issubset(set(runtime_origins)):
        raise HTTPException(status_code=403, detail="Requested origin is outside the runtime allowlist.")
    if policy.get("network_egress") != "allowlist_only":
        raise HTTPException(status_code=403, detail="Only allowlisted network egress is permitted.")
    if policy.get("filesystem_access") not in {"sandbox_only", "disabled"}:
        raise HTTPException(status_code=403, detail="Host filesystem access is not permitted.")
    if policy.get("host_environment") != "not_inherited":
        raise HTTPException(status_code=403, detail="Host environment variables must not be inherited.")
    if policy.get("production_write") is not False:
        raise HTTPException(status_code=403, detail="Production writes are disabled.")
    if policy.get("require_approval_for_consequential_actions") is not True:
        raise HTTPException(status_code=403, detail="Consequential actions require user approval.")
    return normalized


def create_app(*, auth_token: str | None = None, allowed_origins: list[str] | None = None, network_policy_enforced: bool | None = None, executor: Executor | None = None) -> FastAPI:
    """Create the runtime API. A trusted launcher must attest the Vercel egress policy."""
    token = auth_token if auth_token is not None else os.getenv("COMPUTER_USE_RUNTIME_TOKEN", "")
    raw_origins = allowed_origins if allowed_origins is not None else os.getenv("COMPUTER_USE_ALLOWED_ORIGINS", "").split(",")
    policy_attested = network_policy_enforced if network_policy_enforced is not None else os.getenv("COMPUTER_USE_NETWORK_POLICY_ENFORCED", "").lower() == "true"
    if isinstance(raw_origins, str):
        raw_origins = [raw_origins]
    normalized_origins: list[str] = []
    for origin in raw_origins:
        if not origin:
            continue
        try:
            normalized = _normalize_origin(origin)
        except ValueError as exc:
            raise ValueError("Runtime origin allowlist contains an invalid origin.") from exc
        if normalized not in normalized_origins:
            normalized_origins.append(normalized)

    runtime_executor = executor
    if runtime_executor is None:
        from .playwright_executor import PlaywrightExecutor
        runtime_executor = PlaywrightExecutor()

    app = FastAPI(title="MARSEL ROAPP Isolated Computer Use Runtime", docs_url=None, redoc_url=None)
    app.state.executor = runtime_executor
    app.state.auth_token = token
    app.state.allowed_origins = normalized_origins
    app.state.network_policy_enforced = bool(policy_attested)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ready" if app.state.network_policy_enforced and app.state.auth_token else "blocked", "network_policy_enforced": app.state.network_policy_enforced}

    @app.post("/execute")
    async def execute(request: ExecuteRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        if not app.state.auth_token or not authorization:
            raise HTTPException(status_code=401, detail="Unauthorized.")
        scheme, _, supplied = authorization.partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(supplied, app.state.auth_token):
            raise HTTPException(status_code=401, detail="Unauthorized.")
        if not app.state.network_policy_enforced:
            raise HTTPException(status_code=503, detail="Sandbox network policy is not attested.")
        if not app.state.allowed_origins:
            raise HTTPException(status_code=503, detail="Runtime origin allowlist is empty.")
        try:
            UUID(request.session_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid session identifier.") from exc
        if not request.code.strip():
            raise HTTPException(status_code=422, detail="Code must not be empty.")
        if len(request.code) > 20_000:
            raise HTTPException(status_code=413, detail="Code exceeds the maximum size.")
        allowed = _validate_policy(request.policy, app.state.allowed_origins)
        try:
            result = app.state.executor.execute(request.session_id, request.code, allowed)
            if inspect.isawaitable(result):
                result = await result
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Isolated execution failed.") from exc
        if not isinstance(result, list) or not result:
            raise HTTPException(status_code=502, detail="Runtime returned no observations.")
        return {"policy_enforced": True, "output": result}

    @app.delete("/sessions/{session_id}")
    async def close_session(session_id: str, authorization: str | None = Header(default=None)) -> dict[str, bool]:
        if not app.state.auth_token or not authorization:
            raise HTTPException(status_code=401, detail="Unauthorized.")
        scheme, _, supplied = authorization.partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(supplied, app.state.auth_token):
            raise HTTPException(status_code=401, detail="Unauthorized.")
        try:
            UUID(session_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid session identifier.") from exc
        try:
            result = app.state.executor.close(session_id)
            if inspect.isawaitable(result):
                await result
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Session cleanup failed.") from exc
        return {"closed": True}

    return app
