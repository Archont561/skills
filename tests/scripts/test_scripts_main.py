"""python -m scripts shows the Typer CLI help (and discovers commands)."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_python_m_scripts_prints_cli_help():
    proc = subprocess.run(
        [sys.executable, "-m", "scripts"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "Usage" in proc.stdout


def test_cli_discovers_lint_command():
    proc = subprocess.run(
        [sys.executable, "-m", "scripts", "--help"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "lint" in proc.stdout
