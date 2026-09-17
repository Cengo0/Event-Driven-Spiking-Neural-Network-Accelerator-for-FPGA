# Inferred from syn.array_partition.complete_threshold=4
set_directive_array_partition snn_top_hls/CONNECTION_TABLE (.src_size) -dim=1 -type=complete CONNECTION_TABLE (.src_size)
# Inferred from performance & pipeline pragmas/directives
set_directive_array_partition snn_top_hls/encoder_frame -dim=1 -type=cyclic -factor=2 encoder_frame
