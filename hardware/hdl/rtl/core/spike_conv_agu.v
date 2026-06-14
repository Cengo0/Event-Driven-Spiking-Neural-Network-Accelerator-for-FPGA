//-----------------------------------------------------------------------------
// Title       : SpikeMold EventConv AGU
// Description : Shared-kernel, event-triggered convolution address generator.
//
// Output packet:
//   m_axis_spike_tdata[31:16] = destination neuron id
//   m_axis_spike_tdata[15:0]  = flattened kernel weight index
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps
`include "spikemold_params.vh"

module spike_conv_agu #(
    parameter KERNEL_SIZE = 3,
    parameter INPUT_WIDTH = 32,
    parameter INPUT_HEIGHT = 32,
    parameter NUM_CHANNELS = 3,
    parameter OUTPUT_CHANNELS = 1,
    parameter STRIDE = 1,
    parameter PADDING = 0,
    parameter KERNEL_WEIGHT_BITS = 8
)(
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         enable,

    input  wire                         s_axis_spike_tvalid,
    input  wire [31:0]                  s_axis_spike_tdata,
    output wire                         s_axis_spike_tready,

    output wire                         m_axis_spike_tvalid,
    output wire [31:0]                  m_axis_spike_tdata,
    input  wire                         m_axis_spike_tready,

    output reg  [KERNEL_WEIGHT_BITS-1:0] kernel_weight_out,
    input  wire [(OUTPUT_CHANNELS*NUM_CHANNELS*KERNEL_SIZE*KERNEL_SIZE*KERNEL_WEIGHT_BITS)-1:0]
                                        kernel_weight_flat,

    output wire [31:0]                  conv_spikes_processed,
    output wire [31:0]                  conv_updates_generated,
    output wire [31:0]                  conv_address_errors
);

    localparam OUTPUT_WIDTH = ((INPUT_WIDTH + (2 * PADDING) - KERNEL_SIZE) / STRIDE) + 1;
    localparam OUTPUT_HEIGHT = ((INPUT_HEIGHT + (2 * PADDING) - KERNEL_SIZE) / STRIDE) + 1;
    localparam STATE_IDLE = 1'b0;
    localparam STATE_SCAN = 1'b1;

    reg state;
    reg [7:0] spike_x;
    reg [7:0] spike_y;
    reg [7:0] spike_channel;
    reg [7:0] out_channel_idx;
    reg [7:0] kernel_row_idx;
    reg [7:0] kernel_col_idx;
    reg [31:0] input_spike_count;
    reg [31:0] generated_update_count;
    reg [31:0] address_error_count;
    reg emit_valid;
    reg scan_complete;
    reg [15:0] emit_dest_id;
    reg [15:0] emit_weight_idx;

    integer shifted_x;
    integer shifted_y;
    integer out_x;
    integer out_y;
    integer dest_calc;
    integer weight_idx_calc;

    reg coord_valid;
    reg channel_valid;
    reg weight_nonzero;
    reg candidate_valid;
    reg [15:0] candidate_dest_id;
    reg [15:0] candidate_weight_idx;
    reg [KERNEL_WEIGHT_BITS-1:0] candidate_kernel_weight;
    integer weight_bit_base;

    wire scan_last =
        (out_channel_idx == OUTPUT_CHANNELS - 1) &&
        (kernel_row_idx == KERNEL_SIZE - 1) &&
        (kernel_col_idx == KERNEL_SIZE - 1);
    wire scan_can_advance = (state == STATE_SCAN) && !scan_complete &&
                             (!emit_valid || m_axis_spike_tready);
    wire input_fire = (state == STATE_IDLE) && enable && s_axis_spike_tvalid;
    wire output_fire = emit_valid && m_axis_spike_tready;

    assign s_axis_spike_tready = (state == STATE_IDLE) && enable;
    assign m_axis_spike_tvalid = emit_valid;
    assign m_axis_spike_tdata = {emit_dest_id, emit_weight_idx};
    assign conv_spikes_processed = input_spike_count;
    assign conv_updates_generated = generated_update_count;
    assign conv_address_errors = address_error_count;

    always @(*) begin
        shifted_x = $signed({1'b0, spike_x}) + PADDING - kernel_col_idx;
        shifted_y = $signed({1'b0, spike_y}) + PADDING - kernel_row_idx;
        out_x = 0;
        out_y = 0;
        coord_valid = 1'b0;

        if ((shifted_x >= 0) && (shifted_y >= 0) &&
            ((shifted_x % STRIDE) == 0) && ((shifted_y % STRIDE) == 0)) begin
            out_x = shifted_x / STRIDE;
            out_y = shifted_y / STRIDE;
            coord_valid = (out_x >= 0) && (out_x < OUTPUT_WIDTH) &&
                          (out_y >= 0) && (out_y < OUTPUT_HEIGHT);
        end

        dest_calc = ((out_channel_idx * OUTPUT_HEIGHT + out_y) * OUTPUT_WIDTH) + out_x;
        weight_idx_calc =
            (((out_channel_idx * NUM_CHANNELS + spike_channel) * KERNEL_SIZE + kernel_row_idx) *
             KERNEL_SIZE) + kernel_col_idx;
        weight_bit_base = weight_idx_calc * KERNEL_WEIGHT_BITS;
        candidate_kernel_weight = kernel_weight_flat[weight_bit_base +: KERNEL_WEIGHT_BITS];
        channel_valid = (spike_channel < NUM_CHANNELS);
        weight_nonzero = (candidate_kernel_weight != {KERNEL_WEIGHT_BITS{1'b0}});
        candidate_valid = channel_valid && coord_valid && weight_nonzero;
        candidate_dest_id = dest_calc[15:0];
        candidate_weight_idx = weight_idx_calc[15:0];
    end

    always @(posedge clk) begin
        if (!rst_n) begin
            state <= STATE_IDLE;
            spike_x <= 8'd0;
            spike_y <= 8'd0;
            spike_channel <= 8'd0;
            out_channel_idx <= 8'd0;
            kernel_row_idx <= 8'd0;
            kernel_col_idx <= 8'd0;
            input_spike_count <= 32'd0;
            generated_update_count <= 32'd0;
            address_error_count <= 32'd0;
            emit_valid <= 1'b0;
            scan_complete <= 1'b0;
            emit_dest_id <= 16'd0;
            emit_weight_idx <= 16'd0;
            kernel_weight_out <= {KERNEL_WEIGHT_BITS{1'b0}};
        end else if (!enable) begin
            state <= STATE_IDLE;
            emit_valid <= 1'b0;
            scan_complete <= 1'b0;
        end else begin
            if (output_fire) begin
                generated_update_count <= generated_update_count + 32'd1;
                emit_valid <= 1'b0;
                if (scan_complete) begin
                    scan_complete <= 1'b0;
                    state <= STATE_IDLE;
                end
            end

            if (input_fire) begin
                spike_x <= s_axis_spike_tdata[31:24];
                spike_y <= s_axis_spike_tdata[23:16];
                spike_channel <= s_axis_spike_tdata[15:8];
                out_channel_idx <= 8'd0;
                kernel_row_idx <= 8'd0;
                kernel_col_idx <= 8'd0;
                input_spike_count <= input_spike_count + 32'd1;
                emit_valid <= 1'b0;
                scan_complete <= 1'b0;
                state <= STATE_SCAN;
            end else if (scan_can_advance) begin
                if (candidate_valid) begin
                    emit_valid <= 1'b1;
                    emit_dest_id <= candidate_dest_id;
                    emit_weight_idx <= candidate_weight_idx;
                    kernel_weight_out <= candidate_kernel_weight;
                end else if (!coord_valid || !channel_valid) begin
                    address_error_count <= address_error_count + 32'd1;
                end

                if (scan_last) begin
                    if (candidate_valid) begin
                        scan_complete <= 1'b1;
                    end else begin
                        state <= STATE_IDLE;
                    end
                end else if (kernel_col_idx < KERNEL_SIZE - 1) begin
                    kernel_col_idx <= kernel_col_idx + 8'd1;
                end else if (kernel_row_idx < KERNEL_SIZE - 1) begin
                    kernel_col_idx <= 8'd0;
                    kernel_row_idx <= kernel_row_idx + 8'd1;
                end else begin
                    kernel_col_idx <= 8'd0;
                    kernel_row_idx <= 8'd0;
                    out_channel_idx <= out_channel_idx + 8'd1;
                end
            end
        end
    end

endmodule
