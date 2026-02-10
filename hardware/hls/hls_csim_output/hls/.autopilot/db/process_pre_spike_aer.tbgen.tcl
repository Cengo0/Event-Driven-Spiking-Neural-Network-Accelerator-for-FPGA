set moduleName process_pre_spike_aer
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
set C_modelName {process_pre_spike_aer}
set C_modelType { void 0 }
set ap_memory_interface_dict [dict create]
dict set ap_memory_interface_dict pre_traces_trace_0 { MEM_WIDTH 8 MEM_SIZE 128 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 0 }
dict set ap_memory_interface_dict pre_traces_trace_1 { MEM_WIDTH 8 MEM_SIZE 128 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 0 }
dict set ap_memory_interface_dict pre_traces_last_spike_time_0 { MEM_WIDTH 16 MEM_SIZE 256 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 0 }
dict set ap_memory_interface_dict pre_traces_last_spike_time_1 { MEM_WIDTH 16 MEM_SIZE 256 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 0 }
dict set ap_memory_interface_dict EXP_DECAY_LUT { MEM_WIDTH 8 MEM_SIZE 16 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict post_traces_trace_1 { MEM_WIDTH 8 MEM_SIZE 128 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict post_traces_last_spike_time_1 { MEM_WIDTH 16 MEM_SIZE 256 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict post_traces_trace_0 { MEM_WIDTH 8 MEM_SIZE 128 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict post_traces_last_spike_time_0 { MEM_WIDTH 16 MEM_SIZE 256 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict p_ZL13weight_memory_0 { MEM_WIDTH 8 MEM_SIZE 32768 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict p_ZL13weight_memory_1 { MEM_WIDTH 8 MEM_SIZE 32768 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
set C_modelArgList {
	{ pre_id int 8 regular  }
	{ current_time int 16 regular  }
	{ pre_traces_trace_0 int 8 regular {array 128 { 1 0 } 1 1 } {global 2}  }
	{ pre_traces_trace_1 int 8 regular {array 128 { 1 0 } 1 1 } {global 2}  }
	{ pre_traces_last_spike_time_0 int 16 regular {array 128 { 1 0 } 1 1 } {global 2}  }
	{ pre_traces_last_spike_time_1 int 16 regular {array 128 { 1 0 } 1 1 } {global 2}  }
	{ EXP_DECAY_LUT int 8 regular {array 16 { 1 } 1 1 } {global 0}  }
	{ post_traces_trace_1 int 8 regular {array 128 { 1 3 } 1 1 } {global 0}  }
	{ post_traces_last_spike_time_1 int 16 regular {array 128 { 1 3 } 1 1 } {global 0}  }
	{ post_traces_trace_0 int 8 regular {array 128 { 1 3 } 1 1 } {global 0}  }
	{ post_traces_last_spike_time_0 int 16 regular {array 128 { 1 3 } 1 1 } {global 0}  }
	{ p_ZL13weight_memory_0 int 8 regular {array 32768 { 1 0 } 1 1 } {global 2}  }
	{ p_ZL13weight_memory_1 int 8 regular {array 32768 { 1 0 } 1 1 } {global 2}  }
}
set hasAXIMCache 0
set l_AXIML2Cache [list]
set AXIMCacheInstDict [dict create]
set C_modelArgMapList {[ 
	{ "Name" : "pre_id", "interface" : "wire", "bitwidth" : 8, "direction" : "READONLY"} , 
 	{ "Name" : "current_time", "interface" : "wire", "bitwidth" : 16, "direction" : "READONLY"} , 
 	{ "Name" : "pre_traces_trace_0", "interface" : "memory", "bitwidth" : 8, "direction" : "READWRITE", "extern" : 0} , 
 	{ "Name" : "pre_traces_trace_1", "interface" : "memory", "bitwidth" : 8, "direction" : "READWRITE", "extern" : 0} , 
 	{ "Name" : "pre_traces_last_spike_time_0", "interface" : "memory", "bitwidth" : 16, "direction" : "READWRITE", "extern" : 0} , 
 	{ "Name" : "pre_traces_last_spike_time_1", "interface" : "memory", "bitwidth" : 16, "direction" : "READWRITE", "extern" : 0} , 
 	{ "Name" : "EXP_DECAY_LUT", "interface" : "memory", "bitwidth" : 8, "direction" : "READONLY", "extern" : 0} , 
 	{ "Name" : "post_traces_trace_1", "interface" : "memory", "bitwidth" : 8, "direction" : "READONLY", "extern" : 0} , 
 	{ "Name" : "post_traces_last_spike_time_1", "interface" : "memory", "bitwidth" : 16, "direction" : "READONLY", "extern" : 0} , 
 	{ "Name" : "post_traces_trace_0", "interface" : "memory", "bitwidth" : 8, "direction" : "READONLY", "extern" : 0} , 
 	{ "Name" : "post_traces_last_spike_time_0", "interface" : "memory", "bitwidth" : 16, "direction" : "READONLY", "extern" : 0} , 
 	{ "Name" : "p_ZL13weight_memory_0", "interface" : "memory", "bitwidth" : 8, "direction" : "READWRITE", "extern" : 0} , 
 	{ "Name" : "p_ZL13weight_memory_1", "interface" : "memory", "bitwidth" : 8, "direction" : "READWRITE", "extern" : 0} ]}
# RTL Port declarations: 
set portNum 65
set portList { 
	{ ap_clk sc_in sc_logic 1 clock -1 } 
	{ ap_rst sc_in sc_logic 1 reset -1 active_high_sync } 
	{ ap_start sc_in sc_logic 1 start -1 } 
	{ ap_done sc_out sc_logic 1 predone -1 } 
	{ ap_idle sc_out sc_logic 1 done -1 } 
	{ ap_ready sc_out sc_logic 1 ready -1 } 
	{ pre_id sc_in sc_lv 8 signal 0 } 
	{ current_time sc_in sc_lv 16 signal 1 } 
	{ pre_traces_trace_0_address0 sc_out sc_lv 7 signal 2 } 
	{ pre_traces_trace_0_ce0 sc_out sc_logic 1 signal 2 } 
	{ pre_traces_trace_0_q0 sc_in sc_lv 8 signal 2 } 
	{ pre_traces_trace_0_address1 sc_out sc_lv 7 signal 2 } 
	{ pre_traces_trace_0_ce1 sc_out sc_logic 1 signal 2 } 
	{ pre_traces_trace_0_we1 sc_out sc_logic 1 signal 2 } 
	{ pre_traces_trace_0_d1 sc_out sc_lv 8 signal 2 } 
	{ pre_traces_trace_1_address0 sc_out sc_lv 7 signal 3 } 
	{ pre_traces_trace_1_ce0 sc_out sc_logic 1 signal 3 } 
	{ pre_traces_trace_1_q0 sc_in sc_lv 8 signal 3 } 
	{ pre_traces_trace_1_address1 sc_out sc_lv 7 signal 3 } 
	{ pre_traces_trace_1_ce1 sc_out sc_logic 1 signal 3 } 
	{ pre_traces_trace_1_we1 sc_out sc_logic 1 signal 3 } 
	{ pre_traces_trace_1_d1 sc_out sc_lv 8 signal 3 } 
	{ pre_traces_last_spike_time_0_address0 sc_out sc_lv 7 signal 4 } 
	{ pre_traces_last_spike_time_0_ce0 sc_out sc_logic 1 signal 4 } 
	{ pre_traces_last_spike_time_0_q0 sc_in sc_lv 16 signal 4 } 
	{ pre_traces_last_spike_time_0_address1 sc_out sc_lv 7 signal 4 } 
	{ pre_traces_last_spike_time_0_ce1 sc_out sc_logic 1 signal 4 } 
	{ pre_traces_last_spike_time_0_we1 sc_out sc_logic 1 signal 4 } 
	{ pre_traces_last_spike_time_0_d1 sc_out sc_lv 16 signal 4 } 
	{ pre_traces_last_spike_time_1_address0 sc_out sc_lv 7 signal 5 } 
	{ pre_traces_last_spike_time_1_ce0 sc_out sc_logic 1 signal 5 } 
	{ pre_traces_last_spike_time_1_q0 sc_in sc_lv 16 signal 5 } 
	{ pre_traces_last_spike_time_1_address1 sc_out sc_lv 7 signal 5 } 
	{ pre_traces_last_spike_time_1_ce1 sc_out sc_logic 1 signal 5 } 
	{ pre_traces_last_spike_time_1_we1 sc_out sc_logic 1 signal 5 } 
	{ pre_traces_last_spike_time_1_d1 sc_out sc_lv 16 signal 5 } 
	{ EXP_DECAY_LUT_address0 sc_out sc_lv 4 signal 6 } 
	{ EXP_DECAY_LUT_ce0 sc_out sc_logic 1 signal 6 } 
	{ EXP_DECAY_LUT_q0 sc_in sc_lv 8 signal 6 } 
	{ post_traces_trace_1_address0 sc_out sc_lv 7 signal 7 } 
	{ post_traces_trace_1_ce0 sc_out sc_logic 1 signal 7 } 
	{ post_traces_trace_1_q0 sc_in sc_lv 8 signal 7 } 
	{ post_traces_last_spike_time_1_address0 sc_out sc_lv 7 signal 8 } 
	{ post_traces_last_spike_time_1_ce0 sc_out sc_logic 1 signal 8 } 
	{ post_traces_last_spike_time_1_q0 sc_in sc_lv 16 signal 8 } 
	{ post_traces_trace_0_address0 sc_out sc_lv 7 signal 9 } 
	{ post_traces_trace_0_ce0 sc_out sc_logic 1 signal 9 } 
	{ post_traces_trace_0_q0 sc_in sc_lv 8 signal 9 } 
	{ post_traces_last_spike_time_0_address0 sc_out sc_lv 7 signal 10 } 
	{ post_traces_last_spike_time_0_ce0 sc_out sc_logic 1 signal 10 } 
	{ post_traces_last_spike_time_0_q0 sc_in sc_lv 16 signal 10 } 
	{ p_ZL13weight_memory_0_address0 sc_out sc_lv 15 signal 11 } 
	{ p_ZL13weight_memory_0_ce0 sc_out sc_logic 1 signal 11 } 
	{ p_ZL13weight_memory_0_q0 sc_in sc_lv 8 signal 11 } 
	{ p_ZL13weight_memory_0_address1 sc_out sc_lv 15 signal 11 } 
	{ p_ZL13weight_memory_0_ce1 sc_out sc_logic 1 signal 11 } 
	{ p_ZL13weight_memory_0_we1 sc_out sc_logic 1 signal 11 } 
	{ p_ZL13weight_memory_0_d1 sc_out sc_lv 8 signal 11 } 
	{ p_ZL13weight_memory_1_address0 sc_out sc_lv 15 signal 12 } 
	{ p_ZL13weight_memory_1_ce0 sc_out sc_logic 1 signal 12 } 
	{ p_ZL13weight_memory_1_q0 sc_in sc_lv 8 signal 12 } 
	{ p_ZL13weight_memory_1_address1 sc_out sc_lv 15 signal 12 } 
	{ p_ZL13weight_memory_1_ce1 sc_out sc_logic 1 signal 12 } 
	{ p_ZL13weight_memory_1_we1 sc_out sc_logic 1 signal 12 } 
	{ p_ZL13weight_memory_1_d1 sc_out sc_lv 8 signal 12 } 
}
set NewPortList {[ 
	{ "name": "ap_clk", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "clock", "bundle":{"name": "ap_clk", "role": "default" }} , 
 	{ "name": "ap_rst", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "reset", "bundle":{"name": "ap_rst", "role": "default" }} , 
 	{ "name": "ap_start", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "start", "bundle":{"name": "ap_start", "role": "default" }} , 
 	{ "name": "ap_done", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "predone", "bundle":{"name": "ap_done", "role": "default" }} , 
 	{ "name": "ap_idle", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "done", "bundle":{"name": "ap_idle", "role": "default" }} , 
 	{ "name": "ap_ready", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "ready", "bundle":{"name": "ap_ready", "role": "default" }} , 
 	{ "name": "pre_id", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "pre_id", "role": "default" }} , 
 	{ "name": "current_time", "direction": "in", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "current_time", "role": "default" }} , 
 	{ "name": "pre_traces_trace_0_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "pre_traces_trace_0", "role": "address0" }} , 
 	{ "name": "pre_traces_trace_0_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_trace_0", "role": "ce0" }} , 
 	{ "name": "pre_traces_trace_0_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "pre_traces_trace_0", "role": "q0" }} , 
 	{ "name": "pre_traces_trace_0_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "pre_traces_trace_0", "role": "address1" }} , 
 	{ "name": "pre_traces_trace_0_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_trace_0", "role": "ce1" }} , 
 	{ "name": "pre_traces_trace_0_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_trace_0", "role": "we1" }} , 
 	{ "name": "pre_traces_trace_0_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "pre_traces_trace_0", "role": "d1" }} , 
 	{ "name": "pre_traces_trace_1_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "pre_traces_trace_1", "role": "address0" }} , 
 	{ "name": "pre_traces_trace_1_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_trace_1", "role": "ce0" }} , 
 	{ "name": "pre_traces_trace_1_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "pre_traces_trace_1", "role": "q0" }} , 
 	{ "name": "pre_traces_trace_1_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "pre_traces_trace_1", "role": "address1" }} , 
 	{ "name": "pre_traces_trace_1_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_trace_1", "role": "ce1" }} , 
 	{ "name": "pre_traces_trace_1_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_trace_1", "role": "we1" }} , 
 	{ "name": "pre_traces_trace_1_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "pre_traces_trace_1", "role": "d1" }} , 
 	{ "name": "pre_traces_last_spike_time_0_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_0", "role": "address0" }} , 
 	{ "name": "pre_traces_last_spike_time_0_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_0", "role": "ce0" }} , 
 	{ "name": "pre_traces_last_spike_time_0_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_0", "role": "q0" }} , 
 	{ "name": "pre_traces_last_spike_time_0_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_0", "role": "address1" }} , 
 	{ "name": "pre_traces_last_spike_time_0_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_0", "role": "ce1" }} , 
 	{ "name": "pre_traces_last_spike_time_0_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_0", "role": "we1" }} , 
 	{ "name": "pre_traces_last_spike_time_0_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_0", "role": "d1" }} , 
 	{ "name": "pre_traces_last_spike_time_1_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_1", "role": "address0" }} , 
 	{ "name": "pre_traces_last_spike_time_1_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_1", "role": "ce0" }} , 
 	{ "name": "pre_traces_last_spike_time_1_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_1", "role": "q0" }} , 
 	{ "name": "pre_traces_last_spike_time_1_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_1", "role": "address1" }} , 
 	{ "name": "pre_traces_last_spike_time_1_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_1", "role": "ce1" }} , 
 	{ "name": "pre_traces_last_spike_time_1_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_1", "role": "we1" }} , 
 	{ "name": "pre_traces_last_spike_time_1_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_1", "role": "d1" }} , 
 	{ "name": "EXP_DECAY_LUT_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":4, "type": "signal", "bundle":{"name": "EXP_DECAY_LUT", "role": "address0" }} , 
 	{ "name": "EXP_DECAY_LUT_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "EXP_DECAY_LUT", "role": "ce0" }} , 
 	{ "name": "EXP_DECAY_LUT_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "EXP_DECAY_LUT", "role": "q0" }} , 
 	{ "name": "post_traces_trace_1_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "post_traces_trace_1", "role": "address0" }} , 
 	{ "name": "post_traces_trace_1_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "post_traces_trace_1", "role": "ce0" }} , 
 	{ "name": "post_traces_trace_1_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "post_traces_trace_1", "role": "q0" }} , 
 	{ "name": "post_traces_last_spike_time_1_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "post_traces_last_spike_time_1", "role": "address0" }} , 
 	{ "name": "post_traces_last_spike_time_1_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "post_traces_last_spike_time_1", "role": "ce0" }} , 
 	{ "name": "post_traces_last_spike_time_1_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "post_traces_last_spike_time_1", "role": "q0" }} , 
 	{ "name": "post_traces_trace_0_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "post_traces_trace_0", "role": "address0" }} , 
 	{ "name": "post_traces_trace_0_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "post_traces_trace_0", "role": "ce0" }} , 
 	{ "name": "post_traces_trace_0_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "post_traces_trace_0", "role": "q0" }} , 
 	{ "name": "post_traces_last_spike_time_0_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "post_traces_last_spike_time_0", "role": "address0" }} , 
 	{ "name": "post_traces_last_spike_time_0_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "post_traces_last_spike_time_0", "role": "ce0" }} , 
 	{ "name": "post_traces_last_spike_time_0_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "post_traces_last_spike_time_0", "role": "q0" }} , 
 	{ "name": "p_ZL13weight_memory_0_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":15, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_0", "role": "address0" }} , 
 	{ "name": "p_ZL13weight_memory_0_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_0", "role": "ce0" }} , 
 	{ "name": "p_ZL13weight_memory_0_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_0", "role": "q0" }} , 
 	{ "name": "p_ZL13weight_memory_0_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":15, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_0", "role": "address1" }} , 
 	{ "name": "p_ZL13weight_memory_0_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_0", "role": "ce1" }} , 
 	{ "name": "p_ZL13weight_memory_0_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_0", "role": "we1" }} , 
 	{ "name": "p_ZL13weight_memory_0_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_0", "role": "d1" }} , 
 	{ "name": "p_ZL13weight_memory_1_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":15, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_1", "role": "address0" }} , 
 	{ "name": "p_ZL13weight_memory_1_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_1", "role": "ce0" }} , 
 	{ "name": "p_ZL13weight_memory_1_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_1", "role": "q0" }} , 
 	{ "name": "p_ZL13weight_memory_1_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":15, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_1", "role": "address1" }} , 
 	{ "name": "p_ZL13weight_memory_1_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_1", "role": "ce1" }} , 
 	{ "name": "p_ZL13weight_memory_1_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_1", "role": "we1" }} , 
 	{ "name": "p_ZL13weight_memory_1_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_1", "role": "d1" }}  ]}

set ArgLastReadFirstWriteLatency {
	process_pre_spike_aer {
		pre_id {Type I LastRead 0 FirstWrite -1}
		current_time {Type I LastRead 2 FirstWrite -1}
		pre_traces_trace_0 {Type IO LastRead 2 FirstWrite 5}
		pre_traces_trace_1 {Type IO LastRead 2 FirstWrite 5}
		pre_traces_last_spike_time_0 {Type IO LastRead 0 FirstWrite 4}
		pre_traces_last_spike_time_1 {Type IO LastRead 0 FirstWrite 4}
		EXP_DECAY_LUT {Type I LastRead 2 FirstWrite -1}
		post_traces_trace_1 {Type I LastRead 2 FirstWrite -1}
		post_traces_last_spike_time_1 {Type I LastRead 0 FirstWrite -1}
		post_traces_trace_0 {Type I LastRead 0 FirstWrite -1}
		post_traces_last_spike_time_0 {Type I LastRead 0 FirstWrite -1}
		p_ZL13weight_memory_0 {Type IO LastRead 4 FirstWrite 7}
		p_ZL13weight_memory_1 {Type IO LastRead 5 FirstWrite 8}}
	process_pre_spike_aer_Pipeline_LTD_LOOP {
		current_time {Type I LastRead 0 FirstWrite -1}
		pre_id {Type I LastRead 0 FirstWrite -1}
		post_traces_trace_1 {Type I LastRead 2 FirstWrite -1}
		post_traces_last_spike_time_1 {Type I LastRead 0 FirstWrite -1}
		EXP_DECAY_LUT {Type I LastRead -1 FirstWrite -1}
		post_traces_trace_0 {Type I LastRead 0 FirstWrite -1}
		post_traces_last_spike_time_0 {Type I LastRead 0 FirstWrite -1}
		p_ZL13weight_memory_0 {Type IO LastRead 4 FirstWrite 7}
		p_ZL13weight_memory_1 {Type IO LastRead 5 FirstWrite 8}}}

set hasDtUnsupportedChannel 0

set PerformanceInfo {[
	{"Name" : "Latency", "Min" : "271", "Max" : "271"}
	, {"Name" : "Interval", "Min" : "271", "Max" : "271"}
]}

set PipelineEnableSignalInfo {[
]}

set Spec2ImplPortList { 
	pre_id { ap_none {  { pre_id in_data 0 8 } } }
	current_time { ap_none {  { current_time in_data 0 16 } } }
	pre_traces_trace_0 { ap_memory {  { pre_traces_trace_0_address0 mem_address 1 7 }  { pre_traces_trace_0_ce0 mem_ce 1 1 }  { pre_traces_trace_0_q0 mem_dout 0 8 }  { pre_traces_trace_0_address1 MemPortADDR2 1 7 }  { pre_traces_trace_0_ce1 MemPortCE2 1 1 }  { pre_traces_trace_0_we1 MemPortWE2 1 1 }  { pre_traces_trace_0_d1 MemPortDIN2 1 8 } } }
	pre_traces_trace_1 { ap_memory {  { pre_traces_trace_1_address0 mem_address 1 7 }  { pre_traces_trace_1_ce0 mem_ce 1 1 }  { pre_traces_trace_1_q0 mem_dout 0 8 }  { pre_traces_trace_1_address1 MemPortADDR2 1 7 }  { pre_traces_trace_1_ce1 MemPortCE2 1 1 }  { pre_traces_trace_1_we1 MemPortWE2 1 1 }  { pre_traces_trace_1_d1 MemPortDIN2 1 8 } } }
	pre_traces_last_spike_time_0 { ap_memory {  { pre_traces_last_spike_time_0_address0 mem_address 1 7 }  { pre_traces_last_spike_time_0_ce0 mem_ce 1 1 }  { pre_traces_last_spike_time_0_q0 mem_dout 0 16 }  { pre_traces_last_spike_time_0_address1 MemPortADDR2 1 7 }  { pre_traces_last_spike_time_0_ce1 MemPortCE2 1 1 }  { pre_traces_last_spike_time_0_we1 MemPortWE2 1 1 }  { pre_traces_last_spike_time_0_d1 MemPortDIN2 1 16 } } }
	pre_traces_last_spike_time_1 { ap_memory {  { pre_traces_last_spike_time_1_address0 mem_address 1 7 }  { pre_traces_last_spike_time_1_ce0 mem_ce 1 1 }  { pre_traces_last_spike_time_1_q0 mem_dout 0 16 }  { pre_traces_last_spike_time_1_address1 MemPortADDR2 1 7 }  { pre_traces_last_spike_time_1_ce1 MemPortCE2 1 1 }  { pre_traces_last_spike_time_1_we1 MemPortWE2 1 1 }  { pre_traces_last_spike_time_1_d1 MemPortDIN2 1 16 } } }
	EXP_DECAY_LUT { ap_memory {  { EXP_DECAY_LUT_address0 mem_address 1 4 }  { EXP_DECAY_LUT_ce0 mem_ce 1 1 }  { EXP_DECAY_LUT_q0 mem_dout 0 8 } } }
	post_traces_trace_1 { ap_memory {  { post_traces_trace_1_address0 mem_address 1 7 }  { post_traces_trace_1_ce0 mem_ce 1 1 }  { post_traces_trace_1_q0 mem_dout 0 8 } } }
	post_traces_last_spike_time_1 { ap_memory {  { post_traces_last_spike_time_1_address0 mem_address 1 7 }  { post_traces_last_spike_time_1_ce0 mem_ce 1 1 }  { post_traces_last_spike_time_1_q0 mem_dout 0 16 } } }
	post_traces_trace_0 { ap_memory {  { post_traces_trace_0_address0 mem_address 1 7 }  { post_traces_trace_0_ce0 mem_ce 1 1 }  { post_traces_trace_0_q0 mem_dout 0 8 } } }
	post_traces_last_spike_time_0 { ap_memory {  { post_traces_last_spike_time_0_address0 mem_address 1 7 }  { post_traces_last_spike_time_0_ce0 mem_ce 1 1 }  { post_traces_last_spike_time_0_q0 mem_dout 0 16 } } }
	p_ZL13weight_memory_0 { ap_memory {  { p_ZL13weight_memory_0_address0 mem_address 1 15 }  { p_ZL13weight_memory_0_ce0 mem_ce 1 1 }  { p_ZL13weight_memory_0_q0 mem_dout 0 8 }  { p_ZL13weight_memory_0_address1 MemPortADDR2 1 15 }  { p_ZL13weight_memory_0_ce1 MemPortCE2 1 1 }  { p_ZL13weight_memory_0_we1 MemPortWE2 1 1 }  { p_ZL13weight_memory_0_d1 MemPortDIN2 1 8 } } }
	p_ZL13weight_memory_1 { ap_memory {  { p_ZL13weight_memory_1_address0 mem_address 1 15 }  { p_ZL13weight_memory_1_ce0 mem_ce 1 1 }  { p_ZL13weight_memory_1_q0 mem_dout 0 8 }  { p_ZL13weight_memory_1_address1 MemPortADDR2 1 15 }  { p_ZL13weight_memory_1_ce1 MemPortCE2 1 1 }  { p_ZL13weight_memory_1_we1 MemPortWE2 1 1 }  { p_ZL13weight_memory_1_d1 MemPortDIN2 1 8 } } }
}
