# SpikeMold HLS/Vivado Build Evidence Report

Status: HLS C-sim, HLS synthesis/IP package, and integrated Vivado route timing passed

## Evidence Level

`hls_csim_hls_synth_vivado_routed_no_board`

No board execution was run. This report does not claim PYNQ-Z2 PL correctness,
latency, throughput, energy, or dataset accuracy.

## HLS Results

| Gate | Result | Evidence |
|---|---:|---|
| HLS C-sim | `True` | `hardware/hls/hls_csim_output/hls_csim_output.hlsrun_csim_summary` |
| HLS synthesis/package | `True` | `hardware/hls/hls_output/hls/syn/report/csynth.rpt` |
| HLS timing estimate meets 12.5 ns | `True` | estimated `7.984` ns, Fmax `125.25` MHz |
| HLS DSP usage | `0` | add-only top-level HLS estimate |

HLS resource estimate:

- BRAM_18K: `133` / `280`
- LUT: `3018` / `53200`
- FF: `1543` / `106400`
- DSP: `0` / `220`
- worst-case latency estimate: `103808509` cycles (`1.298 sec`)
- ENCODER_LOOP final II: `2` (`Resource Limitation`)

## Vivado Routed Results

| Gate | Result | Evidence |
|---|---:|---|
| routed clock | `20.0` MHz | `outputs/spikemold_pynq_z2_eventconv_20mhz_timing.rpt` |
| routed WNS | `34.974` ns | timing summary |
| routed TNS failing endpoints | `0` | timing summary |
| all timing met | `True` | timing summary |
| bitstream present | `True` | `outputs/spikemold_pynq_z2_eventconv_20mhz.bit` + `outputs/spikemold_pynq_z2_eventconv_20mhz.hwh` |

Timing status: `HLS C-sim, HLS synthesis/IP package, and integrated Vivado route timing passed`. When `all timing met` is `False`, the bit/HWH may be
used only for functional board smoke; do not use it for latency, throughput, or
frequency claims.

Routed utilization:

- Slice LUTs: `9548` / `53200` (`17.95`%)
- Slice Registers: `9007` / `106400` (`8.47`%)
- Block RAM Tile: `99` / `140` (`70.71`%)
- DSPs: `4` / `220` (`1.82`%)

Power report estimate:

- total on-chip power: `1.718` W
- dynamic: `1.564` W
- static: `0.153` W
- confidence: `Medium`
- vectorless estimate: `True`

## Artifacts

| Artifact | Size bytes | SHA-256 |
|---|---:|---|
| `hardware/hls/hls_output/hls/impl/ip/component.xml` | `159756` | `14bf8959bbbc54bd93ea6ad1b6c9555e49e940990fef2d0f58e599b66f761982` |
| `hardware/hls/hls_output/spikemold_top_hls.zip` | `108917` | `bbe0d83b87e990d4d9e94acc18646f15978fa76d634d5fdbc2c545db3c4ada70` |
| `outputs/spikemold_pynq_z2_eventconv_20mhz.bit` | `4045700` | `5b6b3d64a8263b3e6b075c934bcef0d3684d576756cba600711d2918d863d1d0` |
| `outputs/spikemold_pynq_z2_eventconv_20mhz.hwh` | `525968` | `9447e36cbfc687c8cf0683b6ae05671ad4ef9bb017ef78c1a0777b73d6a87ec3` |

## Methodology Warnings

| Rule | Severity | Count | Description |
|---|---|---:|---|
| LUTAR-1 | Warning | 6 | LUT drives async reset alert |
| SYNTH-6 | Warning | 29 | Timing of a RAM block might be sub-optimal |

## Claim Boundary

`hls_csim_hls_synth_vivado_routed_bitstream_only_no_board_execution`

## Next Gate

Run PYNQ-Z2 one-shot board smoke with the generated bit/HWH and record board
JSON counters/readback. Until then, this is routed build evidence only.
