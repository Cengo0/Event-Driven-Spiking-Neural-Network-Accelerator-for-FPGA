import numpy as np

from spikepress import InputSpike, SpikePressModel, fc_lif_model


def test_spikepress_fc_lif_compile_and_trace():
    model = SpikePressModel("tiny")
    model.add_fc_lif(
        "readout",
        weights=[[3, 1], [2, 0]],
        thresholds=[5, 9],
    )

    compiled = model.compile_spikemold_ednp()
    trace = model.golden_trace(
        [
            InputSpike(tick=0, src_id=0),
            InputSpike(tick=1, src_id=1),
            InputSpike(tick=2, src_id=0),
        ]
    ).to_dict()

    assert compiled.artifact.manifest["schema"] == "spikemold.ednp_artifact.v1"
    assert compiled.resource_report["python_inner_loop_required"] is False
    assert trace["counters"]["generated_update_count"] == 5
    assert trace["counters"]["commit_count"] == 1


def test_spikepress_fc_lif_helper_and_budget():
    model = fc_lif_model("helper", weights=np.array([[1], [2]], dtype=np.int16), thresholds=[3])

    result = model.evaluate_sample_budget(
        [
            InputSpike(tick=0, src_id=0),
            InputSpike(tick=1, src_id=1),
        ]
    )

    assert result.ok is True
    assert result.counters["python_inner_loop_steps"] == 0
