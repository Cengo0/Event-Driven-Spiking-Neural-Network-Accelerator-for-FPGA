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

    output wire [(STATE_COUNT*STATE_WIDTH)-1:0] state_flat,
    output reg  [STATE_COUNT-1:0]       active_mask,
    output reg  [31:0]                  active_neuron_count,
    output reg  [31:0]                  state_read_count,
    output reg  [31:0]                  state_write_count,
    output reg  [31:0]                  update_count,
    output reg  [31:0]                  invalid_dest_count,
    output reg signed [31:0]            state_checksum
);

    reg signed [STATE_WIDTH-1:0] state_mem [0:STATE_COUNT-1];
    wire [DEST_ID_WIDTH-1:0] update_dest_id = s_axis_update_tdata[31:16];
    wire dest_valid = (update_dest_id < STATE_COUNT);
    wire update_fire = enable && s_axis_update_tvalid && s_axis_update_tready;
    wire signed [STATE_WIDTH-1:0] extended_weight =
        {{(STATE_WIDTH-WEIGHT_WIDTH){update_weight[WEIGHT_WIDTH-1]}}, update_weight};

    integer i;
    genvar gi;

    assign s_axis_update_tready = enable;

    generate
        for (gi = 0; gi < STATE_COUNT; gi = gi + 1) begin : gen_state_flat
            assign state_flat[gi*STATE_WIDTH +: STATE_WIDTH] = state_mem[gi];
        end
    endgenerate

    always @(posedge clk) begin
        if (!rst_n || clear) begin
            for (i = 0; i < STATE_COUNT; i = i + 1) begin
                state_mem[i] <= {STATE_WIDTH{1'b0}};
            end
            active_mask <= {STATE_COUNT{1'b0}};
            active_neuron_count <= 32'd0;
            state_read_count <= 32'd0;
            state_write_count <= 32'd0;
            update_count <= 32'd0;
            invalid_dest_count <= 32'd0;
            state_checksum <= 32'sd0;
        end else if (update_fire) begin
            if (dest_valid) begin
                state_mem[update_dest_id] <= state_mem[update_dest_id] + extended_weight;
                state_read_count <= state_read_count + 32'd1;
                state_write_count <= state_write_count + 32'd1;
                update_count <= update_count + 32'd1;
                state_checksum <= state_checksum + extended_weight;
                if (!active_mask[update_dest_id]) begin
                    active_mask[update_dest_id] <= 1'b1;
                    active_neuron_count <= active_neuron_count + 32'd1;
                end
            end else begin
                invalid_dest_count <= invalid_dest_count + 32'd1;
            end
        end
    end

endmodule
