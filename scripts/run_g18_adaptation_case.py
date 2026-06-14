#!/usr/bin/env python3
"""Run a simple two-phase STDP adaptation case and summarize weight-shift evidence."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run 2-phase STDP adaptation case (G18 B4 helper)")
    p.add_argument("--parity-script", required=True, help="Path to tests/fpga_stdp_parity.py")
    p.add_argument("--data-dir", required=True, help="Board data directory")
    p.add_argument("--out-dir", required=True, help="Output directory")

    p.add_argument("--phase1-steps", type=int, default=100)
    p.add_argument("--phase2-steps", type=int, default=100)
    p.add_argument("--checkpoint-every", type=int, default=10)
    p.add_argument("--run-chunk-steps", type=int, default=1)
    p.add_argument("--runtime-profile", default="balanced")
    p.add_argument("--packet-id-width", type=int, default=13)
    p.add_argument("--post-flush-runs", type=int, default=4)

    p.add_argument("--phase1-pattern", choices=["cycle", "random"], default="cycle")
    p.add_argument("--phase2-pattern", choices=["cycle", "random"], default="random")
    p.add_argument("--phase1-seed", type=int, default=1)
    p.add_argument("--phase2-seed", type=int, default=123)
    p.add_argument("--phase1-pre-base", type=int, default=0)
    p.add_argument("--phase2-pre-base", type=int, default=32)
    p.add_argument("--phase1-post-base", type=int, default=784)
    p.add_argument("--phase2-post-base", type=int, default=816)
    p.add_argument("--n-sources", type=int, default=196)
    p.add_argument("--sw-post-source", choices=["synthetic", "captured"], default="synthetic")

    p.add_argument("--python", default="/usr/local/share/pynq-venv/bin/python3")
    p.add_argument("--sudo", action="store_true")
    p.add_argument("--no-strict", action="store_true")
    p.add_argument("--no-check-hls-version", action="store_true")
    p.add_argument("--phase1-no-assert-hls-reset", action="store_true")
    p.add_argument(
        "--phase2-no-assert-hls-reset",
        action="store_true",
        default=False,
        help="Disable phase2 assert-hls-reset (default is enabled).",
    )
    p.add_argument(
        "--phase2-program",
        action="store_true",
        help="Program FPGA again for phase2 (default keeps phase1 programming via --no-program).",
    )
    p.add_argument("--allow-cma-spike-buffer", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--allow-fail", action="store_true", help="Do not exit non-zero on adaptation_gate_pass false")
    return p.parse_args()


def _build_cmd(
    args: argparse.Namespace,
    output_path: Path,
    *,
    n_steps: int,
    pattern: str,
    seed: int,
    pre_base: int,
    post_base: int,
    assert_hls_reset: bool,
    no_program: bool,
) -> List[str]:
    cmd: List[str] = []
    if args.sudo and os.geteuid() != 0:
        py_path = "/home/xilinx/snn/software/python"
        cmd += ["sudo", "-E", "env", f"PYTHONPATH={py_path}"]

    cmd += [
        args.python,
        args.parity_script,
        "--data",
        args.data_dir,
        "--output",
        str(output_path),
        "--n-steps",
        str(int(n_steps)),
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
        "--pattern",
        str(pattern),
        "--seed",
        str(int(seed)),
        "--pre-base",
        str(int(pre_base)),
        "--post-base",
        str(int(post_base)),
        "--n-sources",
        str(int(args.n_sources)),
        "--sw-post-source",
        str(args.sw_post_source),
    ]

    if no_program:
        cmd.append("--no-program")
    if assert_hls_reset:
        cmd.append("--assert-hls-reset")
    if not args.no_strict:
        cmd.append("--strict")
    if not args.no_check_hls_version:
        cmd.append("--check-hls-version")
    if not args.allow_cma_spike_buffer:
        cmd.append("--no-cma-spike-buffer")
    return cmd


def _load_parity(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _has_complete_parity_output(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return isinstance(d, dict) and isinstance(d.get("final_compare"), dict) and isinstance(d.get("chunks"), list)


def _last_checkpoint_wsum(parity: Dict[str, Any]) -> int:
    chunks = parity.get("chunks", [])
    for c in reversed(chunks):
        ck = c.get("checkpoint_meta")
        if isinstance(ck, dict) and "weight_sum_checkpoint" in ck:
            return int(ck.get("weight_sum_checkpoint", 0))
    init_ck = parity.get("initial_checkpoint", {})
    return int(init_ck.get("weight_sum_checkpoint", 0))


def _final_mismatch(parity: Dict[str, Any]) -> int:
    fc = parity.get("final_compare", {})
    return int(fc.get("mismatch_count", -1))


def _to_md(payload: Dict[str, Any]) -> str:
    s = payload["summary"]
    p1 = payload["phase1"]
    p2 = payload["phase2"]
    lines = [
        "# G18 Adaptation Case Summary",
        "",
        "## Phase Config",
        "",
        f"- phase1: pattern={p1['config']['pattern']}, seed={p1['config']['seed']}, pre_base={p1['config']['pre_base']}, post_base={p1['config']['post_base']}, steps={p1['config']['steps']}",
        f"- phase2: pattern={p2['config']['pattern']}, seed={p2['config']['seed']}, pre_base={p2['config']['pre_base']}, post_base={p2['config']['post_base']}, steps={p2['config']['steps']}",
        "",
        "## Results",
        "",
        f"- phase1_final_mismatch_count: `{p1['final_mismatch_count']}`",
        f"- phase1_compare_pass: `{p1['compare_pass']}`",
        f"- phase2_final_mismatch_count: `{p2['final_mismatch_count']}`",
        f"- phase2_compare_pass: `{p2['compare_pass']}`",
        f"- phase1_last_checkpoint_weight_sum: `{p1['last_checkpoint_weight_sum']}`",
        f"- phase2_last_checkpoint_weight_sum: `{p2['last_checkpoint_weight_sum']}`",
        f"- weight_sum_delta_phase2_minus_phase1: `{s['weight_sum_delta']}`",
        f"- adaptation_signal_observed: `{s['adaptation_signal_observed']}`",
        f"- adaptation_gate_pass: `{s['adaptation_gate_pass']}`",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    p1_json = out_dir / "stdp_parity_phase1.json"
    p2_json = out_dir / "stdp_parity_phase2.json"
    summary_json = out_dir / "g18_adaptation_summary.json"
    summary_md = out_dir / "g18_adaptation_summary.md"

    cmd1 = _build_cmd(
        args,
        p1_json,
        n_steps=int(args.phase1_steps),
        pattern=str(args.phase1_pattern),
        seed=int(args.phase1_seed),
        pre_base=int(args.phase1_pre_base),
        post_base=int(args.phase1_post_base),
        assert_hls_reset=bool(not args.phase1_no_assert_hls_reset),
        no_program=False,
    )
    cmd2 = _build_cmd(
        args,
        p2_json,
        n_steps=int(args.phase2_steps),
        pattern=str(args.phase2_pattern),
        seed=int(args.phase2_seed),
        pre_base=int(args.phase2_pre_base),
        post_base=int(args.phase2_post_base),
        assert_hls_reset=bool(not args.phase2_no_assert_hls_reset),
        no_program=bool(not args.phase2_program),
    )

    if args.resume and p1_json.exists():
        print(f"[RESUME] phase1 reuse: {p1_json}")
    else:
        print("[RUN phase1]", " ".join(cmd1))
        if not args.dry_run:
            try:
                subprocess.run(cmd1, check=True)
            except subprocess.CalledProcessError as e:
                if _has_complete_parity_output(p1_json):
                    print(
                        f"[WARN] phase1 exited non-zero (rc={e.returncode}) but parity JSON exists; "
                        "continuing with generated artifact."
                    )
                else:
                    raise

    if args.resume and p2_json.exists():
        print(f"[RESUME] phase2 reuse: {p2_json}")
    else:
        print("[RUN phase2]", " ".join(cmd2))
        if not args.dry_run:
            try:
                subprocess.run(cmd2, check=True)
            except subprocess.CalledProcessError as e:
                if _has_complete_parity_output(p2_json):
                    print(
                        f"[WARN] phase2 exited non-zero (rc={e.returncode}) but parity JSON exists; "
                        "continuing with generated artifact."
                    )
                else:
                    raise

    if args.dry_run:
        return

    d1 = _load_parity(p1_json)
    d2 = _load_parity(p2_json)

    p1_wsum = _last_checkpoint_wsum(d1)
    p2_wsum = _last_checkpoint_wsum(d2)
    p1_mis = _final_mismatch(d1)
    p2_mis = _final_mismatch(d2)

    delta = int(p2_wsum - p1_wsum)
    adapt_signal = bool(delta != 0)
    adapt_pass = bool(p1_mis == 0 and p2_mis == 0 and adapt_signal)

    payload = {
        "config": {
            "parity_script": args.parity_script,
            "data_dir": args.data_dir,
            "strict": bool(not args.no_strict),
            "sw_post_source": args.sw_post_source,
            "runtime_profile": args.runtime_profile,
            "packet_id_width": int(args.packet_id_width),
            "checkpoint_every": int(args.checkpoint_every),
            "run_chunk_steps": int(args.run_chunk_steps),
            "post_flush_runs": int(args.post_flush_runs),
            "phase2_no_program": bool(not args.phase2_program),
            "phase1_assert_hls_reset": bool(not args.phase1_no_assert_hls_reset),
            "phase2_assert_hls_reset": bool(not args.phase2_no_assert_hls_reset),
        },
        "phase1": {
            "json_path": str(p1_json),
            "config": {
                "steps": int(args.phase1_steps),
                "pattern": str(args.phase1_pattern),
                "seed": int(args.phase1_seed),
                "pre_base": int(args.phase1_pre_base),
                "post_base": int(args.phase1_post_base),
            },
            "final_mismatch_count": p1_mis,
            "last_checkpoint_weight_sum": p1_wsum,
            "ms_per_step": float(d1.get("ms_per_step", 0.0)),
            "compare_pass": bool(p1_mis == 0),
        },
        "phase2": {
            "json_path": str(p2_json),
            "config": {
                "steps": int(args.phase2_steps),
                "pattern": str(args.phase2_pattern),
                "seed": int(args.phase2_seed),
                "pre_base": int(args.phase2_pre_base),
                "post_base": int(args.phase2_post_base),
            },
            "final_mismatch_count": p2_mis,
            "last_checkpoint_weight_sum": p2_wsum,
            "ms_per_step": float(d2.get("ms_per_step", 0.0)),
            "compare_pass": bool(p2_mis == 0),
        },
        "summary": {
            "weight_sum_delta": delta,
            "adaptation_signal_observed": adapt_signal,
            "adaptation_gate_pass": adapt_pass,
            "adaptation_gate_basis": "phase1/phase2 final mismatch_count == 0 AND phase2_weight_sum != phase1_weight_sum",
        },
    }

    summary_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    summary_md.write_text(_to_md(payload), encoding="utf-8")
    print(f"\nSaved: {summary_json}")
    print(f"Saved: {summary_md}")
    print("adaptation_gate_pass:", payload["summary"]["adaptation_gate_pass"])
    print("weight_sum_delta:", payload["summary"]["weight_sum_delta"])

    if (not payload["summary"]["adaptation_gate_pass"]) and (not args.allow_fail):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
