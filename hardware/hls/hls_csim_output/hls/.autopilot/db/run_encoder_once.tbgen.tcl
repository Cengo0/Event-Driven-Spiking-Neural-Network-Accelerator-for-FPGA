set moduleName run_encoder_once
set isTopModule 0
set isCombinational 0
set isDatapathOnly 0
set isPipelined 0
set isPipelined_legacy 0
set pipeline_type none
set FunctionProtocol ap_ctrl_hs
set restart_counter_num 0
set isOneStateSeq 0
set ProfileFlag 0
set StallSigGenFlag 0
set isEnableWaveformDebug 1
set hasInterrupt 0
set DLRegFirstOffset 0
set DLRegItemOffset 0
set svuvm_can_support 1
set cdfgNum 21
set C_modelName {run_encoder_once}
set C_modelType { void 0 }
set ap_memory_interface_dict [dict create]
dict set ap_memory_interface_dict p_ZL13encoder_frame_0 { MEM_WIDTH 8 MEM_SIZE 392 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict p_ZL22encoder_temporal_fired_1 { MEM_WIDTH 1 MEM_SIZE 392 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict p_ZL22encoder_temporal_fired_0 { MEM_WIDTH 1 MEM_SIZE 392 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict p_ZL22encoder_temporal_start_0 { MEM_WIDTH 32 MEM_SIZE 1568 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict p_ZL22encoder_temporal_start_1 { MEM_WIDTH 32 MEM_SIZE 1568 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict p_ZL17encoder_phase_acc_1 { MEM_WIDTH 16 MEM_SIZE 784 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict p_ZL17encoder_phase_acc_0 { MEM_WIDTH 16 MEM_SIZE 784 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict p_ZL13encoder_frame_1 { MEM_WIDTH 8 MEM_SIZE 392 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
set C_modelArgList {
	{ config_encoding_type_val int 4 regular  }
	{ config_two_neuron_enable_val int 1 regular  }
	{ config_baseline_val int 8 regular  }
	{ config_rate_scale_val int 16 regular  }
	{ config_latency_window_val int 16 regular  }
	{ config_delta_threshold_val int 16 regular  }
	{ config_delta_decay_val int 16 regular  }
	{ config_num_channels_val int 16 regular  }
	{ config_default_weight_val int 8 regular  }
	{ time_r int 32 regular  }
	{ encoder_spikes int 41 regular {fifo 1 volatile }  }
	{ encoder_frame_loaded int 1 regular {pointer 0} {global 0}  }
	{ latency_window_counter int 16 regular {pointer 2} {global 2}  }
	{ p_ZL13encoder_frame_0 int 8 regular {array 392 { 1 3 } 1 1 } {global 0}  }
	{ encoder_spike_counter int 32 regular {pointer 2} {global 2}  }
	{ p_ZL22encoder_temporal_fired_1 int 1 regular {array 392 { 1 2 } 1 1 } {global 2}  }
	{ p_ZL22encoder_temporal_fired_0 int 1 regular {array 392 { 1 2 } 1 1 } {global 2}  }
	{ p_ZL22encoder_temporal_start_0 int 32 regular {array 392 { 1 0 } 1 1 } {global 2}  }
	{ p_ZL22encoder_temporal_start_1 int 32 regular {array 392 { 1 0 } 1 1 } {global 2}  }
	{ p_ZL17encoder_phase_acc_1 int 16 regular {array 392 { 1 0 } 1 1 } {global 2}  }
	{ p_ZL17encoder_phase_acc_0 int 16 regular {array 392 { 1 0 } 1 1 } {global 2}  }
	{ p_ZL13encoder_frame_1 int 8 regular {array 392 { 1 3 } 1 1 } {global 0}  }
}
set hasAXIMCache 0
set l_AXIML2Cache [list]
set AXIMCacheInstDict [dict create]
set C_modelArgMapList {[ 
	{ "Name" : "config_encoding_type_val", "interface" : "wire", "bitwidth" : 4, "direction" : "READONLY"} , 
 	{ "Name" : "config_two_neuron_enable_val", "interface" : "wire", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "config_baseline_val", "interface" : "wire", "bitwidth" : 8, "direction" : "READONLY"} , 
 	{ "Name" : "config_rate_scale_val", "interface" : "wire", "bitwidth" : 16, "direction" : "READONLY"} , 
 	{ "Name" : "config_latency_window_val", "interface" : "wire", "bitwidth" : 16, "direction" : "READONLY"} , 
 	{ "Name" : "config_delta_threshold_val", "interface" : "wire", "bitwidth" : 16, "direction" : "READONLY"} , 
 	{ "Name" : "config_delta_decay_val", "interface" : "wire", "bitwidth" : 16, "direction" : "READONLY"} , 
 	{ "Name" : "config_num_channels_val", "interface" : "wire", "bitwidth" : 16, "direction" : "READONLY"} , 
 	{ "Name" : "config_default_weight_val", "interface" : "wire", "bitwidth" : 8, "direction" : "READONLY"} , 
 	{ "Name" : "time_r", "interface" : "wire", "bitwidth" : 32, "direction" : "READONLY"} , 
 	{ "Name" : "encoder_spikes", "interface" : "fifo", "bitwidth" : 41, "direction" : "WRITEONLY"} , 
 	{ "Name" : "encoder_frame_loaded", "interface" : "wire", "bitwidth" : 1, "direction" : "READONLY", "extern" : 0} , 
 	{ "Name" : "latency_window_counter", "interface" : "wire", "bitwidth" : 16, "direction" : "READWRITE", "extern" : 0} , 
 	{ "Name" : "p_ZL13encoder_frame_0", "interface" : "memory", "bitwidth" : 8, "direction" : "READONLY", "extern" : 0} , 
 	{ "Name" : "encoder_spike_counter", "interface" : "wire", "bitwidth" : 32, "direction" : "READWRITE", "extern" : 0} , 
 	{ "Name" : "p_ZL22encoder_temporal_fired_1", "interface" : "memory", "bitwidth" : 1, "direction" : "READWRITE", "extern" : 0} , 
 	{ "Name" : "p_ZL22encoder_temporal_fired_0", "interface" : "memory", "bitwidth" : 1, "direction" : "READWRITE", "extern" : 0} , 
 	{ "Name" : "p_ZL22encoder_temporal_start_0", "interface" : "memory", "bitwidth" : 32, "direction" : "READWRITE", "extern" : 0} , 
 	{ "Name" : "p_ZL22encoder_temporal_start_1", "interface" : "memory", "bitwidth" : 32, "direction" : "READWRITE", "extern" : 0} , 
 	{ "Name" : "p_ZL17encoder_phase_acc_1", "interface" : "memory", "bitwidth" : 16, "direction" : "READWRITE", "extern" : 0} , 
 	{ "Name" : "p_ZL17encoder_phase_acc_0", "interface" : "memory", "bitwidth" : 16, "direction" : "READWRITE", "extern" : 0} , 
 	{ "Name" : "p_ZL13encoder_frame_1", "interface" : "memory", "bitwidth" : 8, "direction" : "READONLY", "extern" : 0} ]}
# RTL Port declarations: 
set portNum 76
set portList { 
	{ ap_clk sc_in sc_logic 1 clock -1 } 
	{ ap_rst sc_in sc_logic 1 reset -1 active_high_sync } 
	{ ap_start sc_in sc_logic 1 start -1 } 
	{ ap_done sc_out sc_logic 1 predone -1 } 
	{ ap_idle sc_out sc_logic 1 done -1 } 
	{ ap_ready sc_out sc_logic 1 ready -1 } 
	{ config_encoding_type_val sc_in sc_lv 4 signal 0 } 
	{ config_two_neuron_enable_val sc_in sc_lv 1 signal 1 } 
	{ config_baseline_val sc_in sc_lv 8 signal 2 } 
	{ config_rate_scale_val sc_in sc_lv 16 signal 3 } 
	{ config_latency_window_val sc_in sc_lv 16 signal 4 } 
	{ config_delta_threshold_val sc_in sc_lv 16 signal 5 } 
	{ config_delta_decay_val sc_in sc_lv 16 signal 6 } 
	{ config_num_channels_val sc_in sc_lv 16 signal 7 } 
	{ config_default_weight_val sc_in sc_lv 8 signal 8 } 
	{ time_r sc_in sc_lv 32 signal 9 } 
	{ encoder_spikes_din sc_out sc_lv 41 signal 10 } 
	{ encoder_spikes_full_n sc_in sc_logic 1 signal 10 } 
	{ encoder_spikes_write sc_out sc_logic 1 signal 10 } 
	{ encoder_frame_loaded sc_in sc_lv 1 signal 11 } 
	{ latency_window_counter_i sc_in sc_lv 16 signal 12 } 
	{ latency_window_counter_o sc_out sc_lv 16 signal 12 } 
	{ latency_window_counter_o_ap_vld sc_out sc_logic 1 outvld 12 } 
	{ p_ZL13encoder_frame_0_address0 sc_out sc_lv 9 signal 13 } 
	{ p_ZL13encoder_frame_0_ce0 sc_out sc_logic 1 signal 13 } 
	{ p_ZL13encoder_frame_0_q0 sc_in sc_lv 8 signal 13 } 
	{ encoder_spike_counter_i sc_in sc_lv 32 signal 14 } 
	{ encoder_spike_counter_o sc_out sc_lv 32 signal 14 } 
	{ encoder_spike_counter_o_ap_vld sc_out sc_logic 1 outvld 14 } 
	{ p_ZL22encoder_temporal_fired_1_address0 sc_out sc_lv 9 signal 15 } 
	{ p_ZL22encoder_temporal_fired_1_ce0 sc_out sc_logic 1 signal 15 } 
	{ p_ZL22encoder_temporal_fired_1_q0 sc_in sc_lv 1 signal 15 } 
	{ p_ZL22encoder_temporal_fired_1_address1 sc_out sc_lv 9 signal 15 } 
	{ p_ZL22encoder_temporal_fired_1_ce1 sc_out sc_logic 1 signal 15 } 
	{ p_ZL22encoder_temporal_fired_1_we1 sc_out sc_logic 1 signal 15 } 
	{ p_ZL22encoder_temporal_fired_1_d1 sc_out sc_lv 1 signal 15 } 
	{ p_ZL22encoder_temporal_fired_1_q1 sc_in sc_lv 1 signal 15 } 
	{ p_ZL22encoder_temporal_fired_0_address0 sc_out sc_lv 9 signal 16 } 
	{ p_ZL22encoder_temporal_fired_0_ce0 sc_out sc_logic 1 signal 16 } 
	{ p_ZL22encoder_temporal_fired_0_q0 sc_in sc_lv 1 signal 16 } 
	{ p_ZL22encoder_temporal_fired_0_address1 sc_out sc_lv 9 signal 16 } 
	{ p_ZL22encoder_temporal_fired_0_ce1 sc_out sc_logic 1 signal 16 } 
	{ p_ZL22encoder_temporal_fired_0_we1 sc_out sc_logic 1 signal 16 } 
	{ p_ZL22encoder_temporal_fired_0_d1 sc_out sc_lv 1 signal 16 } 
	{ p_ZL22encoder_temporal_fired_0_q1 sc_in sc_lv 1 signal 16 } 
	{ p_ZL22encoder_temporal_start_0_address0 sc_out sc_lv 9 signal 17 } 
	{ p_ZL22encoder_temporal_start_0_ce0 sc_out sc_logic 1 signal 17 } 
	{ p_ZL22encoder_temporal_start_0_q0 sc_in sc_lv 32 signal 17 } 
	{ p_ZL22encoder_temporal_start_0_address1 sc_out sc_lv 9 signal 17 } 
	{ p_ZL22encoder_temporal_start_0_ce1 sc_out sc_logic 1 signal 17 } 
	{ p_ZL22encoder_temporal_start_0_we1 sc_out sc_logic 1 signal 17 } 
	{ p_ZL22encoder_temporal_start_0_d1 sc_out sc_lv 32 signal 17 } 
	{ p_ZL22encoder_temporal_start_1_address0 sc_out sc_lv 9 signal 18 } 
	{ p_ZL22encoder_temporal_start_1_ce0 sc_out sc_logic 1 signal 18 } 
	{ p_ZL22encoder_temporal_start_1_q0 sc_in sc_lv 32 signal 18 } 
	{ p_ZL22encoder_temporal_start_1_address1 sc_out sc_lv 9 signal 18 } 
	{ p_ZL22encoder_temporal_start_1_ce1 sc_out sc_logic 1 signal 18 } 
	{ p_ZL22encoder_temporal_start_1_we1 sc_out sc_logic 1 signal 18 } 
	{ p_ZL22encoder_temporal_start_1_d1 sc_out sc_lv 32 signal 18 } 
	{ p_ZL17encoder_phase_acc_1_address0 sc_out sc_lv 9 signal 19 } 
	{ p_ZL17encoder_phase_acc_1_ce0 sc_out sc_logic 1 signal 19 } 
	{ p_ZL17encoder_phase_acc_1_q0 sc_in sc_lv 16 signal 19 } 
	{ p_ZL17encoder_phase_acc_1_address1 sc_out sc_lv 9 signal 19 } 
	{ p_ZL17encoder_phase_acc_1_ce1 sc_out sc_logic 1 signal 19 } 
	{ p_ZL17encoder_phase_acc_1_we1 sc_out sc_logic 1 signal 19 } 
	{ p_ZL17encoder_phase_acc_1_d1 sc_out sc_lv 16 signal 19 } 
	{ p_ZL17encoder_phase_acc_0_address0 sc_out sc_lv 9 signal 20 } 
	{ p_ZL17encoder_phase_acc_0_ce0 sc_out sc_logic 1 signal 20 } 
	{ p_ZL17encoder_phase_acc_0_q0 sc_in sc_lv 16 signal 20 } 
	{ p_ZL17encoder_phase_acc_0_address1 sc_out sc_lv 9 signal 20 } 
	{ p_ZL17encoder_phase_acc_0_ce1 sc_out sc_logic 1 signal 20 } 
	{ p_ZL17encoder_phase_acc_0_we1 sc_out sc_logic 1 signal 20 } 
	{ p_ZL17encoder_phase_acc_0_d1 sc_out sc_lv 16 signal 20 } 
	{ p_ZL13encoder_frame_1_address0 sc_out sc_lv 9 signal 21 } 
	{ p_ZL13encoder_frame_1_ce0 sc_out sc_logic 1 signal 21 } 
	{ p_ZL13encoder_frame_1_q0 sc_in sc_lv 8 signal 21 } 
}
set NewPortList {[ 
	{ "name": "ap_clk", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "clock", "bundle":{"name": "ap_clk", "role": "default" }} , 
 	{ "name": "ap_rst", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "reset", "bundle":{"name": "ap_rst", "role": "default" }} , 
 	{ "name": "ap_start", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "start", "bundle":{"name": "ap_start", "role": "default" }} , 
 	{ "name": "ap_done", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "predone", "bundle":{"name": "ap_done", "role": "default" }} , 
 	{ "name": "ap_idle", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "done", "bundle":{"name": "ap_idle", "role": "default" }} , 
 	{ "name": "ap_ready", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "ready", "bundle":{"name": "ap_ready", "role": "default" }} , 
 	{ "name": "config_encoding_type_val", "direction": "in", "datatype": "sc_lv", "bitwidth":4, "type": "signal", "bundle":{"name": "config_encoding_type_val", "role": "default" }} , 
 	{ "name": "config_two_neuron_enable_val", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "config_two_neuron_enable_val", "role": "default" }} , 
 	{ "name": "config_baseline_val", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "config_baseline_val", "role": "default" }} , 
 	{ "name": "config_rate_scale_val", "direction": "in", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "config_rate_scale_val", "role": "default" }} , 
 	{ "name": "config_latency_window_val", "direction": "in", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "config_latency_window_val", "role": "default" }} , 
 	{ "name": "config_delta_threshold_val", "direction": "in", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "config_delta_threshold_val", "role": "default" }} , 
 	{ "name": "config_delta_decay_val", "direction": "in", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "config_delta_decay_val", "role": "default" }} , 
 	{ "name": "config_num_channels_val", "direction": "in", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "config_num_channels_val", "role": "default" }} , 
 	{ "name": "config_default_weight_val", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "config_default_weight_val", "role": "default" }} , 
 	{ "name": "time_r", "direction": "in", "datatype": "sc_lv", "bitwidth":32, "type": "signal", "bundle":{"name": "time_r", "role": "default" }} , 
 	{ "name": "encoder_spikes_din", "direction": "out", "datatype": "sc_lv", "bitwidth":41, "type": "signal", "bundle":{"name": "encoder_spikes", "role": "din" }} , 
 	{ "name": "encoder_spikes_full_n", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "encoder_spikes", "role": "full_n" }} , 
 	{ "name": "encoder_spikes_write", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "encoder_spikes", "role": "write" }} , 
 	{ "name": "encoder_frame_loaded", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "encoder_frame_loaded", "role": "default" }} , 
 	{ "name": "latency_window_counter_i", "direction": "in", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "latency_window_counter", "role": "i" }} , 
 	{ "name": "latency_window_counter_o", "direction": "out", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "latency_window_counter", "role": "o" }} , 
 	{ "name": "latency_window_counter_o_ap_vld", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "outvld", "bundle":{"name": "latency_window_counter", "role": "o_ap_vld" }} , 
 	{ "name": "p_ZL13encoder_frame_0_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_0", "role": "address0" }} , 
 	{ "name": "p_ZL13encoder_frame_0_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_0", "role": "ce0" }} , 
 	{ "name": "p_ZL13encoder_frame_0_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_0", "role": "q0" }} , 
 	{ "name": "encoder_spike_counter_i", "direction": "in", "datatype": "sc_lv", "bitwidth":32, "type": "signal", "bundle":{"name": "encoder_spike_counter", "role": "i" }} , 
 	{ "name": "encoder_spike_counter_o", "direction": "out", "datatype": "sc_lv", "bitwidth":32, "type": "signal", "bundle":{"name": "encoder_spike_counter", "role": "o" }} , 
 	{ "name": "encoder_spike_counter_o_ap_vld", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "outvld", "bundle":{"name": "encoder_spike_counter", "role": "o_ap_vld" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_1_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_1", "role": "address0" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_1_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_1", "role": "ce0" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_1_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_1", "role": "q0" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_1_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_1", "role": "address1" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_1_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_1", "role": "ce1" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_1_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_1", "role": "we1" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_1_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_1", "role": "d1" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_1_q1", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_1", "role": "q1" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_0_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_0", "role": "address0" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_0_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_0", "role": "ce0" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_0_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_0", "role": "q0" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_0_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_0", "role": "address1" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_0_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_0", "role": "ce1" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_0_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_0", "role": "we1" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_0_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_0", "role": "d1" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_0_q1", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_0", "role": "q1" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_0_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_0", "role": "address0" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_0_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_0", "role": "ce0" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_0_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":32, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_0", "role": "q0" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_0_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_0", "role": "address1" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_0_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_0", "role": "ce1" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_0_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_0", "role": "we1" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_0_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":32, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_0", "role": "d1" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_1_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_1", "role": "address0" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_1_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_1", "role": "ce0" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_1_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":32, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_1", "role": "q0" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_1_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_1", "role": "address1" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_1_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_1", "role": "ce1" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_1_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_1", "role": "we1" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_1_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":32, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_1", "role": "d1" }} , 
 	{ "name": "p_ZL17encoder_phase_acc_1_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL17encoder_phase_acc_1", "role": "address0" }} , 
 	{ "name": "p_ZL17encoder_phase_acc_1_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL17encoder_phase_acc_1", "role": "ce0" }} , 
 	{ "name": "p_ZL17encoder_phase_acc_1_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "p_ZL17encoder_phase_acc_1", "role": "q0" }} , 
 	{ "name": "p_ZL17encoder_phase_acc_1_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL17encoder_phase_acc_1", "role": "address1" }} , 
 	{ "name": "p_ZL17encoder_phase_acc_1_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL17encoder_phase_acc_1", "role": "ce1" }} , 
 	{ "name": "p_ZL17encoder_phase_acc_1_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL17encoder_phase_acc_1", "role": "we1" }} , 
 	{ "name": "p_ZL17encoder_phase_acc_1_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "p_ZL17encoder_phase_acc_1", "role": "d1" }} , 
 	{ "name": "p_ZL17encoder_phase_acc_0_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL17encoder_phase_acc_0", "role": "address0" }} , 
 	{ "name": "p_ZL17encoder_phase_acc_0_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL17encoder_phase_acc_0", "role": "ce0" }} , 
 	{ "name": "p_ZL17encoder_phase_acc_0_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "p_ZL17encoder_phase_acc_0", "role": "q0" }} , 
 	{ "name": "p_ZL17encoder_phase_acc_0_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL17encoder_phase_acc_0", "role": "address1" }} , 
 	{ "name": "p_ZL17encoder_phase_acc_0_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL17encoder_phase_acc_0", "role": "ce1" }} , 
 	{ "name": "p_ZL17encoder_phase_acc_0_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL17encoder_phase_acc_0", "role": "we1" }} , 
 	{ "name": "p_ZL17encoder_phase_acc_0_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "p_ZL17encoder_phase_acc_0", "role": "d1" }} , 
 	{ "name": "p_ZL13encoder_frame_1_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_1", "role": "address0" }} , 
 	{ "name": "p_ZL13encoder_frame_1_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_1", "role": "ce0" }} , 
 	{ "name": "p_ZL13encoder_frame_1_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_1", "role": "q0" }}  ]}

set ArgLastReadFirstWriteLatency {
	run_encoder_once {
		config_encoding_type_val {Type I LastRead 0 FirstWrite -1}
		config_two_neuron_enable_val {Type I LastRead 0 FirstWrite -1}
		config_baseline_val {Type I LastRead 0 FirstWrite -1}
		config_rate_scale_val {Type I LastRead 0 FirstWrite -1}
		config_latency_window_val {Type I LastRead 0 FirstWrite -1}
		config_delta_threshold_val {Type I LastRead 0 FirstWrite -1}
		config_delta_decay_val {Type I LastRead 0 FirstWrite -1}
		config_num_channels_val {Type I LastRead 0 FirstWrite -1}
		config_default_weight_val {Type I LastRead 0 FirstWrite -1}
		time_r {Type I LastRead 0 FirstWrite -1}
		encoder_spikes {Type O LastRead 8 FirstWrite 5}
		encoder_frame_loaded {Type I LastRead 0 FirstWrite -1}
		latency_window_counter {Type IO LastRead 0 FirstWrite 0}
		p_ZL13encoder_frame_0 {Type I LastRead 0 FirstWrite -1}
		lfsr {Type IO LastRead -1 FirstWrite -1}
		encoder_spike_counter {Type IO LastRead 8 FirstWrite 5}
		p_ZL22encoder_temporal_fired_1 {Type IO LastRead 2 FirstWrite 2}
		p_ZL22encoder_temporal_fired_0 {Type IO LastRead 2 FirstWrite 2}
		p_ZL22encoder_temporal_start_0 {Type IO LastRead 3 FirstWrite 0}
		p_ZL22encoder_temporal_start_1 {Type IO LastRead 3 FirstWrite 0}
		p_ZL17encoder_phase_acc_1 {Type IO LastRead 3 FirstWrite 3}
		p_ZL17encoder_phase_acc_0 {Type IO LastRead 3 FirstWrite 3}
		p_ZL13encoder_frame_1 {Type I LastRead 0 FirstWrite -1}}
	run_encoder_once_Pipeline_ENCODER_LOOP {
		time_r {Type I LastRead 0 FirstWrite -1}
		config_num_channels_val {Type I LastRead 0 FirstWrite -1}
		config_baseline_val {Type I LastRead 0 FirstWrite -1}
		config_encoding_type_val {Type I LastRead 0 FirstWrite -1}
		config_two_neuron_enable_val {Type I LastRead 0 FirstWrite -1}
		zext_ln108 {Type I LastRead 0 FirstWrite -1}
		encoder_spikes {Type O LastRead 8 FirstWrite 5}
		config_default_weight_val {Type I LastRead 0 FirstWrite -1}
		latency_window_reset_1 {Type I LastRead 0 FirstWrite -1}
		zext_ln137_13 {Type I LastRead 0 FirstWrite -1}
		config_delta_decay_val {Type I LastRead 0 FirstWrite -1}
		config_delta_threshold_val {Type I LastRead 0 FirstWrite -1}
		p_ZL13encoder_frame_0 {Type I LastRead 0 FirstWrite -1}
		lfsr {Type IO LastRead -1 FirstWrite -1}
		encoder_spike_counter {Type IO LastRead 8 FirstWrite 5}
		p_ZL22encoder_temporal_fired_1 {Type IO LastRead 2 FirstWrite 2}
		p_ZL22encoder_temporal_fired_0 {Type IO LastRead 2 FirstWrite 2}
		p_ZL22encoder_temporal_start_0 {Type IO LastRead 3 FirstWrite 0}
		p_ZL22encoder_temporal_start_1 {Type IO LastRead 3 FirstWrite 0}
		p_ZL17encoder_phase_acc_1 {Type IO LastRead 3 FirstWrite 3}
		p_ZL17encoder_phase_acc_0 {Type IO LastRead 3 FirstWrite 3}
		p_ZL13encoder_frame_1 {Type I LastRead 0 FirstWrite -1}}}

set hasDtUnsupportedChannel 0

set PerformanceInfo {[
	{"Name" : "Latency", "Min" : "1", "Max" : "1576"}
	, {"Name" : "Interval", "Min" : "1", "Max" : "1576"}
]}

set PipelineEnableSignalInfo {[
]}

set Spec2ImplPortList { 
	config_encoding_type_val { ap_none {  { config_encoding_type_val in_data 0 4 } } }
	config_two_neuron_enable_val { ap_none {  { config_two_neuron_enable_val in_data 0 1 } } }
	config_baseline_val { ap_none {  { config_baseline_val in_data 0 8 } } }
	config_rate_scale_val { ap_none {  { config_rate_scale_val in_data 0 16 } } }
	config_latency_window_val { ap_none {  { config_latency_window_val in_data 0 16 } } }
	config_delta_threshold_val { ap_none {  { config_delta_threshold_val in_data 0 16 } } }
	config_delta_decay_val { ap_none {  { config_delta_decay_val in_data 0 16 } } }
	config_num_channels_val { ap_none {  { config_num_channels_val in_data 0 16 } } }
	config_default_weight_val { ap_none {  { config_default_weight_val in_data 0 8 } } }
	time_r { ap_none {  { time_r in_data 0 32 } } }
	encoder_spikes { ap_fifo {  { encoder_spikes_din fifo_data_out 1 41 }  { encoder_spikes_full_n fifo_status_empty 0 1 }  { encoder_spikes_write fifo_data_in 1 1 } } }
	encoder_frame_loaded { ap_none {  { encoder_frame_loaded in_data 0 1 } } }
	latency_window_counter { ap_ovld {  { latency_window_counter_i in_data 0 16 }  { latency_window_counter_o out_data 1 16 }  { latency_window_counter_o_ap_vld out_vld 1 1 } } }
	p_ZL13encoder_frame_0 { ap_memory {  { p_ZL13encoder_frame_0_address0 mem_address 1 9 }  { p_ZL13encoder_frame_0_ce0 mem_ce 1 1 }  { p_ZL13encoder_frame_0_q0 mem_dout 0 8 } } }
	encoder_spike_counter { ap_ovld {  { encoder_spike_counter_i in_data 0 32 }  { encoder_spike_counter_o out_data 1 32 }  { encoder_spike_counter_o_ap_vld out_vld 1 1 } } }
	p_ZL22encoder_temporal_fired_1 { ap_memory {  { p_ZL22encoder_temporal_fired_1_address0 mem_address 1 9 }  { p_ZL22encoder_temporal_fired_1_ce0 mem_ce 1 1 }  { p_ZL22encoder_temporal_fired_1_q0 mem_dout 0 1 }  { p_ZL22encoder_temporal_fired_1_address1 MemPortADDR2 1 9 }  { p_ZL22encoder_temporal_fired_1_ce1 MemPortCE2 1 1 }  { p_ZL22encoder_temporal_fired_1_we1 MemPortWE2 1 1 }  { p_ZL22encoder_temporal_fired_1_d1 MemPortDIN2 1 1 }  { p_ZL22encoder_temporal_fired_1_q1 MemPortDOUT2 0 1 } } }
	p_ZL22encoder_temporal_fired_0 { ap_memory {  { p_ZL22encoder_temporal_fired_0_address0 mem_address 1 9 }  { p_ZL22encoder_temporal_fired_0_ce0 mem_ce 1 1 }  { p_ZL22encoder_temporal_fired_0_q0 mem_dout 0 1 }  { p_ZL22encoder_temporal_fired_0_address1 MemPortADDR2 1 9 }  { p_ZL22encoder_temporal_fired_0_ce1 MemPortCE2 1 1 }  { p_ZL22encoder_temporal_fired_0_we1 MemPortWE2 1 1 }  { p_ZL22encoder_temporal_fired_0_d1 MemPortDIN2 1 1 }  { p_ZL22encoder_temporal_fired_0_q1 MemPortDOUT2 0 1 } } }
	p_ZL22encoder_temporal_start_0 { ap_memory {  { p_ZL22encoder_temporal_start_0_address0 mem_address 1 9 }  { p_ZL22encoder_temporal_start_0_ce0 mem_ce 1 1 }  { p_ZL22encoder_temporal_start_0_q0 mem_dout 0 32 }  { p_ZL22encoder_temporal_start_0_address1 MemPortADDR2 1 9 }  { p_ZL22encoder_temporal_start_0_ce1 MemPortCE2 1 1 }  { p_ZL22encoder_temporal_start_0_we1 MemPortWE2 1 1 }  { p_ZL22encoder_temporal_start_0_d1 MemPortDIN2 1 32 } } }
	p_ZL22encoder_temporal_start_1 { ap_memory {  { p_ZL22encoder_temporal_start_1_address0 mem_address 1 9 }  { p_ZL22encoder_temporal_start_1_ce0 mem_ce 1 1 }  { p_ZL22encoder_temporal_start_1_q0 mem_dout 0 32 }  { p_ZL22encoder_temporal_start_1_address1 MemPortADDR2 1 9 }  { p_ZL22encoder_temporal_start_1_ce1 MemPortCE2 1 1 }  { p_ZL22encoder_temporal_start_1_we1 MemPortWE2 1 1 }  { p_ZL22encoder_temporal_start_1_d1 MemPortDIN2 1 32 } } }
	p_ZL17encoder_phase_acc_1 { ap_memory {  { p_ZL17encoder_phase_acc_1_address0 mem_address 1 9 }  { p_ZL17encoder_phase_acc_1_ce0 mem_ce 1 1 }  { p_ZL17encoder_phase_acc_1_q0 mem_dout 0 16 }  { p_ZL17encoder_phase_acc_1_address1 MemPortADDR2 1 9 }  { p_ZL17encoder_phase_acc_1_ce1 MemPortCE2 1 1 }  { p_ZL17encoder_phase_acc_1_we1 MemPortWE2 1 1 }  { p_ZL17encoder_phase_acc_1_d1 MemPortDIN2 1 16 } } }
	p_ZL17encoder_phase_acc_0 { ap_memory {  { p_ZL17encoder_phase_acc_0_address0 mem_address 1 9 }  { p_ZL17encoder_phase_acc_0_ce0 mem_ce 1 1 }  { p_ZL17encoder_phase_acc_0_q0 mem_dout 0 16 }  { p_ZL17encoder_phase_acc_0_address1 MemPortADDR2 1 9 }  { p_ZL17encoder_phase_acc_0_ce1 MemPortCE2 1 1 }  { p_ZL17encoder_phase_acc_0_we1 MemPortWE2 1 1 }  { p_ZL17encoder_phase_acc_0_d1 MemPortDIN2 1 16 } } }
	p_ZL13encoder_frame_1 { ap_memory {  { p_ZL13encoder_frame_1_address0 mem_address 1 9 }  { p_ZL13encoder_frame_1_ce0 mem_ce 1 1 }  { p_ZL13encoder_frame_1_q0 mem_dout 0 8 } } }
}
