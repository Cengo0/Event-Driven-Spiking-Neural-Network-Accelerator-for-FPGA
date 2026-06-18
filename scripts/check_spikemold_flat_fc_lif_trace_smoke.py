#!/usr/bin/env python3
"""Check SpikeMold PYNQ-Z2 tiny flat FC-LIF trace/readout smoke evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from spikepress import InputSpike, fc_lif_model  # noqa: E402
from spikepress.transport import lower_eventword64_inputs_to_axis32, pack_input_spikes  # noqa: E402


BOARD_JSON = ROOT / "outputs" / "board" / "flat_fc_lif_trace_smoke_result_20260614.json"
REPORT_MD = ROOT / "reports" / "spikemold_flat_fc_lif_trace_smoke_report.md"
SCHEMA = "spikemold.pynq_flat_fc_lif_trace_smoke.v1"
EVIDENCE_LEVEL = "pynq_board_flat_fc_lif_commit_value_state_checksum_smoke"
CLAIM_BOUNDARY = "pynq_axi_dma0_direct_rtl_tiny_flat_fc_lif_commit_value_state_checksum_readback"
BIT_SHA256 = "5b6b3d64a8263b3e6b075c934bcef0d3684d576756cba600711d2918d863d1d0"
HWH_SHA256 = "9447e36cbfc687c8cf0683b6ae05671ad4ef9bb017ef78c1a0777b73d6a87ec3"
EXPECTED_AXIS32 = [8192, 2105345, 4202496]
EXPECTED_OUTPUT_WORDS = [40962]
EXPECTED_READOUT_IDS = [2]
EXPECTED_COMMIT_VALUES = [5]
EXPECTED_FINAL_STATE = {"2": 3, "3": 2}
EXPECTED_STATE_CHECKSUM = 5


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


def expected_trace() -> dict:
    model = fc_lif_model(
        "batch_1b_tiny_fc_lif",
        weights=[[3, 1], [2, 0]],
        thresholds=[5, 9],
    )
    spikes = [
        InputSpike(tick=0, src_id=0),
        InputSpike(tick=1, src_id=1),
        InputSpike(tick=2, src_id=0),
    ]
    trace = model.golden_trace(spikes).to_dict()
    return {
        "trace": trace,
        "input_eventword64": pack_input_spikes(spikes),
        "input_axis32": lower_eventword64_inputs_to_axis32(pack_input_spikes(spikes)),
        "readout_ids": [commit["dst_id"] for commit in trace["commits"]],
    }


def main() -> int:
    if not BOARD_JSON.exists():
        fail(f"missing board JSON: {BOARD_JSON}")
    if not REPORT_MD.exists():
        fail(f"missing report: {REPORT_MD}")

    result = load_json(BOARD_JSON)
    expected = expected_trace()
    trace = expected["trace"]
    counters = trace["counters"]

    if result.get("schema") != SCHEMA:
        fail("schema mismatch")
    if result.get("evidence_level") != EVIDENCE_LEVEL:
        fail("evidence level mismatch")
    if result.get("claim_boundary") != CLAIM_BOUNDARY:
        fail("claim boundary mismatch")
    if result.get("board_executed") is not True:
        fail("board_executed must be true")
    if result.get("ok") is not True:
        fail("flat FC-LIF trace smoke ok must be true")

    model = require_mapping(result.get("model"), "model")
    if model.get("weights") != [[3, 1], [2, 0]]:
        fail("model weights mismatch")
    if model.get("thresholds") != [5, 9]:
        fail("model thresholds mismatch")
    if model.get("global_threshold_used") != 5:
        fail("global threshold mismatch")
    semantic_limit = str(model.get("semantic_limit", ""))
    if "commit value" not in semantic_limit or "final membrane checksum" not in semantic_limit:
        fail("semantic limit missing commit value/checksum boundary")

    state_reset = require_mapping(result.get("state_reset_boundary"), "state_reset_boundary")
    if state_reset.get("fresh_overlay_loaded") is not True:
        fail("fresh overlay boundary missing")
    if state_reset.get("hls_soft_reset_clears_membrane_bram") is not False:
        fail("HLS soft reset must not be claimed to clear membrane BRAM")
    if state_reset.get("state_checksum_valid_after_soft_reset") is not False:
        fail("state checksum must not be marked valid after soft reset alone")
    if "fresh overlay" not in str(state_reset.get("state_checksum_validity", "")):
        fail("state checksum validity boundary missing")

    if result.get("input_eventword64") != expected["input_eventword64"]:
        fail("input EventWord64 mismatch")
    if result.get("input_axis32") != EXPECTED_AXIS32:
        fail("input AXIS32 mismatch")
    if expected["input_axis32"] != EXPECTED_AXIS32:
        fail("host lowering expected AXIS32 mismatch")
    if counters.get("generated_update_count") != 5:
        fail("golden generated update count mismatch")
    if counters.get("commit_count") != 1:
        fail("golden commit count mismatch")
    if trace.get("commits") != [{"kind": "commit", "tick": 1, "dst_id": 2, "value": 5}]:
        fail("golden commit mismatch")

    expected_section = require_mapping(result.get("expected"), "expected")
    if expected_section.get("generated_updates") != counters.get("generated_update_count"):
        fail("expected generated update count mismatch")
    if expected_section.get("readout_ids") != EXPECTED_READOUT_IDS:
        fail("expected readout ids mismatch")
    if expected_section.get("commit_values") != EXPECTED_COMMIT_VALUES:
        fail("expected commit values mismatch")
    if expected_section.get("output_words") != EXPECTED_OUTPUT_WORDS:
        fail("expected output words mismatch")
    if expected_section.get("final_state") != EXPECTED_FINAL_STATE:
        fail("expected final state mismatch")
    if expected_section.get("state_checksum") != EXPECTED_STATE_CHECKSUM:
        fail("expected state checksum mismatch")

    output = require_mapping(result.get("output"), "output")
    if output.get("readout_ids") != EXPECTED_READOUT_IDS:
        fail("board readout ids mismatch")
    if output.get("commit_values") != EXPECTED_COMMIT_VALUES:
        fail("board commit values mismatch")
    if output.get("output_words") != EXPECTED_OUTPUT_WORDS:
        fail("board output words mismatch")
    if output.get("state_checksum") != EXPECTED_STATE_CHECKSUM:
        fail("board state checksum mismatch")
    if output.get("readout_ids") != expected["readout_ids"]:
        fail("board readout ids do not match golden commit dst ids")

    required = require_mapping(result.get("required_checks"), "required_checks")
    for key in [
        "reset_ap_done",
        "release_ap_done",
        "trace_ap_done",
        "hls_version_matches",
        "config_version_matches",
        "input_count_reached",
        "router_accept_count_reached",
        "router_update_count_reached",
        "neuron_spike_count_matches",
        "output_words_match",
        "output_ids_match",
        "output_commit_values_match",
        "state_checksum_matches",
        "output_bridge_events_match",
        "output_bridge_emits_match",
    ]:
        if required.get(key) is not True:
            fail(f"required check failed: {key}")

    config = require_mapping(result.get("config_after"), "config_after")
    if int(config.get("pl_busy_cycles", 0)) < 3:
        fail("input counter did not reach 3")
    if int(config.get("output_drain_cycles", 0)) < 3:
        fail("router accept counter did not reach 3")
    if int(config.get("router_spike_cnt", 0)) < 5:
        fail("router update count did not reach 5")
    if int(config.get("neuron_spike_cnt", -1)) != 1:
        fail("neuron spike count mismatch")
    if int(config.get("output_br_events", -1)) != 1:
        fail("output bridge event count mismatch")
    if int(config.get("output_br_emits", -1)) != 1:
        fail("output bridge emit count mismatch")
    if int(config.get("output_br_drops", -1)) != 0:
        fail("output bridge drops must be zero")
    if int(config.get("state_checksum", -1)) != EXPECTED_STATE_CHECKSUM:
        fail("config state checksum mismatch")

    bitstream = require_mapping(result.get("bitstream"), "bitstream")
    hwh = require_mapping(result.get("hwh"), "hwh")
    if bitstream.get("sha256") != BIT_SHA256:
        fail("bitstream sha256 mismatch")
    if hwh.get("sha256") != HWH_SHA256:
        fail("HWH sha256 mismatch")

    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in [
        "PYNQ-Z2 tiny flat FC-LIF trace smoke passed",
        CLAIM_BOUNDARY,
        "commit value readback",
        "commit values",
        "state checksum",
        "raw board diagnostics",
        "not latency",
        BIT_SHA256,
        HWH_SHA256,
    ]:
        if phrase not in text:
            fail(f"report missing phrase: {phrase}")

    print("PASS: SpikeMold PYNQ-Z2 flat FC-LIF trace smoke evidence valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
