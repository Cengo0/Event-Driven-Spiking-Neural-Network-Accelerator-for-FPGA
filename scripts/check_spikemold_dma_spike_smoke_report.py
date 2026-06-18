#!/usr/bin/env python3
"""Check SpikeMold PYNQ-Z2 DMA spike smoke evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
BOARD_JSON = ROOT / "outputs" / "board" / "dma_spike_smoke_result_20260614.json"
EVENTWORD64_BOARD_JSON = ROOT / "outputs" / "board" / "dma_spike_smoke_eventword64_result_20260614.json"
REPORT_MD = ROOT / "reports" / "spikemold_dma_spike_smoke_report.md"
SCHEMA = "spikemold.pynq_dma_spike_smoke.v2"
CLAIM_BOUNDARY = "pynq_axi_dma0_direct_rtl_one_spike_event_to_post_spike_readback_only_no_dataset"
EXPECTED_HLS_VERSION = 0x20260221
EXPECTED_CONFIG_VERSION = 0x534D3031
BIT_SHA256 = "5b6b3d64a8263b3e6b075c934bcef0d3684d576756cba600711d2918d863d1d0"
HWH_SHA256 = "9447e36cbfc687c8cf0683b6ae05671ad4ef9bb017ef78c1a0777b73d6a87ec3"
EVENTWORD64_INPUT_WORD = 0x800
EVENTWORD64_LOWERED_AXIS32 = 0x2000


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        fail(f"{name} must be a mapping")
    return value


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        fail(f"cannot load JSON {path}: {exc}")


def main() -> int:
    if not BOARD_JSON.exists():
        fail(f"missing board JSON: {BOARD_JSON}")
    if not REPORT_MD.exists():
        fail(f"missing report: {REPORT_MD}")

    result = load_json(BOARD_JSON)
    if result.get("schema") != SCHEMA:
        fail("schema mismatch")
    if result.get("evidence_level") != "pynq_board_dma_spike_stream_smoke":
        fail("evidence level mismatch")
    if result.get("board_executed") is not True:
        fail("board_executed must be true")
    if result.get("ok") is not True:
        fail("DMA spike smoke ok must be true")
    if result.get("claim_boundary") != CLAIM_BOUNDARY:
        fail("claim boundary mismatch")
    if result.get("ip_name") != "spikemold_top_hls_0":
        fail("IP name mismatch")
    if result.get("dma_name") != "axi_dma_0":
        fail("DMA name mismatch")
    if result.get("config_ip_name") != "spikemold_config_regs_0":
        fail("config IP name mismatch")
    for ip_name in ["spikemold_top_hls_0", "axi_dma_0", "spikemold_config_regs_0"]:
        if ip_name not in result.get("available_ips", []):
            fail(f"overlay missing {ip_name}")

    if int(result.get("expected_hls_version", 0)) != EXPECTED_HLS_VERSION:
        fail("expected HLS version mismatch")
    if int(result.get("expected_config_version", 0)) != EXPECTED_CONFIG_VERSION:
        fail("expected config version mismatch")

    checks = require_mapping(result.get("checks"), "checks")
    required_checks = require_mapping(result.get("required_checks", checks), "required_checks")
    for key in [
        "reset_ap_done",
        "spike_ap_done",
        "hls_version_matches",
        "config_version_matches",
        "axis_input_seen_nonzero",
        "axis_router_accept_nonzero",
        "router_spike_count_nonzero",
        "neuron_spike_count_nonzero",
        "output_id_matches",
        "output_commit_value_matches",
        "output_word_matches",
        "output_reserved_top3_zero",
    ]:
        if required_checks.get(key) is not True:
            fail(f"check failed: {key}")
    for key in ["output_event_count_nonzero", "output_emit_count_nonzero"]:
        if key not in checks:
            fail(f"missing diagnostic check: {key}")

    route = require_mapping(result.get("route_config"), "route_config")
    if route.get("source_id") != 0:
        fail("source_id mismatch")
    if route.get("dest_id") != 1:
        fail("dest_id mismatch")
    if route.get("route_weight") != 1:
        fail("route_weight mismatch")
    if route.get("threshold") != 1:
        fail("threshold mismatch")
    if route.get("route_word") != 0x0C040001:
        fail("route_word mismatch")

    input_spike = require_mapping(result.get("input_spike"), "input_spike")
    lowering = result.get("eventword64_lowering")
    if lowering is None:
        if input_spike.get("input_word") != 0x00002000:
            fail("input spike word mismatch")
    else:
        lowering = require_mapping(lowering, "eventword64_lowering")
        if lowering.get("lossless_flat_input_semantics") is not True:
            fail("EventWord64 lowering must preserve flat input semantics")
        if lowering.get("output_axis32") != input_spike.get("input_word"):
            fail("EventWord64 lowering output_axis32 does not match input spike word")
        decoded_lowering = require_mapping(lowering.get("decoded"), "eventword64 decoded")
        if decoded_lowering.get("src_id") != route.get("source_id"):
            fail("EventWord64 lowering source id mismatch")
        if decoded_lowering.get("signed_payload") != input_spike.get("input_weight"):
            fail("EventWord64 lowering payload mismatch")

    output_spike = require_mapping(result.get("output_spike"), "output_spike")
    output_words = output_spike.get("output_words", [])
    if not isinstance(output_words, list) or len(output_words) != 1:
        fail("output word count mismatch")
    decoded = require_mapping(output_spike.get("decoded"), "decoded output")
    if decoded.get("id") != 1:
        fail("decoded output id mismatch")
    if decoded.get("commit_value_u16") != 1:
        fail("decoded output commit value mismatch")
    if decoded.get("reserved_top3") != 0:
        fail("decoded output reserved bits mismatch")
    if int(output_words[0]) != 0x00002001:
        fail("output payload mismatch")

    runs = require_mapping(result.get("runs"), "runs")
    spike_run = require_mapping(runs.get("spike"), "spike run")
    if int(spike_run.get("version_reg", 0)) != EXPECTED_HLS_VERSION:
        fail("spike run HLS version mismatch")
    config_after = require_mapping(result.get("config_after"), "config_after")
    if int(config_after.get("version", 0)) != EXPECTED_CONFIG_VERSION:
        fail("config version mismatch")
    for key in ["pl_busy_cycles", "output_drain_cycles", "router_spike_cnt", "neuron_spike_cnt"]:
        if int(config_after.get(key, 0)) < 1:
            fail(f"{key} must be nonzero")
    for key in ["output_br_events", "output_br_emits"]:
        if int(config_after.get(key, 0)) < 1:
            fail(f"{key} must be nonzero")
    diagnostics = require_mapping(result.get("diagnostic_checks"), "diagnostic_checks")
    for key in ["output_event_count_nonzero", "output_emit_count_nonzero"]:
        if diagnostics.get(key) is not True:
            fail(f"diagnostic check must be true: {key}")

    bitstream = require_mapping(result.get("bitstream"), "bitstream")
    hwh = require_mapping(result.get("hwh"), "hwh")
    if bitstream.get("sha256") != BIT_SHA256:
        fail("bitstream sha256 mismatch")
    if hwh.get("sha256") != HWH_SHA256:
        fail("HWH sha256 mismatch")

    text = REPORT_MD.read_text(encoding="utf-8")
    if EVENTWORD64_BOARD_JSON.exists():
        eventword64 = load_json(EVENTWORD64_BOARD_JSON)
        if eventword64.get("schema") != SCHEMA:
            fail("EventWord64 board schema mismatch")
        if eventword64.get("board_executed") is not True:
            fail("EventWord64 board_executed must be true")
        if eventword64.get("ok") is not True:
            fail("EventWord64 board ok must be true")
        if eventword64.get("claim_boundary") != CLAIM_BOUNDARY:
            fail("EventWord64 board claim boundary mismatch")
        lowering = require_mapping(eventword64.get("eventword64_lowering"), "EventWord64 lowering")
        if lowering.get("input_eventword64") != EVENTWORD64_INPUT_WORD:
            fail("EventWord64 input word mismatch")
        if lowering.get("output_axis32") != EVENTWORD64_LOWERED_AXIS32:
            fail("EventWord64 lowered AXIS32 mismatch")
        if lowering.get("lossless_flat_input_semantics") is not True:
            fail("EventWord64 lowering must preserve flat input semantics")
        ev_route = require_mapping(eventword64.get("route_config"), "EventWord64 route_config")
        if ev_route.get("source_id") != 0 or ev_route.get("dest_id") != 1:
            fail("EventWord64 route mismatch")
        ev_output = require_mapping(eventword64.get("output_spike"), "EventWord64 output_spike")
        ev_words = ev_output.get("output_words", [])
        if not isinstance(ev_words, list) or ev_words != [8193]:
            fail("EventWord64 output word mismatch")
        ev_config = require_mapping(eventword64.get("config_after"), "EventWord64 config_after")
        for key in ["pl_busy_cycles", "output_drain_cycles", "router_spike_cnt", "neuron_spike_cnt"]:
            if int(ev_config.get(key, 0)) < 1:
                fail(f"EventWord64 {key} must be nonzero")
        if require_mapping(eventword64.get("bitstream"), "EventWord64 bitstream").get("sha256") != BIT_SHA256:
            fail("EventWord64 bitstream sha256 mismatch")
        if require_mapping(eventword64.get("hwh"), "EventWord64 hwh").get("sha256") != HWH_SHA256:
            fail("EventWord64 HWH sha256 mismatch")
        for phrase in [
            "EventWord64-Lowered Board Result",
            str(EVENTWORD64_INPUT_WORD),
            str(EVENTWORD64_LOWERED_AXIS32),
            "lossless flat input semantics",
        ]:
            if phrase not in text:
                fail(f"report missing EventWord64 phrase: {phrase}")

    for phrase in [
        "PYNQ-Z2 AXI DMA spike stream smoke passed",
        "This is a board execution result",
        "claim SpikePress EventWord64 parity",
        CLAIM_BOUNDARY,
    ]:
        if phrase not in text:
            fail(f"report missing phrase: {phrase}")

    print("PASS: SpikeMold PYNQ-Z2 DMA spike smoke evidence valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
