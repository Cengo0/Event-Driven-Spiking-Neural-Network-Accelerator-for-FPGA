#!/usr/bin/env python3
"""Check SpikeMold HLS/Vivado build evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = ROOT / "outputs" / "resource" / "spikemold_build_evidence_report.json"
REPORT_MD = ROOT / "reports" / "spikemold_build_evidence_report.md"
SCHEMA = "spikemold.hls_vivado_build_evidence.v1"
CLAIM_BOUNDARY = "hls_csim_hls_synth_vivado_routed_bitstream_only_no_board_execution"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        fail(f"cannot load JSON {path}: {exc}")


def check_hash(payload: dict) -> None:
    body = dict(payload)
    hashes = dict(body.pop("hashes", {}))
    if hashes.get("build_evidence_sha256") != sha256_json(body):
        fail("build_evidence_sha256 mismatch")


def require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        fail(f"{name} must be a mapping")
    return value


def check_artifact(item: Mapping[str, object], name: str) -> None:
    rel = item.get("path")
    expected_hash = item.get("sha256")
    size = item.get("size_bytes")
    if not rel or not expected_hash or not isinstance(size, int):
        fail(f"{name} artifact metadata malformed")
    path = ROOT / str(rel)
    if not path.exists():
        fail(f"{name} missing artifact: {rel}")
    if path.stat().st_size != size:
        fail(f"{name} size mismatch")
    if sha256_file(path) != expected_hash:
        fail(f"{name} sha256 mismatch")


def main() -> int:
    if not REPORT_JSON.exists():
        fail(f"missing JSON report: {REPORT_JSON}")
    if not REPORT_MD.exists():
        fail(f"missing Markdown report: {REPORT_MD}")

    report = load_json(REPORT_JSON)
    if report.get("schema") != SCHEMA:
        fail("schema mismatch")
    if report.get("evidence_level") != "hls_csim_hls_synth_vivado_routed_no_board":
        fail("evidence level mismatch")
    if report.get("board_executed") is not False:
        fail("must not claim board execution")
    if report.get("claim_boundary") != CLAIM_BOUNDARY:
        fail("claim boundary mismatch")
    hls_csim = require_mapping(report.get("hls_csim"), "hls_csim")
    hls_synthesis = require_mapping(report.get("hls_synthesis"), "hls_synthesis")
    hls_csynth = require_mapping(report.get("hls_csynth"), "hls_csynth")
    routed = require_mapping(report.get("vivado_routed"), "vivado_routed")
    artifacts = require_mapping(report.get("artifacts"), "artifacts")
    target = require_mapping(report.get("target"), "target")

    if hls_csim.get("passed") is not True:
        fail("HLS C-sim did not pass")
    if hls_synthesis.get("passed") is not True:
        fail("HLS synthesis did not pass")
    if hls_csynth.get("top_model") != "spikemold_top_hls":
        fail("HLS top model mismatch")
    if float(hls_csynth.get("target_clock_period_ns", 999.0)) != 12.5:
        fail("HLS target clock must be 12.5 ns")
    if hls_csynth.get("timing_estimate_meets_target") is not True:
        fail("HLS timing estimate must meet target")
    resources = require_mapping(hls_csynth.get("resources"), "hls resources")
    available = require_mapping(hls_csynth.get("available_resources"), "hls available resources")
    if resources.get("dsp") != 0:
        fail("HLS DSP usage must be zero")
    if int(resources.get("bram_18k", 999999)) > int(available.get("bram_18k", -1)):
        fail("HLS BRAM estimate exceeds available")
    encoder_loop_ii = require_mapping(hls_csynth.get("encoder_loop_ii"), "encoder_loop_ii")
    if encoder_loop_ii.get("final_ii") != 2:
        fail("expected current ENCODER_LOOP final II of 2")
    if encoder_loop_ii.get("accepted_as_known_limitation") is not True:
        fail("ENCODER_LOOP II limitation must be explicit")

    for key in ["csynth_xml", "csynth_report"]:
        check_artifact(require_mapping(hls_csynth.get(key), key), key)
    for key in ["hls_ip_component_xml", "hls_kernel_zip", "bitstream", "hwh"]:
        check_artifact(require_mapping(artifacts.get(key), key), key)

    timing = require_mapping(routed.get("timing"), "routed timing")
    utilization = require_mapping(routed.get("utilization"), "routed utilization")
    power = require_mapping(routed.get("power_estimate"), "routed power estimate")
    if routed.get("bitstream_and_hwh_present") is not True:
        fail("bitstream and HWH must be present")
    if float(target.get("routed_clock_mhz", 0.0)) != 20.0:
        fail("routed target clock must be 20 MHz")
    timing_fields_ok = (
        float(timing.get("wns_ns", -999.0)) >= 0.0
        and timing.get("tns_failing_endpoints") == 0
        and timing.get("ths_failing_endpoints") == 0
        and timing.get("tpws_failing_endpoints") == 0
        and timing.get("report_says_timing_met") is True
    )
    if routed.get("all_timing_met") is not timing_fields_ok:
        fail("routed all_timing_met must match timing report fields")
    expected_all_ok = (
        hls_csim.get("passed") is True
        and hls_synthesis.get("passed") is True
        and hls_csynth.get("timing_estimate_meets_target") is True
        and timing_fields_ok
        and routed.get("bitstream_and_hwh_present") is True
    )
    if report.get("all_ok") is not expected_all_ok:
        fail("all_ok must reflect strict HLS plus routed timing status")
    expected_functional_artifact_ok = (
        hls_csim.get("passed") is True
        and hls_synthesis.get("passed") is True
        and hls_csynth.get("timing_estimate_meets_target") is True
        and routed.get("bitstream_and_hwh_present") is True
    )
    if report.get("functional_artifact_ok") is not expected_functional_artifact_ok:
        fail("functional_artifact_ok mismatch")
    if timing.get("ths_failing_endpoints") != 0:
        fail("routed THS failing endpoints must be zero")
    if timing.get("tpws_failing_endpoints") != 0:
        fail("routed TPWS failing endpoints must be zero")
    if not timing_fields_ok:
        limitations = report.get("known_limitations", [])
        if not any("timing is not met" in str(item) for item in limitations):
            fail("timing miss must be explicit in known_limitations")
    if str(timing.get("design_state")).lower() != "routed":
        fail("timing design state must be routed")
    check_artifact(require_mapping(timing.get("report"), "timing report"), "timing report")
    check_artifact(require_mapping(utilization.get("report"), "utilization report"), "utilization report")
    check_artifact(require_mapping(power.get("report"), "power report"), "power report")

    for row_name in ["slice_luts", "slice_registers", "block_ram_tile", "dsp"]:
        row = require_mapping(utilization.get(row_name), row_name)
        if int(row.get("used", 999999)) > int(row.get("available", -1)):
            fail(f"{row_name} exceeds available")
    if int(require_mapping(utilization.get("block_ram_tile"), "block_ram_tile").get("used", 0)) != 99:
        fail("current routed BRAM tile count changed; regenerate/review evidence")
    if int(require_mapping(utilization.get("dsp"), "dsp").get("used", 0)) != 4:
        fail("current routed DSP count changed; regenerate/review evidence")
    if power.get("confidence_level") != "Medium":
        fail("power confidence level changed; regenerate/review evidence")
    if power.get("is_vectorless_estimate") is not True:
        fail("power report should remain marked vectorless estimate")
    check_hash(report)

    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in [
        "HLS C-sim, HLS synthesis/IP package, and integrated Vivado route timing passed",
        "No board execution was run",
        "Vivado Routed Results",
        "functional board smoke",
        CLAIM_BOUNDARY,
    ]:
        if phrase not in text:
            fail(f"Markdown report missing phrase: {phrase}")

    print("PASS: SpikeMold HLS/Vivado build evidence valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
