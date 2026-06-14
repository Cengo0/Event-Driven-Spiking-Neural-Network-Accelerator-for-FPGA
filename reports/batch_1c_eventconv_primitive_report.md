# Batch 1C EventConv Primitive Report

Status: C0/C1 board-free gate passed

## Evidence Level

`rtl_xsim_agu_only_no_board`

No board execution was run. This report does not claim PYNQ-Z2 PL deployment,
latency, throughput, or energy.

## Generated

- `golden_traces/v1/eventconv_agu_c0_tiny_v1.json`
- `hardware/hdl/rtl/core/spike_conv_agu.v`
- `hardware/hdl/tb/tb_spike_conv_agu.v`

## Gate Results

| Stage | Result | Evidence |
|---|---:|---|
| C0 trace-locked tiny case | PASS | `scripts/check_batch1c_eventconv.py` |
| C1 AGU-only | PASS | Vivado xsim `tb_spike_conv_agu`: 19 PASS, 0 FAIL |
| C2 AGU + state update | PENDING | not implemented |
| C3 AGU + active-set commit | PENDING | not implemented |
| C4 scale-up | PENDING | waits for C3 |

## C0 Trace Contract

The locked tiny case uses one input spike at `(x=1, y=1, channel=0)` with a
shared 2x2 kernel `[[1, 2], [3, 4]]` on a 3x3 input. Expected AGU updates are:

| Order | Destination | Weight Index | Weight |
|---:|---:|---:|---:|
| 0 | 3 | 0 | 1 |
| 1 | 2 | 1 | 2 |
| 2 | 1 | 2 | 3 |
| 3 | 0 | 3 | 4 |

## Runtime Assumptions

- Python inner loop required: `False`
- random DDR inner loop: `False`
- full-neuron scan primary: `False`
- shared-kernel AGU: `True`

## Next Gate

Implement C2 by feeding AGU update packets into a tiny state RAM and checking
the state checksum against `eventconv_agu_c0_tiny_v1`.
