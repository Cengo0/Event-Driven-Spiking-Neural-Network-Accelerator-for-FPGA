# Batch 0 Contract Freeze Report

Status: initial freeze complete
Date: 2026-06-14

## Contracts

- `contracts/ARCHITECTURE_CONTRACT_V1.md`
- `contracts/INTEGER_SEMANTICS_V1.md`
- `contracts/EVENT_FORMAT_V1.md`
- `contracts/TRACE_SCHEMA_V1.md`
- `contracts/REGISTER_MAP_MINIMAL_V1.md`
- `contracts/RESOURCE_BUDGET_V1.md`
- `contracts/ARCHITECTURE_PATTERN_POLICY_V1.md`

## Policy Decision

Page, tile, and coregroup patterns are allowed on probation. The contract bans
failure modes instead:

- Python-controlled inner loops
- random DDR state or synapse access in the critical path
- unbounded fanout without compiler rejection
- full-neuron scan as the primary mode
- silent semantic changes

## Evidence Boundary

This freeze is a design and software-contract milestone only. It does not claim
HLS, RTL, or PYNQ-Z2 execution.

## Next Gate

Batch 1A must keep producing architecture-neutral traces under
`golden_traces/v1/`, event budget artifacts under `outputs/event_budget/`, and
software foundation evidence under `reports/`.
