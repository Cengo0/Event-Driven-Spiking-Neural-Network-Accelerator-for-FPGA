#!/usr/bin/env python3
"""
Prepare 10-class MNIST Deployment Package for FPGA
====================================================
Runs on the HOST machine (GPU/CPU with PyTorch + torchvision).

Loads the FaithfulOnChipTrainer model (data/cache/onchip_faithful_model_150n.npz),
quantises weights to int8, loads 10,000 MNIST test images, and saves a single
deployment .npz ready to be SCP'd to the PYNQ board.

Usage:
    python3 tests/prepare_10class_deployment.py
    # Then copy to board:
    scp data/cache/mnist_10class_deployment.npz xilinx@192.168.0.40:/home/xilinx/snn/

Output:
    data/cache/mnist_10class_deployment.npz
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────

MODEL_PATH  = 'data/cache/onchip_faithful_model_150n.npz'
OUTPUT_PATH = 'data/cache/mnist_10class_deployment.npz'

N_CLASSES      = 10
FPS_PER_CLASS  = 15   # features (output neurons) per class
N_NEURONS      = N_CLASSES * FPS_PER_CLASS   # 150

# Weight scale: float → int8
# FaithfulOnChipTrainer uses SCALE=127 internally, so weights are already
# in [0,1] range after normalisation. Multiply by 127 → int8 [0,127].
WEIGHT_SCALE   = 127.0

# For pixel threshold: MNIST pixels in [0,1]; pixels > 0.3 treated as active.
PIXEL_THRESHOLD = 0.3


# ─────────────────────────────────────────────────────────────────────
# Load model
# ─────────────────────────────────────────────────────────────────────

print(f"Loading model: {MODEL_PATH}")
if not os.path.exists(MODEL_PATH):
    print(f"ERROR: {MODEL_PATH} not found.")
    print("Run tests/experiment_full_comparison.py or tests/onchip_stdp_faithful.py first.")
    sys.exit(1)

saved = np.load(MODEL_PATH, allow_pickle=True)
print(f"  Keys: {list(saved.keys())}")

weights    = saved['weights'].astype(np.float32)   # (150, 784)
thresholds = saved['thresholds'].astype(np.float32) # (150,)  or scalar

if weights.ndim != 2 or weights.shape[0] != N_NEURONS or weights.shape[1] != 784:
    print(f"ERROR: unexpected weight shape {weights.shape}, expected ({N_NEURONS}, 784)")
    sys.exit(1)

print(f"  Weights: {weights.shape}  [{weights.min():.4f}, {weights.max():.4f}]")
print(f"  Thresholds: {thresholds.shape}  [{thresholds.min():.4f}, {thresholds.max():.4f}]")

# Compute hardware threshold (mean threshold → single int for fixed HW register)
hw_threshold = int(round(float(np.mean(thresholds))))
print(f"  HW threshold (mean): {hw_threshold}")

# Quantise weights to int8
q_weights = np.clip(np.round(weights * WEIGHT_SCALE), -127, 127).astype(np.int8)
print(f"  Quantised weights: {q_weights.shape}  [{q_weights.min()}, {q_weights.max()}]")

# Quick sanity: zero-weight fraction
zero_frac = (q_weights == 0).mean()
print(f"  Zero-weight fraction: {zero_frac:.2%}")


# ─────────────────────────────────────────────────────────────────────
# Load MNIST test set
# ─────────────────────────────────────────────────────────────────────

print("\nLoading MNIST test set ...")

try:
    from torchvision import datasets, transforms
    import torch

    test_ds = datasets.MNIST('./data', train=False, download=True,
                             transform=transforms.ToTensor())
    test_imgs = np.stack([img.squeeze(0).numpy() for img, _ in test_ds])  # (10000,28,28)
    test_lbls = np.array([lbl for _, lbl in test_ds], dtype=np.int64)
    print(f"  Loaded via torchvision: {test_imgs.shape}, dtype={test_imgs.dtype}")

except ImportError:
    # Fallback: load from cached .pt files if torchvision unavailable
    cache_test = 'data/cache/mnist_rstdp_test_10class.pt'
    if os.path.exists(cache_test):
        import torch
        td = torch.load(cache_test)
        test_imgs = td['images'].numpy()
        test_lbls = td['labels'].numpy().astype(np.int64)
        print(f"  Loaded from cache: {test_imgs.shape}")
    else:
        print("ERROR: Cannot load MNIST test set. Install torchvision or run precache script.")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────
# SW accuracy check (verify the quantised weights still work)
# ─────────────────────────────────────────────────────────────────────

print("\nVerifying quantised weight accuracy (SW only) ...")

correct = 0
N_CHECK = min(1000, len(test_imgs))
for i in range(N_CHECK):
    img  = test_imgs[i].flatten()
    lbl  = int(test_lbls[i])
    active = np.where(img > PIXEL_THRESHOLD)[0]

    potentials = np.zeros(N_NEURONS, dtype=np.int64)
    fired      = np.zeros(N_NEURONS, dtype=bool)
    for ii in active:
        col = q_weights[:, ii].astype(np.int64)
        mask = (col > 0) & ~fired
        potentials[mask] += col[mask]
        new_fires = mask & (potentials >= hw_threshold)
        fired |= new_fires

    group_sums = np.array([
        potentials[c*FPS_PER_CLASS:(c+1)*FPS_PER_CLASS].sum()
        for c in range(N_CLASSES)
    ])
    pred = int(np.argmax(group_sums))
    if pred == lbl:
        correct += 1

sw_acc = correct / N_CHECK * 100
print(f"  SW accuracy (int8, N={N_CHECK}): {correct}/{N_CHECK} = {sw_acc:.1f}%")

if sw_acc < 60.0:
    print("WARNING: accuracy < 60% — check WEIGHT_SCALE and model path")
elif sw_acc >= 80.0:
    print("  → Acceptable for FPGA deployment")


# ─────────────────────────────────────────────────────────────────────
# Save deployment package
# ─────────────────────────────────────────────────────────────────────

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

np.savez_compressed(
    OUTPUT_PATH,
    q_weights     = q_weights,
    thresholds    = thresholds,
    test_imgs     = test_imgs,
    test_lbls     = test_lbls,
    hw_threshold  = np.array(hw_threshold, dtype=np.int32),
    weight_scale  = np.array(WEIGHT_SCALE, dtype=np.float32),
    n_classes     = np.array(N_CLASSES, dtype=np.int32),
    fps_per_class = np.array(FPS_PER_CLASS, dtype=np.int32),
    sw_accuracy   = np.array(sw_acc, dtype=np.float32),
    pixel_threshold = np.array(PIXEL_THRESHOLD, dtype=np.float32),
)

size_mb = os.path.getsize(OUTPUT_PATH) / 1e6
print(f"\nSaved: {OUTPUT_PATH}  ({size_mb:.1f} MB)")
print("\nNext steps:")
print(f"  scp {OUTPUT_PATH} xilinx@192.168.0.40:/home/xilinx/snn/")
print(f"  scp outputs/snn_integrated.bit xilinx@192.168.0.40:/home/xilinx/snn/snn_integrated_v2.bit")
print(f"  scp tests/fpga_10class_inference.py xilinx@192.168.0.40:/home/xilinx/snn/")
print(f"  ssh xilinx@192.168.0.40 'cd /home/xilinx/snn && sudo python3 fpga_10class_inference.py'")
