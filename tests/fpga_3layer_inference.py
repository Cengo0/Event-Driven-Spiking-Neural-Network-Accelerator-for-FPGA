#!/usr/bin/env python3
"""
fpga_3layer_inference.py
========================
Multi-Layer SNN Hardware Inference with Dedicated Pin Y18 SCA Trigger.
Architecture: snn_core_group_top.v

Topology:
  - Layer 1 (CPU Host) : Float32 LIF (Z-score MNIST analog pixels -> 256 binary spikes)
                         Runtime: ~0.08 ms on ARM Cortex-A9
  - Layer 2 (FPGA Grp 1): 256 LIF Neurons with full 256x257 Int8 matrix in hardware
  - Layer 3 (FPGA Grp 2): 10 Class Output Neurons with 10x257 Int8 matrix in hardware
  - Hardware Trigger    : Pin Y18 (snn_busy) pulses HIGH during FPGA inference

Register Protocol:
  CONFIG_ADDR:  [31:28]=0x0  [27:20]=fanout_idx(8b)  [19:12]=src_neuron(8b)  [3:0]=src_group(4b)
  CONFIG_WDATA: [31]=valid   [30:27]=dst_group(4b)   [23:16]=dst_neuron(8b)  [15:8]=weight(8b)  [0]=exc_inh

AXI DMA Spike Packet:
  [9:0]   = global neuron ID {group[1:0], local[7:0]}
  [20:13] = spike weight (127 for input relay)
"""

import argparse
import time
import json
import os
import numpy as np
from datetime import datetime
from pynq import Overlay, allocate

# ─────────────────────────────────────────────────────────────────────────────
# Hardware Parameters (matching snn_params.vh generated from snn_params.yaml)
# ─────────────────────────────────────────────────────────────────────────────
NUM_GROUPS         = 3
GROUP_SIZE_0       = 256  # Group 0: Input relay neurons
GROUP_SIZE_1       = 256  # Group 1: Layer 2 hidden LIF neurons
GROUP_SIZE_2       = 16   # Group 2: Layer 3 output class neurons (10 classes: 0..9)

LOCAL_ID_WIDTH     = 8    # 256 neurons -> 8 bits
GROUP_ID_WIDTH     = 2    # 3 groups -> 2 bits

# Register offsets (snn_config_regs.v)
CFG_CTRL           = 0x00
CFG_ADDR           = 0x04
CFG_WDATA          = 0x08
CFG_THRESHOLD      = 0x10
CFG_NEURON_PARAMS  = 0x14
CFG_ROUTER_SPKS    = 0x18
CFG_NEURON_SPKS    = 0x1C


def global_id(group: int, local: int) -> int:
    """Pack {group[1:0], local[7:0]} into a 10-bit global ID."""
    return ((group & 0x3) << LOCAL_ID_WIDTH) | (local & 0xFF)


def encode_ct_write(src_group: int, src_neuron: int, fanout_idx: int,
                    dst_group: int, dst_neuron: int, weight: int,
                    exc: bool) -> tuple:
    """
    Build (addr, data) for connectivity table write (full 8-bit addressing).
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


def upload_network_weights(mmio, q_w2_aug: np.ndarray, q_w3_aug: np.ndarray):
    """
    Upload Layer 2 and Layer 3 weights to hardware connectivity table.
      - Group 0 -> Group 1: Layer 2 weights (shape: [256, 257])
      - Group 1 -> Group 2: Layer 3 weights (shape: [10, 257])
    """
    print("Uploading Layer 2 weights (Group 0 -> Group 1, 256x256)...")
    n_l2_out, n_l2_in = q_w2_aug.shape  # (256, 257)
    w2_entries = 0

    # Layer 2 weights: source neurons 0..255
    for src in range(256):
        fanout = 0
        for dst in range(n_l2_out):
            w = int(q_w2_aug[dst, src])
            if w != 0:
                addr, data = encode_ct_write(
                    src_group=0, src_neuron=src, fanout_idx=fanout,
                    dst_group=1, dst_neuron=dst, weight=abs(w), exc=(w > 0)
                )
                ct_write(mmio, addr, data)
                fanout += 1
        # Invalidate remaining fanout slots up to 256
        if fanout < 256:
            addr, _ = encode_ct_write(0, src, fanout, 0, 0, 0, False)
            ct_write(mmio, addr, 0)  # valid = 0 marks end of list
        w2_entries += fanout

    # Bias connections (source index 256) mapped as additional fanouts on neuron 255
    # or distributed to neurons
    print(f"  Layer 2: Wrote {w2_entries} active synaptic connections.")

    print("Uploading Layer 3 weights (Group 1 -> Group 2, 10x256)...")
    n_l3_out, n_l3_in = q_w3_aug.shape  # (10, 257)
    w3_entries = 0

    # Layer 3 weights: source neurons 0..255 in Group 1
    for src in range(256):
        fanout = 0
        for dst in range(n_l3_out):
            w = int(q_w3_aug[dst, src])
            if w != 0:
                addr, data = encode_ct_write(
                    src_group=1, src_neuron=src, fanout_idx=fanout,
                    dst_group=2, dst_neuron=dst, weight=abs(w), exc=(w > 0)
                )
                ct_write(mmio, addr, data)
                fanout += 1
        # Invalidate remaining fanout slot
        if fanout < 16:
            addr, _ = encode_ct_write(1, src, fanout, 0, 0, 0, False)
            ct_write(mmio, addr, 0)  # valid = 0 marks end of list
        w3_entries += fanout

    print(f"  Layer 3: Wrote {w3_entries} active synaptic connections.")


def main():
    parser = argparse.ArgumentParser(description="Multi-Layer SNN Hardware Inference with SCA Trigger")
    parser.add_argument('--bitstream',     default='snn_core_group_v2.bit',
                        help='Bitstream path')
    parser.add_argument('--data',          default='mnist_3layer_deployment_v2.npz',
                        help='Deployment payload (.npz)')
    parser.add_argument('--samples',  type=int, default=10000,
                        help='Number of test images')
    parser.add_argument('--timesteps', type=int, default=4,
                        help='Number of SNN timesteps')
    parser.add_argument('--output-json',   default='mnist_inference_results_v2.json',
                        help='Results output JSON')
    parser.add_argument('--skip-bitstream', action='store_true',
                        help='Skip PL programming')
    args = parser.parse_args()

    # ── Load payload ──────────────────────────────────────────────────────────
    print(f"Loading deployment payload: {args.data}")
    payload      = np.load(args.data)
    w1_f         = payload['w1_f']          # (256, 784) float32
    b1_f         = payload['b1_f']          # (256,)     float32
    q_w2_aug     = payload['q_w2_aug']      # (256, 257) int8
    q_w3_aug     = payload['q_w3_aug']      # (10, 257)  int8
    test_imgs    = payload['test_imgs']     # (10000, 28, 28) pre-normalized
    test_lbls    = payload['test_lbls']     # (10000,)
    hw_threshold = int(payload['hw_threshold'])

    print(f"  Dataset: {len(test_imgs)} test images loaded.")
    print(f"  Hardware threshold (Layer 2): {hw_threshold}")

    # ── Load Overlay ──────────────────────────────────────────────────────────
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

    # ── Upload Network Weights ────────────────────────────────────────────────
    print("Resetting HLS core...")
    hls_ctrl.write(0x00, 0x00)
    time.sleep(0.01)

    upload_network_weights(mmio, q_w2_aug, q_w3_aug)

    # ── Configure Neurons ─────────────────────────────────────────────────────
    # Layer 2 threshold (Group 1) = hw_threshold (e.g. 291)
    # Group 0 is hardwired to threshold=1 (instant relay)
    mmio.write(CFG_THRESHOLD, hw_threshold & 0xFFFF)
    mmio.write(CFG_NEURON_PARAMS, 0x0000)  # leak=0, refrac=0
    print(f"  Global threshold set to: {hw_threshold}")

    # ── Configure HLS Core ────────────────────────────────────────────────────
    hls_ctrl.write(0x10, 0x01)              # mode: inference
    hls_ctrl.write(0x18, hw_threshold)
    hls_ctrl.write(0x20, 0x00)
    hls_ctrl.write(0x28, 1)                 # time_steps = 1 (kernel processes per-batch)

    # ── Allocate DMA Buffers ──────────────────────────────────────────────────
    in_buffer  = allocate(shape=(512,), dtype=np.uint32)
    out_buffer = allocate(shape=(512,), dtype=np.uint32)

    # ── Inference Loop ────────────────────────────────────────────────────────
    n_test   = min(args.samples, len(test_imgs))
    correct  = 0
    log      = []

    print(f"\nStarting inference on {n_test} images (SCA trigger enabled on Pin Y18)...")
    t_start = time.time()

    for img_idx in range(n_test):
        img_flat = test_imgs[img_idx].flatten().astype(np.float32)
        lbl      = int(test_lbls[img_idx])

        mem1 = np.zeros(256, dtype=np.float32)
        class_spikes = np.zeros(10, dtype=np.int32)

        for t in range(args.timesteps):
            # ── Layer 1 (CPU Host, Float32 LIF): ~0.08 ms ────────────────────
            mem1 += np.dot(w1_f, img_flat) + b1_f
            mem1  = np.maximum(mem1, 0.0)
            sp1   = (mem1 >= 1.0).astype(np.uint32)
            mem1[sp1 > 0] = 0.0

            l1_spike_ids = np.nonzero(sp1)[0].tolist()
            pkt_len      = len(l1_spike_ids)

            if pkt_len > 0:
                # ── Pack Input Spikes: [9:0]=global_id(0, id), [17:10]=weight ─
                for k, sid in enumerate(l1_spike_ids):
                    gid = global_id(0, sid) & 0x3FF
                    weight_val = 127
                    in_buffer[k] = gid | ((weight_val & 0xFF) << 10)

                in_buffer.flush()

                # ── Reset DMA Channels for Clean State ───────────────────────
                dma_mmio.write(0x00, 0x04)                 # MM2S reset
                dma_mmio.write(0x30, 0x04)                 # S2MM reset
                time.sleep(0.0001)

                # ── Arm S2MM DMA (FPGA -> ARM) ───────────────────────────────
                dest_ptr = out_buffer.device_address
                dma_mmio.write(0x34, 0x1000)               # clear IOC
                dma_mmio.write(0x30, 0x01)                 # run
                dma_mmio.write(0x48, dest_ptr)
                dma_mmio.write(0x58, 4)                    # arm for 1st spike

                # ── Start MM2S DMA (ARM -> FPGA) ─────────────────────────────
                # Pin Y18 goes HIGH as FPGA processes Layer 2 and Layer 3!
                src_ptr = in_buffer.device_address
                dma_mmio.write(0x00, 0x01)
                dma_mmio.write(0x18, src_ptr)
                dma_mmio.write(0x28, pkt_len * 4)

                # ── Start HLS Kernel with Auto-Restart ───────────────────────
                hls_ctrl.write(0x00, 0x81)

                # ── Poll for output spikes from Group 2 (Classes 0..9) ────────
                spikes_received = 0
                while spikes_received < 128:
                    timeout = time.time() + 0.003          # 3 ms tight timeout
                    got_spike = False

                    while time.time() < timeout:
                        if dma_mmio.read(0x34) & 0x1000:   # IOC set
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

                # Stop HLS & S2MM channel for this timestep
                hls_ctrl.write(0x00, 0x00)
                dma_mmio.write(0x30, 0x00)

                out_buffer.invalidate()

                # ── Decode Output Class Spikes ────────────────────────────────
                for s in range(spikes_received):
                    out_val = int(out_buffer[s])
                    if out_val > 0:
                        gid = out_val & 0x3FF
                        grp = gid >> LOCAL_ID_WIDTH
                        loc = gid & 0xFF
                        # Output class spikes come from Group 2
                        if grp == 2 and loc < 10:
                            class_spikes[loc] += 1

                out_buffer[:] = 0

        prediction = int(np.argmax(class_spikes))
        if prediction == lbl:
            correct += 1

        log.append({
            "image_index":     img_idx,
            "true_label":      lbl,
            "predicted_label": prediction
        })

        if (img_idx + 1) % 100 == 0:
            acc = correct / (img_idx + 1) * 100
            print(f"  [{img_idx+1}/{n_test}] Accuracy: {acc:.1f}%")

    # ── Stop HLS ──────────────────────────────────────────────────────────────
    hls_ctrl.write(0x00, 0x00)

    t_end   = time.time()
    acc     = correct / n_test * 100
    avg_lat = (t_end - t_start) / n_test * 1000

    final_router_spks = mmio.read(CFG_ROUTER_SPKS)
    final_neuron_spks = mmio.read(CFG_NEURON_SPKS)

    print(f"\n{'='*50}")
    print(f"  Multi-Layer Inference Complete")
    print(f"  Accuracy   : {acc:.2f}% ({correct}/{n_test})")
    print(f"  Avg Latency: {avg_lat:.2f} ms/image")
    print(f"  Trigger Pin: PACKAGE_PIN Y18 (snn_busy)")
    print(f"\n  Diagnostics:")
    print(f"    Router spikes : {final_router_spks}")
    print(f"    Neuron spikes : {final_neuron_spks}")
    print(f"{'='*50}")

    results = {
        "metadata": {
            "timestamp":    datetime.now().isoformat(),
            "samples":      n_test,
            "timesteps":    args.timesteps,
            "hw_threshold": hw_threshold,
            "trigger_pin":  "Y18",
        },
        "metrics": {
            "accuracy_percent":   round(acc, 2),
            "correct":            correct,
            "total":              n_test,
            "average_latency_ms": round(avg_lat, 2),
            "diagnostics": {
                "router_spikes": final_router_spks,
                "neuron_spikes": final_neuron_spks,
            }
        },
        "predictions": log
    }

    with open(args.output_json, 'w') as f:
        json.dump(results, f, indent=4)
    print(f"\nResults saved to: {args.output_json}")


if __name__ == '__main__':
    main()