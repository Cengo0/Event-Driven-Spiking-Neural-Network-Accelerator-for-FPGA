#!/usr/bin/env python3
"""Run G15 scaling sweep with prebuilt deployment variants and optional HW reports."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Run scaling sweep over deployment variants. "
            "Each variant is label:path_to_npz."
        )
    )
    p.add_argument("--inference-script", required=True, help="Path to fpga_10class_inference.py")
    p.add_argument("--data-dir", required=True, help="Board data directory (bit/hwh root)")
    p.add_argument(
        "--variants",
        required=True,
        help=(
            "Comma-separated variant definitions: "
            "label:path_to_deployment_npz,label2:path2"
        ),
    )
    p.add_argument("--n", type=int, default=10000, help="Number of images")
    p.add_argument("--packet-id-width", type=int, default=13)
    p.add_argument("--pl-clock-hz", type=float, default=80_000_000.0)
    p.add_argument("--out-dir", required=True, help="Output directory")
    p.add_argument("--report-map-json", default=None, help="Optional report mapping JSON")
    p.add_argument("--python", default="python3", help="Python executable")
    p.add_argument("--sudo", action="store_true", help="Prepend sudo to inference command")
    p.add_argument("--max-retries", type=int, default=2, help="Retries per failed variant run")
    p.add_argument("--resume", action="store_true", help="Skip variants with complete existing result json")
    p.add_argument(
        "--program-every-variant",
        action="store_true",
        help="Force bitstream reprogramming for each variant (default: only first variant programs FPGA)",
    )
    p.add_argument("--dry-run", action="store_true", help="Print commands only")
    return p.parse_args()


def _to_int(txt: str) -> int:
    return int(txt.replace(",", ""))


def _read_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _parse_variants(raw: str) -> List[Tuple[str, Path]]:
    out: List[Tuple[str, Path]] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            raise SystemExit(f"Invalid variant '{item}' (expected label:path)")
        label, path = item.split(":", 1)
        out.append((label.strip(), Path(path.strip())))
    if not out:
        raise SystemExit("No valid variants parsed from --variants")
    return out


def _parse_utilization_report(path: Path) -> Dict[str, Optional[float]]:
    text = path.read_text(encoding="utf-8", errors="ignore")

    def row_val(name: str) -> Tuple[Optional[int], Optional[int], Optional[float]]:
        pat = re.compile(
            rf"\|\s*{re.escape(name)}\s*\|\s*([\d,]+)\s*\|.*?\|\s*([\d,]+)\s*\|\s*([\d.]+)\s*\|"
        )
        m = pat.search(text)
        if not m:
            return None, None, None
        return _to_int(m.group(1)), _to_int(m.group(2)), float(m.group(3))

    lut_used, lut_avail, lut_util = row_val("Slice LUTs")
    ff_used, ff_avail, ff_util = row_val("Slice Registers")
    bram_used, bram_avail, bram_util = row_val("Block RAM Tile")
    dsp_used, dsp_avail, dsp_util = row_val("DSPs")

    return {
        "lut_used": lut_used,
        "lut_avail": lut_avail,
        "lut_util_pct": lut_util,
        "ff_used": ff_used,
        "ff_avail": ff_avail,
        "ff_util_pct": ff_util,
        "bram_used": bram_used,
        "bram_avail": bram_avail,
        "bram_util_pct": bram_util,
        "dsp_used": dsp_used,
        "dsp_avail": dsp_avail,
        "dsp_util_pct": dsp_util,
    }


def _parse_timing_report(path: Path) -> Dict[str, Optional[float]]:
    text = path.read_text(encoding="utf-8", errors="ignore")

    row = re.search(
        r"Design Timing Summary.*?\n\s*[-\s]+\n\s*([-\d.]+)\s+([-\d.]+)\s+\d+\s+\d+\s+([-\d.]+)\s+([-\d.]+)",
        text,
        flags=re.S,
    )
    wns = float(row.group(1)) if row else None
    tns = float(row.group(2)) if row else None
    whs = float(row.group(3)) if row else None
    ths = float(row.group(4)) if row else None

    clk = re.search(
        r"clk_fpga_0\s+\{[^}]+\}\s+([-\d.]+)\s+([-\d.]+)",
        text,
    )
    period_ns = float(clk.group(1)) if clk else None
    freq_mhz = float(clk.group(2)) if clk else None

    return {
        "wns_ns": wns,
        "tns_ns": tns,
        "whs_ns": whs,
        "ths_ns": ths,
        "clock_period_ns": period_ns,
        "clock_freq_mhz": freq_mhz,
    }


def _parse_power_report(path: Path) -> Dict[str, Optional[float]]:
    text = path.read_text(encoding="utf-8", errors="ignore")

    def scalar(label: str) -> Optional[float]:
        m = re.search(rf"\|\s*{re.escape(label)}\s*\|\s*([-\d.]+)", text)
        return float(m.group(1)) if m else None

    return {
        "total_onchip_w": scalar("Total On-Chip Power (W)"),
        "dynamic_w": scalar("Dynamic (W)"),
        "static_w": scalar("Device Static (W)"),
    }


def _parse_report_map(path: Optional[str]) -> Dict[str, Dict[str, str]]:
    if not path:
        return {}
    data = _read_json(Path(path))
    if not isinstance(data, dict):
        raise SystemExit("--report-map-json must be an object")
    return data


def _is_complete_result(result_json: Path, n_expected: int) -> bool:
    if not result_json.exists():
        return False
    try:
        d = _read_json(result_json)
    except Exception:
        return False
    n_images = d.get("n_images", None)
    rows = d.get("results", None)
    if n_images is None or rows is None:
        return False
    try:
        return int(n_images) == int(n_expected) and len(rows) == int(n_expected)
    except Exception:
        return False


def _infer_metrics(path: Path) -> Dict[str, Optional[float]]:
    d = _read_json(path)
    strict_failures = d.get("strict_failures", [])
    n_images = int(d.get("n_images", 0) or 0)
    strict_pass_count = int(d.get("strict_pass_count", max(n_images - len(strict_failures), 0)))
    strict_identical_pass = bool(
        d.get("strict_identical_pass", bool(d.get("strict_identical", False)) and len(strict_failures) == 0)
    )
    return {
        "hw_acc_ttfs": float(d.get("hw_acc_ttfs", 0.0)),
        "sw_acc_ttfs": float(d.get("sw_acc_ttfs", 0.0)),
        "sw_acc_count": float(d.get("sw_acc_count", 0.0)),
        "ms_per_image": float(d.get("ms_per_image", 0.0)),
        "strict_identical": bool(d.get("strict_identical", False)),
        "strict_identical_pass": strict_identical_pass,
        "strict_failures_n": int(len(strict_failures)),
        "strict_pass_count": strict_pass_count,
        "strict_pass_rate": (
            float(d.get("strict_pass_rate", strict_pass_count / n_images))
            if n_images > 0 else None
        ),
        "pl_latency_cycles_mean": d.get("pl_latency_cycles_mean"),
        "pl_service_cycles_mean": d.get("pl_service_cycles_mean"),
        "pl_latency_ms_mean": d.get("pl_latency_ms_mean"),
        "pl_service_ms_mean": d.get("pl_service_ms_mean"),
        "pl_first_spike_tput_img_s": d.get("pl_first_spike_tput_img_s"),
        "pl_service_tput_img_s": d.get("pl_service_tput_img_s"),
    }


def _to_md(rows: List[Dict[str, object]]) -> str:
    def fmt(v: object, nd: int = 2) -> str:
        if v is None:
            return "N/A"
        return f"{float(v):.{nd}f}"

    lines = [
        "# G15 Scaling Sweep Summary",
        "",
        "| Variant | Neurons | HW TTFS | Strict pass | strict_failures | PL service cyc | PL service us | PL throughput (img/s) | LUT% | BRAM% | DSP% | WNS (ns) | Dyn Power (W) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        svc_us = None
        if r.get("pl_service_ms_mean") is not None:
            svc_us = float(r["pl_service_ms_mean"]) * 1000.0
        lines.append(
            f"| {r['variant']} | {r['n_neurons']} | {float(r['hw_acc_ttfs']):.4f} | "
            f"{'Yes' if r.get('strict_identical_pass') else 'No'} | {r['strict_failures_n']} | "
            f"{r.get('pl_service_cycles_mean')} | "
            f"{(f'{svc_us:.4f}' if svc_us is not None else 'N/A')} | "
            f"{fmt(r.get('pl_service_tput_img_s'), 2)} | "
            f"{fmt(r.get('lut_util_pct'), 2)} | "
            f"{fmt(r.get('bram_util_pct'), 2)} | "
            f"{fmt(r.get('dsp_util_pct'), 2)} | "
            f"{fmt(r.get('wns_ns'), 3)} | "
            f"{fmt(r.get('dynamic_w'), 3)} |"
        )
    lines.append("")
    return "\n".join(lines)


def _run_variant(
    args: argparse.Namespace,
    deploy_path: Path,
    out_json: Path,
    is_first_variant: bool,
) -> None:
    cmd: List[str] = []
    if args.sudo and os.geteuid() != 0:
        cmd.append("sudo")
    cmd += [
        args.python,
        args.inference_script,
        "--data",
        args.data_dir,
        "--weights",
        str(deploy_path),
        "--n",
        str(args.n),
        "--packet-id-width",
        str(args.packet_id_width),
        "--assert-hls-reset",
        "--strict-identical",
        "--pl-clock-hz",
        str(int(args.pl_clock_hz)),
        "--output",
        str(out_json),
    ]
    if (not args.program_every_variant) and (not is_first_variant):
        cmd.append("--no-program")

    print("\n[RUN]", " ".join(cmd))
    if args.dry_run:
        return

    if args.resume and _is_complete_result(out_json, args.n):
        print(f"[RESUME] complete result exists, skip: {out_json}")
        return

    max_tries = max(1, int(args.max_retries) + 1)
    for attempt in range(1, max_tries + 1):
        try:
            subprocess.run(cmd, check=True)
            return
        except subprocess.CalledProcessError as e:
            if _is_complete_result(out_json, args.n):
                print(
                    f"[WARN] inference exited non-zero (rc={e.returncode}) but complete json exists; "
                    f"accepting result: {out_json}"
                )
                return
            if attempt >= max_tries:
                raise
            print(f"[RETRY] failed attempt {attempt}/{max_tries-1}, retrying variant ...")


def main() -> None:
    args = parse_args()
    variants = _parse_variants(args.variants)
    report_map = _parse_report_map(args.report_map_json)

    out_dir = Path(args.out_dir)
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, object]] = []

    for idx, (label, deploy_path) in enumerate(variants):
        if not deploy_path.exists():
            raise SystemExit(f"Missing deployment for variant '{label}': {deploy_path}")

        dep = np.load(deploy_path, allow_pickle=True)
        n_neurons = int(dep["q_weights"].shape[0])
        out_json = out_dir / f"mnist_10class_results_{label}.json"

        _run_variant(args, deploy_path, out_json, is_first_variant=(idx == 0))

        metrics = _infer_metrics(out_json) if not args.dry_run else {
            "hw_acc_ttfs": 0.0,
            "sw_acc_ttfs": 0.0,
            "sw_acc_count": 0.0,
            "ms_per_image": 0.0,
            "strict_identical": False,
            "strict_failures_n": 0,
            "pl_latency_cycles_mean": None,
            "pl_service_cycles_mean": None,
            "pl_latency_ms_mean": None,
            "pl_service_ms_mean": None,
            "pl_first_spike_tput_img_s": None,
            "pl_service_tput_img_s": None,
        }

        rep_info = report_map.get(label, {})
        parsed_rep: Dict[str, Optional[float]] = {}
        util_path = Path(rep_info["utilization"]) if "utilization" in rep_info else None
        timing_path = Path(rep_info["timing"]) if "timing" in rep_info else None
        power_path = Path(rep_info["power"]) if "power" in rep_info else None

        if util_path and util_path.exists():
            parsed_rep.update(_parse_utilization_report(util_path))
        if timing_path and timing_path.exists():
            parsed_rep.update(_parse_timing_report(timing_path))
        if power_path and power_path.exists():
            parsed_rep.update(_parse_power_report(power_path))

        row: Dict[str, object] = {
            "variant": label,
            "deployment": str(deploy_path),
            "n_neurons": n_neurons,
            "result": str(out_json),
            **metrics,
            **parsed_rep,
        }
        rows.append(row)

    if args.dry_run:
        return

    summary = {
        "config": {
            "inference_script": args.inference_script,
            "data_dir": args.data_dir,
            "variants": [{k: str(v)} for k, v in variants],
            "n": args.n,
            "packet_id_width": args.packet_id_width,
            "pl_clock_hz": args.pl_clock_hz,
            "sudo": args.sudo,
            "report_map_json": args.report_map_json,
        },
        "all_variants_strict_identical_pass": all(bool(r.get("strict_identical_pass")) for r in rows),
        "rows": rows,
    }

    summary_json = out_dir / "g15_scaling_summary.json"
    summary_md = out_dir / "g15_scaling_summary.md"
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md.write_text(_to_md(rows), encoding="utf-8")

    print(f"\nSaved: {summary_json}")
    print(f"Saved: {summary_md}")
    if not summary["all_variants_strict_identical_pass"]:
        print("[FAIL] One or more scaling points failed strict identity. See summary for details.")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
