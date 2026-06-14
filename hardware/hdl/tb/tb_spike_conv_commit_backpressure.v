`timescale 1ns / 1ps

module tb_spike_conv_commit_backpressure;
    localparam STATE_COUNT = 4;
    localparam STATE_WIDTH = 16;
    localparam DEST_ID_WIDTH = 16;

    reg clk = 1'b0;
    always #6.25 clk = ~clk;

    reg rst_n;
    reg enable;
    reg clear;
    reg commit_start;
    reg signed [STATE_WIDTH-1:0] commit_threshold;
    reg [(STATE_COUNT*DEST_ID_WIDTH)-1:0] active_id_flat;
    reg [(STATE_COUNT*STATE_WIDTH)-1:0] state_flat;
    wire commit_busy;
    wire commit_done;
    wire commit_tvalid;
    wire [31:0] commit_tdata;
    reg commit_tready;
    wire reset_tvalid;
    wire [DEST_ID_WIDTH-1:0] reset_tdest;
    reg reset_tready;
    wire [31:0] active_commit_read_count;
    wire [31:0] commit_emit_count;
    wire [31:0] full_scan_count;
    wire signed [31:0] readout_checksum;
    wire [31:0] output_backpressure_cycle_count;

    integer pass_count = 0;
    integer fail_count = 0;
    integer cycles;
    integer commit_seen = 0;
    integer reset_seen = 0;
    reg [31:0] commit_words [0:3];
    reg [DEST_ID_WIDTH-1:0] reset_dests [0:3];
    reg commit_done_seen = 1'b0;

    spike_conv_active_commit #(
        .STATE_COUNT(STATE_COUNT),
        .DEST_ID_WIDTH(DEST_ID_WIDTH),
        .STATE_WIDTH(STATE_WIDTH)
    ) u_commit (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .clear(clear),
        .commit_start(commit_start),
        .commit_threshold(commit_threshold),
        .active_neuron_count(32'd4),
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
        .readout_checksum(readout_checksum),
        .output_backpressure_cycle_count(output_backpressure_cycle_count)
    );

    always @(posedge clk) begin
        if (commit_tvalid && commit_tready) begin
            commit_words[commit_seen] <= commit_tdata;
            commit_seen <= commit_seen + 1;
        end
        if (reset_tvalid && reset_tready) begin
            reset_dests[reset_seen] <= reset_tdest;
            reset_seen <= reset_seen + 1;
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
            clear = 1'b0;
            commit_start = 1'b0;
            commit_threshold = 16'sd3;
            commit_tready = 1'b0;
            reset_tready = 1'b0;
            commit_seen = 0;
            reset_seen = 0;

            active_id_flat = {16'd0, 16'd1, 16'd2, 16'd3};
            state_flat = {16'd1, 16'd2, 16'd3, 16'd4};

            repeat (4) @(posedge clk);
            @(negedge clk);
            rst_n = 1'b1;
            enable = 1'b1;
            @(posedge clk);
            @(negedge clk);
        end
    endtask

    task automatic start_readout;
        begin
            @(negedge clk);
            commit_start = 1'b1;
            @(posedge clk);
            @(negedge clk);
            commit_start = 1'b0;
        end
    endtask

    task automatic wait_valid_pair;
        begin
            cycles = 0;
            while ((!commit_tvalid || !reset_tvalid) && cycles < 64) begin
                @(posedge clk);
                cycles = cycles + 1;
            end
            #1;
        end
    endtask

    task automatic wait_done;
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
        reset_dut();
        start_readout();

        wait_valid_pair();
        check("C5 first commit/reset valid pair appears", commit_tvalid && reset_tvalid);
        check("C5 first held commit payload is dest1 state3", commit_tdata == {16'd1, 16'd3});
        check("C5 first held reset dest is dest1", reset_tdest == 16'd1);

        repeat (3) @(posedge clk);
        #1;
        check("C5 backpressure holds first commit valid", commit_tvalid == 1'b1);
        check("C5 backpressure holds first reset valid", reset_tvalid == 1'b1);
        check("C5 no output emitted while both sinks stalled", commit_emit_count == 32'd0);

        @(negedge clk);
        commit_tready = 1'b1;
        reset_tready = 1'b0;
        @(posedge clk);
        @(negedge clk);
        commit_tready = 1'b1;
        reset_tready = 1'b0;
        repeat (2) @(posedge clk);
        #1;
        check("C5 one-sided commit ready accepts first commit once", commit_seen == 1);
        check("C5 one-sided commit ready does not duplicate commit", commit_tvalid == 1'b0);
        check("C5 reset channel remains valid while stalled", reset_tvalid == 1'b1);
        check("C5 first output not counted until reset handshakes", commit_emit_count == 32'd0);

        @(negedge clk);
        commit_tready = 1'b0;
        reset_tready = 1'b1;
        @(posedge clk);
        @(negedge clk);
        commit_tready = 1'b0;
        reset_tready = 1'b0;
        wait_valid_pair();
        check("C5 first paired output completes after reset ready", commit_emit_count == 32'd1);
        check("C5 first reset accepted once", reset_seen == 1);
        check("C5 second held commit payload is dest0 state4", commit_tdata == {16'd0, 16'd4});
        check("C5 second held reset dest is dest0", reset_tdest == 16'd0);

        @(negedge clk);
        commit_tready = 1'b0;
        reset_tready = 1'b1;
        @(posedge clk);
        @(negedge clk);
        commit_tready = 1'b0;
        reset_tready = 1'b1;
        repeat (2) @(posedge clk);
        #1;
        check("C5 one-sided reset ready accepts second reset once", reset_seen == 2);
        check("C5 one-sided reset ready does not duplicate reset", reset_tvalid == 1'b0);
        check("C5 commit channel remains valid while stalled", commit_tvalid == 1'b1);
        check("C5 second output not counted until commit handshakes", commit_emit_count == 32'd1);

        @(negedge clk);
        commit_tready = 1'b1;
        reset_tready = 1'b0;
        @(posedge clk);
        @(negedge clk);
        commit_tready = 1'b0;
        reset_tready = 1'b0;
        wait_done();

        check("C5 commit backpressure readout done", commit_done_seen == 1'b1);
        check("C5 commit output count remains exact", commit_seen == 2);
        check("C5 reset output count remains exact", reset_seen == 2);
        check("C5 emits exactly two paired commits", commit_emit_count == 32'd2);
        check("C5 first commit word preserved", commit_words[0] == {16'd1, 16'd3});
        check("C5 second commit word preserved", commit_words[1] == {16'd0, 16'd4});
        check("C5 first reset dest preserved", reset_dests[0] == 16'd1);
        check("C5 second reset dest preserved", reset_dests[1] == 16'd0);
        check("C5 scans active set only", active_commit_read_count == 32'd4);
        check("C5 uses no full-neuron scan", full_scan_count == 32'd0);
        check("C5 readout checksum matches committed states", readout_checksum == 32'sd7);
        check("C5 records output backpressure cycles", output_backpressure_cycle_count > 32'd0);
        check("C5 no extra valid remains after done", !commit_tvalid && !reset_tvalid);

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
