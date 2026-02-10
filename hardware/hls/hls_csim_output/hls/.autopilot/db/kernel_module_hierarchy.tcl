set ModuleHierarchy {[{
"Name" : "snn_top_hls", "RefName" : "snn_top_hls","ID" : "0","Type" : "sequential",
"SubInsts" : [
	{"Name" : "grp_encoder_reset_temporal_state_fu_1012", "RefName" : "encoder_reset_temporal_state","ID" : "1","Type" : "sequential",
		"SubLoops" : [
		{"Name" : "VITIS_LOOP_48_1","RefName" : "VITIS_LOOP_48_1","ID" : "2","Type" : "pipeline"},]},
	{"Name" : "grp_snn_top_hls_Pipeline_RESET_ELIG_fu_1026", "RefName" : "snn_top_hls_Pipeline_RESET_ELIG","ID" : "3","Type" : "sequential",
		"SubLoops" : [
		{"Name" : "RESET_ELIG","RefName" : "RESET_ELIG","ID" : "4","Type" : "pipeline"},]},
	{"Name" : "grp_snn_top_hls_Pipeline_RESET_TRACES_fu_1038", "RefName" : "snn_top_hls_Pipeline_RESET_TRACES","ID" : "5","Type" : "sequential",
		"SubLoops" : [
		{"Name" : "RESET_TRACES","RefName" : "RESET_TRACES","ID" : "6","Type" : "pipeline"},]},
	{"Name" : "grp_snn_top_hls_Pipeline_RESET_ENCODER_fu_1058", "RefName" : "snn_top_hls_Pipeline_RESET_ENCODER","ID" : "7","Type" : "sequential",
		"SubLoops" : [
		{"Name" : "RESET_ENCODER","RefName" : "RESET_ENCODER","ID" : "8","Type" : "pipeline"},]},
	{"Name" : "grp_snn_top_hls_Pipeline_INIT_WEIGHT_OUTER_INIT_WEIGHT_INNER_fu_1066", "RefName" : "snn_top_hls_Pipeline_INIT_WEIGHT_OUTER_INIT_WEIGHT_INNER","ID" : "9","Type" : "sequential",
		"SubLoops" : [
		{"Name" : "INIT_WEIGHT_OUTER_INIT_WEIGHT_INNER","RefName" : "INIT_WEIGHT_OUTER_INIT_WEIGHT_INNER","ID" : "10","Type" : "pipeline"},]},
	{"Name" : "grp_snn_top_hls_Pipeline_LOAD_FRAME_fu_1074", "RefName" : "snn_top_hls_Pipeline_LOAD_FRAME","ID" : "11","Type" : "sequential",
		"SubLoops" : [
		{"Name" : "LOAD_FRAME","RefName" : "LOAD_FRAME","ID" : "12","Type" : "pipeline"},]},
	{"Name" : "grp_snn_top_hls_Pipeline_WEIGHT_SUM_fu_1135", "RefName" : "snn_top_hls_Pipeline_WEIGHT_SUM","ID" : "13","Type" : "sequential",
		"SubLoops" : [
		{"Name" : "WEIGHT_SUM","RefName" : "WEIGHT_SUM","ID" : "14","Type" : "pipeline"},]},],
"SubLoops" : [
	{"Name" : "TIME_LOOP","RefName" : "TIME_LOOP","ID" : "15","Type" : "no",
	"SubInsts" : [
	{"Name" : "grp_run_encoder_once_fu_1096", "RefName" : "run_encoder_once","ID" : "16","Type" : "sequential",
			"SubInsts" : [
			{"Name" : "grp_run_encoder_once_Pipeline_ENCODER_LOOP_fu_158", "RefName" : "run_encoder_once_Pipeline_ENCODER_LOOP","ID" : "17","Type" : "sequential",
				"SubLoops" : [
				{"Name" : "ENCODER_LOOP","RefName" : "ENCODER_LOOP","ID" : "18","Type" : "pipeline"},]},]},
	{"Name" : "grp_process_pre_spike_aer_fu_1144", "RefName" : "process_pre_spike_aer","ID" : "19","Type" : "sequential",
			"SubInsts" : [
			{"Name" : "grp_process_pre_spike_aer_Pipeline_LTD_LOOP_fu_161", "RefName" : "process_pre_spike_aer_Pipeline_LTD_LOOP","ID" : "20","Type" : "sequential",
				"SubLoops" : [
				{"Name" : "LTD_LOOP","RefName" : "LTD_LOOP","ID" : "21","Type" : "pipeline"},]},]},
	{"Name" : "grp_process_post_spike_aer_fu_1172", "RefName" : "process_post_spike_aer","ID" : "22","Type" : "sequential",
			"SubInsts" : [
			{"Name" : "grp_process_post_spike_aer_Pipeline_LTP_LOOP_fu_161", "RefName" : "process_post_spike_aer_Pipeline_LTP_LOOP","ID" : "23","Type" : "sequential",
				"SubLoops" : [
				{"Name" : "LTP_LOOP","RefName" : "LTP_LOOP","ID" : "24","Type" : "pipeline"},]},]},
	{"Name" : "grp_apply_rstdp_reward_fu_1200", "RefName" : "apply_rstdp_reward","ID" : "25","Type" : "sequential",
			"SubLoops" : [
			{"Name" : "RSTDP_OUTER","RefName" : "RSTDP_OUTER","ID" : "26","Type" : "no",
			"SubInsts" : [
			{"Name" : "grp_apply_rstdp_reward_Pipeline_RSTDP_INNER_fu_132", "RefName" : "apply_rstdp_reward_Pipeline_RSTDP_INNER","ID" : "27","Type" : "sequential",
					"SubLoops" : [
					{"Name" : "RSTDP_INNER","RefName" : "RSTDP_INNER","ID" : "28","Type" : "pipeline"},]},]},]},
	{"Name" : "grp_decay_eligibility_traces_fu_1218", "RefName" : "decay_eligibility_traces","ID" : "29","Type" : "sequential",
			"SubInsts" : [
			{"Name" : "grp_decay_eligibility_traces_Pipeline_DECAY_PRE_fu_22", "RefName" : "decay_eligibility_traces_Pipeline_DECAY_PRE","ID" : "30","Type" : "sequential",
				"SubLoops" : [
				{"Name" : "DECAY_PRE","RefName" : "DECAY_PRE","ID" : "31","Type" : "pipeline"},]},
			{"Name" : "grp_decay_eligibility_traces_Pipeline_DECAY_POST_fu_30", "RefName" : "decay_eligibility_traces_Pipeline_DECAY_POST","ID" : "32","Type" : "sequential",
				"SubLoops" : [
				{"Name" : "DECAY_POST","RefName" : "DECAY_POST","ID" : "33","Type" : "pipeline"},]},]},]},]
}]}