set moduleName apply_rstdp_reward
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
set C_modelName {apply_rstdp_reward}
set C_modelType { void 0 }
set ap_memory_interface_dict [dict create]
dict set ap_memory_interface_dict p_ZL15pre_eligibility_0 { MEM_WIDTH 8 MEM_SIZE 128 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict p_ZL15pre_eligibility_1 { MEM_WIDTH 8 MEM_SIZE 128 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict p_ZL16post_eligibility_0 { MEM_WIDTH 8 MEM_SIZE 128 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict p_ZL16post_eligibility_1 { MEM_WIDTH 8 MEM_SIZE 128 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict p_ZL13weight_memory_0 { MEM_WIDTH 8 MEM_SIZE 32768 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict p_ZL13weight_memory_1 { MEM_WIDTH 8 MEM_SIZE 32768 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
set C_modelArgList {
	{ reward_signal int 8 regular  }
	{ params_rstdp_enable_val int 1 regular  }
	{ p_ZL15pre_eligibility_0 int 8 regular {array 128 { 1 3 } 1 1 } {global 0}  }
	{ p_ZL15pre_eligibility_1 int 8 regular {array 128 { 1 3 } 1 1 } {global 0}  }
	{ p_ZL16post_eligibility_0 int 8 regular {array 128 { 1 3 } 1 1 } {global 0}  }
	{ p_ZL16post_eligibility_1 int 8 regular {array 128 { 1 3 } 1 1 } {global 0}  }
	{ p_ZL13weight_memory_0 int 8 regular {array 32768 { 1 0 } 1 1 } {global 2}  }
	{ p_ZL13weight_memory_1 int 8 regular {array 32768 { 1 0 } 1 1 } {global 2}  }
}
set hasAXIMCache 0
set l_AXIML2Cache [list]
set AXIMCacheInstDict [dict create]
set C_modelArgMapList {[ 
	{ "Name" : "reward_signal", "interface" : "wire", "bitwidth" : 8, "direction" : "READONLY"} , 
 	{ "Name" : "params_rstdp_enable_val", "interface" : "wire", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "p_ZL15pre_eligibility_0", "interface" : "memory", "bitwidth" : 8, "direction" : "READONLY", "extern" : 0} , 
 	{ "Name" : "p_ZL15pre_eligibility_1", "interface" : "memory", "bitwidth" : 8, "direction" : "READONLY", "extern" : 0} , 
 	{ "Name" : "p_ZL16post_eligibility_0", "interface" : "memory", "bitwidth" : 8, "direction" : "READONLY", "extern" : 0} , 
 	{ "Name" : "p_ZL16post_eligibility_1", "interface" : "memory", "bitwidth" : 8, "direction" : "READONLY", "extern" : 0} , 
 	{ "Name" : "p_ZL13weight_memory_0", "interface" : "memory", "bitwidth" : 8, "direction" : "READWRITE", "extern" : 0} , 
 	{ "Name" : "p_ZL13weight_memory_1", "interface" : "memory", "bitwidth" : 8, "direction" : "READWRITE", "extern" : 0} ]}
# RTL Port declarations: 
set portNum 34
set portList { 
	{ ap_clk sc_in sc_logic 1 clock -1 } 
	{ ap_rst sc_in sc_logic 1 reset -1 active_high_sync } 
	{ ap_start sc_in sc_logic 1 start -1 } 
	{ ap_done sc_out sc_logic 1 predone -1 } 
	{ ap_idle sc_out sc_logic 1 done -1 } 
	{ ap_ready sc_out sc_logic 1 ready -1 } 
	{ reward_signal sc_in sc_lv 8 signal 0 } 
	{ params_rstdp_enable_val sc_in sc_lv 1 signal 1 } 
	{ p_ZL15pre_eligibility_0_address0 sc_out sc_lv 7 signal 2 } 
	{ p_ZL15pre_eligibility_0_ce0 sc_out sc_logic 1 signal 2 } 
	{ p_ZL15pre_eligibility_0_q0 sc_in sc_lv 8 signal 2 } 
	{ p_ZL15pre_eligibility_1_address0 sc_out sc_lv 7 signal 3 } 
	{ p_ZL15pre_eligibility_1_ce0 sc_out sc_logic 1 signal 3 } 
	{ p_ZL15pre_eligibility_1_q0 sc_in sc_lv 8 signal 3 } 
	{ p_ZL16post_eligibility_0_address0 sc_out sc_lv 7 signal 4 } 
	{ p_ZL16post_eligibility_0_ce0 sc_out sc_logic 1 signal 4 } 
	{ p_ZL16post_eligibility_0_q0 sc_in sc_lv 8 signal 4 } 
	{ p_ZL16post_eligibility_1_address0 sc_out sc_lv 7 signal 5 } 
	{ p_ZL16post_eligibility_1_ce0 sc_out sc_logic 1 signal 5 } 
	{ p_ZL16post_eligibility_1_q0 sc_in sc_lv 8 signal 5 } 
	{ p_ZL13weight_memory_0_address0 sc_out sc_lv 15 signal 6 } 
	{ p_ZL13weight_memory_0_ce0 sc_out sc_logic 1 signal 6 } 
	{ p_ZL13weight_memory_0_q0 sc_in sc_lv 8 signal 6 } 
	{ p_ZL13weight_memory_0_address1 sc_out sc_lv 15 signal 6 } 
	{ p_ZL13weight_memory_0_ce1 sc_out sc_logic 1 signal 6 } 
	{ p_ZL13weight_memory_0_we1 sc_out sc_logic 1 signal 6 } 
	{ p_ZL13weight_memory_0_d1 sc_out sc_lv 8 signal 6 } 
	{ p_ZL13weight_memory_1_address0 sc_out sc_lv 15 signal 7 } 
	{ p_ZL13weight_memory_1_ce0 sc_out sc_logic 1 signal 7 } 
	{ p_ZL13weight_memory_1_q0 sc_in sc_lv 8 signal 7 } 
	{ p_ZL13weight_memory_1_address1 sc_out sc_lv 15 signal 7 } 
	{ p_ZL13weight_memory_1_ce1 sc_out sc_logic 1 signal 7 } 
	{ p_ZL13weight_memory_1_we1 sc_out sc_logic 1 signal 7 } 
	{ p_ZL13weight_memory_1_d1 sc_out sc_lv 8 signal 7 } 
}
set NewPortList {[ 
	{ "name": "ap_clk", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "clock", "bundle":{"name": "ap_clk", "role": "default" }} , 
 	{ "name": "ap_rst", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "reset", "bundle":{"name": "ap_rst", "role": "default" }} , 
 	{ "name": "ap_start", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "start", "bundle":{"name": "ap_start", "role": "default" }} , 
 	{ "name": "ap_done", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "predone", "bundle":{"name": "ap_done", "role": "default" }} , 
 	{ "name": "ap_idle", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "done", "bundle":{"name": "ap_idle", "role": "default" }} , 
 	{ "name": "ap_ready", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "ready", "bundle":{"name": "ap_ready", "role": "default" }} , 
 	{ "name": "reward_signal", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "reward_signal", "role": "default" }} , 
 	{ "name": "params_rstdp_enable_val", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "params_rstdp_enable_val", "role": "default" }} , 
 	{ "name": "p_ZL15pre_eligibility_0_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "p_ZL15pre_eligibility_0", "role": "address0" }} , 
 	{ "name": "p_ZL15pre_eligibility_0_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL15pre_eligibility_0", "role": "ce0" }} , 
 	{ "name": "p_ZL15pre_eligibility_0_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "p_ZL15pre_eligibility_0", "role": "q0" }} , 
 	{ "name": "p_ZL15pre_eligibility_1_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "p_ZL15pre_eligibility_1", "role": "address0" }} , 
 	{ "name": "p_ZL15pre_eligibility_1_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL15pre_eligibility_1", "role": "ce0" }} , 
 	{ "name": "p_ZL15pre_eligibility_1_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "p_ZL15pre_eligibility_1", "role": "q0" }} , 
 	{ "name": "p_ZL16post_eligibility_0_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "p_ZL16post_eligibility_0", "role": "address0" }} , 
 	{ "name": "p_ZL16post_eligibility_0_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL16post_eligibility_0", "role": "ce0" }} , 
 	{ "name": "p_ZL16post_eligibility_0_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "p_ZL16post_eligibility_0", "role": "q0" }} , 
 	{ "name": "p_ZL16post_eligibility_1_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "p_ZL16post_eligibility_1", "role": "address0" }} , 
 	{ "name": "p_ZL16post_eligibility_1_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL16post_eligibility_1", "role": "ce0" }} , 
 	{ "name": "p_ZL16post_eligibility_1_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "p_ZL16post_eligibility_1", "role": "q0" }} , 
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
	apply_rstdp_reward {
		reward_signal {Type I LastRead 0 FirstWrite -1}
		params_rstdp_enable_val {Type I LastRead 0 FirstWrite -1}
		p_ZL15pre_eligibility_0 {Type I LastRead 1 FirstWrite -1}
		p_ZL15pre_eligibility_1 {Type I LastRead 1 FirstWrite -1}
		p_ZL16post_eligibility_0 {Type I LastRead 0 FirstWrite -1}
		p_ZL16post_eligibility_1 {Type I LastRead 0 FirstWrite -1}
		p_ZL13weight_memory_0 {Type IO LastRead 2 FirstWrite 4}
		p_ZL13weight_memory_1 {Type IO LastRead 2 FirstWrite 4}}
	apply_rstdp_reward_Pipeline_RSTDP_INNER {
		i {Type I LastRead 0 FirstWrite -1}
		sext_ln486 {Type I LastRead 0 FirstWrite -1}
		shift_sel {Type I LastRead 0 FirstWrite -1}
		empty {Type I LastRead 0 FirstWrite -1}
		p_ZL16post_eligibility_0 {Type I LastRead 0 FirstWrite -1}
		p_ZL16post_eligibility_1 {Type I LastRead 0 FirstWrite -1}
		p_ZL13weight_memory_0 {Type IO LastRead 2 FirstWrite 4}
		p_ZL13weight_memory_1 {Type IO LastRead 2 FirstWrite 4}}}

set hasDtUnsupportedChannel 0

set PerformanceInfo {[
	{"Name" : "Latency", "Min" : "1", "Max" : "67585"}
	, {"Name" : "Interval", "Min" : "1", "Max" : "67585"}
]}

set PipelineEnableSignalInfo {[
]}

set Spec2ImplPortList { 
	reward_signal { ap_none {  { reward_signal in_data 0 8 } } }
	params_rstdp_enable_val { ap_none {  { params_rstdp_enable_val in_data 0 1 } } }
	p_ZL15pre_eligibility_0 { ap_memory {  { p_ZL15pre_eligibility_0_address0 mem_address 1 7 }  { p_ZL15pre_eligibility_0_ce0 mem_ce 1 1 }  { p_ZL15pre_eligibility_0_q0 mem_dout 0 8 } } }
	p_ZL15pre_eligibility_1 { ap_memory {  { p_ZL15pre_eligibility_1_address0 mem_address 1 7 }  { p_ZL15pre_eligibility_1_ce0 mem_ce 1 1 }  { p_ZL15pre_eligibility_1_q0 mem_dout 0 8 } } }
	p_ZL16post_eligibility_0 { ap_memory {  { p_ZL16post_eligibility_0_address0 mem_address 1 7 }  { p_ZL16post_eligibility_0_ce0 mem_ce 1 1 }  { p_ZL16post_eligibility_0_q0 mem_dout 0 8 } } }
	p_ZL16post_eligibility_1 { ap_memory {  { p_ZL16post_eligibility_1_address0 mem_address 1 7 }  { p_ZL16post_eligibility_1_ce0 mem_ce 1 1 }  { p_ZL16post_eligibility_1_q0 mem_dout 0 8 } } }
	p_ZL13weight_memory_0 { ap_memory {  { p_ZL13weight_memory_0_address0 mem_address 1 15 }  { p_ZL13weight_memory_0_ce0 mem_ce 1 1 }  { p_ZL13weight_memory_0_q0 mem_dout 0 8 }  { p_ZL13weight_memory_0_address1 MemPortADDR2 1 15 }  { p_ZL13weight_memory_0_ce1 MemPortCE2 1 1 }  { p_ZL13weight_memory_0_we1 MemPortWE2 1 1 }  { p_ZL13weight_memory_0_d1 MemPortDIN2 1 8 } } }
	p_ZL13weight_memory_1 { ap_memory {  { p_ZL13weight_memory_1_address0 mem_address 1 15 }  { p_ZL13weight_memory_1_ce0 mem_ce 1 1 }  { p_ZL13weight_memory_1_q0 mem_dout 0 8 }  { p_ZL13weight_memory_1_address1 MemPortADDR2 1 15 }  { p_ZL13weight_memory_1_ce1 MemPortCE2 1 1 }  { p_ZL13weight_memory_1_we1 MemPortWE2 1 1 }  { p_ZL13weight_memory_1_d1 MemPortDIN2 1 8 } } }
}
