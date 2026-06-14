# Architecture Pattern Policy V1

Status: active

## Rule

Do not ban architecture names. Ban failure modes.

The following patterns are allowed on probation:

- page
- tile
- coregroup
- core-local memory
- block-sparse layout
- micro-batching
- event pages
- synapse pages
- activation tiles
- shared-kernel EventConv AGU

## Probation Requirements

An allowed pattern must prove:

- event-triggered semantics
- golden trace correctness
- no Python inner loop
- no random DDR state or synapse access in the critical inner loop
- bounded BRAM footprint
- compile-time resource report
- measurable HLS C-sim or board cycle estimate
- explicit failure and pivot rules

## Forbidden Failure Modes

- Python-controlled event loop
- Python-controlled timestep loop
- Python-controlled layer loop
- random DDR state paging in the critical path
- random DDR synapse fetch per event
- unbounded fanout with no compiler gate
- full-neuron scan every timestep as the primary mode
- silent semantic changes
- legacy code reuse without trace compliance

## Legacy Reuse

Legacy code may be reused only when:

- it is wrapped behind the V1 trace contract
- it passes the same tests as new code
- it does not import old runtime assumptions
- a reuse justification is written in the relevant report

