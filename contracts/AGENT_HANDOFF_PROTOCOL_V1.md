# Agent Handoff Protocol V1

Status: active draft

## Main Orchestrator

Responsibilities:

- keep contracts coherent
- prevent semantic drift
- approve or reject architecture candidates
- keep evidence levels separate
- prevent CIFAR/full-network work from preceding primitive gates

## Subagent A: Software Foundation

Owns:

- minimal SpikePress API
- integer golden simulator
- event budget simulator
- trace exporter
- architecture-neutral trace generator
- artifact roundtrip tests

Produces:

- `golden_traces/v1/`
- `outputs/event_budget/recommended_flat_fc_lif_config.json`
- `reports/batch_1a_software_foundation_report.md`

## Subagent B: Transport + Flat FC-LIF

Owns:

- AXI-Lite smoke
- DMA loopback
- EventWord64 counter
- SpikeMold flat FC-LIF path
- minimal PYNQ runtime

Produces:

- `reports/batch_1b_transport_flat_fc_lif_report.md`

## Subagent C: EventConv Primitive

Owns:

- trace-locked tiny EventConv case
- AGU-only update generation
- AGU plus state update
- AGU plus active-set commit
- scale-up only after tiny trace passes

Produces:

- `reports/batch_1c_eventconv_primitive_report.md`

## Subagent D: Verifier

Owns:

- contract checks
- trace compliance checks
- architecture policy checks
- forbidden failure mode checks

Produces:

- `reports/verifier_gate_review.md`

## Subagent E: Architecture Explorer

Owns:

- coregroup simulator experiments
- page/block sparse simulator experiments
- tile/micro-batch estimates
- HLS C-sim microbenchmarks when useful

Produces:

- `reports/architecture_selection_v1.md`

## Handoff Rule

Every handoff must name:

- files changed
- traces used
- tests run
- evidence level reached
- blocked items
