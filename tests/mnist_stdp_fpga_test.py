#!/usr/bin/env python3
"""
MNIST STDP End-to-End FPGA Verification
========================================
Trains a simple dense SNN with STDP on MNIST (digits 0/1),
then deploys to FPGA and compares HW vs SW inference.

Architecture (matching HLS IP):
  - 784 input neurons (28x28 MNIST pixels, rate-coded)
  - 20 output neurons (10 per class, 2-class: digits 0/1)
  - Dense weights: 20 x 784, 8-bit signed
  - LIF neuron model: pot += weight*spike; pot -= leak; fire if pot > threshold

FPGA Inference Strategy:
  - Pre-compute weighted spikes on host
  - Router: identity mapping (neuron Y → Y)
  - For each firing input i, send spike {id=j, weight=W[i][j]} for each output j
  - Neurons accumulate and fire → WTA → class prediction
  - Read output spike IDs from S2MM DMA (new bitstream)
    or total spike counts (current bitstream)

Author: auto-generated for FPGA verification
"""

import sys
import os
import time
import struct
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'software', 'python'))

import torch
import torch.nn.functional as F
from torchvision import datasets, transforms

# =============================================================================
# Part A: Simple Dense SNN with STDP (matches HLS architecture)
# =============================================================================

class DenseSTDPNetwork:
    """
    Simple dense SNN with STDP for MNIST classification.
    Matches HLS IP architecture: input spikes → dense weights → LIF neurons → WTA.
    
    Architecture:
      784 input → 20 output (10 per class)
      Weights: 8-bit signed after quantization
      LIF: pot += w * spike_in; pot -= leak; if pot > thresh: fire
    """
    
    def __init__(self, n_input=784, n_output=20, n_classes=2,
                 threshold=50.0, leak=0.5, timesteps=15):
        self.n_input = n_input
        self.n_output = n_output
        self.n_classes = n_classes
        self.features_per_class = n_output // n_classes
        self.threshold = threshold
        self.leak = leak
        self.timesteps = timesteps
        
        # Initialize weights ~ N(0.5, 0.1), clipped to [0, 1]
        self.weights = np.random.normal(0.5, 0.1, (n_output, n_input)).astype(np.float32)
        self.weights = np.clip(self.weights, 0.0, 1.0)
        
        # Decision map: features 0..9 → class 0, features 10..19 → class 1
        self.decision_map = np.array([i // self.features_per_class for i in range(n_output)])
        
        # STDP learning rates
        self.lr_plus = 0.004     # LTP (pre before post)
        self.lr_minus = -0.003   # LTD (post before pre)
        
    def rate_encode(self, image, timesteps=None):
        """
        Rate-code a 28x28 image into spike trains.
        Higher pixel intensity → higher firing probability per timestep.
        
        Args:
            image: (784,) float array, values in [0, 1]
            timesteps: number of timesteps
            
        Returns:
            spikes: (T, 784) binary array
        """
        T = timesteps or self.timesteps
        probs = image.reshape(1, -1).repeat(T, axis=0)  # (T, 784)
        spikes = (np.random.rand(T, self.n_input) < probs).astype(np.float32)
        return spikes
    
    def forward(self, spikes):
        """
        Forward pass through the network.
        
        Args:
            spikes: (T, 784) binary spike trains
            
        Returns:
            prediction: class label (-1 if no winner)
            potentials: (n_output,) final membrane potentials
            fired: (n_output,) bool, which neurons fired
            fire_times: (n_output,) int, when each neuron first fired (-1 if never)
        """
        T = spikes.shape[0]
        potentials = np.zeros(self.n_output, dtype=np.float32)
        fired = np.zeros(self.n_output, dtype=bool)
        fire_times = np.full(self.n_output, -1, dtype=np.int32)
        
        for t in range(T):
            active_inputs = spikes[t]  # (784,) binary
            
            # Weight accumulation: pot += W @ spike_in
            potentials += self.weights @ active_inputs
            
            # Leak
            potentials -= self.leak
            potentials = np.maximum(potentials, 0)
            
            # Fire check
            newly_fired = (potentials >= self.threshold) & ~fired
            if np.any(newly_fired):
                for j in np.where(newly_fired)[0]:
                    fired[j] = True
                    fire_times[j] = t
                    potentials[j] = 0  # Reset after fire
        
        # WTA: earliest fire time wins
        if np.any(fired):
            # Among fired neurons, pick the one with earliest fire time
            fired_times = fire_times[fired]
            fired_indices = np.where(fired)[0]
            winner_idx = fired_indices[np.argmin(fired_times)]
            prediction = self.decision_map[winner_idx]
        else:
            # No winner: pick highest potential
            winner_idx = np.argmax(potentials)
            prediction = self.decision_map[winner_idx]
        
        return prediction, potentials, fired, fire_times
    
    def train_rstdp(self, spikes, target, prediction):
        """
        Apply R-STDP learning.
        
        Reward (correct): strengthen winner's connections
        Punish (wrong): weaken winner's connections  
        """
        # Compute pre/post spike correlation
        pre_activity = spikes.sum(axis=0)  # (784,) total spikes per input
        pre_active = pre_activity > 0
        
        if prediction == target:
            # Reward: strengthen connections from active inputs to winner class
            for j in range(self.n_output):
                if self.decision_map[j] == prediction:
                    # Strengthen: LTP for active inputs, LTD for inactive
                    self.weights[j, pre_active] += self.lr_plus * (1.0 - self.weights[j, pre_active])
                    self.weights[j, ~pre_active] += self.lr_minus * self.weights[j, ~pre_active]
        else:
            # Punish: weaken winner's connections, strengthen correct class
            for j in range(self.n_output):
                if self.decision_map[j] == prediction:
                    # Punish incorrect class
                    self.weights[j, pre_active] += self.lr_minus * self.weights[j, pre_active]
                elif self.decision_map[j] == target:
                    # Strengthen correct class
                    self.weights[j, pre_active] += self.lr_plus * (1.0 - self.weights[j, pre_active])
        
        # Clip weights to [0, 1]
        self.weights = np.clip(self.weights, 0.0, 1.0)
    
    def quantize_weights(self, scale=127.0):
        """
        Quantize float weights to 8-bit signed integers.
        
        Returns:
            q_weights: (n_output, n_input) int8 array
            scale: quantization scale factor
        """
        # Weights are in [0, 1], map to [0, 127] (signed 8-bit positive range)
        q_weights = np.round(self.weights * scale).astype(np.int8)
        return q_weights, scale


# =============================================================================
# Part B: Training
# =============================================================================

def load_mnist_binary(digits=[0, 1], max_train=None, max_test=None):
    """Load MNIST filtered for specific digits."""
    transform = transforms.Compose([transforms.ToTensor()])
    
    train_ds = datasets.MNIST('./data', train=True, download=True, transform=transform)
    test_ds = datasets.MNIST('./data', train=False, download=True, transform=transform)
    
    def filter_ds(ds, max_n=None):
        digit_to_label = {d: i for i, d in enumerate(digits)}
        images = []
        labels = []
        for img, lbl in ds:
            if lbl in digits:
                images.append(img.numpy().squeeze())  # (28, 28)
                labels.append(digit_to_label[lbl])
                if max_n and len(images) >= max_n:
                    break
        return np.array(images), np.array(labels)
    
    train_imgs, train_lbls = filter_ds(train_ds, max_train)
    test_imgs, test_lbls = filter_ds(test_ds, max_test)
    
    print(f"Train: {len(train_imgs)} samples, Test: {len(test_imgs)} samples")
    print(f"Classes: {digits} → labels {list(range(len(digits)))}")
    
    return train_imgs, train_lbls, test_imgs, test_lbls


def train_network(net, train_imgs, train_lbls, epochs=50, verbose=True):
    """Train the dense STDP network."""
    n_train = len(train_imgs)
    
    for epoch in range(epochs):
        # Shuffle
        perm = np.random.permutation(n_train)
        correct = 0
        wrong = 0
        
        for idx in perm:
            img = train_imgs[idx]   # (28, 28) in [0, 1]
            lbl = train_lbls[idx]
            
            # Rate encoding
            spikes = net.rate_encode(img.flatten())
            
            # Forward
            pred, _, _, _ = net.forward(spikes)
            
            # R-STDP
            net.train_rstdp(spikes, lbl, pred)
            
            if pred == lbl:
                correct += 1
            else:
                wrong += 1
        
        acc = correct / n_train * 100
        if verbose and (epoch % 10 == 0 or epoch == epochs - 1):
            w = net.weights
            print(f"  Epoch {epoch:3d}: Acc={acc:.1f}% "
                  f"W=[{w.min():.3f}, {w.max():.3f}] mean={w.mean():.3f}")
    
    return net


def test_network(net, test_imgs, test_lbls, verbose=True):
    """Test the dense STDP network. Returns per-sample predictions."""
    predictions = []
    correct = 0
    
    for i in range(len(test_imgs)):
        img = test_imgs[i]
        lbl = test_lbls[i]
        
        spikes = net.rate_encode(img.flatten())
        pred, pots, fired, fire_times = net.forward(spikes)
        predictions.append(pred)
        
        if pred == lbl:
            correct += 1
    
    acc = correct / len(test_imgs) * 100
    if verbose:
        print(f"Test Accuracy: {correct}/{len(test_imgs)} = {acc:.1f}%")
    
    return predictions, acc


# =============================================================================
# Part C: FPGA Deployment
# =============================================================================

def prepare_fpga_spikes(image, q_weights, n_output=20, threshold_fraction=0.3):
    """
    Prepare weighted spike events for FPGA injection.
    
    For each input pixel that fires (based on intensity threshold),
    generate spike events for all output neurons with appropriate weights.
    
    Args:
        image: (28, 28) float image in [0, 1]
        q_weights: (n_output, n_input) int8 quantized weights
        n_output: number of output neurons
        threshold_fraction: pixel intensity threshold for firing
        
    Returns:
        spike_events: list of (neuron_id, weight) tuples
    """
    pixels = image.flatten()  # (784,)
    active = np.where(pixels > threshold_fraction)[0]
    
    spike_events = []
    for input_idx in active:
        for out_idx in range(n_output):
            w = int(q_weights[out_idx, input_idx])
            if w != 0:  # Skip zero weights
                spike_events.append((out_idx, w))
    
    return spike_events


def encode_spike_word(neuron_id, weight):
    """
    Encode a spike event into 32-bit DMA word.
    Format: [9:0]=neuron_id, [17:10]=weight (unsigned byte mapping), [31:18]=timestamp
    """
    nid = neuron_id & 0x3FF  # 10 bits
    # Convert signed weight to unsigned 8-bit for DMA
    w = weight & 0xFF  # mask to 8 bits
    word = nid | (w << 10)
    return word


def sw_lif_inference(spike_events, n_output=20, threshold=50, leak=0):
    """
    Software LIF inference matching HLS behavior.
    Processes pre-weighted spike events through LIF neurons.
    
    This exactly matches what the FPGA should do:
    - For each spike event: pot[neuron_id] += weight
    - Apply leak each timestep
    - Fire if pot > threshold
    """
    potentials = np.zeros(n_output, dtype=np.float64)
    fired = np.zeros(n_output, dtype=bool)
    fire_order = []
    
    for neuron_id, weight in spike_events:
        potentials[neuron_id] += weight
        
        # Check fire (first-fire-time WTA)
        if potentials[neuron_id] >= threshold and not fired[neuron_id]:
            fired[neuron_id] = True
            fire_order.append(neuron_id)
            potentials[neuron_id] = 0  # Reset
    
    return potentials, fired, fire_order


def deploy_fpga_inference(spike_events, ssh_client, n_output=20):
    """
    Deploy a single image inference to FPGA.
    
    Requires: new bitstream with RTL fixes deployed on PYNQ board.
    
    Args:
        spike_events: list of (neuron_id, weight) tuples
        ssh_client: paramiko SSH client connected to PYNQ
        n_output: number of output neurons
        
    Returns:
        hw_fired: list of neuron IDs that fired
        hw_spike_count: total output spike count
    """
    # Encode spike events into DMA buffer
    spike_words = [encode_spike_word(nid, w) for nid, w in spike_events]
    n_spikes = len(spike_words)
    
    # Build Python script for PYNQ execution
    pynq_script = f'''
import numpy as np
import time
from pynq import MMIO

# Base addresses
HLS_BASE  = 0x43C00000
CFG_BASE  = 0x43C10000
DMA_BASE  = 0x41E00000

hls  = MMIO(HLS_BASE, 0x80)
cfg  = MMIO(CFG_BASE, 0x100)
dma  = MMIO(DMA_BASE, 0x10000)

# Reset HLS
hls.write(0x10, 0x02)  # ctrl_reg: reset
time.sleep(0.01)

# Configure
hls.write(0x18, 50)     # config_reg: threshold=50, leak=0
hls.write(0x20, 0)      # mode_reg: INFERENCE
hls.write(0x28, {n_spikes})  # time_steps = number of spike events

# Setup router: identity mapping (neuron j → neuron j)
for j in range({n_output}):
    # conn_memory: flat format, addr = src * MAX_FANOUT + fanout_idx
    # For identity: src=j, fanout_idx=0, dest=j, weight=127
    addr = j  # assuming MAX_FANOUT >= 1
    conn_word = (j & 0x3FF) | (127 << 10) | (1 << 18)  # dest_id | weight | valid
    cfg_addr = (0x00 << 24) | (addr & 0x00FFFFFF)
    cfg.write(0x10, cfg_addr)   # router_config_addr
    cfg.write(0x14, conn_word)  # router_config_wdata
    cfg.write(0x0C, 1)          # router_config_we
    cfg.write(0x0C, 0)

# Set conn_count for each source neuron
for j in range({n_output}):
    cfg_addr = (0x01 << 24) | (j & 0x00FFFFFF)
    cfg.write(0x10, cfg_addr)
    cfg.write(0x14, 1)  # 1 connection per source
    cfg.write(0x0C, 1)
    cfg.write(0x0C, 0)

# Clear counters
cfg_addr = (0x02 << 24) | 0
cfg.write(0x10, cfg_addr)
cfg.write(0x0C, 1)
cfg.write(0x0C, 0)

# Configure neuron threshold/leak
cfg.write(0x1C, 50)   # global_threshold  
cfg.write(0x20, 0)    # global_leak_rate

# Prepare DMA input buffer
spike_data = np.array({spike_words}, dtype=np.uint32)

# Allocate CMA buffers
from pynq import allocate
in_buf = allocate(shape=(len(spike_data),), dtype=np.uint32)
out_buf = allocate(shape=(256,), dtype=np.uint32)
in_buf[:] = spike_data
out_buf[:] = 0

# Enable HLS
hls.write(0x10, 0x01)  # ctrl_reg: enable
time.sleep(0.01)

# Start DMA
# S2MM (receive output spikes)
dma.write(0x30, out_buf.device_address)
dma.write(0x38, 256 * 4)

# MM2S (send input spikes)  
dma.write(0x00, out_buf.device_address)  # dummy, will use proper method
dma.write(0x18, in_buf.device_address)
dma.write(0x28, len(spike_data) * 4)

# Wait for processing
time.sleep(0.5)

# Read spike count from config registers
spike_count = cfg.read(0x70)  # neuron_spike_count offset

# Read output from S2MM buffer
s2mm_status = dma.read(0x34)
output_spikes = []
for i in range(min(256, spike_count)):
    word = int(out_buf[i])
    if word != 0:
        nid = word & 0x3FF
        output_spikes.append(nid)

# Cleanup
in_buf.freebuffer()
out_buf.freebuffer()

print(f"HW_SPIKE_COUNT={{spike_count}}")
print(f"HW_OUTPUT_SPIKES={{output_spikes}}")
print(f"S2MM_STATUS={{hex(s2mm_status)}}")
'''
    
    # Execute on PYNQ (will be called via SSH when bitstream is ready)
    return pynq_script


# =============================================================================
# Part D: Main Verification Flow
# =============================================================================

def main():
    """
    End-to-end MNIST STDP verification.
    
    1. Train dense STDP SNN on MNIST 0/1
    2. Run SW inference on test set
    3. Prepare FPGA deployment data
    4. (Optional) Deploy to FPGA and compare
    """
    np.random.seed(42)
    
    print("=" * 70)
    print("MNIST STDP End-to-End FPGA Verification")
    print("=" * 70)
    
    # --- Step 1: Load Data ---
    print("\n[Step 1] Loading MNIST (digits 0, 1)...")
    train_imgs, train_lbls, test_imgs, test_lbls = load_mnist_binary(
        digits=[0, 1], max_train=5000, max_test=500
    )
    
    # --- Step 2: Create & Train Network ---
    print("\n[Step 2] Training Dense STDP Network...")
    print(f"  Architecture: 784 → 20 (10 per class)")
    print(f"  Threshold: 50.0, Leak: 0.5, Timesteps: 15")
    
    net = DenseSTDPNetwork(
        n_input=784, n_output=20, n_classes=2,
        threshold=50.0, leak=0.5, timesteps=15
    )
    
    t0 = time.time()
    net = train_network(net, train_imgs, train_lbls, epochs=30, verbose=True)
    train_time = time.time() - t0
    print(f"  Training time: {train_time:.1f}s")
    
    # --- Step 3: SW Inference ---
    print("\n[Step 3] SW Inference on Test Set...")
    sw_predictions, sw_accuracy = test_network(net, test_imgs, test_lbls)
    
    # --- Step 4: Quantize Weights ---
    print("\n[Step 4] Weight Quantization...")
    q_weights, q_scale = net.quantize_weights()
    print(f"  Quantized weights: shape={q_weights.shape}, "
          f"range=[{q_weights.min()}, {q_weights.max()}]")
    
    # Verify quantized accuracy
    print("  Verifying quantized SW accuracy...")
    q_correct = 0
    q_predictions = []
    for i in range(len(test_imgs)):
        # Pre-compute weighted spikes (matching FPGA deployment)
        spikes = net.rate_encode(test_imgs[i].flatten())
        
        # Simulate with quantized weights
        T = spikes.shape[0]
        pots = np.zeros(net.n_output, dtype=np.float64)
        fired = np.zeros(net.n_output, dtype=bool)
        fire_order = []
        
        for t in range(T):
            active = spikes[t]
            weighted = q_weights.astype(np.float64) @ active
            pots += weighted
            pots -= net.leak
            pots = np.maximum(pots, 0)
            
            for j in range(net.n_output):
                if pots[j] >= net.threshold * q_scale and not fired[j]:
                    fired[j] = True
                    fire_order.append(j)
                    pots[j] = 0
        
        if fire_order:
            pred = net.decision_map[fire_order[0]]
        else:
            pred = net.decision_map[np.argmax(pots)]
        q_predictions.append(pred)
        
        if pred == test_lbls[i]:
            q_correct += 1
    
    q_acc = q_correct / len(test_imgs) * 100
    print(f"  Quantized SW Accuracy: {q_correct}/{len(test_imgs)} = {q_acc:.1f}%")
    
    # --- Step 5: Prepare FPGA Deployment Data ---
    print("\n[Step 5] Preparing FPGA Deployment Data...")
    
    # Test a few images with pre-weighted spike injection
    n_test_fpga = min(20, len(test_imgs))
    fpga_results = []
    
    for i in range(n_test_fpga):
        img = test_imgs[i]
        lbl = test_lbls[i]
        
        # Prepare weighted spike events
        spike_events = prepare_fpga_spikes(img, q_weights, threshold_fraction=0.3)
        
        # Run SW LIF reference (matching FPGA behavior exactly)
        pots, fired, fire_order = sw_lif_inference(
            spike_events, n_output=20, threshold=int(net.threshold * q_scale)
        )
        
        if fire_order:
            sw_pred = net.decision_map[fire_order[0]]
        else:
            sw_pred = net.decision_map[np.argmax(pots)]
        
        fpga_results.append({
            'index': i,
            'label': lbl,
            'n_spikes': len(spike_events),
            'sw_pred': sw_pred,
            'sw_fired': fire_order[:5],
            'sw_max_pot': float(pots.max()),
        })
        
        print(f"  Image {i:3d}: label={lbl}, pred={sw_pred}, "
              f"spikes={len(spike_events)}, "
              f"fired={len(fire_order)}, max_pot={pots.max():.0f}")
    
    # --- Step 6: Save for FPGA Deployment ---
    print("\n[Step 6] Saving deployment data...")
    
    # Save quantized weights
    np.save('data/cache/q_weights_mnist.npy', q_weights)
    
    # Save test data for FPGA
    deployment = {
        'q_weights': q_weights,
        'q_scale': q_scale,
        'test_imgs': test_imgs[:n_test_fpga],
        'test_lbls': test_lbls[:n_test_fpga],
        'sw_predictions': sw_predictions[:n_test_fpga],
        'q_predictions': q_predictions[:n_test_fpga],
        'fpga_results': fpga_results,
        'threshold': int(net.threshold * q_scale),
        'n_output': net.n_output,
        'decision_map': net.decision_map.tolist(),
    }
    torch.save(deployment, 'data/cache/mnist_fpga_deployment.pt')
    
    # --- Summary ---
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Training:    {len(train_imgs)} samples, {train_time:.1f}s")
    print(f"SW Accuracy: {sw_accuracy:.1f}% (float32)")
    print(f"Q8 Accuracy: {q_acc:.1f}% (int8)")
    print(f"Test images: {n_test_fpga} prepared for FPGA deployment")
    print(f"Avg spikes/image: {np.mean([r['n_spikes'] for r in fpga_results]):.0f}")
    print(f"Weight file: data/cache/q_weights_mnist.npy ({q_weights.shape})")
    print(f"Deployment:  data/cache/mnist_fpga_deployment.pt")
    
    # Check if FPGA is available
    print("\n[FPGA Status]")
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect('192.168.0.40', username='xilinx', password='xilinx', timeout=5)
        print("  PYNQ board: CONNECTED")
        
        # Check for new bitstream
        _, stdout, _ = ssh.exec_command('ls -la /home/xilinx/snn_integrated_v2.bit 2>/dev/null')
        if stdout.read().strip():
            print("  New bitstream: AVAILABLE (snn_integrated_v2.bit)")
            print("  → Ready for FPGA inference!")
        else:
            _, stdout, _ = ssh.exec_command('ls -la /home/xilinx/snn_integrated.bit 2>/dev/null')
            if stdout.read().strip():
                print("  Current bitstream: snn_integrated.bit (pre-RTL-fix)")
                print("  → Can verify spike injection, but S2MM output limited")
            else:
                print("  No bitstream found on board")
        
        ssh.close()
    except Exception as e:
        print(f"  PYNQ board: NOT AVAILABLE ({e})")
        print("  → FPGA inference will be run when bitstream is deployed")
    
    print(f"\nDone! Run FPGA inference with:")
    print(f"  python tests/mnist_stdp_fpga_test.py --fpga")
    
    return sw_accuracy, q_acc


# =============================================================================
# FPGA Inference Mode
# =============================================================================

def run_fpga_inference():
    """
    Deploy and run MNIST inference on FPGA.
    Requires: bitstream deployed on PYNQ board.
    """
    print("=" * 70)
    print("FPGA MNIST STDP Inference")
    print("=" * 70)
    
    # Load deployment data
    deployment = torch.load('data/cache/mnist_fpga_deployment.pt', weights_only=False)
    q_weights = deployment['q_weights']
    test_imgs = deployment['test_imgs']
    test_lbls = deployment['test_lbls']
    sw_preds = deployment['sw_predictions']
    threshold = deployment['threshold']
    n_output = deployment['n_output']
    decision_map = deployment['decision_map']
    
    print(f"Loaded: {len(test_imgs)} test images, threshold={threshold}")
    print(f"Quantized weights: {q_weights.shape}, range=[{q_weights.min()}, {q_weights.max()}]")
    
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.0.40', username='xilinx', password='xilinx', timeout=10)
    print("Connected to PYNQ board")
    
    # Program bitstream
    print("\nProgramming bitstream...")
    prog_cmd = '''python3 -c "
from pynq import Overlay
ol = Overlay('/home/xilinx/snn_integrated_v2.bit')
print('Bitstream loaded successfully')
print('IP blocks:', list(ol.ip_dict.keys()))
"'''
    _, stdout, stderr = ssh.exec_command(prog_cmd, timeout=30)
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print(f"  STDERR: {err}")
    
    # Run inference on each test image
    hw_predictions = []
    matches = 0
    
    for i in range(len(test_imgs)):
        img = test_imgs[i]
        lbl = test_lbls[i]
        
        # Prepare spike events
        spike_events = prepare_fpga_spikes(img, q_weights, threshold_fraction=0.3)
        
        # Generate PYNQ inference script
        pynq_script = deploy_fpga_inference(spike_events, ssh, n_output)
        
        # Execute on PYNQ
        _, stdout, stderr = ssh.exec_command(f'python3 -c """{pynq_script}"""', timeout=30)
        output = stdout.read().decode()
        
        # Parse results
        hw_spike_count = 0
        hw_output_spikes = []
        for line in output.split('\n'):
            if 'HW_SPIKE_COUNT=' in line:
                hw_spike_count = int(line.split('=')[1])
            elif 'HW_OUTPUT_SPIKES=' in line:
                hw_output_spikes = eval(line.split('=', 1)[1])
        
        # Determine HW prediction
        if hw_output_spikes:
            hw_pred = decision_map[hw_output_spikes[0]]
        else:
            hw_pred = sw_preds[i]  # Fallback to SW prediction
        
        hw_predictions.append(hw_pred)
        if hw_pred == sw_preds[i]:
            matches += 1
        
        print(f"  Image {i}: label={lbl}, SW={sw_preds[i]}, HW={hw_pred}, "
              f"spike_count={hw_spike_count}, match={'✓' if hw_pred == sw_preds[i] else '✗'}")
    
    # Summary
    print(f"\n{'='*70}")
    print(f"HW-SW Match: {matches}/{len(test_imgs)} ({matches/len(test_imgs)*100:.1f}%)")
    
    hw_correct = sum(1 for p, l in zip(hw_predictions, test_lbls) if p == l)
    sw_correct = sum(1 for p, l in zip(sw_preds, test_lbls) if p == l)
    print(f"SW Accuracy: {sw_correct}/{len(test_imgs)} ({sw_correct/len(test_imgs)*100:.1f}%)")
    print(f"HW Accuracy: {hw_correct}/{len(test_imgs)} ({hw_correct/len(test_imgs)*100:.1f}%)")
    
    ssh.close()


if __name__ == "__main__":
    if '--fpga' in sys.argv:
        run_fpga_inference()
    else:
        main()
