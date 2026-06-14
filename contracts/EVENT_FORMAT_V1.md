# Event Format V1

Status: active draft

## JSON Trace Event

Architecture-neutral traces use JSON dictionaries. Required fields:

```text
tick: integer
kind: string
```

Input spike fields:

```text
kind = "input_spike"
src_id: integer
y: integer, optional
x: integer, optional
channel: integer, optional
payload: integer, default 1
```

Synaptic update fields:

```text
kind = "synaptic_update"
src_id: integer
dst_id: integer
weight: integer
y: integer, optional
x: integer, optional
channel: integer, optional
```

Commit/readout fields:

```text
kind = "commit"
dst_id: integer
value: integer
```

## EventWord64 Hardware Packing

The first hardware-facing packed event word uses this layout:

```text
[63:60] event_type
[59:48] tick_low12
[47:38] src_y_or_src_hi10
[37:28] src_x_or_src_lo10
[27:20] channel_or_dst_hi8
[19]    sign
[18:11] weight_abs_or_payload8
[10:5]  flags6
[4:0]   target_or_reserved5
```

This is a transport encoding, not the semantic source of truth. JSON traces are
the source of truth for software golden checks.

## Event Type Values

```text
0 = input_spike
1 = synaptic_update
2 = commit
3 = readout
15 = invalid/reserved
```

