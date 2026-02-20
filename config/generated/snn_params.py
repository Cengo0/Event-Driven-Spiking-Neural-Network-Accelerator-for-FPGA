"""
SNN Accelerator Parameters — AUTO-GENERATED from snn_params.yaml

Generated: 2026-02-11 09:19:54
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

# ─── Fixed-Point (HLS ap_fixed<16,8>) ─────────────────────────────
FIXED_POINT_FRAC_BITS = 8
FIXED_POINT_SCALE     = 1 << FIXED_POINT_FRAC_BITS  # 256

# ─── Legacy 8-bit weight constants (backward compat) ──────────────
LEGACY_MAX_WEIGHT   = 127
LEGACY_MIN_WEIGHT   = -128
LEGACY_WEIGHT_SCALE = 128
WEIGHT_SCALE        = 256

# ─── FPGA Target ──────────────────────────────────────────────────
FPGA_PART           = "xc7z020clg400-1"
CLOCK_PERIOD_NS     = 10
BOARD               = "tul.com.tw:pynq-z2:part0:1.0"
