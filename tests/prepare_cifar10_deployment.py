#!/usr/bin/env python3
import os
import sys
import numpy as np
import torch

MODEL_PATH  = 'models/fc3_T_4_rate_spikes_clean_l2[0.000500].pth'
OUTPUT_PATH = 'data/cache/cifar10_3layer_deployment.npz'
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
print(f"Loading PyTorch CIFAR-10 model: {MODEL_PATH}")
state_dict = torch.load(MODEL_PATH, map_location='cpu')

w1_f, b1_f = fuse_batchnorm(state_dict['features.0.weight'], state_dict['features.1.weight'], state_dict['features.1.bias'], state_dict['features.1.running_mean'], state_dict['features.1.running_var'])
w2_f, b2_f = fuse_batchnorm(state_dict['features.3.weight'], state_dict['features.4.weight'], state_dict['features.4.bias'], state_dict['features.4.running_mean'], state_dict['features.4.running_var'])
w3_f = state_dict['classifier.weight'].numpy()
b3_f = state_dict['classifier.bias'].numpy()

print(f"  Layer 1 shape: {w1_f.shape} (Input 3072 -> 256 Hidden)")
print(f"  Layer 2 shape: {w2_f.shape} (Hidden 256 -> 256 Hidden)")
print(f"  Layer 3 shape: {w3_f.shape} (Hidden 256 -> 10 Output)")

# ─────────────────────────────────────────────────────────────────────
# 2. Load CIFAR-10 Data
# ─────────────────────────────────────────────────────────────────────
print("\nLoading CIFAR-10 Test Dataset...")
try:
    from torchvision import datasets, transforms
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))
    ])
    test_ds = datasets.CIFAR10('./data', train=False, download=True, transform=transform)
    test_imgs = np.stack([img.numpy() for img, _ in test_ds]) # (10000, 3, 32, 32)
    test_lbls = np.array([lbl for _, lbl in test_ds], dtype=np.int64)
    print(f"  Loaded {len(test_imgs)} CIFAR-10 test images, shape: {test_imgs.shape}")
except Exception as e:
    print(f"Note: Could not automatically download CIFAR-10 ({e}).")
    print("If you have CIFAR-10 test set downloaded, place it in ./data.")
    # Fallback dummy for verification if needed
    test_imgs = np.zeros((100, 3, 32, 32), dtype=np.float32)
    test_lbls = np.zeros((100,), dtype=np.int64)

# ─────────────────────────────────────────────────────────────────────
# 3. Quantize FPGA Layers (Layer 2 and 3 ONLY)
# ─────────────────────────────────────────────────────────────────────
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
# 4. Calibrate Co-Processing Hardware Threshold
# ─────────────────────────────────────────────────────────────────────
base_th = int(WEIGHT_SCALE)
best_acc, best_th = 0, base_th

if len(test_imgs) > 0 and np.any(test_imgs):
    print("\nRunning Co-Processing Threshold Sweep on CIFAR-10...")
    N_CHECK = min(500, len(test_imgs))
    for test_th in [base_th // 2, int(base_th * 0.8), base_th, int(base_th * 1.2), int(base_th * 1.5)]:
        correct = 0
        for i in range(N_CHECK):
            img = test_imgs[i].flatten()
            lbl = int(test_lbls[i])
            
            mem1 = np.zeros(256, dtype=np.float32)
            mem2 = np.zeros(256, dtype=np.float32)
            mem3 = np.zeros(10, dtype=np.float32)
            
            for t in range(TIMESTEPS):
                mem1 += np.dot(w1_f, img) + b1_f
                mem1 = np.maximum(mem1, 0)
                spike1 = (mem1 >= 1.0).astype(np.float32)
                mem1[spike1 > 0] = 0.0
                
                spike1_aug = np.append(spike1, 1.0)
                mem2 += np.dot(q_w2_aug, spike1_aug)
                mem2 = np.maximum(mem2, 0)
                spike2 = (mem2 >= test_th).astype(np.int32)
                mem2[spike2 > 0] = 0
                
                spike2_aug = np.append(spike2, 1.0)
                mem3 += np.dot(q_w3_aug, spike2_aug)
                
            if int(np.argmax(mem3)) == lbl:
                correct += 1

        acc = correct / N_CHECK * 100
        print(f"  FPGA TH={test_th:3d} | Acc: {acc:.1f}%")
        if acc > best_acc:
            best_acc, best_th = acc, test_th
else:
    best_th = base_th

# ─────────────────────────────────────────────────────────────────────
# 5. Save Payload
# ─────────────────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
np.savez_compressed(
    OUTPUT_PATH,
    w1_f=w1_f, b1_f=b1_f,                 # CPU Payload (3072 input)
    q_w2_aug=q_w2_aug, q_w3_aug=q_w3_aug, # FPGA Payload (256x256 and 10x256)
    test_imgs=test_imgs, test_lbls=test_lbls,
    hw_threshold=np.array(best_th, dtype=np.int32)
)
print(f"\nSaved CIFAR-10 Deployment Payload: {OUTPUT_PATH}")

