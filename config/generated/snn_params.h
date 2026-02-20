// =============================================================================
// SNN Accelerator Parameters — AUTO-GENERATED from snn_params.yaml
// Generated: 2026-02-11 09:19:54
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
const int SNN_HLS_NEURON_ID_WIDTH = 11;
const int SNN_HLS_MAX_NEURONS     = 2048;
const int SNN_HLS_WEIGHT_WIDTH    = 8;

// ─── Fixed-Point (ap_fixed<16,8>) ─────────────────────────────────
const int SNN_FIXED_POINT_FRAC_BITS = 8;
const int SNN_FIXED_POINT_SCALE     = (1 << SNN_FIXED_POINT_FRAC_BITS);

#endif // SNN_PARAMS_H
