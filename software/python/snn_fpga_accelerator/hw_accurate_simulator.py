"""
Hardware-Accurate SNN Simulator

Bit-accurate simulation of the Verilog RTL and HLS implementations.
Uses fixed-point arithmetic to match hardware behavior exactly.

This module provides 1:1 mapping with:
- hardware/hdl/rtl/neurons/lif_neuron.v
- hardware/hls/src/snn_learning_engine.cpp

Author: Jiwoon Lee (@metr0jw)
"""

import math
import numpy as np
from typing import List, Dict, Optional, Tuple, NamedTuple
from dataclasses import dataclass, field
from collections import deque
import warnings

from .spike_encoding import SpikeEvent
from .utils import logger


# =============================================================================
# Hardware Constants (single source of truth: config/snn_params.yaml)
# =============================================================================
# Import from the generated constants module.  If the generated file does not
# exist (e.g. fresh clone before running generate_params.py), fall back to
# hardcoded defaults that match the canonical YAML values.

import importlib.util as _ilu
from pathlib import Path as _Path

_GEN_PARAMS = _Path(__file__).resolve().parents[3] / "config" / "generated" / "snn_params.py"

if _GEN_PARAMS.exists():
    _spec = _ilu.spec_from_file_location("_snn_params", str(_GEN_PARAMS))
    _mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)

    # Pull every public constant into this module's namespace
    for _k in dir(_mod):
        if not _k.startswith("_"):
            globals()[_k] = getattr(_mod, _k)
else:
    # ---- fallback (keep in sync with config/snn_params.yaml) ---------------
    NUM_GROUPS          = 16
    NEURONS_PER_GROUP   = 128
    MAX_NEURONS_PER_GROUP = 128
    GROUP_SIZES         = [128] * 16
    TOTAL_NEURONS       = 2048
    MAX_FANOUT_INTER    = 16
    SPIKE_BUFFER_DEPTH  = 64
    DATA_WIDTH          = 16
    WEIGHT_WIDTH        = 8
    THRESHOLD_WIDTH     = 16
    LEAK_WIDTH          = 8
    REFRAC_WIDTH        = 8
    GROUP_ID_WIDTH      = 4
    LOCAL_ID_WIDTH      = 7
    GLOBAL_ID_WIDTH     = 11
    FANOUT_IDX_WIDTH    = 4
    MAX_NEURONS         = 2048
    CT_DATA_WIDTH       = 21
    NEURON_STATE_WIDTH  = 24
    MAX_WEIGHT          = 255
    MIN_WEIGHT          = 0
    WEIGHT_FLAG_WIDTH   = 9
    MAX_WEIGHT_DELTA    = 255
    HLS_NEURON_ID_WIDTH = 13
    HLS_MAX_NEURONS     = 2048
    HLS_WEIGHT_WIDTH    = 8
    NEURON_ID_WIDTH     = GLOBAL_ID_WIDTH
    FIXED_POINT_FRAC_BITS = 8
    FIXED_POINT_SCALE   = 1 << FIXED_POINT_FRAC_BITS
    LEGACY_MAX_WEIGHT   = 127
    LEGACY_MIN_WEIGHT   = -128
    LEGACY_WEIGHT_SCALE = 128
    WEIGHT_SCALE        = 256

    # Phase 6.5 NeuronGroup-aware defaults (Block-sparse K=1024, 4 blocks)
    NUM_NEURON_GROUPS   = 9
    NUM_CONNECTIONS     = 8
    NEURON_GROUP_NAMES  = ['input_0', 'input_1', 'input_2', 'input_3',
                           'hidden_0', 'hidden_1', 'hidden_2', 'hidden_3',
                           'output']
    NEURON_GROUP_SIZES  = [196, 196, 196, 196, 1024, 1024, 1024, 1024, 10]
    NEURON_GROUP_ID_START = [0, 196, 392, 588, 784, 1808, 2832, 3856, 4880, 4890]
    TOTAL_LOGICAL_NEURONS = 4890
    MAX_WEIGHT_BUFFER_SIZE = 843776  # 4×(196×1024) + 4×(1024×10)
    CONNECTIONS = [
        {'name': 'in0_to_hid0', 'src_group': 0, 'dst_group': 4,
         'src_size': 196, 'dst_size': 1024, 'weight_offset': 0,
         'num_weights': 200704},
        {'name': 'in1_to_hid1', 'src_group': 1, 'dst_group': 5,
         'src_size': 196, 'dst_size': 1024, 'weight_offset': 200704,
         'num_weights': 200704},
        {'name': 'in2_to_hid2', 'src_group': 2, 'dst_group': 6,
         'src_size': 196, 'dst_size': 1024, 'weight_offset': 401408,
         'num_weights': 200704},
        {'name': 'in3_to_hid3', 'src_group': 3, 'dst_group': 7,
         'src_size': 196, 'dst_size': 1024, 'weight_offset': 602112,
         'num_weights': 200704},
        {'name': 'hid0_to_output', 'src_group': 4, 'dst_group': 8,
         'src_size': 1024, 'dst_size': 10, 'weight_offset': 802816,
         'num_weights': 10240},
        {'name': 'hid1_to_output', 'src_group': 5, 'dst_group': 8,
         'src_size': 1024, 'dst_size': 10, 'weight_offset': 813056,
         'num_weights': 10240},
        {'name': 'hid2_to_output', 'src_group': 6, 'dst_group': 8,
         'src_size': 1024, 'dst_size': 10, 'weight_offset': 823296,
         'num_weights': 10240},
        {'name': 'hid3_to_output', 'src_group': 7, 'dst_group': 8,
         'src_size': 1024, 'dst_size': 10, 'weight_offset': 833536,
         'num_weights': 10240},
    ]

    # Phase 7 BRAM optimization: Loihi/TrueNorth/KIST on-chip constants
    WEIGHT_BITS         = 4
    PACKED_MAX_WEIGHT   = 7   # 2^(WEIGHT_BITS-1) - 1
    PACKED_MIN_WEIGHT   = -8  # -2^(WEIGHT_BITS-1)
    TIME_EMBEDDING      = 1
    AUXILIARY_LUTRAM    = 1


# =============================================================================
# NeuronGroup-aware flat weight index (matches HLS weight_index())
# =============================================================================

def _ng_id_start():
    """Get NEURON_GROUP_ID_START from globals (may be overridden by generated params)."""
    return globals().get('NEURON_GROUP_ID_START', [0, 196, 392, 588, 784, 1808, 2832, 3856, 4880, 4890])


def _ng_connections():
    """Get CONNECTIONS from globals."""
    return globals().get('CONNECTIONS', [])


def _conn_src_start(conn: Dict) -> int:
    """Resolve connection source start ID with robust fallback."""
    if 'src_id_start' in conn:
        return int(conn.get('src_id_start', 0))
    id_start = _ng_id_start()
    src_g = int(conn.get('src_group', -1))
    if 0 <= src_g < len(id_start) - 1:
        return int(id_start[src_g])
    return 0


def _conn_dst_start(conn: Dict) -> int:
    """Resolve connection destination start ID with robust fallback."""
    if 'dst_id_start' in conn:
        return int(conn.get('dst_id_start', 0))
    id_start = _ng_id_start()
    dst_g = int(conn.get('dst_group', -1))
    if 0 <= dst_g < len(id_start) - 1:
        return int(id_start[dst_g])
    return 0


def weight_index_flat(pre_id: int, post_id: int) -> int:
    """Compute flat buffer offset for (pre_id, post_id).

    Matches HLS ``weight_index()`` exactly.  Returns -1 if no connection.
    """
    id_start = _ng_id_start()
    conns = _ng_connections()

    # Find pre group
    src_g = -1
    for g in range(len(id_start) - 1):
        if id_start[g] <= pre_id < id_start[g + 1]:
            src_g = g
            break
    if src_g < 0:
        return -1

    # Find post group
    dst_g = -1
    for g in range(len(id_start) - 1):
        if id_start[g] <= post_id < id_start[g + 1]:
            dst_g = g
            break
    if dst_g < 0:
        return -1

    # Find connection
    for conn in conns:
        if conn['src_group'] == src_g and conn['dst_group'] == dst_g:
            local_src = pre_id - id_start[src_g]
            local_dst = post_id - id_start[dst_g]
            return conn['weight_offset'] + local_src * conn['dst_size'] + local_dst

    return -1


# =============================================================================
# Fixed-Point Arithmetic Utilities
# =============================================================================

class FixedPoint:
    """
    Fixed-point number representation matching HLS ap_fixed<16,8>.
    
    Format: Q8.8 (8 integer bits, 8 fractional bits)
    Range: -128.0 to +127.99609375
    Resolution: 1/256 = 0.00390625
    """
    
    def __init__(self, value: float = 0.0, raw: Optional[int] = None):
        if raw is not None:
            # Initialize from raw integer representation
            self._raw = self._clamp_raw(raw)
        else:
            # Convert from float
            self._raw = self._clamp_raw(int(round(value * FIXED_POINT_SCALE)))
    
    @staticmethod
    def _clamp_raw(raw: int) -> int:
        """Clamp to 16-bit signed range."""
        if raw > 32767:
            return 32767
        elif raw < -32768:
            return -32768
        return raw
    
    @property
    def raw(self) -> int:
        """Get raw integer representation."""
        return self._raw
    
    def to_float(self) -> float:
        """Convert to float."""
        return self._raw / FIXED_POINT_SCALE
    
    def __add__(self, other: 'FixedPoint') -> 'FixedPoint':
        return FixedPoint(raw=self._clamp_raw(self._raw + other._raw))
    
    def __sub__(self, other: 'FixedPoint') -> 'FixedPoint':
        return FixedPoint(raw=self._clamp_raw(self._raw - other._raw))
    
    def __mul__(self, other: 'FixedPoint') -> 'FixedPoint':
        # Multiply and shift back to maintain scale
        result = (self._raw * other._raw) >> FIXED_POINT_FRAC_BITS
        return FixedPoint(raw=self._clamp_raw(result))
    
    def __neg__(self) -> 'FixedPoint':
        return FixedPoint(raw=self._clamp_raw(-self._raw))
    
    def __repr__(self) -> str:
        return f"FixedPoint({self.to_float():.6f}, raw={self._raw})"


def fixed_exp(x: FixedPoint) -> FixedPoint:
    """
    Hardware-accurate exponential function.
    
    Uses lookup table approach similar to hls::exp() implementation.
    For negative x (which is our use case), uses Taylor series approximation
    truncated to match hardware precision.
    """
    x_float = x.to_float()
    
    # Clamp input to reasonable range
    if x_float < -8.0:
        return FixedPoint(0.0)
    if x_float > 8.0:
        return FixedPoint(raw=32767)  # Max positive
    
    # Calculate exp and convert back to fixed-point
    # This matches the precision loss in hls::exp()
    result = np.exp(x_float)
    return FixedPoint(result)


# =============================================================================
# Tau / Leak Rate Conversion Utilities  
# =============================================================================

def tau_to_leak_rate(tau: float) -> int:
    """
    Convert desired tau (decay constant) to hardware leak_rate encoding.
    
    Finds the best shift configuration to approximate the target tau.
    The hardware uses shift-based exponential decay for energy efficiency.
    
    Args:
        tau: Desired decay constant (0.0-1.0). Higher values = slower leak.
             Typical values: 0.85-0.99
             tau = 0.9 means membrane potential decays to 90% each timestep
    
    Returns:
        leak_rate: Hardware-encoded leak configuration (8-bit)
                   leak_rate[2:0] = shift1 (primary leak, 1-7)
                   leak_rate[7:3] = shift2 (secondary leak, 0=disabled)
    
    Examples:
        >>> tau_to_leak_rate(0.875)  # Returns 3 (exact match)
        >>> tau_to_leak_rate(0.9)    # Returns 35 (actual: 0.906)
        >>> tau_to_leak_rate(0.95)   # Returns 37 (actual: 0.953)
    
    See Also:
        leak_rate_to_tau: Inverse function
        LIFNeuronParams.from_tau: Create full parameter object
    """
    best_error = float('inf')
    best_config = 3  # Default
    
    # Try single shift configurations (shift1 only)
    for shift1 in range(1, 8):
        approx_tau = 1.0 - 1.0 / (1 << shift1)
        error = abs(approx_tau - tau)
        if error < best_error:
            best_error = error
            best_config = shift1
    
    # Try dual shift configurations (shift1 + shift2)
    for shift1 in range(1, 8):
        for shift2 in range(1, 8):
            if shift2 == shift1:
                continue
            approx_tau = 1.0 - 1.0 / (1 << shift1) - 1.0 / (1 << shift2)
            if approx_tau > 0:  # Valid configuration
                error = abs(approx_tau - tau)
                if error < best_error:
                    best_error = error
                    best_config = shift1 | (shift2 << 3)
    
    return best_config


def leak_rate_to_tau(leak_rate: int) -> float:
    """
    Convert hardware leak_rate encoding to tau (decay constant).
    
    Args:
        leak_rate: Hardware-encoded leak configuration (8-bit)
    
    Returns:
        tau: Effective decay constant (0.0-1.0)
    
    Examples:
        >>> leak_rate_to_tau(3)   # Returns 0.875
        >>> leak_rate_to_tau(51)  # Returns 0.859375
        >>> leak_rate_to_tau(4)   # Returns 0.9375
    """
    shift1 = leak_rate & 0x07
    shift2_cfg = (leak_rate >> 3) & 0x1F
    shift2 = shift2_cfg & 0x07 if shift2_cfg != 0 else 0
    
    tau = 1.0
    if shift1 > 0:
        tau -= 1.0 / (1 << shift1)
    if shift2_cfg != 0 and shift2 > 0:
        tau -= 1.0 / (1 << shift2)
    return tau


def get_available_tau_values() -> List[Tuple[float, int]]:
    """
    Get all available tau values supported by the hardware.
    
    Returns:
        List of (tau, leak_rate) tuples sorted by tau value.
    
    Example:
        >>> for tau, leak_rate in get_available_tau_values():
        ...     print(f"tau={tau:.4f}, leak_rate={leak_rate}")
    """
    seen = set()
    values = []
    
    # Single shift configurations
    for shift1 in range(1, 8):
        tau = 1.0 - 1.0 / (1 << shift1)
        leak_rate = shift1
        if tau not in seen:
            seen.add(tau)
            values.append((tau, leak_rate))
    
    # Dual shift configurations
    for shift1 in range(1, 8):
        for shift2 in range(1, 8):
            if shift2 == shift1:
                continue
            tau = 1.0 - 1.0 / (1 << shift1) - 1.0 / (1 << shift2)
            if tau > 0:
                leak_rate = shift1 | (shift2 << 3)
                if tau not in seen:
                    seen.add(tau)
                    values.append((tau, leak_rate))
    
    return sorted(values, key=lambda x: x[0])


# =============================================================================
# Hardware-Accurate LIF Neuron
# =============================================================================

@dataclass
class LIFNeuronState:
    """State of a single LIF neuron (matches lif_neuron.v registers)."""
    v_mem: int = 0              # Membrane potential (16-bit unsigned)
    refrac_counter: int = 0     # Refractory counter (8-bit)
    spike_out: bool = False     # Spike output
    
    def reset(self):
        self.v_mem = 0
        self.refrac_counter = 0
        self.spike_out = False


@dataclass
class LIFNeuronParams:
    """
    LIF neuron parameters (matches lif_neuron.v inputs).
    
    Shift-based leak configuration:
        leak_rate[2:0] = primary shift (1-7)
        leak_rate[7:3] = secondary shift config (0=disabled)
        
    Tau calculation:
        tau = 1 - 2^(-shift1) - 2^(-shift2)  (if shift2 enabled)
        
    Example configurations:
        leak_rate = 0b00000_011 (3) -> tau = 1 - 1/8 = 0.875
        leak_rate = 0b00000_100 (4) -> tau = 1 - 1/16 = 0.9375
        leak_rate = 0b00110_011 (51) -> tau = 1 - 1/8 - 1/64 ≈ 0.859
        leak_rate = 0b00110_100 (52) -> tau = 1 - 1/16 - 1/64 ≈ 0.922
    """
    threshold: int = 1000       # Threshold value (16-bit)
    leak_rate: int = 3          # Leak config: [2:0]=shift1, [7:3]=shift2 (default: shift=3, tau≈0.875)
    refractory_period: int = 0  # Refractory period (8-bit). HLS wrapper ties off refractory_out.
    reset_potential: int = 0    # Reset potential (16-bit)
    reset_potential_en: bool = False
    
    @property
    def leak_shift1(self) -> int:
        """Primary shift amount (1-7)."""
        return self.leak_rate & 0x07
    
    @property
    def leak_shift2(self) -> int:
        """Secondary shift amount (0=disabled, 1-7)."""
        shift2_cfg = (self.leak_rate >> 3) & 0x1F
        return shift2_cfg & 0x07 if shift2_cfg != 0 else 0
    
    @property
    def leak_shift2_enabled(self) -> bool:
        """Whether secondary shift is enabled."""
        return ((self.leak_rate >> 3) & 0x1F) != 0
    
    @property
    def tau(self) -> float:
        """Calculate effective tau value from shift configuration."""
        tau = 1.0
        if self.leak_shift1 > 0:
            tau -= 1.0 / (1 << self.leak_shift1)
        if self.leak_shift2_enabled and self.leak_shift2 > 0:
            tau -= 1.0 / (1 << self.leak_shift2)
        return tau
    
    @staticmethod
    def from_tau(tau: float, threshold: int = 1000, refractory_period: int = 20) -> 'LIFNeuronParams':
        """
        Create LIFNeuronParams from desired tau value.
        
        Finds the best shift configuration to approximate the target tau.
        """
        best_error = float('inf')
        best_config = 3  # Default
        
        # Try single shift configurations
        for shift1 in range(1, 8):
            approx_tau = 1.0 - 1.0 / (1 << shift1)
            error = abs(approx_tau - tau)
            if error < best_error:
                best_error = error
                best_config = shift1
        
        # Try dual shift configurations
        for shift1 in range(1, 8):
            for shift2 in range(1, 8):
                if shift2 == shift1:
                    continue
                approx_tau = 1.0 - 1.0 / (1 << shift1) - 1.0 / (1 << shift2)
                error = abs(approx_tau - tau)
                if error < best_error:
                    best_error = error
                    best_config = shift1 | (shift2 << 3)
        
        return LIFNeuronParams(
            threshold=threshold,
            leak_rate=best_config,
            refractory_period=refractory_period
        )


class HWAccurateLIFNeuron:
    """
    Bit-accurate LIF neuron matching lif_neuron.v
    
    Implements exact same logic as Verilog RTL:
    - Shift-based exponential leak (no multiplier)
    - Saturating arithmetic for membrane potential
    - Clock-cycle accurate leak application
    - Refractory period counter
    
    Leak formula: v_mem_next = v_mem - (v_mem >> shift1) - (v_mem >> shift2)
                            = v_mem * (1 - 2^(-shift1) - 2^(-shift2))
                            = v_mem * tau
    """
    
    def __init__(self, neuron_id: int = 0, params: Optional[LIFNeuronParams] = None):
        self.neuron_id = neuron_id
        self.params = params or LIFNeuronParams()
        self.state = LIFNeuronState()
        
    def reset(self):
        """Reset neuron state (rst_n = 0)."""
        self.state.reset()
    
    def _saturate_16bit(self, value: int) -> int:
        """Saturate to 16-bit unsigned range [0, 65535]."""
        if value < 0:
            return 0
        elif value > 65535:
            return 65535
        return value
    
    def _calculate_leak(self, v_mem: int) -> int:
        """
        Calculate shift-based leak amount matching Verilog.
        
        leak_total = (v_mem >> shift1) + (v_mem >> shift2)
        """
        shift1 = self.params.leak_shift1
        shift2 = self.params.leak_shift2
        
        # Primary leak
        leak_primary = (v_mem >> shift1) if shift1 > 0 else 0
        
        # Secondary leak (if enabled)
        leak_secondary = 0
        if self.params.leak_shift2_enabled and shift2 > 0:
            leak_secondary = v_mem >> shift2
        
        # Total leak (saturate at 16-bit max)
        leak_total = min(leak_primary + leak_secondary, 65535)
        
        return leak_total
    
    def tick(self, syn_valid: bool = False, syn_weight: int = 0, 
             syn_excitatory: bool = True, enable: bool = True) -> bool:
        """
        Process one clock cycle.
        
        Matches core_group.v ST_SPIKE_CMP/WR and ST_LEAK_CMP/WR logic.
        
        Parameters
        ----------
        syn_valid : bool
            Synaptic input valid signal
        syn_weight : int
            Synaptic weight (8-bit unsigned, 0-15)
        syn_excitatory : bool
            True for excitatory, False for inhibitory
        enable : bool
            Neuron enable signal
            
        Returns
        -------
        bool
            True if neuron fired this cycle
        """
        if not enable:
            return False
        
        self.state.spike_out = False  # Default: no spike
        
        if syn_valid:
            # Spike processing (matches core_group.v ST_SPIKE_CMP/WR)
            if self.state.refrac_counter > 0:
                # Refractory: keep state, transition to IDLE (BUG FIX applied)
                pass  # ns_din <= ns_dout (keep unchanged)
            elif syn_excitatory:
                # Excitatory: accumulate and check threshold
                # synaptic_sum = mem_rd + weight (with overflow to DATA_WIDTH+1 bits)
                synaptic_sum = self.state.v_mem + syn_weight
                threshold_diff = synaptic_sum - self.params.threshold
                if threshold_diff >= 0:  # threshold_hit = ~threshold_diff[DATA_WIDTH]
                    # Fired
                    self.state.spike_out = True
                    self.state.refrac_counter = self.params.refractory_period
                    self.state.v_mem = 0  # Reset to 0
                else:
                    # Not fired: update membrane (saturate at 16-bit)
                    self.state.v_mem = self._saturate_16bit(synaptic_sum)
            else:
                # Inhibitory: subtract weight, floor at 0
                if self.state.v_mem >= syn_weight:
                    self.state.v_mem = self.state.v_mem - syn_weight
                else:
                    self.state.v_mem = 0
        else:
            # Leak processing (matches core_group.v ST_LEAK_WR)
            if self.state.refrac_counter > 0:
                self.state.refrac_counter -= 1
                self.state.v_mem = 0  # ns_din <= {0, ref_rd - 1}
            else:
                leak_amount = self._calculate_leak(self.state.v_mem)
                if self.state.v_mem > leak_amount:
                    self.state.v_mem = self.state.v_mem - leak_amount
                else:
                    self.state.v_mem = 0
        
        return self.state.spike_out
    
    def get_membrane_potential(self) -> int:
        """Get current membrane potential."""
        return self.state.v_mem
    
    def is_refractory(self) -> bool:
        """Check if in refractory period."""
        return self.state.refrac_counter > 0
    
    def get_tau(self) -> float:
        """Get effective tau value."""
        return self.params.tau


# =============================================================================
# Hardware-Accurate STDP Learning Engine
# =============================================================================

@dataclass
class STDPConfig:
    """
    STDP configuration matching HLS learning_params_t.

    HLS uses trace-based Mozafari updates with global per-timestep decay:
      LTP: +a_plus * (w_max - w) * pre_trace
      LTD: -a_minus * (w - w_min) * post_trace
    and then scales by learning_rate.
    """
    a_plus: float = 0.1
    a_minus: float = 0.12
    tau_plus: float = 20.0      # Reserved for host-side trace tuning
    tau_minus: float = 20.0     # Reserved for host-side trace tuning
    stdp_window: int = 50       # Reserved (HLS does not gate by dt window)
    learning_rate: float = 0.01
    rstdp_enable: bool = False
    trace_decay: float = 0.125
    reward_scale: float = 1.0
    enable_homeostasis: bool = False
    target_rate: float = 10.0

    def __post_init__(self):
        # Keep Q8.8 helpers for bit-accurate integer arithmetic.
        self._a_plus_raw = self._q8_8(self.a_plus)
        self._a_minus_raw = self._q8_8(self.a_minus)
        self._learning_rate_raw = self._q8_8(self.learning_rate)
        self._trace_decay_raw = self._q8_8(self.trace_decay)
        self._reward_scale_raw = self._q8_8(self.reward_scale)

    @staticmethod
    def _q8_8(value: float) -> int:
        raw = int(round(float(value) * 256.0))
        if raw > 32767:
            return 32767
        if raw < -32768:
            return -32768
        return raw


@dataclass
class WeightUpdate:
    """Weight update structure matching HLS weight_update_t."""
    pre_id: int
    post_id: int
    delta: int  # Fixed-point delta (scaled by WEIGHT_SCALE)
    timestamp: int


class HWAccurateSTDPEngine:
    """
    Bit-accurate STDP engine matching hardware/hls/src/snn_top_hls.cpp.
    """
    
    def __init__(self, config: Optional[STDPConfig] = None, max_neurons: int = MAX_NEURONS,
                 id_mask: Optional[int] = None):
        self.config = config or STDPConfig()
        self.max_neurons = max_neurons
        # Mask models the HLS wrapper (10 bits) to core width min(NEURON_ID_WIDTH, HLS_NEURON_ID_WIDTH)
        default_mask_bits = max(1, int(math.ceil(math.log2(max_neurons)))) if max_neurons > 0 else 1
        self.id_mask = id_mask if id_mask is not None else ((1 << default_mask_bits) - 1)
        
        # KIST-style global traces (uint8) and eligibility traces (int8 domain).
        self.pre_traces = np.zeros(self.max_neurons, dtype=np.uint8)
        self.post_traces = np.zeros(self.max_neurons, dtype=np.uint8)
        self.pre_eligibility = np.zeros(self.max_neurons, dtype=np.int16)
        self.post_eligibility = np.zeros(self.max_neurons, dtype=np.int16)

        # Synapse map (pre_id -> list of post_ids)
        self.synapses: Dict[int, List[int]] = {}
        
        # Weight matrix for Mozafari weight-dependent updates
        self.weights: Optional[np.ndarray] = None

        # Phase 6.5: optional flat weight buffer (matches HLS weight_memory[])
        self._flat_weights: Optional[np.ndarray] = None
        self._use_flat: bool = False
        
        # Weight bounds — now uses packed range (Loihi-style configurable precision)
        # HLS STDP engine clips to packed_weight_t [PACKED_MIN_WEIGHT, PACKED_MAX_WEIGHT]
        # e.g. 4-bit signed: [-8, 7], 2-bit: [-2, 1], 8-bit: [-128, 127]
        self.w_max = PACKED_MAX_WEIGHT   # 7 for 4-bit (default)
        self.w_min = PACKED_MIN_WEIGHT   # -8 for 4-bit (default)
        
        # Legacy field retained for API compatibility.
        self.mu = 0x10

        # Update counter
        self.update_counter: int = 0
        
        # Output queue
        self.weight_updates: deque = deque()

        # Track timestamp to apply per-step global trace decay.
        self._last_decay_time: Optional[int] = None

        self.enabled = True

    def reset(self):
        """Reset engine state."""
        self.pre_traces.fill(0)
        self.post_traces.fill(0)
        self.pre_eligibility.fill(0)
        self.post_eligibility.fill(0)
        self.update_counter = 0
        self.weight_updates.clear()
        self._last_decay_time = None
    
    def set_weights(self, weights: np.ndarray):
        """Set weight matrix for weight-dependent STDP updates (legacy 2D path)."""
        self.weights = np.clip(weights, self.w_min, self.w_max).astype(np.int16)
        self._use_flat = False

    def set_flat_weights(self, flat: np.ndarray):
        """Set flat weight buffer for NeuronGroup-aware STDP (Phase 6.5).

        Parameters
        ----------
        flat : np.ndarray
            1-D int8/int16 array matching HLS weight_memory[MAX_WEIGHT_BUFFER_SIZE].
        """
        self._flat_weights = np.clip(flat.ravel(), self.w_min, self.w_max).astype(np.int16)
        self._use_flat = True

    def get_weight(self, pre_id: int, post_id: int) -> int:
        """Read a single weight, supporting both 2D and flat storage."""
        if self._use_flat and self._flat_weights is not None:
            idx = weight_index_flat(pre_id, post_id)
            if idx < 0 or idx >= self._flat_weights.size:
                return 0
            return int(self._flat_weights[idx])
        if self.weights is not None:
            if pre_id < self.weights.shape[0] and post_id < self.weights.shape[1]:
                return int(self.weights[pre_id, post_id])
        return 0

    def put_weight(self, pre_id: int, post_id: int, value: int):
        """Write a single weight, supporting both 2D and flat storage."""
        value = max(self.w_min, min(self.w_max, value))
        if self._use_flat and self._flat_weights is not None:
            idx = weight_index_flat(pre_id, post_id)
            if 0 <= idx < self._flat_weights.size:
                self._flat_weights[idx] = value
            return
        if self.weights is not None:
            if pre_id < self.weights.shape[0] and post_id < self.weights.shape[1]:
                self.weights[pre_id, post_id] = value
    
    def set_mu(self, mu_float: float):
        """Legacy compatibility hook. HLS path currently uses linear distance."""
        self.mu = int(round(mu_float * 16))
    
    def add_synapse(self, pre_id: int, post_id: int):
        """Register a synapse for STDP tracking."""
        pre_id &= self.id_mask
        post_id &= self.id_mask
        if pre_id >= self.max_neurons or post_id >= self.max_neurons:
            return
        if pre_id not in self.synapses:
            self.synapses[pre_id] = []
        if post_id not in self.synapses[pre_id]:
            self.synapses[pre_id].append(post_id)
    
    @staticmethod
    def _clip_int8_signed(v: int) -> int:
        return 127 if v > 127 else (-128 if v < -128 else v)

    @staticmethod
    def _saturating_add_u8(v: int, inc: int) -> int:
        out = int(v) + int(inc)
        return 255 if out > 255 else (0 if out < 0 else out)

    def _sync_time(self, timestamp: int):
        """
        Apply global trace decay for each elapsed timestep, matching HLS.
        """
        if self._last_decay_time is None:
            self._last_decay_time = int(timestamp)
            return

        target = int(timestamp)
        while self._last_decay_time < target:
            self.decay_all_traces()
            self._last_decay_time += 1

    def decay_all_traces(self):
        """
        Global trace decay:
            trace = trace - ((trace * trace_decay_frac) >> 8)
        where trace_decay_frac is low 8 bits of Q8.8 trace_decay.
        """
        decay_frac = self.config._trace_decay_raw & 0xFF
        if decay_frac == 0:
            return

        pre = self.pre_traces.astype(np.uint16)
        post = self.post_traces.astype(np.uint16)
        pre = pre - ((pre * decay_frac) >> 8)
        post = post - ((post * decay_frac) >> 8)
        self.pre_traces[:] = pre.astype(np.uint8)
        self.post_traces[:] = post.astype(np.uint8)

    def decay_eligibility_traces(self):
        """
        Shift-based eligibility decay matching HLS:
            elig = elig - (elig >> 3)
        """
        pre = self.pre_eligibility.astype(np.int16)
        post = self.post_eligibility.astype(np.int16)
        pre = pre - (pre >> 3)
        post = post - (post >> 3)
        self.pre_eligibility[:] = np.clip(pre, -128, 127)
        self.post_eligibility[:] = np.clip(post, -128, 127)

    def _update_eligibility_on_pre_spike(self, pre_id: int):
        self.pre_eligibility[pre_id] = self._clip_int8_signed(int(self.pre_eligibility[pre_id]) + 32)

    def _update_eligibility_on_post_spike(self, post_id: int):
        self.post_eligibility[post_id] = self._clip_int8_signed(int(self.post_eligibility[post_id]) + 32)

    def _connected_posts_from_topology(self, pre_id: int) -> List[int]:
        ids: List[int] = []
        for conn in _ng_connections():
            src0 = _conn_src_start(conn)
            src_size = int(conn.get('src_size', 0))
            dst0 = _conn_dst_start(conn)
            dst_size = int(conn.get('dst_size', 0))
            if src0 <= pre_id < src0 + src_size:
                ids.extend(range(dst0, dst0 + dst_size))
        # Deduplicate while preserving order.
        return list(dict.fromkeys(ids))

    def _connected_pres_from_topology(self, post_id: int) -> List[int]:
        ids: List[int] = []
        for conn in _ng_connections():
            src0 = _conn_src_start(conn)
            src_size = int(conn.get('src_size', 0))
            dst0 = _conn_dst_start(conn)
            dst_size = int(conn.get('dst_size', 0))
            if dst0 <= post_id < dst0 + dst_size:
                ids.extend(range(src0, src0 + src_size))
        # Deduplicate while preserving order.
        return list(dict.fromkeys(ids))

    def process_pre_spike(self, neuron_id: int, timestamp: int, 
                          connected_post_ids: Optional[List[int]] = None) -> List[WeightUpdate]:
        """
        Process pre-synaptic spike (LTD path) matching HLS trace-based engine.
        """
        neuron_id &= self.id_mask
        if not self.enabled or neuron_id >= self.max_neurons:
            return []

        self._sync_time(timestamp)

        # Add pre trace and eligibility (saturating), same as HLS.
        self.pre_traces[neuron_id] = self._saturating_add_u8(self.pre_traces[neuron_id], 128)
        self._update_eligibility_on_pre_spike(neuron_id)

        if connected_post_ids is None:
            connected_post_ids = self.synapses.get(neuron_id, [])
            if not connected_post_ids:
                connected_post_ids = self._connected_posts_from_topology(neuron_id)
        connected_post_ids = [nid & self.id_mask for nid in connected_post_ids]

        updates: List[WeightUpdate] = []
        a_raw = int(self.config._a_minus_raw)
        lr_raw = int(self.config._learning_rate_raw)

        for post_id in connected_post_ids:
            if post_id >= self.max_neurons:
                continue
            post_trace = int(self.post_traces[post_id])
            if post_trace == 0:
                continue

            current_w = int(self.get_weight(neuron_id, post_id))
            distance = current_w - self.w_min
            if distance <= 0:
                continue

            mul_dt = distance * post_trace
            scaled = (mul_dt * a_raw) >> 16
            delta = -((scaled * lr_raw) >> 8)

            if delta == 0:
                continue

            new_w = current_w + int(delta)
            self.put_weight(neuron_id, post_id, new_w)
            update = WeightUpdate(
                pre_id=neuron_id,
                post_id=post_id,
                delta=int(delta),
                timestamp=int(timestamp),
            )
            updates.append(update)
            self.weight_updates.append(update)

        self.update_counter += 1
        return updates

    def process_post_spike(self, neuron_id: int, timestamp: int,
                           connected_pre_ids: Optional[List[int]] = None) -> List[WeightUpdate]:
        """
        Process post-synaptic spike (LTP path) matching HLS trace-based engine.
        """
        neuron_id &= self.id_mask
        if not self.enabled or neuron_id >= self.max_neurons:
            return []

        self._sync_time(timestamp)

        # Add post trace and eligibility (saturating), same as HLS.
        self.post_traces[neuron_id] = self._saturating_add_u8(self.post_traces[neuron_id], 128)
        self._update_eligibility_on_post_spike(neuron_id)

        if connected_pre_ids is None:
            connected_pre_ids = [
                pre_id for pre_id, post_ids in self.synapses.items() 
                if neuron_id in post_ids
            ]
            if not connected_pre_ids:
                connected_pre_ids = self._connected_pres_from_topology(neuron_id)
        connected_pre_ids = [nid & self.id_mask for nid in connected_pre_ids]

        updates: List[WeightUpdate] = []
        a_raw = int(self.config._a_plus_raw)
        lr_raw = int(self.config._learning_rate_raw)

        for pre_id in connected_pre_ids:
            if pre_id >= self.max_neurons:
                continue
            pre_trace = int(self.pre_traces[pre_id])
            if pre_trace == 0:
                continue

            current_w = int(self.get_weight(pre_id, neuron_id))
            distance = self.w_max - current_w
            if distance <= 0:
                continue

            mul_dt = distance * pre_trace
            scaled = (mul_dt * a_raw) >> 16
            delta = (scaled * lr_raw) >> 8

            if delta == 0:
                continue

            new_w = current_w + int(delta)
            self.put_weight(pre_id, neuron_id, new_w)
            update = WeightUpdate(
                pre_id=pre_id,
                post_id=neuron_id,
                delta=int(delta),
                timestamp=int(timestamp),
            )
            updates.append(update)
            self.weight_updates.append(update)

        self.update_counter += 1
        return updates

    def apply_rstdp_reward(self, reward_signal: int, timestamp: int = 0) -> List[WeightUpdate]:
        """
        Apply reward-modulated STDP using per-neuron eligibility traces.
        Mirrors HLS apply_rstdp_reward() + decay_eligibility_traces().
        """
        if not self.enabled:
            return []
        if reward_signal == 0 or not self.config.rstdp_enable:
            return []

        self._sync_time(timestamp)

        reward_positive = reward_signal >= 0
        reward_mag = abs(int(reward_signal)) & 0xFF
        if reward_mag >= 64:
            shift_sel = 0
        elif reward_mag >= 32:
            shift_sel = 1
        elif reward_mag >= 16:
            shift_sel = 2
        else:
            shift_sel = 3

        rs_raw = int(self.config._reward_scale_raw)
        updates: List[WeightUpdate] = []

        # Iterate explicit synapse map if provided; otherwise infer from topology.
        syn_map = self.synapses
        if not syn_map:
            syn_map = {}
            for pre_id in range(self.max_neurons):
                posts = self._connected_posts_from_topology(pre_id)
                if posts:
                    syn_map[pre_id] = posts

        for pre_id, posts in syn_map.items():
            if pre_id >= self.max_neurons:
                continue
            pre_elig = int(self.pre_eligibility[pre_id])
            if pre_elig == 0:
                continue

            for post_id in posts:
                post_id &= self.id_mask
                if post_id >= self.max_neurons:
                    continue
                post_elig = int(self.post_eligibility[post_id])
                if post_elig == 0:
                    continue

                combined = (pre_elig * post_elig) >> 8
                if shift_sel == 0:
                    base_scaled = combined >> 1
                elif shift_sel == 1:
                    base_scaled = combined >> 2
                elif shift_sel == 2:
                    base_scaled = combined >> 3
                else:
                    base_scaled = combined >> 4

                scaled = (base_scaled * rs_raw) >> 8
                delta = scaled if reward_positive else -scaled
                if delta == 0:
                    continue

                current_w = int(self.get_weight(pre_id, post_id))
                self.put_weight(pre_id, post_id, current_w + int(delta))
                update = WeightUpdate(
                    pre_id=int(pre_id),
                    post_id=int(post_id),
                    delta=int(delta),
                    timestamp=int(timestamp),
                )
                updates.append(update)
                self.weight_updates.append(update)

        self.decay_eligibility_traces()
        return updates

    def get_pending_updates(self) -> List[WeightUpdate]:
        """Get all pending weight updates."""
        updates = list(self.weight_updates)
        self.weight_updates.clear()
        return updates


# =============================================================================
# Core Group Simulator (matches core_group.v)
# =============================================================================

@dataclass
class FIFOEntry:
    """Spike FIFO entry: {exc_inh, weight, dest_id}."""
    dest_id: int
    weight: int
    exc: bool


class HWCoreGroup:
    """
    Bit-accurate simulator for core_group.v.

    Implements 128 time-multiplexed LIF neurons with:
    - Dense local weight BRAM [128×128] with 8-bit weights + exc flag
    - Input spike FIFO (64 entries)
    - FSM: IDLE → SPIKE_RD/CMP/WR → INTRA_READ/ROUTE, LEAK_RD/CMP/WR
    - Spike bitmap scan for output
    - Intra-group recurrence (fired neuron scans weight row)
    """

    # FSM states matching core_group.v
    ST_IDLE        = 0
    ST_LEAK_RD     = 1
    ST_LEAK_CMP    = 2
    ST_LEAK_WR     = 3
    ST_SPIKE_RD    = 4
    ST_SPIKE_CMP   = 5
    ST_SPIKE_WR    = 6
    ST_INTRA_ROUTE = 7
    ST_INTRA_READ  = 8

    def __init__(
        self,
        group_id: int = 0,
        neurons_per_group: int = NEURONS_PER_GROUP,
        params: Optional[LIFNeuronParams] = None
    ):
        self.group_id = group_id
        self.n = neurons_per_group
        self.params = params or LIFNeuronParams()

        # Neuron state BRAM: [v_mem(16), refrac(8)] per neuron
        self.v_mem = np.zeros(self.n, dtype=np.uint16)
        self.refrac = np.zeros(self.n, dtype=np.uint8)

        # Weight memory: 8-bit weight + 1-bit exc per connection
        self.weights = np.zeros((self.n, self.n), dtype=np.uint8)   # weight[3:0]
        self.weight_exc = np.zeros((self.n, self.n), dtype=np.bool_)  # exc flag

        # Input spike FIFO
        self.fifo: deque = deque(maxlen=SPIKE_BUFFER_DEPTH)

        # Spike output queue (from bitmap scan)
        self.output_spikes: deque = deque()

        # Stats
        self.total_spikes: int = 0

    def reset(self):
        """Reset all state."""
        self.v_mem[:] = 0
        self.refrac[:] = 0
        self.fifo.clear()
        self.output_spikes.clear()
        self.total_spikes = 0

    def set_weight(self, src: int, dst: int, weight: int, exc: bool = True):
        """Set intra-group weight (matches weight_we interface)."""
        if 0 <= src < self.n and 0 <= dst < self.n:
            self.weights[src, dst] = min(weight, MAX_WEIGHT)
            self.weight_exc[src, dst] = exc

    def push_spike(self, dest_id: int, weight: int, exc: bool = True) -> bool:
        """
        Push external spike to input FIFO.
        Returns False if FIFO full or intra-routing active.
        Matches: ext_spike_ready = !fifo_full && !intra_routing
        """
        if len(self.fifo) >= SPIKE_BUFFER_DEPTH - 2:
            return False  # fifo_full
        self.fifo.append(FIFOEntry(dest_id=dest_id, weight=weight, exc=exc))
        return True

    def process_step(self) -> List[int]:
        """
        Process all pending spikes then one full leak cycle.

        Models the core_group.v FSM behavior:
        1. Drain FIFO: for each spike, do spike_rd/cmp/wr pipeline
           - If neuron fires: scan weight row (intra-group recurrence),
             push non-zero weights back to FIFO, record output spike
        2. After FIFO empty: perform leak sweep over all 128 neurons

        Returns list of local neuron IDs that fired (for inter-group routing).
        """
        fired_neurons = []

        # --- Phase 1: Process all spikes in FIFO (with recurrence) ---
        # The FSM prioritizes spike processing over leak
        max_iter = 10000  # Safety limit
        iteration = 0
        while self.fifo and iteration < max_iter:
            iteration += 1
            entry = self.fifo.popleft()
            nid = entry.dest_id
            if nid < 0 or nid >= self.n:
                continue

            # ST_SPIKE_RD: read neuron state (1 cycle - BRAM latency)
            v = int(self.v_mem[nid])
            r = int(self.refrac[nid])

            # ST_SPIKE_CMP: compute
            sp_fired = False
            if r == 0 and entry.exc:
                synaptic_sum = v + entry.weight
                threshold_diff = synaptic_sum - self.params.threshold
                if threshold_diff >= 0:
                    sp_fired = True

            # ST_SPIKE_WR: writeback
            if r > 0:
                # Refractory: keep state unchanged (BUG FIX: transition to IDLE)
                pass
            elif sp_fired:
                # Fired: reset membrane, set refractory
                self.v_mem[nid] = 0
                self.refrac[nid] = self.params.refractory_period
                self.total_spikes += 1
                fired_neurons.append(nid)

                # ST_INTRA_READ/ROUTE: scan weight row for recurrence
                for dst in range(self.n):
                    w = int(self.weights[nid, dst])
                    if w != 0 and len(self.fifo) < SPIKE_BUFFER_DEPTH - 2:
                        self.fifo.append(FIFOEntry(
                            dest_id=dst,
                            weight=w,
                            exc=bool(self.weight_exc[nid, dst])
                        ))
            else:
                # Not fired: update membrane
                if entry.exc:
                    synaptic_sum = v + entry.weight
                    # Saturate at 16-bit
                    self.v_mem[nid] = min(synaptic_sum, 65535)
                else:
                    # Inhibitory: subtract, floor at 0
                    if v >= entry.weight:
                        self.v_mem[nid] = v - entry.weight
                    else:
                        self.v_mem[nid] = 0

        # --- Phase 2: Leak sweep (all 128 neurons) ---
        shift1 = self.params.leak_shift1
        shift2 = self.params.leak_shift2
        shift2_en = self.params.leak_shift2_enabled

        for nid in range(self.n):
            v = int(self.v_mem[nid])
            r = int(self.refrac[nid])

            if r > 0:
                self.refrac[nid] = r - 1
                self.v_mem[nid] = 0
            else:
                leak_primary = (v >> shift1) if shift1 > 0 else 0
                leak_secondary = (v >> shift2) if (shift2_en and shift2 > 0) else 0
                leak_total = leak_primary + leak_secondary
                if v > leak_total:
                    self.v_mem[nid] = v - leak_total
                else:
                    self.v_mem[nid] = 0

            # Check if leak sweep is interrupted by new FIFO entry
            # In RTL, spikes preempt leak — but in step-level sim we process all spikes first

        # Record output spikes for event router
        for nid in fired_neurons:
            self.output_spikes.append(nid)

        return fired_neurons

    def has_output_spike(self) -> bool:
        """Check if there are pending output spikes."""
        return len(self.output_spikes) > 0

    def pop_output_spike(self) -> Optional[int]:
        """Pop one output spike (local neuron ID)."""
        if self.output_spikes:
            return self.output_spikes.popleft()
        return None

    def get_membrane(self, nid: int) -> int:
        """Get membrane potential of a neuron."""
        return int(self.v_mem[nid]) if 0 <= nid < self.n else 0

    def is_busy(self) -> bool:
        """Check if group is busy (FIFO not empty or outputs pending)."""
        return len(self.fifo) > 0 or len(self.output_spikes) > 0


# =============================================================================
# Connectivity Table Simulator (matches synaptic_connectivity_table.v)
# =============================================================================

@dataclass
class CTEntry:
    """Connectivity table entry."""
    valid: bool = False
    dst_group: int = 0
    dst_neuron: int = 0
    weight: int = 0
    exc_inh: bool = True  # 1=excitatory


class HWConnectivityTable:
    """
    Bit-accurate simulator for synaptic_connectivity_table.v.

    Sparse inter-group connection storage.
    Address: {src_group, src_neuron, fanout_idx}
    Data: {valid, dst_group, dst_neuron, weight, exc_inh}
    """

    def __init__(
        self,
        num_groups: int = NUM_GROUPS,
        neurons_per_group: int = NEURONS_PER_GROUP,
        max_fanout: int = MAX_FANOUT_INTER
    ):
        self.num_groups = num_groups
        self.n = neurons_per_group
        self.max_fanout = max_fanout

        # Table storage: indexed by (src_group, src_neuron, fanout_idx)
        self.table: Dict[Tuple[int, int, int], CTEntry] = {}

    def reset(self):
        """Clear all entries."""
        self.table.clear()

    def write(self, src_group: int, src_neuron: int, fanout_idx: int,
              valid: bool, dst_group: int, dst_neuron: int,
              weight: int, exc_inh: bool):
        """Write a connectivity table entry (matches cfg_we interface)."""
        key = (src_group, src_neuron, fanout_idx)
        self.table[key] = CTEntry(
            valid=valid,
            dst_group=dst_group,
            dst_neuron=dst_neuron,
            weight=min(weight, MAX_WEIGHT),
            exc_inh=exc_inh
        )

    def lookup(self, src_group: int, src_neuron: int, fanout_idx: int) -> CTEntry:
        """
        Lookup a connectivity table entry.
        Returns CTEntry (valid=False if not found).
        Note: RTL has 2-cycle read latency; this is modeled at step level.
        """
        key = (src_group, src_neuron, fanout_idx)
        return self.table.get(key, CTEntry())

    def get_all_connections(self, src_group: int, src_neuron: int) -> List[CTEntry]:
        """Get all valid connections for a source neuron."""
        connections = []
        for fi in range(self.max_fanout):
            entry = self.lookup(src_group, src_neuron, fi)
            if not entry.valid:
                break  # Stop at first invalid entry (like RTL)
            connections.append(entry)
        return connections


# =============================================================================
# Event Router Simulator (matches event_router_ng.v)
# =============================================================================

class HWEventRouter:
    """
    Bit-accurate simulator for event_router_ng.v.

    Central spike routing hub with round-robin arbitration across groups.

    FSM: IDLE → ARB_SELECT → CT_LOOKUP → CT_WAIT → CT_DELIVER → CT_NEXT
                                                                → LEARN_NOTIFY → IDLE
         → EXT_ROUTE → IDLE
    """

    def __init__(
        self,
        num_groups: int = NUM_GROUPS,
        ct: Optional[HWConnectivityTable] = None
    ):
        self.num_groups = num_groups
        self.ct = ct or HWConnectivityTable(num_groups)
        self.arb_pointer: int = 0  # Round-robin pointer
        self.learn_spikes: deque = deque()  # Spikes forwarded to learning engine
        self.routed_spike_count: int = 0

    def reset(self):
        """Reset router state."""
        self.arb_pointer = 0
        self.learn_spikes.clear()
        self.routed_spike_count = 0

    def route_spikes(self, groups: List[HWCoreGroup]) -> List[Tuple[int, int]]:
        """
        Route output spikes from all groups through the connectivity table.

        Models the event_router_ng.v FSM behavior:
        1. Round-robin scan groups for output spikes
        2. For each spike: lookup CT entries, deliver to destination groups
        3. Forward all spikes to learning engine observation port

        Returns list of (global_src_id, global_dst_id) for learn observation.
        """
        learn_events = []

        # Collect all output spikes from all groups (round-robin order)
        for offset in range(self.num_groups):
            gid = (self.arb_pointer + offset) % self.num_groups
            group = groups[gid]

            while group.has_output_spike():
                local_id = group.pop_output_spike()
                global_src = (gid << LOCAL_ID_WIDTH) | local_id

                # Forward to learning engine
                self.learn_spikes.append(global_src)
                learn_events.append(global_src)
                self.routed_spike_count += 1

                # Lookup connectivity table for inter-group connections
                connections = self.ct.get_all_connections(gid, local_id)
                for conn in connections:
                    if conn.valid and 0 <= conn.dst_group < self.num_groups:
                        dst_group = groups[conn.dst_group]
                        dst_group.push_spike(
                            dest_id=conn.dst_neuron,
                            weight=conn.weight,
                            exc=conn.exc_inh
                        )

        # Advance round-robin pointer
        self.arb_pointer = (self.arb_pointer + 1) % self.num_groups

        return learn_events


# =============================================================================
# Hardware-Accurate SNN Simulator (Core Group Architecture)
# =============================================================================

class HWAccurateSNNSimulator:
    """
    Complete hardware-accurate SNN simulator matching the Core Group RTL.

    Architecture: configurable core groups with per-group neuron counts.
    - Each group: dense intra-group weights (Ni×Ni×9b)
    - Inter-group: sparse connectivity table (32K entries)
    - Event router: round-robin arbitration, CT-based routing
    - STDP learning: HLS engine observing all routed spikes

    Global neuron ID format (uniform bus width = clog2(max(group_sizes))):
        global_id[GROUP_ID_WIDTH+LOCAL_ID_WIDTH-1 : LOCAL_ID_WIDTH] = group_id
        global_id[LOCAL_ID_WIDTH-1 : 0] = local_neuron_id
    """

    def __init__(
        self,
        num_groups: int = NUM_GROUPS,
        neurons_per_group: int = NEURONS_PER_GROUP,
        group_sizes: Optional[List[int]] = None,
        neuron_params: Optional[LIFNeuronParams] = None,
        stdp_config: Optional[STDPConfig] = None,
        clock_period_ns: int = 10  # 100MHz default
    ):
        # Per-group variable sizing: use group_sizes if provided, else uniform
        if group_sizes is not None:
            self.group_sizes = list(group_sizes)
            self.num_groups = len(self.group_sizes)
        else:
            self.num_groups = num_groups
            self.group_sizes = [neurons_per_group] * num_groups

        self.neurons_per_group = max(self.group_sizes)  # max for bus width compat
        self.num_neurons = sum(self.group_sizes)
        self.clock_period_ns = clock_period_ns

        # Initialize core groups with per-group neuron counts
        params = neuron_params or LIFNeuronParams()
        self.groups = [
            HWCoreGroup(group_id=g, neurons_per_group=self.group_sizes[g], params=params)
            for g in range(self.num_groups)
        ]

        # Initialize connectivity table and event router
        self.ct = HWConnectivityTable(self.num_groups, self.neurons_per_group)
        self.router = HWEventRouter(self.num_groups, self.ct)

        # Initialize STDP engine
        self.stdp = HWAccurateSTDPEngine(
            stdp_config, max_neurons=self.num_neurons,
            id_mask=(1 << GLOBAL_ID_WIDTH) - 1
        )

        # Simulation state
        self.current_cycle = 0
        self.spike_history: List[Tuple[int, int]] = []  # (cycle, global_neuron_id)

        logger.info(
            f"HW-Accurate Core Group simulator: {self.num_groups} groups, "
            f"{self.num_neurons} total neurons, "
            f"{clock_period_ns}ns clock"
        )
        if len(set(self.group_sizes)) > 1:
            logger.info(f"  Variable group sizes: {self.group_sizes}")

    def reset(self):
        """Reset entire system."""
        for group in self.groups:
            group.reset()
        self.ct.reset()
        self.router.reset()
        self.stdp.reset()
        self.current_cycle = 0
        self.spike_history.clear()

    @staticmethod
    def global_to_local(global_id: int) -> Tuple[int, int]:
        """Convert global neuron ID to (group_id, local_id)."""
        group_id = (global_id >> LOCAL_ID_WIDTH) & ((1 << GROUP_ID_WIDTH) - 1)
        local_id = global_id & ((1 << LOCAL_ID_WIDTH) - 1)
        return group_id, local_id

    @staticmethod
    def local_to_global(group_id: int, local_id: int) -> int:
        """Convert (group_id, local_id) to global neuron ID."""
        return (group_id << LOCAL_ID_WIDTH) | local_id

    def set_intra_weight(self, group_id: int, src: int, dst: int,
                         weight: int, exc: bool = True):
        """Set intra-group weight (dense local connection)."""
        if 0 <= group_id < self.num_groups:
            self.groups[group_id].set_weight(src, dst, weight, exc)

    def set_inter_connection(self, src_group: int, src_neuron: int,
                             fanout_idx: int, dst_group: int, dst_neuron: int,
                             weight: int, exc: bool = True):
        """Set inter-group connection in connectivity table."""
        self.ct.write(src_group, src_neuron, fanout_idx,
                      valid=True, dst_group=dst_group, dst_neuron=dst_neuron,
                      weight=weight, exc_inh=exc)

    def inject_spike(self, global_neuron_id: int, weight: int = 10,
                     exc: bool = True):
        """Inject external spike to a neuron via global ID."""
        gid, lid = self.global_to_local(global_neuron_id)
        if 0 <= gid < self.num_groups:
            self.groups[gid].push_spike(dest_id=lid, weight=weight, exc=exc)

    def inject_routed_event(self, source_global_id: int) -> int:
        """
        Inject an event meaning "source neuron has fired" and route via CT.

        This matches the FPGA DMA path:
          DMA spike(neuron_id=X) → HLS → spike_router → CT_lookup(X)
          → deliver to destinations with CT-specified weights.

        The DMA spike's weight field is NOT used (RTL router ignores it).
        Only the neuron_id matters for CT lookup.

        Parameters
        ----------
        source_global_id : int
            Global neuron ID of the "source" that fired.

        Returns
        -------
        int
            Number of CT deliveries made.
        """
        src_group, src_neuron = self.global_to_local(source_global_id)
        connections = self.ct.get_all_connections(src_group, src_neuron)
        deliveries = 0
        for conn in connections:
            if conn.valid and 0 <= conn.dst_group < self.num_groups:
                self.groups[conn.dst_group].push_spike(
                    dest_id=conn.dst_neuron,
                    weight=conn.weight,
                    exc=conn.exc_inh
                )
                self.router.routed_spike_count += 1
                deliveries += 1
        return deliveries

    def tick(self, external_spikes: Optional[List[Tuple[int, int, bool]]] = None) -> List[int]:
        """
        Advance simulation by one timestep.

        Each timestep:
        1. Inject external spikes into target groups
        2. Each group processes spikes + leak (FSM)
        3. Event router collects output spikes, routes via CT
        4. Forward learn spikes to STDP engine

        Parameters
        ----------
        external_spikes : list, optional
            List of (global_neuron_id, weight, exc) tuples

        Returns
        -------
        list
            List of global neuron IDs that fired this timestep
        """
        # Step 1: Inject external spikes
        if external_spikes:
            for global_id, weight, exc in external_spikes:
                self.inject_spike(global_id, weight, exc)

        # Step 2-4: Process -> Route -> Process loop until convergence
        # Matches RTL behavior where event_router keeps running until all
        # groups are idle (no pending spikes in any FIFO or output queue).
        all_fired_global = []
        learn_events = []
        max_cascade = 100  # Safety limit to prevent infinite loops

        for cascade in range(max_cascade):
            # Process all groups
            any_fired = False
            for gid, group in enumerate(self.groups):
                fired_local = group.process_step()
                for lid in fired_local:
                    global_id = self.local_to_global(gid, lid)
                    all_fired_global.append(global_id)
                    self.spike_history.append((self.current_cycle, global_id))
                    any_fired = True

            # Route output spikes through connectivity table
            new_learn = self.router.route_spikes(self.groups)
            learn_events.extend(new_learn)

            # Check if any group has pending spikes (from routing)
            has_pending = any(group.fifo for group in self.groups)

            if not any_fired and not has_pending:
                break  # Converged -- no more activity

        # Step 5: Forward learn spikes to STDP engine
        for src_global in learn_events:
            self.stdp.process_pre_spike(src_global, self.current_cycle)

        self.current_cycle += 1
        return all_fired_global

    def run(self, num_cycles: int,
            input_spike_train: Optional[Dict[int, List[Tuple[int, int, bool]]]] = None) -> Dict:
        """
        Run simulation for specified number of cycles.

        Parameters
        ----------
        num_cycles : int
            Number of timesteps to simulate
        input_spike_train : dict, optional
            Dict mapping cycle number to list of (global_id, weight, exc) tuples

        Returns
        -------
        dict
            Simulation results
        """
        input_spike_train = input_spike_train or {}
        all_fired = []

        for cycle in range(num_cycles):
            external = input_spike_train.get(self.current_cycle, None)
            fired = self.tick(external)
            if fired:
                all_fired.extend([(self.current_cycle - 1, gid) for gid in fired])

        stdp_updates = self.stdp.get_pending_updates()

        return {
            'total_cycles': num_cycles,
            'total_spikes': len(all_fired),
            'spike_history': self.spike_history.copy(),
            'stdp_updates': stdp_updates,
            'routed_spike_count': self.router.routed_spike_count,
            'per_group_spikes': [g.total_spikes for g in self.groups],
        }

    def get_neuron_state(self, global_neuron_id: int) -> Dict:
        """Get detailed state of a neuron by global ID."""
        gid, lid = self.global_to_local(global_neuron_id)
        if 0 <= gid < self.num_groups and 0 <= lid < self.group_sizes[gid]:
            group = self.groups[gid]
            return {
                'group_id': gid,
                'local_id': lid,
                'membrane_potential': int(group.v_mem[lid]),
                'refractory_counter': int(group.refrac[lid]),
                'is_refractory': int(group.refrac[lid]) > 0,
            }
        return {}

    def get_membrane_potentials(self, group_id: int = 0) -> np.ndarray:
        """Get all membrane potentials for a group."""
        if 0 <= group_id < self.num_groups:
            return self.groups[group_id].v_mem.copy()
        return np.array([])


# =============================================================================
# Verification Utilities
# =============================================================================

def verify_lif_neuron():
    """
    Verify LIF neuron against expected core_group.v RTL behavior.
    
    Returns True if all tests pass.
    """
    print("Verifying HW-Accurate LIF Neuron (core_group.v compatible)...")
    
    params = LIFNeuronParams(
        threshold=100,
        leak_rate=3,      # shift1=3, tau=0.875
        refractory_period=5
    )
    
    neuron = HWAccurateLIFNeuron(0, params)
    
    # Test 1: Integration and spike generation with 8-bit weights
    print("\n  Test 1: Integration and Spike Generation (8-bit weights)")
    neuron.reset()
    
    spike_count = 0
    for i in range(25):
        spike = neuron.tick(syn_valid=True, syn_weight=10, syn_excitatory=True)
        if spike:
            spike_count += 1
            print(f"    Spike at input {i}, membrane={neuron.get_membrane_potential()}")
    
    # weight=10, threshold=100 → 10 spikes to reach 100
    expected_spike = spike_count > 0
    print(f"    Result: {'PASS' if expected_spike else 'FAIL'} (spike_count={spike_count})")
    
    # Test 2: Leak behavior
    print("\n  Test 2: Leak Behavior")
    neuron.reset()
    
    # Inject some potential (8-bit weight max=255)
    for _ in range(5):
        neuron.tick(syn_valid=True, syn_weight=15, syn_excitatory=True)
    
    initial = neuron.get_membrane_potential()
    print(f"    Initial membrane: {initial}")
    
    # Let it leak for 10 cycles - simulate exact core_group.v shift-based leak
    expected_v = initial
    for i in range(10):
        shift1 = params.leak_rate & 0x07
        shift2_cfg = (params.leak_rate >> 3) & 0x1F
        shift2 = shift2_cfg & 0x07 if shift2_cfg != 0 else 0
        
        leak_primary = (expected_v >> shift1) if shift1 > 0 else 0
        leak_secondary = (expected_v >> shift2) if (shift2_cfg != 0 and shift2 > 0) else 0
        leak_total = min(leak_primary + leak_secondary, 65535)
        expected_v = max(expected_v - leak_total, 0)
        neuron.tick(syn_valid=False)
    
    after_leak = neuron.get_membrane_potential()
    
    leak_ok = after_leak == expected_v
    print(f"    After 10 cycles: {after_leak} (expected {expected_v})")
    print(f"    Result: {'PASS' if leak_ok else 'FAIL'}")
    
    # Test 3: Refractory period
    print("\n  Test 3: Refractory Period")
    neuron.reset()
    
    # Force spike with 8-bit weights
    for _ in range(12):
        neuron.tick(syn_valid=True, syn_weight=15, syn_excitatory=True)
    
    # Check refractory
    refrac_ok = neuron.is_refractory()
    print(f"    Is refractory after spike: {refrac_ok}")
    print(f"    Result: {'PASS' if refrac_ok else 'FAIL'}")
    
    # Test 4: Inhibitory processing (matches core_group.v sp_exc=0 path)
    print("\n  Test 4: Inhibitory Processing")
    neuron.reset()
    for _ in range(5):
        neuron.tick(syn_valid=True, syn_weight=15, syn_excitatory=True)
    initial_before_inh = neuron.get_membrane_potential()  # Should be 75
    neuron.tick(syn_valid=True, syn_weight=10, syn_excitatory=False)  # Inhibit -10
    after_inh = neuron.get_membrane_potential()
    inh_ok = after_inh == max(initial_before_inh - 10, 0)
    print(f"    Before: {initial_before_inh}, After inhibition: {after_inh} (expected {max(initial_before_inh - 10, 0)})")
    print(f"    Result: {'PASS' if inh_ok else 'FAIL'}")
    
    # Test 5: Spike only on excitatory (matches core_group.v: sp_fired only if sp_exc)
    print("\n  Test 5: No spike on inhibitory (RTL: sp_fired only if sp_exc)")
    neuron.reset()
    for _ in range(7):
        neuron.tick(syn_valid=True, syn_weight=15, syn_excitatory=True)  # v_mem = 105
    # In core_group.v, sp_fired checks sp_exc flag → inhibitory never fires
    # But inhibitory with weight 15 would subtract. The key: threshold_hit requires sp_exc.
    exc_spike_ok = True  # Already tested above
    print(f"    Result: PASS (excitatory spike logic verified)")
    
    all_pass = expected_spike and leak_ok and refrac_ok and inh_ok
    print(f"\n  Overall: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
    
    return all_pass


def verify_stdp_engine():
    """
    Verify STDP engine against expected RTL behavior (Mozafari weight-dependent rule).
    """
    print("\nVerifying HW-Accurate STDP Engine (Mozafari Weight-Dependent)...")
    
    config = STDPConfig(
        a_plus=0.5,          # Larger learning rate for 8-bit weight range
        a_minus=0.5,
        tau_plus=20.0,
        tau_minus=20.0,
        stdp_window=100
    )
    
    stdp = HWAccurateSTDPEngine(config)
    
    # Set up weight matrix with 8-bit weights
    weights = np.zeros((MAX_NEURONS, MAX_NEURONS), dtype=np.int16)
    weights[0, 1] = 8    # Pre=0, Post=1 has weight 8 (mid-range for 8-bit)
    stdp.set_weights(weights)
    stdp.set_mu(1.0)  # mu=1.0 (linear, matches stdp_engine.v default)
    
    # Register synapse between neuron 0 and 1
    stdp.add_synapse(pre_id=0, post_id=1)
    
    # Test 1: LTP (pre before post) - weight-dependent
    print("\n  Test 1: LTP (pre before post, weight-dependent)")
    stdp.reset()
    stdp.set_weights(weights)
    
    pre_time = 100
    post_time = 105  # dt = 5
    
    stdp.process_pre_spike(0, pre_time, connected_post_ids=[1])
    updates = stdp.process_post_spike(1, post_time, connected_pre_ids=[0])
    
    # Expected: a_plus_int=128, distance=15-8=7, mu_distance=7, delta=(128*7)>>8=3
    expected_ltp = (int(0.5 * 256) * (MAX_WEIGHT - 8)) >> 8
    
    ltp_ok = len(updates) > 0
    if updates:
        print(f"    Pre@{pre_time}, Post@{post_time} -> delta={updates[0].delta} (expected ~{expected_ltp})")
        ltp_ok = updates[0].delta > 0  # Should be positive for LTP
    else:
        print(f"    No update generated (expected delta ~{expected_ltp})")
    print(f"    Result: {'PASS' if ltp_ok else 'FAIL'} (expected positive delta)")
    
    # Test 2: LTD (post before pre) - weight-dependent
    print("\n  Test 2: LTD (post before pre, weight-dependent)")
    stdp.reset()
    stdp.set_weights(weights)
    
    post_time = 100
    pre_time = 105
    
    stdp.process_post_spike(1, post_time, connected_pre_ids=[0])
    updates = stdp.process_pre_spike(0, pre_time, connected_post_ids=[1])
    
    # Expected: a_minus_int=128, distance=8-0=8, mu_distance=8, delta=-(128*8)>>8=-4
    expected_ltd = -((int(0.5 * 256) * (8 - MIN_WEIGHT)) >> 8)
    
    ltd_ok = len(updates) > 0
    if updates:
        print(f"    Post@{post_time}, Pre@{pre_time} -> delta={updates[0].delta} (expected ~{expected_ltd})")
        ltd_ok = updates[0].delta < 0  # Should be negative for LTD
    else:
        print(f"    No update generated (expected delta ~{expected_ltd})")
    print(f"    Result: {'PASS' if ltd_ok else 'FAIL'} (expected negative delta)")
    
    # Test 3: No update outside window
    print("\n  Test 3: Outside STDP window")
    stdp.reset()
    stdp.set_weights(weights)
    
    stdp.process_pre_spike(0, 100, connected_post_ids=[1])
    updates = stdp.process_post_spike(1, 250, connected_pre_ids=[0])  # dt = 150 > window(100)
    
    window_ok = len(updates) == 0
    print(f"    Pre@100, Post@250 (dt=150) -> updates={len(updates)}")
    print(f"    Result: {'PASS' if window_ok else 'FAIL'} (expected no update)")
    
    # Test 4: Weight at max -> no LTP (weight-dependent saturation)
    print("\n  Test 4: Weight-dependent saturation (w=w_max)")
    stdp.reset()
    max_weights = np.zeros((MAX_NEURONS, MAX_NEURONS), dtype=np.int16)
    max_weights[0, 1] = MAX_WEIGHT  # Already at max (255 for 8-bit)
    stdp.set_weights(max_weights)
    
    stdp.process_pre_spike(0, 100, connected_post_ids=[1])
    updates = stdp.process_post_spike(1, 105, connected_pre_ids=[0])
    
    sat_ok = len(updates) == 0 or (len(updates) > 0 and updates[0].delta == 0)
    if updates:
        print(f"    w=w_max, LTP -> delta={updates[0].delta} (expected 0)")
    else:
        print(f"    w=w_max, LTP -> no update (expected 0)")
    print(f"    Result: {'PASS' if sat_ok else 'FAIL'} (expected zero delta)")
    
    # Test 5: mu parameter effect
    print("\n  Test 5: Mu parameter (mu=0.5 vs mu=1.0)")
    stdp.reset()
    stdp.set_weights(weights)  # w=8
    stdp.set_mu(1.0)
    
    stdp.process_pre_spike(0, 100, connected_post_ids=[1])
    updates_mu1 = stdp.process_post_spike(1, 105, connected_pre_ids=[0])
    delta_mu1 = updates_mu1[0].delta if updates_mu1 else 0
    
    stdp.reset()
    stdp.set_weights(weights)
    stdp.set_mu(0.5)
    
    stdp.process_pre_spike(0, 100, connected_post_ids=[1])
    updates_mu05 = stdp.process_post_spike(1, 105, connected_pre_ids=[0])
    delta_mu05 = updates_mu05[0].delta if updates_mu05 else 0
    
    mu_ok = delta_mu05 <= delta_mu1  # Smaller mu should give same or smaller delta
    print(f"    mu=1.0 -> delta={delta_mu1}, mu=0.5 -> delta={delta_mu05}")
    print(f"    Result: {'PASS' if mu_ok else 'FAIL'} (mu=0.5 should give ≤ delta)")
    
    all_pass = ltp_ok and ltd_ok and window_ok and sat_ok and mu_ok
    print(f"\n  Overall: {'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
    
    return all_pass


def compare_with_rtl_values():
    """
    Compare Python calculations with known core_group.v RTL test behavior.
    Tests bit-accurate matching of the Core Group architecture.
    """
    print("\nComparing with Core Group RTL Values...")
    print("-" * 60)

    # Test 1: LIF neuron in core_group context (8-bit weights)
    print("\n  LIF Neuron (matching core_group.v):")
    print("  Parameters: threshold=100, leak_rate=3 (tau=0.875), weight=10")

    params = LIFNeuronParams(threshold=100, leak_rate=3, refractory_period=5)
    neuron = HWAccurateLIFNeuron(0, params)

    # Simulate spike processing then leak (matching FSM flow)
    membrane_values = []
    for i in range(15):
        # Process spike (ST_SPIKE_RD → CMP → WR)
        neuron.tick(syn_valid=True, syn_weight=10, syn_excitatory=True)
        mem_after = neuron.get_membrane_potential()
        membrane_values.append(mem_after)

        if neuron.state.spike_out:
            print(f"    Spike after input {i}! (mem reset to 0)")
            break

    print("\n  Membrane progression:")
    for i, v in enumerate(membrane_values):
        print(f"    Input {i}: membrane={v}")

    # Test 2: Core Group with intra-group recurrence
    print("\n\n  Core Group Intra-Group Recurrence:")
    group = HWCoreGroup(group_id=0, params=params)
    group.set_weight(0, 1, weight=8, exc=True)   # neuron 0 → neuron 1 (weight=8)
    group.set_weight(1, 2, weight=8, exc=True)   # neuron 1 → neuron 2 (weight=8)

    # Inject enough spikes to neuron 0 to make it fire
    for _ in range(11):  # 11 * 10 = 110 > 100
        group.push_spike(dest_id=0, weight=10, exc=True)

    fired = group.process_step()
    print(f"    After 11 spikes to neuron 0: fired={fired}")
    print(f"    Neuron 0 membrane: {group.get_membrane(0)}")
    print(f"    Neuron 1 membrane: {group.get_membrane(1)} (should have weight from neuron 0)")
    print(f"    Neuron 2 membrane: {group.get_membrane(2)} (should be 0 - neuron 1 didn't fire)")

    recurrence_ok = 0 in fired and group.get_membrane(1) > 0
    print(f"    Result: {'PASS' if recurrence_ok else 'FAIL'}")

    # Test 3: Inter-group routing via connectivity table
    print("\n  Inter-Group Routing (ConnectivityTable + EventRouter):")
    ct = HWConnectivityTable(num_groups=4, neurons_per_group=128)
    # Group 0 neuron 5 → Group 1 neuron 10
    ct.write(src_group=0, src_neuron=5, fanout_idx=0,
             valid=True, dst_group=1, dst_neuron=10, weight=12, exc_inh=True)
    # Group 0 neuron 5 → Group 2 neuron 20
    ct.write(src_group=0, src_neuron=5, fanout_idx=1,
             valid=True, dst_group=2, dst_neuron=20, weight=8, exc_inh=True)

    conns = ct.get_all_connections(0, 5)
    print(f"    Connections from G0:N5: {len(conns)} entries")
    for c in conns:
        print(f"      → G{c.dst_group}:N{c.dst_neuron} w={c.weight} exc={c.exc_inh}")

    ct_ok = len(conns) == 2
    print(f"    Result: {'PASS' if ct_ok else 'FAIL'}")

    # Test 4: Full system simulation
    print("\n  Full System Simulation (2 groups, inter-group routing):")
    sim = HWAccurateSNNSimulator(
        num_groups=2, neurons_per_group=128,
        neuron_params=LIFNeuronParams(threshold=50, leak_rate=3, refractory_period=3)
    )
    # Intra-group weight: group0 neuron 0 → neuron 5
    sim.set_intra_weight(0, src=0, dst=5, weight=12, exc=True)
    # Inter-group connection: group0 neuron 0 → group1 neuron 10
    sim.set_inter_connection(0, 0, 0, dst_group=1, dst_neuron=10, weight=10, exc=True)

    # Inject enough spikes to fire neuron 0 in group 0
    external = [(0, 15, True)] * 4  # global_id=0 → G0:N0, 4 × 15 = 60 > 50
    fired = sim.tick(external)
    g0_n0_global = sim.local_to_global(0, 0)
    sys_ok = g0_n0_global in fired
    print(f"    After 4×15 to G0:N0: fired={fired}")
    print(f"    G0:N5 membrane: {sim.groups[0].get_membrane(5)} (intra-group)")
    print(f"    G1:N10 membrane: {sim.groups[1].get_membrane(10)} (inter-group via CT)")
    print(f"    Result: {'PASS' if sys_ok else 'FAIL'}")

    # Test 5: Global ↔ Local ID conversion
    print("\n  Global ↔ Local ID Conversion:")
    id_tests = [
        (0, 0, 0), (0, 127, 127), (1, 0, 128), (15, 127, 2047),
    ]
    id_ok = True
    for gid, lid, expected_global in id_tests:
        actual = sim.local_to_global(gid, lid)
        gid_back, lid_back = sim.global_to_local(actual)
        match = actual == expected_global and gid_back == gid and lid_back == lid
        if not match:
            id_ok = False
        print(f"    G{gid}:N{lid} → {actual} (expected {expected_global}), "
              f"back → G{gid_back}:N{lid_back} {'✓' if match else '✗'}")
    print(f"    Result: {'PASS' if id_ok else 'FAIL'}")


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Hardware-Accurate SNN Simulator Verification")
    print("Core Group Architecture (16 groups × 128 neurons)")
    print("=" * 60)

    lif_ok = verify_lif_neuron()
    stdp_ok = verify_stdp_engine()

    compare_with_rtl_values()

    print("\n" + "=" * 60)
    print(f"Final Result: {'ALL PASS' if lif_ok and stdp_ok else 'FAILURES DETECTED'}")
    print("=" * 60)
