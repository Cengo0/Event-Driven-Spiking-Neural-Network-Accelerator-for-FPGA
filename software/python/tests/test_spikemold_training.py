"""Tests for SpikePress training API."""

import numpy as np
import pytest

try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False

from spikepress.training import (
    LIFNeuronConfig,
    SpikingModel,
)


@pytest.fixture
def lif_config():
    """Default LIF neuron configuration."""
    return LIFNeuronConfig(
        threshold=1.0,
        decay=1.0,
        reset=0.0,
        refractory_period=0,
        scaling_factor=65536,
    )


class TestLIFNeuronConfig:
    """Tests for LIFNeuronConfig."""

    def test_to_int32_conversion(self, lif_config):
        """Test float to int32 conversion."""
        assert lif_config.to_int32(1.0) == 65536
        assert lif_config.to_int32(0.5) == 32768
        assert lif_config.to_int32(0.0) == 0

    def test_from_hardware(self):
        """Test hardware-default config (IF aligned for SpikeMold)."""
        config = LIFNeuronConfig.from_hardware()
        assert config.threshold == 1.0
        assert config.decay == 1.0
        assert config.reset == 0.0
        assert config.refractory_period == 0


class TestSpikingModel:
    """Tests for SpikingModel."""

    def test_initialization(self, lif_config):
        """Test model initialization."""
        layer_sizes = [784, 256, 10]
        model = SpikingModel(layer_sizes, lif_config)

        assert len(model._weights) == 2
        assert model._weights[0].shape == (784, 256)
        assert model._weights[1].shape == (256, 10)

    def test_train_eval_mode(self, lif_config):
        """Test train/eval mode switching."""
        layer_sizes = [10, 5, 2]
        model = SpikingModel(layer_sizes, lif_config)

        assert model.training is True
        model.eval()
        assert model.training is False
        model.train()
        assert model.training is True

    def test_forward_pass_shape(self, lif_config):
        """Test forward pass output shapes with binary spikes + surrogate path."""
        if not _TORCH_AVAILABLE:
            pytest.skip("PyTorch not available")

        layer_sizes = [10, 5, 2]
        model = SpikingModel(layer_sizes, lif_config)

        batch_size = 4
        seq_len = 8
        # Use [0,1] binary-like inputs to mimic rate coded spikes
        input_spikes = (torch.rand(batch_size, seq_len, 10) > 0.5).float()

        output_spikes, states = model.forward(input_spikes, num_steps=seq_len)

        assert output_spikes.shape == (batch_size, seq_len, 2)
        # membrane + refractory + output_spike_counts (per-layer membrane list len == num post-synaptic = 2)
        assert len(states["membrane"]) == 2
        assert "output_spike_counts" in states
        assert states["output_spike_counts"].shape == (batch_size, 2)
        # Spikes are strictly binary 0/1
        assert output_spikes.min() >= 0.0 and output_spikes.max() <= 1.0
        assert torch.all((output_spikes == 0) | (output_spikes == 1))

    def test_get_set_weights(self, lif_config):
        """Test weight get/set operations."""
        layer_sizes = [4, 3, 2]
        model = SpikingModel(layer_sizes, lif_config)

        original_weights = model.get_weights()
        assert len(original_weights) == 2

        # Modify weights
        new_weights = [
            np.ones((4, 3), dtype=np.float32),
            np.ones((3, 2), dtype=np.float32),
        ]
        model.set_weights(new_weights)

        retrieved_weights = model.get_weights()
        assert np.array_equal(retrieved_weights[0], new_weights[0])
        assert np.array_equal(retrieved_weights[1], new_weights[1])

    def test_weight_shape_validation(self, lif_config):
        """Test weight shape validation on set."""
        layer_sizes = [4, 3, 2]
        model = SpikingModel(layer_sizes, lif_config)

        # Wrong number of weights
        with pytest.raises(ValueError):
            model.set_weights([np.ones((4, 3))])

        # Wrong shape
        with pytest.raises(ValueError):
            model.set_weights([
                np.ones((2, 2)),
                np.ones((2, 2)),
            ])

    def test_artifact_conversion(self, lif_config, tmp_path):
        """Test conversion to SpikeMold artifact."""
        layer_sizes = [10, 5, 2]
        model = SpikingModel(layer_sizes, lif_config)

        # Set specific weights for reproducibility
        model.set_weights([
            np.ones((10, 5), dtype=np.float32) * 0.5,
            np.ones((5, 2), dtype=np.float32) * 0.5,
        ])

        artifact = model.to_artifact(
            artifact_id="test_model",
            target="pynq-z2",
        )

        assert artifact.manifest["schema"] == "spikemold.artifact.v1"
        assert artifact.manifest["artifact_id"] == "test_model"
        assert artifact.manifest["target"] == "pynq-z2"

        # Check weights are int8
        weights = artifact.manifest["weights"]
        assert weights["dtype"] == "int8"

        # Verify flat buffer size
        expected_size = 10 * 5 + 5 * 2  # 60 weights
        assert len(weights["values"]) == expected_size

        # Check quantization (should be clipped to [-8, 7])
        for val in weights["values"]:
            assert -8 <= val <= 7


class TestSpikingModelIntegration:
    """Integration tests for SpikingModel."""

    def test_mnist_topology(self, lif_config):
        """Test MNIST network topology creation."""
        from spikepress.network import create_mnist_network

        network = create_mnist_network(hidden_size=2048)

        # Check layer sizes
        assert len(network.populations) == 3
        assert network.populations[0].size == 784  # input
        assert network.populations[1].size == 2048  # hidden
        assert network.populations[2].size == 10  # output

        # Check projections
        assert len(network.projections) == 2
        assert network.projections[0].source.name == "input"
        assert network.projections[0].target.name == "hidden"
        assert network.projections[1].source.name == "hidden"
        assert network.projections[1].target.name == "output"

    def test_block_sparse_topology(self, lif_config):
        """Test block-sparse MNIST topology."""
        from spikepress.network import create_mnist_block_sparse_network

        network = create_mnist_block_sparse_network(n_blocks=4, hidden_per_block=1024)

        # Check layer sizes
        assert len(network.populations) == 9  # 4 input + 4 hidden + 1 output
        assert all(p.size == 196 for p in network.populations[:4])  # input partitions
        assert all(p.size == 1024 for p in network.populations[4:8])  # hidden blocks
        assert network.populations[8].size == 10  # output

        # Check projections
        assert len(network.projections) == 8  # 4 input->hidden + 4 hidden->output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
