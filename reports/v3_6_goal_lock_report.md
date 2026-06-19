# SpikePress + SpikeMold v3.6 Goal Lock Report

Date: 2026-06-19
Target: PYNQ-Z2 / Zynq-7020
Implementation commit: `0c7fa9c0ac7005bd1c473a20f517830f247e2e9e`
Status: **LOCKED for v3.6 mainline functional implementation**

## Lock Scope

This lock covers the SpikePress + SpikeMold v3.6 mainline functional slice:

- Batch 0 contract freeze.
- Batch 1A software foundation and architecture-neutral golden traces.
- Batch 1B transport plus tiny flat FC-LIF path.
- Batch 1C EventConv primitive path.
- Batch 1X architecture sandbox for coregroup/page/tile probation.
- HLS C-sim, HLS synthesis/package, and integrated Vivado routed build evidence.
- PYNQ-Z2 board smokes for direct spike transport, EventWord64 lowering, tiny flat FC-LIF, tiny EventConv, and EventConv burst-boundary.

## Claim Boundary

Allowed claim:

```text
SpikePress + SpikeMold v3.6 has a trace-checked, resource-bounded,
clocked FPGA implementation with event-triggered execution semantics for
the selected FC-LIF plus EventConv primitive path. Current PYNQ-Z2 evidence
covers tiny/direct board smokes with commit-value and state-checksum readback.
```

Forbidden claims at this lock:

- Latency, throughput, frequency, or energy.
- Dataset accuracy on board.
- Full-network PYNQ-Z2 correctness.
- Full-state dump correctness.
- Descriptor-configured arbitrary EventConv shape/kernel support on board.
- Loihi-compatible, TrueNorth-equivalent, fully asynchronous, or general neuromorphic computer.

## Locked Evidence

| Gate | Status | Primary evidence |
|---|---:|---|
| Contract freeze | PASS | `contracts/*.md` |
| Software foundation | PASS | `golden_traces/v1/*.json`, `software/python/spikepress/` |
| Transport + flat FC-LIF | PASS | `reports/batch_1b_transport_flat_fc_lif_report.md` |
| EventConv C0-C5 | PASS | `reports/batch_1c_eventconv_primitive_report.md` |
| Architecture selection | PASS | `reports/architecture_selection_v1.md` |
| HLS/Vivado build | PASS | `reports/spikemold_build_evidence_report.md` |
| Verifier gate | PASS | `reports/verifier_gate_review.md` |
| Final manifest | PASS | `reports/v3_6_goal_lock_manifest.json` |

## Board Evidence

| Board smoke | Boundary | Result |
|---|---|---:|
| Direct RTL spike transport | `pynq_axi_dma0_direct_rtl_one_spike_event_to_post_spike_readback_only_no_dataset` | PASS |
| EventWord64-lowered input | lossless EventWord64 to AXIS32 input smoke | PASS |
| Tiny flat FC-LIF | `pynq_axi_dma0_direct_rtl_tiny_flat_fc_lif_commit_value_state_checksum_readback` | PASS |
| Tiny EventConv | `pynq_axi_dma0_direct_rtl_tiny_eventconv_multi_commit_state_checksum_readback` | PASS |
| EventConv burst-boundary | `pynq_axi_dma0_direct_rtl_eventconv_burst_boundary_state_checksum_readback` | PASS |

Board JSONs remain local generated artifacts under `outputs/board/`. Their hashes are pinned in `reports/v3_6_goal_lock_manifest.json`.

## Build Artifact Identity

| Artifact | SHA-256 |
|---|---|
| `outputs/spikemold_pynq_z2_eventconv_20mhz.bit` | `5b6b3d64a8263b3e6b075c934bcef0d3684d576756cba600711d2918d863d1d0` |
| `outputs/spikemold_pynq_z2_eventconv_20mhz.hwh` | `9447e36cbfc687c8cf0683b6ae05671ad4ef9bb017ef78c1a0777b73d6a87ec3` |
| `hardware/hls/hls_output/hls/impl/ip/component.xml` | `14bf8959bbbc54bd93ea6ad1b6c9555e49e940990fef2d0f58e599b66f761982` |
| `hardware/hls/hls_output/spikemold_top_hls.zip` | `bbe0d83b87e990d4d9e94acc18646f15978fa76d634d5fdbc2c545db3c4ada70` |

Generated build outputs stay ignored. The manifest records identity; source, tests, configs, curated traces, and reports are committed.

## Release Bundle

Local ignored bundle:

| Artifact | SHA-256 | Size |
|---|---|---:|
| `outputs/release/spikemold_v3_6_lock_20260619.tar.gz` | `e6165ffff28e3ce37b7bee489e56c3529a2b146d3f8c980ecac17578b68aebc6` | `726555` bytes |

Bundle contains curated reports, curated golden traces, PYNQ-Z2 bit/HWH,
Vivado reports, board smoke JSON outputs, and HLS IP package/readback files.
It excludes checkpoints, dataset downloads, profiler dumps, and large local
training artifacts.

## Release Bundle Board Rerun

Rerun date: 2026-06-20
Board: PYNQ-Z2 at `192.168.0.54`
Runtime note: use `sudo -n env XILINX_XRT=/usr ...` so PYNQ sees the embedded device.

| Rerun | Result | SHA-256 |
|---|---:|---|
| `outputs/release/flat_fc_lif_rerun_20260620_xrt.json` | PASS | `5a6d014a28359feeba9c80fcc685929bb06b912a35b71070f0b4db748a68e379` |
| `outputs/release/eventconv_tiny_rerun_20260620_xrt.json` | PASS | `99cc4a6350b6c9b83c4a92ccbddef03c2541c425a4dca361f17cf8ea4cb7e81d` |
| `outputs/release/eventconv_burst_boundary_rerun_20260620_xrt.json` | PASS | `10fb33e1299494707041239df10c93115f465357706a22f4c0079e3e99dbf603` |

These reruns prove the release bundle can reproduce the locked tiny board smokes.
They do not expand the claim boundary to full-network correctness or performance.

## Remote Backup

Remote backup branch:

```text
origin/spikemold-v3.6-lock
```

Pull request URL:

```text
https://github.com/metr0jw/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/pull/new/spikemold-v3.6-lock
```

`origin/main` was not overwritten because remote `main` has a newer divergent
public-documentation/runtime history. This lock remains backed up on the
dedicated branch above.

## Final Verifier Commands

Run these from repo root:

```bash
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_spikemold_batch0_1a.py
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_batch1b_transport.py
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_batch1c_eventconv.py
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_verifier_gate.py
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_spikemold_build_evidence_report.py
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_architecture_selection.py
```

Expected result: all six commands print `PASS`.

## Git Hygiene Lock

Committed source/test/config/report scope:

- SpikePress runtime, training support, trace generation, transport, and verifier tools.
- HLS/RTL/config/register-map changes for selected FC-LIF plus EventConv path.
- Curated golden traces under `golden_traces/v1/`.
- Curated reports under `reports/`.
- Dataset download notes under `docs/`.

Ignored local artifacts:

- `outputs/*`
- `data/*`
- `*.pth`, `*.pt`
- `drive-download-*.zip`
- `profiler_*.json`
- `golden_traces/v1/nmnist_eventconv_sample_*.json`
- HLS/Vivado working directories

## Next Gates Outside This Lock

- Descriptor-configured EventConv shape/kernel board evidence.
- Wider destination/state-space board smoke.
- Full-network PYNQ-Z2 equivalence.
- Latency/throughput/energy measurement with same-run counters and host timing.

## Lock Decision

v3.6 mainline functional implementation is locked. Stronger application and performance claims remain blocked until the next gates above pass.
