// =============================================================================
// SNN Accelerator Parameters — AUTO-GENERATED from snn_params.yaml
// Generated: 2026-02-22 16:30:32
// DO NOT EDIT — modify config/snn_params.yaml and run generate_params.py
// =============================================================================

#ifndef SNN_PARAMS_H
#define SNN_PARAMS_H

// ─── Core Architecture ────────────────────────────────────────────
const int SNN_NUM_GROUPS            = 16;
const int SNN_NEURONS_PER_GROUP     = 128;  // max(group_sizes)
const int SNN_MAX_NEURONS_PER_GROUP = 128;
const int SNN_MAX_FANOUT_INTER      = 16;
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

// ─── NeuronGroup Connection Topology (Brian2-style) ─────────────
const int SNN_NUM_NEURON_GROUPS      = 9;
const int SNN_NUM_CONNECTIONS         = 8;
#define SNN_NUM_NEURON_GROUPS_PP      9
#define SNN_NUM_CONNECTIONS_PP         8
const int SNN_MAX_WEIGHT_BUFFER_SIZE  = 843776;
const int SNN_MAX_SRC_NEURONS         = 1024;
const int SNN_MAX_DST_NEURONS         = 1024;
const int SNN_TOTAL_LOGICAL_NEURONS   = 4890;

// Per-NeuronGroup sizes
const int SNN_NG_SIZE_0 = 196;  // input_0
const int SNN_NG_SIZE_1 = 196;  // input_1
const int SNN_NG_SIZE_2 = 196;  // input_2
const int SNN_NG_SIZE_3 = 196;  // input_3
const int SNN_NG_SIZE_4 = 1024;  // hidden_0
const int SNN_NG_SIZE_5 = 1024;  // hidden_1
const int SNN_NG_SIZE_6 = 1024;  // hidden_2
const int SNN_NG_SIZE_7 = 1024;  // hidden_3
const int SNN_NG_SIZE_8 = 10;  // output

// NeuronGroup ID start offsets (cumulative)
const int SNN_NG_ID_START_0 = 0;
const int SNN_NG_ID_START_1 = 196;
const int SNN_NG_ID_START_2 = 392;
const int SNN_NG_ID_START_3 = 588;
const int SNN_NG_ID_START_4 = 784;
const int SNN_NG_ID_START_5 = 1808;
const int SNN_NG_ID_START_6 = 2832;
const int SNN_NG_ID_START_7 = 3856;
const int SNN_NG_ID_START_8 = 4880;
const int SNN_NG_ID_START_9 = 4890;

// Per-Connection parameters
// Connection 0: in0_to_hid0 (group 0 -> group 4)
const int SNN_CONN_0_SRC_GROUP      = 0;
const int SNN_CONN_0_DST_GROUP      = 4;
const int SNN_CONN_0_SRC_SIZE       = 196;
const int SNN_CONN_0_DST_SIZE       = 1024;
const int SNN_CONN_0_WEIGHT_OFFSET  = 0;
const int SNN_CONN_0_NUM_WEIGHTS    = 200704;
const int SNN_CONN_0_SRC_ID_START   = 0;
const int SNN_CONN_0_DST_ID_START   = 784;

// Connection 1: in1_to_hid1 (group 1 -> group 5)
const int SNN_CONN_1_SRC_GROUP      = 1;
const int SNN_CONN_1_DST_GROUP      = 5;
const int SNN_CONN_1_SRC_SIZE       = 196;
const int SNN_CONN_1_DST_SIZE       = 1024;
const int SNN_CONN_1_WEIGHT_OFFSET  = 200704;
const int SNN_CONN_1_NUM_WEIGHTS    = 200704;
const int SNN_CONN_1_SRC_ID_START   = 196;
const int SNN_CONN_1_DST_ID_START   = 1808;

// Connection 2: in2_to_hid2 (group 2 -> group 6)
const int SNN_CONN_2_SRC_GROUP      = 2;
const int SNN_CONN_2_DST_GROUP      = 6;
const int SNN_CONN_2_SRC_SIZE       = 196;
const int SNN_CONN_2_DST_SIZE       = 1024;
const int SNN_CONN_2_WEIGHT_OFFSET  = 401408;
const int SNN_CONN_2_NUM_WEIGHTS    = 200704;
const int SNN_CONN_2_SRC_ID_START   = 392;
const int SNN_CONN_2_DST_ID_START   = 2832;

// Connection 3: in3_to_hid3 (group 3 -> group 7)
const int SNN_CONN_3_SRC_GROUP      = 3;
const int SNN_CONN_3_DST_GROUP      = 7;
const int SNN_CONN_3_SRC_SIZE       = 196;
const int SNN_CONN_3_DST_SIZE       = 1024;
const int SNN_CONN_3_WEIGHT_OFFSET  = 602112;
const int SNN_CONN_3_NUM_WEIGHTS    = 200704;
const int SNN_CONN_3_SRC_ID_START   = 588;
const int SNN_CONN_3_DST_ID_START   = 3856;

// Connection 4: hid0_to_output (group 4 -> group 8)
const int SNN_CONN_4_SRC_GROUP      = 4;
const int SNN_CONN_4_DST_GROUP      = 8;
const int SNN_CONN_4_SRC_SIZE       = 1024;
const int SNN_CONN_4_DST_SIZE       = 10;
const int SNN_CONN_4_WEIGHT_OFFSET  = 802816;
const int SNN_CONN_4_NUM_WEIGHTS    = 10240;
const int SNN_CONN_4_SRC_ID_START   = 784;
const int SNN_CONN_4_DST_ID_START   = 4880;

// Connection 5: hid1_to_output (group 5 -> group 8)
const int SNN_CONN_5_SRC_GROUP      = 5;
const int SNN_CONN_5_DST_GROUP      = 8;
const int SNN_CONN_5_SRC_SIZE       = 1024;
const int SNN_CONN_5_DST_SIZE       = 10;
const int SNN_CONN_5_WEIGHT_OFFSET  = 813056;
const int SNN_CONN_5_NUM_WEIGHTS    = 10240;
const int SNN_CONN_5_SRC_ID_START   = 1808;
const int SNN_CONN_5_DST_ID_START   = 4880;

// Connection 6: hid2_to_output (group 6 -> group 8)
const int SNN_CONN_6_SRC_GROUP      = 6;
const int SNN_CONN_6_DST_GROUP      = 8;
const int SNN_CONN_6_SRC_SIZE       = 1024;
const int SNN_CONN_6_DST_SIZE       = 10;
const int SNN_CONN_6_WEIGHT_OFFSET  = 823296;
const int SNN_CONN_6_NUM_WEIGHTS    = 10240;
const int SNN_CONN_6_SRC_ID_START   = 2832;
const int SNN_CONN_6_DST_ID_START   = 4880;

// Connection 7: hid3_to_output (group 7 -> group 8)
const int SNN_CONN_7_SRC_GROUP      = 7;
const int SNN_CONN_7_DST_GROUP      = 8;
const int SNN_CONN_7_SRC_SIZE       = 1024;
const int SNN_CONN_7_DST_SIZE       = 10;
const int SNN_CONN_7_WEIGHT_OFFSET  = 833536;
const int SNN_CONN_7_NUM_WEIGHTS    = 10240;
const int SNN_CONN_7_SRC_ID_START   = 3856;
const int SNN_CONN_7_DST_ID_START   = 4880;

// ─── Weight Memory Optimization (Loihi/TrueNorth/KIST) ───────────
#define SNN_WEIGHT_BITS           4
#define SNN_TIME_EMBEDDING        1
#define SNN_AUXILIARY_LUTRAM      1
const int SNN_PACKED_BUFFER_BYTES = 421888;

// ─── Fixed-Point (ap_fixed<16,8>) ─────────────────────────────────
const int SNN_FIXED_POINT_FRAC_BITS = 8;
const int SNN_FIXED_POINT_SCALE     = (1 << SNN_FIXED_POINT_FRAC_BITS);

#endif // SNN_PARAMS_H
