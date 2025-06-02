import csv
import os
import subprocess
import sys


def test_dry_run_creates_csv(tmp_path):
    output = tmp_path / "out.csv"
    result = subprocess.run(
        [sys.executable, "heartland_harvester.py", "--limit", "5", "--dry-run", "--out", str(output)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert output.exists()
    with open(output, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
    assert headers == ["company_name", "source_type", "evidence_url", "evidence_snippet"]
