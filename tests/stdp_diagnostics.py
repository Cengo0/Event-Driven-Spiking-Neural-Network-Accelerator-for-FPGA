#!/usr/bin/env python3
"""
STDP Diagnostics: Compare SW Int8 and On-Chip STDP distributions.
=================================================================

Analyzes weight distributions, spike patterns, firing rates, threshold
dynamics, and per-class activation to identify gaps between the SW
reference model and the HLS on-chip STDP simulation.

Usage:
    python tests/stdp_diagnostics.py
    python tests/stdp_diagnostics.py --sw-model data/cache/mnist_10class_model_150n.npz
    python tests/stdp_diagnostics.py --onchip-model data/cache/onchip_stdp_model_150n.npz

Author: Jiwoon Lee (@metr0jw)
"""

import sys, os, argparse
import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


def load_test_data(n_samples=2000):
    """Load MNIST test data."""
    from torchvision import datasets, transforms
    ds = datasets.MNIST('./data', train=False, download=True,
                        transform=transforms.ToTensor())
    imgs, lbls = [], []
    for img, lbl in ds:
        imgs.append(img.squeeze(0))
        lbls.append(lbl)
        if len(imgs) >= n_samples:
            break
    return torch.stack(imgs), torch.tensor(lbls, dtype=torch.long)


def analyze_weight_distribution(weights, name, n_classes=10, fpc=15):
    """Analyze weight matrix distribution."""
    w = weights if isinstance(weights, np.ndarray) else weights.cpu().numpy()
    if w.dtype in (np.float32, np.float64):
        w_display = w
    else:
        w_display = w.astype(np.float32)

    stats = {
        'name': name,
        'shape': w.shape,
        'min': float(w_display.min()),
        'max': float(w_display.max()),
        'mean': float(w_display.mean()),
        'std': float(w_display.std()),
        'median': float(np.median(w_display)),
        'zeros_pct': float((w_display == 0).sum() / w_display.size * 100),
        'saturated_pct': float((w_display >= w_display.max() * 0.95).sum() / w_display.size * 100),
    }

    # Per-neuron stats
    # Handle layout: SW is (n_out, 784), On-Chip is (784, n_out)
    if w.shape[0] < w.shape[1]:
        # (n_out, 784) - SW layout
        per_neuron_mean = w_display.mean(axis=1)
        per_neuron_std = w_display.std(axis=1)
        per_neuron_l2 = np.linalg.norm(w_display, axis=1)
        per_neuron_l1 = np.abs(w_display).sum(axis=1)
    else:
        # (784, n_out) - On-chip layout
        per_neuron_mean = w_display.mean(axis=0)
        per_neuron_std = w_display.std(axis=0)
        per_neuron_l2 = np.linalg.norm(w_display, axis=0)
        per_neuron_l1 = np.abs(w_display).sum(axis=0)

    stats['neuron_mean_range'] = (float(per_neuron_mean.min()), float(per_neuron_mean.max()))
    stats['neuron_std_range'] = (float(per_neuron_std.min()), float(per_neuron_std.max()))
    stats['neuron_l2_range'] = (float(per_neuron_l2.min()), float(per_neuron_l2.max()))
    stats['neuron_l1_range'] = (float(per_neuron_l1.min()), float(per_neuron_l1.max()))
    stats['neuron_mean_mean'] = float(per_neuron_mean.mean())
    stats['neuron_l2_mean'] = float(per_neuron_l2.mean())

    # Per-class stats
    n_neurons = len(per_neuron_mean)
    if fpc > 0 and n_neurons == n_classes * fpc:
        class_means = []
        for c in range(n_classes):
            s, e = c * fpc, (c + 1) * fpc
            class_means.append(float(per_neuron_mean[s:e].mean()))
        stats['class_weight_means'] = class_means

    # Histogram bins (10 bins)
    hist, edges = np.histogram(w_display.flatten(), bins=20)
    stats['histogram'] = (hist.tolist(), edges.tolist())

    return stats


def analyze_spike_patterns(model, test_imgs, test_lbls, model_type='onchip',
                           n_samples=500, device=DEVICE):
    """Analyze spike counts, firing rates, and activation patterns."""
    flat = test_imgs[:n_samples].reshape(n_samples, -1).to(device).float()
    lbls = test_lbls[:n_samples].to(device)

    results = {
        'n_samples': n_samples,
        'model_type': model_type,
    }

    if model_type == 'onchip':
        from tests.onchip_stdp_experiment import OnChipSTDPTrainerGPU
        trainer = model

        # Use fixed seed for reproducibility
        rng_state = torch.random.get_rng_state()
        cuda_state = torch.cuda.get_rng_state() if torch.cuda.is_available() else None
        torch.manual_seed(12345)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(12345)

        w_float = trainer.engine.weights.float().clamp(min=0)
        thr_f = trainer.per_neuron_thr.float().unsqueeze(0)
        T = trainer.timesteps
        n_out = trainer.n_output

        all_spike_counts = []       # per-image input spike count
        all_fire_counts = []        # per-image output fire count
        all_max_potentials = []     # per-image max potential
        all_preds = []
        per_neuron_fires = torch.zeros(n_out, device=device)
        per_neuron_first_fire = torch.zeros(n_out, device=device)
        per_neuron_total_pot = torch.zeros(n_out, device=device)

        batch_size = 256
        for start in range(0, n_samples, batch_size):
            end = min(start + batch_size, n_samples)
            batch = flat[start:end]
            B = batch.shape[0]

            spikes = trainer._encode_spikes_batch(batch)

            # Detailed forward
            pots = torch.zeros(B, n_out, device=device)
            ftimes = torch.full((B, n_out), T + 1, dtype=torch.float32, device=device)
            bi = torch.arange(B, device=device)

            for t in range(T):
                pots.addmm_(spikes[:, t].float(), w_float)
                pots.sub_(trainer.leak)
                pots.clamp_(min=0)

                above = (pots >= thr_f) & (ftimes > T)
                pot_masked = pots.masked_fill(~above, -1.0)
                batch_winners = pot_masked.argmax(dim=1)
                has_winner = above.any(dim=1)
                w_idx = batch_winners[has_winner]
                b_idx = bi[has_winner]
                ftimes[b_idx, w_idx] = float(t)
                pots[has_winner] = 0

            fired = ftimes <= T
            per_neuron_fires += fired.float().sum(dim=0)

            # Input spike stats
            input_spike_count = spikes.float().sum(dim=(1, 2))  # (B,)
            all_spike_counts.extend(input_spike_count.cpu().tolist())

            # Output fire stats
            output_fire_count = fired.float().sum(dim=1)  # (B,)
            all_fire_counts.extend(output_fire_count.cpu().tolist())

            # Max potential
            # For samples that fired, max potential is their threshold
            # For no-fire, track actual max potential
            all_max_potentials.extend(pots.max(dim=1).values.cpu().tolist())

            # Predictions
            dm = trainer.decision_map
            preds = torch.empty(B, dtype=torch.long, device=device)
            any_f = fired.any(dim=1)
            ft = ftimes.clone()
            ft[~fired] = T + 2
            first_fire = ft.argmin(dim=1)
            preds[any_f] = dm[first_fire[any_f]]
            if (~any_f).any():
                preds[~any_f] = dm[pots[~any_f].argmax(dim=1)]
            all_preds.extend(preds.cpu().tolist())

        # Restore RNG
        torch.random.set_rng_state(rng_state)
        if cuda_state is not None:
            torch.cuda.set_rng_state(cuda_state)

        preds_t = torch.tensor(all_preds)
        acc = (preds_t == lbls[:n_samples].cpu()).float().mean().item() * 100

        results['accuracy'] = acc
        results['input_spike_count'] = {
            'mean': np.mean(all_spike_counts),
            'std': np.std(all_spike_counts),
        }
        results['output_fire_count'] = {
            'mean': np.mean(all_fire_counts),
            'std': np.std(all_fire_counts),
            'zero_pct': sum(1 for x in all_fire_counts if x == 0) / len(all_fire_counts) * 100,
        }
        results['per_neuron_fire_rate'] = {
            'mean': (per_neuron_fires / n_samples).mean().item(),
            'std': (per_neuron_fires / n_samples).std().item(),
            'min': (per_neuron_fires / n_samples).min().item(),
            'max': (per_neuron_fires / n_samples).max().item(),
            'dead_neurons': int((per_neuron_fires == 0).sum().item()),
        }
        results['threshold'] = {
            'mean': trainer.per_neuron_thr.mean().item(),
            'std': trainer.per_neuron_thr.std().item(),
            'min': trainer.per_neuron_thr.min().item(),
            'max': trainer.per_neuron_thr.max().item(),
        }

        # Per-class accuracy
        per_class = {}
        for c in range(10):
            mask = lbls[:n_samples].cpu() == c
            if mask.any():
                per_class[c] = (preds_t[mask] == c).float().mean().item() * 100
        results['per_class_accuracy'] = per_class

    elif model_type == 'sw':
        from tests.mnist_10class_train import DenseSTDP10Class
        net = model

        rng_state = torch.random.get_rng_state()
        cuda_state = torch.cuda.get_rng_state() if torch.cuda.is_available() else None
        torch.manual_seed(12345)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(12345)

        n_out = net.n_output
        all_spike_counts = []
        all_fire_counts = []
        all_preds = []
        per_neuron_fires = torch.zeros(n_out, device=device)

        batch_size = 256
        for start in range(0, n_samples, batch_size):
            end = min(start + batch_size, n_samples)
            batch = flat[start:end]
            B = batch.shape[0]

            spikes = net.rate_encode(batch)
            preds, pots, fired, ftimes = net.forward_batch(spikes)

            per_neuron_fires += fired.float().sum(dim=0)
            all_spike_counts.extend(spikes.sum(dim=(1, 2)).cpu().tolist())
            all_fire_counts.extend(fired.float().sum(dim=1).cpu().tolist())
            all_preds.extend(preds.cpu().tolist())

        torch.random.set_rng_state(rng_state)
        if cuda_state is not None:
            torch.cuda.set_rng_state(cuda_state)

        preds_t = torch.tensor(all_preds)
        acc = (preds_t == lbls[:n_samples].cpu()).float().mean().item() * 100

        results['accuracy'] = acc
        results['input_spike_count'] = {
            'mean': np.mean(all_spike_counts),
            'std': np.std(all_spike_counts),
        }
        results['output_fire_count'] = {
            'mean': np.mean(all_fire_counts),
            'std': np.std(all_fire_counts),
            'zero_pct': sum(1 for x in all_fire_counts if x == 0) / len(all_fire_counts) * 100,
        }
        results['per_neuron_fire_rate'] = {
            'mean': (per_neuron_fires / n_samples).mean().item(),
            'std': (per_neuron_fires / n_samples).std().item(),
            'min': (per_neuron_fires / n_samples).min().item(),
            'max': (per_neuron_fires / n_samples).max().item(),
            'dead_neurons': int((per_neuron_fires == 0).sum().item()),
        }
        results['threshold'] = {
            'mean': net.thresholds.mean().item(),
            'std': net.thresholds.std().item(),
            'min': net.thresholds.min().item(),
            'max': net.thresholds.max().item(),
        }
        per_class = {}
        for c in range(10):
            mask = lbls[:n_samples].cpu() == c
            if mask.any():
                per_class[c] = (preds_t[mask] == c).float().mean().item() * 100
        results['per_class_accuracy'] = per_class

    return results


def print_comparison(sw_weight_stats, oc_weight_stats, sw_spike_stats, oc_spike_stats):
    """Print side-by-side comparison."""
    print("\n" + "=" * 78)
    print("DIAGNOSTIC COMPARISON: SW Int8 Reference vs On-Chip STDP")
    print("=" * 78)

    # --- Weight Distribution ---
    print("\n--- Weight Distribution ---")
    sw, oc = sw_weight_stats, oc_weight_stats
    # Normalize on-chip to [0, 1] scale for comparison
    oc_scale = 127.0  # On-chip max weight

    print(f"{'Metric':<30s} {'SW (float)':<20s} {'On-Chip (int)':<20s} {'On-Chip (norm)':<20s}")
    print("-" * 90)
    print(f"{'Range':<30s} [{sw['min']:.3f}, {sw['max']:.3f}]     "
          f"[{oc['min']:.0f}, {oc['max']:.0f}]          "
          f"[{oc['min']/oc_scale:.3f}, {oc['max']/oc_scale:.3f}]")
    print(f"{'Mean':<30s} {sw['mean']:.3f}               "
          f"{oc['mean']:.1f}               "
          f"{oc['mean']/oc_scale:.3f}")
    print(f"{'Std':<30s} {sw['std']:.3f}               "
          f"{oc['std']:.1f}               "
          f"{oc['std']/oc_scale:.3f}")
    print(f"{'Median':<30s} {sw['median']:.3f}               "
          f"{oc['median']:.1f}               "
          f"{oc['median']/oc_scale:.3f}")
    print(f"{'Zeros %':<30s} {sw['zeros_pct']:.1f}%               "
          f"{oc['zeros_pct']:.1f}%")
    print(f"{'Saturated %':<30s} {sw['saturated_pct']:.1f}%               "
          f"{oc['saturated_pct']:.1f}%")
    print(f"{'Neuron L2 mean':<30s} {sw['neuron_l2_mean']:.1f}               "
          f"{oc['neuron_l2_mean']:.1f}               "
          f"{oc['neuron_l2_mean']/oc_scale:.1f}")
    print(f"{'Neuron mean range':<30s} [{sw['neuron_mean_range'][0]:.3f}, {sw['neuron_mean_range'][1]:.3f}]  "
          f"  [{oc['neuron_mean_range'][0]:.1f}, {oc['neuron_mean_range'][1]:.1f}]")

    # Per-class weight means
    if 'class_weight_means' in sw and 'class_weight_means' in oc:
        print(f"\n  Per-class neuron weight means:")
        print(f"  {'Class':<8s} {'SW':>8s} {'On-Chip':>8s} {'OC norm':>8s}")
        for c in range(10):
            sw_m = sw['class_weight_means'][c]
            oc_m = oc['class_weight_means'][c]
            print(f"  {c:<8d} {sw_m:8.3f} {oc_m:8.1f} {oc_m/oc_scale:8.3f}")

    # --- Spike Patterns ---
    print("\n--- Spike & Firing Patterns ---")
    ss, os_ = sw_spike_stats, oc_spike_stats
    print(f"{'Metric':<35s} {'SW':<20s} {'On-Chip':<20s}")
    print("-" * 75)
    print(f"{'Accuracy':<35s} {ss['accuracy']:.1f}%               {os_['accuracy']:.1f}%")
    print(f"{'Input spikes/image (mean)':<35s} {ss['input_spike_count']['mean']:.0f}"
          f"                {os_['input_spike_count']['mean']:.0f}")
    print(f"{'Output fires/image (mean)':<35s} {ss['output_fire_count']['mean']:.1f}"
          f"                {os_['output_fire_count']['mean']:.1f}")
    print(f"{'No-fire images %':<35s} {ss['output_fire_count']['zero_pct']:.1f}%"
          f"               {os_['output_fire_count']['zero_pct']:.1f}%")
    print(f"{'Per-neuron fire rate (mean)':<35s} {ss['per_neuron_fire_rate']['mean']:.4f}"
          f"             {os_['per_neuron_fire_rate']['mean']:.4f}")
    print(f"{'Per-neuron fire rate (std)':<35s} {ss['per_neuron_fire_rate']['std']:.4f}"
          f"             {os_['per_neuron_fire_rate']['std']:.4f}")
    print(f"{'Dead neurons (never fire)':<35s} {ss['per_neuron_fire_rate']['dead_neurons']}"
          f"                   {os_['per_neuron_fire_rate']['dead_neurons']}")
    print(f"{'Threshold mean':<35s} {ss['threshold']['mean']:.1f}"
          f"              {os_['threshold']['mean']:.1f}")
    print(f"{'Threshold range':<35s} [{ss['threshold']['min']:.1f}, {ss['threshold']['max']:.1f}]"
          f"      [{os_['threshold']['min']:.0f}, {os_['threshold']['max']:.0f}]")

    # Per-class accuracy
    print(f"\n  Per-class accuracy:")
    print(f"  {'Class':<8s} {'SW':>8s} {'On-Chip':>8s} {'Gap':>8s}")
    total_gap = 0
    for c in range(10):
        sw_a = ss['per_class_accuracy'].get(c, 0)
        oc_a = os_['per_class_accuracy'].get(c, 0)
        gap = oc_a - sw_a
        total_gap += abs(gap)
        marker = " <<" if gap < -5 else ""
        print(f"  {c:<8d} {sw_a:7.1f}% {oc_a:7.1f}% {gap:+7.1f}%{marker}")
    print(f"  {'Avg gap':<8s} {'':>8s} {'':>8s} {total_gap/10:7.1f}%")

    # --- Key Observations ---
    print("\n--- Key Observations ---")
    observations = []

    # Weight mean comparison (normalize on-chip to [0,1])
    oc_mean_norm = oc['mean'] / oc_scale
    if abs(oc_mean_norm - sw['mean']) > 0.05:
        observations.append(
            f"Weight mean mismatch: SW={sw['mean']:.3f} vs OC(norm)={oc_mean_norm:.3f} "
            f"(diff={oc_mean_norm - sw['mean']:+.3f})")

    # Weight std comparison
    oc_std_norm = oc['std'] / oc_scale
    if abs(oc_std_norm - sw['std']) > 0.05:
        observations.append(
            f"Weight std mismatch: SW={sw['std']:.3f} vs OC(norm)={oc_std_norm:.3f}")

    # Firing rate
    if abs(ss['per_neuron_fire_rate']['mean'] - os_['per_neuron_fire_rate']['mean']) > 0.01:
        observations.append(
            f"Fire rate mismatch: SW={ss['per_neuron_fire_rate']['mean']:.4f} "
            f"vs OC={os_['per_neuron_fire_rate']['mean']:.4f}")

    # Dead neurons
    if os_['per_neuron_fire_rate']['dead_neurons'] > 5:
        observations.append(
            f"On-Chip has {os_['per_neuron_fire_rate']['dead_neurons']} dead neurons")

    # No-fire images
    if os_['output_fire_count']['zero_pct'] > 5:
        observations.append(
            f"On-Chip has {os_['output_fire_count']['zero_pct']:.1f}% no-fire images")

    # Threshold variance
    thr_cv = os_['threshold']['std'] / max(os_['threshold']['mean'], 1)
    if thr_cv > 0.3:
        observations.append(
            f"On-Chip threshold high variance: CV={thr_cv:.2f}")

    # Weight saturation
    if oc['saturated_pct'] > 5:
        observations.append(f"On-Chip weight saturation: {oc['saturated_pct']:.1f}%")
    if oc['zeros_pct'] > 5:
        observations.append(f"On-Chip zero weights: {oc['zeros_pct']:.1f}%")

    for i, obs in enumerate(observations, 1):
        print(f"  {i}. {obs}")

    if not observations:
        print("  (No significant discrepancies found)")

    return observations


def main():
    ap = argparse.ArgumentParser(description='STDP Diagnostics')
    ap.add_argument('--sw-model', type=str, default=None,
                    help='Path to SW model NPZ (will train if not given)')
    ap.add_argument('--onchip-model', type=str, default=None,
                    help='Path to on-chip STDP model NPZ')
    ap.add_argument('--n-samples', type=int, default=2000)
    ap.add_argument('--neurons', type=int, default=15)
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(args.seed)

    fpc = args.neurons
    n_out = fpc * 10

    print("=" * 78)
    print("STDP Diagnostics: SW Int8 Reference vs On-Chip STDP")
    print("=" * 78)

    # Load test data
    print("\n[1] Loading test data ...")
    test_imgs, test_lbls = load_test_data(args.n_samples)
    print(f"  {len(test_imgs)} test images loaded")

    # Load SW model
    print("\n[2] Loading SW model ...")
    sw_model_path = args.sw_model or f'data/cache/mnist_10class_model_{n_out}n.npz'
    if os.path.exists(sw_model_path):
        from tests.mnist_10class_train import DenseSTDP10Class
        sw_net = DenseSTDP10Class.load(sw_model_path, device=DEVICE)
        sw_weights = sw_net.weights.cpu().numpy()  # (n_out, 784) float
        sw_weight_stats = analyze_weight_distribution(sw_weights, 'SW Float32', fpc=fpc)

        # Also get int8 version
        q_weights, q_scale = sw_net.quantize_weights()
        sw_int8_stats = analyze_weight_distribution(q_weights, 'SW Int8', fpc=fpc)
        print(f"  SW model loaded: {sw_model_path}")
        print(f"  Float32: [{sw_weights.min():.3f}, {sw_weights.max():.3f}]")
        print(f"  Int8: [{q_weights.min()}, {q_weights.max()}]")
    else:
        print(f"  WARNING: SW model not found at {sw_model_path}")
        print(f"  Run: python tests/mnist_10class_train.py --neurons {fpc}")
        sw_net = None
        sw_weight_stats = None

    # Load On-Chip STDP model
    print("\n[3] Loading On-Chip STDP model ...")
    oc_model_path = args.onchip_model or f'data/cache/onchip_stdp_model_{n_out}n.npz'
    from tests.onchip_stdp_experiment import OnChipSTDPTrainerGPU
    oc_trainer = OnChipSTDPTrainerGPU(
        n_input=784, n_classes=10, features_per_class=fpc,
        leak=1, timesteps=25, trace_inc=64, lr_shift=6, device=DEVICE)
    if os.path.exists(oc_model_path):
        data = np.load(oc_model_path)
        w = data['weights']
        if w.shape == (784, n_out):
            oc_trainer.engine.weights = torch.from_numpy(w.astype(np.int16)).to(DEVICE)
        elif w.shape == (n_out, 784):
            oc_trainer.engine.weights = torch.from_numpy(w.T.astype(np.int16)).to(DEVICE)
        if 'thresholds' in data:
            oc_trainer.per_neuron_thr = torch.from_numpy(
                data['thresholds'].astype(np.float32)).to(DEVICE)
            oc_trainer.base_threshold = float(data.get('threshold', data['thresholds'].mean()))
        print(f"  On-Chip model loaded: {oc_model_path}")
    else:
        print(f"  WARNING: On-Chip model not found at {oc_model_path}")
        print(f"  Run: python tests/onchip_stdp_experiment.py --neurons {fpc} --prototype-init")

    oc_weights = oc_trainer.engine.weights.cpu().numpy()
    oc_weight_stats = analyze_weight_distribution(oc_weights, 'On-Chip STDP', fpc=fpc)
    print(f"  On-Chip: [{oc_weights.min()}, {oc_weights.max()}]")

    # Spike pattern analysis
    print("\n[4] Analyzing spike patterns ...")
    oc_spike_stats = analyze_spike_patterns(
        oc_trainer, test_imgs, test_lbls, model_type='onchip',
        n_samples=args.n_samples, device=DEVICE)
    print(f"  On-Chip accuracy: {oc_spike_stats['accuracy']:.1f}%")

    if sw_net is not None:
        sw_spike_stats = analyze_spike_patterns(
            sw_net, test_imgs, test_lbls, model_type='sw',
            n_samples=args.n_samples, device=DEVICE)
        print(f"  SW accuracy: {sw_spike_stats['accuracy']:.1f}%")
    else:
        sw_spike_stats = None

    # Print comparison
    if sw_weight_stats and sw_spike_stats:
        observations = print_comparison(
            sw_weight_stats, oc_weight_stats,
            sw_spike_stats, oc_spike_stats)
    else:
        print("\n(Skipping comparison - SW model not available)")
        observations = []

    return observations


if __name__ == '__main__':
    main()
