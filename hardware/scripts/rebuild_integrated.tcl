#-----------------------------------------------------------------------------
# Rebuild snn_integrated bitstream with RTL fixes
# Edge detector on spike_in_valid + hold register on spike_out
#
# Usage: vivado -mode batch -source hardware/scripts/rebuild_integrated.tcl
#-----------------------------------------------------------------------------

set project_dir "/mnt/workspace/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA"
set build_dir   "${project_dir}/hardware/build/snn_integrated_v2"
set rtl_dir     "${project_dir}/hardware/hdl/rtl"
set ip_repo     "${project_dir}/hardware/ip_repo"
set output_dir  "${project_dir}/outputs"
set part        "xc7z020clg400-1"

# Clean previous build
file delete -force $build_dir

# Create project
create_project snn_integrated_v2 $build_dir -part $part -force
set_property target_language Verilog [current_project]

# Add IP repository (packaged HLS IP)
set_property ip_repo_paths [list "${ip_repo}/snn_top_hls_1_0" "${ip_repo}/snn_top_hls"] [current_project]
update_ip_catalog

# =============================================================================
# Create Block Design
# =============================================================================
create_bd_design "design_1"

# --- Zynq PS ---
create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 processing_system7_0

# Apply PYNQ-Z2 preset
set_property -dict [list \
    CONFIG.PCW_USE_S_AXI_HP0 {1} \
    CONFIG.PCW_USE_FABRIC_INTERRUPT {1} \
    CONFIG.PCW_IRQ_F2P_INTR {1} \
    CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {100} \
    CONFIG.PCW_USE_M_AXI_GP0 {1} \
    CONFIG.PCW_QSPI_PERIPHERAL_ENABLE {1} \
    CONFIG.PCW_ENET0_PERIPHERAL_ENABLE {1} \
    CONFIG.PCW_SD0_PERIPHERAL_ENABLE {1} \
    CONFIG.PCW_UART0_PERIPHERAL_ENABLE {1} \
    CONFIG.PCW_USB0_PERIPHERAL_ENABLE {1} \
    CONFIG.PCW_GPIO_MIO_GPIO_ENABLE {1} \
    CONFIG.PCW_TTC0_PERIPHERAL_ENABLE {0} \
] [get_bd_cells processing_system7_0]

# --- Make DDR and FIXED_IO external (required for Zynq PS) ---
create_bd_intf_port -mode Master -vlnv xilinx.com:interface:ddrx_rtl:1.0 DDR
connect_bd_intf_net [get_bd_intf_pins processing_system7_0/DDR] [get_bd_intf_ports DDR]

create_bd_intf_port -mode Master -vlnv xilinx.com:display_processing_system7:fixedio_rtl:1.0 FIXED_IO
connect_bd_intf_net [get_bd_intf_pins processing_system7_0/FIXED_IO] [get_bd_intf_ports FIXED_IO]

# --- Processor System Reset ---
create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 proc_sys_reset_0

# --- AXI DMA ---
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_dma:7.1 axi_dma_0
set_property -dict [list \
    CONFIG.c_include_sg {0} \
    CONFIG.c_sg_include_stscntrl_strm {0} \
    CONFIG.c_sg_length_width {23} \
    CONFIG.c_mm2s_burst_size {16} \
    CONFIG.c_s2mm_burst_size {16} \
    CONFIG.c_m_axi_mm2s_data_width {32} \
    CONFIG.c_m_axi_s2mm_data_width {32} \
    CONFIG.c_m_axis_mm2s_tdata_width {32} \
    CONFIG.c_s_axis_s2mm_tdata_width {32} \
] [get_bd_cells axi_dma_0]

# --- HLS SNN IP ---
create_bd_cell -type ip -vlnv xilinx.com:hls:snn_top_hls:1.0 snn_top_hls_0

# --- Config Regs (RTL module reference) ---
# Must add source file BEFORE creating module reference
add_files -norecurse ${rtl_dir}/common/snn_config_regs.v
update_compile_order -fileset sources_1
create_bd_cell -type module -reference snn_config_regs snn_config_regs_0

# --- AXI Interconnect for GP0 (3 slaves: HLS, Config, DMA) ---
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_interconnect:2.1 axi_interconnect_0
set_property CONFIG.NUM_MI {3} [get_bd_cells axi_interconnect_0]

# --- AXI Interconnect for HP0 (2 masters: DMA MM2S, DMA S2MM) ---
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_interconnect:2.1 axi_interconnect_hp0
set_property -dict [list CONFIG.NUM_SI {2} CONFIG.NUM_MI {1}] [get_bd_cells axi_interconnect_hp0]

# --- Constants ---
create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_one_1bit
set_property CONFIG.CONST_VAL {1} [get_bd_cells const_one_1bit]

create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_zero_1bit
set_property CONFIG.CONST_VAL {0} [get_bd_cells const_zero_1bit]

create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_zero_32bit
set_property -dict [list CONFIG.CONST_VAL {0} CONFIG.CONST_WIDTH {32}] [get_bd_cells const_zero_32bit]

create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_zero_4bit
set_property -dict [list CONFIG.CONST_VAL {0} CONFIG.CONST_WIDTH {4}] [get_bd_cells const_zero_4bit]

# =============================================================================
# Clock and Reset Connections
# =============================================================================
connect_bd_net [get_bd_pins processing_system7_0/FCLK_CLK0] \
    [get_bd_pins proc_sys_reset_0/slowest_sync_clk] \
    [get_bd_pins axi_dma_0/s_axi_lite_aclk] \
    [get_bd_pins axi_dma_0/m_axi_mm2s_aclk] \
    [get_bd_pins axi_dma_0/m_axi_s2mm_aclk] \
    [get_bd_pins snn_top_hls_0/ap_clk] \
    [get_bd_pins snn_config_regs_0/s_axi_aclk] \
    [get_bd_pins axi_interconnect_0/ACLK] \
    [get_bd_pins axi_interconnect_0/S00_ACLK] \
    [get_bd_pins axi_interconnect_0/M00_ACLK] \
    [get_bd_pins axi_interconnect_0/M01_ACLK] \
    [get_bd_pins axi_interconnect_0/M02_ACLK] \
    [get_bd_pins axi_interconnect_hp0/ACLK] \
    [get_bd_pins axi_interconnect_hp0/S00_ACLK] \
    [get_bd_pins axi_interconnect_hp0/S01_ACLK] \
    [get_bd_pins axi_interconnect_hp0/M00_ACLK] \
    [get_bd_pins processing_system7_0/M_AXI_GP0_ACLK] \
    [get_bd_pins processing_system7_0/S_AXI_HP0_ACLK]

connect_bd_net [get_bd_pins processing_system7_0/FCLK_RESET0_N] \
    [get_bd_pins proc_sys_reset_0/ext_reset_in]

connect_bd_net [get_bd_pins proc_sys_reset_0/peripheral_aresetn] \
    [get_bd_pins snn_top_hls_0/ap_rst_n] \
    [get_bd_pins snn_config_regs_0/s_axi_aresetn] \
    [get_bd_pins axi_dma_0/axi_resetn] \
    [get_bd_pins axi_interconnect_0/ARESETN] \
    [get_bd_pins axi_interconnect_0/S00_ARESETN] \
    [get_bd_pins axi_interconnect_0/M00_ARESETN] \
    [get_bd_pins axi_interconnect_0/M01_ARESETN] \
    [get_bd_pins axi_interconnect_0/M02_ARESETN] \
    [get_bd_pins axi_interconnect_hp0/ARESETN] \
    [get_bd_pins axi_interconnect_hp0/S00_ARESETN] \
    [get_bd_pins axi_interconnect_hp0/S01_ARESETN] \
    [get_bd_pins axi_interconnect_hp0/M00_ARESETN]

# =============================================================================
# AXI GP0 Interconnect (PS → Slaves)
# =============================================================================
connect_bd_intf_net [get_bd_intf_pins processing_system7_0/M_AXI_GP0] \
    [get_bd_intf_pins axi_interconnect_0/S00_AXI]

# M00 → snn_top_hls_0/s_axi_ctrl
connect_bd_intf_net [get_bd_intf_pins axi_interconnect_0/M00_AXI] \
    [get_bd_intf_pins snn_top_hls_0/s_axi_ctrl]

# M01 → snn_config_regs_0/S_AXI
connect_bd_intf_net [get_bd_intf_pins axi_interconnect_0/M01_AXI] \
    [get_bd_intf_pins snn_config_regs_0/S_AXI]

# M02 → axi_dma_0/S_AXI_LITE
connect_bd_intf_net [get_bd_intf_pins axi_interconnect_0/M02_AXI] \
    [get_bd_intf_pins axi_dma_0/S_AXI_LITE]

# =============================================================================
# AXI HP0 Interconnect (DMA → DDR)
# =============================================================================
connect_bd_intf_net [get_bd_intf_pins axi_dma_0/M_AXI_MM2S] \
    [get_bd_intf_pins axi_interconnect_hp0/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins axi_dma_0/M_AXI_S2MM] \
    [get_bd_intf_pins axi_interconnect_hp0/S01_AXI]
connect_bd_intf_net [get_bd_intf_pins axi_interconnect_hp0/M00_AXI] \
    [get_bd_intf_pins processing_system7_0/S_AXI_HP0]

# =============================================================================
# DMA ↔ HLS AXI-Stream Connections
# =============================================================================
# MM2S → HLS s_axis_spikes
connect_bd_intf_net [get_bd_intf_pins axi_dma_0/M_AXIS_MM2S] \
    [get_bd_intf_pins snn_top_hls_0/s_axis_spikes]

# HLS m_axis_spikes → S2MM
connect_bd_intf_net [get_bd_intf_pins snn_top_hls_0/m_axis_spikes] \
    [get_bd_intf_pins axi_dma_0/S_AXIS_S2MM]

# Tie off unused AXI-Stream ports (s_axis_data, s_axis_weights, m_axis_weights)
# These need TVALID=0 for inputs
# s_axis_data
connect_bd_net [get_bd_pins const_zero_32bit/dout] [get_bd_pins snn_top_hls_0/s_axis_data_TDATA]
connect_bd_net [get_bd_pins const_zero_1bit/dout]  [get_bd_pins snn_top_hls_0/s_axis_data_TVALID]
connect_bd_net [get_bd_pins const_zero_4bit/dout]  [get_bd_pins snn_top_hls_0/s_axis_data_TKEEP]
connect_bd_net [get_bd_pins const_zero_4bit/dout]  [get_bd_pins snn_top_hls_0/s_axis_data_TSTRB]
connect_bd_net [get_bd_pins const_zero_1bit/dout]  [get_bd_pins snn_top_hls_0/s_axis_data_TLAST]
connect_bd_net [get_bd_pins const_zero_1bit/dout]  [get_bd_pins snn_top_hls_0/s_axis_data_TID]
connect_bd_net [get_bd_pins const_zero_1bit/dout]  [get_bd_pins snn_top_hls_0/s_axis_data_TDEST]
connect_bd_net [get_bd_pins const_zero_1bit/dout]  [get_bd_pins snn_top_hls_0/s_axis_data_TUSER]

# s_axis_weights
connect_bd_net [get_bd_pins const_zero_32bit/dout] [get_bd_pins snn_top_hls_0/s_axis_weights_TDATA]
connect_bd_net [get_bd_pins const_zero_1bit/dout]  [get_bd_pins snn_top_hls_0/s_axis_weights_TVALID]
connect_bd_net [get_bd_pins const_zero_4bit/dout]  [get_bd_pins snn_top_hls_0/s_axis_weights_TKEEP]
connect_bd_net [get_bd_pins const_zero_4bit/dout]  [get_bd_pins snn_top_hls_0/s_axis_weights_TSTRB]
connect_bd_net [get_bd_pins const_zero_1bit/dout]  [get_bd_pins snn_top_hls_0/s_axis_weights_TLAST]
connect_bd_net [get_bd_pins const_zero_1bit/dout]  [get_bd_pins snn_top_hls_0/s_axis_weights_TID]
connect_bd_net [get_bd_pins const_zero_1bit/dout]  [get_bd_pins snn_top_hls_0/s_axis_weights_TDEST]
connect_bd_net [get_bd_pins const_zero_1bit/dout]  [get_bd_pins snn_top_hls_0/s_axis_weights_TUSER]

# m_axis_weights: tie TREADY=1
connect_bd_net [get_bd_pins const_one_1bit/dout] [get_bd_pins snn_top_hls_0/m_axis_weights_TREADY]

# Reward signal is s_axilite register (not standalone port), no tie-off needed

# =============================================================================
# HLS ↔ RTL External Ports  (connected in snn_integrated_top.v wrapper)
# =============================================================================
# Make these external so the top wrapper can connect them

# HLS → RTL: spike output to router
create_bd_port -dir O spike_in_valid -type data
create_bd_port -dir O -from 9 -to 0 spike_in_neuron_id -type data
create_bd_port -dir O -from 7 -to 0 spike_in_weight -type data
create_bd_port -dir I spike_in_ready -type data

connect_bd_net [get_bd_pins snn_top_hls_0/spike_in_valid]       [get_bd_ports spike_in_valid]
connect_bd_net [get_bd_pins snn_top_hls_0/spike_in_neuron_id]   [get_bd_ports spike_in_neuron_id]
connect_bd_net [get_bd_pins snn_top_hls_0/spike_in_weight]      [get_bd_ports spike_in_weight]
connect_bd_net [get_bd_ports spike_in_ready]                     [get_bd_pins snn_top_hls_0/spike_in_ready]

# RTL → HLS: spike from neurons
create_bd_port -dir I spike_out_valid -type data
create_bd_port -dir I -from 9 -to 0 spike_out_neuron_id -type data
create_bd_port -dir I -from 7 -to 0 spike_out_weight -type data
create_bd_port -dir O spike_out_ready -type data

connect_bd_net [get_bd_ports spike_out_valid]                    [get_bd_pins snn_top_hls_0/spike_out_valid]
connect_bd_net [get_bd_ports spike_out_neuron_id]               [get_bd_pins snn_top_hls_0/spike_out_neuron_id]
connect_bd_net [get_bd_ports spike_out_weight]                   [get_bd_pins snn_top_hls_0/spike_out_weight]
connect_bd_net [get_bd_pins snn_top_hls_0/spike_out_ready]      [get_bd_ports spike_out_ready]

# SNN Control
create_bd_port -dir O snn_enable -type data
create_bd_port -dir O snn_reset -type data
create_bd_port -dir I snn_ready -type data
create_bd_port -dir I snn_busy -type data
create_bd_port -dir O -from 15 -to 0 threshold_out -type data
create_bd_port -dir O -from 15 -to 0 leak_rate_out -type data

connect_bd_net [get_bd_pins snn_top_hls_0/snn_enable]           [get_bd_ports snn_enable]
connect_bd_net [get_bd_pins snn_top_hls_0/snn_reset]            [get_bd_ports snn_reset]
connect_bd_net [get_bd_ports snn_ready]                          [get_bd_pins snn_top_hls_0/snn_ready]
connect_bd_net [get_bd_ports snn_busy]                           [get_bd_pins snn_top_hls_0/snn_busy]
connect_bd_net [get_bd_pins snn_top_hls_0/threshold_out]        [get_bd_ports threshold_out]
connect_bd_net [get_bd_pins snn_top_hls_0/leak_rate_out]        [get_bd_ports leak_rate_out]

# Config regs ↔ External ports for router/neuron config
create_bd_port -dir O cfg_router_config_we -type data
create_bd_port -dir O -from 31 -to 0 cfg_router_config_addr -type data
create_bd_port -dir O -from 31 -to 0 cfg_router_config_wdata -type data
create_bd_port -dir I -from 31 -to 0 cfg_router_config_rdata -type data
create_bd_port -dir O cfg_neuron_config_we -type data
create_bd_port -dir O -from 9 -to 0 cfg_neuron_config_addr -type data
create_bd_port -dir O -from 31 -to 0 cfg_neuron_config_wdata -type data
create_bd_port -dir O -from 15 -to 0 cfg_global_threshold -type data
create_bd_port -dir O -from 7 -to 0 cfg_global_leak_rate -type data
create_bd_port -dir O -from 7 -to 0 cfg_global_refrac_period -type data
create_bd_port -dir I -from 31 -to 0 cfg_router_spike_count -type data
create_bd_port -dir I -from 31 -to 0 cfg_neuron_spike_count -type data
create_bd_port -dir I cfg_fifo_overflow -type data
create_bd_port -dir I -from 7 -to 0 cfg_active_neurons -type data
create_bd_port -dir I -from 31 -to 0 cfg_throughput_counter -type data

# Connect config regs to external ports
connect_bd_net [get_bd_pins snn_config_regs_0/router_config_we]     [get_bd_ports cfg_router_config_we]
connect_bd_net [get_bd_pins snn_config_regs_0/router_config_addr]   [get_bd_ports cfg_router_config_addr]
connect_bd_net [get_bd_pins snn_config_regs_0/router_config_wdata]  [get_bd_ports cfg_router_config_wdata]
connect_bd_net [get_bd_ports cfg_router_config_rdata]                [get_bd_pins snn_config_regs_0/router_config_rdata]
connect_bd_net [get_bd_pins snn_config_regs_0/neuron_config_we]     [get_bd_ports cfg_neuron_config_we]
connect_bd_net [get_bd_pins snn_config_regs_0/neuron_config_addr]   [get_bd_ports cfg_neuron_config_addr]
connect_bd_net [get_bd_pins snn_config_regs_0/neuron_config_wdata]  [get_bd_ports cfg_neuron_config_wdata]
connect_bd_net [get_bd_pins snn_config_regs_0/global_threshold]     [get_bd_ports cfg_global_threshold]
connect_bd_net [get_bd_pins snn_config_regs_0/global_leak_rate]     [get_bd_ports cfg_global_leak_rate]
connect_bd_net [get_bd_pins snn_config_regs_0/global_refrac_period] [get_bd_ports cfg_global_refrac_period]
connect_bd_net [get_bd_ports cfg_router_spike_count]                 [get_bd_pins snn_config_regs_0/router_spike_count]
connect_bd_net [get_bd_ports cfg_neuron_spike_count]                 [get_bd_pins snn_config_regs_0/neuron_spike_count]
connect_bd_net [get_bd_ports cfg_fifo_overflow]                      [get_bd_pins snn_config_regs_0/fifo_overflow]
connect_bd_net [get_bd_ports cfg_active_neurons]                     [get_bd_pins snn_config_regs_0/active_neurons]
connect_bd_net [get_bd_ports cfg_throughput_counter]                  [get_bd_pins snn_config_regs_0/throughput_counter]

# Clock/reset external ports
create_bd_port -dir O clk_100mhz -type clk
create_bd_port -dir O rst_n_sync -type rst
create_bd_port -dir O debug_learning_active -type data

connect_bd_net [get_bd_pins processing_system7_0/FCLK_CLK0] [get_bd_ports clk_100mhz]
connect_bd_net [get_bd_pins proc_sys_reset_0/peripheral_aresetn] [get_bd_ports rst_n_sync]
connect_bd_net [get_bd_pins const_zero_1bit/dout] [get_bd_ports debug_learning_active]

# HLS threshold/leak connected via snn_integrated_top.v wrapper, not via config_regs
# (config_regs doesn't have hls_snn_enable/hls_threshold/hls_leak_rate ports)

# Interrupt
connect_bd_net [get_bd_pins axi_dma_0/mm2s_introut] [get_bd_pins processing_system7_0/IRQ_F2P]

# =============================================================================
# Address Map
# =============================================================================
assign_bd_address

# Set specific addresses to match original design
# Use catch to handle address segment name variations
foreach seg [get_bd_addr_segs -of_objects [get_bd_addr_spaces processing_system7_0/Data]] {
    set seg_name [get_property NAME $seg]
    puts "Found address segment: $seg_name"
    
    if {[string match "*snn_top_hls*" $seg_name]} {
        set_property offset 0x43C00000 $seg
        set_property range 128 $seg
        puts "  -> HLS at 0x43C00000"
    } elseif {[string match "*config_regs*" $seg_name]} {
        set_property offset 0x43C10000 $seg
        set_property range 4K $seg
        puts "  -> Config at 0x43C10000"
    } elseif {[string match "*dma*" $seg_name]} {
        set_property offset 0x41E00000 $seg
        set_property range 64K $seg
        puts "  -> DMA at 0x41E00000"
    }
}

# =============================================================================
# Validate and Save Block Design
# =============================================================================
validate_bd_design
save_bd_design

# Generate BD wrapper
make_wrapper -files [get_files ${build_dir}/snn_integrated_v2.srcs/sources_1/bd/design_1/design_1.bd] -top
add_files -norecurse ${build_dir}/snn_integrated_v2.gen/sources_1/bd/design_1/hdl/design_1_wrapper.v

# =============================================================================
# Add RTL Sources (spike_router, lif_neuron_array, snn_integrated_top with fixes)
# =============================================================================
add_files -norecurse ${rtl_dir}/router/spike_router.v
add_files -norecurse ${rtl_dir}/neurons/lif_neuron_array.v
add_files -norecurse ${rtl_dir}/common/fifo.v
add_files -norecurse ${rtl_dir}/top/snn_integrated_top.v

# Set snn_integrated_top as the real top module
set_property top snn_integrated_top [current_fileset]

# Add PYNQ-Z2 constraints
if {[file exists ${project_dir}/hardware/constraints/pynq_z2.xdc]} {
    add_files -fileset constrs_1 -norecurse ${project_dir}/hardware/constraints/pynq_z2.xdc
}

# =============================================================================
# Synthesis
# =============================================================================
puts "===== Starting Synthesis ====="
launch_runs synth_1 -jobs 4
wait_on_run synth_1

if {[get_property PROGRESS [get_runs synth_1]] != "100%"} {
    puts "ERROR: Synthesis failed!"
    exit 1
}
puts "===== Synthesis Complete ====="

# =============================================================================
# Implementation (Place & Route)
# =============================================================================
puts "===== Starting Implementation ====="
launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1

if {[get_property PROGRESS [get_runs impl_1]] != "100%"} {
    puts "ERROR: Implementation failed!"
    exit 1
}
puts "===== Implementation Complete ====="

# =============================================================================
# Copy Outputs
# =============================================================================
set bit_file [glob -nocomplain ${build_dir}/snn_integrated_v2.runs/impl_1/*.bit]
set hwh_file [glob -nocomplain ${build_dir}/snn_integrated_v2.gen/sources_1/bd/design_1/hw_handoff/*.hwh]

if {$bit_file ne ""} {
    file copy -force $bit_file ${output_dir}/snn_integrated_v2.bit
    puts "Bitstream: ${output_dir}/snn_integrated_v2.bit"
}
if {$hwh_file ne ""} {
    file copy -force $hwh_file ${output_dir}/snn_integrated_v2.hwh
    puts "HWH: ${output_dir}/snn_integrated_v2.hwh"
}

# Reports
report_utilization -file ${output_dir}/snn_integrated_v2_utilization.rpt
report_timing_summary -file ${output_dir}/snn_integrated_v2_timing.rpt
report_power -file ${output_dir}/snn_integrated_v2_power.rpt

puts "===== ALL DONE ====="
