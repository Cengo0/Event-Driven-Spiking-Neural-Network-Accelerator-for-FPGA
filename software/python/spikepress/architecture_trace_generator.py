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
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple


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
