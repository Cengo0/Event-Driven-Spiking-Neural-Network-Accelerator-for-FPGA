#!/usr/bin/env python3
"""Generate Batch 1B SpikeMold transport smoke artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from spikepress import InputSpike, fc_lif_model  # noqa: E402
from spikepress.transport import build_batch_1b_transport_smoke  # noqa: E402


def main() -> int:
    output_dir = ROOT / "outputs" / "transport"
    report_dir = ROOT / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    model = fc_lif_model(
        "batch_1b_tiny_fc_lif",
        weights=[[3, 1], [2, 0]],
        thresholds=[5, 9],
    )
    input_spikes = [
        InputSpike(tick=0, src_id=0),
        InputSpike(tick=1, src_id=1),
        InputSpike(tick=2, src_id=0),
    ]
    smoke = build_batch_1b_transport_smoke(model, input_spikes)
    smoke_path = output_dir / "batch_1b_transport_spikemold_mini_smoke.json"
    smoke_path.write_text(json.dumps(smoke, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    spikemold_mini = smoke["spikemold_mini_fc_lif"]
    counters = spikemold_mini["counters"]
    report = f"""# Batch 1B Transport + SpikeMold-mini Report

Status: software transport smoke generated

## Evidence Level

`{smoke["evidence_level"]}`

Board execution was not run. This report does not claim PYNQ-Z2 PL correctness,
latency, throughput, or energy.

## Generated

- `outputs/transport/batch_1b_transport_spikemold_mini_smoke.json`
- `reports/batch_1b_transport_spikemold_mini_report.md`

## Smoke Results

| Gate | Result |
|---|---:|
| AXI-Lite register smoke | `{smoke["register_smoke"]["ok"]}` |
| DMA loopback smoke | `{smoke["dma_loopback"]["ok"]}` |
| EventWord64 counter smoke | `{smoke["eventword64_counter"]["ok"]}` |
| SpikeMold-mini FC-LIF smoke | `{spikemold_mini["ok"]}` |
| All OK | `{smoke["all_ok"]}` |

## SpikeMold-mini Counters

| Counter | Value |
|---|---:|
| input_event_count | `{counters["input_event_count"]}` |
| update_count | `{counters["update_count"]}` |
| active_count | `{counters["active_count"]}` |
| output_words | `{counters["output_words"]}` |
| dma_calls | `{counters["dma_calls"]}` |
| axi_lite_commands | `{counters["axi_lite_commands"]}` |
| python_inner_loop_steps | `{counters["python_inner_loop_steps"]}` |

## Runtime Assumptions

- bounded job: `{smoke["runtime_assumptions"]["bounded_job"]}`
- Python inner loop required: `{smoke["runtime_assumptions"]["python_inner_loop_required"]}`
- random DDR inner loop: `{smoke["runtime_assumptions"]["random_ddr_inner_loop"]}`
- full-neuron scan primary: `{smoke["runtime_assumptions"]["full_neuron_scan_primary"]}`

## Next Gate

Replace software transport smoke with real PYNQ-Z2 board-captured output and
register counters before making board execution or performance claims.
"""
    (report_dir / "batch_1b_transport_spikemold_mini_report.md").write_text(report, encoding="utf-8")
    return 0 if smoke["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
