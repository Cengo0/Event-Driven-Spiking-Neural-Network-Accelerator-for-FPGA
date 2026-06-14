`timescale 1ns / 1ps

module tb_event_frontend_pipeline;
    reg clk = 1'b0;
    always #6.25 clk = ~clk;

    reg rst_n;
    reg enable;
    reg s_event_valid;
    reg [63:0] s_event_word;
    wire s_event_ready;
    wire m_event_valid;
    wire [63:0] m_event_word;
    wire [10:0] m_global_id;
    wire [3:0] m_group_id;
    wire [6:0] m_local_id;
    wire [7:0] m_weight;
    wire m_exc;
    reg m_event_ready;

    reg [9:0] cfg_roi_x_start;
    reg [10:0] cfg_roi_x_stop;
    reg [9:0] cfg_roi_y_start;
    reg [10:0] cfg_roi_y_stop;
    reg cfg_allow_positive;
    reg cfg_allow_negative;
    reg cfg_hot_pixel_enable;
    reg [9:0] cfg_hot_pixel_x;
    reg [9:0] cfg_hot_pixel_y;
    reg [7:0] cfg_hot_pixel_channel;
    reg [11:0] cfg_refractory_ticks;
    reg [3:0] cfg_pool_x_shift;
    reg [3:0] cfg_pool_y_shift;
    reg [15:0] cfg_max_events_per_tile;
    reg cfg_time_surface_clear;
    reg [3:0] cfg_time_surface_decay_shift;
    reg [3:0] cfg_tile_x_shift;
    reg [3:0] cfg_tile_y_shift;
    reg [5:0] cfg_tiles_x;
    reg [6:0] cfg_local_x_mask;
    reg [2:0] cfg_local_y_shift;
    reg cfg_drop_oob_tiles;

    wire [7:0] m_time_surface_cell_index;
    wire [7:0] m_time_surface_value;
    wire [7:0] m_time_surface_previous_value;
    wire m_time_surface_previous_valid;
    wire m_time_surface_collision;
    wire [31:0] filter_input_event_count;
    wire [31:0] filter_accepted_event_count;
    wire [31:0] filter_dropped_roi_count;
    wire [31:0] filter_dropped_polarity_count;
    wire [31:0] filter_dropped_hot_pixel_count;
    wire [31:0] filter_dropped_refractory_count;
    wire [31:0] filter_dropped_tile_rate_count;
    wire [31:0] time_surface_input_event_count;
    wire [31:0] time_surface_update_count;
    wire [31:0] time_surface_collision_overwrite_count;
    wire [31:0] time_surface_valid_cell_count;
    wire [31:0] mapper_mapped_event_count;
    wire [31:0] mapper_dropped_oob_tile_count;

    integer pass_count = 0;
    integer fail_count = 0;

    event_frontend_pipeline dut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .s_event_valid(s_event_valid),
        .s_event_word(s_event_word),
        .s_event_ready(s_event_ready),
        .m_event_valid(m_event_valid),
        .m_event_word(m_event_word),
        .m_global_id(m_global_id),
        .m_group_id(m_group_id),
        .m_local_id(m_local_id),
        .m_weight(m_weight),
        .m_exc(m_exc),
        .m_event_ready(m_event_ready),
        .cfg_roi_x_start(cfg_roi_x_start),
        .cfg_roi_x_stop(cfg_roi_x_stop),
        .cfg_roi_y_start(cfg_roi_y_start),
        .cfg_roi_y_stop(cfg_roi_y_stop),
        .cfg_allow_positive(cfg_allow_positive),
        .cfg_allow_negative(cfg_allow_negative),
        .cfg_hot_pixel_enable(cfg_hot_pixel_enable),
        .cfg_hot_pixel_x(cfg_hot_pixel_x),
        .cfg_hot_pixel_y(cfg_hot_pixel_y),
        .cfg_hot_pixel_channel(cfg_hot_pixel_channel),
        .cfg_refractory_ticks(cfg_refractory_ticks),
        .cfg_pool_x_shift(cfg_pool_x_shift),
        .cfg_pool_y_shift(cfg_pool_y_shift),
        .cfg_max_events_per_tile(cfg_max_events_per_tile),
        .cfg_time_surface_clear(cfg_time_surface_clear),
        .cfg_time_surface_decay_shift(cfg_time_surface_decay_shift),
        .cfg_tile_x_shift(cfg_tile_x_shift),
        .cfg_tile_y_shift(cfg_tile_y_shift),
        .cfg_tiles_x(cfg_tiles_x),
        .cfg_local_x_mask(cfg_local_x_mask),
        .cfg_local_y_shift(cfg_local_y_shift),
        .cfg_drop_oob_tiles(cfg_drop_oob_tiles),
        .m_time_surface_cell_index(m_time_surface_cell_index),
        .m_time_surface_value(m_time_surface_value),
        .m_time_surface_previous_value(m_time_surface_previous_value),
        .m_time_surface_previous_valid(m_time_surface_previous_valid),
        .m_time_surface_collision(m_time_surface_collision),
        .filter_input_event_count(filter_input_event_count),
        .filter_accepted_event_count(filter_accepted_event_count),
        .filter_dropped_roi_count(filter_dropped_roi_count),
        .filter_dropped_polarity_count(filter_dropped_polarity_count),
        .filter_dropped_hot_pixel_count(filter_dropped_hot_pixel_count),
        .filter_dropped_refractory_count(filter_dropped_refractory_count),
        .filter_dropped_tile_rate_count(filter_dropped_tile_rate_count),
        .time_surface_input_event_count(time_surface_input_event_count),
        .time_surface_update_count(time_surface_update_count),
        .time_surface_collision_overwrite_count(time_surface_collision_overwrite_count),
        .time_surface_valid_cell_count(time_surface_valid_cell_count),
        .mapper_mapped_event_count(mapper_mapped_event_count),
        .mapper_dropped_oob_tile_count(mapper_dropped_oob_tile_count)
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
            check("frontend pipeline accepts event when ingress is ready", s_event_ready == 1'b1);
            @(posedge clk);
            #1;
            @(negedge clk);
            s_event_valid = 1'b0;
        end
    endtask

    task automatic wait_for_output;
        integer guard;
        begin
            guard = 0;
            while (m_event_valid == 1'b0 && guard < 10) begin
                @(posedge clk);
                #1;
                guard = guard + 1;
            end
            check("frontend pipeline emits mapped event", m_event_valid == 1'b1);
        end
    endtask

    initial begin
        rst_n = 1'b0;
        enable = 1'b1;
        s_event_valid = 1'b0;
        s_event_word = 64'd0;
        m_event_ready = 1'b1;
        cfg_roi_x_start = 10'd0;
        cfg_roi_x_stop = 11'd32;
        cfg_roi_y_start = 10'd0;
        cfg_roi_y_stop = 11'd32;
        cfg_allow_positive = 1'b1;
        cfg_allow_negative = 1'b0;
        cfg_hot_pixel_enable = 1'b0;
        cfg_hot_pixel_x = 10'd0;
        cfg_hot_pixel_y = 10'd0;
        cfg_hot_pixel_channel = 8'd0;
        cfg_refractory_ticks = 12'd0;
        cfg_pool_x_shift = 4'd1;
        cfg_pool_y_shift = 4'd1;
        cfg_max_events_per_tile = 16'd0;
        cfg_time_surface_clear = 1'b0;
        cfg_time_surface_decay_shift = 4'd1;
        cfg_tile_x_shift = 4'd1;
        cfg_tile_y_shift = 4'd1;
        cfg_tiles_x = 6'd4;
        cfg_local_x_mask = 7'h7f;
        cfg_local_y_shift = 3'd4;
        cfg_drop_oob_tiles = 1'b1;

        repeat (3) @(posedge clk);
        @(negedge clk);
        rst_n = 1'b1;
        @(posedge clk);
        #1;

        check("pipeline reset clears output", m_event_valid == 1'b0);
        check("pipeline reset clears counters", filter_input_event_count == 32'd0 && mapper_mapped_event_count == 32'd0);

        drive_event(make_event(4'd0, 12'd8, 10'd4, 10'd6, 8'd1, 1'b1, 8'd3, 6'd2, 5'd0));
        wait_for_output();
        check("pipeline pools coordinates before mapping", m_event_word[47:38] == 10'd2 && m_event_word[37:28] == 10'd3);
        check("pipeline preserves payload and sideband", m_event_word[18:11] == 8'd3 && m_event_word[10:5] == 6'd2);
        check("pipeline rewrites tile id after pooling", m_event_word[4:0] == 5'd5);
        check("pipeline mapper derives physical IDs", m_group_id == 4'd5 && m_local_id == 7'd50 && m_global_id == 11'd690);
        check("pipeline mapper exposes weight/exc", m_weight == 8'd3 && m_exc == 1'b1);
        check("pipeline time-surface value follows pooled event", m_time_surface_value == 8'd7);
        check("pipeline time-surface cell index is from pooled event", m_time_surface_cell_index == 8'd50);
        check("pipeline counters record all stages", filter_accepted_event_count == 32'd1 && time_surface_update_count == 32'd1 && mapper_mapped_event_count == 32'd1);
        @(posedge clk);
        #1;

        drive_event(make_event(4'd0, 12'd10, 10'd40, 10'd6, 8'd1, 1'b1, 8'd3, 6'd0, 5'd0));
        repeat (3) @(posedge clk);
        #1;
        check("pipeline ROI drop emits no mapped event", m_event_valid == 1'b0 && filter_dropped_roi_count == 32'd1);
        check("pipeline ROI drop does not update downstream", time_surface_update_count == 32'd1 && mapper_mapped_event_count == 32'd1);

        @(negedge clk);
        m_event_ready = 1'b0;
        drive_event(make_event(4'd0, 12'd12, 10'd8, 10'd0, 8'd2, 1'b1, 8'd4, 6'd0, 5'd0));
        wait_for_output();
        check("pipeline holds mapper output under backpressure", m_event_valid == 1'b1 && m_weight == 8'd4);
        @(posedge clk);
        #1;
        check("pipeline keeps output stable while internal stages absorb backpressure", m_event_valid == 1'b1 && m_weight == 8'd4);
        @(negedge clk);
        m_event_ready = 1'b1;
        @(posedge clk);
        #1;
        check("pipeline drains held mapper output", m_event_valid == 1'b0);

        @(negedge clk);
        cfg_time_surface_clear = 1'b1;
        @(posedge clk);
        #1;
        check("pipeline time-surface clear resets valid cells", time_surface_valid_cell_count == 32'd0);
        @(negedge clk);
        cfg_time_surface_clear = 1'b0;

        @(negedge clk);
        enable = 1'b0;
        s_event_valid = 1'b1;
        #1;
        check("disabled pipeline deasserts input ready", s_event_ready == 1'b0);
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
