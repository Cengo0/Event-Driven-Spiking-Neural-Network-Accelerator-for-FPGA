# SNN FPGA Accelerator - Python Package

Python library for building and deploying Spiking Neural Networks on FPGAs.

## Installation

```bash
cd software/python
pip install -e .
```

## Quick Start

```python
from snn_fpga_accelerator import SNNAccelerator
import numpy as np

# Simulation mode
accel = SNNAccelerator(simulation_mode=True)
accel.configure_network({
    'num_neurons': 100,
    'threshold': 1000,
    'tau': 0.9,
    'refractory_period': 5
})

# Run inference
output = accel.infer(input_spikes)
```

## Hardware Deployment

```python
# On PYNQ-Z2
from pynq import Overlay
ol = Overlay('snn_integrated.bit')

# Configure and run
# ... (see examples/)
```

## Features

- **LIF Neurons**: Hardware-optimized Leaky Integrate-and-Fire
- **Spike Encoding**: Poisson, temporal, phase encoders
- **STDP/R-STDP**: On-chip learning
- **PyTorch Integration**: Train SNNs with PyTorch
- **Hardware-Accurate Simulator**: Bit-level accuracy with RTL

## Examples

See `../../examples/pytorch/`:
- `mnist_training_example.py` - MNIST classification
- `r_stdp_learning_example.py` - R-STDP learning
- `mozafari_rstdp_faithful.py` - Deep 3-layer network

## Documentation

Complete API documentation: [../../docs/api_reference.md](../../docs/api_reference.md)

User guide: [../../docs/user_guide.md](../../docs/user_guide.md)

## Package Structure

```
snn_fpga_accelerator/
├── __init__.py
├── accelerator.py              # Main API
├── spike_encoding.py           # Encoders
├── learning.py                 # STDP/R-STDP
├── hw_accurate_simulator.py    # Bit-accurate sim
├── neuron.py                   # Neuron models
├── layer.py                    # SNN layers
└── utils.py
```

## License

MIT License

## Author

Jiwoon Lee (@metr0jw)  
Kwangwoon University
