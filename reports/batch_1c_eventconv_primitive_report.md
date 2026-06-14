# Batch 1C EventConv Primitive Report

Status: C0/C1/C2/C3/C4 board-free gate passed

## Evidence Level

`rtl_xsim_eventconv_primitive_no_board`

No board execution was run. This report does not claim PYNQ-Z2 PL deployment,
latency, throughput, or energy.

## Generated

- `golden_traces/v1/eventconv_agu_c0_tiny_v1.json`
- `golden_traces/v1/eventconv_8x8_tiny_v1.json`
- `hardware/hdl/rtl/core/spike_conv_agu.v`
- `hardware/hdl/rtl/core/spike_conv_state_update.v`
- `hardware/hdl/rtl/core/spike_conv_active_commit.v`
- `hardware/hdl/tb/tb_spike_conv_agu.v`
- `hardware/hdl/tb/tb_spike_conv_state_update.v`
- `hardware/hdl/tb/tb_spike_conv_active_commit.v`
- `hardware/hdl/tb/tb_spike_conv_c4_scaleup.v`

## Gate Results

| Stage | Result | Evidence |
|---|---:|---|
| C0 trace-locked tiny case | PASS | `scripts/check_batch1c_eventconv.py` |
| C1 AGU-only | PASS | Vivado xsim `tb_spike_conv_agu`: 19 PASS, 0 FAIL |
| C2 AGU + state update | PASS | Vivado xsim `tb_spike_conv_state_update`: 19 PASS, 0 FAIL |
| C3 AGU + active-set commit | PASS | Vivado xsim `tb_spike_conv_active_commit`: 36 PASS, 0 FAIL |
| C4 scale-up | PASS | Vivado xsim `tb_spike_conv_c4_scaleup`: 46 PASS, 0 FAIL |

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

## C4 Scale-Up Contract

The C4 gate uses `eventconv_8x8_tiny_v1`: two input spikes, a signed 3x3 kernel
with zero-skipped taps, padding `1`, and an 8x8 output state space.

Expected C4 counters:

- input event count: `2`
- generated update count: `12`
- active neuron count: `12`
- state reads: `12`
- state writes: `12`
- commit output count: `0`
- full-neuron scan count: `0`

The RTL testbench checks all 12 update destinations, signed positive/negative
state values, active-id ordering, active-mask bits, high-threshold active commit,
and no reset when the trace has no commits.

## Residual Risks

- C4 uses centered input spikes; boundary padding invalid-coordinate behavior is
  still a follow-up gate.
- C4 uses always-ready commit output; readout backpressure remains a follow-up
  gate.
- C4 state space is 64 destinations; wider output maps still need resource and
  destination-width gates before board claims.

## Runtime Assumptions

- Python inner loop required: `False`
- random DDR inner loop: `False`
- full-neuron scan primary: `False`
- shared-kernel AGU: `True`

## Next Gate

Batch 1C board-free primitive gates are complete. Next gate is architecture
selection reporting and then board/runtime integration without changing the
trace contract.
