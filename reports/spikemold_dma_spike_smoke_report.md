# SpikeMold PYNQ-Z2 DMA Spike Smoke Report

Status: PYNQ-Z2 AXI DMA spike stream smoke passed

## Evidence Level

`pynq_board_dma_spike_stream_smoke`

This is a board execution result. It proves `axi_dma_0` MM2S direct RTL spike
input, minimal RTL router programming, LIF neuron firing, `axi_dma_0` S2MM spike
readback with TLAST, and register/counter readback for one event. It does not
claim SpikePress EventWord64 parity, dataset accuracy, latency, throughput, or
energy.

## Board Result

| Check | Result |
|---|---:|
| board executed | `True` |
| ok | `True` |
| IP name | `spikemold_top_hls_0` |
| DMA name | `axi_dma_0` |
| config IP name | `spikemold_config_regs_0` |
| reset `ap_done` | `True` |
| spike `ap_done` | `True` |
| HLS version matches | `True` |
| config version matches | `True` |
| AXIS input seen nonzero | `True` |
| AXIS router accept nonzero | `True` |
| router spike count nonzero | `True` |
| neuron spike count nonzero | `True` |
| output ID matches | `True` |
| output commit value matches | `True` |
| output word matches | `True` |
| output reserved top3 zero | `True` |

Diagnostic checks:

- output event count nonzero: `True`
- output emit count nonzero: `True`

## Route Config

- source_id: `0`
- dest_id: `1`
- route_weight: `1`
- threshold: `1`
- route_addr: `0`
- route_word: `201588737`
- count_addr: `16777216`

## Spike Words

- input word: `8192`
- input decoded: `{'id': 0, 'timestamp': 0, 'weight_i8': 1, 'weight_u8': 1, 'word': 8192}`
- input words sha256: `5e4af92d1b61923dfb73d2bb1f11c68b0be4b47ac2e0ed8390962c74df7aa6c1`
- output words: `[8193]`
- output decoded: `{'commit_value_i16': 1, 'commit_value_u16': 1, 'id': 1, 'reserved_top3': 0, 'word': 8193}`
- output words sha256: `a96c64c706ce3d108405690fecacbfa6f4754a0f706ace6562ef811deb13ed0c`

Run counters/register readback:

- reset polls: `995`
- spike polls: `12`
- spike status_reg: `9`
- HLS spike_count_reg: `0`
- router_spike_cnt: `1`
- neuron_spike_cnt: `1`
- throughput cycles: `12`
- service cycles: `11`
- output bridge status: `18432`
- output bridge events: `1`
- output bridge emits: `1`
- PL busy cycles: `1`
- output drain cycles: `1`

EventWord64 lowering:

`None`


## EventWord64-Lowered Board Result

Result JSON:

`outputs/board/dma_spike_smoke_eventword64_result_20260614.json`

| Check | Result |
|---|---:|
| board executed | `True` |
| ok | `True` |
| input EventWord64 | `2048` |
| lowered AXIS32 | `8192` |
| lossless flat input semantics | `True` |
| output words | `[8193]` |
| router_spike_cnt | `1` |
| neuron_spike_cnt | `1` |
| PL busy cycles | `1` |
| output drain cycles | `1` |
| service cycles | `11` |
| throughput cycles | `12` |


## Artifacts

| Artifact | Size bytes | SHA-256 |
|---|---:|---|
| `spikemold_pynq_z2_eventconv_20mhz.bit` | `4045700` | `5b6b3d64a8263b3e6b075c934bcef0d3684d576756cba600711d2918d863d1d0` |
| `spikemold_pynq_z2_eventconv_20mhz.hwh` | `525968` | `9447e36cbfc687c8cf0683b6ae05671ad4ef9bb017ef78c1a0777b73d6a87ec3` |

## Claim Boundary

`pynq_axi_dma0_direct_rtl_one_spike_event_to_post_spike_readback_only_no_dataset`

## Next Gate

Tiny flat FC-LIF commit-value readback is now covered by `reports/spikemold_flat_fc_lif_trace_smoke_report.md`; next expose final state readback or extend to EventConv commit payloads.
