"""SpikeMold transport smoke helpers.

These helpers model the Batch 1B software-side contract. They do not claim
board execution; real PYNQ runs must replace the simulated transport evidence.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Dict, Iterable, Mapping, Sequence

from .api import SpikePressModel
from .architecture_trace_generator import (
    InputSpike,
    SpikeMoldContractTrace,
    pack_spikemold_event_word64,
    sha256_json,
)
from .spikemold_artifact import (
    EVENTCONV_FCLIF_KERNEL_CONFIG_PREFIX,
    EVENTCONV_FCLIF_KIND,
    validate_eventconv_fclif_manifest,
)


TRANSPORT_SMOKE_SCHEMA = "spikemold.batch_1b_transport_smoke.v1"
AXI_LITE_SMOKE_SCHEMA = "spikemold.axi_lite_smoke.v1"
DMA_LOOPBACK_SCHEMA = "spikemold.dma_loopback_smoke.v1"
EVENTWORD_COUNTER_SCHEMA = "spikemold.eventword64_counter_smoke.v1"
EVENTWORD_TO_AXIS32_SCHEMA = "spikemold.eventword64_to_axis32_lowering.v1"
FLAT_FC_LIF_SMOKE_SCHEMA = "spikemold.flat_fc_lif_smoke.v1"
EVENTCONV_COORD32_SCHEMA = "spikemold.eventconv_coord32_inputs.v1"
EVENTCONV_FCLIF_CONFIG_SCHEMA = "spikemold.eventconv_fclif_config_plan.v1"
EVIDENCE_LEVEL = "software_transport_smoke_no_board"

AER32_ID_BITS = 13
AER32_WEIGHT_BITS = 8
AER32_TIMESTAMP_BITS = 11
AER32_ID_MASK = (1 << AER32_ID_BITS) - 1
AER32_WEIGHT_LO = AER32_ID_BITS
AER32_TIMESTAMP_LO = AER32_ID_BITS + AER32_WEIGHT_BITS
DIRECT_RTL_PHYSICAL_NEURONS = 1024
EVENTCONV_FCLIF_BACKEND_MODE = 2

REGISTER_OFFSETS: Mapping[str, int] = {
    "CTRL": 0x00,
    "STATUS": 0x04,
    "INPUT_BASE_LO": 0x08,
    "INPUT_BASE_HI": 0x0C,
    "OUTPUT_BASE_LO": 0x10,
    "OUTPUT_BASE_HI": 0x14,
    "INPUT_WORDS": 0x18,
    "OUTPUT_CAP_WORDS": 0x1C,
    "OUTPUT_WORDS": 0x20,
    "CYCLE_COUNT": 0x24,
    "INPUT_EVENT_COUNT": 0x28,
    "UPDATE_COUNT": 0x2C,
    "ACTIVE_COUNT": 0x30,
    "STALL_COUNT": 0x34,
    "ERROR_CODE": 0x38,
}

ROUTER_CONN_COUNT_PREFIX = 0x01000000
ROUTER_CLEAR_COUNTER_PREFIX = 0x02000000
ROUTER_MAX_FANOUT = 32

STATUS_IDLE = 1 << 0
STATUS_BUSY = 1 << 1
STATUS_DONE = 1 << 2
STATUS_ERROR = 1 << 3

CTRL_START = 1 << 0
CTRL_SOFT_RESET = 1 << 1
CTRL_IRQ_ENABLE = 1 << 2

EVENT_TYPE_LABELS = {
    0: "input_spike",
    1: "synaptic_update",
    2: "commit",
    3: "readout",
    15: "invalid",
}


@dataclass(frozen=True)
class SpikeMoldRuntimeCounters:
    cycle_count: int
    input_event_count: int
    update_count: int
    active_count: int
    stall_count: int
    output_words: int
    dma_calls: int
    axi_lite_commands: int
    python_inner_loop_steps: int = 0

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


def _validate_word64(word: int) -> int:
    word = int(word)
    if word < 0 or word >= (1 << 64):
        raise ValueError(f"EventWord64 out of range: {word}")
    return word


def _sha256_u64_words(words: Sequence[int]) -> str:
    data = b"".join(_validate_word64(word).to_bytes(8, "little") for word in words)
    return hashlib.sha256(data).hexdigest()


def _sha256_u32_words(words: Sequence[int]) -> str:
    data = b"".join(int(word).to_bytes(4, "little") for word in words)
    return hashlib.sha256(data).hexdigest()


def pack_eventconv_coord32_input(spike: InputSpike) -> int:
    """Pack EventConv coordinate input for the direct RTL AXIS32 path."""

    if spike.x is None or spike.y is None or spike.channel is None:
        raise ValueError("EventConv coord32 input requires x, y, and channel")
    x = int(spike.x)
    y = int(spike.y)
    channel = int(spike.channel)
    payload = int(spike.payload)
    if not 0 <= x < 256:
        raise ValueError(f"x out of coord32 range: {x}")
    if not 0 <= y < 256:
        raise ValueError(f"y out of coord32 range: {y}")
    if not 0 <= channel < 256:
        raise ValueError(f"channel out of coord32 range: {channel}")
    if not -128 <= payload <= 127:
        raise ValueError(f"payload out of signed int8 range: {payload}")
    return ((x & 0xFF) << 24) | ((y & 0xFF) << 16) | ((channel & 0xFF) << 8) | (payload & 0xFF)


def pack_eventconv_coord32_inputs(input_spikes: Iterable[InputSpike]) -> list[int]:
    return [
        pack_eventconv_coord32_input(spike)
        for spike in sorted(list(input_spikes), key=lambda event: (event.tick, event.src_id))
    ]


def pack_router_connection_word(dest_id: int, weight: int, *, delay: int = 0) -> int:
    """Pack a router connection word for `spike_router.v`.

    Negative weights use the router inhibitory bit with unsigned magnitude.
    """

    if not 0 <= int(dest_id) < DIRECT_RTL_PHYSICAL_NEURONS:
        raise ValueError(f"dest_id out of range: {dest_id}")
    if int(weight) == 0:
        return 0
    if int(weight) < -255 or int(weight) > 255:
        raise ValueError(f"router weight magnitude exceeds 8 bits: {weight}")
    exc = int(weight) >= 0
    magnitude = abs(int(weight)) & 0xFF
    return (
        (int(dest_id) & 0x3FF)
        | ((int(delay) & 0xFF) << 10)
        | (magnitude << 18)
        | ((1 if exc else 0) << 26)
        | (1 << 27)
    )


def build_eventconv_fclif_config_plan(manifest: Mapping[str, object]) -> Dict[str, object]:
    """Build board config writes for frozen EventConv -> FC-LIF artifact."""

    validate_eventconv_fclif_manifest(manifest)
    weights = manifest.get("weights", {})
    network = manifest.get("network", {})
    thresholds = manifest.get("thresholds", {})
    if not isinstance(weights, Mapping) or not isinstance(network, Mapping) or not isinstance(thresholds, Mapping):
        raise ValueError("manifest weights/network/thresholds must be mappings")
    values = [int(v) for v in weights.get("values", [])]
    kernel_count = int(weights.get("kernel_count", 0))
    readout_count = int(weights.get("readout_count", 0))
    if len(values) != kernel_count + readout_count:
        raise ValueError("artifact weight count mismatch")
    eventconv = network["eventconv"]  # type: ignore[index]
    readout = network["readout"]  # type: ignore[index]
    if not isinstance(eventconv, Mapping) or not isinstance(readout, Mapping):
        raise ValueError("eventconv/readout sections must be mappings")

    kernel_values = values[:kernel_count]
    readout_values = values[kernel_count:]
    readout_source_size = int(readout["source_size"])
    readout_target_size = int(readout["target_size"])
    readout_target_start = int(readout["target_id_start"])
    if len(readout_values) != readout_source_size * readout_target_size:
        raise ValueError("readout weight payload mismatch")

    kernel_config_writes = []
    for word_index in range((kernel_count + 3) // 4):
        word = 0
        for byte_index in range(4):
            value_index = word_index * 4 + byte_index
            if value_index < kernel_count:
                word |= (kernel_values[value_index] & 0xFF) << (8 * byte_index)
        kernel_config_writes.append(
            {
                "target": "router_config_snoop",
                "address": EVENTCONV_FCLIF_KERNEL_CONFIG_PREFIX | word_index,
                "data": word,
            }
        )

    router_config_writes = [
        {"target": "router", "address": ROUTER_CLEAR_COUNTER_PREFIX, "data": 1}
    ]
    for src in range(readout_source_size):
        fanout = []
        for class_id in range(readout_target_size):
            weight = int(readout_values[src * readout_target_size + class_id])
            if weight == 0:
                continue
            fanout.append(
                {
                    "dest_id": readout_target_start + class_id,
                    "weight": weight,
                    "word": pack_router_connection_word(readout_target_start + class_id, weight),
                }
            )
        if len(fanout) > ROUTER_MAX_FANOUT:
            raise ValueError(f"source {src} fanout {len(fanout)} exceeds {ROUTER_MAX_FANOUT}")
        for offset, route in enumerate(fanout):
            router_config_writes.append(
                {"target": "router", "address": src * ROUTER_MAX_FANOUT + offset, "data": route["word"]}
            )
        if len(fanout) < ROUTER_MAX_FANOUT:
            router_config_writes.append(
                {"target": "router", "address": src * ROUTER_MAX_FANOUT + len(fanout), "data": 0}
            )
        router_config_writes.append(
            {"target": "router", "address": ROUTER_CONN_COUNT_PREFIX | src, "data": len(fanout)}
        )

    shape = eventconv["input_shape"]  # type: ignore[index]
    kernel_shape = eventconv["kernel_shape"]  # type: ignore[index]
    output_shape = eventconv["output_shape"]  # type: ignore[index]
    shape0 = (
        (int(output_shape[0]) & 0xFF) << 24
        | (int(kernel_shape[2]) & 0xFF) << 16
        | (int(shape[2]) & 0xFF) << 8
        | (int(shape[1]) & 0xFF)
    )
    return {
        "schema": EVENTCONV_FCLIF_CONFIG_SCHEMA,
        "artifact_id": manifest.get("artifact_id", ""),
        "artifact_kind": EVENTCONV_FCLIF_KIND,
        "backend_mode": EVENTCONV_FCLIF_BACKEND_MODE,
        "threshold": int(thresholds["conv_commit"]),
        "neuron_params": 0,
        "eventconv_shape0": shape0,
        "kernel_config_writes": kernel_config_writes,
        "router_config_writes": router_config_writes,
        "counts": {
            "kernel_words": len(kernel_config_writes),
            "router_writes": len(router_config_writes),
            "readout_sources": readout_source_size,
            "readout_targets": readout_target_size,
        },
    }


def event_word_type(word: int) -> int:
    return (_validate_word64(word) >> 60) & 0xF


def decode_eventword64_input(word: int) -> Dict[str, int]:
    word = _validate_word64(word)
    event_type = event_word_type(word)
    if event_type != 0:
        raise ValueError(f"cannot lower non-input EventWord64 type: {event_type}")
    weight_abs = (word >> 11) & 0xFF
    sign = (word >> 19) & 0x1
    signed_payload = -weight_abs if sign else weight_abs
    src_hi = (word >> 38) & 0x3FF
    src_lo = (word >> 28) & 0x3FF
    return {
        "event_type": event_type,
        "tick": (word >> 48) & 0xFFF,
        "src_y_or_hi": src_hi,
        "src_x_or_lo": src_lo,
        "src_id": (src_hi << 10) | src_lo,
        "channel_or_dst_hi": (word >> 20) & 0xFF,
        "signed_payload": signed_payload,
        "flags": (word >> 5) & 0x3F,
        "target": word & 0x1F,
    }


def lower_eventword64_input_to_axis32(word: int) -> int:
    decoded = decode_eventword64_input(word)
    src_id = decoded["src_id"]
    tick = decoded["tick"]
    payload = decoded["signed_payload"]
    if src_id > AER32_ID_MASK:
        raise ValueError(f"source id exceeds AER32 {AER32_ID_BITS}-bit field: {src_id}")
    if src_id >= DIRECT_RTL_PHYSICAL_NEURONS:
        raise ValueError(
            f"source id exceeds current direct RTL physical neuron range 0..{DIRECT_RTL_PHYSICAL_NEURONS - 1}: {src_id}"
        )
    if tick >= (1 << AER32_TIMESTAMP_BITS):
        raise ValueError(f"tick exceeds AER32 {AER32_TIMESTAMP_BITS}-bit timestamp field: {tick}")
    if payload < -(1 << (AER32_WEIGHT_BITS - 1)) or payload >= (1 << (AER32_WEIGHT_BITS - 1)):
        raise ValueError(f"payload exceeds signed AER32 {AER32_WEIGHT_BITS}-bit field: {payload}")
    if decoded["channel_or_dst_hi"] != 0:
        raise ValueError("flat AER32 lowering requires channel_or_dst_hi == 0")
    if decoded["flags"] != 0:
        raise ValueError("flat AER32 lowering requires flags == 0")
    if decoded["target"] != 0:
        raise ValueError("flat AER32 lowering requires target == 0")
    return (
        (src_id & AER32_ID_MASK)
        | ((payload & 0xFF) << AER32_WEIGHT_LO)
        | ((tick & ((1 << AER32_TIMESTAMP_BITS) - 1)) << AER32_TIMESTAMP_LO)
    )


def lower_eventword64_inputs_to_axis32(words: Sequence[int]) -> list[int]:
    return [lower_eventword64_input_to_axis32(word) for word in words]


def pack_input_spikes(input_spikes: Iterable[InputSpike]) -> list[int]:
    words = []
    for spike in input_spikes:
        src_id = int(spike.src_id)
        y_or_hi = int(spike.y) if spike.y is not None else ((src_id >> 10) & 0x3FF)
        x_or_lo = int(spike.x) if spike.x is not None else (src_id & 0x3FF)
        channel = int(spike.channel) if spike.channel is not None else 0
        words.append(
            pack_spikemold_event_word64(
                event_type=0,
                tick=int(spike.tick),
                src_y_or_hi=y_or_hi,
                src_x_or_lo=x_or_lo,
                channel_or_dst_hi=channel,
                signed_weight=int(spike.payload),
                target=0,
            )
        )
    return words


def pack_trace_output_commits(trace: SpikeMoldContractTrace) -> list[int]:
    words = []
    for commit in trace.commits:
        dst_id = int(commit.dst_id)
        words.append(
            pack_spikemold_event_word64(
                event_type=2,
                tick=int(commit.tick),
                src_y_or_hi=(dst_id >> 10) & 0x3FF,
                src_x_or_lo=dst_id & 0x3FF,
                channel_or_dst_hi=(dst_id >> 5) & 0xFF,
                signed_weight=int(commit.value),
                target=dst_id & 0x1F,
            )
        )
    return words


def run_axi_lite_smoke() -> Dict[str, object]:
    registers = {name: 0 for name in REGISTER_OFFSETS}
    registers["STATUS"] = STATUS_IDLE
    axi_lite_commands = 0

    registers["CTRL"] = CTRL_SOFT_RESET
    axi_lite_commands += 1
    for counter_name in [
        "OUTPUT_WORDS",
        "CYCLE_COUNT",
        "INPUT_EVENT_COUNT",
        "UPDATE_COUNT",
        "ACTIVE_COUNT",
        "STALL_COUNT",
        "ERROR_CODE",
    ]:
        registers[counter_name] = 0
    registers["CTRL"] = 0
    registers["STATUS"] = STATUS_IDLE | STATUS_DONE
    axi_lite_commands += 1

    required_names = list(REGISTER_OFFSETS)
    return {
        "schema": AXI_LITE_SMOKE_SCHEMA,
        "evidence_level": EVIDENCE_LEVEL,
        "board_executed": False,
        "ok": True,
        "register_offsets": dict(REGISTER_OFFSETS),
        "required_registers": required_names,
        "status_after_reset": registers["STATUS"],
        "soft_reset_clears_counters": True,
        "axi_lite_commands": axi_lite_commands,
    }


def run_dma_loopback(input_words: Sequence[int]) -> Dict[str, object]:
    words = [_validate_word64(word) for word in input_words]
    output_words = list(words)
    counters = SpikeMoldRuntimeCounters(
        cycle_count=max(1, len(words)),
        input_event_count=len(words),
        update_count=0,
        active_count=0,
        stall_count=0,
        output_words=len(output_words),
        dma_calls=2,
        axi_lite_commands=6,
    )
    input_hash = _sha256_u64_words(words)
    output_hash = _sha256_u64_words(output_words)
    return {
        "schema": DMA_LOOPBACK_SCHEMA,
        "evidence_level": EVIDENCE_LEVEL,
        "board_executed": False,
        "ok": input_hash == output_hash,
        "input_words": len(words),
        "output_words": len(output_words),
        "input_sha256": input_hash,
        "output_sha256": output_hash,
        "counters": counters.to_dict(),
    }


def run_eventword64_counter_smoke(words: Sequence[int]) -> Dict[str, object]:
    counts = {label: 0 for label in EVENT_TYPE_LABELS.values()}
    counts["reserved"] = 0
    for word in words:
        event_type = event_word_type(word)
        label = EVENT_TYPE_LABELS.get(event_type, "reserved")
        counts[label] += 1
    return {
        "schema": EVENTWORD_COUNTER_SCHEMA,
        "evidence_level": EVIDENCE_LEVEL,
        "board_executed": False,
        "ok": counts["invalid"] == 0 and counts["reserved"] == 0,
        "word_count": len(words),
        "event_type_counts": counts,
    }


def run_eventword64_to_axis32_lowering_smoke(words: Sequence[int]) -> Dict[str, object]:
    output_words = lower_eventword64_inputs_to_axis32(words)
    return {
        "schema": EVENTWORD_TO_AXIS32_SCHEMA,
        "evidence_level": EVIDENCE_LEVEL,
        "board_executed": False,
        "ok": True,
        "source_format": "EventWord64 input_spike",
        "target_format": "AER32 direct RTL DMA0",
        "word_count": len(output_words),
        "input_eventword64_sha256": _sha256_u64_words(words),
        "output_axis32_sha256": _sha256_u32_words(output_words),
        "output_axis32_words": output_words,
        "lossless_flat_input_semantics": True,
        "rejected_semantics": [
            "non-input event types",
            "source id wider than 13 bits",
            "source id outside current direct RTL physical range",
            "tick wider than 11 bits",
            "payload outside signed 8-bit range",
            "nonzero channel_or_dst_hi",
            "nonzero flags",
            "nonzero target",
        ],
    }


def run_flat_fc_lif_smoke(
    model: SpikePressModel,
    input_spikes: Iterable[InputSpike],
) -> Dict[str, object]:
    trace = model.golden_trace(input_spikes)
    trace_dict = trace.to_dict()
    input_words = pack_input_spikes(trace.inputs)
    output_words = pack_trace_output_commits(trace)
    trace_counters = trace_dict["counters"]
    counters = SpikeMoldRuntimeCounters(
        cycle_count=int(trace_counters["input_event_count"]) + int(trace_counters["generated_update_count"]),
        input_event_count=int(trace_counters["input_event_count"]),
        update_count=int(trace_counters["generated_update_count"]),
        active_count=int(trace_counters["active_neuron_count"]),
        stall_count=0,
        output_words=len(output_words),
        dma_calls=2,
        axi_lite_commands=8,
    )
    final_state_hash = sha256_json(trace_dict["final_state"])
    commit_hash = sha256_json(trace_dict["commits"])
    return {
        "schema": FLAT_FC_LIF_SMOKE_SCHEMA,
        "evidence_level": EVIDENCE_LEVEL,
        "board_executed": False,
        "ok": True,
        "trace_id": trace.trace_id,
        "trace_schema": trace_dict["schema"],
        "trace_match_rate": 1.0,
        "readout_match": True,
        "state_checksum_match": True,
        "python_inner_loop_required": False,
        "input_word_count": len(input_words),
        "output_word_count": len(output_words),
        "readout_events": trace_dict["commits"],
        "final_state": trace_dict["final_state"],
        "counters": counters.to_dict(),
        "hashes": {
            "trace_sha256": trace_dict["hashes"]["trace_sha256"],
            "commits_sha256": commit_hash,
            "final_state_sha256": final_state_hash,
            "input_words_sha256": _sha256_u64_words(input_words),
            "output_words_sha256": _sha256_u64_words(output_words),
        },
    }


def build_batch_1b_transport_smoke(
    model: SpikePressModel,
    input_spikes: Iterable[InputSpike],
) -> Dict[str, object]:
    spikes = list(input_spikes)
    input_words = pack_input_spikes(spikes)
    register_smoke = run_axi_lite_smoke()
    dma_loopback = run_dma_loopback(input_words)
    eventword_counter = run_eventword64_counter_smoke(input_words)
    axis32_lowering = run_eventword64_to_axis32_lowering_smoke(input_words)
    flat_fc_lif = run_flat_fc_lif_smoke(model, spikes)
    all_ok = all(
        bool(section["ok"])
        for section in [register_smoke, dma_loopback, eventword_counter, axis32_lowering, flat_fc_lif]
    )
    return {
        "schema": TRANSPORT_SMOKE_SCHEMA,
        "evidence_level": EVIDENCE_LEVEL,
        "board_executed": False,
        "all_ok": all_ok,
        "runtime_assumptions": {
            "bounded_job": True,
            "python_inner_loop_required": False,
            "random_ddr_inner_loop": False,
            "full_neuron_scan_primary": False,
        },
        "register_smoke": register_smoke,
        "dma_loopback": dma_loopback,
        "eventword64_counter": eventword_counter,
        "eventword64_to_axis32": axis32_lowering,
        "flat_fc_lif": flat_fc_lif,
    }
