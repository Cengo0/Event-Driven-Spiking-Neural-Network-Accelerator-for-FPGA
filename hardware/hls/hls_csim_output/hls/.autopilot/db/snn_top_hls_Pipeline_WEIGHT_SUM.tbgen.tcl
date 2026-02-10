set moduleName snn_top_hls_Pipeline_WEIGHT_SUM
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
set C_modelName {snn_top_hls_Pipeline_WEIGHT_SUM}
set C_modelType { void 0 }
set ap_memory_interface_dict [dict create]
dict set ap_memory_interface_dict p_ZL13weight_memory_0 { MEM_WIDTH 8 MEM_SIZE 32768 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
dict set ap_memory_interface_dict p_ZL13weight_memory_1 { MEM_WIDTH 8 MEM_SIZE 32768 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 1 }
set C_modelArgList {
	{ weight_sum_out int 14 regular {pointer 1}  }
	{ p_ZL13weight_memory_0 int 8 regular {array 32768 { 1 1 } 1 1 } {global 0}  }
	{ p_ZL13weight_memory_1 int 8 regular {array 32768 { 1 1 } 1 1 } {global 0}  }
}
set hasAXIMCache 0
set l_AXIML2Cache [list]
set AXIMCacheInstDict [dict create]
set C_modelArgMapList {[ 
	{ "Name" : "weight_sum_out", "interface" : "wire", "bitwidth" : 14, "direction" : "WRITEONLY"} , 
 	{ "Name" : "p_ZL13weight_memory_0", "interface" : "memory", "bitwidth" : 8, "direction" : "READONLY", "extern" : 0} , 
 	{ "Name" : "p_ZL13weight_memory_1", "interface" : "memory", "bitwidth" : 8, "direction" : "READONLY", "extern" : 0} ]}
# RTL Port declarations: 
set portNum 20
set portList { 
	{ ap_clk sc_in sc_logic 1 clock -1 } 
	{ ap_rst sc_in sc_logic 1 reset -1 active_high_sync } 
	{ ap_start sc_in sc_logic 1 start -1 } 
	{ ap_done sc_out sc_logic 1 predone -1 } 
	{ ap_idle sc_out sc_logic 1 done -1 } 
	{ ap_ready sc_out sc_logic 1 ready -1 } 
	{ weight_sum_out sc_out sc_lv 14 signal 0 } 
	{ weight_sum_out_ap_vld sc_out sc_logic 1 outvld 0 } 
	{ p_ZL13weight_memory_0_address0 sc_out sc_lv 15 signal 1 } 
	{ p_ZL13weight_memory_0_ce0 sc_out sc_logic 1 signal 1 } 
	{ p_ZL13weight_memory_0_q0 sc_in sc_lv 8 signal 1 } 
	{ p_ZL13weight_memory_0_address1 sc_out sc_lv 15 signal 1 } 
	{ p_ZL13weight_memory_0_ce1 sc_out sc_logic 1 signal 1 } 
	{ p_ZL13weight_memory_0_q1 sc_in sc_lv 8 signal 1 } 
	{ p_ZL13weight_memory_1_address0 sc_out sc_lv 15 signal 2 } 
	{ p_ZL13weight_memory_1_ce0 sc_out sc_logic 1 signal 2 } 
	{ p_ZL13weight_memory_1_q0 sc_in sc_lv 8 signal 2 } 
	{ p_ZL13weight_memory_1_address1 sc_out sc_lv 15 signal 2 } 
	{ p_ZL13weight_memory_1_ce1 sc_out sc_logic 1 signal 2 } 
	{ p_ZL13weight_memory_1_q1 sc_in sc_lv 8 signal 2 } 
}
set NewPortList {[ 
	{ "name": "ap_clk", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "clock", "bundle":{"name": "ap_clk", "role": "default" }} , 
 	{ "name": "ap_rst", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "reset", "bundle":{"name": "ap_rst", "role": "default" }} , 
 	{ "name": "ap_start", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "start", "bundle":{"name": "ap_start", "role": "default" }} , 
 	{ "name": "ap_done", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "predone", "bundle":{"name": "ap_done", "role": "default" }} , 
 	{ "name": "ap_idle", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "done", "bundle":{"name": "ap_idle", "role": "default" }} , 
 	{ "name": "ap_ready", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "ready", "bundle":{"name": "ap_ready", "role": "default" }} , 
 	{ "name": "weight_sum_out", "direction": "out", "datatype": "sc_lv", "bitwidth":14, "type": "signal", "bundle":{"name": "weight_sum_out", "role": "default" }} , 
 	{ "name": "weight_sum_out_ap_vld", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "outvld", "bundle":{"name": "weight_sum_out", "role": "ap_vld" }} , 
 	{ "name": "p_ZL13weight_memory_0_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":15, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_0", "role": "address0" }} , 
 	{ "name": "p_ZL13weight_memory_0_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_0", "role": "ce0" }} , 
 	{ "name": "p_ZL13weight_memory_0_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_0", "role": "q0" }} , 
 	{ "name": "p_ZL13weight_memory_0_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":15, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_0", "role": "address1" }} , 
 	{ "name": "p_ZL13weight_memory_0_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_0", "role": "ce1" }} , 
 	{ "name": "p_ZL13weight_memory_0_q1", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_0", "role": "q1" }} , 
 	{ "name": "p_ZL13weight_memory_1_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":15, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_1", "role": "address0" }} , 
 	{ "name": "p_ZL13weight_memory_1_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_1", "role": "ce0" }} , 
 	{ "name": "p_ZL13weight_memory_1_q0", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_1", "role": "q0" }} , 
 	{ "name": "p_ZL13weight_memory_1_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":15, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_1", "role": "address1" }} , 
 	{ "name": "p_ZL13weight_memory_1_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_1", "role": "ce1" }} , 
 	{ "name": "p_ZL13weight_memory_1_q1", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "p_ZL13weight_memory_1", "role": "q1" }}  ]}

set ArgLastReadFirstWriteLatency {
	snn_top_hls_Pipeline_WEIGHT_SUM {
		weight_sum_out {Type O LastRead -1 FirstWrite 1}
		p_ZL13weight_memory_0 {Type I LastRead 2 FirstWrite -1}
		p_ZL13weight_memory_1 {Type I LastRead 2 FirstWrite -1}}}

set hasDtUnsupportedChannel 0

set PerformanceInfo {[
	{"Name" : "Latency", "Min" : "19", "Max" : "19"}
	, {"Name" : "Interval", "Min" : "18", "Max" : "18"}
]}

set PipelineEnableSignalInfo {[
	{"Pipeline" : "0", "EnableSignal" : "ap_enable_pp0"}
]}

set Spec2ImplPortList { 
	weight_sum_out { ap_vld {  { weight_sum_out out_data 1 14 }  { weight_sum_out_ap_vld out_vld 1 1 } } }
	p_ZL13weight_memory_0 { ap_memory {  { p_ZL13weight_memory_0_address0 mem_address 1 15 }  { p_ZL13weight_memory_0_ce0 mem_ce 1 1 }  { p_ZL13weight_memory_0_q0 mem_dout 0 8 }  { p_ZL13weight_memory_0_address1 MemPortADDR2 1 15 }  { p_ZL13weight_memory_0_ce1 MemPortCE2 1 1 }  { p_ZL13weight_memory_0_q1 MemPortDOUT2 0 8 } } }
	p_ZL13weight_memory_1 { ap_memory {  { p_ZL13weight_memory_1_address0 mem_address 1 15 }  { p_ZL13weight_memory_1_ce0 mem_ce 1 1 }  { p_ZL13weight_memory_1_q0 mem_dout 0 8 }  { p_ZL13weight_memory_1_address1 MemPortADDR2 1 15 }  { p_ZL13weight_memory_1_ce1 MemPortCE2 1 1 }  { p_ZL13weight_memory_1_q1 MemPortDOUT2 0 8 } } }
}
