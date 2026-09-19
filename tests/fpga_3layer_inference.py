#!/usr/bin/env python3
import argparse
import time
import os
import json
import numpy as np
from datetime import datetime
from pynq import Overlay, allocate

def upload_weights_to_fpga(mmio, w2):
    """
    Programs ONLY Layer 2 into the synaptic_connectivity_table.
    Layer 3 stays on the CPU.
    """
    print("Uploading Layer 2 weights to FPGA BRAM...")
    
    CONFIG_CTRL_OFFSET  = 0x00
    CONFIG_ADDR_OFFSET  = 0x04
    CONFIG_WDATA_OFFSET = 0x08
    
    # Target the Synaptic Connectivity Table
    mmio.write(CONFIG_CTRL_OFFSET, 0) 
    
    current_addr = 0
    for row in w2:
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
    parser.add_argument('--samples', type=int, default=1000, help='Images to test')
    parser.add_argument('--skip-bitstream', action='store_true', help='Skip PL programming')
    parser.add_argument('--output-json', default='inference_results.json', help='Output results file')
    args = parser.parse_args()

    print(f"Loading payload: {args.data}")
    payload = np.load(args.data)
    w1_f = payload['w1_f']
    b1_f = payload['b1_f']
    q_w2_aug = payload['q_w2_aug']
    q_w3_aug = payload['q_w3_aug']
    test_imgs = payload['test_imgs']
    test_lbls = payload['test_lbls']
    hw_threshold = int(payload['hw_threshold'])

    print("Initializing PYNQ Overlay...")
    if not args.skip_bitstream and os.path.exists(args.bitstream):
        overlay = Overlay(args.bitstream)
    else:
        overlay = Overlay(args.bitstream, download=False)

    dma = overlay.axi_dma_0
    dma_mmio = dma.mmio              
    mmio = overlay.snn_config_regs_0.mmio
    hls_ctrl = overlay.snn_top_hls_0.mmio
    
    mmio.write(0x10, hw_threshold)

    # Upload ONLY Layer 2 to the FPGA
    upload_weights_to_fpga(mmio, q_w2_aug)

    in_buffer = allocate(shape=(257,), dtype=np.uint32)
    out_buffer = allocate(shape=(1024,), dtype=np.uint32) 

    correct = 0
    n_test = min(args.samples, len(test_imgs))
    
    print(f"\nStarting Co-Processing Inference for {n_test} images...")
    start_time = time.time()

    for i in range(n_test):
        img = test_imgs[i].flatten()
        lbl = int(test_lbls[i])
        
        mem1 = np.zeros(256, dtype=np.float32)
        mem3 = np.zeros(10, dtype=np.int32) # Layer 3 Voltage Accumulator (CPU)
        
        # --- HARDWARE RESET: Clear FPGA potentials between images ---
        hls_ctrl.write(0x10, 0x04) # CTRL_CLEAR
        hls_ctrl.write(0x00, 0x01) # Start
        while (hls_ctrl.read(0x00) & 0x06) == 0:
            pass 
        hls_ctrl.write(0x00, 0x00)
        
        # --- START HLS FOR CURRENT IMAGE ---
        hls_ctrl.write(0x10, 0x01)             # Enable
        hls_ctrl.write(0x20, 0x00)             # Mode: Inference
        hls_ctrl.write(0x28, 1)                # Timesteps: 1 per stream
        hls_ctrl.write(0x18, hw_threshold)
        hls_ctrl.write(0x00, 0x81)             # Auto-Restart
        
        for t in range(4): 
            # ─────────────────────────────────────────────────────────
            # CPU STAGE 1: Layer 1 Float32 Evaluation
            # ─────────────────────────────────────────────────────────
            mem1 += np.dot(w1_f, img) + b1_f
            mem1 = np.maximum(mem1, 0)
            spike1 = (mem1 >= 1.0).astype(np.uint32)
            mem1[spike1 > 0] = 0.0 
            
            spike_ids = np.nonzero(spike1)[0].astype(np.uint32)
            spike_ids = np.append(spike_ids, 256) 
            
            packet_len = len(spike_ids)
            for idx in range(packet_len):
                in_buffer[idx] = (spike_ids[idx] << 16)
                
            spike2 = np.zeros(256, dtype=np.int32)
                
            # ─────────────────────────────────────────────────────────
            # FPGA STAGE: Pure MMIO DMA Stream and Polled Receive
            # ─────────────────────────────────────────────────────────
            if packet_len > 0:
                dma_mmio.write(0x00, 0x04) 
                dma_mmio.write(0x30, 0x04) 
                time.sleep(0.002)
                
                dest_ptr = out_buffer.device_address
                dma_mmio.write(0x34, 0x1000) 
                dma_mmio.write(0x30, 0x01)   
                dma_mmio.write(0x48, dest_ptr)
                dma_mmio.write(0x58, 4)      
                
                src_ptr = in_buffer.device_address
                dma_mmio.write(0x00, 0x01)   
                dma_mmio.write(0x18, src_ptr)
                dma_mmio.write(0x28, packet_len * 4) 
                
                spikes_received = 0
                max_spikes = 1024
                
                mm2s_done = False
                while spikes_received < max_spikes:
                    timeout = time.time() + 0.005 
                    got_spike = False
                    
                    while time.time() < timeout:
                        sr = dma_mmio.read(0x34)
                        if sr & 0x1000: 
                            got_spike = True
                            break
                        if not mm2s_done and (dma_mmio.read(0x04) & 0x0002):
                            mm2s_done = True
                            
                    if got_spike:
                        spikes_received += 1
                        next_dest = dest_ptr + (spikes_received * 4)
                        dma_mmio.write(0x34, 0x1000)
                        dma_mmio.write(0x30, 0x01)
                        dma_mmio.write(0x48, next_dest)
                        dma_mmio.write(0x58, 4)
                    else:
                        break 
                
                timeout = time.time() + 0.1
                while not mm2s_done and time.time() < timeout:
                    if dma_mmio.read(0x04) & 0x0002:
                        break
                        
                for s in range(spikes_received):
                    out_val = out_buffer[s]
                    if out_val > 0:
                        neuron_id = (out_val >> 16) & 0xFFFF
                        if neuron_id < 256:
                            spike2[neuron_id] = 1 # Log Layer 2 Spike
                            
                out_buffer[:] = 0

            # ─────────────────────────────────────────────────────────
            # CPU STAGE 2: Layer 3 Voltage Accumulation
            # ─────────────────────────────────────────────────────────
            spike2_aug = np.append(spike2, 1)
            mem3 += np.dot(q_w3_aug, spike2_aug) # Accumulate raw voltage

        # Prediction: argmax of final voltage
        if np.argmax(mem3) == lbl:
            correct += 1
            
        if (i + 1) % 100 == 0:
            print(f"Processed {i+1}/{n_test} | Current Acc: {(correct/(i+1))*100:.1f}%")

    end_time = time.time()
    accuracy = (correct / n_test) * 100
    avg_latency = ((end_time - start_time) / n_test) * 1000

    print(f"\n===== Inference Complete =====")
    print(f"Total Accuracy: {accuracy:.1f}%")
    print(f"Average Speed:  {avg_latency:.2f} ms/image")

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