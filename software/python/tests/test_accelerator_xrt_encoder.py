"""XRT encoder-path regression tests for SNNAccelerator."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from snn_fpga_accelerator.accelerator import SNNAccelerator, SpikeEvent


class _DummyXRTBackend:
    def __init__(self):
        self.encoder_calls = []
        self.learning_calls = []
        self.mode_calls = []
        self.time_steps_calls = []
        self.sent_packets = []

    def set_encoder_config(self, **kwargs):
        self.encoder_calls.append(dict(kwargs))

    def set_learning_params(self, **kwargs):
        self.learning_calls.append(dict(kwargs))

    def set_mode(self, mode: int, encoder_enable: bool = False):
        self.mode_calls.append((int(mode), bool(encoder_enable)))

    def set_time_steps(self, steps: int):
        self.time_steps_calls.append(int(steps))

    def send_spike_stream(self, spike_data: bytes, run_kernel: bool = True):
        self.sent_packets.append((bytes(spike_data), bool(run_kernel)))

    def receive_spike_stream(self, max_size: int = 4096) -> bytes:
        return b""


def _mk_xrt_accel() -> tuple:
    acc = SNNAccelerator(simulation_mode=True)
    dummy = _DummyXRTBackend()
    acc.use_xrt = True
    acc._xrt_backend = dummy
    return acc, dummy


def test_configure_encoder_delta_sigma_maps_to_hw_type_1():
    acc, dummy = _mk_xrt_accel()

    acc.configure_encoder(
        encoding_type="delta_sigma",
        num_steps=100,
        delta_threshold=777,
        delta_decay=9,
        num_channels=64,
        default_weight=101,
    )

    call = dummy.encoder_calls[-1]
    assert call["encoding_type"] == 1
    assert call["delta_threshold"] == 777
    assert call["delta_decay"] == 9
    assert call["num_channels"] == 64
    assert call["default_weight"] == 101


def test_configure_encoder_rate_poisson_disables_hw_encoder():
    acc, dummy = _mk_xrt_accel()

    acc.configure_encoder(
        encoding_type="rate_poisson",
        num_steps=100,
        rate_scale=256,
        num_channels=32,
    )

    call = dummy.encoder_calls[-1]
    assert call["encoding_type"] == 0
    assert call["num_channels"] == 32


def test_run_simulation_xrt_legacy_type_3_maps_to_delta_sigma():
    acc, dummy = _mk_xrt_accel()
    spikes = [SpikeEvent(neuron_id=3, timestamp=0.0, weight=1.0)]

    acc._run_simulation_xrt(
        duration=0.01,
        input_spikes=spikes,
        encoding_type=3,  # legacy DELTA_SIGMA code
        encoder_params={
            "delta_threshold": 600,
            "delta_decay": 4,
            "num_channels": 1,
            "default_weight": 99,
        },
    )

    assert dummy.mode_calls[-1] == (0, True)
    call = dummy.encoder_calls[-1]
    assert set(call.keys()) == {
        "encoding_type",
        "delta_threshold",
        "delta_decay",
        "num_channels",
        "default_weight",
    }
    assert call["encoding_type"] == 1


def test_set_learning_parameters_uses_xrt_packed_interface():
    acc, dummy = _mk_xrt_accel()
    acc.simulation_mode = False

    acc.set_learning_parameters(
        learning_rate=0.05,
        stdp_window=42,
        a_plus=0.2,
        a_minus=0.3,
        tau_plus=30,
        tau_minus=40,
        rstdp_enable=True,
        trace_decay=0.25,
        reward_scale=1.5,
    )

    call = dummy.learning_calls[-1]
    assert call["learning_rate"] == 0.05
    assert call["stdp_window"] == 42
    assert call["a_plus"] == 0.2
    assert call["a_minus"] == 0.3
    assert call["tau_plus"] == 30
    assert call["tau_minus"] == 40
    assert call["rstdp_enable"] is True
    assert call["trace_decay"] == 0.25
    assert call["reward_scale"] == 1.5
