// =============================================================================
// SNN Accelerator Parameters — AUTO-GENERATED from snn_params.yaml
// Generated: 2026-09-22 23:24:54
// DO NOT EDIT — modify config/snn_params.yaml and run generate_params.py
// =============================================================================

#ifndef SNN_PARAMS_H
#define SNN_PARAMS_H

// ─── Core Architecture ────────────────────────────────────────────
const int SNN_NUM_GROUPS            = 5;
const int SNN_NEURONS_PER_GROUP     = 196;  // max(group_sizes)
const int SNN_MAX_NEURONS_PER_GROUP = 196;
const int SNN_MAX_FANOUT_INTER      = 16;
const int SNN_SPIKE_BUFFER_DEPTH    = 64;
const int SNN_TOTAL_NEURONS         = 800;

// ─── Data Widths ───────────────────────────────────────────────────
const int SNN_DATA_WIDTH          = 16;
const int SNN_WEIGHT_WIDTH        = 8;
const int SNN_THRESHOLD_WIDTH     = 16;
const int SNN_LEAK_WIDTH          = 8;
const int SNN_REFRAC_WIDTH        = 8;

// ─── Derived Bit Widths ────────────────────────────────────────────
const int SNN_GROUP_ID_WIDTH      = 3;
const int SNN_LOCAL_ID_WIDTH      = 8;
const int SNN_GLOBAL_ID_WIDTH     = 11;
const int SNN_NEURON_ID_WIDTH     = 11;  // Alias
const int SNN_FANOUT_IDX_WIDTH    = 4;

// ─── Derived Counts ────────────────────────────────────────────────
const int SNN_MAX_NEURONS         = 800;
const int SNN_CT_DATA_WIDTH       = 21;
const int SNN_NEURON_STATE_WIDTH  = 24;

// ─── Weight Representation (RTL: unsigned magnitude + exc/inh flag) ─
const int SNN_RTL_MAX_WEIGHT      = 255;
const int SNN_RTL_MIN_WEIGHT      = 0;
const int SNN_WEIGHT_FLAG_WIDTH   = 9;

// ─── HLS Interface ────────────────────────────────────────────────
const int SNN_HLS_NEURON_ID_WIDTH = 11;
const int SNN_HLS_MAX_NEURONS     = 800;
const int SNN_HLS_WEIGHT_WIDTH    = 8;

// ─── NeuronGroup Connection Topology (Brian2-style) ─────────────
const int SNN_NUM_NEURON_GROUPS      = 5;
const int SNN_NUM_CONNECTIONS         = 4;
#define SNN_NUM_NEURON_GROUPS_PP      5
#define SNN_NUM_CONNECTIONS_PP         4
const int SNN_MAX_WEIGHT_BUFFER_SIZE  = 12544;
const int SNN_MAX_SRC_NEURONS         = 196;
const int SNN_MAX_DST_NEURONS         = 16;
const int SNN_TOTAL_LOGICAL_NEURONS   = 800;

// Per-NeuronGroup sizes
const int SNN_NG_SIZE_0 = 196;  // layer2_g0
const int SNN_NG_SIZE_1 = 196;  // layer2_g1
const int SNN_NG_SIZE_2 = 196;  // layer2_g2
const int SNN_NG_SIZE_3 = 196;  // layer2_g3
const int SNN_NG_SIZE_4 = 16;  // layer3_output

// NeuronGroup ID start offsets (cumulative)
const int SNN_NG_ID_START_0 = 0;
const int SNN_NG_ID_START_1 = 196;
const int SNN_NG_ID_START_2 = 392;
const int SNN_NG_ID_START_3 = 588;
const int SNN_NG_ID_START_4 = 784;
const int SNN_NG_ID_START_5 = 800;

// Per-Connection parameters
// Connection 0: l2_g0_to_l3 (group 0 -> group 4)
const int SNN_CONN_0_SRC_GROUP      = 0;
const int SNN_CONN_0_DST_GROUP      = 4;
const int SNN_CONN_0_SRC_SIZE       = 196;
const int SNN_CONN_0_DST_SIZE       = 16;
const int SNN_CONN_0_WEIGHT_OFFSET  = 0;
const int SNN_CONN_0_NUM_WEIGHTS    = 3136;
const int SNN_CONN_0_SRC_ID_START   = 0;
const int SNN_CONN_0_DST_ID_START   = 784;

// Connection 1: l2_g1_to_l3 (group 1 -> group 4)
const int SNN_CONN_1_SRC_GROUP      = 1;
const int SNN_CONN_1_DST_GROUP      = 4;
const int SNN_CONN_1_SRC_SIZE       = 196;
const int SNN_CONN_1_DST_SIZE       = 16;
const int SNN_CONN_1_WEIGHT_OFFSET  = 3136;
const int SNN_CONN_1_NUM_WEIGHTS    = 3136;
const int SNN_CONN_1_SRC_ID_START   = 196;
const int SNN_CONN_1_DST_ID_START   = 784;

// Connection 2: l2_g2_to_l3 (group 2 -> group 4)
const int SNN_CONN_2_SRC_GROUP      = 2;
const int SNN_CONN_2_DST_GROUP      = 4;
const int SNN_CONN_2_SRC_SIZE       = 196;
const int SNN_CONN_2_DST_SIZE       = 16;
const int SNN_CONN_2_WEIGHT_OFFSET  = 6272;
const int SNN_CONN_2_NUM_WEIGHTS    = 3136;
const int SNN_CONN_2_SRC_ID_START   = 392;
const int SNN_CONN_2_DST_ID_START   = 784;

// Connection 3: l2_g3_to_l3 (group 3 -> group 4)
const int SNN_CONN_3_SRC_GROUP      = 3;
const int SNN_CONN_3_DST_GROUP      = 4;
const int SNN_CONN_3_SRC_SIZE       = 196;
const int SNN_CONN_3_DST_SIZE       = 16;
const int SNN_CONN_3_WEIGHT_OFFSET  = 9408;
const int SNN_CONN_3_NUM_WEIGHTS    = 3136;
const int SNN_CONN_3_SRC_ID_START   = 588;
const int SNN_CONN_3_DST_ID_START   = 784;

// ─── Weight Memory Optimization (Loihi/TrueNorth/KIST) ───────────
#define SNN_WEIGHT_BITS           4
#define SNN_TIME_EMBEDDING        1
#define SNN_AUXILIARY_LUTRAM      1
const int SNN_PACKED_BUFFER_BYTES = 6272;

// ─── Fixed-Point (ap_fixed<16,8>) ─────────────────────────────────
const int SNN_FIXED_POINT_FRAC_BITS = 8;
const int SNN_FIXED_POINT_SCALE     = (1 << SNN_FIXED_POINT_FRAC_BITS);

#endif // SNN_PARAMS_H
