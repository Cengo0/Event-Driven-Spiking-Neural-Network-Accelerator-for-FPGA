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
EVENT_BUDGET_PATH = ROOT / "outputs" / "event_budget" / "recommended_spikemold_mini_config.json"
TRANSPORT_PATH = ROOT / "outputs" / "transport" / "batch_1b_transport_spikemold_mini_smoke.json"
ARCH_SANDBOX_PATH = ROOT / "outputs" / "architecture_sandbox" / "batch_1x_architecture_sandbox.json"
RUNTIME_CONTRACT_PATH = ROOT / "outputs" / "runtime" / "spikemold_runtime_contract.json"
RESOURCE_REPORT_PATH = ROOT / "outputs" / "resource" / "spikemold_runtime_resource_report.json"
PYNQ_ONESHOT_SCRIPT = ROOT / "scripts" / "run_spikemold_pynq_one_shot.py"
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


def check_transport() -> None:
    transport = load_json(TRANSPORT_PATH)
    if transport.get("all_ok") is not True:
        fail("transport all_ok must be true")
    if transport.get("board_executed") is not False:
        fail("transport must not claim board execution")
    assumptions = transport.get("runtime_assumptions", {})
    if not isinstance(assumptions, Mapping):
        fail("transport missing runtime assumptions")
    for key in ["python_inner_loop_required", "random_ddr_inner_loop", "full_neuron_scan_primary"]:
        if assumptions.get(key) is not False:
            fail(f"transport forbidden assumption must be false: {key}")
    spikemold_mini = transport.get("spikemold_mini_fc_lif", {})
    if not isinstance(spikemold_mini, Mapping):
        fail("transport missing SpikeMold-mini section")
    for key, value in [
        ("trace_match_rate", 1.0),
        ("readout_match", True),
        ("state_checksum_match", True),
    ]:
        if spikemold_mini.get(key) != value:
            fail(f"SpikeMold-mini {key} mismatch")


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
        "reports/batch_1b_transport_spikemold_mini_report.md": [
            "Board execution was not run",
            "software_transport_smoke_no_board",
        ],
        "reports/batch_1c_eventconv_primitive_report.md": [
            "C0 trace-locked tiny case",
            "C3 AGU + active-set commit",
            "No board execution was run",
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
            "Vivado synthesis must replace LUT/FF/BRAM/timing estimates",
        ],
        "reports/verifier_gate_review.md": [
            "Status: board-free verifier gate passed",
            "Inference-Only Scope",
            "PYNQ one-shot runtime API",
            "No board execution was run",
        ],
    }
    for rel_path, phrases in required_reports.items():
        require_text(ROOT / rel_path, phrases)


def main() -> int:
    check_contracts()
    check_traces()
    check_event_budget()
    check_transport()
    check_architecture_sandbox()
    check_runtime_resource()
    check_pynq_runtime_api()
    check_inference_only_surface()
    check_reports()
    print("PASS: verifier gate review artifacts valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
