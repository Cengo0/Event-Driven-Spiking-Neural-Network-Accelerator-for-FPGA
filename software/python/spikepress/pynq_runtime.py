"""PYNQ-Z2 one-shot runtime for SpikeMold register-map V1.

This module contains the board execution path, but importing it does not require
PYNQ. The `pynq` package is imported only inside `run_spikemold_pynq_one_shot`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence

import numpy as np

from .transport import (
    CTRL_IRQ_ENABLE,
    CTRL_SOFT_RESET,
    CTRL_START,
    REGISTER_OFFSETS,
    STATUS_DONE,
    STATUS_ERROR,
)


PYNQ_ONESHOT_SCHEMA = "spikemold.pynq_oneshot_result.v1"


@dataclass(frozen=True)
class SpikeMoldPynqRunConfig:
    bitstream_path: str
    ip_name: str = "spikemold_ctrl_0"
    output_cap_words: int = 1024
    timeout_polls: int = 100000
    irq_enable: bool = False


@dataclass(frozen=True)
class SpikeMoldPynqRunResult:
    schema: str
    evidence_level: str
    board_executed: bool
    ok: bool
    bitstream_path: str
    ip_name: str
    input_word_count: int
    output_word_count: int
    output_words: tuple[int, ...]
    status: int
    error_code: int
    counters: Mapping[str, int]
    hashes: Mapping[str, str]

    def to_dict(self) -> dict[str, object]:
        body = asdict(self)
        body["output_words"] = list(self.output_words)
        body["counters"] = dict(self.counters)
        body["hashes"] = dict(self.hashes)
        return body

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _validate_words(words: Sequence[int]) -> np.ndarray:
    array = np.asarray([int(word) for word in words], dtype=object)
    for word in array.tolist():
        if word < 0 or word >= (1 << 64):
            raise ValueError(f"EventWord64 out of range: {word}")
    return np.asarray(array.tolist(), dtype=np.uint64)


def _sha256_u64_words(words: Sequence[int]) -> str:
    payload = b"".join(int(word).to_bytes(8, "little") for word in words)
    return hashlib.sha256(payload).hexdigest()


def _buffer_address(buffer: object) -> int:
    for attr in ("physical_address", "device_address"):
        value = getattr(buffer, attr, None)
        if value is not None:
            return int(value)
    raise TypeError("PYNQ buffer does not expose physical_address/device_address")


def _flush(buffer: object) -> None:
    flush = getattr(buffer, "flush", None)
    if callable(flush):
        flush()


def _invalidate(buffer: object) -> None:
    invalidate = getattr(buffer, "invalidate", None)
    if callable(invalidate):
        invalidate()


def _free(buffer: object) -> None:
    free = getattr(buffer, "freebuffer", None)
    if callable(free):
        free()


def _resolve_ip(overlay: object, ip_name: str) -> object:
    direct = getattr(overlay, ip_name, None)
    if direct is not None:
        return direct
    ip_dict = getattr(overlay, "ip_dict", {})
    if isinstance(ip_dict, Mapping) and ip_name in ip_dict:
        return getattr(overlay, ip_name)
    raise KeyError(f"SpikeMold IP not found in overlay: {ip_name}")


def _write_addr64(ip: object, lo_name: str, hi_name: str, address: int) -> None:
    ip.write(REGISTER_OFFSETS[lo_name], int(address) & 0xFFFFFFFF)
    ip.write(REGISTER_OFFSETS[hi_name], (int(address) >> 32) & 0xFFFFFFFF)


def _read_counters(ip: object) -> dict[str, int]:
    names = [
        "OUTPUT_WORDS",
        "CYCLE_COUNT",
        "INPUT_EVENT_COUNT",
        "UPDATE_COUNT",
        "ACTIVE_COUNT",
        "STALL_COUNT",
        "ERROR_CODE",
    ]
    return {name.lower(): int(ip.read(REGISTER_OFFSETS[name])) for name in names}


def run_spikemold_pynq_one_shot(
    input_words: Sequence[int],
    config: SpikeMoldPynqRunConfig,
    *,
    overlay_factory: Optional[Callable[[str], object]] = None,
    allocator: Optional[Callable[..., object]] = None,
    evidence_level: str = "pynq_board_runtime_one_shot",
    board_executed: bool = True,
) -> SpikeMoldPynqRunResult:
    """Run one bounded SpikeMold job through the minimal AXI-Lite register map.

    `overlay_factory` and `allocator` are injectable for tests. Production board
    use should leave them unset, which imports `pynq.Overlay` and `pynq.allocate`.
    """

    if config.output_cap_words <= 0:
        raise ValueError("output_cap_words must be positive")
    if config.timeout_polls <= 0:
        raise ValueError("timeout_polls must be positive")

    words = _validate_words(input_words)

    if overlay_factory is None or allocator is None:
        try:
            from pynq import Overlay, allocate  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on board image
            raise RuntimeError("PYNQ runtime requires the pynq package on the board") from exc
        overlay_factory = overlay_factory or Overlay
        allocator = allocator or allocate

    overlay = overlay_factory(config.bitstream_path)
    ip = _resolve_ip(overlay, config.ip_name)

    input_buffer = allocator(shape=(len(words),), dtype=np.uint64)
    output_buffer = allocator(shape=(config.output_cap_words,), dtype=np.uint64)
    try:
        input_buffer[:] = words
        output_buffer[:] = 0
        _flush(input_buffer)
        _flush(output_buffer)

        ip.write(REGISTER_OFFSETS["CTRL"], CTRL_SOFT_RESET)
        ip.write(REGISTER_OFFSETS["CTRL"], 0)
        _write_addr64(ip, "INPUT_BASE_LO", "INPUT_BASE_HI", _buffer_address(input_buffer))
        _write_addr64(ip, "OUTPUT_BASE_LO", "OUTPUT_BASE_HI", _buffer_address(output_buffer))
        ip.write(REGISTER_OFFSETS["INPUT_WORDS"], len(words))
        ip.write(REGISTER_OFFSETS["OUTPUT_CAP_WORDS"], config.output_cap_words)

        ctrl = CTRL_START | (CTRL_IRQ_ENABLE if config.irq_enable else 0)
        ip.write(REGISTER_OFFSETS["CTRL"], ctrl)

        status = 0
        for _ in range(config.timeout_polls):
            status = int(ip.read(REGISTER_OFFSETS["STATUS"]))
            if status & (STATUS_DONE | STATUS_ERROR):
                break
        else:
            raise TimeoutError(f"SpikeMold job did not finish within {config.timeout_polls} polls")

        _invalidate(output_buffer)
        counters = _read_counters(ip)
        output_word_count = min(int(counters["output_words"]), config.output_cap_words)
        output_words = tuple(int(word) for word in np.asarray(output_buffer[:output_word_count], dtype=np.uint64))
        error_code = int(counters["error_code"])
        ok = bool(status & STATUS_DONE) and not bool(status & STATUS_ERROR) and error_code == 0

        return SpikeMoldPynqRunResult(
            schema=PYNQ_ONESHOT_SCHEMA,
            evidence_level=evidence_level,
            board_executed=board_executed,
            ok=ok,
            bitstream_path=str(config.bitstream_path),
            ip_name=config.ip_name,
            input_word_count=len(words),
            output_word_count=output_word_count,
            output_words=output_words,
            status=status,
            error_code=error_code,
            counters=counters,
            hashes={
                "input_words_sha256": _sha256_u64_words([int(word) for word in words]),
                "output_words_sha256": _sha256_u64_words(output_words),
            },
        )
    finally:
        _free(input_buffer)
        _free(output_buffer)
