// =============================================================================
// SpikeMold Fabric Parameters - AUTO-GENERATED from spikemold_params.yaml
// Generated deterministically from config/spikemold_params.yaml
// DO NOT EDIT — modify config/spikemold_params.yaml and run generate_params.py
// =============================================================================

`ifndef SPIKEMOLD_PARAMS_VH
`define SPIKEMOLD_PARAMS_VH

// ─── Core Architecture ────────────────────────────────────────────
`define SNN_NUM_GROUPS          16
`define SNN_NEURONS_PER_GROUP   128   // max(group_sizes) — bus width driver
`define SNN_MAX_NEURONS_PER_GROUP 128
`define SNN_MAX_FANOUT_INTER    16
`define SNN_ROUTER_MAX_FANOUT   32
`define SNN_ROUTER_DELAY_WIDTH  8
`define SNN_ROUTER_USE_DIRECT_OFFSET_MAP 0
`define SNN_ROUTER_USE_TABLE_FALLBACK 0
`define SNN_ROUTER_DIRECT_MAP_WINDOWS 4
`define SNN_ROUTER_CONN_RAM_STYLE_DIST 0
`define SNN_SPIKE_BUFFER_DEPTH  64

// ─── Per-Group Neuron Counts ─────────────────────────────────────
`define SNN_GROUP_SIZE_0        128
`define SNN_GROUP_SIZE_1        128
`define SNN_GROUP_SIZE_2        128
`define SNN_GROUP_SIZE_3        128
`define SNN_GROUP_SIZE_4        128
`define SNN_GROUP_SIZE_5        128
`define SNN_GROUP_SIZE_6        128
`define SNN_GROUP_SIZE_7        128
`define SNN_GROUP_SIZE_8        128
`define SNN_GROUP_SIZE_9        128
`define SNN_GROUP_SIZE_10       128
`define SNN_GROUP_SIZE_11       128
`define SNN_GROUP_SIZE_12       128
`define SNN_GROUP_SIZE_13       128
`define SNN_GROUP_SIZE_14       128
`define SNN_GROUP_SIZE_15       128

// ─── Data Widths ───────────────────────────────────────────────────
`define SNN_DATA_WIDTH          16
`define SNN_WEIGHT_WIDTH        8
`define SNN_THRESHOLD_WIDTH     16
`define SNN_LEAK_WIDTH          8
`define SNN_REFRAC_WIDTH        8

// ─── Derived Bit Widths (computed from architecture) ───────────────
`define SNN_GROUP_ID_WIDTH      4
`define SNN_LOCAL_ID_WIDTH      7
`define SNN_GLOBAL_ID_WIDTH     11
`define SNN_FANOUT_IDX_WIDTH    4

// ─── Derived Counts ────────────────────────────────────────────────
`define SNN_MAX_NEURONS         2048
`define SNN_TOTAL_NEURONS       2048
`define SNN_CT_DATA_WIDTH       21
`define SNN_NEURON_STATE_WIDTH  24

// ─── Weight Representation ────────────────────────────────────────
`define SNN_MAX_WEIGHT          255
`define SNN_MIN_WEIGHT          0
`define SNN_WEIGHT_FLAG_WIDTH   9

// ─── HLS Interface ────────────────────────────────────────────────
`define SNN_HLS_NEURON_ID_WIDTH 13
`define SNN_HLS_MAX_NEURONS     2048
`define SNN_HLS_WEIGHT_WIDTH    8
`define SNN_HLS_LEARNING_ENABLE 0
`define SNN_HLS_SMOKE_COMMANDS_ENABLE 0
`define SNN_HLS_CNN_DESCRIPTOR_PAGE_ENABLE 1

// ─── SpikePress Weight Buffer ─────────────────────────────────────
`define SNN_MAX_WEIGHT_BUFFER_SIZE 262144
`define SNN_RESIDENT_WEIGHT_BUFFER_SIZE 1
`define SNN_RESIDENT_WEIGHT_LOGICAL_ENTRIES 0
`define SNN_TILED_WEIGHT_ENTRIES 262144
`define SNN_NUM_CONNECTIONS       1
`define SNN_NUM_NEURON_GROUPS     3

// ─── Resource-Aware Weight Memory ──────────
`define SNN_WEIGHT_BITS           8
`define SNN_TIME_EMBEDDING        1
`define SNN_AUXILIARY_LUTRAM      1
`define SNN_TRACE_MAINTENANCE_ACTIVE_SET 0
`define SNN_TRACE_ACTIVE_CLEAR_THRESHOLD 0
`define SNN_PACKED_BUFFER_BYTES   262144

// ─── Weight Tiling (future large-network path) ───────────────────
`define SNN_WEIGHT_TILING_ENABLE  1
`define SNN_WEIGHT_TILING_LARGE_ONLY 1
`define SNN_WEIGHT_TILING_LARGE_CONN_MIN_WEIGHTS 65536
`define SNN_WEIGHT_TILING_SRC_CHUNK 196
`define SNN_WEIGHT_TILING_DST_CHUNK 128
`define SNN_WEIGHT_TILING_DOUBLE_BUFFER 0
`define SNN_WEIGHT_TILING_ACTIVE_BUFFERS 1
`define SNN_WEIGHT_TILING_ACTIVE_TILE_WEIGHTS 25088
`define SNN_WEIGHT_TILING_ACTIVE_TILE_BYTES 25088

`endif // SPIKEMOLD_PARAMS_VH
