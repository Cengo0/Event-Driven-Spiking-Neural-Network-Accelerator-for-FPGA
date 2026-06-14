from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "contracts"


def test_batch0_contract_files_exist():
    required = [
        "ARCHITECTURE_CONTRACT_V1.md",
        "INTEGER_SEMANTICS_V1.md",
        "EVENT_FORMAT_V1.md",
        "TRACE_SCHEMA_V1.md",
        "REGISTER_MAP_MINIMAL_V1.md",
        "RESOURCE_BUDGET_V1.md",
        "ARCHITECTURE_PATTERN_POLICY_V1.md",
    ]

    missing = [name for name in required if not (CONTRACTS / name).exists()]
    assert missing == []


def test_architecture_policy_bans_failure_modes_not_pattern_names():
    text = (CONTRACTS / "ARCHITECTURE_PATTERN_POLICY_V1.md").read_text(encoding="utf-8").lower()

    for pattern in ["page", "tile", "coregroup"]:
        assert f"- {pattern}" in text

    for failure_mode in [
        "python-controlled event loop",
        "random ddr synapse fetch per event",
        "unbounded fanout",
        "full-neuron scan every timestep",
        "silent semantic changes",
    ]:
        assert failure_mode in text
