#!/usr/bin/env python3
"""Run and summarize G13 quantization ablation (8/4/2-bit by default)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run G13 quantization ablation on board")
    p.add_argument("--inference-script", required=True, help="Path to fpga_10class_inference.py on board")
    p.add_argument("--data-dir", required=True, help="Board data dir (bit/npz root)")
    p.add_argument("--weights-dir", required=True, help="Directory containing *_q{bits}.npz")
    p.add_argument("--weights-prefix", default="mnist_10class_deployment", help="Weights file prefix")
    p.add_argument("--variants", default="8,4,2", help="Comma-separated quantization bits")
    p.add_argument("--n", type=int, default=10000, help="Number of images")
    p.add_argument("--packet-id-width", type=int, default=13)
    p.add_argument("--pl-clock-hz", type=float, default=80_000_000.0)
    p.add_argument("--out-dir", required=True, help="Output directory for per-run JSON and summary")
    p.add_argument("--python", default="python3", help="Python executable")
    p.add_argument("--sudo", action="store_true", help="Prepend sudo to inference command")
    p.add_argument("--max-retries", type=int, default=2, help="Retries per variant on non-zero exit")
    p.add_argument("--retry-sleep-s", type=float, default=2.0, help="Sleep between retries")
    p.add_argument("--resume", action="store_true", help="Skip variant if complete result JSON exists")
    p.add_argument(
        "--allow-partial",
        action="store_true",
        help="Continue summary generation even if some variants fail",
    )
    p.add_argument(
        "--program-every-variant",
        action="store_true",
        help="Force bitstream programming for every variant (default: first only, then --no-program)",
    )
    p.add_argument("--dry-run", action="store_true", help="Print commands only")
    return p.parse_args()


def _load_result(path: Path) -> Dict[str, float]:
    d = json.loads(path.read_text(encoding="utf-8"))
    strict_failures = d.get("strict_failures", [])
    return {
        "hw_acc_ttfs": float(d.get("hw_acc_ttfs", 0.0)),
        "sw_acc_ttfs": float(d.get("sw_acc_ttfs", 0.0)),
        "sw_acc_count": float(d.get("sw_acc_count", 0.0)),
        "ms_per_image": float(d.get("ms_per_image", 0.0)),
        "strict_failures_n": int(len(strict_failures)),
        "strict_identical": bool(d.get("strict_identical", False)),
        "pl_latency_cycles_mean": d.get("pl_latency_cycles_mean"),
        "pl_service_cycles_mean": d.get("pl_service_cycles_mean"),
    }


def _is_complete_result(path: Path, n_expected: int) -> bool:
    if not path.exists():
        return False
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
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


def _to_md(rows: List[Dict[str, object]]) -> str:
    lines = [
        "# G13 Quantization Ablation Summary",
        "",
        "| Variant | HW TTFS | SW TTFS | SW Count | ms/img (E2E) | strict_failures | strict_identical | pl_latency_cyc | pl_service_cyc |",
        "|---|---:|---:|---:|---:|---:|---|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| q{r['bits']} | {r['hw_acc_ttfs']:.4f} | {r['sw_acc_ttfs']:.4f} | {r['sw_acc_count']:.4f} | "
            f"{r['ms_per_image']:.4f} | {r['strict_failures_n']} | {r['strict_identical']} | "
            f"{r['pl_latency_cycles_mean']} | {r['pl_service_cycles_mean']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()

    bits = sorted({int(x.strip()) for x in args.variants.split(",") if x.strip()}, reverse=True)
    out_dir = Path(args.out_dir)
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, object]] = []

    failed_bits: List[int] = []

    for idx, b in enumerate(bits):
        w_path = Path(args.weights_dir) / f"{args.weights_prefix}_q{b}.npz"
        out_json = out_dir / f"mnist_10class_results_q{b}.json"

        cmd = []
        if args.sudo and os.geteuid() != 0:
            cmd.append("sudo")
        cmd += [
            args.python,
            args.inference_script,
            "--data", args.data_dir,
            "--weights", str(w_path),
            "--n", str(args.n),
            "--packet-id-width", str(args.packet_id_width),
            "--assert-hls-reset",
            "--strict-identical",
            "--pl-clock-hz", str(int(args.pl_clock_hz)),
            "--output", str(out_json),
        ]
        if (not args.program_every_variant) and idx > 0:
            cmd.append("--no-program")

        print("\n[RUN]", " ".join(cmd))
        if args.dry_run:
            continue

        if not w_path.exists():
            raise SystemExit(f"Missing weights variant: {w_path}")

        if args.resume and _is_complete_result(out_json, args.n):
            print(f"[RESUME] complete result exists, skip: {out_json}")
        else:
            max_tries = max(1, int(args.max_retries) + 1)
            run_ok = False
            for attempt in range(1, max_tries + 1):
                try:
                    print(f"[TRY] q{b} attempt {attempt}/{max_tries}")
                    subprocess.run(cmd, check=True)
                    run_ok = True
                    break
                except subprocess.CalledProcessError as e:
                    if _is_complete_result(out_json, args.n):
                        print(
                            f"[WARN] q{b} non-zero exit (rc={e.returncode}) but complete JSON exists; "
                            f"accepting result: {out_json}"
                        )
                        run_ok = True
                        break
                    if attempt < max_tries and args.retry_sleep_s > 0:
                        print(f"[RETRY] q{b} sleep {args.retry_sleep_s:.1f}s")
                        time.sleep(args.retry_sleep_s)
            if not run_ok:
                msg = f"Variant q{b} failed after retries"
                failed_bits.append(b)
                if not args.allow_partial:
                    raise SystemExit(msg)
                print(f"[WARN] {msg}; continue due to --allow-partial")
                continue

        if not _is_complete_result(out_json, args.n):
            failed_bits.append(b)
            msg = f"Variant q{b} result JSON missing/incomplete: {out_json}"
            if not args.allow_partial:
                raise SystemExit(msg)
            print(f"[WARN] {msg}; continue due to --allow-partial")
            continue

        metrics = _load_result(out_json)
        row: Dict[str, object] = {"bits": b, "weights": str(w_path), "result": str(out_json), **metrics}
        rows.append(row)

    if args.dry_run:
        return

    summary = {
        "variants": rows,
        "failed_variants": failed_bits,
        "config": {
            "inference_script": args.inference_script,
            "data_dir": args.data_dir,
            "weights_dir": args.weights_dir,
            "weights_prefix": args.weights_prefix,
            "n": args.n,
            "packet_id_width": args.packet_id_width,
            "pl_clock_hz": args.pl_clock_hz,
            "sudo": args.sudo,
            "max_retries": args.max_retries,
            "retry_sleep_s": args.retry_sleep_s,
            "resume": args.resume,
            "allow_partial": args.allow_partial,
            "program_every_variant": args.program_every_variant,
        },
    }

    summary_json = out_dir / "g13_quant_ablation_summary.json"
    summary_md = out_dir / "g13_quant_ablation_summary.md"

    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md.write_text(_to_md(rows), encoding="utf-8")

    print(f"\nSaved: {summary_json}")
    print(f"Saved: {summary_md}")


if __name__ == "__main__":
    main()
