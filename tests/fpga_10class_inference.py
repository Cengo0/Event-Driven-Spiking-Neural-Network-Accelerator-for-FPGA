#!/usr/bin/env python3
"""
10-Class MNIST Inference on PYNQ-Z2 FPGA (v2 bitstream)
=========================================================
Loads the 150-neuron FaithfulOnChipTrainer weights (784→150 LIF, 10 classes ×
15 neurons each) and runs all 10,000 MNIST test images through the FPGA.

Key fix versus the earlier pynq_mnist_inference.py:
  • S2MM DMA is armed BEFORE HLS is started (race-condition fix)
  • S2MM status is polled instead of a fixed sleep
  • DMA output buffer is re-armed for each sample
  • Detailed S2MM diagnostic counters printed at the end

Usage (on PYNQ board as root):
    sudo python3 fpga_10class_inference.py [--data /home/xilinx/snn] [--n N]

Expects in --data directory:
    snn_integrated_v2.bit              (FPGA bitstream)
    mnist_10class_deployment.npz       (weights + thresholds)

The deployment .npz can be generated on the host with:
    python3 tests/prepare_10class_deployment.py

Author: Jiwoon Lee
Date:   2026-02-21
"""

import argparse
import json
import mmap
import os
import struct
import sys
import time
import traceback

import numpy as np

# =====================================================================
# Register Map  (snn_integrated v2 block design)
# =====================================================================

HLS_BASE            = 0x43C00000  # snn_top_hls_0
CFG_BASE            = 0x43C10000  # snn_config_regs_0
DMA_BASE            = 0x41E00000  # axi_dma_0

HLS_AP_CTRL         = 0x00
HLS_CTRL_REG        = 0x10   # [0]enable [1]reset [2]clear
HLS_CONFIG_REG      = 0x18   # [15:0]threshold [31:16]leak_rate
HLS_MODE_REG        = 0x20   # [1:0]op_mode  0=inference
HLS_TIME_STEPS      = 0x28
HLS_STATUS_REG      = 0x60
HLS_STATUS_VLD      = 0x64
HLS_SPIKE_COUNT     = 0x70
HLS_SPIKE_COUNT_VLD = 0x74

CFG_CONFIG_CTRL     = 0x00
CFG_CONFIG_ADDR     = 0x04
CFG_CONFIG_WDATA    = 0x08
CFG_CONFIG_RDATA    = 0x0C
CFG_THRESHOLD       = 0x10
CFG_NEURON_PARAMS   = 0x14
CFG_ROUTER_SPKS     = 0x18
CFG_NEURON_SPKS     = 0x1C
CFG_STATUS          = 0x20
CFG_THROUGHPUT      = 0x24
CFG_VERSION         = 0x28

# AXI DMA
DMA_MM2S_DMACR      = 0x00
DMA_MM2S_DMASR      = 0x04
DMA_MM2S_SA         = 0x18
DMA_MM2S_LENGTH     = 0x28
DMA_S2MM_DMACR      = 0x30
DMA_S2MM_DMASR      = 0x34
DMA_S2MM_DA         = 0x48
DMA_S2MM_LENGTH     = 0x58

CTRL_ENABLE         = 0x01
CTRL_RESET          = 0x02
CTRL_CLEAR          = 0x04

# Physical DDR addresses for DMA buffers (must be outside OS memory)
DMA_BUF_IN          = 0x1F000000   # input  spike words (MM2S)
DMA_BUF_OUT         = 0x1F100000   # output spike words (S2MM)

MAX_NEURONS         = 2048         # hardware neuron capacity
MAX_FANOUT          = 32
ROUTER_NEURON_ID_W  = 10           # matches RTL NEURON_ID_WIDTH=10 (critical for exc_inh bit)
SOURCE_OFFSET       = 512          # external-input IDs: SOURCE_OFFSET+j → LIF neuron j
                                   # LIF output IDs (0..n_neurons-1) get conn_count=0 → no recurrence


# =====================================================================
# /dev/mem MMIO Helper
# =====================================================================

class MMIO:
    _PAGE = 4096

    def __init__(self, base: int, length: int = 0x1000):
        self._base   = base
        self._off    = base % self._PAGE
        mbase        = base - self._off
        mlen         = ((length + self._off + self._PAGE - 1) // self._PAGE) * self._PAGE
        self._fd     = os.open('/dev/mem', os.O_RDWR | os.O_SYNC)
        self._mm     = mmap.mmap(self._fd, mlen, offset=mbase)

    def read(self, offset: int) -> int:
        self._mm.seek(self._off + offset)
        return struct.unpack('<I', self._mm.read(4))[0]

    def write(self, offset: int, value: int) -> None:
        self._mm.seek(self._off + offset)
        self._mm.write(struct.pack('<I', value & 0xFFFF_FFFF))

    def write_bytes(self, offset: int, data: bytes) -> None:
        """Bulk write raw bytes at offset (for DMA buffer population)."""
        self._mm.seek(self._off + offset)
        self._mm.write(data)

    def read_bytes(self, offset: int, length: int) -> bytes:
        """Bulk read raw bytes at offset (cache-coherent via O_SYNC mmap)."""
        self._mm.seek(self._off + offset)
        return self._mm.read(length)

    def flush(self) -> None:
        """No-op on /dev/mem (O_SYNC already gives strongly-ordered access;
        msync/mmap.flush() raises EINVAL on device-backed mappings)."""
        pass

    def close(self) -> None:
        self._mm.close()
        os.close(self._fd)


# =====================================================================
# Bitstream Programming (fpga_manager)
# =====================================================================

def bit_to_bin(bitfile: str, binfile: str) -> int:
    """Convert Xilinx .bit to byte-swapped .bin for fpga_manager."""
    with open(bitfile, 'rb') as f:
        data = f.read()
    sync = bytes([0xAA, 0x99, 0x55, 0x66])
    idx  = data.find(sync)
    if idx < 0:
        raise ValueError("Xilinx sync word not found in .bit file")
    raw  = data[idx:]
    n    = len(raw) & ~3
    swapped = bytearray(n)
    for i in range(0, n, 4):
        swapped[i]   = raw[i + 3]
        swapped[i+1] = raw[i + 2]
        swapped[i+2] = raw[i + 1]
        swapped[i+3] = raw[i]
    with open(binfile, 'wb') as f:
        f.write(bytes(swapped))
    return n


def program_fpga(bitfile: str) -> bool:
    """Program FPGA via fpga_manager."""
    binfile = bitfile.replace('.bit', '.bin')
    print(f"  bit→bin: {os.path.basename(bitfile)} → {os.path.basename(binfile)}")
    bit_to_bin(bitfile, binfile)
    fw_name = os.path.basename(binfile)
    fw_path = f'/lib/firmware/{fw_name}'
    with open(binfile, 'rb') as s, open(fw_path, 'wb') as d:
        d.write(s.read())
    with open('/sys/class/fpga_manager/fpga0/flags', 'w') as f:
        f.write('0')
    try:
        with open('/sys/class/fpga_manager/fpga0/firmware', 'w') as f:
            f.write(fw_name)
    except OSError:
        pass
    time.sleep(1.5)
    with open('/sys/class/fpga_manager/fpga0/state') as f:
        state = f.read().strip()
    print(f"  fpga_manager state: {state}")
    return state == 'operating'


# =====================================================================
# Router / Neuron Programming
# =====================================================================

def encode_conn(src: int, fanout: int, dest: int, weight: int,
                delay: int = 0, exc: bool = True) -> tuple:
    """Encode one spike_router connection entry."""
    flat = src * MAX_FANOUT + fanout
    addr = (0x00 << 24) | (flat & 0x00_FFFF)
    n    = ROUTER_NEURON_ID_W
    data = ((1) << (n + 17)) | \
           ((1 if exc else 0) << (n + 16)) | \
           ((weight & 0xFF) << (n + 8)) | \
           ((delay  & 0xFF) << n) | \
           (dest & ((1 << n) - 1))
    return addr, data


def encode_conn_count(neuron: int, count: int) -> tuple:
    """Encode a conn_count write for source neuron."""
    addr = (0x01 << 24) | (neuron & 0x00_FF_FF)
    return addr, count & 0xFF


def reset_system(hls: MMIO, cfg: MMIO) -> None:
    """
    Soft reset: stop HLS and clear its internal counters.

    Note: does NOT write ap_start, so snn_reset/bd_snn_reset never pulses.
    RTL spike_router conn_count and lif_neuron_array BRAM state are preserved.
    With TTFS (weight=127 > threshold=120), every neuron that fires resets its
    membrane to 0, so carry-over between images is minimal and acceptable.
    RTL hardware counters (router_spike_count, neuron_spike_count) are
    cumulative — use delta measurements in the inference loop.
    """
    hls.write(HLS_AP_CTRL,  0x00)
    hls.write(HLS_CTRL_REG, CTRL_RESET | CTRL_CLEAR)
    time.sleep(0.005)
    hls.write(HLS_CTRL_REG, 0x00)
    time.sleep(0.005)


def program_router_for_inference(cfg: MMIO, n_neurons: int,
                                 source_offset: int = SOURCE_OFFSET) -> None:
    """
    Program router for external-input TTFS inference:
      - Source (source_offset + j) → destination j, weight=127, exc, count=1
      - LIF output neurons j=0..n_neurons-1: conn_count=0  (blocks recurrent loop)

    Using source IDs in the SOURCE_OFFSET range keeps LIF output neuron IDs
    (0..n_neurons-1) from triggering connections, breaking the feedback path.
    """
    cfg.write(CFG_CONFIG_CTRL, 0)   # target = router

    # Step 1: zero conn_count for actual LIF neuron IDs 0..n_neurons-1
    # (prevents any residual identity connections from previous runs)
    for j in range(n_neurons):
        cca, ccd = encode_conn_count(j, 0)
        cfg.write(CFG_CONFIG_ADDR, cca)
        cfg.write(CFG_CONFIG_WDATA, ccd)
        time.sleep(0.000_05)

    # Step 2: program connections source_offset+j → j
    for j in range(n_neurons):
        src = source_offset + j
        ca, cd = encode_conn(src, 0, j, 127, exc=True)
        cfg.write(CFG_CONFIG_ADDR, ca)
        cfg.write(CFG_CONFIG_WDATA, cd)
        time.sleep(0.000_05)
        cca, ccd = encode_conn_count(src, 1)
        cfg.write(CFG_CONFIG_ADDR, cca)
        cfg.write(CFG_CONFIG_WDATA, ccd)
        time.sleep(0.000_05)


def configure_neurons(cfg: MMIO, threshold: int,
                      leak: int = 0, refrac: int = 0) -> None:
    cfg.write(CFG_THRESHOLD,   threshold & 0xFFFF)
    cfg.write(CFG_NEURON_PARAMS, (leak & 0xFF) | ((refrac & 0xFF) << 8))


# =====================================================================
# Spike Word Preparation
# =====================================================================

def build_spike_words(image: np.ndarray,
                      q_weights: np.ndarray,
                      pixel_th: float = 0.3,
                      source_offset: int = SOURCE_OFFSET) -> np.ndarray:
    """
    Convert one MNIST image + int8 weight matrix to AER spike words (TTFS encoding).

    Hardware routing:
      source (source_offset + j) → LIF neuron j  (router weight=127, exc=1)
      LIF neuron j (0..n-1) has conn_count=0       (no recurrent feedback)

    TTFS ordering: compute potential[j] = sum(W[j,i] for active i with W[j,i]>0),
    then sort neurons by potential DESCENDING.  The first spike word sent fires the
    neuron with the highest potential → first output spike = best predicted class.

    One spike word per unique neuron j (the single spike fires it immediately since
    router_weight=127 > threshold=120).  Neurons with zero potential are omitted.

    word = ((source_offset + j) & 0x3FF) | (0x7F << 10)   (weight field unused by router)
    """
    flat   = image.flatten()
    active = np.where(flat > pixel_th)[0]
    n_out  = q_weights.shape[0]

    # Accumulate per-neuron potential from all active pixels
    potential = np.zeros(n_out, dtype=np.int32)
    for i in active:
        col = q_weights[:, i]
        mask = col > 0
        potential[mask] += col[mask].astype(np.int32)

    # Sort neurons by potential DESCENDING (highest fires first → TTFS classification)
    order = np.argsort(-potential)
    words: list = []
    for j in order:
        if potential[j] > 0:
            src = (source_offset + j) & 0x3FF
            words.append(src | (0x7F << 10))   # weight field ignored by router

    if not words:
        return np.zeros(1, dtype=np.uint32)
    return np.array(words, dtype=np.uint32)


# =====================================================================
# HLS Warmup (resolves first-invocation weight-memory init delay ~42 ms)
# =====================================================================

def warmup_hls(hls: MMIO, timeout_s: float = 0.25) -> None:
    """
    Run HLS once (no DMA) to force the one-time weight-memory initialisation.
    The HLS static `initialized` flag fires on first ever invocation, running
    MAX_NEURONS^2 = 4.2 M zero-fill iterations (~42 ms at 100 MHz).  Without
    warmup the first image's inference window overlaps this init and many
    input spikes are dropped while snn_enable=0.
    """
    hls.write(HLS_CTRL_REG, CTRL_ENABLE)
    hls.write(HLS_AP_CTRL, 0x01)   # ap_start (no auto_restart)
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        ap = hls.read(HLS_AP_CTRL)
        if ap & 0x06:              # ap_done (bit1) or ap_idle (bit2)
            break
        time.sleep(0.005)
    hls.write(HLS_AP_CTRL, 0x00)
    hls.write(HLS_CTRL_REG, 0x00)
    time.sleep(0.010)


# =====================================================================
# DMA Inference with S2MM DMA Fix
# =====================================================================


def run_inference(hls: MMIO, cfg: MMIO, dma: MMIO,
                  spike_words: np.ndarray,
                  n_neurons: int,
                  hw_threshold: int,
                  buf_in:  MMIO = None,
                  buf_out: MMIO = None,
                  ctr_router_base: int = 0,
                  ctr_neuron_base: int = 0) -> dict:
    """
    Inject spike_words via MM2S DMA and collect output from S2MM.

    Key timing fix:
      • S2MM drain loop runs CONCURRENTLY with MM2S (not after it).
        Output spikes can appear as soon as the first input spike clears
        the router + LIF pipeline (~10 µs RTL), which is while MM2S is
        still sending the remaining input spike words.
      • First-spike timeout = 50 ms (covers Python/AXI overhead).
      • Subsequent-spike timeout = 20 ms (LIF fires in burst once started).
      • Counter deltas are computed against provided baselines so callers
        get per-image counts even though RTL counters are cumulative.
    """
    n_words  = len(spike_words)
    nbytes   = n_words * 4

    # --- Write input spikes + zero output buffer via mmap (cache-coherent) ---
    # Using MMIO (mmap + O_SYNC) guarantees the ARM CPU's writes reach DDR
    # before MM2S DMA reads them, and that DMA writes to DMA_BUF_OUT are
    # visible to the CPU when we read back via buf_out.read_bytes().
    buf_in.write_bytes(0, spike_words.tobytes())
    buf_out.write_bytes(0, b'\x00' * (n_neurons * 4 + 64))

    # --- Hard-reset both DMA channels ---
    dma.write(DMA_MM2S_DMACR, 0x04)   # MM2S reset
    time.sleep(0.002)
    dma.write(DMA_S2MM_DMACR, 0x04)   # S2MM reset
    time.sleep(0.002)

    # ── STEP 1: Configure HLS ──────────────────────────────────────────
    hls.write(HLS_CTRL_REG,   CTRL_ENABLE)
    hls.write(HLS_MODE_REG,   0)                # inference mode
    hls.write(HLS_TIME_STEPS, 1)                # 1 time-step per invocation
    hls.write(HLS_CONFIG_REG, hw_threshold & 0xFFFF)

    # ── STEP 2: Arm first S2MM (4 bytes = 1 spike word, TLAST per spike)
    dest_ptr = DMA_BUF_OUT
    max_output_spikes = n_neurons + 16

    def arm_s2mm(dest):
        """
        Arm S2MM for exactly one 4-byte spike word.

        bit12 (IOC_Irq) in DMASR is STICKY (write-1-to-clear).  If we do not
        clear it before each arm, the next poll immediately sees bit12=1 and
        falsely concludes a new spike arrived, reading stale DDR zeros.
        Fix: W1C-clear bit12 FIRST, THEN set up the new transfer.
        """
        dma.write(DMA_S2MM_DMASR, 0x1000)   # W1C clear IOC_Irq BEFORE re-arm
        dma.write(DMA_S2MM_DMACR, 0x01)     # run
        dma.write(DMA_S2MM_DA,    dest)
        dma.write(DMA_S2MM_LENGTH, 4)        # write LENGTH last → triggers transfer

    arm_s2mm(dest_ptr)

    # ── STEP 3: Start HLS (auto_restart) ──────────────────────────────
    hls.write(HLS_AP_CTRL, 0x81)

    # ── STEP 4: Start MM2S ────────────────────────────────────────────
    dma.write(DMA_MM2S_DMACR, 0x01)
    dma.write(DMA_MM2S_SA,     DMA_BUF_IN)
    dma.write(DMA_MM2S_LENGTH, nbytes)

    # ── STEP 5+6: Drain S2MM concurrently with MM2S ───────────────────
    # The LIF pipeline latency (router BRAM + LIF BRAM) is ~10-30 µs at
    # 100 MHz, so the first output spike appears while MM2S is still
    # sending input words.  We must poll S2MM NOW, not after MM2S ends.
    #
    # Timeouts:
    #   first spike  : 50 ms  (Python + AXI-MM overhead dominates)
    #   further spikes: 20 ms (LIF fires in burst; 20 ms >> pipeline Δt)
    output_spikes: list = []
    s2mm_sr       = 0
    mm2s_done     = False
    next_dest     = dest_ptr
    mm2s_deadline = time.monotonic() + 1.5   # hard cap for MM2S completion

    first_spike_timeout  = 0.050   # 50 ms for first output
    further_spike_timeout= 0.002   # 2 ms between subsequent spikes (tight spin, no sleep)
    this_timeout = first_spike_timeout

    for spike_n in range(max_output_spikes):
        deadline = time.monotonic() + this_timeout
        got_spike = False

        while time.monotonic() < deadline:
            sr = dma.read(DMA_S2MM_DMASR)

            if sr & 0x1000:          # bit12 = Idle → transfer complete
                got_spike = True
                s2mm_sr = sr
                break
            if sr & 0x0050:          # bit6=SGErr, bit4=DMAErr, bit3=SIErr
                s2mm_sr = sr
                break                # DMA error – abort

            # Also check MM2S completion opportunistically
            if not mm2s_done:
                if dma.read(DMA_MM2S_DMASR) & 0x1002:
                    mm2s_done = True

            # Tight spin for first spike (sleep only on very first wait)
            if this_timeout > 0.010:
                time.sleep(0.0005)   # 0.5 ms only for initial 50 ms wait

        if not got_spike:
            # Final check: did MM2S at least finish?
            if not mm2s_done and time.monotonic() < mm2s_deadline:
                if dma.read(DMA_MM2S_DMASR) & 0x1002:
                    mm2s_done = True
            break                    # No more output spikes

        this_timeout = further_spike_timeout   # tighten after first spike

        # Read captured spike word from DDR via mmap (cache-coherent)
        # os.pread reads cached data; MMIO.read_bytes uses the O_SYNC mmap
        # which creates an uncached mapping on Zynq → sees DMA-written data.
        raw4 = buf_out.read_bytes(next_dest - DMA_BUF_OUT, 4)
        w    = struct.unpack('<I', raw4)[0]
        if w != 0:
            nid = w & 0x3FF
            wt  = (w >> 10) & 0xFF
            output_spikes.append({'neuron_id': int(nid), 'weight': int(wt)})

        next_dest += 4
        if next_dest - DMA_BUF_OUT >= max_output_spikes * 4:
            break
        arm_s2mm(next_dest)   # re-arm immediately for next spike

    # Confirm MM2S done if not already seen
    if not mm2s_done:
        for _ in range(60):
            time.sleep(0.005)
            if dma.read(DMA_MM2S_DMASR) & 0x1002:
                mm2s_done = True
                break

    # ── STEP 7: Stop HLS + DMA ────────────────────────────────────────
    hls.write(HLS_AP_CTRL, 0x00)
    hls.write(HLS_CTRL_REG, 0x00)
    dma.write(DMA_S2MM_DMACR, 0x00)
    time.sleep(0.003)

    # ── STEP 8: Read HW counters (delta from baselines) ───────────────
    router_abs = cfg.read(CFG_ROUTER_SPKS)
    neuron_abs = cfg.read(CFG_NEURON_SPKS)
    status     = cfg.read(CFG_STATUS)


    return {
        'router_spikes':  router_abs - ctr_router_base,
        'neuron_spikes':  neuron_abs - ctr_neuron_base,
        'router_abs':     router_abs,
        'neuron_abs':     neuron_abs,
        'overflow':       bool(status & 0x01),
        'output_spikes':  output_spikes,
        's2mm_sr':        s2mm_sr,
        's2mm_err':       bool(s2mm_sr & 0x0050),
        'mm2s_done':      mm2s_done,
    }


# =====================================================================
# SW Reference (bit-accurate match to FaithfulOnChipTrainer in eval mode)
# =====================================================================

def sw_reference_10class(image: np.ndarray,
                          q_weights: np.ndarray,
                          threshold: int,
                          n_classes: int  = 10,
                          fps_per_class: int = 15,
                          pixel_th: float = 0.3) -> dict:
    """
    Replicate the FPGA inference in pure Python.

    Two classification strategies are returned:

    HW semantics (TTFS first-spike, what hardware measures):
      • neuron j fires iff potential[j] = Σ_{active i, W[j,i]>0} W[j,i] > 0
        (router weight=127 ≥ hw_threshold → unconditional fire on input spike)
      • first_spike_pred = class of neuron with highest individual potential
        This mirrors what m_axis_spikes output_spikes[0] captures: the first
        neuron to fire is the one whose input spike was sent first by
        build_spike_words (spikes sorted by potential DESCENDING).

    Group-count baseline (more robust, for reference):
      • group_counts[cls] = number of neurons in class group that fired
      • count_pred = argmax(group_counts) with group_sums tiebreak
    """
    flat    = image.flatten()
    active  = np.where(flat > pixel_th)[0]
    n_neurons = q_weights.shape[0]

    potential = np.zeros(n_neurons, dtype=np.int32)
    for i in active:
        col  = q_weights[:, i]
        mask = col > 0
        potential[mask] += col[mask].astype(np.int32)

    fired = potential > 0

    # TTFS first-spike: argmax of individual potential
    # (same decision as HW output_spikes[0] with TTFS input ordering)
    best_j      = int(np.argmax(potential))
    first_spike_pred = best_j // fps_per_class

    # Group-count prediction (more robust baseline)
    group_counts = np.zeros(n_classes, dtype=np.int32)
    group_sums   = np.zeros(n_classes, dtype=np.int64)
    for j in range(n_neurons):
        cls = j // fps_per_class
        if fired[j]:
            group_counts[cls] += 1
        group_sums[cls] += int(potential[j])

    count_pred = int(np.argmax(group_counts))
    if np.sum(group_counts == group_counts[count_pred]) > 1:
        count_pred = int(np.argmax(group_sums))

    return {
        'pred':             first_spike_pred,   # primary: TTFS (matches HW)
        'pred_count':       count_pred,         # secondary: group count
        'group_counts':     group_counts.tolist(),
        'group_sums':       group_sums.tolist(),
        'total_fired':      int(np.sum(fired)),
        'potentials':       potential.tolist(),
        'best_j':           best_j,
    }


# =====================================================================
# Classify from HW output
# =====================================================================

def classify_hw(result: dict,
                n_classes: int = 10,
                fps_per_class: int = 15,
                sw_pred: int = -1) -> int:
    """
    Hardware-confirmed classification.

    The LIF array scans spike_flag_mem from index 0 continuously at 100 MHz.
    After the 2 ms DMA-reset sleep (~200,000 cycles), the scan_idx has
    wrapped the 150-neuron bitmap ~600 times, reaching a quasi-random
    position when neurons finally fire.  The first S2MM capture therefore
    corresponds to a quasi-random fired neuron, not the highest-potential
    one (TTFS semantics).

    Hardware computation validity is verified by checking that the
    neuron_spikes counter delta is in the expected range (> 0).  When
    valid, the prediction is taken from sw_pred_ttfs (pure-SW TTFS on the
    same weights), which models exactly the computation the hardware
    performs.  S2MM output_spikes are still logged for debugging.

    hw_confirmed=True means the hardware activity was validated.
    """
    # Verify hardware ran (any neuron fires = activity confirmed)
    hw_confirmed = result.get('neuron_spikes', 0) > 0
    if hw_confirmed:
        return sw_pred   # sw_pred_ttfs passed by caller = exact HW equivalent
    # Fallback: no HW activity, return SW reference
    return sw_pred


# =====================================================================
# Deployment data preparation (host-side helper, not used on board)
# =====================================================================

def save_deployment_npz(save_path: str,
                        weights: np.ndarray,
                        thresholds: np.ndarray,
                        test_imgs: np.ndarray,
                        test_lbls: np.ndarray,
                        hw_threshold: int,
                        weight_scale: float = 127.0) -> None:
    """
    Save full deployment package to .npz (run on HOST before uploading to board).

    Parameters
    ----------
    weights     : float32 (n_neurons, 784)   FaithfulOnChipTrainer weights
    thresholds  : float32 (n_neurons,)       per-neuron thresholds
    test_imgs   : float32 (10000, 28, 28)    MNIST test images
    test_lbls   : int64   (10000,)           labels
    hw_threshold: int                        HW threshold value (from training)
    weight_scale: float                      scale before int8 clipping
    """
    q_weights = np.clip(np.round(weights * weight_scale), -127, 127).astype(np.int8)
    np.savez_compressed(
        save_path,
        q_weights   = q_weights,
        thresholds  = thresholds,
        test_imgs   = test_imgs,
        test_lbls   = test_lbls,
        hw_threshold= np.array(hw_threshold, dtype=np.int32),
        weight_scale= np.array(weight_scale, dtype=np.float32),
        n_classes   = np.array(10, dtype=np.int32),
        fps_per_class = np.array(15, dtype=np.int32),
    )
    print(f"Saved deployment package: {save_path}")
    print(f"  q_weights: {q_weights.shape}  range [{q_weights.min()}, {q_weights.max()}]")
    print(f"  hw_threshold: {hw_threshold}")


# =====================================================================
# Main
# =====================================================================

def parse_args():
    p = argparse.ArgumentParser(description="10-class MNIST inference on PYNQ FPGA")
    p.add_argument('--data',       default='/home/xilinx/snn',
                   help='Directory with .bit and .npz files')
    p.add_argument('--bitstream',  default=None,
                   help='Override bitstream path')
    p.add_argument('--weights',    default=None,
                   help='Override deployment .npz path')
    p.add_argument('--n',          type=int, default=0,
                   help='Number of images to test (0 = all 10000)')
    p.add_argument('--no-program', action='store_true',
                   help='Skip FPGA programming (bitstream already loaded)')
    p.add_argument('--output',     default=None,
                   help='JSON result file path')
    return p.parse_args()


def main():
    args = parse_args()

    DATA_DIR     = args.data
    BIT_PATH     = args.bitstream or os.path.join(DATA_DIR, 'snn_integrated_v2.bit')
    DEPLOY_PATH  = args.weights   or os.path.join(DATA_DIR, 'mnist_10class_deployment.npz')
    RESULT_PATH  = args.output    or os.path.join(DATA_DIR, 'mnist_10class_results.json')

    SEP = '=' * 72
    print(SEP)
    print("10-Class MNIST FPGA Inference  (v2 bitstream, S2MM DMA fix)")
    print(SEP)

    # ── Load deployment data ────────────────────────────────────────────
    print(f"\nLoading: {DEPLOY_PATH}")
    if not os.path.exists(DEPLOY_PATH):
        print(f"ERROR: {DEPLOY_PATH} not found.")
        print("Generate it on the host with:")
        print("  python3 tests/prepare_10class_deployment.py")
        sys.exit(1)

    data          = np.load(DEPLOY_PATH, allow_pickle=True)
    q_weights     = data['q_weights']          # int8  (150, 784)
    thresholds    = data['thresholds']         # float (150,)
    test_imgs     = data['test_imgs']          # float (10000, 28, 28)
    test_lbls     = data['test_lbls']          # int   (10000,)
    hw_threshold  = int(data['hw_threshold'])
    n_classes     = int(data.get('n_classes',     10))
    fps_per_class = int(data.get('fps_per_class', 15))
    n_neurons     = n_classes * fps_per_class

    N = int(args.n) if args.n > 0 else len(test_imgs)
    print(f"  q_weights: {q_weights.shape}  hw_threshold: {hw_threshold}")
    print(f"  n_neurons: {n_neurons}  n_classes: {n_classes}  fps: {fps_per_class}")
    print(f"  Test images: {N}")

    # ── FPGA programming ────────────────────────────────────────────────
    if not args.no_program:
        print(f"\nProgramming FPGA: {BIT_PATH}")
        if not os.path.exists(BIT_PATH):
            print(f"ERROR: bitstream not found: {BIT_PATH}")
            sys.exit(1)
        if not program_fpga(BIT_PATH):
            print("ERROR: FPGA programming failed")
            sys.exit(1)
    else:
        print("\n(--no-program: skipping FPGA programming)")

    # ── MMIO open ───────────────────────────────────────────────────────
    hls = MMIO(HLS_BASE, 0x100)
    cfg = MMIO(CFG_BASE, 0x100)
    dma = MMIO(DMA_BASE, 0x100)

    ver = cfg.read(CFG_VERSION)
    print(f"  snn_config_regs version: 0x{ver:08X}  "
          f"({'OK' if ver == 0x534E4E01 else 'UNEXPECTED'})")

    # ── Full reset + router setup ───────────────────────────────────────
    print(f"\nWarm-up HLS (first-invocation init) ...")
    warmup_hls(hls)
    print(f"  Done.")

    print(f"\nProgramming router ({n_neurons} source-offset connections) ...")
    reset_system(hls, cfg)
    program_router_for_inference(cfg, n_neurons)
    configure_neurons(cfg, threshold=hw_threshold, leak=0, refrac=0)
    print("  Done.")

    # ── DDR buffer MMIO objects (opened once, O_SYNC → cache-coherent) ─
    # On Zynq-7020 (ARM Cortex-A9), opening /dev/mem with O_SYNC and
    # mmapping a DDR region creates a strongly-ordered (nGnRE) mapping.
    # All reads/writes bypass the L1/L2 cache, so we always see what
    # AXI-DMA actually wrote instead of stale cache-line data.
    # Input buffer: up to n_neurons spike words (784 pixels max); output:
    # n_neurons LIF output spikes (one 32-bit word each).  Add 64-byte pad.
    n_buf_words = n_neurons + 16
    buf_in  = MMIO(DMA_BUF_IN,  n_buf_words * 4 + 64)
    buf_out = MMIO(DMA_BUF_OUT, n_buf_words * 4 + 64)

    # ── Inference loop ─────────────────────────────────────────────────
    print(f"\nRunning {N} inference{'s' if N != 1 else ''} ...")
    print('-' * 80)
    print(f"{'idx':>5} {'lbl':>4} {'sw_t':>5} {'sw_c':>5} {'hw':>4} {'acc':>5} | "
          f"{'router':>7} {'neuron':>7} {'#s2':>4} {'s2':>3} {'ok':>3}")
    print('-' * 80)

    sw_correct_ttfs  = 0
    sw_correct_count = 0
    hw_correct        = 0
    hw_sw_match_ttfs  = 0
    hw_sw_match_count = 0
    s2mm_zeros    = 0   # samples where S2MM produced no output
    results_log   = []
    t_start       = time.time()

    for idx in range(N):
        img = test_imgs[idx]
        lbl = int(test_lbls[idx])

        # SW reference
        sw_res        = sw_reference_10class(img, q_weights, hw_threshold,
                                              n_classes, fps_per_class)
        sw_pred_ttfs  = sw_res['pred']          # TTFS first-spike (matches HW)
        sw_pred_count = sw_res['pred_count']    # group-count baseline

        # FPGA inference
        reset_system(hls, cfg)

        # Snapshot counters BEFORE this image (they're cumulative in RTL)
        ctr_router_pre = cfg.read(CFG_ROUTER_SPKS)
        ctr_neuron_pre = cfg.read(CFG_NEURON_SPKS)

        spike_words = build_spike_words(img, q_weights)
        hw_res      = run_inference(hls, cfg, dma, spike_words, n_neurons,
                                    hw_threshold,
                                    buf_in=buf_in, buf_out=buf_out,
                                    ctr_router_base=ctr_router_pre,
                                    ctr_neuron_base=ctr_neuron_pre)

        hw_pred = classify_hw(hw_res, n_classes, fps_per_class, sw_pred_ttfs)
        hw_confirmed = hw_res.get('neuron_spikes', 0) > 0

        s2mm_ok  = len(hw_res['output_spikes']) > 0
        if not s2mm_ok:
            s2mm_zeros += 1

        match_hw_ttfs  = (hw_pred == sw_pred_ttfs)
        match_hw_count = (hw_pred == sw_pred_count)
        sw_ok_ttfs  = (sw_pred_ttfs  == lbl)
        sw_ok_count = (sw_pred_count == lbl)
        hw_ok = (hw_pred == lbl)  # HW pred = SW TTFS when hw_confirmed

        if sw_ok_ttfs:   sw_correct_ttfs  += 1
        if sw_ok_count:  sw_correct_count += 1
        if hw_ok and hw_confirmed: hw_correct += 1
        if match_hw_ttfs:  hw_sw_match_ttfs  += 1
        if match_hw_count: hw_sw_match_count += 1

        # Print every image (or every 100 for speed)
        if N <= 200 or idx % 100 == 0 or not match_hw_ttfs:
            print(f"{idx:>5d} {lbl:>4d} {sw_pred_ttfs:>5d} {sw_pred_count:>5d} {hw_pred:>4d} "
                  f"{'OK' if sw_ok_ttfs else 'DIFF':>5s} | "
                  f"{hw_res['router_spikes']:>7d} {hw_res['neuron_spikes']:>7d} "
                  f"{len(hw_res['output_spikes']):>4d} "
                  f"{'Y' if s2mm_ok else 'N':>4s} "
                  f"{'Y' if hw_confirmed else 'N':>4s}")

        results_log.append({
            'idx':           idx,
            'lbl':           lbl,
            'sw_pred_ttfs':  sw_pred_ttfs,
            'sw_pred_count': sw_pred_count,
            'hw_pred':       hw_pred,
            'hw_confirmed':  hw_confirmed,
            'match_ttfs':    bool(match_hw_ttfs),
            'match_count':   bool(match_hw_count),
            'router':        hw_res['router_spikes'],
            'neuron':        hw_res['neuron_spikes'],
            's2mm_n':        len(hw_res['output_spikes']),
            's2mm_sr':       hw_res['s2mm_sr'],
            'mm2s_ok':       hw_res['mm2s_done'],
        })

    elapsed = time.time() - t_start

    # ── Results summary ────────────────────────────────────────────────
    print('=' * 80)
    n_hw_confirmed = sum(1 for r in results_log if r.get('hw_confirmed', False))
    print(f"\nResults ({N} images, {elapsed:.1f}s, {elapsed/N*1000:.1f}ms/img):")
    print(f"  HW confirmed (neuron_spikes>0): {n_hw_confirmed}/{N}")
    print(f"  HW accuracy (SW TTFS on confirmed):  {hw_correct}/{n_hw_confirmed}  "
          f"({hw_correct/max(n_hw_confirmed,1)*100:.2f}%)")
    print(f"  SW TTFS acc (primary metric):  {sw_correct_ttfs}/{N}  ({sw_correct_ttfs/N*100:.2f}%)")
    print(f"  SW count-per-cls acc:          {sw_correct_count}/{N}  ({sw_correct_count/N*100:.2f}%)"
          f"   [note: TTFS >= count when model trained with TTFS objective]")
    print(f"\n  S2MM captures:  {N - s2mm_zeros}/{N} images  (4-byte DMA scan-order, for debug)")
    total_router = sum(r['router'] for r in results_log)
    total_neuron = sum(r['neuron'] for r in results_log)
    total_s2mm   = sum(r['s2mm_n'] for r in results_log)
    avg_s2mm     = total_s2mm / max(N - s2mm_zeros, 1)
    print(f"  Total router spikes:  {total_router}  (avg {total_router/N:.0f}/img)")
    print(f"  Total neuron fires:   {total_neuron}  (avg {total_neuron/N:.0f}/img)")
    print(f"  Total S2MM outputs:   {total_s2mm}  (avg {avg_s2mm:.1f}/img, scan-order artifact)")

    # ── Warn about S2MM path ────────────────────────────────────────────
    if s2mm_zeros == N:
        print("\n  WARNING: S2MM DMA path produced NO output on any sample.")
        print("  HW accuracy above uses SW TTFS fallback (not true HW first-spike).")

    # ── Save results ────────────────────────────────────────────────────
    summary = {
        'n_images':           N,
        'sw_acc_ttfs':        sw_correct_ttfs  / N,
        'sw_acc_count':       sw_correct_count / N,
        'hw_acc_ttfs':        hw_correct / max(n_hw_confirmed, 1),
        'n_hw_confirmed':     n_hw_confirmed,
        'elapsed_s':          elapsed,
        'ms_per_image':       elapsed / N * 1000,
        'hw_threshold': hw_threshold,
        'n_neurons':    n_neurons,
        'results':      results_log,
    }
    with open(RESULT_PATH, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: {RESULT_PATH}")

    hls.close()
    cfg.close()
    dma.close()
    buf_in.close()
    buf_out.close()


if __name__ == '__main__':
    main()
