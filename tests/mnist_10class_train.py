#!/usr/bin/env python3
"""
MNIST 10-Class Dense STDP Training + FPGA Deployment Preparation
=================================================================
Trains a dense SNN with competitive R-STDP on full MNIST (10 classes)
using PyTorch GPU acceleration.  Quantizes to int8, runs SW verification,
and produces deployment NPZ for PYNQ-Z2.

Architecture (matching HLS IP):
  - 784 input neurons (28x28 MNIST pixels, rate-coded)
  - N_output neurons  (features_per_class x 10 classes, default 100)
  - Dense weights: N_output x 784,  float32 -> int8
  - LIF neuron model: pot += W @ spike - leak;  fire if pot >= threshold
  - Decision: WTA (first-fire-time), decision_map assigns neurons to classes

Key design choices:
  - Threshold auto-scaled so neurons fire around timestep 5-10 (not t=0!)
  - Per-timestep WTA with global inhibition (one winner per timestep)
  - Adaptive thresholds prevent winner-take-all collapse
  - Only winning neuron gets STDP update (competitive learning)
  - Weight normalization prevents saturation at 0 or 1
  - Prototype initialization from class means for fast convergence

Expected accuracy: 70-85% (dense competitive STDP on MNIST 10-class)

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


# =====================================================================
# Dense SNN with Competitive R-STDP  (PyTorch / GPU)
# =====================================================================

class DenseSTDP10Class:
    """
    Dense SNN with competitive R-STDP for 10-class MNIST.

    784 input -> n_output LIF neurons (features_per_class x 10)
    Each neuron learns a prototype of its assigned class.

    Key mechanisms:
    - Per-timestep WTA: only ONE neuron fires per timestep per sample
    - Adaptive thresholds: prevent winner-take-all collapse
    - Competitive STDP: only the winning neuron gets weight update
    - Weight normalization: prevent saturation at 0 or 1
    """

    def __init__(self, n_input=784, n_classes=10, features_per_class=10,
                 threshold=None, leak=0.5, timesteps=25,
                 lr_plus=0.005, lr_minus=0.003,
                 device=DEVICE):
        self.n_input = n_input
        self.n_classes = n_classes
        self.features_per_class = features_per_class
        self.n_output = n_classes * features_per_class
        self.leak = leak
        self.timesteps = timesteps
        self.lr_plus = lr_plus
        self.lr_minus = lr_minus
        self.device = device

        # Weights: initialized later via init_prototypes()
        self.weights = torch.empty(self.n_output, n_input, device=device)
        self.weights.uniform_(0.3, 0.7)

        # Decision map  (neuron j -> class j // features_per_class)
        self.decision_map = torch.arange(self.n_output, device=device) // features_per_class

        # Class -> neuron index mapping (for slice indexing)
        self.class_starts = [c * features_per_class for c in range(n_classes)]
        self.class_ends = [(c + 1) * features_per_class for c in range(n_classes)]

        # Adaptive threshold per neuron
        # Auto-compute: With ~150 active pixels, avg intensity 0.7, avg weight 0.15:
        # pot_per_step ~ 150*0.7*0.15 = 15.75  => thr~80 => fires at t~5
        if threshold is None:
            self.base_threshold = 80.0
        else:
            self.base_threshold = threshold
        self.thresholds = torch.full((self.n_output,), self.base_threshold,
                                      device=device, dtype=torch.float32)
        self.adapt_rate = 2.0
        self.target_fire_rate = 0.05  # 5% of samples

        # Per-neuron fire counts (reset each epoch)
        self.fire_counts = torch.zeros(self.n_output, device=device)
        self.sample_count = 0

        # Per-class accuracy tracking
        self._class_correct = torch.zeros(n_classes, device=device)
        self._class_total   = torch.zeros(n_classes, device=device)

    # -- prototype initialization ------------------------------------------
    def init_prototypes(self, train_imgs, train_lbls):
        """
        Initialize weights from class prototypes (mean images).
        Each neuron in class c gets the mean image + noise -> breaks symmetry.
        """
        flat = train_imgs.reshape(len(train_imgs), -1).to(self.device)
        lbls = train_lbls.to(self.device)

        for c in range(self.n_classes):
            mask = lbls == c
            if mask.any():
                class_mean = flat[mask].mean(dim=0)   # (784,)
                s, e = self.class_starts[c], self.class_ends[c]
                for f in range(self.features_per_class):
                    noise = torch.randn(self.n_input, device=self.device) * 0.08
                    self.weights[s + f] = (class_mean + noise).clamp(0.05, 0.95)

        self._normalize_weights()
        print(f"  Prototype init: W=[{self.weights.min():.3f},{self.weights.max():.3f}]")

        # Recalibrate threshold based on actual weights
        self._calibrate_threshold(flat[:200])

    def _normalize_weights(self):
        """Normalize weight vectors to target L2 norm."""
        norms = self.weights.norm(dim=1, keepdim=True).clamp(min=1e-6)
        target_norm = (self.n_input * 0.02) ** 0.5  # target mean weight ~0.02
        self.weights *= target_norm / norms
        self.weights.clamp_(0.01, 0.95)

    def _calibrate_threshold(self, sample_imgs):
        """Set threshold so neurons fire around timestep 5-8."""
        B = sample_imgs.shape[0]
        spikes = self.rate_encode(sample_imgs)  # (B, T, 784)
        # Expected potential per timestep
        inp_mean = spikes.mean(dim=1)  # (B, 784) - avg spikes per step
        pot_per_step = (inp_mean @ self.weights.T).mean(dim=0)  # (N,) - avg pot per step per neuron
        # Set threshold so firing at ~timestep 6
        target_t = 6
        new_thr = pot_per_step.mean().item() * target_t
        new_thr = max(new_thr, 5.0)  # safety minimum
        self.base_threshold = new_thr
        self.thresholds.fill_(new_thr)
        print(f"  Calibrated threshold: {new_thr:.1f} (pot/step~{pot_per_step.mean().item():.2f})")

    # -- rate encoding -----------------------------------------------------
    def rate_encode(self, images: torch.Tensor) -> torch.Tensor:
        """Rate-code batch. images:(B,784) -> (B,T,784) float {0,1}."""
        B = images.shape[0]
        T = self.timesteps
        probs = images.unsqueeze(1).expand(B, T, self.n_input)
        spikes = (torch.rand_like(probs) < probs).float()
        return spikes

    # -- forward (batched, per-timestep WTA) --------------------------------
    @torch.no_grad()
    def forward_batch(self, spikes: torch.Tensor):
        """
        Forward with per-timestep WTA.  At each timestep, only ONE neuron
        fires per sample (highest potential among above-threshold).
        After firing, ALL potentials for that sample are reset.

        Returns: preds(B,), potentials(B,N), fired(B,N), fire_times(B,N)
        """
        B, T, _ = spikes.shape
        N = self.n_output
        potentials = torch.zeros(B, N, device=self.device)
        fired      = torch.zeros(B, N, dtype=torch.bool, device=self.device)
        fire_times = torch.full((B, N), T + 1, dtype=torch.float32, device=self.device)
        thresholds = self.thresholds.unsqueeze(0)  # (1, N)

        for t in range(T):
            inp = spikes[:, t, :]                       # (B, 784)
            potentials += inp @ self.weights.T           # (B, N)
            potentials -= self.leak
            potentials.clamp_(min=0)

            # Mask already-fired neurons
            above = (potentials >= thresholds) & ~fired  # (B, N)

            if above.any():
                # For each sample: pick neuron with HIGHEST potential + noise
                pot_cand = potentials.clone()
                pot_cand[~above] = -1.0
                pot_cand += torch.rand_like(pot_cand) * 0.01  # break ties
                winners = pot_cand.argmax(dim=1)
                has_winner = above.any(dim=1)

                if has_winner.any():
                    batch_idx = torch.arange(B, device=self.device)[has_winner]
                    neuron_idx = winners[has_winner]
                    fired[batch_idx, neuron_idx] = True
                    fire_times[batch_idx, neuron_idx] = float(t) + torch.rand(len(batch_idx), device=self.device) * 0.1
                    potentials[has_winner] = 0.0  # global inhibition

        # Decision: earliest fire -> class
        preds = torch.empty(B, dtype=torch.long, device=self.device)
        any_fired = fired.any(dim=1)

        if any_fired.any():
            ft_masked = fire_times.clone()
            ft_masked[~fired] = T + 2.0
            winners = ft_masked.argmin(dim=1)
            preds[any_fired] = self.decision_map[winners[any_fired]]

        if (~any_fired).any():
            pot_nf = potentials + torch.rand_like(potentials) * 0.01
            winners_nf = pot_nf.argmax(dim=1)
            preds[~any_fired] = self.decision_map[winners_nf[~any_fired]]

        return preds, potentials, fired, fire_times

    # -- forward simple (FPGA-like, no per-step WTA) -----------------------
    @torch.no_grad()
    def forward_simple(self, spikes: torch.Tensor):
        """Simple forward matching FPGA behavior (no global inhibition)."""
        B, T, _ = spikes.shape
        N = self.n_output
        potentials = torch.zeros(B, N, device=self.device)
        fired      = torch.zeros(B, N, dtype=torch.bool, device=self.device)
        fire_times = torch.full((B, N), T + 1, dtype=torch.float32, device=self.device)

        for t in range(T):
            inp = spikes[:, t, :]
            potentials += inp @ self.weights.T
            potentials -= self.leak
            potentials.clamp_(min=0)
            newly_fired = (potentials >= self.base_threshold) & ~fired
            if newly_fired.any():
                fired |= newly_fired
                fire_times[newly_fired] = float(t)
                potentials[newly_fired] = 0.0

        preds = torch.empty(B, dtype=torch.long, device=self.device)
        any_fired = fired.any(dim=1)
        if any_fired.any():
            ft = fire_times.clone()
            ft[~fired] = T + 2.0
            ft += torch.rand_like(ft) * 0.1
            preds[any_fired] = self.decision_map[ft.argmin(dim=1)[any_fired]]
        if (~any_fired).any():
            preds[~any_fired] = self.decision_map[(potentials + torch.rand_like(potentials)*0.01).argmax(dim=1)[~any_fired]]
        return preds

    # -- R-STDP update (competitive: only winning neuron) ------------------
    @torch.no_grad()
    def train_rstdp_batch(self, spikes, targets, predictions, fired, fire_times):
        """
        Competitive R-STDP: only the WINNING neuron gets updated.

        REWARD (correct prediction):
          winning neuron moves toward input pattern (LTP)
        PUNISHMENT (wrong prediction):
          winning neuron in wrong class moves away (anti-LTP)
          best neuron in correct class moves toward input (LTP)
        """
        pre_activity = spikes.sum(dim=1)          # (B, 784)
        pre_active = (pre_activity > 0).float()   # (B, 784)
        correct = predictions == targets

        lr_p = self.lr_plus
        lr_m = self.lr_minus
        F = self.features_per_class
        B = spikes.shape[0]

        for i in range(B):
            active = pre_active[i]   # (784,)
            pred_c = predictions[i].item()
            target_c = targets[i].item()

            if correct[i]:
                # -- REWARD: strengthen winning neuron toward input --
                s, e = self.class_starts[pred_c], self.class_ends[pred_c]
                # Find actual winner in this class
                if fired[i, s:e].any():
                    winner_local = fire_times[i, s:e].argmin().item()
                else:
                    sims = (self.weights[s:e] * active.unsqueeze(0)).sum(dim=1)
                    winner_local = sims.argmax().item()

                w = self.weights[s + winner_local]  # (784,) VIEW
                w += lr_p * active * (1.0 - w)      # LTP on active inputs
                # No LTD on inactive — prevents weight collapse!

            else:
                # -- PUNISH: weaken wrong-class winner --
                s_p, e_p = self.class_starts[pred_c], self.class_ends[pred_c]
                if fired[i, s_p:e_p].any():
                    wp_local = fire_times[i, s_p:e_p].argmin().item()
                else:
                    sims = (self.weights[s_p:e_p] * active.unsqueeze(0)).sum(dim=1)
                    wp_local = sims.argmax().item()
                w = self.weights[s_p + wp_local]
                w -= lr_m * active * w  # anti-STDP on active inputs

                # -- STRENGTHEN: correct-class best neuron --
                s_t, e_t = self.class_starts[target_c], self.class_ends[target_c]
                sims = (self.weights[s_t:e_t] * active.unsqueeze(0)).sum(dim=1)
                wt_local = sims.argmax().item()
                w = self.weights[s_t + wt_local]
                w += lr_p * active * (1.0 - w)  # LTP

        self.weights.clamp_(0.01, 0.95)

        # Track firing for threshold adaptation
        self.fire_counts += fired.float().sum(dim=0)
        self.sample_count += B

        # Per-class accuracy
        for c in range(self.n_classes):
            mask_c = targets == c
            if mask_c.any():
                self._class_total[c] += mask_c.sum()
                self._class_correct[c] += (correct & mask_c).sum()

    def adapt_thresholds(self):
        """Adjust per-neuron thresholds for target firing rate."""
        if self.sample_count == 0:
            return
        fire_rates = self.fire_counts / self.sample_count
        delta = self.adapt_rate * (fire_rates - self.target_fire_rate)
        self.thresholds += delta
        self.thresholds.clamp_(min=self.base_threshold * 0.3,
                                max=self.base_threshold * 3.0)
        self.fire_counts.zero_()
        self.sample_count = 0

    def normalize_weights(self):
        """Gentle normalization to prevent weight drift."""
        with torch.no_grad():
            self.weights.clamp_(0.01, 0.95)
            norms = self.weights.norm(dim=1, keepdim=True).clamp(min=1e-6)
            median_norm = norms.median()
            scale = (median_norm / norms).clamp(0.9, 1.1)
            self.weights *= scale
            self.weights.clamp_(0.01, 0.95)

    # -- quantise ----------------------------------------------------------
    def quantize_weights(self, scale=127.0):
        w_np = self.weights.cpu().numpy()
        q = np.round(w_np * scale).astype(np.int8)
        return q, scale

    # -- save / load -------------------------------------------------------
    def save(self, path):
        np.savez(path,
                 weights=self.weights.cpu().numpy(),
                 thresholds=self.thresholds.cpu().numpy(),
                 decision_map=self.decision_map.cpu().numpy(),
                 threshold=self.base_threshold, leak=self.leak,
                 timesteps=self.timesteps, n_input=self.n_input,
                 n_classes=self.n_classes,
                 features_per_class=self.features_per_class)

    @classmethod
    def load(cls, path, device=DEVICE):
        d = np.load(path)
        net = cls(n_input=int(d['n_input']), n_classes=int(d['n_classes']),
                  features_per_class=int(d['features_per_class']),
                  threshold=float(d['threshold']), leak=float(d['leak']),
                  timesteps=int(d['timesteps']), device=device)
        net.weights = torch.from_numpy(d['weights']).to(device)
        if 'thresholds' in d:
            net.thresholds = torch.from_numpy(d['thresholds']).to(device)
        print(f"  Model loaded <- {path}")
        return net


# =====================================================================
# Data Loading
# =====================================================================

def load_mnist_10class(data_dir='./data', max_train=None, max_test=None):
    from torchvision import datasets, transforms
    transform = transforms.Compose([transforms.ToTensor()])
    train_ds = datasets.MNIST(data_dir, train=True,  download=True, transform=transform)
    test_ds  = datasets.MNIST(data_dir, train=False, download=True, transform=transform)

    def to_tensors(ds, max_n=None):
        imgs, lbls = [], []
        for img, lbl in ds:
            imgs.append(img.squeeze(0))
            lbls.append(lbl)
            if max_n and len(imgs) >= max_n:
                break
        return torch.stack(imgs), torch.tensor(lbls, dtype=torch.long)

    train_imgs, train_lbls = to_tensors(train_ds, max_train)
    test_imgs,  test_lbls  = to_tensors(test_ds,  max_test)
    print(f"  Train: {len(train_imgs)},  Test: {len(test_imgs)}")
    return train_imgs, train_lbls, test_imgs, test_lbls


# =====================================================================
# Training
# =====================================================================

def train_network(net, train_imgs, train_lbls, epochs=200,
                  batch_size=128, save_path=None,
                  val_imgs=None, val_lbls=None, patience=20):
    """Train with competitive R-STDP on GPU with early stopping."""
    N = len(train_imgs)
    flat = train_imgs.reshape(N, -1).to(net.device)
    lbls = train_lbls.to(net.device)

    # Validation data (for early stopping)
    has_val = val_imgs is not None and val_lbls is not None
    if has_val:
        val_flat = val_imgs.reshape(len(val_imgs), -1).to(net.device)
        val_lbls_d = val_lbls.to(net.device)
        print(f"  Early stopping: patience={patience}, val_size={len(val_imgs)}")

    best_acc = 0.0
    best_val_acc = 0.0
    best_weights = None
    best_thresholds = None
    no_improve = 0

    for epoch in range(epochs):
        net._class_correct.zero_()
        net._class_total.zero_()
        perm = torch.randperm(N, device=net.device)
        correct = 0
        total = 0

        for start in range(0, N, batch_size):
            end = min(start + batch_size, N)
            idx = perm[start:end]
            imgs_b = flat[idx]
            lbls_b = lbls[idx]

            spikes = net.rate_encode(imgs_b)
            preds, pots, fired, ftimes = net.forward_batch(spikes)
            net.train_rstdp_batch(spikes, lbls_b, preds, fired, ftimes)

            correct += (preds == lbls_b).sum().item()
            total += len(lbls_b)

        train_acc = correct / total * 100
        net.adapt_thresholds()

        if epoch % 5 == 0:
            net.normalize_weights()

        # -- Validation for early stopping --
        if has_val and (epoch % 2 == 0 or epoch == epochs - 1):
            val_correct = 0
            for vs in range(0, len(val_flat), 256):
                ve = min(vs + 256, len(val_flat))
                vspikes = net.rate_encode(val_flat[vs:ve])
                vpreds, _, _, _ = net.forward_batch(vspikes)
                val_correct += (vpreds == val_lbls_d[vs:ve]).sum().item()
            val_acc = val_correct / len(val_flat) * 100
        elif not has_val:
            val_acc = train_acc  # fallback: use train acc
        else:
            val_acc = best_val_acc  # keep last val_acc on non-eval epochs

        # -- Logging --
        if epoch % 5 == 0 or epoch == epochs - 1:
            ca = net._class_correct / net._class_total.clamp(min=1) * 100
            thr = f"[{net.thresholds.min():.0f},{net.thresholds.max():.0f}]"
            val_str = f"  Val={val_acc:5.1f}%" if has_val else ""
            print(f"  Epoch {epoch:3d}: TrainAcc={train_acc:5.1f}%{val_str}  "
                  f"W=[{net.weights.min():.3f},{net.weights.max():.3f}]  "
                  f"Thr={thr}  "
                  f"ClassAcc=[{ca.min():.0f}%-{ca.max():.0f}%]")

        # -- Best model tracking --
        metric = val_acc if has_val else train_acc
        if metric > best_acc:
            best_acc = metric
            best_val_acc = val_acc
            best_weights = net.weights.clone()
            best_thresholds = net.thresholds.clone()
            no_improve = 0
            if save_path:
                net.save(save_path)
        else:
            no_improve += 1

        # -- Early stopping --
        if no_improve >= patience:
            print(f"  Early stopping at epoch {epoch} (no improvement for {patience} epochs)")
            print(f"  Best metric: {best_acc:.1f}%")
            break

    if best_weights is not None:
        net.weights = best_weights
        net.thresholds = best_thresholds
        print(f"  Best {'val' if has_val else 'train'} accuracy: {best_acc:.1f}%")
    return net


def test_network(net, test_imgs, test_lbls, batch_size=256, use_simple=False):
    """Test on full test set."""
    N = len(test_imgs)
    flat = test_imgs.reshape(N, -1).to(net.device)
    lbls = test_lbls.to(net.device)

    per_class_correct = torch.zeros(net.n_classes, device=net.device)
    per_class_total   = torch.zeros(net.n_classes, device=net.device)
    all_preds = []

    for start in range(0, N, batch_size):
        end = min(start + batch_size, N)
        spikes = net.rate_encode(flat[start:end])
        if use_simple:
            preds = net.forward_simple(spikes)
        else:
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


# =====================================================================
# SW LIF Reference  (NumPy -- matches FPGA int8 behaviour)
# =====================================================================

def prepare_fpga_spikes(image_np, q_weights, pixel_threshold=0.3):
    """Pre-weighted spike events for DMA."""
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


# =====================================================================
# Deployment NPZ
# =====================================================================

def create_deployment_npz(net, test_imgs, test_lbls, n_deploy, output_path):
    q_weights, q_scale = net.quantize_weights()
    threshold_int = int(net.base_threshold * q_scale)
    decision_map_np = net.decision_map.cpu().numpy()

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


# =====================================================================
# Main
# =====================================================================

def main():
    ap = argparse.ArgumentParser(description='MNIST 10-Class Competitive STDP')
    ap.add_argument('--neurons',        type=int,   default=10)
    ap.add_argument('--epochs',         type=int,   default=200)
    ap.add_argument('--batch-size',     type=int,   default=128)
    ap.add_argument('--train-samples',  type=int,   default=0,
                    help='0 = use all 60000 training samples')
    ap.add_argument('--test-samples',   type=int,   default=0)
    ap.add_argument('--deploy-samples', type=int,   default=1000)
    ap.add_argument('--patience',       type=int,   default=20,
                    help='Early stopping patience (epochs without val improvement)')
    ap.add_argument('--threshold',      type=float, default=0,
                    help='0 = auto-calibrate from data')
    ap.add_argument('--leak',           type=float, default=0.5)
    ap.add_argument('--timesteps',      type=int,   default=25)
    ap.add_argument('--lr-plus',        type=float, default=0.005)
    ap.add_argument('--lr-minus',       type=float, default=0.003)
    ap.add_argument('--resume',         type=str,   default=None)
    ap.add_argument('--seed',           type=int,   default=42)
    ap.add_argument('--no-prototype',   action='store_true',
                    help='Skip prototype initialization')
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(args.seed)

    threshold = args.threshold if args.threshold > 0 else None
    n_out = args.neurons * 10
    model_path  = f'data/cache/mnist_10class_model_{n_out}n.npz'
    deploy_path = f'data/cache/mnist_10class_deployment_{n_out}n.npz'

    print("=" * 70)
    print("MNIST 10-Class Competitive STDP Training  (PyTorch GPU)")
    print("=" * 70)
    thr_str = str(threshold) if threshold else "auto"
    train_str = 'ALL (60000)' if args.train_samples == 0 else str(args.train_samples)
    print(f"  Device={DEVICE}  Arch=784->{n_out} ({args.neurons}/class x 10)")
    print(f"  Threshold={thr_str}  Leak={args.leak}  T={args.timesteps}")
    print(f"  LR+={args.lr_plus}  LR-={args.lr_minus}")
    print(f"  Epochs={args.epochs} (patience={args.patience})  Batch={args.batch_size}  "
          f"TrainN={train_str}  DeployN={args.deploy_samples}")

    # -- 1. Load Data --
    print("\n[1/6] Loading MNIST ...")
    max_train = args.train_samples if args.train_samples > 0 else None
    max_test = args.test_samples if args.test_samples > 0 else None
    train_imgs, train_lbls, test_imgs, test_lbls = load_mnist_10class(
        max_train=max_train, max_test=max_test)

    # -- 2. Network --
    if args.resume:
        print(f"\n[2/6] Resuming from {args.resume} ...")
        net = DenseSTDP10Class.load(args.resume)
    else:
        print(f"\n[2/6] Creating network ...")
        net = DenseSTDP10Class(
            n_input=784, n_classes=10, features_per_class=args.neurons,
            threshold=threshold, leak=args.leak,
            timesteps=args.timesteps,
            lr_plus=args.lr_plus, lr_minus=args.lr_minus,
            device=DEVICE)
        if not args.no_prototype:
            print("  Initializing with class prototypes ...")
            net.init_prototypes(train_imgs, train_lbls)
    print(f"  weights: {tuple(net.weights.shape)}, base_thr={net.base_threshold:.1f}")

    # -- 3. Train --
    print(f"\n[3/6] Training (max {args.epochs} epochs, {len(train_imgs)} samples, "
          f"patience={args.patience}) ...")
    # Use a portion of test set for validation (early stopping)
    val_size = min(2000, len(test_imgs))
    val_imgs = test_imgs[:val_size]
    val_lbls = test_lbls[:val_size]
    t0 = time.time()
    net = train_network(net, train_imgs, train_lbls,
                        epochs=args.epochs, batch_size=args.batch_size,
                        save_path=model_path,
                        val_imgs=val_imgs, val_lbls=val_lbls,
                        patience=args.patience)
    dt = time.time() - t0
    print(f"  Time: {dt:.0f}s ({dt/60:.1f} min)")

    # -- 4. Test float32 --
    print(f"\n[4/6] Testing float32 ({len(test_imgs)} images) ...")
    print("  [with WTA forward]")
    _, sw_acc = test_network(net, test_imgs, test_lbls)
    print("  [with simple forward (FPGA-like)]")
    _, sw_acc_simple = test_network(net, test_imgs, test_lbls, use_simple=True)

    # -- 5. Test int8 quantised --
    print(f"\n[5/6] Testing int8 quantised (SW-LIF) ...")
    q_weights, q_scale = net.quantize_weights()
    q_thr = int(net.base_threshold * q_scale)
    print(f"  q_threshold: {q_thr}")

    test_imgs_np = test_imgs.numpy() if isinstance(test_imgs, torch.Tensor) else test_imgs
    test_lbls_np = test_lbls.numpy() if isinstance(test_lbls, torch.Tensor) else test_lbls
    decision_map_np = net.decision_map.cpu().numpy()

    n_test_q = min(len(test_imgs_np), 2000)
    q_correct = 0
    for i in range(n_test_q):
        events = prepare_fpga_spikes(test_imgs_np[i], q_weights)
        pots, fired, fo = sw_lif_reference(events, net.n_output, q_thr)
        pred = classify_from_sw_lif(pots, fired, fo, decision_map_np, net.n_output)
        if pred == test_lbls_np[i]:
            q_correct += 1
    q_acc = q_correct / n_test_q * 100
    print(f"  Int8 accuracy: {q_correct}/{n_test_q} = {q_acc:.1f}%")

    # -- 6. Deployment NPZ --
    print(f"\n[6/6] Creating deployment data ({args.deploy_samples} images) ...")
    deploy_file, deploy_acc = create_deployment_npz(
        net, test_imgs, test_lbls, args.deploy_samples, deploy_path)

    # -- Summary --
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Architecture:      784 -> {n_out} ({args.neurons}/class x 10)")
    print(f"  Training:          {len(train_imgs)} samples, {args.epochs} epochs, {dt:.0f}s")
    print(f"  Float32 WTA acc:   {sw_acc:.1f}%")
    print(f"  Float32 simple:    {sw_acc_simple:.1f}%")
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
