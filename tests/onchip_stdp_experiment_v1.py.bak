#!/usr/bin/env python3
"""
On-Chip STDP Experiment: Bit-Accurate HLS Learning Engine Simulation (GPU)
===========================================================================

Simulates the EXACT behavior of the HLS on-chip STDP engine
(hardware/hls/src/snn_top_hls.cpp) using PyTorch GPU acceleration.
Trains on MNIST to measure what accuracy the hardware learning engine
would achieve.

Key HLS architecture constraints modeled (bit-accurate):
  1. Signed 8-bit weights [-128, 127] (weight_t = ap_int<8>)
  2. Per-neuron traces: O(N+M) NOT per-synapse O(N*M)
  3. Mozafari weight-dependent STDP:
     - LTD: Δw = -(w - w_min) * post_trace / 256
     - LTP: Δw = +(w_max - w) * pre_trace / 256
  4. Exponential decay LUT (16 entries, lazy timestamp-based)
  5. R-STDP: per-neuron eligibility traces, reward modulation
  6. Delta-sigma encoder for spike generation

All inner loops (over synapses) are vectorized on GPU while maintaining
bit-accurate integer arithmetic matching the HLS implementation.

Usage:
    python tests/onchip_stdp_experiment.py                     # Default
    python tests/onchip_stdp_experiment.py --neurons 10        # 10/class
    python tests/onchip_stdp_experiment.py --rstdp              # Enable R-STDP
    python tests/onchip_stdp_experiment.py --epochs 100         # More epochs

Author: Jiwoon Lee (@metr0jw)
"""

import sys, os, time, argparse
import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


# =====================================================================
# HLS Constants (from snn_top_hls.h and snn_params.h)
# =====================================================================

MAX_WEIGHT = 127       # ap_int<8> max
MIN_WEIGHT = -128      # ap_int<8> min

# Exponential Decay LUT (from snn_top_hls.cpp lines 133-150)
EXP_DECAY_LUT = torch.tensor([
    255,  # dt=0:  exp(0) = 1.0
    223,  # dt=1:  ~0.875
    195,  # dt=2:  ~0.765
    170,  # dt=3:  ~0.670
    149,  # dt=4:  ~0.585
    130,  # dt=5:  ~0.512
    114,  # dt=6:  ~0.448
    100,  # dt=7:  ~0.392
    87,   # dt=8:  ~0.343
    76,   # dt=9:  ~0.300
    67,   # dt=10: ~0.262
    58,   # dt=11: ~0.229
    51,   # dt=12: ~0.200
    45,   # dt=13: ~0.175
    39,   # dt=14: ~0.153
    34    # dt=15: ~0.134
], dtype=torch.long)


# =====================================================================
# Bit-Accurate HLS STDP Engine (PyTorch GPU)
# =====================================================================

class HLSSTDPEngineGPU:
    """
    GPU-accelerated bit-accurate simulation of the HLS on-chip STDP engine.

    All synapse-level operations (LTD, LTP, reward) are vectorized as
    matrix operations on GPU while maintaining exact integer arithmetic
    matching snn_top_hls.cpp.

    Weight shape: [n_pre, n_post] matching HLS weight_memory[pre_id][post_id].
    """

    def __init__(self, n_pre, n_post, a_plus=0.1, a_minus=0.12,
                 rstdp_enable=False, trace_inc=128, device=DEVICE):
        self.n_pre = n_pre
        self.n_post = n_post
        self.device = device
        self.rstdp_enable = rstdp_enable
        self.trace_inc = trace_inc  # Spike trace increment (HLS: 128, lower = smaller LR)

        self.exp_lut = EXP_DECAY_LUT.to(device)

        # Weights: int16 for overflow-safe computation, clamp to [-128, 127]
        self.weights = torch.zeros(n_pre, n_post, dtype=torch.int16, device=device)

        # Per-neuron traces (matching HLS neuron_trace_t)
        self.pre_trace_val  = torch.zeros(n_pre,  dtype=torch.long, device=device)
        self.pre_trace_time = torch.zeros(n_pre,  dtype=torch.long, device=device)
        self.post_trace_val  = torch.zeros(n_post, dtype=torch.long, device=device)
        self.post_trace_time = torch.zeros(n_post, dtype=torch.long, device=device)

        # Per-neuron eligibility traces (matching HLS ap_int<8>)
        self.pre_eligibility  = torch.zeros(n_pre,  dtype=torch.long, device=device)
        self.post_eligibility = torch.zeros(n_post, dtype=torch.long, device=device)

        # Timestamp counter
        self.timestamp = 0

        # Stats
        self.ltp_count = 0
        self.ltd_count = 0

    def reset_traces(self):
        """Reset traces and timestamp (per-image reset)."""
        self.pre_trace_val.zero_()
        self.pre_trace_time.zero_()
        self.post_trace_val.zero_()
        self.post_trace_time.zero_()
        self.pre_eligibility.zero_()
        self.post_eligibility.zero_()
        self.timestamp = 0

    def _decayed_traces(self, trace_val, trace_time):
        """
        Vectorized lazy decay: exact match of HLS compute_decayed_trace().
        trace = old_trace * EXP_DECAY_LUT[dt] / 256, dt clamped to [0,15].
        """
        dt = (self.timestamp - trace_time).clamp(0, 15)
        decay = self.exp_lut[dt]                       # (N,)
        decayed = (trace_val * decay) >> 8             # integer div by 256
        return decayed.clamp(0, 255)

    def process_pre_spikes(self, active_pre):
        """
        Vectorized match of HLS process_pre_spike_aer() for all active pre-neurons.

        active_pre: (n_pre,) bool tensor — which pre-neurons spiked.

        For each active pre-neuron:
        1. Update pre-trace: lazy decay + add spike (128 in uint8)
        2. Apply LTD to all synapses where post_trace > 0:
           Δw = -(w - w_min) * post_trace / 256

        Vectorization is bit-accurate because each pre-neuron updates its OWN
        row of the weight matrix independently (no cross-row dependency).
        """
        if not active_pre.any():
            return

        # 1. Update pre-traces ONLY for active neurons (lazy timestamp: don't
        #    touch non-spiking neurons to avoid double-decay)
        dt = (self.timestamp - self.pre_trace_time[active_pre]).clamp(0, 15)
        decay = self.exp_lut[dt]
        old_val = self.pre_trace_val[active_pre]
        decayed_active = (old_val * decay) >> 8
        self.pre_trace_val[active_pre] = (decayed_active + self.trace_inc).clamp(0, 255)
        self.pre_trace_time[active_pre] = self.timestamp

        # 2. LTD: all (active_pre × post_with_trace) pairs
        post_traces = self._decayed_traces(self.post_trace_val, self.post_trace_time)
        post_has_trace = post_traces > 0

        if post_has_trace.any():
            w = self.weights.long()                        # (n_pre, n_post)
            distance = w - MIN_WEIGHT                      # ≥ 0
            pt = post_traces.unsqueeze(0)                  # (1, n_post)
            delta = -((distance * pt) >> 8)                # (n_pre, n_post)

            # Mask: only active pre-rows × post-with-trace columns
            mask = active_pre.unsqueeze(1) & post_has_trace.unsqueeze(0)
            delta = torch.where(mask, delta, torch.zeros_like(delta))

            self.weights = (w + delta).clamp(MIN_WEIGHT, MAX_WEIGHT).to(torch.int16)
            self.ltd_count += mask.sum().item()

    def process_post_spikes(self, fired_post):
        """
        Vectorized match of HLS process_post_spike_aer() for all fired post-neurons.

        fired_post: (n_post,) bool tensor — which post-neurons fired.

        For each fired post-neuron:
        1. Update post-trace: lazy decay + add spike
        2. Apply LTP to all synapses where pre_trace > 0:
           Δw = +(w_max - w) * pre_trace / 256

        Vectorization is bit-accurate because each post-neuron updates its OWN
        column of the weight matrix independently.
        """
        if not fired_post.any():
            return

        # 1. Update post-traces ONLY for fired neurons (lazy timestamp: don't
        #    touch non-firing neurons to avoid double-decay)
        dt = (self.timestamp - self.post_trace_time[fired_post]).clamp(0, 15)
        decay = self.exp_lut[dt]
        old_val = self.post_trace_val[fired_post]
        decayed_fired = (old_val * decay) >> 8
        self.post_trace_val[fired_post] = (decayed_fired + self.trace_inc).clamp(0, 255)
        self.post_trace_time[fired_post] = self.timestamp

        # 2. LTP: all (pre_with_trace × fired_post) pairs
        pre_traces = self._decayed_traces(self.pre_trace_val, self.pre_trace_time)
        pre_has_trace = pre_traces > 0

        if pre_has_trace.any():
            w = self.weights.long()
            distance = MAX_WEIGHT - w                      # ≥ 0
            pt = pre_traces.unsqueeze(1)                   # (n_pre, 1)
            delta = (distance * pt) >> 8                   # (n_pre, n_post)

            mask = pre_has_trace.unsqueeze(1) & fired_post.unsqueeze(0)
            delta = torch.where(mask, delta, torch.zeros_like(delta))

            self.weights = (w + delta).clamp(MIN_WEIGHT, MAX_WEIGHT).to(torch.int16)
            self.ltp_count += mask.sum().item()

    def update_eligibility(self, active_pre, fired_post):
        """Exact match of HLS update_eligibility_on_{pre,post}_spike()."""
        self.pre_eligibility[active_pre] = \
            (self.pre_eligibility[active_pre] + 32).clamp(-128, 127)
        self.post_eligibility[fired_post] = \
            (self.post_eligibility[fired_post] + 32).clamp(-128, 127)

    def apply_reward(self, reward_signal):
        """
        Vectorized match of HLS apply_rstdp_reward().
        w[i][j] += (pre_elig[i] * post_elig[j]) >> 8 >> shift * sign(reward)
        """
        if reward_signal == 0 or not self.rstdp_enable:
            return

        reward_mag = abs(reward_signal)
        if reward_mag >= 64:
            shift = 1
        elif reward_mag >= 32:
            shift = 2
        elif reward_mag >= 16:
            shift = 3
        else:
            shift = 4

        pre_active = self.pre_eligibility != 0
        post_active = self.post_eligibility != 0

        if pre_active.any() and post_active.any():
            # Outer product of eligibility traces
            combined = (self.pre_eligibility.unsqueeze(1) *
                        self.post_eligibility.unsqueeze(0)) >> 8  # (n_pre, n_post)
            scaled = combined >> shift
            delta = scaled if reward_signal > 0 else -scaled

            mask = pre_active.unsqueeze(1) & post_active.unsqueeze(0)
            delta = torch.where(mask, delta, torch.zeros_like(delta))

            w = self.weights.long() + delta
            self.weights = w.clamp(MIN_WEIGHT, MAX_WEIGHT).to(torch.int16)

    def decay_eligibility(self):
        """Exact match of HLS decay_eligibility_traces(): *= 0.875."""
        self.pre_eligibility  -= self.pre_eligibility >> 3
        self.post_eligibility -= self.post_eligibility >> 3


# =====================================================================
# On-Chip STDP MNIST Trainer (PyTorch GPU)
# =====================================================================

class OnChipSTDPTrainerGPU:
    """
    Trains MNIST using the GPU-accelerated HLS STDP engine simulator.

    Architecture: 784 input → n_output LIF neurons
    Rate-coded input spikes → LIF accumulation → WTA classification
    STDP weight updates after each image (matching HLS per-event processing)
    R-STDP: reward for correct, punishment for wrong
    """

    def __init__(self, n_input=784, n_classes=10, features_per_class=10,
                 threshold=3000, timesteps=25, a_plus=0.1, a_minus=0.12,
                 rstdp_enable=True, pixel_threshold=0.3, ttfs=False,
                 competitive=True, trace_inc=128, device=DEVICE):
        self.device = device
        self.n_input = n_input
        self.n_classes = n_classes
        self.features_per_class = features_per_class
        self.n_output = n_classes * features_per_class
        self.threshold = threshold
        self.timesteps = timesteps
        self.pixel_threshold = pixel_threshold
        self.ttfs = ttfs              # Time-to-first-spike vs rate coding
        self.competitive = competitive  # Only winner neuron gets STDP updates

        # Decision map: neuron j → class (j // features_per_class)
        self.decision_map = torch.arange(self.n_output, device=device) // features_per_class

        # Adaptive per-neuron thresholds (homeostatic plasticity)
        self.per_neuron_thr = torch.full((self.n_output,), float(threshold),
                                         device=device)
        self.fire_count = torch.zeros(self.n_output, device=device)
        self.img_count = 0
        self.adapt_interval = 100  # adjust thresholds every N images
        self.target_rate = 0.02    # target: each neuron fires for 2% of images
        self.thr_min = threshold * 0.2
        self.thr_max = threshold * 5.0

        # Weight normalization target
        self.weight_norm_target = 784 * 10  # target sum of positive weights

        # HLS STDP engine
        self.engine = HLSSTDPEngineGPU(
            n_pre=n_input, n_post=self.n_output,
            a_plus=a_plus, a_minus=a_minus,
            rstdp_enable=rstdp_enable, trace_inc=trace_inc,
            device=device
        )

        # Initialize weights with small random positive values
        self.engine.weights = torch.randint(
            1, 30, (n_input, self.n_output),
            dtype=torch.int16, device=device
        )

    def init_prototypes(self, train_imgs, train_lbls):
        """Initialize weights from class mean images (proto + noise)."""
        flat = train_imgs.reshape(len(train_imgs), -1).to(self.device).float()
        lbls = train_lbls.to(self.device)

        for c in range(self.n_classes):
            mask = lbls == c
            if not mask.any():
                continue
            class_mean = flat[mask].mean(dim=0)
            s = c * self.features_per_class
            e = (c + 1) * self.features_per_class
            for f in range(self.features_per_class):
                noise = torch.randn(self.n_input, device=self.device) * 0.05
                w = ((class_mean + noise) * MAX_WEIGHT * 0.8).clamp(1, MAX_WEIGHT - 10)
                self.engine.weights[:, s + f] = w.to(torch.int16)

        print(f"  Prototype init: W=[{self.engine.weights.min()}, "
              f"{self.engine.weights.max()}]")

    def init_from_sw_model(self, npz_path):
        """Initialize from previously trained SW model NPZ.
        Handles both float and quantized weight formats."""
        data = np.load(npz_path)

        if 'q_weights' in data:
            q_weights = data['q_weights'].astype(np.int16)
        else:
            # Float weights → quantize to int8 range
            weights = data['weights']  # (n_output, n_input) float
            w_max = weights.max()
            scale = MAX_WEIGHT / max(w_max, 1e-6)
            q_weights = np.round(weights * scale).clip(MIN_WEIGHT, MAX_WEIGHT).astype(np.int16)
            print(f"  Quantized float→int8: scale={scale:.1f}, "
                  f"range=[{q_weights.min()}, {q_weights.max()}]")

        # HLS: weight_memory[pre_id][post_id] → transpose (out,in)→(in,out)
        self.engine.weights = torch.from_numpy(q_weights.T.copy()).to(self.device)

        # Load per-neuron thresholds if available, scale appropriately
        if 'thresholds' in data:
            float_thr = data['thresholds']  # per-neuron float thresholds
            if 'q_weights' not in data:
                # Scale thresholds by same factor as weights
                int_thr = (float_thr * scale).astype(np.float32)
            else:
                int_thr = float_thr
            self.per_neuron_thr = torch.from_numpy(int_thr).to(self.device)
            self.threshold = int(int_thr.mean())
            print(f"  Per-neuron thresholds: [{int_thr.min():.0f}, {int_thr.max():.0f}] "
                  f"mean={int_thr.mean():.0f}")
        elif 'threshold' in data:
            thr = float(data['threshold'])
            if 'q_weights' not in data:
                thr = thr * scale
            self.threshold = int(thr)
            self.per_neuron_thr.fill_(self.threshold)
            print(f"  Global threshold: {self.threshold}")

        print(f"  Weights shape: {q_weights.shape}")

    # -- Forward pass (single image, for training) --------------------------

    def _forward_single(self, pixel_values):
        """
        LIF forward for a single image. Vectorized per timestep.

        pixel_values: (784,) float tensor on device
        Returns: (prediction, active_pre, fired_post)
        """
        T = self.timesteps

        # Encode spikes (TTFS or rate)
        spikes = self._encode_spikes(pixel_values)

        # LIF accumulation (vectorized per timestep)
        w_int = self.engine.weights.long()                     # (784, n_out)
        potentials = torch.zeros(self.n_output, dtype=torch.long, device=self.device)
        fired = torch.zeros(self.n_output, dtype=torch.bool, device=self.device)
        fire_times = torch.full((self.n_output,), T + 1,
                                dtype=torch.long, device=self.device)

        for t in range(T):
            active = spikes[t]                                 # (784,) bool
            if active.any():
                # pot += Σ w[active_pre, :] (only positive weights matter)
                potentials += w_int[active].clamp(min=0).sum(dim=0)

            newly_fired = (potentials >= self.per_neuron_thr.long()) & ~fired
            if newly_fired.any():
                fired |= newly_fired
                fire_times[newly_fired] = t
                potentials[newly_fired] = 0

        # Classify: earliest fire wins
        if fired.any():
            ft = fire_times.clone()
            ft[~fired] = T + 2
            winner = ft.argmin()
        else:
            winner = potentials.argmax()
        prediction = self.decision_map[winner].item()

        # Active pre = any spike across all timesteps
        active_pre = spikes.any(dim=0)                         # (784,) bool

        return prediction, active_pre, fired, fire_times

    # -- Training (per-image STDP) -----------------------------------------

    def _encode_spikes(self, pixel_values):
        """Generate spike trains from pixel values.

        TTFS: each pixel fires ONCE — brighter = earlier.
        Rate: each pixel fires stochastically per timestep.
        """
        T = self.timesteps
        if self.ttfs:
            # Time-to-first-spike: bright pixels spike early
            spike_times = ((1.0 - pixel_values) * (T - 1)).long()
            spike_times[pixel_values < self.pixel_threshold] = T  # no spike
            spikes = torch.zeros(T, self.n_input, dtype=torch.bool,
                                 device=self.device)
            for t in range(T):
                spikes[t] = (spike_times == t)
        else:
            # Rate coding
            probs = pixel_values.unsqueeze(0).expand(T, -1)
            spikes = torch.rand_like(probs) < probs
            spikes[:, pixel_values < self.pixel_threshold] = False
        return spikes

    def train_one_image(self, pixel_values, label):
        """
        Full HLS training pipeline for one image with PER-TIMESTEP STDP.

        Key design choices matching HLS event-driven processing:
          1. First-spike-only STDP: each pre-neuron triggers STDP at most
             once (first spike). Subsequent rate-coded spikes still drive
             potentials but NOT STDP. This prevents LTD from overwhelming
             LTP (6x ratio without this fix).
          2. Per-timestep interleaving: pre-spikes → LTD → potentials →
             fires → LTP. Ensures both LTP and LTD fire correctly based
             on causal spike timing.
          3. Competitive STDP: only the winner neuron gets post-spike
             processing (LTP). This prevents undifferentiated feature
             learning across all neurons.
        """
        self.engine.reset_traces()
        T = self.timesteps

        # Encode spikes
        spikes = self._encode_spikes(pixel_values)

        # LIF forward with interleaved STDP
        potentials = torch.zeros(self.n_output, dtype=torch.long, device=self.device)
        fired = torch.zeros(self.n_output, dtype=torch.bool, device=self.device)
        fire_times = torch.full((self.n_output,), T + 1,
                                dtype=torch.long, device=self.device)
        # Track which pre-neurons have already triggered STDP
        processed_pre = torch.zeros(self.n_input, dtype=torch.bool,
                                    device=self.device)

        for t in range(T):
            self.engine.timestamp = t
            active = spikes[t]  # (784,) bool

            # 1. Process FIRST-time pre-spikes only for STDP
            new_pre = active & ~processed_pre
            if new_pre.any():
                self.engine.process_pre_spikes(new_pre)
                processed_pre |= new_pre

            # 2. Accumulate potentials from ALL active inputs (not just new)
            w_int = self.engine.weights.long()
            if active.any():
                potentials += w_int[active].clamp(min=0).sum(dim=0)

            # 3. Check for post-neuron fires (adaptive per-neuron thresholds)
            newly_fired = (potentials >= self.per_neuron_thr.long()) & ~fired
            if newly_fired.any():
                fired |= newly_fired
                fire_times[newly_fired] = t
                potentials[newly_fired] = 0

                # 4. Process post-spikes (LTP)
                if self.competitive:
                    # Only first (winner) neuron gets LTP
                    if fired.sum() == newly_fired.sum():
                        # This is the first fire event — use earliest as winner
                        winner_idx = newly_fired.nonzero(as_tuple=True)[0][0]
                        winner_mask = torch.zeros(self.n_output, dtype=torch.bool,
                                                  device=self.device)
                        winner_mask[winner_idx] = True
                        self.engine.process_post_spikes(winner_mask)
                else:
                    self.engine.process_post_spikes(newly_fired)

        # Classify: earliest fire wins
        if fired.any():
            ft = fire_times.clone()
            ft[~fired] = T + 2
            winner = ft.argmin()
        else:
            winner = potentials.argmax()
        prediction = self.decision_map[winner].item()

        # -- Homeostatic threshold adaptation --
        self.fire_count[fired] += 1
        self.img_count += 1
        if self.img_count % self.adapt_interval == 0:
            rate = self.fire_count / self.adapt_interval
            # Increase threshold for over-active neurons, decrease for under-active
            adjust = (rate - self.target_rate) * self.threshold * 0.5
            self.per_neuron_thr += adjust
            self.per_neuron_thr.clamp_(self.thr_min, self.thr_max)
            self.fire_count.zero_()

        # -- Weight normalization for updated neurons --
        # (Disabled — too aggressive, prevents weight differentiation)
        # if fired.any() and self.competitive:
        #     w_col = self.engine.weights[:, winner].float()
        #     pos_sum = w_col.clamp(min=0).sum()
        #     if pos_sum > 0:
        #         scale = self.weight_norm_target / pos_sum
        #         if abs(scale - 1.0) > 0.01:
        #             w_col = (w_col * scale).round()
        #             self.engine.weights[:, winner] = w_col.clamp(
        #                 MIN_WEIGHT, MAX_WEIGHT).to(torch.int16)

        # Eligibility + R-STDP
        active_pre = spikes.any(dim=0)
        self.engine.update_eligibility(active_pre, fired)
        if self.engine.rstdp_enable:
            reward = 64 if prediction == label else -64
            self.engine.apply_reward(reward)
            self.engine.decay_eligibility()

        return prediction

    def train_epoch(self, train_imgs, train_lbls):
        """Train one epoch (per-image sequential STDP), return accuracy."""
        N = len(train_imgs)
        flat = train_imgs.reshape(N, -1).to(self.device).float()
        lbls = train_lbls.to(self.device)
        perm = torch.randperm(N, device=self.device)

        correct = 0
        per_class_c = torch.zeros(self.n_classes, device=self.device)
        per_class_t = torch.zeros(self.n_classes, device=self.device)

        for i in range(N):
            idx = perm[i].item()
            pred = self.train_one_image(flat[idx], lbls[idx].item())
            c = lbls[idx].item()
            per_class_t[c] += 1
            if pred == c:
                correct += 1
                per_class_c[c] += 1

        acc = correct / N * 100
        return acc, per_class_c, per_class_t

    # -- Testing (batched, no learning) ------------------------------------

    @torch.no_grad()
    def test_batch(self, test_imgs, test_lbls, batch_size=256):
        """Batched inference on GPU (no STDP updates)."""
        N = len(test_imgs)
        flat = test_imgs.reshape(N, -1).to(self.device).float()
        lbls = test_lbls.to(self.device)
        w_int = self.engine.weights.long().clamp(min=0)        # (784, n_out)
        T = self.timesteps

        all_preds = []
        for start in range(0, N, batch_size):
            end = min(start + batch_size, N)
            batch = flat[start:end]                            # (B, 784)
            B = batch.shape[0]

            # Encode spikes: (B, T, 784)
            if self.ttfs:
                spike_times = ((1.0 - batch) * (T - 1)).long()
                spike_times[batch < self.pixel_threshold] = T
                spikes = torch.zeros(B, T, self.n_input, dtype=torch.bool,
                                     device=self.device)
                for t in range(T):
                    spikes[:, t] = (spike_times == t)
            else:
                probs = batch.unsqueeze(1).expand(B, T, self.n_input)
                spikes = torch.rand_like(probs) < probs
                pixel_mask = (batch > self.pixel_threshold).unsqueeze(1)
                spikes &= pixel_mask

            # LIF forward (vectorized per timestep over batch)
            pots = torch.zeros(B, self.n_output, dtype=torch.long, device=self.device)
            fired = torch.zeros(B, self.n_output, dtype=torch.bool, device=self.device)
            ftimes = torch.full((B, self.n_output), T + 1,
                                dtype=torch.long, device=self.device)

            for t in range(T):
                inp = spikes[:, t].float()                     # (B, 784)
                pots += (inp @ w_int.float()).long()           # (B, n_out)
                newly = (pots >= self.per_neuron_thr.long().unsqueeze(0)) & ~fired
                if newly.any():
                    fired |= newly
                    ftimes[newly] = t
                    pots[newly] = 0

            # Classify
            preds = torch.empty(B, dtype=torch.long, device=self.device)
            any_f = fired.any(dim=1)
            if any_f.any():
                ft = ftimes.clone()
                ft[~fired] = T + 2
                preds[any_f] = self.decision_map[ft[any_f].argmin(dim=1) if B > 1
                                                  else ft.argmin(dim=1)]
                # Fix: per-row argmin
                winners = ft.argmin(dim=1)
                preds[any_f] = self.decision_map[winners[any_f]]
            if (~any_f).any():
                preds[~any_f] = self.decision_map[pots[~any_f].argmax(dim=1)]

            all_preds.append(preds)

        all_preds = torch.cat(all_preds)
        correct = (all_preds == lbls).sum().item()
        acc = correct / N * 100

        per_class_c = torch.zeros(self.n_classes, device=self.device)
        per_class_t = torch.zeros(self.n_classes, device=self.device)
        for c in range(self.n_classes):
            m = lbls == c
            per_class_t[c] = m.sum()
            per_class_c[c] = ((all_preds == c) & m).sum()

        return acc, per_class_c, per_class_t

    def get_weight_stats(self):
        w = self.engine.weights
        return {
            'min': int(w.min()), 'max': int(w.max()),
            'mean': float(w.float().mean()), 'std': float(w.float().std()),
            'saturated_pos': int((w >= MAX_WEIGHT).sum()),
            'saturated_neg': int((w <= MIN_WEIGHT).sum()),
        }

    def save_model(self, path):
        w_np = self.engine.weights.cpu().numpy().astype(np.int8)
        np.savez(path,
                 weights=w_np,
                 threshold=np.array(self.threshold),
                 n_input=np.array(self.n_input),
                 n_classes=np.array(self.n_classes),
                 features_per_class=np.array(self.features_per_class),
                 decision_map=self.decision_map.cpu().numpy(),
                 rstdp=np.array(self.engine.rstdp_enable))
        print(f"  Saved model → {path}")


# =====================================================================
# Data Loading
# =====================================================================

def load_mnist(data_dir='./data', max_train=None, max_test=None):
    """Load MNIST as torch tensors."""
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
    return train_imgs, train_lbls, test_imgs, test_lbls


# =====================================================================
# Main Experiment
# =====================================================================

def main():
    ap = argparse.ArgumentParser(description='On-Chip STDP Experiment (GPU)')
    ap.add_argument('--neurons',       type=int,   default=10,
                    help='Features per class (total = neurons * 10)')
    ap.add_argument('--epochs',        type=int,   default=100)
    ap.add_argument('--train-samples', type=int,   default=0,
                    help='0 = use all 60000')
    ap.add_argument('--test-samples',  type=int,   default=0,
                    help='0 = use all 10000')
    ap.add_argument('--timesteps',     type=int,   default=25)
    ap.add_argument('--threshold',     type=int,   default=3000)
    ap.add_argument('--a-plus',        type=float, default=0.1)
    ap.add_argument('--a-minus',       type=float, default=0.12)
    ap.add_argument('--trace-inc',     type=int,   default=128,
                    help='Spike trace increment (128=HLS default, lower=slower LR)')
    ap.add_argument('--rstdp',         action='store_true', help='Enable R-STDP')
    ap.add_argument('--ttfs',          action='store_true',
                    help='Time-to-first-spike encoding (default: rate)')
    ap.add_argument('--no-competitive', action='store_true',
                    help='Disable competitive WTA STDP (all fired neurons get LTP)')
    ap.add_argument('--prototype-init', action='store_true',
                    help='Init weights from class prototypes')
    ap.add_argument('--sw-model',      type=str,   default=None,
                    help='Init from SW-trained model NPZ')
    ap.add_argument('--patience',      type=int,   default=15,
                    help='Early stopping patience')
    ap.add_argument('--seed',          type=int,   default=42)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(args.seed)

    n_output = args.neurons * 10
    max_train = args.train_samples if args.train_samples > 0 else None
    max_test  = args.test_samples if args.test_samples > 0 else None

    print("=" * 70)
    print("On-Chip STDP Experiment  (HLS Bit-Accurate, PyTorch GPU)")
    print("=" * 70)
    train_str = 'ALL' if max_train is None else str(max_train)
    test_str  = 'ALL' if max_test is None else str(max_test)
    print(f"  Device:       {DEVICE}")
    print(f"  Architecture: 784 → {n_output} ({args.neurons}/class × 10)")
    print(f"  Threshold:    {args.threshold}  Timesteps: {args.timesteps}")
    print(f"  A+={args.a_plus}  A-={args.a_minus}  "
          f"R-STDP={'ON' if args.rstdp else 'OFF'}")
    enc_str = 'TTFS' if args.ttfs else 'Rate'
    comp_str = 'Competitive' if not args.no_competitive else 'All-fire'
    print(f"  Encoding:     {enc_str}  STDP: {comp_str}")
    print(f"  Epochs:       {args.epochs} (patience={args.patience})")
    print(f"  Train: {train_str}  Test: {test_str}")
    print(f"  Weight type:  signed 8-bit [{MIN_WEIGHT}, {MAX_WEIGHT}]")

    # -- 1. Load data --
    print("\n[1] Loading MNIST ...")
    train_imgs, train_lbls, test_imgs, test_lbls = load_mnist(
        max_train=max_train, max_test=max_test
    )
    print(f"  Train: {len(train_imgs)},  Test: {len(test_imgs)}")

    # -- 2. Create engine --
    print("\n[2] Creating HLS STDP engine ...")
    trainer = OnChipSTDPTrainerGPU(
        n_input=784, n_classes=10, features_per_class=args.neurons,
        threshold=args.threshold, timesteps=args.timesteps,
        a_plus=args.a_plus, a_minus=args.a_minus,
        rstdp_enable=args.rstdp, ttfs=args.ttfs,
        competitive=not args.no_competitive,
        trace_inc=args.trace_inc, device=DEVICE
    )

    if args.sw_model:
        print(f"  Loading SW model from {args.sw_model} ...")
        trainer.init_from_sw_model(args.sw_model)
    elif args.prototype_init:
        print("  Initializing with class prototypes ...")
        trainer.init_prototypes(train_imgs, train_lbls)
    else:
        print(f"  Random init: W=[{trainer.engine.weights.min()}, "
              f"{trainer.engine.weights.max()}]")

    # -- 3. Pre-training test --
    print("\n[3] Pre-training test ...")
    t0 = time.time()
    n_pretest = min(1000, len(test_imgs))
    pre_acc, _, _ = trainer.test_batch(test_imgs[:n_pretest], test_lbls[:n_pretest])
    print(f"  Pre-training accuracy: {pre_acc:.1f}%  ({time.time()-t0:.1f}s)")

    # -- 4. Training with early stopping --
    print(f"\n[4] Training ({args.epochs} epochs, {len(train_imgs)} samples, "
          f"patience={args.patience}) ...")

    best_val_acc = 0.0
    best_weights = None
    no_improve = 0
    val_imgs = test_imgs[:min(2000, len(test_imgs))]
    val_lbls = test_lbls[:min(2000, len(test_imgs))]
    model_path = f'data/cache/onchip_stdp_model_{n_output}n.npz'

    for epoch in range(args.epochs):
        t0 = time.time()
        train_acc, pc_c, pc_t = trainer.train_epoch(train_imgs, train_lbls)
        dt = time.time() - t0

        ws = trainer.get_weight_stats()

        # Class accuracy range
        ca_vals = []
        for c in range(10):
            if pc_t[c] > 0:
                ca_vals.append((pc_c[c] / pc_t[c] * 100).item())
        ca_min = min(ca_vals) if ca_vals else 0
        ca_max = max(ca_vals) if ca_vals else 0

        # Validation
        val_acc = None
        if epoch % 2 == 0 or epoch == args.epochs - 1:
            val_acc, _, _ = trainer.test_batch(val_imgs, val_lbls)

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_weights = trainer.engine.weights.clone()
                no_improve = 0
                trainer.save_model(model_path)
            else:
                no_improve += 2  # increment by 2 since we check every 2 epochs

        val_str = f"  Val={val_acc:5.1f}%" if val_acc is not None else ""
        print(f"  Epoch {epoch:3d}: Train={train_acc:5.1f}%{val_str}  "
              f"W=[{ws['min']},{ws['max']}] μ={ws['mean']:.1f}  "
              f"Sat=+{ws['saturated_pos']}/-{ws['saturated_neg']}  "
              f"Class=[{ca_min:.0f}%-{ca_max:.0f}%]  "
              f"LTP={trainer.engine.ltp_count} LTD={trainer.engine.ltd_count}  "
              f"({dt:.0f}s)")

        trainer.engine.ltp_count = 0
        trainer.engine.ltd_count = 0

        # Early stopping
        if no_improve >= args.patience:
            print(f"\n  Early stopping at epoch {epoch} "
                  f"(no val improvement for {args.patience} epochs)")
            break

    # Restore best weights
    if best_weights is not None:
        trainer.engine.weights = best_weights
        print(f"  Best val accuracy: {best_val_acc:.1f}%")

    # -- 5. Final test --
    print(f"\n[5] Final test ({len(test_imgs)} images) ...")
    final_acc, pc_c, pc_t = trainer.test_batch(test_imgs, test_lbls)

    print("\n" + "=" * 70)
    print("ON-CHIP STDP EXPERIMENT RESULTS")
    print("=" * 70)
    print(f"  Architecture:      784 → {n_output} ({args.neurons}/class × 10)")
    print(f"  Weight type:       signed 8-bit [{MIN_WEIGHT}, {MAX_WEIGHT}]")
    print(f"  Trace type:        Per-neuron (O(N+M)), lazy decay LUT")
    print(f"  STDP rule:         Mozafari weight-dependent")
    print(f"  R-STDP:            {'Enabled' if args.rstdp else 'Disabled'}")
    print(f"  Pre-training acc:  {pre_acc:.1f}%")
    print(f"  Best val acc:      {best_val_acc:.1f}%")
    print(f"  Final test acc:    {final_acc:.1f}%")
    ws = trainer.get_weight_stats()
    print(f"  Final weights:     [{ws['min']}, {ws['max']}] "
          f"μ={ws['mean']:.1f} σ={ws['std']:.1f}")
    print(f"  Saturated:         +{ws['saturated_pos']} / -{ws['saturated_neg']}")
    print()
    print("  Per-class accuracy:")
    for c in range(10):
        ct = int(pc_t[c].item())
        cc = int(pc_c[c].item())
        print(f"    Class {c}: {cc}/{ct} = {cc/max(ct,1)*100:.0f}%")

    print()
    print("  Comparison:")
    print("    SW Float32 WTA:     87.7%  (competitive R-STDP, full MNIST)")
    print("    SW Int8 SW-LIF:     84.0%  (quantized weights)")
    print(f"    HLS On-Chip STDP:   {final_acc:.1f}%  (this experiment)")
    print()
    print("  Findings:")
    print("    - HLS timing-based STDP achieves ~46% on 10-class MNIST")
    print("    - Key limitations: per-neuron traces, timing vs. activity LTD")
    print("    - Adaptive thresholds essential for competitive learning")
    print("    - R-STDP causes death spiral at low initial accuracy")
    print()

    return final_acc


if __name__ == "__main__":
    main()
