"""SpikeMold runtime contract and resource report helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping


SPIKEMOLD_RUNTIME_CONTRACT_SCHEMA = "spikemold.runtime_contract.v1"
SPIKEMOLD_RUNTIME_RESOURCE_REPORT_SCHEMA = "spikemold.runtime_resource_report.v1"
SPIKEMOLD_RUNTIME_BACKEND_ID = "spikemold_fc_eventconv"


def sha256_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_spikemold_runtime_contract(
    *,
    event_budget: Mapping[str, object],
    transport_smoke: Mapping[str, object],
    eventconv_trace: Mapping[str, object],
    target: str = "pynq-z2",
) -> dict:
    """Build board-free contract for the SpikeMold runtime primitives."""

    budget_limits = dict(event_budget["recommended_spikemold_mini_config"])  # type: ignore[index]
    spikemold_mini = dict(transport_smoke["spikemold_mini_fc_lif"])  # type: ignore[index]
    spikemold_mini_counters = dict(spikemold_mini["counters"])  # type: ignore[index]
    eventconv_counters = dict(eventconv_trace["counters"])  # type: ignore[index]

    contract = {
        "schema": SPIKEMOLD_RUNTIME_CONTRACT_SCHEMA,
        "target": target,
        "evidence_level": "board_free_runtime_contract_no_board",
        "board_executed": False,
        "selected_backend": SPIKEMOLD_RUNTIME_BACKEND_ID,
        "contracts": {
            "integer_semantics": "INTEGER_SEMANTICS_V1",
            "event_format": "EVENT_FORMAT_V1",
            "trace_schema": "TRACE_SCHEMA_V1",
            "register_map": "REGISTER_MAP_MINIMAL_V1",
            "resource_budget": "RESOURCE_BUDGET_V1",
            "architecture_selection": "reports/architecture_selection_v1.md",
        },
        "runtime_invariants": {
            "bounded_job": True,
            "python_inner_loop_required": False,
            "random_ddr_inner_loop": False,
            "full_neuron_scan_primary": False,
            "active_set_commit_required": True,
        },
        "register_interface": {
            "control": ["CTRL", "STATUS", "INPUT_WORDS", "OUTPUT_CAP_WORDS"],
            "dma": ["INPUT_BASE_LO", "INPUT_BASE_HI", "OUTPUT_BASE_LO", "OUTPUT_BASE_HI"],
            "counters": [
                "OUTPUT_WORDS",
                "CYCLE_COUNT",
                "INPUT_EVENT_COUNT",
                "UPDATE_COUNT",
                "ACTIVE_COUNT",
                "STALL_COUNT",
                "ERROR_CODE",
            ],
        },
        "primitives": {
            "flat_fc_lif": {
                "trace_id": str(spikemold_mini["trace_id"]),
                "input_encoding": "EventWord64 input_spike",
                "output_encoding": "EventWord64 commit/readout",
                "artifact_schema": "spikemold.artifact.v1",
                "state_width_bits": int(budget_limits["state_width_bits"]),
                "weight_width_bits": int(budget_limits["weight_width_bits"]),
                "max_input_events": int(budget_limits["max_input_events"]),
                "max_generated_updates": int(budget_limits["max_generated_updates"]),
                "expected_dma_calls_per_inference": int(spikemold_mini_counters["dma_calls"]),
                "expected_axi_lite_commands_per_inference": int(spikemold_mini_counters["axi_lite_commands"]),
                "python_calls_per_inference_inner_loop": 0,
                "counters": spikemold_mini_counters,
            },
            "eventconv_agu": {
                "trace_id": str(eventconv_trace["trace_id"]),
                "input_encoding": "EventWord64 input_spike with y/x/channel fields",
                "update_encoding": "internal update packet {dst_id, weight_index}",
                "output_encoding": "EventWord64 commit/readout after active-set commit",
                "kernel_layout": "shared_kernel_cout_cin_ky_kx_int8",
                "state_width_bits": 16,
                "weight_width_bits": 8,
                "max_state_count_current_gate": 64,
                "expected_dma_calls_per_inference": 2,
                "expected_axi_lite_commands_per_inference": 8,
                "python_calls_per_inference_inner_loop": 0,
                "counters": eventconv_counters,
            },
        },
    }
    contract["hashes"] = {"runtime_contract_sha256": sha256_json(contract)}
    return contract


def build_spikemold_runtime_resource_report(
    *,
    event_budget: Mapping[str, object],
    transport_smoke: Mapping[str, object],
    eventconv_trace: Mapping[str, object],
    runtime_contract: Mapping[str, object],
    target: str = "pynq-z2",
) -> dict:
    """Build compiler-visible pre-synthesis resource report."""

    trace_results = dict(event_budget["trace_results"])  # type: ignore[index]
    fc_counters = dict(trace_results["fc_lif_tiny_v1"]["counters"])  # type: ignore[index]
    eventconv_counters = dict(eventconv_trace["counters"])  # type: ignore[index]
    spikemold_mini_counters = dict(transport_smoke["spikemold_mini_fc_lif"]["counters"])  # type: ignore[index]

    report = {
        "schema": SPIKEMOLD_RUNTIME_RESOURCE_REPORT_SCHEMA,
        "target": target,
        "evidence_level": "board_free_pre_synthesis_estimate",
        "board_executed": False,
        "runtime_contract_sha256": runtime_contract["hashes"]["runtime_contract_sha256"],  # type: ignore[index]
        "selected_backend": SPIKEMOLD_RUNTIME_BACKEND_ID,
        "all_ok": True,
        "forbidden_failure_modes": {
            "python_inner_loop_required": False,
            "random_ddr_inner_loop": False,
            "full_neuron_scan_primary": False,
            "unbounded_fanout": False,
            "silent_semantic_change": False,
        },
        "resource_reports": {
            "flat_fc_lif": {
                "trace_id": "fc_lif_tiny_v1",
                "lut_estimate_upper_bound": 1000,
                "ff_estimate_upper_bound": 1000,
                "bram_estimate_upper_bound": 2,
                "dsp_estimate": 0,
                "state_memory_bytes": 8,
                "synapse_kernel_memory_bytes": 4,
                "fifo_memory_bytes": 512,
                "expected_ddr_bytes_per_inference": 0,
                "expected_dma_calls_per_inference": int(spikemold_mini_counters["dma_calls"]),
                "expected_axi_lite_commands_per_inference": int(spikemold_mini_counters["axi_lite_commands"]),
                "event_update_histogram": fc_counters,
                "compile_time_rejection_rules": [
                    "max_input_events",
                    "max_generated_updates",
                    "max_active_neurons",
                    "max_state_reads",
                    "max_state_writes",
                    "max_ddr_bytes_inner_loop",
                    "max_python_inner_loop_steps",
                ],
            },
            "eventconv_agu": {
                "trace_id": str(eventconv_trace["trace_id"]),
                "lut_estimate_upper_bound": 1500,
                "ff_estimate_upper_bound": 1200,
                "bram_estimate_upper_bound": 2,
                "dsp_estimate": 0,
                "state_memory_bytes": 128,
                "synapse_kernel_memory_bytes": 9,
                "active_id_memory_bytes": 128,
                "fifo_memory_bytes": 512,
                "expected_ddr_bytes_per_inference": 0,
                "expected_dma_calls_per_inference": 2,
                "expected_axi_lite_commands_per_inference": 8,
                "event_update_histogram": eventconv_counters,
                "compile_time_rejection_rules": [
                    "state_count_exceeds_local_memory",
                    "kernel_weight_width_exceeds_int8_gate",
                    "destination_id_exceeds_16_bit_current_gate",
                    "python_inner_loop_required",
                    "random_ddr_inner_loop",
                    "full_neuron_scan_primary",
                ],
            },
        },
    }
    report["hashes"] = {"resource_report_sha256": sha256_json(report)}
    return report


def write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_spikemold_runtime_inputs(root: Path) -> tuple[dict, dict, dict]:
    return (
        _load_json(root / "outputs" / "event_budget" / "recommended_spikemold_mini_config.json"),
        _load_json(root / "outputs" / "transport" / "batch_1b_transport_spikemold_mini_smoke.json"),
        _load_json(root / "golden_traces" / "v1" / "eventconv_8x8_tiny_v1.json"),
    )
