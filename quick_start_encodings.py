from software.python.snn_fpga_accelerator.accelerator import SNNAccelerator
from software.python.snn_fpga_accelerator.spike_encoding import PoissonEncoder, TemporalEncoder, RateEncoder
import numpy as np

# Encode input
image = np.random.rand(784)  # 28x28 MNIST

# Create encoder
# Poisson encoding (rate-based)
encoder = PoissonEncoder(num_neurons=784, duration=0.1, max_rate=100.0)
spikes = encoder.encode(image)
print("Poisson ---- \n spikes = ", len(spikes))

# Temporal encoding (first-to-spike)
from software.python.snn_fpga_accelerator.spike_encoding import TemporalEncoder
encoder = TemporalEncoder(num_neurons=784, duration=0.1)
spikes = encoder.encode(image)
print("Temporal ---- \n spikes = ", len(spikes))

# Rate encoding
from software.python.snn_fpga_accelerator.spike_encoding import RateEncoder
encoder = RateEncoder(num_neurons=784, duration=0.1)
spikes = encoder.encode(image)
print("Rate ---- \n spikes = ", len(spikes))


# # Run inference (simulation mode)
accel = SNNAccelerator(simulation_mode=True)
# accel.configure_network({
#     'num_neurons': 10,
#     'threshold': 1000,
#     'tau': 0.9,  # Decay constant
#     'refractory_period': 5,
#     'connections': [
#         {'src': list(range(784)), 'dst': list(range(10)), 'weights': 'random'}
#     ]
# })

# output = accel.infer(spikes)
# prediction = np.argmax(output.sum(axis=1))

accel.initialize([784, 200])                 # 784 inputs -> 200 output neurons, random weights
#accel.configure_network(config)
# Run inference
output = accel.infer(spikes)

print(f"Input shape: {image.shape}")
print(f"Spike shape: {len(spikes)}")
print(f"Output shape: {output.shape}")
print(f"Predicted class: {np.argmax(output)}")

print("✅ Quick start completed successfully!")
