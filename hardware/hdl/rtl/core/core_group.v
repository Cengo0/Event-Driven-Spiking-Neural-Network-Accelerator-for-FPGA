//-----------------------------------------------------------------------------
// Title         : Core Group - Hierarchical Neuron Core with Local Synapses
// Project       : PYNQ-Z2 SNN Accelerator
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
    output wire                         ext_spike_ready,

    // --- Output Spike (to Event Router for inter-group routing) ---
    output reg                          out_spike_valid,
    output reg  [LOCAL_ID_WIDTH-1:0]    out_spike_neuron_id,
    input  wire                         out_spike_ready,

    // --- Global Neuron Parameters ---
    input  wire [THRESHOLD_WIDTH-1:0]   global_threshold,
    input  wire [LEAK_WIDTH-1:0]        global_leak_rate,
    input  wire [REFRAC_WIDTH-1:0]      global_refrac_period,

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
    localparam FIFO_ENTRY_WIDTH = LOCAL_ID_WIDTH + WEIGHT_WIDTH + 1; // dest + weight + exc

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

    wire fifo_empty = (fifo_count == 0);
    wire fifo_full  = (fifo_count >= SPIKE_BUFFER_DEPTH - 2);  // Leave room for recurrent

    // FIFO async read head
    wire [LOCAL_ID_WIDTH-1:0]  fifo_dest   = spike_fifo[fifo_rd_ptr][LOCAL_ID_WIDTH-1:0];
    wire [WEIGHT_WIDTH-1:0]    fifo_weight = spike_fifo[fifo_rd_ptr][LOCAL_ID_WIDTH+WEIGHT_WIDTH-1:LOCAL_ID_WIDTH];
    wire                       fifo_exc    = spike_fifo[fifo_rd_ptr][FIFO_ENTRY_WIDTH-1];

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

    always @(posedge clk) begin
        if (!rst_n) begin : sf_rst
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

    wire [DATA_WIDTH:0] synaptic_sum    = {1'b0, mem_rd} + {{(DATA_WIDTH-WEIGHT_WIDTH+1){1'b0}}, sp_weight};
    wire [DATA_WIDTH:0] threshold_diff  = synaptic_sum - {1'b0, global_threshold};
    wire                threshold_hit   = sp_exc && ~threshold_diff[DATA_WIDTH];

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
        ST_INTRA_READ   = 4'd8;   // Wait for weight memory read

    reg [3:0] state;
    reg [LOCAL_ID_WIDTH-1:0] leak_idx;
    reg                      leak_cycle_done;
    reg                      sp_fired;
    reg [LOCAL_ID_WIDTH-1:0] fired_neuron_id;
    reg [LOCAL_ID_WIDTH-1:0] intra_scan_idx;
    reg [LOCAL_ID_WIDTH-1:0] leak_addr_hold;
    reg [15:0]               total_spikes;

    // FIFO write signals (external or recurrent)
    reg                      fifo_push;
    reg [FIFO_ENTRY_WIDTH-1:0] fifo_push_data;
    reg                      fifo_pop;

    // Block external writes during intra-group routing to prevent FIFO write collision
    wire intra_routing = (state == ST_INTRA_ROUTE || state == ST_INTRA_READ);
    assign ext_spike_ready = !fifo_full && !intra_routing;
    assign group_busy  = (state != ST_IDLE) || !fifo_empty;
    assign spike_count = total_spikes;

    always @(posedge clk) begin
        if (!rst_n) begin
            state           <= ST_IDLE;
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
            fired_neuron_id <= 0;
            intra_scan_idx  <= 0;
            leak_addr_hold  <= 0;
            total_spikes    <= 0;
            sf_set_pending  <= 0;
            sf_set_addr     <= 0;
            sf_set_bit      <= 0;
            fifo_wr_ptr     <= 0;
            fifo_rd_ptr     <= 0;
            fifo_count      <= 0;
            fifo_push       <= 0;
            fifo_pop        <= 0;
        end else begin
            // Defaults
            ns_we          <= 0;
            sf_set_pending <= 0;
            fifo_push      <= 0;
            fifo_pop       <= 0;
            wm_we          <= 0;

            //--- External FIFO write (blocked during intra-group routing) ---
            if (ext_spike_valid && !fifo_full && !intra_routing) begin
                spike_fifo[fifo_wr_ptr] <= {ext_spike_exc_inh, ext_spike_weight, ext_spike_dest_id};
                fifo_wr_ptr <= fifo_wr_ptr + 1;
                fifo_push   <= 1;
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
                    ST_IDLE: begin
                        sp_fired <= 0;
                        if (!fifo_empty) begin
                            // Pop spike from FIFO
                            sp_addr      <= fifo_dest;
                            sp_weight    <= fifo_weight;
                            sp_exc       <= fifo_exc;
                            ns_rd_addr   <= fifo_dest;
                            fifo_rd_ptr  <= fifo_rd_ptr + 1;
                            fifo_pop     <= 1;
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
                            ns_rd_addr   <= fifo_dest;
                            fifo_rd_ptr  <= fifo_rd_ptr + 1;
                            fifo_pop     <= 1;
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
                        if (ref_rd == 0 && sp_exc) begin
                            if (~threshold_diff[DATA_WIDTH])
                                sp_fired <= 1;
                        end
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

                            // Start intra-group recurrent routing
                            fired_neuron_id <= sp_addr;
                            intra_scan_idx  <= 0;
                            // Issue first weight memory read
                            wm_rd_addr <= sp_addr * NEURONS_PER_GROUP;  // weight[fired][0]
                            state      <= ST_INTRA_READ;
                        end else begin
                            // Not fired: update membrane
                            if (sp_exc) begin
                                if (synaptic_sum[DATA_WIDTH])
                                    ns_din <= {{DATA_WIDTH{1'b1}}, ref_rd};  // Saturate
                                else
                                    ns_din <= {synaptic_sum[DATA_WIDTH-1:0], ref_rd};
                            end else begin
                                if (mem_rd >= {{(DATA_WIDTH-WEIGHT_WIDTH){1'b0}}, sp_weight})
                                    ns_din <= {mem_rd - {{(DATA_WIDTH-WEIGHT_WIDTH){1'b0}}, sp_weight}, ref_rd};
                                else
                                    ns_din <= {{DATA_WIDTH{1'b0}}, ref_rd};
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
                        // Process weight readout: if non-zero, push to FIFO
                        if (wm_weight != 0 && !fifo_full) begin
                            spike_fifo[fifo_wr_ptr] <= {wm_exc, wm_weight, intra_scan_idx};
                            fifo_wr_ptr <= fifo_wr_ptr + 1;
                            fifo_push   <= 1;
                        end

                        // Advance scan
                        if (intra_scan_idx + 1 >= NEURONS_PER_GROUP) begin
                            // Done scanning all local connections
                            state <= ST_IDLE;
                        end else begin
                            intra_scan_idx <= intra_scan_idx + 1;
                            wm_rd_addr <= fired_neuron_id * NEURONS_PER_GROUP + intra_scan_idx + 1;
                            state      <= ST_INTRA_READ;
                        end
                    end

                    default: state <= ST_IDLE;
                endcase

                // Reset leak cycle
                if (leak_cycle_done && fifo_empty && state == ST_IDLE)
                    leak_cycle_done <= 0;
            end

            //--- FIFO count management ---
            case ({fifo_push, fifo_pop})
                2'b10: fifo_count <= fifo_count + 1;
                2'b01: fifo_count <= fifo_count - 1;
                default: fifo_count <= fifo_count;  // 00 or 11 (push+pop)
            endcase
        end
    end

    //=========================================================================
    // 7. Output Spike Scan (bitmap → event router)
    //    Scans spike_flag_mem, outputs one spike per cycle when ready
    //=========================================================================
    reg [LOCAL_ID_WIDTH-1:0] scan_idx;
    reg [7:0]                scan_byte;
    reg [2:0]                scan_bit_pos;
    reg                      scan_active;

    always @(posedge clk) begin
        if (!rst_n) begin
            out_spike_valid     <= 0;
            out_spike_neuron_id <= 0;
            scan_idx            <= 0;
            scan_byte           <= 0;
            scan_bit_pos        <= 0;
            scan_active         <= 0;
            sf_clear_pending    <= 0;
            sf_clear_addr       <= 0;
            sf_clear_mask       <= 8'hFF;
        end else begin
            sf_clear_pending <= 0;

            if (out_spike_ready || !out_spike_valid) begin
                out_spike_valid <= 0;

                if (!scan_active) begin
                    scan_byte    <= spike_flag_mem[scan_idx[LOCAL_ID_WIDTH-1:3]];
                    scan_bit_pos <= 0;
                    scan_active  <= 1;
                end else begin
                    if (scan_byte[scan_bit_pos]) begin
                        out_spike_valid     <= 1;
                        out_spike_neuron_id <= {scan_idx[LOCAL_ID_WIDTH-1:3], scan_bit_pos};
                        sf_clear_pending    <= 1;
                        sf_clear_addr       <= scan_idx[LOCAL_ID_WIDTH-1:3];
                        sf_clear_mask       <= ~(8'd1 << scan_bit_pos);
                    end

                    if (scan_bit_pos == 3'd7) begin
                        scan_active <= 0;
                        if (scan_idx + 8 >= NEURONS_PER_GROUP)
                            scan_idx <= 0;
                        else
                            scan_idx <= scan_idx + 8;
                    end else begin
                        scan_bit_pos <= scan_bit_pos + 1;
                    end
                end
            end
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
    end

endmodule
