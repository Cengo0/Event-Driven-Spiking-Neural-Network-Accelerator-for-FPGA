# Architecture Selection V1

Status: board-free selection gate passed

## Evidence Level

`board_free_architecture_selection_no_board`

No board execution was run. This report does not claim PYNQ-Z2 PL correctness,
latency, throughput, or energy. Resource and performance values below are
analytic or simulator-bound estimates until Vivado synthesis or board counters
replace them.

## 1. Candidates Tested

| Candidate | Pattern | Evidence | Gate |
|---|---|---|---:|
| A flat EDNP-mini event pipeline | flat event/update/state/readout | Batch 1B software transport smoke | PASS |
| D shared-kernel EventConv AGU | AGU plus state plus active-set commit | Batch 1C C0-C4 RTL xsim | PASS |
| B coregroup partition | local state plus router | Batch 1X board-free trace replay sandbox | DEFER |
| C page/block sparse execution | page/block sparse descriptor path | Batch 1X board-free trace replay sandbox | DEFER |
| E hybrid backend | flat FC plus EventConv, later coregroup/page as needed | selected staging composition | WINNER |

## 2. Trace Version Used

| Trace | Schema | Purpose |
|---|---|---|
| `golden_traces/v1/fc_lif_tiny_v1.json` | `spikemold.ednp_trace.v1` | flat FC-LIF readout correctness |
| `golden_traces/v1/eventconv_agu_c0_tiny_v1.json` | `spikemold.ednp_trace.v1` | trace-locked tiny EventConv AGU correctness |
| `golden_traces/v1/eventconv_8x8_tiny_v1.json` | `spikemold.ednp_trace.v1` | signed 3x3 EventConv scale-up correctness |

## 3. Workloads Used

| Workload | Inputs | Updates | Active | Commits | Evidence |
|---|---:|---:|---:|---:|---|
| EDNP-mini FC-LIF | 3 | 5 | 2 | 1 | `outputs/transport/batch_1b_transport_ednp_mini_smoke.json` |
| EventConv C0 tiny | 1 | 4 | 4 | 0 | `scripts/check_batch1c_eventconv.py` |
| EventConv C4 scale | 2 | 12 | 12 | 0 | `tb_spike_conv_c4_scaleup`: 46 PASS, 0 FAIL |

## Correctness Table

| Candidate | trace_match_rate | readout_match | state_checksum_match | Result |
|---|---:|---:|---:|---:|
| A flat EDNP-mini event pipeline | 1.0 | true | true | PASS |
| D shared-kernel EventConv AGU | 1.0 | true | true | PASS |
| B coregroup partition | 1.0 in Batch 1X sandbox | true | true | DEFER |
| C page/block sparse execution | 1.0 in Batch 1X sandbox | true | true | DEFER |
| E hybrid backend | 1.0 on selected components | true on selected components | true on selected components | WINNER |

## 4. Resource Estimate Table

These are pre-synthesis estimates. They are fit checks, not routed utilization.

| Candidate | LUT estimate | FF estimate | BRAM estimate | DSP estimate | FIFO memory | max clock estimate |
|---|---:|---:|---:|---:|---:|---:|
| A flat EDNP-mini event pipeline | < 1000 | < 1000 | 1-2 BRAM | 0 | <= 512 B | 125 MHz target, not routed |
| D shared-kernel EventConv AGU C4 | < 1500 | < 1200 | 1-2 BRAM | 0 | <= 512 B | 125 MHz target, xsim only |
| B coregroup partition | < 1300 | < 1100 | <= 2 BRAM | 0 | <= 2048 B | board-free estimate |
| C page/block sparse execution | < 1000 | < 900 | <= 3 BRAM | 0 | page FIFO + 8 KiB page buffer | board-free estimate |
| E hybrid backend | sum of A + D per deployed layer | sum of A + D per deployed layer | local state plus small kernel memory | 0 expected | bounded per primitive | 125 MHz target, needs synth |

## 5. Performance Estimate Table

Cycle estimates are board-free. `cycle_count` for EDNP-mini is from the
software transport smoke model. EventConv values are xsim-bounded by the
testbench waits, not measured PL performance.

| Candidate | cycles per input event | cycles per generated update | cycles per active commit | maximum supported event count | stall count |
|---|---:|---:|---:|---:|---:|
| A flat EDNP-mini event pipeline | 8 model cycles / 3 inputs | 8 model cycles / 5 updates | 8 model cycles / 1 output | 1024 by current budget | 0 in smoke |
| D shared-kernel EventConv AGU C4 | <= 256 cycles / 2 inputs in TB | <= 256 cycles / 12 updates in TB | <= 128 cycles / 12 active in TB | 1024 by current budget, 64-state TB | 0 observed in always-ready TB |
| B coregroup partition | 128 cycles / 5 inputs in sandbox | 128 cycles / 17 updates in sandbox | active-set only in sandbox | 256 by local FIFO estimate | 0 estimated |
| C page/block sparse execution | 177 cycles / 5 inputs in sandbox | 177 cycles / 17 updates in sandbox | active-set only in sandbox | 256 updates per page | 0 estimated |
| E hybrid backend | component-dependent | component-dependent | active-set only for selected primitives | compiler budget constrained | must be measured before board claim |

## Memory Table

| Candidate | state reads | state writes | DDR bursts | DDR bytes | BRAM bytes |
|---|---:|---:|---:|---:|---:|
| A flat EDNP-mini event pipeline | 5 | 6 | 0 inner-loop | 0 inner-loop | small local state/FIFO |
| D shared-kernel EventConv AGU C4 | 12 | 12 | 0 inner-loop | 0 inner-loop | 64 states, active IDs, 3x3 kernel |
| B coregroup partition | 17 | 18 | 0 inner-loop | 0 inner-loop | 3072 B estimated |
| C page/block sparse execution | 17 | 18 | 4 burst transfers estimated | 0 inner-loop, 264 B burst traffic | 8704 B estimated |
| E hybrid backend | trace-dependent | trace-dependent | 0 inner-loop required | 0 inner-loop required | bounded per selected primitive |

## Resource Budget Field Table

| Field | A flat EDNP-mini event pipeline | D shared-kernel EventConv AGU C4 |
|---|---:|---:|
| state memory bytes | <= 2048 B by current 512 active / 32-bit budget | 128 B state plus 128 B active IDs in C4 TB |
| synapse/kernel memory bytes | 6 B for tiny FC-LIF trace weights | 9 B signed 3x3 kernel |
| FIFO memory bytes | <= 512 B estimate | <= 512 B estimate |
| expected DDR bytes per inference | 0 inner-loop DDR bytes | 0 inner-loop DDR bytes |
| expected DMA calls per inference | 2 in software transport smoke | not board-run; runtime ABI next |
| expected AXI-Lite commands per inference | 8 in software transport smoke | not board-run; runtime ABI next |
| event/update histogram | `outputs/event_budget/recommended_ednp_mini_config.json` | `outputs/event_budget/recommended_ednp_mini_config.json` |

## 6. Runtime Complexity Table

| Candidate | DMA calls per inference | AXI-Lite commands per inference | Python calls per inference | Runtime risk |
|---|---:|---:|---:|---|
| A flat EDNP-mini event pipeline | 2 in smoke | 8 in smoke | 0 inner-loop | board runtime still needed |
| D shared-kernel EventConv AGU | not board-run | not board-run | 0 inner-loop by contract | needs runtime wrapper |
| B coregroup partition | 2 estimated | 8 estimated | 0 inner-loop | router/commit complexity |
| C page/block sparse execution | 6 estimated | 8 estimated | 0 inner-loop | page overhead can dominate |
| E hybrid backend | component-dependent | component-dependent | 0 inner-loop required | compiler must choose primitive |

## 7. Winner

Winner for next implementation stage: **E hybrid backend**, restricted to the
two proven components:

- A flat EDNP-mini path for small FC/readout workloads
- D shared-kernel EventConv AGU plus near-memory state plus active-set commit
  for convolutional event workloads

This selection preserves the contribution claim: SpikePress can produce integer
golden traces and SpikeMold can run event-triggered primitives without a Python
inner loop, random inner-loop DDR fetch, or full-neuron scan as the primary
mode.

## 8. Rejected Candidates And Why

| Candidate | Decision | Reason |
|---|---|---|
| B coregroup partition | DEFER | Batch 1X board-free trace replay passes, but no HLS/board resource or timing evidence yet. |
| C page/block sparse execution | DEFER | Batch 1X board-free trace replay and burst estimate pass, but page overhead has no HLS/board evidence yet. |
| Full hybrid with page/coregroup | REJECT for current stage | Would mix unproven patterns into the mainline before primitive gates and report evidence exist. |

No architecture name is banned. Deferred candidates can return when they pass
the same trace correctness, resource, performance, memory, and runtime tables.

## Probation And Failure-Mode Checks

| Check | Status | Evidence |
|---|---:|---|
| event-triggered semantics | PASS | explicit input events, update stream, and active commit |
| golden trace correctness | PASS | `trace_match_rate = 1.0` for selected components |
| no Python inner loop | PASS | `python_inner_loop_steps = 0` in current traces/budget |
| no random DDR state/synapse inner loop | PASS | `ddr_bytes_inner_loop = 0` in current traces/budget |
| bounded BRAM footprint | PASS for current tiny gates | local state/kernel/FIFO estimates above |
| cycle estimate | PARTIAL | software smoke model and xsim-bounded waits only |
| explicit pivot rules | PASS | deferred candidates require same tables before selection |

Pivot rules:

- If `trace_match_rate < 1.0`, reject candidate.
- If Python controls timestep, layer, event, page, tile, or group inner loop,
  reject candidate.
- If random DDR state or synapse fetch appears in the critical path, reject
  candidate.
- If full-neuron scan becomes the primary commit mode, reject candidate.
- If Vivado synthesis or board counters exceed PYNQ-Z2 resource/runtime budget,
  pivot to smaller core/local-state partition or keep candidate in Batch 1X.

## 9. Recommended Next Implementation Stage

1. Add a board-free runtime contract for the selected FC/EventConv primitives.
2. Generate compiler-visible resource reports for FC-LIF and EventConv artifacts.
3. Keep Batch 1X sandbox artifacts for coregroup/page/tile probation without
   switching the mainline.
4. Run Vivado synthesis for the selected RTL primitives and replace analytic
   estimates with utilization and timing reports.
5. Add PYNQ-Z2 board smoke only after the bitstream/runtime contract is fixed.

## Batch 1X Sandbox Update

`outputs/architecture_sandbox/batch_1x_architecture_sandbox.json` adds
board-free trace replay, resource estimates, performance estimates, memory
estimates, runtime estimates, and pivot rules for:

- `coregroup_2x64`
- `page_block_256_updates`
- `tile_microbatch_4x4`

All three candidates preserve `trace_match_rate = 1.0`, keep
`python_calls_per_inference = 0`, keep `ddr_bytes_inner_loop = 0`, and keep
`mainline_switch_recommended = False`. This upgrades B/C/tile from unevaluated
to probationary board-free candidates only. It does not justify replacing the
selected SpikeMold FC/EventConv runtime mainline.
