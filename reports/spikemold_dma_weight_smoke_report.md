# SpikeMold PYNQ-Z2 DMA Weight Smoke Report

Status: PYNQ-Z2 AXI DMA weight stream smoke passed

## Evidence Level

`pynq_board_dma_weight_stream_smoke`

This is a board execution result. It proves `axi_dma_1` MM2S weight-load stream,
HLS weight-memory write, `axi_dma_1` S2MM checkpoint readback stream, TLAST
completion, and register readback for one valid SpikePress connection. It does
not claim spike input/output correctness, neural output correctness, latency,
throughput, energy, or dataset accuracy.

## Board Result

| Check | Result |
|---|---:|
| board executed | `True` |
| ok | `True` |
| IP name | `spikemold_top_hls_0` |
| DMA name | `axi_dma_1` |
| reset `ap_done` | `True` |
| load `ap_done` | `True` |
| checkpoint `ap_done` | `True` |
| version matches | `True` |
| first checkpoint index zero | `True` |
| first checkpoint weight matches | `True` |

## Weight Load

- pre_id: `512`
- post_id: `0`
- weight: `7`
- packed input word: `117441024`

## Checkpoint Readback

- requested words: `4`
- output words: `[7340032, 1, 2, 3]`
- expected first word: `7340032`
- decoded first weight: `7`
- output words sha256: `568aeb24a778d89d0993f1470245c1626193e9085d10eeee086e8d44af54e245`

Run counters/register readback:

- reset polls: `967`
- load polls: `1`
- checkpoint polls: `1`
- checkpoint status_reg: `129`
- checkpoint weight_sum_reg: `7`

## Artifacts

| Artifact | Size bytes | SHA-256 |
|---|---:|---|
| `spikemold_pynq_z2.bit` | `4045700` | `034f62803060e81e37a98f459c8433a358183e4485b84ba12d8585016b3eb418` |
| `spikemold_pynq_z2.hwh` | `518428` | `033a777f37c04e09fb36772ae62c05922a67c43d35a736a80c66a1b63ac8cad1` |

## Claim Boundary

`pynq_axi_dma1_weight_load_checkpoint_readback_only_no_neural_dataset`

## Next Gate

Run `axi_dma_0` spike-stream smoke and compare board spike/readout words with
the SpikePress golden trace contract.
