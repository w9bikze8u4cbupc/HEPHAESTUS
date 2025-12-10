from pathlib import Path
import subprocess
import sys


def test_cli_help_runs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "hephaestus.cli", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "pdf_path" in result.stdout