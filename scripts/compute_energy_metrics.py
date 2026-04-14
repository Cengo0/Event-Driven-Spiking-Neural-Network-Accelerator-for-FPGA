#!/usr/bin/env python3
"""Compute paper-ready energy metrics from inference/power artifacts.

Inputs:
- inference JSON from tests/fpga_10class_inference.py
- power JSON from tests/ina226_power_measure.py

Outputs:
- Board-level energy per image (E2E and PL-window variants)
- Per-event energy (input spike / router spike / neuron spike)
- Optional PL-dynamic energy when XPA dynamic power is provided
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _get_active_idle_power_w(power: Dict[str, Any]) -> Tuple[Optional[float], Optional[float], str, Optional[float]]:
    """Return (active_W, idle_W, source_label, uncertainty_frac)."""
    mode = str(power.get("mode", "")).lower()

    # standalone / idle mode
    if "mean_total_W" in power:
        active = float(power["mean_total_W"])
        per_rail = power.get("per_rail", {})
        source = "unknown"
        uncertainty = None
        if isinstance(per_rail, dict) and "XADC_TOTAL" in per_rail:
            source = "xadc"
            uncertainty = 0.20
        elif isinstance(per_rail, dict) and per_rail:
            source = "ina226"
        return active, None, source, uncertainty

    # full mode (idle/busy)
    if mode == "full" and isinstance(power.get("busy"), dict):
        busy = power["busy"]
        idle = power.get("idle")
        active = float(busy.get("mean_total_W", 0.0))
        idle_w = float(idle.get("mean_total_W", 0.0)) if isinstance(idle, dict) else None
        per_rail = busy.get("per_rail", {}) if isinstance(busy, dict) else {}
        source = "unknown"
        uncertainty = None
        if isinstance(per_rail, dict) and "XADC_TOTAL" in per_rail:
            source = "xadc"
            uncertainty = 0.20
        elif isinstance(per_rail, dict) and per_rail:
            source = "ina226"
        return active, idle_w, source, uncertainty

    return None, None, "unknown", None


def _safe_div(x: float, y: float) -> Optional[float]:
    if y == 0:
        return None
    return x / y


def _fmt(v: Optional[float], unit: str = "") -> str:
    if v is None:
        return "N/A"
    if abs(v) >= 1000 or abs(v) < 0.001:
        return f"{v:.6e}{unit}"
    return f"{v:.6f}{unit}"


def main() -> None:
    p = argparse.ArgumentParser(description="Compute energy metrics from inference/power artifacts")
    p.add_argument("--inference-json", required=True, help="Path to inference results JSON")
    p.add_argument("--power-json", required=True, help="Path to power results JSON")
    p.add_argument(
        "--xpa-dynamic-w",
        type=float,
        default=None,
        help="Optional PL dynamic power from Vivado XPA report (W)",
    )
    p.add_argument("--output", default=None, help="Optional output JSON path")
    args = p.parse_args()

    inf_path = Path(args.inference_json)
    pwr_path = Path(args.power_json)

    inf = _load_json(inf_path)
    pwr = _load_json(pwr_path)

    n_images = int(inf.get("n_images", 0))
    ms_per_img_e2e = float(inf.get("ms_per_image", 0.0))

    pl_clock_hz = float(inf.get("pl_clock_hz", 0.0))
    pl_latency_cycles_mean = inf.get("pl_latency_cycles_mean")
    pl_service_cycles_mean = inf.get("pl_service_cycles_mean")

    pl_latency_ms_mean = inf.get("pl_latency_ms_mean")
    if pl_latency_ms_mean is None and pl_latency_cycles_mean is not None and pl_clock_hz > 0:
        pl_latency_ms_mean = (float(pl_latency_cycles_mean) / pl_clock_hz) * 1000.0

    pl_service_ms_mean = inf.get("pl_service_ms_mean")
    if pl_service_ms_mean is None and pl_service_cycles_mean is not None and pl_clock_hz > 0:
        pl_service_ms_mean = (float(pl_service_cycles_mean) / pl_clock_hz) * 1000.0

    total_input_words = float(inf.get("total_input_words", 0))
    total_router_spikes = float(inf.get("total_router_spikes", 0))
    total_neuron_spikes = float(inf.get("total_neuron_spikes", 0))

    input_spk_per_img = _safe_div(total_input_words, max(n_images, 1))
    router_spk_per_img = _safe_div(total_router_spikes, max(n_images, 1))
    neuron_spk_per_img = _safe_div(total_neuron_spikes, max(n_images, 1))

    p_active_w, p_idle_w, power_source, p_unc = _get_active_idle_power_w(pwr)

    if p_active_w is None:
        raise SystemExit("Could not parse active power from power JSON")

    # Board-level energy metrics
    e_board_e2e_mj = p_active_w * ms_per_img_e2e
    e_board_firstspike_mj = (p_active_w * float(pl_latency_ms_mean)) if pl_latency_ms_mean is not None else None
    e_board_service_mj = (p_active_w * float(pl_service_ms_mean)) if pl_service_ms_mean is not None else None

    # Optional board dynamic-only (active-idle)
    p_board_dyn_w = (p_active_w - p_idle_w) if p_idle_w is not None else None
    e_board_dyn_service_mj = (
        p_board_dyn_w * float(pl_service_ms_mean)
        if (p_board_dyn_w is not None and pl_service_ms_mean is not None)
        else None
    )

    # Optional PL-dynamic-only using XPA
    p_pl_dyn_w = args.xpa_dynamic_w
    e_pl_dyn_firstspike_mj = (
        p_pl_dyn_w * float(pl_latency_ms_mean)
        if (p_pl_dyn_w is not None and pl_latency_ms_mean is not None)
        else None
    )
    e_pl_dyn_service_mj = (
        p_pl_dyn_w * float(pl_service_ms_mean)
        if (p_pl_dyn_w is not None and pl_service_ms_mean is not None)
        else None
    )

    def per_event_uj(e_mj: Optional[float], events_per_img: Optional[float]) -> Optional[float]:
        if e_mj is None or events_per_img is None or events_per_img <= 0:
            return None
        return (e_mj * 1000.0) / events_per_img

    report = {
        "inference_json": str(inf_path),
        "power_json": str(pwr_path),
        "n_images": n_images,
        "power": {
            "active_w": p_active_w,
            "idle_w": p_idle_w,
            "board_dynamic_w": p_board_dyn_w,
            "source": power_source,
            "uncertainty_frac": p_unc,
            "xpa_dynamic_w": p_pl_dyn_w,
        },
        "latency": {
            "system_ms_per_img": ms_per_img_e2e,
            "pl_clock_hz": pl_clock_hz,
            "pl_first_spike_cycles_mean": pl_latency_cycles_mean,
            "pl_first_spike_ms_mean": pl_latency_ms_mean,
            "pl_service_cycles_mean": pl_service_cycles_mean,
            "pl_service_ms_mean": pl_service_ms_mean,
        },
        "events_per_img": {
            "input_spikes": input_spk_per_img,
            "router_spikes": router_spk_per_img,
            "neuron_spikes": neuron_spk_per_img,
        },
        "energy_mj_per_img": {
            "board_e2e": e_board_e2e_mj,
            "board_first_spike_window": e_board_firstspike_mj,
            "board_service_window": e_board_service_mj,
            "board_dynamic_service_window": e_board_dyn_service_mj,
            "pl_dynamic_first_spike_window": e_pl_dyn_firstspike_mj,
            "pl_dynamic_service_window": e_pl_dyn_service_mj,
        },
        "energy_uj_per_event": {
            "board_e2e_per_input_spike": per_event_uj(e_board_e2e_mj, input_spk_per_img),
            "board_e2e_per_router_spike": per_event_uj(e_board_e2e_mj, router_spk_per_img),
            "board_e2e_per_neuron_spike": per_event_uj(e_board_e2e_mj, neuron_spk_per_img),
            "board_service_per_input_spike": per_event_uj(e_board_service_mj, input_spk_per_img),
            "pl_dynamic_service_per_input_spike": per_event_uj(e_pl_dyn_service_mj, input_spk_per_img),
        },
    }

    print("=== Energy Metrics Summary ===")
    print(f"Power source: {power_source} (active={_fmt(p_active_w, ' W')}, idle={_fmt(p_idle_w, ' W')})")
    if p_unc is not None:
        print(f"Power uncertainty: ±{p_unc*100:.0f}%")
    if p_pl_dyn_w is not None:
        print(f"XPA PL dynamic power: {_fmt(p_pl_dyn_w, ' W')}")

    print("\nLatency metrics")
    print(f"  System E2E: {_fmt(ms_per_img_e2e, ' ms/img')}")
    print(f"  PL first-spike: {_fmt(pl_latency_ms_mean, ' ms/img')}")
    print(f"  PL service: {_fmt(pl_service_ms_mean, ' ms/img')}")

    print("\nEnergy (mJ/img)")
    for k, v in report["energy_mj_per_img"].items():
        print(f"  {k}: {_fmt(v, ' mJ/img')}")

    print("\nPer-event energy")
    for k, v in report["energy_uj_per_event"].items():
        print(f"  {k}: {_fmt(v, ' uJ/event')}")

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
