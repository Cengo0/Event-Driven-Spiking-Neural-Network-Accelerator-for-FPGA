# FPGA SNN Baseline Comparison

**Purpose**: Paper Section V comparison table (required for all target venues — P0).  
**Status**: Table structure ready; ⚠️ values marked below need verification from actual papers.  
**Last Updated**: 2026-02-21

---

## Table 1 — FPGA SNN Platform Comparison

> **Instructions**: Verify each ⚠️ value by reading the cited paper before finalising.
> Our measured values (annotated with *) are from the PYNQ-Z2 experiments.

| Field | Neil & Liu (FPL 2014) [1] | Pani et al. (TNNLS 2017) [2] | Cheung et al. (FPGA 2016) [3] | **Ours (PYNQ-Z2)** |
|-------|--------------------------|-------------------------------|-------------------------------|---------------------|
| **FPGA Device** | Spartan-6 XC6SLX150T | Virtex-7 / Kintex-7 ⚠️ | Virtex-7 XC7VX485T ⚠️ | Zynq-7020 (PYNQ-Z2) |
| **Neuron Model** | LIF | LIF | LIF / IF | LIF |
| **Neuron Count** | 200 ⚠️ | ~800 ⚠️ | 100K (scalable) ⚠️ | **2,048** |
| **Synapse Count** | 80K ⚠️ | ~640K ⚠️ | varies ⚠️ | 2,048 × 32 = 65K |
| **Learning Rule** | STDP | STDP / recurrent ⚠️ | None (fixed) ⚠️ | STDP / R-STDP |
| **Dataset** | MNIST / DVS ⚠️ | MNIST ⚠️ | benchmarks ⚠️ | MNIST 10-class |
| **Accuracy** | ~95% ⚠️ | ~96% ⚠️ | N/A ⚠️ | **87.1% (SW), FPGA TBD** |
| **LUTs** | ⚠️ | ⚠️ | ⚠️ | 28.76% of Zynq-7020 |
| **BRAMs** | ⚠️ | ⚠️ | ⚠️ | 80.71% of Zynq-7020 |
| **Clock (MHz)** | ⚠️ | ⚠️ | ⚠️ | **100 MHz** |
| **Latency (ms/img)** | ⚠️ | ⚠️ | ⚠️ | TBD (board test) |
| **Power (mW)** | ⚠️ | ⚠️ | ⚠️ | TBD (INA226) |
| **Energy (mJ/img)** | ⚠️ | ⚠️ | ⚠️ | TBD (INA226) |
| **Spike-triggered arch** | Yes | Partial ⚠️ | No (clock-driven) ⚠️ | **Yes (AER spike-router)** |
| **PyTorch compatibility** | No | No | No | **Yes (SpikingJelly)** |
| **On-chip learning** | STDP offline ⚠️ | Limited ⚠️ | No | **Yes (HLS STDP engine)** |
| **Open source** | No | No | No | **Yes (GitHub)** |
| **Target platform pricing** | ~$300–500 ⚠️ | ~$1000+ ⚠️ | ~$3000+ ⚠️ | **~$300 (PYNQ-Z2)** |

---

## Referenced Papers

### [1] Neil & Liu, FPL 2014 — "Minitaur"

**Full citation**:  
D. Neil and S.-C. Liu, "Minitaur, an event-driven FPGA-based spiking network accelerator,"
_IEEE Trans. Very Large Scale Integr. Syst._, vol. 22, no. 12, pp. 2621–2628, Dec. 2014.

> ⚠️ NOTE: This reference appears in multiple forms. The original FPL 2014 conference paper
> vs. the TVLSI 2014 journal version may differ slightly. Verify exact venue and year.

**Key claims (to verify from paper)**:
- Event-driven spike processing using AER FIFO
- LIF neurons with programmable threshold and leak
- MNIST recognition task (digit subset)
- Spartan-6 FPGA resource breakdown (Table in paper)
- No on-chip STDP learning (weights pre-loaded)

**How we are better**:
- Our architecture: 10× more neurons (2,048 vs 200) on a cheaper device
- On-chip STDP/R-STDP learning engine (HLS)
- PyTorch/SpikingJelly integration for model conversion
- Open source + PYNQ-Z2 ($300) vs custom FPGA board

---

### [2] Pani et al., TNNLS 2017 (or JETCAS 2017)

**Full citation (to verify)**:  
D. Pani et al., "An FPGA platform for real-time simulation of spiking neuronal networks,"
_Frontiers in Neuroscience_, 2017.  
OR  
D. Pani et al., "An FPGA implementation of a recurrent spiking neural network for digit
recognition," _IEEE J. Emerg. Sel. Topics Circuits Syst._, 2017.

> ⚠️ NOTE: "Pani et al. 2017" is ambiguous — there are multiple FPGA SNN papers from Pani
> et al. around 2017. The most relevant for MNIST comparison is the JETCAS version.
> Verify the exact paper and citation.

**Key claims (to verify from paper)**:
- LIF SNN on Xilinx FPGA
- MNIST classification benchmark
- Recurrent connections (lateral inhibition)
- Resource usage: LUT, FF, BRAM breakdown
- Accuracy with STDP training

---

### [3] Cheung et al., FPGA 2016 — "NeuroFlow"

**Full citation**:  
B. Cheung, E. Weiss, and B. Olshausen, "Emergence of foveal image sampling from
learning to attend in visual scenes," arXiv, 2016.  
OR (more likely):  
K.-H. Cheung et al., "NeuroFlow: A general purpose spiking neural network simulation
platform using customizable processors on FPGAs," _Proc. ACM/SIGDA FPGA_, 2016, pp. 117–126.

> ⚠️ NOTE: Verify the exact NeuroFlow citation. The ACM FPGA 2016 paper by Cheung et al.
> focuses on scalable simulation, not MNIST accuracy. May need a different "clock-driven"
> baseline or add a 4th paper (e.g., Shen et al. 2016 "Dynamic Fixed Point").

**Key claims (to verify from paper)**:
- Customizable multi-processor SNN simulation on FPGA
- Virtex-7 FPGA, scalable to 100K+ neurons
- Clock-driven (all neurons updated every timestep) — contrasts with our spike-triggered approach
- No learning, no PyTorch integration

---

## Additional Recommended Baselines

The following papers can strengthen the comparison table as optional additions:

| Paper | FPGA | Neurons | Dataset | Notes |
|-------|------|---------|---------|-------|
| Spiking-BERT [FPL 2022] | Alveo U200 | large Transformer | NLP | Different domain |
| Frenkel et al. [ISSCC 2020] | ASIC (ODIN) | 256 | MNIST | Different platform |
| Safa et al. [IEEE TCAS 2022] | Zynq-7020 | 1024 | MNIST | **Best comparison** ⭐ |
| Han et al. [DATE 2020] | Zynq | SNN on Zynq | MNIST | Similar platform |

> ⭐ Prioritise finding a paper that also uses **Zynq-7020** (same device) for a fair
> apples-to-apples resource comparison.

---

## How to Complete This Table

### Step 1: Verify paper details
```bash
# Access papers via:
# IEEE Xplore: https://ieeexplore.ieee.org
# ACM DL: https://dl.acm.org
# arXiv: https://arxiv.org
# Search: "SNN FPGA MNIST LIF Zynq event-driven"
```

### Step 2: Fill in ⚠️ values
For each paper, extract:
- [ ] FPGA device name and family
- [ ] Neuron count and type
- [ ] LUT, FF, BRAM, DSP usage (raw counts or %)
- [ ] Test accuracy on MNIST (or other benchmark)
- [ ] Clock frequency
- [ ] Power consumption (mW) — if reported
- [ ] Inference latency (ms/image) — if reported

### Step 3: Measure our own values
- [ ] Run `tests/fpga_10class_inference.py` → get accuracy + latency
- [ ] Run `tests/ina226_power_measure.py` → get power (mW)
- [ ] Compute energy: `E = P_total × T_latency`

### Step 4: Generate LaTeX table
```python
# Skeleton LaTeX table structure (fill in values):
TABLE = r"""
\begin{table}[t]
\centering
\caption{Comparison of FPGA-based SNN Accelerators}
\label{tab:comparison}
\begin{tabular}{lcccc}
\toprule
 & Neil \& Liu~\cite{neil2014} & Pani et al.~\cite{pani2017}
 & Cheung et al.~\cite{cheung2016} & \textbf{This Work} \\
\midrule
FPGA Device     & Spartan-6  & Virtex-7  & Virtex-7  & \textbf{Zynq-7020} \\
Neurons         & 200        & 800       & 100K      & \textbf{2,048}      \\
Learning        & N/A        & STDP      & N/A       & \textbf{STDP/R-STDP}\\
Accuracy (\%)   & 95.0       & 96.0      & N/A       & \textbf{87.1}$^\dagger$ \\
LUTs (\%)       & --         & --        & --        & \textbf{28.8}       \\
Clock (MHz)     & --         & --        & --        & \textbf{100}        \\
Power (mW)      & --         & --        & --        & \textbf{TBD}        \\
PyTorch API     & \XSolid    & \XSolid   & \XSolid   & \textbf{\CheckmarkBold} \\
Open Source     & \XSolid    & \XSolid   & \XSolid   & \textbf{\CheckmarkBold} \\
\bottomrule
\end{tabular}
\footnotesize{$^\dagger$ SW training accuracy; FPGA deployment in progress}
\end{table}
"""
```

---

## BibTeX Entries

```bibtex
@article{neil2014minitaur,
  author    = {D. Neil and S.-C. Liu},
  title     = {Minitaur, an Event-Driven {FPGA}-based Spiking Network Accelerator},
  journal   = {{IEEE} Trans. Very Large Scale Integr. ({VLSI}) Syst.},
  volume    = {22},
  number    = {12},
  pages     = {2621--2628},
  year      = {2014},
  note      = {Verify: original FPL 2014 vs TVLSI 2014}
}

@article{pani2017fpga,
  author    = {D. Pani and others},
  title     = {{FPGA} Implementation of a Spiking Neural Network for {MNIST}},
  journal   = {{IEEE} J. Emerg. Sel. Topics Circuits Syst.},
  year      = {2017},
  note      = {⚠️ Verify exact citation — multiple Pani et al. 2017 papers}
}

@inproceedings{cheung2016neuroflow,
  author    = {K.-H. Cheung and others},
  title     = {{NeuroFlow}: A General Purpose Spiking Neural Network Simulation
               Platform Using Customizable Processors on {FPGAs}},
  booktitle = {Proc. ACM/SIGDA Int. Symp. Field-Programmable Gate Arrays ({FPGA})},
  year      = {2016},
  pages     = {117--126},
  note      = {⚠️ Verify citation — focuses on simulation scalability, not MNIST accuracy}
}
```

---

## Notes on Fair Comparison

When presenting this table, explicitly note:

1. **Platform difference**: Spartan-6 / Virtex-7 >> Zynq-7020 in capacity. Our result is
   significant precisely because we achieve competitive neuron density on a **$300 accessible
   platform** vs $1K–3K+ research FPGA boards.

2. **Accuracy caveat**: Our 87.1% is SW-training accuracy; the FPGA inference accuracy will
   be reported after the S2MM DMA fix (see `tests/fpga_10class_inference.py`).

3. **Terminology**: Use "spike-triggered gating" (not "event-driven") when comparing with
   [1] and [2] which also claim event-driven execution — distinguish our specific AER-based
   hardware implementation.

4. **Clock-driven baseline [3]**: NeuroFlow is the best example of a completely clock-driven
   design, each neuron updated every timestep — contrasts with our spike-triggered approach
   (only neurons with incoming spikes are updated). Cite for the O(N×T) vs O(k×T) argument.
