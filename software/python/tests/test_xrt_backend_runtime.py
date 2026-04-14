"""Runtime behavior tests for XRTBackend control-path logic."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import snn_fpga_accelerator.xrt_backend as xrt_backend_module
from snn_fpga_accelerator.exceptions import TimeoutError as AcceleratorTimeoutError
from snn_fpga_accelerator.xrt_backend import RegisterMap, XRTBackend


class _FakeKernel:
    def __init__(self, ap_ctrl_sequence):
        self._ap_ctrl_sequence = list(ap_ctrl_sequence)
        self._idx = 0
        self.write_log = []

    def write_register(self, offset, value):
        self.write_log.append((int(offset), int(value)))

    def read_register(self, offset):
        if offset != 0x00:
            return 0
        if not self._ap_ctrl_sequence:
            return 0
        if self._idx < len(self._ap_ctrl_sequence):
            value = self._ap_ctrl_sequence[self._idx]
            self._idx += 1
            return int(value)
        return int(self._ap_ctrl_sequence[-1])


def _build_backend(ap_ctrl_sequence) -> XRTBackend:
    backend = object.__new__(XRTBackend)
    backend.kernel = _FakeKernel(ap_ctrl_sequence)
    backend.regs = RegisterMap()
    return backend


def test_run_kernel_treats_ap_ready_as_non_error(monkeypatch):
    monkeypatch.setattr(xrt_backend_module, "xrt", object())
    backend = _build_backend(
        [
            XRTBackend.AP_READY,  # ready asserted before done
            XRTBackend.AP_READY | XRTBackend.AP_DONE,
        ]
    )

    backend.run_kernel(timeout_sec=0.1)

    assert backend.kernel.write_log[0] == (backend.regs.ap_ctrl, XRTBackend.AP_START)


def test_run_kernel_times_out_when_ap_done_not_set(monkeypatch):
    monkeypatch.setattr(xrt_backend_module, "xrt", object())
    backend = _build_backend([XRTBackend.AP_READY])

    with pytest.raises(AcceleratorTimeoutError):
        backend.run_kernel(timeout_sec=0.005)
