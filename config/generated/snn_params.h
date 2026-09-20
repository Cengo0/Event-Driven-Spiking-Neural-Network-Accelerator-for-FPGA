// =============================================================================
// SNN Accelerator Parameters — AUTO-GENERATED from snn_params.yaml
// Generated: 2026-09-20 00:16:18
// DO NOT EDIT — modify config/snn_params.yaml and run generate_params.py
// =============================================================================

#ifndef SNN_PARAMS_H
#define SNN_PARAMS_H

// ─── Core Architecture ────────────────────────────────────────────
const int SNN_NUM_GROUPS            = 3;
const int SNN_NEURONS_PER_GROUP     = 256;  // max(group_sizes)
const int SNN_MAX_NEURONS_PER_GROUP = 256;
const int SNN_MAX_FANOUT_INTER      = 256;
const int SNN_SPIKE_BUFFER_DEPTH    = 64;
const int SNN_TOTAL_NEURONS         = 528;

// ─── Data Widths ───────────────────────────────────────────────────
const int SNN_DATA_WIDTH          = 16;
const int SNN_WEIGHT_WIDTH        = 8;
const int SNN_THRESHOLD_WIDTH     = 16;
const int SNN_LEAK_WIDTH          = 8;
const int SNN_REFRAC_WIDTH        = 8;

// ─── Derived Bit Widths ────────────────────────────────────────────
const int SNN_GROUP_ID_WIDTH      = 2;
const int SNN_LOCAL_ID_WIDTH      = 8;
const int SNN_GLOBAL_ID_WIDTH     = 10;
const int SNN_NEURON_ID_WIDTH     = 10;  // Alias
const int SNN_FANOUT_IDX_WIDTH    = 8;

// ─── Derived Counts ────────────────────────────────────────────────
const int SNN_MAX_NEURONS         = 528;
const int SNN_CT_DATA_WIDTH       = 20;
const int SNN_NEURON_STATE_WIDTH  = 24;

// ─── Weight Representation (RTL: unsigned magnitude + exc/inh flag) ─
const int SNN_RTL_MAX_WEIGHT      = 255;
const int SNN_RTL_MIN_WEIGHT      = 0;
const int SNN_WEIGHT_FLAG_WIDTH   = 9;

// ─── HLS Interface ────────────────────────────────────────────────
const int SNN_HLS_NEURON_ID_WIDTH = 10;
const int SNN_HLS_MAX_NEURONS     = 528;
const int SNN_HLS_WEIGHT_WIDTH    = 8;

// ─── NeuronGroup Connection Topology (Brian2-style) ─────────────
const int SNN_NUM_NEURON_GROUPS      = 3;
const int SNN_NUM_CONNECTIONS         = 2;
#define SNN_NUM_NEURON_GROUPS_PP      3
#define SNN_NUM_CONNECTIONS_PP         2
const int SNN_MAX_WEIGHT_BUFFER_SIZE  = 69632;
const int SNN_MAX_SRC_NEURONS         = 256;
const int SNN_MAX_DST_NEURONS         = 256;
const int SNN_TOTAL_LOGICAL_NEURONS   = 528;

// Per-NeuronGroup sizes
const int SNN_NG_SIZE_0 = 256;  // layer1_relay
const int SNN_NG_SIZE_1 = 256;  // layer2_hidden
const int SNN_NG_SIZE_2 = 16;  // layer3_output

// NeuronGroup ID start offsets (cumulative)
const int SNN_NG_ID_START_0 = 0;
const int SNN_NG_ID_START_1 = 256;
const int SNN_NG_ID_START_2 = 512;
const int SNN_NG_ID_START_3 = 528;

// Per-Connection parameters
// Connection 0: l1_to_l2 (group 0 -> group 1)
const int SNN_CONN_0_SRC_GROUP      = 0;
const int SNN_CONN_0_DST_GROUP      = 1;
const int SNN_CONN_0_SRC_SIZE       = 256;
const int SNN_CONN_0_DST_SIZE       = 256;
const int SNN_CONN_0_WEIGHT_OFFSET  = 0;
const int SNN_CONN_0_NUM_WEIGHTS    = 65536;
const int SNN_CONN_0_SRC_ID_START   = 0;
const int SNN_CONN_0_DST_ID_START   = 256;

// Connection 1: l2_to_l3 (group 1 -> group 2)
const int SNN_CONN_1_SRC_GROUP      = 1;
const int SNN_CONN_1_DST_GROUP      = 2;
const int SNN_CONN_1_SRC_SIZE       = 256;
const int SNN_CONN_1_DST_SIZE       = 16;
const int SNN_CONN_1_WEIGHT_OFFSET  = 65536;
const int SNN_CONN_1_NUM_WEIGHTS    = 4096;
const int SNN_CONN_1_SRC_ID_START   = 256;
const int SNN_CONN_1_DST_ID_START   = 512;

// ─── Weight Memory Optimization (Loihi/TrueNorth/KIST) ───────────
#define SNN_WEIGHT_BITS           4
#define SNN_TIME_EMBEDDING        1
#define SNN_AUXILIARY_LUTRAM      1
const int SNN_PACKED_BUFFER_BYTES = 34816;

// ─── Fixed-Point (ap_fixed<16,8>) ─────────────────────────────────
const int SNN_FIXED_POINT_FRAC_BITS = 8;
const int SNN_FIXED_POINT_SCALE     = (1 << SNN_FIXED_POINT_FRAC_BITS);

#endif // SNN_PARAMS_H
