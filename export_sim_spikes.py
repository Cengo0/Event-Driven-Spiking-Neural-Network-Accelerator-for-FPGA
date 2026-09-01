import numpy as np

def encode_spike_word(neuron_id, weight):
    nid = neuron_id & 0x3FF
    w = weight & 0xFF
    return nid | (w << 10)

def main():
    print("Loading deployment data...")
    data = np.load('data/cache/mnist_10class_deployment.npz', allow_pickle=True)
    q_weights = data['q_weights']
    test_imgs = data['test_imgs']
    
    n_images = 10 # We will simulate the first 10 images
    n_output = int(data['n_output'])
    pixel_threshold = 0.3
    
    with open('hardware/sim/sim_input_spikes.hex', 'w') as f:
        for i in range(n_images):
            img = test_imgs[i].flatten()
            active_pixels = np.where(img > pixel_threshold)[0]
            
            for input_idx in active_pixels:
                for out_idx in range(n_output):
                    w = int(q_weights[out_idx, input_idx])
                    if w > 0:
                        word = encode_spike_word(out_idx, w)
                        f.write(f"{word:08X}\n")
            
            # Write a delimiter to tell the Verilog testbench this image is done
            f.write("FFFFFFFF\n")
            
    print(f"Exported hex spikes for {n_images} images to sim_input_spikes.hex")

if __name__ == '__main__':
    main()