#!/usr/bin/env python3
"""Run tiny EventConv AGU/state/commit smoke on PYNQ-Z2 direct RTL path."""

from __future__ import annotations

import argparse
import json
import signal
import time
from pathlib import Path
from typing import Any, Mapping

import numpy as np

import run_spikemold_pynq_dma_spike_smoke as dma_smoke


SCHEMA = "spikemold.pynq_eventconv_trace_smoke.v1"
DEFAULT_VARIANT = "tiny"

BACKEND_MODE_FLAT = 0
BACKEND_MODE_EVENTCONV = 1
EVENTCONV_SHAPE0_TINY = 0x04020303
EVENTCONV_DESC_STATUS_SHAPE_SUPPORTED = 1 << 0
EVENTCONV_DESC_STATUS_KERNEL_RUNTIME = 1 << 1

TRACE_VARIANTS = {
    "tiny": {
        "evidence_level": "pynq_board_eventconv_multi_commit_state_checksum_smoke",
        "claim_boundary": "pynq_axi_dma0_direct_rtl_tiny_eventconv_multi_commit_state_checksum_readback",
        "model": {
            "name": "batch_1c_tiny_eventconv_c4_multi_commit",
            "input_shape": [1, 3, 3],
            "kernel": [[[[1, 2], [3, 4]]]],
            "stride": 1,
            "padding": 0,
            "commit_threshold": 2,
            "semantic_limit": (
                "board readout exposes a multi-commit EventConv output packet and final "
                "state checksum; full per-state dump remains outside this smoke"
            ),
        },
        "input_spikes": [
            {"tick": 0, "src_id": 0, "x": 1, "y": 1, "channel": 0, "payload": 1},
        ],
        "expected_input_axis32": [0x01010000],
        "expected_generated_updates": 4,
        "expected_active_commit_reads": 4,
        "expected_readout_ids": [2, 1, 0],
        "expected_commit_values": [2, 3, 4],
        "expected_final_state": {"3": 1},
        "expected_state_checksum": 1,
        "expected_active_neurons_after_commit": 1,
        "state_checksum_method": "sum of final EventConv state values after threshold-2 active commit reset",
    },
    "burst-boundary": {
        "evidence_level": "pynq_board_eventconv_burst_boundary_state_checksum_smoke",
        "claim_boundary": "pynq_axi_dma0_direct_rtl_eventconv_burst_boundary_state_checksum_readback",
        "model": {
            "name": "batch_1c_eventconv_c4_burst_boundary",
            "input_shape": [1, 3, 3],
            "kernel": [[[[1, 2], [3, 4]]]],
            "stride": 1,
            "padding": 0,
            "commit_threshold": 3,
            "semantic_limit": (
                "three EventConv input events are accepted in one DMA packet; "
                "boundary coordinates skip invalid taps before active commit"
            ),
        },
        "input_spikes": [
            {"tick": 0, "src_id": 0, "x": 1, "y": 1, "channel": 0, "payload": 1},
            {"tick": 1, "src_id": 1, "x": 2, "y": 2, "channel": 0, "payload": 1},
            {"tick": 2, "src_id": 2, "x": 0, "y": 0, "channel": 0, "payload": 1},
        ],
        "expected_input_axis32": [0x01010000, 0x02020000, 0x00000000],
        "expected_generated_updates": 6,
        "expected_active_commit_reads": 4,
        "expected_readout_ids": [3, 1, 0],
        "expected_commit_values": [5, 3, 5],
        "expected_final_state": {"2": 2},
        "expected_state_checksum": 2,
        "expected_active_neurons_after_commit": 1,
        "state_checksum_method": "sum of final EventConv state values after threshold-3 burst-boundary active commit reset",
    },
}


def expected_output_words(spec: Mapping[str, Any]) -> list[int]:
    return [
        dma_smoke.pack_commit_value_word(dst_id, value)
        for dst_id, value in zip(spec["expected_readout_ids"], spec["expected_commit_values"])
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bitstream", required=True, help="Path to .bit on the PYNQ board")
    parser.add_argument("--hwh", default="", help="Optional .hwh path for hashing only")
    parser.add_argument("--ip-name", default=dma_smoke.DEFAULT_IP_NAME)
    parser.add_argument("--dma-name", default=dma_smoke.DEFAULT_DMA_NAME)
    parser.add_argument("--config-ip-name", default=dma_smoke.DEFAULT_CONFIG_IP_NAME)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--variant", default=DEFAULT_VARIANT, choices=sorted(TRACE_VARIANTS))
    parser.add_argument("--timeout-polls", type=int, default=100000)
    parser.add_argument("--timeout-seconds", type=int, default=40)
    parser.add_argument("--time-steps", type=int, default=2048)
    parser.add_argument(
        "--write-eventconv-descriptor",
        action="store_true",
        help="Write/read EventConv descriptor extension registers before running; requires a rebuilt bitstream with descriptor support.",
    )
    return parser.parse_args()


def pack_eventconv_axis32(*, x: int, y: int, channel: int) -> int:
    return ((int(x) & 0xFF) << 24) | ((int(y) & 0xFF) << 16) | ((int(channel) & 0xFF) << 8)


def pack_eventconv_kernel0(kernel: object) -> int:
    weights = kernel[0][0]  # type: ignore[index]
    flat = [int(weights[0][0]), int(weights[0][1]), int(weights[1][0]), int(weights[1][1])]  # type: ignore[index]
    value = 0
    for idx, weight in enumerate(flat):
        value |= (weight & 0xFF) << (idx * 8)
    return value


def build_failure_result(
    args: argparse.Namespace,
    spec: Mapping[str, Any],
    bitstream: Path,
    hwh: Path,
    error: str,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "variant": args.variant,
        "evidence_level": spec["evidence_level"],
        "claim_boundary": spec["claim_boundary"],
        "board_executed": False,
        "ok": False,
        "error": error,
        "ip_name": args.ip_name,
        "dma_name": args.dma_name,
        "config_ip_name": args.config_ip_name,
        "bitstream": {
            "path": str(bitstream),
            "sha256": dma_smoke.sha256_file(bitstream) if bitstream.exists() else "",
            "size_bytes": bitstream.stat().st_size if bitstream.exists() else 0,
        },
        "hwh": {
            "path": str(hwh),
            "sha256": dma_smoke.sha256_file(hwh) if hwh.exists() else "",
            "size_bytes": hwh.stat().st_size if hwh.exists() else 0,
        },
    }


def main() -> int:
    args = parse_args()
    spec = TRACE_VARIANTS[args.variant]
    model = spec["model"]
    output_words_expected = expected_output_words(spec)
    bitstream = Path(args.bitstream)
    hwh = Path(args.hwh) if args.hwh else bitstream.with_suffix(".hwh")
    output_path = Path(args.output_json)
    stage = "start"
    overlay_loaded = False
    partial: dict[str, Any] = {}
    ok = False

    dma_smoke.install_alarm(args.timeout_seconds)
    start = time.monotonic()

    try:
        try:
            from pynq import Overlay, allocate  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("PYNQ runtime import failed; run this script on PYNQ-Z2") from exc

        stage = "overlay_load"
        overlay = Overlay(str(bitstream))
        overlay_loaded = True
        ip = dma_smoke.resolve_attr(overlay, args.ip_name)
        dma = dma_smoke.resolve_attr(overlay, args.dma_name)
        config_ip = dma_smoke.resolve_attr(overlay, args.config_ip_name)
        ip_dict = getattr(overlay, "ip_dict", {})
        available_ips = sorted(ip_dict) if isinstance(ip_dict, Mapping) else []

        input_axis32 = [pack_eventconv_axis32(x=spike["x"], y=spike["y"], channel=spike["channel"]) for spike in spec["input_spikes"]]
        if input_axis32 != spec["expected_input_axis32"]:
            raise RuntimeError(f"internal EventConv AXIS32 mismatch: {input_axis32}")

        send_buf = allocate(shape=(len(input_axis32),), dtype=np.uint32)
        recv_buf = allocate(shape=(len(output_words_expected),), dtype=np.uint32)
        try:
            stage = "buffer_prepare"
            for idx, word in enumerate(input_axis32):
                send_buf[idx] = np.uint32(word)
            for idx in range(len(output_words_expected)):
                recv_buf[idx] = np.uint32(0)
            if hasattr(send_buf, "flush"):
                send_buf.flush()
            if hasattr(recv_buf, "flush"):
                recv_buf.flush()

            stage = "hls_reset"
            dma_smoke.write_common_regs(ip, ctrl_reg=dma_smoke.CTRL_RESET, config_reg=0, mode_reg=0, time_steps=1)
            reset_run = dma_smoke.start_and_poll(ip, args.timeout_polls)

            stage = "hls_reset_release"
            dma_smoke.write_common_regs(ip, ctrl_reg=0, config_reg=0, mode_reg=0, time_steps=1)
            release_run = dma_smoke.start_and_poll(ip, args.timeout_polls)

            stage = "rtl_eventconv_config"
            descriptor_expected = {
                "shape0": EVENTCONV_SHAPE0_TINY,
                "kernel0": pack_eventconv_kernel0(model["kernel"]),
            }
            if args.write_eventconv_descriptor:
                config_ip.write(dma_smoke.CONFIG_OFFSETS["EVENTCONV_SHAPE0"], descriptor_expected["shape0"])
                config_ip.write(dma_smoke.CONFIG_OFFSETS["EVENTCONV_KERNEL0"], descriptor_expected["kernel0"])
            config_ip.write(dma_smoke.CONFIG_OFFSETS["BACKEND_MODE"], BACKEND_MODE_EVENTCONV)
            config_ip.write(dma_smoke.CONFIG_OFFSETS["THRESHOLD"], model["commit_threshold"] & 0xFFFF)
            config_ip.write(dma_smoke.CONFIG_OFFSETS["NEURON_PARAMS"], 0)
            config_before = dma_smoke.config_snapshot(config_ip)

            stage = "dma_recv_transfer"
            dma.recvchannel.transfer(recv_buf)
            stage = "dma_send_transfer"
            dma.sendchannel.transfer(send_buf)
            stage = "hls_eventconv_run"
            dma_smoke.write_common_regs(
                ip,
                ctrl_reg=dma_smoke.CTRL_ENABLE,
                config_reg=model["commit_threshold"] & 0xFFFF,
                mode_reg=0,
                time_steps=args.time_steps,
            )
            trace_run = dma_smoke.start_and_poll(ip, args.timeout_polls)
            config_after_hls = dma_smoke.config_snapshot(config_ip)

            stage = "dma_send_wait"
            dma.sendchannel.wait()
            stage = "dma_recv_wait"
            dma.recvchannel.wait()
            if hasattr(recv_buf, "invalidate"):
                recv_buf.invalidate()

            stage = "decode_output"
            output_words = [int(word) for word in np.asarray(recv_buf, dtype=np.uint32).tolist()]
            output_decoded = [dma_smoke.decode_commit_value_word(word) for word in output_words]
            output_ids = [item["id"] for item in output_decoded]
            output_commit_values = [item["commit_value_u16"] for item in output_decoded]
            config_after = dma_smoke.config_snapshot(config_ip)
        finally:
            if hasattr(send_buf, "freebuffer"):
                send_buf.freebuffer()
            if hasattr(recv_buf, "freebuffer"):
                recv_buf.freebuffer()

        required_checks = {
            "reset_ap_done": bool(reset_run["ap_ctrl"] & dma_smoke.AP_DONE),
            "release_ap_done": bool(release_run["ap_ctrl"] & dma_smoke.AP_DONE),
            "trace_ap_done": bool(trace_run["ap_ctrl"] & dma_smoke.AP_DONE),
            "hls_version_matches": trace_run["version_reg"] == dma_smoke.EXPECTED_HLS_VERSION,
            "config_version_matches": config_after["version"] == dma_smoke.EXPECTED_CONFIG_VERSION,
            "backend_mode_matches": config_after["backend_mode"] == BACKEND_MODE_EVENTCONV,
            "input_count_reached": config_after["pl_busy_cycles"] >= len(input_axis32),
            "eventconv_update_count_matches": config_after["router_spike_cnt"] == spec["expected_generated_updates"],
            "active_commit_reads_match": config_after["output_drain_cycles"] == spec["expected_active_commit_reads"],
            "commit_emit_count_matches": config_after["neuron_spike_cnt"] == len(output_words_expected),
            "active_neurons_after_commit_match": ((config_after["status"] >> 1) & 0xFF) == spec["expected_active_neurons_after_commit"],
            "output_words_match": output_words == output_words_expected,
            "output_ids_match": output_ids == spec["expected_readout_ids"],
            "output_commit_values_match": output_commit_values == spec["expected_commit_values"],
            "state_checksum_matches": config_after["state_checksum"] == spec["expected_state_checksum"],
            "output_bridge_events_match": config_after["output_br_events"] == len(output_words_expected),
            "output_bridge_emits_match": config_after["output_br_emits"] == len(output_words_expected),
            "multi_commit_packet_drained": len(output_words) == len(output_words_expected),
        }
        descriptor_checks = {}
        if args.write_eventconv_descriptor:
            descriptor_checks = {
                "eventconv_shape0_matches": config_after["eventconv_shape0"] == descriptor_expected["shape0"],
                "eventconv_kernel0_matches": config_after["eventconv_kernel0"] == descriptor_expected["kernel0"],
                "eventconv_descriptor_shape_supported": (
                    config_after["eventconv_desc_status"] & EVENTCONV_DESC_STATUS_SHAPE_SUPPORTED
                ) != 0,
                "eventconv_descriptor_kernel_runtime": (
                    config_after["eventconv_desc_status"] & EVENTCONV_DESC_STATUS_KERNEL_RUNTIME
                ) != 0,
            }
            required_checks.update(descriptor_checks)
        diagnostic_checks = {
            "no_output_bridge_drops": config_after["output_br_drops"] == 0,
            "no_eventconv_invalid_dest": (config_after["status"] & 0x1) == 0,
        }
        checks = {**required_checks, **diagnostic_checks}
        ok = all(checks.values())

        elapsed = time.monotonic() - start
        result = {
            "schema": SCHEMA,
            "variant": args.variant,
            "evidence_level": spec["evidence_level"],
            "claim_boundary": spec["claim_boundary"],
            "board_executed": True,
            "ok": ok,
            "ip_name": args.ip_name,
            "dma_name": args.dma_name,
            "config_ip_name": args.config_ip_name,
            "available_ips": available_ips,
            "expected_hls_version": dma_smoke.EXPECTED_HLS_VERSION,
            "expected_config_version": dma_smoke.EXPECTED_CONFIG_VERSION,
            "elapsed_host_seconds": elapsed,
            "model": model,
            "state_reset_boundary": {
                "fresh_overlay_loaded": True,
                "eventconv_state_zeroed_by": "EventConv state_update reset/clear path",
                "hls_soft_reset_clears_eventconv_state": True,
                "state_checksum_validity": "valid after HLS reset plus backend_mode=EventConv tiny trace run",
            },
            "descriptor": {
                "write_enabled": bool(args.write_eventconv_descriptor),
                "shape0_expected": descriptor_expected["shape0"],
                "kernel0_expected": descriptor_expected["kernel0"],
                "shape0_boundary": "current RTL accepts only 3x3 input, 2x2 kernel, 4-state EventConv smoke",
                "kernel0_boundary": "packed int8 2x2 kernel register drives AGU runtime weights when descriptor-capable bitstream is used",
                "checks": descriptor_checks,
            },
            "input_spikes": spec["input_spikes"],
            "input_axis32": input_axis32,
            "input_axis32_sha256": dma_smoke.sha256_u32_words(input_axis32),
            "expected": {
                "backend_mode": BACKEND_MODE_EVENTCONV,
                "generated_updates": spec["expected_generated_updates"],
                "active_commit_reads": spec["expected_active_commit_reads"],
                "readout_ids": spec["expected_readout_ids"],
                "commit_values": spec["expected_commit_values"],
                "output_words": output_words_expected,
                "output_words_sha256": dma_smoke.sha256_u32_words(output_words_expected),
                "final_state": spec["expected_final_state"],
                "state_checksum": spec["expected_state_checksum"],
                "state_checksum_method": spec["state_checksum_method"],
            },
            "output": {
                "output_words": output_words,
                "output_words_sha256": dma_smoke.sha256_u32_words(output_words),
                "decoded": output_decoded,
                "readout_ids": output_ids,
                "commit_values": output_commit_values,
                "state_checksum": config_after["state_checksum"],
                "state_checksum_method": "board register 0x48 selected EventConv state checksum",
            },
            "runs": {
                "reset": reset_run,
                "reset_release": release_run,
                "trace": trace_run,
            },
            "config_before": config_before,
            "config_after_hls": config_after_hls,
            "config_after": config_after,
            "checks": checks,
            "required_checks": required_checks,
            "diagnostic_checks": diagnostic_checks,
            "bitstream": {
                "path": str(bitstream),
                "sha256": dma_smoke.sha256_file(bitstream) if bitstream.exists() else "",
                "size_bytes": bitstream.stat().st_size if bitstream.exists() else 0,
            },
            "hwh": {
                "path": str(hwh),
                "sha256": dma_smoke.sha256_file(hwh) if hwh.exists() else "",
                "size_bytes": hwh.stat().st_size if hwh.exists() else 0,
            },
        }
    except Exception as exc:
        result = build_failure_result(args, spec, bitstream, hwh, repr(exc))
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
