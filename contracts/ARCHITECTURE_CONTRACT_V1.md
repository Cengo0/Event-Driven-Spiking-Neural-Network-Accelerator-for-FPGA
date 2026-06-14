# SpikePress + SpikeMold-EDNP Architecture Contract V1

Status: active draft
Target: PYNQ-Z2 / Zynq-7020

## Purpose

This contract defines the execution boundary for the first SpikeMold-EDNP
backend. It is architecture-neutral. Flat pipelines, coregroups, pages, tiles,
block-sparse layouts, and shared-kernel EventConv AGUs are allowed only when
they preserve the trace semantics and pass the same evidence gates.

## Required Execution Semantics

- Input is an ordered stream of spike events.
- Hardware-visible execution is event-triggered: no input event means no
  synaptic update work for that event slot.
- Synaptic updates produce explicit update records before state commit.
- Neuron state update is near-memory read-modify-write.
- Readout uses active-set commit, not a full-neuron scan as the primary mode.
- Board/runtime control submits bounded jobs, not Python-controlled inner loops.
- Trace output must be deterministic for fixed artifacts and fixed inputs.

## Backend Boundary

The SpikeMold-EDNP backend consumes:

- target specification
- integer model artifact
- event trace or encoded spike input
- resource budget

The backend produces:

- readout events or logits
- execution counters
- trace hashes
- failure reason when rejected

## Correctness Gate

For deterministic tiny traces:

- `trace_match_rate` must be `1.0`.
- readout events must match integer golden output exactly.
- final state checksum must match integer golden output exactly.
- no silent semantic change is allowed to satisfy a resource target.

## Runtime Gate

One inference must be executable as a bounded hardware/runtime job. The host may
launch jobs and drain outputs, but the host must not iterate over every timestep,
layer, spike, page, tile, or neuron as the primary execution mechanism.

## Evidence Levels

Keep these evidence levels separate:

- CPU/GPU SpikePress simulation
- integer golden trace
- HLS C-sim trace match
- RTL simulation trace match
- packaged bit/HWH readback
- PYNQ-Z2 PL execution with board-captured output

Only the last item supports board execution claims.
