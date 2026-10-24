"""Regression tests: inventory must distinguish real producers from mentions."""

from scripts.marsel_evidence_producer_inventory_v1 import is_direct_producer


def test_filename_mention_in_test_is_not_a_producer():
    source = 'assert "backup_evidence.json" in workflow_text'
    assert not is_direct_producer(source, "backup_evidence.json")


def test_explicit_file_write_is_a_producer():
    source = 'Path("backup_evidence.json").write_text(payload)'
    assert is_direct_producer(source, "backup_evidence.json")


def test_artifact_upload_path_is_not_a_producer():
    source = "path: artifacts/backup_evidence.json"
    assert not is_direct_producer(source, "backup_evidence.json")
