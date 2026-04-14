"""
HLS STDP trace-rule parity tests.

Verifies that HWAccurateSTDPEngine applies the same integer arithmetic as
hardware/hls/src/snn_top_hls.cpp for:
  - LTP (post spike update)
  - LTD (pre spike update)
  - R-STDP reward modulation
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from snn_fpga_accelerator.hw_accurate_simulator import HWAccurateSTDPEngine, STDPConfig


def _mk_engine(cfg: STDPConfig) -> HWAccurateSTDPEngine:
    eng = HWAccurateSTDPEngine(cfg, max_neurons=16)
    w = np.zeros((16, 16), dtype=np.int16)
    eng.set_weights(w)
    eng.add_synapse(0, 1)
    return eng


def test_ltp_integer_path_matches_hls_formula():
    """
    LTP reference (HLS):
      distance = w_max - w
      scaled   = (distance * pre_trace * a_plus_raw) >> 16
      delta    = (scaled * learning_rate_raw) >> 8
    """
    cfg = STDPConfig(a_plus=1.0, a_minus=1.0, learning_rate=1.0, trace_decay=0.125)
    eng = _mk_engine(cfg)
    eng.put_weight(0, 1, -8)  # maximize distance for non-zero delta

    eng.process_pre_spike(0, timestamp=10, connected_post_ids=[1])  # pre_trace[0] = 128
    updates = eng.process_post_spike(1, timestamp=10, connected_pre_ids=[0])

    assert len(updates) == 1
    assert updates[0].delta == 7  # ((15*128*256)>>16)*256>>8 = 7
    assert eng.get_weight(0, 1) == -1


def test_ltd_with_global_trace_decay_matches_hls_formula():
    """
    LTD reference with two global decays:
      post_trace: 128 -> 112 -> 98  (trace_decay=0.125)
      delta = -((((15 * 98) * 256) >> 16) * 256 >> 8) = -5
    """
    cfg = STDPConfig(a_plus=1.0, a_minus=1.0, learning_rate=1.0, trace_decay=0.125)
    eng = _mk_engine(cfg)
    eng.put_weight(0, 1, 7)

    eng.process_post_spike(1, timestamp=0, connected_pre_ids=[0])   # post_trace[1] = 128
    updates = eng.process_pre_spike(0, timestamp=2, connected_post_ids=[1])

    assert len(updates) == 1
    assert updates[0].delta == -5
    assert eng.get_weight(0, 1) == 2


def test_rstdp_reward_integer_path_matches_hls_formula():
    """
    R-STDP reference (reward_signal=64 => shift_sel=0):
      pre_elig=32, post_elig=32
      combined   = (32*32) >> 8 = 4
      base_scaled= combined >> 1 = 2
      delta      = (2 * reward_scale_raw) >> 8 = 2  (reward_scale=1.0)
    """
    cfg = STDPConfig(
        a_plus=1.0,
        a_minus=1.0,
        learning_rate=0.0,  # isolate reward path from STDP updates
        trace_decay=0.125,
        rstdp_enable=True,
        reward_scale=1.0,
    )
    eng = _mk_engine(cfg)
    eng.put_weight(0, 1, 0)

    eng.process_pre_spike(0, timestamp=0, connected_post_ids=[1])   # pre_elig += 32
    eng.process_post_spike(1, timestamp=0, connected_pre_ids=[0])   # post_elig += 32
    updates = eng.apply_rstdp_reward(reward_signal=64, timestamp=0)

    assert len(updates) == 1
    assert updates[0].delta == 2
    assert eng.get_weight(0, 1) == 2
    # Eligibility decay is applied after reward: 32 - (32 >> 3) = 28
    assert int(eng.pre_eligibility[0]) == 28
    assert int(eng.post_eligibility[1]) == 28
