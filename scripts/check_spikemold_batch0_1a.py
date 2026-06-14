#!/usr/bin/env python3
"""Check SpikeMold Batch 0 and initial Batch 1A artifacts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from spikepress.architecture_trace_generator import TRACE_SCHEMA, sha256_json  # noqa: E402
from spikepress.event_budget import evaluate_trace_budget  # noqa: E402


SPIKEPRESS_SOURCE_FILES = [
    ROOT / "software" / "python" / "spikepress" / "architecture_trace_generator.py",
    ROOT / "software" / "python" / "spikepress" / "spikemold_artifact.py",
    ROOT / "software" / "python" / "spikepress" / "event_budget.py",
    ROOT / "software" / "python" / "spikepress" / "api.py",
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

REQUIRED_TRACE_COUNTERS = [
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


def check_contracts() -> None:
    contracts = ROOT / "contracts"
    missing = [name for name in REQUIRED_CONTRACTS if not (contracts / name).exists()]
    if missing:
        fail(f"missing contracts: {missing}")

    policy = (contracts / "ARCHITECTURE_PATTERN_POLICY_V1.md").read_text(encoding="utf-8").lower()
    for pattern in ["page", "tile", "coregroup"]:
        if f"- {pattern}" not in policy:
            fail(f"policy does not allow probationary pattern: {pattern}")
    for failure_mode in [
        "python-controlled event loop",
        "random ddr synapse fetch per event",
        "unbounded fanout",
        "full-neuron scan every timestep",
        "silent semantic changes",
    ]:
        if failure_mode not in policy:
            fail(f"policy missing forbidden failure mode: {failure_mode}")


def check_trace(path: Path) -> None:
    trace = load_json(path)
    if trace.get("schema") != TRACE_SCHEMA:
        fail(f"{path} schema mismatch")
    counters = trace.get("counters", {})
    for key in REQUIRED_TRACE_COUNTERS:
        if key not in counters:
            fail(f"{path} missing counter {key}")
    if counters["ddr_bytes_inner_loop"] != 0:
        fail(f"{path} uses DDR inner-loop bytes")
    if counters["python_inner_loop_steps"] != 0:
        fail(f"{path} uses Python inner-loop steps")

    hashes = trace.get("hashes", {})
    checks = [
        ("input_sha256", trace.get("inputs")),
        ("updates_sha256", trace.get("updates")),
        ("commits_sha256", trace.get("commits")),
        ("final_state_sha256", trace.get("final_state")),
    ]
    for key, value in checks:
        if hashes.get(key) != sha256_json(value):
            fail(f"{path} hash mismatch: {key}")
    body_without_trace_hash = dict(trace)
    body_without_trace_hash["hashes"] = dict(hashes)
    expected_trace_hash = body_without_trace_hash["hashes"].pop("trace_sha256", None)
    if expected_trace_hash is None:
        fail(f"{path} missing trace_sha256")
    if expected_trace_hash != sha256_json(body_without_trace_hash):
        fail(f"{path} trace_sha256 mismatch")

    result = evaluate_trace_budget(trace)
    if not result.ok:
        fail(f"{path} budget failed: {result.failures}")


def check_batch1a() -> None:
    traces = [
        ROOT / "golden_traces" / "v1" / "fc_lif_tiny_v1.json",
        ROOT / "golden_traces" / "v1" / "eventconv_8x8_tiny_v1.json",
    ]
    for path in traces:
        if not path.exists():
            fail(f"missing trace: {path}")
        check_trace(path)

    budget = ROOT / "outputs" / "event_budget" / "recommended_spikemold_mini_config.json"
    if not budget.exists():
        fail(f"missing budget artifact: {budget}")
    budget_json = load_json(budget)
    if budget_json.get("schema") != "spikemold.event_budget.v1":
        fail("event budget schema mismatch")
    if budget_json.get("all_ok") is not True:
        fail("event budget all_ok is not true")
    if "counter_histogram" not in budget_json:
        fail("event budget missing counter_histogram")

    for report in [
        ROOT / "reports" / "batch_0_contract_freeze_report.md",
        ROOT / "reports" / "batch_1a_software_foundation_report.md",
        ROOT / "reports" / "verifier_gate_review.md",
    ]:
        if not report.exists():
            fail(f"missing report: {report}")


def check_removed_api_dependencies_excluded() -> None:
    removed_legacy_api_alias = r"[_-]".join(("snn", "fpga", "accelerator"))
    removed_api_patterns = [
        removed_legacy_api_alias,
        "Neuron" + "Group",
        "Syn" + "apses",
        "SpikePress" + "Connection",
        "compile_" + "e" + "dnp",
        "class " + "E" + "DNP" + "Artifact",
        "build_" + "e" + "dnp" + "_artifact",
        "read_" + "e" + "dnp" + "_artifact",
        "write_" + "e" + "dnp" + "_artifact",
        "SpikePress" + "Compiled" + "E" + "DNP",
        "DEFAULT_" + "M3" + "_LIMITS",
        "recommended_" + "m3" + "_config",
    ]
    for path in SPIKEPRESS_SOURCE_FILES:
        if not path.exists():
            fail(f"missing SpikePress source file: {path}")
        text = path.read_text(encoding="utf-8")
        for pattern in removed_api_patterns:
            if re.search(pattern, text):
                fail(f"removed API dependency found in {path}: {pattern}")


def main() -> int:
    check_contracts()
    check_batch1a()
    check_removed_api_dependencies_excluded()
    print("PASS: SpikeMold Batch 0 + initial Batch 1A artifacts valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
