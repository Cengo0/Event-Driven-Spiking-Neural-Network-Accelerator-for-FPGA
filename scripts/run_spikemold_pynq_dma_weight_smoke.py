#!/usr/bin/env python3
"""Run SpikeMold AXI DMA weight-stream smoke on PYNQ-Z2."""

from __future__ import annotations

import argparse
import hashlib
import json
import signal
import time
from pathlib import Path
from typing import Mapping

import numpy as np


SCHEMA = "spikemold.pynq_dma_weight_smoke.v1"
EXPECTED_VERSION = 0x20260221
DEFAULT_IP_NAME = "spikemold_top_hls_0"
DEFAULT_DMA_NAME = "axi_dma_1"

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

AP_START = 1 << 0
AP_DONE = 1 << 1

CTRL_RESET = 1 << 1
CTRL_WEIGHT_LOAD_MODE = 1 << 6
MODE_CHECKPOINT = 2


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
    parser.add_argument("--dma-name", default=DEFAULT_DMA_NAME, help="AXI DMA instance for weight stream")
    parser.add_argument("--output-json", required=True, help="Where to write board result JSON")
    parser.add_argument("--timeout-polls", type=int, default=100000)
    parser.add_argument("--timeout-seconds", type=int, default=20)
    parser.add_argument("--pre-id", type=int, default=512)
    parser.add_argument("--post-id", type=int, default=0)
    parser.add_argument("--weight", type=int, default=7)
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


def write_common_regs(ip: object, *, ctrl_reg: int, mode_reg: int, time_steps: int) -> None:
    ip.write(HLS_OFFSETS["CTRL_REG"], int(ctrl_reg))
    ip.write(HLS_OFFSETS["CONFIG_REG"], 0)
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


def pack_weight_load_word(pre_id: int, post_id: int, weight: int) -> int:
    return (int(pre_id) & 0xFFF) | ((int(post_id) & 0xFFF) << 12) | ((int(weight) & 0xFF) << 24)


def checkpoint_weight_value(word: int) -> int:
    value = (int(word) >> 20) & 0xFF
    return value - 256 if value & 0x80 else value


def install_alarm(timeout_seconds: int) -> None:
    def _handler(_signum: int, _frame: object) -> None:
        raise TimeoutError(f"board DMA smoke exceeded {timeout_seconds} seconds")

    signal.signal(signal.SIGALRM, _handler)
    signal.alarm(timeout_seconds)


def main() -> int:
    args = parse_args()
    bitstream = Path(args.bitstream)
    hwh = Path(args.hwh) if args.hwh else bitstream.with_suffix(".hwh")

    if args.weight < -128 or args.weight > 127:
        raise ValueError("--weight must fit signed int8")
    install_alarm(args.timeout_seconds)

    try:
        from pynq import Overlay, allocate  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PYNQ runtime import failed; run this script on PYNQ-Z2") from exc

    start = time.monotonic()
    overlay = Overlay(str(bitstream))
    ip = resolve_attr(overlay, args.ip_name)
    dma = resolve_attr(overlay, args.dma_name)
    ip_dict = getattr(overlay, "ip_dict", {})
    available_ips = sorted(ip_dict) if isinstance(ip_dict, Mapping) else []

    weight_word = pack_weight_load_word(args.pre_id, args.post_id, args.weight)
    send_buf = allocate(shape=(1,), dtype=np.uint32)
    recv_buf = allocate(shape=(4,), dtype=np.uint32)
    try:
        send_buf[0] = np.uint32(weight_word)
        recv_buf[:] = np.zeros((4,), dtype=np.uint32)
        if hasattr(send_buf, "flush"):
            send_buf.flush()
        if hasattr(recv_buf, "flush"):
            recv_buf.flush()

        write_common_regs(ip, ctrl_reg=CTRL_RESET, mode_reg=0, time_steps=1)
        reset_run = start_and_poll(ip, args.timeout_polls)

        dma.sendchannel.transfer(send_buf)
        write_common_regs(ip, ctrl_reg=CTRL_WEIGHT_LOAD_MODE, mode_reg=0, time_steps=1)
        load_run = start_and_poll(ip, args.timeout_polls)
        dma.sendchannel.wait()
        # Current HLS uses a nonblocking stream-empty check for weight load.
        # One extra HLS invocation after DMA completion gives the stream bridge
        # a deterministic consume opportunity without changing the bitstream.
        write_common_regs(ip, ctrl_reg=CTRL_WEIGHT_LOAD_MODE, mode_reg=0, time_steps=1)
        load_consume_run = start_and_poll(ip, args.timeout_polls)

        checkpoint_words = 4
        mode_reg = MODE_CHECKPOINT | (checkpoint_words << 16)
        dma.recvchannel.transfer(recv_buf)
        write_common_regs(ip, ctrl_reg=0, mode_reg=mode_reg, time_steps=checkpoint_words)
        checkpoint_run = start_and_poll(ip, args.timeout_polls)
        dma.recvchannel.wait()
        if hasattr(recv_buf, "invalidate"):
            recv_buf.invalidate()

        output_words = [int(word) for word in np.asarray(recv_buf, dtype=np.uint32).tolist()]
    finally:
        if hasattr(send_buf, "freebuffer"):
            send_buf.freebuffer()
        if hasattr(recv_buf, "freebuffer"):
            recv_buf.freebuffer()
        signal.alarm(0)

    elapsed = time.monotonic() - start
    expected_first_word = (int(args.weight) & 0xFF) << 20
    checks = {
        "reset_ap_done": bool(reset_run["ap_ctrl"] & AP_DONE),
        "load_ap_done": bool(load_run["ap_ctrl"] & AP_DONE),
        "checkpoint_ap_done": bool(checkpoint_run["ap_ctrl"] & AP_DONE),
        "version_matches": checkpoint_run["version_reg"] == EXPECTED_VERSION,
        "first_checkpoint_index_zero": (output_words[0] & 0xFFFFF) == 0,
        "first_checkpoint_weight_matches": checkpoint_weight_value(output_words[0]) == int(args.weight),
        "checkpoint_last_word_count": len(output_words) == checkpoint_words,
    }
    ok = all(checks.values())

    result = {
        "schema": SCHEMA,
        "evidence_level": "pynq_board_dma_weight_stream_smoke",
        "board_executed": True,
        "ok": ok,
        "ip_name": args.ip_name,
        "dma_name": args.dma_name,
        "available_ips": available_ips,
        "expected_version": EXPECTED_VERSION,
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
        "weight_load": {
            "pre_id": int(args.pre_id),
            "post_id": int(args.post_id),
            "weight": int(args.weight),
            "input_word": int(weight_word),
            "input_words_sha256": sha256_u32_words([int(weight_word)]),
        },
        "checkpoint": {
            "requested_words": checkpoint_words,
            "output_words": output_words,
            "output_words_sha256": sha256_u32_words(output_words),
            "expected_first_word": expected_first_word,
            "decoded_first_weight": checkpoint_weight_value(output_words[0]),
        },
        "runs": {
            "reset": reset_run,
            "load": load_run,
            "load_consume": load_consume_run,
            "checkpoint": checkpoint_run,
        },
        "checks": checks,
        "claim_boundary": "pynq_axi_dma1_weight_load_checkpoint_readback_only_no_neural_dataset",
    }
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
