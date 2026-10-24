"""Regression tests for MARSEL workflow evidence integrity."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SYNC_WORKFLOW = ROOT / ".github" / "workflows" / "marsel-system-sync.yml"
EXECUTION_WORKFLOW = ROOT / ".github" / "workflows" / "marsel-execution-worker.yml"
UNIFIED_WORKFLOW = ROOT / ".github" / "workflows" / "marsel-unified-control-plane.yml"


def test_sync_evidence_uses_canonical_repository_identity():
    text = SYNC_WORKFLOW.read_text(encoding="utf-8")
    assert "repository=atalanrafael-jpg/MARSEL-ROAPP" in text
    assert "repository=atalanrafael-jpg/MARSEL-Ro-app" not in text


def test_execution_evidence_creates_artifacts_directory_before_write():
    text = EXECUTION_WORKFLOW.read_text(encoding="utf-8")
    mkdir = text.find("Path('artifacts').mkdir(parents=True, exist_ok=True)")
    write = text.find("Path('artifacts/marsel-executor-evidence.json').write_text(")
    assert mkdir >= 0
    assert write >= 0
    assert mkdir < write


def test_unified_evidence_is_written_once_and_keeps_gate_outcome():
    text = UNIFIED_WORKFLOW.read_text(encoding="utf-8")
    start = text.index("- name: Build unified evidence with failure provenance")
    end = text.index("- name: Upload unified evidence", start)
    block = text[start:end]
    assert block.count("json.dump(") == 1
    assert "'quality_gate_outcome': quality_gate_outcome" in block
    assert "quality_gate_outcome == 'success'" in block
    assert "status = 'INCOMPLETE' if missing else ('PASS' if quality_gate_outcome == 'success' and final == 'PASS' else 'REVIEW_REQUIRED')" in block
