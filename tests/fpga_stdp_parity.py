#!/usr/bin/env python3
"""
On-board STDP parity harness (HW checkpoint vs bit-accurate SW simulator).

Flow:
  1) Program router so pre source IDs map to deterministic post neuron IDs.
  2) Run HLS in STDP mode (op_mode=1) for N steps with synthetic spikes.
  3) Read full HLS weight checkpoint stream via dedicated weight DMA.
  4) Replay identical pre/post events in HWAccurateSTDPEngine.
  5) Compare full flat weight buffer 1:1 (optionally every sample/chunk).

Requires integrated bitstream rebuilt with weight-stream DMA connections:
  - axi_dma_1 MM2S  -> snn_top_hls_0/s_axis_weights
  - snn_top_hls_0/m_axis_weights -> axi_dma_1 S2MM
"""

import argparse
import importlib
import importlib.util
import json
import mmap
import os
import struct
import sys
import time
import types
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import warnings

import numpy as np


# ---------------------------------------------------------------------------
# Local imports (works without pip install)
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
PKG_PARENT = REPO_ROOT / "software" / "python"
PKG_DIR = PKG_PARENT / "snn_fpga_accelerator"
sys.path.insert(0, str(PKG_PARENT))
sys.path.insert(0, str(REPO_ROOT))

warnings.filterwarnings(
    "ignore",
    message=r"PyTorch not found\..*",
    category=RuntimeWarning,
)


def _load_local_submodule(pkg_dir: Path, mod_name: str):
    full_name = f"snn_fpga_accelerator.{mod_name}"
    if full_name in sys.modules:
        return sys.modules[full_name]

    src = pkg_dir / f"{mod_name}.py"
    if not src.exists():
        raise ModuleNotFoundError(f"missing module source: {src}")

    spec = importlib.util.spec_from_file_location(full_name, str(src))
    if spec is None or spec.loader is None:
        raise ImportError(f"failed to load module spec: {full_name}")

    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _import_hw_accurate_sim_module():
    import_exc = None
    try:
        return importlib.import_module("snn_fpga_accelerator.hw_accurate_simulator")
    except ModuleNotFoundError as exc:
        # Fall back to direct file loading so this script works even when the
        # package is not installed, or when __init__.py optional deps are absent.
        import_exc = exc

    if not PKG_DIR.exists():
        raise ModuleNotFoundError(
            "snn_fpga_accelerator package not found.\n"
            f"Expected path: {PKG_DIR}\n"
            "Copy the repository's software/python directory to the board, or run:\n"
            f"  sudo PYTHONPATH={PKG_PARENT}:$PYTHONPATH python3 tests/fpga_stdp_parity.py ..."
        ) from import_exc

    # Build a minimal package shell so relative imports inside modules work
    # without requiring pip install or __init__.py side effects.
    if "snn_fpga_accelerator" not in sys.modules:
        pkg = types.ModuleType("snn_fpga_accelerator")
        pkg.__path__ = [str(PKG_DIR)]
        pkg.__package__ = "snn_fpga_accelerator"
        sys.modules["snn_fpga_accelerator"] = pkg

    _load_local_submodule(PKG_DIR, "spike_encoding")
    _load_local_submodule(PKG_DIR, "utils")
    return _load_local_submodule(PKG_DIR, "hw_accurate_simulator")


_HW_SIM = _import_hw_accurate_sim_module()

CONNECTIONS = _HW_SIM.CONNECTIONS
HWAccurateSTDPEngine = _HW_SIM.HWAccurateSTDPEngine
MAX_WEIGHT_BUFFER_SIZE = _HW_SIM.MAX_WEIGHT_BUFFER_SIZE
PACKED_MAX_WEIGHT = _HW_SIM.PACKED_MAX_WEIGHT
PACKED_MIN_WEIGHT = _HW_SIM.PACKED_MIN_WEIGHT
STDPConfig = _HW_SIM.STDPConfig
WEIGHT_BITS = int(getattr(_HW_SIM, "WEIGHT_BITS", 8))
NEURON_GROUP_ID_START = getattr(
    _HW_SIM,
    "NEURON_GROUP_ID_START",
    [0, 196, 392, 588, 784, 1808, 2832, 3856, 4880, 4890],
)

PACKED_WORD_BITS = max(1, min(int(WEIGHT_BITS), 8))
PACKED_WORD_MASK = (1 << PACKED_WORD_BITS) - 1
PACKED_WORD_SIGN = 1 << (PACKED_WORD_BITS - 1)


def _q8_8(value: float) -> int:
    raw = int(round(float(value) * 256.0))
    if raw > 32767:
        raw = 32767
    elif raw < -32768:
        raw = -32768
    return raw & 0xFFFF


def pack_learning_params_words(
    a_plus: float = 0.1,
    a_minus: float = 0.12,
    tau_plus: int = 20,
    tau_minus: int = 20,
    stdp_window: int = 50,
    learning_rate: float = 0.01,
    rstdp_enable: bool = False,
    trace_decay: float = 0.125,
    reward_scale: float = 1.0,
) -> Tuple[int, int, int, int, int]:
    tau_plus_u16 = int(tau_plus) & 0xFFFF
    tau_minus_u16 = int(tau_minus) & 0xFFFF
    stdp_window_u16 = int(stdp_window) & 0xFFFF
    rstdp_u8 = 1 if rstdp_enable else 0

    a_plus_u16 = _q8_8(a_plus)
    a_minus_u16 = _q8_8(a_minus)
    learning_rate_u16 = _q8_8(learning_rate)
    trace_decay_u16 = _q8_8(trace_decay)
    reward_scale_u16 = _q8_8(reward_scale)

    w0 = a_plus_u16 | (a_minus_u16 << 16)
    w1 = tau_plus_u16 | (tau_minus_u16 << 16)
    w2 = stdp_window_u16 | (learning_rate_u16 << 16)
    w3 = (rstdp_u8 & 0xFF) | (trace_decay_u16 << 16)
    w4 = reward_scale_u16
    return w0, w1, w2, w3, w4


# ---------------------------------------------------------------------------
# HWH helpers (preflight address-map sanity)
# ---------------------------------------------------------------------------

def _parse_hex_u32(text: str) -> Optional[int]:
    if text is None:
        return None
    t = text.strip()
    try:
        return int(t, 16) if t.lower().startswith("0x") else int(t, 10)
    except ValueError:
        return None


def _find_memrange(hwh_path: str, instance: str) -> Optional[Tuple[int, int]]:
    try:
        root = ET.parse(hwh_path).getroot()
    except Exception:
        return None

    for mr in root.iter("MEMRANGE"):
        if mr.get("INSTANCE") != instance:
            continue
        base = _parse_hex_u32(mr.get("BASEVALUE"))
        high = _parse_hex_u32(mr.get("HIGHVALUE"))
        if base is not None and high is not None and high >= base:
            return base, high
    return None


def detect_hls_visible_offset_limit(hwh_path: str, hls_base: int) -> Optional[int]:
    mr = _find_memrange(hwh_path, "snn_top_hls_0")
    if mr is None:
        return None
    base, high = mr
    if base != hls_base or high < base:
        return None
    return int(high - base)


def detect_dma_present(hwh_path: str, dma_instance: str, dma_base: int) -> bool:
    mr = _find_memrange(hwh_path, dma_instance)
    if mr is None:
        return False
    return int(mr[0]) == int(dma_base)


# ---------------------------------------------------------------------------
# Register map (snn_integrated_v2)
# ---------------------------------------------------------------------------

HLS_BASE = 0x43C00000
CFG_BASE = 0x43C10000
DMA_SPIKE_BASE = 0x41E00000
DMA_WEIGHT_BASE = 0x41E10000  # second DMA for checkpoint/weight stream

HLS_AP_CTRL = 0x00
HLS_CTRL_REG = 0x10
HLS_CONFIG_REG = 0x18
HLS_MODE_REG = 0x20
HLS_TIME_STEPS = 0x28
HLS_LEARNING_BASE = 0x30  # 5 x 32-bit words
HLS_STATUS_REG = 0x58
HLS_STATUS_VLD = 0x5C
HLS_SPIKE_COUNT = 0x68
HLS_SPIKE_COUNT_VLD = 0x6C
HLS_WEIGHT_SUM = 0x78
HLS_VERSION_REG = 0x88
HLS_REWARD_SIGNAL = 0x98

CFG_CONFIG_CTRL = 0x00
CFG_CONFIG_ADDR = 0x04
CFG_CONFIG_WDATA = 0x08
CFG_CONFIG_RDATA = 0x0C
CFG_THRESHOLD = 0x10
CFG_NEURON_PARAMS = 0x14
CFG_ROUTER_SPKS = 0x18
CFG_NEURON_SPKS = 0x1C
CFG_STATUS = 0x20
CFG_VERSION = 0x28

DMA_MM2S_DMACR = 0x00
DMA_MM2S_DMASR = 0x04
DMA_MM2S_SA = 0x18
DMA_MM2S_LENGTH = 0x28
DMA_S2MM_DMACR = 0x30
DMA_S2MM_DMASR = 0x34
DMA_S2MM_DA = 0x48
DMA_S2MM_LENGTH = 0x58

CTRL_ENABLE = 0x01
CTRL_RESET = 0x02
CTRL_CLEAR = 0x04
CTRL_LEARNING_EN = 0x08
CTRL_WEIGHT_READ = 0x10
CTRL_APPLY_REWARD = 0x20
CTRL_FIRST_SPIKE_ONLY = 0x80
CTRL_WEIGHT_LOAD = 0x40

MODE_INFERENCE = 0
MODE_TRAIN_STDP = 1
MODE_CHECKPOINT = 2

EXPECTED_CFG_VERSION = 0x534E4E01
EXPECTED_HLS_VERSION = 0x20260221

ROUTER_NEURON_ID_W = 10
MAX_FANOUT = 32

DMA_BUF_SPIKES_IN = 0x1F000000
DMA_BUF_SPIKES_OUT = 0x1F100000
DMA_BUF_WEIGHTS_OUT = 0x1F200000
DMA_BUF_WEIGHTS_IN = 0x1F300000

# Runtime tuning profiles (CPU usage vs latency trade-off).
_RUNTIME_PROFILES: Dict[str, Dict[str, float]] = {
    "balanced": {
        "hls_poll_s": 0.001,
        "dma_poll_s": 0.001,
        "router_rw_s": 20e-6,
        "dma_reset_s": 0.001,
        "setup_sleep_s": 0.001,
        "settle_min_s": 0.5,
        "settle_per_word_s": 0.05,
        "stall_timeout_s": 0.5,
        "post_chunk_drain_s": 0.005,
    },
    "fast": {
        "hls_poll_s": 0.0002,
        "dma_poll_s": 0.0002,
        "router_rw_s": 10e-6,
        "dma_reset_s": 0.0005,
        "setup_sleep_s": 0.0005,
        "settle_min_s": 0.2,
        "settle_per_word_s": 0.02,
        "stall_timeout_s": 0.2,
        "post_chunk_drain_s": 0.002,
    },
    "low-cpu": {
        "hls_poll_s": 0.002,
        "dma_poll_s": 0.002,
        "router_rw_s": 30e-6,
        "dma_reset_s": 0.0015,
        "setup_sleep_s": 0.0015,
        "settle_min_s": 0.8,
        "settle_per_word_s": 0.08,
        "stall_timeout_s": 0.8,
        "post_chunk_drain_s": 0.008,
    },
}

RUNTIME_TUNING: Dict[str, float] = dict(_RUNTIME_PROFILES["balanced"])


def _rt(key: str) -> float:
    return float(RUNTIME_TUNING.get(key, 0.001))


def _clamp_pos(v: float, lo: float = 1e-6, hi: float = 60.0) -> float:
    return max(lo, min(float(v), hi))


def configure_runtime_tuning(args) -> Dict[str, float]:
    prof = str(getattr(args, "runtime_profile", "balanced"))
    if prof not in _RUNTIME_PROFILES:
        prof = "balanced"
    cfg = dict(_RUNTIME_PROFILES[prof])

    # Optional overrides (in ms/us) for fine-grained tuning.
    if args.hls_poll_ms is not None:
        cfg["hls_poll_s"] = float(args.hls_poll_ms) / 1000.0
    if args.dma_poll_ms is not None:
        cfg["dma_poll_s"] = float(args.dma_poll_ms) / 1000.0
    if args.router_rw_us is not None:
        cfg["router_rw_s"] = float(args.router_rw_us) / 1_000_000.0
    if args.dma_reset_ms is not None:
        cfg["dma_reset_s"] = float(args.dma_reset_ms) / 1000.0
    if args.setup_sleep_ms is not None:
        cfg["setup_sleep_s"] = float(args.setup_sleep_ms) / 1000.0
    if args.settle_min_ms is not None:
        cfg["settle_min_s"] = float(args.settle_min_ms) / 1000.0
    if args.settle_per_word_ms is not None:
        cfg["settle_per_word_s"] = float(args.settle_per_word_ms) / 1000.0
    if args.stall_timeout_ms is not None:
        cfg["stall_timeout_s"] = float(args.stall_timeout_ms) / 1000.0
    if args.post_chunk_drain_ms is not None:
        cfg["post_chunk_drain_s"] = float(args.post_chunk_drain_ms) / 1000.0

    for k in list(cfg.keys()):
        cfg[k] = _clamp_pos(cfg[k])

    RUNTIME_TUNING.clear()
    RUNTIME_TUNING.update(cfg)
    return dict(cfg)


class MMIO:
    _PAGE = 4096

    def __init__(self, base: int, length: int = 0x1000):
        self._base = base
        self._off = base % self._PAGE
        mbase = base - self._off
        mlen = ((length + self._off + self._PAGE - 1) // self._PAGE) * self._PAGE
        self._fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
        self._mm = mmap.mmap(self._fd, mlen, offset=mbase)

    def read(self, offset: int) -> int:
        self._mm.seek(self._off + offset)
        return struct.unpack("<I", self._mm.read(4))[0]

    def write(self, offset: int, value: int) -> None:
        self._mm.seek(self._off + offset)
        self._mm.write(struct.pack("<I", value & 0xFFFF_FFFF))

    def write_bytes(self, offset: int, data: bytes) -> None:
        self._mm.seek(self._off + offset)
        self._mm.write(data)

    def read_bytes(self, offset: int, length: int) -> bytes:
        self._mm.seek(self._off + offset)
        return self._mm.read(length)

    def close(self) -> None:
        self._mm.close()
        os.close(self._fd)


def alloc_dma_buffer(
    n_words: int,
    fallback_paddr: int,
    prefer_cma: bool = True,
    tag: str = "",
    allow_unsafe_devmem: bool = False,
    devmem_window_words: Optional[int] = None,
) -> Dict[str, Any]:
    n_words_i = max(1, int(n_words))
    nbytes = n_words_i * 4

    if prefer_cma:
        try:
            from pynq import allocate as pynq_allocate  # type: ignore

            arr = pynq_allocate(shape=(n_words_i,), dtype=np.uint32)
            paddr = int(getattr(arr, "physical_address"))
            return {
                "mode": "cma",
                "arr": arr,
                "paddr": paddr,
                "n_words": n_words_i,
                "nbytes": nbytes,
                "tag": tag,
            }
        except Exception as e:
            print(f"  WARNING: CMA allocate failed for {tag or 'dma'} ({e}); falling back to /dev/mem fixed address")
            if "No Devices Found" in str(e):
                print("  HINT: XRT device is not visible in this sudo environment.")
                print("        Try: source /etc/profile.d/xrt_setup.sh && sudo -E ...")
            # Legacy PYNQ fallback path (no XRT device): Xlnk CMA allocator.
            try:
                from pynq import Xlnk  # type: ignore

                xlnk = Xlnk()
                arr = xlnk.cma_array(shape=(n_words_i,), dtype=np.uint32)
                paddr = int(getattr(arr, "physical_address"))
                return {
                    "mode": "xlnk",
                    "arr": arr,
                    "xlnk": xlnk,
                    "paddr": paddr,
                    "n_words": n_words_i,
                    "nbytes": nbytes,
                    "tag": tag,
                }
            except Exception as e_xlnk:
                print(f"  WARNING: Xlnk fallback failed for {tag or 'dma'} ({e_xlnk})")

    map_words = n_words_i
    if devmem_window_words is not None and devmem_window_words > 0:
        map_words = max(1, min(n_words_i, int(devmem_window_words)))

    if (not allow_unsafe_devmem) and (nbytes >= (1 << 20)) and map_words >= n_words_i:
        raise RuntimeError(
            f"Unsafe devmem fallback blocked for {tag or 'dma'} ({nbytes} bytes). "
            "No CMA/Xlnk allocator available. "
            "Either enable PYNQ CMA/XRT device, provide a devmem window, "
            "or pass --unsafe-devmem-checkpoint."
        )

    map_nbytes = map_words * 4
    mm = MMIO(fallback_paddr, max(4096, map_nbytes + 256))
    return {
        "mode": "devmem",
        "mmio": mm,
        "paddr": int(fallback_paddr),
        "n_words": int(map_words),          # mapped window words
        "nbytes": int(map_nbytes),          # mapped window bytes
        "requested_words": int(n_words_i),  # logical request
        "requested_bytes": int(nbytes),
        "tag": tag,
    }


def dma_buf_paddr(buf: Dict[str, Any]) -> int:
    return int(buf["paddr"])


def dma_buf_write_words(buf: Dict[str, Any], words: np.ndarray) -> None:
    words_u32 = np.asarray(words, dtype=np.uint32)
    n_words = int(words_u32.size)
    if n_words > int(buf["n_words"]):
        raise ValueError(f"DMA write exceeds buffer capacity: {n_words} > {buf['n_words']}")

    if buf["mode"] == "cma":
        arr = buf["arr"]
        arr[:n_words] = words_u32
        if hasattr(arr, "flush"):
            arr.flush()
    elif buf["mode"] == "xlnk":
        arr = buf["arr"]
        arr[:n_words] = words_u32
        if hasattr(arr, "flush"):
            arr.flush()
    else:
        buf["mmio"].write_bytes(0, words_u32.tobytes())


def dma_buf_read_words(buf: Dict[str, Any], n_words: int) -> np.ndarray:
    n_words_i = int(n_words)
    if n_words_i > int(buf["n_words"]):
        raise ValueError(f"DMA read exceeds buffer capacity: {n_words_i} > {buf['n_words']}")

    if buf["mode"] == "cma":
        arr = buf["arr"]
        if hasattr(arr, "invalidate"):
            arr.invalidate()
        return np.array(arr[:n_words_i], dtype=np.uint32, copy=True)
    if buf["mode"] == "xlnk":
        arr = buf["arr"]
        if hasattr(arr, "invalidate"):
            arr.invalidate()
        return np.array(arr[:n_words_i], dtype=np.uint32, copy=True)

    raw = buf["mmio"].read_bytes(0, n_words_i * 4)
    return np.frombuffer(raw, dtype=np.uint32).copy()


def dma_buf_clear(buf: Dict[str, Any], n_words: int) -> None:
    n_words_i = int(n_words)
    if n_words_i > int(buf["n_words"]):
        raise ValueError(f"DMA clear exceeds buffer capacity: {n_words_i} > {buf['n_words']}")

    if buf["mode"] == "cma":
        arr = buf["arr"]
        arr[:n_words_i] = 0
        if hasattr(arr, "flush"):
            arr.flush()
    elif buf["mode"] == "xlnk":
        arr = buf["arr"]
        arr[:n_words_i] = 0
        if hasattr(arr, "flush"):
            arr.flush()
    else:
        buf["mmio"].write_bytes(0, b"\x00" * (n_words_i * 4))


def dma_buf_close(buf: Dict[str, Any]) -> None:
    if buf["mode"] == "cma":
        arr = buf["arr"]
        if hasattr(arr, "freebuffer"):
            arr.freebuffer()
        elif hasattr(arr, "close"):
            arr.close()
    elif buf["mode"] == "xlnk":
        arr = buf["arr"]
        if hasattr(arr, "freebuffer"):
            arr.freebuffer()
        elif hasattr(arr, "close"):
            arr.close()
        xlnk = buf.get("xlnk")
        if xlnk is not None and hasattr(xlnk, "xlnk_reset"):
            # Best-effort cleanup for legacy CMA allocator.
            try:
                xlnk.xlnk_reset()
            except Exception:
                pass
    else:
        buf["mmio"].close()


def bit_to_bin(bitfile: str, binfile: str) -> int:
    with open(bitfile, "rb") as f:
        data = f.read()
    sync = bytes([0xAA, 0x99, 0x55, 0x66])
    idx = data.find(sync)
    if idx < 0:
        raise ValueError("Xilinx sync word not found in .bit file")
    raw = data[idx:]
    n = len(raw) & ~3
    swapped = bytearray(n)
    for i in range(0, n, 4):
        swapped[i] = raw[i + 3]
        swapped[i + 1] = raw[i + 2]
        swapped[i + 2] = raw[i + 1]
        swapped[i + 3] = raw[i]
    with open(binfile, "wb") as f:
        f.write(bytes(swapped))
    return n


def _try_program_with_pynq_overlay(bitfile: str) -> bool:
    """Try PYNQ Overlay programming first so pynq.allocate sees downloaded overlay."""
    try:
        from pynq import Overlay  # type: ignore
    except Exception as e:
        print(f"  INFO: PYNQ Overlay API unavailable ({e}); using fpga_manager")
        return False

    try:
        # Keep reference alive in module scope for runtime lifetime.
        global _ACTIVE_OVERLAY
        _ACTIVE_OVERLAY = Overlay(bitfile, download=True)
        print(f"  pynq Overlay download: {os.path.basename(bitfile)} (OK)")
        return True
    except Exception as e:
        print(f"  INFO: PYNQ Overlay download failed ({e}); using fpga_manager")
        return False


def program_fpga(bitfile: str) -> bool:
    if _try_program_with_pynq_overlay(bitfile):
        # Mirror legacy diagnostic line for consistency with existing logs.
        state = "unknown"
        try:
            with open("/sys/class/fpga_manager/fpga0/state") as f:
                state = f.read().strip()
        except Exception:
            pass
        print(f"  fpga_manager state: {state}")
        return state in ("operating", "unknown")

    binfile = bitfile.replace(".bit", ".bin")
    print(f"  bit→bin: {os.path.basename(bitfile)} → {os.path.basename(binfile)}")
    bit_to_bin(bitfile, binfile)
    fw_name = os.path.basename(binfile)
    fw_path = f"/lib/firmware/{fw_name}"
    with open(binfile, "rb") as src, open(fw_path, "wb") as dst:
        dst.write(src.read())
    with open("/sys/class/fpga_manager/fpga0/flags", "w") as f:
        f.write("0")
    with open("/sys/class/fpga_manager/fpga0/firmware", "w") as f:
        f.write(fw_name)
    time.sleep(1.5)
    with open("/sys/class/fpga_manager/fpga0/state") as f:
        state = f.read().strip()
    print(f"  fpga_manager state: {state}")
    return state == "operating"


def decode_hls_status(status: int) -> Dict[str, int]:
    return {
        "snn_ready": int(bool(status & (1 << 0))),
        "snn_busy": int(bool(status & (1 << 1))),
        "stdp_active": int(bool(status & (1 << 2))),
        "first_spike_only": int(bool(status & (1 << 3))),
        "rstdp_enable": int(bool(status & (1 << 4))),
        "encoder_enable": int(bool(status & (1 << 5))),
        "op_mode": int((status >> 6) & 0x3),
        "update_counter_8b": int((status >> 8) & 0xFF),
        "first_spike_pending": int(bool(status & (1 << 16))),
    }


def run_hls_oneshot(hls: MMIO, ctrl_word: int, mode: int = MODE_INFERENCE, timeout_s: float = 0.05) -> None:
    hls.write(HLS_AP_CTRL, 0x00)
    hls.write(HLS_MODE_REG, mode)
    hls.write(HLS_TIME_STEPS, 1)
    hls.write(HLS_CTRL_REG, ctrl_word)
    hls.write(HLS_AP_CTRL, 0x01)

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        ap = hls.read(HLS_AP_CTRL)
        if ap & 0x06:  # ap_done or ap_idle
            break
        time.sleep(_rt("hls_poll_s"))
    hls.write(HLS_AP_CTRL, 0x00)


def wait_hls_idle(hls: MMIO, timeout_s: float = 2.0) -> Tuple[bool, int]:
    """Wait until HLS ap_ctrl reports IDLE after a stop/reconfig sequence."""
    deadline = time.monotonic() + timeout_s
    last = 0
    while time.monotonic() < deadline:
        ap = hls.read(HLS_AP_CTRL)
        last = ap
        if ap & 0x04:  # ap_idle
            return True, ap
        time.sleep(_rt("hls_poll_s"))
    return False, last


def wait_hls_run_done(hls: MMIO, timeout_s: float = 2.0) -> Tuple[bool, int]:
    """Wait one ap_start launch to finish (robust against stale ap_done)."""
    deadline = time.monotonic() + timeout_s
    last = 0
    saw_busy = False
    while time.monotonic() < deadline:
        ap = hls.read(HLS_AP_CTRL)
        last = ap
        idle = bool(ap & 0x04)
        done = bool(ap & 0x02)
        if not idle:
            saw_busy = True
        # Preferred completion: observed busy and returned to idle.
        if saw_busy and idle:
            return True, ap
        # Fallback for very short launches: ap_done with start deasserted.
        if done and ((ap & 0x01) == 0):
            return True, ap
        time.sleep(_rt("hls_poll_s"))
    return False, last


def reset_system(hls: MMIO, assert_hls_reset: bool = False) -> None:
    if assert_hls_reset:
        run_hls_oneshot(hls, CTRL_RESET | CTRL_CLEAR, MODE_INFERENCE)
        run_hls_oneshot(hls, 0x00, MODE_INFERENCE)
    else:
        run_hls_oneshot(hls, CTRL_CLEAR, MODE_INFERENCE)
        run_hls_oneshot(hls, 0x00, MODE_INFERENCE)
    hls.write(HLS_CTRL_REG, 0x00)
    time.sleep(_rt("setup_sleep_s") * 2.0)


def warmup_hls(hls: MMIO, timeout_s: float = 0.4) -> None:
    hls.write(HLS_MODE_REG, MODE_INFERENCE)
    hls.write(HLS_TIME_STEPS, 1)
    hls.write(HLS_CTRL_REG, CTRL_ENABLE)
    hls.write(HLS_AP_CTRL, 0x01)
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        ap = hls.read(HLS_AP_CTRL)
        if ap & 0x06:
            break
        time.sleep(_rt("hls_poll_s"))
    hls.write(HLS_AP_CTRL, 0x00)
    hls.write(HLS_CTRL_REG, 0x00)
    time.sleep(_rt("setup_sleep_s") * 10.0)


def rearm_hls_datapath(hls: MMIO, timeout_s: float = 0.8) -> Tuple[int, int]:
    """
    Non-destructive HLS re-arm sequence after checkpoint/auto-restart phases.
    Keeps weights/traces intact while forcing AP_CTRL + mode back to a clean state.
    """
    hls.write(HLS_AP_CTRL, 0x00)
    hls.write(HLS_CTRL_REG, 0x00)
    hls.write(HLS_MODE_REG, MODE_INFERENCE)
    hls.write(HLS_TIME_STEPS, 1)
    time.sleep(_rt("setup_sleep_s"))
    # One-shot with ctrl=0 to clear stale ap_start/ap_done latches.
    run_hls_oneshot(hls, 0x00, MODE_INFERENCE, timeout_s=min(0.2, max(0.05, timeout_s)))
    hls.write(HLS_AP_CTRL, 0x00)
    hls.write(HLS_CTRL_REG, 0x00)
    hls.write(HLS_MODE_REG, MODE_INFERENCE)
    hls.write(HLS_TIME_STEPS, 1)
    idle_ok, ap_last = wait_hls_idle(hls, timeout_s=timeout_s)
    return int(idle_ok), int(ap_last)


def write_learning_params(
    hls: MMIO,
    a_plus: float,
    a_minus: float,
    tau_plus: int,
    tau_minus: int,
    stdp_window: int,
    learning_rate: float,
    rstdp_enable: bool,
    trace_decay: float,
    reward_scale: float,
) -> Tuple[int, int, int, int, int]:
    words = pack_learning_params_words(
        a_plus=a_plus,
        a_minus=a_minus,
        tau_plus=tau_plus,
        tau_minus=tau_minus,
        stdp_window=stdp_window,
        learning_rate=learning_rate,
        rstdp_enable=rstdp_enable,
        trace_decay=trace_decay,
        reward_scale=reward_scale,
    )
    for i, w in enumerate(words):
        hls.write(HLS_LEARNING_BASE + (i * 4), int(w))
    return words


def encode_conn(src: int, fanout: int, dest: int, weight: int, delay: int = 0, exc: bool = True) -> Tuple[int, int]:
    flat = src * MAX_FANOUT + fanout
    addr = (0x00 << 24) | (flat & 0x00_FFFF)

    if delay == 0:
        # dual-width compatible encoding (10b/11b router variants)
        w7 = ((weight & 0xFE) >> 1) & 0x7F
        data = 0
        data |= (dest & 0x7FF)
        data |= (w7 << 19)
        if exc:
            data |= (1 << 26)
        data |= (1 << 27)  # valid10 + exc11
        data |= (1 << 28)  # valid11
    else:
        n = ROUTER_NEURON_ID_W
        data = ((1) << (n + 17)) | ((1 if exc else 0) << (n + 16)) | ((weight & 0xFF) << (n + 8))
        data |= ((delay & 0xFF) << n) | (dest & ((1 << n) - 1))
    return addr, data


def encode_conn_count(src: int, count: int) -> Tuple[int, int]:
    addr = (0x01 << 24) | (src & 0x00_FFFF)
    return addr, count & 0xFF


def router_write(cfg: MMIO, addr: int, data: int) -> None:
    cfg.write(CFG_CONFIG_CTRL, 0)  # target router
    cfg.write(CFG_CONFIG_ADDR, addr & 0xFFFF_FFFF)
    cfg.write(CFG_CONFIG_WDATA, data & 0xFFFF_FFFF)
    time.sleep(_rt("router_rw_s"))


def router_read(cfg: MMIO, addr: int) -> int:
    cfg.write(CFG_CONFIG_CTRL, 0)
    cfg.write(CFG_CONFIG_ADDR, addr & 0xFFFF_FFFF)
    time.sleep(_rt("router_rw_s"))
    return cfg.read(CFG_CONFIG_RDATA)


def program_router_stdp(cfg: MMIO, pre_base: int, post_base: int, n_sources: int) -> None:
    # Clear source conn_count for pre and destination IDs to avoid recurrence.
    for i in range(n_sources):
        src = pre_base + i
        dst = post_base + i
        addr, data = encode_conn_count(src, 0)
        router_write(cfg, addr, data)
        addr, data = encode_conn_count(dst, 0)
        router_write(cfg, addr, data)

    for i in range(n_sources):
        src = pre_base + i
        dst = post_base + i
        ca, cd = encode_conn(src, 0, dst, 127, delay=0, exc=True)
        router_write(cfg, ca, cd)
        cca, ccd = encode_conn_count(src, 1)
        router_write(cfg, cca, ccd)


def verify_router_stdp(cfg: MMIO, pre_base: int, post_base: int, n_sources: int) -> Tuple[bool, List[Tuple[int, int, int, int, int, int, int]]]:
    if n_sources <= 0:
        return True, []
    idxs = sorted(set([0, n_sources // 2, n_sources - 1]))
    out = []
    ok = True
    nid_mask10 = (1 << 10) - 1
    nid_mask11 = (1 << 11) - 1

    for i in idxs:
        src = pre_base + i
        dst = post_base + i
        cnt_addr = (0x01 << 24) | (src & 0x00_FFFF)
        conn_addr = (0x00 << 24) | (((src * MAX_FANOUT) + 0) & 0x00_FFFF)
        cnt = router_read(cfg, cnt_addr) & 0xFF
        word = router_read(cfg, conn_addr)
        v10 = (word >> 27) & 0x1
        v11 = (word >> 28) & 0x1
        d10 = word & nid_mask10
        d11 = word & nid_mask11
        ok10 = (v10 == 1) and (d10 == (dst & nid_mask10))
        ok11 = (v11 == 1) and (d11 == (dst & nid_mask11))
        if cnt != 1 or not (ok10 or ok11):
            ok = False
        out.append((i, src, dst, cnt, v10, v11, word))
    return ok, out


def dma_soft_reset(dma: MMIO) -> None:
    dma.write(DMA_MM2S_DMACR, 0x04)
    time.sleep(_rt("dma_reset_s"))
    dma.write(DMA_S2MM_DMACR, 0x04)
    time.sleep(_rt("dma_reset_s"))
    dma.write(DMA_MM2S_DMASR, 0xFFFF_FFFF)
    dma.write(DMA_S2MM_DMASR, 0xFFFF_FFFF)


def wait_mm2s_done(dma: MMIO, timeout_s: float = 1.0) -> Tuple[bool, int]:
    deadline = time.monotonic() + timeout_s
    last = 0
    saw_active = False
    while time.monotonic() < deadline:
        sr = dma.read(DMA_MM2S_DMASR)
        last = sr
        if sr & 0x0050:
            return False, sr
        if sr & 0x1000:  # IOC
            return True, sr
        if (sr & 0x0002) == 0:  # Idle=0 -> channel actually running
            saw_active = True
        if saw_active and (sr & 0x0002):
            return True, sr
        time.sleep(_rt("dma_poll_s"))
    return False, last


def wait_s2mm_done(dma: MMIO, timeout_s: float = 2.0) -> Tuple[bool, int]:
    deadline = time.monotonic() + timeout_s
    last = 0
    while time.monotonic() < deadline:
        sr = dma.read(DMA_S2MM_DMASR)
        last = sr
        if sr & 0x0050:
            return False, sr
        if sr & 0x1000:  # IOC
            return True, sr
        time.sleep(_rt("dma_poll_s"))
    return False, last


def decode_checkpoint_words_into(
    words: np.ndarray,
    flat: np.ndarray,
    idx_seen: np.ndarray,
    prev_idx: int = -1,
) -> Tuple[int, int]:
    if words.size == 0:
        return 0, int(prev_idx)

    wi = words.astype(np.uint32, copy=False)
    idx_all = (wi & np.uint32(0xFFFFF)).astype(np.int64)
    valid = idx_all < int(flat.size)
    if not np.any(valid):
        return 0, int(prev_idx)

    idx = idx_all[valid]
    # HLS checkpoint packet uses packed signed weights (SNN_WEIGHT_BITS, e.g. 4-bit)
    # in data[20 + WEIGHT_BITS - 1 : 20]. Decode with sign extension accordingly.
    w_raw = ((wi >> np.uint32(20)) & np.uint32(PACKED_WORD_MASK)).astype(np.int16, copy=False)
    w_signed = np.where(
        (w_raw & np.int16(PACKED_WORD_SIGN)) != 0,
        w_raw - np.int16(1 << PACKED_WORD_BITS),
        w_raw,
    ).astype(np.int16, copy=False)
    wv = w_signed[valid]

    # Checkpoint stream is sequential and unique per full capture. Vectorized
    # scatter drastically reduces Python-side overhead on PYNQ ARM CPUs.
    flat[idx] = wv
    idx_seen[idx] = 1

    seq_errors = 0
    pidx = int(prev_idx)
    if idx.size > 0:
        if pidx >= 0 and int(idx[0]) != ((pidx + 1) % flat.size):
            seq_errors += 1
        if idx.size > 1:
            expected = (idx[:-1] + 1) % flat.size
            seq_errors += int(np.count_nonzero(idx[1:] != expected))
        pidx = int(idx[-1])
    return int(seq_errors), int(pidx)


def infer_checkpoint_format(
    checkpoint_words: int,
    weight_byte_nonzero: int,
    index_only_words: int,
    raw_weight_byte_nonzero: Optional[int] = None,
    raw_weight_byte_nonzero_shift24: Optional[int] = None,
) -> str:
    """
    Return a compact checkpoint payload format label for logs/results.
    """
    total = int(max(0, checkpoint_words))
    wb_nz = int(max(0, weight_byte_nonzero))
    raw_nz = int(max(0, wb_nz if raw_weight_byte_nonzero is None else raw_weight_byte_nonzero))
    raw24_nz = int(max(0, 0 if raw_weight_byte_nonzero_shift24 is None else raw_weight_byte_nonzero_shift24))
    idx_only = int(max(0, index_only_words))
    if total == 0:
        return "empty"
    if raw_nz == 0 and raw24_nz > 0:
        return "packed-weight@24"
    if idx_only >= total and raw_nz == 0:
        return "index-only"
    return "packed-weight"


def run_stdp_chunk(
    hls: MMIO,
    cfg: MMIO,
    dma_spike: MMIO,
    buf_in: Dict[str, Any],
    spike_words: np.ndarray,
    apply_reward: bool = False,
    first_spike_only: bool = True,
    rearm_first_spike_per_run: bool = False,
    post_flush_runs: int = 0,
    buf_out_spikes: Optional[Dict[str, Any]] = None,
    capture_out_words: int = 0,
    out_id_width: int = 13,
) -> Dict[str, object]:
    n_words = int(len(spike_words))
    nbytes = n_words * 4

    ap_ctrl_pre = hls.read(HLS_AP_CTRL)
    mode_reg_pre = hls.read(HLS_MODE_REG)
    hls_status_pre = hls.read(HLS_STATUS_REG)
    upd8_pre = int((hls_status_pre >> 8) & 0xFF)
    wsum_pre = hls.read(HLS_WEIGHT_SUM)
    ctr_router_pre = cfg.read(CFG_ROUTER_SPKS)
    ctr_neuron_pre = cfg.read(CFG_NEURON_SPKS)
    hls_in_pre = hls.read(HLS_SPIKE_COUNT)

    dma_buf_write_words(buf_in, spike_words)
    dma_soft_reset(dma_spike)

    cap_words = 0
    out_ok = 0
    out_sr = 0
    out_nonzero_words = 0
    out_first_ids: List[int] = []
    out_first_words_hex: List[str] = []
    if buf_out_spikes is not None and int(capture_out_words) > 0:
        cap_words = int(min(int(capture_out_words), int(buf_out_spikes["n_words"])))
        if cap_words > 0:
            dma_buf_clear(buf_out_spikes, cap_words)
            dma_spike.write(DMA_S2MM_DMASR, 0xFFFF_FFFF)
            dma_spike.write(DMA_S2MM_DMACR, 0x01)
            dma_spike.write(DMA_S2MM_DA, dma_buf_paddr(buf_out_spikes))
            dma_spike.write(DMA_S2MM_LENGTH, cap_words * 4)

    # Force a clean transition out of any prior checkpoint stream run.
    hls.write(HLS_AP_CTRL, 0x00)
    hls.write(HLS_CTRL_REG, 0x00)
    idle_ok_pre, ap_idle_pre = wait_hls_idle(hls, timeout_s=2.0)
    rearm_used = 0
    if not idle_ok_pre:
        rearm_used = 1
        idle_ok_fix, ap_fix = rearm_hls_datapath(hls, timeout_s=1.0)
        if idle_ok_fix:
            idle_ok_pre = True
            ap_idle_pre = ap_fix
    hls.write(HLS_MODE_REG, MODE_INFERENCE)
    hls.write(HLS_TIME_STEPS, 1)
    time.sleep(_rt("setup_sleep_s"))

    # In STDP parity runs, output spike DMA is not the metric. first_spike_only
    # can reduce output-stream backpressure stalls on some integrated builds.
    hls_ctrl = CTRL_ENABLE | CTRL_LEARNING_EN
    if first_spike_only:
        hls_ctrl |= CTRL_FIRST_SPIKE_ONLY
    if apply_reward:
        hls_ctrl |= CTRL_APPLY_REWARD
    hls.write(HLS_MODE_REG, MODE_TRAIN_STDP)
    # Keep one timestep per HLS launch for compatibility with deployed
    # integrated builds that expose spike_in_* via ap_none level signals.
    # This preserves one-packet-per-run semantics without auto_restart.
    hls.write(HLS_TIME_STEPS, 1)
    hls.write(HLS_CTRL_REG, hls_ctrl)
    mode_reg_cfg = hls.read(HLS_MODE_REG)
    hls_status_cfg = hls.read(HLS_STATUS_REG)

    dma_spike.write(DMA_MM2S_DMACR, 0x01)
    dma_spike.write(DMA_MM2S_SA, dma_buf_paddr(buf_in))
    dma_spike.write(DMA_MM2S_LENGTH, nbytes)
    # Deterministic finite-run launch:
    # avoid long auto-restart windows that can over-consume level-style
    # spike_out_valid on some integrated builds.
    ap_ctrl_start = 0
    run_count = 0
    rearm_runs = 0
    mm2s_ok = False
    mm2s_sr = 0
    consumed = 0
    router_delta = 0
    neuron_delta = 0
    upd8_delta = 0
    upd8_now = upd8_pre
    expected_upd8_delta = int(min(255, max(0, 2 * n_words)))
    wait_start = time.monotonic()
    settle_deadline = wait_start + max(_rt("settle_min_s"), n_words * _rt("settle_per_word_s"))
    last_progress_at = wait_start
    max_runs = max(2, n_words + 2)

    while run_count < max_runs:
        if first_spike_only and rearm_first_spike_per_run:
            # In first-spike-only mode, HLS latches first_spike_sent in static
            # state. Re-arm by running one short invocation with enable=0.
            hls.write(HLS_CTRL_REG, 0x00)
            hls.write(HLS_TIME_STEPS, 1)
            _ = hls.read(HLS_AP_CTRL)
            hls.write(HLS_AP_CTRL, 0x01)
            _ = wait_hls_run_done(hls, timeout_s=max(0.05, _rt("hls_poll_s") * 50.0))
            rearm_runs += 1
            hls.write(HLS_CTRL_REG, hls_ctrl)

        hls.write(HLS_TIME_STEPS, 1)
        _ = hls.read(HLS_AP_CTRL)  # clear stale ap_done
        hls.write(HLS_AP_CTRL, 0x01)  # one-shot start (no auto-restart)
        ap_ctrl_start = int(hls.read(HLS_AP_CTRL))
        run_count += 1

        # STDP update path can be slow on PYNQ-Z2; keep timeout conservative.
        run_timeout_s = max(0.5, min(2.0, _rt("settle_per_word_s") * 3.0))
        _run_ok, _run_ap = wait_hls_run_done(hls, timeout_s=run_timeout_s)

        hls_in_now = hls.read(HLS_SPIKE_COUNT)
        consumed = int(hls_in_now - hls_in_pre)
        router_now = cfg.read(CFG_ROUTER_SPKS)
        neuron_now = cfg.read(CFG_NEURON_SPKS)
        router_delta = int(router_now - ctr_router_pre)
        neuron_delta = int(neuron_now - ctr_neuron_pre)
        hs_now = hls.read(HLS_STATUS_REG)
        upd8_now = int((hs_now >> 8) & 0xFF)
        upd8_delta = int((upd8_now - upd8_pre) & 0xFF)

        sr_now = int(dma_spike.read(DMA_MM2S_DMASR))
        mm2s_sr = sr_now
        mm2s_ok = bool(sr_now & 0x1000)

        if (consumed > 0) or (router_delta > 0) or (neuron_delta > 0) or (upd8_delta > 0):
            last_progress_at = time.monotonic()

        input_done = consumed >= n_words
        flow_done = (router_delta >= n_words) and (neuron_delta >= n_words)
        if input_done and flow_done:
            break

        if time.monotonic() >= settle_deadline:
            break
        if mm2s_ok and (time.monotonic() - last_progress_at) > _rt("stall_timeout_s"):
            break
        time.sleep(_rt("hls_poll_s"))

    settle_wait_s = float(time.monotonic() - wait_start)
    consumed_complete = int(consumed >= n_words)
    if not mm2s_ok:
        mm2s_ok, mm2s_sr = wait_mm2s_done(dma_spike, timeout_s=max(0.5, n_words * 0.02))

    # Optional post-run flush: keep STDP mode enabled and run empty one-shots
    # so late post-spike/update pipeline stages can retire before shutdown.
    flush_runs_done = 0
    flush_runs_req = max(0, int(post_flush_runs))
    for _ in range(flush_runs_req):
        hls.write(HLS_TIME_STEPS, 1)
        _ = hls.read(HLS_AP_CTRL)
        hls.write(HLS_AP_CTRL, 0x01)
        ok_flush, _ = wait_hls_run_done(hls, timeout_s=max(0.1, _rt("hls_poll_s") * 200.0))
        if not ok_flush:
            break
        flush_runs_done += 1

    # Allow router/neuron pipeline to drain.
    time.sleep(_rt("post_chunk_drain_s"))

    if cap_words > 0 and buf_out_spikes is not None:
        out_ok_b, out_sr_i = wait_s2mm_done(dma_spike, timeout_s=max(0.2, n_words * 0.02))
        out_ok = int(out_ok_b)
        out_sr = int(out_sr_i)
        dma_spike.write(DMA_S2MM_DMACR, 0x00)
        out_words = dma_buf_read_words(buf_out_spikes, cap_words)
        nz = out_words[out_words != 0]
        out_nonzero_words = int(nz.size)
        if out_nonzero_words > 0:
            id_mask = (1 << max(1, int(out_id_width))) - 1
            for w in nz[:8]:
                wi = int(w)
                out_first_words_hex.append(f"0x{wi:08X}")
                out_first_ids.append(int(wi & id_mask))

    hls.write(HLS_AP_CTRL, 0x00)
    hls.write(HLS_CTRL_REG, 0x00)
    dma_spike.write(DMA_MM2S_DMACR, 0x00)
    idle_ok_post, ap_idle_post = wait_hls_idle(hls, timeout_s=max(0.5, _rt("stall_timeout_s") * 4.0))
    ap_ctrl_post = hls.read(HLS_AP_CTRL)
    mode_reg_post = hls.read(HLS_MODE_REG)

    ctr_router_post = cfg.read(CFG_ROUTER_SPKS)
    ctr_neuron_post = cfg.read(CFG_NEURON_SPKS)
    hls_in_post = hls.read(HLS_SPIKE_COUNT)
    hls_status = hls.read(HLS_STATUS_REG)
    wsum_post = hls.read(HLS_WEIGHT_SUM)
    upd8_post = int((hls_status >> 8) & 0xFF)
    upd8_final_delta = int((upd8_post - upd8_pre) & 0xFF)
    input_delta = int(hls_in_post - hls_in_pre)
    # update_counter increments on both pre- and post-spike processing in HLS.
    # With modulo-8b arithmetic, this estimates post events modulo 256.
    post_spikes_est = int((upd8_final_delta - input_delta) & 0xFF)

    return {
        "n_words": n_words,
        "run_count": int(run_count),
        "rearm_runs": int(rearm_runs),
        "post_flush_runs_req": int(flush_runs_req),
        "post_flush_runs_done": int(flush_runs_done),
        "mm2s_ok": int(mm2s_ok),
        "mm2s_sr": int(mm2s_sr),
        "expected_words": int(n_words),
        "consumed_complete": int(consumed_complete),
        "router_complete": int(router_delta >= n_words),
        "neuron_complete": int(neuron_delta >= n_words),
        "expected_update_delta_8b": int(expected_upd8_delta),
        "update_delta_8b": int(upd8_final_delta),
        "update_complete": int(upd8_final_delta >= expected_upd8_delta),
        "expected_post_spikes": int(n_words),
        "post_spikes_est_8b": int(post_spikes_est),
        "post_complete_est": int(post_spikes_est == n_words),
        "settle_wait_s": float(settle_wait_s),
        "router_spikes": int(ctr_router_post - ctr_router_pre),
        "neuron_spikes": int(ctr_neuron_post - ctr_neuron_pre),
        "hls_input_spikes": int(input_delta),
        "ap_ctrl_pre": int(ap_ctrl_pre),
        "ap_ctrl_start": int(ap_ctrl_start),
        "ap_ctrl_post": int(ap_ctrl_post),
        "mode_reg_pre": int(mode_reg_pre),
        "mode_reg_cfg": int(mode_reg_cfg),
        "mode_reg_post": int(mode_reg_post),
        "idle_ok_pre": int(idle_ok_pre),
        "ap_idle_pre": int(ap_idle_pre),
        "idle_ok_post": int(idle_ok_post),
        "ap_idle_post": int(ap_idle_post),
        "rearm_used": int(rearm_used),
        "hls_status_pre": int(hls_status_pre),
        "hls_status_cfg": int(hls_status_cfg),
        "hls_status": int(hls_status),
        "weight_sum_pre": int(wsum_pre),
        "weight_sum_post": int(wsum_post),
        "spike_out_capture_words": int(cap_words),
        "spike_out_s2mm_ok": int(out_ok),
        "spike_out_s2mm_sr": int(out_sr),
        "spike_out_nonzero_words": int(out_nonzero_words),
        "spike_out_first_ids": out_first_ids,
        "spike_out_first_words_hex": out_first_words_hex,
    }


def resolve_sw_post_ids_for_chunk(
    args,
    run_meta: Dict[str, object],
    synthetic_post_ids: np.ndarray,
    chunk_steps: int,
) -> Tuple[List[int], Dict[str, int]]:
    """
    Resolve SW post-spike replay IDs for this chunk.

    synthetic:
      Use deterministic post_id sequence (legacy behavior).
    captured:
      Use captured m_axis_spikes IDs (from --capture-out-spikes) when present.
      Missing captures can be skipped or synthetically backfilled.
    """
    mode = str(getattr(args, "sw_post_source", "synthetic")).strip().lower()
    if mode != "captured":
        return [int(x) for x in synthetic_post_ids[:chunk_steps]], {
            "sw_post_source_mode": 0,
            "sw_post_capture_count": 0,
            "sw_post_missing_count": 0,
            "sw_post_capture_fallback": 0,
            "sw_post_capture_skip_missing": 0,
        }

    captured = [int(x) for x in list(run_meta.get("spike_out_first_ids", []))]
    skip_missing = int(bool(getattr(args, "sw_skip_post_if_missing_capture", False)))
    out: List[int] = []
    missing = 0
    fallback = 0

    for k in range(int(chunk_steps)):
        if k < len(captured):
            out.append(int(captured[k]))
            continue
        missing += 1
        if skip_missing:
            # Sentinel -1 => caller skips SW post update for this step.
            out.append(-1)
        else:
            out.append(int(synthetic_post_ids[k]))
            fallback += 1

    return out, {
        "sw_post_source_mode": 1,
        "sw_post_capture_count": int(len(captured)),
        "sw_post_missing_count": int(missing),
        "sw_post_capture_fallback": int(fallback),
        "sw_post_capture_skip_missing": int(skip_missing),
    }


def read_weight_checkpoint(
    hls: MMIO,
    dma_weight: MMIO,
    buf_out: Dict[str, Any],
    n_words: int,
    timeout_s: float = 4.0,
    clear_buffer: bool = False,
) -> Tuple[np.ndarray, Dict[str, int]]:
    nbytes = int(n_words) * 4
    if nbytes <= 0:
        raise ValueError("n_words must be > 0")

    cap_words = int(buf_out["n_words"])
    if cap_words <= 0:
        raise ValueError("output DMA buffer capacity is zero")
    chunked_capture = bool(cap_words < n_words)
    burst_words = max(1, min(cap_words, 4096))
    mode_chunk_words = int(min(burst_words, 0xFFFF)) if chunked_capture else 0

    # Do NOT clear a multi-MB /dev/mem DDR region by default.
    # On some PYNQ Linux images, bulk writes to fixed physical addresses can
    # corrupt live kernel/user pages if that region is not fully reserved.
    if clear_buffer:
        dma_buf_clear(buf_out, min(n_words, cap_words))
    dma_soft_reset(dma_weight)

    # Snapshot HLS-side sum before checkpoint readback for diagnostics.
    wsum_hls_pre = int(hls.read(HLS_WEIGHT_SUM))

    # Force mode transition into checkpoint so checkpoint_idx resets.
    # First, stop and wait until HLS is truly idle (auto-restart can linger).
    hls.write(HLS_AP_CTRL, 0x00)
    hls.write(HLS_CTRL_REG, 0x00)
    idle_ok_pre, ap_idle_pre = wait_hls_idle(hls, timeout_s=max(1.0, timeout_s * 0.25))
    rearm_used = 0
    if not idle_ok_pre:
        rearm_used = 1
        ra_ok, ra_ap = rearm_hls_datapath(hls, timeout_s=max(0.5, timeout_s * 0.125))
        if ra_ok:
            idle_ok_pre = True
            ap_idle_pre = ra_ap
    hls.write(HLS_MODE_REG, MODE_INFERENCE)
    hls.write(HLS_TIME_STEPS, 1)
    time.sleep(_rt("setup_sleep_s"))

    ckpt_mode_reg = (int(mode_chunk_words) << 16) | int(MODE_CHECKPOINT)
    hls.write(HLS_MODE_REG, ckpt_mode_reg)
    hls.write(HLS_CTRL_REG, CTRL_ENABLE | CTRL_WEIGHT_READ)

    flat = np.zeros(n_words, dtype=np.int16)
    idx_seen = np.zeros(n_words, dtype=np.uint8)
    seq_errors = 0
    prev_idx = -1
    packets_collected = 0
    chunks = 0
    remaining_words_post_runs = 0
    last_sr = 0
    s2mm_ok = True
    sample_words_hex: List[str] = []
    weight_byte_nonzero = 0
    weight_byte_nonzero_raw8 = 0
    weight_byte_nonzero_raw8_shift16 = 0
    weight_byte_nonzero_raw8_shift24 = 0
    weight_high_nibble_nonzero = 0
    index_only_words = 0

    # Full-buffer path (CMA/Xlnk or explicitly unsafe devmem)
    if cap_words >= n_words:
        dma_weight.write(DMA_S2MM_DMASR, 0xFFFF_FFFF)
        dma_weight.write(DMA_S2MM_DMACR, 0x01)
        dma_weight.write(DMA_S2MM_DA, dma_buf_paddr(buf_out))
        dma_weight.write(DMA_S2MM_LENGTH, nbytes)

        # Avoid sticky auto-restart mode across runtime phases.
        # Launch finite runs with exact remaining words so HLS can return idle
        # immediately after the final capture-completing run.
        remaining_words = int(n_words)
        need_runs = (remaining_words + 0xFFFF - 1) // 0xFFFF
        max_runs = max(need_runs + 4, 8)
        runs = 0
        while remaining_words > 0 and runs < max_runs:
            this_run_words = int(min(remaining_words, 0xFFFF))
            hls.write(HLS_TIME_STEPS, this_run_words)
            # Clear stale ap_done before arming a new run.
            _ = hls.read(HLS_AP_CTRL)
            hls.write(HLS_AP_CTRL, 0x01)
            # Be conservative on integrated boards: one HLS run can be much
            # slower than nominal depending on downstream backpressure/clocking.
            per_run_timeout = max(2.0, timeout_s * 4.0)
            run_ok, _ = wait_hls_run_done(hls, timeout_s=per_run_timeout)
            runs += 1
            chunks = runs
            if not run_ok:
                s2mm_ok = False
                break
            remaining_words -= this_run_words

            sr = dma_weight.read(DMA_S2MM_DMASR)
            last_sr = int(sr)
            if sr & 0x0050:
                s2mm_ok = False
                break

        remaining_words_post_runs = int(remaining_words)
        if s2mm_ok and remaining_words > 0:
            s2mm_ok = False
        if s2mm_ok:
            if (last_sr & 0x1000) == 0:
                s2mm_ok, last_sr = wait_s2mm_done(dma_weight, timeout_s=timeout_s)

        dma_weight.write(DMA_S2MM_DMACR, 0x00)
        words = dma_buf_read_words(buf_out, n_words)
        if not sample_words_hex:
            sample_words_hex = [f"0x{int(x):08X}" for x in words[:8]]
        wi = words.astype(np.uint32, copy=False)
        w_raw8 = ((wi >> np.uint32(20)) & np.uint32(0xFF)).astype(np.uint32, copy=False)
        w_raw8_s16 = ((wi >> np.uint32(16)) & np.uint32(0xFF)).astype(np.uint32, copy=False)
        w_raw8_s24 = ((wi >> np.uint32(24)) & np.uint32(0xFF)).astype(np.uint32, copy=False)
        weight_byte_nonzero_raw8 = int(np.count_nonzero(w_raw8))
        weight_byte_nonzero_raw8_shift16 = int(np.count_nonzero(w_raw8_s16))
        weight_byte_nonzero_raw8_shift24 = int(np.count_nonzero(w_raw8_s24))
        weight_byte_nonzero = int(np.count_nonzero(w_raw8 & np.uint32(PACKED_WORD_MASK)))
        weight_high_nibble_nonzero = int(np.count_nonzero(w_raw8 & np.uint32(0xF0)))
        index_only_words = int(np.count_nonzero(w_raw8 == 0))
        se_inc, prev_idx = decode_checkpoint_words_into(words, flat, idx_seen, prev_idx)
        seq_errors += se_inc
        packets_collected += int(n_words)
    else:
        # Segmented capture path for small devmem windows: repeatedly arm S2MM
        # with a safe window size and accumulate by explicit packet index field.
        expected_chunks = (n_words + burst_words - 1) // burst_words
        max_chunks = max(expected_chunks * 6, expected_chunks + 16)

        # Chunked mode uses HLS-side chunk TLAST (mode_reg[31:16]) + auto-restart.
        hls.write(HLS_TIME_STEPS, 1)
        hls.write(HLS_AP_CTRL, 0x81)
        while chunks < max_chunks:
            dma_weight.write(DMA_S2MM_DMASR, 0xFFFF_FFFF)
            dma_weight.write(DMA_S2MM_DMACR, 0x01)
            dma_weight.write(DMA_S2MM_DA, dma_buf_paddr(buf_out))
            dma_weight.write(DMA_S2MM_LENGTH, burst_words * 4)
            ok_i, sr_i = wait_s2mm_done(dma_weight, timeout_s=max(timeout_s, 0.5))
            dma_weight.write(DMA_S2MM_DMACR, 0x00)
            chunks += 1
            last_sr = int(sr_i)
            if not ok_i:
                s2mm_ok = False
                break
            words = dma_buf_read_words(buf_out, burst_words)
            if not sample_words_hex:
                sample_words_hex = [f"0x{int(x):08X}" for x in words[:8]]
            wi = words.astype(np.uint32, copy=False)
            w_raw8 = ((wi >> np.uint32(20)) & np.uint32(0xFF)).astype(np.uint32, copy=False)
            w_raw8_s16 = ((wi >> np.uint32(16)) & np.uint32(0xFF)).astype(np.uint32, copy=False)
            w_raw8_s24 = ((wi >> np.uint32(24)) & np.uint32(0xFF)).astype(np.uint32, copy=False)
            weight_byte_nonzero_raw8 += int(np.count_nonzero(w_raw8))
            weight_byte_nonzero_raw8_shift16 += int(np.count_nonzero(w_raw8_s16))
            weight_byte_nonzero_raw8_shift24 += int(np.count_nonzero(w_raw8_s24))
            weight_byte_nonzero += int(np.count_nonzero(w_raw8 & np.uint32(PACKED_WORD_MASK)))
            weight_high_nibble_nonzero += int(np.count_nonzero(w_raw8 & np.uint32(0xF0)))
            index_only_words += int(np.count_nonzero(w_raw8 == 0))
            se_inc, prev_idx = decode_checkpoint_words_into(words, flat, idx_seen, prev_idx)
            seq_errors += se_inc
            packets_collected += int(burst_words)
            if np.all(idx_seen):
                break

    hls.write(HLS_AP_CTRL, 0x00)
    hls.write(HLS_CTRL_REG, 0x00)
    idle_ok, ap_last = wait_hls_idle(hls, timeout_s=max(1.0, timeout_s))
    wsum_hls_post = int(hls.read(HLS_WEIGHT_SUM))
    missing = int(np.sum(idx_seen == 0))
    flat_sum = int(np.sum(flat.astype(np.int64), dtype=np.int64))
    meta = {
        "s2mm_ok": int(s2mm_ok),
        "s2mm_sr": int(last_sr),
        "hls_idle_pre_ok": int(idle_ok_pre),
        "hls_ap_pre": int(ap_idle_pre),
        "hls_rearm_used": int(rearm_used),
        "hls_idle_ok": int(idle_ok),
        "hls_ap_last": int(ap_last),
        "checkpoint_words": int(n_words),
        "buffer_capacity_words": int(cap_words),
        "chunked_capture": int(chunked_capture),
        "chunk_words": int(mode_chunk_words),
        "chunks": int(chunks),
        "remaining_words_post_runs": int(remaining_words_post_runs),
        "packets_collected": int(packets_collected),
        "missing_indices": int(missing),
        "sequence_errors": int(seq_errors),
        "weight_field_bits": int(PACKED_WORD_BITS),
        "weight_byte_nonzero": int(weight_byte_nonzero),
        "weight_byte_nonzero_raw8": int(weight_byte_nonzero_raw8),
        "weight_byte_nonzero_raw8_shift16": int(weight_byte_nonzero_raw8_shift16),
        "weight_byte_nonzero_raw8_shift24": int(weight_byte_nonzero_raw8_shift24),
        "weight_byte_nonzero_decoded": int(weight_byte_nonzero),
        "weight_high_nibble_nonzero": int(weight_high_nibble_nonzero),
        "packed_decode_all_zero": int((weight_byte_nonzero == 0) and (weight_byte_nonzero_raw8 > 0)),
        "index_only_words": int(index_only_words),
        "weight_sum_checkpoint": int(flat_sum),
        "weight_sum_hls_pre": int(wsum_hls_pre),
        "weight_sum_hls_post": int(wsum_hls_post),
        "checkpoint_format": infer_checkpoint_format(
            int(n_words),
            int(weight_byte_nonzero),
            int(index_only_words),
            raw_weight_byte_nonzero=int(weight_byte_nonzero_raw8),
            raw_weight_byte_nonzero_shift24=int(weight_byte_nonzero_raw8_shift24),
        ),
        "sample_words_hex": sample_words_hex,
    }
    return flat, meta


def stream_weight_load_packets(
    hls: MMIO,
    dma_weight: MMIO,
    buf_in: Dict[str, Any],
    words: np.ndarray,
    timeout_s: float = 2.0,
) -> Dict[str, int]:
    """
    Stream packed weight-load packets through DMA1 MM2S -> HLS s_axis_weights.
    HLS consumes at most one packet per invocation in current implementation.
    """
    n_words = int(len(words))
    if n_words <= 0:
        return {
            "n_words": 0,
            "run_count": 0,
            "run_done_count": 0,
            "mm2s_ok": 1,
            "mm2s_sr": 0,
            "idle_ok": 1,
            "ap_last": int(hls.read(HLS_AP_CTRL)),
        }
    if int(buf_in["n_words"]) < n_words:
        raise RuntimeError(
            f"weight-load buffer too small: need {n_words} words, have {int(buf_in['n_words'])}"
        )

    dma_buf_write_words(buf_in, words.astype(np.uint32, copy=False))
    dma_soft_reset(dma_weight)

    hls.write(HLS_AP_CTRL, 0x00)
    hls.write(HLS_CTRL_REG, 0x00)
    hls.write(HLS_MODE_REG, MODE_INFERENCE)
    hls.write(HLS_TIME_STEPS, 1)
    time.sleep(_rt("setup_sleep_s"))

    hls.write(HLS_CTRL_REG, CTRL_ENABLE | CTRL_WEIGHT_LOAD)
    dma_weight.write(DMA_MM2S_DMASR, 0xFFFF_FFFF)
    dma_weight.write(DMA_MM2S_DMACR, 0x01)
    dma_weight.write(DMA_MM2S_SA, dma_buf_paddr(buf_in))
    dma_weight.write(DMA_MM2S_LENGTH, n_words * 4)

    # IMPORTANT:
    # MM2S IOC can assert before HLS has consumed all words from the AXIS input
    # staging path. Do not stop launches solely on IOC. Launch enough one-shot
    # runs so HLS can drain up to one packet per invocation.
    run_limit = max(8, (n_words * 2) + 4)
    run_done_count = 0
    run_count = 0
    ap_last = 0
    mm2s_sr = 0
    for _ in range(run_limit):
        hls.write(HLS_TIME_STEPS, 1)
        _ = hls.read(HLS_AP_CTRL)  # clear stale ap_done
        hls.write(HLS_AP_CTRL, 0x01)
        run_count += 1
        run_ok, ap_last = wait_hls_run_done(hls, timeout_s=max(0.1, _rt("settle_per_word_s")))
        if run_ok:
            run_done_count += 1
        mm2s_sr = int(dma_weight.read(DMA_MM2S_DMASR))
        if (mm2s_sr & 0x0050) != 0:
            break
        time.sleep(_rt("hls_poll_s"))

    mm2s_ok, mm2s_sr_done = wait_mm2s_done(dma_weight, timeout_s=max(timeout_s, n_words * 0.05))
    mm2s_sr = int(mm2s_sr_done if mm2s_sr_done != 0 else mm2s_sr)

    dma_weight.write(DMA_MM2S_DMACR, 0x00)
    hls.write(HLS_AP_CTRL, 0x00)
    hls.write(HLS_CTRL_REG, 0x00)
    idle_ok, ap_idle = wait_hls_idle(hls, timeout_s=max(0.2, timeout_s))

    return {
        "n_words": int(n_words),
        "run_count": int(run_count),
        "run_done_count": int(run_done_count),
        "mm2s_ok": int(mm2s_ok),
        "mm2s_sr": int(mm2s_sr),
        "idle_ok": int(idle_ok),
        "ap_last": int(ap_idle),
    }


def run_checkpoint_weight_smoke(
    hls: MMIO,
    dma_weight: MMIO,
    buf_weight_in: Dict[str, Any],
    buf_weight_out: Dict[str, Any],
    n_weight_words: int,
    pre_base: int,
    post_base: int,
    id_width: int,
    sample_count: int = 8,
) -> Dict[str, Any]:
    """
    Isolated checkpoint-path smoke test:
      1) Load known non-zero weights via s_axis_weights (DMA1 MM2S).
      2) Capture full checkpoint via m_axis_weights (DMA1 S2MM).
      3) Verify loaded indices contain expected values.
    """
    count = max(1, int(sample_count))
    sample_weights = [1, 2, 3, 4, 5, 6, 7]
    samples: List[Dict[str, int]] = []
    packets: List[int] = []

    for i in range(count):
        pre_id = int(pre_base)
        post_id = int(post_base + i)
        idx = flat_weight_index(pre_id, post_id)
        if idx is None:
            continue
        w = int(sample_weights[i % len(sample_weights)])
        samples.append(
            {
                "pre_id": int(pre_id),
                "post_id": int(post_id),
                "index": int(idx),
                "expected": int(clip_weight_packed(w)),
            }
        )
        packets.append(encode_weight_load_word(pre_id, post_id, w, id_width))

    if not samples:
        return {
            "ok": 0,
            "reason": "no_valid_samples",
            "samples": [],
            "load_meta": {"mm2s_ok": 0},
            "checkpoint_meta": {"s2mm_ok": 0},
        }

    pkt_arr = np.array(packets, dtype=np.uint32)
    load_meta = stream_weight_load_packets(hls, dma_weight, buf_weight_in, pkt_arr, timeout_s=2.0)
    hw_ckpt, ckpt_meta = read_weight_checkpoint(
        hls, dma_weight, buf_weight_out, int(n_weight_words), timeout_s=8.0, clear_buffer=False
    )

    match_count = 0
    for s in samples:
        idx = int(s["index"])
        hwv = int(hw_ckpt[idx]) if 0 <= idx < int(hw_ckpt.size) else 0
        s["hw"] = int(hwv)
        s["match"] = int(hwv == int(s["expected"]))
        match_count += int(s["match"])

    ok = int(
        int(load_meta.get("mm2s_ok", 0)) == 1
        and int(ckpt_meta.get("s2mm_ok", 0)) == 1
        and match_count == len(samples)
    )
    return {
        "ok": int(ok),
        "sample_count": int(len(samples)),
        "match_count": int(match_count),
        "samples": samples,
        "load_meta": load_meta,
        "checkpoint_meta": ckpt_meta,
    }


def decode_weight_index(idx: int) -> Optional[Dict[str, int]]:
    for conn in CONNECTIONS:
        off = int(conn.get("weight_offset", -1))
        num = int(conn.get("num_weights", 0))
        if off < 0 or num <= 0:
            continue
        if off <= idx < off + num:
            local = idx - off
            dst_size = int(conn.get("dst_size", 1))
            if dst_size <= 0:
                dst_size = 1

            src0 = conn.get("src_id_start", None)
            dst0 = conn.get("dst_id_start", None)
            if src0 is None:
                sg = conn.get("src_group", None)
                if sg is not None and 0 <= int(sg) < len(NEURON_GROUP_ID_START) - 1:
                    src0 = int(NEURON_GROUP_ID_START[int(sg)])
            if dst0 is None:
                dg = conn.get("dst_group", None)
                if dg is not None and 0 <= int(dg) < len(NEURON_GROUP_ID_START) - 1:
                    dst0 = int(NEURON_GROUP_ID_START[int(dg)])

            entry: Dict[str, int] = {
                "connection": str(conn.get("name", f"offset_{off}")),
                "offset": off,
            }
            if src0 is not None and dst0 is not None:
                entry["pre_id"] = int(src0) + (local // dst_size)
                entry["post_id"] = int(dst0) + (local % dst_size)
            return entry
    return None


def clip_weight_packed(weight: int) -> int:
    w = int(weight)
    if w > int(PACKED_MAX_WEIGHT):
        return int(PACKED_MAX_WEIGHT)
    if w < int(PACKED_MIN_WEIGHT):
        return int(PACKED_MIN_WEIGHT)
    return w


def _conn_global_start(conn: Dict[str, Any], key_id_start: str, key_group: str) -> Optional[int]:
    v = conn.get(key_id_start, None)
    if v is not None:
        return int(v)
    g = conn.get(key_group, None)
    if g is None:
        return None
    gi = int(g)
    if 0 <= gi < (len(NEURON_GROUP_ID_START) - 1):
        return int(NEURON_GROUP_ID_START[gi])
    return None


def flat_weight_index(pre_id: int, post_id: int) -> Optional[int]:
    pre = int(pre_id)
    post = int(post_id)
    for conn in CONNECTIONS:
        off = int(conn.get("weight_offset", -1))
        src_size = int(conn.get("src_size", 0))
        dst_size = int(conn.get("dst_size", 0))
        if off < 0 or src_size <= 0 or dst_size <= 0:
            continue
        src0 = _conn_global_start(conn, "src_id_start", "src_group")
        dst0 = _conn_global_start(conn, "dst_id_start", "dst_group")
        if src0 is None or dst0 is None:
            continue
        if not (src0 <= pre < (src0 + src_size)):
            continue
        if not (dst0 <= post < (dst0 + dst_size)):
            continue
        local_pre = pre - src0
        local_post = post - dst0
        return int(off + local_pre * dst_size + local_post)
    return None


def encode_weight_load_word(pre_id: int, post_id: int, weight: int, id_width: int) -> int:
    """
    Pack one s_axis_weights word for HLS weight_load mode.

    With 32-bit AXIS and id_width=13, only lower packed bits are representable
    in the weight field. For SNN_WEIGHT_BITS=4 this maps cleanly to [29:26].
    """
    idw = int(id_width)
    if idw <= 0:
        raise ValueError("id_width must be > 0")
    weight_shift = 2 * idw
    if weight_shift >= 32:
        raise ValueError(f"id_width too large for 32-bit packet: {idw}")
    id_mask = (1 << idw) - 1
    # Keep weight packing consistent with configured packed-weight width while
    # respecting the remaining packet bit budget.
    rem_bits = max(1, 32 - weight_shift)
    w_bits = min(PACKED_WORD_BITS, rem_bits)
    w_mask = (1 << w_bits) - 1
    wc = clip_weight_packed(weight)
    if wc < 0:
        w_raw = ((1 << w_bits) + wc) & w_mask
    else:
        w_raw = wc & w_mask
    word = (int(pre_id) & id_mask)
    word |= (int(post_id) & id_mask) << idw
    word |= (int(w_raw) & w_mask) << weight_shift
    return int(word & 0xFFFF_FFFF)


def compare_flat_weights(hw: np.ndarray, sw: np.ndarray, max_report: int = 20) -> Dict[str, object]:
    mism_idx = np.flatnonzero(hw.astype(np.int16) != sw.astype(np.int16))
    report = []
    for idx in mism_idx[:max_report]:
        idx_i = int(idx)
        entry = {
            "idx": idx_i,
            "hw": int(hw[idx_i]),
            "sw": int(sw[idx_i]),
        }
        info = decode_weight_index(idx_i)
        if info is not None:
            entry.update(info)
        report.append(entry)
    return {
        "equal": int(len(mism_idx) == 0),
        "mismatch_count": int(len(mism_idx)),
        "first_mismatches": report,
    }


def checkpoint_payload_is_index_only(meta: Optional[Dict[str, Any]]) -> bool:
    """
    Detect the pathological checkpoint stream where only packet index is present
    (data[19:0]) and the packed weight field is effectively always zero.
    """
    if not meta:
        return False
    fmt = str(meta.get("checkpoint_format", "")).strip().lower()
    if fmt == "index-only":
        return True
    if fmt.startswith("packed-weight"):
        return False

    total = int(meta.get("checkpoint_words", 0))
    if total <= 0:
        return False
    idx_only = int(meta.get("index_only_words", 0))
    raw_nz = int(meta.get("weight_byte_nonzero_raw8", meta.get("weight_byte_nonzero", 0)))
    return (idx_only >= total) and (raw_nz == 0)


def build_pre_sequence(n_steps: int, n_sources: int, pattern: str, seed: int) -> np.ndarray:
    if n_steps <= 0:
        return np.zeros(0, dtype=np.int32)
    if pattern == "random":
        rng = np.random.default_rng(seed)
        return rng.integers(low=0, high=n_sources, size=n_steps, dtype=np.int32)
    return (np.arange(n_steps, dtype=np.int32) % max(1, n_sources)).astype(np.int32)


def parse_args():
    p = argparse.ArgumentParser(description="On-board STDP checkpoint parity harness")
    p.add_argument("--data", default="/home/xilinx/snn", help="Directory containing bitstream")
    p.add_argument("--bitstream", default=None, help="Override bitstream path")
    p.add_argument("--no-program", action="store_true", help="Skip FPGA programming")
    p.add_argument("--output", default=None, help="JSON output path")
    p.add_argument("--n-steps", type=int, default=32, help="Number of STDP steps")
    p.add_argument("--checkpoint-every", type=int, default=1,
                   help="Checkpoint compare interval in steps (1=sample-wise, 0=final only)")
    p.add_argument("--run-chunk-steps", type=int, default=0,
                   help="Execution/log chunk size in steps (0: auto, no effect on checkpoint cadence)")
    p.add_argument("--pattern", choices=["cycle", "random"], default="cycle", help="Pre-spike sequence pattern")
    p.add_argument("--seed", type=int, default=1, help="Random seed for pattern=random")
    p.add_argument("--packet-id-width", type=int, default=13, help="HLS packet neuron-id width")
    p.add_argument("--pre-base", type=int, default=0, help="Source neuron base ID")
    p.add_argument("--post-base", type=int, default=784, help="Destination neuron base ID")
    p.add_argument("--n-sources", type=int, default=196, help="Number of source IDs to map")
    p.add_argument("--threshold", type=int, default=120, help="Global threshold")
    p.add_argument("--leak", type=int, default=0, help="Global leak rate")
    p.add_argument("--refrac", type=int, default=0, help="Global refractory period")
    p.add_argument("--a-plus", type=float, default=1.0)
    p.add_argument("--a-minus", type=float, default=1.0)
    p.add_argument("--tau-plus", type=int, default=20)
    p.add_argument("--tau-minus", type=int, default=20)
    p.add_argument("--stdp-window", type=int, default=50)
    p.add_argument("--learning-rate", type=float, default=1.0)
    p.add_argument("--trace-decay", type=float, default=0.0,
                   help="Use 0.0 for timestamp-insensitive strict parity")
    p.add_argument("--reward-scale", type=float, default=1.0)
    p.add_argument("--rstdp-enable", action="store_true")
    p.add_argument("--reward-signal", type=int, default=0)
    p.add_argument("--no-first-spike-only", action="store_true",
                   help="Disable ctrl_reg bit7 during STDP run (debug: may increase output backpressure)")
    p.add_argument("--assert-hls-reset", action="store_true")
    p.add_argument("--check-hls-version", action="store_true")
    p.add_argument("--runtime-profile", choices=["fast", "balanced", "low-cpu"], default="balanced",
                   help="Host-side polling/wait profile (CPU vs runtime trade-off)")
    p.add_argument("--hls-poll-ms", type=float, default=None,
                   help="Override HLS AP/status polling interval in milliseconds")
    p.add_argument("--dma-poll-ms", type=float, default=None,
                   help="Override DMA status polling interval in milliseconds")
    p.add_argument("--router-rw-us", type=float, default=None,
                   help="Override router cfg read/write settle delay in microseconds")
    p.add_argument("--dma-reset-ms", type=float, default=None,
                   help="Override DMA soft-reset settle delay in milliseconds")
    p.add_argument("--setup-sleep-ms", type=float, default=None,
                   help="Override short setup sleep used around mode/control transitions (milliseconds)")
    p.add_argument("--settle-min-ms", type=float, default=None,
                   help="Minimum post-MM2S settle wait per chunk (milliseconds)")
    p.add_argument("--settle-per-word-ms", type=float, default=None,
                   help="Additional settle wait per input word (milliseconds)")
    p.add_argument("--stall-timeout-ms", type=float, default=None,
                   help="No-progress timeout after MM2S done before closing chunk wait (milliseconds)")
    p.add_argument("--post-chunk-drain-ms", type=float, default=None,
                   help="Post-chunk pipeline drain sleep before reading counters (milliseconds)")
    p.add_argument("--post-flush-runs", type=int, default=0,
                   help="Additional empty one-shot HLS runs after each chunk (before shutdown)")
    p.add_argument("--capture-out-spikes", action="store_true",
                   help="Capture a small m_axis_spikes sample via DMA0 S2MM for post-ID diagnostics")
    p.add_argument("--out-capture-words", type=int, default=64,
                   help="Number of 32-bit words to capture from m_axis_spikes when --capture-out-spikes is set")
    p.add_argument("--out-id-width", type=int, default=13,
                   help="Neuron-ID width used to decode captured m_axis_spikes packet IDs")
    p.add_argument("--sw-post-source", choices=["synthetic", "captured"], default="synthetic",
                   help="SW replay post-spike source: synthetic(post_base+pattern) or captured(--capture-out-spikes)")
    p.add_argument("--sw-skip-post-if-missing-capture", action="store_true",
                   help="With --sw-post-source captured, skip SW post update when captured IDs are insufficient")
    p.add_argument("--rearm-first-spike-per-run", dest="rearm_first_spike_per_run", action="store_true",
                   help="Enable per-run first-spike re-arm shim (debug; can perturb post-spike accounting)")
    p.add_argument("--no-rearm-first-spike-per-run", dest="rearm_first_spike_per_run", action="store_false",
                   help=argparse.SUPPRESS)
    p.set_defaults(rearm_first_spike_per_run=False)
    p.add_argument("--checkpoint-smoke", action="store_true",
                   help="Run isolated weight-load->checkpoint smoke test before STDP parity run")
    p.add_argument("--checkpoint-smoke-only", action="store_true",
                   help="Run only checkpoint smoke test and exit")
    p.add_argument("--checkpoint-smoke-count", type=int, default=8,
                   help="Number of synthetic sample weights used by --checkpoint-smoke")
    p.add_argument("--strict", action="store_true",
                   help="Exit non-zero on any mismatch/counter anomaly")
    p.add_argument("--clear-checkpoint-buffer", action="store_true",
                   help="Zero-fill checkpoint DDR buffer before capture (off by default for board safety)")
    p.add_argument("--no-cma-buffers", action="store_true",
                   help="Disable PYNQ CMA buffers and use fixed /dev/mem physical addresses")
    p.add_argument("--no-cma-spike-buffer", action="store_true",
                   help="Force spike_in MM2S buffer to fixed /dev/mem (checkpoint buffer remains CMA by default)")
    p.add_argument("--no-cma-checkpoint-buffer", action="store_true",
                   help="Force checkpoint S2MM buffer to fixed /dev/mem (not recommended except debug)")
    p.add_argument("--devmem-chunk-words", type=int, default=4096,
                   help="When using devmem fallback, map this many words for segmented checkpoint capture")
    p.add_argument("--unsafe-devmem-checkpoint", action="store_true",
                   help="Allow large checkpoint buffer on fixed /dev/mem physical address (can crash board)")
    return p.parse_args()


def main():
    args = parse_args()
    runtime_tuning = configure_runtime_tuning(args)
    sep = "=" * 72
    print(sep)
    print("On-board STDP Parity Harness (HW checkpoint vs SW bit-accurate)")
    print(sep)
    print(
        "Runtime tuning:"
        f" profile={args.runtime_profile}"
        f" hls_poll={runtime_tuning['hls_poll_s']*1e3:.3f}ms"
        f" dma_poll={runtime_tuning['dma_poll_s']*1e3:.3f}ms"
        f" settle_min={runtime_tuning['settle_min_s']*1e3:.1f}ms"
        f" settle_per_word={runtime_tuning['settle_per_word_s']*1e3:.3f}ms"
        f" stall={runtime_tuning['stall_timeout_s']*1e3:.1f}ms"
        f" first_spike_only={int(not args.no_first_spike_only)}"
    )
    if (
        str(getattr(args, "sw_post_source", "synthetic")).strip().lower() == "captured"
        and (not bool(args.no_first_spike_only))
        and (not bool(args.rearm_first_spike_per_run))
    ):
        print(
            "NOTE: sw_post_source=captured with first_spike_only=1 and rearm=0 can miss captures.\n"
            "      HW may still consume post spikes while SW skips missing captures."
        )

    bit_path = args.bitstream or os.path.join(args.data, "snn_integrated_v2.bit")
    out_path = args.output or os.path.join(args.data, "stdp_parity_results.json")
    hwh_path = os.path.splitext(bit_path)[0] + ".hwh"

    if args.n_steps <= 0:
        print("ERROR: --n-steps must be > 0")
        sys.exit(1)
    if args.n_sources <= 0:
        print("ERROR: --n-sources must be > 0")
        sys.exit(1)

    # Keep routing IDs in safe shared range for 10b/11b router variants.
    router_id_limit = 1 << ROUTER_NEURON_ID_W
    if (args.pre_base + args.n_sources) > router_id_limit or (args.post_base + args.n_sources) > router_id_limit:
        print(f"ERROR: source/post ID range exceeds router 10-bit limit ({router_id_limit})")
        print("       Choose values so pre_base+n_sources and post_base+n_sources are <= 1024")
        sys.exit(1)

    if not args.no_program:
        print(f"\nProgramming FPGA: {bit_path}")
        if not os.path.exists(bit_path):
            print(f"ERROR: bitstream not found: {bit_path}")
            sys.exit(1)
        if not program_fpga(bit_path):
            print("ERROR: FPGA programming failed")
            sys.exit(1)
    else:
        print("\n(--no-program: skipping FPGA programming)")

    hls_visible_limit: Optional[int] = None
    if os.path.exists(hwh_path):
        hls_visible_limit = detect_hls_visible_offset_limit(hwh_path, HLS_BASE)
        dma1_ok = detect_dma_present(hwh_path, "axi_dma_1", DMA_WEIGHT_BASE)
        if hls_visible_limit is not None:
            print(f"  HLS AXI-Lite visible offsets: 0x00..0x{hls_visible_limit:02X} (from {os.path.basename(hwh_path)})")
        else:
            print(f"  HLS AXI-Lite visible range: unknown (could not parse {os.path.basename(hwh_path)})")
        if not dma1_ok:
            print("ERROR: axi_dma_1@0x41E10000 not found in HWH. STDP checkpoint parity requires weight DMA.")
            sys.exit(1)
    else:
        print(f"  WARNING: HWH not found: {hwh_path} (skipping address-map preflight)")

    hls = MMIO(HLS_BASE, 0x1000)
    cfg = MMIO(CFG_BASE, 0x1000)
    dma_spike = MMIO(DMA_SPIKE_BASE, 0x1000)
    dma_weight = MMIO(DMA_WEIGHT_BASE, 0x1000)

    n_weight_words = int(MAX_WEIGHT_BUFFER_SIZE)
    weight_bytes = n_weight_words * 4
    prefer_cma_default = not bool(args.no_cma_buffers)
    prefer_cma_spike = prefer_cma_default and (not bool(args.no_cma_spike_buffer))
    prefer_cma_ckpt = prefer_cma_default and (not bool(args.no_cma_checkpoint_buffer))
    buf_spike_out: Optional[Dict[str, Any]] = None
    buf_weight_in: Optional[Dict[str, Any]] = None
    try:
        buf_spike = alloc_dma_buffer(
            max(args.n_steps, 1),
            DMA_BUF_SPIKES_IN,
            prefer_cma=prefer_cma_spike,
            tag="spike_in",
            allow_unsafe_devmem=True,  # small buffer; safe fallback
        )
        buf_wout = alloc_dma_buffer(
            n_weight_words,
            0x1F010000,
            prefer_cma=prefer_cma_ckpt,
            tag="weight_ckpt_out",
            allow_unsafe_devmem=bool(args.unsafe_devmem_checkpoint),
            devmem_window_words=int(args.devmem_chunk_words) if int(args.devmem_chunk_words) > 0 else None,
        )
        if bool(args.capture_out_spikes):
            buf_spike_out = alloc_dma_buffer(
                max(1, int(args.out_capture_words)),
                DMA_BUF_SPIKES_OUT,
                prefer_cma=prefer_cma_spike,
                tag="spike_out_dbg",
                allow_unsafe_devmem=True,  # small buffer; safe fallback
            )
        if bool(args.checkpoint_smoke) or bool(args.checkpoint_smoke_only):
            buf_weight_in = alloc_dma_buffer(
                max(1, int(args.checkpoint_smoke_count)),
                DMA_BUF_WEIGHTS_IN,
                prefer_cma=prefer_cma_spike,
                tag="weight_load_in",
                allow_unsafe_devmem=True,  # small buffer; safe fallback
            )
    except RuntimeError as e:
        print(f"ERROR: {e}")
        print("       Try sourcing XRT/PYNQ environment, or (unsafe) add --unsafe-devmem-checkpoint")
        hls.close()
        cfg.close()
        dma_spike.close()
        dma_weight.close()
        sys.exit(1)
    print(
        f"  DMA buffers: spike_in={buf_spike['mode']}@0x{dma_buf_paddr(buf_spike):08X}, "
        f"weight_out={buf_wout['mode']}@0x{dma_buf_paddr(buf_wout):08X} "
        f"(mapped={buf_wout['nbytes']}B, requested={weight_bytes}B)"
    )
    if buf_spike_out is not None:
        print(
            f"  spike_out debug buffer: {buf_spike_out['mode']}@0x{dma_buf_paddr(buf_spike_out):08X} "
            f"({buf_spike_out['nbytes']}B, words={buf_spike_out['n_words']})"
        )
    if buf_weight_in is not None:
        print(
            f"  weight_load debug buffer: {buf_weight_in['mode']}@0x{dma_buf_paddr(buf_weight_in):08X} "
            f"({buf_weight_in['nbytes']}B, words={buf_weight_in['n_words']})"
        )
    if int(buf_wout["n_words"]) < n_weight_words:
        print(
            f"  segmented checkpoint capture enabled "
            f"(window_words={buf_wout['n_words']}, total_words={n_weight_words})"
        )

    cfg_ver = cfg.read(CFG_VERSION)
    print(f"  snn_config_regs version: 0x{cfg_ver:08X} ({'OK' if cfg_ver == EXPECTED_CFG_VERSION else 'UNEXPECTED'})")
    if cfg_ver != EXPECTED_CFG_VERSION:
        print("ERROR: snn_config_regs version mismatch (fabric/IP likely not active).")
        if args.no_program:
            print("       You used --no-program, but FPGA appears unprogrammed or stale.")
            print("       Re-run once WITHOUT --no-program to load snn_integrated_v2.bit.")
        else:
            print("       Check bitstream/.hwh pair and FPGA programming state.")
        hls.close()
        cfg.close()
        dma_spike.close()
        dma_weight.close()
        dma_buf_close(buf_spike)
        dma_buf_close(buf_wout)
        if buf_spike_out is not None:
            dma_buf_close(buf_spike_out)
        if buf_weight_in is not None:
            dma_buf_close(buf_weight_in)
        sys.exit(1)
    hls_ver: Optional[int] = None
    hls_version_check_supported = not (
        hls_visible_limit is not None and HLS_VERSION_REG > hls_visible_limit
    )
    if args.check_hls_version:
        if not hls_version_check_supported:
            print(
                f"  hls version_reg: (SKIPPED; offset 0x{HLS_VERSION_REG:02X} exceeds AXI-Lite visible range)"
            )
        else:
            print("  hls version_reg: (deferred until after warm-up)")
    else:
        print("  hls version_reg: (SKIPPED; use --check-hls-version to enable)")

    print("\nWarm-up HLS ...")
    warmup_hls(hls)
    print("  Done.")

    if args.check_hls_version and hls_version_check_supported:
        # version_reg is an output scalar with ap_vld; read after at least one
        # completed invocation so the value is latched and software-visible.
        hls_ver = hls.read(HLS_VERSION_REG)
        if hls_ver == 0:
            time.sleep(0.001)
            hls_ver = hls.read(HLS_VERSION_REG)
        ver_ok = (hls_ver == EXPECTED_HLS_VERSION)
        print(f"  hls version_reg: 0x{hls_ver:08X} ({'OK' if ver_ok else 'UNEXPECTED'})")
        if (not ver_ok) and bool(args.strict):
            print("ERROR: HLS version mismatch in strict mode; aborting parity run.")
            print(
                f"       expected=0x{EXPECTED_HLS_VERSION:08X} got=0x{hls_ver:08X}"
            )
            print(
                "       This usually means stale/mismatched bitstream vs HLS package."
            )
            hls.close()
            cfg.close()
            dma_spike.close()
            dma_weight.close()
            dma_buf_close(buf_spike)
            dma_buf_close(buf_wout)
            if buf_spike_out is not None:
                dma_buf_close(buf_spike_out)
            if buf_weight_in is not None:
                dma_buf_close(buf_weight_in)
            sys.exit(1)

    print("\nReset + router setup ...")
    reset_system(hls, assert_hls_reset=args.assert_hls_reset)
    program_router_stdp(cfg, args.pre_base, args.post_base, args.n_sources)
    cfg.write(CFG_THRESHOLD, int(args.threshold) & 0xFFFF)
    cfg.write(CFG_NEURON_PARAMS, (int(args.refrac) & 0xFF) << 8 | (int(args.leak) & 0xFF))
    hls.write(HLS_CONFIG_REG, ((int(args.leak) & 0xFFFF) << 16) | (int(args.threshold) & 0xFFFF))
    verify_ok, verify_rows = verify_router_stdp(cfg, args.pre_base, args.post_base, args.n_sources)
    print(f"  Router readback: {'OK' if verify_ok else 'WARNING'}")
    for (i, src, dst, cnt, v10, v11, word) in verify_rows:
        print(f"    i={i:3d} src={src:4d} dst={dst:4d} cnt={cnt:2d} v10={v10} v11={v11} word=0x{word:08X}")
    if not verify_ok:
        print("ERROR: Router programming/readback failed; aborting before checkpoint DMA.")
        print("       Confirm bitstream is loaded and snn_config_regs responds correctly.")
        hls.close()
        cfg.close()
        dma_spike.close()
        dma_weight.close()
        dma_buf_close(buf_spike)
        dma_buf_close(buf_wout)
        if buf_spike_out is not None:
            dma_buf_close(buf_spike_out)
        if buf_weight_in is not None:
            dma_buf_close(buf_weight_in)
        sys.exit(1)

    lp_words = write_learning_params(
        hls,
        a_plus=args.a_plus,
        a_minus=args.a_minus,
        tau_plus=args.tau_plus,
        tau_minus=args.tau_minus,
        stdp_window=args.stdp_window,
        learning_rate=args.learning_rate,
        rstdp_enable=bool(args.rstdp_enable),
        trace_decay=args.trace_decay,
        reward_scale=args.reward_scale,
    )
    # Reward register can be outside PS-visible AXI-Lite range on some integrated builds.
    # In plain STDP mode (rstdp_enable=0, reward=0) this write is unnecessary.
    need_reward_write = bool(args.rstdp_enable) or (int(args.reward_signal) != 0)
    if need_reward_write:
        if hls_visible_limit is not None and HLS_REWARD_SIGNAL > hls_visible_limit:
            print(
                f"  WARNING: reward_signal offset 0x{HLS_REWARD_SIGNAL:02X} is outside "
                f"AXI-Lite visible range 0x00..0x{hls_visible_limit:02X}; skipping reward write"
            )
        else:
            hls.write(HLS_REWARD_SIGNAL, int(args.reward_signal) & 0xFF)
    print("  learning_params words:", " ".join([f"0x{w:08X}" for w in lp_words]))

    smoke_report: Optional[Dict[str, Any]] = None
    if bool(args.checkpoint_smoke) or bool(args.checkpoint_smoke_only):
        if buf_weight_in is None:
            print("ERROR: internal: checkpoint-smoke requested but weight_load buffer is missing")
            hls.close()
            cfg.close()
            dma_spike.close()
            dma_weight.close()
            dma_buf_close(buf_spike)
            dma_buf_close(buf_wout)
            if buf_spike_out is not None:
                dma_buf_close(buf_spike_out)
            sys.exit(1)
        print("\nCheckpoint smoke (MM2S weight-load -> S2MM checkpoint) ...")
        smoke_report = run_checkpoint_weight_smoke(
            hls=hls,
            dma_weight=dma_weight,
            buf_weight_in=buf_weight_in,
            buf_weight_out=buf_wout,
            n_weight_words=n_weight_words,
            pre_base=int(args.pre_base),
            post_base=int(args.post_base),
            id_width=int(args.packet_id_width),
            sample_count=int(args.checkpoint_smoke_count),
        )
        sm_load = smoke_report.get("load_meta", {})
        sm_ckpt = smoke_report.get("checkpoint_meta", {})
        print(
            f"  smoke: ok={int(smoke_report.get('ok', 0))} "
            f"samples={int(smoke_report.get('sample_count', 0))} "
            f"match={int(smoke_report.get('match_count', 0))} "
            f"load_mm2s={int(sm_load.get('mm2s_ok', 0))} "
            f"ckpt_s2mm={int(sm_ckpt.get('s2mm_ok', 0))} "
            f"fmt={str(sm_ckpt.get('checkpoint_format', 'n/a'))}"
        )
        for s in list(smoke_report.get("samples", []))[:8]:
            print(
                f"    idx={int(s.get('index', -1))} pre={int(s.get('pre_id', -1))} "
                f"post={int(s.get('post_id', -1))} exp={int(s.get('expected', 0))} "
                f"hw={int(s.get('hw', 0))} match={int(s.get('match', 0))}"
            )
        if bool(args.strict) and bool(args.checkpoint_smoke) and int(smoke_report.get("ok", 0)) != 1:
            print("ERROR: checkpoint-smoke failed in strict mode; aborting parity run.")
            hls.close()
            cfg.close()
            dma_spike.close()
            dma_weight.close()
            dma_buf_close(buf_spike)
            dma_buf_close(buf_wout)
            if buf_spike_out is not None:
                dma_buf_close(buf_spike_out)
            if buf_weight_in is not None:
                dma_buf_close(buf_weight_in)
            sys.exit(2)
        if bool(args.checkpoint_smoke_only):
            summary = {
                "mode": "checkpoint_smoke_only",
                "strict": bool(args.strict),
                "cfg_version": int(cfg_ver),
                "hls_version": int(hls_ver) if hls_ver is not None else None,
                "runtime_profile": str(args.runtime_profile),
                "runtime_tuning": {k: float(v) for k, v in runtime_tuning.items()},
                "checkpoint_smoke": smoke_report,
            }
            with open(out_path, "w") as f:
                json.dump(summary, f, indent=2)
            print(f"\nSaved: {out_path}")
            hls.close()
            cfg.close()
            dma_spike.close()
            dma_weight.close()
            dma_buf_close(buf_spike)
            dma_buf_close(buf_wout)
            if buf_spike_out is not None:
                dma_buf_close(buf_spike_out)
            if buf_weight_in is not None:
                dma_buf_close(buf_weight_in)
            if bool(args.strict) and int(smoke_report.get("ok", 0)) != 1:
                sys.exit(2)
            return

    print("\nCheckpointing initial HW flat weights ...")
    hw_init, init_meta = read_weight_checkpoint(
        hls, dma_weight, buf_wout, n_weight_words, timeout_s=8.0,
        clear_buffer=bool(args.clear_checkpoint_buffer)
    )
    print(
        f"  init checkpoint: s2mm_ok={init_meta['s2mm_ok']} "
        f"missing={init_meta['missing_indices']} seq_err={init_meta['sequence_errors']} "
        f"chunk_words={init_meta.get('chunk_words', 0)} "
        f"hls_idle={init_meta.get('hls_idle_ok', 0)} ap=0x{init_meta.get('hls_ap_last', 0):08X} "
        f"wbyte_nz={init_meta.get('weight_byte_nonzero', 0)}/{init_meta.get('weight_byte_nonzero_raw8', 0)} "
        f"idx_only={init_meta.get('index_only_words', 0)} "
        f"wsum(ckpt/hls)=({init_meta.get('weight_sum_checkpoint', 0)}/"
        f"{init_meta.get('weight_sum_hls_post', 0)})"
    )
    if int(init_meta.get("s2mm_ok", 0)) != 1 or int(init_meta.get("missing_indices", n_weight_words)) != 0:
        print("ERROR: Initial checkpoint capture is incomplete; aborting STDP parity run.")
        print(
            f"       s2mm_ok={int(init_meta.get('s2mm_ok', 0))} "
            f"missing_indices={int(init_meta.get('missing_indices', n_weight_words))} "
            f"sequence_errors={int(init_meta.get('sequence_errors', 0))}"
        )
        if int(init_meta.get("chunked_capture", 0)) == 1:
            print(
                "       chunked_capture=1: current platform is using segmented checkpoint DMA. "
                "If S2MM never completes, enable CMA/Xlnk allocator (recommended) or review TLAST/stream framing."
            )
        if str(buf_wout.get("mode", "")) == "devmem":
            print(
                "       DMA buffer mode=devmem. For full checkpoint parity, CMA/Xlnk-backed contiguous buffer is required."
            )
        hls.close()
        cfg.close()
        dma_spike.close()
        dma_weight.close()
        dma_buf_close(buf_spike)
        dma_buf_close(buf_wout)
        if buf_spike_out is not None:
            dma_buf_close(buf_spike_out)
        if buf_weight_in is not None:
            dma_buf_close(buf_weight_in)
        sys.exit(2 if args.strict else 1)
    if int(init_meta.get("hls_idle_ok", 0)) != 1:
        # Some integrated/runtime combinations can leave AP_START latched
        # (ap_ctrl=0x00000001) right after segmented checkpoint capture even
        # though checkpoint data is complete. Try a non-destructive datapath
        # re-arm before declaring failure.
        print("WARN: HLS not IDLE after checkpoint capture; trying datapath re-arm ...")
        print(f"      ap_ctrl(last)=0x{int(init_meta.get('hls_ap_last', 0)):08X}")
        rearm_ok, rearm_ap = rearm_hls_datapath(hls, timeout_s=1.0)
        init_meta["hls_idle_rearm_ok"] = int(rearm_ok)
        init_meta["hls_ap_rearm"] = int(rearm_ap)
        if int(rearm_ok) != 1:
            # On some fallback/devmem segmented-capture paths, AP_START can
            # remain latched after a complete checkpoint transfer. If strict
            # reset is requested, continue and let the explicit reset+rearm
            # sequence below recover the datapath.
            can_continue = (
                bool(args.assert_hls_reset)
                and int(init_meta.get("chunked_capture", 0)) == 1
                and int(init_meta.get("s2mm_ok", 0)) == 1
                and int(init_meta.get("missing_indices", n_weight_words)) == 0
            )
            if can_continue:
                print("WARN: HLS re-arm failed after checkpoint capture, but checkpoint is complete.")
                print("      Continuing with assert-hls-reset recovery path.")
                print(f"      ap_ctrl(rearm)=0x{int(rearm_ap):08X}")
                init_meta["hls_idle_rearm_force_continue"] = 1
            else:
                print("ERROR: HLS re-arm failed after checkpoint capture; aborting STDP parity run.")
                print(f"       ap_ctrl(rearm)=0x{int(rearm_ap):08X}")
                hls.close()
                cfg.close()
                dma_spike.close()
                dma_weight.close()
                dma_buf_close(buf_spike)
                dma_buf_close(buf_wout)
                if buf_spike_out is not None:
                    dma_buf_close(buf_spike_out)
                if buf_weight_in is not None:
                    dma_buf_close(buf_weight_in)
                sys.exit(2 if args.strict else 1)

    # Re-arm datapath after checkpoint streaming before STDP traffic injection.
    # This avoids sticky checkpoint-mode state on some integrated runtime builds.
    print("Re-arming STDP datapath after initial checkpoint ...")
    reset_system(hls, assert_hls_reset=args.assert_hls_reset)
    program_router_stdp(cfg, args.pre_base, args.post_base, args.n_sources)
    hls.write(HLS_CONFIG_REG, ((int(args.leak) & 0xFFFF) << 16) | (int(args.threshold) & 0xFFFF))
    _ = write_learning_params(
        hls,
        a_plus=args.a_plus,
        a_minus=args.a_minus,
        tau_plus=args.tau_plus,
        tau_minus=args.tau_minus,
        stdp_window=args.stdp_window,
        learning_rate=args.learning_rate,
        rstdp_enable=bool(args.rstdp_enable),
        trace_decay=args.trace_decay,
        reward_scale=args.reward_scale,
    )
    hls.write(HLS_AP_CTRL, 0x00)
    hls.write(HLS_CTRL_REG, 0x00)
    hls.write(HLS_MODE_REG, MODE_INFERENCE)
    hls.write(HLS_TIME_STEPS, 1)
    time.sleep(_rt("setup_sleep_s"))

    # Build deterministic input sequence and words.
    pre_local = build_pre_sequence(args.n_steps, args.n_sources, args.pattern, args.seed)
    pre_ids = pre_local + int(args.pre_base)
    post_ids = pre_local + int(args.post_base)
    pkt_id_mask = (1 << int(args.packet_id_width)) - 1
    pkt_wgt_shift = int(args.packet_id_width)
    spike_words = ((pre_ids & pkt_id_mask).astype(np.uint32) | (np.uint32(0x7F) << np.uint32(pkt_wgt_shift))).astype(np.uint32)

    # SW reference engine
    sw_cfg = STDPConfig(
        a_plus=float(args.a_plus),
        a_minus=float(args.a_minus),
        tau_plus=float(args.tau_plus),
        tau_minus=float(args.tau_minus),
        stdp_window=int(args.stdp_window),
        learning_rate=float(args.learning_rate),
        rstdp_enable=bool(args.rstdp_enable),
        trace_decay=float(args.trace_decay),
        reward_scale=float(args.reward_scale),
    )
    sw = HWAccurateSTDPEngine(sw_cfg, max_neurons=2048)
    sw.set_flat_weights(hw_init.astype(np.int16))

    print(
        f"\nRunning STDP {args.n_steps} steps "
        f"(checkpoint_every={args.checkpoint_every}, trace_decay={args.trace_decay}) ..."
    )
    apply_reward = bool(args.rstdp_enable and int(args.reward_signal) != 0)
    if apply_reward:
        print(f"  R-STDP reward active each step (reward_signal={int(args.reward_signal)})")
    t0 = time.time()
    steps_done = 0
    chunk_idx = 0
    chunk_logs: List[Dict[str, object]] = []
    final_cmp: Dict[str, object] = {"equal": 0, "mismatch_count": n_weight_words, "first_mismatches": []}
    run_chunk_steps = int(args.run_chunk_steps) if int(args.run_chunk_steps) > 0 else 0
    ckpt_every = int(args.checkpoint_every) if int(args.checkpoint_every) > 0 else 0
    next_ckpt_step = ckpt_every if ckpt_every > 0 else None

    while steps_done < args.n_steps:
        if run_chunk_steps > 0:
            chunk = min(run_chunk_steps, args.n_steps - steps_done)
        elif ckpt_every > 0:
            chunk = min(ckpt_every, args.n_steps - steps_done)
        else:
            chunk = args.n_steps - steps_done

        sl = slice(steps_done, steps_done + chunk)
        chunk_words = spike_words[sl]
        run_meta = run_stdp_chunk(
            hls, cfg, dma_spike, buf_spike, chunk_words,
            apply_reward=apply_reward,
            first_spike_only=(not bool(args.no_first_spike_only)),
            rearm_first_spike_per_run=(
                bool(args.rearm_first_spike_per_run)
                and (not bool(args.no_first_spike_only))
                and bool(args.capture_out_spikes)
            ),
            post_flush_runs=max(0, int(args.post_flush_runs)),
            buf_out_spikes=buf_spike_out,
            capture_out_words=(int(args.out_capture_words) if bool(args.capture_out_spikes) else 0),
            out_id_width=int(args.out_id_width),
        )

        # Replay step sequence in SW reference.
        sw_post_ids_chunk, sw_post_meta = resolve_sw_post_ids_for_chunk(
            args=args,
            run_meta=run_meta,
            synthetic_post_ids=post_ids[sl],
            chunk_steps=chunk,
        )
        for k in range(chunk):
            t = steps_done + k
            sw.process_pre_spike(int(pre_ids[t]), t)
            post_id_k = int(sw_post_ids_chunk[k])
            if post_id_k >= 0:
                sw.process_post_spike(post_id_k, t)
            if apply_reward:
                sw.apply_rstdp_reward(int(args.reward_signal), t)

        chunk_end = steps_done + chunk
        do_checkpoint = False
        if chunk_end == args.n_steps:
            do_checkpoint = True
        elif next_ckpt_step is not None and chunk_end >= next_ckpt_step:
            do_checkpoint = True
            while next_ckpt_step is not None and chunk_end >= next_ckpt_step:
                next_ckpt_step += ckpt_every
        cmp_meta: Optional[Dict[str, object]] = None
        ckpt_meta: Optional[Dict[str, int]] = None

        if do_checkpoint:
            hw_ckpt, ckpt_meta = read_weight_checkpoint(
                hls, dma_weight, buf_wout, n_weight_words, timeout_s=8.0,
                clear_buffer=bool(args.clear_checkpoint_buffer)
            )
            sw_ckpt = np.clip(sw._flat_weights.astype(np.int16), PACKED_MIN_WEIGHT, PACKED_MAX_WEIGHT).astype(np.int16)
            cmp_meta = compare_flat_weights(hw_ckpt, sw_ckpt, max_report=20)
            # Extra diagnostics for index-space mismatches:
            # when run-path counters are healthy but final parity fails, we need
            # to know whether HW updated a different region or did not update.
            hw_nz_idx = np.flatnonzero(hw_ckpt.astype(np.int16) != 0)
            sw_nz_idx = np.flatnonzero(sw_ckpt.astype(np.int16) != 0)
            both_nz = np.intersect1d(hw_nz_idx, sw_nz_idx, assume_unique=False)
            cmp_meta["nonzero_summary"] = {
                "hw_nonzero_count": int(hw_nz_idx.size),
                "sw_nonzero_count": int(sw_nz_idx.size),
                "overlap_nonzero_count": int(both_nz.size),
                "hw_nonzero_first10": [int(x) for x in hw_nz_idx[:10]],
                "sw_nonzero_first10": [int(x) for x in sw_nz_idx[:10]],
            }
            final_cmp = cmp_meta
            # Intermediate checkpoints leave some builds in sticky checkpoint/AP state.
            # Re-arm before next STDP chunk without resetting learning state.
            if (steps_done + chunk) < args.n_steps:
                ra_ok, ra_ap = rearm_hls_datapath(hls, timeout_s=1.0)
                if ckpt_meta is None:
                    ckpt_meta = {}
                ckpt_meta["post_ckpt_rearm_ok"] = int(ra_ok)
                ckpt_meta["post_ckpt_rearm_ap"] = int(ra_ap)

        chunk_log = {
            "chunk_idx": chunk_idx,
            "start_step": int(steps_done),
            "end_step": int(steps_done + chunk - 1),
            "chunk_steps": int(chunk),
            "run_meta": run_meta,
            "sw_post_meta": sw_post_meta,
            "checkpoint_meta": ckpt_meta,
            "compare": cmp_meta,
        }
        chunk_logs.append(chunk_log)

        msg = (
            f"  chunk#{chunk_idx:03d} steps[{steps_done}:{steps_done + chunk - 1}] "
            f"router={run_meta['router_spikes']} neuron={run_meta['neuron_spikes']} "
            f"hls_in={run_meta['hls_input_spikes']} "
            f"runs={run_meta.get('run_count', 0)} "
            f"rearm={run_meta.get('rearm_runs', 0)} "
            f"flush={run_meta.get('post_flush_runs_done', 0)}/{run_meta.get('post_flush_runs_req', 0)} "
            f"mm2s_ok={run_meta['mm2s_ok']} mm2s_sr=0x{run_meta['mm2s_sr']:08X} "
            f"consumed={run_meta.get('hls_input_spikes', 0)}/{run_meta.get('expected_words', 0)} "
            f"done={run_meta.get('consumed_complete', 0)} "
            f"flow={run_meta.get('router_complete', 0)}/{run_meta.get('neuron_complete', 0)} "
            f"upd8={run_meta.get('update_delta_8b', 0)}/{run_meta.get('expected_update_delta_8b', 0)} "
            f"upd_done={run_meta.get('update_complete', 0)} "
            f"post_est={run_meta.get('post_spikes_est_8b', 0)}/{run_meta.get('expected_post_spikes', 0)} "
            f"post_ok={run_meta.get('post_complete_est', 0)} "
            f"mode(pre/cfg/post)=0x{run_meta.get('mode_reg_pre', 0):08X}/"
            f"0x{run_meta.get('mode_reg_cfg', 0):08X}/0x{run_meta.get('mode_reg_post', 0):08X} "
            f"ap(pre/start/post)=0x{run_meta.get('ap_ctrl_pre', 0):08X}/"
            f"0x{run_meta.get('ap_ctrl_start', 0):08X}/0x{run_meta.get('ap_ctrl_post', 0):08X} "
            f"idle_pre={run_meta.get('idle_ok_pre', 0)} ap_idle=0x{run_meta.get('ap_idle_pre', 0):08X} "
            f"idle_post={run_meta.get('idle_ok_post', 0)} ap_post=0x{run_meta.get('ap_idle_post', 0):08X}"
        )
        msg += (
            f" hs_pre=0x{run_meta.get('hls_status_pre', 0):08X}"
            f" hs_cfg=0x{run_meta.get('hls_status_cfg', 0):08X}"
            f" hs_post=0x{run_meta.get('hls_status', 0):08X}"
            f" wsum={run_meta.get('weight_sum_pre', 0)}->{run_meta.get('weight_sum_post', 0)}"
        )
        if int(run_meta.get("spike_out_capture_words", 0)) > 0:
            out_ids = run_meta.get("spike_out_first_ids", [])
            ids_txt = ",".join([str(int(x)) for x in out_ids[:4]]) if isinstance(out_ids, list) else ""
            msg += (
                f" out_ok={int(run_meta.get('spike_out_s2mm_ok', 0))}"
                f" out_nz={int(run_meta.get('spike_out_nonzero_words', 0))}"
                f" out_ids=[{ids_txt}]"
            )
        if int(sw_post_meta.get("sw_post_source_mode", 0)) == 1:
            msg += (
                f" sw_post(cap={int(sw_post_meta.get('sw_post_capture_count', 0))}/{chunk}"
                f" miss={int(sw_post_meta.get('sw_post_missing_count', 0))}"
                f" fb={int(sw_post_meta.get('sw_post_capture_fallback', 0))}"
                f" skip={int(sw_post_meta.get('sw_post_capture_skip_missing', 0))})"
            )
        if cmp_meta is not None:
            msg += f" mismatch={cmp_meta['mismatch_count']}"
            nz = cmp_meta.get("nonzero_summary", {})
            if nz:
                msg += (
                    f" nz(hw/sw/ov)={nz.get('hw_nonzero_count', 0)}/"
                    f"{nz.get('sw_nonzero_count', 0)}/"
                    f"{nz.get('overlap_nonzero_count', 0)}"
                )
            if ckpt_meta is not None:
                msg += (
                    f" ckpt_wb_nz={int(ckpt_meta.get('weight_byte_nonzero', 0))}/"
                    f"{int(ckpt_meta.get('weight_byte_nonzero_raw8', 0))}"
                    f" s16={int(ckpt_meta.get('weight_byte_nonzero_raw8_shift16', 0))}"
                    f" s24={int(ckpt_meta.get('weight_byte_nonzero_raw8_shift24', 0))}"
                    f" ckpt_idx_only={int(ckpt_meta.get('index_only_words', 0))}"
                    f" ckpt_wsum={int(ckpt_meta.get('weight_sum_checkpoint', 0))}/"
                    f"{int(ckpt_meta.get('weight_sum_hls_post', 0))}"
                )
                if checkpoint_payload_is_index_only(ckpt_meta):
                    msg += " ckpt_fmt=index-only"
                    if int(run_meta.get("update_delta_8b", 0)) > 0:
                        if int(run_meta.get("post_complete_est", 0)) == 0:
                            msg += " ckpt_note=post_path_incomplete"
                        else:
                            msg += " ckpt_warn=payload_missing_weight_bits"
                elif int(ckpt_meta.get("packed_decode_all_zero", 0)) == 1:
                    msg += " ckpt_note=raw_payload_nonzero_decode_zero"
        print(msg)

        steps_done += chunk
        chunk_idx += 1

    elapsed = time.time() - t0

    # Final status snapshot
    hls_status = hls.read(HLS_STATUS_REG)
    hls_status_dec = decode_hls_status(hls_status)

    print("\n" + sep)
    print(f"Steps: {args.n_steps}  elapsed: {elapsed:.2f}s  ({elapsed/max(args.n_steps,1)*1000:.2f} ms/step)")
    print(
        f"Final compare: {'PASS' if final_cmp.get('mismatch_count', 1) == 0 else 'FAIL'} "
        f"(mismatch_count={final_cmp.get('mismatch_count', -1)})"
    )
    print(
        f"HLS status: ready={hls_status_dec['snn_ready']} busy={hls_status_dec['snn_busy']} "
        f"stdp={hls_status_dec['stdp_active']} mode={hls_status_dec['op_mode']} "
        f"upd8={hls_status_dec['update_counter_8b']}"
    )

    if final_cmp.get("mismatch_count", 0):
        print("First mismatches:")
        for row in final_cmp.get("first_mismatches", [])[:10]:
            conn = row.get("connection", "n/a")
            pre = row.get("pre_id", -1)
            post = row.get("post_id", -1)
            print(
                f"  idx={row['idx']} hw={row['hw']} sw={row['sw']} "
                f"conn={conn} pre={pre} post={post}"
            )

    final_ckpt_meta = chunk_logs[-1].get("checkpoint_meta") if chunk_logs else None
    final_run_meta = chunk_logs[-1].get("run_meta") if chunk_logs else None
    post_path_incomplete = int((final_run_meta or {}).get("post_complete_est", 0)) == 0
    if checkpoint_payload_is_index_only(final_ckpt_meta):
        print("\nWARNING: Checkpoint payload appears INDEX-ONLY (weight field all-zero).")
        print("  Stream has sequential packet indices, but packed weight bits are missing.")
        if post_path_incomplete:
            print("  NOTE: This run also shows incomplete post-spike consumption (post_ok=0).")
            print("  In that case, weights may legitimately remain zero despite non-zero traffic counters.")
        else:
            print("  This usually indicates stale/mismatched HLS IP/bitstream or checkpoint TDATA packing issue.")
            print("  Rebuild and redeploy BOTH snn_integrated_v2.bit and snn_integrated_v2.hwh from the same build.")
    elif final_ckpt_meta and int(final_ckpt_meta.get("packed_decode_all_zero", 0)) == 1:
        print("\nWARNING: Checkpoint raw payload is non-zero, but configured packed decode is all-zero.")
        print(
            "  This suggests checkpoint decode-width mismatch "
            f"(SW expects {PACKED_WORD_BITS}-bit packed weights)."
        )
        print("  Verify SNN_WEIGHT_BITS consistency between bitstream build and SW simulator constants.")

    summary = {
        "n_steps": int(args.n_steps),
        "checkpoint_every": int(args.checkpoint_every),
        "run_chunk_steps": int(args.run_chunk_steps),
        "trace_decay": float(args.trace_decay),
        "strict": bool(args.strict),
        "programmed": bool(not args.no_program),
        "packet_id_width": int(args.packet_id_width),
        "first_spike_only": bool(not args.no_first_spike_only),
        "sw_post_source": str(args.sw_post_source),
        "sw_skip_post_if_missing_capture": bool(args.sw_skip_post_if_missing_capture),
        "rearm_first_spike_per_run": bool(args.rearm_first_spike_per_run),
        "pre_base": int(args.pre_base),
        "post_base": int(args.post_base),
        "n_sources": int(args.n_sources),
        "threshold": int(args.threshold),
        "leak": int(args.leak),
        "refrac": int(args.refrac),
        "learning_params_words": [int(x) for x in lp_words],
        "cfg_version": int(cfg_ver),
        "hls_status": int(hls_status),
        "hls_status_decode": hls_status_dec,
        "checkpoint_smoke": smoke_report,
        "initial_checkpoint": init_meta,
        "final_compare": final_cmp,
        "final_checkpoint_index_only": bool(checkpoint_payload_is_index_only(final_ckpt_meta)),
        "elapsed_s": float(elapsed),
        "ms_per_step": float(elapsed / max(args.n_steps, 1) * 1000.0),
        "runtime_profile": str(args.runtime_profile),
        "runtime_tuning": {k: float(v) for k, v in runtime_tuning.items()},
        "capture_out_spikes": bool(args.capture_out_spikes),
        "out_capture_words": int(args.out_capture_words),
        "out_id_width": int(args.out_id_width),
        "chunks": chunk_logs,
    }

    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved: {out_path}")

    hls.close()
    cfg.close()
    dma_spike.close()
    dma_weight.close()
    dma_buf_close(buf_spike)
    dma_buf_close(buf_wout)
    if buf_spike_out is not None:
        dma_buf_close(buf_spike_out)
    if buf_weight_in is not None:
        dma_buf_close(buf_weight_in)

    fail = False
    if args.strict:
        if final_cmp.get("mismatch_count", 1) != 0:
            fail = True
        if not verify_ok:
            fail = True
        for c in chunk_logs:
            run_meta = c["run_meta"]
            chunk_steps = int(c["chunk_steps"])
            if int(run_meta["mm2s_ok"]) != 1:
                fail = True
            if int(run_meta["hls_input_spikes"]) != chunk_steps:
                fail = True
            if int(run_meta["router_spikes"]) != chunk_steps:
                fail = True
            if int(run_meta["neuron_spikes"]) != chunk_steps:
                fail = True
            if int(run_meta.get("update_complete", 0)) != 1:
                fail = True
            if int(run_meta.get("post_complete_est", 0)) != 1:
                fail = True
            ckpt_meta = c.get("checkpoint_meta")
            if ckpt_meta is not None:
                if int(ckpt_meta["s2mm_ok"]) != 1:
                    fail = True
                if int(ckpt_meta["missing_indices"]) != 0:
                    fail = True
        if fail:
            sys.exit(2)


if __name__ == "__main__":
    main()
