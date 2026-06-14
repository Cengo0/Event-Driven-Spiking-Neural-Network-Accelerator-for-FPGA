# EventConv Vivado OOC Synthesis Report

Status: EventConv Vivado OOC synthesis evidence generated

## Evidence Level

`vivado_ooc_synthesis_no_board`

No board execution was run. This report does not claim bitstream, routed timing,
PYNQ-Z2 PL correctness, latency, throughput, or energy.

## Target

- toolchain: `Vivado 2025.2`
- part: `xc7z020clg400-1`
- clock period: `50.0` ns
- clock frequency: `20.0` MHz
- source script: `hardware/scripts/synth_eventconv_ooc_synthesis.tcl`

## Results

| EventConv block | RTL top | LUT | FF | BRAM tile | DSP | WNS ns | Timing met |
|---|---|---:|---:|---:|---:|---:|---:|
| eventconv_agu_c4 | `spike_conv_agu` | 143 | 172 | 0 | 0 | 38.311 | True |
| eventconv_state_update_c4 | `spike_conv_state_update` | 2354 | 2304 | 0 | 0 | 35.876 | True |
| eventconv_active_commit_c4 | `spike_conv_active_commit` | 664 | 232 | 0 | 0 | 41.202 | True |

## Aggregate

- total LUT: `3161`
- total FF: `2708`
- total BRAM tile: `0`
- total DSP: `0`
- minimum WNS: `35.876` ns
- all timing met: `True`
- all DSP zero: `True`
- all BRAM tile zero: `True`

## Claim Boundary

`eventconv_ooc_synthesis_only_no_bitstream_no_board`
