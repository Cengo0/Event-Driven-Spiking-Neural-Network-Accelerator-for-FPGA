#!/usr/bin/env python3
"""Check Batch 1X architecture sandbox artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from spikepress.architecture_sandbox import ARCHITECTURE_SANDBOX_SCHEMA, sha256_json  # noqa: E402


SANDBOX_PATH = ROOT / "outputs" / "architecture_sandbox" / "batch_1x_architecture_sandbox.json"
REPORT_PATH = ROOT / "reports" / "batch_1x_architecture_sandbox_report.md"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - diagnostic path
        fail(f"cannot load JSON {path}: {exc}")


def check_hash(payload: dict) -> None:
    hashes = dict(payload.get("hashes", {}))
    expected = hashes.pop("architecture_sandbox_sha256", None)
    body = dict(payload)
    if hashes:
        body["hashes"] = hashes
    else:
        body.pop("hashes", None)
    if expected != sha256_json(body):
        fail("architecture sandbox hash mismatch")


def main() -> int:
    for path in [SANDBOX_PATH, REPORT_PATH]:
        if not path.exists():
            fail(f"missing artifact: {path}")

    sandbox = load_json(SANDBOX_PATH)
    if sandbox.get("schema") != ARCHITECTURE_SANDBOX_SCHEMA:
        fail("sandbox schema mismatch")
    if sandbox.get("evidence_level") != "board_free_architecture_sandbox_no_board":
        fail("sandbox evidence level mismatch")
    if sandbox.get("board_executed") is not False:
        fail("sandbox must not claim board execution")
    if sandbox.get("all_ok") is not True:
        fail("sandbox all_ok must be true")
    if sandbox.get("mainline_switch_recommended") is not False:
        fail("board-free sandbox must not recommend mainline switch")

    trace_ids = sandbox.get("trace_ids", [])
    for trace_id in ["fc_lif_tiny_v1", "eventconv_8x8_tiny_v1"]:
        if trace_id not in trace_ids:
            fail(f"missing sandbox trace id: {trace_id}")

    candidates = sandbox.get("candidates", {})
    expected_candidates = {
        "coregroup_2x64": "coregroup_partition",
        "page_block_256_updates": "page_block_sparse_execution",
        "tile_microbatch_4x4": "tile_microbatch",
    }
    for candidate_id, pattern in expected_candidates.items():
        candidate = candidates.get(candidate_id)
        if not isinstance(candidate, dict):
            fail(f"missing candidate: {candidate_id}")
        if candidate.get("pattern") != pattern:
            fail(f"candidate pattern mismatch: {candidate_id}")

        for check in candidate.get("correctness", []):
            if check.get("trace_match_rate") != 1.0:
                fail(f"{candidate_id} trace_match_rate mismatch")
            if check.get("readout_match") is not True:
                fail(f"{candidate_id} readout mismatch")
            if check.get("state_checksum_match") is not True:
                fail(f"{candidate_id} state checksum mismatch")

        probation = candidate.get("probation", {})
        expected_probation = {
            "event_triggered_semantics": True,
            "golden_trace_correctness": True,
            "python_inner_loop_required": False,
            "random_ddr_inner_loop": False,
            "full_neuron_scan_primary": False,
            "bounded_bram_layout": True,
            "silent_semantic_change": False,
        }
        for key, value in expected_probation.items():
            if probation.get(key) != value:
                fail(f"{candidate_id} probation mismatch for {key}")

        resource = candidate.get("resource_report", {})
        memory = candidate.get("memory_estimate", {})
        runtime = candidate.get("runtime_estimate", {})
        performance = candidate.get("performance_estimate", {})
        if resource.get("dsp_estimate") != 0:
            fail(f"{candidate_id} must remain DSP-free")
        if memory.get("ddr_bytes_inner_loop") != 0:
            fail(f"{candidate_id} must keep inner-loop DDR bytes at zero")
        if runtime.get("python_calls_per_inference") != 0:
            fail(f"{candidate_id} must not require Python inner-loop calls")
        if int(performance.get("cycle_count_estimate", 0)) <= 0:
            fail(f"{candidate_id} missing positive cycle estimate")
        if not resource.get("compile_time_rejection_rules"):
            fail(f"{candidate_id} missing compile-time rejection rules")

    page_memory = candidates["page_block_256_updates"]["memory_estimate"]
    if page_memory.get("ddr_bursts", 0) <= 0:
        fail("page/block candidate must report burst traffic estimate")
    if page_memory.get("ddr_bytes", 0) <= 0:
        fail("page/block candidate must report DDR byte estimate")

    check_hash(sandbox)

    report = REPORT_PATH.read_text(encoding="utf-8")
    for phrase in [
        "board_free_architecture_sandbox_no_board",
        "coregroup_2x64",
        "page_block_256_updates",
        "tile_microbatch_4x4",
        "trace_match_rate: `1.0`",
        "python_inner_loop_required: `False`",
        "random_ddr_inner_loop: `False`",
        "mainline_switch_recommended",
        "not enough to replace the mainline",
    ]:
        if phrase not in report:
            fail(f"report missing phrase: {phrase}")

    print("PASS: Batch 1X architecture sandbox artifacts valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
