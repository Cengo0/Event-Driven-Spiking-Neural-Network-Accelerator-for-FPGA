`timescale 1ns / 1ps

module tb_spike_conv_c4_scaleup;
    localparam KERNEL_SIZE = 3;
    localparam INPUT_WIDTH = 8;
    localparam INPUT_HEIGHT = 8;
    localparam NUM_CHANNELS = 1;
    localparam OUTPUT_CHANNELS = 1;
    localparam STRIDE = 1;
    localparam PADDING = 1;
    localparam KERNEL_WEIGHT_BITS = 8;
    localparam KERNEL_WORDS = OUTPUT_CHANNELS * NUM_CHANNELS * KERNEL_SIZE * KERNEL_SIZE;
    localparam STATE_COUNT = 64;
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
    integer commit_seen = 0;
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
            check("C4 input spike accepted by AGU", s_axis_spike_tready == 1'b1);
            @(negedge clk);
            s_axis_spike_tvalid = 1'b0;
        end
    endtask

    task automatic wait_updates;
        input [31:0] expected_count;
        begin
            cycles = 0;
            while (update_count < expected_count && cycles < 256) begin
                @(posedge clk);
                cycles = cycles + 1;
            end
            repeat (2) @(posedge clk);
            #1;
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
            while (!commit_done && cycles < 128) begin
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

    initial begin
        kernel_weight_flat = {
            8'hFF, 8'd0, 8'd1,
            8'hFE, 8'd0, 8'd2,
            8'hFF, 8'd0, 8'd1
        };
        reset_dut();

        send_spike(8'd3, 8'd3, 8'd0);
        wait_updates(32'd6);
        send_spike(8'd4, 8'd4, 8'd0);
        wait_updates(32'd12);

        check("C4 processed two input spikes", conv_spikes_processed == 32'd2);
        check("C4 generated twelve signed updates", conv_updates_generated == 32'd12);
        check("C4 state update consumed twelve updates", update_count == 32'd12);
        check("C4 state reads match scale trace", state_read_count == 32'd12);
        check("C4 state writes match scale trace", state_write_count == 32'd12);
        check("C4 active count matches scale trace", active_neuron_count == 32'd12);
        check("C4 no invalid destination", invalid_dest_count == 32'd0);
        check("C4 no AGU address errors", conv_address_errors == 32'd0);
        check("C4 no commit resets before readout", commit_reset_count == 32'd0);
        check("C4 signed state checksum matches trace", state_checksum == 32'sd0);

        check("C4 active id[0] matches scale trace", active_id_flat[0*16 +: 16] == 16'd36);
        check("C4 active id[1] matches scale trace", active_id_flat[1*16 +: 16] == 16'd34);
        check("C4 active id[2] matches scale trace", active_id_flat[2*16 +: 16] == 16'd28);
        check("C4 active id[3] matches scale trace", active_id_flat[3*16 +: 16] == 16'd26);
        check("C4 active id[4] matches scale trace", active_id_flat[4*16 +: 16] == 16'd20);
        check("C4 active id[5] matches scale trace", active_id_flat[5*16 +: 16] == 16'd18);
        check("C4 active id[6] matches scale trace", active_id_flat[6*16 +: 16] == 16'd45);
        check("C4 active id[7] matches scale trace", active_id_flat[7*16 +: 16] == 16'd43);
        check("C4 active id[8] matches scale trace", active_id_flat[8*16 +: 16] == 16'd37);
        check("C4 active id[9] matches scale trace", active_id_flat[9*16 +: 16] == 16'd35);
        check("C4 active id[10] matches scale trace", active_id_flat[10*16 +: 16] == 16'd29);
        check("C4 active id[11] matches scale trace", active_id_flat[11*16 +: 16] == 16'd27);

        check("C4 state[36] positive signed match", state_flat[36*STATE_WIDTH +: STATE_WIDTH] == 16'd1);
        check("C4 state[34] negative signed match", state_flat[34*STATE_WIDTH +: STATE_WIDTH] == 16'hFFFF);
        check("C4 state[28] positive signed match", state_flat[28*STATE_WIDTH +: STATE_WIDTH] == 16'd2);
        check("C4 state[26] negative signed match", state_flat[26*STATE_WIDTH +: STATE_WIDTH] == 16'hFFFE);
        check("C4 state[20] positive signed match", state_flat[20*STATE_WIDTH +: STATE_WIDTH] == 16'd1);
        check("C4 state[18] negative signed match", state_flat[18*STATE_WIDTH +: STATE_WIDTH] == 16'hFFFF);
        check("C4 state[45] positive signed match", state_flat[45*STATE_WIDTH +: STATE_WIDTH] == 16'd1);
        check("C4 state[43] negative signed match", state_flat[43*STATE_WIDTH +: STATE_WIDTH] == 16'hFFFF);
        check("C4 state[37] positive signed match", state_flat[37*STATE_WIDTH +: STATE_WIDTH] == 16'd2);
        check("C4 state[35] negative signed match", state_flat[35*STATE_WIDTH +: STATE_WIDTH] == 16'hFFFE);
        check("C4 state[29] positive signed match", state_flat[29*STATE_WIDTH +: STATE_WIDTH] == 16'd1);
        check("C4 state[27] negative signed match", state_flat[27*STATE_WIDTH +: STATE_WIDTH] == 16'hFFFF);
        check("C4 active mask includes first active destination", active_mask[36] == 1'b1);
        check("C4 active mask includes last active destination", active_mask[27] == 1'b1);
        check("C4 inactive destination remains clear", active_mask[0] == 1'b0);

        start_commit(16'sd99);
        wait_commit_done();

        check("C4 high-threshold active commit done", commit_done_seen == 1'b1);
        check("C4 high-threshold scans active set only", active_commit_read_count == 32'd12);
        check("C4 high-threshold emits zero commits", commit_emit_count == 32'd0);
        check("C4 high-threshold output stream stays empty", commit_seen == 0);
        check("C4 high-threshold readout checksum is zero", readout_checksum == 32'sd0);
        check("C4 high-threshold uses no full-neuron scan", full_scan_count == 32'd0);
        check("C4 high-threshold performs no reset", commit_reset_count == 32'd0);

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
