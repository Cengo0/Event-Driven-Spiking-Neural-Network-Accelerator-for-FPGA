"""SpikePress software API for SpikeMold artifacts."""

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
from .architecture_sandbox import (
    ARCHITECTURE_SANDBOX_SCHEMA,
    build_batch_1x_architecture_sandbox,
)
from .spikemold_artifact import (
    SpikeMoldArtifact,
    build_spikemold_artifact,
    read_spikemold_artifact,
    write_spikemold_artifact,
)
from .event_budget import (
    EventBudgetLimits,
    EventBudgetResult,
    DEFAULT_SPIKEMOLD_MINI_LIMITS,
    evaluate_trace_budget,
    recommended_spikemold_mini_config,
    summarize_trace_budgets,
)
from .spikemold_runtime_contract import (
    SPIKEMOLD_RUNTIME_BACKEND_ID,
    SPIKEMOLD_RUNTIME_CONTRACT_SCHEMA,
    SPIKEMOLD_RUNTIME_RESOURCE_REPORT_SCHEMA,
    build_spikemold_runtime_contract,
    build_spikemold_runtime_resource_report,
)
from .pynq_runtime import (
    PYNQ_ONESHOT_SCHEMA,
    SpikeMoldPynqRunConfig,
    SpikeMoldPynqRunResult,
    run_spikemold_pynq_one_shot,
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
    run_spikemold_mini_fc_lif_smoke,
    run_eventword64_counter_smoke,
)

__all__ = [
    "SpikeMoldContractTrace",
    "ActiveSetCommit",
    "ARCHITECTURE_SANDBOX_SCHEMA",
    "DEFAULT_SPIKEMOLD_MINI_LIMITS",
    "EventBudgetLimits",
    "EventBudgetResult",
    "InputSpike",
    "SPIKEMOLD_RUNTIME_BACKEND_ID",
    "SPIKEMOLD_RUNTIME_CONTRACT_SCHEMA",
    "SPIKEMOLD_RUNTIME_RESOURCE_REPORT_SCHEMA",
    "PYNQ_ONESHOT_SCHEMA",
    "CompiledSpikePressTopology",
    "SpikePressNetwork",
    "SpikePressNeuronPopulation",
    "SpikePressProjection",
    "SpikePressProjectionInfo",
    "REGISTER_OFFSETS",
    "SpikeMoldArtifact",
    "SpikeMoldPynqRunConfig",
    "SpikeMoldPynqRunResult",
    "SpikeMoldRuntimeCounters",
    "SpikePressCompileResult",
    "SpikePressFCLIFLayer",
    "SpikePressModel",
    "SynapticUpdate",
    "build_spikemold_artifact",
    "build_batch_1b_transport_smoke",
    "build_batch_1x_architecture_sandbox",
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
    "read_spikemold_artifact",
    "recommended_spikemold_mini_config",
    "run_axi_lite_smoke",
    "run_dma_loopback",
    "run_spikemold_mini_fc_lif_smoke",
    "run_eventword64_counter_smoke",
    "run_spikemold_pynq_one_shot",
    "summarize_trace_budgets",
    "write_spikemold_artifact",
]

__version__ = "0.1.0"
