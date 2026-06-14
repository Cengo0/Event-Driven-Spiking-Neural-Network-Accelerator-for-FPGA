// =============================================================================
// SpikeMold Fabric Parameters - AUTO-GENERATED from spikemold_params.yaml
// Generated deterministically from config/spikemold_params.yaml
// DO NOT EDIT — modify config/spikemold_params.yaml and run generate_params.py
// =============================================================================

#ifndef SPIKEMOLD_PARAMS_H
#define SPIKEMOLD_PARAMS_H

// ─── Core Architecture ────────────────────────────────────────────
const int SNN_NUM_GROUPS            = 16;
const int SNN_NEURONS_PER_GROUP     = 128;  // max(group_sizes)
const int SNN_MAX_NEURONS_PER_GROUP = 128;
const int SNN_MAX_FANOUT_INTER      = 16;
const int SNN_ROUTER_MAX_FANOUT     = 32;
const int SNN_ROUTER_DELAY_WIDTH    = 8;
const int SNN_ROUTER_USE_DIRECT_OFFSET_MAP = 0;
const int SNN_ROUTER_USE_TABLE_FALLBACK = 0;
const int SNN_ROUTER_DIRECT_MAP_WINDOWS = 4;
const int SNN_ROUTER_CONN_RAM_STYLE_DIST = 0;
const int SNN_SPIKE_BUFFER_DEPTH    = 64;
const int SNN_TOTAL_NEURONS         = 2048;

// ─── Data Widths ───────────────────────────────────────────────────
const int SNN_DATA_WIDTH          = 16;
const int SNN_WEIGHT_WIDTH        = 8;
const int SNN_THRESHOLD_WIDTH     = 16;
const int SNN_LEAK_WIDTH          = 8;
const int SNN_REFRAC_WIDTH        = 8;

// ─── Derived Bit Widths ────────────────────────────────────────────
const int SNN_GROUP_ID_WIDTH      = 4;
const int SNN_LOCAL_ID_WIDTH      = 7;
const int SNN_GLOBAL_ID_WIDTH     = 11;
const int SNN_NEURON_ID_WIDTH     = 11;  // Alias
const int SNN_FANOUT_IDX_WIDTH    = 4;

// ─── Derived Counts ────────────────────────────────────────────────
const int SNN_MAX_NEURONS         = 2048;
const int SNN_CT_DATA_WIDTH       = 21;
const int SNN_NEURON_STATE_WIDTH  = 24;

// ─── Weight Representation (RTL: unsigned magnitude + exc/inh flag) ─
const int SNN_RTL_MAX_WEIGHT      = 255;
const int SNN_RTL_MIN_WEIGHT      = 0;
const int SNN_WEIGHT_FLAG_WIDTH   = 9;

// ─── HLS Interface ────────────────────────────────────────────────
const int SNN_HLS_NEURON_ID_WIDTH = 13;
const int SNN_HLS_MAX_NEURONS     = 2048;
const int SNN_HLS_WEIGHT_WIDTH    = 8;
#ifndef SNN_HLS_SMOKE_COMMANDS_ENABLE
#define SNN_HLS_SMOKE_COMMANDS_ENABLE 0
#endif
#ifndef SNN_HLS_CNN_DESCRIPTOR_PAGE_ENABLE
#define SNN_HLS_CNN_DESCRIPTOR_PAGE_ENABLE 1
#endif

// ─── SpikePress Projection Topology ─────────────
const int SNN_NUM_NEURON_GROUPS      = 3;
const int SNN_NUM_CONNECTIONS         = 1;
#define SNN_NUM_NEURON_GROUPS_PP      3
#define SNN_NUM_CONNECTIONS_PP         1
const int SNN_MAX_WEIGHT_BUFFER_SIZE  = 262144;
const int SNN_RESIDENT_WEIGHT_BUFFER_SIZE = 1;
const int SNN_RESIDENT_WEIGHT_LOGICAL_ENTRIES = 0;
const int SNN_TILED_WEIGHT_ENTRIES    = 262144;
const int SNN_MAX_SRC_NEURONS         = 512;
const int SNN_MAX_DST_NEURONS         = 512;
const int SNN_TOTAL_LOGICAL_NEURONS   = 4890;

// Per-population sizes
const int SNN_NG_SIZE_0 = 512;  // visible_output
const int SNN_NG_SIZE_1 = 512;  // input
const int SNN_NG_SIZE_2 = 3866;  // capacity_reserve

// Population ID start offsets (cumulative)
const int SNN_NG_ID_START_0 = 0;
const int SNN_NG_ID_START_1 = 512;
const int SNN_NG_ID_START_2 = 1024;
const int SNN_NG_ID_START_3 = 4890;

// Per-Connection parameters
// Connection 0: input_to_visible_output (group 1 -> group 0)
const int SNN_CONN_0_SRC_GROUP      = 1;
const int SNN_CONN_0_DST_GROUP      = 0;
const int SNN_CONN_0_SRC_SIZE       = 512;
const int SNN_CONN_0_DST_SIZE       = 512;
const int SNN_CONN_0_WEIGHT_OFFSET  = 0;
const int SNN_CONN_0_RESIDENT_WEIGHT_OFFSET = -1;
const int SNN_CONN_0_TILED          = 1;
const int SNN_CONN_0_NUM_WEIGHTS    = 262144;
const int SNN_CONN_0_SRC_ID_START   = 512;
const int SNN_CONN_0_DST_ID_START   = 0;

// ─── Resource-Aware Weight Memory ───────────
#define SNN_WEIGHT_BITS           8
#define SNN_TIME_EMBEDDING        1
#define SNN_AUXILIARY_LUTRAM      1
#define SNN_TRACE_MAINTENANCE_ACTIVE_SET 0
#define SNN_TRACE_ACTIVE_CLEAR_THRESHOLD 0
const int SNN_PACKED_BUFFER_BYTES = 262144;

// ─── Weight Tiling (future large-network path) ───────────────────
#define SNN_WEIGHT_TILING_ENABLE 1
#define SNN_WEIGHT_TILING_LARGE_ONLY 1
#define SNN_WEIGHT_TILING_LARGE_CONN_MIN_WEIGHTS 65536
#define SNN_WEIGHT_TILING_SRC_CHUNK 196
#define SNN_WEIGHT_TILING_DST_CHUNK 128
#define SNN_WEIGHT_TILING_DOUBLE_BUFFER 0
#define SNN_WEIGHT_TILING_ACTIVE_BUFFERS 1
#define SNN_WEIGHT_TILING_ACTIVE_TILE_WEIGHTS 25088
#define SNN_WEIGHT_TILING_ACTIVE_TILE_BYTES 25088

// ─── Fixed-Point (ap_fixed<16,8>) ─────────────────────────────────
const int SNN_FIXED_POINT_FRAC_BITS = 8;
const int SNN_FIXED_POINT_SCALE     = (1 << SNN_FIXED_POINT_FRAC_BITS);

#endif // SPIKEMOLD_PARAMS_H
