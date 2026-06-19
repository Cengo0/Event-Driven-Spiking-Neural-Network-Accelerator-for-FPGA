#!/usr/bin/env python3
"""Run frozen EventConv -> FC-LIF SpikeMold artifact on PYNQ-Z2."""

from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

import run_spikemold_pynq_dma_spike_smoke as dma_smoke  # noqa: E402
from spikepress.architecture_trace_generator import InputSpike  # noqa: E402
from spikepress.spikemold_artifact import read_spikemold_artifact, validate_eventconv_fclif_manifest  # noqa: E402
from spikepress.transport import build_eventconv_fclif_config_plan, pack_eventconv_coord32_inputs  # noqa: E402


SCHEMA = "spikemold.pynq_eventconv_fclif_result.v1"
CLAIM_BOUNDARY = "fixed_mnist_eventconv_fclif_sample_equivalence_only_no_latency_throughput_energy_or_full_accuracy"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bitstream", required=True, help="Path to .bit on the PYNQ board")
    parser.add_argument("--hwh", default="", help="Optional .hwh path for hashing only")
    parser.add_argument("--artifact", default="outputs/artifacts/mnist_eventconv_fclif_frozen.json")
    parser.add_argument("--trace", default="golden_traces/v1/mnist_eventconv_fclif_frozen_v1.json")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--ip-name", default=dma_smoke.DEFAULT_IP_NAME)
    parser.add_argument("--dma-name", default=dma_smoke.DEFAULT_DMA_NAME)
    parser.add_argument("--config-ip-name", default=dma_smoke.DEFAULT_CONFIG_IP_NAME)
    parser.add_argument("--timeout-polls", type=int, default=100000)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--time-steps", type=int, default=4096)
    return parser.parse_args()


def install_alarm(timeout_seconds: int) -> None:
    def _handler(_signum: int, _frame: object) -> None:
        raise TimeoutError(f"EventConv-FC board run exceeded {timeout_seconds} seconds")

    signal.signal(signal.SIGALRM, _handler)
    signal.alarm(timeout_seconds)


def trace_inputs_to_spikes(trace: Mapping[str, object]) -> list[InputSpike]:
    spikes = []
    for record in trace.get("inputs", []):
        if not isinstance(record, Mapping):
            raise ValueError("trace input record must be mapping")
        spikes.append(
            InputSpike(
                tick=int(record["tick"]),
                src_id=int(record["src_id"]),
                y=int(record["y"]),
                x=int(record["x"]),
                channel=int(record["channel"]),
                payload=int(record.get("payload", 1)),
            )
        )
    return spikes


def expected_commit_words(trace: Mapping[str, object]) -> list[int]:
    words = []
    for record in trace.get("commits", []):
        if not isinstance(record, Mapping):
            raise ValueError("trace commit record must be mapping")
        words.append(dma_smoke.pack_commit_value_word(int(record["dst_id"]), int(record["value"])))
    return words


def build_failure(args: argparse.Namespace, bitstream: Path, hwh: Path, error: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "evidence_level": "pynq_board_eventconv_fclif",
        "board_executed": False,
        "ok": False,
        "error": error,
        "stage": "failure",
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
        "claim_boundary": CLAIM_BOUNDARY,
    }


def main() -> int:
    args = parse_args()
    bitstream = Path(args.bitstream)
    hwh = Path(args.hwh) if args.hwh else bitstream.with_suffix(".hwh")
    artifact_path = Path(args.artifact)
    trace_path = Path(args.trace)
    output_path = Path(args.output_json)
    stage = "start"
    start = time.monotonic()
    partial: dict[str, Any] = {}

    install_alarm(args.timeout_seconds)
    try:
        artifact = read_spikemold_artifact(artifact_path)
        deploy_report = validate_eventconv_fclif_manifest(artifact.manifest)
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        config_plan = build_eventconv_fclif_config_plan(artifact.manifest)
        input_words = pack_eventconv_coord32_inputs(trace_inputs_to_spikes(trace))
        expected_words = expected_commit_words(trace)
        if not expected_words:
            raise ValueError("golden trace has no readout commits")

        try:
            from pynq import Overlay, allocate  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("PYNQ runtime import failed; run this script on PYNQ-Z2") from exc

        stage = "overlay_load"
        overlay = Overlay(str(bitstream))
        ip = dma_smoke.resolve_attr(overlay, args.ip_name)
        dma = dma_smoke.resolve_attr(overlay, args.dma_name)
        config_ip = dma_smoke.resolve_attr(overlay, args.config_ip_name)
        ip_dict = getattr(overlay, "ip_dict", {})
        available_ips = sorted(ip_dict) if isinstance(ip_dict, Mapping) else []

        send_buf = allocate(shape=(len(input_words),), dtype=np.uint32)
        recv_buf = allocate(shape=(len(expected_words),), dtype=np.uint32)
        try:
            send_buf[:] = np.asarray(input_words, dtype=np.uint32)
            recv_buf[:] = 0
            if hasattr(send_buf, "flush"):
                send_buf.flush()
            if hasattr(recv_buf, "flush"):
                recv_buf.flush()

            stage = "hls_reset"
            dma_smoke.write_common_regs(ip, ctrl_reg=dma_smoke.CTRL_RESET, config_reg=0, mode_reg=0, time_steps=1)
            reset_run = dma_smoke.start_and_poll(ip, args.timeout_polls)
            dma_smoke.write_common_regs(ip, ctrl_reg=0, config_reg=0, mode_reg=0, time_steps=1)
            release_run = dma_smoke.start_and_poll(ip, args.timeout_polls)

            stage = "rtl_config"
            config_ip.write(dma_smoke.CONFIG_OFFSETS["BACKEND_MODE"], int(config_plan["backend_mode"]))
            config_ip.write(dma_smoke.CONFIG_OFFSETS["EVENTCONV_SHAPE0"], int(config_plan["eventconv_shape0"]))
            config_ip.write(dma_smoke.CONFIG_OFFSETS["THRESHOLD"], int(config_plan["threshold"]) & 0xFFFF)
            config_ip.write(dma_smoke.CONFIG_OFFSETS["NEURON_PARAMS"], int(config_plan["neuron_params"]) & 0xFFFF)
            for write in config_plan["kernel_config_writes"]:
                dma_smoke.config_write(
                    config_ip,
                    target=dma_smoke.ROUTER_TARGET,
                    address=int(write["address"]),
                    data=int(write["data"]),
                )
            for write in config_plan["router_config_writes"]:
                dma_smoke.config_write(
                    config_ip,
                    target=dma_smoke.ROUTER_TARGET,
                    address=int(write["address"]),
                    data=int(write["data"]),
                )
            config_before = dma_smoke.config_snapshot(config_ip)

            stage = "dma_recv_transfer"
            dma.recvchannel.transfer(recv_buf)
            stage = "dma_send_transfer"
            dma.sendchannel.transfer(send_buf)
            stage = "hls_run"
            dma_smoke.write_common_regs(
                ip,
                ctrl_reg=dma_smoke.CTRL_ENABLE,
                config_reg=int(config_plan["threshold"]) & 0xFFFF,
                mode_reg=0,
                time_steps=args.time_steps,
            )
            run = dma_smoke.start_and_poll(ip, args.timeout_polls)
            dma.sendchannel.wait()
            dma.recvchannel.wait()
            if hasattr(recv_buf, "invalidate"):
                recv_buf.invalidate()

            output_words = [int(word) for word in np.asarray(recv_buf, dtype=np.uint32).tolist()]
            config_after = dma_smoke.config_snapshot(config_ip)
        finally:
            if hasattr(send_buf, "freebuffer"):
                send_buf.freebuffer()
            if hasattr(recv_buf, "freebuffer"):
                recv_buf.freebuffer()

        ok = output_words == expected_words
        result = {
            "schema": SCHEMA,
            "evidence_level": "pynq_board_eventconv_fclif",
            "board_executed": True,
            "ok": ok,
            "claim_boundary": CLAIM_BOUNDARY,
            "elapsed_host_seconds": time.monotonic() - start,
            "ip_name": args.ip_name,
            "dma_name": args.dma_name,
            "config_ip_name": args.config_ip_name,
            "available_ips": available_ips,
            "artifact": {
                "path": str(artifact_path),
                "sha256": artifact.sha256,
                "deployability": deploy_report,
            },
            "trace": {
                "path": str(trace_path),
                "trace_sha256": trace.get("hashes", {}).get("trace_sha256", ""),
            },
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
            "input_words": input_words,
            "input_words_sha256": dma_smoke.sha256_u32_words(input_words),
            "output_words": output_words,
            "output_words_sha256": dma_smoke.sha256_u32_words(output_words),
            "expected_words": expected_words,
            "expected_words_sha256": dma_smoke.sha256_u32_words(expected_words),
            "config_before": config_before,
            "config_after": config_after,
            "runs": {"reset": reset_run, "reset_release": release_run, "eventconv_fclif": run},
            "checks": {
                "output_words_match": ok,
                "backend_mode": config_after.get("backend_mode") == 2,
                "shape_supported": bool(config_after.get("eventconv_desc_status", 0) & (1 << 3)),
                "no_output_drops": config_after.get("output_br_drops") == 0,
            },
        }
    except Exception as exc:
        result = build_failure(args, bitstream, hwh, f"{stage}: {type(exc).__name__}: {exc}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "board_executed": result["board_executed"], "output": str(output_path)}, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
