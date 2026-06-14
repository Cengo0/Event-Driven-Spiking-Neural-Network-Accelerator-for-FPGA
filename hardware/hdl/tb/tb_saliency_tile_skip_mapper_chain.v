`timescale 1ns / 1ps

module tb_saliency_tile_skip_mapper_chain;
    reg clk = 1'b0;
    always #6.25 clk = ~clk;

    reg rst_n;
    reg enable;
    reg cfg_clear;
    reg s_event_valid;
    reg [63:0] s_event_word;
    wire s_event_ready;

    wire saliency_event_valid;
    wire [63:0] saliency_event_word;
    wire [7:0] saliency_tile_index;
    wire [7:0] saliency_activity_count;
    wire [7:0] saliency_previous_count;
    wire saliency_skip;
    wire saliency_saturated;
    wire saliency_event_ready;
    wire [31:0] saliency_input_event_count;
    wire [31:0] saliency_update_count;
    wire [31:0] saliency_skipped_tile_count;
    wire [31:0] saliency_active_tile_count;
    wire [31:0] saliency_saturated_update_count;
    wire [31:0] saliency_dropped_oob_tile_count;
    wire [31:0] saliency_clear_count;

    wire mapper_s_event_valid;
    wire mapper_s_event_ready;
    wire mapper_event_valid;
    wire [63:0] mapper_event_word;
    wire [10:0] mapper_global_id;
    wire [3:0] mapper_group_id;
    wire [6:0] mapper_local_id;
    wire [7:0] mapper_weight;
    wire mapper_exc;
    reg mapper_event_ready;
    wire [31:0] mapper_mapped_event_count;
    wire [31:0] mapper_dropped_oob_tile_count;

    integer pass_count = 0;
    integer fail_count = 0;

    assign mapper_s_event_valid = saliency_event_valid && !saliency_skip;
    assign saliency_event_ready = saliency_skip || mapper_s_event_ready;

    saliency_tile_skipper #(
        .TILE_COUNT(16),
        .TILE_INDEX_WIDTH(8),
        .COUNTER_WIDTH(8)
    ) saliency_i (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .cfg_clear(cfg_clear),
        .cfg_tile_x_shift(4'd1),
        .cfg_tile_y_shift(4'd1),
        .cfg_tiles_x(8'd4),
        .cfg_threshold(8'd2),
        .cfg_drop_oob_tiles(1'b1),
        .s_event_valid(s_event_valid),
        .s_event_word(s_event_word),
        .s_event_ready(s_event_ready),
        .m_event_valid(saliency_event_valid),
        .m_event_word(saliency_event_word),
        .m_tile_index(saliency_tile_index),
        .m_activity_count(saliency_activity_count),
        .m_previous_count(saliency_previous_count),
        .m_skip(saliency_skip),
        .m_saturated(saliency_saturated),
        .m_event_ready(saliency_event_ready),
        .input_event_count(saliency_input_event_count),
        .update_count(saliency_update_count),
        .skipped_tile_count(saliency_skipped_tile_count),
        .active_tile_count(saliency_active_tile_count),
        .saturated_update_count(saliency_saturated_update_count),
        .dropped_oob_tile_count(saliency_dropped_oob_tile_count),
        .clear_count(saliency_clear_count)
    );

    event_to_tile_mapper mapper_i (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .s_event_valid(mapper_s_event_valid),
        .s_event_word(saliency_event_word),
        .s_event_ready(mapper_s_event_ready),
        .m_event_valid(mapper_event_valid),
        .m_event_word(mapper_event_word),
        .m_global_id(mapper_global_id),
        .m_group_id(mapper_group_id),
        .m_local_id(mapper_local_id),
        .m_weight(mapper_weight),
        .m_exc(mapper_exc),
        .m_event_ready(mapper_event_ready),
        .cfg_tile_x_shift(4'd1),
        .cfg_tile_y_shift(4'd1),
        .cfg_tiles_x(6'd4),
        .cfg_local_x_mask(7'h7f),
        .cfg_local_y_shift(3'd4),
        .cfg_drop_oob_tiles(1'b1),
        .mapped_event_count(mapper_mapped_event_count),
        .dropped_oob_tile_count(mapper_dropped_oob_tile_count)
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
            check("saliency-mapper chain accepts event when ingress is ready", s_event_ready == 1'b1);
            @(posedge clk);
            #1;
            @(negedge clk);
            s_event_valid = 1'b0;
        end
    endtask

    initial begin
        rst_n = 1'b0;
        enable = 1'b1;
        cfg_clear = 1'b0;
        s_event_valid = 1'b0;
        s_event_word = 64'd0;
        mapper_event_ready = 1'b1;

        repeat (3) @(posedge clk);
        @(negedge clk);
        rst_n = 1'b1;
        @(posedge clk);
        #1;

        check("saliency-mapper chain reset clears outputs", saliency_event_valid == 1'b0 && mapper_event_valid == 1'b0);
        check("saliency-mapper chain reset clears counters", saliency_input_event_count == 32'd0 && mapper_mapped_event_count == 32'd0);

        drive_event(make_event(4'd0, 12'd1, 10'd4, 10'd6, 8'd1, 1'b1, 8'd2, 6'd0, 5'd0));
        #1;
        check("first saliency chain update is below-threshold skip", saliency_event_valid == 1'b1 && saliency_skip == 1'b1);
        check("skipped saliency event is not sent to mapper", mapper_event_valid == 1'b0 && mapper_mapped_event_count == 32'd0);
        @(posedge clk);
        #1;
        check("skip metadata is consumed without mapper output", saliency_event_valid == 1'b0 && mapper_event_valid == 1'b0);

        drive_event(make_event(4'd0, 12'd2, 10'd5, 10'd7, 8'd1, 1'b1, 8'd3, 6'd0, 5'd0));
        @(posedge clk);
        #1;
        check("second saliency chain update reaches threshold", saliency_activity_count == 8'd2 && saliency_skip == 1'b0);
        check("non-skip saliency event maps to coregroup", mapper_event_valid == 1'b1 && mapper_group_id == 4'd14);
        check("non-skip saliency event derives local/global ID", mapper_local_id == 7'd117 && mapper_global_id == 11'd1909);
        check("non-skip saliency event preserves payload sign sideband", mapper_weight == 8'd3 && mapper_exc == 1'b1 && mapper_event_word[4:0] == 5'd14);
        check("saliency and mapper counters record one mapped event", saliency_update_count == 32'd2 && mapper_mapped_event_count == 32'd1);
        @(posedge clk);
        #1;
        check("mapped event drains when downstream ready", mapper_event_valid == 1'b0);

        drive_event(make_event(4'd0, 12'd3, 10'd0, 10'd32, 8'd1, 1'b1, 8'd1, 6'd0, 5'd0));
        repeat (2) @(posedge clk);
        #1;
        check("OOB saliency tile is dropped before mapper", saliency_dropped_oob_tile_count == 32'd1 && mapper_mapped_event_count == 32'd1);
        check("OOB saliency drop does not assert mapper OOB counter", mapper_dropped_oob_tile_count == 32'd0);

        @(negedge clk);
        mapper_event_ready = 1'b0;
        drive_event(make_event(4'd0, 12'd4, 10'd4, 10'd6, 8'd1, 1'b1, 8'd4, 6'd0, 5'd0));
        @(posedge clk);
        #1;
        check("mapper holds first non-skip output under backpressure", mapper_event_valid == 1'b1 && mapper_weight == 8'd4);

        drive_event(make_event(4'd0, 12'd5, 10'd4, 10'd6, 8'd1, 1'b1, 8'd5, 6'd0, 5'd0));
        @(posedge clk);
        #1;
        check("saliency output holds while mapper is backpressured", saliency_event_valid == 1'b1 && saliency_skip == 1'b0 && mapper_event_valid == 1'b1);
        check("upstream ready deasserts when non-skip output is held", s_event_ready == 1'b0);
        @(negedge clk);
        mapper_event_ready = 1'b1;
        @(posedge clk);
        #1;
        check("held saliency output advances after mapper ready", mapper_event_valid == 1'b1 && mapper_weight == 8'd5);
        @(posedge clk);
        #1;
        check("saliency-mapper backpressure path drains", saliency_event_valid == 1'b0 && mapper_event_valid == 1'b0);

        @(negedge clk);
        cfg_clear = 1'b1;
        @(posedge clk);
        #1;
        check("saliency clear resets active tile count", saliency_active_tile_count == 32'd0);
        check("saliency clear suppresses output", saliency_event_valid == 1'b0);
        @(negedge clk);
        cfg_clear = 1'b0;

        @(negedge clk);
        enable = 1'b0;
        s_event_valid = 1'b1;
        s_event_word = make_event(4'd0, 12'd6, 10'd1, 10'd1, 8'd0, 1'b1, 8'd1, 6'd0, 5'd0);
        #1;
        check("disabled saliency-mapper chain deasserts input ready", s_event_ready == 1'b0);
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
