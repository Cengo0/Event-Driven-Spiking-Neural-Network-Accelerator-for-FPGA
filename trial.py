import numpy as np
from pynq import Overlay, allocate
import time

def main():
    print("="*60)
    print("🚀 PYNQ-Z2 BARE-METAL SCA TRIGGER")
    print("="*60)
    
    # 1. Load the overlay directly
    print("Loading bitstream...")
    overlay = Overlay("design_1_wrapper.bit")
    
    # Map the IP and DMAs based on your Vivado design
    snn_ip = overlay.snn_top_hls_0
    spike_dma = overlay.axi_dma_1
    weight_dma = overlay.axi_dma_2
    
    # 2. Initialize the Hardware Registers directly
    # 0x81 = Enable ap_start and auto_restart
    snn_ip.write(0x00, 0x81)
    snn_ip.write(0x10, 200)   # Threshold
    snn_ip.write(0x14, 0)     # Leak = 0
    snn_ip.write(0x18, 5)     # Refractory Period
    
    # 3. Load exactly 2,000 weights (Max Excitatory)
    print("Loading 2,000 weights into HLS BRAM...")
    w_buf = allocate(shape=(2000,), dtype=np.int8)
    w_buf[:] = 127  # Maximum positive 8-bit integer
    
    weight_dma.sendchannel.transfer(w_buf)
    weight_dma.sendchannel.wait()
    
    # 4. Prepare a DMA-safe burst of input spikes (4,000 spikes = 16,000 bytes)
    print("Packing 4,000 input spikes...")
    s_buf = allocate(shape=(4000,), dtype=np.uint32)
    
    for i in range(4000):
        # Cycle through the 900 spatial input neurons
        neuron_id = i % 900
        weight = 127  
        timestamp = 1 # Timestamp is irrelevant with leak set to 0
        
        # Pack to 32-bit AER format: [31:18] timestamp, [17:10] weight, [9:0] neuron_id
        word = (timestamp << 18) | (weight << 10) | neuron_id
        s_buf[i] = word

    # 5. Execute the trigger
    print("\n⚡ TRIGGER OSCILLOSCOPE NOW ⚡")
    time.sleep(2) # Brief pause to arm the oscilloscope
    
    start_time = time.time()
    spike_dma.sendchannel.transfer(s_buf)
    spike_dma.sendchannel.wait()
    hw_time = (time.time() - start_time) * 1000
    
    print(f"✅ Fired 4,000 spikes directly into MAC units via DMA in {hw_time:.2f} ms")

if __name__ == '__main__':
    main()