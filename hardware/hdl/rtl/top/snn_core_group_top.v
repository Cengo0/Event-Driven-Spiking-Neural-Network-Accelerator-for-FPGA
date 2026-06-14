//-----------------------------------------------------------------------------
// Title         : SNN Core Group Top - Hierarchical Neuromorphic Processor
// Project       : SpikeMold (HW) + SpikePress (SW)
// File          : snn_core_group_top.v
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : Top-level integration of the Core Group architecture:
//
//                 ┌─────────────────────────────────────────────────────┐
//                 │              snn_core_group_top                     │
//                 │                                                     │
//                 │  ┌─────────────────┐    ┌──────────────────┐        │
//                 │  │ design_1_wrapper│    │  Synaptic Conn.  │        │
//                 │  │  (PS + HLS IP)  │    │  Table (BRAM)    │        │
//                 │  └──────┬──────────┘    └────────┬─────────┘        │
//                 │         │                        │                  │
//                 │         ▼                        ▼                  │
//                 │  ┌──────────────────────────────────────────┐       │
//                 │  │         Event Router (NG)                │       │
//                 │  │  - Round-robin arbitration               │       │
//                 │  │  - Sparse inter-group routing            │       │
//                 │  │  - Learning engine interface             │       │
//                 │  │  - External sensor/host input            │       │
//                 │  └──┬───┬───┬───┬───┬───┬────────┬───┬──────┘       │
//                 │     │   │   │   │   │   │        │   │              │
//                 │     ▼   ▼   ▼   ▼   ▼   ▼  ...   ▼   ▼              │
//                 │  ┌───┐┌───┐┌───┐┌───┐┌───┐     ┌────┐┌────┐         │
//                 │  │CG0││CG1││CG2││CG3││CG4│ ... │CG14││CG15│         │
//                 │  │ N0││ N1││ N2││ N3││ N4│     │ N14││ N15│         │
//                 │  └───┘└───┘└───┘└───┘└───┘     └────┘└────┘         │
//                 │                                                     │
//                 │  Variable group sizes: Ni = SNN_GROUP_SIZE_i        │
//                 │  Default: all 128 (16 × 128 = 2048 neurons)         │
//                 │  Bus width: LOCAL_ID_WIDTH = clog2(max(Ni))         │
//                 └─────────────────────────────────────────────────────┘
//
// Config Register Mapping (from AXI-Lite):
//   cfg_router_config_addr[31:28]:
//     0x0: Connectivity table write (inter-group)
//     0x1: Intra-group weight write (selects group via addr[27:25])
//     0x2: Status readback
//     0xB: Wide-layer accumulate/commit control
//     0xD: Selected destination tile/group clear control
//     0xF: Route-table lifecycle/status ABI
//
//   cfg_router_config_wdata format for connectivity table (8-bit weight):
//     [31]    = valid
//     [30:27] = dst_group  (4-bit, supports up to 16 groups)
//     [26:20] = dst_neuron (7-bit, max neurons/group)
//     [19:12] = weight     (8-bit unsigned magnitude)
//     [11]    = exc_inh
//     [10:7]  = fanout_idx (4-bit, max 16 fanout)
//     [6:0]   = src_neuron (7-bit)
//     addr[3:0] = src_group (4-bit)
//
//   cfg_router_config_wdata format for intra-group weight (8-bit weight):
//     [31:25] = src_neuron
//     [24:18] = dst_neuron
//     [17:10] = weight     (8-bit unsigned magnitude)
//     [9]     = exc
//     [8:5]   = group_id   (4-bit, supports up to 16 groups)
//     [4:0]   = reserved
//
// Resource Budget (xc7z020clg400-1):
//   - 16 Core Groups:      ~48 BRAM36, ~9,120 LUT
//   - Connectivity Table:  ~16 BRAM36 (32K×17b)
//   - Event Router:        ~300 LUT
//   - Block Design (PS+HLS): existing
//   Total RTL: ~64 BRAM36, ~9,420 LUT
//   Leaves ~54% BRAM, ~82% LUT for HLS IP
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps
`include "snn_params.vh"

module snn_core_group_top #(
    // Core Group Parameters (defaults from snn_params.yaml via snn_params.vh)
    parameter NUM_GROUPS            = `SNN_NUM_GROUPS,
    parameter NEURONS_PER_GROUP     = `SNN_NEURONS_PER_GROUP,
    parameter WEIGHT_WIDTH          = `SNN_WEIGHT_WIDTH,
    parameter MAX_FANOUT_INTER      = `SNN_MAX_FANOUT_INTER,
    parameter GROUP_ID_WIDTH        = `SNN_GROUP_ID_WIDTH,
    parameter LOCAL_ID_WIDTH        = `SNN_LOCAL_ID_WIDTH,
    parameter GLOBAL_ID_WIDTH       = `SNN_GLOBAL_ID_WIDTH,

    // Neuron Parameters
    parameter DATA_WIDTH            = `SNN_DATA_WIDTH,
    parameter THRESHOLD_WIDTH       = `SNN_THRESHOLD_WIDTH,
    parameter LEAK_WIDTH            = `SNN_LEAK_WIDTH,
    parameter REFRAC_WIDTH          = `SNN_REFRAC_WIDTH,
    parameter SPIKE_BUFFER_DEPTH    = `SNN_SPIKE_BUFFER_DEPTH,

    // HLS Compatibility
    parameter HLS_NEURON_ID_WIDTH   = `SNN_HLS_NEURON_ID_WIDTH,
    parameter HLS_MAX_NEURONS       = `SNN_TOTAL_NEURONS,
    parameter HLS_WEIGHT_WIDTH      = `SNN_HLS_WEIGHT_WIDTH,
    parameter STRICT_PHYSICAL_ID_INGRESS = 0,
`ifdef SNN_FABRIC_TOP_BOARD_VISIBLE
    parameter HLS_DIRECT_TILE_COMPAT = 1,
`else
    parameter HLS_DIRECT_TILE_COMPAT = 0,
`endif
    parameter LEARN_NOTIFY_ENABLE   = `SNN_HLS_LEARNING_ENABLE
)(
    //-------------------------------------------------------------------------
    // DDR Interface (directly from PS)
    //-------------------------------------------------------------------------
    inout  wire [14:0]  DDR_addr,
    inout  wire [2:0]   DDR_ba,
    inout  wire         DDR_cas_n,
    inout  wire         DDR_ck_n,
    inout  wire         DDR_ck_p,
    inout  wire         DDR_cke,
    inout  wire         DDR_cs_n,
    inout  wire [3:0]   DDR_dm,
    inout  wire [31:0]  DDR_dq,
    inout  wire [3:0]   DDR_dqs_n,
    inout  wire [3:0]   DDR_dqs_p,
    inout  wire         DDR_odt,
    inout  wire         DDR_ras_n,
    inout  wire         DDR_reset_n,
    inout  wire         DDR_we_n,

    //-------------------------------------------------------------------------
    // Fixed IO (PS)
    //-------------------------------------------------------------------------
    inout  wire         FIXED_IO_ddr_vrn,
    inout  wire         FIXED_IO_ddr_vrp,
    inout  wire [53:0]  FIXED_IO_mio,
    inout  wire         FIXED_IO_ps_clk,
    inout  wire         FIXED_IO_ps_porb,
    inout  wire         FIXED_IO_ps_srstb
);

    //=========================================================================
    // Derived Parameters
    //=========================================================================
    localparam FANOUT_IDX_WIDTH = $clog2(MAX_FANOUT_INTER);
    localparam TOTAL_NEURONS    = `SNN_TOTAL_NEURONS;
    localparam DIRECT_FIFO_DEPTH = 256;
    localparam DIRECT_FIFO_PTR_WIDTH = $clog2(DIRECT_FIFO_DEPTH);
    localparam integer DIRECT_MSB_FLAG_DEST_CAPACITY =
        (1 << (GLOBAL_ID_WIDTH - 1));
    localparam [0:0] DIRECT_MSB_FLAG_WIDE_LAYER_UNSAFE =
        (HLS_MAX_NEURONS > DIRECT_MSB_FLAG_DEST_CAPACITY);

    //=========================================================================
    // Clock / Reset from PS Block Design
    //=========================================================================
    wire pl_clk;
    wire rst_n_sync;
    wire debug_learning_active;

    //=========================================================================
    // HLS <-> RTL Interface Signals (from Block Design)
    //=========================================================================
    wire                            hls_spike_out_valid;
    wire [HLS_NEURON_ID_WIDTH-1:0]  hls_spike_out_neuron_id;
    wire [HLS_WEIGHT_WIDTH-1:0]     hls_spike_out_weight;
    wire                            rtl_spike_in_ready;

    wire [31:0]                     hls_direct_axis_tdata;
    wire [3:0]                      hls_direct_axis_tkeep;
    wire [3:0]                      hls_direct_axis_tstrb;
    wire                            hls_direct_axis_tvalid;
    wire                            hls_direct_axis_tlast;
    wire                            hls_direct_axis_tready;
    wire                            hls_direct_axis_tid;
    wire                            hls_direct_axis_tdest;
    wire                            hls_direct_axis_tuser;

    wire                            rtl_spike_out_valid;
    wire [HLS_NEURON_ID_WIDTH-1:0]  rtl_spike_out_neuron_id;
    wire [HLS_WEIGHT_WIDTH-1:0]     rtl_spike_out_weight;
    wire [31:0]                     rtl_spike_axis_tdata;
    wire [3:0]                      rtl_spike_axis_tkeep;
    wire [3:0]                      rtl_spike_axis_tstrb;
    wire                            rtl_spike_axis_tvalid;
    wire                            rtl_spike_axis_tlast;
    wire                            rtl_spike_axis_tready;
    wire                            rtl_spike_axis_tid;
    wire                            rtl_spike_axis_tdest;
    wire                            rtl_spike_axis_tuser;
    wire                            rtl_output_axis_enable;
    wire                            hls_spike_in_ready;

    // HLS learned-weight update channel (HLS -> Event Router) - DISABLED FOR INFERENCE
`ifdef SNN_CORE_GROUP_LEARNING_ENABLE
    wire                            hls_learn_weight_valid;
    wire [GROUP_ID_WIDTH-1:0]       hls_learn_weight_group;
    wire [LOCAL_ID_WIDTH-1:0]       hls_learn_weight_src;
    wire [LOCAL_ID_WIDTH-1:0]       hls_learn_weight_dst;
    wire [WEIGHT_WIDTH-1:0]         hls_learn_weight_data;
    wire                            hls_learn_weight_exc;
    wire                            hls_learn_weight_is_inter;
    wire [GROUP_ID_WIDTH-1:0]       hls_learn_weight_dst_group;
    wire [FANOUT_IDX_WIDTH-1:0]     hls_learn_weight_fanout_idx;
    wire                            rtl_learn_weight_ready;
`else
    // Inference mode: learning disabled - tie off to safe values
    wire                            hls_learn_weight_valid = 1'b0;
    wire [GROUP_ID_WIDTH-1:0]       hls_learn_weight_group = 0;
    wire [LOCAL_ID_WIDTH-1:0]       hls_learn_weight_src = 0;
    wire [LOCAL_ID_WIDTH-1:0]       hls_learn_weight_dst = 0;
    wire [WEIGHT_WIDTH-1:0]         hls_learn_weight_data = 0;
    wire                            hls_learn_weight_exc = 0;
    wire                            hls_learn_weight_is_inter = 0;
    wire [GROUP_ID_WIDTH-1:0]       hls_learn_weight_dst_group = 0;
    wire [FANOUT_IDX_WIDTH-1:0]     hls_learn_weight_fanout_idx = 0;
    wire                            rtl_learn_weight_ready = 1'b0;
`endif

    wire                            hls_snn_enable;
    wire                            hls_snn_reset;
    wire                            rtl_snn_ready;
    wire                            rtl_snn_busy;
    wire [15:0]                     hls_threshold_out;
    wire [15:0]                     hls_leak_rate_out;

    //=========================================================================
    // Config Register Interface (from AXI-Lite in Block Design)
    //=========================================================================
    wire                            cfg_router_config_we;
    wire [31:0]                     cfg_router_config_addr;
    wire [31:0]                     cfg_router_config_wdata;
    wire [31:0]                     cfg_router_config_rdata;

    wire                            cfg_neuron_config_we;
    wire [9:0]                      cfg_neuron_config_addr;
    wire [31:0]                     cfg_neuron_config_wdata;

    wire [15:0]                     cfg_global_threshold;
    wire [7:0]                      cfg_global_leak_rate;
    wire [7:0]                      cfg_global_refrac_period;

    //=========================================================================
    // Internal Wiring: Event Router <-> Core Groups
    //=========================================================================

    // Core group output spikes → event router
    wire [NUM_GROUPS-1:0]                       grp_spike_valid;
    wire [NUM_GROUPS*LOCAL_ID_WIDTH-1:0]        grp_spike_neuron_id;
    wire [NUM_GROUPS-1:0]                       grp_spike_ready;
    wire [NUM_GROUPS-1:0]                       router_grp_spike_valid;
    wire [NUM_GROUPS*LOCAL_ID_WIDTH-1:0]        router_grp_spike_neuron_id;
    wire [NUM_GROUPS-1:0]                       router_grp_spike_ready;

    // Event router / direct HLS replay → core group input spikes.
    // Direct active-tile replay bypasses the inter-group router so it preserves
    // the compatibility board-visible inference contract while the router remains
    // responsible for recurrent/inter-group fanout.
    wire [NUM_GROUPS-1:0]                       router_grp_in_valid;
    wire [NUM_GROUPS*LOCAL_ID_WIDTH-1:0]        router_grp_in_dest_id;
    wire [NUM_GROUPS*WEIGHT_WIDTH-1:0]          router_grp_in_weight;
    wire [NUM_GROUPS-1:0]                       router_grp_in_exc;
    wire [NUM_GROUPS-1:0]                       router_grp_in_ready;
    wire [NUM_GROUPS-1:0]                       grp_in_valid;
    wire [NUM_GROUPS*LOCAL_ID_WIDTH-1:0]        grp_in_dest_id;
    wire [NUM_GROUPS*WEIGHT_WIDTH-1:0]          grp_in_weight;
    wire [NUM_GROUPS-1:0]                       grp_in_exc;
    wire [NUM_GROUPS*THRESHOLD_WIDTH-1:0]       grp_in_threshold;
    wire [NUM_GROUPS-1:0]                       grp_in_ready;

    // Weight config from event router → core groups
    wire [NUM_GROUPS-1:0]                       grp_weight_we;
    wire [LOCAL_ID_WIDTH-1:0]                   grp_weight_src;
    wire [LOCAL_ID_WIDTH-1:0]                   grp_weight_dst;
    wire [WEIGHT_WIDTH-1:0]                     grp_weight_data;
    wire                                        grp_weight_exc;

    // Core group status
    wire [NUM_GROUPS*16-1:0]                    grp_spike_count;
    wire [NUM_GROUPS-1:0]                       grp_busy;

    //=========================================================================
    // Internal Wiring: Event Router <-> Connectivity Table
    //=========================================================================
    wire                          ct_lookup_en;
    wire [GROUP_ID_WIDTH-1:0]     ct_lookup_src_group;
    wire [LOCAL_ID_WIDTH-1:0]     ct_lookup_src_neuron;
    wire [FANOUT_IDX_WIDTH-1:0]   ct_lookup_fanout_idx;

    wire                          ct_result_valid;
    wire [GROUP_ID_WIDTH-1:0]     ct_result_dst_group;
    wire [LOCAL_ID_WIDTH-1:0]     ct_result_dst_neuron;
    wire [WEIGHT_WIDTH-1:0]       ct_result_weight;
    wire                          ct_result_exc_inh;
    wire                          ct_result_entry_valid;

    // Connectivity table config (from event router or decode logic)
    wire                          ct_cfg_we;
    wire [GROUP_ID_WIDTH-1:0]     ct_cfg_src_group;
    wire [LOCAL_ID_WIDTH-1:0]     ct_cfg_src_neuron;
    wire [FANOUT_IDX_WIDTH-1:0]   ct_cfg_fanout_idx;
    wire                          ct_cfg_valid_bit;
    wire [GROUP_ID_WIDTH-1:0]     ct_cfg_dst_group;
    wire [LOCAL_ID_WIDTH-1:0]     ct_cfg_dst_neuron;
    wire [WEIGHT_WIDTH-1:0]       ct_cfg_weight;
    wire                          ct_cfg_exc_inh;

    // Learning engine interface - DISABLED FOR INFERENCE MODE
`ifdef SNN_CORE_GROUP_LEARNING_ENABLE
    wire                          learn_spike_valid;
    wire [GLOBAL_ID_WIDTH-1:0]    learn_spike_src_id;
    wire                          learn_spike_ready;

    // Enable learned-weight bridge from HLS to Event Router.
    localparam                    LEARN_WEIGHT_BRIDGE_ENABLE = 1'b1;
    wire                          learn_weight_valid_br;
    wire [GROUP_ID_WIDTH-1:0]     learn_weight_group_br;
    wire [LOCAL_ID_WIDTH-1:0]     learn_weight_src_br;
    wire [LOCAL_ID_WIDTH-1:0]     learn_weight_dst_br;
    wire [WEIGHT_WIDTH-1:0]       learn_weight_data_br;
    wire                          learn_weight_exc_br;
    wire                          learn_weight_is_inter_br;
    wire [GROUP_ID_WIDTH-1:0]     learn_weight_dst_group_br;
    wire [FANOUT_IDX_WIDTH-1:0]   learn_weight_fanout_idx_br;
    wire                          learn_weight_ready_br;

    assign learn_weight_valid_br      = LEARN_WEIGHT_BRIDGE_ENABLE ? hls_learn_weight_valid : 1'b0;
    assign learn_weight_group_br      = LEARN_WEIGHT_BRIDGE_ENABLE ? hls_learn_weight_group : {GROUP_ID_WIDTH{1'b0}};
    assign learn_weight_src_br        = LEARN_WEIGHT_BRIDGE_ENABLE ? hls_learn_weight_src : {LOCAL_ID_WIDTH{1'b0}};
    assign learn_weight_dst_br        = LEARN_WEIGHT_BRIDGE_ENABLE ? hls_learn_weight_dst : {LOCAL_ID_WIDTH{1'b0}};
    assign learn_weight_data_br       = LEARN_WEIGHT_BRIDGE_ENABLE ? hls_learn_weight_data : {WEIGHT_WIDTH{1'b0}};
    assign learn_weight_exc_br        = LEARN_WEIGHT_BRIDGE_ENABLE ? hls_learn_weight_exc : 1'b0;
    assign learn_weight_is_inter_br   = LEARN_WEIGHT_BRIDGE_ENABLE ? hls_learn_weight_is_inter : 1'b0;
    assign learn_weight_dst_group_br  = LEARN_WEIGHT_BRIDGE_ENABLE ? hls_learn_weight_dst_group : {GROUP_ID_WIDTH{1'b0}};
    assign learn_weight_fanout_idx_br = LEARN_WEIGHT_BRIDGE_ENABLE ? hls_learn_weight_fanout_idx : {FANOUT_IDX_WIDTH{1'b0}};
`else
    // Inference mode: learning disabled - tie off to safe values
    wire                          learn_spike_valid = 1'b0;
    wire [GLOBAL_ID_WIDTH-1:0]    learn_spike_src_id = 0;
    wire                          learn_spike_ready = 1'b1;

    localparam                    LEARN_WEIGHT_BRIDGE_ENABLE = 1'b0;
    wire                          learn_weight_valid_br = 1'b0;
    wire [GROUP_ID_WIDTH-1:0]     learn_weight_group_br = 0;
    wire [LOCAL_ID_WIDTH-1:0]     learn_weight_src_br = 0;
    wire [LOCAL_ID_WIDTH-1:0]     learn_weight_dst_br = 0;
    wire [WEIGHT_WIDTH-1:0]       learn_weight_data_br = 0;
    wire                          learn_weight_exc_br = 0;
    wire                          learn_weight_is_inter_br = 0;
    wire [GROUP_ID_WIDTH-1:0]     learn_weight_dst_group_br = 0;
    wire [FANOUT_IDX_WIDTH-1:0]   learn_weight_fanout_idx_br = 0;
    wire                          learn_weight_ready_br = 1'b0;
`endif

    // Router status
    wire [31:0]                   routed_spike_count;
    wire                          router_busy;
    wire [31:0]                   router_ext_invalid_group_count;
    wire [31:0]                   router_ct_invalid_entry_count;
    wire [31:0]                   router_ct_invalid_dst_count;
    wire [31:0]                   router_fanout_scan_count;
    wire [31:0]                   router_route_miss_count;
    wire [31:0]                   router_backpressure_stall_count;

    // Route table lifecycle/status ABI
    wire                          route_clear_busy;
    wire                          route_clear_done;
    wire [31:0]                   route_entry_count;
    wire [31:0]                   route_checksum;
    wire [31:0]                   route_write_error_count;
    reg                           route_clear_start_reg;
    reg                           route_begin_seen;
    reg                           route_committed;
    reg                           route_commit_error;
    reg                           route_clear_done_sticky;
    reg [15:0]                    route_model_id;
    reg [31:0]                    route_expected_entry_count;
    reg [31:0]                    route_expected_checksum;
    wire [3:0]                    cfg_route_subcmd;
    wire                          route_entry_count_match;
    wire                          route_checksum_match;
    wire                          route_write_error;
    wire [31:0]                   route_status_word;

    // Event-router output bridge status
    wire                          output_bridge_event;
    wire                          output_bridge_overflow;
    wire [31:0]                   output_bridge_fifo_level;
    wire [31:0]                   output_bridge_event_count;
    wire [31:0]                   output_bridge_emit_count;
    wire [31:0]                   output_bridge_drop_count;
    reg [31:0]                    service_cycles_counter;
    reg [31:0]                    pl_busy_cycles_counter;
    reg [31:0]                    output_drain_cycles_counter;
    wire                          output_drain_busy;

    //=========================================================================
    // Config Register Decode Logic
    //=========================================================================
    // Decode cfg_router_config for connectivity table & intra-group weights

    wire [3:0] cfg_cmd = cfg_router_config_addr[31:28];
    assign cfg_route_subcmd = cfg_router_config_addr[3:0];
    assign route_entry_count_match = (route_entry_count == route_expected_entry_count);
    assign route_checksum_match = (route_checksum == route_expected_checksum);
    assign route_write_error = (route_write_error_count != 32'd0);
    assign route_status_word = {
        24'd0,
        route_entry_count_match,
        route_checksum_match,
        route_write_error,
        route_clear_done_sticky,
        route_clear_busy,
        route_commit_error,
        route_committed,
        route_begin_seen
    };

    // Connectivity table write: cmd = 0x0
    reg                          ct_cfg_we_reg;
    reg [GROUP_ID_WIDTH-1:0]     ct_cfg_src_group_reg;
    reg [LOCAL_ID_WIDTH-1:0]     ct_cfg_src_neuron_reg;
    reg [FANOUT_IDX_WIDTH-1:0]   ct_cfg_fanout_idx_reg;
    reg                          ct_cfg_valid_reg;
    reg [GROUP_ID_WIDTH-1:0]     ct_cfg_dst_group_reg;
    reg [LOCAL_ID_WIDTH-1:0]     ct_cfg_dst_neuron_reg;
    reg [WEIGHT_WIDTH-1:0]       ct_cfg_weight_reg;
    reg                          ct_cfg_exc_inh_reg;

    // Intra-group weight write: cmd = 0x1
    reg [NUM_GROUPS-1:0]         intra_weight_we_reg;
    reg [LOCAL_ID_WIDTH-1:0]     intra_weight_src_reg;
    reg [LOCAL_ID_WIDTH-1:0]     intra_weight_dst_reg;
    reg [WEIGHT_WIDTH-1:0]       intra_weight_data_reg;
    reg                          intra_weight_exc_reg;

    // Wide-layer commit/clear control: cmd = 0xB / 0xD
    wire                         cfg_accumulate_only;
    wire [NUM_GROUPS-1:0]        cfg_commit_group_mask;
    wire                         cfg_commit_start_pulse;
    wire [NUM_GROUPS-1:0]        grp_commit_busy;
    wire [NUM_GROUPS-1:0]        grp_commit_done;
    wire [NUM_GROUPS-1:0]        cfg_clear_group_mask;
    wire                         cfg_clear_start_pulse;
    wire [NUM_GROUPS-1:0]        grp_clear_busy;
    wire [NUM_GROUPS-1:0]        grp_clear_done;

    always @(posedge pl_clk) begin
        if (!rst_n_sync) begin
            ct_cfg_we_reg       <= 0;
            intra_weight_we_reg <= {NUM_GROUPS{1'b0}};
            route_clear_start_reg <= 1'b0;
            route_begin_seen <= 1'b0;
            route_committed <= 1'b0;
            route_commit_error <= 1'b0;
            route_clear_done_sticky <= 1'b0;
            route_model_id <= 16'd0;
            route_expected_entry_count <= 32'd0;
            route_expected_checksum <= 32'd0;
        end else begin
            ct_cfg_we_reg       <= 0;
            intra_weight_we_reg <= {NUM_GROUPS{1'b0}};
            route_clear_start_reg <= 1'b0;

            if (route_clear_done)
                route_clear_done_sticky <= 1'b1;

            if (cfg_router_config_we) begin
                case (cfg_cmd)
                    4'h0: begin
                        // Connectivity table write (8-bit weight format)
                        // src_group is in address register [3:0]
                        ct_cfg_we_reg         <= 1;
                        ct_cfg_valid_reg      <= cfg_router_config_wdata[31];
                        ct_cfg_dst_group_reg  <= cfg_router_config_wdata[30:27];
                        ct_cfg_dst_neuron_reg <= cfg_router_config_wdata[26:20];
                        ct_cfg_weight_reg     <= cfg_router_config_wdata[19:12];
                        ct_cfg_exc_inh_reg    <= cfg_router_config_wdata[11];
                        ct_cfg_fanout_idx_reg <= cfg_router_config_wdata[10:7];
                        ct_cfg_src_neuron_reg <= cfg_router_config_wdata[6:0];
                        ct_cfg_src_group_reg  <= cfg_router_config_addr[3:0];
                    end
                    4'h1: begin
                        // Intra-group weight write (8-bit weight format)
                        intra_weight_src_reg  <= cfg_router_config_wdata[31:25];
                        intra_weight_dst_reg  <= cfg_router_config_wdata[24:18];
                        intra_weight_data_reg <= cfg_router_config_wdata[17:10];
                        intra_weight_exc_reg  <= cfg_router_config_wdata[9];
                        intra_weight_we_reg[cfg_router_config_wdata[8:5]] <= 1'b1;
                    end
                    4'hF: begin
                        case (cfg_route_subcmd)
                            4'h0: begin
                                // route_begin(model_id, entry_count[15:0]).
                                // The host must wait for clear_done before route_write.
                                route_clear_start_reg <= 1'b1;
                                route_begin_seen <= 1'b1;
                                route_committed <= 1'b0;
                                route_commit_error <= 1'b0;
                                route_clear_done_sticky <= 1'b0;
                                route_model_id <= cfg_router_config_wdata[15:0];
                                route_expected_entry_count <= {16'd0, cfg_router_config_wdata[31:16]};
                                route_expected_checksum <= 32'd0;
                            end
                            4'h1: begin
                                route_expected_checksum <= cfg_router_config_wdata;
                            end
                            4'h2: begin
                                if (route_begin_seen &&
                                    !route_clear_busy &&
                                    !route_write_error &&
                                    route_entry_count_match &&
                                    route_checksum_match) begin
                                    route_committed <= 1'b1;
                                    route_commit_error <= 1'b0;
                                end else begin
                                    route_committed <= 1'b0;
                                    route_commit_error <= 1'b1;
                                end
                            end
                            4'h3: begin
                                route_clear_start_reg <= 1'b1;
                                route_begin_seen <= 1'b0;
                                route_committed <= 1'b0;
                                route_commit_error <= 1'b0;
                                route_clear_done_sticky <= 1'b0;
                                route_model_id <= 16'd0;
                                route_expected_entry_count <= 32'd0;
                                route_expected_checksum <= 32'd0;
                            end
                            default: ;
                        endcase
                    end
                    default: ;
                endcase
            end
        end
    end

    wide_control_decode #(
        .NUM_GROUPS(NUM_GROUPS)
    ) u_wide_control_decode (
        .clk(pl_clk),
        .rst_n(rst_n_sync),
        .cfg_we(cfg_router_config_we),
        .cfg_addr(cfg_router_config_addr),
        .cfg_wdata(cfg_router_config_wdata),
        .accumulate_only(cfg_accumulate_only),
        .commit_group_mask(cfg_commit_group_mask),
        .commit_start_pulse(cfg_commit_start_pulse),
        .clear_group_mask(cfg_clear_group_mask),
        .clear_start_pulse(cfg_clear_start_pulse)
    );

    //=========================================================================
    // Status Readback
    //=========================================================================
    reg [31:0] total_neuron_spikes;

    // Parametric spike summation: returns 0 for out-of-range group indices
    function [15:0] safe_spike_count;
        input integer idx;
        begin
            if (idx < NUM_GROUPS)
                safe_spike_count = grp_spike_count[16*idx +: 16];
            else
                safe_spike_count = 16'd0;
        end
    endfunction

    // Sum spike counts from all groups (pipelined for timing)
    reg [31:0] spike_sum_stage1 [0:3];  // 4 partial sums of up to 4 groups each
    integer si;
    always @(posedge pl_clk) begin
        if (!rst_n_sync || hls_snn_reset) begin
            for (si = 0; si < 4; si = si + 1)
                spike_sum_stage1[si] <= 0;
            total_neuron_spikes <= 0;
        end else begin
            // Stage 1: Sum up to 4 groups each (safe for NUM_GROUPS < 16)
            spike_sum_stage1[0] <= safe_spike_count(0)  + safe_spike_count(1)  +
                                   safe_spike_count(2)  + safe_spike_count(3);
            spike_sum_stage1[1] <= safe_spike_count(4)  + safe_spike_count(5)  +
                                   safe_spike_count(6)  + safe_spike_count(7);
            spike_sum_stage1[2] <= safe_spike_count(8)  + safe_spike_count(9)  +
                                   safe_spike_count(10) + safe_spike_count(11);
            spike_sum_stage1[3] <= safe_spike_count(12) + safe_spike_count(13) +
                                   safe_spike_count(14) + safe_spike_count(15);
            // Stage 2: Final sum
            total_neuron_spikes <= spike_sum_stage1[0] + spike_sum_stage1[1] +
                                   spike_sum_stage1[2] + spike_sum_stage1[3];
        end
    end

    assign cfg_router_config_rdata = (cfg_cmd == 4'h2) ? routed_spike_count :
                                     (cfg_cmd == 4'h3) ? total_neuron_spikes :
                                     (cfg_cmd == 4'h4) ? hls_direct_axis_accept_count :
                                     (cfg_cmd == 4'h5) ? hls_direct_fifo_push_count :
                                     (cfg_cmd == 4'h6) ? hls_direct_core_accept_count :
                                     (cfg_cmd == 4'h7) ? {20'd0, hls_direct_axis_tvalid,
                                                          hls_direct_axis_tready,
                                                          hls_direct_fifo_full,
                                                          hls_direct_fifo_empty,
                                                          hls_direct_fifo_count[7:0]} :
                                     (cfg_cmd == 4'h8) ? {30'd0,
                                                          (HLS_DIRECT_TILE_COMPAT != 0),
                                                          DIRECT_MSB_FLAG_WIDE_LAYER_UNSAFE} :
                                     (cfg_cmd == 4'h9) ? hls_direct_axis_scalar_collision_count :
                                     (cfg_cmd == 4'hA) ? hls_direct_axis_invalid_id_count :
                                     (cfg_cmd == 4'hB) ? {grp_commit_done,
                                                          grp_commit_busy} :
                                     (cfg_cmd == 4'hC) ? {15'd0,
                                                          cfg_accumulate_only,
                                                          cfg_commit_group_mask} :
                                     (cfg_cmd == 4'hD) ? {grp_clear_done,
                                                          grp_clear_busy} :
                                     (cfg_cmd == 4'hE) ? {16'd0,
                                                          cfg_clear_group_mask} :
                                     (cfg_cmd == 4'hF && cfg_route_subcmd == 4'h0) ? route_status_word :
                                     (cfg_cmd == 4'hF && cfg_route_subcmd == 4'h1) ? route_entry_count :
                                     (cfg_cmd == 4'hF && cfg_route_subcmd == 4'h2) ? route_checksum :
                                     (cfg_cmd == 4'hF && cfg_route_subcmd == 4'h3) ? route_expected_entry_count :
                                     (cfg_cmd == 4'hF && cfg_route_subcmd == 4'h4) ? route_expected_checksum :
                                     (cfg_cmd == 4'hF && cfg_route_subcmd == 4'h5) ? {16'd0, route_model_id} :
                                     (cfg_cmd == 4'hF && cfg_route_subcmd == 4'h8) ? router_ext_invalid_group_count :
                                     (cfg_cmd == 4'hF && cfg_route_subcmd == 4'h9) ? router_ct_invalid_entry_count :
                                     (cfg_cmd == 4'hF && cfg_route_subcmd == 4'hA) ? router_ct_invalid_dst_count :
                                     (cfg_cmd == 4'hF && cfg_route_subcmd == 4'hB) ? router_fanout_scan_count :
                                     (cfg_cmd == 4'hF && cfg_route_subcmd == 4'hC) ? router_route_miss_count :
                                     (cfg_cmd == 4'hF && cfg_route_subcmd == 4'hD) ? router_backpressure_stall_count :
                                     32'hDEAD_BEEF;

    //=========================================================================
    // Block Design Instantiation (PS + HLS IP + AXI + Config Regs)
    //=========================================================================

    design_1_wrapper u_block_design (
        // DDR Interface
        .DDR_addr           (DDR_addr),
        .DDR_ba             (DDR_ba),
        .DDR_cas_n          (DDR_cas_n),
        .DDR_ck_n           (DDR_ck_n),
        .DDR_ck_p           (DDR_ck_p),
        .DDR_cke            (DDR_cke),
        .DDR_cs_n           (DDR_cs_n),
        .DDR_dm             (DDR_dm),
        .DDR_dq             (DDR_dq),
        .DDR_dqs_n          (DDR_dqs_n),
        .DDR_dqs_p          (DDR_dqs_p),
        .DDR_odt            (DDR_odt),
        .DDR_ras_n          (DDR_ras_n),
        .DDR_reset_n        (DDR_reset_n),
        .DDR_we_n           (DDR_we_n),

        // Fixed IO
        .FIXED_IO_ddr_vrn   (FIXED_IO_ddr_vrn),
        .FIXED_IO_ddr_vrp   (FIXED_IO_ddr_vrp),
        .FIXED_IO_mio       (FIXED_IO_mio),
        .FIXED_IO_ps_clk    (FIXED_IO_ps_clk),
        .FIXED_IO_ps_porb   (FIXED_IO_ps_porb),
        .FIXED_IO_ps_srstb  (FIXED_IO_ps_srstb),

        // PL Clock/Reset
        .pl_clk         (pl_clk),
        .rst_n_sync          (rst_n_sync),

        // Debug
        .debug_learning_active (debug_learning_active),

        // HLS -> RTL Spike Interface
        .spike_in_valid          (hls_spike_out_valid),
        .spike_in_neuron_id      (hls_spike_out_neuron_id),
        .spike_in_weight         (hls_spike_out_weight),
        .spike_in_ready          (rtl_spike_in_ready),

        // HLS -> RTL Direct Spike AXI-Stream Interface
        .m_axis_direct_TDATA     (hls_direct_axis_tdata),
        .m_axis_direct_TKEEP     (hls_direct_axis_tkeep),
        .m_axis_direct_TSTRB     (hls_direct_axis_tstrb),
        .m_axis_direct_TVALID    (hls_direct_axis_tvalid),
        .m_axis_direct_TLAST     (hls_direct_axis_tlast),
        .m_axis_direct_TREADY    (hls_direct_axis_tready),
        .m_axis_direct_TID       (hls_direct_axis_tid),
        .m_axis_direct_TDEST     (hls_direct_axis_tdest),
        .m_axis_direct_TUSER     (hls_direct_axis_tuser),

        // RTL -> HLS Spike Interface
        .spike_out_valid         (rtl_output_axis_enable ? 1'b0 : rtl_spike_out_valid),
        .spike_out_neuron_id     (rtl_spike_out_neuron_id),
        .spike_out_weight        (rtl_spike_out_weight),
        .spike_out_ready         (hls_spike_in_ready),

        // RTL -> HLS Spike AXI-Stream Interface
        .s_axis_rtl_spikes_TDATA  (rtl_spike_axis_tdata),
        .s_axis_rtl_spikes_TKEEP  (rtl_spike_axis_tkeep),
        .s_axis_rtl_spikes_TSTRB  (rtl_spike_axis_tstrb),
        .s_axis_rtl_spikes_TVALID (rtl_spike_axis_tvalid),
        .s_axis_rtl_spikes_TLAST  (rtl_spike_axis_tlast),
        .s_axis_rtl_spikes_TREADY (rtl_spike_axis_tready),
        .s_axis_rtl_spikes_TID    (rtl_spike_axis_tid),
        .s_axis_rtl_spikes_TDEST  (rtl_spike_axis_tdest),
        .s_axis_rtl_spikes_TUSER  (rtl_spike_axis_tuser),

 `ifdef SNN_CORE_GROUP_LEARNING_ENABLE
        // HLS -> RTL learned-weight update interface
        .learn_weight_valid      (hls_learn_weight_valid),
        .learn_weight_group      (hls_learn_weight_group),
        .learn_weight_src        (hls_learn_weight_src),
        .learn_weight_dst        (hls_learn_weight_dst),
        .learn_weight_data       (hls_learn_weight_data),
        .learn_weight_exc        (hls_learn_weight_exc),
        .learn_weight_is_inter   (hls_learn_weight_is_inter),
        .learn_weight_dst_group  (hls_learn_weight_dst_group),
        .learn_weight_fanout_idx (hls_learn_weight_fanout_idx),
        .learn_weight_ready      (rtl_learn_weight_ready),
`else
        // Inference mode: learning disabled - tie off to safe values
        .learn_weight_valid      (1'b0),
        .learn_weight_group      (0),
        .learn_weight_src        (0),
        .learn_weight_dst        (0),
        .learn_weight_data       (0),
        .learn_weight_exc        (0),
        .learn_weight_is_inter   (0),
        .learn_weight_dst_group  (0),
        .learn_weight_fanout_idx (0),
        .learn_weight_ready      (1'b0),
`endif

        // SNN Control
        .snn_enable              (hls_snn_enable),
        .snn_reset               (hls_snn_reset),
        .snn_ready               (rtl_snn_ready),
        .snn_busy                (rtl_snn_busy),

        // HLS Neuron Parameters
        .threshold_out           (hls_threshold_out),
        .leak_rate_out           (hls_leak_rate_out),

        // Config Registers
        .cfg_router_config_we    (cfg_router_config_we),
        .cfg_router_config_addr  (cfg_router_config_addr),
        .cfg_router_config_wdata (cfg_router_config_wdata),
        .cfg_router_config_rdata (cfg_router_config_rdata),
        .cfg_neuron_config_we    (cfg_neuron_config_we),
        .cfg_neuron_config_addr  (cfg_neuron_config_addr),
        .cfg_neuron_config_wdata (cfg_neuron_config_wdata),
        .cfg_global_threshold    (cfg_global_threshold),
        .cfg_global_leak_rate    (cfg_global_leak_rate),
        .cfg_global_refrac_period(cfg_global_refrac_period),

        // Status
        .cfg_router_spike_count  (routed_spike_count),
        .cfg_neuron_spike_count  (total_neuron_spikes),
        .cfg_fifo_overflow       (output_bridge_overflow),
        .cfg_active_neurons      (8'd0),  // TODO: aggregate
        .cfg_throughput_counter  (routed_spike_count),
        .cfg_service_cycles_counter(service_cycles_counter),
        .cfg_pl_busy_cycles_counter(pl_busy_cycles_counter),
        .cfg_output_drain_cycles_counter(output_drain_cycles_counter),
        .cfg_output_bridge_status({22'd0,
                                   (output_bridge_fifo_level != 32'd0),
                                   output_bridge_fifo_level[7:0],
                                   output_bridge_overflow}),
        .cfg_output_bridge_event_count(output_bridge_event_count),
        .cfg_output_bridge_emit_count(output_bridge_emit_count),
        .cfg_output_bridge_drop_count(output_bridge_drop_count)
    );

    //=========================================================================
    // HLS ↔ Event Router Bridge
    //=========================================================================

    // HLS spike output -> Event Router external input
    // Current tiled HLS replay can still emit the compatibility direct-tile form:
    // bit GLOBAL_ID_WIDTH-1 marks a direct destination and lower bits hold the
    // physical destination. In board-visible compatibility mode, strip that
    // flag and convert the signed int8 payload into magnitude + exc/inh.
    reg                             hls_spike_valid_d;
    reg                             hls_spike_accepted_d;
    reg [HLS_NEURON_ID_WIDTH-1:0]   hls_spike_nid_d;
    reg [HLS_WEIGHT_WIDTH-1:0]      hls_spike_wt_d;
    reg                             hls_spike_wait_clear;
    wire [GLOBAL_ID_WIDTH-1:0]      hls_global_id;
    wire [GLOBAL_ID_WIDTH-1:0]      hls_direct_dest_id;
    wire [WEIGHT_WIDTH-1:0]         hls_weight_truncated;
    wire                            hls_spike_payload_changed;
    wire                            hls_spike_capture_ready;
    wire                            hls_pending_ready;
    wire                            hls_spike_event;
    wire                            hls_direct_raw;
    wire                            hls_direct_flagged_raw;
    wire                            hls_board_visible_dest_raw;
    wire                            hls_direct_event;
    wire                            hls_direct_scalar_push;
    wire                            hls_router_event;
    wire [HLS_NEURON_ID_WIDTH-1:0]  hls_direct_axis_neuron_id;
    wire [HLS_WEIGHT_WIDTH-1:0]     hls_direct_axis_weight;
    wire                            hls_direct_axis_raw;
    wire                            hls_direct_axis_explicit_raw;
    wire                            hls_direct_axis_explicit_invalid;
    wire                            hls_direct_axis_ingress_invalid;
    wire                            hls_direct_axis_compat_raw;
    wire                            hls_direct_axis_flagged_raw;
    wire                            hls_direct_axis_board_visible_raw;
    wire [GLOBAL_ID_WIDTH-1:0]      hls_direct_axis_dest_id;
    wire                            hls_scalar_id_in_range;
    wire                            hls_scalar_invalid;
    wire                            hls_scalar_invalid_event;
    wire                            hls_spike_capture_event;
    wire                            hls_direct_axis_weight_negative;
    wire [HLS_WEIGHT_WIDTH-1:0]     hls_direct_axis_weight_abs;
    wire [WEIGHT_WIDTH-1:0]         hls_direct_axis_weight_mag;
    wire                            hls_direct_axis_push;
    wire                            hls_direct_scalar_axis_collision;
    wire                            hls_spike_weight_negative;
    wire [HLS_WEIGHT_WIDTH-1:0]     hls_spike_weight_abs;
    wire [WEIGHT_WIDTH-1:0]         hls_spike_weight_mag;
    wire                            hls_direct_weight_negative;
    wire [HLS_WEIGHT_WIDTH-1:0]     hls_direct_weight_abs;
    wire [WEIGHT_WIDTH-1:0]         hls_direct_weight_mag;
    wire [GLOBAL_ID_WIDTH-1:0]      hls_direct_push_id;
    wire [WEIGHT_WIDTH-1:0]         hls_direct_push_weight;
    wire                            hls_direct_push_exc;
    wire                            hls_direct_pending;
    wire [GLOBAL_ID_WIDTH-1:0]      hls_direct_pending_id;
    wire [WEIGHT_WIDTH-1:0]         hls_direct_pending_weight;
    wire                            hls_direct_pending_exc;
    wire [THRESHOLD_WIDTH-1:0]      hls_direct_pending_threshold;
    wire [GROUP_ID_WIDTH-1:0]       hls_direct_pending_group_id;
    wire [LOCAL_ID_WIDTH-1:0]       hls_direct_pending_local_id;
    wire                            hls_direct_pending_group_valid;
    wire                            hls_direct_pending_ready;
    wire                            hls_direct_fifo_full;
    wire                            hls_direct_fifo_empty;
    wire                            hls_direct_fifo_push;
    wire                            hls_direct_fifo_pop;
    wire                            router_ext_spike_ready;
    wire                            router_ext_spike_valid;
    wire [GLOBAL_ID_WIDTH-1:0]      router_ext_spike_id;
    wire [WEIGHT_WIDTH-1:0]         router_ext_spike_weight;
    wire                            router_ext_spike_exc;
    wire                            host_output_spike_valid_raw;
    wire [GLOBAL_ID_WIDTH-1:0]      host_output_spike_id_raw;
    reg                             host_output_spike_valid_q;
    reg  [GLOBAL_ID_WIDTH-1:0]      host_output_spike_id_q;
    reg                             direct_host_spike_valid;
    reg  [GLOBAL_ID_WIDTH-1:0]      direct_host_spike_id;
    reg  [NUM_GROUPS-1:0]           direct_host_spike_ready;

    localparam DIRECT_FIFO_ENTRY_WIDTH = GLOBAL_ID_WIDTH + WEIGHT_WIDTH + 1 + THRESHOLD_WIDTH;

    reg [DIRECT_FIFO_ENTRY_WIDTH-1:0] hls_direct_fifo [0:DIRECT_FIFO_DEPTH-1];
    reg [DIRECT_FIFO_PTR_WIDTH-1:0]   hls_direct_fifo_wr_ptr;
    reg [DIRECT_FIFO_PTR_WIDTH-1:0]   hls_direct_fifo_rd_ptr;
    reg [DIRECT_FIFO_PTR_WIDTH:0]     hls_direct_fifo_count;
    reg [31:0]                        hls_direct_axis_accept_count;
    reg [31:0]                        hls_direct_fifo_push_count;
    reg [31:0]                        hls_direct_core_accept_count;
    reg [31:0]                        hls_direct_axis_scalar_collision_count;
    reg [31:0]                        hls_direct_axis_invalid_id_count;

    wire [DIRECT_FIFO_ENTRY_WIDTH-1:0] hls_direct_fifo_head;

    assign hls_weight_truncated = hls_spike_weight_mag;
    assign hls_spike_weight_negative = hls_spike_out_weight[HLS_WEIGHT_WIDTH-1];
    assign hls_spike_weight_abs = hls_spike_weight_negative
        ? ((~hls_spike_out_weight) + {{(HLS_WEIGHT_WIDTH-1){1'b0}}, 1'b1})
        : hls_spike_out_weight;
    assign hls_spike_weight_mag = hls_spike_weight_abs[WEIGHT_WIDTH-1:0];
    assign hls_spike_payload_changed =
        (hls_spike_out_neuron_id != hls_spike_nid_d) ||
        (hls_spike_out_weight    != hls_spike_wt_d);
    assign hls_pending_ready = (!hls_spike_out_valid || !hls_scalar_id_in_range)
        ? 1'b1
        : (hls_direct_raw ? !hls_direct_fifo_full : router_ext_spike_ready);
    assign hls_spike_capture_event = hls_snn_enable &
                                     hls_spike_out_valid &
                                     !hls_spike_wait_clear &
                                     hls_pending_ready;
    assign hls_spike_event = hls_spike_capture_event &
                             hls_scalar_id_in_range;
    assign hls_scalar_invalid_event = hls_spike_capture_event &
                                      hls_scalar_invalid;
    assign hls_spike_capture_ready = hls_snn_enable &
                                     hls_pending_ready;

    hls_scalar_spike_id_guard #(
        .HLS_NEURON_ID_WIDTH(HLS_NEURON_ID_WIDTH),
        .GLOBAL_ID_WIDTH(GLOBAL_ID_WIDTH),
        .HLS_DIRECT_TILE_COMPAT(HLS_DIRECT_TILE_COMPAT),
        .STRICT_PHYSICAL_ID_INGRESS(STRICT_PHYSICAL_ID_INGRESS)
    ) u_hls_scalar_spike_id_guard (
        .neuron_id          (hls_spike_out_neuron_id),
        .tvalid             (hls_spike_out_valid),
        .global_id          (hls_global_id),
        .direct_dest_id     (hls_direct_dest_id),
        .id_in_range        (hls_scalar_id_in_range),
        .invalid            (hls_scalar_invalid),
        .flagged_raw        (hls_direct_flagged_raw),
        .board_visible_raw  (hls_board_visible_dest_raw),
        .direct_raw         (hls_direct_raw),
        .router_raw         ()
    );
    // Board-visible dst0 replay is physically partitioned as:
    //   source IDs      512..1023
    //   destination IDs   0..511
    // The HLS direct replay contract normally marks destinations with the MSB
    // direct flag.  Accept the unflagged dst0 range as direct too so generated
    // HLS variants that expose stripped physical destination IDs do not fall
    // back into the router external path.
    assign hls_direct_event = hls_spike_event & hls_direct_raw;
    // In board-visible direct replay the AXIS packet is the authoritative
    // destination event.  A same-cycle scalar sideband event is a compatibility
    // duplicate from the HLS ap_none path; acknowledge it so HLS can advance,
    // suppress the duplicate FIFO write, and expose the collision counter.
    assign hls_direct_scalar_push = hls_direct_event & !hls_direct_fifo_full &
                                    !hls_direct_axis_push;
    assign hls_router_event = hls_spike_event & ~hls_direct_raw;
    assign hls_direct_weight_negative = hls_spike_weight_negative;
    assign hls_direct_weight_abs = hls_spike_weight_abs;
    assign hls_direct_weight_mag = hls_spike_weight_mag;

    assign hls_direct_axis_neuron_id =
        hls_direct_axis_tdata[HLS_NEURON_ID_WIDTH-1:0];
    assign hls_direct_axis_weight =
        hls_direct_axis_tdata[HLS_NEURON_ID_WIDTH +: HLS_WEIGHT_WIDTH];

    direct_axis_id_decoder #(
        .HLS_NEURON_ID_WIDTH(HLS_NEURON_ID_WIDTH),
        .GLOBAL_ID_WIDTH    (GLOBAL_ID_WIDTH),
        .HLS_DIRECT_TILE_COMPAT(HLS_DIRECT_TILE_COMPAT),
        .STRICT_PHYSICAL_ID_INGRESS(STRICT_PHYSICAL_ID_INGRESS)
    ) u_direct_axis_id_decoder (
        .neuron_id          (hls_direct_axis_neuron_id),
        .tvalid             (hls_direct_axis_tvalid),
        .tuser              (hls_direct_axis_tuser),
        .dest_id            (hls_direct_axis_dest_id),
        .explicit_raw       (hls_direct_axis_explicit_raw),
        .explicit_invalid   (hls_direct_axis_explicit_invalid),
        .ingress_invalid    (hls_direct_axis_ingress_invalid),
        .compat_id_in_range (),
        .flagged_raw        (hls_direct_axis_flagged_raw),
        .board_visible_raw  (hls_direct_axis_board_visible_raw),
        .compat_raw         (hls_direct_axis_compat_raw),
        .direct_raw         (hls_direct_axis_raw)
    );
    assign hls_direct_axis_tready = !hls_direct_fifo_full;
    assign hls_direct_axis_push = (HLS_DIRECT_TILE_COMPAT != 0) &
                                  hls_direct_axis_raw &
                                  hls_direct_axis_tvalid &
                                  hls_direct_axis_tready;
    assign hls_direct_scalar_axis_collision =
        hls_snn_enable & hls_direct_raw & hls_spike_out_valid & hls_direct_axis_push;
    assign hls_direct_axis_weight_negative =
        hls_direct_axis_weight[HLS_WEIGHT_WIDTH-1];
    assign hls_direct_axis_weight_abs = hls_direct_axis_weight_negative
        ? ((~hls_direct_axis_weight) + {{(HLS_WEIGHT_WIDTH-1){1'b0}}, 1'b1})
        : hls_direct_axis_weight;
    assign hls_direct_axis_weight_mag =
        hls_direct_axis_weight_abs[WEIGHT_WIDTH-1:0];

    assign hls_direct_push_id = hls_direct_axis_push
        ? hls_direct_axis_dest_id
        : hls_direct_dest_id;
    assign hls_direct_push_weight = hls_direct_axis_push
        ? hls_direct_axis_weight_mag
        : hls_direct_weight_mag;
    assign hls_direct_push_exc = hls_direct_axis_push
        ? ~hls_direct_axis_weight_negative
        : ~hls_direct_weight_negative;

    assign hls_direct_fifo_full = (hls_direct_fifo_count == DIRECT_FIFO_DEPTH);
    assign hls_direct_fifo_empty = (hls_direct_fifo_count == 0);
    assign hls_direct_fifo_push = hls_direct_axis_push | hls_direct_scalar_push;
    assign hls_direct_fifo_head = hls_direct_fifo[hls_direct_fifo_rd_ptr];
    assign hls_direct_pending = !hls_direct_fifo_empty;
    assign hls_direct_pending_id = hls_direct_fifo_head[GLOBAL_ID_WIDTH-1:0];
    assign hls_direct_pending_weight =
        hls_direct_fifo_head[GLOBAL_ID_WIDTH +: WEIGHT_WIDTH];
    assign hls_direct_pending_exc =
        hls_direct_fifo_head[GLOBAL_ID_WIDTH + WEIGHT_WIDTH];
    assign hls_direct_pending_threshold =
        hls_direct_fifo_head[GLOBAL_ID_WIDTH + WEIGHT_WIDTH + 1 +: THRESHOLD_WIDTH];
    assign hls_direct_pending_group_id = hls_direct_pending_id[GLOBAL_ID_WIDTH-1:LOCAL_ID_WIDTH];
    assign hls_direct_pending_local_id = hls_direct_pending_id[LOCAL_ID_WIDTH-1:0];
    assign hls_direct_pending_group_valid =
        hls_direct_pending && (hls_direct_pending_group_id < NUM_GROUPS);
    assign hls_direct_pending_ready = hls_direct_pending_group_valid
        ? grp_in_ready[hls_direct_pending_group_id]
        : 1'b1;
    assign hls_direct_fifo_pop = hls_direct_pending &&
                                 (!hls_direct_pending_group_valid || hls_direct_pending_ready);

    always @(posedge pl_clk) begin
        if (!rst_n_sync || hls_snn_reset) begin
            hls_spike_valid_d       <= 1'b0;
            hls_spike_accepted_d    <= 1'b0;
            hls_spike_nid_d         <= {HLS_NEURON_ID_WIDTH{1'b0}};
            hls_spike_wt_d          <= {HLS_WEIGHT_WIDTH{1'b0}};
            hls_spike_wait_clear    <= 1'b0;
            hls_direct_fifo_wr_ptr  <= {DIRECT_FIFO_PTR_WIDTH{1'b0}};
            hls_direct_fifo_rd_ptr  <= {DIRECT_FIFO_PTR_WIDTH{1'b0}};
            hls_direct_fifo_count   <= {(DIRECT_FIFO_PTR_WIDTH+1){1'b0}};
            hls_direct_axis_accept_count <= 32'd0;
            hls_direct_fifo_push_count   <= 32'd0;
            hls_direct_core_accept_count <= 32'd0;
            hls_direct_axis_scalar_collision_count <= 32'd0;
            hls_direct_axis_invalid_id_count <= 32'd0;
        end else begin
            if (!hls_snn_enable) begin
                hls_spike_valid_d <= 1'b0;
                hls_spike_accepted_d <= 1'b0;
                hls_spike_nid_d   <= {HLS_NEURON_ID_WIDTH{1'b0}};
                hls_spike_wt_d    <= {HLS_WEIGHT_WIDTH{1'b0}};
                hls_spike_wait_clear <= 1'b0;
                hls_direct_fifo_wr_ptr <= {DIRECT_FIFO_PTR_WIDTH{1'b0}};
                hls_direct_fifo_rd_ptr <= {DIRECT_FIFO_PTR_WIDTH{1'b0}};
                hls_direct_fifo_count  <= {(DIRECT_FIFO_PTR_WIDTH+1){1'b0}};
            end else begin
                if (hls_spike_capture_event) begin
                    hls_spike_accepted_d <= 1'b1;
                    hls_spike_nid_d <= hls_spike_out_neuron_id;
                    hls_spike_wt_d <= hls_spike_out_weight;
                    hls_spike_wait_clear <= 1'b1;
                end else if (!hls_spike_out_valid || hls_spike_payload_changed) begin
                    hls_spike_wait_clear <= 1'b0;
                end
            end

            if (hls_direct_fifo_push) begin
                hls_direct_fifo[hls_direct_fifo_wr_ptr] <= {
                    cfg_global_threshold,
                    hls_direct_push_exc,
                    hls_direct_push_weight,
                    hls_direct_push_id
                };
                hls_direct_fifo_wr_ptr <= hls_direct_fifo_wr_ptr + 1'b1;
            end

            if (hls_direct_fifo_pop)
                hls_direct_fifo_rd_ptr <= hls_direct_fifo_rd_ptr + 1'b1;

            case ({hls_direct_fifo_push, hls_direct_fifo_pop})
                2'b10: hls_direct_fifo_count <= hls_direct_fifo_count + 1'b1;
                2'b01: hls_direct_fifo_count <= hls_direct_fifo_count - 1'b1;
                default: hls_direct_fifo_count <= hls_direct_fifo_count;
            endcase

            if (hls_direct_axis_push)
                hls_direct_axis_accept_count <= hls_direct_axis_accept_count + 1'b1;
            if (hls_direct_fifo_push)
                hls_direct_fifo_push_count <= hls_direct_fifo_push_count + 1'b1;
            if (hls_direct_fifo_pop)
                hls_direct_core_accept_count <= hls_direct_core_accept_count + 1'b1;
            if (hls_direct_scalar_axis_collision)
                hls_direct_axis_scalar_collision_count <= hls_direct_axis_scalar_collision_count + 1'b1;
            if ((HLS_DIRECT_TILE_COMPAT != 0) &&
                ((hls_direct_axis_tvalid &&
                  hls_direct_axis_tready &&
                  hls_direct_axis_ingress_invalid) ||
                 hls_scalar_invalid_event))
                hls_direct_axis_invalid_id_count <= hls_direct_axis_invalid_id_count + 1'b1;
        end
    end

    assign router_ext_spike_valid = hls_router_event;
    assign router_ext_spike_id = hls_global_id;
    assign router_ext_spike_weight = hls_weight_truncated;
    assign router_ext_spike_exc = ~hls_spike_weight_negative;

    // Event Router -> HLS output bridge
    // Buffer post-spikes so HLS ready-token stalls do not drop one-cycle
    // learning/output notifications.
    //
    // In direct active-tile compatibility mode, the host-visible output should
    // reflect the physical core that actually fired.  Drain the core output
    // FIFOs directly and keep the event router out of this replay-only path;
    // the router learning notification is delayed by CT traversal and is not a
    // dedicated host-output contract.
    assign router_grp_spike_valid = (HLS_DIRECT_TILE_COMPAT != 0)
        ? {NUM_GROUPS{1'b0}}
        : grp_spike_valid;
    assign router_grp_spike_neuron_id = grp_spike_neuron_id;
    assign grp_spike_ready = (HLS_DIRECT_TILE_COMPAT != 0)
        ? direct_host_spike_ready
        : router_grp_spike_ready;

    integer host_spike_i;
    always @(*) begin
        direct_host_spike_valid = 1'b0;
        direct_host_spike_id = {GLOBAL_ID_WIDTH{1'b0}};
        direct_host_spike_ready = {NUM_GROUPS{1'b0}};
        for (host_spike_i = 0; host_spike_i < NUM_GROUPS; host_spike_i = host_spike_i + 1) begin
            if (!direct_host_spike_valid && grp_spike_valid[host_spike_i]) begin
                direct_host_spike_valid = 1'b1;
                direct_host_spike_ready[host_spike_i] = 1'b1;
                direct_host_spike_id = {
                    host_spike_i[GROUP_ID_WIDTH-1:0],
                    grp_spike_neuron_id[host_spike_i*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH]
                };
            end
        end
    end

    assign host_output_spike_valid_raw = (HLS_DIRECT_TILE_COMPAT != 0)
        ? direct_host_spike_valid
        : learn_spike_valid;
    assign host_output_spike_id_raw = (HLS_DIRECT_TILE_COMPAT != 0)
        ? direct_host_spike_id
        : learn_spike_src_id;
    assign rtl_output_axis_enable = (HLS_DIRECT_TILE_COMPAT != 0);

    // Break the long path from core-group output FIFO read/arbiter logic into
    // the host-output bridge FIFO write-enable.  The HLS-facing output contract
    // is tokenized and frame-oriented, so one cycle of staging is acceptable
    // and makes the 80 MHz route closure deterministic.
    always @(posedge pl_clk) begin
        if (!rst_n_sync || hls_snn_reset || !hls_snn_enable) begin
            host_output_spike_valid_q <= 1'b0;
            host_output_spike_id_q    <= {GLOBAL_ID_WIDTH{1'b0}};
        end else begin
            host_output_spike_valid_q <= host_output_spike_valid_raw;
            if (host_output_spike_valid_raw)
                host_output_spike_id_q <= host_output_spike_id_raw;
        end
    end

    spike_out_bridge #(
        .HLS_NEURON_ID_WIDTH(HLS_NEURON_ID_WIDTH),
        .HLS_MAX_NEURONS    (HLS_MAX_NEURONS),
        .NEURON_ID_WIDTH    (GLOBAL_ID_WIDTH),
        .WEIGHT_WIDTH       (HLS_WEIGHT_WIDTH),
        .FIFO_DEPTH         (256),
        .INPUT_VALID_IS_PULSE(HLS_DIRECT_TILE_COMPAT != 0),
        .OUTPUT_AXIS_ENABLE (HLS_DIRECT_TILE_COMPAT != 0)
    ) u_spike_out_bridge (
        .clk                 (pl_clk),
        .rst_n               (rst_n_sync),
        .enable              (hls_snn_enable),
        .clear               (hls_snn_reset),
        .neuron_spike_valid  (host_output_spike_valid_q),
        .neuron_spike_id     (host_output_spike_id_q),
        .spike_out_ready_token(hls_spike_in_ready),
        .neuron_spike_event  (output_bridge_event),
        .spike_out_valid     (rtl_spike_out_valid),
        .spike_out_neuron_id (rtl_spike_out_neuron_id),
        .spike_out_weight    (rtl_spike_out_weight),
        .m_axis_tdata        (rtl_spike_axis_tdata),
        .m_axis_tkeep        (rtl_spike_axis_tkeep),
        .m_axis_tstrb        (rtl_spike_axis_tstrb),
        .m_axis_tvalid       (rtl_spike_axis_tvalid),
        .m_axis_tlast        (rtl_spike_axis_tlast),
        .m_axis_tready       (rtl_spike_axis_tready),
        .m_axis_tid          (rtl_spike_axis_tid),
        .m_axis_tdest        (rtl_spike_axis_tdest),
        .m_axis_tuser        (rtl_spike_axis_tuser),
        .fifo_overflow       (output_bridge_overflow),
        .fifo_level          (output_bridge_fifo_level),
        .output_event_count  (output_bridge_event_count),
        .output_emit_count   (output_bridge_emit_count),
        .output_drop_count   (output_bridge_drop_count)
    );

    assign rtl_learn_weight_ready = LEARN_WEIGHT_BRIDGE_ENABLE ? learn_weight_ready_br : 1'b0;
    assign learn_spike_ready      = 1'b1;

    // HLS ready/busy
    assign rtl_spike_in_ready = hls_spike_capture_ready;
    assign rtl_snn_ready      = !router_busy &
                                (grp_busy == {NUM_GROUPS{1'b0}}) &
                                hls_direct_fifo_empty;
    assign rtl_snn_busy       = router_busy |
                                (grp_busy != {NUM_GROUPS{1'b0}}) |
                                !hls_direct_fifo_empty;
    assign output_drain_busy  = !hls_direct_fifo_empty |
                                (output_bridge_fifo_level != 32'd0) |
                                rtl_spike_axis_tvalid;

    always @(posedge pl_clk) begin
        if (!rst_n_sync || hls_snn_reset) begin
            service_cycles_counter <= 32'd0;
            pl_busy_cycles_counter <= 32'd0;
            output_drain_cycles_counter <= 32'd0;
        end else begin
            if (hls_snn_enable && rtl_snn_busy) begin
                if (service_cycles_counter != 32'hFFFFFFFF) begin
                    service_cycles_counter <= service_cycles_counter + 32'd1;
                end
                if (pl_busy_cycles_counter != 32'hFFFFFFFF) begin
                    pl_busy_cycles_counter <= pl_busy_cycles_counter + 32'd1;
                end
            end
            if (hls_snn_enable && output_drain_busy && output_drain_cycles_counter != 32'hFFFFFFFF) begin
                output_drain_cycles_counter <= output_drain_cycles_counter + 32'd1;
            end
        end
    end

    genvar dg;
    generate
        for (dg = 0; dg < NUM_GROUPS; dg = dg + 1) begin : gen_direct_input_mux
            wire direct_to_group = hls_direct_pending_group_valid &&
                                   (hls_direct_pending_group_id == dg[GROUP_ID_WIDTH-1:0]);

            assign grp_in_valid[dg] = direct_to_group ? 1'b1 : router_grp_in_valid[dg];
            assign grp_in_dest_id[dg*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH] =
                direct_to_group ? hls_direct_pending_local_id :
                                  router_grp_in_dest_id[dg*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH];
            assign grp_in_weight[dg*WEIGHT_WIDTH +: WEIGHT_WIDTH] =
                direct_to_group ? hls_direct_pending_weight :
                                  router_grp_in_weight[dg*WEIGHT_WIDTH +: WEIGHT_WIDTH];
            assign grp_in_exc[dg] = direct_to_group ? hls_direct_pending_exc :
                                                      router_grp_in_exc[dg];
            assign grp_in_threshold[dg*THRESHOLD_WIDTH +: THRESHOLD_WIDTH] =
                direct_to_group ? hls_direct_pending_threshold :
                                  cfg_global_threshold;
            assign router_grp_in_ready[dg] = direct_to_group ? 1'b0 : grp_in_ready[dg];
        end
    endgenerate

    //=========================================================================
    // Core Group Instantiations
    //=========================================================================
    // Each group has its own NEURONS_PER_GROUP from SNN_GROUP_SIZE_x defines.
    // All groups share the same LOCAL_ID_WIDTH (= clog2(max(group_sizes)))
    // for uniform interconnect bus widths.
    //
    // Default: 16 × 128 = 2048 neurons (all groups identical).
    // Variable: configure group_sizes in snn_params.yaml for mixed sizes.
    //=========================================================================

    // Mux write enable: AXI config writes OR event router weight updates
    wire [NUM_GROUPS-1:0]     combined_weight_we;
    wire [LOCAL_ID_WIDTH-1:0] combined_weight_src [0:NUM_GROUPS-1];
    wire [LOCAL_ID_WIDTH-1:0] combined_weight_dst [0:NUM_GROUPS-1];
    wire [WEIGHT_WIDTH-1:0]   combined_weight_data[0:NUM_GROUPS-1];
    wire                      combined_weight_exc [0:NUM_GROUPS-1];

    genvar g;
    generate
        for (g = 0; g < NUM_GROUPS; g = g + 1) begin : gen_weight_mux
            // AXI config has priority over router weight updates
            assign combined_weight_we[g]   = intra_weight_we_reg[g] | grp_weight_we[g];
            assign combined_weight_src[g]  = intra_weight_we_reg[g] ?
                                             intra_weight_src_reg : grp_weight_src;
            assign combined_weight_dst[g]  = intra_weight_we_reg[g] ?
                                             intra_weight_dst_reg : grp_weight_dst;
            assign combined_weight_data[g] = intra_weight_we_reg[g] ?
                                             intra_weight_data_reg : grp_weight_data;
            assign combined_weight_exc[g]  = intra_weight_we_reg[g] ?
                                             intra_weight_exc_reg : grp_weight_exc;
        end
    endgenerate

    generate
        for (g = 0; g < NUM_GROUPS; g = g + 1) begin : gen_core_groups

            // Per-group neuron count: maps genvar g → SNN_GROUP_SIZE_x define.
            // All groups use uniform LOCAL_ID_WIDTH for bus compatibility.
            localparam THIS_NPG =
                (g ==  0) ? `SNN_GROUP_SIZE_0  :
                (g ==  1) ? `SNN_GROUP_SIZE_1  :
                (g ==  2) ? `SNN_GROUP_SIZE_2  :
                (g ==  3) ? `SNN_GROUP_SIZE_3  :
                (g ==  4) ? `SNN_GROUP_SIZE_4  :
                (g ==  5) ? `SNN_GROUP_SIZE_5  :
                (g ==  6) ? `SNN_GROUP_SIZE_6  :
                (g ==  7) ? `SNN_GROUP_SIZE_7  :
                (g ==  8) ? `SNN_GROUP_SIZE_8  :
                (g ==  9) ? `SNN_GROUP_SIZE_9  :
                (g == 10) ? `SNN_GROUP_SIZE_10 :
                (g == 11) ? `SNN_GROUP_SIZE_11 :
                (g == 12) ? `SNN_GROUP_SIZE_12 :
                (g == 13) ? `SNN_GROUP_SIZE_13 :
                (g == 14) ? `SNN_GROUP_SIZE_14 :
                            `SNN_GROUP_SIZE_15 ;

            core_group #(
                .GROUP_ID           (g),
                .NEURONS_PER_GROUP  (THIS_NPG),
                .LOCAL_ID_WIDTH     (LOCAL_ID_WIDTH),
                .DATA_WIDTH         (DATA_WIDTH),
                .WEIGHT_WIDTH       (WEIGHT_WIDTH),
                .THRESHOLD_WIDTH    (THRESHOLD_WIDTH),
                .LEAK_WIDTH         (LEAK_WIDTH),
                .REFRAC_WIDTH       (REFRAC_WIDTH),
                .SPIKE_BUFFER_DEPTH (SPIKE_BUFFER_DEPTH),
                .ENABLE_INTRA_RECURRENCE(HLS_DIRECT_TILE_COMPAT ? 0 : 1)
            ) u_core_group (
                .clk                (pl_clk),
                .rst_n              (rst_n_sync & ~hls_snn_reset),
                .enable             (hls_snn_enable),

                // External spike input (from event router)
                .ext_spike_valid    (grp_in_valid[g]),
                .ext_spike_dest_id  (grp_in_dest_id[g*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH]),
                .ext_spike_weight   (grp_in_weight[g*WEIGHT_WIDTH +: WEIGHT_WIDTH]),
                .ext_spike_exc_inh  (grp_in_exc[g]),
                .ext_spike_threshold(grp_in_threshold[g*THRESHOLD_WIDTH +: THRESHOLD_WIDTH]),
                .ext_spike_ready    (grp_in_ready[g]),

                // Output spike (to event router)
                .out_spike_valid    (grp_spike_valid[g]),
                .out_spike_neuron_id(grp_spike_neuron_id[g*LOCAL_ID_WIDTH +: LOCAL_ID_WIDTH]),
                .out_spike_ready    (grp_spike_ready[g]),

                // Global neuron parameters
                .global_threshold   (cfg_global_threshold),
                .global_leak_rate   (cfg_global_leak_rate),
                .global_refrac_period(cfg_global_refrac_period),
                .accumulate_only    (cfg_accumulate_only),
                .commit_start       (cfg_commit_start_pulse & cfg_commit_group_mask[g]),
                .commit_threshold   (cfg_global_threshold),
                .commit_busy        (grp_commit_busy[g]),
                .commit_done        (grp_commit_done[g]),
                .clear_start        (cfg_clear_start_pulse & cfg_clear_group_mask[g]),
                .clear_busy         (grp_clear_busy[g]),
                .clear_done         (grp_clear_done[g]),

                // Weight load (combined from AXI config + learning engine)
                .weight_we          (combined_weight_we[g]),
                .weight_src_id      (combined_weight_src[g]),
                .weight_dst_id      (combined_weight_dst[g]),
                .weight_data        (combined_weight_data[g]),
                .weight_exc         (combined_weight_exc[g]),

                // Status
                .spike_count        (grp_spike_count[g*16 +: 16]),
                .group_busy         (grp_busy[g])
            );
        end
    endgenerate

    //=========================================================================
    // Synaptic Connectivity Table (Inter-Group Connections)
    //=========================================================================

    // Mux: AXI config writes OR event router config writes
    wire                          ct_cfg_we_mux;
    wire [GROUP_ID_WIDTH-1:0]     ct_cfg_src_group_mux;
    wire [LOCAL_ID_WIDTH-1:0]     ct_cfg_src_neuron_mux;
    wire [FANOUT_IDX_WIDTH-1:0]   ct_cfg_fanout_idx_mux;
    wire                          ct_cfg_valid_mux;
    wire [GROUP_ID_WIDTH-1:0]     ct_cfg_dst_group_mux;
    wire [LOCAL_ID_WIDTH-1:0]     ct_cfg_dst_neuron_mux;
    wire [WEIGHT_WIDTH-1:0]       ct_cfg_weight_mux;
    wire                          ct_cfg_exc_inh_mux;

    // AXI config has priority
    assign ct_cfg_we_mux         = ct_cfg_we_reg | ct_cfg_we;
    assign ct_cfg_src_group_mux  = ct_cfg_we_reg ? ct_cfg_src_group_reg  : ct_cfg_src_group;
    assign ct_cfg_src_neuron_mux = ct_cfg_we_reg ? ct_cfg_src_neuron_reg : ct_cfg_src_neuron;
    assign ct_cfg_fanout_idx_mux = ct_cfg_we_reg ? ct_cfg_fanout_idx_reg : ct_cfg_fanout_idx;
    assign ct_cfg_valid_mux      = ct_cfg_we_reg ? ct_cfg_valid_reg      : ct_cfg_valid_bit;
    assign ct_cfg_dst_group_mux  = ct_cfg_we_reg ? ct_cfg_dst_group_reg  : ct_cfg_dst_group;
    assign ct_cfg_dst_neuron_mux = ct_cfg_we_reg ? ct_cfg_dst_neuron_reg : ct_cfg_dst_neuron;
    assign ct_cfg_weight_mux     = ct_cfg_we_reg ? ct_cfg_weight_reg     : ct_cfg_weight;
    assign ct_cfg_exc_inh_mux    = ct_cfg_we_reg ? ct_cfg_exc_inh_reg    : ct_cfg_exc_inh;

    synaptic_connectivity_table #(
        .NUM_GROUPS         (NUM_GROUPS),
        .NEURONS_PER_GROUP  (NEURONS_PER_GROUP),
        .WEIGHT_WIDTH       (WEIGHT_WIDTH),
        .MAX_FANOUT_INTER   (MAX_FANOUT_INTER)
    ) u_connectivity_table (
        .clk                (pl_clk),
        .rst_n              (rst_n_sync & ~hls_snn_reset),

        // Write port (config)
        .cfg_we             (ct_cfg_we_mux),
        .cfg_src_group      (ct_cfg_src_group_mux),
        .cfg_src_neuron     (ct_cfg_src_neuron_mux),
        .cfg_fanout_idx     (ct_cfg_fanout_idx_mux),
        .cfg_valid          (ct_cfg_valid_mux),
        .cfg_dst_group      (ct_cfg_dst_group_mux),
        .cfg_dst_neuron     (ct_cfg_dst_neuron_mux),
        .cfg_weight         (ct_cfg_weight_mux),
        .cfg_exc_inh        (ct_cfg_exc_inh_mux),
        .route_clear_start  (route_clear_start_reg),

        // Lookup port (from event router)
        .lookup_en          (ct_lookup_en),
        .lookup_src_group   (ct_lookup_src_group),
        .lookup_src_neuron  (ct_lookup_src_neuron),
        .lookup_fanout_idx  (ct_lookup_fanout_idx),

        // Lookup result
        .result_valid       (ct_result_valid),
        .result_dst_group   (ct_result_dst_group),
        .result_dst_neuron  (ct_result_dst_neuron),
        .result_weight      (ct_result_weight),
        .result_exc_inh     (ct_result_exc_inh),
        .result_entry_valid (ct_result_entry_valid),
        .route_clear_busy   (route_clear_busy),
        .route_clear_done   (route_clear_done),
        .route_entry_count  (route_entry_count),
        .route_checksum     (route_checksum),
        .route_write_error_count(route_write_error_count)
    );

    //=========================================================================
    // Event Router (Next-Gen) - Central Spike Routing Hub
    //=========================================================================

    event_router_ng #(
        .NUM_GROUPS         (NUM_GROUPS),
        .NEURONS_PER_GROUP  (NEURONS_PER_GROUP),
        .WEIGHT_WIDTH       (WEIGHT_WIDTH),
        .MAX_FANOUT_INTER   (MAX_FANOUT_INTER),
        .LEARN_NOTIFY_ENABLE(LEARN_NOTIFY_ENABLE)
    ) u_event_router (
        .clk                (pl_clk),
        .rst_n              (rst_n_sync & ~hls_snn_reset),
        .enable             (hls_snn_enable),

        // Core group spike outputs (FROM groups)
        .grp_spike_valid    (router_grp_spike_valid),
        .grp_spike_neuron_id(router_grp_spike_neuron_id),
        .grp_spike_ready    (router_grp_spike_ready),

        // Core group spike inputs (TO groups)
        .grp_in_valid       (router_grp_in_valid),
        .grp_in_dest_id     (router_grp_in_dest_id),
        .grp_in_weight      (router_grp_in_weight),
        .grp_in_exc         (router_grp_in_exc),
        .grp_in_ready       (router_grp_in_ready),

        // External spike input (from HLS)
        .ext_spike_valid    (router_ext_spike_valid),
        .ext_spike_neuron_id(router_ext_spike_id),
        .ext_spike_weight   (router_ext_spike_weight),
        .ext_spike_exc      (router_ext_spike_exc),
        .ext_spike_ready    (router_ext_spike_ready),

        // Learning engine observation
        .learn_spike_valid  (learn_spike_valid),
        .learn_spike_src_id (learn_spike_src_id),
        .learn_spike_ready  (learn_spike_ready),

        // Learning weight update (HLS -> Event Router bridge)
        .learn_weight_valid     (learn_weight_valid_br),
        .learn_weight_group     (learn_weight_group_br),
        .learn_weight_src       (learn_weight_src_br),
        .learn_weight_dst       (learn_weight_dst_br),
        .learn_weight_data      (learn_weight_data_br),
        .learn_weight_exc       (learn_weight_exc_br),
        .learn_weight_is_inter  (learn_weight_is_inter_br),
        .learn_weight_dst_group (learn_weight_dst_group_br),
        .learn_weight_fanout_idx(learn_weight_fanout_idx_br),
        .learn_weight_ready     (learn_weight_ready_br),

        // Connectivity table interface
        .ct_lookup_en       (ct_lookup_en),
        .ct_lookup_src_group(ct_lookup_src_group),
        .ct_lookup_src_neuron(ct_lookup_src_neuron),
        .ct_lookup_fanout_idx(ct_lookup_fanout_idx),

        .ct_result_valid    (ct_result_valid),
        .ct_result_dst_group(ct_result_dst_group),
        .ct_result_dst_neuron(ct_result_dst_neuron),
        .ct_result_weight   (ct_result_weight),
        .ct_result_exc_inh  (ct_result_exc_inh),
        .ct_result_entry_valid(ct_result_entry_valid),

        // Weight config passthrough
        .grp_weight_we      (grp_weight_we),
        .grp_weight_src     (grp_weight_src),
        .grp_weight_dst     (grp_weight_dst),
        .grp_weight_data    (grp_weight_data),
        .grp_weight_exc     (grp_weight_exc),

        // CT config passthrough
        .ct_cfg_we          (ct_cfg_we),
        .ct_cfg_src_group   (ct_cfg_src_group),
        .ct_cfg_src_neuron  (ct_cfg_src_neuron),
        .ct_cfg_fanout_idx  (ct_cfg_fanout_idx),
        .ct_cfg_valid       (ct_cfg_valid_bit),
        .ct_cfg_dst_group   (ct_cfg_dst_group),
        .ct_cfg_dst_neuron  (ct_cfg_dst_neuron),
        .ct_cfg_weight      (ct_cfg_weight),
        .ct_cfg_exc_inh     (ct_cfg_exc_inh),

        // Status
        .routed_spike_count (routed_spike_count),
        .router_ext_invalid_group_count(router_ext_invalid_group_count),
        .router_ct_invalid_entry_count(router_ct_invalid_entry_count),
        .router_ct_invalid_dst_count(router_ct_invalid_dst_count),
        .router_fanout_scan_count(router_fanout_scan_count),
        .router_route_miss_count(router_route_miss_count),
        .router_backpressure_stall_count(router_backpressure_stall_count),
        .router_busy        (router_busy)
    );

endmodule
