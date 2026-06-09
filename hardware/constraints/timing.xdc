##-----------------------------------------------------------------------------
## File: timing.xdc
## Author        : Jiwoon Lee (@metr0jw)
## Organization  : Kwangwoon University, Seoul, South Korea
## Contact       : jwlee@linux.com
## Description: Timing constraints for SpikeMold fabric
##
## Note: For the integrated system (snn_fabric_top), all clocks
## come from PS FCLK_CLK0 (80 MHz). The Zynq PS auto-generates the
## clock constraint. No explicit create_clock is needed here.
## This file is for the standalone (non-PS) build only.
##-----------------------------------------------------------------------------

## AXI Clock constraint for standalone builds only.
## In the integrated system, FCLK_CLK0 provides the clock via BD.
## Vivado will ignore this if port 'aclk' does not exist (which is
## the case in snn_fabric_top).
# create_clock -period 12.500 -name axi_clk [get_ports aclk]

## Clock domain crossings (if any)
# set_false_path -from [get_clocks axi_clk] -to [get_clocks sys_clk_pin]
# set_false_path -from [get_clocks sys_clk_pin] -to [get_clocks axi_clk]

## Input/Output delays (example - adjust based on actual requirements)
# set_input_delay -clock [get_clocks axi_clk] -min 1.0 [get_ports s_axi_*]
# set_input_delay -clock [get_clocks axi_clk] -max 3.0 [get_ports s_axi_*]
# set_output_delay -clock [get_clocks axi_clk] -min 1.0 [get_ports m_axi_*]
# set_output_delay -clock [get_clocks axi_clk] -max 3.0 [get_ports m_axi_*]
