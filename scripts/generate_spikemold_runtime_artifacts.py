#!/usr/bin/env python3
"""Generate SpikeMold runtime contract and resource artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from spikepress.spikemold_runtime_contract import (  # noqa: E402
    build_spikemold_runtime_contract,
    build_spikemold_runtime_resource_report,
    load_spikemold_runtime_inputs,
    write_json,
)


def load_optional_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    event_budget, transport_smoke, eventconv_trace = load_spikemold_runtime_inputs(ROOT)
    eventconv_ooc_synthesis = load_optional_json(
        ROOT / "outputs" / "resource" / "eventconv_ooc_synthesis_report.json"
    )
    runtime_contract = build_spikemold_runtime_contract(
        event_budget=event_budget,
        transport_smoke=transport_smoke,
        eventconv_trace=eventconv_trace,
    )
    resource_report = build_spikemold_runtime_resource_report(
        event_budget=event_budget,
        transport_smoke=transport_smoke,
        eventconv_trace=eventconv_trace,
        runtime_contract=runtime_contract,
        eventconv_ooc_synthesis=eventconv_ooc_synthesis,
    )

    write_json(ROOT / "outputs" / "runtime" / "spikemold_runtime_contract.json", runtime_contract)
    write_json(ROOT / "outputs" / "resource" / "spikemold_runtime_resource_report.json", resource_report)

    report_path = ROOT / "reports" / "spikemold_runtime_resource_report.md"
    report_path.write_text(
        """# SpikeMold Runtime Contract And Resource Report

Status: board-free runtime/resource artifacts generated

## Evidence Level

- runtime contract: `board_free_runtime_contract_no_board`
- resource report: `board_free_resource_report_with_eventconv_ooc_synthesis`

No board execution was run. This report does not claim PYNQ-Z2 PL correctness,
latency, throughput, or energy.

## Generated

- `outputs/runtime/spikemold_runtime_contract.json`
- `outputs/resource/spikemold_runtime_resource_report.json`

## Selected Backend

`spikemold_fc_eventconv`

The runtime contract exposes two SpikeMold runtime blocks:

- `flat_fc_lif`: small FC/readout path
- `eventconv_agu`: shared-kernel EventConv AGU plus near-memory state and active-set commit

## Required Runtime Invariants

- bounded job: `True`
- Python inner loop required: `False`
- random DDR inner loop: `False`
- full-neuron scan primary: `False`
- active-set commit required: `True`

## Resource Evidence

The resource report is compiler-visible. Flat FC-LIF remains contract-level
because no standalone flat FC-LIF RTL primitive exists; EventConv has Vivado OOC
synthesis evidence at 20 MHz.

| Primitive | State bytes | Kernel/weight bytes | FIFO bytes | DDR inner-loop bytes | Synthesis evidence |
|---|---:|---:|---:|---:|---|
| flat_fc_lif | `8` | `4` | `512` | `0` | contract/HLS-integrated path only |
| eventconv_agu | `128` | `9` | `512` | `0` | `outputs/resource/eventconv_ooc_synthesis_report.json` |

Both selected blocks use the minimal transport model estimate of two DMA
calls and eight AXI-Lite commands per bounded inference. This is a contract
estimate, not a board measurement.

## EventConv OOC Synthesis

The EventConv C4 RTL blocks synthesize out-of-context on
`xc7z020clg400-1` at 20 MHz with zero DSP and zero BRAM tile usage. This is not
routed implementation evidence and does not prove board execution.

## Next Gate

Build the integrated bitstream/runtime contract and run PYNQ-Z2 board smoke.
""",
        encoding="utf-8",
    )
    print("Wrote SpikeMold runtime contract and resource artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
