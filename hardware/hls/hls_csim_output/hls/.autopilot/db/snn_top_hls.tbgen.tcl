set moduleName snn_top_hls
set isTopModule 1
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
set C_modelName {snn_top_hls}
set C_modelType { void 0 }
set ap_memory_interface_dict [dict create]
set C_modelArgList {
	{ ctrl_reg int 32 regular {axi_slave 0}  }
	{ config_reg int 32 regular {axi_slave 0}  }
	{ mode_reg int 32 regular {axi_slave 0}  }
	{ time_steps_reg int 32 regular {axi_slave 0}  }
	{ learning_params int 144 regular {axi_slave 0}  }
	{ encoder_config int 144 regular {axi_slave 0}  }
	{ status_reg int 32 regular {axi_slave 1}  }
	{ spike_count_reg int 32 regular {axi_slave 1}  }
	{ weight_sum_reg int 32 regular {axi_slave 1}  }
	{ version_reg int 32 regular {axi_slave 1}  }
	{ s_axis_spikes_V_data_V int 32 regular {axi_s 0 volatile  { s_axis_spikes Data } }  }
	{ s_axis_spikes_V_keep_V int 4 regular {axi_s 0 volatile  { s_axis_spikes Keep } }  }
	{ s_axis_spikes_V_strb_V int 4 regular {axi_s 0 volatile  { s_axis_spikes Strb } }  }
	{ s_axis_spikes_V_user_V int 1 regular {axi_s 0 volatile  { s_axis_spikes User } }  }
	{ s_axis_spikes_V_last_V int 1 regular {axi_s 0 volatile  { s_axis_spikes Last } }  }
	{ s_axis_spikes_V_id_V int 1 regular {axi_s 0 volatile  { s_axis_spikes ID } }  }
	{ s_axis_spikes_V_dest_V int 1 regular {axi_s 0 volatile  { s_axis_spikes Dest } }  }
	{ s_axis_data_V_data_V int 32 regular {axi_s 0 volatile  { s_axis_data Data } }  }
	{ s_axis_data_V_keep_V int 4 regular {axi_s 0 volatile  { s_axis_data Keep } }  }
	{ s_axis_data_V_strb_V int 4 regular {axi_s 0 volatile  { s_axis_data Strb } }  }
	{ s_axis_data_V_user_V int 1 regular {axi_s 0 volatile  { s_axis_data User } }  }
	{ s_axis_data_V_last_V int 1 regular {axi_s 0 volatile  { s_axis_data Last } }  }
	{ s_axis_data_V_id_V int 1 regular {axi_s 0 volatile  { s_axis_data ID } }  }
	{ s_axis_data_V_dest_V int 1 regular {axi_s 0 volatile  { s_axis_data Dest } }  }
	{ s_axis_weights_V_data_V int 32 regular {axi_s 0 volatile  { s_axis_weights Data } }  }
	{ s_axis_weights_V_keep_V int 4 regular {axi_s 0 volatile  { s_axis_weights Keep } }  }
	{ s_axis_weights_V_strb_V int 4 regular {axi_s 0 volatile  { s_axis_weights Strb } }  }
	{ s_axis_weights_V_user_V int 1 regular {axi_s 0 volatile  { s_axis_weights User } }  }
	{ s_axis_weights_V_last_V int 1 regular {axi_s 0 volatile  { s_axis_weights Last } }  }
	{ s_axis_weights_V_id_V int 1 regular {axi_s 0 volatile  { s_axis_weights ID } }  }
	{ s_axis_weights_V_dest_V int 1 regular {axi_s 0 volatile  { s_axis_weights Dest } }  }
	{ m_axis_spikes_V_data_V int 32 regular {axi_s 1 volatile  { m_axis_spikes Data } }  }
	{ m_axis_spikes_V_keep_V int 4 regular {axi_s 1 volatile  { m_axis_spikes Keep } }  }
	{ m_axis_spikes_V_strb_V int 4 regular {axi_s 1 volatile  { m_axis_spikes Strb } }  }
	{ m_axis_spikes_V_user_V int 1 regular {axi_s 1 volatile  { m_axis_spikes User } }  }
	{ m_axis_spikes_V_last_V int 1 regular {axi_s 1 volatile  { m_axis_spikes Last } }  }
	{ m_axis_spikes_V_id_V int 1 regular {axi_s 1 volatile  { m_axis_spikes ID } }  }
	{ m_axis_spikes_V_dest_V int 1 regular {axi_s 1 volatile  { m_axis_spikes Dest } }  }
	{ m_axis_weights_V_data_V int 32 regular {axi_s 1 volatile  { m_axis_weights Data } }  }
	{ m_axis_weights_V_keep_V int 4 regular {axi_s 1 volatile  { m_axis_weights Keep } }  }
	{ m_axis_weights_V_strb_V int 4 regular {axi_s 1 volatile  { m_axis_weights Strb } }  }
	{ m_axis_weights_V_user_V int 1 regular {axi_s 1 volatile  { m_axis_weights User } }  }
	{ m_axis_weights_V_last_V int 1 regular {axi_s 1 volatile  { m_axis_weights Last } }  }
	{ m_axis_weights_V_id_V int 1 regular {axi_s 1 volatile  { m_axis_weights ID } }  }
	{ m_axis_weights_V_dest_V int 1 regular {axi_s 1 volatile  { m_axis_weights Dest } }  }
	{ reward_signal int 8 regular {axi_slave 0}  }
	{ spike_in_valid int 1 regular {pointer 1}  }
	{ spike_in_neuron_id int 8 regular {pointer 1}  }
	{ spike_in_weight int 8 regular {pointer 1}  }
	{ spike_in_ready int 1 regular  }
	{ spike_out_valid int 1 regular  }
	{ spike_out_neuron_id int 8 regular  }
	{ spike_out_weight int 8 regular  }
	{ spike_out_ready int 1 regular {pointer 1}  }
	{ snn_enable int 1 regular {pointer 1}  }
	{ snn_reset int 1 regular {pointer 1}  }
	{ threshold_out int 16 regular {pointer 1}  }
	{ leak_rate_out int 16 regular {pointer 1}  }
	{ snn_ready int 1 regular  }
	{ snn_busy int 1 regular  }
}
set hasAXIMCache 0
set l_AXIML2Cache [list]
set AXIMCacheInstDict [dict create]
set C_modelArgMapList {[ 
	{ "Name" : "ctrl_reg", "interface" : "axi_slave", "bundle":"ctrl","type":"ap_none","bitwidth" : 32, "direction" : "READONLY", "offset" : {"in":16}, "offset_end" : {"in":23}} , 
 	{ "Name" : "config_reg", "interface" : "axi_slave", "bundle":"ctrl","type":"ap_none","bitwidth" : 32, "direction" : "READONLY", "offset" : {"in":24}, "offset_end" : {"in":31}} , 
 	{ "Name" : "mode_reg", "interface" : "axi_slave", "bundle":"ctrl","type":"ap_none","bitwidth" : 32, "direction" : "READONLY", "offset" : {"in":32}, "offset_end" : {"in":39}} , 
 	{ "Name" : "time_steps_reg", "interface" : "axi_slave", "bundle":"ctrl","type":"ap_none","bitwidth" : 32, "direction" : "READONLY", "offset" : {"in":40}, "offset_end" : {"in":47}} , 
 	{ "Name" : "learning_params", "interface" : "axi_slave", "bundle":"ctrl","type":"ap_none","bitwidth" : 144, "direction" : "READONLY", "offset" : {"in":48}, "offset_end" : {"in":71}} , 
 	{ "Name" : "encoder_config", "interface" : "axi_slave", "bundle":"ctrl","type":"ap_none","bitwidth" : 144, "direction" : "READONLY", "offset" : {"in":72}, "offset_end" : {"in":95}} , 
 	{ "Name" : "status_reg", "interface" : "axi_slave", "bundle":"ctrl","type":"ap_vld","bitwidth" : 32, "direction" : "WRITEONLY", "offset" : {"out":96}, "offset_end" : {"out":103}} , 
 	{ "Name" : "spike_count_reg", "interface" : "axi_slave", "bundle":"ctrl","type":"ap_vld","bitwidth" : 32, "direction" : "WRITEONLY", "offset" : {"out":112}, "offset_end" : {"out":119}} , 
 	{ "Name" : "weight_sum_reg", "interface" : "axi_slave", "bundle":"ctrl","type":"ap_vld","bitwidth" : 32, "direction" : "WRITEONLY", "offset" : {"out":128}, "offset_end" : {"out":135}} , 
 	{ "Name" : "version_reg", "interface" : "axi_slave", "bundle":"ctrl","type":"ap_vld","bitwidth" : 32, "direction" : "WRITEONLY", "offset" : {"out":144}, "offset_end" : {"out":151}} , 
 	{ "Name" : "s_axis_spikes_V_data_V", "interface" : "axis", "bitwidth" : 32, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_spikes_V_keep_V", "interface" : "axis", "bitwidth" : 4, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_spikes_V_strb_V", "interface" : "axis", "bitwidth" : 4, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_spikes_V_user_V", "interface" : "axis", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_spikes_V_last_V", "interface" : "axis", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_spikes_V_id_V", "interface" : "axis", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_spikes_V_dest_V", "interface" : "axis", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_data_V_data_V", "interface" : "axis", "bitwidth" : 32, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_data_V_keep_V", "interface" : "axis", "bitwidth" : 4, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_data_V_strb_V", "interface" : "axis", "bitwidth" : 4, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_data_V_user_V", "interface" : "axis", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_data_V_last_V", "interface" : "axis", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_data_V_id_V", "interface" : "axis", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_data_V_dest_V", "interface" : "axis", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_weights_V_data_V", "interface" : "axis", "bitwidth" : 32, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_weights_V_keep_V", "interface" : "axis", "bitwidth" : 4, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_weights_V_strb_V", "interface" : "axis", "bitwidth" : 4, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_weights_V_user_V", "interface" : "axis", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_weights_V_last_V", "interface" : "axis", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_weights_V_id_V", "interface" : "axis", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "s_axis_weights_V_dest_V", "interface" : "axis", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "m_axis_spikes_V_data_V", "interface" : "axis", "bitwidth" : 32, "direction" : "WRITEONLY"} , 
 	{ "Name" : "m_axis_spikes_V_keep_V", "interface" : "axis", "bitwidth" : 4, "direction" : "WRITEONLY"} , 
 	{ "Name" : "m_axis_spikes_V_strb_V", "interface" : "axis", "bitwidth" : 4, "direction" : "WRITEONLY"} , 
 	{ "Name" : "m_axis_spikes_V_user_V", "interface" : "axis", "bitwidth" : 1, "direction" : "WRITEONLY"} , 
 	{ "Name" : "m_axis_spikes_V_last_V", "interface" : "axis", "bitwidth" : 1, "direction" : "WRITEONLY"} , 
 	{ "Name" : "m_axis_spikes_V_id_V", "interface" : "axis", "bitwidth" : 1, "direction" : "WRITEONLY"} , 
 	{ "Name" : "m_axis_spikes_V_dest_V", "interface" : "axis", "bitwidth" : 1, "direction" : "WRITEONLY"} , 
 	{ "Name" : "m_axis_weights_V_data_V", "interface" : "axis", "bitwidth" : 32, "direction" : "WRITEONLY"} , 
 	{ "Name" : "m_axis_weights_V_keep_V", "interface" : "axis", "bitwidth" : 4, "direction" : "WRITEONLY"} , 
 	{ "Name" : "m_axis_weights_V_strb_V", "interface" : "axis", "bitwidth" : 4, "direction" : "WRITEONLY"} , 
 	{ "Name" : "m_axis_weights_V_user_V", "interface" : "axis", "bitwidth" : 1, "direction" : "WRITEONLY"} , 
 	{ "Name" : "m_axis_weights_V_last_V", "interface" : "axis", "bitwidth" : 1, "direction" : "WRITEONLY"} , 
 	{ "Name" : "m_axis_weights_V_id_V", "interface" : "axis", "bitwidth" : 1, "direction" : "WRITEONLY"} , 
 	{ "Name" : "m_axis_weights_V_dest_V", "interface" : "axis", "bitwidth" : 1, "direction" : "WRITEONLY"} , 
 	{ "Name" : "reward_signal", "interface" : "axi_slave", "bundle":"ctrl","type":"ap_none","bitwidth" : 8, "direction" : "READONLY", "offset" : {"in":160}, "offset_end" : {"in":167}} , 
 	{ "Name" : "spike_in_valid", "interface" : "wire", "bitwidth" : 1, "direction" : "WRITEONLY"} , 
 	{ "Name" : "spike_in_neuron_id", "interface" : "wire", "bitwidth" : 8, "direction" : "WRITEONLY"} , 
 	{ "Name" : "spike_in_weight", "interface" : "wire", "bitwidth" : 8, "direction" : "WRITEONLY"} , 
 	{ "Name" : "spike_in_ready", "interface" : "wire", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "spike_out_valid", "interface" : "wire", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "spike_out_neuron_id", "interface" : "wire", "bitwidth" : 8, "direction" : "READONLY"} , 
 	{ "Name" : "spike_out_weight", "interface" : "wire", "bitwidth" : 8, "direction" : "READONLY"} , 
 	{ "Name" : "spike_out_ready", "interface" : "wire", "bitwidth" : 1, "direction" : "WRITEONLY"} , 
 	{ "Name" : "snn_enable", "interface" : "wire", "bitwidth" : 1, "direction" : "WRITEONLY"} , 
 	{ "Name" : "snn_reset", "interface" : "wire", "bitwidth" : 1, "direction" : "WRITEONLY"} , 
 	{ "Name" : "threshold_out", "interface" : "wire", "bitwidth" : 16, "direction" : "WRITEONLY"} , 
 	{ "Name" : "leak_rate_out", "interface" : "wire", "bitwidth" : 16, "direction" : "WRITEONLY"} , 
 	{ "Name" : "snn_ready", "interface" : "wire", "bitwidth" : 1, "direction" : "READONLY"} , 
 	{ "Name" : "snn_busy", "interface" : "wire", "bitwidth" : 1, "direction" : "READONLY"} ]}
# RTL Port declarations: 
set portNum 79
set portList { 
	{ ap_clk sc_in sc_logic 1 clock -1 } 
	{ ap_rst_n sc_in sc_logic 1 reset -1 active_low_sync } 
	{ s_axis_spikes_TDATA sc_in sc_lv 32 signal 10 } 
	{ s_axis_spikes_TVALID sc_in sc_logic 1 invld 16 } 
	{ s_axis_spikes_TREADY sc_out sc_logic 1 inacc 16 } 
	{ s_axis_spikes_TKEEP sc_in sc_lv 4 signal 11 } 
	{ s_axis_spikes_TSTRB sc_in sc_lv 4 signal 12 } 
	{ s_axis_spikes_TUSER sc_in sc_lv 1 signal 13 } 
	{ s_axis_spikes_TLAST sc_in sc_lv 1 signal 14 } 
	{ s_axis_spikes_TID sc_in sc_lv 1 signal 15 } 
	{ s_axis_spikes_TDEST sc_in sc_lv 1 signal 16 } 
	{ s_axis_data_TDATA sc_in sc_lv 32 signal 17 } 
	{ s_axis_data_TVALID sc_in sc_logic 1 invld 23 } 
	{ s_axis_data_TREADY sc_out sc_logic 1 inacc 23 } 
	{ s_axis_data_TKEEP sc_in sc_lv 4 signal 18 } 
	{ s_axis_data_TSTRB sc_in sc_lv 4 signal 19 } 
	{ s_axis_data_TUSER sc_in sc_lv 1 signal 20 } 
	{ s_axis_data_TLAST sc_in sc_lv 1 signal 21 } 
	{ s_axis_data_TID sc_in sc_lv 1 signal 22 } 
	{ s_axis_data_TDEST sc_in sc_lv 1 signal 23 } 
	{ s_axis_weights_TDATA sc_in sc_lv 32 signal 24 } 
	{ s_axis_weights_TVALID sc_in sc_logic 1 invld 30 } 
	{ s_axis_weights_TREADY sc_out sc_logic 1 inacc 30 } 
	{ s_axis_weights_TKEEP sc_in sc_lv 4 signal 25 } 
	{ s_axis_weights_TSTRB sc_in sc_lv 4 signal 26 } 
	{ s_axis_weights_TUSER sc_in sc_lv 1 signal 27 } 
	{ s_axis_weights_TLAST sc_in sc_lv 1 signal 28 } 
	{ s_axis_weights_TID sc_in sc_lv 1 signal 29 } 
	{ s_axis_weights_TDEST sc_in sc_lv 1 signal 30 } 
	{ m_axis_spikes_TDATA sc_out sc_lv 32 signal 31 } 
	{ m_axis_spikes_TVALID sc_out sc_logic 1 outvld 37 } 
	{ m_axis_spikes_TREADY sc_in sc_logic 1 outacc 37 } 
	{ m_axis_spikes_TKEEP sc_out sc_lv 4 signal 32 } 
	{ m_axis_spikes_TSTRB sc_out sc_lv 4 signal 33 } 
	{ m_axis_spikes_TUSER sc_out sc_lv 1 signal 34 } 
	{ m_axis_spikes_TLAST sc_out sc_lv 1 signal 35 } 
	{ m_axis_spikes_TID sc_out sc_lv 1 signal 36 } 
	{ m_axis_spikes_TDEST sc_out sc_lv 1 signal 37 } 
	{ m_axis_weights_TDATA sc_out sc_lv 32 signal 38 } 
	{ m_axis_weights_TVALID sc_out sc_logic 1 outvld 44 } 
	{ m_axis_weights_TREADY sc_in sc_logic 1 outacc 44 } 
	{ m_axis_weights_TKEEP sc_out sc_lv 4 signal 39 } 
	{ m_axis_weights_TSTRB sc_out sc_lv 4 signal 40 } 
	{ m_axis_weights_TUSER sc_out sc_lv 1 signal 41 } 
	{ m_axis_weights_TLAST sc_out sc_lv 1 signal 42 } 
	{ m_axis_weights_TID sc_out sc_lv 1 signal 43 } 
	{ m_axis_weights_TDEST sc_out sc_lv 1 signal 44 } 
	{ spike_in_valid sc_out sc_lv 1 signal 46 } 
	{ spike_in_neuron_id sc_out sc_lv 8 signal 47 } 
	{ spike_in_weight sc_out sc_lv 8 signal 48 } 
	{ spike_in_ready sc_in sc_lv 1 signal 49 } 
	{ spike_out_valid sc_in sc_lv 1 signal 50 } 
	{ spike_out_neuron_id sc_in sc_lv 8 signal 51 } 
	{ spike_out_weight sc_in sc_lv 8 signal 52 } 
	{ spike_out_ready sc_out sc_lv 1 signal 53 } 
	{ snn_enable sc_out sc_lv 1 signal 54 } 
	{ snn_reset sc_out sc_lv 1 signal 55 } 
	{ threshold_out sc_out sc_lv 16 signal 56 } 
	{ leak_rate_out sc_out sc_lv 16 signal 57 } 
	{ snn_ready sc_in sc_lv 1 signal 58 } 
	{ snn_busy sc_in sc_lv 1 signal 59 } 
	{ s_axi_ctrl_AWVALID sc_in sc_logic 1 signal -1 } 
	{ s_axi_ctrl_AWREADY sc_out sc_logic 1 signal -1 } 
	{ s_axi_ctrl_AWADDR sc_in sc_lv 8 signal -1 } 
	{ s_axi_ctrl_WVALID sc_in sc_logic 1 signal -1 } 
	{ s_axi_ctrl_WREADY sc_out sc_logic 1 signal -1 } 
	{ s_axi_ctrl_WDATA sc_in sc_lv 32 signal -1 } 
	{ s_axi_ctrl_WSTRB sc_in sc_lv 4 signal -1 } 
	{ s_axi_ctrl_ARVALID sc_in sc_logic 1 signal -1 } 
	{ s_axi_ctrl_ARREADY sc_out sc_logic 1 signal -1 } 
	{ s_axi_ctrl_ARADDR sc_in sc_lv 8 signal -1 } 
	{ s_axi_ctrl_RVALID sc_out sc_logic 1 signal -1 } 
	{ s_axi_ctrl_RREADY sc_in sc_logic 1 signal -1 } 
	{ s_axi_ctrl_RDATA sc_out sc_lv 32 signal -1 } 
	{ s_axi_ctrl_RRESP sc_out sc_lv 2 signal -1 } 
	{ s_axi_ctrl_BVALID sc_out sc_logic 1 signal -1 } 
	{ s_axi_ctrl_BREADY sc_in sc_logic 1 signal -1 } 
	{ s_axi_ctrl_BRESP sc_out sc_lv 2 signal -1 } 
	{ interrupt sc_out sc_logic 1 signal -1 } 
}
set NewPortList {[ 
	{ "name": "s_axi_ctrl_AWADDR", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "ctrl", "role": "AWADDR" },"address":[{"name":"snn_top_hls","role":"start","value":"0","valid_bit":"0"},{"name":"snn_top_hls","role":"continue","value":"0","valid_bit":"4"},{"name":"snn_top_hls","role":"auto_start","value":"0","valid_bit":"7"},{"name":"ctrl_reg","role":"data","value":"16"},{"name":"config_reg","role":"data","value":"24"},{"name":"mode_reg","role":"data","value":"32"},{"name":"time_steps_reg","role":"data","value":"40"},{"name":"learning_params","role":"data","value":"48"},{"name":"encoder_config","role":"data","value":"72"},{"name":"reward_signal","role":"data","value":"160"}] },
	{ "name": "s_axi_ctrl_AWVALID", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "ctrl", "role": "AWVALID" } },
	{ "name": "s_axi_ctrl_AWREADY", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "ctrl", "role": "AWREADY" } },
	{ "name": "s_axi_ctrl_WVALID", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "ctrl", "role": "WVALID" } },
	{ "name": "s_axi_ctrl_WREADY", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "ctrl", "role": "WREADY" } },
	{ "name": "s_axi_ctrl_WDATA", "direction": "in", "datatype": "sc_lv", "bitwidth":32, "type": "signal", "bundle":{"name": "ctrl", "role": "WDATA" } },
	{ "name": "s_axi_ctrl_WSTRB", "direction": "in", "datatype": "sc_lv", "bitwidth":4, "type": "signal", "bundle":{"name": "ctrl", "role": "WSTRB" } },
	{ "name": "s_axi_ctrl_ARADDR", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "ctrl", "role": "ARADDR" },"address":[{"name":"snn_top_hls","role":"start","value":"0","valid_bit":"0"},{"name":"snn_top_hls","role":"done","value":"0","valid_bit":"1"},{"name":"snn_top_hls","role":"idle","value":"0","valid_bit":"2"},{"name":"snn_top_hls","role":"ready","value":"0","valid_bit":"3"},{"name":"snn_top_hls","role":"auto_start","value":"0","valid_bit":"7"},{"name":"status_reg","role":"data","value":"96"}, {"name":"status_reg","role":"valid","value":"100","valid_bit":"0"},{"name":"spike_count_reg","role":"data","value":"112"}, {"name":"spike_count_reg","role":"valid","value":"116","valid_bit":"0"},{"name":"weight_sum_reg","role":"data","value":"128"}, {"name":"weight_sum_reg","role":"valid","value":"132","valid_bit":"0"},{"name":"version_reg","role":"data","value":"144"}, {"name":"version_reg","role":"valid","value":"148","valid_bit":"0"}] },
	{ "name": "s_axi_ctrl_ARVALID", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "ctrl", "role": "ARVALID" } },
	{ "name": "s_axi_ctrl_ARREADY", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "ctrl", "role": "ARREADY" } },
	{ "name": "s_axi_ctrl_RVALID", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "ctrl", "role": "RVALID" } },
	{ "name": "s_axi_ctrl_RREADY", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "ctrl", "role": "RREADY" } },
	{ "name": "s_axi_ctrl_RDATA", "direction": "out", "datatype": "sc_lv", "bitwidth":32, "type": "signal", "bundle":{"name": "ctrl", "role": "RDATA" } },
	{ "name": "s_axi_ctrl_RRESP", "direction": "out", "datatype": "sc_lv", "bitwidth":2, "type": "signal", "bundle":{"name": "ctrl", "role": "RRESP" } },
	{ "name": "s_axi_ctrl_BVALID", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "ctrl", "role": "BVALID" } },
	{ "name": "s_axi_ctrl_BREADY", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "ctrl", "role": "BREADY" } },
	{ "name": "s_axi_ctrl_BRESP", "direction": "out", "datatype": "sc_lv", "bitwidth":2, "type": "signal", "bundle":{"name": "ctrl", "role": "BRESP" } },
	{ "name": "interrupt", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "signal", "bundle":{"name": "ctrl", "role": "interrupt" } }, 
 	{ "name": "ap_clk", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "clock", "bundle":{"name": "ap_clk", "role": "default" }} , 
 	{ "name": "ap_rst_n", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "reset", "bundle":{"name": "ap_rst_n", "role": "default" }} , 
 	{ "name": "s_axis_spikes_TDATA", "direction": "in", "datatype": "sc_lv", "bitwidth":32, "type": "signal", "bundle":{"name": "s_axis_spikes_V_data_V", "role": "default" }} , 
 	{ "name": "s_axis_spikes_TVALID", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "invld", "bundle":{"name": "s_axis_spikes_V_dest_V", "role": "default" }} , 
 	{ "name": "s_axis_spikes_TREADY", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "inacc", "bundle":{"name": "s_axis_spikes_V_dest_V", "role": "default" }} , 
 	{ "name": "s_axis_spikes_TKEEP", "direction": "in", "datatype": "sc_lv", "bitwidth":4, "type": "signal", "bundle":{"name": "s_axis_spikes_V_keep_V", "role": "default" }} , 
 	{ "name": "s_axis_spikes_TSTRB", "direction": "in", "datatype": "sc_lv", "bitwidth":4, "type": "signal", "bundle":{"name": "s_axis_spikes_V_strb_V", "role": "default" }} , 
 	{ "name": "s_axis_spikes_TUSER", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "s_axis_spikes_V_user_V", "role": "default" }} , 
 	{ "name": "s_axis_spikes_TLAST", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "s_axis_spikes_V_last_V", "role": "default" }} , 
 	{ "name": "s_axis_spikes_TID", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "s_axis_spikes_V_id_V", "role": "default" }} , 
 	{ "name": "s_axis_spikes_TDEST", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "s_axis_spikes_V_dest_V", "role": "default" }} , 
 	{ "name": "s_axis_data_TDATA", "direction": "in", "datatype": "sc_lv", "bitwidth":32, "type": "signal", "bundle":{"name": "s_axis_data_V_data_V", "role": "default" }} , 
 	{ "name": "s_axis_data_TVALID", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "invld", "bundle":{"name": "s_axis_data_V_dest_V", "role": "default" }} , 
 	{ "name": "s_axis_data_TREADY", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "inacc", "bundle":{"name": "s_axis_data_V_dest_V", "role": "default" }} , 
 	{ "name": "s_axis_data_TKEEP", "direction": "in", "datatype": "sc_lv", "bitwidth":4, "type": "signal", "bundle":{"name": "s_axis_data_V_keep_V", "role": "default" }} , 
 	{ "name": "s_axis_data_TSTRB", "direction": "in", "datatype": "sc_lv", "bitwidth":4, "type": "signal", "bundle":{"name": "s_axis_data_V_strb_V", "role": "default" }} , 
 	{ "name": "s_axis_data_TUSER", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "s_axis_data_V_user_V", "role": "default" }} , 
 	{ "name": "s_axis_data_TLAST", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "s_axis_data_V_last_V", "role": "default" }} , 
 	{ "name": "s_axis_data_TID", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "s_axis_data_V_id_V", "role": "default" }} , 
 	{ "name": "s_axis_data_TDEST", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "s_axis_data_V_dest_V", "role": "default" }} , 
 	{ "name": "s_axis_weights_TDATA", "direction": "in", "datatype": "sc_lv", "bitwidth":32, "type": "signal", "bundle":{"name": "s_axis_weights_V_data_V", "role": "default" }} , 
 	{ "name": "s_axis_weights_TVALID", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "invld", "bundle":{"name": "s_axis_weights_V_dest_V", "role": "default" }} , 
 	{ "name": "s_axis_weights_TREADY", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "inacc", "bundle":{"name": "s_axis_weights_V_dest_V", "role": "default" }} , 
 	{ "name": "s_axis_weights_TKEEP", "direction": "in", "datatype": "sc_lv", "bitwidth":4, "type": "signal", "bundle":{"name": "s_axis_weights_V_keep_V", "role": "default" }} , 
 	{ "name": "s_axis_weights_TSTRB", "direction": "in", "datatype": "sc_lv", "bitwidth":4, "type": "signal", "bundle":{"name": "s_axis_weights_V_strb_V", "role": "default" }} , 
 	{ "name": "s_axis_weights_TUSER", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "s_axis_weights_V_user_V", "role": "default" }} , 
 	{ "name": "s_axis_weights_TLAST", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "s_axis_weights_V_last_V", "role": "default" }} , 
 	{ "name": "s_axis_weights_TID", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "s_axis_weights_V_id_V", "role": "default" }} , 
 	{ "name": "s_axis_weights_TDEST", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "s_axis_weights_V_dest_V", "role": "default" }} , 
 	{ "name": "m_axis_spikes_TDATA", "direction": "out", "datatype": "sc_lv", "bitwidth":32, "type": "signal", "bundle":{"name": "m_axis_spikes_V_data_V", "role": "default" }} , 
 	{ "name": "m_axis_spikes_TVALID", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "outvld", "bundle":{"name": "m_axis_spikes_V_dest_V", "role": "default" }} , 
 	{ "name": "m_axis_spikes_TREADY", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "outacc", "bundle":{"name": "m_axis_spikes_V_dest_V", "role": "default" }} , 
 	{ "name": "m_axis_spikes_TKEEP", "direction": "out", "datatype": "sc_lv", "bitwidth":4, "type": "signal", "bundle":{"name": "m_axis_spikes_V_keep_V", "role": "default" }} , 
 	{ "name": "m_axis_spikes_TSTRB", "direction": "out", "datatype": "sc_lv", "bitwidth":4, "type": "signal", "bundle":{"name": "m_axis_spikes_V_strb_V", "role": "default" }} , 
 	{ "name": "m_axis_spikes_TUSER", "direction": "out", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "m_axis_spikes_V_user_V", "role": "default" }} , 
 	{ "name": "m_axis_spikes_TLAST", "direction": "out", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "m_axis_spikes_V_last_V", "role": "default" }} , 
 	{ "name": "m_axis_spikes_TID", "direction": "out", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "m_axis_spikes_V_id_V", "role": "default" }} , 
 	{ "name": "m_axis_spikes_TDEST", "direction": "out", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "m_axis_spikes_V_dest_V", "role": "default" }} , 
 	{ "name": "m_axis_weights_TDATA", "direction": "out", "datatype": "sc_lv", "bitwidth":32, "type": "signal", "bundle":{"name": "m_axis_weights_V_data_V", "role": "default" }} , 
 	{ "name": "m_axis_weights_TVALID", "direction": "out", "datatype": "sc_logic", "bitwidth":1, "type": "outvld", "bundle":{"name": "m_axis_weights_V_dest_V", "role": "default" }} , 
 	{ "name": "m_axis_weights_TREADY", "direction": "in", "datatype": "sc_logic", "bitwidth":1, "type": "outacc", "bundle":{"name": "m_axis_weights_V_dest_V", "role": "default" }} , 
 	{ "name": "m_axis_weights_TKEEP", "direction": "out", "datatype": "sc_lv", "bitwidth":4, "type": "signal", "bundle":{"name": "m_axis_weights_V_keep_V", "role": "default" }} , 
 	{ "name": "m_axis_weights_TSTRB", "direction": "out", "datatype": "sc_lv", "bitwidth":4, "type": "signal", "bundle":{"name": "m_axis_weights_V_strb_V", "role": "default" }} , 
 	{ "name": "m_axis_weights_TUSER", "direction": "out", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "m_axis_weights_V_user_V", "role": "default" }} , 
 	{ "name": "m_axis_weights_TLAST", "direction": "out", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "m_axis_weights_V_last_V", "role": "default" }} , 
 	{ "name": "m_axis_weights_TID", "direction": "out", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "m_axis_weights_V_id_V", "role": "default" }} , 
 	{ "name": "m_axis_weights_TDEST", "direction": "out", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "m_axis_weights_V_dest_V", "role": "default" }} , 
 	{ "name": "spike_in_valid", "direction": "out", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "spike_in_valid", "role": "default" }} , 
 	{ "name": "spike_in_neuron_id", "direction": "out", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "spike_in_neuron_id", "role": "default" }} , 
 	{ "name": "spike_in_weight", "direction": "out", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "spike_in_weight", "role": "default" }} , 
 	{ "name": "spike_in_ready", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "spike_in_ready", "role": "default" }} , 
 	{ "name": "spike_out_valid", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "spike_out_valid", "role": "default" }} , 
 	{ "name": "spike_out_neuron_id", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "spike_out_neuron_id", "role": "default" }} , 
 	{ "name": "spike_out_weight", "direction": "in", "datatype": "sc_lv", "bitwidth":8, "type": "signal", "bundle":{"name": "spike_out_weight", "role": "default" }} , 
 	{ "name": "spike_out_ready", "direction": "out", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "spike_out_ready", "role": "default" }} , 
 	{ "name": "snn_enable", "direction": "out", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "snn_enable", "role": "default" }} , 
 	{ "name": "snn_reset", "direction": "out", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "snn_reset", "role": "default" }} , 
 	{ "name": "threshold_out", "direction": "out", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "threshold_out", "role": "default" }} , 
 	{ "name": "leak_rate_out", "direction": "out", "datatype": "sc_lv", "bitwidth":16, "type": "signal", "bundle":{"name": "leak_rate_out", "role": "default" }} , 
 	{ "name": "snn_ready", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "snn_ready", "role": "default" }} , 
 	{ "name": "snn_busy", "direction": "in", "datatype": "sc_lv", "bitwidth":1, "type": "signal", "bundle":{"name": "snn_busy", "role": "default" }}  ]}

set ArgLastReadFirstWriteLatency {
	snn_top_hls {
		ctrl_reg {Type I LastRead 0 FirstWrite -1}
		config_reg {Type I LastRead 0 FirstWrite -1}
		mode_reg {Type I LastRead 0 FirstWrite -1}
		time_steps_reg {Type I LastRead 0 FirstWrite -1}
		learning_params {Type I LastRead 0 FirstWrite -1}
		encoder_config {Type I LastRead 0 FirstWrite -1}
		status_reg {Type O LastRead -1 FirstWrite 9}
		spike_count_reg {Type O LastRead -1 FirstWrite 9}
		weight_sum_reg {Type O LastRead -1 FirstWrite 9}
		version_reg {Type O LastRead -1 FirstWrite 9}
		s_axis_spikes_V_data_V {Type I LastRead 9 FirstWrite -1}
		s_axis_spikes_V_keep_V {Type I LastRead 9 FirstWrite -1}
		s_axis_spikes_V_strb_V {Type I LastRead 9 FirstWrite -1}
		s_axis_spikes_V_user_V {Type I LastRead 9 FirstWrite -1}
		s_axis_spikes_V_last_V {Type I LastRead 9 FirstWrite -1}
		s_axis_spikes_V_id_V {Type I LastRead 9 FirstWrite -1}
		s_axis_spikes_V_dest_V {Type I LastRead 9 FirstWrite -1}
		s_axis_data_V_data_V {Type I LastRead 3 FirstWrite -1}
		s_axis_data_V_keep_V {Type I LastRead 3 FirstWrite -1}
		s_axis_data_V_strb_V {Type I LastRead 3 FirstWrite -1}
		s_axis_data_V_user_V {Type I LastRead 3 FirstWrite -1}
		s_axis_data_V_last_V {Type I LastRead 3 FirstWrite -1}
		s_axis_data_V_id_V {Type I LastRead 3 FirstWrite -1}
		s_axis_data_V_dest_V {Type I LastRead 3 FirstWrite -1}
		s_axis_weights_V_data_V {Type I LastRead 2 FirstWrite -1}
		s_axis_weights_V_keep_V {Type I LastRead 2 FirstWrite -1}
		s_axis_weights_V_strb_V {Type I LastRead 2 FirstWrite -1}
		s_axis_weights_V_user_V {Type I LastRead 2 FirstWrite -1}
		s_axis_weights_V_last_V {Type I LastRead 2 FirstWrite -1}
		s_axis_weights_V_id_V {Type I LastRead 2 FirstWrite -1}
		s_axis_weights_V_dest_V {Type I LastRead 2 FirstWrite -1}
		m_axis_spikes_V_data_V {Type O LastRead 12 FirstWrite 12}
		m_axis_spikes_V_keep_V {Type O LastRead 12 FirstWrite 12}
		m_axis_spikes_V_strb_V {Type O LastRead 12 FirstWrite 12}
		m_axis_spikes_V_user_V {Type O LastRead 12 FirstWrite 12}
		m_axis_spikes_V_last_V {Type O LastRead 12 FirstWrite 12}
		m_axis_spikes_V_id_V {Type O LastRead 12 FirstWrite 12}
		m_axis_spikes_V_dest_V {Type O LastRead 12 FirstWrite 12}
		m_axis_weights_V_data_V {Type O LastRead 19 FirstWrite 20}
		m_axis_weights_V_keep_V {Type O LastRead 19 FirstWrite 20}
		m_axis_weights_V_strb_V {Type O LastRead 19 FirstWrite 20}
		m_axis_weights_V_user_V {Type O LastRead 19 FirstWrite 20}
		m_axis_weights_V_last_V {Type O LastRead 19 FirstWrite 20}
		m_axis_weights_V_id_V {Type O LastRead 19 FirstWrite 20}
		m_axis_weights_V_dest_V {Type O LastRead 19 FirstWrite 20}
		reward_signal {Type I LastRead 0 FirstWrite -1}
		spike_in_valid {Type O LastRead -1 FirstWrite 7}
		spike_in_neuron_id {Type O LastRead -1 FirstWrite 7}
		spike_in_weight {Type O LastRead -1 FirstWrite 7}
		spike_in_ready {Type I LastRead 0 FirstWrite -1}
		spike_out_valid {Type I LastRead 0 FirstWrite -1}
		spike_out_neuron_id {Type I LastRead 0 FirstWrite -1}
		spike_out_weight {Type I LastRead 0 FirstWrite -1}
		spike_out_ready {Type O LastRead -1 FirstWrite 7}
		snn_enable {Type O LastRead -1 FirstWrite 3}
		snn_reset {Type O LastRead -1 FirstWrite 3}
		threshold_out {Type O LastRead -1 FirstWrite 3}
		leak_rate_out {Type O LastRead -1 FirstWrite 3}
		snn_ready {Type I LastRead 0 FirstWrite -1}
		snn_busy {Type I LastRead 0 FirstWrite -1}
		initialized {Type IO LastRead -1 FirstWrite -1}
		last_mode {Type IO LastRead -1 FirstWrite -1}
		timestamp {Type IO LastRead -1 FirstWrite -1}
		spike_counter {Type IO LastRead -1 FirstWrite -1}
		encoder_spike_counter {Type IO LastRead -1 FirstWrite -1}
		checkpoint_col {Type IO LastRead -1 FirstWrite -1}
		encoder_frame_loaded {Type IO LastRead -1 FirstWrite -1}
		p_ZL22encoder_temporal_fired_0 {Type IO LastRead -1 FirstWrite -1}
		p_ZL22encoder_temporal_start_0 {Type IO LastRead -1 FirstWrite -1}
		p_ZL22encoder_temporal_fired_1 {Type IO LastRead -1 FirstWrite -1}
		p_ZL22encoder_temporal_start_1 {Type IO LastRead -1 FirstWrite -1}
		p_ZL15pre_eligibility_0 {Type IO LastRead -1 FirstWrite -1}
		p_ZL16post_eligibility_0 {Type IO LastRead -1 FirstWrite -1}
		p_ZL15pre_eligibility_1 {Type IO LastRead -1 FirstWrite -1}
		p_ZL16post_eligibility_1 {Type IO LastRead -1 FirstWrite -1}
		pre_traces_trace_0 {Type IO LastRead -1 FirstWrite -1}
		pre_traces_last_spike_time_0 {Type IO LastRead -1 FirstWrite -1}
		post_traces_trace_0 {Type IO LastRead -1 FirstWrite -1}
		post_traces_last_spike_time_0 {Type IO LastRead -1 FirstWrite -1}
		pre_traces_trace_1 {Type IO LastRead -1 FirstWrite -1}
		pre_traces_last_spike_time_1 {Type IO LastRead -1 FirstWrite -1}
		post_traces_trace_1 {Type IO LastRead -1 FirstWrite -1}
		post_traces_last_spike_time_1 {Type IO LastRead -1 FirstWrite -1}
		p_ZL17encoder_phase_acc_0 {Type IO LastRead -1 FirstWrite -1}
		p_ZL17encoder_phase_acc_1 {Type IO LastRead -1 FirstWrite -1}
		latency_window_counter {Type IO LastRead -1 FirstWrite -1}
		p_ZL13weight_memory_0 {Type IO LastRead -1 FirstWrite -1}
		p_ZL13weight_memory_1 {Type IO LastRead -1 FirstWrite -1}
		p_ZL13encoder_frame_0 {Type IO LastRead -1 FirstWrite -1}
		p_ZL13encoder_frame_1 {Type IO LastRead -1 FirstWrite -1}
		lfsr {Type IO LastRead -1 FirstWrite -1}
		EXP_DECAY_LUT {Type I LastRead -1 FirstWrite -1}}
	encoder_reset_temporal_state {
		now_val {Type I LastRead 0 FirstWrite -1}
		p_ZL22encoder_temporal_fired_0 {Type O LastRead -1 FirstWrite 0}
		p_ZL22encoder_temporal_start_0 {Type O LastRead -1 FirstWrite 0}
		p_ZL22encoder_temporal_fired_1 {Type O LastRead -1 FirstWrite 0}
		p_ZL22encoder_temporal_start_1 {Type O LastRead -1 FirstWrite 0}}
	snn_top_hls_Pipeline_RESET_ELIG {
		p_ZL15pre_eligibility_0 {Type O LastRead -1 FirstWrite 0}
		p_ZL16post_eligibility_0 {Type O LastRead -1 FirstWrite 0}
		p_ZL15pre_eligibility_1 {Type O LastRead -1 FirstWrite 0}
		p_ZL16post_eligibility_1 {Type O LastRead -1 FirstWrite 0}}
	snn_top_hls_Pipeline_RESET_TRACES {
		pre_traces_trace_0 {Type O LastRead -1 FirstWrite 0}
		pre_traces_last_spike_time_0 {Type O LastRead -1 FirstWrite 0}
		post_traces_trace_0 {Type O LastRead -1 FirstWrite 0}
		post_traces_last_spike_time_0 {Type O LastRead -1 FirstWrite 0}
		pre_traces_trace_1 {Type O LastRead -1 FirstWrite 0}
		pre_traces_last_spike_time_1 {Type O LastRead -1 FirstWrite 0}
		post_traces_trace_1 {Type O LastRead -1 FirstWrite 0}
		post_traces_last_spike_time_1 {Type O LastRead -1 FirstWrite 0}}
	snn_top_hls_Pipeline_RESET_ENCODER {
		p_ZL17encoder_phase_acc_0 {Type O LastRead -1 FirstWrite 0}
		p_ZL17encoder_phase_acc_1 {Type O LastRead -1 FirstWrite 0}}
	snn_top_hls_Pipeline_INIT_WEIGHT_OUTER_INIT_WEIGHT_INNER {
		p_ZL13weight_memory_0 {Type O LastRead -1 FirstWrite 1}
		p_ZL13weight_memory_1 {Type O LastRead -1 FirstWrite 1}}
	snn_top_hls_Pipeline_LOAD_FRAME {
		s_axis_data_V_data_V {Type I LastRead 0 FirstWrite -1}
		s_axis_data_V_keep_V {Type I LastRead 0 FirstWrite -1}
		s_axis_data_V_strb_V {Type I LastRead 0 FirstWrite -1}
		s_axis_data_V_user_V {Type I LastRead 0 FirstWrite -1}
		s_axis_data_V_last_V {Type I LastRead 0 FirstWrite -1}
		s_axis_data_V_id_V {Type I LastRead 0 FirstWrite -1}
		s_axis_data_V_dest_V {Type I LastRead 0 FirstWrite -1}
		p_ZL13encoder_frame_0 {Type O LastRead -1 FirstWrite 0}
		p_ZL13encoder_frame_1 {Type O LastRead -1 FirstWrite 0}}
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
		p_ZL13encoder_frame_1 {Type I LastRead 0 FirstWrite -1}}
	snn_top_hls_Pipeline_WEIGHT_SUM {
		weight_sum_out {Type O LastRead -1 FirstWrite 1}
		p_ZL13weight_memory_0 {Type I LastRead 2 FirstWrite -1}
		p_ZL13weight_memory_1 {Type I LastRead 2 FirstWrite -1}}
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
		p_ZL13weight_memory_1 {Type IO LastRead 5 FirstWrite 8}}
	process_post_spike_aer {
		post_id {Type I LastRead 0 FirstWrite -1}
		current_time {Type I LastRead 2 FirstWrite -1}
		post_traces_trace_0 {Type IO LastRead 2 FirstWrite 5}
		post_traces_trace_1 {Type IO LastRead 2 FirstWrite 5}
		post_traces_last_spike_time_0 {Type IO LastRead 0 FirstWrite 4}
		post_traces_last_spike_time_1 {Type IO LastRead 0 FirstWrite 4}
		EXP_DECAY_LUT {Type I LastRead 2 FirstWrite -1}
		pre_traces_trace_1 {Type I LastRead 2 FirstWrite -1}
		pre_traces_last_spike_time_1 {Type I LastRead 0 FirstWrite -1}
		pre_traces_trace_0 {Type I LastRead 0 FirstWrite -1}
		pre_traces_last_spike_time_0 {Type I LastRead 0 FirstWrite -1}
		p_ZL13weight_memory_0 {Type IO LastRead 5 FirstWrite 7}
		p_ZL13weight_memory_1 {Type IO LastRead 5 FirstWrite 7}}
	process_post_spike_aer_Pipeline_LTP_LOOP {
		lshr_ln {Type I LastRead 0 FirstWrite -1}
		current_time {Type I LastRead 0 FirstWrite -1}
		empty {Type I LastRead 0 FirstWrite -1}
		pre_traces_trace_1 {Type I LastRead 2 FirstWrite -1}
		pre_traces_last_spike_time_1 {Type I LastRead 0 FirstWrite -1}
		EXP_DECAY_LUT {Type I LastRead -1 FirstWrite -1}
		pre_traces_trace_0 {Type I LastRead 0 FirstWrite -1}
		pre_traces_last_spike_time_0 {Type I LastRead 0 FirstWrite -1}
		p_ZL13weight_memory_0 {Type IO LastRead 5 FirstWrite 7}
		p_ZL13weight_memory_1 {Type IO LastRead 5 FirstWrite 7}}
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
		p_ZL13weight_memory_1 {Type IO LastRead 2 FirstWrite 4}}
	decay_eligibility_traces {
		p_ZL15pre_eligibility_0 {Type IO LastRead 0 FirstWrite 2}
		p_ZL15pre_eligibility_1 {Type IO LastRead 0 FirstWrite 2}
		p_ZL16post_eligibility_0 {Type IO LastRead 0 FirstWrite 2}
		p_ZL16post_eligibility_1 {Type IO LastRead 0 FirstWrite 2}}
	decay_eligibility_traces_Pipeline_DECAY_PRE {
		p_ZL15pre_eligibility_0 {Type IO LastRead 0 FirstWrite 2}
		p_ZL15pre_eligibility_1 {Type IO LastRead 0 FirstWrite 2}}
	decay_eligibility_traces_Pipeline_DECAY_POST {
		p_ZL16post_eligibility_0 {Type IO LastRead 0 FirstWrite 2}
		p_ZL16post_eligibility_1 {Type IO LastRead 0 FirstWrite 2}}}

set hasDtUnsupportedChannel 0

set PerformanceInfo {[
	{"Name" : "Latency", "Min" : "36", "Max" : "4577686899"}
	, {"Name" : "Interval", "Min" : "37", "Max" : "4577686900"}
]}

set PipelineEnableSignalInfo {[
]}

set Spec2ImplPortList { 
	s_axis_spikes_V_data_V { axis {  { s_axis_spikes_TDATA in_data 0 32 } } }
	s_axis_spikes_V_keep_V { axis {  { s_axis_spikes_TKEEP in_data 0 4 } } }
	s_axis_spikes_V_strb_V { axis {  { s_axis_spikes_TSTRB in_data 0 4 } } }
	s_axis_spikes_V_user_V { axis {  { s_axis_spikes_TUSER in_data 0 1 } } }
	s_axis_spikes_V_last_V { axis {  { s_axis_spikes_TLAST in_data 0 1 } } }
	s_axis_spikes_V_id_V { axis {  { s_axis_spikes_TID in_data 0 1 } } }
	s_axis_spikes_V_dest_V { axis {  { s_axis_spikes_TVALID in_vld 0 1 }  { s_axis_spikes_TREADY in_acc 1 1 }  { s_axis_spikes_TDEST in_data 0 1 } } }
	s_axis_data_V_data_V { axis {  { s_axis_data_TDATA in_data 0 32 } } }
	s_axis_data_V_keep_V { axis {  { s_axis_data_TKEEP in_data 0 4 } } }
	s_axis_data_V_strb_V { axis {  { s_axis_data_TSTRB in_data 0 4 } } }
	s_axis_data_V_user_V { axis {  { s_axis_data_TUSER in_data 0 1 } } }
	s_axis_data_V_last_V { axis {  { s_axis_data_TLAST in_data 0 1 } } }
	s_axis_data_V_id_V { axis {  { s_axis_data_TID in_data 0 1 } } }
	s_axis_data_V_dest_V { axis {  { s_axis_data_TVALID in_vld 0 1 }  { s_axis_data_TREADY in_acc 1 1 }  { s_axis_data_TDEST in_data 0 1 } } }
	s_axis_weights_V_data_V { axis {  { s_axis_weights_TDATA in_data 0 32 } } }
	s_axis_weights_V_keep_V { axis {  { s_axis_weights_TKEEP in_data 0 4 } } }
	s_axis_weights_V_strb_V { axis {  { s_axis_weights_TSTRB in_data 0 4 } } }
	s_axis_weights_V_user_V { axis {  { s_axis_weights_TUSER in_data 0 1 } } }
	s_axis_weights_V_last_V { axis {  { s_axis_weights_TLAST in_data 0 1 } } }
	s_axis_weights_V_id_V { axis {  { s_axis_weights_TID in_data 0 1 } } }
	s_axis_weights_V_dest_V { axis {  { s_axis_weights_TVALID in_vld 0 1 }  { s_axis_weights_TREADY in_acc 1 1 }  { s_axis_weights_TDEST in_data 0 1 } } }
	m_axis_spikes_V_data_V { axis {  { m_axis_spikes_TDATA out_data 1 32 } } }
	m_axis_spikes_V_keep_V { axis {  { m_axis_spikes_TKEEP out_data 1 4 } } }
	m_axis_spikes_V_strb_V { axis {  { m_axis_spikes_TSTRB out_data 1 4 } } }
	m_axis_spikes_V_user_V { axis {  { m_axis_spikes_TUSER out_data 1 1 } } }
	m_axis_spikes_V_last_V { axis {  { m_axis_spikes_TLAST out_data 1 1 } } }
	m_axis_spikes_V_id_V { axis {  { m_axis_spikes_TID out_data 1 1 } } }
	m_axis_spikes_V_dest_V { axis {  { m_axis_spikes_TVALID out_vld 1 1 }  { m_axis_spikes_TREADY out_acc 0 1 }  { m_axis_spikes_TDEST out_data 1 1 } } }
	m_axis_weights_V_data_V { axis {  { m_axis_weights_TDATA out_data 1 32 } } }
	m_axis_weights_V_keep_V { axis {  { m_axis_weights_TKEEP out_data 1 4 } } }
	m_axis_weights_V_strb_V { axis {  { m_axis_weights_TSTRB out_data 1 4 } } }
	m_axis_weights_V_user_V { axis {  { m_axis_weights_TUSER out_data 1 1 } } }
	m_axis_weights_V_last_V { axis {  { m_axis_weights_TLAST out_data 1 1 } } }
	m_axis_weights_V_id_V { axis {  { m_axis_weights_TID out_data 1 1 } } }
	m_axis_weights_V_dest_V { axis {  { m_axis_weights_TVALID out_vld 1 1 }  { m_axis_weights_TREADY out_acc 0 1 }  { m_axis_weights_TDEST out_data 1 1 } } }
	spike_in_valid { ap_none {  { spike_in_valid out_data 1 1 } } }
	spike_in_neuron_id { ap_none {  { spike_in_neuron_id out_data 1 8 } } }
	spike_in_weight { ap_none {  { spike_in_weight out_data 1 8 } } }
	spike_in_ready { ap_none {  { spike_in_ready in_data 0 1 } } }
	spike_out_valid { ap_none {  { spike_out_valid in_data 0 1 } } }
	spike_out_neuron_id { ap_none {  { spike_out_neuron_id in_data 0 8 } } }
	spike_out_weight { ap_none {  { spike_out_weight in_data 0 8 } } }
	spike_out_ready { ap_none {  { spike_out_ready out_data 1 1 } } }
	snn_enable { ap_none {  { snn_enable out_data 1 1 } } }
	snn_reset { ap_none {  { snn_reset out_data 1 1 } } }
	threshold_out { ap_none {  { threshold_out out_data 1 16 } } }
	leak_rate_out { ap_none {  { leak_rate_out out_data 1 16 } } }
	snn_ready { ap_none {  { snn_ready in_data 0 1 } } }
	snn_busy { ap_none {  { snn_busy in_data 0 1 } } }
}

set maxi_interface_dict [dict create]

# RTL port scheduling information:
set fifoSchedulingInfoList { 
}

# RTL bus port read request latency information:
set busReadReqLatencyList { 
}

# RTL bus port write response latency information:
set busWriteResLatencyList { 
}

# RTL array port load latency information:
set memoryLoadLatencyList { 
}
