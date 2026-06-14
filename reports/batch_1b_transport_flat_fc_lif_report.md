# Batch 1B Transport + Flat FC-LIF Report

Status: software transport smoke generated

## Evidence Level

`software_transport_smoke_no_board`

Board execution was not run. This report does not claim PYNQ-Z2 PL correctness,
latency, throughput, or energy.

## Generated

- `outputs/transport/batch_1b_transport_flat_fc_lif_smoke.json`
- `reports/batch_1b_transport_flat_fc_lif_report.md`

## Smoke Results

| Gate | Result |
|---|---:|
| AXI-Lite register smoke | `True` |
| DMA loopback smoke | `True` |
| EventWord64 counter smoke | `True` |
| SpikeMold flat FC-LIF smoke | `True` |
| All OK | `True` |

## Flat FC-LIF Counters

| Counter | Value |
|---|---:|
| input_event_count | `3` |
| update_count | `5` |
| active_count | `2` |
| output_words | `1` |
| dma_calls | `2` |
| axi_lite_commands | `8` |
| python_inner_loop_steps | `0` |

## Runtime Assumptions

- bounded job: `True`
- Python inner loop required: `False`
- random DDR inner loop: `False`
- full-neuron scan primary: `False`

## Next Gate

Replace software transport smoke with real PYNQ-Z2 board-captured output and
register counters before making board execution or performance claims.
