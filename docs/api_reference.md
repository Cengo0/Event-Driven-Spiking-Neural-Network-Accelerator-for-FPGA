# API Reference

Python API documentation for the SNN FPGA Accelerator.

## Core Classes

### SNNAccelerator

Main interface for the accelerator.

```python
from snn_fpga_accelerator import SNNAccelerator

# Simulation mode
accel = SNNAccelerator(simulation_mode=True)

# Hardware mode
accel = SNNAccelerator(bitstream_path='snn_integrated.bit', simulation_mode=False)
```

#### Methods

**configure_network(config: dict)**

```python
config = {
    'num_neurons': 100,
    'threshold': 1000,
    'tau': 0.9,  # or 'leak_rate': 0x2C
    'refractory_period': 5,
    'connections': [
        {'src': [0, 1, 2], 'dst': [10, 11], 'weights': 'random'}
    ]
}
accel.configure_network(config)
```

**infer(spikes, duration=0.1)**

Run inference.

```python
output_spikes = accel.infer(input_spikes, duration=0.1)
```

**load_weights(weights: np.ndarray)**

Load weight matrix.

```python
weights = np.load('weights.npy')
accel.load_weights(weights)
```

**update_weights(weights: np.ndarray)**

Update weights (for learning).

```python
accel.update_weights(new_weights)
```

**reset()**

Reset neuron states.

```python
accel.reset()
```

## Spike Encoding

### PoissonEncoder

Rate-based encoding.

```python
from snn_fpga_accelerator.spike_encoding import PoissonEncoder

encoder = PoissonEncoder(num_neurons=784, duration=0.1, max_rate=100.0)
spikes = encoder.encode(image_data)
```

### TemporalEncoder

Intensity-to-latency encoding.

```python
from snn_fpga_accelerator.spike_encoding import TemporalEncoder

encoder = TemporalEncoder(num_neurons=784, duration=0.1)
spikes = encoder.encode(image_data)
```

### PhaseEncoder

Phase-based encoding.

```python
from snn_fpga_accelerator.spike_encoding import PhaseEncoder

encoder = PhaseEncoder(num_neurons=784, duration=0.1, num_phases=8)
spikes = encoder.encode(image_data)
```

## Learning Algorithms

### STDPLearning

Spike-timing-dependent plasticity.

```python
from snn_fpga_accelerator.learning import STDPLearning

stdp = STDPLearning(
    tau_pre=20.0,
    tau_post=20.0,
    a_plus=0.01,
    a_minus=0.01,
    w_min=0.0,
    w_max=1.0
)

# Update weights
new_weights = stdp.update(pre_spikes, post_spikes)
```

### RSTDPLearning

Reward-modulated STDP.

```python
from snn_fpga_accelerator.learning import RSTDPLearning

rstdp = RSTDPLearning(
    tau_pre=20.0,
    tau_post=20.0,
    a_plus=0.01,
    a_minus=0.01,
    w_min=0.0,
    w_max=1.0,
    reward_scale=1.0
)

# Update with reward
new_weights = rstdp.update(pre_spikes, post_spikes, reward)
```

## PyTorch Integration

### Model Conversion

Convert PyTorch model to SNN.

```python
import torch
import torch.nn as nn
from snn_fpga_accelerator.pytorch import convert_to_snn

# Define ANN
class ANN(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(784, 128)
        self.fc2 = nn.Linear(128, 10)
        
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        return self.fc2(x)

# Convert to SNN
ann = ANN()
snn = convert_to_snn(ann, neuron_params={'threshold': 1000, 'tau': 0.9})
```

### Training with PyTorch

```python
import torch
import snntorch as snn

# Define SNN
class MySNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(784, 128)
        self.lif1 = snn.Leaky(beta=0.9)
        self.fc2 = nn.Linear(128, 10)
        self.lif2 = snn.Leaky(beta=0.9)
    
    def forward(self, x):
        mem1 = self.lif1.init_leaky()
        mem2 = self.lif2.init_leaky()
        
        spk1, mem1 = self.lif1(self.fc1(x), mem1)
        spk2, mem2 = self.lif2(self.fc2(spk1), mem2)
        return spk2, mem2

# Train
model = MySNN()
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
criterion = torch.nn.CrossEntropyLoss()

for epoch in range(num_epochs):
    for data, target in dataloader:
        optimizer.zero_grad()
        output, _ = model(data)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()

# Deploy to FPGA
from snn_fpga_accelerator.pytorch import export_weights
weights = export_weights(model)
accel.load_weights(weights)
```

## Utilities

### tau_to_leak_rate(tau: float) -> int

Convert tau to hardware leak_rate encoding.

```python
from snn_fpga_accelerator.utils import tau_to_leak_rate

leak_rate = tau_to_leak_rate(0.9)  # Returns 0x2C (shift1=4, shift2=5)
```

### leak_rate_to_tau(leak_rate: int) -> float

Convert hardware leak_rate to tau.

```python
from snn_fpga_accelerator.utils import leak_rate_to_tau

tau = leak_rate_to_tau(0x2C)  # Returns ~0.906
```

### visualize_spikes(spikes, duration=0.1)

Plot spike raster.

```python
from snn_fpga_accelerator.utils import visualize_spikes
import matplotlib.pyplot as plt

visualize_spikes(spikes, duration=0.1)
plt.show()
```

### spike_rate(spikes, duration=0.1)

Calculate spike rates.

```python
from snn_fpga_accelerator.utils import spike_rate

rates = spike_rate(spikes, duration=0.1)
```

## Hardware-Accurate Simulator

Bit-accurate simulation matching RTL/HLS behavior.

### HWAccurateLIFNeuron

```python
from snn_fpga_accelerator.hw_accurate_simulator import HWAccurateLIFNeuron

neuron = HWAccurateLIFNeuron(
    threshold=1000,
    leak_rate=0x2C,  # shift1=4, shift2=5
    refractory_period=5,
    reset_potential=0
)

# Simulate
for weight in input_weights:
    v_mem, spike = neuron.step(weight)
```

### HWAccurateSTDPEngine

```python
from snn_fpga_accelerator.hw_accurate_simulator import HWAccurateSTDPEngine

stdp = HWAccurateSTDPEngine(
    a_plus=4,
    a_minus=3,
    w_min=51,
    w_max=204,
    mu=16  # Q4.4 fixed-point (16 = 1.0)
)

# Update weight
delta_w = stdp.update_weight(pre_spike_time, post_spike_time, current_weight)
```

### verify_lif_neuron()

Run LIF neuron verification tests.

```python
from snn_fpga_accelerator.hw_accurate_simulator import verify_lif_neuron

verify_lif_neuron()  # Runs 3 tests, prints results
```

### verify_stdp_engine()

Run STDP engine verification tests.

```python
from snn_fpga_accelerator.hw_accurate_simulator import verify_stdp_engine

verify_stdp_engine()  # Runs 5 tests, prints results
```

## Configuration

### Neuron Parameters

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| threshold | int | 1-65535 | 1000 | Spike threshold |
| tau | float | 0.1-0.99 | 0.9 | Decay constant |
| leak_rate | int | 0-255 | - | Raw hardware encoding (alternative to tau) |
| refractory_period | int | 0-255 | 5 | Cycles after spike |
| reset_potential | int | 0-65535 | 0 | Post-spike reset |

### STDP Parameters

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| tau_pre | float | 1-100 | 20.0 | Pre-trace decay (ms) |
| tau_post | float | 1-100 | 20.0 | Post-trace decay (ms) |
| a_plus | float | 0-1 | 0.01 | LTP magnitude |
| a_minus | float | 0-1 | 0.01 | LTD magnitude |
| w_min | float | 0-1 | 0.0 | Min weight |
| w_max | float | 0-1 | 1.0 | Max weight |

### Spike Format

Spikes represented as list of (neuron_id, timestamp) tuples:

```python
spikes = [
    (0, 0.001),   # Neuron 0 fires at t=1ms
    (5, 0.003),   # Neuron 5 fires at t=3ms
    (0, 0.010),   # Neuron 0 fires again at t=10ms
]
```

Or as numpy array (neuron_id, timestamp, value):

```python
spikes = np.array([
    [0, 0.001, 1.0],
    [5, 0.003, 1.0],
    [0, 0.010, 1.0]
])
```

## Examples

Complete examples in `examples/` directory:

- `examples/pytorch/mnist_training_example.py` - MNIST classification
- `examples/pytorch/r_stdp_learning_example.py` - R-STDP learning
- `examples/pytorch/mozafari_rstdp_faithful.py` - 3-layer deep network
- `examples/complete_integration_example.py` - Full workflow

## Error Handling

Common exceptions:

```python
from snn_fpga_accelerator.exceptions import (
    SNNConfigError,
    SNNBitstreamError,
    SNNHardwareError
)

try:
    accel = SNNAccelerator(bitstream_path='nonexistent.bit')
except SNNBitstreamError as e:
    print(f"Bitstream error: {e}")

try:
    accel.configure_network({'invalid': 'config'})
except SNNConfigError as e:
    print(f"Config error: {e}")
```

## References

- [User Guide](user_guide.md) - Usage and examples
- [Developer Guide](developer_guide.md) - Development workflow
- [Architecture](architecture.md) - System design
