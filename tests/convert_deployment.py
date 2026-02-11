#!/usr/bin/env python3
"""Convert torch deployment data to npz for PYNQ board."""
import torch
import numpy as np

d = torch.load('data/cache/mnist_fpga_deployment.pt', weights_only=False)
np.savez('data/cache/mnist_fpga_deployment.npz',
    q_weights=d['q_weights'],
    test_imgs=d['test_imgs'],
    test_lbls=d['test_lbls'],
    threshold=np.array(d['threshold']),
    n_output=np.array(d['n_output']),
    decision_map=np.array(d['decision_map']))
print('Saved mnist_fpga_deployment.npz')
print(f'  q_weights: {d["q_weights"].shape}')
print(f'  test_imgs: {d["test_imgs"].shape}')
print(f'  threshold: {d["threshold"]}')
