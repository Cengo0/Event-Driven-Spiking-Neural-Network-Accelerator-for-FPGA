//-----------------------------------------------------------------------------
// Title         : Integrated SpikeMold Top (BD Wrapper + RTL)
// Project       : PYNQ-Z2 SpikeMold
// File          : spikemold_integrated_top.v
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : Top-level wrapper connecting Block Design (PS + HLS + DMA +
//                 Config Regs) to RTL spike_router and lif_neuron_array.
//                 DDR/FIXED_IO are internal to the BD.
//
//                 Key fixes:
//                 1. Direct DMA0 AXI-stream spike ingress into the RTL event
//                    router. HLS stays on the control/config path.
//                 2. FIFO bridge on RTL neuron output to DMA0 S2MM with TLAST
//                    per event packet.
//
//                 SpikePress population note (Phase 6.5):
//                 The SpikePress projection topology is handled
//                 entirely in HLS weight_memory (flat buffer) and Python host.
//                 The RTL spike_router uses a generic config-based conn_memory
//                 that is population-agnostic. The Python host generates the
//                 routing table entries from SpikePress projections.
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps

module spikemold_integrated_top #(
    parameter NUM_NEURONS           = 1024,
    parameter NUM_AXONS             = 1024,
    parameter NUM_PARALLEL_UNITS    = 4,
    parameter SPIKE_BUFFER_DEPTH    = 64,
    parameter HLS_NEURON_ID_WIDTH   = 11,
    parameter HLS_MAX_NEURONS       = NUM_NEURONS,
    parameter NEURON_ID_WIDTH       = 10,
    parameter AXON_ID_WIDTH         = 10,
    parameter DATA_WIDTH            = 16,
    parameter WEIGHT_WIDTH          = 8,
    parameter LEAK_WIDTH            = 8,
    parameter THRESHOLD_WIDTH       = 16,
    parameter REFRAC_WIDTH          = 8,
    parameter ROUTER_BUFFER_DEPTH   = 512
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
    // BD <-> RTL Interconnect Signals
    //=========================================================================
    wire        clk;
    wire [0:0]  rst_n_vec;
    wire        rst_n;

    // HLS -> RTL spike (legacy ap_none outputs from BD)
    wire [0:0]  bd_spike_in_valid;
    wire [HLS_NEURON_ID_WIDTH-1:0]  bd_spike_in_neuron_id;
    wire [7:0]  bd_spike_in_weight;
    wire        bd_spike_in_ready;

    // RTL -> HLS spike (ap_none inputs to BD)
    wire        bd_spike_out_valid;
    wire [HLS_NEURON_ID_WIDTH-1:0]  bd_spike_out_neuron_id;
    wire [7:0]  bd_spike_out_weight;
    wire [0:0]  bd_spike_out_ready;

    // DMA0 direct spike AXI-stream ports exposed from BD.
    wire [31:0] bd_dma_spike_in_tdata;
    wire [3:0]  bd_dma_spike_in_tkeep;
    wire        bd_dma_spike_in_tlast;
    wire        bd_dma_spike_in_tvalid;
    wire        bd_dma_spike_in_tready;
    wire [31:0] bd_dma_spike_out_tdata;
    wire [3:0]  bd_dma_spike_out_tkeep;
    wire        bd_dma_spike_out_tlast;
    wire        bd_dma_spike_out_tvalid;
    wire        bd_dma_spike_out_tready;

    // SpikeMold Control
    wire [0:0]  bd_spikemold_enable;
    wire [0:0]  bd_spikemold_reset;
    wire        bd_spikemold_ready;
    wire        bd_spikemold_busy;

    // Config
    wire        cfg_router_config_we;
    wire [31:0] cfg_router_config_addr;
    wire [31:0] cfg_router_config_wdata;
    wire [31:0] cfg_router_config_rdata;
    wire        cfg_neuron_config_we;
    wire [9:0]  cfg_neuron_config_addr;
    wire [31:0] cfg_neuron_config_wdata;
    wire [15:0] cfg_global_threshold;
    wire [7:0]  cfg_global_leak_rate;
    wire [7:0]  cfg_global_refrac_period;
    wire [1:0]  cfg_backend_mode;

    // Status
    wire [31:0] router_spike_count;
    wire [31:0] flat_router_spike_count;
    wire [31:0] neuron_spike_count;
    wire [31:0] flat_neuron_spike_count;
    wire        fifo_overflow;
    wire        flat_fifo_overflow;
    wire [7:0]  active_neurons;
    wire [7:0]  flat_active_neurons;
    wire [31:0] cfg_throughput_counter;
    wire [31:0] cfg_service_cycles_counter;
    wire [31:0] cfg_pl_busy_cycles_counter;
    wire [31:0] cfg_output_drain_cycles_counter;
    wire [31:0] cfg_output_bridge_status;
    wire [31:0] cfg_output_bridge_drop_count;
    wire [31:0] cfg_output_bridge_event_count;
    wire [31:0] cfg_output_bridge_emit_count;
    wire [31:0] neuron_throughput_counter;
    wire [31:0] neuron_state_checksum;
    wire [31:0] flat_neuron_state_checksum;
    wire [15:0] threshold_out;
    wire [15:0] leak_rate_out;
    wire [0:0]  debug_reserved_zero;

    // Router config command queue
    localparam ROUTER_CFG_CMD_FIFO_DEPTH = 16;
    wire        router_cfg_cmd_fifo_full;
    wire        router_cfg_cmd_fifo_empty;
    wire        router_cfg_cmd_fifo_almost_full;
    wire        router_cfg_cmd_fifo_almost_empty;
    wire [64-1:0] router_cfg_cmd_fifo_rd_data;
    wire [$clog2(ROUTER_CFG_CMD_FIFO_DEPTH):0] router_cfg_cmd_fifo_count;
    wire        router_cfg_cmd_fifo_overflow;
    wire        router_cfg_cmd_fifo_underflow;
    wire        router_cfg_cmd_fifo_rd_en;
    reg         router_cfg_cmd_pop_pending;
    reg         router_cfg_cmd_valid;
    reg  [31:0] router_cfg_cmd_addr;
    reg  [31:0] router_cfg_cmd_data;

    // Router internal
    wire                       router_spike_valid;
    wire [NEURON_ID_WIDTH-1:0] router_spike_dest_id;
    wire [WEIGHT_WIDTH-1:0]    router_spike_weight;
    wire                       router_spike_exc_inh;
    wire                       router_spike_ready;
    wire                       router_input_valid;
    wire [NEURON_ID_WIDTH-1:0] router_input_neuron_id;
    wire                       router_input_ready;
    wire                       spike_in_in_router_range;

    // Neuron output
    wire                       neuron_spike_valid;
    wire [NEURON_ID_WIDTH-1:0] neuron_spike_id;
    wire [DATA_WIDTH-1:0]      neuron_spike_value;
    wire                       neuron_spike_ready_wire;
    wire                       router_busy;
    wire                       neuron_array_busy;
    wire                       flat_backend_mode;
    wire                       eventconv_backend_mode;

    // Tiny EventConv smoke backend: one 3x3/2x2 shared-kernel primitive.
    localparam [1:0] BACKEND_MODE_FLAT      = 2'd0;
    localparam [1:0] BACKEND_MODE_EVENTCONV = 2'd1;
    localparam EVENTCONV_KERNEL_SIZE        = 2;
    localparam EVENTCONV_INPUT_WIDTH        = 3;
    localparam EVENTCONV_INPUT_HEIGHT       = 3;
    localparam EVENTCONV_NUM_CHANNELS       = 1;
    localparam EVENTCONV_OUTPUT_CHANNELS    = 1;
    localparam EVENTCONV_STATE_COUNT        = 4;
    localparam EVENTCONV_STATE_WIDTH        = 16;
    localparam EVENTCONV_DEST_ID_WIDTH      = 16;
    localparam EVENTCONV_KERNEL_WORDS =
        EVENTCONV_KERNEL_SIZE * EVENTCONV_KERNEL_SIZE *
        EVENTCONV_NUM_CHANNELS * EVENTCONV_OUTPUT_CHANNELS;

    wire eventconv_enable;
    wire eventconv_clear;
    wire eventconv_input_tready;
    wire eventconv_input_fire;
    wire eventconv_update_tvalid;
    wire eventconv_update_tready;
    wire [31:0] eventconv_update_tdata;
    wire signed [7:0] eventconv_update_weight;
    wire [7:0] eventconv_kernel_weight_out;
    wire [(EVENTCONV_KERNEL_WORDS*8)-1:0] eventconv_kernel_weight_flat;
    wire [31:0] eventconv_spikes_processed;
    wire [31:0] eventconv_updates_generated;
    wire [31:0] eventconv_address_errors;
    wire [(EVENTCONV_STATE_COUNT*EVENTCONV_STATE_WIDTH)-1:0] eventconv_state_flat;
    wire [(EVENTCONV_STATE_COUNT*EVENTCONV_DEST_ID_WIDTH)-1:0] eventconv_active_id_flat;
    wire [EVENTCONV_STATE_COUNT-1:0] eventconv_active_mask;
    wire [31:0] eventconv_active_neuron_count;
    wire [31:0] eventconv_state_read_count;
    wire [31:0] eventconv_state_write_count;
    wire [31:0] eventconv_update_count;
    wire [31:0] eventconv_commit_reset_count;
    wire [31:0] eventconv_invalid_dest_count;
    wire signed [31:0] eventconv_state_checksum;
    reg  eventconv_commit_start;
    wire eventconv_commit_busy;
    wire eventconv_commit_done;
    wire eventconv_commit_tvalid;
    wire [31:0] eventconv_commit_tdata;
    wire eventconv_commit_tready;
    wire eventconv_reset_tvalid;
    wire [EVENTCONV_DEST_ID_WIDTH-1:0] eventconv_reset_tdest;
    wire eventconv_reset_tready;
    wire [31:0] eventconv_active_commit_read_count;
    wire [31:0] eventconv_commit_emit_count;
    wire [31:0] eventconv_full_scan_count;
    wire signed [31:0] eventconv_readout_checksum;
    wire [31:0] eventconv_output_backpressure_cycle_count;
    reg  eventconv_input_seen;
    reg  eventconv_packet_done;
    reg  eventconv_commit_started;
    reg  eventconv_commit_done_latched;
    wire eventconv_run_busy;

    assign rst_n = rst_n_vec[0];
    assign flat_backend_mode = (cfg_backend_mode == BACKEND_MODE_FLAT);
    assign eventconv_backend_mode = (cfg_backend_mode == BACKEND_MODE_EVENTCONV);
    assign eventconv_enable = bd_spikemold_enable[0] & eventconv_backend_mode;
    assign eventconv_clear = !eventconv_backend_mode;
    //=========================================================================
    // Block Design Instantiation
    //=========================================================================
    design_1_wrapper u_block_design (
        // DDR Interface
        .DDR_addr            (DDR_addr),
        .DDR_ba              (DDR_ba),
        .DDR_cas_n           (DDR_cas_n),
        .DDR_ck_n            (DDR_ck_n),
        .DDR_ck_p            (DDR_ck_p),
        .DDR_cke             (DDR_cke),
        .DDR_cs_n            (DDR_cs_n),
        .DDR_dm              (DDR_dm),
        .DDR_dq              (DDR_dq),
        .DDR_dqs_n           (DDR_dqs_n),
        .DDR_dqs_p           (DDR_dqs_p),
        .DDR_odt             (DDR_odt),
        .DDR_ras_n           (DDR_ras_n),
        .DDR_reset_n         (DDR_reset_n),
        .DDR_we_n            (DDR_we_n),
        // Fixed IO
        .FIXED_IO_ddr_vrn    (FIXED_IO_ddr_vrn),
        .FIXED_IO_ddr_vrp    (FIXED_IO_ddr_vrp),
        .FIXED_IO_mio        (FIXED_IO_mio),
        .FIXED_IO_ps_clk     (FIXED_IO_ps_clk),
        .FIXED_IO_ps_porb    (FIXED_IO_ps_porb),
        .FIXED_IO_ps_srstb   (FIXED_IO_ps_srstb),
        // Clock/Reset
        .clk_100mhz             (clk),
        .rst_n_sync              (rst_n_vec),
        .debug_reserved_zero     (debug_reserved_zero),

        // HLS -> RTL spike (BD port names match HLS ap_none ports)
        .spike_in_valid          (bd_spike_in_valid),
        .spike_in_neuron_id      (bd_spike_in_neuron_id),
        .spike_in_weight         (bd_spike_in_weight),
        .spike_in_ready          (bd_spike_in_ready),

        // RTL -> HLS spike
        .spike_out_valid         (bd_spike_out_valid),
        .spike_out_neuron_id     (bd_spike_out_neuron_id),
        .spike_out_weight        (bd_spike_out_weight),
        .spike_out_ready         (bd_spike_out_ready),

        // DMA0 direct spike AXI-stream.
        .dma_spike_in_tdata      (bd_dma_spike_in_tdata),
        .dma_spike_in_tkeep      (bd_dma_spike_in_tkeep),
        .dma_spike_in_tlast      (bd_dma_spike_in_tlast),
        .dma_spike_in_tvalid     (bd_dma_spike_in_tvalid),
        .dma_spike_in_tready     (bd_dma_spike_in_tready),
        .dma_spike_out_tdata     (bd_dma_spike_out_tdata),
        .dma_spike_out_tkeep     (bd_dma_spike_out_tkeep),
        .dma_spike_out_tlast     (bd_dma_spike_out_tlast),
        .dma_spike_out_tvalid    (bd_dma_spike_out_tvalid),
        .dma_spike_out_tready    (bd_dma_spike_out_tready),

        // SpikeMold Control
        .spikemold_enable              (bd_spikemold_enable),
        .spikemold_reset               (bd_spikemold_reset),
        .spikemold_ready               (bd_spikemold_ready),
        .spikemold_busy                (bd_spikemold_busy),

        // Monitoring
        .threshold_out           (threshold_out),
        .leak_rate_out           (leak_rate_out),

        // Config
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
        .cfg_backend_mode        (cfg_backend_mode),

        // Status feedback
        .cfg_router_spike_count  (router_spike_count),
        .cfg_neuron_spike_count  (neuron_spike_count),
        .cfg_fifo_overflow       (fifo_overflow),
        .cfg_active_neurons      (active_neurons),
        .cfg_throughput_counter  (cfg_throughput_counter),
        .cfg_service_cycles_counter(cfg_service_cycles_counter),
        .cfg_pl_busy_cycles_counter(cfg_pl_busy_cycles_counter),
        .cfg_output_drain_cycles_counter(cfg_output_drain_cycles_counter),
        .cfg_output_bridge_status(cfg_output_bridge_status),
        .cfg_output_bridge_drop_count(cfg_output_bridge_drop_count),
        .cfg_output_bridge_event_count(cfg_output_bridge_event_count),
        .cfg_output_bridge_emit_count(cfg_output_bridge_emit_count),
        .cfg_state_checksum     (neuron_state_checksum)
    );

    //=========================================================================
    // DMA0 AXI-Stream input bridge
    // Input packet format follows SpikePress/HLS AER words:
    //   [12:0] id, [20:13] weight, [31:21] timestamp.
    // Direct RTL output packet format is a post-spike commit word:
    //   [12:0] id, [28:13] commit_value, [31:29] zero.
    // The router consumes source ID only; route weights come from conn_memory.
    //=========================================================================
    localparam SPIKE_AXIS_ID_WIDTH  = 13;
    localparam SPIKE_AXIS_WEIGHT_LO = SPIKE_AXIS_ID_WIDTH;
    localparam SPIKE_AXIS_WEIGHT_HI = SPIKE_AXIS_ID_WIDTH + WEIGHT_WIDTH - 1;
    localparam SPIKE_AXIS_VALUE_LO  = SPIKE_AXIS_ID_WIDTH;
    localparam SPIKE_AXIS_VALUE_HI  = SPIKE_AXIS_ID_WIDTH + DATA_WIDTH - 1;

    wire [SPIKE_AXIS_ID_WIDTH-1:0]   axis_spike_in_id =
        bd_dma_spike_in_tdata[SPIKE_AXIS_ID_WIDTH-1:0];
    wire [WEIGHT_WIDTH-1:0]          axis_spike_in_weight =
        bd_dma_spike_in_tdata[SPIKE_AXIS_WEIGHT_HI:SPIKE_AXIS_WEIGHT_LO];
    wire                             axis_spike_in_fire;
    reg                              axis_spike_pending;
    reg  [SPIKE_AXIS_ID_WIDTH-1:0]   axis_spike_pending_id;
    reg  [WEIGHT_WIDTH-1:0]          axis_spike_pending_wt;
    reg  [31:0]                      axis_valid_seen_count;
    reg  [31:0]                      axis_event_seen_count;
    reg  [31:0]                      axis_router_accept_count;
    reg  [31:0]                      axis_pending_drop_count;
    wire                             axis_spike_accept_event;
    wire                             axis_spike_can_capture;

    always @(posedge clk) begin
        if (!rst_n || bd_spikemold_reset[0]) begin
            axis_spike_pending       <= 1'b0;
            axis_spike_pending_id    <= {SPIKE_AXIS_ID_WIDTH{1'b0}};
            axis_spike_pending_wt    <= {WEIGHT_WIDTH{1'b0}};
            axis_valid_seen_count    <= 32'd0;
            axis_event_seen_count    <= 32'd0;
            axis_router_accept_count <= 32'd0;
            axis_pending_drop_count  <= 32'd0;
        end else if (!bd_spikemold_enable[0]) begin
            axis_spike_pending <= 1'b0;
        end else begin
            if (bd_dma_spike_in_tvalid) begin
                if (axis_valid_seen_count != 32'hFFFFFFFF) begin
                    axis_valid_seen_count <= axis_valid_seen_count + 1'b1;
                end
            end

            if (axis_spike_accept_event) begin
                axis_spike_pending <= 1'b0;
                if (axis_router_accept_count != 32'hFFFFFFFF) begin
                    axis_router_accept_count <= axis_router_accept_count + 1'b1;
                end
            end

            if (axis_spike_in_fire) begin
                if (axis_event_seen_count != 32'hFFFFFFFF) begin
                    axis_event_seen_count <= axis_event_seen_count + 1'b1;
                end
                if (axis_spike_can_capture) begin
                    axis_spike_pending    <= 1'b1;
                    axis_spike_pending_id <= axis_spike_in_id;
                    axis_spike_pending_wt <= axis_spike_in_weight;
                end else if (axis_pending_drop_count != 32'hFFFFFFFF) begin
                    axis_pending_drop_count <= axis_pending_drop_count + 1'b1;
                end
            end
        end
    end

    assign axis_spike_accept_event = axis_spike_pending & router_input_ready;
    assign axis_spike_can_capture = !axis_spike_pending | axis_spike_accept_event;
    assign bd_dma_spike_in_tready = eventconv_backend_mode
                                    ? eventconv_input_tready
                                    : (bd_spikemold_enable[0] & axis_spike_can_capture);
    assign axis_spike_in_fire = flat_backend_mode & bd_dma_spike_in_tvalid & bd_dma_spike_in_tready;
    assign eventconv_input_fire = eventconv_backend_mode & bd_dma_spike_in_tvalid & bd_dma_spike_in_tready;

    //=========================================================================
    // Spike Input Mux  (DMA ingress priority > recurrent)
    //=========================================================================
    assign spike_in_in_router_range = (axis_spike_pending_id < NUM_NEURONS);
    assign router_input_valid     = flat_backend_mode &
                                    ((axis_spike_pending & spike_in_in_router_range) | neuron_spike_valid);
    assign router_input_neuron_id = (axis_spike_pending & spike_in_in_router_range)
                                    ? axis_spike_pending_id[NEURON_ID_WIDTH-1:0]
                                    : neuron_spike_id;
    assign bd_spike_in_ready      = 1'b1;
    assign neuron_spike_ready_wire = flat_backend_mode &
                                     router_input_ready &
                                     ~(axis_spike_pending & spike_in_in_router_range);

    //=========================================================================
    // Tiny EventConv Backend
    //=========================================================================
    assign eventconv_kernel_weight_flat = {8'd4, 8'd3, 8'd2, 8'd1};
    assign eventconv_update_weight = eventconv_kernel_weight_out;

    always @(posedge clk) begin
        if (!rst_n || bd_spikemold_reset[0] || !eventconv_backend_mode) begin
            eventconv_input_seen <= 1'b0;
            eventconv_packet_done <= 1'b0;
            eventconv_commit_started <= 1'b0;
            eventconv_commit_done_latched <= 1'b0;
            eventconv_commit_start <= 1'b0;
        end else begin
            eventconv_commit_start <= 1'b0;

            if (eventconv_input_fire) begin
                eventconv_input_seen <= 1'b1;
                eventconv_commit_done_latched <= 1'b0;
                if (bd_dma_spike_in_tlast) begin
                    eventconv_packet_done <= 1'b1;
                end
            end

            if (eventconv_commit_done) begin
                eventconv_commit_done_latched <= 1'b1;
            end

            if (eventconv_input_seen &&
                eventconv_packet_done &&
                !eventconv_commit_started &&
                !eventconv_commit_busy &&
                eventconv_input_tready &&
                (eventconv_updates_generated != 32'd0)) begin
                eventconv_commit_start <= 1'b1;
                eventconv_commit_started <= 1'b1;
            end
        end
    end

    assign eventconv_run_busy =
        eventconv_backend_mode &&
        (eventconv_input_seen || eventconv_commit_started) &&
        !eventconv_commit_done_latched;

    spike_conv_agu #(
        .KERNEL_SIZE        (EVENTCONV_KERNEL_SIZE),
        .INPUT_WIDTH        (EVENTCONV_INPUT_WIDTH),
        .INPUT_HEIGHT       (EVENTCONV_INPUT_HEIGHT),
        .NUM_CHANNELS       (EVENTCONV_NUM_CHANNELS),
        .OUTPUT_CHANNELS    (EVENTCONV_OUTPUT_CHANNELS),
        .STRIDE             (1),
        .PADDING            (0),
        .KERNEL_WEIGHT_BITS (8)
    ) u_eventconv_agu (
        .clk                    (clk),
        .rst_n                  (rst_n & ~bd_spikemold_reset[0]),
        .enable                 (eventconv_enable),
        .s_axis_spike_tvalid    (eventconv_backend_mode & bd_dma_spike_in_tvalid),
        .s_axis_spike_tdata     (bd_dma_spike_in_tdata),
        .s_axis_spike_tready    (eventconv_input_tready),
        .m_axis_spike_tvalid    (eventconv_update_tvalid),
        .m_axis_spike_tdata     (eventconv_update_tdata),
        .m_axis_spike_tready    (eventconv_update_tready),
        .kernel_weight_out      (eventconv_kernel_weight_out),
        .kernel_weight_flat     (eventconv_kernel_weight_flat),
        .conv_spikes_processed  (eventconv_spikes_processed),
        .conv_updates_generated (eventconv_updates_generated),
        .conv_address_errors    (eventconv_address_errors)
    );

    spike_conv_state_update #(
        .STATE_COUNT   (EVENTCONV_STATE_COUNT),
        .DEST_ID_WIDTH (EVENTCONV_DEST_ID_WIDTH),
        .STATE_WIDTH   (EVENTCONV_STATE_WIDTH),
        .WEIGHT_WIDTH  (8)
    ) u_eventconv_state (
        .clk                    (clk),
        .rst_n                  (rst_n & ~bd_spikemold_reset[0]),
        .enable                 (eventconv_enable),
        .clear                  (eventconv_clear),
        .s_axis_update_tvalid   (eventconv_update_tvalid),
        .s_axis_update_tdata    (eventconv_update_tdata),
        .update_weight          (eventconv_update_weight),
        .s_axis_update_tready   (eventconv_update_tready),
        .s_axis_reset_tvalid    (eventconv_reset_tvalid),
        .s_axis_reset_tdest     (eventconv_reset_tdest),
        .s_axis_reset_tready    (eventconv_reset_tready),
        .state_flat             (eventconv_state_flat),
        .active_id_flat         (eventconv_active_id_flat),
        .active_mask            (eventconv_active_mask),
        .active_neuron_count    (eventconv_active_neuron_count),
        .state_read_count       (eventconv_state_read_count),
        .state_write_count      (eventconv_state_write_count),
        .update_count           (eventconv_update_count),
        .commit_reset_count     (eventconv_commit_reset_count),
        .invalid_dest_count     (eventconv_invalid_dest_count),
        .state_checksum         (eventconv_state_checksum)
    );

    spike_conv_active_commit #(
        .STATE_COUNT   (EVENTCONV_STATE_COUNT),
        .DEST_ID_WIDTH (EVENTCONV_DEST_ID_WIDTH),
        .STATE_WIDTH   (EVENTCONV_STATE_WIDTH)
    ) u_eventconv_commit (
        .clk                                (clk),
        .rst_n                              (rst_n & ~bd_spikemold_reset[0]),
        .enable                             (eventconv_enable),
        .clear                              (eventconv_clear),
        .commit_start                       (eventconv_commit_start),
        .commit_threshold                   (cfg_global_threshold[EVENTCONV_STATE_WIDTH-1:0]),
        .active_neuron_count                (eventconv_active_neuron_count),
        .active_id_flat                     (eventconv_active_id_flat),
        .state_flat                         (eventconv_state_flat),
        .commit_busy                        (eventconv_commit_busy),
        .commit_done                        (eventconv_commit_done),
        .m_axis_commit_tvalid               (eventconv_commit_tvalid),
        .m_axis_commit_tdata                (eventconv_commit_tdata),
        .m_axis_commit_tready               (eventconv_commit_tready),
        .m_axis_reset_tvalid                (eventconv_reset_tvalid),
        .m_axis_reset_tdest                 (eventconv_reset_tdest),
        .m_axis_reset_tready                (eventconv_reset_tready),
        .active_commit_read_count           (eventconv_active_commit_read_count),
        .commit_emit_count                  (eventconv_commit_emit_count),
        .full_scan_count                    (eventconv_full_scan_count),
        .readout_checksum                   (eventconv_readout_checksum),
        .output_backpressure_cycle_count    (eventconv_output_backpressure_cycle_count)
    );

    //=========================================================================
    // FIFO Bridge  RTL neuron output -> DMA0 S2MM
    // Neuron pulse can arrive while DMA S2MM ready is deasserted. A single hold
    // register drops bursts in that case, so buffer post-spikes in a small
    // local FIFO and stream them to HLS with ready/valid handshaking.
    //=========================================================================
    localparam [SPIKE_AXIS_ID_WIDTH-1:0] AXIS_MAX_NEURON_ID = HLS_MAX_NEURONS[SPIKE_AXIS_ID_WIDTH-1:0];
    wire [SPIKE_AXIS_ID_WIDTH-1:0] neuron_spike_id_axis =
        {{(SPIKE_AXIS_ID_WIDTH-NEURON_ID_WIDTH){1'b0}}, neuron_spike_id};
    wire neuron_in_hls_range = (neuron_spike_id_axis < AXIS_MAX_NEURON_ID);
    localparam SPIKE_OUT_FIFO_DEPTH = 32;
    localparam SPIKE_OUT_FIFO_AW    = $clog2(SPIKE_OUT_FIFO_DEPTH);
    localparam SPIKE_OUT_FIFO_DW    = SPIKE_AXIS_ID_WIDTH + DATA_WIDTH;
    localparam [SPIKE_OUT_FIFO_AW-1:0] SPIKE_OUT_FIFO_LAST = {SPIKE_OUT_FIFO_AW{1'b1}};

    reg [SPIKE_OUT_FIFO_DW-1:0] spike_out_fifo_mem [0:SPIKE_OUT_FIFO_DEPTH-1];
    reg [SPIKE_OUT_FIFO_AW-1:0] spike_out_fifo_wr_ptr;
    reg [SPIKE_OUT_FIFO_AW-1:0] spike_out_fifo_rd_ptr;
    reg [SPIKE_OUT_FIFO_AW:0]   spike_out_fifo_count;
    reg [31:0]                  output_bridge_event_count_reg;
    reg [31:0]                  output_bridge_emit_count_reg;
    reg [31:0]                  output_bridge_drop_count_reg;

    wire spike_out_fifo_empty = (spike_out_fifo_count == 0);
    wire spike_out_fifo_full  = (spike_out_fifo_count == SPIKE_OUT_FIFO_DEPTH);
    // Capture exactly the post-spikes popped from the LIF output FIFO. This
    // keeps repeated same-id/value commits visible to the board readback path.
    wire neuron_spike_event = neuron_spike_valid && neuron_spike_ready_wire;
    wire eventconv_output_event = eventconv_commit_tvalid && eventconv_commit_tready;
    wire [EVENTCONV_DEST_ID_WIDTH-1:0] eventconv_commit_dest_id =
        eventconv_commit_tdata[31:16];
    wire [SPIKE_AXIS_ID_WIDTH-1:0] eventconv_commit_id_axis =
        eventconv_commit_dest_id[SPIKE_AXIS_ID_WIDTH-1:0];
    wire [DATA_WIDTH-1:0] eventconv_commit_value =
        eventconv_commit_tdata[DATA_WIDTH-1:0];
    wire selected_output_event =
        eventconv_backend_mode ? eventconv_output_event : neuron_spike_event;
    wire [SPIKE_AXIS_ID_WIDTH-1:0] selected_output_id =
        eventconv_backend_mode ? eventconv_commit_id_axis : neuron_spike_id_axis;
    wire [DATA_WIDTH-1:0] selected_output_value =
        eventconv_backend_mode ? eventconv_commit_value : neuron_spike_value;
    wire selected_output_in_hls_range =
        eventconv_backend_mode ? (eventconv_commit_id_axis < AXIS_MAX_NEURON_ID) : neuron_in_hls_range;
    wire spike_out_fifo_push  =
        bd_spikemold_enable[0] && selected_output_event && selected_output_in_hls_range;
    wire spike_out_fifo_pop   = bd_dma_spike_out_tvalid && bd_dma_spike_out_tready;
    wire [SPIKE_OUT_FIFO_DW-1:0] spike_out_fifo_head =
        spike_out_fifo_mem[spike_out_fifo_rd_ptr];
    wire [SPIKE_OUT_FIFO_AW-1:0] spike_out_fifo_wr_ptr_next =
        (spike_out_fifo_wr_ptr == SPIKE_OUT_FIFO_LAST) ? {SPIKE_OUT_FIFO_AW{1'b0}} : (spike_out_fifo_wr_ptr + 1'b1);
    wire [SPIKE_OUT_FIFO_AW-1:0] spike_out_fifo_rd_ptr_next =
        (spike_out_fifo_rd_ptr == SPIKE_OUT_FIFO_LAST) ? {SPIKE_OUT_FIFO_AW{1'b0}} : (spike_out_fifo_rd_ptr + 1'b1);
    wire eventconv_drain_ready =
        eventconv_backend_mode && (eventconv_commit_done_latched || eventconv_commit_done);
    wire spike_out_fifo_dma_valid =
        !spike_out_fifo_empty && (!eventconv_backend_mode || eventconv_drain_ready);

    always @(posedge clk) begin
        if (!rst_n || bd_spikemold_reset[0]) begin
            spike_out_fifo_wr_ptr <= {SPIKE_OUT_FIFO_AW{1'b0}};
            spike_out_fifo_rd_ptr <= {SPIKE_OUT_FIFO_AW{1'b0}};
            spike_out_fifo_count  <= {(SPIKE_OUT_FIFO_AW+1){1'b0}};
            output_bridge_event_count_reg <= 32'd0;
            output_bridge_emit_count_reg  <= 32'd0;
            output_bridge_drop_count_reg  <= 32'd0;
        end else begin
            if (spike_out_fifo_push && !spike_out_fifo_full) begin
                spike_out_fifo_mem[spike_out_fifo_wr_ptr] <= {selected_output_value, selected_output_id};
                spike_out_fifo_wr_ptr <= spike_out_fifo_wr_ptr_next;
                if (output_bridge_event_count_reg != 32'hFFFFFFFF) begin
                    output_bridge_event_count_reg <= output_bridge_event_count_reg + 1'b1;
                end
            end else if (spike_out_fifo_push && output_bridge_drop_count_reg != 32'hFFFFFFFF) begin
                output_bridge_drop_count_reg <= output_bridge_drop_count_reg + 1'b1;
            end

            if (spike_out_fifo_pop) begin
                spike_out_fifo_rd_ptr <= spike_out_fifo_rd_ptr_next;
                if (output_bridge_emit_count_reg != 32'hFFFFFFFF) begin
                    output_bridge_emit_count_reg <= output_bridge_emit_count_reg + 1'b1;
                end
            end

            case ({(spike_out_fifo_push && !spike_out_fifo_full), spike_out_fifo_pop})
                2'b10: spike_out_fifo_count <= spike_out_fifo_count + 1'b1;
                2'b01: spike_out_fifo_count <= spike_out_fifo_count - 1'b1;
                default: spike_out_fifo_count <= spike_out_fifo_count;
            endcase
        end
    end

    assign bd_spike_out_valid     = 1'b0;
    assign bd_spike_out_neuron_id = {HLS_NEURON_ID_WIDTH{1'b0}};
    assign bd_spike_out_weight    = {WEIGHT_WIDTH{1'b0}};
    assign bd_dma_spike_out_tvalid = spike_out_fifo_dma_valid;
    assign bd_dma_spike_out_tdata = {
        {(32-SPIKE_AXIS_ID_WIDTH-DATA_WIDTH){1'b0}},
        spike_out_fifo_head[SPIKE_OUT_FIFO_DW-1:SPIKE_AXIS_ID_WIDTH],
        spike_out_fifo_head[SPIKE_AXIS_ID_WIDTH-1:0]
    };
    assign bd_dma_spike_out_tkeep = 4'hF;
    assign bd_dma_spike_out_tlast = eventconv_backend_mode
                                    ? (bd_dma_spike_out_tvalid && (spike_out_fifo_count == 1))
                                    : bd_dma_spike_out_tvalid;
    assign eventconv_commit_tready = eventconv_backend_mode & !spike_out_fifo_full;

    //=========================================================================
    // PL-only latency counter (cycles)
    // Measures: first accepted AXIS input spike -> first neuron output spike.
    // Exported through cfg_throughput_counter (0x24) for host-side conversion:
    //   latency_ms = cycles / f_clk_hz * 1000
    //=========================================================================
    reg [31:0] pl_latency_cycles_cur;
    reg [31:0] pl_latency_cycles_latched;
    reg        pl_latency_active;
    reg        pl_latency_done;
    reg [31:0] pl_service_cycles_cur;
    reg [31:0] pl_service_cycles_latched;
    reg        pl_service_active;
    reg        pl_service_done;
    reg        pl_service_seen_busy;

    wire hls_input_accept_event =
        eventconv_backend_mode ? eventconv_input_fire : axis_spike_accept_event;
    wire pl_output_commit_event =
        eventconv_backend_mode ? eventconv_output_event : neuron_spike_event;

    always @(posedge clk) begin
        if (!rst_n || bd_spikemold_reset[0]) begin
            pl_latency_cycles_cur    <= 32'd0;
            pl_latency_cycles_latched<= 32'd0;
            pl_latency_active        <= 1'b0;
            pl_latency_done          <= 1'b0;
            pl_service_cycles_cur    <= 32'd0;
            pl_service_cycles_latched<= 32'd0;
            pl_service_active        <= 1'b0;
            pl_service_done          <= 1'b0;
            pl_service_seen_busy     <= 1'b0;
        end else if (!bd_spikemold_enable[0]) begin
            // Inter-image idle window: keep last latched value readable.
            pl_latency_cycles_cur <= 32'd0;
            pl_latency_active     <= 1'b0;
            pl_latency_done       <= 1'b0;
            pl_service_cycles_cur <= 32'd0;
            pl_service_active     <= 1'b0;
            pl_service_done       <= 1'b0;
            pl_service_seen_busy  <= 1'b0;
        end else begin
            if (!pl_latency_active && !pl_latency_done) begin
                if (hls_input_accept_event) begin
                    pl_latency_cycles_cur     <= 32'd0;
                    pl_latency_cycles_latched <= 32'd0;
                    pl_latency_active         <= 1'b1;
                end
            end else if (pl_latency_active) begin
                pl_latency_cycles_cur <= pl_latency_cycles_cur + 1'b1;
                if (pl_output_commit_event) begin
                    pl_latency_cycles_latched <= pl_latency_cycles_cur + 1'b1;
                    pl_latency_active         <= 1'b0;
                    pl_latency_done           <= 1'b1;
                end
            end

            // Service-time cycles:
            // first accepted input spike -> return to idle after busy period.
            if (!pl_service_active && !pl_service_done) begin
                if (hls_input_accept_event) begin
                    pl_service_cycles_cur     <= 32'd0;
                    pl_service_cycles_latched <= 32'd0;
                    pl_service_active         <= 1'b1;
                    pl_service_seen_busy      <= bd_spikemold_busy;
                end
            end else if (pl_service_active) begin
                pl_service_cycles_cur <= pl_service_cycles_cur + 1'b1;
                if (bd_spikemold_busy) begin
                    pl_service_seen_busy <= 1'b1;
                end
                if ((pl_service_seen_busy || bd_spikemold_busy) && !bd_spikemold_busy) begin
                    pl_service_cycles_latched <= pl_service_cycles_cur + 1'b1;
                    pl_service_active         <= 1'b0;
                    pl_service_done           <= 1'b1;
                end
            end
        end
    end

    assign cfg_throughput_counter = pl_latency_cycles_latched;
    assign cfg_service_cycles_counter = pl_service_cycles_latched;
    assign cfg_pl_busy_cycles_counter = axis_valid_seen_count;
    assign cfg_output_drain_cycles_counter =
        eventconv_backend_mode ? eventconv_active_commit_read_count : axis_router_accept_count;
    assign cfg_output_bridge_status = {
        16'd0,
        axis_spike_pending,
        axis_spike_can_capture,
        axis_spike_in_fire,
        axis_spike_accept_event,
        router_input_ready,
        router_input_valid,
        spike_out_fifo_full,
        !spike_out_fifo_empty,
        {{(8-(SPIKE_OUT_FIFO_AW+1)){1'b0}}, spike_out_fifo_count}
    };
    assign cfg_output_bridge_drop_count = output_bridge_drop_count_reg + axis_pending_drop_count;
    assign cfg_output_bridge_event_count = output_bridge_event_count_reg;
    assign cfg_output_bridge_emit_count = output_bridge_emit_count_reg;
    assign router_spike_count =
        eventconv_backend_mode ? eventconv_update_count : flat_router_spike_count;
    assign neuron_spike_count =
        eventconv_backend_mode ? eventconv_commit_emit_count : flat_neuron_spike_count;
    assign fifo_overflow =
        eventconv_backend_mode ? (eventconv_invalid_dest_count != 32'd0) : flat_fifo_overflow;
    assign active_neurons =
        eventconv_backend_mode ? eventconv_active_neuron_count[7:0] : flat_active_neurons;
    assign neuron_state_checksum =
        eventconv_backend_mode ? eventconv_state_checksum[31:0] : flat_neuron_state_checksum;

    //=========================================================================
    // SpikeMold Status
    //=========================================================================
    assign bd_spikemold_ready = eventconv_backend_mode
                                ? ~eventconv_run_busy
                                : (~router_busy & ~neuron_array_busy);
    assign bd_spikemold_busy  = eventconv_backend_mode
                                ? eventconv_run_busy
                                : (router_busy | neuron_array_busy);

    //=========================================================================
    // Router Config Queue (decoupled control path)
    // Decouple AXI register fanout from router BRAM write path.
    //=========================================================================
    fifo #(
        .DATA_WIDTH(64),
        .DEPTH(ROUTER_CFG_CMD_FIFO_DEPTH)
    ) u_router_cfg_cmd_fifo (
        .clk          (clk),
        .rst_n        (rst_n & ~bd_spikemold_reset[0]),
        .wr_en        (cfg_router_config_we),
        .wr_data      ({cfg_router_config_addr, cfg_router_config_wdata}),
        .full         (router_cfg_cmd_fifo_full),
        .almost_full  (router_cfg_cmd_fifo_almost_full),
        .rd_en        (router_cfg_cmd_fifo_rd_en),
        .rd_data      (router_cfg_cmd_fifo_rd_data),
        .empty        (router_cfg_cmd_fifo_empty),
        .almost_empty (router_cfg_cmd_fifo_almost_empty),
        .count        (router_cfg_cmd_fifo_count),
        .overflow     (router_cfg_cmd_fifo_overflow),
        .underflow    (router_cfg_cmd_fifo_underflow)
    );

    assign router_cfg_cmd_fifo_rd_en = !router_cfg_cmd_pop_pending && !router_cfg_cmd_fifo_empty;

    always @(posedge clk) begin
        if (!rst_n || bd_spikemold_reset[0]) begin
            router_cfg_cmd_pop_pending <= 1'b0;
            router_cfg_cmd_valid       <= 1'b0;
            router_cfg_cmd_addr        <= 32'd0;
            router_cfg_cmd_data        <= 32'd0;
        end else begin
            router_cfg_cmd_valid <= 1'b0;

            if (router_cfg_cmd_pop_pending) begin
                router_cfg_cmd_addr        <= router_cfg_cmd_fifo_rd_data[63:32];
                router_cfg_cmd_data        <= router_cfg_cmd_fifo_rd_data[31:0];
                router_cfg_cmd_valid       <= 1'b1;
                router_cfg_cmd_pop_pending <= 1'b0;
            end else if (!router_cfg_cmd_fifo_empty) begin
                router_cfg_cmd_pop_pending <= 1'b1;
            end
        end
    end

    //=========================================================================
    // Spike Router
    //=========================================================================
    spike_router #(
        .NUM_NEURONS     (NUM_NEURONS),
        .MAX_FANOUT      (32),
        .WEIGHT_WIDTH    (WEIGHT_WIDTH),
        .NEURON_ID_WIDTH (NEURON_ID_WIDTH),
        .DELAY_WIDTH     (8),
        .FIFO_DEPTH      (ROUTER_BUFFER_DEPTH)
    ) u_spike_router (
        .clk             (clk),
        .rst_n           (rst_n & ~bd_spikemold_reset[0]),
        .s_spike_valid   (router_input_valid),
        .s_spike_neuron_id(router_input_neuron_id),
        .s_spike_ready   (router_input_ready),
        .m_spike_valid   (router_spike_valid),
        .m_spike_dest_id (router_spike_dest_id),
        .m_spike_weight  (router_spike_weight),
        .m_spike_exc_inh (router_spike_exc_inh),
        .m_spike_ready   (router_spike_ready),
        .config_we       (1'b0),
        .config_addr     (cfg_router_config_addr),
        .config_data     (32'd0),
        .config_cmd_valid(router_cfg_cmd_valid),
        .config_cmd_addr (router_cfg_cmd_addr),
        .config_cmd_data (router_cfg_cmd_data),
        .config_readdata (cfg_router_config_rdata),
        .routed_spike_count(flat_router_spike_count),
        .router_busy     (router_busy),
        .fifo_overflow   (flat_fifo_overflow)
    );

    //=========================================================================
    // LIF Neuron Array
    //=========================================================================
    lif_neuron_array #(
        .NUM_NEURONS        (NUM_NEURONS),
        .NUM_AXONS          (NUM_AXONS),
        .DATA_WIDTH         (DATA_WIDTH),
        .WEIGHT_WIDTH       (WEIGHT_WIDTH),
        .THRESHOLD_WIDTH    (THRESHOLD_WIDTH),
        .LEAK_WIDTH         (LEAK_WIDTH),
        .REFRAC_WIDTH       (REFRAC_WIDTH),
        .NUM_PARALLEL_UNITS (NUM_PARALLEL_UNITS),
        .SPIKE_BUFFER_DEPTH (SPIKE_BUFFER_DEPTH),
        .USE_BRAM           (1),
        .USE_DSP            (1)
    ) u_neuron_array (
        .clk                    (clk),
        .rst_n                  (rst_n & ~bd_spikemold_reset[0]),
        .enable                 (bd_spikemold_enable[0] & flat_backend_mode),
        .s_axis_spike_valid     (router_spike_valid),
        .s_axis_spike_dest_id   (router_spike_dest_id),
        .s_axis_spike_weight    (router_spike_weight),
        .s_axis_spike_exc_inh   (router_spike_exc_inh),
        .s_axis_spike_ready     (router_spike_ready),
        .m_axis_spike_valid     (neuron_spike_valid),
        .m_axis_spike_neuron_id (neuron_spike_id),
        .m_axis_spike_value     (neuron_spike_value),
        .m_axis_spike_ready     (neuron_spike_ready_wire),
        .config_we              (cfg_neuron_config_we),
        .config_addr            (cfg_neuron_config_addr),
        .config_data            (cfg_neuron_config_wdata),
        .global_threshold       (cfg_global_threshold),
        .global_leak_rate       (cfg_global_leak_rate),
        .global_refrac_period   (cfg_global_refrac_period),
        .spike_count            (flat_neuron_spike_count),
        .array_busy             (neuron_array_busy),
        .throughput_counter     (neuron_throughput_counter),
        .state_checksum         (flat_neuron_state_checksum),
        .active_neurons         (flat_active_neurons)
    );

endmodule
