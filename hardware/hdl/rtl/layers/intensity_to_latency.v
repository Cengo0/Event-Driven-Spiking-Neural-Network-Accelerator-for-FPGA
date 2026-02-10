//-----------------------------------------------------------------------------
// Title         : Intensity-to-Latency Temporal Encoder V2 (Bin-Packing)
// Project       : PYNQ-Z2 SNN Accelerator
// File          : intensity_to_latency_v2.v
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : Converts intensity values to spike latencies using bin-packing
//                 
//                 This implements the SpykeTorch-style encoding:
//                 1. Sort all intensity values (descending)
//                 2. Top bin_size values → timestep 0
//                 3. Next bin_size values → timestep 1
//                 4. ... and so on
//                 5. Zero values → NO SPIKE (critical!)
//                 
//                 Key difference from V1:
//                 - Zero/low intensity positions do NOT spike at all
//                 - Spike assignment is relative (ranking-based), not absolute
//                 - Produces sparse temporal code (not all positions spike)
//
//                 Hardware Implementation Strategy:
//                 - Two-pass approach for sorting efficiency
//                 - Pass 1: Store all intensities, find max, count nonzero
//                 - Pass 2: Threshold-based binning (approximate sorting)
//                 
//                 Alternative: Use histogram-based binning for O(N) complexity
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps

module intensity_to_latency_v2 #(
    parameter HEIGHT        = 28,
    parameter WIDTH         = 28,
    parameter CHANNELS      = 6,          // 6 DoG filters
    parameter DATA_WIDTH    = 16,         // Input precision
    parameter TIME_STEPS    = 15,         // Number of time bins
    parameter TIME_WIDTH    = 4,          // log2(TIME_STEPS)
    parameter THRESHOLD     = 10,         // Minimum intensity for spike (CRITICAL)
    parameter NUM_BINS      = 16,         // Histogram bins for fast sorting
    parameter TOTAL_PIXELS  = HEIGHT * WIDTH * CHANNELS
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
    
    //=========================================================================
    // Intensity Input (from DoG filter bank)
    //=========================================================================
    input  wire                         s_intensity_valid,
    input  wire [DATA_WIDTH-1:0]        s_intensity_data,
    input  wire [$clog2(CHANNELS)-1:0]  s_intensity_ch,
    input  wire [$clog2(HEIGHT)-1:0]    s_intensity_row,
    input  wire [$clog2(WIDTH)-1:0]     s_intensity_col,
    input  wire                         s_frame_last,
    output wire                         s_intensity_ready,
    
    //=========================================================================
    // Spike Output (Temporal encoded spikes - ONLY for nonzero intensities)
    //=========================================================================
    output reg                          m_spike_valid,
    output reg  [TIME_WIDTH-1:0]        m_spike_time,      // Spike timing (0 = earliest)
    output reg  [$clog2(CHANNELS)-1:0]  m_spike_ch,
    output reg  [$clog2(HEIGHT)-1:0]    m_spike_row,
    output reg  [$clog2(WIDTH)-1:0]     m_spike_col,
    output reg                          m_frame_last,
    input  wire                         m_spike_ready,
    
    //=========================================================================
    // Spike Memory Interface (sparse format)
    // Only writes positions that actually spike
    //=========================================================================
    output reg                          mem_write_en,
    output reg  [$clog2(TOTAL_PIXELS)-1:0] mem_write_addr,
    output reg  [TIME_WIDTH-1:0]        mem_write_time,
    
    //=========================================================================
    // Statistics
    //=========================================================================
    output reg  [31:0]                  total_spikes,      // Should be < TOTAL_PIXELS
    output reg  [31:0]                  nonzero_count,     // Pixels above threshold
    output reg  [DATA_WIDTH-1:0]        max_intensity_found,
    output reg  [31:0]                  bin_size_used      // Pixels per timestep
);

    //=========================================================================
    // Internal Memory
    // Store intensity and position for sorting
    //=========================================================================
    localparam ADDR_WIDTH = $clog2(TOTAL_PIXELS);
    
    // Intensity buffer (dual-port for read during output)
    reg [DATA_WIDTH-1:0] intensity_mem [0:TOTAL_PIXELS-1];
    
    // Position buffer (row, col, ch packed)
    localparam POS_WIDTH = $clog2(HEIGHT) + $clog2(WIDTH) + $clog2(CHANNELS);
    reg [POS_WIDTH-1:0] position_mem [0:TOTAL_PIXELS-1];
    
    // Histogram for approximate sorting
    // Each bin counts pixels in intensity range
    reg [15:0] histogram [0:NUM_BINS-1];
    reg [DATA_WIDTH-1:0] bin_thresholds [0:NUM_BINS-1];
    
    //=========================================================================
    // State Machine
    //=========================================================================
    localparam IDLE           = 4'd0;
    localparam COLLECT        = 4'd1;   // Collect all intensities
    localparam ANALYZE        = 4'd2;   // Find max, count nonzero, build histogram
    localparam COMPUTE_BINS   = 4'd3;   // Compute bin thresholds for time assignment
    localparam OUTPUT_PASS    = 4'd4;   // Output spikes by bin (multiple passes)
    localparam OUTPUT_PIXEL   = 4'd5;   // Output single pixel
    localparam NEXT_BIN       = 4'd6;   // Move to next time bin
    localparam DONE_STATE     = 4'd7;
    
    reg [3:0] state;
    assign busy = (state != IDLE);
    assign s_intensity_ready = (state == COLLECT) && enable;
    
    //=========================================================================
    // Working Registers
    //=========================================================================
    reg [ADDR_WIDTH-1:0]    write_idx;
    reg [ADDR_WIDTH-1:0]    read_idx;
    reg [ADDR_WIDTH-1:0]    pixel_count;
    reg [DATA_WIDTH-1:0]    current_max;
    reg [31:0]              current_nonzero;
    reg [TIME_WIDTH-1:0]    current_time_bin;
    reg [DATA_WIDTH-1:0]    current_bin_min;
    reg [DATA_WIDTH-1:0]    current_bin_max;
    reg [31:0]              spikes_in_bin;
    reg [31:0]              target_bin_size;
    
    // Histogram index calculation
    wire [$clog2(NUM_BINS)-1:0] hist_idx;
    reg [DATA_WIDTH-1:0] intensity_for_hist;
    
    // Scale intensity to histogram bin (simple shift for power-of-2 bins)
    assign hist_idx = intensity_for_hist >> (DATA_WIDTH - $clog2(NUM_BINS));
    
    //=========================================================================
    // Main State Machine
    //=========================================================================
    integer i;
    reg [DATA_WIDTH-1:0] read_intensity;
    reg [POS_WIDTH-1:0] read_position;
    reg [$clog2(HEIGHT)-1:0] out_row;
    reg [$clog2(WIDTH)-1:0] out_col;
    reg [$clog2(CHANNELS)-1:0] out_ch;
    
    always @(posedge clk) begin
        if (!rst_n) begin
            state <= IDLE;
            done <= 1'b0;
            m_spike_valid <= 1'b0;
            mem_write_en <= 1'b0;
            write_idx <= 0;
            read_idx <= 0;
            total_spikes <= 0;
            nonzero_count <= 0;
            max_intensity_found <= 0;
            
            for (i = 0; i < NUM_BINS; i = i + 1) begin
                histogram[i] <= 0;
            end
        end else if (enable) begin
            case (state)
                //=============================================================
                // IDLE: Wait for start
                //=============================================================
                IDLE: begin
                    done <= 1'b0;
                    m_spike_valid <= 1'b0;
                    mem_write_en <= 1'b0;
                    
                    if (start) begin
                        write_idx <= 0;
                        pixel_count <= 0;
                        current_max <= 0;
                        current_nonzero <= 0;
                        total_spikes <= 0;
                        
                        for (i = 0; i < NUM_BINS; i = i + 1) begin
                            histogram[i] <= 0;
                        end
                        
                        state <= COLLECT;
                    end
                end
                
                //=============================================================
                // COLLECT: Receive all intensity values
                //=============================================================
                COLLECT: begin
                    if (s_intensity_valid) begin
                        // Store intensity
                        intensity_mem[write_idx] <= s_intensity_data;
                        
                        // Store position (packed)
                        position_mem[write_idx] <= {s_intensity_row, s_intensity_col, s_intensity_ch};
                        
                        // Track max and nonzero count
                        if (s_intensity_data > current_max) begin
                            current_max <= s_intensity_data;
                        end
                        
                        if (s_intensity_data >= THRESHOLD) begin
                            current_nonzero <= current_nonzero + 1;
                            
                            // Update histogram
                            intensity_for_hist <= s_intensity_data;
                            histogram[s_intensity_data >> (DATA_WIDTH - $clog2(NUM_BINS))] <= 
                                histogram[s_intensity_data >> (DATA_WIDTH - $clog2(NUM_BINS))] + 1;
                        end
                        
                        write_idx <= write_idx + 1;
                        pixel_count <= pixel_count + 1;
                        
                        if (s_frame_last || write_idx == TOTAL_PIXELS - 1) begin
                            state <= ANALYZE;
                        end
                    end
                end
                
                //=============================================================
                // ANALYZE: Compute statistics
                //=============================================================
                ANALYZE: begin
                    max_intensity_found <= current_max;
                    nonzero_count <= current_nonzero;
                    
                    // Calculate bin size (pixels per timestep)
                    // bin_size = nonzero_count / TIME_STEPS (rounded up)
                    if (current_nonzero > 0) begin
                        target_bin_size <= (current_nonzero + TIME_STEPS - 1) / TIME_STEPS;
                    end else begin
                        target_bin_size <= 0;
                    end
                    
                    state <= COMPUTE_BINS;
                end
                
                //=============================================================
                // COMPUTE_BINS: Calculate intensity thresholds for each time bin
                // Using cumulative histogram approach
                //=============================================================
                COMPUTE_BINS: begin
                    // Compute bin thresholds from histogram
                    // This is approximate but O(1) per bin
                    begin : compute_thresholds
                        integer b;
                        reg [31:0] cumsum;
                        reg [31:0] target;
                        
                        cumsum = 0;
                        
                        // Scan histogram from high to low intensity
                        for (b = NUM_BINS - 1; b >= 0; b = b - 1) begin
                            cumsum = cumsum + histogram[b];
                        end
                        
                        // Simple linear threshold assignment
                        // bin_thresholds[t] = max_intensity * (TIME_STEPS - t) / TIME_STEPS
                        for (b = 0; b < TIME_STEPS; b = b + 1) begin
                            if (b < NUM_BINS) begin
                                bin_thresholds[b] <= (current_max * (TIME_STEPS - b)) / TIME_STEPS;
                            end
                        end
                    end
                    
                    // Start output from highest intensity (time bin 0)
                    current_time_bin <= 0;
                    read_idx <= 0;
                    spikes_in_bin <= 0;
                    
                    // Set initial threshold range
                    current_bin_max <= current_max;
                    current_bin_min <= (current_max * (TIME_STEPS - 1)) / TIME_STEPS;
                    
                    state <= OUTPUT_PASS;
                end
                
                //=============================================================
                // OUTPUT_PASS: Scan all pixels, output those in current bin
                //=============================================================
                OUTPUT_PASS: begin
                    if (read_idx < pixel_count) begin
                        read_intensity <= intensity_mem[read_idx];
                        read_position <= position_mem[read_idx];
                        
                        state <= OUTPUT_PIXEL;
                    end else begin
                        state <= NEXT_BIN;
                    end
                end
                
                //=============================================================
                // OUTPUT_PIXEL: Check if pixel belongs to current time bin
                //=============================================================
                OUTPUT_PIXEL: begin
                    // Unpack position
                    out_ch <= read_position[$clog2(CHANNELS)-1:0];
                    out_col <= read_position[$clog2(CHANNELS) +: $clog2(WIDTH)];
                    out_row <= read_position[$clog2(CHANNELS)+$clog2(WIDTH) +: $clog2(HEIGHT)];
                    
                    // Check if intensity is in current bin range AND above threshold
                    if (read_intensity >= THRESHOLD && 
                        read_intensity <= current_bin_max &&
                        read_intensity > current_bin_min) begin
                        
                        // Output spike
                        m_spike_valid <= 1'b1;
                        m_spike_time <= current_time_bin;
                        m_spike_row <= read_position[$clog2(CHANNELS)+$clog2(WIDTH) +: $clog2(HEIGHT)];
                        m_spike_col <= read_position[$clog2(CHANNELS) +: $clog2(WIDTH)];
                        m_spike_ch <= read_position[$clog2(CHANNELS)-1:0];
                        m_frame_last <= (read_idx == pixel_count - 1) && 
                                       (current_time_bin == TIME_STEPS - 1);
                        
                        // Memory write
                        mem_write_en <= 1'b1;
                        mem_write_addr <= read_idx;
                        mem_write_time <= current_time_bin;
                        
                        if (m_spike_ready) begin
                            m_spike_valid <= 1'b0;
                            mem_write_en <= 1'b0;
                            total_spikes <= total_spikes + 1;
                            spikes_in_bin <= spikes_in_bin + 1;
                            read_idx <= read_idx + 1;
                            state <= OUTPUT_PASS;
                        end
                    end else begin
                        // Skip this pixel for current bin
                        read_idx <= read_idx + 1;
                        state <= OUTPUT_PASS;
                    end
                end
                
                //=============================================================
                // NEXT_BIN: Move to next time bin
                //=============================================================
                NEXT_BIN: begin
                    m_spike_valid <= 1'b0;
                    mem_write_en <= 1'b0;
                    
                    bin_size_used <= spikes_in_bin;
                    
                    if (current_time_bin < TIME_STEPS - 1) begin
                        current_time_bin <= current_time_bin + 1;
                        read_idx <= 0;
                        spikes_in_bin <= 0;
                        
                        // Update bin range
                        current_bin_max <= current_bin_min;
                        current_bin_min <= (current_max * (TIME_STEPS - current_time_bin - 2)) / TIME_STEPS;
                        
                        // Handle last bin specially (include threshold)
                        if (current_time_bin == TIME_STEPS - 2) begin
                            current_bin_min <= THRESHOLD;
                        end
                        
                        state <= OUTPUT_PASS;
                    end else begin
                        state <= DONE_STATE;
                    end
                end
                
                //=============================================================
                // DONE_STATE: Processing complete
                //=============================================================
                DONE_STATE: begin
                    done <= 1'b1;
                    m_spike_valid <= 1'b0;
                    mem_write_en <= 1'b0;
                    state <= IDLE;
                end
                
                default: state <= IDLE;
            endcase
        end
    end

endmodule


//-----------------------------------------------------------------------------
// Alternative: Single-Pass Intensity-to-Latency with Quantile Thresholds
// This version uses pre-computed thresholds (set by software)
// More efficient but requires calibration
//-----------------------------------------------------------------------------
module intensity_to_latency_threshold #(
    parameter HEIGHT        = 28,
    parameter WIDTH         = 28,
    parameter CHANNELS      = 6,
    parameter DATA_WIDTH    = 16,
    parameter TIME_STEPS    = 15,
    parameter TIME_WIDTH    = 4,
    parameter THRESHOLD     = 10
)(
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         enable,
    
    // Control
    input  wire                         start,
    output reg                          done,
    output wire                         busy,
    
    // Pre-computed thresholds from software (one per time bin)
    // threshold[0] = highest (for t=0), threshold[T-1] = lowest (for t=T-1)
    input  wire [DATA_WIDTH*TIME_STEPS-1:0] cfg_thresholds,
    
    // Streaming input
    input  wire                         s_valid,
    input  wire [DATA_WIDTH-1:0]        s_data,
    input  wire [$clog2(HEIGHT)-1:0]    s_row,
    input  wire [$clog2(WIDTH)-1:0]     s_col,
    input  wire [$clog2(CHANNELS)-1:0]  s_ch,
    input  wire                         s_last,
    output wire                         s_ready,
    
    // Streaming output (only for pixels that spike)
    output reg                          m_valid,
    output reg  [TIME_WIDTH-1:0]        m_time,
    output reg  [$clog2(HEIGHT)-1:0]    m_row,
    output reg  [$clog2(WIDTH)-1:0]     m_col,
    output reg  [$clog2(CHANNELS)-1:0]  m_ch,
    output reg                          m_last,
    input  wire                         m_ready,
    
    // Statistics
    output reg  [31:0]                  spike_count
);

    // Unpack thresholds
    wire [DATA_WIDTH-1:0] thresholds [0:TIME_STEPS-1];
    genvar g;
    generate
        for (g = 0; g < TIME_STEPS; g = g + 1) begin : unpack_thresh
            assign thresholds[g] = cfg_thresholds[g*DATA_WIDTH +: DATA_WIDTH];
        end
    endgenerate
    
    // State
    localparam IDLE = 2'd0;
    localparam PROCESS = 2'd1;
    localparam OUTPUT = 2'd2;
    localparam DONE_ST = 2'd3;
    
    reg [1:0] state;
    assign busy = (state != IDLE);
    assign s_ready = (state == PROCESS) && enable;
    
    // Pipeline registers
    reg [DATA_WIDTH-1:0] data_reg;
    reg [$clog2(HEIGHT)-1:0] row_reg;
    reg [$clog2(WIDTH)-1:0] col_reg;
    reg [$clog2(CHANNELS)-1:0] ch_reg;
    reg last_reg;
    reg [TIME_WIDTH-1:0] computed_time;
    reg should_spike;
    
    // Time bin computation (combinational)
    // Find first threshold that data exceeds
    integer t;
    reg [TIME_WIDTH-1:0] found_time;
    reg found;
    
    always @(*) begin
        found = 1'b0;
        found_time = TIME_STEPS;  // No spike default
        
        // Higher intensity -> lower time (earlier spike)
        // Check from t=0 (highest threshold) to t=T-1 (lowest)
        for (t = 0; t < TIME_STEPS; t = t + 1) begin
            if (!found && data_reg >= thresholds[t]) begin
                found_time = t;
                found = 1'b1;
            end
        end
    end
    
    always @(posedge clk) begin
        if (!rst_n) begin
            state <= IDLE;
            done <= 1'b0;
            m_valid <= 1'b0;
            spike_count <= 0;
        end else if (enable) begin
            case (state)
                IDLE: begin
                    done <= 1'b0;
                    m_valid <= 1'b0;
                    if (start) begin
                        spike_count <= 0;
                        state <= PROCESS;
                    end
                end
                
                PROCESS: begin
                    if (s_valid) begin
                        data_reg <= s_data;
                        row_reg <= s_row;
                        col_reg <= s_col;
                        ch_reg <= s_ch;
                        last_reg <= s_last;
                        
                        // Only spike if above minimum threshold
                        should_spike <= (s_data >= THRESHOLD);
                        computed_time <= found_time;
                        
                        state <= OUTPUT;
                    end
                end
                
                OUTPUT: begin
                    if (should_spike && computed_time < TIME_STEPS) begin
                        m_valid <= 1'b1;
                        m_time <= computed_time;
                        m_row <= row_reg;
                        m_col <= col_reg;
                        m_ch <= ch_reg;
                        m_last <= last_reg;
                        
                        if (m_ready) begin
                            m_valid <= 1'b0;
                            spike_count <= spike_count + 1;
                            
                            if (last_reg) begin
                                state <= DONE_ST;
                            end else begin
                                state <= PROCESS;
                            end
                        end
                    end else begin
                        // No spike for this pixel - skip to next
                        if (last_reg) begin
                            state <= DONE_ST;
                        end else begin
                            state <= PROCESS;
                        end
                    end
                end
                
                DONE_ST: begin
                    done <= 1'b1;
                    m_valid <= 1'b0;
                    state <= IDLE;
                end
            endcase
        end
    end

endmodule
