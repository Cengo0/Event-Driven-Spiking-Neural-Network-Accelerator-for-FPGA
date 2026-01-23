"""
SpykeTorch Compatible Functions for SNN FPGA Accelerator

This module provides SpykeTorch-like functional operations for building
Mozafari et al. (2018) style R-STDP networks.

Key components:
- DoG (Difference of Gaussian) filters
- Gabor filters  
- Intensity to Latency encoding
- Pointwise inhibition
- Local normalization
- Winner-take-all with radius (k-winners)
- STDP convolution layer

Reference:
    Mozafari, M., et al. "First-spike-based visual categorization using 
    reward-modulated STDP." IEEE TNNLS (2018).

Author: Jiwoon Lee (@metr0jw)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor
from typing import Optional, Tuple, List, Union
import math
import numpy as np

__all__ = [
    # Filters
    'DoGKernel', 'GaborKernel', 'Filter',
    # Transforms
    'Intensity2Latency', 'LateralIntensityInhibition',
    # Functional operations
    'local_normalization', 'pointwise_inhibition', 'fire',
    'get_k_winners', 'get_k_winners_pot', 'pooling', 'pad',
    # STDP Layer
    'STDPConvolution', 'STDP',
    # Complete transforms
    'S1C1Transform',
]


# =============================================================================
# Filter Kernels
# =============================================================================

class DoGKernel:
    """
    Difference of Gaussian (DoG) kernel.
    
    Approximates edge detection in biological visual systems.
    DoG = Gaussian(sigma1) - Gaussian(sigma2)
    
    Args:
        kernel_size: Size of the kernel (must be odd)
        sigma1: Sigma for the first Gaussian (center)
        sigma2: Sigma for the second Gaussian (surround)
    """
    
    def __init__(self, kernel_size: int, sigma1: float, sigma2: float):
        assert kernel_size % 2 == 1, "Kernel size must be odd"
        self.kernel_size = kernel_size
        self.sigma1 = sigma1
        self.sigma2 = sigma2
        self.kernel = self._create_kernel()
    
    def _create_kernel(self) -> Tensor:
        """Create DoG kernel."""
        k = self.kernel_size
        center = k // 2
        
        x = torch.arange(k, dtype=torch.float32) - center
        y = torch.arange(k, dtype=torch.float32) - center
        y, x = torch.meshgrid(y, x, indexing='ij')
        
        # Two Gaussians
        g1 = torch.exp(-(x**2 + y**2) / (2 * self.sigma1**2))
        g2 = torch.exp(-(x**2 + y**2) / (2 * self.sigma2**2))
        
        # Normalize each Gaussian
        g1 = g1 / g1.sum()
        g2 = g2 / g2.sum()
        
        # Difference
        dog = g1 - g2
        
        return dog
    
    def __call__(self) -> Tensor:
        return self.kernel.clone()


class GaborKernel:
    """
    Gabor kernel for orientation-selective filtering.
    
    Args:
        kernel_size: Size of the kernel (must be odd)
        theta: Orientation angle in degrees
        sigma: Gaussian envelope sigma
        freq: Spatial frequency
        gamma: Aspect ratio (default: 1.0)
        psi: Phase offset (default: 0)
    """
    
    def __init__(
        self,
        kernel_size: int,
        theta: float,
        sigma: float = 1.0,
        freq: float = 0.25,
        gamma: float = 1.0,
        psi: float = 0.0
    ):
        assert kernel_size % 2 == 1, "Kernel size must be odd"
        self.kernel_size = kernel_size
        self.theta = math.radians(theta)  # Convert to radians
        self.sigma = sigma
        self.freq = freq
        self.gamma = gamma
        self.psi = psi
        self.kernel = self._create_kernel()
    
    def _create_kernel(self) -> Tensor:
        """Create Gabor kernel."""
        k = self.kernel_size
        center = k // 2
        
        x = torch.arange(k, dtype=torch.float32) - center
        y = torch.arange(k, dtype=torch.float32) - center
        y, x = torch.meshgrid(y, x, indexing='ij')
        
        # Rotation
        x_theta = x * math.cos(self.theta) + y * math.sin(self.theta)
        y_theta = -x * math.sin(self.theta) + y * math.cos(self.theta)
        
        # Gabor function
        gaussian = torch.exp(
            -0.5 * (x_theta**2 + self.gamma**2 * y_theta**2) / self.sigma**2
        )
        sinusoidal = torch.cos(2 * math.pi * self.freq * x_theta + self.psi)
        
        gabor = gaussian * sinusoidal
        
        # Normalize to zero mean
        gabor = gabor - gabor.mean()
        gabor = gabor / (gabor.norm() + 1e-8)
        
        return gabor
    
    def __call__(self) -> Tensor:
        return self.kernel.clone()


class Filter(nn.Module):
    """
    Apply a bank of filters to input images.
    
    Args:
        kernels: List of kernel objects (DoGKernel, GaborKernel)
        padding: Padding size (default: auto-calculated)
        thresholds: Threshold values for each filter (optional)
        use_abs: Use absolute value of filter responses
    """
    
    def __init__(
        self,
        kernels: List,
        padding: Optional[int] = None,
        thresholds: Optional[Union[float, List[float]]] = None,
        use_abs: bool = True
    ):
        super().__init__()
        
        self.use_abs = use_abs
        
        # Stack kernels into conv weights
        kernel_tensors = [k() if callable(k) else k.kernel for k in kernels]
        self.num_filters = len(kernel_tensors)
        
        # Find max kernel size
        self.max_window_size = max(k.shape[0] for k in kernel_tensors)
        
        # Pad smaller kernels to match largest
        padded_kernels = []
        for k in kernel_tensors:
            if k.shape[0] < self.max_window_size:
                pad_size = (self.max_window_size - k.shape[0]) // 2
                k = F.pad(k, (pad_size, pad_size, pad_size, pad_size))
            padded_kernels.append(k)
        
        # Create weight tensor (out_ch, in_ch, H, W)
        weight = torch.stack(padded_kernels).unsqueeze(1)
        self.register_buffer('kernels', weight)
        
        # Padding
        self.padding = padding if padding is not None else self.max_window_size // 2
        
        # Thresholds
        if thresholds is not None:
            if isinstance(thresholds, (int, float)):
                thresholds = [thresholds] * self.num_filters
            self.register_buffer('thresholds', torch.tensor(thresholds, dtype=torch.float32))
        else:
            self.thresholds = None
    
    def forward(self, x: Tensor) -> Tensor:
        """
        Apply filter bank to input.
        
        Args:
            x: Input tensor (B, 1, H, W) or (1, 1, H, W)
            
        Returns:
            Filtered output (B, num_filters, H, W)
        """
        # Apply convolution
        out = F.conv2d(x, self.kernels, padding=self.padding)
        
        # Absolute value
        if self.use_abs:
            out = torch.abs(out)
        
        # Apply thresholds
        if self.thresholds is not None:
            for i in range(self.num_filters):
                out[:, i] = torch.where(
                    out[:, i] > self.thresholds[i],
                    out[:, i],
                    torch.zeros_like(out[:, i])
                )
        
        return out


# =============================================================================
# Temporal Encoding
# =============================================================================

class Intensity2Latency(nn.Module):
    """
    Convert intensity values to spike latencies using bin-packing.
    
    This is the SpykeTorch-compatible implementation where:
    - Intensities are sorted and packed into bins
    - Each bin has roughly equal number of spikes
    - Higher intensity = earlier bin (earlier spike)
    - Zero intensities are excluded (don't generate spikes)
    - Spikes are accumulative (spike at t appears in t+1, t+2, ...)
    
    Args:
        time_steps: Number of time steps (bins)
        to_spike: Convert to binary spike tensor (default: True)
    """
    
    def __init__(self, time_steps: int = 15, to_spike: bool = True):
        super().__init__()
        self.time_steps = time_steps
        self.to_spike = to_spike
    
    def forward(self, x: Tensor) -> Tensor:
        """
        Args:
            x: Input intensity tensor (B, C, H, W) in [0, max]
            
        Returns:
            Spike tensor (T, B, C, H, W) or (T, C, H, W) if B=1
        """
        # Get shape info
        shape = x.shape
        device = x.device
        
        # Count non-zero elements
        nonzero_mask = x > 0
        nonzero_cnt = nonzero_mask.sum().item()
        
        if nonzero_cnt == 0:
            # No activity - return zeros
            spikes = torch.zeros(self.time_steps, *shape, device=device, dtype=x.dtype)
            return spikes
        
        # Bin size: divide non-zero elements equally among time steps
        bin_size = max(1, nonzero_cnt // self.time_steps)
        
        # Flatten and sort by intensity (descending - highest first)
        x_flat = x.view(-1)
        sorted_vals, sorted_idx = torch.sort(x_flat, descending=True)
        
        # Create spike map for each timestep
        bins_intensities = []
        spike_map = torch.zeros_like(x_flat)
        
        for t in range(self.time_steps):
            # Get indices for this bin
            start_idx = t * bin_size
            end_idx = min((t + 1) * bin_size, len(sorted_idx))
            
            if start_idx >= len(sorted_idx):
                break
                
            # Assign values to spike map (accumulative)
            bin_indices = sorted_idx[start_idx:end_idx]
            bin_values = sorted_vals[start_idx:end_idx]
            
            # Only include non-zero values
            valid_mask = bin_values > 0
            if valid_mask.any():
                spike_map.scatter_(0, bin_indices[valid_mask], bin_values[valid_mask])
            
            # Clone current state
            spike_map_reshaped = spike_map.clone().reshape(shape)
            bins_intensities.append(spike_map_reshaped.squeeze(0).float())
        
        # Pad with final state if needed
        while len(bins_intensities) < self.time_steps:
            bins_intensities.append(bins_intensities[-1].clone())
        
        result = torch.stack(bins_intensities)
        
        if self.to_spike:
            return result.sign()
        return result


def _generate_inhibition_kernel(inhibition_percents: List[float]) -> Tensor:
    """
    Generate inhibition kernel for lateral intensity inhibition.
    
    Creates a spatial kernel where the center is 0 and surrounding positions
    contain the inhibition factors based on Chebyshev distance.
    
    Args:
        inhibition_percents: List of inhibition factors for each distance ring
        
    Returns:
        Tensor: (2*len+1, 2*len+1) inhibition kernel
    """
    size = 2 * len(inhibition_percents) + 1
    kernel = torch.zeros(size, size, dtype=torch.float32)
    center = len(inhibition_percents)
    
    for i in range(size):
        for j in range(size):
            dist = int(max(abs(i - center), abs(j - center)))
            if dist != 0 and dist <= len(inhibition_percents):
                kernel[i, j] = inhibition_percents[dist - 1]
    
    return kernel


class LateralIntensityInhibition(nn.Module):
    """
    Lateral intensity inhibition from SpykeTorch.
    
    For each location, decreases the intensity of surrounding cells that have
    lower intensities by a specific factor based on their distance.
    
    This is a SPATIAL operation - it inhibits nearby weaker responses.
    
    For each pixel, if it is stronger than a neighbor, that neighbor gets
    inhibited (its value increases by inhibition_percent * value, which
    acts to suppress it relative to the strong center).
    
    Args:
        inhibition_percents: List of inhibition factors for each distance ring
                            e.g., [0.15, 0.12, 0.1, 0.07, 0.05]
    """
    
    def __init__(self, inhibition_percents: List[float]):
        super().__init__()
        self.inhibition_percents = inhibition_percents
        self.inhibition_kernel = _generate_inhibition_kernel(inhibition_percents)
        # Shape: (1, 1, k, k) for use with conv2d
        self.inhibition_kernel = self.inhibition_kernel.unsqueeze(0).unsqueeze(0)
        self.radius = len(inhibition_percents)
    
    def forward(self, x: Tensor) -> Tensor:
        """
        Apply lateral intensity inhibition.
        
        The algorithm:
        1. For each spatial location, compare with neighbors
        2. If center > neighbor, neighbor gets inhibited
        3. Inhibition factor depends on distance from center
        
        Args:
            x: Input tensor (B, C, H, W)
            
        Returns:
            Inhibited tensor (B, C, H, W)
        """
        device = x.device
        kernel = self.inhibition_kernel.to(device)
        k = kernel.size(-1)
        rad = k // 2
        
        # Process each channel independently
        B, C, H, W = x.shape
        results = []
        
        for c in range(C):
            channel = x[:, c:c+1, :, :]  # (B, 1, H, W)
            
            # Pad the channel
            padded = F.pad(channel, (rad, rad, rad, rad))
            
            # For each position, count how many neighbors are smaller
            # and accumulate inhibition factor
            # This is equivalent to the SpykeTorch algorithm
            
            # Use unfold to get patches
            patches = F.unfold(padded, k)  # (B, k*k, H*W)
            center_idx = (k * k) // 2
            center_vals = patches[:, center_idx:center_idx+1, :]  # (B, 1, H*W)
            
            # Compare center with all positions in patch
            # Where center > neighbor, neighbor should be inhibited
            diff = center_vals - patches  # (B, k*k, H*W)
            mask = (diff > 0).float()  # 1 where center > neighbor
            
            # Get inhibition weights for each position in patch
            kernel_flat = kernel.view(-1)  # (k*k,)
            
            # Accumulate inhibition: sum of (mask * kernel_weight)
            # This gives how much each position should be inhibited
            inhibition = (mask * kernel_flat.view(1, -1, 1)).sum(dim=1, keepdim=True)  # (B, 1, H*W)
            
            # Apply inhibition: result = value + value * inhibition_factor
            channel_flat = channel.view(B, 1, -1)  # (B, 1, H*W)
            result = channel_flat + channel_flat * inhibition
            
            result = result.view(B, 1, H, W)
            results.append(result)
        
        return torch.cat(results, dim=1)


# =============================================================================
# Functional Operations
# =============================================================================

def local_normalization(x: Tensor, kernel_size: int = 8) -> Tensor:
    """
    Local contrast normalization.
    
    Subtracts local mean and divides by local std.
    
    Args:
        x: Input tensor (B, C, H, W)
        kernel_size: Size of local window
        
    Returns:
        Normalized tensor
    """
    B, C, H, W = x.shape
    device = x.device
    
    # Create averaging kernel
    kernel = torch.ones(C, 1, kernel_size, kernel_size, device=device) / (kernel_size ** 2)
    
    # Calculate padding for 'same' output size
    # For even kernel sizes, we need asymmetric padding
    pad_total = kernel_size - 1
    pad_left = pad_total // 2
    pad_right = pad_total - pad_left
    pad_top = pad_total // 2
    pad_bottom = pad_total - pad_top
    
    # Pad input
    x_padded = F.pad(x, (pad_left, pad_right, pad_top, pad_bottom), mode='reflect')
    
    # Local mean using depthwise convolution
    local_mean = F.conv2d(x_padded, kernel, groups=C)
    
    # Ensure same size (should be automatic with correct padding)
    if local_mean.shape != x.shape:
        # Fallback: use F.avg_pool2d with padding
        local_mean = F.avg_pool2d(
            F.pad(x, (pad_left, pad_right, pad_top, pad_bottom), mode='reflect'),
            kernel_size, stride=1
        )
    
    # Local variance
    x_centered = x - local_mean
    x_centered_padded = F.pad(x_centered ** 2, (pad_left, pad_right, pad_top, pad_bottom), mode='reflect')
    local_var = F.conv2d(x_centered_padded, kernel, groups=C)
    
    if local_var.shape != x.shape:
        local_var = F.avg_pool2d(
            F.pad(x_centered ** 2, (pad_left, pad_right, pad_top, pad_bottom), mode='reflect'),
            kernel_size, stride=1
        )
    
    local_std = torch.sqrt(local_var + 1e-8)
    
    # Normalize
    out = x_centered / local_std
    
    return out


def pointwise_inhibition(spikes: Tensor) -> Tensor:
    """
    Pointwise inhibition: only first spike at each location survives.
    
    This is CRITICAL for proper temporal coding in Mozafari's method.
    Once a neuron spikes, it cannot spike again.
    
    Args:
        spikes: Spike tensor (T, B, C, H, W) or (T, C, H, W)
        
    Returns:
        Inhibited spike tensor
    """
    T = spikes.shape[0]
    
    # Track which locations have already spiked
    has_spiked = torch.zeros_like(spikes[0])
    
    out = torch.zeros_like(spikes)
    
    for t in range(T):
        # Only allow spikes where no spike has occurred yet
        new_spikes = spikes[t] * (1 - has_spiked)
        out[t] = new_spikes
        
        # Update spiked locations
        has_spiked = torch.clamp(has_spiked + new_spikes, 0, 1)
    
    return out


def fire(
    potentials: Tensor,
    threshold: float,
    return_potentials: bool = False
) -> Union[Tensor, Tuple[Tensor, Tensor]]:
    """
    Generate spikes from membrane potentials.
    
    Args:
        potentials: Membrane potentials (B, C, H, W)
        threshold: Firing threshold
        return_potentials: Also return potentials after reset
        
    Returns:
        spikes: Binary spike tensor
        potentials: (optional) Potentials with subthreshold values reset
    """
    spikes = (potentials >= threshold).float()
    
    if return_potentials:
        # Keep only potentials at spiking locations
        pot_out = potentials.clone()
        pot_out[potentials < threshold] = 0
        return spikes, pot_out
    
    return spikes


def get_k_winners(
    potentials: Tensor,
    k: int,
    radius: int,
    spikes: Tensor
) -> List[Tuple[int, int, int]]:
    """
    Get k winners with spatial inhibition radius.
    
    SpykeTorch-compatible: handles temporal input (T, C, H, W).
    Selects winners based on earliest spike time, then maximum potential.
    
    Args:
        potentials: Membrane potentials (T, C, H, W) - temporal
        k: Number of winners
        radius: Inhibition radius
        spikes: Spike tensor (same shape as potentials)
        
    Returns:
        List of winner tuples: (channel, y, x) for each winner
    """
    if spikes is None:
        spikes = potentials.sign()
    
    # Handle temporal dimension
    if potentials.dim() == 4:
        T, C, H, W = potentials.shape
        
        # Finding earliest spike time for each position
        # (T - sum of spikes) gives inverse latency (lower = earlier spike)
        # maximum[t] = T - cumsum => earliest spike has maximum value
        maximum = (T - spikes.sum(dim=0, keepdim=True)).long()
        maximum = maximum.clamp(0, T-1)
        
        # Gather potential at the earliest spike time
        values = potentials.gather(dim=0, index=maximum)  # (1, C, H, W)
        
        # Propagate earliest potential through all timesteps
        truncated_pot = spikes * values
        
        # Add large value at spike positions to prioritize earlier spikes
        v = truncated_pot.max() * T
        truncated_pot = truncated_pot + spikes * v
        
        # Sum over all timesteps
        total = truncated_pot.sum(dim=0)  # (C, H, W)
        spk_total = spikes.sum(dim=0)  # (C, H, W) for masking
    else:
        # Non-temporal case (C, H, W)
        C, H, W = potentials.shape
        total = potentials.clone()
        spk_total = spikes.clone()
    
    winners = []
    
    for _ in range(k):
        # Find location with maximum total among spiking neurons
        masked_total = total * (spk_total > 0).float()
        
        if masked_total.max() <= 0:
            break
        
        # Find max location
        flat_idx = masked_total.view(-1).argmax().item()
        c = flat_idx // (H * W)
        hw = flat_idx % (H * W)
        h = hw // W
        w = hw % W
        
        winners.append((c, h, w))
        
        # Prevent same feature from winning again
        total[c, :, :] = 0
        
        # Inhibit neurons within radius (columnar inhibition)
        if radius != 0:
            h_start = max(0, h - radius)
            h_end = min(H, h + radius + 1)
            w_start = max(0, w - radius)
            w_end = min(W, w + radius + 1)
            total[:, h_start:h_end, w_start:w_end] = 0
    
    return winners


def get_k_winners_pot(
    potentials: Tensor,
    k: int,
    radius: int
) -> List[Tuple[int, int, int]]:
    """
    Get k winners based on potential only (no spike threshold required).
    
    This ensures we always get a winner for learning, even when potentials
    are below the firing threshold. The learning rule will strengthen
    the winning neurons over time.
    
    Args:
        potentials: Membrane potentials (B, C, H, W) or (C, H, W)
        k: Number of winners
        radius: Inhibition radius
        
    Returns:
        List of winner tuples: (channel, y, x) for each winner
    """
    if potentials.dim() == 4:
        potentials = potentials[0]
    
    C, H, W = potentials.shape
    
    winners = []
    pot = potentials.clone()
    
    for _ in range(k):
        if pot.max() <= 0:
            break
        
        # Find max location
        flat_idx = pot.view(-1).argmax().item()
        c = flat_idx // (H * W)
        hw = flat_idx % (H * W)
        h = hw // W
        w = hw % W
        
        winners.append((c, h, w))
        
        # Inhibit neurons within radius
        h_start = max(0, h - radius)
        h_end = min(H, h + radius + 1)
        w_start = max(0, w - radius)
        w_end = min(W, w + radius + 1)
        
        pot[:, h_start:h_end, w_start:w_end] = 0
    
    return winners


def pooling(
    x: Tensor,
    kernel_size: int,
    stride: Optional[int] = None,
    padding: int = 0
) -> Tensor:
    """
    Spike-compatible max pooling.
    
    Args:
        x: Input tensor (B, C, H, W) or (C, H, W)
        kernel_size: Pooling window size
        stride: Pooling stride (default: kernel_size)
        padding: Padding size
        
    Returns:
        Pooled tensor
    """
    if stride is None:
        stride = kernel_size
    
    return F.max_pool2d(x, kernel_size, stride, padding)


def pad(x: Tensor, pad_size: Union[int, Tuple[int, ...]], value: float = 0) -> Tensor:
    """
    Pad tensor.
    
    Args:
        x: Input tensor
        pad_size: Padding (int for all sides, or tuple for (left, right, top, bottom))
        value: Padding value
        
    Returns:
        Padded tensor
    """
    if isinstance(pad_size, int):
        pad_size = (pad_size, pad_size, pad_size, pad_size)
    
    return F.pad(x, pad_size, value=value)


# =============================================================================
# STDP Convolution Layer
# =============================================================================

class STDPConvolution(nn.Module):
    """
    Convolution layer with STDP-compatible weight updates.
    
    This is the core trainable layer for Mozafari-style networks.
    Weights are kept in [0, 1] range and updated via STDP.
    
    Args:
        in_channels: Input channels
        out_channels: Output channels  
        kernel_size: Convolution kernel size
        weight_mean: Initial weight mean (default: 0.8)
        weight_std: Initial weight std (default: 0.05)
        padding: Convolution padding
    """
    
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: Union[int, Tuple[int, int]],
        weight_mean: float = 0.8,
        weight_std: float = 0.05,
        padding: int = 0
    ):
        super().__init__()
        
        self.in_channels = in_channels
        self.out_channels = out_channels
        
        if isinstance(kernel_size, int):
            kernel_size = (kernel_size, kernel_size)
        self.kernel_size = kernel_size
        self.padding = padding
        
        # Initialize weights in [0, 1]
        weight = torch.randn(out_channels, in_channels, *kernel_size)
        weight = weight * weight_std + weight_mean
        weight = torch.clamp(weight, 0, 1)
        self.weight = nn.Parameter(weight)
    
    def forward(self, x: Tensor) -> Tensor:
        """
        Convolve input spikes with weights.
        
        SpykeTorch-compatible: supports temporal input (T, C, H, W)
        where T is time dimension. Convolution is applied at each timestep.
        
        Args:
            x: Input spikes (T, C, H, W) or (B, C, H, W)
            
        Returns:
            Membrane potentials - same shape as input with different channels
        """
        return F.conv2d(x.float(), self.weight, padding=self.padding)
    
    def get_pre_post_spikes(
        self,
        input_spikes: Tensor,
        output_spikes: Tensor,
        winners: List[Tuple[int, int, int]]
    ) -> Tuple[Tensor, Tensor]:
        """
        Extract pre and post synaptic spikes for STDP.
        
        Args:
            input_spikes: Pre-synaptic spikes (B, in_C, H, W)
            output_spikes: Post-synaptic spikes (B, out_C, H', W')
            winners: List of winner positions (c, h, w)
            
        Returns:
            pre_spikes: (num_winners, in_C, kH, kW)
            post_spikes: (num_winners,) - always 1 for winners
        """
        if not winners:
            return None, None
        
        B = input_spikes.shape[0]
        kH, kW = self.kernel_size
        pad = self.padding
        
        # Pad input
        if pad > 0:
            input_padded = F.pad(input_spikes, (pad, pad, pad, pad))
        else:
            input_padded = input_spikes
        
        pre_patches = []
        
        for (c, h, w) in winners:
            # Extract input patch that corresponds to this output location
            patch = input_padded[0, :, h:h+kH, w:w+kW]  # (in_C, kH, kW)
            pre_patches.append(patch)
        
        if pre_patches:
            pre_spikes = torch.stack(pre_patches)  # (num_winners, in_C, kH, kW)
        else:
            pre_spikes = None
        
        return pre_spikes, winners


class STDP(nn.Module):
    """
    STDP learning rule for STDPConvolution layers.
    
    Implements the STDP weight update from Mozafari et al. (SpykeTorch).
    
    The learning rule determines weight changes based on spike timing:
    - LTP (a_plus): Applied when pre-synaptic spike fires BEFORE or AT SAME TIME as post
    - LTD (a_minus): Applied when pre-synaptic spike fires AFTER post (or didn't fire)
    
    Weight change: Δw = lr * (w - lower_bound) * (upper_bound - w)  [with stabilizer]
    
    Args:
        conv_layer: STDPConvolution layer to update
        learning_rate: Tuple of (a_plus, a_minus)
        use_stabilizer: Use weight stabilizer (default: True)
        lower_bound: Lower weight bound for stabilizer
        upper_bound: Upper weight bound for stabilizer
    """
    
    def __init__(
        self,
        conv_layer: STDPConvolution,
        learning_rate: Tuple[float, float],
        use_stabilizer: bool = True,
        lower_bound: float = 0.0,
        upper_bound: float = 1.0
    ):
        super().__init__()
        
        self.conv = conv_layer
        self.use_stabilizer = use_stabilizer
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        
        # Store per-feature learning rates (like SpykeTorch)
        self.learning_rate = []
        for i in range(conv_layer.out_channels):
            self.learning_rate.append([
                torch.tensor([learning_rate[0]]),  # a_plus (LTP)
                torch.tensor([learning_rate[1]])   # a_minus (LTD)
            ])
    
    def get_pre_post_ordering(
        self,
        input_spikes: Tensor,
        output_spikes: Tensor,
        winners: List[Tuple[int, int, int]],
        winner_fire_time: Optional[float] = None
    ) -> List[Tensor]:
        """
        Compute pre-post ordering for STDP based on SPIKE TIMING.
        
        Original SpykeTorch STDP rule:
        - LTP: Input spike fires BEFORE or AT output spike time
        - LTD: Input spike fires AFTER output spike time (or never)
        
        With winner_fire_time:
        - Computes first spike time for each input synapse
        - LTP if input_first_spike_time <= winner_fire_time
        - LTD if input_first_spike_time > winner_fire_time (or never spiked)
        
        Args:
            input_spikes: (T, C, H, W) input spike train
            output_spikes: (T or 1, C_out, H_out, W_out) output spikes
            winners: List of (channel, y, x) tuples
            winner_fire_time: The timestep at which winner fired (1-indexed, optional)
            
        Returns:
            List of boolean tensors - True where LTP should be applied, False for LTD
        """
        device = input_spikes.device
        T = input_spikes.shape[0]
        
        kH, kW = self.conv.kernel_size
        pad = self.conv.padding
        
        # Compute input first spike time for each position
        # Cumsum of spikes gives how many spikes by each time
        # T - cumsum gives inverse latency (higher = earlier spike)
        input_float = input_spikes.float()
        
        # Find first spike time for each position (1-indexed, T+1 means never spiked)
        input_first_spike = torch.full((input_float.shape[1], input_float.shape[2], input_float.shape[3]), 
                                       T + 1, device=device, dtype=torch.float32)
        for t in range(T):
            spiked_now = (input_float[t] > 0) & (input_first_spike > t)
            input_first_spike[spiked_now] = t + 1  # 1-indexed
        
        # Pad if needed
        if pad > 0:
            input_first_spike = F.pad(input_first_spike.unsqueeze(0), (pad, pad, pad, pad), value=T+1).squeeze(0)
        
        result = []
        for winner in winners:
            c, h, w = winner
            
            # Input first spike times in the receptive field
            in_times = input_first_spike[:, h:h+kH, w:w+kW]  # (C_in, kH, kW)
            
            if winner_fire_time is not None:
                # Use actual winner fire time for STDP ordering
                # LTP: input fired at or before winner
                # LTD: input fired after winner or never
                ordering = (in_times <= winner_fire_time)
            else:
                # Fallback: use spike count comparison (original SpykeTorch style)
                input_counts = input_spikes.float().sum(dim=0)
                if pad > 0:
                    input_counts = F.pad(input_counts.unsqueeze(0), (pad, pad, pad, pad), value=0).squeeze(0)
                in_tensor = input_counts[:, h:h+kH, w:w+kW]
                
                output_counts = output_spikes.float().sum(dim=0) if output_spikes.dim() == 4 else output_spikes.float()
                if output_counts.dim() == 3:
                    out_val = output_counts[c, h, w]
                else:
                    out_val = 1.0  # Single fire
                
                ordering = (in_tensor >= out_val)
            
            result.append(ordering)
        
        return result
    
    def forward(
        self,
        input_spikes: Tensor,
        potentials: Tensor,
        output_spikes: Tensor,
        winners: List[Tuple[int, int, int]],
        winner_fire_time: Optional[float] = None
    ):
        """
        Apply STDP update based on spike timing.
        
        Args:
            input_spikes: Pre-synaptic spikes (T, C, H, W) or (1, C, H, W)
            potentials: Membrane potentials (1, out_C, H', W')
            output_spikes: Post-synaptic spikes (1, out_C, H', W')
            winners: Winner positions [(c, h, w), ...]
            winner_fire_time: Timestep at which winner fired (1-indexed, optional)
        """
        if not winners:
            return
        
        with torch.no_grad():
            # Get pre-post ordering for each winner (using spike timing)
            pairings = self.get_pre_post_ordering(input_spikes, output_spikes, winners, winner_fire_time)
            
            # Build learning rate tensor (same shape as weights)
            lr = torch.zeros_like(self.conv.weight)
            
            for i, winner in enumerate(winners):
                f = winner[0]  # Feature/channel index
                
                # Get learning rates for this feature
                a_plus = self.learning_rate[f][0].to(lr.device)
                a_minus = self.learning_rate[f][1].to(lr.device)
                
                # Apply LTP where pre fires before/at post, LTD otherwise
                lr[f] = torch.where(pairings[i], a_plus, a_minus)
            
            # Apply weight update with optional stabilizer
            if self.use_stabilizer:
                stabilizer = (self.conv.weight - self.lower_bound) * (self.upper_bound - self.conv.weight)
                self.conv.weight += lr * stabilizer
            else:
                self.conv.weight += lr
            
            # Clamp weights to bounds
            self.conv.weight.data.clamp_(self.lower_bound, self.upper_bound)
    
    def update_learning_rate(self, feature: int, ap: float, an: float):
        """Update learning rates for a specific feature."""
        self.learning_rate[feature][0][0] = ap
        self.learning_rate[feature][1][0] = an
    
    def update_all_learning_rate(self, ap: float, an: float):
        """Update learning rates for all features."""
        for feature in range(self.conv.out_channels):
            self.learning_rate[feature][0][0] = ap
            self.learning_rate[feature][1][0] = an


# =============================================================================
# Complete Transform
# =============================================================================

class S1C1Transform:
    """
    Complete S1-C1 transform for Mozafari-style networks.
    
    S1: Simple cells (edge detection with DoG/Gabor)
    C1: Complex cells (pooling for invariance)
    
    Args:
        filter: Filter bank (DoG or Gabor)
        pooling_size: Pooling kernel size
        pooling_stride: Pooling stride
        lateral_inhibition: Optional lateral inhibition
        timesteps: Number of time steps for encoding
    """
    
    def __init__(
        self,
        filter: Filter,
        pooling_size: int = 7,
        pooling_stride: int = 6,
        lateral_inhibition: Optional[LateralIntensityInhibition] = None,
        timesteps: int = 15
    ):
        self.filter = filter
        self.pooling_size = pooling_size
        self.pooling_stride = pooling_stride
        self.lateral_inhibition = lateral_inhibition
        self.timesteps = timesteps
        self.temporal_transform = Intensity2Latency(timesteps)
    
    def __call__(self, image: Tensor) -> Tensor:
        """
        Apply S1-C1 transform.
        
        Args:
            image: Input image tensor (C, H, W) or PIL Image
            
        Returns:
            Spike tensor (T, C, H', W')
        """
        # Ensure tensor format
        if not isinstance(image, Tensor):
            from torchvision.transforms import ToTensor
            image = ToTensor()(image)
        
        # Ensure batch dimension
        if image.dim() == 3:
            image = image.unsqueeze(0)
        
        # Convert to grayscale if needed
        if image.shape[1] == 3:
            image = image.mean(dim=1, keepdim=True)
        
        # S1: Apply filters
        s1 = self.filter(image)
        
        # C1: Pooling
        c1 = pooling(s1, self.pooling_size, self.pooling_stride, 
                     padding=self.pooling_size // 2)
        
        # Lateral inhibition (if provided)
        if self.lateral_inhibition is not None:
            c1 = self.lateral_inhibition(c1)
        
        # Temporal encoding
        temporal = self.temporal_transform(c1)
        
        # Pointwise inhibition (critical!)
        temporal = pointwise_inhibition(temporal)
        
        # Convert to binary
        temporal = temporal.sign()
        
        # Remove batch dimension
        temporal = temporal.squeeze(1)  # (T, C, H, W)
        
        return temporal


# =============================================================================
# Utility class for caching datasets
# =============================================================================

class CacheDataset(torch.utils.data.Dataset):
    """
    Dataset wrapper that caches transformed samples.
    
    Useful for S1C1Transform which is computationally expensive.
    """
    
    def __init__(self, dataset, max_cache_size: int = 60000):
        self.dataset = dataset
        self.max_cache_size = max_cache_size
        self.cache = {}
    
    def __len__(self):
        return len(self.dataset)
    
    def __getitem__(self, idx):
        if idx not in self.cache and len(self.cache) < self.max_cache_size:
            self.cache[idx] = self.dataset[idx]
        
        if idx in self.cache:
            return self.cache[idx]
        else:
            return self.dataset[idx]
