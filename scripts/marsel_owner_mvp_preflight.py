#!/usr/bin/env python3
"""Static Owner MVP preflight.

This check is intentionally offline/read-only. It never contacts RO App or Supabase,
never writes application data, and never changes production gates.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md",
    "01_MASTER/MARSEL_ROAPP_PRODUCTIZATION_MVP.md",
    "app/main.py",
    "app/config.py",
    "web/index.html",
]

FORBIDDEN_SECRET_PATTERNS = [
    r"(?i)ROAPP_API_KEY\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}",
    r"(?i)(service_role|SUPABASE_SERVICE_ROLE_KEY)\s*[:=]\s*['\"][^'\"]+",
]

def fail(message: str) -> None:
    print(f"OWNER_MVP_PREFLIGHT=FAIL\nREASON={message}")
    raise SystemExit(1)

for rel in REQUIRED:
    if not (ROOT / rel).is_file():
        fail(f"missing required file: {rel}")

main = (ROOT / "app/main.py").read_text(encoding="utf-8")
config = (ROOT / "app/config.py").read_text(encoding="utf-8")
ui = (ROOT / "web/index.html").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")

for pattern in FORBIDDEN_SECRET_PATTERNS:
    for path in [ROOT / "app", ROOT / "web", ROOT / "config"]:
        if not path.exists():
            continue
        for file in path.rglob("*"):
            if file.is_file() and file.suffix in {".py", ".js", ".html", ".json", ".yaml", ".yml"}:
                text = file.read_text(encoding="utf-8", errors="ignore")
                if re.search(pattern, text):
                    fail(f"possible embedded secret in {file.relative_to(ROOT)}")

checks = {
    "health_route": '@app.get("/health")' in main,
    "ready_route": '@app.get("/ready")' in main,
    "owner_app_route": '@app.get("/app"' in main,
    "supabase_auth_gate": "require_supabase_user" in main,
    "owner_role_gate": 'role not in {"owner", "admin", "employee"}' in main,
    "read_only_roapp": "Production WRITE is disabled." in readme,
    "owner_ui": "Вход владельца" in ui,
    "client_flow": 'from("clients").insert' in ui,
    "repair_flow": 'from("repairs").insert' in ui,
    "status_history": 'from("repair_status_history").insert' in ui,
    "audit_log": 'from("audit_log").insert' in ui,
    "attachment_reference": 'from("attachments").insert' in ui,
}

failed = [name for name, ok in checks.items() if not ok]
if failed:
    fail("failed checks: " + ", ".join(failed))

print("OWNER_MVP_PREFLIGHT=PASS")
for name in checks:
    print(f"{name}=PASS")
print("ROAPP_WRITE=DISABLED_BY_PROJECT_POLICY")
print("EXTERNAL_LIVE_DEPLOYMENT=NOT_VERIFIED")
