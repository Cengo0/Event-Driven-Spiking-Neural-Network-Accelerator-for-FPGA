# This script segment is generated automatically by AutoPilot

# clear list
if {${::AESL::PGuard_autoexp_gen}} {
    cg_default_interface_gen_dc_begin
    cg_default_interface_gen_bundle_begin
    AESL_LIB_XILADAPTER::native_axis_begin
}

# XIL_BRAM:
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc ::AESL_LIB_XILADAPTER::xil_bram_gen] == "::AESL_LIB_XILADAPTER::xil_bram_gen"} {
eval "::AESL_LIB_XILADAPTER::xil_bram_gen { \
    id 105 \
    name pre_traces_trace_0 \
    reset_level 1 \
    sync_rst true \
    dir IO \
    corename pre_traces_trace_0 \
    op interface \
    ports { pre_traces_trace_0_address0 { O 7 vector } pre_traces_trace_0_ce0 { O 1 bit } pre_traces_trace_0_q0 { I 8 vector } pre_traces_trace_0_address1 { O 7 vector } pre_traces_trace_0_ce1 { O 1 bit } pre_traces_trace_0_we1 { O 1 bit } pre_traces_trace_0_d1 { O 8 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'pre_traces_trace_0'"
}
}


# XIL_BRAM:
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc ::AESL_LIB_XILADAPTER::xil_bram_gen] == "::AESL_LIB_XILADAPTER::xil_bram_gen"} {
eval "::AESL_LIB_XILADAPTER::xil_bram_gen { \
    id 106 \
    name pre_traces_trace_1 \
    reset_level 1 \
    sync_rst true \
    dir IO \
    corename pre_traces_trace_1 \
    op interface \
    ports { pre_traces_trace_1_address0 { O 7 vector } pre_traces_trace_1_ce0 { O 1 bit } pre_traces_trace_1_q0 { I 8 vector } pre_traces_trace_1_address1 { O 7 vector } pre_traces_trace_1_ce1 { O 1 bit } pre_traces_trace_1_we1 { O 1 bit } pre_traces_trace_1_d1 { O 8 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'pre_traces_trace_1'"
}
}


# XIL_BRAM:
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc ::AESL_LIB_XILADAPTER::xil_bram_gen] == "::AESL_LIB_XILADAPTER::xil_bram_gen"} {
eval "::AESL_LIB_XILADAPTER::xil_bram_gen { \
    id 107 \
    name pre_traces_last_spike_time_0 \
    reset_level 1 \
    sync_rst true \
    dir IO \
    corename pre_traces_last_spike_time_0 \
    op interface \
    ports { pre_traces_last_spike_time_0_address0 { O 7 vector } pre_traces_last_spike_time_0_ce0 { O 1 bit } pre_traces_last_spike_time_0_q0 { I 16 vector } pre_traces_last_spike_time_0_address1 { O 7 vector } pre_traces_last_spike_time_0_ce1 { O 1 bit } pre_traces_last_spike_time_0_we1 { O 1 bit } pre_traces_last_spike_time_0_d1 { O 16 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'pre_traces_last_spike_time_0'"
}
}


# XIL_BRAM:
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc ::AESL_LIB_XILADAPTER::xil_bram_gen] == "::AESL_LIB_XILADAPTER::xil_bram_gen"} {
eval "::AESL_LIB_XILADAPTER::xil_bram_gen { \
    id 108 \
    name pre_traces_last_spike_time_1 \
    reset_level 1 \
    sync_rst true \
    dir IO \
    corename pre_traces_last_spike_time_1 \
    op interface \
    ports { pre_traces_last_spike_time_1_address0 { O 7 vector } pre_traces_last_spike_time_1_ce0 { O 1 bit } pre_traces_last_spike_time_1_q0 { I 16 vector } pre_traces_last_spike_time_1_address1 { O 7 vector } pre_traces_last_spike_time_1_ce1 { O 1 bit } pre_traces_last_spike_time_1_we1 { O 1 bit } pre_traces_last_spike_time_1_d1 { O 16 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'pre_traces_last_spike_time_1'"
}
}


# XIL_BRAM:
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc ::AESL_LIB_XILADAPTER::xil_bram_gen] == "::AESL_LIB_XILADAPTER::xil_bram_gen"} {
eval "::AESL_LIB_XILADAPTER::xil_bram_gen { \
    id 109 \
    name EXP_DECAY_LUT \
    reset_level 1 \
    sync_rst true \
    dir I \
    corename EXP_DECAY_LUT \
    op interface \
    ports { EXP_DECAY_LUT_address0 { O 4 vector } EXP_DECAY_LUT_ce0 { O 1 bit } EXP_DECAY_LUT_q0 { I 8 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'EXP_DECAY_LUT'"
}
}


# XIL_BRAM:
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc ::AESL_LIB_XILADAPTER::xil_bram_gen] == "::AESL_LIB_XILADAPTER::xil_bram_gen"} {
eval "::AESL_LIB_XILADAPTER::xil_bram_gen { \
    id 110 \
    name post_traces_trace_1 \
    reset_level 1 \
    sync_rst true \
    dir I \
    corename post_traces_trace_1 \
    op interface \
    ports { post_traces_trace_1_address0 { O 7 vector } post_traces_trace_1_ce0 { O 1 bit } post_traces_trace_1_q0 { I 8 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'post_traces_trace_1'"
}
}


# XIL_BRAM:
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc ::AESL_LIB_XILADAPTER::xil_bram_gen] == "::AESL_LIB_XILADAPTER::xil_bram_gen"} {
eval "::AESL_LIB_XILADAPTER::xil_bram_gen { \
    id 111 \
    name post_traces_last_spike_time_1 \
    reset_level 1 \
    sync_rst true \
    dir I \
    corename post_traces_last_spike_time_1 \
    op interface \
    ports { post_traces_last_spike_time_1_address0 { O 7 vector } post_traces_last_spike_time_1_ce0 { O 1 bit } post_traces_last_spike_time_1_q0 { I 16 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'post_traces_last_spike_time_1'"
}
}


# XIL_BRAM:
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc ::AESL_LIB_XILADAPTER::xil_bram_gen] == "::AESL_LIB_XILADAPTER::xil_bram_gen"} {
eval "::AESL_LIB_XILADAPTER::xil_bram_gen { \
    id 112 \
    name post_traces_trace_0 \
    reset_level 1 \
    sync_rst true \
    dir I \
    corename post_traces_trace_0 \
    op interface \
    ports { post_traces_trace_0_address0 { O 7 vector } post_traces_trace_0_ce0 { O 1 bit } post_traces_trace_0_q0 { I 8 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'post_traces_trace_0'"
}
}


# XIL_BRAM:
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc ::AESL_LIB_XILADAPTER::xil_bram_gen] == "::AESL_LIB_XILADAPTER::xil_bram_gen"} {
eval "::AESL_LIB_XILADAPTER::xil_bram_gen { \
    id 113 \
    name post_traces_last_spike_time_0 \
    reset_level 1 \
    sync_rst true \
    dir I \
    corename post_traces_last_spike_time_0 \
    op interface \
    ports { post_traces_last_spike_time_0_address0 { O 7 vector } post_traces_last_spike_time_0_ce0 { O 1 bit } post_traces_last_spike_time_0_q0 { I 16 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'post_traces_last_spike_time_0'"
}
}


# XIL_BRAM:
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc ::AESL_LIB_XILADAPTER::xil_bram_gen] == "::AESL_LIB_XILADAPTER::xil_bram_gen"} {
eval "::AESL_LIB_XILADAPTER::xil_bram_gen { \
    id 114 \
    name p_ZL13weight_memory_0 \
    reset_level 1 \
    sync_rst true \
    dir IO \
    corename p_ZL13weight_memory_0 \
    op interface \
    ports { p_ZL13weight_memory_0_address0 { O 15 vector } p_ZL13weight_memory_0_ce0 { O 1 bit } p_ZL13weight_memory_0_q0 { I 8 vector } p_ZL13weight_memory_0_address1 { O 15 vector } p_ZL13weight_memory_0_ce1 { O 1 bit } p_ZL13weight_memory_0_we1 { O 1 bit } p_ZL13weight_memory_0_d1 { O 8 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'p_ZL13weight_memory_0'"
}
}


# XIL_BRAM:
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc ::AESL_LIB_XILADAPTER::xil_bram_gen] == "::AESL_LIB_XILADAPTER::xil_bram_gen"} {
eval "::AESL_LIB_XILADAPTER::xil_bram_gen { \
    id 115 \
    name p_ZL13weight_memory_1 \
    reset_level 1 \
    sync_rst true \
    dir IO \
    corename p_ZL13weight_memory_1 \
    op interface \
    ports { p_ZL13weight_memory_1_address0 { O 15 vector } p_ZL13weight_memory_1_ce0 { O 1 bit } p_ZL13weight_memory_1_q0 { I 8 vector } p_ZL13weight_memory_1_address1 { O 15 vector } p_ZL13weight_memory_1_ce1 { O 1 bit } p_ZL13weight_memory_1_we1 { O 1 bit } p_ZL13weight_memory_1_d1 { O 8 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'p_ZL13weight_memory_1'"
}
}


# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 103 \
    name pre_id \
    type other \
    dir I \
    reset_level 1 \
    sync_rst true \
    corename dc_pre_id \
    op interface \
    ports { pre_id { I 8 vector } } \
} "
}

# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 104 \
    name current_time \
    type other \
    dir I \
    reset_level 1 \
    sync_rst true \
    corename dc_current_time \
    op interface \
    ports { current_time { I 16 vector } } \
} "
}

# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id -1 \
    name ap_ctrl \
    type ap_ctrl \
    reset_level 1 \
    sync_rst true \
    corename ap_ctrl \
    op interface \
    ports { ap_start { I 1 bit } ap_ready { O 1 bit } ap_done { O 1 bit } ap_idle { O 1 bit } } \
} "
}


# Adapter definition:
set PortName ap_clk
set DataWd 1 
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc cg_default_interface_gen_clock] == "cg_default_interface_gen_clock"} {
eval "cg_default_interface_gen_clock { \
    id -2 \
    name ${PortName} \
    reset_level 1 \
    sync_rst true \
    corename apif_ap_clk \
    data_wd ${DataWd} \
    op interface \
}"
} else {
puts "@W \[IMPL-113\] Cannot find bus interface model in the library. Ignored generation of bus interface for '${PortName}'"
}
}


# Adapter definition:
set PortName ap_rst
set DataWd 1 
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc cg_default_interface_gen_reset] == "cg_default_interface_gen_reset"} {
eval "cg_default_interface_gen_reset { \
    id -3 \
    name ${PortName} \
    reset_level 1 \
    sync_rst true \
    corename apif_ap_rst \
    data_wd ${DataWd} \
    op interface \
}"
} else {
puts "@W \[IMPL-114\] Cannot find bus interface model in the library. Ignored generation of bus interface for '${PortName}'"
}
}



# merge
if {${::AESL::PGuard_autoexp_gen}} {
    cg_default_interface_gen_dc_end
    cg_default_interface_gen_bundle_end
    AESL_LIB_XILADAPTER::native_axis_end
}


