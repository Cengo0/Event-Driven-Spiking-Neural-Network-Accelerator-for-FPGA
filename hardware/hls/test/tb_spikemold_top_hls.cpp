//-----------------------------------------------------------------------------
// Title         : SpikeMold Top-Level HLS Testbench
// Project       : PYNQ-Z2 SpikeMold
// File          : tb_spikemold_top_hls.cpp
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : C++ testbench for SNN top-level with on-chip learning
//-----------------------------------------------------------------------------

#include <iostream>
#include <iomanip>
#include <cmath>
#include "../include/spikemold_top_hls.h"

// Test configuration
#define NUM_TEST_SPIKES 20
#define NUM_TIMESTEPS 100
#define VERBOSE 1

static const neuron_id_t TEST_FIRST_PRE_ID = SNN_CONN_0_SRC_ID_START;
static const neuron_id_t TEST_SECOND_PRE_ID = SNN_CONN_0_SRC_ID_START + 2;
static const neuron_id_t TEST_POST_ID = SNN_CONN_0_DST_ID_START;
static const rtl_nid_t TEST_POST_RTL_ID = (rtl_nid_t)SNN_CONN_0_DST_ID_START;
static const int TEST_FIRST_WEIGHT_INDEX = 0;
static const int TEST_SECOND_WEIGHT_INDEX = 2 * SNN_CONN_0_DST_SIZE;

// Error counter
int error_count = 0;

//=============================================================================
// Helper Functions
//=============================================================================
void print_result(const char* test_name, bool passed) {
    std::cout << "  " << (passed ? "PASS" : "FAIL") << ": " << test_name << std::endl;
    if (!passed) error_count++;
}

void drain_spike_stream(hls::stream<axis_spike_t> &stream) {
    while (!stream.empty()) {
        stream.read();
    }
}

void drain_weight_stream(hls::stream<axis_weight_t> &stream) {
    while (!stream.empty()) {
        stream.read();
    }
}

axis_spike_t create_spike(neuron_id_t neuron_id, int8_t weight, uint16_t timestamp) {
    axis_spike_t pkt;
    pkt.data = 0;
    pkt.data(SPIKE_PKT_ID_HI, SPIKE_PKT_ID_LO) = neuron_id;
    pkt.data(SPIKE_PKT_WGT_HI, SPIKE_PKT_WGT_LO) = (ap_uint<8>)weight;
    pkt.data(SPIKE_PKT_TS_HI, SPIKE_PKT_TS_LO) =
        (ap_uint<SPIKE_PKT_TS_HI - SPIKE_PKT_TS_LO + 1>)timestamp;
    pkt.keep = 0xF;
    pkt.strb = 0xF;
    pkt.last = 1;
    pkt.id = 0;
    pkt.dest = 0;
    pkt.user = 0;
    return pkt;
}

axis_weight_t create_weight_packet(neuron_id_t pre_id, neuron_id_t post_id, int8_t weight) {
    axis_weight_t pkt;
    pkt.data = 0;
    pkt.data(WEIGHT_LOAD_PKT_PRE_HI, WEIGHT_LOAD_PKT_PRE_LO) =
        (ap_uint<WEIGHT_LOAD_PKT_ID_WIDTH>)pre_id;
    pkt.data(WEIGHT_LOAD_PKT_POST_HI, WEIGHT_LOAD_PKT_POST_LO) =
        (ap_uint<WEIGHT_LOAD_PKT_ID_WIDTH>)post_id;
    pkt.data(WEIGHT_LOAD_PKT_WGT_HI, WEIGHT_LOAD_PKT_WGT_LO) = (ap_uint<8>)weight;
    pkt.keep = 0xF;
    pkt.strb = 0xF;
    pkt.last = 1;
    pkt.id = 0;
    pkt.dest = 0;
    pkt.user = 0;
    return pkt;
}

learning_params_t get_default_params() {
    learning_params_t params;
    params.a_plus = 0.1;
    params.a_minus = 0.12;
    params.tau_plus = 20;
    params.tau_minus = 20;
    params.stdp_window = 50;
    params.learning_rate = 0.01;
    params.rstdp_enable = false;
    params.trace_decay = 0.99;
    params.reward_scale = 1.0;
    return params;
}

encoder_config_t get_default_encoder_config() {
    encoder_config_t cfg;
    cfg.encoding_type = ENC_NONE;
    cfg.delta_threshold = 1024;
    cfg.delta_decay = 1;
    cfg.num_channels = 0;
    cfg.default_weight = 1;
    return cfg;
}

//=============================================================================
// Test 1: Basic Control Register Operations
//=============================================================================
void test_control_registers() {
    std::cout << "\n=== Test 1: Control Registers ===" << std::endl;
    
    // Streams
    hls::stream<axis_spike_t> s_axis_spikes;
    hls::stream<axis_data_t> s_axis_data;
    hls::stream<axis_weight_t> s_axis_weights;
    hls::stream<axis_spike_t> m_axis_spikes;
    hls::stream<axis_weight_t> m_axis_weights;
    
    // Control/Status
    ap_uint<32> ctrl_reg = 0;
    ap_uint<32> config_reg = 0;
    ap_uint<32> mode_reg = 0;
    ap_uint<32> time_steps_reg = 1;
    encoder_config_t encoder_cfg = get_default_encoder_config();
    learning_params_t params = get_default_params();
    ap_uint<32> status_reg, spike_count_reg, weight_sum_reg, version_reg;
    ap_int<8> reward_signal = 0;
    
    // Verilog interface (simulated)
    ap_uint<1> spike_in_valid, spike_out_ready, spikemold_enable, spikemold_reset;
    rtl_nid_t spike_in_neuron_id;
    ap_int<8> spike_in_weight;
    ap_uint<16> threshold_out, leak_rate_out;
    
    ap_uint<1> spike_in_ready = 1;
    ap_uint<1> spike_out_valid = 0;
    rtl_nid_t spike_out_neuron_id = 0;
    ap_int<8> spike_out_weight = 0;
    ap_uint<1> spikemold_ready = 1;
    ap_uint<1> spikemold_busy = 0;
    ap_uint<1> learn_weight_valid = 0;
    group_id_t learn_weight_group = 0;
    local_id_t learn_weight_src = 0;
    local_id_t learn_weight_dst = 0;
    ap_uint<8> learn_weight_data = 0;
    ap_uint<1> learn_weight_exc = 0;
    ap_uint<1> learn_weight_is_inter = 0;
    group_id_t learn_weight_dst_group = 0;
    fanout_idx_t learn_weight_fanout_idx = 0;
    ap_uint<1> learn_weight_ready = 1;
    
    // Test reset
    ctrl_reg = 0x02;  // Reset bit
    config_reg = (100 << 16) | 51;  // leak_rate=100, threshold=51
    
        spikemold_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                    status_reg, spike_count_reg,
                    weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                    m_axis_spikes,
                    m_axis_weights, reward_signal,
                spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                spikemold_enable, spikemold_reset, threshold_out, leak_rate_out,
                spikemold_ready, spikemold_busy);
    
    print_result("Reset signal routed", spikemold_reset == 1);
    print_result("Version register set", version_reg == VERSION_ID);
    print_result("Threshold routed", threshold_out == 51);
    print_result("Leak rate routed", leak_rate_out == 100);
    
    // Test enable
    ctrl_reg = 0x01;  // Enable bit
    
        spikemold_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                    status_reg, spike_count_reg,
                    weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                    m_axis_spikes,
                    m_axis_weights, reward_signal,
                spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                spikemold_enable, spikemold_reset, threshold_out, leak_rate_out,
                spikemold_ready, spikemold_busy);
    
    print_result("Enable signal routed", spikemold_enable == 1);
}

//=============================================================================
// Test 2: Spike Input Path
//=============================================================================
void test_spike_input() {
    std::cout << "\n=== Test 2: Spike Input Path ===" << std::endl;
    
    hls::stream<axis_spike_t> s_axis_spikes;
    hls::stream<axis_data_t> s_axis_data;
    hls::stream<axis_weight_t> s_axis_weights;
    hls::stream<axis_spike_t> m_axis_spikes;
    hls::stream<axis_weight_t> m_axis_weights;
    
    ap_uint<32> ctrl_reg = 0x01;  // Enable
    ap_uint<32> config_reg = (100 << 16) | 51;
    ap_uint<32> mode_reg = 0;
    ap_uint<32> time_steps_reg = 1;
    encoder_config_t encoder_cfg = get_default_encoder_config();
    learning_params_t params = get_default_params();
    ap_uint<32> status_reg, spike_count_reg, weight_sum_reg, version_reg;
    ap_int<8> reward_signal = 0;
    
    ap_uint<1> spike_in_valid, spike_out_ready, spikemold_enable, spikemold_reset;
    rtl_nid_t spike_in_neuron_id;
    ap_int<8> spike_in_weight;
    ap_uint<16> threshold_out, leak_rate_out;
    
    ap_uint<1> spike_in_ready = 1;
    ap_uint<1> spike_out_valid = 0;
    rtl_nid_t spike_out_neuron_id = 0;
    ap_int<8> spike_out_weight = 0;
    ap_uint<1> spikemold_ready = 1;
    ap_uint<1> spikemold_busy = 0;
    ap_uint<1> learn_weight_valid = 0;
    group_id_t learn_weight_group = 0;
    local_id_t learn_weight_src = 0;
    local_id_t learn_weight_dst = 0;
    ap_uint<8> learn_weight_data = 0;
    ap_uint<1> learn_weight_exc = 0;
    ap_uint<1> learn_weight_is_inter = 0;
    group_id_t learn_weight_dst_group = 0;
    fanout_idx_t learn_weight_fanout_idx = 0;
    ap_uint<1> learn_weight_ready = 1;
    
    // Send spikes
    for (int i = 0; i < 5; i++) {
        s_axis_spikes.write(create_spike(i, 10 + i, 100 + i));
    }
    
    int spikes_received = 0;
    bool ids_ok = true;
    bool weights_ok = true;
    for (int t = 0; t < 10; t++) {
        spikemold_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes,
                m_axis_weights, reward_signal,
                    spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                    spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                spikemold_enable, spikemold_reset, threshold_out, leak_rate_out,
                    spikemold_ready, spikemold_busy);
        
        if (spike_in_valid) {
            int expected_id = spikes_received;
            int expected_weight = 10 + spikes_received;
            if ((int)spike_in_neuron_id != expected_id) ids_ok = false;
            if ((int)spike_in_weight != expected_weight) weights_ok = false;

            if (VERBOSE) {
                std::cout << "  Spike: neuron=" << (int)spike_in_neuron_id 
                          << " weight=" << (int)spike_in_weight << std::endl;
            }
            spikes_received++;
        }
    }
    
    print_result("All input spikes forwarded", spikes_received == 5);
    print_result("Input spike neuron IDs preserved", ids_ok);
    print_result("Input spike weights preserved", weights_ok);
    print_result("Spike counter updated", spike_count_reg == 5);
}

//=============================================================================
// Test 3: Spike Output Path
//=============================================================================
void test_spike_output() {
    std::cout << "\n=== Test 3: Spike Output Path ===" << std::endl;
    
    hls::stream<axis_spike_t> s_axis_spikes;
    hls::stream<axis_data_t> s_axis_data;
    hls::stream<axis_weight_t> s_axis_weights;
    hls::stream<axis_spike_t> m_axis_spikes;
    hls::stream<axis_weight_t> m_axis_weights;
    
    ap_uint<32> ctrl_reg = 0x01;
    ap_uint<32> config_reg = (100 << 16) | 51;
    ap_uint<32> mode_reg = 0;
    ap_uint<32> time_steps_reg = 1;
    encoder_config_t encoder_cfg = get_default_encoder_config();
    learning_params_t params = get_default_params();
    ap_uint<32> status_reg, spike_count_reg, weight_sum_reg, version_reg;
    ap_int<8> reward_signal = 0;
    
    ap_uint<1> spike_in_valid, spike_out_ready, spikemold_enable, spikemold_reset;
    rtl_nid_t spike_in_neuron_id;
    ap_int<8> spike_in_weight;
    ap_uint<16> threshold_out, leak_rate_out;
    
    ap_uint<1> spike_in_ready = 1;
    ap_uint<1> spike_out_valid = 0;
    rtl_nid_t spike_out_neuron_id = 0;
    ap_int<8> spike_out_weight = 0;
    ap_uint<1> spikemold_ready = 1;
    ap_uint<1> spikemold_busy = 0;
    ap_uint<1> learn_weight_valid = 0;
    group_id_t learn_weight_group = 0;
    local_id_t learn_weight_src = 0;
    local_id_t learn_weight_dst = 0;
    ap_uint<8> learn_weight_data = 0;
    ap_uint<1> learn_weight_exc = 0;
    ap_uint<1> learn_weight_is_inter = 0;
    group_id_t learn_weight_dst_group = 0;
    fanout_idx_t learn_weight_fanout_idx = 0;
    ap_uint<1> learn_weight_ready = 1;
    
    // Simulate output spikes from Verilog core
    int spikes_collected = 0;
    bool out_ids_ok = true;
    bool out_weights_ok = true;
    int expected_ids[3] = {0, 2, 4};
    int expected_weights[3] = {20, 21, 22};

    for (int t = 0; t < 10; t++) {
        // Simulate Verilog generating a spike
        if (t < 3) {
            spike_out_valid = 1;
            spike_out_neuron_id = t * 2;
            spike_out_weight = 20 + t;
        } else {
            spike_out_valid = 0;
        }
        
        spikemold_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes,
                m_axis_weights, reward_signal,
                    spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                    spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                spikemold_enable, spikemold_reset, threshold_out, leak_rate_out,
                    spikemold_ready, spikemold_busy);
    }
    
    // Check output stream
    while (!m_axis_spikes.empty()) {
        axis_spike_t pkt = m_axis_spikes.read();
        int out_id = (int)pkt.data(SPIKE_PKT_ID_HI, SPIKE_PKT_ID_LO);
        int out_weight = (int)(int8_t)pkt.data(SPIKE_PKT_WGT_HI, SPIKE_PKT_WGT_LO);

        if (spikes_collected < 3) {
            if (out_id != expected_ids[spikes_collected]) out_ids_ok = false;
            if (out_weight != expected_weights[spikes_collected]) out_weights_ok = false;
        } else {
            out_ids_ok = false;
            out_weights_ok = false;
        }

        if (VERBOSE) {
            std::cout << "  Output: neuron=" << out_id
                      << " weight=" << out_weight << std::endl;
        }
        spikes_collected++;
    }
    
    print_result("Output spikes collected", spikes_collected == 3);
    print_result("Output spike neuron IDs preserved", out_ids_ok);
    print_result("Output spike weights preserved", out_weights_ok);
}

//=============================================================================
// Test 4: STDP Learning
//=============================================================================
void test_stdp_learning() {
    std::cout << "\n=== Test 4: STDP Learning ===" << std::endl;
    
    hls::stream<axis_spike_t> s_axis_spikes;
    hls::stream<axis_data_t> s_axis_data;
    hls::stream<axis_weight_t> s_axis_weights;
    hls::stream<axis_spike_t> m_axis_spikes;
    hls::stream<axis_weight_t> m_axis_weights;
    
    ap_uint<32> ctrl_reg = 0x09;  // Enable + Learning enable (bit 0 and bit 3)
    ap_uint<32> config_reg = (100 << 16) | 51;
    ap_uint<32> mode_reg = MODE_TRAIN_STDP;
    ap_uint<32> time_steps_reg = 1;
    encoder_config_t encoder_cfg = get_default_encoder_config();
    learning_params_t params = get_default_params();
    params.a_plus = 0.5;
    params.a_minus = 0.5;
    params.learning_rate = 0.1;
    
    ap_uint<32> status_reg, spike_count_reg, weight_sum_reg, version_reg;
    ap_int<8> reward_signal = 0;
    
    ap_uint<1> spike_in_valid, spike_out_ready, spikemold_enable, spikemold_reset;
    rtl_nid_t spike_in_neuron_id;
    ap_int<8> spike_in_weight;
    ap_uint<16> threshold_out, leak_rate_out;
    
    ap_uint<1> spike_in_ready = 1;
    ap_uint<1> spike_out_valid = 0;
    rtl_nid_t spike_out_neuron_id = 0;
    ap_int<8> spike_out_weight = 0;
    ap_uint<1> spikemold_ready = 1;
    ap_uint<1> spikemold_busy = 0;
    ap_uint<1> learn_weight_valid = 0;
    group_id_t learn_weight_group = 0;
    local_id_t learn_weight_src = 0;
    local_id_t learn_weight_dst = 0;
    ap_uint<8> learn_weight_data = 0;
    ap_uint<1> learn_weight_exc = 0;
    ap_uint<1> learn_weight_is_inter = 0;
    group_id_t learn_weight_dst_group = 0;
    fanout_idx_t learn_weight_fanout_idx = 0;
    ap_uint<1> learn_weight_ready = 1;
    
    // First, reset to initialize
    ctrl_reg = 0x02;
    spikemold_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes,
                m_axis_weights, reward_signal,
                spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                spikemold_enable, spikemold_reset, threshold_out, leak_rate_out,
                spikemold_ready, spikemold_busy);
    
    // Enable with learning
    ctrl_reg = 0x09;
    
    // Scenario on connection 0 from generated SpikeMold topology:
    // pre spike from TEST_FIRST_PRE_ID, then post spike from TEST_POST_ID.
    s_axis_spikes.write(create_spike(TEST_FIRST_PRE_ID, 10, 5));
    
    for (int t = 0; t < 5; t++) {
        spikemold_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes,
                m_axis_weights, reward_signal,
                    spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                    spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                spikemold_enable, spikemold_reset, threshold_out, leak_rate_out,
                    spikemold_ready, spikemold_busy);
    }
    
    // Now simulate post-synaptic spike.
    for (int t = 5; t < 15; t++) {
        if (t == 10) {
            spike_out_valid = 1;
            spike_out_neuron_id = TEST_POST_RTL_ID;
            spike_out_weight = 20;
        } else {
            spike_out_valid = 0;
        }
        
        spikemold_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes,
                m_axis_weights, reward_signal,
                    spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                    spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                spikemold_enable, spikemold_reset, threshold_out, leak_rate_out,
                    spikemold_ready, spikemold_busy);
    }
    
    // Check learning status
    bool learning_active = status_reg[2];
    print_result("Learning enabled in status", learning_active);
    
    std::cout << "  Weight sum (sample): " << weight_sum_reg << std::endl;
    drain_spike_stream(m_axis_spikes);
    drain_weight_stream(m_axis_weights);
}

//=============================================================================
// Test 5: R-STDP with Reward
//=============================================================================
void test_rstdp_learning() {
    std::cout << "\n=== Test 5: R-STDP Learning ===" << std::endl;
    
    hls::stream<axis_spike_t> s_axis_spikes;
    hls::stream<axis_data_t> s_axis_data;
    hls::stream<axis_weight_t> s_axis_weights;
    hls::stream<axis_spike_t> m_axis_spikes;
    hls::stream<axis_weight_t> m_axis_weights;
    
    ap_uint<32> ctrl_reg = 0x09;
    ap_uint<32> config_reg = (100 << 16) | 51;
    ap_uint<32> mode_reg = MODE_TRAIN_STDP;
    ap_uint<32> time_steps_reg = 1;
    encoder_config_t encoder_cfg = get_default_encoder_config();
    learning_params_t params = get_default_params();
    params.rstdp_enable = true;
    params.trace_decay = 0.95;
    params.reward_scale = 1.0;
    
    ap_uint<32> status_reg, spike_count_reg, weight_sum_reg, version_reg;
    ap_int<8> reward_signal = 64;  // Positive reward
    
    ap_uint<1> spike_in_valid, spike_out_ready, spikemold_enable, spikemold_reset;
    rtl_nid_t spike_in_neuron_id;
    ap_int<8> spike_in_weight;
    ap_uint<16> threshold_out, leak_rate_out;
    
    ap_uint<1> spike_in_ready = 1;
    ap_uint<1> spike_out_valid = 0;
    rtl_nid_t spike_out_neuron_id = 0;
    ap_int<8> spike_out_weight = 0;
    ap_uint<1> spikemold_ready = 1;
    ap_uint<1> spikemold_busy = 0;
    ap_uint<1> learn_weight_valid = 0;
    group_id_t learn_weight_group = 0;
    local_id_t learn_weight_src = 0;
    local_id_t learn_weight_dst = 0;
    ap_uint<8> learn_weight_data = 0;
    ap_uint<1> learn_weight_exc = 0;
    ap_uint<1> learn_weight_is_inter = 0;
    group_id_t learn_weight_dst_group = 0;
    fanout_idx_t learn_weight_fanout_idx = 0;
    ap_uint<1> learn_weight_ready = 1;
    
    // Reset
    ctrl_reg = 0x02;
    spikemold_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes,
                m_axis_weights, reward_signal,
                spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                spikemold_enable, spikemold_reset, threshold_out, leak_rate_out,
                spikemold_ready, spikemold_busy);
    
    // Run with R-STDP
    ctrl_reg = 0x29;  // Enable + Learning + Apply reward (bits 0, 3, 5)
    
    // Generate spike activity on connection 0.
    s_axis_spikes.write(create_spike(TEST_FIRST_PRE_ID, 10, 0));
    
    for (int t = 0; t < 20; t++) {
        if (t == 5) {
            spike_out_valid = 1;
            spike_out_neuron_id = TEST_POST_RTL_ID;
            spike_out_weight = 20;
        } else {
            spike_out_valid = 0;
        }
        
        spikemold_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes,
                m_axis_weights, reward_signal,
                    spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                    spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                spikemold_enable, spikemold_reset, threshold_out, leak_rate_out,
                    spikemold_ready, spikemold_busy);
    }
    
    bool rstdp_enabled = status_reg[4];
    print_result("R-STDP enabled in status", rstdp_enabled);
    
    std::cout << "  Weight sum after R-STDP: " << weight_sum_reg << std::endl;
    drain_spike_stream(m_axis_spikes);
    drain_weight_stream(m_axis_weights);
}

//=============================================================================
// Test 6: Checkpoint Stream Payload Format
//=============================================================================
void test_checkpoint_stream_payload() {
    std::cout << "\n=== Test 6: Checkpoint Stream Payload ===" << std::endl;

    hls::stream<axis_spike_t> s_axis_spikes;
    hls::stream<axis_data_t> s_axis_data;
    hls::stream<axis_weight_t> s_axis_weights;
    hls::stream<axis_spike_t> m_axis_spikes;
    hls::stream<axis_weight_t> m_axis_weights;

    ap_uint<32> ctrl_reg = 0;
    ap_uint<32> config_reg = 0;
    ap_uint<32> mode_reg = MODE_INFERENCE;
    ap_uint<32> time_steps_reg = 1;
    encoder_config_t encoder_cfg = get_default_encoder_config();
    learning_params_t params = get_default_params();
    ap_uint<32> status_reg = 0, spike_count_reg = 0, weight_sum_reg = 0, version_reg = 0;
    ap_int<8> reward_signal = 0;

    ap_uint<1> spike_in_valid, spike_out_ready, spikemold_enable, spikemold_reset;
    rtl_nid_t spike_in_neuron_id;
    ap_int<8> spike_in_weight;
    ap_uint<16> threshold_out, leak_rate_out;

    ap_uint<1> spike_in_ready = 1;
    ap_uint<1> spike_out_valid = 0;
    rtl_nid_t spike_out_neuron_id = 0;
    ap_int<8> spike_out_weight = 0;
    ap_uint<1> spikemold_ready = 1;
    ap_uint<1> spikemold_busy = 0;
    ap_uint<1> learn_weight_valid = 0;
    group_id_t learn_weight_group = 0;
    local_id_t learn_weight_src = 0;
    local_id_t learn_weight_dst = 0;
    ap_uint<8> learn_weight_data = 0;
    ap_uint<1> learn_weight_exc = 0;
    ap_uint<1> learn_weight_is_inter = 0;
    group_id_t learn_weight_dst_group = 0;
    fanout_idx_t learn_weight_fanout_idx = 0;
    ap_uint<1> learn_weight_ready = 1;

    // Hard reset
    ctrl_reg = 0x02;
    spikemold_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes, m_axis_weights, reward_signal,
                spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                spikemold_enable, spikemold_reset, threshold_out, leak_rate_out,
                spikemold_ready, spikemold_busy);

    // Load two known weights from the generated connection 0:
    //   first index  : first source neuron -> first destination neuron, +3
    //   second index : third source neuron -> first destination neuron, -3
    ctrl_reg = 0x41;  // enable + weight_load_mode
    mode_reg = MODE_INFERENCE;
    s_axis_weights.write(create_weight_packet(TEST_FIRST_PRE_ID, TEST_POST_ID, 3));
    s_axis_weights.write(create_weight_packet(TEST_SECOND_PRE_ID, TEST_POST_ID, -3));
    for (int i = 0; i < 4; i++) {
        spikemold_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                    status_reg, spike_count_reg,
                    weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                    m_axis_spikes, m_axis_weights, reward_signal,
                    spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                    spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                    learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                    learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                    learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                    spikemold_enable, spikemold_reset, threshold_out, leak_rate_out,
                    spikemold_ready, spikemold_busy);
    }

    // Enter checkpoint mode and read back stream.
    ctrl_reg = 0x11;  // enable + weight_read_mode
    mode_reg = MODE_CHECKPOINT;

    bool found_first_weight = false;
    bool found_second_weight = false;
    int8_t first_weight_value = 0;
    int8_t second_weight_value = 0;
    int nonzero_payload_words = 0;
    int packets_seen = 0;

    for (int cyc = 0; cyc < 1200; cyc++) {
        spikemold_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                    status_reg, spike_count_reg,
                    weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                    m_axis_spikes, m_axis_weights, reward_signal,
                    spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                    spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                    learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                    learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                    learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                    spikemold_enable, spikemold_reset, threshold_out, leak_rate_out,
                    spikemold_ready, spikemold_busy);

        if (!m_axis_weights.empty()) {
            axis_weight_t pkt = m_axis_weights.read();
            packets_seen++;
            int idx = (int)pkt.data(19, 0);
            int8_t w = (int8_t)(ap_uint<8>)pkt.data(27, 20);
            if (w != 0) nonzero_payload_words++;

            if (idx == TEST_FIRST_WEIGHT_INDEX) {
                found_first_weight = true;
                first_weight_value = w;
            } else if (idx == TEST_SECOND_WEIGHT_INDEX) {
                found_second_weight = true;
                second_weight_value = w;
            }
        }
    }

    print_result("Checkpoint stream produced packets", packets_seen > 0);
    print_result("Checkpoint payload has non-zero words", nonzero_payload_words > 0);
    print_result("Checkpoint first loaded weight present", found_first_weight);
    print_result("Checkpoint first loaded weight matches", found_first_weight && first_weight_value == 3);
    print_result("Checkpoint second loaded weight present", found_second_weight);
    print_result("Checkpoint second loaded weight matches", found_second_weight && second_weight_value == -3);
}

//=============================================================================
// Test 7: STDP Update Visibility in Checkpoint Stream
//=============================================================================
void test_stdp_checkpoint_visibility() {
    std::cout << "\n=== Test 7: STDP -> Checkpoint Visibility ===" << std::endl;

    hls::stream<axis_spike_t> s_axis_spikes;
    hls::stream<axis_data_t> s_axis_data;
    hls::stream<axis_weight_t> s_axis_weights;
    hls::stream<axis_spike_t> m_axis_spikes;
    hls::stream<axis_weight_t> m_axis_weights;

    ap_uint<32> ctrl_reg = 0;
    ap_uint<32> config_reg = (100 << 16) | 51;
    ap_uint<32> mode_reg = MODE_INFERENCE;
    ap_uint<32> time_steps_reg = 1;
    encoder_config_t encoder_cfg = get_default_encoder_config();
    learning_params_t params = get_default_params();
    params.a_plus = 0.5;
    params.a_minus = 0.5;
    params.learning_rate = 0.1;
    ap_uint<32> status_reg = 0, spike_count_reg = 0, weight_sum_reg = 0, version_reg = 0;
    ap_int<8> reward_signal = 0;

    ap_uint<1> spike_in_valid, spike_out_ready, spikemold_enable, spikemold_reset;
    rtl_nid_t spike_in_neuron_id;
    ap_int<8> spike_in_weight;
    ap_uint<16> threshold_out, leak_rate_out;

    ap_uint<1> spike_in_ready = 1;
    ap_uint<1> spike_out_valid = 0;
    rtl_nid_t spike_out_neuron_id = 0;
    ap_int<8> spike_out_weight = 0;
    ap_uint<1> spikemold_ready = 1;
    ap_uint<1> spikemold_busy = 0;
    ap_uint<1> learn_weight_valid = 0;
    group_id_t learn_weight_group = 0;
    local_id_t learn_weight_src = 0;
    local_id_t learn_weight_dst = 0;
    ap_uint<8> learn_weight_data = 0;
    ap_uint<1> learn_weight_exc = 0;
    ap_uint<1> learn_weight_is_inter = 0;
    group_id_t learn_weight_dst_group = 0;
    fanout_idx_t learn_weight_fanout_idx = 0;
    ap_uint<1> learn_weight_ready = 1;

    // Hard reset
    ctrl_reg = 0x02;
    spikemold_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes, m_axis_weights, reward_signal,
                spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                spikemold_enable, spikemold_reset, threshold_out, leak_rate_out,
                spikemold_ready, spikemold_busy);

    // STDP mode: one pre spike + one post spike on generated connection 0.
    ctrl_reg = 0x09;  // enable + learning_enable
    mode_reg = MODE_TRAIN_STDP;
    s_axis_spikes.write(create_spike(TEST_FIRST_PRE_ID, 10, 0));
    spike_out_valid = 0;
    spikemold_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes, m_axis_weights, reward_signal,
                spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                spikemold_enable, spikemold_reset, threshold_out, leak_rate_out,
                spikemold_ready, spikemold_busy);

    spike_out_valid = 1;
    spike_out_neuron_id = TEST_POST_RTL_ID;
    spike_out_weight = 20;
    spikemold_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes, m_axis_weights, reward_signal,
                spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                spikemold_enable, spikemold_reset, threshold_out, leak_rate_out,
                spikemold_ready, spikemold_busy);

    // Drain one extra cycle
    spike_out_valid = 0;
    spikemold_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes, m_axis_weights, reward_signal,
                spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                spikemold_enable, spikemold_reset, threshold_out, leak_rate_out,
                spikemold_ready, spikemold_busy);

    bool stdp_weight_sum_nonzero = ((int)weight_sum_reg != 0);

    // Checkpoint capture
    ctrl_reg = 0x11;  // enable + weight_read_mode
    mode_reg = MODE_CHECKPOINT;
    bool found_first_weight = false;
    int8_t first_weight_value = 0;
    int nonzero_payload_words = 0;
    int packets_seen = 0;

    for (int cyc = 0; cyc < 2048; cyc++) {
        spikemold_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                    status_reg, spike_count_reg,
                    weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                    m_axis_spikes, m_axis_weights, reward_signal,
                    spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                    spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                    learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                    learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                    learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                    spikemold_enable, spikemold_reset, threshold_out, leak_rate_out,
                    spikemold_ready, spikemold_busy);

        if (!m_axis_weights.empty()) {
            axis_weight_t pkt = m_axis_weights.read();
            packets_seen++;
            int idx = (int)pkt.data(19, 0);
            int8_t w = (int8_t)(ap_uint<8>)pkt.data(27, 20);
            if (w != 0) nonzero_payload_words++;
            if (idx == TEST_FIRST_WEIGHT_INDEX) {
                found_first_weight = true;
                first_weight_value = w;
            }
        }
    }

    print_result("STDP run changed sampled weight sum", stdp_weight_sum_nonzero);
    print_result("Checkpoint stream produced packets after STDP", packets_seen > 0);
    print_result("Checkpoint payload has non-zero words after STDP", nonzero_payload_words > 0);
    print_result("Checkpoint learned weight seen after STDP", found_first_weight);
    print_result("Checkpoint learned weight is non-zero after STDP",
                 found_first_weight && first_weight_value != 0);
    drain_spike_stream(m_axis_spikes);
    drain_weight_stream(m_axis_weights);
}

//=============================================================================
// Main
//=============================================================================
int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "SpikeMold Top-Level HLS Testbench" << std::endl;
    std::cout << "On-Chip Learning Test Suite" << std::endl;
    std::cout << "========================================" << std::endl;
    
    test_control_registers();
    test_spike_input();
    test_spike_output();
    test_stdp_learning();
    test_rstdp_learning();
    test_checkpoint_stream_payload();
    test_stdp_checkpoint_visibility();
    
    std::cout << "\n========================================" << std::endl;
    if (error_count == 0) {
        std::cout << "All tests PASSED!" << std::endl;
    } else {
        std::cout << "Tests completed with " << error_count << " errors" << std::endl;
    }
    std::cout << "========================================" << std::endl;
    
    return error_count;
}
