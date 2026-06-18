#!/usr/bin/env python3
"""Generate Markdown evidence from SpikeMold DMA spike smoke JSON."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD_JSON = ROOT / "outputs" / "board" / "dma_spike_smoke_result_20260614.json"
EVENTWORD64_BOARD_JSON = ROOT / "outputs" / "board" / "dma_spike_smoke_eventword64_result_20260614.json"
FLAT_FC_LIF_BOARD_JSON = ROOT / "outputs" / "board" / "flat_fc_lif_trace_smoke_result_20260614.json"
OUT_MD = ROOT / "reports" / "spikemold_dma_spike_smoke_report.md"


def main() -> int:
    result = json.loads(BOARD_JSON.read_text(encoding="utf-8"))
    bitstream = result["bitstream"]
    hwh = result["hwh"]
    route_config = result["route_config"]
    input_spike = result["input_spike"]
    output_spike = result["output_spike"]
    eventword64_lowering = result.get("eventword64_lowering")
    runs = result["runs"]
    config_after = result["config_after"]
    required_checks = result.get("required_checks", result["checks"])
    diagnostic_checks = result.get("diagnostic_checks", {})
    eventword64_result = (
        json.loads(EVENTWORD64_BOARD_JSON.read_text(encoding="utf-8"))
        if EVENTWORD64_BOARD_JSON.exists()
        else None
    )
    eventword64_section = ""
    next_gate = (
        "Run a SpikePress EventWord64-lowered input through this direct RTL path on board, "
        "then extend from one event to tiny flat FC-LIF trace/readout parity."
    )
    if eventword64_result is not None:
        ev_lowering = eventword64_result.get("eventword64_lowering", {})
        ev_config_after = eventword64_result["config_after"]
        ev_output = eventword64_result["output_spike"]
        next_gate = "Extend from EventWord64-lowered one-event board smoke to tiny flat FC-LIF trace/readout parity."
        eventword64_section = f"""
## EventWord64-Lowered Board Result

Result JSON:

`{EVENTWORD64_BOARD_JSON.relative_to(ROOT)}`

| Check | Result |
|---|---:|
| board executed | `{eventword64_result["board_executed"]}` |
| ok | `{eventword64_result["ok"]}` |
| input EventWord64 | `{ev_lowering.get("input_eventword64")}` |
| lowered AXIS32 | `{ev_lowering.get("output_axis32")}` |
| lossless flat input semantics | `{ev_lowering.get("lossless_flat_input_semantics")}` |
| output words | `{ev_output["output_words"]}` |
| router_spike_cnt | `{ev_config_after["router_spike_cnt"]}` |
| neuron_spike_cnt | `{ev_config_after["neuron_spike_cnt"]}` |
| PL busy cycles | `{ev_config_after["pl_busy_cycles"]}` |
| output drain cycles | `{ev_config_after["output_drain_cycles"]}` |
| service cycles | `{ev_config_after["service_cycles"]}` |
| throughput cycles | `{ev_config_after["throughput"]}` |
"""
    if FLAT_FC_LIF_BOARD_JSON.exists():
        next_gate = (
            "Tiny flat FC-LIF commit-value readback is now covered by "
            "`reports/spikemold_flat_fc_lif_trace_smoke_report.md`; next expose "
            "final state readback or extend to EventConv commit payloads."
        )

    status = "passed" if result["ok"] else "failed"
    text = f"""# SpikeMold PYNQ-Z2 DMA Spike Smoke Report

Status: PYNQ-Z2 AXI DMA spike stream smoke {status}

## Evidence Level

`{result["evidence_level"]}`

This is a board execution result. It proves `axi_dma_0` MM2S direct RTL spike
input, minimal RTL router programming, LIF neuron firing, `axi_dma_0` S2MM spike
readback with TLAST, and register/counter readback for one event. It does not
claim SpikePress EventWord64 parity, dataset accuracy, latency, throughput, or
energy.

## Board Result

| Check | Result |
|---|---:|
| board executed | `{result["board_executed"]}` |
| ok | `{result["ok"]}` |
| IP name | `{result["ip_name"]}` |
| DMA name | `{result["dma_name"]}` |
| config IP name | `{result["config_ip_name"]}` |
| reset `ap_done` | `{required_checks["reset_ap_done"]}` |
| spike `ap_done` | `{required_checks["spike_ap_done"]}` |
| HLS version matches | `{required_checks["hls_version_matches"]}` |
| config version matches | `{required_checks["config_version_matches"]}` |
| AXIS input seen nonzero | `{required_checks["axis_input_seen_nonzero"]}` |
| AXIS router accept nonzero | `{required_checks["axis_router_accept_nonzero"]}` |
| router spike count nonzero | `{required_checks["router_spike_count_nonzero"]}` |
| neuron spike count nonzero | `{required_checks["neuron_spike_count_nonzero"]}` |
| output ID matches | `{required_checks["output_id_matches"]}` |
| output commit value matches | `{required_checks["output_commit_value_matches"]}` |
| output word matches | `{required_checks["output_word_matches"]}` |
| output reserved top3 zero | `{required_checks["output_reserved_top3_zero"]}` |

Diagnostic checks:

- output event count nonzero: `{diagnostic_checks.get("output_event_count_nonzero")}`
- output emit count nonzero: `{diagnostic_checks.get("output_emit_count_nonzero")}`

## Route Config

- source_id: `{route_config["source_id"]}`
- dest_id: `{route_config["dest_id"]}`
- route_weight: `{route_config["route_weight"]}`
- threshold: `{route_config["threshold"]}`
- route_addr: `{route_config["route_addr"]}`
- route_word: `{route_config["route_word"]}`
- count_addr: `{route_config["count_addr"]}`

## Spike Words

- input word: `{input_spike["input_word"]}`
- input decoded: `{input_spike["decoded"]}`
- input words sha256: `{input_spike["input_words_sha256"]}`
- output words: `{output_spike["output_words"]}`
- output decoded: `{output_spike["decoded"]}`
- output words sha256: `{output_spike["output_words_sha256"]}`

Run counters/register readback:

- reset polls: `{runs["reset"]["polls"]}`
- spike polls: `{runs["spike"]["polls"]}`
- spike status_reg: `{runs["spike"]["status_reg"]}`
- HLS spike_count_reg: `{runs["spike"]["spike_count_reg"]}`
- router_spike_cnt: `{config_after["router_spike_cnt"]}`
- neuron_spike_cnt: `{config_after["neuron_spike_cnt"]}`
- throughput cycles: `{config_after["throughput"]}`
- service cycles: `{config_after["service_cycles"]}`
- output bridge status: `{config_after["output_br_status"]}`
- output bridge events: `{config_after["output_br_events"]}`
- output bridge emits: `{config_after["output_br_emits"]}`
- PL busy cycles: `{config_after["pl_busy_cycles"]}`
- output drain cycles: `{config_after["output_drain_cycles"]}`

EventWord64 lowering:

`{eventword64_lowering}`

{eventword64_section}

## Artifacts

| Artifact | Size bytes | SHA-256 |
|---|---:|---|
| `{bitstream["path"]}` | `{bitstream["size_bytes"]}` | `{bitstream["sha256"]}` |
| `{hwh["path"]}` | `{hwh["size_bytes"]}` | `{hwh["sha256"]}` |

## Claim Boundary

`{result["claim_boundary"]}`

## Next Gate

{next_gate}
"""
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
