# Architecture Migration and Debugging Summary: 3-Layer SNN Co-Processing

## 1. Hardware Parameterization & HLS Generation
*   **Original State:** The base architecture was configured for a simple, flat 150-neuron array (10 classes × 15 neurons) designed for end-to-end Time-To-First-Spike (TTFS) evaluation.
*   **Modifications:** We updated the YAML configuration files to target a deep 3-layer architecture (784 → 256 → 256 → 10). Because synthesizing the entire network would exceed the Zynq-7020's BRAM limits, we parameterized the hardware to exclusively accelerate the densest hidden layer (Layer 2: 256 inputs, 256 outputs). 
*   **Purpose:** This configuration generates the specific Vitis HLS IP (`snn_top_hls_0`) and parameter headers required to drive a 256-neuron hardware block. Isolating this dense hidden layer on the programmable logic creates a highly localized, high-switching-activity target optimized for capturing precise electromagnetic (EM) side-channel traces.

## 2. Vivado Project & Bitstream Generation
*   **Original State:** The original Vivado TCL script generated a block design mapping the HLS controller to a 150-neuron Verilog RTL array using the legacy `spike_router.v` logic.
*   **Modifications:** We altered the TCL script to integrate the new 256-neuron `snn_core_group_top.v` RTL block. We stripped out the obsolete `spike_router.v` and replaced it with `event_router.v` and its accompanying `synaptic_connectivity_table.v`. We safely bypassed missing physical pin constraints (e.g., `snn_busy`) and re-mapped the AXI Stream (DMA) and AXI-Lite (MMIO) interfaces to handle the increased memory dimensions.
*   **Purpose:** To synthesize `snn_core_group_v2.bit` and its memory map (`.hwh`), bridging the ARM processing system with the newly expanded and routed SNN logic fabric.

## 3. Software Payload & Sanity Check (Host Python)
*   **Original State:** Raw MNIST pixels (0.0 to 1.0) were converted directly into binary spikes on the CPU. The FPGA weights were uploaded without bias integration, and the entire math pipeline was effectively bypassed in favor of a 1-to-1 routing loop.
*   **Modifications:** We created `prepare_3layer_deployment.py` to establish a "CPU-FPGA-CPU Sandwich" co-processing model:
    *   **Layer 1 (CPU):** Processes Z-score normalized analog inputs (-0.42 to 2.82) via float32 multiplication to generate the first wave of spikes.
    *   **Layer 2 (FPGA):** Handles the massive Int8 matrix multiplication. We embedded the Layer 2 biases directly into the weight matrix by appending an "Always-On Bias Neuron" to the input vectors. 
    *   **Layer 3 (CPU):** Accumulates the FPGA's output spikes into final voltage logits.
*   **Purpose:** This script successfully matched the PyTorch model's ~98% accuracy in software, applied dynamic sparsity (pruning weights <= 4) to fit the hardware limits, and packed the final states into `mnist_3layer_deployment.npz`.

## 4. Hardware Inference Execution (PYNQ Board Python)
*   **Original State:** The original `fpga_10class_inference.py` script relied on high-level PYNQ DMA drivers and performed dot-product math on the CPU, using the FPGA merely as a dummy spike sorter.
*   **Modifications:** We authored `fpga_3layer_inference.py` and `run_inference.sh` to force the FPGA silicon to execute the actual matrix multiplication:
    *   **Virtual Source Expansion:** The Verilog RTL has a strict physical limit of 32 fanouts per input. We bypassed this by breaking each of the 257 inputs into virtual chunks of 32 (mapping 257 real inputs to ~1778 virtual IDs) and offset them by 256 to prevent physical output loopbacks.
    *   **Pure MMIO DMA:** We bypassed PYNQ's high-level DMA driver to resolve severe FIFO deadlocks, manually driving the memory transfers and handling AXI interrupts via register reads.
    *   **Cache Coherency:** Implemented `flush()` and `invalidate()` commands to ensure the ARM CPU and FPGA shared the same physical DDR memory states.
    *   **Threshold Scaling:** Scaled the hardware threshold dynamically to compensate for both the sparsity pruning and the hardware router's native bit-shift weight halving.

## 5. Current Bottleneck & Diagnostics
*   **The Symptom:** The inference script runs seamlessly without deadlocks, but outputs an accuracy of exactly 8.9%. Every single image is classified as Label 8. 
*   **The Cause:** Layer 3 (running on the CPU) is receiving zero meaningful spikes from the FPGA. When Layer 3 accumulates an array of zeros, it defaults to its highest naturally trained bias, which corresponds to Class 8.
*   **Hardware State:** The built-in hardware diagnostic counters confirm the FPGA is not broken. `CFG_ROUTER_SPKS` and `CFG_NEURON_SPKS` report thousands of processed spikes, proving the DMA, HLS IP, and Verilog routers are receiving data, running the math, and firing.
*   **Core Problem:** A severe disconnect exists between the spikes the hardware is generating and the data the software is decoding. Potential culprits include a bit-mask misalignment when unpacking the AXI stream (the CPU is looking at the wrong bits for the neuron ID), physical voltage suppression (the physical threshold is still mismatched against the routed weights), or a memory mapping fault within the Virtual Source Expansion loop (the hardware is routing the inputs to the wrong destinations).

---

## 6. Comprehensive Project File Inventory

**I. Hardware Configuration & RTL Sources**
*   `snn_config.yaml`: The master configuration file dictating neuron counts, network depth, and global parameters.
*   `snn_config_regs.v`: Verilog RTL mapping the AXI-Lite memory offsets to the configuration registers.
*   `synaptic_connectivity_table.v`: Verilog RTL defining the BRAM routing tables and the physical 32-fanout limit.
*   `event_router.v`: Verilog RTL replacing the legacy spike router; responsible for distributing incoming spikes to destination neurons based on the connectivity table.
*   `snn_core_group_top.v`: The top-level Verilog wrapper integrating the neurons, router, and configuration logic for the 256-neuron array.

**II. High-Level Synthesis (HLS)**
*   `snn_top_hls_0` (C/C++ Source & Headers): The Vitis HLS kernel that provides the state machine, threshold application, and spike encoding/decoding.
*   *HLS IP Archive (.zip)*: The packaged IP block exported from Vitis to Vivado.

**III. Vivado Integration & Bitstream**
*   `snn_integrated_v2.tcl`: The build script used to automate the Vivado block design, wire the AXI DMA/MMIO channels, and generate the bitstream.
*   `snn_core_group_v2.bit`: The synthesized programmable logic file flashed to the PYNQ-Z2 board.
*   `snn_core_group_v2.hwh`: The hardware handoff file containing the physical register maps utilized by the PYNQ `Overlay` class.

**IV. Host Software (Preparation)**
*   `prepare_3layer_deployment.py`: Python script run on the host computer. Extracts weights from the PyTorch `.pth` file, tests the software sanity baseline, applies L2 augmentation, and scales parameters for hardware deployment.
*   `mnist_3layer_deployment.npz`: The serialized data payload containing weights, biases, hardware thresholds, and flattened MNIST test vectors.

**V. Embedded Software (Execution)**
*   `fpga_3layer_inference.py`: Python script run directly on the ARM Cortex-A9 processor of the PYNQ-Z2 board. Handles Layer 1/Layer 3 math, dynamic weight sparsity, Virtual Source Expansion, raw MMIO DMA transfers, and cache synchronization.
*   `run_inference.sh`: A shell script wrapper that executes the inference Python script with `sudo -E` privileges to ensure stable `/dev/mem` access while preserving environmental paths.
*   `inference_results.json`: The detailed logging output generated after an inference run, recording accuracy, latency matrices, predictions, and hardware diagnostic counters.