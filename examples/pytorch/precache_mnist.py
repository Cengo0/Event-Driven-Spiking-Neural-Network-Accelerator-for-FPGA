#!/usr/bin/env python3
"""
Pre-cache MNIST transforms for R-STDP training.

This script computes and saves the transformed MNIST data to disk,
so training can load it instantly without recomputing.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'software', 'python'))

import torch
import torch.nn.functional as F
from torchvision import datasets, transforms
from typing import List
import time

import snn_fpga_accelerator as snn
from snn_fpga_accelerator import sf


class FastMNISTTransform:
    """
    Fast S1-C1 transform using CUDA.
    """
    
    def __init__(self, timesteps: int = 15, pooling_size: int = 2, pooling_stride: int = 2, device: str = 'cuda'):
        self.timesteps = timesteps
        self.pooling_size = pooling_size
        self.pooling_stride = pooling_stride
        self.device = device
        
        # Use Gabor filters (4 orientations)
        kernels = [
            snn.GaborKernel(5, 45 + 22.5),
            snn.GaborKernel(5, 90 + 22.5),
            snn.GaborKernel(5, 135 + 22.5),
            snn.GaborKernel(5, 180 + 22.5),
        ]
        
        self.filter = snn.Filter(kernels, padding=2, use_abs=True)
        self.lateral_inhibition = snn.LateralIntensityInhibition([0.15, 0.12, 0.1, 0.07, 0.05])
        self.temporal_transform = snn.Intensity2Latency(timesteps)
        
        # Move filter kernels to GPU
        self.filter.kernels = self.filter.kernels.to(device)
    
    def __call__(self, image: torch.Tensor) -> torch.Tensor:
        # Scale to [0, 255] range
        if image.max() <= 1.0:
            image = image * 255.0
        
        # Move to GPU and add batch dimension
        image = image.to(self.device).unsqueeze(0)
        
        # S1: Apply filters
        s1 = self.filter(image)
        
        # C1: Pooling
        c1 = sf.pooling(s1, self.pooling_size, self.pooling_stride, 
                        padding=self.pooling_size // 2)
        
        # Lateral intensity inhibition
        c1 = self.lateral_inhibition(c1)
        
        # Temporal encoding
        temporal = self.temporal_transform(c1)
        temporal = temporal.squeeze(1)
        
        # Pointwise inhibition
        temporal = sf.pointwise_inhibition(temporal)
        
        # Convert to binary spikes and move to CPU
        return temporal.sign().byte().cpu()


def get_cache_path(digits: List[int], train: bool) -> str:
    """Get cache file path."""
    digits_str = '_'.join(map(str, sorted(digits)))
    split = 'train' if train else 'test'
    cache_dir = './data/cache'
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f'mnist_rstdp_{split}_{digits_str}.pt')


def cache_dataset(digits: List[int], train: bool, device: str = 'cuda'):
    """Cache transformed dataset."""
    cache_path = get_cache_path(digits, train)
    
    print(f"\n{'='*60}")
    print(f"Caching {'training' if train else 'test'} data for digits {digits}")
    print(f"Cache path: {cache_path}")
    print(f"{'='*60}")
    
    # Load raw MNIST
    to_tensor = transforms.ToTensor()
    dataset = datasets.MNIST('./data', train=train, download=True, transform=to_tensor)
    
    # Filter for selected digits
    digit_to_label = {d: i for i, d in enumerate(digits)}
    indices = [i for i in range(len(dataset)) if dataset.targets[i].item() in digits]
    
    print(f"Total samples: {len(indices)}")
    
    # Create transform
    transform = FastMNISTTransform(timesteps=15, device=device)
    
    data_list = []
    target_list = []
    
    start_time = time.time()
    
    for i, idx in enumerate(indices):
        image, target = dataset[idx]
        
        # Transform
        spike_tensor = transform(image)
        
        # Map target
        target_mapped = digit_to_label[target]
        
        data_list.append(spike_tensor)
        target_list.append(target_mapped)
        
        if (i + 1) % 1000 == 0:
            elapsed = time.time() - start_time
            samples_per_sec = (i + 1) / elapsed
            remaining = (len(indices) - i - 1) / samples_per_sec
            print(f"  Processed {i+1}/{len(indices)} samples "
                  f"({samples_per_sec:.1f} samples/sec, ~{remaining:.0f}s remaining)")
    
    targets_tensor = torch.tensor(target_list)
    
    # Save to disk
    torch.save({'data': data_list, 'targets': targets_tensor}, cache_path)
    
    elapsed = time.time() - start_time
    print(f"\nSaved {len(data_list)} samples to {cache_path}")
    print(f"Total time: {elapsed:.1f}s ({len(data_list)/elapsed:.1f} samples/sec)")
    
    return data_list, targets_tensor


def main():
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}")
    
    # Cache for 2-class (digits 0 vs 1)
    print("\n" + "="*60)
    print("Caching 2-class dataset (digits 0 vs 1)")
    print("="*60)
    cache_dataset([0, 1], train=True, device=device)
    cache_dataset([0, 1], train=False, device=device)
    
    # Cache for 10-class (all digits)
    print("\n" + "="*60)
    print("Caching 10-class dataset (all digits)")
    print("="*60)
    cache_dataset(list(range(10)), train=True, device=device)
    cache_dataset(list(range(10)), train=False, device=device)
    
    print("\n" + "="*60)
    print("All caches created successfully!")
    print("="*60)


if __name__ == "__main__":
    main()
