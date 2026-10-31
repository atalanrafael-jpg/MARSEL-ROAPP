from pathlib import Path


def test_public_repository_guard_runs_before_credentials_and_backup_export():
    workflow = Path(
        ".github/workflows/marsel-backup-evidence-producer.yml"
    ).read_text(encoding="utf-8")

    guard = workflow.index("Block raw backup export from a public repository")
    dependency_install = workflow.index("Install dependencies")
    secret_check = workflow.index("Verify RO App secret")
    full_export = workflow.index("Run full READ-ONLY export")

    assert guard < dependency_install < secret_check < full_export
    assert "REPOSITORY_PRIVATE" in workflow
    assert "REPOSITORY_PRIVATE: ${{ github.event.repository.private }}" in workflow
    assert 'if [ "$REPOSITORY_PRIVATE" != "true" ]; then' in workflow
    assert "BACKUP_EXPORT_BLOCKED=PUBLIC_REPOSITORY" in workflow
    assert "exit 2" in workflow


def test_backup_and_restore_artifacts_have_seven_day_retention():
    workflow = Path(
        ".github/workflows/marsel-backup-evidence-producer.yml"
    ).read_text(encoding="utf-8")

    assert workflow.count("retention-days: 7") == 2
    assert "retention-days: 90" not in workflow
