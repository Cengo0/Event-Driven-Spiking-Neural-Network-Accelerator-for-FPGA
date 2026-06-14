//-----------------------------------------------------------------------------
// Title         : Core Group - Hierarchical Neuron Core with Local Synapses
// Project       : SpikeMold (HW) + SpikePress (SW)
// File          : core_group.v
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : A neuron core group containing:
//                 - N time-multiplexed LIF neurons (SDP BRAM state)
//                 - Dense local weight memory [N x N] for intra-group synapses
//                 - Intra-group spike recurrence (fire → weight lookup → internal)
//                 - External spike input from event router
//                 - Output spikes to event router for inter-group routing
//
// Architecture:
//   ext_spike_in → [Input FIFO] → [Processing FSM] → neuron state BRAM
//                                       ↑    ↓ (fire)
//                      [intra-group recurrence] → [local weight BRAM read]
//                                                       ↓ (non-zero)
//                                                  [back to FIFO]
//                                  + spike_out → event router
//
// Resource Budget (per group, 128 neurons, 8-bit weights):
//   - Neuron state BRAM: 128 x 24b = 1 BRAM18K
//   - Weight memory: 128 x 128 x 9b ≈ 8 BRAM18K (SDP, incl. exc/inh flag)
//   - Spike FIFO: LUTRAM (~32 entries)
//   - Logic: ~600 LUT, ~200 FF
//   Total per group: ~9 BRAM18K, ~600 LUT
//   16 groups: ~144 BRAM18K, ~9,600 LUT
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps
`include "snn_params.vh"

module core_group #(
    parameter GROUP_ID              = 0,
    parameter NEURONS_PER_GROUP     = `SNN_NEURONS_PER_GROUP,
    parameter DATA_WIDTH            = `SNN_DATA_WIDTH,
    parameter WEIGHT_WIDTH          = `SNN_WEIGHT_WIDTH,
    parameter THRESHOLD_WIDTH       = `SNN_THRESHOLD_WIDTH,
    parameter LEAK_WIDTH            = `SNN_LEAK_WIDTH,
    parameter REFRAC_WIDTH          = `SNN_REFRAC_WIDTH,
    parameter SPIKE_BUFFER_DEPTH    = `SNN_SPIKE_BUFFER_DEPTH,
    parameter ENABLE_INTRA_RECURRENCE = 1,
    parameter LOCAL_ID_WIDTH        = $clog2(NEURONS_PER_GROUP)
)(
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         enable,

    // --- External Spike Input (from Event Router) ---
    input  wire                         ext_spike_valid,
    input  wire [LOCAL_ID_WIDTH-1:0]    ext_spike_dest_id,
    input  wire [WEIGHT_WIDTH-1:0]      ext_spike_weight,
    input  wire                         ext_spike_exc_inh,  // 1=excitatory
    input  wire [THRESHOLD_WIDTH-1:0]   ext_spike_threshold,
    output wire                         ext_spike_ready,

    // --- Output Spike (to Event Router for inter-group routing) ---
    output wire                         out_spike_valid,
    output wire [LOCAL_ID_WIDTH-1:0]    out_spike_neuron_id,
    input  wire                         out_spike_ready,

    // --- Global Neuron Parameters ---
    input  wire [THRESHOLD_WIDTH-1:0]   global_threshold,
    input  wire [LEAK_WIDTH-1:0]        global_leak_rate,
    input  wire [REFRAC_WIDTH-1:0]      global_refrac_period,

    // --- Wide-layer Commit Control ---
    input  wire                         accumulate_only,
    input  wire                         commit_start,
    input  wire [THRESHOLD_WIDTH-1:0]   commit_threshold,
    output wire                         commit_busy,
    output reg                          commit_done,
    input  wire                         clear_start,
    output wire                         clear_busy,
    output reg                          clear_done,

    // --- Weight Load Interface (from Host/HLS) ---
    input  wire                         weight_we,
    input  wire [LOCAL_ID_WIDTH-1:0]    weight_src_id,
    input  wire [LOCAL_ID_WIDTH-1:0]    weight_dst_id,
    input  wire [WEIGHT_WIDTH-1:0]      weight_data,
    input  wire                         weight_exc,     // 1=excitatory weight

    // --- Status ---
    output wire [15:0]                  spike_count,
    output wire                         group_busy
);

    //=========================================================================
    // Derived Parameters
    //=========================================================================
    localparam STATE_WIDTH  = DATA_WIDTH + REFRAC_WIDTH;  // 24 bits
    localparam WEIGHT_DEPTH = NEURONS_PER_GROUP * NEURONS_PER_GROUP;
    localparam WEIGHT_ADDR_WIDTH = $clog2(WEIGHT_DEPTH);
    localparam FIFO_IDX_WIDTH = $clog2(SPIKE_BUFFER_DEPTH);
    localparam FIFO_ENTRY_WIDTH = LOCAL_ID_WIDTH + WEIGHT_WIDTH + 1 + THRESHOLD_WIDTH; // dest + weight + exc + threshold

    //=========================================================================
    // 1. Neuron State Memory (SDP BRAM)
    //    Format: [23:8] membrane (16b), [7:0] refractory (8b)
    //=========================================================================
    reg [STATE_WIDTH-1:0] neuron_state_mem [0:NEURONS_PER_GROUP-1];

    reg  [LOCAL_ID_WIDTH-1:0] ns_wr_addr;
    reg                       ns_we;
    reg  [STATE_WIDTH-1:0]    ns_din;
    reg  [LOCAL_ID_WIDTH-1:0] ns_rd_addr;
    reg  [STATE_WIDTH-1:0]    ns_dout;

    // SDP BRAM: Write port
    always @(posedge clk) begin
        if (ns_we)
            neuron_state_mem[ns_wr_addr] <= ns_din;
    end

    // SDP BRAM: Read port
    always @(posedge clk) begin
        ns_dout <= neuron_state_mem[ns_rd_addr];
    end

    wire [DATA_WIDTH-1:0]   mem_rd  = ns_dout[STATE_WIDTH-1:REFRAC_WIDTH];
    wire [REFRAC_WIDTH-1:0] ref_rd  = ns_dout[REFRAC_WIDTH-1:0];

    //=========================================================================
    // 2. Local Weight Memory (SDP BRAM) - Intra-group dense connections
    //    Address: src_neuron * NEURONS_PER_GROUP + dst_neuron
    //    Data: {excitatory(1), weight(WEIGHT_WIDTH)}
    //=========================================================================
    localparam WM_DATA_WIDTH = WEIGHT_WIDTH + 1;  // weight + exc flag

    reg [WM_DATA_WIDTH-1:0] weight_mem [0:WEIGHT_DEPTH-1];

    reg  [WEIGHT_ADDR_WIDTH-1:0] wm_wr_addr;
    reg                          wm_we;
    reg  [WM_DATA_WIDTH-1:0]     wm_din;
    reg  [WEIGHT_ADDR_WIDTH-1:0] wm_rd_addr;
    reg  [WM_DATA_WIDTH-1:0]     wm_dout;

    // SDP BRAM: Write port
    always @(posedge clk) begin
        if (wm_we)
            weight_mem[wm_wr_addr] <= wm_din;
    end

    // SDP BRAM: Read port
    always @(posedge clk) begin
        wm_dout <= weight_mem[wm_rd_addr];
    end

    wire [WEIGHT_WIDTH-1:0] wm_weight = wm_dout[WEIGHT_WIDTH-1:0];
    wire                    wm_exc    = wm_dout[WM_DATA_WIDTH-1];

    //=========================================================================
    // 3. Spike Input FIFO (LUTRAM - handles external + intra-group recurrent)
    //=========================================================================
    reg [FIFO_ENTRY_WIDTH-1:0] spike_fifo [0:SPIKE_BUFFER_DEPTH-1];
    reg [FIFO_IDX_WIDTH-1:0]   fifo_wr_ptr, fifo_rd_ptr;
    reg [FIFO_IDX_WIDTH:0]     fifo_count;

    wire fifo_empty       = (fifo_count == 0);
    wire fifo_full        = (fifo_count >= SPIKE_BUFFER_DEPTH - 2);  // External backpressure margin
    wire fifo_at_capacity = (fifo_count >= SPIKE_BUFFER_DEPTH);

    // FIFO async read head
    wire [LOCAL_ID_WIDTH-1:0]  fifo_dest   = spike_fifo[fifo_rd_ptr][LOCAL_ID_WIDTH-1:0];
    wire [WEIGHT_WIDTH-1:0]    fifo_weight = spike_fifo[fifo_rd_ptr][LOCAL_ID_WIDTH+WEIGHT_WIDTH-1:LOCAL_ID_WIDTH];
    wire                       fifo_exc    = spike_fifo[fifo_rd_ptr][LOCAL_ID_WIDTH+WEIGHT_WIDTH];
    wire [THRESHOLD_WIDTH-1:0] fifo_threshold =
        spike_fifo[fifo_rd_ptr][FIFO_ENTRY_WIDTH-1:LOCAL_ID_WIDTH+WEIGHT_WIDTH+1];

    //=========================================================================
    // 4. Spike Flag Bitmap (for output scan)
    //=========================================================================
    localparam SF_DEPTH  = (NEURONS_PER_GROUP + 7) / 8;
    localparam SF_ADDR_W = (SF_DEPTH <= 1) ? 1 : $clog2(SF_DEPTH);

    reg [7:0] spike_flag_mem [0:SF_DEPTH-1];

    reg                   sf_set_pending;
    reg [SF_ADDR_W-1:0]   sf_set_addr;
    reg [2:0]             sf_set_bit;
    reg                   sf_clear_pending;
    reg [SF_ADDR_W-1:0]   sf_clear_addr;
    reg [7:0]             sf_clear_mask;
    reg                   tile_clear_flush;

    always @(posedge clk) begin
        if (!rst_n) begin : sf_rst
            integer j;
            for (j = 0; j < SF_DEPTH; j = j + 1)
                spike_flag_mem[j] <= 8'd0;
        end else if (tile_clear_flush) begin : sf_clear_all
            integer j;
            for (j = 0; j < SF_DEPTH; j = j + 1)
                spike_flag_mem[j] <= 8'd0;
        end else begin
            if (sf_set_pending)
                spike_flag_mem[sf_set_addr] <=
                    spike_flag_mem[sf_set_addr] | (8'd1 << sf_set_bit);
            if (sf_clear_pending)
                spike_flag_mem[sf_clear_addr] <=
                    spike_flag_mem[sf_clear_addr] & sf_clear_mask;
        end
    end

    //=========================================================================
    // 5. Combinational: Leak & Synaptic Accumulation (DSP-friendly)
    //=========================================================================
    wire [2:0] shift1     = global_leak_rate[2:0];
    wire [4:0] shift2_cfg = global_leak_rate[7:3];
    wire [2:0] shift2     = shift2_cfg[2:0];
    wire       shift2_en  = (shift2_cfg != 5'd0);

    wire [DATA_WIDTH-1:0] leak_primary   = (shift1 != 3'd0) ? (mem_rd >> shift1) : {DATA_WIDTH{1'b0}};
    wire [DATA_WIDTH-1:0] leak_secondary = (shift2_en && shift2 != 3'd0) ? (mem_rd >> shift2) : {DATA_WIDTH{1'b0}};
    wire [DATA_WIDTH-1:0] leak_total     = leak_primary + leak_secondary;

    // Spike processing: accumulate with sign extension
    reg [WEIGHT_WIDTH-1:0] sp_weight;
    reg                    sp_exc;
    reg [LOCAL_ID_WIDTH-1:0] sp_addr;
    reg [THRESHOLD_WIDTH-1:0] sp_threshold;

    wire [DATA_WIDTH-1:0] weight_ext = {{(DATA_WIDTH-WEIGHT_WIDTH){1'b0}}, sp_weight};
    wire [DATA_WIDTH-1:0] inhibitory_sum =
        (mem_rd >= weight_ext) ? (mem_rd - weight_ext) : {DATA_WIDTH{1'b0}};
    wire [DATA_WIDTH:0] synaptic_sum    = {1'b0, mem_rd} + {1'b0, weight_ext};
    wire [DATA_WIDTH:0] threshold_diff  = synaptic_sum - {1'b0, sp_threshold};
    wire                threshold_hit   = sp_exc && ~threshold_diff[DATA_WIDTH];
    wire [DATA_WIDTH:0] commit_threshold_diff =
        {1'b0, mem_rd} - {1'b0, commit_threshold};
    wire                commit_threshold_hit = ~commit_threshold_diff[DATA_WIDTH];

    //=========================================================================
    // 6. Main Processing FSM
    //=========================================================================
    localparam [3:0]
        ST_IDLE         = 4'd0,
        ST_LEAK_RD      = 4'd1,
        ST_LEAK_CMP     = 4'd2,
        ST_LEAK_WR      = 4'd3,
        ST_SPIKE_RD     = 4'd4,
        ST_SPIKE_CMP    = 4'd5,
        ST_SPIKE_WR     = 4'd6,
        ST_INTRA_ROUTE  = 4'd7,   // Scan local weight matrix for fired neuron
        ST_INTRA_READ   = 4'd8,   // Wait for weight memory read
        ST_RESET_CLEAR  = 4'd9,   // Scrub neuron state BRAM after reset
        ST_COMMIT_RD    = 4'd10,  // Read neuron state during commit scan
        ST_COMMIT_CMP   = 4'd11,  // Compare membrane against commit threshold
        ST_COMMIT_WR    = 4'd12,  // Fire/reset thresholded commit neuron
        ST_CLEAR_STATE  = 4'd13;  // Clear selected destination group state

    reg [3:0] state;
    reg [LOCAL_ID_WIDTH-1:0] leak_idx;
    reg                      leak_cycle_done;
    reg                      sp_fired;
    reg                      neuron_fire_pulse;
    reg [LOCAL_ID_WIDTH-1:0] neuron_fire_id;
    reg [LOCAL_ID_WIDTH-1:0] fired_neuron_id;
    reg [LOCAL_ID_WIDTH-1:0] intra_scan_idx;
    reg [LOCAL_ID_WIDTH-1:0] leak_addr_hold;
    reg [LOCAL_ID_WIDTH-1:0] commit_idx;
    reg [LOCAL_ID_WIDTH-1:0] commit_addr_hold;
    reg                      commit_fired;
    reg                      commit_pending;
    reg [LOCAL_ID_WIDTH-1:0] clear_idx;
    reg                      clear_pending;
    reg [15:0]               total_spikes;

    // FIFO write signals (external or recurrent)
    reg                      fifo_push;
    reg [FIFO_ENTRY_WIDTH-1:0] fifo_push_data;
    reg                      fifo_pop;
    reg                      fifo_push_now;
    reg                      fifo_pop_now;

    // Block external writes during intra-group routing to prevent FIFO write collision.
    // Keep group_busy scoped to event processing only; the background leak sweep
    // can run whenever the group is idle and must not hold the host drain fence.
    wire intra_routing = (state == ST_INTRA_ROUTE || state == ST_INTRA_READ);
    wire commit_scanning = (state == ST_COMMIT_RD) ||
                           (state == ST_COMMIT_CMP) ||
                           (state == ST_COMMIT_WR);
    wire commit_active = commit_pending || commit_scanning;
    wire clear_scanning = (state == ST_CLEAR_STATE);
    wire clear_active = clear_pending || clear_scanning;
    wire event_pipeline_busy = (state == ST_SPIKE_RD) ||
                               (state == ST_SPIKE_CMP) ||
                               (state == ST_SPIKE_WR) ||
                               (state == ST_INTRA_ROUTE) ||
                               (state == ST_INTRA_READ) ||
                               (state == ST_COMMIT_RD) ||
                               (state == ST_COMMIT_CMP) ||
                               (state == ST_COMMIT_WR) ||
                               (state == ST_CLEAR_STATE) ||
                               (state == ST_RESET_CLEAR);
    wire spike_fire_commit =
        (state == ST_SPIKE_WR) && (ref_rd == 0) && sp_fired && !accumulate_only;
    wire commit_fire_commit = (state == ST_COMMIT_WR) && commit_fired;
    wire neuron_fire_commit = spike_fire_commit || commit_fire_commit;
    wire [LOCAL_ID_WIDTH-1:0] neuron_fire_commit_id =
        commit_fire_commit ? commit_addr_hold : sp_addr;
    wire output_pending_busy;
    assign ext_spike_ready =
        !fifo_full && !intra_routing && !commit_active && !clear_active && (state != ST_RESET_CLEAR);
    assign group_busy  = event_pipeline_busy || commit_pending || clear_pending ||
                         !fifo_empty || output_pending_busy;
    assign commit_busy = commit_active;
    assign clear_busy  = clear_active;
    assign spike_count = total_spikes;

    always @(posedge clk) begin
        if (!rst_n) begin
            state           <= ST_RESET_CLEAR;
            leak_idx        <= 0;
            leak_cycle_done <= 0;
            ns_we           <= 0;
            ns_wr_addr      <= 0;
            ns_rd_addr      <= 0;
            ns_din          <= 0;
            wm_we           <= 0;
            wm_rd_addr      <= 0;
            sp_addr         <= 0;
            sp_weight       <= 0;
            sp_exc          <= 0;
            sp_fired        <= 0;
            neuron_fire_pulse <= 0;
            neuron_fire_id  <= 0;
            sp_threshold    <= 0;
            fired_neuron_id <= 0;
            intra_scan_idx  <= 0;
            leak_addr_hold  <= 0;
            commit_idx      <= 0;
            commit_addr_hold <= 0;
            commit_fired    <= 0;
            commit_pending   <= 0;
            commit_done     <= 0;
            clear_idx       <= 0;
            clear_pending   <= 0;
            clear_done      <= 0;
            total_spikes    <= 0;
            sf_set_pending  <= 0;
            sf_set_addr     <= 0;
            sf_set_bit      <= 0;
            tile_clear_flush <= 0;
            fifo_wr_ptr     <= 0;
            fifo_rd_ptr     <= 0;
            fifo_count      <= 0;
            fifo_push       <= 0;
            fifo_pop        <= 0;
            fifo_push_now   <= 0;
            fifo_pop_now    <= 0;
        end else begin
            // Defaults
            ns_we          <= 0;
            sf_set_pending <= 0;
            neuron_fire_pulse <= 0;
            commit_done    <= 0;
            clear_done     <= 0;
            tile_clear_flush <= 0;
            if (clear_start) begin
                clear_pending <= 1;
                commit_pending <= 0;
            end else if (commit_start && !clear_active) begin
                commit_pending <= 1;
            end
            fifo_push_now  = 1'b0;
            fifo_pop_now   = 1'b0;
            wm_we          <= 0;

            //--- External FIFO write (exactly follows ready/valid acceptance) ---
            if (ext_spike_valid && ext_spike_ready) begin
                spike_fifo[fifo_wr_ptr] <= {
                    ext_spike_threshold,
                    ext_spike_exc_inh,
                    ext_spike_weight,
                    ext_spike_dest_id
                };
                fifo_wr_ptr <= fifo_wr_ptr + 1;
                fifo_push_now = 1'b1;
            end

            //--- Weight load (config) ---
            if (weight_we) begin
                wm_we      <= 1;
                wm_wr_addr <= weight_src_id * NEURONS_PER_GROUP + weight_dst_id;
                wm_din     <= {weight_exc, weight_data};
            end

            if (enable || state != ST_IDLE) begin
                case (state)
                    //------------------------------------------------------
                    // Reset scrub: inferred BRAM contents are not cleared by
                    // a one-cycle reset, so clear one neuron state per clock.
                    //------------------------------------------------------
                    ST_RESET_CLEAR: begin
                        ns_we      <= 1;
                        ns_wr_addr <= leak_idx;
                        ns_din     <= {STATE_WIDTH{1'b0}};
                        if (leak_idx + 1 >= NEURONS_PER_GROUP) begin
                            leak_idx        <= 0;
                            leak_cycle_done <= 0;
                            state           <= ST_IDLE;
                        end else begin
                            leak_idx <= leak_idx + 1'b1;
                        end
                    end

                    //------------------------------------------------------
                    ST_IDLE: begin
                        sp_fired <= 0;
                        if ((clear_start || clear_pending) && fifo_empty) begin
                            clear_idx <= 0;
                            clear_pending <= 0;
                            commit_pending <= 0;
                            tile_clear_flush <= 1;
                            state <= ST_CLEAR_STATE;
                        end else if ((commit_start || commit_pending) && fifo_empty) begin
                            commit_idx       <= 0;
                            commit_addr_hold <= 0;
                            commit_fired     <= 0;
                            commit_pending   <= 0;
                            ns_rd_addr       <= 0;
                            state            <= ST_COMMIT_RD;
                        end else if (!fifo_empty) begin
                            // Pop spike from FIFO
                            sp_addr      <= fifo_dest;
                            sp_weight    <= fifo_weight;
                            sp_exc       <= fifo_exc;
                            sp_threshold <= fifo_threshold;
                            ns_rd_addr   <= fifo_dest;
                            fifo_rd_ptr  <= fifo_rd_ptr + 1;
                            fifo_pop_now = 1'b1;
                            state        <= ST_SPIKE_RD;
                        end else if (!leak_cycle_done) begin
                            ns_rd_addr   <= leak_idx;
                            state        <= ST_LEAK_RD;
                        end
                    end

                    //------------------------------------------------------
                    // Leak pipeline: RD → CMP → WR
                    //------------------------------------------------------
                    ST_LEAK_RD: begin
                        leak_addr_hold <= ns_rd_addr;
                        if (!fifo_empty) begin
                            // Interrupt for incoming spike
                            sp_addr      <= fifo_dest;
                            sp_weight    <= fifo_weight;
                            sp_exc       <= fifo_exc;
                            sp_threshold <= fifo_threshold;
                            ns_rd_addr   <= fifo_dest;
                            fifo_rd_ptr  <= fifo_rd_ptr + 1;
                            fifo_pop_now = 1'b1;
                            state        <= ST_SPIKE_RD;
                        end else begin
                            state <= ST_LEAK_CMP;
                        end
                    end

                    ST_LEAK_CMP: begin
                        state <= ST_LEAK_WR;
                    end

                    ST_LEAK_WR: begin
                        ns_we      <= 1;
                        ns_wr_addr <= leak_addr_hold;
                        if (ref_rd > 0)
                            ns_din <= {{DATA_WIDTH{1'b0}}, ref_rd - 1'b1};
                        else if (mem_rd > leak_total)
                            ns_din <= {mem_rd - leak_total, {REFRAC_WIDTH{1'b0}}};
                        else
                            ns_din <= {STATE_WIDTH{1'b0}};

                        leak_idx <= leak_addr_hold + 1;
                        if (leak_addr_hold + 1 >= NEURONS_PER_GROUP) begin
                            leak_idx        <= 0;
                            leak_cycle_done <= 1;
                            state           <= ST_IDLE;
                        end else begin
                            ns_rd_addr <= leak_addr_hold + 1;
                            state      <= ST_LEAK_RD;
                        end
                    end

                    //------------------------------------------------------
                    // Spike pipeline: RD → CMP → WR → (optional INTRA_ROUTE)
                    //------------------------------------------------------
                    ST_SPIKE_RD: begin
                        state <= ST_SPIKE_CMP;
                    end

                    ST_SPIKE_CMP: begin
                        sp_fired <= 0;
                        if (ref_rd == 0 && threshold_hit && !accumulate_only)
                            sp_fired <= 1;
                        state <= ST_SPIKE_WR;
                    end

                    ST_SPIKE_WR: begin
                        ns_we      <= 1;
                        ns_wr_addr <= sp_addr;

                        if (ref_rd > 0) begin
                            ns_din <= ns_dout;  // Keep during refractory
                            state  <= ST_IDLE;  // BUG FIX: was missing → FSM stuck
                        end else if (sp_fired) begin
                            // Fired: reset membrane, set refractory, set flag
                            ns_din <= {{DATA_WIDTH{1'b0}}, global_refrac_period};
                            sf_set_pending <= 1;
                            sf_set_addr    <= sp_addr[LOCAL_ID_WIDTH-1:3];
                            sf_set_bit     <= sp_addr[2:0];
                            total_spikes   <= total_spikes + 1;
                            neuron_fire_pulse <= 1;
                            neuron_fire_id <= sp_addr;

                            if (ENABLE_INTRA_RECURRENCE != 0) begin
                                // Start intra-group recurrent routing.
                                fired_neuron_id <= sp_addr;
                                intra_scan_idx  <= 0;
                                // Issue first weight memory read.
                                wm_rd_addr <= sp_addr * NEURONS_PER_GROUP;  // weight[fired][0]
                                state      <= ST_INTRA_READ;
                            end else begin
                                state <= ST_IDLE;
                            end
                        end else begin
                            // Not fired: update membrane
                            if (sp_exc) begin
                                if (synaptic_sum[DATA_WIDTH])
                                    ns_din <= {{DATA_WIDTH{1'b1}}, ref_rd};  // Saturate
                                else
                                    ns_din <= {synaptic_sum[DATA_WIDTH-1:0], ref_rd};
                            end else begin
                                ns_din <= {inhibitory_sum, ref_rd};
                            end
                            state <= ST_IDLE;
                        end
                    end

                    //------------------------------------------------------
                    // Intra-group recurrent routing (scan local weight row)
                    //------------------------------------------------------
                    ST_INTRA_READ: begin
                        // Wait one cycle for weight memory read
                        state <= ST_INTRA_ROUTE;
                    end

                    ST_INTRA_ROUTE: begin
                        if (wm_weight != 0 && fifo_at_capacity) begin
                            // Hold the current non-zero recurrent event until
                            // a FIFO slot is available; never advance past it.
                            state <= ST_INTRA_ROUTE;
                        end else begin
                            // Process weight readout: if non-zero, push to FIFO.
                            if (wm_weight != 0) begin
                                spike_fifo[fifo_wr_ptr] <= {
                                    global_threshold,
                                    wm_exc,
                                    wm_weight,
                                    intra_scan_idx
                                };
                                fifo_wr_ptr <= fifo_wr_ptr + 1;
                                fifo_push_now = 1'b1;
                            end

                            // Advance scan only after a zero weight or a
                            // successfully queued recurrent event.
                            if (intra_scan_idx + 1 >= NEURONS_PER_GROUP) begin
                                // Done scanning all local connections
                                state <= ST_IDLE;
                            end else begin
                                intra_scan_idx <= intra_scan_idx + 1;
                                wm_rd_addr <= fired_neuron_id * NEURONS_PER_GROUP + intra_scan_idx + 1;
                                state      <= ST_INTRA_READ;
                            end
                        end
                    end

                    //------------------------------------------------------
                    // Commit scan: threshold accumulated membrane state
                    // without relying on a dummy input spike.
                    //------------------------------------------------------
                    ST_COMMIT_RD: begin
                        commit_addr_hold <= ns_rd_addr;
                        state <= ST_COMMIT_CMP;
                    end

                    ST_COMMIT_CMP: begin
                        commit_fired <= 0;
                        if (ref_rd == 0 && commit_threshold_hit) begin
                            commit_fired <= 1;
                        end
                        state <= ST_COMMIT_WR;
                    end

                    ST_COMMIT_WR: begin
                        if (commit_fired) begin
                            ns_we      <= 1;
                            ns_wr_addr <= commit_addr_hold;
                            ns_din     <= {{DATA_WIDTH{1'b0}}, global_refrac_period};
                            sf_set_pending <= 1;
                            sf_set_addr    <= commit_addr_hold[LOCAL_ID_WIDTH-1:3];
                            sf_set_bit     <= commit_addr_hold[2:0];
                            total_spikes   <= total_spikes + 1;
                            neuron_fire_pulse <= 1;
                            neuron_fire_id <= commit_addr_hold;
                        end

                        if (commit_addr_hold + 1 >= NEURONS_PER_GROUP) begin
                            commit_idx  <= 0;
                            commit_done <= 1;
                            state       <= ST_IDLE;
                        end else begin
                            commit_idx <= commit_addr_hold + 1'b1;
                            ns_rd_addr <= commit_addr_hold + 1'b1;
                            state      <= ST_COMMIT_RD;
                        end
                    end

                    //------------------------------------------------------
                    // Selected destination tile/group clear.  The host-level
                    // mask selects which core groups receive clear_start.
                    //------------------------------------------------------
                    ST_CLEAR_STATE: begin
                        ns_we      <= 1;
                        ns_wr_addr <= clear_idx;
                        ns_din     <= {STATE_WIDTH{1'b0}};

                        if (clear_idx + 1 >= NEURONS_PER_GROUP) begin
                            clear_idx       <= 0;
                            leak_idx        <= 0;
                            leak_cycle_done <= 1;
                            clear_done      <= 1;
                            state           <= ST_IDLE;
                        end else begin
                            clear_idx <= clear_idx + 1'b1;
                        end
                    end

                    default: state <= ST_IDLE;
                endcase

                // Reset leak cycle
                if (leak_cycle_done && fifo_empty && state == ST_IDLE)
                    leak_cycle_done <= 0;
            end

            //--- FIFO count management ---
            fifo_push <= fifo_push_now;
            fifo_pop  <= fifo_pop_now;
            case ({fifo_push_now, fifo_pop_now})
                2'b10: fifo_count <= fifo_count + 1;
                2'b01: fifo_count <= fifo_count - 1;
                default: fifo_count <= fifo_count;  // 00 or 11 (push+pop)
            endcase
        end
    end

    //=========================================================================
    // 7. Output Spike FIFO
    //    Preserve fire order for the host-visible frame contract. The bitmap is
    //    still maintained for debug visibility, but output does not depend on a
    //    slow asynchronous scan.
    //=========================================================================
    localparam OUT_FIFO_DEPTH = NEURONS_PER_GROUP;
    localparam OUT_FIFO_PTR_W = (OUT_FIFO_DEPTH <= 1) ? 1 : $clog2(OUT_FIFO_DEPTH);

    reg [LOCAL_ID_WIDTH-1:0] out_spike_fifo [0:OUT_FIFO_DEPTH-1];
    reg [OUT_FIFO_PTR_W-1:0] out_fifo_wr_ptr;
    reg [OUT_FIFO_PTR_W-1:0] out_fifo_rd_ptr;
    reg [OUT_FIFO_PTR_W:0]   out_fifo_count;
    reg [31:0]               out_fifo_drop_count;

    wire out_fifo_empty = (out_fifo_count == 0);
    wire out_fifo_full  = (out_fifo_count == OUT_FIFO_DEPTH);
    wire out_fifo_pop   = (!out_fifo_empty && out_spike_ready);
    wire out_fifo_push  = neuron_fire_commit && (!out_fifo_full || out_fifo_pop);

    assign output_pending_busy = !out_fifo_empty || neuron_fire_commit;
    assign out_spike_valid = !out_fifo_empty;
    assign out_spike_neuron_id = out_spike_fifo[out_fifo_rd_ptr];

    always @(posedge clk) begin
        if (!rst_n || tile_clear_flush) begin
            out_fifo_wr_ptr     <= 0;
            out_fifo_rd_ptr     <= 0;
            out_fifo_count      <= 0;
            out_fifo_drop_count <= 0;
            sf_clear_pending    <= 0;
            sf_clear_addr       <= 0;
            sf_clear_mask       <= 8'hFF;
        end else begin
            sf_clear_pending <= 0;

            if (out_fifo_push) begin
                out_spike_fifo[out_fifo_wr_ptr] <= neuron_fire_commit_id;
                if (out_fifo_wr_ptr == OUT_FIFO_DEPTH - 1)
                    out_fifo_wr_ptr <= 0;
                else
                    out_fifo_wr_ptr <= out_fifo_wr_ptr + 1'b1;
            end else if (neuron_fire_commit) begin
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

        end
    end

    //=========================================================================
    // Memory initialization (simulation only)
    //=========================================================================
    integer init_i;
    initial begin
        for (init_i = 0; init_i < NEURONS_PER_GROUP; init_i = init_i + 1)
            neuron_state_mem[init_i] = {STATE_WIDTH{1'b0}};
        for (init_i = 0; init_i < WEIGHT_DEPTH; init_i = init_i + 1)
            weight_mem[init_i] = {WM_DATA_WIDTH{1'b0}};
        for (init_i = 0; init_i < SF_DEPTH; init_i = init_i + 1)
            spike_flag_mem[init_i] = 8'd0;
        for (init_i = 0; init_i < SPIKE_BUFFER_DEPTH; init_i = init_i + 1)
            spike_fifo[init_i] = {FIFO_ENTRY_WIDTH{1'b0}};
        for (init_i = 0; init_i < OUT_FIFO_DEPTH; init_i = init_i + 1)
            out_spike_fifo[init_i] = {LOCAL_ID_WIDTH{1'b0}};
    end

endmodule
