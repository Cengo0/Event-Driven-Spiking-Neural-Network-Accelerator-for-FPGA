#!/usr/bin/env python3
"""Check architecture selection report and backing board-free artifacts."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "architecture_selection_v1.md"
BUDGET_PATH = ROOT / "outputs" / "event_budget" / "recommended_ednp_mini_config.json"
TRANSPORT_PATH = ROOT / "outputs" / "transport" / "batch_1b_transport_ednp_mini_smoke.json"
C4_TRACE_PATH = ROOT / "golden_traces" / "v1" / "eventconv_8x8_tiny_v1.json"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - diagnostic path
        fail(f"cannot load JSON {path}: {exc}")


def require_text(text: str, phrases: list[str]) -> None:
    for phrase in phrases:
        if phrase not in text:
            fail(f"report missing phrase: {phrase}")


def main() -> int:
    for path in [REPORT_PATH, BUDGET_PATH, TRANSPORT_PATH, C4_TRACE_PATH]:
        if not path.exists():
            fail(f"missing artifact: {path}")

    report = REPORT_PATH.read_text(encoding="utf-8")
    require_text(
        report,
        [
            "# Architecture Selection V1",
            "board_free_architecture_selection_no_board",
            "## 1. Candidates Tested",
            "## 2. Trace Version Used",
            "## 3. Workloads Used",
            "## 4. Resource Estimate Table",
            "## 5. Performance Estimate Table",
            "## 6. Runtime Complexity Table",
            "## 7. Winner",
            "## 8. Rejected Candidates And Why",
            "## 9. Recommended Next Implementation Stage",
            "trace_match_rate",
            "readout_match",
            "state_checksum_match",
            "LUT estimate",
            "FF estimate",
            "BRAM estimate",
            "DSP estimate",
            "FIFO memory",
            "max clock estimate",
            "cycles per input event",
            "cycles per generated update",
            "cycles per active commit",
            "maximum supported event count",
            "stall count",
            "state reads",
            "state writes",
            "DDR bursts",
            "DDR bytes",
            "BRAM bytes",
            "state memory bytes",
            "synapse/kernel memory bytes",
            "FIFO memory bytes",
            "expected DDR bytes per inference",
            "expected DMA calls per inference",
            "expected AXI-Lite commands per inference",
            "event/update histogram",
            "DMA calls per inference",
            "AXI-Lite commands per inference",
            "Python calls per inference",
            "E hybrid backend",
            "Probation And Failure-Mode Checks",
            "python_inner_loop_steps = 0",
            "ddr_bytes_inner_loop = 0",
            "If `trace_match_rate < 1.0`, reject candidate.",
            "No board execution was run",
        ],
    )

    budget = load_json(BUDGET_PATH)
    if budget.get("schema") != "spikemold.ednp_event_budget.v1":
        fail("event budget schema mismatch")
    if budget.get("all_ok") is not True:
        fail("event budget all_ok is not true")
    histogram = budget.get("counter_histogram", {})
    if histogram.get("generated_update_count", {}).get("max") != 12:
        fail("event budget max generated_update_count must be 12")
    if histogram.get("ddr_bytes_inner_loop", {}).get("max") != 0:
        fail("event budget must keep inner-loop DDR bytes at zero")
    if histogram.get("python_inner_loop_steps", {}).get("max") != 0:
        fail("event budget must keep Python inner-loop steps at zero")

    transport = load_json(TRANSPORT_PATH)
    if transport.get("all_ok") is not True:
        fail("transport smoke all_ok is not true")
    if transport.get("board_executed") is not False:
        fail("architecture report must not rely on board execution")
    ednp = transport.get("ednp_mini_fc_lif", {})
    if ednp.get("trace_match_rate") != 1.0:
        fail("EDNP-mini trace_match_rate is not 1.0")
    if ednp.get("readout_match") is not True:
        fail("EDNP-mini readout_match is not true")
    if ednp.get("state_checksum_match") is not True:
        fail("EDNP-mini state_checksum_match is not true")
    counters = ednp.get("counters", {})
    if counters.get("dma_calls") != 2:
        fail("EDNP-mini DMA call estimate mismatch")
    if counters.get("axi_lite_commands") != 8:
        fail("EDNP-mini AXI-Lite command estimate mismatch")
    if counters.get("python_inner_loop_steps") != 0:
        fail("EDNP-mini Python inner-loop count must be zero")

    c4 = load_json(C4_TRACE_PATH)
    if c4.get("trace_id") != "eventconv_8x8_tiny_v1":
        fail("C4 trace_id mismatch")
    c4_counters = c4.get("counters", {})
    expected = {
        "input_event_count": 2,
        "generated_update_count": 12,
        "active_neuron_count": 12,
        "commit_count": 0,
        "state_reads": 12,
        "state_writes": 12,
        "ddr_bytes_inner_loop": 0,
        "python_inner_loop_steps": 0,
    }
    for key, value in expected.items():
        if c4_counters.get(key) != value:
            fail(f"C4 counter mismatch for {key}: got {c4_counters.get(key)} want {value}")

    print("PASS: Architecture selection V1 report valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
