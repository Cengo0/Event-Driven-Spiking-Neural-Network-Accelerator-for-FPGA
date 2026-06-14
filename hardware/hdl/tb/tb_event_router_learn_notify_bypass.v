//=============================================================================
// Testbench: Event Router learning-notify bypass parameter
//=============================================================================

`timescale 1ns / 1ps
`include "snn_params.vh"

module tb_event_router_learn_notify_bypass;

    parameter NUM_GROUPS        = `SNN_NUM_GROUPS;
    parameter NEURONS_PER_GROUP = `SNN_NEURONS_PER_GROUP;
    parameter WEIGHT_WIDTH      = `SNN_WEIGHT_WIDTH;
    parameter MAX_FANOUT_INTER  = `SNN_MAX_FANOUT_INTER;
    parameter GROUP_ID_WIDTH    = `SNN_GROUP_ID_WIDTH;
    parameter LOCAL_ID_WIDTH    = `SNN_LOCAL_ID_WIDTH;
    parameter GLOBAL_ID_WIDTH   = `SNN_GLOBAL_ID_WIDTH;
    parameter FANOUT_IDX_WIDTH  = `SNN_FANOUT_IDX_WIDTH;

    reg clk = 0;
    always #5 clk = ~clk;

    reg                         rst_n;
    reg                         enable;
    reg  [NUM_GROUPS-1:0]       grp_spike_valid;
    reg  [NUM_GROUPS*LOCAL_ID_WIDTH-1:0] grp_spike_neuron_id;
    wire [NUM_GROUPS-1:0]       grp_spike_ready_default;
    wire [NUM_GROUPS-1:0]       grp_spike_ready_bypass;
    wire [NUM_GROUPS-1:0]       grp_in_valid_default;
    wire [NUM_GROUPS-1:0]       grp_in_valid_bypass;
    wire [NUM_GROUPS*LOCAL_ID_WIDTH-1:0] grp_in_dest_id_default;
    wire [NUM_GROUPS*LOCAL_ID_WIDTH-1:0] grp_in_dest_id_bypass;
    wire [NUM_GROUPS*WEIGHT_WIDTH-1:0] grp_in_weight_default;
    wire [NUM_GROUPS*WEIGHT_WIDTH-1:0] grp_in_weight_bypass;
    wire [NUM_GROUPS-1:0]       grp_in_exc_default;
    wire [NUM_GROUPS-1:0]       grp_in_exc_bypass;
    reg  [NUM_GROUPS-1:0]       grp_in_ready;
    wire                        learn_spike_valid_default;
    wire                        learn_spike_valid_bypass;
    wire [GLOBAL_ID_WIDTH-1:0]  learn_spike_src_id_default;
    wire [GLOBAL_ID_WIDTH-1:0]  learn_spike_src_id_bypass;
    wire                        router_busy_default;
    wire                        router_busy_bypass;

    wire [31:0] routed_spike_count_default;
    wire [31:0] routed_spike_count_bypass;
    wire [31:0] router_ext_invalid_group_count_default;
    wire [31:0] router_ext_invalid_group_count_bypass;
    wire [31:0] router_ct_invalid_entry_count_default;
    wire [31:0] router_ct_invalid_entry_count_bypass;
    wire [31:0] router_ct_invalid_dst_count_default;
    wire [31:0] router_ct_invalid_dst_count_bypass;
    wire [31:0] router_fanout_scan_count_default;
    wire [31:0] router_fanout_scan_count_bypass;
    wire [31:0] router_route_miss_count_default;
    wire [31:0] router_route_miss_count_bypass;
    wire [31:0] router_backpressure_stall_count_default;
    wire [31:0] router_backpressure_stall_count_bypass;

    wire                        unused_ext_ready_default;
    wire                        unused_ext_ready_bypass;
    wire                        unused_learn_weight_ready_default;
    wire                        unused_learn_weight_ready_bypass;
    wire                        unused_ct_lookup_en_default;
    wire                        unused_ct_lookup_en_bypass;
    wire [GROUP_ID_WIDTH-1:0]   unused_ct_lookup_src_group_default;
    wire [GROUP_ID_WIDTH-1:0]   unused_ct_lookup_src_group_bypass;
    wire [LOCAL_ID_WIDTH-1:0]   unused_ct_lookup_src_neuron_default;
    wire [LOCAL_ID_WIDTH-1:0]   unused_ct_lookup_src_neuron_bypass;
    wire [FANOUT_IDX_WIDTH-1:0] unused_ct_lookup_fanout_idx_default;
    wire [FANOUT_IDX_WIDTH-1:0] unused_ct_lookup_fanout_idx_bypass;
    wire [NUM_GROUPS-1:0]       unused_grp_weight_we_default;
    wire [NUM_GROUPS-1:0]       unused_grp_weight_we_bypass;
    wire [LOCAL_ID_WIDTH-1:0]   unused_grp_weight_src_default;
    wire [LOCAL_ID_WIDTH-1:0]   unused_grp_weight_src_bypass;
    wire [LOCAL_ID_WIDTH-1:0]   unused_grp_weight_dst_default;
    wire [LOCAL_ID_WIDTH-1:0]   unused_grp_weight_dst_bypass;
    wire [WEIGHT_WIDTH-1:0]     unused_grp_weight_data_default;
    wire [WEIGHT_WIDTH-1:0]     unused_grp_weight_data_bypass;
    wire                        unused_grp_weight_exc_default;
    wire                        unused_grp_weight_exc_bypass;
    wire                        unused_ct_cfg_we_default;
    wire                        unused_ct_cfg_we_bypass;
    wire [GROUP_ID_WIDTH-1:0]   unused_ct_cfg_src_group_default;
    wire [GROUP_ID_WIDTH-1:0]   unused_ct_cfg_src_group_bypass;
    wire [LOCAL_ID_WIDTH-1:0]   unused_ct_cfg_src_neuron_default;
    wire [LOCAL_ID_WIDTH-1:0]   unused_ct_cfg_src_neuron_bypass;
    wire [FANOUT_IDX_WIDTH-1:0] unused_ct_cfg_fanout_idx_default;
    wire [FANOUT_IDX_WIDTH-1:0] unused_ct_cfg_fanout_idx_bypass;
    wire                        unused_ct_cfg_valid_default;
    wire                        unused_ct_cfg_valid_bypass;
    wire [GROUP_ID_WIDTH-1:0]   unused_ct_cfg_dst_group_default;
    wire [GROUP_ID_WIDTH-1:0]   unused_ct_cfg_dst_group_bypass;
    wire [LOCAL_ID_WIDTH-1:0]   unused_ct_cfg_dst_neuron_default;
    wire [LOCAL_ID_WIDTH-1:0]   unused_ct_cfg_dst_neuron_bypass;
    wire [WEIGHT_WIDTH-1:0]     unused_ct_cfg_weight_default;
    wire [WEIGHT_WIDTH-1:0]     unused_ct_cfg_weight_bypass;
    wire                        unused_ct_cfg_exc_inh_default;
    wire                        unused_ct_cfg_exc_inh_bypass;

    integer fail_count = 0;
    integer default_notify_count = 0;
    integer bypass_notify_count = 0;

    always @(posedge clk) begin
        if (learn_spike_valid_default)
            default_notify_count = default_notify_count + 1;
        if (learn_spike_valid_bypass)
            bypass_notify_count = bypass_notify_count + 1;
    end

    task automatic check(input [8*80-1:0] desc, input integer condition);
    begin
        if (condition) begin
            $display("[PASS] %0s", desc);
        end else begin
            $display("[FAIL] %0s", desc);
            fail_count = fail_count + 1;
        end
    end
    endtask

    event_router_ng #(
        .NUM_GROUPS(NUM_GROUPS),
        .NEURONS_PER_GROUP(NEURONS_PER_GROUP),
        .WEIGHT_WIDTH(WEIGHT_WIDTH),
        .MAX_FANOUT_INTER(MAX_FANOUT_INTER)
    ) u_router_default (
        .clk(clk), .rst_n(rst_n), .enable(enable),
        .grp_spike_valid(grp_spike_valid),
        .grp_spike_neuron_id(grp_spike_neuron_id),
        .grp_spike_ready(grp_spike_ready_default),
        .grp_in_valid(grp_in_valid_default),
        .grp_in_dest_id(grp_in_dest_id_default),
        .grp_in_weight(grp_in_weight_default),
        .grp_in_exc(grp_in_exc_default),
        .grp_in_ready(grp_in_ready),
        .ext_spike_valid(1'b0),
        .ext_spike_neuron_id({GLOBAL_ID_WIDTH{1'b0}}),
        .ext_spike_weight({WEIGHT_WIDTH{1'b0}}),
        .ext_spike_exc(1'b0),
        .ext_spike_ready(unused_ext_ready_default),
        .learn_spike_valid(learn_spike_valid_default),
        .learn_spike_src_id(learn_spike_src_id_default),
        .learn_spike_ready(1'b1),
        .learn_weight_valid(1'b0),
        .learn_weight_group({GROUP_ID_WIDTH{1'b0}}),
        .learn_weight_src({LOCAL_ID_WIDTH{1'b0}}),
        .learn_weight_dst({LOCAL_ID_WIDTH{1'b0}}),
        .learn_weight_data({WEIGHT_WIDTH{1'b0}}),
        .learn_weight_exc(1'b0),
        .learn_weight_is_inter(1'b0),
        .learn_weight_dst_group({GROUP_ID_WIDTH{1'b0}}),
        .learn_weight_fanout_idx({FANOUT_IDX_WIDTH{1'b0}}),
        .learn_weight_ready(unused_learn_weight_ready_default),
        .ct_lookup_en(unused_ct_lookup_en_default),
        .ct_lookup_src_group(unused_ct_lookup_src_group_default),
        .ct_lookup_src_neuron(unused_ct_lookup_src_neuron_default),
        .ct_lookup_fanout_idx(unused_ct_lookup_fanout_idx_default),
        .ct_result_valid(1'b0),
        .ct_result_dst_group({GROUP_ID_WIDTH{1'b0}}),
        .ct_result_dst_neuron({LOCAL_ID_WIDTH{1'b0}}),
        .ct_result_weight({WEIGHT_WIDTH{1'b0}}),
        .ct_result_exc_inh(1'b0),
        .ct_result_entry_valid(1'b0),
        .grp_weight_we(unused_grp_weight_we_default),
        .grp_weight_src(unused_grp_weight_src_default),
        .grp_weight_dst(unused_grp_weight_dst_default),
        .grp_weight_data(unused_grp_weight_data_default),
        .grp_weight_exc(unused_grp_weight_exc_default),
        .ct_cfg_we(unused_ct_cfg_we_default),
        .ct_cfg_src_group(unused_ct_cfg_src_group_default),
        .ct_cfg_src_neuron(unused_ct_cfg_src_neuron_default),
        .ct_cfg_fanout_idx(unused_ct_cfg_fanout_idx_default),
        .ct_cfg_valid(unused_ct_cfg_valid_default),
        .ct_cfg_dst_group(unused_ct_cfg_dst_group_default),
        .ct_cfg_dst_neuron(unused_ct_cfg_dst_neuron_default),
        .ct_cfg_weight(unused_ct_cfg_weight_default),
        .ct_cfg_exc_inh(unused_ct_cfg_exc_inh_default),
        .routed_spike_count(routed_spike_count_default),
        .router_busy(router_busy_default),
        .router_ext_invalid_group_count(router_ext_invalid_group_count_default),
        .router_ct_invalid_entry_count(router_ct_invalid_entry_count_default),
        .router_ct_invalid_dst_count(router_ct_invalid_dst_count_default),
        .router_fanout_scan_count(router_fanout_scan_count_default),
        .router_route_miss_count(router_route_miss_count_default),
        .router_backpressure_stall_count(router_backpressure_stall_count_default)
    );

    event_router_ng #(
        .NUM_GROUPS(NUM_GROUPS),
        .NEURONS_PER_GROUP(NEURONS_PER_GROUP),
        .WEIGHT_WIDTH(WEIGHT_WIDTH),
        .MAX_FANOUT_INTER(MAX_FANOUT_INTER),
        .LEARN_NOTIFY_ENABLE(0)
    ) u_router_bypass (
        .clk(clk), .rst_n(rst_n), .enable(enable),
        .grp_spike_valid(grp_spike_valid),
        .grp_spike_neuron_id(grp_spike_neuron_id),
        .grp_spike_ready(grp_spike_ready_bypass),
        .grp_in_valid(grp_in_valid_bypass),
        .grp_in_dest_id(grp_in_dest_id_bypass),
        .grp_in_weight(grp_in_weight_bypass),
        .grp_in_exc(grp_in_exc_bypass),
        .grp_in_ready(grp_in_ready),
        .ext_spike_valid(1'b0),
        .ext_spike_neuron_id({GLOBAL_ID_WIDTH{1'b0}}),
        .ext_spike_weight({WEIGHT_WIDTH{1'b0}}),
        .ext_spike_exc(1'b0),
        .ext_spike_ready(unused_ext_ready_bypass),
        .learn_spike_valid(learn_spike_valid_bypass),
        .learn_spike_src_id(learn_spike_src_id_bypass),
        .learn_spike_ready(1'b1),
        .learn_weight_valid(1'b0),
        .learn_weight_group({GROUP_ID_WIDTH{1'b0}}),
        .learn_weight_src({LOCAL_ID_WIDTH{1'b0}}),
        .learn_weight_dst({LOCAL_ID_WIDTH{1'b0}}),
        .learn_weight_data({WEIGHT_WIDTH{1'b0}}),
        .learn_weight_exc(1'b0),
        .learn_weight_is_inter(1'b0),
        .learn_weight_dst_group({GROUP_ID_WIDTH{1'b0}}),
        .learn_weight_fanout_idx({FANOUT_IDX_WIDTH{1'b0}}),
        .learn_weight_ready(unused_learn_weight_ready_bypass),
        .ct_lookup_en(unused_ct_lookup_en_bypass),
        .ct_lookup_src_group(unused_ct_lookup_src_group_bypass),
        .ct_lookup_src_neuron(unused_ct_lookup_src_neuron_bypass),
        .ct_lookup_fanout_idx(unused_ct_lookup_fanout_idx_bypass),
        .ct_result_valid(1'b0),
        .ct_result_dst_group({GROUP_ID_WIDTH{1'b0}}),
        .ct_result_dst_neuron({LOCAL_ID_WIDTH{1'b0}}),
        .ct_result_weight({WEIGHT_WIDTH{1'b0}}),
        .ct_result_exc_inh(1'b0),
        .ct_result_entry_valid(1'b0),
        .grp_weight_we(unused_grp_weight_we_bypass),
        .grp_weight_src(unused_grp_weight_src_bypass),
        .grp_weight_dst(unused_grp_weight_dst_bypass),
        .grp_weight_data(unused_grp_weight_data_bypass),
        .grp_weight_exc(unused_grp_weight_exc_bypass),
        .ct_cfg_we(unused_ct_cfg_we_bypass),
        .ct_cfg_src_group(unused_ct_cfg_src_group_bypass),
        .ct_cfg_src_neuron(unused_ct_cfg_src_neuron_bypass),
        .ct_cfg_fanout_idx(unused_ct_cfg_fanout_idx_bypass),
        .ct_cfg_valid(unused_ct_cfg_valid_bypass),
        .ct_cfg_dst_group(unused_ct_cfg_dst_group_bypass),
        .ct_cfg_dst_neuron(unused_ct_cfg_dst_neuron_bypass),
        .ct_cfg_weight(unused_ct_cfg_weight_bypass),
        .ct_cfg_exc_inh(unused_ct_cfg_exc_inh_bypass),
        .routed_spike_count(routed_spike_count_bypass),
        .router_busy(router_busy_bypass),
        .router_ext_invalid_group_count(router_ext_invalid_group_count_bypass),
        .router_ct_invalid_entry_count(router_ct_invalid_entry_count_bypass),
        .router_ct_invalid_dst_count(router_ct_invalid_dst_count_bypass),
        .router_fanout_scan_count(router_fanout_scan_count_bypass),
        .router_route_miss_count(router_route_miss_count_bypass),
        .router_backpressure_stall_count(router_backpressure_stall_count_bypass)
    );

    initial begin
        rst_n = 0;
        enable = 0;
        grp_spike_valid = {NUM_GROUPS{1'b0}};
        grp_spike_neuron_id = {(NUM_GROUPS*LOCAL_ID_WIDTH){1'b0}};
        grp_in_ready = {NUM_GROUPS{1'b1}};
        repeat (5) @(posedge clk);
        rst_n = 1;
        enable = 1;
        repeat (3) @(posedge clk);

        grp_spike_valid[2] = 1'b1;
        grp_spike_neuron_id[2*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH] = 7'd21;
        @(posedge clk);
        while (!grp_spike_ready_default || !grp_spike_ready_bypass)
            @(posedge clk);
        grp_spike_valid[2] = 1'b0;

        repeat (40) @(posedge clk);

        check("Default router keeps learning notification enabled",
              default_notify_count == 1 &&
              learn_spike_src_id_default == {4'd2, 7'd21});
        check("Bypass router suppresses learning notification",
              bypass_notify_count == 0 && !learn_spike_valid_bypass);
        check("Bypass router returns idle after empty fanout scan",
              !router_busy_bypass &&
              router_ct_invalid_entry_count_bypass == 1 &&
              router_route_miss_count_bypass == 1);

        if (fail_count != 0) begin
            $display("*** SOME TESTS FAILED ***");
            $finish(1);
        end
        $display("*** ALL TESTS PASSED ***");
        $finish(0);
    end

    initial begin
        #200000;
        $display("[ERROR] Simulation timed out");
        $finish(2);
    end

endmodule
