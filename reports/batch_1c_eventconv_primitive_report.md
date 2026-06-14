# Batch 1C EventConv Primitive Report

Status: C0/C1/C2/C3 board-free gate passed

## Evidence Level

`rtl_xsim_eventconv_primitive_no_board`

No board execution was run. This report does not claim PYNQ-Z2 PL deployment,
latency, throughput, or energy.

## Generated

- `golden_traces/v1/eventconv_agu_c0_tiny_v1.json`
- `hardware/hdl/rtl/core/spike_conv_agu.v`
- `hardware/hdl/rtl/core/spike_conv_state_update.v`
- `hardware/hdl/rtl/core/spike_conv_active_commit.v`
- `hardware/hdl/tb/tb_spike_conv_agu.v`
- `hardware/hdl/tb/tb_spike_conv_state_update.v`
- `hardware/hdl/tb/tb_spike_conv_active_commit.v`

## Gate Results

| Stage | Result | Evidence |
|---|---:|---|
| C0 trace-locked tiny case | PASS | `scripts/check_batch1c_eventconv.py` |
| C1 AGU-only | PASS | Vivado xsim `tb_spike_conv_agu`: 19 PASS, 0 FAIL |
| C2 AGU + state update | PASS | Vivado xsim `tb_spike_conv_state_update`: 19 PASS, 0 FAIL |
| C3 AGU + active-set commit | PASS | Vivado xsim `tb_spike_conv_active_commit`: 36 PASS, 0 FAIL |
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

## C3 Active Commit Contract

The active-set commit stage consumes the C2 active-id list. It checks only
active destinations, not the whole state array.

For the trace-locked high-threshold readout:

- active commit read count: `4`
- commit output count: `0`
- active commit readout checksum: `0`
- full-neuron scan count: `0`
- commit reset count: `0`

The testbench also runs a positive-threshold check at threshold `3` to prove
readout emission order and reset-to-zero semantics:

| Order | Destination | State |
|---:|---:|---:|
| 0 | 1 | 3 |
| 1 | 0 | 4 |

After the positive-threshold readout, committed destinations `1` and `0` reset
to zero, active count compacts from `4` to `2`, and state checksum becomes `3`.

## Runtime Assumptions

- Python inner loop required: `False`
- random DDR inner loop: `False`
- full-neuron scan primary: `False`
- shared-kernel AGU: `True`

## Next Gate

Implement C4 by scaling the EventConv primitive beyond the tiny 2x2 kernel case
while preserving trace correctness and active-set commit counters.
