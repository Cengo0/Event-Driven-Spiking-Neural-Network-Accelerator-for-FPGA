//-----------------------------------------------------------------------------
// Title         : LIF Neuron Array - SDP BRAM/DSP Optimized (v3)
// Project       : SpikeMold-EDNP
// File          : lif_neuron_array.v
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : Area-optimized LIF neuron array using:
//                 - Simple Dual-Port BRAM for neuron state (UG901 SDP)
//                 - DSP48E1 for synaptic accumulation
//                 - Time-multiplexed leak processing
//                 - Distributed RAM spike flag storage
//                 Supports up to 1024 neurons on xc7z020.
//
// Optimization Summary (v3 vs v2):
//   - TDP BRAM → SDP BRAM (fixes Vivado synthesis at 1024 depth)
//   - Separate read/write ports fix address-override bug in leak FSM
//   - 256→1024 neurons: only +292 LUT (+0.55%), timing met
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps

module lif_neuron_array #(
    parameter NUM_NEURONS           = 256,
    parameter NUM_AXONS             = 256,
    parameter DATA_WIDTH            = 16,
    parameter WEIGHT_WIDTH          = 8,
    parameter THRESHOLD_WIDTH       = 16,
    parameter LEAK_WIDTH            = 8,
    parameter REFRAC_WIDTH          = 8,
    parameter NUM_PARALLEL_UNITS    = 4,      // Reduced from 8 to save LUT
    parameter SPIKE_BUFFER_DEPTH    = 64,
    parameter USE_BRAM              = 1,
    parameter USE_DSP               = 1,
    parameter NEURON_ID_WIDTH       = $clog2(NUM_NEURONS)
)(
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         enable,

    // Input spike interface (AXI-Stream)
    input  wire                         s_axis_spike_valid,
    input  wire [NEURON_ID_WIDTH-1:0]   s_axis_spike_dest_id,
    input  wire [WEIGHT_WIDTH-1:0]      s_axis_spike_weight,
    input  wire                         s_axis_spike_exc_inh,
    output wire                         s_axis_spike_ready,

    // Output spike interface
    output wire                         m_axis_spike_valid,
    output wire [NEURON_ID_WIDTH-1:0]   m_axis_spike_neuron_id,
    input  wire                         m_axis_spike_ready,

    // Configuration interface
    input  wire                         config_we,
    input  wire [NEURON_ID_WIDTH-1:0]   config_addr,
    input  wire [31:0]                  config_data,

    // Global neuron parameters
    input  wire [THRESHOLD_WIDTH-1:0]   global_threshold,
    input  wire [LEAK_WIDTH-1:0]        global_leak_rate,
    input  wire [REFRAC_WIDTH-1:0]      global_refrac_period,

    // Status
    output wire [31:0]                  spike_count,
    output wire                         array_busy,
    output wire [31:0]                  throughput_counter,
    output wire [7:0]                   active_neurons
);

    localparam STATE_WIDTH = DATA_WIDTH + REFRAC_WIDTH;  // 24 bits

    //=========================================================================
    // Neuron State: Simple Dual-Port BRAM (UG901 SDP template)
    //=========================================================================
    // Port A (write-only): leak writes + spike writes + config writes
    // Port B (read-only):  leak reads + spike reads
    // Format: [23:8] = membrane (16-bit), [7:0] = refractory (8-bit)
    // SDP guarantees BRAM inference at any depth (1024+) unlike TDP
    //=========================================================================
    // SDP guarantees BRAM inference at any depth (1024+) when active
    // Vivado auto-selects: BRAM when memory has real data flow, optimized away when idle
    reg [STATE_WIDTH-1:0] neuron_state_mem [0:NUM_NEURONS-1];

    // Write port signals
    reg  [NEURON_ID_WIDTH-1:0] bram_wr_addr;
    reg                        bram_we;
    reg  [STATE_WIDTH-1:0]     bram_din;

    // Read port signals
    reg  [NEURON_ID_WIDTH-1:0] bram_rd_addr;
    reg  [STATE_WIDTH-1:0]     bram_dout;

    // SDP BRAM: Write port (Port A)
    always @(posedge clk) begin
        if (bram_we)
            neuron_state_mem[bram_wr_addr] <= bram_din;
    end

    // SDP BRAM: Read port (Port B)
    always @(posedge clk) begin
        bram_dout <= neuron_state_mem[bram_rd_addr];
    end

    // Convenience splits for read output (serves both leak and spike paths)
    wire [DATA_WIDTH-1:0]   mem_rd = bram_dout[STATE_WIDTH-1:REFRAC_WIDTH];
    wire [REFRAC_WIDTH-1:0] ref_rd = bram_dout[REFRAC_WIDTH-1:0];

    //=========================================================================
    // Spike Flag Memory (BRAM-based bitmap)
    //=========================================================================
    // One bit per neuron, packed 8 per byte.
    // Set from spike processing, cleared by output scan.
    //=========================================================================
    localparam SF_DEPTH  = (NUM_NEURONS + 7) / 8;
    localparam SF_ADDR_W = (SF_DEPTH <= 1) ? 1 : $clog2(SF_DEPTH);

    // Spike flag: distributed RAM (small, has sync reset + read-modify-write)
    reg [7:0] spike_flag_mem [0:SF_DEPTH-1];

    // Set interface
    reg                   sf_set_pending;
    reg [SF_ADDR_W-1:0]   sf_set_addr;
    reg [2:0]             sf_set_bit;

    // Clear interface
    reg                   sf_clear_pending;
    reg [SF_ADDR_W-1:0]   sf_clear_addr;
    reg [7:0]             sf_clear_mask;

    always @(posedge clk) begin
        if (!rst_n) begin : sf_rst_blk
            integer j;
            for (j = 0; j < SF_DEPTH; j = j + 1)
                spike_flag_mem[j] <= 8'd0;
        end else begin
            if (sf_set_pending)
                spike_flag_mem[sf_set_addr] <= spike_flag_mem[sf_set_addr] | (8'd1 << sf_set_bit);
            if (sf_clear_pending)
                spike_flag_mem[sf_clear_addr] <= spike_flag_mem[sf_clear_addr] & sf_clear_mask;
        end
    end

    //=========================================================================
    // Input Spike FIFO (LUT RAM - small, async read needed)
    //=========================================================================
    localparam FIFO_WIDTH = NEURON_ID_WIDTH + WEIGHT_WIDTH + 1;
    reg [FIFO_WIDTH-1:0] spike_fifo [0:SPIKE_BUFFER_DEPTH-1];
    reg [$clog2(SPIKE_BUFFER_DEPTH)-1:0] fifo_wr_ptr, fifo_rd_ptr;
    reg [$clog2(SPIKE_BUFFER_DEPTH):0]   fifo_count;

    wire fifo_empty = (fifo_count == 0);
    wire fifo_full  = (fifo_count == SPIKE_BUFFER_DEPTH);
    assign s_axis_spike_ready = !fifo_full;

    // FIFO async-read head
    wire [NEURON_ID_WIDTH-1:0] fifo_dest   = spike_fifo[fifo_rd_ptr][NEURON_ID_WIDTH-1:0];
    wire [WEIGHT_WIDTH-1:0]    fifo_weight = spike_fifo[fifo_rd_ptr][NEURON_ID_WIDTH+WEIGHT_WIDTH-1:NEURON_ID_WIDTH];
    wire                       fifo_exc    = spike_fifo[fifo_rd_ptr][FIFO_WIDTH-1];

    //=========================================================================
    // Spike processing registers (declared early for DSP block usage)
    //=========================================================================
    reg [NEURON_ID_WIDTH-1:0] sp_addr;
    reg [WEIGHT_WIDTH-1:0]    sp_weight;
    reg                       sp_exc;
    reg                       sp_fired;
    reg                       neuron_fire_pulse;
    reg [NEURON_ID_WIDTH-1:0] neuron_fire_id;
    reg [DATA_WIDTH-1:0]      mem_pipe;
    reg [REFRAC_WIDTH-1:0]    ref_pipe;
    reg                       leak_spike_pending;
    reg [NEURON_ID_WIDTH-1:0] leak_sp_addr_pending;
    reg [WEIGHT_WIDTH-1:0]    leak_sp_weight_pending;
    reg                       leak_sp_exc_pending;

    //=========================================================================
    // Shift-based Leak Parameters
    //=========================================================================
    wire [2:0] shift1     = global_leak_rate[2:0];
    wire [4:0] shift2_cfg = global_leak_rate[7:3];
    wire [2:0] shift2     = shift2_cfg[2:0];
    wire       shift2_en  = (shift2_cfg != 5'd0);

    // Leak combinational path (DSP-inferred add)
    wire [DATA_WIDTH-1:0] leak_primary   = (shift1 != 3'd0) ? (mem_pipe >> shift1) : {DATA_WIDTH{1'b0}};
    wire [DATA_WIDTH-1:0] leak_secondary = (shift2_en && shift2 != 3'd0) ? (mem_pipe >> shift2) : {DATA_WIDTH{1'b0}};
    (* use_dsp = "yes" *) wire [DATA_WIDTH-1:0] leak_total;
    assign leak_total = leak_primary + leak_secondary;

    //=========================================================================
    // DSP-friendly Synaptic Accumulation
    //=========================================================================
    // Force DSP48E1 inference: accumulate + threshold compare
    (* use_dsp = "yes" *) wire [DATA_WIDTH:0] synaptic_sum_curr;
    assign synaptic_sum_curr = {1'b0, mem_rd} + {{(DATA_WIDTH-WEIGHT_WIDTH+1){1'b0}}, sp_weight};
    (* use_dsp = "yes" *) wire [DATA_WIDTH:0] threshold_diff_curr;
    assign threshold_diff_curr = synaptic_sum_curr - {1'b0, global_threshold};
    (* use_dsp = "yes" *) wire [DATA_WIDTH:0] synaptic_sum_pipe;
    assign synaptic_sum_pipe = {1'b0, mem_pipe} + {{(DATA_WIDTH-WEIGHT_WIDTH+1){1'b0}}, sp_weight};

    //=========================================================================
    // Main State Machine
    //=========================================================================
    localparam [2:0]
        ST_IDLE     = 3'd0,
        ST_LEAK_RD  = 3'd1,
        ST_LEAK_CMP = 3'd2,
        ST_LEAK_WR  = 3'd3,
        ST_SPIKE_RD = 3'd4,
        ST_SPIKE_CMP = 3'd5,
        ST_SPIKE_WR = 3'd6;

    reg [2:0] state;
    reg [NEURON_ID_WIDTH-1:0] leak_idx;
    reg leak_cycle_done;

    // Leak hold registers
    reg [NEURON_ID_WIDTH-1:0] leak_addr_hold;

    assign array_busy = (state != ST_IDLE) || !fifo_empty;

    always @(posedge clk) begin
        if (!rst_n) begin
            state <= ST_IDLE;
            leak_idx <= 0;
            leak_cycle_done <= 0;
            bram_we <= 0;
            bram_wr_addr <= 0;
            bram_rd_addr <= 0;
            bram_din <= 0;
            sp_addr <= 0;
            sp_weight <= 0;
            sp_exc <= 0;
            sp_fired <= 0;
            neuron_fire_pulse <= 0;
            neuron_fire_id <= 0;
            mem_pipe <= 0;
            ref_pipe <= 0;
            leak_spike_pending <= 0;
            leak_sp_addr_pending <= 0;
            leak_sp_weight_pending <= 0;
            leak_sp_exc_pending <= 0;
            leak_addr_hold <= 0;
            sf_set_pending <= 0;
            sf_set_addr <= 0;
            sf_set_bit <= 0;
            fifo_wr_ptr <= 0;
            fifo_rd_ptr <= 0;
            fifo_count <= 0;
        end else begin
            // Defaults
            bram_we <= 0;
            sf_set_pending <= 0;
            neuron_fire_pulse <= 0;

            // FIFO write (always active)
            if (s_axis_spike_valid && !fifo_full) begin
                spike_fifo[fifo_wr_ptr] <= {s_axis_spike_exc_inh, s_axis_spike_weight, s_axis_spike_dest_id};
                fifo_wr_ptr <= fifo_wr_ptr + 1;
            end

            if (enable || state != ST_IDLE) begin
                case (state)
                    //------------------------------------------------------
                    ST_IDLE: begin
                        sp_fired <= 0;

                        if (!fifo_empty) begin
                            // Capture spike from FIFO, issue BRAM read
                            sp_addr   <= fifo_dest;
                            sp_weight <= fifo_weight;
                            sp_exc    <= fifo_exc;
                            bram_rd_addr <= fifo_dest;
                            fifo_rd_ptr <= fifo_rd_ptr + 1;
                            state <= ST_SPIKE_RD;
                        end else if (!leak_cycle_done) begin
                            bram_rd_addr <= leak_idx;
                            state <= ST_LEAK_RD;
                        end
                    end

                    //------------------------------------------------------
                    // Leak pipeline: RD -> CMP -> WR (3 cycles per neuron)
                    //------------------------------------------------------
                    ST_LEAK_RD: begin
                        leak_addr_hold <= bram_rd_addr;
                        // Interrupt leak for incoming spike
                        if (!fifo_empty) begin
                            sp_addr   <= fifo_dest;
                            sp_weight <= fifo_weight;
                            sp_exc    <= fifo_exc;
                            bram_rd_addr <= fifo_dest;
                            fifo_rd_ptr <= fifo_rd_ptr + 1;
                            state <= ST_SPIKE_RD;
                        end else begin
                            state <= ST_LEAK_CMP;
                        end
                    end

                    ST_LEAK_CMP: begin
                        // Capture BRAM output into local pipeline registers
                        mem_pipe <= mem_rd;
                        ref_pipe <= ref_rd;

                        // Optionally queue one spike, then commit leak write next cycle
                        leak_spike_pending <= 0;
                        if (!fifo_empty) begin
                            leak_spike_pending <= 1;
                            leak_sp_addr_pending <= fifo_dest;
                            leak_sp_weight_pending <= fifo_weight;
                            leak_sp_exc_pending <= fifo_exc;
                            fifo_rd_ptr <= fifo_rd_ptr + 1;
                        end
                        state <= ST_LEAK_WR;
                    end

                    ST_LEAK_WR: begin
                        bram_we  <= 1;
                        bram_wr_addr <= leak_addr_hold;  // Write port (separate from read)

                        if (ref_pipe > 0)
                            bram_din <= {{DATA_WIDTH{1'b0}}, ref_pipe - 1'b1};
                        else if (mem_pipe > leak_total)
                            bram_din <= {mem_pipe - leak_total, {REFRAC_WIDTH{1'b0}}};
                        else
                            bram_din <= {STATE_WIDTH{1'b0}};

                        // Advance leak index
                        leak_idx <= leak_addr_hold + 1'b1;
                        if (leak_addr_hold + 1 >= NUM_NEURONS) begin
                            leak_idx <= 0;
                            leak_cycle_done <= 1;
                            if (leak_spike_pending) begin
                                sp_addr <= leak_sp_addr_pending;
                                sp_weight <= leak_sp_weight_pending;
                                sp_exc <= leak_sp_exc_pending;
                                bram_rd_addr <= leak_sp_addr_pending;
                                leak_spike_pending <= 0;
                                state <= ST_SPIKE_RD;
                            end else begin
                                state <= ST_IDLE;
                            end
                        end else begin
                            if (leak_spike_pending) begin
                                sp_addr <= leak_sp_addr_pending;
                                sp_weight <= leak_sp_weight_pending;
                                sp_exc <= leak_sp_exc_pending;
                                bram_rd_addr <= leak_sp_addr_pending;
                                leak_spike_pending <= 0;
                                state <= ST_SPIKE_RD;
                            end else begin
                                bram_rd_addr <= leak_addr_hold + 1'b1;  // Read port (independent)
                                state <= ST_LEAK_RD;
                            end
                        end
                    end

                    //------------------------------------------------------
                    // Spike pipeline: RD -> CMP -> WR (3 cycles)
                    //------------------------------------------------------
                    ST_SPIKE_RD: begin
                        state <= ST_SPIKE_CMP;
                    end

                    ST_SPIKE_CMP: begin
                        mem_pipe <= mem_rd;
                        ref_pipe <= ref_rd;
                        sp_fired <= 0;
                        if (ref_rd == 0 && sp_exc) begin
                            if (~threshold_diff_curr[DATA_WIDTH]) // DSP: sum >= threshold
                                sp_fired <= 1;
                        end
                        state <= ST_SPIKE_WR;
                    end

                    ST_SPIKE_WR: begin
                        bram_we  <= 1;
                        bram_wr_addr <= sp_addr;

                        if (ref_pipe > 0) begin
                            bram_din <= {mem_pipe, ref_pipe};  // Keep as-is during refractory
                        end else if (sp_fired) begin
                            bram_din <= {{DATA_WIDTH{1'b0}}, global_refrac_period};
                            sf_set_pending <= 1;
                            sf_set_addr <= sp_addr[NEURON_ID_WIDTH-1:3];
                            sf_set_bit  <= sp_addr[2:0];
                            neuron_fire_pulse <= 1;
                            neuron_fire_id <= sp_addr;
                        end else begin
                            // Not fired - update membrane
                            if (sp_exc) begin
                                if (synaptic_sum_pipe[DATA_WIDTH])
                                    bram_din <= {{DATA_WIDTH{1'b1}}, ref_pipe};  // Saturate
                                else
                                    bram_din <= {synaptic_sum_pipe[DATA_WIDTH-1:0], ref_pipe};
                            end else begin
                                // Inhibitory
                                if (mem_pipe >= sp_weight)
                                    bram_din <= {mem_pipe - {{(DATA_WIDTH-WEIGHT_WIDTH){1'b0}}, sp_weight}, ref_pipe};
                                else
                                    bram_din <= {{DATA_WIDTH{1'b0}}, ref_pipe};
                            end
                        end

                        state <= ST_IDLE;
                    end

                    default: state <= ST_IDLE;
                endcase

                // Reset leak_cycle_done for continuous operation
                if (leak_cycle_done && fifo_empty && state == ST_IDLE)
                    leak_cycle_done <= 0;

                // Config write override (highest priority)
                if (config_we && config_addr < NUM_NEURONS) begin
                    bram_we  <= 1;
                    bram_wr_addr <= config_addr;
                    case (config_data[31:30])
                        2'b00: bram_din <= {config_data[DATA_WIDTH-1:0], bram_dout[REFRAC_WIDTH-1:0]};
                        2'b01: bram_din <= {bram_dout[STATE_WIDTH-1:REFRAC_WIDTH], config_data[REFRAC_WIDTH-1:0]};
                        default: bram_din <= bram_dout;
                    endcase
                end
            end

            // FIFO count management
            // Detect transitions that consume from FIFO
            if (state == ST_IDLE && !fifo_empty && enable) begin
                // Will consume one entry
                if (s_axis_spike_valid && !fifo_full)
                    fifo_count <= fifo_count;  // simultaneous push+pop
                else
                    fifo_count <= fifo_count - 1;
            end else if ((state == ST_LEAK_RD || state == ST_LEAK_CMP) && !fifo_empty) begin
                // Leak interrupted by spike - consume
                if (s_axis_spike_valid && !fifo_full)
                    fifo_count <= fifo_count;
                else
                    fifo_count <= fifo_count - 1;
            end else if (s_axis_spike_valid && !fifo_full) begin
                fifo_count <= fifo_count + 1;
            end
        end
    end

    //=========================================================================
    // Output Spike Generation
    //=========================================================================
    localparam OUT_FIFO_DEPTH = NUM_NEURONS;
    localparam OUT_FIFO_PTR_W = (OUT_FIFO_DEPTH <= 1) ? 1 : $clog2(OUT_FIFO_DEPTH);

    reg [NEURON_ID_WIDTH-1:0] out_spike_fifo [0:OUT_FIFO_DEPTH-1];
    reg [OUT_FIFO_PTR_W-1:0]  out_fifo_wr_ptr;
    reg [OUT_FIFO_PTR_W-1:0]  out_fifo_rd_ptr;
    reg [OUT_FIFO_PTR_W:0]    out_fifo_count;
    reg [31:0]                out_fifo_drop_count;

    wire out_fifo_empty = (out_fifo_count == 0);
    wire out_fifo_full  = (out_fifo_count == OUT_FIFO_DEPTH);
    wire out_fifo_pop   = (!out_fifo_empty && m_axis_spike_ready);
    wire out_fifo_push  = neuron_fire_pulse && (!out_fifo_full || out_fifo_pop);

    assign m_axis_spike_valid     = !out_fifo_empty;
    assign m_axis_spike_neuron_id = out_spike_fifo[out_fifo_rd_ptr];

    reg [31:0] total_spikes;
    reg [31:0] throughput_cnt;
    reg [7:0]  active_neuron_cnt;

    assign spike_count        = total_spikes;
    assign throughput_counter = throughput_cnt;
    assign active_neurons     = active_neuron_cnt;

    always @(posedge clk) begin
        if (!rst_n) begin
            total_spikes <= 0;
            throughput_cnt <= 0;
            active_neuron_cnt <= 0;
            out_fifo_wr_ptr <= 0;
            out_fifo_rd_ptr <= 0;
            out_fifo_count <= 0;
            out_fifo_drop_count <= 0;
            sf_clear_pending <= 0;
            sf_clear_addr <= 0;
            sf_clear_mask <= 8'hFF;
        end else begin
            sf_clear_pending <= 0;
            throughput_cnt <= throughput_cnt + 1;
            if (neuron_fire_pulse) begin
                total_spikes <= total_spikes + 1;
                active_neuron_cnt <= active_neuron_cnt + 1;
            end

            if (out_fifo_push) begin
                out_spike_fifo[out_fifo_wr_ptr] <= neuron_fire_id;
                if (out_fifo_wr_ptr == OUT_FIFO_DEPTH - 1)
                    out_fifo_wr_ptr <= 0;
                else
                    out_fifo_wr_ptr <= out_fifo_wr_ptr + 1'b1;
            end else if (neuron_fire_pulse) begin
                // Should be unreachable in steady state because pop+push is allowed,
                // but keep a drop counter for overflow diagnostics.
                out_fifo_drop_count <= out_fifo_drop_count + 1'b1;
            end

            if (out_fifo_pop) begin
                if (out_fifo_rd_ptr == OUT_FIFO_DEPTH - 1)
                    out_fifo_rd_ptr <= 0;
                else
                    out_fifo_rd_ptr <= out_fifo_rd_ptr + 1'b1;
            end

            case ({out_fifo_push, out_fifo_pop})
                2'b10: out_fifo_count <= out_fifo_count + 1'b1;
                2'b01: out_fifo_count <= out_fifo_count - 1'b1;
                default: out_fifo_count <= out_fifo_count;
            endcase

            if (throughput_cnt[15:0] == 0)
                active_neuron_cnt <= 0;
        end
    end

    //=========================================================================
    // Memory Init (simulation only)
    //=========================================================================
    integer init_i;
    initial begin
        for (init_i = 0; init_i < NUM_NEURONS; init_i = init_i + 1)
            neuron_state_mem[init_i] = {STATE_WIDTH{1'b0}};
        for (init_i = 0; init_i < SF_DEPTH; init_i = init_i + 1)
            spike_flag_mem[init_i] = 8'd0;
        for (init_i = 0; init_i < SPIKE_BUFFER_DEPTH; init_i = init_i + 1)
            spike_fifo[init_i] = {FIFO_WIDTH{1'b0}};
        for (init_i = 0; init_i < OUT_FIFO_DEPTH; init_i = init_i + 1)
            out_spike_fifo[init_i] = {NEURON_ID_WIDTH{1'b0}};
    end

endmodule
