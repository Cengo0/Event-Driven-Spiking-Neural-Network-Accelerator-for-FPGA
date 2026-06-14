//-----------------------------------------------------------------------------
// Title       : SpikeMold EventConv State Update
// Description : Tiny near-memory state RMW block for EventConv C2.
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps

module spike_conv_state_update #(
    parameter STATE_COUNT = 16,
    parameter DEST_ID_WIDTH = 16,
    parameter STATE_WIDTH = 16,
    parameter WEIGHT_WIDTH = 8
)(
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         enable,
    input  wire                         clear,

    input  wire                         s_axis_update_tvalid,
    input  wire [31:0]                  s_axis_update_tdata,
    input  wire signed [WEIGHT_WIDTH-1:0] update_weight,
    output wire                         s_axis_update_tready,

    input  wire                         s_axis_reset_tvalid,
    input  wire [DEST_ID_WIDTH-1:0]     s_axis_reset_tdest,
    output wire                         s_axis_reset_tready,

    output wire [(STATE_COUNT*STATE_WIDTH)-1:0] state_flat,
    output wire [(STATE_COUNT*DEST_ID_WIDTH)-1:0] active_id_flat,
    output reg  [STATE_COUNT-1:0]       active_mask,
    output reg  [31:0]                  active_neuron_count,
    output reg  [31:0]                  state_read_count,
    output reg  [31:0]                  state_write_count,
    output reg  [31:0]                  update_count,
    output reg  [31:0]                  commit_reset_count,
    output reg  [31:0]                  invalid_dest_count,
    output reg signed [31:0]            state_checksum
);

    localparam STATE_INDEX_WIDTH = (STATE_COUNT <= 2) ? 1 : $clog2(STATE_COUNT);

    reg signed [STATE_WIDTH-1:0] state_mem [0:STATE_COUNT-1];
    reg [DEST_ID_WIDTH-1:0] active_ids [0:STATE_COUNT-1];
    wire [DEST_ID_WIDTH-1:0] update_dest_id = s_axis_update_tdata[31:16];
    wire dest_valid = (update_dest_id < STATE_COUNT);
    wire [STATE_INDEX_WIDTH-1:0] update_index =
        update_dest_id[STATE_INDEX_WIDTH-1:0];
    wire [STATE_INDEX_WIDTH-1:0] active_insert_index =
        active_neuron_count[STATE_INDEX_WIDTH-1:0];
    wire reset_dest_valid = (s_axis_reset_tdest < STATE_COUNT);
    wire [STATE_INDEX_WIDTH-1:0] reset_index =
        s_axis_reset_tdest[STATE_INDEX_WIDTH-1:0];
    wire update_fire = enable && s_axis_update_tvalid && s_axis_update_tready;
    wire reset_fire = enable && s_axis_reset_tvalid && s_axis_reset_tready;
    wire signed [STATE_WIDTH-1:0] extended_weight =
        {{(STATE_WIDTH-WEIGHT_WIDTH){update_weight[WEIGHT_WIDTH-1]}}, update_weight};
    reg reset_id_found;
    reg [STATE_INDEX_WIDTH-1:0] reset_list_index;

    integer i;
    integer search_i;
    integer compact_i;
    genvar gi;

    assign s_axis_update_tready = enable && !s_axis_reset_tvalid;
    assign s_axis_reset_tready = enable;

    always @(*) begin
        reset_id_found = 1'b0;
        reset_list_index = {STATE_INDEX_WIDTH{1'b0}};
        for (search_i = 0; search_i < STATE_COUNT; search_i = search_i + 1) begin
            if (!reset_id_found &&
                (search_i < active_neuron_count) &&
                (active_ids[search_i] == s_axis_reset_tdest)) begin
                reset_id_found = 1'b1;
                reset_list_index = search_i[STATE_INDEX_WIDTH-1:0];
            end
        end
    end

    generate
        for (gi = 0; gi < STATE_COUNT; gi = gi + 1) begin : gen_state_flat
            assign state_flat[gi*STATE_WIDTH +: STATE_WIDTH] = state_mem[gi];
            assign active_id_flat[gi*DEST_ID_WIDTH +: DEST_ID_WIDTH] = active_ids[gi];
        end
    endgenerate

    always @(posedge clk) begin
        if (!rst_n || clear) begin
            for (i = 0; i < STATE_COUNT; i = i + 1) begin
                state_mem[i] <= {STATE_WIDTH{1'b0}};
                active_ids[i] <= {DEST_ID_WIDTH{1'b0}};
            end
            active_mask <= {STATE_COUNT{1'b0}};
            active_neuron_count <= 32'd0;
            state_read_count <= 32'd0;
            state_write_count <= 32'd0;
            update_count <= 32'd0;
            commit_reset_count <= 32'd0;
            invalid_dest_count <= 32'd0;
            state_checksum <= 32'sd0;
        end else if (reset_fire) begin
            if (reset_dest_valid) begin
                state_checksum <= state_checksum - state_mem[reset_index];
                state_mem[reset_index] <= {STATE_WIDTH{1'b0}};
                state_write_count <= state_write_count + 32'd1;
                commit_reset_count <= commit_reset_count + 32'd1;
                if (active_mask[reset_index]) begin
                    active_mask[reset_index] <= 1'b0;
                    if (active_neuron_count > 32'd0) begin
                        active_neuron_count <= active_neuron_count - 32'd1;
                    end
                    if (reset_id_found) begin
                        for (compact_i = 0; compact_i < STATE_COUNT - 1; compact_i = compact_i + 1) begin
                            if (compact_i >= reset_list_index) begin
                                active_ids[compact_i] <= active_ids[compact_i + 1];
                            end
                        end
                        active_ids[STATE_COUNT-1] <= {DEST_ID_WIDTH{1'b0}};
                    end
                end
            end else begin
                invalid_dest_count <= invalid_dest_count + 32'd1;
            end
        end else if (update_fire) begin
            if (dest_valid) begin
                state_mem[update_index] <= state_mem[update_index] + extended_weight;
                state_read_count <= state_read_count + 32'd1;
                state_write_count <= state_write_count + 32'd1;
                update_count <= update_count + 32'd1;
                state_checksum <= state_checksum + extended_weight;
                if (!active_mask[update_index]) begin
                    active_mask[update_index] <= 1'b1;
                    active_ids[active_insert_index] <= update_dest_id;
                    active_neuron_count <= active_neuron_count + 32'd1;
                end
            end else begin
                invalid_dest_count <= invalid_dest_count + 32'd1;
            end
        end
    end

endmodule
