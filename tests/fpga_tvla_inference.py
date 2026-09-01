#!/usr/bin/env python3
"""
TVLA Data Logger for 10-Class MNIST Inference on PYNQ-Z2
=========================================================
Modified to capture full spiking activity across 10 images
for side-channel Test Vector Leakage Assessment (TVLA).
"""

import argparse
import json
import mmap
import os
import re
import struct
import sys
import time

import numpy as np

# =====================================================================
# Register Map
# =====================================================================
HLS_BASE            = 0x43C00000
CFG_BASE            = 0x43C10000
DMA_BASE            = 0x41E00000

HLS_AP_CTRL         = 0x00
HLS_CTRL_REG        = 0x10   
HLS_CONFIG_REG      = 0x18   
HLS_MODE_REG        = 0x20   
HLS_TIME_STEPS      = 0x28
HLS_STATUS_REG      = 0x58
HLS_SPIKE_COUNT     = 0x68
HLS_VERSION_REG     = 0x88

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
CFG_SERVICE_CYCLES  = 0x2C   

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
CTRL_FIRST_SPIKE_ONLY = 0x80

DMA_BUF_IN          = 0x1F000000   
DMA_BUF_OUT         = 0x1F100000   

MAX_FANOUT          = 32
ROUTER_NEURON_ID_W  = 10           
SOURCE_OFFSET       = 256          
HLS_SPIKE_PKT_ID_W  = 13

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
        self._mm.seek(self._off + offset)
        self._mm.write(data)

    def read_bytes(self, offset: int, length: int) -> bytes:
        self._mm.seek(self._off + offset)
        return self._mm.read(length)

    def close(self) -> None:
        self._mm.close()
        os.close(self._fd)

def encode_conn(src: int, fanout: int, dest: int, weight: int, exc: bool = True) -> tuple:
    flat = src * MAX_FANOUT + fanout
    addr = (0x00 << 24) | (flat & 0x00_FFFF)
    w7 = ((weight & 0xFE) >> 1) & 0x7F  
    data = 0
    data |= (dest & 0x7FF)              
    data |= (w7 << 19)                  
    if exc:
        data |= (1 << 26)               
    data |= (1 << 27)                   
    data |= (1 << 28)                   
    return addr, data

def encode_conn_count(neuron: int, count: int) -> tuple:
    addr = (0x01 << 24) | (neuron & 0x00_FF_FF)
    return addr, count & 0xFF

def reset_system(hls: MMIO, cfg: MMIO) -> None:
    def run_hls_oneshot(ctrl_word: int) -> None:
        hls.write(HLS_AP_CTRL, 0x00)
        hls.write(HLS_MODE_REG, 0)
        hls.write(HLS_TIME_STEPS, 1)
        hls.write(HLS_CTRL_REG, ctrl_word)
        hls.write(HLS_AP_CTRL, 0x01)
        deadline = time.monotonic() + 0.05
        while time.monotonic() < deadline:
            if hls.read(HLS_AP_CTRL) & 0x06:
                break
        hls.write(HLS_AP_CTRL, 0x00)

    run_hls_oneshot(CTRL_CLEAR)
    run_hls_oneshot(0x00)
    hls.write(HLS_CTRL_REG, 0x00)

def program_router_for_inference(cfg: MMIO, n_neurons: int, source_offset: int) -> None:
    cfg.write(CFG_CONFIG_CTRL, 0)   
    for j in range(n_neurons):
        cca, ccd = encode_conn_count(j, 0)
        cfg.write(CFG_CONFIG_ADDR, cca)
        cfg.write(CFG_CONFIG_WDATA, ccd)
    for j in range(n_neurons):
        src = source_offset + j
        ca, cd = encode_conn(src, 0, j, 127, exc=True)
        cfg.write(CFG_CONFIG_ADDR, ca)
        cfg.write(CFG_CONFIG_WDATA, cd)
        cca, ccd = encode_conn_count(src, 1)
        cfg.write(CFG_CONFIG_ADDR, cca)
        cfg.write(CFG_CONFIG_WDATA, ccd)

def compute_positive_potential(image: np.ndarray, q_weights: np.ndarray, pixel_th: float = 0.3) -> np.ndarray:
    active_mask = image.reshape(-1) > pixel_th
    if not np.any(active_mask):
        return np.zeros(q_weights.shape[0], dtype=np.int32)
    active_cols = q_weights[:, active_mask]
    return np.maximum(active_cols, 0).sum(axis=1, dtype=np.int32)

def ttfs_order_from_potential(potential: np.ndarray) -> np.ndarray:
    return np.argsort(-potential, kind='stable')

def build_spike_words(image: np.ndarray, q_weights: np.ndarray, potential: np.ndarray) -> np.ndarray:
    n_out  = q_weights.shape[0]
    hls_spike_id_mask = (1 << HLS_SPIKE_PKT_ID_W) - 1
    hls_spike_wgt_shift = HLS_SPIKE_PKT_ID_W
    order = ttfs_order_from_potential(potential)
    pos_order = order[potential[order] > 0]
    if pos_order.size == 0:
        return np.zeros(1, dtype=np.uint32)
    src_ids = (SOURCE_OFFSET + pos_order) & hls_spike_id_mask
    return src_ids.astype(np.uint32) | np.uint32(0x7F << hls_spike_wgt_shift)

def run_inference(hls: MMIO, cfg: MMIO, dma: MMIO, spike_words: np.ndarray, 
                  buf_in: MMIO, buf_out: MMIO, hw_threshold: int) -> dict:
    
    n_words = len(spike_words)
    nbytes = n_words * 4
    hls_spike_id_mask = (1 << HLS_SPIKE_PKT_ID_W) - 1
    hls_spike_wgt_shift = HLS_SPIKE_PKT_ID_W
    
    # TVLA Mode forces capture of all spikes for up to 10,000 cycles
    max_output_spikes = 10000 
    
    buf_in.write_bytes(0, spike_words.tobytes())
    buf_out.write_bytes(0, b'\x00' * (max_output_spikes * 4 + 64))

    dma.write(DMA_MM2S_DMACR, 0x04)   
    dma.write(DMA_S2MM_DMACR, 0x04)   

    # Disable First-Spike-Only truncation
    hls.write(HLS_CTRL_REG, CTRL_ENABLE | 0)
    hls.write(HLS_MODE_REG, 0)
    hls.write(HLS_TIME_STEPS, 1)
    hls.write(HLS_CONFIG_REG, hw_threshold & 0xFFFF)

    dest_ptr = DMA_BUF_OUT

    def arm_s2mm(dest):
        dma.write(DMA_S2MM_DMASR, 0x1000)   
        dma.write(DMA_S2MM_DMACR, 0x01)     
        dma.write(DMA_S2MM_DA,    dest)
        dma.write(DMA_S2MM_LENGTH, 4)       

    arm_s2mm(dest_ptr)

    dma.write(DMA_MM2S_DMACR, 0x01)
    dma.write(DMA_MM2S_SA,     DMA_BUF_IN)
    dma.write(DMA_MM2S_LENGTH, nbytes)

    hls.write(HLS_AP_CTRL, 0x81)

    output_spikes = []
    next_dest = dest_ptr
    spike_n = 0
    
    while spike_n < max_output_spikes:
        deadline = time.monotonic() + 0.05
        got_completion = False

        while time.monotonic() < deadline:
            sr = dma.read(DMA_S2MM_DMASR)
            if sr & 0x1000:          
                got_completion = True
                break
            if sr & 0x0050:          
                break                

        if not got_completion:
            break                    

        raw4 = buf_out.read_bytes(next_dest - DMA_BUF_OUT, 4)
        w    = struct.unpack('<I', raw4)[0]

        if w != 0:
            nid = w & hls_spike_id_mask
            wt  = (w >> hls_spike_wgt_shift) & 0xFF
            # EXtract the 14-bit clock cycle timestamp 
            ts  = (w >> 18) & 0x3FFF  
            output_spikes.append({'neuron_id': int(nid), 'weight': int(wt), 'timestamp': int(ts)})
            
        spike_n += 1
        next_dest += 4
        if next_dest - DMA_BUF_OUT >= max_output_spikes * 4:
            break
        arm_s2mm(next_dest)   

    hls.write(HLS_AP_CTRL, 0x00)
    hls.write(HLS_CTRL_REG, 0x00)
    dma.write(DMA_S2MM_DMACR, 0x00)

    return {'output_spikes':  output_spikes}

def main():
    print("=========================================================")
    print("TVLA Data Logger for FPGA (Full Temporal Capture)")
    print("=========================================================")

    DEPLOY_PATH  = '/home/xilinx/snn/mnist_10class_deployment.npz'
    TVLA_OUTPUT  = '/home/xilinx/snn/physical_output_spikes.txt'

    data          = np.load(DEPLOY_PATH, allow_pickle=True)
    q_weights     = data['q_weights']          
    test_imgs     = data['test_imgs']          
    hw_threshold  = int(data['hw_threshold'])
    n_classes     = int(data.get('n_classes',     10))
    fps_per_class = int(data.get('fps_per_class', 15))
    n_neurons     = n_classes * fps_per_class

    N = 10 # Force 10 images for TVLA logging
    
    hls = MMIO(HLS_BASE, 0x100)
    cfg = MMIO(CFG_BASE, 0x100)
    dma = MMIO(DMA_BASE, 0x100)

    reset_system(hls, cfg)
    program_router_for_inference(cfg, n_neurons, source_offset=SOURCE_OFFSET)
    
    cfg.write(CFG_THRESHOLD, hw_threshold & 0xFFFF)
    cfg.write(CFG_NEURON_PARAMS, 0)

    # Allocate a massive 10,000 word buffer for TVLA full capture
    n_buf_words = 10000 
    buf_in  = MMIO(DMA_BUF_IN,  n_buf_words * 4 + 64)
    buf_out = MMIO(DMA_BUF_OUT, n_buf_words * 4 + 64)

    print(f"\nRunning {N} inferences in Full-Capture TVLA Mode...")
    
    with open(TVLA_OUTPUT, "w") as tvla_file:
        tvla_file.write("Image_ID,Clock_Cycle,Neuron_ID\n")
        
        for idx in range(N):
            img = test_imgs[idx]
            potential = compute_positive_potential(img, q_weights)
            
            reset_system(hls, cfg)

            spike_words = build_spike_words(img, q_weights, potential)
            
            hw_res = run_inference(hls, cfg, dma, spike_words, buf_in, buf_out, hw_threshold)
            
            # Log exact timestamp and neuron to the text file
            for spk in hw_res['output_spikes']:
                tvla_file.write(f"{idx},{spk['timestamp']},{spk['neuron_id']}\n")
                
            print(f"  Image {idx} complete. Captured {len(hw_res['output_spikes'])} output spikes.")

    print(f"\nTVLA temporal logging complete. Saved to: {TVLA_OUTPUT}")

    hls.close()
    cfg.close()
    dma.close()
    buf_in.close()
    buf_out.close()

if __name__ == '__main__':
    main()