#!/usr/bin/env python3
"""
fpga_cnn3_inference.py
======================
Multi-Layer Convolutional SNN (CNN3) 100% On-FPGA Inference with Pin Y18 SCA Trigger.
Architecture: snn_core_group_top.v (v3) + HLS Streaming 2D Convolution Engine

Pipeline on Hardware:
  - Layer 1 (HLS 2D Conv Engine) : Conv2d(1->8, 3x3) -> LIF -> AvgPool2d(2x2) [On-Chip DSP & Line Buffers]
  - Layer 2 (RTL Core Groups 0..3): 784 LIF Neurons across 4 Core Groups (196 each) [On-Chip Int8]
  - Layer 3 (RTL Core Group 4)   : 10 Class LIF Neurons in Group 4 [On-Chip Int8]
  - Inter-Group Routing Table    : Hardware BRAM (12,544 rows mapping Layer 2 -> Layer 3)
  - Dedicated Hardware Trigger   : Pin Y18 (snn_busy) pulses HIGH during full on-chip inference

Usage:
  python3 tests/fpga_cnn3_inference.py --bitstream outputs_v3/snn_core_group_v3.bit \
                                       --data data/cache/mnist_cnn3_deployment.npz
"""

import argparse
import time
import json
import os
import numpy as np
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# Hardware Parameters (matching snn_params.vh generated from snn_params.yaml)
# ─────────────────────────────────────────────────────────────────────────────
NUM_GROUPS         = 5
GROUP_SIZE_L2      = 196  # Groups 0..3: Layer 2 hidden LIF neurons (4 x 196 = 784)
GROUP_SIZE_L3      = 16   # Group 4: Layer 3 output class neurons (10 classes: 0..9)
OUTPUT_GROUP       = 4    # Output classification layer

LOCAL_ID_WIDTH     = 8    # 196 neurons -> 8 bits
GROUP_ID_WIDTH     = 3    # 5 groups -> 3 bits

# Register offsets (snn_config_regs.v)
CFG_CTRL           = 0x00
CFG_ADDR           = 0x04
CFG_WDATA          = 0x08
CFG_THRESHOLD      = 0x10
CFG_NEURON_PARAMS  = 0x14
CFG_ROUTER_SPKS    = 0x18
CFG_NEURON_SPKS    = 0x1C

# HLS Modes
MODE_INFERENCE     = 0x01
MODE_CNN_STREAM    = 0x03


def encode_ct_write(src_group: int, src_neuron: int, fanout_idx: int,
                    dst_group: int, dst_neuron: int, weight: int,
                    exc: bool) -> tuple:
    """
    Build (addr, data) for connectivity table write (14-bit compact addressing).
    ADDR:  [31:28]=0x0, [27:20]=fanout_idx(8b), [19:12]=src_neuron(8b), [3:0]=src_group(4b)
    WDATA: [31]=valid, [30:27]=dst_group(4b), [23:16]=dst_neuron(8b), [15:8]=weight(8b), [0]=exc
    """
    addr  = (0x0 << 28)
    addr |= ((fanout_idx & 0xFF) << 20)
    addr |= ((src_neuron & 0xFF) << 12)
    addr |= (src_group  & 0xF)

    data  = (1 << 31)                      # valid bit
    data |= ((dst_group  & 0xF)  << 27)    # dst_group
    data |= ((dst_neuron & 0xFF) << 16)    # dst_neuron (8-bit)
    data |= ((weight     & 0xFF) << 8)     # weight (8-bit)
    data |= (1 if exc else 0)              # exc_inh (bit 0)

    return addr, data


def ct_write(mmio, addr: int, data: int):
    """Write one row of the connectivity table via AXI-Lite."""
    mmio.write(CFG_CTRL,  0)      # target = router
    mmio.write(CFG_ADDR,  addr)
    mmio.write(CFG_WDATA, data)   # triggers config_we pulse


def upload_layer3_weights(mmio, q_fc_w: np.ndarray):
    """
    Upload Layer 2 -> Layer 3 dense weights to hardware connectivity table.
      - Source neurons: 784 Layer 2 neurons mapped across Groups 0..3 (196 each)
      - Destination neurons: 10 Class neurons in Group 4
    """
    n_classes, n_l2 = q_fc_w.shape  # (10, 784)
    print(f"Uploading Layer 3 weights to hardware connectivity table (784 -> 10, {n_l2 * n_classes} synapses)...")
    total_entries = 0

    for global_src in range(n_l2):
        src_grp = global_src // GROUP_SIZE_L2
        src_nid = global_src % GROUP_SIZE_L2
        fanout = 0

        for dst in range(n_classes):
            w = int(q_fc_w[dst, global_src])
            if w != 0:
                addr, data = encode_ct_write(
                    src_group=src_grp,
                    src_neuron=src_nid,
                    fanout_idx=fanout,
                    dst_group=OUTPUT_GROUP,
                    dst_neuron=dst,
                    weight=abs(w),
                    exc=(w > 0)
                )
                ct_write(mmio, addr, data)
                fanout += 1

        # Invalidate remaining fanout slots up to 16
        if fanout < 16:
            addr, _ = encode_ct_write(src_grp, src_nid, fanout, 0, 0, 0, False)
            ct_write(mmio, addr, 0)
        total_entries += fanout

    print(f"  Layer 3: Successfully wrote {total_entries} active synaptic connections into BRAM table.")


def main():
    parser = argparse.ArgumentParser(description="All-on-FPGA CNN3 SNN Hardware Inference with SCA Trigger")
    parser.add_argument('--bitstream',     default='snn_core_group_v3.bit',
                        help='Path to snn_core_group_v3 bitstream')
    parser.add_argument('--data',          default='mnist_cnn3_deployment.npz',
                        help='Deployment payload (.npz)')
    parser.add_argument('--samples',  type=int, default=10000,
                        help='Number of test images to evaluate (default: 10000)')
    parser.add_argument('--timesteps', type=int, default=4,
                        help='Number of SNN timesteps (default: 4)')
    parser.add_argument('--output-json',   default='mnist_cnn3_inference_results.json',
                        help='Results output JSON path')
    parser.add_argument('--skip-bitstream', action='store_true',
                        help='Skip PL programming if overlay is already active')
    args = parser.parse_args()

    # ── Load Deployment Payload ───────────────────────────────────────────────
    print(f"Loading CNN3 deployment payload: {args.data}")
    payload      = np.load(args.data)
    q_fc_w       = payload['q_fc_w']        # (10, 784) int8
    test_imgs    = payload['test_imgs']     # (10000, 28, 28) pre-normalized float32
    test_lbls    = payload['test_lbls']     # (10000,)
    hw_threshold = int(payload['hw_threshold'])

    print(f"  Dataset: {len(test_imgs)} test images loaded.")
    print(f"  Hardware calibrated threshold: {hw_threshold}")

    # ── Initialise PYNQ Overlay ───────────────────────────────────────────────
    try:
        from pynq import Overlay, allocate
        print("Initialising PYNQ Overlay...")
        if not args.skip_bitstream and os.path.exists(args.bitstream):
            overlay = Overlay(args.bitstream)
            print(f"  Programmed PL with: {args.bitstream}")
        else:
            overlay = Overlay(args.bitstream, download=False)
            print("  Using existing PL configuration.")

        mmio     = overlay.snn_config_regs_0.mmio
        hls_ctrl = overlay.snn_top_hls_0.mmio
        dma      = overlay.axi_dma_0

        # Reset HLS core
        print("Resetting HLS core and hardware state...")
        hls_ctrl.write(0x00, 0x02) # assert reset
        time.sleep(0.01)
        hls_ctrl.write(0x00, 0x00) # deassert reset
        time.sleep(0.01)

        # ── Upload Weights to Connectivity Table ──────────────────────────────
        upload_layer3_weights(mmio, q_fc_w)

        # ── Configure Hardware Neurons & Registers ─────────────────────────────
        mmio.write(CFG_THRESHOLD, hw_threshold & 0xFFFF)
        mmio.write(CFG_NEURON_PARAMS, 0x0000)  # leak=0, refrac=0
        print(f"  Hardware global threshold configured: {hw_threshold}")

        # ── Configure HLS for CNN Streaming Mode ───────────────────────────────
        hls_ctrl.write(0x10, MODE_CNN_STREAM)   # Mode 3: Streaming 2D Conv
        hls_ctrl.write(0x18, hw_threshold)
        hls_ctrl.write(0x28, args.timesteps)    # timesteps = 4
        hls_ctrl.write(0x00, 0x01)              # enable = 1

        # ── Allocate DMA Buffers ──────────────────────────────────────────────
        in_buffer  = allocate(shape=(784,), dtype=np.uint32)
        out_buffer = allocate(shape=(256,), dtype=np.uint32)

        # ── Run Hardware Inference Loop ───────────────────────────────────────
        n_test  = min(args.samples, len(test_imgs))
        correct = 0
        total_spikes = 0
        latencies_ms = []

        print(f"\nStarting 100% on-FPGA inference on {n_test} images (Pin Y18 SCA Trigger active)...")
        t_start_all = time.time()

        for i in range(n_test):
            img = test_imgs[i] # 28x28 float32
            lbl = int(test_lbls[i])

            # Quantize pixel values to Q8.8 fixed-point (pixel * 256)
            px_quant = np.clip(np.round(img.flatten() * 256.0), -32768, 32767).astype(np.int16)
            for k in range(784):
                in_buffer[k] = int(px_quant[k]) & 0xFFFF

            # DMA Transfer: Send pixels to HLS Conv1 -> SNN Core Groups -> Read output
            t0 = time.time()
            dma.sendchannel.transfer(in_buffer)
            dma.recvchannel.transfer(out_buffer)
            dma.sendchannel.wait()
            dma.recvchannel.wait()
            t1 = time.time()
            latencies_ms.append((t1 - t0) * 1000.0)

            # Unpack class spikes from output buffer
            # Output packets: [9:0] = global_id {group[2:0], local[7:0]}
            class_spk = np.zeros(10, dtype=np.int32)
            for pkt in out_buffer:
                if pkt != 0:
                    gid = pkt & 0x7FF
                    grp = (gid >> LOCAL_ID_WIDTH) & 0x7
                    nid = gid & 0xFF
                    if grp == OUTPUT_GROUP and nid < 10:
                        class_spk[nid] += 1

            total_spikes += np.sum(class_spk)
            pred = int(np.argmax(class_spk))
            if pred == lbl:
                correct += 1

            if (i + 1) % 500 == 0 or (i + 1) == n_test:
                acc_so_far = correct / (i + 1) * 100
                avg_spk_so_far = total_spikes / (i + 1)
                print(f"  Processed [{i+1:5d}/{n_test:5d}] | Acc: {acc_so_far:.2f}% | Avg Spikes/Img: {avg_spk_so_far:.1f}")

        total_time = time.time() - t_start_all
        accuracy = correct / n_test * 100
        avg_lat = np.mean(latencies_ms)
        fps = n_test / total_time

        print(f"\n========================================================")
        print(f"  CNN3 Hardware Inference Results (All-on-FPGA)")
        print(f"========================================================")
        print(f"  Total Images   : {n_test}")
        print(f"  Accuracy       : {accuracy:.2f}% ({correct}/{n_test})")
        print(f"  Avg Latency    : {avg_lat:.2f} ms/image")
        print(f"  Throughput     : {fps:.1f} FPS")
        print(f"  Avg Spk/Img    : {total_spikes / n_test:.1f}")
        print(f"========================================================")

        # Save summary JSON
        os.makedirs(os.path.dirname(args.output_json), exist_ok=True)
        results = {
            "model": "cnn3_T_4_clean_l2",
            "samples": n_test,
            "accuracy": accuracy,
            "latency_ms_avg": avg_lat,
            "fps": fps,
            "avg_spikes_per_image": total_spikes / n_test,
            "hardware_threshold": hw_threshold,
            "timestamp": datetime.now().isoformat()
        }
        with open(args.output_json, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Saved results to: {args.output_json}")

    except ImportError:
        print("Note: pynq library not found on this host. Run this script directly on the PYNQ-Z2 board.")


if __name__ == '__main__':
    main()

