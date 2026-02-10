; ModuleID = '/mnt/workspace/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA/hardware/hls/hls_csim_output/hls/.autopilot/db/a.g.ld.5.gdce.bc'
source_filename = "llvm-link"
target datalayout = "e-m:e-i64:64-i128:128-i256:256-i512:512-i1024:1024-i2048:2048-i4096:4096-n8:16:32:64-S128-v16:16-v24:32-v32:32-v48:64-v96:128-v192:256-v256:256-v512:512-v1024:1024"
target triple = "fpga64-xilinx-none"

%struct.learning_params_t = type { %"struct.ap_uint<16>", %"struct.ap_uint<16>", %"struct.ap_uint<16>", %"struct.ap_uint<16>", %"struct.ap_uint<16>", %"struct.ap_uint<16>", i1, %"struct.ap_uint<16>", %"struct.ap_uint<16>" }
%"struct.ap_uint<16>" = type { %"struct.ap_int_base<16, false>" }
%"struct.ap_int_base<16, false>" = type { %"struct.ssdm_int<16, false>" }
%"struct.ssdm_int<16, false>" = type { i16 }
%struct.encoder_config_t = type { %"struct.ap_uint<4>", i1, %"struct.ap_uint<8>", %"struct.ap_uint<16>", %"struct.ap_uint<16>", %"struct.ap_uint<16>", %"struct.ap_uint<16>", %"struct.ap_uint<16>", %"struct.ap_uint<16>", %"struct.ap_uint<8>" }
%"struct.ap_uint<4>" = type { %"struct.ap_int_base<4, false>" }
%"struct.ap_int_base<4, false>" = type { %"struct.ssdm_int<4, false>" }
%"struct.ssdm_int<4, false>" = type { i4 }
%"struct.ap_uint<8>" = type { %"struct.ap_int_base<8, false>" }
%"struct.ap_int_base<8, false>" = type { %"struct.ssdm_int<8, false>" }
%"struct.ssdm_int<8, false>" = type { i8 }
%"struct.ap_uint<32>" = type { %"struct.ap_int_base<32, false>" }
%"struct.ap_int_base<32, false>" = type { %"struct.ssdm_int<32, false>" }
%"struct.ssdm_int<32, false>" = type { i32 }
%"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>" = type { %"struct.hls::axis<ap_uint<32>, 1, 1, 1>" }
%"struct.hls::axis<ap_uint<32>, 1, 1, 1>" = type { %"struct.ap_uint<32>", %"struct.ap_uint<4>", %"struct.ap_uint<4>", %"struct.ap_uint<1>", %"struct.ap_uint<1>", %"struct.ap_uint<1>", %"struct.ap_uint<1>" }
%"struct.ap_uint<1>" = type { %"struct.ap_int_base<1, false>" }
%"struct.ap_int_base<1, false>" = type { %"struct.ssdm_int<1, false>" }
%"struct.ssdm_int<1, false>" = type { i1 }

; Function Attrs: noinline willreturn
define void @apatb_snn_top_hls_ir(%"struct.ap_uint<32>"* nocapture readonly %ctrl_reg, %"struct.ap_uint<32>"* nocapture readonly %config_reg, %"struct.ap_uint<32>"* nocapture readonly %mode_reg, %"struct.ap_uint<32>"* nocapture readonly %time_steps_reg, %struct.learning_params_t* nocapture readonly %learning_params, %struct.encoder_config_t* nocapture readonly %encoder_config, %"struct.ap_uint<32>"* noalias nocapture nonnull align 4 dereferenceable(4) %status_reg, %"struct.ap_uint<32>"* noalias nocapture nonnull align 4 dereferenceable(4) %spike_count_reg, %"struct.ap_uint<32>"* noalias nocapture nonnull align 4 dereferenceable(4) %weight_sum_reg, %"struct.ap_uint<32>"* noalias nocapture nonnull align 4 dereferenceable(4) %version_reg, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias nonnull align 4 dereferenceable(12) %s_axis_spikes, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias nonnull align 4 dereferenceable(12) %s_axis_data, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias nonnull align 4 dereferenceable(12) %s_axis_weights, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias nonnull align 4 dereferenceable(12) %m_axis_spikes, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias nonnull align 4 dereferenceable(12) %m_axis_weights, %"struct.ap_uint<8>"* nocapture readonly %reward_signal, %"struct.ap_uint<1>"* noalias nocapture nonnull align 1 dereferenceable(1) %spike_in_valid, %"struct.ap_uint<8>"* noalias nocapture nonnull align 1 dereferenceable(1) %spike_in_neuron_id, %"struct.ap_uint<8>"* noalias nocapture nonnull align 1 dereferenceable(1) %spike_in_weight, %"struct.ap_uint<1>"* nocapture readonly %spike_in_ready, %"struct.ap_uint<1>"* nocapture readonly %spike_out_valid, %"struct.ap_uint<8>"* nocapture readonly %spike_out_neuron_id, %"struct.ap_uint<8>"* nocapture readonly %spike_out_weight, %"struct.ap_uint<1>"* noalias nocapture nonnull align 1 dereferenceable(1) %spike_out_ready, %"struct.ap_uint<1>"* noalias nocapture nonnull align 1 dereferenceable(1) %snn_enable, %"struct.ap_uint<1>"* noalias nocapture nonnull align 1 dereferenceable(1) %snn_reset, %"struct.ap_uint<16>"* noalias nocapture nonnull align 2 dereferenceable(2) %threshold_out, %"struct.ap_uint<16>"* noalias nocapture nonnull align 2 dereferenceable(2) %leak_rate_out, %"struct.ap_uint<1>"* nocapture readonly %snn_ready, %"struct.ap_uint<1>"* nocapture readonly %snn_busy) local_unnamed_addr #0 {
entry:
  %status_reg_copy = alloca i32, align 512
  %spike_count_reg_copy = alloca i32, align 512
  %weight_sum_reg_copy = alloca i32, align 512
  %version_reg_copy = alloca i32, align 512
  %s_axis_spikes_copy.data = alloca i32, align 512
  %s_axis_spikes_copy.keep = alloca i4, align 512
  %s_axis_spikes_copy.strb = alloca i4, align 512
  %s_axis_spikes_copy.user = alloca i1, align 512
  %s_axis_spikes_copy.last = alloca i1, align 512
  %s_axis_spikes_copy.id = alloca i1, align 512
  %s_axis_spikes_copy.dest = alloca i1, align 512
  %s_axis_data_copy.data = alloca i32, align 512
  %s_axis_data_copy.keep = alloca i4, align 512
  %s_axis_data_copy.strb = alloca i4, align 512
  %s_axis_data_copy.user = alloca i1, align 512
  %s_axis_data_copy.last = alloca i1, align 512
  %s_axis_data_copy.id = alloca i1, align 512
  %s_axis_data_copy.dest = alloca i1, align 512
  %s_axis_weights_copy.data = alloca i32, align 512
  %s_axis_weights_copy.keep = alloca i4, align 512
  %s_axis_weights_copy.strb = alloca i4, align 512
  %s_axis_weights_copy.user = alloca i1, align 512
  %s_axis_weights_copy.last = alloca i1, align 512
  %s_axis_weights_copy.id = alloca i1, align 512
  %s_axis_weights_copy.dest = alloca i1, align 512
  %m_axis_spikes_copy.data = alloca i32, align 512
  %m_axis_spikes_copy.keep = alloca i4, align 512
  %m_axis_spikes_copy.strb = alloca i4, align 512
  %m_axis_spikes_copy.user = alloca i1, align 512
  %m_axis_spikes_copy.last = alloca i1, align 512
  %m_axis_spikes_copy.id = alloca i1, align 512
  %m_axis_spikes_copy.dest = alloca i1, align 512
  %m_axis_weights_copy.data = alloca i32, align 512
  %m_axis_weights_copy.keep = alloca i4, align 512
  %m_axis_weights_copy.strb = alloca i4, align 512
  %m_axis_weights_copy.user = alloca i1, align 512
  %m_axis_weights_copy.last = alloca i1, align 512
  %m_axis_weights_copy.id = alloca i1, align 512
  %m_axis_weights_copy.dest = alloca i1, align 512
  %spike_in_valid_copy = alloca i1, align 512
  %spike_in_neuron_id_copy = alloca i8, align 512
  %spike_in_weight_copy = alloca i8, align 512
  %spike_out_ready_copy = alloca i1, align 512
  %snn_enable_copy = alloca i1, align 512
  %snn_reset_copy = alloca i1, align 512
  %threshold_out_copy = alloca i16, align 512
  %leak_rate_out_copy = alloca i16, align 512
  call fastcc void @copy_in(%"struct.ap_uint<32>"* nonnull %status_reg, i32* nonnull align 512 %status_reg_copy, %"struct.ap_uint<32>"* nonnull %spike_count_reg, i32* nonnull align 512 %spike_count_reg_copy, %"struct.ap_uint<32>"* nonnull %weight_sum_reg, i32* nonnull align 512 %weight_sum_reg_copy, %"struct.ap_uint<32>"* nonnull %version_reg, i32* nonnull align 512 %version_reg_copy, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* nonnull %s_axis_spikes, i32* nonnull align 512 %s_axis_spikes_copy.data, i4* nonnull align 512 %s_axis_spikes_copy.keep, i4* nonnull align 512 %s_axis_spikes_copy.strb, i1* nonnull align 512 %s_axis_spikes_copy.user, i1* nonnull align 512 %s_axis_spikes_copy.last, i1* nonnull align 512 %s_axis_spikes_copy.id, i1* nonnull align 512 %s_axis_spikes_copy.dest, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* nonnull %s_axis_data, i32* nonnull align 512 %s_axis_data_copy.data, i4* nonnull align 512 %s_axis_data_copy.keep, i4* nonnull align 512 %s_axis_data_copy.strb, i1* nonnull align 512 %s_axis_data_copy.user, i1* nonnull align 512 %s_axis_data_copy.last, i1* nonnull align 512 %s_axis_data_copy.id, i1* nonnull align 512 %s_axis_data_copy.dest, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* nonnull %s_axis_weights, i32* nonnull align 512 %s_axis_weights_copy.data, i4* nonnull align 512 %s_axis_weights_copy.keep, i4* nonnull align 512 %s_axis_weights_copy.strb, i1* nonnull align 512 %s_axis_weights_copy.user, i1* nonnull align 512 %s_axis_weights_copy.last, i1* nonnull align 512 %s_axis_weights_copy.id, i1* nonnull align 512 %s_axis_weights_copy.dest, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* nonnull %m_axis_spikes, i32* nonnull align 512 %m_axis_spikes_copy.data, i4* nonnull align 512 %m_axis_spikes_copy.keep, i4* nonnull align 512 %m_axis_spikes_copy.strb, i1* nonnull align 512 %m_axis_spikes_copy.user, i1* nonnull align 512 %m_axis_spikes_copy.last, i1* nonnull align 512 %m_axis_spikes_copy.id, i1* nonnull align 512 %m_axis_spikes_copy.dest, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* nonnull %m_axis_weights, i32* nonnull align 512 %m_axis_weights_copy.data, i4* nonnull align 512 %m_axis_weights_copy.keep, i4* nonnull align 512 %m_axis_weights_copy.strb, i1* nonnull align 512 %m_axis_weights_copy.user, i1* nonnull align 512 %m_axis_weights_copy.last, i1* nonnull align 512 %m_axis_weights_copy.id, i1* nonnull align 512 %m_axis_weights_copy.dest, %"struct.ap_uint<1>"* nonnull %spike_in_valid, i1* nonnull align 512 %spike_in_valid_copy, %"struct.ap_uint<8>"* nonnull %spike_in_neuron_id, i8* nonnull align 512 %spike_in_neuron_id_copy, %"struct.ap_uint<8>"* nonnull %spike_in_weight, i8* nonnull align 512 %spike_in_weight_copy, %"struct.ap_uint<1>"* nonnull %spike_out_ready, i1* nonnull align 512 %spike_out_ready_copy, %"struct.ap_uint<1>"* nonnull %snn_enable, i1* nonnull align 512 %snn_enable_copy, %"struct.ap_uint<1>"* nonnull %snn_reset, i1* nonnull align 512 %snn_reset_copy, %"struct.ap_uint<16>"* nonnull %threshold_out, i16* nonnull align 512 %threshold_out_copy, %"struct.ap_uint<16>"* nonnull %leak_rate_out, i16* nonnull align 512 %leak_rate_out_copy)
  call void @apatb_snn_top_hls_hw(%"struct.ap_uint<32>"* %ctrl_reg, %"struct.ap_uint<32>"* %config_reg, %"struct.ap_uint<32>"* %mode_reg, %"struct.ap_uint<32>"* %time_steps_reg, %struct.learning_params_t* %learning_params, %struct.encoder_config_t* %encoder_config, i32* %status_reg_copy, i32* %spike_count_reg_copy, i32* %weight_sum_reg_copy, i32* %version_reg_copy, i32* %s_axis_spikes_copy.data, i4* %s_axis_spikes_copy.keep, i4* %s_axis_spikes_copy.strb, i1* %s_axis_spikes_copy.user, i1* %s_axis_spikes_copy.last, i1* %s_axis_spikes_copy.id, i1* %s_axis_spikes_copy.dest, i32* %s_axis_data_copy.data, i4* %s_axis_data_copy.keep, i4* %s_axis_data_copy.strb, i1* %s_axis_data_copy.user, i1* %s_axis_data_copy.last, i1* %s_axis_data_copy.id, i1* %s_axis_data_copy.dest, i32* %s_axis_weights_copy.data, i4* %s_axis_weights_copy.keep, i4* %s_axis_weights_copy.strb, i1* %s_axis_weights_copy.user, i1* %s_axis_weights_copy.last, i1* %s_axis_weights_copy.id, i1* %s_axis_weights_copy.dest, i32* %m_axis_spikes_copy.data, i4* %m_axis_spikes_copy.keep, i4* %m_axis_spikes_copy.strb, i1* %m_axis_spikes_copy.user, i1* %m_axis_spikes_copy.last, i1* %m_axis_spikes_copy.id, i1* %m_axis_spikes_copy.dest, i32* %m_axis_weights_copy.data, i4* %m_axis_weights_copy.keep, i4* %m_axis_weights_copy.strb, i1* %m_axis_weights_copy.user, i1* %m_axis_weights_copy.last, i1* %m_axis_weights_copy.id, i1* %m_axis_weights_copy.dest, %"struct.ap_uint<8>"* %reward_signal, i1* %spike_in_valid_copy, i8* %spike_in_neuron_id_copy, i8* %spike_in_weight_copy, %"struct.ap_uint<1>"* %spike_in_ready, %"struct.ap_uint<1>"* %spike_out_valid, %"struct.ap_uint<8>"* %spike_out_neuron_id, %"struct.ap_uint<8>"* %spike_out_weight, i1* %spike_out_ready_copy, i1* %snn_enable_copy, i1* %snn_reset_copy, i16* %threshold_out_copy, i16* %leak_rate_out_copy, %"struct.ap_uint<1>"* %snn_ready, %"struct.ap_uint<1>"* %snn_busy)
  call void @copy_back(%"struct.ap_uint<32>"* %status_reg, i32* %status_reg_copy, %"struct.ap_uint<32>"* %spike_count_reg, i32* %spike_count_reg_copy, %"struct.ap_uint<32>"* %weight_sum_reg, i32* %weight_sum_reg_copy, %"struct.ap_uint<32>"* %version_reg, i32* %version_reg_copy, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %s_axis_spikes, i32* %s_axis_spikes_copy.data, i4* %s_axis_spikes_copy.keep, i4* %s_axis_spikes_copy.strb, i1* %s_axis_spikes_copy.user, i1* %s_axis_spikes_copy.last, i1* %s_axis_spikes_copy.id, i1* %s_axis_spikes_copy.dest, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %s_axis_data, i32* %s_axis_data_copy.data, i4* %s_axis_data_copy.keep, i4* %s_axis_data_copy.strb, i1* %s_axis_data_copy.user, i1* %s_axis_data_copy.last, i1* %s_axis_data_copy.id, i1* %s_axis_data_copy.dest, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %s_axis_weights, i32* %s_axis_weights_copy.data, i4* %s_axis_weights_copy.keep, i4* %s_axis_weights_copy.strb, i1* %s_axis_weights_copy.user, i1* %s_axis_weights_copy.last, i1* %s_axis_weights_copy.id, i1* %s_axis_weights_copy.dest, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %m_axis_spikes, i32* %m_axis_spikes_copy.data, i4* %m_axis_spikes_copy.keep, i4* %m_axis_spikes_copy.strb, i1* %m_axis_spikes_copy.user, i1* %m_axis_spikes_copy.last, i1* %m_axis_spikes_copy.id, i1* %m_axis_spikes_copy.dest, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %m_axis_weights, i32* %m_axis_weights_copy.data, i4* %m_axis_weights_copy.keep, i4* %m_axis_weights_copy.strb, i1* %m_axis_weights_copy.user, i1* %m_axis_weights_copy.last, i1* %m_axis_weights_copy.id, i1* %m_axis_weights_copy.dest, %"struct.ap_uint<1>"* %spike_in_valid, i1* %spike_in_valid_copy, %"struct.ap_uint<8>"* %spike_in_neuron_id, i8* %spike_in_neuron_id_copy, %"struct.ap_uint<8>"* %spike_in_weight, i8* %spike_in_weight_copy, %"struct.ap_uint<1>"* %spike_out_ready, i1* %spike_out_ready_copy, %"struct.ap_uint<1>"* %snn_enable, i1* %snn_enable_copy, %"struct.ap_uint<1>"* %snn_reset, i1* %snn_reset_copy, %"struct.ap_uint<16>"* %threshold_out, i16* %threshold_out_copy, %"struct.ap_uint<16>"* %leak_rate_out, i16* %leak_rate_out_copy)
  ret void
}

; Function Attrs: argmemonly noinline willreturn
define internal fastcc void @copy_in(%"struct.ap_uint<32>"* noalias readonly "unpacked"="0", i32* noalias nocapture align 512 "unpacked"="1.0", %"struct.ap_uint<32>"* noalias readonly "unpacked"="2", i32* noalias nocapture align 512 "unpacked"="3.0", %"struct.ap_uint<32>"* noalias readonly "unpacked"="4", i32* noalias nocapture align 512 "unpacked"="5.0", %"struct.ap_uint<32>"* noalias readonly "unpacked"="6", i32* noalias nocapture align 512 "unpacked"="7.0", %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias "unpacked"="8", i32* noalias align 512 "unpacked"="9.0" %_V_data_V, i4* noalias align 512 "unpacked"="9.1" %_V_keep_V, i4* noalias align 512 "unpacked"="9.2" %_V_strb_V, i1* noalias align 512 "unpacked"="9.3" %_V_user_V, i1* noalias align 512 "unpacked"="9.4" %_V_last_V, i1* noalias align 512 "unpacked"="9.5" %_V_id_V, i1* noalias align 512 "unpacked"="9.6" %_V_dest_V, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias "unpacked"="10", i32* noalias align 512 "unpacked"="11.0" %_V_data_V1, i4* noalias align 512 "unpacked"="11.1" %_V_keep_V2, i4* noalias align 512 "unpacked"="11.2" %_V_strb_V3, i1* noalias align 512 "unpacked"="11.3" %_V_user_V4, i1* noalias align 512 "unpacked"="11.4" %_V_last_V5, i1* noalias align 512 "unpacked"="11.5" %_V_id_V6, i1* noalias align 512 "unpacked"="11.6" %_V_dest_V7, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias "unpacked"="12", i32* noalias align 512 "unpacked"="13.0" %_V_data_V18, i4* noalias align 512 "unpacked"="13.1" %_V_keep_V29, i4* noalias align 512 "unpacked"="13.2" %_V_strb_V310, i1* noalias align 512 "unpacked"="13.3" %_V_user_V411, i1* noalias align 512 "unpacked"="13.4" %_V_last_V512, i1* noalias align 512 "unpacked"="13.5" %_V_id_V613, i1* noalias align 512 "unpacked"="13.6" %_V_dest_V714, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias "unpacked"="14", i32* noalias align 512 "unpacked"="15.0" %_V_data_V1815, i4* noalias align 512 "unpacked"="15.1" %_V_keep_V2916, i4* noalias align 512 "unpacked"="15.2" %_V_strb_V31017, i1* noalias align 512 "unpacked"="15.3" %_V_user_V41118, i1* noalias align 512 "unpacked"="15.4" %_V_last_V51219, i1* noalias align 512 "unpacked"="15.5" %_V_id_V61320, i1* noalias align 512 "unpacked"="15.6" %_V_dest_V71421, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias "unpacked"="16", i32* noalias align 512 "unpacked"="17.0" %_V_data_V181522, i4* noalias align 512 "unpacked"="17.1" %_V_keep_V291623, i4* noalias align 512 "unpacked"="17.2" %_V_strb_V3101724, i1* noalias align 512 "unpacked"="17.3" %_V_user_V4111825, i1* noalias align 512 "unpacked"="17.4" %_V_last_V5121926, i1* noalias align 512 "unpacked"="17.5" %_V_id_V6132027, i1* noalias align 512 "unpacked"="17.6" %_V_dest_V7142128, %"struct.ap_uint<1>"* noalias readonly "unpacked"="18", i1* noalias nocapture align 512 "unpacked"="19.0", %"struct.ap_uint<8>"* noalias readonly "unpacked"="20", i8* noalias nocapture align 512 "unpacked"="21.0", %"struct.ap_uint<8>"* noalias readonly "unpacked"="22", i8* noalias nocapture align 512 "unpacked"="23.0", %"struct.ap_uint<1>"* noalias readonly "unpacked"="24", i1* noalias nocapture align 512 "unpacked"="25.0", %"struct.ap_uint<1>"* noalias readonly "unpacked"="26", i1* noalias nocapture align 512 "unpacked"="27.0", %"struct.ap_uint<1>"* noalias readonly "unpacked"="28", i1* noalias nocapture align 512 "unpacked"="29.0", %"struct.ap_uint<16>"* noalias readonly "unpacked"="30", i16* noalias nocapture align 512 "unpacked"="31.0", %"struct.ap_uint<16>"* noalias readonly "unpacked"="32", i16* noalias nocapture align 512 "unpacked"="33.0") unnamed_addr #1 {
entry:
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<32>.179"(i32* align 512 %1, %"struct.ap_uint<32>"* %0)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<32>.179"(i32* align 512 %3, %"struct.ap_uint<32>"* %2)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<32>.179"(i32* align 512 %5, %"struct.ap_uint<32>"* %4)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<32>.179"(i32* align 512 %7, %"struct.ap_uint<32>"* %6)
  call fastcc void @"onebyonecpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"(i32* align 512 %_V_data_V, i4* align 512 %_V_keep_V, i4* align 512 %_V_strb_V, i1* align 512 %_V_user_V, i1* align 512 %_V_last_V, i1* align 512 %_V_id_V, i1* align 512 %_V_dest_V, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %8)
  call fastcc void @"onebyonecpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"(i32* align 512 %_V_data_V1, i4* align 512 %_V_keep_V2, i4* align 512 %_V_strb_V3, i1* align 512 %_V_user_V4, i1* align 512 %_V_last_V5, i1* align 512 %_V_id_V6, i1* align 512 %_V_dest_V7, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %9)
  call fastcc void @"onebyonecpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"(i32* align 512 %_V_data_V18, i4* align 512 %_V_keep_V29, i4* align 512 %_V_strb_V310, i1* align 512 %_V_user_V411, i1* align 512 %_V_last_V512, i1* align 512 %_V_id_V613, i1* align 512 %_V_dest_V714, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %10)
  call fastcc void @"onebyonecpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"(i32* align 512 %_V_data_V1815, i4* align 512 %_V_keep_V2916, i4* align 512 %_V_strb_V31017, i1* align 512 %_V_user_V41118, i1* align 512 %_V_last_V51219, i1* align 512 %_V_id_V61320, i1* align 512 %_V_dest_V71421, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %11)
  call fastcc void @"onebyonecpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"(i32* align 512 %_V_data_V181522, i4* align 512 %_V_keep_V291623, i4* align 512 %_V_strb_V3101724, i1* align 512 %_V_user_V4111825, i1* align 512 %_V_last_V5121926, i1* align 512 %_V_id_V6132027, i1* align 512 %_V_dest_V7142128, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %12)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<1>.147"(i1* align 512 %14, %"struct.ap_uint<1>"* %13)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<8>"(i8* align 512 %16, %"struct.ap_uint<8>"* %15)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<8>"(i8* align 512 %18, %"struct.ap_uint<8>"* %17)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<1>.147"(i1* align 512 %20, %"struct.ap_uint<1>"* %19)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<1>.147"(i1* align 512 %22, %"struct.ap_uint<1>"* %21)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<1>.147"(i1* align 512 %24, %"struct.ap_uint<1>"* %23)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<16>.134"(i16* align 512 %26, %"struct.ap_uint<16>"* %25)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<16>.134"(i16* align 512 %28, %"struct.ap_uint<16>"* %27)
  ret void
}

; Function Attrs: argmemonly noinline willreturn
define internal fastcc void @copy_out(%"struct.ap_uint<32>"* noalias "unpacked"="0", i32* noalias nocapture readonly align 512 "unpacked"="1.0", %"struct.ap_uint<32>"* noalias "unpacked"="2", i32* noalias nocapture readonly align 512 "unpacked"="3.0", %"struct.ap_uint<32>"* noalias "unpacked"="4", i32* noalias nocapture readonly align 512 "unpacked"="5.0", %"struct.ap_uint<32>"* noalias "unpacked"="6", i32* noalias nocapture readonly align 512 "unpacked"="7.0", %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias "unpacked"="8", i32* noalias align 512 "unpacked"="9.0" %_V_data_V, i4* noalias align 512 "unpacked"="9.1" %_V_keep_V, i4* noalias align 512 "unpacked"="9.2" %_V_strb_V, i1* noalias align 512 "unpacked"="9.3" %_V_user_V, i1* noalias align 512 "unpacked"="9.4" %_V_last_V, i1* noalias align 512 "unpacked"="9.5" %_V_id_V, i1* noalias align 512 "unpacked"="9.6" %_V_dest_V, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias "unpacked"="10", i32* noalias align 512 "unpacked"="11.0" %_V_data_V1, i4* noalias align 512 "unpacked"="11.1" %_V_keep_V2, i4* noalias align 512 "unpacked"="11.2" %_V_strb_V3, i1* noalias align 512 "unpacked"="11.3" %_V_user_V4, i1* noalias align 512 "unpacked"="11.4" %_V_last_V5, i1* noalias align 512 "unpacked"="11.5" %_V_id_V6, i1* noalias align 512 "unpacked"="11.6" %_V_dest_V7, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias "unpacked"="12", i32* noalias align 512 "unpacked"="13.0" %_V_data_V18, i4* noalias align 512 "unpacked"="13.1" %_V_keep_V29, i4* noalias align 512 "unpacked"="13.2" %_V_strb_V310, i1* noalias align 512 "unpacked"="13.3" %_V_user_V411, i1* noalias align 512 "unpacked"="13.4" %_V_last_V512, i1* noalias align 512 "unpacked"="13.5" %_V_id_V613, i1* noalias align 512 "unpacked"="13.6" %_V_dest_V714, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias "unpacked"="14", i32* noalias align 512 "unpacked"="15.0" %_V_data_V1815, i4* noalias align 512 "unpacked"="15.1" %_V_keep_V2916, i4* noalias align 512 "unpacked"="15.2" %_V_strb_V31017, i1* noalias align 512 "unpacked"="15.3" %_V_user_V41118, i1* noalias align 512 "unpacked"="15.4" %_V_last_V51219, i1* noalias align 512 "unpacked"="15.5" %_V_id_V61320, i1* noalias align 512 "unpacked"="15.6" %_V_dest_V71421, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias "unpacked"="16", i32* noalias align 512 "unpacked"="17.0" %_V_data_V181522, i4* noalias align 512 "unpacked"="17.1" %_V_keep_V291623, i4* noalias align 512 "unpacked"="17.2" %_V_strb_V3101724, i1* noalias align 512 "unpacked"="17.3" %_V_user_V4111825, i1* noalias align 512 "unpacked"="17.4" %_V_last_V5121926, i1* noalias align 512 "unpacked"="17.5" %_V_id_V6132027, i1* noalias align 512 "unpacked"="17.6" %_V_dest_V7142128, %"struct.ap_uint<1>"* noalias "unpacked"="18", i1* noalias nocapture readonly align 512 "unpacked"="19.0", %"struct.ap_uint<8>"* noalias "unpacked"="20", i8* noalias nocapture readonly align 512 "unpacked"="21.0", %"struct.ap_uint<8>"* noalias "unpacked"="22", i8* noalias nocapture readonly align 512 "unpacked"="23.0", %"struct.ap_uint<1>"* noalias "unpacked"="24", i1* noalias nocapture readonly align 512 "unpacked"="25.0", %"struct.ap_uint<1>"* noalias "unpacked"="26", i1* noalias nocapture readonly align 512 "unpacked"="27.0", %"struct.ap_uint<1>"* noalias "unpacked"="28", i1* noalias nocapture readonly align 512 "unpacked"="29.0", %"struct.ap_uint<16>"* noalias "unpacked"="30", i16* noalias nocapture readonly align 512 "unpacked"="31.0", %"struct.ap_uint<16>"* noalias "unpacked"="32", i16* noalias nocapture readonly align 512 "unpacked"="33.0") unnamed_addr #2 {
entry:
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<32>"(%"struct.ap_uint<32>"* %0, i32* align 512 %1)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<32>"(%"struct.ap_uint<32>"* %2, i32* align 512 %3)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<32>"(%"struct.ap_uint<32>"* %4, i32* align 512 %5)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<32>"(%"struct.ap_uint<32>"* %6, i32* align 512 %7)
  call fastcc void @"onebyonecpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>.194"(%"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %8, i32* align 512 %_V_data_V, i4* align 512 %_V_keep_V, i4* align 512 %_V_strb_V, i1* align 512 %_V_user_V, i1* align 512 %_V_last_V, i1* align 512 %_V_id_V, i1* align 512 %_V_dest_V)
  call fastcc void @"onebyonecpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>.194"(%"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %9, i32* align 512 %_V_data_V1, i4* align 512 %_V_keep_V2, i4* align 512 %_V_strb_V3, i1* align 512 %_V_user_V4, i1* align 512 %_V_last_V5, i1* align 512 %_V_id_V6, i1* align 512 %_V_dest_V7)
  call fastcc void @"onebyonecpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>.194"(%"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %10, i32* align 512 %_V_data_V18, i4* align 512 %_V_keep_V29, i4* align 512 %_V_strb_V310, i1* align 512 %_V_user_V411, i1* align 512 %_V_last_V512, i1* align 512 %_V_id_V613, i1* align 512 %_V_dest_V714)
  call fastcc void @"onebyonecpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>.194"(%"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %11, i32* align 512 %_V_data_V1815, i4* align 512 %_V_keep_V2916, i4* align 512 %_V_strb_V31017, i1* align 512 %_V_user_V41118, i1* align 512 %_V_last_V51219, i1* align 512 %_V_id_V61320, i1* align 512 %_V_dest_V71421)
  call fastcc void @"onebyonecpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>.194"(%"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %12, i32* align 512 %_V_data_V181522, i4* align 512 %_V_keep_V291623, i4* align 512 %_V_strb_V3101724, i1* align 512 %_V_user_V4111825, i1* align 512 %_V_last_V5121926, i1* align 512 %_V_id_V6132027, i1* align 512 %_V_dest_V7142128)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<1>"(%"struct.ap_uint<1>"* %13, i1* align 512 %14)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<8>.162"(%"struct.ap_uint<8>"* %15, i8* align 512 %16)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<8>.162"(%"struct.ap_uint<8>"* %17, i8* align 512 %18)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<1>"(%"struct.ap_uint<1>"* %19, i1* align 512 %20)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<1>"(%"struct.ap_uint<1>"* %21, i1* align 512 %22)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<1>"(%"struct.ap_uint<1>"* %23, i1* align 512 %24)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<16>"(%"struct.ap_uint<16>"* %25, i16* align 512 %26)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<16>"(%"struct.ap_uint<16>"* %27, i16* align 512 %28)
  ret void
}

; Function Attrs: argmemonly noinline norecurse willreturn
define internal fastcc void @"onebyonecpy_hls.p0struct.ap_uint<16>"(%"struct.ap_uint<16>"* noalias "unpacked"="0" %dst, i16* noalias nocapture readonly align 512 "unpacked"="1.0" %src) unnamed_addr #3 {
entry:
  %0 = icmp eq %"struct.ap_uint<16>"* %dst, null
  br i1 %0, label %ret, label %copy

copy:                                             ; preds = %entry
  %dst.0.0.04 = getelementptr %"struct.ap_uint<16>", %"struct.ap_uint<16>"* %dst, i64 0, i32 0, i32 0, i32 0
  %1 = load i16, i16* %src, align 512
  store i16 %1, i16* %dst.0.0.04, align 2
  br label %ret

ret:                                              ; preds = %copy, %entry
  ret void
}

; Function Attrs: argmemonly noinline norecurse willreturn
define internal fastcc void @"onebyonecpy_hls.p0struct.ap_uint<16>.134"(i16* noalias nocapture align 512 "unpacked"="0.0" %dst, %"struct.ap_uint<16>"* noalias readonly "unpacked"="1" %src) unnamed_addr #3 {
entry:
  %0 = icmp eq %"struct.ap_uint<16>"* %src, null
  br i1 %0, label %ret, label %copy

copy:                                             ; preds = %entry
  %src.0.0.03 = getelementptr %"struct.ap_uint<16>", %"struct.ap_uint<16>"* %src, i64 0, i32 0, i32 0, i32 0
  %1 = load i16, i16* %src.0.0.03, align 2
  store i16 %1, i16* %dst, align 512
  br label %ret

ret:                                              ; preds = %copy, %entry
  ret void
}

; Function Attrs: argmemonly noinline norecurse willreturn
define internal fastcc void @"onebyonecpy_hls.p0struct.ap_uint<1>"(%"struct.ap_uint<1>"* noalias "unpacked"="0" %dst, i1* noalias nocapture readonly align 512 "unpacked"="1.0" %src) unnamed_addr #3 {
entry:
  %0 = icmp eq %"struct.ap_uint<1>"* %dst, null
  br i1 %0, label %ret, label %copy

copy:                                             ; preds = %entry
  %dst.0.0.04 = getelementptr %"struct.ap_uint<1>", %"struct.ap_uint<1>"* %dst, i64 0, i32 0, i32 0, i32 0
  %1 = bitcast i1* %src to i8*
  %2 = load i8, i8* %1
  %3 = trunc i8 %2 to i1
  store i1 %3, i1* %dst.0.0.04, align 1
  br label %ret

ret:                                              ; preds = %copy, %entry
  ret void
}

; Function Attrs: argmemonly noinline norecurse willreturn
define internal fastcc void @"onebyonecpy_hls.p0struct.ap_uint<1>.147"(i1* noalias nocapture align 512 "unpacked"="0.0" %dst, %"struct.ap_uint<1>"* noalias readonly "unpacked"="1" %src) unnamed_addr #3 {
entry:
  %0 = icmp eq %"struct.ap_uint<1>"* %src, null
  br i1 %0, label %ret, label %copy

copy:                                             ; preds = %entry
  %src.0.0.03 = getelementptr %"struct.ap_uint<1>", %"struct.ap_uint<1>"* %src, i64 0, i32 0, i32 0, i32 0
  %1 = bitcast i1* %src.0.0.03 to i8*
  %2 = load i8, i8* %1
  %3 = trunc i8 %2 to i1
  store i1 %3, i1* %dst, align 512
  br label %ret

ret:                                              ; preds = %copy, %entry
  ret void
}

; Function Attrs: argmemonly noinline norecurse willreturn
define internal fastcc void @"onebyonecpy_hls.p0struct.ap_uint<8>"(i8* noalias nocapture align 512 "unpacked"="0.0" %dst, %"struct.ap_uint<8>"* noalias readonly "unpacked"="1" %src) unnamed_addr #3 {
entry:
  %0 = icmp eq %"struct.ap_uint<8>"* %src, null
  br i1 %0, label %ret, label %copy

copy:                                             ; preds = %entry
  %src.0.0.03 = getelementptr %"struct.ap_uint<8>", %"struct.ap_uint<8>"* %src, i64 0, i32 0, i32 0, i32 0
  %1 = load i8, i8* %src.0.0.03, align 1
  store i8 %1, i8* %dst, align 512
  br label %ret

ret:                                              ; preds = %copy, %entry
  ret void
}

; Function Attrs: argmemonly noinline norecurse willreturn
define internal fastcc void @"onebyonecpy_hls.p0struct.ap_uint<8>.162"(%"struct.ap_uint<8>"* noalias "unpacked"="0" %dst, i8* noalias nocapture readonly align 512 "unpacked"="1.0" %src) unnamed_addr #3 {
entry:
  %0 = icmp eq %"struct.ap_uint<8>"* %dst, null
  br i1 %0, label %ret, label %copy

copy:                                             ; preds = %entry
  %dst.0.0.04 = getelementptr %"struct.ap_uint<8>", %"struct.ap_uint<8>"* %dst, i64 0, i32 0, i32 0, i32 0
  %1 = load i8, i8* %src, align 512
  store i8 %1, i8* %dst.0.0.04, align 1
  br label %ret

ret:                                              ; preds = %copy, %entry
  ret void
}

; Function Attrs: argmemonly noinline norecurse willreturn
define internal fastcc void @"onebyonecpy_hls.p0struct.ap_uint<32>"(%"struct.ap_uint<32>"* noalias "unpacked"="0" %dst, i32* noalias nocapture readonly align 512 "unpacked"="1.0" %src) unnamed_addr #3 {
entry:
  %0 = icmp eq %"struct.ap_uint<32>"* %dst, null
  br i1 %0, label %ret, label %copy

copy:                                             ; preds = %entry
  %dst.0.0.04 = getelementptr %"struct.ap_uint<32>", %"struct.ap_uint<32>"* %dst, i64 0, i32 0, i32 0, i32 0
  %1 = load i32, i32* %src, align 512
  store i32 %1, i32* %dst.0.0.04, align 4
  br label %ret

ret:                                              ; preds = %copy, %entry
  ret void
}

; Function Attrs: argmemonly noinline norecurse willreturn
define internal fastcc void @"onebyonecpy_hls.p0struct.ap_uint<32>.179"(i32* noalias nocapture align 512 "unpacked"="0.0" %dst, %"struct.ap_uint<32>"* noalias readonly "unpacked"="1" %src) unnamed_addr #3 {
entry:
  %0 = icmp eq %"struct.ap_uint<32>"* %src, null
  br i1 %0, label %ret, label %copy

copy:                                             ; preds = %entry
  %src.0.0.03 = getelementptr %"struct.ap_uint<32>", %"struct.ap_uint<32>"* %src, i64 0, i32 0, i32 0, i32 0
  %1 = load i32, i32* %src.0.0.03, align 4
  store i32 %1, i32* %dst, align 512
  br label %ret

ret:                                              ; preds = %copy, %entry
  ret void
}

; Function Attrs: argmemonly noinline willreturn
define internal fastcc void @"onebyonecpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>.194"(%"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias %dst, i32* noalias align 512 "unpacked"="1.0" %src_V_data_V, i4* noalias align 512 "unpacked"="1.1" %src_V_keep_V, i4* noalias align 512 "unpacked"="1.2" %src_V_strb_V, i1* noalias align 512 "unpacked"="1.3" %src_V_user_V, i1* noalias align 512 "unpacked"="1.4" %src_V_last_V, i1* noalias align 512 "unpacked"="1.5" %src_V_id_V, i1* noalias align 512 "unpacked"="1.6" %src_V_dest_V) unnamed_addr #4 {
entry:
  %0 = icmp eq %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %dst, null
  br i1 %0, label %ret, label %copy

copy:                                             ; preds = %entry
  call fastcc void @"streamcpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>.197"(%"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* nonnull %dst, i32* align 512 %src_V_data_V, i4* align 512 %src_V_keep_V, i4* align 512 %src_V_strb_V, i1* align 512 %src_V_user_V, i1* align 512 %src_V_last_V, i1* align 512 %src_V_id_V, i1* align 512 %src_V_dest_V)
  br label %ret

ret:                                              ; preds = %copy, %entry
  ret void
}

; Function Attrs: argmemonly noinline willreturn
define internal fastcc void @"streamcpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>.197"(%"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias nocapture, i32* noalias nocapture align 512 "unpacked"="1.0" %_V_data_V, i4* noalias nocapture align 512 "unpacked"="1.1" %_V_keep_V, i4* noalias nocapture align 512 "unpacked"="1.2" %_V_strb_V, i1* noalias nocapture align 512 "unpacked"="1.3" %_V_user_V, i1* noalias nocapture align 512 "unpacked"="1.4" %_V_last_V, i1* noalias nocapture align 512 "unpacked"="1.5" %_V_id_V, i1* noalias nocapture align 512 "unpacked"="1.6" %_V_dest_V) unnamed_addr #5 {
entry:
  %1 = alloca i32
  %2 = alloca i4
  %3 = alloca i4
  %4 = alloca i1
  %5 = alloca i1
  %6 = alloca i1
  %7 = alloca i1
  %8 = alloca %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"
  br label %empty

empty:                                            ; preds = %push, %entry
  %9 = bitcast i32* %_V_data_V to i8*
  %10 = call i1 @fpga_fifo_not_empty_4(i8* %9)
  br i1 %10, label %push, label %ret

push:                                             ; preds = %empty
  %11 = bitcast i32* %1 to i8*
  %12 = bitcast i32* %_V_data_V to i8*
  call void @fpga_fifo_pop_4(i8* %11, i8* %12)
  %13 = load volatile i32, i32* %1
  %14 = bitcast i4* %3 to i8*
  %15 = bitcast i4* %_V_keep_V to i8*
  call void @fpga_fifo_pop_1(i8* %14, i8* %15)
  %16 = bitcast i4* %3 to i8*
  %17 = load i8, i8* %16
  %18 = trunc i8 %17 to i4
  %19 = bitcast i4* %2 to i8*
  %20 = bitcast i4* %_V_strb_V to i8*
  call void @fpga_fifo_pop_1(i8* %19, i8* %20)
  %21 = bitcast i4* %2 to i8*
  %22 = load i8, i8* %21
  %23 = trunc i8 %22 to i4
  %24 = bitcast i1* %7 to i8*
  %25 = bitcast i1* %_V_user_V to i8*
  call void @fpga_fifo_pop_1(i8* %24, i8* %25)
  %26 = bitcast i1* %7 to i8*
  %27 = load i8, i8* %26
  %28 = trunc i8 %27 to i1
  %29 = bitcast i1* %6 to i8*
  %30 = bitcast i1* %_V_last_V to i8*
  call void @fpga_fifo_pop_1(i8* %29, i8* %30)
  %31 = bitcast i1* %6 to i8*
  %32 = load i8, i8* %31
  %33 = trunc i8 %32 to i1
  %34 = bitcast i1* %5 to i8*
  %35 = bitcast i1* %_V_id_V to i8*
  call void @fpga_fifo_pop_1(i8* %34, i8* %35)
  %36 = bitcast i1* %5 to i8*
  %37 = load i8, i8* %36
  %38 = trunc i8 %37 to i1
  %39 = bitcast i1* %4 to i8*
  %40 = bitcast i1* %_V_dest_V to i8*
  call void @fpga_fifo_pop_1(i8* %39, i8* %40)
  %41 = bitcast i1* %4 to i8*
  %42 = load i8, i8* %41
  %43 = trunc i8 %42 to i1
  %.fca.0.0.0.0.0.insert = insertvalue %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>" undef, i32 %13, 0, 0, 0, 0, 0
  %.fca.0.1.0.0.0.insert = insertvalue %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>" %.fca.0.0.0.0.0.insert, i4 %18, 0, 1, 0, 0, 0
  %.fca.0.2.0.0.0.insert = insertvalue %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>" %.fca.0.1.0.0.0.insert, i4 %23, 0, 2, 0, 0, 0
  %.fca.0.3.0.0.0.insert = insertvalue %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>" %.fca.0.2.0.0.0.insert, i1 %28, 0, 3, 0, 0, 0
  %.fca.0.4.0.0.0.insert = insertvalue %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>" %.fca.0.3.0.0.0.insert, i1 %33, 0, 4, 0, 0, 0
  %.fca.0.5.0.0.0.insert = insertvalue %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>" %.fca.0.4.0.0.0.insert, i1 %38, 0, 5, 0, 0, 0
  %.fca.0.6.0.0.0.insert = insertvalue %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>" %.fca.0.5.0.0.0.insert, i1 %43, 0, 6, 0, 0, 0
  store %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>" %.fca.0.6.0.0.0.insert, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %8
  %44 = bitcast %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %8 to i8*
  %45 = bitcast %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %0 to i8*
  call void @fpga_fifo_push_12(i8* %44, i8* %45)
  br label %empty, !llvm.loop !6

ret:                                              ; preds = %empty
  ret void
}

; Function Attrs: argmemonly noinline willreturn
define internal fastcc void @"onebyonecpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"(i32* noalias align 512 "unpacked"="0.0" %dst_V_data_V, i4* noalias align 512 "unpacked"="0.1" %dst_V_keep_V, i4* noalias align 512 "unpacked"="0.2" %dst_V_strb_V, i1* noalias align 512 "unpacked"="0.3" %dst_V_user_V, i1* noalias align 512 "unpacked"="0.4" %dst_V_last_V, i1* noalias align 512 "unpacked"="0.5" %dst_V_id_V, i1* noalias align 512 "unpacked"="0.6" %dst_V_dest_V, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias %src) unnamed_addr #4 {
entry:
  %0 = icmp eq %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %src, null
  br i1 %0, label %ret, label %copy

copy:                                             ; preds = %entry
  call fastcc void @"streamcpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>.205"(i32* align 512 %dst_V_data_V, i4* align 512 %dst_V_keep_V, i4* align 512 %dst_V_strb_V, i1* align 512 %dst_V_user_V, i1* align 512 %dst_V_last_V, i1* align 512 %dst_V_id_V, i1* align 512 %dst_V_dest_V, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* nonnull %src)
  br label %ret

ret:                                              ; preds = %copy, %entry
  ret void
}

; Function Attrs: argmemonly noinline willreturn
define internal fastcc void @"streamcpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>.205"(i32* noalias nocapture align 512 "unpacked"="0.0" %_V_data_V, i4* noalias nocapture align 512 "unpacked"="0.1" %_V_keep_V, i4* noalias nocapture align 512 "unpacked"="0.2" %_V_strb_V, i1* noalias nocapture align 512 "unpacked"="0.3" %_V_user_V, i1* noalias nocapture align 512 "unpacked"="0.4" %_V_last_V, i1* noalias nocapture align 512 "unpacked"="0.5" %_V_id_V, i1* noalias nocapture align 512 "unpacked"="0.6" %_V_dest_V, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias nocapture) unnamed_addr #5 {
entry:
  %1 = alloca %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"
  %2 = alloca i32
  %3 = alloca i4
  %4 = alloca i4
  %5 = alloca i1
  %6 = alloca i1
  %7 = alloca i1
  %8 = alloca i1
  br label %empty

empty:                                            ; preds = %push, %entry
  %9 = bitcast %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %0 to i8*
  %10 = call i1 @fpga_fifo_not_empty_12(i8* %9)
  br i1 %10, label %push, label %ret

push:                                             ; preds = %empty
  %11 = bitcast %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %1 to i8*
  %12 = bitcast %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %0 to i8*
  call void @fpga_fifo_pop_12(i8* %11, i8* %12)
  %13 = load volatile %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>", %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %1
  %.fca.0.0.0.0.0.extract = extractvalue %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>" %13, 0, 0, 0, 0, 0
  %.fca.0.1.0.0.0.extract = extractvalue %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>" %13, 0, 1, 0, 0, 0
  %.fca.0.2.0.0.0.extract = extractvalue %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>" %13, 0, 2, 0, 0, 0
  %.fca.0.3.0.0.0.extract = extractvalue %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>" %13, 0, 3, 0, 0, 0
  %.fca.0.4.0.0.0.extract = extractvalue %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>" %13, 0, 4, 0, 0, 0
  %.fca.0.5.0.0.0.extract = extractvalue %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>" %13, 0, 5, 0, 0, 0
  %.fca.0.6.0.0.0.extract = extractvalue %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>" %13, 0, 6, 0, 0, 0
  store i32 %.fca.0.0.0.0.0.extract, i32* %2
  %14 = bitcast i32* %2 to i8*
  %15 = bitcast i32* %_V_data_V to i8*
  call void @fpga_fifo_push_4(i8* %14, i8* %15)
  store i4 %.fca.0.1.0.0.0.extract, i4* %4
  %16 = bitcast i4* %4 to i8*
  %17 = bitcast i4* %_V_keep_V to i8*
  call void @fpga_fifo_push_1(i8* %16, i8* %17)
  store i4 %.fca.0.2.0.0.0.extract, i4* %3
  %18 = bitcast i4* %3 to i8*
  %19 = bitcast i4* %_V_strb_V to i8*
  call void @fpga_fifo_push_1(i8* %18, i8* %19)
  store i1 %.fca.0.3.0.0.0.extract, i1* %8
  %20 = bitcast i1* %8 to i8*
  %21 = bitcast i1* %_V_user_V to i8*
  call void @fpga_fifo_push_1(i8* %20, i8* %21)
  store i1 %.fca.0.4.0.0.0.extract, i1* %7
  %22 = bitcast i1* %7 to i8*
  %23 = bitcast i1* %_V_last_V to i8*
  call void @fpga_fifo_push_1(i8* %22, i8* %23)
  store i1 %.fca.0.5.0.0.0.extract, i1* %6
  %24 = bitcast i1* %6 to i8*
  %25 = bitcast i1* %_V_id_V to i8*
  call void @fpga_fifo_push_1(i8* %24, i8* %25)
  store i1 %.fca.0.6.0.0.0.extract, i1* %5
  %26 = bitcast i1* %5 to i8*
  %27 = bitcast i1* %_V_dest_V to i8*
  call void @fpga_fifo_push_1(i8* %26, i8* %27)
  br label %empty, !llvm.loop !6

ret:                                              ; preds = %empty
  ret void
}

declare i8* @malloc(i64)

declare void @free(i8*)

declare void @apatb_snn_top_hls_hw(%"struct.ap_uint<32>"*, %"struct.ap_uint<32>"*, %"struct.ap_uint<32>"*, %"struct.ap_uint<32>"*, %struct.learning_params_t*, %struct.encoder_config_t*, i32*, i32*, i32*, i32*, i32*, i4*, i4*, i1*, i1*, i1*, i1*, i32*, i4*, i4*, i1*, i1*, i1*, i1*, i32*, i4*, i4*, i1*, i1*, i1*, i1*, i32*, i4*, i4*, i1*, i1*, i1*, i1*, i32*, i4*, i4*, i1*, i1*, i1*, i1*, %"struct.ap_uint<8>"*, i1*, i8*, i8*, %"struct.ap_uint<1>"*, %"struct.ap_uint<1>"*, %"struct.ap_uint<8>"*, %"struct.ap_uint<8>"*, i1*, i1*, i1*, i16*, i16*, %"struct.ap_uint<1>"*, %"struct.ap_uint<1>"*)

; Function Attrs: argmemonly noinline willreturn
define internal fastcc void @copy_back(%"struct.ap_uint<32>"* noalias "unpacked"="0", i32* noalias nocapture readonly align 512 "unpacked"="1.0", %"struct.ap_uint<32>"* noalias "unpacked"="2", i32* noalias nocapture readonly align 512 "unpacked"="3.0", %"struct.ap_uint<32>"* noalias "unpacked"="4", i32* noalias nocapture readonly align 512 "unpacked"="5.0", %"struct.ap_uint<32>"* noalias "unpacked"="6", i32* noalias nocapture readonly align 512 "unpacked"="7.0", %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias "unpacked"="8", i32* noalias align 512 "unpacked"="9.0" %_V_data_V, i4* noalias align 512 "unpacked"="9.1" %_V_keep_V, i4* noalias align 512 "unpacked"="9.2" %_V_strb_V, i1* noalias align 512 "unpacked"="9.3" %_V_user_V, i1* noalias align 512 "unpacked"="9.4" %_V_last_V, i1* noalias align 512 "unpacked"="9.5" %_V_id_V, i1* noalias align 512 "unpacked"="9.6" %_V_dest_V, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias "unpacked"="10", i32* noalias align 512 "unpacked"="11.0" %_V_data_V1, i4* noalias align 512 "unpacked"="11.1" %_V_keep_V2, i4* noalias align 512 "unpacked"="11.2" %_V_strb_V3, i1* noalias align 512 "unpacked"="11.3" %_V_user_V4, i1* noalias align 512 "unpacked"="11.4" %_V_last_V5, i1* noalias align 512 "unpacked"="11.5" %_V_id_V6, i1* noalias align 512 "unpacked"="11.6" %_V_dest_V7, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias "unpacked"="12", i32* noalias align 512 "unpacked"="13.0" %_V_data_V18, i4* noalias align 512 "unpacked"="13.1" %_V_keep_V29, i4* noalias align 512 "unpacked"="13.2" %_V_strb_V310, i1* noalias align 512 "unpacked"="13.3" %_V_user_V411, i1* noalias align 512 "unpacked"="13.4" %_V_last_V512, i1* noalias align 512 "unpacked"="13.5" %_V_id_V613, i1* noalias align 512 "unpacked"="13.6" %_V_dest_V714, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias "unpacked"="14", i32* noalias align 512 "unpacked"="15.0" %_V_data_V1815, i4* noalias align 512 "unpacked"="15.1" %_V_keep_V2916, i4* noalias align 512 "unpacked"="15.2" %_V_strb_V31017, i1* noalias align 512 "unpacked"="15.3" %_V_user_V41118, i1* noalias align 512 "unpacked"="15.4" %_V_last_V51219, i1* noalias align 512 "unpacked"="15.5" %_V_id_V61320, i1* noalias align 512 "unpacked"="15.6" %_V_dest_V71421, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias "unpacked"="16", i32* noalias align 512 "unpacked"="17.0" %_V_data_V181522, i4* noalias align 512 "unpacked"="17.1" %_V_keep_V291623, i4* noalias align 512 "unpacked"="17.2" %_V_strb_V3101724, i1* noalias align 512 "unpacked"="17.3" %_V_user_V4111825, i1* noalias align 512 "unpacked"="17.4" %_V_last_V5121926, i1* noalias align 512 "unpacked"="17.5" %_V_id_V6132027, i1* noalias align 512 "unpacked"="17.6" %_V_dest_V7142128, %"struct.ap_uint<1>"* noalias "unpacked"="18", i1* noalias nocapture readonly align 512 "unpacked"="19.0", %"struct.ap_uint<8>"* noalias "unpacked"="20", i8* noalias nocapture readonly align 512 "unpacked"="21.0", %"struct.ap_uint<8>"* noalias "unpacked"="22", i8* noalias nocapture readonly align 512 "unpacked"="23.0", %"struct.ap_uint<1>"* noalias "unpacked"="24", i1* noalias nocapture readonly align 512 "unpacked"="25.0", %"struct.ap_uint<1>"* noalias "unpacked"="26", i1* noalias nocapture readonly align 512 "unpacked"="27.0", %"struct.ap_uint<1>"* noalias "unpacked"="28", i1* noalias nocapture readonly align 512 "unpacked"="29.0", %"struct.ap_uint<16>"* noalias "unpacked"="30", i16* noalias nocapture readonly align 512 "unpacked"="31.0", %"struct.ap_uint<16>"* noalias "unpacked"="32", i16* noalias nocapture readonly align 512 "unpacked"="33.0") unnamed_addr #2 {
entry:
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<32>"(%"struct.ap_uint<32>"* %0, i32* align 512 %1)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<32>"(%"struct.ap_uint<32>"* %2, i32* align 512 %3)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<32>"(%"struct.ap_uint<32>"* %4, i32* align 512 %5)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<32>"(%"struct.ap_uint<32>"* %6, i32* align 512 %7)
  call fastcc void @"onebyonecpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>.194"(%"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %8, i32* align 512 %_V_data_V, i4* align 512 %_V_keep_V, i4* align 512 %_V_strb_V, i1* align 512 %_V_user_V, i1* align 512 %_V_last_V, i1* align 512 %_V_id_V, i1* align 512 %_V_dest_V)
  call fastcc void @"onebyonecpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>.194"(%"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %9, i32* align 512 %_V_data_V1, i4* align 512 %_V_keep_V2, i4* align 512 %_V_strb_V3, i1* align 512 %_V_user_V4, i1* align 512 %_V_last_V5, i1* align 512 %_V_id_V6, i1* align 512 %_V_dest_V7)
  call fastcc void @"onebyonecpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>.194"(%"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %10, i32* align 512 %_V_data_V18, i4* align 512 %_V_keep_V29, i4* align 512 %_V_strb_V310, i1* align 512 %_V_user_V411, i1* align 512 %_V_last_V512, i1* align 512 %_V_id_V613, i1* align 512 %_V_dest_V714)
  call fastcc void @"onebyonecpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>.194"(%"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %11, i32* align 512 %_V_data_V1815, i4* align 512 %_V_keep_V2916, i4* align 512 %_V_strb_V31017, i1* align 512 %_V_user_V41118, i1* align 512 %_V_last_V51219, i1* align 512 %_V_id_V61320, i1* align 512 %_V_dest_V71421)
  call fastcc void @"onebyonecpy_hls.p0class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>.194"(%"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %12, i32* align 512 %_V_data_V181522, i4* align 512 %_V_keep_V291623, i4* align 512 %_V_strb_V3101724, i1* align 512 %_V_user_V4111825, i1* align 512 %_V_last_V5121926, i1* align 512 %_V_id_V6132027, i1* align 512 %_V_dest_V7142128)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<1>"(%"struct.ap_uint<1>"* %13, i1* align 512 %14)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<8>.162"(%"struct.ap_uint<8>"* %15, i8* align 512 %16)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<8>.162"(%"struct.ap_uint<8>"* %17, i8* align 512 %18)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<1>"(%"struct.ap_uint<1>"* %19, i1* align 512 %20)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<1>"(%"struct.ap_uint<1>"* %21, i1* align 512 %22)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<1>"(%"struct.ap_uint<1>"* %23, i1* align 512 %24)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<16>"(%"struct.ap_uint<16>"* %25, i16* align 512 %26)
  call fastcc void @"onebyonecpy_hls.p0struct.ap_uint<16>"(%"struct.ap_uint<16>"* %27, i16* align 512 %28)
  ret void
}

declare void @snn_top_hls_hw_stub(%"struct.ap_uint<32>"* nocapture readonly, %"struct.ap_uint<32>"* nocapture readonly, %"struct.ap_uint<32>"* nocapture readonly, %"struct.ap_uint<32>"* nocapture readonly, %struct.learning_params_t* nocapture readonly, %struct.encoder_config_t* nocapture readonly, %"struct.ap_uint<32>"* noalias nocapture nonnull, %"struct.ap_uint<32>"* noalias nocapture nonnull, %"struct.ap_uint<32>"* noalias nocapture nonnull, %"struct.ap_uint<32>"* noalias nocapture nonnull, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias nonnull, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias nonnull, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias nonnull, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias nonnull, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* noalias nonnull, %"struct.ap_uint<8>"* nocapture readonly, %"struct.ap_uint<1>"* noalias nocapture nonnull, %"struct.ap_uint<8>"* noalias nocapture nonnull, %"struct.ap_uint<8>"* noalias nocapture nonnull, %"struct.ap_uint<1>"* nocapture readonly, %"struct.ap_uint<1>"* nocapture readonly, %"struct.ap_uint<8>"* nocapture readonly, %"struct.ap_uint<8>"* nocapture readonly, %"struct.ap_uint<1>"* noalias nocapture nonnull, %"struct.ap_uint<1>"* noalias nocapture nonnull, %"struct.ap_uint<1>"* noalias nocapture nonnull, %"struct.ap_uint<16>"* noalias nocapture nonnull, %"struct.ap_uint<16>"* noalias nocapture nonnull, %"struct.ap_uint<1>"* nocapture readonly, %"struct.ap_uint<1>"* nocapture readonly)

define void @snn_top_hls_hw_stub_wrapper(%"struct.ap_uint<32>"*, %"struct.ap_uint<32>"*, %"struct.ap_uint<32>"*, %"struct.ap_uint<32>"*, %struct.learning_params_t*, %struct.encoder_config_t*, i32*, i32*, i32*, i32*, i32*, i4*, i4*, i1*, i1*, i1*, i1*, i32*, i4*, i4*, i1*, i1*, i1*, i1*, i32*, i4*, i4*, i1*, i1*, i1*, i1*, i32*, i4*, i4*, i1*, i1*, i1*, i1*, i32*, i4*, i4*, i1*, i1*, i1*, i1*, %"struct.ap_uint<8>"*, i1*, i8*, i8*, %"struct.ap_uint<1>"*, %"struct.ap_uint<1>"*, %"struct.ap_uint<8>"*, %"struct.ap_uint<8>"*, i1*, i1*, i1*, i16*, i16*, %"struct.ap_uint<1>"*, %"struct.ap_uint<1>"*) #6 {
entry:
  %60 = call i8* @malloc(i64 4)
  %61 = bitcast i8* %60 to %"struct.ap_uint<32>"*
  %62 = call i8* @malloc(i64 4)
  %63 = bitcast i8* %62 to %"struct.ap_uint<32>"*
  %64 = call i8* @malloc(i64 4)
  %65 = bitcast i8* %64 to %"struct.ap_uint<32>"*
  %66 = call i8* @malloc(i64 4)
  %67 = bitcast i8* %66 to %"struct.ap_uint<32>"*
  %68 = call i8* @malloc(i64 12)
  %69 = bitcast i8* %68 to %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"*
  %70 = call i8* @malloc(i64 12)
  %71 = bitcast i8* %70 to %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"*
  %72 = call i8* @malloc(i64 12)
  %73 = bitcast i8* %72 to %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"*
  %74 = call i8* @malloc(i64 12)
  %75 = bitcast i8* %74 to %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"*
  %76 = call i8* @malloc(i64 12)
  %77 = bitcast i8* %76 to %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"*
  %78 = call i8* @malloc(i64 1)
  %79 = bitcast i8* %78 to %"struct.ap_uint<1>"*
  %80 = call i8* @malloc(i64 1)
  %81 = bitcast i8* %80 to %"struct.ap_uint<8>"*
  %82 = call i8* @malloc(i64 1)
  %83 = bitcast i8* %82 to %"struct.ap_uint<8>"*
  %84 = call i8* @malloc(i64 1)
  %85 = bitcast i8* %84 to %"struct.ap_uint<1>"*
  %86 = call i8* @malloc(i64 1)
  %87 = bitcast i8* %86 to %"struct.ap_uint<1>"*
  %88 = call i8* @malloc(i64 1)
  %89 = bitcast i8* %88 to %"struct.ap_uint<1>"*
  %90 = call i8* @malloc(i64 2)
  %91 = bitcast i8* %90 to %"struct.ap_uint<16>"*
  %92 = call i8* @malloc(i64 2)
  %93 = bitcast i8* %92 to %"struct.ap_uint<16>"*
  call void @copy_out(%"struct.ap_uint<32>"* %61, i32* %6, %"struct.ap_uint<32>"* %63, i32* %7, %"struct.ap_uint<32>"* %65, i32* %8, %"struct.ap_uint<32>"* %67, i32* %9, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %69, i32* %10, i4* %11, i4* %12, i1* %13, i1* %14, i1* %15, i1* %16, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %71, i32* %17, i4* %18, i4* %19, i1* %20, i1* %21, i1* %22, i1* %23, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %73, i32* %24, i4* %25, i4* %26, i1* %27, i1* %28, i1* %29, i1* %30, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %75, i32* %31, i4* %32, i4* %33, i1* %34, i1* %35, i1* %36, i1* %37, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %77, i32* %38, i4* %39, i4* %40, i1* %41, i1* %42, i1* %43, i1* %44, %"struct.ap_uint<1>"* %79, i1* %46, %"struct.ap_uint<8>"* %81, i8* %47, %"struct.ap_uint<8>"* %83, i8* %48, %"struct.ap_uint<1>"* %85, i1* %53, %"struct.ap_uint<1>"* %87, i1* %54, %"struct.ap_uint<1>"* %89, i1* %55, %"struct.ap_uint<16>"* %91, i16* %56, %"struct.ap_uint<16>"* %93, i16* %57)
  call void @snn_top_hls_hw_stub(%"struct.ap_uint<32>"* %0, %"struct.ap_uint<32>"* %1, %"struct.ap_uint<32>"* %2, %"struct.ap_uint<32>"* %3, %struct.learning_params_t* %4, %struct.encoder_config_t* %5, %"struct.ap_uint<32>"* %61, %"struct.ap_uint<32>"* %63, %"struct.ap_uint<32>"* %65, %"struct.ap_uint<32>"* %67, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %69, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %71, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %73, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %75, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %77, %"struct.ap_uint<8>"* %45, %"struct.ap_uint<1>"* %79, %"struct.ap_uint<8>"* %81, %"struct.ap_uint<8>"* %83, %"struct.ap_uint<1>"* %49, %"struct.ap_uint<1>"* %50, %"struct.ap_uint<8>"* %51, %"struct.ap_uint<8>"* %52, %"struct.ap_uint<1>"* %85, %"struct.ap_uint<1>"* %87, %"struct.ap_uint<1>"* %89, %"struct.ap_uint<16>"* %91, %"struct.ap_uint<16>"* %93, %"struct.ap_uint<1>"* %58, %"struct.ap_uint<1>"* %59)
  call void @copy_in(%"struct.ap_uint<32>"* %61, i32* %6, %"struct.ap_uint<32>"* %63, i32* %7, %"struct.ap_uint<32>"* %65, i32* %8, %"struct.ap_uint<32>"* %67, i32* %9, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %69, i32* %10, i4* %11, i4* %12, i1* %13, i1* %14, i1* %15, i1* %16, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %71, i32* %17, i4* %18, i4* %19, i1* %20, i1* %21, i1* %22, i1* %23, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %73, i32* %24, i4* %25, i4* %26, i1* %27, i1* %28, i1* %29, i1* %30, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %75, i32* %31, i4* %32, i4* %33, i1* %34, i1* %35, i1* %36, i1* %37, %"class.hls::stream<hls::axis<ap_uint<32>, 1, 1, 1, '8', false>, 0>"* %77, i32* %38, i4* %39, i4* %40, i1* %41, i1* %42, i1* %43, i1* %44, %"struct.ap_uint<1>"* %79, i1* %46, %"struct.ap_uint<8>"* %81, i8* %47, %"struct.ap_uint<8>"* %83, i8* %48, %"struct.ap_uint<1>"* %85, i1* %53, %"struct.ap_uint<1>"* %87, i1* %54, %"struct.ap_uint<1>"* %89, i1* %55, %"struct.ap_uint<16>"* %91, i16* %56, %"struct.ap_uint<16>"* %93, i16* %57)
  call void @free(i8* %60)
  call void @free(i8* %62)
  call void @free(i8* %64)
  call void @free(i8* %66)
  call void @free(i8* %68)
  call void @free(i8* %70)
  call void @free(i8* %72)
  call void @free(i8* %74)
  call void @free(i8* %76)
  call void @free(i8* %78)
  call void @free(i8* %80)
  call void @free(i8* %82)
  call void @free(i8* %84)
  call void @free(i8* %86)
  call void @free(i8* %88)
  call void @free(i8* %90)
  call void @free(i8* %92)
  ret void
}

declare i1 @fpga_fifo_not_empty_12(i8*)

declare i1 @fpga_fifo_not_empty_4(i8*)

declare void @fpga_fifo_pop_12(i8*, i8*)

declare void @fpga_fifo_pop_4(i8*, i8*)

declare void @fpga_fifo_pop_1(i8*, i8*)

declare void @fpga_fifo_push_12(i8*, i8*)

declare void @fpga_fifo_push_4(i8*, i8*)

declare void @fpga_fifo_push_1(i8*, i8*)

attributes #0 = { noinline willreturn "fpga.wrapper.func"="wrapper" }
attributes #1 = { argmemonly noinline willreturn "fpga.wrapper.func"="copyin" }
attributes #2 = { argmemonly noinline willreturn "fpga.wrapper.func"="copyout" }
attributes #3 = { argmemonly noinline norecurse willreturn "fpga.wrapper.func"="onebyonecpy_hls" }
attributes #4 = { argmemonly noinline willreturn "fpga.wrapper.func"="onebyonecpy_hls" }
attributes #5 = { argmemonly noinline willreturn "fpga.wrapper.func"="streamcpy_hls" }
attributes #6 = { "fpga.wrapper.func"="stub" }

!llvm.dbg.cu = !{}
!llvm.ident = !{!0, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1, !1}
!llvm.module.flags = !{!2, !3, !4}
!blackbox_cfg = !{!5}

!0 = !{!"AMD/Xilinx clang version 16.0.6"}
!1 = !{!"clang version 7.0.0 "}
!2 = !{i32 2, !"Dwarf Version", i32 4}
!3 = !{i32 2, !"Debug Info Version", i32 3}
!4 = !{i32 1, !"wchar_size", i32 4}
!5 = !{}
!6 = distinct !{!6, !7}
!7 = !{!"llvm.loop.rotate.disable"}
