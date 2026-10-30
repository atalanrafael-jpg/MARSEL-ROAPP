#!/usr/bin/env python3
"""MARSEL full read-only backup controller.

Consumes canonical API inventory and reads only explicitly documented GET
endpoints. Collection responses are paginated to the first short page; valid
singleton/object responses are captured as one record. Any HTTP/schema/
pagination failure makes the backup incomplete. No write request is possible
in this program.
"""
from __future__ import annotations
import hashlib, json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
import httpx
from marsel_date_windows import build_date_windows

BASE = os.environ.get("ROAPP_API_BASE", "https://api.roapp.io/v2").rstrip("/")
KEY = os.environ.get("ROAPP_API_KEY", "")
INVENTORY = Path(os.environ.get("MARSEL_INVENTORY_INPUT", "marsel-api-inventory-v20-31.json"))
OUT = Path(os.environ.get("MARSEL_FULL_BACKUP_OUTPUT", "marsel-full-readonly-backup-v1.json"))
PAGE_SIZE = min(max(int(os.environ.get("ROAPP_PAGE_SIZE", "50")), 1), 50)
MAX_PAGES = int(os.environ.get("MARSEL_MAX_PAGES_PER_ENDPOINT", "10000"))
INTERVAL = max(float(os.environ.get("ROAPP_MIN_REQUEST_INTERVAL", "0.34")), 0.34)
if not KEY:
    raise SystemExit("ROAPP_API_KEY is required")
if not INVENTORY.exists():
    raise SystemExit(f"inventory missing: {INVENTORY}")
inv = json.loads(INVENTORY.read_text(encoding="utf-8"))

items = []
def walk(x):
    if isinstance(x, dict):
        method = str(x.get("method", "")).upper()
        path = x.get("path") or x.get("endpoint") or x.get("url")
        evidence = str(x.get("evidence", "")).upper()
        if method == "GET" and isinstance(path, str) and path.startswith("/") and "DOCUMENTATION_CONFIRMED" in evidence:
            items.append(x)
        for v in x.values():
            walk(v)
    elif isinstance(x, list):
        for v in x:
            walk(v)
walk(inv)

paths = []
for x in items:
    p = x.get("path") or x.get("endpoint") or x.get("url")
    if isinstance(p, str) and "{" not in p and "}" not in p:
        p = p.split("?")[0]
        # Inventory evidence may contain absolute API paths (/v2/...), while
        # ROAPP_API_BASE already includes /v2. Normalize once to avoid /v2/v2/.
        if p.startswith("/v2/"):
            p = p[3:]
        elif p == "/v2":
            p = "/"
        if not p.startswith("/"):
            p = "/" + p
        if p not in paths:
            paths.append(p)

headers = {
    "Authorization": f"Bearer {KEY}",
    "Accept": "application/json",
    "User-Agent": "MARSEL-Full-Readonly-Backup-v4",
}
results = []
write_requests = 0

with httpx.Client(timeout=20) as c:
    for p in sorted(paths):
        rows = []
        endpoint_ok = True
        endpoint_error = None
        response_kind = None
        pages_read = 0

        # RO App limits this endpoint to 92 calendar days per request.
        # Split the configured inclusive range into contiguous, non-overlapping
        # windows and restart pagination for each window.
        date_windows = [(None, None)]
        if p == "/company/work-schedule/days":
            date_from = os.environ.get("ROAPP_WORK_SCHEDULE_DATE_FROM", "")
            date_to = os.environ.get("ROAPP_WORK_SCHEDULE_DATE_TO", "")
            if not date_from or not date_to:
                endpoint_ok = False
                endpoint_error = (
                    "ROAPP_WORK_SCHEDULE_DATE_FROM and "
                    "ROAPP_WORK_SCHEDULE_DATE_TO are required for "
                    "/company/work-schedule/days"
                )
            else:
                try:
                    date_windows = build_date_windows(date_from, date_to)
                except ValueError as e:
                    endpoint_ok = False
                    endpoint_error = f"invalid work-schedule date range: {e}"

        for window_start, window_end in date_windows:
            if not endpoint_ok:
                break
            page = 1
            while page <= MAX_PAGES:
                try:
                    params = {"page": page, "limit": PAGE_SIZE}
                    if window_start is not None and window_end is not None:
                        params.update({
                            "date_from": window_start.isoformat(),
                            "date_to": window_end.isoformat(),
                        })
                    r = c.get(BASE + p, headers=headers, params=params)
                    if r.status_code != 200:
                        endpoint_ok = False
                        endpoint_error = f"HTTP {r.status_code}: {r.text[:500]}"
                        break
                    payload = r.json()
                    has_paging = False
                    total_pages = None
                    if isinstance(payload, dict):
                        data = payload.get("data")
                        if not isinstance(data, list):
                            data = payload.get("items")
                        paging = payload.get("paging")
                        has_paging = isinstance(paging, dict)
                        if has_paging:
                            total_pages = paging.get("total_pages") or paging.get("totalPages")
                        if isinstance(data, list):
                            response_kind = "collection"
                        else:
                            data = [payload]
                            response_kind = "singleton"
                    elif isinstance(payload, list):
                        data = payload
                        response_kind = "collection"
                    else:
                        endpoint_ok = False
                        endpoint_error = "response is neither a JSON object nor a JSON list"
                        break

                    rows.extend(x for x in data if isinstance(x, dict))
                    pages_read += 1

                    # Only paginate when the live response explicitly exposes
                    # pagination metadata. A bare JSON list/dict collection is a
                    # complete singleton response; blindly adding page/limit to
                    # such endpoints can repeat the same records indefinitely.
                    if response_kind == "singleton" or not has_paging:
                        break
                    if isinstance(total_pages, int) and page >= total_pages:
                        break
                    if len(data) < PAGE_SIZE:
                        break
                    page += 1
                    time.sleep(INTERVAL)
                except Exception as e:
                    endpoint_ok = False
                    endpoint_error = f"{type(e).__name__}: {e}"
                    break
            else:
                endpoint_ok = False
                endpoint_error = f"pagination exceeded MARSEL_MAX_PAGES_PER_ENDPOINT={MAX_PAGES}"

            if not endpoint_ok:
                break

        result = {
            "path": p,
            "ok": endpoint_ok,
            "response_kind": response_kind,
            "pages_read": pages_read,
            "records": len(rows),
            "data": rows if endpoint_ok else [],
            "error": endpoint_error,
        }
        results.append(result)
        print(f"ENDPOINT path={p} ok={endpoint_ok} kind={response_kind} pages={pages_read} records={len(rows)}")
        if endpoint_error:
            print(f"ENDPOINT_ERROR path={p} error={endpoint_error}")
        time.sleep(INTERVAL)

failed = [x for x in results if not x["ok"]]
complete = bool(paths) and not failed
report = {
    "version": "4",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "readonly": True,
    "inventory": str(INVENTORY),
    "documented_get_endpoints": paths,
    "successful_endpoints": len(results) - len(failed),
    "failed_endpoints": len(failed),
    "total_records": sum(x["records"] for x in results),
    "write_requests_made": write_requests,
    "ro_app_data_mutated": False,
    "complete": complete,
    "results": results,
}
canonical = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
report["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"DOCUMENTED_GET_ENDPOINTS={len(paths)}")
print(f"SUCCESS={len(results)-len(failed)} FAILED={len(failed)} RECORDS={report['total_records']}")
print("WRITE_REQUESTS_MADE=0")
print("RO_APP_DATA_MUTATED=False")
print("RESULT=PASS" if complete else "RESULT=INCOMPLETE")
if not complete:
    raise SystemExit(2)
