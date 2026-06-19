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
| `0x4C` | `BACKEND_MODE` | RW | backend selector: 0 flat FC-LIF, 1 EventConv smoke, 2 frozen EventConv-FC slice |
| `0x50` | `EVENTCONV_SHAPE0` | RW | compatible EventConv descriptor. Mode 1 accepts `0x04020303`; mode 2 accepts `0x04031c1c` (`28x28`, `3x3`, 4 output channels) |
| `0x54` | `EVENTCONV_KERNEL0` | RW | packed EventConv int8 kernel weights for mode-1 2x2 smoke only; mode 2 loads 36 kernel bytes through config writes `0x02000000..0x02000008` |
| `0x58` | `EVENTCONV_DESC_STATUS` | RO | mode/shape status. bit0 mode-1 shape accepted, bit1 kernel register drives mode-1 AGU, bit2 mode-1 static gate present, bit3 mode-2 shape accepted, bit4 mode-2 selected |

## EventConv Descriptor Boundary

The descriptor extension is a compatible register-map step toward configurable
EventConv. At this gate, `EVENTCONV_KERNEL0` drives the integrated mode-1
EventConv AGU weights, while `EVENTCONV_SHAPE0` is accepted for two static RTL
specializations:

- mode 1: tiny 3x3-input, 2x2-kernel, 4-state EventConv smoke.
- mode 2: frozen `EventConv(1x28x28, 4 filters, 3x3, stride 2, padding 1) -> FC-LIF(784->10)` final-goal slice.

Mode 2 kernel bytes are loaded through router-config target writes with high
address byte `0x02`; router readout weights use the existing router connection
and count tables. Arbitrary EventConv shape/kernel board claims remain outside
this contract until rebuilt bit/HWH evidence proves a wider descriptor path.

## Required Smoke Behavior

- Soft reset clears counters.
- DMA loopback can prove input/output path before SpikeMold execution.
- Counter reads are stable after `STATUS.done = 1`.
- Error status must include a nonzero `ERROR_CODE`.
