"""Unit tests for XRT register map and packing helpers."""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from snn_fpga_accelerator.xrt_backend import (
    RegisterMap,
    pack_learning_params_words,
    pack_encoder_config_words,
)


def _load_hls_axi_ctrl_offsets() -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    hls_data_path = repo_root / "hardware" / "hls" / "hls_output" / "hls" / "hls_data.json"
    if not hls_data_path.exists():
        pytest.skip(f"HLS metadata not found: {hls_data_path}")

    with hls_data_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    registers = data.get("Interfaces", {}).get("s_axi_ctrl", {}).get("registers", [])
    if not registers:
        pytest.skip("No s_axi_ctrl register metadata in hls_data.json")

    return {r["name"]: int(r["offset"], 0) for r in registers if "name" in r and "offset" in r}


def test_register_map_matches_hls_ctrl_offsets():
    regs = RegisterMap()
    hls_off = _load_hls_axi_ctrl_offsets()

    assert regs.ctrl_reg == hls_off["ctrl_reg"]
    assert regs.config_reg == hls_off["config_reg"]
    assert regs.mode_reg == hls_off["mode_reg"]
    assert regs.time_steps_reg == hls_off["time_steps_reg"]

    assert regs.learning_base == hls_off["learning_params_1"]
    assert hls_off["learning_params_5"] == (regs.learning_base + 0x10)

    assert regs.encoder_base == hls_off["encoder_config_1"]
    assert hls_off["encoder_config_3"] == (regs.encoder_base + 0x08)

    assert regs.status_reg == hls_off["status_reg"]
    assert regs.spike_count_reg == hls_off["spike_count_reg"]
    assert regs.weight_sum_reg == hls_off["weight_sum_reg"]
    assert regs.version_reg == hls_off["version_reg"]
    assert regs.reward_signal == hls_off["reward_signal"]


def test_pack_learning_params_words_layout():
    words = pack_learning_params_words(
        a_plus=0.5,
        a_minus=-0.25,
        tau_plus=20,
        tau_minus=30,
        stdp_window=50,
        learning_rate=0.01,
        rstdp_enable=True,
        trace_decay=0.125,
        reward_scale=1.0,
    )

    # Q8.8: 0.5 -> 0x0080, -0.25 -> 0xFFC0
    assert words[0] == 0xFFC00080
    assert words[1] == 0x001E0014
    # learning_rate=0.01 -> round(2.56)=3 -> 0x0003 in upper 16b
    assert words[2] == 0x00030032
    # rstdp in bit[0] of low byte, trace_decay=0.125 -> 0x0020 upper 16b
    assert words[3] == 0x00200001
    # reward_scale=1.0 -> 0x0100
    assert words[4] == 0x00000100


def test_pack_encoder_config_words_layout():
    w0, w1, w2 = pack_encoder_config_words(
        encoding_type=1,
        delta_threshold=0x1234,
        delta_decay=0x00AA,
        num_channels=0x0555,
        default_weight=0x7F,
    )
    assert w0 == 0x12340001
    assert w1 == 0x055500AA
    assert w2 == 0x0000007F
