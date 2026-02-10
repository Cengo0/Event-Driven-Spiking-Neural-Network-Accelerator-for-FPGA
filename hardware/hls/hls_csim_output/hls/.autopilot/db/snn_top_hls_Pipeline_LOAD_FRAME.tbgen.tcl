set moduleName snn_top_hls_Pipeline_LOAD_FRAME
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
set C_modelName {snn_top_hls_Pipeline_LOAD_FRAME}
set C_modelType { void 0 }
set ap_memory_interface_dict [dict create]
dict set ap_memory_interface_dict p_ZL13encoder_frame_0 { MEM_WIDTH 8 MEM_SIZE 392 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 0 }
dict set ap_memory_interface_dict p_ZL13encoder_frame_1 { MEM_WIDTH 8 MEM_SIZE 392 MASTER_TYPE BRAM_CTRL MEM_ADDRESS_MODE WORD_ADDRESS PACKAGE_IO port READ_LATENCY 0 }
set C_modelArgList {
	{ s_axis_data_V_data_V int 32 regular {axi_s 0 volatile  { s_axis_data Data } }  }
	{ s_axis_data_V_keep_V int 4 regular {axi_s 0 volatile  { s_axis_data Keep } }  }
	{ s_axis_data_V_strb_V int 4 regular {axi_s 0 volatile  { s_axis_data Strb } }  }
	{ s_axis_data_V_user_V int 1 regular {axi_s 0 volatile  { s_axis_data User } }  }
	{ s_axis_data_V_last_V int 1 regular {axi_s 0 volatile  { s_axis_data Last } }  }
	{ s_axis_data_V_id_V int 1 regular {axi_s 0 volatile  { s_axis_data ID } }  }
	{ s_axis_data_V_dest_V int 1 regular {axi_s 0 volatile  { s_axis_data Dest } }  }
	{ p_ZL13encoder_frame_0 int 8 regular {array 392 { 0 0 } 0 1 } {global 1}  }
	{ p_ZL13encoder_frame_1 int 8 regular {array 392 { 0 0 } 0 1 } {global 1}  }
}
set hasAXIMCache 0
set l_AXIML2Cache [list]
set AXIMCacheInstDict [dict create]
set C_modelArgMapList {[ 
	{ "Name" : "s_axis_data_V_data_V", "interface" : "axis", "bitwidth" : 32, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_data_V_keep_V", "interface" : "axis", "bitwidth" : 4, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_data_V_strb_V", "interface" : "axis", "bitwidth" : 4, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_data_V_user_V", "interface" : "axis", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_data_V_last_V", "interface" : "axis", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_data_V_id_V", "interface" : "axis", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_data_V_dest_V", "interface" : "axis", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "p_ZL13encoder_frame_0", "interface" : "memory", "bitwidth" : 8, "direction" : "WRITEONLY", "extern" : 0} , 
 	{ "Name" : "p_ZL13encoder_frame_1", "interface" : "memory", "bitwidth" : 8, "direction" : "WRITEONLY", "extern" : 0} ]}
# RTL Port declarations: 
set portNum 31
set portList { 
	{ ap_clk sc_in sc_logic 1 clock -1 } 
	{ ap_rst sc_in sc_logic 1 reset -1 active_high_sync } 
	{ ap_start sc_in sc_logic 1 start -1 } 
	{ ap_done sc_out sc_logic 1 predone -1 } 
	{ ap_idle sc_out sc_logic 1 done -1 } 
	{ ap_ready sc_out sc_logic 1 ready -1 } 
	{ s_axis_data_TVALID sc_in sc_logic 1 invld 0 } 
	{ s_axis_data_TDATA sc_in sc_lv 32 signal 0 } 
	{ s_axis_data_TREADY sc_out sc_logic 1 inacc 6 } 
	{ s_axis_data_TKEEP sc_in sc_lv 4 signal 1 } 
	{ s_axis_data_TSTRB sc_in sc_lv 4 signal 2 } 
	{ s_axis_data_TUSER sc_in sc_lv 1 signal 3 } 
	{ s_axis_data_TLAST sc_in sc_lv 1 signal 4 } 
	{ s_axis_data_TID sc_in sc_lv 1 signal 5 } 
	{ s_axis_data_TDEST sc_in sc_lv 1 signal 6 } 
	{ p_ZL13encoder_frame_0_address0 sc_out sc_lv 9 signal 7 } 
	{ p_ZL13encoder_frame_0_ce0 sc_out sc_logic 1 signal 7 } 
	{ p_ZL13encoder_frame_0_we0 sc_out sc_logic 1 signal 7 } 
	{ p_ZL13encoder_frame_0_d0 sc_out sc_lv 8 signal 7 } 
	{ p_ZL13encoder_frame_0_address1 sc_out sc_lv 9 signal 7 } 
	{ p_ZL13encoder_frame_0_ce1 sc_out sc_logic 1 signal 7 } 
	{ p_ZL13encoder_frame_0_we1 sc_out sc_logic 1 signal 7 } 
	{ p_ZL13encoder_frame_0_d1 sc_out sc_lv 8 signal 7 } 
	{ p_ZL13encoder_frame_1_address0 sc_out sc_lv 9 signal 8 } 
	{ p_ZL13encoder_frame_1_ce0 sc_out sc_logic 1 signal 8 } 
	{ p_ZL13encoder_frame_1_we0 sc_out sc_logic 1 signal 8 } 
	{ p_ZL13encoder_frame_1_d0 sc_out sc_lv 8 signal 8 } 
	{ p_ZL13encoder_frame_1_address1 sc_out sc_lv 9 signal 8 } 
	{ p_ZL13encoder_frame_1_ce1 sc_out sc_logic 1 signal 8 } 
	{ p_ZL13encoder_frame_1_we1 sc_out sc_logic 1 signal 8 } 
	{ p_ZL13encoder_frame_1_d1 sc_out sc_lv 8 signal 8 } 
}
set NewPortList {[ 
	{ "name": "ap_clk", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "clock", "bundle":{"name": "ap_clk", "role": "default" }} , 
 	{ "name": "ap_rst", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "reset", "bundle":{"name": "ap_rst", "role": "default" }} , 
 	{ "name": "ap_start", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "start", "bundle":{"name": "ap_start", "role": "default" }} , 
 	{ "name": "ap_done", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "predone", "bundle":{"name": "ap_done", "role": "default" }} , 
 	{ "name": "ap_idle", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "done", "bundle":{"name": "ap_idle", "role": "default" }} , 
 	{ "name": "ap_ready", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "ready", "bundle":{"name": "ap_ready", "role": "default" }} , 
 	{ "name": "s_axis_data_TVALID", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "invld", "bundle":{"name": "s_axis_data_V_data_V", "role": "default" }} , 
 	{ "name": "s_axis_data_TDATA", "direction": "in", "datatype": "sc_lv", "bitwidth":32, "type": "signal", "bundle":{"name": "s_axis_data_V_data_V", "role": "default" }} , 
 	{ "name": "s_axis_data_TREADY", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "inacc", "bundle":{"name": "s_axis_data_V_dest_V", "role": "default" }} , 
 	{ "name": "s_axis_data_TKEEP", "direction": "in", "datatype": "sc_lv", "bitwidth":4, "type": "signal", "bundle":{"name": "s_axis_data_V_keep_V", "role": "default" }} , 
 	{ "name": "s_axis_data_TSTRB", "direction": "in", "datatype": "sc_lv", "bitwidth":4, "type": "signal", "bundle":{"name": "s_axis_data_V_strb_V", "role": "default" }} , 
 	{ "name": "s_axis_data_TUSER", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "s_axis_data_V_user_V", "role": "default" }} , 
 	{ "name": "s_axis_data_TLAST", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "s_axis_data_V_last_V", "role": "default" }} , 
 	{ "name": "s_axis_data_TID", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "s_axis_data_V_id_V", "role": "default" }} , 
 	{ "name": "s_axis_data_TDEST", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "s_axis_data_V_dest_V", "role": "default" }} , 
 	{ "name": "p_ZL13encoder_frame_0_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_0", "role": "address0" }} , 
 	{ "name": "p_ZL13encoder_frame_0_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_0", "role": "ce0" }} , 
 	{ "name": "p_ZL13encoder_frame_0_we0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_0", "role": "we0" }} , 
 	{ "name": "p_ZL13encoder_frame_0_d0", "direction": "out", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_0", "role": "d0" }} , 
 	{ "name": "p_ZL13encoder_frame_0_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_0", "role": "address1" }} , 
 	{ "name": "p_ZL13encoder_frame_0_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_0", "role": "ce1" }} , 
 	{ "name": "p_ZL13encoder_frame_0_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_0", "role": "we1" }} , 
 	{ "name": "p_ZL13encoder_frame_0_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_0", "role": "d1" }} , 
 	{ "name": "p_ZL13encoder_frame_1_address0", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_1", "role": "address0" }} , 
 	{ "name": "p_ZL13encoder_frame_1_ce0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_1", "role": "ce0" }} , 
 	{ "name": "p_ZL13encoder_frame_1_we0", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_1", "role": "we0" }} , 
 	{ "name": "p_ZL13encoder_frame_1_d0", "direction": "out", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_1", "role": "d0" }} , 
 	{ "name": "p_ZL13encoder_frame_1_address1", "direction": "out", "datatype": "sc_lv", "bitwidth":9, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_1", "role": "address1" }} , 
 	{ "name": "p_ZL13encoder_frame_1_ce1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_1", "role": "ce1" }} , 
 	{ "name": "p_ZL13encoder_frame_1_we1", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_1", "role": "we1" }} , 
 	{ "name": "p_ZL13encoder_frame_1_d1", "direction": "out", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "p_ZL13encoder_frame_1", "role": "d1" }}  ]}

set ArgLastReadFirstWriteLatency {
	snn_top_hls_Pipeline_LOAD_FRAME {
		s_axis_data_V_data_V {Type I LastRead 0 FirstWrite -1}
		s_axis_data_V_keep_V {Type I LastRead 0 FirstWrite -1}
		s_axis_data_V_strb_V {Type I LastRead 0 FirstWrite -1}
		s_axis_data_V_user_V {Type I LastRead 0 FirstWrite -1}
		s_axis_data_V_last_V {Type I LastRead 0 FirstWrite -1}
		s_axis_data_V_id_V {Type I LastRead 0 FirstWrite -1}
		s_axis_data_V_dest_V {Type I LastRead 0 FirstWrite -1}
		p_ZL13encoder_frame_0 {Type O LastRead -1 FirstWrite 0}
		p_ZL13encoder_frame_1 {Type O LastRead -1 FirstWrite 0}}}

set hasDtUnsupportedChannel 0

set PerformanceInfo {[
	{"Name" : "Latency", "Min" : "2", "Max" : "198"}
	, {"Name" : "Interval", "Min" : "1", "Max" : "197"}
]}

set PipelineEnableSignalInfo {[
]}

set Spec2ImplPortList { 
	s_axis_data_V_data_V { axis {  { s_axis_data_TVALID in_vld 0 1 }  { s_axis_data_TDATA in_data 0 32 } } }
	s_axis_data_V_keep_V { axis {  { s_axis_data_TKEEP in_data 0 4 } } }
	s_axis_data_V_strb_V { axis {  { s_axis_data_TSTRB in_data 0 4 } } }
	s_axis_data_V_user_V { axis {  { s_axis_data_TUSER in_data 0 1 } } }
	s_axis_data_V_last_V { axis {  { s_axis_data_TLAST in_data 0 1 } } }
	s_axis_data_V_id_V { axis {  { s_axis_data_TID in_data 0 1 } } }
	s_axis_data_V_dest_V { axis {  { s_axis_data_TREADY in_acc 1 1 }  { s_axis_data_TDEST in_data 0 1 } } }
	p_ZL13encoder_frame_0 { ap_memory {  { p_ZL13encoder_frame_0_address0 mem_address 1 9 }  { p_ZL13encoder_frame_0_ce0 mem_ce 1 1 }  { p_ZL13encoder_frame_0_we0 mem_we 1 1 }  { p_ZL13encoder_frame_0_d0 mem_din 1 8 }  { p_ZL13encoder_frame_0_address1 MemPortADDR2 1 9 }  { p_ZL13encoder_frame_0_ce1 MemPortCE2 1 1 }  { p_ZL13encoder_frame_0_we1 MemPortWE2 1 1 }  { p_ZL13encoder_frame_0_d1 MemPortDIN2 1 8 } } }
	p_ZL13encoder_frame_1 { ap_memory {  { p_ZL13encoder_frame_1_address0 mem_address 1 9 }  { p_ZL13encoder_frame_1_ce0 mem_ce 1 1 }  { p_ZL13encoder_frame_1_we0 mem_we 1 1 }  { p_ZL13encoder_frame_1_d0 mem_din 1 8 }  { p_ZL13encoder_frame_1_address1 MemPortADDR2 1 9 }  { p_ZL13encoder_frame_1_ce1 MemPortCE2 1 1 }  { p_ZL13encoder_frame_1_we1 MemPortWE2 1 1 }  { p_ZL13encoder_frame_1_d1 MemPortDIN2 1 8 } } }
}
