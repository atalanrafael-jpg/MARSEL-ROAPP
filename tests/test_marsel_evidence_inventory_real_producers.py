"""Regression tests: inventory must distinguish real producers from mentions."""

from scripts.marsel_evidence_producer_inventory_v1 import classify_inventory_rows, is_direct_producer


def test_filename_mention_is_not_a_producer():
    source = 'assert "backup_evidence.json" in workflow_text'
    assert not is_direct_producer(source, "backup_evidence.json")


def test_filename_mention_in_test_is_not_a_producer():
    source = 'test_path = "backup_evidence.json"'
    assert not is_direct_producer(source, "backup_evidence.json")


def test_explicit_file_write_is_a_producer():
    source = 'Path("backup_evidence.json").write_text(payload)'
    assert is_direct_producer(source, "backup_evidence.json")


def test_open_write_mode_is_a_producer():
    source = 'open("evidence/backup_evidence.json", "w")'
    assert is_direct_producer(source, "backup_evidence.json")


def test_artifact_upload_path_is_not_a_producer():
    source = "path: artifacts/backup_evidence.json"
    assert not is_direct_producer(source, "backup_evidence.json")


def test_environment_configured_pathlib_output_is_a_producer():
    source = '''
import os
from pathlib import Path
OUTPUT = Path(os.environ.get("MARSEL_BACKUP_EVIDENCE_OUTPUT", "backup_evidence.json"))
OUTPUT.write_text(payload, encoding="utf-8")
'''
    assert is_direct_producer(source, "backup_evidence.json")


def test_environment_configured_nested_output_path_is_a_producer():
    source = '''
import os
from pathlib import Path
OUT = Path(os.environ.get("MARSEL_RESTORE_EVIDENCE_OUTPUT", "evidence/restore_evidence.json"))
OUT.write_text(payload, encoding="utf-8")
'''
    assert is_direct_producer(source, "restore_evidence.json")


def test_environment_output_assignment_without_write_is_not_a_producer():
    source = '''
import os
from pathlib import Path
OUTPUT = Path(os.environ.get("MARSEL_BACKUP_EVIDENCE_OUTPUT", "backup_evidence.json"))
print(OUTPUT)
'''
    assert not is_direct_producer(source, "backup_evidence.json")


def test_missing_artifact_is_not_misreported_as_missing_producer():
    rows = [
        {"evidence": "backup_evidence.json", "file_present": False, "producer_count": 1},
        {"evidence": "wix_roapp_reconciliation.json", "file_present": True, "producer_count": 0},
    ]
    result = classify_inventory_rows(rows)
    assert result["missing_evidence"] == ["backup_evidence.json"]
    assert result["missing_producers"] == ["wix_roapp_reconciliation.json"]
    assert result["incomplete"] == ["backup_evidence.json", "wix_roapp_reconciliation.json"]


def test_existing_file_with_no_producer_remains_incomplete():
    rows = [{"evidence": "rollback_evidence.json", "file_present": True, "producer_count": 0}]
    result = classify_inventory_rows(rows)
    assert result["missing_evidence"] == []
    assert result["missing_producers"] == ["rollback_evidence.json"]
    assert result["incomplete"] == ["rollback_evidence.json"]
