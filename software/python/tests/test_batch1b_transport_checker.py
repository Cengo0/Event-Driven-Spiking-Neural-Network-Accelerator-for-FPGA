import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_batch1b_transport_generator_and_checker_pass():
    generate = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_batch1b_transport_artifacts.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert generate.returncode == 0, generate.stderr + generate.stdout

    check = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_batch1b_transport.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert check.returncode == 0, check.stderr + check.stdout
    assert "PASS: Batch 1B transport + SpikeMold-mini smoke artifacts valid" in check.stdout
