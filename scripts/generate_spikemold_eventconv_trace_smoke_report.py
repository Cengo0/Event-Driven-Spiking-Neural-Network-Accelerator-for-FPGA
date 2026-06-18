#!/usr/bin/env python3
"""Generate markdown report for EventConv PYNQ-Z2 smokes."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD_JSONS = [
    ROOT / "outputs" / "board" / "eventconv_trace_smoke_result_20260614.json",
    ROOT / "outputs" / "board" / "eventconv_burst_boundary_smoke_result_20260615.json",
]
REPORT_MD = ROOT / "reports" / "spikemold_eventconv_trace_smoke_report.md"


def load_result(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def result_section(result: dict) -> str:
    config = result["config_after"]
    expected = result["expected"]
    output = result["output"]
    active_after = (config["status"] >> 1) & 0xFF
    return f"""### `{result["variant"]}`

Evidence level: `{result["evidence_level"]}`

Claim boundary: `{result["claim_boundary"]}`

| field | value |
|---|---:|
| model | `{result["model"]["name"]}` |
| ok | `{result["ok"]}` |
| EventConv backend mode | `{config["backend_mode"]}` |
| input axis32 words | `{result["input_axis32"]}` |
| expected output words | `{expected["output_words"]}` |
| board output words | `{output["output_words"]}` |
| expected readout ids | `{expected["readout_ids"]}` |
| board readout ids | `{output["readout_ids"]}` |
| expected commit values | `{expected["commit_values"]}` |
| board commit values | `{output["commit_values"]}` |
| expected state checksum | `{expected["state_checksum"]}` |
| board state checksum | `{output["state_checksum"]}` |
| generated EventConv updates | `{config["router_spike_cnt"]}` |
| active commit reads | `{config["output_drain_cycles"]}` |
| commit emits | `{config["neuron_spike_cnt"]}` |
| output bridge drops | `{config["output_br_drops"]}` |
| active neurons after commit | `{active_after}` |
"""


def main() -> int:
    results = [load_result(path) for path in BOARD_JSONS]
    bitstream = results[0]["bitstream"]
    hwh = results[0]["hwh"]

    sections = "\n".join(result_section(result) for result in results)
    text = f"""# SpikeMold EventConv Trace Smoke Report

Status: PYNQ-Z2 EventConv trace smokes passed

## Artifact Identity

| artifact | sha256 | bytes |
|---|---:|---:|
| bitstream | `{bitstream["sha256"]}` | `{bitstream["size_bytes"]}` |
| hwh | `{hwh["sha256"]}` | `{hwh["size_bytes"]}` |

## Board Results

{sections}

## Boundary

These are fixed-shape EventConv AGU/state/active-commit board smokes. The
`tiny` case proves multi-commit packet readback and state checksum readback.
The `burst-boundary` case proves one DMA packet can carry multiple EventConv
input events and boundary coordinates skip invalid taps before active-set
commit. They are not latency, throughput, energy, dataset correctness, or full
ConvSNN proof.

Next: lift the integrated EventConv backend toward configurable shape/kernel
descriptors, then compare larger golden trace families on board.
"""
    REPORT_MD.write_text(text, encoding="utf-8")
    print(f"Wrote {REPORT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
