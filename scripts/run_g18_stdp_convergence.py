#!/usr/bin/env python3
"""Run STDP convergence campaign (B1/B2) and summarize trajectory agreement."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run G18 STDP convergence + trajectory agreement summary")
    p.add_argument("--parity-script", required=True, help="Path to tests/fpga_stdp_parity.py")
    p.add_argument("--data-dir", required=True, help="Board data directory (bit/hwh root)")
    p.add_argument("--out-dir", required=True, help="Output directory for raw parity + summary")

    p.add_argument("--n-steps", type=int, default=100, help="STDP step count")
    p.add_argument("--checkpoint-every", type=int, default=10, help="Checkpoint cadence (steps)")
    p.add_argument("--run-chunk-steps", type=int, default=1, help="Execution chunk size")
    p.add_argument("--runtime-profile", default="balanced")
    p.add_argument("--packet-id-width", type=int, default=13)
    p.add_argument("--post-flush-runs", type=int, default=4)

    p.add_argument("--python", default="/usr/local/share/pynq-venv/bin/python3")
    p.add_argument("--sudo", action="store_true")
    p.add_argument("--no-assert-hls-reset", action="store_true")
    p.add_argument("--no-check-hls-version", action="store_true")
    p.add_argument("--no-program", action="store_true")
    p.add_argument("--no-strict", action="store_true")
    p.add_argument("--allow-cma-spike-buffer", action="store_true")
    p.add_argument("--sw-post-source", default="synthetic", choices=["synthetic", "captured", "none"])
    p.add_argument(
        "--allow-fail",
        action="store_true",
        help="Do not raise non-zero even when trajectory_agreement_pass is false",
    )
    p.add_argument("--resume", action="store_true", help="Reuse existing parity output if present")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--parity-output",
        default="",
        help="Optional raw parity output path (default: <out-dir>/stdp_parity_results_g18.json)",
    )
    return p.parse_args()


def _pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0.0 or vy <= 0.0:
        return None
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return float(cov / math.sqrt(vx * vy))


def _build_parity_cmd(args: argparse.Namespace, parity_output: Path) -> List[str]:
    cmd: List[str] = []
    if args.sudo and os.geteuid() != 0:
        # Keep a deterministic project-local PYTHONPATH for board reproducibility.
        py_path = "/home/xilinx/snn/software/python"
        cmd += ["sudo", "-E", "env", f"PYTHONPATH={py_path}"]

    cmd += [
        args.python,
        args.parity_script,
        "--data",
        args.data_dir,
        "--n-steps",
        str(int(args.n_steps)),
        "--checkpoint-every",
        str(int(args.checkpoint_every)),
        "--run-chunk-steps",
        str(int(args.run_chunk_steps)),
        "--runtime-profile",
        str(args.runtime_profile),
        "--packet-id-width",
        str(int(args.packet_id_width)),
        "--post-flush-runs",
        str(int(args.post_flush_runs)),
        "--sw-post-source",
        str(args.sw_post_source),
        "--output",
        str(parity_output),
    ]

    if not args.no_assert_hls_reset:
        cmd.append("--assert-hls-reset")
    if not args.no_check_hls_version:
        cmd.append("--check-hls-version")
    if args.no_program:
        cmd.append("--no-program")
    if not args.no_strict:
        cmd.append("--strict")
    if not args.allow_cma_spike_buffer:
        cmd.append("--no-cma-spike-buffer")

    return cmd


def _extract_checkpoint_rows(parity: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    chunks = parity.get("chunks", [])
    for c in chunks:
        cmp_meta = c.get("compare")
        if not isinstance(cmp_meta, dict):
            continue
        ckpt = c.get("checkpoint_meta") or {}
        run = c.get("run_meta") or {}
        nz = cmp_meta.get("nonzero_summary") or {}
        row = {
            "chunk_idx": int(c.get("chunk_idx", -1)),
            "end_step": int(c.get("end_step", -1)),
            "mismatch_count": int(cmp_meta.get("mismatch_count", -1)),
            "equal": int(cmp_meta.get("equal", 0)),
            "weight_sum_checkpoint": int(ckpt.get("weight_sum_checkpoint", 0)),
            "weight_sum_hls_pre": int(ckpt.get("weight_sum_hls_pre", 0)),
            "weight_sum_hls_post": int(ckpt.get("weight_sum_hls_post", 0)),
            "weight_sum_run_pre": int(run.get("weight_sum_pre", 0)),
            "weight_sum_run_post": int(run.get("weight_sum_post", 0)),
            "update_complete": int(run.get("update_complete", 0)),
            "post_complete_est": int(run.get("post_complete_est", 0)),
            "router_spikes": int(run.get("router_spikes", 0)),
            "neuron_spikes": int(run.get("neuron_spikes", 0)),
            "hls_input_spikes": int(run.get("hls_input_spikes", 0)),
            "hw_nonzero_count": int(nz.get("hw_nonzero_count", 0)),
            "sw_nonzero_count": int(nz.get("sw_nonzero_count", 0)),
            "overlap_nonzero_count": int(nz.get("overlap_nonzero_count", 0)),
        }
        rows.append(row)
    return rows


def _aggregate(parity: Dict[str, Any], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    mism = [int(r["mismatch_count"]) for r in rows]
    w_ckpt = [float(r["weight_sum_checkpoint"]) for r in rows]
    w_hls = [float(r["weight_sum_hls_post"]) for r in rows]
    w_run_post = [float(r["weight_sum_run_post"]) for r in rows]
    w_abs_err = [abs(a - b) for a, b in zip(w_ckpt, w_hls)]

    final_cmp = parity.get("final_compare", {}) if isinstance(parity.get("final_compare"), dict) else {}
    final_mismatch = int(final_cmp.get("mismatch_count", -1))
    final_equal = int(final_cmp.get("equal", 0))

    traj_pass = (
        len(rows) > 0
        and all(int(x) == 0 for x in mism)
        and final_mismatch == 0
        and final_equal == 1
        and all(int(r["update_complete"]) == 1 for r in rows)
        and all(int(r["post_complete_est"]) == 1 for r in rows)
    )

    return {
        "n_steps": int(parity.get("n_steps", 0)),
        "checkpoint_every": int(parity.get("checkpoint_every", 0)),
        "run_chunk_steps": int(parity.get("run_chunk_steps", 0)),
        "n_checkpoints": len(rows),
        "final_mismatch_count": final_mismatch,
        "final_equal": bool(final_equal == 1),
        "all_checkpoint_equal": bool(len(rows) > 0 and all(int(x) == 0 for x in mism)),
        "checkpoint_mismatch_max": int(max(mism) if mism else -1),
        "checkpoint_mismatch_mean": float(statistics.fmean(mism) if mism else float("nan")),
        "update_complete_all": bool(rows and all(int(r["update_complete"]) == 1 for r in rows)),
        "post_complete_all": bool(rows and all(int(r["post_complete_est"]) == 1 for r in rows)),
        "weight_sum_abs_err_mean": float(statistics.fmean(w_abs_err) if w_abs_err else float("nan")),
        "weight_sum_abs_err_max": float(max(w_abs_err) if w_abs_err else float("nan")),
        # Correlation metrics are diagnostic-only. Pass/fail is determined by
        # checkpoint mismatch + update/post completion flags above.
        "weight_sum_corr_ckpt_vs_hls_post": _pearson(w_ckpt, w_hls),
        "weight_sum_corr_ckpt_vs_run_post": _pearson(w_ckpt, w_run_post),
        "trajectory_agreement_pass": bool(traj_pass),
        "convergence_trace_available": bool(len(rows) >= 2),
        "trajectory_agreement_basis": "all checkpoint mismatch_count == 0 AND final mismatch_count == 0 AND update_complete/post_complete_est == 1",
        "ms_per_step": float(parity.get("ms_per_step", 0.0)),
    }


def _to_md(summary: Dict[str, Any], rows: List[Dict[str, Any]], raw_path: Path) -> str:
    def fmt(v: Any, nd: int = 6) -> str:
        if v is None:
            return "N/A"
        if isinstance(v, float) and math.isnan(v):
            return "N/A"
        if isinstance(v, bool):
            return str(v)
        if isinstance(v, int):
            return str(v)
        return f"{float(v):.{nd}f}"

    lines = [
        "# G18 STDP Convergence Summary",
        "",
        f"- raw_parity_json: `{raw_path}`",
        f"- trajectory_agreement_pass: `{summary['trajectory_agreement_pass']}`",
        f"- convergence_trace_available: `{summary['convergence_trace_available']}`",
        f"- n_checkpoints: `{summary['n_checkpoints']}`",
        f"- final_mismatch_count: `{summary['final_mismatch_count']}`",
        f"- checkpoint_mismatch_mean/max: `{fmt(summary['checkpoint_mismatch_mean'], 4)}` / `{summary['checkpoint_mismatch_max']}`",
        f"- weight_sum_abs_err_mean/max: `{fmt(summary['weight_sum_abs_err_mean'], 4)}` / `{fmt(summary['weight_sum_abs_err_max'], 4)}`",
        f"- weight_sum_corr_ckpt_vs_hls_post (diagnostic): `{fmt(summary['weight_sum_corr_ckpt_vs_hls_post'], 6)}`",
        f"- weight_sum_corr_ckpt_vs_run_post (diagnostic): `{fmt(summary['weight_sum_corr_ckpt_vs_run_post'], 6)}`",
        f"- trajectory_agreement_basis: `{summary['trajectory_agreement_basis']}`",
        "",
        "| ckpt# | end_step | mismatch | wsum_ckpt | wsum_hls_post | wsum_abs_err | update_ok | post_ok |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for r in rows:
        err = abs(float(r["weight_sum_checkpoint"]) - float(r["weight_sum_hls_post"]))
        lines.append(
            f"| {r['chunk_idx']} | {r['end_step']} | {r['mismatch_count']} | "
            f"{r['weight_sum_checkpoint']} | {r['weight_sum_hls_post']} | {err:.4f} | "
            f"{r['update_complete']} | {r['post_complete_est']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    parity_output = Path(args.parity_output) if args.parity_output else (out_dir / "stdp_parity_results_g18.json")
    summary_json = out_dir / "g18_stdp_convergence_summary.json"
    summary_md = out_dir / "g18_stdp_convergence_summary.md"

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    cmd = _build_parity_cmd(args, parity_output)
    if args.resume and parity_output.exists():
        print(f"[RESUME] using existing parity output: {parity_output}")
    else:
        print("[RUN]", " ".join(cmd))
        if not args.dry_run:
            subprocess.run(cmd, check=True)

    if args.dry_run:
        return

    parity = json.loads(parity_output.read_text(encoding="utf-8"))
    rows = _extract_checkpoint_rows(parity)
    summary = _aggregate(parity, rows)

    payload = {
        "config": {
            "parity_script": args.parity_script,
            "data_dir": args.data_dir,
            "n_steps": int(args.n_steps),
            "checkpoint_every": int(args.checkpoint_every),
            "run_chunk_steps": int(args.run_chunk_steps),
            "runtime_profile": str(args.runtime_profile),
            "packet_id_width": int(args.packet_id_width),
            "post_flush_runs": int(args.post_flush_runs),
            "strict": bool(not args.no_strict),
            "sw_post_source": str(args.sw_post_source),
            "sudo": bool(args.sudo),
        },
        "raw_parity_json": str(parity_output),
        "summary": summary,
        "checkpoint_rows": rows,
    }
    summary_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    summary_md.write_text(_to_md(summary, rows, parity_output), encoding="utf-8")

    print(f"\nSaved: {summary_json}")
    print(f"Saved: {summary_md}")
    print("trajectory_agreement_pass:", summary["trajectory_agreement_pass"])
    print("convergence_trace_available:", summary["convergence_trace_available"])
    print("n_checkpoints:", summary["n_checkpoints"])
    print("final_mismatch_count:", summary["final_mismatch_count"])

    # Gate-style failure for G18 pre-check.
    if (not summary["trajectory_agreement_pass"]) and (not args.allow_fail):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
