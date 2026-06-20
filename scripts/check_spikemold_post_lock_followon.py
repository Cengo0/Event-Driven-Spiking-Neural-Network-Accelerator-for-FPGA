#!/usr/bin/env python3
"""Check post-lock SpikeMold follow-on report boundaries."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "spikemold_post_lock_followon_report.md"

REQUIRED_PATHS = [
    ROOT / "reports" / "spikemold_eventconv_trace_smoke_report.md",
    ROOT / "reports" / "spikemold_final_goal_report.md",
    ROOT / "reports" / "spikemold_mnist_multisample_board_report.md",
    ROOT / "reports" / "spikemold_mnist_top8_board_report.md",
    ROOT / "outputs" / "runtime" / "mnist_eventconv_fclif_top8_multisample" / "manifest.json",
    ROOT / "outputs" / "board" / "eventconv_desc_tiny_20260620.json",
    ROOT / "outputs" / "board" / "eventconv_desc_burst_boundary_20260620.json",
    ROOT / "outputs" / "board" / "eventconv_fclif_frozen_mnist_10mhz_result_20260620.json",
]

REQUIRED_PHRASES = [
    "Descriptor-configured tiny EventConv board smoke",
    "Fixed MNIST EventConv-FC-LIF board equivalence",
    "MNIST-derived sparse multi-sample board equivalence",
    "MNIST-derived top-8 sparse multi-sample board equivalence",
    "Five MNIST-derived sparse top-3 event sample board equivalence",
    "Five MNIST-derived sparse top-8 event sample board equivalence",
    "Not claimed:",
    "Full MNIST board accuracy",
    "Arbitrary EventConv shape/kernel board support",
    "Latency",
    "Throughput",
    "Energy",
    "Remaining Real Gates",
]

FORBIDDEN_PHRASES = [
    "Full MNIST board accuracy: PASS",
    "arbitrary EventConv shape/kernel support: PASS",
    "latency claim: PASS",
    "throughput claim: PASS",
    "energy claim: PASS",
]


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not REPORT_PATH.exists():
        fail(f"missing report: {REPORT_PATH.relative_to(ROOT)}")
    for path in REQUIRED_PATHS:
        if not path.exists():
            fail(f"missing required evidence: {path.relative_to(ROOT)}")

    text = REPORT_PATH.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            fail(f"report missing phrase: {phrase}")
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text:
            fail(f"report overclaims: {phrase}")

    for path in REQUIRED_PATHS:
        digest = sha256_file(path)
        if digest not in text:
            fail(f"report missing sha256 for {path.relative_to(ROOT)}")

    print("PASS: SpikeMold post-lock follow-on evidence boundaries valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
