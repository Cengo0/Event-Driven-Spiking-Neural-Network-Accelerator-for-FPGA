# SpikePress + SpikeMold Architecture

## Boundary

SpikePress produces deterministic integer artifacts and traces. SpikeMold
consumes those artifacts through a bounded hardware runtime.

## Default SpikeMold Path

```text
input events
  -> update generation
  -> local state read-modify-write
  -> active-set commit
  -> readout events
```

The mainline is inference-only for now.

## Allowed Patterns

Page, tile, coregroup, block-sparse, and shared-kernel EventConv AGU structures
are allowed only when they satisfy the contract in
`contracts/ARCHITECTURE_PATTERN_POLICY_V1.md`.

## Forbidden Runtime Failure Modes

- Python-controlled event loop
- Python-controlled timestep loop
- random DDR state or synapse access in the critical path
- unbounded fanout with no compiler rejection
- full-neuron scan as primary mode
- silent semantic changes to pass resource limits

## PYNQ-Z2 Reality

Primary constraints are BRAM capacity, BRAM port bandwidth, state RMW pressure,
FIFO pressure, DMA/cache stability, and HLS timing. DSP count is not the first
constraint for the current add-only event path.
