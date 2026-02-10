# Event-Driven SNN Accelerator for FPGA

Energy-efficient spiking neural network accelerator on FPGA with PyTorch integration.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Target**: Xilinx Zynq-7020 (PYNQ-Z2)  
**Tools**: Vivado 2025.2, Python 3.13, PyTorch 2.9  
**Status**: Bitstream ready (`outputs/snn_integrated.bit`)

## Quick Start

```bash
# Setup
git clone https://github.com/metr0jw/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA.git
cd Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA
./setup.sh

# Run example
python examples/pytorch/mnist_training_example.py
```

## Features

- **LIF Neurons**: Fixed-point hardware implementation with shift-based leak
- **AC-Based**: Accumulate-only ops (5x energy reduction vs MAC)
- **STDP/R-STDP**: On-chip learning with per-neuron traces
- **PyTorch Integration**: Direct model conversion
- **Spike Encoders**: Rate, temporal, phase, delta-sigma

## Architecture

```
ARM PS (PyTorch) <--AXI--> FPGA PL (256 LIF neurons + STDP + Router)
```

**Resources** (Integrated build @ 100MHz):
- LUT: 26.7K (50%), FF: 24.3K (23%), BRAM: 16.5 (12%), DSP: 38 (17%)
- Timing: WNS +0.845ns ✅

## Usage

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

For hardware deployment:
```python
# On PYNQ-Z2
from pynq import Overlay
ol = Overlay('snn_integrated.bit')
```

## Build

```bash
# HLS learning engine
cd hardware/hls && ./scripts/build_hls.sh

# Complete system (HLS + RTL)
cd hardware/scripts && ./build_integrated.sh
```

Output: `outputs/snn_integrated.bit`

## Examples

```bash
# MNIST training
python examples/pytorch/mnist_training_example.py

# R-STDP learning
python examples/pytorch/r_stdp_learning_example.py

# Deep R-STDP (3-layer)
python examples/pytorch/mozafari_rstdp_faithful.py
```

## Documentation

- [User Guide](docs/user_guide.md) - Usage and configuration
- [Developer Guide](docs/developer_guide.md) - Development workflow  
- [API Reference](docs/api_reference.md) - Python API
- [Architecture](docs/architecture.md) - System design

## Recent Changes (2026-02-10)

Fixed 8 critical bugs across all layers:
- RTL: leak_rate encoding, spike timing, parameterization, mu parameter
- HLS: neuron_id width, STDP algorithm alignment
- Python: bit-accurate simulator, 3-layer network

All verification tests pass (RTL ↔ Python bit-match).

## Project Structure

```
hardware/
├── hdl/rtl/      # Verilog RTL (neurons, router, synapses)
├── hls/          # Vitis HLS (learning engine)
└── scripts/      # Build scripts

software/python/  # Python package
examples/         # Usage examples
docs/             # Documentation
outputs/          # Generated bitstreams
```

## Citation

```bibtex
@misc{lee2025snnaccelerator,
  title={Event-Driven Spiking Neural Network Accelerator for FPGA},
  author={Lee, Jiwoon},
  year={2025},
  url={https://github.com/metr0jw/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA}
}
```

## License

MIT License - see [LICENSE](LICENSE)

## Author

Jiwoon Lee (@metr0jw)  
Kwangwoon University, Seoul, South Korea  
jwlee@linux.com

---

For questions or issues, open a GitHub issue or check the documentation.
