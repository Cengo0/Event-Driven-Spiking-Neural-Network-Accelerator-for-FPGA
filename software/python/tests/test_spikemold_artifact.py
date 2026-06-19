import numpy as np

from spikepress.spikemold_artifact import (
    ARTIFACT_SCHEMA,
    EVENTCONV_FCLIF_BACKEND_MODE,
    EVENTCONV_FCLIF_KIND,
    build_eventconv_fclif_artifact,
    build_spikemold_artifact,
    read_spikemold_artifact,
    refresh_spikemold_artifact_hash,
    validate_eventconv_fclif_manifest,
    write_spikemold_artifact,
)
from spikepress.network import (
    PACKED_MAX_WEIGHT,
    PACKED_MIN_WEIGHT,
    SpikePressNeuronPopulation,
    SpikePressProjection,
    SpikePressNetwork,
)


def _tiny_compiled_network():
    network = SpikePressNetwork()
    input_population = network.add_population(SpikePressNeuronPopulation(2, "input"))
    output_population = network.add_population(SpikePressNeuronPopulation(3, "output"))
    network.add_projection(SpikePressProjection(input_population, output_population, name="input_to_output"))
    return network.compile()


def test_spikemold_artifact_roundtrip(tmp_path):
    compiled = _tiny_compiled_network()
    weights = {
        "input_to_output": np.array(
            [[1, 2, 3], [4, 5, 6]],
            dtype=np.int8,
        )
    }
    artifact = build_spikemold_artifact(compiled, weights, artifact_id="tiny")
    path = tmp_path / "artifact.json"
    write_spikemold_artifact(path, artifact)

    loaded = read_spikemold_artifact(path)

    assert loaded.manifest["schema"] == ARTIFACT_SCHEMA
    assert loaded.manifest["target"] == "pynq-z2"
    assert loaded.manifest["network"]["total_logical_neurons"] == 5
    assert len(loaded.manifest["network"]["populations"]) == 2
    assert len(loaded.manifest["network"]["projections"]) == 1
    np.testing.assert_array_equal(loaded.flat_weights, artifact.flat_weights)
    assert loaded.sha256 == artifact.sha256


def test_spikemold_artifact_clips_to_hardware_weight_range():
    compiled = _tiny_compiled_network()
    artifact = build_spikemold_artifact(
        compiled,
        {
            "input_to_output": np.array(
                [
                    [PACKED_MAX_WEIGHT + 1, PACKED_MIN_WEIGHT - 1, 0],
                    [PACKED_MAX_WEIGHT, PACKED_MIN_WEIGHT, 1],
                ],
                dtype=np.int16,
            )
        },
    )

    assert artifact.flat_weights.tolist() == [
        PACKED_MAX_WEIGHT,
        PACKED_MIN_WEIGHT,
        0,
        PACKED_MAX_WEIGHT,
        PACKED_MIN_WEIGHT,
        1,
    ]
    assert artifact.manifest["contracts"]["trace_schema"] == "TRACE_SCHEMA_V1"


def test_spikemold_artifact_hash_refresh_after_metadata_update(tmp_path):
    compiled = _tiny_compiled_network()
    artifact = build_spikemold_artifact(
        compiled,
        {"input_to_output": np.ones((2, 3), dtype=np.int8)},
        artifact_id="tiny",
    )
    manifest = dict(artifact.manifest)
    manifest["training"] = {"accuracy": 0.9}
    refreshed = refresh_spikemold_artifact_hash(
        type(artifact)(manifest=manifest, flat_weights=artifact.flat_weights)
    )
    path = tmp_path / "refreshed.json"
    write_spikemold_artifact(path, refreshed)

    loaded = read_spikemold_artifact(path)
    assert loaded.manifest["training"]["accuracy"] == 0.9
    assert loaded.sha256 == refreshed.sha256


def test_eventconv_fclif_artifact_roundtrip_and_deployability(tmp_path):
    kernel = np.ones((4, 1, 3, 3), dtype=np.int16)
    readout = np.zeros((4 * 14 * 14, 10), dtype=np.int16)
    readout[:, :] = np.arange(10, dtype=np.int16) - 4

    artifact = build_eventconv_fclif_artifact(
        kernel=kernel,
        readout_weights=readout,
        conv_threshold=2,
        readout_thresholds=[2] * 10,
        artifact_id="frozen",
    )
    path = tmp_path / "eventconv_fclif.json"
    write_spikemold_artifact(path, artifact)
    loaded = read_spikemold_artifact(path)
    report = validate_eventconv_fclif_manifest(loaded.manifest)

    assert loaded.manifest["schema"] == ARTIFACT_SCHEMA
    assert loaded.manifest["kind"] == EVENTCONV_FCLIF_KIND
    assert loaded.manifest["runtime"]["backend_mode"] == EVENTCONV_FCLIF_BACKEND_MODE
    assert loaded.manifest["network"]["total_logical_neurons"] == 794
    assert loaded.manifest["network"]["eventconv"]["output_shape"] == [4, 14, 14]
    assert loaded.manifest["network"]["readout"]["max_fanout"] == 9
    assert report["ok"] is True
    np.testing.assert_array_equal(loaded.flat_weights, artifact.flat_weights)


def test_eventconv_fclif_artifact_rejects_unsupported_shape():
    kernel = np.ones((8, 1, 3, 3), dtype=np.int16)
    readout = np.ones((8 * 14 * 14, 10), dtype=np.int16)

    try:
        build_eventconv_fclif_artifact(kernel=kernel, readout_weights=readout)
    except ValueError as exc:
        assert "limit" in str(exc) or "unsupported" in str(exc)
    else:
        raise AssertionError("unsupported shape should be rejected")
