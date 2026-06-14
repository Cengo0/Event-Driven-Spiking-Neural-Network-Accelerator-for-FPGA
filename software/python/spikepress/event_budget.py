"""Event/update budget checks for SpikeMold-EDNP traces."""

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


DEFAULT_EDNP_MINI_LIMITS = EventBudgetLimits(
    max_input_events=1024,
    max_generated_updates=8192,
    max_active_neurons=512,
    max_state_reads=8192,
    max_state_writes=9216,
    max_ddr_bytes_inner_loop=0,
    max_python_inner_loop_steps=0,
)


def recommended_ednp_mini_config() -> Dict[str, object]:
    return {
        "target": "pynq-z2",
        "primitive": "ednp-mini-fc-lif",
        "state_width_bits": 32,
        "weight_width_bits": 16,
        "ddr_bytes_inner_loop": DEFAULT_EDNP_MINI_LIMITS.max_ddr_bytes_inner_loop,
        "python_inner_loop_steps": DEFAULT_EDNP_MINI_LIMITS.max_python_inner_loop_steps,
        **asdict(DEFAULT_EDNP_MINI_LIMITS),
    }


def evaluate_trace_budget(
    trace: Mapping[str, object],
    limits: EventBudgetLimits = DEFAULT_EDNP_MINI_LIMITS,
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
    limits: EventBudgetLimits = DEFAULT_EDNP_MINI_LIMITS,
) -> Dict[str, object]:
    results = {name: evaluate_trace_budget(trace, limits).to_dict() for name, trace in traces.items()}
    return {
        "schema": "spikemold.ednp_event_budget.v1",
        "recommended_ednp_mini_config": recommended_ednp_mini_config(),
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
