import numpy as np
import time
import os
from software.python.snn_fpga_accelerator.accelerator import SNNAccelerator
from software.python.snn_fpga_accelerator.spike_encoding import LatencyEncoder
from software.python.snn_fpga_accelerator.pytorch_interface import SNNModel, SNNLayer

MOZAFARI_GABOR_ANGLES = (45.0, 90.0, 135.0, 180.0)


def build_gabor_kernel(kernel_size, theta_deg, sigma=1.0, freq=0.25, gamma=1.0, psi=0.0):
    """Build a small Gabor kernel using NumPy only."""
    center = kernel_size // 2
    coords = np.arange(kernel_size, dtype=np.float32) - center
    y, x = np.meshgrid(coords, coords)

    theta = np.deg2rad(theta_deg)
    x_theta = x * np.cos(theta) + y * np.sin(theta)
    y_theta = -x * np.sin(theta) + y * np.cos(theta)

    gaussian = np.exp(-0.5 * (x_theta**2 + (gamma**2) * y_theta**2) / (sigma**2))
    sinusoidal = np.cos(2 * np.pi * freq * x_theta + psi)
    kernel = gaussian * sinusoidal
    kernel = kernel - kernel.mean()
    norm = np.linalg.norm(kernel)
    return kernel / (norm + 1e-8)


def conv2d_valid(image, kernel, padding=0):
    """2D convolution with zero padding, implemented in NumPy."""
    if padding > 0:
        image = np.pad(image, ((padding, padding), (padding, padding)), mode="constant")

    kernel_h, kernel_w = kernel.shape
    out_h = image.shape[0] - kernel_h + 1
    out_w = image.shape[1] - kernel_w + 1
    output = np.zeros((out_h, out_w), dtype=np.float32)

    for y in range(out_h):
        for x in range(out_w):
            window = image[y : y + kernel_h, x : x + kernel_w]
            output[y, x] = float(np.sum(window * kernel))

    return output


def max_pool2d(image, kernel_size, stride, padding=0):
    """Simple max-pooling helper for a 2D NumPy array."""
    if padding > 0:
        image = np.pad(image, ((padding, padding), (padding, padding)), mode="constant")

    out_h = (image.shape[0] - kernel_size) // stride + 1
    out_w = (image.shape[1] - kernel_size) // stride + 1
    output = np.zeros((out_h, out_w), dtype=np.float32)

    for y in range(out_h):
        for x in range(out_w):
            y0 = y * stride
            x0 = x * stride
            window = image[y0 : y0 + kernel_size, x0 : x0 + kernel_size]
            output[y, x] = float(np.max(window))

    return output


def preprocess_mozafari_image(raw_image, duration=0.1):
    """Convert a raw grayscale image into Mozafari-style spike events."""
    image = np.asarray(raw_image, dtype=np.float32)
    if image.ndim != 2:
        raise ValueError(f"Expected a 2D grayscale image, got shape {image.shape}")

    image_min = float(image.min())
    image_max = float(image.max())
    if image_max > image_min:
        image = (image - image_min) / (image_max - image_min)
    else:
        image = np.zeros_like(image, dtype=np.float32)

    gabor_maps = []
    for angle in MOZAFARI_GABOR_ANGLES:
        kernel = build_gabor_kernel(5, angle)
        response = np.abs(conv2d_valid(image, kernel, padding=2))
        pooled = max_pool2d(response, kernel_size=7, stride=6, padding=3)
        gabor_maps.append(pooled)

    feature_map = np.stack(gabor_maps, axis=0)
    feature_max = float(feature_map.max())
    if feature_max > 0:
        feature_map = feature_map / feature_max

    flat_features = feature_map.reshape(-1)
    encoder = LatencyEncoder(num_neurons=flat_features.size, duration=duration)
    spikes = encoder.encode(flat_features)
    return feature_map, spikes

def load_snn_from_npy(weights_path, bias_path=None):
    """Loads the Mozafari model using strictly NumPy."""
    snn_model = SNNModel(name="mozafari_hardware_numpy")
    
    # Load the raw arrays
    w = np.load(weights_path)
    b = np.load(bias_path) if bias_path and os.path.exists(bias_path) else None

    if w.ndim == 4:
        # Mozafari s2 checkpoint: (out_channels, in_channels, kernel_h, kernel_w)
        layer = SNNLayer(
            input_size=w.shape[1],
            output_size=w.shape[0],
            layer_type="convolutional",
            in_channels=w.shape[1],
            out_channels=w.shape[0],
            kernel_size=(w.shape[2], w.shape[3]),
            stride=(1, 1),
            padding=(0, 0),
        )
    elif w.ndim == 2:
        layer = SNNLayer(
            input_size=w.shape[1],
            output_size=w.shape[0],
            layer_type="fully_connected",
        )
    else:
        raise ValueError(f"Unsupported Mozafari weight tensor shape: {w.shape}")

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

        raw_image_path = "raw_input.npy"
        if os.path.exists(raw_image_path):
            raw_image = np.load(raw_image_path)
            print(f"Loaded raw image from {raw_image_path} with shape {raw_image.shape}")
        else:
            print(
                "No raw_input.npy found, generating a demo grayscale image. "
                "Replace this with your real raw image for meaningful results."
            )
            rng = np.random.default_rng(42)
            raw_image = rng.random((28, 28), dtype=np.float32)

        print("Preprocessing raw image with Mozafari S1/C1 pipeline...")
        feature_map, spikes = preprocess_mozafari_image(raw_image, duration=0.1)
        input_dim = feature_map.size
        print(f"Mozafari feature map shape: {feature_map.shape} -> flattened {input_dim}")
        print(f"Encoded feature spikes: {len(spikes)}")
        
        print("\n⚡ TRIGGER SCA MEASUREMENT NOW ⚡")
        start_time = time.time()
        
        output = accelerator.infer(spikes, return_events = True) 
        
        hw_time = (time.time() - start_time) * 1000
        
        print("\n✅ Hardware Inference Complete")
        print(f"  Input Spikes:  {len(spikes)}")
        print(f"  Output Spikes: {len(output)}")
        print(f"  Exec Time:     {hw_time:.2f} ms")
        if len(output) > 0:
            first = output[0]
            print(f"  First output spike: neuron={first.neuron_id}, ts={first.timestamp:.6f}, weight={first.weight:.3f}")
            
    finally:
        accelerator.disconnect()

if __name__ == '__main__':
    main()