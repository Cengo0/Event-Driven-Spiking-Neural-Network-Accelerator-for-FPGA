// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2026 Advanced Micro Devices, Inc. All Rights Reserved.
// -------------------------------------------------------------------------------
// This file contains confidential and proprietary information
// of AMD and is protected under U.S. and international copyright
// and other intellectual property laws.
//
// DISCLAIMER
// This disclaimer is not a license and does not grant any
// rights to the materials distributed herewith. Except as
// otherwise provided in a valid license issued to you by
// AMD, and to the maximum extent permitted by applicable
// law: (1) THESE MATERIALS ARE MADE AVAILABLE "AS IS" AND
// WITH ALL FAULTS, AND AMD HEREBY DISCLAIMS ALL WARRANTIES
// AND CONDITIONS, EXPRESS, IMPLIED, OR STATUTORY, INCLUDING
// BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, NON-
// INFRINGEMENT, OR FITNESS FOR ANY PARTICULAR PURPOSE; and
// (2) AMD shall not be liable (whether in contract or tort,
// including negligence, or under any other theory of
// liability) for any loss or damage of any kind or nature
// related to, arising under or in connection with these
// materials, including for any direct, or any indirect,
// special, incidental, or consequential loss or damage
// (including loss of data, profits, goodwill, or any type of
// loss or damage suffered as a result of any action brought
// by a third party) even if such damage or loss was
// reasonably foreseeable or AMD had been advised of the
// possibility of the same.
//
// CRITICAL APPLICATIONS
// AMD products are not designed or intended to be fail-
// safe, or for use in any application requiring fail-safe
// performance, such as life-support or safety devices or
// systems, Class III medical devices, nuclear facilities,
// applications related to the deployment of airbags, or any
// other applications that could lead to death, personal
// injury, or severe property or environmental damage
// (individually and collectively, "Critical
// Applications"). Customer assumes the sole risk and
// liability of any use of AMD products in Critical
// Applications, subject only to applicable laws and
// regulations governing limitations on product liability.
//
// THIS COPYRIGHT NOTICE AND DISCLAIMER MUST BE RETAINED AS
// PART OF THIS FILE AT ALL TIMES.
//
// DO NOT MODIFY THIS FILE.

// MODULE VLNV: amd.com:blockdesign:design_1:1.0

`timescale 1ps / 1ps

`include "vivado_interfaces.svh"

module design_1_sv (
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire DDR_cas_n,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire DDR_cke,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire DDR_ck_n,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire DDR_ck_p,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire DDR_cs_n,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire DDR_reset_n,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire DDR_odt,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire DDR_ras_n,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire DDR_we_n,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire [2:0] DDR_ba,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire [14:0] DDR_addr,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire [3:0] DDR_dm,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire [31:0] DDR_dq,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire [3:0] DDR_dqs_n,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire [3:0] DDR_dqs_p,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire [53:0] FIXED_IO_mio,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire FIXED_IO_ddr_vrn,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire FIXED_IO_ddr_vrp,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire FIXED_IO_ps_srstb,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire FIXED_IO_ps_clk,
  (* X_INTERFACE_IGNORE = "true" *)
  inout wire FIXED_IO_ps_porb,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [0:0] spike_in_valid,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [10:0] spike_in_neuron_id,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [7:0] spike_in_weight,
  (* X_INTERFACE_IGNORE = "true" *)
  input wire spike_in_ready,
  (* X_INTERFACE_IGNORE = "true" *)
  input wire spike_out_valid,
  (* X_INTERFACE_IGNORE = "true" *)
  input wire [10:0] spike_out_neuron_id,
  (* X_INTERFACE_IGNORE = "true" *)
  input wire [7:0] spike_out_weight,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [0:0] spike_out_ready,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [0:0] learn_weight_valid,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [3:0] learn_weight_group,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [6:0] learn_weight_src,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [6:0] learn_weight_dst,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [7:0] learn_weight_data,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [0:0] learn_weight_exc,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [0:0] learn_weight_is_inter,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [3:0] learn_weight_dst_group,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [3:0] learn_weight_fanout_idx,
  (* X_INTERFACE_IGNORE = "true" *)
  input wire learn_weight_ready,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [0:0] snn_enable,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [0:0] snn_reset,
  (* X_INTERFACE_IGNORE = "true" *)
  input wire snn_ready,
  (* X_INTERFACE_IGNORE = "true" *)
  input wire snn_busy,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [15:0] threshold_out,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [15:0] leak_rate_out,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire cfg_router_config_we,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [31:0] cfg_router_config_addr,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [31:0] cfg_router_config_wdata,
  (* X_INTERFACE_IGNORE = "true" *)
  input wire [31:0] cfg_router_config_rdata,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire cfg_neuron_config_we,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [9:0] cfg_neuron_config_addr,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [31:0] cfg_neuron_config_wdata,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [15:0] cfg_global_threshold,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [7:0] cfg_global_leak_rate,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [7:0] cfg_global_refrac_period,
  (* X_INTERFACE_IGNORE = "true" *)
  input wire [31:0] cfg_router_spike_count,
  (* X_INTERFACE_IGNORE = "true" *)
  input wire [31:0] cfg_neuron_spike_count,
  (* X_INTERFACE_IGNORE = "true" *)
  input wire cfg_fifo_overflow,
  (* X_INTERFACE_IGNORE = "true" *)
  input wire [7:0] cfg_active_neurons,
  (* X_INTERFACE_IGNORE = "true" *)
  input wire [31:0] cfg_throughput_counter,
  (* X_INTERFACE_IGNORE = "true" *)
  input wire [31:0] cfg_service_cycles_counter,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire clk_100mhz,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [0:0] rst_n_sync,
  (* X_INTERFACE_IGNORE = "true" *)
  output wire [0:0] debug_learning_active
);

  design_1 inst (
    .DDR_cas_n(DDR_cas_n),
    .DDR_cke(DDR_cke),
    .DDR_ck_n(DDR_ck_n),
    .DDR_ck_p(DDR_ck_p),
    .DDR_cs_n(DDR_cs_n),
    .DDR_reset_n(DDR_reset_n),
    .DDR_odt(DDR_odt),
    .DDR_ras_n(DDR_ras_n),
    .DDR_we_n(DDR_we_n),
    .DDR_ba(DDR_ba),
    .DDR_addr(DDR_addr),
    .DDR_dm(DDR_dm),
    .DDR_dq(DDR_dq),
    .DDR_dqs_n(DDR_dqs_n),
    .DDR_dqs_p(DDR_dqs_p),
    .FIXED_IO_mio(FIXED_IO_mio),
    .FIXED_IO_ddr_vrn(FIXED_IO_ddr_vrn),
    .FIXED_IO_ddr_vrp(FIXED_IO_ddr_vrp),
    .FIXED_IO_ps_srstb(FIXED_IO_ps_srstb),
    .FIXED_IO_ps_clk(FIXED_IO_ps_clk),
    .FIXED_IO_ps_porb(FIXED_IO_ps_porb),
    .spike_in_valid(spike_in_valid),
    .spike_in_neuron_id(spike_in_neuron_id),
    .spike_in_weight(spike_in_weight),
    .spike_in_ready(spike_in_ready),
    .spike_out_valid(spike_out_valid),
    .spike_out_neuron_id(spike_out_neuron_id),
    .spike_out_weight(spike_out_weight),
    .spike_out_ready(spike_out_ready),
    .learn_weight_valid(learn_weight_valid),
    .learn_weight_group(learn_weight_group),
    .learn_weight_src(learn_weight_src),
    .learn_weight_dst(learn_weight_dst),
    .learn_weight_data(learn_weight_data),
    .learn_weight_exc(learn_weight_exc),
    .learn_weight_is_inter(learn_weight_is_inter),
    .learn_weight_dst_group(learn_weight_dst_group),
    .learn_weight_fanout_idx(learn_weight_fanout_idx),
    .learn_weight_ready(learn_weight_ready),
    .snn_enable(snn_enable),
    .snn_reset(snn_reset),
    .snn_ready(snn_ready),
    .snn_busy(snn_busy),
    .threshold_out(threshold_out),
    .leak_rate_out(leak_rate_out),
    .cfg_router_config_we(cfg_router_config_we),
    .cfg_router_config_addr(cfg_router_config_addr),
    .cfg_router_config_wdata(cfg_router_config_wdata),
    .cfg_router_config_rdata(cfg_router_config_rdata),
    .cfg_neuron_config_we(cfg_neuron_config_we),
    .cfg_neuron_config_addr(cfg_neuron_config_addr),
    .cfg_neuron_config_wdata(cfg_neuron_config_wdata),
    .cfg_global_threshold(cfg_global_threshold),
    .cfg_global_leak_rate(cfg_global_leak_rate),
    .cfg_global_refrac_period(cfg_global_refrac_period),
    .cfg_router_spike_count(cfg_router_spike_count),
    .cfg_neuron_spike_count(cfg_neuron_spike_count),
    .cfg_fifo_overflow(cfg_fifo_overflow),
    .cfg_active_neurons(cfg_active_neurons),
    .cfg_throughput_counter(cfg_throughput_counter),
    .cfg_service_cycles_counter(cfg_service_cycles_counter),
    .clk_100mhz(clk_100mhz),
    .rst_n_sync(rst_n_sync),
    .debug_learning_active(debug_learning_active)
  );

endmodule
