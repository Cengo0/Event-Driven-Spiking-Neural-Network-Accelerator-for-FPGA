# SpikeMold Final Goal Lock Report

Date: 2026-06-20
Target: PYNQ-Z2 / Zynq-7020
Status: **LOCKED for fixed MNIST EventConv-FC sample equivalence only**

## Frozen Slice

- Model: `EventConv(1x28x28, 4 filters, 3x3, stride 2, padding 1) -> sparse FC-LIF(784->10)`
- Hardware states: `794` (`784` EventConv states + `10` readout states)
- Physical neurons configured in runtime artifact: `1024`
- Backend mode: `2`
- Router fanout limit: `32`; artifact readout max fanout: `10`
- Training gate: `95.44%` final validation accuracy (`>=90%` required before synthesis)
- Artifact source: `trained_or_existing_artifact_runtime_prefix_migrated`

## Locked Artifacts

| Artifact | SHA-256 |
|---|---|
| `outputs/artifacts/mnist_eventconv_fclif_frozen.json` | file `21a9faa8f0469f329ab193f3a50a25053f08e862bc2458e240775b02fc74e58c`, manifest `439b702ee516b7564f08143bfd63b2cb46d185a42aba9436ca00fa979f9fd8dd` |
| `golden_traces/v1/mnist_eventconv_fclif_frozen_v1.json` | file `dc7f57038deeb154fb02621a0a94f6c84e31aaf906e36315367cbfa6cc4801ff`, trace `4c543d8041c641c4f8351134c9dc77acd1e8483616ed5eb94d3b947f5da64a35` |
| `outputs/runtime/mnist_eventconv_fclif_config_plan.json` | `68e7a70c3aa02d3cc0a66c7a64c6a627a6389348b6a5b03f4caef3ad02e8cbcb` |
| `outputs/spikemold_pynq_z2_frozen_mnist_10mhz.bit` | `c307b9b8bfeb7bc33be3ee9275f28130ff5027db012b10e00392078e45257b09` |
| `outputs/spikemold_pynq_z2_frozen_mnist_10mhz.hwh` | `2816d9ad88f736ac9b9b6cfa585c817ee606be7bd02a8151b95687061d29d355` |
| `outputs/board/eventconv_fclif_frozen_mnist_10mhz_result_20260620.json` | `b0beca695277f7776596e442c0a8147e79ce36e1a13a27551f8c5ce93369e278` |

## Runtime Contract

- Config plan schema: `spikemold.eventconv_fclif_config_plan.v1`
- Kernel config prefix: `0x03000000`
- Router clear/count prefix remains outside kernel prefix space.
- Kernel config writes: `9`
- Router config writes: `6625`
- Expected output words: `36`
- Golden trace commit count: `36`
- RTL top: `hardware/hdl/rtl/top/spikemold_integrated_top.v`

## Build Evidence

Vivado rebuild command:

```bash
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && source /tools/Xilinx/2025.2/Vivado/settings64.sh && SPIKEMOLD_PL_CLK_MHZ=10 SPIKEMOLD_TOP_NUM_NEURONS=800 SPIKEMOLD_ROUTER_BUFFER_DEPTH=256 SPIKEMOLD_DISABLE_WEIGHT_DMA=1 SPIKEMOLD_SYNTH_DIRECTIVE=RuntimeOptimized SPIKEMOLD_OUTPUT_BASENAME=spikemold_pynq_z2_frozen_mnist_10mhz rtk vivado -mode batch -source hardware/scripts/rebuild_integrated.tcl
```

Result:

- `write_bitstream` completed successfully.
- Timing met: WNS `58.849 ns`, TNS `0.000 ns`, WHS `0.031 ns`, THS `0.000 ns`.
- Utilization: LUT `26298 / 53200 (49.43%)`, FF `33089 / 106400 (31.10%)`, BRAM tile `97 / 140 (69.29%)`, DSP `4 / 220 (1.82%)`.

## RTL Xsim Evidence

Command:

```bash
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk bash hardware/scripts/run_testbenches.sh
```

Result:

- `420 PASS, 0 FAIL`
- `*** ALL TESTS PASSED ***`

## Board Evidence

Board command:

```bash
cd /home/xilinx/spikemold_final_goal && sudo -n env XILINX_XRT=/usr /usr/local/share/pynq-venv/bin/python3 scripts/run_spikemold_pynq_eventconv_fclif.py --bitstream outputs/spikemold_pynq_z2_frozen_mnist_10mhz.bit --hwh outputs/spikemold_pynq_z2_frozen_mnist_10mhz.hwh --artifact outputs/artifacts/mnist_eventconv_fclif_frozen.json --trace golden_traces/v1/mnist_eventconv_fclif_frozen_v1.json --output-json outputs/board/eventconv_fclif_frozen_mnist_10mhz_result_20260620.json --timeout-seconds 600 --time-steps 4096
```

Result:

- `ok: true`
- `board_executed: true`
- `output_words_match: true`
- `output_event_count_exact: true`
- `output_emit_count_exact: true`
- `no_output_drops: true`
- Output words: `36`
- Expected words: `36`
- Board JSON elapsed host time: `5.287022965960205 s`

Elapsed host time is recorded only as run metadata. It is not a latency or throughput claim.

## Claim Boundary

Allowed claim:

```text
SpikePress trained/frozen a small MNIST EventConv-FC-LIF slice above the 90% software gate,
compiled it into a SpikeMold runtime artifact, generated an integer golden trace and board
config plan, rebuilt the PYNQ-Z2 bit/HWH, and verified one fixed MNIST EventConv-FC sample
equivalence on board with exact 36-word output match and zero output drops.
```

Required exact boundary:

- fixed MNIST EventConv-FC sample equivalence only
- Not claimed: full MNIST board accuracy
- Not claimed: latency
- Not claimed: throughput
- Not claimed: energy
- Not claimed: arbitrary EventConv shape/kernel support

## Final Verifier Commands

```bash
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_spikemold_batch0_1a.py
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_batch1b_transport.py
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_batch1c_eventconv.py
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_verifier_gate.py
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_spikemold_build_evidence_report.py
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_architecture_selection.py
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk python scripts/check_spikemold_final_goal.py
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk pytest -q software/python/tests/test_architecture_trace_generator.py software/python/tests/test_spikemold_transport.py software/python/tests/test_spikemold_artifact.py software/python/tests/test_spikemold_training.py
source /home/jwlee/miniconda3/etc/profile.d/conda.sh && conda activate fpga && rtk bash hardware/scripts/run_testbenches.sh
```

Expected result: the seven checker commands print `PASS`, the targeted Python suite prints `32 passed`, and the RTL xsim suite prints `420 PASS, 0 FAIL`.

## Next Gates Outside This Lock

- Full MNIST board-equivalence or board-accuracy run.
- Descriptor-configured arbitrary EventConv board proof.
- Wider network/state-space board proof.
- Same-run measured latency, throughput, and energy methodology.

Follow-on multi-sample sparse MNIST-derived board evidence is recorded in
`reports/spikemold_mnist_multisample_board_report.md`. It does not expand the
claim boundary to full MNIST board accuracy.

Follow-on top-8 sparse MNIST-derived board evidence is recorded in
`reports/spikemold_mnist_top8_board_report.md`. It increases the sparse input
event budget only; it is not full MNIST board accuracy.

Post-lock evidence reconciliation is recorded in
`reports/spikemold_post_lock_followon_report.md`.
