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


def test_readme_sync_workflow_has_one_job_definition_and_artifact_path():
    text = (ROOT / ".github" / "workflows" / "readme-roapp-sync.yml").read_text(encoding="utf-8")
    assert len(re.findall(r"^jobs:", text, re.MULTILINE)) == 1
    assert text.count("          path:") == 1


def test_live_probes_workflow_has_no_incomplete_duplicate_steps():
    text = (ROOT / ".github" / "workflows" / "marsel-live-probes.yml").read_text(encoding="utf-8")
    assert text.count("- uses: actions/checkout@") == 1
    assert text.count("- name: Run read-only probes") == 1
    assert text.count("uses: actions/upload-artifact@") == 1
    assert text.count("- name: Upload probe report") == 1


def test_integration_health_workflow_has_one_job_steps_block():
    text = (ROOT / ".github" / "workflows" / "marsel-integration-health.yml").read_text(encoding="utf-8")
    assert len(re.findall(r"^    steps:", text, re.MULTILINE)) == 1
    assert text.count("- name: Run read-only integration health check") == 1

def test_readme_sync_skips_download_when_official_openapi_is_unavailable():
    text = (ROOT / ".github" / "workflows" / "readme-roapp-sync.yml").read_text(encoding="utf-8")
    contract = text.index("id: contract")
    download = text.index("- name: Download official OpenAPI JSON")
    assert contract < download
    assert "if: ${{ steps.contract.outputs.openapi_available == 'true' }}" in text[download:]
    assert "Upload validation evidence" not in text


def test_pr_safe_evidence_is_written_once_and_preserves_timestamp_and_source():
    text = UNIFIED_WORKFLOW.read_text(encoding="utf-8")
    start = text.index("- name: Build PR-safe incomplete evidence")
    end = text.index("- name: Evaluate unified READ-ONLY safety and quality", start)
    block = text[start:end]
    assert block.count("json.dump(") == 1
    assert "'observed_at': datetime.now(timezone.utc).isoformat()" in block
    assert "'source': 'github-actions:MARSEL Unified Control Plane'" in block
