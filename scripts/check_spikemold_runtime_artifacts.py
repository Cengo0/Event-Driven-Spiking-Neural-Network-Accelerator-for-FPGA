#!/usr/bin/env python3
"""Check SpikeMold runtime contract and resource artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from spikepress.spikemold_runtime_contract import (  # noqa: E402
    SPIKEMOLD_RUNTIME_BACKEND_ID,
    SPIKEMOLD_RUNTIME_CONTRACT_SCHEMA,
    SPIKEMOLD_RUNTIME_RESOURCE_REPORT_SCHEMA,
    sha256_json,
)


ABI_PATH = ROOT / "outputs" / "runtime" / "spikemold_runtime_contract.json"
RESOURCE_PATH = ROOT / "outputs" / "resource" / "spikemold_runtime_resource_report.json"
REPORT_PATH = ROOT / "reports" / "spikemold_runtime_resource_report.md"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - diagnostic path
        fail(f"cannot load JSON {path}: {exc}")


def check_hash(payload: dict, hash_key: str) -> None:
    hashes = dict(payload.get("hashes", {}))
    expected = hashes.pop(hash_key, None)
    body = dict(payload)
    if hashes:
        body["hashes"] = hashes
    else:
        body.pop("hashes", None)
    if expected != sha256_json(body):
        fail(f"hash mismatch: {hash_key}")


def main() -> int:
    for path in [ABI_PATH, RESOURCE_PATH, REPORT_PATH]:
        if not path.exists():
            fail(f"missing artifact: {path}")

    abi = load_json(ABI_PATH)
    if abi.get("schema") != SPIKEMOLD_RUNTIME_CONTRACT_SCHEMA:
        fail("runtime contract schema mismatch")
    if abi.get("evidence_level") != "board_free_runtime_contract_no_board":
        fail("runtime contract evidence level mismatch")
    if abi.get("selected_backend") != SPIKEMOLD_RUNTIME_BACKEND_ID:
        fail("runtime contract backend mismatch")
    if abi.get("board_executed") is not False:
        fail("runtime contract must not claim board execution")
    invariants = abi.get("runtime_invariants", {})
    expected_invariants = {
        "bounded_job": True,
        "python_inner_loop_required": False,
        "random_ddr_inner_loop": False,
        "full_neuron_scan_primary": False,
        "active_set_commit_required": True,
    }
    for key, value in expected_invariants.items():
        if invariants.get(key) != value:
            fail(f"runtime invariant mismatch for {key}: {invariants.get(key)}")

    primitives = abi.get("primitives", {})
    flat = primitives.get("flat_fc_lif", {})
    eventconv = primitives.get("eventconv_agu", {})
    if flat.get("expected_dma_calls_per_inference") != 2:
        fail("flat_fc_lif expected DMA calls mismatch")
    if flat.get("expected_axi_lite_commands_per_inference") != 8:
        fail("flat_fc_lif expected AXI-Lite commands mismatch")
    if flat.get("python_calls_per_inference_inner_loop") != 0:
        fail("flat_fc_lif Python inner-loop calls must be zero")
    if eventconv.get("trace_id") != "eventconv_8x8_tiny_v1":
        fail("eventconv trace_id mismatch")
    if eventconv.get("max_state_count_current_gate") != 64:
        fail("eventconv state count gate mismatch")
    if eventconv.get("expected_dma_calls_per_inference") != 2:
        fail("eventconv expected DMA calls mismatch")
    if eventconv.get("expected_axi_lite_commands_per_inference") != 8:
        fail("eventconv expected AXI-Lite commands mismatch")
    if eventconv.get("python_calls_per_inference_inner_loop") != 0:
        fail("eventconv Python inner-loop calls must be zero")
    check_hash(abi, "runtime_contract_sha256")

    resource = load_json(RESOURCE_PATH)
    if resource.get("schema") != SPIKEMOLD_RUNTIME_RESOURCE_REPORT_SCHEMA:
        fail("resource report schema mismatch")
    if resource.get("selected_backend") != SPIKEMOLD_RUNTIME_BACKEND_ID:
        fail("resource report backend mismatch")
    if resource.get("board_executed") is not False:
        fail("resource report must not claim board execution")
    if resource.get("runtime_contract_sha256") != abi["hashes"]["runtime_contract_sha256"]:
        fail("runtime contract hash link mismatch")
    failures = resource.get("forbidden_failure_modes", {})
    for key in [
        "python_inner_loop_required",
        "random_ddr_inner_loop",
        "full_neuron_scan_primary",
        "unbounded_fanout",
        "silent_semantic_change",
    ]:
        if failures.get(key) is not False:
            fail(f"forbidden failure mode not false: {key}")

    reports = resource.get("resource_reports", {})
    flat_report = reports.get("flat_fc_lif", {})
    eventconv_report = reports.get("eventconv_agu", {})
    required_fields = [
        "lut_estimate_upper_bound",
        "ff_estimate_upper_bound",
        "bram_estimate_upper_bound",
        "dsp_estimate",
        "state_memory_bytes",
        "synapse_kernel_memory_bytes",
        "fifo_memory_bytes",
        "expected_ddr_bytes_per_inference",
        "expected_dma_calls_per_inference",
        "expected_axi_lite_commands_per_inference",
        "event_update_histogram",
        "compile_time_rejection_rules",
    ]
    for primitive_name, primitive_report in [
        ("flat_fc_lif", flat_report),
        ("eventconv_agu", eventconv_report),
    ]:
        for field in required_fields:
            if field not in primitive_report:
                fail(f"{primitive_name} missing resource field: {field}")
        if primitive_report.get("dsp_estimate") != 0:
            fail(f"{primitive_name} must remain add-only/DSP-free")
        if primitive_report.get("expected_ddr_bytes_per_inference") != 0:
            fail(f"{primitive_name} must keep inner-loop DDR bytes at zero")

    if eventconv_report.get("state_memory_bytes") != 128:
        fail("eventconv state memory estimate mismatch")
    if eventconv_report.get("synapse_kernel_memory_bytes") != 9:
        fail("eventconv kernel memory estimate mismatch")
    if eventconv_report.get("active_id_memory_bytes") != 128:
        fail("eventconv active-id memory estimate mismatch")
    if eventconv_report.get("expected_dma_calls_per_inference") != 2:
        fail("eventconv resource DMA call estimate mismatch")
    if eventconv_report.get("expected_axi_lite_commands_per_inference") != 8:
        fail("eventconv resource AXI-Lite command estimate mismatch")
    eventconv_hist = eventconv_report.get("event_update_histogram", {})
    if eventconv_hist.get("generated_update_count") != 12:
        fail("eventconv generated update histogram mismatch")
    if eventconv_hist.get("python_inner_loop_steps") != 0:
        fail("eventconv Python inner-loop histogram must be zero")
    check_hash(resource, "resource_report_sha256")

    report_text = REPORT_PATH.read_text(encoding="utf-8")
    for phrase in [
        "board_free_runtime_contract_no_board",
        "spikemold_fc_eventconv",
        "Python inner loop required: `False`",
        "random DDR inner loop: `False`",
        "full-neuron scan primary: `False`",
        "Vivado synthesis must replace LUT/FF/BRAM/timing estimates",
    ]:
        if phrase not in report_text:
            fail(f"report missing phrase: {phrase}")

    print("PASS: SpikeMold runtime/resource artifacts valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
