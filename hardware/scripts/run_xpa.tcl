# hardware/scripts/run_xpa.tcl
# Xilinx Power Analyzer (XPA) Batch Script for Vivado 2025.2
# Uses SAIF activity file from simulation

set dcp [lindex $argv 0]
set saif [lindex $argv 1]
set out_dir [lindex $argv 2]

puts "--- Loading Checkpoint: $dcp ---"
open_checkpoint $dcp

puts "--- Reading SAIF: $saif ---"
# Map testbench hierarchy to implemented hierarchy
# Testbench path: tb_spikemold_power_sweep/router_inst -> Cell: u_spike_router
# Testbench path: tb_spikemold_power_sweep/neuron_array_inst -> Cell: u_neuron_array

read_saif -strip_path tb_spikemold_power_sweep -out_file "${out_dir}/saif_match.txt" $saif

puts "--- Reporting Power ---"
report_power -file "${out_dir}/integrated_power_final.rpt" -hier all -xpe "${out_dir}/integrated_power_final.xpe"

puts "--- XPA Analysis Complete ---"
quit
