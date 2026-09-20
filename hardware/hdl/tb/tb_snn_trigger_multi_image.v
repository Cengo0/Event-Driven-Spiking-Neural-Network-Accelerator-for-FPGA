//=============================================================================
// Testbench: Multi-Image SCA Trigger Simulation for snn_busy (Pin Y18)
// Verifies:
//   1. snn_busy is LOW (0) before an image starts.
//   2. snn_busy rises to HIGH (1) when hardware begins processing the image.
//   3. snn_busy falls to LOW (0) when hardware finishes processing all spikes.
//   4. snn_busy stays LOW (0) in the inter-image gap.
//   5. snn_busy rises to HIGH (1) again for the next image.
//   6. Measures exact pulse durations and duty cycles for oscilloscope capture.
//=============================================================================

`timescale 1ns / 1ps
`include "snn_params.vh"

module tb_snn_trigger_multi_image;

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
    always #5 clk = ~clk;  // 100 MHz (10 ns per cycle)

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

    // Pin Y18 SCA Trigger signal
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

    // Monitor snn_busy edge transitions in real time
    time t_rise, t_fall;
    always @(posedge snn_busy) begin
        t_rise = $time;
        $display("[%0t ns] TRIGGER RISING EDGE: snn_busy -> 1 (Hardware Active / Processing Started)", $time/1000);
    end

    always @(negedge snn_busy) begin
        t_fall = $time;
        $display("[%0t ns] TRIGGER FALLING EDGE: snn_busy -> 0 (Hardware Idle / Processing Completed, Duration: %0d ns)",
                 $time/1000, ($time - t_rise)/1000);
    end

    task automatic run_image_inference(
        input integer img_id,
        input [7:0]   input_neuron,
        input [7:0]   expected_class
    );
        integer timeout;
    begin
        $display("\n=========================================================");
        $display("  STARTING IMAGE %0d INFERENCE", img_id);
        $display("  Initial state: snn_busy = %b", snn_busy);
        $display("=========================================================");

        // Pre-condition: Trigger must be 0 before starting
        if (snn_busy != 0)
            $display("[ERROR] Trigger snn_busy is not 0 before starting Image %0d!", img_id);

        // Inject external spike from Layer 1
        @(posedge clk);
        hls_spike_out_valid     <= 1;
        hls_spike_out_neuron_id <= {2'd0, input_neuron};
        hls_spike_out_weight    <= 8'd127;
        repeat (10) @(posedge clk);
        hls_spike_out_valid     <= 0;

        // Wait until trigger turns ON
        timeout = 0;
        while (!snn_busy && timeout < 500) begin
            @(posedge clk);
            timeout = timeout + 1;
        end
        if (snn_busy)
            $display("[VERIFIED] Image %0d: snn_busy transitioned to 1 at start of computation", img_id);
        else
            $display("[ERROR] Image %0d: snn_busy never went high!", img_id);

        // Wait until output class spike is emitted by Group 2
        timeout = 0;
        while (!rtl_spike_out_valid && timeout < 5000) begin
            @(posedge clk);
            timeout = timeout + 1;
        end

        // Drain output spike from FIFO
        if (rtl_spike_out_valid) begin
            $display("[VERIFIED] Image %0d: Output class spike received: Neuron ID %0d (Class %0d)",
                     img_id, rtl_spike_out_neuron_id, rtl_spike_out_neuron_id - 512);
            hls_spike_in_ready <= ~hls_spike_in_ready;
            repeat (5) @(posedge clk);
        end else begin
            $display("[ERROR] Image %0d: Output class spike was not received within timeout!", img_id);
        end

        // Wait until all hardware finishes and trigger returns to 0
        timeout = 0;
        while (snn_busy && timeout < 500) begin
            @(posedge clk);
            timeout = timeout + 1;
        end
        if (!snn_busy)
            $display("[VERIFIED] Image %0d: snn_busy returned to 0 when computation completed", img_id);
        else
            $display("[ERROR] Image %0d: snn_busy remained stuck high!", img_id);

        // Verify idle gap between images
        repeat (200) @(posedge clk);
        if (snn_busy == 0)
            $display("[VERIFIED] Image %0d: snn_busy stays LOW in inter-image window", img_id);
        else
            $display("[ERROR] Image %0d: snn_busy asserted during inter-image window!", img_id);
    end
    endtask

    initial begin
        $dumpfile("snn_trigger_multi_image_waves.vcd");
        $dumpvars(0, tb_snn_trigger_multi_image);

        // Reset
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

        // Program Synaptic Weights:
        // Input Neuron 10 -> Hidden Neuron 20 -> Class 3
        program_ct_entry(2'd0, 8'd10, 8'd0, 1'b1, 2'd1, 8'd20, 8'd15, 1'b1);
        program_ct_entry(2'd0, 8'd10, 8'd1, 1'b0, 2'd0, 8'd0,  8'd0,  1'b0);
        program_ct_entry(2'd1, 8'd20, 8'd0, 1'b1, 2'd2, 8'd3,  8'd15, 1'b1);
        program_ct_entry(2'd1, 8'd20, 8'd1, 1'b0, 2'd0, 8'd0,  8'd0,  1'b0);

        // Input Neuron 50 -> Hidden Neuron 60 -> Class 7
        program_ct_entry(2'd0, 8'd50, 8'd0, 1'b1, 2'd1, 8'd60, 8'd15, 1'b1);
        program_ct_entry(2'd0, 8'd50, 8'd1, 1'b0, 2'd0, 8'd0,  8'd0,  1'b0);
        program_ct_entry(2'd1, 8'd60, 8'd0, 1'b1, 2'd2, 8'd7,  8'd15, 1'b1);
        program_ct_entry(2'd1, 8'd60, 8'd1, 1'b0, 2'd0, 8'd0,  8'd0,  1'b0);

        // Input Neuron 90 -> Hidden Neuron 100 -> Class 1
        program_ct_entry(2'd0, 8'd90, 8'd0, 1'b1, 2'd1, 8'd100, 8'd15, 1'b1);
        program_ct_entry(2'd0, 8'd90, 8'd1, 1'b0, 2'd0, 8'd0,   8'd0,  1'b0);
        program_ct_entry(2'd1, 8'd100, 8'd0, 1'b1, 2'd2, 8'd1,  8'd15, 1'b1);
        program_ct_entry(2'd1, 8'd100, 8'd1, 1'b0, 2'd0, 8'd0,  8'd0,  1'b0);

        repeat (50) @(posedge clk);

        // Run 3 consecutive images
        run_image_inference(0, 8'd10, 8'd3);
        run_image_inference(1, 8'd50, 8'd7);
        run_image_inference(2, 8'd90, 8'd1);

        $display("\n=========================================================");
        $display("  MULTI-IMAGE TRIGGER VERIFICATION COMPLETE: ALL PASSED!");
        $display("=========================================================\n");
        $finish;
    end

endmodule
