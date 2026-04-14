#!/usr/bin/env python3
"""Run G19 sparsity sweep by generating sparse deployment variants and benchmarking."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate sparsity variants and run inference sweep")
    p.add_argument("--base-npz", required=True, help="Base deployment npz")
    p.add_argument("--out-dir", required=True, help="Output directory")
    p.add_argument(
        "--sparsity-levels",
        default="0.0,0.25,0.5,0.75,0.9",
        help="Comma-separated drop ratios over active pixels (>pixel-threshold)",
    )
    p.add_argument("--pixel-threshold", type=float, default=0.3, help="Active pixel threshold")
    p.add_argument("--strategy", choices=["topk", "random"], default="topk")
    p.add_argument("--seed", type=int, default=42)

    p.add_argument("--inference-script", default="", help="Path to fpga_10class_inference.py")
    p.add_argument("--data-dir", default="", help="Data directory (required when inference is enabled)")
    p.add_argument("--n", type=int, default=10000)
    p.add_argument("--packet-id-width", type=int, default=13)
    p.add_argument("--pl-clock-hz", type=float, default=80_000_000.0)
    p.add_argument("--python", default="python3")
    p.add_argument("--sudo", action="store_true")
    p.add_argument("--max-retries", type=int, default=2, help="Retries per failed variant run")
    p.add_argument("--resume", action="store_true", help="Skip variants with complete existing result json")
    p.add_argument(
        "--program-every-variant",
        action="store_true",
        help="Force bitstream reprogramming for each variant (default: only first variant programs FPGA)",
    )
    p.add_argument("--skip-inference", action="store_true", help="Only generate NPZ variants")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def _parse_levels(raw: str) -> List[float]:
    vals: List[float] = []
    for x in raw.split(","):
        x = x.strip()
        if not x:
            continue
        v = float(x)
        if v < 0.0 or v >= 1.0:
            raise SystemExit(f"Invalid sparsity level {v}. Use 0 <= v < 1.")
        vals.append(v)
    if not vals:
        raise SystemExit("No sparsity levels provided")
    return sorted(set(vals))


def _active_ratio(images: np.ndarray, pixel_th: float) -> float:
    flat = images.reshape(images.shape[0], -1)
    return float((flat > pixel_th).mean())


def _sparsify_images(
    images: np.ndarray,
    drop_ratio: float,
    pixel_th: float,
    strategy: str,
    rng: np.random.Generator,
) -> np.ndarray:
    if drop_ratio <= 0.0:
        return images.copy()

    out = images.copy()
    n_img = out.shape[0]
    flat = out.reshape(n_img, -1)

    for i in range(n_img):
        row = flat[i]
        active = np.flatnonzero(row > pixel_th)
        n_active = int(active.size)
        if n_active == 0:
            continue
        keep = int(round((1.0 - drop_ratio) * n_active))
        keep = max(0, min(keep, n_active))

        if keep == n_active:
            continue
        if keep == 0:
            row[active] = 0.0
            continue

        if strategy == "topk":
            vals = row[active]
            idx_local = np.argpartition(vals, -keep)[-keep:]
            keep_idx = active[idx_local]
        else:
            keep_idx = rng.choice(active, size=keep, replace=False)

        drop_mask = np.ones(n_active, dtype=bool)
        pos = {int(v): j for j, v in enumerate(active.tolist())}
        for k in keep_idx.tolist():
            drop_mask[pos[int(k)]] = False
        row[active[drop_mask]] = 0.0

    return out


def _is_complete_result(result_json: Path, n_expected: int) -> bool:
    if not result_json.exists():
        return False
    try:
        d = json.loads(result_json.read_text(encoding="utf-8"))
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


def _run_inference(
    args: argparse.Namespace,
    weights_npz: Path,
    result_json: Path,
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
        str(weights_npz),
        "--n",
        str(args.n),
        "--packet-id-width",
        str(args.packet_id_width),
        "--assert-hls-reset",
        "--strict-identical",
        "--pl-clock-hz",
        str(int(args.pl_clock_hz)),
        "--output",
        str(result_json),
    ]
    if (not args.program_every_variant) and (not is_first_variant):
        cmd.append("--no-program")
    print("[RUN]", " ".join(cmd))
    if args.dry_run:
        return

    if args.resume and _is_complete_result(result_json, args.n):
        print(f"[RESUME] complete result exists, skip: {result_json}")
        return

    max_tries = max(1, int(args.max_retries) + 1)
    for attempt in range(1, max_tries + 1):
        try:
            subprocess.run(cmd, check=True)
            return
        except subprocess.CalledProcessError as e:
            if _is_complete_result(result_json, args.n):
                print(
                    f"[WARN] inference exited non-zero (rc={e.returncode}) but complete json exists; "
                    f"accepting result: {result_json}"
                )
                return
            if attempt >= max_tries:
                raise
            print(f"[RETRY] failed attempt {attempt}/{max_tries-1}, retrying variant ...")


def _load_metrics(path: Path) -> Dict[str, Optional[float]]:
    d = json.loads(path.read_text(encoding="utf-8"))
    return {
        "hw_acc_ttfs": float(d.get("hw_acc_ttfs", 0.0)),
        "sw_acc_ttfs": float(d.get("sw_acc_ttfs", 0.0)),
        "ms_per_image": float(d.get("ms_per_image", 0.0)),
        "strict_identical": bool(d.get("strict_identical", False)),
        "strict_failures_n": int(len(d.get("strict_failures", []))),
        "pl_service_cycles_mean": d.get("pl_service_cycles_mean"),
        "pl_service_ms_mean": d.get("pl_service_ms_mean"),
        "pl_service_tput_img_s": d.get("pl_service_tput_img_s"),
    }


def _to_md(rows: List[Dict[str, object]]) -> str:
    def fmt(v: object, nd: int = 4) -> str:
        if v is None:
            return "N/A"
        return f"{float(v):.{nd}f}"

    lines = [
        "# G19 Sparsity Sweep Summary",
        "",
        "| Drop Ratio | Active Ratio (before) | Active Ratio (after) | HW TTFS | strict_failures | PL service cyc | PL throughput (img/s) |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(
            f"| {float(r['drop_ratio']):.2f} | {float(r['active_ratio_before']):.4f} | "
            f"{float(r['active_ratio_after']):.4f} | "
            f"{fmt(r.get('hw_acc_ttfs'), 4)} | "
            f"{r.get('strict_failures_n', 'N/A')} | "
            f"{r.get('pl_service_cycles_mean', 'N/A')} | "
            f"{fmt(r.get('pl_service_tput_img_s'), 2)} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    levels = _parse_levels(args.sparsity_levels)
    out_dir = Path(args.out_dir)
    variant_dir = out_dir / "variants"
    result_dir = out_dir / "results"
    if not args.dry_run:
        variant_dir.mkdir(parents=True, exist_ok=True)
        result_dir.mkdir(parents=True, exist_ok=True)

    if not Path(args.base_npz).exists():
        raise SystemExit(f"Base deployment missing: {args.base_npz}")
    base = np.load(args.base_npz, allow_pickle=True)
    payload = {k: base[k] for k in base.files}

    if "test_imgs" not in payload:
        raise SystemExit(f"{args.base_npz} missing test_imgs")

    base_imgs = payload["test_imgs"].astype(np.float32)
    active_before = _active_ratio(base_imgs, args.pixel_threshold)
    rng = np.random.default_rng(args.seed)

    need_infer = (not args.skip_inference)
    if need_infer:
        if not args.inference_script:
            raise SystemExit("--inference-script is required unless --skip-inference")
        if not args.data_dir:
            raise SystemExit("--data-dir is required unless --skip-inference")

    rows: List[Dict[str, object]] = []

    for idx, drop in enumerate(levels):
        sparse_imgs = _sparsify_images(
            images=base_imgs,
            drop_ratio=drop,
            pixel_th=args.pixel_threshold,
            strategy=args.strategy,
            rng=rng,
        )
        active_after = _active_ratio(sparse_imgs, args.pixel_threshold)

        tag = f"s{int(round(drop * 100)):02d}"
        var_npz = variant_dir / f"mnist_10class_deployment_{tag}.npz"
        result_json = result_dir / f"mnist_10class_results_{tag}.json"

        payload_var = dict(payload)
        payload_var["test_imgs"] = sparse_imgs

        print(f"\n[VARIANT] drop={drop:.2f} -> {var_npz}")
        if not args.dry_run:
            np.savez_compressed(var_npz, **payload_var)

        row: Dict[str, object] = {
            "drop_ratio": drop,
            "variant_npz": str(var_npz),
            "active_ratio_before": active_before,
            "active_ratio_after": active_after,
        }

        if need_infer:
            _run_inference(args, var_npz, result_json, is_first_variant=(idx == 0))
            if not args.dry_run:
                row.update(_load_metrics(result_json))
                row["result_json"] = str(result_json)

        rows.append(row)

    if args.dry_run:
        return

    summary = {
        "config": {
            "base_npz": str(Path(args.base_npz).resolve()),
            "levels": levels,
            "pixel_threshold": args.pixel_threshold,
            "strategy": args.strategy,
            "seed": args.seed,
            "inference_enabled": need_infer,
            "inference_script": args.inference_script,
            "data_dir": args.data_dir,
            "n": args.n,
            "packet_id_width": args.packet_id_width,
            "pl_clock_hz": args.pl_clock_hz,
            "sudo": args.sudo,
        },
        "rows": rows,
    }

    summary_json = out_dir / "g19_sparsity_summary.json"
    summary_md = out_dir / "g19_sparsity_summary.md"
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md.write_text(_to_md(rows), encoding="utf-8")

    print(f"\nSaved: {summary_json}")
    print(f"Saved: {summary_md}")


if __name__ == "__main__":
    main()
