# Batch 1C EventConv Primitive Report

Status: C0/C1/C2 board-free gate passed

## Evidence Level

`rtl_xsim_eventconv_primitive_no_board`

No board execution was run. This report does not claim PYNQ-Z2 PL deployment,
latency, throughput, or energy.

## Generated

- `golden_traces/v1/eventconv_agu_c0_tiny_v1.json`
- `hardware/hdl/rtl/core/spike_conv_agu.v`
- `hardware/hdl/rtl/core/spike_conv_state_update.v`
- `hardware/hdl/tb/tb_spike_conv_agu.v`
- `hardware/hdl/tb/tb_spike_conv_state_update.v`

## Gate Results

| Stage | Result | Evidence |
|---|---:|---|
| C0 trace-locked tiny case | PASS | `scripts/check_batch1c_eventconv.py` |
| C1 AGU-only | PASS | Vivado xsim `tb_spike_conv_agu`: 19 PASS, 0 FAIL |
| C2 AGU + state update | PASS | Vivado xsim `tb_spike_conv_state_update`: 14 PASS, 0 FAIL |
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

## C2 State Contract

The AGU output packets feed a tiny near-memory state RAM. The C2 gate does
read-modify-write only; it does not emit commits or claim board execution.

Expected state after the C0 spike:

| Destination | Final State |
|---:|---:|
| 0 | 4 |
| 1 | 3 |
| 2 | 2 |
| 3 | 1 |

- state checksum: `10`
- active mask: `0xF`
- state reads: `4`
- state writes: `4`

## Runtime Assumptions

- Python inner loop required: `False`
- random DDR inner loop: `False`
- full-neuron scan primary: `False`
- shared-kernel AGU: `True`

## Next Gate

Implement C3 by adding active-set commit/readout on top of the C2 state RAM and
checking commit output against `eventconv_agu_c0_tiny_v1`.
