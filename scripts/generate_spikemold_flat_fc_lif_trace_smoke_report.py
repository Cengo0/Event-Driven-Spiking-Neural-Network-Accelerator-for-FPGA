#!/usr/bin/env python3
"""Generate Markdown evidence from tiny flat FC-LIF board trace JSON."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD_JSON = ROOT / "outputs" / "board" / "flat_fc_lif_trace_smoke_result_20260614.json"
OUT_MD = ROOT / "reports" / "spikemold_flat_fc_lif_trace_smoke_report.md"


def main() -> int:
    result = json.loads(BOARD_JSON.read_text(encoding="utf-8"))
    status = "passed" if result["ok"] else "failed"
    bitstream = result["bitstream"]
    hwh = result["hwh"]
    config = result["config_after"]
    expected = result["expected"]
    output = result["output"]

    text = f"""# SpikeMold PYNQ-Z2 Flat FC-LIF Trace Smoke Report

Status: PYNQ-Z2 tiny flat FC-LIF trace smoke {status}

## Evidence Level

`{result["evidence_level"]}`

This is a board execution result. It proves the current direct RTL AXI DMA path
can consume three SpikePress EventWord64-lowered input spikes, route five
synaptic updates, and emit the expected readout spike id and commit value for
the tiny flat FC-LIF trace. This is commit value readback plus final membrane
checksum readback evidence. Full per-neuron state dump remains outside this
smoke. Counters below are raw board diagnostics only; they are not latency,
throughput, frequency, or energy claims.

## Claim Boundary

`{result["claim_boundary"]}`

## Trace

| Field | Value |
|---|---:|
| input spikes | `{result["input_spikes"]}` |
| EventWord64 words | `{result["input_eventword64"]}` |
| lowered AXIS32 words | `{result["input_axis32"]}` |
| expected generated updates | `{expected["generated_updates"]}` |
| expected readout ids | `{expected["readout_ids"]}` |
| board readout ids | `{output["readout_ids"]}` |
| expected commit values | `{expected["commit_values"]}` |
| board commit values | `{output["commit_values"]}` |
| expected output words | `{expected["output_words"]}` |
| board output words | `{output["output_words"]}` |
| expected final state | `{expected["final_state"]}` |
| expected state checksum | `{expected["state_checksum"]}` |
| board state checksum | `{output["state_checksum"]}` |

## Counters

| Counter | Value |
|---|---:|
| PL busy register / AXIS seen count | `{config["pl_busy_cycles"]}` |
| output drain register / AXIS accept count | `{config["output_drain_cycles"]}` |
| router_spike_cnt | `{config["router_spike_cnt"]}` |
| neuron_spike_cnt | `{config["neuron_spike_cnt"]}` |
| output bridge events | `{config["output_br_events"]}` |
| output bridge emits | `{config["output_br_emits"]}` |
| output bridge drops | `{config["output_br_drops"]}` |
| service cycles | `{config["service_cycles"]}` |
| throughput cycles | `{config["throughput"]}` |

## State Reset Boundary

- fresh overlay loaded: `{result["state_reset_boundary"]["fresh_overlay_loaded"]}`
- membrane state zeroed by: `{result["state_reset_boundary"]["membrane_state_zeroed_by"]}`
- HLS soft reset clears membrane BRAM: `{result["state_reset_boundary"]["hls_soft_reset_clears_membrane_bram"]}`
- state checksum valid after soft reset alone: `{result["state_reset_boundary"]["state_checksum_valid_after_soft_reset"]}`
- state checksum validity: `{result["state_reset_boundary"]["state_checksum_validity"]}`

## Artifacts

| Artifact | Size bytes | SHA-256 |
|---|---:|---|
| `{bitstream["path"]}` | `{bitstream["size_bytes"]}` | `{bitstream["sha256"]}` |
| `{hwh["path"]}` | `{hwh["size_bytes"]}` | `{hwh["sha256"]}` |

## Next Gate

Extend the board path to EventConv commit payloads/checksum, then compare the
EventConv SpikePress golden trace on PYNQ-Z2.
"""
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
