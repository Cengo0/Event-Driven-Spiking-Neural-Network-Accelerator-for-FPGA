`timescale 1ns / 1ps

module tb_event_delay_wheel;
    reg clk = 1'b0;
    always #6.25 clk = ~clk;

    reg rst_n;
    reg enable;
    reg tick;
    reg clear;
    reg s_event_valid;
    reg [63:0] s_event_word;
    reg [2:0] s_delay_class;
    wire s_event_ready;
    wire m_event_valid;
    wire [63:0] m_event_word;
    wire [2:0] m_delay_class;
    wire [15:0] m_release_tick;
    reg m_event_ready;
    wire [15:0] current_tick;
    wire [31:0] enqueued_event_count;
    wire [31:0] released_event_count;
    wire [31:0] blocked_bucket_count;

    integer pass_count = 0;
    integer fail_count = 0;

    event_delay_wheel dut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .tick(tick),
        .clear(clear),
        .s_event_valid(s_event_valid),
        .s_event_word(s_event_word),
        .s_delay_class(s_delay_class),
        .s_event_ready(s_event_ready),
        .m_event_valid(m_event_valid),
        .m_event_word(m_event_word),
        .m_delay_class(m_delay_class),
        .m_release_tick(m_release_tick),
        .m_event_ready(m_event_ready),
        .current_tick(current_tick),
        .enqueued_event_count(enqueued_event_count),
        .released_event_count(released_event_count),
        .blocked_bucket_count(blocked_bucket_count)
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
        input [2:0] delay_class;
        begin
            @(negedge clk);
            s_event_word = word;
            s_delay_class = delay_class;
            s_event_valid = 1'b1;
            #1;
            check("delay wheel accepts event when target bucket is free", s_event_ready == 1'b1);
            @(posedge clk);
            #1;
            @(negedge clk);
            s_event_valid = 1'b0;
        end
    endtask

    task automatic pulse_tick;
        begin
            @(negedge clk);
            tick = 1'b1;
            @(posedge clk);
            #1;
            @(negedge clk);
            tick = 1'b0;
        end
    endtask

    task automatic drain_due;
        begin
            @(posedge clk);
            #1;
        end
    endtask

    initial begin
        rst_n = 1'b0;
        enable = 1'b1;
        tick = 1'b0;
        clear = 1'b0;
        s_event_valid = 1'b0;
        s_event_word = 64'd0;
        s_delay_class = 3'd0;
        m_event_ready = 1'b1;

        repeat (3) @(posedge clk);
        @(negedge clk);
        rst_n = 1'b1;
        @(posedge clk);
        #1;

        check("reset clears delay output", m_event_valid == 1'b0);
        check("reset clears delay counters", enqueued_event_count == 32'd0 && released_event_count == 32'd0);
        check("reset clears delay tick", current_tick == 16'd0);

        drive_event(make_event(4'd0, 12'd10, 10'd1, 10'd2, 8'd3, 1'b1, 8'd4, 6'd0, 5'd0), 3'd0);
        check("zero delay event is immediately due", m_event_valid == 1'b1);
        check("zero delay preserves EventWord64", m_event_word[59:48] == 12'd10 && m_event_word[27:20] == 8'd3);
        check("zero delay records class and release tick", m_delay_class == 3'd0 && m_release_tick == 16'd0);
        drain_due();
        check("ready drains zero delay event", m_event_valid == 1'b0 && released_event_count == 32'd1);

        drive_event(make_event(4'd0, 12'd20, 10'd4, 10'd6, 8'd1, 1'b1, 8'd2, 6'd0, 5'd0), 3'd2);
        check("class 2 event is not due at tick 0", m_event_valid == 1'b0);
        pulse_tick();
        check("class 2 event is not due at tick 1", current_tick == 16'd1 && m_event_valid == 1'b0);

        drive_event(make_event(4'd0, 12'd21, 10'd8, 10'd8, 8'd2, 1'b1, 8'd1, 6'd0, 5'd0), 3'd0);
        check("later zero delay event is due before older delayed event", m_event_valid == 1'b1);
        check("later zero delay release tick is current tick", m_release_tick == 16'd1 && m_event_word[59:48] == 12'd21);
        drain_due();
        pulse_tick();
        check("older class 2 event is due at tick 2", current_tick == 16'd2 && m_event_valid == 1'b1);
        check("older class 2 event preserves payload", m_event_word[18:11] == 8'd2 && m_delay_class == 3'd2);
        drain_due();

        drive_event(make_event(4'd0, 12'd30, 10'd1, 10'd1, 8'd1, 1'b1, 8'd1, 6'd0, 5'd0), 3'd1);
        pulse_tick();
        m_event_ready = 1'b0;
        #1;
        check("due event is held under backpressure", m_event_valid == 1'b1 && m_release_tick == 16'd3);
        pulse_tick();
        check("delay wheel tick stalls while due output is blocked", current_tick == 16'd3 && m_event_valid == 1'b1);
        m_event_ready = 1'b1;
        drain_due();

        drive_event(make_event(4'd0, 12'd40, 10'd0, 10'd0, 8'd0, 1'b1, 8'd1, 6'd0, 5'd0), 3'd3);
        @(negedge clk);
        s_event_word = make_event(4'd0, 12'd41, 10'd0, 10'd0, 8'd0, 1'b1, 8'd1, 6'd0, 5'd0);
        s_delay_class = 3'd3;
        s_event_valid = 1'b1;
        #1;
        check("occupied target bucket backpressures second event", s_event_ready == 1'b0);
        @(posedge clk);
        #1;
        check("blocked bucket counter increments deterministically", blocked_bucket_count != 32'd0);
        @(negedge clk);
        s_event_valid = 1'b0;

        @(negedge clk);
        clear = 1'b1;
        @(posedge clk);
        #1;
        @(negedge clk);
        clear = 1'b0;
        check("clear removes pending delayed event", m_event_valid == 1'b0 && current_tick == 16'd0);

        @(negedge clk);
        enable = 1'b0;
        s_event_valid = 1'b1;
        #1;
        check("disabled delay wheel deasserts input ready", s_event_ready == 1'b0);
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
