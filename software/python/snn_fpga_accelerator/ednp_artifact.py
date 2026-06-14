"""Minimal EDNP compiler artifact helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Sequence

import numpy as np

from .network import CompiledNetwork


ARTIFACT_SCHEMA = "ednp.artifact.v1"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class EDNPArtifact:
    manifest: Mapping[str, object]
    flat_weights: np.ndarray

    @property
    def sha256(self) -> str:
        return str(self.manifest["hashes"]["artifact_sha256"])  # type: ignore[index]


def build_ednp_artifact(
    compiled: CompiledNetwork,
    weight_dict: Mapping[str, np.ndarray],
    *,
    target: str = "pynq-z2",
    artifact_id: str = "ednp_artifact",
) -> EDNPArtifact:
    """Build a minimal hardware-deployable EDNP artifact manifest."""

    flat = compiled.pack_weights(dict(weight_dict)).astype(np.int8, copy=False)
    flat_bytes = flat.tobytes()
    groups = [
        {
            "name": group.name,
            "size": int(group.n),
            "id_start": int(compiled.group_id_start[index]),
        }
        for index, group in enumerate(compiled.groups)
    ]
    connections = [
        {
            "name": conn.name,
            "src_group": int(conn.src_group),
            "dst_group": int(conn.dst_group),
            "src_size": int(conn.src_size),
            "dst_size": int(conn.dst_size),
            "weight_offset": int(conn.weight_offset),
            "num_weights": int(conn.num_weights),
            "src_id_start": int(conn.src_id_start),
            "dst_id_start": int(conn.dst_id_start),
        }
        for conn in compiled.connections
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
            "groups": groups,
            "group_id_start": [int(v) for v in compiled.group_id_start],
            "connections": connections,
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
    return EDNPArtifact(manifest=manifest, flat_weights=flat.copy())


def write_ednp_artifact(path: Path, artifact: EDNPArtifact) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_ednp_artifact(path: Path) -> EDNPArtifact:
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
    return EDNPArtifact(manifest=manifest, flat_weights=flat)

