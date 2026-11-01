"""Regression tests: inventory must distinguish real producers from mentions."""

from scripts.marsel_evidence_producer_inventory_v1 import is_direct_producer


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
