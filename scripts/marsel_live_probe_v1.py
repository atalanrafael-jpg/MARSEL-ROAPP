#!/usr/bin/env python3
"""MARSEL ROAPP safe live probes.

Only probe endpoints explicitly supplied through environment variables.
No credentials are printed or persisted. No write methods are used.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen

TARGETS = {
    "ROAPP API": "ROAPP_HEALTH_URL",
    "Supabase": "SUPABASE_HEALTH_URL",
    "Vercel": "VERCEL_HEALTH_URL",
    "OpenAI Platform": "OPENAI_HEALTH_URL",
    "Wix": "WIX_HEALTH_URL",
}
OUT = Path("artifacts/marsel-live-probes.json")


def probe(url: str) -> dict:
    start = time.monotonic()
    try:
        request = Request(
            url,
            method="GET",
            headers={"User-Agent": "MARSEL-ROAPP-Health/1.2"},
        )
        with urlopen(request, timeout=10) as response:
            return {
                "verified": 200 <= response.status < 400,
                "http_status": response.status,
                "latency_ms": round((time.monotonic() - start) * 1000, 1),
            }
    except Exception as exc:
        return {
            "verified": False,
            "error_class": type(exc).__name__,
            "latency_ms": round((time.monotonic() - start) * 1000, 1),
        }


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    results = []

    for system, env_name in TARGETS.items():
        url = os.getenv(env_name)
        if not url:
            results.append({
                "system": system,
                "status": "HEALTH_ENDPOINT_NOT_CONFIGURED",
                "verified": False,
            })
            continue

        result = probe(url)
        result.update({
            "system": system,
            "status": "LIVE_VERIFIED" if result["verified"] else "FAILED",
        })
        results.append(result)

    missing = [
        result["system"] for result in results
        if result["status"] == "HEALTH_ENDPOINT_NOT_CONFIGURED"
    ]
    failed = [
        result["system"] for result in results
        if result["status"] == "FAILED"
    ]
    verified = [
        result["system"] for result in results
        if result["status"] == "LIVE_VERIFIED"
    ]
    review_required = bool(missing or failed)

    payload = {
        "schema": "marsel-live-probes/v1.1",
        "project": "MARSEL ROAPP",
        "mode": "READ_ONLY",
        "status": "REVIEW_REQUIRED" if review_required else "PASS",
        "credentials_exposed": False,
        "production_write": False,
        "results": results,
        "review_reasons": [
            *(
                f"{system}: auxiliary health endpoint not configured"
                for system in missing
            ),
            *(f"{system}: auxiliary health probe failed" for system in failed),
        ],
        "note": (
            "This workflow checks auxiliary health URLs only; absence of a "
            "health URL does not prove that the underlying integration is "
            "unavailable. Production Gate remains fail-closed and authoritative."
        ),
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        "MARSEL_LIVE_PROBES=REVIEW_REQUIRED"
        if review_required else "MARSEL_LIVE_PROBES=PASS"
    )
    print("LIVE_VERIFIED=" + ",".join(verified) if verified else "LIVE_VERIFIED=NONE")
    if missing:
        print("HEALTH_ENDPOINT_NOT_CONFIGURED=" + ",".join(missing))
    if failed:
        print("FAILED=" + ",".join(failed))

    # Diagnostic evidence only; this does not decide production readiness.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
