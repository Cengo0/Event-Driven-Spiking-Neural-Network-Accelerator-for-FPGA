//-----------------------------------------------------------------------------
// Title         : SpikeMold-EDNP HLS Module with On-Chip Learning
// Project       : SpikeMold-EDNP
// File          : snn_top_hls.cpp
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : Unified HLS top-level integrating:
//                 - AXI4-Lite control/status registers
//                 - AXI4-Stream spike I/O (AER: Address Event Representation)
//                 - STDP/R-STDP on-chip learning engine
//                 - Per-Neuron Trace (NOT Per-Synapse) for memory efficiency
//                 - Lazy Update with timestamp-based decay
//                 - Weight memory management
//                 - Direct interface to Verilog SNN core
//-----------------------------------------------------------------------------

#include "../include/snn_top_hls.h"

//=============================================================================
// Delta-Sigma Spike Encoder (only HW encoder retained for area savings)
// Rate/Latency/Two-Neuron encoders removed — do those on host PC instead
//=============================================================================
// Local axis word for encoder stream (avoid ap_axiu on non-port streams)
typedef struct {
    ap_uint<32> data;
    ap_uint<4> keep;
    ap_uint<4> strb;
    ap_uint<1> last;
} encoder_axis_word_t;

static ap_uint<16> encoder_phase_acc[MAX_INPUT_CHANNELS];
static input_data_t encoder_frame;
static bool encoder_frame_loaded = false;

static void encoder_write_axis_spike(
    int channel,
    weight_t weight,
    ap_uint<32> time,
    hls::stream<encoder_axis_word_t> &fifo,
    ap_uint<32> &counter
) {
    #pragma HLS INLINE
    if (fifo.full()) return;

    encoder_axis_word_t pkt;
    pkt.data = 0;
    pkt.data(SPIKE_PKT_ID_HI, SPIKE_PKT_ID_LO) = channel;
    pkt.data(SPIKE_PKT_WGT_HI, SPIKE_PKT_WGT_LO) = (ap_uint<8>)weight;
    pkt.data(SPIKE_PKT_TS_HI, SPIKE_PKT_TS_LO) = time(SPIKE_PKT_TS_HI - SPIKE_PKT_TS_LO, 0);
    pkt.keep = 0xF;
    pkt.strb = 0xF;
    pkt.last = 1;
    fifo.write(pkt);
    counter++;
}

static void encoder_delta_sigma(
    int channel,
    pixel_t value,
    ap_uint<32> time,
    const encoder_config_t &config,
    hls::stream<encoder_axis_word_t> &fifo,
    ap_uint<32> &counter
) {
    #pragma HLS INLINE
    // Delta-sigma modulation: integrate input and spike when threshold exceeded
    ap_uint<16> increment = value;  // Input contribution
    encoder_phase_acc[channel] += increment;
    
    // Apply decay
    if (encoder_phase_acc[channel] > config.delta_decay) {
        encoder_phase_acc[channel] -= config.delta_decay;
    }
    
    // Fire spike if threshold exceeded
    if (encoder_phase_acc[channel] >= config.delta_threshold) {
        encoder_write_axis_spike(channel, config.default_weight, time, fifo, counter);
        encoder_phase_acc[channel] -= config.delta_threshold;  // Reset by threshold amount
    }
}

static void run_encoder_once(
    bool enable,
    const encoder_config_t &config,
    ap_uint<32> time,
    hls::stream<encoder_axis_word_t> &fifo,
    ap_uint<32> &counter
) {
    #pragma HLS INLINE
    if (!enable || !encoder_frame_loaded) return;

    ENCODER_LOOP: for (int ch = 0; ch < MAX_INPUT_CHANNELS; ch++) {
        #pragma HLS PIPELINE II=1
        if (ch >= config.num_channels) continue;

        pixel_t pixel_value = encoder_frame.pixels[ch];

        if (config.encoding_type == ENC_DELTA_SIGMA) {
            encoder_delta_sigma(ch, pixel_value, time, config, fifo, counter);
        }
        // ENC_NONE: spikes come from s_axis_spikes, nothing to do here
    }
}

//=============================================================================
// Weight Memory (On-Chip BRAM) — population-aware flat buffer
// Loihi/TrueNorth-inspired: ALL weights on-chip, no DDR in datapath.
// Configurable precision via SNN_WEIGHT_BITS (2/4/8 bit per synapse).
//   8-bit: [-128, 127],  ~794 BRAM18K for 1.6M synapses
//   4-bit: [-8,    7],   ~353 BRAM18K  (Loihi default precision)
//   2-bit: [-2,    1],   ~177 BRAM18K  (TrueNorth ternary-like)
//=============================================================================
static packed_weight_t weight_memory[MAX_WEIGHT_BUFFER_SIZE];

//=============================================================================
// Per-Neuron Trace Storage — KIST Time-Embedding
// Instead of storing (trace + 16-bit timestamp) per neuron and computing
// lazy decay on access, we store only the 8-bit trace value and apply
// a global shift-based decay every timestep.  This saves 16 bits × N × 2
// = ~19 KB of BRAM for N=4890 (K=1024).
//=============================================================================
static ap_uint<8> pre_traces[TOTAL_LOGICAL_NEURONS];   // Pre-synaptic traces
static ap_uint<8> post_traces[TOTAL_LOGICAL_NEURONS];  // Post-synaptic traces

//=============================================================================
// Weight Clipping — adapted for configurable packed_weight_t
//=============================================================================
static packed_weight_t clip_weight(ap_int<16> w) {
    #pragma HLS INLINE
    if (w > MAX_WEIGHT) return MAX_WEIGHT;
    if (w < MIN_WEIGHT) return MIN_WEIGHT;
    return (packed_weight_t)w;
}

//-----------------------------------------------------------------------------
// Learned-Weight Bridge State (HLS -> Event Router)
// Single-entry pending register with ready/valid handshake.
// If multiple updates occur while pending is occupied, additional updates are
// dropped in this revision (bounded-latency bridge without deep FIFO).
//-----------------------------------------------------------------------------
struct learn_weight_bridge_t {
    ap_uint<1> valid;
    group_id_t group;
    local_id_t src;
    local_id_t dst;
    ap_uint<8> data;
    ap_uint<1> exc;
    ap_uint<1> is_inter;
    group_id_t dst_group;
    fanout_idx_t fanout_idx;
};

static inline void enqueue_learn_weight_update(
    neuron_id_t pre_id,
    neuron_id_t post_id,
    packed_weight_t updated_weight,
    learn_weight_bridge_t &bridge,
    ap_uint<1> learn_weight_ready
) {
    #pragma HLS INLINE

    if (bridge.valid && !learn_weight_ready) {
        return;
    }

    // Bridge only the subset representable by RTL core-group global IDs.
    if ((ap_uint<16>)pre_id >= (ap_uint<16>)SNN_TOTAL_NEURONS ||
        (ap_uint<16>)post_id >= (ap_uint<16>)SNN_TOTAL_NEURONS) {
        return;
    }

    ap_uint<RTL_NEURON_ID_WIDTH> pre_rtl = (ap_uint<RTL_NEURON_ID_WIDTH>)pre_id;
    ap_uint<RTL_NEURON_ID_WIDTH> post_rtl = (ap_uint<RTL_NEURON_ID_WIDTH>)post_id;

    group_id_t src_group = (group_id_t)(pre_rtl >> SNN_LOCAL_ID_WIDTH);
    group_id_t dst_group = (group_id_t)(post_rtl >> SNN_LOCAL_ID_WIDTH);
    local_id_t src_local = (local_id_t)pre_rtl(SNN_LOCAL_ID_WIDTH - 1, 0);
    local_id_t dst_local = (local_id_t)post_rtl(SNN_LOCAL_ID_WIDTH - 1, 0);

    ap_int<16> w16 = (ap_int<16>)updated_weight;
    ap_uint<1> exc = (w16 >= 0) ? (ap_uint<1>)1 : (ap_uint<1>)0;
    ap_uint<8> mag = (w16 >= 0) ? (ap_uint<8>)w16 : (ap_uint<8>)(-w16);

    bridge.valid = 1;
    bridge.group = src_group;
    bridge.src = src_local;
    bridge.dst = dst_local;
    bridge.data = mag;
    bridge.exc = exc;
    bridge.is_inter = (src_group != dst_group) ? (ap_uint<1>)1 : (ap_uint<1>)0;
    bridge.dst_group = dst_group;
    bridge.fanout_idx = 0;  // Not tracked in HLS flat-buffer update path
}

//=============================================================================
// Global Trace Decay (KIST Time-Embedding)
// Applied once per timestep in the main TIME_LOOP.
// Uses trace_decay parameter (ap_fixed<16,8>): fraction of trace removed per step.
//   trace_decay = 0.125 → 12.5% removed → 87.5% retention (≈ τ=8)
//   trace_decay = 0.0625 → 6.25% removed → 93.75% retention (≈ τ=16)
//=============================================================================
static void decay_all_traces(const learning_params_t &params) {
    #pragma HLS INLINE off

    // Extract fractional decay (lower 8 bits of ap_fixed<16,8>)
    ap_uint<8> decay_frac = params.trace_decay.range(7, 0);

    DECAY_PRE_TRACE: for (int i = 0; i < TOTAL_LOGICAL_NEURONS; i++) {
        #pragma HLS PIPELINE II=1
        #pragma HLS LOOP_TRIPCOUNT min=4890 max=4890
        ap_uint<8> t = pre_traces[i];
        ap_uint<16> mul_decay_pre = (ap_uint<16>)t * decay_frac;
        #pragma HLS BIND_OP variable=mul_decay_pre op=mul impl=dsp latency=2
        pre_traces[i] = (ap_uint<8>)((ap_uint<16>)t - (mul_decay_pre >> 8));
    }
    DECAY_POST_TRACE: for (int i = 0; i < TOTAL_LOGICAL_NEURONS; i++) {
        #pragma HLS PIPELINE II=1
        #pragma HLS LOOP_TRIPCOUNT min=4890 max=4890
        ap_uint<8> t = post_traces[i];
        ap_uint<16> mul_decay_post = (ap_uint<16>)t * decay_frac;
        #pragma HLS BIND_OP variable=mul_decay_post op=mul impl=dsp latency=2
        post_traces[i] = (ap_uint<8>)((ap_uint<16>)t - (mul_decay_post >> 8));
    }
}

//=============================================================================
// Process Pre-Synaptic Spike (Input Spike) - Mozafari Weight-Dependent STDP
// When pre-neuron i fires:
//   1. Add spike to pre_trace[i] (global decay already applied per-timestep)
//   2. For all post-neurons j with existing post_trace[j]:
//      Apply LTD: Δw = -a_minus * (w - w_min)^μ
//      (Mozafari multiplicative rule, matching stdp_engine.v)
//=============================================================================
static void process_pre_spike_aer(
    neuron_id_t pre_id,
    ap_uint<16> current_time,
    const learning_params_t &params,
    learn_weight_bridge_t &learn_bridge,
    ap_uint<1> learn_weight_ready
) {
    #pragma HLS INLINE off
    
    // Step 1: Add new spike to pre-trace (KIST: no lazy decay, already done globally)
    ap_uint<9> new_trace = (ap_uint<9>)pre_traces[pre_id] + 128;
    pre_traces[pre_id] = (new_trace > 255) ? (ap_uint<8>)255 : (ap_uint<8>)new_trace;
    
    // Step 2: Apply LTD to all synapses from this pre-neuron.
    // Use explicit source ID ranges per connection so HLS cannot over-prune
    // group-matching loops during static analysis.
    const ap_int<16> a_raw = params.a_minus.range(15, 0);
    const ap_int<16> lr_raw = params.learning_rate.range(15, 0);

    LTD_CONN_LOOP: for (int c = 0; c < NUM_CONNECTIONS; c++) {
        #pragma HLS LOOP_FLATTEN off
        const SynapticConnection &conn = CONNECTION_TABLE[c];
        int src_start = conn.src_id_start;
        int src_end = conn.src_id_start + conn.src_size;
        if ((int)pre_id < src_start || (int)pre_id >= src_end) continue;

        int local_src = (int)pre_id - conn.src_id_start;
        int base_offset = conn.weight_offset + local_src * conn.dst_size;
        int widx = base_offset;
        
        LTD_LOOP: for (int jj = 0; jj < conn.dst_size; jj++) {
            #pragma HLS PIPELINE II=1
            #pragma HLS LOOP_TRIPCOUNT min=10 max=4096
            
            int global_post = conn.dst_id_start + jj;
            
            // KIST: trace already decayed globally, just read current value
            ap_uint<8> post_trace_val = post_traces[global_post];
            
            // Skip compute/update when there is no post activity, but keep
            // sequential address progression to simplify address generation.
            if (post_trace_val != 0) {
                // Read current weight from flat buffer (packed_weight_t)
                packed_weight_t current_w = weight_memory[widx];
                
                // Mozafari weight-dependent LTD: Δw = -a_minus * (w - w_min) * trace / 256
                // DSP48E1-mapped multiplications (operands narrowed to ≤25×18)
                ap_int<16> distance = (ap_int<16>)current_w - (ap_int<16>)MIN_WEIGHT;

                // Mul1: distance × trace (16b × 8b → 24b, fits 25×18 DSP)
                ap_int<24> mul_dt = (ap_int<24>)distance * (ap_int<24>)post_trace_val;
                #pragma HLS BIND_OP variable=mul_dt op=mul impl=dsp latency=2

                // Mul2: (distance*trace) × a_minus (24b × 16b → fits 25×18 DSP)
                ap_int<40> mul_a = (ap_int<40>)mul_dt * (ap_int<40>)a_raw;
                #pragma HLS BIND_OP variable=mul_a op=mul impl=dsp latency=3
                ap_int<24> scaled = (ap_int<24>)(mul_a >> 16);

                // Mul3: scaled × learning_rate (24b × 16b → fits 25×18 DSP)
                ap_int<40> mul_lr = (ap_int<40>)scaled * (ap_int<40>)lr_raw;
                #pragma HLS BIND_OP variable=mul_lr op=mul impl=dsp latency=3
                ap_int<16> delta = -(ap_int<16>)(mul_lr >> 8);
                
                // Apply update
                packed_weight_t updated = clip_weight((ap_int<16>)current_w + delta);
                weight_memory[widx] = updated;
                enqueue_learn_weight_update(
                    pre_id,
                    (neuron_id_t)global_post,
                    updated,
                    learn_bridge,
                    learn_weight_ready
                );
            }
            widx++;
        }
    }
}

//=============================================================================
// Process Post-Synaptic Spike (Output Spike) - Mozafari Weight-Dependent STDP
// When post-neuron j fires:
//   1. Add spike to post_trace[j] (global decay already applied per-timestep)
//   2. For all pre-neurons i with existing pre_trace[i]:
//      Apply LTP: Δw = +a_plus * (w_max - w)^μ
//      (Mozafari multiplicative rule, matching stdp_engine.v)
//=============================================================================
static void process_post_spike_aer(
    neuron_id_t post_id,
    ap_uint<16> current_time,
    const learning_params_t &params,
    learn_weight_bridge_t &learn_bridge,
    ap_uint<1> learn_weight_ready
) {
    #pragma HLS INLINE off
    
    // Step 1: Add new spike to post-trace (KIST: no lazy decay, already done globally)
    ap_uint<9> new_trace = (ap_uint<9>)post_traces[post_id] + 128;
    post_traces[post_id] = (new_trace > 255) ? (ap_uint<8>)255 : (ap_uint<8>)new_trace;
    
    // Step 2: Apply LTP to all synapses to this post-neuron.
    // Range check on destination ID per connection avoids HLS pruning the
    // connection loop into a no-op.
    const ap_int<16> a_raw = params.a_plus.range(15, 0);
    const ap_int<16> lr_raw = params.learning_rate.range(15, 0);

    LTP_CONN_LOOP: for (int c = 0; c < NUM_CONNECTIONS; c++) {
        #pragma HLS LOOP_FLATTEN off
        const SynapticConnection &conn = CONNECTION_TABLE[c];
        int dst_start = conn.dst_id_start;
        int dst_end = conn.dst_id_start + conn.dst_size;
        if ((int)post_id < dst_start || (int)post_id >= dst_end) continue;
        if (conn.src_size <= 0 || conn.dst_size <= 0) continue;

        int local_dst = (int)post_id - conn.dst_id_start;
        int widx = conn.weight_offset + local_dst;
        
        LTP_LOOP: for (int ii = 0; ii < conn.src_size; ii++) {
            #pragma HLS PIPELINE II=1
            #pragma HLS LOOP_TRIPCOUNT min=10 max=4096
            
            int global_pre = conn.src_id_start + ii;
            
            // KIST: trace already decayed globally, just read current value
            ap_uint<8> pre_trace_val = pre_traces[global_pre];
            
            // Skip compute/update when there is no pre activity, but keep
            // fixed-stride address progression to avoid inner-loop multiply.
            if (pre_trace_val != 0) {
                // Read current weight from flat buffer (packed_weight_t)
                packed_weight_t current_w = weight_memory[widx];
                
                // Mozafari weight-dependent LTP: Δw = +a_plus * (w_max - w) * trace / 256
                // DSP48E1-mapped multiplications (operands narrowed to ≤25×18)
                ap_int<16> distance = (ap_int<16>)MAX_WEIGHT - (ap_int<16>)current_w;

                // Mul1: distance × trace (16b × 8b → 24b, fits 25×18 DSP)
                ap_int<24> mul_dt = (ap_int<24>)distance * (ap_int<24>)pre_trace_val;
                #pragma HLS BIND_OP variable=mul_dt op=mul impl=dsp latency=2

                // Mul2: (distance*trace) × a_plus (24b × 16b → fits 25×18 DSP)
                ap_int<40> mul_a = (ap_int<40>)mul_dt * (ap_int<40>)a_raw;
                #pragma HLS BIND_OP variable=mul_a op=mul impl=dsp latency=3
                ap_int<24> scaled = (ap_int<24>)(mul_a >> 16);

                // Mul3: scaled × learning_rate (24b × 16b → fits 25×18 DSP)
                ap_int<40> mul_lr = (ap_int<40>)scaled * (ap_int<40>)lr_raw;
                #pragma HLS BIND_OP variable=mul_lr op=mul impl=dsp latency=3
                ap_int<16> delta = (ap_int<16>)(mul_lr >> 8);
                
                // Apply update
                packed_weight_t updated = clip_weight((ap_int<16>)current_w + delta);
                weight_memory[widx] = updated;
                enqueue_learn_weight_update(
                    (neuron_id_t)global_pre,
                    post_id,
                    updated,
                    learn_bridge,
                    learn_weight_ready
                );
            }
            widx += conn.dst_size;
        }
    }
}

//=============================================================================
// Apply Weight Updates with R-STDP Modulation
// Per-Neuron Eligibility Traces: O(N+M) storage only
//=============================================================================

// Per-Neuron Eligibility traces for R-STDP (NOT per-synapse!)
static ap_int<8> pre_eligibility[TOTAL_LOGICAL_NEURONS];   // Pre-neuron eligibility
static ap_int<8> post_eligibility[TOTAL_LOGICAL_NEURONS];  // Post-neuron eligibility

static void apply_rstdp_reward(
    ap_int<8> reward_signal,
    const learning_params_t &params,
    ap_uint<16> current_time,
    learn_weight_bridge_t &learn_bridge,
    ap_uint<1> learn_weight_ready
) {
    #pragma HLS INLINE off
    
    if (reward_signal == 0 || !params.rstdp_enable) return;
    
    bool reward_positive = (reward_signal >= 0);
    ap_uint<8> reward_mag = reward_positive ? (ap_uint<8>)reward_signal : (ap_uint<8>)(-reward_signal);
    
    // Determine base shift from reward magnitude
    ap_uint<2> shift_sel;
    if (reward_mag >= 64) shift_sel = 0;
    else if (reward_mag >= 32) shift_sel = 1;
    else if (reward_mag >= 16) shift_sel = 2;
    else shift_sel = 3;
    
    // reward_scale (ap_fixed<16,8>): scales the final delta
    ap_int<16> rs_raw = params.reward_scale.range(15, 0);
    
    // Apply reward modulated by eligibility traces
    // population-aware: only iterate over defined connections
    RSTDP_CONN_LOOP: for (int c = 0; c < NUM_CONNECTIONS; c++) {
        #pragma HLS LOOP_FLATTEN off
        const SynapticConnection &conn = CONNECTION_TABLE[c];
        
        RSTDP_OUTER: for (int ii = 0; ii < conn.src_size; ii++) {
            #pragma HLS LOOP_FLATTEN off
            #pragma HLS LOOP_TRIPCOUNT min=10 max=4096
            
            int global_pre = conn.src_id_start + ii;
            ap_int<8> pre_elig = pre_eligibility[global_pre];
            if (pre_elig == 0) continue;  // Skip inactive pre-neurons
            
            int base_offset = conn.weight_offset + ii * conn.dst_size;
            int widx = base_offset;
            
            RSTDP_INNER: for (int jj = 0; jj < conn.dst_size; jj++) {
                #pragma HLS PIPELINE II=1
                #pragma HLS LOOP_TRIPCOUNT min=10 max=4096
                
                int global_post = conn.dst_id_start + jj;
                ap_int<8> post_elig = post_eligibility[global_post];
                if (post_elig != 0) {
                    // Combine eligibilities via DSP: (pre_elig * post_elig) >> 8
                    ap_int<16> mul_elig = (ap_int<16>)pre_elig * (ap_int<16>)post_elig;
                    #pragma HLS BIND_OP variable=mul_elig op=mul impl=dsp latency=2
                    ap_int<16> combined_elig = mul_elig >> 8;
                    
                    // Apply reward magnitude scaling (shift-based)
                    ap_int<16> base_scaled;
                    switch (shift_sel) {
                        case 0: base_scaled = combined_elig >> 1; break;
                        case 1: base_scaled = combined_elig >> 2; break;
                        case 2: base_scaled = combined_elig >> 3; break;
                        default: base_scaled = combined_elig >> 4; break;
                    }
                    
                    // Apply reward_scale parameter via DSP (16b × 16b → fits 25×18)
                    ap_int<24> mul_rs = (ap_int<24>)base_scaled * (ap_int<24>)rs_raw;
                    #pragma HLS BIND_OP variable=mul_rs op=mul impl=dsp latency=2
                    ap_int<16> scaled = (ap_int<16>)(mul_rs >> 8);
                    
                    // Apply sign
                    ap_int<16> delta = reward_positive ? scaled : (ap_int<16>)(-scaled);
                    
                    // Update weight in flat buffer (packed_weight_t)
                    packed_weight_t current_w = weight_memory[widx];
                    packed_weight_t updated = clip_weight((ap_int<16>)current_w + delta);
                    weight_memory[widx] = updated;
                    enqueue_learn_weight_update(
                        (neuron_id_t)global_pre,
                        (neuron_id_t)global_post,
                        updated,
                        learn_bridge,
                        learn_weight_ready
                    );
                }
                widx++;
            }
        }
    }
}

//=============================================================================
// Decay Per-Neuron Eligibility Traces - O(N+M) operations only!
// Much faster than O(N*M) per-synapse decay
//=============================================================================
static void decay_eligibility_traces(const learning_params_t &params) {
    #pragma HLS INLINE off
    
    // Decay pre-neuron eligibility traces
    DECAY_PRE: for (int i = 0; i < TOTAL_LOGICAL_NEURONS; i++) {
        #pragma HLS PIPELINE II=1
        #pragma HLS LOOP_TRIPCOUNT min=4890 max=4890
        
        // Simple shift-based decay: trace = trace - (trace >> 3) ≈ 0.875
        ap_int<8> trace = pre_eligibility[i];
        pre_eligibility[i] = trace - (trace >> 3);
    }
    
    // Decay post-neuron eligibility traces
    DECAY_POST: for (int j = 0; j < TOTAL_LOGICAL_NEURONS; j++) {
        #pragma HLS PIPELINE II=1
        #pragma HLS LOOP_TRIPCOUNT min=4890 max=4890
        
        ap_int<8> trace = post_eligibility[j];
        post_eligibility[j] = trace - (trace >> 3);
    }
}

//=============================================================================
// Update Eligibility on Spike Events
// Called when pre/post spikes occur to mark "credit assignment"
//=============================================================================
static void update_eligibility_on_pre_spike(neuron_id_t pre_id) {
    #pragma HLS INLINE
    // Increase pre-neuron eligibility (saturating)
    ap_int<9> new_elig = (ap_int<9>)pre_eligibility[pre_id] + 32;
    pre_eligibility[pre_id] = (new_elig > 127) ? (ap_int<8>)127 : (ap_int<8>)new_elig;
}

static void update_eligibility_on_post_spike(neuron_id_t post_id) {
    #pragma HLS INLINE
    // Increase post-neuron eligibility (saturating)
    ap_int<9> new_elig = (ap_int<9>)post_eligibility[post_id] + 32;
    post_eligibility[post_id] = (new_elig > 127) ? (ap_int<8>)127 : (ap_int<8>)new_elig;
}

//=============================================================================
// Main Top-Level Function
//=============================================================================
void snn_top_hls(
    // AXI4-Lite Control Interface
    ap_uint<32> ctrl_reg,
    ap_uint<32> config_reg,
    ap_uint<32> mode_reg,
    ap_uint<32> time_steps_reg,
    learning_params_t learning_params,
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
    
    // Reward signal input (for R-STDP)
    ap_int<8> reward_signal,
    
    // Verilog Interface - Spike Input (to SNN core) — RTL-width IDs
    ap_uint<1> &spike_in_valid,
    rtl_nid_t &spike_in_neuron_id,
    ap_int<8> &spike_in_weight,
    ap_uint<1> spike_in_ready,
    
    // Verilog Interface - Spike Output (from SNN core) — RTL-width IDs
    ap_uint<1> spike_out_valid,
    rtl_nid_t spike_out_neuron_id,
    ap_int<8> spike_out_weight,
    ap_uint<1> &spike_out_ready,

    // Verilog Interface - Learned weight update (HLS -> Event Router)
    ap_uint<1> &learn_weight_valid,
    group_id_t &learn_weight_group,
    local_id_t &learn_weight_src,
    local_id_t &learn_weight_dst,
    ap_uint<8> &learn_weight_data,
    ap_uint<1> &learn_weight_exc,
    ap_uint<1> &learn_weight_is_inter,
    group_id_t &learn_weight_dst_group,
    fanout_idx_t &learn_weight_fanout_idx,
    ap_uint<1> learn_weight_ready,
    
    // Verilog Interface - Control signals
    ap_uint<1> &snn_enable,
    ap_uint<1> &snn_reset,
    ap_uint<16> &threshold_out,
    ap_uint<16> &leak_rate_out,
    
    // Verilog Interface - Status signals
    ap_uint<1> snn_ready,
    ap_uint<1> snn_busy
) {
    //=========================================================================
    // HLS Interface Pragmas
    //=========================================================================
    // AXI4-Lite slave interface
    #pragma HLS INTERFACE s_axilite port=ctrl_reg bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=config_reg bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=mode_reg bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=time_steps_reg bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=learning_params bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=encoder_config bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=status_reg bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=spike_count_reg bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=weight_sum_reg bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=version_reg bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=reward_signal bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=return bundle=ctrl
    
    // AXI4-Stream interfaces
    #pragma HLS INTERFACE axis port=s_axis_spikes
    #pragma HLS INTERFACE axis port=s_axis_data
    #pragma HLS INTERFACE axis port=s_axis_weights
    #pragma HLS INTERFACE axis port=m_axis_spikes
    #pragma HLS INTERFACE axis port=m_axis_weights
    
    // Direct wire interfaces to Verilog
    #pragma HLS INTERFACE ap_none port=spike_in_valid
    #pragma HLS INTERFACE ap_none port=spike_in_neuron_id
    #pragma HLS INTERFACE ap_none port=spike_in_weight
    #pragma HLS INTERFACE ap_none port=spike_in_ready
    #pragma HLS INTERFACE ap_none port=spike_out_valid
    #pragma HLS INTERFACE ap_none port=spike_out_neuron_id
    #pragma HLS INTERFACE ap_none port=spike_out_weight
    #pragma HLS INTERFACE ap_none port=spike_out_ready
    #pragma HLS INTERFACE ap_none port=learn_weight_valid
    #pragma HLS INTERFACE ap_none port=learn_weight_group
    #pragma HLS INTERFACE ap_none port=learn_weight_src
    #pragma HLS INTERFACE ap_none port=learn_weight_dst
    #pragma HLS INTERFACE ap_none port=learn_weight_data
    #pragma HLS INTERFACE ap_none port=learn_weight_exc
    #pragma HLS INTERFACE ap_none port=learn_weight_is_inter
    #pragma HLS INTERFACE ap_none port=learn_weight_dst_group
    #pragma HLS INTERFACE ap_none port=learn_weight_fanout_idx
    #pragma HLS INTERFACE ap_none port=learn_weight_ready
    #pragma HLS INTERFACE ap_none port=snn_enable
    #pragma HLS INTERFACE ap_none port=snn_reset
    #pragma HLS INTERFACE ap_none port=threshold_out
    #pragma HLS INTERFACE ap_none port=leak_rate_out
    #pragma HLS INTERFACE ap_none port=snn_ready
    #pragma HLS INTERFACE ap_none port=snn_busy
    
    //=========================================================================
    // Static Array Storage Bindings — Neuromorphic On-Chip Architecture
    // Loihi/TrueNorth-inspired: ALL data on-chip SRAM, no DDR in datapath.
    //=========================================================================
    // Weight Memory — BRAM, packed at SNN_WEIGHT_BITS precision
    // No ARRAY_PARTITION: reduces BRAM addressing overhead and allows
    // HLS to optimally map the narrow-word array to BRAM18K blocks.
    // Prefer true dual-port BRAM here. In integrated builds, checkpoint readback
    // and STDP update/read monitors can otherwise trigger aggressive memory
    // replication/port-muxing that makes debug visibility brittle.
    #pragma HLS BIND_STORAGE variable=weight_memory type=RAM_T2P impl=BRAM latency=3
    
    // Per-Neuron Eligibility — LUTRAM (distributed RAM)
    // ~2,842 × 8 bits each = ~355 LUTs (0.7% of xc7z020), freeing BRAM.
#if SNN_AUXILIARY_LUTRAM
    #pragma HLS BIND_STORAGE variable=pre_eligibility type=RAM_2P impl=LUTRAM
    #pragma HLS BIND_STORAGE variable=post_eligibility type=RAM_2P impl=LUTRAM
#else
    #pragma HLS BIND_STORAGE variable=pre_eligibility type=RAM_2P impl=BRAM
    #pragma HLS BIND_STORAGE variable=post_eligibility type=RAM_2P impl=BRAM
#endif
    
    // Per-Neuron Traces — LUTRAM (KIST time-embedding: only 8-bit, no timestamp)
    // After time-embedding: 2,842 × 8 bits each = ~355 LUTs per array.
#if SNN_AUXILIARY_LUTRAM
    #pragma HLS BIND_STORAGE variable=pre_traces type=RAM_2P impl=LUTRAM
    #pragma HLS BIND_STORAGE variable=post_traces type=RAM_2P impl=LUTRAM
#else
    #pragma HLS BIND_STORAGE variable=pre_traces type=RAM_2P impl=BRAM
    #pragma HLS BIND_STORAGE variable=post_traces type=RAM_2P impl=BRAM
#endif

    // Encoder state (delta-sigma only): keep in LUTRAM to reduce BRAM pressure
    // on integrated builds (Z-7020 is BRAM-constrained at 50 MHz+).
    #pragma HLS BIND_STORAGE variable=encoder_phase_acc type=RAM_2P impl=LUTRAM
    #pragma HLS ARRAY_PARTITION variable=encoder_phase_acc cyclic factor=2
    
    //=========================================================================
    // Internal State
    //=========================================================================
    static ap_uint<32> timestamp = 0;
    static ap_uint<32> spike_counter = 0;
    static ap_uint<32> update_counter = 0;
    static bool initialized = false;
    static ap_uint<2> last_mode = MODE_INFERENCE;
    static ap_uint<32> checkpoint_idx = 0;  // flat buffer index for weight checkpoint
    static ap_uint<16> checkpoint_chunk_pos = 0;  // position within checkpoint chunk frame
    static ap_uint<32> encoder_spike_counter = 0;
    static learn_weight_bridge_t learn_bridge = {0, 0, 0, 0, 0, 0, 0, 0, 0};
    static bool first_spike_sent = false;
    static bool first_spike_pending = false;
    static neuron_id_t first_spike_pending_id = 0;
    static weight_t first_spike_pending_weight = 0;
    // Post-spike consume acknowledge token (toggles once per consumed spike).
    // ap_none outputs are level signals across invocations, so using a toggle
    // avoids "stuck-high" ready that can break one-spike-per-ack semantics.
    static ap_uint<1> spike_out_ack_toggle = 0;
    
    //=========================================================================
    // Control Signal Extraction
    //=========================================================================
    bool enable = ctrl_reg[0];
    bool reset = ctrl_reg[1];
    bool clear_counters = ctrl_reg[2];
    bool learning_enable = ctrl_reg[3];
    bool weight_read_mode = ctrl_reg[4];
    bool apply_reward = ctrl_reg[5];
    bool weight_load_mode = ctrl_reg[6];  // New: enable weight loading from s_axis_weights
    bool first_spike_only = ctrl_reg[7];
    ap_uint<2> op_mode = mode_reg(1, 0);
    // mode_reg[31:16]: optional checkpoint chunk size in words.
    // 0 => legacy behavior (single frame, TLAST only at MAX_WEIGHT_BUFFER_SIZE-1).
    ap_uint<16> checkpoint_chunk_words = mode_reg(31, 16);
    bool encoder_enable = mode_reg[8];
    bool checkpoint_mode = (op_mode == MODE_CHECKPOINT);
    bool stdp_mode = (op_mode == MODE_TRAIN_STDP);
    bool stdp_active = learning_enable && stdp_mode;
    ap_uint<16> time_steps = (time_steps_reg == 0) ? (ap_uint<16>)1 : (ap_uint<16>)time_steps_reg;
    
    ap_uint<16> threshold = config_reg(15, 0);
    ap_uint<16> leak_rate = config_reg(31, 16);

    // Default bridge outputs; valid payload is driven during TIME_LOOP.
    learn_weight_valid = 0;
    learn_weight_group = 0;
    learn_weight_src = 0;
    learn_weight_dst = 0;
    learn_weight_data = 0;
    learn_weight_exc = 0;
    learn_weight_is_inter = 0;
    learn_weight_dst_group = 0;
    learn_weight_fanout_idx = 0;
    
    //=========================================================================
    // Reset Logic
    //=========================================================================
    if (reset || !initialized) {
        timestamp = 0;
        spike_counter = 0;
        update_counter = 0;
        encoder_spike_counter = 0;
        last_mode = MODE_INFERENCE;
        checkpoint_idx = 0;
        checkpoint_chunk_pos = 0;
        encoder_frame_loaded = false;
        learn_bridge.valid = 0;
        learn_bridge.group = 0;
        learn_bridge.src = 0;
        learn_bridge.dst = 0;
        learn_bridge.data = 0;
        learn_bridge.exc = 0;
        learn_bridge.is_inter = 0;
        learn_bridge.dst_group = 0;
        learn_bridge.fanout_idx = 0;
        first_spike_sent = false;
        first_spike_pending = false;
        first_spike_pending_id = 0;
        first_spike_pending_weight = 0;
        spike_out_ack_toggle = 0;
        
        // Clear Per-Neuron eligibility traces (O(N) - much faster than O(N²)!)
        RESET_ELIG: for (int i = 0; i < TOTAL_LOGICAL_NEURONS; i++) {
            #pragma HLS PIPELINE II=1
            #pragma HLS LOOP_TRIPCOUNT min=4890 max=4890
            pre_eligibility[i] = 0;
            post_eligibility[i] = 0;
        }
        
        // Clear Per-Neuron STDP traces
        RESET_TRACES: for (int i = 0; i < TOTAL_LOGICAL_NEURONS; i++) {
            #pragma HLS PIPELINE II=1
            #pragma HLS LOOP_TRIPCOUNT min=4890 max=4890
            pre_traces[i] = 0;
            post_traces[i] = 0;
        }

        RESET_ENCODER: for (int i = 0; i < MAX_INPUT_CHANNELS; i++) {
            #pragma HLS PIPELINE II=1
            encoder_phase_acc[i] = 0;
        }
        
        // Initialize weights (flat buffer)
        if (!initialized) {
            INIT_WEIGHT: for (int k = 0; k < MAX_WEIGHT_BUFFER_SIZE; k++) {
                #pragma HLS PIPELINE II=1
                #pragma HLS LOOP_TRIPCOUNT min=843776 max=843776
                // Default to zero; will be overwritten if weight_load_mode is set
                weight_memory[k] = 0;
            }
            initialized = true;
        }
    }
    
    // Weight Loading Mode: Stream weights from s_axis_weights to weight_memory
    // population-aware: uses connection table to compute flat buffer index
    // Host should set ctrl_reg[6] = 1, then stream weights
    // Format: axis_weight_t.data[NEURON_ID_WIDTH-1:0] = pre_id,
    //         [2*NEURON_ID_WIDTH-1:NEURON_ID_WIDTH] = post_id,
    //         [2*NEURON_ID_WIDTH+7:2*NEURON_ID_WIDTH] = weight
    // AXI weight is 8-bit; clip to packed_weight_t range on store.
    if (weight_load_mode && !s_axis_weights.empty()) {
        axis_weight_t w_pkt = s_axis_weights.read();
        neuron_id_t row = w_pkt.data(NEURON_ID_WIDTH - 1, 0);
        neuron_id_t col = w_pkt.data(2 * NEURON_ID_WIDTH - 1, NEURON_ID_WIDTH);
        weight_t weight_val = w_pkt.data(2 * NEURON_ID_WIDTH + 7, 2 * NEURON_ID_WIDTH);
        
        int widx = weight_index(row, col);
        if (widx >= 0) {
            // Clip 8-bit AXI weight to SNN_WEIGHT_BITS range
            weight_memory[widx] = clip_weight((ap_int<16>)weight_val);
        }
    }
    
    if (clear_counters) {
        spike_counter = 0;
        update_counter = 0;
        encoder_spike_counter = 0;
    }

    if (!enable) {
        // Re-arm first-spike capture on each host-launched inference run.
        first_spike_sent = false;
        first_spike_pending = false;
        first_spike_pending_id = 0;
        first_spike_pending_weight = 0;
    }
    
    //=========================================================================
    // Route Control to Verilog Core
    //=========================================================================
    snn_enable = enable;
    snn_reset = reset;
    threshold_out = threshold;
    leak_rate_out = leak_rate;
    
    // Preload encoder frame via 32-bit AXI-Stream (4 pixels per beat, 196 beats)
    if (encoder_enable && !encoder_frame_loaded && !s_axis_data.empty()) {
        LOAD_FRAME: for (int i = 0; i < FRAME_LOAD_BEATS; i++) {
            #pragma HLS PIPELINE II=1
            if (s_axis_data.empty()) break;
            axis_data_t beat = s_axis_data.read();
            int base = i * 4;
            if (base < MAX_INPUT_CHANNELS) encoder_frame.pixels[base] = beat.data(7, 0);
            if (base+1 < MAX_INPUT_CHANNELS) encoder_frame.pixels[base+1] = beat.data(15, 8);
            if (base+2 < MAX_INPUT_CHANNELS) encoder_frame.pixels[base+2] = beat.data(23, 16);
            if (base+3 < MAX_INPUT_CHANNELS) encoder_frame.pixels[base+3] = beat.data(31, 24);
            if (beat.last) break;
        }
        encoder_frame_loaded = true;
    }

    // Reset checkpoint iterator on mode transition into checkpoint
    if (op_mode != last_mode && checkpoint_mode) {
        checkpoint_idx = 0;
        checkpoint_chunk_pos = 0;
    }

    hls::stream<encoder_axis_word_t> encoder_spikes("encoder_spikes");
    #pragma HLS STREAM variable=encoder_spikes depth=32

    //=========================================================================
    // Time-Stepped Processing Loop
    //=========================================================================
    TIME_LOOP: for (ap_uint<16> t = 0; t < time_steps; t++) {
        #pragma HLS LOOP_FLATTEN off

        // Consume pending learned-weight event when router acknowledges ready.
        if (learn_bridge.valid && learn_weight_ready) {
            learn_bridge.valid = 0;
        }

        // KIST Time-Embedding: apply global trace decay every timestep
        // Replaces lazy per-access compute_decayed_trace()
#if SNN_TIME_EMBEDDING
        if (stdp_active) {
            decay_all_traces(learning_params);
        }
#endif

        if (encoder_enable && encoder_frame_loaded) {
            run_encoder_once(true, encoder_config, timestamp, encoder_spikes, encoder_spike_counter);
        }

        // Input Spike Processing (encoder has priority when enabled)
        spike_in_valid = 0;
        spike_in_neuron_id = 0;
        spike_in_weight = 0;

        if (enable && spike_in_ready) {
            axis_spike_t in_pkt;
            bool have_pkt = false;

            if (encoder_enable && !encoder_spikes.empty()) {
                encoder_axis_word_t enc_word = encoder_spikes.read();
                in_pkt.data = enc_word.data;
                in_pkt.keep = enc_word.keep;
                in_pkt.strb = enc_word.strb;
                in_pkt.last = enc_word.last;
                in_pkt.id = 0;
                in_pkt.dest = 0;
                in_pkt.user = 0;
                have_pkt = true;
            } else if (!s_axis_spikes.empty()) {
                in_pkt = s_axis_spikes.read();
                have_pkt = true;
            }

            if (have_pkt) {
                neuron_id_t pre_id = in_pkt.data(SPIKE_PKT_ID_HI, SPIKE_PKT_ID_LO);
                weight_t weight = (weight_t)in_pkt.data(SPIKE_PKT_WGT_HI, SPIKE_PKT_WGT_LO);

                spike_in_valid = 1;
                spike_in_neuron_id = (rtl_nid_t)pre_id;
                spike_in_weight = weight;

                if (stdp_active) {
                    process_pre_spike_aer(
                        pre_id,
                        timestamp,
                        learning_params,
                        learn_bridge,
                        learn_weight_ready
                    );
                    update_eligibility_on_pre_spike(pre_id);
                    update_counter++;
                }

                spike_counter++;
            }
        }

        // Output Spike Processing
        // Treat spike_out_ready as a consume-ack token: toggle once per
        // consumed spike. This is robust for ap_none level semantics.
        // Optional first-spike-only mode (ctrl_reg[7]) guarantees deterministic
        // first-spike capture. The first spike is latched into a pending register
        // and emitted when AXIS output becomes writable, avoiding backpressure
        // deadlocks when S2MM is not ready in the same cycle.
        spike_out_ready = spike_out_ack_toggle;

        if (enable && first_spike_only && first_spike_pending && !m_axis_spikes.full()) {
            axis_spike_t out_pkt;
            out_pkt.data = 0;
            out_pkt.data(SPIKE_PKT_ID_HI, SPIKE_PKT_ID_LO) = first_spike_pending_id;
            out_pkt.data(SPIKE_PKT_WGT_HI, SPIKE_PKT_WGT_LO) = (ap_uint<8>)first_spike_pending_weight;
            out_pkt.data(SPIKE_PKT_TS_HI, SPIKE_PKT_TS_LO) = timestamp(SPIKE_PKT_TS_HI - SPIKE_PKT_TS_LO, 0);
            out_pkt.keep = 0xF;
            out_pkt.strb = 0xF;
            out_pkt.last = 1;
            out_pkt.id = 0;
            out_pkt.dest = 0;
            out_pkt.user = 0;
            m_axis_spikes.write(out_pkt);
            first_spike_pending = false;
        }

        if (enable && spike_out_valid) {
            neuron_id_t post_id = (neuron_id_t)spike_out_neuron_id;
            weight_t weight = spike_out_weight;
            bool consume_post_spike = false;

            if (first_spike_only) {
                if (!first_spike_sent && !first_spike_pending) {
                    // Latch first observed spike immediately, then emit later when
                    // AXIS output is ready. This preserves deterministic "first event"
                    // semantics while preventing RTL hold-register deadlock.
                    first_spike_pending_id = post_id;
                    first_spike_pending_weight = weight;
                    first_spike_pending = true;
                    first_spike_sent = true;
                }
                // Always consume post spikes in first-spike-only mode.
                consume_post_spike = true;
            } else if (!m_axis_spikes.full()) {
                axis_spike_t out_pkt;
                out_pkt.data = 0;
                out_pkt.data(SPIKE_PKT_ID_HI, SPIKE_PKT_ID_LO) = post_id;
                out_pkt.data(SPIKE_PKT_WGT_HI, SPIKE_PKT_WGT_LO) = (ap_uint<8>)weight;
                out_pkt.data(SPIKE_PKT_TS_HI, SPIKE_PKT_TS_LO) = timestamp(SPIKE_PKT_TS_HI - SPIKE_PKT_TS_LO, 0);
                out_pkt.keep = 0xF;
                out_pkt.strb = 0xF;
                out_pkt.last = 1;
                out_pkt.id = 0;
                out_pkt.dest = 0;
                out_pkt.user = 0;
                m_axis_spikes.write(out_pkt);
                consume_post_spike = true;
            }

            if (consume_post_spike) {
                spike_out_ack_toggle = (ap_uint<1>)(!spike_out_ack_toggle);
                spike_out_ready = spike_out_ack_toggle;
                if (stdp_active) {
                    process_post_spike_aer(
                        post_id,
                        timestamp,
                        learning_params,
                        learn_bridge,
                        learn_weight_ready
                    );
                    update_eligibility_on_post_spike(post_id);
                    update_counter++;
                }
            }
        }

        // R-STDP Reward Application (uses Per-Neuron Eligibility Traces)
        if (apply_reward && stdp_active && learning_params.rstdp_enable) {
            apply_rstdp_reward(
                reward_signal,
                learning_params,
                timestamp,
                learn_bridge,
                learn_weight_ready
            );
            decay_eligibility_traces(learning_params);
        }

        // Weight Read / Checkpoint Mode (stream weights to PS/DDR)
        // Streams flat buffer sequentially; host decodes using connection table
        if ((weight_read_mode || checkpoint_mode) && !m_axis_weights.full()) {
            axis_weight_t w_pkt;
            w_pkt.data = 0;
            // Pack: [31:28] reserved, [27:20] weight, [19:0] flat index (low 20 bits)
            w_pkt.data(19, 0) = checkpoint_idx(19, 0);
            // Sign-extend packed_weight_t to 8-bit for AXI output
            if (checkpoint_idx < MAX_WEIGHT_BUFFER_SIZE) {
                packed_weight_t pw = weight_memory[checkpoint_idx];
                w_pkt.data(27, 20) = (ap_uint<8>)(weight_t)pw;  // sign-extend to 8-bit
            } else {
                w_pkt.data(27, 20) = (ap_uint<8>)0;
            }
            w_pkt.keep = 0xF;
            w_pkt.strb = 0xF;
            bool full_last = (checkpoint_idx >= (ap_uint<32>)(MAX_WEIGHT_BUFFER_SIZE - 1));
            bool chunk_last = false;
            if (checkpoint_mode && checkpoint_chunk_words != 0) {
                ap_uint<16> next_pos = checkpoint_chunk_pos + 1;
                chunk_last = (next_pos >= checkpoint_chunk_words);
            }
            w_pkt.last = (full_last || chunk_last) ? (ap_uint<1>)1 : (ap_uint<1>)0;
            w_pkt.id = 0;
            w_pkt.dest = 0;
            w_pkt.user = 0;
            m_axis_weights.write(w_pkt);

            checkpoint_idx++;
            if (checkpoint_idx >= (ap_uint<32>)MAX_WEIGHT_BUFFER_SIZE) {
                checkpoint_idx = 0;
            }
            if (chunk_last || full_last) {
                checkpoint_chunk_pos = 0;
            } else {
                checkpoint_chunk_pos++;
            }
        }

        if (enable) {
            timestamp++;
        }

        // Drive learned-weight bridge outputs.
        learn_weight_valid = learn_bridge.valid;
        if (learn_bridge.valid) {
            learn_weight_group = learn_bridge.group;
            learn_weight_src = learn_bridge.src;
            learn_weight_dst = learn_bridge.dst;
            learn_weight_data = learn_bridge.data;
            learn_weight_exc = learn_bridge.exc;
            learn_weight_is_inter = learn_bridge.is_inter;
            learn_weight_dst_group = learn_bridge.dst_group;
            learn_weight_fanout_idx = learn_bridge.fanout_idx;
        } else {
            learn_weight_group = 0;
            learn_weight_src = 0;
            learn_weight_dst = 0;
            learn_weight_data = 0;
            learn_weight_exc = 0;
            learn_weight_is_inter = 0;
            learn_weight_dst_group = 0;
            learn_weight_fanout_idx = 0;
        }
    }

    // Release encoder frame after programmed time steps
    if (encoder_frame_loaded) {
        encoder_frame_loaded = false;
    }
    last_mode = op_mode;
    
    //=========================================================================
    // Status Register Assembly
    //=========================================================================
    ap_uint<32> status = 0;
    status[0] = snn_ready;
    status[1] = snn_busy;
    status[2] = stdp_active;
    status[3] = first_spike_only;
    status[4] = learning_params.rstdp_enable;
    status[5] = encoder_enable;
    status(7, 6) = op_mode;
    status(15, 8) = update_counter(7, 0);
    status[16] = first_spike_pending;
    
    status_reg = status;
    spike_count_reg = spike_counter;
    version_reg = VERSION_ID;
    
    // Calculate weight sum for monitoring (reduced sampling to save LUTs).
    // Hold the last sampled value during checkpoint streaming to avoid adding
    // extra read pressure on weight_memory in MODE_CHECKPOINT.
    static ap_uint<32> weight_sum_shadow = 0;
    if (!checkpoint_mode) {
        ap_int<32> weight_sum = 0;
        WEIGHT_SUM: for (int i = 0; i < 64; i++) {  // Sample first 64 entries of flat buffer
            #pragma HLS PIPELINE II=1
            weight_sum += weight_memory[i];
        }
        weight_sum_shadow = (ap_uint<32>)weight_sum;
    }
    weight_sum_reg = weight_sum_shadow;
}

//=============================================================================
// Weight Memory Access Functions (for external use)
// Uses SpikePress population connection table for global_id → flat buffer lookup
// Returns/accepts packed_weight_t (SNN_WEIGHT_BITS precision)
//=============================================================================
void write_weight(
    neuron_id_t pre_id,
    neuron_id_t post_id,
    packed_weight_t weight
) {
    #pragma HLS INLINE
    int idx = weight_index(pre_id, post_id);
    if (idx >= 0) {
        weight_memory[idx] = weight;
    }
}

packed_weight_t read_weight(
    neuron_id_t pre_id,
    neuron_id_t post_id
) {
    #pragma HLS INLINE
    int idx = weight_index(pre_id, post_id);
    if (idx >= 0) {
        return weight_memory[idx];
    }
    return 0;
}

//=============================================================================
// Batch Weight Load (via AXI-Stream)
// population-aware: uses weight_index() for flat buffer lookup
//=============================================================================
void load_weights_from_stream(
    hls::stream<axis_weight_t> &weight_stream,
    ap_uint<32> num_weights
) {
    #pragma HLS INLINE off
    
    LOAD_WEIGHTS: for (int i = 0; i < num_weights; i++) {
        #pragma HLS PIPELINE II=1
        
        if (weight_stream.empty()) break;
        
        axis_weight_t pkt = weight_stream.read();
        neuron_id_t pre_id = pkt.data(7, 0);
        neuron_id_t post_id = pkt.data(15, 8);
        weight_t raw_weight = pkt.data(23, 16);
        
        int idx = weight_index(pre_id, post_id);
        if (idx >= 0) {
            // Clip 8-bit AXI weight to packed range
            weight_memory[idx] = clip_weight((ap_int<16>)raw_weight);
        }
    }
}
