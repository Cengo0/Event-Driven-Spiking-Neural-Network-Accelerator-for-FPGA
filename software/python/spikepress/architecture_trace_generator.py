"""Architecture-neutral SpikeMold trace generation.

The objects in this module are small deterministic golden builders for the
SpikePress + SpikeMold contract. They do not model a full training stack.
They generate trace records that flat pipelines, coregroups, page/block sparse
experiments, and EventConv AGU candidates can consume without semantic changes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Set


INT32_MIN = -(1 << 31)
INT32_MAX = (1 << 31) - 1
TRACE_SCHEMA = "spikemold.trace.v1"


def _clamp_i32(value: int) -> int:
    return max(INT32_MIN, min(INT32_MAX, int(value)))


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


@dataclass(frozen=True)
class InputSpike:
    tick: int
    src_id: int
    y: Optional[int] = None
    x: Optional[int] = None
    channel: Optional[int] = None
    payload: int = 1

    def to_record(self) -> Dict[str, int]:
        record = {
            "kind": "input_spike",
            "tick": int(self.tick),
            "src_id": int(self.src_id),
            "payload": int(self.payload),
        }
        if self.y is not None:
            record["y"] = int(self.y)
        if self.x is not None:
            record["x"] = int(self.x)
        if self.channel is not None:
            record["channel"] = int(self.channel)
        return record


@dataclass(frozen=True)
class SynapticUpdate:
    tick: int
    src_id: int
    dst_id: int
    weight: int
    y: Optional[int] = None
    x: Optional[int] = None
    channel: Optional[int] = None

    def to_record(self) -> Dict[str, int]:
        record = {
            "kind": "synaptic_update",
            "tick": int(self.tick),
            "src_id": int(self.src_id),
            "dst_id": int(self.dst_id),
            "weight": int(self.weight),
        }
        if self.y is not None:
            record["y"] = int(self.y)
        if self.x is not None:
            record["x"] = int(self.x)
        if self.channel is not None:
            record["channel"] = int(self.channel)
        return record


@dataclass(frozen=True)
class ActiveSetCommit:
    tick: int
    dst_id: int
    value: int

    def to_record(self) -> Dict[str, int]:
        return {
            "kind": "commit",
            "tick": int(self.tick),
            "dst_id": int(self.dst_id),
            "value": int(self.value),
        }


@dataclass(frozen=True)
class TraceCounters:
    input_event_count: int
    generated_update_count: int
    active_neuron_count: int
    commit_count: int
    state_reads: int
    state_writes: int
    ddr_bytes_inner_loop: int
    python_inner_loop_steps: int


@dataclass(frozen=True)
class SpikeMoldContractTrace:
    trace_id: str
    target: str
    metadata: Mapping[str, object]
    inputs: Sequence[InputSpike]
    updates: Sequence[SynapticUpdate]
    commits: Sequence[ActiveSetCommit]
    final_state: Mapping[int, int]
    counters: TraceCounters

    def to_dict(self) -> Dict[str, object]:
        inputs = [event.to_record() for event in self.inputs]
        updates = [event.to_record() for event in self.updates]
        commits = [event.to_record() for event in self.commits]
        final_state = {str(k): int(v) for k, v in sorted(self.final_state.items())}
        counters = asdict(self.counters)
        body: Dict[str, object] = {
            "schema": TRACE_SCHEMA,
            "trace_id": self.trace_id,
            "target": self.target,
            "metadata": dict(self.metadata),
            "inputs": inputs,
            "updates": updates,
            "commits": commits,
            "final_state": final_state,
            "counters": counters,
        }
        body["hashes"] = {
            "input_sha256": sha256_json(inputs),
            "updates_sha256": sha256_json(updates),
            "commits_sha256": sha256_json(commits),
            "final_state_sha256": sha256_json(final_state),
        }
        body["hashes"]["trace_sha256"] = sha256_json(body)
        return body

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def pack_spikemold_event_word64(
    event_type: int,
    tick: int,
    src_y_or_hi: int = 0,
    src_x_or_lo: int = 0,
    channel_or_dst_hi: int = 0,
    signed_weight: int = 0,
    flags: int = 0,
    target: int = 0,
) -> int:
    """Pack the provisional EventWord64 transport format from EVENT_FORMAT_V1."""

    sign = 1 if signed_weight < 0 else 0
    weight_abs = abs(int(signed_weight)) & 0xFF
    word = 0
    word |= (int(event_type) & 0xF) << 60
    word |= (int(tick) & 0xFFF) << 48
    word |= (int(src_y_or_hi) & 0x3FF) << 38
    word |= (int(src_x_or_lo) & 0x3FF) << 28
    word |= (int(channel_or_dst_hi) & 0xFF) << 20
    word |= sign << 19
    word |= weight_abs << 11
    word |= (int(flags) & 0x3F) << 5
    word |= int(target) & 0x1F
    return word


def generate_fc_lif_trace(
    input_spikes: Iterable[InputSpike],
    weights: Mapping[Tuple[int, int], int],
    thresholds: Mapping[int, int],
    reset_values: Optional[Mapping[int, int]] = None,
    initial_state: Optional[Mapping[int, int]] = None,
    trace_id: str = "fc_lif_tiny",
) -> SpikeMoldContractTrace:
    """Generate deterministic FC-LIF updates and active-set commits."""

    ordered_inputs = sorted(list(input_spikes), key=lambda event: (event.tick, event.src_id))
    state: MutableMapping[int, int] = {int(k): int(v) for k, v in (initial_state or {}).items()}
    reset_values = reset_values or {}
    updates: List[SynapticUpdate] = []
    commits: List[ActiveSetCommit] = []
    active = set()

    fanout = sorted(((src, dst, weight) for (src, dst), weight in weights.items()), key=lambda item: item[:2])
    for spike in ordered_inputs:
        for src, dst, weight in fanout:
            if src != spike.src_id:
                continue
            updates.append(SynapticUpdate(spike.tick, src, dst, int(weight)))
            active.add(dst)
            state[dst] = _clamp_i32(state.get(dst, 0) + int(weight))
            if state[dst] >= int(thresholds.get(dst, INT32_MAX)):
                commits.append(ActiveSetCommit(spike.tick, dst, state[dst]))
                state[dst] = int(reset_values.get(dst, 0))

    counters = TraceCounters(
        input_event_count=len(ordered_inputs),
        generated_update_count=len(updates),
        active_neuron_count=len(active),
        commit_count=len(commits),
        state_reads=len(updates),
        state_writes=len(updates) + len(commits),
        ddr_bytes_inner_loop=0,
        python_inner_loop_steps=0,
    )
    return SpikeMoldContractTrace(
        trace_id=trace_id,
        target="architecture-neutral",
        metadata={
            "primitive": "fc_lif",
            "reset_mode": "zero",
            "weight_storage": "explicit_sparse",
        },
        inputs=ordered_inputs,
        updates=updates,
        commits=commits,
        final_state=dict(state),
        counters=counters,
    )


def generate_eventconv_trace(
    input_spikes: Iterable[InputSpike],
    kernel: Sequence[Sequence[Sequence[Sequence[int]]]],
    input_shape: Tuple[int, int, int],
    stride: int = 1,
    padding: int = 0,
    thresholds: Optional[Mapping[int, int]] = None,
    trace_id: str = "eventconv_tiny",
) -> SpikeMoldContractTrace:
    """Generate shared-kernel EventConv AGU trace.

    Kernel layout is `[cout][cin][ky][kx]`.
    Input shape is `(channels, height, width)`.
    """

    in_channels, in_h, in_w = input_shape
    out_channels = len(kernel)
    if out_channels == 0:
        raise ValueError("kernel must have at least one output channel")
    kernel_h = len(kernel[0][0])
    kernel_w = len(kernel[0][0][0])
    out_h = ((in_h + 2 * padding - kernel_h) // stride) + 1
    out_w = ((in_w + 2 * padding - kernel_w) // stride) + 1
    if out_h <= 0 or out_w <= 0:
        raise ValueError("invalid output shape")

    ordered_inputs = sorted(list(input_spikes), key=lambda event: (event.tick, event.src_id))
    thresholds = thresholds or {}
    state: MutableMapping[int, int] = {}
    updates: List[SynapticUpdate] = []
    commits: List[ActiveSetCommit] = []
    active = set()

    for spike in ordered_inputs:
        if spike.y is None or spike.x is None or spike.channel is None:
            raise ValueError("eventconv spikes require y, x, and channel")
        if not (0 <= spike.channel < in_channels):
            raise ValueError("input spike channel out of range")
        for cout in range(out_channels):
            for ky in range(kernel_h):
                shifted_y = spike.y + padding - ky
                if shifted_y % stride != 0:
                    continue
                out_y = shifted_y // stride
                if not (0 <= out_y < out_h):
                    continue
                for kx in range(kernel_w):
                    shifted_x = spike.x + padding - kx
                    if shifted_x % stride != 0:
                        continue
                    out_x = shifted_x // stride
                    if not (0 <= out_x < out_w):
                        continue
                    weight = int(kernel[cout][spike.channel][ky][kx])
                    if weight == 0:
                        continue
                    dst = (cout * out_h + out_y) * out_w + out_x
                    updates.append(
                        SynapticUpdate(
                            tick=spike.tick,
                            src_id=spike.src_id,
                            dst_id=dst,
                            weight=weight,
                            y=out_y,
                            x=out_x,
                            channel=cout,
                        )
                    )
                    active.add(dst)
                    state[dst] = _clamp_i32(state.get(dst, 0) + weight)
                    if state[dst] >= int(thresholds.get(dst, INT32_MAX)):
                        commits.append(ActiveSetCommit(spike.tick, dst, state[dst]))
                        state[dst] = 0

    counters = TraceCounters(
        input_event_count=len(ordered_inputs),
        generated_update_count=len(updates),
        active_neuron_count=len(active),
        commit_count=len(commits),
        state_reads=len(updates),
        state_writes=len(updates) + len(commits),
        ddr_bytes_inner_loop=0,
        python_inner_loop_steps=0,
    )
    return SpikeMoldContractTrace(
        trace_id=trace_id,
        target="architecture-neutral",
        metadata={
            "primitive": "eventconv_agu",
            "input_shape": list(input_shape),
            "output_shape": [out_channels, out_h, out_w],
            "kernel_shape": [out_channels, in_channels, kernel_h, kernel_w],
            "stride": int(stride),
            "padding": int(padding),
            "weight_storage": "shared_kernel",
        },
        inputs=ordered_inputs,
        updates=updates,
        commits=commits,
        final_state=dict(state),
        counters=counters,
    )


def generate_eventconv_active_readout_trace(
    input_spikes: Iterable[InputSpike],
    kernel: Sequence[Sequence[Sequence[Sequence[int]]]],
    input_shape: Tuple[int, int, int],
    stride: int = 1,
    padding: int = 0,
    commit_thresholds: Optional[Mapping[int, int]] = None,
    trace_id: str = "eventconv_active_readout",
) -> SpikeMoldContractTrace:
    """Generate EventConv trace with packet-end active-set commit.

    This matches the integrated board path: input spikes first generate
    near-memory state updates, then active destinations are scanned once at
    the packet boundary.
    """

    base = generate_eventconv_trace(
        input_spikes=input_spikes,
        kernel=kernel,
        input_shape=input_shape,
        stride=stride,
        padding=padding,
        thresholds={},
        trace_id=trace_id,
    )
    thresholds = commit_thresholds or {}
    state: MutableMapping[int, int] = {int(k): int(v) for k, v in base.final_state.items()}
    active_order: List[int] = []
    for update in base.updates:
        if update.dst_id not in active_order:
            active_order.append(update.dst_id)

    commits: List[ActiveSetCommit] = []
    commit_tick = max((event.tick for event in base.inputs), default=0)
    scan_index = 0
    while scan_index < len(active_order):
        dst = active_order[scan_index]
        value = int(state.get(dst, 0))
        if value >= int(thresholds.get(dst, INT32_MAX)):
            commits.append(ActiveSetCommit(commit_tick, dst, value))
            state[dst] = 0
            active_order.pop(scan_index)
        else:
            scan_index += 1

    nonzero_state = {dst: value for dst, value in state.items() if value != 0}
    counters = TraceCounters(
        input_event_count=len(base.inputs),
        generated_update_count=len(base.updates),
        active_neuron_count=len({update.dst_id for update in base.updates}),
        commit_count=len(commits),
        state_reads=len(base.updates),
        state_writes=len(base.updates) + len(commits),
        ddr_bytes_inner_loop=0,
        python_inner_loop_steps=0,
    )
    metadata = dict(base.metadata)
    metadata.update(
        {
            "commit_mode": "packet_end_active_set",
            "active_neuron_count_after_commit": len(active_order),
            "readout_scan_count": counters.active_neuron_count,
        }
    )
    return SpikeMoldContractTrace(
        trace_id=trace_id,
        target=base.target,
        metadata=metadata,
        inputs=base.inputs,
        updates=base.updates,
        commits=commits,
        final_state=nonzero_state,
        counters=counters,
    )


def generate_eventconv_fclif_trace(
    input_spikes: Iterable[InputSpike],
    kernel: Sequence[Sequence[Sequence[Sequence[int]]]],
    input_shape: Tuple[int, int, int],
    readout_weights: Sequence[Sequence[int]],
    stride: int = 2,
    padding: int = 1,
    conv_thresholds: Optional[Mapping[int, int]] = None,
    readout_thresholds: Optional[Mapping[int, int]] = None,
    readout_id_start: Optional[int] = None,
    trace_id: str = "eventconv_fclif_mnist_slice",
    target: str = "pynq-z2",
) -> SpikeMoldContractTrace:
    """Generate frozen EventConv -> FC-LIF trace for SpikePress/SpikeMold.

    EventConv commits are internal spikes into the FC readout. The public
    `commits` list contains only final readout commits, matching the intended
    board output FIFO for the final-goal slice.
    """

    in_channels, in_h, in_w = input_shape
    out_channels = len(kernel)
    if out_channels == 0:
        raise ValueError("kernel must have at least one output channel")
    kernel_h = len(kernel[0][0])
    kernel_w = len(kernel[0][0][0])
    out_h = ((in_h + 2 * padding - kernel_h) // stride) + 1
    out_w = ((in_w + 2 * padding - kernel_w) // stride) + 1
    conv_state_count = out_channels * out_h * out_w
    if conv_state_count <= 0:
        raise ValueError("invalid EventConv output shape")

    readout_rows = [list(row) for row in readout_weights]
    if len(readout_rows) != conv_state_count:
        raise ValueError(
            f"readout row count must equal conv state count: {len(readout_rows)} != {conv_state_count}"
        )
    readout_cols = len(readout_rows[0]) if readout_rows else 0
    if readout_cols <= 0:
        raise ValueError("readout must have at least one output class")
    for row in readout_rows:
        if len(row) != readout_cols:
            raise ValueError("readout rows must have consistent class count")

    if readout_id_start is None:
        readout_id_start = conv_state_count

    if conv_thresholds is None:
        conv_thresholds = {state_id: 1 for state_id in range(conv_state_count)}
    if readout_thresholds is None:
        readout_thresholds = {
            readout_id_start + class_id: 1 for class_id in range(readout_cols)
        }

    conv_trace = generate_eventconv_active_readout_trace(
        input_spikes=input_spikes,
        kernel=kernel,
        input_shape=input_shape,
        stride=stride,
        padding=padding,
        commit_thresholds=conv_thresholds,
        trace_id=f"{trace_id}_eventconv_internal",
    )

    readout_state: MutableMapping[int, int] = {}
    readout_updates: List[SynapticUpdate] = []
    readout_commits: List[ActiveSetCommit] = []
    readout_active = set()

    for conv_commit in conv_trace.commits:
        src = int(conv_commit.dst_id)
        if not 0 <= src < conv_state_count:
            raise ValueError(f"conv commit id out of readout range: {src}")
        for class_id, weight in enumerate(readout_rows[src]):
            weight = int(weight)
            if weight == 0:
                continue
            dst = readout_id_start + class_id
            readout_updates.append(
                SynapticUpdate(
                    tick=int(conv_commit.tick),
                    src_id=src,
                    dst_id=dst,
                    weight=weight,
                )
            )
            readout_active.add(dst)
            readout_state[dst] = _clamp_i32(readout_state.get(dst, 0) + weight)
            if readout_state[dst] >= int(readout_thresholds.get(dst, INT32_MAX)):
                readout_commits.append(ActiveSetCommit(conv_commit.tick, dst, readout_state[dst]))
                readout_state[dst] = 0

    conv_final = {int(k): int(v) for k, v in conv_trace.final_state.items() if int(v) != 0}
    readout_final = {dst: value for dst, value in readout_state.items() if value != 0}
    final_state = {**conv_final, **readout_final}
    conv_active = {update.dst_id for update in conv_trace.updates}
    all_updates: List[SynapticUpdate] = list(conv_trace.updates) + readout_updates
    conv_reset_writes = len(conv_trace.commits)
    readout_reset_writes = len(readout_commits)
    counters = TraceCounters(
        input_event_count=len(conv_trace.inputs),
        generated_update_count=len(all_updates),
        active_neuron_count=len(conv_active | readout_active),
        commit_count=len(readout_commits),
        state_reads=len(all_updates),
        state_writes=len(all_updates) + conv_reset_writes + readout_reset_writes,
        ddr_bytes_inner_loop=0,
        python_inner_loop_steps=0,
    )

    return SpikeMoldContractTrace(
        trace_id=trace_id,
        target=target,
        metadata={
            "primitive": "eventconv_fclif",
            "input_shape": [in_channels, in_h, in_w],
            "eventconv_output_shape": [out_channels, out_h, out_w],
            "kernel_shape": [out_channels, in_channels, kernel_h, kernel_w],
            "stride": int(stride),
            "padding": int(padding),
            "conv_state_count": int(conv_state_count),
            "readout_id_start": int(readout_id_start),
            "readout_classes": int(readout_cols),
            "internal_conv_commit_count": len(conv_trace.commits),
            "conv_commit_mode": "packet_end_active_set",
            "readout_weight_storage": "row_major_conv_state_to_class",
        },
        inputs=conv_trace.inputs,
        updates=all_updates,
        commits=readout_commits,
        final_state=final_state,
        counters=counters,
    )


# =============================================================================
# Multi-layer FC-LIF trace generation
# =============================================================================

def generate_fclif_layer_trace(
    input_ids: Sequence[int],
    weights: Mapping[Tuple[int, int], int],
    thresholds: Mapping[int, int],
    reset_values: Optional[Mapping[int, int]] = None,
    initial_state: Optional[Mapping[int, int]] = None,
    layer_name: str = "fc_lif_layer",
) -> Tuple[Sequence[SynapticUpdate], Sequence[ActiveSetCommit], MutableMapping[int, int]]:
    """Generate updates and commits for one FC-LIF layer.

    Args:
        input_ids: Source neuron IDs that fire (input spikes)
        weights: {(src_id, dst_id): weight} mapping
        thresholds: {dst_id: threshold} for firing
        reset_values: {dst_id: value} after firing (default: 0)
        initial_state: {dst_id: state} starting state
        layer_name: Layer identifier for tracing

    Returns:
        (updates, commits, final_state)
    """
    reset_values = reset_values or {}
    state: MutableMapping[int, int] = {int(k): int(v) for k, v in (initial_state or {}).items()}
    updates: List[SynapticUpdate] = []
    commits: List[ActiveSetCommit] = []

    fanout = sorted(((src, dst, weight) for (src, dst), weight in weights.items()), key=lambda item: item[:2])

    for src_id in input_ids:
        for src, dst, weight in fanout:
            if src != src_id:
                continue
            # Use tick 0 for all layer computations (trace-level timing handled externally)
            updates.append(SynapticUpdate(0, src, dst, int(weight)))
            state[dst] = _clamp_i32(state.get(dst, 0) + int(weight))
            if state[dst] >= int(thresholds.get(dst, INT32_MAX)):
                commits.append(ActiveSetCommit(0, dst, state[dst]))
                state[dst] = int(reset_values.get(dst, 0))

    return updates, commits, dict(state)


def generate_multilayer_fc_lif_trace(
    layer_configs: Sequence[Mapping[str, object]],
    input_spikes: Iterable[InputSpike],
    trace_id: str = "multilayer_fclif",
    target: str = "architecture-neutral",
) -> SpikeMoldContractTrace:
    """Generate deterministic multi-layer FC-LIF trace.

    Args:
        layer_configs: List of layer configurations, each with:
            - 'name': layer name
            - 'input_ids': list of input neuron IDs for this layer
            - 'weights': {(src_id, dst_id): weight}
            - 'thresholds': {dst_id: threshold}
            - 'reset_values': optional {dst_id: value}
        input_spikes: Input spike events
        trace_id: Trace identifier
        target: Target platform

    Returns:
        SpikeMoldContractTrace with multi-layer computation results
    """
    ordered_inputs = sorted(list(input_spikes), key=lambda event: (event.tick, event.src_id))

    # Track state across layers
    layer_states: List[MutableMapping[int, int]] = []
    all_updates: List[SynapticUpdate] = []
    all_commits: List[ActiveSetCommit] = []
    active_set: Set[int] = set()

    current_input_ids = [spike.src_id for spike in ordered_inputs]

    for layer_idx, config in enumerate(layer_configs):
        layer_name = config.get('name', f'layer_{layer_idx}')
        weights = config.get('weights', {})
        thresholds = config.get('thresholds', {})
        reset_values = config.get('reset_values', {})

        updates, commits, final_state = generate_fclif_layer_trace(
            input_ids=current_input_ids,
            weights=weights,
            thresholds=thresholds,
            reset_values=reset_values,
            initial_state=None,  # Each layer starts fresh
            layer_name=layer_name,
        )

        layer_states.append(final_state)
        all_updates.extend(updates)

        for commit in commits:
            all_commits.append(ActiveSetCommit(
                tick=ordered_inputs[0].tick if ordered_inputs else 0,
                dst_id=commit.dst_id,
                value=commit.value,
            ))
            # Next layer input is the committed neurons
            current_input_ids = [commit.dst_id for commit in commits]

        active_set.update(update.dst_id for update in updates)

    counters = TraceCounters(
        input_event_count=len(ordered_inputs),
        generated_update_count=len(all_updates),
        active_neuron_count=len(active_set),
        commit_count=len(all_commits),
        state_reads=len(all_updates),
        state_writes=len(all_updates) + len(all_commits),
        ddr_bytes_inner_loop=0,
        python_inner_loop_steps=0,
    )

    # Final state is the last layer's output (non-committed neurons)
    final_state_output = layer_states[-1] if layer_states else {}
    nonzero_state = {dst: value for dst, value in final_state_output.items() if value != 0}

    return SpikeMoldContractTrace(
        trace_id=trace_id,
        target=target,
        metadata={
            "primitive": "multilayer_fc_lif",
            "num_layers": len(layer_configs),
            "layer_names": [c.get('name', f'layer_{i}') for i, c in enumerate(layer_configs)],
            "reset_mode": "zero",
            "weight_storage": "explicit_sparse",
        },
        inputs=ordered_inputs,
        updates=all_updates,
        commits=all_commits,
        final_state=nonzero_state,
        counters=counters,
    )
