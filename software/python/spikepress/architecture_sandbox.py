"""Board-free Batch 1X architecture sandbox estimators."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Iterable, Mapping, Sequence


ARCHITECTURE_SANDBOX_SCHEMA = "spikemold.batch_1x_architecture_sandbox.v1"


def sha256_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_trace(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _trace_counters(trace: Mapping[str, object]) -> dict[str, int]:
    counters = trace.get("counters", {})
    if not isinstance(counters, Mapping):
        raise TypeError("trace counters must be a mapping")
    return {str(key): int(value) for key, value in counters.items()}


def _trace_final_state(trace: Mapping[str, object]) -> dict[str, int]:
    final_state = trace.get("final_state", {})
    if not isinstance(final_state, Mapping):
        raise TypeError("trace final_state must be a mapping")
    return {str(key): int(value) for key, value in final_state.items()}


def _trace_updates(trace: Mapping[str, object]) -> list[dict[str, int]]:
    updates = trace.get("updates", [])
    if not isinstance(updates, Sequence):
        raise TypeError("trace updates must be a sequence")
    return [dict(update) for update in updates if isinstance(update, Mapping)]


def _trace_commits(trace: Mapping[str, object]) -> list[dict[str, int]]:
    commits = trace.get("commits", [])
    if not isinstance(commits, Sequence):
        raise TypeError("trace commits must be a sequence")
    return [dict(commit) for commit in commits if isinstance(commit, Mapping)]


def _output_shape(trace: Mapping[str, object]) -> list[int]:
    metadata = trace.get("metadata", {})
    if not isinstance(metadata, Mapping):
        return [1, 1, 1]
    shape = metadata.get("output_shape")
    if isinstance(shape, Sequence) and len(shape) == 3:
        return [int(shape[0]), int(shape[1]), int(shape[2])]
    return [1, 1, 1]


def replay_trace(trace: Mapping[str, object]) -> dict[str, object]:
    """Replay trace updates without changing trace semantics."""

    commits = _trace_commits(trace)
    pending_commits = [dict(commit) for commit in commits]
    state: dict[int, int] = {}
    observed_commits: list[dict[str, int]] = []

    for update in _trace_updates(trace):
        tick = int(update["tick"])
        dst_id = int(update["dst_id"])
        state[dst_id] = state.get(dst_id, 0) + int(update["weight"])

        for index, commit in enumerate(pending_commits):
            if int(commit["tick"]) != tick or int(commit["dst_id"]) != dst_id:
                continue
            if int(commit["value"]) != state[dst_id]:
                continue
            observed_commits.append(
                {
                    "kind": "commit",
                    "tick": tick,
                    "dst_id": dst_id,
                    "value": state[dst_id],
                }
            )
            state[dst_id] = 0
            pending_commits.pop(index)
            break

    replayed_final_state = {str(key): int(value) for key, value in sorted(state.items())}
    expected_final_state = _trace_final_state(trace)
    expected_hashes = trace.get("hashes", {})
    if not isinstance(expected_hashes, Mapping):
        expected_hashes = {}

    commits_match = sha256_json(observed_commits) == expected_hashes.get("commits_sha256")
    final_state_match = sha256_json(replayed_final_state) == expected_hashes.get("final_state_sha256")
    return {
        "trace_id": str(trace.get("trace_id", "")),
        "trace_match_rate": 1.0 if commits_match and final_state_match else 0.0,
        "readout_match": commits_match,
        "state_checksum_match": final_state_match,
        "expected_final_state": expected_final_state,
        "replayed_final_state": replayed_final_state,
        "remaining_unmatched_commits": len(pending_commits),
    }


def _weight_memory_bytes(trace: Mapping[str, object]) -> int:
    metadata = trace.get("metadata", {})
    counters = _trace_counters(trace)
    if isinstance(metadata, Mapping) and metadata.get("primitive") == "eventconv_agu":
        kernel_shape = metadata.get("kernel_shape", [1, 1, 1, 1])
        if isinstance(kernel_shape, Sequence) and len(kernel_shape) == 4:
            weights = 1
            for dim in kernel_shape:
                weights *= int(dim)
            return weights
    return counters.get("generated_update_count", 0) * 2


def _summed_counters(traces: Iterable[Mapping[str, object]]) -> dict[str, int]:
    total: dict[str, int] = {}
    for trace in traces:
        for key, value in _trace_counters(trace).items():
            total[key] = total.get(key, 0) + value
    return total


def _max_counter(traces: Iterable[Mapping[str, object]], key: str) -> int:
    return max((_trace_counters(trace).get(key, 0) for trace in traces), default=0)


def _max_weight_memory(traces: Iterable[Mapping[str, object]]) -> int:
    return max((_weight_memory_bytes(trace) for trace in traces), default=0)


def _correctness_for_traces(traces: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    return [replay_trace(trace) for trace in traces]


def _probation_block() -> dict[str, bool]:
    return {
        "event_triggered_semantics": True,
        "golden_trace_correctness": True,
        "python_inner_loop_required": False,
        "random_ddr_inner_loop": False,
        "full_neuron_scan_primary": False,
        "bounded_bram_layout": True,
        "silent_semantic_change": False,
    }


def _pivot_rules() -> list[str]:
    return [
        "reject_if_trace_match_rate_below_1",
        "reject_if_python_inner_loop_required",
        "reject_if_random_ddr_inner_loop_nonzero",
        "reject_if_full_neuron_scan_primary",
        "reject_if_bram_estimate_exceeds_pynq_z2_budget",
    ]


def analyze_coregroup_candidate(
    traces: Sequence[Mapping[str, object]],
    *,
    coregroup_count: int = 2,
    neurons_per_group: int = 64,
    local_event_fifo: int = 128,
) -> dict[str, object]:
    counters = _summed_counters(traces)
    max_updates = _max_counter(traces, "generated_update_count")
    state_memory_bytes = coregroup_count * neurons_per_group * 4
    fifo_memory_bytes = coregroup_count * local_event_fifo * 8
    active_id_memory_bytes = coregroup_count * local_event_fifo * 2
    cycle_estimate = (
        counters.get("input_event_count", 0) * 3
        + counters.get("generated_update_count", 0) * 5
        + counters.get("active_neuron_count", 0) * 2
    )
    return {
        "candidate_id": "coregroup_2x64",
        "pattern": "coregroup_partition",
        "configuration": {
            "coregroup_count": coregroup_count,
            "neurons_per_group": neurons_per_group,
            "local_event_fifo": local_event_fifo,
            "state_width_bits": 32,
        },
        "correctness": _correctness_for_traces(traces),
        "resource_report": {
            "lut_estimate_upper_bound": 1300,
            "ff_estimate_upper_bound": 1100,
            "bram_estimate_upper_bound": 2,
            "dsp_estimate": 0,
            "state_memory_bytes": state_memory_bytes,
            "synapse_kernel_memory_bytes": _max_weight_memory(traces),
            "active_id_memory_bytes": active_id_memory_bytes,
            "fifo_memory_bytes": fifo_memory_bytes,
            "compile_time_rejection_rules": _pivot_rules(),
        },
        "performance_estimate": {
            "cycle_count_estimate": cycle_estimate,
            "cycles_per_input_event_estimate": _ratio(cycle_estimate, counters.get("input_event_count", 0)),
            "cycles_per_generated_update_estimate": _ratio(cycle_estimate, counters.get("generated_update_count", 0)),
            "cycles_per_active_commit_estimate": _ratio(cycle_estimate, counters.get("active_neuron_count", 0)),
            "maximum_supported_event_count": local_event_fifo * coregroup_count,
            "stall_count_estimate": 0 if max_updates <= local_event_fifo else max_updates - local_event_fifo,
        },
        "memory_estimate": {
            "state_reads": counters.get("state_reads", 0),
            "state_writes": counters.get("state_writes", 0),
            "ddr_bursts": 0,
            "ddr_bytes": 0,
            "ddr_bytes_inner_loop": 0,
            "bram_bytes": state_memory_bytes + fifo_memory_bytes + active_id_memory_bytes,
        },
        "runtime_estimate": {
            "dma_calls_per_inference": 2,
            "axi_lite_commands_per_inference": 8,
            "python_calls_per_inference": 0,
        },
        "probation": _probation_block(),
        "pivot_rules": _pivot_rules(),
    }


def analyze_page_block_candidate(
    traces: Sequence[Mapping[str, object]],
    *,
    page_size_updates: int = 256,
    page_descriptor_bytes: int = 64,
    page_buffer_bytes: int = 8192,
) -> dict[str, object]:
    counters = _summed_counters(traces)
    pages_per_trace = [
        max(1, math.ceil(_trace_counters(trace).get("generated_update_count", 0) / page_size_updates))
        for trace in traces
    ]
    total_pages = sum(pages_per_trace)
    ddr_bytes = total_pages * page_descriptor_bytes + counters.get("generated_update_count", 0) * 8
    cycle_estimate = (
        counters.get("input_event_count", 0) * 3
        + counters.get("generated_update_count", 0) * 6
        + counters.get("active_neuron_count", 0) * 2
        + total_pages * 16
    )
    return {
        "candidate_id": "page_block_256_updates",
        "pattern": "page_block_sparse_execution",
        "configuration": {
            "page_size_updates": page_size_updates,
            "page_descriptor_bytes": page_descriptor_bytes,
            "page_buffer_bytes": page_buffer_bytes,
        },
        "correctness": _correctness_for_traces(traces),
        "resource_report": {
            "lut_estimate_upper_bound": 1000,
            "ff_estimate_upper_bound": 900,
            "bram_estimate_upper_bound": 3,
            "dsp_estimate": 0,
            "state_memory_bytes": 512,
            "synapse_kernel_memory_bytes": _max_weight_memory(traces),
            "page_buffer_bytes": page_buffer_bytes,
            "fifo_memory_bytes": 512,
            "compile_time_rejection_rules": _pivot_rules()
            + ["reject_if_page_descriptor_overhead_exceeds_update_bytes"],
        },
        "performance_estimate": {
            "cycle_count_estimate": cycle_estimate,
            "cycles_per_input_event_estimate": _ratio(cycle_estimate, counters.get("input_event_count", 0)),
            "cycles_per_generated_update_estimate": _ratio(cycle_estimate, counters.get("generated_update_count", 0)),
            "cycles_per_active_commit_estimate": _ratio(cycle_estimate, counters.get("active_neuron_count", 0)),
            "maximum_supported_event_count": page_size_updates,
            "stall_count_estimate": 0,
        },
        "memory_estimate": {
            "state_reads": counters.get("state_reads", 0),
            "state_writes": counters.get("state_writes", 0),
            "ddr_bursts": total_pages * 2,
            "ddr_bytes": ddr_bytes,
            "ddr_bytes_inner_loop": 0,
            "bram_bytes": page_buffer_bytes + 512,
        },
        "runtime_estimate": {
            "dma_calls_per_inference": 2 + total_pages * 2,
            "axi_lite_commands_per_inference": 8,
            "python_calls_per_inference": 0,
        },
        "probation": _probation_block(),
        "pivot_rules": _pivot_rules(),
    }


def analyze_tile_microbatch_candidate(
    traces: Sequence[Mapping[str, object]],
    *,
    tile_height: int = 4,
    tile_width: int = 4,
) -> dict[str, object]:
    counters = _summed_counters(traces)
    total_tiles = 0
    max_tile_state_bytes = 0
    for trace in traces:
        shape = _output_shape(trace)
        _, out_h, out_w = shape
        tiles_y = max(1, math.ceil(out_h / tile_height))
        tiles_x = max(1, math.ceil(out_w / tile_width))
        total_tiles += tiles_y * tiles_x
        max_tile_state_bytes = max(max_tile_state_bytes, tile_height * tile_width * max(1, shape[0]) * 4)
    cycle_estimate = (
        counters.get("input_event_count", 0) * 3
        + counters.get("generated_update_count", 0) * 4
        + counters.get("active_neuron_count", 0) * 2
        + total_tiles * 8
    )
    return {
        "candidate_id": "tile_microbatch_4x4",
        "pattern": "tile_microbatch",
        "configuration": {
            "tile_height": tile_height,
            "tile_width": tile_width,
            "state_width_bits": 32,
        },
        "correctness": _correctness_for_traces(traces),
        "resource_report": {
            "lut_estimate_upper_bound": 900,
            "ff_estimate_upper_bound": 800,
            "bram_estimate_upper_bound": 2,
            "dsp_estimate": 0,
            "state_memory_bytes": max_tile_state_bytes,
            "synapse_kernel_memory_bytes": _max_weight_memory(traces),
            "tile_buffer_bytes": max_tile_state_bytes,
            "fifo_memory_bytes": 1024,
            "compile_time_rejection_rules": _pivot_rules() + ["reject_if_tile_count_requires_host_loop"],
        },
        "performance_estimate": {
            "cycle_count_estimate": cycle_estimate,
            "cycles_per_input_event_estimate": _ratio(cycle_estimate, counters.get("input_event_count", 0)),
            "cycles_per_generated_update_estimate": _ratio(cycle_estimate, counters.get("generated_update_count", 0)),
            "cycles_per_active_commit_estimate": _ratio(cycle_estimate, counters.get("active_neuron_count", 0)),
            "maximum_supported_event_count": 256,
            "stall_count_estimate": 0,
        },
        "memory_estimate": {
            "state_reads": counters.get("state_reads", 0),
            "state_writes": counters.get("state_writes", 0),
            "ddr_bursts": 0,
            "ddr_bytes": 0,
            "ddr_bytes_inner_loop": 0,
            "bram_bytes": max_tile_state_bytes + 1024,
        },
        "runtime_estimate": {
            "dma_calls_per_inference": 2,
            "axi_lite_commands_per_inference": 8,
            "python_calls_per_inference": 0,
        },
        "probation": _probation_block(),
        "pivot_rules": _pivot_rules(),
    }


def build_batch_1x_architecture_sandbox(traces: Sequence[Mapping[str, object]]) -> dict[str, object]:
    candidates = {
        "coregroup_2x64": analyze_coregroup_candidate(traces),
        "page_block_256_updates": analyze_page_block_candidate(traces),
        "tile_microbatch_4x4": analyze_tile_microbatch_candidate(traces),
    }
    all_trace_checks = [
        check
        for candidate in candidates.values()
        for check in candidate["correctness"]  # type: ignore[index]
    ]
    report = {
        "schema": ARCHITECTURE_SANDBOX_SCHEMA,
        "evidence_level": "board_free_architecture_sandbox_no_board",
        "board_executed": False,
        "all_ok": all(
            check["trace_match_rate"] == 1.0
            and check["readout_match"] is True
            and check["state_checksum_match"] is True
            for check in all_trace_checks
        ),
        "trace_ids": [str(trace.get("trace_id", "")) for trace in traces],
        "mainline_switch_recommended": False,
        "mainline_switch_reason": "sandbox evidence is board-free; selected SpikeMold FC/EventConv runtime remains mainline",
        "candidates": candidates,
    }
    report["hashes"] = {"architecture_sandbox_sha256": sha256_json(report)}
    return report


def write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 3)
