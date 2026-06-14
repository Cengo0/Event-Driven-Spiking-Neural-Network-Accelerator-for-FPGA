import numpy as np

from snn_fpga_accelerator.ednp_artifact import (
    ARTIFACT_SCHEMA,
    build_ednp_artifact,
    read_ednp_artifact,
    write_ednp_artifact,
)
from snn_fpga_accelerator.network import NeuronGroup, SNNNetwork, Synapses


def _tiny_compiled_network():
    net = SNNNetwork()
    src = net.add_group(NeuronGroup(2, "input"))
    dst = net.add_group(NeuronGroup(3, "output"))
    net.add_synapses(Synapses(src, dst, name="input_to_output"))
    return net.compile()


def test_ednp_artifact_roundtrip(tmp_path):
    compiled = _tiny_compiled_network()
    weights = {
        "input_to_output": np.array(
            [[1, 2, 3], [4, 5, 6]],
            dtype=np.int8,
        )
    }
    artifact = build_ednp_artifact(compiled, weights, artifact_id="tiny")
    path = tmp_path / "artifact.json"
    write_ednp_artifact(path, artifact)

    loaded = read_ednp_artifact(path)

    assert loaded.manifest["schema"] == ARTIFACT_SCHEMA
    assert loaded.manifest["target"] == "pynq-z2"
    assert loaded.manifest["network"]["total_logical_neurons"] == 5
    np.testing.assert_array_equal(loaded.flat_weights, artifact.flat_weights)
    assert loaded.sha256 == artifact.sha256


def test_ednp_artifact_clips_to_hardware_weight_range():
    compiled = _tiny_compiled_network()
    artifact = build_ednp_artifact(
        compiled,
        {"input_to_output": np.array([[99, -99, 0], [7, -8, 1]], dtype=np.int16)},
    )

    assert artifact.flat_weights.tolist() == [7, -8, 0, 7, -8, 1]
    assert artifact.manifest["contracts"]["trace_schema"] == "TRACE_SCHEMA_V1"
