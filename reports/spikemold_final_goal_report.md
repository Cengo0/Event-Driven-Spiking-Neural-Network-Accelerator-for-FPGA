# SpikeMold Final Goal Contract Report

Status: host-side frozen SpikePress/SpikeMold contract generated.

## Frozen Slice

- Model: `EventConv(1x28x28, 4 filters, 3x3, stride 2, padding 1) -> sparse FC-LIF(784->10)`
- Hardware states: `794` (`784` EventConv states + `10` readout states)
- Backend mode: `2`
- Router fanout limit: `32`; generated sparse readout max fanout: `1`

## Artifacts

- Artifact: `outputs/artifacts/mnist_eventconv_fclif_frozen.json`
- Artifact SHA256: `d37c9be72dcef7c04e8c2bf141abe8d873c8e2249ad78a66d4a1fced7ef23f64`
- Golden trace: `golden_traces/v1/mnist_eventconv_fclif_frozen_v1.json`
- Trace SHA256: `beefd5f3d055f036c7536db154c45c69d68acc5430639e83cdb0281f4aac5770`
- Config plan: `outputs/runtime/mnist_eventconv_fclif_config_plan.json`
- Kernel config writes: `9`
- Router config writes: `2353`
- RTL top: `hardware/hdl/rtl/top/spikemold_integrated_top.v`
- Focused RTL TB: `hardware/hdl/tb/tb_spike_conv_frozen_mnist_slice.v`

## Claim Boundary

- Allowed claim after board run: fixed MNIST EventConv-FC sample equivalence only.
- Not claimed: full MNIST board accuracy.
- Not claimed: latency.
- Not claimed: throughput.
- Not claimed: energy.
- Not claimed: arbitrary EventConv shape/kernel support.

## Next Gate

Run `python scripts/check_spikemold_final_goal.py`, focused frozen-slice xsim, then at most two integrated Vivado builds.
