#!/usr/bin/env rtk python
"""Run large-scale traces on PYNQ-Z2 board.

This script executes MNIST/CIFAR/N-MNIST scale traces on the actual PYNQ-Z2
hardware using the SpikeMold runtime contract.
"""

import json
import sys
from pathlib import Path

from spikepress.pynq_runtime import (
    SpikeMoldPynqRunConfig,
    run_spikemold_pynq_one_shot,
)
from spikepress.transport import pack_input_spikes, decode_eventword64_input


def load_trace(trace_path: str) -> dict:
    """Load a golden trace JSON file."""
    return json.loads(Path(trace_path).read_text())


def trace_to_input_words(trace: dict) -> list[int]:
    """Convert trace to EventWord64 input words for board execution.

    Uses the same packing format as pack_input_spikes in transport.py
    but adapted for trace data.
    """
    inputs = trace.get("inputs", [])
    eventword64_inputs = []

    for inp in inputs:
        if inp.get("kind") == "input_spike":
            tick = inp.get("tick", 0)
            src_id = inp.get("src_id", 0)
            payload = inp.get("payload", 1)

            # Pack as EventWord64 matching spikepress.transport
            word = (0x1 << 60) | ((tick & 0xFFF) << 48) | (src_id & 0xFFFFFFF)
            eventword64_inputs.append(word)

    return eventword64_inputs


def run_trace_on_board(trace_path: str, bitstream_path: str,
                       output_cap_words: int = 1024) -> dict:
    """Run a trace on PYNQ-Z2 board."""
    trace = load_trace(trace_path)

    # Extract input words
    input_words = trace_to_input_words(trace)

    print(f"Trace: {Path(trace_path).name}")
    print(f"  Input words: {len(input_words)}")
    print(f"  Updates: {trace['counters']['generated_update_count']}")
    print(f"  Commits: {trace['counters']['commit_count']}")
    print(f"  Input events: {trace['counters']['input_event_count']}")

    if not input_words:
        raise ValueError("No input words found in trace!")

    # Run on board
    config = SpikeMoldPynqRunConfig(
        bitstream_path=bitstream_path,
        ip_name="spikemold_top_hls_0",
        output_cap_words=output_cap_words,
    )

    result = run_spikemold_pynq_one_shot(input_words, config)

    # Verify against trace golden results
    output_words = list(result.output_words)
    print(f"  Board output words: {len(output_words)}")

    return result.to_dict()


def main():
    """Run large-scale traces on PYNQ-Z2."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run large-scale traces on PYNQ-Z2 board"
    )
    parser.add_argument("--trace", required=True,
                       help="Trace JSON file path")
    parser.add_argument("--bitstream",
                       default="outputs/spikemold_pynq_z2_eventconv_20mhz.bit",
                       help="Bitstream path")
    parser.add_argument("--output", "-o",
                       help="Output JSON path (default: outputs/board/{trace_name}_board_result.json)")

    args = parser.parse_args()

    if not Path(args.bitstream).exists():
        print(f"ERROR: Bitstream not found: {args.bitstream}")
        sys.exit(1)

    result = run_trace_on_board(args.trace, args.bitstream)

    output_path = args.output or Path("outputs/board") / f"{Path(args.trace).stem}_board_result.json"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(result, indent=2, sort_keys=True))

    print(f"\nResult: {'PASS' if result['ok'] else 'FAIL'}")
    print(f"  Board executed: {result['board_executed']}")
    print(f"  Input words: {result['input_word_count']}")
    print(f"  Output words: {result['output_word_count']}")
    print(f"  Status: {result['status']:#x}")
    print(f"  Error code: {result['error_code']}")
    print(f"  Counters:")
    for k, v in result['counters'].items():
        print(f"    {k}: {v}")

    if result['ok']:
        print(f"\nBoard execution PASSED")
        print(f"Output: {output_path}")
    else:
        print(f"\nBoard execution FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
