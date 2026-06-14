# Contributing

This repository now uses SpikePress and SpikeMold names only.

## Naming

- Software package/API: `spikepress`
- Hardware/backend name: `spikemold` or `SpikeMold`
- Do not add references to removed package names.
- Do not reintroduce removed experiment paths into the EDNP mainline.

## Environment

Use the `fpga` conda environment:

```bash
source /home/jwlee/miniconda3/etc/profile.d/conda.sh
conda activate fpga
```

Use Xilinx 2025.2 tools under `/tools/Xilinx/2025.2` for HLS/Vivado work. Do not
use `iverilog`.

Use `rtk` for shell commands in this checkout.

## Evidence

Keep evidence levels separate:

- SpikePress software/golden
- HLS C-sim
- RTL simulation
- packaged bit/HWH readback
- PYNQ-Z2 board execution

Only board-captured output plus counters supports board execution, latency,
throughput, or energy claims.

## Validation

For current Batch 0/1A work:

```bash
rtk python scripts/generate_ednp_batch1a_artifacts.py
rtk python scripts/check_ednp_batch0_1a.py
rtk pytest software/python/tests
```
