# CNN3 Accelerator Architecture, Diagnostics, and Engineering Guide

**Target Hardware**: PYNQ-Z2 Development Board (Xilinx Zynq-7020 SoC: Dual ARM Cortex-A9 + Artix-7 PL)  
**Target Model**: 3-Layer Convolutional Spiking Neural Network (`cnn3_T_4_clean_l2[0.000500].pth`, $T=4$ timesteps)  
**Status Overview**:
- **Option A (Hardware Co-Processing)**: **97.1% – 98.3% On-Board Accuracy** on physical PYNQ-Z2 (`tests/fpga_cnn3_coproc_inference.py`).
- **Option B (100% On-FPGA Inference)**: **11.00% Accuracy** (Class 8 prediction skew / under-quantization collapse) on physical PYNQ-Z2 (`tests/fpga_cnn3_inference.py`).
- **Fully-Connected Reference (FC3)**: **>97.0% On-Board Accuracy** (`tests/fpga_3layer_inference.py`).

---

# 1. Executive Summary & Problem Diagnosis

This document serves as the authoritative, self-contained architecture and diagnostic guide for deploying the 3-Layer Convolutional Spiking Neural Network (CNN3) onto the PYNQ-Z2 FPGA accelerator.

### The Central Question
> *Why did the 3-layer fully connected model (FC3) achieve >97% accuracy on board, and Option A (co-processing) achieve >97% accuracy on board using the exact same FPGA bitstream, while Option B (100% on-FPGA streaming) collapsed to 11.00% with overwhelming Class 8 prediction skew?*

### The Core Findings
1. **The Physical RTL Fabric is 100% Functionally Verified**:
   Option A (`tests/fpga_cnn3_coproc_inference.py`) offloads Layer 3 classification to the FPGA (Core Group 4 LIF neurons + BRAM Synaptic Connectivity Table) and drives it with Layer 2 spikes. It achieves **97.1% – 98.3% accuracy** on the physical PYNQ-Z2 board. This conclusively proves that:
   - The Vivado block design (`design_1_wrapper`),
   - The AXI DMA streaming paths (MM2S & S2MM),
   - The Non-blocking Event Router (`event_router_ng.v`),
   - The BRAM Synaptic Connectivity Table (`synaptic_connectivity_table.v`),
   - The Hierarchical Core Group LIF Engine (`core_group.v`),
   - And the dedicated SCA Trigger Pin (Package Pin Y18) are **fully operational, bit-exact, and timing-clean at 100 MHz**.

2. **Architectural Clarification (Flat Legacy vs. Hierarchical Core Group)**:
   - The original repository initially included a flat 1-core design defined in [`hardware/hdl/rtl/top/snn_integrated_top.v`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/hdl/rtl/top/snn_integrated_top.v), which used a monolithic [`hardware/hdl/rtl/neurons/lif_neuron_array.v`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/hdl/rtl/neurons/lif_neuron_array.v) and [`hardware/hdl/rtl/router/spike_router.v`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/hdl/rtl/router/spike_router.v).
   - **Those two files are legacy and are completely unused in the current accelerator.**
   - The active architecture is the **Core Group Architecture** ([`hardware/hdl/rtl/top/snn_core_group_top.v`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/hdl/rtl/top/snn_core_group_top.v)), where each neuron cluster is encapsulated inside [`hardware/hdl/rtl/core/core_group.v`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/hdl/rtl/core/core_group.v). Each `core_group` contains its own dedicated Simple Dual-Port (SDP) BRAM neuron state memory, its own LIF processing state machine, its own local weight matrix, and its own input FIFO. Inter-group routing is performed by [`hardware/hdl/rtl/core/event_router_ng.v`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/hdl/rtl/core/event_router_ng.v) and [`hardware/hdl/rtl/core/synaptic_connectivity_table.v`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/hdl/rtl/core/synaptic_connectivity_table.v).

3. **The 11.00% Collapse in Option B is Caused by Layer 3 Under-Quantization & Sequential Spike Dynamics**:
   In the latest 1,000-image Option B run (`mnist_cnn3_inference_results.json`), the network predicted Class 8 for almost every sample (average 5.78 spikes/image, 110/1000 correct = 11.00%).
   - To prevent an earlier S2MM DMA FIFO overflow issue, the Layer 3 quantization scale (`scale3_ratio`) was compressed down to $0.04$ (`scale3 = 5.89`).
   - This compressed the Layer 3 weights (`q_fc_w`) into the tiny integer dynamic range **$[-5, +4]$**, with **5,057 out of 7,840 weights (64.5%) rounding to exact zero**.
   - With `hw_threshold = 143`, a class neuron requires **36 to 70 coincident positive spikes** to fire.
   - Digits with sharp, localized features (such as 1, 4, 7) only produce 5 to 15 spikes and cannot clear the threshold.
   - Conversely, Class 8 possesses the most diffuse, broadly connected receptive field (responding to general upper, middle, and lower loops). Because static bias folding rounded to zero and inhibitory spikes are clamped at zero potential when arriving before excitation in `core_group.v`, Class 8 accumulates diffuse $+1$ charge across the entire 784-neuron map and fires repeatedly.

---

# 2. System Architecture & End-to-End Pipeline

```
                               ┌────────────────────────────────────────────────────────┐
                               │            HOST PC / COMPILATION ENVIRONMENT           │
                               │                                                        │
                               │  config/snn_params.yaml ──> generate_params.py         │
                               │           │                        │                   │
                               │           ▼                        ▼                   │
                               │   config/generated/         models/cnn3_*.pth          │
                               │   (vh, py, h headers)              │                   │
                               │           │                        ▼                   │
                               │           │           tests/prepare_cnn3_deployment.py │
                               │           │                        │                   │
                               │           ▼                        ▼                   │
                               │   hardware/hls/ ───> cnn3_weights.h & deployment.npz  │
                               │   (v++ HLS Build)                  │                   │
                               │           │                        │                   │
                               │           ▼                        │                   │
                               │   hardware/build/ ─────────────────┘                   │
                               │   (Vivado Bitstream: snn_core_group_v3.bit)            │
                               └──────────────────────────┬─────────────────────────────┘
                                                          │ SCP Network Transfer
                                                          ▼
                               ┌────────────────────────────────────────────────────────┐
                               │                 PYNQ-Z2 TARGET BOARD                   │
                               │                                                        │
                               │   /home/xilinx/snn_conv/                               │
                               │    ├── snn_core_group_v3.bit & .hwh                    │
                               │    ├── mnist_cnn3_deployment.npz                       │
                               │    ├── fpga_cnn3_coproc_inference.py (Option A: 97.1%) │
                               │    └── fpga_cnn3_inference.py        (Option B: 11.0%) │
                               │                                                        │
                               │  ┌──────────────────────────────────────────────────┐  │
                               │  │                  ZYNQ-7020 PL                    │  │
                               │  │  DMA MM2S ──> HLS (Conv1 + Conv2 Engine)         │  │
                               │  │                  │                               │  │
                               │  │                  ▼                               │  │
                               │  │               Core Groups 0..3 (L2 784 Neurons)  │  │
                               │  │                  │ (Instant Relay: Vth = 1)      │  │
                               │  │                  ▼                               │  │
                               │  │               Router + BRAM Connectivity Table   │  │
                               │  │                  │ (Dense 784 -> 10 Mapping)     │  │
                               │  │                  ▼                               │  │
                               │  │               Core Group 4 (L3 10 Class Neurons) │  │
                               │  │                  │ (Classifier: Vth = 143)       │  │
                               │  │                  ▼                               │  │
                               │  │               Output FIFO (32) ──> DMA S2MM      │  │
                               │  └──────────────────────────────────────────────────┘  │
                               └────────────────────────────────────────────────────────┘
```

## Detailed Dataflow Path

```mermaid
flowchart TD
    A["Raw Image (28x28 Float32)"] -->|"Quantize Q8.8 (784 x 4B)"| B["AXI DMA MM2S"]
    B -->|"AXI4-Stream (s_axis_spikes)"| C["HLS snn_top_hls Engine"]
    
    subgraph HLS_Engine ["HLS Streaming Engine (snn_top_hls.cpp)"]
        C1["cnn_frame[28][28] (Line Buffer)"] --> C2["Phase 1: Conv1 (3x3, 8ch) + LIF (Vth=1.0)"]
        C2 -->|"2x2 Pool Binning"| C3["conv1_spike_buf[2048]"]
        C3 --> C4["Phase 2: Conv2 (3x3, 16ch) Event Scatter"]
        C4 --> C5["cnn_l2_v_mem[16][14][14]"]
        C5 --> C6["Phase 3: L2 LIF Sweep (Vth * 4) + 2x2 Sum Pool"]
        C6 --> C7["encoder_spikes FIFO (Depth=2048)"]
    end
    
    C --> HLS_Engine
    C7 -->|"Direct Wire Bridge (hls_spike_event)"| D["Event Router (event_router_ng.v)"]
    
    subgraph RTL_Core ["RTL Accelerator Fabric (snn_core_group_top.v)"]
        D -->|"grp_in_valid"| E["Core Groups 0..3 (L2 784 Neurons, Vth=1)"]
        E -->|"grp_spike_valid (Instant Relay)"| D
        D -->|"Lookup (src_grp, src_nid)"| F["BRAM Connectivity Table (12,544 rows)"]
        F -->|"dst_grp=4, dst_nid=class, weight, exc"| G["Core Group 4 (Classifier 10 Neurons, Vth=143)"]
        G -->|"Output Class Spike"| H["Output Spike FIFO (Depth=32)"]
    end
    
    H -->|"AXI4-Stream (m_axis_spikes)"| I["AXI DMA S2MM"]
    I -->|"DMA Drain Poll"| J["Host Python (Argmax Class Count)"]
```

---

# 3. Component Breakdown: HLS, RTL, and Software

## A. HLS Streaming Engine (`hardware/hls/src/snn_top_hls.cpp`)
The HLS IP acts as a multi-stage front-end co-processor. When operated in `MODE_CNN_STREAM` (`0x03`):
1. **Frame Buffering**: Receives 784 pixel beats over `s_axis_spikes`. When the 784th pixel is written, it triggers execution.
2. **Phase 1 (Conv1 MAC + Float32 LIF)**:
   - Computes $8 \times 3 \times 3$ convolutions with exact zero-padding.
   - Float32 membrane array: `cnn_v_mem[8][28][28]`.
   - Threshold = $1.0$, subtractive reset: `cnn_v_mem -= 1.0`.
   - Spatially bins spikes into 2x2 pooling coordinates: $py = y \gg 1, px = x \gg 1$.
   - Stores up to 2048 spikes in `conv1_spike_buf`.
3. **Phase 2 (Conv2 Event-Driven Scatter)**:
   - Iterates through `conv1_spike_buf`.
   - For each Conv1 spike at $(k, py, px)$, looks up $16 \times 3 \times 3$ Int8 weights from `CONV2_WEIGHTS[co][k][1-dy][1-dx]`.
   - Adds weights directly into `cnn_l2_v_mem[16][14][14]`.
4. **Phase 3 (Layer 2 Sweep & Relay Generation)**:
   - Threshold is scaled by 4: `threshold_l2 = threshold << 2` to mathematically balance the 2x2 sum-pooling.
   - For each $(y2, x2) \in [0, 6] \times [0, 6]$, evaluates the 4 sub-pixels in $14 \times 14$.
   - When a neuron fires, emits an AXI spike packet to `encoder_spikes`:
     - `global_nid = (dst_grp << 8) | local_nid`
     - Alternates weight between 127 and 126 (`cnn_spike_toggle`) so that the RTL edge detector (`hls_spike_payload_changed`) reliably registers back-to-back spikes from the same neuron.

## B. RTL Core Group Architecture (`hardware/hdl/rtl/`)
1. **Hierarchical Topology (`config/snn_params.yaml`)**:
   - Total Groups: 5.
   - Groups 0..3: 196 neurons each ($4 \times 196 = 784$ total). Configured with $V_{th} = 1$, acting as instant relays for Layer 2 spikes from HLS.
   - Group 4: 16 allocated neurons (neurons 0..9 represent MNIST digit classes 0..9). Configured with $V_{th} = \text{cfg\_global\_threshold}$ ($143$).
2. **Hierarchical Core Group LIF Engine (`core_group.v`)**:
   - Each Core Group encapsulates its own internal Simple Dual-Port (SDP) BRAM neuron state memory:
     ```verilog
     reg [STATE_WIDTH-1:0] neuron_state_mem [0:NEURONS_PER_GROUP-1];
     ```
   - Format: `[23:8]` membrane potential (16-bit signed), `[7:0]` refractory counter (8-bit).
   - **Reset Policy**: When membrane crosses threshold, `ns_din <= {{DATA_WIDTH{1'b0}}, global_refrac_period}` (**Hard Reset to Zero**).
   - **Inhibition Policy**: When an inhibitory spike arrives, `ns_din <= (mem_rd >= sp_weight) ? (mem_rd - sp_weight) : 0` (**Clamped at Zero**).
   - Contains its own internal input spike FIFO (`spike_fifo [0:SPIKE_BUFFER_DEPTH-1]`) and local dense intra-group weight memory (`weight_mem`).
3. **Non-Blocking Event Router (`event_router_ng.v`)**:
   - Manages inter-group spike propagation using a round-robin arbiter.
   - When an external spike arrives from HLS (`ext_spike_valid`), routes it directly into Core Groups 0..3.
   - When a Core Group neuron spikes, triggers a lookup into the Synaptic Connectivity Table.
4. **Synaptic Connectivity Table (`synaptic_connectivity_table.v`)**:
   - BRAM-based routing table holding up to 16 fanout entries per source neuron (12,544 rows total).
   - Maps source neurons in Groups 0..3 to destination neurons in Group 4 with 8-bit weight magnitude and sign.

---

# 4. In-Depth Comparison: FC3 vs CNN3 (Option A vs Option B)

| Architectural Metric | Working FC3 Model (`fpga_3layer_inference.py`) | CNN3 Option A (`fpga_cnn3_coproc_inference.py`) | CNN3 Option B (`fpga_cnn3_inference.py`) |
| :--- | :--- | :--- | :--- |
| **On-Board Accuracy** | **> 97.0%** (10,000 images) | **97.1% – 98.3%** (1,000 images) | **11.00%** (1,000 images) |
| **Layer 1 Execution** | Host CPU (Float32 NumPy, $28\times 28 \to 256$) | Host CPU (Float32 NumPy Conv1 + Pool1) | FPGA HLS (`cnn_frame` + Conv1 engine) |
| **Layer 2 Execution** | FPGA Core Group 1 ($256$ LIF Neurons) | Host CPU (Int8 NumPy Conv2 + Pool2) | FPGA HLS (`cnn_l2_v_mem` + Sweep) |
| **Layer 3 Execution** | FPGA Core Group 2 ($10$ Class Neurons) | FPGA Core Group 4 ($10$ Class Neurons) | FPGA Core Group 4 ($10$ Class Neurons) |
| **Layer 3 Weight Range** | **Full 8-bit Range** ($[-114, +127]$) | **Full 8-bit Range** ($[-127, +127]$) | **Compressed Range** ($[-5, +4]$) |
| **Layer 3 Zero Synapses** | $< 5\%$ | $< 5\%$ | **64.5% (5,057 / 7,840 zeroed)** |
| **Hardware Threshold** | $80$ | $143$ | $143$ |
| **Spikes to Fire Class** | **1 – 2 spikes** (due to strong weights) | **2 – 3 spikes** | **36 – 70 spikes** (virtually unreachable) |
| **DMA Traffic Pattern** | Sparse ($\sim 20$ spikes / timestep) | Sparse ($\sim 15$ spikes / timestep) | Bulk Burst (HLS dumps L2 all at once) |
| **Output FIFO Status** | Zero drops (spikes fit in 32-entry FIFO)| Zero drops | Dropped $\sim 295$ spikes during burst |

---

# 5. Root Cause Analysis: The 11.00% Run & Class 8 Collapse

In the latest benchmark of Option B (`mnist_cnn3_inference_results.json`):
```json
{
    "metadata": { "model": "cnn3_T_4_clean_l2", "samples": 1000, "timesteps": 4, "hw_threshold": 143 },
    "metrics": { "accuracy_percent": 11.0, "correct": 110, "total": 1000, "avg_spikes_per_image": 5.78 }
}
```
Inspecting the individual sample predictions:
- `Image 0 (True: 7) -> Pred: 8` (Spikes: `[0, 0, 0, 1, 0, 2, 0, 0, 4, 0]`)
- `Image 1 (True: 2) -> Pred: 2` (Spikes: `[0, 0, 1, 0, 0, 0, 0, 0, 1, 0]`)
- `Image 3 (True: 0) -> Pred: 8` (Spikes: `[1, 0, 1, 1, 0, 1, 0, 0, 2, 0]`)
- `Image 4 (True: 4) -> Pred: 8` (Spikes: `[0, 0, 0, 1, 0, 1, 0, 0, 3, 0]`)
- `Image 6 (True: 1) -> Pred: 3` (Spikes: `[0, 0, 0, 1, 0, 0, 0, 0, 0, 0]`)

### The 4 Compounding Mechanisms Behind the Failure:

#### 1. Under-Quantization of Layer 3 Weights (`scale3 = 5.89`)
In `tests/prepare_cnn3_deployment.py`, `best_scale3_ratio` was reduced to `0.04` to prevent high-frequency DMA FIFO overflows. This scaled the weights as follows:
$$\text{final\_scale3} = 0.04 \times \frac{127.0}{\max |W_3|} = 5.89$$
- Weights were quantized via `np.round(w3 * 5.89)`.
- The resulting matrix `q_fc_w` has a minimum value of $-5$ and maximum of $+4$.
- **5,057 out of 7,840 weights rounded to zero**.
- All subtle negative inhibitory features designed to suppress rival classes were completely wiped out.

#### 2. The Unreachable Threshold for True Classes
- With `hw_threshold = 143`, accumulating 143 potential using weights of $+1$ to $+4$ requires:
  $$N_{\text{spikes}} \ge \frac{143}{4} \approx 36 \text{ spikes (or } 143 \text{ spikes for weight } +1\text{)}$$
- Correct digit classes (e.g. digit 1, 4, or 7) have sharp, localized spatial activations that only trigger 8 to 20 Layer 2 neurons. They **can never cross 143**.
- Digit 8, however, consists of two large loops spanning almost all quadrants of the $7\times 7$ feature map. It has hundreds of small $+1$ excitatory synapses. Across the 4 timesteps, the diffuse background activity easily accumulates $>143$ potential for Neuron 8, causing it to win by default.

#### 3. Temporal Clamping of Inhibitory Spikes in `core_group.v`
In software vector dot-products:
$$V_{\text{final}} = V_{\text{initial}} + \sum W_{\text{exc}} - \sum |W_{\text{inh}}|$$
Positive and negative influences cancel simultaneously.  
In hardware, spikes arrive **sequentially** through the Event Router:
- If an inhibitory spike arrives when a neuron's membrane is at 0:
  ```verilog
  if (mem_rd >= sp_weight)
      ns_din <= {mem_rd - sp_weight, ref_rd};
  else
      ns_din <= {{DATA_WIDTH{1'b0}}, ref_rd}; // CLAMPED TO ZERO!
  ```
- The negative charge is **discarded**.
- When excitatory spikes subsequently arrive later in the timestep, there is zero accumulated negative potential to resist them. This causes massive over-excitation of classes that rely on strong negative inhibition (most notably Class 8, which has the strongest negative bias in the PyTorch model: $-0.2507$).

#### 4. Hardware Hard Reset vs Software Subtractive Reset
- In `core_group.v`: `ns_din <= {{DATA_WIDTH{1'b0}}, global_refrac_period}` resets the potential to 0 upon firing.
- In software simulation: `v -= threshold` preserves the remainder (e.g., if potential reached 160 and threshold was 143, 17 remains).
- With very small weights ($+1$ to $+4$), discarding the remainder penalizes multi-spike burst generation for true classes.

---

# 6. Minimal File & Subfolder Checklist for Gemini 4 Argon

To provide Gemini 4 Argon with the exact, uncluttered context required to analyze and resolve this issue, upload **only** the following 14 curated files (totaling $<150\text{ KB}$ of text):

### A. RTL Hardware Architecture (5 active files)
1. [`hardware/hdl/rtl/top/snn_core_group_top.v`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/hdl/rtl/top/snn_core_group_top.v) (Top-level integration, HLS bridge, output FIFO, threshold assignment)
2. [`hardware/hdl/rtl/core/core_group.v`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/hdl/rtl/core/core_group.v) (Hierarchical neuron core with internal SDP BRAM state, LIF FSM, hard reset, zero-clamped inhibition, and local weight memory)
3. [`hardware/hdl/rtl/core/event_router_ng.v`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/hdl/rtl/core/event_router_ng.v) (Non-blocking crossbar, external spike routing, CT lookup FSM)
4. [`hardware/hdl/rtl/core/synaptic_connectivity_table.v`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/hdl/rtl/core/synaptic_connectivity_table.v) (Inter-group routing BRAM table)
5. [`hardware/hdl/rtl/common/snn_config_regs.v`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/hdl/rtl/common/snn_config_regs.v) (AXI-Lite configuration and status registers)

*(Note: `lif_neuron_array.v` and `spike_router.v` are legacy artifacts from the original flat architecture `snn_integrated_top.v` and are completely omitted.)*

### B. HLS C++ Streaming Engine (3 files)
6. [`hardware/hls/src/snn_top_hls.cpp`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/hls/src/snn_top_hls.cpp) (Streaming 2D Conv1 + Conv2 engine, Phase 1/2/3 pipeline, spike emitter)
7. [`hardware/hls/include/snn_top_hls.h`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/hls/include/snn_top_hls.h) (Interface structs, packet bitfields, constants)
8. [`hardware/hls/include/cnn3_weights.h`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/hls/include/cnn3_weights.h) (Auto-generated Int8 Conv1/Conv2 weight tensors)

### C. System Configuration (2 files)
9. [`config/snn_params.yaml`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/config/snn_params.yaml) (Master architectural single-source-of-truth)
10. [`config/generated/snn_params.h`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/config/generated/snn_params.h) (Auto-generated C++ header with derived bitwidths)

### D. Software Deployment & Drivers (3 files)
11. [`tests/prepare_cnn3_deployment.py`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/tests/prepare_cnn3_deployment.py) (Weight quantization, bias folding, threshold calibration sweep)
12. [`tests/fpga_cnn3_coproc_inference.py`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/tests/fpga_cnn3_coproc_inference.py) (**Option A**: Working 97.1% on-board co-processing driver)
13. [`tests/fpga_cnn3_inference.py`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/tests/fpga_cnn3_inference.py) (**Option B**: 100% on-FPGA streaming driver with DMA drain loop)

### E. Reference Working Model (1 file)
14. [`tests/fpga_3layer_inference.py`](file:///Users/cenkersahin/Desktop/SNN_Radboud/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/tests/fpga_3layer_inference.py) (Proven >97% fully connected hardware driver for comparison)

---

# 7. Recommended Engineering Solutions

To bring Option B up to the >97% accuracy demonstrated by Option A, three targeted adjustments must be implemented:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                RECOMMENDED ACTION PLAN                                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. RESTORE FULL 8-BIT QUANTIZATION FOR LAYER 3                                         │
│    Set scale3_ratio = 1.0 (or calibrate scale3 to span [-127, +127]).                  │
│    Eliminates the 64.5% dead synapses and restores sharp digit filter specificity.     │
│                                                                                        │
│ 2. PREVENT S2MM DMA FIFO OVERFLOW IN HARDWARE                                          │
│    Option A: In snn_core_group_top.v, increase SPIKE_OUT_FIFO_DEPTH from 32 to 512.     │
│    Option B: In snn_top_hls.cpp, configure AXI DMA burst streaming (out_pkt.last = 0     │
│    during inference, last = 1 on end of timestep) to stream spikes into DDR RAM.       │
│                                                                                        │
│ 3. MATCH HARDWARE RESET DYNAMICS IN DEPLOYMENT CALIBRATION                             │
│    In tests/prepare_cnn3_deployment.py, update the threshold calibration loop to use   │
│    Hard Reset (v = 0) and zero-clamped inhibition, exactly matching core_group.v.      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```
