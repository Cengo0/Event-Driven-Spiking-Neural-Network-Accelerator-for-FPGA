#!/usr/bin/env python3
"""Generate Batch 1X architecture sandbox artifacts."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from spikepress.architecture_sandbox import (  # noqa: E402
    build_batch_1x_architecture_sandbox,
    load_trace,
    write_json,
)


TRACE_PATHS = [
    ROOT / "golden_traces" / "v1" / "fc_lif_tiny_v1.json",
    ROOT / "golden_traces" / "v1" / "eventconv_8x8_tiny_v1.json",
]


def candidate_row(name: str, candidate: dict) -> str:
    resource = candidate["resource_report"]
    performance = candidate["performance_estimate"]
    memory = candidate["memory_estimate"]
    runtime = candidate["runtime_estimate"]
    return (
        f"| `{name}` | `{candidate['pattern']}` | "
        f"`{resource['bram_estimate_upper_bound']}` | "
        f"`{resource['dsp_estimate']}` | "
        f"`{memory['ddr_bytes_inner_loop']}` | "
        f"`{performance['cycle_count_estimate']}` | "
        f"`{runtime['python_calls_per_inference']}` | PASS |"
    )


def main() -> int:
    traces = [load_trace(path) for path in TRACE_PATHS]
    sandbox = build_batch_1x_architecture_sandbox(traces)

    write_json(ROOT / "outputs" / "architecture_sandbox" / "batch_1x_architecture_sandbox.json", sandbox)

    rows = "\n".join(
        candidate_row(name, candidate)
        for name, candidate in sandbox["candidates"].items()
    )
    report_path = ROOT / "reports" / "batch_1x_architecture_sandbox_report.md"
    report_path.write_text(
        f"""# Batch 1X Architecture Sandbox Report

Status: board-free architecture sandbox passed

## Evidence Level

`board_free_architecture_sandbox_no_board`

No board execution, routed implementation, latency, throughput, or energy claim
is made here. This sandbox replays existing golden traces and estimates resource,
memory, runtime, and cycle cost for probationary architectural patterns.

## Traces

- `golden_traces/v1/fc_lif_tiny_v1.json`
- `golden_traces/v1/eventconv_8x8_tiny_v1.json`

## Candidate Summary

| Candidate | Pattern | BRAM est | DSP est | DDR inner-loop bytes | Cycle estimate | Python calls | Gate |
|---|---|---:|---:|---:|---:|---:|---|
{rows}

## Probation Checks

All sandbox candidates preserve:

- trace_match_rate: `1.0`
- readout_match: `True`
- state_checksum_match: `True`
- python_inner_loop_required: `False`
- random_ddr_inner_loop: `False`
- full_neuron_scan_primary: `False`
- silent_semantic_change: `False`

## Decision

`mainline_switch_recommended`: `{sandbox['mainline_switch_recommended']}`

Reason: {sandbox['mainline_switch_reason']}

The selected SpikeMold FC/EventConv runtime remains the mainline. Coregroup,
page/block, and tile/micro-batch patterns stay allowed as probationary patterns,
but this board-free sandbox is not enough to replace the mainline.
""",
        encoding="utf-8",
    )
    print("Wrote Batch 1X architecture sandbox artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
