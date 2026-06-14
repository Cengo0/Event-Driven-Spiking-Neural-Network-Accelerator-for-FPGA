# Trace Schema V1

Status: active draft

## File Shape

Trace files are JSON objects:

```json
{
  "schema": "spikemold.trace.v1",
  "trace_id": "name",
  "target": "architecture-neutral",
  "metadata": {},
  "inputs": [],
  "updates": [],
  "commits": [],
  "final_state": {},
  "counters": {},
  "hashes": {}
}
```

## Required Counters

- `input_event_count`
- `generated_update_count`
- `active_neuron_count`
- `commit_count`
- `state_reads`
- `state_writes`
- `ddr_bytes_inner_loop`
- `python_inner_loop_steps`

## Required Hashes

- `input_sha256`
- `updates_sha256`
- `commits_sha256`
- `final_state_sha256`
- `trace_sha256`

Hashes are computed over canonical JSON: sorted keys, compact separators, UTF-8
bytes.

## Architecture Candidate Compatibility

Every candidate must consume the same trace schema. Candidate-specific metadata
belongs under `metadata.candidate`, not in new top-level semantics.

## Failure Rule

If a candidate cannot represent a trace without semantic changes, it must reject
the trace and report the reason. It must not rewrite the trace into a different
network.
