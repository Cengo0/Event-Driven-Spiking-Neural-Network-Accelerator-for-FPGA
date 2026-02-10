//-----------------------------------------------------------------------------
// Title         : Integrated SNN Accelerator Top (HLS + Verilog RTL)
// Project       : PYNQ-Z2 SNN Accelerator
// File          : snn_integrated_top.v
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : Top-level wrapper with FULL HLS <-> RTL integration:
//                 - HLS IP outputs spikes → Spike Router → LIF Neurons
//                 - LIF Neuron outputs → HLS IP (for STDP learning)
//                 - AXI-Lite config registers for runtime RTL configuration
//                 - Bidirectional DMA spike streaming (MM2S + S2MM)
//                 - Full monitoring: spike counts, overflow, throughput
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps

module snn_integrated_top #(
    // System Parameters  
    parameter NUM_NEURONS           = 1024,   // Scaled up: BRAM-backed, LUT-neutral
    parameter NUM_AXONS             = 1024,
    parameter NUM_PARALLEL_UNITS    = 4,
    parameter SPIKE_BUFFER_DEPTH    = 64,
    parameter HLS_NEURON_ID_WIDTH   = 10,     // Matches HLS neuron_id_t (10-bit)
    parameter HLS_MAX_NEURONS       = 720,    // HLS weight_memory covers neurons 0..719
    parameter NEURON_ID_WIDTH       = (NUM_NEURONS <= 256) ? 8 :
                                     (NUM_NEURONS <= 512) ? 9 : 10,
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
    // Internal Signals: Clock and Reset
    //=========================================================================
    wire clk_100mhz;
    wire rst_n_sync;
    wire debug_learning_active;
    
    //=========================================================================
    // HLS <-> RTL Interface Signals (from Block Design)
    //=========================================================================
    
    // HLS → RTL: Spikes from HLS to RTL neurons (8-bit interface)
    wire                             hls_spike_out_valid;
    wire [HLS_NEURON_ID_WIDTH-1:0]   hls_spike_out_neuron_id;
    wire [WEIGHT_WIDTH-1:0]          hls_spike_out_weight;
    wire                             rtl_spike_in_ready;
    
    // RTL → HLS: Spikes from RTL neurons to HLS (8-bit interface)
    wire                             rtl_spike_out_valid;
    wire [HLS_NEURON_ID_WIDTH-1:0]   rtl_spike_out_neuron_id;
    wire [WEIGHT_WIDTH-1:0]          rtl_spike_out_weight;
    wire                             hls_spike_in_ready;
    
    //=========================================================================
    // HLS ↔ RTL Width Adapters (8-bit HLS ↔ 10-bit internal)
    // HLS addresses neurons 0-255; neurons 256-1023 are RTL-internal
    //=========================================================================
    wire [NEURON_ID_WIDTH-1:0] hls_spike_id_extended;
    assign hls_spike_id_extended = {{(NEURON_ID_WIDTH-HLS_NEURON_ID_WIDTH){1'b0}},
                                    hls_spike_out_neuron_id};
    
    // SNN Control
    wire                         hls_snn_enable;
    wire                         hls_snn_reset;
    wire                         rtl_snn_ready;
    wire                         rtl_snn_busy;
    
    // HLS neuron parameter outputs (monitoring only)
    wire [15:0]                  hls_threshold_out;
    wire [15:0]                  hls_leak_rate_out;
    
    //=========================================================================
    // Config Register Interface (from AXI-Lite slave in Block Design)
    //=========================================================================
    wire                         cfg_router_config_we;
    wire [31:0]                  cfg_router_config_addr;
    wire [31:0]                  cfg_router_config_wdata;
    wire [31:0]                  cfg_router_config_rdata;
    
    wire                         cfg_neuron_config_we;
    wire [9:0]                   cfg_neuron_config_addr;
    wire [31:0]                  cfg_neuron_config_wdata;
    
    wire [15:0]                  cfg_global_threshold;
    wire [7:0]                   cfg_global_leak_rate;
    wire [7:0]                   cfg_global_refrac_period;
    
    //=========================================================================
    // Internal Spike Router Signals
    //=========================================================================
    wire                         router_spike_valid;
    wire [NEURON_ID_WIDTH-1:0]   router_spike_dest_id;
    wire [WEIGHT_WIDTH-1:0]      router_spike_weight;
    wire                         router_spike_exc_inh;
    wire                         router_spike_ready;
    
    // Router input selection (HLS or recurrent)
    wire                         router_input_valid;
    wire [NEURON_ID_WIDTH-1:0]   router_input_neuron_id;
    wire                         router_input_ready;
    
    //=========================================================================
    // Neuron Array Output Signals
    //=========================================================================
    wire                         neuron_spike_valid;
    wire [NEURON_ID_WIDTH-1:0]   neuron_spike_id;
    wire                         neuron_spike_ready;
    
    // Statistics & Monitoring
    wire [31:0]                  router_spike_count;
    wire [31:0]                  neuron_spike_count;
    wire                         router_busy;
    wire                         neuron_array_busy;
    wire                         fifo_overflow;
    wire [31:0]                  throughput_counter;
    wire [7:0]                   active_neurons;
    
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
        
        // PL Clock/Reset outputs
        .clk_100mhz         (clk_100mhz),
        .rst_n_sync          (rst_n_sync),
        
        // Debug
        .debug_learning_active (debug_learning_active),
        
        //---------------------------------------------------------------------
        // HLS → RTL Spike Interface
        //---------------------------------------------------------------------
        .hls_spike_out_valid     (hls_spike_out_valid),
        .hls_spike_out_neuron_id (hls_spike_out_neuron_id),
        .hls_spike_out_weight    (hls_spike_out_weight),
        .rtl_spike_in_ready      (rtl_spike_in_ready),
        
        //---------------------------------------------------------------------
        // RTL → HLS Spike Interface (for STDP learning)
        //---------------------------------------------------------------------
        .rtl_spike_out_valid     (rtl_spike_out_valid),
        .rtl_spike_out_neuron_id (rtl_spike_out_neuron_id),
        .rtl_spike_out_weight    (rtl_spike_out_weight),
        .hls_spike_in_ready      (hls_spike_in_ready),
        
        //---------------------------------------------------------------------
        // SNN Control Interface
        //---------------------------------------------------------------------
        .hls_snn_enable          (hls_snn_enable),
        .hls_snn_reset           (hls_snn_reset),
        .rtl_snn_ready           (rtl_snn_ready),
        .rtl_snn_busy            (rtl_snn_busy),
        
        //---------------------------------------------------------------------
        // HLS Neuron Parameter Outputs (monitoring)
        //---------------------------------------------------------------------
        .hls_threshold_out       (hls_threshold_out),
        .hls_leak_rate_out       (hls_leak_rate_out),
        
        //---------------------------------------------------------------------
        // Config Register Interface
        //---------------------------------------------------------------------
        // Router config
        .cfg_router_config_we    (cfg_router_config_we),
        .cfg_router_config_addr  (cfg_router_config_addr),
        .cfg_router_config_wdata (cfg_router_config_wdata),
        .cfg_router_config_rdata (cfg_router_config_rdata),
        
        // Neuron config
        .cfg_neuron_config_we    (cfg_neuron_config_we),
        .cfg_neuron_config_addr  (cfg_neuron_config_addr),
        .cfg_neuron_config_wdata (cfg_neuron_config_wdata),
        
        // Global parameters
        .cfg_global_threshold    (cfg_global_threshold),
        .cfg_global_leak_rate    (cfg_global_leak_rate),
        .cfg_global_refrac_period(cfg_global_refrac_period),
        
        // Status feedback
        .cfg_router_spike_count  (router_spike_count),
        .cfg_neuron_spike_count  (neuron_spike_count),
        .cfg_fifo_overflow       (fifo_overflow),
        .cfg_active_neurons      (active_neurons),
        .cfg_throughput_counter  (throughput_counter)
    );
    
    //=========================================================================
    // Spike Input Multiplexer
    // Priority: HLS spikes > Recurrent neuron spikes
    //=========================================================================
    
    // Simple priority: HLS has priority when sending spikes
    assign router_input_valid     = hls_spike_out_valid | neuron_spike_valid;
    assign router_input_neuron_id = hls_spike_out_valid ? hls_spike_id_extended : neuron_spike_id;
    
    // Ready signals
    assign rtl_spike_in_ready = router_input_ready;
    assign neuron_spike_ready = router_input_ready & ~hls_spike_out_valid;
    
    //=========================================================================
    // RTL → HLS Connection
    // Send neuron output spikes to HLS for STDP learning
    // GUARD: Only forward spikes from neurons 0-255 to avoid ID aliasing
    // Neurons 256-1023 participate in recurrent activity but are not
    // reported to HLS (8-bit truncation would cause wrong neuron IDs)
    //=========================================================================
    
    wire neuron_in_hls_range = (neuron_spike_id < HLS_MAX_NEURONS);
    
    assign rtl_spike_out_valid     = neuron_spike_valid & neuron_in_hls_range;
    assign rtl_spike_out_neuron_id = neuron_spike_id[HLS_NEURON_ID_WIDTH-1:0];
    assign rtl_spike_out_weight    = router_spike_weight;  // Use current weight
    
    //=========================================================================
    // SNN Status to HLS
    //=========================================================================
    
    assign rtl_snn_ready = ~router_busy & ~neuron_array_busy;
    assign rtl_snn_busy  = router_busy | neuron_array_busy;
    
    //=========================================================================
    // Verilog RTL: Spike Router (AER-based)
    //=========================================================================
    
    spike_router #(
        .NUM_NEURONS        (NUM_NEURONS),
        .MAX_FANOUT         (32),
        .WEIGHT_WIDTH       (WEIGHT_WIDTH),
        .NEURON_ID_WIDTH    (NEURON_ID_WIDTH),
        .DELAY_WIDTH        (8),
        .FIFO_DEPTH         (ROUTER_BUFFER_DEPTH)
    ) u_spike_router (
        .clk                (clk_100mhz),
        .rst_n              (rst_n_sync & ~hls_snn_reset),
        
        // Input (from HLS or recurrent)
        .s_spike_valid      (router_input_valid),
        .s_spike_neuron_id  (router_input_neuron_id),
        .s_spike_ready      (router_input_ready),
        
        // Output to neuron array
        .m_spike_valid      (router_spike_valid),
        .m_spike_dest_id    (router_spike_dest_id),
        .m_spike_weight     (router_spike_weight),
        .m_spike_exc_inh    (router_spike_exc_inh),
        .m_spike_ready      (router_spike_ready),
        
        // Configuration (driven by AXI-Lite config registers)
        .config_we          (cfg_router_config_we),
        .config_addr        (cfg_router_config_addr),
        .config_data        (cfg_router_config_wdata),
        .config_readdata    (cfg_router_config_rdata),
        
        // Statistics
        .routed_spike_count (router_spike_count),
        .router_busy        (router_busy),
        .fifo_overflow      (fifo_overflow)
    );
    
    //=========================================================================
    // Verilog RTL: LIF Neuron Array (AC-based, energy-efficient)
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
        .USE_DSP            (1)  // DSP48E1 for synaptic accumulation
    ) u_neuron_array (
        .clk                (clk_100mhz),
        .rst_n              (rst_n_sync & ~hls_snn_reset),
        .enable             (hls_snn_enable),
        
        // Input from spike router
        .s_axis_spike_valid     (router_spike_valid),
        .s_axis_spike_dest_id   (router_spike_dest_id),
        .s_axis_spike_weight    (router_spike_weight),
        .s_axis_spike_exc_inh   (router_spike_exc_inh),
        .s_axis_spike_ready     (router_spike_ready),
        
        // Output spikes (to HLS for learning + recurrent)
        .m_axis_spike_valid     (neuron_spike_valid),
        .m_axis_spike_neuron_id (neuron_spike_id),
        .m_axis_spike_ready     (hls_spike_in_ready),  // HLS controls flow
        
        // Configuration (driven by AXI-Lite config registers)
        .config_we              (cfg_neuron_config_we),
        .config_addr            (cfg_neuron_config_addr),
        .config_data            (cfg_neuron_config_wdata),
        
        // Global neuron parameters (driven by AXI-Lite config registers)
        .global_threshold       (cfg_global_threshold),
        .global_leak_rate       (cfg_global_leak_rate),
        .global_refrac_period   (cfg_global_refrac_period),
        
        // Monitoring (fed back to config register status inputs)
        .spike_count            (neuron_spike_count),
        .array_busy             (neuron_array_busy),
        .throughput_counter     (throughput_counter),
        .active_neurons         (active_neurons)
    );
    
endmodule
