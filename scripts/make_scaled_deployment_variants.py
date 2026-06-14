#!/usr/bin/env python3
"""Generate neuron-scaled deployment NPZ variants from a base deployment file.

This script is intended for rapid G15 execution bootstrap. It keeps dataset,
threshold, and metadata compatible with `tests/fpga_10class_inference.py`,
and only changes the per-class neuron count by truncation/tiling per class.

For paper-final claims, prefer retrained variants (not tiled variants).
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create scaled deployment NPZ variants")
    p.add_argument(
        "--base-npz",
        required=True,
        help="Base deployment npz (e.g., /home/xilinx/snn/mnist_10class_deployment.npz)",
    )
    p.add_argument(
        "--target-neurons",
        default="150,300,600",
        help="Comma-separated total output neurons (must be divisible by n_classes)",
    )
    p.add_argument(
        "--out-dir",
        required=True,
        help="Output directory for generated variants",
    )
    p.add_argument(
        "--prefix",
        default="mnist_10class_deployment",
        help="Output filename prefix",
    )
    p.add_argument(
        "--summary-json",
        default="",
        help="Optional summary json output path",
    )
    return p.parse_args()


def _parse_targets(raw: str) -> List[int]:
    vals = sorted({int(x.strip()) for x in raw.split(",") if x.strip()})
    if not vals:
        raise SystemExit("No valid targets parsed from --target-neurons")
    if any(v <= 0 for v in vals):
        raise SystemExit("All --target-neurons values must be > 0")
    return vals


def _slice_or_tile_per_class(
    q_weights: np.ndarray,
    thresholds: np.ndarray,
    n_classes: int,
    target_fpc: int,
) -> Tuple[np.ndarray, np.ndarray]:
    base_n = int(q_weights.shape[0])
    base_fpc = base_n // n_classes
    out_w: List[np.ndarray] = []
    out_t: List[np.ndarray] = []

    for c in range(n_classes):
        s = c * base_fpc
        e = (c + 1) * base_fpc
        w_c = q_weights[s:e]
        t_c = thresholds[s:e]

        if target_fpc <= base_fpc:
            out_w.append(w_c[:target_fpc].copy())
            out_t.append(t_c[:target_fpc].copy())
        else:
            reps = target_fpc // base_fpc
            rem = target_fpc % base_fpc
            w_parts = [w_c.copy() for _ in range(reps)]
            t_parts = [t_c.copy() for _ in range(reps)]
            if rem > 0:
                w_parts.append(w_c[:rem].copy())
                t_parts.append(t_c[:rem].copy())
            out_w.append(np.concatenate(w_parts, axis=0))
            out_t.append(np.concatenate(t_parts, axis=0))

    return np.concatenate(out_w, axis=0), np.concatenate(out_t, axis=0)


def _save_npz_atomic(out_path: Path, payload: Dict[str, np.ndarray]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Use a real .npz temp path so np.savez writes to this exact file name
    # (avoids suffix auto-append corner cases).
    fd, tmp_name = tempfile.mkstemp(prefix=out_path.stem + ".", suffix=".npz", dir=str(out_path.parent))
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        np.savez(tmp_path, **payload)
        os.replace(str(tmp_path), str(out_path))
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _verify_variant_npz(path: Path, n_out: int, n_classes: int, fpc_t: int) -> None:
    try:
        with np.load(path, allow_pickle=True) as chk:
            # Force full read of large payload to catch CRC issues early.
            _ = np.asarray(chk["test_imgs"])
            _ = np.asarray(chk["test_lbls"])
            qw = np.asarray(chk["q_weights"])
            th = np.asarray(chk["thresholds"])
            n_output = int(chk["n_output"])
            n_classes_chk = int(chk.get("n_classes", n_classes))
            fps_chk = int(chk.get("fps_per_class", fpc_t))
    except Exception as e:
        raise SystemExit(f"Variant integrity check failed: {path} ({e})")

    if qw.shape[0] != n_out or th.shape[0] != n_out:
        raise SystemExit(
            f"Variant shape mismatch: {path} q_weights={qw.shape[0]}, thresholds={th.shape[0]}, expected={n_out}"
        )
    if n_output != n_out:
        raise SystemExit(f"Variant n_output mismatch: {path} n_output={n_output}, expected={n_out}")
    if n_classes_chk != n_classes:
        raise SystemExit(f"Variant n_classes mismatch: {path} n_classes={n_classes_chk}, expected={n_classes}")
    if fps_chk != fpc_t:
        raise SystemExit(f"Variant fps_per_class mismatch: {path} fps={fps_chk}, expected={fpc_t}")


def main() -> None:
    args = parse_args()
    base_path = Path(args.base_npz)
    if not base_path.exists():
        raise SystemExit(f"Base deployment not found: {base_path}")

    targets = _parse_targets(args.target_neurons)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    base = np.load(base_path, allow_pickle=True)
    q_weights = np.asarray(base["q_weights"])
    thresholds = np.asarray(base["thresholds"])

    n_classes = int(base.get("n_classes", 10))
    fps_per_class = int(base.get("fps_per_class", max(1, q_weights.shape[0] // n_classes)))
    base_n = int(q_weights.shape[0])

    if base_n % n_classes != 0:
        raise SystemExit(f"Base q_weights rows ({base_n}) must be divisible by n_classes ({n_classes})")
    if thresholds.shape[0] != base_n:
        raise SystemExit(
            f"Threshold length mismatch: thresholds={thresholds.shape[0]}, q_weights={base_n}"
        )

    rows: List[Dict[str, object]] = []
    for n_out in targets:
        if n_out % n_classes != 0:
            raise SystemExit(
                f"Target neurons {n_out} not divisible by n_classes={n_classes}"
            )
        fpc_t = n_out // n_classes

        qw_t, th_t = _slice_or_tile_per_class(
            q_weights=q_weights,
            thresholds=thresholds,
            n_classes=n_classes,
            target_fpc=fpc_t,
        )

        out_path = out_dir / f"{args.prefix}_{n_out}n.npz"
        payload = {k: base[k] for k in base.files if k not in ("q_weights", "thresholds", "fps_per_class", "n_output")}
        payload["q_weights"] = qw_t.astype(np.int8, copy=False)
        payload["thresholds"] = th_t.astype(np.float32, copy=False)
        payload["fps_per_class"] = np.array(fpc_t, dtype=np.int32)
        payload["n_output"] = np.array(n_out, dtype=np.int32)
        payload["n_classes"] = np.array(n_classes, dtype=np.int32)

        _save_npz_atomic(out_path, payload)
        _verify_variant_npz(out_path, n_out=n_out, n_classes=n_classes, fpc_t=fpc_t)

        rows.append(
            {
                "target_neurons": n_out,
                "fps_per_class": fpc_t,
                "path": str(out_path),
                "source_mode": (
                    "copy" if n_out == base_n else
                    ("truncate_per_class" if fpc_t < fps_per_class else "tile_per_class")
                ),
            }
        )
        print(f"[OK] {n_out}n -> {out_path}")

    summary = {
        "base_npz": str(base_path),
        "base_neurons": base_n,
        "base_fps_per_class": fps_per_class,
        "n_classes": n_classes,
        "targets": rows,
    }

    summary_path = Path(args.summary_json) if args.summary_json else (out_dir / "g15_variant_generation_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Saved: {summary_path}")


if __name__ == "__main__":
    main()
