# Verifier Gate Review

Status: board-free verifier gate passed
Date: 2026-06-14

## Evidence Level

`board_free_verifier_gate_no_board`

No board execution was run. This review does not claim PYNQ-Z2 PL correctness,
latency, throughput, energy, board execution correctness, or dataset accuracy.

## Scope

This review checks the current SpikePress + SpikeMold v3.6 board-free
implementation slice:

- Batch 0 contract freeze
- Batch 1A SpikePress software foundation and architecture-neutral traces
- Batch 1B transport and SpikeMold flat FC-LIF software smoke artifacts
- Batch 1C EventConv primitive artifacts
- Batch 1X architecture exploration sandbox
- selected FC/EventConv runtime contract and resource report
- EventConv Vivado OOC synthesis evidence
- SpikeMold HLS/Vivado build evidence
- PYNQ one-shot runtime API and CLI entrypoint

## Gate Results

| Gate | Result | Evidence |
|---|---:|---|
| contracts exist | PASS | `contracts/*.md` |
| page/tile/coregroup policy is architecture-open | PASS | `contracts/ARCHITECTURE_PATTERN_POLICY_V1.md` |
| trace schema and hashes match | PASS | `golden_traces/v1/*.json` |
| event budget passes | PASS | `outputs/event_budget/recommended_flat_fc_lif_config.json` |
| Python inner-loop count is zero | PASS | trace counters and runtime contract |
| inner-loop DDR bytes are zero | PASS | trace counters and runtime/resource reports |
| SpikeMold flat FC-LIF trace/readout/state match | PASS | `outputs/transport/batch_1b_transport_flat_fc_lif_smoke.json` |
| EventConv C0-C5 artifacts present | PASS | `reports/batch_1c_eventconv_primitive_report.md` |
| EventConv OOC synthesis evidence | PASS | `reports/eventconv_ooc_synthesis_report.md` |
| HLS C-sim and synthesis/IP package | PASS | `reports/spikemold_build_evidence_report.md` |
| integrated Vivado routed timing at 20 MHz | PASS | `outputs/spikemold_pynq_z2_timing.rpt` |
| bit/HWH artifact hashes present | PASS | `outputs/spikemold_pynq_z2.bit`, `outputs/spikemold_pynq_z2.hwh` |
| architecture sandbox preserves semantics | PASS | `outputs/architecture_sandbox/batch_1x_architecture_sandbox.json` |
| selected runtime backend excludes probationary switch | PASS | `outputs/runtime/spikemold_runtime_contract.json` |
| PYNQ one-shot runtime API exists | PASS | `software/python/spikepress/pynq_runtime.py` |
| PYNQ one-shot CLI exists | PASS | `scripts/run_spikemold_pynq_one_shot.py` |
| board claims absent | PASS | reports and JSON artifacts set `board_executed=false` |

## Inference-Only Scope

The selected backend is `spikemold_fc_eventconv`, covering inference-only
FC-LIF and shared-kernel EventConv primitives. Training or on-chip adaptation
paths are not part of this gate and must not be used to claim correctness,
performance, or hardware readiness.

The HLS public surface, generated config, RTL router/top selected fabric, and
active router/integration testbenches are now inference-only.

## Current Build Evidence

The integrated SpikeMold build now has HLS C-sim pass, HLS synthesis/IP package,
and routed Vivado bitstream evidence at 20 MHz. This remains a no-board result:
`board_executed=false`.

## Required Next Gate

PYNQ one-shot runtime API is present, but was not executed as part of this
board-free gate. A separate HLS register board smoke exists in
`reports/spikemold_board_smoke_report.md`.

Before neural correctness claims:

1. Replace the legacy memory-base one-shot runtime with the current HLS
   AXI-stream/DMA runtime.
2. Run DMA stream smoke through `axi_dma_0`/`axi_dma_1`.
3. Compare board readback with the SpikePress golden trace/readout hash.

## Verifier Command

```bash
rtk python scripts/check_verifier_gate.py
```
