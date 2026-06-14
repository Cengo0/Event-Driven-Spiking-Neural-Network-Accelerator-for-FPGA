"""
SpikeMold Fabric Parameters - AUTO-GENERATED from snn_params.yaml

Generated deterministically from config/snn_params.yaml
DO NOT EDIT — modify config/snn_params.yaml and run generate_params.py
"""

# ─── Core Architecture ─────────────────────────────────────────────
NUM_GROUPS          = 16
NEURONS_PER_GROUP   = 128   # max(GROUP_SIZES)
MAX_NEURONS_PER_GROUP = 128
MAX_FANOUT_INTER    = 16
ROUTER_MAX_FANOUT   = 32
ROUTER_DELAY_WIDTH  = 8
ROUTER_USE_DIRECT_OFFSET_MAP = 0
ROUTER_USE_TABLE_FALLBACK = 0
ROUTER_DIRECT_MAP_WINDOWS = 4
ROUTER_CONN_RAM_STYLE = "block"
ROUTER_CONN_RAM_STYLE_DIST = 0
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
HLS_NEURON_ID_WIDTH = 13
HLS_MAX_NEURONS     = 2048
HLS_WEIGHT_WIDTH    = 8
HLS_LEARNING_ENABLE = 0
HLS_SMOKE_COMMANDS_ENABLE = 0
HLS_CNN_DESCRIPTOR_PAGE_ENABLE = 1
NEURON_ID_WIDTH     = GLOBAL_ID_WIDTH  # Alias

# ─── SpikePress Projection Topology ────────────────
NUM_NEURON_GROUPS       = 3
NUM_CONNECTIONS         = 1
MAX_WEIGHT_BUFFER_SIZE  = 262144
RESIDENT_WEIGHT_BUFFER_SIZE = 1
RESIDENT_WEIGHT_LOGICAL_ENTRIES = 0
TILED_WEIGHT_ENTRIES    = 262144
MAX_SRC_NEURONS         = 512
MAX_DST_NEURONS         = 512
TOTAL_LOGICAL_NEURONS   = 4890

NEURON_GROUP_NAMES  = ['visible_output', 'input', 'dummy_pad']
NEURON_GROUP_SIZES  = [512, 512, 3866]
NEURON_GROUP_ID_START = [0, 512, 1024, 4890]

# Per-Connection metadata: list of dicts
CONNECTIONS = [
    {"name": "input_to_visible_output", "src_group": 1, "dst_group": 0, "src_size": 512, "dst_size": 512, "weight_offset": 0, "resident_weight_offset": -1, "tiled": True, "num_weights": 262144, "src_id_start": 512, "dst_id_start": 0},
]

# ─── Fixed-Point (HLS ap_fixed<16,8>) ─────────────────────────────
FIXED_POINT_FRAC_BITS = 8
FIXED_POINT_SCALE     = 1 << FIXED_POINT_FRAC_BITS  # 256

# ─── Reference signed 8-bit packed weight constants ──────────────
REFERENCE_MAX_WEIGHT = 127
REFERENCE_MIN_WEIGHT = -128
REFERENCE_WEIGHT_SCALE = 128
WEIGHT_SCALE        = 256

# ─── Weight Memory Optimization (Loihi/TrueNorth/KIST) ──────────
WEIGHT_BITS             = 8
PACKED_MAX_WEIGHT       = 127
PACKED_MIN_WEIGHT       = -128
TIME_EMBEDDING          = 1
AUXILIARY_LUTRAM         = 1
TRACE_MAINTENANCE_MODE  = "global"
TRACE_MAINTENANCE_ACTIVE_SET = 0
TRACE_ACTIVE_CLEAR_THRESHOLD = 0
PACKED_BUFFER_BYTES     = 262144

# ─── Weight Tiling (future large-network path) ──────────────────
WEIGHT_TILING_ENABLE            = 1
WEIGHT_TILING_LARGE_ONLY        = 1
WEIGHT_TILING_LARGE_CONN_MIN_WEIGHTS = 65536
WEIGHT_TILING_SRC_CHUNK         = 196
WEIGHT_TILING_DST_CHUNK         = 128
WEIGHT_TILING_DOUBLE_BUFFER     = 0
WEIGHT_TILING_ACTIVE_BUFFERS    = 1
WEIGHT_TILING_ACTIVE_TILE_WEIGHTS = 25088
WEIGHT_TILING_ACTIVE_TILE_BYTES = 25088

# ─── FPGA Target ──────────────────────────────────────────────────
FPGA_PART           = "xc7z020clg400-1"
CLOCK_PERIOD_NS     = 12.5
BOARD               = "tul.com.tw:pynq-z2:part0:1.0"
