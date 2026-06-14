#!/usr/bin/env tclsh
#===============================================================================
# update_hls_ip.tcl - Update HLS IP in existing Vivado project (CLI)
#
# Usage:
#   vivado -mode batch -source update_hls_ip.tcl
#   or
#   vivado -mode tcl -source update_hls_ip.tcl  # for interactive debugging
#
# This script:
#   1. Opens existing Vivado project
#   2. Adds new HLS IP repository
#   3. Upgrades IP in block design
#   4. Reconnects any new ports (s_axis_data, etc.)
#   5. Validates design
#   6. Optionally runs synthesis/implementation
#===============================================================================

# Project paths
set hls_ip_repo "../hls/hls_output/hls/impl/ip"
set bd_name "design_1"

# Current SpikeMold-EDNP build output.
set project_candidates [list \
    "../build/spikemold_ednp_pynq_z2/spikemold_ednp_pynq_z2.xpr" \
]

set proj_xpr ""
foreach cand $project_candidates {
    if {[file exists $cand]} {
        set proj_xpr $cand
        break
    }
}

if {$proj_xpr eq ""} {
    puts "ERROR: No Vivado project (.xpr) found in expected locations:"
    foreach cand $project_candidates {
        puts "  - $cand"
    }
    exit 1
}

set proj_dir [file dirname $proj_xpr]
set proj_name [file rootname [file tail $proj_xpr]]

# Open existing project
puts "Opening project: ${proj_xpr}"
open_project ${proj_xpr}

# Add HLS IP repository
puts "Adding HLS IP repository: ${hls_ip_repo}"
set_property ip_repo_paths [concat [get_property ip_repo_paths [current_project]] ${hls_ip_repo}] [current_project]
update_ip_catalog -rebuild

# Open block design
puts "Opening block design: ${bd_name}"
set bd_path "${proj_dir}/${proj_name}.srcs/sources_1/bd/${bd_name}/${bd_name}.bd"
if {![file exists $bd_path]} {
    puts "ERROR: Block design not found: ${bd_path}"
    exit 1
}
open_bd_design ${bd_path}

# Report current IP versions
puts "\n=== Current IP versions in design ==="
set bd_cells [get_bd_cells]
if {[llength $bd_cells] > 0} {
    foreach cell $bd_cells {
        puts "  - $cell ([get_property VLNV $cell])"
    }
} else {
    puts "No BD cells found in ${bd_name}."
}

# Upgrade IP cores (interactive prompt disabled in batch mode)
puts "\n=== Upgrading IP cores ==="
set ip_to_upgrade [get_ips -filter {UPGRADE_VERSIONS != ""}]
if {[llength $ip_to_upgrade] > 0} {
    puts "Found IP to upgrade:"
    foreach ip $ip_to_upgrade {
        puts "  - [get_property NAME $ip] (current: [get_property VERSION $ip])"
    }
    upgrade_ip [get_ips]
} else {
    puts "No IP upgrades available."
}

# Find spikemold_top_hls instance in BD
set spikemold_hls_cell [get_bd_cells -quiet -filter {VLNV =~ "*spikemold_top_hls*"}]
if {$spikemold_hls_cell != ""} {
    puts "\n=== Found HLS IP instance: $spikemold_hls_cell ==="
    
    # Check for unconnected pins (new ports added in HLS)
    set unconnected_pins [get_bd_pins -quiet -of_objects $spikemold_hls_cell -filter {TYPE == slave && DIR == I} -filter {CONNECTED == false}]
    if {[llength $unconnected_pins] > 0} {
        puts "WARNING: Unconnected input pins detected:"
        foreach pin $unconnected_pins {
            puts "  - $pin"
        }
        puts "You may need to manually connect s_axis_data or tie off unused ports."
    }
    
    # Example: Tie off s_axis_data if not used yet
    # Uncomment and adjust if you want to auto-tie-off:
    # set s_axis_data_pin [get_bd_pins -quiet ${spikemold_hls_cell}/s_axis_data_TVALID]
    # if {$s_axis_data_pin != ""} {
    #     create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 const_s_axis_data_tvalid
    #     set_property -dict [list CONFIG.CONST_VAL {0}] [get_bd_cells const_s_axis_data_tvalid]
    #     connect_bd_net [get_bd_pins const_s_axis_data_tvalid/dout] [get_bd_pins ${spikemold_hls_cell}/s_axis_data_TVALID]
    # }
    
} else {
    puts "WARNING: No spikemold_top_hls IP found in block design. You may need to manually add it."
}

# Regenerate layout and validate
puts "\n=== Regenerating block design layout ==="
regenerate_bd_layout
validate_bd_design

# Assign addresses (if not already assigned)
puts "\n=== Assigning addresses ==="
assign_bd_address

# Save block design
puts "\n=== Saving block design ==="
save_bd_design

# Report address map
puts "\n=== Address Map ==="
set addr_segs [get_bd_addr_segs -of_objects [get_bd_addr_spaces]]
foreach seg $addr_segs {
    set range [get_property RANGE $seg]
    set offset [get_property OFFSET $seg]
    puts "[format %-40s $seg] OFFSET=$offset RANGE=$range"
}

puts "\n=== IP update completed ==="
puts "Next steps:"
puts "  1. Review address map above and update Python RegisterMap base address"
puts "  2. Check for any unconnected ports and wire them as needed"
puts "  3. Run synthesis: launch_runs synth_1 -jobs 8"
puts "  4. Run implementation: launch_runs impl_1 -to_step write_bitstream -jobs 8"
puts "  5. Export hardware: write_hw_platform -fixed -include_bit -file design_1_wrapper.xsa"

# Optionally auto-run synthesis (uncomment if desired)
# puts "\n=== Launching synthesis ==="
# reset_run synth_1
# launch_runs synth_1 -jobs 8
# wait_on_run synth_1

# Close project
close_project
puts "\nDone!"
