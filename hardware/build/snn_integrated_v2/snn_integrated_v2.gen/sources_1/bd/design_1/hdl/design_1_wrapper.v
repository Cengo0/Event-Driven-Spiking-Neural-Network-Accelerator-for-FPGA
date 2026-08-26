//Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
//Copyright 2022-2025 Advanced Micro Devices, Inc. All Rights Reserved.
//--------------------------------------------------------------------------------
//Tool Version: Vivado v.2025.2 (lin64) Build 6299465 Fri Nov 14 12:34:56 MST 2025
//Date        : Mon Aug 24 12:52:20 2026
//Host        : Mariana running 64-bit Ubuntu 22.04.5 LTS
//Command     : generate_target design_1_wrapper.bd
//Design      : design_1_wrapper
//Purpose     : IP block netlist
//--------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

module design_1_wrapper
   (DDR_addr,
    DDR_ba,
    DDR_cas_n,
    DDR_ck_n,
    DDR_ck_p,
    DDR_cke,
    DDR_cs_n,
    DDR_dm,
    DDR_dq,
    DDR_dqs_n,
    DDR_dqs_p,
    DDR_odt,
    DDR_ras_n,
    DDR_reset_n,
    DDR_we_n,
    FIXED_IO_ddr_vrn,
    FIXED_IO_ddr_vrp,
    FIXED_IO_mio,
    FIXED_IO_ps_clk,
    FIXED_IO_ps_porb,
    FIXED_IO_ps_srstb,
    cfg_active_neurons,
    cfg_fifo_overflow,
    cfg_global_leak_rate,
    cfg_global_refrac_period,
    cfg_global_threshold,
    cfg_neuron_config_addr,
    cfg_neuron_config_wdata,
    cfg_neuron_config_we,
    cfg_neuron_spike_count,
    cfg_router_config_addr,
    cfg_router_config_rdata,
    cfg_router_config_wdata,
    cfg_router_config_we,
    cfg_router_spike_count,
    cfg_service_cycles_counter,
    cfg_throughput_counter,
    clk_100mhz,
    debug_learning_active,
    leak_rate_out,
    learn_weight_data,
    learn_weight_dst,
    learn_weight_dst_group,
    learn_weight_exc,
    learn_weight_fanout_idx,
    learn_weight_group,
    learn_weight_is_inter,
    learn_weight_ready,
    learn_weight_src,
    learn_weight_valid,
    rst_n_sync,
    snn_busy,
    snn_enable,
    snn_ready,
    snn_reset,
    spike_in_neuron_id,
    spike_in_ready,
    spike_in_valid,
    spike_in_weight,
    spike_out_neuron_id,
    spike_out_ready,
    spike_out_valid,
    spike_out_weight,
    threshold_out);
  inout [14:0]DDR_addr;
  inout [2:0]DDR_ba;
  inout DDR_cas_n;
  inout DDR_ck_n;
  inout DDR_ck_p;
  inout DDR_cke;
  inout DDR_cs_n;
  inout [3:0]DDR_dm;
  inout [31:0]DDR_dq;
  inout [3:0]DDR_dqs_n;
  inout [3:0]DDR_dqs_p;
  inout DDR_odt;
  inout DDR_ras_n;
  inout DDR_reset_n;
  inout DDR_we_n;
  inout FIXED_IO_ddr_vrn;
  inout FIXED_IO_ddr_vrp;
  inout [53:0]FIXED_IO_mio;
  inout FIXED_IO_ps_clk;
  inout FIXED_IO_ps_porb;
  inout FIXED_IO_ps_srstb;
  input [7:0]cfg_active_neurons;
  input cfg_fifo_overflow;
  output [7:0]cfg_global_leak_rate;
  output [7:0]cfg_global_refrac_period;
  output [15:0]cfg_global_threshold;
  output [9:0]cfg_neuron_config_addr;
  output [31:0]cfg_neuron_config_wdata;
  output cfg_neuron_config_we;
  input [31:0]cfg_neuron_spike_count;
  output [31:0]cfg_router_config_addr;
  input [31:0]cfg_router_config_rdata;
  output [31:0]cfg_router_config_wdata;
  output cfg_router_config_we;
  input [31:0]cfg_router_spike_count;
  input [31:0]cfg_service_cycles_counter;
  input [31:0]cfg_throughput_counter;
  output clk_100mhz;
  output [0:0]debug_learning_active;
  output [15:0]leak_rate_out;
  output [7:0]learn_weight_data;
  output [6:0]learn_weight_dst;
  output [3:0]learn_weight_dst_group;
  output [0:0]learn_weight_exc;
  output [3:0]learn_weight_fanout_idx;
  output [3:0]learn_weight_group;
  output [0:0]learn_weight_is_inter;
  input learn_weight_ready;
  output [6:0]learn_weight_src;
  output [0:0]learn_weight_valid;
  output [0:0]rst_n_sync;
  input snn_busy;
  output [0:0]snn_enable;
  input snn_ready;
  output [0:0]snn_reset;
  output [10:0]spike_in_neuron_id;
  input spike_in_ready;
  output [0:0]spike_in_valid;
  output [7:0]spike_in_weight;
  input [10:0]spike_out_neuron_id;
  output [0:0]spike_out_ready;
  input spike_out_valid;
  input [7:0]spike_out_weight;
  output [15:0]threshold_out;

  wire [14:0]DDR_addr;
  wire [2:0]DDR_ba;
  wire DDR_cas_n;
  wire DDR_ck_n;
  wire DDR_ck_p;
  wire DDR_cke;
  wire DDR_cs_n;
  wire [3:0]DDR_dm;
  wire [31:0]DDR_dq;
  wire [3:0]DDR_dqs_n;
  wire [3:0]DDR_dqs_p;
  wire DDR_odt;
  wire DDR_ras_n;
  wire DDR_reset_n;
  wire DDR_we_n;
  wire FIXED_IO_ddr_vrn;
  wire FIXED_IO_ddr_vrp;
  wire [53:0]FIXED_IO_mio;
  wire FIXED_IO_ps_clk;
  wire FIXED_IO_ps_porb;
  wire FIXED_IO_ps_srstb;
  wire [7:0]cfg_active_neurons;
  wire cfg_fifo_overflow;
  wire [7:0]cfg_global_leak_rate;
  wire [7:0]cfg_global_refrac_period;
  wire [15:0]cfg_global_threshold;
  wire [9:0]cfg_neuron_config_addr;
  wire [31:0]cfg_neuron_config_wdata;
  wire cfg_neuron_config_we;
  wire [31:0]cfg_neuron_spike_count;
  wire [31:0]cfg_router_config_addr;
  wire [31:0]cfg_router_config_rdata;
  wire [31:0]cfg_router_config_wdata;
  wire cfg_router_config_we;
  wire [31:0]cfg_router_spike_count;
  wire [31:0]cfg_service_cycles_counter;
  wire [31:0]cfg_throughput_counter;
  wire clk_100mhz;
  wire [0:0]debug_learning_active;
  wire [15:0]leak_rate_out;
  wire [7:0]learn_weight_data;
  wire [6:0]learn_weight_dst;
  wire [3:0]learn_weight_dst_group;
  wire [0:0]learn_weight_exc;
  wire [3:0]learn_weight_fanout_idx;
  wire [3:0]learn_weight_group;
  wire [0:0]learn_weight_is_inter;
  wire learn_weight_ready;
  wire [6:0]learn_weight_src;
  wire [0:0]learn_weight_valid;
  wire [0:0]rst_n_sync;
  wire snn_busy;
  wire [0:0]snn_enable;
  wire snn_ready;
  wire [0:0]snn_reset;
  wire [10:0]spike_in_neuron_id;
  wire spike_in_ready;
  wire [0:0]spike_in_valid;
  wire [7:0]spike_in_weight;
  wire [10:0]spike_out_neuron_id;
  wire [0:0]spike_out_ready;
  wire spike_out_valid;
  wire [7:0]spike_out_weight;
  wire [15:0]threshold_out;

  design_1 design_1_i
       (.DDR_addr(DDR_addr),
        .DDR_ba(DDR_ba),
        .DDR_cas_n(DDR_cas_n),
        .DDR_ck_n(DDR_ck_n),
        .DDR_ck_p(DDR_ck_p),
        .DDR_cke(DDR_cke),
        .DDR_cs_n(DDR_cs_n),
        .DDR_dm(DDR_dm),
        .DDR_dq(DDR_dq),
        .DDR_dqs_n(DDR_dqs_n),
        .DDR_dqs_p(DDR_dqs_p),
        .DDR_odt(DDR_odt),
        .DDR_ras_n(DDR_ras_n),
        .DDR_reset_n(DDR_reset_n),
        .DDR_we_n(DDR_we_n),
        .FIXED_IO_ddr_vrn(FIXED_IO_ddr_vrn),
        .FIXED_IO_ddr_vrp(FIXED_IO_ddr_vrp),
        .FIXED_IO_mio(FIXED_IO_mio),
        .FIXED_IO_ps_clk(FIXED_IO_ps_clk),
        .FIXED_IO_ps_porb(FIXED_IO_ps_porb),
        .FIXED_IO_ps_srstb(FIXED_IO_ps_srstb),
        .cfg_active_neurons(cfg_active_neurons),
        .cfg_fifo_overflow(cfg_fifo_overflow),
        .cfg_global_leak_rate(cfg_global_leak_rate),
        .cfg_global_refrac_period(cfg_global_refrac_period),
        .cfg_global_threshold(cfg_global_threshold),
        .cfg_neuron_config_addr(cfg_neuron_config_addr),
        .cfg_neuron_config_wdata(cfg_neuron_config_wdata),
        .cfg_neuron_config_we(cfg_neuron_config_we),
        .cfg_neuron_spike_count(cfg_neuron_spike_count),
        .cfg_router_config_addr(cfg_router_config_addr),
        .cfg_router_config_rdata(cfg_router_config_rdata),
        .cfg_router_config_wdata(cfg_router_config_wdata),
        .cfg_router_config_we(cfg_router_config_we),
        .cfg_router_spike_count(cfg_router_spike_count),
        .cfg_service_cycles_counter(cfg_service_cycles_counter),
        .cfg_throughput_counter(cfg_throughput_counter),
        .clk_100mhz(clk_100mhz),
        .debug_learning_active(debug_learning_active),
        .leak_rate_out(leak_rate_out),
        .learn_weight_data(learn_weight_data),
        .learn_weight_dst(learn_weight_dst),
        .learn_weight_dst_group(learn_weight_dst_group),
        .learn_weight_exc(learn_weight_exc),
        .learn_weight_fanout_idx(learn_weight_fanout_idx),
        .learn_weight_group(learn_weight_group),
        .learn_weight_is_inter(learn_weight_is_inter),
        .learn_weight_ready(learn_weight_ready),
        .learn_weight_src(learn_weight_src),
        .learn_weight_valid(learn_weight_valid),
        .rst_n_sync(rst_n_sync),
        .snn_busy(snn_busy),
        .snn_enable(snn_enable),
        .snn_ready(snn_ready),
        .snn_reset(snn_reset),
        .spike_in_neuron_id(spike_in_neuron_id),
        .spike_in_ready(spike_in_ready),
        .spike_in_valid(spike_in_valid),
        .spike_in_weight(spike_in_weight),
        .spike_out_neuron_id(spike_out_neuron_id),
        .spike_out_ready(spike_out_ready),
        .spike_out_valid(spike_out_valid),
        .spike_out_weight(spike_out_weight),
        .threshold_out(threshold_out));
endmodule
