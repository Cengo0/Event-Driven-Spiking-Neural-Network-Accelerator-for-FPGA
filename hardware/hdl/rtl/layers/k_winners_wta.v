//-----------------------------------------------------------------------------
// Title         : K-Winners-Take-All with Spatial Inhibition Radius
// Project       : PYNQ-Z2 SNN Accelerator
// File          : k_winners_wta.v
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : Winner-Take-All mechanism for Mozafari et al. R-STDP
//
//                 Selects k winners (neurons with highest potentials) with
//                 spatial inhibition radius. When a winner is selected,
//                 neurons within radius are inhibited from being selected.
//
//                 Key features:
//                 - Iteratively finds top-k potentials
//                 - Applies spatial inhibition after each winner
//                 - Supports configurable k and radius
//                 - Compatible with STDP learning
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps

module k_winners_wta #(
    parameter HEIGHT        = 10,       // Feature map height
    parameter WIDTH         = 10,       // Feature map width
    parameter CHANNELS      = 100,      // Number of features/filters
    parameter VMEM_WIDTH    = 16,       // Membrane potential precision
    parameter MAX_WINNERS   = 5,        // Maximum k value
    parameter MAX_RADIUS    = 4         // Maximum inhibition radius
)(
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         enable,
    
    //=========================================================================
    // Control Interface
    //=========================================================================
    input  wire                         start,
    input  wire [$clog2(MAX_WINNERS):0] k,              // Number of winners
    input  wire [$clog2(MAX_RADIUS):0]  radius,         // Inhibition radius
    input  wire [VMEM_WIDTH-1:0]        threshold,      // Minimum threshold
    output reg                          done,
    output wire                         busy,
    
    //=========================================================================
    // Membrane Potential Input
    // Assumes potentials are provided sequentially or via memory interface
    //=========================================================================
    output reg                          vmem_rd_en,
    output reg  [$clog2(CHANNELS)-1:0]  vmem_ch_addr,
    output reg  [$clog2(HEIGHT)-1:0]    vmem_row_addr,
    output reg  [$clog2(WIDTH)-1:0]     vmem_col_addr,
    input  wire [VMEM_WIDTH-1:0]        vmem_data,
    input  wire                         vmem_valid,
    
    //=========================================================================
    // Winner Output
    //=========================================================================
    output reg                          winner_valid,
    output reg  [$clog2(CHANNELS)-1:0]  winner_ch,
    output reg  [$clog2(HEIGHT)-1:0]    winner_row,
    output reg  [$clog2(WIDTH)-1:0]     winner_col,
    output reg  [VMEM_WIDTH-1:0]        winner_potential,
    output reg  [$clog2(MAX_WINNERS):0] winner_index,   // 0 to k-1
    input  wire                         winner_ready,
    
    //=========================================================================
    // Spike Output (for all winners combined)
    //=========================================================================
    output reg  [CHANNELS*HEIGHT*WIDTH-1:0] spike_map,  // Flattened spike output
    
    //=========================================================================
    // Statistics
    //=========================================================================
    output reg  [$clog2(MAX_WINNERS):0] num_winners_found
);

    //=========================================================================
    // Local Parameters
    //=========================================================================
    localparam TOTAL_NEURONS = CHANNELS * HEIGHT * WIDTH;
    localparam ADDR_WIDTH = $clog2(TOTAL_NEURONS);
    
    //=========================================================================
    // State Machine
    //=========================================================================
    localparam IDLE             = 4'd0;
    localparam INIT_SCAN        = 4'd1;
    localparam SCAN_READ        = 4'd2;
    localparam SCAN_WAIT        = 4'd3;
    localparam SCAN_COMPARE     = 4'd4;
    localparam SCAN_NEXT        = 4'd5;
    localparam CHECK_WINNER     = 4'd6;
    localparam APPLY_INHIBITION = 4'd7;
    localparam OUTPUT_WINNER    = 4'd8;
    localparam NEXT_WINNER      = 4'd9;
    localparam FINISH           = 4'd10;
    
    reg [3:0] state;
    assign busy = (state != IDLE);
    
    //=========================================================================
    // Inhibition Mask Memory
    // 1 = inhibited, 0 = can be selected
    //=========================================================================
    reg [TOTAL_NEURONS-1:0] inhibition_mask;
    
    //=========================================================================
    // Scan Registers
    //=========================================================================
    reg [$clog2(CHANNELS)-1:0]  scan_ch;
    reg [$clog2(HEIGHT)-1:0]    scan_row;
    reg [$clog2(WIDTH)-1:0]     scan_col;
    reg                         scan_done;
    
    // Current maximum tracking
    reg [VMEM_WIDTH-1:0]        current_max_potential;
    reg [$clog2(CHANNELS)-1:0]  current_max_ch;
    reg [$clog2(HEIGHT)-1:0]    current_max_row;
    reg [$clog2(WIDTH)-1:0]     current_max_col;
    reg                         found_valid_winner;
    
    // Winner count
    reg [$clog2(MAX_WINNERS):0] winner_count;
    
    // Inhibition application
    reg signed [$clog2(HEIGHT)+1:0] inhib_row;
    reg signed [$clog2(WIDTH)+1:0]  inhib_col;
    
    //=========================================================================
    // Address Calculation
    //=========================================================================
    function [ADDR_WIDTH-1:0] flatten_addr;
        input [$clog2(CHANNELS)-1:0] ch;
        input [$clog2(HEIGHT)-1:0]   row;
        input [$clog2(WIDTH)-1:0]    col;
        begin
            flatten_addr = ch * (HEIGHT * WIDTH) + row * WIDTH + col;
        end
    endfunction
    
    //=========================================================================
    // Check if current scan position is inhibited
    //=========================================================================
    wire current_inhibited;
    wire [ADDR_WIDTH-1:0] current_addr = flatten_addr(scan_ch, scan_row, scan_col);
    assign current_inhibited = inhibition_mask[current_addr];
    
    //=========================================================================
    // Main State Machine
    //=========================================================================
    always @(posedge clk) begin
        if (!rst_n) begin
            state <= IDLE;
            done <= 1'b0;
            winner_valid <= 1'b0;
            vmem_rd_en <= 1'b0;
            inhibition_mask <= {TOTAL_NEURONS{1'b0}};
            spike_map <= {TOTAL_NEURONS{1'b0}};
            num_winners_found <= 0;
            winner_count <= 0;
        end else if (enable) begin
            case (state)
                //=============================================================
                // IDLE: Wait for start signal
                //=============================================================
                IDLE: begin
                    done <= 1'b0;
                    winner_valid <= 1'b0;
                    
                    if (start) begin
                        inhibition_mask <= {TOTAL_NEURONS{1'b0}};
                        spike_map <= {TOTAL_NEURONS{1'b0}};
                        winner_count <= 0;
                        num_winners_found <= 0;
                        state <= INIT_SCAN;
                    end
                end
                
                //=============================================================
                // INIT_SCAN: Initialize scan for next winner
                //=============================================================
                INIT_SCAN: begin
                    scan_ch <= 0;
                    scan_row <= 0;
                    scan_col <= 0;
                    scan_done <= 1'b0;
                    current_max_potential <= 0;
                    found_valid_winner <= 1'b0;
                    state <= SCAN_READ;
                end
                
                //=============================================================
                // SCAN_READ: Request membrane potential
                //=============================================================
                SCAN_READ: begin
                    if (!current_inhibited) begin
                        vmem_rd_en <= 1'b1;
                        vmem_ch_addr <= scan_ch;
                        vmem_row_addr <= scan_row;
                        vmem_col_addr <= scan_col;
                        state <= SCAN_WAIT;
                    end else begin
                        // Skip inhibited neuron
                        state <= SCAN_NEXT;
                    end
                end
                
                //=============================================================
                // SCAN_WAIT: Wait for memory response
                //=============================================================
                SCAN_WAIT: begin
                    vmem_rd_en <= 1'b0;
                    if (vmem_valid) begin
                        state <= SCAN_COMPARE;
                    end
                end
                
                //=============================================================
                // SCAN_COMPARE: Compare with current maximum
                //=============================================================
                SCAN_COMPARE: begin
                    // Check if this neuron is above threshold and is new max
                    if (vmem_data >= threshold && vmem_data > current_max_potential) begin
                        current_max_potential <= vmem_data;
                        current_max_ch <= scan_ch;
                        current_max_row <= scan_row;
                        current_max_col <= scan_col;
                        found_valid_winner <= 1'b1;
                    end
                    state <= SCAN_NEXT;
                end
                
                //=============================================================
                // SCAN_NEXT: Move to next neuron
                //=============================================================
                SCAN_NEXT: begin
                    if (scan_col < WIDTH - 1) begin
                        scan_col <= scan_col + 1;
                        state <= SCAN_READ;
                    end else if (scan_row < HEIGHT - 1) begin
                        scan_col <= 0;
                        scan_row <= scan_row + 1;
                        state <= SCAN_READ;
                    end else if (scan_ch < CHANNELS - 1) begin
                        scan_col <= 0;
                        scan_row <= 0;
                        scan_ch <= scan_ch + 1;
                        state <= SCAN_READ;
                    end else begin
                        // Scan complete
                        state <= CHECK_WINNER;
                    end
                end
                
                //=============================================================
                // CHECK_WINNER: Check if valid winner found
                //=============================================================
                CHECK_WINNER: begin
                    if (found_valid_winner) begin
                        // Found a winner
                        inhib_row <= $signed({1'b0, current_max_row}) - $signed({1'b0, radius[$clog2(MAX_RADIUS):0]});
                        inhib_col <= $signed({1'b0, current_max_col}) - $signed({1'b0, radius[$clog2(MAX_RADIUS):0]});
                        state <= APPLY_INHIBITION;
                    end else begin
                        // No more winners
                        state <= FINISH;
                    end
                end
                
                //=============================================================
                // APPLY_INHIBITION: Mark neighborhood as inhibited
                //=============================================================
                APPLY_INHIBITION: begin
                    // Apply inhibition to all channels at spatial neighborhood
                    // This is done over multiple cycles for area efficiency
                    
                    // For simplicity, do all at once (can be pipelined)
                    begin : inhibit_block
                        integer ch_i;
                        integer r, c;
                        reg signed [$clog2(HEIGHT)+1:0] row_i;
                        reg signed [$clog2(WIDTH)+1:0] col_i;
                        
                        for (ch_i = 0; ch_i < CHANNELS; ch_i = ch_i + 1) begin
                            for (r = 0; r <= 2*MAX_RADIUS; r = r + 1) begin
                                for (c = 0; c <= 2*MAX_RADIUS; c = c + 1) begin
                                    row_i = $signed({1'b0, current_max_row}) - $signed(radius) + r;
                                    col_i = $signed({1'b0, current_max_col}) - $signed(radius) + c;
                                    
                                    // Check bounds and within radius
                                    if (row_i >= 0 && row_i < HEIGHT &&
                                        col_i >= 0 && col_i < WIDTH &&
                                        r <= 2*radius && c <= 2*radius) begin
                                        inhibition_mask[ch_i * (HEIGHT * WIDTH) + row_i * WIDTH + col_i] <= 1'b1;
                                    end
                                end
                            end
                        end
                    end
                    
                    // Mark winner in spike map
                    spike_map[flatten_addr(current_max_ch, current_max_row, current_max_col)] <= 1'b1;
                    
                    state <= OUTPUT_WINNER;
                end
                
                //=============================================================
                // OUTPUT_WINNER: Output winner information
                //=============================================================
                OUTPUT_WINNER: begin
                    winner_valid <= 1'b1;
                    winner_ch <= current_max_ch;
                    winner_row <= current_max_row;
                    winner_col <= current_max_col;
                    winner_potential <= current_max_potential;
                    winner_index <= winner_count;
                    
                    if (winner_ready) begin
                        winner_valid <= 1'b0;
                        winner_count <= winner_count + 1;
                        num_winners_found <= winner_count + 1;
                        state <= NEXT_WINNER;
                    end
                end
                
                //=============================================================
                // NEXT_WINNER: Check if more winners needed
                //=============================================================
                NEXT_WINNER: begin
                    if (winner_count < k) begin
                        // Find next winner
                        state <= INIT_SCAN;
                    end else begin
                        // Found all k winners
                        state <= FINISH;
                    end
                end
                
                //=============================================================
                // FINISH: Signal completion
                //=============================================================
                FINISH: begin
                    done <= 1'b1;
                    state <= IDLE;
                end
                
                default: state <= IDLE;
            endcase
        end
    end

endmodule
