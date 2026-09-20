// =============================================================================
// SNN Accelerator Parameters — AUTO-GENERATED from snn_params.yaml
// Generated: 2026-09-20 00:16:18
// DO NOT EDIT — modify config/snn_params.yaml and run generate_params.py
// =============================================================================

`ifndef SNN_PARAMS_VH
`define SNN_PARAMS_VH

// ─── Core Architecture ────────────────────────────────────────────
`define SNN_NUM_GROUPS          3
`define SNN_NEURONS_PER_GROUP   256   // max(group_sizes) — bus width driver
`define SNN_MAX_NEURONS_PER_GROUP 256
`define SNN_MAX_FANOUT_INTER    256
`define SNN_SPIKE_BUFFER_DEPTH  64

// ─── Per-Group Neuron Counts ─────────────────────────────────────
`define SNN_GROUP_SIZE_0        256
`define SNN_GROUP_SIZE_1        256
`define SNN_GROUP_SIZE_2        16
`define SNN_GROUP_SIZE_3        256
`define SNN_GROUP_SIZE_4        256
`define SNN_GROUP_SIZE_5        256
`define SNN_GROUP_SIZE_6        256
`define SNN_GROUP_SIZE_7        256
`define SNN_GROUP_SIZE_8        256
`define SNN_GROUP_SIZE_9        256
`define SNN_GROUP_SIZE_10       256
`define SNN_GROUP_SIZE_11       256
`define SNN_GROUP_SIZE_12       256
`define SNN_GROUP_SIZE_13       256
`define SNN_GROUP_SIZE_14       256
`define SNN_GROUP_SIZE_15       256

// ─── Data Widths ───────────────────────────────────────────────────
`define SNN_DATA_WIDTH          16
`define SNN_WEIGHT_WIDTH        8
`define SNN_THRESHOLD_WIDTH     16
`define SNN_LEAK_WIDTH          8
`define SNN_REFRAC_WIDTH        8

// ─── Derived Bit Widths (computed from architecture) ───────────────
`define SNN_GROUP_ID_WIDTH      2
`define SNN_LOCAL_ID_WIDTH      8
`define SNN_GLOBAL_ID_WIDTH     10
`define SNN_FANOUT_IDX_WIDTH    8

// ─── Derived Counts ────────────────────────────────────────────────
`define SNN_MAX_NEURONS         528
`define SNN_TOTAL_NEURONS       528
`define SNN_CT_DATA_WIDTH       20
`define SNN_NEURON_STATE_WIDTH  24

// ─── Weight Representation ────────────────────────────────────────
`define SNN_MAX_WEIGHT          255
`define SNN_MIN_WEIGHT          0
`define SNN_WEIGHT_FLAG_WIDTH   9

// ─── HLS Interface ────────────────────────────────────────────────
`define SNN_HLS_NEURON_ID_WIDTH 10
`define SNN_HLS_MAX_NEURONS     528
`define SNN_HLS_WEIGHT_WIDTH    8

// ─── NeuronGroup Weight Buffer ─────────────────────────────────────
`define SNN_MAX_WEIGHT_BUFFER_SIZE 69632
`define SNN_NUM_CONNECTIONS       2
`define SNN_NUM_NEURON_GROUPS     3

// ─── Weight Memory Optimization (Loihi/TrueNorth/KIST) ──────────
`define SNN_WEIGHT_BITS           4
`define SNN_TIME_EMBEDDING        1
`define SNN_AUXILIARY_LUTRAM      1
`define SNN_PACKED_BUFFER_BYTES   34816

`endif // SNN_PARAMS_VH
