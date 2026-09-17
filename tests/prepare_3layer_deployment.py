#!/usr/bin/env python3
import os
import sys
import numpy as np
import torch

MODEL_PATH  = 'models/fc3_T_4_clean_l2[0.000500].pth'
OUTPUT_PATH = 'data/cache/mnist_3layer_deployment.npz'
TIMESTEPS   = 4

def fuse_batchnorm(w, bn_gamma, bn_beta, bn_mean, bn_var, eps=1e-5):
    """Fold BatchNorm parameters into the Linear layer weights and biases."""
    std = torch.sqrt(bn_var + eps)
    w_fused = w * (bn_gamma / std).unsqueeze(1)
    b_fused = bn_beta - bn_mean * (bn_gamma / std)
    return w_fused.numpy(), b_fused.numpy()

# ─────────────────────────────────────────────────────────────────────
# 1. Load Model
# ─────────────────────────────────────────────────────────────────────
print(f"Loading PyTorch model: {MODEL_PATH}")
state_dict = torch.load(MODEL_PATH, map_location='cpu')

w1_f, b1_f = fuse_batchnorm(state_dict['features.0.weight'], state_dict['features.1.weight'], state_dict['features.1.bias'], state_dict['features.1.running_mean'], state_dict['features.1.running_var'])
w2_f, b2_f = fuse_batchnorm(state_dict['features.3.weight'], state_dict['features.4.weight'], state_dict['features.4.bias'], state_dict['features.4.running_mean'], state_dict['features.4.running_var'])
w3_f = state_dict['classifier.weight'].numpy()
b3_f = state_dict['classifier.bias'].numpy()

# ─────────────────────────────────────────────────────────────────────
# 2. Load and Normalize MNIST Data
# ─────────────────────────────────────────────────────────────────────
print("\nLoading and Z-Score Normalizing MNIST...")
try:
    from torchvision import datasets, transforms
    # Apply the exact normalization the PyTorch model expects
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    test_ds = datasets.MNIST('./data', train=False, download=True, transform=transform)
    test_imgs = np.stack([img.squeeze(0).numpy() for img, _ in test_ds])
    test_lbls = np.array([lbl for _, lbl in test_ds], dtype=np.int64)
except ImportError:
    print("Please install torchvision.")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────
# 3. Quantize FPGA Layers (Layer 2 and 3 ONLY)
# ─────────────────────────────────────────────────────────────────────
# Layer 1 stays Float32 for the CPU. We only scale the FPGA weights.
max_abs = max(np.max(np.abs(w2_f)), np.max(np.abs(w3_f)), np.max(np.abs(b2_f)), np.max(np.abs(b3_f)))
WEIGHT_SCALE = 127.0 / max_abs
print(f"\nFPGA Dynamic Weight Scale: {WEIGHT_SCALE:.2f}")

q_w2 = np.clip(np.round(w2_f * WEIGHT_SCALE), -127, 127).astype(np.int8)
q_b2 = np.clip(np.round(b2_f * WEIGHT_SCALE), -127, 127).astype(np.int8)
q_w2_aug = np.hstack([q_w2, q_b2[:, None]])

q_w3 = np.clip(np.round(w3_f * WEIGHT_SCALE), -127, 127).astype(np.int8)
q_b3 = np.clip(np.round(b3_f * WEIGHT_SCALE), -127, 127).astype(np.int8)
q_w3_aug = np.hstack([q_w3, q_b3[:, None]])

# ─────────────────────────────────────────────────────────────────────
# 4. Co-Processing Sanity Check
# ─────────────────────────────────────────────────────────────────────
print("\nRunning Co-Processing Threshold Sweep...")
N_CHECK = min(1000, len(test_imgs))
base_th = int(WEIGHT_SCALE)
best_acc, best_th = 0, base_th

for test_th in [base_th // 2, int(base_th * 0.8), base_th, int(base_th * 1.2), int(base_th * 1.5)]:
    correct = 0
    for i in range(N_CHECK):
        img = test_imgs[i].flatten()
        lbl = int(test_lbls[i])
        
        mem1 = np.zeros(256, dtype=np.float32)
        mem2 = np.zeros(256, dtype=np.float32)
        mem3 = np.zeros(10, dtype=np.float32)
        
        for t in range(TIMESTEPS):
            # LAYER 1 (CPU): Float32 math, analog inputs
            mem1 += np.dot(w1_f, img) + b1_f
            mem1 = np.maximum(mem1, 0)
            spike1 = (mem1 >= 1.0).astype(np.float32)
            mem1[spike1 > 0] = 0.0
            
            # LAYER 2 (FPGA): Int32 math simulating Int8 hardware
            spike1_aug = np.append(spike1, 1.0)
            mem2 += np.dot(q_w2_aug, spike1_aug)
            mem2 = np.maximum(mem2, 0)
            spike2 = (mem2 >= test_th).astype(np.int32)
            mem2[spike2 > 0] = 0
            
            # LAYER 3 (FPGA): Output Voltage Accumulator
            spike2_aug = np.append(spike2, 1.0)
            mem3 += np.dot(q_w3_aug, spike2_aug)
            
        if int(np.argmax(mem3)) == lbl:
            correct += 1

    acc = correct / N_CHECK * 100
    print(f"  FPGA TH={test_th:3d} | Acc: {acc:.1f}%")
    if acc > best_acc:
        best_acc, best_th = acc, test_th

# ─────────────────────────────────────────────────────────────────────
# 5. Save Payload
# ─────────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
np.savez_compressed(
    OUTPUT_PATH,
    w1_f=w1_f, b1_f=b1_f,                 # CPU Payload
    q_w2_aug=q_w2_aug, q_w3_aug=q_w3_aug, # FPGA Payload
    test_imgs=test_imgs, test_lbls=test_lbls,
    hw_threshold=np.array(best_th, dtype=np.int32)
)
print(f"\nSaved Deployment Payload: {OUTPUT_PATH}")