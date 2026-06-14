`timescale 1ns / 1ps

module tb_time_surface_bank;
    reg clk = 1'b0;
    always #6.25 clk = ~clk;

    reg rst_n;
    reg enable;
    reg cfg_clear;
    reg [3:0] cfg_decay_shift;
    reg s_event_valid;
    reg [63:0] s_event_word;
    wire s_event_ready;
    wire m_sample_valid;
    wire [63:0] m_event_word;
    wire [7:0] m_cell_index;
    wire [7:0] m_surface_value;
    wire [7:0] m_previous_value;
    wire m_previous_valid;
    wire m_collision;
    reg m_sample_ready;
    wire [31:0] input_event_count;
    wire [31:0] update_count;
    wire [31:0] collision_overwrite_count;
    wire [31:0] valid_cell_count;
    wire [31:0] clear_count;

    integer pass_count = 0;
    integer fail_count = 0;

    time_surface_bank dut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .cfg_clear(cfg_clear),
        .cfg_decay_shift(cfg_decay_shift),
        .s_event_valid(s_event_valid),
        .s_event_word(s_event_word),
        .s_event_ready(s_event_ready),
        .m_sample_valid(m_sample_valid),
        .m_event_word(m_event_word),
        .m_cell_index(m_cell_index),
        .m_surface_value(m_surface_value),
        .m_previous_value(m_previous_value),
        .m_previous_valid(m_previous_valid),
        .m_collision(m_collision),
        .m_sample_ready(m_sample_ready),
        .input_event_count(input_event_count),
        .update_count(update_count),
        .collision_overwrite_count(collision_overwrite_count),
        .valid_cell_count(valid_cell_count),
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

    function [7:0] cell_index;
        input [9:0] x;
        input [9:0] y;
        input [7:0] channel;
        input polarity;
        begin
            cell_index = x[7:0] ^ {y[3:0], channel[3:0]} ^ {7'd0, polarity};
        end
    endfunction

    task automatic drive_event;
        input [63:0] word;
        begin
            @(negedge clk);
            s_event_word = word;
            s_event_valid = 1'b1;
            #1;
            check("time-surface bank accepts event when output slot available", s_event_ready == 1'b1);
            @(posedge clk);
            #1;
            @(negedge clk);
            s_event_valid = 1'b0;
        end
    endtask

    task automatic drain_sample;
        begin
            @(posedge clk);
            #1;
        end
    endtask

    initial begin
        rst_n = 1'b0;
        enable = 1'b1;
        cfg_clear = 1'b0;
        cfg_decay_shift = 4'd1;
        s_event_valid = 1'b0;
        s_event_word = 64'd0;
        m_sample_ready = 1'b1;

        repeat (3) @(posedge clk);
        @(negedge clk);
        rst_n = 1'b1;
        @(posedge clk);
        #1;

        check("reset clears time-surface output", m_sample_valid == 1'b0);
        check("reset clears time-surface counters", input_event_count == 32'd0 && update_count == 32'd0);

        drive_event(make_event(4'd0, 12'd6, 10'd1, 10'd2, 8'd3, 1'b1, 8'd2, 6'd0, 5'd0));
        check("time-surface sample emits update", m_sample_valid == 1'b1);
        check("time-surface sample preserves event word", m_event_word == make_event(4'd0, 12'd6, 10'd1, 10'd2, 8'd3, 1'b1, 8'd2, 6'd0, 5'd0));
        check("time-surface value matches HLS helper formula", m_surface_value == 8'd5);
        check("time-surface cell index is deterministic", m_cell_index == cell_index(10'd1, 10'd2, 8'd3, 1'b1));
        check("first time-surface update has no previous value", m_previous_valid == 1'b0 && m_collision == 1'b0);
        check("first time-surface update increments valid cell count", valid_cell_count == 32'd1);
        drain_sample();

        drive_event(make_event(4'd0, 12'd8, 10'd1, 10'd2, 8'd3, 1'b1, 8'hFC, 6'd0, 5'd0));
        check("time-surface signed payload uses absolute magnitude", m_surface_value == 8'd8);
        check("time-surface same-key update exposes previous value", m_previous_valid == 1'b1 && m_previous_value == 8'd5);
        check("time-surface same-key update is not a collision", m_collision == 1'b0);
        check("same-key update preserves valid cell count", valid_cell_count == 32'd1);
        drain_sample();

        cfg_decay_shift = 4'd0;
        drive_event(make_event(4'd0, 12'd3, 10'd5, 10'd1, 8'd3, 1'b1, 8'd0, 6'd0, 5'd0));
        check("zero payload uses base one", m_surface_value == 8'd4);
        check("new cell increments valid cell count", valid_cell_count == 32'd2);
        drain_sample();

        drive_event(make_event(4'd0, 12'd4095, 10'd9, 10'd1, 8'd3, 1'b1, 8'd10, 6'd0, 5'd0));
        check("time-surface value saturates to uint8", m_surface_value == 8'd255);
        drain_sample();

        drive_event(make_event(4'd0, 12'd5, 10'd257, 10'd2, 8'd3, 1'b1, 8'd1, 6'd0, 5'd0));
        check("hash collision overwrite is visible", m_collision == 1'b1 && m_previous_valid == 1'b1);
        check("collision counter increments", collision_overwrite_count == 32'd1);
        drain_sample();

        @(negedge clk);
        m_sample_ready = 1'b0;
        drive_event(make_event(4'd0, 12'd7, 10'd6, 10'd1, 8'd3, 1'b1, 8'd2, 6'd0, 5'd0));
        check("time-surface output holds under backpressure", m_sample_valid == 1'b1 && m_surface_value == 8'd9);
        @(posedge clk);
        #1;
        check("time-surface source is backpressured by held output", s_event_ready == 1'b0);
        @(negedge clk);
        m_sample_ready = 1'b1;
        drain_sample();

        @(negedge clk);
        cfg_clear = 1'b1;
        @(posedge clk);
        #1;
        check("time-surface clear removes valid cells", valid_cell_count == 32'd0);
        check("time-surface clear suppresses output", m_sample_valid == 1'b0);
        check("time-surface clear counter increments", clear_count == 32'd1);
        @(negedge clk);
        cfg_clear = 1'b0;

        @(negedge clk);
        enable = 1'b0;
        s_event_valid = 1'b1;
        #1;
        check("disabled time-surface bank deasserts input ready", s_event_ready == 1'b0);
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
