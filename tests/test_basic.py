import subprocess
import sys


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "heartland_harvester.py", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()
