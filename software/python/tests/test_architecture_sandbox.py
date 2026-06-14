from spikepress.architecture_sandbox import (
    ARCHITECTURE_SANDBOX_SCHEMA,
    build_batch_1x_architecture_sandbox,
    replay_trace,
)
from spikepress.architecture_trace_generator import InputSpike, generate_eventconv_trace, generate_fc_lif_trace


def test_architecture_sandbox_replays_traces_without_semantic_change():
    fc_trace = generate_fc_lif_trace(
        input_spikes=[InputSpike(tick=0, src_id=0), InputSpike(tick=1, src_id=1)],
        weights={(0, 10): 3, (1, 10): 2},
        thresholds={10: 5},
        trace_id="fc_lif_unit",
    ).to_dict()
    conv_trace = generate_eventconv_trace(
        input_spikes=[InputSpike(tick=0, src_id=0, y=1, x=1, channel=0)],
        kernel=[[[[1, -1], [2, 0]]]],
        input_shape=(1, 3, 3),
        trace_id="eventconv_unit",
    ).to_dict()

    for trace in [fc_trace, conv_trace]:
        replay = replay_trace(trace)
        assert replay["trace_match_rate"] == 1.0
        assert replay["readout_match"] is True
        assert replay["state_checksum_match"] is True

    sandbox = build_batch_1x_architecture_sandbox([fc_trace, conv_trace])

    assert sandbox["schema"] == ARCHITECTURE_SANDBOX_SCHEMA
    assert sandbox["board_executed"] is False
    assert sandbox["all_ok"] is True
    assert sandbox["mainline_switch_recommended"] is False

    expected = {
        "coregroup_2x64": "coregroup_partition",
        "page_block_256_updates": "page_block_sparse_execution",
        "tile_microbatch_4x4": "tile_microbatch",
    }
    assert {key: value["pattern"] for key, value in sandbox["candidates"].items()} == expected

    for candidate in sandbox["candidates"].values():
        assert candidate["probation"]["event_triggered_semantics"] is True
        assert candidate["probation"]["python_inner_loop_required"] is False
        assert candidate["probation"]["random_ddr_inner_loop"] is False
        assert candidate["probation"]["full_neuron_scan_primary"] is False
        assert candidate["probation"]["silent_semantic_change"] is False
        assert candidate["resource_report"]["dsp_estimate"] == 0
        assert candidate["memory_estimate"]["ddr_bytes_inner_loop"] == 0
        assert candidate["runtime_estimate"]["python_calls_per_inference"] == 0
        assert candidate["performance_estimate"]["cycle_count_estimate"] > 0

    assert sandbox["candidates"]["page_block_256_updates"]["memory_estimate"]["ddr_bursts"] > 0
