#!/usr/bin/env python3
"""Inventory production-evidence producers without manufacturing evidence.

This controller is deliberately fail-closed: it reports which required evidence
files have real local producers and which are missing. It never writes PASS
claims or synthetic evidence documents.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "evidence"
REQUIRED = [
    "backup_evidence.json",
    "restore_evidence.json",
    "wix_roapp_reconciliation.json",
    "marsel-unified-evidence.json",
    "duplicate_reference_evidence.json",
    "write_dry_run.json",
    "idempotency_evidence.json",
    "rollback_evidence.json",
]
# A producer must contain the evidence filename (or a clearly equivalent
# output assignment) outside the release-readiness validator itself.
SEARCH_ROOTS = [ROOT / "scripts", ROOT / ".github", ROOT / "tests"]
EXCLUDED = {"marsel_release_readiness_v1.py", "marsel_evidence_producer_inventory_v1.py"}


def is_direct_producer(source: str, evidence_name: str) -> bool:
    """Return true only for an explicit file-creation/write operation.

    Filename mentions, tests, artifact upload declarations, and read operations
    are not evidence producers. This conservative check may report unknown
    dynamic writers as unverified; it must never promote them to verified.
    """
    escaped = re.escape(evidence_name)
    patterns = (
        rf"Path\(\s*['\"]{escaped}['\"]\s*\)\s*\.\s*(?:write_text|write_bytes)\s*\(",
        rf"open\(\s*['\"]{escaped}['\"]\s*,\s*['\"][wa]['\"]",
    )
    return any(re.search(pattern, source) for pattern in patterns)


def main() -> int:
    rows = []
    for name in REQUIRED:
        producers = []
        for base in SEARCH_ROOTS:
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if not path.is_file() or path.name in EXCLUDED:
                    continue
                if path.suffix not in {".py", ".yml", ".yaml", ".sh"}:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                if path.parts[-2] == "tests":
                    continue
                if is_direct_producer(text, name):
                    producers.append(str(path.relative_to(ROOT)))
        rows.append({
            "evidence": name,
            "file_present": (EVIDENCE_DIR / name).is_file(),
            "producers": sorted(set(producers)),
            "producer_count": len(set(producers)),
        })

    payload = {
        "system": "MARSEL Evidence Producer Inventory",
        "status": "PASS" if all(r["file_present"] and r["producer_count"] > 0 for r in rows) else "INCOMPLETE",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source": "github-actions:marsel-evidence-producer-inventory",
        "readonly": True,
        "write_requests_made": 0,
        "ro_app_data_mutated": False,
        "required_count": len(rows),
        "rows": rows,
    }
    out = ROOT / "marsel-evidence-producer-inventory.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    missing = [r["evidence"] for r in rows if not r["file_present"] or not r["producers"]]
    print(f"REQUIRED_EVIDENCE_COUNT={len(rows)}")
    print(f"MISSING_PRODUCER_COUNT={len(missing)}")
    for item in missing:
        print(f"MISSING_PRODUCER={item}")
    if missing:
        raise SystemExit(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
