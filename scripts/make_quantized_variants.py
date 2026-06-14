#!/usr/bin/env python3
"""Create quantized deployment NPZ variants (e.g., 8/4/2-bit) for ablation runs.

Input NPZ must contain at least:
- q_weights (int8, shape [n_neurons, 784])

All other fields are copied through unchanged.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import numpy as np


def quantize_int8_to_nbit(weights_int8: np.ndarray, bits: int) -> np.ndarray:
    if bits < 2 or bits > 8:
        raise ValueError(f"bits must be in [2, 8], got {bits}")
    if bits == 8:
        return weights_int8.astype(np.int8, copy=True)

    qmax = (1 << (bits - 1)) - 1
    # Map int8 [-127,127] -> n-bit codebook [-qmax, qmax], then back to int8 range.
    scale = 127.0 / float(qmax)
    nbit = np.clip(np.round(weights_int8.astype(np.float32) / scale), -qmax, qmax)
    back_to_int8 = np.clip(np.round(nbit * scale), -127, 127).astype(np.int8)
    return back_to_int8


def summarize(weights: np.ndarray) -> Dict[str, float]:
    unique = np.unique(weights)
    return {
        "min": int(weights.min()),
        "max": int(weights.max()),
        "nonzero_frac": float(np.count_nonzero(weights) / weights.size),
        "unique_values": int(unique.size),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate quantized deployment variants for ablation")
    p.add_argument(
        "--base-npz",
        required=True,
        help="Base deployment npz (typically mnist_10class_deployment.npz)",
    )
    p.add_argument(
        "--bits",
        default="8,4,2",
        help="Comma-separated bit-width list (default: 8,4,2)",
    )
    p.add_argument(
        "--out-dir",
        required=True,
        help="Directory to write generated npz variants",
    )
    p.add_argument(
        "--prefix",
        default="mnist_10class_deployment",
        help="Output filename prefix (default: mnist_10class_deployment)",
    )
    p.add_argument(
        "--summary-json",
        default="",
        help="Optional summary json output path",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    base_path = Path(args.base_npz)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    bits: List[int] = []
    for tok in args.bits.split(","):
        tok = tok.strip()
        if not tok:
            continue
        bits.append(int(tok))
    bits = sorted(set(bits), reverse=True)
    if not bits:
        raise SystemExit("No valid bits provided")

    data = np.load(base_path, allow_pickle=True)
    if "q_weights" not in data:
        raise SystemExit(f"{base_path} missing 'q_weights'")

    q_weights = data["q_weights"].astype(np.int8)
    summary: Dict[str, Dict[str, float]] = {
        "base": summarize(q_weights),
        "outputs": {},
    }

    keys = list(data.keys())
    payload = {k: data[k] for k in keys if k != "q_weights"}

    print(f"Base: {base_path}")
    print(f"  q_weights shape={q_weights.shape} range=[{q_weights.min()}, {q_weights.max()}]")

    for b in bits:
        q_b = quantize_int8_to_nbit(q_weights, b)
        out_path = out_dir / f"{args.prefix}_q{b}.npz"

        np.savez_compressed(
            out_path,
            q_weights=q_b,
            quant_bits=np.array(b, dtype=np.int32),
            quant_from=np.array(str(base_path), dtype=object),
            **payload,
        )

        s = summarize(q_b)
        summary["outputs"][f"q{b}"] = {
            "path": str(out_path),
            **s,
        }

        print(
            f"  q{b}: saved {out_path.name} "
            f"range=[{s['min']}, {s['max']}] nz={s['nonzero_frac']:.4f} unique={s['unique_values']}"
        )

    if args.summary_json:
        summary_path = Path(args.summary_json)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
