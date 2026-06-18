"""Generate CIFAR-10 EventConvSNN traces for DESIGN-GUIDE Batch 2C."""

import pickle
from pathlib import Path
from spikepress.architecture_trace_generator import (
    InputSpike,
    generate_eventconv_active_readout_trace,
)
from spikepress.spikemold_artifact import write_spikemold_artifact


def load_cifar_batch(batch_path):
    """Load a single CIFAR-10 batch."""
    with open(batch_path, "rb") as f:
        data = pickle.load(f, encoding="bytes")
    return data


def load_cifar_dataset(dataset_dir):
    """Load all CIFAR-10 training batches."""
    all_data = []
    for i in range(1, 6):
        batch_path = Path(dataset_dir) / f"data_batch_{i}"
        data = load_cifar_batch(batch_path)
        all_data.append(data)
    return all_data


def grayscale_conversion(r, g, b):
    """Convert RGB to grayscale using standard weights."""
    return 0.299 * r + 0.587 * g + 0.114 * b


def create_spikemold_event_word64_from_pixel(x, y, channel, intensity, tick):
    """Create a SpikeMold EventWord64 from pixel data.

    Format: [31:28] event_type, [27:16] tick, [15:6] y, [5:0] x
    """
    event_type = 0x1  # Spike event
    word = 0
    word |= (event_type & 0xF) << 60
    word |= (tick & 0xFFF) << 48
    word |= ((y >> 4) & 0x3FF) << 38  # High bits of y
    word |= ((x >> 4) & 0x3FF) << 28  # High bits of x
    word |= ((channel >> 6) & 0xFF) << 20  # Channel high bits
    word |= 1 << 19  # Sign bit (positive)
    word |= ((intensity >> 4) & 0x3FF) << 9  # Intensity (scaled down)
    word |= (tick & 0x1FF)  # Tick low bits
    return word


def generate_cifar_eventconv_trace(sample_idx=0, threshold=5):
    """Generate EventConv trace for a CIFAR-10 image.

    Uses a 3x3 edge detection kernel to create event-driven representation.
    """
    # Load first training batch for demonstration
    dataset_dir = "data/cifar10/cifar-10-batches-py"
    data = load_cifar_batch(Path(dataset_dir) / "data_batch_1")

    images = data[b"data"]  # Shape: (10000, 3072)
    labels = data[b"labels"]

    if sample_idx >= len(images):
        sample_idx = 0

    image = images[sample_idx].reshape(3, 32, 32)
    label = labels[sample_idx]

    # Convert to grayscale and threshold
    gray = grayscale_conversion(
        image[0].astype(float),
        image[1].astype(float),
        image[2].astype(float)
    )

    # Create binary edge map (spike events where gradient is high)
    input_spikes = []
    tick = 0
    for y in range(32):
        for x in range(32):
            # Simple threshold-based spike generation
            if gray[y, x] > 128:  # Threshold
                input_spikes.append(InputSpike(
                    tick=tick,
                    src_id=y * 32 + x,
                    y=y,
                    x=x,
                    channel=0,  # Use grayscale as single channel
                    payload=int(gray[y, x] / 16)  # Scale intensity
                ))
                tick += 1

    # 3x3 edge detection kernel (Sobel-like)
    kernel = [[[
        [-1, 0, 1],
        [-2, 0, 2],
        [-1, 0, 1],
    ]]]

    trace = generate_eventconv_active_readout_trace(
        input_spikes=input_spikes,
        kernel=kernel,
        input_shape=(1, 32, 32),
        stride=1,
        padding=1,
        commit_thresholds=None,  # No threshold - all activations
        trace_id=f"cifar10_eventconv_32x32_3x3_sample_{sample_idx}_v1",
    )

    return trace


def generate_cifar_batch_trace(sample_start=0, num_samples=5, threshold=5):
    """Generate EventConv traces for multiple CIFAR-10 samples.

    Returns combined trace with all samples processed sequentially.
    """
    dataset_dir = "data/cifar10/cifar-10-batches-py"
    data = load_cifar_batch(Path(dataset_dir) / "data_batch_1")
    images = data[b"data"]
    labels = data[b"labels"]

    all_spikes = []
    sample_info = []

    for i in range(num_samples):
        idx = (sample_start + i) % len(images)
        image = images[idx].reshape(3, 32, 32)
        label = labels[idx]

        # Convert to grayscale
        gray = grayscale_conversion(
            image[0].astype(float),
            image[1].astype(float),
            image[2].astype(float)
        )

        # Create spike events
        tick_offset = len(all_spikes)
        for y in range(32):
            for x in range(32):
                if gray[y, x] > 128:
                    all_spikes.append(InputSpike(
                        tick=tick_offset + (y * 32 + x),
                        src_id=idx * 1024 + y * 32 + x,
                        y=y,
                        x=x,
                        channel=0,
                        payload=int(gray[y, x] / 16)
                    ))

        sample_info.append({"idx": idx, "label": label})

    # 3x3 edge detection kernel
    kernel = [[[
        [-1, 0, 1],
        [-2, 0, 2],
        [-1, 0, 1],
    ]]]

    trace = generate_eventconv_active_readout_trace(
        input_spikes=all_spikes,
        kernel=kernel,
        input_shape=(1, 32, 32),
        stride=1,
        padding=1,
        commit_thresholds=None,
        trace_id=f"cifar10_eventconv_32x32_batch_{sample_start}_{num_samples}_v1",
    )

    return trace, sample_info


def main():
    """Generate CIFAR-10 EventConv traces."""
    output_dir = Path("golden_traces/v1")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate single sample trace
    print("Generating CIFAR-10 EventConv traces...")

    for sample_idx in range(3):
        trace, _ = generate_cifar_batch_trace(sample_start=sample_idx, num_samples=1)

        output_path = output_dir / f"cifar10_eventconv_sample_{sample_idx}_v1.json"
        trace.write_json(output_path)

        print(f"\nGenerated: {output_path}")
        print(f"  Input spikes: {trace.counters.input_event_count}")
        print(f"  Updates: {trace.counters.generated_update_count}")
        print(f"  Commits: {trace.counters.commit_count}")

    # Generate batch trace (5 samples)
    trace, sample_info = generate_cifar_batch_trace(sample_start=0, num_samples=5)
    output_path = output_dir / "cifar10_eventconv_batch_5_v1.json"
    trace.write_json(output_path)

    print(f"\nGenerated: {output_path}")
    print(f"  Input spikes: {trace.counters.input_event_count}")
    print(f"  Updates: {trace.counters.generated_update_count}")
    print(f"  Commits: {trace.counters.commit_count}")
    print(f"\nSample labels: {[s['label'] for s in sample_info]}")


if __name__ == "__main__":
    main()
