# SpikePress + SpikeMold-EDNP

SpikePress + SpikeMold-EDNP is a fixed-bitstream FPGA SNN research stack.

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
- EDNP artifact JSON roundtrip
- Batch 0/1A contract verification

Out of scope for the current EDNP mainline:

- legacy accelerator API
- Python-controlled inner loops as runtime architecture

## Quick Check

```bash
source /home/jwlee/miniconda3/etc/profile.d/conda.sh
conda activate fpga
rtk python scripts/generate_ednp_batch1a_artifacts.py
rtk python scripts/check_ednp_batch0_1a.py
rtk pytest software/python/tests
```

## Minimal SpikePress Example

```python
from spikepress import InputSpike, fc_lif_model

model = fc_lif_model("tiny", weights=[[3, 1], [2, 0]], thresholds=[5, 9])
compiled = model.compile_ednp(target="pynq-z2")
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
- `scripts/check_ednp_batch0_1a.py`: contract/artifact checker
- `reports/`: current gate reports

## License

MIT License. See [LICENSE](LICENSE).
