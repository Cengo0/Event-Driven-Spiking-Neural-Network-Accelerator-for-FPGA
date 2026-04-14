#!/usr/bin/env python3
"""Measure GPU INT8 ANN kernel baseline (quantized input/weights)."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import List, Optional

import numpy as np


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="GPU INT8 ANN kernel benchmark")
    p.add_argument("--deployment", required=True)
    p.add_argument("--n", type=int, default=10000)
    p.add_argument("--batch-size", type=int, default=2048)
    p.add_argument("--warmup", type=int, default=5)
    p.add_argument("--repeat", type=int, default=2000)
    p.add_argument("--input-scale", type=float, default=127.0)
    p.add_argument("--power-interval", type=float, default=0.05)
    p.add_argument("--idle-seconds", type=float, default=3.0)
    p.add_argument("--gpu-index", type=int, default=0)
    p.add_argument("--output", required=True)
    return p.parse_args()


def query_gpu_power_w(gpu_index: int) -> Optional[float]:
    cmd = ["nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits", "-i", str(gpu_index)]
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


def compile_bench(repo_root: Path, build_dir: Path) -> Path:
    src = repo_root / "scripts" / "gpu_ann_int8_kernel_bench.cu"
    bin_path = build_dir / "gpu_ann_int8_kernel_bench"
    subprocess.check_call(["nvcc", "-O3", "-std=c++17", str(src), "-o", str(bin_path)])
    return bin_path


def run_bench(bin_path: Path, imgs_i8_bin: Path, labels_bin: Path, weights_i8_bin: Path, n: int, nin: int, nneurons: int, fps: int, batch: int, warmup: int, repeat: int) -> dict:
    cmd = [
        str(bin_path),
        "--imgs-i8", str(imgs_i8_bin),
        "--labels", str(labels_bin),
        "--weights-i8", str(weights_i8_bin),
        "--n", str(n),
        "--nin", str(nin),
        "--nneurons", str(nneurons),
        "--fps", str(fps),
        "--batch", str(batch),
        "--warmup", str(warmup),
        "--repeat", str(repeat),
    ]
    return json.loads(subprocess.check_output(cmd, text=True).strip())


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    dep = np.load(args.deployment, allow_pickle=True)
    q_weights = dep["q_weights"].astype(np.int8)
    imgs = dep["test_imgs"]
    labels = dep["test_lbls"].astype(np.uint8)
    fps = int(dep.get("fps_per_class", 15))

    n = int(args.n) if args.n > 0 else int(len(imgs))
    imgs = imgs[:n].reshape(n, -1).astype(np.float32)
    labels = labels[:n]

    imgs_i8 = np.clip(np.round(imgs * args.input_scale), -128, 127).astype(np.int8)

    nin = int(imgs.shape[1])
    nneurons = int(q_weights.shape[0])

    print(f"GPU INT8 ANN kernel benchmark: n={n}, nin={nin}, nneurons={nneurons}, fps={fps}")

    with tempfile.TemporaryDirectory(prefix="gpu_ann_int8_") as td:
        td_path = Path(td)
        imgs_i8_bin = td_path / "imgs_i8.bin"
        labels_bin = td_path / "labels.bin"
        weights_i8_bin = td_path / "weights_i8.bin"

        imgs_i8.tofile(imgs_i8_bin)
        labels.tofile(labels_bin)
        q_weights.tofile(weights_i8_bin)

        bin_path = compile_bench(repo_root, td_path)

        print("Sampling idle GPU power ...")
        idle_samples = sample_power_window(args.gpu_index, args.idle_seconds, args.power_interval)
        idle_w = float(np.mean(idle_samples)) if idle_samples else None

        active_samples: List[float] = []
        stop_evt = threading.Event()
        t = threading.Thread(target=power_sampler_thread, args=(args.gpu_index, args.power_interval, stop_evt, active_samples), daemon=True)

        print("Running CUDA INT8 ANN kernel benchmark ...")
        t.start()
        infer = run_bench(
            bin_path=bin_path,
            imgs_i8_bin=imgs_i8_bin,
            labels_bin=labels_bin,
            weights_i8_bin=weights_i8_bin,
            n=n,
            nin=nin,
            nneurons=nneurons,
            fps=fps,
            batch=args.batch_size,
            warmup=args.warmup,
            repeat=args.repeat,
        )
        stop_evt.set()
        t.join(timeout=1.0)

    active_w = float(np.mean(active_samples)) if active_samples else None
    dynamic_w = (active_w - idle_w) if (active_w is not None and idle_w is not None) else None

    e2e_mj = (active_w * infer["ms_per_image"]) if active_w is not None else None
    dyn_mj = (dynamic_w * infer["ms_per_image"]) if dynamic_w is not None else None

    result = {
        "device": {
            "name": subprocess.check_output(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader", "-i", str(args.gpu_index)], text=True).strip(),
            "index": args.gpu_index,
        },
        "methodology": {
            "model_type": "ann_int8_baseline",
            "weights": "deployment_q_weights_int8",
            "inputs": f"quantized_int8_scale_{args.input_scale}",
            "topology": "784_to_150_linear_int8",
            "decision_rule": "argmax_neuron_then_class_group",
            "timing_scope": "gpu_inference_kernel_path",
            "implementation": "custom_cuda_kernel",
        },
        "config": {
            "deployment": str(Path(args.deployment).resolve()),
            "n": n,
            "batch_size": args.batch_size,
            "warmup": args.warmup,
            "repeat": args.repeat,
            "input_scale": args.input_scale,
            "power_interval_s": args.power_interval,
            "idle_seconds": args.idle_seconds,
        },
        "inference": {
            "n_images": int(infer["n_images"]),
            "correct": int(infer["correct"]),
            "acc_ann_int8": float(infer["acc_ann_int8"]),
            "elapsed_s": float(infer["elapsed_s"]),
            "repeat": int(infer.get("repeat", args.repeat)),
            "ms_per_image": float(infer["ms_per_image"]),
            "throughput_img_s": float(infer["throughput_img_s"]),
        },
        "power": {
            "idle_w": idle_w,
            "active_w": active_w,
            "dynamic_w": dynamic_w,
            "idle_samples_n": len(idle_samples),
            "active_samples_n": len(active_samples),
        },
        "energy": {
            "e2e_mj_per_img": e2e_mj,
            "dynamic_mj_per_img": dyn_mj,
        },
    }

    print("\n=== GPU INT8 ANN Kernel Metrics ===")
    print(f"acc_ann_int8: {result['inference']['acc_ann_int8']*100:.2f}%")
    print(f"ms_per_image: {result['inference']['ms_per_image']:.9f}")
    print(f"throughput_img_s: {result['inference']['throughput_img_s']:.2f}")
    print(f"power_active_w: {result['power']['active_w']}")
    print(f"power_idle_w: {result['power']['idle_w']}")
    print(f"energy_dynamic_mj_per_img: {result['energy']['dynamic_mj_per_img']}")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
