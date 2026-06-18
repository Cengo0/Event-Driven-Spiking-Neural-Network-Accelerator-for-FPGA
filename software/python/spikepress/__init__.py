"""SpikePress software API for SpikeMold artifacts."""

from .api import (
    SpikePressFCLIFLayer,
    SpikePressModel,
    fc_lif_model,
    SpikePressCompileResult,
)
try:
    from .training import (
        LIFNeuronConfig,
        SpikingModel,
        SpikePressTrainer,
        train_ann,
        ann_to_snn,
        pytorch_to_snn,
    )
except Exception:
    # Training/ANNtoSNN require torch (not present in pure PYNQ runtime envs)
    LIFNeuronConfig = None  # type: ignore
    SpikingModel = None  # type: ignore
    SpikePressTrainer = None  # type: ignore
    train_ann = None  # type: ignore
    ann_to_snn = None  # type: ignore
    pytorch_to_snn = None  # type: ignore
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
    DEFAULT_FLAT_FC_LIF_LIMITS,
    DEFAULT_HYBRID_BLOCK_LIMITS,
    evaluate_trace_budget,
    recommended_flat_fc_lif_config,
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
    decode_eventword64_input,
    event_word_type,
    lower_eventword64_input_to_axis32,
    lower_eventword64_inputs_to_axis32,
    pack_input_spikes,
    pack_trace_output_commits,
    run_axi_lite_smoke,
    run_dma_loopback,
    run_eventword64_to_axis32_lowering_smoke,
    run_flat_fc_lif_smoke,
    run_eventword64_counter_smoke,
)
from .full_board_run import (
    EquivalenceResult,
    SpikeMoldBoardConfig,
    SpikeMoldFullBoardResult,
    load_artifact,
    run_model_on_board,
    run_full_board_verification,
    verify_equivalence,
)

__all__ = [
    "SpikeMoldContractTrace",
    "ActiveSetCommit",
    "ARCHITECTURE_SANDBOX_SCHEMA",
    "DEFAULT_FLAT_FC_LIF_LIMITS",
    "DEFAULT_HYBRID_BLOCK_LIMITS",
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
    # Training API
    "LIFNeuronConfig",
    "SpikingModel",
    "SpikePressTrainer",
    # Build functions
    "build_spikemold_artifact",
    "build_batch_1b_transport_smoke",
    "build_batch_1x_architecture_sandbox",
    "build_spikemold_runtime_contract",
    "build_spikemold_runtime_resource_report",
    # Trace functions
    "decode_eventword64_input",
    "event_word_type",
    "evaluate_trace_budget",
    "fc_lif_model",
    "generate_eventconv_trace",
    "generate_fc_lif_trace",
    "lower_eventword64_input_to_axis32",
    "lower_eventword64_inputs_to_axis32",
    "pack_spikemold_event_word64",
    "pack_input_spikes",
    "pack_trace_output_commits",
    # Artifact I/O
    "read_spikemold_artifact",
    "recommended_flat_fc_lif_config",
    "run_axi_lite_smoke",
    "run_dma_loopback",
    "run_eventword64_to_axis32_lowering_smoke",
    "run_flat_fc_lif_smoke",
    "run_eventword64_counter_smoke",
    "run_spikemold_pynq_one_shot",
    "summarize_trace_budgets",
    "write_spikemold_artifact",
    # Full board run
    "EquivalenceResult",
    "SpikeMoldBoardConfig",
    "SpikeMoldFullBoardResult",
    "load_artifact",
    "run_model_on_board",
    "run_full_board_verification",
    "verify_equivalence",
]

__version__ = "0.1.0"
