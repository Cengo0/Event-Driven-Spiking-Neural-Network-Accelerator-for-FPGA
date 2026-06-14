#!/usr/bin/env python3
"""Check SpikeMold PYNQ-Z2 board smoke evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
BOARD_JSON = ROOT / "outputs" / "board" / "hls_register_smoke_result_20260614.json"
REPORT_MD = ROOT / "reports" / "spikemold_board_smoke_report.md"
SCHEMA = "spikemold.pynq_hls_register_smoke.v1"
CLAIM_BOUNDARY = "pynq_overlay_load_hls_register_ap_done_version_only_no_dma_no_dataset"
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
        fail(f"missing board report: {REPORT_MD}")

    result = load_json(BOARD_JSON)
    if result.get("schema") != SCHEMA:
        fail("schema mismatch")
    if result.get("evidence_level") != "pynq_board_hls_register_smoke":
        fail("evidence level mismatch")
    if result.get("board_executed") is not True:
        fail("board_executed must be true")
    if result.get("ok") is not True:
        fail("board smoke ok must be true")
    if result.get("claim_boundary") != CLAIM_BOUNDARY:
        fail("claim boundary mismatch")
    if result.get("ip_name") != "spikemold_top_hls_0":
        fail("IP name mismatch")
    if "spikemold_top_hls_0" not in result.get("available_ips", []):
        fail("HLS IP missing from board overlay")
    if "axi_dma_0" not in result.get("available_ips", []):
        fail("axi_dma_0 missing from board overlay")
    if "axi_dma_1" not in result.get("available_ips", []):
        fail("axi_dma_1 missing from board overlay")

    checks = require_mapping(result.get("checks"), "checks")
    if checks.get("ap_done") is not True:
        fail("ap_done check failed")
    if checks.get("version_matches") is not True:
        fail("version check failed")
    if int(result.get("expected_version", 0)) != EXPECTED_VERSION:
        fail("expected version mismatch")

    runs = require_mapping(result.get("runs"), "runs")
    normal = require_mapping(runs.get("normal"), "normal run")
    reset = require_mapping(runs.get("reset"), "reset run")
    if int(normal.get("version_reg", 0)) != EXPECTED_VERSION:
        fail("normal run version mismatch")
    if int(normal.get("ap_ctrl", 0)) & 0x2 == 0:
        fail("normal run did not set ap_done")
    if int(reset.get("ap_ctrl", 0)) & 0x2 == 0:
        fail("reset run did not set ap_done")
    if int(normal.get("spike_count_reg", -1)) != 0:
        fail("normal run spike_count_reg must be zero for no-input smoke")
    if int(normal.get("weight_sum_reg", -1)) != 0:
        fail("normal run weight_sum_reg must be zero for reset/no-weight smoke")

    bitstream = require_mapping(result.get("bitstream"), "bitstream")
    hwh = require_mapping(result.get("hwh"), "hwh")
    if bitstream.get("sha256") != BIT_SHA256:
        fail("bitstream sha256 mismatch")
    if hwh.get("sha256") != HWH_SHA256:
        fail("HWH sha256 mismatch")
    if int(bitstream.get("size_bytes", 0)) <= 0:
        fail("bitstream size missing")
    if int(hwh.get("size_bytes", 0)) <= 0:
        fail("HWH size missing")

    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in [
        "PYNQ-Z2 HLS register smoke passed",
        "This is a board execution result",
        "does not claim DMA streaming correctness",
        CLAIM_BOUNDARY,
    ]:
        if phrase not in text:
            fail(f"report missing phrase: {phrase}")

    print("PASS: SpikeMold PYNQ-Z2 board smoke evidence valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
