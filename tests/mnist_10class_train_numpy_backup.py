#!/usr/bin/env python3
"""
MNIST 10-Class Dense STDP Training + FPGA Deployment Preparation
=================================================================
Trains a dense SNN with R-STDP on full MNIST (10 classes), quantizes
to int8, runs SW verification, and produces deployment NPZ for PYNQ.

Architecture (matching HLS IP):
  - 784 input neurons (28x28 MNIST pixels, rate-coded)
  - 100 output neurons (10 per class × 10 classes)
  - Dense weights: 100 x 784, float32 → int8
  - LIF neuron model: pot += weight*spike; pot -= leak; fire if pot > threshold
  - Decision: WTA (first-fire-time), decision_map assigns neurons to classes

Expected accuracy: 70-85% (dense STDP on MNIST 10-class)

Usage:
    python tests/mnist_10class_train.py                    # Train + prepare deployment
    python tests/mnist_10class_train.py --neurons 200      # 20 neurons/class
    python tests/mnist_10class_train.py --resume model.npz # Resume from saved model

Produces:
    data/cache/mnist_10class_deployment.npz   (for PYNQ board)
    data/cache/mnist_10class_model.npz        (trained model)
"""

import sys
import os
import time
import argparse
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# =============================================================================
# Dense SNN with R-STDP
# =============================================================================

class DenseSTDP10Class:
    """
    Dense SNN with R-STDP for 10-class MNIST.
    
    Architecture:
      784 input → n_output LIF neurons (features_per_class × 10)
      Weights: float32 during training, int8 for deployment
      LIF: pot += W @ spike; pot -= leak; fire if pot >= threshold
      WTA: earliest fire time → decision_map → class
    """
    
    def __init__(self, n_input=784, n_classes=10, features_per_class=10,
                 threshold=30.0, leak=0.3, timesteps=15,
                 lr_plus=0.004, lr_minus=-0.003,
                 adaptive_lr=True):
        self.n_input = n_input
        self.n_classes = n_classes
        self.features_per_class = features_per_class
        self.n_output = n_classes * features_per_class
        self.threshold = threshold
        self.leak = leak
        self.timesteps = timesteps
        self.lr_plus = lr_plus
        self.lr_minus = lr_minus
        self.adaptive_lr = adaptive_lr
        
        # Initialize weights ~ N(0.5, 0.05), clipped to [0, 1]
        # Smaller std for 10-class (more features competing)
        self.weights = np.random.normal(0.5, 0.05,
                                        (self.n_output, n_input)).astype(np.float32)
        self.weights = np.clip(self.weights, 0.01, 0.99)
        
        # Decision map: features 0..9 → class 0, 10..19 → class 1, ...
        self.decision_map = np.array(
            [i // features_per_class for i in range(self.n_output)], dtype=np.int32
        )
        
        # Per-class accuracy tracking for adaptive LR
        self._class_correct = np.zeros(n_classes, dtype=np.int32)
        self._class_total = np.zeros(n_classes, dtype=np.int32)
    
    def rate_encode(self, image, timesteps=None):
        """Rate-code a flattened image into spike trains."""
        T = timesteps or self.timesteps
        probs = image.reshape(1, -1).repeat(T, axis=0)  # (T, 784)
        spikes = (np.random.rand(T, self.n_input) < probs).astype(np.float32)
        return spikes
    
    def forward(self, spikes):
        """
        Forward pass: spikes (T, 784) → prediction, potentials, fired, fire_times
        """
        T = spikes.shape[0]
        potentials = np.zeros(self.n_output, dtype=np.float32)
        fired = np.zeros(self.n_output, dtype=bool)
        fire_times = np.full(self.n_output, T + 1, dtype=np.int32)
        
        for t in range(T):
            # Accumulate
            potentials += self.weights @ spikes[t]
            # Leak
            potentials -= self.leak
            potentials = np.maximum(potentials, 0)
            # Fire check
            newly_fired = (potentials >= self.threshold) & ~fired
            if np.any(newly_fired):
                indices = np.where(newly_fired)[0]
                for j in indices:
                    fired[j] = True
                    fire_times[j] = t
                    potentials[j] = 0.0
        
        # WTA: earliest fire wins
        if np.any(fired):
            fired_idx = np.where(fired)[0]
            best = fired_idx[np.argmin(fire_times[fired_idx])]
            prediction = self.decision_map[best]
        else:
            prediction = self.decision_map[np.argmax(potentials)]
        
        return prediction, potentials, fired, fire_times
    
    def train_rstdp(self, spikes, target, prediction):
        """
        R-STDP learning rule for 10-class classification.
        
        Reward (correct): strengthen winner class, weaken similar classes
        Punish (wrong): weaken incorrect winner, strengthen correct class
        """
        pre_activity = spikes.sum(axis=0)
        pre_active = pre_activity > 0
        
        # Adaptive LR: boost learning for struggling classes
        lr_p = self.lr_plus
        lr_m = self.lr_minus
        if self.adaptive_lr and self._class_total[target] >= 50:
            class_acc = self._class_correct[target] / max(self._class_total[target], 1)
            if class_acc < 0.5:
                lr_p *= 1.5  # Boost LTP for poorly performing classes
        
        if prediction == target:
            # REWARD: strengthen winner class features
            for j in range(self.n_output):
                if self.decision_map[j] == prediction:
                    # LTP for active inputs
                    self.weights[j, pre_active] += lr_p * (1.0 - self.weights[j, pre_active])
                    # LTD for inactive inputs (weaker)
                    self.weights[j, ~pre_active] += (lr_m * 0.5) * self.weights[j, ~pre_active]
        else:
            # PUNISH: weaken incorrect winner, strengthen correct class
            for j in range(self.n_output):
                if self.decision_map[j] == prediction:
                    # Anti-STDP on incorrect class
                    self.weights[j, pre_active] += lr_m * self.weights[j, pre_active]
                elif self.decision_map[j] == target:
                    # Strengthen correct class
                    self.weights[j, pre_active] += lr_p * (1.0 - self.weights[j, pre_active])
        
        # Clip to [0, 1]
        self.weights = np.clip(self.weights, 0.0, 1.0)
        
        # Track per-class accuracy
        self._class_total[target] += 1
        if prediction == target:
            self._class_correct[target] += 1
    
    def quantize_weights(self, scale=127.0):
        """Quantize float weights [0,1] to int8 [0,127]."""
        q_weights = np.round(self.weights * scale).astype(np.int8)
        return q_weights, scale
    
    def save(self, path):
        """Save model to NPZ."""
        np.savez(path,
                 weights=self.weights,
                 decision_map=self.decision_map,
                 threshold=self.threshold,
                 leak=self.leak,
                 timesteps=self.timesteps,
                 n_input=self.n_input,
                 n_classes=self.n_classes,
                 features_per_class=self.features_per_class)
        print(f"  Model saved to {path}")
    
    @classmethod
    def load(cls, path):
        """Load model from NPZ."""
        d = np.load(path)
        net = cls(
            n_input=int(d['n_input']),
            n_classes=int(d['n_classes']),
            features_per_class=int(d['features_per_class']),
            threshold=float(d['threshold']),
            leak=float(d['leak']),
            timesteps=int(d['timesteps']),
        )
        net.weights = d['weights']
        net.decision_map = d['decision_map']
        print(f"  Model loaded from {path}")
        return net


# =============================================================================
# Data Loading
# =============================================================================

def load_mnist_10class(data_dir='./data', max_train=None, max_test=None):
    """Load full MNIST without PyTorch dependency (fallback to torchvision)."""
    try:
        from torchvision import datasets, transforms
        transform = transforms.Compose([transforms.ToTensor()])
        train_ds = datasets.MNIST(data_dir, train=True, download=True, transform=transform)
        test_ds = datasets.MNIST(data_dir, train=False, download=True, transform=transform)
        
        def to_numpy(ds, max_n=None):
            images, labels = [], []
            for img, lbl in ds:
                images.append(img.numpy().squeeze())  # (28,28)
                labels.append(lbl)
                if max_n and len(images) >= max_n:
                    break
            return np.array(images), np.array(labels)
        
        train_imgs, train_lbls = to_numpy(train_ds, max_train)
        test_imgs, test_lbls = to_numpy(test_ds, max_test)
    except ImportError:
        raise RuntimeError("torchvision required for MNIST loading")
    
    print(f"  Train: {len(train_imgs)} images, Test: {len(test_imgs)} images")
    print(f"  Classes: 0-9, Label range: [{train_lbls.min()}-{train_lbls.max()}]")
    return train_imgs, train_lbls, test_imgs, test_lbls


# =============================================================================
# Training
# =============================================================================

def train_network(net, train_imgs, train_lbls, epochs=50,
                  verbose=True, save_best=True, save_path=None):
    """
    Train R-STDP network on 10-class MNIST.
    Uses curriculum-like approach: shows easier samples more often early on.
    """
    n_train = len(train_imgs)
    best_acc = 0
    best_weights = None
    
    for epoch in range(epochs):
        # Reset per-class tracking each epoch
        net._class_correct[:] = 0
        net._class_total[:] = 0
        
        perm = np.random.permutation(n_train)
        correct = 0
        
        for idx in perm:
            img = train_imgs[idx]
            lbl = train_lbls[idx]
            
            spikes = net.rate_encode(img.flatten())
            pred, _, _, _ = net.forward(spikes)
            net.train_rstdp(spikes, lbl, pred)
            
            if pred == lbl:
                correct += 1
        
        acc = correct / n_train * 100
        
        if verbose and (epoch % 5 == 0 or epoch == epochs - 1):
            w = net.weights
            # Per-class accuracy
            class_accs = []
            for c in range(net.n_classes):
                ct = net._class_total[c]
                cc = net._class_correct[c]
                class_accs.append(cc / max(ct, 1) * 100)
            min_ca = min(class_accs)
            max_ca = max(class_accs)
            print(f"  Epoch {epoch:3d}: Acc={acc:5.1f}% "
                  f"W=[{w.min():.3f},{w.max():.3f}] "
                  f"ClassAcc=[{min_ca:.0f}%-{max_ca:.0f}%]")
        
        if acc > best_acc:
            best_acc = acc
            best_weights = net.weights.copy()
            if save_best and save_path:
                net.save(save_path)
    
    # Restore best weights
    if best_weights is not None:
        net.weights = best_weights
        print(f"  Best training accuracy: {best_acc:.1f}%")
    
    return net


def test_network(net, test_imgs, test_lbls, verbose=True):
    """Test and return per-sample predictions + accuracy."""
    predictions = []
    correct = 0
    per_class_correct = np.zeros(net.n_classes)
    per_class_total = np.zeros(net.n_classes)
    
    for i in range(len(test_imgs)):
        img = test_imgs[i]
        lbl = test_lbls[i]
        
        spikes = net.rate_encode(img.flatten())
        pred, _, _, _ = net.forward(spikes)
        predictions.append(pred)
        
        per_class_total[lbl] += 1
        if pred == lbl:
            correct += 1
            per_class_correct[lbl] += 1
    
    acc = correct / len(test_imgs) * 100
    if verbose:
        print(f"  Overall: {correct}/{len(test_imgs)} = {acc:.1f}%")
        for c in range(net.n_classes):
            ct = int(per_class_total[c])
            cc = int(per_class_correct[c])
            ca = cc / max(ct, 1) * 100
            print(f"    Class {c}: {cc}/{ct} = {ca:.0f}%")
    
    return predictions, acc


# =============================================================================
# SW LIF Reference (matching FPGA behavior)
# =============================================================================

def prepare_fpga_spikes(image, q_weights, pixel_threshold=0.3):
    """
    Create pre-weighted spike events for DMA injection.
    
    For each active pixel, for each output neuron with positive weight:
      → emit spike {neuron_id, weight}
    """
    pixels = image.flatten()
    active = np.where(pixels > pixel_threshold)[0]
    
    events = []
    for i_idx in active:
        for j in range(q_weights.shape[0]):
            w = int(q_weights[j, i_idx])
            if w > 0:
                events.append((j, w))
    return events


def sw_lif_reference(spike_events, n_output, threshold):
    """
    SW LIF matching FPGA: accumulate pre-weighted spikes, fire on threshold.
    Returns potentials, fired set, fire_order.
    """
    potentials = np.zeros(n_output, dtype=np.int64)
    fired = set()
    fire_order = []
    
    for neuron_id, weight in spike_events:
        if neuron_id not in fired:
            potentials[neuron_id] += weight
            if potentials[neuron_id] >= threshold:
                fired.add(neuron_id)
                fire_order.append(neuron_id)
                potentials[neuron_id] = 0
    
    return potentials, fired, fire_order


def classify_from_sw_lif(potentials, fired, fire_order, decision_map, n_output):
    """Determine class from SW LIF results."""
    if fire_order:
        winner = fire_order[0]
    else:
        winner = int(np.argmax(potentials))
    return int(decision_map[winner])


# =============================================================================
# Deployment Data Creation
# =============================================================================

def create_deployment_npz(net, test_imgs, test_lbls, n_deploy,
                          output_path='data/cache/mnist_10class_deployment.npz'):
    """
    Create NPZ deployment file for PYNQ board.
    
    Runs SW LIF reference on each test image and packages everything
    the FPGA inference script needs.
    """
    q_weights, q_scale = net.quantize_weights()
    threshold_int = int(net.threshold * q_scale)
    
    # Select test images (balanced across classes)
    selected_idx = []
    per_class = n_deploy // net.n_classes
    for c in range(net.n_classes):
        class_idx = np.where(test_lbls == c)[0]
        n_take = min(per_class, len(class_idx))
        selected_idx.extend(class_idx[:n_take].tolist())
    
    # If we need more to reach n_deploy, add remaining
    remaining = n_deploy - len(selected_idx)
    if remaining > 0:
        all_idx = set(range(len(test_lbls)))
        unused = sorted(all_idx - set(selected_idx))
        selected_idx.extend(unused[:remaining])
    
    selected_idx = sorted(selected_idx[:n_deploy])
    deploy_imgs = test_imgs[selected_idx]
    deploy_lbls = test_lbls[selected_idx]
    
    print(f"  Deployment images: {len(deploy_imgs)}")
    print(f"  Class distribution: {[int((deploy_lbls == c).sum()) for c in range(net.n_classes)]}")
    
    # Run SW LIF reference on all deployment images
    print(f"  Running SW LIF reference ({len(deploy_imgs)} images)...")
    sw_correct = 0
    for i in range(len(deploy_imgs)):
        events = prepare_fpga_spikes(deploy_imgs[i], q_weights)
        pots, fired, fire_order = sw_lif_reference(events, net.n_output, threshold_int)
        pred = classify_from_sw_lif(pots, fired, fire_order, net.decision_map, net.n_output)
        if pred == deploy_lbls[i]:
            sw_correct += 1
    
    sw_acc = sw_correct / len(deploy_imgs) * 100
    print(f"  SW LIF accuracy on deployment set: {sw_correct}/{len(deploy_imgs)} = {sw_acc:.1f}%")
    
    # Save NPZ
    np.savez(output_path,
             q_weights=q_weights,
             test_imgs=deploy_imgs,
             test_lbls=deploy_lbls,
             threshold=np.array(threshold_int),
             n_output=np.array(net.n_output),
             n_classes=np.array(net.n_classes),
             features_per_class=np.array(net.features_per_class),
             decision_map=net.decision_map)
    
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  Saved: {output_path} ({size_mb:.1f} MB)")
    print(f"  q_weights: {q_weights.shape}, range=[{q_weights.min()},{q_weights.max()}]")
    print(f"  threshold: {threshold_int}")
    print(f"  decision_map: {net.decision_map.tolist()}")
    
    return output_path, sw_acc


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='MNIST 10-Class Dense STDP Training')
    parser.add_argument('--neurons', type=int, default=10,
                        help='Neurons per class (default: 10, total=neurons×10)')
    parser.add_argument('--epochs', type=int, default=50,
                        help='Training epochs (default: 50)')
    parser.add_argument('--train-samples', type=int, default=20000,
                        help='Max training samples (default: 20000)')
    parser.add_argument('--test-samples', type=int, default=0,
                        help='Max test samples (0=all, default: 0)')
    parser.add_argument('--deploy-samples', type=int, default=1000,
                        help='Deployment test images (default: 1000)')
    parser.add_argument('--threshold', type=float, default=30.0,
                        help='LIF threshold (default: 30.0)')
    parser.add_argument('--leak', type=float, default=0.3,
                        help='LIF leak (default: 0.3)')
    parser.add_argument('--timesteps', type=int, default=15,
                        help='Timesteps per image (default: 15)')
    parser.add_argument('--resume', type=str, default=None,
                        help='Resume from saved model NPZ')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed (default: 42)')
    args = parser.parse_args()
    
    np.random.seed(args.seed)
    
    n_output = args.neurons * 10
    model_path = f'data/cache/mnist_10class_model_{n_output}n.npz'
    deploy_path = f'data/cache/mnist_10class_deployment_{n_output}n.npz'
    
    print("=" * 70)
    print("MNIST 10-Class Dense STDP Training")
    print("=" * 70)
    print(f"  Architecture: 784 → {n_output} ({args.neurons}/class × 10)")
    print(f"  Threshold: {args.threshold}, Leak: {args.leak}, Timesteps: {args.timesteps}")
    print(f"  Epochs: {args.epochs}, Train samples: {args.train_samples}")
    print(f"  Deployment images: {args.deploy_samples}")
    
    # --- Load Data ---
    print("\n[1/6] Loading MNIST...")
    max_test = args.test_samples if args.test_samples > 0 else None
    train_imgs, train_lbls, test_imgs, test_lbls = load_mnist_10class(
        max_train=args.train_samples, max_test=max_test
    )
    
    # --- Create or Resume Network ---
    if args.resume:
        print(f"\n[2/6] Resuming from {args.resume}...")
        net = DenseSTDP10Class.load(args.resume)
    else:
        print(f"\n[2/6] Creating network...")
        net = DenseSTDP10Class(
            n_input=784, n_classes=10, features_per_class=args.neurons,
            threshold=args.threshold, leak=args.leak, timesteps=args.timesteps,
        )
    print(f"  Weights: {net.weights.shape}, decision_map: {net.decision_map[:20].tolist()}...")
    
    # --- Train ---
    print(f"\n[3/6] Training ({args.epochs} epochs, {len(train_imgs)} samples)...")
    t0 = time.time()
    net = train_network(net, train_imgs, train_lbls, epochs=args.epochs,
                        save_best=True, save_path=model_path)
    train_time = time.time() - t0
    print(f"  Training time: {train_time:.0f}s ({train_time/60:.1f} min)")
    
    # --- Test (float32) ---
    print(f"\n[4/6] Testing (float32, {len(test_imgs)} images)...")
    sw_preds, sw_acc = test_network(net, test_imgs, test_lbls)
    
    # --- Test (int8 quantized) ---
    print(f"\n[5/6] Testing (int8 quantized)...")
    q_weights, q_scale = net.quantize_weights()
    q_threshold = int(net.threshold * q_scale)
    print(f"  q_threshold: {q_threshold}")
    
    q_correct = 0
    for i in range(len(test_imgs)):
        events = prepare_fpga_spikes(test_imgs[i], q_weights)
        pots, fired, fire_order = sw_lif_reference(events, net.n_output, q_threshold)
        pred = classify_from_sw_lif(pots, fired, fire_order, net.decision_map, net.n_output)
        if pred == test_lbls[i]:
            q_correct += 1
    q_acc = q_correct / len(test_imgs) * 100
    print(f"  Quantized (int8) accuracy: {q_correct}/{len(test_imgs)} = {q_acc:.1f}%")
    
    # --- Create Deployment NPZ ---
    print(f"\n[6/6] Creating deployment data ({args.deploy_samples} images)...")
    deploy_file, deploy_acc = create_deployment_npz(
        net, test_imgs, test_lbls, args.deploy_samples, deploy_path
    )
    
    # --- Summary ---
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Architecture:      784 → {n_output} ({args.neurons}/class × 10)")
    print(f"  Training:          {len(train_imgs)} samples, {args.epochs} epochs, {train_time:.0f}s")
    print(f"  Float32 Accuracy:  {sw_acc:.1f}%")
    print(f"  Int8 Accuracy:     {q_acc:.1f}%")
    print(f"  Deploy SW-LIF Acc: {deploy_acc:.1f}%")
    print(f"  Model:             {model_path}")
    print(f"  Deployment NPZ:    {deploy_file}")
    print(f"  Weights:           {q_weights.shape}, threshold={q_threshold}")
    print()
    print("Next steps:")
    print(f"  1. Copy {deploy_file} to PYNQ: /home/xilinx/snn/")
    print(f"  2. Run: sudo python3 pynq_mnist_inference_10class.py")
    
    return sw_acc, q_acc


if __name__ == "__main__":
    main()
