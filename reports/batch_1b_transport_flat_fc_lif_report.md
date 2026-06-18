# Batch 1B Transport + Flat FC-LIF Report

Status: software transport plus PYNQ flat FC-LIF commit-value/state-checksum smoke complete

## Evidence Level

`software_transport_plus_pynq_flat_fc_lif_commit_value_state_checksum_smoke`

## Generated

- `outputs/transport/batch_1b_transport_flat_fc_lif_smoke.json`
- `reports/batch_1b_transport_flat_fc_lif_report.md`

## Smoke Results

| Gate | Result |
|---|---:|
| AXI-Lite register smoke | `True` |
| DMA loopback smoke | `True` |
| EventWord64 counter smoke | `True` |
| EventWord64 to AXIS32 lowering | `True` |
| SpikeMold flat FC-LIF smoke | `True` |
| All OK | `True` |

## EventWord64 To AXIS32 Lowering

| Field | Value |
|---|---:|
| source format | `EventWord64 input_spike` |
| target format | `AER32 direct RTL DMA0` |
| word count | `3` |
| lossless flat input semantics | `True` |
| output axis32 sha256 | `208ca20930e1573d934e83c862d208d2731e0fc50f75c2fe8fe1bc4727135724` |

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

## Board Evidence

### Direct AER32 Board Smoke

PYNQ-Z2 direct RTL AXI spike smoke was included from
`outputs/board/dma_spike_smoke_result_20260614.json`.

| Counter | Value |
|---|---:|
| board executed | `True` |
| board ok | `True` |
| AXIS input seen check | `True` |
| AXIS router accept check | `True` |
| PL busy register / AXIS seen count | `1` |
| output drain register / AXIS accept count | `1` |
| router_spike_cnt | `1` |
| neuron_spike_cnt | `1` |
| output bridge events | `1` |
| output bridge emits | `1` |
| output words | `[8193]` |

Board claim boundary:

`pynq_axi_dma0_direct_rtl_one_spike_event_to_post_spike_readback_only_no_dataset`

Bitstream SHA-256:

`5b6b3d64a8263b3e6b075c934bcef0d3684d576756cba600711d2918d863d1d0`

HWH SHA-256:

`9447e36cbfc687c8cf0683b6ae05671ad4ef9bb017ef78c1a0777b73d6a87ec3`


### EventWord64-Lowered Board Smoke

PYNQ-Z2 direct RTL AXI spike smoke accepted a SpikePress EventWord64 input from
`outputs/board/dma_spike_smoke_eventword64_result_20260614.json` and lowered it to the current direct RTL
AER32 stream.

| Counter | Value |
|---|---:|
| board executed | `True` |
| board ok | `True` |
| input EventWord64 | `2048` |
| lowered AXIS32 | `8192` |
| lossless flat input semantics | `True` |
| AXIS input seen check | `True` |
| AXIS router accept check | `True` |
| PL busy register / AXIS seen count | `1` |
| output drain register / AXIS accept count | `1` |
| router_spike_cnt | `1` |
| neuron_spike_cnt | `1` |
| output bridge events | `1` |
| output bridge emits | `1` |
| output words | `[8193]` |

Board claim boundary:

`pynq_axi_dma0_direct_rtl_one_spike_event_to_post_spike_readback_only_no_dataset`

Bitstream SHA-256:

`5b6b3d64a8263b3e6b075c934bcef0d3684d576756cba600711d2918d863d1d0`

HWH SHA-256:

`9447e36cbfc687c8cf0683b6ae05671ad4ef9bb017ef78c1a0777b73d6a87ec3`


### Tiny Flat FC-LIF Board Trace Smoke

PYNQ-Z2 direct RTL AXI spike smoke consumed the tiny flat FC-LIF SpikePress trace
from `outputs/board/flat_fc_lif_trace_smoke_result_20260614.json`. This is readout id, commit value,
and final membrane checksum readback evidence. Counters are raw diagnostics
only, not latency, throughput, frequency, or energy claims.

| Counter | Value |
|---|---:|
| board executed | `True` |
| board ok | `True` |
| input EventWord64 words | `[2048, 281475245148160, 562949953423360]` |
| lowered AXIS32 words | `[8192, 2105345, 4202496]` |
| expected readout ids | `[2]` |
| board readout ids | `[2]` |
| expected commit values | `[5]` |
| board commit values | `[5]` |
| expected output words | `[40962]` |
| board output words | `[40962]` |
| expected final state | `{'2': 3, '3': 2}` |
| expected state checksum | `5` |
| board state checksum | `5` |
| PL busy register / AXIS seen count | `3` |
| output drain register / AXIS accept count | `3` |
| router_spike_cnt | `5` |
| neuron_spike_cnt | `1` |
| output bridge events | `1` |
| output bridge emits | `1` |
| output bridge drops | `0` |
| config state checksum | `5` |
| fresh overlay loaded | `True` |
| HLS soft reset clears membrane BRAM | `False` |
| state checksum valid after soft reset alone | `False` |
| state checksum validity | `valid for fresh overlay zero-init traces and controlled membrane config writes; HLS soft reset alone does not clear membrane BRAM` |

Board claim boundary:

`pynq_axi_dma0_direct_rtl_tiny_flat_fc_lif_commit_value_state_checksum_readback`

Bitstream SHA-256:

`5b6b3d64a8263b3e6b075c934bcef0d3684d576756cba600711d2918d863d1d0`

HWH SHA-256:

`9447e36cbfc687c8cf0683b6ae05671ad4ef9bb017ef78c1a0777b73d6a87ec3`



## Next Gate

Extend to EventConv commit payload/checksum board smoke and compare the EventConv golden trace.
