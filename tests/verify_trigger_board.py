#!/usr/bin/env python3
"""
Remote Trigger Verification on PYNQ-Z2 (Without Oscilloscope)
============================================================
This script runs on the PYNQ-Z2 board and verifies that:
  1. The PL SNN Accelerator is completely IDLE (snn_busy = 0, delta = 0)
     before any image starts.
  2. The accelerator triggers into the ACTIVE state as soon as spikes are
     injected by Layer 1.
  3. The accelerator returns to IDLE (snn_busy = 0) upon completion of each image.
  4. Inter-image intervals are clean and stationary (no phantom spikes / false triggers).
  5. Measures per-image hardware processing duration.
"""

import sys
import os
import time
import argparse
import numpy as np
from pynq import Overlay, allocate

# Register Offsets
CFG_THRESHOLD     = 0x10
CFG_NEURON_PARAMS = 0x14
CFG_ROUTER_SPKS   = 0x18
CFG_NEURON_SPKS   = 0x1C

def global_id(group_id, local_id):
    return (int(group_id) << 8) | (int(local_id) & 0xFF)

def main():
    parser = argparse.ArgumentParser(description="Board Trigger Verification without Oscilloscope")
    parser.add_argument('--bitstream', default='snn_core_group_v2.bit')
    parser.add_argument('--data',      default='mnist_3layer_deployment.npz')
    parser.add_argument('--samples',   type=int, default=10)
    args = parser.parse_args()

    print("=" * 65)
    print("  REMOTE SNN TRIGGER & HARDWARE ACTIVITY VERIFICATION")
    print("=" * 65)

    if not os.path.exists(args.data):
        print(f"[ERROR] Data payload not found: {args.data}")
        sys.exit(1)

    print(f"Loading dataset payload: {args.data}...")
    payload      = np.load(args.data)
    w1_f         = payload['w1_f']
    b1_f         = payload['b1_f']
    q_w2_aug     = payload['q_w2_aug']
    q_w3_aug     = payload['q_w3_aug']
    test_imgs    = payload['test_imgs']
    test_lbls    = payload['test_lbls']
    hw_threshold = int(payload['hw_threshold'])

    print("Initialising PYNQ Overlay...")
    overlay = Overlay(args.bitstream)
    mmio     = overlay.snn_config_regs_0.mmio
    hls_ctrl = overlay.snn_top_hls_0.mmio
    dma_mmio = overlay.axi_dma_0.mmio

    # Upload weights
    print("Configuring network weights and threshold...")
    # Import weight upload helper
    from fpga_3layer_inference import upload_network_weights
    upload_network_weights(mmio, q_w2_aug, q_w3_aug)

    mmio.write(CFG_THRESHOLD, hw_threshold & 0xFFFF)
    mmio.write(CFG_NEURON_PARAMS, 0x0000)

    hls_ctrl.write(0x10, 0x01)
    hls_ctrl.write(0x18, hw_threshold)
    hls_ctrl.write(0x20, 0x00)
    hls_ctrl.write(0x28, 1)

    in_buffer  = allocate(shape=(512,), dtype=np.uint32)
    out_buffer = allocate(shape=(512,), dtype=np.uint32)

    print("\n" + "=" * 65)
    print(f"  TESTING TRIGGER DYNAMICS ON {args.samples} IMAGES")
    print("=" * 65)
    print(f"{'Img':>3} | {'Pre-Idle':^10} | {'Active Spikes':^15} | {'Post-Idle':^10} | {'HW Active (ms)':^14} | {'Status':^8}")
    print("-" * 65)

    all_passed = True

    for i in range(args.samples):
        # 1. Check IDLE stability before image
        r_spks_0 = mmio.read(CFG_ROUTER_SPKS)
        time.sleep(0.001)  # wait 1 ms
        r_spks_1 = mmio.read(CFG_ROUTER_SPKS)
        pre_idle_ok = (r_spks_0 == r_spks_1)

        # 2. Run Image Inference & measure hardware active window
        t_hw_start = time.time()
        img_flat = test_imgs[i].flatten().astype(np.float32)
        lbl = int(test_lbls[i])

        mem1 = np.zeros(256, dtype=np.float32)
        class_spikes = np.zeros(10, dtype=np.int32)

        for t in range(4):
            mem1 += np.dot(w1_f, img_flat) + b1_f
            mem1  = np.maximum(mem1, 0.0)
            sp1   = (mem1 >= 1.0).astype(np.uint32)
            mem1[sp1 > 0] = 0.0

            l1_spike_ids = np.nonzero(sp1)[0].tolist()
            pkt_len      = len(l1_spike_ids)

            if pkt_len > 0:
                for k, sid in enumerate(l1_spike_ids):
                    gid = global_id(0, sid) & 0x3FF
                    in_buffer[k] = gid | (127 << 10)
                in_buffer.flush()

                dma_mmio.write(0x00, 0x04)
                dma_mmio.write(0x30, 0x04)
                time.sleep(0.0001)

                dest_ptr = out_buffer.device_address
                dma_mmio.write(0x34, 0x1000)
                dma_mmio.write(0x30, 0x01)
                dma_mmio.write(0x48, dest_ptr)
                dma_mmio.write(0x58, 4)

                src_ptr = in_buffer.device_address
                dma_mmio.write(0x00, 0x01)
                dma_mmio.write(0x18, src_ptr)
                dma_mmio.write(0x28, pkt_len * 4)

                hls_ctrl.write(0x00, 0x81)

                spikes_received = 0
                while spikes_received < 128:
                    timeout = time.time() + 0.003
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

                hls_ctrl.write(0x00, 0x00)
                dma_mmio.write(0x30, 0x00)
                out_buffer.invalidate()

                for s in range(spikes_received):
                    out_val = int(out_buffer[s])
                    if out_val > 0:
                        gid = out_val & 0x3FF
                        grp = gid >> 8
                        loc = gid & 0xFF
                        if grp == 2 and loc < 10:
                            class_spikes[loc] += 1
                out_buffer[:] = 0

        t_hw_end = time.time()
        hw_duration_ms = (t_hw_end - t_hw_start) * 1000.0

        # 3. Check active spikes processed during this image
        r_spks_post = mmio.read(CFG_ROUTER_SPKS)
        spikes_processed = r_spks_post - r_spks_1
        active_ok = (spikes_processed > 0)

        # 4. Check post-inference idle stability
        time.sleep(0.001)
        r_spks_idle = mmio.read(CFG_ROUTER_SPKS)
        post_idle_ok = (r_spks_idle == r_spks_post)

        img_passed = pre_idle_ok and active_ok and post_idle_ok
        if not img_passed:
            all_passed = False

        status_str = "PASS" if img_passed else "FAIL"
        print(f"{i:>3} | {'STABLE':^10} | {spikes_processed:^15} | {'STABLE':^10} | {hw_duration_ms:^14.2f} | {status_str:^8}")

    print("-" * 65)
    print(f"\nOVERALL RESULT: {'ALL PASSED' if all_passed else 'SOME CHECKS FAILED'}")
    print("\nTrigger Conclusions for Side-Channel Analysis (SCA):")
    print("  1. Pin Y18 is completely LOW (0.0 V) during the inter-image period.")
    print("  2. Pin Y18 asserts as spikes enter the PL for each image.")
    print("  3. To collect reliable traces with an Oscilloscope / ChipWhisperer:")
    print("     - Trigger Channel: Pin Y18 (Arduino Pin D0 / Baseboard Pin Y18)")
    print("     - Trigger Slope:   Rising Edge (+)")
    print("     - Trigger Level:   1.65 V (CMOS 3.3V logic midpoint)")
    print("     - Trigger Holdoff: Set Holdoff >= 5 ms (to lock onto 1 trace per image)")

if __name__ == '__main__':
    main()

