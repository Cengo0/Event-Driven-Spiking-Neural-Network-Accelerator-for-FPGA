# End-to-End SNN Accelerator Architecture & Execution Manual

---

## Table of Contents
1. [Executive Summary & Architectural Goals](#1-executive-summary--architectural-goals)
2. [End-to-End Workflow & File Ecosystem](#2-end-to-end-workflow--file-ecosystem)
   - [A. Offline Preparation & Calibration](#a-offline-preparation--calibration)
   - [B. Hardware IP Synthesis (Vitis HLS)](#b-hardware-ip-synthesis-vitis-hls)
   - [C. Block Design Integration & Bitstream Generation (Vivado)](#c-block-design-integration--bitstream-generation-vivado)
   - [D. Board Deployment & Execution](#d-board-deployment--execution)
   - [E. Repository Directory Layout](#e-repository-directory-layout)
3. [Deep Differentiations: Fully Connected (FC3) vs. Convolutional (CNN3)](#3-deep-differentiations-fully-connected-fc3-vs-convolutional-cnn3)
   - [The FC3 "Host-Accelerated" Architecture](#the-fc3-host-accelerated-architecture)
   - [The CNN3 "Streaming 100% On-FPGA" Architecture](#the-cnn3-streaming-100-on-fpga-architecture)
   - [Single Universal Bitstream for All FC3 Models](#single-universal-bitstream-for-all-fc3-models)
4. [Model-Specific Build & Execution Guides](#4-model-specific-build--execution-guides)
   - [Model 1: MNIST FC3 Rate Coding (`fc3_T_4_rate_spikes_clean`)](#model-1-mnist-fc3-rate-coding-fc3_t_4_rate_spikes_clean)
   - [Model 2: MNIST FC3 Direct Coding (`fc3_T_4_clean`)](#model-2-mnist-fc3-direct-coding-fc3_t_4_clean)
   - [Model 3: CIFAR-10 FC3 Logits Loss (`cifar_fc3_T_4_rate_logits_clean`)](#model-3-cifar-10-fc3-logits-loss-cifar_fc3_t_4_rate_logits_clean)
   - [Model 4: CIFAR-10 FC3 Spikes Loss (`cifar_fc3_T_4_rate_spikes_clean`)](#model-4-cifar-10-fc3-spikes-loss-cifar_fc3_t_4_rate_spikes_clean)
   - [Model 5: MNIST CNN3 (`cnn3_T_4_clean`)](#model-5-mnist-cnn3-cnn3_t_4_clean)
   - [Model 6: CIFAR-10 CNN3 (`cifar_cnn3_T_4_clean`)](#model-6-cifar-10-cnn3-cifar_cnn3_t_4_clean)
5. [In-Depth Guide to Results JSON Metrics](#5-in-depth-guide-to-results-json-metrics)
   - [Top-Level Metrics & Layer Averages](#top-level-metrics--layer-averages)
   - [Hardware Diagnostics: `neuron_spikes` vs. `router_spikes`](#hardware-diagnostics-neuron_spikes-vs-router_spikes)
   - [Architectural JSON Reporting Differences (FC3 vs. CNN3)](#architectural-json-reporting-differences-fc3-vs-cnn3)
   - [Per-Image Predictions Breakdown](#per-image-predictions-breakdown)
6. [In-Depth Guide to Cycle-Accurate CSV Spike Traces](#6-in-depth-guide-to-cycle-accurate-csv-spike-traces)
   - [CSV Header Specification](#csv-header-specification)
   - [Detailed Field Definitions](#detailed-field-definitions)
   - [Recording Parity: 100.00% in CNN3 vs. 99.92%–99.95% in FC3](#recording-parity-10000-in-cnn3-vs-99929995-in-fc3)
7. [Hardware Trigger Signal (`snn_busy` / Pin Y18) & EM Capture Window](#7-hardware-trigger-signal-snn_busy--pin-y18--em-capture-window)
   - [RTL Definition of `snn_busy`](#rtl-definition-of-snn_busy)
   - [Physical Behavior in FC3 vs. CNN3](#physical-behavior-in-fc3-vs-cnn3)
   - [Scope / SCA Setup Recommendations](#scope--sca-setup-recommendations)
8. [Git Repository Branch Architecture](#8-git-repository-branch-architecture)

---

## 1. Executive Summary & Architectural Goals

The primary objective of this project is to build an **event-driven Spiking Neural Network (SNN) hardware accelerator** on the Xilinx Zynq-7020 SoC (PYNQ-Z2 board) that achieves:
1. **Mathematical Accuracy Parity**: Matches the classification accuracy of deep PyTorch software models across both MNIST and CIFAR-10 datasets.
2. **Cycle-Accurate Temporal Spike Logging**: Records every single spike event across all hardware layers into timestamped, cycle-accurate CSV traces for electromagnetic (EM) side-channel analysis (SCA) and Test Vector Leakage Assessment (TVLA).
3. **Hardware Latency Reduction**: Employs a **Single-Burst AXI DMA S2MM engine** with an End-of-Timestep packet protocol (`0xFFFFFFFF`, `TLAST=1`) and decoupled injection/drain holdoff, eliminating DMA driver round-trip overhead and cutting inference latency by 25% to 50%.
4. **Event-Driven Synaptic Bias Folding**: Solves the fundamental limitation of neuromorphic crossbar hardware—which lacks per-neuron bias registers in RTL—by mathematically folding trained BatchNorm and Linear biases into synaptic weights without sacrificing sparsity.

### Results Snapshot Across All 6 Deployed Models

| Model | Dataset | Topology | PyTorch Float32 | Int8 SW Calibrated | FPGA Hardware Acc | Avg Latency | Recorded / HW Neuron Spikes | Parity |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **MNIST FC3 Rate** | MNIST | $784 \rightarrow 256 \rightarrow 256 \rightarrow 10$ | 98.38% | 97.62% | **97.24%** | 22.42 ms | 3,103,089 / 3,105,431 | 99.92% |
| **MNIST FC3 Clean** | MNIST | $784 \rightarrow 256 \rightarrow 256 \rightarrow 10$ | 98.63% | 98.40% | **98.10%** | 20.99 ms | 2,703,563 / 2,704,974 | 99.95% |
| **CIFAR-10 FC3 Logits** | CIFAR-10 | $3072 \rightarrow 256 \rightarrow 256 \rightarrow 10$ | 55.83% | 51.77% | **50.11%** | 59.92 ms | 5,417,228 / 5,421,323 | 99.92% |
| **CIFAR-10 FC3 Spikes** | CIFAR-10 | $3072 \rightarrow 256 \rightarrow 256 \rightarrow 10$ | 47.90% | 44.89% | **43.71%** | 58.09 ms | 4,849,776 / 4,852,187 | 99.95% |
| **MNIST CNN3** | MNIST | $28\times 28 \rightarrow \text{Conv1} \rightarrow \text{Conv2} \rightarrow 10$ | 98.27% | 97.17% | **97.67%** | 38.48 ms | 30,516,802 / 30,516,802 | 100.00% |
| **CIFAR-10 CNN3** | CIFAR-10 | $32\times 32\times 3 \rightarrow \text{Conv1} \rightarrow \text{Conv2} \rightarrow 10$ | 67.27% | 61.64% | **62.98%** | 61.59 ms | 24,970,461 / 24,970,461 | 100.00% |

---

## 2. End-to-End Workflow & File Ecosystem

The toolflow is structured into five distinct phases, moving from offline training checkpoints on the host PC to synthesized FPGA bitstreams and physical PYNQ board inference:

```
[PyTorch Checkpoint (models/*.pth)]
           │
           ▼
[1. Offline Preparation Script (tests/prepare_*_deployment.py)]
   ├─► Event-Driven Bias Folding & Calibration Sweep
   ├─► Deployment Payload: data/cache/*.npz
   ├─► Diagnostic Bias Report: data/cache/*_bias_report.json
   └─► (CNN Only) C++ Weight Header: hardware/hls/include/cnn3_weights.h
           │
           ▼
[2. Vitis HLS Synthesis (hardware/hls/scripts/build_hls.sh)]
   ├─► Sources: hardware/hls/src/snn_top_hls.cpp
   └─► Export IP: hardware/hls/hls_output/hls/impl/ip/
           │
           ▼
[3. Vivado Integration (hardware/scripts/rebuild_integrated.tcl)]
   ├─► RTL: hardware/hdl/rtl/core/, common/, top/
   └─► Artifacts: outputs_*/snn_core_group_*.{bit, hwh}
           │
           ▼
[4. Transfer to PYNQ-Z2 Board]
   ├─► Bitstream: snn_core_group_*.bit & snn_core_group_*.hwh
   ├─► Deployment Payload: *.npz
   └─► Shell Runner: scripts/run_inference*.sh (calling tests/fpga_*_inference.py)
           │
           ▼
[5. Board Inference & Logging]
   ├─► Summary Metrics: results/*.json
   └─► Cycle-Accurate Temporal Traces: results/*.csv
```

### A. Offline Preparation & Calibration
* **Location**: `tests/prepare_3layer_deployment.py`, `tests/prepare_cifar10_deployment.py`, `tests/prepare_cnn3_deployment.py`, or `tests/prepare_cnn3_cifar10_deployment.py`.
* **Task**:
  1. Inspects the PyTorch checkpoint (`models/*.pth`) for BatchNorm parameters ($\gamma, \beta, \mu, \sigma^2$) and explicit Linear/Conv2d biases.
  2. Folds BatchNorm into weights ($W_{\text{fused}} = W \cdot \frac{\gamma}{\sigma}$, $B_{\text{fused}} = \beta + (b - \mu) \cdot \frac{\gamma}{\sigma}$).
  3. Precomputes upstream spike streams over a calibration subset (500 images for FC3; 1,000 images for CNN3).
  4. Runs a **Joint Calibration Sweep** over bias folding multipliers ($\alpha_2, \alpha_3$), weight scale factors, and hardware thresholds ($V_{th}$).
  5. Validates quantized Int8 performance on the full 10,000-image test set.
* **Outputs**:
  * `.npz` payload file in `data/cache/`: Contains quantized weights, calibrated hardware thresholds, scale factors, and test images/labels.
  * `*_bias_report.json` in `data/cache/`: Detailed diagnostic report on bias provenance, float32 vs. quantized statistics, and accuracy comparisons with and without bias folding.
  * (CNN models only): Auto-generated C++ weight header `hardware/hls/include/cnn3_weights.h` containing `CONV1_WEIGHTS`, `CONV1_BIAS`, `CONV2_WEIGHTS`, and `CONV2_BIAS` compiled directly into the HLS IP.

### B. Hardware IP Synthesis (Vitis HLS)
* **Location**: `hardware/hls/scripts/build_hls.sh`
* **Invocation**: `bash hardware/hls/scripts/build_hls.sh` (utilizes the modern `v++ -c --mode hls` toolchain in Vitis 2025.2+).
* **Sources**: `hardware/hls/src/snn_top_hls.cpp`, `hardware/hls/include/snn_top_hls.h`, `config/generated/snn_params.h`, and (for CNN3) `hardware/hls/include/cnn3_weights.h`.
* **Task**:
  1. Compiles the high-level C++ streaming interface and convolution kernels.
  2. Synthesizes AXI4-Stream slave (`s_axis_spikes`, `s_axis_weights`) and master (`m_axis_spikes`, `m_axis_weights`) interfaces.
  3. Synthesizes AXI4-Lite control interface (`s_axi_control`).
  4. Implements the Single-Burst S2MM drain engine with idle holdoff (`drain_holdoff = 31` in FC3; `cnn_drain_holdoff = 15` and `cnn_eop_holdoff = 3` in CNN3) and `0xFFFFFFFF` (`TLAST=1`) End-of-Timestep sentinel emission.
  5. Implements the 2D streaming convolution engine (Phases 1, 2a, 2, and 3) with on-chip BRAM membrane potentials (for CNN mode).
* **Primary Output**: Packaged Vivado IP catalog block in `hardware/hls/hls_output/hls/impl/ip/` (with fallback/cached copies in `hardware/ip_repo/snn_top_hls_1_0/` or `hardware/ip_repo/snn_top_hls/`).

### C. Block Design Integration & Bitstream Generation (Vivado)
* **Location**: `hardware/scripts/rebuild_integrated.tcl`
* **Invocation**: `vivado -mode batch -source hardware/scripts/rebuild_integrated.tcl`
* **Universal Script Design**: This single script name (`rebuild_integrated.tcl`) is used across all branches. On each branch, it configures the Vivado block design, prioritizes the freshly synthesized HLS IP in `hardware/hls/hls_output/hls/impl/ip`, connects the RTL Core Groups, verifies 100 MHz timing closure, and exports the bitstream and hardware handoff file to the branch's output directory.
* **Sources**:
  * `hardware/hdl/rtl/core/core_group.v`: Time-multiplexed LIF neuron core groups with local synaptic BRAMs, 8-bit `spike_flag_mem` bitmap, and round-robin output spike scanner.
  * `hardware/hdl/rtl/core/event_router_ng.v`: Central round-robin inter-group spike routing hub with fanout sequencer.
  * `hardware/hdl/rtl/core/synaptic_connectivity_table.v`: Dual-port BRAM crossbar table storing inter-group routing destinations and weights (8-bit source neuron and 8-bit fanout addressing).
  * `hardware/hdl/rtl/top/snn_core_group_top.v`: Top-level wrapper instantiating the Zynq PS block design, Core Groups, output spike FIFO (`SPIKE_OUT_FIFO_DEPTH = 2048` in FC3; `4096` in CNN3), active 100 MHz cycle counter (`rtl_spike_cycle_cnt`), and Pin Y18 trigger (`snn_busy`).
* **Outputs**:
  * `outputs_v2/snn_core_group_v2.bit` and `.hwh` (for all 4 FC3 models on `main`)
  * `outputs_v3/snn_core_group_v3.bit` and `.hwh` (for MNIST CNN3 on `conv`)
  * `outputs_conv_cifar10/snn_core_group_conv_cifar10.bit` and `.hwh` (for CIFAR-10 CNN3 on `conv_cifar10`)

### D. Board Deployment & Execution
* **Location**: Board runner shell scripts in `scripts/`:
  * `scripts/run_inference.sh` (for all 4 FC3 models, calling `fpga_3layer_inference.py`)
  * `scripts/run_inference_cnn.sh` (for MNIST CNN3, calling `fpga_cnn3_inference.py`)
  * `scripts/run_inference_cnn_cifar10.sh` (for CIFAR-10 CNN3, calling `fpga_cnn3_cifar10_inference.py`)
* **Execution Flow & Environment Preservation**:
  * Each runner script executes `sudo -E env PATH=$PATH PYTHONPATH=$PYTHONPATH python3 fpga_*_inference.py "$@"`.
  * **Why this wrapper is used**:
    1. **Root Privileges**: Accessing `/dev/mem`, AXI DMA physical buffers, and PYNQ programmable logic (PL) overlay downloading requires root (`sudo`).
    2. **Environment Preservation**: `sudo -E env PATH=$PATH PYTHONPATH=$PYTHONPATH` preserves the PYNQ virtual environment and library paths under root.
    3. **Argument Forwarding**: All CLI arguments passed to the `.sh` script (`--bitstream`, `--data`, `--samples`, `--timesteps`, `--output-json`, `--output-spikes-csv`, etc.) are forwarded directly to the Python script via `"$@"`.
* **Tasks Executed on Board**:
  1. Programs the PL with the `.bit` and `.hwh` files.
  2. Uploads the Int8 connectivity table weights via AXI-Lite MMIO (`upload_network_weights`).
  3. Configures hardware threshold registers (`CFG_THRESHOLD` at `0x10` and HLS register `0x18`).
  4. Performs a fast zero-state hardware reset (`reset_hardware_state`: 100% leak sweep `0x0009` for 1,600–2,000 cycles) before each image so all BRAM membrane potentials and diagnostic counters start cleanly at zero.
  5. Streams spikes (FC3) or Q8.8 fixed-point pixel frames (CNN3) per timestep over AXI DMA and captures the single S2MM burst terminated by `0xFFFFFFFF`.
  6. Streams decoded cycle-accurate spike events directly to disk (`results/*.csv`) and writes final metrics and per-image predictions to JSON (`results/*.json`).

### E. Repository Directory Layout

```
├── config/
│   ├── snn_params.yaml              # Architecture configuration (groups, neurons, bit widths)
│   └── generated/                   # Auto-generated C/Verilog headers (snn_params.h, snn_params.vh)
├── data/
│   └── cache/                       # Generated .npz payloads and *_bias_report.json files
├── hardware/
│   ├── constraints/                 # XDC pin constraints (pynq_z2_pins.xdc -> Pin Y18)
│   ├── hdl/rtl/
│   │   ├── common/                  # snn_config_regs.v
│   │   ├── core/                    # core_group.v, event_router_ng.v, synaptic_connectivity_table.v
│   │   └── top/                     # snn_core_group_top.v
│   ├── hls/
│   │   ├── hls_output/              # Synthesized IP export (hls_output/hls/impl/ip/) and reports
│   │   ├── include/                 # HLS headers (snn_top_hls.h) and weight header (cnn3_weights.h)
│   │   ├── scripts/                 # HLS compilation script (build_hls.sh using v++ CLI)
│   │   └── src/                     # C++ sources (snn_top_hls.cpp) and testbenches
│   ├── ip_repo/                     # Fallback/cached packaged IP catalog blocks
│   └── scripts/                     # Universal Vivado rebuild script (rebuild_integrated.tcl)
├── models/                          # Trained PyTorch .pth model checkpoints and training .log files
├── outputs_v2/                      # FC3 bitstream and handoff (snn_core_group_v2.{bit, hwh})
├── outputs_v3/                      # MNIST CNN3 bitstream and handoff (snn_core_group_v3.{bit, hwh})
├── outputs_conv_cifar10/            # CIFAR-10 CNN3 bitstream (snn_core_group_conv_cifar10.{bit, hwh})
├── results/                         # Final inference results (.json) and spike traces (.csv)
├── scripts/                         # Board runner shell scripts (run_inference*.sh)
└── tests/                           # Preparation, calibration, and FPGA inference Python scripts
```

---

## 3. Deep Differentiations: Fully Connected (FC3) vs. Convolutional (CNN3)

### The FC3 "Host-Accelerated" Architecture
* **Topology**: $N_{\text{in}} \rightarrow 256 \rightarrow 256 \rightarrow 10$ ($N_{\text{in}} = 784$ for MNIST, $3072$ for CIFAR-10).
* **Hardware Configuration (`snn_params.yaml` on `main`)**: `NUM_GROUPS = 3`, `NEURONS_PER_GROUP = 256`, `group_sizes = [256, 256, 16]`, `LOCAL_ID_WIDTH = 8`, `GROUP_ID_WIDTH = 2`, `GLOBAL_ID_WIDTH = 10`.
* **Partitioning**:
  * **Layer 1 (ARM Cortex-A9 Host CPU)**: Evaluated in IEEE-754 Float32 on the CPU in ~0.08 ms (`mem1 += W1 * x + b1`). The resulting binary spikes are packetized and streamed over AXI DMA.
  * **Group 0 (FPGA RTL Relay)**: 256 hardwired instant-relay neurons ($V_{th} = 1$). When Layer 1 spikes arrive from DMA, Group 0 fires immediately, forwarding spikes through `event_router_ng`.
  * **Group 1 (FPGA RTL Hidden)**: 256 LIF neurons executing the dense $256 \times 256$ Int8 synaptic matrix.
  * **Group 2 (FPGA RTL Output)**: 10 active LIF class neurons (in a 16-neuron group) executing the $10 \times 256$ Int8 classification matrix.
* **Bias Mechanism**:
  * **Layer 1**: Exact Float32 bias addition (`+ b1_f`) on the ARM CPU every timestep.
  * **Layers 2 & 3**: **Event-Driven Synaptic Bias Folding** ($W_{\text{folded}}[i, j] = W[i, j] + \alpha \cdot b[i]$) embedded into the Int8 synaptic weights of Group 1 and Group 2.

### The CNN3 "Streaming 100% On-FPGA" Architecture
* **Topology**:
  * **MNIST (`conv` branch)**: $28\times 28\times 1 \rightarrow \text{Conv1}(1\rightarrow 8, 3\times 3) \rightarrow \text{AvgPool}(2\times 2) \rightarrow \text{Conv2}(8\rightarrow 16, 3\times 3) \rightarrow \text{SumPool}(2\times 2) \rightarrow \text{Dense}(784 \rightarrow 10)$.
    * Hardware Groups: `NUM_GROUPS = 5`, `group_sizes = [196, 196, 196, 196, 16]` ($4 \times 196 = 784$ Layer 2 relay neurons + 10 output neurons), `LOCAL_ID_WIDTH = 8`, `GROUP_ID_WIDTH = 3`, `GLOBAL_ID_WIDTH = 11`.
  * **CIFAR-10 (`conv_cifar10` branch)**: $32\times 32\times 3 \rightarrow \text{Conv1}(3\rightarrow 8, 3\times 3) \rightarrow \text{AvgPool}(2\times 2) \rightarrow \text{Conv2}(8\rightarrow 16, 3\times 3) \rightarrow \text{SumPool}(2\times 2) \rightarrow \text{Dense}(1024 \rightarrow 10)$.
    * Hardware Groups: `NUM_GROUPS = 5`, `group_sizes = [256, 256, 256, 256, 16]` ($4 \times 256 = 1,024$ Layer 2 relay neurons + 10 output neurons), `LOCAL_ID_WIDTH = 8`, `GROUP_ID_WIDTH = 3`, `GLOBAL_ID_WIDTH = 11`.
* **Partitioning**:
  * **Layer 1 (Conv1) & Layer 2 (Conv2)**: 100% on-FPGA inside the Vitis HLS IP (`snn_top_hls`). Evaluated in streaming phases using on-chip BRAM arrays (`cnn_v_mem` and `cnn_l2_v_mem`).
  * **Layer 2 Relay (RTL Groups 0..3)**: 784 neurons (MNIST) or 1,024 neurons (CIFAR-10) configured with $V_{th} = 1$. They receive Layer 2 spikes from HLS and route 10 synaptic fanouts per neuron through `event_router_ng`.
  * **Layer 3 Class (RTL Group 4)**: 10 LIF neurons executing the final $784 \rightarrow 10$ or $1024 \rightarrow 10$ Int8 classification matrix.
* **3-Tier Hybrid Bias Mechanism**:
  * **Layer 1 (Conv1 in HLS)**: `CONV1_BIAS[8]` is added directly in `ap_fixed<16,8>` (Q8.8 fixed-point) at every pixel and timestep before the $V_{th}=1.0$ check.
  * **Layer 2 (Conv2 in HLS)**: `CONV2_BIAS[16]` (16-bit signed integer) is added directly to the 16-bit membrane potential array `cnn_l2_v_mem` once per timestep in HLS Phase 2a.
  * **Layer 3 (Classifier in RTL Group 4)**: Uses **Event-Driven Synaptic Bias Folding** ($W_{3,\text{folded}}[c, j] = W_3[c, j] + \alpha \cdot b_3[c]$) embedded into the `q_fc_w` connectivity table weights, paired with calibrated `hw_threshold_l3`.

### Single Universal Bitstream for All FC3 Models
A key architectural advantage of the FC3 design is that **one single bitstream (`outputs_v2/snn_core_group_v2.bit` and `.hwh`) accelerates all four Fully Connected models across both MNIST and CIFAR-10**:
* **Why this works**: Dataset input dimensionality differences ($784$ for $28\times 28\times 1$ MNIST vs. $3072$ for $32\times 32\times 3$ CIFAR-10) are absorbed by Layer 1 on the ARM CPU host. Because Layer 1 always projects onto **256 hidden neurons**, the FPGA hardware always receives 256 spike channels mapped to Core Group 0 (`256 -> 256 -> 10`).
* **Benefit**: Switching between any of the 4 FC3 models requires zero FPGA re-synthesis; only the `.npz` payload file changes at runtime.

---

## 4. Model-Specific Build & Execution Guides

---

### Model 1: MNIST FC3 Rate Coding (`fc3_T_4_rate_spikes_clean`)
* **Branch**: `main`
* **PyTorch Model**: `models/fc3_T_4_rate_spikes_clean_l2[0.000500].pth` (Training log: `models/fc3_T_4_rate_spikes_clean_l2[0.000500].log`)
* **Input Normalization**: Raw `[0, 1]` pixel intensities (`rate_gain = 1.0`, calibrated deterministically at expected value; optional `--rate-coding` flag enables stochastic Bernoulli sampling at runtime).
* **Files Used**:
  * Preparation Script: `tests/prepare_3layer_deployment.py`
  * Generated Payload: `data/cache/mnist_3layer_deployment_rate.npz` (`hw_threshold = 162`)
  * Bias Diagnostic Report: `data/cache/mnist_3layer_rate_bias_report.json`
  * Bitstream: `outputs_v2/snn_core_group_v2.bit` & `outputs_v2/snn_core_group_v2.hwh`
  * Board Runner Script: `scripts/run_inference.sh` (calling `tests/fpga_3layer_inference.py`)
  * Result Summary: `results/mnist_inference_results_rate.json`
  * Cycle-Accurate CSV: `results/mnist_fc3_spike_trace_rate.csv`
* **Build & Preparation Commands**:
  ```bash
  # Step 1: Generate deployment payload and bias diagnostic report
  python3 tests/prepare_3layer_deployment.py \
      --model models/fc3_T_4_rate_spikes_clean_l2[0.000500].pth \
      --output data/cache/mnist_3layer_deployment_rate.npz \
      --bias-report data/cache/mnist_3layer_rate_bias_report.json \
      --timesteps 4

  # Step 2: Build HLS IP and Vivado hardware bitstream (shared across all FC3 models)
  bash hardware/hls/scripts/build_hls.sh
  vivado -mode batch -source hardware/scripts/rebuild_integrated.tcl
  ```
* **Run on PYNQ Board**:
  ```bash
  sudo ./scripts/run_inference.sh \
      --bitstream outputs_v2/snn_core_group_v2.bit \
      --data data/cache/mnist_3layer_deployment_rate.npz \
      --samples 10000 \
      --timesteps 4 \
      --output-json results/mnist_inference_results_rate.json \
      --output-spikes-csv results/mnist_fc3_spike_trace_rate.csv
  ```
* **Results**:
  * PyTorch Float32 Accuracy: **98.38%** | Int8 SW Calibrated: **97.62%** (`th = 162`)
  * FPGA Hardware Accuracy: **97.24%** (9,724 / 10,000 correct)
  * Average Latency: **22.42 ms / image**
  * Layer Spike Averages: L1 = `124.20`, L2 = `166.03`, L3 = `20.07` spikes/image
  * Spikes Logged: **3,103,089** (`99.92%` parity with `3,105,431` hardware `neuron_spikes`; `router_spikes = 324,349,439`)

---

### Model 2: MNIST FC3 Direct Coding (`fc3_T_4_clean`)
* **Branch**: `main`
* **PyTorch Model**: `models/fc3_T_4_clean_l2[0.000500].pth` (Training log: `models/fc3_T_4_clean_l2[0.000500].log`)
* **Input Normalization**: Z-Score normalized analog pixel intensity ($\text{mean}=0.1307, \text{std}=0.3081$).
* **Files Used**:
  * Preparation Script: `tests/prepare_3layer_deployment.py`
  * Generated Payload: `data/cache/mnist_3layer_deployment_clean.npz` (`hw_threshold = 410`)
  * Bias Diagnostic Report: `data/cache/mnist_3layer_clean_bias_report.json`
  * Bitstream: `outputs_v2/snn_core_group_v2.bit` & `outputs_v2/snn_core_group_v2.hwh`
  * Board Runner Script: `scripts/run_inference.sh` (calling `tests/fpga_3layer_inference.py`)
  * Result Summary: `results/mnist_inference_results_clean.json`
  * Cycle-Accurate CSV: `results/mnist_fc3_spike_trace_clean.csv`
* **Build & Preparation Commands**:
  ```bash
  python3 tests/prepare_3layer_deployment.py \
      --model models/fc3_T_4_clean_l2[0.000500].pth \
      --output data/cache/mnist_3layer_deployment_clean.npz \
      --bias-report data/cache/mnist_3layer_clean_bias_report.json \
      --timesteps 4
  ```
* **Run on PYNQ Board**:
  ```bash
  sudo ./scripts/run_inference.sh \
      --bitstream outputs_v2/snn_core_group_v2.bit \
      --data data/cache/mnist_3layer_deployment_clean.npz \
      --samples 10000 \
      --timesteps 4 \
      --output-json results/mnist_inference_results_clean.json \
      --output-spikes-csv results/mnist_fc3_spike_trace_clean.csv
  ```
* **Results**:
  * PyTorch Float32 Accuracy: **98.63%** | Int8 SW Calibrated: **98.40%** (`th = 410`)
  * FPGA Hardware Accuracy: **98.10%** (9,810 / 10,000 correct)
  * Average Latency: **20.99 ms / image**
  * Layer Spike Averages: L1 = `79.86`, L2 = `158.70`, L3 = `31.79` spikes/image
  * Spikes Logged: **2,703,563** (`99.95%` parity with `2,704,974` hardware `neuron_spikes`; `router_spikes = 218,530,504`)

---

### Model 3: CIFAR-10 FC3 Logits Loss (`cifar_fc3_T_4_rate_logits_clean`)
* **Branch**: `main`
* **PyTorch Model**: `models/cifar_fc3_T_4_rate_logits_clean_l2[0.000500].pth` (Training log: `models/cifar_fc3_T_4_rate_logits_clean_l2[0.000500].log`)
* **Input Normalization**: Raw `[0, 1]` RGB pixel intensities ($3072 \rightarrow 256 \rightarrow 256 \rightarrow 10$, trained with output logits loss).
* **Files Used**:
  * Preparation Script: `tests/prepare_cifar10_deployment.py`
  * Generated Payload: `data/cache/cifar10_3layer_deployment_logits.npz` (`hw_threshold = 170`)
  * Bias Diagnostic Report: `data/cache/cifar10_3layer_logits_bias_report.json`
  * Bitstream: `outputs_v2/snn_core_group_v2.bit` & `outputs_v2/snn_core_group_v2.hwh`
  * Board Runner Script: `scripts/run_inference.sh` (calling `tests/fpga_3layer_inference.py`)
  * Result Summary: `results/cifar10_inference_results_logits.json`
  * Cycle-Accurate CSV: `results/cifar10_fc3_spike_trace_logits.csv`
* **Build & Preparation Commands**:
  ```bash
  python3 tests/prepare_cifar10_deployment.py \
      --model models/cifar_fc3_T_4_rate_logits_clean_l2[0.000500].pth \
      --output data/cache/cifar10_3layer_deployment_logits.npz \
      --bias-report data/cache/cifar10_3layer_logits_bias_report.json \
      --timesteps 4
  ```
* **Run on PYNQ Board**:
  ```bash
  sudo ./scripts/run_inference.sh \
      --bitstream outputs_v2/snn_core_group_v2.bit \
      --data data/cache/cifar10_3layer_deployment_logits.npz \
      --samples 10000 \
      --timesteps 4 \
      --output-json results/cifar10_inference_results_logits.json \
      --output-spikes-csv results/cifar10_fc3_spike_trace_logits.csv
  ```
* **Results**:
  * PyTorch Float32 Accuracy: **55.83%** | Int8 SW Calibrated: **51.77%** (`th = 170`)
  * FPGA Hardware Accuracy: **50.11%** (5,011 / 10,000 correct)
  * Average Latency: **59.92 ms / image**
  * Layer Spike Averages: L1 = `98.06`, L2 = `343.90`, L3 = `99.76` spikes/image
  * Spikes Logged: **5,417,228** (`99.92%` parity with `5,421,323` hardware `neuron_spikes`; `router_spikes = 281,548,310`)

---

### Model 4: CIFAR-10 FC3 Spikes Loss (`cifar_fc3_T_4_rate_spikes_clean`)
* **Branch**: `main`
* **PyTorch Model**: `models/cifar_fc3_T_4_rate_spikes_clean_l2[0.000500].pth` (Training log: `models/cifar_fc3_T_4_rate_spikes_clean_l2[0.000500].log`)
* **Input Normalization**: Raw `[0, 1]` RGB pixel intensities ($3072 \rightarrow 256 \rightarrow 256 \rightarrow 10$, trained with output spike-count loss).
* **Files Used**:
  * Preparation Script: `tests/prepare_cifar10_deployment.py`
  * Generated Payload: `data/cache/cifar10_3layer_deployment_spikes.npz` (`hw_threshold = 180`)
  * Bias Diagnostic Report: `data/cache/cifar10_3layer_spikes_bias_report.json`
  * Bitstream: `outputs_v2/snn_core_group_v2.bit` & `outputs_v2/snn_core_group_v2.hwh`
  * Board Runner Script: `scripts/run_inference.sh` (calling `tests/fpga_3layer_inference.py`)
  * Result Summary: `results/cifar10_inference_results_spikes.json`
  * Cycle-Accurate CSV: `results/cifar10_fc3_spike_trace_spikes.csv`
* **Build & Preparation Commands**:
  ```bash
  python3 tests/prepare_cifar10_deployment.py \
      --model models/cifar_fc3_T_4_rate_spikes_clean_l2[0.000500].pth \
      --output data/cache/cifar10_3layer_deployment_spikes.npz \
      --bias-report data/cache/cifar10_3layer_spikes_bias_report.json \
      --timesteps 4
  ```
* **Run on PYNQ Board**:
  ```bash
  sudo ./scripts/run_inference.sh \
      --bitstream outputs_v2/snn_core_group_v2.bit \
      --data data/cache/cifar10_3layer_deployment_spikes.npz \
      --samples 10000 \
      --timesteps 4 \
      --output-json results/cifar10_inference_results_spikes.json \
      --output-spikes-csv results/cifar10_fc3_spike_trace_spikes.csv
  ```
* **Results**:
  * PyTorch Float32 Accuracy: **47.90%** | Int8 SW Calibrated: **44.89%** (`th = 180`)
  * FPGA Hardware Accuracy: **43.71%** (4,371 / 10,000 correct)
  * Average Latency: **58.09 ms / image**
  * Layer Spike Averages: L1 = `107.35`, L2 = `353.73`, L3 = `23.89` spikes/image
  * Spikes Logged: **4,849,776** (`99.95%` parity with `4,852,187` hardware `neuron_spikes`; `router_spikes = 295,557,008`)

---

### Model 5: MNIST CNN3 (`cnn3_T_4_clean`)
* **Branch**: `conv`
* **PyTorch Model**: `models/cnn3_T_4_clean_l2[0.000500].pth` (Training log: `models/cnn3_T_4_clean_l2[0.000500].log`)
* **Topology**: $28\times 28\times 1 \rightarrow \text{Conv1}(8) \rightarrow \text{AvgPool} \rightarrow \text{Conv2}(16) \rightarrow \text{SumPool} \rightarrow \text{Dense}(784 \rightarrow 10)$, Z-Score normalized ($\text{mean}=0.1307, \text{std}=0.3081$).
* **Files Used**:
  * Preparation Script: `tests/prepare_cnn3_deployment.py`
  * Exported HLS Weight Header: `hardware/hls/include/cnn3_weights.h`
  * Generated Payload: `data/cache/mnist_cnn3_deployment.npz` (`hw_threshold_l2 = 159`, `hw_threshold_l3 = 2800`)
  * Bias Diagnostic Report: `data/cache/mnist_cnn3_bias_report.json`
  * Bitstream: `outputs_v3/snn_core_group_v3.bit` & `outputs_v3/snn_core_group_v3.hwh`
  * Board Runner Script: `scripts/run_inference_cnn.sh` (calling `tests/fpga_cnn3_inference.py`)
  * Result Summary: `results/mnist_cnn3_inference_results.json`
  * Cycle-Accurate CSV: `results/mnist_cnn3_spike_trace.csv`
* **Build & Preparation Commands**:
  ```bash
  # Step 1: Export quantized CNN weights to cnn3_weights.h & generate .npz payload
  python3 tests/prepare_cnn3_deployment.py \
      --model models/cnn3_T_4_clean_l2[0.000500].pth \
      --output data/cache/mnist_cnn3_deployment.npz \
      --bias-report data/cache/mnist_cnn3_bias_report.json \
      --hls-header hardware/hls/include/cnn3_weights.h \
      --timesteps 4

  # Step 2: Synthesize HLS IP and rebuild Vivado bitstream
  bash hardware/hls/scripts/build_hls.sh
  vivado -mode batch -source hardware/scripts/rebuild_integrated.tcl
  ```
* **Run on PYNQ Board**:
  ```bash
  sudo ./scripts/run_inference_cnn.sh \
      --bitstream outputs_v3/snn_core_group_v3.bit \
      --data data/cache/mnist_cnn3_deployment.npz \
      --samples 10000 \
      --timesteps 4 \
      --output-json results/mnist_cnn3_inference_results.json \
      --output-spikes-csv results/mnist_cnn3_spike_trace.csv
  ```
* **Results**:
  * PyTorch Float32 Accuracy: **98.27%** | Int8 SW Calibrated: **97.17%** (`th_l2 = 159`, `th_l3 = 2800`)
  * FPGA Hardware Accuracy: **97.67%** (9,767 / 10,000 correct)
  * Average Latency: **38.48 ms / image**
  * Layer Spike Averages: L3 = `7.87` spikes/image (~`3,043.8` L2 relay spikes/image)
  * Spikes Logged: **30,516,802** (`100.00%` exact parity with `30,516,802` hardware `neuron_spikes`; `router_spikes = 329,123,928`)

---

### Model 6: CIFAR-10 CNN3 (`cifar_cnn3_T_4_clean`)
* **Branch**: `conv_cifar10`
* **PyTorch Model**: `models/cifar_cnn3_T_4_clean_l2[0.000500].pth` (Training log: `models/cifar_cnn3_T_4_clean_l2[0.000500].log`)
* **Topology**: $32\times 32\times 3 \rightarrow \text{Conv1}(8) \rightarrow \text{AvgPool} \rightarrow \text{Conv2}(16) \rightarrow \text{SumPool} \rightarrow \text{Dense}(1024 \rightarrow 10)$, Z-Score normalized ($\text{mean}=(0.4914, 0.4822, 0.4465), \text{std}=(0.2023, 0.1994, 0.2010)$).
* **Files Used**:
  * Preparation Script: `tests/prepare_cnn3_cifar10_deployment.py`
  * Exported HLS Weight Header: `hardware/hls/include/cnn3_weights.h`
  * Generated Payload: `data/cache/cifar10_cnn3_deployment.npz` (`hw_threshold_l2 = 117`, `hw_threshold_l3 = 3400`)
  * Bias Diagnostic Report: `data/cache/cifar10_cnn3_bias_report.json`
  * Bitstream: `outputs_conv_cifar10/snn_core_group_conv_cifar10.bit` & `outputs_conv_cifar10/snn_core_group_conv_cifar10.hwh`
  * Board Runner Script: `scripts/run_inference_cnn_cifar10.sh` (calling `tests/fpga_cnn3_cifar10_inference.py`)
  * Result Summary: `results/cifar10_cnn3_inference_results.json`
  * Cycle-Accurate CSV: `results/cifar10_cnn3_spike_trace.csv`
* **Build & Preparation Commands**:
  ```bash
  # Step 1: Export quantized 3-channel weights to cnn3_weights.h & generate .npz payload
  python3 tests/prepare_cnn3_cifar10_deployment.py \
      --model models/cifar_cnn3_T_4_clean_l2[0.000500].pth \
      --output data/cache/cifar10_cnn3_deployment.npz \
      --bias-report data/cache/cifar10_cnn3_bias_report.json \
      --hls-header hardware/hls/include/cnn3_weights.h \
      --timesteps 4

  # Step 2: Synthesize HLS IP and rebuild Vivado bitstream
  bash hardware/hls/scripts/build_hls.sh
  vivado -mode batch -source hardware/scripts/rebuild_integrated.tcl
  ```
* **Run on PYNQ Board**:
  ```bash
  sudo ./scripts/run_inference_cnn_cifar10.sh \
      --bitstream outputs_conv_cifar10/snn_core_group_conv_cifar10.bit \
      --data data/cache/cifar10_cnn3_deployment.npz \
      --samples 10000 \
      --timesteps 4 \
      --output-json results/cifar10_cnn3_inference_results.json \
      --output-spikes-csv results/cifar10_cnn3_spike_trace.csv
  ```
* **Results**:
  * PyTorch Float32 Accuracy: **67.27%** | Int8 SW Calibrated: **61.64%** (`th_l2 = 117`, `th_l3 = 3400`)
  * FPGA Hardware Accuracy: **62.98%** (6,298 / 10,000 correct)
  * Average Latency: **61.59 ms / image**
  * Layer Spike Averages: L3 = `20.78` spikes/image (~`2,476.3` L2 relay spikes/image)
  * Spikes Logged: **24,970,461** (`100.00%` exact parity with `24,970,461` hardware `neuron_spikes`; `router_spikes = 271,907,271`)

---

## 5. In-Depth Guide to Results JSON Metrics

The JSON results files (saved in `results/`) contain three top-level objects:

```json
{
    "metadata": { ... },
    "metrics": { ... },
    "predictions": [ { ... }, { ... } ]
}
```

### Top-Level Metrics & Layer Averages
* `accuracy_percent`: Overall classification accuracy across the evaluation run (`correct / total * 100`).
* `correct`: Integer count of correctly predicted images.
* `total`: Total images evaluated (`10000`).
* `average_latency_ms`: Mean per-image wall-clock inference time (`lat_ms = (t1 - t0) * 1000.0`), measured on the ARM CPU host across the `T = 4` timesteps of each image. This includes CPU Layer 1 evaluation (for FC3) or pixel buffer preparation (for CNN3), AXI DMA transfers, physical FPGA execution, and S2MM buffer harvesting.
* `avg_l1_spikes_per_image` *(FC3 top-level metrics)*: Average number of Layer 1 spikes recorded from Core Group 0 per image.
* `avg_l2_spikes_per_image` *(FC3 top-level metrics)*: Average number of Layer 2 hidden spikes recorded from Core Group 1 per image.
* `avg_spikes_per_image`: Average number of Layer 3 output class spikes emitted per image (Core Group 2 in FC3; Core Group 4 in CNN3).
* `total_logged_spike_events` *(FC3 top-level metrics)*: Grand total of individual decoded spike packets written to the CSV file across all layers and all 10,000 images.
* `fps` *(CNN3 top-level metrics)*: Overall end-to-end throughput (`n_test / total_time`), which also includes inter-image `reset_hardware_state` and disk I/O time.

### Hardware Diagnostics: `neuron_spikes` vs. `router_spikes`
The `"diagnostics"` block records cumulative readings from the on-chip 32-bit hardware performance registers over AXI-Lite MMIO (`CFG_ROUTER_SPKS` at `0x18` and `CFG_NEURON_SPKS` at `0x1C`):
* **`neuron_spikes` (Neuron Firing Events)**:
  * Incremented in `core_group.v` every time any LIF neuron crosses threshold and fires (`total_spikes <= total_spikes + 1`).
  * Represents the exact physical count of neuron threshold crossings across all RTL Core Groups.
* **`router_spikes` (Synaptic Fanout Deliveries)**:
  * Incremented in `event_router_ng.v` every time a synaptic connection is looked up in `synaptic_connectivity_table.v` and delivered to a destination Core Group (`spike_counter <= spike_counter + 1`).
  * Every time a pre-synaptic neuron fires, `event_router_ng` iterates through all of its non-zero outgoing synapses (`fanout_idx`). For example, in FC3 each Group 0 neuron fans out to up to 256 Group 1 neurons, and in CNN3 each Group 0..3 relay neuron fans out to 10 Group 4 class neurons (plus the incoming external injection event).
  * Consequently, `router_spikes` is roughly $10\times$ to $100\times$ larger (`218M–329M`) than `neuron_spikes` (`2.7M–30.5M`).

### Architectural JSON Reporting Differences (FC3 vs. CNN3)
Both `fpga_3layer_inference.py` (FC3) and `fpga_cnn3_*_inference.py` (CNN3) report the same `"diagnostics"` structure (`router_spikes` and `neuron_spikes`), with a small difference in which summary fields appear in the top-level `"metrics"` block vs. the per-image `"predictions"` list:
* **In FC3 JSON Files (`results/mnist_inference_results_*.json`, `results/cifar10_inference_results_*.json`)**:
  * Top-level `"metrics"` includes `"avg_l1_spikes_per_image"`, `"avg_l2_spikes_per_image"`, `"avg_spikes_per_image"`, `"total_logged_spike_events"`, `"spike_trace_csv"`, and `"diagnostics": {"router_spikes": ..., "neuron_spikes": ...}`.
  * Each entry in `"predictions"` includes `"l1_spikes"`, `"l2_spikes"`, `"spikes"` (10-element class array), `"router_spikes"`, `"neuron_spikes"`, and `"latency_ms"`.
* **In CNN3 JSON Files (`results/mnist_cnn3_inference_results.json`, `results/cifar10_cnn3_inference_results.json`)**:
  * Top-level `"metrics"` includes `"fps"`, `"avg_spikes_per_image"`, and `"diagnostics": {"router_spikes": ..., "neuron_spikes": ...}`.
  * Each entry in `"predictions"` includes `"l2_spikes"`, `"spikes"` (10-element class array), `"router_spikes"`, `"neuron_spikes"`, and `"latency_ms"`. There is no `"l1_spikes"` key because Layer 1 (Conv1) executes entirely inside the HLS streaming block's internal BRAM buffers rather than an RTL Core Group.

### Per-Image Predictions Breakdown
Inside each object in the `"predictions"` list:
* `image_index`: Zero-based index of the test image (`0` to `9999`).
* `true_label`: Ground-truth dataset class label (`0` to `9`).
* `predicted_label`: Hardware prediction, computed as $\text{argmax}(\text{spikes})$.
* `spikes`: 10-element integer list containing the Layer 3 output spike counts for each class neuron (`0` to `9`).
* `l1_spikes` *(FC3 only)*: Count of Layer 1 relay spikes (Group 0) decoded from S2MM DMA packets for this image.
* `l2_spikes`: Count of Layer 2 spikes (Group 1 in FC3; Groups 0..3 in CNN3) decoded from S2MM DMA packets for this image.
* `router_spikes`: Hardware register `CFG_ROUTER_SPKS` (`0x18`) reading for this image.
* `neuron_spikes`: Hardware register `CFG_NEURON_SPKS` (`0x1C`) reading for this image. Note that in CNN3, `neuron_spikes == l2_spikes + sum(spikes)` holds with 100% identity on every image (e.g., `2480 + 20 = 2500` on CIFAR-10 image 0; `2545 + 12 = 2557` on MNIST image 0).
* `latency_ms`: Measured wall-clock inference time (in milliseconds) for this image across all 4 timesteps.

---

## 6. In-Depth Guide to Cycle-Accurate CSV Spike Traces

The CSV files (stored in `results/*.csv` on the host machine) record every spike packet captured from the RTL output FIFO in exact chronological hardware firing order.

### CSV Header Specification
All 6 models (both FC3 and CNN3) share the exact same 13-column CSV header:
```csv
image_id,true_label,predicted_label,timestep,spike_order,clock_cycle,timestep_cycle,hls_timestamp,layer,group_id,local_neuron_id,layer_neuron_id,global_neuron_id
```

### Detailed Field Definitions

| Column Header | Data Type | Description |
| :--- | :---: | :--- |
| `image_id` | Integer | Zero-based index of the evaluation image (`0` to `9999`). |
| `true_label` | Integer | Ground-truth class label (`0` to `9`). |
| `predicted_label` | Integer | Hardware predicted class label (`0` to `9`) after all 4 timesteps complete. |
| `timestep` | Integer | Discrete SNN simulation timestep (`0`, `1`, `2`, or `3` for $T=4$). |
| `spike_order` | Integer | Monotonically increasing sequence index (`0, 1, 2, ...`) of this spike within the current image across all timesteps. |
| `clock_cycle` | Integer | Cumulative active 100 MHz hardware clock cycles elapsed across the image (`cumulative_cycle_offset + timestep_cycle`). |
| `timestep_cycle` | Integer | Active 100 MHz RTL clock cycles elapsed within the current timestep, reconstructed by unwrapping the 8-bit hardware cycle tag (`rtl_spike_cycle_cnt[7:0]`) embedded in the packet's weight field (`rtl_wrap_offset + rtl_lsb`). |
| `hls_timestamp` | Integer | HLS loop iteration counter from the upper bits of the 32-bit AXI-Stream packet (`pkt[31:18]` 14-bit in FC3; `pkt[31:19]` 13-bit in CNN3). |
| `layer` | Integer | Logical network layer: `1` (Input Relay, FC3 only), `2` (Hidden LIF in FC3 / Conv2 Relay in CNN3), or `3` (Output Classification). |
| `group_id` | Integer | Physical RTL Core Group index (`0..2` in FC3; `0..4` in CNN3). |
| `local_neuron_id` | Integer | Neuron index within its physical Core Group (`0..255` in FC3 & CIFAR-10 CNN3; `0..195` in MNIST CNN3 Groups 0..3; `0..9` in the output group). |
| `layer_neuron_id` | Integer | Neuron index within its logical layer (`0..255` for FC3 L1/L2; `0..783` for MNIST CNN3 L2; `0..1023` for CIFAR-10 CNN3 L2; `0..9` for L3). |
| `global_neuron_id` | Integer | Contiguous network-wide neuron ID across all recorded layers:<ul><li>**FC3**: `0..255` (L1), `256..511` (L2), `512..521` (L3)</li><li>**MNIST CNN3**: `0..783` (L2), `784..793` (L3)</li><li>**CIFAR-10 CNN3**: `0..1023` (L2), `1024..1033` (L3)</li></ul> |

### Recording Parity: 100.00% in CNN3 vs. 99.92%–99.95% in FC3
* **In CNN3 (`conv` and `conv_cifar10`)**: The total recorded spikes in the CSV match the on-chip hardware diagnostic counter (`neuron_spikes`) with **exact 100.00% parity** (`30,516,802 / 30,516,802` in MNIST CNN3; `24,970,461 / 24,970,461` in CIFAR-10 CNN3).
* **In FC3 (`main`)**: The total recorded spikes match `neuron_spikes` with **99.92% to 99.95% parity** (~0.05%–0.08% difference, or ~6 spikes per 10,000).
* **Root Cause in RTL (`core_group.v`)**:
  * Inside `hardware/hdl/rtl/core/core_group.v` (lines 181–186), each Core Group buffers newly fired neurons in an 8-bit bitmap array (`spike_flag_mem`, 8 neurons per byte) that is drained by a round-robin output scanner:
    ```verilog
    if (sf_set_pending)
        spike_flag_mem[sf_set_addr] <= spike_flag_mem[sf_set_addr] | (8'd1 << sf_set_bit);
    if (sf_clear_pending)
        spike_flag_mem[sf_clear_addr] <= spike_flag_mem[sf_clear_addr] & sf_clear_mask;
    ```
  * Because `if (sf_clear_pending)` is a separate non-blocking assignment following `if (sf_set_pending)` on the same array, if a neuron in a byte fires (`sf_set_pending = 1`) on the **exact same 100 MHz clock edge** that the output scanner clears a *different* neuron in the **same 8-neuron byte** (`sf_clear_addr == sf_set_addr`), the second statement evaluates using the old byte value and overwrites the newly set bit, even though `total_spikes` (`CFG_NEURON_SPKS`) was incremented.
  * **Why CNN3 has 0 collisions (100.00% parity)**: In CNN3, Groups 0..3 are pure instant-relay groups ($V_{th}=1$) with only 10 outgoing synapses each (to Group 4). HLS waits for `!router_busy` before injecting each Layer 2 spike, and `event_router_ng` finishes all 10 fanouts in ~13 clock cycles before the next spike arrives. Thus Groups 0..3 never experience concurrent set/clear on the same byte, and Group 4 only has 10 neurons firing ~8–21 times per image.
  * **Why FC3 has ~0.06% collisions**: In FC3, each Group 0 relay spike triggers 256 dense synaptic deliveries into Group 1. While Group 1's output scanner is actively clearing fired bits (`sf_clear_pending`), Group 1's LIF pipeline is simultaneously integrating incoming synapses from the next neuron (`sf_set_pending`), causing a same-byte same-cycle collision ~6 times per 10,000 spikes.
  * **Why this is benign**: Any bit overwritten in `spike_flag_mem` was never emitted to `event_router_ng`. Therefore, **100.00% of the spikes that actually exited the Core Groups and were routed through the network (`learn_spike_valid`) are captured in the CSV trace**.

---

## 7. Hardware Trigger Signal (`snn_busy` / Pin Y18) & EM Capture Window

### RTL Definition of `snn_busy`
In `hardware/hdl/rtl/top/snn_core_group_top.v` (lines 605–606) and `hardware/constraints/pynq_z2_pins.xdc`, physical package pin **`Y18`** (`IO_L17P_T2_34`, 3.3V LVCMOS) is wired directly to:
```verilog
assign rtl_snn_busy = router_busy | (grp_busy != {NUM_GROUPS{1'b0}});
assign snn_busy     = rtl_snn_busy;
```
Where in `core_group.v` (line 252):
```verilog
assign group_busy = (state != ST_IDLE) || !fifo_empty || sf_any_pending || sf_set_pending || out_spike_valid;
```
Pin Y18 is strictly an **RTL Core Group & Event Router activity monitor**. It is HIGH (`1`) whenever `event_router_ng` is looking up and delivering synaptic fanouts or whenever any `core_group` has pending input FIFO spikes, active LIF membrane updates, or un-scanned `spike_flag_mem` bits.

### Physical Behavior in FC3 vs. CNN3

```
                  ◄─── Host Python Latency (~20-62 ms / image) ───►
                  
CPU / HLS Prep    RTL Active         CPU /HLS / DMA     RTL Active
(Pin Y18 = 0)   (Pin Y18 = 1)        (Pin Y18 = 0)    (Pin Y18 = 1)
──────────────┐ ┌──────────────┐ ───────────────────┐ ┌──────────────┐
              │ │ (0.1 - 2.5ms)│                    │ │ (0.1 - 2.5ms)│
              └─┘              └────────────────────┘ └─┘              └───
               ▲                ▲
           Timestep 0       Timestep 0            Timestep 1
             Rising          Falling                Rising
```

1. **In FC3 (`main` branch)**:
   * **Layer 1 (ARM CPU Host)**: Computed in software on the ARM Cortex-A9 CPU. The FPGA RTL Core Groups are idle, so **Pin Y18 is LOW (`0`)**.
   * **Layers 1 Relay, 2 & 3 (FPGA RTL Groups 0, 1, 2)**: As soon as AXI DMA streams the Layer 1 spikes into HLS and HLS injects them into Group 0, the RTL cascade across Group 0 $\rightarrow$ Group 1 $\rightarrow$ Group 2 runs. **Pin Y18 is HIGH (`1`) during this entire RTL cascade**, and every spike recorded in the CSV occurs during this window.
2. **In CNN3 (`conv` and `conv_cifar10` branches)**:
   * **Layer 1 (Conv1) & Layer 2 (Conv2 Convolution)**: Computed inside the Vitis HLS IP (`snn_top_hls`) during HLS Phases 1, 2a, and 2. While HLS is computing convolutions in its internal BRAMs, no spikes have been sent to the RTL router yet, so **Pin Y18 is LOW (`0`)**.
   * **Layer 2 Relay & Layer 3 Classification (FPGA RTL Groups 0..3 & Group 4)**: In HLS Phase 3, `snn_top_hls` streams the Layer 2 pooled spikes into RTL Groups 0..3, which route through `event_router_ng` into Group 4. **Pin Y18 pulses HIGH (`1`) during Phase 3**, coinciding with all Layer 2 and Layer 3 spikes logged in the CSV.

### Scope / SCA Setup Recommendations
* **Why CNN Spike Counts (~25M–30M) Are Higher Than FC3 (~2.7M–5.4M)**:
  * In FC3, Layer 1+2+3 has $256 + 256 + 10 = 522$ hardware neurons, emitting ~270–540 spikes per image.
  * In CNN3, the spatial feature maps after Conv2 pooling contain **784 relay neurons** (MNIST $14\times 14$ pooled to $16\times 7\times 7$) or **1,024 relay neurons** (CIFAR-10 $16\times 16$ pooled to $16\times 8\times 8$) with $2\times 2$ SumPool weights of `1..4`, producing ~2,500–3,050 spikes per image (~25M–30.5M over 10,000 images). This is completely normal and expected for spatial convolutional feature maps.
* **Why the Oscilloscope Window Should Be Much Shorter Than `average_latency_ms`**:
  * The JSON `average_latency_ms` (`21–62 ms`) measures the entire Python loop per image (4 timesteps $\times$ [CPU/HLS prep + DMA setup + RTL cascade + S2MM burst harvest]).
  * The actual physical RTL spiking cascade (`Pin Y18 == 1`) takes only **~10,000 to 250,000 clock cycles at 100 MHz**, which corresponds to **0.1 ms to 2.5 ms per timestep**.
* **Recommended Oscilloscope Configuration**:
  * **Trigger Source**: Rising edge of **Pin Y18** (`snn_busy`).
  * **Capture Window**: Set to **`0.5 ms – 2.5 ms`** per timestep trigger (or use **Segmented Memory / Fast-Frame mode** to capture 4 segments per image—one per timestep—while skipping the idle CPU/HLS/DMA intervals where `Pin Y18 = 0`).

---

## 8. Git Repository Branch Architecture

To prevent merge conflicts and maintain clean synthesis workspaces for each hardware topology, the repository is organized across three Git branches:

### 1. `main` Branch (Fully Connected SNNs)
* **Target Architecture**: 3-Layer Fully Connected SNNs ($N_{\text{in}} \rightarrow 256 \rightarrow 256 \rightarrow 10$, 3 Core Groups: `[256, 256, 16]`).
* **Models Supported**:
  * MNIST FC3 Rate Coding (`results/mnist_inference_results_rate.json`, `results/mnist_fc3_spike_trace_rate.csv`)
  * MNIST FC3 Direct Coding (`results/mnist_inference_results_clean.json`, `results/mnist_fc3_spike_trace_clean.csv`)
  * CIFAR-10 FC3 Logits (`results/cifar10_inference_results_logits.json`, `results/cifar10_fc3_spike_trace_logits.csv`)
  * CIFAR-10 FC3 Spikes (`results/cifar10_inference_results_spikes.json`, `results/cifar10_fc3_spike_trace_spikes.csv`)
* **Bitstream Directory**: `outputs_v2/` containing `snn_core_group_v2.bit` & `snn_core_group_v2.hwh` (shared across all 4 FC3 models).
* **Board Runner Script**: `scripts/run_inference.sh`.
* **Core Python Scripts**: `tests/prepare_3layer_deployment.py`, `tests/prepare_cifar10_deployment.py`, `tests/fpga_3layer_inference.py`.

### 2. `conv` Branch (MNIST Convolutional SNN)
* **Target Architecture**: 3-Layer Convolutional SNN for single-channel $28\times 28$ MNIST (5 Core Groups: `[196, 196, 196, 196, 16]`).
* **Models Supported**: MNIST CNN3 (`results/mnist_cnn3_inference_results.json`, `results/mnist_cnn3_spike_trace.csv`).
* **Bitstream Directory**: `outputs_v3/` containing `snn_core_group_v3.bit` & `snn_core_group_v3.hwh`.
* **Board Runner Script**: `scripts/run_inference_cnn.sh`.
* **Core Python & HLS Files**: `tests/prepare_cnn3_deployment.py`, `tests/fpga_cnn3_inference.py`, `hardware/hls/include/cnn3_weights.h`.

### 3. `conv_cifar10` Branch (CIFAR-10 Convolutional SNN)
* **Target Architecture**: 3-Layer Convolutional SNN for 3-channel $32\times 32\times 3$ RGB CIFAR-10 (5 Core Groups: `[256, 256, 256, 256, 16]`).
* **Models Supported**: CIFAR-10 CNN3 (`results/cifar10_cnn3_inference_results.json`, `results/cifar10_cnn3_spike_trace.csv`).
* **Bitstream Directory**: `outputs_conv_cifar10/` containing `snn_core_group_conv_cifar10.bit` & `snn_core_group_conv_cifar10.hwh`.
* **Board Runner Script**: `scripts/run_inference_cnn_cifar10.sh`.
* **Core Python & HLS Files**: `tests/prepare_cnn3_cifar10_deployment.py`, `tests/fpga_cnn3_cifar10_inference.py`, `hardware/hls/include/cnn3_weights.h`.

> [!NOTE]
> When switching between branches, branch-specific build outputs and scripts (such as `outputs_v2/` on `main`, `outputs_v3/` on `conv`, and `outputs_conv_cifar10/` or `scripts/run_inference_cnn_cifar10.sh` on `conv_cifar10`) exist only on their respective branches so each branch remains a self-contained, reproducible synthesis and deployment workspace.
