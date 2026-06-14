# SpikeMold HLS/Vivado Build Evidence Report

Status: HLS C-sim, HLS synthesis/IP package, and integrated Vivado route passed

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
| routed clock | `20.0` MHz | `outputs/spikemold_pynq_z2_timing.rpt` |
| routed WNS | `36.122` ns | timing summary |
| routed TNS failing endpoints | `0` | timing summary |
| all timing met | `True` | timing summary |
| bitstream present | `True` | `outputs/spikemold_pynq_z2.bit` + `.hwh` |

Routed utilization:

- Slice LUTs: `8288` / `53200` (`15.58`%)
- Slice Registers: `8490` / `106400` (`7.98`%)
- Block RAM Tile: `100` / `140` (`71.43`%)
- DSPs: `4` / `220` (`1.82`%)

Power report estimate:

- total on-chip power: `1.717` W
- dynamic: `1.563` W
- static: `0.153` W
- confidence: `Medium`
- vectorless estimate: `True`

## Artifacts

| Artifact | Size bytes | SHA-256 |
|---|---:|---|
| `hardware/hls/hls_output/hls/impl/ip/component.xml` | `159756` | `14bf8959bbbc54bd93ea6ad1b6c9555e49e940990fef2d0f58e599b66f761982` |
| `hardware/hls/hls_output/spikemold_top_hls.zip` | `108917` | `bbe0d83b87e990d4d9e94acc18646f15978fa76d634d5fdbc2c545db3c4ada70` |
| `outputs/spikemold_pynq_z2.bit` | `4045700` | `034f62803060e81e37a98f459c8433a358183e4485b84ba12d8585016b3eb418` |
| `outputs/spikemold_pynq_z2.hwh` | `518428` | `033a777f37c04e09fb36772ae62c05922a67c43d35a736a80c66a1b63ac8cad1` |

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
