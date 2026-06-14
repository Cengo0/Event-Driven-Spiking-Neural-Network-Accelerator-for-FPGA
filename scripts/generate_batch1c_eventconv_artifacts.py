#!/usr/bin/env python3
"""Generate Batch 1C EventConv C0 trace artifact."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from spikepress.architecture_trace_generator import InputSpike, generate_eventconv_trace  # noqa: E402


def main() -> int:
    golden_dir = ROOT / "golden_traces" / "v1"
    golden_dir.mkdir(parents=True, exist_ok=True)

    trace = generate_eventconv_trace(
        input_spikes=[InputSpike(tick=0, src_id=0, y=1, x=1, channel=0)],
        kernel=[[[[1, 2], [3, 4]]]],
        input_shape=(1, 3, 3),
        stride=1,
        padding=0,
        thresholds={},
        trace_id="eventconv_agu_c0_tiny_v1",
    )
    trace.write_json(golden_dir / "eventconv_agu_c0_tiny_v1.json")
    print("Wrote golden_traces/v1/eventconv_agu_c0_tiny_v1.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
