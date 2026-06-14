//-----------------------------------------------------------------------------
// Title         : SpikeMold Top-Level HLS Header
// Project       : PYNQ-Z2 SpikeMold
// File          : spikemold_top_hls.h
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : Header for inference-only SpikeMold HLS top-level
//-----------------------------------------------------------------------------

#ifndef SPIKEMOLD_TOP_HLS_H
#define SPIKEMOLD_TOP_HLS_H

#include <ap_int.h>
#include <ap_fixed.h>
#include <ap_axi_sdata.h>
#include <hls_stream.h>

// Centralized parameters (source of truth: config/spikemold_params.yaml)
#include "spikemold_params.h"

//=============================================================================
// Configuration (derived from spikemold_params.h)
//=============================================================================
const int MAX_NEURONS    = SNN_MAX_NEURONS;                  // 16×128 = 2048

// --- population-aware weight buffer (Brian2-style) ---
// Replaces the old O(N²) dense weight_memory[MAX_NEURONS][MAX_NEURONS].
// Weight memory is now a flat buffer: Σ(src_size × dst_size) per connection.
const int MAX_WEIGHT_BUFFER_SIZE = SNN_MAX_WEIGHT_BUFFER_SIZE;
const int NUM_CONNECTIONS        = SNN_NUM_CONNECTIONS;
const int NUM_NEURON_GROUPS      = SNN_NUM_NEURON_GROUPS;
const int TOTAL_LOGICAL_NEURONS  = SNN_TOTAL_LOGICAL_NEURONS;

// Connection descriptor: defines one src_group→dst_group synaptic projection.
// Used by HLS to index into the flat weight_memory[] buffer.
struct SynapticConnection {
    int src_group;        // source SpikePress population index
    int dst_group;        // destination SpikePress population index
    int src_size;         // number of neurons in source group
    int dst_size;         // number of neurons in destination group
    int weight_offset;    // byte offset into flat weight_memory[]
    int num_weights;      // src_size * dst_size
    int src_id_start;     // global neuron ID of first neuron in src group
    int dst_id_start;     // global neuron ID of first neuron in dst group
};

// Static connection table (initialized from generated constants)
// Supports up to 8 connections for block-sparse topology (K=1024, 4 blocks)
static const SynapticConnection CONNECTION_TABLE[NUM_CONNECTIONS] = {
#if SNN_NUM_CONNECTIONS_PP >= 1
    { SNN_CONN_0_SRC_GROUP, SNN_CONN_0_DST_GROUP,
      SNN_CONN_0_SRC_SIZE,  SNN_CONN_0_DST_SIZE,
      SNN_CONN_0_WEIGHT_OFFSET, SNN_CONN_0_NUM_WEIGHTS,
      SNN_CONN_0_SRC_ID_START, SNN_CONN_0_DST_ID_START },
#endif
#if SNN_NUM_CONNECTIONS_PP >= 2
    { SNN_CONN_1_SRC_GROUP, SNN_CONN_1_DST_GROUP,
      SNN_CONN_1_SRC_SIZE,  SNN_CONN_1_DST_SIZE,
      SNN_CONN_1_WEIGHT_OFFSET, SNN_CONN_1_NUM_WEIGHTS,
      SNN_CONN_1_SRC_ID_START, SNN_CONN_1_DST_ID_START },
#endif
#if SNN_NUM_CONNECTIONS_PP >= 3
    { SNN_CONN_2_SRC_GROUP, SNN_CONN_2_DST_GROUP,
      SNN_CONN_2_SRC_SIZE,  SNN_CONN_2_DST_SIZE,
      SNN_CONN_2_WEIGHT_OFFSET, SNN_CONN_2_NUM_WEIGHTS,
      SNN_CONN_2_SRC_ID_START, SNN_CONN_2_DST_ID_START },
#endif
#if SNN_NUM_CONNECTIONS_PP >= 4
    { SNN_CONN_3_SRC_GROUP, SNN_CONN_3_DST_GROUP,
      SNN_CONN_3_SRC_SIZE,  SNN_CONN_3_DST_SIZE,
      SNN_CONN_3_WEIGHT_OFFSET, SNN_CONN_3_NUM_WEIGHTS,
      SNN_CONN_3_SRC_ID_START, SNN_CONN_3_DST_ID_START },
#endif
#if SNN_NUM_CONNECTIONS_PP >= 5
    { SNN_CONN_4_SRC_GROUP, SNN_CONN_4_DST_GROUP,
      SNN_CONN_4_SRC_SIZE,  SNN_CONN_4_DST_SIZE,
      SNN_CONN_4_WEIGHT_OFFSET, SNN_CONN_4_NUM_WEIGHTS,
      SNN_CONN_4_SRC_ID_START, SNN_CONN_4_DST_ID_START },
#endif
#if SNN_NUM_CONNECTIONS_PP >= 6
    { SNN_CONN_5_SRC_GROUP, SNN_CONN_5_DST_GROUP,
      SNN_CONN_5_SRC_SIZE,  SNN_CONN_5_DST_SIZE,
      SNN_CONN_5_WEIGHT_OFFSET, SNN_CONN_5_NUM_WEIGHTS,
      SNN_CONN_5_SRC_ID_START, SNN_CONN_5_DST_ID_START },
#endif
#if SNN_NUM_CONNECTIONS_PP >= 7
    { SNN_CONN_6_SRC_GROUP, SNN_CONN_6_DST_GROUP,
      SNN_CONN_6_SRC_SIZE,  SNN_CONN_6_DST_SIZE,
      SNN_CONN_6_WEIGHT_OFFSET, SNN_CONN_6_NUM_WEIGHTS,
      SNN_CONN_6_SRC_ID_START, SNN_CONN_6_DST_ID_START },
#endif
#if SNN_NUM_CONNECTIONS_PP >= 8
    { SNN_CONN_7_SRC_GROUP, SNN_CONN_7_DST_GROUP,
      SNN_CONN_7_SRC_SIZE,  SNN_CONN_7_DST_SIZE,
      SNN_CONN_7_WEIGHT_OFFSET, SNN_CONN_7_NUM_WEIGHTS,
      SNN_CONN_7_SRC_ID_START, SNN_CONN_7_DST_ID_START },
#endif
};

// Population ID start offsets (for global_id → local_id conversion)
// Supports up to 9 groups + 1 sentinel for block-sparse topology
static const int NG_ID_START[NUM_NEURON_GROUPS + 1] = {
    SNN_NG_ID_START_0,
    SNN_NG_ID_START_1,
    SNN_NG_ID_START_2,
#if SNN_NUM_NEURON_GROUPS_PP >= 4
    SNN_NG_ID_START_3,
#endif
#if SNN_NUM_NEURON_GROUPS_PP >= 5
    SNN_NG_ID_START_4,
#endif
#if SNN_NUM_NEURON_GROUPS_PP >= 6
    SNN_NG_ID_START_5,
#endif
#if SNN_NUM_NEURON_GROUPS_PP >= 7
    SNN_NG_ID_START_6,
#endif
#if SNN_NUM_NEURON_GROUPS_PP >= 8
    SNN_NG_ID_START_7,
#endif
#if SNN_NUM_NEURON_GROUPS_PP >= 9
    SNN_NG_ID_START_8,
#endif
#if SNN_NUM_NEURON_GROUPS_PP >= 10
    SNN_NG_ID_START_9,
#endif
    // Explicit sentinel avoids zero-initialized tail when group count changes.
    SNN_TOTAL_LOGICAL_NEURONS,
};

const int WEIGHT_WIDTH   = SNN_WEIGHT_WIDTH;                 // 8
const int RTL_NEURON_ID_WIDTH = SNN_NEURON_ID_WIDTH;         // 11 (RTL SpikeMold Coregroup global ID)
const int NEURON_ID_WIDTH = SNN_HLS_NEURON_ID_WIDTH;         // 13 (HLS logical neuron space, K=1024)
const int TIMESTAMP_WIDTH = 32;

// AXI Spike Packet Bit-Field Layout (32-bit total):
//   [NEURON_ID_WIDTH-1 : 0]          neuron_id  (13 bits, K=1024)
//   [NEURON_ID_WIDTH+7 : NEURON_ID_WIDTH]  weight     (8 bits)
//   [31 : NEURON_ID_WIDTH+8]         timestamp  (11 bits)
const int SPIKE_PKT_ID_LO  = 0;
const int SPIKE_PKT_ID_HI  = NEURON_ID_WIDTH - 1;
const int SPIKE_PKT_WGT_LO = NEURON_ID_WIDTH;
const int SPIKE_PKT_WGT_HI = NEURON_ID_WIDTH + 7;
const int SPIKE_PKT_TS_LO  = NEURON_ID_WIDTH + 8;
const int SPIKE_PKT_TS_HI  = 31;

//=============================================================================
// Resource-Aware Weight Memory Optimization
//=============================================================================
// WEIGHT_BITS: Configurable synapse precision (configurable per-backend limits).
//   8-bit: full precision (original), ~794 BRAM18K for N=2048
//   4-bit: reduced precision,            ~353 BRAM18K (halved)
//   2-bit: ultra-low precision,        ~177 BRAM18K (quartered)
//
// PACKED_BUFFER_BYTES: ceil(MAX_WEIGHT_BUFFER_SIZE * WEIGHT_BITS / 8)
//   The storage array is declared as ap_int<WEIGHT_BITS> flat entries,
//   letting HLS map to the most efficient BRAM configuration.
//
// TIME_EMBEDDING: remove per-neuron 16-bit timestamps.
//   Traces decay globally each timestep instead of lazily per-access.
//   Saves 16 bits × TOTAL_LOGICAL_NEURONS × 2 in BRAM.
//
// AUXILIARY_LUTRAM: Move traces & eligibility to distributed LUTRAM
//   instead of BRAM.  ~1,400 LUTs (2.6% of xc7z020) frees ~30 BRAM18K.
//=============================================================================
const int WEIGHT_BITS    = SNN_WEIGHT_BITS;                  // 4 (default)
const int PACKED_BUFFER_SIZE = SNN_MAX_WEIGHT_BUFFER_SIZE;   // logical entries

// Packed weight type: signed N-bit value stored per synapse
typedef ap_int<SNN_WEIGHT_BITS> packed_weight_t;

// Weight range depends on bit width
#if SNN_WEIGHT_BITS == 2
const packed_weight_t PACKED_MAX_WEIGHT = 1;     // 2-bit: [-2, 1]
const packed_weight_t PACKED_MIN_WEIGHT = -2;
#elif SNN_WEIGHT_BITS == 4
const packed_weight_t PACKED_MAX_WEIGHT = 7;     // 4-bit: [-8, 7]
const packed_weight_t PACKED_MIN_WEIGHT = -8;
#else  // SNN_WEIGHT_BITS == 8 (original)
const packed_weight_t PACKED_MAX_WEIGHT = 127;   // 8-bit: [-128, 127]
const packed_weight_t PACKED_MIN_WEIGHT = -128;
#endif

const int WEIGHT_SCALE   = 128;
const int VERSION_ID     = 0x20260221;

//=============================================================================
// Operation Modes (use #define for switch-case compatibility)
//=============================================================================
#define MODE_INFERENCE 0       // Forward inference only
#define MODE_CHECKPOINT 2      // Stream weights to DDR/PS
// mode_reg[31:16] can optionally hold checkpoint chunk size (words):
//   0 -> single-frame checkpoint (TLAST at final word only)
//   N -> emit TLAST every N words while streaming checkpoint packets

//=============================================================================
// Basic Data Types
//=============================================================================
typedef ap_uint<NEURON_ID_WIDTH> neuron_id_t;      // HLS logical neuron ID (13b, K=1024)
typedef ap_uint<RTL_NEURON_ID_WIDTH> rtl_nid_t;    // RTL coregroup ID (11b)
typedef ap_uint<SNN_GROUP_ID_WIDTH> group_id_t;
typedef ap_uint<SNN_LOCAL_ID_WIDTH> local_id_t;
typedef ap_uint<SNN_FANOUT_IDX_WIDTH> fanout_idx_t;
typedef ap_int<WEIGHT_WIDTH> weight_t;              // HLS AXI interface: signed 8-bit
typedef ap_uint<TIMESTAMP_WIDTH> spike_time_t;

// AXI-Stream packets still use 8-bit weight_t for interface compatibility.
// RTL spikemold_coregroup.v uses unsigned 8-bit magnitude [0, 255] + 1-bit exc/inh flag.
const packed_weight_t MAX_WEIGHT = PACKED_MAX_WEIGHT;
const packed_weight_t MIN_WEIGHT = PACKED_MIN_WEIGHT;

//=============================================================================
// AXI4-Stream Types
//=============================================================================
// Spike packet (AER over AXIS32) — parameterized bit-field layout:
//   [SPIKE_PKT_ID_HI : SPIKE_PKT_ID_LO]   neuron_id  (NEURON_ID_WIDTH bits)
//   [SPIKE_PKT_WGT_HI : SPIKE_PKT_WGT_LO] weight     (8 bits)
//   [SPIKE_PKT_TS_HI : SPIKE_PKT_TS_LO]   timestamp  (remaining bits)
typedef ap_axiu<32, 1, 1, 1> axis_spike_t;

// Weight-load packet (AXIS32):
//   [11:0]  pre_id
//   [23:12] post_id
//   [31:24] signed 8-bit weight
// The 12-bit ID fields match the compact AXIS32 loader path. Full logical IDs
// above 4095 must use table/bulk artifact loading instead of this stream.
const int WEIGHT_LOAD_PKT_ID_WIDTH = 12;
const int WEIGHT_LOAD_PKT_PRE_LO = 0;
const int WEIGHT_LOAD_PKT_PRE_HI = 11;
const int WEIGHT_LOAD_PKT_POST_LO = 12;
const int WEIGHT_LOAD_PKT_POST_HI = 23;
const int WEIGHT_LOAD_PKT_WGT_LO = 24;
const int WEIGHT_LOAD_PKT_WGT_HI = 31;
typedef ap_axiu<32, 1, 1, 1> axis_weight_t;

// Data packet (for encoder input frames) - 32-bit wide (4 pixels per beat)
typedef ap_axiu<32, 1, 1, 1> axis_data_t;

//=============================================================================
// Encoder Configuration
//=============================================================================
const int MAX_INPUT_CHANNELS = 784;  // 28x28 MNIST default
const int FRAME_LOAD_BEATS = (MAX_INPUT_CHANNELS + 3) / 4;  // 196 beats for 784 pixels (4 per beat)

typedef ap_uint<8> pixel_t;          // Single pixel value (0-255)

struct input_data_t {
    pixel_t pixels[MAX_INPUT_CHANNELS];  // Complete input frame
};

// Encoding types
#define ENC_NONE           0  // No encoding - direct spike input
#define ENC_DELTA_SIGMA    1  // Delta-sigma modulation (only HW encoder)
// Removed: ENC_RATE_POISSON, ENC_LATENCY — encode on host PC for area savings

struct encoder_config_t {
    ap_uint<4> encoding_type;        // 0=none, 1=delta-sigma
    ap_uint<16> delta_threshold;     // Delta-sigma: threshold for integration
    ap_uint<16> delta_decay;         // Delta-sigma: decay rate
    ap_uint<16> num_channels;        // Number of input channels
    weight_t default_weight;         // Default spike weight
};

//=============================================================================
// Main Function Declaration
//=============================================================================
void spikemold_top_hls(
    // AXI4-Lite Control Interface
    ap_uint<32> ctrl_reg,
    ap_uint<32> config_reg,
    ap_uint<32> mode_reg,
    ap_uint<32> time_steps_reg,
    encoder_config_t encoder_config,
    ap_uint<32> &status_reg,
    ap_uint<32> &spike_count_reg,
    ap_uint<32> &weight_sum_reg,
    ap_uint<32> &version_reg,
    
    // AXI4-Stream Spike Input (from PS)
    hls::stream<axis_spike_t> &s_axis_spikes,
    
    // AXI4-Stream Raw Data Input (for on-chip encoder) - 32-bit streaming
    hls::stream<axis_data_t> &s_axis_data,
    
    // AXI4-Stream Weight Write (for loading weights)
    hls::stream<axis_weight_t> &s_axis_weights,
    
    // AXI4-Stream Spike Output (to PS)
    hls::stream<axis_spike_t> &m_axis_spikes,
    
    // AXI4-Stream Weight Read (for debugging)
    hls::stream<axis_weight_t> &m_axis_weights,
    
    // Verilog Interface - Spike Input (to SpikeMold coregroup) - RTL-width IDs
    ap_uint<1> &spike_in_valid,
    rtl_nid_t &spike_in_neuron_id,
    ap_int<8> &spike_in_weight,
    ap_uint<1> spike_in_ready,
    
    // Verilog Interface - Spike Output (from SpikeMold coregroup) - RTL-width IDs
    ap_uint<1> spike_out_valid,
    rtl_nid_t spike_out_neuron_id,
    ap_int<8> spike_out_weight,
    ap_uint<1> &spike_out_ready,

    // Verilog Interface - Control signals
    ap_uint<1> &spikemold_enable,
    ap_uint<1> &spikemold_reset,
    ap_uint<16> &threshold_out,
    ap_uint<16> &leak_rate_out,
    
    // Verilog Interface - Status signals
    ap_uint<1> spikemold_ready,
    ap_uint<1> spikemold_busy
);

//=============================================================================
// Utility Functions
//=============================================================================
void write_weight(neuron_id_t pre_id, neuron_id_t post_id, packed_weight_t weight);
packed_weight_t read_weight(neuron_id_t pre_id, neuron_id_t post_id);
void load_weights_from_stream(hls::stream<axis_weight_t> &weight_stream, ap_uint<32> num_weights);

//=============================================================================
// SpikePress population Weight Access Helpers
// These convert global neuron IDs to flat buffer offsets via connection table.
//=============================================================================

// Find which SpikePress population a global neuron ID belongs to.
// Returns group index [0, NUM_NEURON_GROUPS), or -1 if not found.
static inline int find_neuron_group(neuron_id_t nid) {
    #pragma HLS INLINE
    for (int g = 0; g < NUM_NEURON_GROUPS; g++) {
        #pragma HLS UNROLL
        if ((int)nid >= NG_ID_START[g] && (int)nid < NG_ID_START[g + 1]) {
            return g;
        }
    }
    return -1;
}

// Find connection index for a (src_group, dst_group) pair.
// Returns connection index [0, NUM_CONNECTIONS), or -1 if not connected.
static inline int find_connection(int src_group, int dst_group) {
    #pragma HLS INLINE
    for (int c = 0; c < NUM_CONNECTIONS; c++) {
        #pragma HLS UNROLL
        if (CONNECTION_TABLE[c].src_group == src_group &&
            CONNECTION_TABLE[c].dst_group == dst_group) {
            return c;
        }
    }
    return -1;
}

// Compute flat buffer index for a (pre_id, post_id) pair.
// Returns offset into weight_memory[], or -1 if not connected.
static inline int weight_index(neuron_id_t pre_id, neuron_id_t post_id) {
    #pragma HLS INLINE
    int src_g = find_neuron_group(pre_id);
    int dst_g = find_neuron_group(post_id);
    if (src_g < 0 || dst_g < 0) return -1;

    int conn_idx = find_connection(src_g, dst_g);
    if (conn_idx < 0) return -1;

    const SynapticConnection &conn = CONNECTION_TABLE[conn_idx];
    int local_src = (int)pre_id - conn.src_id_start;
    int local_dst = (int)post_id - conn.dst_id_start;
    return conn.weight_offset + local_src * conn.dst_size + local_dst;
}

#endif // SPIKEMOLD_TOP_HLS_H
