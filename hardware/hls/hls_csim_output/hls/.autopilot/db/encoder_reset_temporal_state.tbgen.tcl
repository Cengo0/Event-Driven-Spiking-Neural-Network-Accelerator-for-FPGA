set moduleName encoder_reset_temporal_state
set isTopModule 0
set isCombinational 0
set isDatapathOnly 0
set isPipelined 1
set isPipelined_legacy 1
set pipeline_type loop_auto_rewind
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
set C_modelName {encoder_reset_temporal_state}
set C_modelType { void 0 }
set ap_memory_interface_dict [dict create]
dict set ap_memory_interface_dict p_ZL22encoder_temporal_fired_0 { MEM_WIDTH 1 MEM_SIZE 392 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 0 }
dict set ap_memory_interface_dict p_ZL22encoder_temporal_start_0 { MEM_WIDTH 32 MEM_SIZE 1568 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 0 }
dict set ap_memory_interface_dict p_ZL22encoder_temporal_fired_1 { MEM_WIDTH 1 MEM_SIZE 392 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 0 }
dict set ap_memory_interface_dict p_ZL22encoder_temporal_start_1 { MEM_WIDTH 32 MEM_SIZE 1568 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 0 }
set C_modelArgList {
	{ now_val int 32 regular  }
	{ p_ZL22encoder_temporal_fired_0 int 1 regular {array 392 { 3 0 } 0 1 } {global 1}  }
	{ p_ZL22encoder_temporal_start_0 int 32 regular {array 392 { 3 0 } 0 1 } {global 1}  }
	{ p_ZL22encoder_temporal_fired_1 int 1 regular {array 392 { 3 0 } 0 1 } {global 1}  }
	{ p_ZL22encoder_temporal_start_1 int 32 regular {array 392 { 3 0 } 0 1 } {global 1}  }
}
set hasAXIMCache 0
set l_AXIML2Cache [list]
set AXIMCacheInstDict [dict create]
set C_modelArgMapList {[ 
	{ "Name" : "now_val", "interface" : "wire", "bitwidth" : 32, "direction" : "READONLY"} , 
 	{ "Name" : "p_ZL22encoder_temporal_fired_0", "interface" : "memory", "bitwidth" : 1, "direction" : "WRITEONLY", "extern" : 0} , 
 	{ "Name" : "p_ZL22encoder_temporal_start_0", "interface" : "memory", "bitwidth" : 32, "direction" : "WRITEONLY", "extern" : 0} , 
 	{ "Name" : "p_ZL22encoder_temporal_fired_1", "interface" : "memory", "bitwidth" : 1, "direction" : "WRITEONLY", "extern" : 0} , 
 	{ "Name" : "p_ZL22encoder_temporal_start_1", "interface" : "memory", "bitwidth" : 32, "direction" : "WRITEONLY", "extern" : 0} ]}
# RTL Port declarations: 
set portNum 23
set portList { 
	{ ap_clk sc_in sc_logic 1 clock -1 } 
	{ ap_rst sc_in sc_logic 1 reset -1 active_high_sync } 
	{ ap_start sc_in sc_logic 1 start -1 } 
	{ ap_done sc_out sc_logic 1 predone -1 } 
	{ ap_idle sc_out sc_logic 1 done -1 } 
	{ ap_ready sc_out sc_logic 1 ready -1 } 
	{ now_val sc_in sc_lv 32 signal 0 } 
	{ p_ZL22encoder_temporal_fired_0_address1 sc_out sc_lv 9 signal 1 } 
	{ p_ZL22encoder_temporal_fired_0_ce1 sc_out sc_logic 1 signal 1 } 
	{ p_ZL22encoder_temporal_fired_0_we1 sc_out sc_logic 1 signal 1 } 
	{ p_ZL22encoder_temporal_fired_0_d1 sc_out sc_lv 1 signal 1 } 
	{ p_ZL22encoder_temporal_start_0_address1 sc_out sc_lv 9 signal 2 } 
	{ p_ZL22encoder_temporal_start_0_ce1 sc_out sc_logic 1 signal 2 } 
	{ p_ZL22encoder_temporal_start_0_we1 sc_out sc_logic 1 signal 2 } 
	{ p_ZL22encoder_temporal_start_0_d1 sc_out sc_lv 32 signal 2 } 
	{ p_ZL22encoder_temporal_fired_1_address1 sc_out sc_lv 9 signal 3 } 
	{ p_ZL22encoder_temporal_fired_1_ce1 sc_out sc_logic 1 signal 3 } 
	{ p_ZL22encoder_temporal_fired_1_we1 sc_out sc_logic 1 signal 3 } 
	{ p_ZL22encoder_temporal_fired_1_d1 sc_out sc_lv 1 signal 3 } 
	{ p_ZL22encoder_temporal_start_1_address1 sc_out sc_lv 9 signal 4 } 
	{ p_ZL22encoder_temporal_start_1_ce1 sc_out sc_logic 1 signal 4 } 
	{ p_ZL22encoder_temporal_start_1_we1 sc_out sc_logic 1 signal 4 } 
	{ p_ZL22encoder_temporal_start_1_d1 sc_out sc_lv 32 signal 4 } 
}
set NewPortList {[ 
	{ "name": "ap_clk", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "clock", "bundle":{"name": "ap_clk", "role": "default" }} , 
 	{ "name": "ap_rst", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "reset", "bundle":{"name": "ap_rst", "role": "default" }} , 
 	{ "name": "ap_start", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "start", "bundle":{"name": "ap_start", "role": "default" }} , 
 	{ "name": "ap_done", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "predone", "bundle":{"name": "ap_done", "role": "default" }} , 
 	{ "name": "ap_idle", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "done", "bundle":{"name": "ap_idle", "role": "default" }} , 
 	{ "name": "ap_ready", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "ready", "bundle":{"name": "ap_ready", "role": "default" }} , 
 	{ "name": "now_val", "direction": "in", "datatype": "sc_lv", "bitwidth":32, "type": "signal", "bundle":{"name": "now_val", "role": "default" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_0_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_0", "role": "address1" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_0_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_0", "role": "ce1" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_0_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_0", "role": "we1" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_0_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_0", "role": "d1" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_0_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_0", "role": "address1" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_0_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_0", "role": "ce1" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_0_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_0", "role": "we1" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_0_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":32, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_0", "role": "d1" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_1_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_1", "role": "address1" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_1_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_1", "role": "ce1" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_1_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_1", "role": "we1" }} , 
 	{ "name": "p_ZL22encoder_temporal_fired_1_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_fired_1", "role": "d1" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_1_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_1", "role": "address1" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_1_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_1", "role": "ce1" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_1_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_1", "role": "we1" }} , 
 	{ "name": "p_ZL22encoder_temporal_start_1_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":32, "type": "signal", "bundle":{"name": "p_ZL22encoder_temporal_start_1", "role": "d1" }}  ]}

set ArgLastReadFirstWriteLatency {
	encoder_reset_temporal_state {
		now_val {Type I LastRead 0 FirstWrite -1}
		p_ZL22encoder_temporal_fired_0 {Type O LastRead -1 FirstWrite 0}
		p_ZL22encoder_temporal_start_0 {Type O LastRead -1 FirstWrite 0}
		p_ZL22encoder_temporal_fired_1 {Type O LastRead -1 FirstWrite 0}
		p_ZL22encoder_temporal_start_1 {Type O LastRead -1 FirstWrite 0}}}

set hasDtUnsupportedChannel 0

set PerformanceInfo {[
	{"Name" : "Latency", "Min" : "786", "Max" : "786"}
	, {"Name" : "Interval", "Min" : "785", "Max" : "785"}
]}

set PipelineEnableSignalInfo {[
]}

set Spec2ImplPortList { 
	now_val { ap_none {  { now_val in_data 0 32 } } }
	p_ZL22encoder_temporal_fired_0 { ap_memory {  { p_ZL22encoder_temporal_fired_0_address1 MemPortADDR2 1 9 }  { p_ZL22encoder_temporal_fired_0_ce1 MemPortCE2 1 1 }  { p_ZL22encoder_temporal_fired_0_we1 MemPortWE2 1 1 }  { p_ZL22encoder_temporal_fired_0_d1 MemPortDIN2 1 1 } } }
	p_ZL22encoder_temporal_start_0 { ap_memory {  { p_ZL22encoder_temporal_start_0_address1 MemPortADDR2 1 9 }  { p_ZL22encoder_temporal_start_0_ce1 MemPortCE2 1 1 }  { p_ZL22encoder_temporal_start_0_we1 MemPortWE2 1 1 }  { p_ZL22encoder_temporal_start_0_d1 MemPortDIN2 1 32 } } }
	p_ZL22encoder_temporal_fired_1 { ap_memory {  { p_ZL22encoder_temporal_fired_1_address1 MemPortADDR2 1 9 }  { p_ZL22encoder_temporal_fired_1_ce1 MemPortCE2 1 1 }  { p_ZL22encoder_temporal_fired_1_we1 MemPortWE2 1 1 }  { p_ZL22encoder_temporal_fired_1_d1 MemPortDIN2 1 1 } } }
	p_ZL22encoder_temporal_start_1 { ap_memory {  { p_ZL22encoder_temporal_start_1_address1 MemPortADDR2 1 9 }  { p_ZL22encoder_temporal_start_1_ce1 MemPortCE2 1 1 }  { p_ZL22encoder_temporal_start_1_we1 MemPortWE2 1 1 }  { p_ZL22encoder_temporal_start_1_d1 MemPortDIN2 1 32 } } }
}
