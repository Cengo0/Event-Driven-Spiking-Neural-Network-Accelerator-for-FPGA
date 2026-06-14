#!/usr/bin/env python3
"""Generate EventConv Vivado OOC synthesis evidence."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SYNTH_DIR = ROOT / "outputs" / "synthesis" / "eventconv_ooc"
OUT_JSON = ROOT / "outputs" / "resource" / "eventconv_ooc_synthesis_report.json"
OUT_MD = ROOT / "reports" / "eventconv_ooc_synthesis_report.md"
SCHEMA = "spikemold.eventconv_ooc_synthesis.v1"
EVIDENCE_LEVEL = "vivado_ooc_synthesis_no_board"

EVENTCONV_BLOCKS = {
    "eventconv_agu_c4": {
        "top": "spike_conv_agu",
        "rtl": "hardware/hdl/rtl/core/spike_conv_agu.v",
    },
    "eventconv_state_update_c4": {
        "top": "spike_conv_state_update",
        "rtl": "hardware/hdl/rtl/core/spike_conv_state_update.v",
    },
    "eventconv_active_commit_c4": {
        "top": "spike_conv_active_commit",
        "rtl": "hardware/hdl/rtl/core/spike_conv_active_commit.v",
    },
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def parse_table_row(text: str, label: str) -> dict[str, Any]:
    pattern = re.compile(
        r"^\|\s*" + re.escape(label) + r"\*?\s*\|\s*([0-9]+)\s*\|\s*([0-9]+)\s*\|"
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


def parse_utilization(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    design_match = re.search(r"^\| Design\s+:\s+(.+)$", text, re.MULTILINE)
    device_match = re.search(r"^\| Device\s+:\s+(.+)$", text, re.MULTILINE)
    tool_match = re.search(r"^\| Tool Version\s+:\s+(.+)$", text, re.MULTILINE)
    date_match = re.search(r"^\| Date\s+:\s+(.+)$", text, re.MULTILINE)
    return {
        "tool_version": tool_match.group(1).strip() if tool_match else "",
        "date": date_match.group(1).strip() if date_match else "",
        "design": design_match.group(1).strip() if design_match else "",
        "device": device_match.group(1).strip() if device_match else "",
        "slice_luts": parse_table_row(text, "Slice LUTs"),
        "slice_registers": parse_table_row(text, "Slice Registers"),
        "block_ram_tile": parse_table_row(text, "Block RAM Tile"),
        "dsp": parse_table_row(text, "DSPs"),
    }


def parse_timing(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    summary = re.search(
        r"^\s*([+-]?[0-9.]+|NA)\s+([+-]?[0-9.]+|NA)\s+([0-9]+|NA)\s+([0-9]+|NA)"
        r"\s+([+-]?[0-9.]+|NA)\s+([+-]?[0-9.]+|NA)\s+([0-9]+|NA)\s+([0-9]+|NA)\s*$",
        text,
        re.MULTILINE,
    )
    clock = re.search(
        r"^clk\s+\{[0-9.]+\s+[0-9.]+\}\s+([0-9.]+)\s+([0-9.]+)\s*$",
        text,
        re.MULTILINE,
    )
    if not summary:
        raise ValueError(f"missing timing summary: {path}")
    fields = summary.groups()

    def parse_float(value: str) -> float | None:
        return None if value == "NA" else float(value)

    def parse_int(value: str) -> int | None:
        return None if value == "NA" else int(value)

    wns = parse_float(fields[0])
    failing = parse_int(fields[2])
    return {
        "clock_period_ns": float(clock.group(1)) if clock else None,
        "clock_mhz": float(clock.group(2)) if clock else None,
        "wns_ns": wns,
        "tns_ns": parse_float(fields[1]),
        "tns_failing_endpoints": failing,
        "tns_total_endpoints": parse_int(fields[3]),
        "wpws_ns": parse_float(fields[4]),
        "tpws_ns": parse_float(fields[5]),
        "tpws_failing_endpoints": parse_int(fields[6]),
        "tpws_total_endpoints": parse_int(fields[7]),
        "timing_met": (wns is not None and wns >= 0.0 and failing == 0),
        "report_says_timing_met": "All user specified timing constraints are met." in text,
    }


def build_report() -> dict[str, Any]:
    eventconv_blocks: dict[str, Any] = {}
    aggregate = {
        "slice_luts_used": 0,
        "slice_registers_used": 0,
        "block_ram_tile_used": 0,
        "dsp_used": 0,
        "min_wns_ns": None,
    }

    for name, meta in EVENTCONV_BLOCKS.items():
        util_path = SYNTH_DIR / f"{name}_utilization.rpt"
        timing_path = SYNTH_DIR / f"{name}_timing.rpt"
        dcp_path = SYNTH_DIR / f"{name}.dcp"
        missing = [str(path) for path in [util_path, timing_path, dcp_path] if not path.exists()]
        if missing:
            raise FileNotFoundError(f"missing EventConv OOC artifacts for {name}: {missing}")

        utilization = parse_utilization(util_path)
        timing = parse_timing(timing_path)
        eventconv_blocks[name] = {
            "top": meta["top"],
            "rtl": meta["rtl"],
            "reports": {
                "utilization": str(util_path.relative_to(ROOT)),
                "timing": str(timing_path.relative_to(ROOT)),
                "checkpoint": str(dcp_path.relative_to(ROOT)),
            },
            "hashes": {
                "utilization_sha256": sha256_file(util_path),
                "timing_sha256": sha256_file(timing_path),
                "checkpoint_sha256": sha256_file(dcp_path),
            },
            "utilization": utilization,
            "timing": timing,
        }

        aggregate["slice_luts_used"] += utilization["slice_luts"]["used"]
        aggregate["slice_registers_used"] += utilization["slice_registers"]["used"]
        aggregate["block_ram_tile_used"] += utilization["block_ram_tile"]["used"]
        aggregate["dsp_used"] += utilization["dsp"]["used"]
        wns = timing["wns_ns"]
        if wns is not None:
            current = aggregate["min_wns_ns"]
            aggregate["min_wns_ns"] = wns if current is None else min(float(current), wns)

    target_clock_period_ns = next(iter(eventconv_blocks.values()))["timing"]["clock_period_ns"]
    target_clock_mhz = next(iter(eventconv_blocks.values()))["timing"]["clock_mhz"]
    report = {
        "schema": SCHEMA,
        "evidence_level": EVIDENCE_LEVEL,
        "board_executed": False,
        "toolchain": "Vivado 2025.2",
        "part": "xc7z020clg400-1",
        "target_clock_period_ns": target_clock_period_ns,
        "target_clock_mhz": target_clock_mhz,
        "selected_backend": "spikemold_fc_eventconv",
        "source_script": "hardware/scripts/synth_eventconv_ooc_synthesis.tcl",
        "runner_script": "hardware/scripts/run_eventconv_ooc_synthesis.sh",
        "eventconv_blocks": eventconv_blocks,
        "aggregate_utilization": aggregate,
        "all_blocks_synthesized": True,
        "all_timing_met": all(item["timing"]["timing_met"] for item in eventconv_blocks.values()),
        "all_dsp_zero": all(item["utilization"]["dsp"]["used"] == 0 for item in eventconv_blocks.values()),
        "all_bram_tile_zero": all(
            item["utilization"]["block_ram_tile"]["used"] == 0 for item in eventconv_blocks.values()
        ),
        "claim_boundary": "eventconv_ooc_synthesis_only_no_bitstream_no_board",
    }
    report["hashes"] = {"synthesis_report_sha256": sha256_json(report)}
    return report


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    rows = []
    for name, item in report["eventconv_blocks"].items():
        util = item["utilization"]
        timing = item["timing"]
        rows.append(
            "| {name} | `{top}` | {lut} | {ff} | {bram} | {dsp} | {wns:.3f} | {met} |".format(
                name=name,
                top=item["top"],
                lut=util["slice_luts"]["used"],
                ff=util["slice_registers"]["used"],
                bram=util["block_ram_tile"]["used"],
                dsp=util["dsp"]["used"],
                wns=float(timing["wns_ns"]),
                met=timing["timing_met"],
            )
        )

    aggregate = report["aggregate_utilization"]
    text = f"""# EventConv Vivado OOC Synthesis Report

Status: EventConv Vivado OOC synthesis evidence generated

## Evidence Level

`{report["evidence_level"]}`

No board execution was run. This report does not claim bitstream, routed timing,
PYNQ-Z2 PL correctness, latency, throughput, or energy.

## Target

- toolchain: `{report["toolchain"]}`
- part: `{report["part"]}`
- clock period: `{report["target_clock_period_ns"]}` ns
- clock frequency: `{report["target_clock_mhz"]}` MHz
- source script: `{report["source_script"]}`

## Results

| EventConv block | RTL top | LUT | FF | BRAM tile | DSP | WNS ns | Timing met |
|---|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

## Aggregate

- total LUT: `{aggregate["slice_luts_used"]}`
- total FF: `{aggregate["slice_registers_used"]}`
- total BRAM tile: `{aggregate["block_ram_tile_used"]}`
- total DSP: `{aggregate["dsp_used"]}`
- minimum WNS: `{aggregate["min_wns_ns"]}` ns
- all timing met: `{report["all_timing_met"]}`
- all DSP zero: `{report["all_dsp_zero"]}`
- all BRAM tile zero: `{report["all_bram_tile_zero"]}`

## Claim Boundary

`{report["claim_boundary"]}`
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
