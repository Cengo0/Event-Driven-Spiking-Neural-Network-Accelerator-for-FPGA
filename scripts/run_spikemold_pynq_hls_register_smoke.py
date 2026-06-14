#!/usr/bin/env python3
"""Run a minimal SpikeMold HLS register smoke on PYNQ-Z2."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Mapping


SCHEMA = "spikemold.pynq_hls_register_smoke.v1"
EXPECTED_VERSION = 0x20260221
DEFAULT_IP_NAME = "spikemold_top_hls_0"

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
AP_IDLE = 1 << 2
AP_READY = 1 << 3


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bitstream", required=True, help="Path to .bit on the PYNQ board")
    parser.add_argument("--hwh", default="", help="Optional .hwh path for hashing only")
    parser.add_argument("--ip-name", default=DEFAULT_IP_NAME, help="HLS IP name in overlay")
    parser.add_argument("--output-json", required=True, help="Where to write board result JSON")
    parser.add_argument("--timeout-polls", type=int, default=100000)
    return parser.parse_args()


def resolve_ip(overlay: object, ip_name: str) -> object:
    direct = getattr(overlay, ip_name, None)
    if direct is not None:
        return direct
    ip_dict = getattr(overlay, "ip_dict", {})
    if isinstance(ip_dict, Mapping) and ip_name in ip_dict:
        return getattr(overlay, ip_name)
    raise KeyError(f"IP not found in overlay: {ip_name}; available={sorted(ip_dict)}")


def poll_done(ip: object, timeout_polls: int) -> tuple[int, int]:
    for poll in range(timeout_polls):
        ctrl = int(ip.read(HLS_OFFSETS["AP_CTRL"]))
        if ctrl & AP_DONE:
            return ctrl, poll + 1
    raise TimeoutError(f"HLS IP did not assert ap_done within {timeout_polls} polls")


def run_hls_once(ip: object, *, ctrl_reg: int, timeout_polls: int) -> dict[str, int]:
    ip.write(HLS_OFFSETS["CTRL_REG"], int(ctrl_reg))
    ip.write(HLS_OFFSETS["CONFIG_REG"], 0)
    ip.write(HLS_OFFSETS["MODE_REG"], 0)
    ip.write(HLS_OFFSETS["TIME_STEPS_REG"], 1)
    ip.write(HLS_OFFSETS["ENCODER_CONFIG_1"], 0)
    ip.write(HLS_OFFSETS["ENCODER_CONFIG_2"], 0)
    ip.write(HLS_OFFSETS["ENCODER_CONFIG_3"], 0)
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


def main() -> int:
    args = parse_args()
    bitstream = Path(args.bitstream)
    hwh = Path(args.hwh) if args.hwh else bitstream.with_suffix(".hwh")

    try:
        from pynq import Overlay  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PYNQ Overlay import failed; run this script on PYNQ-Z2") from exc

    start = time.monotonic()
    overlay = Overlay(str(bitstream))
    ip = resolve_ip(overlay, args.ip_name)
    ip_dict = getattr(overlay, "ip_dict", {})
    available_ips = sorted(ip_dict) if isinstance(ip_dict, Mapping) else []

    reset_run = run_hls_once(ip, ctrl_reg=0x2, timeout_polls=args.timeout_polls)
    normal_run = run_hls_once(ip, ctrl_reg=0x0, timeout_polls=args.timeout_polls)
    elapsed = time.monotonic() - start

    version_ok = normal_run["version_reg"] == EXPECTED_VERSION
    ap_done_ok = bool(normal_run["ap_ctrl"] & AP_DONE)
    ok = bool(version_ok and ap_done_ok)

    result = {
        "schema": SCHEMA,
        "evidence_level": "pynq_board_hls_register_smoke",
        "board_executed": True,
        "ok": ok,
        "ip_name": args.ip_name,
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
        "runs": {
            "reset": reset_run,
            "normal": normal_run,
        },
        "checks": {
            "ap_done": ap_done_ok,
            "version_matches": version_ok,
        },
        "claim_boundary": "pynq_overlay_load_hls_register_ap_done_version_only_no_dma_no_dataset",
    }
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
