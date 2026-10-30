#!/usr/bin/env python3
"""MARSEL warehouse-list contract diagnostic for the documented RO App v2 API.

READ-ONLY only. The official API reference documents GET /v2/warehouse/.
Undocumented compatibility routes are never promoted to PASS evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

KEY = os.getenv("ROAPP_API_KEY", "")
API_ROOT = os.getenv("ROAPP_API_ROOT", "https://api.roapp.io").rstrip("/")
TIMEOUT = float(os.getenv("ROAPP_TIMEOUT", "30"))
INTERVAL = max(float(os.getenv("ROAPP_MIN_REQUEST_INTERVAL", "0.34")), 0.34)
OUT = os.getenv("WAREHOUSE_DIAGNOSTIC_OUTPUT", "marsel-unified-warehouse-contract.json")
DOC = "https://roappua.readme.io/reference/get-warehouses"
DOCUMENTED_PATH = "/v2/warehouse/"
PROBE_TYPES = ("product", "asset")


def get(path: str, query: dict[str, str] | None = None):
    time.sleep(INTERVAL)
    url = f"{API_ROOT}{path}"
    if query:
        url += "?" + urlencode(query)
    req = Request(
        url,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Accept": "application/json",
            "User-Agent": "MARSEL-V20.48.1-READONLY",
        },
        method="GET",
    )
    started = time.time()
    try:
        with urlopen(req, timeout=TIMEOUT) as response:
            body = response.read().decode("utf-8", errors="replace")
            return {
                "url": url,
                "http": response.status,
                "elapsed_s": round(time.time() - started, 3),
                "body": body,
                "error": None,
            }
    except Exception as exc:
        body = ""
        status = getattr(exc, "code", None)
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return {
            "url": url,
            "http": status,
            "elapsed_s": round(time.time() - started, 3),
            "body": body,
            "error": f"{type(exc).__name__}: {exc}",
        }


def summarize(result):
    body = result.get("body", "")
    summary = {k: result.get(k) for k in ("url", "http", "elapsed_s", "error")}
    try:
        payload = json.loads(body)
    except Exception:
        summary.update(
            {
                "json_valid": False,
                "top_level_type": None,
                "keys": None,
                "candidate_counts": {},
                "data_is_list": False,
                "data_count": None,
                "count": None,
                "success": None,
                "collection_complete": False,
            }
        )
        return summary
    summary.update({"json_valid": True, "top_level_type": type(payload).__name__})
    if isinstance(payload, dict):
        summary["keys"] = sorted(payload.keys())
        counts = {}
        for key, value in payload.items():
            if isinstance(value, list):
                counts[key] = len(value)
            elif isinstance(value, dict):
                counts[key] = {"type": "dict", "keys": sorted(value.keys())[:30]}
        data = payload.get("data")
        summary["candidate_counts"] = counts
        summary["data_is_list"] = isinstance(data, list)
        summary["data_count"] = len(data) if isinstance(data, list) else None
        summary["count"] = payload.get("count")
        summary["success"] = payload.get("success")
    else:
        summary["keys"] = None
        summary["candidate_counts"] = {"root_list": len(payload)} if isinstance(payload, list) else {}
        summary["data_is_list"] = isinstance(payload, list)
        summary["data_count"] = len(payload) if isinstance(payload, list) else None
        summary["count"] = None
        summary["success"] = None
    summary["collection_complete"] = is_complete_list_response(summary)
    return summary


def is_complete_list_response(probe):
    """Require a valid documented list shape and a matching declared count."""
    count = probe.get("count")
    data_count = probe.get("data_count")
    success = probe.get("success")
    return (
        probe.get("http") == 200
        and probe.get("json_valid") is True
        and probe.get("data_is_list") is True
        and isinstance(count, int)
        and count == data_count
        and (success is None or success is True)
    )

def main() -> int:
    if not KEY:
        raise SystemExit("ROAPP_API_KEY is required")

    # Both values are explicitly documented by the current v2 API reference.
    # Do not add page/limit or branch identifiers unless the contract documents them.
    probes = [
        summarize(get(DOCUMENTED_PATH, {"type": warehouse_type}))
        for warehouse_type in PROBE_TYPES
    ]
    for warehouse_type, probe in zip(PROBE_TYPES, probes):
        print(
            "WAREHOUSE_PROBE "
            f"type={warehouse_type} http={probe.get('http')} "
            f"data_count={probe.get('data_count')} declared_count={probe.get('count')} "
            f"error={probe.get('error')}"
        )
    list_ok = len(probes) == len(PROBE_TYPES) and all(
        is_complete_list_response(probe) for probe in probes
    )
    result = "PASS" if list_ok else "NOT_VERIFIED"
    report = {
        "version": "20.48.1",
        "mode": "READ_ONLY",
        "readonly": True,
        "result": result,
        "official_documentation": DOC,
        "documented_contract": DOCUMENTED_PATH,
        "documented_type_values": list(PROBE_TYPES),
        "api_root": API_ROOT,
        "probed_path": DOCUMENTED_PATH,
        "probes": probes,
        "warehouse_list_contract_verified": list_ok,
        "collection_completeness_verified": list_ok,
        "confirmed_live_gets": [
            p for p in probes if p.get("http") == 200 and p.get("json_valid")
        ],
        "write_requests_made": 0,
        "ro_app_data_mutated": False,
    }
    raw = json.dumps(report, ensure_ascii=False, indent=2).encode()
    report["report_sha256"] = hashlib.sha256(raw).hexdigest()
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    print(f"WAREHOUSE_CONTRACT_RESULT={result}")
    print(f"WAREHOUSE_LIST_CONTRACT_VERIFIED={str(list_ok).lower()}")
    print(f"WAREHOUSE_CONFIRMED_LIVE_GETS={len(report['confirmed_live_gets'])}")
    print(f"WAREHOUSE_COLLECTION_COMPLETENESS_VERIFIED={str(list_ok).lower()}")
    print("WRITE_REQUESTS_MADE=0")
    print("RO_APP_DATA_MUTATED=false")
    return 0 if list_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
