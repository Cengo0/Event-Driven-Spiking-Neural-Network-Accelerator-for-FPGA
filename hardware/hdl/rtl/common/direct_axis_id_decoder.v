`timescale 1ns / 1ps

module direct_axis_id_decoder #(
    parameter HLS_NEURON_ID_WIDTH = 13,
    parameter GLOBAL_ID_WIDTH = 11,
    parameter HLS_DIRECT_TILE_COMPAT = 1,
    parameter STRICT_PHYSICAL_ID_INGRESS = 0
)(
    input  wire [HLS_NEURON_ID_WIDTH-1:0] neuron_id,
    input  wire                           tvalid,
    input  wire                           tuser,
    output wire [GLOBAL_ID_WIDTH-1:0]     dest_id,
    output wire                           explicit_id_accepted,
    output wire                           explicit_invalid,
    output wire                           ingress_invalid,
    output wire                           compat_id_in_range,
    output wire                           flagged_compat_id,
    output wire                           board_visible_compat_id,
    output wire                           compat_id_accepted,
    output wire                           direct_id_accepted
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

    assign explicit_id_accepted = tvalid && tuser && physical_id_in_range;
    assign explicit_invalid = tvalid && tuser && !physical_id_in_range;

    assign compat_id_in_range = tvalid && !tuser && physical_id_in_range;
    assign board_visible_compat_id =
        (STRICT_PHYSICAL_ID_INGRESS == 0) && (HLS_DIRECT_TILE_COMPAT != 0) &&
        tvalid && !tuser && board_visible_candidate;
    assign flagged_compat_id =
        (STRICT_PHYSICAL_ID_INGRESS == 0) && (HLS_DIRECT_TILE_COMPAT != 0) &&
        tvalid && !tuser && flagged_candidate;
    assign compat_id_accepted = board_visible_compat_id || flagged_compat_id;
    assign direct_id_accepted = explicit_id_accepted || compat_id_accepted;
    assign ingress_invalid = tvalid && !direct_id_accepted &&
        ((STRICT_PHYSICAL_ID_INGRESS != 0) || explicit_invalid || (!tuser && !physical_id_in_range));

    assign dest_id = flagged_compat_id ? (neuron_id[GLOBAL_ID_WIDTH-1:0] - DIRECT_FLAG_BASE_DEST)
                                       : neuron_id[GLOBAL_ID_WIDTH-1:0];

endmodule
