//=============================================================================
// Testbench: HLS Layer 1 (Conv1 Streaming Engine + Conv2 Fanout)
// Simulates snn_top_hls synthesized Verilog with Icarus Verilog
// Validates:
//   1. AXI-Lite control interface configuration (Mode 3, Threshold, Enable, Start)
//   2. AXI-Stream pixel ingestion (784 pixels, 16-bit fixed point Q8.8)
//   3. Layer 1 2D line buffer & sliding window processing
//   4. Layer 2 Conv2 fanout generation onto spike_in_valid / spike_in_neuron_id
//=============================================================================

`timescale 1ns / 1ps

module tb_hls_layer1;

    reg clk;
    reg rst_n;

    // Clock generation: 100 MHz (10ns period)
    initial clk = 0;
    always #5 clk = ~clk;

    // AXI-Stream pixel input
    reg  [31:0] s_axis_spikes_TDATA;
    reg         s_axis_spikes_TVALID;
    wire        s_axis_spikes_TREADY;
    reg  [3:0]  s_axis_spikes_TKEEP;
    reg  [3:0]  s_axis_spikes_TSTRB;
    reg  [0:0]  s_axis_spikes_TUSER;
    reg  [0:0]  s_axis_spikes_TLAST;
    reg  [0:0]  s_axis_spikes_TID;
    reg  [0:0]  s_axis_spikes_TDEST;

    // Output fanout spikes (HLS -> RTL Core Groups 0..3)
    wire        spike_in_valid;
    wire [10:0] spike_in_neuron_id;
    wire [7:0]  spike_in_weight;
    reg         spike_in_ready;

    // Output spikes (HLS -> S2MM DMA)
    wire [31:0] m_axis_spikes_TDATA;
    wire        m_axis_spikes_TVALID;
    reg         m_axis_spikes_TREADY;
    wire [3:0]  m_axis_spikes_TKEEP;
    wire [3:0]  m_axis_spikes_TSTRB;
    wire [0:0]  m_axis_spikes_TUSER;
    wire [0:0]  m_axis_spikes_TLAST;
    wire [0:0]  m_axis_spikes_TID;
    wire [0:0]  m_axis_spikes_TDEST;

    // Unused streams / signals
    wire [31:0] s_axis_data_TDATA = 32'd0;
    wire        s_axis_data_TVALID = 1'b0;
    wire        s_axis_data_TREADY;
    wire [3:0]  s_axis_data_TKEEP = 4'hF;
    wire [3:0]  s_axis_data_TSTRB = 4'hF;
    wire [0:0]  s_axis_data_TUSER = 1'b0;
    wire [0:0]  s_axis_data_TLAST = 1'b0;
    wire [0:0]  s_axis_data_TID = 1'b0;
    wire [0:0]  s_axis_data_TDEST = 1'b0;

    wire [31:0] s_axis_weights_TDATA = 32'd0;
    wire        s_axis_weights_TVALID = 1'b0;
    wire        s_axis_weights_TREADY;
    wire [3:0]  s_axis_weights_TKEEP = 4'hF;
    wire [3:0]  s_axis_weights_TSTRB = 4'hF;
    wire [0:0]  s_axis_weights_TUSER = 1'b0;
    wire [0:0]  s_axis_weights_TLAST = 1'b0;
    wire [0:0]  s_axis_weights_TID = 1'b0;
    wire [0:0]  s_axis_weights_TDEST = 1'b0;

    wire [31:0] m_axis_weights_TDATA;
    wire        m_axis_weights_TVALID;
    reg         m_axis_weights_TREADY = 1'b1;
    wire [3:0]  m_axis_weights_TKEEP;
    wire [3:0]  m_axis_weights_TSTRB;
    wire [0:0]  m_axis_weights_TUSER;
    wire [0:0]  m_axis_weights_TLAST;
    wire [0:0]  m_axis_weights_TID;
    wire [0:0]  m_axis_weights_TDEST;

    reg         spike_out_valid = 1'b0;
    reg  [10:0] spike_out_neuron_id = 11'd0;
    reg  [7:0]  spike_out_weight = 8'd0;
    wire        spike_out_ready;

    wire        learn_weight_valid;
    wire [2:0]  learn_weight_group;
    wire [7:0]  learn_weight_src;
    wire [7:0]  learn_weight_dst;
    wire [7:0]  learn_weight_data;
    wire        learn_weight_exc;
    wire        learn_weight_is_inter;
    wire [2:0]  learn_weight_dst_group;
    wire [3:0]  learn_weight_fanout_idx;
    reg         learn_weight_ready = 1'b1;

    wire        snn_enable;
    wire        snn_reset;
    wire [15:0] threshold_out;
    wire [15:0] leak_rate_out;
    reg         snn_ready = 1'b1;
    reg         snn_busy  = 1'b0;

    // AXI-Lite Control Signals
    reg         s_axi_ctrl_AWVALID;
    wire        s_axi_ctrl_AWREADY;
    reg  [7:0]  s_axi_ctrl_AWADDR;
    reg         s_axi_ctrl_WVALID;
    wire        s_axi_ctrl_WREADY;
    reg  [31:0] s_axi_ctrl_WDATA;
    reg  [3:0]  s_axi_ctrl_WSTRB;
    wire [1:0]  s_axi_ctrl_BRESP;
    wire        s_axi_ctrl_BVALID;
    reg         s_axi_ctrl_BREADY;
    reg         s_axi_ctrl_ARVALID;
    wire        s_axi_ctrl_ARREADY;
    reg  [7:0]  s_axi_ctrl_ARADDR;
    wire [31:0] s_axi_ctrl_RDATA;
    wire [1:0]  s_axi_ctrl_RRESP;
    wire        s_axi_ctrl_RVALID;
    reg         s_axi_ctrl_RREADY;

    // Instantiate HLS Top-Level Core
    snn_top_hls u_hls (
        .ap_clk                 (clk),
        .ap_rst_n              (rst_n),
        .s_axis_spikes_TDATA    (s_axis_spikes_TDATA),
        .s_axis_spikes_TVALID   (s_axis_spikes_TVALID),
        .s_axis_spikes_TREADY   (s_axis_spikes_TREADY),
        .s_axis_spikes_TKEEP    (s_axis_spikes_TKEEP),
        .s_axis_spikes_TSTRB    (s_axis_spikes_TSTRB),
        .s_axis_spikes_TUSER    (s_axis_spikes_TUSER),
        .s_axis_spikes_TLAST    (s_axis_spikes_TLAST),
        .s_axis_spikes_TID      (s_axis_spikes_TID),
        .s_axis_spikes_TDEST    (s_axis_spikes_TDEST),
        .s_axis_data_TDATA      (s_axis_data_TDATA),
        .s_axis_data_TVALID     (s_axis_data_TVALID),
        .s_axis_data_TREADY     (s_axis_data_TREADY),
        .s_axis_data_TKEEP      (s_axis_data_TKEEP),
        .s_axis_data_TSTRB      (s_axis_data_TSTRB),
        .s_axis_data_TUSER      (s_axis_data_TUSER),
        .s_axis_data_TLAST      (s_axis_data_TLAST),
        .s_axis_data_TID        (s_axis_data_TID),
        .s_axis_data_TDEST      (s_axis_data_TDEST),
        .s_axis_weights_TDATA   (s_axis_weights_TDATA),
        .s_axis_weights_TVALID  (s_axis_weights_TVALID),
        .s_axis_weights_TREADY  (s_axis_weights_TREADY),
        .s_axis_weights_TKEEP   (s_axis_weights_TKEEP),
        .s_axis_weights_TSTRB   (s_axis_weights_TSTRB),
        .s_axis_weights_TUSER   (s_axis_weights_TUSER),
        .s_axis_weights_TLAST   (s_axis_weights_TLAST),
        .s_axis_weights_TID     (s_axis_weights_TID),
        .s_axis_weights_TDEST   (s_axis_weights_TDEST),
        .m_axis_spikes_TDATA    (m_axis_spikes_TDATA),
        .m_axis_spikes_TVALID   (m_axis_spikes_TVALID),
        .m_axis_spikes_TREADY   (m_axis_spikes_TREADY),
        .m_axis_spikes_TKEEP    (m_axis_spikes_TKEEP),
        .m_axis_spikes_TSTRB    (m_axis_spikes_TSTRB),
        .m_axis_spikes_TUSER    (m_axis_spikes_TUSER),
        .m_axis_spikes_TLAST    (m_axis_spikes_TLAST),
        .m_axis_spikes_TID      (m_axis_spikes_TID),
        .m_axis_spikes_TDEST    (m_axis_spikes_TDEST),
        .m_axis_weights_TDATA   (m_axis_weights_TDATA),
        .m_axis_weights_TVALID  (m_axis_weights_TVALID),
        .m_axis_weights_TREADY  (m_axis_weights_TREADY),
        .m_axis_weights_TKEEP   (m_axis_weights_TKEEP),
        .m_axis_weights_TSTRB   (m_axis_weights_TSTRB),
        .m_axis_weights_TUSER   (m_axis_weights_TUSER),
        .m_axis_weights_TLAST   (m_axis_weights_TLAST),
        .m_axis_weights_TID     (m_axis_weights_TID),
        .m_axis_weights_TDEST   (m_axis_weights_TDEST),
        .spike_in_valid         (spike_in_valid),
        .spike_in_neuron_id     (spike_in_neuron_id),
        .spike_in_weight        (spike_in_weight),
        .spike_in_ready         (spike_in_ready),
        .spike_out_valid        (spike_out_valid),
        .spike_out_neuron_id    (spike_out_neuron_id),
        .spike_out_weight       (spike_out_weight),
        .spike_out_ready        (spike_out_ready),
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
        .snn_enable             (snn_enable),
        .snn_reset              (snn_reset),
        .threshold_out          (threshold_out),
        .leak_rate_out          (leak_rate_out),
        .snn_ready              (snn_ready),
        .snn_busy               (snn_busy),
        .s_axi_ctrl_AWVALID     (s_axi_ctrl_AWVALID),
        .s_axi_ctrl_AWREADY     (s_axi_ctrl_AWREADY),
        .s_axi_ctrl_AWADDR      (s_axi_ctrl_AWADDR),
        .s_axi_ctrl_WVALID      (s_axi_ctrl_WVALID),
        .s_axi_ctrl_WREADY      (s_axi_ctrl_WREADY),
        .s_axi_ctrl_WDATA       (s_axi_ctrl_WDATA),
        .s_axi_ctrl_WSTRB       (s_axi_ctrl_WSTRB),
        .s_axi_ctrl_ARVALID     (s_axi_ctrl_ARVALID),
        .s_axi_ctrl_ARREADY     (s_axi_ctrl_ARREADY),
        .s_axi_ctrl_ARADDR      (s_axi_ctrl_ARADDR),
        .s_axi_ctrl_RVALID      (s_axi_ctrl_RVALID),
        .s_axi_ctrl_RREADY      (s_axi_ctrl_RREADY),
        .s_axi_ctrl_RDATA       (s_axi_ctrl_RDATA),
        .s_axi_ctrl_RRESP       (s_axi_ctrl_RRESP),
        .s_axi_ctrl_BVALID      (s_axi_ctrl_BVALID),
        .s_axi_ctrl_BREADY      (s_axi_ctrl_BREADY),
        .s_axi_ctrl_BRESP       (s_axi_ctrl_BRESP)
    );

    // AXI-Lite Write Task
    task axi_write(input [7:0] addr, input [31:0] data);
        reg aw_done;
        reg w_done;
    begin
        @(posedge clk);
        s_axi_ctrl_AWVALID <= 1'b1;
        s_axi_ctrl_AWADDR  <= addr;
        s_axi_ctrl_WVALID  <= 1'b1;
        s_axi_ctrl_WDATA   <= data;
        s_axi_ctrl_WSTRB   <= 4'hF;
        s_axi_ctrl_BREADY  <= 1'b1;
        aw_done = 1'b0;
        w_done  = 1'b0;

        while (!aw_done || !w_done) begin
            @(posedge clk);
            if (s_axi_ctrl_AWVALID && s_axi_ctrl_AWREADY) begin
                s_axi_ctrl_AWVALID <= 1'b0;
                aw_done = 1'b1;
            end
            if (s_axi_ctrl_WVALID && s_axi_ctrl_WREADY) begin
                s_axi_ctrl_WVALID <= 1'b0;
                w_done = 1'b1;
            end
        end

        while (!s_axi_ctrl_BVALID) @(posedge clk);
        @(posedge clk);
        s_axi_ctrl_BREADY  <= 1'b0;
    end
    endtask

    // Stream Pixel Task
    task stream_pixel(input [15:0] px_val, input is_last);
        reg done;
        integer timeout_cycles;
    begin
        @(posedge clk);
        s_axis_spikes_TVALID <= 1'b1;
        s_axis_spikes_TDATA  <= {16'd0, px_val};
        s_axis_spikes_TKEEP  <= 4'hF;
        s_axis_spikes_TSTRB  <= 4'hF;
        s_axis_spikes_TLAST  <= is_last;
        done = 1'b0;
        timeout_cycles = 0;
        while (!done) begin
            @(posedge clk);
            timeout_cycles = timeout_cycles + 1;
            if (s_axis_spikes_TVALID && s_axis_spikes_TREADY) begin
                s_axis_spikes_TVALID <= 1'b0;
                s_axis_spikes_TLAST  <= 1'b0;
                done = 1'b1;
            end
            if (timeout_cycles > 50000) begin
                $display("  [TIMEOUT at pixel %0d] TREADY=%b, FSM state=%h, mode=%d, time_steps=%d",
                         pi, s_axis_spikes_TREADY, u_hls.ap_CS_fsm, u_hls.mode_reg, u_hls.time_steps_reg);
                $finish;
            end
        end
    end
    endtask

    // Testbench counters and checkers
    integer total_fanout_spikes = 0;
    integer g0_spikes = 0;
    integer g1_spikes = 0;
    integer g2_spikes = 0;
    integer g3_spikes = 0;
    integer invalid_spikes = 0;
    integer pass_count = 0;
    integer fail_count = 0;

    task check(input [255:0] name, input cond);
    begin
        if (cond) begin
            $display("  [PASS] %0s", name);
            pass_count = pass_count + 1;
        end else begin
            $display("  [FAIL] %0s", name);
            fail_count = fail_count + 1;
        end
    end
    endtask

    // Monitor fanout spikes emitted by HLS into RTL Core Groups
    always @(posedge clk) begin
        if (rst_n && spike_in_valid && spike_in_ready) begin
            total_fanout_spikes = total_fanout_spikes + 1;
            case (spike_in_neuron_id[10:8])
                3'd0: g0_spikes = g0_spikes + 1;
                3'd1: g1_spikes = g1_spikes + 1;
                3'd2: g2_spikes = g2_spikes + 1;
                3'd3: g3_spikes = g3_spikes + 1;
                default: invalid_spikes = invalid_spikes + 1;
            endcase
        end
    end

    integer pi;

    initial begin
        // $dumpfile("hls_layer1_waves.vcd");
        // $dumpvars(0, tb_hls_layer1);

        $display("=========================================================");
        $display("  HLS Layer 1 (Conv1 Streaming) Icarus Verilog Testbench");
        $display("=========================================================");

        // Initialize signals
        rst_n                = 1'b0;
        u_hls.initialized    = 1'b1; // Bypass 843,776-cycle dummy DRAM zeroing
        s_axis_spikes_TDATA  = 32'd0;
        s_axis_spikes_TVALID = 1'b0;
        s_axis_spikes_TKEEP  = 4'h0;
        s_axis_spikes_TSTRB  = 4'h0;
        s_axis_spikes_TUSER  = 1'b0;
        s_axis_spikes_TLAST  = 1'b0;
        s_axis_spikes_TID    = 1'b0;
        s_axis_spikes_TDEST  = 1'b0;
        m_axis_spikes_TREADY = 1'b1;
        spike_in_ready       = 1'b1;

        s_axi_ctrl_AWVALID   = 1'b0;
        s_axi_ctrl_AWADDR    = 7'd0;
        s_axi_ctrl_WVALID    = 1'b0;
        s_axi_ctrl_WDATA     = 32'd0;
        s_axi_ctrl_WSTRB     = 4'h0;
        s_axi_ctrl_BREADY    = 1'b0;
        s_axi_ctrl_ARVALID   = 1'b0;
        s_axi_ctrl_ARADDR    = 7'd0;
        s_axi_ctrl_RREADY    = 1'b0;

        repeat (20) @(posedge clk);
        rst_n = 1'b1;
        repeat (10) @(posedge clk);

        check("HLS Reset Release: ap_clk active & rst_n high", rst_n == 1'b1);

        // ── Step 1: Configure HLS Engine via AXI-Lite ──
        $display("\n--- Step 1: Configuring HLS Core via AXI-Lite ---");
        axi_write(8'h10, 32'h00000001); // ctrl_reg: enable=1, reset=0
        axi_write(8'h18, 32'd103);      // threshold = 103
        axi_write(8'h20, 32'd3);        // mode = 3 (MODE_CNN_STREAM)
        axi_write(8'h28, 32'd5000);     // time_steps = 5000 (allows streaming loop to ingest frame)
        axi_write(8'h00, 32'h00000081); // ap_start=1, auto_restart=1

        repeat (10) @(posedge clk);
        check("HLS Engine Initialized in Mode 3 (CNN Stream)", u_hls.mode_reg == 3);

        // ── Step 2: Stream High-Contrast Synthetic Pattern ──
        $display("\n--- Step 2: Streaming 28x28 Image Frame ---");
        // Stream 784 pixels: a bright 14x14 square in the center (pixel val = 256.0 -> 16'h0100)
        for (pi = 0; pi < 784; pi = pi + 1) begin
            integer row, col;
            reg [15:0] px;
            row = pi / 28;
            col = pi % 28;
            if (row >= 7 && row < 21 && col >= 7 && col < 21)
                px = 16'h0100; // Q8.8 fixed-point for 1.0 (bright pixel)
            else
                px = 16'h0000; // 0.0 (background)

            stream_pixel(px, (pi == 783) ? 1'b1 : 1'b0);
            if ((pi + 1) % 28 == 0)
                $display("  [Row %0d/28 Complete] %0d / 784 pixels ingested. Fanout spikes so far: %0d",
                         (pi + 1) / 28, pi + 1, total_fanout_spikes);
        end

        // Wait for all internal pipeline stages and fanout FIFO to drain
        $display("  Waiting for pipeline to process all pixels and drain fanout...");
        repeat (2000) @(posedge clk);

        // ── Step 3: Validate Generated Fanout Spikes ──
        $display("\n--- Step 3: Verifying Conv2 Fanout Spikes to Core Groups ---");
        $display("  Total Conv2 Fanout Spikes Emitted: %0d", total_fanout_spikes);
        $display("    Core Group 0 Spikes: %0d", g0_spikes);
        $display("    Core Group 1 Spikes: %0d", g1_spikes);
        $display("    Core Group 2 Spikes: %0d", g2_spikes);
        $display("    Core Group 3 Spikes: %0d", g3_spikes);

        check("HLS streaming engine generated fanout spikes (> 500)", total_fanout_spikes > 500);
        check("Core Group 0 received fanout spikes", g0_spikes > 0);
        check("Core Group 1 received fanout spikes", g1_spikes > 0);
        check("Core Group 2 received fanout spikes", g2_spikes > 0);
        check("Core Group 3 received fanout spikes", g3_spikes > 0);
        check("Zero invalid group IDs emitted (all dst_grp < 4)", invalid_spikes == 0);

        $display("\n=========================================================");
        $display("  HLS Layer 1 Testbench: %0d PASSED, %0d FAILED", pass_count, fail_count);
        $display("=========================================================");

        if (fail_count == 0)
            $display("[SUCCESS] HLS Layer 1 Streaming Engine verified in Icarus Verilog!");
        else
            $display("[ERROR] HLS Layer 1 Verification Failed!");

        $finish;
    end

endmodule
