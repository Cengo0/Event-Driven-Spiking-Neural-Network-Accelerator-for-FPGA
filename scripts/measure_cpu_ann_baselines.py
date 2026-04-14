#!/usr/bin/env python3
"""Measure CPU ANN baselines (FP32 / INT8) on the same deployment artifact."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CPU ANN baseline benchmark")
    p.add_argument("--deployment", required=True)
    p.add_argument("--n", type=int, default=10000)
    p.add_argument("--repeat", type=int, default=50)
    p.add_argument("--input-scale", type=float, default=127.0)
    p.add_argument("--output", required=True)
    return p.parse_args()


def bench_fp32(imgs: np.ndarray, labels: np.ndarray, w_fp32: np.ndarray, fps: int, repeat: int) -> dict:
    # warmup
    _ = np.argmax(imgs[:256] @ w_fp32.T, axis=1)

    t0 = time.perf_counter()
    pred = None
    for _ in range(max(1, repeat)):
        score = imgs @ w_fp32.T
        pred = np.argmax(score, axis=1) // fps
    t1 = time.perf_counter()

    assert pred is not None
    correct = int((pred == labels).sum())
    elapsed_s = t1 - t0
    ms_per_img = (elapsed_s * 1000.0) / (len(imgs) * max(1, repeat))
    throughput = (len(imgs) * max(1, repeat)) / elapsed_s if elapsed_s > 0 else 0.0

    return {
        "correct": correct,
        "acc_ann_fp32": float(correct / len(imgs)),
        "elapsed_s": float(elapsed_s),
        "ms_per_image": float(ms_per_img),
        "throughput_img_s": float(throughput),
    }


def bench_int8(imgs_i8: np.ndarray, labels: np.ndarray, w_i8: np.ndarray, fps: int, repeat: int) -> dict:
    x = imgs_i8.astype(np.int32)
    w = w_i8.astype(np.int32)

    # warmup
    _ = np.argmax(x[:256] @ w.T, axis=1)

    t0 = time.perf_counter()
    pred = None
    for _ in range(max(1, repeat)):
        score = x @ w.T
        pred = np.argmax(score, axis=1) // fps
    t1 = time.perf_counter()

    assert pred is not None
    correct = int((pred == labels).sum())
    elapsed_s = t1 - t0
    ms_per_img = (elapsed_s * 1000.0) / (len(imgs_i8) * max(1, repeat))
    throughput = (len(imgs_i8) * max(1, repeat)) / elapsed_s if elapsed_s > 0 else 0.0

    return {
        "correct": correct,
        "acc_ann_int8": float(correct / len(imgs_i8)),
        "elapsed_s": float(elapsed_s),
        "ms_per_image": float(ms_per_img),
        "throughput_img_s": float(throughput),
    }


def main() -> None:
    args = parse_args()

    dep = np.load(args.deployment, allow_pickle=True)
    q_weights = dep["q_weights"].astype(np.int8)
    weight_scale = float(dep["weight_scale"])

    imgs = dep["test_imgs"]
    labels = dep["test_lbls"].astype(np.int64)
    fps = int(dep.get("fps_per_class", 15))

    n = int(args.n) if args.n > 0 else int(len(imgs))
    imgs = imgs[:n].reshape(n, -1).astype(np.float32)
    labels = labels[:n]

    w_fp32 = q_weights.astype(np.float32) / weight_scale
    imgs_i8 = np.clip(np.round(imgs * args.input_scale), -128, 127).astype(np.int8)

    fp32 = bench_fp32(imgs, labels, w_fp32, fps=fps, repeat=args.repeat)
    int8 = bench_int8(imgs_i8, labels, q_weights, fps=fps, repeat=args.repeat)

    result = {
        "methodology": {
            "model": "ann_baseline_cpu",
            "topology": "784_to_150_linear",
            "decision_rule": "argmax_neuron_then_class_group",
            "timing_scope": "cpu_compute_path",
            "repeat": args.repeat,
        },
        "config": {
            "deployment": str(Path(args.deployment).resolve()),
            "n": n,
            "input_scale": args.input_scale,
        },
        "fp32": fp32,
        "int8": int8,
    }

    print("=== CPU ANN Baselines ===")
    print(f"FP32 acc: {fp32['acc_ann_fp32']*100:.2f}%  ms/img: {fp32['ms_per_image']:.6f}  tput: {fp32['throughput_img_s']:.2f}")
    print(f"INT8 acc: {int8['acc_ann_int8']*100:.2f}%  ms/img: {int8['ms_per_image']:.6f}  tput: {int8['throughput_img_s']:.2f}")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
