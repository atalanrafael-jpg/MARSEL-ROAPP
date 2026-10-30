from pathlib import Path


def test_owner_preflight_triggers_when_its_workflow_changes():
    workflow = Path(".github/workflows/marsel-owner-mvp-preflight.yml").read_text(encoding="utf-8")
    assert '".github/workflows/marsel-owner-mvp-preflight.yml"' in workflow


def test_owner_preflight_test_script_is_a_literal_multiline_shell_block():
    workflow = Path(".github/workflows/marsel-owner-mvp-preflight.yml").read_text(encoding="utf-8")
    assert "      - name: Run tests when present\n        shell: bash\n        run: |\n" in workflow
