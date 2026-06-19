#!/usr/bin/env python3
"""Generate frozen SpikePress -> SpikeMold final-goal artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from spikepress.architecture_trace_generator import InputSpike, generate_eventconv_fclif_trace  # noqa: E402
from spikepress.spikemold_artifact import build_eventconv_fclif_artifact, write_spikemold_artifact  # noqa: E402
from spikepress.transport import build_eventconv_fclif_config_plan  # noqa: E402


ARTIFACT_PATH = ROOT / "outputs" / "artifacts" / "mnist_eventconv_fclif_frozen.json"
TRACE_PATH = ROOT / "golden_traces" / "v1" / "mnist_eventconv_fclif_frozen_v1.json"
CONFIG_PLAN_PATH = ROOT / "outputs" / "runtime" / "mnist_eventconv_fclif_config_plan.json"
REPORT_PATH = ROOT / "reports" / "spikemold_final_goal_report.md"


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


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_report(artifact: object, trace: object, config_plan: dict[str, object]) -> None:
    manifest = artifact.manifest  # type: ignore[attr-defined]
    trace_dict = trace.to_dict()  # type: ignore[attr-defined]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        "\n".join(
            [
                "# SpikeMold Final Goal Contract Report",
                "",
                "Status: host-side frozen SpikePress/SpikeMold contract generated.",
                "",
                "## Frozen Slice",
                "",
                "- Model: `EventConv(1x28x28, 4 filters, 3x3, stride 2, padding 1) -> sparse FC-LIF(784->10)`",
                "- Hardware states: `794` (`784` EventConv states + `10` readout states)",
                "- Backend mode: `2`",
                "- Router fanout limit: `32`; generated sparse readout max fanout: `1`",
                "",
                "## Artifacts",
                "",
                f"- Artifact: `{ARTIFACT_PATH.relative_to(ROOT)}`",
                f"- Artifact SHA256: `{manifest['hashes']['artifact_sha256']}`",
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
                "Run `python scripts/check_spikemold_final_goal.py`, focused frozen-slice xsim, then at most two integrated Vivado builds.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    kernel = build_kernel()
    readout = build_sparse_readout()
    input_spikes = build_sample_input()

    artifact = build_eventconv_fclif_artifact(
        kernel=kernel,
        readout_weights=readout,
        conv_threshold=1,
        readout_thresholds=[1] * 10,
        artifact_id="mnist_eventconv_fclif_frozen",
    )
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
    config_plan = build_eventconv_fclif_config_plan(artifact.manifest)

    write_spikemold_artifact(ARTIFACT_PATH, artifact)
    trace.write_json(TRACE_PATH)
    write_json(CONFIG_PLAN_PATH, config_plan)
    write_report(artifact, trace, config_plan)

    print(f"Wrote {ARTIFACT_PATH.relative_to(ROOT)}")
    print(f"Wrote {TRACE_PATH.relative_to(ROOT)}")
    print(f"Wrote {CONFIG_PLAN_PATH.relative_to(ROOT)}")
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
