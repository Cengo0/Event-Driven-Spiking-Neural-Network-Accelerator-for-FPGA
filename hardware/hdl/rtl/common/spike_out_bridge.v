`timescale 1ns / 1ps

module spike_out_bridge #(
    parameter HLS_NEURON_ID_WIDTH = 13,
    parameter HLS_MAX_NEURONS = 2048,
    parameter NEURON_ID_WIDTH = 11,
    parameter WEIGHT_WIDTH = 8,
    parameter FIFO_DEPTH = 256,
    parameter INPUT_VALID_IS_PULSE = 0,
    parameter OUTPUT_AXIS_ENABLE = 0
)(
    input  wire                          clk,
    input  wire                          rst_n,
    input  wire                          enable,
    input  wire                          clear,
    input  wire                          neuron_spike_valid,
    input  wire [NEURON_ID_WIDTH-1:0]    neuron_spike_id,
    input  wire                          spike_out_ready_token,
    output wire                          neuron_spike_event,
    output wire                          spike_out_valid,
    output wire [HLS_NEURON_ID_WIDTH-1:0] spike_out_neuron_id,
    output wire [WEIGHT_WIDTH-1:0]       spike_out_weight,
    output wire [31:0]                   m_axis_tdata,
    output wire [3:0]                    m_axis_tkeep,
    output wire [3:0]                    m_axis_tstrb,
    output wire                          m_axis_tvalid,
    output wire                          m_axis_tlast,
    input  wire                          m_axis_tready,
    output wire                          m_axis_tid,
    output wire                          m_axis_tdest,
    output wire                          m_axis_tuser,
    output reg                           fifo_overflow,
    output wire [31:0]                   fifo_level,
    output reg  [31:0]                   output_event_count,
    output reg  [31:0]                   output_emit_count,
    output reg  [31:0]                   output_drop_count
);

    localparam FIFO_PTR_WIDTH = $clog2(FIFO_DEPTH);
    localparam [HLS_NEURON_ID_WIDTH-1:0] HLS_MAX_NEURONS_VALUE = HLS_MAX_NEURONS;
    localparam [WEIGHT_WIDTH-1:0] UNIT_WEIGHT = {{(WEIGHT_WIDTH-1){1'b0}}, 1'b1};

    reg [HLS_NEURON_ID_WIDTH-1:0] fifo_mem [0:FIFO_DEPTH-1];
    reg [FIFO_PTR_WIDTH-1:0] fifo_wr_ptr;
    reg [FIFO_PTR_WIDTH-1:0] fifo_rd_ptr;
    reg [FIFO_PTR_WIDTH:0] fifo_count;
    reg prev_ready_token;
    reg prev_spike_valid;
    reg [NEURON_ID_WIDTH-1:0] prev_spike_id;

    wire [HLS_NEURON_ID_WIDTH-1:0] spike_id_hls =
        {{(HLS_NEURON_ID_WIDTH-NEURON_ID_WIDTH){1'b0}}, neuron_spike_id};
    wire spike_id_in_range = (spike_id_hls < HLS_MAX_NEURONS_VALUE);
    wire payload_changed = (neuron_spike_id != prev_spike_id);
    wire edge_event = neuron_spike_valid && (!prev_spike_valid || payload_changed);
    wire pulse_event = neuron_spike_valid;
    wire event_candidate = (INPUT_VALID_IS_PULSE != 0) ? pulse_event : edge_event;
    wire fifo_empty = (fifo_count == 0);
    wire fifo_full = (fifo_count == FIFO_DEPTH);
    wire scalar_pop = (OUTPUT_AXIS_ENABLE == 0) &&
                      (spike_out_ready_token ^ prev_ready_token) &&
                      !fifo_empty;
    wire axis_pop = (OUTPUT_AXIS_ENABLE != 0) && m_axis_tvalid && m_axis_tready;
    wire pop_event = scalar_pop || axis_pop;
    wire push_event = event_candidate && spike_id_in_range && !fifo_full;
    wire drop_event = event_candidate && (!spike_id_in_range || fifo_full);

    assign neuron_spike_event = enable && event_candidate;
    assign spike_out_valid = (OUTPUT_AXIS_ENABLE == 0) && !fifo_empty;
    assign spike_out_neuron_id = fifo_empty ? {HLS_NEURON_ID_WIDTH{1'b0}} : fifo_mem[fifo_rd_ptr];
    assign spike_out_weight = UNIT_WEIGHT;
    assign fifo_level = { {(32-(FIFO_PTR_WIDTH+1)){1'b0}}, fifo_count };

    assign m_axis_tvalid = (OUTPUT_AXIS_ENABLE != 0) && !fifo_empty;
    assign m_axis_tdata = {{(32-HLS_NEURON_ID_WIDTH-WEIGHT_WIDTH){1'b0}},
                           UNIT_WEIGHT,
                           spike_out_neuron_id};
    assign m_axis_tkeep = 4'hF;
    assign m_axis_tstrb = 4'hF;
    assign m_axis_tlast = 1'b0;
    assign m_axis_tid = 1'b0;
    assign m_axis_tdest = 1'b0;
    assign m_axis_tuser = 1'b0;

    always @(posedge clk) begin
        if (!rst_n || clear || !enable) begin
            fifo_wr_ptr <= {FIFO_PTR_WIDTH{1'b0}};
            fifo_rd_ptr <= {FIFO_PTR_WIDTH{1'b0}};
            fifo_count <= {(FIFO_PTR_WIDTH+1){1'b0}};
            fifo_overflow <= 1'b0;
            output_event_count <= 32'd0;
            output_emit_count <= 32'd0;
            output_drop_count <= 32'd0;
            prev_ready_token <= 1'b0;
            prev_spike_valid <= 1'b0;
            prev_spike_id <= {NEURON_ID_WIDTH{1'b0}};
        end else begin
            prev_ready_token <= spike_out_ready_token;
            prev_spike_valid <= neuron_spike_valid;
            if (neuron_spike_valid) begin
                prev_spike_id <= neuron_spike_id;
            end

            if (event_candidate) begin
                output_event_count <= output_event_count + 32'd1;
                if (drop_event) begin
                    output_drop_count <= output_drop_count + 32'd1;
                end
            end

            if (push_event) begin
                fifo_mem[fifo_wr_ptr] <= spike_id_hls;
                fifo_wr_ptr <= (fifo_wr_ptr == FIFO_DEPTH - 1) ?
                    {FIFO_PTR_WIDTH{1'b0}} : (fifo_wr_ptr + 1'b1);
            end

            if (drop_event && fifo_full) begin
                fifo_overflow <= 1'b1;
            end

            if (pop_event) begin
                fifo_rd_ptr <= (fifo_rd_ptr == FIFO_DEPTH - 1) ?
                    {FIFO_PTR_WIDTH{1'b0}} : (fifo_rd_ptr + 1'b1);
                output_emit_count <= output_emit_count + 32'd1;
            end

            case ({push_event, pop_event})
                2'b10: fifo_count <= fifo_count + 1'b1;
                2'b01: fifo_count <= fifo_count - 1'b1;
                default: fifo_count <= fifo_count;
            endcase
        end
    end

endmodule
