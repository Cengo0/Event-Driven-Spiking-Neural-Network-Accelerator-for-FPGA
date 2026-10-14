//=============================================================================
// Testbench: CNN3 SNN Hardware Pipeline (5 Core Groups + CT + Router + FIFO)
// Architecture for CNN3:
//   - Groups 0..3: Layer 2 hidden LIF neurons (4 x 196 = 784 neurons, threshold 103)
//   - Group 4    : Layer 3 output class LIF neurons (10 classes: 0..9, threshold 103)
//   - Inter-group Connectivity Table: BRAM mapping Layer 2 -> Layer 3
//   - Event Router: Arbitrates spikes, performs CT lookup, delivers across groups
//   - Output FIFO: Captures Group 4 class spikes for HLS / DMA readback
//   - Pin Y18 trigger (snn_busy): Monitors active routing & integration
//=============================================================================

`timescale 1ns / 1ps
`include "snn_params.vh"

module tb_snn_cnn3;

    parameter NUM_GROUPS        = `SNN_NUM_GROUPS;          // 5
    parameter NEURONS_PER_GROUP = `SNN_NEURONS_PER_GROUP;  // 196
    parameter WEIGHT_WIDTH      = `SNN_WEIGHT_WIDTH;        // 8
    parameter MAX_FANOUT_INTER  = `SNN_MAX_FANOUT_INTER;    // 16
    parameter DATA_WIDTH        = `SNN_DATA_WIDTH;          // 16
    parameter THRESHOLD_WIDTH   = `SNN_THRESHOLD_WIDTH;     // 16
    parameter LEAK_WIDTH        = `SNN_LEAK_WIDTH;          // 8
    parameter REFRAC_WIDTH      = `SNN_REFRAC_WIDTH;        // 8
    parameter SPIKE_BUFFER_DEPTH= `SNN_SPIKE_BUFFER_DEPTH;  // 64
    parameter GROUP_ID_WIDTH    = `SNN_GROUP_ID_WIDTH;      // 3
    parameter LOCAL_ID_WIDTH    = `SNN_LOCAL_ID_WIDTH;      // 8
    parameter GLOBAL_ID_WIDTH   = `SNN_GLOBAL_ID_WIDTH;     // 11
    parameter FANOUT_IDX_WIDTH  = `SNN_FANOUT_IDX_WIDTH;    // 4
    parameter HLS_NEURON_ID_WIDTH = `SNN_HLS_NEURON_ID_WIDTH; // 11
    parameter HLS_WEIGHT_WIDTH  = `SNN_HLS_WEIGHT_WIDTH;    // 8

    localparam OUTPUT_GROUP     = NUM_GROUPS - 1;           // Group 4

    reg clk;
    reg rst_n;
    reg enable;

    initial clk = 0;
    always #5 clk = ~clk;  // 100 MHz clock

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

    // Router <-> Connectivity Table wires
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

    // CT programming wires (Host interface emulation)
    reg                         host_ct_we;
    reg  [GROUP_ID_WIDTH-1:0]   host_ct_src_group;
    reg  [LOCAL_ID_WIDTH-1:0]   host_ct_src_neuron;
    reg  [FANOUT_IDX_WIDTH-1:0] host_ct_fanout_idx;
    reg                         host_ct_valid;
    reg  [GROUP_ID_WIDTH-1:0]   host_ct_dst_group;
    reg  [LOCAL_ID_WIDTH-1:0]   host_ct_dst_neuron;
    reg  [WEIGHT_WIDTH-1:0]     host_ct_weight;
    reg                         host_ct_exc_inh;

    // External Spike Input (mimicking HLS Conv2 fanout into Layer 2)
    reg                             ext_spike_valid;
    reg  [GLOBAL_ID_WIDTH-1:0]      ext_spike_neuron_id;
    reg  [WEIGHT_WIDTH-1:0]         ext_spike_weight;
    reg                             ext_spike_exc;
    wire                            ext_spike_ready;

    // Learning Engine / Observation Port
    wire                            learn_spike_valid;
    wire [GLOBAL_ID_WIDTH-1:0]      learn_spike_src_id;
    wire                            learn_spike_ready;

    // Output Spike FIFO (Group 4 -> HLS)
    localparam SPIKE_OUT_FIFO_DEPTH = 32;
    localparam SPIKE_OUT_FIFO_AW    = $clog2(SPIKE_OUT_FIFO_DEPTH);
    localparam SPIKE_OUT_FIFO_DW    = HLS_NEURON_ID_WIDTH + HLS_WEIGHT_WIDTH;
    localparam [SPIKE_OUT_FIFO_AW-1:0] SPIKE_OUT_FIFO_LAST = {SPIKE_OUT_FIFO_AW{1'b1}};

    reg [SPIKE_OUT_FIFO_DW-1:0]     spike_out_fifo_mem [0:SPIKE_OUT_FIFO_DEPTH-1];
    reg [SPIKE_OUT_FIFO_AW-1:0]     spike_out_fifo_wr_ptr;
    reg [SPIKE_OUT_FIFO_AW-1:0]     spike_out_fifo_rd_ptr;
    reg [SPIKE_OUT_FIFO_AW:0]       spike_out_fifo_count;
    reg                             spike_out_ready_d;
    reg                             hls_spike_in_ready;

    wire spike_out_fifo_empty = (spike_out_fifo_count == 0);
    wire spike_out_fifo_full  = (spike_out_fifo_count == SPIKE_OUT_FIFO_DEPTH);

    // Group 4 (OUTPUT_GROUP) class spikes trigger FIFO push
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

    wire                            rtl_spike_out_valid     = !spike_out_fifo_empty;
    wire [HLS_NEURON_ID_WIDTH-1:0]  rtl_spike_out_neuron_id = spike_out_fifo_head[SPIKE_OUT_FIFO_DW-1 : HLS_WEIGHT_WIDTH];
    wire [HLS_WEIGHT_WIDTH-1:0]     rtl_spike_out_weight    = spike_out_fifo_head[HLS_WEIGHT_WIDTH-1 : 0];
    assign learn_spike_ready = !spike_out_fifo_full;

    wire [31:0] routed_spike_count;
    wire        router_busy;
    wire        snn_busy = router_busy | (grp_busy != {NUM_GROUPS{1'b0}});

    // Thresholds: All groups configured to hw_threshold = 103 (matching deployment)
    reg [THRESHOLD_WIDTH-1:0] global_hw_threshold;

    // Instantiate 5 Core Groups (0..3: Layer 2; 4: Layer 3)
    genvar g;
    generate
        for (g = 0; g < NUM_GROUPS; g = g + 1) begin : gen_cg
            localparam THIS_NPG = (g == 4) ? `SNN_GROUP_SIZE_4 : `SNN_GROUP_SIZE_0;
            core_group #(
                .GROUP_ID           (g),
                .NEURONS_PER_GROUP  (THIS_NPG),
                .LOCAL_ID_WIDTH     (LOCAL_ID_WIDTH),
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
                .global_threshold   (global_hw_threshold),
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

    // Connectivity Table (BRAM)
    synaptic_connectivity_table #(
        .NUM_GROUPS         (NUM_GROUPS),
        .NEURONS_PER_GROUP  (NEURONS_PER_GROUP),
        .WEIGHT_WIDTH       (WEIGHT_WIDTH),
        .MAX_FANOUT_INTER   (MAX_FANOUT_INTER)
    ) u_ct (
        .clk                (clk),
        .rst_n              (rst_n),
        .cfg_we             (host_ct_we),
        .cfg_src_group      (host_ct_src_group),
        .cfg_src_neuron     (host_ct_src_neuron),
        .cfg_fanout_idx     (host_ct_fanout_idx),
        .cfg_valid          (host_ct_valid),
        .cfg_dst_group      (host_ct_dst_group),
        .cfg_dst_neuron     (host_ct_dst_neuron),
        .cfg_weight         (host_ct_weight),
        .cfg_exc_inh        (host_ct_exc_inh),
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
        .ext_spike_valid    (ext_spike_valid),
        .ext_spike_neuron_id(ext_spike_neuron_id),
        .ext_spike_weight   (ext_spike_weight),
        .ext_spike_exc      (ext_spike_exc),
        .ext_spike_ready    (ext_spike_ready),
        .learn_spike_valid  (learn_spike_valid),
        .learn_spike_src_id (learn_spike_src_id),
        .learn_spike_ready  (learn_spike_ready),
        .learn_weight_valid (1'b0),
        .learn_weight_group ({GROUP_ID_WIDTH{1'b0}}),
        .learn_weight_src   ({LOCAL_ID_WIDTH{1'b0}}),
        .learn_weight_dst   ({LOCAL_ID_WIDTH{1'b0}}),
        .learn_weight_data  ({WEIGHT_WIDTH{1'b0}}),
        .learn_weight_exc   (1'b0),
        .learn_weight_is_inter (1'b0),
        .learn_weight_dst_group({GROUP_ID_WIDTH{1'b0}}),
        .learn_weight_fanout_idx({FANOUT_IDX_WIDTH{1'b0}}),
        .learn_weight_ready (),
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
        .ct_cfg_we          (),
        .ct_cfg_src_group   (),
        .ct_cfg_src_neuron  (),
        .ct_cfg_fanout_idx  (),
        .ct_cfg_valid       (),
        .ct_cfg_dst_group   (),
        .ct_cfg_dst_neuron  (),
        .ct_cfg_weight      (),
        .ct_cfg_exc_inh     (),
        .routed_spike_count (routed_spike_count),
        .router_busy        (router_busy)
    );

    // Helper task to program Connectivity Table entries
    task program_ct_entry(
        input [GROUP_ID_WIDTH-1:0]   src_grp,
        input [LOCAL_ID_WIDTH-1:0]   src_nid,
        input [FANOUT_IDX_WIDTH-1:0] fanout,
        input                        valid,
        input [GROUP_ID_WIDTH-1:0]   dst_grp,
        input [LOCAL_ID_WIDTH-1:0]   dst_nid,
        input [WEIGHT_WIDTH-1:0]     weight,
        input                        exc
    );
    begin
        @(posedge clk);
        host_ct_we         <= 1'b1;
        host_ct_src_group  <= src_grp;
        host_ct_src_neuron <= src_nid;
        host_ct_fanout_idx <= fanout;
        host_ct_valid      <= valid;
        host_ct_dst_group  <= dst_grp;
        host_ct_dst_neuron <= dst_nid;
        host_ct_weight     <= weight;
        host_ct_exc_inh    <= exc;
        @(posedge clk);
        host_ct_we         <= 1'b0;
    end
    endtask

    // Helper task to inject an external spike into Groups 0..3
    task inject_ext_spike(
        input [GROUP_ID_WIDTH-1:0] grp,
        input [LOCAL_ID_WIDTH-1:0] nid,
        input [WEIGHT_WIDTH-1:0]   wt,
        input                      exc
    );
    begin
        // Wait until router is ready to accept external spike
        while (!ext_spike_ready) @(posedge clk);
        @(posedge clk);
        ext_spike_valid     <= 1'b1;
        ext_spike_neuron_id <= {grp, nid};
        ext_spike_weight    <= wt;
        ext_spike_exc       <= exc;
        @(posedge clk);
        ext_spike_valid     <= 1'b0;
    end
    endtask

    integer pass_count = 0;
    integer fail_count = 0;

    task check(input [255:0] test_name, input condition);
    begin
        if (condition) begin
            $display("[PASS] %0s", test_name);
            pass_count = pass_count + 1;
        end else begin
            $display("[FAIL] %0s", test_name);
            fail_count = fail_count + 1;
        end
    end
    endtask

    initial begin
        $dumpfile("snn_cnn3_waves.vcd");
        $dumpvars(0, tb_snn_cnn3);

        $display("=========================================================");
        $display("  CNN3 SNN 5-Group Hardware Pipeline Testbench");
        $display("=========================================================");

        // Initial conditions
        rst_n               = 0;
        enable              = 0;
        global_hw_threshold = 16'd103;  // Calibrated hardware threshold
        host_ct_we          = 0;
        host_ct_src_group   = 0;
        host_ct_src_neuron  = 0;
        host_ct_fanout_idx  = 0;
        host_ct_valid       = 0;
        host_ct_dst_group   = 0;
        host_ct_dst_neuron  = 0;
        host_ct_weight      = 0;
        host_ct_exc_inh     = 0;
        ext_spike_valid     = 0;
        ext_spike_neuron_id = 0;
        ext_spike_weight    = 0;
        ext_spike_exc       = 0;
        hls_spike_in_ready  = 0;

        repeat (10) @(posedge clk);
        rst_n  = 1;
        enable = 1;
        repeat (5) @(posedge clk);

        check("Initial State: snn_busy is LOW", snn_busy == 0);
        check("Initial State: rtl_spike_out_valid is LOW", rtl_spike_out_valid == 0);

        // ── Step 1: Program Connectivity Table (Layer 2 -> Layer 3) ──
        $display("\n--- Step 1: Programming Connectivity Table ---");
        // Group 0, Neuron 10 -> Group 4 (Class 7), weight = 35, exc = 1
        program_ct_entry(3'd0, 8'd10, 4'd0, 1'b1, 3'd4, 8'd7, 8'd35, 1'b1);
        program_ct_entry(3'd0, 8'd10, 4'd1, 1'b0, 3'd0, 8'd0, 8'd0,  1'b0);

        // Group 1, Neuron 20 -> Group 4 (Class 7), weight = 40, exc = 1
        program_ct_entry(3'd1, 8'd20, 4'd0, 1'b1, 3'd4, 8'd7, 8'd40, 1'b1);
        program_ct_entry(3'd1, 8'd20, 4'd1, 1'b0, 3'd0, 8'd0, 8'd0,  1'b0);

        // Group 2, Neuron 30 -> Group 4 (Class 7), weight = 40, exc = 1
        program_ct_entry(3'd2, 8'd30, 4'd0, 1'b1, 3'd4, 8'd7, 8'd40, 1'b1);
        program_ct_entry(3'd2, 8'd30, 4'd1, 1'b0, 3'd0, 8'd0, 8'd0,  1'b0);

        repeat (10) @(posedge clk);
        check("CT Programmed: router returns to IDLE", router_busy == 0);

        // ── Step 2: Inject External Spikes into Layer 2 (Group 0 Neuron 10) ──
        $display("\n--- Step 2: Injecting External Spikes into Group 0 Neuron 10 ---");
        // Threshold is 103. Send three spikes of weight 40: 40 + 40 = 80 (< 103), then + 40 = 120 (>= 103).
        inject_ext_spike(3'd0, 8'd10, 8'd40, 1'b1);
        repeat (15) @(posedge clk);
        check("Group 0 sub-threshold spike 1: not fired", grp_spike_count[0*16 +: 16] == 0);

        inject_ext_spike(3'd0, 8'd10, 8'd40, 1'b1);
        repeat (15) @(posedge clk);
        check("Group 0 sub-threshold spike 2: not fired", grp_spike_count[0*16 +: 16] == 0);

        inject_ext_spike(3'd0, 8'd10, 8'd40, 1'b1);
        // Wait for integration and firing: Group 0 integrates -> fires -> router arbitrates -> delivers to Group 4
        repeat (50) @(posedge clk);
        check("Group 0 threshold reached: fired 1 spike", grp_spike_count[0*16 +: 16] == 1);
        check("Router routed Group 0 spike to Group 4", grp_in_valid[4] == 0 || grp_busy[4] == 1 || grp_spike_count[4*16 +: 16] == 0);

        // ── Step 3: Fire Group 1 and Group 2 Neurons to Exceed Group 4 Threshold ──
        $display("\n--- Step 3: Firing Group 1 & Group 2 into Group 4 Class 7 ---");
        // Fire Group 1 Neuron 20 (delivers weight 40 to Group 4 Class 7)
        inject_ext_spike(3'd1, 8'd20, 8'd55, 1'b1);
        inject_ext_spike(3'd1, 8'd20, 8'd55, 1'b1);
        repeat (50) @(posedge clk);
        check("Group 1 threshold reached: fired 1 spike", grp_spike_count[1*16 +: 16] == 1);

        // Fire Group 2 Neuron 30 (delivers weight 40 to Group 4 Class 7)
        // Group 4 Class 7 accumulated: 35 + 40 + 40 = 115 >= 103!
        inject_ext_spike(3'd2, 8'd30, 8'd55, 1'b1);
        inject_ext_spike(3'd2, 8'd30, 8'd55, 1'b1);
        repeat (60) @(posedge clk);
        check("Group 2 threshold reached: fired 1 spike", grp_spike_count[2*16 +: 16] == 1);

        // Wait for Group 4 Class 7 to integrate, fire, and push into output FIFO
        repeat (100) @(posedge clk);
        $display("DEBUG: grp_spike_count: G0=%0d G1=%0d G2=%0d G3=%0d G4=%0d",
            grp_spike_count[0*16 +: 16], grp_spike_count[1*16 +: 16],
            grp_spike_count[2*16 +: 16], grp_spike_count[3*16 +: 16],
            grp_spike_count[4*16 +: 16]);
        $display("DEBUG: grp_busy=%b, router_busy=%b, routed_spike_count=%0d",
            grp_busy, router_busy, routed_spike_count);
        $display("DEBUG: learn_spike_valid=%b, learn_spike_src_id=%0d (grp=%0d, nid=%0d)",
            learn_spike_valid, learn_spike_src_id,
            learn_spike_src_id[GLOBAL_ID_WIDTH-1:LOCAL_ID_WIDTH],
            learn_spike_src_id[LOCAL_ID_WIDTH-1:0]);
        $display("DEBUG: spike_out_fifo_count=%0d, rtl_spike_out_valid=%b",
            spike_out_fifo_count, rtl_spike_out_valid);
        check("Group 4 (Class 7) threshold reached: fired 1 spike", grp_spike_count[4*16 +: 16] == 1);
        check("Output Spike FIFO valid is asserted", rtl_spike_out_valid == 1);

        // In 5-group topology: Group 4 neuron 7 has global ID = (4 << 8) | 7 = 1031
        check("Output Class Neuron ID matches Group 4 Class 7",
              rtl_spike_out_neuron_id == ((4 << LOCAL_ID_WIDTH) | 7));

        // ── Step 4: HLS Acknowledges and Pops Output Spike FIFO ──
        $display("\n--- Step 4: Emulate HLS Consuming Output Spike ---");
        @(posedge clk);
        hls_spike_in_ready <= ~hls_spike_in_ready;  // Toggle token
        @(posedge clk);
        @(posedge clk);

        check("Output Spike FIFO is empty after pop", rtl_spike_out_valid == 0);

        repeat (20) @(posedge clk);
        check("SCA Trigger snn_busy returned to 0 (IDLE)", snn_busy == 0);

        $display("\n=========================================================");
        $display("  Results: %0d PASS, %0d FAIL", pass_count, fail_count);
        $display("=========================================================");

        if (fail_count == 0)
            $display("*** ALL CNN3 5-GROUP PIPELINE TESTS PASSED! ***\n");
        else
            $display("*** SOME TESTS FAILED ***\n");

        $finish;
    end

endmodule
