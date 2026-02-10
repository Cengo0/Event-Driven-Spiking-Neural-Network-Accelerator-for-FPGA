set moduleName snn_top_hls_Pipeline_RESET_TRACES
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
set C_modelName {snn_top_hls_Pipeline_RESET_TRACES}
set C_modelType { void 0 }
set ap_memory_interface_dict [dict create]
dict set ap_memory_interface_dict pre_traces_trace_0 { MEM_WIDTH 8 MEM_SIZE 128 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 0 }
dict set ap_memory_interface_dict pre_traces_last_spike_time_0 { MEM_WIDTH 16 MEM_SIZE 256 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 0 }
dict set ap_memory_interface_dict post_traces_trace_0 { MEM_WIDTH 8 MEM_SIZE 128 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 0 }
dict set ap_memory_interface_dict post_traces_last_spike_time_0 { MEM_WIDTH 16 MEM_SIZE 256 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 0 }
dict set ap_memory_interface_dict pre_traces_trace_1 { MEM_WIDTH 8 MEM_SIZE 128 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 0 }
dict set ap_memory_interface_dict pre_traces_last_spike_time_1 { MEM_WIDTH 16 MEM_SIZE 256 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 0 }
dict set ap_memory_interface_dict post_traces_trace_1 { MEM_WIDTH 8 MEM_SIZE 128 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 0 }
dict set ap_memory_interface_dict post_traces_last_spike_time_1 { MEM_WIDTH 16 MEM_SIZE 256 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 0 }
set C_modelArgList {
	{ pre_traces_trace_0 int 8 regular {array 128 { 3 0 } 0 1 } {global 1}  }
	{ pre_traces_last_spike_time_0 int 16 regular {array 128 { 3 0 } 0 1 } {global 1}  }
	{ post_traces_trace_0 int 8 regular {array 128 { 3 0 } 0 1 } {global 1}  }
	{ post_traces_last_spike_time_0 int 16 regular {array 128 { 3 0 } 0 1 } {global 1}  }
	{ pre_traces_trace_1 int 8 regular {array 128 { 3 0 } 0 1 } {global 1}  }
	{ pre_traces_last_spike_time_1 int 16 regular {array 128 { 3 0 } 0 1 } {global 1}  }
	{ post_traces_trace_1 int 8 regular {array 128 { 3 0 } 0 1 } {global 1}  }
	{ post_traces_last_spike_time_1 int 16 regular {array 128 { 3 0 } 0 1 } {global 1}  }
}
set hasAXIMCache 0
set l_AXIML2Cache [list]
set AXIMCacheInstDict [dict create]
set C_modelArgMapList {[ 
	{ "Name" : "pre_traces_trace_0", "interface" : "memory", "bitwidth" : 8, "direction" : "WRITEONLY", "extern" : 0} , 
 	{ "Name" : "pre_traces_last_spike_time_0", "interface" : "memory", "bitwidth" : 16, "direction" : "WRITEONLY", "extern" : 0} , 
 	{ "Name" : "post_traces_trace_0", "interface" : "memory", "bitwidth" : 8, "direction" : "WRITEONLY", "extern" : 0} , 
 	{ "Name" : "post_traces_last_spike_time_0", "interface" : "memory", "bitwidth" : 16, "direction" : "WRITEONLY", "extern" : 0} , 
 	{ "Name" : "pre_traces_trace_1", "interface" : "memory", "bitwidth" : 8, "direction" : "WRITEONLY", "extern" : 0} , 
 	{ "Name" : "pre_traces_last_spike_time_1", "interface" : "memory", "bitwidth" : 16, "direction" : "WRITEONLY", "extern" : 0} , 
 	{ "Name" : "post_traces_trace_1", "interface" : "memory", "bitwidth" : 8, "direction" : "WRITEONLY", "extern" : 0} , 
 	{ "Name" : "post_traces_last_spike_time_1", "interface" : "memory", "bitwidth" : 16, "direction" : "WRITEONLY", "extern" : 0} ]}
# RTL Port declarations: 
set portNum 38
set portList { 
	{ ap_clk sc_in sc_logic 1 clock -1 } 
	{ ap_rst sc_in sc_logic 1 reset -1 active_high_sync } 
	{ ap_start sc_in sc_logic 1 start -1 } 
	{ ap_done sc_out sc_logic 1 predone -1 } 
	{ ap_idle sc_out sc_logic 1 done -1 } 
	{ ap_ready sc_out sc_logic 1 ready -1 } 
	{ pre_traces_trace_0_address1 sc_out sc_lv 7 signal 0 } 
	{ pre_traces_trace_0_ce1 sc_out sc_logic 1 signal 0 } 
	{ pre_traces_trace_0_we1 sc_out sc_logic 1 signal 0 } 
	{ pre_traces_trace_0_d1 sc_out sc_lv 8 signal 0 } 
	{ pre_traces_last_spike_time_0_address1 sc_out sc_lv 7 signal 1 } 
	{ pre_traces_last_spike_time_0_ce1 sc_out sc_logic 1 signal 1 } 
	{ pre_traces_last_spike_time_0_we1 sc_out sc_logic 1 signal 1 } 
	{ pre_traces_last_spike_time_0_d1 sc_out sc_lv 16 signal 1 } 
	{ post_traces_trace_0_address1 sc_out sc_lv 7 signal 2 } 
	{ post_traces_trace_0_ce1 sc_out sc_logic 1 signal 2 } 
	{ post_traces_trace_0_we1 sc_out sc_logic 1 signal 2 } 
	{ post_traces_trace_0_d1 sc_out sc_lv 8 signal 2 } 
	{ post_traces_last_spike_time_0_address1 sc_out sc_lv 7 signal 3 } 
	{ post_traces_last_spike_time_0_ce1 sc_out sc_logic 1 signal 3 } 
	{ post_traces_last_spike_time_0_we1 sc_out sc_logic 1 signal 3 } 
	{ post_traces_last_spike_time_0_d1 sc_out sc_lv 16 signal 3 } 
	{ pre_traces_trace_1_address1 sc_out sc_lv 7 signal 4 } 
	{ pre_traces_trace_1_ce1 sc_out sc_logic 1 signal 4 } 
	{ pre_traces_trace_1_we1 sc_out sc_logic 1 signal 4 } 
	{ pre_traces_trace_1_d1 sc_out sc_lv 8 signal 4 } 
	{ pre_traces_last_spike_time_1_address1 sc_out sc_lv 7 signal 5 } 
	{ pre_traces_last_spike_time_1_ce1 sc_out sc_logic 1 signal 5 } 
	{ pre_traces_last_spike_time_1_we1 sc_out sc_logic 1 signal 5 } 
	{ pre_traces_last_spike_time_1_d1 sc_out sc_lv 16 signal 5 } 
	{ post_traces_trace_1_address1 sc_out sc_lv 7 signal 6 } 
	{ post_traces_trace_1_ce1 sc_out sc_logic 1 signal 6 } 
	{ post_traces_trace_1_we1 sc_out sc_logic 1 signal 6 } 
	{ post_traces_trace_1_d1 sc_out sc_lv 8 signal 6 } 
	{ post_traces_last_spike_time_1_address1 sc_out sc_lv 7 signal 7 } 
	{ post_traces_last_spike_time_1_ce1 sc_out sc_logic 1 signal 7 } 
	{ post_traces_last_spike_time_1_we1 sc_out sc_logic 1 signal 7 } 
	{ post_traces_last_spike_time_1_d1 sc_out sc_lv 16 signal 7 } 
}
set NewPortList {[ 
	{ "name": "ap_clk", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "clock", "bundle":{"name": "ap_clk", "role": "default" }} , 
 	{ "name": "ap_rst", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "reset", "bundle":{"name": "ap_rst", "role": "default" }} , 
 	{ "name": "ap_start", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "start", "bundle":{"name": "ap_start", "role": "default" }} , 
 	{ "name": "ap_done", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "predone", "bundle":{"name": "ap_done", "role": "default" }} , 
 	{ "name": "ap_idle", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "done", "bundle":{"name": "ap_idle", "role": "default" }} , 
 	{ "name": "ap_ready", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "ready", "bundle":{"name": "ap_ready", "role": "default" }} , 
 	{ "name": "pre_traces_trace_0_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "pre_traces_trace_0", "role": "address1" }} , 
 	{ "name": "pre_traces_trace_0_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_trace_0", "role": "ce1" }} , 
 	{ "name": "pre_traces_trace_0_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_trace_0", "role": "we1" }} , 
 	{ "name": "pre_traces_trace_0_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "pre_traces_trace_0", "role": "d1" }} , 
 	{ "name": "pre_traces_last_spike_time_0_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_0", "role": "address1" }} , 
 	{ "name": "pre_traces_last_spike_time_0_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_0", "role": "ce1" }} , 
 	{ "name": "pre_traces_last_spike_time_0_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_0", "role": "we1" }} , 
 	{ "name": "pre_traces_last_spike_time_0_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_0", "role": "d1" }} , 
 	{ "name": "post_traces_trace_0_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "post_traces_trace_0", "role": "address1" }} , 
 	{ "name": "post_traces_trace_0_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "post_traces_trace_0", "role": "ce1" }} , 
 	{ "name": "post_traces_trace_0_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "post_traces_trace_0", "role": "we1" }} , 
 	{ "name": "post_traces_trace_0_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "post_traces_trace_0", "role": "d1" }} , 
 	{ "name": "post_traces_last_spike_time_0_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "post_traces_last_spike_time_0", "role": "address1" }} , 
 	{ "name": "post_traces_last_spike_time_0_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "post_traces_last_spike_time_0", "role": "ce1" }} , 
 	{ "name": "post_traces_last_spike_time_0_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "post_traces_last_spike_time_0", "role": "we1" }} , 
 	{ "name": "post_traces_last_spike_time_0_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "post_traces_last_spike_time_0", "role": "d1" }} , 
 	{ "name": "pre_traces_trace_1_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "pre_traces_trace_1", "role": "address1" }} , 
 	{ "name": "pre_traces_trace_1_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_trace_1", "role": "ce1" }} , 
 	{ "name": "pre_traces_trace_1_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_trace_1", "role": "we1" }} , 
 	{ "name": "pre_traces_trace_1_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "pre_traces_trace_1", "role": "d1" }} , 
 	{ "name": "pre_traces_last_spike_time_1_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_1", "role": "address1" }} , 
 	{ "name": "pre_traces_last_spike_time_1_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_1", "role": "ce1" }} , 
 	{ "name": "pre_traces_last_spike_time_1_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_1", "role": "we1" }} , 
 	{ "name": "pre_traces_last_spike_time_1_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "pre_traces_last_spike_time_1", "role": "d1" }} , 
 	{ "name": "post_traces_trace_1_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "post_traces_trace_1", "role": "address1" }} , 
 	{ "name": "post_traces_trace_1_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "post_traces_trace_1", "role": "ce1" }} , 
 	{ "name": "post_traces_trace_1_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "post_traces_trace_1", "role": "we1" }} , 
 	{ "name": "post_traces_trace_1_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "post_traces_trace_1", "role": "d1" }} , 
 	{ "name": "post_traces_last_spike_time_1_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":7, "type": "signal", "bundle":{"name": "post_traces_last_spike_time_1", "role": "address1" }} , 
 	{ "name": "post_traces_last_spike_time_1_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "post_traces_last_spike_time_1", "role": "ce1" }} , 
 	{ "name": "post_traces_last_spike_time_1_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "post_traces_last_spike_time_1", "role": "we1" }} , 
 	{ "name": "post_traces_last_spike_time_1_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "post_traces_last_spike_time_1", "role": "d1" }}  ]}

set ArgLastReadFirstWriteLatency {
	snn_top_hls_Pipeline_RESET_TRACES {
		pre_traces_trace_0 {Type O LastRead -1 FirstWrite 0}
		pre_traces_last_spike_time_0 {Type O LastRead -1 FirstWrite 0}
		post_traces_trace_0 {Type O LastRead -1 FirstWrite 0}
		post_traces_last_spike_time_0 {Type O LastRead -1 FirstWrite 0}
		pre_traces_trace_1 {Type O LastRead -1 FirstWrite 0}
		pre_traces_last_spike_time_1 {Type O LastRead -1 FirstWrite 0}
		post_traces_trace_1 {Type O LastRead -1 FirstWrite 0}
		post_traces_last_spike_time_1 {Type O LastRead -1 FirstWrite 0}}}

set hasDtUnsupportedChannel 0

set PerformanceInfo {[
	{"Name" : "Latency", "Min" : "258", "Max" : "258"}
	, {"Name" : "Interval", "Min" : "257", "Max" : "257"}
]}

set PipelineEnableSignalInfo {[
]}

set Spec2ImplPortList { 
	pre_traces_trace_0 { ap_memory {  { pre_traces_trace_0_address1 MemPortADDR2 1 7 }  { pre_traces_trace_0_ce1 MemPortCE2 1 1 }  { pre_traces_trace_0_we1 MemPortWE2 1 1 }  { pre_traces_trace_0_d1 MemPortDIN2 1 8 } } }
	pre_traces_last_spike_time_0 { ap_memory {  { pre_traces_last_spike_time_0_address1 MemPortADDR2 1 7 }  { pre_traces_last_spike_time_0_ce1 MemPortCE2 1 1 }  { pre_traces_last_spike_time_0_we1 MemPortWE2 1 1 }  { pre_traces_last_spike_time_0_d1 MemPortDIN2 1 16 } } }
	post_traces_trace_0 { ap_memory {  { post_traces_trace_0_address1 MemPortADDR2 1 7 }  { post_traces_trace_0_ce1 MemPortCE2 1 1 }  { post_traces_trace_0_we1 MemPortWE2 1 1 }  { post_traces_trace_0_d1 MemPortDIN2 1 8 } } }
	post_traces_last_spike_time_0 { ap_memory {  { post_traces_last_spike_time_0_address1 MemPortADDR2 1 7 }  { post_traces_last_spike_time_0_ce1 MemPortCE2 1 1 }  { post_traces_last_spike_time_0_we1 MemPortWE2 1 1 }  { post_traces_last_spike_time_0_d1 MemPortDIN2 1 16 } } }
	pre_traces_trace_1 { ap_memory {  { pre_traces_trace_1_address1 MemPortADDR2 1 7 }  { pre_traces_trace_1_ce1 MemPortCE2 1 1 }  { pre_traces_trace_1_we1 MemPortWE2 1 1 }  { pre_traces_trace_1_d1 MemPortDIN2 1 8 } } }
	pre_traces_last_spike_time_1 { ap_memory {  { pre_traces_last_spike_time_1_address1 MemPortADDR2 1 7 }  { pre_traces_last_spike_time_1_ce1 MemPortCE2 1 1 }  { pre_traces_last_spike_time_1_we1 MemPortWE2 1 1 }  { pre_traces_last_spike_time_1_d1 MemPortDIN2 1 16 } } }
	post_traces_trace_1 { ap_memory {  { post_traces_trace_1_address1 MemPortADDR2 1 7 }  { post_traces_trace_1_ce1 MemPortCE2 1 1 }  { post_traces_trace_1_we1 MemPortWE2 1 1 }  { post_traces_trace_1_d1 MemPortDIN2 1 8 } } }
	post_traces_last_spike_time_1 { ap_memory {  { post_traces_last_spike_time_1_address1 MemPortADDR2 1 7 }  { post_traces_last_spike_time_1_ce1 MemPortCE2 1 1 }  { post_traces_last_spike_time_1_we1 MemPortWE2 1 1 }  { post_traces_last_spike_time_1_d1 MemPortDIN2 1 16 } } }
}
