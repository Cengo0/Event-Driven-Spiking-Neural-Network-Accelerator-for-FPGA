set SynModuleInfo {
  {SRCNAME encoder_reset_temporal_state MODELNAME encoder_reset_temporal_state RTLNAME snn_top_hls_encoder_reset_temporal_state
    SUBMODULES {
      {MODELNAME snn_top_hls_flow_control_loop_pipe_sequential_init RTLNAME snn_top_hls_flow_control_loop_pipe_sequential_init BINDTYPE interface TYPE internal_upc_flow_control INSTNAME snn_top_hls_flow_control_loop_pipe_sequential_init_U}
    }
  }
  {SRCNAME snn_top_hls_Pipeline_RESET_ELIG MODELNAME snn_top_hls_Pipeline_RESET_ELIG RTLNAME snn_top_hls_snn_top_hls_Pipeline_RESET_ELIG}
  {SRCNAME snn_top_hls_Pipeline_RESET_TRACES MODELNAME snn_top_hls_Pipeline_RESET_TRACES RTLNAME snn_top_hls_snn_top_hls_Pipeline_RESET_TRACES}
  {SRCNAME snn_top_hls_Pipeline_RESET_ENCODER MODELNAME snn_top_hls_Pipeline_RESET_ENCODER RTLNAME snn_top_hls_snn_top_hls_Pipeline_RESET_ENCODER}
  {SRCNAME snn_top_hls_Pipeline_INIT_WEIGHT_OUTER_INIT_WEIGHT_INNER MODELNAME snn_top_hls_Pipeline_INIT_WEIGHT_OUTER_INIT_WEIGHT_INNER RTLNAME snn_top_hls_snn_top_hls_Pipeline_INIT_WEIGHT_OUTER_INIT_WEIGHT_INNER}
  {SRCNAME snn_top_hls_Pipeline_LOAD_FRAME MODELNAME snn_top_hls_Pipeline_LOAD_FRAME RTLNAME snn_top_hls_snn_top_hls_Pipeline_LOAD_FRAME}
  {SRCNAME run_encoder_once_Pipeline_ENCODER_LOOP MODELNAME run_encoder_once_Pipeline_ENCODER_LOOP RTLNAME snn_top_hls_run_encoder_once_Pipeline_ENCODER_LOOP
    SUBMODULES {
      {MODELNAME snn_top_hls_mul_16ns_8ns_24_1_1 RTLNAME snn_top_hls_mul_16ns_8ns_24_1_1 BINDTYPE op TYPE mul IMPL auto LATENCY 0 ALLOW_PRAGMA 1}
      {MODELNAME snn_top_hls_mul_8ns_16ns_24_1_1 RTLNAME snn_top_hls_mul_8ns_16ns_24_1_1 BINDTYPE op TYPE mul IMPL auto LATENCY 0 ALLOW_PRAGMA 1}
    }
  }
  {SRCNAME run_encoder_once MODELNAME run_encoder_once RTLNAME snn_top_hls_run_encoder_once}
  {SRCNAME process_pre_spike_aer_Pipeline_LTD_LOOP MODELNAME process_pre_spike_aer_Pipeline_LTD_LOOP RTLNAME snn_top_hls_process_pre_spike_aer_Pipeline_LTD_LOOP
    SUBMODULES {
      {MODELNAME snn_top_hls_mul_8ns_8ns_16_1_1 RTLNAME snn_top_hls_mul_8ns_8ns_16_1_1 BINDTYPE op TYPE mul IMPL auto LATENCY 0 ALLOW_PRAGMA 1}
      {MODELNAME snn_top_hls_process_pre_spike_aer_Pipeline_LTD_LOOP_EXP_DECAY_LUT_ROM_AUTO_1R RTLNAME snn_top_hls_process_pre_spike_aer_Pipeline_LTD_LOOP_EXP_DECAY_LUT_ROM_AUTO_1R BINDTYPE storage TYPE rom IMPL auto LATENCY 2 ALLOW_PRAGMA 1}
    }
  }
  {SRCNAME process_pre_spike_aer MODELNAME process_pre_spike_aer RTLNAME snn_top_hls_process_pre_spike_aer}
  {SRCNAME process_post_spike_aer_Pipeline_LTP_LOOP MODELNAME process_post_spike_aer_Pipeline_LTP_LOOP RTLNAME snn_top_hls_process_post_spike_aer_Pipeline_LTP_LOOP}
  {SRCNAME process_post_spike_aer MODELNAME process_post_spike_aer RTLNAME snn_top_hls_process_post_spike_aer}
  {SRCNAME apply_rstdp_reward_Pipeline_RSTDP_INNER MODELNAME apply_rstdp_reward_Pipeline_RSTDP_INNER RTLNAME snn_top_hls_apply_rstdp_reward_Pipeline_RSTDP_INNER
    SUBMODULES {
      {MODELNAME snn_top_hls_mul_8s_8s_16_1_1 RTLNAME snn_top_hls_mul_8s_8s_16_1_1 BINDTYPE op TYPE mul IMPL auto LATENCY 0 ALLOW_PRAGMA 1}
      {MODELNAME snn_top_hls_sparsemux_9_3_7_1_1 RTLNAME snn_top_hls_sparsemux_9_3_7_1_1 BINDTYPE op TYPE sparsemux IMPL onehotencoding_realdef}
    }
  }
  {SRCNAME apply_rstdp_reward MODELNAME apply_rstdp_reward RTLNAME snn_top_hls_apply_rstdp_reward
    SUBMODULES {
      {MODELNAME snn_top_hls_sparsemux_7_2_2_1_1 RTLNAME snn_top_hls_sparsemux_7_2_2_1_1 BINDTYPE op TYPE sparsemux IMPL onehotencoding_realdef}
    }
  }
  {SRCNAME decay_eligibility_traces_Pipeline_DECAY_PRE MODELNAME decay_eligibility_traces_Pipeline_DECAY_PRE RTLNAME snn_top_hls_decay_eligibility_traces_Pipeline_DECAY_PRE}
  {SRCNAME decay_eligibility_traces_Pipeline_DECAY_POST MODELNAME decay_eligibility_traces_Pipeline_DECAY_POST RTLNAME snn_top_hls_decay_eligibility_traces_Pipeline_DECAY_POST}
  {SRCNAME decay_eligibility_traces MODELNAME decay_eligibility_traces RTLNAME snn_top_hls_decay_eligibility_traces}
  {SRCNAME snn_top_hls_Pipeline_WEIGHT_SUM MODELNAME snn_top_hls_Pipeline_WEIGHT_SUM RTLNAME snn_top_hls_snn_top_hls_Pipeline_WEIGHT_SUM}
  {SRCNAME snn_top_hls MODELNAME snn_top_hls RTLNAME snn_top_hls IS_TOP 1
    SUBMODULES {
      {MODELNAME snn_top_hls_p_ZL22encoder_temporal_fired_0_RAM_2P_BRAM_1R1W RTLNAME snn_top_hls_p_ZL22encoder_temporal_fired_0_RAM_2P_BRAM_1R1W BINDTYPE storage TYPE ram_2p IMPL bram LATENCY 2 ALLOW_PRAGMA 1}
      {MODELNAME snn_top_hls_p_ZL22encoder_temporal_start_0_RAM_2P_BRAM_1R1W RTLNAME snn_top_hls_p_ZL22encoder_temporal_start_0_RAM_2P_BRAM_1R1W BINDTYPE storage TYPE ram_2p IMPL bram LATENCY 2 ALLOW_PRAGMA 1}
      {MODELNAME snn_top_hls_p_ZL15pre_eligibility_0_RAM_2P_BRAM_1R1W RTLNAME snn_top_hls_p_ZL15pre_eligibility_0_RAM_2P_BRAM_1R1W BINDTYPE storage TYPE ram_2p IMPL bram LATENCY 2 ALLOW_PRAGMA 1}
      {MODELNAME snn_top_hls_pre_traces_last_spike_time_0_RAM_2P_BRAM_1R1W RTLNAME snn_top_hls_pre_traces_last_spike_time_0_RAM_2P_BRAM_1R1W BINDTYPE storage TYPE ram_2p IMPL bram LATENCY 2 ALLOW_PRAGMA 1}
      {MODELNAME snn_top_hls_p_ZL17encoder_phase_acc_0_RAM_2P_BRAM_1R1W RTLNAME snn_top_hls_p_ZL17encoder_phase_acc_0_RAM_2P_BRAM_1R1W BINDTYPE storage TYPE ram_2p IMPL bram LATENCY 2 ALLOW_PRAGMA 1}
      {MODELNAME snn_top_hls_p_ZL13weight_memory_0_RAM_2P_BRAM_1R1W RTLNAME snn_top_hls_p_ZL13weight_memory_0_RAM_2P_BRAM_1R1W BINDTYPE storage TYPE ram_2p IMPL bram LATENCY 2 ALLOW_PRAGMA 1}
      {MODELNAME snn_top_hls_p_ZL13encoder_frame_0_RAM_AUTO_1R1W RTLNAME snn_top_hls_p_ZL13encoder_frame_0_RAM_AUTO_1R1W BINDTYPE storage TYPE ram IMPL auto LATENCY 2 ALLOW_PRAGMA 1}
      {MODELNAME snn_top_hls_fifo_w41_d32_A RTLNAME snn_top_hls_fifo_w41_d32_A BINDTYPE storage TYPE fifo IMPL memory ALLOW_PRAGMA 1 INSTNAME encoder_spikes_U}
      {MODELNAME snn_top_hls_ctrl_s_axi RTLNAME snn_top_hls_ctrl_s_axi BINDTYPE interface TYPE interface_s_axilite}
      {MODELNAME snn_top_hls_regslice_both RTLNAME snn_top_hls_regslice_both BINDTYPE interface TYPE adapter IMPL reg_slice}
    }
  }
}
