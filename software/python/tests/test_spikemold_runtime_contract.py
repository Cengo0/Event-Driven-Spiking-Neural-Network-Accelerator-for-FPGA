from spikepress.spikemold_runtime_contract import (
    SPIKEMOLD_RUNTIME_BACKEND_ID,
    SPIKEMOLD_RUNTIME_CONTRACT_SCHEMA,
    SPIKEMOLD_RUNTIME_RESOURCE_REPORT_SCHEMA,
    build_spikemold_runtime_contract,
    build_spikemold_runtime_resource_report,
)


def test_spikemold_runtime_contract_and_resource_report():
    event_budget = {
        "recommended_spikemold_mini_config": {
            "state_width_bits": 32,
            "weight_width_bits": 16,
            "max_input_events": 1024,
            "max_generated_updates": 8192,
        },
        "trace_results": {
            "fc_lif_tiny_v1": {
                "counters": {
                    "input_event_count": 3,
                    "generated_update_count": 5,
                    "active_neuron_count": 2,
                    "commit_count": 1,
                    "state_reads": 5,
                    "state_writes": 6,
                    "ddr_bytes_inner_loop": 0,
                    "python_inner_loop_steps": 0,
                }
            }
        },
    }
    transport_smoke = {
        "spikemold_mini_fc_lif": {
            "trace_id": "batch_1b_tiny_fc_lif_output_golden",
            "counters": {
                "input_event_count": 3,
                "update_count": 5,
                "active_count": 2,
                "output_words": 1,
                "dma_calls": 2,
                "axi_lite_commands": 8,
                "python_inner_loop_steps": 0,
            },
        }
    }
    eventconv_trace = {
        "trace_id": "eventconv_8x8_tiny_v1",
        "counters": {
            "input_event_count": 2,
            "generated_update_count": 12,
            "active_neuron_count": 12,
            "commit_count": 0,
            "state_reads": 12,
            "state_writes": 12,
            "ddr_bytes_inner_loop": 0,
            "python_inner_loop_steps": 0,
        },
    }

    runtime_contract = build_spikemold_runtime_contract(
        event_budget=event_budget,
        transport_smoke=transport_smoke,
        eventconv_trace=eventconv_trace,
    )
    resource = build_spikemold_runtime_resource_report(
        event_budget=event_budget,
        transport_smoke=transport_smoke,
        eventconv_trace=eventconv_trace,
        runtime_contract=runtime_contract,
    )

    assert runtime_contract["schema"] == SPIKEMOLD_RUNTIME_CONTRACT_SCHEMA
    assert runtime_contract["selected_backend"] == SPIKEMOLD_RUNTIME_BACKEND_ID
    assert runtime_contract["board_executed"] is False
    assert runtime_contract["runtime_invariants"]["python_inner_loop_required"] is False
    assert runtime_contract["primitives"]["flat_fc_lif"]["expected_dma_calls_per_inference"] == 2
    assert runtime_contract["primitives"]["eventconv_agu"]["max_state_count_current_gate"] == 64
    assert runtime_contract["primitives"]["eventconv_agu"]["expected_axi_lite_commands_per_inference"] == 8
    assert resource["schema"] == SPIKEMOLD_RUNTIME_RESOURCE_REPORT_SCHEMA
    assert resource["runtime_contract_sha256"] == runtime_contract["hashes"]["runtime_contract_sha256"]
    assert resource["resource_reports"]["eventconv_agu"]["state_memory_bytes"] == 128
    assert resource["resource_reports"]["eventconv_agu"]["dsp_estimate"] == 0
    assert resource["resource_reports"]["eventconv_agu"]["expected_dma_calls_per_inference"] == 2
