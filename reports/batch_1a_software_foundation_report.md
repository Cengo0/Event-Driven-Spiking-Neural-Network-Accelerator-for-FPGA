# Batch 1A Software Foundation Report

Status: verifier gate complete

## Generated

- `golden_traces/v1/fc_lif_tiny_v1.json`
- `golden_traces/v1/eventconv_8x8_tiny_v1.json`
- `outputs/event_budget/recommended_ednp_mini_config.json`
- `software/python/spikepress/`

## Evidence Level

Integer golden trace generation only. No HLS, RTL, or board claim.

## Current Scope

- FC-LIF tiny deterministic trace
- shared-kernel EventConv AGU tiny deterministic trace
- event/update/active/state counter budget
- inference-only SpikePress API and SpikeMold-EDNP artifact path
- event counter histogram
- SpikeMold-EDNP artifact JSON roundtrip

## Remaining Batch 1A Work

- None for the current board-free Batch 1A slice.

## Verifier

- `reports/verifier_gate_review.md`
- `scripts/check_verifier_gate.py`
