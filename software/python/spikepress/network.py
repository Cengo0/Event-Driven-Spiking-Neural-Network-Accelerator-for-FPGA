"""SpikePress network topology compiler.

Provides a small API for defining EDNP-compatible SNN topologies with explicit
neuron populations and directed projections. The flat weight buffer layout is
computed at compile time and maps to the SpikeMold hardware artifact contract.

Example:
    >>> from spikepress.network import SpikePressNeuronPopulation, SpikePressProjection, SpikePressNetwork
    >>> input_pop = SpikePressNeuronPopulation(784, name="input")
    >>> hidden_pop = SpikePressNeuronPopulation(2048, name="hidden")
    >>> output_pop = SpikePressNeuronPopulation(10, name="output")
    >>> network = SpikePressNetwork()
    >>> network.add_population(input_pop)
    >>> network.add_population(hidden_pop)
    >>> network.add_population(output_pop)
    >>> input_to_hidden = SpikePressProjection(input_pop, hidden_pop)
    >>> hidden_to_output = SpikePressProjection(hidden_pop, output_pop)
    >>> network.add_projection(input_to_hidden)
    >>> network.add_projection(hidden_to_output)
    >>> compiled = network.compile()
    >>> flat_weights = compiled.pack_weights({"input_to_hidden": w1, "hidden_to_output": w2})
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional

# Import generated constants for validation
try:
    from config.generated.snn_params import (
        MAX_WEIGHT_BUFFER_SIZE,
        NUM_CONNECTIONS,
        NUM_NEURON_GROUPS,
        NEURON_GROUP_SIZES,
        NEURON_GROUP_ID_START,
        CONNECTIONS as HW_CONNECTIONS,
        PACKED_MAX_WEIGHT,
        PACKED_MIN_WEIGHT,
        WEIGHT_BITS,
    )
    _HW_PARAMS_AVAILABLE = True
except ImportError:
    _HW_PARAMS_AVAILABLE = False
    PACKED_MAX_WEIGHT = 7
    PACKED_MIN_WEIGHT = -8
    WEIGHT_BITS = 4


# =============================================================================
# SpikePressNeuronPopulation
# =============================================================================
class SpikePressNeuronPopulation:
    """A population of logical neurons."""

    def __init__(self, size: int, name: str = ""):
        if size <= 0:
            raise ValueError(f"SpikePressNeuronPopulation size must be positive, got {size}")
        self.size = size
        self.name = name
        self._population_index: Optional[int] = None  # set by SpikePressNetwork.add_population
        self._id_start: Optional[int] = None      # set by SpikePressNetwork.compile

    def __repr__(self):
        return f"SpikePressNeuronPopulation(size={self.size}, name='{self.name}')"


# =============================================================================
class SpikePressProjection:
    """A directed synaptic projection between two neuron populations.

    Weights are stored as a `(source.size, target.size)` matrix.
    """

    def __init__(self, source: SpikePressNeuronPopulation, target: SpikePressNeuronPopulation, name: str = ""):
        self.source = source
        self.target = target
        self.name = name or f"{source.name}_to_{target.name}"
        self._weights: Optional[np.ndarray] = None
        self._projection_index: Optional[int] = None       # set by SpikePressNetwork
        self._weight_offset: Optional[int] = None     # set by SpikePressNetwork.compile

    @property
    def weights(self) -> np.ndarray:
        """Weight matrix, shape `(source.size, target.size)`."""
        if self._weights is None:
            self._weights = np.zeros((self.source.size, self.target.size), dtype=np.int8)
        return self._weights

    @weights.setter
    def weights(self, value: np.ndarray):
        value = np.asarray(value, dtype=np.int8)
        if value.shape != (self.source.size, self.target.size):
            raise ValueError(
                f"Weight shape {value.shape} doesn't match "
                f"({self.source.size}, {self.target.size})"
            )
        self._weights = value

    @property
    def num_weights(self) -> int:
        return self.source.size * self.target.size

    def __repr__(self):
        return (
            f"SpikePressProjection('{self.name}': "
            f"{self.source.name}[{self.source.size}] -> "
            f"{self.target.name}[{self.target.size}], "
            f"weights={self.num_weights})"
        )


# =============================================================================
# CompiledSpikePressTopology
# =============================================================================
@dataclass
class SpikePressProjectionInfo:
    """Metadata for one synaptic projection in the compiled topology."""
    name: str
    source_population: int
    target_population: int
    source_size: int
    target_size: int
    weight_offset: int
    num_weights: int
    source_id_start: int
    target_id_start: int


@dataclass
class CompiledSpikePressTopology:
    """Compiled network topology with flat weight buffer layout."""
    populations: List[SpikePressNeuronPopulation]
    projections: List[SpikePressProjectionInfo]
    population_id_start: List[int]
    total_logical_neurons: int
    max_weight_buffer_size: int

    def pack_weights(self, weight_dict: Dict[str, np.ndarray]) -> np.ndarray:
        """Pack per-projection weight matrices into a single flat buffer.

        Args:
            weight_dict: {projection_name: np.ndarray of shape (source_size, target_size)}

        Returns:
            Flat int8 array of length max_weight_buffer_size.
            Values are clipped to [PACKED_MIN_WEIGHT, PACKED_MAX_WEIGHT]
            matching the HLS packed_weight_t range (default 4-bit: [-8, 7]).
        """
        flat = np.zeros(self.max_weight_buffer_size, dtype=np.int8)
        for projection in self.projections:
            if projection.name in weight_dict:
                # Clip to packed weight range before storing
                weights = np.clip(
                    np.asarray(weight_dict[projection.name]),
                    PACKED_MIN_WEIGHT, PACKED_MAX_WEIGHT
                ).astype(np.int8)
                if weights.shape != (projection.source_size, projection.target_size):
                    raise ValueError(
                        f"Weight '{projection.name}' shape {weights.shape} doesn't match "
                        f"({projection.source_size}, {projection.target_size})"
                    )
                flat[
                    projection.weight_offset:projection.weight_offset + projection.num_weights
                ] = weights.ravel()
        return flat

    def unpack_weights(self, flat: np.ndarray) -> Dict[str, np.ndarray]:
        """Unpack a flat weight buffer into per-projection matrices.

        Args:
            flat: int8 array of length max_weight_buffer_size

        Returns:
            Dict of {projection_name: np.ndarray of shape (source_size, target_size)}
        """
        result = {}
        for projection in self.projections:
            flat_slice = flat[projection.weight_offset:projection.weight_offset + projection.num_weights]
            result[projection.name] = flat_slice.reshape(projection.source_size, projection.target_size)
        return result

    def weight_index(self, pre_id: int, post_id: int) -> int:
        """Compute flat buffer index for a (pre_id, post_id) pair.

        Matches HLS weight_index() function exactly.

        Returns:
            Flat buffer offset, or -1 if no projection exists.
        """
        source_population = self._find_population(pre_id)
        target_population = self._find_population(post_id)
        if source_population < 0 or target_population < 0:
            return -1

        for projection in self.projections:
            if (
                projection.source_population == source_population
                and projection.target_population == target_population
            ):
                local_source = pre_id - projection.source_id_start
                local_target = post_id - projection.target_id_start
                return projection.weight_offset + local_source * projection.target_size + local_target
        return -1

    def _find_population(self, neuron_id: int) -> int:
        """Find which population a neuron ID belongs to. Returns -1 if not found."""
        for index in range(len(self.populations)):
            if self.population_id_start[index] <= neuron_id < self.population_id_start[index + 1]:
                return index
        return -1

    def validate_against_hardware(self) -> List[str]:
        """Validate this compiled network matches the HW-generated constants.

        Returns list of error messages (empty = all good).
        """
        if not _HW_PARAMS_AVAILABLE:
            return ["Cannot validate: config.generated.snn_params not importable"]

        errors = []
        if self.max_weight_buffer_size != MAX_WEIGHT_BUFFER_SIZE:
            errors.append(
                f"max_weight_buffer_size mismatch: compiled={self.max_weight_buffer_size} "
                f"vs HW={MAX_WEIGHT_BUFFER_SIZE}"
            )
        if len(self.projections) != NUM_CONNECTIONS:
            errors.append(
                f"projection_count mismatch: compiled={len(self.projections)} "
                f"vs HW={NUM_CONNECTIONS}"
            )
        if self.total_logical_neurons != sum(NEURON_GROUP_SIZES):
            errors.append(
                f"total_logical_neurons mismatch: compiled={self.total_logical_neurons} "
                f"vs HW={sum(NEURON_GROUP_SIZES)}"
            )
        for i, projection in enumerate(self.projections):
            if i < len(HW_CONNECTIONS):
                hw = HW_CONNECTIONS[i]
                if projection.weight_offset != hw['weight_offset']:
                    errors.append(
                        f"projection '{projection.name}' weight_offset: "
                        f"compiled={projection.weight_offset} vs HW={hw['weight_offset']}"
                    )
        return errors


# =============================================================================
# SpikePressNetwork
# =============================================================================
class SpikePressNetwork:
    """Network definition that compiles to a flat weight buffer layout.

    Usage:
        network = SpikePressNetwork()
        network.add_population(SpikePressNeuronPopulation(784, "input"))
        network.add_population(SpikePressNeuronPopulation(2048, "hidden"))
        network.add_population(SpikePressNeuronPopulation(10, "output"))
        network.add_projection(SpikePressProjection(input_population, hidden_population))
        network.add_projection(SpikePressProjection(hidden_population, output_population))
        compiled = network.compile()
    """

    def __init__(self):
        self._populations: List[SpikePressNeuronPopulation] = []
        self._projections: List[SpikePressProjection] = []
        self._compiled: Optional[CompiledSpikePressTopology] = None

    def add_population(self, population: SpikePressNeuronPopulation) -> SpikePressNeuronPopulation:
        """Add a neuron population to the network. Returns the population."""
        if self._compiled is not None:
            raise RuntimeError("Cannot modify network after compile()")
        population._population_index = len(self._populations)
        self._populations.append(population)
        return population

    def add_projection(self, projection: SpikePressProjection) -> SpikePressProjection:
        """Add a directed projection. Returns the projection."""
        if self._compiled is not None:
            raise RuntimeError("Cannot modify network after compile()")
        if projection.source not in self._populations:
            raise ValueError(f"Source population '{projection.source.name}' not added to network")
        if projection.target not in self._populations:
            raise ValueError(f"Target population '{projection.target.name}' not added to network")
        projection._projection_index = len(self._projections)
        self._projections.append(projection)
        return projection

    def compile(self) -> CompiledSpikePressTopology:
        """Compile the network topology into a flat weight buffer layout.

        Computes population ID start offsets and projection weight offsets.
        """
        if self._compiled is not None:
            return self._compiled

        # Compute population ID starts.
        population_id_start = [0]
        for population in self._populations:
            population_id_start.append(population_id_start[-1] + population.size)
        total_logical_neurons = population_id_start[-1]

        # Assign population IDs.
        for index, population in enumerate(self._populations):
            population._id_start = population_id_start[index]

        # Compute projection offsets.
        weight_offset = 0
        projection_infos = []
        for projection in self._projections:
            source_index = projection.source._population_index
            target_index = projection.target._population_index
            if source_index is None or target_index is None:
                raise RuntimeError("projection population index missing")
            weight_count = projection.source.size * projection.target.size
            projection._weight_offset = weight_offset

            projection_infos.append(SpikePressProjectionInfo(
                name=projection.name,
                source_population=source_index,
                target_population=target_index,
                source_size=projection.source.size,
                target_size=projection.target.size,
                weight_offset=weight_offset,
                num_weights=weight_count,
                source_id_start=population_id_start[source_index],
                target_id_start=population_id_start[target_index],
            ))
            weight_offset += weight_count

        self._compiled = CompiledSpikePressTopology(
            populations=self._populations,
            projections=projection_infos,
            population_id_start=population_id_start,
            total_logical_neurons=total_logical_neurons,
            max_weight_buffer_size=weight_offset,
        )
        return self._compiled

    @staticmethod
    def from_config() -> "SpikePressNetwork":
        """Create a network from the hardware-generated configuration.

        Uses config/generated/snn_params.py constants to rebuild
        the exact topology that matches the HLS flat buffer layout.
        """
        if not _HW_PARAMS_AVAILABLE:
            raise RuntimeError(
                "Cannot load HW config: config.generated.snn_params not importable. "
                "Run config/generate_params.py first."
            )

        from config.generated.snn_params import (
            NEURON_GROUP_NAMES,
            NEURON_GROUP_SIZES,
            CONNECTIONS as HW_CONNS,
        )

        network = SpikePressNetwork()
        populations = []
        for name, size in zip(NEURON_GROUP_NAMES, NEURON_GROUP_SIZES):
            population = SpikePressNeuronPopulation(size, name=name)
            network.add_population(population)
            populations.append(population)

        for conn in HW_CONNS:
            projection = SpikePressProjection(
                populations[conn['src_group']],
                populations[conn['dst_group']],
                name=conn['name'],
            )
            network.add_projection(projection)

        return network

    @property
    def populations(self) -> List[SpikePressNeuronPopulation]:
        return list(self._populations)

    @property
    def projections(self) -> List[SpikePressProjection]:
        return list(self._projections)

    def summary(self) -> str:
        """Human-readable summary of the network topology."""
        lines = ["SpikePress Network Summary", "=" * 40]

        lines.append(f"\nNeuron populations ({len(self._populations)}):")
        for index, population in enumerate(self._populations):
            lines.append(f"  [{index}] {population.name}: {population.size} neurons")

        lines.append(f"\nProjections ({len(self._projections)}):")
        total_weights = 0
        for projection in self._projections:
            lines.append(
                f"  {projection.name}: {projection.source.name}[{projection.source.size}] -> "
                f"{projection.target.name}[{projection.target.size}] = {projection.num_weights:,} weights"
            )
            total_weights += projection.num_weights

        lines.append(f"\nTotal weights: {total_weights:,}")
        lines.append(f"Buffer size (int8): {total_weights:,} bytes = {total_weights/1024:.1f} KB")

        dense_weight_count = sum(population.size for population in self._populations) ** 2
        if dense_weight_count > 0:
            reduction = (1 - total_weights / dense_weight_count) * 100
            lines.append(f"vs all-to-all dense: {dense_weight_count:,} -> {reduction:.1f}% reduction")

        return "\n".join(lines)


# =============================================================================
# Convenience: create the default MNIST network topology
# =============================================================================
def create_mnist_network(hidden_size: int = 2048) -> SpikePressNetwork:
    """Create the standard MNIST 3-layer SNN network (fully-connected).

    Args:
        hidden_size: Number of hidden layer neurons (default: 2048)

    Returns:
        SpikePressNetwork ready to compile.

    Note:
        This creates a fully-connected topology.  For the BRAM-optimised
        block-sparse version, use :func:`create_mnist_block_sparse_network`.
    """
    network = SpikePressNetwork()
    input_population = network.add_population(SpikePressNeuronPopulation(784, name="input"))
    hidden_population = network.add_population(SpikePressNeuronPopulation(hidden_size, name="hidden"))
    output_population = network.add_population(SpikePressNeuronPopulation(10, name="output"))
    network.add_projection(SpikePressProjection(input_population, hidden_population))
    network.add_projection(SpikePressProjection(hidden_population, output_population))
    return network


def create_mnist_block_sparse_network(
    n_blocks: int = 4,
    hidden_per_block: int = 1024,
) -> SpikePressNetwork:
    """Create a block-sparse MNIST SNN with local input partitions.

    The 784 MNIST input pixels are split into ``n_blocks`` horizontal stripes,
    each connecting to a dedicated block of ``hidden_per_block`` hidden neurons.
    All hidden blocks converge fully-connected to the 10-class output layer.

    With the default (n_blocks=4, hidden_per_block=1024):
      - 4 input populations of 196 pixels (7 MNIST rows each)
      - 4 hidden populations of 1024 neurons each (4096 total)
      - 1 output population of 10 neurons
      - Total projection weights: 843,776  (48% less than fully-connected)
      - At 4-bit: 263 BRAM18K  (93.9% of xc7z020)

    Args:
        n_blocks: Number of spatial blocks to partition the image into.
        hidden_per_block: Hidden neurons per block.

    Returns:
        SpikePressNetwork ready to compile.
    """
    assert 784 % n_blocks == 0, f"784 must be divisible by n_blocks={n_blocks}"
    pixels_per_block = 784 // n_blocks

    network = SpikePressNetwork()

    # Input populations (image stripe partitions)
    input_populations = []
    for index in range(n_blocks):
        population = network.add_population(SpikePressNeuronPopulation(pixels_per_block, name=f"input_{index}"))
        input_populations.append(population)

    # Hidden populations (one per block)
    hidden_populations = []
    for index in range(n_blocks):
        population = network.add_population(SpikePressNeuronPopulation(hidden_per_block, name=f"hidden_{index}"))
        hidden_populations.append(population)

    # Output population
    output_population = network.add_population(SpikePressNeuronPopulation(10, name="output"))

    # Block-sparse input→hidden projections
    for index in range(n_blocks):
        network.add_projection(SpikePressProjection(input_populations[index], hidden_populations[index]))

    # Fully-connected hidden→output projections
    for hidden_population in hidden_populations:
        network.add_projection(SpikePressProjection(hidden_population, output_population))

    return network
