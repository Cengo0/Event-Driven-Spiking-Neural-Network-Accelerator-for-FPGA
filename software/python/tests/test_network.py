"""
Tests for SpikePress network topology API.

Validates the SpikePress topology builder, flat weight buffer packing,
and consistency with HLS weight_index().
"""

import sys
import os
import numpy as np
import pytest

# Ensure project root is on sys.path so config.generated is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from spikepress.network import (
    SpikePressNeuronPopulation,
    SpikePressProjection,
    SpikePressNetwork,
    create_mnist_network,
)


class TestSpikePressNeuronPopulation:
    def test_create(self):
        population = SpikePressNeuronPopulation(784, name="input")
        assert population.size == 784
        assert population.name == "input"

    def test_invalid_size(self):
        with pytest.raises(ValueError):
            SpikePressNeuronPopulation(0)


class TestSpikePressProjection:
    def test_create(self):
        input_population = SpikePressNeuronPopulation(784, "input")
        hidden_population = SpikePressNeuronPopulation(2048, "hidden")
        projection = SpikePressProjection(input_population, hidden_population)
        assert projection.num_weights == 784 * 2048
        assert projection.name == "input_to_hidden"

    def test_weight_shape(self):
        source_population = SpikePressNeuronPopulation(10, "a")
        target_population = SpikePressNeuronPopulation(5, "b")
        projection = SpikePressProjection(source_population, target_population)
        assert projection.weights.shape == (10, 5)
        assert projection.weights.dtype == np.int8

    def test_weight_assignment(self):
        source_population = SpikePressNeuronPopulation(3, "a")
        target_population = SpikePressNeuronPopulation(2, "b")
        projection = SpikePressProjection(source_population, target_population)
        weights = np.array([[1, 2], [3, 4], [5, 6]], dtype=np.int8)
        projection.weights = weights
        np.testing.assert_array_equal(projection.weights, weights)

    def test_weight_shape_mismatch(self):
        source_population = SpikePressNeuronPopulation(3, "a")
        target_population = SpikePressNeuronPopulation(2, "b")
        projection = SpikePressProjection(source_population, target_population)
        with pytest.raises(ValueError):
            projection.weights = np.zeros((4, 2), dtype=np.int8)


class TestSpikePressNetwork:
    def test_compile_simple(self):
        network = SpikePressNetwork()
        input_population = network.add_population(SpikePressNeuronPopulation(10, "input"))
        hidden_population = network.add_population(SpikePressNeuronPopulation(20, "hidden"))
        output_population = network.add_population(SpikePressNeuronPopulation(5, "output"))
        network.add_projection(SpikePressProjection(input_population, hidden_population))
        network.add_projection(SpikePressProjection(hidden_population, output_population))
        compiled = network.compile()

        assert compiled.total_logical_neurons == 35
        assert compiled.max_weight_buffer_size == 10 * 20 + 20 * 5
        assert len(compiled.projections) == 2
        assert compiled.population_id_start == [0, 10, 30, 35]

    def test_projection_offsets(self):
        network = SpikePressNetwork()
        a_population = network.add_population(SpikePressNeuronPopulation(4, "a"))
        b_population = network.add_population(SpikePressNeuronPopulation(3, "b"))
        c_population = network.add_population(SpikePressNeuronPopulation(2, "c"))
        network.add_projection(SpikePressProjection(a_population, b_population))
        network.add_projection(SpikePressProjection(b_population, c_population))
        compiled = network.compile()

        assert compiled.projections[0].weight_offset == 0
        assert compiled.projections[0].num_weights == 12  # 4*3
        assert compiled.projections[1].weight_offset == 12
        assert compiled.projections[1].num_weights == 6   # 3*2

    def test_cannot_modify_after_compile(self):
        network = SpikePressNetwork()
        network.add_population(SpikePressNeuronPopulation(5, "x"))
        network.compile()
        with pytest.raises(RuntimeError):
            network.add_population(SpikePressNeuronPopulation(3, "y"))

    def test_unregistered_population_rejected(self):
        network = SpikePressNetwork()
        a_population = network.add_population(SpikePressNeuronPopulation(5, "a"))
        orphan_population = SpikePressNeuronPopulation(3, "orphan")
        with pytest.raises(ValueError):
            network.add_projection(SpikePressProjection(a_population, orphan_population))


class TestPackUnpack:
    @pytest.fixture
    def compiled(self):
        network = SpikePressNetwork()
        a_population = network.add_population(SpikePressNeuronPopulation(3, "a"))
        b_population = network.add_population(SpikePressNeuronPopulation(2, "b"))
        c_population = network.add_population(SpikePressNeuronPopulation(2, "c"))
        network.add_projection(SpikePressProjection(a_population, b_population))
        network.add_projection(SpikePressProjection(b_population, c_population))
        return network.compile()

    def test_round_trip(self, compiled):
        weights_ab = np.array([[1, 2], [3, 4], [5, 6]], dtype=np.int8)
        weights_bc = np.array([[-3, 5], [-7, 2]], dtype=np.int8)
        flat = compiled.pack_weights({"a_to_b": weights_ab, "b_to_c": weights_bc})

        assert flat.shape == (10,)
        unpacked = compiled.unpack_weights(flat)
        np.testing.assert_array_equal(unpacked["a_to_b"], weights_ab)
        np.testing.assert_array_equal(unpacked["b_to_c"], weights_bc)

    def test_weight_index(self, compiled):
        # a=[0..2], b=[3..4], c=[5..6]
        # a→b projection: offset 0, dst_size=2
        # weight_index(pre=0, post=3) = 0 + 0*2 + 0 = 0
        assert compiled.weight_index(0, 3) == 0
        # weight_index(pre=2, post=4) = 0 + 2*2 + 1 = 5
        assert compiled.weight_index(2, 4) == 5
        # b→c projection: offset 6, dst_size=2
        # weight_index(pre=3, post=5) = 6 + 0*2 + 0 = 6
        assert compiled.weight_index(3, 5) == 6
        # No projection a→c
        assert compiled.weight_index(0, 5) == -1

    def test_wrong_shape_rejected(self, compiled):
        with pytest.raises(ValueError):
            compiled.pack_weights({"a_to_b": np.zeros((4, 2), dtype=np.int8)})


class TestMNISTNetwork:
    def test_default_mnist(self):
        network = create_mnist_network()
        compiled = network.compile()
        assert compiled.total_logical_neurons == 784 + 2048 + 10
        assert compiled.max_weight_buffer_size == 784 * 2048 + 2048 * 10

    def test_custom_hidden(self):
        network = create_mnist_network(hidden_size=400)
        compiled = network.compile()
        assert compiled.total_logical_neurons == 784 + 400 + 10
        assert compiled.max_weight_buffer_size == 784 * 400 + 400 * 10

    def test_summary(self):
        network = create_mnist_network()
        network.compile()
        summary = network.summary()
        assert "input" in summary
        assert "hidden" in summary
        assert "1,626,112" in summary


class TestFromConfig:
    def test_from_config_matches_constants(self):
        """Network from HW config must produce identical buffer sizes."""
        try:
            network = SpikePressNetwork.from_config()
        except RuntimeError:
            pytest.skip("config.generated.spikemold_params not available")
        compiled = network.compile()
        errors = compiled.validate_against_hardware()
        assert errors == [], f"Mismatch: {errors}"
