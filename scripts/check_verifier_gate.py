#!/usr/bin/env python3
"""Independent board-free verifier gate for SpikePress + SpikeMold."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from spikepress.architecture_trace_generator import TRACE_SCHEMA, sha256_json  # noqa: E402
from spikepress.spikemold_runtime_contract import (  # noqa: E402
    SPIKEMOLD_RUNTIME_BACKEND_ID,
    SPIKEMOLD_RUNTIME_CONTRACT_SCHEMA,
    SPIKEMOLD_RUNTIME_RESOURCE_REPORT_SCHEMA,
    sha256_json as sha256_runtime_json,
)
from spikepress.pynq_runtime import PYNQ_ONESHOT_SCHEMA, SpikeMoldPynqRunConfig  # noqa: E402


REPORT_PATH = ROOT / "reports" / "verifier_gate_review.md"
CONTRACT_DIR = ROOT / "contracts"
TRACE_DIR = ROOT / "golden_traces" / "v1"
EVENT_BUDGET_PATH = ROOT / "outputs" / "event_budget" / "recommended_flat_fc_lif_config.json"
TRANSPORT_PATH = ROOT / "outputs" / "transport" / "batch_1b_transport_flat_fc_lif_smoke.json"
ARCH_SANDBOX_PATH = ROOT / "outputs" / "architecture_sandbox" / "batch_1x_architecture_sandbox.json"
RUNTIME_CONTRACT_PATH = ROOT / "outputs" / "runtime" / "spikemold_runtime_contract.json"
RESOURCE_REPORT_PATH = ROOT / "outputs" / "resource" / "spikemold_runtime_resource_report.json"
EVENTCONV_OOC_SYNTHESIS_PATH = ROOT / "outputs" / "resource" / "eventconv_ooc_synthesis_report.json"
BUILD_EVIDENCE_PATH = ROOT / "outputs" / "resource" / "spikemold_build_evidence_report.json"
BOARD_SPIKE_SMOKE_PATH = ROOT / "outputs" / "board" / "dma_spike_smoke_result_20260614.json"
EVENTWORD64_BOARD_SPIKE_SMOKE_PATH = (
    ROOT / "outputs" / "board" / "dma_spike_smoke_eventword64_result_20260614.json"
)
FLAT_FC_LIF_BOARD_SMOKE_PATH = ROOT / "outputs" / "board" / "flat_fc_lif_trace_smoke_result_20260614.json"
EVENTCONV_BOARD_SMOKE_PATH = ROOT / "outputs" / "board" / "eventconv_trace_smoke_result_20260614.json"
PYNQ_ONESHOT_SCRIPT = ROOT / "scripts" / "run_spikemold_pynq_one_shot.py"
BOARD_SPIKE_SMOKE_SCHEMA = "spikemold.pynq_dma_spike_smoke.v2"
BOARD_SPIKE_SMOKE_CLAIM_BOUNDARY = "pynq_axi_dma0_direct_rtl_one_spike_event_to_post_spike_readback_only_no_dataset"
BOARD_SPIKE_SMOKE_BIT_SHA256 = "5b6b3d64a8263b3e6b075c934bcef0d3684d576756cba600711d2918d863d1d0"
BOARD_SPIKE_SMOKE_HWH_SHA256 = "9447e36cbfc687c8cf0683b6ae05671ad4ef9bb017ef78c1a0777b73d6a87ec3"
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
EVENTCONV_BOARD_SCHEMA = "spikemold.pynq_eventconv_trace_smoke.v1"
EVENTCONV_TRACE_SPECS = {
    "tiny": {
        "path": EVENTCONV_BOARD_SMOKE_PATH,
        "evidence_level": "pynq_board_eventconv_multi_commit_state_checksum_smoke",
        "claim_boundary": "pynq_axi_dma0_direct_rtl_tiny_eventconv_multi_commit_state_checksum_readback",
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
INFERENCE_ONLY_SURFACE_FILES = [
    ROOT / "hardware" / "hls" / "include" / "spikemold_top_hls.h",
    ROOT / "hardware" / "hls" / "src" / "spikemold_top_hls.cpp",
    ROOT / "hardware" / "hls" / "test" / "tb_spikemold_top_hls.cpp",
    ROOT / "hardware" / "scripts" / "rebuild_integrated.tcl",
    ROOT / "hardware" / "hdl" / "rtl" / "top" / "spikemold_integrated_top.v",
    ROOT / "hardware" / "hdl" / "rtl" / "top" / "spikemold_coregroup_top.v",
    ROOT / "hardware" / "hdl" / "rtl" / "core" / "event_router_ng.v",
    ROOT / "hardware" / "hdl" / "tb" / "tb_router_ct.v",
    ROOT / "hardware" / "hdl" / "tb" / "tb_integration.v",
    ROOT / "config" / "generated" / "spikemold_params.vh",
    ROOT / "config" / "generated" / "spikemold_params.py",
    ROOT / "config" / "generated" / "spikemold_params.h",
]
FORBIDDEN_INFERENCE_SURFACE_TOKENS = [
    "learning_params_t",
    "learn_spike",
    "learn_weight",
    "MODE_TRAIN_STDP",
    "reward_signal",
    "debug_learning_active",
    "SNN_EVENT_ROUTER_LEARNING_ENABLE",
    "SNN_CORE_GROUP_LEARNING_ENABLE",
    "SNN_HLS_LEARNING_ENABLE",
    "LEARN_NOTIFY_ENABLE",
    "ST_LEARN_NOTIFY",
    "ST_WEIGHT_FWD",
    "STDP",
    "R-STDP",
    "rstdp",
    "stdp",
]

REQUIRED_CONTRACTS = [
    "ARCHITECTURE_CONTRACT_V1.md",
    "INTEGER_SEMANTICS_V1.md",
    "EVENT_FORMAT_V1.md",
    "TRACE_SCHEMA_V1.md",
    "REGISTER_MAP_MINIMAL_V1.md",
    "RESOURCE_BUDGET_V1.md",
    "ARCHITECTURE_PATTERN_POLICY_V1.md",
    "AGENT_HANDOFF_PROTOCOL_V1.md",
]

REQUIRED_TRACES = [
    "fc_lif_tiny_v1.json",
    "eventconv_agu_c0_tiny_v1.json",
    "eventconv_8x8_tiny_v1.json",
]

TRACE_COUNTERS = [
    "input_event_count",
    "generated_update_count",
    "active_neuron_count",
    "commit_count",
    "state_reads",
    "state_writes",
    "ddr_bytes_inner_loop",
    "python_inner_loop_steps",
]


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
    result = load_json(FLAT_FC_LIF_BOARD_SMOKE_PATH)
    config_after = result.get("config_after", {})
    return {
        "path": str(FLAT_FC_LIF_BOARD_SMOKE_PATH.relative_to(ROOT)),
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


def check_eventconv_board_smoke() -> None:
    for name, spec in EVENTCONV_TRACE_SPECS.items():
        path = spec["path"]
        if not isinstance(path, Path):
            fail(f"EventConv {name} path must be Path")
        if not path.exists():
            fail(f"missing EventConv board smoke: {path}")
        check_eventconv_trace_result(name, spec, load_json(path))


def check_eventconv_trace_result(name: str, spec: Mapping[str, object], result: Mapping[str, object]) -> None:
    config_after = result.get("config_after", {})
    if result.get("schema") != EVENTCONV_BOARD_SCHEMA:
        fail(f"EventConv {name} board schema mismatch")
    if result.get("variant") != name:
        fail(f"EventConv {name} variant mismatch")
    if result.get("evidence_level") != spec["evidence_level"]:
        fail(f"EventConv {name} board evidence level mismatch")
    if result.get("claim_boundary") != spec["claim_boundary"]:
        fail(f"EventConv {name} board claim boundary mismatch")
    if result.get("board_executed") is not True or result.get("ok") is not True:
        fail(f"EventConv {name} board smoke must execute and pass")
    if result.get("bitstream", {}).get("sha256") != BOARD_SPIKE_SMOKE_BIT_SHA256:
        fail(f"EventConv {name} board bitstream sha256 mismatch")
    if result.get("hwh", {}).get("sha256") != BOARD_SPIKE_SMOKE_HWH_SHA256:
        fail(f"EventConv {name} board HWH sha256 mismatch")
    if result.get("input_axis32") != spec["input_axis32"]:
        fail(f"EventConv {name} board input AXIS32 mismatch")
    expected = result.get("expected", {})
    output = result.get("output", {})
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
            fail(f"EventConv {name} expected {key} mismatch")
    for key, spec_key in [
        ("output_words", "output_words"),
        ("readout_ids", "readout_ids"),
        ("commit_values", "commit_values"),
        ("state_checksum", "state_checksum"),
    ]:
        if output.get(key) != spec[spec_key]:
            fail(f"EventConv {name} board {key} mismatch")
    if config_after.get("backend_mode") != 1:
        fail(f"EventConv {name} backend mode mismatch")
    if config_after.get("router_spike_cnt") != spec["generated_updates"]:
        fail(f"EventConv {name} update counter mismatch")
    if config_after.get("output_drain_cycles") != spec["active_commit_reads"]:
        fail(f"EventConv {name} active commit read counter mismatch")
    if config_after.get("neuron_spike_cnt") != len(spec["output_words"]):
        fail(f"EventConv {name} commit emit counter mismatch")
    if ((int(config_after.get("status", 0)) >> 1) & 0xFF) != spec["active_neurons_after_commit"]:
        fail(f"EventConv {name} active neuron count mismatch")
    if config_after.get("state_checksum") != spec["state_checksum"]:
        fail(f"EventConv {name} config state checksum mismatch")
    if config_after.get("output_br_drops") != 0:
        fail(f"EventConv {name} output drops must be zero")
    required = result.get("required_checks", {})
    for key in [
        "backend_mode_matches",
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
            fail(f"EventConv {name} board required check failed: {key}")


def require_text(path: Path, phrases: list[str]) -> str:
    if not path.exists():
        fail(f"missing text artifact: {path}")
    text = path.read_text(encoding="utf-8")
    for phrase in phrases:
        if phrase not in text:
            fail(f"{path} missing phrase: {phrase}")
    return text


def check_trace_hashes(path: Path, trace: Mapping[str, object]) -> None:
    hashes = trace.get("hashes", {})
    if not isinstance(hashes, Mapping):
        fail(f"{path} missing hashes")
    for hash_key, body_key in [
        ("input_sha256", "inputs"),
        ("updates_sha256", "updates"),
        ("commits_sha256", "commits"),
        ("final_state_sha256", "final_state"),
    ]:
        if hashes.get(hash_key) != sha256_json(trace.get(body_key)):
            fail(f"{path} hash mismatch: {hash_key}")
    body = dict(trace)
    body["hashes"] = dict(hashes)
    expected = body["hashes"].pop("trace_sha256", None)
    if expected != sha256_json(body):
        fail(f"{path} trace_sha256 mismatch")


def check_contracts() -> None:
    missing = [name for name in REQUIRED_CONTRACTS if not (CONTRACT_DIR / name).exists()]
    if missing:
        fail(f"missing contracts: {missing}")

    policy = (CONTRACT_DIR / "ARCHITECTURE_PATTERN_POLICY_V1.md").read_text(encoding="utf-8")
    for phrase in [
        "Do not ban architecture names. Ban failure modes.",
        "page",
        "tile",
        "coregroup",
        "shared-kernel EventConv AGU",
        "Python-controlled event loop",
        "random DDR synapse fetch per event",
        "full-neuron scan every timestep as the primary mode",
        "silent semantic changes",
    ]:
        if phrase not in policy:
            fail(f"architecture pattern policy missing: {phrase}")

    handoff = (CONTRACT_DIR / "AGENT_HANDOFF_PROTOCOL_V1.md").read_text(encoding="utf-8")
    for phrase in [
        "Status: active contract",
        "ARCHITECTURE_PATTERN_POLICY_V1.md",
        "architecture policy and forbidden failure mode check result",
        "evidence level reached",
    ]:
        if phrase not in handoff:
            fail(f"agent handoff protocol missing: {phrase}")


def check_traces() -> None:
    for name in REQUIRED_TRACES:
        path = TRACE_DIR / name
        if not path.exists():
            fail(f"missing trace: {path}")
        trace = load_json(path)
        if trace.get("schema") != TRACE_SCHEMA:
            fail(f"{path} schema mismatch")
        counters = trace.get("counters", {})
        if not isinstance(counters, Mapping):
            fail(f"{path} counters must be mapping")
        for key in TRACE_COUNTERS:
            if key not in counters:
                fail(f"{path} missing counter: {key}")
        if counters.get("ddr_bytes_inner_loop") != 0:
            fail(f"{path} inner-loop DDR bytes must be zero")
        if counters.get("python_inner_loop_steps") != 0:
            fail(f"{path} Python inner-loop steps must be zero")
        check_trace_hashes(path, trace)


def check_event_budget() -> None:
    budget = load_json(EVENT_BUDGET_PATH)
    if budget.get("schema") != "spikemold.event_budget.v1":
        fail("event budget schema mismatch")
    if budget.get("all_ok") is not True:
        fail("event budget all_ok must be true")
    histogram = budget.get("counter_histogram", {})
    if not isinstance(histogram, Mapping):
        fail("event budget missing counter_histogram")
    for key in ["ddr_bytes_inner_loop", "python_inner_loop_steps"]:
        item = histogram.get(key, {})
        if not isinstance(item, Mapping) or item.get("max") != 0:
            fail(f"event budget {key} max must be zero")


def check_board_smoke_section(
    *,
    transport: Mapping[str, object],
    source_json: Path,
    section_key: str,
    expect_eventword64_lowering: bool,
) -> None:
    if not source_json.exists():
        if section_key in transport:
            fail(f"transport has {section_key} but source board JSON is missing")
        return

    board_result = load_json(source_json)
    if board_result.get("schema") != BOARD_SPIKE_SMOKE_SCHEMA:
        fail(f"{section_key} schema mismatch")
    if board_result.get("board_executed") is not True:
        fail(f"{section_key} did not execute")
    if board_result.get("ok") is not True:
        fail(f"{section_key} ok must be true")
    if board_result.get("claim_boundary") != BOARD_SPIKE_SMOKE_CLAIM_BOUNDARY:
        fail(f"{section_key} claim boundary mismatch")

    board_smoke = transport.get(section_key, {})
    if not isinstance(board_smoke, Mapping):
        fail(f"transport missing {section_key} section")
    if dict(board_smoke) != summarize_board_smoke(source_json):
        fail(f"transport {section_key} is stale or does not match source board JSON")
    for key, expected in [
        ("schema", BOARD_SPIKE_SMOKE_SCHEMA),
        ("claim_boundary", BOARD_SPIKE_SMOKE_CLAIM_BOUNDARY),
        ("bitstream_sha256", BOARD_SPIKE_SMOKE_BIT_SHA256),
        ("hwh_sha256", BOARD_SPIKE_SMOKE_HWH_SHA256),
    ]:
        if board_smoke.get(key) != expected:
            fail(f"transport {section_key} {key} mismatch")
    for key in [
        "pl_busy_cycles_counter",
        "output_drain_cycles_counter",
        "router_spike_cnt",
        "neuron_spike_cnt",
        "output_br_events",
        "output_br_emits",
    ]:
        if int(board_smoke.get(key, 0)) < 1:
            fail(f"transport {section_key} counter must be nonzero: {key}")
    for key in ["axis_input_seen_nonzero_check", "axis_router_accept_nonzero_check"]:
        if board_smoke.get(key) is not True:
            fail(f"transport {section_key} check must be true: {key}")
    decoded = board_smoke.get("output_decoded", {})
    if (
        not isinstance(decoded, Mapping)
        or decoded.get("id") != 1
        or decoded.get("commit_value_u16") != 1
        or decoded.get("reserved_top3") != 0
    ):
        fail(f"transport {section_key} output decode mismatch")

    lowering = board_smoke.get("eventword64_lowering")
    if expect_eventword64_lowering:
        if not isinstance(lowering, Mapping):
            fail(f"transport {section_key} missing EventWord64 lowering")
        if lowering.get("input_eventword64") != EVENTWORD64_INPUT_WORD:
            fail(f"transport {section_key} EventWord64 input mismatch")
        if lowering.get("output_axis32") != EVENTWORD64_LOWERED_AXIS32:
            fail(f"transport {section_key} lowered AXIS32 mismatch")
        if lowering.get("lossless_flat_input_semantics") is not True:
            fail(f"transport {section_key} lowering must preserve flat semantics")
    elif lowering is not None:
        fail(f"transport {section_key} unexpectedly includes EventWord64 lowering")


def check_transport() -> None:
    transport = load_json(TRANSPORT_PATH)
    if transport.get("all_ok") is not True:
        fail("transport all_ok must be true")
    any_board = (
        BOARD_SPIKE_SMOKE_PATH.exists()
        or EVENTWORD64_BOARD_SPIKE_SMOKE_PATH.exists()
        or FLAT_FC_LIF_BOARD_SMOKE_PATH.exists()
        or EVENTCONV_BOARD_SMOKE_PATH.exists()
    )
    if any_board:
        if transport.get("board_executed") is not True:
            fail("transport must reflect board smoke execution")
        expected_evidence = (
            "software_transport_plus_pynq_flat_fc_lif_commit_value_state_checksum_smoke"
            if FLAT_FC_LIF_BOARD_SMOKE_PATH.exists()
            else (
                "software_transport_plus_pynq_direct_rtl_eventword64_smoke"
                if EVENTWORD64_BOARD_SPIKE_SMOKE_PATH.exists()
                else "software_transport_plus_pynq_direct_rtl_spike_smoke"
            )
        )
        if transport.get("evidence_level") != expected_evidence:
            fail("transport evidence level must match board smoke")
        check_board_smoke_section(
            transport=transport,
            source_json=BOARD_SPIKE_SMOKE_PATH,
            section_key="board_smoke",
            expect_eventword64_lowering=False,
        )
        check_board_smoke_section(
            transport=transport,
            source_json=EVENTWORD64_BOARD_SPIKE_SMOKE_PATH,
            section_key="eventword64_board_smoke",
            expect_eventword64_lowering=True,
        )
        if FLAT_FC_LIF_BOARD_SMOKE_PATH.exists():
            flat = transport.get("flat_fc_lif_board_smoke")
            if not isinstance(flat, Mapping):
                fail("transport missing flat_fc_lif_board_smoke section")
            if dict(flat) != summarize_flat_fc_lif_board_smoke():
                fail("transport flat_fc_lif_board_smoke is stale or does not match source board JSON")
            if flat.get("schema") != FLAT_FC_LIF_BOARD_SCHEMA:
                fail("flat FC-LIF board schema mismatch")
            if flat.get("claim_boundary") != FLAT_FC_LIF_CLAIM_BOUNDARY:
                fail("flat FC-LIF board claim boundary mismatch")
            if flat.get("board_executed") is not True or flat.get("ok") is not True:
                fail("flat FC-LIF board smoke must execute and pass")
            if flat.get("bitstream_sha256") != BOARD_SPIKE_SMOKE_BIT_SHA256:
                fail("flat FC-LIF board bitstream sha256 mismatch")
            if flat.get("hwh_sha256") != BOARD_SPIKE_SMOKE_HWH_SHA256:
                fail("flat FC-LIF board HWH sha256 mismatch")
            if flat.get("input_axis32") != FLAT_FC_LIF_INPUT_AXIS32:
                fail("flat FC-LIF board input AXIS32 mismatch")
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
                fail("flat FC-LIF board reset boundary mismatch")
            if flat.get("state_reset_boundary", {}).get("state_checksum_valid_after_soft_reset") is not False:
                fail("flat FC-LIF board checksum reset boundary mismatch")
            for key in [
                "input_count_reached",
                "router_update_count_reached",
                "output_words_match",
                "output_ids_match",
                "output_commit_values_match",
                "state_checksum_matches",
            ]:
                if flat.get("required_checks", {}).get(key) is not True:
                    fail(f"flat FC-LIF board required check failed: {key}")
    else:
        if transport.get("board_executed") is not False:
            fail("transport must not claim board execution")
    assumptions = transport.get("runtime_assumptions", {})
    if not isinstance(assumptions, Mapping):
        fail("transport missing runtime assumptions")
    for key in ["python_inner_loop_required", "random_ddr_inner_loop", "full_neuron_scan_primary"]:
        if assumptions.get(key) is not False:
            fail(f"transport forbidden assumption must be false: {key}")
    flat_fc_lif = transport.get("flat_fc_lif", {})
    if not isinstance(flat_fc_lif, Mapping):
        fail("transport missing SpikeMold flat FC-LIF section")
    axis32 = transport.get("eventword64_to_axis32", {})
    if not isinstance(axis32, Mapping):
        fail("transport missing EventWord64 to AXIS32 lowering section")
    if axis32.get("schema") != "spikemold.eventword64_to_axis32_lowering.v1":
        fail("EventWord64 to AXIS32 lowering schema mismatch")
    if axis32.get("ok") is not True:
        fail("EventWord64 to AXIS32 lowering must pass")
    if axis32.get("board_executed") is not False:
        fail("EventWord64 to AXIS32 lowering must not claim board execution")
    if axis32.get("lossless_flat_input_semantics") is not True:
        fail("EventWord64 to AXIS32 lowering must preserve flat input semantics")
    for key, value in [
        ("trace_match_rate", 1.0),
        ("readout_match", True),
        ("state_checksum_match", True),
    ]:
        if flat_fc_lif.get(key) != value:
            fail(f"SpikeMold flat FC-LIF {key} mismatch")


def check_architecture_sandbox() -> None:
    sandbox = load_json(ARCH_SANDBOX_PATH)
    if sandbox.get("schema") != "spikemold.batch_1x_architecture_sandbox.v1":
        fail("architecture sandbox schema mismatch")
    if sandbox.get("all_ok") is not True:
        fail("architecture sandbox all_ok must be true")
    if sandbox.get("board_executed") is not False:
        fail("architecture sandbox must not claim board execution")
    if sandbox.get("mainline_switch_recommended") is not False:
        fail("architecture sandbox must not switch mainline")
    candidates = sandbox.get("candidates", {})
    if not isinstance(candidates, Mapping):
        fail("architecture sandbox missing candidates")
    for candidate_id in ["coregroup_2x64", "page_block_256_updates", "tile_microbatch_4x4"]:
        candidate = candidates.get(candidate_id, {})
        if not isinstance(candidate, Mapping):
            fail(f"missing candidate: {candidate_id}")
        for correctness in candidate.get("correctness", []):
            if correctness.get("trace_match_rate") != 1.0:
                fail(f"{candidate_id} trace_match_rate mismatch")
            if correctness.get("readout_match") is not True:
                fail(f"{candidate_id} readout_match mismatch")
            if correctness.get("state_checksum_match") is not True:
                fail(f"{candidate_id} state_checksum_match mismatch")
        memory = candidate.get("memory_estimate", {})
        runtime = candidate.get("runtime_estimate", {})
        if memory.get("ddr_bytes_inner_loop") != 0:
            fail(f"{candidate_id} inner-loop DDR bytes must be zero")
        if runtime.get("python_calls_per_inference") != 0:
            fail(f"{candidate_id} Python calls per inference must be zero")


def check_runtime_resource() -> None:
    runtime = load_json(RUNTIME_CONTRACT_PATH)
    if runtime.get("schema") != SPIKEMOLD_RUNTIME_CONTRACT_SCHEMA:
        fail("runtime contract schema mismatch")
    if runtime.get("selected_backend") != SPIKEMOLD_RUNTIME_BACKEND_ID:
        fail("runtime backend mismatch")
    if runtime.get("board_executed") is not False:
        fail("runtime must not claim board execution")
    invariants = runtime.get("runtime_invariants", {})
    for key in ["python_inner_loop_required", "random_ddr_inner_loop", "full_neuron_scan_primary"]:
        if invariants.get(key) is not False:
            fail(f"runtime invariant must be false: {key}")
    if "learning" in runtime.get("selected_backend", ""):
        fail("selected backend must not include learning engine")

    body = dict(runtime)
    hashes = dict(body.pop("hashes", {}))
    if hashes.get("runtime_contract_sha256") != sha256_runtime_json(body):
        fail("runtime contract hash mismatch")

    resource = load_json(RESOURCE_REPORT_PATH)
    if resource.get("schema") != SPIKEMOLD_RUNTIME_RESOURCE_REPORT_SCHEMA:
        fail("resource report schema mismatch")
    if resource.get("selected_backend") != SPIKEMOLD_RUNTIME_BACKEND_ID:
        fail("resource backend mismatch")
    if resource.get("evidence_level") != "board_free_resource_report_with_eventconv_ooc_synthesis":
        fail("resource evidence level mismatch")
    if resource.get("board_executed") is not False:
        fail("resource report must not claim board execution")
    if resource.get("runtime_contract_sha256") != hashes.get("runtime_contract_sha256"):
        fail("resource report runtime hash link mismatch")
    failure_modes = resource.get("forbidden_failure_modes", {})
    for key in [
        "python_inner_loop_required",
        "random_ddr_inner_loop",
        "full_neuron_scan_primary",
        "unbounded_fanout",
        "silent_semantic_change",
    ]:
        if failure_modes.get(key) is not False:
            fail(f"resource forbidden mode must be false: {key}")

    eventconv_ooc = load_json(EVENTCONV_OOC_SYNTHESIS_PATH)
    if eventconv_ooc.get("schema") != "spikemold.eventconv_ooc_synthesis.v1":
        fail("EventConv OOC synthesis schema mismatch")
    if eventconv_ooc.get("evidence_level") != "vivado_ooc_synthesis_no_board":
        fail("EventConv OOC synthesis evidence level mismatch")
    if eventconv_ooc.get("board_executed") is not False:
        fail("EventConv OOC synthesis must not claim board execution")
    if eventconv_ooc.get("claim_boundary") != "eventconv_ooc_synthesis_only_no_bitstream_no_board":
        fail("EventConv OOC synthesis claim boundary mismatch")
    if eventconv_ooc.get("all_blocks_synthesized") is not True:
        fail("EventConv OOC synthesis all_blocks_synthesized must be true")
    if eventconv_ooc.get("all_timing_met") is not True:
        fail("EventConv OOC synthesis all_timing_met must be true")
    if eventconv_ooc.get("all_dsp_zero") is not True:
        fail("EventConv OOC synthesis all_dsp_zero must be true")
    if eventconv_ooc.get("all_bram_tile_zero") is not True:
        fail("EventConv OOC synthesis all_bram_tile_zero must be true")

    resource_ooc = resource.get("eventconv_ooc_synthesis", {})
    if not isinstance(resource_ooc, Mapping):
        fail("resource report missing EventConv OOC synthesis evidence")
    if resource_ooc.get("synthesis_report_sha256") != eventconv_ooc["hashes"]["synthesis_report_sha256"]:
        fail("resource report EventConv OOC synthesis hash mismatch")


def check_build_evidence() -> None:
    build = load_json(BUILD_EVIDENCE_PATH)
    if build.get("schema") != "spikemold.hls_vivado_build_evidence.v1":
        fail("SpikeMold build evidence schema mismatch")
    if build.get("evidence_level") != "hls_csim_hls_synth_vivado_routed_no_board":
        fail("SpikeMold build evidence level mismatch")
    if build.get("board_executed") is not False:
        fail("SpikeMold build evidence must not claim board execution")
    if build.get("claim_boundary") != "hls_csim_hls_synth_vivado_routed_bitstream_only_no_board_execution":
        fail("SpikeMold build evidence claim boundary mismatch")
    hls_csim = build.get("hls_csim", {})
    hls_synthesis = build.get("hls_synthesis", {})
    hls_csynth = build.get("hls_csynth", {})
    routed = build.get("vivado_routed", {})
    target = build.get("target", {})
    if not isinstance(hls_csim, Mapping) or hls_csim.get("passed") is not True:
        fail("SpikeMold HLS C-sim evidence must pass")
    if not isinstance(hls_synthesis, Mapping) or hls_synthesis.get("passed") is not True:
        fail("SpikeMold HLS synthesis evidence must pass")
    if not isinstance(hls_csynth, Mapping) or hls_csynth.get("timing_estimate_meets_target") is not True:
        fail("SpikeMold HLS csynth timing estimate must pass")
    if hls_csynth.get("resources", {}).get("dsp") != 0:
        fail("SpikeMold HLS csynth DSP usage must be zero")
    if not isinstance(routed, Mapping):
        fail("SpikeMold routed evidence missing")
    if routed.get("bitstream_and_hwh_present") is not True:
        fail("SpikeMold routed bit/HWH evidence missing")
    timing = routed.get("timing", {})
    if not isinstance(timing, Mapping):
        fail("SpikeMold routed timing details missing")
    timing_fields_ok = (
        float(timing.get("wns_ns", -999.0)) >= 0.0
        and timing.get("tns_failing_endpoints") == 0
        and timing.get("ths_failing_endpoints") == 0
        and timing.get("tpws_failing_endpoints") == 0
        and timing.get("report_says_timing_met") is True
    )
    if routed.get("all_timing_met") is not timing_fields_ok:
        fail("SpikeMold routed timing flag mismatch")
    expected_build_all_ok = (
        hls_csim.get("passed") is True
        and hls_synthesis.get("passed") is True
        and hls_csynth.get("timing_estimate_meets_target") is True
        and timing_fields_ok
        and routed.get("bitstream_and_hwh_present") is True
    )
    if build.get("all_ok") is not expected_build_all_ok:
        fail("SpikeMold build all_ok mismatch")
    if build.get("functional_artifact_ok") is not True:
        fail("SpikeMold functional bit/HWH artifact evidence must pass")
    if not isinstance(target, Mapping) or target.get("routed_clock_mhz") != 20.0:
        fail("SpikeMold routed clock must be 20 MHz")


def check_pynq_runtime_api() -> None:
    if PYNQ_ONESHOT_SCHEMA != "spikemold.pynq_oneshot_result.v1":
        fail("PYNQ one-shot schema mismatch")
    default_config = SpikeMoldPynqRunConfig(bitstream_path="placeholder.bit")
    if default_config.ip_name != "spikemold_ctrl_0":
        fail("PYNQ default IP name mismatch")
    if not PYNQ_ONESHOT_SCRIPT.exists():
        fail(f"missing PYNQ one-shot script: {PYNQ_ONESHOT_SCRIPT}")
    text = PYNQ_ONESHOT_SCRIPT.read_text(encoding="utf-8")
    for phrase in ["--bitstream", "--input-json", "--output-json", "run_spikemold_pynq_one_shot"]:
        if phrase not in text:
            fail(f"PYNQ one-shot script missing phrase: {phrase}")


def check_inference_only_surface() -> None:
    for path in INFERENCE_ONLY_SURFACE_FILES:
        if not path.exists():
            fail(f"missing inference-only surface file: {path}")
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_INFERENCE_SURFACE_TOKENS:
            if token in text:
                fail(f"{path} still exposes removed learning token: {token}")


def check_reports() -> None:
    required_reports = {
        "reports/batch_0_contract_freeze_report.md": [
            "Page, tile, and coregroup patterns are allowed on probation.",
            "This freeze is a design and software-contract milestone only.",
        ],
        "reports/batch_1a_software_foundation_report.md": [
            "Status: verifier gate complete",
            "No HLS, RTL, or board claim.",
        ],
        "reports/batch_1b_transport_flat_fc_lif_report.md": [
            "Board execution was not run",
            "software_transport_smoke_no_board",
        ],
        "reports/batch_1c_eventconv_primitive_report.md": [
            "C0 trace-locked tiny case",
            "C3 AGU + active-set commit",
            "pynq_axi_dma0_direct_rtl_eventconv_burst_boundary_state_checksum_readback",
        ],
        "reports/batch_1x_architecture_sandbox_report.md": [
            "Batch 1X Architecture Sandbox Report",
            "board-free",
            "`mainline_switch_recommended`: `False`",
        ],
        "reports/architecture_selection_v1.md": [
            "board_free_architecture_selection_no_board",
            "Winner for next implementation stage: **E hybrid backend**",
            "No architecture name is banned.",
        ],
        "reports/spikemold_runtime_resource_report.md": [
            "board_free_runtime_contract_no_board",
            "spikemold_fc_eventconv",
            "EventConv OOC Synthesis",
        ],
        "reports/eventconv_ooc_synthesis_report.md": [
            "EventConv Vivado OOC Synthesis Report",
            "EventConv Vivado OOC synthesis evidence generated",
            "eventconv_ooc_synthesis_only_no_bitstream_no_board",
        ],
        "reports/spikemold_build_evidence_report.md": [
            "SpikeMold HLS/Vivado Build Evidence Report",
            "HLS C-sim, HLS synthesis/IP package, and integrated Vivado route timing passed",
            "hls_csim_hls_synth_vivado_routed_bitstream_only_no_board_execution",
            "No board execution was run",
            "functional board smoke",
        ],
        "reports/spikemold_flat_fc_lif_trace_smoke_report.md": [
            "PYNQ-Z2 tiny flat FC-LIF trace smoke passed",
            FLAT_FC_LIF_CLAIM_BOUNDARY,
            "commit value",
            "state checksum",
        ],
        "reports/spikemold_eventconv_trace_smoke_report.md": [
            "PYNQ-Z2 EventConv trace smokes passed",
            "pynq_axi_dma0_direct_rtl_tiny_eventconv_multi_commit_state_checksum_readback",
            "pynq_axi_dma0_direct_rtl_eventconv_burst_boundary_state_checksum_readback",
            "EventConv backend mode",
            "multi-commit",
            "burst-boundary",
            "boundary coordinates skip invalid taps",
            "state checksum",
        ],
        "reports/verifier_gate_review.md": [
            "Status: board-free verifier gate passed",
            "Inference-Only Scope",
            "SpikeMold HLS/Vivado build evidence",
            "PYNQ one-shot runtime API",
            "No board execution was run",
        ],
    }
    if (
        BOARD_SPIKE_SMOKE_PATH.exists()
        or EVENTWORD64_BOARD_SPIKE_SMOKE_PATH.exists()
        or FLAT_FC_LIF_BOARD_SMOKE_PATH.exists()
        or EVENTCONV_BOARD_SMOKE_PATH.exists()
    ):
        required_reports["reports/batch_1b_transport_flat_fc_lif_report.md"] = [
            "Board Evidence",
            BOARD_SPIKE_SMOKE_CLAIM_BOUNDARY,
            BOARD_SPIKE_SMOKE_BIT_SHA256,
            BOARD_SPIKE_SMOKE_HWH_SHA256,
        ]
        required_reports["reports/verifier_gate_review.md"] = [
            "Status: verifier gate passed with direct RTL transport, flat FC-LIF, and EventConv board smokes",
            "Inference-Only Scope",
            "PYNQ-Z2 direct RTL spike transport smoke",
            BOARD_SPIKE_SMOKE_CLAIM_BOUNDARY,
            BOARD_SPIKE_SMOKE_BIT_SHA256,
            BOARD_SPIKE_SMOKE_HWH_SHA256,
            "No latency, throughput, energy, dataset",
        ]
    if EVENTWORD64_BOARD_SPIKE_SMOKE_PATH.exists():
        required_reports["reports/batch_1b_transport_flat_fc_lif_report.md"].extend(
            [
                "EventWord64-Lowered Board Smoke",
                str(EVENTWORD64_INPUT_WORD),
                str(EVENTWORD64_LOWERED_AXIS32),
                "lossless flat input semantics",
            ]
        )
    if FLAT_FC_LIF_BOARD_SMOKE_PATH.exists():
        required_reports["reports/batch_1b_transport_flat_fc_lif_report.md"].extend(
            [
                "Tiny Flat FC-LIF Board Trace Smoke",
                FLAT_FC_LIF_CLAIM_BOUNDARY,
                "commit value",
            ]
        )
        required_reports["reports/verifier_gate_review.md"].extend(
            [
                "tiny flat FC-LIF board commit-value/state-checksum smoke",
                FLAT_FC_LIF_CLAIM_BOUNDARY,
                "commit value",
                "state checksum",
            ]
        )
        required_reports["reports/verifier_gate_review.md"].extend(
            [
                "EventWord64-lowered input board smoke",
                str(EVENTWORD64_INPUT_WORD),
                str(EVENTWORD64_LOWERED_AXIS32),
            ]
        )
    if EVENTCONV_BOARD_SMOKE_PATH.exists():
        required_reports["reports/verifier_gate_review.md"].extend(
            [
                "tiny EventConv board commit-value/state-checksum smoke",
                str(EVENTCONV_TRACE_SPECS["tiny"]["claim_boundary"]),
                "EventConv backend mode: `1`",
                "EventConv input AXIS32 words: `[16842752]`",
                "EventConv expected/board commit values: `[2, 3, 4]`",
                "EventConv expected/board state checksum: `1`",
                "EventConv counters: `pl_busy_cycles=1`",
            ]
        )
    burst_path = EVENTCONV_TRACE_SPECS["burst-boundary"]["path"]
    if isinstance(burst_path, Path) and burst_path.exists():
        required_reports["reports/verifier_gate_review.md"].extend(
            [
                "burst-boundary EventConv board commit-value/state-checksum smoke",
                str(EVENTCONV_TRACE_SPECS["burst-boundary"]["claim_boundary"]),
                "EventConv burst-boundary input AXIS32 words: `[16842752, 33685504, 0]`",
                "EventConv burst-boundary expected/board commit values: `[5, 3, 5]`",
                "EventConv burst-boundary expected/board state checksum: `2`",
                "EventConv burst-boundary counters: `pl_busy_cycles=13`",
            ]
        )
    for rel_path, phrases in required_reports.items():
        require_text(ROOT / rel_path, phrases)


def main() -> int:
    check_contracts()
    check_traces()
    check_event_budget()
    check_transport()
    check_eventconv_board_smoke()
    check_architecture_sandbox()
    check_runtime_resource()
    check_build_evidence()
    check_pynq_runtime_api()
    check_inference_only_surface()
    check_reports()
    print("PASS: verifier gate review artifacts valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
