-- Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
-- Copyright 2022-2026 Advanced Micro Devices, Inc. All Rights Reserved.
-- -------------------------------------------------------------------------------
-- This file contains confidential and proprietary information
-- of AMD and is protected under U.S. and international copyright
-- and other intellectual property laws.
--
-- DISCLAIMER
-- This disclaimer is not a license and does not grant any
-- rights to the materials distributed herewith. Except as
-- otherwise provided in a valid license issued to you by
-- AMD, and to the maximum extent permitted by applicable
-- law: (1) THESE MATERIALS ARE MADE AVAILABLE "AS IS" AND
-- WITH ALL FAULTS, AND AMD HEREBY DISCLAIMS ALL WARRANTIES
-- AND CONDITIONS, EXPRESS, IMPLIED, OR STATUTORY, INCLUDING
-- BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, NON-
-- INFRINGEMENT, OR FITNESS FOR ANY PARTICULAR PURPOSE; and
-- (2) AMD shall not be liable (whether in contract or tort,
-- including negligence, or under any other theory of
-- liability) for any loss or damage of any kind or nature
-- related to, arising under or in connection with these
-- materials, including for any direct, or any indirect,
-- special, incidental, or consequential loss or damage
-- (including loss of data, profits, goodwill, or any type of
-- loss or damage suffered as a result of any action brought
-- by a third party) even if such damage or loss was
-- reasonably foreseeable or AMD had been advised of the
-- possibility of the same.
--
-- CRITICAL APPLICATIONS
-- AMD products are not designed or intended to be fail-
-- safe, or for use in any application requiring fail-safe
-- performance, such as life-support or safety devices or
-- systems, Class III medical devices, nuclear facilities,
-- applications related to the deployment of airbags, or any
-- other applications that could lead to death, personal
-- injury, or severe property or environmental damage
-- (individually and collectively, "Critical
-- Applications"). Customer assumes the sole risk and
-- liability of any use of AMD products in Critical
-- Applications, subject only to applicable laws and
-- regulations governing limitations on product liability.
--
-- THIS COPYRIGHT NOTICE AND DISCLAIMER MUST BE RETAINED AS
-- PART OF THIS FILE AT ALL TIMES.
--
-- DO NOT MODIFY THIS FILE.

-- MODULE VLNV: amd.com:blockdesign:design_1:1.0

-- The following code must appear in the VHDL architecture header.

-- COMP_TAG     ------ Begin cut for COMPONENT Declaration ------
COMPONENT design_1
  PORT (
    DDR_cas_n : INOUT STD_LOGIC;
    DDR_cke : INOUT STD_LOGIC;
    DDR_ck_n : INOUT STD_LOGIC;
    DDR_ck_p : INOUT STD_LOGIC;
    DDR_cs_n : INOUT STD_LOGIC;
    DDR_reset_n : INOUT STD_LOGIC;
    DDR_odt : INOUT STD_LOGIC;
    DDR_ras_n : INOUT STD_LOGIC;
    DDR_we_n : INOUT STD_LOGIC;
    DDR_ba : INOUT STD_LOGIC_VECTOR(2 DOWNTO 0);
    DDR_addr : INOUT STD_LOGIC_VECTOR(14 DOWNTO 0);
    DDR_dm : INOUT STD_LOGIC_VECTOR(3 DOWNTO 0);
    DDR_dq : INOUT STD_LOGIC_VECTOR(31 DOWNTO 0);
    DDR_dqs_n : INOUT STD_LOGIC_VECTOR(3 DOWNTO 0);
    DDR_dqs_p : INOUT STD_LOGIC_VECTOR(3 DOWNTO 0);
    FIXED_IO_mio : INOUT STD_LOGIC_VECTOR(53 DOWNTO 0);
    FIXED_IO_ddr_vrn : INOUT STD_LOGIC;
    FIXED_IO_ddr_vrp : INOUT STD_LOGIC;
    FIXED_IO_ps_srstb : INOUT STD_LOGIC;
    FIXED_IO_ps_clk : INOUT STD_LOGIC;
    FIXED_IO_ps_porb : INOUT STD_LOGIC;
    spike_in_valid : OUT STD_LOGIC_VECTOR(0 DOWNTO 0);
    spike_in_neuron_id : OUT STD_LOGIC_VECTOR(10 DOWNTO 0);
    spike_in_weight : OUT STD_LOGIC_VECTOR(7 DOWNTO 0);
    spike_in_ready : IN STD_LOGIC;
    spike_out_valid : IN STD_LOGIC;
    spike_out_neuron_id : IN STD_LOGIC_VECTOR(10 DOWNTO 0);
    spike_out_weight : IN STD_LOGIC_VECTOR(7 DOWNTO 0);
    spike_out_ready : OUT STD_LOGIC_VECTOR(0 DOWNTO 0);
    learn_weight_valid : OUT STD_LOGIC_VECTOR(0 DOWNTO 0);
    learn_weight_group : OUT STD_LOGIC_VECTOR(3 DOWNTO 0);
    learn_weight_src : OUT STD_LOGIC_VECTOR(6 DOWNTO 0);
    learn_weight_dst : OUT STD_LOGIC_VECTOR(6 DOWNTO 0);
    learn_weight_data : OUT STD_LOGIC_VECTOR(7 DOWNTO 0);
    learn_weight_exc : OUT STD_LOGIC_VECTOR(0 DOWNTO 0);
    learn_weight_is_inter : OUT STD_LOGIC_VECTOR(0 DOWNTO 0);
    learn_weight_dst_group : OUT STD_LOGIC_VECTOR(3 DOWNTO 0);
    learn_weight_fanout_idx : OUT STD_LOGIC_VECTOR(3 DOWNTO 0);
    learn_weight_ready : IN STD_LOGIC;
    snn_enable : OUT STD_LOGIC_VECTOR(0 DOWNTO 0);
    snn_reset : OUT STD_LOGIC_VECTOR(0 DOWNTO 0);
    snn_ready : IN STD_LOGIC;
    snn_busy : IN STD_LOGIC;
    threshold_out : OUT STD_LOGIC_VECTOR(15 DOWNTO 0);
    leak_rate_out : OUT STD_LOGIC_VECTOR(15 DOWNTO 0);
    cfg_router_config_we : OUT STD_LOGIC;
    cfg_router_config_addr : OUT STD_LOGIC_VECTOR(31 DOWNTO 0);
    cfg_router_config_wdata : OUT STD_LOGIC_VECTOR(31 DOWNTO 0);
    cfg_router_config_rdata : IN STD_LOGIC_VECTOR(31 DOWNTO 0);
    cfg_neuron_config_we : OUT STD_LOGIC;
    cfg_neuron_config_addr : OUT STD_LOGIC_VECTOR(9 DOWNTO 0);
    cfg_neuron_config_wdata : OUT STD_LOGIC_VECTOR(31 DOWNTO 0);
    cfg_global_threshold : OUT STD_LOGIC_VECTOR(15 DOWNTO 0);
    cfg_global_leak_rate : OUT STD_LOGIC_VECTOR(7 DOWNTO 0);
    cfg_global_refrac_period : OUT STD_LOGIC_VECTOR(7 DOWNTO 0);
    cfg_router_spike_count : IN STD_LOGIC_VECTOR(31 DOWNTO 0);
    cfg_neuron_spike_count : IN STD_LOGIC_VECTOR(31 DOWNTO 0);
    cfg_fifo_overflow : IN STD_LOGIC;
    cfg_active_neurons : IN STD_LOGIC_VECTOR(7 DOWNTO 0);
    cfg_throughput_counter : IN STD_LOGIC_VECTOR(31 DOWNTO 0);
    cfg_service_cycles_counter : IN STD_LOGIC_VECTOR(31 DOWNTO 0);
    clk_100mhz : OUT STD_LOGIC;
    rst_n_sync : OUT STD_LOGIC_VECTOR(0 DOWNTO 0);
    debug_learning_active : OUT STD_LOGIC_VECTOR(0 DOWNTO 0)
  );
END COMPONENT;
-- COMP_TAG_END ------  End cut for COMPONENT Declaration  ------

-- The following code must appear in the VHDL architecture
-- body. Substitute your own instance name and net names.

-- INST_TAG     ------ Begin cut for INSTANTIATION Template ------
your_instance_name : design_1
  PORT MAP (
    DDR_cas_n => DDR_cas_n,
    DDR_cke => DDR_cke,
    DDR_ck_n => DDR_ck_n,
    DDR_ck_p => DDR_ck_p,
    DDR_cs_n => DDR_cs_n,
    DDR_reset_n => DDR_reset_n,
    DDR_odt => DDR_odt,
    DDR_ras_n => DDR_ras_n,
    DDR_we_n => DDR_we_n,
    DDR_ba => DDR_ba,
    DDR_addr => DDR_addr,
    DDR_dm => DDR_dm,
    DDR_dq => DDR_dq,
    DDR_dqs_n => DDR_dqs_n,
    DDR_dqs_p => DDR_dqs_p,
    FIXED_IO_mio => FIXED_IO_mio,
    FIXED_IO_ddr_vrn => FIXED_IO_ddr_vrn,
    FIXED_IO_ddr_vrp => FIXED_IO_ddr_vrp,
    FIXED_IO_ps_srstb => FIXED_IO_ps_srstb,
    FIXED_IO_ps_clk => FIXED_IO_ps_clk,
    FIXED_IO_ps_porb => FIXED_IO_ps_porb,
    spike_in_valid => spike_in_valid,
    spike_in_neuron_id => spike_in_neuron_id,
    spike_in_weight => spike_in_weight,
    spike_in_ready => spike_in_ready,
    spike_out_valid => spike_out_valid,
    spike_out_neuron_id => spike_out_neuron_id,
    spike_out_weight => spike_out_weight,
    spike_out_ready => spike_out_ready,
    learn_weight_valid => learn_weight_valid,
    learn_weight_group => learn_weight_group,
    learn_weight_src => learn_weight_src,
    learn_weight_dst => learn_weight_dst,
    learn_weight_data => learn_weight_data,
    learn_weight_exc => learn_weight_exc,
    learn_weight_is_inter => learn_weight_is_inter,
    learn_weight_dst_group => learn_weight_dst_group,
    learn_weight_fanout_idx => learn_weight_fanout_idx,
    learn_weight_ready => learn_weight_ready,
    snn_enable => snn_enable,
    snn_reset => snn_reset,
    snn_ready => snn_ready,
    snn_busy => snn_busy,
    threshold_out => threshold_out,
    leak_rate_out => leak_rate_out,
    cfg_router_config_we => cfg_router_config_we,
    cfg_router_config_addr => cfg_router_config_addr,
    cfg_router_config_wdata => cfg_router_config_wdata,
    cfg_router_config_rdata => cfg_router_config_rdata,
    cfg_neuron_config_we => cfg_neuron_config_we,
    cfg_neuron_config_addr => cfg_neuron_config_addr,
    cfg_neuron_config_wdata => cfg_neuron_config_wdata,
    cfg_global_threshold => cfg_global_threshold,
    cfg_global_leak_rate => cfg_global_leak_rate,
    cfg_global_refrac_period => cfg_global_refrac_period,
    cfg_router_spike_count => cfg_router_spike_count,
    cfg_neuron_spike_count => cfg_neuron_spike_count,
    cfg_fifo_overflow => cfg_fifo_overflow,
    cfg_active_neurons => cfg_active_neurons,
    cfg_throughput_counter => cfg_throughput_counter,
    cfg_service_cycles_counter => cfg_service_cycles_counter,
    clk_100mhz => clk_100mhz,
    rst_n_sync => rst_n_sync,
    debug_learning_active => debug_learning_active
  );
-- INST_TAG_END ------  End cut for INSTANTIATION Template  ------

-- You must compile the wrapper file design_1.vhd when simulating
-- the module, design_1. When compiling the wrapper file, be sure to
-- reference the VHDL simulation library.
