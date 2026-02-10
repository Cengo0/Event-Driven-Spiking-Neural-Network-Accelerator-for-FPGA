##-----------------------------------------------------------------------------
## Title         : Build Integrated SNN System (HLS + Verilog RTL)
## Project       : PYNQ-Z2 SNN Accelerator
## File          : build_integrated_system.tcl
## Author        : Jiwoon Lee (@metr0jw)
## Organization  : Kwangwoon University, Seoul, South Korea
## Contact       : jwlee@linux.com
## Description   : Creates Block Design with exported ports for RTL integration
##                 Includes AXI-Lite config slave for runtime RTL configuration,
##                 S2MM DMA for output spike streaming, and full monitoring.
##-----------------------------------------------------------------------------

set script_dir [file dirname [file normalize [info script]]]
set proj_root [file normalize "$script_dir/../.."]
set build_dir "$proj_root/build/vivado_integrated"
set proj_name "snn_integrated"

# Create project
puts "Step 1: Creating Vivado project..."
create_project $proj_name $build_dir -part xc7z020clg400-1 -force
# Note: PYNQ-Z2 board files not installed, using part only

# Add IP repository (HLS IP)
puts "Step 2: Adding IP repositories..."
set_property ip_repo_paths [list \
    "$proj_root/hardware/ip_repo" \
] [current_project]
update_ip_catalog
puts "  Added IP repository: $proj_root/hardware/ip_repo"

#==============================================================================
# Step 3: Add Verilog RTL sources
#==============================================================================
puts "Step 3: Adding Verilog RTL sources..."
set hdl_dir "$proj_root/hardware/hdl/rtl"

# Add files by category
foreach dir {common neurons synapses router layers top} {
    set files [glob -nocomplain $hdl_dir/$dir/*.v]
    if {[llength $files] > 0} {
        add_files -norecurse $files
        puts "  Added [llength $files] files from $dir/"
    }
}

# Set top module to the integrated wrapper
set_property top snn_integrated_top [current_fileset]
update_compile_order -fileset sources_1

#==============================================================================
# Step 4: Create Block Design (with exported ports)
#==============================================================================
puts "Step 4: Creating Block Design with exported interfaces..."

create_bd_design "design_1"

# Create Processing System
puts "  Creating Zynq PS..."
create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 processing_system7_0

# Apply PS configuration
apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 \
    -config {make_external "FIXED_IO, DDR" apply_board_preset "1" Master "Disable" Slave "Disable"} \
    [get_bd_cells processing_system7_0]

# Enable HP0 and GP0
set_property -dict [list \
    CONFIG.PCW_USE_S_AXI_HP0 {1} \
    CONFIG.PCW_S_AXI_HP0_DATA_WIDTH {64} \
    CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ {100} \
] [get_bd_cells processing_system7_0]

# Create HLS IP
puts "  Creating HLS learning engine..."
create_bd_cell -type ip -vlnv xilinx.com:hls:snn_top_hls:1.0 snn_top_hls_0

# Create AXI DMA for spike streaming (MM2S + S2MM for bidirectional)
puts "  Creating AXI DMA (bidirectional)..."
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_dma:7.1 axi_dma_0
set_property -dict [list \
    CONFIG.c_include_sg {0} \
    CONFIG.c_sg_include_stscntrl_strm {0} \
    CONFIG.c_include_mm2s {1} \
    CONFIG.c_include_s2mm {1} \
    CONFIG.c_m_axi_mm2s_data_width {64} \
    CONFIG.c_m_axis_mm2s_tdata_width {32} \
    CONFIG.c_mm2s_burst_size {16} \
    CONFIG.c_m_axi_s2mm_data_width {64} \
    CONFIG.c_s_axis_s2mm_tdata_width {32} \
    CONFIG.c_s2mm_burst_size {16} \
] [get_bd_cells axi_dma_0]

# Create AXI Interconnect (GP0 → 3 masters: HLS + DMA + Config)
puts "  Creating AXI interconnects..."
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_interconnect:2.1 axi_interconnect_0
set_property -dict [list CONFIG.NUM_MI {3}] [get_bd_cells axi_interconnect_0]

# HP0 interconnect (2 slaves: DMA MM2S + DMA S2MM)
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_interconnect:2.1 axi_interconnect_hp0
set_property -dict [list \
    CONFIG.NUM_SI {2} \
    CONFIG.NUM_MI {1} \
] [get_bd_cells axi_interconnect_hp0]

# Create RTL Config Register Module Reference (AXI-Lite slave)
puts "  Creating SNN Config Registers (AXI-Lite slave)..."
create_bd_cell -type module -reference snn_config_regs snn_config_regs_0

# Reset management
puts "  Creating reset controller..."
create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 proc_sys_reset_0

#==============================================================================
# Step 5: Make External Ports (for RTL integration)
#==============================================================================
puts "Step 5: Creating external ports for RTL integration..."

# Clock and reset outputs (for RTL wrapper)
create_bd_port -dir O -type clk clk_100mhz
set_property CONFIG.FREQ_HZ 100000000 [get_bd_ports clk_100mhz]

create_bd_port -dir O -type rst rst_n_sync
set_property CONFIG.POLARITY ACTIVE_LOW [get_bd_ports rst_n_sync]

# Debug output (interrupt from HLS)
create_bd_port -dir O debug_learning_active

#------------------------------------------------------------------------------
# HLS → RTL Interface (Spikes from HLS to RTL neurons)
#------------------------------------------------------------------------------
create_bd_port -dir O hls_spike_out_valid
create_bd_port -dir O -from 7 -to 0 hls_spike_out_neuron_id
create_bd_port -dir O -from 7 -to 0 hls_spike_out_weight
create_bd_port -dir I rtl_spike_in_ready

#------------------------------------------------------------------------------
# RTL → HLS Interface (Spikes from RTL neurons to HLS for learning)
#------------------------------------------------------------------------------
create_bd_port -dir I rtl_spike_out_valid
create_bd_port -dir I -from 7 -to 0 rtl_spike_out_neuron_id
create_bd_port -dir I -from 7 -to 0 rtl_spike_out_weight
create_bd_port -dir O hls_spike_in_ready

#------------------------------------------------------------------------------
# SNN Control Interface
#------------------------------------------------------------------------------
create_bd_port -dir O hls_snn_enable
create_bd_port -dir O hls_snn_reset
create_bd_port -dir I rtl_snn_ready
create_bd_port -dir I rtl_snn_busy

#------------------------------------------------------------------------------
# HLS Neuron Parameter Outputs (from config_reg via AXI-Lite)
#------------------------------------------------------------------------------
create_bd_port -dir O -from 15 -to 0 hls_threshold_out
create_bd_port -dir O -from 15 -to 0 hls_leak_rate_out

#------------------------------------------------------------------------------
# Config Register Interface (from snn_config_regs AXI-Lite slave)
#------------------------------------------------------------------------------
# Router config
create_bd_port -dir O cfg_router_config_we
create_bd_port -dir O -from 31 -to 0 cfg_router_config_addr
create_bd_port -dir O -from 31 -to 0 cfg_router_config_wdata
create_bd_port -dir I -from 31 -to 0 cfg_router_config_rdata

# Neuron config
create_bd_port -dir O cfg_neuron_config_we
create_bd_port -dir O -from 9 -to 0 cfg_neuron_config_addr
create_bd_port -dir O -from 31 -to 0 cfg_neuron_config_wdata

# Global parameters
create_bd_port -dir O -from 15 -to 0 cfg_global_threshold
create_bd_port -dir O -from 7 -to 0 cfg_global_leak_rate
create_bd_port -dir O -from 7 -to 0 cfg_global_refrac_period

# Status inputs
create_bd_port -dir I -from 31 -to 0 cfg_router_spike_count
create_bd_port -dir I -from 31 -to 0 cfg_neuron_spike_count
create_bd_port -dir I cfg_fifo_overflow
create_bd_port -dir I -from 7 -to 0 cfg_active_neurons
create_bd_port -dir I -from 31 -to 0 cfg_throughput_counter

puts "  Created HLS <-> RTL spike interface ports"
puts "  Created config register interface ports"
puts "  Created HLS threshold/leak_rate monitor ports"

#==============================================================================
# Step 6: Connect Block Design
#==============================================================================
puts "Step 6: Connecting Block Design..."

# Connect clocks
connect_bd_net [get_bd_pins processing_system7_0/FCLK_CLK0] \
    [get_bd_pins processing_system7_0/M_AXI_GP0_ACLK] \
    [get_bd_pins processing_system7_0/S_AXI_HP0_ACLK] \
    [get_bd_pins snn_top_hls_0/ap_clk] \
    [get_bd_pins axi_dma_0/s_axi_lite_aclk] \
    [get_bd_pins axi_dma_0/m_axi_mm2s_aclk] \
    [get_bd_pins axi_dma_0/m_axi_s2mm_aclk] \
    [get_bd_pins axi_interconnect_0/ACLK] \
    [get_bd_pins axi_interconnect_0/S00_ACLK] \
    [get_bd_pins axi_interconnect_0/M00_ACLK] \
    [get_bd_pins axi_interconnect_0/M01_ACLK] \
    [get_bd_pins axi_interconnect_0/M02_ACLK] \
    [get_bd_pins axi_interconnect_hp0/ACLK] \
    [get_bd_pins axi_interconnect_hp0/S00_ACLK] \
    [get_bd_pins axi_interconnect_hp0/S01_ACLK] \
    [get_bd_pins axi_interconnect_hp0/M00_ACLK] \
    [get_bd_pins snn_config_regs_0/s_axi_aclk] \
    [get_bd_pins proc_sys_reset_0/slowest_sync_clk] \
    [get_bd_ports clk_100mhz]

# Connect resets
connect_bd_net [get_bd_pins processing_system7_0/FCLK_RESET0_N] \
    [get_bd_pins proc_sys_reset_0/ext_reset_in]
    
connect_bd_net [get_bd_pins proc_sys_reset_0/peripheral_aresetn] \
    [get_bd_pins snn_top_hls_0/ap_rst_n] \
    [get_bd_pins axi_dma_0/axi_resetn] \
    [get_bd_pins axi_interconnect_0/ARESETN] \
    [get_bd_pins axi_interconnect_0/S00_ARESETN] \
    [get_bd_pins axi_interconnect_0/M00_ARESETN] \
    [get_bd_pins axi_interconnect_0/M01_ARESETN] \
    [get_bd_pins axi_interconnect_0/M02_ARESETN] \
    [get_bd_pins axi_interconnect_hp0/ARESETN] \
    [get_bd_pins axi_interconnect_hp0/S00_ARESETN] \
    [get_bd_pins axi_interconnect_hp0/S01_ARESETN] \
    [get_bd_pins axi_interconnect_hp0/M00_ARESETN] \
    [get_bd_pins snn_config_regs_0/s_axi_aresetn] \
    [get_bd_ports rst_n_sync]

# Connect AXI interfaces (GP0 → 3 masters)
connect_bd_intf_net [get_bd_intf_pins processing_system7_0/M_AXI_GP0] \
    [get_bd_intf_pins axi_interconnect_0/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins axi_interconnect_0/M00_AXI] \
    [get_bd_intf_pins snn_top_hls_0/s_axi_ctrl]
connect_bd_intf_net [get_bd_intf_pins axi_interconnect_0/M01_AXI] \
    [get_bd_intf_pins axi_dma_0/S_AXI_LITE]
connect_bd_intf_net [get_bd_intf_pins axi_interconnect_0/M02_AXI] \
    [get_bd_intf_pins snn_config_regs_0/s_axi]

# HP0 interconnect (2 slaves: DMA MM2S + DMA S2MM)
connect_bd_intf_net [get_bd_intf_pins axi_dma_0/M_AXI_MM2S] \
    [get_bd_intf_pins axi_interconnect_hp0/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins axi_dma_0/M_AXI_S2MM] \
    [get_bd_intf_pins axi_interconnect_hp0/S01_AXI]
connect_bd_intf_net [get_bd_intf_pins axi_interconnect_hp0/M00_AXI] \
    [get_bd_intf_pins processing_system7_0/S_AXI_HP0]

# Connect AXI-Stream (DMA ↔ HLS bidirectional)
connect_bd_intf_net [get_bd_intf_pins axi_dma_0/M_AXIS_MM2S] \
    [get_bd_intf_pins snn_top_hls_0/s_axis_spikes]
connect_bd_intf_net [get_bd_intf_pins snn_top_hls_0/m_axis_spikes] \
    [get_bd_intf_pins axi_dma_0/S_AXIS_S2MM]

#------------------------------------------------------------------------------
# Tie off unused AXI-Stream interfaces (s_axis_data, s_axis_weights, m_axis_weights)
# These are used for encoder frame loading and weight checkpoint I/O.
# For the initial build, tie off inputs and leave outputs unconnected.
#------------------------------------------------------------------------------
puts "  Tying off unused AXI-Stream interfaces..."

# s_axis_data: Tie TVALID=0 using AXI-Stream constant (no frame data sent)
create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_zero_1bit
set_property -dict [list CONFIG.CONST_VAL {0} CONFIG.CONST_WIDTH {1}] [get_bd_cells const_zero_1bit]
create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_zero_32bit
set_property -dict [list CONFIG.CONST_VAL {0} CONFIG.CONST_WIDTH {32}] [get_bd_cells const_zero_32bit]
create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_zero_4bit
set_property -dict [list CONFIG.CONST_VAL {0} CONFIG.CONST_WIDTH {4}] [get_bd_cells const_zero_4bit]

# Connect s_axis_data individual signals (tie TVALID=0, TDATA=0, TLAST=0, etc.)
connect_bd_net [get_bd_pins const_zero_1bit/dout] [get_bd_pins snn_top_hls_0/s_axis_data_TVALID]
connect_bd_net [get_bd_pins const_zero_32bit/dout] [get_bd_pins snn_top_hls_0/s_axis_data_TDATA]
connect_bd_net [get_bd_pins const_zero_1bit/dout] [get_bd_pins snn_top_hls_0/s_axis_data_TLAST]
connect_bd_net [get_bd_pins const_zero_4bit/dout] [get_bd_pins snn_top_hls_0/s_axis_data_TKEEP]
connect_bd_net [get_bd_pins const_zero_4bit/dout] [get_bd_pins snn_top_hls_0/s_axis_data_TSTRB]
connect_bd_net [get_bd_pins const_zero_1bit/dout] [get_bd_pins snn_top_hls_0/s_axis_data_TUSER]
connect_bd_net [get_bd_pins const_zero_1bit/dout] [get_bd_pins snn_top_hls_0/s_axis_data_TID]
connect_bd_net [get_bd_pins const_zero_1bit/dout] [get_bd_pins snn_top_hls_0/s_axis_data_TDEST]

# Connect s_axis_weights individual signals (tie TVALID=0)
connect_bd_net [get_bd_pins const_zero_1bit/dout] [get_bd_pins snn_top_hls_0/s_axis_weights_TVALID]
connect_bd_net [get_bd_pins const_zero_32bit/dout] [get_bd_pins snn_top_hls_0/s_axis_weights_TDATA]
connect_bd_net [get_bd_pins const_zero_1bit/dout] [get_bd_pins snn_top_hls_0/s_axis_weights_TLAST]
connect_bd_net [get_bd_pins const_zero_4bit/dout] [get_bd_pins snn_top_hls_0/s_axis_weights_TKEEP]
connect_bd_net [get_bd_pins const_zero_4bit/dout] [get_bd_pins snn_top_hls_0/s_axis_weights_TSTRB]
connect_bd_net [get_bd_pins const_zero_1bit/dout] [get_bd_pins snn_top_hls_0/s_axis_weights_TUSER]
connect_bd_net [get_bd_pins const_zero_1bit/dout] [get_bd_pins snn_top_hls_0/s_axis_weights_TID]
connect_bd_net [get_bd_pins const_zero_1bit/dout] [get_bd_pins snn_top_hls_0/s_axis_weights_TDEST]

# Tie TREADY=1 on m_axis_weights output (always accept, data discarded)
create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_one_1bit
set_property -dict [list CONFIG.CONST_VAL {1} CONFIG.CONST_WIDTH {1}] [get_bd_cells const_one_1bit]
connect_bd_net [get_bd_pins const_one_1bit/dout] [get_bd_pins snn_top_hls_0/m_axis_weights_TREADY]

#==============================================================================
# Step 7: Export signals for RTL integration
#==============================================================================
puts "Step 7: Exporting signals for RTL integration..."

# Export interrupt signal as debug
connect_bd_net [get_bd_pins snn_top_hls_0/interrupt] \
    [get_bd_ports debug_learning_active]

#------------------------------------------------------------------------------
# Connect HLS spike output interface (HLS → RTL)
#------------------------------------------------------------------------------
connect_bd_net [get_bd_pins snn_top_hls_0/spike_in_valid] \
    [get_bd_ports hls_spike_out_valid]
connect_bd_net [get_bd_pins snn_top_hls_0/spike_in_neuron_id] \
    [get_bd_ports hls_spike_out_neuron_id]
connect_bd_net [get_bd_pins snn_top_hls_0/spike_in_weight] \
    [get_bd_ports hls_spike_out_weight]
connect_bd_net [get_bd_ports rtl_spike_in_ready] \
    [get_bd_pins snn_top_hls_0/spike_in_ready]

#------------------------------------------------------------------------------
# Connect HLS spike input interface (RTL → HLS for learning)
#------------------------------------------------------------------------------
connect_bd_net [get_bd_ports rtl_spike_out_valid] \
    [get_bd_pins snn_top_hls_0/spike_out_valid]
connect_bd_net [get_bd_ports rtl_spike_out_neuron_id] \
    [get_bd_pins snn_top_hls_0/spike_out_neuron_id]
connect_bd_net [get_bd_ports rtl_spike_out_weight] \
    [get_bd_pins snn_top_hls_0/spike_out_weight]
connect_bd_net [get_bd_pins snn_top_hls_0/spike_out_ready] \
    [get_bd_ports hls_spike_in_ready]

#------------------------------------------------------------------------------
# Connect SNN control interface
#------------------------------------------------------------------------------
connect_bd_net [get_bd_pins snn_top_hls_0/snn_enable] \
    [get_bd_ports hls_snn_enable]
connect_bd_net [get_bd_pins snn_top_hls_0/snn_reset] \
    [get_bd_ports hls_snn_reset]
connect_bd_net [get_bd_ports rtl_snn_ready] \
    [get_bd_pins snn_top_hls_0/snn_ready]
connect_bd_net [get_bd_ports rtl_snn_busy] \
    [get_bd_pins snn_top_hls_0/snn_busy]

#------------------------------------------------------------------------------
# Connect HLS neuron parameter outputs (monitoring)
#------------------------------------------------------------------------------
connect_bd_net [get_bd_pins snn_top_hls_0/threshold_out] \
    [get_bd_ports hls_threshold_out]
connect_bd_net [get_bd_pins snn_top_hls_0/leak_rate_out] \
    [get_bd_ports hls_leak_rate_out]

#------------------------------------------------------------------------------
# Connect Config Register outputs/inputs
#------------------------------------------------------------------------------
# Router config
connect_bd_net [get_bd_pins snn_config_regs_0/router_config_we] \
    [get_bd_ports cfg_router_config_we]
connect_bd_net [get_bd_pins snn_config_regs_0/router_config_addr] \
    [get_bd_ports cfg_router_config_addr]
connect_bd_net [get_bd_pins snn_config_regs_0/router_config_wdata] \
    [get_bd_ports cfg_router_config_wdata]
connect_bd_net [get_bd_ports cfg_router_config_rdata] \
    [get_bd_pins snn_config_regs_0/router_config_rdata]

# Neuron config
connect_bd_net [get_bd_pins snn_config_regs_0/neuron_config_we] \
    [get_bd_ports cfg_neuron_config_we]
connect_bd_net [get_bd_pins snn_config_regs_0/neuron_config_addr] \
    [get_bd_ports cfg_neuron_config_addr]
connect_bd_net [get_bd_pins snn_config_regs_0/neuron_config_wdata] \
    [get_bd_ports cfg_neuron_config_wdata]

# Global parameters
connect_bd_net [get_bd_pins snn_config_regs_0/global_threshold] \
    [get_bd_ports cfg_global_threshold]
connect_bd_net [get_bd_pins snn_config_regs_0/global_leak_rate] \
    [get_bd_ports cfg_global_leak_rate]
connect_bd_net [get_bd_pins snn_config_regs_0/global_refrac_period] \
    [get_bd_ports cfg_global_refrac_period]

# Status inputs
connect_bd_net [get_bd_ports cfg_router_spike_count] \
    [get_bd_pins snn_config_regs_0/router_spike_count]
connect_bd_net [get_bd_ports cfg_neuron_spike_count] \
    [get_bd_pins snn_config_regs_0/neuron_spike_count]
connect_bd_net [get_bd_ports cfg_fifo_overflow] \
    [get_bd_pins snn_config_regs_0/fifo_overflow]
connect_bd_net [get_bd_ports cfg_active_neurons] \
    [get_bd_pins snn_config_regs_0/active_neurons]
connect_bd_net [get_bd_ports cfg_throughput_counter] \
    [get_bd_pins snn_config_regs_0/throughput_counter]

puts "  Connected HLS <-> RTL spike interface"
puts "  Connected config register interface"
puts "  Connected DMA S2MM for output spike streaming"
puts "  Exported HLS threshold/leak_rate monitor outputs"

#==============================================================================
# Step 8: Assign addresses
#==============================================================================
puts "Step 8: Assigning addresses..."
assign_bd_address

# Set HLS IP address (0x43C00000, 128 bytes)
set_property range 128 [get_bd_addr_segs {processing_system7_0/Data/SEG_snn_top_hls_0_Reg}]
set_property offset 0x43C00000 [get_bd_addr_segs {processing_system7_0/Data/SEG_snn_top_hls_0_Reg}]

# Set Config Registers address (0x43C10000, 4K)
set_property range 4K [get_bd_addr_segs {processing_system7_0/Data/SEG_snn_config_regs_0_reg0}]
set_property offset 0x43C10000 [get_bd_addr_segs {processing_system7_0/Data/SEG_snn_config_regs_0_reg0}]

#==============================================================================
# Step 9: Validate and save
#==============================================================================
puts "Step 9: Validating Block Design..."
regenerate_bd_layout
validate_bd_design
save_bd_design

# Create HDL wrapper
puts "Step 10: Creating HDL wrapper..."
make_wrapper -files [get_files $build_dir/$proj_name.srcs/sources_1/bd/design_1/design_1.bd] -top
add_files -norecurse $build_dir/$proj_name.gen/sources_1/bd/design_1/hdl/design_1_wrapper.v

# Update to use integrated top instead
set_property top snn_integrated_top [current_fileset]
update_compile_order -fileset sources_1

#==============================================================================
# Step 11: Run Synthesis
#==============================================================================
puts "Step 11: Running synthesis..."
launch_runs synth_1 -jobs 8
wait_on_run synth_1

if {[get_property PROGRESS [get_runs synth_1]] != "100%"} {
    puts "ERROR: Synthesis failed!"
    exit 1
}

puts "Synthesis complete!"

#==============================================================================
# Step 12: Run Implementation
#==============================================================================
puts "Step 12: Running implementation..."
launch_runs impl_1 -to_step write_bitstream -jobs 8
wait_on_run impl_1

if {[get_property PROGRESS [get_runs impl_1]] != "100%"} {
    puts "ERROR: Implementation failed!"
    exit 1
}

puts "Implementation complete!"

#==============================================================================
# Step 13: Generate reports
#==============================================================================
puts "Step 13: Generating reports..."
open_run impl_1

report_utilization -file $proj_root/outputs/integrated_utilization.rpt
report_timing_summary -file $proj_root/outputs/integrated_timing.rpt
report_power -file $proj_root/outputs/integrated_power.rpt

# Copy outputs (bitstream + hardware handoff for PYNQ)
puts "Step 14: Copying outputs..."
file mkdir $proj_root/outputs

# Copy bitstream
file copy -force \
    $build_dir/$proj_name.runs/impl_1/snn_integrated_top.bit \
    $proj_root/outputs/snn_integrated.bit

# Copy hardware handoff file (.hwh) — required for PYNQ overlay
set hwh_src "$build_dir/$proj_name.gen/sources_1/bd/design_1/hw_handoff/design_1.hwh"
if {[file exists $hwh_src]} {
    file copy -force $hwh_src $proj_root/outputs/snn_integrated.hwh
    puts "  Copied .hwh file for PYNQ overlay"
} else {
    set hwh_alt "$build_dir/$proj_name.srcs/sources_1/bd/design_1/hw_handoff/design_1.hwh"
    if {[file exists $hwh_alt]} {
        file copy -force $hwh_alt $proj_root/outputs/snn_integrated.hwh
        puts "  Copied .hwh file from alternative location"
    } else {
        puts "WARNING: .hwh file not found — PYNQ overlay will not load without it"
    }
}

puts "===================================================================="
puts "BUILD COMPLETE: Integrated SNN System (HLS + Verilog RTL)"
puts "===================================================================="
puts "Bitstream:    outputs/snn_integrated.bit"
puts "HW Handoff:   outputs/snn_integrated.hwh"
puts "Reports:      outputs/integrated_*.rpt"
puts ""
puts "Address Map:"
puts "  HLS IP (s_axi_ctrl):     0x43C00000 (128 bytes)"
puts "  SNN Config (s_axi):      0x43C10000 (4K)"
puts "  AXI DMA (S_AXI_LITE):    auto-assigned"
puts "===================================================================="
