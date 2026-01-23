#!/usr/bin/env python3
"""
Mozafari et al. (2018) R-STDP MNIST Classification

Faithful reimplementation of the R-STDP algorithm using the snn_fpga_accelerator library.
This version closely follows the original SpykeTorch implementation.

Key features:
1. DoG (Difference of Gaussian) filters for edge detection
2. Proper intensity-to-latency encoding with pointwise inhibition
3. STDP convolution with winner-take-all and spatial inhibition
4. Adaptive learning rates based on performance
5. R-STDP (Reward/Anti-STDP) for classification

Architecture (Shallow network - MozafariShallow):
    Input (28x28) -> DoG filters (6 channels) -> Local norm -> 
    Intensity2Latency -> Pooling -> STDP Conv (features_per_class * n_classes) -> 
    WTA Decision

Reference:
    Mozafari, M., et al. "First-spike-based visual categorization using 
    reward-modulated STDP." IEEE TNNLS (2018).

Author: Jiwoon Lee (@metr0jw)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'software', 'python'))

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor
import numpy as np
import time
from typing import Optional, Tuple, List, Dict
from torchvision import datasets, transforms
from torch.utils.data import DataLoader

# Import our SpykeTorch-compatible functions
import snn_fpga_accelerator as snn
from snn_fpga_accelerator import sf  # SpykeTorch-like functional module


# =============================================================================
# Mozafari R-STDP Network
# =============================================================================

class MozafariRSTDP(nn.Module):
    """
    Mozafari et al. (2018) R-STDP Network.
    
    Shallow network for few-class classification.
    
    Args:
        input_channels: Number of S1 filter channels (default: 6 for DoG)
        features_per_class: Number of STDP features per class
        number_of_classes: Number of output classes
        kernel_size: S2 (STDP) convolution kernel size
        threshold: Firing threshold for S2 neurons
        stdp_lr: STDP learning rate (a_plus, a_minus)
        anti_stdp_lr: Anti-STDP learning rate (a_plus, a_minus)
        dropout: Dropout rate for features during training
    """
    
    def __init__(
        self,
        input_channels: int = 6,
        features_per_class: int = 10,
        number_of_classes: int = 10,
        kernel_size: Tuple[int, int] = (5, 5),
        threshold: float = 15.0,
        stdp_lr: Tuple[float, float] = (0.004, -0.003),
        anti_stdp_lr: Tuple[float, float] = (-0.004, 0.0005),
        dropout: float = 0.0
    ):
        super().__init__()
        
        self.features_per_class = features_per_class
        self.number_of_classes = number_of_classes
        self.number_of_features = features_per_class * number_of_classes
        self.kernel_size = kernel_size if isinstance(kernel_size, tuple) else (kernel_size, kernel_size)
        self.threshold = threshold
        self.stdp_lr = stdp_lr
        self.anti_stdp_lr = anti_stdp_lr
        
        # Dropout mask
        self.dropout_rate = dropout
        self.dropout_mask = torch.ones(self.number_of_features)
        self.to_be_dropped = torch.tensor([])
        
        # STDP Convolution layer
        self.s2 = snn.STDPConvolution(
            in_channels=input_channels,
            out_channels=self.number_of_features,
            kernel_size=self.kernel_size,
            weight_mean=0.8,
            weight_std=0.02  # SpykeTorch default is 0.02
        )
        
        # STDP and Anti-STDP learning rules
        self.stdp = snn.STDP(self.s2, stdp_lr)
        self.anti_stdp = snn.STDP(self.s2, anti_stdp_lr)
        
        # Decision map: feature index -> class label
        self.decision_map = []
        for i in range(number_of_classes):
            self.decision_map.extend([i] * features_per_class)
        
        # Context for learning
        self.ctx = {
            "input_spikes": None,
            "potentials": None,
            "output_spikes": None,
            "winners": None
        }
    
    def forward(self, x: Tensor) -> int:
        """
        Forward pass through the network.
        
        Uses FIRST-FIRE TIME approach (original SpykeTorch style):
        1. Convolve input at each timestep
        2. Accumulate potentials
        3. Track WHEN each neuron first fires (crosses threshold)
        4. Use earliest-fire winner selection
        5. STDP uses first-fire time for proper pre/post ordering
        
        Args:
            x: Input spike tensor (T, C, H, W) - temporal spike train
            
        Returns:
            Predicted class (-1 if no winner)
        """
        x = x.float()
        T = x.shape[0]
        
        # Track first fire time and accumulated potential
        pot = None
        fire_time = None  # Track when each neuron first fires (T+1 = never)
        
        for t in range(T):
            pot_t = self.s2(x[t:t+1])  # (1, C_out, H', W')
            if pot is None:
                pot = pot_t
            else:
                pot = pot + pot_t
            
            # Check for first fire
            if fire_time is None:
                fire_time = torch.full_like(pot[0], T + 1)  # (C_out, H', W')
            
            # Mark neurons that first crossed threshold at this timestep
            fired_now = (pot[0] >= self.threshold) & (fire_time > t)
            fire_time[fired_now] = t + 1  # 1-indexed (1 = earliest)
        
        # pot is now (1, C_out, H', W') - accumulated over all timesteps
        
        # Apply dropout during training
        if self.training and self.dropout_rate > 0:
            self._apply_feature_dropout(pot)
        
        # Final spike mask (neurons that ever fired)
        spk = (fire_time <= T).float().unsqueeze(0)  # (1, C, H, W)
        
        if pot.dim() == 4:
            pot_3d = pot[0]  # Remove batch dimension
            spk_3d = spk[0]
        else:
            pot_3d = pot
            spk_3d = spk
        
        # Find winner: earliest fire time, then highest potential as tiebreaker
        masked_pot = pot_3d * spk_3d
        if masked_pot.max() > 0:
            C, H, W = pot_3d.shape
            
            # Priority: earliest fire time (smaller = better), then potential
            # Negate fire_time and add scaled potential
            priority = (T + 1 - fire_time) * 1000 + pot_3d * spk_3d
            
            flat_idx = priority.view(-1).argmax().item()
            c = flat_idx // (H * W)
            hw = flat_idx % (H * W)
            h = hw // W
            w = hw % W
            winners = [(c, h, w)]
            winner_fire_time = fire_time[c, h, w].item()
        else:
            winners = []
            winner_fire_time = T + 1
        
        # Determine output class
        output = -1
        if len(winners) > 0:
            output = self.decision_map[winners[0][0]]
        
        # Save context for learning
        if self.training:
            self.ctx["input_spikes"] = x  # Temporal input for STDP
            self.ctx["potentials"] = pot_3d.unsqueeze(0)  # Make 4D
            self.ctx["output_spikes"] = spk  # Single timestep binary
            self.ctx["winners"] = winners
            self.ctx["winner_fire_time"] = winner_fire_time  # NEW: for STDP
        else:
            self.ctx = {k: None for k in self.ctx}
        
        return output
    
    def _apply_feature_dropout(self, pot: Tensor):
        """Apply dropout to feature maps."""
        for idx in self.to_be_dropped:
            pot[:, idx, :, :] = 0
    
    def update_dropout(self):
        """Update dropout mask for next sample."""
        self.dropout_mask = torch.ones(self.number_of_features) * self.dropout_rate
        self.to_be_dropped = torch.bernoulli(self.dropout_mask).nonzero().squeeze(-1)
    
    def update_learning_rates(
        self,
        stdp_ap: float,
        stdp_an: float,
        anti_stdp_ap: float,
        anti_stdp_an: float
    ):
        """Update STDP learning rates (for adaptive learning)."""
        self.stdp.update_all_learning_rate(stdp_ap, stdp_an)
        self.anti_stdp.update_all_learning_rate(anti_stdp_an, anti_stdp_ap)
    
    def reward(self):
        """Apply STDP (reward) update."""
        if self.ctx["winners"]:
            self.stdp(
                self.ctx["input_spikes"],
                self.ctx["potentials"],
                self.ctx["output_spikes"],
                self.ctx["winners"],
                self.ctx.get("winner_fire_time")  # Pass fire time for proper STDP
            )
    
    def punish(self):
        """Apply Anti-STDP (punishment) update."""
        if self.ctx["winners"]:
            self.anti_stdp(
                self.ctx["input_spikes"],
                self.ctx["potentials"],
                self.ctx["output_spikes"],
                self.ctx["winners"],
                self.ctx.get("winner_fire_time")  # Pass fire time for proper STDP
            )


# =============================================================================
# S1-C1 Transform (Preprocessing)
# =============================================================================

class MNISTTransform:
    """
    Complete S1-C1 transform for MNIST.
    
    Uses Gabor filters for edge detection (like original SpykeTorch),
    followed by pooling, lateral inhibition, and intensity-to-latency encoding.
    """
    
    def __init__(
        self,
        timesteps: int = 15,
        pooling_size: int = 2,
        pooling_stride: int = 2,
        use_gabor: bool = True
    ):
        self.timesteps = timesteps
        self.pooling_size = pooling_size
        self.pooling_stride = pooling_stride
        
        if use_gabor:
            # Use Gabor filters like original SpykeTorch (4 orientations)
            kernels = [
                snn.GaborKernel(5, 45 + 22.5),   # ~67.5 degrees
                snn.GaborKernel(5, 90 + 22.5),   # ~112.5 degrees
                snn.GaborKernel(5, 135 + 22.5),  # ~157.5 degrees
                snn.GaborKernel(5, 180 + 22.5),  # ~202.5 degrees
            ]
            self.num_channels = 4
        else:
            # DoG filter bank (6 filters)
            kernels = [
                snn.DoGKernel(3, 3/9, 6/9),    # On-center small
                snn.DoGKernel(3, 6/9, 3/9),    # Off-center small
                snn.DoGKernel(7, 7/9, 14/9),   # On-center medium
                snn.DoGKernel(7, 14/9, 7/9),   # Off-center medium
                snn.DoGKernel(13, 13/9, 26/9), # On-center large
                snn.DoGKernel(13, 26/9, 13/9), # Off-center large
            ]
            self.num_channels = 6
        
        self.filter = snn.Filter(kernels, padding=kernels[0].kernel_size // 2, use_abs=True)
        
        # Lateral intensity inhibition (critical for competitive learning!)
        self.lateral_inhibition = snn.LateralIntensityInhibition([0.15, 0.12, 0.1, 0.07, 0.05])
        
        self.temporal_transform = snn.Intensity2Latency(timesteps)
        
        # For counting (debug)
        self.cnt = 0
    
    def __call__(self, image: Tensor) -> Tensor:
        """
        Apply S1-C1 transform.
        
        Args:
            image: Input image (C, H, W) tensor
            
        Returns:
            Spike tensor (T, num_filters, H', W')
        """
        self.cnt += 1
        
        # Scale to [0, 255] range if needed
        if image.max() <= 1.0:
            image = image * 255.0
        
        # Add batch dimension
        image = image.unsqueeze(0)  # (1, C, H, W)
        
        # S1: Apply filters
        s1 = self.filter(image)
        
        # C1: Pooling (critical for spatial invariance!)
        c1 = sf.pooling(s1, self.pooling_size, self.pooling_stride, 
                        padding=self.pooling_size // 2)
        
        # Lateral intensity inhibition
        c1 = self.lateral_inhibition(c1)
        
        # Temporal encoding
        temporal = self.temporal_transform(c1)  # (T, 1, C, H, W)
        temporal = temporal.squeeze(1)  # (T, C, H, W)
        
        # Pointwise inhibition (critical!)
        temporal = sf.pointwise_inhibition(temporal)
        
        # Convert to binary spikes
        temporal = temporal.sign()
        
        return temporal.byte()


# =============================================================================
# Training Functions
# =============================================================================

def train_epoch(
    network: MozafariRSTDP,
    data: Tensor,
    targets: Tensor,
    device: str = 'cpu'
) -> np.ndarray:
    """
    Train for one epoch.
    
    Args:
        network: MozafariRSTDP network
        data: Batch of spike data (N, T, C, H, W)
        targets: Class labels (N,)
        device: Device to use
        
    Returns:
        Performance array [correct, wrong, silence]
    """
    network.train()
    perf = np.array([0, 0, 0])  # correct, wrong, silence
    
    network.update_dropout()
    
    for i in range(len(data)):
        data_in = data[i].to(device)
        target_in = targets[i].item()
        
        # Forward pass
        prediction = network(data_in)
        
        if prediction != -1:
            # Winner found - learn based on correctness
            if prediction == target_in:
                perf[0] += 1
                network.reward()
            else:
                perf[1] += 1
                network.punish()
        else:
            # No winner (silent) - no learning
            perf[2] += 1
    
    return perf


def test_epoch(
    network: MozafariRSTDP,
    data: Tensor,
    targets: Tensor,
    device: str = 'cpu'
) -> np.ndarray:
    """
    Test for one epoch.
    
    Args:
        network: MozafariRSTDP network
        data: Batch of spike data (N, T, C, H, W)
        targets: Class labels (N,)
        device: Device to use
        
    Returns:
        Performance array [correct, wrong, silence]
    """
    network.eval()
    perf = np.array([0, 0, 0])  # correct, wrong, silence
    
    with torch.no_grad():
        for i in range(len(data)):
            data_in = data[i].to(device)
            target_in = targets[i].item()
            
            prediction = network(data_in)
            
            if prediction != -1:
                if prediction == target_in:
                    perf[0] += 1
                else:
                    perf[1] += 1
            else:
                perf[2] += 1
    
    return perf


# =============================================================================
# Main Training Loop
# =============================================================================

def train_mozafari_network(
    digits: List[int] = list(range(10)),
    features_per_class: int = 10,
    kernel_size: int = 5,
    threshold: float = 15.0,
    max_epochs: int = 400,
    device: str = 'cpu',
    batch_size: int = 1000
):
    """
    Train Mozafari R-STDP network on MNIST.
    
    Args:
        digits: List of digit classes to use
        features_per_class: Features per class
        kernel_size: S2 kernel size
        threshold: S2 firing threshold
        max_epochs: Maximum training epochs
        device: Device to use
        batch_size: Batch size for data loading
    """
    
    n_classes = len(digits)
    digit_to_label = {d: i for i, d in enumerate(digits)}
    
    print("=" * 60)
    print("Mozafari R-STDP Network Training")
    print("=" * 60)
    print(f"Classes: {n_classes} ({digits})")
    print(f"Features per class: {features_per_class}")
    print(f"Kernel size: {kernel_size}x{kernel_size}")
    print(f"Threshold: {threshold}")
    print(f"Max epochs: {max_epochs}")
    print(f"Device: {device}")
    print()
    
    # Create transform
    transform = transforms.Compose([
        transforms.ToTensor(),
        MNISTTransform(timesteps=15)
    ])
    
    # Load MNIST
    print("Loading MNIST dataset...")
    train_dataset = datasets.MNIST('./data', train=True, download=True, transform=transform)
    test_dataset = datasets.MNIST('./data', train=False, download=True, transform=transform)
    
    # Filter for selected digits
    if n_classes < 10:
        train_indices = [i for i in range(len(train_dataset)) 
                        if train_dataset.targets[i].item() in digits]
        test_indices = [i for i in range(len(test_dataset)) 
                       if test_dataset.targets[i].item() in digits]
        
        train_dataset = torch.utils.data.Subset(train_dataset, train_indices)
        test_dataset = torch.utils.data.Subset(test_dataset, test_indices)
    
    # Cache datasets for faster loading (saves to disk)
    print("Loading/caching transformed data...")
    train_data, train_targets = cache_dataset(train_dataset, digits, digit_to_label, train=True)
    test_data, test_targets = cache_dataset(test_dataset, digits, digit_to_label, train=False)
    
    print(f"Training samples: {len(train_data)}")
    print(f"Test samples: {len(test_data)}")
    print()
    
    # Create network
    # Determine input size after transform
    sample_input = train_data[0]
    input_channels = sample_input.shape[1]  # (T, C, H, W)
    
    network = MozafariRSTDP(
        input_channels=input_channels,
        features_per_class=features_per_class,
        number_of_classes=n_classes,
        kernel_size=kernel_size,
        threshold=threshold,
        stdp_lr=(0.02, -0.015),       # More aggressive LTP (5x)
        anti_stdp_lr=(-0.005, 0.001), # More aggressive punishment
        dropout=0.0
    ).to(device)
    
    print(f"Network created with {network.number_of_features} features")
    print(f"Input shape: {sample_input.shape}")
    print()
    
    # Initial adaptive learning rates
    apr = network.stdp_lr[0]
    anr = network.stdp_lr[1]
    app = network.anti_stdp_lr[1]
    anp = network.anti_stdp_lr[0]
    
    adaptive_min = 0.2
    adaptive_int = 0.8
    
    # Initial adaptive rates
    apr_adapt = ((1.0 - 1.0 / n_classes) * adaptive_int + adaptive_min) * apr
    anr_adapt = ((1.0 - 1.0 / n_classes) * adaptive_int + adaptive_min) * anr
    app_adapt = ((1.0 / n_classes) * adaptive_int + adaptive_min) * app
    anp_adapt = ((1.0 / n_classes) * adaptive_int + adaptive_min) * anp
    
    # Performance tracking
    best_train = np.array([0, 0, 0, 0], dtype=float)  # correct, wrong, silence, epoch
    best_test = np.array([0, 0, 0, 0], dtype=float)
    
    # Training loop
    print("Training started...")
    print("-" * 60)
    
    for epoch in range(max_epochs):
        start_time = time.time()
        
        # Shuffle training data
        perm = torch.randperm(len(train_data))
        train_data_shuffled = [train_data[i] for i in perm]
        train_targets_shuffled = train_targets[perm]
        
        # Train
        perf_train = train_epoch(network, train_data_shuffled, train_targets_shuffled, device)
        perf_train_norm = perf_train / len(train_data)
        
        # Update best train
        if best_train[0] <= perf_train_norm[0]:
            best_train = np.append(perf_train_norm, epoch)
        
        # Test
        perf_test = test_epoch(network, test_data, test_targets, device)
        perf_test_norm = perf_test / len(test_data)
        
        # Update best test
        if best_test[0] <= perf_test_norm[0]:
            best_test = np.append(perf_test_norm, epoch)
            # Save best model
            torch.save(network.state_dict(), "mozafari_best.pth")
        
        elapsed = time.time() - start_time
        
        # Print progress
        if epoch % 10 == 0 or epoch == max_epochs - 1:
            # Debug: show silence ratio and weight stats
            w = network.s2.weight.data
            print(f"Epoch {epoch:3d}/{max_epochs}: "
                  f"Train Acc={perf_train_norm[0]*100:5.1f}% "
                  f"Test Acc={perf_test_norm[0]*100:5.1f}% "
                  f"Best={best_test[0]*100:5.1f}% "
                  f"Silent={perf_train_norm[2]*100:4.1f}% "
                  f"W=[{w.min():.2f},{w.max():.2f}] "
                  f"[{elapsed:.1f}s]")
        
        # Update adaptive learning rates
        apr_adapt = apr * (perf_train_norm[1] * adaptive_int + adaptive_min)
        anr_adapt = anr * (perf_train_norm[1] * adaptive_int + adaptive_min)
        app_adapt = app * (perf_train_norm[0] * adaptive_int + adaptive_min)
        anp_adapt = anp * (perf_train_norm[0] * adaptive_int + adaptive_min)
        network.update_learning_rates(apr_adapt, anr_adapt, app_adapt, anp_adapt)
        
        # Early stopping if accuracy is very high
        if perf_test_norm[0] >= 0.99:
            print(f"Early stopping at epoch {epoch} with {perf_test_norm[0]*100:.1f}% accuracy")
            break
    
    print("-" * 60)
    print("Training completed!")
    print(f"Best Train: Acc={best_train[0]*100:.1f}% @ epoch {int(best_train[3])}")
    print(f"Best Test:  Acc={best_test[0]*100:.1f}% @ epoch {int(best_test[3])}")
    
    return network, best_test


def get_cache_path(digits: List[int], train: bool) -> str:
    """Get cache file path for given digits and train/test split."""
    digits_str = '_'.join(map(str, sorted(digits)))
    split = 'train' if train else 'test'
    cache_dir = './data/cache'
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f'mnist_rstdp_{split}_{digits_str}.pt')


def cache_dataset(dataset, digits, digit_to_label, train: bool = True, force_recompute: bool = False):
    """Cache transformed dataset to disk for fast loading."""
    cache_path = get_cache_path(digits, train)
    
    # Try to load from cache
    if os.path.exists(cache_path) and not force_recompute:
        print(f"  Loading cached data from {cache_path}...")
        cached = torch.load(cache_path)
        return cached['data'], cached['targets']
    
    # Compute and cache
    print(f"  Computing transforms (will save to {cache_path})...")
    data_list = []
    target_list = []
    
    for i in range(len(dataset)):
        sample, target = dataset[i]
        
        # Convert target if using subset of digits
        if isinstance(target, int):
            target_mapped = digit_to_label.get(target, target)
        else:
            target_mapped = digit_to_label.get(target.item(), target.item())
        
        data_list.append(sample)
        target_list.append(target_mapped)
        
        if (i + 1) % 1000 == 0:
            print(f"    Processed {i+1}/{len(dataset)} samples")
    
    targets_tensor = torch.tensor(target_list)
    
    # Save to disk
    torch.save({'data': data_list, 'targets': targets_tensor}, cache_path)
    print(f"  Saved cache to {cache_path}")
    
    return data_list, targets_tensor


# =============================================================================
# Main
# =============================================================================

def main():
    """Main entry point."""
    torch.manual_seed(42)
    np.random.seed(42)
    
    # Determine device
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}\n")
    
    # Option 1: Simple 2-class classification (fast training, good for testing)
    # Using parameters closer to original SpykeTorch
    print("=" * 60)
    print("2-Class Classification (digits 0 vs 1)")
    print("=" * 60)
    
    network_2class, best_2class = train_mozafari_network(
        digits=[0, 1],
        features_per_class=10,
        kernel_size=5,           # 5x5 kernel for 14x14 feature maps
        threshold=8.0,           # Lower threshold for MNIST (small images)
        max_epochs=100,
        device=device
    )
    
    print(f"\n2-Class Final Accuracy: {best_2class[0]*100:.1f}%")
    
    # Option 2: Full 10-class classification (slower, more challenging)
    print("\n" + "=" * 60)
    print("10-Class Classification (all digits)")
    print("=" * 60)
    
    network_10class, best_10class = train_mozafari_network(
        digits=list(range(10)),
        features_per_class=20,
        kernel_size=5,
        threshold=20.0,
        max_epochs=200,
        device=device
    )
    
    print(f"\n10-Class Final Accuracy: {best_10class[0]*100:.1f}%")


if __name__ == "__main__":
    main()
