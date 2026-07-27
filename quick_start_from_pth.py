"""
Quick Start Example for PYNQ-Z2 SNN Accelerator
Demonstrates dynamically loading a pretrained VGG-16 SNN model from a .pth file.
"""
import numpy as np
from software.python.snn_fpga_accelerator.accelerator import SNNAccelerator
from software.python.snn_fpga_accelerator.spike_encoding import RateEncoder
from software.python.snn_fpga_accelerator.pytorch_interface import SNNModel, SNNLayer

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

def load_snn_from_pth(pth_file_path):
    """Loads a PyTorch .pth file and dynamically converts it into a mapped SNNModel."""
    if not TORCH_AVAILABLE:
        raise RuntimeError("PyTorch is required to load .pth files.")
        
    # Load the state dictionary to the CPU
    state_dict = torch.load(pth_file_path, map_location='cpu')
    
    # Initialize an empty SNN model
    snn_model = SNNModel(name="vgg16_pretrained")
    
    print("\n" + "="*60)
    print("🏗️  BUILDING SNN MODEL FROM .pth FILE")
    print("-" * 60)
    
    # Iterate through all keys to find Conv2D and Linear layers dynamically
    layer_count = 0
    for key, tensor in state_dict.items():
        # We only want to trigger on '.weight' keys
        if not key.endswith('.weight'):
            continue

        shape = tensor.shape
        
        # Filter out BatchNorm weights (which are 1D tensors). 
        # We only want Conv2D (4D) and Fully Connected (2D) weights.
        if len(shape) not in [2, 4]:
            continue
            
        w = tensor.numpy()
        
        # Look for a matching bias for this specific layer
        bias_key = key.replace('.weight', '.bias')
        b = state_dict[bias_key].numpy() if bias_key in state_dict else None

        # Determine layer type and dimensions based on tensor shape
        if len(shape) == 4:
            layer_type = "conv2d"
            in_size = shape[1]   # in_channels
            out_size = shape[0]  # out_channels
        elif len(shape) == 2:
            layer_type = "fully_connected"
            in_size = shape[1]   # in_features
            out_size = shape[0]  # out_features

        # Create the hardware-mapped layer
        layer = SNNLayer(
            input_size=in_size, 
            output_size=out_size, 
            layer_type=layer_type
        )
        layer.set_weights(w, b)
        
        # Apply the calibrated thresholds
        layer.set_neuron_parameters(threshold=0.005, leak_rate=0.01, refractory_period=3)
        
        snn_model.add_layer(layer)
        layer_count += 1
        print(f"  [{layer_count:02d}] Added {layer_type.ljust(15)} from '{key}' (Shape: {shape})")
        
    print("="*60 + "\n")
    return snn_model

def main():
    print("PYNQ-Z2 SNN Accelerator - VGG-16 Loader")
    print("-" * 60)
    
    # Initialize accelerator in simulation mode
    accelerator = SNNAccelerator(simulation_mode=True)
    
    pth_filename = "mozafari_best.pth"  
    
    try:
        snn_model = load_snn_from_pth(pth_filename)
    except FileNotFoundError:
        print(f"❌ ERROR: Could not find '{pth_filename}'. Please ensure the file is in the same directory.")
        return
        
    # Apply the configured model to the accelerator
    accelerator.configure_network(snn_model)
    
    # # -------------------------------------------------------------
    # # INPUT DATA ADJUSTMENT
    # # The first layer 'layer1.0.weight' expects 3 input channels.
    # # If working with CIFAR-10 (3x32x32), the flattened size is 3072.
    # # Ensure this matches your dataset's actual dimensions.
    # # -------------------------------------------------------------
    # input_dim = 3072  # 3 * 32 * 32
    # np.random.seed(42)
    # input_data = np.random.rand(input_dim) * 0.8 + 0.2

    # -------------------------------------------------------------
    # INPUT DATA ADJUSTMENT
    # Mozafari targets MNIST, which is 28x28 grayscale (784 pixels)
    # -------------------------------------------------------------
    input_dim = 784  
    np.random.seed(42)
    input_data = np.random.rand(input_dim) * 0.8 + 0.2
    
    # Encode input
    print("Encoding input data...")
    encoder = RateEncoder(num_neurons=input_dim, duration=0.1, max_rate=100.0)
    spikes = encoder.encode(input_data)
    
    # Run inference
    print("Running inference...")
    output = accelerator.infer(spikes)
    
    print(f"\nResults:")
    print(f"  Input shape: {input_data.shape}")
    print(f"  Number of input spikes: {len(spikes)}")
    print(f"  Output spikes: {len(output)}")
    if len(output) > 0:
        print(f"  Predicted class: {np.argmax(output)}")
    else:
        print("  Predicted class: None (0 output spikes)")

    print("\nExecution completed.")

if __name__ == '__main__':
    main()