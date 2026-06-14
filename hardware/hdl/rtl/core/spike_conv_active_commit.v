//-----------------------------------------------------------------------------
// Title       : SpikeMold EventConv Active Commit
// Description : Active-list commit/readout for EventConv C3.
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps

module spike_conv_active_commit #(
    parameter STATE_COUNT = 16,
    parameter DEST_ID_WIDTH = 16,
    parameter STATE_WIDTH = 16
)(
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         enable,
    input  wire                         clear,

    input  wire                         commit_start,
    input  wire signed [STATE_WIDTH-1:0] commit_threshold,
    input  wire [31:0]                  active_neuron_count,
    input  wire [(STATE_COUNT*DEST_ID_WIDTH)-1:0] active_id_flat,
    input  wire [(STATE_COUNT*STATE_WIDTH)-1:0] state_flat,

    output reg                          commit_busy,
    output reg                          commit_done,
    output reg                          m_axis_commit_tvalid,
    output reg  [31:0]                  m_axis_commit_tdata,
    input  wire                         m_axis_commit_tready,
    output reg                          m_axis_reset_tvalid,
    output reg  [DEST_ID_WIDTH-1:0]     m_axis_reset_tdest,
    input  wire                         m_axis_reset_tready,

    output reg  [31:0]                  active_commit_read_count,
    output reg  [31:0]                  commit_emit_count,
    output reg  [31:0]                  full_scan_count,
    output reg signed [31:0]            readout_checksum
);

    localparam STATE_IDLE = 2'd0;
    localparam STATE_CHECK = 2'd1;
    localparam STATE_EMIT = 2'd2;

    reg [1:0] state;
    reg [31:0] active_index;
    reg [31:0] active_count_latched;
    reg [DEST_ID_WIDTH-1:0] held_dest_id;
    reg signed [STATE_WIDTH-1:0] held_state_value;

    wire active_index_in_range =
        (active_index < active_count_latched) && (active_index < STATE_COUNT);
    wire [DEST_ID_WIDTH-1:0] current_dest_id =
        active_id_flat[active_index*DEST_ID_WIDTH +: DEST_ID_WIDTH];
    wire current_dest_valid = (current_dest_id < STATE_COUNT);
    wire signed [STATE_WIDTH-1:0] current_state_value =
        state_flat[current_dest_id*STATE_WIDTH +: STATE_WIDTH];
    wire current_should_emit =
        current_dest_valid && (current_state_value >= commit_threshold);
    wire commit_output_fire =
        m_axis_commit_tvalid && m_axis_commit_tready &&
        m_axis_reset_tvalid && m_axis_reset_tready;

    always @(posedge clk) begin
        if (!rst_n || clear) begin
            state <= STATE_IDLE;
            active_index <= 32'd0;
            active_count_latched <= 32'd0;
            held_dest_id <= {DEST_ID_WIDTH{1'b0}};
            held_state_value <= {STATE_WIDTH{1'b0}};
            commit_busy <= 1'b0;
            commit_done <= 1'b0;
            m_axis_commit_tvalid <= 1'b0;
            m_axis_commit_tdata <= 32'd0;
            m_axis_reset_tvalid <= 1'b0;
            m_axis_reset_tdest <= {DEST_ID_WIDTH{1'b0}};
            active_commit_read_count <= 32'd0;
            commit_emit_count <= 32'd0;
            full_scan_count <= 32'd0;
            readout_checksum <= 32'sd0;
        end else if (!enable) begin
            state <= STATE_IDLE;
            active_index <= 32'd0;
            commit_busy <= 1'b0;
            commit_done <= 1'b0;
            m_axis_commit_tvalid <= 1'b0;
            m_axis_reset_tvalid <= 1'b0;
        end else begin
            commit_done <= 1'b0;

            case (state)
                STATE_IDLE: begin
                    m_axis_commit_tvalid <= 1'b0;
                    m_axis_reset_tvalid <= 1'b0;
                    if (commit_start) begin
                        active_index <= 32'd0;
                        active_count_latched <= active_neuron_count;
                        if (active_neuron_count == 32'd0) begin
                            commit_busy <= 1'b0;
                            commit_done <= 1'b1;
                        end else begin
                            commit_busy <= 1'b1;
                            state <= STATE_CHECK;
                        end
                    end
                end

                STATE_CHECK: begin
                    if (!active_index_in_range) begin
                        commit_busy <= 1'b0;
                        commit_done <= 1'b1;
                        state <= STATE_IDLE;
                    end else begin
                        active_commit_read_count <= active_commit_read_count + 32'd1;
                        if (current_should_emit) begin
                            held_dest_id <= current_dest_id;
                            held_state_value <= current_state_value;
                            m_axis_commit_tdata <= {
                                current_dest_id[15:0],
                                current_state_value[15:0]
                            };
                            m_axis_commit_tvalid <= 1'b1;
                            m_axis_reset_tdest <= current_dest_id;
                            m_axis_reset_tvalid <= 1'b1;
                            state <= STATE_EMIT;
                        end else begin
                            active_index <= active_index + 32'd1;
                        end
                    end
                end

                STATE_EMIT: begin
                    if (commit_output_fire) begin
                        m_axis_commit_tvalid <= 1'b0;
                        m_axis_reset_tvalid <= 1'b0;
                        commit_emit_count <= commit_emit_count + 32'd1;
                        readout_checksum <= readout_checksum + held_state_value;
                        active_index <= active_index + 32'd1;
                        state <= STATE_CHECK;
                    end
                end

                default: begin
                    state <= STATE_IDLE;
                    commit_busy <= 1'b0;
                    m_axis_commit_tvalid <= 1'b0;
                    m_axis_reset_tvalid <= 1'b0;
                end
            endcase
        end
    end

endmodule
