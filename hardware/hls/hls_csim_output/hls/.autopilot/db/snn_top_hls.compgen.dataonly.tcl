# This script segment is generated automatically by AutoPilot

set axilite_register_dict [dict create]
set port_ctrl {
ctrl_reg { 
	dir I
	width 32
	depth 1
	mode ap_none
	offset 16
	offset_end 23
}
config_reg { 
	dir I
	width 32
	depth 1
	mode ap_none
	offset 24
	offset_end 31
}
mode_reg { 
	dir I
	width 32
	depth 1
	mode ap_none
	offset 32
	offset_end 39
}
time_steps_reg { 
	dir I
	width 32
	depth 1
	mode ap_none
	offset 40
	offset_end 47
}
learning_params { 
	dir I
	width 144
	depth 1
	mode ap_none
	offset 48
	offset_end 71
}
encoder_config { 
	dir I
	width 144
	depth 1
	mode ap_none
	offset 72
	offset_end 95
}
status_reg { 
	dir O
	width 32
	depth 1
	mode ap_vld
	offset 96
	offset_end 103
}
spike_count_reg { 
	dir O
	width 32
	depth 1
	mode ap_vld
	offset 112
	offset_end 119
}
weight_sum_reg { 
	dir O
	width 32
	depth 1
	mode ap_vld
	offset 128
	offset_end 135
}
version_reg { 
	dir O
	width 32
	depth 1
	mode ap_vld
	offset 144
	offset_end 151
}
reward_signal { 
	dir I
	width 8
	depth 1
	mode ap_none
	offset 160
	offset_end 167
}
ap_start { }
ap_done { }
ap_ready { }
ap_idle { }
interrupt {
}
}
dict set axilite_register_dict ctrl $port_ctrl


