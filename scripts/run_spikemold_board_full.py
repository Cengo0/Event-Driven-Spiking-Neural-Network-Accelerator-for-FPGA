#!/usr/bin/env python3
"""Run SpikeMold full board execution with artifact model and equivalence verification.

Usage:
    python run_spikemold_board_full.py \\
        --artifact outputs/artifacts/trained_mnist.json \\
        --input golden_traces/v1/mnist_fclif_784_512_10_v1.json \\
        --bitstream /home/xilinx/projects/spikemold.bit \\
        --output outputs/board/full_run_result.json

Board execution requires:
    - PYNQ-Z2 board at 192.168.0.54
    - SpikeMold bitstream loaded
    - pynq package installed on board

Output includes:
    - Full board execution result with counters
    - Equivalence verification against golden trace
"""

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run SpikeMold full board execution"
    )
    parser.add_argument(
        "--artifact",
        type=str,
        required=True,
        help="Path to SpikeMold artifact JSON file",
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to input spikes (golden trace or events JSON)",
    )
    parser.add_argument(
        "--bitstream",
        type=str,
        default="/home/xilinx/projects/spikemold.bit",
        help="Path to bitstream on PYNQ-Z2",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/board/full_run_result.json",
        help="Output path for results",
    )
    parser.add_argument(
        "--ip-name",
        type=str,
        default="spikemold_ctrl_0",
        help="Name of SpikeMold IP in overlay",
    )
    parser.add_argument(
        "--output-cap",
        type=int,
        default=1024,
        help="Output buffer capacity in words",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=100000,
        help="Timeout polls for job completion",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    return parser.parse_args()


def load_input_spikes(path: Path) -> list:
    """Load input spikes from JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))

    # Handle golden trace format
    if "schema" in data and "inputs" in data:
        inputs = data.get("inputs", [])
        return [
            {
                "src_id": inp["src_id"],
                "tick": inp["tick"],
                "payload": inp["payload"],
                "x": inp.get("x"),
                "y": inp.get("y"),
                "channel": inp.get("channel"),
            }
            for inp in inputs
        ]

    # Handle direct events format
    if isinstance(data, list):
        return data

    raise ValueError(f"Unknown input format: {path}")


def main() -> int:
    """Main entry point."""
    args = parse_args()

    artifact_path = Path(args.artifact)
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not artifact_path.exists():
        print(f"Error: Artifact not found: {artifact_path}", file=sys.stderr)
        return 1

    if not input_path.exists():
        print(f"Error: Input not found: {input_path}", file=sys.stderr)
        return 1

    # Import after argument parsing (allows running without PYNQ for testing)
    try:
        from spikepress.full_board_run import (
            EquivalenceResult,
            SpikeMoldBoardConfig,
            SpikeMoldFullBoardResult,
            load_artifact,
            read_golden_trace,
            run_full_board_verification,
        )
        from spikepress.transport import pack_input_spikes
    except ImportError as e:
        print(f"Error: Failed to import spikepress: {e}", file=sys.stderr)
        return 1

    # Load inputs
    artifact = load_artifact(artifact_path)
    input_spikes = load_input_spikes(input_path)

    if args.verbose:
        print(f"Loaded artifact: {artifact.manifest.get('artifact_id', 'unknown')}")
        print(f"Input spikes: {len(input_spikes)}")

    # Pack spikes for board execution
    packed_spikes = pack_input_spikes(input_spikes)

    # Create config
    config = SpikeMoldBoardConfig(
        bitstream_path=args.bitstream,
        ip_name=args.ip_name,
        output_cap_words=args.output_cap,
        timeout_polls=args.timeout,
        verbose=args.verbose,
    )

    if args.verbose:
        print(f"Running on board: {args.bitstream}")

    # Run full verification
    try:
        board_result, equivalence = run_full_board_verification(
            artifact_path=artifact_path,
            input_spikes=input_spikes,
            golden_trace_path=input_path,
            config=config,
        )

        if args.verbose:
            print(f"\nBoard Result:")
            print(f"  OK: {board_result.ok}")
            print(f"  Output words: {board_result.output_word_count}")
            print(f"  Counters: cycle={board_result.cycle_count}, "
                  f"input={board_result.input_event_count}, "
                  f"update={board_result.update_count}, "
                  f"active={board_result.active_count}")
            print(f"\nEquivalence Verification:")
            print(f"  Verified: {equivalence.verified}")
            print(f"  Readout match: {equivalence.readout_match}")
            print(f"  Commit values match: {equivalence.commit_values_match}")
            print(f"  State checksum match: {equivalence.state_checksum_match}")

        # Write results
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result = {
            "schema": "spikemold.full_board_verification_result.v1",
            "board_result": board_result.to_dict(),
            "equivalence": equivalence.to_dict(),
        }

        output_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8"
        )

        if args.verbose:
            print(f"\nResults written to: {output_path}")

        return 0 if equivalence.verified else 1

    except Exception as e:
        print(f"Error during board execution: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
