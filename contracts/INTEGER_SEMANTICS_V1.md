# Integer Semantics V1

Status: active draft

## Numeric Rule

The SpikePress compiler/golden simulator and SpikeMold backend use explicit
integer arithmetic. Floating point may be used during training, calibration, and
export, but not inside the locked hardware trace contract.

## Default Widths

- input event coordinate fields: unsigned integers
- tick: unsigned 32-bit logical timestep
- neuron id: unsigned 32-bit logical id in traces
- synaptic weight: signed 16-bit integer
- membrane state: signed 32-bit integer
- threshold: signed 32-bit integer
- leak: signed 16-bit integer
- readout count/logit: signed 32-bit integer

## LIF Update

For each generated synaptic update:

```text
state[dst] = clamp_i32(state[dst] + weight)
```

For commit:

```text
if state[dst] >= threshold[dst]:
    emit spike/readout event
    state[dst] = reset_value[dst]
```

The first SpikeMold flat FC-LIF path uses reset-to-zero after fire. Later
contracts may add subtract-threshold reset only if traces name that mode
explicitly.

## EventConv Update

Input spike `(tick, y, x, cin)` generates updates for each valid output
coordinate and output channel:

```text
weight = kernel[cout][cin][ky][kx]
dst = flatten(cout, out_y, out_x)
state[dst] += weight
```

Stride and padding are applied by the AGU. Invalid coordinates generate no
update.

## Saturation

Default golden semantics use signed 32-bit saturation for membrane state. Any
hardware implementation with narrower state must prove the compiler rejects
traces that can overflow the narrower state.
