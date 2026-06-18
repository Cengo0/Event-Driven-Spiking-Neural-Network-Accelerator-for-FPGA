"""SpikePress Training API for PyTorch-like SNN training.

This module provides a PyTorch-compatible interface for training Spiking Neural
Networks with the goal of deploying to SpikeMold hardware.

SNN direct training (surrogate gradient) best practices implemented:
  - Rate-coded (bernoulli) spike input encoding from pixel intensity
  - Binary spikes (0/1) with surrogate gradient (fast_sigmoid) for all layers
  - Cross-entropy loss on output spike counts (spike counts used as logits)
  - IF/LIF dynamics (default decay=1.0 to align with SpikeMold IF event trace/HW)
  - T=16-32 timesteps typical for MNIST

Example:
    >>> from spikepress.training import SpikePressTrainer, LIFNeuronConfig
    >>> from spikepress.network import SpikePressNetwork, SpikePressNeuronPopulation, SpikePressProjection
    >>>
    >>> # Create network topology
    >>> network = SpikePressNetwork()
    >>> input_pop = network.add_population(SpikePressNeuronPopulation(784, "input"))
    >>> hidden_pop = network.add_population(SpikePressNeuronPopulation(2048, "hidden"))
    >>> output_pop = network.add_population(SpikePressNeuronPopulation(10, "output"))
    >>> network.add_projection(SpikePressProjection(input_pop, hidden_pop))
    >>> network.add_projection(SpikePressProjection(hidden_pop, output_pop))
    >>>
    >>> # Configure (use from_hardware() for HW-aligned IF params)
    >>> lif_config = LIFNeuronConfig.from_hardware()
    >>>
    >>> # Create trainer (num_steps ~16-32)
    >>> trainer = SpikePressTrainer(model, lif_config, num_steps=16)
    >>>
    >>> # Train with PyTorch-style API (CE on spike counts)
    >>> for epoch in range(10):
    ...     trainer.train_epoch(train_loader, lr=0.005)
    ...     trainer.evaluate(val_loader)

ANN-to-SNN conversion path also supported via separate utilities (see
pytorch_to_snn style weight scaling + export).

Weight quantization for SpikeMold:
    - Weights are clipped to int8 range [-8, 7] for 4-bit representation (default)
    - Matches HLS PACKED weights + WEIGHT_SCALE=128 in hardware semantics
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

try:
    import torch
    import torch.nn.functional as F
    from torch.utils.checkpoint import checkpoint
    from torch.utils.data import DataLoader
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
    DataLoader = None  # type: ignore
    F = None  # type: ignore
    checkpoint = None  # type: ignore


from .network import (
    CompiledSpikePressTopology,
    SpikePressNetwork,
    SpikePressNeuronPopulation,
    SpikePressProjection,
)
from .spikemold_artifact import SpikeMoldArtifact, build_spikemold_artifact


# =============================================================================
# LIF Neuron Configuration
# =============================================================================

@dataclass(frozen=True)
class LIFNeuronConfig:
    """Configuration for LIF/IF neurons (SpikeMold training + HW alignment).

    Research-backed defaults for direct surrogate training (snntorch, SpikingJelly, papers):
    - decay/beta ~0.9 for leaky (helps MNIST/CIFAR acc), or 1.0 for pure IF (better HW trace match).
    - reset_mechanism: 'zero' (hard reset, matches our trace gen) or 'subtract' (common for better training).
    - Use from_hardware() for SpikeMold integer IF fidelity (decay=1.0, reset=0, refractory=0).
    Threshold ~1.0, rate or direct-current encoding, T=16-50 for MNIST.
    """

    threshold: float = 1.0
    decay: float = 0.9          # 0.9 leaky common for acc; 1.0 = IF for HW alignment
    reset: float = 0.0
    refractory_period: int = 0
    scaling_factor: int = 65536
    reset_mechanism: str = "zero"  # "zero" (HW trace match) or "subtract" (training-friendly)

    def to_int32(self, value: float) -> int:
        return int(value * self.scaling_factor)

    @classmethod
    def from_hardware(cls) -> "LIFNeuronConfig":
        # Hardware-aligned defaults for SpikeMold IF (non-leaky) backend:
        # decay=1.0 for pure IF, refractory often 0 in event trace path.
        return cls(
            threshold=1.0,
            decay=1.0,
            reset=0.0,
            refractory_period=0,
            scaling_factor=65536,
        )


class SpikeFunction(torch.autograd.Function):
    """Binary spike forward with surrogate gradient backward for BPTT in SNNs.

    Forward: Heaviside step (1 if v >= threshold else 0).
    Backward: surrogate derivative (fast_sigmoid or atan) to allow gradient flow.
    This matches best practices from snnTorch / SpikingJelly surrogate training.
    """

    @staticmethod
    def forward(ctx, membrane: torch.Tensor, threshold: torch.Tensor, surrogate: str = "fast_sigmoid", slope: float = 25.0):
        # threshold can be scalar or per-neuron tensor
        ctx.save_for_backward(membrane, threshold if isinstance(threshold, torch.Tensor) else torch.tensor(threshold))
        ctx.surrogate = surrogate
        ctx.slope = float(slope)
        # Binary spike
        return (membrane >= threshold).float()

    @staticmethod
    def backward(ctx, grad_output):
        membrane, threshold = ctx.saved_tensors
        v_minus_th = membrane - threshold
        surrogate = ctx.surrogate
        slope = ctx.slope

        if surrogate == "atan":
            # Arctan surrogate derivative (common in literature)
            # d/dx (0.5 + (1/pi) arctan( pi * beta * x ))  ~  beta / (1 + (pi * beta * x)^2)
            pi_beta = 3.1415926535 * slope
            grad = grad_output * (slope / (1.0 + (pi_beta * v_minus_th) ** 2))
        else:
            # fast_sigmoid surrogate:  slope / (1 + slope * |v-th| )**2   (or equiv)
            # Popular, robust for SNN direct training on MNIST
            grad = grad_output * (slope / (1.0 + slope * torch.abs(v_minus_th)) ** 2)

        return grad, None, None, None


    # =============================================================================
    # Spiking Neural Network Model (PyTorch Module)
    # =============================================================================

class SpikingModel(torch.nn.Module):
    """Spiking Neural Network with LIF dynamics for training."""

    def __init__(
        self,
        layer_sizes: Sequence[int] = None,
        lif_config: LIFNeuronConfig = None,
        conv_specs: List[Dict[str, Any]] = None,
        fc_sizes: Sequence[int] = None,
        weight_init_scale: float = 0.1,
        device: str = "cpu",
        surrogate: str = "fast_sigmoid",
        surrogate_slope: float = 25.0,
        input_encoding: str = "direct",
        output_mode: str = "spike_count",
        timestep_vectorized: bool = False,
        lateral_inh_strength: float = 0.0,
    ):
        super().__init__()

        if lif_config is None:
            lif_config = LIFNeuronConfig.from_hardware()

        self.lif_config = lif_config
        self.surrogate = surrogate
        self.surrogate_slope = float(surrogate_slope)
        self.input_encoding = input_encoding
        self.output_mode = output_mode
        self.device = torch.device(device)
        self.weight_init_scale = weight_init_scale
        self.timestep_vectorized = bool(timestep_vectorized)
        self.lateral_inh_strength = float(lateral_inh_strength)

        self.convs = None
        self.fc = None
        self._is_hybrid = False

        if conv_specs is not None:
            # Hybrid / Conv mode
            self._is_hybrid = True
            self.convs = torch.nn.ModuleList()
            for spec in conv_specs:
                conv = SpikingEventConv(
                    in_channels=spec['in_c'],
                    out_channels=spec['out_c'],
                    kernel_size=spec.get('k', 3),
                    stride=spec.get('s', 1),
                    padding=spec.get('p', 0),
                    lif_config=lif_config,
                    weight_init_scale=weight_init_scale,
                    device=device,
                    surrogate=surrogate,
                    surrogate_slope=surrogate_slope,
                    timestep_vectorized=self.timestep_vectorized,
                )
                self.convs.append(conv)

            if fc_sizes is not None:
                self.fc = SpikingModel(  # recursive for pure FC part
                    layer_sizes=fc_sizes,
                    lif_config=lif_config,
                    weight_init_scale=weight_init_scale,
                    device=device,
                    surrogate=surrogate,
                    surrogate_slope=surrogate_slope,
                    input_encoding="direct",
                    output_mode="membrane",  # better class logits for hybrid heads (final Vmem of readout); spikes still returned for reg
                    timestep_vectorized=self.timestep_vectorized,
                    lateral_inh_strength=0.0,  # reserved (lateral implemented only via static negative recurrence weights for HW)
                )
            else:
                self.fc = None
            # For compatibility with old code checking hasattr
            # layer_sizes etc not set for pure hybrid, but script branches
        else:
            # Pure FC mode (original)
            if layer_sizes is None or len(layer_sizes) < 2:
                raise ValueError("Need layer_sizes with at least input and output for FC mode, or conv_specs+fc_sizes")

            self.layer_sizes = tuple(layer_sizes)
            self.num_layers = len(layer_sizes) - 1

            self._weights: torch.nn.ParameterList = torch.nn.ParameterList()
            self._thresholds: torch.nn.ParameterList = torch.nn.ParameterList()

            for i in range(self.num_layers):
                pre_size, post_size = layer_sizes[i], layer_sizes[i + 1]
                scale = weight_init_scale / np.sqrt(pre_size)

                w = torch.randn(pre_size, post_size, device=self.device) * scale
                self._weights.append(torch.nn.Parameter(w))

                t = torch.full((post_size,), lif_config.threshold, device=self.device)
                self._thresholds.append(torch.nn.Parameter(t))

    def forward(
        self,
        input_data: torch.Tensor,
        num_steps: int,
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """Unified forward for pure FC or hybrid EventConv+FC.

        For hybrid (when conv_specs was used): input_data can be 4D images [B,C,H,W] or [B,T,C,H,W].
        For pure FC:  [B, features] or [B, T, features].

        See class doc and research-backed options in __init__.
        """
        if getattr(self, '_is_hybrid', False):
            return self._forward_hybrid(input_data, num_steps)

        input_spike_train = input_data
        batch_size, seq_len, _ = input_spike_train.shape
        device = input_spike_train.device
        decay = self.lif_config.decay
        reset_val = self.lif_config.reset
        refrac_period = int(self.lif_config.refractory_period)
        reset_subtract = (self.lif_config.reset_mechanism == "subtract")

        membrane: List[torch.Tensor] = [
            torch.zeros(batch_size, self.layer_sizes[i + 1], device=device)
            for i in range(self.num_layers)
        ]
        refractory: List[torch.Tensor] = [
            torch.zeros(batch_size, self.layer_sizes[i + 1], device=device, dtype=torch.long)
            for i in range(self.num_layers)
        ]

        output_spikes = torch.zeros(batch_size, seq_len, self.layer_sizes[-1], device=device)
        final_membrane = torch.zeros(batch_size, self.layer_sizes[-1], device=device)

        if self.timestep_vectorized:
            # Vectorized (high-VRAM) path: one large GEMM per layer over the full (B*T) then a cheap
            # inner per-timestep loop *only* for LIF state (membrane/spike/reset/refrac).
            # This is the "루프 빼서 최적화" version (removes matmuls from the python timestep loop).
            # Good for GPU throughput / compile / CUDAGraphs but materializes large temporal buffers
            # (e.g. (B*T, 65536) for max hidden experiments).
            layer_input = input_spike_train.float()  # (B, T, dim) for layer 0

            for layer_idx in range(self.num_layers):
                flat_in = layer_input.reshape(batch_size * seq_len, -1)
                weights = self._weights[layer_idx]

                if self.layer_sizes[layer_idx + 1] > 10000 and checkpoint is not None:
                    all_projected = checkpoint(
                        lambda x, w: (x @ w).reshape(batch_size, seq_len, -1),
                        flat_in,
                        weights,
                        use_reentrant=False,
                    )
                else:
                    all_projected = (flat_in @ weights).reshape(batch_size, seq_len, -1)

                spike_threshold = self._thresholds[layer_idx]
                this_layer_spikes = torch.zeros(batch_size, seq_len, self.layer_sizes[layer_idx + 1], device=device)

                # Compile the per-timestep LIF update to reduce Python overhead in the 25-iteration loop
                # (still recurrent so we keep the time loop, but the body is fused/reduced-overhead).
                # For --vectorize-timesteps training with GradScaler we disable this inner compile
                # because it triggers the exact CUDAGraph dealloc mismatch error during backward
                # (the main perf win is already the hoisted (B*T) matmul outside the T loop).
                def _lif_update(m, proj, thresh, dec, rv, rsub, ref, rp, sur, sl):
                    m = dec * m + proj
                    sp = SpikeFunction.apply(m, thresh, sur, sl)
                    if rp > 0:
                        rm = (ref > 0).float()
                        sp = sp * (1.0 - rm)
                    if rsub:
                        m = m - sp.detach() * thresh.detach()
                    else:
                        mb = m
                        m = mb * (1.0 - sp.detach()) + rv * sp.detach()
                    if rp > 0:
                        sn = (sp > 0).long()
                        ref[sn > 0] = rp
                        ref = torch.clamp(ref - 1, min=0)
                    return m, sp, ref

                # Only compile the small LIF update if not in vectorized training (avoids cudagraph_trees dealloc TODO).
                # The script sets this via the global or we check the model flag.
                if not getattr(self, '_disable_inner_lif_compile_for_vectorize', False):
                    _lif_update = torch.compile(_lif_update, mode="reduce-overhead")

                for t in range(seq_len):
                    projected = all_projected[:, t]
                    membrane[layer_idx], spiked, refractory[layer_idx] = _lif_update(
                        membrane[layer_idx], projected, spike_threshold,
                        decay, reset_val, reset_subtract, refractory[layer_idx], refrac_period,
                        self.surrogate, self.surrogate_slope
                    )

                    this_layer_spikes[:, t] = spiked

                    if layer_idx == self.num_layers - 1:
                        output_spikes[:, t, :] = spiked
                        if self.output_mode == "membrane":
                            final_membrane = membrane[layer_idx].clone()

                layer_input = this_layer_spikes
                if layer_idx == self.num_layers - 2 and self.num_layers > 1:
                    hidden_spikes = this_layer_spikes  # spikes from the large hidden population (e.g. 65536) for better reg
        else:
            # Classic looped (memory-efficient, default) path: full serial per-timestep loop.
            # At each t we do small per-layer matmuls + LIF. Peak memory is O(B * largest_layer)
            # instead of O(B * T * largest_layer). Slower for large T or wide layers but uses much less VRAM.
            # This is the "루프로 해서 하는거" version.
            hidden_spike_volume = torch.tensor(0.0, device=device)
            for t in range(seq_len):
                x = input_spike_train[:, t].float()  # (B, feat) for this timestep

                for layer_idx in range(self.num_layers):
                    weights = self._weights[layer_idx]
                    projected = x @ weights

                    membrane[layer_idx] = decay * membrane[layer_idx] + projected

                    spiked = SpikeFunction.apply(
                        membrane[layer_idx],
                        self._thresholds[layer_idx],
                        self.surrogate,
                        self.surrogate_slope,
                    )

                    if refrac_period > 0:
                        ref_mask = (refractory[layer_idx] > 0).float()
                        spiked = spiked * (1.0 - ref_mask)

                    if layer_idx == self.num_layers - 1:
                        output_spikes[:, t, :] = spiked
                        if self.output_mode == "membrane":
                            final_membrane = membrane[layer_idx].clone()

                    if reset_subtract:
                        membrane[layer_idx] = membrane[layer_idx] - spiked.detach() * self._thresholds[layer_idx].detach()
                    else:
                        mem_before = membrane[layer_idx]
                        membrane[layer_idx] = mem_before * (1.0 - spiked.detach()) + reset_val * spiked.detach()

                    if refrac_period > 0:
                        spiked_now = (spiked > 0).long()
                        refractory[layer_idx][spiked_now > 0] = refrac_period
                        refractory[layer_idx] = torch.clamp(refractory[layer_idx] - 1, min=0)

                    # feed next layer (same t)
                    x = spiked

                    if layer_idx == self.num_layers - 2 and self.num_layers > 1:
                        hidden_spike_volume = hidden_spike_volume + spiked.sum()

        states = {
            "membrane": [m for m in membrane],
            "refractory": [r for r in refractory],
            "output_spike_counts": output_spikes.sum(dim=1),
            "final_membrane": final_membrane if self.output_mode == "membrane" else None,
        }
        # Expose hidden layer spike volume (the large population like 65536) so that
        # spike_reg in the trainer can penalize it (critical for the max 65k hybrid to avoid explosion).
        if 'hidden_spikes' in locals():
            states["hidden_spike_volume"] = hidden_spikes.sum()
        elif 'hidden_spike_volume' in locals():
            states["hidden_spike_volume"] = hidden_spike_volume

        if self.output_mode == "membrane":
            return output_spikes, states
        return output_spikes, states

    def _forward_hybrid(self, input_data: torch.Tensor, num_steps: int):
        """Hybrid EventConv + (optional) FC forward."""
        input_data = input_data.to(self.device)
        if input_data.dim() == 4:
            if getattr(self, 'input_encoding', 'direct') == "rate":
                b, c, h, w = input_data.shape
                rates = torch.clamp(input_data * 2 + 0.5, 0, 1).unsqueeze(1).expand(-1, num_steps, -1, -1, -1)
                randm = torch.rand(b, num_steps, c, h, w, device=input_data.device)
                x = (randm < rates).float()
            else:
                x = input_data.unsqueeze(1).expand(-1, num_steps, -1, -1, -1)
        else:
            x = input_data

        for conv in self.convs or []:
            x, _ = conv(x, num_steps)

        if not hasattr(self, 'fc') or self.fc is None:
            return x, {"conv_spikes": x.detach().cpu()}

        b, t, co, ho, wo = x.shape
        flat = x.reshape(b, t, co * ho * wo).contiguous()

        # Apply activation checkpointing (1번 memory optimization) to the FC sub-model call
        # only in vectorized-timesteps mode (where full (B*T, hidden) activations are materialized).
        # In default looped mode the inner per-t matmuls are already small-memory; wrapping the
        # whole fc here is unnecessary and can interact badly with torch.compile + autocast.
        fc_is_vectorized = getattr(self.fc, 'timestep_vectorized', False) if hasattr(self, 'fc') and self.fc is not None else False
        if (fc_is_vectorized and
            any(getattr(self.fc, 'layer_sizes', []) and s > 10000 for s in self.fc.layer_sizes) and
            checkpoint is not None):
            out_spikes, fc_states = checkpoint(
                self.fc, flat, num_steps, use_reentrant=False
            )
        else:
            out_spikes, fc_states = self.fc(flat, num_steps)

        states = {"conv_spikes": x, "fc_states": fc_states}
        return out_spikes, states

    def get_weights(self):
        if getattr(self, '_is_hybrid', False):
            conv_ws = [c.weight.detach().cpu().numpy() for c in (self.convs or [])]
            fc_ws = self.fc.get_weights() if self.fc is not None and hasattr(self.fc, 'get_weights') else []
            return {'conv_weights': conv_ws, 'fc_weights': fc_ws}
        return [w.detach().cpu().numpy() for w in self._weights]

    def set_weights(self, weights):
        if getattr(self, '_is_hybrid', False):
            if isinstance(weights, dict):
                for i, w in enumerate(weights.get('conv_weights', [])):
                    if self.convs and i < len(self.convs):
                        self.convs[i].weight.data.copy_(torch.from_numpy(w).to(self.device))
                if 'fc_weights' in weights and self.fc is not None and hasattr(self.fc, 'set_weights'):
                    self.fc.set_weights(weights['fc_weights'])
            return
        # pure FC
        if len(weights) != len(self._weights):
            raise ValueError(f"Expected {len(self._weights)} weight matrices")
        with torch.no_grad():
            for i, w in enumerate(weights):
                if w.shape != self._weights[i].shape:
                    raise ValueError(
                        f"Weight {i} shape mismatch: expected {self._weights[i].shape}, got {w.shape}"
                    )
                self._weights[i].copy_(torch.from_numpy(w))

    def to_artifact(self, *args, **kwargs):
        if getattr(self, '_is_hybrid', False) and self.fc is not None and hasattr(self.fc, 'to_artifact'):
            return self.fc.to_artifact(*args, **kwargs)
        if hasattr(self, '_weights'):
            # delegate to original impl if present, or error
            pass
        raise NotImplementedError("Use get_weights for hybrid (conv kernels + fc) or implement for pure FC")


class SpikingEventConv(torch.nn.Module):
    """EventConv-like layer with surrogate gradient LIF for direct SNN training.

    Supports shared-kernel convolution + per-position LIF (matches SpikeMold EventConv AGU semantics for training).
    Use for spatial feature extraction on MNIST/CIFAR before FC readout.
    For co-design, after training quantize kernel and use with generate_eventconv_trace or hardware EventConv.
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int = 3,
        stride: int = 1,
        padding: int = 0,
        lif_config: Optional[LIFNeuronConfig] = None,
        weight_init_scale: float = 0.1,
        device: str = "cpu",
        surrogate: str = "fast_sigmoid",
        surrogate_slope: float = 25.0,
        timestep_vectorized: bool = False,
    ):
        super().__init__()
        if lif_config is None:
            lif_config = LIFNeuronConfig.from_hardware()
        self.lif_config = lif_config
        self.stride = stride
        self.padding = padding
        self.kernel_size = kernel_size
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.surrogate = surrogate
        self.surrogate_slope = surrogate_slope
        self.device = torch.device(device)
        self.timestep_vectorized = bool(timestep_vectorized)

        # Conv kernel (shared, [cout, cin, k, k])
        scale = weight_init_scale / (in_channels * kernel_size * kernel_size) ** 0.5
        w = torch.randn(out_channels, in_channels, kernel_size, kernel_size, device=self.device) * scale
        self.weight = torch.nn.Parameter(w)

        # For simplicity, per-output-channel threshold (can be per-position if needed)
        # In full, output positions = out_h * out_w , thresh per 'neuron'
        # Per-channel threshold; can be broadcast per position if needed.
        t = torch.full((out_channels,), lif_config.threshold, device=self.device)
        self.threshold = torch.nn.Parameter(t)

    def forward(
        self,
        input_spike_or_current: torch.Tensor,  # [B, T, C, H, W] or [B, C, H, W] for direct current (will repeat)
        num_steps: int,
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        input_spike_or_current = input_spike_or_current.to(self.device)
        batch_size = input_spike_or_current.shape[0]
        device = input_spike_or_current.device
        if input_spike_or_current.dim() == 4:
            # direct current: repeat over time
            current = input_spike_or_current.unsqueeze(1).expand(-1, num_steps, -1, -1, -1)
        else:
            current = input_spike_or_current  # [B, T, C, H, W]

        # Compute output spatial size (assume same for all batch)
        _, _, _, in_h, in_w = current.shape
        out_h = (in_h + 2 * self.padding - self.kernel_size) // self.stride + 1
        out_w = (in_w + 2 * self.padding - self.kernel_size) // self.stride + 1

        membrane = torch.zeros(batch_size, self.out_channels, out_h, out_w, device=device)
        output_spikes = torch.zeros(batch_size, num_steps, self.out_channels, out_h, out_w, device=device)

        decay = self.lif_config.decay
        reset_val = self.lif_config.reset

        if self.timestep_vectorized:
            # Vectorized (high-VRAM opt) path for EventConv: batched conv over (B*T) then per-t LIF.
            # "루프 빼서" style for the conv op.
            current_flat = current.reshape(batch_size * num_steps, current.size(2), in_h, in_w).float()
            conv_flat = F.conv2d(current_flat, self.weight, stride=self.stride, padding=self.padding)
            conv_out = conv_flat.reshape(batch_size, num_steps, self.out_channels, out_h, out_w)

            for t in range(num_steps):
                membrane = decay * membrane + conv_out[:, t]
                thresh = self.threshold.view(1, -1, 1, 1)
                spiked = SpikeFunction.apply(membrane, thresh, self.surrogate, self.surrogate_slope)
                output_spikes[:, t] = spiked
                membrane = membrane * (1.0 - spiked.detach()) + reset_val * spiked.detach()
        else:
            # Classic per-timestep conv (default, lower VRAM): conv only the current slice each step.
            # "루프로" style. Lower peak feature-map memory.
            for t in range(num_steps):
                curr_t = current[:, t].float()  # (B, C, H, W)
                conv_t = F.conv2d(curr_t, self.weight, stride=self.stride, padding=self.padding)
                membrane = decay * membrane + conv_t
                thresh = self.threshold.view(1, -1, 1, 1)
                spiked = SpikeFunction.apply(membrane, thresh, self.surrogate, self.surrogate_slope)
                output_spikes[:, t] = spiked
                membrane = membrane * (1.0 - spiked.detach()) + reset_val * spiked.detach()

        states = {
            "membrane": membrane,
            "output_spike_volume": output_spikes,
        }
        return output_spikes, states


# (Old SpikingHybridModel class removed during unification into SpikingModel.
# Users now instantiate SpikingModel(conv_specs=..., fc_sizes=...) for hybrid/EventConv+FC cases.)
        compiled = self._compile_to_topology()

        weight_dict: Dict[str, np.ndarray] = {}
        for i, projection in enumerate(compiled.projections):
            w = self._weights[i].detach().cpu().numpy() * hw_weight_scale
            if hw_weight_clip is not None:
                w = np.clip(w, hw_weight_clip[0], hw_weight_clip[1])
            quantized = w.astype(np.int8)
            weight_dict[projection.name] = quantized

        return build_spikemold_artifact(
            compiled,
            weight_dict,
            target=target,
            artifact_id=artifact_id,
        )

    def _compile_to_topology(self) -> CompiledSpikePressTopology:
        network = SpikePressNetwork()

        populations: List[SpikePressNeuronPopulation] = []
        for i, size in enumerate(self.layer_sizes):
            pop = network.add_population(
                SpikePressNeuronPopulation(size, name=f"layer_{i}")
            )
            populations.append(pop)

        for i in range(self.num_layers):
            proj = SpikePressProjection(populations[i], populations[i + 1])
            proj.weights = self._weights[i].detach().cpu().numpy()
            network.add_projection(proj)

        return network.compile()


# =============================================================================
# Trainer for PyTorch-style Training
# =============================================================================

class SpikePressTrainer:
    """Trainer for Spiking Neural Networks with PyTorch-style API."""

    def __init__(
        self,
        model: SpikingModel,
        lif_config: LIFNeuronConfig,
        num_steps: int = 16,
        device: str = "cpu",
        spike_reg: float = 0.0,   # L1 regularization on total spikes (common to control activity)
    ):
        self.model = model
        self.lif_config = lif_config
        self.num_steps = num_steps
        self.device = torch.device(device)
        self.spike_reg = float(spike_reg)

    def train_epoch(
        self,
        dataloader: DataLoader,
        lr: float = 0.01,
        clip_grad: float = 1.0,
        log_interval: int = 100,
    ) -> Dict[str, float]:
        """Train for one epoch using spike-count cross-entropy (standard for direct SNN training).
        Uses mixed precision (bf16/fp16) via autocast to improve GPU utilization on large models.
        """
        self.model.train()
        total_loss = 0.0
        correct = 0
        total = 0

        optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=1e-4)
        scaler = torch.amp.GradScaler('cuda', enabled=(self.device.type == 'cuda'))

        _batch_block_start = time.time()
        prev_batch_loss = None
        for batch_idx, (data, target) in enumerate(dataloader):
            data, target = data.to(self.device), target.to(self.device)

            # Prepare input_tensor with encoding (if rate) OUTSIDE the model forward.
            # This is critical for --vectorize-timesteps + CUDAGraph stability:
            # rand allocations must not happen inside captured graph regions.
            # For hybrid, we now pre-encode to 5D spikes (matching what _forward_hybrid expects when dim!=4).
            if getattr(self.model, "_is_hybrid", False):
                if getattr(self.model, "input_encoding", "direct") == "rate":
                    b, c, h, w = data.shape
                    rates = torch.clamp(data * 2.0 + 0.5, 0.0, 1.0).unsqueeze(1).expand(-1, self.num_steps, -1, -1, -1)
                    rand_mat = torch.rand(b, self.num_steps, c, h, w, device=data.device)
                    input_tensor = (rand_mat < rates).float()
                else:
                    input_tensor = data.unsqueeze(1).expand(-1, self.num_steps, -1, -1, -1)
            else:
                # Flatten for FC 1D
                flat_data = data.view(data.size(0), -1)

                # Prepare input according to model's encoding.
                if getattr(self.model, "input_encoding", "direct") == "rate":
                    rates = torch.clamp(flat_data * 2.0 + 0.5, 0.0, 1.0)
                    rand_mat = torch.rand(flat_data.size(0), self.num_steps, flat_data.size(1), device=data.device)
                    input_tensor = (rand_mat < rates.unsqueeze(1)).float()
                else:
                    input_tensor = flat_data.unsqueeze(1).expand(-1, self.num_steps, -1)

            optimizer.zero_grad()
            if getattr(self.model, 'timestep_vectorized', False):
                # Recommended by torch for CUDAGraphs in training loops with repeated forward/backward.
                # Helps avoid "pending uninvoked backwards" and graph capture state issues.
                try:
                    torch.compiler.cudagraph_mark_step_begin()
                except Exception:
                    pass
            with torch.amp.autocast('cuda', enabled=(self.device.type == 'cuda')):
                output_spikes, states = self.model.forward(input_tensor, self.num_steps)

                # Hybrid: prefer final membrane from fc head (when created with output_mode=membrane)
                # as logits for CE; falls back to spike count. Pure FC respects its output_mode.
                if hasattr(self.model, "convs"):
                    fc_st = states.get("fc_states", {}) if isinstance(states, dict) else {}
                    if isinstance(fc_st, dict) and fc_st.get("final_membrane") is not None:
                        logits = fc_st["final_membrane"]
                    else:
                        logits = output_spikes.sum(dim=1)
                elif getattr(self.model, "output_mode", "spike_count") == "membrane":
                    logits = states.get("final_membrane")
                    if logits is None:
                        logits = output_spikes.sum(dim=1)
                else:
                    logits = output_spikes.sum(dim=1)

                logits = torch.clamp(logits, -20.0, 20.0)  # stability clamp for large hybrid to prevent exploding CE loss
                loss = F.cross_entropy(logits, target)

                # Optional spike count regularization (L1 on total spikes across layers/time)
                # Improved to penalize the large hidden population (e.g. 65k) in hybrid models.
                # This is critical to prevent the high firing rates (0.3-0.6) that were causing
                # divergence/saturation in the max-resource 65k experiments. Only final output
                # spikes are not enough.
                if self.spike_reg > 0:
                    total_spikes = output_spikes.sum()
                    # Pull hidden spike volume if the model exposed it (from the big hidden layer in FC head)
                    hidden_vol = states.get("hidden_spike_volume", 0)
                    if getattr(self.model, "_is_hybrid", False):
                        fc_st = states.get("fc_states", {})
                        if isinstance(fc_st, dict):
                            hidden_vol = hidden_vol + fc_st.get("hidden_spike_volume", 0)
                    reg_spikes = total_spikes + hidden_vol
                    loss = loss + self.spike_reg * reg_spikes / (data.size(0) * self.num_steps)

            scaler.scale(loss).backward()

            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), clip_grad)
            scaler.step(optimizer)
            scaler.update()

            # Conservative loss spike handling for large hybrid stability:
            # Delay damping until after initial batches (let early learning happen).
            # Then, if spike, mildly reduce LR in-place (smaller reduction).
            curr_l = loss.item()
            if batch_idx > 50 and prev_batch_loss is not None and curr_l > max(0.3, prev_batch_loss * 1.5):
                for g in optimizer.param_groups:
                    g['lr'] = max(g['lr'] * 0.95, 1e-6)
                print(f"  (loss spike {prev_batch_loss:.3f} -> {curr_l:.3f}; mild LR reduce to {optimizer.param_groups[0]['lr']:.6f})")
            prev_batch_loss = 0.9 * (prev_batch_loss or curr_l) + 0.1 * curr_l   # light ema for detector

            total_loss += loss.item()
            correct += self._count_correct(output_spikes, target)
            total += target.size(0)

            if batch_idx % log_interval == 0:
                print(
                    f"Train Epoch: {batch_idx}/{len(dataloader)} "
                    f"Loss: {loss.item():.4f} "
                    f"Acc: {100 * correct / total:.2f}%"
                )

            # Simple per-100-batch timing to quantify raw throughput for the 65k vectorized model
            if batch_idx % 100 == 0:
                if batch_idx > 0:
                    print(f"  (100 batches in {time.time() - _batch_block_start:.1f}s)")
                _batch_block_start = time.time()

        return {
            "loss": total_loss / len(dataloader),
            "accuracy": correct / total,
        }

    def evaluate(
        self,
        dataloader: DataLoader,
        num_samples: Optional[int] = None,
    ) -> Dict[str, float]:
        """Evaluate model on validation/test set (CE on spike counts). Uses autocast for consistency."""
        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0

        with torch.no_grad():
            with torch.amp.autocast('cuda', enabled=(self.device.type == 'cuda')):
                for batch_idx, (data, target) in enumerate(dataloader):
                    data, target = data.to(self.device), target.to(self.device)

                    # Same pre-encoding as train_epoch for CUDAGraph/vectorize stability.
                    if getattr(self.model, "_is_hybrid", False):
                        if getattr(self.model, "input_encoding", "direct") == "rate":
                            b, c, h, w = data.shape
                            rates = torch.clamp(data * 2.0 + 0.5, 0.0, 1.0).unsqueeze(1).expand(-1, self.num_steps, -1, -1, -1)
                            rand_mat = torch.rand(b, self.num_steps, c, h, w, device=data.device)
                            input_tensor = (rand_mat < rates).float()
                        else:
                            input_tensor = data.unsqueeze(1).expand(-1, self.num_steps, -1, -1, -1)
                    else:
                        flat_data = data.view(data.size(0), -1)
                        if getattr(self.model, "input_encoding", "direct") == "rate":
                            rates = torch.clamp(flat_data * 2.0 + 0.5, 0.0, 1.0)
                            rand_mat = torch.rand(flat_data.size(0), self.num_steps, flat_data.size(1), device=data.device)
                            input_tensor = (rand_mat < rates.unsqueeze(1)).float()
                        else:
                            input_tensor = flat_data.unsqueeze(1).expand(-1, self.num_steps, -1)

                    if getattr(self.model, 'timestep_vectorized', False):
                        try:
                            torch.compiler.cudagraph_mark_step_begin()
                        except Exception:
                            pass
                    output_spikes, states = self.model.forward(input_tensor, self.num_steps)

                    # Hybrid: prefer final membrane from fc head (when created with output_mode=membrane)
                    # as logits for CE; falls back to spike count. Pure FC respects its output_mode.
                    if hasattr(self.model, "convs"):
                        fc_st = states.get("fc_states", {}) if isinstance(states, dict) else {}
                        if isinstance(fc_st, dict) and fc_st.get("final_membrane") is not None:
                            logits = fc_st["final_membrane"]
                        else:
                            logits = output_spikes.sum(dim=1)
                    elif getattr(self.model, "output_mode", "spike_count") == "membrane":
                        logits = states.get("final_membrane") or output_spikes.sum(dim=1)
                    else:
                        logits = output_spikes.sum(dim=1)
                    logits = torch.clamp(logits, -20.0, 20.0)  # stability clamp for large hybrid
                    loss = F.cross_entropy(logits, target)
                    total_loss += loss.item()
                    correct += self._count_correct(output_spikes, target)
                    total += target.size(0)

                    if num_samples and total >= num_samples:
                        break

        return {
            "loss": total_loss / max(1, len(dataloader)),
            "accuracy": correct / total,
        }

    def _count_correct(
        self,
        output_spikes: torch.Tensor,
        target_labels: torch.Tensor,
    ) -> int:
        """Argmax over total spike count (standard for rate-coded SNN classification)."""
        spike_counts = output_spikes.sum(dim=1)
        predicted = spike_counts.argmax(dim=1)
        return (predicted == target_labels).sum().item()

    def compile_to_artifact(
        self,
        artifact_id: str = "trained_snn",
        target: str = "pynq-z2",
    ) -> SpikeMoldArtifact:
        """Compile trained model to SpikeMold artifact."""
        return self.model.to_artifact(artifact_id=artifact_id, target=target)


# =============================================================================
# ANN-to-SNN Conversion (for hybrid workflow)
# =============================================================================
class SimpleANN(torch.nn.Module):
    """Standard ANN (ReLU) for pre-training before conversion (matches original repo workflow)."""

    def __init__(self, layer_sizes: Sequence[int]):
        super().__init__()
        layers = []
        for i in range(len(layer_sizes) - 1):
            layers.append(torch.nn.Linear(layer_sizes[i], layer_sizes[i + 1]))
            if i < len(layer_sizes) - 2:
                layers.append(torch.nn.ReLU())
        self.net = torch.nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


def train_ann(
    layer_sizes: Sequence[int],
    train_loader: DataLoader,
    test_loader: DataLoader,
    epochs: int = 5,
    lr: float = 0.01,
    device: str = "cpu",
) -> torch.nn.Module:
    """Quickly train a standard ANN (for subsequent conversion to SNN)."""
    model = SimpleANN(layer_sizes).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    crit = torch.nn.CrossEntropyLoss()
    for ep in range(epochs):
        model.train()
        for data, target in train_loader:
            data, target = data.to(device).view(data.size(0), -1), target.to(device)
            opt.zero_grad()
            out = model(data)
            loss = crit(out, target)
            loss.backward()
            opt.step()
        # quick val
        model.eval()
        correct = 0
        tot = 0
        with torch.no_grad():
            for data, target in test_loader:
                data, target = data.to(device).view(data.size(0), -1), target.to(device)
                pred = model(data).argmax(1)
                correct += (pred == target).sum().item()
                tot += target.size(0)
        print(f"ANN epoch {ep+1}: val acc {100*correct/tot:.1f}%")
    return model


def ann_to_snn(
    ann_model: torch.nn.Module,
    layer_sizes: Sequence[int],
    lif_config: Optional[LIFNeuronConfig] = None,
    weight_scale: float = 1.0,
    clip: Optional[Tuple[float, float]] = None,
    device: str = "cpu",
) -> SpikingModel:
    """Convert a trained ANN (Linear+ReLU) to SpikingModel.

    Basic conversion (as in original pytorch_interface / history):
      - Extract Linear weights
      - Optional scale (e.g. 128 for fixed-point like original *128 clip[-128,127])
      - Clip if requested (for our 4-bit: clip=(-8,7))
      - Initialize SpikingModel and load the (scaled) weights.
      - Neuron params from lif_config (default HW IF).

    Note: full conversion may also involve threshold balancing / rate norm;
    this provides the basic weight-transfer path requested.
    """
    if lif_config is None:
        lif_config = LIFNeuronConfig.from_hardware()
    snn = SpikingModel(layer_sizes, lif_config, device=device, timestep_vectorized=False)

    # Collect Linear weights in order. nn.Linear stores (out, in); SpikingModel uses (in, out)
    weights = []
    for m in ann_model.modules():
        if isinstance(m, torch.nn.Linear):
            weights.append(m.weight.data.detach().T.clone())  # transpose to (in, out)

    if len(weights) != snn.num_layers:
        raise ValueError(f"ANN has {len(weights)} Linear layers, expected {snn.num_layers}")

    converted = []
    for w in weights:
        w = w * weight_scale
        if clip is not None:
            w = torch.clamp(w, clip[0], clip[1])
        converted.append(w.cpu().numpy())

    snn.set_weights(converted)
    return snn


def pytorch_to_snn(
    torch_model: torch.nn.Module,
    layer_sizes: Sequence[int],
    scale: float = 128.0,
    clip_range: Tuple[float, float] = (-128.0, 127.0),
    **lif_kwargs,
) -> SpikingModel:
    """Historical-style pytorch_to_snn: scale weights *128, clip to int8 range, produce SNN.

    Matches the "Original Repo" conversion workflow discussed.
    Use clip_range=(-8,7) + scale=1.0 for current 4-bit SpikeMold default.
    """
    lif_config = LIFNeuronConfig(**lif_kwargs) if lif_kwargs else LIFNeuronConfig.from_hardware()
    return ann_to_snn(
        torch_model,
        layer_sizes,
        lif_config=lif_config,
        weight_scale=scale,
        clip=clip_range,
    )


# =============================================================================
# HW-SW Co-design Helpers (SpikePress <-> SpikeMold)
# =============================================================================
#
# These utilities ensure that what is learned in the PyTorch surrogate trainer
# can be faithfully deployed and verified on the integer event-driven SpikeMold HW.
# Key principle: training forward (float, surrogate) is an *approximation tool*.
# Final equivalence and board claims are done via:
#   1. Quantized weights from artifact
#   2. Exact same InputSpike events (rate-coded or encoder-equivalent)
#   3. Integer golden trace (generate_multilayer_fc_lif_trace or per-layer)
#   4. Real board execution (full_board_run) + output event decode
#
# Always keep the rate encoding logic in the trainer and the spike->InputSpike
# converter in sync.

from .architecture_trace_generator import InputSpike  # for type / conversion helpers


def spike_train_to_input_spikes(
    spike_train: torch.Tensor,  # [batch, T, input_size] binary or [T, input_size]
    input_id_start: int = 0,
    batch_index: int = 0,
) -> list[InputSpike]:
    """Convert the dense rate-coded spike tensor used in training into list[InputSpike].

    Bridge from the PyTorch training loop (dense 0/1 per timestep)
    to the AER-style events expected by the SpikeMold runtime and golden trace.

    Matches the bernoulli rate logic used inside SpikePressTrainer.
    """
    if spike_train.dim() == 2:
        spike_train = spike_train.unsqueeze(0)  # treat as batch=1

    spikes: list[InputSpike] = []
    b = batch_index
    for t in range(spike_train.shape[1]):
        for j in range(spike_train.shape[2]):
            if spike_train[b, t, j] > 0.5:  # binary spike at (t, j)
                spikes.append(InputSpike(tick=t, src_id=input_id_start + j))
    return spikes


def images_to_rate_input_spikes(
    images: torch.Tensor,  # [N, 1, 28, 28] or [N, 784] in [0,1] or normalized
    num_steps: int,
    input_id_start: int = 0,
    rate_scale: float = 1.0,
    clamp: bool = True,
) -> list[list[InputSpike]]:
    """Replicate the exact rate encoding used during training and turn images into per-sample InputSpike lists.

    Use this when you want to feed a test set to the golden trace or to run_model_on_board
    with the *identical* stochastic or deterministic events that the loss saw.
    """
    if images.dim() == 4:
        images = images.view(images.size(0), -1)

    all_spike_lists: list[list[InputSpike]] = []
    for b in range(images.size(0)):
        data = images[b]
        rates = torch.clamp(data * 2.0 * rate_scale + 0.5, 0.0, 1.0) if clamp else data
        rand_mat = torch.rand(num_steps, data.size(0), device=data.device)
        spike_train = (rand_mat < rates.unsqueeze(0)).float()
        spike_list = spike_train_to_input_spikes(spike_train, input_id_start=input_id_start, batch_index=0)
        all_spike_lists.append(spike_list)
    return all_spike_lists


def evaluate_with_integer_trace(
    model: SpikingModel,
    input_spike_lists: list[list[InputSpike]],
    thresholds: Optional[dict[int, int]] = None,
) -> list[torch.Tensor]:
    """Run the *quantized integer* IF semantics (exact same as golden trace + HW) on a trained model.

    Co-design "golden" evaluator. It uses the weights that will actually
    be packed into the artifact (clipped int8) and the multilayer trace generator.

    Returns per-sample spike counts for the output population (for argmax classification).
    """
    from .architecture_trace_generator import generate_multilayer_fc_lif_trace
    from .network import CompiledSpikePressTopology

    compiled: CompiledSpikePressTopology = model._compile_to_topology()

    # Build per-projection quantized weight maps exactly as they will be packed in the artifact.
    # Key co-design step: the integer trace and the board see these exact small ints.
    quantized_weights_per_proj: list[dict[tuple[int, int], int]] = []
    for li, proj_info in enumerate(compiled.projections):
        w_float = model._weights[li].detach().cpu().numpy()
        w_q = np.clip(w_float, -8, 7).astype(np.int8)
        w_map: dict[tuple[int, int], int] = {}
        s0 = proj_info.source_id_start
        d0 = proj_info.target_id_start
        for si in range(proj_info.source_size):
            for di in range(proj_info.target_size):
                w_map[(s0 + si, d0 + di)] = int(w_q[si, di])
        quantized_weights_per_proj.append(w_map)

    # Use the model's own (scaled) threshold so that the integer trace matches
    # the scale the surrogate was trained against.
    th_scaled = int(model.lif_config.threshold * model.lif_config.scaling_factor)

    results = []
    for spike_list in input_spike_lists:
        layer_cfgs = []
        for li, proj_info in enumerate(compiled.projections):
            thresh_map = {
                nid: th_scaled
                for nid in range(proj_info.target_id_start,
                                 proj_info.target_id_start + proj_info.target_size)
            }
            layer_cfgs.append({
                "name": proj_info.name or f"layer_{li}",
                "weights": quantized_weights_per_proj[li],
                "thresholds": thresh_map,
                "reset_values": {nid: 0 for nid in thresh_map},
            })

        trace = generate_multilayer_fc_lif_trace(
            layer_configs=layer_cfgs,
            input_spikes=spike_list,
        )

        # Count output spikes in the last population
        output_start = compiled.population_id_start[-2] if len(compiled.population_id_start) > 1 else 0
        output_size = compiled.populations[-1].size if compiled.populations else 10
        counts = torch.zeros(output_size)
        for commit in trace.commits:
            if output_start <= commit.dst_id < output_start + output_size:
                counts[commit.dst_id - output_start] += 1
        results.append(counts)

    return results


# close the big if _TORCH_AVAILABLE that wraps all torch-dependent training/conversion/co-design code