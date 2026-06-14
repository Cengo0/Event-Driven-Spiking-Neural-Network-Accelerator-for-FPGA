# Batch 1X Architecture Sandbox Report

Status: board-free architecture sandbox passed

## Evidence Level

`board_free_architecture_sandbox_no_board`

No board execution, routed implementation, latency, throughput, or energy claim
is made here. This sandbox replays existing golden traces and estimates resource,
memory, runtime, and cycle cost for probationary architectural patterns.

## Traces

- `golden_traces/v1/fc_lif_tiny_v1.json`
- `golden_traces/v1/eventconv_8x8_tiny_v1.json`

## Candidate Summary

| Candidate | Pattern | BRAM est | DSP est | DDR inner-loop bytes | Cycle estimate | Python calls | Gate |
|---|---|---:|---:|---:|---:|---:|---|
| `coregroup_2x64` | `coregroup_partition` | `2` | `0` | `0` | `128` | `0` | PASS |
| `page_block_256_updates` | `page_block_sparse_execution` | `3` | `0` | `0` | `177` | `0` | PASS |
| `tile_microbatch_4x4` | `tile_microbatch` | `2` | `0` | `0` | `151` | `0` | PASS |

## Probation Checks

All sandbox candidates preserve:

- trace_match_rate: `1.0`
- readout_match: `True`
- state_checksum_match: `True`
- python_inner_loop_required: `False`
- random_ddr_inner_loop: `False`
- full_neuron_scan_primary: `False`
- silent_semantic_change: `False`

## Decision

`mainline_switch_recommended`: `False`

Reason: sandbox evidence is board-free; selected SpikeMold FC/EventConv runtime remains mainline

The selected SpikeMold FC/EventConv runtime remains the mainline. Coregroup,
page/block, and tile/micro-batch patterns stay allowed as probationary patterns,
but this board-free sandbox is not enough to replace the mainline.
