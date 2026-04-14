#!/usr/bin/env python3
"""Run G20 reproducibility campaign by repeating strict inference runs."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple


_FLAG_SUPPORT_CACHE: Dict[Tuple[str, str], bool] = {}
_UNSUPPORTED_WARNED: Set[Tuple[str, str]] = set()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run repeated strict-inference reproducibility campaign")
    p.add_argument("--inference-script", required=True, help="Path to fpga_10class_inference.py")
    p.add_argument("--data-dir", required=True, help="Data directory (bit/hwh root)")
    p.add_argument("--weights", default="", help="Optional deployment npz path override")
    p.add_argument("--runs", type=int, default=5, help="Number of repeated runs")
    p.add_argument("--n", type=int, default=10000, help="Images per run")
    p.add_argument("--packet-id-width", type=int, default=13)
    p.add_argument("--pl-clock-hz", type=float, default=80_000_000.0)
    p.add_argument("--out-dir", required=True, help="Output directory")
    p.add_argument("--python", default="python3")
    p.add_argument("--sudo", action="store_true")
    p.add_argument("--no-program", action="store_true", help="Pass --no-program to inference script")
    p.add_argument("--sleep-between-s", type=float, default=0.0, help="Sleep between runs")
    p.add_argument("--max-retries", type=int, default=2, help="Retries per run on non-zero exit")
    p.add_argument("--retry-sleep-s", type=float, default=2.0, help="Sleep between retries")
    p.add_argument("--resume", action="store_true", help="Skip run if output JSON already exists")
    p.add_argument(
        "--allow-partial",
        action="store_true",
        help="Do not abort whole campaign if one run still fails after retries; summarize completed runs",
    )
    p.add_argument("--print-every", type=int, default=200)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def _script_supports_flag(script_path: str, flag: str) -> bool:
    key = (script_path, flag)
    if key in _FLAG_SUPPORT_CACHE:
        return _FLAG_SUPPORT_CACHE[key]
    try:
        txt = Path(script_path).read_text(encoding="utf-8", errors="ignore")
        ok = flag in txt
    except OSError:
        ok = False
    _FLAG_SUPPORT_CACHE[key] = ok
    return ok


def _warn_flag_omitted(script_path: str, flag: str) -> None:
    key = (script_path, flag)
    if key in _UNSUPPORTED_WARNED:
        return
    _UNSUPPORTED_WARNED.add(key)
    print(f"[INFO] omit unsupported flag '{flag}' for script: {script_path}")


def _run_once(args: argparse.Namespace, run_idx: int, out_json: Path) -> None:
    if args.resume and out_json.exists():
        print(f"\n[RUN {run_idx+1}] resume-skip: {out_json}")
        return

    base_cmd: List[str] = []
    if args.sudo and os.geteuid() != 0:
        base_cmd.append("sudo")
    base_cmd += [
        args.python,
        args.inference_script,
        "--data",
        args.data_dir,
        "--n",
        str(args.n),
        "--packet-id-width",
        str(args.packet_id_width),
        "--assert-hls-reset",
        "--strict-identical",
        "--output",
        str(out_json),
    ]
    if _script_supports_flag(args.inference_script, "--pl-clock-hz"):
        base_cmd += ["--pl-clock-hz", str(int(args.pl_clock_hz))]
    elif _script_supports_flag(args.inference_script, "--pl-clock-mhz"):
        base_cmd += ["--pl-clock-mhz", f"{args.pl_clock_hz / 1_000_000.0:.6f}"]
    else:
        raise RuntimeError(
            f"Inference script does not support --pl-clock-hz/--pl-clock-mhz: {args.inference_script}"
        )

    if _script_supports_flag(args.inference_script, "--print-every"):
        base_cmd += ["--print-every", str(args.print_every)]
    else:
        _warn_flag_omitted(args.inference_script, "--print-every")

    if args.weights:
        base_cmd += ["--weights", args.weights]
    if args.no_program:
        base_cmd.append("--no-program")

    attempts = max(1, int(args.max_retries))
    last_exc: subprocess.CalledProcessError | None = None
    for attempt in range(1, attempts + 1):
        print(f"\n[RUN {run_idx+1}] attempt {attempt}/{attempts}: {' '.join(base_cmd)}")
        if args.dry_run:
            return
        try:
            subprocess.run(base_cmd, check=True)
            return
        except subprocess.CalledProcessError as exc:
            last_exc = exc
            # Some board-side failures can happen after JSON has already been written.
            if out_json.exists():
                print(f"[WARN] run failed but output exists, accept: {out_json}")
                return
            if attempt < attempts and args.retry_sleep_s > 0:
                print(f"[RETRY] sleep {args.retry_sleep_s:.1f}s")
                time.sleep(args.retry_sleep_s)

    assert last_exc is not None
    raise last_exc


def _load_result(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        d = json.load(f)
    fails = d.get("strict_failures", [])
    fail_idx: List[int] = [int(x.get("idx")) for x in fails if "idx" in x]
    return {
        "json_path": str(path),
        "strict_failures_n": len(fail_idx),
        "fail_indices": sorted(set(fail_idx)),
        "strict_identical": bool(d.get("strict_identical", False)),
        "hw_acc_ttfs": float(d.get("hw_acc_ttfs", 0.0)),
        "sw_acc_ttfs": float(d.get("sw_acc_ttfs", 0.0)),
        "ms_per_image": float(d.get("ms_per_image", 0.0)),
        "pl_service_cycles_mean": d.get("pl_service_cycles_mean"),
        "pl_service_ms_mean": d.get("pl_service_ms_mean"),
    }


def _to_md(rows: List[Dict], summary: Dict) -> str:
    lines = [
        "# G20 Reproducibility Summary",
        "",
        "| Run | strict_failures | HW TTFS | SW TTFS | ms/img | PL service cyc |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for i, r in enumerate(rows):
        lines.append(
            f"| {i+1} | {r['strict_failures_n']} | {r['hw_acc_ttfs']:.4f} | {r['sw_acc_ttfs']:.4f} | "
            f"{r['ms_per_image']:.4f} | {r.get('pl_service_cycles_mean')} |"
        )
    lines += [
        "",
        "## Aggregate",
        "",
        f"- all_zero_strict_failures: `{summary['all_zero_strict_failures']}`",
        f"- strict_failures_mean: `{summary['strict_failures_mean']:.4f}`",
        f"- strict_failures_std: `{summary['strict_failures_std']:.4f}`",
        f"- hw_acc_ttfs_mean: `{summary['hw_acc_ttfs_mean']:.6f}`",
        f"- hw_acc_ttfs_std: `{summary['hw_acc_ttfs_std']:.6f}`",
        f"- ms_per_image_mean: `{summary['ms_per_image_mean']:.6f}`",
        f"- ms_per_image_std: `{summary['ms_per_image_std']:.6f}`",
        f"- fail_index_union_size: `{summary['fail_index_union_size']}`",
        f"- fail_index_intersection_size: `{summary['fail_index_intersection_size']}`",
        "",
    ]
    return "\n".join(lines)


def _mean(vals: List[float]) -> float:
    return float(sum(vals) / max(len(vals), 1))


def _stdev(vals: List[float]) -> float:
    if len(vals) < 2:
        return 0.0
    return float(statistics.pstdev(vals))


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict] = []

    for i in range(args.runs):
        out_json = out_dir / f"mnist_10class_results_run{i+1:02d}.json"
        try:
            _run_once(args, i, out_json)
        except subprocess.CalledProcessError as exc:
            if not args.allow_partial:
                raise exc
            print(
                f"[WARN] run {i+1} failed after retries (allow-partial enabled): {exc}. "
                "Continuing with completed runs."
            )
            break
        if not args.dry_run:
            if out_json.exists():
                row = _load_result(out_json)
                rows.append(row)
            elif not args.allow_partial:
                raise FileNotFoundError(f"Missing expected result JSON: {out_json}")
        if args.sleep_between_s > 0 and i < args.runs - 1:
            print(f"[SLEEP] {args.sleep_between_s:.2f}s")
            time.sleep(args.sleep_between_s)

    if args.dry_run:
        return

    strict_ns = [float(r["strict_failures_n"]) for r in rows]
    hw_accs = [float(r["hw_acc_ttfs"]) for r in rows]
    ms_e2e = [float(r["ms_per_image"]) for r in rows]

    fail_sets: List[Set[int]] = [set(r["fail_indices"]) for r in rows]
    fail_union: Set[int] = set().union(*fail_sets) if fail_sets else set()
    fail_intersection: Set[int] = set(fail_sets[0]) if fail_sets else set()
    for s in fail_sets[1:]:
        fail_intersection &= s

    summary = {
        "target_runs": args.runs,
        "completed_runs": len(rows),
        "runs": args.runs,
        "all_zero_strict_failures": all(n == 0 for n in strict_ns),
        "strict_failures_mean": _mean(strict_ns),
        "strict_failures_std": _stdev(strict_ns),
        "hw_acc_ttfs_mean": _mean(hw_accs),
        "hw_acc_ttfs_std": _stdev(hw_accs),
        "ms_per_image_mean": _mean(ms_e2e),
        "ms_per_image_std": _stdev(ms_e2e),
        "fail_index_union_size": len(fail_union),
        "fail_index_intersection_size": len(fail_intersection),
        "fail_index_union": sorted(fail_union),
        "fail_index_intersection": sorted(fail_intersection),
    }

    payload = {
        "config": {
            "inference_script": args.inference_script,
            "data_dir": args.data_dir,
            "weights": args.weights,
            "runs": args.runs,
            "n": args.n,
            "packet_id_width": args.packet_id_width,
            "pl_clock_hz": args.pl_clock_hz,
            "sudo": args.sudo,
            "no_program": args.no_program,
            "sleep_between_s": args.sleep_between_s,
            "max_retries": args.max_retries,
            "retry_sleep_s": args.retry_sleep_s,
            "resume": args.resume,
            "allow_partial": args.allow_partial,
        },
        "rows": rows,
        "summary": summary,
    }

    summary_json = out_dir / "g20_reproducibility_summary.json"
    summary_md = out_dir / "g20_reproducibility_summary.md"
    summary_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    summary_md.write_text(_to_md(rows, summary), encoding="utf-8")

    print(f"\nSaved: {summary_json}")
    print(f"Saved: {summary_md}")


if __name__ == "__main__":
    main()
