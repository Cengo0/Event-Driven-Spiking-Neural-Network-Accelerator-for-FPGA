# SNN Side-Channel Temporal Logging Manual

## Pre-Silicon Simulation Flow (Host PC)
This phase establishes a cycle-accurate baseline of the network's behavior before analyzing physical silicon.
*   **Generate Stimulus:** Run `python export_sim_spikes.py`. This script extracts thresholded weights and active pixels from the `mnist_10class_deployment.npz` archive to output `sim_input_spikes.hex`.
*   **Execute Testbench:** Compile and run the Verilog testbench using `iverilog -g2012 -I ../../config/generated -I rtl/include -o mnist_sim ../sim/tb_mnist_inference.v rtl/neurons/*.v rtl/common/*.v` followed by `vvp mnist_sim`.
*   **Simulation Output:** This produces a waveform file (`mnist_inference.vcd`) and a raw cycle-by-cycle text log (`sim_output_spikes.txt`) detailing exactly when each neuron fires under saturated input conditions.

## Post-Silicon Physical Execution (PYNQ-Z2)
This phase captures the true hardware execution, revealing actual Time-To-First-Spike (TTFS) behavior and physical DMA startup latencies.
*   **Deploy Logger:** Transfer the dedicated tracking scripts, `fpga_tvla_inference.py` and `run_tvla_fpga_infer.sh`, to the board.
*   **Execute on Board:** Run `./run_tvla_fpga_infer.sh`. This script bypasses standard truncation, allocating a massive 10,000-word S2MM buffer to capture the full temporal trace for the first 10 images.
*   **Physical Output:** The board generates `physical_output_spikes.txt` containing the 14-bit timestamps and 10-bit neuron IDs. Transfer this back to your host machine for analysis.

## TVLA Analytics and Visualization
The final step standardizes the data for Test Vector Leakage Assessment (TVLA) to correlate against physical power traces.
*   **Generate Analytics:** Execute `python plot_leakage.py`, ensuring the read path points to either your simulated or physical text log.
*   **Parquet Packaging:** The script compresses the raw log into `batch=00000.parquet`, the optimized columnar format required for efficient side-channel data processing.
*   **Leakage Visualization:** Two plots are generated: `temporal_cycle_plot.png` (revealing internal burst activity and 80-microsecond DMA delays) and `image_cross_sectional_plot.png` (proving data-dependent dynamic power consumption).

## Strategic Security Implications
With the temporal logging pipeline completely verified, the discrepancies between the raw event-stream simulation and the highly-optimized physical TTFS execution are fully mapped. This provides the exact cycle-by-cycle templates needed to correlate power signatures in the laboratory environment in Nijmegen.