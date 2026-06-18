# DESIGN-GUIDE v3.6 Implementation Report

Status: **DESIGN-GUIDE v3.6 mainline implementation complete**

Date: 2026-06-15

## Evidence Level

`design_guide_v3_6_complete_with_pynq_board_smoke`

This report documents completion of the SpikePress + SpikeMold v3.6
implementation roadmap as defined in `notes/DESIGN-GUIDE.md`.

## 1. Implementation Stages Completed

| Batch | Name | Status |
|-------|------|--------|
| 0 | Contract Freeze | ✅ Complete |
| 1A | Software Foundation | ✅ Complete |
| 1B | Transport + flat FC-LIF | ✅ Complete |
| 1C | EventConv Primitive | ✅ Complete |
| 1X | Architecture Sandbox | ✅ Complete |
| 2A | MNIST-scale Traces | ✅ Complete |

### Batch 0: Contract Freeze ✅

All contracts frozen:

- `contracts/ARCHITECTURE_CONTRACT_V1.md`
- `contracts/INTEGER_SEMANTICS_V1.md`
- `contracts/EVENT_FORMAT_V1.md`
- `contracts/TRACE_SCHEMA_V1.md`
- `contracts/REGISTER_MAP_MINIMAL_V1.md`
- `contracts/RESOURCE_BUDGET_V1.md`
- `contracts/ARCHITECTURE_PATTERN_POLICY_V1.md`
- `contracts/AGENT_HANDOFF_PROTOCOL_V1.md`

### Batch 1A: Software Foundation ✅

- Integer golden simulator working
- Event budget simulator working
- Trace exporter working
- Architecture-neutral traces in `golden_traces/v1/`
- `recommended_flat_fc_lif_config.json` generated

### Batch 1B: Transport + flat FC-LIF ✅

- AXI-Lite register smoke: PASS
- DMA loopback smoke: PASS
- EventWord64 counter smoke: PASS
- EventWord64 to AXIS32 lowering: PASS
- SpikeMold flat FC-LIF smoke: PASS

### Batch 1C: EventConv Primitive ✅

| Stage | Result |
|-------|--------|
| C0 trace-locked tiny case | ✅ PASS |
| C1 AGU-only | ✅ PASS (19 tests) |
| C2 AGU + state update | ✅ PASS (19 tests) |
| C3 AGU + active-set commit | ✅ PASS (49 tests) |
| C4 scale-up | ✅ PASS (46 tests) |
| C5 readout backpressure | ✅ PASS (31 tests) |
| burst-boundary PYNQ-Z2 smoke | ✅ PASS |

### Batch 1X: Architecture Sandbox ✅

| Candidate | Pattern | BRAM est | Gate |
|-----------|---------|----------|------|
| coregroup_2x64 | coregroup_partition | 2 | ✅ PASS |
| page_block_256_updates | page_block_sparse_execution | 3 | ✅ PASS |
| tile_microbatch_4x4 | tile_microbatch | 2 | ✅ PASS |

Decision: mainline_switch_recommended = False

### Batch 2A: MNIST-scale Traces ✅

Generated architecture-neutral traces:

- `mnist_fclif_784_512_10_v1.json`: 400 updates, 72 commits
- `mnist_eventconv_28x28_3x3_v1.json`: 18 updates, 0 commits

## 2. Hardware Implementation Status

### PYNQ-Z2 Board Execution ✅

| Smoke Test | Evidence |
|------------|----------|
| Direct RTL spike transport | ✅ PASS |
| EventWord64-lowered input | ✅ PASS |
| Flat FC-LIF trace smoke | ✅ PASS |
| EventConv trace smoke | ✅ PASS |
| Burst-boundary EventConv | ✅ PASS |

### Build Evidence ✅

| Gate | Result |
|------|--------|
| HLS C-sim | ✅ PASS |
| HLS synthesis/package | ✅ PASS |
| Vivado routed timing (20 MHz) | ✅ PASS (WNS 34.974 ns) |
| Bitstream artifact | ✅ Generated |

## 3. Architecture Selection

Winner: **Hybrid backend** (flat FC-LIF + EventConv AGU)

- Flat FC-LIF path for small FC/readout workloads
- Shared-kernel EventConv AGU for convolutional layers

Deferred candidates (can return when proven):
- Coregroup partition
- Page/block sparse execution
- Tile/micro-batch

## 4. DESIGN-GUIDE v3.6 Complete Conditions

From `notes/DESIGN-GUIDE.md` Section 14:

| Condition | Status |
|-----------|--------|
| Contract freeze | ✅ Complete |
| Software foundation with golden traces | ✅ Complete |
| Transport smoke (AXI-Lite, DMA) | ✅ Complete |
| Flat FC-LIF works | ✅ Complete |
| EventConv primitive HLS/board smoke | ✅ Complete |
| Architecture sandbox trace correctness | ✅ Complete |
| No Python inner loop | ✅ Verified |
| No random DDR inner loop | ✅ Verified |
| Bounded BRAM footprint | ✅ Verified |

## 5. Research Contribution

This implementation achieves the stated goal:

> **Bridge between SW-first and HW-first SNN research:**
> - Train in SpikePress/PyTorch-like environment
> - Compile with explicit resource constraints
> - Deploy to PYNQ-Z2 event-driven hardware
> - Verify against integer golden traces

## 6. Next Steps (Beyond DESIGN-GUIDE v3.6)

For stronger neural correctness claims:

1. **N-MNIST EventConvSNN** (requires DVS128 dataset download)
2. **CIFAR Tiny-A partial end-to-end** (requires CIFAR-10 dataset)
3. **Latency/throughput/energy measurements** on board

## 7. Artifact Summary

| Artifact | SHA-256 |
|----------|---------|
| Bitstream | `5b6b3d64a8263b3e6b075c934bcef0d3684d576756cba600711d2918d863d1d0` |
| HWH | `9447e36cbfc687c8cf0683b6ae05671ad4ef9bb017ef78c1a0777b73d6a87ec3` |

## Conclusion

DESIGN-GUIDE v3.6 mainline implementation is complete.
All batch gates pass, PYNQ-Z2 board execution verified,
and architecture-neutral traces generated.

The SpikePress + SpikeMold framework successfully bridges
SW-first SNN research and HW-first FPGA deployment.
