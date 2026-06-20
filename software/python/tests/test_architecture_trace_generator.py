import json

from spikepress.architecture_trace_generator import (
    TRACE_SCHEMA,
    InputSpike,
    generate_eventconv_active_readout_trace,
    generate_eventconv_fclif_trace,
    generate_eventconv_trace,
    generate_fc_lif_trace,
    pack_spikemold_event_word64,
)
from spikepress.event_budget import (
    EventBudgetLimits,
    evaluate_trace_budget,
    recommended_flat_fc_lif_config,
)


def test_fc_lif_trace_is_deterministic_and_hashes():
    trace = generate_fc_lif_trace(
        input_spikes=[
            InputSpike(tick=1, src_id=1),
            InputSpike(tick=0, src_id=0),
            InputSpike(tick=2, src_id=0),
        ],
        weights={(0, 10): 3, (1, 10): 2},
        thresholds={10: 5},
    ).to_dict()

    assert trace["schema"] == TRACE_SCHEMA
    assert trace["counters"]["input_event_count"] == 3
    assert trace["counters"]["generated_update_count"] == 3
    assert trace["counters"]["commit_count"] == 1
    assert trace["counters"]["python_inner_loop_steps"] == 0
    assert trace["counters"]["ddr_bytes_inner_loop"] == 0
    assert trace["final_state"]["10"] == 3
    assert len(trace["hashes"]["trace_sha256"]) == 64


def test_eventconv_trace_uses_shared_kernel_agu_semantics():
    trace = generate_eventconv_trace(
        input_spikes=[InputSpike(tick=0, src_id=0, y=1, x=1, channel=0)],
        kernel=[[[[1, 2], [3, 4]]]],
        input_shape=(1, 3, 3),
        stride=1,
        padding=0,
        thresholds={0: 1},
    ).to_dict()

    assert trace["metadata"]["primitive"] == "eventconv_agu"
    assert trace["metadata"]["weight_storage"] == "shared_kernel"
    assert trace["metadata"]["output_shape"] == [1, 2, 2]
    assert trace["counters"]["generated_update_count"] == 4
    assert trace["counters"]["active_neuron_count"] == 4
    assert trace["counters"]["commit_count"] == 1


def test_eventconv_active_readout_trace_defers_commits_to_packet_end():
    trace = generate_eventconv_active_readout_trace(
        input_spikes=[
            InputSpike(tick=0, src_id=0, y=1, x=1, channel=0),
            InputSpike(tick=1, src_id=1, y=2, x=2, channel=0),
            InputSpike(tick=2, src_id=2, y=0, x=0, channel=0),
        ],
        kernel=[[[[1, 2], [3, 4]]]],
        input_shape=(1, 3, 3),
        stride=1,
        padding=0,
        commit_thresholds={0: 3, 1: 3, 2: 3, 3: 3},
    ).to_dict()

    assert trace["metadata"]["commit_mode"] == "packet_end_active_set"
    assert trace["metadata"]["active_neuron_count_after_commit"] == 1
    assert trace["counters"]["input_event_count"] == 3
    assert trace["counters"]["generated_update_count"] == 6
    assert trace["counters"]["commit_count"] == 3
    assert trace["commits"] == [
        {"dst_id": 3, "kind": "commit", "tick": 2, "value": 5},
        {"dst_id": 1, "kind": "commit", "tick": 2, "value": 3},
        {"dst_id": 0, "kind": "commit", "tick": 2, "value": 5},
    ]
    assert trace["final_state"] == {"2": 2}


def test_eventconv_fclif_trace_uses_internal_conv_commits_for_readout():
    trace = generate_eventconv_fclif_trace(
        input_spikes=[InputSpike(tick=0, src_id=0, y=1, x=1, channel=0)],
        kernel=[[[[1, 1], [1, 1]]]],
        input_shape=(1, 3, 3),
        readout_weights=[
            [1, 0],
            [0, 2],
            [3, 0],
            [0, 4],
        ],
        stride=1,
        padding=0,
        conv_thresholds={0: 1, 1: 1, 2: 1, 3: 1},
        readout_thresholds={4: 3, 5: 4},
    ).to_dict()

    assert trace["metadata"]["primitive"] == "eventconv_fclif"
    assert trace["metadata"]["internal_conv_commit_count"] == 4
    assert trace["metadata"]["readout_id_start"] == 4
    assert trace["counters"]["generated_update_count"] == 8
    assert trace["counters"]["commit_count"] == 2
    assert trace["commits"] == [
        {"dst_id": 5, "kind": "commit", "tick": 0, "value": 4},
        {"dst_id": 4, "kind": "commit", "tick": 0, "value": 3},
    ]


def test_eventconv_fclif_trace_uses_router_lif_inhibitory_semantics():
    trace = generate_eventconv_fclif_trace(
        input_spikes=[
            InputSpike(tick=0, src_id=0, y=0, x=0, channel=0),
            InputSpike(tick=1, src_id=1, y=0, x=1, channel=0),
        ],
        kernel=[[[[1]]]],
        input_shape=(1, 3, 3),
        readout_weights=[
            [2, -1],
            [2, -1],
            [0, 0],
            [0, 0],
            [0, 0],
            [0, 0],
            [0, 0],
            [0, 0],
            [0, 0],
        ],
        stride=1,
        padding=0,
        conv_thresholds={0: 1, 1: 1},
        readout_thresholds={9: 3, 10: 1},
        readout_id_start=9,
    ).to_dict()

    assert trace["metadata"]["readout_lif_weight_semantics"] == "router_exc_inh_magnitude_clamped"
    assert trace["counters"]["commit_count"] == 1
    assert trace["commits"] == [
        {"dst_id": 9, "kind": "commit", "tick": 1, "value": 4},
    ]


def test_trace_json_roundtrip(tmp_path):
    path = tmp_path / "trace.json"
    trace = generate_fc_lif_trace(
        input_spikes=[InputSpike(tick=0, src_id=0)],
        weights={(0, 1): 7},
        thresholds={1: 99},
    )
    trace.write_json(path)

    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["schema"] == TRACE_SCHEMA
    assert loaded["updates"][0]["weight"] == 7


def test_eventword64_pack_matches_contract_fields():
    word = pack_spikemold_event_word64(
        event_type=1,
        tick=0x1234,
        src_y_or_hi=0x155,
        src_x_or_lo=0x2AA,
        channel_or_dst_hi=0x5A,
        signed_weight=-7,
        flags=0x2A,
        target=0x15,
    )

    assert (word >> 60) & 0xF == 1
    assert (word >> 48) & 0xFFF == 0x234
    assert (word >> 38) & 0x3FF == 0x155
    assert (word >> 28) & 0x3FF == 0x2AA
    assert (word >> 20) & 0xFF == 0x5A
    assert (word >> 19) & 0x1 == 1
    assert (word >> 11) & 0xFF == 7
    assert (word >> 5) & 0x3F == 0x2A
    assert word & 0x1F == 0x15


def test_event_budget_accepts_tiny_trace_and_rejects_overflow():
    trace = generate_fc_lif_trace(
        input_spikes=[InputSpike(tick=0, src_id=0)],
        weights={(0, 1): 7},
        thresholds={1: 99},
    ).to_dict()

    assert evaluate_trace_budget(trace).ok is True

    tiny_limits = EventBudgetLimits(
        max_input_events=0,
        max_generated_updates=8,
        max_active_neurons=8,
        max_state_reads=8,
        max_state_writes=8,
    )
    rejected = evaluate_trace_budget(trace, tiny_limits)
    assert rejected.ok is False
    assert rejected.failures == ("limit_exceeded:input_event_count:1>0",)


def test_recommended_flat_fc_lif_config_exposes_runtime_guards():
    config = recommended_flat_fc_lif_config()

    assert config["target"] == "pynq-z2"
    assert config["primitive"] == "spikemold-flat-fc-lif"
    assert config["python_inner_loop_steps"] == 0
    assert config["ddr_bytes_inner_loop"] == 0
