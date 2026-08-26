// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2025 Advanced Micro Devices, Inc. All Rights Reserved.
// --------------------------------------------------------------------------------
// Tool Version: Vivado v.2025.2 (lin64) Build 6299465 Fri Nov 14 12:34:56 MST 2025
// Date        : Mon Aug 24 12:57:04 2026
// Host        : Mariana running 64-bit Ubuntu 22.04.5 LTS
// Command     : write_verilog -force -mode funcsim
//               /home/chipwisperer/Documents/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/build/snn_integrated_v2/snn_integrated_v2.gen/sources_1/bd/design_1/ip/design_1_snn_config_regs_0_0/design_1_snn_config_regs_0_0_sim_netlist.v
// Design      : design_1_snn_config_regs_0_0
// Purpose     : This verilog netlist is a functional simulation representation of the design and should not be modified
//               or synthesized. This netlist cannot be used for SDF annotated simulation.
// Device      : xc7z020clg400-1
// --------------------------------------------------------------------------------
`timescale 1 ps / 1 ps

(* CHECK_LICENSE_TYPE = "design_1_snn_config_regs_0_0,snn_config_regs,{}" *) (* DowngradeIPIdentifiedWarnings = "yes" *) (* IP_DEFINITION_SOURCE = "module_ref" *) 
(* X_CORE_INFO = "snn_config_regs,Vivado 2025.2" *) 
(* NotValidForBitStream *)
module design_1_snn_config_regs_0_0
   (s_axi_aclk,
    s_axi_aresetn,
    s_axi_awaddr,
    s_axi_awprot,
    s_axi_awvalid,
    s_axi_awready,
    s_axi_wdata,
    s_axi_wstrb,
    s_axi_wvalid,
    s_axi_wready,
    s_axi_bresp,
    s_axi_bvalid,
    s_axi_bready,
    s_axi_araddr,
    s_axi_arprot,
    s_axi_arvalid,
    s_axi_arready,
    s_axi_rdata,
    s_axi_rresp,
    s_axi_rvalid,
    s_axi_rready,
    router_config_we,
    router_config_addr,
    router_config_wdata,
    router_config_rdata,
    neuron_config_we,
    neuron_config_addr,
    neuron_config_wdata,
    global_threshold,
    global_leak_rate,
    global_refrac_period,
    router_spike_count,
    neuron_spike_count,
    fifo_overflow,
    active_neurons,
    throughput_counter,
    service_cycles_counter);
  (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 s_axi_aclk CLK" *) (* X_INTERFACE_MODE = "slave" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axi_aclk, ASSOCIATED_BUSIF s_axi, ASSOCIATED_RESET s_axi_aresetn, FREQ_HZ 100000000, FREQ_TOLERANCE_HZ 0, PHASE 0.0, CLK_DOMAIN design_1_processing_system7_0_0_FCLK_CLK0, INSERT_VIP 0" *) input s_axi_aclk;
  (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 s_axi_aresetn RST" *) (* X_INTERFACE_MODE = "slave" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axi_aresetn, POLARITY ACTIVE_LOW, INSERT_VIP 0" *) input s_axi_aresetn;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi AWADDR" *) (* X_INTERFACE_MODE = "slave" *) (* X_INTERFACE_PARAMETER = "XIL_INTERFACENAME s_axi, DATA_WIDTH 32, PROTOCOL AXI4LITE, FREQ_HZ 100000000, ID_WIDTH 0, ADDR_WIDTH 6, AWUSER_WIDTH 0, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, READ_WRITE_MODE READ_WRITE, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 1, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, HAS_WSTRB 1, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 1, PHASE 0.0, CLK_DOMAIN design_1_processing_system7_0_0_FCLK_CLK0, NUM_READ_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0" *) input [5:0]s_axi_awaddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi AWPROT" *) input [2:0]s_axi_awprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi AWVALID" *) input s_axi_awvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi AWREADY" *) output s_axi_awready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi WDATA" *) input [31:0]s_axi_wdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi WSTRB" *) input [3:0]s_axi_wstrb;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi WVALID" *) input s_axi_wvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi WREADY" *) output s_axi_wready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi BRESP" *) output [1:0]s_axi_bresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi BVALID" *) output s_axi_bvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi BREADY" *) input s_axi_bready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi ARADDR" *) input [5:0]s_axi_araddr;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi ARPROT" *) input [2:0]s_axi_arprot;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi ARVALID" *) input s_axi_arvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi ARREADY" *) output s_axi_arready;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) output [31:0]s_axi_rdata;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RRESP" *) output [1:0]s_axi_rresp;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RVALID" *) output s_axi_rvalid;
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RREADY" *) input s_axi_rready;
  output router_config_we;
  output [31:0]router_config_addr;
  output [31:0]router_config_wdata;
  input [31:0]router_config_rdata;
  output neuron_config_we;
  output [9:0]neuron_config_addr;
  output [31:0]neuron_config_wdata;
  output [15:0]global_threshold;
  output [7:0]global_leak_rate;
  output [7:0]global_refrac_period;
  input [31:0]router_spike_count;
  input [31:0]neuron_spike_count;
  input fifo_overflow;
  input [7:0]active_neurons;
  input [31:0]throughput_counter;
  input [31:0]service_cycles_counter;

  wire \<const0> ;
  wire [7:0]active_neurons;
  wire fifo_overflow;
  wire [7:0]global_leak_rate;
  wire [7:0]global_refrac_period;
  wire [15:0]global_threshold;
  wire neuron_config_we;
  wire [31:0]neuron_spike_count;
  wire [31:0]router_config_addr;
  wire [31:0]router_config_rdata;
  wire [31:0]router_config_wdata;
  wire router_config_we;
  wire [31:0]router_spike_count;
  wire s_axi_aclk;
  wire [5:0]s_axi_araddr;
  wire s_axi_aresetn;
  wire s_axi_arready;
  wire s_axi_arvalid;
  wire [5:0]s_axi_awaddr;
  wire s_axi_awready;
  wire s_axi_awvalid;
  wire s_axi_bready;
  wire s_axi_bvalid;
  wire [31:0]s_axi_rdata;
  wire s_axi_rready;
  wire s_axi_rvalid;
  wire [31:0]s_axi_wdata;
  wire s_axi_wready;
  wire [3:0]s_axi_wstrb;
  wire s_axi_wvalid;
  wire [31:0]service_cycles_counter;
  wire [31:0]throughput_counter;

  assign neuron_config_addr[9:0] = router_config_addr[9:0];
  assign neuron_config_wdata[31:0] = router_config_wdata;
  assign s_axi_bresp[1] = \<const0> ;
  assign s_axi_bresp[0] = \<const0> ;
  assign s_axi_rresp[1] = \<const0> ;
  assign s_axi_rresp[0] = \<const0> ;
  GND GND
       (.G(\<const0> ));
  design_1_snn_config_regs_0_0_snn_config_regs inst
       (.active_neurons(active_neurons),
        .fifo_overflow(fifo_overflow),
        .global_leak_rate(global_leak_rate),
        .global_refrac_period(global_refrac_period),
        .global_threshold(global_threshold),
        .neuron_config_we(neuron_config_we),
        .neuron_spike_count(neuron_spike_count),
        .router_config_addr(router_config_addr),
        .router_config_rdata(router_config_rdata),
        .router_config_wdata(router_config_wdata),
        .router_config_we(router_config_we),
        .router_spike_count(router_spike_count),
        .s_axi_aclk(s_axi_aclk),
        .s_axi_araddr(s_axi_araddr[5:2]),
        .s_axi_aresetn(s_axi_aresetn),
        .s_axi_arready(s_axi_arready),
        .s_axi_arvalid(s_axi_arvalid),
        .s_axi_awaddr(s_axi_awaddr[5:2]),
        .s_axi_awready(s_axi_awready),
        .s_axi_awvalid(s_axi_awvalid),
        .s_axi_bready(s_axi_bready),
        .s_axi_bvalid(s_axi_bvalid),
        .s_axi_rdata(s_axi_rdata),
        .s_axi_rready(s_axi_rready),
        .s_axi_rvalid(s_axi_rvalid),
        .s_axi_wdata(s_axi_wdata),
        .s_axi_wready(s_axi_wready),
        .s_axi_wstrb(s_axi_wstrb),
        .s_axi_wvalid(s_axi_wvalid),
        .service_cycles_counter(service_cycles_counter),
        .throughput_counter(throughput_counter));
endmodule

(* ORIG_REF_NAME = "snn_config_regs" *) 
module design_1_snn_config_regs_0_0_snn_config_regs
   (s_axi_wready,
    s_axi_awready,
    s_axi_arready,
    router_config_addr,
    router_config_wdata,
    global_threshold,
    global_leak_rate,
    global_refrac_period,
    s_axi_rdata,
    s_axi_rvalid,
    router_config_we,
    neuron_config_we,
    s_axi_bvalid,
    active_neurons,
    throughput_counter,
    service_cycles_counter,
    s_axi_aclk,
    s_axi_awaddr,
    s_axi_wdata,
    s_axi_araddr,
    router_config_rdata,
    neuron_spike_count,
    router_spike_count,
    fifo_overflow,
    s_axi_aresetn,
    s_axi_wstrb,
    s_axi_awvalid,
    s_axi_wvalid,
    s_axi_arvalid,
    s_axi_bready,
    s_axi_rready);
  output s_axi_wready;
  output s_axi_awready;
  output s_axi_arready;
  output [31:0]router_config_addr;
  output [31:0]router_config_wdata;
  output [15:0]global_threshold;
  output [7:0]global_leak_rate;
  output [7:0]global_refrac_period;
  output [31:0]s_axi_rdata;
  output s_axi_rvalid;
  output router_config_we;
  output neuron_config_we;
  output s_axi_bvalid;
  input [7:0]active_neurons;
  input [31:0]throughput_counter;
  input [31:0]service_cycles_counter;
  input s_axi_aclk;
  input [3:0]s_axi_awaddr;
  input [31:0]s_axi_wdata;
  input [3:0]s_axi_araddr;
  input [31:0]router_config_rdata;
  input [31:0]neuron_spike_count;
  input [31:0]router_spike_count;
  input fifo_overflow;
  input s_axi_aresetn;
  input [3:0]s_axi_wstrb;
  input s_axi_awvalid;
  input s_axi_wvalid;
  input s_axi_arvalid;
  input s_axi_bready;
  input s_axi_rready;

  wire [7:0]active_neurons;
  wire ar_ready0;
  wire aw_en_i_1_n_0;
  wire aw_en_reg_n_0;
  wire aw_ready0;
  wire b_valid_i_1_n_0;
  wire \config_target[0]_i_1_n_0 ;
  wire \config_target[1]_i_1_n_0 ;
  wire \config_target[1]_i_2_n_0 ;
  wire \config_target_reg_n_0_[0] ;
  wire \config_target_reg_n_0_[1] ;
  wire config_we_pulse;
  wire config_we_pulse_i_1_n_0;
  wire fifo_overflow;
  wire [7:0]global_leak_rate;
  wire [7:0]global_refrac_period;
  wire [15:0]global_threshold;
  wire neuron_config_we;
  wire [31:0]neuron_spike_count;
  wire p_0_in;
  wire [31:7]p_1_in;
  wire [31:0]r_data;
  wire r_data0__0;
  wire \r_data[0]_i_2_n_0 ;
  wire \r_data[0]_i_3_n_0 ;
  wire \r_data[0]_i_4_n_0 ;
  wire \r_data[10]_i_2_n_0 ;
  wire \r_data[10]_i_3_n_0 ;
  wire \r_data[10]_i_4_n_0 ;
  wire \r_data[11]_i_2_n_0 ;
  wire \r_data[11]_i_3_n_0 ;
  wire \r_data[11]_i_4_n_0 ;
  wire \r_data[12]_i_2_n_0 ;
  wire \r_data[12]_i_3_n_0 ;
  wire \r_data[12]_i_4_n_0 ;
  wire \r_data[13]_i_2_n_0 ;
  wire \r_data[13]_i_3_n_0 ;
  wire \r_data[13]_i_4_n_0 ;
  wire \r_data[14]_i_2_n_0 ;
  wire \r_data[14]_i_3_n_0 ;
  wire \r_data[14]_i_4_n_0 ;
  wire \r_data[15]_i_2_n_0 ;
  wire \r_data[15]_i_3_n_0 ;
  wire \r_data[15]_i_4_n_0 ;
  wire \r_data[16]_i_2_n_0 ;
  wire \r_data[16]_i_3_n_0 ;
  wire \r_data[16]_i_4_n_0 ;
  wire \r_data[17]_i_2_n_0 ;
  wire \r_data[17]_i_3_n_0 ;
  wire \r_data[17]_i_4_n_0 ;
  wire \r_data[18]_i_2_n_0 ;
  wire \r_data[18]_i_3_n_0 ;
  wire \r_data[18]_i_4_n_0 ;
  wire \r_data[19]_i_2_n_0 ;
  wire \r_data[19]_i_3_n_0 ;
  wire \r_data[19]_i_4_n_0 ;
  wire \r_data[1]_i_2_n_0 ;
  wire \r_data[1]_i_3_n_0 ;
  wire \r_data[1]_i_4_n_0 ;
  wire \r_data[20]_i_2_n_0 ;
  wire \r_data[20]_i_3_n_0 ;
  wire \r_data[20]_i_4_n_0 ;
  wire \r_data[21]_i_2_n_0 ;
  wire \r_data[21]_i_3_n_0 ;
  wire \r_data[21]_i_4_n_0 ;
  wire \r_data[22]_i_2_n_0 ;
  wire \r_data[22]_i_3_n_0 ;
  wire \r_data[22]_i_4_n_0 ;
  wire \r_data[23]_i_2_n_0 ;
  wire \r_data[23]_i_3_n_0 ;
  wire \r_data[23]_i_4_n_0 ;
  wire \r_data[24]_i_2_n_0 ;
  wire \r_data[24]_i_3_n_0 ;
  wire \r_data[24]_i_4_n_0 ;
  wire \r_data[25]_i_2_n_0 ;
  wire \r_data[25]_i_3_n_0 ;
  wire \r_data[25]_i_4_n_0 ;
  wire \r_data[26]_i_2_n_0 ;
  wire \r_data[26]_i_3_n_0 ;
  wire \r_data[26]_i_4_n_0 ;
  wire \r_data[27]_i_2_n_0 ;
  wire \r_data[27]_i_3_n_0 ;
  wire \r_data[27]_i_4_n_0 ;
  wire \r_data[28]_i_2_n_0 ;
  wire \r_data[28]_i_3_n_0 ;
  wire \r_data[28]_i_4_n_0 ;
  wire \r_data[29]_i_2_n_0 ;
  wire \r_data[29]_i_3_n_0 ;
  wire \r_data[29]_i_4_n_0 ;
  wire \r_data[2]_i_2_n_0 ;
  wire \r_data[2]_i_3_n_0 ;
  wire \r_data[2]_i_4_n_0 ;
  wire \r_data[30]_i_2_n_0 ;
  wire \r_data[30]_i_3_n_0 ;
  wire \r_data[30]_i_4_n_0 ;
  wire \r_data[31]_i_2_n_0 ;
  wire \r_data[31]_i_3_n_0 ;
  wire \r_data[31]_i_4_n_0 ;
  wire \r_data[3]_i_2_n_0 ;
  wire \r_data[3]_i_3_n_0 ;
  wire \r_data[3]_i_4_n_0 ;
  wire \r_data[4]_i_2_n_0 ;
  wire \r_data[4]_i_3_n_0 ;
  wire \r_data[4]_i_4_n_0 ;
  wire \r_data[5]_i_2_n_0 ;
  wire \r_data[5]_i_3_n_0 ;
  wire \r_data[5]_i_4_n_0 ;
  wire \r_data[6]_i_2_n_0 ;
  wire \r_data[6]_i_3_n_0 ;
  wire \r_data[6]_i_4_n_0 ;
  wire \r_data[7]_i_2_n_0 ;
  wire \r_data[7]_i_3_n_0 ;
  wire \r_data[7]_i_4_n_0 ;
  wire \r_data[8]_i_2_n_0 ;
  wire \r_data[8]_i_3_n_0 ;
  wire \r_data[8]_i_4_n_0 ;
  wire \r_data[9]_i_2_n_0 ;
  wire \r_data[9]_i_3_n_0 ;
  wire \r_data[9]_i_4_n_0 ;
  wire r_valid_i_1_n_0;
  wire [7:7]reg_config_ctrl;
  wire \reg_config_ctrl_reg_n_0_[0] ;
  wire \reg_config_ctrl_reg_n_0_[1] ;
  wire \reg_config_ctrl_reg_n_0_[2] ;
  wire \reg_config_ctrl_reg_n_0_[3] ;
  wire \reg_config_ctrl_reg_n_0_[4] ;
  wire \reg_config_ctrl_reg_n_0_[5] ;
  wire \reg_config_ctrl_reg_n_0_[6] ;
  wire \reg_config_ctrl_reg_n_0_[7] ;
  wire \reg_config_wdata[15]_i_1_n_0 ;
  wire \reg_config_wdata[23]_i_1_n_0 ;
  wire \reg_config_wdata[31]_i_1_n_0 ;
  wire \reg_config_wdata[7]_i_1_n_0 ;
  wire [0:0]reg_leak_rate;
  wire [0:0]reg_refrac_period;
  wire \reg_threshold[15]_i_1_n_0 ;
  wire \reg_threshold[7]_i_1_n_0 ;
  wire [31:0]router_config_addr;
  wire [31:0]router_config_rdata;
  wire [31:0]router_config_wdata;
  wire router_config_we;
  wire [31:0]router_spike_count;
  wire s_axi_aclk;
  wire [3:0]s_axi_araddr;
  wire s_axi_aresetn;
  wire s_axi_arready;
  wire s_axi_arvalid;
  wire [3:0]s_axi_awaddr;
  wire s_axi_awready;
  wire s_axi_awvalid;
  wire s_axi_bready;
  wire s_axi_bvalid;
  wire [31:0]s_axi_rdata;
  wire s_axi_rready;
  wire s_axi_rvalid;
  wire [31:0]s_axi_wdata;
  wire s_axi_wready;
  wire [3:0]s_axi_wstrb;
  wire s_axi_wvalid;
  wire [3:0]sel0;
  wire [31:0]service_cycles_counter;
  wire [31:0]throughput_counter;
  wire w_ready0;
  wire [3:0]write_addr;
  wire write_en__1;

  FDRE \ar_addr_reg[2] 
       (.C(s_axi_aclk),
        .CE(ar_ready0),
        .D(s_axi_araddr[0]),
        .Q(sel0[0]),
        .R(p_0_in));
  FDRE \ar_addr_reg[3] 
       (.C(s_axi_aclk),
        .CE(ar_ready0),
        .D(s_axi_araddr[1]),
        .Q(sel0[1]),
        .R(p_0_in));
  FDRE \ar_addr_reg[4] 
       (.C(s_axi_aclk),
        .CE(ar_ready0),
        .D(s_axi_araddr[2]),
        .Q(sel0[2]),
        .R(p_0_in));
  FDRE \ar_addr_reg[5] 
       (.C(s_axi_aclk),
        .CE(ar_ready0),
        .D(s_axi_araddr[3]),
        .Q(sel0[3]),
        .R(p_0_in));
  LUT2 #(
    .INIT(4'h2)) 
    ar_ready_i_1
       (.I0(s_axi_arvalid),
        .I1(s_axi_arready),
        .O(ar_ready0));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi ARREADY" *) 
  FDRE ar_ready_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(ar_ready0),
        .Q(s_axi_arready),
        .R(p_0_in));
  FDRE \aw_addr_reg[2] 
       (.C(s_axi_aclk),
        .CE(aw_ready0),
        .D(s_axi_awaddr[0]),
        .Q(write_addr[0]),
        .R(p_0_in));
  FDRE \aw_addr_reg[3] 
       (.C(s_axi_aclk),
        .CE(aw_ready0),
        .D(s_axi_awaddr[1]),
        .Q(write_addr[1]),
        .R(p_0_in));
  FDRE \aw_addr_reg[4] 
       (.C(s_axi_aclk),
        .CE(aw_ready0),
        .D(s_axi_awaddr[2]),
        .Q(write_addr[2]),
        .R(p_0_in));
  FDRE \aw_addr_reg[5] 
       (.C(s_axi_aclk),
        .CE(aw_ready0),
        .D(s_axi_awaddr[3]),
        .Q(write_addr[3]),
        .R(p_0_in));
  LUT6 #(
    .INIT(64'hF7FFF700F700F700)) 
    aw_en_i_1
       (.I0(s_axi_awvalid),
        .I1(s_axi_wvalid),
        .I2(s_axi_awready),
        .I3(aw_en_reg_n_0),
        .I4(s_axi_bready),
        .I5(s_axi_bvalid),
        .O(aw_en_i_1_n_0));
  FDSE aw_en_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(aw_en_i_1_n_0),
        .Q(aw_en_reg_n_0),
        .S(p_0_in));
  LUT1 #(
    .INIT(2'h1)) 
    aw_ready_i_1
       (.I0(s_axi_aresetn),
        .O(p_0_in));
  LUT4 #(
    .INIT(16'h2000)) 
    aw_ready_i_2
       (.I0(aw_en_reg_n_0),
        .I1(s_axi_awready),
        .I2(s_axi_wvalid),
        .I3(s_axi_awvalid),
        .O(aw_ready0));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi AWREADY" *) 
  FDRE aw_ready_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(aw_ready0),
        .Q(s_axi_awready),
        .R(p_0_in));
  LUT6 #(
    .INIT(64'h0000FFFF80008000)) 
    b_valid_i_1
       (.I0(s_axi_awvalid),
        .I1(s_axi_wvalid),
        .I2(s_axi_awready),
        .I3(s_axi_wready),
        .I4(s_axi_bready),
        .I5(s_axi_bvalid),
        .O(b_valid_i_1_n_0));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi BVALID" *) 
  FDRE b_valid_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(b_valid_i_1_n_0),
        .Q(s_axi_bvalid),
        .R(p_0_in));
  LUT4 #(
    .INIT(16'hBF80)) 
    \config_target[0]_i_1 
       (.I0(s_axi_wdata[0]),
        .I1(write_en__1),
        .I2(\config_target[1]_i_2_n_0 ),
        .I3(\config_target_reg_n_0_[0] ),
        .O(\config_target[0]_i_1_n_0 ));
  LUT4 #(
    .INIT(16'hBF80)) 
    \config_target[1]_i_1 
       (.I0(s_axi_wdata[1]),
        .I1(write_en__1),
        .I2(\config_target[1]_i_2_n_0 ),
        .I3(\config_target_reg_n_0_[1] ),
        .O(\config_target[1]_i_1_n_0 ));
  LUT5 #(
    .INIT(32'h00000004)) 
    \config_target[1]_i_2 
       (.I0(write_addr[1]),
        .I1(s_axi_wstrb[0]),
        .I2(write_addr[2]),
        .I3(write_addr[0]),
        .I4(write_addr[3]),
        .O(\config_target[1]_i_2_n_0 ));
  FDRE \config_target_reg[0] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\config_target[0]_i_1_n_0 ),
        .Q(\config_target_reg_n_0_[0] ),
        .R(p_0_in));
  FDRE \config_target_reg[1] 
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(\config_target[1]_i_1_n_0 ),
        .Q(\config_target_reg_n_0_[1] ),
        .R(p_0_in));
  LUT6 #(
    .INIT(64'h0004000000000000)) 
    config_we_pulse_i_1
       (.I0(write_addr[3]),
        .I1(write_addr[1]),
        .I2(write_addr[0]),
        .I3(write_addr[2]),
        .I4(write_en__1),
        .I5(s_axi_aresetn),
        .O(config_we_pulse_i_1_n_0));
  FDRE config_we_pulse_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(config_we_pulse_i_1_n_0),
        .Q(config_we_pulse),
        .R(1'b0));
  (* SOFT_HLUTNM = "soft_lutpair1" *) 
  LUT3 #(
    .INIT(8'h40)) 
    neuron_config_we__0
       (.I0(\config_target_reg_n_0_[1] ),
        .I1(\config_target_reg_n_0_[0] ),
        .I2(config_we_pulse),
        .O(neuron_config_we));
  LUT3 #(
    .INIT(8'h08)) 
    r_data0
       (.I0(s_axi_arvalid),
        .I1(s_axi_arready),
        .I2(s_axi_rvalid),
        .O(r_data0__0));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[0]_i_1 
       (.I0(\r_data[0]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[0]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[0]_i_4_n_0 ),
        .O(r_data[0]));
  LUT6 #(
    .INIT(64'hFFFFFEAEAFAFFEAE)) 
    \r_data[0]_i_2 
       (.I0(sel0[2]),
        .I1(fifo_overflow),
        .I2(sel0[0]),
        .I3(throughput_counter[0]),
        .I4(sel0[1]),
        .I5(service_cycles_counter[0]),
        .O(\r_data[0]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[0]_i_3 
       (.I0(neuron_spike_count[0]),
        .I1(router_spike_count[0]),
        .I2(sel0[1]),
        .I3(global_leak_rate[0]),
        .I4(sel0[0]),
        .I5(global_threshold[0]),
        .O(\r_data[0]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[0]_i_4 
       (.I0(router_config_rdata[0]),
        .I1(router_config_wdata[0]),
        .I2(sel0[1]),
        .I3(router_config_addr[0]),
        .I4(sel0[0]),
        .I5(\reg_config_ctrl_reg_n_0_[0] ),
        .O(\r_data[0]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[10]_i_1 
       (.I0(\r_data[10]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[10]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[10]_i_4_n_0 ),
        .O(r_data[10]));
  LUT5 #(
    .INIT(32'hFFEAAFEA)) 
    \r_data[10]_i_2 
       (.I0(sel0[2]),
        .I1(throughput_counter[10]),
        .I2(sel0[0]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[10]),
        .O(\r_data[10]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[10]_i_3 
       (.I0(neuron_spike_count[10]),
        .I1(router_spike_count[10]),
        .I2(sel0[1]),
        .I3(global_refrac_period[2]),
        .I4(sel0[0]),
        .I5(global_threshold[10]),
        .O(\r_data[10]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[10]_i_4 
       (.I0(router_config_rdata[10]),
        .I1(router_config_wdata[10]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[10]),
        .O(\r_data[10]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[11]_i_1 
       (.I0(\r_data[11]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[11]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[11]_i_4_n_0 ),
        .O(r_data[11]));
  LUT5 #(
    .INIT(32'hFFEAAFEA)) 
    \r_data[11]_i_2 
       (.I0(sel0[2]),
        .I1(throughput_counter[11]),
        .I2(sel0[0]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[11]),
        .O(\r_data[11]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[11]_i_3 
       (.I0(neuron_spike_count[11]),
        .I1(router_spike_count[11]),
        .I2(sel0[1]),
        .I3(global_refrac_period[3]),
        .I4(sel0[0]),
        .I5(global_threshold[11]),
        .O(\r_data[11]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[11]_i_4 
       (.I0(router_config_rdata[11]),
        .I1(router_config_wdata[11]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[11]),
        .O(\r_data[11]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[12]_i_1 
       (.I0(\r_data[12]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[12]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[12]_i_4_n_0 ),
        .O(r_data[12]));
  LUT5 #(
    .INIT(32'hFAEAAAEA)) 
    \r_data[12]_i_2 
       (.I0(sel0[2]),
        .I1(throughput_counter[12]),
        .I2(sel0[0]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[12]),
        .O(\r_data[12]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[12]_i_3 
       (.I0(neuron_spike_count[12]),
        .I1(router_spike_count[12]),
        .I2(sel0[1]),
        .I3(global_refrac_period[4]),
        .I4(sel0[0]),
        .I5(global_threshold[12]),
        .O(\r_data[12]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[12]_i_4 
       (.I0(router_config_rdata[12]),
        .I1(router_config_wdata[12]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[12]),
        .O(\r_data[12]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[13]_i_1 
       (.I0(\r_data[13]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[13]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[13]_i_4_n_0 ),
        .O(r_data[13]));
  LUT5 #(
    .INIT(32'hFAEAAAEA)) 
    \r_data[13]_i_2 
       (.I0(sel0[2]),
        .I1(throughput_counter[13]),
        .I2(sel0[0]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[13]),
        .O(\r_data[13]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[13]_i_3 
       (.I0(neuron_spike_count[13]),
        .I1(router_spike_count[13]),
        .I2(sel0[1]),
        .I3(global_refrac_period[5]),
        .I4(sel0[0]),
        .I5(global_threshold[13]),
        .O(\r_data[13]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[13]_i_4 
       (.I0(router_config_rdata[13]),
        .I1(router_config_wdata[13]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[13]),
        .O(\r_data[13]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[14]_i_1 
       (.I0(\r_data[14]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[14]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[14]_i_4_n_0 ),
        .O(r_data[14]));
  LUT5 #(
    .INIT(32'h0000F838)) 
    \r_data[14]_i_2 
       (.I0(throughput_counter[14]),
        .I1(sel0[0]),
        .I2(sel0[1]),
        .I3(service_cycles_counter[14]),
        .I4(sel0[2]),
        .O(\r_data[14]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[14]_i_3 
       (.I0(neuron_spike_count[14]),
        .I1(router_spike_count[14]),
        .I2(sel0[1]),
        .I3(global_refrac_period[6]),
        .I4(sel0[0]),
        .I5(global_threshold[14]),
        .O(\r_data[14]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[14]_i_4 
       (.I0(router_config_rdata[14]),
        .I1(router_config_wdata[14]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[14]),
        .O(\r_data[14]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[15]_i_1 
       (.I0(\r_data[15]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[15]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[15]_i_4_n_0 ),
        .O(r_data[15]));
  LUT5 #(
    .INIT(32'hFAEAAAEA)) 
    \r_data[15]_i_2 
       (.I0(sel0[2]),
        .I1(throughput_counter[15]),
        .I2(sel0[0]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[15]),
        .O(\r_data[15]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[15]_i_3 
       (.I0(neuron_spike_count[15]),
        .I1(router_spike_count[15]),
        .I2(sel0[1]),
        .I3(global_refrac_period[7]),
        .I4(sel0[0]),
        .I5(global_threshold[15]),
        .O(\r_data[15]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[15]_i_4 
       (.I0(router_config_rdata[15]),
        .I1(router_config_wdata[15]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[15]),
        .O(\r_data[15]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[16]_i_1 
       (.I0(\r_data[16]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[16]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[16]_i_4_n_0 ),
        .O(r_data[16]));
  LUT5 #(
    .INIT(32'hFAEAAAEA)) 
    \r_data[16]_i_2 
       (.I0(sel0[2]),
        .I1(throughput_counter[16]),
        .I2(sel0[0]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[16]),
        .O(\r_data[16]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hA808)) 
    \r_data[16]_i_3 
       (.I0(sel0[1]),
        .I1(router_spike_count[16]),
        .I2(sel0[0]),
        .I3(neuron_spike_count[16]),
        .O(\r_data[16]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[16]_i_4 
       (.I0(router_config_rdata[16]),
        .I1(router_config_wdata[16]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[16]),
        .O(\r_data[16]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[17]_i_1 
       (.I0(\r_data[17]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[17]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[17]_i_4_n_0 ),
        .O(r_data[17]));
  LUT5 #(
    .INIT(32'h0000F838)) 
    \r_data[17]_i_2 
       (.I0(throughput_counter[17]),
        .I1(sel0[0]),
        .I2(sel0[1]),
        .I3(service_cycles_counter[17]),
        .I4(sel0[2]),
        .O(\r_data[17]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hA808)) 
    \r_data[17]_i_3 
       (.I0(sel0[1]),
        .I1(router_spike_count[17]),
        .I2(sel0[0]),
        .I3(neuron_spike_count[17]),
        .O(\r_data[17]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[17]_i_4 
       (.I0(router_config_rdata[17]),
        .I1(router_config_wdata[17]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[17]),
        .O(\r_data[17]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[18]_i_1 
       (.I0(\r_data[18]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[18]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[18]_i_4_n_0 ),
        .O(r_data[18]));
  LUT5 #(
    .INIT(32'hFFEAAFEA)) 
    \r_data[18]_i_2 
       (.I0(sel0[2]),
        .I1(throughput_counter[18]),
        .I2(sel0[0]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[18]),
        .O(\r_data[18]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hA808)) 
    \r_data[18]_i_3 
       (.I0(sel0[1]),
        .I1(router_spike_count[18]),
        .I2(sel0[0]),
        .I3(neuron_spike_count[18]),
        .O(\r_data[18]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[18]_i_4 
       (.I0(router_config_rdata[18]),
        .I1(router_config_wdata[18]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[18]),
        .O(\r_data[18]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[19]_i_1 
       (.I0(\r_data[19]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[19]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[19]_i_4_n_0 ),
        .O(r_data[19]));
  LUT5 #(
    .INIT(32'hFFEAAFEA)) 
    \r_data[19]_i_2 
       (.I0(sel0[2]),
        .I1(throughput_counter[19]),
        .I2(sel0[0]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[19]),
        .O(\r_data[19]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hA808)) 
    \r_data[19]_i_3 
       (.I0(sel0[1]),
        .I1(router_spike_count[19]),
        .I2(sel0[0]),
        .I3(neuron_spike_count[19]),
        .O(\r_data[19]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[19]_i_4 
       (.I0(router_config_rdata[19]),
        .I1(router_config_wdata[19]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[19]),
        .O(\r_data[19]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[1]_i_1 
       (.I0(\r_data[1]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[1]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[1]_i_4_n_0 ),
        .O(r_data[1]));
  LUT6 #(
    .INIT(64'hFAFAFEAEAAAAFEAE)) 
    \r_data[1]_i_2 
       (.I0(sel0[2]),
        .I1(active_neurons[0]),
        .I2(sel0[0]),
        .I3(throughput_counter[1]),
        .I4(sel0[1]),
        .I5(service_cycles_counter[1]),
        .O(\r_data[1]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[1]_i_3 
       (.I0(neuron_spike_count[1]),
        .I1(router_spike_count[1]),
        .I2(sel0[1]),
        .I3(global_leak_rate[1]),
        .I4(sel0[0]),
        .I5(global_threshold[1]),
        .O(\r_data[1]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[1]_i_4 
       (.I0(router_config_rdata[1]),
        .I1(router_config_wdata[1]),
        .I2(sel0[1]),
        .I3(router_config_addr[1]),
        .I4(sel0[0]),
        .I5(\reg_config_ctrl_reg_n_0_[1] ),
        .O(\r_data[1]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[20]_i_1 
       (.I0(\r_data[20]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[20]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[20]_i_4_n_0 ),
        .O(r_data[20]));
  LUT5 #(
    .INIT(32'h0000C808)) 
    \r_data[20]_i_2 
       (.I0(throughput_counter[20]),
        .I1(sel0[0]),
        .I2(sel0[1]),
        .I3(service_cycles_counter[20]),
        .I4(sel0[2]),
        .O(\r_data[20]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hA808)) 
    \r_data[20]_i_3 
       (.I0(sel0[1]),
        .I1(router_spike_count[20]),
        .I2(sel0[0]),
        .I3(neuron_spike_count[20]),
        .O(\r_data[20]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[20]_i_4 
       (.I0(router_config_rdata[20]),
        .I1(router_config_wdata[20]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[20]),
        .O(\r_data[20]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[21]_i_1 
       (.I0(\r_data[21]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[21]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[21]_i_4_n_0 ),
        .O(r_data[21]));
  LUT5 #(
    .INIT(32'hFAEAAAEA)) 
    \r_data[21]_i_2 
       (.I0(sel0[2]),
        .I1(throughput_counter[21]),
        .I2(sel0[0]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[21]),
        .O(\r_data[21]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hA808)) 
    \r_data[21]_i_3 
       (.I0(sel0[1]),
        .I1(router_spike_count[21]),
        .I2(sel0[0]),
        .I3(neuron_spike_count[21]),
        .O(\r_data[21]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[21]_i_4 
       (.I0(router_config_rdata[21]),
        .I1(router_config_wdata[21]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[21]),
        .O(\r_data[21]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[22]_i_1 
       (.I0(\r_data[22]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[22]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[22]_i_4_n_0 ),
        .O(r_data[22]));
  LUT5 #(
    .INIT(32'h0000F838)) 
    \r_data[22]_i_2 
       (.I0(throughput_counter[22]),
        .I1(sel0[0]),
        .I2(sel0[1]),
        .I3(service_cycles_counter[22]),
        .I4(sel0[2]),
        .O(\r_data[22]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hA808)) 
    \r_data[22]_i_3 
       (.I0(sel0[1]),
        .I1(router_spike_count[22]),
        .I2(sel0[0]),
        .I3(neuron_spike_count[22]),
        .O(\r_data[22]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[22]_i_4 
       (.I0(router_config_rdata[22]),
        .I1(router_config_wdata[22]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[22]),
        .O(\r_data[22]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[23]_i_1 
       (.I0(\r_data[23]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[23]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[23]_i_4_n_0 ),
        .O(r_data[23]));
  LUT5 #(
    .INIT(32'hFAEAAAEA)) 
    \r_data[23]_i_2 
       (.I0(sel0[2]),
        .I1(throughput_counter[23]),
        .I2(sel0[0]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[23]),
        .O(\r_data[23]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hA808)) 
    \r_data[23]_i_3 
       (.I0(sel0[1]),
        .I1(router_spike_count[23]),
        .I2(sel0[0]),
        .I3(neuron_spike_count[23]),
        .O(\r_data[23]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[23]_i_4 
       (.I0(router_config_rdata[23]),
        .I1(router_config_wdata[23]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[23]),
        .O(\r_data[23]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[24]_i_1 
       (.I0(\r_data[24]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[24]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[24]_i_4_n_0 ),
        .O(r_data[24]));
  LUT5 #(
    .INIT(32'h0000F838)) 
    \r_data[24]_i_2 
       (.I0(throughput_counter[24]),
        .I1(sel0[0]),
        .I2(sel0[1]),
        .I3(service_cycles_counter[24]),
        .I4(sel0[2]),
        .O(\r_data[24]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hA808)) 
    \r_data[24]_i_3 
       (.I0(sel0[1]),
        .I1(router_spike_count[24]),
        .I2(sel0[0]),
        .I3(neuron_spike_count[24]),
        .O(\r_data[24]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[24]_i_4 
       (.I0(router_config_rdata[24]),
        .I1(router_config_wdata[24]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[24]),
        .O(\r_data[24]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[25]_i_1 
       (.I0(\r_data[25]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[25]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[25]_i_4_n_0 ),
        .O(r_data[25]));
  LUT5 #(
    .INIT(32'hFFEAAFEA)) 
    \r_data[25]_i_2 
       (.I0(sel0[2]),
        .I1(throughput_counter[25]),
        .I2(sel0[0]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[25]),
        .O(\r_data[25]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hA808)) 
    \r_data[25]_i_3 
       (.I0(sel0[1]),
        .I1(router_spike_count[25]),
        .I2(sel0[0]),
        .I3(neuron_spike_count[25]),
        .O(\r_data[25]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[25]_i_4 
       (.I0(router_config_rdata[25]),
        .I1(router_config_wdata[25]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[25]),
        .O(\r_data[25]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[26]_i_1 
       (.I0(\r_data[26]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[26]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[26]_i_4_n_0 ),
        .O(r_data[26]));
  LUT5 #(
    .INIT(32'hFAEAAAEA)) 
    \r_data[26]_i_2 
       (.I0(sel0[2]),
        .I1(throughput_counter[26]),
        .I2(sel0[0]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[26]),
        .O(\r_data[26]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hA808)) 
    \r_data[26]_i_3 
       (.I0(sel0[1]),
        .I1(router_spike_count[26]),
        .I2(sel0[0]),
        .I3(neuron_spike_count[26]),
        .O(\r_data[26]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[26]_i_4 
       (.I0(router_config_rdata[26]),
        .I1(router_config_wdata[26]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[26]),
        .O(\r_data[26]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[27]_i_1 
       (.I0(\r_data[27]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[27]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[27]_i_4_n_0 ),
        .O(r_data[27]));
  LUT5 #(
    .INIT(32'hFAEAAAEA)) 
    \r_data[27]_i_2 
       (.I0(sel0[2]),
        .I1(throughput_counter[27]),
        .I2(sel0[0]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[27]),
        .O(\r_data[27]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hA808)) 
    \r_data[27]_i_3 
       (.I0(sel0[1]),
        .I1(router_spike_count[27]),
        .I2(sel0[0]),
        .I3(neuron_spike_count[27]),
        .O(\r_data[27]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[27]_i_4 
       (.I0(router_config_rdata[27]),
        .I1(router_config_wdata[27]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[27]),
        .O(\r_data[27]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[28]_i_1 
       (.I0(\r_data[28]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[28]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[28]_i_4_n_0 ),
        .O(r_data[28]));
  LUT5 #(
    .INIT(32'hFFEAAFEA)) 
    \r_data[28]_i_2 
       (.I0(sel0[2]),
        .I1(throughput_counter[28]),
        .I2(sel0[0]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[28]),
        .O(\r_data[28]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hA808)) 
    \r_data[28]_i_3 
       (.I0(sel0[1]),
        .I1(router_spike_count[28]),
        .I2(sel0[0]),
        .I3(neuron_spike_count[28]),
        .O(\r_data[28]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[28]_i_4 
       (.I0(router_config_rdata[28]),
        .I1(router_config_wdata[28]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[28]),
        .O(\r_data[28]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[29]_i_1 
       (.I0(\r_data[29]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[29]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[29]_i_4_n_0 ),
        .O(r_data[29]));
  LUT5 #(
    .INIT(32'h0000C808)) 
    \r_data[29]_i_2 
       (.I0(throughput_counter[29]),
        .I1(sel0[0]),
        .I2(sel0[1]),
        .I3(service_cycles_counter[29]),
        .I4(sel0[2]),
        .O(\r_data[29]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hA808)) 
    \r_data[29]_i_3 
       (.I0(sel0[1]),
        .I1(router_spike_count[29]),
        .I2(sel0[0]),
        .I3(neuron_spike_count[29]),
        .O(\r_data[29]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[29]_i_4 
       (.I0(router_config_rdata[29]),
        .I1(router_config_wdata[29]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[29]),
        .O(\r_data[29]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[2]_i_1 
       (.I0(\r_data[2]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[2]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[2]_i_4_n_0 ),
        .O(r_data[2]));
  LUT6 #(
    .INIT(64'hFAFAFEAEAAAAFEAE)) 
    \r_data[2]_i_2 
       (.I0(sel0[2]),
        .I1(active_neurons[1]),
        .I2(sel0[0]),
        .I3(throughput_counter[2]),
        .I4(sel0[1]),
        .I5(service_cycles_counter[2]),
        .O(\r_data[2]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[2]_i_3 
       (.I0(neuron_spike_count[2]),
        .I1(router_spike_count[2]),
        .I2(sel0[1]),
        .I3(global_leak_rate[2]),
        .I4(sel0[0]),
        .I5(global_threshold[2]),
        .O(\r_data[2]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[2]_i_4 
       (.I0(router_config_rdata[2]),
        .I1(router_config_wdata[2]),
        .I2(sel0[1]),
        .I3(router_config_addr[2]),
        .I4(sel0[0]),
        .I5(\reg_config_ctrl_reg_n_0_[2] ),
        .O(\r_data[2]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[30]_i_1 
       (.I0(\r_data[30]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[30]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[30]_i_4_n_0 ),
        .O(r_data[30]));
  LUT5 #(
    .INIT(32'hFFEAAFEA)) 
    \r_data[30]_i_2 
       (.I0(sel0[2]),
        .I1(throughput_counter[30]),
        .I2(sel0[0]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[30]),
        .O(\r_data[30]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hA808)) 
    \r_data[30]_i_3 
       (.I0(sel0[1]),
        .I1(router_spike_count[30]),
        .I2(sel0[0]),
        .I3(neuron_spike_count[30]),
        .O(\r_data[30]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[30]_i_4 
       (.I0(router_config_rdata[30]),
        .I1(router_config_wdata[30]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[30]),
        .O(\r_data[30]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[31]_i_1 
       (.I0(\r_data[31]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[31]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[31]_i_4_n_0 ),
        .O(r_data[31]));
  LUT5 #(
    .INIT(32'hFAEAAAEA)) 
    \r_data[31]_i_2 
       (.I0(sel0[2]),
        .I1(throughput_counter[31]),
        .I2(sel0[0]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[31]),
        .O(\r_data[31]_i_2_n_0 ));
  LUT4 #(
    .INIT(16'hA808)) 
    \r_data[31]_i_3 
       (.I0(sel0[1]),
        .I1(router_spike_count[31]),
        .I2(sel0[0]),
        .I3(neuron_spike_count[31]),
        .O(\r_data[31]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[31]_i_4 
       (.I0(router_config_rdata[31]),
        .I1(router_config_wdata[31]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[31]),
        .O(\r_data[31]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[3]_i_1 
       (.I0(\r_data[3]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[3]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[3]_i_4_n_0 ),
        .O(r_data[3]));
  LUT6 #(
    .INIT(64'hFAFAFEAEAAAAFEAE)) 
    \r_data[3]_i_2 
       (.I0(sel0[2]),
        .I1(active_neurons[2]),
        .I2(sel0[0]),
        .I3(throughput_counter[3]),
        .I4(sel0[1]),
        .I5(service_cycles_counter[3]),
        .O(\r_data[3]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[3]_i_3 
       (.I0(neuron_spike_count[3]),
        .I1(router_spike_count[3]),
        .I2(sel0[1]),
        .I3(global_leak_rate[3]),
        .I4(sel0[0]),
        .I5(global_threshold[3]),
        .O(\r_data[3]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[3]_i_4 
       (.I0(router_config_rdata[3]),
        .I1(router_config_wdata[3]),
        .I2(sel0[1]),
        .I3(router_config_addr[3]),
        .I4(sel0[0]),
        .I5(\reg_config_ctrl_reg_n_0_[3] ),
        .O(\r_data[3]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[4]_i_1 
       (.I0(\r_data[4]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[4]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[4]_i_4_n_0 ),
        .O(r_data[4]));
  LUT6 #(
    .INIT(64'h00000000CCE200E2)) 
    \r_data[4]_i_2 
       (.I0(active_neurons[3]),
        .I1(sel0[0]),
        .I2(throughput_counter[4]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[4]),
        .I5(sel0[2]),
        .O(\r_data[4]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[4]_i_3 
       (.I0(neuron_spike_count[4]),
        .I1(router_spike_count[4]),
        .I2(sel0[1]),
        .I3(global_leak_rate[4]),
        .I4(sel0[0]),
        .I5(global_threshold[4]),
        .O(\r_data[4]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[4]_i_4 
       (.I0(router_config_rdata[4]),
        .I1(router_config_wdata[4]),
        .I2(sel0[1]),
        .I3(router_config_addr[4]),
        .I4(sel0[0]),
        .I5(\reg_config_ctrl_reg_n_0_[4] ),
        .O(\r_data[4]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[5]_i_1 
       (.I0(\r_data[5]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[5]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[5]_i_4_n_0 ),
        .O(r_data[5]));
  LUT6 #(
    .INIT(64'hFAFAFEAEAAAAFEAE)) 
    \r_data[5]_i_2 
       (.I0(sel0[2]),
        .I1(active_neurons[4]),
        .I2(sel0[0]),
        .I3(throughput_counter[5]),
        .I4(sel0[1]),
        .I5(service_cycles_counter[5]),
        .O(\r_data[5]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[5]_i_3 
       (.I0(neuron_spike_count[5]),
        .I1(router_spike_count[5]),
        .I2(sel0[1]),
        .I3(global_leak_rate[5]),
        .I4(sel0[0]),
        .I5(global_threshold[5]),
        .O(\r_data[5]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[5]_i_4 
       (.I0(router_config_rdata[5]),
        .I1(router_config_wdata[5]),
        .I2(sel0[1]),
        .I3(router_config_addr[5]),
        .I4(sel0[0]),
        .I5(\reg_config_ctrl_reg_n_0_[5] ),
        .O(\r_data[5]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[6]_i_1 
       (.I0(\r_data[6]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[6]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[6]_i_4_n_0 ),
        .O(r_data[6]));
  LUT6 #(
    .INIT(64'hFAFAFEAEAAAAFEAE)) 
    \r_data[6]_i_2 
       (.I0(sel0[2]),
        .I1(active_neurons[5]),
        .I2(sel0[0]),
        .I3(throughput_counter[6]),
        .I4(sel0[1]),
        .I5(service_cycles_counter[6]),
        .O(\r_data[6]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[6]_i_3 
       (.I0(neuron_spike_count[6]),
        .I1(router_spike_count[6]),
        .I2(sel0[1]),
        .I3(global_leak_rate[6]),
        .I4(sel0[0]),
        .I5(global_threshold[6]),
        .O(\r_data[6]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[6]_i_4 
       (.I0(router_config_rdata[6]),
        .I1(router_config_wdata[6]),
        .I2(sel0[1]),
        .I3(router_config_addr[6]),
        .I4(sel0[0]),
        .I5(\reg_config_ctrl_reg_n_0_[6] ),
        .O(\r_data[6]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[7]_i_1 
       (.I0(\r_data[7]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[7]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[7]_i_4_n_0 ),
        .O(r_data[7]));
  LUT6 #(
    .INIT(64'hFAFAFEAEAAAAFEAE)) 
    \r_data[7]_i_2 
       (.I0(sel0[2]),
        .I1(active_neurons[6]),
        .I2(sel0[0]),
        .I3(throughput_counter[7]),
        .I4(sel0[1]),
        .I5(service_cycles_counter[7]),
        .O(\r_data[7]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[7]_i_3 
       (.I0(neuron_spike_count[7]),
        .I1(router_spike_count[7]),
        .I2(sel0[1]),
        .I3(global_leak_rate[7]),
        .I4(sel0[0]),
        .I5(global_threshold[7]),
        .O(\r_data[7]_i_3_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[7]_i_4 
       (.I0(router_config_rdata[7]),
        .I1(router_config_wdata[7]),
        .I2(sel0[1]),
        .I3(router_config_addr[7]),
        .I4(sel0[0]),
        .I5(\reg_config_ctrl_reg_n_0_[7] ),
        .O(\r_data[7]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[8]_i_1 
       (.I0(\r_data[8]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[8]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[8]_i_4_n_0 ),
        .O(r_data[8]));
  LUT6 #(
    .INIT(64'h00000000CCE200E2)) 
    \r_data[8]_i_2 
       (.I0(active_neurons[7]),
        .I1(sel0[0]),
        .I2(throughput_counter[8]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[8]),
        .I5(sel0[2]),
        .O(\r_data[8]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[8]_i_3 
       (.I0(neuron_spike_count[8]),
        .I1(router_spike_count[8]),
        .I2(sel0[1]),
        .I3(global_refrac_period[0]),
        .I4(sel0[0]),
        .I5(global_threshold[8]),
        .O(\r_data[8]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[8]_i_4 
       (.I0(router_config_rdata[8]),
        .I1(router_config_wdata[8]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[8]),
        .O(\r_data[8]_i_4_n_0 ));
  LUT5 #(
    .INIT(32'hB8BBB888)) 
    \r_data[9]_i_1 
       (.I0(\r_data[9]_i_2_n_0 ),
        .I1(sel0[3]),
        .I2(\r_data[9]_i_3_n_0 ),
        .I3(sel0[2]),
        .I4(\r_data[9]_i_4_n_0 ),
        .O(r_data[9]));
  LUT5 #(
    .INIT(32'hFFEAAFEA)) 
    \r_data[9]_i_2 
       (.I0(sel0[2]),
        .I1(throughput_counter[9]),
        .I2(sel0[0]),
        .I3(sel0[1]),
        .I4(service_cycles_counter[9]),
        .O(\r_data[9]_i_2_n_0 ));
  LUT6 #(
    .INIT(64'hAFA0CFCFAFA0C0C0)) 
    \r_data[9]_i_3 
       (.I0(neuron_spike_count[9]),
        .I1(router_spike_count[9]),
        .I2(sel0[1]),
        .I3(global_refrac_period[1]),
        .I4(sel0[0]),
        .I5(global_threshold[9]),
        .O(\r_data[9]_i_3_n_0 ));
  LUT5 #(
    .INIT(32'hAFC0A0C0)) 
    \r_data[9]_i_4 
       (.I0(router_config_rdata[9]),
        .I1(router_config_wdata[9]),
        .I2(sel0[1]),
        .I3(sel0[0]),
        .I4(router_config_addr[9]),
        .O(\r_data[9]_i_4_n_0 ));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[0] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[0]),
        .Q(s_axi_rdata[0]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[10] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[10]),
        .Q(s_axi_rdata[10]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[11] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[11]),
        .Q(s_axi_rdata[11]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[12] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[12]),
        .Q(s_axi_rdata[12]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[13] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[13]),
        .Q(s_axi_rdata[13]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[14] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[14]),
        .Q(s_axi_rdata[14]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[15] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[15]),
        .Q(s_axi_rdata[15]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[16] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[16]),
        .Q(s_axi_rdata[16]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[17] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[17]),
        .Q(s_axi_rdata[17]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[18] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[18]),
        .Q(s_axi_rdata[18]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[19] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[19]),
        .Q(s_axi_rdata[19]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[1] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[1]),
        .Q(s_axi_rdata[1]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[20] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[20]),
        .Q(s_axi_rdata[20]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[21] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[21]),
        .Q(s_axi_rdata[21]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[22] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[22]),
        .Q(s_axi_rdata[22]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[23] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[23]),
        .Q(s_axi_rdata[23]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[24] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[24]),
        .Q(s_axi_rdata[24]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[25] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[25]),
        .Q(s_axi_rdata[25]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[26] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[26]),
        .Q(s_axi_rdata[26]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[27] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[27]),
        .Q(s_axi_rdata[27]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[28] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[28]),
        .Q(s_axi_rdata[28]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[29] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[29]),
        .Q(s_axi_rdata[29]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[2] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[2]),
        .Q(s_axi_rdata[2]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[30] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[30]),
        .Q(s_axi_rdata[30]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[31] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[31]),
        .Q(s_axi_rdata[31]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[3] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[3]),
        .Q(s_axi_rdata[3]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[4] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[4]),
        .Q(s_axi_rdata[4]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[5] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[5]),
        .Q(s_axi_rdata[5]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[6] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[6]),
        .Q(s_axi_rdata[6]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[7] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[7]),
        .Q(s_axi_rdata[7]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[8] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[8]),
        .Q(s_axi_rdata[8]),
        .R(p_0_in));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *) 
  FDRE \r_data_reg[9] 
       (.C(s_axi_aclk),
        .CE(r_data0__0),
        .D(r_data[9]),
        .Q(s_axi_rdata[9]),
        .R(p_0_in));
  LUT4 #(
    .INIT(16'h08F8)) 
    r_valid_i_1
       (.I0(s_axi_arready),
        .I1(s_axi_arvalid),
        .I2(s_axi_rvalid),
        .I3(s_axi_rready),
        .O(r_valid_i_1_n_0));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RVALID" *) 
  FDRE r_valid_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(r_valid_i_1_n_0),
        .Q(s_axi_rvalid),
        .R(p_0_in));
  LUT6 #(
    .INIT(64'h0000000000002000)) 
    \reg_config_addr[15]_i_1 
       (.I0(write_en__1),
        .I1(write_addr[3]),
        .I2(write_addr[0]),
        .I3(s_axi_wstrb[1]),
        .I4(write_addr[1]),
        .I5(write_addr[2]),
        .O(p_1_in[15]));
  LUT6 #(
    .INIT(64'h0000000000002000)) 
    \reg_config_addr[23]_i_1 
       (.I0(write_en__1),
        .I1(write_addr[3]),
        .I2(write_addr[0]),
        .I3(s_axi_wstrb[2]),
        .I4(write_addr[1]),
        .I5(write_addr[2]),
        .O(p_1_in[23]));
  LUT6 #(
    .INIT(64'h0000000000002000)) 
    \reg_config_addr[31]_i_1 
       (.I0(write_en__1),
        .I1(write_addr[3]),
        .I2(write_addr[0]),
        .I3(s_axi_wstrb[3]),
        .I4(write_addr[1]),
        .I5(write_addr[2]),
        .O(p_1_in[31]));
  (* SOFT_HLUTNM = "soft_lutpair0" *) 
  LUT4 #(
    .INIT(16'h8000)) 
    \reg_config_addr[31]_i_2 
       (.I0(s_axi_awvalid),
        .I1(s_axi_wvalid),
        .I2(s_axi_awready),
        .I3(s_axi_wready),
        .O(write_en__1));
  LUT6 #(
    .INIT(64'h0000000000002000)) 
    \reg_config_addr[7]_i_1 
       (.I0(write_en__1),
        .I1(write_addr[3]),
        .I2(write_addr[0]),
        .I3(s_axi_wstrb[0]),
        .I4(write_addr[1]),
        .I5(write_addr[2]),
        .O(p_1_in[7]));
  FDRE \reg_config_addr_reg[0] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(s_axi_wdata[0]),
        .Q(router_config_addr[0]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[10] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(s_axi_wdata[10]),
        .Q(router_config_addr[10]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[11] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(s_axi_wdata[11]),
        .Q(router_config_addr[11]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[12] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(s_axi_wdata[12]),
        .Q(router_config_addr[12]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[13] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(s_axi_wdata[13]),
        .Q(router_config_addr[13]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[14] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(s_axi_wdata[14]),
        .Q(router_config_addr[14]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[15] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(s_axi_wdata[15]),
        .Q(router_config_addr[15]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[16] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(s_axi_wdata[16]),
        .Q(router_config_addr[16]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[17] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(s_axi_wdata[17]),
        .Q(router_config_addr[17]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[18] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(s_axi_wdata[18]),
        .Q(router_config_addr[18]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[19] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(s_axi_wdata[19]),
        .Q(router_config_addr[19]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[1] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(s_axi_wdata[1]),
        .Q(router_config_addr[1]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[20] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(s_axi_wdata[20]),
        .Q(router_config_addr[20]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[21] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(s_axi_wdata[21]),
        .Q(router_config_addr[21]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[22] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(s_axi_wdata[22]),
        .Q(router_config_addr[22]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[23] 
       (.C(s_axi_aclk),
        .CE(p_1_in[23]),
        .D(s_axi_wdata[23]),
        .Q(router_config_addr[23]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[24] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(s_axi_wdata[24]),
        .Q(router_config_addr[24]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[25] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(s_axi_wdata[25]),
        .Q(router_config_addr[25]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[26] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(s_axi_wdata[26]),
        .Q(router_config_addr[26]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[27] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(s_axi_wdata[27]),
        .Q(router_config_addr[27]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[28] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(s_axi_wdata[28]),
        .Q(router_config_addr[28]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[29] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(s_axi_wdata[29]),
        .Q(router_config_addr[29]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[2] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(s_axi_wdata[2]),
        .Q(router_config_addr[2]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[30] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(s_axi_wdata[30]),
        .Q(router_config_addr[30]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[31] 
       (.C(s_axi_aclk),
        .CE(p_1_in[31]),
        .D(s_axi_wdata[31]),
        .Q(router_config_addr[31]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[3] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(s_axi_wdata[3]),
        .Q(router_config_addr[3]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[4] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(s_axi_wdata[4]),
        .Q(router_config_addr[4]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[5] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(s_axi_wdata[5]),
        .Q(router_config_addr[5]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[6] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(s_axi_wdata[6]),
        .Q(router_config_addr[6]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[7] 
       (.C(s_axi_aclk),
        .CE(p_1_in[7]),
        .D(s_axi_wdata[7]),
        .Q(router_config_addr[7]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[8] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(s_axi_wdata[8]),
        .Q(router_config_addr[8]),
        .R(p_0_in));
  FDRE \reg_config_addr_reg[9] 
       (.C(s_axi_aclk),
        .CE(p_1_in[15]),
        .D(s_axi_wdata[9]),
        .Q(router_config_addr[9]),
        .R(p_0_in));
  LUT6 #(
    .INIT(64'h0000000000000020)) 
    \reg_config_ctrl[7]_i_1 
       (.I0(write_en__1),
        .I1(write_addr[3]),
        .I2(s_axi_wstrb[0]),
        .I3(write_addr[2]),
        .I4(write_addr[0]),
        .I5(write_addr[1]),
        .O(reg_config_ctrl));
  FDRE \reg_config_ctrl_reg[0] 
       (.C(s_axi_aclk),
        .CE(reg_config_ctrl),
        .D(s_axi_wdata[0]),
        .Q(\reg_config_ctrl_reg_n_0_[0] ),
        .R(p_0_in));
  FDRE \reg_config_ctrl_reg[1] 
       (.C(s_axi_aclk),
        .CE(reg_config_ctrl),
        .D(s_axi_wdata[1]),
        .Q(\reg_config_ctrl_reg_n_0_[1] ),
        .R(p_0_in));
  FDRE \reg_config_ctrl_reg[2] 
       (.C(s_axi_aclk),
        .CE(reg_config_ctrl),
        .D(s_axi_wdata[2]),
        .Q(\reg_config_ctrl_reg_n_0_[2] ),
        .R(p_0_in));
  FDRE \reg_config_ctrl_reg[3] 
       (.C(s_axi_aclk),
        .CE(reg_config_ctrl),
        .D(s_axi_wdata[3]),
        .Q(\reg_config_ctrl_reg_n_0_[3] ),
        .R(p_0_in));
  FDRE \reg_config_ctrl_reg[4] 
       (.C(s_axi_aclk),
        .CE(reg_config_ctrl),
        .D(s_axi_wdata[4]),
        .Q(\reg_config_ctrl_reg_n_0_[4] ),
        .R(p_0_in));
  FDRE \reg_config_ctrl_reg[5] 
       (.C(s_axi_aclk),
        .CE(reg_config_ctrl),
        .D(s_axi_wdata[5]),
        .Q(\reg_config_ctrl_reg_n_0_[5] ),
        .R(p_0_in));
  FDRE \reg_config_ctrl_reg[6] 
       (.C(s_axi_aclk),
        .CE(reg_config_ctrl),
        .D(s_axi_wdata[6]),
        .Q(\reg_config_ctrl_reg_n_0_[6] ),
        .R(p_0_in));
  FDRE \reg_config_ctrl_reg[7] 
       (.C(s_axi_aclk),
        .CE(reg_config_ctrl),
        .D(s_axi_wdata[7]),
        .Q(\reg_config_ctrl_reg_n_0_[7] ),
        .R(p_0_in));
  LUT6 #(
    .INIT(64'h0000000000002000)) 
    \reg_config_wdata[15]_i_1 
       (.I0(write_en__1),
        .I1(write_addr[3]),
        .I2(write_addr[1]),
        .I3(s_axi_wstrb[1]),
        .I4(write_addr[0]),
        .I5(write_addr[2]),
        .O(\reg_config_wdata[15]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0000000000002000)) 
    \reg_config_wdata[23]_i_1 
       (.I0(write_en__1),
        .I1(write_addr[3]),
        .I2(write_addr[1]),
        .I3(s_axi_wstrb[2]),
        .I4(write_addr[0]),
        .I5(write_addr[2]),
        .O(\reg_config_wdata[23]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0000000000002000)) 
    \reg_config_wdata[31]_i_1 
       (.I0(write_en__1),
        .I1(write_addr[3]),
        .I2(write_addr[1]),
        .I3(s_axi_wstrb[3]),
        .I4(write_addr[0]),
        .I5(write_addr[2]),
        .O(\reg_config_wdata[31]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0000000000002000)) 
    \reg_config_wdata[7]_i_1 
       (.I0(write_en__1),
        .I1(write_addr[3]),
        .I2(write_addr[1]),
        .I3(s_axi_wstrb[0]),
        .I4(write_addr[0]),
        .I5(write_addr[2]),
        .O(\reg_config_wdata[7]_i_1_n_0 ));
  FDRE \reg_config_wdata_reg[0] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[7]_i_1_n_0 ),
        .D(s_axi_wdata[0]),
        .Q(router_config_wdata[0]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[10] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[15]_i_1_n_0 ),
        .D(s_axi_wdata[10]),
        .Q(router_config_wdata[10]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[11] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[15]_i_1_n_0 ),
        .D(s_axi_wdata[11]),
        .Q(router_config_wdata[11]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[12] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[15]_i_1_n_0 ),
        .D(s_axi_wdata[12]),
        .Q(router_config_wdata[12]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[13] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[15]_i_1_n_0 ),
        .D(s_axi_wdata[13]),
        .Q(router_config_wdata[13]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[14] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[15]_i_1_n_0 ),
        .D(s_axi_wdata[14]),
        .Q(router_config_wdata[14]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[15] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[15]_i_1_n_0 ),
        .D(s_axi_wdata[15]),
        .Q(router_config_wdata[15]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[16] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[23]_i_1_n_0 ),
        .D(s_axi_wdata[16]),
        .Q(router_config_wdata[16]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[17] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[23]_i_1_n_0 ),
        .D(s_axi_wdata[17]),
        .Q(router_config_wdata[17]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[18] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[23]_i_1_n_0 ),
        .D(s_axi_wdata[18]),
        .Q(router_config_wdata[18]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[19] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[23]_i_1_n_0 ),
        .D(s_axi_wdata[19]),
        .Q(router_config_wdata[19]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[1] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[7]_i_1_n_0 ),
        .D(s_axi_wdata[1]),
        .Q(router_config_wdata[1]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[20] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[23]_i_1_n_0 ),
        .D(s_axi_wdata[20]),
        .Q(router_config_wdata[20]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[21] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[23]_i_1_n_0 ),
        .D(s_axi_wdata[21]),
        .Q(router_config_wdata[21]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[22] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[23]_i_1_n_0 ),
        .D(s_axi_wdata[22]),
        .Q(router_config_wdata[22]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[23] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[23]_i_1_n_0 ),
        .D(s_axi_wdata[23]),
        .Q(router_config_wdata[23]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[24] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[31]_i_1_n_0 ),
        .D(s_axi_wdata[24]),
        .Q(router_config_wdata[24]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[25] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[31]_i_1_n_0 ),
        .D(s_axi_wdata[25]),
        .Q(router_config_wdata[25]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[26] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[31]_i_1_n_0 ),
        .D(s_axi_wdata[26]),
        .Q(router_config_wdata[26]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[27] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[31]_i_1_n_0 ),
        .D(s_axi_wdata[27]),
        .Q(router_config_wdata[27]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[28] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[31]_i_1_n_0 ),
        .D(s_axi_wdata[28]),
        .Q(router_config_wdata[28]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[29] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[31]_i_1_n_0 ),
        .D(s_axi_wdata[29]),
        .Q(router_config_wdata[29]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[2] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[7]_i_1_n_0 ),
        .D(s_axi_wdata[2]),
        .Q(router_config_wdata[2]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[30] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[31]_i_1_n_0 ),
        .D(s_axi_wdata[30]),
        .Q(router_config_wdata[30]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[31] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[31]_i_1_n_0 ),
        .D(s_axi_wdata[31]),
        .Q(router_config_wdata[31]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[3] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[7]_i_1_n_0 ),
        .D(s_axi_wdata[3]),
        .Q(router_config_wdata[3]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[4] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[7]_i_1_n_0 ),
        .D(s_axi_wdata[4]),
        .Q(router_config_wdata[4]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[5] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[7]_i_1_n_0 ),
        .D(s_axi_wdata[5]),
        .Q(router_config_wdata[5]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[6] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[7]_i_1_n_0 ),
        .D(s_axi_wdata[6]),
        .Q(router_config_wdata[6]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[7] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[7]_i_1_n_0 ),
        .D(s_axi_wdata[7]),
        .Q(router_config_wdata[7]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[8] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[15]_i_1_n_0 ),
        .D(s_axi_wdata[8]),
        .Q(router_config_wdata[8]),
        .R(p_0_in));
  FDRE \reg_config_wdata_reg[9] 
       (.C(s_axi_aclk),
        .CE(\reg_config_wdata[15]_i_1_n_0 ),
        .D(s_axi_wdata[9]),
        .Q(router_config_wdata[9]),
        .R(p_0_in));
  LUT6 #(
    .INIT(64'h0020000000000000)) 
    \reg_leak_rate[7]_i_1 
       (.I0(write_en__1),
        .I1(write_addr[3]),
        .I2(write_addr[2]),
        .I3(write_addr[1]),
        .I4(write_addr[0]),
        .I5(s_axi_wstrb[0]),
        .O(reg_leak_rate));
  FDSE \reg_leak_rate_reg[0] 
       (.C(s_axi_aclk),
        .CE(reg_leak_rate),
        .D(s_axi_wdata[0]),
        .Q(global_leak_rate[0]),
        .S(p_0_in));
  FDSE \reg_leak_rate_reg[1] 
       (.C(s_axi_aclk),
        .CE(reg_leak_rate),
        .D(s_axi_wdata[1]),
        .Q(global_leak_rate[1]),
        .S(p_0_in));
  FDRE \reg_leak_rate_reg[2] 
       (.C(s_axi_aclk),
        .CE(reg_leak_rate),
        .D(s_axi_wdata[2]),
        .Q(global_leak_rate[2]),
        .R(p_0_in));
  FDRE \reg_leak_rate_reg[3] 
       (.C(s_axi_aclk),
        .CE(reg_leak_rate),
        .D(s_axi_wdata[3]),
        .Q(global_leak_rate[3]),
        .R(p_0_in));
  FDRE \reg_leak_rate_reg[4] 
       (.C(s_axi_aclk),
        .CE(reg_leak_rate),
        .D(s_axi_wdata[4]),
        .Q(global_leak_rate[4]),
        .R(p_0_in));
  FDRE \reg_leak_rate_reg[5] 
       (.C(s_axi_aclk),
        .CE(reg_leak_rate),
        .D(s_axi_wdata[5]),
        .Q(global_leak_rate[5]),
        .R(p_0_in));
  FDRE \reg_leak_rate_reg[6] 
       (.C(s_axi_aclk),
        .CE(reg_leak_rate),
        .D(s_axi_wdata[6]),
        .Q(global_leak_rate[6]),
        .R(p_0_in));
  FDRE \reg_leak_rate_reg[7] 
       (.C(s_axi_aclk),
        .CE(reg_leak_rate),
        .D(s_axi_wdata[7]),
        .Q(global_leak_rate[7]),
        .R(p_0_in));
  LUT6 #(
    .INIT(64'h0020000000000000)) 
    \reg_refrac_period[7]_i_1 
       (.I0(write_en__1),
        .I1(write_addr[3]),
        .I2(write_addr[2]),
        .I3(write_addr[1]),
        .I4(write_addr[0]),
        .I5(s_axi_wstrb[1]),
        .O(reg_refrac_period));
  FDRE \reg_refrac_period_reg[0] 
       (.C(s_axi_aclk),
        .CE(reg_refrac_period),
        .D(s_axi_wdata[8]),
        .Q(global_refrac_period[0]),
        .R(p_0_in));
  FDSE \reg_refrac_period_reg[1] 
       (.C(s_axi_aclk),
        .CE(reg_refrac_period),
        .D(s_axi_wdata[9]),
        .Q(global_refrac_period[1]),
        .S(p_0_in));
  FDRE \reg_refrac_period_reg[2] 
       (.C(s_axi_aclk),
        .CE(reg_refrac_period),
        .D(s_axi_wdata[10]),
        .Q(global_refrac_period[2]),
        .R(p_0_in));
  FDSE \reg_refrac_period_reg[3] 
       (.C(s_axi_aclk),
        .CE(reg_refrac_period),
        .D(s_axi_wdata[11]),
        .Q(global_refrac_period[3]),
        .S(p_0_in));
  FDRE \reg_refrac_period_reg[4] 
       (.C(s_axi_aclk),
        .CE(reg_refrac_period),
        .D(s_axi_wdata[12]),
        .Q(global_refrac_period[4]),
        .R(p_0_in));
  FDRE \reg_refrac_period_reg[5] 
       (.C(s_axi_aclk),
        .CE(reg_refrac_period),
        .D(s_axi_wdata[13]),
        .Q(global_refrac_period[5]),
        .R(p_0_in));
  FDRE \reg_refrac_period_reg[6] 
       (.C(s_axi_aclk),
        .CE(reg_refrac_period),
        .D(s_axi_wdata[14]),
        .Q(global_refrac_period[6]),
        .R(p_0_in));
  FDRE \reg_refrac_period_reg[7] 
       (.C(s_axi_aclk),
        .CE(reg_refrac_period),
        .D(s_axi_wdata[15]),
        .Q(global_refrac_period[7]),
        .R(p_0_in));
  LUT6 #(
    .INIT(64'h0000000000002000)) 
    \reg_threshold[15]_i_1 
       (.I0(write_en__1),
        .I1(write_addr[3]),
        .I2(s_axi_wstrb[1]),
        .I3(write_addr[2]),
        .I4(write_addr[0]),
        .I5(write_addr[1]),
        .O(\reg_threshold[15]_i_1_n_0 ));
  LUT6 #(
    .INIT(64'h0000000000002000)) 
    \reg_threshold[7]_i_1 
       (.I0(write_en__1),
        .I1(write_addr[3]),
        .I2(s_axi_wstrb[0]),
        .I3(write_addr[2]),
        .I4(write_addr[0]),
        .I5(write_addr[1]),
        .O(\reg_threshold[7]_i_1_n_0 ));
  FDRE \reg_threshold_reg[0] 
       (.C(s_axi_aclk),
        .CE(\reg_threshold[7]_i_1_n_0 ),
        .D(s_axi_wdata[0]),
        .Q(global_threshold[0]),
        .R(p_0_in));
  FDRE \reg_threshold_reg[10] 
       (.C(s_axi_aclk),
        .CE(\reg_threshold[15]_i_1_n_0 ),
        .D(s_axi_wdata[10]),
        .Q(global_threshold[10]),
        .R(p_0_in));
  FDRE \reg_threshold_reg[11] 
       (.C(s_axi_aclk),
        .CE(\reg_threshold[15]_i_1_n_0 ),
        .D(s_axi_wdata[11]),
        .Q(global_threshold[11]),
        .R(p_0_in));
  FDRE \reg_threshold_reg[12] 
       (.C(s_axi_aclk),
        .CE(\reg_threshold[15]_i_1_n_0 ),
        .D(s_axi_wdata[12]),
        .Q(global_threshold[12]),
        .R(p_0_in));
  FDRE \reg_threshold_reg[13] 
       (.C(s_axi_aclk),
        .CE(\reg_threshold[15]_i_1_n_0 ),
        .D(s_axi_wdata[13]),
        .Q(global_threshold[13]),
        .R(p_0_in));
  FDRE \reg_threshold_reg[14] 
       (.C(s_axi_aclk),
        .CE(\reg_threshold[15]_i_1_n_0 ),
        .D(s_axi_wdata[14]),
        .Q(global_threshold[14]),
        .R(p_0_in));
  FDRE \reg_threshold_reg[15] 
       (.C(s_axi_aclk),
        .CE(\reg_threshold[15]_i_1_n_0 ),
        .D(s_axi_wdata[15]),
        .Q(global_threshold[15]),
        .R(p_0_in));
  FDRE \reg_threshold_reg[1] 
       (.C(s_axi_aclk),
        .CE(\reg_threshold[7]_i_1_n_0 ),
        .D(s_axi_wdata[1]),
        .Q(global_threshold[1]),
        .R(p_0_in));
  FDSE \reg_threshold_reg[2] 
       (.C(s_axi_aclk),
        .CE(\reg_threshold[7]_i_1_n_0 ),
        .D(s_axi_wdata[2]),
        .Q(global_threshold[2]),
        .S(p_0_in));
  FDRE \reg_threshold_reg[3] 
       (.C(s_axi_aclk),
        .CE(\reg_threshold[7]_i_1_n_0 ),
        .D(s_axi_wdata[3]),
        .Q(global_threshold[3]),
        .R(p_0_in));
  FDRE \reg_threshold_reg[4] 
       (.C(s_axi_aclk),
        .CE(\reg_threshold[7]_i_1_n_0 ),
        .D(s_axi_wdata[4]),
        .Q(global_threshold[4]),
        .R(p_0_in));
  FDSE \reg_threshold_reg[5] 
       (.C(s_axi_aclk),
        .CE(\reg_threshold[7]_i_1_n_0 ),
        .D(s_axi_wdata[5]),
        .Q(global_threshold[5]),
        .S(p_0_in));
  FDSE \reg_threshold_reg[6] 
       (.C(s_axi_aclk),
        .CE(\reg_threshold[7]_i_1_n_0 ),
        .D(s_axi_wdata[6]),
        .Q(global_threshold[6]),
        .S(p_0_in));
  FDRE \reg_threshold_reg[7] 
       (.C(s_axi_aclk),
        .CE(\reg_threshold[7]_i_1_n_0 ),
        .D(s_axi_wdata[7]),
        .Q(global_threshold[7]),
        .R(p_0_in));
  FDRE \reg_threshold_reg[8] 
       (.C(s_axi_aclk),
        .CE(\reg_threshold[15]_i_1_n_0 ),
        .D(s_axi_wdata[8]),
        .Q(global_threshold[8]),
        .R(p_0_in));
  FDRE \reg_threshold_reg[9] 
       (.C(s_axi_aclk),
        .CE(\reg_threshold[15]_i_1_n_0 ),
        .D(s_axi_wdata[9]),
        .Q(global_threshold[9]),
        .R(p_0_in));
  (* SOFT_HLUTNM = "soft_lutpair1" *) 
  LUT3 #(
    .INIT(8'h02)) 
    router_config_we__0
       (.I0(config_we_pulse),
        .I1(\config_target_reg_n_0_[1] ),
        .I2(\config_target_reg_n_0_[0] ),
        .O(router_config_we));
  (* SOFT_HLUTNM = "soft_lutpair0" *) 
  LUT4 #(
    .INIT(16'h2000)) 
    w_ready_i_1
       (.I0(aw_en_reg_n_0),
        .I1(s_axi_wready),
        .I2(s_axi_wvalid),
        .I3(s_axi_awvalid),
        .O(w_ready0));
  (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi WREADY" *) 
  FDRE w_ready_reg
       (.C(s_axi_aclk),
        .CE(1'b1),
        .D(w_ready0),
        .Q(s_axi_wready),
        .R(p_0_in));
endmodule
`ifndef GLBL
`define GLBL
`timescale  1 ps / 1 ps

module glbl ();

    parameter ROC_WIDTH = 100000;
    parameter TOC_WIDTH = 0;
    parameter GRES_WIDTH = 10000;
    parameter GRES_START = 10000;

//--------   STARTUP Globals --------------
    wire GSR;
    wire GTS;
    wire GWE;
    wire PRLD;
    wire GRESTORE;
    tri1 p_up_tmp;
    tri (weak1, strong0) PLL_LOCKG = p_up_tmp;

    wire PROGB_GLBL;
    wire CCLKO_GLBL;
    wire FCSBO_GLBL;
    wire [3:0] DO_GLBL;
    wire [3:0] DI_GLBL;
   
    reg GSR_int;
    reg GTS_int;
    reg PRLD_int;
    reg GRESTORE_int;

//--------   JTAG Globals --------------
    wire JTAG_TDO_GLBL;
    wire JTAG_TCK_GLBL;
    wire JTAG_TDI_GLBL;
    wire JTAG_TMS_GLBL;
    wire JTAG_TRST_GLBL;

    reg JTAG_CAPTURE_GLBL;
    reg JTAG_RESET_GLBL;
    reg JTAG_SHIFT_GLBL;
    reg JTAG_UPDATE_GLBL;
    reg JTAG_RUNTEST_GLBL;

    reg JTAG_SEL1_GLBL = 0;
    reg JTAG_SEL2_GLBL = 0 ;
    reg JTAG_SEL3_GLBL = 0;
    reg JTAG_SEL4_GLBL = 0;

    reg JTAG_USER_TDO1_GLBL = 1'bz;
    reg JTAG_USER_TDO2_GLBL = 1'bz;
    reg JTAG_USER_TDO3_GLBL = 1'bz;
    reg JTAG_USER_TDO4_GLBL = 1'bz;

    assign (strong1, weak0) GSR = GSR_int;
    assign (strong1, weak0) GTS = GTS_int;
    assign (weak1, weak0) PRLD = PRLD_int;
    assign (strong1, weak0) GRESTORE = GRESTORE_int;

    initial begin
	GSR_int = 1'b1;
	PRLD_int = 1'b1;
	#(ROC_WIDTH)
	GSR_int = 1'b0;
	PRLD_int = 1'b0;
    end

    initial begin
	GTS_int = 1'b1;
	#(TOC_WIDTH)
	GTS_int = 1'b0;
    end

    initial begin 
	GRESTORE_int = 1'b0;
	#(GRES_START);
	GRESTORE_int = 1'b1;
	#(GRES_WIDTH);
	GRESTORE_int = 1'b0;
    end

endmodule
`endif
