"""Minimal SpikeMold-EDNP compiler artifact helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Sequence

import numpy as np

from .network import CompiledSpikePressTopology


ARTIFACT_SCHEMA = "spikemold.ednp_artifact.v1"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class SpikeMoldEDNPArtifact:
    manifest: Mapping[str, object]
    flat_weights: np.ndarray

    @property
    def sha256(self) -> str:
        return str(self.manifest["hashes"]["artifact_sha256"])  # type: ignore[index]


def build_spikemold_ednp_artifact(
    compiled: CompiledSpikePressTopology,
    weight_dict: Mapping[str, np.ndarray],
    *,
    target: str = "pynq-z2",
    artifact_id: str = "spikemold_ednp_artifact",
) -> SpikeMoldEDNPArtifact:
    """Build a minimal hardware-deployable SpikeMold-EDNP artifact manifest."""

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
    return SpikeMoldEDNPArtifact(manifest=manifest, flat_weights=flat.copy())


def write_spikemold_ednp_artifact(path: Path, artifact: SpikeMoldEDNPArtifact) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_spikemold_ednp_artifact(path: Path) -> SpikeMoldEDNPArtifact:
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
    return SpikeMoldEDNPArtifact(manifest=manifest, flat_weights=flat)
