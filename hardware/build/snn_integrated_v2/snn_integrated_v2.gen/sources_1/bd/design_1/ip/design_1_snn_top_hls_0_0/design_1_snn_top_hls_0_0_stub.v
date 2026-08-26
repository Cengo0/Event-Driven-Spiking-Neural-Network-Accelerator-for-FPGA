// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2025 Advanced Micro Devices, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2025.2 (lin64) Build 6299465 Fri Nov 14 12:34:56 MST 2025
// Date        : Mon Aug 24 12:55:03 2026
// Host        : Mariana running 64-bit Ubuntu 22.04.5 LTS
// Command     : write_verilog -force -mode synth_stub
//               /home/chipwisperer/Documents/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/build/snn_integrated_v2/snn_integrated_v2.gen/sources_1/bd/design_1/ip/design_1_snn_top_hls_0_0/design_1_snn_top_hls_0_0_stub.v
// Design      : design_1_snn_top_hls_0_0
// Purpose     : Stub declaration of top-level module interface
// Device      : xc7z020clg400-1
// --------------------------------------------------------------------------------

// This empty module with port declaration file causes synthesis tools to infer a black box for IP.
// The synthesis directives are for Synopsys Synplify support to prevent IO buffer insertion.
// Please paste the declaration into a Verilog source file or add the file as an additional source.
(* CHECK_LICENSE_TYPE = "design_1_snn_top_hls_0_0,snn_top_hls,{}" *) (* CORE_GENERATION_INFO = "design_1_snn_top_hls_0_0,snn_top_hls,{x_ipProduct=Vivado 2025.2,x_ipVendor=xilinx.com,x_ipLibrary=hls,x_ipName=snn_top_hls,x_ipVersion=1.0,x_ipCoreRevision=2114755266,x_ipLanguage=VERILOG,x_ipSimLanguage=MIXED,C_S_AXI_CTRL_ADDR_WIDTH=8,C_S_AXI_CTRL_DATA_WIDTH=32}" *) (* DowngradeIPIdentifiedWarnings = "yes" *) 
(* IP_DEFINITION_SOURCE = "HLS" *) (* X_CORE_INFO = "snn_top_hls,Vivado 2025.2" *) (* hls_module = "yes" *) 
module design_1_snn_top_hls_0_0(s_axi_ctrl_ARADDR, s_axi_ctrl_ARREADY, 
  s_axi_ctrl_ARVALID, s_axi_ctrl_AWADDR, s_axi_ctrl_AWREADY, s_axi_ctrl_AWVALID, 
  s_axi_ctrl_BREADY, s_axi_ctrl_BRESP, s_axi_ctrl_BVALID, s_axi_ctrl_RDATA, 
  s_axi_ctrl_RREADY, s_axi_ctrl_RRESP, s_axi_ctrl_RVALID, s_axi_ctrl_WDATA, 
  s_axi_ctrl_WREADY, s_axi_ctrl_WSTRB, s_axi_ctrl_WVALID, ap_clk, ap_rst_n, interrupt, 
  s_axis_spikes_TDATA, s_axis_spikes_TDEST, s_axis_spikes_TID, s_axis_spikes_TKEEP, 
  s_axis_spikes_TLAST, s_axis_spikes_TREADY, s_axis_spikes_TSTRB, s_axis_spikes_TUSER, 
  s_axis_spikes_TVALID, s_axis_data_TDATA, s_axis_data_TDEST, s_axis_data_TID, 
  s_axis_data_TKEEP, s_axis_data_TLAST, s_axis_data_TREADY, s_axis_data_TSTRB, 
  s_axis_data_TUSER, s_axis_data_TVALID, s_axis_weights_TDATA, s_axis_weights_TDEST, 
  s_axis_weights_TID, s_axis_weights_TKEEP, s_axis_weights_TLAST, s_axis_weights_TREADY, 
  s_axis_weights_TSTRB, s_axis_weights_TUSER, s_axis_weights_TVALID, m_axis_spikes_TDATA, 
  m_axis_spikes_TDEST, m_axis_spikes_TID, m_axis_spikes_TKEEP, m_axis_spikes_TLAST, 
  m_axis_spikes_TREADY, m_axis_spikes_TSTRB, m_axis_spikes_TUSER, m_axis_spikes_TVALID, 
  m_axis_weights_TDATA, m_axis_weights_TDEST, m_axis_weights_TID, m_axis_weights_TKEEP, 
  m_axis_weights_TLAST, m_axis_weights_TREADY, m_axis_weights_TSTRB, 
  m_axis_weights_TUSER, m_axis_weights_TVALID, spike_in_valid, spike_in_neuron_id, 
  spike_in_weight, spike_in_ready, spike_out_valid, spike_out_neuron_id, spike_out_weight, 
  spike_out_ready, learn_weight_valid, learn_weight_group, learn_weight_src, 
  learn_weight_dst, learn_weight_data, learn_weight_exc, learn_weight_is_inter, 
  learn_weight_dst_group, learn_weight_fanout_idx, learn_weight_ready, snn_enable, 
  snn_reset, threshold_out, leak_rate_out, snn_ready, snn_busy)
/* synthesis syn_black_box black_box_pad_pin="s_axi_ctrl_ARADDR[7:0],s_axi_ctrl_ARREADY,s_axi_ctrl_ARVALID,s_axi_ctrl_AWADDR[7:0],s_axi_ctrl_AWREADY,s_axi_ctrl_AWVALID,s_axi_ctrl_BREADY,s_axi_ctrl_BRESP[1:0],s_axi_ctrl_BVALID,s_axi_ctrl_RDATA[31:0],s_axi_ctrl_RREADY,s_axi_ctrl_RRESP[1:0],s_axi_ctrl_RVALID,s_axi_ctrl_WDATA[31:0],s_axi_ctrl_WREADY,s_axi_ctrl_WSTRB[3:0],s_axi_ctrl_WVALID,ap_rst_n,interrupt,s_axis_spikes_TDATA[31:0],s_axis_spikes_TDEST[0:0],s_axis_spikes_TID[0:0],s_axis_spikes_TKEEP[3:0],s_axis_spikes_TLAST[0:0],s_axis_spikes_TREADY,s_axis_spikes_TSTRB[3:0],s_axis_spikes_TUSER[0:0],s_axis_spikes_TVALID,s_axis_data_TDATA[31:0],s_axis_data_TDEST[0:0],s_axis_data_TID[0:0],s_axis_data_TKEEP[3:0],s_axis_data_TLAST[0:0],s_axis_data_TREADY,s_axis_data_TSTRB[3:0],s_axis_data_TUSER[0:0],s_axis_data_TVALID,s_axis_weights_TDATA[31:0],s_axis_weights_TDEST[0:0],s_axis_weights_TID[0:0],s_axis_weights_TKEEP[3:0],s_axis_weights_TLAST[0:0],s_axis_weights_TREADY,s_axis_weights_TSTRB[3:0],s_axis_weights_TUSER[0:0],s_axis_weights_TVALID,m_axis_spikes_TDATA[31:0],m_axis_spikes_TDEST[0:0],m_axis_spikes_TID[0:0],m_axis_spikes_TKEEP[3:0],m_axis_spikes_TLAST[0:0],m_axis_spikes_TREADY,m_axis_spikes_TSTRB[3:0],m_axis_spikes_TUSER[0:0],m_axis_spikes_TVALID,m_axis_weights_TDATA[31:0],m_axis_weights_TDEST[0:0],m_axis_weights_TID[0:0],m_axis_weights_TKEEP[3:0],m_axis_weights_TLAST[0:0],m_axis_weights_TREADY,m_axis_weights_TSTRB[3:0],m_axis_weights_TUSER[0:0],m_axis_weights_TVALID,spike_in_valid[0:0],spike_in_neuron_id[10:0],spike_in_weight[7:0],spike_in_ready[0:0],spike_out_valid[0:0],spike_out_neuron_id[10:0],spike_out_weight[7:0],spike_out_ready[0:0],learn_weight_valid[0:0],learn_weight_group[3:0],learn_weight_src[6:0],learn_weight_dst[6:0],learn_weight_data[7:0],learn_weight_exc[0:0],learn_weight_is_inter[0:0],learn_weight_dst_group[3:0],learn_weight_fanout_idx[3:0],learn_weight_ready[0:0],snn_enable[0:0],snn_reset[0:0],threshold_out[15:0],leak_rate_out[15:0],snn_ready[0:0],snn_busy[0:0]" */
/* synthesis syn_force_seq_prim="ap_clk" */;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl ARADDR" *) (* X_INTERFACE_MODE = "slave" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axi_ctrl, ADDR_WIDTH 8, DATA_WIDTH 32, PROTOCOL AXI4LITE, READ_WRITE_MODE READ_WRITE, FREQ_HZ 100000000, ID_WIDTH 0, AWUSER_WIDTH 0, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 0, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, HAS_WSTRB 1, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 1, PHASE 0.0, CLK_DOMAIN design_1_processing_system7_0_0_FCLK_CLK0, NUM_READ_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0" *) input [7:0]s_axi_ctrl_ARADDR;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl ARREADY" *) output s_axi_ctrl_ARREADY;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl ARVALID" *) input s_axi_ctrl_ARVALID;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl AWADDR" *) input [7:0]s_axi_ctrl_AWADDR;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl AWREADY" *) output s_axi_ctrl_AWREADY;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl AWVALID" *) input s_axi_ctrl_AWVALID;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl BREADY" *) input s_axi_ctrl_BREADY;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl BRESP" *) output [1:0]s_axi_ctrl_BRESP;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl BVALID" *) output s_axi_ctrl_BVALID;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl RDATA" *) output [31:0]s_axi_ctrl_RDATA;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl RREADY" *) input s_axi_ctrl_RREADY;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl RRESP" *) output [1:0]s_axi_ctrl_RRESP;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl RVALID" *) output s_axi_ctrl_RVALID;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl WDATA" *) input [31:0]s_axi_ctrl_WDATA;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl WREADY" *) output s_axi_ctrl_WREADY;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl WSTRB" *) input [3:0]s_axi_ctrl_WSTRB;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi_ctrl WVALID" *) input s_axi_ctrl_WVALID;
  (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 ap_clk CLK" *) (* X_INTERFACE_MODE = "slave" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ap_clk, ASSOCIATED_BUSIF s_axi_ctrl:s_axis_spikes:s_axis_data:s_axis_weights:m_axis_spikes:m_axis_weights, ASSOCIATED_RESET ap_rst_n, FREQ_HZ 100000000, FREQ_TOLERANCE_HZ 0, PHASE 0.0, CLK_DOMAIN design_1_processing_system7_0_0_FCLK_CLK0, INSERT_VIP 0" *) input ap_clk /* synthesis syn_isclock = 1 */;
  (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 ap_rst_n RST" *) (* X_INTERFACE_MODE = "slave" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME ap_rst_n, POLARITY ACTIVE_LOW, INSERT_VIP 0" *) input ap_rst_n;
  (* X_INTERFACE_INFO = "xilinx.com:signal:interrupt:1.0 interrupt INTERRUPT" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME interrupt, SENSITIVITY LEVEL_HIGH, PortWidth 1" *) output interrupt;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_spikes TDATA" *) (* X_INTERFACE_MODE = "slave" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axis_spikes, TUSER_WIDTH 1, TDATA_NUM_BYTES 4, TDEST_WIDTH 1, TID_WIDTH 1, HAS_TREADY 1, HAS_TSTRB 1, HAS_TKEEP 1, HAS_TLAST 1, FREQ_HZ 100000000, PHASE 0.0, CLK_DOMAIN design_1_processing_system7_0_0_FCLK_CLK0, LAYERED_METADATA undef, INSERT_VIP 0" *) input [31:0]s_axis_spikes_TDATA;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_spikes TDEST" *) input [0:0]s_axis_spikes_TDEST;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_spikes TID" *) input [0:0]s_axis_spikes_TID;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_spikes TKEEP" *) input [3:0]s_axis_spikes_TKEEP;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_spikes TLAST" *) input [0:0]s_axis_spikes_TLAST;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_spikes TREADY" *) output s_axis_spikes_TREADY;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_spikes TSTRB" *) input [3:0]s_axis_spikes_TSTRB;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_spikes TUSER" *) input [0:0]s_axis_spikes_TUSER;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_spikes TVALID" *) input s_axis_spikes_TVALID;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_data TDATA" *) (* X_INTERFACE_MODE = "slave" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axis_data, TUSER_WIDTH 1, TDATA_NUM_BYTES 4, TDEST_WIDTH 1, TID_WIDTH 1, HAS_TREADY 1, HAS_TSTRB 1, HAS_TKEEP 1, HAS_TLAST 1, FREQ_HZ 100000000, PHASE 0.0, CLK_DOMAIN design_1_processing_system7_0_0_FCLK_CLK0, LAYERED_METADATA undef, INSERT_VIP 0" *) input [31:0]s_axis_data_TDATA;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_data TDEST" *) input [0:0]s_axis_data_TDEST;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_data TID" *) input [0:0]s_axis_data_TID;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_data TKEEP" *) input [3:0]s_axis_data_TKEEP;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_data TLAST" *) input [0:0]s_axis_data_TLAST;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_data TREADY" *) output s_axis_data_TREADY;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_data TSTRB" *) input [3:0]s_axis_data_TSTRB;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_data TUSER" *) input [0:0]s_axis_data_TUSER;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_data TVALID" *) input s_axis_data_TVALID;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_weights TDATA" *) (* X_INTERFACE_MODE = "slave" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axis_weights, TUSER_WIDTH 1, TDATA_NUM_BYTES 4, TDEST_WIDTH 1, TID_WIDTH 1, HAS_TREADY 1, HAS_TSTRB 1, HAS_TKEEP 1, HAS_TLAST 1, FREQ_HZ 100000000, PHASE 0.0, CLK_DOMAIN design_1_processing_system7_0_0_FCLK_CLK0, LAYERED_METADATA undef, INSERT_VIP 0" *) input [31:0]s_axis_weights_TDATA;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_weights TDEST" *) input [0:0]s_axis_weights_TDEST;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_weights TID" *) input [0:0]s_axis_weights_TID;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_weights TKEEP" *) input [3:0]s_axis_weights_TKEEP;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_weights TLAST" *) input [0:0]s_axis_weights_TLAST;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_weights TREADY" *) output s_axis_weights_TREADY;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_weights TSTRB" *) input [3:0]s_axis_weights_TSTRB;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_weights TUSER" *) input [0:0]s_axis_weights_TUSER;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 s_axis_weights TVALID" *) input s_axis_weights_TVALID;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_spikes TDATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME m_axis_spikes, TUSER_WIDTH 1, TDATA_NUM_BYTES 4, TDEST_WIDTH 1, TID_WIDTH 1, HAS_TREADY 1, HAS_TSTRB 1, HAS_TKEEP 1, HAS_TLAST 1, FREQ_HZ 100000000, PHASE 0.0, CLK_DOMAIN design_1_processing_system7_0_0_FCLK_CLK0, LAYERED_METADATA undef, INSERT_VIP 0" *) output [31:0]m_axis_spikes_TDATA;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_spikes TDEST" *) output [0:0]m_axis_spikes_TDEST;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_spikes TID" *) output [0:0]m_axis_spikes_TID;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_spikes TKEEP" *) output [3:0]m_axis_spikes_TKEEP;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_spikes TLAST" *) output [0:0]m_axis_spikes_TLAST;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_spikes TREADY" *) input m_axis_spikes_TREADY;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_spikes TSTRB" *) output [3:0]m_axis_spikes_TSTRB;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_spikes TUSER" *) output [0:0]m_axis_spikes_TUSER;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_spikes TVALID" *) output m_axis_spikes_TVALID;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_weights TDATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME m_axis_weights, TUSER_WIDTH 1, TDATA_NUM_BYTES 4, TDEST_WIDTH 1, TID_WIDTH 1, HAS_TREADY 1, HAS_TSTRB 1, HAS_TKEEP 1, HAS_TLAST 1, FREQ_HZ 100000000, PHASE 0.0, CLK_DOMAIN design_1_processing_system7_0_0_FCLK_CLK0, LAYERED_METADATA undef, INSERT_VIP 0" *) output [31:0]m_axis_weights_TDATA;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_weights TDEST" *) output [0:0]m_axis_weights_TDEST;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_weights TID" *) output [0:0]m_axis_weights_TID;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_weights TKEEP" *) output [3:0]m_axis_weights_TKEEP;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_weights TLAST" *) output [0:0]m_axis_weights_TLAST;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_weights TREADY" *) input m_axis_weights_TREADY;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_weights TSTRB" *) output [3:0]m_axis_weights_TSTRB;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_weights TUSER" *) output [0:0]m_axis_weights_TUSER;
  (* X_INTERFACE_INFO = "xilinx.com:interface:axis:1.0 m_axis_weights TVALID" *) output m_axis_weights_TVALID;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 spike_in_valid DATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME spike_in_valid, LAYERED_METADATA undef" *) output [0:0]spike_in_valid;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 spike_in_neuron_id DATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME spike_in_neuron_id, LAYERED_METADATA undef" *) output [10:0]spike_in_neuron_id;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 spike_in_weight DATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME spike_in_weight, LAYERED_METADATA undef" *) output [7:0]spike_in_weight;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 spike_in_ready DATA" *) (* X_INTERFACE_MODE = "slave" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME spike_in_ready, LAYERED_METADATA undef" *) input [0:0]spike_in_ready;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 spike_out_valid DATA" *) (* X_INTERFACE_MODE = "slave" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME spike_out_valid, LAYERED_METADATA undef" *) input [0:0]spike_out_valid;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 spike_out_neuron_id DATA" *) (* X_INTERFACE_MODE = "slave" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME spike_out_neuron_id, LAYERED_METADATA undef" *) input [10:0]spike_out_neuron_id;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 spike_out_weight DATA" *) (* X_INTERFACE_MODE = "slave" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME spike_out_weight, LAYERED_METADATA undef" *) input [7:0]spike_out_weight;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 spike_out_ready DATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME spike_out_ready, LAYERED_METADATA undef" *) output [0:0]spike_out_ready;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_valid DATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_valid, LAYERED_METADATA undef" *) output [0:0]learn_weight_valid;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_group DATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_group, LAYERED_METADATA undef" *) output [3:0]learn_weight_group;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_src DATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_src, LAYERED_METADATA undef" *) output [6:0]learn_weight_src;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_dst DATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_dst, LAYERED_METADATA undef" *) output [6:0]learn_weight_dst;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_data DATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_data, LAYERED_METADATA undef" *) output [7:0]learn_weight_data;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_exc DATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_exc, LAYERED_METADATA undef" *) output [0:0]learn_weight_exc;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_is_inter DATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_is_inter, LAYERED_METADATA undef" *) output [0:0]learn_weight_is_inter;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_dst_group DATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_dst_group, LAYERED_METADATA undef" *) output [3:0]learn_weight_dst_group;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_fanout_idx DATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_fanout_idx, LAYERED_METADATA undef" *) output [3:0]learn_weight_fanout_idx;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 learn_weight_ready DATA" *) (* X_INTERFACE_MODE = "slave" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME learn_weight_ready, LAYERED_METADATA undef" *) input [0:0]learn_weight_ready;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 snn_enable DATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME snn_enable, LAYERED_METADATA undef" *) output [0:0]snn_enable;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 snn_reset DATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME snn_reset, LAYERED_METADATA undef" *) output [0:0]snn_reset;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 threshold_out DATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME threshold_out, LAYERED_METADATA undef" *) output [15:0]threshold_out;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 leak_rate_out DATA" *) (* X_INTERFACE_MODE = "master" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME leak_rate_out, LAYERED_METADATA undef" *) output [15:0]leak_rate_out;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 snn_ready DATA" *) (* X_INTERFACE_MODE = "slave" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME snn_ready, LAYERED_METADATA undef" *) input [0:0]snn_ready;
  (* X_INTERFACE_INFO = "xilinx.com:signal:data:1.0 snn_busy DATA" *) (* X_INTERFACE_MODE = "slave" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME snn_busy, LAYERED_METADATA undef" *) input [0:0]snn_busy;
endmodule
