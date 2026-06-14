`timescale 1ns / 1ps
//------------------------------------------------------------------------------
// EventWord64 decoder for SpikeMold-EDNP transport smoke.
//
// Layout from contracts/EVENT_FORMAT_V1.md:
// [63:60] event_type
// [59:48] tick_low12
// [47:38] src_y_or_src_hi10
// [37:28] src_x_or_src_lo10
// [27:20] channel_or_dst_hi8
// [19]    sign
// [18:11] weight_abs_or_payload8
// [10:5]  flags6
// [4:0]   target_or_reserved5
//------------------------------------------------------------------------------

module event_word64_decode (
    input  wire [63:0] event_word,
    output wire [3:0]  event_type,
    output wire [11:0] timestamp_delta,
    output wire [9:0]  x,
    output wire [9:0]  y,
    output wire [7:0]  channel,
    output wire        payload_sign,
    output wire [7:0]  payload_u8,
    output wire signed [7:0] payload_s8,
    output wire [5:0]  layer_id,
    output wire [4:0]  tile_id,
    output wire        event_type_supported,
    output wire        is_sensor_event,
    output wire        is_neuron_event,
    output wire        payload_negative,
    output wire [63:0] repacked_word
);

    assign event_type      = event_word[63:60];
    assign timestamp_delta = event_word[59:48];
    assign x               = event_word[47:38];
    assign y               = event_word[37:28];
    assign channel         = event_word[27:20];
    assign payload_sign    = event_word[19];
    assign payload_u8      = event_word[18:11];
    assign layer_id        = event_word[10:5];
    assign tile_id         = event_word[4:0];

    assign payload_negative = (payload_sign == 1'b1) && (payload_u8 != 8'd0);
    assign payload_s8 = payload_negative ? -$signed({1'b0, payload_u8}) : $signed({1'b0, payload_u8});

    assign is_sensor_event = (event_type == 4'd0);
    assign is_neuron_event = (event_type == 4'd1) || (event_type == 4'd2) || (event_type == 4'd3);
    assign event_type_supported = is_sensor_event || is_neuron_event;

    assign repacked_word = {
        event_type,
        timestamp_delta,
        x,
        y,
        channel,
        payload_sign,
        payload_u8,
        layer_id,
        tile_id
    };

endmodule
