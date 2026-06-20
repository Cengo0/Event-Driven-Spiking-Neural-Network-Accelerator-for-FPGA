# SpikeMold MNIST Top-8 Board Report

Date: 2026-06-20
Target: PYNQ-Z2 / Zynq-7020
Status: **5 / 5 PASS**

## Scope

This is follow-on evidence for a larger sparse input event budget than the
top-3 multi-sample gate. It reuses the same frozen SpikePress/SpikeMold
artifact and the same routed PYNQ-Z2 bit/HWH. Each trace is generated from a
real MNIST test image by taking the top-8 brightest pixels as sparse coordinate
events.

Claim boundary:

- MNIST-derived top-8 sparse event samples equivalence only
- Not claimed: full MNIST board accuracy
- Not claimed: full MNIST board equivalence
- Not claimed: latency
- Not claimed: throughput
- Not claimed: energy
- Not claimed: arbitrary EventConv shape/kernel support

## Commands

Trace generation:

```bash
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/generate_spikemold_mnist_multisample_traces.py --num-samples 5 --top-k 8 --max-output-words 64 --output-dir outputs/runtime/mnist_eventconv_fclif_top8_multisample --manifest outputs/runtime/mnist_eventconv_fclif_top8_multisample/manifest.json
```

Board loop:

```bash
cd /home/xilinx/spikemold_final_goal
for trace in outputs/runtime/mnist_eventconv_fclif_top8_multisample/mnist_eventconv_fclif_top8_sample_*.json; do
  base=$(basename "$trace" .json)
  sudo -n env XILINX_XRT=/usr /usr/local/share/pynq-venv/bin/python3 scripts/run_spikemold_pynq_eventconv_fclif.py \
    --bitstream outputs/spikemold_pynq_z2_frozen_mnist_10mhz.bit \
    --hwh outputs/spikemold_pynq_z2_frozen_mnist_10mhz.hwh \
    --artifact outputs/artifacts/mnist_eventconv_fclif_frozen.json \
    --trace "$trace" \
    --output-json "outputs/board/mnist_top8_multisample_20260620/${base}_board.json" \
    --timeout-seconds 600 \
    --time-steps 4096
done
```

Checker:

```bash
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_spikemold_mnist_top8_board.py
```

## Artifact Identity

| Artifact | SHA-256 |
|---|---|
| `outputs/runtime/mnist_eventconv_fclif_top8_multisample/manifest.json` | `797e8449b9670af0100c6022f62a5a4a5d8b5c2a7ad38d0154926a0e14268564` |
| `outputs/spikemold_pynq_z2_frozen_mnist_10mhz.bit` | `c307b9b8bfeb7bc33be3ee9275f28130ff5027db012b10e00392078e45257b09` |
| `outputs/spikemold_pynq_z2_frozen_mnist_10mhz.hwh` | `2816d9ad88f736ac9b9b6cfa585c817ee606be7bd02a8151b95687061d29d355` |

## Board Results

| sample | MNIST label | input events | output words | board JSON SHA-256 | result |
|---:|---:|---:|---:|---|---:|
| 0 | 7 | 8 | 52 | `0285391447f5c4a9ccc6508a2b2ab8fe74cc7d5d23b33cf5410ba509971f57a3` | PASS |
| 1 | 2 | 8 | 20 | `78e65bdd25bf3448c20a8b1356f9275e9f8ec5f0c41e14a288e1b31009e4e015` | PASS |
| 2 | 1 | 8 | 52 | `c5573ce6339b554bff6f3db55814a5d4dae907701b9ffa1d833798ec0f8c16c7` | PASS |
| 3 | 0 | 8 | 49 | `4963b4ace44b2d7eb6ad7f5deae8f7de581cf759065bd6250be53fe569f6f36e` | PASS |
| 4 | 4 | 8 | 51 | `d930d7dc9e08865bf53daec4865260ff605e271e07d427494d690a034ceedd9a` | PASS |

All five board runs have:

- `ok: true`
- `board_executed: true`
- `output_words_match: true`
- `output_event_count_exact: true`
- `output_emit_count_exact: true`
- `no_output_drops: true`

## Boundary

Top-8 is a larger sparse event budget than the locked top-3 follow-on, but it
is still not a full MNIST board run. Beyond top-8 event budgets remain unproven.
Full-image rate-coded MNIST, arbitrary EventConv shapes, latency, throughput,
and energy remain outside this claim.
