#!/usr/bin/env python3
"""Check SpikeMold PYNQ-Z2 DMA weight smoke evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
BOARD_JSON = ROOT / "outputs" / "board" / "dma_weight_smoke_result_20260614.json"
REPORT_MD = ROOT / "reports" / "spikemold_dma_weight_smoke_report.md"
SCHEMA = "spikemold.pynq_dma_weight_smoke.v1"
CLAIM_BOUNDARY = "pynq_axi_dma1_weight_load_checkpoint_readback_only_no_neural_dataset"
EXPECTED_VERSION = 0x20260221
BIT_SHA256 = "034f62803060e81e37a98f459c8433a358183e4485b84ba12d8585016b3eb418"
HWH_SHA256 = "033a777f37c04e09fb36772ae62c05922a67c43d35a736a80c66a1b63ac8cad1"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        fail(f"{name} must be a mapping")
    return value


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        fail(f"cannot load JSON {path}: {exc}")


def main() -> int:
    if not BOARD_JSON.exists():
        fail(f"missing board JSON: {BOARD_JSON}")
    if not REPORT_MD.exists():
        fail(f"missing report: {REPORT_MD}")

    result = load_json(BOARD_JSON)
    if result.get("schema") != SCHEMA:
        fail("schema mismatch")
    if result.get("evidence_level") != "pynq_board_dma_weight_stream_smoke":
        fail("evidence level mismatch")
    if result.get("board_executed") is not True:
        fail("board_executed must be true")
    if result.get("ok") is not True:
        fail("DMA weight smoke ok must be true")
    if result.get("claim_boundary") != CLAIM_BOUNDARY:
        fail("claim boundary mismatch")
    if result.get("ip_name") != "spikemold_top_hls_0":
        fail("IP name mismatch")
    if result.get("dma_name") != "axi_dma_1":
        fail("DMA name mismatch")
    for ip_name in ["spikemold_top_hls_0", "axi_dma_1"]:
        if ip_name not in result.get("available_ips", []):
            fail(f"overlay missing {ip_name}")

    checks = require_mapping(result.get("checks"), "checks")
    for key in [
        "reset_ap_done",
        "load_ap_done",
        "checkpoint_ap_done",
        "version_matches",
        "first_checkpoint_index_zero",
        "first_checkpoint_weight_matches",
        "checkpoint_last_word_count",
    ]:
        if checks.get(key) is not True:
            fail(f"check failed: {key}")

    weight_load = require_mapping(result.get("weight_load"), "weight_load")
    if weight_load.get("pre_id") != 512:
        fail("pre_id must match generated SpikePress connection")
    if weight_load.get("post_id") != 0:
        fail("post_id must match generated SpikePress connection")
    if weight_load.get("weight") != 7:
        fail("weight mismatch")

    checkpoint = require_mapping(result.get("checkpoint"), "checkpoint")
    output_words = checkpoint.get("output_words", [])
    if not isinstance(output_words, list) or len(output_words) != 4:
        fail("checkpoint output word count mismatch")
    if int(output_words[0]) != int(checkpoint.get("expected_first_word", -1)):
        fail("first checkpoint word mismatch")
    if checkpoint.get("decoded_first_weight") != 7:
        fail("decoded first weight mismatch")

    runs = require_mapping(result.get("runs"), "runs")
    checkpoint_run = require_mapping(runs.get("checkpoint"), "checkpoint run")
    if int(checkpoint_run.get("version_reg", 0)) != EXPECTED_VERSION:
        fail("checkpoint version mismatch")
    if int(checkpoint_run.get("weight_sum_reg", -1)) != 7:
        fail("checkpoint weight_sum_reg mismatch")

    bitstream = require_mapping(result.get("bitstream"), "bitstream")
    hwh = require_mapping(result.get("hwh"), "hwh")
    if bitstream.get("sha256") != BIT_SHA256:
        fail("bitstream sha256 mismatch")
    if hwh.get("sha256") != HWH_SHA256:
        fail("HWH sha256 mismatch")

    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in [
        "PYNQ-Z2 AXI DMA weight stream smoke passed",
        "This is a board execution result",
        "not claim spike input/output correctness",
        CLAIM_BOUNDARY,
    ]:
        if phrase not in text:
            fail(f"report missing phrase: {phrase}")

    print("PASS: SpikeMold PYNQ-Z2 DMA weight smoke evidence valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
