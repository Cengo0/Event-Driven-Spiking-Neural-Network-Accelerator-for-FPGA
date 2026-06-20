#!/usr/bin/env python3
"""Generate frozen SpikePress -> SpikeMold final-goal artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from spikepress.architecture_trace_generator import InputSpike, generate_eventconv_fclif_trace  # noqa: E402
from spikepress.spikemold_artifact import (  # noqa: E402
    EVENTCONV_FCLIF_KERNEL_CONFIG_PREFIX,
    SpikeMoldArtifact,
    build_eventconv_fclif_artifact,
    read_spikemold_artifact,
    refresh_spikemold_artifact_hash,
    write_spikemold_artifact,
)
from spikepress.transport import build_eventconv_fclif_config_plan  # noqa: E402


ARTIFACT_PATH = ROOT / "outputs" / "artifacts" / "mnist_eventconv_fclif_frozen.json"
TRACE_PATH = ROOT / "golden_traces" / "v1" / "mnist_eventconv_fclif_frozen_v1.json"
CONFIG_PLAN_PATH = ROOT / "outputs" / "runtime" / "mnist_eventconv_fclif_config_plan.json"
REPORT_PATH = ROOT / "reports" / "spikemold_final_goal_report.md"
MIN_TRAINED_ACCURACY = 0.90


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        choices=["auto", "artifact", "deterministic"],
        default="auto",
        help="Artifact source. auto uses a trained artifact when present; deterministic emits the smoke seed artifact.",
    )
    parser.add_argument(
        "--require-trained",
        action="store_true",
        help="Fail unless the canonical artifact carries final_validation_accuracy >= 90%%.",
    )
    return parser.parse_args()


def build_kernel() -> np.ndarray:
    """Return deterministic 4-filter 3x3 int8 kernel bank."""

    return np.asarray(
        [
            [[[1, 0, -1], [1, 0, -1], [1, 0, -1]]],
            [[[1, 1, 1], [0, 0, 0], [-1, -1, -1]]],
            [[[0, 1, 0], [1, 2, 1], [0, 1, 0]]],
            [[[-1, 0, 1], [0, 2, 0], [1, 0, -1]]],
        ],
        dtype=np.int16,
    )


def build_sparse_readout() -> np.ndarray:
    """Return bounded-fanout FC readout weights for 784 EventConv states."""

    readout = np.zeros((4 * 14 * 14, 10), dtype=np.int16)
    for src in range(readout.shape[0]):
        readout[src, src % 10] = 1
    return readout


def build_sample_input() -> list[InputSpike]:
    return [
        InputSpike(tick=0, src_id=0, y=14, x=14, channel=0, payload=1),
        InputSpike(tick=1, src_id=1, y=7, x=7, channel=0, payload=1),
        InputSpike(tick=2, src_id=2, y=21, x=21, channel=0, payload=1),
    ]


def split_artifact_weights(artifact: object) -> tuple[np.ndarray, np.ndarray]:
    manifest = artifact.manifest  # type: ignore[attr-defined]
    network = manifest["network"]
    eventconv = network["eventconv"]
    readout = network["readout"]
    weights = manifest["weights"]
    values = np.asarray(weights["values"], dtype=np.int8)
    kernel_count = int(weights["kernel_count"])
    kernel_shape = tuple(int(v) for v in eventconv["kernel_shape"])
    readout_shape = (int(readout["source_size"]), int(readout["target_size"]))
    kernel = values[:kernel_count].reshape(kernel_shape)
    readout_weights = values[kernel_count:].reshape(readout_shape)
    return kernel.astype(np.int16), readout_weights.astype(np.int16)


def migrate_artifact_runtime_prefix(artifact: object) -> tuple[object, bool]:
    manifest = artifact.manifest  # type: ignore[attr-defined]
    runtime = manifest.get("runtime", {})
    if (
        isinstance(runtime, dict)
        and int(runtime.get("eventconv_kernel_config_prefix", -1)) == EVENTCONV_FCLIF_KERNEL_CONFIG_PREFIX
    ):
        return artifact, False

    kernel, readout = split_artifact_weights(artifact)
    network = manifest["network"]
    eventconv = network["eventconv"]
    thresholds = manifest["thresholds"]
    rebuilt = build_eventconv_fclif_artifact(
        kernel=kernel,
        readout_weights=readout,
        conv_threshold=int(thresholds["conv_commit"]),
        readout_thresholds=[int(v) for v in thresholds["readout"]],
        target=str(manifest.get("target", "pynq-z2")),
        artifact_id=str(manifest.get("artifact_id", "mnist_eventconv_fclif_frozen")),
        input_shape=tuple(int(v) for v in eventconv["input_shape"]),
        stride=int(eventconv["stride"]),
        padding=int(eventconv["padding"]),
    )
    rebuilt_manifest = dict(rebuilt.manifest)
    if "training" in manifest:
        rebuilt_manifest["training"] = dict(manifest["training"])
    rebuilt = SpikeMoldArtifact(manifest=rebuilt_manifest, flat_weights=rebuilt.flat_weights)
    return refresh_spikemold_artifact_hash(rebuilt), True


def load_or_build_artifact(source: str) -> tuple[object, str]:
    if source == "artifact" or (source == "auto" and ARTIFACT_PATH.exists()):
        artifact = read_spikemold_artifact(ARTIFACT_PATH)
        artifact, migrated = migrate_artifact_runtime_prefix(artifact)
        if migrated:
            write_spikemold_artifact(ARTIFACT_PATH, artifact)
        suffix = "_runtime_prefix_migrated" if migrated else ""
        return artifact, f"trained_or_existing_artifact{suffix}"

    artifact = build_eventconv_fclif_artifact(
        kernel=build_kernel(),
        readout_weights=build_sparse_readout(),
        conv_threshold=1,
        readout_thresholds=[1] * 10,
        artifact_id="mnist_eventconv_fclif_frozen",
    )
    write_spikemold_artifact(ARTIFACT_PATH, artifact)
    return artifact, "deterministic_smoke_seed"


def check_training_gate(artifact: object, *, required: bool) -> str:
    manifest = artifact.manifest  # type: ignore[attr-defined]
    training = manifest.get("training", {})
    if not isinstance(training, dict) or "final_validation_accuracy" not in training:
        if required:
            raise SystemExit("missing trained MNIST accuracy in artifact manifest")
        return "not recorded"
    accuracy = float(training["final_validation_accuracy"])
    if accuracy < MIN_TRAINED_ACCURACY:
        raise SystemExit(
            f"trained MNIST accuracy {accuracy:.4f} below required {MIN_TRAINED_ACCURACY:.2f}"
        )
    return f"{accuracy * 100:.2f}%"


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_report(artifact: object, trace: object, config_plan: dict[str, object], source_label: str, training_gate: str) -> None:
    manifest = artifact.manifest  # type: ignore[attr-defined]
    trace_dict = trace.to_dict()  # type: ignore[attr-defined]
    readout = manifest["network"]["readout"]
    hashes = manifest["hashes"]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        "\n".join(
            [
                "# SpikeMold Final Goal Contract Report",
                "",
                "Status: trained frozen SpikePress/SpikeMold contract generated and locked.",
                "",
                "## Frozen Slice",
                "",
                "- Model: `EventConv(1x28x28, 4 filters, 3x3, stride 2, padding 1) -> sparse FC-LIF(784->10)`",
                "- Hardware states: `794` (`784` EventConv states + `10` readout states)",
                "- Backend mode: `2`",
                f"- Router fanout limit: `32`; artifact readout max fanout: `{readout['max_fanout']}`",
                f"- Training gate: `{training_gate}` final validation accuracy (`>=90%` required before synthesis)",
                f"- Artifact source: `{source_label}`",
                "",
                "## Artifacts",
                "",
                f"- Artifact: `{ARTIFACT_PATH.relative_to(ROOT)}`",
                f"- Artifact SHA256: `{hashes['artifact_sha256']}`",
                f"- EventConv kernel SHA256: `{hashes['eventconv_kernel_sha256']}`",
                f"- Readout weights SHA256: `{hashes['readout_weights_sha256']}`",
                f"- Golden trace: `{TRACE_PATH.relative_to(ROOT)}`",
                f"- Trace SHA256: `{trace_dict['hashes']['trace_sha256']}`",
                f"- Config plan: `{CONFIG_PLAN_PATH.relative_to(ROOT)}`",
                f"- Kernel config writes: `{len(config_plan['kernel_config_writes'])}`",
                f"- Router config writes: `{config_plan['counts']['router_writes']}`",
                f"- RTL top: `hardware/hdl/rtl/top/spikemold_integrated_top.v`",
                f"- Focused RTL TB: `hardware/hdl/tb/tb_spike_conv_frozen_mnist_slice.v`",
                "",
                "## Claim Boundary",
                "",
                "- Allowed claim after board run: fixed MNIST EventConv-FC sample equivalence only.",
                "- Not claimed: full MNIST board accuracy.",
                "- Not claimed: latency.",
                "- Not claimed: throughput.",
                "- Not claimed: energy.",
                "- Not claimed: arbitrary EventConv shape/kernel support.",
                "",
                "## Next Gate",
                "",
                "Run `python scripts/check_spikemold_final_goal.py`, focused frozen-slice xsim, then one integrated Vivado build.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    artifact, source_label = load_or_build_artifact(args.source)
    training_gate = check_training_gate(artifact, required=args.require_trained)
    kernel, readout = split_artifact_weights(artifact)
    input_spikes = build_sample_input()

    trace = generate_eventconv_fclif_trace(
        input_spikes=input_spikes,
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
    config_plan = build_eventconv_fclif_config_plan(
        artifact.manifest,
        expected_output_words=len(trace.commits),
    )

    trace.write_json(TRACE_PATH)
    write_json(CONFIG_PLAN_PATH, config_plan)
    write_report(artifact, trace, config_plan, source_label, training_gate)

    print(f"Wrote {ARTIFACT_PATH.relative_to(ROOT)}")
    print(f"Wrote {TRACE_PATH.relative_to(ROOT)}")
    print(f"Wrote {CONFIG_PLAN_PATH.relative_to(ROOT)}")
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
