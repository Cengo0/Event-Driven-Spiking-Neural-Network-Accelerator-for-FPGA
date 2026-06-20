#!/usr/bin/env python3
"""Generate deterministic MNIST-derived EventConv-FC-LIF traces.

These traces reuse the frozen SpikeMold artifact and select a tiny top-k event
set from real MNIST test images. They are for board equivalence only, not an
accuracy claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from spikepress.architecture_trace_generator import InputSpike, generate_eventconv_fclif_trace  # noqa: E402
from spikepress.spikemold_artifact import read_spikemold_artifact, validate_eventconv_fclif_manifest  # noqa: E402


DEFAULT_ARTIFACT = ROOT / "outputs" / "artifacts" / "mnist_eventconv_fclif_frozen.json"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "runtime" / "mnist_eventconv_fclif_multisample"
DEFAULT_MANIFEST = DEFAULT_OUTPUT_DIR / "manifest.json"
SCHEMA = "spikemold.mnist_eventconv_fclif_multisample_traces.v1"
CLAIM_BOUNDARY = "mnist_derived_sparse_event_samples_equivalence_only_no_accuracy_latency_throughput_energy"


def repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--download-dir", default=str(ROOT / "data"))
    parser.add_argument("--num-samples", type=int, default=5)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--max-output-words", type=int, default=64)
    parser.add_argument("--download", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def split_artifact_weights(manifest: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    network = manifest["network"]
    eventconv = network["eventconv"]
    readout = network["readout"]
    weights = manifest["weights"]
    values = np.asarray(weights["values"], dtype=np.int8)
    kernel_count = int(weights["kernel_count"])
    kernel_shape = tuple(int(v) for v in eventconv["kernel_shape"])
    readout_shape = (int(readout["source_size"]), int(readout["target_size"]))
    return (
        values[:kernel_count].reshape(kernel_shape).astype(np.int16),
        values[kernel_count:].reshape(readout_shape).astype(np.int16),
    )


def load_mnist_test(download_dir: Path, *, download: bool) -> Any:
    try:
        from torchvision import datasets, transforms
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("torchvision is required to generate MNIST sample traces") from exc

    return datasets.MNIST(
        root=str(download_dir),
        train=False,
        download=download,
        transform=transforms.ToTensor(),
    )


def image_to_topk_spikes(image: Any, *, top_k: int) -> tuple[list[InputSpike], list[dict[str, Any]]]:
    arr = np.asarray(image, dtype=np.float32)
    if arr.ndim == 3:
        arr = arr[0]
    if arr.shape != (28, 28):
        raise ValueError(f"expected MNIST image shape (28, 28), got {arr.shape}")
    flat = arr.reshape(-1)
    if top_k <= 0:
        raise ValueError("top_k must be positive")

    order = np.argsort(-flat, kind="stable")
    spikes: list[InputSpike] = []
    selected: list[dict[str, Any]] = []
    used = 0
    for idx in order:
        intensity = float(flat[int(idx)])
        if intensity <= 0.0:
            continue
        y = int(idx) // 28
        x = int(idx) % 28
        spikes.append(InputSpike(tick=used, src_id=used, y=y, x=x, channel=0, payload=1))
        selected.append({"rank": used, "y": y, "x": x, "intensity": intensity})
        used += 1
        if used >= top_k:
            break
    return spikes, selected


def main() -> int:
    args = parse_args()
    artifact_path = repo_path(args.artifact)
    output_dir = repo_path(args.output_dir)
    manifest_path = repo_path(args.manifest)
    output_dir.mkdir(parents=True, exist_ok=True)

    artifact = read_spikemold_artifact(artifact_path)
    report = validate_eventconv_fclif_manifest(artifact.manifest)
    if report.get("ok") is not True:
        raise SystemExit("artifact deployability validation failed")
    kernel, readout = split_artifact_weights(artifact.manifest)
    dataset = load_mnist_test(Path(args.download_dir), download=bool(args.download))

    samples: list[dict[str, Any]] = []
    dataset_index = int(args.start_index)
    while len(samples) < int(args.num_samples) and dataset_index < len(dataset):
        image, label = dataset[dataset_index]
        spikes, selected_pixels = image_to_topk_spikes(image, top_k=int(args.top_k))
        if not spikes:
            dataset_index += 1
            continue

        trace_id = f"mnist_eventconv_fclif_top{args.top_k}_sample_{dataset_index:04d}_v1"
        trace = generate_eventconv_fclif_trace(
            input_spikes=spikes,
            kernel=kernel.tolist(),
            input_shape=(1, 28, 28),
            readout_weights=readout.tolist(),
            stride=2,
            padding=1,
            conv_thresholds={idx: 1 for idx in range(4 * 14 * 14)},
            readout_thresholds={784 + idx: 1 for idx in range(10)},
            trace_id=trace_id,
            target="pynq-z2",
        )
        trace_dict = trace.to_dict()
        commit_count = len(trace_dict["commits"])
        if commit_count <= 0 or commit_count > int(args.max_output_words):
            dataset_index += 1
            continue

        trace_path = output_dir / f"{trace_id}.json"
        trace.write_json(trace_path)
        samples.append(
            {
                "dataset_index": dataset_index,
                "label": int(label),
                "trace_id": trace_id,
                "trace_path": str(trace_path.relative_to(ROOT)),
                "trace_file_sha256": sha256_file(trace_path),
                "trace_sha256": trace_dict["hashes"]["trace_sha256"],
                "input_event_count": len(spikes),
                "commit_count": commit_count,
                "selected_pixels": selected_pixels,
            }
        )
        dataset_index += 1

    if len(samples) < int(args.num_samples):
        raise SystemExit(f"only generated {len(samples)} samples")

    manifest = {
        "schema": SCHEMA,
        "claim_boundary": CLAIM_BOUNDARY,
        "artifact": {
            "path": str(artifact_path.relative_to(ROOT)),
            "file_sha256": artifact.sha256,
            "manifest_sha256": artifact.manifest["hashes"]["artifact_sha256"],
        },
        "dataset": {
            "name": "MNIST",
            "split": "test",
            "start_index": int(args.start_index),
            "top_k": int(args.top_k),
        },
        "limits": {
            "max_output_words": int(args.max_output_words),
        },
        "samples": samples,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "manifest": str(manifest_path), "samples": len(samples)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
