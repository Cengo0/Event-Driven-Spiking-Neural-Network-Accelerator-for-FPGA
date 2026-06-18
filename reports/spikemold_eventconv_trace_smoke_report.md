# SpikeMold EventConv Trace Smoke Report

Status: PYNQ-Z2 EventConv trace smokes passed

## Artifact Identity

| artifact | sha256 | bytes |
|---|---:|---:|
| bitstream | `5b6b3d64a8263b3e6b075c934bcef0d3684d576756cba600711d2918d863d1d0` | `4045700` |
| hwh | `9447e36cbfc687c8cf0683b6ae05671ad4ef9bb017ef78c1a0777b73d6a87ec3` | `525968` |

## Board Results

### `tiny`

Evidence level: `pynq_board_eventconv_multi_commit_state_checksum_smoke`

Claim boundary: `pynq_axi_dma0_direct_rtl_tiny_eventconv_multi_commit_state_checksum_readback`

| field | value |
|---|---:|
| model | `batch_1c_tiny_eventconv_c4_multi_commit` |
| ok | `True` |
| EventConv backend mode | `1` |
| input axis32 words | `[16842752]` |
| expected output words | `[16386, 24577, 32768]` |
| board output words | `[16386, 24577, 32768]` |
| expected readout ids | `[2, 1, 0]` |
| board readout ids | `[2, 1, 0]` |
| expected commit values | `[2, 3, 4]` |
| board commit values | `[2, 3, 4]` |
| expected state checksum | `1` |
| board state checksum | `1` |
| generated EventConv updates | `4` |
| active commit reads | `4` |
| commit emits | `3` |
| output bridge drops | `0` |
| active neurons after commit | `1` |

### `burst-boundary`

Evidence level: `pynq_board_eventconv_burst_boundary_state_checksum_smoke`

Claim boundary: `pynq_axi_dma0_direct_rtl_eventconv_burst_boundary_state_checksum_readback`

| field | value |
|---|---:|
| model | `batch_1c_eventconv_c4_burst_boundary` |
| ok | `True` |
| EventConv backend mode | `1` |
| input axis32 words | `[16842752, 33685504, 0]` |
| expected output words | `[40963, 24577, 40960]` |
| board output words | `[40963, 24577, 40960]` |
| expected readout ids | `[3, 1, 0]` |
| board readout ids | `[3, 1, 0]` |
| expected commit values | `[5, 3, 5]` |
| board commit values | `[5, 3, 5]` |
| expected state checksum | `2` |
| board state checksum | `2` |
| generated EventConv updates | `6` |
| active commit reads | `4` |
| commit emits | `3` |
| output bridge drops | `0` |
| active neurons after commit | `1` |


## Boundary

These are fixed-shape EventConv AGU/state/active-commit board smokes. The
`tiny` case proves multi-commit packet readback and state checksum readback.
The `burst-boundary` case proves one DMA packet can carry multiple EventConv
input events and boundary coordinates skip invalid taps before active-set
commit. They are not latency, throughput, energy, dataset correctness, or full
ConvSNN proof.

Next: lift the integrated EventConv backend toward configurable shape/kernel
descriptors, then compare larger golden trace families on board.
