#!/usr/bin/env python3
import argparse
import time
import os
import json
import numpy as np
from datetime import datetime
from pynq import Overlay, allocate

def upload_weights_to_fpga(mmio, w2, w3):
    """
    Programs the synaptic_connectivity_table via AXI-Lite using the 
    snn_config_regs.v memory map.
    """
    print("Uploading Layer 2 and Layer 3 weights to FPGA BRAM...")
    
    CONFIG_CTRL_OFFSET  = 0x00
    CONFIG_ADDR_OFFSET  = 0x04
    CONFIG_WDATA_OFFSET = 0x08
    
    # 1. Target the Synaptic Connectivity Table (previously 'router')
    mmio.write(CONFIG_CTRL_OFFSET, 0) 
    
    # 2. Upload Layer 2 Weights
    # Assuming sequential addressing starting at 0 for the BRAM
    current_addr = 0
    for row in w2:
        for weight in row:
            mmio.write(CONFIG_ADDR_OFFSET, current_addr)
            # Convert signed int8 to unsigned 32-bit for AXI transfer
            val = int(weight) & 0xFF 
            mmio.write(CONFIG_WDATA_OFFSET, val)
            current_addr += 1
            
    # 3. Upload Layer 3 Weights
    for row in w3:
        for weight in row:
            mmio.write(CONFIG_ADDR_OFFSET, current_addr)
            val = int(weight) & 0xFF
            mmio.write(CONFIG_WDATA_OFFSET, val)
            current_addr += 1
            
    print(f"Weight upload complete. Total synaptic connections mapped: {current_addr}")

def main():
    parser = argparse.ArgumentParser(description="3-Layer SNN FPGA Inference")
    parser.add_argument('--bitstream', default='snn_core_group_v2.bit', help='Path to bitstream')
    parser.add_argument('--data', default='mnist_3layer_deployment.npz', help='Deployment payload')
    parser.add_argument('--samples', type=int, default=10, help='Images to test')
    parser.add_argument('--skip-bitstream', action='store_true', help='Skip PL programming')
    parser.add_argument('--output-json', default='inference_results.json', help='Output results file')
    args = parser.parse_args()

    # 1. Load Data Payload
    print(f"Loading payload: {args.data}")
    payload = np.load(args.data)
    w1_f = payload['w1_f']
    b1_f = payload['b1_f']
    q_w2_aug = payload['q_w2_aug']
    q_w3_aug = payload['q_w3_aug']
    test_imgs = payload['test_imgs']
    test_lbls = payload['test_lbls']
    hw_threshold = int(payload['hw_threshold'])

    # 2. Initialize Overlay and DMA
    print("Initializing PYNQ Overlay...")
    if not args.skip_bitstream and os.path.exists(args.bitstream):
        overlay = Overlay(args.bitstream)
    else:
        overlay = Overlay(args.bitstream, download=False)

    dma = overlay.axi_dma_0
    dma_mmio = dma.mmio              # ADD THIS: Raw DMA register access
    mmio = overlay.snn_config_regs_0.mmio
    hls_ctrl = overlay.snn_top_hls_0.mmio
    
    # ─────────────────────────────────────────────────────────
    # HLS WAKEUP SEQUENCE (Adapted from original script)
    # ─────────────────────────────────────────────────────────
    hls_ctrl.write(0x10, 0x01)             # HLS_CTRL_REG: Enable
    hls_ctrl.write(0x20, 0x00)             # HLS_MODE_REG: Inference mode
    hls_ctrl.write(0x28, 0x01)             # HLS_TIME_STEPS: 1 (Required for streaming)
    hls_ctrl.write(0x18, hw_threshold)     # HLS_CONFIG_REG: Threshold
    hls_ctrl.write(0x00, 0x81)             # HLS_AP_CTRL: Auto-Restart | Start
    
    # Set Global Hardware Threshold (Register 0x10 in Config RTL)
    mmio.write(0x10, hw_threshold)

    # 3. Upload FPGA Weights
    upload_weights_to_fpga(mmio, q_w2_aug, q_w3_aug)

    # 4. Allocate DMA Buffers (Max spikes per timestep = 256 L1 neurons + 1 Bias)
    in_buffer = allocate(shape=(257,), dtype=np.uint32)
    out_buffer = allocate(shape=(1024,), dtype=np.uint32)

    correct = 0
    n_test = min(args.samples, len(test_imgs))
    
    print(f"\nStarting Co-Processing Inference for {n_test} images...")
    start_time = time.time()

    for i in range(n_test):
        print("testing image", i)
        img = test_imgs[i].flatten()
        lbl = int(test_lbls[i])
        
        # CPU Memory for Layer 1
        mem1 = np.zeros(256, dtype=np.float32)
        out_spikes = np.zeros(10, dtype=np.int32)

        # --- HARDWARE RESET: Clear neuron potentials from previous image ---
        hls_ctrl.write(0x10, 0x04) # CTRL_CLEAR
        hls_ctrl.write(0x00, 0x01) # Start
        while (hls_ctrl.read(0x00) & 0x06) == 0:
            pass # Wait for done
        hls_ctrl.write(0x00, 0x00)

        # --- START HLS FOR CURRENT IMAGE ---
        hls_ctrl.write(0x10, 0x01)             # Enable
        hls_ctrl.write(0x20, 0x00)             # Mode: Inference
        hls_ctrl.write(0x28, 1)                # Timesteps: 1 per stream
        hls_ctrl.write(0x18, hw_threshold)
        hls_ctrl.write(0x00, 0x81)             # Auto-Restart

        for t in range(4): # TIMESTEPS = 4
            print(f"Processing timestep {t}")
            # ─────────────────────────────────────────────────────────
            # CPU STAGE: Layer 1 Float32 Evaluation
            # ─────────────────────────────────────────────────────────
            mem1 += np.dot(w1_f, img) + b1_f
            mem1 = np.maximum(mem1, 0)
            spike1 = (mem1 >= 1.0).astype(np.uint32)
            mem1[spike1 > 0] = 0.0 # Hard Reset
            
            # Pack Spikes for DMA: Format [31:16 ID, 15:0 Padding/Weight]
            # ID 256 acts as the "Always-On Bias Neuron" for Layer 2
            spike_ids = np.nonzero(spike1)[0].astype(np.uint32)
            spike_ids = np.append(spike_ids, 256) 
            
            packet_len = len(spike_ids)
            for idx in range(packet_len):
                in_buffer[idx] = (spike_ids[idx] << 16)
                
            # ─────────────────────────────────────────────────────────
            # FPGA STAGE: Pure MMIO DMA Stream and Polled Receive
            # ─────────────────────────────────────────────────────────
            if packet_len > 0:
                # 1. Hard Reset DMA Channels
                dma_mmio.write(0x00, 0x04) # MM2S Reset
                dma_mmio.write(0x30, 0x04) # S2MM Reset
                time.sleep(0.002)
                
                # 2. Arm First Receive Transfer (4 bytes)
                dest_ptr = out_buffer.device_address
                dma_mmio.write(0x34, 0x1000) # Clear IOC_Irq
                dma_mmio.write(0x30, 0x01)   # Run
                dma_mmio.write(0x48, dest_ptr)
                dma_mmio.write(0x58, 4)      # Length triggers transfer
                
                # 3. Fire Send Channel
                src_ptr = in_buffer.device_address
                dma_mmio.write(0x00, 0x01)   # Run
                dma_mmio.write(0x18, src_ptr)
                dma_mmio.write(0x28, packet_len * 4) # Length triggers transfer
                
                # 4. Concurrently Poll Receive and Send
                spikes_received = 0
                max_spikes = 1024
                
                mm2s_done = False
                while spikes_received < max_spikes:
                    timeout = time.time() + 0.005 # 5ms timeout per spike
                    got_spike = False
                    
                    while time.time() < timeout:
                        sr = dma_mmio.read(0x34)
                        if sr & 0x1000: # S2MM IOC_Irq (transfer complete)
                            got_spike = True
                            break
                        
                        if not mm2s_done and (dma_mmio.read(0x04) & 0x0002):
                            mm2s_done = True
                            
                    if got_spike:
                        spikes_received += 1
                        # Re-arm immediately for the next spike
                        next_dest = dest_ptr + (spikes_received * 4)
                        dma_mmio.write(0x34, 0x1000)
                        dma_mmio.write(0x30, 0x01)
                        dma_mmio.write(0x48, next_dest)
                        dma_mmio.write(0x58, 4)
                    else:
                        break # No more spikes arriving
                
                # 5. Wait for MM2S (Send) to finish if it hasn't already
                timeout = time.time() + 0.1
                while not mm2s_done and time.time() < timeout:
                    if dma_mmio.read(0x04) & 0x0002:
                        break
                        
                # 6. Decode Spikes
                for s in range(spikes_received):
                    out_val = out_buffer[s]
                    if out_val > 0:
                        neuron_id = (out_val >> 16) & 0xFFFF
                        if neuron_id < 10:
                            out_spikes[neuron_id] += 1
                            
                out_buffer[:] = 0

        # Prediction
        if np.argmax(out_spikes) == lbl:
            correct += 1
            
        # if (i + 1) % 1 == 0:
        print(f"Processed {i+1}/{n_test} | Current Acc: {(correct/(i+1))*100:.1f}%")

    end_time = time.time()
    accuracy = (correct / n_test) * 100
    avg_latency = ((end_time - start_time) / n_test) * 1000

    print(f"\n===== Inference Complete =====")
    print(f"Total Accuracy: {accuracy:.1f}%")
    print(f"Average Speed:  {avg_latency:.2f} ms/image")

    # 5. Generate JSON Log
    results = {
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "bitstream": args.bitstream,
            "payload_file": args.data,
            "hardware_threshold": hw_threshold,
            "timesteps": 4
        },
        "metrics": {
            "total_samples": n_test,
            "correct_predictions": correct,
            "accuracy_percent": round(accuracy, 2),
            "total_inference_time_sec": round(end_time - start_time, 4),
            "average_latency_ms": round(avg_latency, 2)
        }
    }
    
    with open(args.output_json, 'w') as f:
        json.dump(results, f, indent=4)
    print(f"Detailed results logged to {args.output_json}")

    in_buffer.freebuffer()
    out_buffer.freebuffer()

if __name__ == '__main__':
    main()