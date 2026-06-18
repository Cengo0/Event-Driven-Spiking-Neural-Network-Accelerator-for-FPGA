"""Event/update budget checks for SpikeMold traces."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Iterable, Mapping, Tuple


@dataclass(frozen=True)
class EventBudgetLimits:
    max_input_events: int
    max_generated_updates: int
    max_active_neurons: int
    max_state_reads: int
    max_state_writes: int
    max_ddr_bytes_inner_loop: int = 0
    max_python_inner_loop_steps: int = 0


@dataclass(frozen=True)
class EventBudgetResult:
    ok: bool
    failures: Tuple[str, ...]
    counters: Mapping[str, int]
    limits: EventBudgetLimits

    def to_dict(self) -> Dict[str, object]:
        return {
            "ok": self.ok,
            "failures": list(self.failures),
            "counters": dict(self.counters),
            "limits": asdict(self.limits),
        }


# Conservative limits from the very first tiny flat-FC-LIF primitive experiments.
# These are intentionally tight for "no tiling / no block-sparse / no heavy mux" cases.
# For the current hybrid + 16-block reduced design (logical 16k hidden on 2k physical fabric)
# the real constraints are weight_tiling chunks, per-block commit, and measured activity
# (see train script hybrid-reduced annotations and post-training integer trace validation).
# We keep the old numbers for backward compat on flat checks but also provide a relaxed
# hybrid-aware set that the training deploy checker can prefer.
DEFAULT_FLAT_FC_LIF_LIMITS = EventBudgetLimits(
    max_input_events=1024,
    max_generated_updates=8192,
    max_active_neurons=512,
    max_state_reads=8192,
    max_state_writes=9216,
    max_ddr_bytes_inner_loop=0,
    max_python_inner_loop_steps=0,
)

# More realistic limits for block-sparse hybrid designs on PYNQ-Z2.
# These reflect the architecture's use of weight tiling + active-set commit + 16-block
# multiplexing over the 16×128 physical fabric. Still conservative; final truth is always
# the integer golden trace + board execution with the actual tiled weights.
DEFAULT_HYBRID_BLOCK_LIMITS = EventBudgetLimits(
    max_input_events=8192,        # rate-encoded images + conv output events into FC
    max_generated_updates=65536,
    max_active_neurons=8192,      # logical active across all blocks (physical fabric 2048; block-sparse + tiling + active commit is how we exceed it)
    max_state_reads=32768,
    max_state_writes=32768,
    max_ddr_bytes_inner_loop=0,
    max_python_inner_loop_steps=0,
)


def recommended_flat_fc_lif_config() -> Dict[str, object]:
    return {
        "target": "pynq-z2",
        "primitive": "spikemold-flat-fc-lif",
        "state_width_bits": 32,
        "weight_width_bits": 16,
        "ddr_bytes_inner_loop": DEFAULT_FLAT_FC_LIF_LIMITS.max_ddr_bytes_inner_loop,
        "python_inner_loop_steps": DEFAULT_FLAT_FC_LIF_LIMITS.max_python_inner_loop_steps,
        **asdict(DEFAULT_FLAT_FC_LIF_LIMITS),
    }


def evaluate_trace_budget(
    trace: Mapping[str, object],
    limits: EventBudgetLimits = DEFAULT_FLAT_FC_LIF_LIMITS,
) -> EventBudgetResult:
    counters_obj = trace.get("counters", {})
    if not isinstance(counters_obj, Mapping):
        raise TypeError("trace counters must be a mapping")
    counters = {str(k): int(v) for k, v in counters_obj.items()}
    failures = []

    checks = [
        ("input_event_count", limits.max_input_events),
        ("generated_update_count", limits.max_generated_updates),
        ("active_neuron_count", limits.max_active_neurons),
        ("state_reads", limits.max_state_reads),
        ("state_writes", limits.max_state_writes),
        ("ddr_bytes_inner_loop", limits.max_ddr_bytes_inner_loop),
        ("python_inner_loop_steps", limits.max_python_inner_loop_steps),
    ]
    for key, limit in checks:
        value = counters.get(key)
        if value is None:
            failures.append(f"missing_counter:{key}")
        elif value > limit:
            failures.append(f"limit_exceeded:{key}:{value}>{limit}")

    return EventBudgetResult(
        ok=not failures,
        failures=tuple(failures),
        counters=counters,
        limits=limits,
    )


def summarize_trace_budgets(
    traces: Mapping[str, Mapping[str, object]],
    limits: EventBudgetLimits = DEFAULT_FLAT_FC_LIF_LIMITS,
) -> Dict[str, object]:
    results = {name: evaluate_trace_budget(trace, limits).to_dict() for name, trace in traces.items()}
    return {
        "schema": "spikemold.event_budget.v1",
        "recommended_flat_fc_lif_config": recommended_flat_fc_lif_config(),
        "all_ok": all(result["ok"] for result in results.values()),
        "counter_histogram": build_counter_histogram(trace.get("counters", {}) for trace in traces.values()),
        "trace_results": results,
    }


def build_counter_histogram(counter_sets: Iterable[Mapping[str, object]]) -> Dict[str, Dict[str, int]]:
    histogram: Dict[str, Dict[str, int]] = {}
    for counters_obj in counter_sets:
        counters = {str(k): int(v) for k, v in counters_obj.items()}
        for key, value in counters.items():
            if key not in histogram:
                histogram[key] = {"min": value, "max": value, "total": 0}
            histogram[key]["min"] = min(histogram[key]["min"], value)
            histogram[key]["max"] = max(histogram[key]["max"], value)
            histogram[key]["total"] += value
    return histogram
