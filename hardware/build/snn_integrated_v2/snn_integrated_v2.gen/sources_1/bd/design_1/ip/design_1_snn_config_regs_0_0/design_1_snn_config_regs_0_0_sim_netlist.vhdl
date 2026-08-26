-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- Copyright 2022-2025 Advanced Micro Devices, Inc. All Rights Reserved.
-- --------------------------------------------------------------------------------
-- Tool Version: Vivado v.2025.2 (lin64) Build 6299465 Fri Nov 14 12:34:56 MST 2025
-- Date        : Mon Aug 24 12:57:04 2026
-- Host        : Mariana running 64-bit Ubuntu 22.04.5 LTS
-- Command     : write_vhdl -force -mode funcsim
--               /home/chipwisperer/Documents/SNN/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/build/snn_integrated_v2/snn_integrated_v2.gen/sources_1/bd/design_1/ip/design_1_snn_config_regs_0_0/design_1_snn_config_regs_0_0_sim_netlist.vhdl
-- Design      : design_1_snn_config_regs_0_0
-- Purpose     : This VHDL netlist is a functional simulation representation of the design and should not be modified or
--               synthesized. This netlist cannot be used for SDF annotated simulation.
-- Device      : xc7z020clg400-1
-- --------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity design_1_snn_config_regs_0_0_snn_config_regs is
  port (
    s_axi_wready : out STD_LOGIC;
    s_axi_awready : out STD_LOGIC;
    s_axi_arready : out STD_LOGIC;
    router_config_addr : out STD_LOGIC_VECTOR ( 31 downto 0 );
    router_config_wdata : out STD_LOGIC_VECTOR ( 31 downto 0 );
    global_threshold : out STD_LOGIC_VECTOR ( 15 downto 0 );
    global_leak_rate : out STD_LOGIC_VECTOR ( 7 downto 0 );
    global_refrac_period : out STD_LOGIC_VECTOR ( 7 downto 0 );
    s_axi_rdata : out STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_rvalid : out STD_LOGIC;
    router_config_we : out STD_LOGIC;
    neuron_config_we : out STD_LOGIC;
    s_axi_bvalid : out STD_LOGIC;
    active_neurons : in STD_LOGIC_VECTOR ( 7 downto 0 );
    throughput_counter : in STD_LOGIC_VECTOR ( 31 downto 0 );
    service_cycles_counter : in STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_aclk : in STD_LOGIC;
    s_axi_awaddr : in STD_LOGIC_VECTOR ( 3 downto 0 );
    s_axi_wdata : in STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_araddr : in STD_LOGIC_VECTOR ( 3 downto 0 );
    router_config_rdata : in STD_LOGIC_VECTOR ( 31 downto 0 );
    neuron_spike_count : in STD_LOGIC_VECTOR ( 31 downto 0 );
    router_spike_count : in STD_LOGIC_VECTOR ( 31 downto 0 );
    fifo_overflow : in STD_LOGIC;
    s_axi_aresetn : in STD_LOGIC;
    s_axi_wstrb : in STD_LOGIC_VECTOR ( 3 downto 0 );
    s_axi_awvalid : in STD_LOGIC;
    s_axi_wvalid : in STD_LOGIC;
    s_axi_arvalid : in STD_LOGIC;
    s_axi_bready : in STD_LOGIC;
    s_axi_rready : in STD_LOGIC
  );
  attribute ORIG_REF_NAME : string;
  attribute ORIG_REF_NAME of design_1_snn_config_regs_0_0_snn_config_regs : entity is "snn_config_regs";
end design_1_snn_config_regs_0_0_snn_config_regs;

architecture STRUCTURE of design_1_snn_config_regs_0_0_snn_config_regs is
  signal ar_ready0 : STD_LOGIC;
  signal aw_en_i_1_n_0 : STD_LOGIC;
  signal aw_en_reg_n_0 : STD_LOGIC;
  signal aw_ready0 : STD_LOGIC;
  signal b_valid_i_1_n_0 : STD_LOGIC;
  signal \config_target[0]_i_1_n_0\ : STD_LOGIC;
  signal \config_target[1]_i_1_n_0\ : STD_LOGIC;
  signal \config_target[1]_i_2_n_0\ : STD_LOGIC;
  signal \config_target_reg_n_0_[0]\ : STD_LOGIC;
  signal \config_target_reg_n_0_[1]\ : STD_LOGIC;
  signal config_we_pulse : STD_LOGIC;
  signal config_we_pulse_i_1_n_0 : STD_LOGIC;
  signal \^global_leak_rate\ : STD_LOGIC_VECTOR ( 7 downto 0 );
  signal \^global_refrac_period\ : STD_LOGIC_VECTOR ( 7 downto 0 );
  signal \^global_threshold\ : STD_LOGIC_VECTOR ( 15 downto 0 );
  signal p_0_in : STD_LOGIC;
  signal p_1_in : STD_LOGIC_VECTOR ( 31 downto 7 );
  signal r_data : STD_LOGIC_VECTOR ( 31 downto 0 );
  signal \r_data0__0\ : STD_LOGIC;
  signal \r_data[0]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[0]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[0]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[10]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[10]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[10]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[11]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[11]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[11]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[12]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[12]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[12]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[13]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[13]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[13]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[14]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[14]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[14]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[15]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[15]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[15]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[16]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[16]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[16]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[17]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[17]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[17]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[18]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[18]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[18]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[19]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[19]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[19]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[1]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[1]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[1]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[20]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[20]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[20]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[21]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[21]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[21]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[22]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[22]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[22]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[23]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[23]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[23]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[24]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[24]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[24]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[25]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[25]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[25]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[26]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[26]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[26]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[27]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[27]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[27]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[28]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[28]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[28]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[29]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[29]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[29]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[2]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[2]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[2]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[30]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[30]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[30]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[31]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[31]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[31]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[3]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[3]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[3]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[4]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[4]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[4]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[5]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[5]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[5]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[6]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[6]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[6]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[7]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[7]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[7]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[8]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[8]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[8]_i_4_n_0\ : STD_LOGIC;
  signal \r_data[9]_i_2_n_0\ : STD_LOGIC;
  signal \r_data[9]_i_3_n_0\ : STD_LOGIC;
  signal \r_data[9]_i_4_n_0\ : STD_LOGIC;
  signal r_valid_i_1_n_0 : STD_LOGIC;
  signal reg_config_ctrl : STD_LOGIC_VECTOR ( 7 to 7 );
  signal \reg_config_ctrl_reg_n_0_[0]\ : STD_LOGIC;
  signal \reg_config_ctrl_reg_n_0_[1]\ : STD_LOGIC;
  signal \reg_config_ctrl_reg_n_0_[2]\ : STD_LOGIC;
  signal \reg_config_ctrl_reg_n_0_[3]\ : STD_LOGIC;
  signal \reg_config_ctrl_reg_n_0_[4]\ : STD_LOGIC;
  signal \reg_config_ctrl_reg_n_0_[5]\ : STD_LOGIC;
  signal \reg_config_ctrl_reg_n_0_[6]\ : STD_LOGIC;
  signal \reg_config_ctrl_reg_n_0_[7]\ : STD_LOGIC;
  signal \reg_config_wdata[15]_i_1_n_0\ : STD_LOGIC;
  signal \reg_config_wdata[23]_i_1_n_0\ : STD_LOGIC;
  signal \reg_config_wdata[31]_i_1_n_0\ : STD_LOGIC;
  signal \reg_config_wdata[7]_i_1_n_0\ : STD_LOGIC;
  signal reg_leak_rate : STD_LOGIC_VECTOR ( 0 to 0 );
  signal reg_refrac_period : STD_LOGIC_VECTOR ( 0 to 0 );
  signal \reg_threshold[15]_i_1_n_0\ : STD_LOGIC;
  signal \reg_threshold[7]_i_1_n_0\ : STD_LOGIC;
  signal \^router_config_addr\ : STD_LOGIC_VECTOR ( 31 downto 0 );
  signal \^router_config_wdata\ : STD_LOGIC_VECTOR ( 31 downto 0 );
  signal \^s_axi_arready\ : STD_LOGIC;
  signal \^s_axi_awready\ : STD_LOGIC;
  signal \^s_axi_bvalid\ : STD_LOGIC;
  signal \^s_axi_rvalid\ : STD_LOGIC;
  signal \^s_axi_wready\ : STD_LOGIC;
  signal sel0 : STD_LOGIC_VECTOR ( 3 downto 0 );
  signal w_ready0 : STD_LOGIC;
  signal write_addr : STD_LOGIC_VECTOR ( 3 downto 0 );
  signal \write_en__1\ : STD_LOGIC;
  attribute X_INTERFACE_INFO : string;
  attribute X_INTERFACE_INFO of ar_ready_reg : label is "xilinx.com:interface:aximm:1.0 s_axi ARREADY";
  attribute X_INTERFACE_INFO of aw_ready_reg : label is "xilinx.com:interface:aximm:1.0 s_axi AWREADY";
  attribute X_INTERFACE_INFO of b_valid_reg : label is "xilinx.com:interface:aximm:1.0 s_axi BVALID";
  attribute SOFT_HLUTNM : string;
  attribute SOFT_HLUTNM of \neuron_config_we__0\ : label is "soft_lutpair1";
  attribute X_INTERFACE_INFO of \r_data_reg[0]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[10]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[11]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[12]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[13]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[14]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[15]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[16]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[17]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[18]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[19]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[1]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[20]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[21]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[22]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[23]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[24]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[25]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[26]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[27]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[28]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[29]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[2]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[30]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[31]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[3]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[4]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[5]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[6]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[7]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[8]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of \r_data_reg[9]\ : label is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of r_valid_reg : label is "xilinx.com:interface:aximm:1.0 s_axi RVALID";
  attribute SOFT_HLUTNM of \reg_config_addr[31]_i_2\ : label is "soft_lutpair0";
  attribute SOFT_HLUTNM of \router_config_we__0\ : label is "soft_lutpair1";
  attribute SOFT_HLUTNM of w_ready_i_1 : label is "soft_lutpair0";
  attribute X_INTERFACE_INFO of w_ready_reg : label is "xilinx.com:interface:aximm:1.0 s_axi WREADY";
begin
  global_leak_rate(7 downto 0) <= \^global_leak_rate\(7 downto 0);
  global_refrac_period(7 downto 0) <= \^global_refrac_period\(7 downto 0);
  global_threshold(15 downto 0) <= \^global_threshold\(15 downto 0);
  router_config_addr(31 downto 0) <= \^router_config_addr\(31 downto 0);
  router_config_wdata(31 downto 0) <= \^router_config_wdata\(31 downto 0);
  s_axi_arready <= \^s_axi_arready\;
  s_axi_awready <= \^s_axi_awready\;
  s_axi_bvalid <= \^s_axi_bvalid\;
  s_axi_rvalid <= \^s_axi_rvalid\;
  s_axi_wready <= \^s_axi_wready\;
\ar_addr_reg[2]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => ar_ready0,
      D => s_axi_araddr(0),
      Q => sel0(0),
      R => p_0_in
    );
\ar_addr_reg[3]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => ar_ready0,
      D => s_axi_araddr(1),
      Q => sel0(1),
      R => p_0_in
    );
\ar_addr_reg[4]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => ar_ready0,
      D => s_axi_araddr(2),
      Q => sel0(2),
      R => p_0_in
    );
\ar_addr_reg[5]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => ar_ready0,
      D => s_axi_araddr(3),
      Q => sel0(3),
      R => p_0_in
    );
ar_ready_i_1: unisim.vcomponents.LUT2
    generic map(
      INIT => X"2"
    )
        port map (
      I0 => s_axi_arvalid,
      I1 => \^s_axi_arready\,
      O => ar_ready0
    );
ar_ready_reg: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => ar_ready0,
      Q => \^s_axi_arready\,
      R => p_0_in
    );
\aw_addr_reg[2]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => aw_ready0,
      D => s_axi_awaddr(0),
      Q => write_addr(0),
      R => p_0_in
    );
\aw_addr_reg[3]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => aw_ready0,
      D => s_axi_awaddr(1),
      Q => write_addr(1),
      R => p_0_in
    );
\aw_addr_reg[4]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => aw_ready0,
      D => s_axi_awaddr(2),
      Q => write_addr(2),
      R => p_0_in
    );
\aw_addr_reg[5]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => aw_ready0,
      D => s_axi_awaddr(3),
      Q => write_addr(3),
      R => p_0_in
    );
aw_en_i_1: unisim.vcomponents.LUT6
    generic map(
      INIT => X"F7FFF700F700F700"
    )
        port map (
      I0 => s_axi_awvalid,
      I1 => s_axi_wvalid,
      I2 => \^s_axi_awready\,
      I3 => aw_en_reg_n_0,
      I4 => s_axi_bready,
      I5 => \^s_axi_bvalid\,
      O => aw_en_i_1_n_0
    );
aw_en_reg: unisim.vcomponents.FDSE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => aw_en_i_1_n_0,
      Q => aw_en_reg_n_0,
      S => p_0_in
    );
aw_ready_i_1: unisim.vcomponents.LUT1
    generic map(
      INIT => X"1"
    )
        port map (
      I0 => s_axi_aresetn,
      O => p_0_in
    );
aw_ready_i_2: unisim.vcomponents.LUT4
    generic map(
      INIT => X"2000"
    )
        port map (
      I0 => aw_en_reg_n_0,
      I1 => \^s_axi_awready\,
      I2 => s_axi_wvalid,
      I3 => s_axi_awvalid,
      O => aw_ready0
    );
aw_ready_reg: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => aw_ready0,
      Q => \^s_axi_awready\,
      R => p_0_in
    );
b_valid_i_1: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000FFFF80008000"
    )
        port map (
      I0 => s_axi_awvalid,
      I1 => s_axi_wvalid,
      I2 => \^s_axi_awready\,
      I3 => \^s_axi_wready\,
      I4 => s_axi_bready,
      I5 => \^s_axi_bvalid\,
      O => b_valid_i_1_n_0
    );
b_valid_reg: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => b_valid_i_1_n_0,
      Q => \^s_axi_bvalid\,
      R => p_0_in
    );
\config_target[0]_i_1\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"BF80"
    )
        port map (
      I0 => s_axi_wdata(0),
      I1 => \write_en__1\,
      I2 => \config_target[1]_i_2_n_0\,
      I3 => \config_target_reg_n_0_[0]\,
      O => \config_target[0]_i_1_n_0\
    );
\config_target[1]_i_1\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"BF80"
    )
        port map (
      I0 => s_axi_wdata(1),
      I1 => \write_en__1\,
      I2 => \config_target[1]_i_2_n_0\,
      I3 => \config_target_reg_n_0_[1]\,
      O => \config_target[1]_i_1_n_0\
    );
\config_target[1]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"00000004"
    )
        port map (
      I0 => write_addr(1),
      I1 => s_axi_wstrb(0),
      I2 => write_addr(2),
      I3 => write_addr(0),
      I4 => write_addr(3),
      O => \config_target[1]_i_2_n_0\
    );
\config_target_reg[0]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => \config_target[0]_i_1_n_0\,
      Q => \config_target_reg_n_0_[0]\,
      R => p_0_in
    );
\config_target_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => \config_target[1]_i_1_n_0\,
      Q => \config_target_reg_n_0_[1]\,
      R => p_0_in
    );
config_we_pulse_i_1: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0004000000000000"
    )
        port map (
      I0 => write_addr(3),
      I1 => write_addr(1),
      I2 => write_addr(0),
      I3 => write_addr(2),
      I4 => \write_en__1\,
      I5 => s_axi_aresetn,
      O => config_we_pulse_i_1_n_0
    );
config_we_pulse_reg: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => config_we_pulse_i_1_n_0,
      Q => config_we_pulse,
      R => '0'
    );
\neuron_config_we__0\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"40"
    )
        port map (
      I0 => \config_target_reg_n_0_[1]\,
      I1 => \config_target_reg_n_0_[0]\,
      I2 => config_we_pulse,
      O => neuron_config_we
    );
r_data0: unisim.vcomponents.LUT3
    generic map(
      INIT => X"08"
    )
        port map (
      I0 => s_axi_arvalid,
      I1 => \^s_axi_arready\,
      I2 => \^s_axi_rvalid\,
      O => \r_data0__0\
    );
\r_data[0]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[0]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[0]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[0]_i_4_n_0\,
      O => r_data(0)
    );
\r_data[0]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FFFFFEAEAFAFFEAE"
    )
        port map (
      I0 => sel0(2),
      I1 => fifo_overflow,
      I2 => sel0(0),
      I3 => throughput_counter(0),
      I4 => sel0(1),
      I5 => service_cycles_counter(0),
      O => \r_data[0]_i_2_n_0\
    );
\r_data[0]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => neuron_spike_count(0),
      I1 => router_spike_count(0),
      I2 => sel0(1),
      I3 => \^global_leak_rate\(0),
      I4 => sel0(0),
      I5 => \^global_threshold\(0),
      O => \r_data[0]_i_3_n_0\
    );
\r_data[0]_i_4\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => router_config_rdata(0),
      I1 => \^router_config_wdata\(0),
      I2 => sel0(1),
      I3 => \^router_config_addr\(0),
      I4 => sel0(0),
      I5 => \reg_config_ctrl_reg_n_0_[0]\,
      O => \r_data[0]_i_4_n_0\
    );
\r_data[10]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[10]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[10]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[10]_i_4_n_0\,
      O => r_data(10)
    );
\r_data[10]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFEAAFEA"
    )
        port map (
      I0 => sel0(2),
      I1 => throughput_counter(10),
      I2 => sel0(0),
      I3 => sel0(1),
      I4 => service_cycles_counter(10),
      O => \r_data[10]_i_2_n_0\
    );
\r_data[10]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => neuron_spike_count(10),
      I1 => router_spike_count(10),
      I2 => sel0(1),
      I3 => \^global_refrac_period\(2),
      I4 => sel0(0),
      I5 => \^global_threshold\(10),
      O => \r_data[10]_i_3_n_0\
    );
\r_data[10]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(10),
      I1 => \^router_config_wdata\(10),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(10),
      O => \r_data[10]_i_4_n_0\
    );
\r_data[11]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[11]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[11]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[11]_i_4_n_0\,
      O => r_data(11)
    );
\r_data[11]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFEAAFEA"
    )
        port map (
      I0 => sel0(2),
      I1 => throughput_counter(11),
      I2 => sel0(0),
      I3 => sel0(1),
      I4 => service_cycles_counter(11),
      O => \r_data[11]_i_2_n_0\
    );
\r_data[11]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => neuron_spike_count(11),
      I1 => router_spike_count(11),
      I2 => sel0(1),
      I3 => \^global_refrac_period\(3),
      I4 => sel0(0),
      I5 => \^global_threshold\(11),
      O => \r_data[11]_i_3_n_0\
    );
\r_data[11]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(11),
      I1 => \^router_config_wdata\(11),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(11),
      O => \r_data[11]_i_4_n_0\
    );
\r_data[12]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[12]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[12]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[12]_i_4_n_0\,
      O => r_data(12)
    );
\r_data[12]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FAEAAAEA"
    )
        port map (
      I0 => sel0(2),
      I1 => throughput_counter(12),
      I2 => sel0(0),
      I3 => sel0(1),
      I4 => service_cycles_counter(12),
      O => \r_data[12]_i_2_n_0\
    );
\r_data[12]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => neuron_spike_count(12),
      I1 => router_spike_count(12),
      I2 => sel0(1),
      I3 => \^global_refrac_period\(4),
      I4 => sel0(0),
      I5 => \^global_threshold\(12),
      O => \r_data[12]_i_3_n_0\
    );
\r_data[12]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(12),
      I1 => \^router_config_wdata\(12),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(12),
      O => \r_data[12]_i_4_n_0\
    );
\r_data[13]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[13]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[13]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[13]_i_4_n_0\,
      O => r_data(13)
    );
\r_data[13]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FAEAAAEA"
    )
        port map (
      I0 => sel0(2),
      I1 => throughput_counter(13),
      I2 => sel0(0),
      I3 => sel0(1),
      I4 => service_cycles_counter(13),
      O => \r_data[13]_i_2_n_0\
    );
\r_data[13]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => neuron_spike_count(13),
      I1 => router_spike_count(13),
      I2 => sel0(1),
      I3 => \^global_refrac_period\(5),
      I4 => sel0(0),
      I5 => \^global_threshold\(13),
      O => \r_data[13]_i_3_n_0\
    );
\r_data[13]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(13),
      I1 => \^router_config_wdata\(13),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(13),
      O => \r_data[13]_i_4_n_0\
    );
\r_data[14]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[14]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[14]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[14]_i_4_n_0\,
      O => r_data(14)
    );
\r_data[14]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"0000F838"
    )
        port map (
      I0 => throughput_counter(14),
      I1 => sel0(0),
      I2 => sel0(1),
      I3 => service_cycles_counter(14),
      I4 => sel0(2),
      O => \r_data[14]_i_2_n_0\
    );
\r_data[14]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => neuron_spike_count(14),
      I1 => router_spike_count(14),
      I2 => sel0(1),
      I3 => \^global_refrac_period\(6),
      I4 => sel0(0),
      I5 => \^global_threshold\(14),
      O => \r_data[14]_i_3_n_0\
    );
\r_data[14]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(14),
      I1 => \^router_config_wdata\(14),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(14),
      O => \r_data[14]_i_4_n_0\
    );
\r_data[15]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[15]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[15]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[15]_i_4_n_0\,
      O => r_data(15)
    );
\r_data[15]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FAEAAAEA"
    )
        port map (
      I0 => sel0(2),
      I1 => throughput_counter(15),
      I2 => sel0(0),
      I3 => sel0(1),
      I4 => service_cycles_counter(15),
      O => \r_data[15]_i_2_n_0\
    );
\r_data[15]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => neuron_spike_count(15),
      I1 => router_spike_count(15),
      I2 => sel0(1),
      I3 => \^global_refrac_period\(7),
      I4 => sel0(0),
      I5 => \^global_threshold\(15),
      O => \r_data[15]_i_3_n_0\
    );
\r_data[15]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(15),
      I1 => \^router_config_wdata\(15),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(15),
      O => \r_data[15]_i_4_n_0\
    );
\r_data[16]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[16]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[16]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[16]_i_4_n_0\,
      O => r_data(16)
    );
\r_data[16]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FAEAAAEA"
    )
        port map (
      I0 => sel0(2),
      I1 => throughput_counter(16),
      I2 => sel0(0),
      I3 => sel0(1),
      I4 => service_cycles_counter(16),
      O => \r_data[16]_i_2_n_0\
    );
\r_data[16]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"A808"
    )
        port map (
      I0 => sel0(1),
      I1 => router_spike_count(16),
      I2 => sel0(0),
      I3 => neuron_spike_count(16),
      O => \r_data[16]_i_3_n_0\
    );
\r_data[16]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(16),
      I1 => \^router_config_wdata\(16),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(16),
      O => \r_data[16]_i_4_n_0\
    );
\r_data[17]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[17]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[17]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[17]_i_4_n_0\,
      O => r_data(17)
    );
\r_data[17]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"0000F838"
    )
        port map (
      I0 => throughput_counter(17),
      I1 => sel0(0),
      I2 => sel0(1),
      I3 => service_cycles_counter(17),
      I4 => sel0(2),
      O => \r_data[17]_i_2_n_0\
    );
\r_data[17]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"A808"
    )
        port map (
      I0 => sel0(1),
      I1 => router_spike_count(17),
      I2 => sel0(0),
      I3 => neuron_spike_count(17),
      O => \r_data[17]_i_3_n_0\
    );
\r_data[17]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(17),
      I1 => \^router_config_wdata\(17),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(17),
      O => \r_data[17]_i_4_n_0\
    );
\r_data[18]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[18]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[18]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[18]_i_4_n_0\,
      O => r_data(18)
    );
\r_data[18]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFEAAFEA"
    )
        port map (
      I0 => sel0(2),
      I1 => throughput_counter(18),
      I2 => sel0(0),
      I3 => sel0(1),
      I4 => service_cycles_counter(18),
      O => \r_data[18]_i_2_n_0\
    );
\r_data[18]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"A808"
    )
        port map (
      I0 => sel0(1),
      I1 => router_spike_count(18),
      I2 => sel0(0),
      I3 => neuron_spike_count(18),
      O => \r_data[18]_i_3_n_0\
    );
\r_data[18]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(18),
      I1 => \^router_config_wdata\(18),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(18),
      O => \r_data[18]_i_4_n_0\
    );
\r_data[19]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[19]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[19]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[19]_i_4_n_0\,
      O => r_data(19)
    );
\r_data[19]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFEAAFEA"
    )
        port map (
      I0 => sel0(2),
      I1 => throughput_counter(19),
      I2 => sel0(0),
      I3 => sel0(1),
      I4 => service_cycles_counter(19),
      O => \r_data[19]_i_2_n_0\
    );
\r_data[19]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"A808"
    )
        port map (
      I0 => sel0(1),
      I1 => router_spike_count(19),
      I2 => sel0(0),
      I3 => neuron_spike_count(19),
      O => \r_data[19]_i_3_n_0\
    );
\r_data[19]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(19),
      I1 => \^router_config_wdata\(19),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(19),
      O => \r_data[19]_i_4_n_0\
    );
\r_data[1]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[1]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[1]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[1]_i_4_n_0\,
      O => r_data(1)
    );
\r_data[1]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FAFAFEAEAAAAFEAE"
    )
        port map (
      I0 => sel0(2),
      I1 => active_neurons(0),
      I2 => sel0(0),
      I3 => throughput_counter(1),
      I4 => sel0(1),
      I5 => service_cycles_counter(1),
      O => \r_data[1]_i_2_n_0\
    );
\r_data[1]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => neuron_spike_count(1),
      I1 => router_spike_count(1),
      I2 => sel0(1),
      I3 => \^global_leak_rate\(1),
      I4 => sel0(0),
      I5 => \^global_threshold\(1),
      O => \r_data[1]_i_3_n_0\
    );
\r_data[1]_i_4\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => router_config_rdata(1),
      I1 => \^router_config_wdata\(1),
      I2 => sel0(1),
      I3 => \^router_config_addr\(1),
      I4 => sel0(0),
      I5 => \reg_config_ctrl_reg_n_0_[1]\,
      O => \r_data[1]_i_4_n_0\
    );
\r_data[20]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[20]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[20]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[20]_i_4_n_0\,
      O => r_data(20)
    );
\r_data[20]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"0000C808"
    )
        port map (
      I0 => throughput_counter(20),
      I1 => sel0(0),
      I2 => sel0(1),
      I3 => service_cycles_counter(20),
      I4 => sel0(2),
      O => \r_data[20]_i_2_n_0\
    );
\r_data[20]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"A808"
    )
        port map (
      I0 => sel0(1),
      I1 => router_spike_count(20),
      I2 => sel0(0),
      I3 => neuron_spike_count(20),
      O => \r_data[20]_i_3_n_0\
    );
\r_data[20]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(20),
      I1 => \^router_config_wdata\(20),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(20),
      O => \r_data[20]_i_4_n_0\
    );
\r_data[21]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[21]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[21]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[21]_i_4_n_0\,
      O => r_data(21)
    );
\r_data[21]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FAEAAAEA"
    )
        port map (
      I0 => sel0(2),
      I1 => throughput_counter(21),
      I2 => sel0(0),
      I3 => sel0(1),
      I4 => service_cycles_counter(21),
      O => \r_data[21]_i_2_n_0\
    );
\r_data[21]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"A808"
    )
        port map (
      I0 => sel0(1),
      I1 => router_spike_count(21),
      I2 => sel0(0),
      I3 => neuron_spike_count(21),
      O => \r_data[21]_i_3_n_0\
    );
\r_data[21]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(21),
      I1 => \^router_config_wdata\(21),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(21),
      O => \r_data[21]_i_4_n_0\
    );
\r_data[22]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[22]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[22]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[22]_i_4_n_0\,
      O => r_data(22)
    );
\r_data[22]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"0000F838"
    )
        port map (
      I0 => throughput_counter(22),
      I1 => sel0(0),
      I2 => sel0(1),
      I3 => service_cycles_counter(22),
      I4 => sel0(2),
      O => \r_data[22]_i_2_n_0\
    );
\r_data[22]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"A808"
    )
        port map (
      I0 => sel0(1),
      I1 => router_spike_count(22),
      I2 => sel0(0),
      I3 => neuron_spike_count(22),
      O => \r_data[22]_i_3_n_0\
    );
\r_data[22]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(22),
      I1 => \^router_config_wdata\(22),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(22),
      O => \r_data[22]_i_4_n_0\
    );
\r_data[23]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[23]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[23]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[23]_i_4_n_0\,
      O => r_data(23)
    );
\r_data[23]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FAEAAAEA"
    )
        port map (
      I0 => sel0(2),
      I1 => throughput_counter(23),
      I2 => sel0(0),
      I3 => sel0(1),
      I4 => service_cycles_counter(23),
      O => \r_data[23]_i_2_n_0\
    );
\r_data[23]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"A808"
    )
        port map (
      I0 => sel0(1),
      I1 => router_spike_count(23),
      I2 => sel0(0),
      I3 => neuron_spike_count(23),
      O => \r_data[23]_i_3_n_0\
    );
\r_data[23]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(23),
      I1 => \^router_config_wdata\(23),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(23),
      O => \r_data[23]_i_4_n_0\
    );
\r_data[24]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[24]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[24]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[24]_i_4_n_0\,
      O => r_data(24)
    );
\r_data[24]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"0000F838"
    )
        port map (
      I0 => throughput_counter(24),
      I1 => sel0(0),
      I2 => sel0(1),
      I3 => service_cycles_counter(24),
      I4 => sel0(2),
      O => \r_data[24]_i_2_n_0\
    );
\r_data[24]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"A808"
    )
        port map (
      I0 => sel0(1),
      I1 => router_spike_count(24),
      I2 => sel0(0),
      I3 => neuron_spike_count(24),
      O => \r_data[24]_i_3_n_0\
    );
\r_data[24]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(24),
      I1 => \^router_config_wdata\(24),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(24),
      O => \r_data[24]_i_4_n_0\
    );
\r_data[25]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[25]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[25]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[25]_i_4_n_0\,
      O => r_data(25)
    );
\r_data[25]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFEAAFEA"
    )
        port map (
      I0 => sel0(2),
      I1 => throughput_counter(25),
      I2 => sel0(0),
      I3 => sel0(1),
      I4 => service_cycles_counter(25),
      O => \r_data[25]_i_2_n_0\
    );
\r_data[25]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"A808"
    )
        port map (
      I0 => sel0(1),
      I1 => router_spike_count(25),
      I2 => sel0(0),
      I3 => neuron_spike_count(25),
      O => \r_data[25]_i_3_n_0\
    );
\r_data[25]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(25),
      I1 => \^router_config_wdata\(25),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(25),
      O => \r_data[25]_i_4_n_0\
    );
\r_data[26]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[26]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[26]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[26]_i_4_n_0\,
      O => r_data(26)
    );
\r_data[26]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FAEAAAEA"
    )
        port map (
      I0 => sel0(2),
      I1 => throughput_counter(26),
      I2 => sel0(0),
      I3 => sel0(1),
      I4 => service_cycles_counter(26),
      O => \r_data[26]_i_2_n_0\
    );
\r_data[26]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"A808"
    )
        port map (
      I0 => sel0(1),
      I1 => router_spike_count(26),
      I2 => sel0(0),
      I3 => neuron_spike_count(26),
      O => \r_data[26]_i_3_n_0\
    );
\r_data[26]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(26),
      I1 => \^router_config_wdata\(26),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(26),
      O => \r_data[26]_i_4_n_0\
    );
\r_data[27]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[27]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[27]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[27]_i_4_n_0\,
      O => r_data(27)
    );
\r_data[27]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FAEAAAEA"
    )
        port map (
      I0 => sel0(2),
      I1 => throughput_counter(27),
      I2 => sel0(0),
      I3 => sel0(1),
      I4 => service_cycles_counter(27),
      O => \r_data[27]_i_2_n_0\
    );
\r_data[27]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"A808"
    )
        port map (
      I0 => sel0(1),
      I1 => router_spike_count(27),
      I2 => sel0(0),
      I3 => neuron_spike_count(27),
      O => \r_data[27]_i_3_n_0\
    );
\r_data[27]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(27),
      I1 => \^router_config_wdata\(27),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(27),
      O => \r_data[27]_i_4_n_0\
    );
\r_data[28]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[28]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[28]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[28]_i_4_n_0\,
      O => r_data(28)
    );
\r_data[28]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFEAAFEA"
    )
        port map (
      I0 => sel0(2),
      I1 => throughput_counter(28),
      I2 => sel0(0),
      I3 => sel0(1),
      I4 => service_cycles_counter(28),
      O => \r_data[28]_i_2_n_0\
    );
\r_data[28]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"A808"
    )
        port map (
      I0 => sel0(1),
      I1 => router_spike_count(28),
      I2 => sel0(0),
      I3 => neuron_spike_count(28),
      O => \r_data[28]_i_3_n_0\
    );
\r_data[28]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(28),
      I1 => \^router_config_wdata\(28),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(28),
      O => \r_data[28]_i_4_n_0\
    );
\r_data[29]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[29]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[29]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[29]_i_4_n_0\,
      O => r_data(29)
    );
\r_data[29]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"0000C808"
    )
        port map (
      I0 => throughput_counter(29),
      I1 => sel0(0),
      I2 => sel0(1),
      I3 => service_cycles_counter(29),
      I4 => sel0(2),
      O => \r_data[29]_i_2_n_0\
    );
\r_data[29]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"A808"
    )
        port map (
      I0 => sel0(1),
      I1 => router_spike_count(29),
      I2 => sel0(0),
      I3 => neuron_spike_count(29),
      O => \r_data[29]_i_3_n_0\
    );
\r_data[29]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(29),
      I1 => \^router_config_wdata\(29),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(29),
      O => \r_data[29]_i_4_n_0\
    );
\r_data[2]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[2]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[2]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[2]_i_4_n_0\,
      O => r_data(2)
    );
\r_data[2]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FAFAFEAEAAAAFEAE"
    )
        port map (
      I0 => sel0(2),
      I1 => active_neurons(1),
      I2 => sel0(0),
      I3 => throughput_counter(2),
      I4 => sel0(1),
      I5 => service_cycles_counter(2),
      O => \r_data[2]_i_2_n_0\
    );
\r_data[2]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => neuron_spike_count(2),
      I1 => router_spike_count(2),
      I2 => sel0(1),
      I3 => \^global_leak_rate\(2),
      I4 => sel0(0),
      I5 => \^global_threshold\(2),
      O => \r_data[2]_i_3_n_0\
    );
\r_data[2]_i_4\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => router_config_rdata(2),
      I1 => \^router_config_wdata\(2),
      I2 => sel0(1),
      I3 => \^router_config_addr\(2),
      I4 => sel0(0),
      I5 => \reg_config_ctrl_reg_n_0_[2]\,
      O => \r_data[2]_i_4_n_0\
    );
\r_data[30]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[30]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[30]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[30]_i_4_n_0\,
      O => r_data(30)
    );
\r_data[30]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFEAAFEA"
    )
        port map (
      I0 => sel0(2),
      I1 => throughput_counter(30),
      I2 => sel0(0),
      I3 => sel0(1),
      I4 => service_cycles_counter(30),
      O => \r_data[30]_i_2_n_0\
    );
\r_data[30]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"A808"
    )
        port map (
      I0 => sel0(1),
      I1 => router_spike_count(30),
      I2 => sel0(0),
      I3 => neuron_spike_count(30),
      O => \r_data[30]_i_3_n_0\
    );
\r_data[30]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(30),
      I1 => \^router_config_wdata\(30),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(30),
      O => \r_data[30]_i_4_n_0\
    );
\r_data[31]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[31]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[31]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[31]_i_4_n_0\,
      O => r_data(31)
    );
\r_data[31]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FAEAAAEA"
    )
        port map (
      I0 => sel0(2),
      I1 => throughput_counter(31),
      I2 => sel0(0),
      I3 => sel0(1),
      I4 => service_cycles_counter(31),
      O => \r_data[31]_i_2_n_0\
    );
\r_data[31]_i_3\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"A808"
    )
        port map (
      I0 => sel0(1),
      I1 => router_spike_count(31),
      I2 => sel0(0),
      I3 => neuron_spike_count(31),
      O => \r_data[31]_i_3_n_0\
    );
\r_data[31]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(31),
      I1 => \^router_config_wdata\(31),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(31),
      O => \r_data[31]_i_4_n_0\
    );
\r_data[3]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[3]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[3]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[3]_i_4_n_0\,
      O => r_data(3)
    );
\r_data[3]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FAFAFEAEAAAAFEAE"
    )
        port map (
      I0 => sel0(2),
      I1 => active_neurons(2),
      I2 => sel0(0),
      I3 => throughput_counter(3),
      I4 => sel0(1),
      I5 => service_cycles_counter(3),
      O => \r_data[3]_i_2_n_0\
    );
\r_data[3]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => neuron_spike_count(3),
      I1 => router_spike_count(3),
      I2 => sel0(1),
      I3 => \^global_leak_rate\(3),
      I4 => sel0(0),
      I5 => \^global_threshold\(3),
      O => \r_data[3]_i_3_n_0\
    );
\r_data[3]_i_4\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => router_config_rdata(3),
      I1 => \^router_config_wdata\(3),
      I2 => sel0(1),
      I3 => \^router_config_addr\(3),
      I4 => sel0(0),
      I5 => \reg_config_ctrl_reg_n_0_[3]\,
      O => \r_data[3]_i_4_n_0\
    );
\r_data[4]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[4]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[4]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[4]_i_4_n_0\,
      O => r_data(4)
    );
\r_data[4]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"00000000CCE200E2"
    )
        port map (
      I0 => active_neurons(3),
      I1 => sel0(0),
      I2 => throughput_counter(4),
      I3 => sel0(1),
      I4 => service_cycles_counter(4),
      I5 => sel0(2),
      O => \r_data[4]_i_2_n_0\
    );
\r_data[4]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => neuron_spike_count(4),
      I1 => router_spike_count(4),
      I2 => sel0(1),
      I3 => \^global_leak_rate\(4),
      I4 => sel0(0),
      I5 => \^global_threshold\(4),
      O => \r_data[4]_i_3_n_0\
    );
\r_data[4]_i_4\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => router_config_rdata(4),
      I1 => \^router_config_wdata\(4),
      I2 => sel0(1),
      I3 => \^router_config_addr\(4),
      I4 => sel0(0),
      I5 => \reg_config_ctrl_reg_n_0_[4]\,
      O => \r_data[4]_i_4_n_0\
    );
\r_data[5]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[5]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[5]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[5]_i_4_n_0\,
      O => r_data(5)
    );
\r_data[5]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FAFAFEAEAAAAFEAE"
    )
        port map (
      I0 => sel0(2),
      I1 => active_neurons(4),
      I2 => sel0(0),
      I3 => throughput_counter(5),
      I4 => sel0(1),
      I5 => service_cycles_counter(5),
      O => \r_data[5]_i_2_n_0\
    );
\r_data[5]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => neuron_spike_count(5),
      I1 => router_spike_count(5),
      I2 => sel0(1),
      I3 => \^global_leak_rate\(5),
      I4 => sel0(0),
      I5 => \^global_threshold\(5),
      O => \r_data[5]_i_3_n_0\
    );
\r_data[5]_i_4\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => router_config_rdata(5),
      I1 => \^router_config_wdata\(5),
      I2 => sel0(1),
      I3 => \^router_config_addr\(5),
      I4 => sel0(0),
      I5 => \reg_config_ctrl_reg_n_0_[5]\,
      O => \r_data[5]_i_4_n_0\
    );
\r_data[6]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[6]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[6]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[6]_i_4_n_0\,
      O => r_data(6)
    );
\r_data[6]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FAFAFEAEAAAAFEAE"
    )
        port map (
      I0 => sel0(2),
      I1 => active_neurons(5),
      I2 => sel0(0),
      I3 => throughput_counter(6),
      I4 => sel0(1),
      I5 => service_cycles_counter(6),
      O => \r_data[6]_i_2_n_0\
    );
\r_data[6]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => neuron_spike_count(6),
      I1 => router_spike_count(6),
      I2 => sel0(1),
      I3 => \^global_leak_rate\(6),
      I4 => sel0(0),
      I5 => \^global_threshold\(6),
      O => \r_data[6]_i_3_n_0\
    );
\r_data[6]_i_4\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => router_config_rdata(6),
      I1 => \^router_config_wdata\(6),
      I2 => sel0(1),
      I3 => \^router_config_addr\(6),
      I4 => sel0(0),
      I5 => \reg_config_ctrl_reg_n_0_[6]\,
      O => \r_data[6]_i_4_n_0\
    );
\r_data[7]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[7]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[7]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[7]_i_4_n_0\,
      O => r_data(7)
    );
\r_data[7]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"FAFAFEAEAAAAFEAE"
    )
        port map (
      I0 => sel0(2),
      I1 => active_neurons(6),
      I2 => sel0(0),
      I3 => throughput_counter(7),
      I4 => sel0(1),
      I5 => service_cycles_counter(7),
      O => \r_data[7]_i_2_n_0\
    );
\r_data[7]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => neuron_spike_count(7),
      I1 => router_spike_count(7),
      I2 => sel0(1),
      I3 => \^global_leak_rate\(7),
      I4 => sel0(0),
      I5 => \^global_threshold\(7),
      O => \r_data[7]_i_3_n_0\
    );
\r_data[7]_i_4\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => router_config_rdata(7),
      I1 => \^router_config_wdata\(7),
      I2 => sel0(1),
      I3 => \^router_config_addr\(7),
      I4 => sel0(0),
      I5 => \reg_config_ctrl_reg_n_0_[7]\,
      O => \r_data[7]_i_4_n_0\
    );
\r_data[8]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[8]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[8]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[8]_i_4_n_0\,
      O => r_data(8)
    );
\r_data[8]_i_2\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"00000000CCE200E2"
    )
        port map (
      I0 => active_neurons(7),
      I1 => sel0(0),
      I2 => throughput_counter(8),
      I3 => sel0(1),
      I4 => service_cycles_counter(8),
      I5 => sel0(2),
      O => \r_data[8]_i_2_n_0\
    );
\r_data[8]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => neuron_spike_count(8),
      I1 => router_spike_count(8),
      I2 => sel0(1),
      I3 => \^global_refrac_period\(0),
      I4 => sel0(0),
      I5 => \^global_threshold\(8),
      O => \r_data[8]_i_3_n_0\
    );
\r_data[8]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(8),
      I1 => \^router_config_wdata\(8),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(8),
      O => \r_data[8]_i_4_n_0\
    );
\r_data[9]_i_1\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"B8BBB888"
    )
        port map (
      I0 => \r_data[9]_i_2_n_0\,
      I1 => sel0(3),
      I2 => \r_data[9]_i_3_n_0\,
      I3 => sel0(2),
      I4 => \r_data[9]_i_4_n_0\,
      O => r_data(9)
    );
\r_data[9]_i_2\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"FFEAAFEA"
    )
        port map (
      I0 => sel0(2),
      I1 => throughput_counter(9),
      I2 => sel0(0),
      I3 => sel0(1),
      I4 => service_cycles_counter(9),
      O => \r_data[9]_i_2_n_0\
    );
\r_data[9]_i_3\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"AFA0CFCFAFA0C0C0"
    )
        port map (
      I0 => neuron_spike_count(9),
      I1 => router_spike_count(9),
      I2 => sel0(1),
      I3 => \^global_refrac_period\(1),
      I4 => sel0(0),
      I5 => \^global_threshold\(9),
      O => \r_data[9]_i_3_n_0\
    );
\r_data[9]_i_4\: unisim.vcomponents.LUT5
    generic map(
      INIT => X"AFC0A0C0"
    )
        port map (
      I0 => router_config_rdata(9),
      I1 => \^router_config_wdata\(9),
      I2 => sel0(1),
      I3 => sel0(0),
      I4 => \^router_config_addr\(9),
      O => \r_data[9]_i_4_n_0\
    );
\r_data_reg[0]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(0),
      Q => s_axi_rdata(0),
      R => p_0_in
    );
\r_data_reg[10]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(10),
      Q => s_axi_rdata(10),
      R => p_0_in
    );
\r_data_reg[11]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(11),
      Q => s_axi_rdata(11),
      R => p_0_in
    );
\r_data_reg[12]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(12),
      Q => s_axi_rdata(12),
      R => p_0_in
    );
\r_data_reg[13]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(13),
      Q => s_axi_rdata(13),
      R => p_0_in
    );
\r_data_reg[14]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(14),
      Q => s_axi_rdata(14),
      R => p_0_in
    );
\r_data_reg[15]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(15),
      Q => s_axi_rdata(15),
      R => p_0_in
    );
\r_data_reg[16]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(16),
      Q => s_axi_rdata(16),
      R => p_0_in
    );
\r_data_reg[17]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(17),
      Q => s_axi_rdata(17),
      R => p_0_in
    );
\r_data_reg[18]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(18),
      Q => s_axi_rdata(18),
      R => p_0_in
    );
\r_data_reg[19]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(19),
      Q => s_axi_rdata(19),
      R => p_0_in
    );
\r_data_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(1),
      Q => s_axi_rdata(1),
      R => p_0_in
    );
\r_data_reg[20]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(20),
      Q => s_axi_rdata(20),
      R => p_0_in
    );
\r_data_reg[21]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(21),
      Q => s_axi_rdata(21),
      R => p_0_in
    );
\r_data_reg[22]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(22),
      Q => s_axi_rdata(22),
      R => p_0_in
    );
\r_data_reg[23]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(23),
      Q => s_axi_rdata(23),
      R => p_0_in
    );
\r_data_reg[24]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(24),
      Q => s_axi_rdata(24),
      R => p_0_in
    );
\r_data_reg[25]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(25),
      Q => s_axi_rdata(25),
      R => p_0_in
    );
\r_data_reg[26]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(26),
      Q => s_axi_rdata(26),
      R => p_0_in
    );
\r_data_reg[27]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(27),
      Q => s_axi_rdata(27),
      R => p_0_in
    );
\r_data_reg[28]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(28),
      Q => s_axi_rdata(28),
      R => p_0_in
    );
\r_data_reg[29]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(29),
      Q => s_axi_rdata(29),
      R => p_0_in
    );
\r_data_reg[2]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(2),
      Q => s_axi_rdata(2),
      R => p_0_in
    );
\r_data_reg[30]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(30),
      Q => s_axi_rdata(30),
      R => p_0_in
    );
\r_data_reg[31]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(31),
      Q => s_axi_rdata(31),
      R => p_0_in
    );
\r_data_reg[3]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(3),
      Q => s_axi_rdata(3),
      R => p_0_in
    );
\r_data_reg[4]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(4),
      Q => s_axi_rdata(4),
      R => p_0_in
    );
\r_data_reg[5]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(5),
      Q => s_axi_rdata(5),
      R => p_0_in
    );
\r_data_reg[6]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(6),
      Q => s_axi_rdata(6),
      R => p_0_in
    );
\r_data_reg[7]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(7),
      Q => s_axi_rdata(7),
      R => p_0_in
    );
\r_data_reg[8]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(8),
      Q => s_axi_rdata(8),
      R => p_0_in
    );
\r_data_reg[9]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \r_data0__0\,
      D => r_data(9),
      Q => s_axi_rdata(9),
      R => p_0_in
    );
r_valid_i_1: unisim.vcomponents.LUT4
    generic map(
      INIT => X"08F8"
    )
        port map (
      I0 => \^s_axi_arready\,
      I1 => s_axi_arvalid,
      I2 => \^s_axi_rvalid\,
      I3 => s_axi_rready,
      O => r_valid_i_1_n_0
    );
r_valid_reg: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => r_valid_i_1_n_0,
      Q => \^s_axi_rvalid\,
      R => p_0_in
    );
\reg_config_addr[15]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000002000"
    )
        port map (
      I0 => \write_en__1\,
      I1 => write_addr(3),
      I2 => write_addr(0),
      I3 => s_axi_wstrb(1),
      I4 => write_addr(1),
      I5 => write_addr(2),
      O => p_1_in(15)
    );
\reg_config_addr[23]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000002000"
    )
        port map (
      I0 => \write_en__1\,
      I1 => write_addr(3),
      I2 => write_addr(0),
      I3 => s_axi_wstrb(2),
      I4 => write_addr(1),
      I5 => write_addr(2),
      O => p_1_in(23)
    );
\reg_config_addr[31]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000002000"
    )
        port map (
      I0 => \write_en__1\,
      I1 => write_addr(3),
      I2 => write_addr(0),
      I3 => s_axi_wstrb(3),
      I4 => write_addr(1),
      I5 => write_addr(2),
      O => p_1_in(31)
    );
\reg_config_addr[31]_i_2\: unisim.vcomponents.LUT4
    generic map(
      INIT => X"8000"
    )
        port map (
      I0 => s_axi_awvalid,
      I1 => s_axi_wvalid,
      I2 => \^s_axi_awready\,
      I3 => \^s_axi_wready\,
      O => \write_en__1\
    );
\reg_config_addr[7]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000002000"
    )
        port map (
      I0 => \write_en__1\,
      I1 => write_addr(3),
      I2 => write_addr(0),
      I3 => s_axi_wstrb(0),
      I4 => write_addr(1),
      I5 => write_addr(2),
      O => p_1_in(7)
    );
\reg_config_addr_reg[0]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => s_axi_wdata(0),
      Q => \^router_config_addr\(0),
      R => p_0_in
    );
\reg_config_addr_reg[10]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => s_axi_wdata(10),
      Q => \^router_config_addr\(10),
      R => p_0_in
    );
\reg_config_addr_reg[11]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => s_axi_wdata(11),
      Q => \^router_config_addr\(11),
      R => p_0_in
    );
\reg_config_addr_reg[12]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => s_axi_wdata(12),
      Q => \^router_config_addr\(12),
      R => p_0_in
    );
\reg_config_addr_reg[13]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => s_axi_wdata(13),
      Q => \^router_config_addr\(13),
      R => p_0_in
    );
\reg_config_addr_reg[14]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => s_axi_wdata(14),
      Q => \^router_config_addr\(14),
      R => p_0_in
    );
\reg_config_addr_reg[15]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => s_axi_wdata(15),
      Q => \^router_config_addr\(15),
      R => p_0_in
    );
\reg_config_addr_reg[16]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => s_axi_wdata(16),
      Q => \^router_config_addr\(16),
      R => p_0_in
    );
\reg_config_addr_reg[17]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => s_axi_wdata(17),
      Q => \^router_config_addr\(17),
      R => p_0_in
    );
\reg_config_addr_reg[18]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => s_axi_wdata(18),
      Q => \^router_config_addr\(18),
      R => p_0_in
    );
\reg_config_addr_reg[19]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => s_axi_wdata(19),
      Q => \^router_config_addr\(19),
      R => p_0_in
    );
\reg_config_addr_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => s_axi_wdata(1),
      Q => \^router_config_addr\(1),
      R => p_0_in
    );
\reg_config_addr_reg[20]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => s_axi_wdata(20),
      Q => \^router_config_addr\(20),
      R => p_0_in
    );
\reg_config_addr_reg[21]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => s_axi_wdata(21),
      Q => \^router_config_addr\(21),
      R => p_0_in
    );
\reg_config_addr_reg[22]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => s_axi_wdata(22),
      Q => \^router_config_addr\(22),
      R => p_0_in
    );
\reg_config_addr_reg[23]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(23),
      D => s_axi_wdata(23),
      Q => \^router_config_addr\(23),
      R => p_0_in
    );
\reg_config_addr_reg[24]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => s_axi_wdata(24),
      Q => \^router_config_addr\(24),
      R => p_0_in
    );
\reg_config_addr_reg[25]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => s_axi_wdata(25),
      Q => \^router_config_addr\(25),
      R => p_0_in
    );
\reg_config_addr_reg[26]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => s_axi_wdata(26),
      Q => \^router_config_addr\(26),
      R => p_0_in
    );
\reg_config_addr_reg[27]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => s_axi_wdata(27),
      Q => \^router_config_addr\(27),
      R => p_0_in
    );
\reg_config_addr_reg[28]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => s_axi_wdata(28),
      Q => \^router_config_addr\(28),
      R => p_0_in
    );
\reg_config_addr_reg[29]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => s_axi_wdata(29),
      Q => \^router_config_addr\(29),
      R => p_0_in
    );
\reg_config_addr_reg[2]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => s_axi_wdata(2),
      Q => \^router_config_addr\(2),
      R => p_0_in
    );
\reg_config_addr_reg[30]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => s_axi_wdata(30),
      Q => \^router_config_addr\(30),
      R => p_0_in
    );
\reg_config_addr_reg[31]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(31),
      D => s_axi_wdata(31),
      Q => \^router_config_addr\(31),
      R => p_0_in
    );
\reg_config_addr_reg[3]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => s_axi_wdata(3),
      Q => \^router_config_addr\(3),
      R => p_0_in
    );
\reg_config_addr_reg[4]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => s_axi_wdata(4),
      Q => \^router_config_addr\(4),
      R => p_0_in
    );
\reg_config_addr_reg[5]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => s_axi_wdata(5),
      Q => \^router_config_addr\(5),
      R => p_0_in
    );
\reg_config_addr_reg[6]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => s_axi_wdata(6),
      Q => \^router_config_addr\(6),
      R => p_0_in
    );
\reg_config_addr_reg[7]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(7),
      D => s_axi_wdata(7),
      Q => \^router_config_addr\(7),
      R => p_0_in
    );
\reg_config_addr_reg[8]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => s_axi_wdata(8),
      Q => \^router_config_addr\(8),
      R => p_0_in
    );
\reg_config_addr_reg[9]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => p_1_in(15),
      D => s_axi_wdata(9),
      Q => \^router_config_addr\(9),
      R => p_0_in
    );
\reg_config_ctrl[7]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000000020"
    )
        port map (
      I0 => \write_en__1\,
      I1 => write_addr(3),
      I2 => s_axi_wstrb(0),
      I3 => write_addr(2),
      I4 => write_addr(0),
      I5 => write_addr(1),
      O => reg_config_ctrl(7)
    );
\reg_config_ctrl_reg[0]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_config_ctrl(7),
      D => s_axi_wdata(0),
      Q => \reg_config_ctrl_reg_n_0_[0]\,
      R => p_0_in
    );
\reg_config_ctrl_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_config_ctrl(7),
      D => s_axi_wdata(1),
      Q => \reg_config_ctrl_reg_n_0_[1]\,
      R => p_0_in
    );
\reg_config_ctrl_reg[2]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_config_ctrl(7),
      D => s_axi_wdata(2),
      Q => \reg_config_ctrl_reg_n_0_[2]\,
      R => p_0_in
    );
\reg_config_ctrl_reg[3]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_config_ctrl(7),
      D => s_axi_wdata(3),
      Q => \reg_config_ctrl_reg_n_0_[3]\,
      R => p_0_in
    );
\reg_config_ctrl_reg[4]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_config_ctrl(7),
      D => s_axi_wdata(4),
      Q => \reg_config_ctrl_reg_n_0_[4]\,
      R => p_0_in
    );
\reg_config_ctrl_reg[5]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_config_ctrl(7),
      D => s_axi_wdata(5),
      Q => \reg_config_ctrl_reg_n_0_[5]\,
      R => p_0_in
    );
\reg_config_ctrl_reg[6]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_config_ctrl(7),
      D => s_axi_wdata(6),
      Q => \reg_config_ctrl_reg_n_0_[6]\,
      R => p_0_in
    );
\reg_config_ctrl_reg[7]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_config_ctrl(7),
      D => s_axi_wdata(7),
      Q => \reg_config_ctrl_reg_n_0_[7]\,
      R => p_0_in
    );
\reg_config_wdata[15]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000002000"
    )
        port map (
      I0 => \write_en__1\,
      I1 => write_addr(3),
      I2 => write_addr(1),
      I3 => s_axi_wstrb(1),
      I4 => write_addr(0),
      I5 => write_addr(2),
      O => \reg_config_wdata[15]_i_1_n_0\
    );
\reg_config_wdata[23]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000002000"
    )
        port map (
      I0 => \write_en__1\,
      I1 => write_addr(3),
      I2 => write_addr(1),
      I3 => s_axi_wstrb(2),
      I4 => write_addr(0),
      I5 => write_addr(2),
      O => \reg_config_wdata[23]_i_1_n_0\
    );
\reg_config_wdata[31]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000002000"
    )
        port map (
      I0 => \write_en__1\,
      I1 => write_addr(3),
      I2 => write_addr(1),
      I3 => s_axi_wstrb(3),
      I4 => write_addr(0),
      I5 => write_addr(2),
      O => \reg_config_wdata[31]_i_1_n_0\
    );
\reg_config_wdata[7]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000002000"
    )
        port map (
      I0 => \write_en__1\,
      I1 => write_addr(3),
      I2 => write_addr(1),
      I3 => s_axi_wstrb(0),
      I4 => write_addr(0),
      I5 => write_addr(2),
      O => \reg_config_wdata[7]_i_1_n_0\
    );
\reg_config_wdata_reg[0]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[7]_i_1_n_0\,
      D => s_axi_wdata(0),
      Q => \^router_config_wdata\(0),
      R => p_0_in
    );
\reg_config_wdata_reg[10]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[15]_i_1_n_0\,
      D => s_axi_wdata(10),
      Q => \^router_config_wdata\(10),
      R => p_0_in
    );
\reg_config_wdata_reg[11]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[15]_i_1_n_0\,
      D => s_axi_wdata(11),
      Q => \^router_config_wdata\(11),
      R => p_0_in
    );
\reg_config_wdata_reg[12]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[15]_i_1_n_0\,
      D => s_axi_wdata(12),
      Q => \^router_config_wdata\(12),
      R => p_0_in
    );
\reg_config_wdata_reg[13]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[15]_i_1_n_0\,
      D => s_axi_wdata(13),
      Q => \^router_config_wdata\(13),
      R => p_0_in
    );
\reg_config_wdata_reg[14]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[15]_i_1_n_0\,
      D => s_axi_wdata(14),
      Q => \^router_config_wdata\(14),
      R => p_0_in
    );
\reg_config_wdata_reg[15]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[15]_i_1_n_0\,
      D => s_axi_wdata(15),
      Q => \^router_config_wdata\(15),
      R => p_0_in
    );
\reg_config_wdata_reg[16]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[23]_i_1_n_0\,
      D => s_axi_wdata(16),
      Q => \^router_config_wdata\(16),
      R => p_0_in
    );
\reg_config_wdata_reg[17]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[23]_i_1_n_0\,
      D => s_axi_wdata(17),
      Q => \^router_config_wdata\(17),
      R => p_0_in
    );
\reg_config_wdata_reg[18]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[23]_i_1_n_0\,
      D => s_axi_wdata(18),
      Q => \^router_config_wdata\(18),
      R => p_0_in
    );
\reg_config_wdata_reg[19]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[23]_i_1_n_0\,
      D => s_axi_wdata(19),
      Q => \^router_config_wdata\(19),
      R => p_0_in
    );
\reg_config_wdata_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[7]_i_1_n_0\,
      D => s_axi_wdata(1),
      Q => \^router_config_wdata\(1),
      R => p_0_in
    );
\reg_config_wdata_reg[20]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[23]_i_1_n_0\,
      D => s_axi_wdata(20),
      Q => \^router_config_wdata\(20),
      R => p_0_in
    );
\reg_config_wdata_reg[21]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[23]_i_1_n_0\,
      D => s_axi_wdata(21),
      Q => \^router_config_wdata\(21),
      R => p_0_in
    );
\reg_config_wdata_reg[22]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[23]_i_1_n_0\,
      D => s_axi_wdata(22),
      Q => \^router_config_wdata\(22),
      R => p_0_in
    );
\reg_config_wdata_reg[23]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[23]_i_1_n_0\,
      D => s_axi_wdata(23),
      Q => \^router_config_wdata\(23),
      R => p_0_in
    );
\reg_config_wdata_reg[24]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[31]_i_1_n_0\,
      D => s_axi_wdata(24),
      Q => \^router_config_wdata\(24),
      R => p_0_in
    );
\reg_config_wdata_reg[25]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[31]_i_1_n_0\,
      D => s_axi_wdata(25),
      Q => \^router_config_wdata\(25),
      R => p_0_in
    );
\reg_config_wdata_reg[26]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[31]_i_1_n_0\,
      D => s_axi_wdata(26),
      Q => \^router_config_wdata\(26),
      R => p_0_in
    );
\reg_config_wdata_reg[27]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[31]_i_1_n_0\,
      D => s_axi_wdata(27),
      Q => \^router_config_wdata\(27),
      R => p_0_in
    );
\reg_config_wdata_reg[28]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[31]_i_1_n_0\,
      D => s_axi_wdata(28),
      Q => \^router_config_wdata\(28),
      R => p_0_in
    );
\reg_config_wdata_reg[29]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[31]_i_1_n_0\,
      D => s_axi_wdata(29),
      Q => \^router_config_wdata\(29),
      R => p_0_in
    );
\reg_config_wdata_reg[2]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[7]_i_1_n_0\,
      D => s_axi_wdata(2),
      Q => \^router_config_wdata\(2),
      R => p_0_in
    );
\reg_config_wdata_reg[30]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[31]_i_1_n_0\,
      D => s_axi_wdata(30),
      Q => \^router_config_wdata\(30),
      R => p_0_in
    );
\reg_config_wdata_reg[31]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[31]_i_1_n_0\,
      D => s_axi_wdata(31),
      Q => \^router_config_wdata\(31),
      R => p_0_in
    );
\reg_config_wdata_reg[3]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[7]_i_1_n_0\,
      D => s_axi_wdata(3),
      Q => \^router_config_wdata\(3),
      R => p_0_in
    );
\reg_config_wdata_reg[4]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[7]_i_1_n_0\,
      D => s_axi_wdata(4),
      Q => \^router_config_wdata\(4),
      R => p_0_in
    );
\reg_config_wdata_reg[5]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[7]_i_1_n_0\,
      D => s_axi_wdata(5),
      Q => \^router_config_wdata\(5),
      R => p_0_in
    );
\reg_config_wdata_reg[6]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[7]_i_1_n_0\,
      D => s_axi_wdata(6),
      Q => \^router_config_wdata\(6),
      R => p_0_in
    );
\reg_config_wdata_reg[7]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[7]_i_1_n_0\,
      D => s_axi_wdata(7),
      Q => \^router_config_wdata\(7),
      R => p_0_in
    );
\reg_config_wdata_reg[8]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[15]_i_1_n_0\,
      D => s_axi_wdata(8),
      Q => \^router_config_wdata\(8),
      R => p_0_in
    );
\reg_config_wdata_reg[9]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_config_wdata[15]_i_1_n_0\,
      D => s_axi_wdata(9),
      Q => \^router_config_wdata\(9),
      R => p_0_in
    );
\reg_leak_rate[7]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0020000000000000"
    )
        port map (
      I0 => \write_en__1\,
      I1 => write_addr(3),
      I2 => write_addr(2),
      I3 => write_addr(1),
      I4 => write_addr(0),
      I5 => s_axi_wstrb(0),
      O => reg_leak_rate(0)
    );
\reg_leak_rate_reg[0]\: unisim.vcomponents.FDSE
     port map (
      C => s_axi_aclk,
      CE => reg_leak_rate(0),
      D => s_axi_wdata(0),
      Q => \^global_leak_rate\(0),
      S => p_0_in
    );
\reg_leak_rate_reg[1]\: unisim.vcomponents.FDSE
     port map (
      C => s_axi_aclk,
      CE => reg_leak_rate(0),
      D => s_axi_wdata(1),
      Q => \^global_leak_rate\(1),
      S => p_0_in
    );
\reg_leak_rate_reg[2]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_leak_rate(0),
      D => s_axi_wdata(2),
      Q => \^global_leak_rate\(2),
      R => p_0_in
    );
\reg_leak_rate_reg[3]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_leak_rate(0),
      D => s_axi_wdata(3),
      Q => \^global_leak_rate\(3),
      R => p_0_in
    );
\reg_leak_rate_reg[4]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_leak_rate(0),
      D => s_axi_wdata(4),
      Q => \^global_leak_rate\(4),
      R => p_0_in
    );
\reg_leak_rate_reg[5]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_leak_rate(0),
      D => s_axi_wdata(5),
      Q => \^global_leak_rate\(5),
      R => p_0_in
    );
\reg_leak_rate_reg[6]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_leak_rate(0),
      D => s_axi_wdata(6),
      Q => \^global_leak_rate\(6),
      R => p_0_in
    );
\reg_leak_rate_reg[7]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_leak_rate(0),
      D => s_axi_wdata(7),
      Q => \^global_leak_rate\(7),
      R => p_0_in
    );
\reg_refrac_period[7]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0020000000000000"
    )
        port map (
      I0 => \write_en__1\,
      I1 => write_addr(3),
      I2 => write_addr(2),
      I3 => write_addr(1),
      I4 => write_addr(0),
      I5 => s_axi_wstrb(1),
      O => reg_refrac_period(0)
    );
\reg_refrac_period_reg[0]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_refrac_period(0),
      D => s_axi_wdata(8),
      Q => \^global_refrac_period\(0),
      R => p_0_in
    );
\reg_refrac_period_reg[1]\: unisim.vcomponents.FDSE
     port map (
      C => s_axi_aclk,
      CE => reg_refrac_period(0),
      D => s_axi_wdata(9),
      Q => \^global_refrac_period\(1),
      S => p_0_in
    );
\reg_refrac_period_reg[2]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_refrac_period(0),
      D => s_axi_wdata(10),
      Q => \^global_refrac_period\(2),
      R => p_0_in
    );
\reg_refrac_period_reg[3]\: unisim.vcomponents.FDSE
     port map (
      C => s_axi_aclk,
      CE => reg_refrac_period(0),
      D => s_axi_wdata(11),
      Q => \^global_refrac_period\(3),
      S => p_0_in
    );
\reg_refrac_period_reg[4]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_refrac_period(0),
      D => s_axi_wdata(12),
      Q => \^global_refrac_period\(4),
      R => p_0_in
    );
\reg_refrac_period_reg[5]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_refrac_period(0),
      D => s_axi_wdata(13),
      Q => \^global_refrac_period\(5),
      R => p_0_in
    );
\reg_refrac_period_reg[6]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_refrac_period(0),
      D => s_axi_wdata(14),
      Q => \^global_refrac_period\(6),
      R => p_0_in
    );
\reg_refrac_period_reg[7]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => reg_refrac_period(0),
      D => s_axi_wdata(15),
      Q => \^global_refrac_period\(7),
      R => p_0_in
    );
\reg_threshold[15]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000002000"
    )
        port map (
      I0 => \write_en__1\,
      I1 => write_addr(3),
      I2 => s_axi_wstrb(1),
      I3 => write_addr(2),
      I4 => write_addr(0),
      I5 => write_addr(1),
      O => \reg_threshold[15]_i_1_n_0\
    );
\reg_threshold[7]_i_1\: unisim.vcomponents.LUT6
    generic map(
      INIT => X"0000000000002000"
    )
        port map (
      I0 => \write_en__1\,
      I1 => write_addr(3),
      I2 => s_axi_wstrb(0),
      I3 => write_addr(2),
      I4 => write_addr(0),
      I5 => write_addr(1),
      O => \reg_threshold[7]_i_1_n_0\
    );
\reg_threshold_reg[0]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_threshold[7]_i_1_n_0\,
      D => s_axi_wdata(0),
      Q => \^global_threshold\(0),
      R => p_0_in
    );
\reg_threshold_reg[10]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_threshold[15]_i_1_n_0\,
      D => s_axi_wdata(10),
      Q => \^global_threshold\(10),
      R => p_0_in
    );
\reg_threshold_reg[11]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_threshold[15]_i_1_n_0\,
      D => s_axi_wdata(11),
      Q => \^global_threshold\(11),
      R => p_0_in
    );
\reg_threshold_reg[12]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_threshold[15]_i_1_n_0\,
      D => s_axi_wdata(12),
      Q => \^global_threshold\(12),
      R => p_0_in
    );
\reg_threshold_reg[13]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_threshold[15]_i_1_n_0\,
      D => s_axi_wdata(13),
      Q => \^global_threshold\(13),
      R => p_0_in
    );
\reg_threshold_reg[14]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_threshold[15]_i_1_n_0\,
      D => s_axi_wdata(14),
      Q => \^global_threshold\(14),
      R => p_0_in
    );
\reg_threshold_reg[15]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_threshold[15]_i_1_n_0\,
      D => s_axi_wdata(15),
      Q => \^global_threshold\(15),
      R => p_0_in
    );
\reg_threshold_reg[1]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_threshold[7]_i_1_n_0\,
      D => s_axi_wdata(1),
      Q => \^global_threshold\(1),
      R => p_0_in
    );
\reg_threshold_reg[2]\: unisim.vcomponents.FDSE
     port map (
      C => s_axi_aclk,
      CE => \reg_threshold[7]_i_1_n_0\,
      D => s_axi_wdata(2),
      Q => \^global_threshold\(2),
      S => p_0_in
    );
\reg_threshold_reg[3]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_threshold[7]_i_1_n_0\,
      D => s_axi_wdata(3),
      Q => \^global_threshold\(3),
      R => p_0_in
    );
\reg_threshold_reg[4]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_threshold[7]_i_1_n_0\,
      D => s_axi_wdata(4),
      Q => \^global_threshold\(4),
      R => p_0_in
    );
\reg_threshold_reg[5]\: unisim.vcomponents.FDSE
     port map (
      C => s_axi_aclk,
      CE => \reg_threshold[7]_i_1_n_0\,
      D => s_axi_wdata(5),
      Q => \^global_threshold\(5),
      S => p_0_in
    );
\reg_threshold_reg[6]\: unisim.vcomponents.FDSE
     port map (
      C => s_axi_aclk,
      CE => \reg_threshold[7]_i_1_n_0\,
      D => s_axi_wdata(6),
      Q => \^global_threshold\(6),
      S => p_0_in
    );
\reg_threshold_reg[7]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_threshold[7]_i_1_n_0\,
      D => s_axi_wdata(7),
      Q => \^global_threshold\(7),
      R => p_0_in
    );
\reg_threshold_reg[8]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_threshold[15]_i_1_n_0\,
      D => s_axi_wdata(8),
      Q => \^global_threshold\(8),
      R => p_0_in
    );
\reg_threshold_reg[9]\: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => \reg_threshold[15]_i_1_n_0\,
      D => s_axi_wdata(9),
      Q => \^global_threshold\(9),
      R => p_0_in
    );
\router_config_we__0\: unisim.vcomponents.LUT3
    generic map(
      INIT => X"02"
    )
        port map (
      I0 => config_we_pulse,
      I1 => \config_target_reg_n_0_[1]\,
      I2 => \config_target_reg_n_0_[0]\,
      O => router_config_we
    );
w_ready_i_1: unisim.vcomponents.LUT4
    generic map(
      INIT => X"2000"
    )
        port map (
      I0 => aw_en_reg_n_0,
      I1 => \^s_axi_wready\,
      I2 => s_axi_wvalid,
      I3 => s_axi_awvalid,
      O => w_ready0
    );
w_ready_reg: unisim.vcomponents.FDRE
     port map (
      C => s_axi_aclk,
      CE => '1',
      D => w_ready0,
      Q => \^s_axi_wready\,
      R => p_0_in
    );
end STRUCTURE;
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
library UNISIM;
use UNISIM.VCOMPONENTS.ALL;
entity design_1_snn_config_regs_0_0 is
  port (
    s_axi_aclk : in STD_LOGIC;
    s_axi_aresetn : in STD_LOGIC;
    s_axi_awaddr : in STD_LOGIC_VECTOR ( 5 downto 0 );
    s_axi_awprot : in STD_LOGIC_VECTOR ( 2 downto 0 );
    s_axi_awvalid : in STD_LOGIC;
    s_axi_awready : out STD_LOGIC;
    s_axi_wdata : in STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_wstrb : in STD_LOGIC_VECTOR ( 3 downto 0 );
    s_axi_wvalid : in STD_LOGIC;
    s_axi_wready : out STD_LOGIC;
    s_axi_bresp : out STD_LOGIC_VECTOR ( 1 downto 0 );
    s_axi_bvalid : out STD_LOGIC;
    s_axi_bready : in STD_LOGIC;
    s_axi_araddr : in STD_LOGIC_VECTOR ( 5 downto 0 );
    s_axi_arprot : in STD_LOGIC_VECTOR ( 2 downto 0 );
    s_axi_arvalid : in STD_LOGIC;
    s_axi_arready : out STD_LOGIC;
    s_axi_rdata : out STD_LOGIC_VECTOR ( 31 downto 0 );
    s_axi_rresp : out STD_LOGIC_VECTOR ( 1 downto 0 );
    s_axi_rvalid : out STD_LOGIC;
    s_axi_rready : in STD_LOGIC;
    router_config_we : out STD_LOGIC;
    router_config_addr : out STD_LOGIC_VECTOR ( 31 downto 0 );
    router_config_wdata : out STD_LOGIC_VECTOR ( 31 downto 0 );
    router_config_rdata : in STD_LOGIC_VECTOR ( 31 downto 0 );
    neuron_config_we : out STD_LOGIC;
    neuron_config_addr : out STD_LOGIC_VECTOR ( 9 downto 0 );
    neuron_config_wdata : out STD_LOGIC_VECTOR ( 31 downto 0 );
    global_threshold : out STD_LOGIC_VECTOR ( 15 downto 0 );
    global_leak_rate : out STD_LOGIC_VECTOR ( 7 downto 0 );
    global_refrac_period : out STD_LOGIC_VECTOR ( 7 downto 0 );
    router_spike_count : in STD_LOGIC_VECTOR ( 31 downto 0 );
    neuron_spike_count : in STD_LOGIC_VECTOR ( 31 downto 0 );
    fifo_overflow : in STD_LOGIC;
    active_neurons : in STD_LOGIC_VECTOR ( 7 downto 0 );
    throughput_counter : in STD_LOGIC_VECTOR ( 31 downto 0 );
    service_cycles_counter : in STD_LOGIC_VECTOR ( 31 downto 0 )
  );
  attribute NotValidForBitStream : boolean;
  attribute NotValidForBitStream of design_1_snn_config_regs_0_0 : entity is true;
  attribute CHECK_LICENSE_TYPE : string;
  attribute CHECK_LICENSE_TYPE of design_1_snn_config_regs_0_0 : entity is "design_1_snn_config_regs_0_0,snn_config_regs,{}";
  attribute DowngradeIPIdentifiedWarnings : string;
  attribute DowngradeIPIdentifiedWarnings of design_1_snn_config_regs_0_0 : entity is "yes";
  attribute IP_DEFINITION_SOURCE : string;
  attribute IP_DEFINITION_SOURCE of design_1_snn_config_regs_0_0 : entity is "module_ref";
  attribute X_CORE_INFO : string;
  attribute X_CORE_INFO of design_1_snn_config_regs_0_0 : entity is "snn_config_regs,Vivado 2025.2";
end design_1_snn_config_regs_0_0;

architecture STRUCTURE of design_1_snn_config_regs_0_0 is
  signal \<const0>\ : STD_LOGIC;
  signal \^router_config_addr\ : STD_LOGIC_VECTOR ( 31 downto 0 );
  signal \^router_config_wdata\ : STD_LOGIC_VECTOR ( 31 downto 0 );
  attribute X_INTERFACE_INFO : string;
  attribute X_INTERFACE_INFO of s_axi_aclk : signal is "xilinx.com:signal:clock:1.0 s_axi_aclk CLK";
  attribute X_INTERFACE_MODE : string;
  attribute X_INTERFACE_MODE of s_axi_aclk : signal is "slave";
  attribute X_INTERFACE_PARAMETER : string;
  attribute X_INTERFACE_PARAMETER of s_axi_aclk : signal is "XIL_INTERFACENAME s_axi_aclk, ASSOCIATED_BUSIF s_axi, ASSOCIATED_RESET s_axi_aresetn, FREQ_HZ 100000000, FREQ_TOLERANCE_HZ 0, PHASE 0.0, CLK_DOMAIN design_1_processing_system7_0_0_FCLK_CLK0, INSERT_VIP 0";
  attribute X_INTERFACE_INFO of s_axi_aresetn : signal is "xilinx.com:signal:reset:1.0 s_axi_aresetn RST";
  attribute X_INTERFACE_MODE of s_axi_aresetn : signal is "slave";
  attribute X_INTERFACE_PARAMETER of s_axi_aresetn : signal is "XIL_INTERFACENAME s_axi_aresetn, POLARITY ACTIVE_LOW, INSERT_VIP 0";
  attribute X_INTERFACE_INFO of s_axi_arready : signal is "xilinx.com:interface:aximm:1.0 s_axi ARREADY";
  attribute X_INTERFACE_INFO of s_axi_arvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi ARVALID";
  attribute X_INTERFACE_INFO of s_axi_awready : signal is "xilinx.com:interface:aximm:1.0 s_axi AWREADY";
  attribute X_INTERFACE_INFO of s_axi_awvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi AWVALID";
  attribute X_INTERFACE_INFO of s_axi_bready : signal is "xilinx.com:interface:aximm:1.0 s_axi BREADY";
  attribute X_INTERFACE_INFO of s_axi_bvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi BVALID";
  attribute X_INTERFACE_INFO of s_axi_rready : signal is "xilinx.com:interface:aximm:1.0 s_axi RREADY";
  attribute X_INTERFACE_INFO of s_axi_rvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi RVALID";
  attribute X_INTERFACE_INFO of s_axi_wready : signal is "xilinx.com:interface:aximm:1.0 s_axi WREADY";
  attribute X_INTERFACE_INFO of s_axi_wvalid : signal is "xilinx.com:interface:aximm:1.0 s_axi WVALID";
  attribute X_INTERFACE_INFO of s_axi_araddr : signal is "xilinx.com:interface:aximm:1.0 s_axi ARADDR";
  attribute X_INTERFACE_INFO of s_axi_arprot : signal is "xilinx.com:interface:aximm:1.0 s_axi ARPROT";
  attribute X_INTERFACE_INFO of s_axi_awaddr : signal is "xilinx.com:interface:aximm:1.0 s_axi AWADDR";
  attribute X_INTERFACE_MODE of s_axi_awaddr : signal is "slave";
  attribute X_INTERFACE_PARAMETER of s_axi_awaddr : signal is "XIL_INTERFACENAME s_axi, DATA_WIDTH 32, PROTOCOL AXI4LITE, FREQ_HZ 100000000, ID_WIDTH 0, ADDR_WIDTH 6, AWUSER_WIDTH 0, ARUSER_WIDTH 0, WUSER_WIDTH 0, RUSER_WIDTH 0, BUSER_WIDTH 0, READ_WRITE_MODE READ_WRITE, HAS_BURST 0, HAS_LOCK 0, HAS_PROT 1, HAS_CACHE 0, HAS_QOS 0, HAS_REGION 0, HAS_WSTRB 1, HAS_BRESP 1, HAS_RRESP 1, SUPPORTS_NARROW_BURST 0, NUM_READ_OUTSTANDING 1, NUM_WRITE_OUTSTANDING 1, MAX_BURST_LENGTH 1, PHASE 0.0, CLK_DOMAIN design_1_processing_system7_0_0_FCLK_CLK0, NUM_READ_THREADS 1, NUM_WRITE_THREADS 1, RUSER_BITS_PER_BYTE 0, WUSER_BITS_PER_BYTE 0, INSERT_VIP 0";
  attribute X_INTERFACE_INFO of s_axi_awprot : signal is "xilinx.com:interface:aximm:1.0 s_axi AWPROT";
  attribute X_INTERFACE_INFO of s_axi_bresp : signal is "xilinx.com:interface:aximm:1.0 s_axi BRESP";
  attribute X_INTERFACE_INFO of s_axi_rdata : signal is "xilinx.com:interface:aximm:1.0 s_axi RDATA";
  attribute X_INTERFACE_INFO of s_axi_rresp : signal is "xilinx.com:interface:aximm:1.0 s_axi RRESP";
  attribute X_INTERFACE_INFO of s_axi_wdata : signal is "xilinx.com:interface:aximm:1.0 s_axi WDATA";
  attribute X_INTERFACE_INFO of s_axi_wstrb : signal is "xilinx.com:interface:aximm:1.0 s_axi WSTRB";
begin
  neuron_config_addr(9 downto 0) <= \^router_config_addr\(9 downto 0);
  neuron_config_wdata(31 downto 0) <= \^router_config_wdata\(31 downto 0);
  router_config_addr(31 downto 0) <= \^router_config_addr\(31 downto 0);
  router_config_wdata(31 downto 0) <= \^router_config_wdata\(31 downto 0);
  s_axi_bresp(1) <= \<const0>\;
  s_axi_bresp(0) <= \<const0>\;
  s_axi_rresp(1) <= \<const0>\;
  s_axi_rresp(0) <= \<const0>\;
GND: unisim.vcomponents.GND
     port map (
      G => \<const0>\
    );
inst: entity work.design_1_snn_config_regs_0_0_snn_config_regs
     port map (
      active_neurons(7 downto 0) => active_neurons(7 downto 0),
      fifo_overflow => fifo_overflow,
      global_leak_rate(7 downto 0) => global_leak_rate(7 downto 0),
      global_refrac_period(7 downto 0) => global_refrac_period(7 downto 0),
      global_threshold(15 downto 0) => global_threshold(15 downto 0),
      neuron_config_we => neuron_config_we,
      neuron_spike_count(31 downto 0) => neuron_spike_count(31 downto 0),
      router_config_addr(31 downto 0) => \^router_config_addr\(31 downto 0),
      router_config_rdata(31 downto 0) => router_config_rdata(31 downto 0),
      router_config_wdata(31 downto 0) => \^router_config_wdata\(31 downto 0),
      router_config_we => router_config_we,
      router_spike_count(31 downto 0) => router_spike_count(31 downto 0),
      s_axi_aclk => s_axi_aclk,
      s_axi_araddr(3 downto 0) => s_axi_araddr(5 downto 2),
      s_axi_aresetn => s_axi_aresetn,
      s_axi_arready => s_axi_arready,
      s_axi_arvalid => s_axi_arvalid,
      s_axi_awaddr(3 downto 0) => s_axi_awaddr(5 downto 2),
      s_axi_awready => s_axi_awready,
      s_axi_awvalid => s_axi_awvalid,
      s_axi_bready => s_axi_bready,
      s_axi_bvalid => s_axi_bvalid,
      s_axi_rdata(31 downto 0) => s_axi_rdata(31 downto 0),
      s_axi_rready => s_axi_rready,
      s_axi_rvalid => s_axi_rvalid,
      s_axi_wdata(31 downto 0) => s_axi_wdata(31 downto 0),
      s_axi_wready => s_axi_wready,
      s_axi_wstrb(3 downto 0) => s_axi_wstrb(3 downto 0),
      s_axi_wvalid => s_axi_wvalid,
      service_cycles_counter(31 downto 0) => service_cycles_counter(31 downto 0),
      throughput_counter(31 downto 0) => throughput_counter(31 downto 0)
    );
end STRUCTURE;
