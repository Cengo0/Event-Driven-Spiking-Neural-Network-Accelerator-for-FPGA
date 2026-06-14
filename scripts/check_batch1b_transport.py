#!/usr/bin/env python3
"""Check Batch 1B SpikeMold-EDNP transport smoke artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = ROOT / "software" / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from spikepress.transport import (  # noqa: E402
    AXI_LITE_SMOKE_SCHEMA,
    DMA_LOOPBACK_SCHEMA,
    EDNP_MINI_SMOKE_SCHEMA,
    EVENTWORD_COUNTER_SCHEMA,
    TRANSPORT_SMOKE_SCHEMA,
)


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - diagnostic path
        fail(f"cannot load JSON {path}: {exc}")


def require_section(root: dict, key: str, schema: str) -> dict:
    section = root.get(key)
    if not isinstance(section, dict):
        fail(f"missing section: {key}")
    if section.get("schema") != schema:
        fail(f"{key} schema mismatch")
    if section.get("ok") is not True:
        fail(f"{key} ok is not true")
    if section.get("board_executed") is not False:
        fail(f"{key} must not claim board execution")
    return section


def main() -> int:
    smoke_path = ROOT / "outputs" / "transport" / "batch_1b_transport_ednp_mini_smoke.json"
    report_path = ROOT / "reports" / "batch_1b_transport_ednp_mini_report.md"
    if not smoke_path.exists():
        fail(f"missing smoke artifact: {smoke_path}")
    if not report_path.exists():
        fail(f"missing report: {report_path}")

    smoke = load_json(smoke_path)
    if smoke.get("schema") != TRANSPORT_SMOKE_SCHEMA:
        fail("transport smoke schema mismatch")
    if smoke.get("all_ok") is not True:
        fail("transport smoke all_ok is not true")
    if smoke.get("board_executed") is not False:
        fail("transport smoke must not claim board execution")

    assumptions = smoke.get("runtime_assumptions", {})
    if assumptions.get("bounded_job") is not True:
        fail("bounded_job assumption missing")
    for key in ["python_inner_loop_required", "random_ddr_inner_loop", "full_neuron_scan_primary"]:
        if assumptions.get(key) is not False:
            fail(f"forbidden runtime assumption not false: {key}")

    require_section(smoke, "register_smoke", AXI_LITE_SMOKE_SCHEMA)
    require_section(smoke, "dma_loopback", DMA_LOOPBACK_SCHEMA)
    require_section(smoke, "eventword64_counter", EVENTWORD_COUNTER_SCHEMA)
    ednp = require_section(smoke, "ednp_mini_fc_lif", EDNP_MINI_SMOKE_SCHEMA)
    if ednp.get("trace_match_rate") != 1.0:
        fail("EDNP-mini trace_match_rate is not 1.0")
    if ednp.get("readout_match") is not True:
        fail("EDNP-mini readout_match is not true")
    if ednp.get("state_checksum_match") is not True:
        fail("EDNP-mini state_checksum_match is not true")
    counters = ednp.get("counters", {})
    for key in ["input_event_count", "update_count", "active_count", "output_words", "dma_calls", "axi_lite_commands"]:
        if int(counters.get(key, -1)) < 0:
            fail(f"missing or invalid counter: {key}")
    if int(counters.get("python_inner_loop_steps", -1)) != 0:
        fail("python_inner_loop_steps must be zero")

    text = report_path.read_text(encoding="utf-8")
    for phrase in ["Board execution was not run", "software_transport_smoke_no_board"]:
        if phrase not in text:
            fail(f"report missing evidence phrase: {phrase}")

    print("PASS: Batch 1B transport + EDNP-mini smoke artifacts valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
