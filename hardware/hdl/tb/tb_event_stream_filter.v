`timescale 1ns / 1ps

module tb_event_stream_filter;
    reg clk = 1'b0;
    always #6.25 clk = ~clk;

    reg rst_n;
    reg enable;
    reg s_event_valid;
    reg [63:0] s_event_word;
    wire s_event_ready;
    wire m_event_valid;
    wire [63:0] m_event_word;
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

    wire [31:0] input_event_count;
    wire [31:0] accepted_event_count;
    wire [31:0] dropped_roi_count;
    wire [31:0] dropped_polarity_count;
    wire [31:0] dropped_hot_pixel_count;
    wire [31:0] dropped_refractory_count;
    wire [31:0] dropped_tile_rate_count;

    integer pass_count = 0;
    integer fail_count = 0;

    event_stream_filter dut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .s_event_valid(s_event_valid),
        .s_event_word(s_event_word),
        .s_event_ready(s_event_ready),
        .m_event_valid(m_event_valid),
        .m_event_word(m_event_word),
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
        .input_event_count(input_event_count),
        .accepted_event_count(accepted_event_count),
        .dropped_roi_count(dropped_roi_count),
        .dropped_polarity_count(dropped_polarity_count),
        .dropped_hot_pixel_count(dropped_hot_pixel_count),
        .dropped_refractory_count(dropped_refractory_count),
        .dropped_tile_rate_count(dropped_tile_rate_count)
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
        input [7:0] payload;
        input [5:0] layer_id;
        input [4:0] tile_id;
        begin
            make_event = {
                event_type,
                timestamp_delta,
                x,
                y,
                channel,
                polarity,
                payload,
                layer_id,
                tile_id
            };
        end
    endfunction

    task automatic drive_event;
        input [63:0] word;
        begin
            @(negedge clk);
            s_event_word = word;
            s_event_valid = 1'b1;
            @(posedge clk);
            #1;
            check("source event accepted by ready/valid", s_event_ready == 1'b1);
            @(negedge clk);
            s_event_valid = 1'b0;
        end
    endtask

    task automatic drain_output_cycle;
        begin
            @(posedge clk);
            #1;
        end
    endtask

    initial begin
        rst_n = 1'b0;
        enable = 1'b1;
        s_event_valid = 1'b0;
        s_event_word = 64'd0;
        m_event_ready = 1'b1;
        cfg_roi_x_start = 10'd0;
        cfg_roi_x_stop = 10'd16;
        cfg_roi_y_start = 10'd0;
        cfg_roi_y_stop = 10'd16;
        cfg_allow_positive = 1'b1;
        cfg_allow_negative = 1'b0;
        cfg_hot_pixel_enable = 1'b1;
        cfg_hot_pixel_x = 10'd2;
        cfg_hot_pixel_y = 10'd2;
        cfg_hot_pixel_channel = 8'd0;
        cfg_refractory_ticks = 12'd5;
        cfg_pool_x_shift = 4'd1;
        cfg_pool_y_shift = 4'd1;
        cfg_max_events_per_tile = 16'd2;

        repeat (3) @(posedge clk);
        @(negedge clk);
        rst_n = 1'b1;
        @(posedge clk);
        #1;

        check("reset clears output valid", m_event_valid == 1'b0);
        check("reset clears counters", input_event_count == 32'd0 && accepted_event_count == 32'd0);

        drive_event(make_event(4'd0, 12'd10, 10'd4, 10'd6, 8'd1, 1'b1, 8'hFB, 6'd3, 5'd7));
        check("accepted event produces output", m_event_valid == 1'b1);
        check("output preserves EventWord64 type", m_event_word[63:60] == 4'd0);
        check("output preserves timestamp", m_event_word[59:48] == 12'd10);
        check("output pools x coordinate", m_event_word[47:38] == 10'd2);
        check("output pools y coordinate", m_event_word[37:28] == 10'd3);
        check("output preserves channel", m_event_word[27:20] == 8'd1);
        check("output preserves polarity", m_event_word[19] == 1'b1);
        check("output preserves signed payload byte", m_event_word[18:11] == 8'hFB);
        check("output preserves layer/tile sideband", m_event_word[10:5] == 6'd3 && m_event_word[4:0] == 5'd7);
        m_event_ready = 1'b0;
        #1;
        check("held output backpressures input ready", s_event_ready == 1'b0);
        m_event_ready = 1'b1;
        drain_output_cycle();

        drive_event(make_event(4'd0, 12'd12, 10'd4, 10'd6, 8'd1, 1'b1, 8'd1, 6'd0, 5'd0));
        check("refractory drop emits no output", m_event_valid == 1'b0);

        drive_event(make_event(4'd0, 12'd20, 10'd17, 10'd6, 8'd1, 1'b1, 8'd1, 6'd0, 5'd0));
        check("ROI drop emits no output", m_event_valid == 1'b0);

        drive_event(make_event(4'd0, 12'd21, 10'd5, 10'd5, 8'd1, 1'b0, 8'd1, 6'd0, 5'd0));
        check("polarity drop emits no output", m_event_valid == 1'b0);

        drive_event(make_event(4'd0, 12'd22, 10'd2, 10'd2, 8'd0, 1'b1, 8'd1, 6'd0, 5'd0));
        check("hot-pixel drop emits no output", m_event_valid == 1'b0);

        drive_event(make_event(4'd0, 12'd30, 10'd4, 10'd6, 8'd1, 1'b1, 8'd2, 6'd0, 5'd0));
        check("post-refractory event produces output", m_event_valid == 1'b1);
        drain_output_cycle();

        drive_event(make_event(4'd0, 12'd40, 10'd4, 10'd6, 8'd1, 1'b1, 8'd2, 6'd0, 5'd0));
        check("tile-rate drop emits no output", m_event_valid == 1'b0);

        check("input counter includes all events", input_event_count == 32'd7);
        check("accepted counter includes only emitted events", accepted_event_count == 32'd2);
        check("drop counters classify ROI", dropped_roi_count == 32'd1);
        check("drop counters classify polarity", dropped_polarity_count == 32'd1);
        check("drop counters classify hot-pixel", dropped_hot_pixel_count == 32'd1);
        check("drop counters classify refractory", dropped_refractory_count == 32'd1);
        check("drop counters classify tile-rate throttle", dropped_tile_rate_count == 32'd1);

        @(negedge clk);
        rst_n = 1'b0;
        @(negedge clk);
        rst_n = 1'b1;
        cfg_allow_negative = 1'b1;
        cfg_hot_pixel_enable = 1'b0;
        cfg_refractory_ticks = 12'd5;
        cfg_max_events_per_tile = 16'd0;
        @(posedge clk);
        drive_event(make_event(4'd0, 12'd10, 10'd8, 10'd8, 8'd2, 1'b1, 8'd1, 6'd0, 5'd0));
        check("polarity-key setup event produces output", m_event_valid == 1'b1);
        drain_output_cycle();
        drive_event(make_event(4'd0, 12'd12, 10'd8, 10'd8, 8'd2, 1'b0, 8'd1, 6'd0, 5'd0));
        check("opposite-polarity event is not refractory-dropped", m_event_valid == 1'b1);
        drain_output_cycle();
        check("refractory key includes polarity", accepted_event_count == 32'd2 && dropped_refractory_count == 32'd0);

        @(negedge clk);
        enable = 1'b0;
        s_event_word = make_event(4'd0, 12'd31, 10'd4, 10'd6, 8'd1, 1'b1, 8'd2, 6'd0, 5'd0);
        s_event_valid = 1'b1;
        #1;
        check("disabled frontend deasserts ready", s_event_ready == 1'b0);
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
