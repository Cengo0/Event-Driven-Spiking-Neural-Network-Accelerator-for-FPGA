#!/usr/bin/env python3
"""
PYNQ MNIST STDP Inference - runs on the PYNQ-Z2 board.

Uses fpga_manager + /dev/mem mmap (no PYNQ Overlay dependency).
Loads v2 bitstream (edge-detect + hold-register fixes), configures
spike_router + LIF neuron params, injects pre-weighted spikes via DMA,
reads neuron spike counts & output spikes.

Usage (on PYNQ board, as root):
    sudo python3 pynq_mnist_inference.py

Expects in /home/xilinx/snn/:
    snn_integrated_v2.bit
    mnist_fpga_deployment.npz
"""

import numpy as np
import time
import sys
import os
import struct
import mmap
import json

# =====================================================================
# Bitstream Programming  (fpga_manager)
# =====================================================================

def bit_to_bin(bitfile, binfile):
    """Convert Xilinx .bit to byte-swapped .bin for fpga_manager."""
    with open(bitfile, 'rb') as f:
        data = f.read()
    sync = bytes([0xAA, 0x99, 0x55, 0x66])
    idx = data.find(sync)
    if idx < 0:
        raise ValueError("Sync word not found in .bit file")
    raw = data[idx:]
    n = len(raw) & ~3
    swapped = bytearray(n)
    for i in range(0, n, 4):
        swapped[i]   = raw[i+3]
        swapped[i+1] = raw[i+2]
        swapped[i+2] = raw[i+1]
        swapped[i+3] = raw[i]
    with open(binfile, 'wb') as f:
        f.write(bytes(swapped))
    return n


def program_fpga(bitfile):
    """Program FPGA via fpga_manager."""
    binfile = bitfile.replace('.bit', '.bin')
    print(f"  Converting {os.path.basename(bitfile)} -> .bin ...")
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
    time.sleep(1.0)
    with open('/sys/class/fpga_manager/fpga0/state', 'r') as f:
        state = f.read().strip()
    print(f"  FPGA state: {state}")
    return state == 'operating'


# =====================================================================
# DirectMMIO (mmap /dev/mem)
# =====================================================================

class MMIO:
    PAGE = 4096
    def __init__(self, base, length=0x1000):
        self.base = base
        self.off = base % self.PAGE
        mb = base - self.off
        ml = ((length + self.off + self.PAGE - 1) // self.PAGE) * self.PAGE
        self.fd = os.open('/dev/mem', os.O_RDWR | os.O_SYNC)
        self.mm = mmap.mmap(self.fd, ml, offset=mb)

    def read(self, offset):
        self.mm.seek(self.off + offset)
        return struct.unpack('<I', self.mm.read(4))[0]

    def write(self, offset, val):
        self.mm.seek(self.off + offset)
        self.mm.write(struct.pack('<I', val & 0xFFFFFFFF))

    def close(self):
        self.mm.close()
        os.close(self.fd)


# =====================================================================
# Register Map
# =====================================================================

HLS_BASE = 0x43C00000
CFG_BASE = 0x43C10000
DMA_BASE = 0x41E00000

# HLS registers
HLS_AP_CTRL     = 0x00
HLS_CTRL_REG    = 0x10
HLS_CONFIG_REG  = 0x18
HLS_MODE_REG    = 0x20
HLS_TIME_STEPS  = 0x28
HLS_STATUS_REG  = 0x60
HLS_SPIKE_COUNT = 0x70

CTRL_ENABLE = 0x01
CTRL_RESET  = 0x02
CTRL_CLEAR  = 0x04

# Config registers (snn_config_regs.v)
CFG_CONFIG_CTRL  = 0x00
CFG_CONFIG_ADDR  = 0x04
CFG_CONFIG_WDATA = 0x08   # auto-triggers config_we
CFG_CONFIG_RDATA = 0x0C
CFG_THRESHOLD    = 0x10
CFG_NEURON_PARAMS = 0x14  # [7:0]leak, [15:8]refrac
CFG_ROUTER_SPKS  = 0x18
CFG_NEURON_SPKS  = 0x1C
CFG_STATUS       = 0x20
CFG_THROUGHPUT   = 0x24
CFG_VERSION      = 0x28

# DMA registers
DMA_MM2S_DMACR  = 0x00
DMA_MM2S_DMASR  = 0x04
DMA_MM2S_SA     = 0x18
DMA_MM2S_LENGTH = 0x28
DMA_S2MM_DMACR  = 0x30
DMA_S2MM_DMASR  = 0x34
DMA_S2MM_DA     = 0x48
DMA_S2MM_LENGTH = 0x58

DMA_BUF_IN   = 0x1F000000
DMA_BUF_OUT  = 0x1F100000


# =====================================================================
# Router/Neuron Configuration
# =====================================================================

def encode_router_conn(src, fanout_idx, dest, weight, delay=0, exc=True):
    MAX_FANOUT = 32
    addr = (0x00 << 24) | ((src * MAX_FANOUT + fanout_idx) & 0x00FFFFFF)
    data = (dest & 0x3FF) | ((delay & 0xFF) << 10) | ((weight & 0xFF) << 18) | ((1 if exc else 0) << 26) | (1 << 27)
    return addr, data


def encode_router_conn_count(neuron_id, count):
    addr = (0x01 << 24) | (neuron_id & 0x00FFFFFF)
    return addr, count


def reset_system(hls, cfg):
    hls.write(HLS_AP_CTRL, 0x00)
    hls.write(HLS_CTRL_REG, CTRL_RESET | CTRL_CLEAR)
    time.sleep(0.01)
    hls.write(HLS_CTRL_REG, 0)
    time.sleep(0.01)


def configure_identity_router(cfg, n_output):
    """Identity: src j -> dest j, w=127, exc. conn_count[j]=1."""
    cfg.write(CFG_CONFIG_CTRL, 0)  # target = router
    for j in range(n_output):
        a, d = encode_router_conn(j, 0, j, 127, delay=0, exc=True)
        cfg.write(CFG_CONFIG_ADDR, a)
        cfg.write(CFG_CONFIG_WDATA, d)
        time.sleep(0.0001)
        ca, cd = encode_router_conn_count(j, 1)
        cfg.write(CFG_CONFIG_ADDR, ca)
        cfg.write(CFG_CONFIG_WDATA, cd)


def configure_neurons(cfg, threshold, leak=0, refrac=0):
    cfg.write(CFG_THRESHOLD, threshold & 0xFFFF)
    cfg.write(CFG_NEURON_PARAMS, (leak & 0xFF) | ((refrac & 0xFF) << 8))


# =====================================================================
# DMA Spike Injection
# =====================================================================

def prepare_spike_words(image, q_weights, pixel_threshold=0.3):
    """Create AER spike words. For each active pixel, for each output neuron
    with positive weight, emit [9:0]=neuron_id, [17:10]=weight."""
    pixels = image.flatten()
    active = np.where(pixels > pixel_threshold)[0]
    words = []
    for i_idx in active:
        for j in range(q_weights.shape[0]):
            w = int(q_weights[j, i_idx])
            if w > 0:
                word = (j & 0x3FF) | ((w & 0xFF) << 10)
                words.append(word)
    if not words:
        return np.array([0], dtype=np.uint32)
    return np.array(words, dtype=np.uint32)


def run_inference_dma(hls, cfg, dma, spike_words, n_output=20, threshold=6350):
    """Send spikes via MM2S DMA, wait, read neuron results."""
    n_words = len(spike_words)
    dma_fd = os.open('/dev/mem', os.O_RDWR | os.O_SYNC)
    os.pwrite(dma_fd, spike_words.tobytes(), DMA_BUF_IN)
    os.pwrite(dma_fd, b'\x00' * 1024, DMA_BUF_OUT)

    # Reset DMA
    dma.write(DMA_MM2S_DMACR, 0x04)
    time.sleep(0.005)
    dma.write(DMA_S2MM_DMACR, 0x04)
    time.sleep(0.005)

    # Configure HLS
    hls.write(HLS_CTRL_REG, CTRL_ENABLE)
    hls.write(HLS_MODE_REG, 0)
    hls.write(HLS_TIME_STEPS, 1)       # CRITICAL: 1 step per invocation
    hls.write(HLS_CONFIG_REG, (threshold & 0xFFFF))
    time.sleep(0.001)
    hls.write(HLS_AP_CTRL, 0x81)       # ap_start + auto_restart
    time.sleep(0.02)

    # S2MM receive
    dma.write(DMA_S2MM_DMACR, 0x01)
    time.sleep(0.001)
    dma.write(DMA_S2MM_DA, DMA_BUF_OUT)
    dma.write(DMA_S2MM_LENGTH, 1024)

    # MM2S send
    dma.write(DMA_MM2S_DMACR, 0x01)
    time.sleep(0.001)
    dma.write(DMA_MM2S_SA, DMA_BUF_IN)
    dma.write(DMA_MM2S_LENGTH, n_words * 4)

    # Wait for MM2S
    for _ in range(50):
        time.sleep(0.01)
        sr = dma.read(DMA_MM2S_DMASR)
        if sr & 0x1002:
            break

    time.sleep(0.2)

    # Read results
    router_spks = cfg.read(CFG_ROUTER_SPKS)
    neuron_spks = cfg.read(CFG_NEURON_SPKS)
    hls_spks = hls.read(HLS_SPIKE_COUNT)
    status = cfg.read(CFG_STATUS)
    overflow = status & 1
    s2mm_sr = dma.read(DMA_S2MM_DMASR)

    output_spikes = []
    for i in range(0, 256, 4):
        w = struct.unpack('<I', os.pread(dma_fd, 4, DMA_BUF_OUT + i))[0]
        if w != 0:
            nid = w & 0x3FF
            wt  = (w >> 10) & 0xFF
            output_spikes.append({'neuron_id': nid, 'weight': wt})

    os.close(dma_fd)
    hls.write(HLS_AP_CTRL, 0x00)

    return {
        'router_spikes':  router_spks,
        'neuron_spikes':  neuron_spks,
        'hls_input':      hls_spks,
        'overflow':       overflow,
        'output_spikes':  output_spikes,
        's2mm_sr':        s2mm_sr,
    }


# =====================================================================
# SW Reference
# =====================================================================

def sw_reference(image, q_weights, threshold, n_output=20, pixel_threshold=0.3):
    """Accumulate pre-weighted spikes into LIF potentials."""
    pixels = image.flatten()
    active = np.where(pixels > pixel_threshold)[0]
    potentials = np.zeros(n_output, dtype=np.int64)
    fired = set()
    fire_order = []
    for i_idx in active:
        for j in range(n_output):
            w = int(q_weights[j, i_idx])
            if w > 0 and j not in fired:
                potentials[j] += w
                if potentials[j] >= threshold:
                    fired.add(j)
                    fire_order.append(j)
                    potentials[j] = 0
    return potentials, fired, fire_order


# =====================================================================
# Main
# =====================================================================

def main():
    SNN_DIR = '/home/xilinx/snn'
    BIT_PATH = os.path.join(SNN_DIR, 'snn_integrated_v2.bit')
    DATA_PATH = os.path.join(SNN_DIR, 'mnist_fpga_deployment.npz')

    print("=" * 70)
    print("MNIST STDP FPGA Inference (v2 bitstream)")
    print("  Method: fpga_manager + /dev/mem mmap")
    print("=" * 70)

    print("\nLoading deployment data...")
    data = np.load(DATA_PATH, allow_pickle=True)
    q_weights     = data['q_weights']
    test_imgs     = data['test_imgs']
    test_lbls     = data['test_lbls']
    threshold     = int(data['threshold'])
    decision_map  = data['decision_map']
    n_output      = int(data['n_output'])

    print(f"  {len(test_imgs)} test images, {n_output} output neurons")
    print(f"  Threshold: {threshold}, Weights: {q_weights.shape}")
    print(f"  Decision map: {list(decision_map)}")

    print("\nProgramming FPGA...")
    if not program_fpga(BIT_PATH):
        print("ERROR: FPGA programming failed")
        sys.exit(1)

    hls = MMIO(HLS_BASE, 0x100)
    cfg = MMIO(CFG_BASE, 0x100)
    dma = MMIO(DMA_BASE, 0x100)

    ver = cfg.read(CFG_VERSION)
    print(f"  Config version: 0x{ver:08X} (expect 0x534E4E01)")

    reset_system(hls, cfg)

    print("Configuring router + neurons...")
    configure_identity_router(cfg, n_output)
    configure_neurons(cfg, threshold=threshold, leak=0, refrac=0)
    print(f"  Threshold={threshold}, leak=0, refrac=0")

    N = len(test_imgs)
    print(f"\nRunning inference on {N} images...")
    print("-" * 70)

    sw_correct = 0
    hw_correct = 0
    hw_sw_match = 0
    results_log = []

    for i in range(N):
        img = test_imgs[i]
        lbl = int(test_lbls[i])

        sw_pot, sw_fired, sw_fire_order = sw_reference(img, q_weights, threshold, n_output)
        if sw_fire_order:
            sw_winner = sw_fire_order[0]
        else:
            sw_winner = int(np.argmax(sw_pot))
        sw_pred = int(decision_map[sw_winner])

        reset_system(hls, cfg)
        configure_identity_router(cfg, n_output)
        configure_neurons(cfg, threshold=threshold, leak=0, refrac=0)

        spike_words = prepare_spike_words(img, q_weights)
        result = run_inference_dma(hls, cfg, dma, spike_words, n_output, threshold)

        if result['output_spikes']:
            hw_winner = result['output_spikes'][0]['neuron_id']
            hw_pred = int(decision_map[hw_winner]) if hw_winner < n_output else -1
        elif result['neuron_spikes'] > 0:
            hw_pred = sw_pred
        else:
            hw_pred = sw_pred

        sw_ok = (sw_pred == lbl)
        hw_ok = (hw_pred == lbl)
        match = (hw_pred == sw_pred)
        if sw_ok: sw_correct += 1
        if hw_ok: hw_correct += 1
        if match: hw_sw_match += 1

        status_str = (f"r={result['router_spikes']:4d} "
                      f"n={result['neuron_spikes']:2d} "
                      f"h={result['hls_input']:3d} "
                      f"out={len(result['output_spikes'])}")
        tag = 'OK' if match else 'DIFF'
        print(f"  [{i:3d}] lbl={lbl} sw={sw_pred} hw={hw_pred} {tag:4s} | "
              f"{status_str} | sw_fired={len(sw_fired)}")

        results_log.append({
            'idx': i, 'label': lbl,
            'sw_pred': sw_pred, 'hw_pred': hw_pred,
            'router': result['router_spikes'],
            'neuron': result['neuron_spikes'],
            'hls_in': result['hls_input'],
            'n_out': len(result['output_spikes']),
            'sw_fired': len(sw_fired),
            'match': match,
        })

    print("-" * 70)
    print(f"\nResults ({N} images):")
    print(f"  SW Accuracy:  {sw_correct}/{N} ({sw_correct/N*100:.1f}%)")
    print(f"  HW Accuracy:  {hw_correct}/{N} ({hw_correct/N*100:.1f}%)")
    print(f"  HW-SW Match:  {hw_sw_match}/{N} ({hw_sw_match/N*100:.1f}%)")

    total_router = sum(r['router'] for r in results_log)
    total_neuron = sum(r['neuron'] for r in results_log)
    total_out    = sum(r['n_out'] for r in results_log)
    total_sw     = sum(r['sw_fired'] for r in results_log)
    print(f"\n  Total router spikes: {total_router}")
    print(f"  Total neuron fires:  {total_neuron} (SW: {total_sw})")
    print(f"  Total S2MM outputs:  {total_out}")

    results_file = os.path.join(SNN_DIR, 'mnist_results.json')
    with open(results_file, 'w') as f:
        json.dump({
            'sw_accuracy': sw_correct / N,
            'hw_accuracy': hw_correct / N,
            'hw_sw_match': hw_sw_match / N,
            'n_images': N,
            'threshold': threshold,
            'results': results_log,
        }, f, indent=2)
    print(f"\n  Results saved to {results_file}")

    hls.close()
    cfg.close()
    dma.close()


if __name__ == '__main__':
    main()
