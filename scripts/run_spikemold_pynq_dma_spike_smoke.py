#!/usr/bin/env python3
"""Run SpikeMold AXI DMA spike-stream smoke on PYNQ-Z2."""

from __future__ import annotations

import argparse
import hashlib
import json
import signal
import time
from pathlib import Path
from typing import Any, Mapping

import numpy as np


SCHEMA = "spikemold.pynq_dma_spike_smoke.v2"
CLAIM_BOUNDARY = "pynq_axi_dma0_direct_rtl_one_spike_event_to_post_spike_readback_only_no_dataset"
EXPECTED_HLS_VERSION = 0x20260221
EXPECTED_CONFIG_VERSION = 0x534D3031
DEFAULT_IP_NAME = "spikemold_top_hls_0"
DEFAULT_DMA_NAME = "axi_dma_0"
DEFAULT_CONFIG_IP_NAME = "spikemold_config_regs_0"

HLS_OFFSETS = {
    "AP_CTRL": 0x00,
    "CTRL_REG": 0x10,
    "CONFIG_REG": 0x18,
    "MODE_REG": 0x20,
    "TIME_STEPS_REG": 0x28,
    "ENCODER_CONFIG_1": 0x30,
    "ENCODER_CONFIG_2": 0x34,
    "ENCODER_CONFIG_3": 0x38,
    "STATUS_REG": 0x40,
    "SPIKE_COUNT_REG": 0x50,
    "WEIGHT_SUM_REG": 0x60,
    "VERSION_REG": 0x70,
}

CONFIG_OFFSETS = {
    "CONFIG_CTRL": 0x00,
    "CONFIG_ADDR": 0x04,
    "CONFIG_WDATA": 0x08,
    "CONFIG_RDATA": 0x0C,
    "THRESHOLD": 0x10,
    "NEURON_PARAMS": 0x14,
    "ROUTER_SPIKE_CNT": 0x18,
    "NEURON_SPIKE_CNT": 0x1C,
    "STATUS": 0x20,
    "THROUGHPUT": 0x24,
    "VERSION": 0x28,
    "SERVICE_CYCLES": 0x2C,
    "OUTPUT_BR_STATUS": 0x30,
    "OUTPUT_BR_DROPS": 0x34,
    "OUTPUT_BR_EVENTS": 0x38,
    "OUTPUT_BR_EMITS": 0x3C,
    "PL_BUSY_CYCLES": 0x40,
    "OUTPUT_DRAIN_CYCLES": 0x44,
    "STATE_CHECKSUM": 0x48,
    "BACKEND_MODE": 0x4C,
    "EVENTCONV_SHAPE0": 0x50,
    "EVENTCONV_KERNEL0": 0x54,
    "EVENTCONV_DESC_STATUS": 0x58,
}

AP_START = 1 << 0
AP_DONE = 1 << 1

CTRL_ENABLE = 1 << 0
CTRL_RESET = 1 << 1
CTRL_FIRST_SPIKE_ONLY = 1 << 7

NEURON_ID_WIDTH = 13
SPIKE_PKT_ID_MASK = (1 << NEURON_ID_WIDTH) - 1
SPIKE_PKT_WGT_LO = NEURON_ID_WIDTH
SPIKE_PKT_TS_LO = NEURON_ID_WIDTH + 8
SPIKE_PKT_TS_BITS = 11
COMMIT_VALUE_LO = NEURON_ID_WIDTH
COMMIT_VALUE_BITS = 16
COMMIT_VALUE_MASK = (1 << COMMIT_VALUE_BITS) - 1
DIRECT_RTL_PHYSICAL_NEURONS = 1024

ROUTER_TARGET = 0
ROUTER_CONN_COUNT_PREFIX = 0x01000000
ROUTER_CLEAR_COUNTER_PREFIX = 0x02000000
MAX_FANOUT = 32


def parse_int_auto(value: str) -> int:
    return int(value, 0)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_u32_words(words: list[int]) -> str:
    payload = b"".join(int(word).to_bytes(4, "little") for word in words)
    return hashlib.sha256(payload).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bitstream", required=True, help="Path to .bit on the PYNQ board")
    parser.add_argument("--hwh", default="", help="Optional .hwh path for hashing only")
    parser.add_argument("--ip-name", default=DEFAULT_IP_NAME, help="HLS IP name in overlay")
    parser.add_argument("--dma-name", default=DEFAULT_DMA_NAME, help="AXI DMA instance for spike stream")
    parser.add_argument("--config-ip-name", default=DEFAULT_CONFIG_IP_NAME)
    parser.add_argument("--output-json", required=True, help="Where to write board result JSON")
    parser.add_argument("--timeout-polls", type=int, default=100000)
    parser.add_argument("--timeout-seconds", type=int, default=20)
    parser.add_argument("--source-id", type=int, default=0)
    parser.add_argument("--dest-id", type=int, default=1)
    parser.add_argument("--input-weight", type=int, default=1)
    parser.add_argument("--timestamp", type=int, default=0)
    parser.add_argument(
        "--input-eventword64",
        type=parse_int_auto,
        default=None,
        help="Optional SpikePress EventWord64 input_spike word lowered to the direct RTL AER32 stream",
    )
    parser.add_argument("--route-weight", type=int, default=1)
    parser.add_argument("--threshold", type=int, default=1)
    parser.add_argument("--leak-rate", type=int, default=0)
    parser.add_argument("--refrac-period", type=int, default=0)
    parser.add_argument("--time-steps", type=int, default=512)
    return parser.parse_args()


def resolve_attr(overlay: object, name: str) -> object:
    direct = getattr(overlay, name, None)
    if direct is not None:
        return direct
    ip_dict = getattr(overlay, "ip_dict", {})
    if isinstance(ip_dict, Mapping) and name in ip_dict:
        return getattr(overlay, name)
    raise KeyError(f"overlay object not found: {name}; available={sorted(ip_dict)}")


def poll_done(ip: object, timeout_polls: int) -> tuple[int, int]:
    for poll in range(timeout_polls):
        ctrl = int(ip.read(HLS_OFFSETS["AP_CTRL"]))
        if ctrl & AP_DONE:
            return ctrl, poll + 1
    raise TimeoutError(f"HLS IP did not assert ap_done within {timeout_polls} polls")


def write_common_regs(
    ip: object,
    *,
    ctrl_reg: int,
    config_reg: int,
    mode_reg: int,
    time_steps: int,
) -> None:
    ip.write(HLS_OFFSETS["CTRL_REG"], int(ctrl_reg))
    ip.write(HLS_OFFSETS["CONFIG_REG"], int(config_reg))
    ip.write(HLS_OFFSETS["MODE_REG"], int(mode_reg))
    ip.write(HLS_OFFSETS["TIME_STEPS_REG"], int(time_steps))
    ip.write(HLS_OFFSETS["ENCODER_CONFIG_1"], 0)
    ip.write(HLS_OFFSETS["ENCODER_CONFIG_2"], 0)
    ip.write(HLS_OFFSETS["ENCODER_CONFIG_3"], 0)


def start_and_poll(ip: object, timeout_polls: int) -> dict[str, int]:
    ip.write(HLS_OFFSETS["AP_CTRL"], AP_START)
    ap_ctrl, polls = poll_done(ip, timeout_polls)
    return {
        "ap_ctrl": ap_ctrl,
        "polls": polls,
        "status_reg": int(ip.read(HLS_OFFSETS["STATUS_REG"])),
        "spike_count_reg": int(ip.read(HLS_OFFSETS["SPIKE_COUNT_REG"])),
        "weight_sum_reg": int(ip.read(HLS_OFFSETS["WEIGHT_SUM_REG"])),
        "version_reg": int(ip.read(HLS_OFFSETS["VERSION_REG"])),
    }


def config_write(config_ip: object, *, target: int, address: int, data: int) -> None:
    # Same addr/data is idempotent; repeat write keeps the registered AXI-lite to
    # module-ref config handoff deterministic across routed bitstream revisions.
    for _ in range(2):
        config_ip.write(CONFIG_OFFSETS["CONFIG_CTRL"], int(target) & 0x3)
        config_ip.write(CONFIG_OFFSETS["CONFIG_ADDR"], int(address) & 0xFFFFFFFF)
        config_ip.write(CONFIG_OFFSETS["CONFIG_WDATA"], int(data) & 0xFFFFFFFF)


def router_read(config_ip: object, address: int, *, settle_reads: int = 4) -> int:
    config_ip.write(CONFIG_OFFSETS["CONFIG_CTRL"], ROUTER_TARGET)
    config_ip.write(CONFIG_OFFSETS["CONFIG_ADDR"], int(address) & 0xFFFFFFFF)
    value = 0
    for _ in range(max(1, settle_reads)):
        value = int(config_ip.read(CONFIG_OFFSETS["CONFIG_RDATA"]))
    return value


def config_snapshot(config_ip: object) -> dict[str, int]:
    return {
        key.lower(): int(config_ip.read(offset))
        for key, offset in CONFIG_OFFSETS.items()
        if key
        in {
            "THRESHOLD",
            "NEURON_PARAMS",
            "ROUTER_SPIKE_CNT",
            "NEURON_SPIKE_CNT",
            "STATUS",
            "THROUGHPUT",
            "VERSION",
            "SERVICE_CYCLES",
            "OUTPUT_BR_STATUS",
            "OUTPUT_BR_DROPS",
            "OUTPUT_BR_EVENTS",
            "OUTPUT_BR_EMITS",
            "PL_BUSY_CYCLES",
            "OUTPUT_DRAIN_CYCLES",
            "STATE_CHECKSUM",
            "BACKEND_MODE",
            "EVENTCONV_SHAPE0",
            "EVENTCONV_KERNEL0",
            "EVENTCONV_DESC_STATUS",
        }
    }


def pack_router_connection(dest_id: int, weight: int, *, delay: int = 0, exc: bool = True) -> int:
    dest_bits = int(dest_id) & 0x3FF
    delay_bits = int(delay) & 0xFF
    weight_bits = int(weight) & 0xFF
    exc_bit = 1 if exc else 0
    valid_bit = 1
    return (
        dest_bits
        | (delay_bits << 10)
        | (weight_bits << 18)
        | (exc_bit << 26)
        | (valid_bit << 27)
    )


def pack_spike_word(neuron_id: int, weight: int, timestamp: int) -> int:
    return (
        (int(neuron_id) & SPIKE_PKT_ID_MASK)
        | ((int(weight) & 0xFF) << SPIKE_PKT_WGT_LO)
        | ((int(timestamp) & 0x7FF) << SPIKE_PKT_TS_LO)
    )


def pack_commit_value_word(neuron_id: int, value: int) -> int:
    return (int(neuron_id) & SPIKE_PKT_ID_MASK) | ((int(value) & COMMIT_VALUE_MASK) << COMMIT_VALUE_LO)


def validate_direct_rtl_fields(source_id: int, dest_id: int, weight: int, timestamp: int) -> None:
    if not 0 <= int(source_id) < DIRECT_RTL_PHYSICAL_NEURONS:
        raise ValueError(
            f"source id exceeds current direct RTL physical neuron range 0..{DIRECT_RTL_PHYSICAL_NEURONS - 1}: {source_id}"
        )
    if not 0 <= int(dest_id) < DIRECT_RTL_PHYSICAL_NEURONS:
        raise ValueError(
            f"dest id exceeds current direct RTL physical neuron range 0..{DIRECT_RTL_PHYSICAL_NEURONS - 1}: {dest_id}"
        )
    if int(weight) < -128 or int(weight) > 127:
        raise ValueError(f"weight exceeds signed AER32 8-bit field: {weight}")
    if not 0 <= int(timestamp) < (1 << SPIKE_PKT_TS_BITS):
        raise ValueError(f"timestamp exceeds AER32 {SPIKE_PKT_TS_BITS}-bit field: {timestamp}")


def decode_eventword64_input(word: int) -> dict[str, int]:
    word = int(word)
    event_type = (word >> 60) & 0xF
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


def lower_eventword64_input_to_axis32(word: int) -> tuple[int, dict[str, int]]:
    decoded = decode_eventword64_input(word)
    if decoded["src_id"] > SPIKE_PKT_ID_MASK:
        raise ValueError(f"source id exceeds AER32 {NEURON_ID_WIDTH}-bit field: {decoded['src_id']}")
    if decoded["src_id"] >= DIRECT_RTL_PHYSICAL_NEURONS:
        raise ValueError(
            f"source id exceeds current direct RTL physical neuron range 0..{DIRECT_RTL_PHYSICAL_NEURONS - 1}: {decoded['src_id']}"
        )
    if decoded["tick"] >= (1 << SPIKE_PKT_TS_BITS):
        raise ValueError(f"tick exceeds AER32 {SPIKE_PKT_TS_BITS}-bit timestamp field: {decoded['tick']}")
    if decoded["signed_payload"] < -128 or decoded["signed_payload"] > 127:
        raise ValueError(f"payload exceeds signed AER32 8-bit field: {decoded['signed_payload']}")
    if decoded["channel_or_dst_hi"] != 0:
        raise ValueError("flat AER32 lowering requires channel_or_dst_hi == 0")
    if decoded["flags"] != 0:
        raise ValueError("flat AER32 lowering requires flags == 0")
    if decoded["target"] != 0:
        raise ValueError("flat AER32 lowering requires target == 0")
    return (
        pack_spike_word(decoded["src_id"], decoded["signed_payload"], decoded["tick"]),
        decoded,
    )


def decode_spike_word(word: int) -> dict[str, int]:
    weight = (int(word) >> SPIKE_PKT_WGT_LO) & 0xFF
    signed_weight = weight - 256 if weight & 0x80 else weight
    return {
        "word": int(word),
        "id": int(word) & SPIKE_PKT_ID_MASK,
        "weight_u8": weight,
        "weight_i8": signed_weight,
        "timestamp": (int(word) >> SPIKE_PKT_TS_LO) & 0x7FF,
    }


def decode_commit_value_word(word: int) -> dict[str, int]:
    value = (int(word) >> COMMIT_VALUE_LO) & COMMIT_VALUE_MASK
    signed_value = value - (1 << COMMIT_VALUE_BITS) if value & (1 << (COMMIT_VALUE_BITS - 1)) else value
    return {
        "word": int(word),
        "id": int(word) & SPIKE_PKT_ID_MASK,
        "commit_value_u16": value,
        "commit_value_i16": signed_value,
        "reserved_top3": (int(word) >> (COMMIT_VALUE_LO + COMMIT_VALUE_BITS)) & 0x7,
    }


def install_alarm(timeout_seconds: int) -> None:
    def _handler(_signum: int, _frame: object) -> None:
        raise TimeoutError(f"board DMA spike smoke exceeded {timeout_seconds} seconds")

    signal.signal(signal.SIGALRM, _handler)
    signal.alarm(timeout_seconds)


def build_failure_result(args: argparse.Namespace, bitstream: Path, hwh: Path, error: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "evidence_level": "pynq_board_dma_spike_stream_smoke",
        "board_executed": False,
        "ok": False,
        "ip_name": args.ip_name,
        "dma_name": args.dma_name,
        "config_ip_name": args.config_ip_name,
        "expected_hls_version": EXPECTED_HLS_VERSION,
        "expected_config_version": EXPECTED_CONFIG_VERSION,
        "error": error,
        "bitstream": {
            "path": str(bitstream),
            "sha256": sha256_file(bitstream) if bitstream.exists() else "",
            "size_bytes": bitstream.stat().st_size if bitstream.exists() else 0,
        },
        "hwh": {
            "path": str(hwh),
            "sha256": sha256_file(hwh) if hwh.exists() else "",
            "size_bytes": hwh.stat().st_size if hwh.exists() else 0,
        },
        "claim_boundary": CLAIM_BOUNDARY,
    }


def main() -> int:
    args = parse_args()
    bitstream = Path(args.bitstream)
    hwh = Path(args.hwh) if args.hwh else bitstream.with_suffix(".hwh")
    output_path = Path(args.output_json)
    stage = "start"
    overlay_loaded = False
    partial: dict[str, Any] = {}

    install_alarm(args.timeout_seconds)
    start = time.monotonic()

    try:
        try:
            from pynq import Overlay, allocate  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("PYNQ runtime import failed; run this script on PYNQ-Z2") from exc

        stage = "overlay_load"
        overlay = Overlay(str(bitstream))
        overlay_loaded = True
        ip = resolve_attr(overlay, args.ip_name)
        dma = resolve_attr(overlay, args.dma_name)
        config_ip = resolve_attr(overlay, args.config_ip_name)
        ip_dict = getattr(overlay, "ip_dict", {})
        available_ips = sorted(ip_dict) if isinstance(ip_dict, Mapping) else []
        partial["available_ips"] = available_ips

        eventword64_lowering = None
        if args.input_eventword64 is None:
            source_id = int(args.source_id)
            input_weight = int(args.input_weight)
            timestamp = int(args.timestamp)
            input_word = pack_spike_word(source_id, input_weight, timestamp)
        else:
            input_word, eventword64_decoded = lower_eventword64_input_to_axis32(args.input_eventword64)
            source_id = int(eventword64_decoded["src_id"])
            input_weight = int(eventword64_decoded["signed_payload"])
            timestamp = int(eventword64_decoded["tick"])
            eventword64_lowering = {
                "input_eventword64": int(args.input_eventword64),
                "decoded": eventword64_decoded,
                "output_axis32": int(input_word),
                "lossless_flat_input_semantics": True,
            }
        validate_direct_rtl_fields(source_id, args.dest_id, input_weight, timestamp)
        route_word = pack_router_connection(args.dest_id, args.route_weight)
        route_addr = source_id * MAX_FANOUT
        count_addr = ROUTER_CONN_COUNT_PREFIX | (source_id & 0x3FF)
        partial["route_config"] = {
            "source_id": source_id,
            "dest_id": int(args.dest_id),
            "route_weight": int(args.route_weight),
            "threshold": int(args.threshold),
            "route_addr": route_addr,
            "route_word": route_word,
            "count_addr": count_addr,
        }
        partial["input_spike"] = {
            "source_id": source_id,
            "input_weight": input_weight,
            "timestamp": timestamp,
            "input_word": int(input_word),
            "decoded": decode_spike_word(input_word),
        }
        if eventword64_lowering is not None:
            partial["eventword64_lowering"] = eventword64_lowering

        send_buf = allocate(shape=(1,), dtype=np.uint32)
        recv_buf = allocate(shape=(1,), dtype=np.uint32)
        try:
            stage = "buffer_prepare"
            send_buf[0] = np.uint32(input_word)
            recv_buf[0] = np.uint32(0)
            if hasattr(send_buf, "flush"):
                send_buf.flush()
            if hasattr(recv_buf, "flush"):
                recv_buf.flush()

            stage = "hls_reset"
            write_common_regs(ip, ctrl_reg=CTRL_RESET, config_reg=0, mode_reg=0, time_steps=1)
            reset_run = start_and_poll(ip, args.timeout_polls)
            partial["runs"] = {"reset": reset_run}

            stage = "hls_reset_release"
            write_common_regs(ip, ctrl_reg=0, config_reg=0, mode_reg=0, time_steps=1)
            release_run = start_and_poll(ip, args.timeout_polls)
            partial["runs"]["reset_release"] = release_run

            stage = "rtl_config"
            config_ip.write(CONFIG_OFFSETS["THRESHOLD"], int(args.threshold) & 0xFFFF)
            config_ip.write(
                CONFIG_OFFSETS["NEURON_PARAMS"],
                (int(args.leak_rate) & 0xFF) | ((int(args.refrac_period) & 0xFF) << 8),
            )
            config_write(config_ip, target=ROUTER_TARGET, address=ROUTER_CLEAR_COUNTER_PREFIX, data=1)
            config_write(config_ip, target=ROUTER_TARGET, address=route_addr, data=route_word)
            config_write(config_ip, target=ROUTER_TARGET, address=route_addr + 1, data=0)
            config_write(config_ip, target=ROUTER_TARGET, address=count_addr, data=1)
            config_write(
                config_ip,
                target=ROUTER_TARGET,
                address=ROUTER_CONN_COUNT_PREFIX | ((source_id + 1) & 0x3FF),
                data=0,
            )
            config_write(
                config_ip,
                target=ROUTER_TARGET,
                address=(source_id + 1) * MAX_FANOUT,
                data=0,
            )
            route_readback = {
                "route_word": router_read(config_ip, route_addr),
                "route_terminator": router_read(config_ip, route_addr + 1),
                "source_count": router_read(config_ip, count_addr),
                "next_source_count": router_read(
                    config_ip, ROUTER_CONN_COUNT_PREFIX | ((source_id + 1) & 0x3FF)
                ),
                "next_source_route0": router_read(config_ip, (source_id + 1) * MAX_FANOUT),
            }
            partial["route_readback"] = route_readback
            config_before = config_snapshot(config_ip)
            partial["config_before"] = config_before

            stage = "dma_recv_transfer"
            dma.recvchannel.transfer(recv_buf)
            stage = "dma_send_transfer"
            dma.sendchannel.transfer(send_buf)
            hls_config_reg = int(args.threshold) & 0xFFFF
            ctrl_reg = CTRL_ENABLE | CTRL_FIRST_SPIKE_ONLY
            stage = "hls_spike_run"
            write_common_regs(
                ip,
                ctrl_reg=ctrl_reg,
                config_reg=hls_config_reg,
                mode_reg=0,
                time_steps=args.time_steps,
            )
            spike_run = start_and_poll(ip, args.timeout_polls)
            partial["runs"]["spike"] = spike_run
            partial["config_after_hls"] = config_snapshot(config_ip)
            stage = "dma_send_wait"
            dma.sendchannel.wait()
            partial["send_wait_done"] = True
            partial["config_after_send_wait"] = config_snapshot(config_ip)
            stage = "dma_recv_wait"
            dma.recvchannel.wait()
            partial["recv_wait_done"] = True
            if hasattr(recv_buf, "invalidate"):
                recv_buf.invalidate()

            stage = "decode_output"
            output_words = [int(word) for word in np.asarray(recv_buf, dtype=np.uint32).tolist()]
            decoded_output = decode_commit_value_word(output_words[0])
            config_after = config_snapshot(config_ip)
            partial["output_words"] = output_words
            partial["decoded_output"] = decoded_output
            partial["config_after"] = config_after
        finally:
            if hasattr(send_buf, "freebuffer"):
                send_buf.freebuffer()
            if hasattr(recv_buf, "freebuffer"):
                recv_buf.freebuffer()

        elapsed = time.monotonic() - start
        expected_output_word = pack_commit_value_word(args.dest_id, args.route_weight)
        required_checks = {
            "reset_ap_done": bool(reset_run["ap_ctrl"] & AP_DONE),
            "spike_ap_done": bool(spike_run["ap_ctrl"] & AP_DONE),
            "hls_version_matches": spike_run["version_reg"] == EXPECTED_HLS_VERSION,
            "config_version_matches": config_after["version"] == EXPECTED_CONFIG_VERSION,
            "axis_input_seen_nonzero": config_after["pl_busy_cycles"] >= 1,
            "axis_router_accept_nonzero": config_after["output_drain_cycles"] >= 1,
            "router_spike_count_nonzero": config_after["router_spike_cnt"] >= 1,
            "neuron_spike_count_nonzero": config_after["neuron_spike_cnt"] >= 1,
            "output_id_matches": decoded_output["id"] == int(args.dest_id),
            "output_commit_value_matches": decoded_output["commit_value_u16"] == (int(args.route_weight) & COMMIT_VALUE_MASK),
            "output_word_matches": output_words == [expected_output_word],
            "output_reserved_top3_zero": decoded_output["reserved_top3"] == 0,
        }
        diagnostic_checks = {
            "output_event_count_nonzero": config_after["output_br_events"] >= 1,
            "output_emit_count_nonzero": config_after["output_br_emits"] >= 1,
        }
        checks = {**required_checks, **diagnostic_checks}
        ok = all(required_checks.values())

        result: dict[str, Any] = {
            "schema": SCHEMA,
            "evidence_level": "pynq_board_dma_spike_stream_smoke",
            "board_executed": True,
            "ok": ok,
            "ip_name": args.ip_name,
            "dma_name": args.dma_name,
            "config_ip_name": args.config_ip_name,
            "available_ips": available_ips,
            "expected_hls_version": EXPECTED_HLS_VERSION,
            "expected_config_version": EXPECTED_CONFIG_VERSION,
            "elapsed_host_seconds": elapsed,
            "bitstream": {
                "path": str(bitstream),
                "sha256": sha256_file(bitstream) if bitstream.exists() else "",
                "size_bytes": bitstream.stat().st_size if bitstream.exists() else 0,
            },
            "hwh": {
                "path": str(hwh),
                "sha256": sha256_file(hwh) if hwh.exists() else "",
                "size_bytes": hwh.stat().st_size if hwh.exists() else 0,
            },
            "route_config": {
                "source_id": source_id,
                "dest_id": int(args.dest_id),
                "route_weight": int(args.route_weight),
                "threshold": int(args.threshold),
                "leak_rate": int(args.leak_rate),
                "refrac_period": int(args.refrac_period),
                "route_addr": route_addr,
                "route_word": route_word,
                "count_addr": count_addr,
            },
            "route_readback": route_readback,
            "input_spike": {
                "source_id": source_id,
                "input_weight": input_weight,
                "timestamp": timestamp,
                "input_word": int(input_word),
                "input_words_sha256": sha256_u32_words([int(input_word)]),
                "decoded": decode_spike_word(input_word),
            },
            "eventword64_lowering": eventword64_lowering,
            "output_spike": {
                "requested_words": 1,
                "output_words": output_words,
                "output_words_sha256": sha256_u32_words(output_words),
                "decoded": decoded_output,
                "expected_words": [expected_output_word],
                "expected_words_sha256": sha256_u32_words([expected_output_word]),
            },
            "runs": {
                "reset": reset_run,
                "reset_release": release_run,
                "spike": spike_run,
            },
            "config_before": config_before,
            "config_after": config_after,
            "checks": checks,
            "required_checks": required_checks,
            "diagnostic_checks": diagnostic_checks,
            "claim_boundary": CLAIM_BOUNDARY,
        }
    except Exception as exc:
        result = build_failure_result(args, bitstream, hwh, repr(exc))
        result["board_executed"] = overlay_loaded
        result["failure_stage"] = stage
        result["partial"] = partial
        ok = False
    finally:
        signal.alarm(0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
