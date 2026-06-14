# SpikeMold PYNQ-Z2 Board Smoke Report

Status: PYNQ-Z2 HLS register smoke passed

## Evidence Level

`pynq_board_hls_register_smoke`

This is a board execution result. It proves overlay load, HLS AXI-Lite register
access, `ap_start`/`ap_done`, and `version_reg` readback for the routed
SpikeMold bitstream. It does not claim DMA streaming correctness, neural output
correctness, latency, throughput, energy, or dataset accuracy.

## Board Result

| Check | Result |
|---|---:|
| board executed | `True` |
| ok | `True` |
| IP name | `spikemold_top_hls_0` |
| `ap_done` | `True` |
| version matches | `True` |
| expected version | `0x20260221` |
| read version | `0x20260221` |
| normal status_reg | `1` |
| normal spike_count_reg | `0` |
| normal weight_sum_reg | `0` |
| normal poll count | `1` |
| reset poll count | `1019` |

## Overlay

Available IPs:

```text
axi_dma_0
axi_dma_1
processing_system7_0
spikemold_config_regs_0
spikemold_top_hls_0
```

## Artifacts

| Artifact | Size bytes | SHA-256 |
|---|---:|---|
| `spikemold_pynq_z2.bit` | `4045700` | `034f62803060e81e37a98f459c8433a358183e4485b84ba12d8585016b3eb418` |
| `spikemold_pynq_z2.hwh` | `518428` | `033a777f37c04e09fb36772ae62c05922a67c43d35a736a80c66a1b63ac8cad1` |

## Claim Boundary

`pynq_overlay_load_hls_register_ap_done_version_only_no_dma_no_dataset`

## Next Gate

DMA weight stream smoke is recorded separately in
`reports/spikemold_dma_weight_smoke_report.md`. Next gate is `axi_dma_0`
spike-stream smoke and SpikePress golden trace comparison.
