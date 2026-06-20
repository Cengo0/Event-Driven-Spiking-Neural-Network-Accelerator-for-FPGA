# SpikeMold MNIST Multi-Sample Board Report

Date: 2026-06-20
Target: PYNQ-Z2 / Zynq-7020
Status: **5 / 5 PASS**

## Scope

This is follow-on evidence after the final single-sample lock. It reuses the
same frozen SpikePress/SpikeMold artifact and the same routed PYNQ-Z2 bit/HWH.
Each trace is generated from a real MNIST test image by taking the top-3
brightest pixels as sparse coordinate events.

Claim boundary:

- MNIST-derived sparse event samples equivalence only
- Not claimed: full MNIST board accuracy
- Not claimed: latency
- Not claimed: throughput
- Not claimed: energy
- Not claimed: arbitrary EventConv shape/kernel support

## Commands

Trace generation:

```bash
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/generate_spikemold_mnist_multisample_traces.py --num-samples 5 --top-k 3 --max-output-words 64
```

Board loop:

```bash
cd /home/xilinx/spikemold_final_goal
for trace in outputs/runtime/mnist_eventconv_fclif_multisample/mnist_eventconv_fclif_top3_sample_*.json; do
  base=$(basename "$trace" .json)
  sudo -n env XILINX_XRT=/usr /usr/local/share/pynq-venv/bin/python3 scripts/run_spikemold_pynq_eventconv_fclif.py \
    --bitstream outputs/spikemold_pynq_z2_frozen_mnist_10mhz.bit \
    --hwh outputs/spikemold_pynq_z2_frozen_mnist_10mhz.hwh \
    --artifact outputs/artifacts/mnist_eventconv_fclif_frozen.json \
    --trace "$trace" \
    --output-json "outputs/board/mnist_multisample_20260620/${base}_board.json" \
    --timeout-seconds 600 \
    --time-steps 4096
done
```

Checker:

```bash
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_spikemold_mnist_multisample_board.py
```

## Artifact Identity

| Artifact | SHA-256 |
|---|---|
| `outputs/runtime/mnist_eventconv_fclif_multisample/manifest.json` | `afa3491485cbd9600c3a039fae8e0b84766ae68c89be68f0f66fb660b1da5252` |
| `outputs/spikemold_pynq_z2_frozen_mnist_10mhz.bit` | `c307b9b8bfeb7bc33be3ee9275f28130ff5027db012b10e00392078e45257b09` |
| `outputs/spikemold_pynq_z2_frozen_mnist_10mhz.hwh` | `2816d9ad88f736ac9b9b6cfa585c817ee606be7bd02a8151b95687061d29d355` |

## Board Results

| sample | MNIST label | input events | output words | board JSON SHA-256 | result |
|---:|---:|---:|---:|---|---:|
| 0 | 7 | 3 | 22 | `bc815e5fe00ab17882c68bdee9067f3f2d3194cfa95b0738d674eafafcd03dde` | PASS |
| 1 | 2 | 3 | 14 | `5b6728f0197c92cb5b62888777d4e20184cdc0ca839a18cb88039a11efdc04c4` | PASS |
| 2 | 1 | 3 | 16 | `6841ba9867587516880ee6ce3f413c3b4dad75360f91aa7afdebb2afe3b7c5b9` | PASS |
| 3 | 0 | 3 | 36 | `13223bbb8b9147b3758a10b1690ebe27be3e9d4a252c51a059d40df9832f2c78` | PASS |
| 4 | 4 | 3 | 19 | `b943441370e44494487e5487d6d1a5de41246b2b9ccab996aad0f0c3ddead9f5` | PASS |

All five board runs have:

- `ok: true`
- `board_executed: true`
- `output_words_match: true`
- `output_event_count_exact: true`
- `output_emit_count_exact: true`
- `no_output_drops: true`

## Next Gates

- Full MNIST board accuracy remains unproven.
- Larger per-sample event budgets remain unproven.
- Descriptor-configured arbitrary EventConv board support remains unproven.
- Latency, throughput, and energy remain unclaimed.
