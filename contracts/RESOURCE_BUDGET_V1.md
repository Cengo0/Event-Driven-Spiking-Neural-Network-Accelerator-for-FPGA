# Resource Budget V1

Status: active draft
Target: PYNQ-Z2 / Zynq-7020

## Board Constraints

- DDR3: 512 MB, 16-bit bus
- PL clock target: 125 MHz for default estimates
- DSP slices: 220
- BRAM and BRAM ports are primary constraints
- DMA/cache stability is a first-class runtime constraint

## Default Compiler Rejection Rules

Reject or pivot when:

- unbounded fanout exists
- per-event random DDR synapse fetch is required
- per-event random DDR state fetch is required
- full-neuron scan is the primary commit mechanism
- Python controls each timestep, layer, event, page, tile, or group
- expected BRAM footprint exceeds target budget
- expected output FIFO can overflow without bounded backpressure handling

## Required Resource Report Fields

- LUT estimate
- FF estimate
- BRAM estimate
- DSP estimate
- state memory bytes
- synapse/kernel memory bytes
- FIFO memory bytes
- expected DDR bytes per inference
- expected DMA calls per inference
- expected AXI-Lite commands per inference
- event/update histogram

## Initial EDNP-mini Budget

The first board-oriented primitive should fit within a small fraction of the
device:

- one flat event pipeline
- one local state RAM
- one input FIFO
- one output FIFO
- no large MAC array
- no full model stored as random DDR lookup in the inner loop

These are not final performance limits. They are the first safe compile target.

