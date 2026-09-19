#!/usr/bin/env python3
"""
fpga_3layer_inference.py
========================
3-Layer SNN Co-Processing Inference on PYNQ-Z2 board.
Architecture: snn_core_group_top.v (5 groups × 128 neurons = 640 total)

Co-processing model:
  Layer 1 (CPU)  : float32 LIF, processes Z-score-normalised MNIST pixels
  Layer 2 (FPGA) : Int8 synaptic integration in 5 × 128-neuron core groups
  Layer 3 (CPU)  : int32 voltage accumulator → argmax → class prediction

Hardware parameters (from config/generated/snn_params.vh):
  NUM_GROUPS       = 5
  NEURONS_PER_GROUP = 128
  TOTAL_NEURONS    = 640   (only first 256 used for L2)
  GROUP_ID_WIDTH   = 3 bits
  LOCAL_ID_WIDTH   = 7 bits
  GLOBAL_ID_WIDTH  = 10 bits
  MAX_FANOUT_INTER = 16
  FANOUT_IDX_WIDTH = 4 bits

Address map (from rebuild_integrated.tcl):
  0x43C00000  snn_top_hls_0      (HLS control)
  0x43C10000  snn_config_regs_0  (RTL config/status)
  0x41E00000  axi_dma_0          (spike DMA)

snn_config_regs register map (snn_config_regs.v):
  0x00  CONFIG_CTRL   [W]  [1:0] target (0=router, 1=neuron)
  0x04  CONFIG_ADDR   [W]  [31:0] address
  0x08  CONFIG_WDATA  [W]  [31:0] data (triggers config_we on write)
  0x10  THRESHOLD     [RW] [15:0]
  0x14  NEURON_PARAMS [RW] [7:0]=leak_rate, [15:8]=refrac_period
  0x18  ROUTER_SPIKE_CNT [R]
  0x1C  NEURON_SPIKE_CNT [R]

Connectivity-table write format (snn_core_group_top.v lines 308-319):
  CONFIG_ADDR:  [31:28]=cmd(0x0)  [3:0]=src_group
  CONFIG_WDATA: [31]=valid  [30:27]=dst_group(4b)  [26:20]=dst_neuron(7b)
                [19:12]=weight(8b)  [11]=exc_inh  [10:7]=fanout_idx(4b)
                [6:0]=src_neuron(7b)

AXI-Stream DMA spike packet (32-bit word):
  [9:0]  = global neuron ID  {group_id[2:0], local_id[6:0]}
  [31:10] = reserved / 0
  (The HLS IP reads this and dispatches via event_router_ng.ext_spike_valid)
"""

import argparse
import time
import json
import os
import numpy as np
from datetime import datetime
from pynq import Overlay, allocate

# ─────────────────────────────────────────────────────────────────────────────
# Hardware Constants (must match snn_params.vh)
# ─────────────────────────────────────────────────────────────────────────────
NUM_GROUPS         = 5
NEURONS_PER_GROUP  = 128
TOTAL_NEURONS      = NUM_GROUPS * NEURONS_PER_GROUP   # 640
GROUP_ID_WIDTH     = 3    # ceil(log2(NUM_GROUPS=5)) → 3 bits
LOCAL_ID_WIDTH     = 7    # ceil(log2(NEURONS_PER_GROUP=128)) → 7 bits
GLOBAL_ID_WIDTH    = GROUP_ID_WIDTH + LOCAL_ID_WIDTH  # 10 bits
MAX_FANOUT_INTER   = 16
FANOUT_IDX_WIDTH   = 4    # ceil(log2(MAX_FANOUT_INTER=16)) → 4 bits

# Layer 2 operates on the first 256 neurons (groups 0 and 1, 128 each)
L2_NEURONS         = 256
L2_GROUPS          = L2_NEURONS // NEURONS_PER_GROUP  # 2 groups (0 and 1)

# snn_config_regs offsets
CFG_CTRL           = 0x00
CFG_ADDR           = 0x04
CFG_WDATA          = 0x08
CFG_THRESHOLD      = 0x10
CFG_NEURON_PARAMS  = 0x14
CFG_ROUTER_SPKS    = 0x18
CFG_NEURON_SPKS    = 0x1C


# ─────────────────────────────────────────────────────────────────────────────
# Helper: make global neuron ID from group + local id
# ─────────────────────────────────────────────────────────────────────────────
def global_id(group: int, local: int) -> int:
    """Pack {group_id[2:0], local_id[6:0]} into a 10-bit global neuron ID."""
    return ((group & 0x7) << LOCAL_ID_WIDTH) | (local & 0x7F)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: encode one connectivity-table write
# ─────────────────────────────────────────────────────────────────────────────
def encode_ct_write(src_group: int, src_neuron: int, fanout_idx: int,
                    dst_group: int, dst_neuron: int, weight: int,
                    exc: bool) -> tuple:
    """
    Build (addr, data) for a snn_config_regs connectivity-table write.

    CONFIG_ADDR  [31:28]=0x0 (cmd=router write)  [3:0]=src_group
    CONFIG_WDATA [31]=valid  [30:27]=dst_group  [26:20]=dst_neuron
                 [19:12]=weight  [11]=exc_inh  [10:7]=fanout_idx  [6:0]=src_neuron
    """
    addr = (0x0 << 28) | (src_group & 0xF)

    data  = (1        << 31)                         # valid
    data |= ((dst_group  & 0xF)  << 27)              # [30:27]
    data |= ((dst_neuron & 0x7F) << 20)              # [26:20]
    data |= ((weight     & 0xFF) << 12)              # [19:12]
    data |= ((1 if exc else 0)   << 11)              # [11]
    data |= ((fanout_idx & 0xF)  << 7)               # [10:7]
    data |= (src_neuron  & 0x7F)                     # [6:0]

    return addr, data


# ─────────────────────────────────────────────────────────────────────────────
# Write connectivity-table entry via snn_config_regs
# ─────────────────────────────────────────────────────────────────────────────
def ct_write(mmio, addr: int, data: int):
    """Write one row of the synaptic connectivity table via AXI-Lite."""
    mmio.write(CFG_CTRL,  0)      # target = router (connectivity table)
    mmio.write(CFG_ADDR,  addr)
    mmio.write(CFG_WDATA, data)   # triggers config_we_pulse internally


# ─────────────────────────────────────────────────────────────────────────────
# Clear the entire connectivity table
# ─────────────────────────────────────────────────────────────────────────────
def clear_connectivity_table(mmio):
    """
    Invalidate all entries in the connectivity table (clear valid bit).
    Table size: NUM_GROUPS × NEURONS_PER_GROUP × MAX_FANOUT_INTER
    = 5 × 128 × 16 = 10,240 entries.
    Only need to clear entries we will actually use (src groups 0..L2_GROUPS-1).
    """
    print("Clearing connectivity table...")
    invalid_data = 0  # valid=0, everything else 0
    for sg in range(L2_GROUPS):
        for sn in range(NEURONS_PER_GROUP):
            for fi in range(MAX_FANOUT_INTER):
                addr = (0x0 << 28) | (sg & 0xF)
                # Build invalidation word: valid=0, all else 0, except positioning
                data  = (0        << 31)
                data |= (0        << 27)
                data |= (0        << 20)
                data |= (0        << 12)
                data |= (0        << 11)
                data |= ((fi & 0xF) << 7)
                data |= (sn & 0x7F)
                ct_write(mmio, addr, data)


# ─────────────────────────────────────────────────────────────────────────────
# Upload Layer-2 weight matrix to the synaptic connectivity table
# ─────────────────────────────────────────────────────────────────────────────
def upload_weights_to_fpga(mmio, q_w2_aug: np.ndarray, prune_th: int = 0) -> float:
    """
    Write q_w2_aug (shape: [256 outputs, 257 inputs]) into the hardware
    synaptic connectivity table.

    Mapping:
      - Rows 0..255  = real input neurons  (L1 spikes from CPU)
        These are spread across groups 0 and 1 (128 each):
          input  0..127 → src_group=0, src_neuron=0..127
          input 128..255 → src_group=1, src_neuron=0..127
      - Row 256       = bias neuron (always-on, virtual slot in group 1)
        We place the bias neuron at src_group=1, src_neuron=127 (last slot).
        Since real input 255 is already at src_group=1, src_neuron=127, we
        use src_group=1, src_neuron=127 for BOTH — but add the bias weight
        as an additional fanout entry after all real connections.
        A cleaner approach: map bias to group 0, src_neuron=127 (same as
        input neuron 127). Instead, we designate a dedicated "bias" slot:
        we put bias at group 1, src_neuron=127 as fanout entries at higher
        fanout_idx slots (after real weight fanouts for that src neuron).

        Simplest correct approach: map the 257 inputs to src slots as follows:
          inputs  0..127 → (group=0, neuron=0..127)
          inputs 128..255 → (group=1, neuron=0..127)
          input  256 (bias) → send from both groups at a dedicated
                               "bias" fanout slot we append.

    Destination neurons:
      - Outputs 0..127 → dst_group=2, dst_neuron=0..127
      - Outputs 128..255 → dst_group=3, dst_neuron=0..127

    NOTE: MAX_FANOUT_INTER = 16, so each source neuron can drive at most
    16 destination neurons. This means we MUST prune aggressively to fit.

    Returns: the actual prune threshold applied.
    """
    n_outputs, n_inputs = q_w2_aug.shape   # (256, 257)
    assert n_outputs == L2_NEURONS and n_inputs == L2_NEURONS + 1, \
        f"Expected ({L2_NEURONS},{L2_NEURONS+1}), got {q_w2_aug.shape}"

    # ── Auto-prune to respect MAX_FANOUT_INTER = 16 ──────────────────────────
    w = q_w2_aug.copy()
    effective_prune_th = prune_th
    while True:
        if effective_prune_th > 0:
            w = q_w2_aug.copy()
            w[np.abs(w) <= effective_prune_th] = 0

        # Count max fanout across all source neurons
        max_fanout = 0
        for src in range(n_inputs):
            non_zero = int(np.count_nonzero(w[:, src]))
            if non_zero > max_fanout:
                max_fanout = non_zero

        if max_fanout <= MAX_FANOUT_INTER:
            break
        effective_prune_th += 1

    total_conns = int(np.count_nonzero(w))
    print(f"  Prune threshold applied: |w| <= {effective_prune_th}")
    print(f"  Total active connections: {total_conns}")

    # ── Write connectivity table entries ──────────────────────────────────────
    # Input → source group/neuron mapping
    def src_from_input(inp_idx):
        """Map input index 0..256 → (src_group, src_neuron)."""
        if inp_idx < 128:
            return 0, inp_idx
        elif inp_idx < 256:
            return 1, inp_idx - 128
        else:  # inp_idx == 256: bias neuron
            # Place bias neuron at a dedicated slot: group=0, src_neuron=127
            # with fanout_idx continuing after real connections for that neuron.
            # (see below — bias fanouts are appended after regular ones)
            return 0, 127  # Shared slot; bias entries go after real connections

    # Output → destination group/neuron mapping
    def dst_from_output(out_idx):
        """Map output index 0..255 → (dst_group, dst_neuron)."""
        if out_idx < 128:
            return 2, out_idx
        else:
            return 3, out_idx - 128

    # Build per-source connection lists
    # Key: (src_group, src_neuron)
    # Value: list of (dst_group, dst_neuron, weight, exc)
    conns = {}
    for src in range(n_inputs - 1):  # inputs 0..255
        sg, sn = src_from_input(src)
        for dst in range(n_outputs):
            weight_val = int(w[dst, src])
            if weight_val == 0:
                continue
            dg, dn = dst_from_output(dst)
            key = (sg, sn)
            if key not in conns:
                conns[key] = []
            conns[key].append((dg, dn, abs(weight_val), weight_val > 0))

    # Append bias connections for input index 256 to the shared slot (0, 127)
    # after any real connections for that source neuron
    bias_key = (0, 127)
    if bias_key not in conns:
        conns[bias_key] = []
    for dst in range(n_outputs):
        weight_val = int(w[dst, 256])
        if weight_val == 0:
            continue
        dg, dn = dst_from_output(dst)
        conns[bias_key].append((dg, dn, abs(weight_val), weight_val > 0))

    # Now write to hardware, capping at MAX_FANOUT_INTER per source
    entries_written = 0
    for (sg, sn), dest_list in conns.items():
        # Truncate to MAX_FANOUT_INTER (pruning already handled above)
        dest_list = dest_list[:MAX_FANOUT_INTER]
        for fi, (dg, dn, wabs, exc) in enumerate(dest_list):
            addr, data = encode_ct_write(sg, sn, fi, dg, dn, wabs, exc)
            ct_write(mmio, addr, data)
            entries_written += 1

    print(f"  Wrote {entries_written} connectivity table entries.")
    return effective_prune_th


# ─────────────────────────────────────────────────────────────────────────────
# Main inference loop
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="3-Layer SNN FPGA Inference")
    parser.add_argument('--bitstream',     default='snn_core_group_v2.bit',
                        help='Path to bitstream (.bit file)')
    parser.add_argument('--data',          default='mnist_3layer_deployment.npz',
                        help='Deployment payload (.npz file)')
    parser.add_argument('--samples',  type=int, default=1000,
                        help='Number of MNIST images to test')
    parser.add_argument('--skip-bitstream', action='store_true',
                        help='Skip PL programming (use existing overlay)')
    parser.add_argument('--output-json',   default='inference_results.json',
                        help='Path for results JSON output')
    parser.add_argument('--prune-th', type=int, default=0,
                        help='Manual prune threshold override (0 = auto)')
    parser.add_argument('--timesteps', type=int, default=4,
                        help='Number of SNN timesteps per image')
    args = parser.parse_args()

    # ── Load deployment payload ───────────────────────────────────────────────
    print(f"Loading deployment payload: {args.data}")
    payload       = np.load(args.data)
    w1_f          = payload['w1_f']          # (256, 784)  float32
    b1_f          = payload['b1_f']          # (256,)      float32
    q_w2_aug      = payload['q_w2_aug'].copy()  # (256, 257)  int8  — copy for in-place prune
    q_w3_aug      = payload['q_w3_aug']      # (10, 257)   int8
    test_imgs     = payload['test_imgs']     # (10000, 28, 28) float32, already Z-score normalised
    test_lbls     = payload['test_lbls']     # (10000,)    int64
    hw_threshold  = int(payload['hw_threshold'])
    print(f"  Loaded {len(test_imgs)} images. Hardware threshold from payload: {hw_threshold}")

    # ── Initialise PYNQ overlay ───────────────────────────────────────────────
    print("Initialising PYNQ Overlay...")
    if not args.skip_bitstream and os.path.exists(args.bitstream):
        overlay = Overlay(args.bitstream)
        print(f"  Programmed PL with: {args.bitstream}")
    else:
        overlay = Overlay(args.bitstream, download=False)
        print("  Skipped PL programming (using existing overlay).")

    # Peripheral handles
    mmio      = overlay.snn_config_regs_0.mmio   # RTL config regs at 0x43C10000
    hls_ctrl  = overlay.snn_top_hls_0.mmio       # HLS AP control  at 0x43C00000
    dma_mmio  = overlay.axi_dma_0.mmio           # Spike DMA       at 0x41E00000

    # ── Reset + disable neuron array before weight upload ─────────────────────
    print("Resetting HLS core...")
    hls_ctrl.write(0x00, 0x00)    # ap_ctrl: stop
    time.sleep(0.02)

    # ── Upload Layer-2 weights to connectivity table ──────────────────────────
    print("Uploading Layer-2 weights to hardware connectivity table...")
    clear_connectivity_table(mmio)
    applied_prune_th = upload_weights_to_fpga(mmio, q_w2_aug,
                                              prune_th=args.prune_th)

    # ── Configure neuron parameters ───────────────────────────────────────────
    # Threshold: the hardware RTL uses cfg_global_threshold (16-bit)
    # We write directly to THRESHOLD register (offset 0x10) in snn_config_regs
    mmio.write(CFG_THRESHOLD,     hw_threshold & 0xFFFF)
    # Leak rate = 0 (no leak), refrac = 0 (no refractory period)
    # NEURON_PARAMS [7:0]=leak_rate, [15:8]=refrac_period
    mmio.write(CFG_NEURON_PARAMS, 0x0000)
    print(f"  Global threshold set to: {hw_threshold}")
    print(f"  Leak rate=0, Refrac=0")

    # ── Start HLS AP engine in inference mode ─────────────────────────────────
    # mode register 0x10 in HLS: bit0=load_weights, bit2=reset_state
    hls_ctrl.write(0x10, 0x04)    # reset internal state
    hls_ctrl.write(0x00, 0x01)    # ap_start
    # Wait for ap_idle or ap_done (bits [2:1])
    timeout = time.time() + 0.5
    while (hls_ctrl.read(0x00) & 0x06) == 0 and time.time() < timeout:
        pass
    hls_ctrl.write(0x00, 0x00)    # ap_stop

    # Enable inference mode (bit0) and set threshold in HLS registers
    hls_ctrl.write(0x10, 0x01)              # mode: inference
    hls_ctrl.write(0x18, hw_threshold)      # HLS-side threshold register
    hls_ctrl.write(0x20, 0x00)             # time-step counter reset
    hls_ctrl.write(0x28, args.timesteps)   # number of timesteps

    # Start HLS for continuous stream operation
    hls_ctrl.write(0x00, 0x81)             # ap_start | ap_continue

    # ── Allocate DMA buffers ──────────────────────────────────────────────────
    # Input: worst case = all 257 inputs fire, each encoded as 1 word
    in_buffer  = allocate(shape=(512,),  dtype=np.uint32)
    # Output: worst case = 256 output neurons fire, each sends 1 word
    out_buffer = allocate(shape=(512,),  dtype=np.uint32)

    # ── Main inference loop ───────────────────────────────────────────────────
    correct  = 0
    n_test   = min(args.samples, len(test_imgs))
    log      = []
    print(f"\nStarting inference on {n_test} images ({args.timesteps} timesteps each)...")
    t_start  = time.time()

    for img_idx in range(n_test):
        print(f"Processing image {img_idx}")
        # ── Layer 1: CPU float32 LIF ─────────────────────────────────────────
        # test_imgs is ALREADY Z-score normalised by prepare_3layer_deployment.py
        # (transforms.Normalize((0.1307,), (0.3081,))). Do NOT re-normalise.
        img_flat = test_imgs[img_idx].flatten().astype(np.float32)  # (784,)
        lbl      = int(test_lbls[img_idx])

        mem1 = np.zeros(256, dtype=np.float32)
        mem3 = np.zeros(10,  dtype=np.int32)

        for t in range(args.timesteps):
            # ── L1: Float LIF step ──────────────────────────────────────────
            mem1  += np.dot(w1_f, img_flat) + b1_f
            mem1   = np.maximum(mem1, 0.0)
            spike1 = (mem1 >= 1.0).astype(np.float32)
            mem1[spike1 > 0] = 0.0

            # Collect spiking L1 neuron indices + bias neuron (index 256)
            l1_spike_ids = np.nonzero(spike1)[0].tolist()
            l1_spike_ids.append(256)   # always-on bias neuron

            # ── Convert L1 spikes to global neuron IDs for the FPGA ──────────
            # Mapping (must match upload_weights_to_fpga):
            #   inputs  0..127 → group=0, local=input_idx
            #   inputs 128..255 → group=1, local=input_idx-128
            #   input  256 (bias) → group=0, local=127
            spike_global_ids = []
            for inp in l1_spike_ids:
                if inp < 128:
                    spike_global_ids.append(global_id(0, inp))
                elif inp < 256:
                    spike_global_ids.append(global_id(1, inp - 128))
                else:  # bias
                    spike_global_ids.append(global_id(0, 127))

            spike_global_ids = list(set(spike_global_ids))  # deduplicate
            pkt_len = len(spike_global_ids)

            # ── DMA: send spikes to FPGA, receive output spikes ─────────────
            spike2 = np.zeros(L2_NEURONS, dtype=np.int32)

            if pkt_len > 0:
                # Pack spike packet: each word = 32-bit, [9:0] = global neuron ID
                for k, gid in enumerate(spike_global_ids):
                    in_buffer[k] = int(gid) & 0x3FF   # 10-bit global ID

                in_buffer.flush()

                # ── DMA S2MM (FPGA→ARM): arm the receive channel first ───────
                dest_ptr = out_buffer.device_address
                dma_mmio.write(0x30, 0x04)            # S2MM reset
                dma_mmio.write(0x30, 0x00)            # clear reset
                dma_mmio.write(0x48, dest_ptr)        # S2MM dest address
                dma_mmio.write(0x58, len(out_buffer) * 4)  # S2MM max bytes

                # ── DMA MM2S (ARM→FPGA): start transmit ─────────────────────
                dma_mmio.write(0x00, 0x04)            # MM2S reset
                dma_mmio.write(0x00, 0x00)            # clear reset
                dma_mmio.write(0x18, in_buffer.device_address)  # src address
                dma_mmio.write(0x28, pkt_len * 4)    # byte count → triggers DMA

                # ── Wait for MM2S completion ─────────────────────────────────
                t_timeout = time.time() + 0.5
                while True:
                    if dma_mmio.read(0x04) & 0x0002:  # MM2S idle/complete
                        break
                    if time.time() > t_timeout:
                        break

                # ── Wait for FPGA to process and return output spikes ────────
                # Poll S2MM for completion or partial data
                t_timeout = time.time() + 0.5
                while True:
                    s2mm_status = dma_mmio.read(0x34)
                    if s2mm_status & 0x0002:   # S2MM idle (packet complete)
                        break
                    if s2mm_status & 0x1000:   # IOC interrupt set
                        break
                    if time.time() > t_timeout:
                        break

                out_buffer.invalidate()

                # ── Decode output spike packet ───────────────────────────────
                # Each 32-bit word from the FPGA = one output spike event.
                # [9:0] = global neuron ID of the fired output neuron.
                # Output neurons live in groups 2 (neurons 0..127) and
                #                              3 (neurons 0..127).
                # Global IDs:
                #   group 2 → global_id(2, n) = (2 << 7) | n = 256 + n
                #   group 3 → global_id(3, n) = (3 << 7) | n = 384 + n
                # L2 neuron index:
                #   group 2 neuron n → L2 index n
                #   group 3 neuron n → L2 index 128 + n

                # Count valid words (non-zero, within valid range)
                n_out_words = min(int(dma_mmio.read(0x58) // 4),
                                  len(out_buffer))
                for k in range(n_out_words):
                    word = int(out_buffer[k])
                    if word == 0:
                        continue
                    gid = word & 0x3FF
                    grp = gid >> LOCAL_ID_WIDTH          # bits [9:7]
                    loc = gid & ((1 << LOCAL_ID_WIDTH) - 1)  # bits [6:0]
                    if grp == 2 and loc < NEURONS_PER_GROUP:
                        spike2[loc] = 1
                    elif grp == 3 and loc < NEURONS_PER_GROUP:
                        spike2[128 + loc] = 1

                # Clear output buffer for next timestep
                out_buffer[:] = 0
                out_buffer.flush()

            # ── L3: CPU accumulator (int32) ─────────────────────────────────
            # q_w3_aug shape: (10, 257), spike2_aug shape: (257,)
            spike2_aug = np.append(spike2, 1)           # append bias neuron
            mem3 += np.dot(q_w3_aug.astype(np.int32), spike2_aug.astype(np.int32))

        # ── Classification ────────────────────────────────────────────────────
        prediction = int(np.argmax(mem3))
        if prediction == lbl:
            correct += 1

        log.append({
            "image_index":     img_idx,
            "true_label":      lbl,
            "predicted_label": prediction
        })

        if (img_idx + 1) % 100 == 0:
            acc_so_far = correct / (img_idx + 1) * 100
            print(f"  [{img_idx+1}/{n_test}] Running accuracy: {acc_so_far:.1f}%")

    # ── Stop HLS ──────────────────────────────────────────────────────────────
    hls_ctrl.write(0x00, 0x00)

    # ── Final results ─────────────────────────────────────────────────────────
    t_end    = time.time()
    accuracy = correct / n_test * 100
    avg_lat  = (t_end - t_start) / n_test * 1000   # ms per image

    final_router_spks = mmio.read(CFG_ROUTER_SPKS)
    final_neuron_spks = mmio.read(CFG_NEURON_SPKS)

    print(f"\n{'='*50}")
    print(f"  Inference Complete")
    print(f"  Accuracy   : {accuracy:.2f}% ({correct}/{n_test})")
    print(f"  Avg latency: {avg_lat:.2f} ms/image")
    print(f"  Prune th   : {applied_prune_th}")
    print(f"  HW threshold: {hw_threshold}")
    print(f"\n  Hardware diagnostics:")
    print(f"    Router spikes : {final_router_spks}")
    print(f"    Neuron spikes : {final_neuron_spks}")
    print(f"{'='*50}")

    results = {
        "metadata": {
            "timestamp":     datetime.now().isoformat(),
            "bitstream":     args.bitstream,
            "data_file":     args.data,
            "samples":       n_test,
            "timesteps":     args.timesteps,
            "hw_threshold":  hw_threshold,
            "prune_th":      applied_prune_th,
        },
        "metrics": {
            "accuracy_percent":   round(accuracy, 2),
            "correct":            correct,
            "total":              n_test,
            "average_latency_ms": round(avg_lat, 2),
            "hardware_diagnostics": {
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