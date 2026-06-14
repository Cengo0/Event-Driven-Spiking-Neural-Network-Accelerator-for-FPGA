# Active coregroup fabric sources.
# spikemold_coregroup_top.v implements the fabric and spikemold_integrated_top.v is the
# board-visible wrapper.

# Core modules
hardware/hdl/rtl/core/spikemold_coregroup.v
hardware/hdl/rtl/core/event_router_ng.v
hardware/hdl/rtl/core/synaptic_connectivity_table.v

# Optional: EventConv primitive sources for shared-kernel AGU experiments.
# Keep these board-free until the trace-locked C-gates promote them into fabric.
# hardware/hdl/rtl/core/spike_conv_agu.v
# hardware/hdl/rtl/core/spike_conv_state_update.v
# hardware/hdl/rtl/core/spike_conv_active_commit.v
# hardware/hdl/rtl/core/spike_conv_connectivity_table.v
# hardware/hdl/rtl/core/spike_conv_layer.v

# Common utilities
hardware/hdl/rtl/common/direct_axis_id_decoder.v
hardware/hdl/rtl/common/event_word64_decode.v
hardware/hdl/rtl/common/spike_out_bridge.v
hardware/hdl/rtl/common/spikemold_scalar_id_guard.v
hardware/hdl/rtl/common/wide_control_decode.v

# Event frontend (optional for board-free coverage)
# hardware/hdl/rtl/event_frontend/event_stream_filter.v
# hardware/hdl/rtl/event_frontend/event_to_tile_mapper.v

# Top-level modules
hardware/hdl/rtl/top/spikemold_coregroup_top.v
hardware/hdl/rtl/top/spikemold_integrated_top.v
