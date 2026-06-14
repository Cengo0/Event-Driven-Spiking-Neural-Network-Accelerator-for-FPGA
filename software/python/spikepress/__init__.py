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
from .spikemold_runtime_contract import (
    SPIKEMOLD_RUNTIME_BACKEND_ID,
    SPIKEMOLD_RUNTIME_CONTRACT_SCHEMA,
    SPIKEMOLD_RUNTIME_RESOURCE_REPORT_SCHEMA,
    build_spikemold_runtime_contract,
    build_spikemold_runtime_resource_report,
)
from .network import (
    CompiledSpikePressTopology,
    SpikePressNeuronPopulation,
    SpikePressProjectionInfo,
    SpikePressNetwork,
    SpikePressProjection,
)
from .transport import (
    REGISTER_OFFSETS,
    SpikeMoldRuntimeCounters,
    build_batch_1b_transport_smoke,
    event_word_type,
    pack_input_spikes,
    pack_trace_output_commits,
    run_axi_lite_smoke,
    run_dma_loopback,
    run_ednp_mini_fc_lif_smoke,
    run_eventword64_counter_smoke,
)

__all__ = [
    "SpikeMoldContractTrace",
    "ActiveSetCommit",
    "DEFAULT_EDNP_MINI_LIMITS",
    "EventBudgetLimits",
    "EventBudgetResult",
    "InputSpike",
    "SPIKEMOLD_RUNTIME_BACKEND_ID",
    "SPIKEMOLD_RUNTIME_CONTRACT_SCHEMA",
    "SPIKEMOLD_RUNTIME_RESOURCE_REPORT_SCHEMA",
    "CompiledSpikePressTopology",
    "SpikePressNetwork",
    "SpikePressNeuronPopulation",
    "SpikePressProjection",
    "SpikePressProjectionInfo",
    "REGISTER_OFFSETS",
    "SpikeMoldEDNPArtifact",
    "SpikeMoldRuntimeCounters",
    "SpikePressCompileResult",
    "SpikePressFCLIFLayer",
    "SpikePressModel",
    "SynapticUpdate",
    "build_spikemold_ednp_artifact",
    "build_batch_1b_transport_smoke",
    "build_spikemold_runtime_contract",
    "build_spikemold_runtime_resource_report",
    "event_word_type",
    "evaluate_trace_budget",
    "fc_lif_model",
    "generate_eventconv_trace",
    "generate_fc_lif_trace",
    "pack_spikemold_event_word64",
    "pack_input_spikes",
    "pack_trace_output_commits",
    "read_spikemold_ednp_artifact",
    "recommended_ednp_mini_config",
    "run_axi_lite_smoke",
    "run_dma_loopback",
    "run_ednp_mini_fc_lif_smoke",
    "run_eventword64_counter_smoke",
    "summarize_trace_budgets",
    "write_spikemold_ednp_artifact",
]

__version__ = "0.1.0"
