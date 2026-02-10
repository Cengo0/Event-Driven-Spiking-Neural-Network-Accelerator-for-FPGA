# Architecture

System architecture of the Event-Driven SNN FPGA Accelerator.

## Overview

```
┌─────────────────────────────────────────────────────────┐
│                Software (Python/PyTorch)                │
│  - Model training                                       │
│  - Spike encoding                                       │
│  - Configuration                                        │
└───────────────────────┬─────────────────────────────────┘
                        │ AXI Bus
┌───────────────────────┴─────────────────────────────────┐
│                 FPGA (PYNQ-Z2)                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────────┐    │
│  │ AXI        │→ │ Spike      │→ │ LIF Neurons    │    │
│  │ Interface  │  │ Router     │  │ (720 neurons)  │    │
│  └────────────┘  └────────────┘  └────────────────┘    │
│         ↓               ↓                 ↓            │
│  ┌──────────────────────────────────────────────────┐  │
│  │         STDP/R-STDP Learning Engine              │  │
│  │         (HLS, per-neuron traces)                 │  │
│  └──────────────────────────────────────────────────┘  │
│         ↓                                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Synaptic Weight Memory (BRAM)            │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Design Principles**:
- Event-driven processing (asynchronous spike-based)
- AC-based operations (accumulate-only, no multiply)
- Fixed-point arithmetic
- Memory-efficient (per-neuron traces, not per-synapse)

**Hardware**: Xilinx Zynq-7020 (xc7z020clg400-1) on PYNQ-Z2

**Resources** (Integrated build, 100 MHz):

| Resource | Used | Available | % |
|----------|------|-----------|---|
| LUT | 15,042 | 53,200 | 28.27% |
| FF | 16,003 | 106,400 | 15.04% |
| BRAM | 113 | 140 | 80.71% |
| DSP | 4 | 220 | 1.82% |

**Timing**: WNS +0.338ns ✅, Clock 100 MHz

## LIF Neuron

Basic computational unit.

**State**:
- `v_mem`: 16-bit unsigned membrane potential
- `refrac_counter`: 8-bit refractory counter
- `spike_out`: 1-bit output

**Operation**:
```
// Input arrives
v_mem += weight  (saturate at 2^16-1)

// No input (leak)
leak1 = v_mem >> shift1
leak2 = v_mem >> shift2  (if enabled)
v_mem -= (leak1 + leak2)

// Spike check
if v_mem >= threshold:
    spike_out = 1
    v_mem = reset_potential
    refrac_counter = refractory_period
```

**Shift-Based Leak**:

Instead of multiply, uses shifts: `tau = 1 - 2^(-shift1) - 2^(-shift2)`

| tau | shift1 | shift2 | Usage |
|-----|--------|--------|-------|
| 0.500 | 1 | 0 | Fast decay |
| 0.875 | 3 | 0 | Moderate |
| 0.906 | 4 | 5 | Typical |
| 0.953 | 5 | 6 | Slow decay |

**leak_rate Encoding**:
- Bits [2:0]: shift1 (1-7)
- Bits [7:3]: shift2 (0 = disabled, 1-31)

**Parameters**:
- threshold: 16-bit (typical 100-2000)
- refractory_period: 8-bit (0-255 timesteps)
- reset_potential: 16-bit (typically 0)

**Files**:
- `hardware/hdl/rtl/neurons/lif_neuron.v` - Base implementation
- `hardware/hdl/rtl/neurons/lif_neuron_ac.v` - AC-based variant
- `hardware/hdl/rtl/neurons/lif_neuron_array.v` - Time-multiplexed array

## Spike Router

Routes spikes from source to destination neurons.

**Features**:
- AER (Address-Event Representation)
- Programmable connectivity
- 512-entry FIFO
- Parameterized neuron ID width

**Connection Entry** (CONN_WIDTH = 18 + NEURON_ID_WIDTH):
```
[CONN_WIDTH-1]     : valid
[CONN_WIDTH-2]     : exc_inh (0=excitatory, 1=inhibitory)
[NEURON_ID+15:NEURON_ID+8] : weight (8-bit signed)
[NEURON_ID+7:NEURON_ID] : delay (8-bit)
[NEURON_ID-1:0]    : dest_neuron_id
```

**Performance**:
- Throughput: 1 spike/cycle
- Latency: 2-5 cycles
- Max connections: Configurable (typically 4096)

**File**: `hardware/hdl/rtl/router/spike_router.v`

## STDP Learning Engine

On-chip learning using Spike-Timing-Dependent Plasticity.

**Algorithm**: Mozafari weight-dependent STDP

$$\Delta w_{LTP} = a^+ \cdot \frac{(w_{max} - w)^{\mu}}{scale}$$

$$\Delta w_{LTD} = -a^- \cdot \frac{(w - w_{min})^{\mu}}{scale}$$

**Per-Neuron Traces** (Memory-efficient):

```cpp
// O(N+M) instead of O(N×M)
static neuron_trace_t pre_traces[MAX_NEURONS];   // 720 entries
static neuron_trace_t post_traces[MAX_NEURONS];  // 720 entries

struct neuron_trace_t {
    ap_uint<8> trace;              // 8-bit exponential trace
    ap_uint<16> last_spike_time;   // Timestamp for lazy update
};
```

**Lazy Update**:
- Don't update every cycle
- Use 16-entry LUT for exponential decay
- Update only on spike arrival

**R-STDP**: Reward-modulated variant

$$\Delta w = eligibility \cdot reward$$

**Parameters**:
- a_plus, a_minus: Learning rates (8-bit fixed-point)
- w_min, w_max: Weight bounds
- tau_pre, tau_post: Trace decay time constants
- mu: Weight-dependence exponent (Q4.4 fixed-point)

**Files**:
- `hardware/hdl/rtl/stdp/stdp_engine.v` - RTL implementation
- `hardware/hls/src/snn_top_hls.cpp` - HLS implementation

## Synaptic Weight Memory

Stores connection weights.

**Organization**:
```
Address: [Src_Neuron_ID][Dst_Neuron_ID]
Data:    8-bit signed weight (-127 to +127)

Example: 720 neurons
Total: 720 × 720 = 518,400 weights × 4-bit = 259 KB
```

**HLS Memory Optimization**:
- Weight array partitioned: cyclic factor=2 on dim=1, cyclic factor=4 on dim=2 (8 banks total)
- Pre/post traces and eligibility: cyclic partition factor=4
- Enables parallel read/write for improved loop throughput

**Access Pattern**:
- Read on spike arrival (get weight)
- Write on STDP update (update weight)
- Single-port BRAM (read or write per cycle)

**File**: `hardware/hdl/rtl/synapses/weight_memory.v`

## Spike Encoding

Convert continuous values to spikes.

### Rate Encoding (Poisson)

Spike probability proportional to input intensity.

```python
rate = input_value * max_rate
spikes = np.random.poisson(rate * dt)
```

### Temporal Encoding

Intensity → latency (brighter = earlier spike)

```python
latency = (1 - input_value) * max_latency
spike_time = latency
```

### Phase Encoding

Value mapped to spike phase within cycle.

### Delta-Sigma

Continuous tracking with feedback.

**File**: `software/python/snn_fpga_accelerator/spike_encoding.py`

## Communication Interfaces

### AXI4-Lite (Control)

32-bit register access.

**Control Registers**:
- Global config (threshold, leak_rate, etc.)
- STDP parameters
- Status/control flags

### AXI4-Stream (Data)

Spike streaming.

**Spike Format** (10-bit neuron IDs):
```
[31:24] - Flags
[23:20] - Reserved
[19:10] - Source neuron ID (10-bit, supports up to 1024 neurons)
[9:0]   - Destination neuron ID (10-bit)
```

**Weight Packet Format** (10-bit IDs):
```
[27:20] - Weight (8-bit)
[19:10] - Column neuron ID (10-bit)
[9:0]   - Row neuron ID (10-bit)
```

## Data Flow

### Inference

1. PS sends input spikes via AXI Stream
2. HLS encoder (optional) processes spikes
3. Spike router forwards to target neurons
4. LIF neurons integrate and fire
5. Output spikes sent back to PS

### Learning

1. Pre-spike: Update pre-trace, apply LTD
2. Post-spike: Update post-trace, apply LTP
3. Weight update: Apply delta, clamp to bounds
4. (R-STDP) Modulate by reward signal

## HLS Pipelining Optimizations

The HLS learning engine has been aggressively optimized for throughput:

| Loop | Before | After | Improvement |
|------|--------|-------|-------------|
| LTD_LOOP | II=2, UNROLL=2 | II=1, UNROLL=4 | 2× throughput |
| LTP_LOOP | II=2 | II=1 | 2× throughput |
| RSTDP_INNER | No unroll | UNROLL=4 | 4× throughput |
| DECAY_PRE/POST | UNROLL=2 | UNROLL=4 | 2× throughput |
| WEIGHT_SUM | II=2 | II=1 | 2× throughput |

**Net Result**: With 512 neurons (4× more synapses than 256), the total RSTDP computation time increased only ~3% (69,632 vs 67,584 cycles) thanks to pipelining improvements.

## Power Efficiency

### AC-Based Architecture

- **MAC operation**: ~4.6 pJ (multiply + add)
- **AC operation**: ~0.9 pJ (add only)
- **Savings**: ~5x per synaptic operation

**Breakdown** (Estimated):
- HLS IP: ~108 mW (65%)
- Verilog RTL: ~35 mW (21%)
- PS interface: ~15 mW (9%)
- Clocking: ~8 mW (5%)

Total: ~166 mW (event-driven, varies with activity)

### Energy Optimization

- Shift-based leak (no multiplier)
- Event-driven (only active on spikes)
- Per-neuron traces (reduce memory access)
- Lazy update (compute on-demand)

## Build Details

**Target Device**: xc7z020clg400-1  
**Clock**: 100 MHz  
**Build Time**: ~20 minutes  
**Output**: `outputs/snn_integrated.bit` (3.9 MB)

**Build Command**:
```bash
cd hardware/scripts
./build_integrated.sh
```

See [developer_guide.md](developer_guide.md) for detailed build instructions.

## References

- [User Guide](user_guide.md) - Usage examples
- [Developer Guide](developer_guide.md) - Development workflow
- [API Reference](api_reference.md) - Python API
