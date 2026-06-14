`timescale 1ns / 1ps
`include "spikemold_params.vh"

module tb_spikemold_coregroup;
    parameter NEURONS_PER_GROUP  = `SNN_NEURONS_PER_GROUP;
    parameter DATA_WIDTH         = `SNN_DATA_WIDTH;
    parameter WEIGHT_WIDTH       = `SNN_WEIGHT_WIDTH;
    parameter THRESHOLD_WIDTH    = `SNN_THRESHOLD_WIDTH;
    parameter LEAK_WIDTH         = `SNN_LEAK_WIDTH;
    parameter REFRAC_WIDTH       = `SNN_REFRAC_WIDTH;
    parameter SPIKE_BUFFER_DEPTH = `SNN_SPIKE_BUFFER_DEPTH;
    parameter LOCAL_ID_WIDTH     = `SNN_LOCAL_ID_WIDTH;

    reg clk = 0;
    always #6.25 clk = ~clk;
    reg rst_n, enable;
    reg ext_spike_valid;
    reg [LOCAL_ID_WIDTH-1:0] ext_spike_dest_id;
    reg [WEIGHT_WIDTH-1:0] ext_spike_weight;
    reg ext_spike_exc_inh;
    reg [THRESHOLD_WIDTH-1:0] ext_spike_threshold;
    wire ext_spike_ready;
    wire out_spike_valid;
    wire [LOCAL_ID_WIDTH-1:0] out_spike_neuron_id;
    reg out_spike_ready;
    reg [THRESHOLD_WIDTH-1:0] global_threshold;
    reg [LEAK_WIDTH-1:0] global_leak_rate;
    reg [REFRAC_WIDTH-1:0] global_refrac_period;
    reg accumulate_only;
    reg commit_start;
    reg [THRESHOLD_WIDTH-1:0] commit_threshold;
    wire commit_busy;
    wire commit_done;
    reg clear_start;
    wire clear_busy;
    wire clear_done;
    reg weight_we;
    reg [LOCAL_ID_WIDTH-1:0] weight_src_id, weight_dst_id;
    reg [WEIGHT_WIDTH-1:0] weight_data;
    reg weight_exc;
    wire [15:0] spike_count;
    wire group_busy;

    spikemold_coregroup #(
        .GROUP_ID(0), .NEURONS_PER_GROUP(NEURONS_PER_GROUP),
        .DATA_WIDTH(DATA_WIDTH), .WEIGHT_WIDTH(WEIGHT_WIDTH),
        .THRESHOLD_WIDTH(THRESHOLD_WIDTH), .LEAK_WIDTH(LEAK_WIDTH),
        .REFRAC_WIDTH(REFRAC_WIDTH), .SPIKE_BUFFER_DEPTH(SPIKE_BUFFER_DEPTH)
    ) u_dut (
        .clk(clk), .rst_n(rst_n), .enable(enable),
        .ext_spike_valid(ext_spike_valid), .ext_spike_dest_id(ext_spike_dest_id),
        .ext_spike_weight(ext_spike_weight), .ext_spike_exc_inh(ext_spike_exc_inh),
        .ext_spike_threshold(ext_spike_threshold),
        .ext_spike_ready(ext_spike_ready),
        .out_spike_valid(out_spike_valid), .out_spike_neuron_id(out_spike_neuron_id),
        .out_spike_ready(out_spike_ready),
        .global_threshold(global_threshold), .global_leak_rate(global_leak_rate),
        .global_refrac_period(global_refrac_period),
        .accumulate_only(accumulate_only), .commit_start(commit_start),
        .commit_threshold(commit_threshold), .commit_busy(commit_busy),
        .commit_done(commit_done), .clear_start(clear_start),
        .clear_busy(clear_busy), .clear_done(clear_done),
        .weight_we(weight_we), .weight_src_id(weight_src_id),
        .weight_dst_id(weight_dst_id), .weight_data(weight_data),
        .weight_exc(weight_exc),
        .spike_count(spike_count), .group_busy(group_busy)
    );

    integer pass_count = 0;
    integer fail_count = 0;

    task automatic check;
        input integer tnum;
        input [8*80-1:0] desc;
        input integer cond;
    begin
        if (cond) begin
            $display("[PASS] Test %0d: %0s", tnum, desc);
            pass_count = pass_count + 1;
        end else begin
            $display("[FAIL] Test %0d: %0s", tnum, desc);
            fail_count = fail_count + 1;
        end
    end
    endtask

    task automatic wait_done;
        integer t;
    begin
        t = 0;
        while (t < 300000) begin
            @(posedge clk);
            t = t + 1;
            if (u_dut.fifo_count == 0 && u_dut.state <= 4'd3)
                t = 300000;
        end
        repeat(5) @(posedge clk);
    end
    endtask

    task automatic wait_idle;
        integer t;
    begin
        t = 0;
        while ((u_dut.fifo_count != 0 || u_dut.state != 4'd0) && t < 300000) begin
            @(posedge clk);
            t = t + 1;
        end
        repeat(2) @(posedge clk);
    end
    endtask

    task automatic wait_spikes;
        input integer expected;
        integer t;
    begin
        t = 0;
        while (spike_count < expected && t < 300000) begin
            @(posedge clk);
            t = t + 1;
        end
        repeat(5) @(posedge clk);
    end
    endtask

    task automatic wait_commit_done;
        integer t;
    begin
        t = 0;
        while (!commit_done && t < 300000) begin
            @(posedge clk);
            t = t + 1;
        end
        repeat(5) @(posedge clk);
    end
    endtask

    task automatic wait_clear_done;
        integer t;
    begin
        t = 0;
        while (!clear_done && t < 300000) begin
            @(posedge clk);
            t = t + 1;
        end
        repeat(5) @(posedge clk);
    end
    endtask

    task automatic inject_spike;
        input [LOCAL_ID_WIDTH-1:0] dest;
        input [WEIGHT_WIDTH-1:0] w;
        input exc;
    begin
        @(posedge clk);
        ext_spike_valid   <= 1;
        ext_spike_dest_id <= dest;
        ext_spike_weight  <= w;
        ext_spike_exc_inh <= exc;
        ext_spike_threshold <= global_threshold;
        @(posedge clk);
        while (!ext_spike_ready) @(posedge clk);
        ext_spike_valid   <= 0;
    end
    endtask

    task automatic load_weight;
        input [LOCAL_ID_WIDTH-1:0] src;
        input [LOCAL_ID_WIDTH-1:0] dst;
        input [WEIGHT_WIDTH-1:0] w;
        input exc;
    begin
        @(posedge clk);
        weight_we <= 1; weight_src_id <= src; weight_dst_id <= dst;
        weight_data <= w; weight_exc <= exc;
        @(posedge clk);
        weight_we <= 0;
    end
    endtask

    task automatic do_reset;
    begin
        rst_n <= 0; enable <= 0;
        ext_spike_valid <= 0; out_spike_ready <= 1;
        ext_spike_threshold <= 0;
        global_threshold <= 16'd10; global_leak_rate <= 8'd0;
        global_refrac_period <= 8'd5;
        accumulate_only <= 0; commit_start <= 0; commit_threshold <= 16'd10;
        clear_start <= 0;
        weight_we <= 0; weight_src_id <= 0; weight_dst_id <= 0;
        weight_data <= 0; weight_exc <= 0;
        repeat(20) @(posedge clk);
        rst_n <= 1;
        repeat(5) @(posedge clk);
        enable <= 1;
        repeat(5) @(posedge clk);
    end
    endtask

    initial begin
        $display("=========================================================");
        $display("  SpikeMold Coregroup Testbench - 128 LIF Neurons");
        $display("=========================================================");
        do_reset;

        // TEST 1: Reset state
        check(1, "spike_count=0 after reset", spike_count == 0);

        // TEST 2: Weight load
        $display("\n--- Test 2: Weight Load ---");
        load_weight(7'd0, 7'd1, 8'd15, 1'b1);
        repeat(5) @(posedge clk);
        check(2, "Weight loaded without error", 1);

        // TEST 3: Sub-threshold (w=5 < threshold=10)
        $display("\n--- Test 3: Sub-threshold ---");
        inject_spike(7'd5, 8'd5, 1'b1);
        wait_done;
        check(3, "Sub-threshold: spike_count stays 0", spike_count == 0);

        // TEST 4: Supra-threshold (w=15 >= threshold=10)
        $display("\n--- Test 4: Supra-threshold ---");
        inject_spike(7'd10, 8'd15, 1'b1);
        wait_spikes(1);
        check(4, "Supra-threshold: spike_count=1", spike_count == 1);

        // TEST 5: Output spike detected
        $display("\n--- Test 5: Output Spike Detection ---");
        begin : t5
            reg seen;
            integer i;
            seen = 0;
            inject_spike(7'd20, 8'd15, 1'b1);
            for (i = 0; i < 5000; i = i + 1) begin
                @(posedge clk);
                if (out_spike_valid && out_spike_neuron_id == 7'd20) seen = 1;
            end
            check(5, "Output spike for neuron 20 seen", seen);
        end

        // TEST 6: Refractory blocks second fire
        $display("\n--- Test 6: Refractory ---");
        begin : t6
            reg [15:0] sc;
            global_refrac_period <= 8'd200;
            repeat(5) @(posedge clk);
            sc = spike_count;
            inject_spike(7'd15, 8'd15, 1'b1);
            wait_spikes(sc + 1);
            sc = spike_count;
            inject_spike(7'd15, 8'd15, 1'b1);
            wait_done;
            check(6, "Refractory blocks second fire", spike_count == sc);
            global_refrac_period <= 8'd5;
        end

        // TEST 7: Accumulation (3x4=12 > threshold=10)
        $display("\n--- Test 7: Accumulation ---");
        begin : t7
            reg [15:0] sc;
            sc = spike_count;
            inject_spike(7'd30, 8'd4, 1'b1);
            wait_done;
            inject_spike(7'd30, 8'd4, 1'b1);
            wait_done;
            inject_spike(7'd30, 8'd4, 1'b1);
            wait_spikes(sc + 1);
            check(7, "3x4=12>10 fires", spike_count > sc);
        end

        // TEST 8: Inhibitory (no fire)
        $display("\n--- Test 8: Inhibitory ---");
        begin : t8
            reg [15:0] sc;
            sc = spike_count;
            inject_spike(7'd40, 8'd10, 1'b0);
            wait_done;
            check(8, "Inhibitory: no fire", spike_count == sc);
        end

        // TEST 9: Intra-group recurrence (50->51)
        $display("\n--- Test 9: Intra-Group Recurrence ---");
        begin : t9
            reg [15:0] sc;
            load_weight(7'd50, 7'd51, 8'd15, 1'b1);
            repeat(5) @(posedge clk);
            sc = spike_count;
            inject_spike(7'd50, 8'd15, 1'b1);
            wait_spikes(sc + 2);
            check(9, "Recurrence: both 50 and 51 fire", spike_count >= sc + 2);
        end

        // TEST 10: Backpressure
        $display("\n--- Test 10: Backpressure ---");
        begin : t10
            reg [15:0] sc;
            out_spike_ready <= 0;
            sc = spike_count;
            inject_spike(7'd60, 8'd15, 1'b1);
            wait_spikes(sc + 1);
            check(10, "Fires even with backpressure", spike_count > sc);
            out_spike_ready <= 1;
            repeat(100) @(posedge clk);
        end

        // TEST 11: Zero weight
        $display("\n--- Test 11: Zero Weight ---");
        begin : t11
            reg [15:0] sc;
            sc = spike_count;
            inject_spike(7'd70, 8'd0, 1'b1);
            wait_done;
            check(11, "Zero weight: no fire", spike_count == sc);
        end

        // TEST 12: Burst (10 neurons w=15)
        $display("\n--- Test 12: Burst ---");
        begin : t12
            integer bi;
            reg [15:0] sc;
            sc = spike_count;
            for (bi = 0; bi < 10; bi = bi + 1) begin
                inject_spike(80 + bi[6:0], 8'd15, 1'b1);
            end
            wait_spikes(sc + 10);
            check(12, "Burst: 10 spikes all fire", spike_count >= sc + 10);
        end

        // TEST 13: Exact threshold (w=10 == threshold)
        $display("\n--- Test 13: Exact Threshold ---");
        begin : t13
            reg [15:0] sc;
            sc = spike_count;
            inject_spike(7'd100, 8'd10, 1'b1);
            wait_spikes(sc + 1);
            check(13, "Exact threshold fires", spike_count > sc);
        end

        // TEST 14: Multi-neuron diverse weights
        $display("\n--- Test 14: Multi-Neuron Diverse ---");
        begin : t14
            reg [15:0] sc;
            sc = spike_count;
            inject_spike(7'd110, 8'd3, 1'b1);
            wait_done;
            inject_spike(7'd111, 8'd12, 1'b1);
            wait_spikes(sc + 1);
            inject_spike(7'd112, 8'd1, 1'b1);
            wait_done;
            check(14, "Only w=12 neuron fires", spike_count == sc + 1);
        end

        // TEST 15: Leak decay
        $display("\n--- Test 15: Leak Decay ---");
        begin : t15
            reg [15:0] sc;
            global_leak_rate <= 8'd1;
            repeat(5) @(posedge clk);
            sc = spike_count;
            inject_spike(7'd120, 8'd8, 1'b1);
            wait_done;
            repeat(5000) @(posedge clk);
            inject_spike(7'd120, 8'd3, 1'b1);
            wait_done;
            check(15, "After leak decay sub-threshold stays sub-thresh", spike_count == sc);
            global_leak_rate <= 8'd0;
        end

        // TEST 16: Inhibitory input must not be a firing trigger.
        $display("\n--- Test 16: Inhibitory Cannot Trigger Fire ---");
        begin : t16
            reg [15:0] sc;
            wait_done;
            sc = spike_count;
            u_dut.neuron_state_mem[7'd41] = {
                {{(DATA_WIDTH-5){1'b0}}, 5'd20},
                {REFRAC_WIDTH{1'b0}}
            };
            inject_spike(7'd41, 8'd1, 1'b0);
            wait_done;
            check(16, "Inhibitory input does not fire even from high membrane", spike_count == sc);
        end

        // TEST 17: Recurrent routing must hold a non-zero event when full.
        $display("\n--- Test 17: Recurrent FIFO Full Hold ---");
        begin : t17
            reg [LOCAL_ID_WIDTH-1:0] held_idx;
            reg [LOCAL_ID_WIDTH-1:0] held_wr_ptr;
            do_reset;
            @(negedge clk);
            u_dut.state = 4'd7;  // ST_INTRA_ROUTE
            u_dut.wm_dout = {1'b1, {{(WEIGHT_WIDTH-4){1'b0}}, 4'd9}};
            u_dut.intra_scan_idx = 7'd3;
            u_dut.fifo_count = SPIKE_BUFFER_DEPTH;
            held_idx = u_dut.intra_scan_idx;
            held_wr_ptr = u_dut.fifo_wr_ptr;
            @(posedge clk);
            repeat(1) @(negedge clk);
            check(17, "Full FIFO holds current recurrent event",
                  u_dut.state == 4'd7 &&
                  u_dut.intra_scan_idx == held_idx &&
                  u_dut.fifo_wr_ptr == held_wr_ptr);
            do_reset;
        end

        // TEST 18: Accumulate-only suppresses early fire, commit scan emits.
        $display("\n--- Test 18: Accumulate-Only Commit Scan ---");
        begin : t18
            reg [15:0] sc;
            reg seen_commit_spike;
            integer i;
            do_reset;
            wait_done;
            sc = spike_count;
            out_spike_ready <= 0;
            accumulate_only <= 1;
            inject_spike(7'd25, 8'd6, 1'b1);
            wait_done;
            inject_spike(7'd25, 8'd6, 1'b1);
            wait_done;
            check(18, "Accumulate-only prevents early threshold fire", spike_count == sc);

            wait_idle;
            commit_threshold <= global_threshold;
            @(posedge clk);
            commit_start <= 1;
            @(posedge clk);
            commit_start <= 0;
            wait_commit_done;

            seen_commit_spike = 0;
            for (i = 0; i < 100; i = i + 1) begin
                @(posedge clk);
                if (out_spike_valid && out_spike_neuron_id == 7'd25)
                    seen_commit_spike = 1;
            end
            check(19, "Commit scan emits accumulated thresholded neuron",
                  spike_count == sc + 1 && seen_commit_spike);
            out_spike_ready <= 1;
            accumulate_only <= 0;
            repeat(10) @(posedge clk);
        end

        // TEST 20: Clear destination group state before commit.
        $display("\n--- Test 20: Selected Group Clear ---");
        begin : t20
            reg [15:0] sc;
            reg seen_spike;
            integer i;
            do_reset;
            wait_done;
            sc = spike_count;
            accumulate_only <= 1;
            inject_spike(7'd27, 8'd6, 1'b1);
            wait_done;
            inject_spike(7'd27, 8'd6, 1'b1);
            wait_done;

            @(posedge clk);
            clear_start <= 1;
            @(posedge clk);
            clear_start <= 0;
            wait_clear_done;
            wait_idle;

            commit_threshold <= global_threshold;
            @(posedge clk);
            commit_start <= 1;
            @(posedge clk);
            commit_start <= 0;
            wait_commit_done;

            seen_spike = 0;
            for (i = 0; i < 100; i = i + 1) begin
                @(posedge clk);
                if (out_spike_valid)
                    seen_spike = 1;
            end
            check(20, "Clear removes accumulated membrane before commit",
                  spike_count == sc && !seen_spike && !clear_busy);
            accumulate_only <= 0;
            repeat(10) @(posedge clk);
        end

        // TEST 21: External FIFO write must exactly follow ext_spike_ready.
        $display("\n--- Test 21: External Write Matches Ready During Commit ---");
        begin : t21
            integer i;
            integer timeout;
            reg write_while_not_ready;
            reg ready_blocked_seen;
            integer fifo_count_before;

            do_reset;
            wait_idle;
            commit_threshold <= global_threshold;
            @(posedge clk);
            commit_start <= 1;
            @(posedge clk);
            commit_start <= 0;

            timeout = 0;
            while (!commit_busy && timeout < 1000) begin
                @(posedge clk);
                timeout = timeout + 1;
            end

            fifo_count_before = u_dut.fifo_count;
            write_while_not_ready = 0;
            ready_blocked_seen = 0;

            @(negedge clk);
            ext_spike_valid <= 1;
            ext_spike_dest_id <= 7'd31;
            ext_spike_weight <= 8'd1;
            ext_spike_exc_inh <= 1'b1;
            ext_spike_threshold <= global_threshold;
            for (i = 0; i < 5; i = i + 1) begin
                @(posedge clk);
                #1;
                if (!ext_spike_ready)
                    ready_blocked_seen = 1;
                if (!ext_spike_ready && u_dut.fifo_count != fifo_count_before)
                    write_while_not_ready = 1;
            end
            @(negedge clk);
            ext_spike_valid <= 0;
            wait_commit_done;
            check(21, "Commit-low ready prevents external FIFO write",
                  ready_blocked_seen && !write_while_not_ready &&
                  u_dut.fifo_count == fifo_count_before);
        end

        // TEST 22: Clear also blocks external writes through the same ready path.
        $display("\n--- Test 22: External Write Matches Ready During Clear ---");
        begin : t22
            integer i;
            integer timeout;
            reg write_while_not_ready;
            reg ready_blocked_seen;
            integer fifo_count_before;

            do_reset;
            wait_idle;
            @(posedge clk);
            clear_start <= 1;
            @(posedge clk);
            clear_start <= 0;

            timeout = 0;
            while (!clear_busy && timeout < 1000) begin
                @(posedge clk);
                timeout = timeout + 1;
            end

            fifo_count_before = u_dut.fifo_count;
            write_while_not_ready = 0;
            ready_blocked_seen = 0;

            @(negedge clk);
            ext_spike_valid <= 1;
            ext_spike_dest_id <= 7'd32;
            ext_spike_weight <= 8'd1;
            ext_spike_exc_inh <= 1'b1;
            ext_spike_threshold <= global_threshold;
            for (i = 0; i < 5; i = i + 1) begin
                @(posedge clk);
                #1;
                if (!ext_spike_ready)
                    ready_blocked_seen = 1;
                if (!ext_spike_ready && u_dut.fifo_count != fifo_count_before)
                    write_while_not_ready = 1;
            end
            @(negedge clk);
            ext_spike_valid <= 0;
            wait_clear_done;
            check(22, "Clear-low ready prevents external FIFO write",
                  ready_blocked_seen && !write_while_not_ready &&
                  u_dut.fifo_count == fifo_count_before);
        end

        $display("\n=========================================================");
        $display("  SpikeMold Coregroup TB: %0d PASS, %0d FAIL (of %0d)",
                 pass_count, fail_count, pass_count + fail_count);
        $display("=========================================================");
        if (fail_count > 0) $finish(1);
        else $finish(0);
    end

    initial begin
        #100000000;
        $display("[ERROR] Global timeout!");
        $finish(2);
    end
endmodule
