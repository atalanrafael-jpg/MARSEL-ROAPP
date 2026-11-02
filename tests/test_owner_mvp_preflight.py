import subprocess
import sys
from pathlib import Path


def test_preflight_accepts_the_existing_russian_owner_login_heading():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "scripts/marsel_owner_mvp_preflight.py")],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
