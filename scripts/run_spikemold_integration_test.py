#!/usr/bin/env python3
"""Integration test for SpikePress + SpikeMold full workflow.

This script tests the complete workflow:
1. SpikePress model creation and training simulation
2. Artifact generation with quantized weights
3. Golden trace generation for verification
4. Equivalence check between PC and hardware expectations

Usage:
    python run_spikemold_integration_test.py

Output:
    - Test results summary
    - Artifact for board deployment
    - Golden traces for equivalence verification
"""

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run SpikePress + SpikeMold integration test"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/integration_test",
        help="Output directory for test artifacts",
    )
    parser.add_argument(
        "--tiny",
        action="store_true",
        help="Use tiny model for quick testing",
    )
    return parser.parse_args()


def test_model_creation():
    """Test SpikePress model creation."""
    print("\n[TEST] Model Creation")

    from spikepress.api import fc_lif_model

    # Create tiny FC-LIF model
    weights = [
        [1, 2, 3],
        [4, 5, 6],
    ]
    thresholds = [100, 200, 300]

    model = fc_lif_model(
        name="test_fc_lif",
        weights=weights,
        thresholds=thresholds,
    )

    assert model.name == "test_fc_lif"
    assert len(model.layers) == 1

    layer = model.layers[0]
    assert layer.input_size == 2
    assert layer.output_size == 3

    print("  PASS: Model created successfully")
    return model


def test_golden_trace_generation():
    """Test golden trace generation."""
    print("\n[TEST] Golden Trace Generation")

    from spikepress.api import fc_lif_model
    from spikepress.transport import pack_input_spikes
    from spikepress.architecture_trace_generator import InputSpike

    weights = [[1, 2], [3, 4]]
    model = fc_lif_model("trace_test", weights)

    # Create input spikes (using InputSpike dataclass)
    input_spikes = [
        InputSpike(src_id=0, tick=0, payload=1),
        InputSpike(src_id=1, tick=1, payload=1),
    ]

    trace = model.golden_trace(input_spikes)
    assert trace.trace_id == "trace_test_output_golden"

    trace_dict = trace.to_dict()
    assert "inputs" in trace_dict
    assert "commits" in trace_dict
    assert "final_state" in trace_dict
    assert "counters" in trace_dict

    # Verify counters
    counters = trace_dict["counters"]
    assert counters["input_event_count"] == 2
    assert counters["generated_update_count"] == 4  # 2 inputs * 2 outputs

    print("  PASS: Golden trace generated successfully")
    return trace


def test_artifact_generation():
    """Test SpikeMold artifact generation."""
    print("\n[TEST] Artifact Generation")

    import numpy as np

    from spikepress.api import fc_lif_model
    from spikepress.spikemold_artifact import build_spikemold_artifact

    weights = [[1, 2], [3, 4]]
    model = fc_lif_model("artifact_test", weights)

    compile_result = model.compile_spikemold(target="pynq-z2")
    artifact = compile_result.artifact

    assert artifact.manifest["schema"] == "spikemold.artifact.v1"
    assert artifact.manifest["target"] == "pynq-z2"

    # Check weights are int8
    flat_weights = artifact.flat_weights
    assert flat_weights.dtype == np.int8

    # Check weight range (quantized to [-8, 7])
    for w in flat_weights:
        assert -8 <= w <= 7

    print("  PASS: Artifact generated successfully")
    return artifact


def test_network_compilation():
    """Test network topology compilation."""
    print("\n[TEST] Network Compilation")

    from spikepress.network import (
        SpikePressNeuronPopulation,
        SpikePressProjection,
        SpikePressNetwork,
    )

    network = SpikePressNetwork()
    input_pop = network.add_population(SpikePressNeuronPopulation(10, "input"))
    hidden_pop = network.add_population(SpikePressNeuronPopulation(5, "hidden"))
    output_pop = network.add_population(SpikePressNeuronPopulation(2, "output"))

    network.add_projection(SpikePressProjection(input_pop, hidden_pop))
    network.add_projection(SpikePressProjection(hidden_pop, output_pop))

    compiled = network.compile()

    assert compiled.total_logical_neurons == 17
    assert compiled.max_weight_buffer_size == 10 * 5 + 5 * 2  # 60

    assert len(compiled.projections) == 2
    assert compiled.projections[0].name == "input_to_hidden"
    assert compiled.projections[1].name == "hidden_to_output"

    print("  PASS: Network compiled successfully")
    return compiled


def test_weight_quantization():
    """Test weight quantization for SpikeMold."""
    print("\n[TEST] Weight Quantization")

    import numpy as np
    from spikepress.network import (
        CompiledSpikePressTopology,
        SpikePressNeuronPopulation,
        SpikePressProjection,
        SpikePressNetwork,
    )

    network = SpikePressNetwork()
    input_pop = network.add_population(SpikePressNeuronPopulation(4, "input"))
    output_pop = network.add_population(SpikePressNeuronPopulation(2, "output"))
    proj = network.add_projection(SpikePressProjection(input_pop, output_pop))

    # Set weights with values outside quantization range
    proj.weights = np.array([
        [0.5, -1.5],
        [2.0, -3.5],
        [8.0, -9.0],  # Will be clipped
        [0.1, -0.1],
    ], dtype=np.float32)

    compiled = network.compile()

    # Pack weights (should quantize to int8)
    packed = compiled.pack_weights({"input_to_output": proj.weights})

    # Check quantization
    for w in packed:
        assert -8 <= w <= 7, f"Weight {w} out of quantization range"

    # Verify clipping
    assert 7 in packed  # 8.0 was clipped to 7
    assert -8 in packed  # -9.0 was clipped to -8

    print("  PASS: Weight quantization working correctly")


def test_equivalence_verification():
    """Test equivalence verification logic."""
    print("\n[TEST] Equivalence Verification")

    from spikepress.transport import pack_input_spikes
    from spikepress.full_board_run import (
        EquivalenceResult,
        SpikeMoldFullBoardResult,
        verify_equivalence,
    )
    from spikepress.architecture_trace_generator import (
        InputSpike,
        SpikeMoldContractTrace,
        SynapticUpdate,
        ActiveSetCommit,
        TraceCounters,
    )

    # Create a simple golden trace
    trace = SpikeMoldContractTrace(
        trace_id="equivalence_test",
        target="pynq-z2",
        metadata={},
        inputs=[
            InputSpike(src_id=0, tick=0, payload=1),
        ],
        updates=[
            SynapticUpdate(src_id=0, dst_id=0, weight=1, tick=0),
        ],
        commits=[
            ActiveSetCommit(
                dst_id=0,
                value=5,
                tick=1,
            ),
        ],
        final_state={0: 3},
        counters=TraceCounters(
            input_event_count=1,
            generated_update_count=1,
            active_neuron_count=1,
            commit_count=1,
            state_reads=1,
            state_writes=1,
            ddr_bytes_inner_loop=0,
            python_inner_loop_steps=0,
        ),
    )

    # Create mock board result
    board_result = SpikeMoldFullBoardResult(
        schema="spikemold.full_board_result.v1",
        evidence_level="pynq_board_full_run_artifact",
        board_executed=True,
        ok=True,
        artifact_id="equivalence_test",
        target="pynq-z2",
        network_info={},
        input_word_count=1,
        output_word_count=1,
        output_words=(2147483650,),  # Commit event for dst=0, value=5
        status=4,
        error_code=0,
        cycle_count=10,
        input_event_count=1,
        update_count=1,
        active_count=1,
        stall_count=0,
        service_cycles=0,
        load_time_ms=1.0,
        run_time_ms=5.0,
        total_time_ms=6.0,
        input_hash="test_input_hash",
        output_hash="test_output_hash",
    )

    equivalence = verify_equivalence(board_result, trace)

    assert isinstance(equivalence, EquivalenceResult)
    assert equivalence.schema == "spikemold.equivalence_result.v1"

    print("  PASS: Equivalence verification working")

    return equivalence


def test_training_api():
    """Test training API (without actual PyTorch)."""
    print("\n[TEST] Training API")

    from spikepress.training import (
        LIFNeuronConfig,
        SpikingModel,
    )

    lif_config = LIFNeuronConfig(threshold=1.0, decay=0.95)

    model = SpikingModel(
        layer_sizes=[4, 3, 2],
        lif_config=lif_config,
        weight_init_scale=0.1,
        timestep_vectorized=False,
    )

    # Test train/eval mode
    model.train()
    assert model.training is True

    model.eval()
    assert model.training is False

    # Test get/set weights
    weights = model.get_weights()
    assert len(weights) == 2
    assert weights[0].shape == (4, 3)
    assert weights[1].shape == (3, 2)

    print("  PASS: Training API working")


def write_test_results(results: dict, output_dir: Path) -> None:
    """Write test results to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Calculate summary
    passed = sum(1 for r in results.values() if r.get("passed", False))
    total = len(results)

    summary = {
        "schema": "spikemold.integration_test_result.v1",
        "timestamp": str(output_dir),
        "passed": passed,
        "total": total,
        "results": results,
    }

    output_path = output_dir / "integration_test_results.json"
    output_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8"
    )

    print(f"\n{'='*60}")
    print(f"Integration Test Summary: {passed}/{total} passed")
    print(f"Results written to: {output_path}")


def main() -> int:
    """Main entry point."""
    args = parse_args()
    output_dir = Path(args.output_dir)

    results = {}

    # Run tests
    try:
        test_model_creation()
        results["model_creation"] = {"passed": True}

        test_golden_trace_generation()
        results["golden_trace_generation"] = {"passed": True}

        test_artifact_generation()
        results["artifact_generation"] = {"passed": True}

        test_network_compilation()
        results["network_compilation"] = {"passed": True}

        test_weight_quantization()
        results["weight_quantization"] = {"passed": True}

        test_equivalence_verification()
        results["equivalence_verification"] = {"passed": True}

        test_training_api()
        results["training_api"] = {"passed": True}

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Write results
    write_test_results(results, output_dir)

    passed = sum(1 for r in results.values() if r.get("passed", False))
    total = len(results)

    if passed == total:
        print(f"\n{'='*60}")
        print("All integration tests passed!")
        return 0
    else:
        print(f"\n{'='*60}")
        print(f"Some tests failed: {passed}/{total} passed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
