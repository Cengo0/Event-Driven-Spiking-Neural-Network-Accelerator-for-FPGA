# Batch 1C EventConv Primitive Report

Status: C0/C1/C2/C3/C4/C5 plus burst-boundary PYNQ-Z2 smoke gate passed

## Evidence Level

`pynq_axi_dma0_direct_rtl_eventconv_burst_boundary_state_checksum_readback`

PYNQ-Z2 board execution is locked for the fixed-shape EventConv tiny and
burst-boundary trace smokes. This report does not claim latency, throughput, or
energy.

## Generated

- `golden_traces/v1/eventconv_agu_c0_tiny_v1.json`
- `golden_traces/v1/eventconv_8x8_tiny_v1.json`
- `golden_traces/v1/eventconv_burst_boundary_v1.json`
- `hardware/hdl/rtl/core/spike_conv_agu.v`
- `hardware/hdl/rtl/core/spike_conv_state_update.v`
- `hardware/hdl/rtl/core/spike_conv_active_commit.v`
- `hardware/hdl/tb/tb_spike_conv_agu.v`
- `hardware/hdl/tb/tb_spike_conv_state_update.v`
- `hardware/hdl/tb/tb_spike_conv_active_commit.v`
- `hardware/hdl/tb/tb_spike_conv_c4_scaleup.v`
- `hardware/hdl/tb/tb_spike_conv_commit_backpressure.v`

## Gate Results

| Stage | Result | Evidence |
|---|---:|---|
| C0 trace-locked tiny case | PASS | `scripts/check_batch1c_eventconv.py` |
| C1 AGU-only | PASS | Vivado xsim `tb_spike_conv_agu`: 19 PASS, 0 FAIL |
| C2 AGU + state update | PASS | Vivado xsim `tb_spike_conv_state_update`: 19 PASS, 0 FAIL |
| C3 AGU + active-set commit | PASS | Vivado xsim `tb_spike_conv_active_commit`: 49 PASS, 0 FAIL |
| C4 scale-up | PASS | Vivado xsim `tb_spike_conv_c4_scaleup`: 46 PASS, 0 FAIL |
| C5 readout backpressure | PASS | Vivado xsim `tb_spike_conv_commit_backpressure`: 31 PASS, 0 FAIL |
| burst-boundary active readout trace | PASS | `golden_traces/v1/eventconv_burst_boundary_v1.json` |
| burst-boundary PYNQ-Z2 smoke | PASS | `outputs/board/eventconv_burst_boundary_smoke_result_20260615.json` |

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

## C5 Readout Backpressure Contract

The C5 gate stalls `m_axis_commit_tready` and `m_axis_reset_tready`
independently. It proves the active commit stage does not duplicate the commit
stream when reset is stalled, does not duplicate the reset stream when commit is
stalled, and records output backpressure cycles.

Expected C5 counters:

- active commit read count: `4`
- commit output count: `2`
- reset output count observed by testbench: `2`
- readout checksum: `7`
- full-neuron scan count: `0`
- output backpressure cycles: `> 0`

## Burst-Boundary Active Readout Contract

The burst-boundary gate uses three input spikes on the fixed 3x3/2x2 EventConv
board shape:

- centered input `(x=1, y=1)`
- bottom-right boundary input `(x=2, y=2)`
- top-left boundary input `(x=0, y=0)`

Invalid boundary taps are skipped, so the trace generates six updates rather
than twelve. Packet-end active-set readout with threshold `3` emits:

| Order | Destination | State |
|---:|---:|---:|
| 0 | 3 | 5 |
| 1 | 1 | 3 |
| 2 | 0 | 5 |

After reset-to-zero for committed destinations, final nonzero state is:

| Destination | Final State |
|---:|---:|
| 2 | 2 |

Expected burst-boundary counters:

- input event count: `3`
- generated update count: `6`
- active neuron count before commit: `4`
- active neuron count after commit: `1`
- commit output count: `3`
- state reads: `6`
- state writes: `9`
- inner-loop DDR bytes: `0`
- Python inner-loop steps: `0`

## Residual Risks

- Burst-boundary board execution is locked for the fixed 3x3 input / 2x2 output
  EventConv backend; configurable shape/kernel descriptors are still pending.
- C4 state space is 64 destinations; wider output maps still need resource and
  destination-width gates before wider board claims.

## Runtime Assumptions

- Python inner loop required: `False`
- random DDR inner loop: `False`
- full-neuron scan primary: `False`
- shared-kernel AGU: `True`

## Next Gate

Batch 1C board-free primitive gates cover centered EventConv scale-up,
burst-boundary invalid-tap skip behavior, and readout backpressure. The fixed
PYNQ-Z2 EventConv smoke gate is now locked. Next EventConv gate is configurable
shape/kernel descriptor evidence before wider-destination claims.
