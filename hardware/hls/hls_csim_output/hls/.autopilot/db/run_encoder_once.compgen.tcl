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
    id 79 \
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
    id 81 \
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
    id 82 \
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
    id 83 \
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
    id 84 \
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
    id 85 \
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
    id 86 \
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
    id 87 \
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
    id 66 \
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
    id 67 \
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
    id 68 \
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
    id 69 \
    name config_rate_scale_val \
    type other \
    dir I \
    reset_level 1 \
    sync_rst true \
    corename dc_config_rate_scale_val \
    op interface \
    ports { config_rate_scale_val { I 16 vector } } \
} "
}

# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 70 \
    name config_latency_window_val \
    type other \
    dir I \
    reset_level 1 \
    sync_rst true \
    corename dc_config_latency_window_val \
    op interface \
    ports { config_latency_window_val { I 16 vector } } \
} "
}

# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 71 \
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
    id 72 \
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
    id 73 \
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
    id 74 \
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
    id 75 \
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
    id 76 \
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
    id 77 \
    name encoder_frame_loaded \
    type other \
    dir I \
    reset_level 1 \
    sync_rst true \
    corename dc_encoder_frame_loaded \
    op interface \
    ports { encoder_frame_loaded { I 1 vector } } \
} "
}

# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 78 \
    name latency_window_counter \
    type other \
    dir IO \
    reset_level 1 \
    sync_rst true \
    corename dc_latency_window_counter \
    op interface \
    ports { latency_window_counter_i { I 16 vector } latency_window_counter_o { O 16 vector } latency_window_counter_o_ap_vld { O 1 bit } } \
} "
}

# Direct connection:
if {${::AESL::PGuard_autoexp_gen}} {
eval "cg_default_interface_gen_dc { \
    id 80 \
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


