#!/usr/bin/env python3
"""
fpga_cnn3_coproc_inference.py
==============================
Hardware Co-Processing Inference for 3-Layer Convolutional SNN (CNN3).
Mirrors the proven architectural blueprint of the FC3 accelerator (>97% on-board accuracy).

Partitioning:
  - Layer 1 (Conv1 + Pool1): Executed on ARM Cortex-A9 host in Float32 (~0.12 ms)
  - Layer 2 (Conv2 + Pool2): Executed on ARM Cortex-A9 host using Int8 quantized weights (~0.35 ms)
  - Layer 3 (Classifier)   : Executed on FPGA Hardware (Core Group 4 LIF Neurons)
                             Inter-layer weights mapped via BRAM Connectivity Table.

Hardware Platform:
  - PYNQ-Z2 (Zynq-7020)
  - Bitstream: snn_core_group_v3.bit
  - Trigger Pin: Y18 (active during FPGA classification integration)
"""

import os
import sys
import time
import json
import argparse
import numpy as np
import torch
import torch.nn as nn

# ─────────────────────────────────────────────────────────────────────────────
# Hardware Architecture Constants (snn_core_group_v3)
# ─────────────────────────────────────────────────────────────────────────────
NUM_GROUPS         = 5
GROUP_SIZE_L2      = 196  # Groups 0..3: Layer 2 hidden neurons (4 x 196 = 784)
OUTPUT_GROUP       = 4    # Group 4: Layer 3 output class neurons (10 classes: 0..9)
LOCAL_ID_WIDTH     = 8    # 196 neurons fits in 8 bits
GROUP_ID_WIDTH     = 3    # 5 groups fits in 3 bits
GLOBAL_ID_WIDTH    = 11   # bits [10:8]=group, bits [7:0]=local neuron

# Register Offsets (snn_config_regs.v)
CFG_CTRL           = 0x00
CFG_ADDR           = 0x04
CFG_WDATA          = 0x08
CFG_THRESHOLD      = 0x10
CFG_NEURON_PARAMS  = 0x14
CFG_ROUTER_SPKS    = 0x18
CFG_NEURON_SPKS    = 0x1C

# HLS Modes
MODE_INFERENCE     = 0x00 # Forward spike streaming directly into Event Router
MODE_CNN_STREAM    = 0x03


def encode_ct_write(src_group: int, src_neuron: int, fanout_idx: int,
                    dst_group: int, dst_neuron: int, weight: int,
                    exc: bool) -> tuple:
    """
    Encode Connectivity Table write operation.
      ADDR:  [31:28]=0x0, [27:20]=fanout_idx(8b), [19:12]=src_neuron(8b), [3:0]=src_group(4b)
      WDATA: [31]=valid, [30:27]=dst_group(4b), [23:16]=dst_neuron(8b), [15:8]=weight(8b), [0]=exc_inh
    """
    addr = ((fanout_idx & 0xFF) << 20) | ((src_neuron & 0xFF) << 12) | (src_group & 0xF)
    w_u8 = abs(int(weight)) & 0xFF
    data = (1 << 31) | ((dst_group & 0xF) << 27) | ((dst_neuron & 0xFF) << 16) | (w_u8 << 8) | (1 if exc else 0)
    return addr, data


def prepare_ct_table(q_fc_w: np.ndarray) -> list:
    """
    Prepares the BRAM Connectivity Table entries for Layer 3 (784 -> 10).
      - Source: 784 neurons across Groups 0..3 (196 each)
      - Destination: 10 Class neurons in Group 4
    """
    n_classes, n_l2 = q_fc_w.shape
    entries = []
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
                entries.append((addr, data))
                fanout += 1
        # Invalidate remaining slot to mark end of list
        if fanout < 16:
            addr, _ = encode_ct_write(
                src_group=src_grp,
                src_neuron=src_nid,
                fanout_idx=fanout,
                dst_group=0,
                dst_neuron=0,
                weight=0,
                exc=False
            )
            entries.append((addr, 0))
    return entries


def upload_layer3_weights(mmio, entries: list):
    """Upload Connectivity Table entries to FPGA BRAM via AXI-Lite."""
    mmio.write(CFG_CTRL, 0)
    for addr, data in entries:
        mmio.write(CFG_ADDR, addr)
        mmio.write(CFG_WDATA, data)
    print(f"  [Init] Successfully uploaded {len(entries)} Layer 3 synaptic connections to BRAM table.")


def reset_hardware_state(hls_ctrl, mmio):
    """Zero hardware membrane potentials using leak sweep FSM."""
    # Configure 100% leak rate on RTL Core Groups
    mmio.write(CFG_NEURON_PARAMS, 0x0009) # shift1=1, shift2=1 -> 100% leak
    hls_ctrl.write(0x10, 0x01)            # enable=1, reset=0
    hls_ctrl.write(0x28, 1000)            # 1000 cycles (>588 cycles required to sweep 196 neurons)
    hls_ctrl.write(0x00, 0x01)            # ap_start
    t0 = time.time() + 0.010
    while time.time() < t0:
        if hls_ctrl.read(0x00) & 0x02:
            break
    # Restore 0% leak for inference
    mmio.write(CFG_NEURON_PARAMS, 0x0000)
    hls_ctrl.write(0x28, 1)
    hls_ctrl.write(0x00, 0x00)


def run_software_simulation(test_imgs, test_lbls, w1_f, b1_f, q_conv2_w, q_fc_w, hw_threshold, timesteps, samples):
    """Bit-accurate software verification of the co-processing pipeline."""
    print("\n" + "=" * 65)
    print(f"  RUNNING SOFTWARE SIMULATION (OPTION A) ON {samples} IMAGES")
    print("=" * 65)

    conv1 = nn.Conv2d(1, w1_f.shape[0], 3, padding=1)
    conv1.weight.data = torch.from_numpy(w1_f)
    conv1.bias.data = torch.from_numpy(b1_f)
    pool1 = nn.AvgPool2d(2, 2)
    pool2 = nn.AvgPool2d(2, 2)
    q_conv2_t = torch.from_numpy(q_conv2_w.astype(np.float32))

    correct = 0
    total_spikes = np.zeros(10, dtype=np.int32)
    t_start = time.time()

    for i in range(samples):
        img_t = torch.from_numpy(test_imgs[i]).unsqueeze(0).unsqueeze(0) # (1, 1, 28, 28)
        lbl = int(test_lbls[i])

        v1 = torch.zeros(1, 8, 28, 28)
        v2 = torch.zeros(1, 16, 14, 14)
        v4 = np.zeros(10, dtype=np.int32)
        spk_out = np.zeros(10, dtype=np.int32)

        cur1 = conv1(img_t)
        for t in range(timesteps):
            # Layer 1
            v1 += cur1
            s1 = (v1 >= 1.0).float()
            v1 -= s1 * 1.0
            p1 = pool1(s1)

            # Layer 2
            cur2 = nn.functional.conv2d(p1, q_conv2_t, padding=1)
            v2 += cur2
            s2 = (v2 >= hw_threshold).float()
            v2 -= s2 * hw_threshold
            p2 = (pool2(s2) * 4.0).view(784).numpy()

            # Active Layer 2 spikes
            active_srcs = np.nonzero(p2 > 0)[0]
            for src in active_srcs:
                count = int(p2[src])
                for _ in range(count):
                    # Deliver weights to Group 4 (Layer 3)
                    for c in range(10):
                        v4[c] += int(q_fc_w[c, src])
                        if v4[c] < 0:
                            v4[c] = 0
                        if v4[c] >= hw_threshold:
                            v4[c] -= hw_threshold
                            spk_out[c] += 1

        pred = int(np.argmax(spk_out))
        if pred == lbl:
            correct += 1
        total_spikes += spk_out

    dt = time.time() - t_start
    acc = correct / samples * 100.0
    print(f"\nSimulation Results:")
    print(f"  Accuracy: {acc:.2f}% ({correct}/{samples})")
    print(f"  Total Spikes per Class: {total_spikes.tolist()}")
    print(f"  Elapsed Time: {dt*1000:.1f} ms ({dt/samples*1000:.2f} ms/img)")
    return acc


def main():
    parser = argparse.ArgumentParser(description="Co-Processing CNN3 SNN Hardware Inference on PYNQ-Z2")
    parser.add_argument('--bitstream',     default='snn_core_group_v3.bit',
                        help='Path to snn_core_group_v3 bitstream')
    parser.add_argument('--data',          default='mnist_cnn3_deployment.npz',
                        help='Deployment payload path (.npz)')
    parser.add_argument('--samples',  type=int, default=1000,
                        help='Number of test images to evaluate (default: 1000)')
    parser.add_argument('--timesteps', type=int, default=4,
                        help='Number of SNN timesteps (default: 4)')
    parser.add_argument('--threshold', type=int, default=None,
                        help='Optional override for global firing threshold (default: from payload)')
    parser.add_argument('--output-json',   default='mnist_cnn3_coproc_results.json',
                        help='Results output JSON path')
    parser.add_argument('--skip-bitstream', action='store_true',
                        help='Skip PL bitstream programming if overlay is already active')
    parser.add_argument('--reset-mode', choices=['flash', 'fast'], default='flash',
                        help='Hardware state reset mode: flash (bitstream reload) or fast (leak sweep)')
    parser.add_argument('--sim-only', action='store_true',
                        help='Run bit-accurate software simulation only (for testing without FPGA board)')
    args = parser.parse_args()

    # ── 1. Load Deployment Payload ───────────────────────────────────────────
    print(f"Loading CNN3 deployment payload: {args.data}")
    if not os.path.exists(args.data):
        print(f"ERROR: Payload file not found: {args.data}")
        sys.exit(1)

    payload      = np.load(args.data)
    w1_f         = payload['w1_f']          # (8, 1, 3, 3) float32
    b1_f         = payload['b1_f']          # (8,) float32
    q_conv2_w    = payload['q_conv2_w']     # (16, 8, 3, 3) int8
    q_fc_w       = payload['q_fc_w']        # (10, 784) int8
    test_imgs    = payload['test_imgs']     # (10000, 28, 28) float32
    test_lbls    = payload['test_lbls']     # (10000,) int64
    hw_threshold = args.threshold if args.threshold is not None else int(payload['hw_threshold'])
    n_test       = min(args.samples, len(test_imgs))

    print(f"  Dataset: {len(test_imgs)} test images loaded (evaluating {n_test}).")
    print(f"  Hardware global threshold: {hw_threshold}")

    # If sim-only requested or running on non-PYNQ host without pynq module
    if args.sim_only:
        run_software_simulation(test_imgs, test_lbls, w1_f, b1_f, q_conv2_w, q_fc_w, hw_threshold, args.timesteps, n_test)
        return

    try:
        from pynq import Overlay, allocate
    except ImportError:
        print("\n[INFO] PYNQ library not found on this machine.")
        print("[INFO] Executing bit-accurate software simulation of Option A instead...\n")
        run_software_simulation(test_imgs, test_lbls, w1_f, b1_f, q_conv2_w, q_fc_w, hw_threshold, args.timesteps, n_test)
        return

    # ── 2. Initialize PYNQ Overlay & Hardware ─────────────────────────────────
    print("Initialising PYNQ Overlay...")
    if not args.skip_bitstream and os.path.exists(args.bitstream):
        overlay = Overlay(args.bitstream)
        print(f"  Programmed PL with: {args.bitstream}")
    else:
        overlay = Overlay(args.bitstream, download=False)
        print("  Using existing PL configuration.")

    mmio     = overlay.snn_config_regs_0.mmio
    hls_ctrl = overlay.snn_top_hls_0.mmio
    dma_mmio = overlay.axi_dma_0.mmio

    # Reset HLS core
    print("Resetting HLS core and hardware state...")
    hls_ctrl.write(0x00, 0x02) # assert reset
    time.sleep(0.01)
    hls_ctrl.write(0x00, 0x00) # deassert reset
    time.sleep(0.01)

    # ── 3. Upload Layer 3 Weights to Connectivity Table ───────────────────────
    ct_entries = prepare_ct_table(q_fc_w)
    upload_layer3_weights(mmio, ct_entries)

    # ── 4. Configure Hardware Neurons & Registers ─────────────────────────────
    mmio.write(CFG_THRESHOLD, hw_threshold & 0xFFFF)
    mmio.write(CFG_NEURON_PARAMS, 0x0000) # leak=0, refrac=0
    print(f"  Hardware global threshold configured: {hw_threshold}")

    # Configure HLS in MODE_INFERENCE (0x00): stream spikes directly to Event Router
    hls_ctrl.write(0x10, 0x01)              # enable=1, reset=0
    hls_ctrl.write(0x18, hw_threshold)      # threshold
    hls_ctrl.write(0x20, MODE_INFERENCE)    # Mode 0: Direct spike stream to router
    hls_ctrl.write(0x28, 1)                 # 1 step
    hls_ctrl.write(0x00, 0x00)              # ap_ctrl: idle

    # ── 5. Allocate DMA Buffers ───────────────────────────────────────────────
    in_buffer  = allocate(shape=(1024,), dtype=np.uint32)
    out_buffer = allocate(shape=(128,), dtype=np.uint32)

    # Setup PyTorch host modules for Layer 1 and Layer 2
    conv1 = nn.Conv2d(1, w1_f.shape[0], 3, padding=1)
    conv1.weight.data = torch.from_numpy(w1_f)
    conv1.bias.data = torch.from_numpy(b1_f)
    pool1 = nn.AvgPool2d(2, 2)
    pool2 = nn.AvgPool2d(2, 2)
    q_conv2_t = torch.from_numpy(q_conv2_w.astype(np.float32))

    # ── 6. Run Co-Processing Inference Loop ───────────────────────────────────
    correct = 0
    total_spikes = 0
    latencies_ms = []
    log = []

    print(f"\nStarting Co-Processing Inference on {n_test} images (Pin Y18 active during FPGA integration)...")
    t_start_all = time.time()

    for i in range(n_test):
        img_np = test_imgs[i]
        lbl    = int(test_lbls[i])

        # Zero hardware state between images
        if args.reset_mode == 'flash':
            overlay.download()
            mmio     = overlay.snn_config_regs_0.mmio
            hls_ctrl = overlay.snn_top_hls_0.mmio
            dma_mmio = overlay.axi_dma_0.mmio
            upload_layer3_weights(mmio, ct_entries)
            mmio.write(CFG_THRESHOLD, hw_threshold & 0xFFFF)
            mmio.write(CFG_NEURON_PARAMS, 0x0000)
            hls_ctrl.write(0x10, 0x01)
            hls_ctrl.write(0x18, hw_threshold)
            hls_ctrl.write(0x20, MODE_INFERENCE)
            hls_ctrl.write(0x28, 1)
            hls_ctrl.write(0x00, 0x00)
        else:
            reset_hardware_state(hls_ctrl, mmio)

        # Host-side LIF membrane state for Layer 1 & 2
        v1 = torch.zeros(1, 8, 28, 28)
        v2 = torch.zeros(1, 16, 14, 14)
        class_spikes = np.zeros(10, dtype=np.int32)
        t_img_start = time.time()

        img_t = torch.from_numpy(img_np).unsqueeze(0).unsqueeze(0)
        cur1 = conv1(img_t)

        for t in range(args.timesteps):
            # A. Layer 1 (Conv1 + Pool1) on Host CPU
            v1 += cur1
            s1 = (v1 >= 1.0).float()
            v1 -= s1 * 1.0
            p1 = pool1(s1)

            # B. Layer 2 (Conv2 + Pool2) on Host CPU
            cur2 = nn.functional.conv2d(p1, q_conv2_t, padding=1)
            v2 += cur2
            s2 = (v2 >= hw_threshold).float()
            v2 -= s2 * hw_threshold
            p2 = (pool2(s2) * 4.0).view(784).numpy()

            # C. Pack active Layer 2 spikes for FPGA
            active_srcs = np.nonzero(p2 > 0)[0]
            spike_words = []
            toggle_w = False

            for src in active_srcs:
                src_grp = int(src // GROUP_SIZE_L2)
                src_nid = int(src % GROUP_SIZE_L2)
                global_nid = (src_grp << 8) | (src_nid & 0xFF)
                count = int(p2[src])

                for _ in range(count):
                    # Alternate weight between 127 and 126 to ensure RTL payload_changed is always 1
                    wt = 127 if not toggle_w else 126
                    toggle_w = not toggle_w
                    # DMA Spike Packet: bits [10:0]=global_nid, bits [18:11]=weight
                    pkt = (global_nid & 0x7FF) | ((wt & 0xFF) << 11)
                    spike_words.append(pkt)

            pkt_len = len(spike_words)
            if pkt_len > 0:
                pkt_len = min(pkt_len, 1024)
                for k in range(pkt_len):
                    in_buffer[k] = spike_words[k]
                in_buffer.flush()

                # Clean DMA channel reset
                dma_mmio.write(0x00, 0x04) # MM2S reset
                dma_mmio.write(0x30, 0x04) # S2MM reset
                time.sleep(0.0001)

                # Arm S2MM DMA (FPGA -> ARM) for first class spike
                dest_ptr = out_buffer.device_address
                dma_mmio.write(0x34, 0x1000) # clear IOC
                dma_mmio.write(0x30, 0x01)   # run
                dma_mmio.write(0x48, dest_ptr)
                dma_mmio.write(0x58, 4)      # arm 4 bytes

                # Start MM2S DMA (ARM -> FPGA)
                src_ptr = in_buffer.device_address
                dma_mmio.write(0x04, 0x1000) # clear IOC
                dma_mmio.write(0x00, 0x01)   # run
                dma_mmio.write(0x18, src_ptr)
                dma_mmio.write(0x28, pkt_len * 4)

                # Start HLS Kernel with Auto-Restart (Trigger Pin Y18 pulses HIGH!)
                hls_ctrl.write(0x00, 0x81)

                # Drain output class spikes from Group 4
                spikes_received = 0
                while spikes_received < 128:
                    timeout = time.time() + 0.003 # 3 ms tight timeout
                    got_spike = False
                    while time.time() < timeout:
                        if dma_mmio.read(0x34) & 0x1000:
                            got_spike = True
                            break
                    if got_spike:
                        spikes_received += 1
                        dma_mmio.write(0x34, 0x1000)
                        dma_mmio.write(0x30, 0x01)
                        if spikes_received < 128:
                            dma_mmio.write(0x48, dest_ptr + (spikes_received * 4))
                            dma_mmio.write(0x58, 4)
                    else:
                        break

                # Stop HLS and S2MM channel for this timestep
                hls_ctrl.write(0x00, 0x00)
                dma_mmio.write(0x30, 0x00)

                out_buffer.invalidate()

                # Decode output class spikes from Group 4
                for s in range(spikes_received):
                    out_val = int(out_buffer[s])
                    if out_val > 0:
                        gid = out_val & 0x7FF
                        grp = gid >> LOCAL_ID_WIDTH
                        loc = gid & 0xFF
                        if grp == OUTPUT_GROUP and loc < 10:
                            class_spikes[loc] += 1

                out_buffer[:] = 0

        dt_ms = (time.time() - t_img_start) * 1000.0
        latencies_ms.append(dt_ms)
        pred = int(np.argmax(class_spikes))
        is_corr = (pred == lbl)
        if is_corr:
            correct += 1
        total_spikes += int(np.sum(class_spikes))

        log.append({
            "image_index": i,
            "true_label": lbl,
            "predicted_label": pred,
            "spikes": class_spikes.tolist(),
            "latency_ms": round(dt_ms, 2)
        })

        if (i + 1) % 10 == 0 or (i + 1) == n_test:
            cur_acc = correct / (i + 1) * 100.0
            print(f"[{i+1:4d}/{n_test}] True: {lbl} | Pred: {pred} | Spikes: {class_spikes.tolist()} | Acc: {cur_acc:5.1f}% | Lat: {dt_ms:5.1f}ms")

    # ── 7. Summary & Output ───────────────────────────────────────────────────
    total_time = time.time() - t_start_all
    final_acc = correct / n_test * 100.0
    avg_lat = np.mean(latencies_ms)
    avg_spk = total_spikes / n_test

    print("\n" + "=" * 65)
    print("  CNN3 SNN CO-PROCESSING HARDWARE EVALUATION COMPLETE")
    print("=" * 65)
    print(f"  Accuracy                : {final_acc:.2f}% ({correct}/{n_test})")
    print(f"  Average Latency         : {avg_lat:.2f} ms/image ({1000.0/avg_lat:.1f} FPS)")
    print(f"  Average Output Spikes   : {avg_spk:.2f} spikes/image")
    print(f"  Total Evaluation Time   : {total_time:.2f} s")
    print("=" * 65)

    results = {
        "metadata": {
            "model": "cnn3_T_4_clean_l2",
            "samples": n_test,
            "timesteps": args.timesteps,
            "hw_threshold": hw_threshold,
            "pipeline": "Option A Co-Processing (CPU Conv1+Conv2 -> FPGA Group 4)"
        },
        "metrics": {
            "accuracy_percent": round(final_acc, 2),
            "correct": correct,
            "total": n_test,
            "average_latency_ms": round(avg_lat, 2),
            "avg_spikes_per_image": round(avg_spk, 2)
        },
        "predictions": log
    }

    with open(args.output_json, 'w') as f:
        json.dump(results, f, indent=4)
    print(f"Saved inference results to: {args.output_json}\n")


if __name__ == '__main__':
    main()

