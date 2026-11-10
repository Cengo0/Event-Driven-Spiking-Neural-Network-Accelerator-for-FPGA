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
import gc
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


def reset_hardware_state(hls_ctrl, mmio):
    """
    Fast Zero-State Hardware Reset between images (~0.3 ms):
      1. Pulses HLS reset (ctrl_reg=0x03) to assert hls_snn_reset into RTL,
         clearing Core Group input FIFOs, spike_flag_mem, and diagnostic counters.
      2. Sets 100% leak rate (0x0009 -> shift1=1, shift2=1) in CFG_NEURON_PARAMS.
      3. Runs HLS with snn_enable=1, reset=0 for 1600 cycles (>2 full 768-cycle sweeps
         across 256 neurons) so all BRAM membrane potentials in Group 1 and Group 2 decay to 0.
      4. Restores zero leak rate (0x0000) for inference.
    """
    hls_ctrl.write(0x10, 0x03)          # ctrl_reg: enable=1, reset=1
    hls_ctrl.write(0x28, 1)             # 1 step
    hls_ctrl.write(0x00, 0x01)          # ap_start
    t0 = time.time() + 0.010
    while time.time() < t0:
        if hls_ctrl.read(0x00) & 0x02:  # wait ap_done
            break

    mmio.write(CFG_NEURON_PARAMS, 0x0009) # shift1=1, shift2=1 -> 100% leak per sweep

    hls_ctrl.write(0x10, 0x01)          # ctrl_reg: enable=1, reset=0
    hls_ctrl.write(0x28, 1600)          # >2 full 768-cycle sweeps of 256-neuron BRAM
    hls_ctrl.write(0x00, 0x01)          # ap_start -> Core Groups zero BRAM!
    t0 = time.time() + 0.015
    while time.time() < t0:
        if hls_ctrl.read(0x00) & 0x02:  # wait ap_done
            break

    mmio.write(CFG_NEURON_PARAMS, 0x0000) # restore zero leak
    hls_ctrl.write(0x28, 1)
    hls_ctrl.write(0x00, 0x00)


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
    parser.add_argument('--output-spikes-csv', default=None,
                        help='Per-image all-layer temporal spike trace CSV output path (auto-named if omitted)')
    parser.add_argument('--output-spikes-parquet', default=None,
                        help='Optional Parquet output path for TVLA/plotting (if pandas/pyarrow installed)')
    parser.add_argument('--max-trace-images', type=int, default=None,
                        help='Max number of images to record full cycle-by-cycle spike traces for (default: all --samples)')
    parser.add_argument('--skip-bitstream', action='store_true',
                        help='Skip PL programming')
    parser.add_argument('--rate-coding',   action='store_true',
                        help='Use stochastic Poisson rate encoding at Layer 1 (matching rate_spikes training)')
    parser.add_argument('--reset-mode',    choices=['fast', 'none'], default='fast',
                        help='Hardware state reset between images: fast (100%% leak sweep, default) or none')
    args = parser.parse_args()

    if args.output_spikes_csv is None:
        if 'cifar' in args.data.lower() or 'cifar' in args.output_json.lower():
            args.output_spikes_csv = 'cifar10_fc3_spike_trace.csv'
        else:
            args.output_spikes_csv = 'mnist_fc3_spike_trace.csv'

    # ── Load payload (Memory-Optimized for PYNQ-Z2 512MB RAM) ─────────────────
    print(f"Loading deployment payload: {args.data}")
    payload      = np.load(args.data)
    w1_f         = np.array(payload['w1_f'], dtype=np.float32, copy=True)
    b1_f         = np.array(payload['b1_f'], dtype=np.float32, copy=True)
    q_w2_aug     = np.array(payload['q_w2_aug'], copy=True)
    q_w3_aug     = np.array(payload['q_w3_aug'], copy=True)
    test_lbls_full = np.array(payload['test_lbls'], copy=True)
    n_test       = min(args.samples, len(test_lbls_full))
    test_lbls    = test_lbls_full[:n_test]
    del test_lbls_full
    hw_threshold = int(payload['hw_threshold'])
    test_imgs    = np.array(payload['test_imgs'][:n_test], dtype=np.float32, copy=True)
    payload.close()
    del payload
    gc.collect()

    print(f"  Dataset: {n_test} test images loaded, shape: {test_imgs.shape}")
    print(f"  Hardware threshold (Reg 0x10): {hw_threshold}")

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
    # Layer 2 (Group 1) & Layer 3 (Group 2) threshold = hw_threshold
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
    MAX_SPIKES_PER_STEP = 4096
    in_buffer  = allocate(shape=(512,), dtype=np.uint32)
    out_buffer = allocate(shape=(MAX_SPIKES_PER_STEP,), dtype=np.uint32)
    out_buffer[:] = 0
    out_buffer.flush()

    # ── Inference Loop ────────────────────────────────────────────────────────
    max_trace_imgs = n_test if args.max_trace_images is None else min(args.max_trace_images, n_test)
    correct  = 0
    total_l1_spikes = 0
    total_l2_spikes = 0
    total_l3_spikes = 0
    total_logged_spikes = 0
    latencies_ms = []
    log      = []

    csv_dir = os.path.dirname(args.output_spikes_csv)
    if csv_dir:
        os.makedirs(csv_dir, exist_ok=True)
    csv_file = open(args.output_spikes_csv, 'w', buffering=65536)
    csv_file.write(
        "image_id,true_label,predicted_label,timestep,spike_order,"
        "clock_cycle,timestep_cycle,hls_timestamp,layer,group_id,"
        "local_neuron_id,layer_neuron_id,global_neuron_id\n"
    )

    print(f"\nStarting inference on {n_test} images (SCA trigger enabled on Pin Y18, reset_mode={args.reset_mode})...")
    t_start = time.time()

    try:
        for img_idx in range(n_test):
            img_flat = test_imgs[img_idx].reshape(-1).astype(np.float32)
            lbl      = int(test_lbls[img_idx])

            if args.reset_mode == 'fast':
                reset_hardware_state(hls_ctrl, mmio)

            mem1 = np.zeros(256, dtype=np.float32)
            class_spikes = np.zeros(10, dtype=np.int32)
            l1_spk_count = 0
            l2_spk_count = 0
            image_spike_events = []
            step_pkt_slices = []
            spike_order = 0
            cumulative_cycle_offset = 0
            t0 = time.time()

            for t in range(args.timesteps):
                # ── Layer 1 (CPU Host, Float32 LIF): ~0.08 ms ─────────────────
                if args.rate_coding:
                    # Stochastic Poisson/Bernoulli rate spikes matching training
                    in_val = (np.random.rand(*img_flat.shape) < img_flat).astype(np.float32)
                else:
                    in_val = img_flat

                mem1 += np.dot(w1_f, in_val) + b1_f
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

                    # ── Reset DMA Channels for Clean State ────────────────────
                    dma_mmio.write(0x00, 0x04)                 # MM2S reset
                    dma_mmio.write(0x30, 0x04)                 # S2MM reset
                    t_rst_wait = time.time() + 0.005
                    while (dma_mmio.read(0x00) & 0x04 or dma_mmio.read(0x30) & 0x04) and time.time() < t_rst_wait:
                        pass

                    # ── Arm S2MM DMA (FPGA -> ARM) for Single-Burst Transfer ──
                    dest_ptr = out_buffer.device_address
                    dma_mmio.write(0x34, 0x1000)               # clear IOC
                    dma_mmio.write(0x30, 0x01)                 # run
                    dma_mmio.write(0x48, dest_ptr)
                    dma_mmio.write(0x58, MAX_SPIKES_PER_STEP * 4)

                    # ── Start MM2S DMA (ARM -> FPGA) ──────────────────────────
                    # Pin Y18 goes HIGH as FPGA processes Layer 1 -> Layer 2 -> Layer 3!
                    src_ptr = in_buffer.device_address
                    dma_mmio.write(0x04, 0x1000)               # clear MM2S IOC
                    dma_mmio.write(0x00, 0x01)
                    dma_mmio.write(0x18, src_ptr)
                    dma_mmio.write(0x28, pkt_len * 4)

                    # ── Start HLS Kernel with Auto-Restart ────────────────────
                    hls_ctrl.write(0x00, 0x81)

                    # ── Wait for Single-Burst S2MM End-of-Timestep EoP (0xFFFFFFFF, TLAST=1) ─
                    spikes_received = 0
                    burst_eop_done = False
                    mm2s_done = False
                    quiet_deadline = None
                    t_abort = time.time() + 0.500              # 500ms hard safety timeout
                    dma_arr = getattr(dma_mmio, 'array', None)

                    while time.time() < t_abort:
                        s2mm_ioc = (dma_arr[13] & 0x1000) if dma_arr is not None else (dma_mmio.read(0x34) & 0x1000)
                        if s2mm_ioc:
                            if dma_arr is not None:
                                dma_arr[13] = 0x1000
                            else:
                                dma_mmio.write(0x34, 0x1000)

                            if spikes_received == 0:
                                out_buffer.invalidate()
                                eop_matches = np.flatnonzero(out_buffer == 0xFFFFFFFF)
                                if len(eop_matches) > 0:
                                    spikes_received = int(eop_matches[0])
                                    burst_eop_done = True
                                    break

                            # Legacy per-spike TLAST=1 fallback
                            if spikes_received < MAX_SPIKES_PER_STEP:
                                spikes_received += 1
                                if spikes_received < MAX_SPIKES_PER_STEP:
                                    if dma_arr is not None:
                                        dma_arr[18] = dest_ptr + (spikes_received << 2)
                                        dma_arr[22] = 4
                                    else:
                                        dma_mmio.write(0x30, 0x01)
                                        dma_mmio.write(0x48, dest_ptr + (spikes_received << 2))
                                        dma_mmio.write(0x58, 4)
                            if mm2s_done:
                                quiet_deadline = time.time() + 0.005

                        if not mm2s_done:
                            mm2s_sr = dma_arr[1] if dma_arr is not None else dma_mmio.read(0x04)
                            if (mm2s_sr & 0x1000) or (mm2s_sr & 0x0002):
                                mm2s_done = True
                                quiet_deadline = time.time() + 0.050  # 50ms fallback (burst EoP exits early via s2mm_ioc)
                        else:
                            if quiet_deadline is not None and time.time() >= quiet_deadline:
                                break

                    # Stop HLS & S2MM channel for this timestep
                    hls_ctrl.write(0x00, 0x00)
                    dma_mmio.write(0x30, 0x00)

                    if not burst_eop_done:
                        out_buffer.invalidate()
                        if spikes_received == 0:
                            eop_matches = np.flatnonzero(out_buffer == 0xFFFFFFFF)
                            if len(eop_matches) > 0:
                                spikes_received = int(eop_matches[0])

                    step_pkt_slices.append((t, out_buffer[:spikes_received].tolist()))
                    clear_n = min(MAX_SPIKES_PER_STEP, spikes_received + 2)
                    out_buffer[:clear_n] = 0
                    out_buffer.flush()
                else:
                    step_pkt_slices.append((t, []))

            t1 = time.time()
            lat_ms = (t1 - t0) * 1000.0
            latencies_ms.append(lat_ms)

            # ── Decode All-Layer Spikes (Group 0 = Layer 1, Group 1 = Layer 2, Group 2 = Layer 3) ─
            for t, step_pkts in step_pkt_slices:
                prev_rtl_lsb = None
                rtl_wrap_offset = 0
                max_step_cycle = 0

                for pkt in step_pkts:
                    if pkt == 0 or pkt == 0xFFFFFFFF:
                        continue
                    gid = pkt & 0x3FF
                    grp = (gid >> LOCAL_ID_WIDTH) & 0x3
                    loc = gid & 0xFF
                    rtl_lsb = (pkt >> 10) & 0xFF
                    hls_ts  = (pkt >> 18) & 0x3FFF

                    if prev_rtl_lsb is not None and rtl_lsb < prev_rtl_lsb:
                        rtl_wrap_offset += 256
                    prev_rtl_lsb = rtl_lsb

                    timestep_cycle = (rtl_wrap_offset + rtl_lsb) if (rtl_wrap_offset > 0 or rtl_lsb != 1) else hls_ts
                    if timestep_cycle > max_step_cycle:
                        max_step_cycle = timestep_cycle
                    clock_cycle = cumulative_cycle_offset + timestep_cycle

                    if grp == 0:
                        l1_spk_count += 1
                        layer = 1
                        layer_nid = loc
                        global_nid = loc
                    elif grp == 1:
                        l2_spk_count += 1
                        layer = 2
                        layer_nid = loc
                        global_nid = GROUP_SIZE_0 + loc
                    elif grp == 2 and loc < 10:
                        class_spikes[loc] += 1
                        layer = 3
                        layer_nid = loc
                        global_nid = GROUP_SIZE_0 + GROUP_SIZE_1 + loc
                    else:
                        continue

                    if img_idx < max_trace_imgs:
                        image_spike_events.append((
                            t, spike_order, clock_cycle, timestep_cycle, hls_ts,
                            layer, grp, loc, layer_nid, global_nid
                        ))
                    spike_order += 1

                cumulative_cycle_offset += max(max_step_cycle + 100, 1000)
            del step_pkt_slices

            prediction = int(np.argmax(class_spikes))
            if prediction == lbl:
                correct += 1

            curr_r_spks = int(mmio.read(CFG_ROUTER_SPKS))
            curr_n_spks = int(mmio.read(CFG_NEURON_SPKS))

            total_l1_spikes += l1_spk_count
            total_l2_spikes += l2_spk_count
            total_l3_spikes += int(np.sum(class_spikes))

            if img_idx < max_trace_imgs and len(image_spike_events) > 0:
                lines = [
                    f"{img_idx},{lbl},{prediction},{ev[0]},{ev[1]},{ev[2]},{ev[3]},{ev[4]},{ev[5]},{ev[6]},{ev[7]},{ev[8]},{ev[9]}\n"
                    for ev in image_spike_events
                ]
                csv_file.writelines(lines)
                total_logged_spikes += len(lines)
                del lines
            del image_spike_events

            log.append({
                "image_index":     img_idx,
                "true_label":      lbl,
                "predicted_label": prediction,
                "spikes":          class_spikes.tolist(),
                "l1_spikes":       l1_spk_count,
                "l2_spikes":       l2_spk_count,
                "router_spikes":   curr_r_spks,
                "neuron_spikes":   curr_n_spks,
                "latency_ms":      round(lat_ms, 2)
            })

            if (img_idx + 1) % 100 == 0 or (img_idx + 1) == n_test:
                acc = correct / (img_idx + 1) * 100
                mean_lat = float(np.mean(latencies_ms))
                print(f"  [{img_idx+1:5d}/{n_test}] Acc: {acc:.2f}% | "
                      f"Latency: {mean_lat:.2f} ms | "
                      f"L1: {l1_spk_count} | L2: {l2_spk_count} | L3: {class_spikes.tolist()}")
    finally:
        hls_ctrl.write(0x00, 0x00)
        try:
            csv_file.flush()
            csv_file.close()
        except Exception:
            pass
        try:
            in_buffer.freebuffer()
            out_buffer.freebuffer()
        except Exception:
            pass

    t_end   = time.time()
    acc     = correct / n_test * 100
    avg_lat = float(np.mean(latencies_ms)) if latencies_ms else ((t_end - t_start) / n_test * 1000)
    avg_l1  = total_l1_spikes / n_test
    avg_l2  = total_l2_spikes / n_test
    avg_l3  = total_l3_spikes / n_test

    if args.reset_mode == 'fast':
        final_router_spks = sum(entry["router_spikes"] for entry in log)
        final_neuron_spks = sum(entry["neuron_spikes"] for entry in log)
    else:
        final_router_spks = int(mmio.read(CFG_ROUTER_SPKS))
        final_neuron_spks = int(mmio.read(CFG_NEURON_SPKS))

    print(f"Saved cycle-accurate 3-layer spike trace CSV ({total_logged_spikes} spikes) to: {args.output_spikes_csv}")

    if args.output_spikes_parquet:
        try:
            import pandas as pd
            df_spikes = pd.read_csv(args.output_spikes_csv)
            df_spikes.to_parquet(args.output_spikes_parquet, index=False)
            print(f"Saved spike trace Parquet to: {args.output_spikes_parquet}")
            del df_spikes
            gc.collect()
        except Exception as e:
            print(f"Note: Parquet export skipped ({e}); CSV trace is complete.")

    print(f"\n{'='*60}")
    print(f"  Multi-Layer Inference Complete")
    print(f"  Accuracy        : {acc:.2f}% ({correct}/{n_test})")
    print(f"  Avg Latency     : {avg_lat:.2f} ms/image")
    print(f"  Avg L1 Spikes   : {avg_l1:.2f} / image (Group 0)")
    print(f"  Avg L2 Spikes   : {avg_l2:.2f} / image (Group 1)")
    print(f"  Avg L3 Spikes   : {avg_l3:.2f} / image (Group 2)")
    print(f"  Trigger Pin     : PACKAGE_PIN Y18 (snn_busy)")
    print(f"\n  Diagnostics:")
    print(f"    Router spikes : {final_router_spks}")
    print(f"    Neuron spikes : {final_neuron_spks}")
    print(f"{'='*60}")

    results = {
        "metadata": {
            "timestamp":    datetime.now().isoformat(),
            "data":         args.data,
            "samples":      n_test,
            "timesteps":    args.timesteps,
            "hw_threshold": hw_threshold,
            "rate_coding":  args.rate_coding,
            "reset_mode":   args.reset_mode,
            "trigger_pin":  "Y18",
        },
        "metrics": {
            "accuracy_percent":          round(acc, 2),
            "correct":                   correct,
            "total":                     n_test,
            "average_latency_ms":        round(avg_lat, 2),
            "avg_l1_spikes_per_image":   round(avg_l1, 2),
            "avg_l2_spikes_per_image":   round(avg_l2, 2),
            "avg_spikes_per_image":      round(avg_l3, 2),
            "total_logged_spike_events": total_logged_spikes,
            "spike_trace_csv":           args.output_spikes_csv,
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