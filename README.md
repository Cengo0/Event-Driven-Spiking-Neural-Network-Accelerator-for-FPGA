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
- **Spike Encoders**: Delta-sigma modulator (on-chip); rate/latency encoding on host PC

## Architecture

```
ARM PS (PyTorch) <--AXI--> FPGA PL (2,048 LIF neurons + STDP + Router)
                              16 Core Groups × 128 neurons, 4-bit weights
```

**Resources** (Integrated build @ 100MHz):
- LUT: 15,042 (28%), FF: 16,003 (15%), BRAM: 113 (81%), DSP: 4 (2%)
- Timing: WNS +0.338ns ✅

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

### Core Group Architecture
- **Hierarchical design**: 16 core groups × 128 LIF neurons = 2,048 total neurons
- **Event Router NG**: Round-robin arbiter with 16 group ports + external source
- **Synaptic Connectivity Table**: Sparse inter-group connections (32K × 17b BRAM)
- **Dense intra-group**: 128×128 × 5b weight matrix per group (4-bit weight + exc/inh)
- **Verified**: 55/55 RTL tests pass, Vivado synthesis clean, Python bit-accurate

### HLS Learning Engine
- **Encoder cleanup**: Only delta-sigma modulator on-chip; other encodings on host PC
- **HLS capacity**: MAX_NEURONS=720, MAX_SYNAPSES=518,400, 4-bit weights
- **Pipelining**: LTD/LTP loops II=1, RSTDP_INNER UNROLL=4
- **Memory**: Weight memory 8 banks, trace arrays factor=4
- **Verified**: C-sim (5/5 PASS), HLS Fmax 125 MHz, Vivado WNS +0.338ns

### Previous Fixes
- RTL: leak_rate encoding, spike timing, parameterization, mu parameter
- HLS: neuron_id width, STDP algorithm alignment
- Python: bit-accurate simulator, 3-layer network

All verification tests pass (RTL ↔ Python bit-match).

## Project Structure

```
hardware/
├── hdl/
│   ├── rtl/          # Verilog RTL
│   │   ├── common/   # FIFO, utilities
│   │   ├── core/     # Core group, event router, connectivity table
│   │   ├── layers/   # Conv1D/2D, pooling
│   │   ├── learning/ # STDP engine
│   │   ├── neurons/  # LIF neuron implementations
│   │   ├── router/   # Legacy spike routing
│   │   ├── synapses/ # Synaptic arrays
│   │   └── top/      # Top-level integration
│   └── tb/           # Testbenches (19 + 2 comprehensive)
├── hls/              # Vitis HLS (learning engine)
└── scripts/          # Build scripts (TCL)

software/python/      # Python package (19 modules)
examples/             # Usage examples
docs/                 # Documentation
outputs/              # Build reports & bitstreams
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
