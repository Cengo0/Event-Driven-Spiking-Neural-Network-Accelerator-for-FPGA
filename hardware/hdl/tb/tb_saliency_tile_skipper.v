`timescale 1ns / 1ps

module tb_saliency_tile_skipper;
    reg clk = 1'b0;
    always #6.25 clk = ~clk;

    reg rst_n;
    reg enable;
    reg cfg_clear;
    reg [3:0] cfg_tile_x_shift;
    reg [3:0] cfg_tile_y_shift;
    reg [7:0] cfg_tiles_x;
    reg [7:0] cfg_threshold;
    reg cfg_drop_oob_tiles;
    reg s_event_valid;
    reg [63:0] s_event_word;
    wire s_event_ready;
    wire m_event_valid;
    wire [63:0] m_event_word;
    wire [7:0] m_tile_index;
    wire [7:0] m_activity_count;
    wire [7:0] m_previous_count;
    wire m_skip;
    wire m_saturated;
    reg m_event_ready;
    wire [31:0] input_event_count;
    wire [31:0] update_count;
    wire [31:0] skipped_tile_count;
    wire [31:0] active_tile_count;
    wire [31:0] saturated_update_count;
    wire [31:0] dropped_oob_tile_count;
    wire [31:0] clear_count;

    integer pass_count = 0;
    integer fail_count = 0;

    saliency_tile_skipper dut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .cfg_clear(cfg_clear),
        .cfg_tile_x_shift(cfg_tile_x_shift),
        .cfg_tile_y_shift(cfg_tile_y_shift),
        .cfg_tiles_x(cfg_tiles_x),
        .cfg_threshold(cfg_threshold),
        .cfg_drop_oob_tiles(cfg_drop_oob_tiles),
        .s_event_valid(s_event_valid),
        .s_event_word(s_event_word),
        .s_event_ready(s_event_ready),
        .m_event_valid(m_event_valid),
        .m_event_word(m_event_word),
        .m_tile_index(m_tile_index),
        .m_activity_count(m_activity_count),
        .m_previous_count(m_previous_count),
        .m_skip(m_skip),
        .m_saturated(m_saturated),
        .m_event_ready(m_event_ready),
        .input_event_count(input_event_count),
        .update_count(update_count),
        .skipped_tile_count(skipped_tile_count),
        .active_tile_count(active_tile_count),
        .saturated_update_count(saturated_update_count),
        .dropped_oob_tile_count(dropped_oob_tile_count),
        .clear_count(clear_count)
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
        input [3:0] event_type;
        input [11:0] timestamp_delta;
        input [9:0] x;
        input [9:0] y;
        input [7:0] channel;
        input polarity;
        input [7:0] payload_u8;
        input [5:0] layer_id;
        input [4:0] tile_id;
        begin
            make_event = 64'd0;
            make_event[63:60] = event_type;
            make_event[59:48] = timestamp_delta;
            make_event[47:38] = x;
            make_event[37:28] = y;
            make_event[27:20] = channel;
            make_event[19] = polarity;
            make_event[18:11] = payload_u8;
            make_event[10:5] = layer_id;
            make_event[4:0] = tile_id;
        end
    endfunction

    task automatic drive_event;
        input [63:0] word;
        begin
            @(negedge clk);
            s_event_word = word;
            s_event_valid = 1'b1;
            #1;
            check("saliency skipper accepts event when output slot available", s_event_ready == 1'b1);
            @(posedge clk);
            #1;
            @(negedge clk);
            s_event_valid = 1'b0;
        end
    endtask

    task automatic drain_output;
        begin
            @(posedge clk);
            #1;
        end
    endtask

    initial begin
        rst_n = 1'b0;
        enable = 1'b1;
        cfg_clear = 1'b0;
        cfg_tile_x_shift = 4'd1;
        cfg_tile_y_shift = 4'd1;
        cfg_tiles_x = 8'd4;
        cfg_threshold = 8'd2;
        cfg_drop_oob_tiles = 1'b1;
        s_event_valid = 1'b0;
        s_event_word = 64'd0;
        m_event_ready = 1'b1;

        repeat (3) @(posedge clk);
        @(negedge clk);
        rst_n = 1'b1;
        @(posedge clk);
        #1;

        check("reset clears saliency output", m_event_valid == 1'b0);
        check("reset clears saliency counters", input_event_count == 32'd0 && update_count == 32'd0);

        drive_event(make_event(4'd0, 12'd1, 10'd4, 10'd6, 8'd1, 1'b1, 8'd2, 6'd0, 5'd0));
        check("first saliency update emits metadata", m_event_valid == 1'b1);
        check("saliency output preserves event word", m_event_word == make_event(4'd0, 12'd1, 10'd4, 10'd6, 8'd1, 1'b1, 8'd2, 6'd0, 5'd0));
        check("saliency tile index matches shift mapping", m_tile_index == 8'd14);
        check("first saliency update count is one", m_previous_count == 8'd0 && m_activity_count == 8'd1);
        check("first saliency update is skipped under threshold", m_skip == 1'b1);
        check("first saliency update creates one active tile", active_tile_count == 32'd1);
        drain_output();

        drive_event(make_event(4'd0, 12'd2, 10'd5, 10'd7, 8'd1, 1'b1, 8'd3, 6'd0, 5'd0));
        check("second same-tile update reaches threshold", m_previous_count == 8'd1 && m_activity_count == 8'd2);
        check("second same-tile update is not skipped", m_skip == 1'b0);
        check("same-tile update preserves active tile count", active_tile_count == 32'd1);
        check("skip counter records only first below-threshold update", skipped_tile_count == 32'd1);
        drain_output();

        drive_event(make_event(4'd0, 12'd3, 10'd0, 10'd128, 8'd1, 1'b1, 8'd1, 6'd0, 5'd0));
        check("OOB saliency tile is dropped", m_event_valid == 1'b0 && dropped_oob_tile_count == 32'd1);
        check("OOB saliency tile does not update count", update_count == 32'd2);

        @(negedge clk);
        cfg_threshold = 8'd255;
        cfg_drop_oob_tiles = 1'b0;
        drive_event(make_event(4'd0, 12'd4, 10'd0, 10'd128, 8'd1, 1'b1, 8'd1, 6'd0, 5'd0));
        check("explicit OOB pass aliases bounded tile index", m_event_valid == 1'b1 && m_tile_index == 8'd0);
        check("new passed OOB tile increments active count", active_tile_count == 32'd2);
        drain_output();

        @(negedge clk);
        cfg_threshold = 8'd1;
        drive_event(make_event(4'd0, 12'd5, 10'd4, 10'd6, 8'd1, 1'b1, 8'd1, 6'd0, 5'd0));
        check("saliency update does not skip when threshold is one", m_skip == 1'b0);
        drain_output();

        @(negedge clk);
        m_event_ready = 1'b0;
        drive_event(make_event(4'd0, 12'd6, 10'd8, 10'd0, 8'd1, 1'b1, 8'd1, 6'd0, 5'd0));
        check("saliency output holds under backpressure", m_event_valid == 1'b1 && m_tile_index == 8'd4);
        @(posedge clk);
        #1;
        check("saliency source is backpressured by held output", s_event_ready == 1'b0);
        @(negedge clk);
        m_event_ready = 1'b1;
        drain_output();

        @(negedge clk);
        cfg_clear = 1'b1;
        @(posedge clk);
        #1;
        check("saliency clear removes active tiles", active_tile_count == 32'd0);
        check("saliency clear suppresses output", m_event_valid == 1'b0);
        check("saliency clear counter increments", clear_count == 32'd1);
        @(negedge clk);
        cfg_clear = 1'b0;

        @(negedge clk);
        enable = 1'b0;
        s_event_valid = 1'b1;
        #1;
        check("disabled saliency skipper deasserts input ready", s_event_ready == 1'b0);
        s_event_valid = 1'b0;

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
