#!/usr/bin/env python3
"""Generate initial EDNP Batch 1A golden traces and event budget artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from spikepress.architecture_trace_generator import (  # noqa: E402
    InputSpike,
    generate_eventconv_trace,
    generate_fc_lif_trace,
)
from spikepress.event_budget import summarize_trace_budgets  # noqa: E402


def main() -> int:
    golden_dir = ROOT / "golden_traces" / "v1"
    event_budget_dir = ROOT / "outputs" / "event_budget"
    report_dir = ROOT / "reports"
    golden_dir.mkdir(parents=True, exist_ok=True)
    event_budget_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    fc_trace = generate_fc_lif_trace(
        input_spikes=[
            InputSpike(tick=0, src_id=0),
            InputSpike(tick=1, src_id=1),
            InputSpike(tick=2, src_id=0),
        ],
        weights={(0, 10): 3, (0, 11): 1, (1, 10): 2},
        thresholds={10: 5, 11: 9},
        trace_id="fc_lif_tiny_v1",
    )
    fc_trace.write_json(golden_dir / "fc_lif_tiny_v1.json")

    eventconv_trace = generate_eventconv_trace(
        input_spikes=[
            InputSpike(tick=0, src_id=0, y=3, x=3, channel=0),
            InputSpike(tick=1, src_id=1, y=4, x=4, channel=0),
        ],
        kernel=[[[[1, 0, -1], [2, 0, -2], [1, 0, -1]]]],
        input_shape=(1, 8, 8),
        stride=1,
        padding=1,
        thresholds={27: 4},
        trace_id="eventconv_8x8_tiny_v1",
    )
    eventconv_trace.write_json(golden_dir / "eventconv_8x8_tiny_v1.json")

    budget = summarize_trace_budgets(
        {
            "fc_lif_tiny_v1": fc_trace.to_dict(),
            "eventconv_8x8_tiny_v1": eventconv_trace.to_dict(),
        }
    )
    (event_budget_dir / "recommended_m3_config.json").write_text(
        json.dumps(budget, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report = """# Batch 1A Software Foundation Report

Status: initial artifacts generated

## Generated

- `golden_traces/v1/fc_lif_tiny_v1.json`
- `golden_traces/v1/eventconv_8x8_tiny_v1.json`
- `outputs/event_budget/recommended_m3_config.json`
- `software/python/spikepress/`

## Evidence Level

Integer golden trace generation only. No HLS, RTL, or board claim.

## Current Scope

- FC-LIF tiny deterministic trace
- shared-kernel EventConv AGU tiny deterministic trace
- event/update/active/state counter budget
- inference-only SpikePress API and compiler artifact path
- event counter histogram
- compiler artifact JSON roundtrip

## Remaining Batch 1A Work

- verifier gate review
"""
    (report_dir / "batch_1a_software_foundation_report.md").write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
