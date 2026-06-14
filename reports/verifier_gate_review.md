# Verifier Gate Review

Status: board-free verifier gate passed
Date: 2026-06-14

## Evidence Level

`board_free_verifier_gate_no_board`

No board execution was run. This review does not claim PYNQ-Z2 PL correctness,
latency, throughput, energy, routed timing, or dataset accuracy.

## Scope

This review checks the current SpikePress + SpikeMold v3.6 board-free
implementation slice:

- Batch 0 contract freeze
- Batch 1A SpikePress software foundation and architecture-neutral traces
- Batch 1B transport and SpikeMold-mini software smoke artifacts
- Batch 1C EventConv primitive artifacts
- Batch 1X architecture exploration sandbox
- selected FC/EventConv runtime contract and resource report
- PYNQ one-shot runtime API and CLI entrypoint

## Gate Results

| Gate | Result | Evidence |
|---|---:|---|
| contracts exist | PASS | `contracts/*.md` |
| page/tile/coregroup policy is architecture-open | PASS | `contracts/ARCHITECTURE_PATTERN_POLICY_V1.md` |
| trace schema and hashes match | PASS | `golden_traces/v1/*.json` |
| event budget passes | PASS | `outputs/event_budget/recommended_spikemold_mini_config.json` |
| Python inner-loop count is zero | PASS | trace counters and runtime contract |
| inner-loop DDR bytes are zero | PASS | trace counters and runtime/resource reports |
| SpikeMold-mini trace/readout/state match | PASS | `outputs/transport/batch_1b_transport_spikemold_mini_smoke.json` |
| EventConv C0-C5 artifacts present | PASS | `reports/batch_1c_eventconv_primitive_report.md` |
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

## Required Next Gate

PYNQ one-shot runtime API is present, but was not executed on the board in this
gate. Before board claims:

1. Remove or fully tie off remaining RTL router/coregroup compatibility residue.
2. Run Vivado synthesis for selected FC/EventConv primitives.
3. Replace analytic LUT/FF/BRAM/timing estimates with routed reports.
4. Run `scripts/run_spikemold_pynq_one_shot.py` on PYNQ-Z2 and record board
   JSON counters.

## Verifier Command

```bash
python scripts/check_verifier_gate.py
```
