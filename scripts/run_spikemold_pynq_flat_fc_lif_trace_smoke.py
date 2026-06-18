#!/usr/bin/env python3
"""Run tiny flat FC-LIF trace/readout smoke on PYNQ-Z2 direct RTL path."""

from __future__ import annotations

import argparse
import hashlib
import json
import signal
import time
from pathlib import Path
from typing import Any, Mapping

import numpy as np

import run_spikemold_pynq_dma_spike_smoke as dma_smoke


SCHEMA = "spikemold.pynq_flat_fc_lif_trace_smoke.v1"
EVIDENCE_LEVEL = "pynq_board_flat_fc_lif_commit_value_state_checksum_smoke"
CLAIM_BOUNDARY = "pynq_axi_dma0_direct_rtl_tiny_flat_fc_lif_commit_value_state_checksum_readback"

MODEL = {
    "name": "batch_1b_tiny_fc_lif",
    "weights": [[3, 1], [2, 0]],
    "thresholds": [5, 9],
    "global_threshold_used": 5,
    "semantic_limit": "board readout exposes output spike id, commit value, and final membrane checksum; full per-neuron state dump remains outside this smoke",
}

INPUT_SPIKES = [
    {"tick": 0, "src_id": 0, "payload": 1},
    {"tick": 1, "src_id": 1, "payload": 1},
    {"tick": 2, "src_id": 0, "payload": 1},
]

ROUTES = {
    0: [
        {"dest_id": 2, "weight": 3},
        {"dest_id": 3, "weight": 1},
    ],
    1: [
        {"dest_id": 2, "weight": 2},
    ],
}

EXPECTED_READOUT_IDS = [2]
EXPECTED_COMMIT_VALUES = [5]
EXPECTED_OUTPUT_WORDS = [dma_smoke.pack_commit_value_word(2, 5)]
EXPECTED_GENERATED_UPDATES = 5
EXPECTED_FINAL_STATE = {"2": 3, "3": 2}
EXPECTED_STATE_CHECKSUM = 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bitstream", required=True, help="Path to .bit on the PYNQ board")
    parser.add_argument("--hwh", default="", help="Optional .hwh path for hashing only")
    parser.add_argument("--ip-name", default=dma_smoke.DEFAULT_IP_NAME)
    parser.add_argument("--dma-name", default=dma_smoke.DEFAULT_DMA_NAME)
    parser.add_argument("--config-ip-name", default=dma_smoke.DEFAULT_CONFIG_IP_NAME)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--timeout-polls", type=int, default=100000)
    parser.add_argument("--timeout-seconds", type=int, default=40)
    parser.add_argument("--time-steps", type=int, default=2048)
    return parser.parse_args()


def pack_eventword64_input(*, tick: int, src_id: int, payload: int) -> int:
    sign = 1 if int(payload) < 0 else 0
    weight_abs = abs(int(payload)) & 0xFF
    src_hi = (int(src_id) >> 10) & 0x3FF
    src_lo = int(src_id) & 0x3FF
    return (
        ((int(tick) & 0xFFF) << 48)
        | (src_hi << 38)
        | (src_lo << 28)
        | (sign << 19)
        | (weight_abs << 11)
    )


def sha256_u64_words(words: list[int]) -> str:
    payload = b"".join(int(word).to_bytes(8, "little") for word in words)
    return hashlib.sha256(payload).hexdigest()


def config_source_routes(config_ip: object, source_id: int, routes: list[dict[str, int]]) -> dict[str, object]:
    route_base = int(source_id) * dma_smoke.MAX_FANOUT
    count_addr = dma_smoke.ROUTER_CONN_COUNT_PREFIX | (int(source_id) & 0x3FF)
    for idx, route in enumerate(routes):
        word = dma_smoke.pack_router_connection(int(route["dest_id"]), int(route["weight"]))
        dma_smoke.config_write(config_ip, target=dma_smoke.ROUTER_TARGET, address=route_base + idx, data=word)
    dma_smoke.config_write(
        config_ip,
        target=dma_smoke.ROUTER_TARGET,
        address=route_base + len(routes),
        data=0,
    )
    dma_smoke.config_write(config_ip, target=dma_smoke.ROUTER_TARGET, address=count_addr, data=len(routes))
    return {
        "source_id": int(source_id),
        "route_base": route_base,
        "count_addr": count_addr,
        "count": len(routes),
        "routes": [
            {
                "dest_id": int(route["dest_id"]),
                "weight": int(route["weight"]),
                "route_addr": route_base + idx,
                "route_word": dma_smoke.pack_router_connection(int(route["dest_id"]), int(route["weight"])),
            }
            for idx, route in enumerate(routes)
        ],
    }


def read_source_routes(config_ip: object, source_id: int, count: int) -> dict[str, object]:
    route_base = int(source_id) * dma_smoke.MAX_FANOUT
    count_addr = dma_smoke.ROUTER_CONN_COUNT_PREFIX | (int(source_id) & 0x3FF)
    return {
        "source_id": int(source_id),
        "source_count": dma_smoke.router_read(config_ip, count_addr),
        "route_words": [dma_smoke.router_read(config_ip, route_base + idx) for idx in range(count)],
        "terminator": dma_smoke.router_read(config_ip, route_base + count),
    }


def build_failure_result(args: argparse.Namespace, bitstream: Path, hwh: Path, error: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "evidence_level": EVIDENCE_LEVEL,
        "claim_boundary": CLAIM_BOUNDARY,
        "board_executed": False,
        "ok": False,
        "error": error,
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

        input_eventword64 = [pack_eventword64_input(**spike) for spike in INPUT_SPIKES]
        lowering = [dma_smoke.lower_eventword64_input_to_axis32(word) for word in input_eventword64]
        input_axis32 = [int(item[0]) for item in lowering]
        lowering_records = [
            {
                "input_eventword64": int(word),
                "decoded": decoded,
                "output_axis32": int(axis32),
                "lossless_flat_input_semantics": True,
            }
            for word, (axis32, decoded) in zip(input_eventword64, lowering)
        ]

        send_buf = allocate(shape=(len(input_axis32),), dtype=np.uint32)
        recv_buf = allocate(shape=(len(EXPECTED_OUTPUT_WORDS),), dtype=np.uint32)
        try:
            stage = "buffer_prepare"
            for idx, word in enumerate(input_axis32):
                send_buf[idx] = np.uint32(word)
            for idx in range(len(EXPECTED_OUTPUT_WORDS)):
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

            stage = "rtl_config"
            config_ip.write(dma_smoke.CONFIG_OFFSETS["THRESHOLD"], MODEL["global_threshold_used"] & 0xFFFF)
            config_ip.write(dma_smoke.CONFIG_OFFSETS["NEURON_PARAMS"], 0)
            dma_smoke.config_write(
                config_ip,
                target=dma_smoke.ROUTER_TARGET,
                address=dma_smoke.ROUTER_CLEAR_COUNTER_PREFIX,
                data=1,
            )
            route_config = {
                source_id: config_source_routes(config_ip, source_id, routes)
                for source_id, routes in ROUTES.items()
            }
            dma_smoke.config_write(
                config_ip,
                target=dma_smoke.ROUTER_TARGET,
                address=dma_smoke.ROUTER_CONN_COUNT_PREFIX | 2,
                data=0,
            )
            route_readback = {
                source_id: read_source_routes(config_ip, source_id, len(routes))
                for source_id, routes in ROUTES.items()
            }
            route_readback[2] = read_source_routes(config_ip, 2, 0)
            config_before = dma_smoke.config_snapshot(config_ip)

            stage = "dma_recv_transfer"
            dma.recvchannel.transfer(recv_buf)
            stage = "dma_send_transfer"
            dma.sendchannel.transfer(send_buf)
            stage = "hls_trace_run"
            dma_smoke.write_common_regs(
                ip,
                ctrl_reg=dma_smoke.CTRL_ENABLE | dma_smoke.CTRL_FIRST_SPIKE_ONLY,
                config_reg=MODEL["global_threshold_used"] & 0xFFFF,
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
            "input_count_reached": config_after["pl_busy_cycles"] >= len(input_axis32),
            "router_accept_count_reached": config_after["output_drain_cycles"] >= len(input_axis32),
            "router_update_count_reached": config_after["router_spike_cnt"] >= EXPECTED_GENERATED_UPDATES,
            "neuron_spike_count_matches": config_after["neuron_spike_cnt"] == len(EXPECTED_OUTPUT_WORDS),
            "output_words_match": output_words == EXPECTED_OUTPUT_WORDS,
            "output_ids_match": output_ids == EXPECTED_READOUT_IDS,
            "output_commit_values_match": output_commit_values == EXPECTED_COMMIT_VALUES,
            "state_checksum_matches": config_after["state_checksum"] == EXPECTED_STATE_CHECKSUM,
            "output_bridge_events_match": config_after["output_br_events"] == len(EXPECTED_OUTPUT_WORDS),
            "output_bridge_emits_match": config_after["output_br_emits"] == len(EXPECTED_OUTPUT_WORDS),
        }
        diagnostic_checks = {
            "no_output_bridge_drops": config_after["output_br_drops"] == 0,
            "source0_count_matches": route_readback[0]["source_count"] == len(ROUTES[0]),
            "source1_count_matches": route_readback[1]["source_count"] == len(ROUTES[1]),
            "source2_count_zero": route_readback[2]["source_count"] == 0,
        }
        checks = {**required_checks, **diagnostic_checks}
        ok = all(checks.values())

        elapsed = time.monotonic() - start
        result = {
            "schema": SCHEMA,
            "evidence_level": EVIDENCE_LEVEL,
            "claim_boundary": CLAIM_BOUNDARY,
            "board_executed": True,
            "ok": ok,
            "ip_name": args.ip_name,
            "dma_name": args.dma_name,
            "config_ip_name": args.config_ip_name,
            "available_ips": available_ips,
            "expected_hls_version": dma_smoke.EXPECTED_HLS_VERSION,
            "expected_config_version": dma_smoke.EXPECTED_CONFIG_VERSION,
            "elapsed_host_seconds": elapsed,
            "model": MODEL,
            "state_reset_boundary": {
                "fresh_overlay_loaded": True,
                "membrane_state_zeroed_by": "bitstream initialization on Overlay load",
                "hls_soft_reset_clears_membrane_bram": False,
                "state_checksum_valid_after_soft_reset": False,
                "state_checksum_validity": (
                    "valid for fresh overlay zero-init traces and controlled membrane "
                    "config writes; HLS soft reset alone does not clear membrane BRAM"
                ),
            },
            "input_spikes": INPUT_SPIKES,
            "input_eventword64": input_eventword64,
            "input_axis32": input_axis32,
            "input_eventword64_sha256": sha256_u64_words(input_eventword64),
            "input_axis32_sha256": dma_smoke.sha256_u32_words(input_axis32),
            "eventword64_lowering": lowering_records,
            "route_config": route_config,
            "route_readback": route_readback,
            "expected": {
                "generated_updates": EXPECTED_GENERATED_UPDATES,
                "readout_ids": EXPECTED_READOUT_IDS,
                "commit_values": EXPECTED_COMMIT_VALUES,
                "output_words": EXPECTED_OUTPUT_WORDS,
                "output_words_sha256": dma_smoke.sha256_u32_words(EXPECTED_OUTPUT_WORDS),
                "final_state": EXPECTED_FINAL_STATE,
                "state_checksum": EXPECTED_STATE_CHECKSUM,
                "state_checksum_method": "sum of final membrane values for the zero-initial tiny trace",
            },
            "output": {
                "output_words": output_words,
                "output_words_sha256": dma_smoke.sha256_u32_words(output_words),
                "decoded": output_decoded,
                "readout_ids": output_ids,
                "commit_values": output_commit_values,
                "state_checksum": config_after["state_checksum"],
                "state_checksum_method": "board register 0x48 running membrane-state checksum",
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
