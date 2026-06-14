//-----------------------------------------------------------------------------
// Title         : Event Router (Next-Gen) - Central Fabric Event Router
// Project       : SpikeMold (HW) + SpikePress (SW)
// File          : event_router_ng.v
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : Inference-only event routing hub connecting:
//                 1. Core groups (bidirectional spike ports)
//                 2. Synaptic connectivity table (inter-group lookup)
//                 3. Host/external spike ingress
//
// Operation:
//   When a coregroup outputs a spike:
//   1. Arbiter selects one source (round-robin among groups + external)
//   2. Connectivity table lookup iterates fanout_idx for inter-group routes
//   3. Router delivers events to destination core groups
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps
`include "spikemold_params.vh"

module event_router_ng #(
    parameter NUM_GROUPS        = `SNN_NUM_GROUPS,
    parameter NEURONS_PER_GROUP = `SNN_NEURONS_PER_GROUP,
    parameter WEIGHT_WIDTH      = `SNN_WEIGHT_WIDTH,
    parameter MAX_FANOUT_INTER  = `SNN_MAX_FANOUT_INTER,
    parameter GROUP_ID_WIDTH    = $clog2(NUM_GROUPS),
    parameter LOCAL_ID_WIDTH    = $clog2(NEURONS_PER_GROUP),
    parameter GLOBAL_ID_WIDTH   = GROUP_ID_WIDTH + LOCAL_ID_WIDTH,
    parameter FANOUT_IDX_WIDTH  = $clog2(MAX_FANOUT_INTER)
)(
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         enable,

    // --- SpikeMold Coregroup Spike Output Ports (spikes FROM groups) ---
    input  wire [NUM_GROUPS-1:0]        grp_spike_valid,
    input  wire [NUM_GROUPS*LOCAL_ID_WIDTH-1:0] grp_spike_neuron_id,
    output reg  [NUM_GROUPS-1:0]        grp_spike_ready,

    // --- SpikeMold Coregroup Spike Input Ports (spikes TO groups) ---
    output reg  [NUM_GROUPS-1:0]        grp_in_valid,
    output reg  [NUM_GROUPS*LOCAL_ID_WIDTH-1:0]  grp_in_dest_id,
    output reg  [NUM_GROUPS*WEIGHT_WIDTH-1:0]    grp_in_weight,
    output reg  [NUM_GROUPS-1:0]        grp_in_exc,
    input  wire [NUM_GROUPS-1:0]        grp_in_ready,

    // --- External Spike Input (Sensors / Host PC) ---
    input  wire                         ext_spike_valid,
    input  wire [GLOBAL_ID_WIDTH-1:0]   ext_spike_neuron_id,
    input  wire [WEIGHT_WIDTH-1:0]      ext_spike_weight,
    input  wire                         ext_spike_exc,
    output wire                         ext_spike_ready,

    // --- Connectivity Table Interface ---
    output reg                          ct_lookup_en,
    output reg  [GROUP_ID_WIDTH-1:0]    ct_lookup_src_group,
    output reg  [LOCAL_ID_WIDTH-1:0]    ct_lookup_src_neuron,
    output reg  [FANOUT_IDX_WIDTH-1:0]  ct_lookup_fanout_idx,

    input  wire                         ct_result_valid,
    input  wire [GROUP_ID_WIDTH-1:0]    ct_result_dst_group,
    input  wire [LOCAL_ID_WIDTH-1:0]    ct_result_dst_neuron,
    input  wire [WEIGHT_WIDTH-1:0]      ct_result_weight,
    input  wire                         ct_result_exc_inh,
    input  wire                         ct_result_entry_valid,

    // --- Status ---
    output wire [31:0]                  routed_spike_count,
    output wire                         router_busy,
    output wire [31:0]                  router_ext_invalid_group_count,
    output wire [31:0]                  router_ct_invalid_entry_count,
    output wire [31:0]                  router_ct_invalid_dst_count,
    output wire [31:0]                  router_fanout_scan_count,
    output wire [31:0]                  router_route_miss_count,
    output wire [31:0]                  router_backpressure_stall_count
);

    localparam [3:0]
        ST_IDLE       = 4'd0,
        ST_ARB_SELECT = 4'd1,
        ST_EXT_ROUTE  = 4'd2,
        ST_CT_LOOKUP  = 4'd3,
        ST_CT_WAIT1   = 4'd4,
        ST_CT_WAIT2   = 4'd5,
        ST_CT_DELIVER = 4'd6,
        ST_CT_NEXT    = 4'd7;

    reg [3:0] state;

    reg [GROUP_ID_WIDTH-1:0] rr_priority;
    reg [GROUP_ID_WIDTH-1:0] selected_group;
    reg [LOCAL_ID_WIDTH-1:0] selected_neuron;
    reg                      ext_selected;
    reg [31:0]               spike_counter;
    reg [31:0]               ext_invalid_group_counter;
    reg [31:0]               ct_invalid_entry_counter;
    reg [31:0]               ct_invalid_dst_counter;
    reg [31:0]               fanout_scan_counter;
    reg [31:0]               route_miss_counter;
    reg [31:0]               backpressure_stall_counter;
    reg [GLOBAL_ID_WIDTH-1:0] ext_spike_neuron_id_q;
    reg [WEIGHT_WIDTH-1:0]    ext_spike_weight_q;
    reg                       ext_spike_exc_q;
    reg [FANOUT_IDX_WIDTH-1:0] fanout_idx;

    assign routed_spike_count = spike_counter;
    assign router_busy = (state != ST_IDLE);
    assign ext_spike_ready = (state == ST_IDLE);
    assign router_ext_invalid_group_count = ext_invalid_group_counter;
    assign router_ct_invalid_entry_count = ct_invalid_entry_counter;
    assign router_ct_invalid_dst_count = ct_invalid_dst_counter;
    assign router_fanout_scan_count = fanout_scan_counter;
    assign router_route_miss_count = route_miss_counter;
    assign router_backpressure_stall_count = backpressure_stall_counter;

    integer gi;

    always @(posedge clk) begin
        if (!rst_n) begin
            state           <= ST_IDLE;
            rr_priority     <= 0;
            selected_group  <= 0;
            selected_neuron <= 0;
            ext_selected    <= 0;
            spike_counter   <= 0;
            ext_invalid_group_counter <= 0;
            ct_invalid_entry_counter  <= 0;
            ct_invalid_dst_counter    <= 0;
            fanout_scan_counter       <= 0;
            route_miss_counter        <= 0;
            backpressure_stall_counter <= 0;
            ext_spike_neuron_id_q <= 0;
            ext_spike_weight_q    <= 0;
            ext_spike_exc_q       <= 0;
            fanout_idx      <= 0;
            ct_lookup_en    <= 0;

            grp_spike_ready <= {NUM_GROUPS{1'b0}};
            grp_in_valid    <= {NUM_GROUPS{1'b0}};
            grp_in_dest_id  <= {(NUM_GROUPS*LOCAL_ID_WIDTH){1'b0}};
            grp_in_weight   <= {(NUM_GROUPS*WEIGHT_WIDTH){1'b0}};
            grp_in_exc      <= {NUM_GROUPS{1'b0}};

        end else begin
            grp_spike_ready <= {NUM_GROUPS{1'b0}};
            grp_in_valid    <= {NUM_GROUPS{1'b0}};
            ct_lookup_en    <= 0;

            if (enable || state != ST_IDLE) begin
                case (state)
                    ST_IDLE: begin
                        if (ext_spike_valid) begin
                            ext_spike_neuron_id_q <= ext_spike_neuron_id;
                            ext_spike_weight_q    <= ext_spike_weight;
                            ext_spike_exc_q       <= ext_spike_exc;
                            ext_selected          <= 1;
                            state                 <= ST_EXT_ROUTE;
                        end else begin
                            state <= ST_ARB_SELECT;
                        end
                    end

                    ST_ARB_SELECT: begin
                        ext_selected <= 0;
                        begin : arb_scan
                            reg found;
                            reg [GROUP_ID_WIDTH-1:0] idx;
                            reg [GROUP_ID_WIDTH-1:0] found_idx;
                            found = 0;
                            found_idx = 0;
                            for (gi = 0; gi < NUM_GROUPS; gi = gi + 1) begin
                                idx = (rr_priority + gi[GROUP_ID_WIDTH-1:0]) % NUM_GROUPS;
                                if (!found && grp_spike_valid[idx]) begin
                                    selected_group <= idx;
                                    selected_neuron <= grp_spike_neuron_id[idx*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH];
                                    grp_spike_ready[idx] <= 1;
                                    found = 1;
                                    found_idx = idx;
                                end
                            end
                            if (found) begin
                                rr_priority <= (found_idx + 1) % NUM_GROUPS;
                                fanout_idx <= 0;
                                state <= ST_CT_LOOKUP;
                            end else begin
                                state <= ST_IDLE;
                            end
                        end
                    end

                    ST_EXT_ROUTE: begin
                        begin : ext_route_body
                            reg [GROUP_ID_WIDTH-1:0] tgt_grp;
                            reg [LOCAL_ID_WIDTH-1:0] tgt_neuron;
                            tgt_grp = ext_spike_neuron_id_q[GLOBAL_ID_WIDTH-1:LOCAL_ID_WIDTH];
                            tgt_neuron = ext_spike_neuron_id_q[LOCAL_ID_WIDTH-1:0];

                            if (tgt_grp < NUM_GROUPS && grp_in_ready[tgt_grp]) begin
                                grp_in_valid[tgt_grp] <= 1;
                                grp_in_dest_id[tgt_grp*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH] <= tgt_neuron;
                                grp_in_weight[tgt_grp*WEIGHT_WIDTH +: WEIGHT_WIDTH] <= ext_spike_weight_q;
                                grp_in_exc[tgt_grp] <= ext_spike_exc_q;
                                spike_counter <= spike_counter + 1;
                                state <= ST_IDLE;
                            end else if (tgt_grp >= NUM_GROUPS) begin
                                ext_invalid_group_counter <= ext_invalid_group_counter + 1'b1;
                                state <= ST_IDLE;
                            end else begin
                                backpressure_stall_counter <= backpressure_stall_counter + 1'b1;
                            end
                        end
                    end

                    ST_CT_LOOKUP: begin
                        ct_lookup_en <= 1;
                        ct_lookup_src_group <= selected_group;
                        ct_lookup_src_neuron <= selected_neuron;
                        ct_lookup_fanout_idx <= fanout_idx;
                        fanout_scan_counter <= fanout_scan_counter + 1'b1;
                        state <= ST_CT_WAIT1;
                    end

                    ST_CT_WAIT1: begin
                        state <= ST_CT_WAIT2;
                    end

                    ST_CT_WAIT2: begin
                        state <= ST_CT_DELIVER;
                    end

                    ST_CT_DELIVER: begin
                        if (ct_result_valid && ct_result_entry_valid) begin
                            if (ct_result_dst_group >= NUM_GROUPS) begin
                                ct_invalid_dst_counter <= ct_invalid_dst_counter + 1'b1;
                                state <= ST_CT_NEXT;
                            end else if (grp_in_ready[ct_result_dst_group]) begin
                                grp_in_valid[ct_result_dst_group] <= 1;
                                grp_in_dest_id[ct_result_dst_group*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH]
                                    <= ct_result_dst_neuron;
                                grp_in_weight[ct_result_dst_group*WEIGHT_WIDTH +: WEIGHT_WIDTH]
                                    <= ct_result_weight;
                                grp_in_exc[ct_result_dst_group] <= ct_result_exc_inh;
                                spike_counter <= spike_counter + 1;
                                state <= ST_CT_NEXT;
                            end else begin
                                backpressure_stall_counter <= backpressure_stall_counter + 1'b1;
                            end
                        end else begin
                            ct_invalid_entry_counter <= ct_invalid_entry_counter + 1'b1;
                            if (fanout_idx == {FANOUT_IDX_WIDTH{1'b0}})
                                route_miss_counter <= route_miss_counter + 1'b1;
                            state <= ST_IDLE;
                        end
                    end

                    ST_CT_NEXT: begin
                        if (fanout_idx + 1 >= MAX_FANOUT_INTER) begin
                            state <= ST_IDLE;
                        end else begin
                            fanout_idx <= fanout_idx + 1;
                            state <= ST_CT_LOOKUP;
                        end
                    end

                    default: state <= ST_IDLE;
                endcase
            end
        end
    end

endmodule
