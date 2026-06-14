#!/usr/bin/env python3
"""Check EventConv Vivado OOC synthesis evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = ROOT / "outputs" / "resource" / "eventconv_ooc_synthesis_report.json"
REPORT_MD = ROOT / "reports" / "eventconv_ooc_synthesis_report.md"
SCHEMA = "spikemold.eventconv_ooc_synthesis.v1"
REQUIRED = [
    "eventconv_agu_c4",
    "eventconv_state_update_c4",
    "eventconv_active_commit_c4",
]


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        fail(f"cannot load JSON {path}: {exc}")


def check_hash(payload: dict) -> None:
    body = dict(payload)
    hashes = dict(body.pop("hashes", {}))
    if hashes.get("synthesis_report_sha256") != sha256_json(body):
        fail("synthesis_report_sha256 mismatch")


def main() -> int:
    if not REPORT_JSON.exists():
        fail(f"missing JSON report: {REPORT_JSON}")
    if not REPORT_MD.exists():
        fail(f"missing Markdown report: {REPORT_MD}")

    report = load_json(REPORT_JSON)
    if report.get("schema") != SCHEMA:
        fail("schema mismatch")
    if report.get("evidence_level") != "vivado_ooc_synthesis_no_board":
        fail("evidence level mismatch")
    if report.get("board_executed") is not False:
        fail("must not claim board execution")
    if report.get("target_clock_mhz") != 20.0:
        fail("target clock must be 20 MHz for conservative OOC gate")
    if report.get("all_blocks_synthesized") is not True:
        fail("all_blocks_synthesized must be true")
    if report.get("all_timing_met") is not True:
        fail("all_timing_met must be true")
    if report.get("all_dsp_zero") is not True:
        fail("all_dsp_zero must be true")
    if report.get("all_bram_tile_zero") is not True:
        fail("all_bram_tile_zero must be true")
    if report.get("claim_boundary") != "eventconv_ooc_synthesis_only_no_bitstream_no_board":
        fail("claim boundary mismatch")

    eventconv_blocks = report.get("eventconv_blocks", {})
    if not isinstance(eventconv_blocks, Mapping):
        fail("eventconv_blocks must be a mapping")
    for name in REQUIRED:
        block = eventconv_blocks.get(name)
        if not isinstance(block, Mapping):
            fail(f"missing EventConv block: {name}")
        utilization = block.get("utilization", {})
        timing = block.get("timing", {})
        if not isinstance(utilization, Mapping) or not isinstance(timing, Mapping):
            fail(f"{name} utilization/timing malformed")
        if utilization.get("dsp", {}).get("used") != 0:
            fail(f"{name} uses DSP")
        if timing.get("timing_met") is not True:
            fail(f"{name} timing not met")
        if float(timing.get("wns_ns", -999.0)) < 0.0:
            fail(f"{name} negative WNS")
        for key, hash_key in [
            ("utilization", "utilization_sha256"),
            ("timing", "timing_sha256"),
            ("checkpoint", "checkpoint_sha256"),
        ]:
            rel = block.get("reports", {}).get(key)
            expected = block.get("hashes", {}).get(hash_key)
            if not rel or not expected:
                fail(f"{name} missing report/hash for {key}")
            path = ROOT / str(rel)
            if not path.exists():
                fail(f"{name} missing report file: {rel}")
            if sha256_file(path) != expected:
                fail(f"{name} hash mismatch for {key}")

    aggregate = report.get("aggregate_utilization", {})
    if aggregate.get("dsp_used") != 0:
        fail("aggregate DSP must be zero")
    if aggregate.get("block_ram_tile_used") != 0:
        fail("aggregate BRAM tile must be zero for current C4 OOC primitives")
    if float(aggregate.get("min_wns_ns", -999.0)) < 0.0:
        fail("aggregate min WNS must be nonnegative")
    check_hash(report)

    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in [
        "EventConv Vivado OOC synthesis evidence generated",
        "No board execution was run",
        "eventconv_ooc_synthesis_only_no_bitstream_no_board",
    ]:
        if phrase not in text:
            fail(f"Markdown report missing phrase: {phrase}")

    print("PASS: EventConv Vivado OOC synthesis evidence valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
