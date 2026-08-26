// (c) Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// (c) Copyright 2022-2026 Advanced Micro Devices, Inc. All rights reserved.
// 
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


// IP VLNV: xilinx.com:hls:snn_top_hls:1.0
// IP Revision: 2114755266

(* X_CORE_INFO = "snn_top_hls,Vivado 2025.2" *)
(* CHECK_LICENSE_TYPE = "design_1_snn_top_hls_0_0,snn_top_hls,{}" *)
(* CORE_GENERATION_INFO = "design_1_snn_top_hls_0_0,snn_top_hls,{x_ipProduct=Vivado 2025.2,x_ipVendor=xilinx.com,x_ipLibrary=hls,x_ipName=snn_top_hls,x_ipVersion=1.0,x_ipCoreRevision=2114755266,x_ipLanguage=VERILOG,x_ipSimLanguage=MIXED,C_S_AXI_CTRL_ADDR_WIDTH=8,C_S_AXI_CTRL_DATA_WIDTH=32}" *)
(* IP_DEFINITION_SOURCE = "HLS" *)
(* DowngradeIPIdentifiedWarnings = "yes" *)
module design_1_snn_top_hls_0_0 (
  s_axi_ctrl_ARADDR,
  s_axi_ctrl_ARREADY,
  s_axi_ctrl_ARVALID,
  s_axi_ctrl_AWADDR,
  s_axi_ctrl_AWREADY,
  s_axi_ctrl_AWVALID,
  s_axi_ctrl_BREADY,
  s_axi_ctrl_BRESP,
  s_axi_ctrl_BVALID,
  s_axi_ctrl_RDATA,
  s_axi_ctrl_RREADY,
  s_axi_ctrl_RRESP,
  s_axi_ctrl_RVALID,
  s_axi_ctrl_WDATA,
  s_axi_ctrl_WREADY,
  s_axi_ctrl_WSTRB,
  s_axi_ctrl_WVALID,
  ap_clk,
  ap_rst_n,
  interrupt,
  s_axis_spikes_TDATA,
  s_axis_spikes_TDEST,
  s_axis_spikes_TID,
  s_axis_spikes_TKEEP,
  s_axis_spikes_TLAST,
  s_axis_spikes_TREADY,
  s_axis_spikes_TSTRB,
  s_axis_spikes_TUSER,
  s_axis_spikes_TVALID,
  s_axis_data_TDATA,
  s_axis_data_TDEST,
  s_axis_data_TID,
  s_axis_data_TKEEP,
  s_axis_data_TLAST,
  s_axis_data_TREADY,
  s_axis_data_TSTRB,
  s_axis_data_TUSER,
  s_axis_data_TVALID,
  s_axis_weights_TDATA,
  s_axis_weights_TDEST,
  s_axis_weights_TID,
  s_axis_weights_TKEEP,
  s_axis_weights_TLAST,
  s_axis_weights_TREADY,
  s_axis_weights_TSTRB,
  s_axis_weights_TUSER,
  s_axis_weights_TVALID,
  m_axis_spikes_TDATA,
  m_axis_spikes_TDEST,
  m_axis_spikes_TID,
  m_axis_spikes_TKEEP,
  m_axis_spikes_TLAST,
  m_axis_spikes_TREADY,
  m_axis_spikes_TSTRB,
  m_axis_spikes_TUSER,
  m_axis_spikes_TVALID,
  m_axis_weights_TDATA,
  m_axis_weights_TDEST,
  m_axis_weights_TID,
  m_axis_weights_TKEEP,
  m_axis_weights_TLAST,
  m_axis_weights_TREADY,
  m_axis_weights_TSTRB,
  m_axis_weights_TUSER,
  m_axis_weights_TVALID,
  spike_in_valid,
  spike_in_neuron_id,
  spike_in_weight,
  spike_in_ready,
  spike_out_valid,
  spike_out_neuron_id,
  spike_out_weight,
  spike_out_ready,
  learn_weight_valid,
  learn_weight_group,
  learn_weight_src,
  learn_weight_dst,
  learn_weight_data,
  learn_weight_exc,
  learn_weight_is_inter,
  learn_weight_dst_group,
  learn_weight_fanout_idx,
  learn_weight_ready,
  snn_enable,
  snn_reset,
  threshold_out,
  leak_rate_out,
  snn_ready,
  snn_busy
);

(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl ARADDR" *)
(* X_INTERFACE_MODE = "slave" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axi_ctrl, ADDR_WIDTH 8, DATA_WIDTH 32, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, FREQ_HZ 100000000, ID_WIDTH 0, AWUSER_WIDTH 0, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 0, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, HAS_WSTRB 1, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 1, PHASE 0.0, CLK_DOMAIN design_1_processing_system7_0_0_FCLK_CLK0, NUM_READ_THRE\
ADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0" *)
input wire [7 : 0] s_axi_ctrl_ARADDR;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl ARREADY" *)
output wire s_axi_ctrl_ARREADY;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl ARVALID" *)
input wire s_axi_ctrl_ARVALID;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl AWADDR" *)
input wire [7 : 0] s_axi_ctrl_AWADDR;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl AWREADY" *)
output wire s_axi_ctrl_AWREADY;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl AWVALID" *)
input wire s_axi_ctrl_AWVALID;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl BREADY" *)
input wire s_axi_ctrl_BREADY;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl BRESP" *)
output wire [1 : 0] s_axi_ctrl_BRESP;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl BVALID" *)
output wire s_axi_ctrl_BVALID;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl RDATA" *)
output wire [31 : 0] s_axi_ctrl_RDATA;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl RREADY" *)
input wire s_axi_ctrl_RREADY;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl RRESP" *)
output wire [1 : 0] s_axi_ctrl_RRESP;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl RVALID" *)
output wire s_axi_ctrl_RVALID;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl WDATA" *)
input wire [31 : 0] s_axi_ctrl_WDATA;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl WREADY" *)
output wire s_axi_ctrl_WREADY;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl WSTRB" *)
input wire [3 : 0] s_axi_ctrl_WSTRB;
(* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl WVALID" *)
input wire s_axi_ctrl_WVALID;
(* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 ap_clk CLK" *)
(* X_INTERFACE_MODE = "slave" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ap_clk, ASSOCIATED_BUSIF s_axi_ctrl:s_axis_spikes:s_axis_data:s_axis_weights:m_axis_spikes:m_axis_weights, ASSOCIATED_RESET ap_rst_n, FREQ_HZ 100000000, FREQ_TOLERANCE_HZ 0, PHASE 0.0, CLK_DOMAIN design_1_processing_system7_0_0_FCLK_CLK0, INSERT_VIP 0" *)
input wire ap_clk;
(* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 ap_rst_n RST" *)
(* X_INTERFACE_MODE = "slave" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ap_rst_n, POLARITY ACTIVE_LOW, INSERT_VIP 0" *)
input wire ap_rst_n;
(* X_INTERFACE_INFO = "xilinx.com:signal:interrupt:1.0 interrupt INTERRUPT" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME interrupt, SENSITIVITY LEVEL_HIGH, PortWidth 1" *)
output wire interrupt;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_spikes TDATA" *)
(* X_INTERFACE_MODE = "slave" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axis_spikes, TUSER_WIDTH 1, TDATA_NUM_BYTES 4, TDEST_WIDTH 1, TID_WIDTH 1, HAS_TREADY 1, HAS_TSTRB 1, HAS_TKEEP 1, HAS_TLAST 1, FREQ_HZ 100000000, PHASE 0.0, CLK_DOMAIN design_1_processing_system7_0_0_FCLK_CLK0, LAYERED_METADATA undef, INSERT_VIP 0" *)
input wire [31 : 0] s_axis_spikes_TDATA;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_spikes TDEST" *)
input wire [0 : 0] s_axis_spikes_TDEST;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_spikes TID" *)
input wire [0 : 0] s_axis_spikes_TID;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_spikes TKEEP" *)
input wire [3 : 0] s_axis_spikes_TKEEP;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_spikes TLAST" *)
input wire [0 : 0] s_axis_spikes_TLAST;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_spikes TREADY" *)
output wire s_axis_spikes_TREADY;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_spikes TSTRB" *)
input wire [3 : 0] s_axis_spikes_TSTRB;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_spikes TUSER" *)
input wire [0 : 0] s_axis_spikes_TUSER;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_spikes TVALID" *)
input wire s_axis_spikes_TVALID;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_data TDATA" *)
(* X_INTERFACE_MODE = "slave" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axis_data, TUSER_WIDTH 1, TDATA_NUM_BYTES 4, TDEST_WIDTH 1, TID_WIDTH 1, HAS_TREADY 1, HAS_TSTRB 1, HAS_TKEEP 1, HAS_TLAST 1, FREQ_HZ 100000000, PHASE 0.0, CLK_DOMAIN design_1_processing_system7_0_0_FCLK_CLK0, LAYERED_METADATA undef, INSERT_VIP 0" *)
input wire [31 : 0] s_axis_data_TDATA;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_data TDEST" *)
input wire [0 : 0] s_axis_data_TDEST;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_data TID" *)
input wire [0 : 0] s_axis_data_TID;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_data TKEEP" *)
input wire [3 : 0] s_axis_data_TKEEP;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_data TLAST" *)
input wire [0 : 0] s_axis_data_TLAST;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_data TREADY" *)
output wire s_axis_data_TREADY;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_data TSTRB" *)
input wire [3 : 0] s_axis_data_TSTRB;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_data TUSER" *)
input wire [0 : 0] s_axis_data_TUSER;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_data TVALID" *)
input wire s_axis_data_TVALID;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_weights TDATA" *)
(* X_INTERFACE_MODE = "slave" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axis_weights, TUSER_WIDTH 1, TDATA_NUM_BYTES 4, TDEST_WIDTH 1, TID_WIDTH 1, HAS_TREADY 1, HAS_TSTRB 1, HAS_TKEEP 1, HAS_TLAST 1, FREQ_HZ 100000000, PHASE 0.0, CLK_DOMAIN design_1_processing_system7_0_0_FCLK_CLK0, LAYERED_METADATA undef, INSERT_VIP 0" *)
input wire [31 : 0] s_axis_weights_TDATA;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_weights TDEST" *)
input wire [0 : 0] s_axis_weights_TDEST;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_weights TID" *)
input wire [0 : 0] s_axis_weights_TID;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_weights TKEEP" *)
input wire [3 : 0] s_axis_weights_TKEEP;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_weights TLAST" *)
input wire [0 : 0] s_axis_weights_TLAST;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_weights TREADY" *)
output wire s_axis_weights_TREADY;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_weights TSTRB" *)
input wire [3 : 0] s_axis_weights_TSTRB;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_weights TUSER" *)
input wire [0 : 0] s_axis_weights_TUSER;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_weights TVALID" *)
input wire s_axis_weights_TVALID;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_spikes TDATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME m_axis_spikes, TUSER_WIDTH 1, TDATA_NUM_BYTES 4, TDEST_WIDTH 1, TID_WIDTH 1, HAS_TREADY 1, HAS_TSTRB 1, HAS_TKEEP 1, HAS_TLAST 1, FREQ_HZ 100000000, PHASE 0.0, CLK_DOMAIN design_1_processing_system7_0_0_FCLK_CLK0, LAYERED_METADATA undef, INSERT_VIP 0" *)
output wire [31 : 0] m_axis_spikes_TDATA;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_spikes TDEST" *)
output wire [0 : 0] m_axis_spikes_TDEST;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_spikes TID" *)
output wire [0 : 0] m_axis_spikes_TID;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_spikes TKEEP" *)
output wire [3 : 0] m_axis_spikes_TKEEP;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_spikes TLAST" *)
output wire [0 : 0] m_axis_spikes_TLAST;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_spikes TREADY" *)
input wire m_axis_spikes_TREADY;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_spikes TSTRB" *)
output wire [3 : 0] m_axis_spikes_TSTRB;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_spikes TUSER" *)
output wire [0 : 0] m_axis_spikes_TUSER;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_spikes TVALID" *)
output wire m_axis_spikes_TVALID;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_weights TDATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME m_axis_weights, TUSER_WIDTH 1, TDATA_NUM_BYTES 4, TDEST_WIDTH 1, TID_WIDTH 1, HAS_TREADY 1, HAS_TSTRB 1, HAS_TKEEP 1, HAS_TLAST 1, FREQ_HZ 100000000, PHASE 0.0, CLK_DOMAIN design_1_processing_system7_0_0_FCLK_CLK0, LAYERED_METADATA undef, INSERT_VIP 0" *)
output wire [31 : 0] m_axis_weights_TDATA;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_weights TDEST" *)
output wire [0 : 0] m_axis_weights_TDEST;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_weights TID" *)
output wire [0 : 0] m_axis_weights_TID;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_weights TKEEP" *)
output wire [3 : 0] m_axis_weights_TKEEP;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_weights TLAST" *)
output wire [0 : 0] m_axis_weights_TLAST;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_weights TREADY" *)
input wire m_axis_weights_TREADY;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_weights TSTRB" *)
output wire [3 : 0] m_axis_weights_TSTRB;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_weights TUSER" *)
output wire [0 : 0] m_axis_weights_TUSER;
(* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_weights TVALID" *)
output wire m_axis_weights_TVALID;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 spike_in_valid DATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME spike_in_valid, LAYERED_METADATA undef" *)
output wire [0 : 0] spike_in_valid;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 spike_in_neuron_id DATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME spike_in_neuron_id, LAYERED_METADATA undef" *)
output wire [10 : 0] spike_in_neuron_id;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 spike_in_weight DATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME spike_in_weight, LAYERED_METADATA undef" *)
output wire [7 : 0] spike_in_weight;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 spike_in_ready DATA" *)
(* X_INTERFACE_MODE = "slave" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME spike_in_ready, LAYERED_METADATA undef" *)
input wire [0 : 0] spike_in_ready;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 spike_out_valid DATA" *)
(* X_INTERFACE_MODE = "slave" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME spike_out_valid, LAYERED_METADATA undef" *)
input wire [0 : 0] spike_out_valid;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 spike_out_neuron_id DATA" *)
(* X_INTERFACE_MODE = "slave" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME spike_out_neuron_id, LAYERED_METADATA undef" *)
input wire [10 : 0] spike_out_neuron_id;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 spike_out_weight DATA" *)
(* X_INTERFACE_MODE = "slave" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME spike_out_weight, LAYERED_METADATA undef" *)
input wire [7 : 0] spike_out_weight;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 spike_out_ready DATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME spike_out_ready, LAYERED_METADATA undef" *)
output wire [0 : 0] spike_out_ready;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_valid DATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_valid, LAYERED_METADATA undef" *)
output wire [0 : 0] learn_weight_valid;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_group DATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_group, LAYERED_METADATA undef" *)
output wire [3 : 0] learn_weight_group;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_src DATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_src, LAYERED_METADATA undef" *)
output wire [6 : 0] learn_weight_src;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_dst DATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_dst, LAYERED_METADATA undef" *)
output wire [6 : 0] learn_weight_dst;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_data DATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_data, LAYERED_METADATA undef" *)
output wire [7 : 0] learn_weight_data;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_exc DATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_exc, LAYERED_METADATA undef" *)
output wire [0 : 0] learn_weight_exc;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_is_inter DATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_is_inter, LAYERED_METADATA undef" *)
output wire [0 : 0] learn_weight_is_inter;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_dst_group DATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_dst_group, LAYERED_METADATA undef" *)
output wire [3 : 0] learn_weight_dst_group;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_fanout_idx DATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_fanout_idx, LAYERED_METADATA undef" *)
output wire [3 : 0] learn_weight_fanout_idx;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_ready DATA" *)
(* X_INTERFACE_MODE = "slave" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_ready, LAYERED_METADATA undef" *)
input wire [0 : 0] learn_weight_ready;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 snn_enable DATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME snn_enable, LAYERED_METADATA undef" *)
output wire [0 : 0] snn_enable;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 snn_reset DATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME snn_reset, LAYERED_METADATA undef" *)
output wire [0 : 0] snn_reset;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 threshold_out DATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME threshold_out, LAYERED_METADATA undef" *)
output wire [15 : 0] threshold_out;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 leak_rate_out DATA" *)
(* X_INTERFACE_MODE = "master" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME leak_rate_out, LAYERED_METADATA undef" *)
output wire [15 : 0] leak_rate_out;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 snn_ready DATA" *)
(* X_INTERFACE_MODE = "slave" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME snn_ready, LAYERED_METADATA undef" *)
input wire [0 : 0] snn_ready;
(* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 snn_busy DATA" *)
(* X_INTERFACE_MODE = "slave" *)
(* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME snn_busy, LAYERED_METADATA undef" *)
input wire [0 : 0] snn_busy;

(* SDX_KERNEL = "true" *)
(* SDX_KERNEL_TYPE = "hls" *)
(* SDX_KERNEL_SYNTH_INST = "inst" *)
  snn_top_hls #(
    .C_S_AXI_CTRL_ADDR_WIDTH(8),
    .C_S_AXI_CTRL_DATA_WIDTH(32)
  ) inst (
    .s_axi_ctrl_ARADDR(s_axi_ctrl_ARADDR),
    .s_axi_ctrl_ARREADY(s_axi_ctrl_ARREADY),
    .s_axi_ctrl_ARVALID(s_axi_ctrl_ARVALID),
    .s_axi_ctrl_AWADDR(s_axi_ctrl_AWADDR),
    .s_axi_ctrl_AWREADY(s_axi_ctrl_AWREADY),
    .s_axi_ctrl_AWVALID(s_axi_ctrl_AWVALID),
    .s_axi_ctrl_BREADY(s_axi_ctrl_BREADY),
    .s_axi_ctrl_BRESP(s_axi_ctrl_BRESP),
    .s_axi_ctrl_BVALID(s_axi_ctrl_BVALID),
    .s_axi_ctrl_RDATA(s_axi_ctrl_RDATA),
    .s_axi_ctrl_RREADY(s_axi_ctrl_RREADY),
    .s_axi_ctrl_RRESP(s_axi_ctrl_RRESP),
    .s_axi_ctrl_RVALID(s_axi_ctrl_RVALID),
    .s_axi_ctrl_WDATA(s_axi_ctrl_WDATA),
    .s_axi_ctrl_WREADY(s_axi_ctrl_WREADY),
    .s_axi_ctrl_WSTRB(s_axi_ctrl_WSTRB),
    .s_axi_ctrl_WVALID(s_axi_ctrl_WVALID),
    .ap_clk(ap_clk),
    .ap_rst_n(ap_rst_n),
    .interrupt(interrupt),
    .s_axis_spikes_TDATA(s_axis_spikes_TDATA),
    .s_axis_spikes_TDEST(s_axis_spikes_TDEST),
    .s_axis_spikes_TID(s_axis_spikes_TID),
    .s_axis_spikes_TKEEP(s_axis_spikes_TKEEP),
    .s_axis_spikes_TLAST(s_axis_spikes_TLAST),
    .s_axis_spikes_TREADY(s_axis_spikes_TREADY),
    .s_axis_spikes_TSTRB(s_axis_spikes_TSTRB),
    .s_axis_spikes_TUSER(s_axis_spikes_TUSER),
    .s_axis_spikes_TVALID(s_axis_spikes_TVALID),
    .s_axis_data_TDATA(s_axis_data_TDATA),
    .s_axis_data_TDEST(s_axis_data_TDEST),
    .s_axis_data_TID(s_axis_data_TID),
    .s_axis_data_TKEEP(s_axis_data_TKEEP),
    .s_axis_data_TLAST(s_axis_data_TLAST),
    .s_axis_data_TREADY(s_axis_data_TREADY),
    .s_axis_data_TSTRB(s_axis_data_TSTRB),
    .s_axis_data_TUSER(s_axis_data_TUSER),
    .s_axis_data_TVALID(s_axis_data_TVALID),
    .s_axis_weights_TDATA(s_axis_weights_TDATA),
    .s_axis_weights_TDEST(s_axis_weights_TDEST),
    .s_axis_weights_TID(s_axis_weights_TID),
    .s_axis_weights_TKEEP(s_axis_weights_TKEEP),
    .s_axis_weights_TLAST(s_axis_weights_TLAST),
    .s_axis_weights_TREADY(s_axis_weights_TREADY),
    .s_axis_weights_TSTRB(s_axis_weights_TSTRB),
    .s_axis_weights_TUSER(s_axis_weights_TUSER),
    .s_axis_weights_TVALID(s_axis_weights_TVALID),
    .m_axis_spikes_TDATA(m_axis_spikes_TDATA),
    .m_axis_spikes_TDEST(m_axis_spikes_TDEST),
    .m_axis_spikes_TID(m_axis_spikes_TID),
    .m_axis_spikes_TKEEP(m_axis_spikes_TKEEP),
    .m_axis_spikes_TLAST(m_axis_spikes_TLAST),
    .m_axis_spikes_TREADY(m_axis_spikes_TREADY),
    .m_axis_spikes_TSTRB(m_axis_spikes_TSTRB),
    .m_axis_spikes_TUSER(m_axis_spikes_TUSER),
    .m_axis_spikes_TVALID(m_axis_spikes_TVALID),
    .m_axis_weights_TDATA(m_axis_weights_TDATA),
    .m_axis_weights_TDEST(m_axis_weights_TDEST),
    .m_axis_weights_TID(m_axis_weights_TID),
    .m_axis_weights_TKEEP(m_axis_weights_TKEEP),
    .m_axis_weights_TLAST(m_axis_weights_TLAST),
    .m_axis_weights_TREADY(m_axis_weights_TREADY),
    .m_axis_weights_TSTRB(m_axis_weights_TSTRB),
    .m_axis_weights_TUSER(m_axis_weights_TUSER),
    .m_axis_weights_TVALID(m_axis_weights_TVALID),
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
    .threshold_out(threshold_out),
    .leak_rate_out(leak_rate_out),
    .snn_ready(snn_ready),
    .snn_busy(snn_busy)
  );
endmodule
