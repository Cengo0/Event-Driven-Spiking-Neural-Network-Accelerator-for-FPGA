import numpy as np

from spikepress.pynq_runtime import (
    PYNQ_ONESHOT_SCHEMA,
    SpikeMoldPynqRunConfig,
    run_spikemold_pynq_one_shot,
)
from spikepress.transport import REGISTER_OFFSETS, STATUS_DONE


class FakeBuffer:
    _next_address = 0x10000000

    def __init__(self, shape, dtype):
        self.array = np.zeros(shape, dtype=dtype)
        self.physical_address = FakeBuffer._next_address
        FakeBuffer._next_address += int(self.array.nbytes) + 0x1000
        self.flushed = False
        self.invalidated = False
        self.freed = False

    def __setitem__(self, key, value):
        self.array[key] = value

    def __getitem__(self, key):
        return self.array[key]

    def flush(self):
        self.flushed = True

    def invalidate(self):
        self.invalidated = True

    def freebuffer(self):
        self.freed = True


class FakeIp:
    buffers = []

    def __init__(self):
        self.registers = {
            REGISTER_OFFSETS["STATUS"]: STATUS_DONE,
            REGISTER_OFFSETS["OUTPUT_WORDS"]: 2,
            REGISTER_OFFSETS["CYCLE_COUNT"]: 17,
            REGISTER_OFFSETS["INPUT_EVENT_COUNT"]: 3,
            REGISTER_OFFSETS["UPDATE_COUNT"]: 5,
            REGISTER_OFFSETS["ACTIVE_COUNT"]: 2,
            REGISTER_OFFSETS["STALL_COUNT"]: 0,
            REGISTER_OFFSETS["ERROR_CODE"]: 0,
        }
        self.writes = []

    def write(self, offset, value):
        self.writes.append((int(offset), int(value)))
        self.registers[int(offset)] = int(value)
        if int(offset) == REGISTER_OFFSETS["CTRL"] and int(value) == 1 and len(FakeIp.buffers) >= 2:
            FakeIp.buffers[1].array[:2] = np.asarray([0xAA, 0xBB], dtype=np.uint64)

    def read(self, offset):
        return self.registers.get(int(offset), 0)


class FakeOverlay:
    def __init__(self, bitstream_path):
        self.bitstream_path = bitstream_path
        self.spikemold_ctrl_0 = FakeIp()


def test_pynq_one_shot_runtime_uses_register_map_with_injected_overlay():
    buffers = []
    FakeIp.buffers = buffers

    def allocator(shape, dtype):
        buffer = FakeBuffer(shape, dtype)
        buffers.append(buffer)
        return buffer

    result = run_spikemold_pynq_one_shot(
        [0x11, 0x22, 0x33],
        SpikeMoldPynqRunConfig(bitstream_path="mock.bit", output_cap_words=4),
        overlay_factory=FakeOverlay,
        allocator=allocator,
        evidence_level="unit_test_mock_no_board",
        board_executed=False,
    )

    assert result.schema == PYNQ_ONESHOT_SCHEMA
    assert result.board_executed is False
    assert result.ok is True
    assert result.input_word_count == 3
    assert result.output_word_count == 2
    assert result.output_words == (0xAA, 0xBB)
    assert result.counters["cycle_count"] == 17
    assert result.counters["input_event_count"] == 3
    assert result.counters["update_count"] == 5
    assert buffers[0].flushed is True
    assert buffers[1].invalidated is True
    assert buffers[0].freed is True
    assert buffers[1].freed is True
