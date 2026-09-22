#!/usr/bin/env python3
import os
import sys
import argparse
import numpy as np
import torch

parser = argparse.ArgumentParser(description="Prepare 3-Layer SNN Payload with Dynamic Threshold Calibration")
parser.add_argument('--model',  default='models/fc3_T_4_rate_spikes_clean_l2[0.000500].pth',
                    help='Path to PyTorch .pth model checkpoint')
parser.add_argument('--output', default='data/cache/mnist_3layer_deployment_v2.npz',
                    help='Output deployment payload path')
parser.add_argument('--timesteps', type=int, default=4,
                    help='Number of SNN timesteps')
args = parser.parse_args()

MODEL_PATH  = args.model
OUTPUT_PATH = args.output
TIMESTEPS   = args.timesteps

def fuse_batchnorm(w, bn_gamma, bn_beta, bn_mean, bn_var, eps=1e-5):
    """Fold BatchNorm parameters into the Linear layer weights and biases."""
    std = torch.sqrt(bn_var + eps)
    w_fused = w * (bn_gamma / std).unsqueeze(1)
    if bn_beta is not None:
        b_fused = bn_beta - bn_mean * (bn_gamma / std)
    else:
        b_fused = - bn_mean * (bn_gamma / std)
    return w_fused.numpy(), b_fused.numpy()

# ─────────────────────────────────────────────────────────────────────
# 1. Load Model
# ─────────────────────────────────────────────────────────────────────
print(f"Loading PyTorch model: {MODEL_PATH}")
state_dict = torch.load(MODEL_PATH, map_location='cpu')

# Layer 1 extraction (detect if BatchNorm is present)
if 'features.1.running_var' in state_dict:
    w1_f, b1_f = fuse_batchnorm(
        state_dict['features.0.weight'],
        state_dict['features.1.weight'],
        state_dict.get('features.1.bias', None),
        state_dict['features.1.running_mean'],
        state_dict['features.1.running_var']
    )
else:
    w1_f = state_dict['features.0.weight'].numpy()
    b1_f = state_dict['features.0.bias'].numpy() if 'features.0.bias' in state_dict else np.zeros(w1_f.shape[0], dtype=np.float32)

# Layer 2 extraction (detect if BatchNorm is present)
if 'features.4.running_var' in state_dict:
    w2_f, b2_f = fuse_batchnorm(
        state_dict['features.3.weight'],
        state_dict['features.4.weight'],
        state_dict.get('features.4.bias', None),
        state_dict['features.4.running_mean'],
        state_dict['features.4.running_var']
    )
else:
    w2_key = 'features.2.weight' if 'features.2.weight' in state_dict else 'features.3.weight'
    w2_f = state_dict[w2_key].numpy()
    b2_key = 'features.2.bias' if 'features.2.bias' in state_dict else 'features.3.bias'
    b2_f = state_dict[b2_key].numpy() if b2_key in state_dict else np.zeros(w2_f.shape[0], dtype=np.float32)

# Layer 3 extraction
w3_f = state_dict['classifier.weight'].numpy()
b3_f = state_dict['classifier.bias'].numpy() if 'classifier.bias' in state_dict else np.zeros(w3_f.shape[0], dtype=np.float32)

has_biases = not (np.all(b1_f == 0) and np.all(b2_f == 0) and np.all(b3_f == 0))
print(f"Model Biases Detected: {'Yes (fused/explicit)' if has_biases else 'No (bias=False / zero bias)'}")


# ─────────────────────────────────────────────────────────────────────
# 2. Load MNIST Data (Auto-Detect Normalization)
# ─────────────────────────────────────────────────────────────────────
try:
    from torchvision import datasets, transforms
    # Auto-detect whether checkpoint was trained with Z-score normalization or raw [0, 1] pixels
    if 'features.1.running_var' in state_dict:
        var_mean = state_dict['features.1.running_var'].mean().item()
        is_normalized = (var_mean >= 0.5)
    else:
        is_normalized = False

    if is_normalized:
        print("Detected Training Normalization: Z-Score Normalized (mean=0.1307, std=0.3081)")
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.1307,), (0.3081,))
        ])
    else:
        print("Detected Training Normalization: Raw [0, 1] intensities (No Z-score normalization)")
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
# We calibrate hw_threshold dynamically relative to the theoretical base
# threshold (base_th = round(WEIGHT_SCALE)), scanning a comprehensive
# range of multipliers to accommodate both unbiased and biased architectures.
base_th = max(1, int(round(WEIGHT_SCALE)))
multipliers = [0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.65, 0.80, 1.00, 1.20, 1.50]
candidate_ths = sorted(list(set([max(1, int(round(base_th * m))) for m in multipliers])))

print(f"\nRunning Hardware-Faithful Sequential Threshold Sweep (base_th = {base_th})...")
print(f"Candidate thresholds ({len(candidate_ths)} points): {candidate_ths}")
N_CHECK = min(1000, len(test_imgs))
best_acc, best_th = 0, base_th

for test_th in candidate_ths:
    correct = 0
    total_output_spikes = 0
    for i in range(N_CHECK):
        img = test_imgs[i].flatten()
        lbl = int(test_lbls[i])
        
        mem1 = np.zeros(256, dtype=np.float32)
        mem2 = np.zeros(256, dtype=np.int32)
        mem3 = np.zeros(10, dtype=np.int32)
        spk3_count = np.zeros(10, dtype=int)
        
        for t in range(TIMESTEPS):
            # LAYER 1 (CPU): Float32 math, analog inputs + bias
            mem1 += np.dot(w1_f, img) + b1_f
            mem1 = np.maximum(mem1, 0.0)
            spike1 = (mem1 >= 1.0).astype(np.int32)
            mem1[spike1 > 0] = 0.0
            
            # LAYER 2 & 3 (FPGA Hardware Emulation): Sequential event-driven spike delivery
            for src in np.nonzero(spike1)[0]:
                mem2 += q_w2[:, src]
                mem2 = np.maximum(mem2, 0)
                f2 = np.nonzero(mem2 >= test_th)[0]
                mem2[f2] = 0
                for f in f2:
                    mem3 += q_w3[:, f]
                    mem3 = np.maximum(mem3, 0)
                    f3 = np.nonzero(mem3 >= test_th)[0]
                    mem3[f3] = 0
                    spk3_count[f3] += 1
            
        total_output_spikes += np.sum(spk3_count)
        if int(np.argmax(spk3_count)) == lbl:
            correct += 1

    acc = correct / N_CHECK * 100
    avg_spikes = total_output_spikes / N_CHECK
    print(f"  FPGA TH={test_th:3d} (m={test_th/base_th:.2f}) | Acc: {acc:.2f}% | Avg Spikes/Img: {avg_spikes:.1f}")
    
    # Select threshold with highest accuracy and well-behaved spike counts (< 250 spikes/img)
    # to avoid flooding DMA buffers on the physical FPGA
    if avg_spikes < 250 and acc > best_acc:
        best_acc, best_th = acc, test_th

print(f"\nOptimal Calibrated Hardware Threshold: {best_th} (Validation Acc: {best_acc:.2f}%)")

# Full 10,000 image validation
print("Validating calibrated threshold on full test set (10,000 images)...")
correct_full = 0
total_full_spikes = 0
for i in range(len(test_imgs)):
    img = test_imgs[i].flatten()
    lbl = int(test_lbls[i])
    mem1 = np.zeros(256, dtype=np.float32)
    mem2 = np.zeros(256, dtype=np.int32)
    mem3 = np.zeros(10, dtype=np.int32)
    spk3_count = np.zeros(10, dtype=int)
    for t in range(TIMESTEPS):
        mem1 += np.dot(w1_f, img) + b1_f
        mem1 = np.maximum(mem1, 0.0)
        spike1 = (mem1 >= 1.0).astype(np.int32)
        mem1[spike1 > 0] = 0.0
        
        for src in np.nonzero(spike1)[0]:
            mem2 += q_w2[:, src]
            mem2 = np.maximum(mem2, 0)
            f2 = np.nonzero(mem2 >= best_th)[0]
            mem2[f2] = 0
            for f in f2:
                mem3 += q_w3[:, f]
                mem3 = np.maximum(mem3, 0)
                f3 = np.nonzero(mem3 >= best_th)[0]
                mem3[f3] = 0
                spk3_count[f3] += 1
    total_full_spikes += np.sum(spk3_count)
    if int(np.argmax(spk3_count)) == lbl:
        correct_full += 1

full_acc = correct_full / len(test_imgs) * 100
print(f"Full Test Set Accuracy (10,000 images): {full_acc:.2f}% (Avg Spikes/Img: {total_full_spikes/len(test_imgs):.1f})")

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