# This script segment is generated automatically by AutoPilot

set name snn_top_hls_mul_16ns_8ns_24_1_1
if {${::AESL::PGuard_rtl_comp_handler}} {
	::AP::rtl_comp_handler $name BINDTYPE {op} TYPE {mul} IMPL {auto} LATENCY 0 ALLOW_PRAGMA 1
}


set name snn_top_hls_mul_8ns_16ns_24_1_1
if {${::AESL::PGuard_rtl_comp_handler}} {
	::AP::rtl_comp_handler $name BINDTYPE {op} TYPE {mul} IMPL {auto} LATENCY 0 ALLOW_PRAGMA 1
}


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
    id 57 \
    name p_ZL13encoder_frame_0 \
    reset_level 1 \
    sync_rst true \
    dir I \
    corename p_ZL13encoder_frame_0 \
    op interface \
    ports { p_ZL13encoder_frame_0_address0 { O 9 vector } p_ZL13encoder_frame_0_ce0 { O 1 bit } p_ZL13encoder_frame_0_q0 { I 8 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'p_ZL13encoder_frame_0'"
}
}


# XIL_BRAM:
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc ::AESL_LIB_XILADAPTER::xil_bram_gen] == "::AESL_LIB_XILADAPTER::xil_bram_gen"} {
eval "::AESL_LIB_XILADAPTER::xil_bram_gen { \
    id 59 \
    name p_ZL22encoder_temporal_fired_1 \
    reset_level 1 \
    sync_rst true \
    dir IO \
    corename p_ZL22encoder_temporal_fired_1 \
    op interface \
    ports { p_ZL22encoder_temporal_fired_1_address0 { O 9 vector } p_ZL22encoder_temporal_fired_1_ce0 { O 1 bit } p_ZL22encoder_temporal_fired_1_q0 { I 1 vector } p_ZL22encoder_temporal_fired_1_address1 { O 9 vector } p_ZL22encoder_temporal_fired_1_ce1 { O 1 bit } p_ZL22encoder_temporal_fired_1_we1 { O 1 bit } p_ZL22encoder_temporal_fired_1_d1 { O 1 vector } p_ZL22encoder_temporal_fired_1_q1 { I 1 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'p_ZL22encoder_temporal_fired_1'"
}
}


# XIL_BRAM:
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc ::AESL_LIB_XILADAPTER::xil_bram_gen] == "::AESL_LIB_XILADAPTER::xil_bram_gen"} {
eval "::AESL_LIB_XILADAPTER::xil_bram_gen { \
    id 60 \
    name p_ZL22encoder_temporal_fired_0 \
    reset_level 1 \
    sync_rst true \
    dir IO \
    corename p_ZL22encoder_temporal_fired_0 \
    op interface \
    ports { p_ZL22encoder_temporal_fired_0_address0 { O 9 vector } p_ZL22encoder_temporal_fired_0_ce0 { O 1 bit } p_ZL22encoder_temporal_fired_0_q0 { I 1 vector } p_ZL22encoder_temporal_fired_0_address1 { O 9 vector } p_ZL22encoder_temporal_fired_0_ce1 { O 1 bit } p_ZL22encoder_temporal_fired_0_we1 { O 1 bit } p_ZL22encoder_temporal_fired_0_d1 { O 1 vector } p_ZL22encoder_temporal_fired_0_q1 { I 1 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'p_ZL22encoder_temporal_fired_0'"
}
}


# XIL_BRAM:
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc ::AESL_LIB_XILADAPTER::xil_bram_gen] == "::AESL_LIB_XILADAPTER::xil_bram_gen"} {
eval "::AESL_LIB_XILADAPTER::xil_bram_gen { \
    id 61 \
    name p_ZL22encoder_temporal_start_0 \
    reset_level 1 \
    sync_rst true \
    dir IO \
    corename p_ZL22encoder_temporal_start_0 \
    op interface \
    ports { p_ZL22encoder_temporal_start_0_address0 { O 9 vector } p_ZL22encoder_temporal_start_0_ce0 { O 1 bit } p_ZL22encoder_temporal_start_0_q0 { I 32 vector } p_ZL22encoder_temporal_start_0_address1 { O 9 vector } p_ZL22encoder_temporal_start_0_ce1 { O 1 bit } p_ZL22encoder_temporal_start_0_we1 { O 1 bit } p_ZL22encoder_temporal_start_0_d1 { O 32 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'p_ZL22encoder_temporal_start_0'"
}
}


# XIL_BRAM:
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc ::AESL_LIB_XILADAPTER::xil_bram_gen] == "::AESL_LIB_XILADAPTER::xil_bram_gen"} {
eval "::AESL_LIB_XILADAPTER::xil_bram_gen { \
    id 62 \
    name p_ZL22encoder_temporal_start_1 \
    reset_level 1 \
    sync_rst true \
    dir IO \
    corename p_ZL22encoder_temporal_start_1 \
    op interface \
    ports { p_ZL22encoder_temporal_start_1_address0 { O 9 vector } p_ZL22encoder_temporal_start_1_ce0 { O 1 bit } p_ZL22encoder_temporal_start_1_q0 { I 32 vector } p_ZL22encoder_temporal_start_1_address1 { O 9 vector } p_ZL22encoder_temporal_start_1_ce1 { O 1 bit } p_ZL22encoder_temporal_start_1_we1 { O 1 bit } p_ZL22encoder_temporal_start_1_d1 { O 32 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'p_ZL22encoder_temporal_start_1'"
}
}


# XIL_BRAM:
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc ::AESL_LIB_XILADAPTER::xil_bram_gen] == "::AESL_LIB_XILADAPTER::xil_bram_gen"} {
eval "::AESL_LIB_XILADAPTER::xil_bram_gen { \
    id 63 \
    name p_ZL17encoder_phase_acc_1 \
    reset_level 1 \
    sync_rst true \
    dir IO \
    corename p_ZL17encoder_phase_acc_1 \
    op interface \
    ports { p_ZL17encoder_phase_acc_1_address0 { O 9 vector } p_ZL17encoder_phase_acc_1_ce0 { O 1 bit } p_ZL17encoder_phase_acc_1_q0 { I 16 vector } p_ZL17encoder_phase_acc_1_address1 { O 9 vector } p_ZL17encoder_phase_acc_1_ce1 { O 1 bit } p_ZL17encoder_phase_acc_1_we1 { O 1 bit } p_ZL17encoder_phase_acc_1_d1 { O 16 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'p_ZL17encoder_phase_acc_1'"
}
}


# XIL_BRAM:
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc ::AESL_LIB_XILADAPTER::xil_bram_gen] == "::AESL_LIB_XILADAPTER::xil_bram_gen"} {
eval "::AESL_LIB_XILADAPTER::xil_bram_gen { \
    id 64 \
    name p_ZL17encoder_phase_acc_0 \
    reset_level 1 \
    sync_rst true \
    dir IO \
    corename p_ZL17encoder_phase_acc_0 \
    op interface \
    ports { p_ZL17encoder_phase_acc_0_address0 { O 9 vector } p_ZL17encoder_phase_acc_0_ce0 { O 1 bit } p_ZL17encoder_phase_acc_0_q0 { I 16 vector } p_ZL17encoder_phase_acc_0_address1 { O 9 vector } p_ZL17encoder_phase_acc_0_ce1 { O 1 bit } p_ZL17encoder_phase_acc_0_we1 { O 1 bit } p_ZL17encoder_phase_acc_0_d1 { O 16 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'p_ZL17encoder_phase_acc_0'"
}
}


# XIL_BRAM:
if {${::AESL::PGuard_autoexp_gen}} {
if {[info proc ::AESL_LIB_XILADAPTER::xil_bram_gen] == "::AESL_LIB_XILADAPTER::xil_bram_gen"} {
eval "::AESL_LIB_XILADAPTER::xil_bram_gen { \
    id 65 \
    name p_ZL13encoder_frame_1 \
    reset_level 1 \
    sync_rst true \
    dir I \
    corename p_ZL13encoder_frame_1 \
    op interface \
    ports { p_ZL13encoder_frame_1_address0 { O 9 vector } p_ZL13encoder_frame_1_ce0 { O 1 bit } p_ZL13encoder_frame_1_q0 { I 8 vector } } \
} "
} else {
puts "@W \[IMPL-110\] Cannot find bus interface model in the library. Ignored generation of bus interface for 'p_ZL13encoder_frame_1'"
}
}


# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 45 \
    name time_r \
    type other \
    dir I \
    reset_level 1 \
    sync_rst true \
    corename dc_time_r \
    op interface \
    ports { time_r { I 32 vector } } \
} "
}

# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 46 \
    name config_num_channels_val \
    type other \
    dir I \
    reset_level 1 \
    sync_rst true \
    corename dc_config_num_channels_val \
    op interface \
    ports { config_num_channels_val { I 16 vector } } \
} "
}

# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 47 \
    name config_baseline_val \
    type other \
    dir I \
    reset_level 1 \
    sync_rst true \
    corename dc_config_baseline_val \
    op interface \
    ports { config_baseline_val { I 8 vector } } \
} "
}

# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 48 \
    name config_encoding_type_val \
    type other \
    dir I \
    reset_level 1 \
    sync_rst true \
    corename dc_config_encoding_type_val \
    op interface \
    ports { config_encoding_type_val { I 4 vector } } \
} "
}

# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 49 \
    name config_two_neuron_enable_val \
    type other \
    dir I \
    reset_level 1 \
    sync_rst true \
    corename dc_config_two_neuron_enable_val \
    op interface \
    ports { config_two_neuron_enable_val { I 1 vector } } \
} "
}

# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 50 \
    name zext_ln108 \
    type other \
    dir I \
    reset_level 1 \
    sync_rst true \
    corename dc_zext_ln108 \
    op interface \
    ports { zext_ln108 { I 16 vector } } \
} "
}

# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 51 \
    name encoder_spikes \
    type fifo \
    dir O \
    reset_level 1 \
    sync_rst true \
    corename dc_encoder_spikes \
    op interface \
    ports { encoder_spikes_din { O 41 vector } encoder_spikes_full_n { I 1 bit } encoder_spikes_write { O 1 bit } } \
} "
}

# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 52 \
    name config_default_weight_val \
    type other \
    dir I \
    reset_level 1 \
    sync_rst true \
    corename dc_config_default_weight_val \
    op interface \
    ports { config_default_weight_val { I 8 vector } } \
} "
}

# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 53 \
    name latency_window_reset_1 \
    type other \
    dir I \
    reset_level 1 \
    sync_rst true \
    corename dc_latency_window_reset_1 \
    op interface \
    ports { latency_window_reset_1 { I 1 vector } } \
} "
}

# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 54 \
    name zext_ln137_13 \
    type other \
    dir I \
    reset_level 1 \
    sync_rst true \
    corename dc_zext_ln137_13 \
    op interface \
    ports { zext_ln137_13 { I 16 vector } } \
} "
}

# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 55 \
    name config_delta_decay_val \
    type other \
    dir I \
    reset_level 1 \
    sync_rst true \
    corename dc_config_delta_decay_val \
    op interface \
    ports { config_delta_decay_val { I 16 vector } } \
} "
}

# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 56 \
    name config_delta_threshold_val \
    type other \
    dir I \
    reset_level 1 \
    sync_rst true \
    corename dc_config_delta_threshold_val \
    op interface \
    ports { config_delta_threshold_val { I 16 vector } } \
} "
}

# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 58 \
    name encoder_spike_counter \
    type other \
    dir IO \
    reset_level 1 \
    sync_rst true \
    corename dc_encoder_spike_counter \
    op interface \
    ports { encoder_spike_counter_i { I 32 vector } encoder_spike_counter_o { O 32 vector } encoder_spike_counter_o_ap_vld { O 1 bit } } \
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


# flow_control definition:
set InstName snn_top_hls_flow_control_loop_pipe_sequential_init_U
set CompName snn_top_hls_flow_control_loop_pipe_sequential_init
set name flow_control_loop_pipe_sequential_init
if {${::AESL::PGuard_autocg_gen} && ${::AESL::PGuard_autocg_ipmgen}} {
if {[info proc ::AESL_LIB_VIRTEX::xil_gen_UPC_flow_control] == "::AESL_LIB_VIRTEX::xil_gen_UPC_flow_control"} {
eval "::AESL_LIB_VIRTEX::xil_gen_UPC_flow_control { \
    name ${name} \
    prefix snn_top_hls_ \
}"
} else {
puts "@W \[IMPL-107\] Cannot find ::AESL_LIB_VIRTEX::xil_gen_UPC_flow_control, check your platform lib"
}
}


if {${::AESL::PGuard_rtl_comp_handler}} {
	::AP::rtl_comp_handler $CompName BINDTYPE interface TYPE internal_upc_flow_control INSTNAME $InstName
}


