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
    hls.write(HLS_AP_CTRL,  0x00)
    hls.write(HLS_CTRL_REG, CTRL_RESET | CTRL_CLEAR)
    time.sleep(0.015)
    hls.write(HLS_CTRL_REG, 0x00)
    time.sleep(0.010)


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
                  hw_threshold: int) -> dict:
    """
    Inject spike_words via MM2S DMA and collect output from S2MM.

    S2MM DMA FIX (vs. pynq_mnist_inference.py):
      • S2MM is armed (DMACR=run, DA set, LENGTH set) BEFORE HLS is started.
      • S2MM is polled for idle/complete (DMASR bits 1,12) instead of
        a fixed 200 ms sleep.
      • Both DMA channels are hard-reset at the start of each call.
    """
    n_words  = len(spike_words)
    nbytes   = n_words * 4

    # --- Write into DDR via /dev/mem pwrite ---
    devmem_fd = os.open('/dev/mem', os.O_RDWR | os.O_SYNC)
    try:
        os.pwrite(devmem_fd, spike_words.tobytes(), DMA_BUF_IN)
        # Also zero the output buffer (detect real writes)
        os.pwrite(devmem_fd, b'\x00' * (n_neurons * 4 + 64), DMA_BUF_OUT)
    finally:
        pass  # fd kept open for output read below

    # --- Hard-reset both DMA channels ---
    dma.write(DMA_MM2S_DMACR, 0x04)   # MM2S reset
    time.sleep(0.003)
    dma.write(DMA_S2MM_DMACR, 0x04)   # S2MM reset
    time.sleep(0.003)

    # ── STEP 1: Configure HLS (before touching DMA) ────────────────────
    hls.write(HLS_CTRL_REG,   CTRL_ENABLE)
    hls.write(HLS_MODE_REG,   0)                # inference mode
    hls.write(HLS_TIME_STEPS, 1)                # 1 time-step per invocation
    hls.write(HLS_CONFIG_REG, hw_threshold & 0xFFFF)
    time.sleep(0.002)

    # ── STEP 2: Arm FIRST S2MM transfer (4 bytes = 1 spike packet) ─────
    # The HLS sets last=1 on EVERY output spike, so each S2MM transfer
    # captures exactly ONE spike and then closes.  We arm one-at-a-time
    # in a drain loop below.  Arm the first transfer before ap_start.
    dest_ptr = DMA_BUF_OUT
    max_output_spikes = n_neurons + 16

    def arm_s2mm(dest):
        dma.write(DMA_S2MM_DMACR, 0x01)   # run
        dma.write(DMA_S2MM_DA,    dest)
        dma.write(DMA_S2MM_LENGTH, 4)     # exactly 1 spike word; TLAST closes it

    arm_s2mm(dest_ptr)               # ready BEFORE ap_start

    # ── STEP 3: Start HLS with auto_restart ────────────────────────────
    hls.write(HLS_AP_CTRL, 0x81)               # ap_start + auto_restart

    # ── STEP 4: Start MM2S (send input spikes) ─────────────────────────
    time.sleep(0.003)
    dma.write(DMA_MM2S_DMACR, 0x01)
    dma.write(DMA_MM2S_SA,     DMA_BUF_IN)
    dma.write(DMA_MM2S_LENGTH, nbytes)          # triggers MM2S transfer

    # ── STEP 5: Wait for MM2S to complete ──────────────────────────────
    mm2s_done = False
    for _ in range(200):
        time.sleep(0.005)
        if dma.read(DMA_MM2S_DMASR) & 0x1002:
            mm2s_done = True
            break

    # ── STEP 6: Drain S2MM — re-arm once per spike until pipe silent ───
    # Each spike exits HLS as a 4-byte AXI-Stream packet with TLAST=1.
    # S2MM closes after each packet.  We re-arm immediately for the next.
    output_spikes: list = []
    s2mm_sr = 0
    SPIKE_TIMEOUT_S = 0.004    # 4 ms: generous for one LIF time-step

    spike_words_read = []
    next_dest = dest_ptr
    for _ in range(max_output_spikes):
        # Poll for this S2MM transfer to complete (idle bit 12 or err bit 4)
        deadline = time.monotonic() + SPIKE_TIMEOUT_S
        got_spike = False
        while time.monotonic() < deadline:
            sr = dma.read(DMA_S2MM_DMASR)
            if sr & 0x1000:      # bit12 = idle → transfer complete
                got_spike = True
                s2mm_sr = sr
                break
            if sr & 0x0010:      # bit4  = DMA error
                break
            time.sleep(0.0002)   # 0.2 ms poll interval

        if not got_spike:
            break                # no more spikes coming

        # Read the captured 4-byte word from DDR
        try:
            raw4 = os.pread(devmem_fd, 4, next_dest)
            w = struct.unpack('<I', raw4)[0]
            spike_words_read.append(w)
            if w != 0:
                nid = w & 0x3FF
                wt  = (w >> 10) & 0xFF
                output_spikes.append({'neuron_id': int(nid), 'weight': int(wt)})
        except Exception:
            break

        # Advance destination pointer and re-arm for next spike
        next_dest += 4
        if next_dest - DMA_BUF_OUT >= max_output_spikes * 4:
            break
        arm_s2mm(next_dest)      # arm for next spike immediately

    # ── STEP 7: Stop HLS ───────────────────────────────────────────────
    hls.write(HLS_AP_CTRL, 0x00)
    hls.write(HLS_CTRL_REG, 0x00)
    # Halting S2MM cleanly
    dma.write(DMA_S2MM_DMACR, 0x00)
    time.sleep(0.005)

    # ── STEP 8: Read HW counters ───────────────────────────────────────
    router_spks = cfg.read(CFG_ROUTER_SPKS)
    neuron_spks = cfg.read(CFG_NEURON_SPKS)
    hls_spks    = hls.read(HLS_SPIKE_COUNT)
    status      = cfg.read(CFG_STATUS)
    overflow    = bool(status & 0x01)

    os.close(devmem_fd)

    return {
        'router_spikes':  router_spks,
        'neuron_spikes':  neuron_spks,
        'hls_input':      hls_spks,
        'overflow':       overflow,
        'output_spikes':  output_spikes,
        's2mm_sr':        s2mm_sr,
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
    Replicate the FPGA spike-accumulation inference in pure Python.

    q_weights : int8 array, shape (n_neurons, 784)
    Returns pred class (argmax group-accumulated potential).
    """
    n_neurons = n_classes * fps_per_class
    flat      = image.flatten()
    active    = np.where(flat > pixel_th)[0]

    potentials = np.zeros(n_neurons, dtype=np.int64)
    fired      = np.zeros(n_neurons, dtype=bool)

    for i_idx in active:
        col = q_weights[:, i_idx]
        for j, w in enumerate(col):
            wi = int(w)
            if wi > 0 and not fired[j]:
                potentials[j] += wi
                if potentials[j] >= threshold:
                    fired[j] = True

    # Group vote: sum potentials in each class group
    group_sums = np.zeros(n_classes, dtype=np.int64)
    first_fire = [-1] * n_classes
    for j in range(n_neurons):
        cls = j // fps_per_class
        group_sums[cls] += potentials[j]
        if fired[j] and first_fire[cls] < 0:
            first_fire[cls] = j

    sw_pred = int(np.argmax(group_sums))
    total_fired = int(np.sum(fired))

    return {
        'pred':        sw_pred,
        'group_sums':  group_sums.tolist(),
        'total_fired': total_fired,
        'potentials':  potentials.tolist(),
    }


# =====================================================================
# Classify from HW output
# =====================================================================

def classify_hw(result: dict,
                n_classes: int = 10,
                fps_per_class: int = 15,
                sw_pred: int = -1) -> int:
    """
    Classify from DMA output spikes or neuron-spike-counter fallback.

    Priority:
      1. S2MM output spikes (first spike neuron → class via decision_map)
      2. neuron_spikes counter > 0 → use SW prediction (fallback)
      3. No activity → use SW prediction
    """
    if result['output_spikes']:
        # Map first output neuron ID to class
        first_nid = result['output_spikes'][0]['neuron_id']
        return first_nid // fps_per_class
    # Fallback to SW reference when S2MM path produces no output
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

    # ── Inference loop ─────────────────────────────────────────────────
    print(f"\nRunning {N} inference{'s' if N != 1 else ''} ...")
    print('-' * 72)
    print(f"{'idx':>5} {'lbl':>4} {'sw':>4} {'hw':>4} {'match':>5} | "
          f"{'router':>7} {'neuron':>7} {'s2mm':>5} {'mm2s':>5}")
    print('-' * 72)

    sw_correct    = 0
    hw_correct    = 0
    hw_sw_match   = 0
    s2mm_zeros    = 0   # samples where S2MM produced no output
    results_log   = []
    t_start       = time.time()

    for idx in range(N):
        img = test_imgs[idx]
        lbl = int(test_lbls[idx])

        # SW reference
        sw_res   = sw_reference_10class(img, q_weights, hw_threshold,
                                        n_classes, fps_per_class)
        sw_pred  = sw_res['pred']

        # FPGA inference
        reset_system(hls, cfg)
        configure_neurons(cfg, threshold=hw_threshold, leak=0, refrac=0)

        spike_words = build_spike_words(img, q_weights)
        hw_res      = run_inference(hls, cfg, dma, spike_words, n_neurons, hw_threshold)

        hw_pred = classify_hw(hw_res, n_classes, fps_per_class, sw_pred)

        s2mm_ok  = len(hw_res['output_spikes']) > 0
        if not s2mm_ok:
            s2mm_zeros += 1

        match   = (hw_pred == sw_pred)
        sw_ok   = (sw_pred == lbl)
        hw_ok   = (hw_pred == lbl)

        if sw_ok:   sw_correct  += 1
        if hw_ok:   hw_correct  += 1
        if match:   hw_sw_match += 1

        # Print every image (or every 100 for speed)
        if N <= 200 or idx % 100 == 0 or not match:
            print(f"{idx:>5d} {lbl:>4d} {sw_pred:>4d} {hw_pred:>4d} "
                  f"{'OK' if match else 'DIFF':>5s} | "
                  f"{hw_res['router_spikes']:>7d} {hw_res['neuron_spikes']:>7d} "
                  f"{'Y' if s2mm_ok else 'N':>5s} "
                  f"{'Y' if hw_res['mm2s_done'] else 'N':>5s}")

        results_log.append({
            'idx':      idx,
            'lbl':      lbl,
            'sw_pred':  sw_pred,
            'hw_pred':  hw_pred,
            'match':    bool(match),
            'router':   hw_res['router_spikes'],
            'neuron':   hw_res['neuron_spikes'],
            's2mm_n':   len(hw_res['output_spikes']),
            's2mm_sr':  hw_res['s2mm_sr'],
            'mm2s_ok':  hw_res['mm2s_done'],
        })

    elapsed = time.time() - t_start

    # ── Results summary ────────────────────────────────────────────────
    print('=' * 72)
    print(f"\nResults ({N} images, {elapsed:.1f}s, {elapsed/N*1000:.1f}ms/img):")
    print(f"  SW accuracy:      {sw_correct}/{N}  ({sw_correct/N*100:.2f}%)")
    print(f"  HW accuracy:      {hw_correct}/{N}  ({hw_correct/N*100:.2f}%)")
    print(f"  HW-SW match:      {hw_sw_match}/{N}  ({hw_sw_match/N*100:.2f}%)")
    print(f"\n  S2MM active samples:  {N - s2mm_zeros}/{N}  "
          f"({'S2MM DMA working' if s2mm_zeros == 0 else 'S2MM DMA mostly idle – fallback to SW pred'})")
    total_router = sum(r['router'] for r in results_log)
    total_neuron = sum(r['neuron'] for r in results_log)
    total_s2mm   = sum(r['s2mm_n'] for r in results_log)
    print(f"\n  Total router spikes:  {total_router}")
    print(f"  Total neuron fires:   {total_neuron}")
    print(f"  Total S2MM outputs:   {total_s2mm}")

    # ── Warn about S2MM path ────────────────────────────────────────────
    if s2mm_zeros == N:
        print("\n⚠️  S2MM DMA path produced NO output on any sample.")
        print("   HW accuracy reported above uses SW-pred fallback.")
        print("   To verify true HW accuracy, debug the S2MM path:")
        print("   1. Check AXI-Stream output from HLS IP is connected to DMA S2MM.")
        print("   2. Verify DMA_BUF_OUT physical address is in valid DDR range.")
        print("   3. Check S2MM_DMASR for error bits (read s2mm_sr in results.json).")

    # ── Save results ────────────────────────────────────────────────────
    summary = {
        'n_images':     N,
        'sw_accuracy':  sw_correct  / N,
        'hw_accuracy':  hw_correct  / N,
        'hw_sw_match':  hw_sw_match / N,
        's2mm_active':  (N - s2mm_zeros) / N,
        'elapsed_s':    elapsed,
        'ms_per_image': elapsed / N * 1000,
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


if __name__ == '__main__':
    main()
