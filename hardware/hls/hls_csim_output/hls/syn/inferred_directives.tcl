# Inferred from syn.compile.pipeline_loops=64
set_directive_pipeline run_encoder_once/ENCODER_LOOP
# Inferred from performance & pipeline pragmas/directives
set_directive_loop_flatten snn_top_hls/INIT_WEIGHT_OUTER
set_directive_array_partition snn_top_hls/encoder_frame -dim=1 -type=cyclic -factor=2 encoder_frame
