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
    NeuronGroup,
    Synapses,
    SpikePressNetwork,
    CompiledSpikePressNetwork,
    create_mnist_network,
)


class TestNeuronGroup:
    def test_create(self):
        g = NeuronGroup(784, name='input')
        assert g.n == 784
        assert g.name == 'input'

    def test_invalid_size(self):
        with pytest.raises(ValueError):
            NeuronGroup(0)


class TestSynapses:
    def test_create(self):
        src = NeuronGroup(784, 'input')
        dst = NeuronGroup(2048, 'hidden')
        syn = Synapses(src, dst)
        assert syn.num_weights == 784 * 2048
        assert syn.name == 'input_to_hidden'

    def test_weight_shape(self):
        src = NeuronGroup(10, 'a')
        dst = NeuronGroup(5, 'b')
        syn = Synapses(src, dst)
        assert syn.w.shape == (10, 5)
        assert syn.w.dtype == np.int8

    def test_weight_assignment(self):
        src = NeuronGroup(3, 'a')
        dst = NeuronGroup(2, 'b')
        syn = Synapses(src, dst)
        w = np.array([[1, 2], [3, 4], [5, 6]], dtype=np.int8)
        syn.w = w
        np.testing.assert_array_equal(syn.w, w)

    def test_weight_shape_mismatch(self):
        src = NeuronGroup(3, 'a')
        dst = NeuronGroup(2, 'b')
        syn = Synapses(src, dst)
        with pytest.raises(ValueError):
            syn.w = np.zeros((4, 2), dtype=np.int8)


class TestSpikePressNetwork:
    def test_compile_simple(self):
        net = SpikePressNetwork()
        inp = net.add_group(NeuronGroup(10, 'input'))
        hid = net.add_group(NeuronGroup(20, 'hidden'))
        out = net.add_group(NeuronGroup(5, 'output'))
        net.add_synapses(Synapses(inp, hid))
        net.add_synapses(Synapses(hid, out))
        c = net.compile()

        assert c.total_logical_neurons == 35
        assert c.max_weight_buffer_size == 10 * 20 + 20 * 5  # 300
        assert len(c.connections) == 2
        assert c.group_id_start == [0, 10, 30, 35]

    def test_connection_offsets(self):
        net = SpikePressNetwork()
        a = net.add_group(NeuronGroup(4, 'a'))
        b = net.add_group(NeuronGroup(3, 'b'))
        c = net.add_group(NeuronGroup(2, 'c'))
        net.add_synapses(Synapses(a, b))
        net.add_synapses(Synapses(b, c))
        compiled = net.compile()

        assert compiled.connections[0].weight_offset == 0
        assert compiled.connections[0].num_weights == 12  # 4*3
        assert compiled.connections[1].weight_offset == 12
        assert compiled.connections[1].num_weights == 6   # 3*2

    def test_cannot_modify_after_compile(self):
        net = SpikePressNetwork()
        g = net.add_group(NeuronGroup(5, 'x'))
        net.compile()
        with pytest.raises(RuntimeError):
            net.add_group(NeuronGroup(3, 'y'))

    def test_unregistered_group_rejected(self):
        net = SpikePressNetwork()
        a = net.add_group(NeuronGroup(5, 'a'))
        orphan = NeuronGroup(3, 'orphan')
        with pytest.raises(ValueError):
            net.add_synapses(Synapses(a, orphan))


class TestPackUnpack:
    @pytest.fixture
    def compiled(self):
        net = SpikePressNetwork()
        a = net.add_group(NeuronGroup(3, 'a'))
        b = net.add_group(NeuronGroup(2, 'b'))
        c = net.add_group(NeuronGroup(2, 'c'))
        net.add_synapses(Synapses(a, b))
        net.add_synapses(Synapses(b, c))
        return net.compile()

    def test_round_trip(self, compiled):
        w_ab = np.array([[1, 2], [3, 4], [5, 6]], dtype=np.int8)
        w_bc = np.array([[-3, 5], [-7, 2]], dtype=np.int8)  # 4-bit range: [-8, 7]
        flat = compiled.pack_weights({'a_to_b': w_ab, 'b_to_c': w_bc})

        assert flat.shape == (10,)  # 3*2 + 2*2
        unpacked = compiled.unpack_weights(flat)
        np.testing.assert_array_equal(unpacked['a_to_b'], w_ab)
        np.testing.assert_array_equal(unpacked['b_to_c'], w_bc)

    def test_weight_index(self, compiled):
        # a=[0..2], b=[3..4], c=[5..6]
        # a→b connection: offset 0, dst_size=2
        # weight_index(pre=0, post=3) = 0 + 0*2 + 0 = 0
        assert compiled.weight_index(0, 3) == 0
        # weight_index(pre=2, post=4) = 0 + 2*2 + 1 = 5
        assert compiled.weight_index(2, 4) == 5
        # b→c connection: offset 6, dst_size=2
        # weight_index(pre=3, post=5) = 6 + 0*2 + 0 = 6
        assert compiled.weight_index(3, 5) == 6
        # No connection a→c
        assert compiled.weight_index(0, 5) == -1

    def test_wrong_shape_rejected(self, compiled):
        with pytest.raises(ValueError):
            compiled.pack_weights({'a_to_b': np.zeros((4, 2), dtype=np.int8)})


class TestMNISTNetwork:
    def test_default_mnist(self):
        net = create_mnist_network()
        c = net.compile()
        assert c.total_logical_neurons == 784 + 2048 + 10  # 2842
        assert c.max_weight_buffer_size == 784 * 2048 + 2048 * 10  # 1,626,112

    def test_custom_hidden(self):
        net = create_mnist_network(n_hidden=400)
        c = net.compile()
        assert c.total_logical_neurons == 784 + 400 + 10
        assert c.max_weight_buffer_size == 784 * 400 + 400 * 10

    def test_summary(self):
        net = create_mnist_network()
        net.compile()
        s = net.summary()
        assert 'input' in s
        assert 'hidden' in s
        assert '1,626,112' in s


class TestFromConfig:
    def test_from_config_matches_constants(self):
        """Network from HW config must produce identical buffer sizes."""
        try:
            net = SpikePressNetwork.from_config()
        except RuntimeError:
            pytest.skip("config.generated.snn_params not available")
        c = net.compile()
        errors = c.validate_against_hardware()
        assert errors == [], f"Mismatch: {errors}"
