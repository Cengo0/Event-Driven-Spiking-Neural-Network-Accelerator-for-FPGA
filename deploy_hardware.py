import numpy as np
import time
import os
from software.python.snn_fpga_accelerator.accelerator import SNNAccelerator
from software.python.snn_fpga_accelerator.spike_encoding import RateEncoder
from software.python.snn_fpga_accelerator.pytorch_interface import SNNModel, SNNLayer

def load_snn_from_npy(weights_path, bias_path=None):
    """Loads the Mozafari model using strictly NumPy."""
    snn_model = SNNModel(name="mozafari_hardware_numpy")
    
    # Load the raw arrays
    w = np.load(weights_path)
    b = np.load(bias_path) if bias_path and os.path.exists(bias_path) else None
    
    layer = SNNLayer(
        input_size=w.shape[1],  
        output_size=w.shape[0], 
        layer_type="conv2d"     
    )
    layer.set_weights(w, b)
    layer.set_neuron_parameters(threshold=0.005, leak_rate=0.01, refractory_period=3)
    snn_model.add_layer(layer)
    
    return snn_model

def main():
    print("="*60)
    print("🚀 PYNQ-Z2 SNN HARDWARE DEPLOYMENT (NUMPY ONLY)")
    print("="*60)
    
    bitstream = "design_1_wrapper.bit"
    print(f"Loading bitstream: {bitstream}...")
    accelerator = SNNAccelerator(bitstream_path=bitstream, simulation_mode=False)
    
    if not accelerator.connect():
        print("❌ FATAL: Failed to connect to FPGA fabric.")
        return

    try:
        print("Loading Mozafari model weights from .npy...")
        # Update these filenames if you named them differently
        snn_model = load_snn_from_npy("mozafari_weights.npy", "mozafari_bias.npy")
        accelerator.configure_network(snn_model)
        
        input_dim = 900  
        np.random.seed(42)
        input_data = np.random.rand(input_dim) * 0.8 + 0.2
        
        print("Encoding input spikes...")
        encoder = RateEncoder(num_neurons=input_dim, duration=0.1, max_rate=100.0)
        spikes = encoder.encode(input_data)
        
        print("\n⚡ TRIGGER SCA MEASUREMENT NOW ⚡")
        start_time = time.time()
        
        output = accelerator.infer(spikes) 
        
        hw_time = (time.time() - start_time) * 1000
        
        print("\n✅ Hardware Inference Complete")
        print(f"  Input Spikes:  {len(spikes)}")
        print(f"  Output Spikes: {len(output)}")
        print(f"  Exec Time:     {hw_time:.2f} ms")
        if len(output) > 0:
            print(f"  Predicted class: {np.argmax(output)}")
            
    finally:
        accelerator.disconnect()

if __name__ == '__main__':
    main()