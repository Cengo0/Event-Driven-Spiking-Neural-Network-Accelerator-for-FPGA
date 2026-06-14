"""
SNN FPGA Accelerator package entrypoint.

This module intentionally keeps imports lightweight so that hardware-accurate
simulation utilities can be used even when optional ML dependencies (PyTorch)
are not installed.
"""

from __future__ import annotations

import importlib.util
import warnings

__version__ = "0.2.0"
__author__ = "Jiwoon Lee"


def _raise_torch_missing(*_args, **_kwargs):
    raise ImportError(
        "PyTorch is required for this API. Install `torch` to use training/"
        "neuron/layer/deploy interfaces."
    )


class _TorchUnavailable:
    def __init__(self, *_args, **_kwargs):
        _raise_torch_missing()


_TORCH_AVAILABLE = importlib.util.find_spec("torch") is not None

# ============================================================================
# Always-available imports (no hard torch dependency)
# ============================================================================
from .network import (
    NeuronGroup,
    Synapses,
    SNNNetwork,
    CompiledNetwork,
    ConnectionInfo,
    create_mnist_network,
    create_mnist_block_sparse_network,
)

from . import hw_accurate_simulator as hw_sim
from .hw_accurate_simulator import (
    HWAccurateLIFNeuron,
    HWAccurateSTDPEngine,
    HWAccurateSNNSimulator,
    LIFNeuronParams,
    LIFNeuronState,
    verify_lif_neuron,
    verify_stdp_engine,
    FixedPoint,
    tau_to_leak_rate,
    leak_rate_to_tau,
    get_available_tau_values,
    weight_index_flat,
)

from .pytorch_interface import (
    pytorch_to_snn,
    SNNLayer,
    SNNModel,
)
from .spike_encoding import SpikeEvent, RateEncoder, PoissonEncoder, LatencyEncoder
from .learning import STDPLearning, RSTDPLearning, LearningConfig, synapse_map_from_network
from .utils import load_weights, save_weights, visualize_spikes
from .xrt_backend import XRTBackend, RegisterMap
from .accelerator import SNNAccelerator


# ============================================================================
# Optional torch-backed APIs
# ============================================================================
if _TORCH_AVAILABLE:
    from .neuron import (
        LIF,
        IF,
        ALIF,
        PLIF,
        Izhikevich,
        FastSigmoid,
        ATan,
        SuperSpike,
        SigmoidGrad,
        PiecewiseLinear,
        get_surrogate,
        reset_neurons,
        detach_states,
        set_hw_mode,
        SpikingNeuron,
    )
    from .layer import (
        Linear,
        SLinear,
        Conv2d,
        SConv2d,
        AvgPool2d,
        MaxPool2d,
        BatchNorm,
        LayerNorm,
        SRNN,
        SLSTM,
        Sequential,
        SNN,
        Dropout,
    )
    from .encoder import (
        Rate,
        Poisson,
        Latency,
        Temporal,
        Delta,
        Phase,
        RateDecoder,
        LatencyDecoder,
        MaxDecoder,
    )
    from .training import (
        CrossEntropy,
        MSE,
        SpikeCount,
        SpikeRate,
        MemPotential,
        STDP,
        RSTDP,
        STDPConfig,
        Trainer,
        accuracy,
    )
    from . import deploy
    from .deploy import (
        quantize,
        dequantize,
        calibrate,
        export,
        export_onnx,
        PYNQ,
        AXIInterface,
        gen_config,
        NetworkConfig,
        LayerConfig,
    )
    from .spyketorch_compat import (
        DoGKernel,
        GaborKernel,
        Filter,
        Intensity2Latency,
        LateralIntensityInhibition,
        local_normalization,
        pointwise_inhibition,
        fire,
        get_k_winners,
        pooling,
        pad,
        STDPConvolution,
        S1C1Transform,
        CacheDataset,
    )
    from . import spyketorch_compat as sf

    class loss:
        CrossEntropy = CrossEntropy
        MSE = MSE
        SpikeCount = SpikeCount
        SpikeRate = SpikeRate
        MemPotential = MemPotential

    class surrogate:
        fast_sigmoid = FastSigmoid
        atan = ATan
        super_spike = SuperSpike
        sigmoid = SigmoidGrad
        pwl = PiecewiseLinear
        get = get_surrogate

    class functional:
        @staticmethod
        def spike(mem, thresh: float = 1.0, surrogate: str = "fast_sigmoid"):
            spike_fn = get_surrogate(surrogate)
            return spike_fn(mem, thresh)

        @staticmethod
        def rate_encode(x, T: int = 100):
            return Rate(T)(x)

        @staticmethod
        def rate_decode(spikes, dim: int = 1):
            return spikes.sum(dim=dim)

    F = functional
else:
    warnings.warn(
        "PyTorch not found. Importing `snn_fpga_accelerator` in minimal mode; "
        "torch-backed APIs are unavailable.",
        RuntimeWarning,
        stacklevel=1,
    )

    LIF = IF = ALIF = PLIF = Izhikevich = _TorchUnavailable
    FastSigmoid = ATan = SuperSpike = SigmoidGrad = PiecewiseLinear = _TorchUnavailable
    SpikingNeuron = _TorchUnavailable
    reset_neurons = detach_states = set_hw_mode = _raise_torch_missing
    get_surrogate = _raise_torch_missing

    Linear = SLinear = Conv2d = SConv2d = AvgPool2d = MaxPool2d = _TorchUnavailable
    BatchNorm = LayerNorm = SRNN = SLSTM = Sequential = SNN = Dropout = _TorchUnavailable

    Rate = Poisson = Latency = Temporal = Delta = Phase = _TorchUnavailable
    RateDecoder = LatencyDecoder = MaxDecoder = _TorchUnavailable

    CrossEntropy = MSE = SpikeCount = SpikeRate = MemPotential = _TorchUnavailable
    STDP = RSTDP = STDPConfig = Trainer = _TorchUnavailable

    deploy = None
    quantize = dequantize = calibrate = export = export_onnx = _raise_torch_missing
    PYNQ = AXIInterface = gen_config = NetworkConfig = LayerConfig = _TorchUnavailable

    DoGKernel = GaborKernel = Filter = Intensity2Latency = LateralIntensityInhibition = _TorchUnavailable
    local_normalization = pointwise_inhibition = fire = get_k_winners = _raise_torch_missing
    pooling = pad = _raise_torch_missing
    STDPConvolution = S1C1Transform = CacheDataset = _TorchUnavailable
    sf = None

    def accuracy(*_args, **_kwargs):
        _raise_torch_missing()

    class loss:
        CrossEntropy = _TorchUnavailable
        MSE = _TorchUnavailable
        SpikeCount = _TorchUnavailable
        SpikeRate = _TorchUnavailable
        MemPotential = _TorchUnavailable

    class surrogate:
        fast_sigmoid = staticmethod(_raise_torch_missing)
        atan = staticmethod(_raise_torch_missing)
        super_spike = staticmethod(_raise_torch_missing)
        sigmoid = staticmethod(_raise_torch_missing)
        pwl = staticmethod(_raise_torch_missing)
        get = staticmethod(_raise_torch_missing)

    class functional:
        @staticmethod
        def spike(*_args, **_kwargs):
            _raise_torch_missing()

        @staticmethod
        def rate_encode(*_args, **_kwargs):
            _raise_torch_missing()

        @staticmethod
        def rate_decode(*_args, **_kwargs):
            _raise_torch_missing()

    F = functional


__all__ = [
    "__version__",
    "__author__",
    # Always available
    "NeuronGroup",
    "Synapses",
    "SNNNetwork",
    "CompiledNetwork",
    "ConnectionInfo",
    "create_mnist_network",
    "create_mnist_block_sparse_network",
    "hw_sim",
    "HWAccurateLIFNeuron",
    "HWAccurateSTDPEngine",
    "HWAccurateSNNSimulator",
    "LIFNeuronParams",
    "LIFNeuronState",
    "verify_lif_neuron",
    "verify_stdp_engine",
    "FixedPoint",
    "tau_to_leak_rate",
    "leak_rate_to_tau",
    "get_available_tau_values",
    "weight_index_flat",
    "SpikeEvent",
    "RateEncoder",
    "PoissonEncoder",
    "LatencyEncoder",
    "STDPLearning",
    "RSTDPLearning",
    "LearningConfig",
    "synapse_map_from_network",
    "SNNAccelerator",
    "XRTBackend",
    "RegisterMap",
    "pytorch_to_snn",
    "SNNLayer",
    "SNNModel",
    "load_weights",
    "save_weights",
    "visualize_spikes",
    # Torch-backed names (exposed as real APIs or placeholders)
    "LIF",
    "IF",
    "ALIF",
    "PLIF",
    "Izhikevich",
    "SpikingNeuron",
    "FastSigmoid",
    "ATan",
    "SuperSpike",
    "SigmoidGrad",
    "PiecewiseLinear",
    "get_surrogate",
    "reset_neurons",
    "detach_states",
    "set_hw_mode",
    "Linear",
    "SLinear",
    "Conv2d",
    "SConv2d",
    "AvgPool2d",
    "MaxPool2d",
    "BatchNorm",
    "LayerNorm",
    "SRNN",
    "SLSTM",
    "Sequential",
    "SNN",
    "Dropout",
    "Rate",
    "Poisson",
    "Latency",
    "Temporal",
    "Delta",
    "Phase",
    "RateDecoder",
    "LatencyDecoder",
    "MaxDecoder",
    "CrossEntropy",
    "MSE",
    "SpikeCount",
    "SpikeRate",
    "MemPotential",
    "STDP",
    "RSTDP",
    "STDPConfig",
    "Trainer",
    "accuracy",
    "loss",
    "surrogate",
    "functional",
    "F",
    "deploy",
    "quantize",
    "dequantize",
    "calibrate",
    "export",
    "export_onnx",
    "PYNQ",
    "AXIInterface",
    "gen_config",
    "NetworkConfig",
    "LayerConfig",
    "DoGKernel",
    "GaborKernel",
    "Filter",
    "Intensity2Latency",
    "LateralIntensityInhibition",
    "local_normalization",
    "pointwise_inhibition",
    "fire",
    "get_k_winners",
    "pooling",
    "pad",
    "STDPConvolution",
    "S1C1Transform",
    "CacheDataset",
    "sf",
]
