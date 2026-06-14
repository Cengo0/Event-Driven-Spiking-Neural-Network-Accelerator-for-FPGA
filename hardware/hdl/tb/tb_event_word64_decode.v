`timescale 1ns / 1ps

module tb_event_word64_decode;
    reg [63:0] event_word;
    wire [3:0] event_type;
    wire [11:0] timestamp_delta;
    wire [9:0] x;
    wire [9:0] y;
    wire [7:0] channel;
    wire payload_sign;
    wire [7:0] payload_u8;
    wire signed [7:0] payload_s8;
    wire [5:0] layer_id;
    wire [4:0] tile_id;
    wire event_type_supported;
    wire is_sensor_event;
    wire is_neuron_event;
    wire payload_negative;
    wire [63:0] repacked_word;

    integer pass_count = 0;
    integer fail_count = 0;

    event_word64_decode dut (
        .event_word(event_word),
        .event_type(event_type),
        .timestamp_delta(timestamp_delta),
        .x(x),
        .y(y),
        .channel(channel),
        .payload_sign(payload_sign),
        .payload_u8(payload_u8),
        .payload_s8(payload_s8),
        .layer_id(layer_id),
        .tile_id(tile_id),
        .event_type_supported(event_type_supported),
        .is_sensor_event(is_sensor_event),
        .is_neuron_event(is_neuron_event),
        .payload_negative(payload_negative),
        .repacked_word(repacked_word)
    );

    task automatic check;
        input [511:0] desc;
        input cond;
        begin
            if (cond) begin
                pass_count = pass_count + 1;
                $display("[PASS] %0s", desc);
            end else begin
                fail_count = fail_count + 1;
                $display("[FAIL] %0s", desc);
            end
        end
    endtask

    function [63:0] make_event;
        input [3:0] event_type_in;
        input [11:0] timestamp_in;
        input [9:0] x_in;
        input [9:0] y_in;
        input [7:0] channel_in;
        input payload_sign_in;
        input [7:0] payload_in;
        input [5:0] layer_in;
        input [4:0] tile_in;
        begin
            make_event = {
                event_type_in,
                timestamp_in,
                x_in,
                y_in,
                channel_in,
                payload_sign_in,
                payload_in,
                layer_in,
                tile_in
            };
        end
    endfunction

    initial begin
        event_word = make_event(4'd0, 12'hABC, 10'd346, 10'd260, 8'd17, 1'b1, 8'd5, 6'd12, 5'd19);
        #1;
        check("decode event type", event_type == 4'd0);
        check("decode timestamp delta", timestamp_delta == 12'hABC);
        check("decode x coordinate", x == 10'd346);
        check("decode y coordinate", y == 10'd260);
        check("decode channel", channel == 8'd17);
        check("decode payload sign", payload_sign == 1'b1);
        check("decode payload byte", payload_u8 == 8'd5);
        check("decode signed payload", payload_s8 == -8'sd5);
        check("decode layer/tile", layer_id == 6'd12 && tile_id == 5'd19);
        check("sensor type predicate", is_sensor_event == 1'b1 && is_neuron_event == 1'b0);
        check("supported type predicate", event_type_supported == 1'b1);
        check("negative payload predicate", payload_negative == 1'b1);
        check("repack preserves word bit-for-bit", repacked_word == event_word);

        event_word = make_event(4'd1, 12'd7, 10'd1, 10'd2, 8'd3, 1'b0, 8'd9, 6'd4, 5'd5);
        #1;
        check("neuron type predicate", is_neuron_event == 1'b1 && is_sensor_event == 1'b0);
        check("positive payload predicate", payload_negative == 1'b0 && payload_s8 == 8'sd9);
        check("second repack preserves word", repacked_word == event_word);

        event_word = make_event(4'd15, 12'd0, 10'd0, 10'd0, 8'd0, 1'b0, 8'd0, 6'd0, 5'd0);
        #1;
        check("unsupported type predicate rejects custom 15", event_type_supported == 1'b0);
        check("unsupported type still repacks bit-for-bit", repacked_word == event_word);

        $display("Results: %0d PASS, %0d FAIL", pass_count, fail_count);
        if (fail_count == 0) begin
            $display("*** ALL TESTS PASSED ***");
        end else begin
            $display("*** SOME TESTS FAILED ***");
            $fatal(1);
        end
        $finish;
    end

endmodule
