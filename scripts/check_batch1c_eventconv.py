#!/usr/bin/env python3
"""Check Batch 1C EventConv C0/C1/C2/C3/C4/C5 artifacts."""

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
SCALE_TRACE_PATH = ROOT / "golden_traces" / "v1" / "eventconv_8x8_tiny_v1.json"
BURST_TRACE_PATH = ROOT / "golden_traces" / "v1" / "eventconv_burst_boundary_v1.json"
REPORT_PATH = ROOT / "reports" / "batch_1c_eventconv_primitive_report.md"
RTL_PATH = ROOT / "hardware" / "hdl" / "rtl" / "core" / "spike_conv_agu.v"
TB_PATH = ROOT / "hardware" / "hdl" / "tb" / "tb_spike_conv_agu.v"
STATE_RTL_PATH = ROOT / "hardware" / "hdl" / "rtl" / "core" / "spike_conv_state_update.v"
STATE_TB_PATH = ROOT / "hardware" / "hdl" / "tb" / "tb_spike_conv_state_update.v"
COMMIT_RTL_PATH = ROOT / "hardware" / "hdl" / "rtl" / "core" / "spike_conv_active_commit.v"
COMMIT_TB_PATH = ROOT / "hardware" / "hdl" / "tb" / "tb_spike_conv_active_commit.v"
SCALE_TB_PATH = ROOT / "hardware" / "hdl" / "tb" / "tb_spike_conv_c4_scaleup.v"
BACKPRESSURE_TB_PATH = ROOT / "hardware" / "hdl" / "tb" / "tb_spike_conv_commit_backpressure.v"


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
        SCALE_TRACE_PATH,
        BURST_TRACE_PATH,
        REPORT_PATH,
        RTL_PATH,
        TB_PATH,
        STATE_RTL_PATH,
        STATE_TB_PATH,
        COMMIT_RTL_PATH,
        COMMIT_TB_PATH,
        SCALE_TB_PATH,
        BACKPRESSURE_TB_PATH,
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
        "output_backpressure_cycle_count",
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
        "C5 readout backpressure",
        "state checksum",
        "active commit readout",
        "reset-to-zero",
        "pynq_axi_dma0_direct_rtl_eventconv_burst_boundary_state_checksum_readback",
        "19 PASS, 0 FAIL",
        "49 PASS, 0 FAIL",
        "31 PASS, 0 FAIL",
    ]:
        if phrase not in report:
            fail(f"report missing phrase: {phrase}")

    check_trace_hashes(trace)

    scale_trace = load_json(SCALE_TRACE_PATH)
    if scale_trace.get("schema") != TRACE_SCHEMA:
        fail("scale trace schema mismatch")
    if scale_trace.get("trace_id") != "eventconv_8x8_tiny_v1":
        fail("scale trace_id mismatch")
    if scale_trace.get("metadata", {}).get("input_shape") != [1, 8, 8]:
        fail("scale input shape mismatch")
    if scale_trace.get("metadata", {}).get("kernel_shape") != [1, 1, 3, 3]:
        fail("scale kernel shape mismatch")
    if scale_trace.get("metadata", {}).get("padding") != 1:
        fail("scale padding mismatch")

    scale_updates = scale_trace.get("updates", [])
    expected_scale_updates = [
        {"dst_id": 36, "weight": 1, "y": 4, "x": 4},
        {"dst_id": 34, "weight": -1, "y": 4, "x": 2},
        {"dst_id": 28, "weight": 2, "y": 3, "x": 4},
        {"dst_id": 26, "weight": -2, "y": 3, "x": 2},
        {"dst_id": 20, "weight": 1, "y": 2, "x": 4},
        {"dst_id": 18, "weight": -1, "y": 2, "x": 2},
        {"dst_id": 45, "weight": 1, "y": 5, "x": 5},
        {"dst_id": 43, "weight": -1, "y": 5, "x": 3},
        {"dst_id": 37, "weight": 2, "y": 4, "x": 5},
        {"dst_id": 35, "weight": -2, "y": 4, "x": 3},
        {"dst_id": 29, "weight": 1, "y": 3, "x": 5},
        {"dst_id": 27, "weight": -1, "y": 3, "x": 3},
    ]
    if len(scale_updates) != len(expected_scale_updates):
        fail(f"scale update count mismatch: {len(scale_updates)}")
    for got, want in zip(scale_updates, expected_scale_updates):
        for key, value in want.items():
            if got.get(key) != value:
                fail(f"scale update mismatch for {key}: got {got.get(key)} want {value}")

    scale_final_state = {int(k): int(v) for k, v in scale_trace.get("final_state", {}).items()}
    expected_scale_state = {
        18: -1,
        20: 1,
        26: -2,
        27: -1,
        28: 2,
        29: 1,
        34: -1,
        35: -2,
        36: 1,
        37: 2,
        43: -1,
        45: 1,
    }
    if scale_final_state != expected_scale_state:
        fail(f"scale final state mismatch: {scale_final_state}")

    scale_counters = scale_trace.get("counters", {})
    expected_scale_counters = {
        "input_event_count": 2,
        "generated_update_count": 12,
        "active_neuron_count": 12,
        "commit_count": 0,
        "state_reads": 12,
        "state_writes": 12,
        "ddr_bytes_inner_loop": 0,
        "python_inner_loop_steps": 0,
    }
    for key, value in expected_scale_counters.items():
        if scale_counters.get(key) != value:
            fail(f"scale counter mismatch for {key}: got {scale_counters.get(key)} want {value}")

    scale_tb = SCALE_TB_PATH.read_text(encoding="utf-8")
    for phrase in [
        "C4 generated twelve signed updates",
        "C4 state[34] negative signed match",
        "C4 high-threshold scans active set only",
        "C4 high-threshold uses no full-neuron scan",
        "*** ALL TESTS PASSED ***",
    ]:
        if phrase not in scale_tb:
            fail(f"scale testbench missing phrase: {phrase}")

    backpressure_tb = BACKPRESSURE_TB_PATH.read_text(encoding="utf-8")
    for phrase in [
        "C5 backpressure holds first commit valid",
        "C5 one-sided commit ready does not duplicate commit",
        "C5 one-sided reset ready does not duplicate reset",
        "C5 commit output count remains exact",
        "C5 reset output count remains exact",
        "C5 records output backpressure cycles",
        "*** ALL TESTS PASSED ***",
    ]:
        if phrase not in backpressure_tb:
            fail(f"backpressure testbench missing phrase: {phrase}")

    report = REPORT_PATH.read_text(encoding="utf-8")
    for phrase in [
        "C4 scale-up",
        "eventconv_8x8_tiny_v1",
        "eventconv_burst_boundary_v1",
        "46 PASS, 0 FAIL",
        "C5 readout backpressure",
        "31 PASS, 0 FAIL",
        "signed 3x3 kernel",
        "Burst-Boundary Active Readout Contract",
        "Invalid boundary taps are skipped",
    ]:
        if phrase not in report:
            fail(f"report missing C4 phrase: {phrase}")

    check_trace_hashes(scale_trace)

    burst_trace = load_json(BURST_TRACE_PATH)
    if burst_trace.get("schema") != TRACE_SCHEMA:
        fail("burst-boundary trace schema mismatch")
    if burst_trace.get("trace_id") != "eventconv_burst_boundary_v1":
        fail("burst-boundary trace_id mismatch")
    burst_meta = burst_trace.get("metadata", {})
    if burst_meta.get("commit_mode") != "packet_end_active_set":
        fail("burst-boundary commit mode mismatch")
    if burst_meta.get("active_neuron_count_after_commit") != 1:
        fail("burst-boundary active count after commit mismatch")
    if burst_meta.get("readout_scan_count") != 4:
        fail("burst-boundary readout scan count mismatch")
    burst_updates = burst_trace.get("updates", [])
    expected_burst_updates = [
        {"dst_id": 3, "weight": 1, "y": 1, "x": 1},
        {"dst_id": 2, "weight": 2, "y": 1, "x": 0},
        {"dst_id": 1, "weight": 3, "y": 0, "x": 1},
        {"dst_id": 0, "weight": 4, "y": 0, "x": 0},
        {"dst_id": 3, "weight": 4, "y": 1, "x": 1},
        {"dst_id": 0, "weight": 1, "y": 0, "x": 0},
    ]
    if len(burst_updates) != len(expected_burst_updates):
        fail(f"burst-boundary update count mismatch: {len(burst_updates)}")
    for got, want in zip(burst_updates, expected_burst_updates):
        for key, value in want.items():
            if got.get(key) != value:
                fail(f"burst-boundary update mismatch for {key}: got {got.get(key)} want {value}")
    expected_burst_commits = [
        {"dst_id": 3, "value": 5},
        {"dst_id": 1, "value": 3},
        {"dst_id": 0, "value": 5},
    ]
    burst_commits = burst_trace.get("commits", [])
    if len(burst_commits) != len(expected_burst_commits):
        fail(f"burst-boundary commit count mismatch: {len(burst_commits)}")
    for got, want in zip(burst_commits, expected_burst_commits):
        for key, value in want.items():
            if got.get(key) != value:
                fail(f"burst-boundary commit mismatch for {key}: got {got.get(key)} want {value}")
    if burst_trace.get("final_state") != {"2": 2}:
        fail("burst-boundary final state mismatch")
    expected_burst_counters = {
        "input_event_count": 3,
        "generated_update_count": 6,
        "active_neuron_count": 4,
        "commit_count": 3,
        "state_reads": 6,
        "state_writes": 9,
        "ddr_bytes_inner_loop": 0,
        "python_inner_loop_steps": 0,
    }
    burst_counters = burst_trace.get("counters", {})
    for key, value in expected_burst_counters.items():
        if burst_counters.get(key) != value:
            fail(f"burst-boundary counter mismatch for {key}: got {burst_counters.get(key)} want {value}")
    check_trace_hashes(burst_trace)

    print("PASS: Batch 1C EventConv C0/C1/C2/C3/C4/C5/burst-boundary artifacts valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
