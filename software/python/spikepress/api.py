"""Minimal SpikePress API for SpikeMold-EDNP Batch 1A.

This module is inference-only. It intentionally exposes only compile and trace
generation objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional, Sequence

import numpy as np

from .architecture_trace_generator import InputSpike, SpikeMoldContractTrace, generate_fc_lif_trace
from .spikemold_ednp_artifact import SpikeMoldEDNPArtifact, build_spikemold_ednp_artifact
from .event_budget import EventBudgetResult, evaluate_trace_budget
from .network import SpikePressNeuronPopulation, SpikePressProjection, SpikePressNetwork


@dataclass(frozen=True)
class SpikePressFCLIFLayer:
    name: str
    input_size: int
    output_size: int
    weights: np.ndarray
    thresholds: np.ndarray

    @staticmethod
    def create(
        name: str,
        weights: Sequence[Sequence[int]],
        thresholds: Optional[Sequence[int]] = None,
    ) -> "SpikePressFCLIFLayer":
        array = np.asarray(weights, dtype=np.int16)
        if array.ndim != 2:
            raise ValueError("FC-LIF weights must be a 2D matrix")
        input_size, output_size = array.shape
        if thresholds is None:
            threshold_array = np.full(output_size, 1 << 30, dtype=np.int32)
        else:
            threshold_array = np.asarray(thresholds, dtype=np.int32)
            if threshold_array.shape != (output_size,):
                raise ValueError(f"threshold shape must be ({output_size},)")
        return SpikePressFCLIFLayer(
            name=name,
            input_size=int(input_size),
            output_size=int(output_size),
            weights=array,
            thresholds=threshold_array,
        )


@dataclass(frozen=True)
class SpikePressCompileResult:
    model_name: str
    artifact: SpikeMoldEDNPArtifact
    resource_report: Mapping[str, object]


class SpikePressModel:
    """Small inference-only model authoring surface for SpikeMold-EDNP mini."""

    def __init__(self, name: str):
        self.name = name
        self._layers: list[SpikePressFCLIFLayer] = []

    @property
    def layers(self) -> tuple[SpikePressFCLIFLayer, ...]:
        return tuple(self._layers)

    def add_fc_lif(
        self,
        name: str,
        weights: Sequence[Sequence[int]],
        thresholds: Optional[Sequence[int]] = None,
    ) -> SpikePressFCLIFLayer:
        if self._layers:
            raise ValueError("Batch 1A SpikeMold-EDNP mini supports one FC-LIF layer")
        layer = SpikePressFCLIFLayer.create(name, weights, thresholds)
        self._layers.append(layer)
        return layer

    def compile_spikemold_ednp(self, *, target: str = "pynq-z2") -> SpikePressCompileResult:
        layer = self._single_layer()
        network = SpikePressNetwork()
        input_population = network.add_population(SpikePressNeuronPopulation(layer.input_size, "input"))
        output_population = network.add_population(SpikePressNeuronPopulation(layer.output_size, layer.name))
        network.add_projection(
            SpikePressProjection(input_population, output_population, name=f"input_to_{layer.name}")
        )
        compiled_network = network.compile()
        artifact = build_spikemold_ednp_artifact(
            compiled_network,
            {f"input_to_{layer.name}": layer.weights},
            target=target,
            artifact_id=self.name,
        )
        report = {
            "schema": "spikemold.resource_report.v1",
            "target": target,
            "model_name": self.name,
            "layers": 1,
            "total_logical_neurons": compiled_network.total_logical_neurons,
            "max_weight_buffer_size": compiled_network.max_weight_buffer_size,
            "weight_bytes": int(artifact.flat_weights.nbytes),
            "state_bytes_i32": int(layer.output_size * 4),
            "projection_count": len(compiled_network.projections),
            "python_inner_loop_required": False,
        }
        return SpikePressCompileResult(
            model_name=self.name,
            artifact=artifact,
            resource_report=report,
        )

    def golden_trace(self, input_spikes: Iterable[InputSpike]) -> SpikeMoldContractTrace:
        layer = self._single_layer()
        weights: Dict[tuple[int, int], int] = {}
        for src in range(layer.input_size):
            for dst in range(layer.output_size):
                weight = int(layer.weights[src, dst])
                if weight != 0:
                    weights[(src, layer.input_size + dst)] = weight
        thresholds = {
            layer.input_size + dst: int(threshold)
            for dst, threshold in enumerate(layer.thresholds.tolist())
        }
        return generate_fc_lif_trace(
            input_spikes=input_spikes,
            weights=weights,
            thresholds=thresholds,
            trace_id=f"{self.name}_{layer.name}_golden",
        )

    def evaluate_sample_budget(self, input_spikes: Iterable[InputSpike]) -> EventBudgetResult:
        return evaluate_trace_budget(self.golden_trace(input_spikes).to_dict())

    def _single_layer(self) -> SpikePressFCLIFLayer:
        if len(self._layers) != 1:
            raise ValueError("SpikePressModel requires exactly one FC-LIF layer for SpikeMold-EDNP mini")
        return self._layers[0]


def fc_lif_model(
    name: str,
    weights: Sequence[Sequence[int]],
    thresholds: Optional[Sequence[int]] = None,
) -> SpikePressModel:
    model = SpikePressModel(name)
    model.add_fc_lif("output", weights, thresholds)
    return model
