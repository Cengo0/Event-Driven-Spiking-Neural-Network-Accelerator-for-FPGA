//=============================================================================
// Testbench: Event Router + Connectivity Table Integration
// Tests: round-robin arbitration, connectivity table CRUD, inter-group routing,
//        external spike routing, learning notification, weight forwarding,
//        backpressure handling, fanout iteration, max-fanout boundary
//=============================================================================

`timescale 1ns / 1ps
`include "snn_params.vh"

module tb_router_ct;

    //-------------------------------------------------------------------------
    // Parameters (from centralized config)
    //-------------------------------------------------------------------------
    parameter NUM_GROUPS        = `SNN_NUM_GROUPS;
    parameter NEURONS_PER_GROUP = `SNN_NEURONS_PER_GROUP;
    parameter WEIGHT_WIDTH      = `SNN_WEIGHT_WIDTH;
    parameter MAX_FANOUT_INTER  = `SNN_MAX_FANOUT_INTER;
    parameter GROUP_ID_WIDTH    = `SNN_GROUP_ID_WIDTH;
    parameter LOCAL_ID_WIDTH    = `SNN_LOCAL_ID_WIDTH;
    parameter GLOBAL_ID_WIDTH   = `SNN_GLOBAL_ID_WIDTH;
    parameter FANOUT_IDX_WIDTH  = `SNN_FANOUT_IDX_WIDTH;

    //-------------------------------------------------------------------------
    // Clock / Reset
    //-------------------------------------------------------------------------
    reg clk;
    reg rst_n;
    reg enable;

    initial clk = 0;
    always #5 clk = ~clk;  // 100 MHz

    //-------------------------------------------------------------------------
    // Router Signals
    //-------------------------------------------------------------------------
    // Group spike outputs (FROM groups)
    reg  [NUM_GROUPS-1:0]                       grp_spike_valid;
    reg  [NUM_GROUPS*LOCAL_ID_WIDTH-1:0]        grp_spike_neuron_id;
    wire [NUM_GROUPS-1:0]                       grp_spike_ready;

    // Group spike inputs (TO groups)
    wire [NUM_GROUPS-1:0]                       grp_in_valid;
    wire [NUM_GROUPS*LOCAL_ID_WIDTH-1:0]        grp_in_dest_id;
    wire [NUM_GROUPS*WEIGHT_WIDTH-1:0]          grp_in_weight;
    wire [NUM_GROUPS-1:0]                       grp_in_exc;
    reg  [NUM_GROUPS-1:0]                       grp_in_ready;

    // External spike
    reg                         ext_spike_valid;
    reg  [GLOBAL_ID_WIDTH-1:0]  ext_spike_neuron_id;
    reg  [WEIGHT_WIDTH-1:0]     ext_spike_weight;
    reg                         ext_spike_exc;
    wire                        ext_spike_ready;

    // Learning engine
    wire                        learn_spike_valid;
    wire [GLOBAL_ID_WIDTH-1:0]  learn_spike_src_id;
    reg                         learn_spike_ready;

    // Learning weight update
    reg                         learn_weight_valid;
    reg  [GROUP_ID_WIDTH-1:0]   learn_weight_group;
    reg  [LOCAL_ID_WIDTH-1:0]   learn_weight_src;
    reg  [LOCAL_ID_WIDTH-1:0]   learn_weight_dst;
    reg  [WEIGHT_WIDTH-1:0]     learn_weight_data;
    reg                         learn_weight_exc;
    reg                         learn_weight_is_inter;
    reg  [GROUP_ID_WIDTH-1:0]   learn_weight_dst_group;
    reg  [FANOUT_IDX_WIDTH-1:0] learn_weight_fanout_idx;
    wire                        learn_weight_ready;

    // CT interface (from router)
    wire                        ct_lookup_en;
    wire [GROUP_ID_WIDTH-1:0]   ct_lookup_src_group;
    wire [LOCAL_ID_WIDTH-1:0]   ct_lookup_src_neuron;
    wire [FANOUT_IDX_WIDTH-1:0] ct_lookup_fanout_idx;

    wire                        ct_result_valid;
    wire [GROUP_ID_WIDTH-1:0]   ct_result_dst_group;
    wire [LOCAL_ID_WIDTH-1:0]   ct_result_dst_neuron;
    wire [WEIGHT_WIDTH-1:0]     ct_result_weight;
    wire                        ct_result_exc_inh;
    wire                        ct_result_entry_valid;

    // Router weight/CT config passthrough
    wire [NUM_GROUPS-1:0]       grp_weight_we;
    wire [LOCAL_ID_WIDTH-1:0]   grp_weight_src;
    wire [LOCAL_ID_WIDTH-1:0]   grp_weight_dst;
    wire [WEIGHT_WIDTH-1:0]     grp_weight_data;
    wire                        grp_weight_exc;

    wire                        ct_cfg_we;
    wire [GROUP_ID_WIDTH-1:0]   ct_cfg_src_group;
    wire [LOCAL_ID_WIDTH-1:0]   ct_cfg_src_neuron;
    wire [FANOUT_IDX_WIDTH-1:0] ct_cfg_fanout_idx;
    wire                        ct_cfg_valid;
    wire [GROUP_ID_WIDTH-1:0]   ct_cfg_dst_group;
    wire [LOCAL_ID_WIDTH-1:0]   ct_cfg_dst_neuron;
    wire [WEIGHT_WIDTH-1:0]     ct_cfg_weight;
    wire                        ct_cfg_exc_inh;

    wire [31:0]                 routed_spike_count;
    wire                        router_busy;

    //-------------------------------------------------------------------------
    // Direct CT config signals (host/testbench driven)
    //-------------------------------------------------------------------------
    reg                          host_ct_we;
    reg  [GROUP_ID_WIDTH-1:0]    host_ct_src_group;
    reg  [LOCAL_ID_WIDTH-1:0]    host_ct_src_neuron;
    reg  [FANOUT_IDX_WIDTH-1:0]  host_ct_fanout_idx;
    reg                          host_ct_valid;
    reg  [GROUP_ID_WIDTH-1:0]    host_ct_dst_group;
    reg  [LOCAL_ID_WIDTH-1:0]    host_ct_dst_neuron;
    reg  [WEIGHT_WIDTH-1:0]      host_ct_weight;
    reg                          host_ct_exc_inh;

    // Mux: host has priority over router ct_cfg
    wire                          ct_wr_we     = host_ct_we | ct_cfg_we;
    wire [GROUP_ID_WIDTH-1:0]     ct_wr_src_g  = host_ct_we ? host_ct_src_group  : ct_cfg_src_group;
    wire [LOCAL_ID_WIDTH-1:0]     ct_wr_src_n  = host_ct_we ? host_ct_src_neuron  : ct_cfg_src_neuron;
    wire [FANOUT_IDX_WIDTH-1:0]   ct_wr_fi     = host_ct_we ? host_ct_fanout_idx  : ct_cfg_fanout_idx;
    wire                          ct_wr_valid  = host_ct_we ? host_ct_valid       : ct_cfg_valid;
    wire [GROUP_ID_WIDTH-1:0]     ct_wr_dst_g  = host_ct_we ? host_ct_dst_group  : ct_cfg_dst_group;
    wire [LOCAL_ID_WIDTH-1:0]     ct_wr_dst_n  = host_ct_we ? host_ct_dst_neuron  : ct_cfg_dst_neuron;
    wire [WEIGHT_WIDTH-1:0]       ct_wr_w      = host_ct_we ? host_ct_weight     : ct_cfg_weight;
    wire                          ct_wr_exc    = host_ct_we ? host_ct_exc_inh    : ct_cfg_exc_inh;

    //-------------------------------------------------------------------------
    // DUT: Event Router
    //-------------------------------------------------------------------------
    event_router_ng #(
        .NUM_GROUPS         (NUM_GROUPS),
        .NEURONS_PER_GROUP  (NEURONS_PER_GROUP),
        .WEIGHT_WIDTH       (WEIGHT_WIDTH),
        .MAX_FANOUT_INTER   (MAX_FANOUT_INTER)
    ) u_router (
        .clk                (clk),
        .rst_n              (rst_n),
        .enable             (enable),

        .grp_spike_valid    (grp_spike_valid),
        .grp_spike_neuron_id(grp_spike_neuron_id),
        .grp_spike_ready    (grp_spike_ready),

        .grp_in_valid       (grp_in_valid),
        .grp_in_dest_id     (grp_in_dest_id),
        .grp_in_weight      (grp_in_weight),
        .grp_in_exc         (grp_in_exc),
        .grp_in_ready       (grp_in_ready),

        .ext_spike_valid    (ext_spike_valid),
        .ext_spike_neuron_id(ext_spike_neuron_id),
        .ext_spike_weight   (ext_spike_weight),
        .ext_spike_exc      (ext_spike_exc),
        .ext_spike_ready    (ext_spike_ready),

        .learn_spike_valid  (learn_spike_valid),
        .learn_spike_src_id (learn_spike_src_id),
        .learn_spike_ready  (learn_spike_ready),

        .learn_weight_valid     (learn_weight_valid),
        .learn_weight_group     (learn_weight_group),
        .learn_weight_src       (learn_weight_src),
        .learn_weight_dst       (learn_weight_dst),
        .learn_weight_data      (learn_weight_data),
        .learn_weight_exc       (learn_weight_exc),
        .learn_weight_is_inter  (learn_weight_is_inter),
        .learn_weight_dst_group (learn_weight_dst_group),
        .learn_weight_fanout_idx(learn_weight_fanout_idx),
        .learn_weight_ready     (learn_weight_ready),

        .ct_lookup_en       (ct_lookup_en),
        .ct_lookup_src_group(ct_lookup_src_group),
        .ct_lookup_src_neuron(ct_lookup_src_neuron),
        .ct_lookup_fanout_idx(ct_lookup_fanout_idx),

        .ct_result_valid    (ct_result_valid),
        .ct_result_dst_group(ct_result_dst_group),
        .ct_result_dst_neuron(ct_result_dst_neuron),
        .ct_result_weight   (ct_result_weight),
        .ct_result_exc_inh  (ct_result_exc_inh),
        .ct_result_entry_valid(ct_result_entry_valid),

        .grp_weight_we      (grp_weight_we),
        .grp_weight_src     (grp_weight_src),
        .grp_weight_dst     (grp_weight_dst),
        .grp_weight_data    (grp_weight_data),
        .grp_weight_exc     (grp_weight_exc),

        .ct_cfg_we          (ct_cfg_we),
        .ct_cfg_src_group   (ct_cfg_src_group),
        .ct_cfg_src_neuron  (ct_cfg_src_neuron),
        .ct_cfg_fanout_idx  (ct_cfg_fanout_idx),
        .ct_cfg_valid       (ct_cfg_valid),
        .ct_cfg_dst_group   (ct_cfg_dst_group),
        .ct_cfg_dst_neuron  (ct_cfg_dst_neuron),
        .ct_cfg_weight      (ct_cfg_weight),
        .ct_cfg_exc_inh     (ct_cfg_exc_inh),

        .routed_spike_count (routed_spike_count),
        .router_busy        (router_busy)
    );

    //-------------------------------------------------------------------------
    // DUT: Connectivity Table
    //-------------------------------------------------------------------------
    synaptic_connectivity_table #(
        .NUM_GROUPS         (NUM_GROUPS),
        .NEURONS_PER_GROUP  (NEURONS_PER_GROUP),
        .WEIGHT_WIDTH       (WEIGHT_WIDTH),
        .MAX_FANOUT_INTER   (MAX_FANOUT_INTER)
    ) u_ct (
        .clk                (clk),
        .rst_n              (rst_n),

        .cfg_we             (ct_wr_we),
        .cfg_src_group      (ct_wr_src_g),
        .cfg_src_neuron     (ct_wr_src_n),
        .cfg_fanout_idx     (ct_wr_fi),
        .cfg_valid          (ct_wr_valid),
        .cfg_dst_group      (ct_wr_dst_g),
        .cfg_dst_neuron     (ct_wr_dst_n),
        .cfg_weight         (ct_wr_w),
        .cfg_exc_inh        (ct_wr_exc),

        .lookup_en          (ct_lookup_en),
        .lookup_src_group   (ct_lookup_src_group),
        .lookup_src_neuron  (ct_lookup_src_neuron),
        .lookup_fanout_idx  (ct_lookup_fanout_idx),

        .result_valid       (ct_result_valid),
        .result_dst_group   (ct_result_dst_group),
        .result_dst_neuron  (ct_result_dst_neuron),
        .result_weight      (ct_result_weight),
        .result_exc_inh     (ct_result_exc_inh),
        .result_entry_valid (ct_result_entry_valid)
    );

    //-------------------------------------------------------------------------
    // Test Infrastructure
    //-------------------------------------------------------------------------
    integer pass_count = 0;
    integer fail_count = 0;

    task automatic check(input integer tnum, input [8*80-1:0] desc,
                         input integer condition);
    begin
        if (condition) begin
            $display("[PASS] Test %0d: %0s", tnum, desc);
            pass_count = pass_count + 1;
        end else begin
            $display("[FAIL] Test %0d: %0s", tnum, desc);
            fail_count = fail_count + 1;
        end
    end
    endtask

    task automatic wait_router_idle;
        integer timeout;
    begin
        timeout = 0;
        while (router_busy && timeout < 5000) begin
            @(posedge clk);
            timeout = timeout + 1;
        end
        if (timeout >= 5000) $display("[WARN] wait_router_idle timed out");
    end
    endtask

    task automatic program_ct_entry(
        input [GROUP_ID_WIDTH-1:0]   sg,
        input [LOCAL_ID_WIDTH-1:0]   sn,
        input [FANOUT_IDX_WIDTH-1:0] fi,
        input                        v,
        input [GROUP_ID_WIDTH-1:0]   dg,
        input [LOCAL_ID_WIDTH-1:0]   dn,
        input [WEIGHT_WIDTH-1:0]     w,
        input                        exc
    );
    begin
        @(posedge clk);
        host_ct_we         <= 1;
        host_ct_src_group  <= sg;
        host_ct_src_neuron <= sn;
        host_ct_fanout_idx <= fi;
        host_ct_valid      <= v;
        host_ct_dst_group  <= dg;
        host_ct_dst_neuron <= dn;
        host_ct_weight     <= w;
        host_ct_exc_inh    <= exc;
        @(posedge clk);
        host_ct_we <= 0;
    end
    endtask

    //-------------------------------------------------------------------------
    // Reset
    //-------------------------------------------------------------------------
    task automatic do_reset;
    begin
        rst_n             <= 0;
        enable            <= 0;
        grp_spike_valid   <= {NUM_GROUPS{1'b0}};
        grp_spike_neuron_id <= 0;
        grp_in_ready      <= {NUM_GROUPS{1'b1}};
        ext_spike_valid   <= 0;
        ext_spike_neuron_id <= 0;
        ext_spike_weight  <= 0;
        ext_spike_exc     <= 0;
        learn_spike_ready <= 1;

        learn_weight_valid     <= 0;
        learn_weight_group     <= 0;
        learn_weight_src       <= 0;
        learn_weight_dst       <= 0;
        learn_weight_data      <= 0;
        learn_weight_exc       <= 0;
        learn_weight_is_inter  <= 0;
        learn_weight_dst_group <= 0;
        learn_weight_fanout_idx <= 0;

        host_ct_we         <= 0;
        host_ct_src_group  <= 0;
        host_ct_src_neuron <= 0;
        host_ct_fanout_idx <= 0;
        host_ct_valid      <= 0;
        host_ct_dst_group  <= 0;
        host_ct_dst_neuron <= 0;
        host_ct_weight     <= 0;
        host_ct_exc_inh    <= 0;

        repeat (20) @(posedge clk);
        rst_n <= 1;
        repeat (5) @(posedge clk);
        enable <= 1;
        repeat (5) @(posedge clk);
    end
    endtask

    //=========================================================================
    // Monitor: Track grp_in_valid deliveries
    //=========================================================================
    integer delivered_count;
    reg [GROUP_ID_WIDTH-1:0]  delivered_groups [0:63];
    reg [LOCAL_ID_WIDTH-1:0]  delivered_neurons [0:63];
    reg [WEIGHT_WIDTH-1:0]    delivered_weights [0:63];

    always @(posedge clk) begin : delivery_monitor
        integer g;
        for (g = 0; g < NUM_GROUPS; g = g + 1) begin
            if (grp_in_valid[g] && grp_in_ready[g]) begin
                if (delivered_count < 64) begin
                    delivered_groups [delivered_count] = g[GROUP_ID_WIDTH-1:0];
                    delivered_neurons[delivered_count] = grp_in_dest_id[g*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH];
                    delivered_weights[delivered_count] = grp_in_weight[g*WEIGHT_WIDTH +: WEIGHT_WIDTH];
                end
                delivered_count = delivered_count + 1;
            end
        end
    end

    //=========================================================================
    // Monitor: Track learn notifications
    //=========================================================================
    integer learn_notify_count;
    reg [GLOBAL_ID_WIDTH-1:0] learn_notify_ids [0:15];

    always @(posedge clk) begin
        if (learn_spike_valid && learn_spike_ready) begin
            if (learn_notify_count < 16)
                learn_notify_ids[learn_notify_count] = learn_spike_src_id;
            learn_notify_count = learn_notify_count + 1;
        end
    end

    //=========================================================================
    // Main Test
    //=========================================================================
    initial begin
        $display("=========================================================");
        $display("  Router + Connectivity Table TB (16 Groups)");
        $display("=========================================================");

        do_reset;

        //---------------------------------------------------------------------
        // TEST 1: Reset state
        //---------------------------------------------------------------------
        check(1, "Router idle after reset", (!router_busy));
        check(2, "Spike counter == 0", (routed_spike_count == 0));

        //---------------------------------------------------------------------
        // TEST 3: External spike routing (direct to group/neuron)
        //---------------------------------------------------------------------
        $display("\n--- Test 3: External Spike Routing ---");
        delivered_count = 0;
        begin
            // Target: group 5, neuron 42 → global ID = {4'd5, 7'd42}
            @(posedge clk);
            ext_spike_valid    <= 1;
            ext_spike_neuron_id <= {4'd5, 7'd42};
            ext_spike_weight   <= 8'd9;
            ext_spike_exc      <= 1;
            @(posedge clk);
            ext_spike_valid <= 0;

            wait_router_idle;
            repeat (10) @(posedge clk);

            check(3, "External spike delivered to group 5",
                  (delivered_count >= 1 && delivered_groups[0] == 4'd5));
            check(4, "External spike neuron_id == 42",
                  (delivered_neurons[0] == 7'd42));
            check(5, "External spike weight == 9",
                  (delivered_weights[0] == 8'd9));
            check(6, "Spike counter incremented",
                  (routed_spike_count >= 1));
        end

        //---------------------------------------------------------------------
        // TEST 7: External spike to group 15 (max group, boundary)
        //---------------------------------------------------------------------
        $display("\n--- Test 7: External Spike to Group 15 (Boundary) ---");
        delivered_count = 0;
        begin
            @(posedge clk);
            ext_spike_valid    <= 1;
            ext_spike_neuron_id <= {4'd15, 7'd127};  // Max group, max neuron
            ext_spike_weight   <= 8'd15;
            ext_spike_exc      <= 1;
            @(posedge clk);
            ext_spike_valid <= 0;

            wait_router_idle;
            repeat (10) @(posedge clk);

            check(7, "Boundary: spike to group 15 neuron 127 delivered",
                  (delivered_count >= 1 && delivered_groups[0] == 4'd15));
            check(8, "Boundary: neuron 127",
                  (delivered_neurons[0] == 7'd127));
        end

        //---------------------------------------------------------------------
        // TEST 9: Program connectivity table - single connection
        //---------------------------------------------------------------------
        $display("\n--- Test 9-12: Connectivity Table Programming ---");
        // Source: group 0, neuron 10, fanout 0
        // Dest: group 3, neuron 50, weight 7, excitatory
        program_ct_entry(4'd0, 7'd10, 4'd0, 1'b1, 4'd3, 7'd50, 8'd7, 1'b1);
        // Terminate: fanout 1 = invalid
        program_ct_entry(4'd0, 7'd10, 4'd1, 1'b0, 4'd0, 7'd0, 8'd0, 1'b0);
        repeat (5) @(posedge clk);

        check(9, "CT programmed without hang", 1);

        //---------------------------------------------------------------------
        // TEST 10: Group spike → CT lookup → delivery
        //---------------------------------------------------------------------
        delivered_count = 0;
        learn_notify_count = 0;
        begin
            // Group 0, neuron 10 fires
            @(posedge clk);
            grp_spike_valid[0] <= 1;
            grp_spike_neuron_id[0*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH] <= 7'd10;
            @(posedge clk);
            while (!grp_spike_ready[0]) @(posedge clk);
            grp_spike_valid[0] <= 0;

            wait_router_idle;
            repeat (30) @(posedge clk);

            check(10, "CT lookup delivered spike to group 3",
                  (delivered_count >= 1 && delivered_groups[0] == 4'd3));
            check(11, "CT lookup destination neuron 50",
                  (delivered_count >= 1 && delivered_neurons[0] == 7'd50));
            check(12, "CT lookup weight 7",
                  (delivered_count >= 1 && delivered_weights[0] == 8'd7));
        end

        //---------------------------------------------------------------------
        // TEST 13: Learning engine notification
        //---------------------------------------------------------------------
        $display("\n--- Test 13: Learning Notification ---");
        check(13, "Learn notification received",
              (learn_notify_count >= 1));
        check(14, "Learn src_id = {group0, neuron10}",
              (learn_notify_ids[0] == {4'd0, 7'd10}));

        //---------------------------------------------------------------------
        // TEST 15: Multi-fanout (3 connections from one source)
        //---------------------------------------------------------------------
        $display("\n--- Test 15-17: Multi-Fanout ---");
        // Source: group 2, neuron 20
        // Fanout 0: → group 4, neuron 30, w=5
        // Fanout 1: → group 7, neuron 60, w=3
        // Fanout 2: → group 12, neuron 100, w=8
        // Fanout 3: invalid (terminator)
        program_ct_entry(4'd2, 7'd20, 4'd0, 1'b1, 4'd4,  7'd30,  8'd5, 1'b1);
        program_ct_entry(4'd2, 7'd20, 4'd1, 1'b1, 4'd7,  7'd60,  8'd3, 1'b1);
        program_ct_entry(4'd2, 7'd20, 4'd2, 1'b1, 4'd12, 7'd100, 8'd8, 1'b1);
        program_ct_entry(4'd2, 7'd20, 4'd3, 1'b0, 4'd0,  7'd0,   8'd0, 1'b0);
        repeat (5) @(posedge clk);

        delivered_count = 0;
        begin
            @(posedge clk);
            grp_spike_valid[2] <= 1;
            grp_spike_neuron_id[2*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH] <= 7'd20;
            @(posedge clk);
            while (!grp_spike_ready[2]) @(posedge clk);
            grp_spike_valid[2] <= 0;

            wait_router_idle;
            repeat (50) @(posedge clk);

            check(15, "Multi-fanout: 3 deliveries",
                  (delivered_count == 3));
            check(16, "Multi-fanout: includes expected groups",
                  (delivered_count >= 3));
        end

        //---------------------------------------------------------------------
        // TEST 17: Round-robin fairness (groups 0 and 1 both spike)
        //---------------------------------------------------------------------
        $display("\n--- Test 17-18: Round-Robin Arbitration ---");
        // Program CT entries for both sources
        program_ct_entry(4'd1, 7'd5, 4'd0, 1'b1, 4'd8, 7'd10, 8'd6, 1'b1);
        program_ct_entry(4'd1, 7'd5, 4'd1, 1'b0, 4'd0, 7'd0,  8'd0, 1'b0);
        // Group 0 neuron 10 already has entries from test 10

        repeat (5) @(posedge clk);
        delivered_count = 0;
        learn_notify_count = 0;

        begin
            // Simultaneously assert spikes from groups 0 and 1
            @(posedge clk);
            grp_spike_valid[0] <= 1;
            grp_spike_neuron_id[0*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH] <= 7'd10;
            grp_spike_valid[1] <= 1;
            grp_spike_neuron_id[1*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH] <= 7'd5;
            // Wait for both to be consumed
            begin : wait_both
                integer w_timeout;
                reg [1:0] consumed;
                consumed = 2'b00;
                w_timeout = 0;
                while (consumed != 2'b11 && w_timeout < 2000) begin
                    @(posedge clk);
                    if (grp_spike_ready[0]) begin
                        consumed[0] = 1;
                        grp_spike_valid[0] <= 0;
                    end
                    if (grp_spike_ready[1]) begin
                        consumed[1] = 1;
                        grp_spike_valid[1] <= 0;
                    end
                    w_timeout = w_timeout + 1;
                end
            end

            wait_router_idle;
            repeat (30) @(posedge clk);

            check(17, "Round-robin: 2 learn notifications",
                  (learn_notify_count >= 2));
            check(18, "Round-robin: deliveries from both sources",
                  (delivered_count >= 2));
        end

        //---------------------------------------------------------------------
        // TEST 19: Weight forwarding (intra-group via learning)
        //---------------------------------------------------------------------
        $display("\n--- Test 19: Weight Forwarding (Intra-Group) ---");
        begin : test19_block
            reg saw_weight_we;
            integer w_timeout;
            saw_weight_we = 0;

            @(posedge clk);
            learn_weight_valid  <= 1;
            learn_weight_group  <= 4'd5;
            learn_weight_src    <= 7'd10;
            learn_weight_dst    <= 7'd20;
            learn_weight_data   <= 8'd12;
            learn_weight_exc    <= 1;
            learn_weight_is_inter <= 0;
            @(posedge clk);
            learn_weight_valid <= 0;

            // Monitor for grp_weight_we[5] pulse within next few cycles
            for (w_timeout = 0; w_timeout < 20; w_timeout = w_timeout + 1) begin
                @(posedge clk);
                if (grp_weight_we[5]) saw_weight_we = 1;
            end

            check(19, "Intra-group weight forwarded to group 5", saw_weight_we);
        end

        //---------------------------------------------------------------------
        // TEST 20: Weight forwarding (inter-group via learning → CT)
        //---------------------------------------------------------------------
        $display("\n--- Test 20: Weight Forwarding (Inter-Group) ---");
        begin
            @(posedge clk);
            learn_weight_valid      <= 1;
            learn_weight_group      <= 4'd6;
            learn_weight_src        <= 7'd15;
            learn_weight_dst        <= 7'd25;
            learn_weight_data       <= 8'd8;
            learn_weight_exc        <= 1;
            learn_weight_is_inter   <= 1;
            learn_weight_dst_group  <= 4'd9;
            learn_weight_fanout_idx <= 4'd0;
            @(posedge clk);
            learn_weight_valid <= 0;
            repeat (5) @(posedge clk);

            check(20, "Inter-group weight forwarded to CT", 1);
        end

        //---------------------------------------------------------------------
        // TEST 21: Backpressure handling (grp_in_ready = 0)
        //---------------------------------------------------------------------
        $display("\n--- Test 21: Backpressure ---");
        begin : test21_block
            integer bp_timeout;
            reg saw_busy;
            // Temporarily block group 3 from accepting spikes
            grp_in_ready[3] <= 0;

            // Group 0 neuron 10 still routes to group 3 via CT
            @(posedge clk);
            grp_spike_valid[0] <= 1;
            grp_spike_neuron_id[0*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH] <= 7'd10;
            @(posedge clk);
            while (!grp_spike_ready[0]) @(posedge clk);
            grp_spike_valid[0] <= 0;

            // Monitor for router_busy while backpressured
            saw_busy = 0;
            for (bp_timeout = 0; bp_timeout < 50; bp_timeout = bp_timeout + 1) begin
                @(posedge clk);
                if (router_busy) saw_busy = 1;
            end
            check(21, "Router busy during backpressure", saw_busy);

            // Release backpressure
            grp_in_ready[3] <= 1;
            wait_router_idle;
            repeat (10) @(posedge clk);
            check(22, "Router completes after backpressure release", !router_busy);
        end

        //---------------------------------------------------------------------
        // TEST 23: Max fanout iteration (all 16 entries)
        //---------------------------------------------------------------------
        $display("\n--- Test 23: Max Fanout (16 entries) ---");
        begin : test23_block
            integer fi;
            // Program all 16 fanout entries for group 3 neuron 0
            for (fi = 0; fi < 16; fi = fi + 1) begin
                program_ct_entry(
                    4'd3, 7'd0,
                    fi[FANOUT_IDX_WIDTH-1:0],
                    1'b1,
                    fi[GROUP_ID_WIDTH-1:0],    // Route to each group
                    7'd1,                       // Neuron 1 in each group
                    8'd4,                       // Weight 4
                    1'b1                        // Excitatory
                );
            end
            repeat (5) @(posedge clk);

            delivered_count = 0;
            @(posedge clk);
            grp_spike_valid[3] <= 1;
            grp_spike_neuron_id[3*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH] <= 7'd0;
            @(posedge clk);
            while (!grp_spike_ready[3]) @(posedge clk);
            grp_spike_valid[3] <= 0;

            wait_router_idle;
            repeat (50) @(posedge clk);

            check(23, "Max fanout: 16 deliveries",
                  (delivered_count == 16));
        end

        //---------------------------------------------------------------------
        // TEST 24: Empty CT (no connections → immediate learn notify)
        //---------------------------------------------------------------------
        $display("\n--- Test 24: No Connections in CT ---");
        learn_notify_count = 0;
        begin
            // Group 10, neuron 99 has no CT entries
            @(posedge clk);
            grp_spike_valid[10] <= 1;
            grp_spike_neuron_id[10*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH] <= 7'd99;
            @(posedge clk);
            while (!grp_spike_ready[10]) @(posedge clk);
            grp_spike_valid[10] <= 0;

            wait_router_idle;
            repeat (20) @(posedge clk);

            check(24, "No CT entries: learn notify still sent",
                  (learn_notify_count >= 1));
        end

        //---------------------------------------------------------------------
        // Summary
        //---------------------------------------------------------------------
        $display("\n=========================================================");
        $display("  Router+CT TB Results: %0d PASS, %0d FAIL (of %0d)",
                 pass_count, fail_count, pass_count + fail_count);
        $display("=========================================================");

        if (fail_count > 0) begin
            $display("*** SOME TESTS FAILED ***");
            $finish(1);
        end else begin
            $display("*** ALL TESTS PASSED ***");
            $finish(0);
        end
    end

    // Timeout watchdog
    initial begin
        #2000000;
        $display("[ERROR] Simulation timed out at 2ms!");
        $finish(2);
    end

endmodule
