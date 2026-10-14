#!/usr/bin/env python3
"""
diag_cnn3_hardware.py
=====================
Comprehensive diagnostic script for the 3-layer CNN SNN hardware accelerator on PYNQ-Z2.

Isolates and tests:
  1. Image Isolation & Membrane State Persistence Test (Repeatability)
  2. Two-Step HLS Reset + RTL Leak Zeroing Verification
  3. Single-Image Evaluation on 20 MNIST images with full isolation
  4. Hardware Firing Threshold Sweep [75, 90, 103, 115, 130]
"""

import argparse
import time
import os
import sys
import numpy as np

# Hardware Parameters
NUM_GROUPS         = 5
GROUP_SIZE_L2      = 196
GROUP_SIZE_L3      = 16
OUTPUT_GROUP       = 4
LOCAL_ID_WIDTH     = 8

# Register offsets
CFG_CTRL           = 0x00
CFG_ADDR           = 0x04
CFG_WDATA          = 0x08
CFG_THRESHOLD      = 0x10
CFG_NEURON_PARAMS  = 0x14
CFG_ROUTER_SPKS    = 0x18
CFG_NEURON_SPKS    = 0x1C

MODE_CNN_STREAM    = 0x03


def encode_ct_write(src_group, src_neuron, fanout_idx, dst_group, dst_neuron, weight, exc):
    addr = ((fanout_idx & 0xFF) << 20) | ((src_neuron & 0xFF) << 12) | (src_group & 0xF)
    w_u8 = abs(int(weight)) & 0xFF
    data = (1 << 31) | ((dst_group & 0xF) << 27) | ((dst_neuron & 0xFF) << 16) | (w_u8 << 8) | (1 if exc else 0)
    return addr, data


def ct_write(mmio, addr, data):
    mmio.write(CFG_CTRL,  0)
    mmio.write(CFG_ADDR,  addr)
    mmio.write(CFG_WDATA, data)


def prepare_ct_table(q_fc_w):
    n_classes, n_l2 = q_fc_w.shape
    entries = []
    for global_src in range(n_l2):
        src_grp = global_src // GROUP_SIZE_L2
        src_nid = global_src % GROUP_SIZE_L2
        fanout = 0
        for dst in range(n_classes):
            w = int(q_fc_w[dst, global_src])
            if w != 0:
                addr, data = encode_ct_write(src_grp, src_nid, fanout, OUTPUT_GROUP, dst, abs(w), (w > 0))
                entries.append((addr, data))
                fanout += 1
        if fanout < 16:
            addr, _ = encode_ct_write(src_grp, src_nid, fanout, 0, 0, 0, False)
            entries.append((addr, 0))
    return entries


def fast_upload_layer3_weights(mmio, entries):
    mmio.write(CFG_CTRL, 0)
    for addr, data in entries:
        mmio.write(CFG_ADDR, addr)
        mmio.write(CFG_WDATA, data)


def upload_layer3_weights(mmio, q_fc_w):
    entries = prepare_ct_table(q_fc_w)
    fast_upload_layer3_weights(mmio, entries)
    print(f"  [Init] Uploaded {len(entries)} Layer 3 synapses into BRAM table.")


def configure_hardware(overlay, ct_entries, hw_threshold):
    overlay.download()
    mmio     = overlay.snn_config_regs_0.mmio
    hls_ctrl = overlay.snn_top_hls_0.mmio
    dma_mmio = overlay.axi_dma_0.mmio

    fast_upload_layer3_weights(mmio, ct_entries)
    mmio.write(CFG_THRESHOLD, hw_threshold & 0xFFFF)
    mmio.write(CFG_NEURON_PARAMS, 0x0000)

    # Configure HLS Kernel for Mode 3 (CNN Stream)
    hls_ctrl.write(0x10, 0x01)              # enable=1, reset=0
    hls_ctrl.write(0x18, hw_threshold)      # threshold
    hls_ctrl.write(0x20, MODE_CNN_STREAM)   # Mode 3 (Streaming 2D Conv)
    hls_ctrl.write(0x28, 1)                 # 1 step
    hls_ctrl.write(0x00, 0x00)              # ap_ctrl: idle

    return mmio, hls_ctrl, dma_mmio


def reset_hardware_state(hls_ctrl, mmio):
    """
    Two-step safe reset:
      1. Execute HLS reset body (clears Conv1 line buffer, window, membrane & drains FIFO).
      2. Run 1-cycle step with reset=0 to deassert physical snn_reset wire on FPGA.
      3. Pulse maximum leak (0x09) on RTL Core Groups to zero BRAM membrane potentials.
    """
    # 1. HLS Reset step
    hls_ctrl.write(0x10, 0x03)          # ctrl_reg: enable=1, reset=1
    hls_ctrl.write(0x28, 1)             # 1 step
    hls_ctrl.write(0x00, 0x01)          # ap_start
    t0 = time.time() + 0.010
    while time.time() < t0:
        if hls_ctrl.read(0x00) & 0x02:  # wait ap_done
            break

    # 2. HLS Deassert reset wire step
    hls_ctrl.write(0x10, 0x01)          # ctrl_reg: enable=1, reset=0
    hls_ctrl.write(0x20, MODE_CNN_STREAM)
    hls_ctrl.write(0x28, 1)
    hls_ctrl.write(0x00, 0x01)          # ap_start -> snn_reset drops to 0!
    t0 = time.time() + 0.010
    while time.time() < t0:
        if hls_ctrl.read(0x00) & 0x02:
            break

    # 3. Clear RTL Core Group BRAM membrane potentials via leak sweep
    mmio.write(CFG_NEURON_PARAMS, 0x0009) # shift1=1, shift2=1 -> leak 100% of potential
    time.sleep(0.0002)                   # 200 us is >30x the 6 us needed for 588-cycle sweep
    mmio.write(CFG_NEURON_PARAMS, 0x0000) # restore zero leak for inference


def run_single_inference(img, timesteps, dma_mmio, hls_ctrl, in_buffer, out_buffer):
    """Executes a single MNIST image across T timesteps and returns class spike vector."""
    px_quant = np.clip(np.round(img.flatten() * 256.0), -32768, 32767).astype(np.int16)
    for k in range(784):
        in_buffer[k] = int(px_quant[k]) & 0xFFFF
    in_buffer.flush()

    class_spk = np.zeros(10, dtype=np.int32)

    for t in range(timesteps):
        # Reset DMA channels
        dma_mmio.write(0x00, 0x04)
        dma_mmio.write(0x30, 0x04)
        time.sleep(0.0001)

        # Arm S2MM
        dest_ptr = out_buffer.device_address
        dma_mmio.write(0x34, 0x1000)
        dma_mmio.write(0x30, 0x01)
        dma_mmio.write(0x48, dest_ptr)
        dma_mmio.write(0x58, 4)

        # Start MM2S
        src_ptr = in_buffer.device_address
        dma_mmio.write(0x00, 0x01)
        dma_mmio.write(0x18, src_ptr)
        dma_mmio.write(0x28, 784 * 4)

        # Start HLS
        hls_ctrl.write(0x00, 0x81)

        # Poll output spikes
        spikes_received = 0
        while spikes_received < 128:
            timeout = time.time() + 0.005
            got_spike = False
            while time.time() < timeout:
                if dma_mmio.read(0x34) & 0x1000:
                    got_spike = True
                    break
            if got_spike:
                spikes_received += 1
                dma_mmio.write(0x34, 0x1000)
                dma_mmio.write(0x30, 0x01)
                dma_mmio.write(0x48, dest_ptr + (spikes_received * 4))
                dma_mmio.write(0x58, 4)
            else:
                break

        # Stop HLS & S2MM
        hls_ctrl.write(0x00, 0x00)
        dma_mmio.write(0x30, 0x00)
        out_buffer.invalidate()

        for s in range(spikes_received):
            pkt = int(out_buffer[s])
            if pkt != 0:
                gid = pkt & 0x7FF
                grp = (gid >> LOCAL_ID_WIDTH) & 0x7
                nid = gid & 0xFF
                if grp == OUTPUT_GROUP and nid < 10:
                    class_spk[nid] += 1
        out_buffer[:] = 0

    return class_spk


def main():
    parser = argparse.ArgumentParser(description="CNN3 SNN Accelerator Diagnostic Suite")
    parser.add_argument('--bitstream', default='snn_core_group_v3.bit')
    parser.add_argument('--data',      default='mnist_cnn3_deployment.npz')
    parser.add_argument('--timesteps', type=int, default=4)
    args = parser.parse_args()

    print("=" * 65)
    print("  CNN3 SNN Hardware Diagnostic Suite")
    print("=" * 65)

    payload = np.load(args.data)
    q_fc_w = payload['q_fc_w']
    test_imgs = payload['test_imgs']
    test_lbls = payload['test_lbls']
    hw_threshold = int(payload['hw_threshold'])
    print(f"Payload loaded: {len(test_imgs)} test images, calibrated threshold = {hw_threshold}")

    try:
        from pynq import Overlay, allocate
        overlay = Overlay(args.bitstream)

        # Pre-compile Layer 3 Connectivity Table entries
        ct_entries = prepare_ct_table(q_fc_w)

        # Initial full hardware configuration
        mmio, hls_ctrl, dma_mmio = configure_hardware(overlay, ct_entries, hw_threshold)

        in_buffer  = allocate(shape=(784,), dtype=np.uint32)
        out_buffer = allocate(shape=(256,), dtype=np.uint32)

        # ─────────────────────────────────────────────────────────────────────
        # DIAGNOSTIC TEST 1: Repeatability & State Isolation Test on Image 0
        # ─────────────────────────────────────────────────────────────────────
        print("\n" + "=" * 65)
        print("TEST 1: State Isolation & Repeatability Test (Image 0: True Label = %d)" % int(test_lbls[0]))
        print("=" * 65)

        # Run 1A: Clean Initial State (cold boot)
        spk_1a = run_single_inference(test_imgs[0], args.timesteps, dma_mmio, hls_ctrl, in_buffer, out_buffer)
        pred_1a = int(np.argmax(spk_1a))
        print(f"  Run 1A (Clean State)      : Pred={pred_1a} | Spikes={spk_1a.tolist()} | Total Spikes={np.sum(spk_1a)}")

        # Run 1B: WITHOUT Reset (observe state leakage)
        spk_1b = run_single_inference(test_imgs[0], args.timesteps, dma_mmio, hls_ctrl, in_buffer, out_buffer)
        pred_1b = int(np.argmax(spk_1b))
        print(f"  Run 1B (Without Reset)    : Pred={pred_1b} | Spikes={spk_1b.tolist()} | Total Spikes={np.sum(spk_1b)}")

        # Run 1C: With Soft Register Reset (observe if soft reset cleared BRAM)
        reset_hardware_state(hls_ctrl, mmio)
        spk_1c = run_single_inference(test_imgs[0], args.timesteps, dma_mmio, hls_ctrl, in_buffer, out_buffer)
        pred_1c = int(np.argmax(spk_1c))
        print(f"  Run 1C (Soft Register Reset) : Pred={pred_1c} | Spikes={spk_1c.tolist()} | Total Spikes={np.sum(spk_1c)}")

        # Run 1D: True Hardware PL Flash Reset via overlay.download()
        t_flash0 = time.time()
        mmio, hls_ctrl, dma_mmio = configure_hardware(overlay, ct_entries, hw_threshold)
        t_flash = (time.time() - t_flash0) * 1000.0

        spk_1d = run_single_inference(test_imgs[0], args.timesteps, dma_mmio, hls_ctrl, in_buffer, out_buffer)
        pred_1d = int(np.argmax(spk_1d))
        print(f"  Run 1D (Hardware Flash Reset, {t_flash:.1f}ms): Pred={pred_1d} | Spikes={spk_1d.tolist()} | Total Spikes={np.sum(spk_1d)}")

        repeatable_flash = np.array_equal(spk_1a, spk_1d)
        leakage_detected = not np.array_equal(spk_1a, spk_1b)
        print(f"\n  >> Diagnostic Result:")
        print(f"     Soft Register Reset Repeatability: {'PASS' if np.array_equal(spk_1a, spk_1c) else 'FAIL (Residual BRAM Charge Leaked)'}")
        print(f"     Hardware Flash Repeatability: {'PASS (100% Deterministic Silicon Isolation)' if repeatable_flash else 'FAIL'}")
        print(f"     Cross-Image State Leakage: {'DETECTED (Confirming Root Cause)' if leakage_detected else 'None'}")

        # ─────────────────────────────────────────────────────────────────────
        # DIAGNOSTIC TEST 2: Evaluation with Guaranteed Image Isolation on 20 Images
        # ─────────────────────────────────────────────────────────────────────
        print("\n" + "=" * 65)
        print("TEST 2: Clean Hardware-Isolated Inference on First 20 Images (Threshold = %d)" % hw_threshold)
        print("=" * 65)

        correct = 0
        total_spks = 0
        latencies = []
        for i in range(20):
            t_img0 = time.time()
            mmio, hls_ctrl, dma_mmio = configure_hardware(overlay, ct_entries, hw_threshold)
            spk = run_single_inference(test_imgs[i], args.timesteps, dma_mmio, hls_ctrl, in_buffer, out_buffer)
            lat_ms = (time.time() - t_img0) * 1000.0
            latencies.append(lat_ms)

            pred = int(np.argmax(spk)) if np.sum(spk) > 0 else 0
            is_corr = (pred == test_lbls[i])
            if is_corr:
                correct += 1
            total_spks += np.sum(spk)
            mark = "✓" if is_corr else "✗"
            print(f"  Img [{i:2d}/20] | True: {test_lbls[i]} | Pred: {pred} {mark} | Spikes: {spk.tolist()} | Lat: {lat_ms:.1f}ms")

        print(f"\n  >> Test 2 Clean Accuracy: {correct}/20 ({correct/20*100:.1f}%) | Avg Spikes/Img: {total_spks/20:.1f} | Avg Latency: {np.mean(latencies):.1f}ms/img")

        # ─────────────────────────────────────────────────────────────────────
        # DIAGNOSTIC TEST 3: Hardware Firing Threshold Sweep on 20 Images
        # ─────────────────────────────────────────────────────────────────────
        print("\n" + "=" * 65)
        print("TEST 3: Threshold Sweep with Image Isolation [75, 90, 103, 115, 130]")
        print("=" * 65)

        candidate_thresholds = [75, 90, 103, 115, 130]
        for th in candidate_thresholds:
            mmio.write(CFG_THRESHOLD, th & 0xFFFF)
            th_correct = 0
            th_spikes = 0
            for i in range(20):
                reset_hardware_state(hls_ctrl, mmio)
                spk = run_single_inference(test_imgs[i], args.timesteps, dma_mmio, hls_ctrl, in_buffer, out_buffer)
                pred = int(np.argmax(spk)) if np.sum(spk) > 0 else 0
                if pred == test_lbls[i]:
                    th_correct += 1
                th_spikes += np.sum(spk)
            print(f"  Threshold {th:3d} -> Accuracy: {th_correct:2d}/20 ({th_correct/20*100:5.1f}%) | Avg Spk/Img: {th_spikes/20:4.1f}")

        # Restore default threshold
        mmio.write(CFG_THRESHOLD, hw_threshold & 0xFFFF)
        print("=" * 65)
        print("Diagnostic Suite Complete.")

    except ImportError:
        print("Note: pynq library not found on this machine. Run this diagnostic directly on the PYNQ-Z2 board.")


if __name__ == '__main__':
    main()

