`timescale 1ns / 1ps

module tb_routed_event_expander;
    reg clk = 1'b0;
    always #6.25 clk = ~clk;

    reg rst_n;
    reg enable;
    reg s_event_valid;
    reg [63:0] s_routed_word;
    wire s_event_ready;
    wire m_event_valid;
    wire [10:0] m_global_id;
    wire [3:0] m_group_id;
    wire [6:0] m_local_id;
    wire [10:0] m_tag;
    wire [3:0] m_weight;
    wire m_exc;
    wire [3:0] m_delay_class;
    wire [3:0] m_route_index;
    reg m_event_ready;
    wire [31:0] input_event_count;
    wire [31:0] expanded_event_count;
    wire [31:0] zero_mask_drop_count;
    wire [31:0] unsupported_route_mode_drop_count;

    integer pass_count = 0;
    integer fail_count = 0;

    routed_event_expander dut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .s_event_valid(s_event_valid),
        .s_routed_word(s_routed_word),
        .s_event_ready(s_event_ready),
        .m_event_valid(m_event_valid),
        .m_global_id(m_global_id),
        .m_group_id(m_group_id),
        .m_local_id(m_local_id),
        .m_tag(m_tag),
        .m_weight(m_weight),
        .m_exc(m_exc),
        .m_delay_class(m_delay_class),
        .m_route_index(m_route_index),
        .m_event_ready(m_event_ready),
        .input_event_count(input_event_count),
        .expanded_event_count(expanded_event_count),
        .zero_mask_drop_count(zero_mask_drop_count),
        .unsupported_route_mode_drop_count(unsupported_route_mode_drop_count)
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

    function [63:0] make_routed;
        input [1:0] route_mode;
        input [1:0] event_type;
        input [10:0] tag;
        input [15:0] dst_group_mask;
        input [6:0] dst_neuron;
        input [3:0] weight_class;
        input exc;
        input [3:0] delay_class;
        begin
            make_routed = 64'd0;
            make_routed[63:62] = route_mode;
            make_routed[61:60] = event_type;
            make_routed[59:49] = tag;
            make_routed[48:33] = dst_group_mask;
            make_routed[32:26] = dst_neuron;
            make_routed[25:22] = weight_class;
            make_routed[21] = exc;
            make_routed[20:17] = delay_class;
        end
    endfunction

    task automatic drive_routed;
        input [63:0] word;
        begin
            @(negedge clk);
            s_routed_word = word;
            s_event_valid = 1'b1;
            #1;
            check("routed expander accepts input when idle", s_event_ready == 1'b1);
            @(posedge clk);
            #1;
            @(negedge clk);
            s_event_valid = 1'b0;
        end
    endtask

    task automatic observe_output;
        input [3:0] exp_group;
        input [6:0] exp_local;
        input [10:0] exp_global;
        input [3:0] exp_route_index;
        input [3:0] exp_weight;
        input exp_exc;
        begin
            @(posedge clk);
            #1;
            check("routed expander emits selected group", m_event_valid == 1'b1 && m_group_id == exp_group);
            check("routed expander derives local/global id", m_local_id == exp_local && m_global_id == exp_global);
            check("routed expander preserves sideband", m_route_index == exp_route_index && m_weight == exp_weight && m_exc == exp_exc);
        end
    endtask

    initial begin
        rst_n = 1'b0;
        enable = 1'b1;
        s_event_valid = 1'b0;
        s_routed_word = 64'd0;
        m_event_ready = 1'b1;

        repeat (3) @(posedge clk);
        @(negedge clk);
        rst_n = 1'b1;
        @(posedge clk);
        #1;

        check("reset clears routed output", m_event_valid == 1'b0);
        check("reset clears routed counters", input_event_count == 32'd0 && expanded_event_count == 32'd0);
        check("reset clears routed drop counters", zero_mask_drop_count == 32'd0 && unsupported_route_mode_drop_count == 32'd0);

        drive_routed(make_routed(2'd2, 2'd1, 11'h155, 16'h00F3, 7'd127, 4'd9, 1'b0, 4'd7));
        observe_output(4'd0, 7'd127, 11'd127, 4'd0, 4'd9, 1'b0);
        check("routed expander preserves tag and delay", m_tag == 11'h155 && m_delay_class == 4'd7);
        observe_output(4'd1, 7'd127, 11'd255, 4'd1, 4'd9, 1'b0);
        observe_output(4'd4, 7'd127, 11'd639, 4'd2, 4'd9, 1'b0);
        observe_output(4'd5, 7'd127, 11'd767, 4'd3, 4'd9, 1'b0);
        observe_output(4'd6, 7'd127, 11'd895, 4'd4, 4'd9, 1'b0);
        observe_output(4'd7, 7'd127, 11'd1023, 4'd5, 4'd9, 1'b0);
        @(posedge clk);
        #1;
        check("routed expander drains after mask fanout", m_event_valid == 1'b0);
        check("routed expander counts expanded destinations", expanded_event_count == 32'd6);

        drive_routed(make_routed(2'd1, 2'd0, 11'd5, 16'h0005, 7'd11, 4'd3, 1'b1, 4'd2));
        @(posedge clk);
        #1;
        check("unsupported route mode emits no destination", m_event_valid == 1'b0);
        check("unsupported route mode increments drop counter", unsupported_route_mode_drop_count == 32'd1);
        check("unsupported route mode does not expand destinations", expanded_event_count == 32'd6);

        drive_routed(make_routed(2'd2, 2'd0, 11'd5, 16'h0005, 7'd11, 4'd3, 1'b1, 4'd2));
        observe_output(4'd0, 7'd11, 11'd11, 4'd0, 4'd3, 1'b1);
        observe_output(4'd2, 7'd11, 11'd267, 4'd1, 4'd3, 1'b1);
        m_event_ready = 1'b0;
        @(posedge clk);
        #1;
        check("routed expander holds output under backpressure", m_event_valid == 1'b1 && m_group_id == 4'd2);
        m_event_ready = 1'b1;
        @(posedge clk);
        #1;
        check("routed expander completes held destination", m_event_valid == 1'b0 || m_group_id == 4'd2);

        drive_routed(make_routed(2'd2, 2'd0, 11'd0, 16'h0000, 7'd0, 4'd0, 1'b1, 4'd0));
        @(posedge clk);
        #1;
        check("zero group mask emits no destination", m_event_valid == 1'b0);
        check("zero group mask increments drop counter", zero_mask_drop_count == 32'd1);

        @(negedge clk);
        enable = 1'b0;
        s_event_valid = 1'b1;
        #1;
        check("disabled routed expander deasserts input ready", s_event_ready == 1'b0);
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
