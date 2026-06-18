"""Generate MNIST-scale golden traces for DESIGN-GUIDE Batch 2."""

import json
from pathlib import Path

from spikepress.architecture_trace_generator import (
    InputSpike,
    generate_multilayer_fc_lif_trace,
    generate_eventconv_trace,
)
from spikepress.spikemold_artifact import write_spikemold_artifact


def generate_mnist_fclif_trace():
    """Generate MNIST-scale FC-LIF trace (784 -> 512 -> 10).

    Uses sparse connectivity to fit within PYNQ-Z2 BRAM constraints.
    """
    # Sparse weight generation for MNIST
    # Input: 784 pixels, Hidden: 512 neurons, Output: 10 classes

    # Create sparse input-to-hidden weights (every 16th connection)
    weights_input_hidden = {}
    for src in range(784):
        for dst in range(512):
            if src % 16 == 0 and dst % 16 == 0:
                weights_input_hidden[(src, dst)] = 1

    # Create sparse hidden-to-output weights
    weights_hidden_output = {}
    for src in range(512):
        for dst in range(10):
            if src % 64 == 0:
                weights_hidden_output[(src, dst)] = 2

    # Thresholds - lower for output to encourage firing
    thresholds_hidden = {j: 10 for j in range(512)}
    thresholds_output = {j: 3 for j in range(10)}

    layer_configs = [
        {
            'name': 'hidden',
            'weights': weights_input_hidden,
            'thresholds': thresholds_hidden,
            'reset_values': {},
        },
        {
            'name': 'output',
            'weights': weights_hidden_output,
            'thresholds': thresholds_output,
            'reset_values': {},
        },
    ]

    # Input spikes - represent MNIST pixel activations
    input_spikes = [
        InputSpike(tick=0, src_id=i, payload=1)
        for i in range(784)
        if i % 10 == 0  # Sparse sampling of input pixels
    ]

    trace = generate_multilayer_fc_lif_trace(
        layer_configs=layer_configs,
        input_spikes=input_spikes,
        trace_id='mnist_fclif_784_512_10_v1',
        target='pynq-z2',
    )

    return trace


def generate_mnist_eventconv_trace():
    """Generate MNIST-scale EventConv trace.

    Uses 3x3 kernel on 28x28 input with shared weights.
    """
    # 3x3 kernel for MNIST (single output channel for simplicity)
    kernel = [[[
        [1, 0, -1],
        [2, 0, -2],
        [1, 0, -1],
    ]]]

    input_shape = (1, 28, 28)  # MNIST grayscale

    # Input spikes representing edge activations
    input_spikes = [
        InputSpike(tick=0, src_id=0, y=14, x=14, channel=0, payload=1),
        InputSpike(tick=1, src_id=1, y=7, x=7, channel=0, payload=1),
        InputSpike(tick=2, src_id=2, y=21, x=21, channel=0, payload=1),
    ]

    trace = generate_eventconv_trace(
        input_spikes=input_spikes,
        kernel=kernel,
        input_shape=input_shape,
        stride=1,
        padding=1,
        trace_id='mnist_eventconv_28x28_3x3_v1',
    )

    return trace


def main():
    """Generate all MNIST-scale traces."""
    output_dir = Path('golden_traces/v1')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate FC-LIF trace
    fclif_trace = generate_mnist_fclif_trace()
    fclif_path = output_dir / 'mnist_fclif_784_512_10_v1.json'
    fclif_trace.write_json(fclif_path)
    print(f"Generated: {fclif_path}")
    print(f"  Updates: {fclif_trace.counters.generated_update_count}")
    print(f"  Commits: {fclif_trace.counters.commit_count}")

    # Generate EventConv trace
    eventconv_trace = generate_mnist_eventconv_trace()
    eventconv_path = output_dir / 'mnist_eventconv_28x28_3x3_v1.json'
    eventconv_trace.write_json(eventconv_path)
    print(f"Generated: {eventconv_path}")
    print(f"  Updates: {eventconv_trace.counters.generated_update_count}")
    print(f"  Commits: {eventconv_trace.counters.commit_count}")


if __name__ == '__main__':
    main()
