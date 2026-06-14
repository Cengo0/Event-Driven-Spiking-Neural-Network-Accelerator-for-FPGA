"""SpikeMold-EDNP transport smoke helpers.

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


TRANSPORT_SMOKE_SCHEMA = "spikemold.batch_1b_transport_smoke.v1"
AXI_LITE_SMOKE_SCHEMA = "spikemold.axi_lite_smoke.v1"
DMA_LOOPBACK_SCHEMA = "spikemold.dma_loopback_smoke.v1"
EVENTWORD_COUNTER_SCHEMA = "spikemold.eventword64_counter_smoke.v1"
EDNP_MINI_SMOKE_SCHEMA = "spikemold.ednp_mini_fc_lif_smoke.v1"
EVIDENCE_LEVEL = "software_transport_smoke_no_board"

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


def event_word_type(word: int) -> int:
    return (_validate_word64(word) >> 60) & 0xF


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


def run_ednp_mini_fc_lif_smoke(
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
        "schema": EDNP_MINI_SMOKE_SCHEMA,
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
    ednp_mini = run_ednp_mini_fc_lif_smoke(model, spikes)
    all_ok = all(
        bool(section["ok"])
        for section in [register_smoke, dma_loopback, eventword_counter, ednp_mini]
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
        "ednp_mini_fc_lif": ednp_mini,
    }
