# SpikeMold Runtime Contract And Resource Report

Status: board-free runtime/resource artifacts generated

## Evidence Level

- runtime contract: `board_free_runtime_contract_no_board`
- resource report: `board_free_resource_report_with_eventconv_ooc_synthesis`

No board execution was run. This report does not claim PYNQ-Z2 PL correctness,
latency, throughput, or energy.

## Generated

- `outputs/runtime/spikemold_runtime_contract.json`
- `outputs/resource/spikemold_runtime_resource_report.json`

## Selected Backend

`spikemold_fc_eventconv`

The runtime contract exposes two SpikeMold runtime blocks:

- `flat_fc_lif`: small FC/readout path
- `eventconv_agu`: shared-kernel EventConv AGU plus near-memory state and active-set commit

## Required Runtime Invariants

- bounded job: `True`
- Python inner loop required: `False`
- random DDR inner loop: `False`
- full-neuron scan primary: `False`
- active-set commit required: `True`

## Resource Evidence

The resource report is compiler-visible. Flat FC-LIF remains contract-level
because no standalone flat FC-LIF RTL primitive exists; EventConv has Vivado OOC
synthesis evidence at 20 MHz.

| Primitive | State bytes | Kernel/weight bytes | FIFO bytes | DDR inner-loop bytes | Synthesis evidence |
|---|---:|---:|---:|---:|---|
| flat_fc_lif | `8` | `4` | `512` | `0` | contract/HLS-integrated path only |
| eventconv_agu | `128` | `9` | `512` | `0` | `outputs/resource/eventconv_ooc_synthesis_report.json` |

Both selected blocks use the minimal transport model estimate of two DMA
calls and eight AXI-Lite commands per bounded inference. This is a contract
estimate, not a board measurement.

## EventConv OOC Synthesis

The EventConv C4 RTL blocks synthesize out-of-context on
`xc7z020clg400-1` at 20 MHz with zero DSP and zero BRAM tile usage. This is not
routed implementation evidence and does not prove board execution.

## Next Gate

Build the integrated bitstream/runtime contract and run PYNQ-Z2 board smoke.
