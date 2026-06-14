//-----------------------------------------------------------------------------
// Title         : SpikeMold HLS Module
// Project       : SpikeMold
// File          : spikemold_top_hls.cpp
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : Inference-only HLS top-level integrating:
//                 - AXI4-Lite control/status registers
//                 - AXI4-Stream spike I/O (AER: Address Event Representation)
//                 - Delta-sigma input encoder
//                 - Population-aware packed weight memory
//                 - Direct interface to Verilog SpikeMold core
//-----------------------------------------------------------------------------

#include "../include/spikemold_top_hls.h"

//=============================================================================
// Delta-Sigma Spike Encoder
//=============================================================================
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
    ap_uint<16> increment = value;
    encoder_phase_acc[channel] += increment;

    if (encoder_phase_acc[channel] > config.delta_decay) {
        encoder_phase_acc[channel] -= config.delta_decay;
    }

    if (encoder_phase_acc[channel] >= config.delta_threshold) {
        encoder_write_axis_spike(channel, config.default_weight, time, fifo, counter);
        encoder_phase_acc[channel] -= config.delta_threshold;
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
    }
}

//=============================================================================
// Weight Memory
//=============================================================================
static packed_weight_t weight_memory[MAX_WEIGHT_BUFFER_SIZE];

static packed_weight_t clip_weight(ap_int<16> w) {
    #pragma HLS INLINE
    if (w > MAX_WEIGHT) return MAX_WEIGHT;
    if (w < MIN_WEIGHT) return MIN_WEIGHT;
    return (packed_weight_t)w;
}

//=============================================================================
// Main Top-Level Function
//=============================================================================
void spikemold_top_hls(
    ap_uint<32> ctrl_reg,
    ap_uint<32> config_reg,
    ap_uint<32> mode_reg,
    ap_uint<32> time_steps_reg,
    encoder_config_t encoder_config,
    ap_uint<32> &status_reg,
    ap_uint<32> &spike_count_reg,
    ap_uint<32> &weight_sum_reg,
    ap_uint<32> &version_reg,

    hls::stream<axis_spike_t> &s_axis_spikes,
    hls::stream<axis_data_t> &s_axis_data,
    hls::stream<axis_weight_t> &s_axis_weights,
    hls::stream<axis_spike_t> &m_axis_spikes,
    hls::stream<axis_weight_t> &m_axis_weights,

    ap_uint<1> &spike_in_valid,
    rtl_nid_t &spike_in_neuron_id,
    ap_int<8> &spike_in_weight,
    ap_uint<1> spike_in_ready,

    ap_uint<1> spike_out_valid,
    rtl_nid_t spike_out_neuron_id,
    ap_int<8> spike_out_weight,
    ap_uint<1> &spike_out_ready,

    ap_uint<1> &spikemold_enable,
    ap_uint<1> &spikemold_reset,
    ap_uint<16> &threshold_out,
    ap_uint<16> &leak_rate_out,

    ap_uint<1> spikemold_ready,
    ap_uint<1> spikemold_busy
) {
    // AXI4-Lite slave interface
    #pragma HLS INTERFACE s_axilite port=ctrl_reg bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=config_reg bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=mode_reg bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=time_steps_reg bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=encoder_config bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=status_reg bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=spike_count_reg bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=weight_sum_reg bundle=ctrl
    #pragma HLS INTERFACE s_axilite port=version_reg bundle=ctrl
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
    #pragma HLS INTERFACE ap_none port=spikemold_enable
    #pragma HLS INTERFACE ap_none port=spikemold_reset
    #pragma HLS INTERFACE ap_none port=threshold_out
    #pragma HLS INTERFACE ap_none port=leak_rate_out
    #pragma HLS INTERFACE ap_none port=spikemold_ready
    #pragma HLS INTERFACE ap_none port=spikemold_busy

    // SpikeMold datapath keeps weights on-chip. True dual-port BRAM avoids
    // checkpoint readback adding aggressive memory replication.
    #pragma HLS BIND_STORAGE variable=weight_memory type=RAM_T2P impl=BRAM latency=3

    // Delta-sigma encoder state: LUTRAM to preserve scarce Z-7020 BRAM.
    #pragma HLS BIND_STORAGE variable=encoder_phase_acc type=RAM_2P impl=LUTRAM
    #pragma HLS ARRAY_PARTITION variable=encoder_phase_acc cyclic factor=2

    static ap_uint<32> timestamp = 0;
    static ap_uint<32> spike_counter = 0;
    static bool initialized = false;
    static ap_uint<2> last_mode = MODE_INFERENCE;
    static ap_uint<32> checkpoint_idx = 0;
    static ap_uint<16> checkpoint_chunk_pos = 0;
    static ap_uint<32> encoder_spike_counter = 0;
    static bool first_spike_sent = false;
    static bool first_spike_pending = false;
    static neuron_id_t first_spike_pending_id = 0;
    static weight_t first_spike_pending_weight = 0;
    static ap_uint<1> spike_out_ack_toggle = 0;

    bool enable = ctrl_reg[0];
    bool reset = ctrl_reg[1];
    bool clear_counters = ctrl_reg[2];
    bool weight_read_mode = ctrl_reg[4];
    bool weight_load_mode = ctrl_reg[6];
    bool first_spike_only = ctrl_reg[7];
    ap_uint<2> op_mode = mode_reg(1, 0);
    ap_uint<16> checkpoint_chunk_words = mode_reg(31, 16);
    bool encoder_enable = mode_reg[8];
    bool checkpoint_mode = (op_mode == MODE_CHECKPOINT);
    ap_uint<16> time_steps = (time_steps_reg == 0) ? (ap_uint<16>)1 : (ap_uint<16>)time_steps_reg;

    ap_uint<16> threshold = config_reg(15, 0);
    ap_uint<16> leak_rate = config_reg(31, 16);

    if (reset || !initialized) {
        timestamp = 0;
        spike_counter = 0;
        encoder_spike_counter = 0;
        last_mode = MODE_INFERENCE;
        checkpoint_idx = 0;
        checkpoint_chunk_pos = 0;
        encoder_frame_loaded = false;
        first_spike_sent = false;
        first_spike_pending = false;
        first_spike_pending_id = 0;
        first_spike_pending_weight = 0;
        spike_out_ack_toggle = 0;

        RESET_ENCODER: for (int i = 0; i < MAX_INPUT_CHANNELS; i++) {
            #pragma HLS PIPELINE II=1
            encoder_phase_acc[i] = 0;
        }

        if (!initialized) {
            INIT_WEIGHT: for (int k = 0; k < MAX_WEIGHT_BUFFER_SIZE; k++) {
                #pragma HLS PIPELINE II=1
                #pragma HLS LOOP_TRIPCOUNT min=843776 max=843776
                weight_memory[k] = 0;
            }
            initialized = true;
        }
    }

    if (weight_load_mode && !s_axis_weights.empty()) {
        axis_weight_t w_pkt = s_axis_weights.read();
        neuron_id_t row = w_pkt.data(WEIGHT_LOAD_PKT_PRE_HI, WEIGHT_LOAD_PKT_PRE_LO);
        neuron_id_t col = w_pkt.data(WEIGHT_LOAD_PKT_POST_HI, WEIGHT_LOAD_PKT_POST_LO);
        weight_t weight_val = w_pkt.data(WEIGHT_LOAD_PKT_WGT_HI, WEIGHT_LOAD_PKT_WGT_LO);

        int widx = weight_index(row, col);
        if (widx >= 0) {
            weight_memory[widx] = clip_weight((ap_int<16>)weight_val);
        }
    }

    if (clear_counters) {
        spike_counter = 0;
        encoder_spike_counter = 0;
    }

    if (!enable) {
        first_spike_sent = false;
        first_spike_pending = false;
        first_spike_pending_id = 0;
        first_spike_pending_weight = 0;
    }

    spikemold_enable = enable;
    spikemold_reset = reset;
    threshold_out = threshold;
    leak_rate_out = leak_rate;

    if (encoder_enable && !encoder_frame_loaded && !s_axis_data.empty()) {
        LOAD_FRAME: for (int i = 0; i < FRAME_LOAD_BEATS; i++) {
            #pragma HLS PIPELINE II=1
            if (s_axis_data.empty()) break;
            axis_data_t beat = s_axis_data.read();
            int base = i * 4;
            if (base < MAX_INPUT_CHANNELS) encoder_frame.pixels[base] = beat.data(7, 0);
            if (base + 1 < MAX_INPUT_CHANNELS) encoder_frame.pixels[base + 1] = beat.data(15, 8);
            if (base + 2 < MAX_INPUT_CHANNELS) encoder_frame.pixels[base + 2] = beat.data(23, 16);
            if (base + 3 < MAX_INPUT_CHANNELS) encoder_frame.pixels[base + 3] = beat.data(31, 24);
            if (beat.last) break;
        }
        encoder_frame_loaded = true;
    }

    if (op_mode != last_mode && checkpoint_mode) {
        checkpoint_idx = 0;
        checkpoint_chunk_pos = 0;
    }

    hls::stream<encoder_axis_word_t> encoder_spikes("encoder_spikes");
    #pragma HLS STREAM variable=encoder_spikes depth=32

    TIME_LOOP: for (ap_uint<16> t = 0; t < time_steps; t++) {
        #pragma HLS LOOP_FLATTEN off

        if (encoder_enable && encoder_frame_loaded) {
            run_encoder_once(true, encoder_config, timestamp, encoder_spikes, encoder_spike_counter);
        }

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
                spike_counter++;
            }
        }

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
                    first_spike_pending_id = post_id;
                    first_spike_pending_weight = weight;
                    first_spike_pending = true;
                    first_spike_sent = true;
                }
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
            }
        }

        if ((weight_read_mode || checkpoint_mode) && !m_axis_weights.full()) {
            axis_weight_t w_pkt;
            w_pkt.data = 0;
            w_pkt.data(19, 0) = checkpoint_idx(19, 0);
            if (checkpoint_idx < MAX_WEIGHT_BUFFER_SIZE) {
                packed_weight_t pw = weight_memory[checkpoint_idx];
                w_pkt.data(27, 20) = (ap_uint<8>)(weight_t)pw;
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
    }

    if (encoder_frame_loaded) {
        encoder_frame_loaded = false;
    }
    last_mode = op_mode;

    ap_uint<32> status = 0;
    status[0] = spikemold_ready;
    status[1] = spikemold_busy;
    status[2] = 0;
    status[3] = first_spike_only;
    status[4] = 0;
    status[5] = encoder_enable;
    status(7, 6) = op_mode;
    status(15, 8) = 0;
    status[16] = first_spike_pending;

    status_reg = status;
    spike_count_reg = spike_counter;
    version_reg = VERSION_ID;

    static ap_uint<32> weight_sum_shadow = 0;
    if (!checkpoint_mode) {
        ap_int<32> weight_sum = 0;
        WEIGHT_SUM: for (int i = 0; i < 64; i++) {
            #pragma HLS PIPELINE II=1
            weight_sum += weight_memory[i];
        }
        weight_sum_shadow = (ap_uint<32>)weight_sum;
    }
    weight_sum_reg = weight_sum_shadow;
}

//=============================================================================
// Weight Memory Access Functions
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

void load_weights_from_stream(
    hls::stream<axis_weight_t> &weight_stream,
    ap_uint<32> num_weights
) {
    #pragma HLS INLINE off

    LOAD_WEIGHTS: for (int i = 0; i < num_weights; i++) {
        #pragma HLS PIPELINE II=1
        if (weight_stream.empty()) break;

        axis_weight_t pkt = weight_stream.read();
        neuron_id_t pre_id = pkt.data(WEIGHT_LOAD_PKT_PRE_HI, WEIGHT_LOAD_PKT_PRE_LO);
        neuron_id_t post_id = pkt.data(WEIGHT_LOAD_PKT_POST_HI, WEIGHT_LOAD_PKT_POST_LO);
        weight_t raw_weight = pkt.data(WEIGHT_LOAD_PKT_WGT_HI, WEIGHT_LOAD_PKT_WGT_LO);

        int idx = weight_index(pre_id, post_id);
        if (idx >= 0) {
            weight_memory[idx] = clip_weight((ap_int<16>)raw_weight);
        }
    }
}
