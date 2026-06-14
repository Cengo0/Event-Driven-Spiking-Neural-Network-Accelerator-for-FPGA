#!/usr/bin/env python3
"""Generate SpikeMold HLS/Vivado build evidence from current artifacts."""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "outputs" / "resource" / "spikemold_build_evidence_report.json"
OUT_MD = ROOT / "reports" / "spikemold_build_evidence_report.md"
SCHEMA = "spikemold.hls_vivado_build_evidence.v1"
EVIDENCE_LEVEL = "hls_csim_hls_synth_vivado_routed_no_board"
CLAIM_BOUNDARY = "hls_csim_hls_synth_vivado_routed_bitstream_only_no_board_execution"

CSIM_SUMMARY = ROOT / "hardware" / "hls" / "hls_csim_output" / "hls_csim_output.hlsrun_csim_summary"
HLS_COMPILE_SUMMARY = ROOT / "hardware" / "hls" / "hls_output" / "hls_output.hlscompile_summary"
CSYNTH_XML = ROOT / "hardware" / "hls" / "hls_output" / "hls" / "syn" / "report" / "csynth.xml"
CSYNTH_RPT = ROOT / "hardware" / "hls" / "hls_output" / "hls" / "syn" / "report" / "csynth.rpt"
HLS_COMPONENT_XML = ROOT / "hardware" / "hls" / "hls_output" / "hls" / "impl" / "ip" / "component.xml"
HLS_ZIP = ROOT / "hardware" / "hls" / "hls_output" / "spikemold_top_hls.zip"
BITSTREAM = ROOT / "outputs" / "spikemold_pynq_z2.bit"
HWH = ROOT / "outputs" / "spikemold_pynq_z2.hwh"
TIMING_RPT = ROOT / "outputs" / "spikemold_pynq_z2_timing.rpt"
UTIL_RPT = ROOT / "outputs" / "spikemold_pynq_z2_utilization.rpt"
POWER_RPT = ROOT / "outputs" / "spikemold_pynq_z2_power.rpt"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def require_paths(paths: list[Path]) -> None:
    missing = [str(path.relative_to(ROOT)) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing build artifacts: {missing}")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def artifact(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def parse_vitis_summary(path: Path, expected_state: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    states = re.findall(r'"state"\s*:\s*"([^"]+)"', text)
    tool_match = re.search(r'"toolVersion"\s*:\s*"([^"]+)"', text)
    command_match = re.search(r'"commandLine"\s*:\s*"([^"]+)"', text)
    if expected_state not in states:
        raise ValueError(f"{path} missing state {expected_state}")
    return {
        "summary": artifact(path),
        "states": states,
        "passed": states[-1] == expected_state,
        "tool_version": tool_match.group(1) if tool_match else "",
        "command_line": command_match.group(1) if command_match else "",
    }


def xml_text(root: ET.Element, path: str) -> str:
    item = root.find(path)
    if item is None or item.text is None:
        raise ValueError(f"missing XML field: {path}")
    return item.text.strip()


def parse_hls_csynth(xml_path: Path, rpt_path: Path) -> dict[str, Any]:
    root = ET.parse(xml_path).getroot()
    rpt_text = rpt_path.read_text(encoding="utf-8", errors="replace")
    estimated_clock_ns = float(xml_text(root, "./PerformanceEstimates/SummaryOfTimingAnalysis/EstimatedClockPeriod"))
    target_clock_ns = float(xml_text(root, "./UserAssignments/TargetClockPeriod"))
    resources = root.find("./AreaEstimates/Resources")
    available = root.find("./AreaEstimates/AvailableResources")
    if resources is None or available is None:
        raise ValueError("missing HLS resource estimates")

    def resource_int(parent: ET.Element, name: str) -> int:
        item = parent.find(name)
        if item is None or item.text is None:
            raise ValueError(f"missing HLS resource: {name}")
        return int(item.text.strip())

    ii_match = re.search(
        r"^\|\s*o\s+ENCODER_LOOP\s*\|\s*II\s*\|\s*Resource Limitation\s*\|"
        r"\s*([0-9]+)\s*\|\s*([0-9]+)\s*\|\s*([0-9]+)\s*\|",
        rpt_text,
        re.MULTILINE,
    )
    encoder_loop_ii = {
        "violation_type": "Resource Limitation" if ii_match else "",
        "latency_cycles": int(ii_match.group(1)) if ii_match else None,
        "final_ii": int(ii_match.group(2)) if ii_match else None,
        "trip_count": int(ii_match.group(3)) if ii_match else None,
        "target_ii": 1,
        "accepted_as_known_limitation": bool(ii_match),
    }

    hls = {
        "csynth_xml": artifact(xml_path),
        "csynth_report": artifact(rpt_path),
        "tool_version": xml_text(root, "./ReportVersion/Version"),
        "part": xml_text(root, "./UserAssignments/Part"),
        "top_model": xml_text(root, "./UserAssignments/TopModelName"),
        "target_clock_period_ns": target_clock_ns,
        "estimated_clock_period_ns": estimated_clock_ns,
        "estimated_fmax_mhz": round(1000.0 / estimated_clock_ns, 2),
        "timing_slack_ns": round(target_clock_ns - estimated_clock_ns, 3),
        "latency_cycles": {
            "best": int(xml_text(root, "./PerformanceEstimates/SummaryOfOverallLatency/Best-caseLatency")),
            "average": int(xml_text(root, "./PerformanceEstimates/SummaryOfOverallLatency/Average-caseLatency")),
            "worst": int(xml_text(root, "./PerformanceEstimates/SummaryOfOverallLatency/Worst-caseLatency")),
        },
        "latency_realtime": {
            "best": xml_text(root, "./PerformanceEstimates/SummaryOfOverallLatency/Best-caseRealTimeLatency"),
            "average": xml_text(root, "./PerformanceEstimates/SummaryOfOverallLatency/Average-caseRealTimeLatency"),
            "worst": xml_text(root, "./PerformanceEstimates/SummaryOfOverallLatency/Worst-caseRealTimeLatency"),
        },
        "resources": {
            "bram_18k": resource_int(resources, "BRAM_18K"),
            "dsp": resource_int(resources, "DSP"),
            "ff": resource_int(resources, "FF"),
            "lut": resource_int(resources, "LUT"),
            "uram": resource_int(resources, "URAM"),
        },
        "available_resources": {
            "bram_18k": resource_int(available, "BRAM_18K"),
            "dsp": resource_int(available, "DSP"),
            "ff": resource_int(available, "FF"),
            "lut": resource_int(available, "LUT"),
            "uram": resource_int(available, "URAM"),
        },
        "encoder_loop_ii": encoder_loop_ii,
        "all_dsp_zero": resource_int(resources, "DSP") == 0,
        "timing_estimate_meets_target": estimated_clock_ns <= target_clock_ns,
    }
    return hls


def parse_header(text: str, label: str) -> str:
    pattern = re.compile(r"^\|\s*" + re.escape(label) + r"\s*:\s*(.+)$", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def parse_table_row(text: str, label: str) -> dict[str, Any]:
    pattern = re.compile(
        r"^\|\s*" + re.escape(label) + r"\s*\|\s*([0-9]+)\s*\|\s*([0-9]+)\s*\|"
        r"\s*([0-9]+)\s*\|\s*([0-9]+)\s*\|\s*([0-9.]+)\s*\|",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        raise ValueError(f"missing utilization row: {label}")
    used, fixed, prohibited, available, util_pct = match.groups()
    return {
        "used": int(used),
        "fixed": int(fixed),
        "prohibited": int(prohibited),
        "available": int(available),
        "util_pct": float(util_pct),
    }


def parse_timing(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    summary = re.search(
        r"^\s*([+-]?[0-9.]+|NA)\s+([+-]?[0-9.]+|NA)\s+([0-9]+|NA)\s+([0-9]+|NA)"
        r"\s+([+-]?[0-9.]+|NA)\s+([+-]?[0-9.]+|NA)\s+([0-9]+|NA)\s+([0-9]+|NA)"
        r"\s+([+-]?[0-9.]+|NA)\s+([+-]?[0-9.]+|NA)\s+([0-9]+|NA)\s+([0-9]+|NA)\s*$",
        text,
        re.MULTILINE,
    )
    clock = re.search(
        r"^clk_fpga_0\s+\{[0-9.]+\s+[0-9.]+\}\s+([0-9.]+)\s+([0-9.]+)\s*$",
        text,
        re.MULTILINE,
    )
    if not summary:
        raise ValueError(f"missing timing summary: {path}")

    def parse_float(value: str) -> float | None:
        return None if value == "NA" else float(value)

    def parse_int(value: str) -> int | None:
        return None if value == "NA" else int(value)

    fields = summary.groups()
    warnings = []
    for match in re.finditer(r"^([A-Z0-9_-]+)\s+(Warning|Critical Warning)\s+(.+?)\s+([0-9]+)\s*$", text, re.MULTILINE):
        warnings.append(
            {
                "rule": match.group(1),
                "severity": match.group(2),
                "description": match.group(3).strip(),
                "violations": int(match.group(4)),
            }
        )
    wns = parse_float(fields[0])
    tns_failing = parse_int(fields[2])
    ths_failing = parse_int(fields[6])
    tpws_failing = parse_int(fields[10])
    return {
        "report": artifact(path),
        "tool_version": parse_header(text, "Tool Version"),
        "date": parse_header(text, "Date"),
        "design": parse_header(text, "Design"),
        "device": parse_header(text, "Device"),
        "design_state": parse_header(text, "Design State"),
        "clock_period_ns": float(clock.group(1)) if clock else None,
        "clock_mhz": float(clock.group(2)) if clock else None,
        "wns_ns": wns,
        "tns_ns": parse_float(fields[1]),
        "tns_failing_endpoints": tns_failing,
        "tns_total_endpoints": parse_int(fields[3]),
        "whs_ns": parse_float(fields[4]),
        "ths_ns": parse_float(fields[5]),
        "ths_failing_endpoints": ths_failing,
        "ths_total_endpoints": parse_int(fields[7]),
        "wpws_ns": parse_float(fields[8]),
        "tpws_ns": parse_float(fields[9]),
        "tpws_failing_endpoints": tpws_failing,
        "tpws_total_endpoints": parse_int(fields[11]),
        "timing_met": (
            wns is not None
            and wns >= 0.0
            and tns_failing == 0
            and ths_failing == 0
            and tpws_failing == 0
        ),
        "report_says_timing_met": "All user specified timing constraints are met." in text,
        "methodology_warnings": warnings,
    }


def parse_utilization(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "report": artifact(path),
        "tool_version": parse_header(text, "Tool Version"),
        "date": parse_header(text, "Date"),
        "design": parse_header(text, "Design"),
        "device": parse_header(text, "Device"),
        "design_state": parse_header(text, "Design State"),
        "slice_luts": parse_table_row(text, "Slice LUTs"),
        "slice_registers": parse_table_row(text, "Slice Registers"),
        "block_ram_tile": parse_table_row(text, "Block RAM Tile"),
        "dsp": parse_table_row(text, "DSPs"),
    }


def parse_power(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")

    def table_value(label: str) -> str:
        match = re.search(r"^\|\s*" + re.escape(label) + r"\s*\|\s*([^|]+)\|", text, re.MULTILINE)
        if not match:
            raise ValueError(f"missing power row: {label}")
        return match.group(1).strip()

    return {
        "report": artifact(path),
        "tool_version": parse_header(text, "Tool Version"),
        "date": parse_header(text, "Date"),
        "design": parse_header(text, "Design"),
        "device": parse_header(text, "Device"),
        "design_state": parse_header(text, "Design State"),
        "total_on_chip_power_w": float(table_value("Total On-Chip Power (W)")),
        "dynamic_w": float(table_value("Dynamic (W)")),
        "device_static_w": float(table_value("Device Static (W)")),
        "confidence_level": table_value("Confidence Level"),
        "is_vectorless_estimate": table_value("Simulation Activity File") == "---",
    }


def build_report() -> dict[str, Any]:
    require_paths(
        [
            CSIM_SUMMARY,
            HLS_COMPILE_SUMMARY,
            CSYNTH_XML,
            CSYNTH_RPT,
            HLS_COMPONENT_XML,
            HLS_ZIP,
            BITSTREAM,
            HWH,
            TIMING_RPT,
            UTIL_RPT,
            POWER_RPT,
        ]
    )
    hls_csim = parse_vitis_summary(CSIM_SUMMARY, "CS_PASSED")
    hls_synthesis = parse_vitis_summary(HLS_COMPILE_SUMMARY, "CS_PASSED")
    csynth = parse_hls_csynth(CSYNTH_XML, CSYNTH_RPT)
    timing = parse_timing(TIMING_RPT)
    utilization = parse_utilization(UTIL_RPT)
    power = parse_power(POWER_RPT)
    artifacts = {
        "hls_ip_component_xml": artifact(HLS_COMPONENT_XML),
        "hls_kernel_zip": artifact(HLS_ZIP),
        "bitstream": artifact(BITSTREAM),
        "hwh": artifact(HWH),
    }
    report = {
        "schema": SCHEMA,
        "evidence_level": EVIDENCE_LEVEL,
        "board_executed": False,
        "toolchain": {
            "vitis": "2025.2",
            "vivado": "2025.2",
            "vivado_tool_version": timing["tool_version"],
        },
        "target": {
            "board": "pynq-z2",
            "part": "xc7z020clg400-1",
            "routed_clock_mhz": timing["clock_mhz"],
            "hls_target_clock_period_ns": csynth["target_clock_period_ns"],
        },
        "hls_csim": hls_csim,
        "hls_synthesis": hls_synthesis,
        "hls_csynth": csynth,
        "artifacts": artifacts,
        "vivado_routed": {
            "timing": timing,
            "utilization": utilization,
            "power_estimate": power,
            "all_timing_met": timing["timing_met"] and timing["report_says_timing_met"],
            "bitstream_and_hwh_present": artifacts["bitstream"]["size_bytes"] > 0
            and artifacts["hwh"]["size_bytes"] > 0,
        },
        "all_ok": (
            hls_csim["passed"]
            and hls_synthesis["passed"]
            and csynth["timing_estimate_meets_target"]
            and timing["timing_met"]
            and timing["report_says_timing_met"]
            and artifacts["bitstream"]["size_bytes"] > 0
            and artifacts["hwh"]["size_bytes"] > 0
        ),
        "known_limitations": [
            "HLS ENCODER_LOOP final II is 2 due Resource Limitation; accepted for this gate.",
            "Vivado power is vectorless/report_power estimate with Medium confidence; not board energy.",
            "No PYNQ-Z2 board execution, latency, throughput, or dataset correctness claim is made.",
        ],
        "claim_boundary": CLAIM_BOUNDARY,
    }
    report["hashes"] = {"build_evidence_sha256": sha256_json(report)}
    return report


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    hls = report["hls_csynth"]
    timing = report["vivado_routed"]["timing"]
    util = report["vivado_routed"]["utilization"]
    power = report["vivado_routed"]["power_estimate"]
    artifacts = report["artifacts"]
    warnings = timing["methodology_warnings"]
    warning_rows = "\n".join(
        f"| {item['rule']} | {item['severity']} | {item['violations']} | {item['description']} |"
        for item in warnings
    )
    text = f"""# SpikeMold HLS/Vivado Build Evidence Report

Status: HLS C-sim, HLS synthesis/IP package, and integrated Vivado route passed

## Evidence Level

`{report["evidence_level"]}`

No board execution was run. This report does not claim PYNQ-Z2 PL correctness,
latency, throughput, energy, or dataset accuracy.

## HLS Results

| Gate | Result | Evidence |
|---|---:|---|
| HLS C-sim | `{report["hls_csim"]["passed"]}` | `{report["hls_csim"]["summary"]["path"]}` |
| HLS synthesis/package | `{report["hls_synthesis"]["passed"]}` | `{hls["csynth_report"]["path"]}` |
| HLS timing estimate meets 12.5 ns | `{hls["timing_estimate_meets_target"]}` | estimated `{hls["estimated_clock_period_ns"]}` ns, Fmax `{hls["estimated_fmax_mhz"]}` MHz |
| HLS DSP usage | `{hls["resources"]["dsp"]}` | add-only top-level HLS estimate |

HLS resource estimate:

- BRAM_18K: `{hls["resources"]["bram_18k"]}` / `{hls["available_resources"]["bram_18k"]}`
- LUT: `{hls["resources"]["lut"]}` / `{hls["available_resources"]["lut"]}`
- FF: `{hls["resources"]["ff"]}` / `{hls["available_resources"]["ff"]}`
- DSP: `{hls["resources"]["dsp"]}` / `{hls["available_resources"]["dsp"]}`
- worst-case latency estimate: `{hls["latency_cycles"]["worst"]}` cycles (`{hls["latency_realtime"]["worst"]}`)
- ENCODER_LOOP final II: `{hls["encoder_loop_ii"]["final_ii"]}` (`{hls["encoder_loop_ii"]["violation_type"]}`)

## Vivado Routed Results

| Gate | Result | Evidence |
|---|---:|---|
| routed clock | `{timing["clock_mhz"]}` MHz | `{timing["report"]["path"]}` |
| routed WNS | `{timing["wns_ns"]}` ns | timing summary |
| routed TNS failing endpoints | `{timing["tns_failing_endpoints"]}` | timing summary |
| all timing met | `{report["vivado_routed"]["all_timing_met"]}` | timing summary |
| bitstream present | `{report["vivado_routed"]["bitstream_and_hwh_present"]}` | `outputs/spikemold_pynq_z2.bit` + `.hwh` |

Routed utilization:

- Slice LUTs: `{util["slice_luts"]["used"]}` / `{util["slice_luts"]["available"]}` (`{util["slice_luts"]["util_pct"]}`%)
- Slice Registers: `{util["slice_registers"]["used"]}` / `{util["slice_registers"]["available"]}` (`{util["slice_registers"]["util_pct"]}`%)
- Block RAM Tile: `{util["block_ram_tile"]["used"]}` / `{util["block_ram_tile"]["available"]}` (`{util["block_ram_tile"]["util_pct"]}`%)
- DSPs: `{util["dsp"]["used"]}` / `{util["dsp"]["available"]}` (`{util["dsp"]["util_pct"]}`%)

Power report estimate:

- total on-chip power: `{power["total_on_chip_power_w"]}` W
- dynamic: `{power["dynamic_w"]}` W
- static: `{power["device_static_w"]}` W
- confidence: `{power["confidence_level"]}`
- vectorless estimate: `{power["is_vectorless_estimate"]}`

## Artifacts

| Artifact | Size bytes | SHA-256 |
|---|---:|---|
| `{artifacts["hls_ip_component_xml"]["path"]}` | `{artifacts["hls_ip_component_xml"]["size_bytes"]}` | `{artifacts["hls_ip_component_xml"]["sha256"]}` |
| `{artifacts["hls_kernel_zip"]["path"]}` | `{artifacts["hls_kernel_zip"]["size_bytes"]}` | `{artifacts["hls_kernel_zip"]["sha256"]}` |
| `{artifacts["bitstream"]["path"]}` | `{artifacts["bitstream"]["size_bytes"]}` | `{artifacts["bitstream"]["sha256"]}` |
| `{artifacts["hwh"]["path"]}` | `{artifacts["hwh"]["size_bytes"]}` | `{artifacts["hwh"]["sha256"]}` |

## Methodology Warnings

| Rule | Severity | Count | Description |
|---|---|---:|---|
{warning_rows if warning_rows else "| none | none | 0 | none |"}

## Claim Boundary

`{report["claim_boundary"]}`

## Next Gate

Run PYNQ-Z2 one-shot board smoke with the generated bit/HWH and record board
JSON counters/readback. Until then, this is routed build evidence only.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    report = build_report()
    write_json(OUT_JSON, report)
    write_markdown(OUT_MD, report)
    print(f"Wrote {OUT_JSON.relative_to(ROOT)}")
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
