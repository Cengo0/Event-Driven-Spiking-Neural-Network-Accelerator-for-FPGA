# SpikeMold Post-Lock Follow-On Report

Date: 2026-06-20
Target: PYNQ-Z2 / Zynq-7020
Status: **follow-on evidence reconciled**

## Completed After v3.6 Lock

| Gate | Evidence | Result |
|---|---|---:|
| Descriptor-configured tiny EventConv board smoke | `reports/spikemold_eventconv_trace_smoke_report.md` | PASS |
| Fixed MNIST EventConv-FC-LIF board equivalence | `reports/spikemold_final_goal_report.md` | PASS |
| MNIST-derived sparse multi-sample board equivalence | `reports/spikemold_mnist_multisample_board_report.md` | PASS |

## Evidence Identity

| Artifact | SHA-256 |
|---|---|
| `reports/spikemold_eventconv_trace_smoke_report.md` | `05bedbeac7c61240bd1bcde5b45f5eccb81407e76b03c100247022cbbf820f5f` |
| `reports/spikemold_final_goal_report.md` | `071109f232473a83cb30621ad95b641e54af84c964398df3af9a77b30e1b5e3e` |
| `reports/spikemold_mnist_multisample_board_report.md` | `ecf73297e87b546c330d8d3ba5861bca83ee3f965ee376d54504e2741d236619` |
| `outputs/board/eventconv_desc_tiny_20260620.json` | `a80b244168199354d6d50e884696ba97498bd8b08618716bb59a78cd6ce7ddff` |
| `outputs/board/eventconv_desc_burst_boundary_20260620.json` | `00fcb17a084134dbbc500ea3574e6b247d897fc32c4d1f5df065189cd09b6655` |
| `outputs/board/eventconv_fclif_frozen_mnist_10mhz_result_20260620.json` | `b0beca695277f7776596e442c0a8147e79ce36e1a13a27551f8c5ce93369e278` |

## Current Boundary

Allowed:

- Descriptor-configured tiny 3x3 input, 2x2 kernel EventConv board smokes.
- Fixed MNIST EventConv-FC-LIF sample board equivalence.
- Five MNIST-derived sparse top-3 event sample board equivalence.
- 794-logical-state EventConv-FC-LIF final slice built and board-checked for the fixed traces above.

Not claimed:

- Full MNIST board accuracy.
- Full MNIST board equivalence.
- Arbitrary EventConv shape/kernel board support.
- Latency.
- Throughput.
- Energy.
- Loihi-compatible, TrueNorth-equivalent, fully asynchronous, or general neuromorphic computer.

## Remaining Real Gates

| Remaining gate | Why still open |
|---|---|
| Full MNIST board accuracy | Current board traces are sparse top-k samples, not full test-set inference. |
| Full MNIST board equivalence | Current board run count is 1 fixed sample + 5 sparse MNIST-derived samples. |
| Arbitrary EventConv shape/kernel | Descriptor evidence is limited to current tiny RTL specialization. |
| Larger event budgets | Current sparse MNIST follow-on uses top-3 image pixels per sample. |
| Performance claims | Same-run measurement method and calibrated counters are not locked. |

## Verifiers

Run:

```bash
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_spikemold_eventconv_trace_smoke.py
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_spikemold_final_goal.py
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_spikemold_mnist_multisample_board.py
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_spikemold_post_lock_followon.py
```

Expected: all print `PASS`.
