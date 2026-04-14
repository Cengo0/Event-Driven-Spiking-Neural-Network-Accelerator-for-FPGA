"""
Phase 6.5 Cross-Verification: Python weight_index vs HLS weight_index

Verifies that the Python flat weight buffer indexing produces correct
results for all boundary conditions.  Tests both the fully-connected
`create_mnist_network()` topology and the block-sparse
`create_mnist_block_sparse_network()` HW topology.
"""

import sys
import os
import numpy as np
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from software.python.snn_fpga_accelerator.network import (
    create_mnist_network, create_mnist_block_sparse_network,
)


class TestWeightIndexFullyConnected:
    """Verify compiled.weight_index() for fully-connected MNIST topology."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """MNIST network: input(784), hidden(2048), output(10)."""
        self.net = create_mnist_network()
        self.compiled = self.net.compile()
        # Connection 0: input→hidden, offset=0, src_size=784, dst_size=2048
        # Connection 1: hidden→output, offset=1605632, src_size=2048, dst_size=10
        # group_id_start = [0, 784, 2832, 2842]

    def test_connection0_first_entry(self):
        """input[0] → hidden[784]: flat index should be 0."""
        assert self.compiled.weight_index(0, 784) == 0

    def test_connection0_last_entry(self):
        """input[783] → hidden[2831]: last entry of connection 0."""
        expected = 783 * 2048 + 2047  # = 1,605,631
        assert self.compiled.weight_index(783, 2831) == expected

    def test_connection1_first_entry(self):
        """hidden[784] → output[2832]: first entry of connection 1."""
        assert self.compiled.weight_index(784, 2832) == 1605632

    def test_connection1_last_entry(self):
        """hidden[2831] → output[2841]: last entry of connection 1."""
        expected = 1605632 + 2047 * 10 + 9  # = 1,626,111
        assert self.compiled.weight_index(2831, 2841) == expected

    def test_no_connection_input_to_output(self):
        """No direct input→output connection → -1."""
        assert self.compiled.weight_index(0, 2832) == -1

    def test_no_connection_hidden_to_input(self):
        """No hidden→input connection → -1."""
        assert self.compiled.weight_index(784, 0) == -1

    def test_same_group_no_connection(self):
        """Intra-group (input→input) → -1."""
        assert self.compiled.weight_index(0, 1) == -1

    def test_out_of_range_neuron(self):
        """Neuron ID beyond total_logical_neurons → -1."""
        assert self.compiled.weight_index(2842, 0) == -1

    def test_pack_unpack_roundtrip(self):
        """Pack random weights → unpack → verify flat buffer values."""
        rng = np.random.default_rng(123)
        w_ih = rng.integers(-8, 8, (784, 2048), dtype=np.int8)  # 4-bit range
        w_ho = rng.integers(-8, 8, (2048, 10), dtype=np.int8)

        flat = self.compiled.pack_weights({
            'input_to_hidden': w_ih,
            'hidden_to_output': w_ho,
        })

        # Spot checks
        assert flat[self.compiled.weight_index(0, 784)] == w_ih[0, 0]
        assert flat[self.compiled.weight_index(783, 2831)] == w_ih[783, 2047]
        assert flat[self.compiled.weight_index(784, 2832)] == w_ho[0, 0]
        assert flat[self.compiled.weight_index(2831, 2841)] == w_ho[2047, 9]

        # Full roundtrip
        unpacked = self.compiled.unpack_weights(flat)
        np.testing.assert_array_equal(unpacked['input_to_hidden'], w_ih)
        np.testing.assert_array_equal(unpacked['hidden_to_output'], w_ho)

    def test_buffer_size(self):
        """FC buffer: 784*2048 + 2048*10 = 1,626,112."""
        assert self.compiled.max_weight_buffer_size == 1626112

    def test_total_neurons(self):
        """FC total: 784 + 2048 + 10 = 2,842."""
        assert self.compiled.total_logical_neurons == 2842


class TestWeightIndexBlockSparse:
    """Verify compiled.weight_index() for block-sparse K=1024 topology."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Block-sparse K=1024: 4×(196→1024) + 4×(1024→10)."""
        self.net = create_mnist_block_sparse_network(n_blocks=4, hidden_per_block=1024)
        self.compiled = self.net.compile()
        # 9 NeuronGroups:
        #   input_0(196) input_1(196) input_2(196) input_3(196)
        #   hidden_0(1024) hidden_1(1024) hidden_2(1024) hidden_3(1024)
        #   output(10)
        # group_id_start = [0, 196, 392, 588, 784, 1808, 2832, 3856, 4880, 4890]

    def test_block0_first_entry(self):
        """input_0[0] → hidden_0[784]: first weight."""
        assert self.compiled.weight_index(0, 784) == 0

    def test_block0_last_entry(self):
        """input_0[195] → hidden_0[1807]: last weight of block 0."""
        expected = 195 * 1024 + 1023  # = 200,703
        assert self.compiled.weight_index(195, 1807) == expected

    def test_block1_first_entry(self):
        """input_1[196] → hidden_1[1808]: first weight of block 1."""
        expected = 200704  # offset of connection 1
        assert self.compiled.weight_index(196, 1808) == expected

    def test_hid0_to_output_first(self):
        """hidden_0[784] → output[4880]: first hid→out weight."""
        expected = 802816  # 4 × (196×1024) = 802,816
        assert self.compiled.weight_index(784, 4880) == expected

    def test_no_cross_block(self):
        """input_0 → hidden_1: no connection in block-sparse → -1."""
        assert self.compiled.weight_index(0, 1808) == -1

    def test_total_neurons(self):
        """Block-sparse total: 4×196 + 4×1024 + 10 = 4,890."""
        assert self.compiled.total_logical_neurons == 4890

    def test_buffer_size(self):
        """Block-sparse buffer: 4×(196×1024) + 4×(1024×10) = 843,776."""
        assert self.compiled.max_weight_buffer_size == 843776

    def test_random_consistency(self):
        """Random pairs: weight_index must return valid offsets or -1."""
        rng = np.random.default_rng(42)
        for _ in range(1000):
            pre = rng.integers(0, 4890)
            post = rng.integers(0, 4890)
            idx = self.compiled.weight_index(pre, post)
            if idx >= 0:
                assert idx < 843776, f"Index {idx} out of range for ({pre},{post})"
