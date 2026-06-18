# SpikeMold PYNQ-Z2 Flat FC-LIF Trace Smoke Report

Status: PYNQ-Z2 tiny flat FC-LIF trace smoke passed

## Evidence Level

`pynq_board_flat_fc_lif_commit_value_state_checksum_smoke`

This is a board execution result. It proves the current direct RTL AXI DMA path
can consume three SpikePress EventWord64-lowered input spikes, route five
synaptic updates, and emit the expected readout spike id and commit value for
the tiny flat FC-LIF trace. This is commit value readback plus final membrane
checksum readback evidence. Full per-neuron state dump remains outside this
smoke. Counters below are raw board diagnostics only; they are not latency,
throughput, frequency, or energy claims.

## Claim Boundary

`pynq_axi_dma0_direct_rtl_tiny_flat_fc_lif_commit_value_state_checksum_readback`

## Trace

| Field | Value |
|---|---:|
| input spikes | `[{'payload': 1, 'src_id': 0, 'tick': 0}, {'payload': 1, 'src_id': 1, 'tick': 1}, {'payload': 1, 'src_id': 0, 'tick': 2}]` |
| EventWord64 words | `[2048, 281475245148160, 562949953423360]` |
| lowered AXIS32 words | `[8192, 2105345, 4202496]` |
| expected generated updates | `5` |
| expected readout ids | `[2]` |
| board readout ids | `[2]` |
| expected commit values | `[5]` |
| board commit values | `[5]` |
| expected output words | `[40962]` |
| board output words | `[40962]` |
| expected final state | `{'2': 3, '3': 2}` |
| expected state checksum | `5` |
| board state checksum | `5` |

## Counters

| Counter | Value |
|---|---:|
| PL busy register / AXIS seen count | `3` |
| output drain register / AXIS accept count | `3` |
| router_spike_cnt | `5` |
| neuron_spike_cnt | `1` |
| output bridge events | `1` |
| output bridge emits | `1` |
| output bridge drops | `0` |
| service cycles | `41` |
| throughput cycles | `25` |

## State Reset Boundary

- fresh overlay loaded: `True`
- membrane state zeroed by: `bitstream initialization on Overlay load`
- HLS soft reset clears membrane BRAM: `False`
- state checksum valid after soft reset alone: `False`
- state checksum validity: `valid for fresh overlay zero-init traces and controlled membrane config writes; HLS soft reset alone does not clear membrane BRAM`

## Artifacts

| Artifact | Size bytes | SHA-256 |
|---|---:|---|
| `spikemold_pynq_z2_eventconv_20mhz.bit` | `4045700` | `5b6b3d64a8263b3e6b075c934bcef0d3684d576756cba600711d2918d863d1d0` |
| `spikemold_pynq_z2_eventconv_20mhz.hwh` | `525968` | `9447e36cbfc687c8cf0683b6ae05671ad4ef9bb017ef78c1a0777b73d6a87ec3` |

## Next Gate

Extend the board path to EventConv commit payloads/checksum, then compare the
EventConv SpikePress golden trace on PYNQ-Z2.
