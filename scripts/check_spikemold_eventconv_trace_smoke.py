#!/usr/bin/env python3
"""Check SpikeMold PYNQ-Z2 EventConv trace/readout smoke evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
REPORT_MD = ROOT / "reports" / "spikemold_eventconv_trace_smoke_report.md"
SCHEMA = "spikemold.pynq_eventconv_trace_smoke.v1"
BIT_SHA256 = "5b6b3d64a8263b3e6b075c934bcef0d3684d576756cba600711d2918d863d1d0"
HWH_SHA256 = "9447e36cbfc687c8cf0683b6ae05671ad4ef9bb017ef78c1a0777b73d6a87ec3"

TRACE_SPECS = {
    "tiny": {
        "path": ROOT / "outputs" / "board" / "eventconv_trace_smoke_result_20260614.json",
        "evidence_level": "pynq_board_eventconv_multi_commit_state_checksum_smoke",
        "claim_boundary": "pynq_axi_dma0_direct_rtl_tiny_eventconv_multi_commit_state_checksum_readback",
        "model_name": "batch_1c_tiny_eventconv_c4_multi_commit",
        "threshold": 2,
        "input_axis32": [16842752],
        "output_words": [16386, 24577, 32768],
        "readout_ids": [2, 1, 0],
        "commit_values": [2, 3, 4],
        "final_state": {"3": 1},
        "state_checksum": 1,
        "active_commit_reads": 4,
        "generated_updates": 4,
        "active_neurons_after_commit": 1,
    },
    "burst-boundary": {
        "path": ROOT / "outputs" / "board" / "eventconv_burst_boundary_smoke_result_20260615.json",
        "evidence_level": "pynq_board_eventconv_burst_boundary_state_checksum_smoke",
        "claim_boundary": "pynq_axi_dma0_direct_rtl_eventconv_burst_boundary_state_checksum_readback",
        "model_name": "batch_1c_eventconv_c4_burst_boundary",
        "threshold": 3,
        "input_axis32": [16842752, 33685504, 0],
        "output_words": [40963, 24577, 40960],
        "readout_ids": [3, 1, 0],
        "commit_values": [5, 3, 5],
        "final_state": {"2": 2},
        "state_checksum": 2,
        "active_commit_reads": 4,
        "generated_updates": 6,
        "active_neurons_after_commit": 1,
    },
}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        fail(f"cannot load JSON {path}: {exc}")


def require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        fail(f"{name} must be a mapping")
    return value


def check_trace_result(name: str, spec: Mapping[str, object]) -> None:
    path = spec["path"]
    if not isinstance(path, Path):
        fail(f"{name} path must be Path")
    if not path.exists():
        fail(f"missing board JSON: {path}")

    result = load_json(path)
    if result.get("schema") != SCHEMA:
        fail(f"{name} schema mismatch")
    if result.get("variant") != name:
        fail(f"{name} variant mismatch")
    if result.get("evidence_level") != spec["evidence_level"]:
        fail(f"{name} evidence level mismatch")
    if result.get("claim_boundary") != spec["claim_boundary"]:
        fail(f"{name} claim boundary mismatch")
    if result.get("board_executed") is not True:
        fail(f"{name} board_executed must be true")
    if result.get("ok") is not True:
        fail(f"{name} EventConv trace smoke ok must be true")

    model = require_mapping(result.get("model"), f"{name} model")
    if model.get("name") != spec["model_name"]:
        fail(f"{name} model name mismatch")
    if model.get("kernel") != [[[[1, 2], [3, 4]]]]:
        fail(f"{name} kernel mismatch")
    if model.get("commit_threshold") != spec["threshold"]:
        fail(f"{name} commit threshold mismatch")

    descriptor = result.get("descriptor")
    if descriptor is not None:
        descriptor_map = require_mapping(descriptor, f"{name} descriptor")
        if descriptor_map.get("shape0_expected") != 0x04020303:
            fail(f"{name} EventConv shape descriptor mismatch")
        if descriptor_map.get("kernel0_expected") != 0x04030201:
            fail(f"{name} EventConv kernel descriptor mismatch")
        if descriptor_map.get("write_enabled") is True:
            descriptor_checks = require_mapping(descriptor_map.get("checks"), f"{name} descriptor checks")
            for key in [
                "eventconv_shape0_matches",
                "eventconv_kernel0_matches",
                "eventconv_descriptor_shape_supported",
                "eventconv_descriptor_kernel_runtime",
            ]:
                if descriptor_checks.get(key) is not True:
                    fail(f"{name} descriptor check failed: {key}")

    if result.get("input_axis32") != spec["input_axis32"]:
        fail(f"{name} input AXIS32 mismatch")

    expected = require_mapping(result.get("expected"), f"{name} expected")
    for key, spec_key in [
        ("generated_updates", "generated_updates"),
        ("active_commit_reads", "active_commit_reads"),
        ("readout_ids", "readout_ids"),
        ("commit_values", "commit_values"),
        ("output_words", "output_words"),
        ("final_state", "final_state"),
        ("state_checksum", "state_checksum"),
    ]:
        if expected.get(key) != spec[spec_key]:
            fail(f"{name} expected {key} mismatch")

    output = require_mapping(result.get("output"), f"{name} output")
    for key, spec_key in [
        ("output_words", "output_words"),
        ("readout_ids", "readout_ids"),
        ("commit_values", "commit_values"),
        ("state_checksum", "state_checksum"),
    ]:
        if output.get(key) != spec[spec_key]:
            fail(f"{name} board {key} mismatch")

    required = require_mapping(result.get("required_checks"), f"{name} required_checks")
    for key in [
        "reset_ap_done",
        "release_ap_done",
        "trace_ap_done",
        "hls_version_matches",
        "config_version_matches",
        "backend_mode_matches",
        "input_count_reached",
        "eventconv_update_count_matches",
        "active_commit_reads_match",
        "commit_emit_count_matches",
        "active_neurons_after_commit_match",
        "output_words_match",
        "output_ids_match",
        "output_commit_values_match",
        "state_checksum_matches",
        "output_bridge_events_match",
        "output_bridge_emits_match",
        "multi_commit_packet_drained",
    ]:
        if required.get(key) is not True:
            fail(f"{name} required check failed: {key}")

    diag = require_mapping(result.get("diagnostic_checks"), f"{name} diagnostic_checks")
    for key in ["no_output_bridge_drops", "no_eventconv_invalid_dest"]:
        if diag.get(key) is not True:
            fail(f"{name} diagnostic check failed: {key}")

    config = require_mapping(result.get("config_after"), f"{name} config_after")
    if int(config.get("backend_mode", -1)) != 1:
        fail(f"{name} backend mode register mismatch")
    if int(config.get("router_spike_cnt", -1)) != spec["generated_updates"]:
        fail(f"{name} EventConv update counter mismatch")
    if int(config.get("output_drain_cycles", -1)) != spec["active_commit_reads"]:
        fail(f"{name} EventConv active commit read counter mismatch")
    if int(config.get("neuron_spike_cnt", -1)) != len(spec["output_words"]):
        fail(f"{name} EventConv commit emit counter mismatch")
    if ((int(config.get("status", 0)) >> 1) & 0xFF) != spec["active_neurons_after_commit"]:
        fail(f"{name} active neuron count after commit mismatch")
    if int(config.get("state_checksum", -1)) != spec["state_checksum"]:
        fail(f"{name} config state checksum mismatch")
    if int(config.get("output_br_drops", -1)) != 0:
        fail(f"{name} output bridge drops must be zero")

    bitstream = require_mapping(result.get("bitstream"), f"{name} bitstream")
    hwh = require_mapping(result.get("hwh"), f"{name} hwh")
    if bitstream.get("sha256") != BIT_SHA256:
        fail(f"{name} bitstream sha256 mismatch")
    if hwh.get("sha256") != HWH_SHA256:
        fail(f"{name} HWH sha256 mismatch")


def main() -> int:
    if not REPORT_MD.exists():
        fail(f"missing report: {REPORT_MD}")
    if "TO_BE_FILLED" in BIT_SHA256 or "TO_BE_FILLED" in HWH_SHA256:
        fail("bit/hwh sha256 constants must be filled after rebuild")

    for name, spec in TRACE_SPECS.items():
        check_trace_result(name, spec)

    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in [
        "PYNQ-Z2 EventConv trace smokes passed",
        "tiny",
        "burst-boundary",
        "multi-commit",
        "boundary coordinates skip invalid taps",
        "state checksum",
        "not latency",
        BIT_SHA256,
        HWH_SHA256,
    ]:
        if phrase not in text:
            fail(f"report missing phrase: {phrase}")

    print("PASS: SpikeMold PYNQ-Z2 EventConv trace smoke evidence valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
