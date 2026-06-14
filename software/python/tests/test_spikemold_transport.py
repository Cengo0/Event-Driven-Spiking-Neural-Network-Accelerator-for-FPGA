from spikepress import InputSpike, fc_lif_model
from spikepress.transport import (
    REGISTER_OFFSETS,
    build_batch_1b_transport_smoke,
    event_word_type,
    pack_input_spikes,
    run_axi_lite_smoke,
    run_dma_loopback,
    run_spikemold_mini_fc_lif_smoke,
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


def test_spikemold_mini_fc_lif_smoke_matches_golden_trace():
    model = fc_lif_model("tiny", weights=[[3, 1], [2, 0]], thresholds=[5, 9])
    smoke = run_spikemold_mini_fc_lif_smoke(
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


def test_batch_1b_transport_smoke_rejects_forbidden_runtime_assumptions():
    model = fc_lif_model("tiny", weights=[[1]], thresholds=[1])
    smoke = build_batch_1b_transport_smoke(model, [InputSpike(tick=0, src_id=0)])

    assert smoke["all_ok"] is True
    assert smoke["board_executed"] is False
    assert smoke["runtime_assumptions"]["bounded_job"] is True
    assert smoke["runtime_assumptions"]["python_inner_loop_required"] is False
    assert smoke["runtime_assumptions"]["random_ddr_inner_loop"] is False
    assert smoke["runtime_assumptions"]["full_neuron_scan_primary"] is False
