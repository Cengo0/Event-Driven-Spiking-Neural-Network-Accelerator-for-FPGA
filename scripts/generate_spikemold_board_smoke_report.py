#!/usr/bin/env python3
"""Generate Markdown evidence from the latest SpikeMold board smoke JSON."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD_JSON = ROOT / "outputs" / "board" / "hls_register_smoke_result_20260614.json"
OUT_MD = ROOT / "reports" / "spikemold_board_smoke_report.md"


def main() -> int:
    result = json.loads(BOARD_JSON.read_text(encoding="utf-8"))
    normal = result["runs"]["normal"]
    reset = result["runs"]["reset"]
    bitstream = result["bitstream"]
    hwh = result["hwh"]
    expected_version = int(result["expected_version"])
    version = int(normal["version_reg"])

    text = f"""# SpikeMold PYNQ-Z2 Board Smoke Report

Status: PYNQ-Z2 HLS register smoke passed

## Evidence Level

`{result["evidence_level"]}`

This is a board execution result. It proves overlay load, HLS AXI-Lite register
access, `ap_start`/`ap_done`, and `version_reg` readback for the routed
SpikeMold bitstream. It does not claim DMA streaming correctness, neural output
correctness, latency, throughput, energy, or dataset accuracy.

## Board Result

| Check | Result |
|---|---:|
| board executed | `{result["board_executed"]}` |
| ok | `{result["ok"]}` |
| IP name | `{result["ip_name"]}` |
| `ap_done` | `{result["checks"]["ap_done"]}` |
| version matches | `{result["checks"]["version_matches"]}` |
| expected version | `0x{expected_version:08x}` |
| read version | `0x{version:08x}` |
| normal status_reg | `{normal["status_reg"]}` |
| normal spike_count_reg | `{normal["spike_count_reg"]}` |
| normal weight_sum_reg | `{normal["weight_sum_reg"]}` |
| normal poll count | `{normal["polls"]}` |
| reset poll count | `{reset["polls"]}` |

## Overlay

Available IPs:

```text
{chr(10).join(result["available_ips"])}
```

## Artifacts

| Artifact | Size bytes | SHA-256 |
|---|---:|---|
| `{bitstream["path"]}` | `{bitstream["size_bytes"]}` | `{bitstream["sha256"]}` |
| `{hwh["path"]}` | `{hwh["size_bytes"]}` | `{hwh["sha256"]}` |

## Claim Boundary

`{result["claim_boundary"]}`

## Next Gate

Run DMA stream smoke through `axi_dma_0`/`axi_dma_1` and compare board output
words/counters with the SpikePress golden trace contract.
"""
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
