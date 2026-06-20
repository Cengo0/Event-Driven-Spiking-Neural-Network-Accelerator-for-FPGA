#!/usr/bin/env python3
"""Check frozen SpikePress -> SpikeMold final-goal artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from spikepress.architecture_trace_generator import InputSpike, TRACE_SCHEMA, generate_eventconv_fclif_trace, sha256_json  # noqa: E402
from spikepress.spikemold_artifact import EVENTCONV_FCLIF_KIND, read_spikemold_artifact, validate_eventconv_fclif_manifest  # noqa: E402
from spikepress.transport import build_eventconv_fclif_config_plan  # noqa: E402


ARTIFACT_PATH = ROOT / "outputs" / "artifacts" / "mnist_eventconv_fclif_frozen.json"
TRACE_PATH = ROOT / "golden_traces" / "v1" / "mnist_eventconv_fclif_frozen_v1.json"
CONFIG_PLAN_PATH = ROOT / "outputs" / "runtime" / "mnist_eventconv_fclif_config_plan.json"
REPORT_PATH = ROOT / "reports" / "spikemold_final_goal_report.md"
RTL_TOP_PATH = ROOT / "hardware" / "hdl" / "rtl" / "top" / "spikemold_integrated_top.v"
MIN_TRAINED_ACCURACY = 0.90


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        fail(f"missing artifact: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def sample_input() -> list[InputSpike]:
    return [
        InputSpike(tick=0, src_id=0, y=14, x=14, channel=0, payload=1),
        InputSpike(tick=1, src_id=1, y=7, x=7, channel=0, payload=1),
        InputSpike(tick=2, src_id=2, y=21, x=21, channel=0, payload=1),
    ]


def split_artifact_weights(manifest: dict[str, object]) -> tuple[np.ndarray, np.ndarray]:
    network = manifest["network"]  # type: ignore[index]
    weights = manifest["weights"]  # type: ignore[index]
    if not isinstance(network, dict) or not isinstance(weights, dict):
        fail("artifact network/weights must be mappings")
    eventconv = network["eventconv"]  # type: ignore[index]
    readout = network["readout"]  # type: ignore[index]
    if not isinstance(eventconv, dict) or not isinstance(readout, dict):
        fail("artifact eventconv/readout must be mappings")
    values = np.asarray(weights["values"], dtype=np.int8)  # type: ignore[index]
    kernel_count = int(weights["kernel_count"])  # type: ignore[index]
    kernel_shape = tuple(int(v) for v in eventconv["kernel_shape"])  # type: ignore[index]
    readout_shape = (int(readout["source_size"]), int(readout["target_size"]))  # type: ignore[index]
    return (
        values[:kernel_count].reshape(kernel_shape).astype(np.int16),
        values[kernel_count:].reshape(readout_shape).astype(np.int16),
    )


def check_training_gate(manifest: dict[str, object]) -> None:
    training = manifest.get("training", {})
    if not isinstance(training, dict):
        fail("artifact missing training metadata")
    accuracy = float(training.get("final_validation_accuracy", -1.0))
    if accuracy < MIN_TRAINED_ACCURACY:
        fail(f"trained MNIST accuracy below gate: {accuracy:.4f}")


def expected_trace_from_artifact(manifest: dict[str, object]) -> dict[str, object]:
    kernel, readout = split_artifact_weights(manifest)
    trace = generate_eventconv_fclif_trace(
        input_spikes=sample_input(),
        kernel=kernel.tolist(),
        input_shape=(1, 28, 28),
        readout_weights=readout.tolist(),
        stride=2,
        padding=1,
        conv_thresholds={idx: 1 for idx in range(4 * 14 * 14)},
        readout_thresholds={784 + idx: 1 for idx in range(10)},
        trace_id="mnist_eventconv_fclif_frozen_v1",
        target="pynq-z2",
    )
    return trace.to_dict()


def check_trace(manifest: dict[str, object]) -> dict[str, object]:
    trace = load_json(TRACE_PATH)
    if trace.get("schema") != TRACE_SCHEMA:
        fail("trace schema mismatch")
    metadata = trace.get("metadata", {})
    if not isinstance(metadata, dict):
        fail("trace metadata must be mapping")
    if metadata.get("primitive") != "eventconv_fclif":
        fail("trace primitive mismatch")
    if metadata.get("eventconv_output_shape") != [4, 14, 14]:
        fail("trace EventConv output shape mismatch")
    if metadata.get("readout_id_start") != 784:
        fail("trace readout id start mismatch")
    counters = trace.get("counters", {})
    if not isinstance(counters, dict):
        fail("trace counters must be mapping")
    if counters.get("python_inner_loop_steps") != 0:
        fail("trace uses Python inner loop")
    if counters.get("ddr_bytes_inner_loop") != 0:
        fail("trace uses DDR inner-loop bytes")
    if int(counters.get("input_event_count", 0)) <= 0:
        fail("trace missing input events")
    if int(counters.get("generated_update_count", 0)) <= 0:
        fail("trace missing generated updates")
    if int(counters.get("commit_count", 0)) <= 0:
        fail("trace missing readout commits")

    hashes = trace.get("hashes", {})
    if not isinstance(hashes, dict):
        fail("trace hashes must be mapping")
    checks = [
        ("input_sha256", trace.get("inputs")),
        ("updates_sha256", trace.get("updates")),
        ("commits_sha256", trace.get("commits")),
        ("final_state_sha256", trace.get("final_state")),
    ]
    for key, value in checks:
        if hashes.get(key) != sha256_json(value):
            fail(f"trace hash mismatch: {key}")
    body_without_trace_hash = dict(trace)
    body_without_trace_hash["hashes"] = dict(hashes)
    expected = body_without_trace_hash["hashes"].pop("trace_sha256", None)  # type: ignore[index]
    if expected != sha256_json(body_without_trace_hash):
        fail("trace_sha256 mismatch")
    expected_trace = expected_trace_from_artifact(manifest)
    for key in ["inputs", "updates", "commits", "final_state", "hashes"]:
        if trace.get(key) != expected_trace.get(key):
            fail(f"trace does not match artifact-derived golden: {key}")
    return trace


def check_config_plan(manifest: dict[str, object], trace: dict[str, object]) -> dict[str, object]:
    plan = load_json(CONFIG_PLAN_PATH)
    if plan.get("schema") != "spikemold.eventconv_fclif_config_plan.v1":
        fail("config plan schema mismatch")
    if plan.get("artifact_kind") != EVENTCONV_FCLIF_KIND:
        fail("config plan artifact kind mismatch")
    if plan.get("backend_mode") != 2:
        fail("config plan backend mode mismatch")
    if plan.get("eventconv_shape0") != 0x04031C1C:
        fail("config plan EventConv shape descriptor mismatch")
    if plan.get("eventconv_output_count0") != len(trace.get("commits", [])):
        fail("config plan expected output count mismatch")
    if len(plan.get("kernel_config_writes", [])) != 9:
        fail("config plan kernel writes mismatch")
    kernel_addresses = [int(write.get("address", 0)) for write in plan.get("kernel_config_writes", [])]
    if not kernel_addresses or kernel_addresses[0] != 0x03000000:
        fail("config plan EventConv-FC kernel prefix mismatch")
    if any((address & 0xFF000000) == 0x02000000 for address in kernel_addresses):
        fail("EventConv-FC kernel prefix collides with router clear prefix")
    counts = plan.get("counts", {})
    if not isinstance(counts, dict):
        fail("config plan counts must be mapping")
    if counts.get("readout_sources") != 784 or counts.get("readout_targets") != 10:
        fail("config plan readout dimensions mismatch")
    if int(counts.get("router_writes", 0)) <= 0:
        fail("config plan missing router writes")
    expected_plan = build_eventconv_fclif_config_plan(
        manifest,
        expected_output_words=len(trace.get("commits", [])),
    )
    if plan != expected_plan:
        fail("config plan does not match artifact-derived board writes")
    return plan


def check_report() -> None:
    if not REPORT_PATH.exists():
        fail("missing final goal report")
    text = REPORT_PATH.read_text(encoding="utf-8")
    for phrase in [
        "fixed MNIST EventConv-FC sample equivalence only",
        "Not claimed: full MNIST board accuracy",
        "Not claimed: latency",
        "Not claimed: throughput",
        "Not claimed: energy",
        "Not claimed: arbitrary EventConv shape/kernel support",
        "Training gate:",
    ]:
        if phrase not in text:
            fail(f"report missing claim-boundary phrase: {phrase}")


def check_rtl_source() -> None:
    text = RTL_TOP_PATH.read_text(encoding="utf-8")
    for phrase in [
        "BACKEND_MODE_EVENTCONV_FCLIF",
        "FCLIF_EVENTCONV_STATE_COUNT        = 784",
        "fclif_eventconv_kernel_weight_flat",
        "cfg_router_config_addr[31:24] == 8'h03",
        "eventconv_fclif_backend_mode",
    ]:
        if phrase not in text:
            fail(f"RTL final-slice support missing phrase: {phrase}")


def main() -> int:
    artifact = read_spikemold_artifact(ARTIFACT_PATH)
    report = validate_eventconv_fclif_manifest(artifact.manifest)
    if report.get("ok") is not True:
        fail("artifact deployability validation failed")
    check_training_gate(artifact.manifest)
    trace = check_trace(artifact.manifest)
    check_config_plan(artifact.manifest, trace)
    check_report()
    check_rtl_source()
    print("PASS: SpikeMold final-goal frozen SpikePress/SpikeMold artifacts valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
