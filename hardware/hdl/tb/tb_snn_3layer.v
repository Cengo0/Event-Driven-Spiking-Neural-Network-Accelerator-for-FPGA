//=============================================================================
// Testbench: 3-Layer SNN Hardware Pipeline (Group 0 -> Group 1 -> Group 2)
// Tests:
//   1. Edge detector turns HLS level valid signal into a single pulse
//   2. Group 0 (relay) fires immediately on external spike
//   3. Event router routes Group 0 spike to Group 1 via Connectivity Table
//   4. Group 1 (hidden) integrates and fires
//   5. Event router routes Group 1 spike to Group 2 via Connectivity Table
//   6. Group 2 (output) fires
//   7. Output Spike FIFO captures Group 2 class spike and asserts rtl_spike_out_valid
//   8. HLS toggle-ack pops FIFO cleanly
//=============================================================================

`timescale 1ns / 1ps
`include "snn_params.vh"

module tb_snn_3layer;

    parameter NUM_GROUPS        = `SNN_NUM_GROUPS;          // 3
    parameter NEURONS_PER_GROUP = `SNN_NEURONS_PER_GROUP;  // 256
    parameter WEIGHT_WIDTH      = `SNN_WEIGHT_WIDTH;        // 8
    parameter MAX_FANOUT_INTER  = `SNN_MAX_FANOUT_INTER;    // 256
    parameter DATA_WIDTH        = `SNN_DATA_WIDTH;          // 16
    parameter THRESHOLD_WIDTH   = `SNN_THRESHOLD_WIDTH;     // 16
    parameter LEAK_WIDTH        = `SNN_LEAK_WIDTH;          // 8
    parameter REFRAC_WIDTH      = `SNN_REFRAC_WIDTH;        // 8
    parameter SPIKE_BUFFER_DEPTH= `SNN_SPIKE_BUFFER_DEPTH;  // 64
    parameter GROUP_ID_WIDTH    = `SNN_GROUP_ID_WIDTH;      // 2
    parameter LOCAL_ID_WIDTH    = `SNN_LOCAL_ID_WIDTH;      // 8
    parameter GLOBAL_ID_WIDTH   = `SNN_GLOBAL_ID_WIDTH;     // 10
    parameter FANOUT_IDX_WIDTH  = `SNN_FANOUT_IDX_WIDTH;    // 8
    parameter HLS_NEURON_ID_WIDTH = `SNN_HLS_NEURON_ID_WIDTH; // 10
    parameter HLS_WEIGHT_WIDTH  = `SNN_HLS_WEIGHT_WIDTH;    // 8

    reg clk;
    reg rst_n;
    reg enable;

    initial clk = 0;
    always #5 clk = ~clk;  // 100 MHz

    // Router <-> Core Group wires
    wire [NUM_GROUPS-1:0]                       grp_spike_valid;
    wire [NUM_GROUPS*LOCAL_ID_WIDTH-1:0]        grp_spike_neuron_id;
    wire [NUM_GROUPS-1:0]                       grp_spike_ready;

    wire [NUM_GROUPS-1:0]                       grp_in_valid;
    wire [NUM_GROUPS*LOCAL_ID_WIDTH-1:0]        grp_in_dest_id;
    wire [NUM_GROUPS*WEIGHT_WIDTH-1:0]          grp_in_weight;
    wire [NUM_GROUPS-1:0]                       grp_in_exc;
    wire [NUM_GROUPS-1:0]                       grp_in_ready;

    wire [NUM_GROUPS-1:0]                       grp_busy;
    wire [NUM_GROUPS*16-1:0]                    grp_spike_count;

    // Router <-> CT wires
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

    // CT programming wires
    reg                         host_ct_we;
    reg  [GROUP_ID_WIDTH-1:0]   host_ct_src_group;
    reg  [LOCAL_ID_WIDTH-1:0]   host_ct_src_neuron;
    reg  [FANOUT_IDX_WIDTH-1:0] host_ct_fanout_idx;
    reg                         host_ct_valid;
    reg  [GROUP_ID_WIDTH-1:0]   host_ct_dst_group;
    reg  [LOCAL_ID_WIDTH-1:0]   host_ct_dst_neuron;
    reg  [WEIGHT_WIDTH-1:0]     host_ct_weight;
    reg                         host_ct_exc_inh;

    wire                        ct_cfg_we;
    wire [GROUP_ID_WIDTH-1:0]   ct_cfg_src_group;
    wire [LOCAL_ID_WIDTH-1:0]   ct_cfg_src_neuron;
    wire [FANOUT_IDX_WIDTH-1:0] ct_cfg_fanout_idx;
    wire                        ct_cfg_valid_bit;
    wire [GROUP_ID_WIDTH-1:0]   ct_cfg_dst_group;
    wire [LOCAL_ID_WIDTH-1:0]   ct_cfg_dst_neuron;
    wire [WEIGHT_WIDTH-1:0]     ct_cfg_weight;
    wire                        ct_cfg_exc_inh;

    wire ct_mux_we     = host_ct_we | ct_cfg_we;
    wire [GROUP_ID_WIDTH-1:0]   ct_mux_sg  = host_ct_we ? host_ct_src_group  : ct_cfg_src_group;
    wire [LOCAL_ID_WIDTH-1:0]   ct_mux_sn  = host_ct_we ? host_ct_src_neuron : ct_cfg_src_neuron;
    wire [FANOUT_IDX_WIDTH-1:0] ct_mux_fi  = host_ct_we ? host_ct_fanout_idx : ct_cfg_fanout_idx;
    wire                        ct_mux_v   = host_ct_we ? host_ct_valid      : ct_cfg_valid_bit;
    wire [GROUP_ID_WIDTH-1:0]   ct_mux_dg  = host_ct_we ? host_ct_dst_group  : ct_cfg_dst_group;
    wire [LOCAL_ID_WIDTH-1:0]   ct_mux_dn  = host_ct_we ? host_ct_dst_neuron : ct_cfg_dst_neuron;
    wire [WEIGHT_WIDTH-1:0]     ct_mux_w   = host_ct_we ? host_ct_weight     : ct_cfg_weight;
    wire                        ct_mux_exc = host_ct_we ? host_ct_exc_inh    : ct_cfg_exc_inh;

    // HLS Interface Signals
    reg                             hls_spike_out_valid;
    reg  [HLS_NEURON_ID_WIDTH-1:0]  hls_spike_out_neuron_id;
    reg  [HLS_WEIGHT_WIDTH-1:0]     hls_spike_out_weight;
    wire                            rtl_spike_in_ready;

    wire                            rtl_spike_out_valid;
    wire [HLS_NEURON_ID_WIDTH-1:0]  rtl_spike_out_neuron_id;
    wire [HLS_WEIGHT_WIDTH-1:0]     rtl_spike_out_weight;
    reg                             hls_spike_in_ready;

    // HLS ap_none pulse edge detector
    reg                             hls_spike_valid_d;
    reg [HLS_NEURON_ID_WIDTH-1:0]  hls_spike_nid_d;
    reg [HLS_WEIGHT_WIDTH-1:0]     hls_spike_wt_d;
    wire                            hls_spike_payload_changed;
    wire                            hls_spike_event;

    always @(posedge clk) begin
        if (!rst_n || !enable) begin
            hls_spike_valid_d <= 1'b0;
            hls_spike_nid_d   <= {HLS_NEURON_ID_WIDTH{1'b0}};
            hls_spike_wt_d    <= {HLS_WEIGHT_WIDTH{1'b0}};
        end else begin
            hls_spike_valid_d <= hls_spike_out_valid;
            if (hls_spike_out_valid) begin
                hls_spike_nid_d <= hls_spike_out_neuron_id;
                hls_spike_wt_d  <= hls_spike_out_weight;
            end
        end
    end

    assign hls_spike_payload_changed =
        (hls_spike_out_neuron_id != hls_spike_nid_d) ||
        (hls_spike_out_weight    != hls_spike_wt_d);

    assign hls_spike_event = hls_spike_out_valid &
                             (~hls_spike_valid_d | hls_spike_payload_changed);

    // Learning Engine / Observation Port
    wire                        learn_spike_valid;
    wire [GLOBAL_ID_WIDTH-1:0]  learn_spike_src_id;
    wire                        learn_spike_ready;

    // Output Spike FIFO (Group 2 -> HLS)
    localparam OUTPUT_GROUP         = NUM_GROUPS - 1;
    localparam SPIKE_OUT_FIFO_DEPTH = 32;
    localparam SPIKE_OUT_FIFO_AW    = $clog2(SPIKE_OUT_FIFO_DEPTH);
    localparam SPIKE_OUT_FIFO_DW    = HLS_NEURON_ID_WIDTH + HLS_WEIGHT_WIDTH;
    localparam [SPIKE_OUT_FIFO_AW-1:0] SPIKE_OUT_FIFO_LAST = {SPIKE_OUT_FIFO_AW{1'b1}};

    reg [SPIKE_OUT_FIFO_DW-1:0] spike_out_fifo_mem [0:SPIKE_OUT_FIFO_DEPTH-1];
    reg [SPIKE_OUT_FIFO_AW-1:0] spike_out_fifo_wr_ptr;
    reg [SPIKE_OUT_FIFO_AW-1:0] spike_out_fifo_rd_ptr;
    reg [SPIKE_OUT_FIFO_AW:0]   spike_out_fifo_count;
    reg                         spike_out_ready_d;

    wire spike_out_fifo_empty = (spike_out_fifo_count == 0);
    wire spike_out_fifo_full  = (spike_out_fifo_count == SPIKE_OUT_FIFO_DEPTH);

    wire is_output_spike     = (learn_spike_src_id[GLOBAL_ID_WIDTH-1 : LOCAL_ID_WIDTH] == OUTPUT_GROUP[GROUP_ID_WIDTH-1:0]);
    wire spike_out_fifo_push = learn_spike_valid && is_output_spike && !spike_out_fifo_full;

    wire spike_out_ready_toggle = (hls_spike_in_ready ^ spike_out_ready_d);
    wire spike_out_fifo_pop     = spike_out_ready_toggle && !spike_out_fifo_empty;

    wire [SPIKE_OUT_FIFO_DW-1:0] spike_out_fifo_head = spike_out_fifo_mem[spike_out_fifo_rd_ptr];
    wire [SPIKE_OUT_FIFO_AW-1:0] spike_out_fifo_wr_ptr_next =
        (spike_out_fifo_wr_ptr == SPIKE_OUT_FIFO_LAST) ? {SPIKE_OUT_FIFO_AW{1'b0}} : (spike_out_fifo_wr_ptr + 1'b1);
    wire [SPIKE_OUT_FIFO_AW-1:0] spike_out_fifo_rd_ptr_next =
        (spike_out_fifo_rd_ptr == SPIKE_OUT_FIFO_LAST) ? {SPIKE_OUT_FIFO_AW{1'b0}} : (spike_out_fifo_rd_ptr + 1'b1);

    always @(posedge clk) begin
        if (!rst_n || !enable) begin
            spike_out_fifo_wr_ptr <= {SPIKE_OUT_FIFO_AW{1'b0}};
            spike_out_fifo_rd_ptr <= {SPIKE_OUT_FIFO_AW{1'b0}};
            spike_out_fifo_count  <= {(SPIKE_OUT_FIFO_AW+1){1'b0}};
            spike_out_ready_d     <= 1'b0;
        end else begin
            spike_out_ready_d <= hls_spike_in_ready;

            if (spike_out_fifo_push) begin
                spike_out_fifo_mem[spike_out_fifo_wr_ptr] <= {
                    {{(HLS_NEURON_ID_WIDTH-GLOBAL_ID_WIDTH){1'b0}}, learn_spike_src_id},
                    {{(HLS_WEIGHT_WIDTH-1){1'b0}}, 1'b1}
                };
                spike_out_fifo_wr_ptr <= spike_out_fifo_wr_ptr_next;
            end

            if (spike_out_fifo_pop) begin
                spike_out_fifo_rd_ptr <= spike_out_fifo_rd_ptr_next;
            end

            case ({spike_out_fifo_push, spike_out_fifo_pop})
                2'b10: spike_out_fifo_count <= spike_out_fifo_count + 1'b1;
                2'b01: spike_out_fifo_count <= spike_out_fifo_count - 1'b1;
                default: spike_out_fifo_count <= spike_out_fifo_count;
            endcase
        end
    end

    assign rtl_spike_out_valid     = !spike_out_fifo_empty;
    assign rtl_spike_out_neuron_id = spike_out_fifo_head[SPIKE_OUT_FIFO_DW-1 : HLS_WEIGHT_WIDTH];
    assign rtl_spike_out_weight    = spike_out_fifo_head[HLS_WEIGHT_WIDTH-1 : 0];
    assign learn_spike_ready       = !spike_out_fifo_full;

    wire [31:0] routed_spike_count;
    wire        router_busy;
    assign rtl_spike_in_ready = !router_busy;
    wire snn_busy = router_busy | (grp_busy != {NUM_GROUPS{1'b0}});

    // Thresholds: Group 0 = 1 (instant relay), Group 1 = 10, Group 2 = 10
    wire [THRESHOLD_WIDTH-1:0] grp_threshold [0:NUM_GROUPS-1];
    assign grp_threshold[0] = 16'd1;
    assign grp_threshold[1] = 16'd10;
    assign grp_threshold[2] = 16'd10;

    // Instantiate 3 Core Groups
    genvar g;
    generate
        for (g = 0; g < NUM_GROUPS; g = g + 1) begin : gen_cg
            core_group #(
                .GROUP_ID           (g),
                .NEURONS_PER_GROUP  (NEURONS_PER_GROUP),
                .DATA_WIDTH         (DATA_WIDTH),
                .WEIGHT_WIDTH       (WEIGHT_WIDTH),
                .THRESHOLD_WIDTH    (THRESHOLD_WIDTH),
                .LEAK_WIDTH         (LEAK_WIDTH),
                .REFRAC_WIDTH       (REFRAC_WIDTH),
                .SPIKE_BUFFER_DEPTH (SPIKE_BUFFER_DEPTH),
                .ENABLE_INTRA_GROUP (0)
            ) u_cg (
                .clk                (clk),
                .rst_n              (rst_n),
                .enable             (enable),
                .ext_spike_valid    (grp_in_valid[g]),
                .ext_spike_dest_id  (grp_in_dest_id[g*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH]),
                .ext_spike_weight   (grp_in_weight[g*WEIGHT_WIDTH +: WEIGHT_WIDTH]),
                .ext_spike_exc_inh  (grp_in_exc[g]),
                .ext_spike_ready    (grp_in_ready[g]),
                .out_spike_valid    (grp_spike_valid[g]),
                .out_spike_neuron_id(grp_spike_neuron_id[g*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH]),
                .out_spike_ready    (grp_spike_ready[g]),
                .global_threshold   (grp_threshold[g]),
                .global_leak_rate   (8'd0),
                .global_refrac_period(8'd0),
                .weight_we          (1'b0),
                .weight_src_id      ({LOCAL_ID_WIDTH{1'b0}}),
                .weight_dst_id      ({LOCAL_ID_WIDTH{1'b0}}),
                .weight_data        ({WEIGHT_WIDTH{1'b0}}),
                .weight_exc         (1'b0),
                .spike_count        (grp_spike_count[g*16 +: 16]),
                .group_busy         (grp_busy[g])
            );
        end
    endgenerate

    // Connectivity Table
    synaptic_connectivity_table #(
        .NUM_GROUPS         (NUM_GROUPS),
        .NEURONS_PER_GROUP  (NEURONS_PER_GROUP),
        .WEIGHT_WIDTH       (WEIGHT_WIDTH),
        .MAX_FANOUT_INTER   (MAX_FANOUT_INTER)
    ) u_ct (
        .clk                (clk),
        .rst_n              (rst_n),
        .cfg_we             (ct_mux_we),
        .cfg_src_group      (ct_mux_sg),
        .cfg_src_neuron     (ct_mux_sn),
        .cfg_fanout_idx     (ct_mux_fi),
        .cfg_valid          (ct_mux_v),
        .cfg_dst_group      (ct_mux_dg),
        .cfg_dst_neuron     (ct_mux_dn),
        .cfg_weight         (ct_mux_w),
        .cfg_exc_inh        (ct_mux_exc),
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

    // Event Router
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
        .ext_spike_valid    (hls_spike_event),
        .ext_spike_neuron_id(hls_spike_out_neuron_id[GLOBAL_ID_WIDTH-1:0]),
        .ext_spike_weight   (hls_spike_out_weight[WEIGHT_WIDTH-1:0]),
        .ext_spike_exc      (1'b1),
        .ext_spike_ready    (),
        .learn_spike_valid  (learn_spike_valid),
        .learn_spike_src_id (learn_spike_src_id),
        .learn_spike_ready  (learn_spike_ready),
        .learn_weight_valid     (1'b0),
        .learn_weight_group     ({GROUP_ID_WIDTH{1'b0}}),
        .learn_weight_src       ({LOCAL_ID_WIDTH{1'b0}}),
        .learn_weight_dst       ({LOCAL_ID_WIDTH{1'b0}}),
        .learn_weight_data      ({WEIGHT_WIDTH{1'b0}}),
        .learn_weight_exc       (1'b0),
        .learn_weight_is_inter  (1'b0),
        .learn_weight_dst_group ({GROUP_ID_WIDTH{1'b0}}),
        .learn_weight_fanout_idx({FANOUT_IDX_WIDTH{1'b0}}),
        .learn_weight_ready     (),
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
        .grp_weight_we      (),
        .grp_weight_src     (),
        .grp_weight_dst     (),
        .grp_weight_data    (),
        .grp_weight_exc     (),
        .ct_cfg_we          (ct_cfg_we),
        .ct_cfg_src_group   (ct_cfg_src_group),
        .ct_cfg_src_neuron  (ct_cfg_src_neuron),
        .ct_cfg_fanout_idx  (ct_cfg_fanout_idx),
        .ct_cfg_valid       (ct_cfg_valid_bit),
        .ct_cfg_dst_group   (ct_cfg_dst_group),
        .ct_cfg_dst_neuron  (ct_cfg_dst_neuron),
        .ct_cfg_weight      (ct_cfg_weight),
        .ct_cfg_exc_inh     (ct_cfg_exc_inh),
        .routed_spike_count (routed_spike_count),
        .router_busy        (router_busy)
    );

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

    integer pass_count = 0;
    integer fail_count = 0;

    task automatic check(input [8*80-1:0] desc, input integer condition);
    begin
        if (condition) begin
            $display("[PASS] %0s", desc);
            pass_count = pass_count + 1;
        end else begin
            $display("[FAIL] %0s", desc);
            fail_count = fail_count + 1;
        end
    end
    endtask

    initial begin
        $dumpfile("snn_3layer_waves.vcd");
        $dumpvars(0, tb_snn_3layer);

        $display("=========================================================");
        $display("  3-Layer SNN Hardware End-to-End Simulation");
        $display("=========================================================");

        // Initialize
        rst_n = 0;
        enable = 0;
        hls_spike_out_valid = 0;
        hls_spike_out_neuron_id = 0;
        hls_spike_out_weight = 0;
        hls_spike_in_ready = 0;
        host_ct_we = 0;

        repeat (20) @(posedge clk);
        rst_n = 1;
        repeat (10) @(posedge clk);
        enable = 1;
        repeat (20) @(posedge clk);

        check("Initial State: snn_busy is 0", snn_busy == 0);
        check("Initial State: rtl_spike_out_valid is 0", rtl_spike_out_valid == 0);

        // ── Program Network Weights ──────────────────────────────────────────
        // Layer 2: Group 0 neuron 42 -> Group 1 neuron 100, weight=15 (exc=1)
        program_ct_entry(2'd0, 8'd42, 8'd0, 1'b1, 2'd1, 8'd100, 8'd15, 1'b1);
        program_ct_entry(2'd0, 8'd42, 8'd1, 1'b0, 2'd0, 8'd0,   8'd0,  1'b0);

        // Layer 3: Group 1 neuron 100 -> Group 2 neuron 7, weight=15 (exc=1)
        program_ct_entry(2'd1, 8'd100, 8'd0, 1'b1, 2'd2, 8'd7,   8'd15, 1'b1);
        program_ct_entry(2'd1, 8'd100, 8'd1, 1'b0, 2'd0, 8'd0,   8'd0,  1'b0);

        repeat (20) @(posedge clk);
        check("Network Programmed: system remains idle", snn_busy == 0);

        // ── Inject External Spike from HLS (level signal held for 15 cycles) ──
        $display("\n--- Injecting External Spike (Neuron 42, weight 127) ---");
        @(posedge clk);
        hls_spike_out_valid     <= 1;
        hls_spike_out_neuron_id <= 10'd42;  // Group 0, neuron 42
        hls_spike_out_weight    <= 8'd127;

        // Keep valid HIGH for 15 clock cycles to verify edge detector avoids multi-trigger
        repeat (15) @(posedge clk);
        hls_spike_out_valid <= 0;

        // Wait for end-to-end propagation: Group 0 -> Group 1 -> Group 2 -> FIFO
        repeat (600) @(posedge clk);

        check("Group 0 fired: spike_count == 1", grp_spike_count[0*16 +: 16] == 1);
        check("Group 1 fired: spike_count == 1", grp_spike_count[1*16 +: 16] == 1);
        check("Group 2 (class 7) fired: spike_count == 1", grp_spike_count[2*16 +: 16] == 1);

        check("Output Spike FIFO valid is asserted", rtl_spike_out_valid == 1);
        check("Output Class Neuron ID is 519 (grp=2, loc=7)",
              rtl_spike_out_neuron_id == (2 * 256 + 7));

        // Emulate HLS consuming the spike and toggling spike_out_ready
        $display("\n--- HLS Acknowledges and Pops Output Spike ---");
        @(posedge clk);
        hls_spike_in_ready <= ~hls_spike_in_ready;  // toggle ready token
        @(posedge clk);
        @(posedge clk);

        check("Output Spike FIFO is empty after pop", rtl_spike_out_valid == 0);
        check("Trigger snn_busy returned to 0 (IDLE)", snn_busy == 0);

        $display("\n=========================================================");
        $display("  Results: %0d PASS, %0d FAIL", pass_count, fail_count);
        $display("=========================================================");

        if (fail_count == 0)
            $display("*** ALL 3-LAYER INTEGRATION TESTS PASSED! ***\n");
        else
            $display("*** SOME TESTS FAILED ***\n");

        $finish;
    end

endmodule
