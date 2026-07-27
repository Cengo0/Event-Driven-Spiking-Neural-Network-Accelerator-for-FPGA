import torch
import numpy as np

# Load the PyTorch dictionary
state_dict = torch.load("mozafari_best.pth", map_location='cpu')

# Extract just the weights and biases for the inference layer
weights = state_dict['s2.weight'].numpy()
np.save("mozafari_weights.npy", weights)

if 's2.bias' in state_dict:
    bias = state_dict['s2.bias'].numpy()
    np.save("mozafari_bias.npy", bias)
    print("Saved weights and bias.")
else:
    print("Saved weights (no bias found).")