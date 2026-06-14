//-----------------------------------------------------------------------------
// Title       : Spike Convolution Connectivity Table - shared-kernel EventConv
// Description : BRAM-based convolutional connectivity with shared kernel weights.
//
// This module implements shared-kernel EventConv:
// - Shared kernel weights stored in small BRAM (3x3 or 5x5)
// - Event-driven address generation for receptive field
// - Add-only accumulation (no DSP blocks needed)
//
// Address Scheme (for 3x3 kernel, stride=1):
//   addr = {dst_group(4), dst_neuron[7:0]} = 12 bits
//   Total: 4,096 entries for 512 neurons
//
// Data Format:
//   [31:24] = spike_x (8 bits)
//   [23:16] = spike_y (8 bits)
//   [15:8]  = channel (8 bits)
//   [7:0]   = kernel_weight_idx (8 bits, 0-8 for 3x3, 0-24 for 5x5)
//
// Operation:
//   When a spike arrives at (x,y,channel), the AGU computes all
//   destination neurons in the receptive field and their corresponding
//   kernel weight indices. The table stores these mappings.
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps
`include "spikemold_params.vh"

module spike_conv_connectivity_table #(
    parameter KERNEL_SIZE         = 3,          // Kernel size: 3 or 5
    parameter NUM_DST_NEURONS     = 512,        // Number of destination neurons
    parameter NUM_CHANNELS        = 3,          // Number of input channels
    parameter STRIDE              = 1,          // Convolution stride: 1 or 2
    parameter GROUP_ID_WIDTH      = 4,
    parameter LOCAL_ID_WIDTH      = $clog2(NUM_DST_NEURONS)
)(
    input  wire                       clk,
    input  wire                       rst_n,

    // --- Write Port (Configuration from Host/HLS) ---
    input  wire                       cfg_we,
    input  wire [GROUP_ID_WIDTH-1:0]  cfg_dst_group,
    input  wire [LOCAL_ID_WIDTH-1:0]  cfg_dst_neuron,
    input  wire [7:0]                 cfg_spike_x,      // Input spike x coordinate
    input  wire [7:0]                 cfg_spike_y,      // Input spike y coordinate
    input  wire [7:0]                 cfg_channel,      // Input channel
    input  wire [7:0]                 cfg_kernel_weight_idx,
    input  wire                       route_clear_start,

    // --- Lookup Port (Query from Event Router) ---
    input  wire                       lookup_en,
    input  wire [GROUP_ID_WIDTH-1:0]  lookup_dst_group,
    input  wire [LOCAL_ID_WIDTH-1:0]  lookup_dst_neuron,

    // --- Lookup Result ---
    output reg                        result_valid,
    output reg  [7:0]                 result_spike_x,
    output reg  [7:0]                 result_spike_y,
    output reg  [7:0]                 result_channel,
    output reg  [7:0]                 result_kernel_weight_idx,

    // --- Runtime status ---
    output reg                        route_clear_busy,
    output reg                        route_clear_done,
    output reg  [31:0]                route_entry_count
);

    //=========================================================================
    // Derived Parameters
    //=========================================================================
    localparam KERNEL_SQ = KERNEL_SIZE * KERNEL_SIZE;

    // For stride=1, padding=0:
    //   input_x = output_x * STRIDE + kernel_col
    //   input_y = output_y * STRIDE + kernel_row

    localparam TABLE_ADDR_WIDTH = GROUP_ID_WIDTH + LOCAL_ID_WIDTH;
    localparam TABLE_DEPTH      = 1 << TABLE_ADDR_WIDTH;

    //=========================================================================
    // Connection Table - BRAM
    //=========================================================================
    localparam TABLE_DATA_WIDTH = 32;  // Full 32-bit entries

    reg [TABLE_DATA_WIDTH-1:0] conv_table [0:TABLE_DEPTH-1];

    // Address construction
    wire [TABLE_ADDR_WIDTH-1:0] wr_addr = {cfg_dst_group, cfg_dst_neuron};
    wire [TABLE_ADDR_WIDTH-1:0] rd_addr = {lookup_dst_group, lookup_dst_neuron};

    //=========================================================================
    // Write Port (Configuration)
    //=========================================================================
    always @(posedge clk) begin
        if (!rst_n) begin
            route_entry_count <= 0;
        end else if (cfg_we && !route_clear_start) begin
            conv_table[wr_addr] <= {
                cfg_spike_x,
                cfg_spike_y,
                cfg_channel,
                cfg_kernel_weight_idx
            };
            route_entry_count <= route_entry_count + 1'b1;
        end else if (route_clear_start) begin
            route_entry_count <= 0;
        end
    end

    //=========================================================================
    // Read Port (Lookup)
    //=========================================================================
    always @(posedge clk) begin
        if (!rst_n) begin
            result_valid         <= 0;
            result_spike_x       <= 0;
            result_spike_y       <= 0;
            result_channel       <= 0;
            result_kernel_weight_idx <= 0;
        end else if (lookup_en) begin
            result_valid             <= 1;
            result_spike_x           <= conv_table[rd_addr][31:24];
            result_spike_y           <= conv_table[rd_addr][23:16];
            result_channel           <= conv_table[rd_addr][15:8];
            result_kernel_weight_idx <= conv_table[rd_addr][7:0];
        end else begin
            result_valid <= 0;
        end
    end

endmodule
