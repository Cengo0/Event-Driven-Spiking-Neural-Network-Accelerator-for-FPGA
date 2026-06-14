import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_ednp_batch0_1a_checker_passes():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_ednp_batch0_1a.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "PASS: EDNP Batch 0 + initial Batch 1A artifacts valid" in result.stdout


def test_verifier_gate_checker_passes():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_verifier_gate.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "PASS: verifier gate review artifacts valid" in result.stdout
