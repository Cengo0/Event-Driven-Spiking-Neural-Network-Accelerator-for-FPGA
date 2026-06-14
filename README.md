# SpikePress + SpikeMold

SpikePress + SpikeMold is a fixed-bitstream FPGA SNN research stack.

- **SpikePress**: software API, integer golden traces, resource-aware compiler artifacts
- **SpikeMold**: PYNQ-Z2 / Zynq-7020 event-triggered hardware backend

The project goal is HW/SW co-design for accessible event-driven neuromorphic
deployment: train or define models in software, compile explicit integer
artifacts, run bounded jobs on SpikeMold, and verify against golden traces.

## Current Scope

Active path:

- inference-only SpikePress API
- integer FC-LIF and EventConv trace generation
- event/update budget checks
- SpikeMold artifact JSON roundtrip
- Batch 0/1A contract verification
- Batch 1B software transport smoke
- Batch 1C EventConv AGU/state/commit C0/C1/C2/C3/C4 RTL smoke
- board-free verifier gate review
- PYNQ one-shot runtime API and CLI entrypoint

Out of scope for the current SpikeMold mainline:

- removed HW/SW API
- Python-controlled inner loops as runtime architecture
- on-chip adaptation/training engines

## Quick Check

```bash
source /home/jwlee/miniconda3/etc/profile.d/conda.sh
conda activate fpga
rtk python scripts/generate_spikemold_batch1a_artifacts.py
rtk python scripts/check_spikemold_batch0_1a.py
rtk python scripts/generate_batch1b_transport_artifacts.py
rtk python scripts/check_batch1b_transport.py
rtk python scripts/generate_batch1c_eventconv_artifacts.py
rtk python scripts/check_batch1c_eventconv.py
rtk python scripts/generate_batch1x_architecture_sandbox_artifacts.py
rtk python scripts/check_batch1x_architecture_sandbox.py
rtk python scripts/check_architecture_selection.py
rtk bash hardware/scripts/run_eventconv_ooc_synthesis.sh
rtk python scripts/generate_eventconv_ooc_synthesis_report.py
rtk python scripts/check_eventconv_ooc_synthesis_report.py
rtk python scripts/generate_spikemold_runtime_artifacts.py
rtk python scripts/check_spikemold_runtime_artifacts.py
source /tools/Xilinx/2025.2/Vitis/settings64.sh
rtk vitis-run --mode hls --csim --config hardware/hls/hls_csim_config.cfg --work_dir hardware/hls/hls_csim_output
rtk bash hardware/hls/scripts/build_hls.sh --profile spikemold-top --work-dir hardware/hls/hls_output --clock 12.5ns --verbose
source /tools/Xilinx/2025.2/Vivado/settings64.sh
rtk env SPIKEMOLD_PL_CLK_MHZ=20 vivado -mode batch -source hardware/scripts/rebuild_integrated.tcl
rtk python scripts/generate_spikemold_build_evidence_report.py
rtk python scripts/check_spikemold_build_evidence_report.py
rtk python scripts/check_verifier_gate.py
rtk pytest software/python/tests
```

## Board Smoke

Live PYNQ-Z2 board smoke is separate from the board-free verifier gate:

```bash
rtk python scripts/generate_spikemold_board_smoke_report.py
rtk python scripts/check_spikemold_board_smoke_report.py
rtk python scripts/generate_spikemold_dma_weight_smoke_report.py
rtk python scripts/check_spikemold_dma_weight_smoke_report.py
```

The current board smoke report proves overlay load, HLS AXI-Lite register
access, `ap_done`, and `version_reg` readback. The DMA weight smoke report
adds `axi_dma_1` weight-load/checkpoint readback proof. Spike input/output
correctness is the next gate.

## Minimal SpikePress Example

```python
from spikepress import InputSpike, fc_lif_model

model = fc_lif_model("tiny", weights=[[3, 1], [2, 0]], thresholds=[5, 9])
compiled = model.compile_spikemold(target="pynq-z2")
trace = model.golden_trace([
    InputSpike(tick=0, src_id=0),
    InputSpike(tick=1, src_id=1),
])

print(compiled.artifact.sha256)
print(trace.to_dict()["counters"])
```

## Evidence Boundary

Current evidence includes board-free software contracts, EventConv OOC synthesis,
and integrated HLS/Vivado routed bitstream reports only when the corresponding
reports exist and pass. Do not infer PYNQ-Z2 board correctness, latency,
throughput, or energy unless a report explicitly records board execution.

## Main Files

- `contracts/`: architecture, trace, event, register, and resource contracts
- `software/python/spikepress/`: SpikePress software package
- `golden_traces/v1/`: deterministic architecture-neutral traces
- `scripts/check_spikemold_batch0_1a.py`: contract/artifact checker
- `scripts/check_verifier_gate.py`: board-free verifier gate checker
- `scripts/check_spikemold_build_evidence_report.py`: HLS/Vivado build evidence checker
- `scripts/check_spikemold_board_smoke_report.py`: PYNQ-Z2 board smoke checker
- `scripts/check_spikemold_dma_weight_smoke_report.py`: PYNQ-Z2 DMA weight smoke checker
- `scripts/run_spikemold_pynq_one_shot.py`: PYNQ one-shot runtime CLI
- `scripts/run_spikemold_pynq_hls_register_smoke.py`: current-bitstream PYNQ smoke CLI
- `scripts/run_spikemold_pynq_dma_weight_smoke.py`: current-bitstream AXI DMA smoke CLI
- `reports/`: current gate reports

## License

MIT License. See [LICENSE](LICENSE).
