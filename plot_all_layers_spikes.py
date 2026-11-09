#!/usr/bin/env python3
"""
plot_all_layers_spikes.py
=========================
Multi-Layer Spiking Activity Raster & TVLA Leakage Plotter.
Reads the structured per-image spike trace (.csv or .parquet) produced by
fpga_cnn3_inference.py / fpga_cnn3_cifar10_inference.py, exports to Parquet
if loaded from CSV, and plots:
  1. Multi-layer temporal spike raster plot (Layer 2 Relay + Layer 3 Class Neurons)
     for a selected image, annotated with True Label and Predicted Label.
  2. Per-image cross-sectional spike volume (split by Layer 2 vs Layer 3) for TVLA.

Usage:
  python3 plot_all_layers_spikes.py --input mnist_cnn3_spike_trace.csv --image-id 0
"""

import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description="Plot multi-layer SNN spike raster and TVLA activity")
    parser.add_argument('--input', default='mnist_cnn3_spike_trace.csv',
                        help='Path to spike trace (.csv or .parquet)')
    parser.add_argument('--image-id', type=int, default=0,
                        help='Image ID to visualize in the temporal raster plot (default: 0)')
    parser.add_argument('--output-dir', default='.',
                        help='Directory to save output plots and parquet file')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Loading spike trace from: {args.input}")
    if args.input.endswith('.parquet'):
        df = pd.read_parquet(args.input)
    else:
        df = pd.read_csv(args.input)
        parquet_out = os.path.splitext(args.input)[0] + '.parquet'
        try:
            df.to_parquet(parquet_out, index=False)
            print(f"  Exported columnar Parquet file for TVLA: {parquet_out}")
        except Exception as e:
            print(f"  Note: Parquet conversion skipped ({e})")

    if df.empty:
        print("Warning: Input spike trace is empty.")
        return

    # ── Plot 1: Multi-Layer Cycle-by-Cycle Raster Plot for Selected Image ─────
    img_df = df[df['image_id'] == args.image_id]
    if img_df.empty:
        first_id = int(df['image_id'].iloc[0])
        print(f"Image {args.image_id} not found; falling back to image_id={first_id}")
        args.image_id = first_id
        img_df = df[df['image_id'] == args.image_id]

    true_lbl = int(img_df['true_label'].iloc[0])
    pred_lbl = int(img_df['predicted_label'].iloc[0])

    l2_df = img_df[img_df['layer'] == 2]
    l3_df = img_df[img_df['layer'] == 3]

    fig, (ax_l3, ax_l2) = plt.subplots(
        2, 1, figsize=(12, 7), sharex=True,
        gridspec_kw={'height_ratios': [1, 2.5]}
    )

    # Top panel: Layer 3 Output Class Neurons (0..9)
    if not l3_df.empty:
        ax_l3.scatter(
            l3_df['clock_cycle'], l3_df['layer_neuron_id'],
            marker='|', s=120, color='#d62728', linewidths=2.0,
            label='Layer 3 (Output Classes 0..9)'
        )
    ax_l3.set_yticks(range(10))
    ax_l3.set_ylim(-0.8, 9.8)
    ax_l3.set_ylabel('L3 Class ID (0–9)')
    ax_l3.set_title(
        f'All-Layer Temporal Spiking Raster — Image {args.image_id} '
        f'(True Class: {true_lbl} | Predicted Class: {pred_lbl})'
    )
    ax_l3.grid(True, linestyle='--', alpha=0.5)
    ax_l3.legend(loc='upper right')

    # Bottom panel: Layer 2 Relay Neurons (colored by Core Group 0..3)
    group_colors = {0: '#1f77b4', 1: '#2ca02c', 2: '#ff7f0e', 3: '#9467bd'}
    for grp_id in sorted(l2_df['group_id'].unique()):
        grp_sub = l2_df[l2_df['group_id'] == grp_id]
        ax_l2.scatter(
            grp_sub['clock_cycle'], grp_sub['layer_neuron_id'],
            marker='|', s=35, color=group_colors.get(int(grp_id), '#1f77b4'),
            alpha=0.85, label=f'Layer 2 — Core Group {grp_id}'
        )
    ax_l2.set_xlabel('Hardware Clock Cycle (Cumulative across Timesteps)')
    ax_l2.set_ylabel('L2 Neuron ID')
    ax_l2.grid(True, linestyle='--', alpha=0.5)
    if not l2_df.empty:
        ax_l2.legend(loc='upper right', ncol=2)

    plt.tight_layout()
    raster_path = os.path.join(args.output_dir, f'all_layers_raster_img{args.image_id}.png')
    plt.savefig(raster_path, dpi=150)
    plt.close(fig)
    print(f"  Saved multi-layer raster plot: {raster_path}")

    # ── Plot 2: Per-Image Cross-Sectional Spiking Activity (TVLA Proxy) ───────
    counts = df.groupby(['image_id', 'layer']).size().unstack(fill_value=0)
    fig, ax = plt.subplots(figsize=(11, 4.5))
    counts.plot(kind='bar', stacked=True, ax=ax, color=['#1f77b4', '#d62728'], alpha=0.85)
    ax.set_title('Data-Dependent Leakage: Spiking Volume per Image Across Layers')
    ax.set_xlabel('Image Index')
    ax.set_ylabel('Total Spikes (Proxy for Dynamic Power)')
    ax.legend(['Layer 2 (Relay Grps 0..3)', 'Layer 3 (Classifier Grp 4)'])
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)
    plt.xticks(rotation=0)
    plt.tight_layout()

    cross_path = os.path.join(args.output_dir, 'all_layers_cross_sectional_plot.png')
    plt.savefig(cross_path, dpi=150)
    plt.close(fig)
    print(f"  Saved cross-sectional TVLA plot: {cross_path}")


if __name__ == '__main__':
    main()
