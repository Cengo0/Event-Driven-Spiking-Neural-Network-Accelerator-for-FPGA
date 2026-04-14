#!/usr/bin/env python3
"""Measure GPU latency/energy for ANN-equivalent MNIST inference.

This uses the same deployment NPZ used by FPGA inference:
- q_weights (int8, shape [150,784])
- test_imgs, test_lbls

Inference rule (matches SW/FPGA TTFS decision semantics):
- potential[j] = sum_{active pixel i} max(q_weights[j,i], 0)
- first-spike class = argmax(potential) // fps_per_class, with 0 when all zero

Modeling note:
- This is not a time-stepped SNN simulation.
- It is an ANN-equivalent inference path using the same deployment weights and
  the same decision rule used by the FPGA parity reference.

Power is sampled via nvidia-smi power.draw (W).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import threading
import time
from pathlib import Path
from typing import List, Optional

import numpy as np
import torch


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="GPU latency/energy measurement for ANN-equivalent MNIST inference")
    p.add_argument("--deployment", required=True, help="Path to mnist_10class_deployment.npz")
    p.add_argument("--n", type=int, default=10000, help="Number of images")
    p.add_argument("--batch-size", type=int, default=1024, help="GPU batch size")
    p.add_argument("--pixel-th", type=float, default=0.3, help="Pixel activation threshold")
    p.add_argument("--warmup", type=int, default=3, help="Warmup iterations")
    p.add_argument("--power-interval", type=float, default=0.05, help="Power sampling interval (seconds)")
    p.add_argument("--idle-seconds", type=float, default=3.0, help="Idle power sampling duration (seconds)")
    p.add_argument("--gpu-index", type=int, default=0, help="GPU index for nvidia-smi query")
    p.add_argument("--output", default="", help="Output JSON path")
    return p.parse_args()


def query_gpu_power_w(gpu_index: int) -> Optional[float]:
    cmd = [
        "nvidia-smi",
        "--query-gpu=power.draw",
        "--format=csv,noheader,nounits",
        "-i",
        str(gpu_index),
    ]
    try:
        out = subprocess.check_output(cmd, text=True, timeout=2.0).strip().splitlines()[0]
        return float(out)
    except Exception:
        return None


def sample_power_window(gpu_index: int, duration_s: float, interval_s: float) -> List[float]:
    samples: List[float] = []
    t_end = time.time() + duration_s
    while time.time() < t_end:
        p = query_gpu_power_w(gpu_index)
        if p is not None:
            samples.append(p)
        time.sleep(max(interval_s, 0.01))
    return samples


def power_sampler_thread(gpu_index: int, interval_s: float, stop_evt: threading.Event, sink: List[float]) -> None:
    while not stop_evt.is_set():
        p = query_gpu_power_w(gpu_index)
        if p is not None:
            sink.append(p)
        time.sleep(max(interval_s, 0.01))


def run_gpu_inference(
    imgs: np.ndarray,
    labels: np.ndarray,
    q_weights: np.ndarray,
    fps_per_class: int,
    pixel_th: float,
    batch_size: int,
    warmup: int,
) -> dict:
    device = torch.device("cuda")

    # Positive-only contribution (matches SW/FPGA semantics)
    w_pos = np.maximum(q_weights.astype(np.int16), 0).astype(np.float32)
    w_t = torch.from_numpy(w_pos).to(device=device, dtype=torch.float32, non_blocking=True)

    x = imgs.reshape(imgs.shape[0], -1).astype(np.float32)
    y = labels.astype(np.int64)

    # Warmup
    with torch.inference_mode():
        for _ in range(max(warmup, 0)):
            xb = torch.from_numpy(x[: min(batch_size, x.shape[0])]).to(device=device, dtype=torch.float32, non_blocking=True)
            ab = (xb > pixel_th).to(dtype=torch.float32)
            pot = ab @ w_t.T
            _ = torch.argmax(pot, dim=1)
        torch.cuda.synchronize()

    preds: List[np.ndarray] = []
    t0 = time.perf_counter()
    with torch.inference_mode():
        for s in range(0, x.shape[0], batch_size):
            e = min(s + batch_size, x.shape[0])
            xb = torch.from_numpy(x[s:e]).to(device=device, dtype=torch.float32, non_blocking=True)
            ab = (xb > pixel_th).to(dtype=torch.float32)
            pot = ab @ w_t.T
            best = torch.argmax(pot, dim=1)
            maxv = torch.max(pot, dim=1).values
            # If all-zero potential, match SW fallback: neuron 0 -> class 0
            best = torch.where(maxv > 0, best, torch.zeros_like(best))
            cls = (best // fps_per_class).to(dtype=torch.int64)
            preds.append(cls.cpu().numpy())
        torch.cuda.synchronize()
    t1 = time.perf_counter()

    pred = np.concatenate(preds, axis=0)
    correct = int((pred == y).sum())
    n = int(x.shape[0])

    elapsed_s = t1 - t0
    ms_per_img = (elapsed_s / n) * 1000.0 if n > 0 else 0.0

    return {
        "n_images": n,
        "correct": correct,
        "acc_ttfs": float(correct / n) if n > 0 else 0.0,
        "elapsed_s": elapsed_s,
        "ms_per_image": ms_per_img,
        "throughput_img_s": float(n / elapsed_s) if elapsed_s > 0 else 0.0,
    }


def main() -> None:
    args = parse_args()

    if not torch.cuda.is_available():
        raise SystemExit("CUDA GPU not available")

    dep = np.load(args.deployment, allow_pickle=True)
    q_weights = dep["q_weights"].astype(np.int8)
    imgs = dep["test_imgs"]
    labels = dep["test_lbls"]
    fps_per_class = int(dep.get("fps_per_class", 15))

    n = int(args.n) if args.n > 0 else int(len(imgs))
    imgs = imgs[:n]
    labels = labels[:n]

    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Images: {n}, batch={args.batch_size}, pixel_th={args.pixel_th}")

    print("Sampling idle GPU power ...")
    idle_samples = sample_power_window(args.gpu_index, args.idle_seconds, args.power_interval)
    idle_w = float(np.mean(idle_samples)) if idle_samples else None

    stop_evt = threading.Event()
    active_samples: List[float] = []
    t = threading.Thread(
        target=power_sampler_thread,
        args=(args.gpu_index, args.power_interval, stop_evt, active_samples),
        daemon=True,
    )

    print("Running GPU inference ...")
    t.start()
    infer = run_gpu_inference(
        imgs=imgs,
        labels=labels,
        q_weights=q_weights,
        fps_per_class=fps_per_class,
        pixel_th=args.pixel_th,
        batch_size=args.batch_size,
        warmup=args.warmup,
    )
    stop_evt.set()
    t.join(timeout=1.0)

    active_w = float(np.mean(active_samples)) if active_samples else None
    dyn_w = (active_w - idle_w) if (active_w is not None and idle_w is not None) else None

    e2e_mj = (active_w * infer["ms_per_image"]) if active_w is not None else None
    dyn_mj = (dyn_w * infer["ms_per_image"]) if dyn_w is not None else None

    result = {
        "device": {
            "name": torch.cuda.get_device_name(0),
            "index": args.gpu_index,
        },
        "methodology": {
            "model_type": "ann_equivalent",
            "topology": "784_to_150_linear_positive_accumulation",
            "decision_rule": "argmax_potential_then_class_group",
            "timing_scope": "gpu_inference_kernel_path",
        },
        "config": {
            "deployment": str(Path(args.deployment).resolve()),
            "n": n,
            "batch_size": args.batch_size,
            "pixel_th": args.pixel_th,
            "warmup": args.warmup,
            "power_interval_s": args.power_interval,
            "idle_seconds": args.idle_seconds,
        },
        "inference": infer,
        "power": {
            "idle_w": idle_w,
            "active_w": active_w,
            "dynamic_w": dyn_w,
            "idle_samples_n": len(idle_samples),
            "active_samples_n": len(active_samples),
        },
        "energy": {
            "e2e_mj_per_img": e2e_mj,
            "dynamic_mj_per_img": dyn_mj,
        },
    }

    print("\n=== GPU Metrics ===")
    print(f"acc_ttfs: {infer['acc_ttfs']*100:.2f}%")
    print(f"ms_per_image: {infer['ms_per_image']:.4f}")
    print(f"throughput_img_s: {infer['throughput_img_s']:.2f}")
    print(f"power_active_w: {active_w}")
    print(f"power_idle_w: {idle_w}")
    print(f"energy_e2e_mj_per_img: {e2e_mj}")
    print(f"energy_dynamic_mj_per_img: {dyn_mj}")

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Saved: {out}")


if __name__ == "__main__":
    main()
