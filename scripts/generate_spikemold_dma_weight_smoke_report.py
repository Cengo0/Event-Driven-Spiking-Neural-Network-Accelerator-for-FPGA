#!/usr/bin/env python3
"""Generate Markdown evidence from SpikeMold DMA weight smoke JSON."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOARD_JSON = ROOT / "outputs" / "board" / "dma_weight_smoke_result_20260614.json"
OUT_MD = ROOT / "reports" / "spikemold_dma_weight_smoke_report.md"


def main() -> int:
    result = json.loads(BOARD_JSON.read_text(encoding="utf-8"))
    bitstream = result["bitstream"]
    hwh = result["hwh"]
    weight_load = result["weight_load"]
    checkpoint = result["checkpoint"]
    runs = result["runs"]

    text = f"""# SpikeMold PYNQ-Z2 DMA Weight Smoke Report

Status: PYNQ-Z2 AXI DMA weight stream smoke passed

## Evidence Level

`{result["evidence_level"]}`

This is a board execution result. It proves `axi_dma_1` MM2S weight-load stream,
HLS weight-memory write, `axi_dma_1` S2MM checkpoint readback stream, TLAST
completion, and register readback for one valid SpikePress connection. It does
not claim spike input/output correctness, neural output correctness, latency,
throughput, energy, or dataset accuracy.

## Board Result

| Check | Result |
|---|---:|
| board executed | `{result["board_executed"]}` |
| ok | `{result["ok"]}` |
| IP name | `{result["ip_name"]}` |
| DMA name | `{result["dma_name"]}` |
| reset `ap_done` | `{result["checks"]["reset_ap_done"]}` |
| load `ap_done` | `{result["checks"]["load_ap_done"]}` |
| checkpoint `ap_done` | `{result["checks"]["checkpoint_ap_done"]}` |
| version matches | `{result["checks"]["version_matches"]}` |
| first checkpoint index zero | `{result["checks"]["first_checkpoint_index_zero"]}` |
| first checkpoint weight matches | `{result["checks"]["first_checkpoint_weight_matches"]}` |

## Weight Load

- pre_id: `{weight_load["pre_id"]}`
- post_id: `{weight_load["post_id"]}`
- weight: `{weight_load["weight"]}`
- packed input word: `{weight_load["input_word"]}`

## Checkpoint Readback

- requested words: `{checkpoint["requested_words"]}`
- output words: `{checkpoint["output_words"]}`
- expected first word: `{checkpoint["expected_first_word"]}`
- decoded first weight: `{checkpoint["decoded_first_weight"]}`
- output words sha256: `{checkpoint["output_words_sha256"]}`

Run counters/register readback:

- reset polls: `{runs["reset"]["polls"]}`
- load polls: `{runs["load"]["polls"]}`
- checkpoint polls: `{runs["checkpoint"]["polls"]}`
- checkpoint status_reg: `{runs["checkpoint"]["status_reg"]}`
- checkpoint weight_sum_reg: `{runs["checkpoint"]["weight_sum_reg"]}`

## Artifacts

| Artifact | Size bytes | SHA-256 |
|---|---:|---|
| `{bitstream["path"]}` | `{bitstream["size_bytes"]}` | `{bitstream["sha256"]}` |
| `{hwh["path"]}` | `{hwh["size_bytes"]}` | `{hwh["sha256"]}` |

## Claim Boundary

`{result["claim_boundary"]}`

## Next Gate

Run `axi_dma_0` spike-stream smoke and compare board spike/readout words with
the SpikePress golden trace contract.
"""
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
