# SNN Deployment and Energy Profiling Workflow

## Phase 1: Hardware Compilation & Power Simulation (Host PC)
1. Compile the C++ learning engine into a Verilog IP block by executing `./scripts/build_hls.sh --clean` in the `hardware/hls` directory.
2. Edit `hardware/scripts/rebuild_integrated.tcl` to set `project_dir` to your local path, then run `vivado -mode batch -source rebuild_integrated.tcl` to synthesize the design and generate the `snn_integrated_v2.bit` bitstream.
3. Simulate hardware switching activity to generate the `power_sweep.saif` file by executing `./hardware/scripts/run_power_sweep_sim.sh`. Before running, ensure line 13 of the script is updated to source your specific Vivado installation path (e.g., `source /home/chipwisperer/AMD/2025.2/Vivado/settings64.sh`). This script utilizes Vivado's simulation tools (`xvlog`, `xelab`, and `xsim`) to automatically output the SAIF file into the `hardware/sim_work_power` directory.
4. Import `power_sweep.saif` into the Vivado Xilinx Power Analyzer (XPA) with the routed design open to extract the isolated Programmable Logic (PL) dynamic power (0.198 W), saving the results to a power report.

## Phase 2: Model Training & Packaging (Host PC)
5. Bypass GPU architecture incompatibilities by forcing CPU execution during training: `CUDA_VISIBLE_DEVICES="" python tests/onchip_stdp_faithful.py`. This generates the trained weights for the 150-neuron baseline model.
6. Quantize the floating-point weights to signed 8-bit integers by running `python tests/prepare_10class_deployment.py`. This script bundles the quantized weights, hardware thresholds, and 10,000 test images into the `mnist_10class_deployment.npz` deployment artifact.

## Phase 3: Transfer & On-Board Execution (PYNQ-Z2)
7. Allocate a secure directory on the board with the correct permissions: `ssh -t xilinx@192.168.2.99 'mkdir -p ~/snn && sudo chown -R xilinx:xilinx ~/snn'`.
8. Transfer the required artifacts using `scp`: send `snn_integrated_v2.bit`, `mnist_10class_deployment.npz`, `fpga_10class_inference.py`, `run_scenario1_native_fpga_infer.sh`, and `ina226_power_measure.py` to the board.
9. In your first SSH terminal, begin capturing the physical board power: `sudo python3 ina226_power_measure.py --mode standalone --duration 60 --output power_active.json`.
10. In a second SSH terminal, execute the inference workload to stream the spikes through the fabric: `./run_scenario1_native_fpga_infer.sh --deployment mnist_10class_deployment.npz --output mnist_results.json`.

## Phase 4: Energy Metrics Computation (Host PC)
11. Retrieve the execution artifacts from the board using `scp xilinx@192.168.2.99:/home/xilinx/snn/*.json .`.
12. Combine the physical XADC board power, hardware latency timings, and Vivado XPA dynamic power by running `python3 scripts/compute_energy_metrics.py`. By passing the `.json` files and `--xpa-dynamic-w 0.198`, this outputs `final_energy_metrics.json` containing the exact picojoule cost per spike.