#!/usr/bin/env python3
"""Check MNIST-derived top-8 sparse EventConv-FC board results."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "outputs" / "runtime" / "mnist_eventconv_fclif_top8_multisample" / "manifest.json"
BOARD_DIR = ROOT / "outputs" / "board" / "mnist_top8_multisample_20260620"
REPORT_PATH = ROOT / "reports" / "spikemold_mnist_top8_board_report.md"
EXPECTED_BIT_SHA = "c307b9b8bfeb7bc33be3ee9275f28130ff5027db012b10e00392078e45257b09"
EXPECTED_HWH_SHA = "2816d9ad88f736ac9b9b6cfa585c817ee606be7bd02a8151b95687061d29d355"
EXPECTED_SCHEMA = "spikemold.mnist_eventconv_fclif_multisample_traces.v1"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check_report() -> None:
    if not REPORT_PATH.exists():
        fail("missing top-8 board report")
    text = REPORT_PATH.read_text(encoding="utf-8")
    for phrase in [
        "MNIST-derived top-8 sparse event samples equivalence only",
        "5 / 5 PASS",
        "Not claimed: full MNIST board accuracy",
        "Not claimed: latency",
        "Not claimed: throughput",
        "Not claimed: energy",
        "Beyond top-8 event budgets remain unproven",
    ]:
        if phrase not in text:
            fail(f"report missing phrase: {phrase}")


def main() -> int:
    manifest = load_json(MANIFEST_PATH)
    if manifest.get("schema") != EXPECTED_SCHEMA:
        fail("manifest schema mismatch")
    if "no_accuracy_latency_throughput_energy" not in str(manifest.get("claim_boundary", "")):
        fail("manifest claim boundary missing")
    if manifest.get("dataset", {}).get("top_k") != 8:
        fail("manifest top_k must be 8")
    samples = manifest.get("samples", [])
    if not isinstance(samples, list) or len(samples) != 5:
        fail("expected exactly 5 top-8 samples")

    for sample in samples:
        if not isinstance(sample, dict):
            fail("sample entry must be mapping")
        if int(sample.get("input_event_count", -1)) != 8:
            fail("top-8 sample must contain 8 input events")
        trace_path = ROOT / str(sample.get("trace_path", ""))
        if not trace_path.exists():
            fail(f"missing trace: {trace_path.relative_to(ROOT)}")
        if sample.get("trace_file_sha256") != sha256_file(trace_path):
            fail(f"trace file sha mismatch: {trace_path.relative_to(ROOT)}")

        board_path = BOARD_DIR / f"{trace_path.stem}_board.json"
        board = load_json(board_path)
        if board.get("ok") is not True or board.get("board_executed") is not True:
            fail(f"board result not ok: {board_path.relative_to(ROOT)}")
        checks = board.get("checks", {})
        if not isinstance(checks, dict) or not all(bool(value) for value in checks.values()):
            fail(f"board checks not all true: {board_path.relative_to(ROOT)}")
        output_words = board.get("output_words", [])
        expected_words = board.get("expected_words", [])
        commit_count = int(sample.get("commit_count", -1))
        if output_words != expected_words:
            fail(f"board output mismatch: {board_path.relative_to(ROOT)}")
        if len(output_words) != commit_count:
            fail(f"board output count mismatch: {board_path.relative_to(ROOT)}")
        config_after = board.get("config_after", {})
        if config_after.get("output_br_drops") != 0:
            fail(f"output bridge drops not zero: {board_path.relative_to(ROOT)}")
        if config_after.get("output_br_events") != commit_count:
            fail(f"output event count mismatch: {board_path.relative_to(ROOT)}")
        if config_after.get("output_br_emits") != commit_count:
            fail(f"output emit count mismatch: {board_path.relative_to(ROOT)}")
        if board.get("bitstream", {}).get("sha256") != EXPECTED_BIT_SHA:
            fail(f"bitstream hash mismatch: {board_path.relative_to(ROOT)}")
        if board.get("hwh", {}).get("sha256") != EXPECTED_HWH_SHA:
            fail(f"HWH hash mismatch: {board_path.relative_to(ROOT)}")

    check_report()
    print("PASS: SpikeMold MNIST top-8 sparse board evidence valid (5 samples)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
