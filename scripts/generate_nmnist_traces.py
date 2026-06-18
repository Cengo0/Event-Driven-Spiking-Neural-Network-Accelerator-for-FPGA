"""Generate N-MNIST EventConvSNN traces from DVS128 binary files."""

import os
import struct
from pathlib import Path
from typing import List, Tuple

from spikepress.architecture_trace_generator import (
    InputSpike,
    generate_eventconv_active_readout_trace,
)


def read_nmnist_bin(bin_path: str) -> List[Tuple[int, int, int, int]]:
    """Read N-MNIST binary file and return list of (x, y, polarity, timestamp).

    Format: 40-bit events packed as 5 bytes per event:
        - byte 0: X address (8 bits)
        - byte 1: Y address (8 bits)
        - byte 2: Polarity (1 bit) + reserved (7 bits)
        - bytes 3-4: Timestamp lower 16 bits
        - bytes 5-6: Timestamp upper 7 bits (in third byte)

    Actually from the readme:
        bit 39-32: X address (8 bits)
        bit 31-24: Y address (8 bits)
        bit 23: Polarity (0=OFF, 1=ON)
        bit 22-0: Timestamp (23 bits)
    """
    events = []

    with open(bin_path, "rb") as f:
        while True:
            # Read 5 bytes for each 40-bit event
            data = f.read(5)
            if len(data) < 5:
                break

            x = data[0]
            y = data[1]

            # Polarity is bit 23 (MSB of byte 2)
            polarity = (data[2] >> 7) & 1
            ts_low = (data[2] & 0x7F) << 16  # Lower 7 bits
            ts_mid = data[3] << 8             # Middle 8 bits
            ts_high = data[4]                 # Upper 8 bits
            timestamp = ts_low | ts_mid | ts_high

            events.append((x, y, polarity, timestamp))

    return events


def create_eventword64_from_nmnist_event(x: int, y: int, polarity: int,
                                         timestamp: int, idx: int) -> int:
    """Convert N-MNIST event to SpikeMold EventWord64 format."""
    # SpikeMold EventWord64 format:
    # bit 63-60: event_type (4 bits)
    # bit 59-48: tick (12 bits)
    # bit 47-38: src_y_or_hi (10 bits)
    # bit 37-28: src_x_or_lo (10 bits)
    # bit 27-20: channel_or_dst_hi (8 bits)
    # bit 19: sign (1 bit)
    # bit 18-11: weight_abs (8 bits)
    # bit 10-5: flags (6 bits)
    # bit 4-0: target (5 bits)

    event_type = 0x1  # Spike event
    word = 0
    word |= (event_type & 0xF) << 60
    word |= (timestamp & 0xFFF) << 48
    word |= ((y >> 4) & 0x3FF) << 38      # High bits of y
    word |= ((x >> 4) & 0x3FF) << 28      # High bits of x
    word |= ((polarity >> 6) & 0xFF) << 20  # Polarity info
    word |= polarity << 19                # Sign bit
    word |= (idx & 0x3F) << 5             # Flags
    word |= (timestamp & 0x1F)            # Tick low bits

    return word


def generate_nmnist_eventconv_trace(sample_idx: int = 0,
                                    max_events: int = 5000,
                                    threshold: int = 3) -> str:
    """Generate EventConv trace for one N-MNIST sample.

    Args:
        sample_idx: Index of sample to use (0-9999 for Train)
        max_events: Maximum number of events to process
        threshold: Readout threshold

    Returns:
        Trace file path
    """
    nmnist_dir = Path("data/nmnist")
    train_dir = nmnist_dir / "Train"

    # Get first sample file from digit 0
    digit_dirs = sorted(train_dir.glob("*"))
    if not digit_dirs:
        raise ValueError(f"No digit directories found in {train_dir}")

    # Use digit 0 for first sample
    sample_file = sorted(digit_dirs[0].glob("*.bin"))[sample_idx % 10]

    print(f"Reading: {sample_file}")

    events = read_nmnist_bin(str(sample_file))
    print(f"Total events: {len(events)}")

    # Limit events for reasonable trace size
    events = events[:max_events]

    # Create input spikes (convert DVS128 to 28x28 for MNIST-like processing)
    input_spikes = []
    scale_factor = 128 / 28  # Scale from 128x128 to 28x28

    for idx, (x, y, polarity, timestamp) in enumerate(events):
        scaled_x = int(x / scale_factor)
        scaled_y = int(y / scale_factor)

        if 0 <= scaled_x < 28 and 0 <= scaled_y < 28:
            input_spikes.append(InputSpike(
                tick=idx,
                src_id=idx,
                y=scaled_y,
                x=scaled_x,
                channel=0,
                payload=polarity + 1  # ON=2, OFF=1
            ))

    print(f"Filtered spikes: {len(input_spikes)}")

    # 3x3 edge detection kernel (Sobel-like)
    kernel = [[[
        [-1, 0, 1],
        [-2, 0, 2],
        [-1, 0, 1],
    ]]]

    trace = generate_eventconv_active_readout_trace(
        input_spikes=input_spikes,
        kernel=kernel,
        input_shape=(1, 28, 28),
        stride=1,
        padding=1,
        commit_thresholds=None,  # No threshold - all activations
        trace_id=f"nmnist_eventconv_28x28_sample_{sample_idx}_v1",
    )

    return trace


def read_nmnist_bin(bin_path: str) -> List[Tuple[int, int, int, int]]:
    """Read N-MNIST binary file and return list of (x, y, polarity, timestamp)."""
    events = []

    with open(bin_path, "rb") as f:
        while True:
            data = f.read(5)
            if len(data) < 5:
                break

            x = data[0]
            y = data[1]

            # Polarity is bit 23 (MSB of byte 2)
            polarity = (data[2] >> 7) & 1
            ts_low = (data[2] & 0x7F) << 16
            ts_mid = data[3] << 8
            ts_high = data[4]
            timestamp = ts_low | ts_mid | ts_high

            events.append((x, y, polarity, timestamp))

    return events


def main():
    """Generate N-MNIST EventConv traces."""
    output_dir = Path("golden_traces/v1")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating N-MNIST EventConv traces...")
    print(f"N-MNIST directory: data/nmnist")

    # Check if Train.zip is extracted
    train_zip = Path("data/nmnist/Train.zip")
    if not train_zip.exists():
        print(f"ERROR: {train_zip} not found!")
        print("Please extract Train.zip first.")
        return

    # Extract Train.zip if needed
    train_dir = Path("data/nmnist/Train")
    if not train_dir.exists():
        import zipfile
        with zipfile.ZipFile(train_zip, "r") as zip_ref:
            zip_ref.extractall("data/nmnist/")
        print("Extracted Train.zip")

    # Generate traces for first 3 samples
    for sample_idx in range(3):
        try:
            trace = generate_nmnist_eventconv_trace(sample_idx=sample_idx)

            output_path = output_dir / f"nmnist_eventconv_sample_{sample_idx}_v1.json"
            trace.write_json(output_path)

            print(f"\nGenerated: {output_path}")
            print(f"  Input spikes: {trace.counters.input_event_count}")
            print(f"  Updates: {trace.counters.generated_update_count}")
            print(f"  Commits: {trace.counters.commit_count}")
        except Exception as e:
            print(f"Error processing sample {sample_idx}: {e}")


if __name__ == "__main__":
    main()
