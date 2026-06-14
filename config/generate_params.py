#!/usr/bin/env python3
"""
Parameter Generator: YAML → Verilog / Python / HLS headers.

Reads config/spikemold_params.yaml (single source of truth) and generates:
  - config/generated/spikemold_params.vh   Verilog `include header
  - config/generated/spikemold_params.py   Python constants module
  - config/generated/spikemold_params.h    HLS/C++ header

Derived widths ($clog2 equivalents) are computed here so RTL doesn't
need to use $clog2 on parameters (which isn't portable across all tools).

Usage:
    python config/generate_params.py
    python config/generate_params.py --config path/to/spikemold_params.yaml

Author: Jiwoon Lee (@metr0jw)
"""

import argparse
import math
import sys
from pathlib import Path

import yaml


GENERATED_NOTICE = "Generated deterministically from config/spikemold_params.yaml"


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
    router = cfg.get('router', {})
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
    d['router_max_fanout'] = int(router.get('max_fanout', 32))
    d['router_delay_width'] = int(router.get('delay_width', 8))
    d['router_mapping_mode'] = str(router.get('mapping_mode', 'table')).strip().lower()
    d['router_direct_map_windows'] = int(router.get('direct_map_windows', 1))
    d['router_conn_ram_style'] = str(router.get('conn_ram_style', 'block')).strip().lower()
    if d['router_mapping_mode'] not in ('table', 'direct_offset', 'hybrid_direct_offset'):
        raise ValueError("router.mapping_mode must be 'table', 'direct_offset', or 'hybrid_direct_offset'")
    if d['router_direct_map_windows'] < 1 or d['router_direct_map_windows'] > 16:
        raise ValueError("router.direct_map_windows must be in [1, 16]")
    if d['router_max_fanout'] < 1:
        raise ValueError("router.max_fanout must be >= 1")
    if d['router_delay_width'] < 1 or d['router_delay_width'] > 8:
        raise ValueError("router.delay_width must be in [1, 8]")
    if d['router_conn_ram_style'] not in ('block', 'distributed'):
        raise ValueError("router.conn_ram_style must be 'block' or 'distributed'")
    d['router_use_direct_offset_map'] = 1 if d['router_mapping_mode'] in ('direct_offset', 'hybrid_direct_offset') else 0
    d['router_use_table_fallback'] = 1 if d['router_mapping_mode'] == 'hybrid_direct_offset' else 0
    d['router_conn_ram_style_dist'] = 1 if d['router_conn_ram_style'] == 'distributed' else 0

    # Aggregate counts used by RTL and software generators.
    d['max_neurons'] = total_neurons

    # HLS compatibility aliases (hls_neuron_id_width computed after topology)
    d['hls_max_neurons'] = total_neurons

    # --- SpikePress Projection Topology -------------------------
    neuron_groups = cfg.get('neuron_groups', [])
    connections = cfg.get('connections', [])

    if neuron_groups and connections:
        # Compute connection details
        conn_list = []
        weight_offset = 0
        total_weight_buffer_size = 0
        max_src_neurons = 0
        max_dst_neurons = 0

        # Build group_id_start array (cumulative neuron ID offsets)
        ng_sizes = [g['size'] for g in neuron_groups]
        ng_id_start = [0]
        for sz in ng_sizes:
            ng_id_start.append(ng_id_start[-1] + sz)

        for conn in connections:
            src_idx = conn['src_group']
            dst_idx = conn['dst_group']
            src_size = neuron_groups[src_idx]['size']
            dst_size = neuron_groups[dst_idx]['size']
            num_weights = src_size * dst_size

            conn_list.append({
                'name': conn['name'],
                'src_group': src_idx,
                'dst_group': dst_idx,
                'src_size': src_size,
                'dst_size': dst_size,
                'weight_offset': weight_offset,
                'num_weights': num_weights,
                'src_id_start': ng_id_start[src_idx],
                'dst_id_start': ng_id_start[dst_idx],
            })

            weight_offset += num_weights
            total_weight_buffer_size += num_weights
            max_src_neurons = max(max_src_neurons, src_size)
            max_dst_neurons = max(max_dst_neurons, dst_size)

        d['neuron_groups'] = neuron_groups
        d['neuron_group_sizes'] = ng_sizes
        d['neuron_group_id_start'] = ng_id_start
        d['num_neuron_groups'] = len(neuron_groups)
        d['connections'] = conn_list
        d['num_connections'] = len(conn_list)
        d['max_weight_buffer_size'] = total_weight_buffer_size
        d['max_src_neurons'] = max_src_neurons
        d['max_dst_neurons'] = max_dst_neurons
        d['total_logical_neurons'] = ng_id_start[-1]  # sum of all group sizes
    else:
        # Fallback: no topology defined, use reference N×N
        d['neuron_groups'] = []
        d['connections'] = []
        d['num_connections'] = 0
        d['num_neuron_groups'] = 0
        d['max_weight_buffer_size'] = total_neurons * total_neurons
        d['max_src_neurons'] = total_neurons
        d['max_dst_neurons'] = total_neurons
        d['neuron_group_sizes'] = []
        d['neuron_group_id_start'] = []
        d['total_logical_neurons'] = total_neurons

    # Connectivity table data width:
    #   [valid(1)] [dst_group(GROUP_ID_WIDTH)] [dst_neuron(LOCAL_ID_WIDTH)]
    #   [weight(WEIGHT_WIDTH)] [exc_inh(1)]
    d['ct_data_width'] = (1 + d['group_id_width'] + d['local_id_width']
                          + widths['weight_width'] + 1)

    # HLS neuron ID width: must accommodate ALL logical neuron IDs.
    # RTL core groups use global_id_width (GROUP_ID + LOCAL_ID = 11 bits for 2048).
    # HLS logical neuron space (SpikePress populations) may be larger (e.g., 4890 → 13 bits).
    logical_bits = clog2(d['total_logical_neurons']) if d['total_logical_neurons'] > 0 else 0
    d['hls_neuron_id_width'] = max(d['global_id_width'], logical_bits)
    hls_cfg = cfg.get('hls', {})
    d['hls_smoke_commands_enable'] = 1 if hls_cfg.get('smoke_commands_enable', True) else 0
    d['hls_cnn_descriptor_page_enable'] = 1 if hls_cfg.get('cnn_descriptor_page_enable', True) else 0

    # Neuron state width (packed BRAM word):
    #   [v_mem(DATA_WIDTH)] [refrac(REFRAC_WIDTH)]
    d['neuron_state_width'] = widths['data_width'] + widths['refrac_width']

    # --- Resource-Aware Weight Memory -----------
    wm = cfg.get('weight_memory', {})
    d['weight_bits'] = wm.get('weight_bits', 8)  # 2, 4, or 8
    d['time_embedding'] = 1 if wm.get('time_embedding', False) else 0
    aux_storage = wm.get('auxiliary_storage', 'bram')
    d['auxiliary_lutram'] = 1 if aux_storage == 'lutram' else 0

    # --- Trace Maintenance (neuromorphic-pure branch) -----------------------
    tm = cfg.get('trace_maintenance', {})
    d['trace_maintenance_mode'] = str(tm.get('mode', 'global')).strip().lower()
    if d['trace_maintenance_mode'] not in ('global', 'active_set'):
        raise ValueError("trace_maintenance.mode must be 'global' or 'active_set'")
    d['trace_maintenance_active_set'] = 1 if d['trace_maintenance_mode'] == 'active_set' else 0
    d['trace_active_clear_threshold'] = int(tm.get('active_clear_threshold', 0))
    if d['trace_active_clear_threshold'] < 0 or d['trace_active_clear_threshold'] > 255:
        raise ValueError("trace_maintenance.active_clear_threshold must be in [0, 255]")

    # Packed buffer size: ceil(max_weight_buffer_size * weight_bits / 8)
    wb = d['weight_bits']
    total_bits = d['max_weight_buffer_size'] * wb
    d['packed_buffer_bytes'] = (total_bits + 7) // 8

    # --- Weight Tiling (future large-projection residency) --------------------
    wt = cfg.get('weight_tiling', {})
    d['weight_tiling_enable'] = 1 if wt.get('enable', False) else 0
    d['weight_tiling_large_only'] = 1 if wt.get('large_only', True) else 0
    d['weight_tiling_large_conn_min_weights'] = int(wt.get('large_conn_min_weights', 65536))
    d['weight_tiling_src_chunk'] = int(wt.get('src_chunk', 196))
    d['weight_tiling_dst_chunk'] = int(wt.get('dst_chunk', 128))
    d['weight_tiling_double_buffer'] = 1 if wt.get('double_buffer', False) else 0
    if d['weight_tiling_large_conn_min_weights'] < 1:
        raise ValueError("weight_tiling.large_conn_min_weights must be >= 1")
    if d['weight_tiling_src_chunk'] < 1:
        raise ValueError("weight_tiling.src_chunk must be >= 1")
    if d['weight_tiling_dst_chunk'] < 1:
        raise ValueError("weight_tiling.dst_chunk must be >= 1")
    d['weight_tiling_active_buffers'] = 2 if d['weight_tiling_double_buffer'] else 1
    d['weight_tiling_active_tile_weights'] = (
        d['weight_tiling_src_chunk'] *
        d['weight_tiling_dst_chunk'] *
        d['weight_tiling_active_buffers']
    )
    d['weight_tiling_active_tile_bytes'] = (
        d['weight_tiling_active_tile_weights'] * d['weight_bits'] + 7
    ) // 8

    resident_offset = 0
    resident_weight_entries = 0
    tiled_weight_entries = 0
    for conn in d.get('connections', []):
        tiled = bool(
            d['weight_tiling_enable'] and
            (
                not d['weight_tiling_large_only'] or
                int(conn['num_weights']) >= d['weight_tiling_large_conn_min_weights']
            )
        )
        conn['tiled'] = 1 if tiled else 0
        if tiled:
            conn['resident_weight_offset'] = -1
            tiled_weight_entries += int(conn['num_weights'])
        else:
            conn['resident_weight_offset'] = resident_offset
            resident_offset += int(conn['num_weights'])
            resident_weight_entries += int(conn['num_weights'])

    if not d.get('connections'):
        resident_weight_entries = d['max_weight_buffer_size']

    d['resident_weight_logical_entries'] = resident_weight_entries
    d['resident_weight_buffer_size'] = max(1, resident_weight_entries)
    d['tiled_weight_entries'] = tiled_weight_entries

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
    num_groups = derived['num_groups']
    group_sizes = derived['group_sizes']
    max_npg = derived['max_neurons_per_group']

    lines = [
        f'// =============================================================================',
        f'// SpikeMold Fabric Parameters - AUTO-GENERATED from spikemold_params.yaml',
        f'// {GENERATED_NOTICE}',
        f'// DO NOT EDIT — modify config/spikemold_params.yaml and run generate_params.py',
        f'// =============================================================================',
        f'',
        f'`ifndef SPIKEMOLD_PARAMS_VH',
        f'`define SPIKEMOLD_PARAMS_VH',
        f'',
        f'// ─── Core Architecture ────────────────────────────────────────────',
        f'`define SNN_NUM_GROUPS          {num_groups}',
        f'`define SNN_NEURONS_PER_GROUP   {max_npg}   // max(group_sizes) — bus width driver',
        f'`define SNN_MAX_NEURONS_PER_GROUP {max_npg}',
        f'`define SNN_MAX_FANOUT_INTER    {arch["max_fanout_inter"]}',
        f'`define SNN_ROUTER_MAX_FANOUT   {derived["router_max_fanout"]}',
        f'`define SNN_ROUTER_DELAY_WIDTH  {derived["router_delay_width"]}',
        f'`define SNN_ROUTER_USE_DIRECT_OFFSET_MAP {derived["router_use_direct_offset_map"]}',
        f'`define SNN_ROUTER_USE_TABLE_FALLBACK {derived["router_use_table_fallback"]}',
        f'`define SNN_ROUTER_DIRECT_MAP_WINDOWS {derived["router_direct_map_windows"]}',
        f'`define SNN_ROUTER_CONN_RAM_STYLE_DIST {derived["router_conn_ram_style_dist"]}',
        f'`define SNN_SPIKE_BUFFER_DEPTH  {arch["spike_buffer_depth"]}',
    ]

    # Per-group size defines — always emit exactly 16 entries so the
    # ternary chain in spikemold_coregroup_top.v compiles for any NUM_GROUPS ≤ 16.
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
        f'`define SNN_HLS_SMOKE_COMMANDS_ENABLE {derived["hls_smoke_commands_enable"]}',
        f'`define SNN_HLS_CNN_DESCRIPTOR_PAGE_ENABLE {derived["hls_cnn_descriptor_page_enable"]}',
        f'',
        f'// ─── SpikePress Weight Buffer ─────────────────────────────────────',
        f'`define SNN_MAX_WEIGHT_BUFFER_SIZE {derived["max_weight_buffer_size"]}',
        f'`define SNN_RESIDENT_WEIGHT_BUFFER_SIZE {derived["resident_weight_buffer_size"]}',
        f'`define SNN_RESIDENT_WEIGHT_LOGICAL_ENTRIES {derived["resident_weight_logical_entries"]}',
        f'`define SNN_TILED_WEIGHT_ENTRIES {derived["tiled_weight_entries"]}',
        f'`define SNN_NUM_CONNECTIONS       {derived["num_connections"]}',
        f'`define SNN_NUM_NEURON_GROUPS     {derived["num_neuron_groups"]}',
        f'',
        f'// ─── Resource-Aware Weight Memory ──────────',
        f'`define SNN_WEIGHT_BITS           {derived["weight_bits"]}',
        f'`define SNN_TIME_EMBEDDING        {derived["time_embedding"]}',
        f'`define SNN_AUXILIARY_LUTRAM      {derived["auxiliary_lutram"]}',
        f'`define SNN_TRACE_MAINTENANCE_ACTIVE_SET {derived["trace_maintenance_active_set"]}',
        f'`define SNN_TRACE_ACTIVE_CLEAR_THRESHOLD {derived["trace_active_clear_threshold"]}',
        f'`define SNN_PACKED_BUFFER_BYTES   {derived["packed_buffer_bytes"]}',
        f'',
        f'// ─── Weight Tiling (future large-network path) ───────────────────',
        f'`define SNN_WEIGHT_TILING_ENABLE  {derived["weight_tiling_enable"]}',
        f'`define SNN_WEIGHT_TILING_LARGE_ONLY {derived["weight_tiling_large_only"]}',
        f'`define SNN_WEIGHT_TILING_LARGE_CONN_MIN_WEIGHTS {derived["weight_tiling_large_conn_min_weights"]}',
        f'`define SNN_WEIGHT_TILING_SRC_CHUNK {derived["weight_tiling_src_chunk"]}',
        f'`define SNN_WEIGHT_TILING_DST_CHUNK {derived["weight_tiling_dst_chunk"]}',
        f'`define SNN_WEIGHT_TILING_DOUBLE_BUFFER {derived["weight_tiling_double_buffer"]}',
        f'`define SNN_WEIGHT_TILING_ACTIVE_BUFFERS {derived["weight_tiling_active_buffers"]}',
        f'`define SNN_WEIGHT_TILING_ACTIVE_TILE_WEIGHTS {derived["weight_tiling_active_tile_weights"]}',
        f'`define SNN_WEIGHT_TILING_ACTIVE_TILE_BYTES {derived["weight_tiling_active_tile_bytes"]}',
        f'',
        f'`endif // SPIKEMOLD_PARAMS_VH',
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
    num_groups = derived['num_groups']
    group_sizes = derived['group_sizes']
    max_npg = derived['max_neurons_per_group']

    lines = [
        f'"""',
        f'SpikeMold Fabric Parameters - AUTO-GENERATED from spikemold_params.yaml',
        f'',
        GENERATED_NOTICE,
        f'DO NOT EDIT — modify config/spikemold_params.yaml and run generate_params.py',
        f'"""',
        f'',
        f'# ─── Core Architecture ─────────────────────────────────────────────',
        f'NUM_GROUPS          = {num_groups}',
        f'NEURONS_PER_GROUP   = {max_npg}   # max(GROUP_SIZES)',
        f'MAX_NEURONS_PER_GROUP = {max_npg}',
        f'MAX_FANOUT_INTER    = {arch["max_fanout_inter"]}',
        f'ROUTER_MAX_FANOUT   = {derived["router_max_fanout"]}',
        f'ROUTER_DELAY_WIDTH  = {derived["router_delay_width"]}',
        f'ROUTER_USE_DIRECT_OFFSET_MAP = {derived["router_use_direct_offset_map"]}',
        f'ROUTER_USE_TABLE_FALLBACK = {derived["router_use_table_fallback"]}',
        f'ROUTER_DIRECT_MAP_WINDOWS = {derived["router_direct_map_windows"]}',
        f'ROUTER_CONN_RAM_STYLE = "{derived["router_conn_ram_style"]}"',
        f'ROUTER_CONN_RAM_STYLE_DIST = {derived["router_conn_ram_style_dist"]}',
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
        f'HLS_SMOKE_COMMANDS_ENABLE = {derived["hls_smoke_commands_enable"]}',
        f'HLS_CNN_DESCRIPTOR_PAGE_ENABLE = {derived["hls_cnn_descriptor_page_enable"]}',
        f'NEURON_ID_WIDTH     = GLOBAL_ID_WIDTH  # Alias',
        f'',
    ]

    # --- SpikePress Projection Topology -------------------------
    if derived['num_neuron_groups'] > 0:
        ng_sizes = derived['neuron_group_sizes']
        ng_id_start = derived['neuron_group_id_start']
        conns = derived['connections']

        lines += [
            f'# ─── SpikePress Projection Topology ────────────────',
            f'NUM_NEURON_GROUPS       = {derived["num_neuron_groups"]}',
            f'NUM_CONNECTIONS         = {derived["num_connections"]}',
            f'MAX_WEIGHT_BUFFER_SIZE  = {derived["max_weight_buffer_size"]}',
            f'RESIDENT_WEIGHT_BUFFER_SIZE = {derived["resident_weight_buffer_size"]}',
            f'RESIDENT_WEIGHT_LOGICAL_ENTRIES = {derived["resident_weight_logical_entries"]}',
            f'TILED_WEIGHT_ENTRIES    = {derived["tiled_weight_entries"]}',
            f'MAX_SRC_NEURONS         = {derived["max_src_neurons"]}',
            f'MAX_DST_NEURONS         = {derived["max_dst_neurons"]}',
            f'TOTAL_LOGICAL_NEURONS   = {derived["total_logical_neurons"]}',
            f'',
            f'NEURON_GROUP_NAMES  = {[g["name"] for g in derived["neuron_groups"]]}',
            f'NEURON_GROUP_SIZES  = {ng_sizes}',
            f'NEURON_GROUP_ID_START = {ng_id_start}',
            f'',
            f'# Per-Connection metadata: list of dicts',
            f'CONNECTIONS = [',
        ]
        for c in conns:
            lines.append(f'    {{"name": "{c["name"]}", "src_group": {c["src_group"]}, '
                         f'"dst_group": {c["dst_group"]}, "src_size": {c["src_size"]}, '
                         f'"dst_size": {c["dst_size"]}, "weight_offset": {c["weight_offset"]}, '
                         f'"resident_weight_offset": {c["resident_weight_offset"]}, '
                         f'"tiled": {bool(c["tiled"])}, '
                         f'"num_weights": {c["num_weights"]}, '
                         f'"src_id_start": {c["src_id_start"]}, '
                         f'"dst_id_start": {c["dst_id_start"]}}},')
        lines += [
            f']',
            f'',
        ]
    else:
        lines += [
            f'# ─── Reference N×N weight memory (no connection topology) ─────────────',
            f'MAX_WEIGHT_BUFFER_SIZE  = {derived["max_weight_buffer_size"]}',
            f'RESIDENT_WEIGHT_BUFFER_SIZE = {derived["resident_weight_buffer_size"]}',
            f'RESIDENT_WEIGHT_LOGICAL_ENTRIES = {derived["resident_weight_logical_entries"]}',
            f'TILED_WEIGHT_ENTRIES    = {derived["tiled_weight_entries"]}',
            f'NUM_CONNECTIONS         = 0',
            f'NUM_NEURON_GROUPS       = 0',
            f'CONNECTIONS             = []',
            f'NEURON_GROUP_NAMES      = []',
            f'NEURON_GROUP_SIZES      = []',
            f'NEURON_GROUP_ID_START   = []',
            f'',
        ]

    lines += [
        f'# ─── Fixed-Point (HLS ap_fixed<16,8>) ─────────────────────────────',
        f'FIXED_POINT_FRAC_BITS = {hls["fixed_point_frac_bits"]}',
        f'FIXED_POINT_SCALE     = 1 << FIXED_POINT_FRAC_BITS  # {1 << hls["fixed_point_frac_bits"]}',
        f'',
        f'# ─── Reference signed 8-bit packed weight constants ──────────────',
        f'REFERENCE_MAX_WEIGHT = 127',
        f'REFERENCE_MIN_WEIGHT = -128',
        f'REFERENCE_WEIGHT_SCALE = 128',
        f'WEIGHT_SCALE        = {1 << widths["weight_width"]}',
        f'',
        f'# ─── Resource-Aware Weight Memory ──────────',
        f'WEIGHT_BITS             = {derived["weight_bits"]}',
        f'PACKED_MAX_WEIGHT       = {(1 << (derived["weight_bits"] - 1)) - 1}',
        f'PACKED_MIN_WEIGHT       = {-(1 << (derived["weight_bits"] - 1))}',
        f'TIME_EMBEDDING          = {derived["time_embedding"]}',
        f'AUXILIARY_LUTRAM         = {derived["auxiliary_lutram"]}',
        f'TRACE_MAINTENANCE_MODE  = "{derived["trace_maintenance_mode"]}"',
        f'TRACE_MAINTENANCE_ACTIVE_SET = {derived["trace_maintenance_active_set"]}',
        f'TRACE_ACTIVE_CLEAR_THRESHOLD = {derived["trace_active_clear_threshold"]}',
        f'PACKED_BUFFER_BYTES     = {derived["packed_buffer_bytes"]}',
        f'',
        f'# ─── Weight Tiling (future large-network path) ──────────────────',
        f'WEIGHT_TILING_ENABLE            = {derived["weight_tiling_enable"]}',
        f'WEIGHT_TILING_LARGE_ONLY        = {derived["weight_tiling_large_only"]}',
        f'WEIGHT_TILING_LARGE_CONN_MIN_WEIGHTS = {derived["weight_tiling_large_conn_min_weights"]}',
        f'WEIGHT_TILING_SRC_CHUNK         = {derived["weight_tiling_src_chunk"]}',
        f'WEIGHT_TILING_DST_CHUNK         = {derived["weight_tiling_dst_chunk"]}',
        f'WEIGHT_TILING_DOUBLE_BUFFER     = {derived["weight_tiling_double_buffer"]}',
        f'WEIGHT_TILING_ACTIVE_BUFFERS    = {derived["weight_tiling_active_buffers"]}',
        f'WEIGHT_TILING_ACTIVE_TILE_WEIGHTS = {derived["weight_tiling_active_tile_weights"]}',
        f'WEIGHT_TILING_ACTIVE_TILE_BYTES = {derived["weight_tiling_active_tile_bytes"]}',
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
    num_groups = derived['num_groups']
    max_npg = derived['max_neurons_per_group']

    lines = [
        f'// =============================================================================',
        f'// SpikeMold Fabric Parameters - AUTO-GENERATED from spikemold_params.yaml',
        f'// {GENERATED_NOTICE}',
        f'// DO NOT EDIT — modify config/spikemold_params.yaml and run generate_params.py',
        f'// =============================================================================',
        f'',
        f'#ifndef SPIKEMOLD_PARAMS_H',
        f'#define SPIKEMOLD_PARAMS_H',
        f'',
        f'// ─── Core Architecture ────────────────────────────────────────────',
        f'const int SNN_NUM_GROUPS            = {num_groups};',
        f'const int SNN_NEURONS_PER_GROUP     = {max_npg};  // max(group_sizes)',
        f'const int SNN_MAX_NEURONS_PER_GROUP = {max_npg};',
        f'const int SNN_MAX_FANOUT_INTER      = {arch["max_fanout_inter"]};',
        f'const int SNN_ROUTER_MAX_FANOUT     = {derived["router_max_fanout"]};',
        f'const int SNN_ROUTER_DELAY_WIDTH    = {derived["router_delay_width"]};',
        f'const int SNN_ROUTER_USE_DIRECT_OFFSET_MAP = {derived["router_use_direct_offset_map"]};',
        f'const int SNN_ROUTER_USE_TABLE_FALLBACK = {derived["router_use_table_fallback"]};',
        f'const int SNN_ROUTER_DIRECT_MAP_WINDOWS = {derived["router_direct_map_windows"]};',
        f'const int SNN_ROUTER_CONN_RAM_STYLE_DIST = {derived["router_conn_ram_style_dist"]};',
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
        f'#ifndef SNN_HLS_SMOKE_COMMANDS_ENABLE',
        f'#define SNN_HLS_SMOKE_COMMANDS_ENABLE {derived["hls_smoke_commands_enable"]}',
        f'#endif',
        f'#ifndef SNN_HLS_CNN_DESCRIPTOR_PAGE_ENABLE',
        f'#define SNN_HLS_CNN_DESCRIPTOR_PAGE_ENABLE {derived["hls_cnn_descriptor_page_enable"]}',
        f'#endif',
        f'',
    ]

    # --- SpikePress Projection Topology -------------------------
    if derived['num_neuron_groups'] > 0:
        ng_sizes = derived['neuron_group_sizes']
        ng_id_start = derived['neuron_group_id_start']
        conns = derived['connections']

        lines += [
            f'// ─── SpikePress Projection Topology ─────────────',
            f'const int SNN_NUM_NEURON_GROUPS      = {derived["num_neuron_groups"]};',
            f'const int SNN_NUM_CONNECTIONS         = {derived["num_connections"]};',
            f'#define SNN_NUM_NEURON_GROUPS_PP      {derived["num_neuron_groups"]}',
            f'#define SNN_NUM_CONNECTIONS_PP         {derived["num_connections"]}',
            f'const int SNN_MAX_WEIGHT_BUFFER_SIZE  = {derived["max_weight_buffer_size"]};',
            f'const int SNN_RESIDENT_WEIGHT_BUFFER_SIZE = {derived["resident_weight_buffer_size"]};',
            f'const int SNN_RESIDENT_WEIGHT_LOGICAL_ENTRIES = {derived["resident_weight_logical_entries"]};',
            f'const int SNN_TILED_WEIGHT_ENTRIES    = {derived["tiled_weight_entries"]};',
            f'const int SNN_MAX_SRC_NEURONS         = {derived["max_src_neurons"]};',
            f'const int SNN_MAX_DST_NEURONS         = {derived["max_dst_neurons"]};',
            f'const int SNN_TOTAL_LOGICAL_NEURONS   = {derived["total_logical_neurons"]};',
            f'',
            f'// Per-population sizes',
        ]
        for i, ng in enumerate(derived['neuron_groups']):
            lines.append(f'const int SNN_NG_SIZE_{i} = {ng["size"]};  // {ng["name"]}')
        lines.append(f'')
        lines.append(f'// Population ID start offsets (cumulative)')
        for i, start in enumerate(ng_id_start):
            lines.append(f'const int SNN_NG_ID_START_{i} = {start};')
        lines.append(f'')
        lines.append(f'// Per-Connection parameters')
        for i, c in enumerate(conns):
            lines.append(f'// Connection {i}: {c["name"]} (group {c["src_group"]} -> group {c["dst_group"]})')
            lines.append(f'const int SNN_CONN_{i}_SRC_GROUP      = {c["src_group"]};')
            lines.append(f'const int SNN_CONN_{i}_DST_GROUP      = {c["dst_group"]};')
            lines.append(f'const int SNN_CONN_{i}_SRC_SIZE       = {c["src_size"]};')
            lines.append(f'const int SNN_CONN_{i}_DST_SIZE       = {c["dst_size"]};')
            lines.append(f'const int SNN_CONN_{i}_WEIGHT_OFFSET  = {c["weight_offset"]};')
            lines.append(f'const int SNN_CONN_{i}_RESIDENT_WEIGHT_OFFSET = {c["resident_weight_offset"]};')
            lines.append(f'const int SNN_CONN_{i}_TILED          = {c["tiled"]};')
            lines.append(f'const int SNN_CONN_{i}_NUM_WEIGHTS    = {c["num_weights"]};')
            lines.append(f'const int SNN_CONN_{i}_SRC_ID_START   = {c["src_id_start"]};')
            lines.append(f'const int SNN_CONN_{i}_DST_ID_START   = {c["dst_id_start"]};')
            lines.append(f'')
    else:
        lines += [
            f'// ─── Reference N×N weight memory (no connection topology defined) ─',
            f'const int SNN_MAX_WEIGHT_BUFFER_SIZE  = {derived["max_weight_buffer_size"]};',
            f'const int SNN_RESIDENT_WEIGHT_BUFFER_SIZE = {derived["resident_weight_buffer_size"]};',
            f'const int SNN_RESIDENT_WEIGHT_LOGICAL_ENTRIES = {derived["resident_weight_logical_entries"]};',
            f'const int SNN_TILED_WEIGHT_ENTRIES    = {derived["tiled_weight_entries"]};',
            f'const int SNN_NUM_CONNECTIONS         = 0;',
            f'const int SNN_NUM_NEURON_GROUPS       = 0;',
            f'#define SNN_NUM_NEURON_GROUPS_PP      0',
            f'#define SNN_NUM_CONNECTIONS_PP         0',
            f'',
        ]

    lines += [
        f'// ─── Resource-Aware Weight Memory ───────────',
        f'#define SNN_WEIGHT_BITS           {derived["weight_bits"]}',
        f'#define SNN_TIME_EMBEDDING        {derived["time_embedding"]}',
        f'#define SNN_AUXILIARY_LUTRAM      {derived["auxiliary_lutram"]}',
        f'#define SNN_TRACE_MAINTENANCE_ACTIVE_SET {derived["trace_maintenance_active_set"]}',
        f'#define SNN_TRACE_ACTIVE_CLEAR_THRESHOLD {derived["trace_active_clear_threshold"]}',
        f'const int SNN_PACKED_BUFFER_BYTES = {derived["packed_buffer_bytes"]};',
        f'',
        f'// ─── Weight Tiling (future large-network path) ───────────────────',
        f'#define SNN_WEIGHT_TILING_ENABLE {derived["weight_tiling_enable"]}',
        f'#define SNN_WEIGHT_TILING_LARGE_ONLY {derived["weight_tiling_large_only"]}',
        f'#define SNN_WEIGHT_TILING_LARGE_CONN_MIN_WEIGHTS {derived["weight_tiling_large_conn_min_weights"]}',
        f'#define SNN_WEIGHT_TILING_SRC_CHUNK {derived["weight_tiling_src_chunk"]}',
        f'#define SNN_WEIGHT_TILING_DST_CHUNK {derived["weight_tiling_dst_chunk"]}',
        f'#define SNN_WEIGHT_TILING_DOUBLE_BUFFER {derived["weight_tiling_double_buffer"]}',
        f'#define SNN_WEIGHT_TILING_ACTIVE_BUFFERS {derived["weight_tiling_active_buffers"]}',
        f'#define SNN_WEIGHT_TILING_ACTIVE_TILE_WEIGHTS {derived["weight_tiling_active_tile_weights"]}',
        f'#define SNN_WEIGHT_TILING_ACTIVE_TILE_BYTES {derived["weight_tiling_active_tile_bytes"]}',
        f'',
        f'// ─── Fixed-Point (ap_fixed<16,8>) ─────────────────────────────────',
        f'const int SNN_FIXED_POINT_FRAC_BITS = {hls["fixed_point_frac_bits"]};',
        f'const int SNN_FIXED_POINT_SCALE     = (1 << SNN_FIXED_POINT_FRAC_BITS);',
        f'',
        f'#endif // SPIKEMOLD_PARAMS_H',
    ]
    return '\n'.join(lines) + '\n'


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Generate RTL/Python/HLS parameter files from spikemold_params.yaml')
    parser.add_argument('--config', default=None,
                        help='Path to spikemold_params.yaml (auto-detected if not given)')
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
        config_path = project_root / 'config' / 'spikemold_params.yaml'

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
    print("SpikeMold Parameter Generator")
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
        'spikemold_params.vh': generate_verilog(cfg, derived),
        'spikemold_params.py': generate_python(cfg, derived),
        'spikemold_params.h':  generate_hls(cfg, derived),
    }

    for filename, content in files.items():
        filepath = out_dir / filename
        filepath.write_text(content)
        print(f"  Generated: {filepath}")

    print(f"\nDone. {len(files)} files generated.")


if __name__ == '__main__':
    main()
