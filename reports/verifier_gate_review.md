# Verifier Gate Review

Status: verifier gate passed with direct RTL transport, flat FC-LIF, and EventConv board smokes
Date: 2026-06-15

## Evidence Level

`verifier_gate_with_pynq_direct_rtl_spike_smoke`

PYNQ-Z2 direct RTL AXI DMA spike smoke, EventWord64-lowered input board smoke,
tiny flat FC-LIF board commit-value/state-checksum smoke, and tiny EventConv
plus burst-boundary EventConv board commit-value/state-checksum smokes were run
and folded into Batch 1B/1C evidence. Strongest board claim boundary:

`pynq_axi_dma0_direct_rtl_eventconv_burst_boundary_state_checksum_readback`

No latency, throughput, energy, dataset, full-state dump, or full-network board
claim is made here.

## Scope

This review checks the current SpikePress + SpikeMold v3.6 board-free
implementation slice:

- Batch 0 contract freeze
- Batch 1A SpikePress software foundation and architecture-neutral traces
- Batch 1B transport and SpikeMold flat FC-LIF software smoke artifacts
- PYNQ-Z2 direct RTL spike transport smoke
- EventWord64-lowered input board smoke
- tiny flat FC-LIF board commit-value/state-checksum smoke
- tiny EventConv board commit-value/state-checksum smoke
- burst-boundary EventConv board commit-value/state-checksum smoke
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
| PYNQ-Z2 direct RTL spike transport smoke | PASS | `outputs/board/dma_spike_smoke_result_20260614.json` |
| EventWord64-lowered input board smoke | PASS | `outputs/board/dma_spike_smoke_eventword64_result_20260614.json` |
| tiny flat FC-LIF board commit value + state checksum | PASS | `outputs/board/flat_fc_lif_trace_smoke_result_20260614.json` |
| tiny EventConv board commit value + state checksum | PASS | `outputs/board/eventconv_trace_smoke_result_20260614.json` |
| burst-boundary EventConv board commit value + state checksum | PASS | `outputs/board/eventconv_burst_boundary_smoke_result_20260615.json` |
| EventConv C0-C5 artifacts present | PASS | `reports/batch_1c_eventconv_primitive_report.md` |
| EventConv OOC synthesis evidence | PASS | `reports/eventconv_ooc_synthesis_report.md` |
| HLS C-sim and synthesis/IP package | PASS | `reports/spikemold_build_evidence_report.md` |
| integrated Vivado bit/HWH artifact | PASS | `outputs/spikemold_pynq_z2_eventconv_20mhz.bit`, `outputs/spikemold_pynq_z2_eventconv_20mhz.hwh` |
| integrated Vivado routed timing at 20 MHz | PASS | WNS `34.974` ns |
| bit/HWH artifact hashes present | PASS | `outputs/spikemold_pynq_z2_eventconv_20mhz.bit`, `outputs/spikemold_pynq_z2_eventconv_20mhz.hwh` |
| architecture sandbox preserves semantics | PASS | `outputs/architecture_sandbox/batch_1x_architecture_sandbox.json` |
| selected runtime backend excludes probationary switch | PASS | `outputs/runtime/spikemold_runtime_contract.json` |
| PYNQ one-shot runtime API exists | PASS | `software/python/spikepress/pynq_runtime.py` |
| PYNQ one-shot CLI exists | PASS | `scripts/run_spikemold_pynq_one_shot.py` |
| board claims scoped | PASS | one-spike, flat FC-LIF, tiny EventConv, and burst-boundary EventConv board smokes only; full-state/full-network/performance claims absent |

## Inference-Only Scope

The selected backend is `spikemold_fc_eventconv`, covering inference-only
FC-LIF and shared-kernel EventConv primitives. Training or on-chip adaptation
paths are not part of this gate and must not be used to claim correctness,
performance, or hardware readiness.

The HLS public surface, generated config, RTL router/top selected fabric, and
active router/integration testbenches are now inference-only.

## Current Build Evidence

The integrated SpikeMold build now has HLS C-sim pass, HLS synthesis/IP package,
and routed Vivado bit/HWH artifact evidence. The current board-smoke bitstream
is routed at 20 MHz and meets timing. Build evidence remains separate from board
execution evidence.

Direct RTL board smoke evidence:

- result JSON: `outputs/board/dma_spike_smoke_result_20260614.json`
- direct one-spike claim boundary:
  `pynq_axi_dma0_direct_rtl_one_spike_event_to_post_spike_readback_only_no_dataset`
- EventWord64 result JSON: `outputs/board/dma_spike_smoke_eventword64_result_20260614.json`
- flat FC-LIF result JSON: `outputs/board/flat_fc_lif_trace_smoke_result_20260614.json`
- flat FC-LIF claim boundary:
  `pynq_axi_dma0_direct_rtl_tiny_flat_fc_lif_commit_value_state_checksum_readback`
- EventConv result JSON: `outputs/board/eventconv_trace_smoke_result_20260614.json`
- EventConv claim boundary:
  `pynq_axi_dma0_direct_rtl_tiny_eventconv_multi_commit_state_checksum_readback`
- EventConv burst-boundary result JSON: `outputs/board/eventconv_burst_boundary_smoke_result_20260615.json`
- EventConv burst-boundary claim boundary:
  `pynq_axi_dma0_direct_rtl_eventconv_burst_boundary_state_checksum_readback`
- EventWord64 input: `2048`
- lowered AXIS32 word: `8192`
- flat FC-LIF input AXIS32 words: `[8192, 2105345, 4202496]`
- flat FC-LIF expected/board readout ids: `[2]`
- flat FC-LIF expected/board commit values: `[5]`
- flat FC-LIF expected/board state checksum: `5`
- EventConv backend mode: `1`
- EventConv input AXIS32 words: `[16842752]`
- EventConv expected/board readout ids: `[2, 1, 0]`
- EventConv expected/board commit values: `[2, 3, 4]`
- EventConv expected/board state checksum: `1`
- EventConv burst-boundary input AXIS32 words: `[16842752, 33685504, 0]`
- EventConv burst-boundary expected/board readout ids: `[3, 1, 0]`
- EventConv burst-boundary expected/board commit values: `[5, 3, 5]`
- EventConv burst-boundary expected/board state checksum: `2`
- bitstream SHA-256: `5b6b3d64a8263b3e6b075c934bcef0d3684d576756cba600711d2918d863d1d0`
- HWH SHA-256: `9447e36cbfc687c8cf0683b6ae05671ad4ef9bb017ef78c1a0777b73d6a87ec3`
- one-spike output word: `[8193]`
- flat FC-LIF output word: `[40962]`
- EventConv output words: `[16386, 24577, 32768]`
- EventConv burst-boundary output words: `[40963, 24577, 40960]`
- flat FC-LIF counters: `pl_busy_cycles=3`, `output_drain_cycles=3`,
  `router_spike_cnt=5`, `neuron_spike_cnt=1`, `service_cycles=41`
- EventConv counters: `pl_busy_cycles=1`, `output_drain_cycles=4`,
  `router_spike_cnt=4`, `neuron_spike_cnt=3`, `service_cycles=17`
- EventConv burst-boundary counters: `pl_busy_cycles=13`,
  `output_drain_cycles=4`, `router_spike_cnt=6`, `neuron_spike_cnt=3`,
  `service_cycles=28`
- direct-path counters: AXIS input seen, router accept, router spike,
  neuron spike, output bridge event, and output bridge emit are all nonzero.

## Required Next Gate

Before stronger neural correctness claims:

1. Lift the integrated EventConv backend from fixed 3x3/2x2 shape to
   descriptor-configured shape/kernel variants.
2. Add wider destination/state-space board evidence after descriptor support.
3. Add full-state dump only if needed for debug; checksum is enough for the
   tiny zero-init correctness gate.
4. Keep latency/throughput/energy claims disabled until counters and host timing
   are recorded for the same board run.

## Verifier Command

```bash
rtk python scripts/check_verifier_gate.py
```
