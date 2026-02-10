# User Guide

## Installation

```bash
git clone https://github.com/metr0jw/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA.git
cd Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA

# Automated setup
./setup.sh

# Or manual
cd software/python
pip install -e .
```

## Quick Start

```python
from snn_fpga_accelerator import SNNAccelerator
from snn_fpga_accelerator.spike_encoding import PoissonEncoder
import numpy as np

# Create encoder
encoder = PoissonEncoder(num_neurons=784, duration=0.1, max_rate=100.0)

# Encode input
image = np.random.rand(784)  # 28x28 MNIST
spikes = encoder.encode(image)

# Run inference (simulation mode)
accel = SNNAccelerator(simulation_mode=True)
accel.configure_network({
    'num_neurons': 100,
    'threshold': 1000,
    'tau': 0.9,  # Decay constant
    'refractory_period': 5
})

output = accel.infer(spikes)
prediction = np.argmax(output.sum(axis=1))
```

## Network Configuration

**Hardware Capacity**:
- **RTL (Core Group)**: Up to 2,048 LIF neurons (16 groups × 128, 11-bit global IDs) with dense intra-group and sparse inter-group connectivity
- **HLS (Learning Engine)**: Up to 720 neurons (10-bit neuron IDs) and 518,400 synapses (720×720 weight matrix)

The FPGA bitstream is `outputs/snn_integrated.bit`.

### Basic Setup

```python
config = {
    'num_neurons': 200,     # Max 720 (HLS) / 2048 (RTL)
    'threshold': 1000,
    'tau': 0.9,  # Use tau for intuitive decay control
    'refractory_period': 5,
    'connections': [
        {'src': list(range(784)), 'dst': list(range(200)), 'weights': 'random'}
    ]
}
accel.configure_network(config)
```

### Tau vs Leak Rate

Simply specify `tau` (decay constant), system finds optimal hardware encoding:

| tau | Description |
|-----|-------------|
| 0.50 | Fast decay |
| 0.75 | Moderate-fast |
| 0.90 | Moderate-slow (typical) |
| 0.95 | Slow decay |

<details>
<summary>Advanced: Manual leak_rate encoding</summary>

```python
# leak_rate encoding:
# bits [2:0]: shift1 (1-7)
# bits [7:3]: shift2 (0=disabled)
# tau = 1 - 2^(-shift1) - 2^(-shift2)

config['leak_rate'] = 0x2C  # shift1=4, shift2=5 → tau≈0.906
```
</details>

## Spike Encoding

```python
# Poisson encoding (rate-based)
encoder = PoissonEncoder(num_neurons=784, duration=0.1, max_rate=100.0)
spikes = encoder.encode(image)

# Temporal encoding (first-to-spike)
from snn_fpga_accelerator.spike_encoding import TemporalEncoder
encoder = TemporalEncoder(num_neurons=784, duration=0.1)
spikes = encoder.encode(image)

# Phase encoding
from snn_fpga_accelerator.spike_encoding import PhaseEncoder
encoder = PhaseEncoder(num_neurons=784, duration=0.1, num_phases=8)
spikes = encoder.encode(image)
```

## Learning

### STDP

```python
from snn_fpga_accelerator.learning import STDPLearning

stdp = STDPLearning(
    tau_pre=20.0,   # Pre-synaptic trace decay
    tau_post=20.0,  # Post-synaptic trace decay
    a_plus=0.01,    # LTP magnitude
    a_minus=0.01,   # LTD magnitude
    w_min=0.0,
    w_max=1.0
)

# Train
for image, label in training_data:
    spikes = encoder.encode(image)
    output = accel.infer(spikes)
    weights = stdp.update(spikes, output)
    accel.update_weights(weights)
```

### R-STDP (Reward-Modulated)

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

for image, label in training_data:
    spikes = encoder.encode(image)
    output = accel.infer(spikes)
    
    # Reward based on correctness
    prediction = np.argmax(output.sum(axis=1))
    reward = 1.0 if prediction == label else -1.0
    
    weights = rstdp.update(spikes, output, reward)
    accel.update_weights(weights)
```

## Hardware Deployment

### Load Bitstream

```python
# Deploy to PYNQ-Z2
accel = SNNAccelerator(
    bitstream_path='outputs/snn_integrated.bit',
    simulation_mode=False
)
```

### Copy to Board

```bash
scp outputs/snn_integrated.bit xilinx@192.168.2.99:~/
scp outputs/design_1.hwh xilinx@192.168.2.99:~/snn_integrated.hwh
```

### Run on Board

```python
from pynq import Overlay
import numpy as np

# Load bitstream
ol = Overlay('/home/xilinx/snn_integrated.bit')

# Configure
# ... (see examples/ for full usage)
```

## Simulation vs Hardware

```python
# Simulation mode (software, no FPGA)
sim_accel = SNNAccelerator(simulation_mode=True)

# Hardware mode (FPGA)
hw_accel = SNNAccelerator(
    bitstream_path='snn_integrated.bit',
    simulation_mode=False
)

# Check mode
if accel.is_simulation_mode():
    print("Running in simulation")
```

Use simulation for:
- Development and testing
- Debugging algorithms
- No hardware available

Use hardware for:
- Production inference
- Performance benchmarking
- Energy-efficient deployment

## Examples

See `examples/` directory:

```bash
# PyTorch MNIST training
python examples/pytorch/mnist_training_example.py

# R-STDP learning
python examples/pytorch/r_stdp_learning_example.py

# Mozafari's deep R-STDP (3-layer)
python examples/pytorch/mozafari_rstdp_faithful.py

# Complete integration
python examples/complete_integration_example.py
```

## Configuration Reference

### Neuron Parameters

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| threshold | int | 1-65535 | 1000 | Spike threshold |
| tau | float | 0.1-0.99 | 0.9 | Decay constant |
| refractory_period | int | 0-255 | 5 | Cycles after spike |
| reset_potential | int | 0-65535 | 0 | Post-spike reset |

### STDP Parameters

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| tau_pre | float | 1-100 | 20.0 | Pre-trace decay (ms) |
| tau_post | float | 1-100 | 20.0 | Post-trace decay (ms) |
| a_plus | float | 0-1 | 0.01 | LTP learning rate |
| a_minus | float | 0-1 | 0.01 | LTD learning rate |
| w_min | float | 0-1 | 0.0 | Min weight |
| w_max | float | 0-1 | 1.0 | Max weight |

## Troubleshooting

**Import error**: Check installation with `pip list | grep snn-fpga`

**Bitstream not found**: Verify path to `.bit` file

**PYNQ connection failed**: Check board IP with `ping 192.168.2.99`

**Timing violations on hardware**: Reduce processing frequency or simplify network

**Memory errors**: Reduce network size or batch size

For more issues, see GitHub issues.

## API Reference

For detailed API documentation, see [api_reference.md](api_reference.md).

For hardware specifications, see [architecture.md](architecture.md).

For development, see [developer_guide.md](developer_guide.md).
