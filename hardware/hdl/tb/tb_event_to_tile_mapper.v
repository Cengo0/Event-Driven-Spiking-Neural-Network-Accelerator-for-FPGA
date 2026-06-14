`timescale 1ns / 1ps

module tb_event_to_tile_mapper;
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

    reg [3:0] cfg_tile_x_shift;
    reg [3:0] cfg_tile_y_shift;
    reg [5:0] cfg_tiles_x;
    reg [6:0] cfg_local_x_mask;
    reg [2:0] cfg_local_y_shift;
    reg cfg_drop_oob_tiles;
    wire [31:0] mapped_event_count;
    wire [31:0] dropped_oob_tile_count;

    integer pass_count = 0;
    integer fail_count = 0;

    event_to_tile_mapper dut (
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
        .cfg_tile_x_shift(cfg_tile_x_shift),
        .cfg_tile_y_shift(cfg_tile_y_shift),
        .cfg_tiles_x(cfg_tiles_x),
        .cfg_local_x_mask(cfg_local_x_mask),
        .cfg_local_y_shift(cfg_local_y_shift),
        .cfg_drop_oob_tiles(cfg_drop_oob_tiles),
        .mapped_event_count(mapped_event_count),
        .dropped_oob_tile_count(dropped_oob_tile_count)
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

    task automatic drain_output;
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
        cfg_tile_x_shift = 4'd4;
        cfg_tile_y_shift = 4'd4;
        cfg_tiles_x = 6'd8;
        cfg_local_x_mask = 7'h0F;
        cfg_local_y_shift = 3'd4;
        cfg_drop_oob_tiles = 1'b1;

        repeat (3) @(posedge clk);
        @(negedge clk);
        rst_n = 1'b1;
        @(posedge clk);
        #1;

        check("reset clears mapper output valid", m_event_valid == 1'b0);
        check("reset clears mapper counters", mapped_event_count == 32'd0 && dropped_oob_tile_count == 32'd0);

        drive_event(make_event(4'd0, 12'd99, 10'd17, 10'd1, 8'd4, 1'b1, 8'd8, 6'd6, 5'd0));
        check("mapper emits first event", m_event_valid == 1'b1);
        check("mapper rewrites tile_id from coordinates", m_event_word[4:0] == 5'd1);
        check(
            "mapper preserves EventWord64 high fields",
            m_event_word[63:60] == 4'd0 &&
            m_event_word[59:48] == 12'd99 &&
            m_event_word[47:38] == 10'd17 &&
            m_event_word[37:28] == 10'd1 &&
            m_event_word[27:20] == 8'd4 &&
            m_event_word[19] == 1'b1 &&
            m_event_word[18:11] == 8'd8 &&
            m_event_word[10:5] == 6'd6
        );
        check("mapper derives group/local/global IDs", m_group_id == 4'd1 && m_local_id == 7'd17 && m_global_id == 11'd145);
        check("mapper maps positive payload to excitatory weight", m_weight == 8'd8 && m_exc == 1'b1);

        m_event_ready = 1'b0;
        #1;
        check("held mapper output backpressures input ready", s_event_ready == 1'b0);
        m_event_ready = 1'b1;
        drain_output();

        drive_event(make_event(4'd1, 12'd7, 10'd2, 10'd7, 8'd3, 1'b0, 8'hFB, 6'd2, 5'd31));
        check("mapper emits negative-payload event", m_event_valid == 1'b1);
        check("mapper rewrites stale input tile sideband", m_event_word[4:0] == 5'd0);
        check("mapper preserves signed payload byte", m_event_word[18:11] == 8'hFB);
        check("mapper maps negative payload to inhibitory weight magnitude", m_weight == 8'd5 && m_exc == 1'b0);
        check("mapper packs local low-coordinate bits", m_group_id == 4'd0 && m_local_id == 7'd114 && m_global_id == 11'd114);
        drain_output();

        drive_event(make_event(4'd0, 12'd20, 10'd0, 10'd32, 8'd1, 1'b1, 8'd1, 6'd0, 5'd0));
        check("tile 16 drops instead of aliasing group 0", m_event_valid == 1'b0);
        check("mapper counters classify mapped and OOB events", mapped_event_count == 32'd2 && dropped_oob_tile_count == 32'd1);

        @(negedge clk);
        cfg_drop_oob_tiles = 1'b0;
        drive_event(make_event(4'd0, 12'd21, 10'd0, 10'd32, 8'd1, 1'b1, 8'd1, 6'd0, 5'd0));
        check("mapper can pass tile 16 with explicit OOB drop disabled", m_event_valid == 1'b1 && m_event_word[4:0] == 5'd16);
        drain_output();

        @(negedge clk);
        enable = 1'b0;
        s_event_word = make_event(4'd0, 12'd0, 10'd0, 10'd0, 8'd0, 1'b1, 8'd1, 6'd0, 5'd0);
        s_event_valid = 1'b1;
        #1;
        check("disabled mapper deasserts ready", s_event_ready == 1'b0);
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
