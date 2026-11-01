#!/usr/bin/env python3
"""Inventory required evidence files and explicit local producers.

A filename mention, test assertion, or artifact upload declaration is not proof
that evidence is produced. This check is conservative and never fabricates
evidence. External/dynamic producers remain unverified until directly observed.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import PurePosixPath
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
SEARCH_ROOTS = [ROOT / "scripts", ROOT / ".github", ROOT / "tests"]
EXCLUDED = {
    "marsel_release_readiness_v1.py",
    "marsel_evidence_producer_inventory_v1.py",
}


def _literal_output_path(node: ast.AST) -> str | None:
    """Return a literal path or an environment default used to build a Path."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return None
    if node.func.attr != "get" or len(node.args) < 2:
        return None
    owner = node.func.value
    if not (
        isinstance(owner, ast.Attribute)
        and owner.attr == "environ"
        and isinstance(owner.value, ast.Name)
        and owner.value.id == "os"
    ):
        return None
    default = node.args[1]
    return default.value if isinstance(default, ast.Constant) and isinstance(default.value, str) else None


def _target_names(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, (ast.Tuple, ast.List)):
        names: set[str] = set()
        for item in node.elts:
            names.update(_target_names(item))
        return names
    return set()


def is_direct_producer(source: str, evidence_name: str) -> bool:
    """Recognize direct writes, including Path outputs configured by environment defaults."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        tree = None

    if tree is not None:
        output_variables: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = node.value
                if (
                    isinstance(value, ast.Call)
                    and isinstance(value.func, ast.Name)
                    and value.func.id == "Path"
                    and value.args
                    and PurePosixPath(_literal_output_path(value.args[0]) or "").name == evidence_name
                ):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    for target in targets:
                        output_variables.update(_target_names(target))

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"write_text", "write_bytes"}
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in output_variables
            ):
                return True

    escaped = re.escape(evidence_name)
    literal_path = rf"(?:[A-Za-z0-9_./-]*?/)?{escaped}"
    patterns = (
        rf"Path\(\s*['\"]{literal_path}['\"]\s*\)\s*\.\s*(?:write_text|write_bytes)\s*\(",
        rf"open\(\s*['\"]{literal_path}['\"]\s*,\s*['\"][wa]['\"]",
    )
    return any(re.search(pattern, source) for pattern in patterns)



def classify_inventory_rows(rows: list[dict]) -> dict[str, list[str]]:
    """Separate absent evidence files from files without a recognized producer."""
    missing_evidence = [
        row["evidence"] for row in rows if not row.get("file_present", False)
    ]
    missing_producers = [
        row["evidence"] for row in rows if not row.get("producer_count", 0)
    ]
    incomplete = [
        row["evidence"] for row in rows
        if not row.get("file_present", False) or not row.get("producer_count", 0)
    ]
    return {
        "missing_evidence": missing_evidence,
        "missing_producers": missing_producers,
        "incomplete": incomplete,
    }

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
                if "tests" in path.relative_to(ROOT).parts:
                    continue
                source = path.read_text(encoding="utf-8", errors="ignore")
                if is_direct_producer(source, name):
                    producers.append(str(path.relative_to(ROOT)))
        rows.append({
            "evidence": name,
            "file_present": (EVIDENCE_DIR / name).is_file(),
            "producers": sorted(set(producers)),
            "producer_count": len(set(producers)),
        })

    classification = classify_inventory_rows(rows)
    payload = {
        "system": "MARSEL Evidence Producer Inventory",
        "status": "PASS" if not classification["incomplete"] else "INCOMPLETE",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source": "github-actions:marsel-evidence-producer-inventory",
        "readonly": True,
        "write_requests_made": 0,
        "ro_app_data_mutated": False,
        "evidence_validation": "NOT_PERFORMED",
        "required_count": len(rows),
        "missing_evidence": classification["missing_evidence"],
        "missing_producers": classification["missing_producers"],
        "rows": rows,
    }
    out = ROOT / "marsel-evidence-producer-inventory.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"REQUIRED_EVIDENCE_COUNT={len(rows)}")
    print(f"MISSING_EVIDENCE_COUNT={len(classification['missing_evidence'])}")
    for item in classification["missing_evidence"]:
        print(f"MISSING_EVIDENCE={item}")
    print(f"MISSING_PRODUCER_COUNT={len(classification['missing_producers'])}")
    for item in classification["missing_producers"]:
        print(f"MISSING_PRODUCER={item}")
    print("EVIDENCE_VALIDATION=NOT_PERFORMED")
    return 2 if classification["incomplete"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
