"""
SNN Accelerator Parameters — AUTO-GENERATED from snn_params.yaml

Generated: 2026-09-22 23:24:54
DO NOT EDIT — modify config/snn_params.yaml and run generate_params.py
"""

# ─── Core Architecture ─────────────────────────────────────────────
NUM_GROUPS          = 5
NEURONS_PER_GROUP   = 196   # max(GROUP_SIZES) — backward compat
MAX_NEURONS_PER_GROUP = 196
MAX_FANOUT_INTER    = 16
SPIKE_BUFFER_DEPTH  = 64

# ─── Per-Group Neuron Counts ────────────────────────────────────────
GROUP_SIZES         = [196, 196, 196, 196, 16]
TOTAL_NEURONS       = 800

# ─── Data Widths ────────────────────────────────────────────────────
DATA_WIDTH          = 16
WEIGHT_WIDTH        = 8
THRESHOLD_WIDTH     = 16
LEAK_WIDTH          = 8
REFRAC_WIDTH        = 8

# ─── Derived Bit Widths ─────────────────────────────────────────────
GROUP_ID_WIDTH      = 3   # clog2(5)
LOCAL_ID_WIDTH      = 8   # clog2(196)
GLOBAL_ID_WIDTH     = 11  # GROUP_ID_WIDTH + LOCAL_ID_WIDTH
FANOUT_IDX_WIDTH    = 4   # clog2(16)

# ─── Derived Counts ─────────────────────────────────────────────────
MAX_NEURONS         = 800  # sum(GROUP_SIZES)
CT_DATA_WIDTH       = 21  # 1+GROUP_ID+LOCAL_ID+WEIGHT+1
NEURON_STATE_WIDTH  = 24  # DATA_WIDTH + REFRAC_WIDTH

# ─── Weight Representation ────────────────────────────────────────
MAX_WEIGHT          = 255  # (1 << WEIGHT_WIDTH) - 1
MIN_WEIGHT          = 0
WEIGHT_FLAG_WIDTH   = 9   # WEIGHT_WIDTH + 1
MAX_WEIGHT_DELTA    = 255

# ─── HLS Interface ────────────────────────────────────────────────
HLS_NEURON_ID_WIDTH = 11
HLS_MAX_NEURONS     = 800
HLS_WEIGHT_WIDTH    = 8
NEURON_ID_WIDTH     = GLOBAL_ID_WIDTH  # Alias

# ─── NeuronGroup Connection Topology (Brian2-style) ────────────────
NUM_NEURON_GROUPS       = 5
NUM_CONNECTIONS         = 4
MAX_WEIGHT_BUFFER_SIZE  = 12544
MAX_SRC_NEURONS         = 196
MAX_DST_NEURONS         = 16
TOTAL_LOGICAL_NEURONS   = 800

NEURON_GROUP_NAMES  = ['layer2_g0', 'layer2_g1', 'layer2_g2', 'layer2_g3', 'layer3_output']
NEURON_GROUP_SIZES  = [196, 196, 196, 196, 16]
NEURON_GROUP_ID_START = [0, 196, 392, 588, 784, 800]

# Per-Connection metadata: list of dicts
CONNECTIONS = [
    {"name": "l2_g0_to_l3", "src_group": 0, "dst_group": 4, "src_size": 196, "dst_size": 16, "weight_offset": 0, "num_weights": 3136, "src_id_start": 0, "dst_id_start": 784},
    {"name": "l2_g1_to_l3", "src_group": 1, "dst_group": 4, "src_size": 196, "dst_size": 16, "weight_offset": 3136, "num_weights": 3136, "src_id_start": 196, "dst_id_start": 784},
    {"name": "l2_g2_to_l3", "src_group": 2, "dst_group": 4, "src_size": 196, "dst_size": 16, "weight_offset": 6272, "num_weights": 3136, "src_id_start": 392, "dst_id_start": 784},
    {"name": "l2_g3_to_l3", "src_group": 3, "dst_group": 4, "src_size": 196, "dst_size": 16, "weight_offset": 9408, "num_weights": 3136, "src_id_start": 588, "dst_id_start": 784},
]

# ─── Fixed-Point (HLS ap_fixed<16,8>) ─────────────────────────────
FIXED_POINT_FRAC_BITS = 8
FIXED_POINT_SCALE     = 1 << FIXED_POINT_FRAC_BITS  # 256

# ─── Legacy 8-bit weight constants (backward compat) ──────────────
LEGACY_MAX_WEIGHT   = 127
LEGACY_MIN_WEIGHT   = -128
LEGACY_WEIGHT_SCALE = 128
WEIGHT_SCALE        = 256

# ─── Weight Memory Optimization (Loihi/TrueNorth/KIST) ──────────
WEIGHT_BITS             = 4
PACKED_MAX_WEIGHT       = 7
PACKED_MIN_WEIGHT       = -8
TIME_EMBEDDING          = 1
AUXILIARY_LUTRAM         = 1
PACKED_BUFFER_BYTES     = 6272

# ─── FPGA Target ──────────────────────────────────────────────────
FPGA_PART           = "xc7z020clg400-1"
CLOCK_PERIOD_NS     = 10
BOARD               = "tul.com.tw:pynq-z2:part0:1.0"
