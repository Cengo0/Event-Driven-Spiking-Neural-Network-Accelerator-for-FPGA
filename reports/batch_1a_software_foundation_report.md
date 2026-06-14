# Batch 1A Software Foundation Report

Status: initial artifacts generated

## Generated

- `golden_traces/v1/fc_lif_tiny_v1.json`
- `golden_traces/v1/eventconv_8x8_tiny_v1.json`
- `outputs/event_budget/recommended_m3_config.json`

## Evidence Level

Integer golden trace generation only. No HLS, RTL, or board claim.

## Current Scope

- FC-LIF tiny deterministic trace
- shared-kernel EventConv AGU tiny deterministic trace
- event/update/active/state counter budget

## Remaining Batch 1A Work

- minimal SpikePress native API contract test
- compiler artifact roundtrip test
- broader event budget histogram
- verifier gate review
