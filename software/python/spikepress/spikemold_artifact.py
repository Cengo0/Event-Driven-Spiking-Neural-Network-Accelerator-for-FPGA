"""Minimal SpikeMold compiler artifact helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Sequence

import numpy as np

from .network import CompiledSpikePressTopology


ARTIFACT_SCHEMA = "spikemold.artifact.v1"
EVENTCONV_FCLIF_KIND = "eventconv_fclif_mnist_v1"
EVENTCONV_FCLIF_BACKEND_MODE = 2
EVENTCONV_FCLIF_PHYSICAL_NEURONS = 1024
EVENTCONV_FCLIF_MAX_FANOUT = 32
EVENTCONV_FCLIF_KERNEL_CONFIG_PREFIX = 0x02000000


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class SpikeMoldArtifact:
    manifest: Mapping[str, object]
    flat_weights: np.ndarray

    @property
    def sha256(self) -> str:
        return str(self.manifest["hashes"]["artifact_sha256"])  # type: ignore[index]


def build_spikemold_artifact(
    compiled: CompiledSpikePressTopology,
    weight_dict: Mapping[str, np.ndarray],
    *,
    target: str = "pynq-z2",
    artifact_id: str = "spikemold_artifact",
) -> SpikeMoldArtifact:
    """Build a minimal hardware-deployable SpikeMold artifact manifest."""

    flat = compiled.pack_weights(dict(weight_dict)).astype(np.int8, copy=False)
    flat_bytes = flat.tobytes()
    populations = [
        {
            "name": population.name,
            "size": int(population.size),
            "id_start": int(compiled.population_id_start[index]),
        }
        for index, population in enumerate(compiled.populations)
    ]
    projections = [
        {
            "name": projection.name,
            "source_population": int(projection.source_population),
            "target_population": int(projection.target_population),
            "source_size": int(projection.source_size),
            "target_size": int(projection.target_size),
            "weight_offset": int(projection.weight_offset),
            "num_weights": int(projection.num_weights),
            "source_id_start": int(projection.source_id_start),
            "target_id_start": int(projection.target_id_start),
        }
        for projection in compiled.projections
    ]
    manifest: Dict[str, object] = {
        "schema": ARTIFACT_SCHEMA,
        "artifact_id": artifact_id,
        "target": target,
        "contracts": {
            "integer_semantics": "INTEGER_SEMANTICS_V1",
            "event_format": "EVENT_FORMAT_V1",
            "trace_schema": "TRACE_SCHEMA_V1",
            "resource_budget": "RESOURCE_BUDGET_V1",
        },
        "network": {
            "populations": populations,
            "population_id_start": [int(v) for v in compiled.population_id_start],
            "projections": projections,
            "total_logical_neurons": int(compiled.total_logical_neurons),
            "max_weight_buffer_size": int(compiled.max_weight_buffer_size),
        },
        "weights": {
            "dtype": "int8",
            "layout": "flat_connection_major",
            "count": int(flat.size),
            "values": [int(v) for v in flat.tolist()],
        },
        "hashes": {
            "flat_weights_sha256": _sha256_bytes(flat_bytes),
        },
    }
    manifest["hashes"]["artifact_sha256"] = _sha256_bytes(  # type: ignore[index]
        _canonical_json(manifest).encode("utf-8")
    )
    return SpikeMoldArtifact(manifest=manifest, flat_weights=flat.copy())


def _eventconv_output_hw(
    input_h: int,
    input_w: int,
    kernel_h: int,
    kernel_w: int,
    stride: int,
    padding: int,
) -> tuple[int, int]:
    out_h = ((int(input_h) + (2 * int(padding)) - int(kernel_h)) // int(stride)) + 1
    out_w = ((int(input_w) + (2 * int(padding)) - int(kernel_w)) // int(stride)) + 1
    if out_h <= 0 or out_w <= 0:
        raise ValueError("invalid EventConv output shape")
    return out_h, out_w


def _as_clipped_i8(name: str, value: object) -> np.ndarray:
    array = np.asarray(value)
    if not np.issubdtype(array.dtype, np.number):
        raise ValueError(f"{name} must be numeric")
    return np.clip(np.rint(array), -128, 127).astype(np.int8)


def build_eventconv_fclif_artifact(
    *,
    kernel: object,
    readout_weights: object,
    conv_threshold: int = 1,
    readout_thresholds: Sequence[int] | None = None,
    target: str = "pynq-z2",
    artifact_id: str = "mnist_eventconv_fclif_frozen",
    input_shape: tuple[int, int, int] = (1, 28, 28),
    stride: int = 2,
    padding: int = 1,
) -> SpikeMoldArtifact:
    """Build the frozen MNIST EventConv -> FC-LIF SpikeMold artifact.

    The artifact is intentionally narrow: one shared-kernel EventConv stage and
    one FC-LIF readout. Validation rejects shapes that cannot map to the current
    direct RTL boundary.
    """

    kernel_i8 = _as_clipped_i8("kernel", kernel)
    if kernel_i8.ndim != 4:
        raise ValueError("kernel must have shape [out_channels, in_channels, ky, kx]")
    out_channels, in_channels, kernel_h, kernel_w = [int(v) for v in kernel_i8.shape]
    expected_in_channels, input_h, input_w = [int(v) for v in input_shape]
    if in_channels != expected_in_channels:
        raise ValueError(f"kernel input channels {in_channels} != input_shape channels {expected_in_channels}")

    readout_i8 = _as_clipped_i8("readout_weights", readout_weights)
    if readout_i8.ndim != 2:
        raise ValueError("readout_weights must have shape [conv_state_count, classes]")
    out_h, out_w = _eventconv_output_hw(input_h, input_w, kernel_h, kernel_w, stride, padding)
    conv_state_count = int(out_channels * out_h * out_w)
    if readout_i8.shape[0] != conv_state_count:
        raise ValueError(
            f"readout source rows {readout_i8.shape[0]} != conv state count {conv_state_count}"
        )
    readout_classes = int(readout_i8.shape[1])
    if readout_classes <= 0:
        raise ValueError("readout must have at least one class")
    total_states = conv_state_count + readout_classes
    if total_states > EVENTCONV_FCLIF_PHYSICAL_NEURONS:
        raise ValueError(
            f"frozen slice uses {total_states} states; limit is {EVENTCONV_FCLIF_PHYSICAL_NEURONS}"
        )

    nonzero_fanout = np.count_nonzero(readout_i8, axis=1)
    max_fanout = int(nonzero_fanout.max(initial=0))
    if max_fanout > EVENTCONV_FCLIF_MAX_FANOUT:
        raise ValueError(f"readout fanout {max_fanout} exceeds {EVENTCONV_FCLIF_MAX_FANOUT}")

    if readout_thresholds is None:
        readout_threshold_array = np.full(readout_classes, int(conv_threshold), dtype=np.int32)
    else:
        readout_threshold_array = np.asarray(readout_thresholds, dtype=np.int32)
        if readout_threshold_array.shape != (readout_classes,):
            raise ValueError(f"readout_thresholds must have shape ({readout_classes},)")
    if np.any(readout_threshold_array < 0) or np.any(readout_threshold_array > 0xFFFF):
        raise ValueError("readout thresholds must fit uint16")
    if int(conv_threshold) < 0 or int(conv_threshold) > 0xFFFF:
        raise ValueError("conv_threshold must fit uint16")

    flat = np.concatenate([kernel_i8.ravel(), readout_i8.ravel()]).astype(np.int8, copy=False)
    flat_bytes = flat.tobytes()
    kernel_words = int(kernel_i8.size)
    readout_id_start = conv_state_count
    manifest: Dict[str, object] = {
        "schema": ARTIFACT_SCHEMA,
        "artifact_id": artifact_id,
        "target": target,
        "kind": EVENTCONV_FCLIF_KIND,
        "contracts": {
            "integer_semantics": "INTEGER_SEMANTICS_V1",
            "event_format": "EVENT_FORMAT_V1",
            "trace_schema": "TRACE_SCHEMA_V1",
            "resource_budget": "RESOURCE_BUDGET_V1",
            "register_map": "REGISTER_MAP_MINIMAL_V1",
        },
        "network": {
            "kind": EVENTCONV_FCLIF_KIND,
            "populations": [
                {"name": "eventconv_state", "size": conv_state_count, "id_start": 0},
                {"name": "readout", "size": readout_classes, "id_start": readout_id_start},
            ],
            "population_id_start": [0, readout_id_start],
            "total_logical_neurons": total_states,
            "max_weight_buffer_size": int(flat.size),
            "eventconv": {
                "input_shape": [in_channels, input_h, input_w],
                "kernel_shape": [out_channels, in_channels, kernel_h, kernel_w],
                "output_shape": [out_channels, out_h, out_w],
                "stride": int(stride),
                "padding": int(padding),
                "state_count": conv_state_count,
                "kernel_weight_count": kernel_words,
            },
            "readout": {
                "source_population": "eventconv_state",
                "target_population": "readout",
                "source_size": conv_state_count,
                "target_size": readout_classes,
                "source_id_start": 0,
                "target_id_start": readout_id_start,
                "max_fanout": max_fanout,
                "nonzero_weights": int(np.count_nonzero(readout_i8)),
            },
        },
        "thresholds": {
            "conv_commit": int(conv_threshold),
            "readout": [int(v) for v in readout_threshold_array.tolist()],
            "single_global_threshold_compatible": bool(np.all(readout_threshold_array == int(conv_threshold))),
        },
        "weights": {
            "dtype": "int8",
            "layout": "eventconv_kernel_cout_cin_ky_kx_then_readout_src_dst",
            "count": int(flat.size),
            "kernel_count": int(kernel_i8.size),
            "readout_count": int(readout_i8.size),
            "values": [int(v) for v in flat.tolist()],
        },
        "runtime": {
            "backend_mode": EVENTCONV_FCLIF_BACKEND_MODE,
            "physical_neurons": EVENTCONV_FCLIF_PHYSICAL_NEURONS,
            "max_fanout": EVENTCONV_FCLIF_MAX_FANOUT,
            "eventconv_kernel_config_prefix": EVENTCONV_FCLIF_KERNEL_CONFIG_PREFIX,
            "router_conn_prefix": 0x00000000,
            "router_count_prefix": 0x01000000,
            "input_axis32_format": "eventconv_coord32_x_y_channel_payload",
            "board_claim_boundary": "fixed MNIST EventConv-FC sample equivalence only",
        },
        "hashes": {
            "flat_weights_sha256": _sha256_bytes(flat_bytes),
            "eventconv_kernel_sha256": _sha256_bytes(kernel_i8.tobytes()),
            "readout_weights_sha256": _sha256_bytes(readout_i8.tobytes()),
        },
    }
    manifest["hashes"]["artifact_sha256"] = _sha256_bytes(  # type: ignore[index]
        _canonical_json(manifest).encode("utf-8")
    )
    artifact = SpikeMoldArtifact(manifest=manifest, flat_weights=flat.copy())
    validate_eventconv_fclif_manifest(artifact.manifest)
    return artifact


def validate_eventconv_fclif_manifest(manifest: Mapping[str, object]) -> Dict[str, object]:
    """Validate deployability of the frozen EventConv -> FC-LIF artifact."""

    if manifest.get("schema") != ARTIFACT_SCHEMA:
        raise ValueError(f"unsupported artifact schema: {manifest.get('schema')}")
    if manifest.get("kind") != EVENTCONV_FCLIF_KIND:
        raise ValueError(f"unsupported artifact kind: {manifest.get('kind')}")
    network = manifest.get("network", {})
    if not isinstance(network, Mapping):
        raise ValueError("network must be a mapping")
    eventconv = network.get("eventconv", {})
    readout = network.get("readout", {})
    runtime = manifest.get("runtime", {})
    thresholds = manifest.get("thresholds", {})
    if not isinstance(eventconv, Mapping) or not isinstance(readout, Mapping) or not isinstance(runtime, Mapping):
        raise ValueError("eventconv/readout/runtime sections must be mappings")
    input_shape = list(eventconv.get("input_shape", []))
    kernel_shape = list(eventconv.get("kernel_shape", []))
    output_shape = list(eventconv.get("output_shape", []))
    if input_shape != [1, 28, 28]:
        raise ValueError(f"unsupported input_shape: {input_shape}")
    if kernel_shape != [4, 1, 3, 3]:
        raise ValueError(f"unsupported kernel_shape: {kernel_shape}")
    if output_shape != [4, 14, 14]:
        raise ValueError(f"unsupported output_shape: {output_shape}")
    if int(eventconv.get("stride", -1)) != 2 or int(eventconv.get("padding", -1)) != 1:
        raise ValueError("unsupported EventConv stride/padding")
    state_count = int(eventconv.get("state_count", -1))
    target_size = int(readout.get("target_size", -1))
    total = int(network.get("total_logical_neurons", -1))
    if state_count != 784 or target_size != 10 or total != 794:
        raise ValueError(f"unexpected state/readout totals: {state_count}/{target_size}/{total}")
    if int(readout.get("max_fanout", EVENTCONV_FCLIF_MAX_FANOUT + 1)) > EVENTCONV_FCLIF_MAX_FANOUT:
        raise ValueError("readout max_fanout exceeds hardware limit")
    if int(runtime.get("backend_mode", -1)) != EVENTCONV_FCLIF_BACKEND_MODE:
        raise ValueError("runtime backend_mode mismatch")
    if bool(thresholds.get("single_global_threshold_compatible", False)) is not True:
        raise ValueError("frozen RTL path requires one global threshold")
    if total > EVENTCONV_FCLIF_PHYSICAL_NEURONS:
        raise ValueError("total states exceed physical neuron limit")
    return {
        "ok": True,
        "kind": EVENTCONV_FCLIF_KIND,
        "total_logical_neurons": total,
        "eventconv_state_count": state_count,
        "readout_classes": target_size,
        "max_fanout": int(readout.get("max_fanout", 0)),
        "backend_mode": EVENTCONV_FCLIF_BACKEND_MODE,
    }


def write_spikemold_artifact(path: Path, artifact: SpikeMoldArtifact) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def refresh_spikemold_artifact_hash(artifact: SpikeMoldArtifact) -> SpikeMoldArtifact:
    """Refresh artifact hash after adding non-weight manifest metadata."""

    manifest = dict(artifact.manifest)
    hashes = dict(manifest.get("hashes", {}))
    hashes["flat_weights_sha256"] = _sha256_bytes(artifact.flat_weights.tobytes())
    hashes.pop("artifact_sha256", None)
    manifest["hashes"] = hashes
    hashes["artifact_sha256"] = _sha256_bytes(_canonical_json(manifest).encode("utf-8"))
    return SpikeMoldArtifact(manifest=manifest, flat_weights=artifact.flat_weights.copy())


def read_spikemold_artifact(path: Path) -> SpikeMoldArtifact:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != ARTIFACT_SCHEMA:
        raise ValueError(f"unsupported artifact schema: {manifest.get('schema')}")
    weights = manifest.get("weights", {})
    if weights.get("dtype") != "int8":
        raise ValueError(f"unsupported weight dtype: {weights.get('dtype')}")
    flat = np.asarray(weights.get("values", []), dtype=np.int8)
    expected_count = int(weights.get("count", -1))
    if flat.size != expected_count:
        raise ValueError(f"weight count mismatch: {flat.size} != {expected_count}")
    hashes = manifest.get("hashes", {})
    if hashes.get("flat_weights_sha256") != _sha256_bytes(flat.tobytes()):
        raise ValueError("flat weight hash mismatch")
    manifest_without_artifact_hash = dict(manifest)
    manifest_without_artifact_hash["hashes"] = dict(hashes)
    expected_artifact_hash = manifest_without_artifact_hash["hashes"].pop("artifact_sha256", None)
    if expected_artifact_hash != _sha256_bytes(_canonical_json(manifest_without_artifact_hash).encode("utf-8")):
        raise ValueError("artifact hash mismatch")
    return SpikeMoldArtifact(manifest=manifest, flat_weights=flat)
