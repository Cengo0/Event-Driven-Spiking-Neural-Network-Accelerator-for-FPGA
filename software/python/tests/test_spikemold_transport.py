import pytest
import numpy as np

from spikepress import InputSpike, build_eventconv_fclif_artifact, fc_lif_model, pack_spikemold_event_word64
from spikepress.transport import (
    REGISTER_OFFSETS,
    build_batch_1b_transport_smoke,
    build_eventconv_fclif_config_plan,
    decode_eventword64_input,
    event_word_type,
    lower_eventword64_input_to_axis32,
    pack_eventconv_coord32_input,
    pack_eventconv_coord32_inputs,
    pack_input_spikes,
    pack_router_connection_word,
    run_axi_lite_smoke,
    run_dma_loopback,
    run_eventword64_to_axis32_lowering_smoke,
    run_flat_fc_lif_smoke,
    run_eventword64_counter_smoke,
)


def test_axi_lite_smoke_matches_minimal_register_contract():
    smoke = run_axi_lite_smoke()

    assert smoke["ok"] is True
    assert smoke["board_executed"] is False
    assert REGISTER_OFFSETS["CTRL"] == 0x00
    assert REGISTER_OFFSETS["STATUS"] == 0x04
    assert REGISTER_OFFSETS["ERROR_CODE"] == 0x38
    assert smoke["soft_reset_clears_counters"] is True


def test_dma_loopback_hashes_match():
    words = [0x0123, 0x1000_0000_0000_0001, 0x2000_0000_0000_0002]
    loopback = run_dma_loopback(words)

    assert loopback["ok"] is True
    assert loopback["input_words"] == 3
    assert loopback["output_words"] == 3
    assert loopback["input_sha256"] == loopback["output_sha256"]
    assert loopback["counters"]["dma_calls"] == 2
    assert loopback["counters"]["python_inner_loop_steps"] == 0


def test_eventword64_counter_counts_input_words():
    spikes = [InputSpike(tick=0, src_id=0), InputSpike(tick=1, src_id=17)]
    words = pack_input_spikes(spikes)
    counter = run_eventword64_counter_smoke(words)

    assert [event_word_type(word) for word in words] == [0, 0]
    assert counter["ok"] is True
    assert counter["event_type_counts"]["input_spike"] == 2
    assert counter["event_type_counts"]["invalid"] == 0


def test_eventword64_to_axis32_lowering_matches_direct_rtl_aer32():
    word = pack_input_spikes([InputSpike(tick=3, src_id=17, payload=1)])[0]
    decoded = decode_eventword64_input(word)
    axis32 = lower_eventword64_input_to_axis32(word)
    smoke = run_eventword64_to_axis32_lowering_smoke([word])

    assert decoded["src_id"] == 17
    assert decoded["tick"] == 3
    assert decoded["signed_payload"] == 1
    assert axis32 == 17 | (1 << 13) | (3 << 21)
    assert smoke["ok"] is True
    assert smoke["word_count"] == 1
    assert smoke["output_axis32_words"] == [axis32]
    assert smoke["lossless_flat_input_semantics"] is True


def test_eventword64_to_axis32_lowering_rejects_semantic_loss():
    commit = pack_spikemold_event_word64(event_type=2, tick=0)
    too_wide_tick = pack_spikemold_event_word64(event_type=0, tick=2048)
    too_wide_direct_rtl_src = pack_spikemold_event_word64(
        event_type=0,
        tick=0,
        src_y_or_hi=1,
        src_x_or_lo=0,
    )
    nonzero_channel = pack_spikemold_event_word64(
        event_type=0,
        tick=0,
        src_x_or_lo=1,
        channel_or_dst_hi=1,
    )

    for word in [commit, too_wide_tick, too_wide_direct_rtl_src, nonzero_channel]:
        with pytest.raises(ValueError):
            lower_eventword64_input_to_axis32(word)


def test_flat_fc_lif_smoke_matches_golden_trace():
    model = fc_lif_model("tiny", weights=[[3, 1], [2, 0]], thresholds=[5, 9])
    smoke = run_flat_fc_lif_smoke(
        model,
        [
            InputSpike(tick=0, src_id=0),
            InputSpike(tick=1, src_id=1),
            InputSpike(tick=2, src_id=0),
        ],
    )

    assert smoke["ok"] is True
    assert smoke["trace_match_rate"] == 1.0
    assert smoke["readout_match"] is True
    assert smoke["state_checksum_match"] is True
    assert smoke["python_inner_loop_required"] is False
    assert smoke["counters"]["input_event_count"] == 3
    assert smoke["counters"]["update_count"] == 5
    assert smoke["counters"]["active_count"] == 2
    assert smoke["counters"]["output_words"] == 1


def test_eventconv_coord32_pack_and_config_plan():
    spike = InputSpike(tick=3, src_id=7, y=2, x=1, channel=0, payload=-1)
    assert pack_eventconv_coord32_input(spike) == 0x010200FF
    assert pack_eventconv_coord32_inputs([spike]) == [0x010200FF]

    kernel = np.ones((4, 1, 3, 3), dtype=np.int16)
    readout = np.zeros((4 * 14 * 14, 10), dtype=np.int16)
    readout[0, 0] = 3
    readout[0, 1] = -2
    artifact = build_eventconv_fclif_artifact(
        kernel=kernel,
        readout_weights=readout,
        conv_threshold=1,
        readout_thresholds=[1] * 10,
    )
    plan = build_eventconv_fclif_config_plan(artifact.manifest)

    assert plan["schema"] == "spikemold.eventconv_fclif_config_plan.v1"
    assert plan["backend_mode"] == 2
    assert plan["eventconv_shape0"] == 0x04031C1C
    assert len(plan["kernel_config_writes"]) == 9
    assert plan["kernel_config_writes"][0]["address"] == 0x02000000
    assert plan["router_config_writes"][1]["address"] == 0
    assert plan["router_config_writes"][1]["data"] == pack_router_connection_word(784, 3)
    assert plan["router_config_writes"][2]["data"] == pack_router_connection_word(785, -2)


def test_batch_1b_transport_smoke_rejects_forbidden_runtime_assumptions():
    model = fc_lif_model("tiny", weights=[[1]], thresholds=[1])
    smoke = build_batch_1b_transport_smoke(model, [InputSpike(tick=0, src_id=0)])

    assert smoke["all_ok"] is True
    assert smoke["board_executed"] is False
    assert smoke["runtime_assumptions"]["bounded_job"] is True
    assert smoke["runtime_assumptions"]["python_inner_loop_required"] is False
    assert smoke["runtime_assumptions"]["random_ddr_inner_loop"] is False
    assert smoke["runtime_assumptions"]["full_neuron_scan_primary"] is False
    assert smoke["eventword64_to_axis32"]["ok"] is True
    assert smoke["eventword64_to_axis32"]["word_count"] == 1
