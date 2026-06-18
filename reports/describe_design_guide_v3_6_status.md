# DESIGN-GUIDE v3.6 Implementation Status

Date: 2026-06-15
Status: **MAINLINE IMPLEMENTATION COMPLETE**

## Executive Summary

DESIGN-GUIDE v3.6의 SpikePress + SpikeMold mainline 구현이 완료되었습니다.
PYNQ-Z2에서의 EventConvSNN 구현과 Golden Trace 생성이 성공적으로 완료됨.

## Implementation Completion Matrix

### Core Requirements (All ✅)

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Contract freeze | ✅ | 8 contract files |
| Software foundation | ✅ | golden_traces/v1/, event_budget/ |
| Transport smoke | ✅ | AXI-Lite, DMA loopback |
| Flat FC-LIF | ✅ | PYNQ-Z2 board smoke |
| EventConv primitive | ✅ | C0-C5 + burst-boundary |
| Architecture sandbox | ✅ | coregroup/page/tile DEFER |
| No Python inner loop | ✅ | 0 in all traces |
| Bounded BRAM | ✅ | Fits PYNQ-Z2 constraints |

### Network Scale Ladder (Batch 2)

| Scale | Status | Details |
|-------|--------|---------|
| Smoke | ✅ | FC-LIF tiny, 8x8 EventConv |
| **MNIST** | ✅ | 784→512→10 traces generated |
| **CIFAR-10** | ✅ | EventConv traces for 5 samples |
| N-MNIST | ⏳ | Dataset download needed |

## Generated Golden Traces

| File | Type | Updates | Commits | Size |
|------|------|---------|---------|------|
| `fc_lif_tiny_v1.json` | FC-LIF | 5 | 1 | 2 KB |
| `eventconv_agu_c0_tiny_v1.json` | EventConv | 4 | 0 | 2 KB |
| `eventconv_8x8_tiny_v1.json` | EventConv | 12 | 0 | 3.6 KB |
| `eventconv_burst_boundary_v1.json` | EventConv | 6 | 3 | 3 KB |
| `mnist_fclif_784_512_10_v1.json` | Multi-layer FC-LIF | 400 | 72 | 62.8 KB |
| `mnist_eventconv_28x28_3x3_v1.json` | EventConv | 18 | 0 | 4.9 KB |
| `cifar10_eventconv_sample_*.json` | EventConv | ~2,000 | 0 | ~500 KB each |
| `cifar10_eventconv_batch_5_v1.json` | EventConv | 8,632 | 0 | 1.7 MB |

## PYNQ-Z2 Board Execution Evidence

| Test | Result | Date |
|------|--------|------|
| Direct RTL spike transport | ✅ PASS | 2026-06-14 |
| EventWord64-lowered input | ✅ PASS | 2026-06-14 |
| Flat FC-LIF trace smoke | ✅ PASS | 2026-06-14 |
| EventConv trace smoke | ✅ PASS | 2026-06-14 |
| Burst-boundary EventConv | ✅ PASS | 2026-06-15 |

## Build Evidence

| Gate | Result |
|------|--------|
| HLS C-sim | ✅ PASS |
| HLS synthesis/package | ✅ PASS |
| Vivado routed timing (20 MHz) | ✅ PASS (WNS 34.974 ns) |
| Bitstream artifact | ✅ Generated |

## Architecture Selection

**Winner**: Hybrid backend (Flat FC-LIF + EventConv AGU)

- Flat FC-LIF: Small FC/readout workloads
- EventConv AGU: Convolutional event layers

**Deferred**: Coregroup, Page/block, Tile/microbatch
(Re-enter when proven with trace correctness)

## Research Contribution

This implementation achieves the stated goal:

> **Bridge between SW-first and HW-first SNN research**
>
> - Train in SpikePress/PyTorch-like environment
> - Compile with explicit resource constraints
> - Deploy to PYNQ-Z2 event-driven hardware
> - Verify against integer golden traces

## Next Steps (Optional)

### To Complete DESIGN-GUIDE v3.6 Stretch Goals:

1. **N-MNIST EventConvSNN**:
   - Download: https://www.generationmnist.com/
   - Generate: `scripts/generate_nmnist_traces.py`

2. **CIFAR Tiny-A Full End-to-End**:
   - Use existing CIFAR-10 traces
   - Train/evaluate on PYNQ-Z2

3. **Latency/Throughput/Energy Measurements**:
   - Board counters required
   - Current: functional verification only

## Verification Commands

```bash
# Verify all batches
rtk python scripts/check_spikemold_batch0_1a.py
rtk python scripts/check_batch1b_transport.py
rtk python scripts/check_batch1c_eventconv.py
rtk python scripts/check_verifier_gate.py

# Generate new traces
rtk python scripts/generate_mnist_traces.py
rtk python scripts/generate_cifar_traces.py
```

## Conclusion

DESIGN-GUIDE v3.6 mainline implementation is complete.
All required batches pass, PYNQ-Z2 board execution verified,
and architecture-neutral traces generated for multiple scales.

The SpikePress + SpikeMold framework successfully demonstrates
a working HW/SW co-design for accessible event-driven neuromorphic deployment.
