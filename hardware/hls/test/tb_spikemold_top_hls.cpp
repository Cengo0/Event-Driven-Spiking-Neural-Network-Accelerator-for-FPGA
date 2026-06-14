//-----------------------------------------------------------------------------
// Title         : SpikeMold Top-Level HLS Testbench
// Project       : PYNQ-Z2 SpikeMold
// File          : tb_spikemold_top_hls.cpp
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : C++ testbench for inference-only SpikeMold HLS top-level
//-----------------------------------------------------------------------------

#include <cstdint>
#include <iostream>
#include "../include/spikemold_top_hls.h"

static const neuron_id_t TEST_FIRST_PRE_ID = SNN_CONN_0_SRC_ID_START;
static const neuron_id_t TEST_SECOND_PRE_ID = SNN_CONN_0_SRC_ID_START + 2;
static const neuron_id_t TEST_POST_ID = SNN_CONN_0_DST_ID_START;
static const rtl_nid_t TEST_POST_RTL_ID = (rtl_nid_t)SNN_CONN_0_DST_ID_START;
static const int TEST_FIRST_WEIGHT_INDEX = 0;
static const int TEST_SECOND_WEIGHT_INDEX = 2 * SNN_CONN_0_DST_SIZE;

int error_count = 0;

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

encoder_config_t get_default_encoder_config() {
    encoder_config_t cfg;
    cfg.encoding_type = ENC_NONE;
    cfg.delta_threshold = 1024;
    cfg.delta_decay = 1;
    cfg.num_channels = 0;
    cfg.default_weight = 1;
    return cfg;
}

struct HlsHarness {
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
    ap_uint<32> status_reg = 0;
    ap_uint<32> spike_count_reg = 0;
    ap_uint<32> weight_sum_reg = 0;
    ap_uint<32> version_reg = 0;

    ap_uint<1> spike_in_valid = 0;
    rtl_nid_t spike_in_neuron_id = 0;
    ap_int<8> spike_in_weight = 0;
    ap_uint<1> spike_in_ready = 1;

    ap_uint<1> spike_out_valid = 0;
    rtl_nid_t spike_out_neuron_id = 0;
    ap_int<8> spike_out_weight = 0;
    ap_uint<1> spike_out_ready = 0;

    ap_uint<1> spikemold_enable = 0;
    ap_uint<1> spikemold_reset = 0;
    ap_uint<16> threshold_out = 0;
    ap_uint<16> leak_rate_out = 0;
    ap_uint<1> spikemold_ready = 1;
    ap_uint<1> spikemold_busy = 0;

    void call() {
        spikemold_top_hls(
            ctrl_reg, config_reg, mode_reg, time_steps_reg, encoder_cfg,
            status_reg, spike_count_reg, weight_sum_reg, version_reg,
            s_axis_spikes, s_axis_data, s_axis_weights,
            m_axis_spikes, m_axis_weights,
            spike_in_valid, spike_in_neuron_id, spike_in_weight, spike_in_ready,
            spike_out_valid, spike_out_neuron_id, spike_out_weight, spike_out_ready,
            spikemold_enable, spikemold_reset, threshold_out, leak_rate_out,
            spikemold_ready, spikemold_busy
        );
    }
};

void reset_hls(HlsHarness &h) {
    h.ctrl_reg = 0x02;
    h.mode_reg = MODE_INFERENCE;
    h.time_steps_reg = 1;
    h.call();
    h.ctrl_reg = 0;
    h.call();
}

void test_control_registers() {
    std::cout << "\n=== Test 1: Control Registers ===" << std::endl;
    HlsHarness h;
    reset_hls(h);

    h.ctrl_reg = 0x01;
    h.config_reg = (100 << 16) | 51;
    h.call();

    print_result("Version register matches", h.version_reg == VERSION_ID);
    print_result("SpikeMold enable routed", h.spikemold_enable == 1);
    print_result("SpikeMold reset deasserted", h.spikemold_reset == 0);
    print_result("Threshold output matches", h.threshold_out == 51);
    print_result("Leak output matches", h.leak_rate_out == 100);
    print_result("Status ready bit mirrors core", h.status_reg[0] == 1);
    print_result("Reserved status bit is zero", h.status_reg[2] == 0);
}

void test_spike_input() {
    std::cout << "\n=== Test 2: Spike Input ===" << std::endl;
    HlsHarness h;
    reset_hls(h);

    h.ctrl_reg = 0x01;
    h.s_axis_spikes.write(create_spike(TEST_FIRST_PRE_ID, 12, 3));
    h.call();

    print_result("Input spike valid asserted", h.spike_in_valid == 1);
    print_result("Input spike neuron ID routed", h.spike_in_neuron_id == (rtl_nid_t)TEST_FIRST_PRE_ID);
    print_result("Input spike weight routed", h.spike_in_weight == 12);
    print_result("Spike count incremented", h.spike_count_reg == 1);
}

void test_spike_output() {
    std::cout << "\n=== Test 3: Spike Output ===" << std::endl;
    HlsHarness h;
    reset_hls(h);

    h.ctrl_reg = 0x01;
    h.spike_out_valid = 1;
    h.spike_out_neuron_id = TEST_POST_RTL_ID;
    h.spike_out_weight = 21;
    h.call();

    bool saw_packet = !h.m_axis_spikes.empty();
    bool id_ok = false;
    bool weight_ok = false;
    if (saw_packet) {
        axis_spike_t pkt = h.m_axis_spikes.read();
        id_ok = (pkt.data(SPIKE_PKT_ID_HI, SPIKE_PKT_ID_LO) == TEST_POST_ID);
        weight_ok = ((ap_int<8>)(ap_uint<8>)pkt.data(SPIKE_PKT_WGT_HI, SPIKE_PKT_WGT_LO) == 21);
    }

    print_result("Output packet emitted", saw_packet);
    print_result("Output packet neuron ID matches", id_ok);
    print_result("Output packet weight matches", weight_ok);
    print_result("Output ready toggled", h.spike_out_ready == 1);
}

void test_checkpoint_stream_payload() {
    std::cout << "\n=== Test 4: Checkpoint Stream Payload ===" << std::endl;
    HlsHarness h;
    reset_hls(h);

    h.ctrl_reg = 0x40;
    h.s_axis_weights.write(create_weight_packet(TEST_FIRST_PRE_ID, TEST_POST_ID, 5));
    h.call();
    h.s_axis_weights.write(create_weight_packet(TEST_SECOND_PRE_ID, TEST_POST_ID, -3));
    h.call();

    h.ctrl_reg = 0x11;
    h.mode_reg = MODE_CHECKPOINT;
    bool found_first_weight = false;
    bool found_second_weight = false;
    int8_t first_weight_value = 0;
    int8_t second_weight_value = 0;
    int packets_seen = 0;

    for (int cyc = 0; cyc < 4096; cyc++) {
        h.call();
        if (!h.m_axis_weights.empty()) {
            axis_weight_t pkt = h.m_axis_weights.read();
            packets_seen++;
            int idx = (int)pkt.data(19, 0);
            int8_t weight = (int8_t)(ap_uint<8>)pkt.data(27, 20);
            if (idx == TEST_FIRST_WEIGHT_INDEX) {
                found_first_weight = true;
                first_weight_value = weight;
            }
            if (idx == TEST_SECOND_WEIGHT_INDEX) {
                found_second_weight = true;
                second_weight_value = weight;
            }
        }
    }

    print_result("Checkpoint stream produced packets", packets_seen > 0);
    print_result("Checkpoint first loaded weight matches", found_first_weight && first_weight_value == 5);
    print_result("Checkpoint second loaded weight matches", found_second_weight && second_weight_value == -3);
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "SpikeMold Top-Level HLS Testbench" << std::endl;
    std::cout << "Inference Test Suite" << std::endl;
    std::cout << "========================================" << std::endl;

    test_control_registers();
    test_spike_input();
    test_spike_output();
    test_checkpoint_stream_payload();

    std::cout << "\n========================================" << std::endl;
    if (error_count == 0) {
        std::cout << "All tests PASSED!" << std::endl;
    } else {
        std::cout << "Tests completed with " << error_count << " errors" << std::endl;
    }
    std::cout << "========================================" << std::endl;

    return error_count;
}
