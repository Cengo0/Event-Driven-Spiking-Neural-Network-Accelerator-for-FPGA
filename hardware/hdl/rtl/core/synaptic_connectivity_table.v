//-----------------------------------------------------------------------------
// Title         : Synaptic Connectivity Table - Sparse Inter-Group Connections
// Project       : PYNQ-Z2 SNN Accelerator
// File          : synaptic_connectivity_table.v
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : BRAM-based sparse inter-group connection table.
//                 Stores cross-group synaptic connections indexed by source.
//
// Address Scheme:
//   addr = {src_group(3), src_neuron(7), fanout_idx(4)} = 14 bits
//   Total: 16,384 entries
//
// Data Format (16 bits):
//   [15]     valid       — entry is active
//   [14:12]  dst_group   — destination core group ID
//   [11:5]   dst_neuron  — destination neuron within group
//   [4:1]    weight      — 4-bit synaptic weight (unsigned magnitude)
//   [0]      exc_inh     — 1=excitatory, 0=inhibitory
//
// Read Interface:
//   Given a source spike (src_group, src_neuron), the event router
//   iterates fanout_idx = 0..MAX_FANOUT-1 to look up all connections.
//   Iteration stops when valid=0 (end of connection list).
//
// Resource Budget:
//   - 16,384 × 16b = 262,144 bits → 15 BRAM18K
//   - Connection count array: 1,024 × 4b → LUTRAM
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps

module synaptic_connectivity_table #(
    parameter NUM_GROUPS        = 8,
    parameter NEURONS_PER_GROUP = 128,
    parameter WEIGHT_WIDTH      = 4,
    parameter MAX_FANOUT_INTER  = 16,           // Max inter-group connections per neuron
    parameter GROUP_ID_WIDTH    = $clog2(NUM_GROUPS),
    parameter LOCAL_ID_WIDTH    = $clog2(NEURONS_PER_GROUP),
    parameter GLOBAL_ID_WIDTH   = GROUP_ID_WIDTH + LOCAL_ID_WIDTH,
    parameter FANOUT_IDX_WIDTH  = $clog2(MAX_FANOUT_INTER)
)(
    input  wire                       clk,
    input  wire                       rst_n,

    // --- Write Port (Configuration from Host/HLS) ---
    input  wire                       cfg_we,
    input  wire [GROUP_ID_WIDTH-1:0]  cfg_src_group,
    input  wire [LOCAL_ID_WIDTH-1:0]  cfg_src_neuron,
    input  wire [FANOUT_IDX_WIDTH-1:0] cfg_fanout_idx,
    input  wire                       cfg_valid,        // Entry valid flag
    input  wire [GROUP_ID_WIDTH-1:0]  cfg_dst_group,
    input  wire [LOCAL_ID_WIDTH-1:0]  cfg_dst_neuron,
    input  wire [WEIGHT_WIDTH-1:0]    cfg_weight,
    input  wire                       cfg_exc_inh,

    // --- Lookup Port (Query from Event Router) ---
    input  wire                       lookup_en,
    input  wire [GROUP_ID_WIDTH-1:0]  lookup_src_group,
    input  wire [LOCAL_ID_WIDTH-1:0]  lookup_src_neuron,
    input  wire [FANOUT_IDX_WIDTH-1:0] lookup_fanout_idx,

    // --- Lookup Result (1 cycle latency) ---
    output reg                        result_valid,
    output reg  [GROUP_ID_WIDTH-1:0]  result_dst_group,
    output reg  [LOCAL_ID_WIDTH-1:0]  result_dst_neuron,
    output reg  [WEIGHT_WIDTH-1:0]    result_weight,
    output reg                        result_exc_inh,
    output reg                        result_entry_valid  // The "valid" bit from table
);

    //=========================================================================
    // Connection Table - Dual-Port BRAM
    //=========================================================================
    localparam TABLE_ADDR_WIDTH = GROUP_ID_WIDTH + LOCAL_ID_WIDTH + FANOUT_IDX_WIDTH;
    localparam TABLE_DEPTH      = 1 << TABLE_ADDR_WIDTH;
    localparam TABLE_DATA_WIDTH = 1 + GROUP_ID_WIDTH + LOCAL_ID_WIDTH + WEIGHT_WIDTH + 1; // 16 bits

    // Connection memory
    reg [TABLE_DATA_WIDTH-1:0] conn_mem [0:TABLE_DEPTH-1];

    // Address construction
    wire [TABLE_ADDR_WIDTH-1:0] wr_addr = {cfg_src_group, cfg_src_neuron, cfg_fanout_idx};
    wire [TABLE_ADDR_WIDTH-1:0] rd_addr = {lookup_src_group, lookup_src_neuron, lookup_fanout_idx};

    // Data packing
    wire [TABLE_DATA_WIDTH-1:0] wr_data = {
        cfg_valid,
        cfg_dst_group,
        cfg_dst_neuron,
        cfg_weight,
        cfg_exc_inh
    };

    // Port A: Write (config)
    always @(posedge clk) begin
        if (cfg_we)
            conn_mem[wr_addr] <= wr_data;
    end

    // Port B: Read (lookup) — 1 cycle latency for BRAM
    reg [TABLE_DATA_WIDTH-1:0] rd_data;

    always @(posedge clk) begin
        rd_data <= conn_mem[rd_addr];
    end

    // Pipeline lookup_en to align with rd_data (both 1-cycle delayed)
    reg lookup_en_d1;
    always @(posedge clk) begin
        if (!rst_n)
            lookup_en_d1 <= 0;
        else
            lookup_en_d1 <= lookup_en;
    end

    // Unpack read data — uses lookup_en_d1 so data and valid are aligned
    always @(posedge clk) begin
        if (!rst_n) begin
            result_valid       <= 0;
            result_entry_valid <= 0;
            result_dst_group   <= 0;
            result_dst_neuron  <= 0;
            result_weight      <= 0;
            result_exc_inh     <= 0;
        end else begin
            result_valid <= lookup_en_d1;
            if (lookup_en_d1) begin
                result_entry_valid <= rd_data[TABLE_DATA_WIDTH-1];
                result_dst_group   <= rd_data[TABLE_DATA_WIDTH-2 : TABLE_DATA_WIDTH-1-GROUP_ID_WIDTH];
                result_dst_neuron  <= rd_data[WEIGHT_WIDTH+1 +: LOCAL_ID_WIDTH];
                result_weight      <= rd_data[1 +: WEIGHT_WIDTH];
                result_exc_inh     <= rd_data[0];
            end else begin
                result_entry_valid <= 0;
            end
        end
    end

    //=========================================================================
    // Memory initialization (simulation only)
    //=========================================================================
    integer init_i;
    initial begin
        for (init_i = 0; init_i < TABLE_DEPTH; init_i = init_i + 1)
            conn_mem[init_i] = {TABLE_DATA_WIDTH{1'b0}};
    end

endmodule
