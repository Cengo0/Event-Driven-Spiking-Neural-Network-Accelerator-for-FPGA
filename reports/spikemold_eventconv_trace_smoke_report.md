# SpikeMold EventConv Trace Smoke Report

Status: PYNQ-Z2 EventConv trace smokes passed

## Artifact Identity

| artifact | sha256 | bytes |
|---|---:|---:|
| bitstream | `5b6b3d64a8263b3e6b075c934bcef0d3684d576756cba600711d2918d863d1d0` | `4045700` |
| hwh | `9447e36cbfc687c8cf0683b6ae05671ad4ef9bb017ef78c1a0777b73d6a87ec3` | `525968` |

## Descriptor-capable rerun

Date: 2026-06-20

Rebuild command boundary:

```text
SPIKEMOLD_OUTPUT_BASENAME=spikemold_pynq_z2_eventconv_desc_20mhz SPIKEMOLD_PL_CLK_MHZ=20 vivado -mode batch -source hardware/scripts/rebuild_integrated.tcl
```

Descriptor run command boundary:

```text
run_spikemold_pynq_eventconv_trace_smoke.py --write-eventconv-descriptor --variant tiny
run_spikemold_pynq_eventconv_trace_smoke.py --write-eventconv-descriptor --variant burst-boundary
```

| artifact | sha256 | bytes |
|---|---:|---:|
| descriptor bitstream | `3543f15996830c68693eb8b33099cfa08ddc3787f5d153a007282aa02859894e` | `4045700` |
| descriptor hwh | `8968cfc6ea303b6364c41e0263e3caaf8278e6be15a9e3c2ee40191463a000c6` | `527620` |
| descriptor tiny JSON | `a80b244168199354d6d50e884696ba97498bd8b08618716bb59a78cd6ce7ddff` | `8163` |
| descriptor burst-boundary JSON | `00fcb17a084134dbbc500ea3574e6b247d897fc32c4d1f5df065189cd09b6655` | `8425` |

Routed timing/resource boundary:

| field | value |
|---|---:|
| setup worst slack | `33.609 ns` |
| hold worst slack | `0.020 ns` |
| Slice LUTs | `9563` |
| Slice Registers | `9054` |
| Block RAM Tile | `99` |
| DSPs | `4` |

Descriptor readback:

| field | tiny | burst-boundary |
|---|---:|---:|
| board ok | `True` | `True` |
| `EVENTCONV_SHAPE0` | `67240707` (`0x04020303`) | `67240707` (`0x04020303`) |
| `EVENTCONV_KERNEL0` | `67305985` (`0x04030201`) | `67305985` (`0x04030201`) |
| `EVENTCONV_DESC_STATUS` | `7` | `7` |
| descriptor shape supported | `True` | `True` |
| descriptor kernel runtime | `True` | `True` |
| board output words | `[16386, 24577, 32768]` | `[40963, 24577, 40960]` |
| board readout ids | `[2, 1, 0]` | `[3, 1, 0]` |
| board commit values | `[2, 3, 4]` | `[5, 3, 5]` |
| board state checksum | `1` | `2` |

Descriptor claim boundary: `EVENTCONV_KERNEL0` now drives the runtime AGU
kernel weights for the descriptor-capable bitstream. `EVENTCONV_SHAPE0` is
accepted only for the current 3x3 input, 2x2 kernel, 4-state tiny RTL
specialization. This is not an arbitrary EventConv shape board claim.

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
