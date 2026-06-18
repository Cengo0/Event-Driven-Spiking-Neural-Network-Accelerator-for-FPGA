#!/usr/bin/env python3
"""Check Batch 1B SpikeMold transport smoke artifacts."""

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

from spikepress.transport import (  # noqa: E402
    AXI_LITE_SMOKE_SCHEMA,
    DMA_LOOPBACK_SCHEMA,
    FLAT_FC_LIF_SMOKE_SCHEMA,
    EVENTWORD_COUNTER_SCHEMA,
    EVENTWORD_TO_AXIS32_SCHEMA,
    TRANSPORT_SMOKE_SCHEMA,
)

BOARD_SMOKE_SCHEMA = "spikemold.pynq_dma_spike_smoke.v2"
BOARD_CLAIM_BOUNDARY = "pynq_axi_dma0_direct_rtl_one_spike_event_to_post_spike_readback_only_no_dataset"
BOARD_BIT_SHA256 = "5b6b3d64a8263b3e6b075c934bcef0d3684d576756cba600711d2918d863d1d0"
BOARD_HWH_SHA256 = "9447e36cbfc687c8cf0683b6ae05671ad4ef9bb017ef78c1a0777b73d6a87ec3"
EVENTWORD64_INPUT_WORD = 0x800
EVENTWORD64_LOWERED_AXIS32 = 0x2000
FLAT_FC_LIF_BOARD_SCHEMA = "spikemold.pynq_flat_fc_lif_trace_smoke.v1"
FLAT_FC_LIF_CLAIM_BOUNDARY = "pynq_axi_dma0_direct_rtl_tiny_flat_fc_lif_commit_value_state_checksum_readback"
FLAT_FC_LIF_INPUT_AXIS32 = [8192, 2105345, 4202496]
FLAT_FC_LIF_OUTPUT_WORDS = [40962]
FLAT_FC_LIF_READOUT_IDS = [2]
FLAT_FC_LIF_COMMIT_VALUES = [5]
FLAT_FC_LIF_FINAL_STATE = {"2": 3, "3": 2}
FLAT_FC_LIF_STATE_CHECKSUM = 5


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - diagnostic path
        fail(f"cannot load JSON {path}: {exc}")


def summarize_board_smoke(path: Path) -> dict:
    result = load_json(path)
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


def summarize_flat_fc_lif_board_smoke() -> dict:
    result = load_json(FLAT_FC_LIF_BOARD_SMOKE_JSON)
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


def require_section(root: dict, key: str, schema: str) -> dict:
    section = root.get(key)
    if not isinstance(section, dict):
        fail(f"missing section: {key}")
    if section.get("schema") != schema:
        fail(f"{key} schema mismatch")
    if section.get("ok") is not True:
        fail(f"{key} ok is not true")
    if section.get("board_executed") is not False:
        fail(f"{key} must not claim board execution")
    return section


def require_board_smoke_section(
    *,
    smoke: dict,
    source_json: Path,
    section_key: str,
    expect_eventword64_lowering: bool,
) -> None:
    if not source_json.exists():
        if section_key in smoke:
            fail(f"{section_key} section present but source board JSON is missing")
        return

    board_json = load_json(source_json)
    if board_json.get("schema") != BOARD_SMOKE_SCHEMA:
        fail(f"{section_key} schema mismatch")
    if board_json.get("board_executed") is not True:
        fail(f"{section_key} did not execute on board")
    if board_json.get("ok") is not True:
        fail(f"{section_key} ok is not true")
    if board_json.get("claim_boundary") != BOARD_CLAIM_BOUNDARY:
        fail(f"{section_key} claim boundary mismatch")

    board_smoke = smoke.get(section_key)
    if not isinstance(board_smoke, dict):
        fail(f"transport smoke missing {section_key} section")
    expected_board_smoke = summarize_board_smoke(source_json)
    if board_smoke != expected_board_smoke:
        fail(f"transport {section_key} is stale or does not match source board JSON")
    if board_smoke.get("schema") != BOARD_SMOKE_SCHEMA:
        fail(f"{section_key} schema mismatch")
    if board_smoke.get("claim_boundary") != BOARD_CLAIM_BOUNDARY:
        fail(f"{section_key} claim boundary mismatch")
    if board_smoke.get("bitstream_sha256") != BOARD_BIT_SHA256:
        fail(f"{section_key} bitstream sha256 mismatch")
    if board_smoke.get("hwh_sha256") != BOARD_HWH_SHA256:
        fail(f"{section_key} hwh sha256 mismatch")
    for key in [
        "pl_busy_cycles_counter",
        "output_drain_cycles_counter",
        "router_spike_cnt",
        "neuron_spike_cnt",
        "output_br_events",
        "output_br_emits",
    ]:
        if int(board_smoke.get(key, 0)) < 1:
            fail(f"{section_key} {key} must be nonzero")
    for key in ["axis_input_seen_nonzero_check", "axis_router_accept_nonzero_check"]:
        if board_smoke.get(key) is not True:
            fail(f"{section_key} {key} must be true")
    decoded = board_smoke.get("output_decoded", {})
    if decoded.get("id") != 1:
        fail(f"{section_key} output id mismatch")
    if decoded.get("commit_value_u16") != 1:
        fail(f"{section_key} output commit value mismatch")
    if decoded.get("reserved_top3") != 0:
        fail(f"{section_key} output reserved bits mismatch")

    lowering = board_smoke.get("eventword64_lowering")
    if expect_eventword64_lowering:
        if not isinstance(lowering, dict):
            fail(f"{section_key} missing EventWord64 lowering")
        if lowering.get("input_eventword64") != EVENTWORD64_INPUT_WORD:
            fail(f"{section_key} EventWord64 input mismatch")
        if lowering.get("output_axis32") != EVENTWORD64_LOWERED_AXIS32:
            fail(f"{section_key} lowered AXIS32 mismatch")
        if lowering.get("lossless_flat_input_semantics") is not True:
            fail(f"{section_key} lowering must preserve flat input semantics")
        decoded_lowering = lowering.get("decoded", {})
        if decoded_lowering.get("src_id") != 0:
            fail(f"{section_key} EventWord64 source id mismatch")
        if decoded_lowering.get("signed_payload") != 1:
            fail(f"{section_key} EventWord64 payload mismatch")
    elif lowering is not None:
        fail(f"{section_key} unexpectedly includes EventWord64 lowering")


def require_board_smoke(smoke: dict) -> None:
    if not BOARD_SMOKE_JSON.exists() and not EVENTWORD64_BOARD_SMOKE_JSON.exists() and not FLAT_FC_LIF_BOARD_SMOKE_JSON.exists():
        if "board_smoke" in smoke or "eventword64_board_smoke" in smoke or "flat_fc_lif_board_smoke" in smoke:
            fail("board smoke section present but source board JSON is missing")
        if smoke.get("board_executed") is not False:
            fail("host-only transport smoke must not claim board execution")
        return

    if smoke.get("board_executed") is not True:
        fail("transport smoke must reflect board execution")
    expected_evidence = (
        "software_transport_plus_pynq_flat_fc_lif_commit_value_state_checksum_smoke"
        if FLAT_FC_LIF_BOARD_SMOKE_JSON.exists()
        else (
            "software_transport_plus_pynq_direct_rtl_eventword64_smoke"
            if EVENTWORD64_BOARD_SMOKE_JSON.exists()
            else "software_transport_plus_pynq_direct_rtl_spike_smoke"
        )
    )
    if smoke.get("evidence_level") != expected_evidence:
        fail("transport smoke evidence level must match board evidence")

    require_board_smoke_section(
        smoke=smoke,
        source_json=BOARD_SMOKE_JSON,
        section_key="board_smoke",
        expect_eventword64_lowering=False,
    )
    require_board_smoke_section(
        smoke=smoke,
        source_json=EVENTWORD64_BOARD_SMOKE_JSON,
        section_key="eventword64_board_smoke",
        expect_eventword64_lowering=True,
    )
    if FLAT_FC_LIF_BOARD_SMOKE_JSON.exists():
        flat = smoke.get("flat_fc_lif_board_smoke")
        if not isinstance(flat, dict):
            fail("transport smoke missing flat_fc_lif_board_smoke section")
        if flat != summarize_flat_fc_lif_board_smoke():
            fail("transport flat_fc_lif_board_smoke is stale or does not match source board JSON")
        if flat.get("schema") != FLAT_FC_LIF_BOARD_SCHEMA:
            fail("flat FC-LIF board schema mismatch")
        if flat.get("claim_boundary") != FLAT_FC_LIF_CLAIM_BOUNDARY:
            fail("flat FC-LIF board claim boundary mismatch")
        if flat.get("board_executed") is not True or flat.get("ok") is not True:
            fail("flat FC-LIF board smoke must execute and pass")
        if flat.get("bitstream_sha256") != BOARD_BIT_SHA256:
            fail("flat FC-LIF board bitstream sha256 mismatch")
        if flat.get("hwh_sha256") != BOARD_HWH_SHA256:
            fail("flat FC-LIF board HWH sha256 mismatch")
        if flat.get("input_axis32") != FLAT_FC_LIF_INPUT_AXIS32:
            fail("flat FC-LIF board input AXIS32 mismatch")
        if flat.get("expected", {}).get("output_words") != FLAT_FC_LIF_OUTPUT_WORDS:
            fail("flat FC-LIF board expected output words mismatch")
        if flat.get("output", {}).get("output_words") != FLAT_FC_LIF_OUTPUT_WORDS:
            fail("flat FC-LIF board output words mismatch")
        if flat.get("output", {}).get("readout_ids") != FLAT_FC_LIF_READOUT_IDS:
            fail("flat FC-LIF board readout ids mismatch")
        if flat.get("output", {}).get("commit_values") != FLAT_FC_LIF_COMMIT_VALUES:
            fail("flat FC-LIF board commit values mismatch")
        if flat.get("expected", {}).get("final_state") != FLAT_FC_LIF_FINAL_STATE:
            fail("flat FC-LIF board expected final state mismatch")
        if flat.get("expected", {}).get("state_checksum") != FLAT_FC_LIF_STATE_CHECKSUM:
            fail("flat FC-LIF board expected state checksum mismatch")
        if flat.get("output", {}).get("state_checksum") != FLAT_FC_LIF_STATE_CHECKSUM:
            fail("flat FC-LIF board output state checksum mismatch")
        if int(flat.get("state_checksum", -1)) != FLAT_FC_LIF_STATE_CHECKSUM:
            fail("flat FC-LIF board config state checksum mismatch")
        if int(flat.get("output_br_drops", -1)) != 0:
            fail("flat FC-LIF board output drops must be zero")
        if flat.get("state_reset_boundary", {}).get("hls_soft_reset_clears_membrane_bram") is not False:
            fail("flat FC-LIF board must not claim HLS soft reset clears membrane BRAM")
        if flat.get("state_reset_boundary", {}).get("state_checksum_valid_after_soft_reset") is not False:
            fail("flat FC-LIF board checksum reset boundary mismatch")
        for key in [
            "reset_ap_done",
            "release_ap_done",
            "trace_ap_done",
            "input_count_reached",
            "router_update_count_reached",
            "output_words_match",
            "output_ids_match",
            "output_commit_values_match",
            "state_checksum_matches",
        ]:
            if flat.get("required_checks", {}).get(key) is not True:
                fail(f"flat FC-LIF board required check failed: {key}")
        if int(flat.get("pl_busy_cycles_counter", 0)) < 3:
            fail("flat FC-LIF board input count too low")
        if int(flat.get("router_spike_cnt", 0)) < 5:
            fail("flat FC-LIF board routed update count too low")
        if int(flat.get("neuron_spike_cnt", -1)) != 1:
            fail("flat FC-LIF board neuron spike count mismatch")
        if int(flat.get("output_br_drops", -1)) != 0:
            fail("flat FC-LIF board output drops must be zero")
    elif "flat_fc_lif_board_smoke" in smoke:
        fail("flat_fc_lif_board_smoke section present but source board JSON is missing")


def main() -> int:
    smoke_path = ROOT / "outputs" / "transport" / "batch_1b_transport_flat_fc_lif_smoke.json"
    report_path = ROOT / "reports" / "batch_1b_transport_flat_fc_lif_report.md"
    if not smoke_path.exists():
        fail(f"missing smoke artifact: {smoke_path}")
    if not report_path.exists():
        fail(f"missing report: {report_path}")

    smoke = load_json(smoke_path)
    if smoke.get("schema") != TRANSPORT_SMOKE_SCHEMA:
        fail("transport smoke schema mismatch")
    if smoke.get("all_ok") is not True:
        fail("transport smoke all_ok is not true")
    require_board_smoke(smoke)

    assumptions = smoke.get("runtime_assumptions", {})
    if assumptions.get("bounded_job") is not True:
        fail("bounded_job assumption missing")
    for key in ["python_inner_loop_required", "random_ddr_inner_loop", "full_neuron_scan_primary"]:
        if assumptions.get(key) is not False:
            fail(f"forbidden runtime assumption not false: {key}")

    require_section(smoke, "register_smoke", AXI_LITE_SMOKE_SCHEMA)
    require_section(smoke, "dma_loopback", DMA_LOOPBACK_SCHEMA)
    require_section(smoke, "eventword64_counter", EVENTWORD_COUNTER_SCHEMA)
    axis32 = require_section(smoke, "eventword64_to_axis32", EVENTWORD_TO_AXIS32_SCHEMA)
    if axis32.get("source_format") != "EventWord64 input_spike":
        fail("EventWord64 to AXIS32 source format mismatch")
    if axis32.get("target_format") != "AER32 direct RTL DMA0":
        fail("EventWord64 to AXIS32 target format mismatch")
    if axis32.get("lossless_flat_input_semantics") is not True:
        fail("EventWord64 to AXIS32 lowering must be lossless for flat inputs")
    if int(axis32.get("word_count", -1)) <= 0:
        fail("EventWord64 to AXIS32 lowering word_count must be positive")
    if "source id outside current direct RTL physical range" not in axis32.get("rejected_semantics", []):
        fail("EventWord64 to AXIS32 lowering must reject out-of-range direct RTL source ids")
    flat_fc_lif = require_section(smoke, "flat_fc_lif", FLAT_FC_LIF_SMOKE_SCHEMA)
    if flat_fc_lif.get("trace_match_rate") != 1.0:
        fail("SpikeMold flat FC-LIF trace_match_rate is not 1.0")
    if flat_fc_lif.get("readout_match") is not True:
        fail("SpikeMold flat FC-LIF readout_match is not true")
    if flat_fc_lif.get("state_checksum_match") is not True:
        fail("SpikeMold flat FC-LIF state_checksum_match is not true")
    counters = flat_fc_lif.get("counters", {})
    for key in ["input_event_count", "update_count", "active_count", "output_words", "dma_calls", "axi_lite_commands"]:
        if int(counters.get(key, -1)) < 0:
            fail(f"missing or invalid counter: {key}")
    if int(counters.get("python_inner_loop_steps", -1)) != 0:
        fail("python_inner_loop_steps must be zero")

    text = report_path.read_text(encoding="utf-8")
    if BOARD_SMOKE_JSON.exists():
        for phrase in [
            "Direct AER32 Board Smoke",
            BOARD_CLAIM_BOUNDARY,
            BOARD_BIT_SHA256,
            BOARD_HWH_SHA256,
        ]:
            if phrase not in text:
                fail(f"report missing board evidence phrase: {phrase}")
    if EVENTWORD64_BOARD_SMOKE_JSON.exists():
        for phrase in [
            "EventWord64-Lowered Board Smoke",
            str(EVENTWORD64_INPUT_WORD),
            str(EVENTWORD64_LOWERED_AXIS32),
            "lossless flat input semantics",
        ]:
            if phrase not in text:
                fail(f"report missing EventWord64 board evidence phrase: {phrase}")
    if FLAT_FC_LIF_BOARD_SMOKE_JSON.exists():
        for phrase in [
            "Tiny Flat FC-LIF Board Trace Smoke",
            FLAT_FC_LIF_CLAIM_BOUNDARY,
            "commit value",
            "state checksum",
        ]:
            if phrase not in text:
                fail(f"report missing flat FC-LIF board evidence phrase: {phrase}")
    if not BOARD_SMOKE_JSON.exists() and not EVENTWORD64_BOARD_SMOKE_JSON.exists():
        for phrase in ["Board execution was not run", "software_transport_smoke_no_board"]:
            if phrase not in text:
                fail(f"report missing evidence phrase: {phrase}")

    print("PASS: Batch 1B transport + SpikeMold flat FC-LIF smoke artifacts valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
