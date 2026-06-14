# Minimal Register Map V1

Status: active draft

## Purpose

This is the minimal AXI-Lite control surface for SpikeMold transport smoke
and the SpikeMold flat FC-LIF path. Wider SpikeMold backends may add registers, but they
must preserve these addresses or provide an explicit compatibility shim.

## Registers

| Offset | Name | Access | Description |
|---:|---|---|---|
| `0x00` | `CTRL` | RW | bit0 start, bit1 soft_reset, bit2 irq_enable |
| `0x04` | `STATUS` | RO | bit0 idle, bit1 busy, bit2 done, bit3 error |
| `0x08` | `INPUT_BASE_LO` | RW | input DMA/DDR base low |
| `0x0C` | `INPUT_BASE_HI` | RW | input DMA/DDR base high |
| `0x10` | `OUTPUT_BASE_LO` | RW | output DMA/DDR base low |
| `0x14` | `OUTPUT_BASE_HI` | RW | output DMA/DDR base high |
| `0x18` | `INPUT_WORDS` | RW | input word count |
| `0x1C` | `OUTPUT_CAP_WORDS` | RW | output capacity |
| `0x20` | `OUTPUT_WORDS` | RO | produced output words |
| `0x24` | `CYCLE_COUNT` | RO | total hardware cycles |
| `0x28` | `INPUT_EVENT_COUNT` | RO | accepted input events |
| `0x2C` | `UPDATE_COUNT` | RO | generated synaptic updates |
| `0x30` | `ACTIVE_COUNT` | RO | unique active neurons committed |
| `0x34` | `STALL_COUNT` | RO | backpressure cycles |
| `0x38` | `ERROR_CODE` | RO | zero on success |

## Required Smoke Behavior

- Soft reset clears counters.
- DMA loopback can prove input/output path before SpikeMold execution.
- Counter reads are stable after `STATUS.done = 1`.
- Error status must include a nonzero `ERROR_CODE`.
