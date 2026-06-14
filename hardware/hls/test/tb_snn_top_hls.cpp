//-----------------------------------------------------------------------------
// Title         : SNN Top-Level HLS Testbench
// Project       : PYNQ-Z2 SNN Accelerator
// File          : tb_snn_top_hls.cpp
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : C++ testbench for SNN top-level with on-chip learning
//-----------------------------------------------------------------------------

#include <iostream>
#include <iomanip>
#include <cmath>
#include "../include/snn_top_hls.h"

// Test configuration
#define NUM_TEST_SPIKES 20
#define NUM_TIMESTEPS 100
#define VERBOSE 1

// Error counter
int error_count = 0;

//=============================================================================
// Helper Functions
//=============================================================================
void print_result(const char* test_name, bool passed) {
    std::cout << "  " << (passed ? "PASS" : "FAIL") << ": " << test_name << std::endl;
    if (!passed) error_count++;
}

axis_spike_t create_spike(neuron_id_t neuron_id, int8_t weight, uint16_t timestamp) {
    axis_spike_t pkt;
    pkt.data = 0;
    pkt.data(SPIKE_PKT_ID_HI, SPIKE_PKT_ID_LO) = neuron_id;
    pkt.data(SPIKE_PKT_WGT_HI, SPIKE_PKT_WGT_LO) = (ap_uint<8>)weight;
    pkt.data(SPIKE_PKT_TS_HI, SPIKE_PKT_TS_LO) =
        timestamp(SPIKE_PKT_TS_HI - SPIKE_PKT_TS_LO, 0);
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
    pkt.data(NEURON_ID_WIDTH - 1, 0) = pre_id;
    pkt.data(2 * NEURON_ID_WIDTH - 1, NEURON_ID_WIDTH) = post_id;
    pkt.data(2 * NEURON_ID_WIDTH + 7, 2 * NEURON_ID_WIDTH) = (ap_uint<8>)weight;
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
    ap_uint<1> spike_in_valid, spike_out_ready, snn_enable, snn_reset;
    neuron_id_t spike_in_neuron_id;
    ap_int<8> spike_in_weight;
    ap_uint<16> threshold_out, leak_rate_out;
    
    ap_uint<1> spike_in_ready = 1;
    ap_uint<1> spike_out_valid = 0;
    neuron_id_t spike_out_neuron_id = 0;
    ap_int<8> spike_out_weight = 0;
    ap_uint<1> snn_ready = 1;
    ap_uint<1> snn_busy = 0;
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
    
        snn_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                    status_reg, spike_count_reg,
                    weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                    m_axis_spikes,
                    m_axis_weights, reward_signal,
                spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                snn_enable, snn_reset, threshold_out, leak_rate_out,
                snn_ready, snn_busy);
    
    print_result("Reset signal routed", snn_reset == 1);
    print_result("Version register set", version_reg == VERSION_ID);
    print_result("Threshold routed", threshold_out == 51);
    print_result("Leak rate routed", leak_rate_out == 100);
    
    // Test enable
    ctrl_reg = 0x01;  // Enable bit
    
        snn_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                    status_reg, spike_count_reg,
                    weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                    m_axis_spikes,
                    m_axis_weights, reward_signal,
                spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                snn_enable, snn_reset, threshold_out, leak_rate_out,
                snn_ready, snn_busy);
    
    print_result("Enable signal routed", snn_enable == 1);
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
    
    ap_uint<1> spike_in_valid, spike_out_ready, snn_enable, snn_reset;
    neuron_id_t spike_in_neuron_id;
    ap_int<8> spike_in_weight;
    ap_uint<16> threshold_out, leak_rate_out;
    
    ap_uint<1> spike_in_ready = 1;
    ap_uint<1> spike_out_valid = 0;
    neuron_id_t spike_out_neuron_id = 0;
    ap_int<8> spike_out_weight = 0;
    ap_uint<1> snn_ready = 1;
    ap_uint<1> snn_busy = 0;
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
        snn_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes,
                m_axis_weights, reward_signal,
                    spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                    spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                snn_enable, snn_reset, threshold_out, leak_rate_out,
                    snn_ready, snn_busy);
        
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
    
    ap_uint<1> spike_in_valid, spike_out_ready, snn_enable, snn_reset;
    neuron_id_t spike_in_neuron_id;
    ap_int<8> spike_in_weight;
    ap_uint<16> threshold_out, leak_rate_out;
    
    ap_uint<1> spike_in_ready = 1;
    ap_uint<1> spike_out_valid = 0;
    neuron_id_t spike_out_neuron_id = 0;
    ap_int<8> spike_out_weight = 0;
    ap_uint<1> snn_ready = 1;
    ap_uint<1> snn_busy = 0;
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
        
        snn_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes,
                m_axis_weights, reward_signal,
                    spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                    spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                snn_enable, snn_reset, threshold_out, leak_rate_out,
                    snn_ready, snn_busy);
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
    
    ap_uint<1> spike_in_valid, spike_out_ready, snn_enable, snn_reset;
    neuron_id_t spike_in_neuron_id;
    ap_int<8> spike_in_weight;
    ap_uint<16> threshold_out, leak_rate_out;
    
    ap_uint<1> spike_in_ready = 1;
    ap_uint<1> spike_out_valid = 0;
    neuron_id_t spike_out_neuron_id = 0;
    ap_int<8> spike_out_weight = 0;
    ap_uint<1> snn_ready = 1;
    ap_uint<1> snn_busy = 0;
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
    snn_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes,
                m_axis_weights, reward_signal,
                spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                snn_enable, snn_reset, threshold_out, leak_rate_out,
                snn_ready, snn_busy);
    
    // Enable with learning
    ctrl_reg = 0x09;
    
    // Scenario: Pre-spike at t=5 from input neuron 0 (group 0),
    //           Post-spike at t=10 from hidden neuron 784 (group 1, first neuron)
    //           Connection 0: input(0-783) -> hidden(784-2831)
    // Should cause LTP on weight_memory[weight_index(0, 784)]
    s_axis_spikes.write(create_spike(0, 10, 5));
    
    for (int t = 0; t < 5; t++) {
        snn_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes,
                m_axis_weights, reward_signal,
                    spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                    spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                snn_enable, snn_reset, threshold_out, leak_rate_out,
                    snn_ready, snn_busy);
    }
    
    // Now simulate post-synaptic spike from hidden neuron 784
    for (int t = 5; t < 15; t++) {
        if (t == 10) {
            spike_out_valid = 1;
            spike_out_neuron_id = 784;  // First neuron in hidden group
            spike_out_weight = 20;
        } else {
            spike_out_valid = 0;
        }
        
        snn_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes,
                m_axis_weights, reward_signal,
                    spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                    spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                snn_enable, snn_reset, threshold_out, leak_rate_out,
                    snn_ready, snn_busy);
    }
    
    // Check learning status
    bool learning_active = status_reg[2];
    print_result("Learning enabled in status", learning_active);
    
    std::cout << "  Weight sum (sample): " << weight_sum_reg << std::endl;
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
    
    ap_uint<1> spike_in_valid, spike_out_ready, snn_enable, snn_reset;
    neuron_id_t spike_in_neuron_id;
    ap_int<8> spike_in_weight;
    ap_uint<16> threshold_out, leak_rate_out;
    
    ap_uint<1> spike_in_ready = 1;
    ap_uint<1> spike_out_valid = 0;
    neuron_id_t spike_out_neuron_id = 0;
    ap_int<8> spike_out_weight = 0;
    ap_uint<1> snn_ready = 1;
    ap_uint<1> snn_busy = 0;
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
    snn_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes,
                m_axis_weights, reward_signal,
                spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                snn_enable, snn_reset, threshold_out, leak_rate_out,
                snn_ready, snn_busy);
    
    // Run with R-STDP
    ctrl_reg = 0x29;  // Enable + Learning + Apply reward (bits 0, 3, 5)
    
    // Generate spike activity: pre-spike from input neuron 0, post from hidden 784
    s_axis_spikes.write(create_spike(0, 10, 0));
    
    for (int t = 0; t < 20; t++) {
        if (t == 5) {
            spike_out_valid = 1;
            spike_out_neuron_id = 784;  // First neuron in hidden group
            spike_out_weight = 20;
        } else {
            spike_out_valid = 0;
        }
        
        snn_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes,
                m_axis_weights, reward_signal,
                    spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                    spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                snn_enable, snn_reset, threshold_out, leak_rate_out,
                    snn_ready, snn_busy);
    }
    
    bool rstdp_enabled = status_reg[4];
    print_result("R-STDP enabled in status", rstdp_enabled);
    
    std::cout << "  Weight sum after R-STDP: " << weight_sum_reg << std::endl;
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

    ap_uint<1> spike_in_valid, spike_out_ready, snn_enable, snn_reset;
    neuron_id_t spike_in_neuron_id;
    ap_int<8> spike_in_weight;
    ap_uint<16> threshold_out, leak_rate_out;

    ap_uint<1> spike_in_ready = 1;
    ap_uint<1> spike_out_valid = 0;
    neuron_id_t spike_out_neuron_id = 0;
    ap_int<8> spike_out_weight = 0;
    ap_uint<1> snn_ready = 1;
    ap_uint<1> snn_busy = 0;
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
    snn_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes, m_axis_weights, reward_signal,
                spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                snn_enable, snn_reset, threshold_out, leak_rate_out,
                snn_ready, snn_busy);

    // Load two known weights:
    //   idx=0      : pre=0, post=784 -> +3
    //   idx=1024   : pre=1, post=784 -> -3
    ctrl_reg = 0x41;  // enable + weight_load_mode
    mode_reg = MODE_INFERENCE;
    s_axis_weights.write(create_weight_packet(0, 784, 3));
    s_axis_weights.write(create_weight_packet(1, 784, -3));
    for (int i = 0; i < 4; i++) {
        snn_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                    status_reg, spike_count_reg,
                    weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                    m_axis_spikes, m_axis_weights, reward_signal,
                    spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                    spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                    learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                    learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                    learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                    snn_enable, snn_reset, threshold_out, leak_rate_out,
                    snn_ready, snn_busy);
    }

    // Enter checkpoint mode and read back stream.
    ctrl_reg = 0x11;  // enable + weight_read_mode
    mode_reg = MODE_CHECKPOINT;

    bool found_idx0 = false;
    bool found_idx1024 = false;
    int8_t idx0_weight = 0;
    int8_t idx1024_weight = 0;
    int nonzero_payload_words = 0;
    int packets_seen = 0;

    for (int cyc = 0; cyc < 1200; cyc++) {
        snn_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                    status_reg, spike_count_reg,
                    weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                    m_axis_spikes, m_axis_weights, reward_signal,
                    spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                    spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                    learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                    learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                    learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                    snn_enable, snn_reset, threshold_out, leak_rate_out,
                    snn_ready, snn_busy);

        if (!m_axis_weights.empty()) {
            axis_weight_t pkt = m_axis_weights.read();
            packets_seen++;
            int idx = (int)pkt.data(19, 0);
            int8_t w = (int8_t)(ap_uint<8>)pkt.data(27, 20);
            if (w != 0) nonzero_payload_words++;

            if (idx == 0) {
                found_idx0 = true;
                idx0_weight = w;
            } else if (idx == 1024) {
                found_idx1024 = true;
                idx1024_weight = w;
            }
        }
    }

    print_result("Checkpoint stream produced packets", packets_seen > 0);
    print_result("Checkpoint payload has non-zero words", nonzero_payload_words > 0);
    print_result("Checkpoint idx=0 present", found_idx0);
    print_result("Checkpoint idx=0 weight matches loaded value", found_idx0 && idx0_weight == 3);
    print_result("Checkpoint idx=1024 present", found_idx1024);
    print_result("Checkpoint idx=1024 weight matches loaded value", found_idx1024 && idx1024_weight == -3);
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

    ap_uint<1> spike_in_valid, spike_out_ready, snn_enable, snn_reset;
    neuron_id_t spike_in_neuron_id;
    ap_int<8> spike_in_weight;
    ap_uint<16> threshold_out, leak_rate_out;

    ap_uint<1> spike_in_ready = 1;
    ap_uint<1> spike_out_valid = 0;
    neuron_id_t spike_out_neuron_id = 0;
    ap_int<8> spike_out_weight = 0;
    ap_uint<1> snn_ready = 1;
    ap_uint<1> snn_busy = 0;
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
    snn_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes, m_axis_weights, reward_signal,
                spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                snn_enable, snn_reset, threshold_out, leak_rate_out,
                snn_ready, snn_busy);

    // STDP mode: one pre spike + one post spike on (0 -> 784)
    ctrl_reg = 0x09;  // enable + learning_enable
    mode_reg = MODE_TRAIN_STDP;
    s_axis_spikes.write(create_spike(0, 10, 0));
    spike_out_valid = 0;
    snn_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes, m_axis_weights, reward_signal,
                spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                snn_enable, snn_reset, threshold_out, leak_rate_out,
                snn_ready, snn_busy);

    spike_out_valid = 1;
    spike_out_neuron_id = 784;
    spike_out_weight = 20;
    snn_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes, m_axis_weights, reward_signal,
                spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                snn_enable, snn_reset, threshold_out, leak_rate_out,
                snn_ready, snn_busy);

    // Drain one extra cycle
    spike_out_valid = 0;
    snn_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                status_reg, spike_count_reg,
                weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                m_axis_spikes, m_axis_weights, reward_signal,
                spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                snn_enable, snn_reset, threshold_out, leak_rate_out,
                snn_ready, snn_busy);

    bool stdp_weight_sum_nonzero = ((int)weight_sum_reg != 0);

    // Checkpoint capture
    ctrl_reg = 0x11;  // enable + weight_read_mode
    mode_reg = MODE_CHECKPOINT;
    bool found_idx0 = false;
    int8_t idx0_weight = 0;
    int nonzero_payload_words = 0;
    int packets_seen = 0;

    for (int cyc = 0; cyc < 2048; cyc++) {
        snn_top_hls(ctrl_reg, config_reg, mode_reg, time_steps_reg, params, encoder_cfg,
                    status_reg, spike_count_reg,
                    weight_sum_reg, version_reg, s_axis_spikes, s_axis_data, s_axis_weights,
                    m_axis_spikes, m_axis_weights, reward_signal,
                    spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
                    spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
                    learn_weight_valid, learn_weight_group, learn_weight_src, learn_weight_dst,
                    learn_weight_data, learn_weight_exc, learn_weight_is_inter,
                    learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready,
                    snn_enable, snn_reset, threshold_out, leak_rate_out,
                    snn_ready, snn_busy);

        if (!m_axis_weights.empty()) {
            axis_weight_t pkt = m_axis_weights.read();
            packets_seen++;
            int idx = (int)pkt.data(19, 0);
            int8_t w = (int8_t)(ap_uint<8>)pkt.data(27, 20);
            if (w != 0) nonzero_payload_words++;
            if (idx == 0) {
                found_idx0 = true;
                idx0_weight = w;
            }
        }
    }

    print_result("STDP run changed sampled weight sum", stdp_weight_sum_nonzero);
    print_result("Checkpoint stream produced packets after STDP", packets_seen > 0);
    print_result("Checkpoint payload has non-zero words after STDP", nonzero_payload_words > 0);
    print_result("Checkpoint idx=0 seen after STDP", found_idx0);
    print_result("Checkpoint idx=0 carries non-zero weight after STDP", found_idx0 && idx0_weight != 0);
}

//=============================================================================
// Main
//=============================================================================
int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "SNN Top-Level HLS Testbench" << std::endl;
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
