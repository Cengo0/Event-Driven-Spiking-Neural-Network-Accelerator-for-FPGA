`timescale 1ns / 1ps

module tb_spike_conv_state_update;
    localparam KERNEL_SIZE = 2;
    localparam INPUT_WIDTH = 3;
    localparam INPUT_HEIGHT = 3;
    localparam NUM_CHANNELS = 1;
    localparam OUTPUT_CHANNELS = 1;
    localparam STRIDE = 1;
    localparam PADDING = 0;
    localparam KERNEL_WEIGHT_BITS = 8;
    localparam KERNEL_WORDS = OUTPUT_CHANNELS * NUM_CHANNELS * KERNEL_SIZE * KERNEL_SIZE;
    localparam STATE_COUNT = 4;
    localparam STATE_WIDTH = 16;

    reg clk = 1'b0;
    always #6.25 clk = ~clk;

    reg rst_n;
    reg enable;
    reg clear;
    reg s_axis_spike_tvalid;
    reg [31:0] s_axis_spike_tdata;
    wire s_axis_spike_tready;
    wire update_tvalid;
    wire [31:0] update_tdata;
    wire update_tready;
    wire signed [KERNEL_WEIGHT_BITS-1:0] update_weight;
    wire [KERNEL_WEIGHT_BITS-1:0] kernel_weight_out;
    reg [(KERNEL_WORDS*KERNEL_WEIGHT_BITS)-1:0] kernel_weight_flat;
    wire [31:0] conv_spikes_processed;
    wire [31:0] conv_updates_generated;
    wire [31:0] conv_address_errors;
    wire [(STATE_COUNT*STATE_WIDTH)-1:0] state_flat;
    wire [(STATE_COUNT*16)-1:0] active_id_flat;
    wire [STATE_COUNT-1:0] active_mask;
    wire [31:0] active_neuron_count;
    wire [31:0] state_read_count;
    wire [31:0] state_write_count;
    wire [31:0] update_count;
    wire [31:0] commit_reset_count;
    wire [31:0] invalid_dest_count;
    wire signed [31:0] state_checksum;

    integer pass_count = 0;
    integer fail_count = 0;
    integer cycles;

    spike_conv_agu #(
        .KERNEL_SIZE(KERNEL_SIZE),
        .INPUT_WIDTH(INPUT_WIDTH),
        .INPUT_HEIGHT(INPUT_HEIGHT),
        .NUM_CHANNELS(NUM_CHANNELS),
        .OUTPUT_CHANNELS(OUTPUT_CHANNELS),
        .STRIDE(STRIDE),
        .PADDING(PADDING),
        .KERNEL_WEIGHT_BITS(KERNEL_WEIGHT_BITS)
    ) u_agu (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .s_axis_spike_tvalid(s_axis_spike_tvalid),
        .s_axis_spike_tdata(s_axis_spike_tdata),
        .s_axis_spike_tready(s_axis_spike_tready),
        .m_axis_spike_tvalid(update_tvalid),
        .m_axis_spike_tdata(update_tdata),
        .m_axis_spike_tready(update_tready),
        .kernel_weight_out(kernel_weight_out),
        .kernel_weight_flat(kernel_weight_flat),
        .conv_spikes_processed(conv_spikes_processed),
        .conv_updates_generated(conv_updates_generated),
        .conv_address_errors(conv_address_errors)
    );

    assign update_weight = kernel_weight_out;

    spike_conv_state_update #(
        .STATE_COUNT(STATE_COUNT),
        .DEST_ID_WIDTH(16),
        .STATE_WIDTH(STATE_WIDTH),
        .WEIGHT_WIDTH(KERNEL_WEIGHT_BITS)
    ) u_state (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .clear(clear),
        .s_axis_update_tvalid(update_tvalid),
        .s_axis_update_tdata(update_tdata),
        .update_weight(update_weight),
        .s_axis_update_tready(update_tready),
        .s_axis_reset_tvalid(1'b0),
        .s_axis_reset_tdest(16'd0),
        .s_axis_reset_tready(),
        .state_flat(state_flat),
        .active_id_flat(active_id_flat),
        .active_mask(active_mask),
        .active_neuron_count(active_neuron_count),
        .state_read_count(state_read_count),
        .state_write_count(state_write_count),
        .update_count(update_count),
        .commit_reset_count(commit_reset_count),
        .invalid_dest_count(invalid_dest_count),
        .state_checksum(state_checksum)
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

    task automatic reset_dut;
        begin
            rst_n = 1'b0;
            enable = 1'b0;
            clear = 1'b0;
            s_axis_spike_tvalid = 1'b0;
            s_axis_spike_tdata = 32'd0;
            repeat (4) @(posedge clk);
            @(negedge clk);
            rst_n = 1'b1;
            enable = 1'b1;
            @(posedge clk);
            @(negedge clk);
        end
    endtask

    task automatic send_spike;
        input [7:0] x;
        input [7:0] y;
        input [7:0] channel;
        begin
            @(negedge clk);
            s_axis_spike_tdata = {x, y, channel, 8'd0};
            s_axis_spike_tvalid = 1'b1;
            @(posedge clk);
            check("input spike accepted by AGU", s_axis_spike_tready == 1'b1);
            @(negedge clk);
            s_axis_spike_tvalid = 1'b0;
        end
    endtask

    initial begin
        kernel_weight_flat = {8'd4, 8'd3, 8'd2, 8'd1};
        reset_dut();
        send_spike(8'd1, 8'd1, 8'd0);

        cycles = 0;
        while (update_count < 4 && cycles < 64) begin
            @(posedge clk);
            cycles = cycles + 1;
        end
        repeat (2) @(posedge clk);
        #1;

        check("C2 AGU generated four updates", conv_updates_generated == 32'd4);
        check("C2 state update consumed four updates", update_count == 32'd4);
        check("C2 state reads match trace", state_read_count == 32'd4);
        check("C2 state writes match trace", state_write_count == 32'd4);
        check("C2 active count matches trace", active_neuron_count == 32'd4);
        check("C2 active id[0] matches update order", active_id_flat[0*16 +: 16] == 16'd3);
        check("C2 active id[1] matches update order", active_id_flat[1*16 +: 16] == 16'd2);
        check("C2 active id[2] matches update order", active_id_flat[2*16 +: 16] == 16'd1);
        check("C2 active id[3] matches update order", active_id_flat[3*16 +: 16] == 16'd0);
        check("C2 no invalid destination", invalid_dest_count == 32'd0);
        check("C2 no commit resets", commit_reset_count == 32'd0);
        check("C2 no AGU address errors", conv_address_errors == 32'd0);
        check("C2 state[0] matches trace", state_flat[0*STATE_WIDTH +: STATE_WIDTH] == 16'd4);
        check("C2 state[1] matches trace", state_flat[1*STATE_WIDTH +: STATE_WIDTH] == 16'd3);
        check("C2 state[2] matches trace", state_flat[2*STATE_WIDTH +: STATE_WIDTH] == 16'd2);
        check("C2 state[3] matches trace", state_flat[3*STATE_WIDTH +: STATE_WIDTH] == 16'd1);
        check("C2 state checksum matches trace", state_checksum == 32'sd10);
        check("C2 active mask matches trace", active_mask == 4'b1111);

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
