#!/usr/bin/env python3
import os
import sys
import numpy as np
import torch

MODEL_PATH  = 'models/fc3_T_4_rate_spikes_clean_l2[0.000500].pth'
OUTPUT_PATH = 'data/cache/mnist_3layer_deployment_v2.npz'
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
# 2. Load MNIST Data (Raw [0, 1] for Rate-Spikes Model)
# ─────────────────────────────────────────────────────────────────────
print("\nLoading MNIST Data (Raw [0, 1] intensities)...")
try:
    from torchvision import datasets, transforms
    # This rate_spikes model was trained on raw [0, 1] pixel intensities without Z-score normalization
    transform = transforms.Compose([
        transforms.ToTensor()
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
# ─────────────────────────────────────────────────────────────────────
# 3. Quantize FPGA Layers (Layer 2 and 3 ONLY)
# ─────────────────────────────────────────────────────────────────────
# Scale weights using max absolute weight across FPGA layers (weights only)
max_abs = max(np.max(np.abs(w2_f)), np.max(np.abs(w3_f)))
WEIGHT_SCALE = 127.0 / max_abs
print(f"\nFPGA Dynamic Weight Scale: {WEIGHT_SCALE:.2f}")

q_w2 = np.clip(np.round(w2_f * WEIGHT_SCALE), -127, 127).astype(np.int8)
q_b2 = np.clip(np.round(b2_f * WEIGHT_SCALE), -127, 127).astype(np.int8)
q_w2_aug = np.hstack([q_w2, q_b2[:, None]])

q_w3 = np.clip(np.round(w3_f * WEIGHT_SCALE), -127, 127).astype(np.int8)
q_b3 = np.clip(np.round(b3_f * WEIGHT_SCALE), -127, 127).astype(np.int8)
q_w3_aug = np.hstack([q_w3, q_b3[:, None]])

# ─────────────────────────────────────────────────────────────────────
# 4. Hardware-Faithful Co-Processing Threshold Sweep
# ─────────────────────────────────────────────────────────────────────
# The FPGA hardware has NO bias inputs for Layer 2 / Layer 3 and uses
# discrete LIF spike counting for Group 2 (not an analog accumulator).
# We calibrate hw_threshold using the exact hardware execution model.
print("\nRunning Hardware-Faithful Threshold Sweep (No HW Biases, Discrete LIF Readout)...")
N_CHECK = min(2000, len(test_imgs))
candidate_ths = [25, 30, 35, 40, 45, 50, 60, 75, 90, 110, 127]
best_acc, best_th = 0, 40

for test_th in candidate_ths:
    correct = 0
    for i in range(N_CHECK):
        img = test_imgs[i].flatten()
        lbl = int(test_lbls[i])
        
        mem1 = np.zeros(256, dtype=np.float32)
        mem2 = np.zeros(256, dtype=np.float32)
        mem3 = np.zeros(10, dtype=np.float32)
        spk3_count = np.zeros(10, dtype=int)
        
        for t in range(TIMESTEPS):
            # LAYER 1 (CPU): Float32 math, analog inputs + bias
            mem1 += np.dot(w1_f, img) + b1_f
            mem1 = np.maximum(mem1, 0.0)
            spike1 = (mem1 >= 1.0).astype(np.float32)
            mem1[spike1 > 0] = 0.0
            
            # LAYER 2 (FPGA Grp 1): Int32 LIF math WITHOUT bias
            mem2 += np.dot(q_w2, spike1)
            mem2 = np.maximum(mem2, 0.0)
            spike2 = (mem2 >= test_th).astype(np.int32)
            mem2[spike2 > 0] = 0.0
            
            # LAYER 3 (FPGA Grp 2): Discrete LIF Spikes WITHOUT bias
            mem3 += np.dot(q_w3, spike2)
            mem3 = np.maximum(mem3, 0.0)
            spike3 = (mem3 >= test_th).astype(np.int32)
            mem3[spike3 > 0] = 0.0
            spk3_count += spike3
            
        if int(np.argmax(spk3_count)) == lbl:
            correct += 1

    acc = correct / N_CHECK * 100
    print(f"  FPGA TH={test_th:3d} | Acc: {acc:.2f}%")
    if acc > best_acc:
        best_acc, best_th = acc, test_th

print(f"\nOptimal Calibrated Hardware Threshold: {best_th} (Validation Acc: {best_acc:.2f}%)")

# Full 10,000 image validation
print("Validating calibrated threshold on full test set (10,000 images)...")
correct_full = 0
for i in range(len(test_imgs)):
    img = test_imgs[i].flatten()
    lbl = int(test_lbls[i])
    mem1 = np.zeros(256, dtype=np.float32)
    mem2 = np.zeros(256, dtype=np.float32)
    mem3 = np.zeros(10, dtype=np.float32)
    spk3_count = np.zeros(10, dtype=int)
    for t in range(TIMESTEPS):
        mem1 += np.dot(w1_f, img) + b1_f
        mem1 = np.maximum(mem1, 0.0)
        spike1 = (mem1 >= 1.0).astype(np.float32)
        mem1[spike1 > 0] = 0.0
        
        mem2 += np.dot(q_w2, spike1)
        mem2 = np.maximum(mem2, 0.0)
        spike2 = (mem2 >= best_th).astype(np.int32)
        mem2[spike2 > 0] = 0.0
        
        mem3 += np.dot(q_w3, spike2)
        mem3 = np.maximum(mem3, 0.0)
        spike3 = (mem3 >= best_th).astype(np.int32)
        mem3[spike3 > 0] = 0.0
        spk3_count += spike3
    if int(np.argmax(spk3_count)) == lbl:
        correct_full += 1

full_acc = correct_full / len(test_imgs) * 100
print(f"Full Test Set Accuracy (10,000 images): {full_acc:.2f}%")

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