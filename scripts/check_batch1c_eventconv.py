#!/usr/bin/env python3
"""Check Batch 1C EventConv C0/C1/C2/C3 artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from spikepress.architecture_trace_generator import TRACE_SCHEMA, sha256_json  # noqa: E402


TRACE_PATH = ROOT / "golden_traces" / "v1" / "eventconv_agu_c0_tiny_v1.json"
REPORT_PATH = ROOT / "reports" / "batch_1c_eventconv_primitive_report.md"
RTL_PATH = ROOT / "hardware" / "hdl" / "rtl" / "core" / "spike_conv_agu.v"
TB_PATH = ROOT / "hardware" / "hdl" / "tb" / "tb_spike_conv_agu.v"
STATE_RTL_PATH = ROOT / "hardware" / "hdl" / "rtl" / "core" / "spike_conv_state_update.v"
STATE_TB_PATH = ROOT / "hardware" / "hdl" / "tb" / "tb_spike_conv_state_update.v"
COMMIT_RTL_PATH = ROOT / "hardware" / "hdl" / "rtl" / "core" / "spike_conv_active_commit.v"
COMMIT_TB_PATH = ROOT / "hardware" / "hdl" / "tb" / "tb_spike_conv_active_commit.v"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - diagnostic path
        fail(f"cannot load JSON {path}: {exc}")


def check_trace_hashes(trace: dict) -> None:
    hashes = trace.get("hashes", {})
    for key, body_key in [
        ("input_sha256", "inputs"),
        ("updates_sha256", "updates"),
        ("commits_sha256", "commits"),
        ("final_state_sha256", "final_state"),
    ]:
        if hashes.get(key) != sha256_json(trace.get(body_key)):
            fail(f"trace hash mismatch: {key}")
    trace_copy = dict(trace)
    trace_copy["hashes"] = dict(hashes)
    expected = trace_copy["hashes"].pop("trace_sha256", None)
    if expected != sha256_json(trace_copy):
        fail("trace_sha256 mismatch")


def main() -> int:
    for path in [
        TRACE_PATH,
        REPORT_PATH,
        RTL_PATH,
        TB_PATH,
        STATE_RTL_PATH,
        STATE_TB_PATH,
        COMMIT_RTL_PATH,
        COMMIT_TB_PATH,
    ]:
        if not path.exists():
            fail(f"missing artifact: {path}")

    trace = load_json(TRACE_PATH)
    if trace.get("schema") != TRACE_SCHEMA:
        fail("trace schema mismatch")
    if trace.get("trace_id") != "eventconv_agu_c0_tiny_v1":
        fail("trace_id mismatch")
    if trace.get("metadata", {}).get("primitive") != "eventconv_agu":
        fail("primitive mismatch")
    if trace.get("metadata", {}).get("weight_storage") != "shared_kernel":
        fail("weight storage mismatch")
    if trace.get("commits") != []:
        fail("C0 tiny trace must have empty commits for C3 high-threshold readout")

    updates = trace.get("updates", [])
    expected = [
        {"dst_id": 3, "weight": 1, "y": 1, "x": 1, "channel": 0},
        {"dst_id": 2, "weight": 2, "y": 1, "x": 0, "channel": 0},
        {"dst_id": 1, "weight": 3, "y": 0, "x": 1, "channel": 0},
        {"dst_id": 0, "weight": 4, "y": 0, "x": 0, "channel": 0},
    ]
    if len(updates) != len(expected):
        fail(f"update count mismatch: {len(updates)}")
    for got, want in zip(updates, expected):
        for key, value in want.items():
            if got.get(key) != value:
                fail(f"update mismatch for {key}: got {got.get(key)} want {value}")

    counters = trace.get("counters", {})
    required_counters = {
        "input_event_count": 1,
        "generated_update_count": 4,
        "active_neuron_count": 4,
        "commit_count": 0,
        "state_reads": 4,
        "state_writes": 4,
        "ddr_bytes_inner_loop": 0,
        "python_inner_loop_steps": 0,
    }
    for key, value in required_counters.items():
        if counters.get(key) != value:
            fail(f"counter mismatch for {key}: got {counters.get(key)} want {value}")

    rtl = RTL_PATH.read_text(encoding="utf-8")
    for token in [
        "module spike_conv_agu",
        "kernel_weight_flat",
        "conv_updates_generated",
        "s_axis_spike_tready",
    ]:
        if token not in rtl:
            fail(f"RTL missing token: {token}")

    tb = TB_PATH.read_text(encoding="utf-8")
    for phrase in [
        "trace-locked destination id",
        "trace-locked weight index",
        "selected shared-kernel weight",
        "*** ALL TESTS PASSED ***",
    ]:
        if phrase not in tb:
            fail(f"testbench missing phrase: {phrase}")

    state_rtl = STATE_RTL_PATH.read_text(encoding="utf-8")
    for token in [
        "module spike_conv_state_update",
        "active_id_flat",
        "state_checksum",
        "active_mask",
        "state_read_count",
        "commit_reset_count",
        "invalid_dest_count",
    ]:
        if token not in state_rtl:
            fail(f"state RTL missing token: {token}")

    state_tb = STATE_TB_PATH.read_text(encoding="utf-8")
    for phrase in [
        "C2 state update consumed four updates",
        "C2 state[0] matches trace",
        "C2 state checksum matches trace",
        "C2 active mask matches trace",
        "C2 no commit resets",
        "*** ALL TESTS PASSED ***",
    ]:
        if phrase not in state_tb:
            fail(f"state testbench missing phrase: {phrase}")

    commit_rtl = COMMIT_RTL_PATH.read_text(encoding="utf-8")
    for token in [
        "module spike_conv_active_commit",
        "active_id_flat",
        "m_axis_reset_tvalid",
        "active_commit_read_count",
        "commit_emit_count",
        "full_scan_count",
        "readout_checksum",
    ]:
        if token not in commit_rtl:
            fail(f"commit RTL missing token: {token}")

    commit_tb = COMMIT_TB_PATH.read_text(encoding="utf-8")
    for phrase in [
        "C3 empty-trace scans active set only",
        "C3 empty-trace emits zero commits",
        "C3 empty-trace uses no full-neuron scan",
        "C3 positive-threshold first commit is dest1 state3",
        "C3 positive-threshold resets state[0]",
        "C3 positive-threshold compacts active count",
        "*** ALL TESTS PASSED ***",
    ]:
        if phrase not in commit_tb:
            fail(f"commit testbench missing phrase: {phrase}")

    report = REPORT_PATH.read_text(encoding="utf-8")
    for phrase in [
        "Batch 1C EventConv Primitive Report",
        "C0 trace-locked tiny case",
        "C1 AGU-only",
        "C2 AGU + state update",
        "C3 AGU + active-set commit",
        "state checksum",
        "active commit readout",
        "reset-to-zero",
        "No board execution was run",
        "19 PASS, 0 FAIL",
        "36 PASS, 0 FAIL",
    ]:
        if phrase not in report:
            fail(f"report missing phrase: {phrase}")

    check_trace_hashes(trace)
    print("PASS: Batch 1C EventConv C0/C1/C2/C3 artifacts valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
