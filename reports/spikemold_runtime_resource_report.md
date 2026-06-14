# SpikeMold Runtime Contract And Resource Report

Status: board-free runtime/resource artifacts generated

## Evidence Level

`board_free_runtime_contract_no_board`

No board execution was run. This report does not claim PYNQ-Z2 PL correctness,
latency, throughput, or energy.

## Generated

- `outputs/runtime/spikemold_runtime_contract.json`
- `outputs/resource/spikemold_runtime_resource_report.json`

## Selected Backend

`spikemold_fc_eventconv`

The runtime contract exposes two selected primitives:

- `flat_fc_lif`: small FC/readout path
- `eventconv_agu`: shared-kernel EventConv AGU plus near-memory state and active-set commit

## Required Runtime Invariants

- bounded job: `True`
- Python inner loop required: `False`
- random DDR inner loop: `False`
- full-neuron scan primary: `False`
- active-set commit required: `True`

## Resource Evidence

The resource report is a compiler-visible pre-synthesis estimate. Vivado synthesis must replace LUT/FF/BRAM/timing estimates before board claims.

| Primitive | State bytes | Kernel/weight bytes | FIFO bytes | DDR inner-loop bytes |
|---|---:|---:|---:|---:|
| flat_fc_lif | `8` | `4` | `512` | `0` |
| eventconv_agu | `128` | `9` | `512` | `0` |

Both selected primitives use the minimal transport model estimate of two DMA
calls and eight AXI-Lite commands per bounded inference. This is a contract
estimate, not a board measurement.

## Next Gate

Run Vivado synthesis for the selected primitives and replace analytic resource
estimates with utilization and timing reports.
