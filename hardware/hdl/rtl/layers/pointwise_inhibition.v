//-----------------------------------------------------------------------------
// Title         : Pointwise Inhibition with First-Spike Time Recording
// Project       : PYNQ-Z2 SNN Accelerator
// File          : pointwise_inhibition_v2.v
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : Enhanced pointwise inhibition that records first spike time
//                 
//                 Key enhancements for STDP:
//                 1. Records first spike TIME for each location
//                 2. Provides first_spike_time memory interface for STDP
//                 3. Distinguishes "no spike" vs "spike at t=0"
//                 
//                 This is CRITICAL for proper STDP learning:
//                 - STDP needs pre/post spike timing comparison
//                 - Earlier spike (lower time) = higher intensity
//                 - LTP when pre <= post, LTD when pre > post
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps

module pointwise_inhibition_v2 #(
    parameter HEIGHT        = 28,
    parameter WIDTH         = 28,
    parameter CHANNELS      = 6,
    parameter TIME_STEPS    = 15,
    parameter TIME_WIDTH    = 4,          // bits for time encoding
    parameter NO_SPIKE_VAL  = 4'hF        // Value indicating no spike (max)
)(
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         enable,
    
    //=========================================================================
    // Control Interface
    //=========================================================================
    input  wire                         start,
    output reg                          done,
    output wire                         busy,
    input  wire                         clear_memory,     // Clear spike time memory
    
    //=========================================================================
    // Spike Input
    //=========================================================================
    input  wire                         s_spike_valid,
    input  wire [CHANNELS-1:0]          s_spike_data,
    input  wire [$clog2(HEIGHT)-1:0]    s_spike_row,
    input  wire [$clog2(WIDTH)-1:0]     s_spike_col,
    input  wire [TIME_WIDTH-1:0]        s_spike_time,
    input  wire                         s_frame_last,
    output wire                         s_spike_ready,
    
    //=========================================================================
    // Inhibited Spike Output
    //=========================================================================
    output reg                          m_spike_valid,
    output reg  [CHANNELS-1:0]          m_spike_data,
    output reg  [$clog2(HEIGHT)-1:0]    m_spike_row,
    output reg  [$clog2(WIDTH)-1:0]     m_spike_col,
    output reg  [TIME_WIDTH-1:0]        m_spike_time,
    output reg                          m_frame_last,
    input  wire                         m_spike_ready,
    
    //=========================================================================
    // First Spike Time Memory Interface (for STDP)
    // Allows reading first spike time for any location
    //=========================================================================
    input  wire                         fst_read_en,
    input  wire [$clog2(HEIGHT)-1:0]    fst_read_row,
    input  wire [$clog2(WIDTH)-1:0]     fst_read_col,
    input  wire [$clog2(CHANNELS)-1:0]  fst_read_ch,
    output reg  [TIME_WIDTH-1:0]        fst_read_time,
    output reg                          fst_read_valid,
    output reg                          fst_no_spike,     // True if location never spiked
    
    // Bulk read interface (for convolution windows)
    input  wire                         fst_bulk_read_en,
    input  wire [$clog2(HEIGHT)-1:0]    fst_bulk_row_start,
    input  wire [$clog2(WIDTH)-1:0]     fst_bulk_col_start,
    input  wire [3:0]                   fst_bulk_kernel_size,  // 3, 5, 7, etc.
    output reg  [TIME_WIDTH*49-1:0]     fst_bulk_data,    // Max 7x7 kernel
    output reg                          fst_bulk_valid,
    
    //=========================================================================
    // Statistics
    //=========================================================================
    output reg  [31:0]                  total_input_spikes,
    output reg  [31:0]                  total_first_spikes,
    output reg  [31:0]                  suppressed_spikes
);

    //=========================================================================
    // Memory for First Spike Times
    // Stores TIME_WIDTH bits per location
    // Value = NO_SPIKE_VAL means no spike occurred
    //=========================================================================
    localparam MEM_SIZE = HEIGHT * WIDTH * CHANNELS;
    localparam ADDR_WIDTH = $clog2(MEM_SIZE);
    
    // First spike time memory (initialized to NO_SPIKE_VAL)
    reg [TIME_WIDTH-1:0] first_spike_time [0:MEM_SIZE-1];
    
    // Has-spiked flags (1-bit per location for fast lookup)
    reg [MEM_SIZE-1:0] has_spiked;
    
    //=========================================================================
    // State Machine
    //=========================================================================
    localparam IDLE         = 3'd0;
    localparam PROCESS      = 3'd1;
    localparam COMPUTE      = 3'd2;
    localparam OUTPUT       = 3'd3;
    localparam DONE_STATE   = 3'd4;
    localparam CLEAR        = 3'd5;
    
    reg [2:0] state;
    assign busy = (state != IDLE);
    assign s_spike_ready = (state == PROCESS);
    
    //=========================================================================
    // Working Registers
    //=========================================================================
    reg [CHANNELS-1:0]              input_spikes;
    reg [CHANNELS-1:0]              output_spikes;
    reg [$clog2(HEIGHT)-1:0]        row_reg;
    reg [$clog2(WIDTH)-1:0]         col_reg;
    reg [TIME_WIDTH-1:0]            time_reg;
    reg                             last_reg;
    reg [ADDR_WIDTH-1:0]            clear_addr;
    
    // Address calculation
    function [ADDR_WIDTH-1:0] calc_addr;
        input [$clog2(CHANNELS)-1:0] ch;
        input [$clog2(HEIGHT)-1:0]   row;
        input [$clog2(WIDTH)-1:0]    col;
        begin
            calc_addr = ch * (HEIGHT * WIDTH) + row * WIDTH + col;
        end
    endfunction
    
    // Current inhibition mask
    wire [CHANNELS-1:0] inhibition_mask;
    genvar ch;
    generate
        for (ch = 0; ch < CHANNELS; ch = ch + 1) begin : gen_inhib
            wire [ADDR_WIDTH-1:0] addr = calc_addr(ch, row_reg, col_reg);
            assign inhibition_mask[ch] = has_spiked[addr];
        end
    endgenerate
    
    //=========================================================================
    // Main State Machine
    //=========================================================================
    integer i;
    
    always @(posedge clk) begin
        if (!rst_n) begin
            state <= IDLE;
            done <= 1'b0;
            m_spike_valid <= 1'b0;
            has_spiked <= {MEM_SIZE{1'b0}};
            total_input_spikes <= 0;
            total_first_spikes <= 0;
            suppressed_spikes <= 0;
            clear_addr <= 0;
            
            // Initialize all to NO_SPIKE_VAL
            for (i = 0; i < MEM_SIZE; i = i + 1) begin
                first_spike_time[i] <= NO_SPIKE_VAL;
            end
        end else if (enable) begin
            case (state)
                IDLE: begin
                    done <= 1'b0;
                    m_spike_valid <= 1'b0;
                    
                    if (clear_memory) begin
                        clear_addr <= 0;
                        has_spiked <= {MEM_SIZE{1'b0}};
                        total_input_spikes <= 0;
                        total_first_spikes <= 0;
                        suppressed_spikes <= 0;
                        state <= CLEAR;
                    end else if (start) begin
                        state <= PROCESS;
                    end
                end
                
                CLEAR: begin
                    // Clear first_spike_time memory
                    first_spike_time[clear_addr] <= NO_SPIKE_VAL;
                    
                    if (clear_addr < MEM_SIZE - 1) begin
                        clear_addr <= clear_addr + 1;
                    end else begin
                        state <= IDLE;
                    end
                end
                
                PROCESS: begin
                    m_spike_valid <= 1'b0;
                    
                    if (s_spike_valid) begin
                        input_spikes <= s_spike_data;
                        row_reg <= s_spike_row;
                        col_reg <= s_spike_col;
                        time_reg <= s_spike_time;
                        last_reg <= s_frame_last;
                        
                        total_input_spikes <= total_input_spikes + count_ones(s_spike_data);
                        state <= COMPUTE;
                    end
                end
                
                COMPUTE: begin
                    // Apply inhibition
                    output_spikes <= input_spikes & (~inhibition_mask);
                    
                    // Count first spikes and suppressed
                    total_first_spikes <= total_first_spikes + 
                                         count_ones(input_spikes & (~inhibition_mask));
                    suppressed_spikes <= suppressed_spikes + 
                                        count_ones(input_spikes & inhibition_mask);
                    
                    state <= OUTPUT;
                end
                
                OUTPUT: begin
                    m_spike_valid <= 1'b1;
                    m_spike_data <= output_spikes;
                    m_spike_row <= row_reg;
                    m_spike_col <= col_reg;
                    m_spike_time <= time_reg;
                    m_frame_last <= last_reg;
                    
                    if (m_spike_ready) begin
                        m_spike_valid <= 1'b0;
                        
                        // Update memories for first spikes
                        for (i = 0; i < CHANNELS; i = i + 1) begin
                            if (output_spikes[i]) begin
                                has_spiked[calc_addr(i, row_reg, col_reg)] <= 1'b1;
                                first_spike_time[calc_addr(i, row_reg, col_reg)] <= time_reg;
                            end
                        end
                        
                        if (last_reg) begin
                            state <= DONE_STATE;
                        end else begin
                            state <= PROCESS;
                        end
                    end
                end
                
                DONE_STATE: begin
                    done <= 1'b1;
                    m_spike_valid <= 1'b0;
                    state <= IDLE;
                end
                
                default: state <= IDLE;
            endcase
        end
    end
    
    //=========================================================================
    // First Spike Time Read Interface
    //=========================================================================
    always @(posedge clk) begin
        if (!rst_n) begin
            fst_read_valid <= 1'b0;
            fst_read_time <= NO_SPIKE_VAL;
            fst_no_spike <= 1'b1;
        end else if (fst_read_en) begin
            fst_read_time <= first_spike_time[calc_addr(fst_read_ch, fst_read_row, fst_read_col)];
            fst_no_spike <= ~has_spiked[calc_addr(fst_read_ch, fst_read_row, fst_read_col)];
            fst_read_valid <= 1'b1;
        end else begin
            fst_read_valid <= 1'b0;
        end
    end
    
    //=========================================================================
    // Bulk Read for Convolution Kernel Windows
    // Reads a kernel_size x kernel_size window of first spike times
    //=========================================================================
    reg [2:0] bulk_read_state;
    reg [3:0] bulk_kr, bulk_kc;
    reg [3:0] bulk_size;
    reg [$clog2(HEIGHT)-1:0] bulk_base_row;
    reg [$clog2(WIDTH)-1:0] bulk_base_col;
    
    localparam BULK_IDLE = 3'd0;
    localparam BULK_READ = 3'd1;
    localparam BULK_DONE = 3'd2;
    
    always @(posedge clk) begin
        if (!rst_n) begin
            bulk_read_state <= BULK_IDLE;
            fst_bulk_valid <= 1'b0;
            fst_bulk_data <= 0;
        end else begin
            case (bulk_read_state)
                BULK_IDLE: begin
                    fst_bulk_valid <= 1'b0;
                    if (fst_bulk_read_en) begin
                        bulk_base_row <= fst_bulk_row_start;
                        bulk_base_col <= fst_bulk_col_start;
                        bulk_size <= fst_bulk_kernel_size;
                        bulk_kr <= 0;
                        bulk_kc <= 0;
                        fst_bulk_data <= 0;
                        bulk_read_state <= BULK_READ;
                    end
                end
                
                BULK_READ: begin
                    // Read one position per cycle (could be parallelized)
                    begin : bulk_read_block
                        reg [$clog2(HEIGHT)-1:0] rd_row;
                        reg [$clog2(WIDTH)-1:0] rd_col;
                        reg [ADDR_WIDTH-1:0] rd_addr;
                        integer idx;
                        
                        rd_row = bulk_base_row + bulk_kr;
                        rd_col = bulk_base_col + bulk_kc;
                        
                        // Check bounds
                        if (rd_row < HEIGHT && rd_col < WIDTH) begin
                            // Read for channel 0 (extend for multi-channel if needed)
                            rd_addr = calc_addr(0, rd_row, rd_col);
                            idx = bulk_kr * 7 + bulk_kc;  // Max 7x7
                            fst_bulk_data[idx*TIME_WIDTH +: TIME_WIDTH] <= 
                                first_spike_time[rd_addr];
                        end else begin
                            // Out of bounds - no spike
                            fst_bulk_data[(bulk_kr * 7 + bulk_kc)*TIME_WIDTH +: TIME_WIDTH] <= 
                                NO_SPIKE_VAL;
                        end
                    end
                    
                    // Advance position
                    if (bulk_kc < bulk_size - 1) begin
                        bulk_kc <= bulk_kc + 1;
                    end else if (bulk_kr < bulk_size - 1) begin
                        bulk_kc <= 0;
                        bulk_kr <= bulk_kr + 1;
                    end else begin
                        bulk_read_state <= BULK_DONE;
                    end
                end
                
                BULK_DONE: begin
                    fst_bulk_valid <= 1'b1;
                    bulk_read_state <= BULK_IDLE;
                end
            endcase
        end
    end
    
    //=========================================================================
    // Helper Function
    //=========================================================================
    function [5:0] count_ones;
        input [CHANNELS-1:0] vec;
        integer j;
        begin
            count_ones = 0;
            for (j = 0; j < CHANNELS; j = j + 1) begin
                count_ones = count_ones + vec[j];
            end
        end
    endfunction

endmodule
