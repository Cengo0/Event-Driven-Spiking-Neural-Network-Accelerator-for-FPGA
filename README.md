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
ARM PS (PyTorch) <--AXI--> FPGA PL (720 LIF neurons + STDP + Router)
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

### Encoder Cleanup & Neuron Scaling
- **Encoder cleanup**: Removed rate-Poisson, latency, two-neuron encoders from HLS
  - Only delta-sigma modulator retained on-chip; other encodings done on host PC
  - Saves ~2,500 LUTs, 8 DSPs, and encoder-related BRAM
- **Neuron scaling**: MAX_NEURONS 512 → 720, MAX_SYNAPSES 262,144 → 518,400
- **4-bit weights**: WEIGHT_WIDTH 8 → 4 (range -8..+7) for BRAM-efficient scaling
- **ENCODER_LOOP simplified**: PIPELINE II=1 (was UNROLL=2 with switch branches)
- **Verified**: C-sim (5/5 PASS), HLS Fmax 125 MHz, Vivado WNS +0.338ns

### Previous: Pipelining & Scaling Optimization
- **Neuron scaling**: MAX_NEURONS 256 → 512, 10-bit neuron IDs
- **HLS pipelining**: LTD/LTP loops II=1, RSTDP_INNER UNROLL=4
- **Memory partitioning**: Weight memory 8 banks, trace arrays factor=4

### Previous Fixes
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
