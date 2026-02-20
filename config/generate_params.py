#!/usr/bin/env python3
"""
Parameter Generator: YAML → Verilog / Python / HLS headers.

Reads config/snn_params.yaml (single source of truth) and generates:
  - config/generated/snn_params.vh   Verilog `include header
  - config/generated/snn_params.py   Python constants module
  - config/generated/snn_params.h    HLS/C++ header

Derived widths ($clog2 equivalents) are computed here so RTL doesn't
need to use $clog2 on parameters (which isn't portable across all tools).

Usage:
    python config/generate_params.py
    python config/generate_params.py --config path/to/snn_params.yaml

Author: Jiwoon Lee (@metr0jw)
"""

import argparse
import math
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml


def clog2(n: int) -> int:
    """Ceiling of log2, matching Verilog's $clog2 behaviour."""
    if n <= 1:
        return 1
    return int(math.ceil(math.log2(n)))


def load_config(config_path: str) -> dict:
    """Load and validate the YAML config."""
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    required_sections = ['architecture', 'widths', 'weights', 'hls', 'target']
    for section in required_sections:
        if section not in cfg:
            raise ValueError(f"Missing required section '{section}' in {config_path}")
    return cfg


def compute_derived(cfg: dict) -> dict:
    """Compute all derived parameters from base config values."""
    arch = cfg['architecture']
    widths = cfg['widths']

    # --- Flexible group sizes ---------------------------------------------------
    # group_sizes: explicit per-group neuron counts (primary)
    # neurons_per_group: fallback / uniform size
    if 'group_sizes' in arch and arch['group_sizes']:
        group_sizes = list(arch['group_sizes'])
    else:
        num_groups = arch.get('num_groups', 16)
        npg = arch.get('neurons_per_group', 128)
        group_sizes = [npg] * num_groups

    num_groups = len(group_sizes)
    if num_groups > 16:
        raise ValueError(
            f"num_groups={num_groups} exceeds hardware limit of 16 "
            f"(4-bit group addressing in config registers and event router)")
    if num_groups < 1:
        raise ValueError("At least one group is required")
    max_neurons_per_group = max(group_sizes)
    total_neurons = sum(group_sizes)
    max_fanout_inter = arch['max_fanout_inter']

    d = {}
    d['group_sizes'] = group_sizes
    d['num_groups'] = num_groups
    d['max_neurons_per_group'] = max_neurons_per_group
    d['total_neurons'] = total_neurons

    # Derived bit widths
    d['group_id_width'] = clog2(num_groups)
    d['local_id_width'] = clog2(max_neurons_per_group)
    d['global_id_width'] = d['group_id_width'] + d['local_id_width']
    d['fanout_idx_width'] = clog2(max_fanout_inter)

    # Aggregate counts (backward compat aliases)
    d['max_neurons'] = total_neurons

    # HLS compatibility aliases
    d['hls_neuron_id_width'] = d['global_id_width']
    d['hls_max_neurons'] = total_neurons

    # Connectivity table data width:
    #   [valid(1)] [dst_group(GROUP_ID_WIDTH)] [dst_neuron(LOCAL_ID_WIDTH)]
    #   [weight(WEIGHT_WIDTH)] [exc_inh(1)]
    d['ct_data_width'] = (1 + d['group_id_width'] + d['local_id_width']
                          + widths['weight_width'] + 1)

    # Neuron state width (packed BRAM word):
    #   [v_mem(DATA_WIDTH)] [refrac(REFRAC_WIDTH)]
    d['neuron_state_width'] = widths['data_width'] + widths['refrac_width']

    return d


# ─────────────────────────────────────────────────────────────────────────────
# Verilog Header Generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_verilog(cfg: dict, derived: dict) -> str:
    """Generate Verilog include file with `define macros.

    RTL modules use these as parameter defaults:
        parameter NUM_GROUPS = `SNN_NUM_GROUPS
    This keeps modules parametric (testbenches can override) while
    centralising the default values.
    """
    arch = cfg['architecture']
    widths = cfg['widths']
    weights = cfg['weights']
    hls = cfg['hls']
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    num_groups = derived['num_groups']
    group_sizes = derived['group_sizes']
    max_npg = derived['max_neurons_per_group']

    lines = [
        f'// =============================================================================',
        f'// SNN Accelerator Parameters — AUTO-GENERATED from snn_params.yaml',
        f'// Generated: {timestamp}',
        f'// DO NOT EDIT — modify config/snn_params.yaml and run generate_params.py',
        f'// =============================================================================',
        f'',
        f'`ifndef SNN_PARAMS_VH',
        f'`define SNN_PARAMS_VH',
        f'',
        f'// ─── Core Architecture ────────────────────────────────────────────',
        f'`define SNN_NUM_GROUPS          {num_groups}',
        f'`define SNN_NEURONS_PER_GROUP   {max_npg}   // max(group_sizes) — bus width driver',
        f'`define SNN_MAX_NEURONS_PER_GROUP {max_npg}',
        f'`define SNN_MAX_FANOUT_INTER    {arch["max_fanout_inter"]}',
        f'`define SNN_SPIKE_BUFFER_DEPTH  {arch["spike_buffer_depth"]}',
    ]

    # Per-group size defines — always emit exactly 16 entries so the
    # ternary chain in snn_core_group_top.v compiles for any NUM_GROUPS ≤ 16.
    # Unused indices get the fallback value (never instantiated in RTL).
    fallback_npg = arch.get('neurons_per_group', max_npg)
    lines.append('')
    lines.append('// ─── Per-Group Neuron Counts ─────────────────────────────────────')
    for i in range(16):
        sz = group_sizes[i] if i < num_groups else fallback_npg
        lines.append(f'`define SNN_GROUP_SIZE_{i:<2d}       {sz}')

    lines += [
        f'',
        f'// ─── Data Widths ───────────────────────────────────────────────────',
        f'`define SNN_DATA_WIDTH          {widths["data_width"]}',
        f'`define SNN_WEIGHT_WIDTH        {widths["weight_width"]}',
        f'`define SNN_THRESHOLD_WIDTH     {widths["threshold_width"]}',
        f'`define SNN_LEAK_WIDTH          {widths["leak_width"]}',
        f'`define SNN_REFRAC_WIDTH        {widths["refrac_width"]}',
        f'',
        f'// ─── Derived Bit Widths (computed from architecture) ───────────────',
        f'`define SNN_GROUP_ID_WIDTH      {derived["group_id_width"]}',
        f'`define SNN_LOCAL_ID_WIDTH      {derived["local_id_width"]}',
        f'`define SNN_GLOBAL_ID_WIDTH     {derived["global_id_width"]}',
        f'`define SNN_FANOUT_IDX_WIDTH    {derived["fanout_idx_width"]}',
        f'',
        f'// ─── Derived Counts ────────────────────────────────────────────────',
        f'`define SNN_MAX_NEURONS         {derived["max_neurons"]}',
        f'`define SNN_TOTAL_NEURONS       {derived["total_neurons"]}',
        f'`define SNN_CT_DATA_WIDTH       {derived["ct_data_width"]}',
        f'`define SNN_NEURON_STATE_WIDTH  {derived["neuron_state_width"]}',
        f'',
        f'// ─── Weight Representation ────────────────────────────────────────',
        f'`define SNN_MAX_WEIGHT          {weights["max_weight"]}',
        f'`define SNN_MIN_WEIGHT          {weights["min_weight"]}',
        f'`define SNN_WEIGHT_FLAG_WIDTH   {weights["weight_with_flag_width"]}',
        f'',
        f'// ─── HLS Interface ────────────────────────────────────────────────',
        f'`define SNN_HLS_NEURON_ID_WIDTH {derived["hls_neuron_id_width"]}',
        f'`define SNN_HLS_MAX_NEURONS     {derived["hls_max_neurons"]}',
        f'`define SNN_HLS_WEIGHT_WIDTH    {hls["hls_weight_width"]}',
        f'',
        f'`endif // SNN_PARAMS_VH',
    ]
    return '\n'.join(lines) + '\n'


# ─────────────────────────────────────────────────────────────────────────────
# Python Module Generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_python(cfg: dict, derived: dict) -> str:
    """Generate Python constants module."""
    arch = cfg['architecture']
    widths = cfg['widths']
    weights = cfg['weights']
    hls = cfg['hls']
    target = cfg['target']
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    num_groups = derived['num_groups']
    group_sizes = derived['group_sizes']
    max_npg = derived['max_neurons_per_group']

    lines = [
        f'"""',
        f'SNN Accelerator Parameters — AUTO-GENERATED from snn_params.yaml',
        f'',
        f'Generated: {timestamp}',
        f'DO NOT EDIT — modify config/snn_params.yaml and run generate_params.py',
        f'"""',
        f'',
        f'# ─── Core Architecture ─────────────────────────────────────────────',
        f'NUM_GROUPS          = {num_groups}',
        f'NEURONS_PER_GROUP   = {max_npg}   # max(GROUP_SIZES) — backward compat',
        f'MAX_NEURONS_PER_GROUP = {max_npg}',
        f'MAX_FANOUT_INTER    = {arch["max_fanout_inter"]}',
        f'SPIKE_BUFFER_DEPTH  = {arch["spike_buffer_depth"]}',
        f'',
        f'# ─── Per-Group Neuron Counts ────────────────────────────────────────',
        f'GROUP_SIZES         = {group_sizes}',
        f'TOTAL_NEURONS       = {derived["total_neurons"]}',
        f'',
        f'# ─── Data Widths ────────────────────────────────────────────────────',
        f'DATA_WIDTH          = {widths["data_width"]}',
        f'WEIGHT_WIDTH        = {widths["weight_width"]}',
        f'THRESHOLD_WIDTH     = {widths["threshold_width"]}',
        f'LEAK_WIDTH          = {widths["leak_width"]}',
        f'REFRAC_WIDTH        = {widths["refrac_width"]}',
        f'',
        f'# ─── Derived Bit Widths ─────────────────────────────────────────────',
        f'GROUP_ID_WIDTH      = {derived["group_id_width"]}   # clog2({num_groups})',
        f'LOCAL_ID_WIDTH      = {derived["local_id_width"]}   # clog2({max_npg})',
        f'GLOBAL_ID_WIDTH     = {derived["global_id_width"]}  # GROUP_ID_WIDTH + LOCAL_ID_WIDTH',
        f'FANOUT_IDX_WIDTH    = {derived["fanout_idx_width"]}   # clog2({arch["max_fanout_inter"]})',
        f'',
        f'# ─── Derived Counts ─────────────────────────────────────────────────',
        f'MAX_NEURONS         = {derived["max_neurons"]}  # sum(GROUP_SIZES)',
        f'CT_DATA_WIDTH       = {derived["ct_data_width"]}  # 1+GROUP_ID+LOCAL_ID+WEIGHT+1',
        f'NEURON_STATE_WIDTH  = {derived["neuron_state_width"]}  # DATA_WIDTH + REFRAC_WIDTH',
        f'',
        f'# ─── Weight Representation ────────────────────────────────────────',
        f'MAX_WEIGHT          = {weights["max_weight"]}  # (1 << WEIGHT_WIDTH) - 1',
        f'MIN_WEIGHT          = {weights["min_weight"]}',
        f'WEIGHT_FLAG_WIDTH   = {weights["weight_with_flag_width"]}   # WEIGHT_WIDTH + 1',
        f'MAX_WEIGHT_DELTA    = {weights["max_weight"]}',
        f'',
        f'# ─── HLS Interface ────────────────────────────────────────────────',
        f'HLS_NEURON_ID_WIDTH = {derived["hls_neuron_id_width"]}',
        f'HLS_MAX_NEURONS     = {derived["hls_max_neurons"]}',
        f'HLS_WEIGHT_WIDTH    = {hls["hls_weight_width"]}',
        f'NEURON_ID_WIDTH     = GLOBAL_ID_WIDTH  # Alias',
        f'',
        f'# ─── Fixed-Point (HLS ap_fixed<16,8>) ─────────────────────────────',
        f'FIXED_POINT_FRAC_BITS = {hls["fixed_point_frac_bits"]}',
        f'FIXED_POINT_SCALE     = 1 << FIXED_POINT_FRAC_BITS  # {1 << hls["fixed_point_frac_bits"]}',
        f'',
        f'# ─── Legacy 8-bit weight constants (backward compat) ──────────────',
        f'LEGACY_MAX_WEIGHT   = 127',
        f'LEGACY_MIN_WEIGHT   = -128',
        f'LEGACY_WEIGHT_SCALE = 128',
        f'WEIGHT_SCALE        = {1 << widths["weight_width"]}',
        f'',
        f'# ─── FPGA Target ──────────────────────────────────────────────────',
        f'FPGA_PART           = "{target["fpga_part"]}"',
        f'CLOCK_PERIOD_NS     = {target["clock_period_ns"]}',
        f'BOARD               = "{target["board"]}"',
    ]
    return '\n'.join(lines) + '\n'


# ─────────────────────────────────────────────────────────────────────────────
# HLS/C++ Header Generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_hls(cfg: dict, derived: dict) -> str:
    """Generate HLS/C++ header file.

    All constants use the SNN_ prefix to avoid name-clashes with HLS-local
    definitions (e.g. HLS uses signed MAX_WEIGHT=7 whereas the canonical
    RTL value is unsigned MAX_WEIGHT=15).
    """
    arch = cfg['architecture']
    widths = cfg['widths']
    weights = cfg['weights']
    hls = cfg['hls']
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    num_groups = derived['num_groups']
    max_npg = derived['max_neurons_per_group']

    lines = [
        f'// =============================================================================',
        f'// SNN Accelerator Parameters — AUTO-GENERATED from snn_params.yaml',
        f'// Generated: {timestamp}',
        f'// DO NOT EDIT — modify config/snn_params.yaml and run generate_params.py',
        f'// =============================================================================',
        f'',
        f'#ifndef SNN_PARAMS_H',
        f'#define SNN_PARAMS_H',
        f'',
        f'// ─── Core Architecture ────────────────────────────────────────────',
        f'const int SNN_NUM_GROUPS            = {num_groups};',
        f'const int SNN_NEURONS_PER_GROUP     = {max_npg};  // max(group_sizes)',
        f'const int SNN_MAX_NEURONS_PER_GROUP = {max_npg};',
        f'const int SNN_MAX_FANOUT_INTER      = {arch["max_fanout_inter"]};',
        f'const int SNN_SPIKE_BUFFER_DEPTH    = {arch["spike_buffer_depth"]};',
        f'const int SNN_TOTAL_NEURONS         = {derived["total_neurons"]};',
        f'',
        f'// ─── Data Widths ───────────────────────────────────────────────────',
        f'const int SNN_DATA_WIDTH          = {widths["data_width"]};',
        f'const int SNN_WEIGHT_WIDTH        = {widths["weight_width"]};',
        f'const int SNN_THRESHOLD_WIDTH     = {widths["threshold_width"]};',
        f'const int SNN_LEAK_WIDTH          = {widths["leak_width"]};',
        f'const int SNN_REFRAC_WIDTH        = {widths["refrac_width"]};',
        f'',
        f'// ─── Derived Bit Widths ────────────────────────────────────────────',
        f'const int SNN_GROUP_ID_WIDTH      = {derived["group_id_width"]};',
        f'const int SNN_LOCAL_ID_WIDTH      = {derived["local_id_width"]};',
        f'const int SNN_GLOBAL_ID_WIDTH     = {derived["global_id_width"]};',
        f'const int SNN_NEURON_ID_WIDTH     = {derived["global_id_width"]};  // Alias',
        f'const int SNN_FANOUT_IDX_WIDTH    = {derived["fanout_idx_width"]};',
        f'',
        f'// ─── Derived Counts ────────────────────────────────────────────────',
        f'const int SNN_MAX_NEURONS         = {derived["max_neurons"]};',
        f'const int SNN_CT_DATA_WIDTH       = {derived["ct_data_width"]};',
        f'const int SNN_NEURON_STATE_WIDTH  = {derived["neuron_state_width"]};',
        f'',
        f'// ─── Weight Representation (RTL: unsigned magnitude + exc/inh flag) ─',
        f'const int SNN_RTL_MAX_WEIGHT      = {weights["max_weight"]};',
        f'const int SNN_RTL_MIN_WEIGHT      = {weights["min_weight"]};',
        f'const int SNN_WEIGHT_FLAG_WIDTH   = {weights["weight_with_flag_width"]};',
        f'',
        f'// ─── HLS Interface ────────────────────────────────────────────────',
        f'const int SNN_HLS_NEURON_ID_WIDTH = {derived["hls_neuron_id_width"]};',
        f'const int SNN_HLS_MAX_NEURONS     = {derived["hls_max_neurons"]};',
        f'const int SNN_HLS_WEIGHT_WIDTH    = {hls["hls_weight_width"]};',
        f'',
        f'// ─── Fixed-Point (ap_fixed<16,8>) ─────────────────────────────────',
        f'const int SNN_FIXED_POINT_FRAC_BITS = {hls["fixed_point_frac_bits"]};',
        f'const int SNN_FIXED_POINT_SCALE     = (1 << SNN_FIXED_POINT_FRAC_BITS);',
        f'',
        f'#endif // SNN_PARAMS_H',
    ]
    return '\n'.join(lines) + '\n'


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Generate RTL/Python/HLS parameter files from snn_params.yaml')
    parser.add_argument('--config', default=None,
                        help='Path to snn_params.yaml (auto-detected if not given)')
    parser.add_argument('--output-dir', default=None,
                        help='Output directory (default: config/generated/)')
    args = parser.parse_args()

    # Find project root
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent if script_dir.name == 'config' else script_dir

    # Config path
    if args.config:
        config_path = Path(args.config)
    else:
        config_path = project_root / 'config' / 'snn_params.yaml'

    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    # Output directory
    if args.output_dir:
        out_dir = Path(args.output_dir)
    else:
        out_dir = project_root / 'config' / 'generated'

    out_dir.mkdir(parents=True, exist_ok=True)

    # Load & compute
    cfg = load_config(str(config_path))
    derived = compute_derived(cfg)

    # Print summary
    arch = cfg['architecture']
    print(f"SNN Parameter Generator")
    print(f"  Config: {config_path}")
    print(f"  Output: {out_dir}/")
    group_sizes = derived['group_sizes']
    num_groups = derived['num_groups']
    max_npg = derived['max_neurons_per_group']
    print(f"  Architecture: {num_groups} groups, "
          f"max {max_npg} neurons/group, "
          f"{derived['total_neurons']} total neurons")
    if len(set(group_sizes)) == 1:
        print(f"  Group sizes: uniform {group_sizes[0]}")
    else:
        print(f"  Group sizes: {group_sizes}")
    print(f"  ID widths: group={derived['group_id_width']}b, "
          f"local={derived['local_id_width']}b, "
          f"global={derived['global_id_width']}b")
    print()

    # Generate files
    files = {
        'snn_params.vh': generate_verilog(cfg, derived),
        'snn_params.py': generate_python(cfg, derived),
        'snn_params.h':  generate_hls(cfg, derived),
    }

    for filename, content in files.items():
        filepath = out_dir / filename
        filepath.write_text(content)
        print(f"  Generated: {filepath}")

    print(f"\nDone. {len(files)} files generated.")


if __name__ == '__main__':
    main()
