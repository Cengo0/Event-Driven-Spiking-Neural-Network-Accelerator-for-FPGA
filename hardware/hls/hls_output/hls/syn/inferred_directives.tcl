# Inferred from syn.array_partition.complete_threshold=4
set_directive_array_partition snn_top_hls/CONNECTION_TABLE (.src_size) -dim=1 -type=complete CONNECTION_TABLE (.src_size)
# Inferred from syn.compile.pipeline_loops=64
set_directive_pipeline snn_top_hls/VITIS_LOOP_70_1
set_directive_pipeline snn_top_hls/VITIS_LOOP_76_3
set_directive_pipeline snn_top_hls/VITIS_LOOP_89_9
set_directive_pipeline snn_top_hls/VITIS_LOOP_84_7
set_directive_pipeline snn_top_hls/VITIS_LOOP_148_5
# Inferred from Performance Budgeter performance directives
set_directive_loop_flatten snn_top_hls/VITIS_LOOP_83_6
set_directive_loop_flatten snn_top_hls/VITIS_LOOP_88_8
set_directive_loop_flatten snn_top_hls/VITIS_LOOP_147_4
# Inferred from performance & pipeline pragmas/directives
set_directive_array_partition snn_top_hls/encoder_frame -dim=1 -type=cyclic -factor=2 encoder_frame
