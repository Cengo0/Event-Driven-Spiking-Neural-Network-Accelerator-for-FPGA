//-----------------------------------------------------------------------------
// Title       : Spike Convolution Layer - shared-kernel EventConv Implementation
// Description : Complete convolution layer with shared weights and AGU.
//
// This module implements shared-kernel EventConv:
// - Shared kernel weights stored in small BRAM (3x3 or 5x5)
// - Event-driven address generation for receptive field
// - Add-only accumulation (no DSP blocks needed)
// - Sparsity-aware: only processes active spikes
//
// Architecture:
//   Input Spike → AGU → Connectivity Table → SpikeMold Coregroup Accumulation
//                    ↓
//              BRAM Kernel Weights (K×K)
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps
`include "spikemold_params.vh"

module spike_conv_layer #(
    parameter KERNEL_SIZE         = 3,          // Kernel size: 3 or 5
    parameter INPUT_WIDTH         = 32,         // Input width (pixels)
    parameter INPUT_HEIGHT        = 32,         // Input height (pixels)
    parameter NUM_CHANNELS        = 3,          // Number of input channels
    parameter NUM_DST_NEURONS     = 512,        // Number of destination neurons
    parameter STRIDE              = 1,          // Convolution stride: 1 or 2
    parameter KERNEL_WEIGHT_BITS  = 8           // Weight precision
)(
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         enable,

    // --- AXI-Stream Input Spike Interface ---
    input  wire                         s_axis_spike_tvalid,
    input  wire [31:0]                  s_axis_spike_tdata,  // {x[7:0], y[7:0], channel[7:0], payload[8:0]}
    output reg                          s_axis_spike_tready,

    // --- Output Spike Interface (to Core Groups) ---
    output wire                         m_axis_spike_tvalid,
    output reg [31:0]                   m_axis_spike_tdata,   // {dest_id[10:0], weight_idx[7:0]}
    input  wire                         m_axis_spike_tready,

    // --- Kernel Weight BRAM Interface ---
    output reg [KERNEL_WEIGHT_BITS-1:0] kernel_weight_out,
    input  wire [KERNEL_WEIGHT_BITS-1:0] kernel_weight_in [0:(KERNEL_SIZE*KERNEL_SIZE*NUM_CHANNELS)-1],

    // --- Status ---
    output wire [31:0]                  conv_spikes_processed,
    output wire [31:0]                  conv_address_errors
);

    //=========================================================================
    // Internal Signals
    //=========================================================================
    wire [7:0] agu_spike_x;
    wire [7:0] agu_spike_y;
    wire [7:0] agu_channel;

    wire [7:0] ct_spike_x;
    wire [7:0] ct_spike_y;
    wire [7:0] ct_channel;
    wire [7:0] ct_kernel_weight_idx;
    wire       ct_result_valid;

    // AGU output
    reg [31:0] agu_dest_id;
    reg [15:0] agu_weight_idx;

    //=========================================================================
    // Spike-driven Address Generation Unit (AGU)
    //=========================================================================
    reg [7:0] kernel_row_idx;
    reg [7:0] kernel_col_idx;
    reg [31:0] spikes_processed;

    assign conv_spikes_processed = spikes_processed;
    assign conv_address_errors = 0;  // TODO: add error counting

    // Parse spike packet
    always @(*) begin
        agu_spike_x      = s_axis_spike_tdata[31:24];
        agu_spike_y      = s_axis_spike_tdata[23:16];
        agu_channel      = s_axis_spike_tdata[15:8];
    end

    // Compute output neuron ID from input spike and kernel offset
    localparam OUTPUT_WIDTH  = (INPUT_WIDTH - KERNEL_SIZE + 1) / STRIDE + 1;
    localparam OUTPUT_HEIGHT = (INPUT_HEIGHT - KERNEL_SIZE + 1) / STRIDE + 1;

    wire [7:0] out_x_calc = (agu_spike_x >= kernel_col_idx) ? ((agu_spike_x - kernel_col_idx) / STRIDE) : 8'd0;
    wire [7:0] out_y_calc = (agu_spike_y >= kernel_row_idx) ? ((agu_spike_y - kernel_row_idx) / STRIDE) : 8'd0;

    wire valid_output = (out_x_calc < OUTPUT_WIDTH) && (out_y_calc < OUTPUT_HEIGHT);

    always @(*) begin
        if (valid_output) begin
            agu_dest_id = {21'd0, out_y_calc * OUTPUT_WIDTH + out_x_calc, agu_channel[7:0]};
        end else begin
            agu_dest_id = 32'hFFFFFFFF;  // Invalid destination
        end
    end

    // Compute weight index for shared kernel weights
    always @(*) begin
        agu_weight_idx = ((agu_channel * KERNEL_SIZE + kernel_row_idx) * KERNEL_SIZE + kernel_col_idx);
    end

    //=========================================================================
    // Connectivity Table Lookup (for shared-kernel mapping)
    //=========================================================================
    wire lookup_en;
    assign lookup_en = enable && s_axis_spike_tvalid;

    spike_conv_connectivity_table #(
        .KERNEL_SIZE     (KERNEL_SIZE),
        .NUM_DST_NEURONS (NUM_DST_NEURONS),
        .NUM_CHANNELS    (NUM_CHANNELS),
        .STRIDE          (STRIDE)
    ) u_conv_ct (
        .clk                  (clk),
        .rst_n                (rst_n),
        .cfg_we               (1'b0),  // Config via host
        .route_clear_start    (1'b0),

        .lookup_en            (lookup_en),
        .lookup_dst_group     (agu_dest_id[31:21]),
        .lookup_dst_neuron    (agu_dest_id[20:0]),

        .result_valid         (ct_result_valid),
        .result_spike_x       (ct_spike_x),
        .result_spike_y       (ct_spike_y),
        .result_channel       (ct_channel),
        .result_kernel_weight_idx(ct_kernel_weight_idx),

        .route_entry_count    ()
    );

    //=========================================================================
    // State Machine for Kernel Scanning
    //=========================================================================
    localparam [1:0]
        ST_IDLE      = 2'd0,
        ST_PROCESS   = 2'd1;

    reg [1:0] state;
    reg kernel_scan_done;

    always @(posedge clk) begin
        if (!rst_n) begin
            state           <= ST_IDLE;
            kernel_row_idx  <= 0;
            kernel_col_idx  <= 0;
            spikes_processed <= 0;
        end else if (enable && s_axis_spike_tvalid) begin
            case (state)
                ST_IDLE: begin
                    // Reset kernel scan indices on new spike
                    kernel_row_idx <= 0;
                    kernel_col_idx <= 0;

                    if (m_axis_spike_tready) begin
                        state <= ST_PROCESS;
                    end
                end

                ST_PROCESS: begin
                    if (m_axis_spike_tready) begin
                        spikes_processed <= spikes_processed + 1'b1;

                        // Advance kernel scan
                        if (kernel_col_idx < KERNEL_SIZE - 1) begin
                            kernel_col_idx <= kernel_col_idx + 1;
                        end else if (kernel_row_idx < KERNEL_SIZE - 1) begin
                            kernel_row_idx <= kernel_row_idx + 1;
                            kernel_col_idx <= 0;
                        end else begin
                            state <= ST_IDLE;
                        end
                    end
                end

                default: state <= ST_IDLE;
            endcase
        end
    end

    //=========================================================================
    // Output Interface
    //=========================================================================
    always @(*) begin
        m_axis_spike_tvalid = (state == ST_PROCESS) && m_axis_spike_tready;

        if (m_axis_spike_tvalid) begin
            m_axis_spike_tdata = {
                agu_dest_id[31:0],
                agu_weight_idx[15:0]
            };
        end else begin
            m_axis_spike_tdata = 32'h0;
        end
    end

    assign s_axis_spike_tready = (state == ST_IDLE);

endmodule
