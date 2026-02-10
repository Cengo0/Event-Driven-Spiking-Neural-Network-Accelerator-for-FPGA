//-----------------------------------------------------------------------------
// Title         : Common SNN Data Types
// Project       : PYNQ-Z2 SNN Accelerator
// File          : snn_types.h
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : Common type definitions for SNN HLS modules
//-----------------------------------------------------------------------------

#ifndef SNN_TYPES_H
#define SNN_TYPES_H

#include <ap_int.h>
#include <ap_fixed.h>
#include <hls_stream.h>

// System parameters
const int MAX_NEURONS = 256;              // Expanded neuron count
const int MAX_SYNAPSES = 65536;           // 256x256
const int MAX_INPUT_CHANNELS = 784;       // 28x28 MNIST default (matches snn_top_hls.h)
const int MAX_OUTPUT_NEURONS = 64;        // More output classes

// Basic data types - unified with snn_top_hls.h
typedef ap_uint<10> neuron_id_t;           // 10-bit: supports up to 1024 encoded channels
typedef ap_uint<8> axon_id_t;
typedef ap_uint<32> spike_time_t;
typedef ap_int<8> weight_t;
typedef ap_int<16> weight_delta_t;
typedef ap_uint<8> pixel_t;
typedef ap_uint<16> membrane_t;

// Fixed-point types for learning
typedef ap_fixed<16,8> learning_rate_t;
typedef ap_fixed<16,8> decay_rate_t;

// Constants
const weight_t MAX_WEIGHT = 127;
const weight_t MIN_WEIGHT = -128;
const weight_delta_t MAX_WEIGHT_DELTA = 127;
const int WEIGHT_SCALE = 128;

// Spike event structure
struct spike_event_t {
    neuron_id_t neuron_id;
    spike_time_t timestamp;
    weight_t weight;
};

// Weight update structure
// Note: snn_top_hls.h has its own weight_update_t; use #ifndef guard
#ifndef SNN_TOP_HLS_H
struct weight_update_t {
    neuron_id_t pre_id;
    neuron_id_t post_id;
    weight_delta_t delta;
    spike_time_t timestamp;
};
#endif

// Input data structure (e.g., for image processing)
// Note: snn_top_hls.h has its own input_data_t; use #ifndef guard
#ifndef SNN_TOP_HLS_H
struct input_data_t {
    pixel_t pixels[MAX_INPUT_CHANNELS];
    ap_uint<16> label;  // For supervised learning
    ap_uint<32> frame_id;
};
#endif

// Output data structure
struct output_data_t {
    ap_uint<8> class_id;
    ap_uint<8> confidence;
    ap_uint<16> values[MAX_OUTPUT_NEURONS];
    ap_uint<32> frame_id;
};

// Control packet for inter-module communication
struct control_packet_t {
    ap_uint<8> command;
    ap_uint<16> param1;
    ap_uint<16> param2;
    spike_time_t timestamp;
};

// Encoding types
enum encoding_type_t {
    RATE_CODING = 0,
    TEMPORAL_CODING = 1,
    PHASE_CODING = 2,
    BURST_CODING = 3
};

// Decoding types
enum decoding_type_t {
    SPIKE_COUNT = 0,
    SPIKE_RATE = 1,
    FIRST_SPIKE = 2,
    POPULATION_VECTOR = 3
};

// Network modes
enum network_mode_t {
    MODE_IDLE = 0,
    MODE_TRAINING = 1,
    MODE_INFERENCE = 2,
    MODE_VALIDATION = 3
};

// Control commands
enum control_command_t {
    CTRL_RESET = 0,
    CTRL_ENABLE = 1,
    CTRL_DISABLE = 2,
    CTRL_CONFIGURE = 3,
    CTRL_FLUSH = 4
};

#endif // SNN_TYPES_H
