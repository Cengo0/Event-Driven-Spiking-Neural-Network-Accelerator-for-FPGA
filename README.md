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
rtk python scripts/generate_spikemold_runtime_artifacts.py
rtk python scripts/check_spikemold_runtime_artifacts.py
rtk python scripts/check_verifier_gate.py
rtk pytest software/python/tests
```

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

Current evidence is software contract/golden only unless a report explicitly says
HLS, RTL, or PYNQ-Z2 board execution was run. Do not infer board latency,
throughput, or energy from software artifacts.

## Main Files

- `contracts/`: architecture, trace, event, register, and resource contracts
- `software/python/spikepress/`: SpikePress software package
- `golden_traces/v1/`: deterministic architecture-neutral traces
- `scripts/check_spikemold_batch0_1a.py`: contract/artifact checker
- `scripts/check_verifier_gate.py`: board-free verifier gate checker
- `scripts/run_spikemold_pynq_one_shot.py`: PYNQ one-shot runtime CLI
- `reports/`: current gate reports

## License

MIT License. See [LICENSE](LICENSE).
