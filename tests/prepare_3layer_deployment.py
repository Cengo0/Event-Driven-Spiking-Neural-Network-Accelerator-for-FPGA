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
# 3 & 4. Event-Driven Bias Folding + Independent L2/L3 Scale & Threshold Sweep
# ─────────────────────────────────────────────────────────────────────
N_CHECK = min(500, len(test_imgs))
calib_imgs_flat = test_imgs[:N_CHECK].reshape(N_CHECK, -1)
calib_lbls = test_lbls[:N_CHECK]

print(f"\nPrecomputing Layer 1 (CPU Float32 LIF) spike streams on {N_CHECK} calibration images...")
s1_calib = []
total_s1_spikes = 0
for i in range(N_CHECK):
    mem1 = np.zeros(256, dtype=np.float32)
    cur1 = np.dot(w1_f, calib_imgs_flat[i]) + b1_f
    img_s1 = []
    for t in range(TIMESTEPS):
        mem1 += cur1
        mem1 = np.maximum(mem1, 0.0)
        sp1 = np.nonzero(mem1 >= 1.0)[0]
        mem1[sp1] = 0.0
        img_s1.append(sp1)
        total_s1_spikes += len(sp1)
    s1_calib.append(img_s1)

avg_s1_per_ts = max(1.0, total_s1_spikes / (N_CHECK * float(TIMESTEPS)))
alpha2_base = 1.0 / avg_s1_per_ts if has_biases else 0.0
alpha2_mults = [0.0, 0.5, 0.8, 1.0, 1.2] if has_biases else [0.0]
alpha3_mults = [0.0, 0.5, 0.8, 1.0, 1.2] if has_biases else [0.0]
m2_candidates = [0.50, 0.65, 0.80, 0.90, 1.00]
s3_ratios = [0.35, 0.50, 0.65, 0.80, 1.00]

print(f"  Avg Layer 1 Spikes / Timestep: {avg_s1_per_ts:.1f} (base alpha2 = {alpha2_base:.4f})")
print("Running Joint Calibration Sweep (L2/L3 Bias Folding + Independent L2/L3 Scaling)...")

best_acc = -1.0
best_cfg = None

for a2_m in alpha2_mults:
    a2 = alpha2_base * a2_m
    w2_fold = w2_f + (b2_f[:, None] * a2)
    scale2 = 127.0 / max(1e-6, float(np.max(np.abs(w2_fold))))
    q_w2_cand = np.clip(np.round(w2_fold * scale2), -127, 127).astype(np.int32)

    for m2 in m2_candidates:
        th_hw = max(1, int(round(scale2 * m2)))

        s2_calib = []
        total_s2_spikes = 0
        for i in range(N_CHECK):
            mem2 = np.zeros(256, dtype=np.int32)
            img_s2 = []
            for t in range(TIMESTEPS):
                ts_f2 = []
                for src in s1_calib[i][t]:
                    mem2 = np.maximum(mem2 + q_w2_cand[:, src], 0)
                    f2 = np.nonzero(mem2 >= th_hw)[0]
                    if len(f2) > 0:
                        mem2[f2] = 0
                        ts_f2.extend(f2.tolist())
                img_s2.append(ts_f2)
                total_s2_spikes += len(ts_f2)
            s2_calib.append(img_s2)

        avg_s2_per_ts = max(1.0, total_s2_spikes / (N_CHECK * float(TIMESTEPS)))
        alpha3_base = 1.0 / avg_s2_per_ts if has_biases else 0.0

        for a3_m in alpha3_mults:
            a3 = alpha3_base * a3_m
            w3_fold = w3_f + (b3_f[:, None] * a3)
            scale3_full = 127.0 / max(1e-6, float(np.max(np.abs(w3_fold))))

            for s3_ratio in s3_ratios:
                scale3 = scale3_full * s3_ratio
                q_w3_cand = np.clip(np.round(w3_fold * scale3), -127, 127).astype(np.int32)

                correct = 0
                total_output_spikes = 0
                for i in range(N_CHECK):
                    mem3 = np.zeros(10, dtype=np.int32)
                    spk3_count = np.zeros(10, dtype=np.int32)
                    for t in range(TIMESTEPS):
                        for f in s2_calib[i][t]:
                            mem3 = np.maximum(mem3 + q_w3_cand[:, f], 0)
                            f3 = np.nonzero(mem3 >= th_hw)[0]
                            if len(f3) > 0:
                                mem3[f3] = 0
                                spk3_count[f3] += 1
                    total_output_spikes += int(np.sum(spk3_count))
                    if np.sum(spk3_count) > 0 and int(np.argmax(spk3_count)) == int(calib_lbls[i]):
                        correct += 1

                acc = correct / N_CHECK * 100.0
                avg_spikes = total_output_spikes / N_CHECK
                if 2.0 <= avg_spikes < 200.0 and acc > best_acc:
                    best_acc = acc
                    best_cfg = (a2, a3, scale2, scale3, s3_ratio, th_hw, avg_spikes)

best_a2, best_a3, best_scale2, best_scale3, best_s3_ratio, best_th, best_avg_spk = best_cfg
w2_final = w2_f + (b2_f[:, None] * best_a2)
w3_final = w3_f + (b3_f[:, None] * best_a3)

q_w2 = np.clip(np.round(w2_final * best_scale2), -127, 127).astype(np.int8)
q_b2 = np.clip(np.round(b2_f * best_scale2), -127, 127).astype(np.int8)
q_w2_aug = np.hstack([q_w2, q_b2[:, None]])

q_w3 = np.clip(np.round(w3_final * best_scale3), -127, 127).astype(np.int8)
q_b3 = np.clip(np.round(b3_f * best_scale3), -127, 127).astype(np.int8)
q_w3_aug = np.hstack([q_w3, q_b3[:, None]])

print(f"\nOptimal Calibrated Parameters:")
print(f"  Validation Accuracy ({N_CHECK} imgs) : {best_acc:.2f}% (Avg Spikes/Img: {best_avg_spk:.1f})")
print(f"  Layer 2 Bias Fold (alpha2)      : {best_a2:.4f} | Scale2: {best_scale2:.2f}")
print(f"  Layer 3 Bias Fold (alpha3)      : {best_a3:.4f} | Scale3: {best_scale3:.2f} (ratio={best_s3_ratio:.2f})")
print(f"  Hardware Threshold (Reg 0x10)   : {best_th} (Effective L3 TH = {int(round(best_th / best_s3_ratio))})")

# Full 10,000 image validation
print("\nValidating calibrated parameters on full test set (10,000 images)...")
q_w2_i32 = q_w2.astype(np.int32)
q_w3_i32 = q_w3.astype(np.int32)
correct_full = 0
total_full_spikes = 0
for i in range(len(test_imgs)):
    img = test_imgs[i].flatten()
    lbl = int(test_lbls[i])
    mem1 = np.zeros(256, dtype=np.float32)
    mem2 = np.zeros(256, dtype=np.int32)
    mem3 = np.zeros(10, dtype=np.int32)
    spk3_count = np.zeros(10, dtype=int)
    cur1 = np.dot(w1_f, img) + b1_f
    for t in range(TIMESTEPS):
        mem1 += cur1
        mem1 = np.maximum(mem1, 0.0)
        spike1 = (mem1 >= 1.0).astype(np.int32)
        mem1[spike1 > 0] = 0.0
        
        for src in np.nonzero(spike1)[0]:
            mem2 += q_w2_i32[:, src]
            mem2 = np.maximum(mem2, 0)
            f2 = np.nonzero(mem2 >= best_th)[0]
            if len(f2) > 0:
                mem2[f2] = 0
                for f in f2:
                    mem3 += q_w3_i32[:, f]
                    mem3 = np.maximum(mem3, 0)
                    f3 = np.nonzero(mem3 >= best_th)[0]
                    if len(f3) > 0:
                        mem3[f3] = 0
                        spk3_count[f3] += 1
    total_full_spikes += np.sum(spk3_count)
    if np.sum(spk3_count) > 0 and int(np.argmax(spk3_count)) == lbl:
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
    hw_threshold=np.array(best_th, dtype=np.int32),
    alpha2=np.array(best_a2, dtype=np.float32),
    alpha3=np.array(best_a3, dtype=np.float32),
    scale2=np.array(best_scale2, dtype=np.float32),
    scale3=np.array(best_scale3, dtype=np.float32)
)
print(f"\nSaved Deployment Payload: {OUTPUT_PATH}")