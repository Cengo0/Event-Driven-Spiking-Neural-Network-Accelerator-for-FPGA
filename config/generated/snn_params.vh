// =============================================================================
// SNN Accelerator Parameters — AUTO-GENERATED from snn_params.yaml
// Generated: 2026-02-11 09:19:54
// DO NOT EDIT — modify config/snn_params.yaml and run generate_params.py
// =============================================================================

`ifndef SNN_PARAMS_VH
`define SNN_PARAMS_VH

// ─── Core Architecture ────────────────────────────────────────────
`define SNN_NUM_GROUPS          16
`define SNN_NEURONS_PER_GROUP   128   // max(group_sizes) — bus width driver
`define SNN_MAX_NEURONS_PER_GROUP 128
`define SNN_MAX_FANOUT_INTER    16
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
`define SNN_HLS_NEURON_ID_WIDTH 11
`define SNN_HLS_MAX_NEURONS     2048
`define SNN_HLS_WEIGHT_WIDTH    8

`endif // SNN_PARAMS_VH
