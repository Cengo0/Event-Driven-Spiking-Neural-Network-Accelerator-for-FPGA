#!/usr/bin/env python3
"""Run one SpikeMold job on PYNQ-Z2 using register-map V1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from spikepress.pynq_runtime import SpikeMoldPynqRunConfig, run_spikemold_pynq_one_shot  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bitstream", required=True, help="Path to .bit on the PYNQ board")
    parser.add_argument("--ip-name", default="spikemold_ctrl_0", help="Overlay IP attribute name")
    parser.add_argument("--input-json", required=True, help="JSON file containing a list of EventWord64 integers")
    parser.add_argument("--output-json", required=True, help="Where to write run result JSON")
    parser.add_argument("--output-cap-words", type=int, default=1024)
    parser.add_argument("--timeout-polls", type=int, default=100000)
    parser.add_argument("--irq-enable", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input_json)
    output_path = Path(args.output_json)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise SystemExit("input JSON must be a list of EventWord64 integers")

    result = run_spikemold_pynq_one_shot(
        payload,
        SpikeMoldPynqRunConfig(
            bitstream_path=args.bitstream,
            ip_name=args.ip_name,
            output_cap_words=args.output_cap_words,
            timeout_polls=args.timeout_polls,
            irq_enable=args.irq_enable,
        ),
    )
    result.write_json(output_path)
    print(f"Wrote {output_path}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
