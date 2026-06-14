"""SpikePress software API for SpikeMold-EDNP artifacts."""

from .api import (
    SpikePressFCLIFLayer,
    SpikePressModel,
    fc_lif_model,
    SpikePressCompileResult,
)
from .architecture_trace_generator import (
    ActiveSetCommit,
    InputSpike,
    SpikeMoldContractTrace,
    SynapticUpdate,
    generate_eventconv_trace,
    generate_fc_lif_trace,
    pack_spikemold_event_word64,
)
from .spikemold_ednp_artifact import (
    SpikeMoldEDNPArtifact,
    build_spikemold_ednp_artifact,
    read_spikemold_ednp_artifact,
    write_spikemold_ednp_artifact,
)
from .event_budget import (
    EventBudgetLimits,
    EventBudgetResult,
    DEFAULT_EDNP_MINI_LIMITS,
    evaluate_trace_budget,
    recommended_ednp_mini_config,
    summarize_trace_budgets,
)
from .network import (
    CompiledSpikePressTopology,
    SpikePressNeuronPopulation,
    SpikePressProjectionInfo,
    SpikePressNetwork,
    SpikePressProjection,
)

__all__ = [
    "SpikeMoldContractTrace",
    "ActiveSetCommit",
    "DEFAULT_EDNP_MINI_LIMITS",
    "EventBudgetLimits",
    "EventBudgetResult",
    "InputSpike",
    "CompiledSpikePressTopology",
    "SpikePressNetwork",
    "SpikePressNeuronPopulation",
    "SpikePressProjection",
    "SpikePressProjectionInfo",
    "SpikeMoldEDNPArtifact",
    "SpikePressCompileResult",
    "SpikePressFCLIFLayer",
    "SpikePressModel",
    "SynapticUpdate",
    "build_spikemold_ednp_artifact",
    "evaluate_trace_budget",
    "fc_lif_model",
    "generate_eventconv_trace",
    "generate_fc_lif_trace",
    "pack_spikemold_event_word64",
    "read_spikemold_ednp_artifact",
    "recommended_ednp_mini_config",
    "summarize_trace_budgets",
    "write_spikemold_ednp_artifact",
]

__version__ = "0.1.0"
