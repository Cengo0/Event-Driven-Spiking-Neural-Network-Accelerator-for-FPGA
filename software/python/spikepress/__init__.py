"""SpikePress software API for SpikeMold-EDNP artifacts."""

from .api import (
    SpikePressCompiledEDNP,
    SpikePressFCLIFLayer,
    SpikePressModel,
    fc_lif_model,
)
from .architecture_trace_generator import (
    ArchitectureTrace,
    CommitEvent,
    InputSpike,
    SynapticUpdate,
    generate_eventconv_trace,
    generate_fc_lif_trace,
    pack_event_word64,
)
from .ednp_artifact import (
    EDNPArtifact,
    build_ednp_artifact,
    read_ednp_artifact,
    write_ednp_artifact,
)
from .event_budget import (
    DEFAULT_M3_LIMITS,
    EventBudgetLimits,
    EventBudgetResult,
    evaluate_trace_budget,
    recommended_m3_config,
    summarize_trace_budgets,
)
from .network import (
    CompiledSpikePressNetwork,
    ConnectionInfo,
    NeuronGroup,
    SpikePressNetwork,
    Synapses,
)

__all__ = [
    "ArchitectureTrace",
    "CommitEvent",
    "CompiledSpikePressNetwork",
    "ConnectionInfo",
    "DEFAULT_M3_LIMITS",
    "EDNPArtifact",
    "EventBudgetLimits",
    "EventBudgetResult",
    "InputSpike",
    "NeuronGroup",
    "SpikePressNetwork",
    "SpikePressCompiledEDNP",
    "SpikePressFCLIFLayer",
    "SpikePressModel",
    "Synapses",
    "SynapticUpdate",
    "build_ednp_artifact",
    "evaluate_trace_budget",
    "fc_lif_model",
    "generate_eventconv_trace",
    "generate_fc_lif_trace",
    "pack_event_word64",
    "read_ednp_artifact",
    "recommended_m3_config",
    "summarize_trace_budgets",
    "write_ednp_artifact",
]

__version__ = "0.1.0"
