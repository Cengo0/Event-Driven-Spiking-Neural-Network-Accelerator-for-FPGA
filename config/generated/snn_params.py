"""
SNN Accelerator Parameters — AUTO-GENERATED from snn_params.yaml

Generated: 2026-09-16 14:58:27
DO NOT EDIT — modify config/snn_params.yaml and run generate_params.py
"""

# ─── Core Architecture ─────────────────────────────────────────────
NUM_GROUPS          = 16
NEURONS_PER_GROUP   = 128   # max(GROUP_SIZES) — backward compat
MAX_NEURONS_PER_GROUP = 128
MAX_FANOUT_INTER    = 16
SPIKE_BUFFER_DEPTH  = 64

# ─── Per-Group Neuron Counts ────────────────────────────────────────
GROUP_SIZES         = [128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128]
TOTAL_NEURONS       = 2048

# ─── Data Widths ────────────────────────────────────────────────────
DATA_WIDTH          = 16
WEIGHT_WIDTH        = 8
THRESHOLD_WIDTH     = 16
LEAK_WIDTH          = 8
REFRAC_WIDTH        = 8

# ─── Derived Bit Widths ─────────────────────────────────────────────
GROUP_ID_WIDTH      = 4   # clog2(16)
LOCAL_ID_WIDTH      = 7   # clog2(128)
GLOBAL_ID_WIDTH     = 11  # GROUP_ID_WIDTH + LOCAL_ID_WIDTH
FANOUT_IDX_WIDTH    = 4   # clog2(16)

# ─── Derived Counts ─────────────────────────────────────────────────
MAX_NEURONS         = 2048  # sum(GROUP_SIZES)
CT_DATA_WIDTH       = 21  # 1+GROUP_ID+LOCAL_ID+WEIGHT+1
NEURON_STATE_WIDTH  = 24  # DATA_WIDTH + REFRAC_WIDTH

# ─── Weight Representation ────────────────────────────────────────
MAX_WEIGHT          = 255  # (1 << WEIGHT_WIDTH) - 1
MIN_WEIGHT          = 0
WEIGHT_FLAG_WIDTH   = 9   # WEIGHT_WIDTH + 1
MAX_WEIGHT_DELTA    = 255

# ─── HLS Interface ────────────────────────────────────────────────
HLS_NEURON_ID_WIDTH = 11
HLS_MAX_NEURONS     = 2048
HLS_WEIGHT_WIDTH    = 8
NEURON_ID_WIDTH     = GLOBAL_ID_WIDTH  # Alias

# ─── NeuronGroup Connection Topology (Brian2-style) ────────────────
NUM_NEURON_GROUPS       = 4
NUM_CONNECTIONS         = 3
MAX_WEIGHT_BUFFER_SIZE  = 268800
MAX_SRC_NEURONS         = 784
MAX_DST_NEURONS         = 256
TOTAL_LOGICAL_NEURONS   = 1306

NEURON_GROUP_NAMES  = ['input_0', 'hidden_0', 'hidden_1', 'output']
NEURON_GROUP_SIZES  = [784, 256, 256, 10]
NEURON_GROUP_ID_START = [0, 784, 1040, 1296, 1306]

# Per-Connection metadata: list of dicts
CONNECTIONS = [
    {"name": "in_to_hid0", "src_group": 0, "dst_group": 1, "src_size": 784, "dst_size": 256, "weight_offset": 0, "num_weights": 200704, "src_id_start": 0, "dst_id_start": 784},
    {"name": "hid0_to_hid1", "src_group": 1, "dst_group": 2, "src_size": 256, "dst_size": 256, "weight_offset": 200704, "num_weights": 65536, "src_id_start": 784, "dst_id_start": 1040},
    {"name": "hid1_to_out", "src_group": 2, "dst_group": 3, "src_size": 256, "dst_size": 10, "weight_offset": 266240, "num_weights": 2560, "src_id_start": 1040, "dst_id_start": 1296},
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
PACKED_BUFFER_BYTES     = 134400

# ─── FPGA Target ──────────────────────────────────────────────────
FPGA_PART           = "xc7z020clg400-1"
CLOCK_PERIOD_NS     = 10
BOARD               = "tul.com.tw:pynq-z2:part0:1.0"
