//-----------------------------------------------------------------------------
// Title       : Testbench for Spike Convolution AGU
// Description : Verification of Loihi-style convolutional address generation
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps
`include "snn_params.vh"

module tb_spike_conv_agu;

    //=========================================================================
    // Parameters
    //=========================================================================
    localparam CLK_PERIOD_NS = 12.5;  // 80 MHz clock

    localparam KERNEL_SIZE     = 3;
    localparam INPUT_WIDTH     = 8;
    localparam INPUT_HEIGHT    = 8;
    localparam NUM_CHANNELS    = 2;
    localparam STRIDE          = 1;

    //=========================================================================
    // DUT Instance
    //=========================================================================
    wire [31:0] conv_spikes_processed;
    wire [31:0] conv_address_errors;

    spike_conv_agu #(
        .KERNEL_SIZE     (KERNEL_SIZE),
        .INPUT_WIDTH     (INPUT_WIDTH),
        .INPUT_HEIGHT    (INPUT_HEIGHT),
        .NUM_CHANNELS    (NUM_CHANNELS),
        .STRIDE          (STRIDE)
    ) dut (
        .clk                 (clk),
        .rst_n               (rst_n),
        .enable              (enable),

        .s_axis_spike_tvalid (s_axis_spike_tvalid),
        .s_axis_spike_tdata  (s_axis_spike_tdata),
        .s_axis_spike_tready (s_axis_spike_tready),

        .m_axis_spike_tvalid (m_axis_spike_tvalid),
        .m_axis_spike_tdata  (m_axis_spike_tdata),
        .m_axis_spike_tready (m_axis_spike_tready),

        .kernel_weight_out   (),
        .kernel_weight_in    ()

    );

    //=========================================================================
    // Clock Generation
    //=========================================================================
    reg clk = 0;
    always begin
        #(`CLK_PERIOD_NS/2) clk = ~clk;
    end

    //=========================================================================
    // Reset and Enable Control
    //=========================================================================
    reg rst_n = 0;
    reg enable = 0;

    initial begin
        // Apply reset
        rst_n = 0;
        #(`CLK_PERIOD_NS * 10);
        rst_n = 1;
        enable = 1;
    end

    //=========================================================================
    // AXI-Stream Input Interface
    //=========================================================================
    reg s_axis_spike_tvalid;
    reg [31:0] s_axis_spike_tdata;

    wire s_axis_spike_tready;

    //=========================================================================
    // AXI-Stream Output Interface
    //=========================================================================
    wire m_axis_spike_tvalid;
    wire [31:0] m_axis_spike_tdata;
    reg m_axis_spike_tready = 0;

    //=========================================================================
    // Test Tasks
    //=========================================================================

    task send_spike;
        input [7:0] x, y, channel;
        begin
            s_axis_spike_tvalid = 1;
            s_axis_spike_tdata = {x, y, channel, 8'd0};
            @(posedge clk);
            while (!s_axis_spike_tready) @(posedge clk);
            s_axis_spike_tvalid = 0;
        end
    endtask

    task wait_for_output;
        begin
            @(posedge m_axis_spike_tvalid);
            #1;
        end
    endtask

    //=========================================================================
    // Test Sequences
    //=========================================================================

    integer i, j, c;
    reg [31:0] output_count;

    initial begin
        $display("========================================");
        $display("Spike Convolution AGU Testbench");
        $display("Kernel Size: %d", KERNEL_SIZE);
        $display("Input: %dx%d @ %d channels", INPUT_WIDTH, INPUT_HEIGHT, NUM_CHANNELS);
        $display("Stride: %d", STRIDE);
        $display("========================================");

        // Wait for reset
        @(negedge rst_n);
        @(posedge rst_n);

        // Test 1: Single spike at center
        $display("\n[Test 1] Single spike at (4,4) channel 0");
        output_count = 0;
        send_spike(4, 4, 0);
        wait_for_output;
        $display("Output: dest_id=%h weight_idx=%d", m_axis_spike_tdata[31:0], m_axis_spike_tdata[15:0]);
        output_count = output_count + 1;

        // Test 2: Spike at corner
        $display("\n[Test 2] Single spike at (0,0) channel 1");
        send_spike(0, 0, 1);
        wait_for_output;
        $display("Output: dest_id=%h weight_idx=%d", m_axis_spike_tdata[31:0], m_axis_spike_tdata[15:0]);
        output_count = output_count + 1;

        // Test 3: Multiple spikes across different channels
        $display("\n[Test 3] Spike scan across all channels");
        for (c = 0; c < NUM_CHANNELS; c = c + 1) begin
            send_spike(4, 4, c);
            wait_for_output;
            $display("Channel %d: dest_id=%h weight_idx=%d", c,
                     m_axis_spike_tdata[31:0], m_axis_spike_tdata[15:0]);
            output_count = output_count + 1;
        end

        // Test 4: Edge spike (should produce invalid destination)
        $display("\n[Test 4] Edge spike at (7,7) - near boundary");
        send_spike(7, 7, 0);
        wait_for_output;
        $display("Output: dest_id=%h weight_idx=%d", m_axis_spike_tdata[31:0], m_axis_spike_tdata[15:0]);
        output_count = output_count + 1;

        // Summary
        #(`CLK_PERIOD_NS * 10);
        $display("\n========================================");
        $display("Test Complete");
        $display("Total outputs: %d", output_count);
        $display("Spikes processed: %d", dut.conv_spikes_processed);
        $display("Address errors: %d", dut.conv_address_errors);
        $display("========================================");

        #(`CLK_PERIOD_NS * 5);
        $finish;
    end

endmodule
