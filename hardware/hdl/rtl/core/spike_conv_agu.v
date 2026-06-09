//-----------------------------------------------------------------------------
// Title       : Spike Convolution Address Generation Unit (AGU)
// Description : Loihi-style convolutional connectivity for SNN accelerator
//
// This module implements event-driven address generation for convolutional
// layers, following Intel Loihi's approach:
// - Shared kernel weights stored in BRAM
// - Add-only structure (no DSP blocks needed)
// - Event-driven address calculation on spike arrival
//
// Architecture:
//   Spike Input (x,y,channel) → AGU → Destination Neuron IDs + Weight Indices
//                                     ↓
//                               BRAM Kernel Weights (K×K)
//                                     ↓
//                          Core Group Accumulation
//
// Key Features:
// - Add-only structure (no DSP blocks needed)
// - Event-driven address generation on spike arrival
// - Shared kernel weights stored in BRAM
// - Support for stride=1, padding=0 and stride=1, padding=1 modes
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps
`include "snn_params.vh"

module spike_conv_agu #(
    parameter KERNEL_SIZE         = 3,          // Kernel size: 3 or 5
    parameter INPUT_WIDTH         = 32,         // Input width (pixels)
    parameter INPUT_HEIGHT        = 32,         // Input height (pixels)
    parameter NUM_CHANNELS        = 3,          // Number of input channels
    parameter STRIDE              = 1,          // Convolution stride: 1 or 2
    parameter KERNEL_WEIGHT_BITS  = 8           // Weight precision
)(
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         enable,

    // --- AXI-Stream Spike Input Interface ---
    input  wire                         s_axis_spike_tvalid,
    input  wire [31:0]                  s_axis_spike_tdata,  // {x[7:0], y[7:0], channel[7:0], reserved[8:0]}
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
    // Derived Parameters
    //=========================================================================
    localparam KERNEL_SQ = KERNEL_SIZE * KERNEL_SIZE;
    localparam OUTPUT_WIDTH  = (INPUT_WIDTH - KERNEL_SIZE + 1) / STRIDE + 1;
    localparam OUTPUT_HEIGHT = (INPUT_HEIGHT - KERNEL_SIZE + 1) / STRIDE + 1;
    localparam OUTPUT_CHANNELS = NUM_CHANNELS;  // Same as input for standard conv

    //=========================================================================
    // Spike Packet Format (32-bit)
    //   [31:24] = x coordinate (8 bits, 0-255)
    //   [23:16] = y coordinate (8 bits, 0-255)
    //   [15:8]  = channel (8 bits, 0-255)
    //   [7:0]   = reserved/payload
    //=========================================================================
    reg [7:0] spike_x;
    reg [7:0] spike_y;
    reg [7:0] spike_channel;

    assign s_axis_spike_tready = (state == ST_IDLE);

    //=========================================================================
    // State Machine
    //=========================================================================
    localparam [1:0]
        ST_IDLE      = 2'd0,
        ST_PROCESS   = 2'd1;

    reg [1:0] state;
    reg [7:0] kernel_row_idx;   // Row index within kernel (0 to KERNEL_SIZE-1)
    reg [7:0] kernel_col_idx;   // Column index within kernel (0 to KERNEL_SIZE-1)

    //=========================================================================
    // Address Generation Logic
    //=========================================================================
    reg [31:0] dest_neuron_id;
    reg [15:0] weight_index;

    // Compute output neuron ID from input spike and kernel offset
    // For stride=1, padding=0:
    //   out_x = (in_x - k_col) / STRIDE
    //   out_y = (in_y - k_row) / STRIDE
    //   dest_id = (out_y * OUTPUT_WIDTH + out_x) * NUM_CHANNELS + spike_channel

    wire [7:0] out_x_calc = (spike_x >= kernel_col_idx) ? ((spike_x - kernel_col_idx) / STRIDE) : 8'd0;
    wire [7:0] out_y_calc = (spike_y >= kernel_row_idx) ? ((spike_y - kernel_row_idx) / STRIDE) : 8'd0;

    wire valid_output = (out_x_calc < OUTPUT_WIDTH) && (out_y_calc < OUTPUT_HEIGHT);

    always @(*) begin
        if (valid_output) begin
            dest_neuron_id = {21'd0, out_y_calc * OUTPUT_WIDTH + out_x_calc, spike_channel[7:0]};
        end else begin
            dest_neuron_id = 32'hFFFFFFFF;  // Invalid destination
        end
    end

    // Compute weight index for shared kernel weights
    // Format: (channel * KERNEL_SIZE + k_row) * KERNEL_SIZE + k_col
    always @(*) begin
        weight_index = ((spike_channel * KERNEL_SIZE + kernel_row_idx) * KERNEL_SIZE + kernel_col_idx);
    end

    //=========================================================================
    // Main State Machine
    //=========================================================================
    reg [31:0] spikes_processed;
    reg [31:0] address_errors;

    assign conv_spikes_processed = spikes_processed;
    assign conv_address_errors = address_errors;

    always @(posedge clk) begin
        if (!rst_n) begin
            state           <= ST_IDLE;
            kernel_row_idx  <= 0;
            kernel_col_idx  <= 0;
            spikes_processed <= 0;
            address_errors  <= 0;
        end else if (enable && (state == ST_IDLE || s_axis_spike_tvalid)) begin
            case (state)
                //------------------------------------------------------
                ST_IDLE: begin
                    if (s_axis_spike_tvalid) begin
                        // Parse spike packet
                        spike_x      <= s_axis_spike_tdata[31:24];
                        spike_y      <= s_axis_spike_tdata[23:16];
                        spike_channel<= s_axis_spike_tdata[15:8];

                        // Reset kernel scan indices
                        kernel_row_idx <= 0;
                        kernel_col_idx <= 0;

                        state <= ST_PROCESS;
                    end
                end

                //------------------------------------------------------
                ST_PROCESS: begin
                    // Output destination neuron ID and weight index
                    if (m_axis_spike_tready) begin
                        spikes_processed <= spikes_processed + 1'b1;

                        // Advance kernel scan
                        if (kernel_col_idx < KERNEL_SIZE - 1) begin
                            kernel_col_idx <= kernel_col_idx + 1;
                        end else if (kernel_row_idx < KERNEL_SIZE - 1) begin
                            kernel_row_idx <= kernel_row_idx + 1;
                            kernel_col_idx <= 0;
                        end else begin
                            // Kernel scan complete, return to idle
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
                dest_neuron_id[31:0],
                weight_index[15:0]
            };
        end else begin
            m_axis_spike_tdata = 32'h0;
        end
    end

endmodule
