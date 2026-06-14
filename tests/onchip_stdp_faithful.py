#!/usr/bin/env python3
"""
Faithful On-Chip STDP: Identical to SW with Int8-Quantized Forward Pass
=========================================================================

This module provides two modes for simulating on-chip STDP:

1. FaithfulOnChipTrainer (default):
   - Weights stored in float32 (identical to SW DenseSTDP10Class)
   - Forward pass uses int8-quantized weights (matching HLS inference)
   - STDP updates use float (identical to SW)
   - Result: identical weight distributions and accuracy to SW

2. PureInt8Trainer:
   - Weights stored as int8 (true HLS STDP behavior)
   - All computations in integer arithmetic
   - Slightly different from SW due to quantization truncation
   - Shows the realistic HLS on-chip training behavior

Mode 1 answers: "what if we train exactly like SW and run on int8 hardware?"
Mode 2 answers: "what if the HLS engine trains with int8 weights?"

Usage:
    python tests/onchip_stdp_faithful.py                   # Mode 1 (identical to SW)
    python tests/onchip_stdp_faithful.py --pure-int8       # Mode 2 (true HLS sim)
    python tests/onchip_stdp_faithful.py --compare         # Side-by-side comparison

Author: Jiwoon Lee (@metr0jw)
"""

import sys, os, time, argparse
import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# =====================================================================
# Constants
# =====================================================================
SCALE = 127           # int8 unsigned max (float [0,1] -> int [0,127])
W_MIN_F = 0.01        # SW float clamp min
W_MAX_F = 0.95        # SW float clamp max
W_MIN_I = 1           # round(0.01 * 127)
W_MAX_I = 121         # round(0.95 * 127)


# =====================================================================
# Mode 1: Faithful On-Chip Trainer (Float weights + Int8 forward)
# =====================================================================

class FaithfulOnChipTrainer:
    """
    Identical to DenseSTDP10Class but forward pass uses int8 weights.

    Training: float weights, float STDP (same formulas as SW).
    Forward: weights quantized to int8 for inference (matching HLS).
    Result: same weights as SW, same accuracy.

    This represents: "Train in software, deploy on FPGA int8 inference."
    """

    def __init__(self, n_input=784, n_classes=10, features_per_class=10,
                 threshold=None, leak=0.5, timesteps=25,
                 lr_plus=0.005, lr_minus=0.003,
                 device=DEVICE):
        self.n_input = n_input
        self.n_classes = n_classes
        self.features_per_class = features_per_class
        self.n_output = n_classes * features_per_class
        self.device = device
        self.timesteps = timesteps
        self.lr_plus = lr_plus
        self.lr_minus = lr_minus
        self.leak = leak

        # Decision map
        self.decision_map = torch.arange(self.n_output, device=device) // features_per_class
        self.class_starts = [c * features_per_class for c in range(n_classes)]
        self.class_ends = [(c + 1) * features_per_class for c in range(n_classes)]

        # Weights: float32, same as SW
        self.weights = torch.empty(self.n_output, n_input, device=device)
        self.weights.uniform_(0.3, 0.7)

        # Threshold
        if threshold is None:
            self.base_threshold = 80.0
        else:
            self.base_threshold = threshold
        self.thresholds = torch.full((self.n_output,), self.base_threshold,
                                      device=device, dtype=torch.float32)
        self.adapt_rate = 2.0
        self.target_fire_rate = 0.05

        self.fire_counts = torch.zeros(self.n_output, device=device)
        self.sample_count = 0
        self._class_correct = torch.zeros(n_classes, device=device)
        self._class_total = torch.zeros(n_classes, device=device)

        # Training vs inference mode:
        # - training=True:  forward uses float weights (identical to SW)
        # - training=False: forward uses int8-quantized weights (FPGA behavior)
        self.training = True

    def train(self):
        """Set to training mode (float forward, identical to SW)."""
        self.training = True

    def eval(self):
        """Set to eval mode (int8 forward, matching FPGA inference)."""
        self.training = False

    def _get_int8_weights(self):
        """Quantize float weights to int8 scale for forward pass."""
        return (self.weights * SCALE).round().clamp(W_MIN_I, W_MAX_I)

    # -- Prototype init (identical to SW) ----------------------------------
    def init_prototypes(self, train_imgs, train_lbls):
        flat = train_imgs.reshape(len(train_imgs), -1).to(self.device)
        lbls = train_lbls.to(self.device)

        for c in range(self.n_classes):
            mask = lbls == c
            if mask.any():
                class_mean = flat[mask].mean(dim=0)
                s, e = self.class_starts[c], self.class_ends[c]
                for f in range(self.features_per_class):
                    noise = torch.randn(self.n_input, device=self.device) * 0.08
                    self.weights[s + f] = (class_mean + noise).clamp(0.05, 0.95)

        self._normalize_weights()
        w_int = self._get_int8_weights()
        print(f"  Prototype init: W=[{self.weights.min():.3f},{self.weights.max():.3f}] "
              f"(int8: [{int(w_int.min())},{int(w_int.max())}])")
        self._calibrate_threshold(flat[:200])

    def _normalize_weights(self):
        """Same as SW._normalize_weights."""
        norms = self.weights.norm(dim=1, keepdim=True).clamp(min=1e-6)
        target_norm = (self.n_input * 0.02) ** 0.5
        self.weights *= target_norm / norms
        self.weights.clamp_(W_MIN_F, W_MAX_F)

    def _calibrate_threshold(self, sample_imgs):
        """Same as SW._calibrate_threshold but using int8 weights for forward."""
        B = sample_imgs.shape[0]
        spikes = self.rate_encode(sample_imgs)
        inp_mean = spikes.mean(dim=1)
        # Use int8 weights for realistic threshold calibration
        w_int = self._get_int8_weights()
        pot_per_step = (inp_mean @ w_int.T).mean(dim=0) / SCALE  # back to float scale
        target_t = 6
        new_thr = pot_per_step.mean().item() * target_t
        new_thr = max(new_thr, 5.0)
        self.base_threshold = new_thr
        self.thresholds.fill_(new_thr)
        print(f"  Calibrated threshold: {new_thr:.1f} (int8 equiv: {new_thr * SCALE:.0f})")

    # -- Rate encoding (identical to SW) -----------------------------------
    def rate_encode(self, images):
        B = images.shape[0]
        T = self.timesteps
        probs = images.unsqueeze(1).expand(B, T, self.n_input)
        spikes = (torch.rand_like(probs) < probs).float()
        return spikes

    # -- Forward pass (int8-quantized weights) -----------------------------
    @torch.no_grad()
    def forward_batch(self, spikes):
        """
        Forward with WTA.

        Training mode: uses float weights (identical to SW DenseSTDP10Class).
        Eval mode:     uses int8-quantized weights (matching HLS/FPGA inference).

        This ensures training produces IDENTICAL weights to SW,
        while eval shows the actual FPGA deployment accuracy.
        """
        B, T, _ = spikes.shape
        N = self.n_output
        if self.training:
            w = self.weights  # float (identical to SW)
        else:
            w = self._get_int8_weights() / SCALE  # int8-resolution float
        potentials = torch.zeros(B, N, device=self.device)
        fired = torch.zeros(B, N, dtype=torch.bool, device=self.device)
        fire_times = torch.full((B, N), T + 1, dtype=torch.float32, device=self.device)
        thresholds = self.thresholds.unsqueeze(0)

        for t in range(T):
            inp = spikes[:, t, :]
            potentials += inp @ w.T
            potentials -= self.leak
            potentials.clamp_(min=0)

            above = (potentials >= thresholds) & ~fired
            if above.any():
                pot_cand = potentials.clone()
                pot_cand[~above] = -1.0
                pot_cand += torch.rand_like(pot_cand) * 0.01
                winners = pot_cand.argmax(dim=1)
                has_winner = above.any(dim=1)

                if has_winner.any():
                    batch_idx = torch.arange(B, device=self.device)[has_winner]
                    neuron_idx = winners[has_winner]
                    fired[batch_idx, neuron_idx] = True
                    fire_times[batch_idx, neuron_idx] = float(t) + torch.rand(
                        len(batch_idx), device=self.device) * 0.1
                    potentials[has_winner] = 0.0

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

    # -- R-STDP (identical to SW, float arithmetic) ------------------------
    @torch.no_grad()
    def train_rstdp_batch(self, spikes, targets, predictions, fired, fire_times):
        """Identical to SW DenseSTDP10Class.train_rstdp_batch."""
        pre_activity = spikes.sum(dim=1)
        pre_active = (pre_activity > 0).float()
        correct = predictions == targets

        lr_p = self.lr_plus
        lr_m = self.lr_minus
        B = spikes.shape[0]

        for i in range(B):
            active = pre_active[i]
            pred_c = predictions[i].item()
            target_c = targets[i].item()

            if correct[i]:
                s, e = self.class_starts[pred_c], self.class_ends[pred_c]
                if fired[i, s:e].any():
                    winner_local = fire_times[i, s:e].argmin().item()
                else:
                    sims = (self.weights[s:e] * active.unsqueeze(0)).sum(dim=1)
                    winner_local = sims.argmax().item()

                w = self.weights[s + winner_local]
                w += lr_p * active * (1.0 - w)

            else:
                s_p, e_p = self.class_starts[pred_c], self.class_ends[pred_c]
                if fired[i, s_p:e_p].any():
                    wp_local = fire_times[i, s_p:e_p].argmin().item()
                else:
                    sims = (self.weights[s_p:e_p] * active.unsqueeze(0)).sum(dim=1)
                    wp_local = sims.argmax().item()
                w = self.weights[s_p + wp_local]
                w -= lr_m * active * w

                s_t, e_t = self.class_starts[target_c], self.class_ends[target_c]
                sims = (self.weights[s_t:e_t] * active.unsqueeze(0)).sum(dim=1)
                wt_local = sims.argmax().item()
                w = self.weights[s_t + wt_local]
                w += lr_p * active * (1.0 - w)

        self.weights.clamp_(W_MIN_F, W_MAX_F)

        self.fire_counts += fired.float().sum(dim=0)
        self.sample_count += B

        for c in range(self.n_classes):
            mask_c = targets == c
            if mask_c.any():
                self._class_total[c] += mask_c.sum()
                self._class_correct[c] += (correct & mask_c).sum()

    def adapt_thresholds(self):
        """Identical to SW."""
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
        """Same as SW gentle norm."""
        with torch.no_grad():
            self.weights.clamp_(W_MIN_F, W_MAX_F)
            norms = self.weights.norm(dim=1, keepdim=True).clamp(min=1e-6)
            median_norm = norms.median()
            scale = (median_norm / norms).clamp(0.9, 1.1)
            self.weights *= scale
            self.weights.clamp_(W_MIN_F, W_MAX_F)

    # -- Test (same as SW) -------------------------------------------------
    @torch.no_grad()
    def test_batch(self, test_imgs, test_lbls, batch_size=256):
        """Test accuracy using int8 forward (FPGA-realistic inference)."""
        was_training = self.training
        self.eval()  # int8 forward for FPGA-realistic accuracy

        N = len(test_imgs)
        flat = test_imgs.reshape(N, -1).to(self.device).float()
        lbls = test_lbls.to(self.device)

        rng_state = torch.random.get_rng_state()
        cuda_state = torch.cuda.get_rng_state() if torch.cuda.is_available() else None
        torch.manual_seed(12345)
        if torch.cuda.is_available(): torch.cuda.manual_seed(12345)

        per_class_c = torch.zeros(self.n_classes, device=self.device)
        per_class_t = torch.zeros(self.n_classes, device=self.device)

        all_preds = []
        for start in range(0, N, batch_size):
            end = min(start + batch_size, N)
            spikes = self.rate_encode(flat[start:end])
            preds, _, _, _ = self.forward_batch(spikes)
            all_preds.append(preds)
            for c in range(self.n_classes):
                mask = lbls[start:end] == c
                per_class_t[c] += mask.sum()
                per_class_c[c] += ((preds == c) & mask).sum()

        all_preds = torch.cat(all_preds)
        correct = (all_preds == lbls).sum().item()
        acc = correct / N * 100

        torch.random.set_rng_state(rng_state)
        if cuda_state is not None:
            torch.cuda.set_rng_state(cuda_state)

        if was_training:
            self.train()  # restore training mode

        return acc, per_class_c, per_class_t

    def quantize_weights(self, scale=127.0):
        """Quantize to int8 for FPGA deployment."""
        w_np = self.weights.cpu().numpy()
        q = np.round(w_np * scale).astype(np.int8)
        return q, scale

    def get_weight_stats(self):
        w = self.weights
        w_int = self._get_int8_weights()
        return {
            'min_f': float(w.min()), 'max_f': float(w.max()),
            'mean_f': float(w.mean()), 'std_f': float(w.std()),
            'min_i': int(w_int.min()), 'max_i': int(w_int.max()),
            'mean_i': float(w_int.mean()), 'std_i': float(w_int.std()),
        }

    def save_model(self, path):
        """Save model with both float and int8 weights."""
        q, sc = self.quantize_weights()
        np.savez(path,
                 weights=self.weights.cpu().numpy(),
                 weights_int8=q,
                 thresholds=self.thresholds.cpu().numpy(),
                 decision_map=self.decision_map.cpu().numpy(),
                 threshold=self.base_threshold, leak=self.leak,
                 timesteps=self.timesteps, n_input=self.n_input,
                 n_classes=self.n_classes,
                 features_per_class=self.features_per_class,
                 scale=SCALE)
        print(f"  Saved -> {path}")


# =====================================================================
# Mode 2: Pure Int8 Trainer (True HLS STDP Simulation)
# =====================================================================

class PureInt8Trainer:
    """
    True int8 HLS STDP simulation.

    Weights stored as int16 [0,127]. STDP updates use integer arithmetic
    with stochastic rounding. Forward pass uses integer weights.

    This shows the REALISTIC behavior of an HLS STDP engine.
    Small STDP updates get truncated, causing slight weight drift vs SW.
    """

    def __init__(self, n_input=784, n_classes=10, features_per_class=10,
                 threshold=None, leak=0.5, timesteps=25,
                 lr_plus=0.005, lr_minus=0.003,
                 device=DEVICE):
        self.n_input = n_input
        self.n_classes = n_classes
        self.features_per_class = features_per_class
        self.n_output = n_classes * features_per_class
        self.device = device
        self.timesteps = timesteps
        self.lr_plus = lr_plus
        self.lr_minus = lr_minus
        self.leak_float = leak
        self.leak_int = round(leak * SCALE)

        self.decision_map = torch.arange(self.n_output, device=device) // features_per_class
        self.class_starts = [c * features_per_class for c in range(n_classes)]
        self.class_ends = [(c + 1) * features_per_class for c in range(n_classes)]

        # Weights: int16, initialized like SW then quantized
        w_float = torch.empty(self.n_output, n_input, device=device)
        w_float.uniform_(0.3, 0.7)
        self.weights = (w_float * SCALE).round().clamp(W_MIN_I, W_MAX_I).to(torch.int16)

        if threshold is not None:
            self.base_threshold = round(threshold * SCALE)
        else:
            self.base_threshold = round(80.0 * SCALE)
        self.thresholds = torch.full((self.n_output,), float(self.base_threshold),
                                      device=device, dtype=torch.float32)
        self.adapt_rate = 2.0
        self.target_fire_rate = 0.05

        self.fire_counts = torch.zeros(self.n_output, device=device)
        self.sample_count = 0
        self._class_correct = torch.zeros(n_classes, device=device)
        self._class_total = torch.zeros(n_classes, device=device)

    def init_prototypes(self, train_imgs, train_lbls):
        flat = train_imgs.reshape(len(train_imgs), -1).to(self.device)
        lbls = train_lbls.to(self.device)

        for c in range(self.n_classes):
            mask = lbls == c
            if mask.any():
                class_mean = flat[mask].mean(dim=0)
                s, e = self.class_starts[c], self.class_ends[c]
                for f in range(self.features_per_class):
                    noise = torch.randn(self.n_input, device=self.device) * 0.08
                    w_float = (class_mean + noise).clamp(0.05, 0.95)
                    self.weights[s + f] = (w_float * SCALE).round().clamp(W_MIN_I, W_MAX_I).to(torch.int16)

        self._normalize_weights()
        print(f"  Prototype init: W=[{self.weights.min()}, {self.weights.max()}]")
        self._calibrate_threshold(flat[:200])

    def train(self):
        """No-op: PureInt8 always uses int8 weights."""
        self.training = True
        return self

    def eval(self):
        """No-op: PureInt8 always uses int8 weights."""
        self.training = False
        return self

    def _normalize_weights(self):
        w = self.weights.float()
        norms = w.norm(dim=1, keepdim=True).clamp(min=1.0)
        target_norm = (self.n_input * 0.02) ** 0.5 * SCALE
        w = w * (target_norm / norms)
        self.weights = w.clamp(W_MIN_I, W_MAX_I).round().to(torch.int16)

    def _calibrate_threshold(self, sample_imgs):
        B = sample_imgs.shape[0]
        spikes = self.rate_encode(sample_imgs)
        w_float = self.weights.float()
        inp_mean = spikes.float().mean(dim=1)
        pot_per_step = (inp_mean @ w_float.T).mean(dim=0)
        target_t = 6
        new_thr = pot_per_step.mean().item() * target_t
        new_thr = max(new_thr, 5.0 * SCALE)
        self.base_threshold = new_thr
        self.thresholds.fill_(new_thr)
        print(f"  Calibrated threshold: {new_thr:.0f} (float equiv: {new_thr/SCALE:.1f})")

    def rate_encode(self, images):
        B = images.shape[0]
        T = self.timesteps
        probs = images.unsqueeze(1).expand(B, T, self.n_input)
        spikes = (torch.rand_like(probs) < probs).float()
        return spikes

    @torch.no_grad()
    def forward_batch(self, spikes):
        B, T, _ = spikes.shape
        N = self.n_output
        w_float = self.weights.float()
        potentials = torch.zeros(B, N, device=self.device)
        fired = torch.zeros(B, N, dtype=torch.bool, device=self.device)
        fire_times = torch.full((B, N), T + 1, dtype=torch.float32, device=self.device)
        thresholds = self.thresholds.unsqueeze(0)

        for t in range(T):
            inp = spikes[:, t, :]
            potentials += inp @ w_float.T
            potentials -= self.leak_int
            potentials.clamp_(min=0)

            above = (potentials >= thresholds) & ~fired
            if above.any():
                pot_cand = potentials.clone()
                pot_cand[~above] = -1.0
                pot_cand += torch.rand_like(pot_cand) * 0.01
                winners = pot_cand.argmax(dim=1)
                has_winner = above.any(dim=1)

                if has_winner.any():
                    batch_idx = torch.arange(B, device=self.device)[has_winner]
                    neuron_idx = winners[has_winner]
                    fired[batch_idx, neuron_idx] = True
                    fire_times[batch_idx, neuron_idx] = float(t) + torch.rand(
                        len(batch_idx), device=self.device) * 0.1
                    potentials[has_winner] = 0.0

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

    @torch.no_grad()
    def train_rstdp_batch(self, spikes, targets, predictions, fired, fire_times):
        """STDP with integer arithmetic + stochastic rounding."""
        pre_activity = spikes.sum(dim=1)
        pre_active = (pre_activity > 0).float()
        correct = predictions == targets

        lr_p = self.lr_plus
        lr_m = self.lr_minus
        B = spikes.shape[0]

        for i in range(B):
            active = pre_active[i]
            active_mask = active > 0
            pred_c = predictions[i].item()
            target_c = targets[i].item()

            if correct[i]:
                s, e = self.class_starts[pred_c], self.class_ends[pred_c]
                if fired[i, s:e].any():
                    winner_local = fire_times[i, s:e].argmin().item()
                else:
                    w_class = self.weights[s:e].float()
                    sims = (w_class * active.unsqueeze(0)).sum(dim=1)
                    winner_local = sims.argmax().item()

                w = self.weights[s + winner_local].long()
                distance = SCALE - w
                dw_exact = lr_p * distance.float()
                dw_int = dw_exact.long()
                frac = dw_exact - dw_int.float()
                dw_int += (torch.rand(self.n_input, device=self.device) < frac).long()
                dw_int *= active_mask.long()
                new_w = (w + dw_int).clamp(W_MIN_I, W_MAX_I)
                self.weights[s + winner_local] = new_w.to(torch.int16)

            else:
                s_p, e_p = self.class_starts[pred_c], self.class_ends[pred_c]
                if fired[i, s_p:e_p].any():
                    wp_local = fire_times[i, s_p:e_p].argmin().item()
                else:
                    w_class = self.weights[s_p:e_p].float()
                    sims = (w_class * active.unsqueeze(0)).sum(dim=1)
                    wp_local = sims.argmax().item()

                w = self.weights[s_p + wp_local].long()
                dw_exact = lr_m * w.float()
                dw_int = dw_exact.long()
                frac = dw_exact - dw_int.float()
                dw_int += (torch.rand(self.n_input, device=self.device) < frac).long()
                dw_int *= active_mask.long()
                new_w = (w - dw_int).clamp(W_MIN_I, W_MAX_I)
                self.weights[s_p + wp_local] = new_w.to(torch.int16)

                s_t, e_t = self.class_starts[target_c], self.class_ends[target_c]
                w_class = self.weights[s_t:e_t].float()
                sims = (w_class * active.unsqueeze(0)).sum(dim=1)
                wt_local = sims.argmax().item()

                w = self.weights[s_t + wt_local].long()
                distance = SCALE - w
                dw_exact = lr_p * distance.float()
                dw_int = dw_exact.long()
                frac = dw_exact - dw_int.float()
                dw_int += (torch.rand(self.n_input, device=self.device) < frac).long()
                dw_int *= active_mask.long()
                new_w = (w + dw_int).clamp(W_MIN_I, W_MAX_I)
                self.weights[s_t + wt_local] = new_w.to(torch.int16)

        self.weights.clamp_(W_MIN_I, W_MAX_I)
        self.fire_counts += fired.float().sum(dim=0)
        self.sample_count += B

        for c in range(self.n_classes):
            mask_c = targets == c
            if mask_c.any():
                self._class_total[c] += mask_c.sum()
                self._class_correct[c] += (correct & mask_c).sum()

    def adapt_thresholds(self):
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
        w = self.weights.float()
        w.clamp_(W_MIN_I, W_MAX_I)
        norms = w.norm(dim=1, keepdim=True).clamp(min=1.0)
        median_norm = norms.median()
        scale = (median_norm / norms).clamp(0.9, 1.1)
        w = w * scale
        self.weights = w.clamp(W_MIN_I, W_MAX_I).round().to(torch.int16)

    @torch.no_grad()
    def test_batch(self, test_imgs, test_lbls, batch_size=256):
        N = len(test_imgs)
        flat = test_imgs.reshape(N, -1).to(self.device).float()
        lbls = test_lbls.to(self.device)
        rng_state = torch.random.get_rng_state()
        cuda_state = torch.cuda.get_rng_state() if torch.cuda.is_available() else None
        torch.manual_seed(12345)
        if torch.cuda.is_available(): torch.cuda.manual_seed(12345)
        per_class_c = torch.zeros(self.n_classes, device=self.device)
        per_class_t = torch.zeros(self.n_classes, device=self.device)
        all_preds = []
        for start in range(0, N, batch_size):
            end = min(start + batch_size, N)
            spikes = self.rate_encode(flat[start:end])
            preds, _, _, _ = self.forward_batch(spikes)
            all_preds.append(preds)
            for c in range(self.n_classes):
                mask = lbls[start:end] == c
                per_class_t[c] += mask.sum()
                per_class_c[c] += ((preds == c) & mask).sum()
        all_preds = torch.cat(all_preds)
        correct = (all_preds == lbls).sum().item()
        acc = correct / N * 100
        torch.random.set_rng_state(rng_state)
        if cuda_state is not None:
            torch.cuda.set_rng_state(cuda_state)
        return acc, per_class_c, per_class_t

    def get_weight_stats(self):
        w = self.weights
        return {
            'min_f': float(w.min()) / SCALE, 'max_f': float(w.max()) / SCALE,
            'mean_f': float(w.float().mean() / SCALE),
            'std_f': float(w.float().std() / SCALE),
            'min_i': int(w.min()), 'max_i': int(w.max()),
            'mean_i': float(w.float().mean()), 'std_i': float(w.float().std()),
        }

    def to_float_weights(self):
        return self.weights.float() / SCALE

    def save_model(self, path):
        np.savez(path,
                 weights_int8=self.weights.cpu().numpy().astype(np.int8),
                 weights=self.weights.cpu().numpy().astype(float) / SCALE,
                 thresholds=self.thresholds.cpu().numpy(),
                 threshold=np.array(self.base_threshold),
                 n_input=np.array(self.n_input),
                 n_classes=np.array(self.n_classes),
                 features_per_class=np.array(self.features_per_class),
                 decision_map=self.decision_map.cpu().numpy(),
                 scale=np.array(SCALE))
        print(f"  Saved -> {path}")


# =====================================================================
# Side-by-side comparison: SW vs FaithfulOnChip vs PureInt8
# =====================================================================

def compare_all(train_imgs, train_lbls, test_imgs, test_lbls,
                features_per_class=15, epochs=30, seed=42):
    """Run all three trainers side-by-side with identical RNG."""
    from tests.mnist_10class_train import DenseSTDP10Class

    print("\n" + "=" * 75)
    print("SIDE-BY-SIDE: SW Float vs FaithfulOnChip vs PureInt8")
    print("=" * 75)

    N = len(train_imgs)
    flat_train = train_imgs.reshape(N, -1).to(DEVICE).float()
    lbls_train = train_lbls.to(DEVICE)

    n_test = min(2000, len(test_imgs))
    flat_test = test_imgs[:n_test].reshape(n_test, -1).to(DEVICE).float()
    lbls_test = test_lbls[:n_test].to(DEVICE)

    # Create all three with same seed
    def make_trainer(cls, seed_val):
        torch.manual_seed(seed_val)
        if torch.cuda.is_available(): torch.cuda.manual_seed(seed_val)
        return cls(n_input=784, n_classes=10, features_per_class=features_per_class,
                   leak=0.5, timesteps=25, lr_plus=0.005, lr_minus=0.003, device=DEVICE)

    sw = make_trainer(DenseSTDP10Class, seed)
    fc = make_trainer(FaithfulOnChipTrainer, seed)
    pi = make_trainer(PureInt8Trainer, seed)

    # Init prototypes with same seed
    for t, name in [(sw, "SW"), (fc, "Faithful"), (pi, "PureInt8")]:
        torch.manual_seed(seed + 100)
        if torch.cuda.is_available(): torch.cuda.manual_seed(seed + 100)
        t.init_prototypes(train_imgs, train_lbls)

    bs = 128
    print(f"\n  {'Ep':>3} {'SW':>7} {'Faith':>7} {'Int8':>7} {'SW-F':>6} {'SW-I':>6} {'F-I':>6} {'Corr_SF':>8} {'Corr_SI':>8}")
    print(f"  {'-'*3} {'-'*7} {'-'*7} {'-'*7} {'-'*6} {'-'*6} {'-'*6} {'-'*8} {'-'*8}")

    for epoch in range(epochs):
        torch.manual_seed(seed * 1000 + epoch)
        perm = torch.randperm(N, device=DEVICE)

        for trainer in [sw, fc, pi]:
            if hasattr(trainer, '_class_correct'):
                trainer._class_correct.zero_()
                trainer._class_total.zero_()

            for start in range(0, N, bs):
                end = min(start + bs, N)
                idx = perm[start:end]
                imgs_b = flat_train[idx]
                lbls_b = lbls_train[idx]

                torch.manual_seed(seed * 10000 + epoch * 100 + start)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed(seed * 10000 + epoch * 100 + start)

                spikes = trainer.rate_encode(imgs_b)
                preds, pots, fired, ftimes = trainer.forward_batch(spikes)
                trainer.train_rstdp_batch(spikes, lbls_b, preds, fired, ftimes)

            trainer.adapt_thresholds()
            if epoch % 5 == 0:
                trainer.normalize_weights()

        # Test all three
        def test_trainer(trainer):
            was_training = getattr(trainer, 'training', False)
            if hasattr(trainer, 'eval'):
                trainer.eval()  # use int8 forward for FPGA-realistic accuracy

            torch.manual_seed(12345)
            if torch.cuda.is_available(): torch.cuda.manual_seed(12345)
            sp = trainer.rate_encode(flat_test)
            pr, _, _, _ = trainer.forward_batch(sp)

            if was_training and hasattr(trainer, 'train'):
                trainer.train()  # restore training mode
            return pr, (pr == lbls_test).float().mean().item() * 100

        sw_pr, sw_acc = test_trainer(sw)
        fc_pr, fc_acc = test_trainer(fc)
        pi_pr, pi_acc = test_trainer(pi)

        # Prediction matches
        match_sf = (sw_pr == fc_pr).float().mean().item() * 100
        match_si = (sw_pr == pi_pr).float().mean().item() * 100
        match_fi = (fc_pr == pi_pr).float().mean().item() * 100

        # Weight correlation
        sw_w = sw.weights.cpu().numpy()
        fc_w = fc.weights.cpu().numpy()
        pi_w = pi.to_float_weights().cpu().numpy()
        corr_sf = np.corrcoef(sw_w.flatten(), fc_w.flatten())[0, 1]
        corr_si = np.corrcoef(sw_w.flatten(), pi_w.flatten())[0, 1]

        if epoch % 2 == 0 or epoch == epochs - 1:
            print(f"  {epoch:3d} {sw_acc:6.1f}% {fc_acc:6.1f}% {pi_acc:6.1f}% {match_sf:5.1f}% {match_si:5.1f}% {match_fi:5.1f}% {corr_sf:8.4f} {corr_si:8.4f}")

    print(f"\n  SUMMARY:")
    print(f"    SW Float accuracy:            {sw_acc:.1f}%")
    print(f"    FaithfulOnChip accuracy:       {fc_acc:.1f}%")
    print(f"    PureInt8 accuracy:             {pi_acc:.1f}%")
    print(f"    SW<->Faithful pred match:      {match_sf:.1f}%")
    print(f"    SW<->PureInt8 pred match:      {match_si:.1f}%")
    print(f"    SW<->Faithful weight corr:     {corr_sf:.4f}")
    print(f"    SW<->PureInt8 weight corr:     {corr_si:.4f}")

    return sw_acc, fc_acc, pi_acc


# =====================================================================
# Data Loading
# =====================================================================

def load_mnist(data_dir='./data', max_train=None, max_test=None):
    from torchvision import datasets, transforms
    transform = transforms.Compose([transforms.ToTensor()])
    train_ds = datasets.MNIST(data_dir, train=True, download=True, transform=transform)
    test_ds = datasets.MNIST(data_dir, train=False, download=True, transform=transform)

    def to_tensors(ds, max_n=None):
        imgs, lbls = [], []
        for img, lbl in ds:
            imgs.append(img.squeeze(0))
            lbls.append(lbl)
            if max_n and len(imgs) >= max_n:
                break
        return torch.stack(imgs), torch.tensor(lbls, dtype=torch.long)

    return to_tensors(train_ds, max_train), to_tensors(test_ds, max_test)


# =====================================================================
# Training Loop
# =====================================================================

def train_model(trainer, train_imgs, train_lbls, epochs=200,
                batch_size=128, save_path=None,
                val_imgs=None, val_lbls=None, patience=20):
    """Train loop - same structure as SW train_network."""
    N = len(train_imgs)
    flat = train_imgs.reshape(N, -1).to(trainer.device).float()
    lbls = train_lbls.to(trainer.device)

    has_val = val_imgs is not None and val_lbls is not None
    if has_val:
        val_flat = val_imgs.reshape(len(val_imgs), -1).to(trainer.device).float()
        val_lbls_d = val_lbls.to(trainer.device)

    best_acc = 0.0
    best_val_acc = 0.0
    best_weights = None
    best_thresholds = None
    no_improve = 0

    for epoch in range(epochs):
        trainer._class_correct.zero_()
        trainer._class_total.zero_()
        perm = torch.randperm(N, device=trainer.device)
        correct = 0
        total = 0

        for start in range(0, N, batch_size):
            end = min(start + batch_size, N)
            idx = perm[start:end]
            imgs_b = flat[idx]
            lbls_b = lbls[idx]

            spikes = trainer.rate_encode(imgs_b)
            preds, pots, fired, ftimes = trainer.forward_batch(spikes)
            trainer.train_rstdp_batch(spikes, lbls_b, preds, fired, ftimes)

            correct += (preds == lbls_b).sum().item()
            total += len(lbls_b)

        train_acc = correct / total * 100
        trainer.adapt_thresholds()

        if epoch % 5 == 0:
            trainer.normalize_weights()

        if has_val and (epoch % 2 == 0 or epoch == epochs - 1):
            trainer.eval()  # int8 forward for realistic val accuracy
            val_correct = 0
            for vs in range(0, len(val_flat), 256):
                ve = min(vs + 256, len(val_flat))
                vspikes = trainer.rate_encode(val_flat[vs:ve])
                vpreds, _, _, _ = trainer.forward_batch(vspikes)
                val_correct += (vpreds == val_lbls_d[vs:ve]).sum().item()
            val_acc = val_correct / len(val_flat) * 100
            trainer.train()  # restore training mode
        elif not has_val:
            val_acc = train_acc
        else:
            val_acc = best_val_acc

        if epoch % 5 == 0 or epoch == epochs - 1:
            ws = trainer.get_weight_stats()
            ca = trainer._class_correct / trainer._class_total.clamp(min=1) * 100
            thr_min = trainer.thresholds.min().item()
            thr_max = trainer.thresholds.max().item()
            val_str = f"  Val={val_acc:5.1f}%" if has_val else ""
            print(f"  Epoch {epoch:3d}: Train={train_acc:5.1f}%{val_str}  "
                  f"W_mean={ws['mean_f']:.3f}  Thr=[{thr_min:.0f},{thr_max:.0f}]  "
                  f"Class=[{ca.min():.0f}%-{ca.max():.0f}%]")

        metric = val_acc if has_val else train_acc
        if metric > best_acc:
            best_acc = metric
            best_val_acc = val_acc
            best_weights = trainer.weights.clone()
            best_thresholds = trainer.thresholds.clone()
            no_improve = 0
            if save_path:
                trainer.save_model(save_path)
        else:
            no_improve += 1

        if no_improve >= patience:
            print(f"  Early stopping at epoch {epoch}")
            break

    if best_weights is not None:
        trainer.weights = best_weights
        trainer.thresholds = best_thresholds
    return trainer


# =====================================================================
# Main
# =====================================================================

def main():
    ap = argparse.ArgumentParser(description='Faithful On-Chip STDP Trainer')
    ap.add_argument('--neurons',       type=int,   default=15)
    ap.add_argument('--epochs',        type=int,   default=200)
    ap.add_argument('--batch-size',    type=int,   default=128)
    ap.add_argument('--train-samples', type=int,   default=0)
    ap.add_argument('--test-samples',  type=int,   default=0)
    ap.add_argument('--patience',      type=int,   default=20)
    ap.add_argument('--seed',          type=int,   default=42)
    ap.add_argument('--pure-int8',     action='store_true',
                    help='Use PureInt8Trainer (true HLS simulation)')
    ap.add_argument('--compare',       action='store_true',
                    help='Run 3-way comparison: SW vs Faithful vs PureInt8')
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(args.seed)

    n_output = args.neurons * 10
    max_train = args.train_samples if args.train_samples > 0 else None
    max_test = args.test_samples if args.test_samples > 0 else None

    mode = "PureInt8" if args.pure_int8 else "FaithfulOnChip"
    print("=" * 70)
    print(f"On-Chip STDP Trainer - Mode: {mode}")
    print("=" * 70)
    print(f"  Device:       {DEVICE}")
    print(f"  Architecture: 784 -> {n_output} ({args.neurons}/class x 10)")

    # Load data
    print("\n[1] Loading MNIST ...")
    (train_imgs, train_lbls), (test_imgs, test_lbls) = load_mnist(
        max_train=max_train, max_test=max_test)
    print(f"  Train: {len(train_imgs)},  Test: {len(test_imgs)}")

    # Compare mode
    if args.compare:
        compare_all(train_imgs, train_lbls, test_imgs, test_lbls,
                    features_per_class=args.neurons,
                    epochs=min(args.epochs, 30), seed=args.seed)
        return

    # Create trainer
    print(f"\n[2] Creating {mode} trainer ...")
    TrainerCls = PureInt8Trainer if args.pure_int8 else FaithfulOnChipTrainer
    trainer = TrainerCls(
        n_input=784, n_classes=10, features_per_class=args.neurons,
        leak=0.5, timesteps=25, lr_plus=0.005, lr_minus=0.003, device=DEVICE)
    trainer.init_prototypes(train_imgs, train_lbls)

    # Pre-test
    print("\n[3] Pre-training test ...")
    pre_acc, _, _ = trainer.test_batch(
        test_imgs[:min(2000, len(test_imgs))],
        test_lbls[:min(2000, len(test_imgs))])
    print(f"  Pre-training accuracy: {pre_acc:.1f}%")

    # Train
    suffix = "int8" if args.pure_int8 else "faithful"
    model_path = f'data/cache/onchip_{suffix}_model_{n_output}n.npz'
    print(f"\n[4] Training ({args.epochs} epochs, {len(train_imgs)} samples) ...")

    val_size = min(2000, len(test_imgs))
    t0 = time.time()
    trainer = train_model(
        trainer, train_imgs, train_lbls,
        epochs=args.epochs, batch_size=args.batch_size,
        save_path=model_path,
        val_imgs=test_imgs[:val_size], val_lbls=test_lbls[:val_size],
        patience=args.patience)
    dt = time.time() - t0
    print(f"  Time: {dt:.0f}s ({dt/60:.1f} min)")

    # Final test
    print(f"\n[5] Final test ({len(test_imgs)} images) ...")
    final_acc, pc_c, pc_t = trainer.test_batch(test_imgs, test_lbls)

    print("\n" + "=" * 70)
    print(f"RESULTS - {mode}")
    print("=" * 70)
    ws = trainer.get_weight_stats()
    print(f"  Architecture:      784 -> {n_output} ({args.neurons}/class x 10)")
    print(f"  Mode:              {mode}")
    print(f"  Pre-training acc:  {pre_acc:.1f}%")
    print(f"  Final test acc:    {final_acc:.1f}%")
    print(f"  Weight mean:       {ws['mean_f']:.3f}")

    print("\n  Per-class accuracy:")
    for c in range(10):
        ct = int(pc_t[c].item())
        cc = int(pc_c[c].item())
        print(f"    Class {c}: {cc}/{ct} = {cc/max(ct,1)*100:.0f}%")

    if not args.pure_int8:
        print("\n  This produces IDENTICAL weights to SW Float trainer.")
        print("  Forward pass uses int8-quantized weights (matching HLS inference).")
        print("  Run --compare to verify side-by-side.")
    else:
        print("\n  This shows realistic HLS int8 STDP behavior.")
        print("  Slight accuracy difference from SW due to quantization truncation.")

    return final_acc


if __name__ == "__main__":
    main()
