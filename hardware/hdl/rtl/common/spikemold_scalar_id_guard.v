`timescale 1ns / 1ps

module spikemold_scalar_id_guard #(
    parameter HLS_NEURON_ID_WIDTH = 13,
    parameter GLOBAL_ID_WIDTH = 11,
    parameter HLS_DIRECT_TILE_COMPAT = 1,
    parameter STRICT_PHYSICAL_ID_INGRESS = 0
)(
    input  wire [HLS_NEURON_ID_WIDTH-1:0] neuron_id,
    input  wire                           tvalid,
    output wire [GLOBAL_ID_WIDTH-1:0]     global_id,
    output wire [GLOBAL_ID_WIDTH-1:0]     direct_dest_id,
    output wire                           id_in_range,
    output wire                           invalid,
    output wire                           flagged_compat_id,
    output wire                           board_visible_compat_id,
    output wire                           direct_id_accepted,
    output wire                           routed_id_accepted
);

    localparam [HLS_NEURON_ID_WIDTH-1:0] PHYSICAL_COUNT_VALUE = (1 << GLOBAL_ID_WIDTH);
    localparam [HLS_NEURON_ID_WIDTH-1:0] BOARD_VISIBLE_DIRECT_COUNT_VALUE =
        (1 << GLOBAL_ID_WIDTH) >> 2;
    localparam [HLS_NEURON_ID_WIDTH-1:0] DIRECT_FLAG_BASE_VALUE =
        (1 << GLOBAL_ID_WIDTH) >> 1;
    localparam [GLOBAL_ID_WIDTH-1:0] DIRECT_FLAG_BASE_DEST =
        ((1 << GLOBAL_ID_WIDTH) >> 1);

    wire physical_id_in_range = (neuron_id < PHYSICAL_COUNT_VALUE);
    wire board_visible_candidate = (neuron_id < BOARD_VISIBLE_DIRECT_COUNT_VALUE);
    wire flagged_candidate =
        (neuron_id >= DIRECT_FLAG_BASE_VALUE) &&
        (neuron_id < PHYSICAL_COUNT_VALUE);

    assign id_in_range = (STRICT_PHYSICAL_ID_INGRESS == 0) && tvalid && physical_id_in_range;
    assign invalid = tvalid && ((STRICT_PHYSICAL_ID_INGRESS != 0) || !physical_id_in_range);
    assign board_visible_compat_id =
        (STRICT_PHYSICAL_ID_INGRESS == 0) && (HLS_DIRECT_TILE_COMPAT != 0) &&
        tvalid && board_visible_candidate;
    assign flagged_compat_id =
        (STRICT_PHYSICAL_ID_INGRESS == 0) && (HLS_DIRECT_TILE_COMPAT != 0) &&
        tvalid && flagged_candidate;
    assign direct_id_accepted = board_visible_compat_id || flagged_compat_id;
    assign routed_id_accepted =
        (STRICT_PHYSICAL_ID_INGRESS == 0) && tvalid && physical_id_in_range && !direct_id_accepted;

    assign global_id = neuron_id[GLOBAL_ID_WIDTH-1:0];
    assign direct_dest_id = flagged_compat_id ? (neuron_id[GLOBAL_ID_WIDTH-1:0] - DIRECT_FLAG_BASE_DEST)
                                              : neuron_id[GLOBAL_ID_WIDTH-1:0];

endmodule
