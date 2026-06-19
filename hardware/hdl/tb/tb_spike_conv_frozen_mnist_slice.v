`timescale 1ns / 1ps

module tb_spike_conv_frozen_mnist_slice;
    localparam KERNEL_SIZE = 3;
    localparam INPUT_WIDTH = 28;
    localparam INPUT_HEIGHT = 28;
    localparam NUM_CHANNELS = 1;
    localparam OUTPUT_CHANNELS = 4;
    localparam STRIDE = 2;
    localparam PADDING = 1;
    localparam KERNEL_WEIGHT_BITS = 8;
    localparam KERNEL_WORDS = OUTPUT_CHANNELS * NUM_CHANNELS * KERNEL_SIZE * KERNEL_SIZE;
    localparam STATE_COUNT = 784;
    localparam STATE_WIDTH = 16;
    localparam DEST_ID_WIDTH = 16;

    reg clk = 1'b0;
    always #6.25 clk = ~clk;

    reg rst_n;
    reg enable;
    reg state_clear;
    reg commit_clear;
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
    wire [(STATE_COUNT*DEST_ID_WIDTH)-1:0] active_id_flat;
    wire [STATE_COUNT-1:0] active_mask;
    wire [31:0] active_neuron_count;
    wire [31:0] state_read_count;
    wire [31:0] state_write_count;
    wire [31:0] update_count;
    wire [31:0] commit_reset_count;
    wire [31:0] invalid_dest_count;
    wire signed [31:0] state_checksum;
    reg commit_start;
    reg signed [STATE_WIDTH-1:0] commit_threshold;
    wire commit_busy;
    wire commit_done;
    wire commit_tvalid;
    wire [31:0] commit_tdata;
    reg commit_tready;
    wire reset_tvalid;
    wire [DEST_ID_WIDTH-1:0] reset_tdest;
    wire reset_tready;
    wire [31:0] active_commit_read_count;
    wire [31:0] commit_emit_count;
    wire [31:0] full_scan_count;
    wire signed [31:0] readout_checksum;

    integer pass_count = 0;
    integer fail_count = 0;
    integer cycles;
    integer idx;
    integer commit_seen = 0;
    reg [31:0] commit_words [0:7];

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
        .DEST_ID_WIDTH(DEST_ID_WIDTH),
        .STATE_WIDTH(STATE_WIDTH),
        .WEIGHT_WIDTH(KERNEL_WEIGHT_BITS)
    ) u_state (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .clear(state_clear),
        .s_axis_update_tvalid(update_tvalid),
        .s_axis_update_tdata(update_tdata),
        .update_weight(update_weight),
        .s_axis_update_tready(update_tready),
        .s_axis_reset_tvalid(reset_tvalid),
        .s_axis_reset_tdest(reset_tdest),
        .s_axis_reset_tready(reset_tready),
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

    spike_conv_active_commit #(
        .STATE_COUNT(STATE_COUNT),
        .DEST_ID_WIDTH(DEST_ID_WIDTH),
        .STATE_WIDTH(STATE_WIDTH)
    ) u_commit (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .clear(commit_clear),
        .commit_start(commit_start),
        .commit_threshold(commit_threshold),
        .active_neuron_count(active_neuron_count),
        .active_id_flat(active_id_flat),
        .state_flat(state_flat),
        .commit_busy(commit_busy),
        .commit_done(commit_done),
        .m_axis_commit_tvalid(commit_tvalid),
        .m_axis_commit_tdata(commit_tdata),
        .m_axis_commit_tready(commit_tready),
        .m_axis_reset_tvalid(reset_tvalid),
        .m_axis_reset_tdest(reset_tdest),
        .m_axis_reset_tready(reset_tready),
        .active_commit_read_count(active_commit_read_count),
        .commit_emit_count(commit_emit_count),
        .full_scan_count(full_scan_count),
        .readout_checksum(readout_checksum)
    );

    always @(posedge clk) begin
        if (commit_tvalid && commit_tready) begin
            commit_words[commit_seen] <= commit_tdata;
            commit_seen <= commit_seen + 1;
        end
    end

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

    task automatic wait_updates;
        begin
            cycles = 0;
            while (update_count < 32'd4 && cycles < 512) begin
                @(posedge clk);
                cycles = cycles + 1;
            end
        end
    endtask

    task automatic wait_commit_done;
        begin
            cycles = 0;
            while (!commit_done && cycles < 2048) begin
                @(posedge clk);
                cycles = cycles + 1;
            end
        end
    endtask

    initial begin
        rst_n = 1'b0;
        enable = 1'b0;
        state_clear = 1'b0;
        commit_clear = 1'b0;
        s_axis_spike_tvalid = 1'b0;
        s_axis_spike_tdata = 32'd0;
        commit_start = 1'b0;
        commit_threshold = 16'sd1;
        commit_tready = 1'b1;
        kernel_weight_flat = {(KERNEL_WORDS){8'h01}};
        for (idx = 0; idx < 8; idx = idx + 1) begin
            commit_words[idx] = 32'd0;
        end

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        enable = 1'b1;
        repeat (2) @(posedge clk);

        s_axis_spike_tdata = {8'd14, 8'd14, 8'd0, 8'd1};
        s_axis_spike_tvalid = 1'b1;
        @(posedge clk);
        check("frozen input spike accepted", s_axis_spike_tready);
        s_axis_spike_tvalid = 1'b0;

        wait_updates();
        check("frozen AGU processed one input", conv_spikes_processed == 32'd1);
        check("frozen AGU generated four channel updates", conv_updates_generated == 32'd4);
        check("frozen state consumed four updates", update_count == 32'd4);
        check("frozen active count is four", active_neuron_count == 32'd4);
        check("frozen active id[0] is cout0 y7 x7", active_id_flat[0 +: 16] == 16'd105);
        check("frozen active id[1] is cout1 y7 x7", active_id_flat[16 +: 16] == 16'd301);
        check("frozen active id[2] is cout2 y7 x7", active_id_flat[32 +: 16] == 16'd497);
        check("frozen active id[3] is cout3 y7 x7", active_id_flat[48 +: 16] == 16'd693);
        check("frozen AGU records skipped stride/pad candidates", conv_address_errors > 32'd0);
        check("frozen has no invalid destinations", invalid_dest_count == 32'd0);

        @(posedge clk);
        commit_start = 1'b1;
        @(posedge clk);
        commit_start = 1'b0;
        wait_commit_done();
        repeat (4) @(posedge clk);

        check("frozen active commit done", commit_done == 1'b1 || commit_emit_count == 32'd4);
        check("frozen emits four conv commits", commit_emit_count == 32'd4);
        check("frozen output count captured", commit_seen == 4);
        check("frozen commit[0]", commit_words[0] == {16'd105, 16'd1});
        check("frozen commit[1]", commit_words[1] == {16'd301, 16'd1});
        check("frozen commit[2]", commit_words[2] == {16'd497, 16'd1});
        check("frozen commit[3]", commit_words[3] == {16'd693, 16'd1});
        check("frozen scans active set only", active_commit_read_count == 32'd4);
        check("frozen uses no full scan", full_scan_count == 32'd0);
        check("frozen resets four states", commit_reset_count == 32'd4);

        $display("Results: %0d PASS, %0d FAIL", pass_count, fail_count);
        if (fail_count == 0) begin
            $display("*** ALL TESTS PASSED ***");
        end else begin
            $display("*** SOME TESTS FAILED ***");
        end
        $finish;
    end
endmodule
