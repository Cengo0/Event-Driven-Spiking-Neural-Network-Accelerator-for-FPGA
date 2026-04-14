# hardware/scripts/gen_saif.tcl
open_saif "power_sweep.saif"
log_saif [get_objects -recursive *]
run all
close_saif
exit
