"""
NeuronGroup-aware Network API (Brian2-style)

Provides a high-level API for defining SNN topologies with explicit
NeuronGroup connections, matching the Brian2 programming model.

The flat weight buffer layout is computed at compile time and maps
directly to the HLS weight_memory[] flat buffer.

Example:
    >>> from snn_fpga_accelerator.network import NeuronGroup, Synapses, SNNNetwork
    >>> inp = NeuronGroup(784, name='input')
    >>> hid = NeuronGroup(2048, name='hidden')
    >>> out = NeuronGroup(10, name='output')
    >>> net = SNNNetwork()
    >>> net.add_group(inp)
    >>> net.add_group(hid)
    >>> net.add_group(out)
    >>> s1 = Synapses(inp, hid)
    >>> s2 = Synapses(hid, out)
    >>> net.add_synapses(s1)
    >>> net.add_synapses(s2)
    >>> cfg = net.compile()
    >>> flat_weights = cfg.pack_weights({'input_to_hidden': w1, 'hidden_to_output': w2})
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

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
# NeuronGroup — Brian2-style neuron population
# =============================================================================
class NeuronGroup:
    """A population of neurons, analogous to Brian2's NeuronGroup."""

    def __init__(self, n: int, name: str = ""):
        if n <= 0:
            raise ValueError(f"NeuronGroup size must be positive, got {n}")
        self.n = n
        self.name = name
        self._group_index: Optional[int] = None  # set by SNNNetwork.add_group
        self._id_start: Optional[int] = None      # set by SNNNetwork.compile

    def __repr__(self):
        return f"NeuronGroup(n={self.n}, name='{self.name}')"


# =============================================================================
# Synapses — Brian2-style synaptic connection between two groups
# =============================================================================
class Synapses:
    """A synaptic connection from src NeuronGroup to dst NeuronGroup.

    Weights are stored as a (src.n, dst.n) matrix.
    """

    def __init__(self, src: NeuronGroup, dst: NeuronGroup, name: str = ""):
        self.src = src
        self.dst = dst
        self.name = name or f"{src.name}_to_{dst.name}"
        self._weights: Optional[np.ndarray] = None  # (src.n, dst.n), int8
        self._conn_index: Optional[int] = None       # set by SNNNetwork
        self._weight_offset: Optional[int] = None     # set by SNNNetwork.compile

    @property
    def w(self) -> np.ndarray:
        """Weight matrix, shape (src.n, dst.n)."""
        if self._weights is None:
            self._weights = np.zeros((self.src.n, self.dst.n), dtype=np.int8)
        return self._weights

    @w.setter
    def w(self, value: np.ndarray):
        value = np.asarray(value, dtype=np.int8)
        if value.shape != (self.src.n, self.dst.n):
            raise ValueError(
                f"Weight shape {value.shape} doesn't match "
                f"({self.src.n}, {self.dst.n})"
            )
        self._weights = value

    @property
    def num_weights(self) -> int:
        return self.src.n * self.dst.n

    def __repr__(self):
        return (f"Synapses('{self.name}': {self.src.name}[{self.src.n}] → "
                f"{self.dst.name}[{self.dst.n}], "
                f"weights={self.num_weights})")


# =============================================================================
# CompiledNetwork — immutable snapshot of the compiled network topology
# =============================================================================
@dataclass
class ConnectionInfo:
    """Metadata for one synaptic connection in the compiled network."""
    name: str
    src_group: int
    dst_group: int
    src_size: int
    dst_size: int
    weight_offset: int
    num_weights: int
    src_id_start: int
    dst_id_start: int


@dataclass
class CompiledNetwork:
    """Compiled network topology with flat weight buffer layout."""
    groups: List[NeuronGroup]
    connections: List[ConnectionInfo]
    group_id_start: List[int]
    total_logical_neurons: int
    max_weight_buffer_size: int

    def pack_weights(self, weight_dict: Dict[str, np.ndarray]) -> np.ndarray:
        """Pack per-connection weight matrices into a single flat buffer.

        Args:
            weight_dict: {connection_name: np.ndarray of shape (src_size, dst_size)}

        Returns:
            Flat int8 array of length max_weight_buffer_size.
            Values are clipped to [PACKED_MIN_WEIGHT, PACKED_MAX_WEIGHT]
            matching the HLS packed_weight_t range (default 4-bit: [-8, 7]).
        """
        flat = np.zeros(self.max_weight_buffer_size, dtype=np.int8)
        for conn in self.connections:
            if conn.name in weight_dict:
                # Clip to packed weight range before storing
                w = np.clip(
                    np.asarray(weight_dict[conn.name]),
                    PACKED_MIN_WEIGHT, PACKED_MAX_WEIGHT
                ).astype(np.int8)
                if w.shape != (conn.src_size, conn.dst_size):
                    raise ValueError(
                        f"Weight '{conn.name}' shape {w.shape} doesn't match "
                        f"({conn.src_size}, {conn.dst_size})"
                    )
                flat[conn.weight_offset:conn.weight_offset + conn.num_weights] = w.ravel()
        return flat

    def unpack_weights(self, flat: np.ndarray) -> Dict[str, np.ndarray]:
        """Unpack a flat weight buffer into per-connection matrices.

        Args:
            flat: int8 array of length max_weight_buffer_size

        Returns:
            Dict of {connection_name: np.ndarray of shape (src_size, dst_size)}
        """
        result = {}
        for conn in self.connections:
            w_flat = flat[conn.weight_offset:conn.weight_offset + conn.num_weights]
            result[conn.name] = w_flat.reshape(conn.src_size, conn.dst_size)
        return result

    def weight_index(self, pre_id: int, post_id: int) -> int:
        """Compute flat buffer index for a (pre_id, post_id) pair.

        Matches HLS weight_index() function exactly.

        Returns:
            Flat buffer offset, or -1 if not connected.
        """
        src_g = self._find_group(pre_id)
        dst_g = self._find_group(post_id)
        if src_g < 0 or dst_g < 0:
            return -1

        for conn in self.connections:
            if conn.src_group == src_g and conn.dst_group == dst_g:
                local_src = pre_id - conn.src_id_start
                local_dst = post_id - conn.dst_id_start
                return conn.weight_offset + local_src * conn.dst_size + local_dst
        return -1

    def _find_group(self, nid: int) -> int:
        """Find which group a neuron ID belongs to. Returns -1 if not found."""
        for g in range(len(self.groups)):
            if self.group_id_start[g] <= nid < self.group_id_start[g + 1]:
                return g
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
        if len(self.connections) != NUM_CONNECTIONS:
            errors.append(
                f"num_connections mismatch: compiled={len(self.connections)} "
                f"vs HW={NUM_CONNECTIONS}"
            )
        if self.total_logical_neurons != sum(NEURON_GROUP_SIZES):
            errors.append(
                f"total_logical_neurons mismatch: compiled={self.total_logical_neurons} "
                f"vs HW={sum(NEURON_GROUP_SIZES)}"
            )
        for i, conn in enumerate(self.connections):
            if i < len(HW_CONNECTIONS):
                hw = HW_CONNECTIONS[i]
                if conn.weight_offset != hw['weight_offset']:
                    errors.append(
                        f"connection '{conn.name}' weight_offset: "
                        f"compiled={conn.weight_offset} vs HW={hw['weight_offset']}"
                    )
        return errors


# =============================================================================
# SNNNetwork — Brian2-style network builder
# =============================================================================
class SNNNetwork:
    """Network definition that compiles to a flat weight buffer layout.

    Usage:
        net = SNNNetwork()
        net.add_group(NeuronGroup(784, 'input'))
        net.add_group(NeuronGroup(2048, 'hidden'))
        net.add_group(NeuronGroup(10, 'output'))
        net.add_synapses(Synapses(input_group, hidden_group))
        net.add_synapses(Synapses(hidden_group, output_group))
        compiled = net.compile()
    """

    def __init__(self):
        self._groups: List[NeuronGroup] = []
        self._synapses: List[Synapses] = []
        self._compiled: Optional[CompiledNetwork] = None

    def add_group(self, group: NeuronGroup) -> NeuronGroup:
        """Add a NeuronGroup to the network. Returns the group for chaining."""
        if self._compiled is not None:
            raise RuntimeError("Cannot modify network after compile()")
        group._group_index = len(self._groups)
        self._groups.append(group)
        return group

    def add_synapses(self, syn: Synapses) -> Synapses:
        """Add a Synapses connection. Returns the synapses for chaining."""
        if self._compiled is not None:
            raise RuntimeError("Cannot modify network after compile()")
        if syn.src not in self._groups:
            raise ValueError(f"Source group '{syn.src.name}' not added to network")
        if syn.dst not in self._groups:
            raise ValueError(f"Destination group '{syn.dst.name}' not added to network")
        syn._conn_index = len(self._synapses)
        self._synapses.append(syn)
        return syn

    def compile(self) -> CompiledNetwork:
        """Compile the network topology into a flat weight buffer layout.

        Computes group ID start offsets and connection weight offsets.
        """
        if self._compiled is not None:
            return self._compiled

        # Compute group_id_start
        group_id_start = [0]
        for g in self._groups:
            group_id_start.append(group_id_start[-1] + g.n)
        total_logical_neurons = group_id_start[-1]

        # Assign group IDs
        for i, g in enumerate(self._groups):
            g._id_start = group_id_start[i]

        # Compute connection offsets
        weight_offset = 0
        conn_infos = []
        for syn in self._synapses:
            src_idx = syn.src._group_index
            dst_idx = syn.dst._group_index
            num_w = syn.src.n * syn.dst.n
            syn._weight_offset = weight_offset

            conn_infos.append(ConnectionInfo(
                name=syn.name,
                src_group=src_idx,
                dst_group=dst_idx,
                src_size=syn.src.n,
                dst_size=syn.dst.n,
                weight_offset=weight_offset,
                num_weights=num_w,
                src_id_start=group_id_start[src_idx],
                dst_id_start=group_id_start[dst_idx],
            ))
            weight_offset += num_w

        self._compiled = CompiledNetwork(
            groups=self._groups,
            connections=conn_infos,
            group_id_start=group_id_start,
            total_logical_neurons=total_logical_neurons,
            max_weight_buffer_size=weight_offset,
        )
        return self._compiled

    @staticmethod
    def from_config() -> 'SNNNetwork':
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

        net = SNNNetwork()
        groups = []
        for name, size in zip(NEURON_GROUP_NAMES, NEURON_GROUP_SIZES):
            g = NeuronGroup(size, name=name)
            net.add_group(g)
            groups.append(g)

        for conn in HW_CONNS:
            syn = Synapses(
                groups[conn['src_group']],
                groups[conn['dst_group']],
                name=conn['name'],
            )
            net.add_synapses(syn)

        return net

    @property
    def groups(self) -> List[NeuronGroup]:
        return list(self._groups)

    @property
    def synapses(self) -> List[Synapses]:
        return list(self._synapses)

    def summary(self) -> str:
        """Human-readable summary of the network topology."""
        lines = ["SNN Network Summary", "=" * 40]

        lines.append(f"\nNeuronGroups ({len(self._groups)}):")
        for i, g in enumerate(self._groups):
            lines.append(f"  [{i}] {g.name}: {g.n} neurons")

        lines.append(f"\nSynapses ({len(self._synapses)}):")
        total_weights = 0
        for syn in self._synapses:
            lines.append(
                f"  {syn.name}: {syn.src.name}[{syn.src.n}] → "
                f"{syn.dst.name}[{syn.dst.n}] = {syn.num_weights:,} weights"
            )
            total_weights += syn.num_weights

        lines.append(f"\nTotal weights: {total_weights:,}")
        lines.append(f"Buffer size (int8): {total_weights:,} bytes = {total_weights/1024:.1f} KB")

        old_size = sum(g.n for g in self._groups) ** 2
        if old_size > 0:
            reduction = (1 - total_weights / old_size) * 100
            lines.append(f"vs N×N dense: {old_size:,} → {reduction:.1f}% reduction")

        return "\n".join(lines)


# =============================================================================
# Convenience: create the default MNIST network topology
# =============================================================================
def create_mnist_network(n_hidden: int = 2048) -> SNNNetwork:
    """Create the standard MNIST 3-layer SNN network (fully-connected).

    Args:
        n_hidden: Number of hidden layer neurons (default: 2048)

    Returns:
        SNNNetwork ready to compile.

    Note:
        This creates a fully-connected topology.  For the BRAM-optimised
        block-sparse version, use :func:`create_mnist_block_sparse_network`.
    """
    net = SNNNetwork()
    inp = net.add_group(NeuronGroup(784, name='input'))
    hid = net.add_group(NeuronGroup(n_hidden, name='hidden'))
    out = net.add_group(NeuronGroup(10, name='output'))
    net.add_synapses(Synapses(inp, hid))
    net.add_synapses(Synapses(hid, out))
    return net


def create_mnist_block_sparse_network(
    n_blocks: int = 4,
    hidden_per_block: int = 1024,
) -> SNNNetwork:
    """Create a block-sparse MNIST SNN (Loihi-inspired local connectivity).

    The 784 MNIST input pixels are split into ``n_blocks`` horizontal stripes,
    each connecting to a dedicated block of ``hidden_per_block`` hidden neurons.
    All hidden blocks converge fully-connected to the 10-class output layer.

    With the default (n_blocks=4, hidden_per_block=1024):
      - 4 input groups of 196 pixels (7 MNIST rows each)
      - 4 hidden groups of 1024 neurons each (4096 total)
      - 1 output group of 10 neurons
      - Total synapses: 843,776  (48% less than fully-connected)
      - At 4-bit: 263 BRAM18K  (93.9% of xc7z020)

    Args:
        n_blocks: Number of spatial blocks to partition the image into.
        hidden_per_block: Hidden neurons per block.

    Returns:
        SNNNetwork ready to compile.
    """
    assert 784 % n_blocks == 0, f"784 must be divisible by n_blocks={n_blocks}"
    pixels_per_block = 784 // n_blocks

    net = SNNNetwork()

    # Input groups (image stripe partitions)
    inp_groups = []
    for i in range(n_blocks):
        g = net.add_group(NeuronGroup(pixels_per_block, name=f'input_{i}'))
        inp_groups.append(g)

    # Hidden groups (one per block)
    hid_groups = []
    for i in range(n_blocks):
        g = net.add_group(NeuronGroup(hidden_per_block, name=f'hidden_{i}'))
        hid_groups.append(g)

    # Output group
    out = net.add_group(NeuronGroup(10, name='output'))

    # Block-sparse input→hidden connections
    for i in range(n_blocks):
        net.add_synapses(Synapses(inp_groups[i], hid_groups[i]))

    # Fully-connected hidden→output connections
    for i in range(n_blocks):
        net.add_synapses(Synapses(hid_groups[i], out))

    return net
