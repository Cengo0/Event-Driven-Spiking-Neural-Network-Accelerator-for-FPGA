`timescale 1ns / 1ps

module tb_spike_conv_active_commit;
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
    wire [31:0] conv_updates_generated;
    wire [31:0] conv_address_errors;
    wire [(STATE_COUNT*STATE_WIDTH)-1:0] state_flat;
    wire [(STATE_COUNT*DEST_ID_WIDTH)-1:0] active_id_flat;
    wire [STATE_COUNT-1:0] active_mask;
    wire [31:0] active_neuron_count;
    wire [31:0] state_write_count;
    wire [31:0] update_count;
    wire [31:0] commit_reset_count;
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
    integer commit_seen = 0;
    reg [31:0] commit_words [0:3];
    reg commit_done_seen = 1'b0;

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
        .conv_spikes_processed(),
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
        .state_read_count(),
        .state_write_count(state_write_count),
        .update_count(update_count),
        .commit_reset_count(commit_reset_count),
        .invalid_dest_count(),
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

    task automatic reset_dut;
        begin
            rst_n = 1'b0;
            enable = 1'b0;
            state_clear = 1'b0;
            commit_clear = 1'b0;
            commit_start = 1'b0;
            commit_threshold = 16'sd99;
            commit_tready = 1'b1;
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
            check("C3 input spike accepted by AGU", s_axis_spike_tready == 1'b1);
            @(negedge clk);
            s_axis_spike_tvalid = 1'b0;
        end
    endtask

    task automatic start_commit;
        input signed [STATE_WIDTH-1:0] threshold;
        begin
            @(negedge clk);
            commit_threshold = threshold;
            commit_start = 1'b1;
            @(posedge clk);
            @(negedge clk);
            commit_start = 1'b0;
        end
    endtask

    task automatic wait_commit_done;
        begin
            cycles = 0;
            commit_done_seen = 1'b0;
            while (!commit_done && cycles < 64) begin
                @(posedge clk);
                if (commit_done) begin
                    commit_done_seen = 1'b1;
                end
                cycles = cycles + 1;
            end
            if (commit_done) begin
                commit_done_seen = 1'b1;
            end
            repeat (2) @(posedge clk);
            #1;
        end
    endtask

    task automatic clear_commit_engine;
        begin
            @(negedge clk);
            commit_seen = 0;
            commit_clear = 1'b1;
            @(posedge clk);
            @(negedge clk);
            commit_clear = 1'b0;
        end
    endtask

    initial begin
        kernel_weight_flat = {8'd4, 8'd3, 8'd2, 8'd1};
        reset_dut();
        commit_seen = 0;
        send_spike(8'd1, 8'd1, 8'd0);

        cycles = 0;
        while (update_count < 4 && cycles < 64) begin
            @(posedge clk);
            cycles = cycles + 1;
        end
        repeat (2) @(posedge clk);
        #1;

        check("C3 AGU generated four updates", conv_updates_generated == 32'd4);
        check("C3 state update consumed four updates", update_count == 32'd4);
        check("C3 active count matches trace", active_neuron_count == 32'd4);
        check("C3 active id[0] matches update order", active_id_flat[0*16 +: 16] == 16'd3);
        check("C3 active id[1] matches update order", active_id_flat[1*16 +: 16] == 16'd2);
        check("C3 active id[2] matches update order", active_id_flat[2*16 +: 16] == 16'd1);
        check("C3 active id[3] matches update order", active_id_flat[3*16 +: 16] == 16'd0);
        check("C3 state checksum matches trace", state_checksum == 32'sd10);
        check("C3 active mask matches trace", active_mask == 4'b1111);
        check("C3 no AGU address errors", conv_address_errors == 32'd0);

        start_commit(16'sd99);
        wait_commit_done();

        check("C3 empty-trace active commit done", commit_done_seen == 1'b1);
        check("C3 empty-trace scans active set only", active_commit_read_count == 32'd4);
        check("C3 empty-trace emits zero commits", commit_emit_count == 32'd0);
        check("C3 empty-trace output stream stays empty", commit_seen == 0);
        check("C3 empty-trace readout checksum is zero", readout_checksum == 32'sd0);
        check("C3 empty-trace uses no full-neuron scan", full_scan_count == 32'd0);
        check("C3 empty-trace performs no reset", commit_reset_count == 32'd0);

        clear_commit_engine();
        start_commit(16'sd3);
        wait_commit_done();

        check("C3 positive-threshold active commit done", commit_done_seen == 1'b1);
        check("C3 positive-threshold scans active set only", active_commit_read_count == 32'd4);
        check("C3 positive-threshold emits two commits", commit_emit_count == 32'd2);
        check("C3 positive-threshold output count matches", commit_seen == 2);
        check("C3 positive-threshold first commit is dest1 state3",
              commit_words[0] == {16'd1, 16'd3});
        check("C3 positive-threshold second commit is dest0 state4",
              commit_words[1] == {16'd0, 16'd4});
        check("C3 positive-threshold readout checksum matches",
              readout_checksum == 32'sd7);
        check("C3 positive-threshold uses no full-neuron scan", full_scan_count == 32'd0);
        check("C3 positive-threshold resets two committed neurons",
              commit_reset_count == 32'd2);
        check("C3 positive-threshold writes two commit resets",
              state_write_count == 32'd6);
        check("C3 positive-threshold resets state[0]",
              state_flat[0*STATE_WIDTH +: STATE_WIDTH] == 16'd0);
        check("C3 positive-threshold resets state[1]",
              state_flat[1*STATE_WIDTH +: STATE_WIDTH] == 16'd0);
        check("C3 positive-threshold preserves state[2]",
              state_flat[2*STATE_WIDTH +: STATE_WIDTH] == 16'd2);
        check("C3 positive-threshold preserves state[3]",
              state_flat[3*STATE_WIDTH +: STATE_WIDTH] == 16'd1);
        check("C3 positive-threshold compacts active count",
              active_neuron_count == 32'd2);
        check("C3 positive-threshold compacts active id[0]",
              active_id_flat[0*16 +: 16] == 16'd3);
        check("C3 positive-threshold compacts active id[1]",
              active_id_flat[1*16 +: 16] == 16'd2);
        check("C3 positive-threshold updates state checksum",
              state_checksum == 32'sd3);

        reset_dut();
        commit_seen = 0;
        send_spike(8'd1, 8'd1, 8'd0);
        cycles = 0;
        while (update_count < 4 && cycles < 64) begin
            @(posedge clk);
            cycles = cycles + 1;
        end
        repeat (2) @(posedge clk);
        #1;
        start_commit(16'sd2);
        wait_commit_done();

        check("C3 threshold-2 active commit done", commit_done_seen == 1'b1);
        check("C3 threshold-2 scans compacted active set once", active_commit_read_count == 32'd4);
        check("C3 threshold-2 emits three commits", commit_emit_count == 32'd3);
        check("C3 threshold-2 output count matches", commit_seen == 3);
        check("C3 threshold-2 first commit is dest2 state2",
              commit_words[0] == {16'd2, 16'd2});
        check("C3 threshold-2 second commit is dest1 state3",
              commit_words[1] == {16'd1, 16'd3});
        check("C3 threshold-2 third commit is dest0 state4",
              commit_words[2] == {16'd0, 16'd4});
        check("C3 threshold-2 readout checksum matches",
              readout_checksum == 32'sd9);
        check("C3 threshold-2 resets three committed neurons",
              commit_reset_count == 32'd3);
        check("C3 threshold-2 preserves only state[3]",
              state_checksum == 32'sd1);
        check("C3 threshold-2 compacts active count",
              active_neuron_count == 32'd1);
        check("C3 threshold-2 compacts active id[0]",
              active_id_flat[0*16 +: 16] == 16'd3);

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
