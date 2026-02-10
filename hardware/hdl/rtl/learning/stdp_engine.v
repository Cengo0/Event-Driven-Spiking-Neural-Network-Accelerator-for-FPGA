//-----------------------------------------------------------------------------
// Title         : STDP Weight Update Engine
// Project       : PYNQ-Z2 SNN Accelerator
// File          : stdp_engine.v
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : Hardware STDP (Spike-Timing Dependent Plasticity) engine
//                 
//                 Implements the temporal learning rule:
//                 - LTP (potentiation): pre_time <= post_time (pre fires first/same)
//                 - LTD (depression):   pre_time > post_time (pre fires after)
//                 - No update: either pre or post didn't spike
//                 
//                 Weight update equations:
//                 - LTP: w += a_plus * (w_max - w)^μ
//                 - LTD: w -= a_minus * (w - w_min)^μ
//                 
//                 For Mozafari R-STDP:
//                 - Reward-modulated: updates scaled by reward signal
//                 - Anti-STDP on incorrect: LTP becomes LTD and vice versa
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps

module stdp_engine #(
    parameter KERNEL_SIZE   = 5,
    parameter IN_CHANNELS   = 6,
    parameter OUT_FEATURES  = 20,
    parameter WEIGHT_WIDTH  = 8,          // Q0.8 fixed point (0-1 range)
    parameter TIME_WIDTH    = 4,
    parameter NO_SPIKE_VAL  = 4'hF,       // Indicates no spike
    parameter NUM_SYNAPSES  = KERNEL_SIZE * KERNEL_SIZE * IN_CHANNELS
)(
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         enable,
    
    //=========================================================================
    // Control
    //=========================================================================
    input  wire                         start,
    output reg                          done,
    output wire                         busy,
    
    //=========================================================================
    // Learning Parameters (from software, Q8.8 format)
    //=========================================================================
    input  wire [15:0]                  cfg_a_plus,       // LTP rate
    input  wire [15:0]                  cfg_a_minus,      // LTD rate
    input  wire [WEIGHT_WIDTH-1:0]      cfg_w_min,        // Min weight (usually 0)
    input  wire [WEIGHT_WIDTH-1:0]      cfg_w_max,        // Max weight (usually 255)
    input  wire [7:0]                   cfg_mu,           // Exponent (Q4.4, usually 0.75)
    
    //=========================================================================
    // Reward Signal (for R-STDP)
    //=========================================================================
    input  wire                         reward_valid,
    input  wire                         reward_positive,  // 1=correct, 0=incorrect
    input  wire [7:0]                   reward_magnitude, // Reward strength
    input  wire                         use_anti_stdp,    // Apply anti-STDP on wrong
    
    //=========================================================================
    // Winner Information
    //=========================================================================
    input  wire                         winner_valid,
    input  wire [$clog2(OUT_FEATURES)-1:0] winner_id,
    input  wire [TIME_WIDTH-1:0]        winner_spike_time,
    input  wire [$clog2(28)-1:0]        winner_row,       // Position in output
    input  wire [$clog2(28)-1:0]        winner_col,
    
    //=========================================================================
    // Pre-synaptic Spike Times (from pointwise_inhibition_v2)
    // For the receptive field of the winner neuron
    //=========================================================================
    input  wire                         pre_times_valid,
    input  wire [TIME_WIDTH*NUM_SYNAPSES-1:0] pre_spike_times, // Packed array
    
    //=========================================================================
    // Weight Memory Interface
    //=========================================================================
    // Read weights for winner
    output reg                          weight_rd_en,
    output reg  [$clog2(OUT_FEATURES)-1:0] weight_rd_feature,
    output reg  [$clog2(NUM_SYNAPSES)-1:0] weight_rd_synapse,
    input  wire [WEIGHT_WIDTH-1:0]      weight_rd_data,
    input  wire                         weight_rd_valid,
    
    // Write updated weights
    output reg                          weight_wr_en,
    output reg  [$clog2(OUT_FEATURES)-1:0] weight_wr_feature,
    output reg  [$clog2(NUM_SYNAPSES)-1:0] weight_wr_synapse,
    output reg  [WEIGHT_WIDTH-1:0]      weight_wr_data,
    
    //=========================================================================
    // Statistics
    //=========================================================================
    output reg  [31:0]                  ltp_count,
    output reg  [31:0]                  ltd_count,
    output reg  [31:0]                  no_update_count,
    output reg  [31:0]                  anti_stdp_count
);

    //=========================================================================
    // State Machine
    //=========================================================================
    localparam IDLE         = 4'd0;
    localparam WAIT_PRE     = 4'd1;
    localparam READ_WEIGHT  = 4'd2;
    localparam WAIT_READ    = 4'd3;
    localparam COMPUTE      = 4'd4;
    localparam WRITE_WEIGHT = 4'd5;
    localparam NEXT_SYNAPSE = 4'd6;
    localparam DONE_STATE   = 4'd7;
    
    reg [3:0] state;
    assign busy = (state != IDLE);
    
    //=========================================================================
    // Working Registers
    //=========================================================================
    reg [$clog2(OUT_FEATURES)-1:0] current_feature;
    reg [$clog2(NUM_SYNAPSES)-1:0] current_synapse;
    reg [TIME_WIDTH-1:0]           post_time;           // Winner spike time
    reg [TIME_WIDTH-1:0]           pre_time;            // Current synapse spike time
    reg [WEIGHT_WIDTH-1:0]         current_weight;
    reg                            is_reward;
    reg                            do_anti_stdp;
    
    // Unpack pre-synaptic times
    wire [TIME_WIDTH-1:0] pre_times [0:NUM_SYNAPSES-1];
    genvar g;
    generate
        for (g = 0; g < NUM_SYNAPSES; g = g + 1) begin : unpack_times
            assign pre_times[g] = pre_spike_times[g*TIME_WIDTH +: TIME_WIDTH];
        end
    endgenerate
    
    //=========================================================================
    // Weight Update Computation
    // Supports μ parameter via shift-based power approximation:
    //   cfg_mu = Q4.4 format: 0x10 = 1.0 (linear), 0x0C = 0.75, 0x08 = 0.5
    //   For μ < 1.0: attenuate the weight-dependent factor
    //   μ=1.0: delta = a * distance / 256  (linear, original)
    //   μ=0.75: delta = a * distance * 3/4 / 256  (approximate)
    //   μ=0.5: delta = a * sqrt(distance) / 256  (approximate via shift)
    //
    // LTP: Δw = a_plus * (w_max - w)^μ >> 8
    // LTD: Δw = a_minus * (w - w_min)^μ >> 8
    //=========================================================================
    reg signed [WEIGHT_WIDTH+16:0] delta_w;
    reg [WEIGHT_WIDTH-1:0] new_weight;
    reg update_type;  // 0=LTD, 1=LTP

    // Power approximation: apply cfg_mu to distance value
    // cfg_mu Q4.4: 0x10=1.0, 0x0C=0.75, 0x08=0.5, 0x04=0.25
    function [WEIGHT_WIDTH-1:0] apply_mu;
        input [WEIGHT_WIDTH-1:0] distance;
        input [7:0] mu;  // Q4.4
        reg [WEIGHT_WIDTH+3:0] scaled;
        begin
            // mu_frac = mu[3:0] (fractional 4 bits), mu_int = mu[7:4]
            // For mu_int=1: full distance; mu_int=0: fractional only
            // Approximation: result = distance * mu / 16
            scaled = distance * mu[7:0];
            apply_mu = scaled[WEIGHT_WIDTH+3:4]; // divide by 16 (Q4.4 to integer)
        end
    endfunction

    // Compute weight update (combinational)
    always @(*) begin
        if (is_reward || !use_anti_stdp) begin
            // Normal STDP or positive reward
            if (pre_time <= post_time && pre_time != NO_SPIKE_VAL) begin
                // LTP: pre fired before or same time as post
                update_type = 1'b1;
                delta_w = (cfg_a_plus * apply_mu(cfg_w_max - current_weight, cfg_mu)) >>> 8;
            end else if (pre_time > post_time && pre_time != NO_SPIKE_VAL) begin
                // LTD: pre fired after post
                update_type = 1'b0;
                delta_w = (cfg_a_minus * apply_mu(current_weight - cfg_w_min, cfg_mu)) >>> 8;
            end else begin
                // No spike from pre - no update
                update_type = 1'b0;
                delta_w = 0;
            end
        end else begin
            // Anti-STDP (incorrect response)
            if (pre_time <= post_time && pre_time != NO_SPIKE_VAL) begin
                // Would be LTP -> becomes LTD
                update_type = 1'b0;
                delta_w = (cfg_a_minus * apply_mu(current_weight - cfg_w_min, cfg_mu)) >>> 8;
            end else if (pre_time > post_time && pre_time != NO_SPIKE_VAL) begin
                // Would be LTD -> becomes LTP
                update_type = 1'b1;
                delta_w = (cfg_a_plus * apply_mu(cfg_w_max - current_weight, cfg_mu)) >>> 8;
            end else begin
                update_type = 1'b0;
                delta_w = 0;
            end
        end
    end
    
    // Apply update with saturation
    always @(*) begin
        if (update_type) begin
            // LTP - increase weight
            if (current_weight + delta_w > cfg_w_max) begin
                new_weight = cfg_w_max;
            end else begin
                new_weight = current_weight + delta_w[WEIGHT_WIDTH-1:0];
            end
        end else begin
            // LTD - decrease weight
            if (delta_w > current_weight - cfg_w_min) begin
                new_weight = cfg_w_min;
            end else begin
                new_weight = current_weight - delta_w[WEIGHT_WIDTH-1:0];
            end
        end
    end
    
    //=========================================================================
    // Main State Machine
    //=========================================================================
    always @(posedge clk) begin
        if (!rst_n) begin
            state <= IDLE;
            done <= 1'b0;
            weight_rd_en <= 1'b0;
            weight_wr_en <= 1'b0;
            ltp_count <= 0;
            ltd_count <= 0;
            no_update_count <= 0;
            anti_stdp_count <= 0;
        end else if (enable) begin
            case (state)
                //=============================================================
                // IDLE: Wait for start
                //=============================================================
                IDLE: begin
                    done <= 1'b0;
                    weight_rd_en <= 1'b0;
                    weight_wr_en <= 1'b0;
                    
                    if (start && winner_valid) begin
                        current_feature <= winner_id;
                        post_time <= winner_spike_time;
                        current_synapse <= 0;
                        
                        // Latch reward info
                        is_reward <= reward_valid && reward_positive;
                        do_anti_stdp <= reward_valid && !reward_positive && use_anti_stdp;
                        
                        state <= WAIT_PRE;
                    end
                end
                
                //=============================================================
                // WAIT_PRE: Wait for pre-synaptic spike times
                //=============================================================
                WAIT_PRE: begin
                    if (pre_times_valid) begin
                        state <= READ_WEIGHT;
                    end
                end
                
                //=============================================================
                // READ_WEIGHT: Request weight read
                //=============================================================
                READ_WEIGHT: begin
                    weight_rd_en <= 1'b1;
                    weight_rd_feature <= current_feature;
                    weight_rd_synapse <= current_synapse;
                    
                    // Get pre spike time for current synapse
                    pre_time <= pre_times[current_synapse];
                    
                    state <= WAIT_READ;
                end
                
                //=============================================================
                // WAIT_READ: Wait for weight data
                //=============================================================
                WAIT_READ: begin
                    weight_rd_en <= 1'b0;
                    
                    if (weight_rd_valid) begin
                        current_weight <= weight_rd_data;
                        state <= COMPUTE;
                    end
                end
                
                //=============================================================
                // COMPUTE: Compute weight update
                //=============================================================
                COMPUTE: begin
                    // Update statistics
                    if (pre_time == NO_SPIKE_VAL || post_time == NO_SPIKE_VAL) begin
                        no_update_count <= no_update_count + 1;
                    end else if (do_anti_stdp) begin
                        anti_stdp_count <= anti_stdp_count + 1;
                        if (update_type) ltp_count <= ltp_count + 1;
                        else ltd_count <= ltd_count + 1;
                    end else begin
                        if (update_type) ltp_count <= ltp_count + 1;
                        else ltd_count <= ltd_count + 1;
                    end
                    
                    state <= WRITE_WEIGHT;
                end
                
                //=============================================================
                // WRITE_WEIGHT: Write updated weight
                //=============================================================
                WRITE_WEIGHT: begin
                    // Only write if there was an actual update
                    if (delta_w != 0) begin
                        weight_wr_en <= 1'b1;
                        weight_wr_feature <= current_feature;
                        weight_wr_synapse <= current_synapse;
                        weight_wr_data <= new_weight;
                    end
                    
                    state <= NEXT_SYNAPSE;
                end
                
                //=============================================================
                // NEXT_SYNAPSE: Move to next synapse
                //=============================================================
                NEXT_SYNAPSE: begin
                    weight_wr_en <= 1'b0;
                    
                    if (current_synapse < NUM_SYNAPSES - 1) begin
                        current_synapse <= current_synapse + 1;
                        state <= READ_WEIGHT;
                    end else begin
                        state <= DONE_STATE;
                    end
                end
                
                //=============================================================
                // DONE_STATE: Complete
                //=============================================================
                DONE_STATE: begin
                    done <= 1'b1;
                    weight_wr_en <= 1'b0;
                    state <= IDLE;
                end
                
                default: state <= IDLE;
            endcase
        end
    end

endmodule


//-----------------------------------------------------------------------------
// Weight Memory Module (BRAM-based)
//-----------------------------------------------------------------------------
module stdp_weight_memory #(
    parameter NUM_FEATURES  = 20,
    parameter NUM_SYNAPSES  = 150,        // 5x5x6
    parameter WEIGHT_WIDTH  = 8
)(
    input  wire                         clk,
    input  wire                         rst_n,
    
    // Port A: Read
    input  wire                         rd_en,
    input  wire [$clog2(NUM_FEATURES)-1:0] rd_feature,
    input  wire [$clog2(NUM_SYNAPSES)-1:0] rd_synapse,
    output reg  [WEIGHT_WIDTH-1:0]      rd_data,
    output reg                          rd_valid,
    
    // Port B: Write
    input  wire                         wr_en,
    input  wire [$clog2(NUM_FEATURES)-1:0] wr_feature,
    input  wire [$clog2(NUM_SYNAPSES)-1:0] wr_synapse,
    input  wire [WEIGHT_WIDTH-1:0]      wr_data,
    
    // Initialization interface
    input  wire                         init_en,
    input  wire [$clog2(NUM_FEATURES*NUM_SYNAPSES)-1:0] init_addr,
    input  wire [WEIGHT_WIDTH-1:0]      init_data
);

    localparam MEM_SIZE = NUM_FEATURES * NUM_SYNAPSES;
    localparam ADDR_WIDTH = $clog2(MEM_SIZE);
    
    // Weight memory
    reg [WEIGHT_WIDTH-1:0] weights [0:MEM_SIZE-1];
    
    // Address calculation
    wire [ADDR_WIDTH-1:0] rd_addr = rd_feature * NUM_SYNAPSES + rd_synapse;
    wire [ADDR_WIDTH-1:0] wr_addr = wr_feature * NUM_SYNAPSES + wr_synapse;
    
    // Initialize to default values
    integer i;
    initial begin
        for (i = 0; i < MEM_SIZE; i = i + 1) begin
            weights[i] = 8'd128;  // 0.5 in Q0.8
        end
    end
    
    // Read port
    always @(posedge clk) begin
        if (!rst_n) begin
            rd_valid <= 1'b0;
            rd_data <= 0;
        end else if (rd_en) begin
            rd_data <= weights[rd_addr];
            rd_valid <= 1'b1;
        end else begin
            rd_valid <= 1'b0;
        end
    end
    
    // Write port
    always @(posedge clk) begin
        if (init_en) begin
            weights[init_addr] <= init_data;
        end else if (wr_en) begin
            weights[wr_addr] <= wr_data;
        end
    end

endmodule
