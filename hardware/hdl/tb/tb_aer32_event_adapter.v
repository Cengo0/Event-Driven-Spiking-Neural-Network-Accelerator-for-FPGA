`timescale 1ns / 1ps

module tb_aer32_event_adapter;
    reg [31:0] aer_word;
    reg [11:0] timestamp_delta;
    reg signed [7:0] cfg_positive_payload;
    reg signed [7:0] cfg_negative_payload;
    reg [5:0] cfg_layer_id;
    reg [4:0] cfg_tile_id;
    reg cfg_invert_polarity;

    wire [9:0] x;
    wire [9:0] y;
    wire [7:0] channel;
    wire raw_polarity;
    wire polarity;
    wire signed [7:0] payload;
    wire [2:0] flags;
    wire [63:0] event_word;

    integer pass_count = 0;
    integer fail_count = 0;

    aer32_event_adapter dut (
        .aer_word(aer_word),
        .timestamp_delta(timestamp_delta),
        .cfg_positive_payload(cfg_positive_payload),
        .cfg_negative_payload(cfg_negative_payload),
        .cfg_layer_id(cfg_layer_id),
        .cfg_tile_id(cfg_tile_id),
        .cfg_invert_polarity(cfg_invert_polarity),
        .x(x),
        .y(y),
        .channel(channel),
        .raw_polarity(raw_polarity),
        .polarity(polarity),
        .payload(payload),
        .flags(flags),
        .event_word(event_word)
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

    function [31:0] make_aer32;
        input [9:0] x_in;
        input [9:0] y_in;
        input [7:0] channel_in;
        input polarity_in;
        input [2:0] flags_in;
        begin
            make_aer32 = {
                x_in,
                y_in,
                channel_in,
                polarity_in,
                flags_in
            };
        end
    endfunction

    function [63:0] make_event;
        input [11:0] timestamp_in;
        input [9:0] x_in;
        input [9:0] y_in;
        input [7:0] channel_in;
        input polarity_in;
        input [7:0] payload_in;
        input [5:0] layer_in;
        input [4:0] tile_in;
        begin
            make_event = {
                4'd0,
                timestamp_in,
                x_in,
                y_in,
                channel_in,
                polarity_in,
                payload_in,
                layer_in,
                tile_in
            };
        end
    endfunction

    initial begin
        timestamp_delta = 12'd11;
        cfg_positive_payload = 8'sd7;
        cfg_negative_payload = -8'sd3;
        cfg_layer_id = 6'd6;
        cfg_tile_id = 5'd12;
        cfg_invert_polarity = 1'b0;
        aer_word = make_aer32(10'd511, 10'd17, 8'd9, 1'b1, 3'd5);
        #1;
        check("AER32 adapter decodes x/y/channel", x == 10'd511 && y == 10'd17 && channel == 8'd9);
        check("AER32 adapter exposes raw polarity and flags", raw_polarity == 1'b1 && flags == 3'd5);
        check("AER32 adapter maps positive polarity payload", polarity == 1'b1 && payload == 8'sd7);
        check("AER32 adapter packs EventWord64 positive event", event_word == make_event(12'd11, 10'd511, 10'd17, 8'd9, 1'b1, 8'd7, 6'd6, 5'd12));

        timestamp_delta = 12'd12;
        aer_word = make_aer32(10'd4, 10'd1023, 8'd2, 1'b0, 3'd0);
        #1;
        check("AER32 adapter maps negative polarity payload", polarity == 1'b0 && payload == -8'sd3);
        check("AER32 adapter packs EventWord64 negative event", event_word == make_event(12'd12, 10'd4, 10'd1023, 8'd2, 1'b0, 8'hFD, 6'd6, 5'd12));

        cfg_invert_polarity = 1'b1;
        timestamp_delta = 12'd4;
        aer_word = make_aer32(10'd1, 10'd2, 8'd3, 1'b1, 3'd0);
        #1;
        check("AER32 adapter supports polarity inversion", raw_polarity == 1'b1 && polarity == 1'b0 && payload == -8'sd3);
        check("AER32 adapter inverted event uses negative payload", event_word == make_event(12'd4, 10'd1, 10'd2, 8'd3, 1'b0, 8'hFD, 6'd6, 5'd12));

        cfg_invert_polarity = 1'b0;
        timestamp_delta = 12'hFFF;
        cfg_positive_payload = 8'sd127;
        cfg_negative_payload = -8'sd128;
        cfg_layer_id = 6'd63;
        cfg_tile_id = 5'd31;
        aer_word = make_aer32(10'd1023, 10'd1023, 8'd255, 1'b0, 3'd7);
        #1;
        check("AER32 adapter preserves max coordinate fields", x == 10'd1023 && y == 10'd1023 && channel == 8'd255);
        check("AER32 adapter preserves signed int8 boundary", payload == -8'sd128);
        check("AER32 adapter packs sideband boundaries", event_word == make_event(12'hFFF, 10'd1023, 10'd1023, 8'd255, 1'b0, 8'h80, 6'd63, 5'd31));

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
