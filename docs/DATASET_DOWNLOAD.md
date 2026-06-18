# Dataset Download Guide

This document describes how to download N-MNIST and CIFAR-10 datasets
for SpikePress + SpikeMold EventConvSNN development.

## N-MNIST Dataset

N-MNIST is an event-driven version of MNIST created using a DVS128 sensor.

### Download Instructions

1. Go to the official N-MNIST website:
   https://www.generationmnist.com/

2. Register for access (free for academic use)

3. Download the N-MNIST dataset (zip file, ~2GB)

4. Extract to `data/nmnist/` directory:

```bash
mkdir -p data/nmnist
unzip N-MNIST.zip -d data/nmnist/
```

### Dataset Structure

```
data/nmnist/
├── Train/
│   ├── 0/
│   ├── 1/
│   ├── ...
│   └── 9/
├── Test/
│   ├── 0/
│   ├── 1/
│   └── ...
└── README.md
```

### Usage in SpikePress

Once downloaded, use `scripts/generate_nmnist_traces.py` to generate
EventConvSNN traces from the N-MNIST dataset.

## CIFAR-10 Dataset

CIFAR-10 is a standard computer vision dataset with 60,000 32x32 color images.

### Download Instructions

CIFAR-10 can be downloaded from:
https://www.cs.toronto.edu/~kriz/cifar.html

### Current Status

The CIFAR-10 dataset has been pre-downloaded to:
```
data/cifar10/cifar-10-batches-py/
```

This includes 5 training batches and 1 test batch.

## Trace Generation

After downloading the datasets, generate traces:

```bash
# CIFAR-10 (already downloaded)
rtk python scripts/generate_cifar_traces.py

# N-MNIST (requires manual download first)
rtk python scripts/generate_nmnist_traces.py
```

## References

- N-MNIST: https://www.generationmnist.com/
- CIFAR-10: https://www.cs.toronto.edu/~kriz/cifar.html
- DVS128 Sensor: https://inilabs.com/product/dvs128/
