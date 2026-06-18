#!/usr/bin/env python3
"""Generate Batch 1B SpikeMold transport smoke artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
BOARD_SMOKE_JSON = ROOT / "outputs" / "board" / "dma_spike_smoke_result_20260614.json"
EVENTWORD64_BOARD_SMOKE_JSON = (
    ROOT / "outputs" / "board" / "dma_spike_smoke_eventword64_result_20260614.json"
)
FLAT_FC_LIF_BOARD_SMOKE_JSON = ROOT / "outputs" / "board" / "flat_fc_lif_trace_smoke_result_20260614.json"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from spikepress import InputSpike, fc_lif_model  # noqa: E402
from spikepress.transport import build_batch_1b_transport_smoke  # noqa: E402


def load_board_smoke(path: Path) -> dict | None:
    if not path.exists():
        return None
    result = json.loads(path.read_text(encoding="utf-8"))
    config_after = result.get("config_after", {})
    output_spike = result.get("output_spike", {})
    checks = result.get("required_checks", result.get("checks", {}))
    return {
        "path": str(path.relative_to(ROOT)),
        "schema": result.get("schema"),
        "evidence_level": result.get("evidence_level"),
        "claim_boundary": result.get("claim_boundary"),
        "board_executed": result.get("board_executed"),
        "ok": result.get("ok"),
        "bitstream_sha256": result.get("bitstream", {}).get("sha256", ""),
        "hwh_sha256": result.get("hwh", {}).get("sha256", ""),
        "axis_input_seen_nonzero_check": checks.get("axis_input_seen_nonzero"),
        "axis_router_accept_nonzero_check": checks.get("axis_router_accept_nonzero"),
        "pl_busy_cycles_counter": config_after.get("pl_busy_cycles", 0),
        "output_drain_cycles_counter": config_after.get("output_drain_cycles", 0),
        "router_spike_cnt": config_after.get("router_spike_cnt", 0),
        "neuron_spike_cnt": config_after.get("neuron_spike_cnt", 0),
        "output_br_events": config_after.get("output_br_events", 0),
        "output_br_emits": config_after.get("output_br_emits", 0),
        "output_words": output_spike.get("output_words", []),
        "output_decoded": output_spike.get("decoded", {}),
        "eventword64_lowering": result.get("eventword64_lowering"),
    }


def load_flat_fc_lif_board_smoke() -> dict | None:
    if not FLAT_FC_LIF_BOARD_SMOKE_JSON.exists():
        return None
    result = json.loads(FLAT_FC_LIF_BOARD_SMOKE_JSON.read_text(encoding="utf-8"))
    config_after = result.get("config_after", {})
    return {
        "path": str(FLAT_FC_LIF_BOARD_SMOKE_JSON.relative_to(ROOT)),
        "schema": result.get("schema"),
        "evidence_level": result.get("evidence_level"),
        "claim_boundary": result.get("claim_boundary"),
        "board_executed": result.get("board_executed"),
        "ok": result.get("ok"),
        "bitstream_sha256": result.get("bitstream", {}).get("sha256", ""),
        "hwh_sha256": result.get("hwh", {}).get("sha256", ""),
        "model": result.get("model", {}),
        "state_reset_boundary": result.get("state_reset_boundary", {}),
        "input_eventword64": result.get("input_eventword64", []),
        "input_axis32": result.get("input_axis32", []),
        "expected": result.get("expected", {}),
        "output": result.get("output", {}),
        "required_checks": result.get("required_checks", {}),
        "pl_busy_cycles_counter": config_after.get("pl_busy_cycles", 0),
        "output_drain_cycles_counter": config_after.get("output_drain_cycles", 0),
        "router_spike_cnt": config_after.get("router_spike_cnt", 0),
        "neuron_spike_cnt": config_after.get("neuron_spike_cnt", 0),
        "output_br_events": config_after.get("output_br_events", 0),
        "output_br_emits": config_after.get("output_br_emits", 0),
        "output_br_drops": config_after.get("output_br_drops", 0),
        "state_checksum": config_after.get("state_checksum", 0),
    }


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
    board_smoke = load_board_smoke(BOARD_SMOKE_JSON)
    eventword64_board_smoke = load_board_smoke(EVENTWORD64_BOARD_SMOKE_JSON)
    flat_fc_lif_board_smoke = load_flat_fc_lif_board_smoke()
    if board_smoke is not None:
        smoke["board_smoke"] = board_smoke
        smoke["board_executed"] = bool(board_smoke["board_executed"])
        smoke["evidence_level"] = "software_transport_plus_pynq_direct_rtl_spike_smoke"
        smoke["all_ok"] = bool(smoke["all_ok"] and board_smoke["ok"])
    if eventword64_board_smoke is not None:
        smoke["eventword64_board_smoke"] = eventword64_board_smoke
        smoke["board_executed"] = True
        smoke["evidence_level"] = "software_transport_plus_pynq_direct_rtl_eventword64_smoke"
        smoke["all_ok"] = bool(smoke["all_ok"] and eventword64_board_smoke["ok"])
    if flat_fc_lif_board_smoke is not None:
        smoke["flat_fc_lif_board_smoke"] = flat_fc_lif_board_smoke
        smoke["board_executed"] = True
        smoke["evidence_level"] = "software_transport_plus_pynq_flat_fc_lif_commit_value_state_checksum_smoke"
        smoke["all_ok"] = bool(smoke["all_ok"] and flat_fc_lif_board_smoke["ok"])
    smoke_path = output_dir / "batch_1b_transport_flat_fc_lif_smoke.json"
    smoke_path.write_text(json.dumps(smoke, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    flat_fc_lif = smoke["flat_fc_lif"]
    axis32 = smoke["eventword64_to_axis32"]
    counters = flat_fc_lif["counters"]
    if board_smoke is None and eventword64_board_smoke is None and flat_fc_lif_board_smoke is None:
        board_section = """## Board Evidence

Board execution was not run for this Batch 1B report. This report does not
claim PYNQ-Z2 PL correctness, latency, throughput, or energy.
"""
        status = "software transport smoke generated"
        next_gate = "Replace software transport smoke with real PYNQ-Z2 board-captured output and register counters."
    else:
        direct_board_section = ""
        if board_smoke is not None:
            direct_board_section = f"""
### Direct AER32 Board Smoke

PYNQ-Z2 direct RTL AXI spike smoke was included from
`{board_smoke["path"]}`.

| Counter | Value |
|---|---:|
| board executed | `{board_smoke["board_executed"]}` |
| board ok | `{board_smoke["ok"]}` |
| AXIS input seen check | `{board_smoke["axis_input_seen_nonzero_check"]}` |
| AXIS router accept check | `{board_smoke["axis_router_accept_nonzero_check"]}` |
| PL busy register / AXIS seen count | `{board_smoke["pl_busy_cycles_counter"]}` |
| output drain register / AXIS accept count | `{board_smoke["output_drain_cycles_counter"]}` |
| router_spike_cnt | `{board_smoke["router_spike_cnt"]}` |
| neuron_spike_cnt | `{board_smoke["neuron_spike_cnt"]}` |
| output bridge events | `{board_smoke["output_br_events"]}` |
| output bridge emits | `{board_smoke["output_br_emits"]}` |
| output words | `{board_smoke["output_words"]}` |

Board claim boundary:

`{board_smoke["claim_boundary"]}`

Bitstream SHA-256:

`{board_smoke["bitstream_sha256"]}`

HWH SHA-256:

`{board_smoke["hwh_sha256"]}`
"""
        eventword64_board_section = ""
        if eventword64_board_smoke is not None:
            lowering = eventword64_board_smoke["eventword64_lowering"] or {}
            eventword64_board_section = f"""
### EventWord64-Lowered Board Smoke

PYNQ-Z2 direct RTL AXI spike smoke accepted a SpikePress EventWord64 input from
`{eventword64_board_smoke["path"]}` and lowered it to the current direct RTL
AER32 stream.

| Counter | Value |
|---|---:|
| board executed | `{eventword64_board_smoke["board_executed"]}` |
| board ok | `{eventword64_board_smoke["ok"]}` |
| input EventWord64 | `{lowering.get("input_eventword64")}` |
| lowered AXIS32 | `{lowering.get("output_axis32")}` |
| lossless flat input semantics | `{lowering.get("lossless_flat_input_semantics")}` |
| AXIS input seen check | `{eventword64_board_smoke["axis_input_seen_nonzero_check"]}` |
| AXIS router accept check | `{eventword64_board_smoke["axis_router_accept_nonzero_check"]}` |
| PL busy register / AXIS seen count | `{eventword64_board_smoke["pl_busy_cycles_counter"]}` |
| output drain register / AXIS accept count | `{eventword64_board_smoke["output_drain_cycles_counter"]}` |
| router_spike_cnt | `{eventword64_board_smoke["router_spike_cnt"]}` |
| neuron_spike_cnt | `{eventword64_board_smoke["neuron_spike_cnt"]}` |
| output bridge events | `{eventword64_board_smoke["output_br_events"]}` |
| output bridge emits | `{eventword64_board_smoke["output_br_emits"]}` |
| output words | `{eventword64_board_smoke["output_words"]}` |

Board claim boundary:

`{eventword64_board_smoke["claim_boundary"]}`

Bitstream SHA-256:

`{eventword64_board_smoke["bitstream_sha256"]}`

HWH SHA-256:

`{eventword64_board_smoke["hwh_sha256"]}`
"""
        flat_fc_lif_board_section = ""
        if flat_fc_lif_board_smoke is not None:
            expected = flat_fc_lif_board_smoke["expected"]
            output = flat_fc_lif_board_smoke["output"]
            state_reset = flat_fc_lif_board_smoke["state_reset_boundary"]
            flat_fc_lif_board_section = f"""
### Tiny Flat FC-LIF Board Trace Smoke

PYNQ-Z2 direct RTL AXI spike smoke consumed the tiny flat FC-LIF SpikePress trace
from `{flat_fc_lif_board_smoke["path"]}`. This is readout id, commit value,
and final membrane checksum readback evidence. Counters are raw diagnostics
only, not latency, throughput, frequency, or energy claims.

| Counter | Value |
|---|---:|
| board executed | `{flat_fc_lif_board_smoke["board_executed"]}` |
| board ok | `{flat_fc_lif_board_smoke["ok"]}` |
| input EventWord64 words | `{flat_fc_lif_board_smoke["input_eventword64"]}` |
| lowered AXIS32 words | `{flat_fc_lif_board_smoke["input_axis32"]}` |
| expected readout ids | `{expected.get("readout_ids")}` |
| board readout ids | `{output.get("readout_ids")}` |
| expected commit values | `{expected.get("commit_values")}` |
| board commit values | `{output.get("commit_values")}` |
| expected output words | `{expected.get("output_words")}` |
| board output words | `{output.get("output_words")}` |
| expected final state | `{expected.get("final_state")}` |
| expected state checksum | `{expected.get("state_checksum")}` |
| board state checksum | `{output.get("state_checksum")}` |
| PL busy register / AXIS seen count | `{flat_fc_lif_board_smoke["pl_busy_cycles_counter"]}` |
| output drain register / AXIS accept count | `{flat_fc_lif_board_smoke["output_drain_cycles_counter"]}` |
| router_spike_cnt | `{flat_fc_lif_board_smoke["router_spike_cnt"]}` |
| neuron_spike_cnt | `{flat_fc_lif_board_smoke["neuron_spike_cnt"]}` |
| output bridge events | `{flat_fc_lif_board_smoke["output_br_events"]}` |
| output bridge emits | `{flat_fc_lif_board_smoke["output_br_emits"]}` |
| output bridge drops | `{flat_fc_lif_board_smoke["output_br_drops"]}` |
| config state checksum | `{flat_fc_lif_board_smoke["state_checksum"]}` |
| fresh overlay loaded | `{state_reset.get("fresh_overlay_loaded")}` |
| HLS soft reset clears membrane BRAM | `{state_reset.get("hls_soft_reset_clears_membrane_bram")}` |
| state checksum valid after soft reset alone | `{state_reset.get("state_checksum_valid_after_soft_reset")}` |
| state checksum validity | `{state_reset.get("state_checksum_validity")}` |

Board claim boundary:

`{flat_fc_lif_board_smoke["claim_boundary"]}`

Bitstream SHA-256:

`{flat_fc_lif_board_smoke["bitstream_sha256"]}`

HWH SHA-256:

`{flat_fc_lif_board_smoke["hwh_sha256"]}`
"""
        board_section = f"""## Board Evidence
{direct_board_section}
{eventword64_board_section}
{flat_fc_lif_board_section}
"""
        if flat_fc_lif_board_smoke is not None:
            status = "software transport plus PYNQ flat FC-LIF commit-value/state-checksum smoke complete"
            next_gate = "Extend to EventConv commit payload/checksum board smoke and compare the EventConv golden trace."
        elif eventword64_board_smoke is not None:
            status = "software transport plus PYNQ direct RTL EventWord64-lowered spike smoke complete"
            next_gate = "Extend from one EventWord64-lowered board event to tiny flat FC-LIF trace/readout parity."
        else:
            status = "software transport plus PYNQ direct RTL spike smoke complete"
            next_gate = "Extend board transport from one-spike direct RTL smoke to EventWord64 counter and flat FC-LIF trace/readout match."
        if not smoke["all_ok"]:
            status = "transport or board smoke failed"
            next_gate = "Fix failed transport or board smoke before claiming the Batch 1B gate."

    report = f"""# Batch 1B Transport + Flat FC-LIF Report

Status: {status}

## Evidence Level

`{smoke["evidence_level"]}`

## Generated

- `outputs/transport/batch_1b_transport_flat_fc_lif_smoke.json`
- `reports/batch_1b_transport_flat_fc_lif_report.md`

## Smoke Results

| Gate | Result |
|---|---:|
| AXI-Lite register smoke | `{smoke["register_smoke"]["ok"]}` |
| DMA loopback smoke | `{smoke["dma_loopback"]["ok"]}` |
| EventWord64 counter smoke | `{smoke["eventword64_counter"]["ok"]}` |
| EventWord64 to AXIS32 lowering | `{axis32["ok"]}` |
| SpikeMold flat FC-LIF smoke | `{flat_fc_lif["ok"]}` |
| All OK | `{smoke["all_ok"]}` |

## EventWord64 To AXIS32 Lowering

| Field | Value |
|---|---:|
| source format | `{axis32["source_format"]}` |
| target format | `{axis32["target_format"]}` |
| word count | `{axis32["word_count"]}` |
| lossless flat input semantics | `{axis32["lossless_flat_input_semantics"]}` |
| output axis32 sha256 | `{axis32["output_axis32_sha256"]}` |

## Flat FC-LIF Counters

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

{board_section}

## Next Gate

{next_gate}
"""
    (report_dir / "batch_1b_transport_flat_fc_lif_report.md").write_text(report, encoding="utf-8")
    return 0 if smoke["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
