#!/usr/bin/env python3
import argparse
import time
import os
import json
import numpy as np
from datetime import datetime
from pynq import Overlay, allocate

def encode_conn(src: int, fanout: int, dest: int, weight: int, exc: bool = True) -> tuple:
    """Encode one spike_router connection entry matching the hardware's 32-bit structure."""
    flat = src * 32 + fanout 
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

def upload_weights_to_fpga(mmio, w2_aug):
    """
    Programs Layer 2 using Virtual Source Expansion and dynamic sparsity 
    to fit perfectly within the FPGA's fragmented BRAM limits.
    """
    print("Preparing Layer 2 weights for FPGA BRAM...")
    
    # --- DYNAMIC SPARSITY: Simulate packing to fit 1792 virtual sources ---
    MAX_VIRTUAL_SOURCES = 2048 - 256 # 1792
    prune_threshold = -1
    
    while True:
        prune_threshold += 1
        if prune_threshold > 0:
            w2_aug[np.abs(w2_aug) <= prune_threshold] = 0
            
        required_v_sources = 0
        for real_src in range(w2_aug.shape[1]):
            non_zeros = np.count_nonzero(w2_aug[:, real_src])
            # Ceiling division by 32 (MAX_FANOUT)
            required_v_sources += (non_zeros + 31) // 32
            
        if required_v_sources <= MAX_VIRTUAL_SOURCES:
            break
            
    total_conns = np.count_nonzero(w2_aug)
    print(f"Applied Sparsity: Dropped weights |w| <= {prune_threshold}.")
    print(f"Total active connections to route: {total_conns}")
    print(f"Required virtual sources: {required_v_sources} / {MAX_VIRTUAL_SOURCES}")

    CONFIG_CTRL_OFFSET  = 0x00
    CONFIG_ADDR_OFFSET  = 0x04
    CONFIG_WDATA_OFFSET = 0x08
    
    mmio.write(CONFIG_CTRL_OFFSET, 0) 
    
    # Zero out old connection counts
    for v in range(2048):
        cnt_addr = (0x01 << 24) | (v & 0x00_FFFF)
        mmio.write(CONFIG_ADDR_OFFSET, cnt_addr)
        mmio.write(CONFIG_WDATA_OFFSET, 0)
        
    real_to_virtual = {}
    virtual_src_id = 256 
    
    for real_src in range(w2_aug.shape[1]): 
        real_to_virtual[real_src] = []
        
        non_zero_dests = []
        for dest in range(w2_aug.shape[0]):
            w = int(w2_aug[dest, real_src])
            if w != 0:
                non_zero_dests.append((dest, w))
                
        for i in range(0, len(non_zero_dests), 32):
            chunk = non_zero_dests[i:i+32]
            v_src = virtual_src_id
            real_to_virtual[real_src].append(v_src)
            
            for fanout, (dest, w) in enumerate(chunk):
                exc = (w > 0)
                abs_w = abs(w)
                ca, cd = encode_conn(v_src, fanout, dest, abs_w, exc=exc)
                mmio.write(CONFIG_ADDR_OFFSET, ca)
                mmio.write(CONFIG_WDATA_OFFSET, cd)
            
            cnt_addr = (0x01 << 24) | (v_src & 0x00_FFFF)
            mmio.write(CONFIG_ADDR_OFFSET, cnt_addr)
            mmio.write(CONFIG_WDATA_OFFSET, len(chunk))
            
            virtual_src_id += 1
            if virtual_src_id >= 2048:
                raise RuntimeError("Hardware router memory full despite sparsity.")
                
    print(f"Mapped {w2_aug.shape[1]} real sources to {virtual_src_id - 256} virtual sources.")
    return real_to_virtual

def main():
    parser = argparse.ArgumentParser(description="3-Layer SNN FPGA Inference")
    parser.add_argument('--bitstream', default='snn_core_group_v2.bit', help='Path to bitstream')
    parser.add_argument('--data', default='mnist_3layer_deployment.npz', help='Deployment payload')
    parser.add_argument('--samples', type=int, default=1000, help='Images to test')
    parser.add_argument('--skip-bitstream', action='store_true', help='Skip PL programming')
    parser.add_argument('--output-json', default='inference_results.json', help='Output results file')
    args = parser.parse_args()

    payload = np.load(args.data)
    w1_f = payload['w1_f']
    b1_f = payload['b1_f']
    q_w2_aug = payload['q_w2_aug'].copy() # Copy to allow pruning modification
    q_w3_aug = payload['q_w3_aug']
    test_imgs = payload['test_imgs']
    test_lbls = payload['test_lbls']
    hw_threshold = int(payload['hw_threshold'])

    print("Initializing PYNQ Overlay...")
    if not args.skip_bitstream and os.path.exists(args.bitstream):
        overlay = Overlay(args.bitstream)
    else:
        overlay = Overlay(args.bitstream, download=False)

    dma_mmio = overlay.axi_dma_0.mmio              
    mmio = overlay.snn_config_regs_0.mmio
    hls_ctrl = overlay.snn_top_hls_0.mmio

    # 1. Halve the threshold to counteract the encode_conn bit-shift,
    # then scale by 85% to compensate for the sparsity pruning.
    hw_threshold = int((hw_threshold / 2.0) * 0.85)

    # 2. Initialize Hardware Registers
    mmio.write(0x10, hw_threshold)
    mmio.write(0x14, 0) # CRITICAL: Force Leak=0 and Refrac=0

    # 3. HLS Warmup (Required on first boot to clear internal BRAM)
    print("Warming up HLS Block...")
    hls_ctrl.write(0x10, 0x01) 
    hls_ctrl.write(0x00, 0x01) 
    time.sleep(0.05)           
    hls_ctrl.write(0x00, 0x00) 
    hls_ctrl.write(0x10, 0x00) 
    time.sleep(0.01)

    src_map = upload_weights_to_fpga(mmio, q_w2_aug)

    in_buffer = allocate(shape=(2048,), dtype=np.uint32)
    out_buffer = allocate(shape=(1024,), dtype=np.uint32) 

    correct = 0
    n_test = min(args.samples, len(test_imgs))
    detailed_log = []
    
    print(f"\nStarting Co-Processing Inference for {n_test} images...")
    start_time = time.time()

    for i in range(n_test):
        img = test_imgs[i].flatten()
        lbl = int(test_lbls[i])
        
        mem1 = np.zeros(256, dtype=np.float32)
        mem3 = np.zeros(10, dtype=np.int32)
        
        hls_ctrl.write(0x10, 0x04) 
        hls_ctrl.write(0x00, 0x01) 
        while (hls_ctrl.read(0x00) & 0x06) == 0:
            pass 
        hls_ctrl.write(0x00, 0x00)
        
        hls_ctrl.write(0x10, 0x01)             
        hls_ctrl.write(0x20, 0x00)             
        hls_ctrl.write(0x28, 1)                
        hls_ctrl.write(0x18, hw_threshold)
        hls_ctrl.write(0x00, 0x81)             
        
        for t in range(4): 
            mem1 += np.dot(w1_f, img) + b1_f
            mem1 = np.maximum(mem1, 0)
            spike1 = (mem1 >= 1.0).astype(np.uint32)
            mem1[spike1 > 0] = 0.0 
            
            spike_ids = np.nonzero(spike1)[0].tolist()
            spike_ids.append(256) 
            
            virtual_spikes = []
            for real_id in spike_ids:
                virtual_spikes.extend(src_map.get(real_id, []))
                
            packet_len = len(virtual_spikes)
            for idx in range(packet_len):
                in_buffer[idx] = (virtual_spikes[idx] & 0x1FFF) | (1 << 13)

            # FLUSH CACHE: Push CPU inputs to physical DDR for the FPGA DMA
            in_buffer.flush()
                
            spike2 = np.zeros(256, dtype=np.int32)
                
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
                mm2s_done = False
                while spikes_received < 1024:
                    timeout = time.time() + 0.005 
                    got_spike = False
                    
                    while time.time() < timeout:
                        if dma_mmio.read(0x34) & 0x1000: 
                            got_spike = True
                            break
                        if not mm2s_done and (dma_mmio.read(0x04) & 0x0002):
                            mm2s_done = True
                            
                    if got_spike:
                        spikes_received += 1
                        dma_mmio.write(0x34, 0x1000)
                        dma_mmio.write(0x30, 0x01)
                        dma_mmio.write(0x48, dest_ptr + (spikes_received * 4))
                        dma_mmio.write(0x58, 4)
                    else:
                        break 
                
                timeout = time.time() + 0.1
                while not mm2s_done and time.time() < timeout:
                    if dma_mmio.read(0x04) & 0x0002:
                        break

                # INVALIDATE CACHE: Pull physical DDR outputs back into CPU cache
                out_buffer.invalidate()
                        
                for s in range(spikes_received):
                    out_val = out_buffer[s]
                    if out_val > 0:
                        neuron_id = out_val & 0x1FFF
                        if neuron_id < 256:
                            spike2[neuron_id] = 1 
                            
                out_buffer[:] = 0

            spike2_aug = np.append(spike2, 1)
            mem3 += np.dot(q_w3_aug, spike2_aug) 

        prediction = int(np.argmax(mem3))
        if prediction == lbl:
            correct += 1
            
        detailed_log.append({
            "image_index": i,
            "true_label": lbl,
            "predicted_label": prediction
        })
            
        if (i + 1) % 100 == 0:
            print(f"Processed {i+1}/{n_test} | Current Acc: {(correct/(i+1))*100:.1f}%")

    end_time = time.time()
    accuracy = (correct / n_test) * 100
    print(f"\n===== Inference Complete =====")
    print(f"Total Accuracy: {accuracy:.1f}%")

    results = {
        "metrics": {
            "accuracy_percent": round(accuracy, 2),
            "average_latency_ms": round(((end_time - start_time) / n_test) * 1000, 2)
        },
        "predictions": detailed_log
    }
    with open(args.output_json, 'w') as f:
        json.dump(results, f, indent=4)

if __name__ == '__main__':
    main()