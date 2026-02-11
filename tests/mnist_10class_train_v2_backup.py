#!/usr/bin/env python3
"""
MNIST 10-Class Dense STDP Training + FPGA Deployment Preparation
=================================================================
Trains a dense SNN with R-STDP on full MNIST (10 classes) using
PyTorch GPU acceleration.  Quantizes to int8, runs SW verification,
and produces deployment NPZ for PYNQ-Z2.

Architecture (matching HLS IP):
  - 784 input neurons (28×28 MNIST pixels, rate-coded)
  - N_output neurons  (features_per_class × 10 classes, default 100)
  - Dense weights: N_output × 784,  float32 → int8
  - LIF neuron model: pot += W @ spike − leak;  fire if pot ≥ threshold
  - Decision: WTA (first-fire-time), decision_map assigns neurons to classes

Expected accuracy: 70-85% (dense STDP on MNIST 10-class)

Usage:
    python tests/mnist_10class_train.py                    # Train + prepare
    python tests/mnist_10class_train.py --neurons 20       # 20 neurons/class
    python tests/mnist_10class_train.py --resume model.npz # Resume

Produces:
    data/cache/mnist_10class_deployment_<N>n.npz   (for PYNQ board)
    data/cache/mnist_10class_model_<N>n.npz        (trained model)
"""

import sys, os, time, argparse
import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


# ═════════════════════════════════════════════════════════════════════
# Dense SNN with R-STDP  (PyTorch / GPU)
# ═════════════════════════════════════════════════════════════════════

class DenseSTDP10Class:
    """
    Dense SNN with R-STDP for 10-class MNIST.

    784 input → n_output LIF neurons (features_per_class × 10)
    Weights kept as torch.Tensor on *device*.  All forward / STDP
    arithmetic is batched with torch matrix ops → GPU fast path.
    """

    def __init__(self, n_input=784, n_classes=10, features_per_class=10,
                 threshold=30.0, leak=0.3, timesteps=15,
                 lr_plus=0.004, lr_minus=0.003,
                 adaptive_lr=True, device=DEVICE):
        self.n_input = n_input
        self.n_classes = n_classes
        self.features_per_class = features_per_class
        self.n_output = n_classes * features_per_class
        self.threshold = threshold
        self.leak = leak
        self.timesteps = timesteps
        self.lr_plus = lr_plus
        self.lr_minus = lr_minus
        self.adaptive_lr = adaptive_lr
        self.device = device

        # Weights ~ U(0.2, 0.8)  — wider init for class diversity
        self.weights = torch.empty(self.n_output, n_input, device=device)
        self.weights.uniform_(0.2, 0.8)

        # Decision map  (neuron j → class j // features_per_class)
        self.decision_map = torch.arange(self.n_output, device=device) // features_per_class

        # class → neuron mask  (n_classes, n_output)  bool
        self.class_mask = torch.zeros(n_classes, self.n_output,
                                      dtype=torch.bool, device=device)
        for c in range(n_classes):
            start = c * features_per_class
            self.class_mask[c, start:start + features_per_class] = True

        # Per-class accuracy tracking
        self._class_correct = torch.zeros(n_classes, device=device)
        self._class_total   = torch.zeros(n_classes, device=device)

    # ── rate encoding ────────────────────────────────────────────────
    def rate_encode(self, images: torch.Tensor) -> torch.Tensor:
        """
        Rate-code a batch of images into spike trains.

        images : (B, 784) float in [0,1]
        returns: (B, T, 784) float {0,1}
        """
        B = images.shape[0]
        T = self.timesteps
        probs = images.unsqueeze(1).expand(B, T, self.n_input)  # (B,T,784)
        spikes = (torch.rand_like(probs) < probs).float()
        return spikes

    # ── forward (batched) ────────────────────────────────────────────
    @torch.no_grad()
    def forward_batch(self, spikes: torch.Tensor):
        """
        Forward pass for a batch.

        spikes : (B, T, 784) float
        returns: preds (B,), potentials (B, n_out), fired (B, n_out), fire_times (B, n_out)
        """
        B, T, _ = spikes.shape
        N = self.n_output
        potentials = torch.zeros(B, N, device=self.device)
        fired      = torch.zeros(B, N, dtype=torch.bool, device=self.device)
        fire_times = torch.full((B, N), T + 1, dtype=torch.int32, device=self.device)

        for t in range(T):
            # (B,784) @ (784,N) → (B,N)
            inp = spikes[:, t, :]                       # (B, 784)
            potentials += inp @ self.weights.T           # (B, N)
            potentials -= self.leak
            potentials.clamp_(min=0)

            newly_fired = (potentials >= self.threshold) & ~fired
            if newly_fired.any():
                fired |= newly_fired
                fire_times[newly_fired] = t
                potentials[newly_fired] = 0.0

        # WTA: earliest fire  → class
        preds = torch.empty(B, dtype=torch.long, device=self.device)
        any_fired = fired.any(dim=1)                    # (B,)

        if any_fired.any():
            # For samples with fires: pick neuron with smallest fire_time
            ft_masked = fire_times.clone()
            ft_masked[~fired] = T + 2                   # mask unfired
            winners = ft_masked.argmin(dim=1)            # (B,)
            preds[any_fired] = self.decision_map[winners[any_fired]]

        if (~any_fired).any():
            # No fires: pick highest potential
            winners_nf = potentials.argmax(dim=1)
            preds[~any_fired] = self.decision_map[winners_nf[~any_fired]]

        return preds, potentials, fired, fire_times

    # ── R-STDP update (fully vectorised — loop over classes, not samples) ──
    @torch.no_grad()
    def train_rstdp_batch(self, spikes: torch.Tensor,
                          targets: torch.Tensor,
                          predictions: torch.Tensor):
        """
        R-STDP update for a whole batch.

        Uses slice indexing (self.weights[start:end]) which returns a VIEW,
        so in-place ops actually modify the weight matrix.  Loops over
        10 classes instead of B samples → fast.

        spikes      : (B, T, 784)
        targets     : (B,) int
        predictions : (B,) int
        """
        pre_activity = spikes.sum(dim=1)          # (B, 784)
        pre_active   = (pre_activity > 0).float() # (B, 784) float for averaging
        correct      = predictions == targets     # (B,)

        lr_p = self.lr_plus
        lr_m = self.lr_minus
        F = self.features_per_class

        for c in range(self.n_classes):
            s, e = c * F, (c + 1) * F
            w = self.weights[s:e]                 # (F, 784) VIEW — in-place OK

            # ── REWARD: samples that correctly predicted class c ──
            mask_reward = correct & (predictions == c)
            if mask_reward.any():
                pa = pre_active[mask_reward]       # (K, 784)
                active_avg = pa.mean(dim=0, keepdim=True)    # (1, 784)
                w += lr_p * active_avg * (1.0 - w)           # LTP active
                w -= (lr_m * 0.5) * (1.0 - active_avg) * w  # LTD inactive

            # ── PUNISH-PRED: samples that wrongly predicted class c ──
            mask_punish = (~correct) & (predictions == c)
            if mask_punish.any():
                pa = pre_active[mask_punish]
                active_avg = pa.mean(dim=0, keepdim=True)
                w -= lr_m * active_avg * w                   # anti-STDP

            # ── STRENGTHEN: samples whose target IS class c but got it wrong ──
            mask_target = (~correct) & (targets == c)
            if mask_target.any():
                pa = pre_active[mask_target]
                active_avg = pa.mean(dim=0, keepdim=True)
                w += lr_p * active_avg * (1.0 - w)           # LTP correct

        self.weights.clamp_(0.0, 1.0)

        # Per-class accuracy tracking
        for c in range(self.n_classes):
            mask_c = targets == c
            if mask_c.any():
                self._class_total[c] += mask_c.sum()
                self._class_correct[c] += (correct & mask_c).sum()

    # ── quantise ─────────────────────────────────────────────────────
    def quantize_weights(self, scale=127.0):
        w_np = self.weights.cpu().numpy()
        q = np.round(w_np * scale).astype(np.int8)
        return q, scale

    # ── save / load ──────────────────────────────────────────────────
    def save(self, path):
        np.savez(path,
                 weights=self.weights.cpu().numpy(),
                 decision_map=self.decision_map.cpu().numpy(),
                 threshold=self.threshold, leak=self.leak,
                 timesteps=self.timesteps, n_input=self.n_input,
                 n_classes=self.n_classes,
                 features_per_class=self.features_per_class)
        print(f"  Model saved → {path}")

    @classmethod
    def load(cls, path, device=DEVICE):
        d = np.load(path)
        net = cls(n_input=int(d['n_input']), n_classes=int(d['n_classes']),
                  features_per_class=int(d['features_per_class']),
                  threshold=float(d['threshold']), leak=float(d['leak']),
                  timesteps=int(d['timesteps']), device=device)
        net.weights = torch.from_numpy(d['weights']).to(device)
        print(f"  Model loaded ← {path}")
        return net


# ═════════════════════════════════════════════════════════════════════
# Data Loading  (torchvision)
# ═════════════════════════════════════════════════════════════════════

def load_mnist_10class(data_dir='./data', max_train=None, max_test=None):
    from torchvision import datasets, transforms
    transform = transforms.Compose([transforms.ToTensor()])
    train_ds = datasets.MNIST(data_dir, train=True,  download=True, transform=transform)
    test_ds  = datasets.MNIST(data_dir, train=False, download=True, transform=transform)

    def to_tensors(ds, max_n=None):
        imgs, lbls = [], []
        for img, lbl in ds:
            imgs.append(img.squeeze(0))                 # (28,28)
            lbls.append(lbl)
            if max_n and len(imgs) >= max_n:
                break
        return torch.stack(imgs), torch.tensor(lbls, dtype=torch.long)

    train_imgs, train_lbls = to_tensors(train_ds, max_train)
    test_imgs,  test_lbls  = to_tensors(test_ds,  max_test)
    print(f"  Train: {len(train_imgs)},  Test: {len(test_imgs)}")
    return train_imgs, train_lbls, test_imgs, test_lbls


# ═════════════════════════════════════════════════════════════════════
# Training  (GPU-batched)
# ═════════════════════════════════════════════════════════════════════

def train_network(net, train_imgs, train_lbls, epochs=50,
                  batch_size=128, save_path=None):
    """Train with mini-batches on GPU."""
    N = len(train_imgs)
    # Flatten to (N, 784) and send to device once
    flat = train_imgs.reshape(N, -1).to(net.device)
    lbls = train_lbls.to(net.device)

    best_acc = 0.0
    best_weights = None

    for epoch in range(epochs):
        net._class_correct.zero_()
        net._class_total.zero_()

        perm = torch.randperm(N, device=net.device)
        correct = 0
        total = 0

        for start in range(0, N, batch_size):
            end = min(start + batch_size, N)
            idx = perm[start:end]
            imgs_b = flat[idx]                          # (B, 784)
            lbls_b = lbls[idx]                          # (B,)

            spikes = net.rate_encode(imgs_b)             # (B, T, 784)
            preds, _, _, _ = net.forward_batch(spikes)   # (B,)
            net.train_rstdp_batch(spikes, lbls_b, preds)

            correct += (preds == lbls_b).sum().item()
            total += len(lbls_b)

        acc = correct / total * 100

        if epoch % 5 == 0 or epoch == epochs - 1:
            ca = net._class_correct / net._class_total.clamp(min=1) * 100
            print(f"  Epoch {epoch:3d}: Acc={acc:5.1f}%  "
                  f"W=[{net.weights.min():.3f},{net.weights.max():.3f}]  "
                  f"ClassAcc=[{ca.min():.0f}%-{ca.max():.0f}%]")

        if acc > best_acc:
            best_acc = acc
            best_weights = net.weights.clone()
            if save_path:
                net.save(save_path)

    if best_weights is not None:
        net.weights = best_weights
        print(f"  Best train accuracy: {best_acc:.1f}%")
    return net


def test_network(net, test_imgs, test_lbls, batch_size=256):
    """Test on full test set with batched forward."""
    N = len(test_imgs)
    flat = test_imgs.reshape(N, -1).to(net.device)
    lbls = test_lbls.to(net.device)

    per_class_correct = torch.zeros(net.n_classes, device=net.device)
    per_class_total   = torch.zeros(net.n_classes, device=net.device)
    all_preds = []

    for start in range(0, N, batch_size):
        end = min(start + batch_size, N)
        spikes = net.rate_encode(flat[start:end])
        preds, _, _, _ = net.forward_batch(spikes)
        all_preds.append(preds)

        for c in range(net.n_classes):
            mask = lbls[start:end] == c
            per_class_total[c] += mask.sum()
            per_class_correct[c] += ((preds == c) & mask).sum()

    all_preds = torch.cat(all_preds)
    correct = (all_preds == lbls).sum().item()
    acc = correct / N * 100

    print(f"  Overall: {correct}/{N} = {acc:.1f}%")
    for c in range(net.n_classes):
        ct = int(per_class_total[c].item())
        cc = int(per_class_correct[c].item())
        print(f"    Class {c}: {cc}/{ct} = {cc/max(ct,1)*100:.0f}%")

    return all_preds.cpu().numpy(), acc


# ═════════════════════════════════════════════════════════════════════
# SW LIF Reference  (NumPy — matches FPGA int8 behaviour)
# ═════════════════════════════════════════════════════════════════════

def prepare_fpga_spikes(image_np, q_weights, pixel_threshold=0.3):
    """Pre-weighted spike events for DMA.  image_np: (28,28) or (784,)."""
    pixels = image_np.flatten()
    active = np.where(pixels > pixel_threshold)[0]
    events = []
    for i_idx in active:
        for j in range(q_weights.shape[0]):
            w = int(q_weights[j, i_idx])
            if w > 0:
                events.append((j, w))
    return events


def sw_lif_reference(spike_events, n_output, threshold):
    """Accumulate pre-weighted spikes, fire on threshold."""
    potentials = np.zeros(n_output, dtype=np.int64)
    fired = set()
    fire_order = []
    for neuron_id, weight in spike_events:
        if neuron_id not in fired:
            potentials[neuron_id] += weight
            if potentials[neuron_id] >= threshold:
                fired.add(neuron_id)
                fire_order.append(neuron_id)
                potentials[neuron_id] = 0
    return potentials, fired, fire_order


def classify_from_sw_lif(potentials, fired, fire_order, decision_map, n_output):
    if fire_order:
        winner = fire_order[0]
    else:
        winner = int(np.argmax(potentials))
    return int(decision_map[winner])


# ═════════════════════════════════════════════════════════════════════
# Deployment NPZ
# ═════════════════════════════════════════════════════════════════════

def create_deployment_npz(net, test_imgs, test_lbls, n_deploy, output_path):
    q_weights, q_scale = net.quantize_weights()
    threshold_int = int(net.threshold * q_scale)
    decision_map_np = net.decision_map.cpu().numpy()

    # Balanced selection
    lbls_np = test_lbls.numpy() if isinstance(test_lbls, torch.Tensor) else test_lbls
    imgs_np = test_imgs.numpy() if isinstance(test_imgs, torch.Tensor) else test_imgs

    selected = []
    per_class = n_deploy // net.n_classes
    for c in range(net.n_classes):
        ci = np.where(lbls_np == c)[0]
        selected.extend(ci[:min(per_class, len(ci))].tolist())
    remaining = n_deploy - len(selected)
    if remaining > 0:
        unused = sorted(set(range(len(lbls_np))) - set(selected))
        selected.extend(unused[:remaining])
    selected = sorted(selected[:n_deploy])

    deploy_imgs = imgs_np[selected]
    deploy_lbls = lbls_np[selected]

    print(f"  Deploy images: {len(deploy_imgs)}")
    dist = [int((deploy_lbls == c).sum()) for c in range(net.n_classes)]
    print(f"  Class distribution: {dist}")

    # SW verification
    sw_correct = 0
    for i in range(len(deploy_imgs)):
        events = prepare_fpga_spikes(deploy_imgs[i], q_weights)
        pots, fired, fo = sw_lif_reference(events, net.n_output, threshold_int)
        pred = classify_from_sw_lif(pots, fired, fo, decision_map_np, net.n_output)
        if pred == deploy_lbls[i]:
            sw_correct += 1
    sw_acc = sw_correct / len(deploy_imgs) * 100
    print(f"  SW-LIF deploy accuracy: {sw_correct}/{len(deploy_imgs)} = {sw_acc:.1f}%")

    np.savez(output_path,
             q_weights=q_weights, test_imgs=deploy_imgs, test_lbls=deploy_lbls,
             threshold=np.array(threshold_int), n_output=np.array(net.n_output),
             n_classes=np.array(net.n_classes),
             features_per_class=np.array(net.features_per_class),
             decision_map=decision_map_np)

    sz = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  Saved: {output_path} ({sz:.1f} MB)")
    print(f"  q_weights: {q_weights.shape}, range=[{q_weights.min()},{q_weights.max()}], thr={threshold_int}")
    return output_path, sw_acc


# ═════════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description='MNIST 10-Class STDP (PyTorch GPU)')
    ap.add_argument('--neurons',        type=int,   default=10)
    ap.add_argument('--epochs',         type=int,   default=50)
    ap.add_argument('--batch-size',     type=int,   default=128)
    ap.add_argument('--train-samples',  type=int,   default=20000)
    ap.add_argument('--test-samples',   type=int,   default=0)
    ap.add_argument('--deploy-samples', type=int,   default=1000)
    ap.add_argument('--threshold',      type=float, default=30.0)
    ap.add_argument('--leak',           type=float, default=0.3)
    ap.add_argument('--timesteps',      type=int,   default=15)
    ap.add_argument('--lr-plus',        type=float, default=0.004)
    ap.add_argument('--lr-minus',       type=float, default=0.003)
    ap.add_argument('--resume',         type=str,   default=None)
    ap.add_argument('--seed',           type=int,   default=42)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(args.seed)

    n_out = args.neurons * 10
    model_path  = f'data/cache/mnist_10class_model_{n_out}n.npz'
    deploy_path = f'data/cache/mnist_10class_deployment_{n_out}n.npz'

    print("=" * 70)
    print("MNIST 10-Class Dense STDP Training  (PyTorch GPU)")
    print("=" * 70)
    print(f"  Device:       {DEVICE}")
    print(f"  Architecture: 784 → {n_out} ({args.neurons}/class × 10)")
    print(f"  Threshold={args.threshold}  Leak={args.leak}  T={args.timesteps}")
    print(f"  Epochs={args.epochs}  Batch={args.batch_size}  "
          f"TrainN={args.train_samples}  DeployN={args.deploy_samples}")

    # ── 1. Load Data ─────────────────────────────────────────────────
    print("\n[1/6] Loading MNIST …")
    max_test = args.test_samples if args.test_samples > 0 else None
    train_imgs, train_lbls, test_imgs, test_lbls = load_mnist_10class(
        max_train=args.train_samples, max_test=max_test)

    # ── 2. Network ───────────────────────────────────────────────────
    if args.resume:
        print(f"\n[2/6] Resuming from {args.resume} …")
        net = DenseSTDP10Class.load(args.resume)
    else:
        print(f"\n[2/6] Creating network …")
        net = DenseSTDP10Class(
            n_input=784, n_classes=10, features_per_class=args.neurons,
            threshold=args.threshold, leak=args.leak,
            timesteps=args.timesteps,
            lr_plus=args.lr_plus, lr_minus=args.lr_minus,
            device=DEVICE)
    print(f"  weights: {tuple(net.weights.shape)}, "
          f"decision_map[0:20]={net.decision_map[:20].tolist()}")

    # ── 3. Train ─────────────────────────────────────────────────────
    print(f"\n[3/6] Training ({args.epochs} epochs, {len(train_imgs)} samples) …")
    t0 = time.time()
    net = train_network(net, train_imgs, train_lbls,
                        epochs=args.epochs, batch_size=args.batch_size,
                        save_path=model_path)
    dt = time.time() - t0
    print(f"  Time: {dt:.0f}s ({dt/60:.1f} min)")

    # ── 4. Test float32 ──────────────────────────────────────────────
    print(f"\n[4/6] Testing float32 ({len(test_imgs)} images) …")
    _, sw_acc = test_network(net, test_imgs, test_lbls)

    # ── 5. Test int8 quantised (SW-LIF reference) ────────────────────
    print(f"\n[5/6] Testing int8 quantised (SW-LIF) …")
    q_weights, q_scale = net.quantize_weights()
    q_thr = int(net.threshold * q_scale)
    print(f"  q_threshold: {q_thr}")

    test_imgs_np = test_imgs.numpy() if isinstance(test_imgs, torch.Tensor) else test_imgs
    test_lbls_np = test_lbls.numpy() if isinstance(test_lbls, torch.Tensor) else test_lbls
    decision_map_np = net.decision_map.cpu().numpy()

    q_correct = 0
    for i in range(len(test_imgs_np)):
        events = prepare_fpga_spikes(test_imgs_np[i], q_weights)
        pots, fired, fo = sw_lif_reference(events, net.n_output, q_thr)
        pred = classify_from_sw_lif(pots, fired, fo, decision_map_np, net.n_output)
        if pred == test_lbls_np[i]:
            q_correct += 1
    q_acc = q_correct / len(test_imgs_np) * 100
    print(f"  Int8 accuracy: {q_correct}/{len(test_imgs_np)} = {q_acc:.1f}%")

    # ── 6. Deployment NPZ ────────────────────────────────────────────
    print(f"\n[6/6] Creating deployment data ({args.deploy_samples} images) …")
    deploy_file, deploy_acc = create_deployment_npz(
        net, test_imgs, test_lbls, args.deploy_samples, deploy_path)

    # ── Summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Architecture:      784 → {n_out} ({args.neurons}/class × 10)")
    print(f"  Training:          {len(train_imgs)} samples, {args.epochs} epochs, {dt:.0f}s")
    print(f"  Float32 accuracy:  {sw_acc:.1f}%")
    print(f"  Int8 accuracy:     {q_acc:.1f}%")
    print(f"  Deploy SW-LIF:     {deploy_acc:.1f}%")
    print(f"  Model:             {model_path}")
    print(f"  Deployment NPZ:    {deploy_file}")
    print(f"  Weights:           {q_weights.shape}, threshold={q_thr}")
    print()
    print("Next steps:")
    print(f"  1. scp {deploy_file} xilinx@<pynq>:/home/xilinx/snn/")
    print(f"  2. sudo python3 pynq_mnist_inference_10class.py")

    return sw_acc, q_acc


if __name__ == "__main__":
    main()
