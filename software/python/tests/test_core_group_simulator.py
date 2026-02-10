"""
Tests for Core Group bit-accurate simulator.

Verifies HWCoreGroup, HWConnectivityTable, HWEventRouter and
HWAccurateSNNSimulator match the core_group.v / event_router_ng.v /
synaptic_connectivity_table.v RTL architecture.

Author: Jiwoon Lee (@metr0jw)
"""

import sys
import os
import numpy as np

# Allow running without package install
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from snn_fpga_accelerator.hw_accurate_simulator import (
    HWAccurateLIFNeuron, LIFNeuronParams, HWCoreGroup, HWConnectivityTable,
    HWEventRouter, HWAccurateSNNSimulator, HWAccurateSTDPEngine, STDPConfig,
    MAX_NEURONS, MAX_WEIGHT, MIN_WEIGHT, WEIGHT_WIDTH, NEURONS_PER_GROUP,
    NUM_GROUPS, HLS_NEURON_ID_WIDTH, GLOBAL_ID_WIDTH, GROUP_ID_WIDTH,
    LOCAL_ID_WIDTH, SPIKE_BUFFER_DEPTH, MAX_FANOUT_INTER,
)
from snn_fpga_accelerator.neuron import LIF


# ============================================================================
# Test Constants
# ============================================================================

def test_constants():
    """Hardware constants match core_group.v RTL parameters."""
    assert MAX_NEURONS == 2048, f"MAX_NEURONS={MAX_NEURONS}"
    assert NUM_GROUPS == 16
    assert NEURONS_PER_GROUP == 128
    assert WEIGHT_WIDTH == 4
    assert MAX_WEIGHT == 15
    assert MIN_WEIGHT == 0
    assert HLS_NEURON_ID_WIDTH == 11
    assert GLOBAL_ID_WIDTH == 11
    assert GROUP_ID_WIDTH == 4
    assert LOCAL_ID_WIDTH == 7
    assert SPIKE_BUFFER_DEPTH == 64
    assert MAX_FANOUT_INTER == 16
    print("PASS: test_constants")


# ============================================================================
# Test LIF Neuron (matches core_group.v FSM)
# ============================================================================

def test_lif_spike_threshold():
    """4-bit weight accumulation triggers spike at threshold."""
    params = LIFNeuronParams(threshold=100, leak_rate=3, refractory_period=5)
    n = HWAccurateLIFNeuron(0, params)

    # 10 * 10 = 100 >= threshold → spike on input 9 (0-indexed)
    for i in range(10):
        fired = n.tick(syn_valid=True, syn_weight=10, syn_excitatory=True)
        if i < 9:
            assert not fired, f"Spurious spike at step {i}"
        else:
            assert fired, f"Expected spike at step {i}"
    assert n.get_membrane_potential() == 0  # Reset
    print("PASS: test_lif_spike_threshold")


def test_lif_leak():
    """Shift-based leak matches core_group.v ST_LEAK_WR."""
    params = LIFNeuronParams(threshold=1000, leak_rate=3)  # shift1=3 → tau=0.875
    n = HWAccurateLIFNeuron(0, params)

    # Set membrane to 80 via 5 spikes × 16
    for _ in range(5):
        n.tick(syn_valid=True, syn_weight=16, syn_excitatory=True)
    assert n.get_membrane_potential() == 80

    # Apply leak: 80 - (80 >> 3) = 80 - 10 = 70
    n.tick(syn_valid=False)
    assert n.get_membrane_potential() == 70
    print("PASS: test_lif_leak")


def test_lif_inhibitory():
    """Inhibitory spike subtracts, floors at 0 (core_group.v sp_exc=0)."""
    params = LIFNeuronParams(threshold=1000, leak_rate=7)
    n = HWAccurateLIFNeuron(0, params)

    n.tick(syn_valid=True, syn_weight=10, syn_excitatory=True)
    assert n.get_membrane_potential() == 10
    n.tick(syn_valid=True, syn_weight=5, syn_excitatory=False)
    assert n.get_membrane_potential() == 5
    n.tick(syn_valid=True, syn_weight=10, syn_excitatory=False)
    assert n.get_membrane_potential() == 0  # Floor at 0
    print("PASS: test_lif_inhibitory")


def test_lif_refractory():
    """Refractory counter blocks accumulation."""
    params = LIFNeuronParams(threshold=20, leak_rate=7, refractory_period=3)
    n = HWAccurateLIFNeuron(0, params)

    # Fire
    n.tick(syn_valid=True, syn_weight=15, syn_excitatory=True)
    fired = n.tick(syn_valid=True, syn_weight=15, syn_excitatory=True)
    assert fired
    assert n.is_refractory()

    # Should be refractory for 3 leak cycles
    for _ in range(3):
        result = n.tick(syn_valid=True, syn_weight=15, syn_excitatory=True)
        assert not result  # No spike during refractory
    print("PASS: test_lif_refractory")


def test_lif_no_spike_on_inhibitory():
    """Core_group.v: sp_fired only when sp_exc=1, even if v_mem >= threshold."""
    params = LIFNeuronParams(threshold=10, leak_rate=7)
    n = HWAccurateLIFNeuron(0, params)

    # Set membrane high
    n.tick(syn_valid=True, syn_weight=9, syn_excitatory=True)
    # Inhibitory spike should NOT fire even if v_mem was near threshold
    fired = n.tick(syn_valid=True, syn_weight=5, syn_excitatory=False)
    assert not fired
    print("PASS: test_lif_no_spike_on_inhibitory")


# ============================================================================
# Test Core Group (matches core_group.v FSM)
# ============================================================================

def test_core_group_basic():
    """Basic spike processing in CoreGroup."""
    params = LIFNeuronParams(threshold=50, leak_rate=3, refractory_period=2)
    group = HWCoreGroup(group_id=0, params=params)

    # Inject spikes to neuron 0 until it fires
    for _ in range(4):
        group.push_spike(0, 15, True)  # 4 × 15 = 60 > 50
    fired = group.process_step()
    assert 0 in fired
    assert group.total_spikes == 1
    print("PASS: test_core_group_basic")


def test_core_group_intra_recurrence():
    """Intra-group recurrence: fired neuron scans weight row."""
    params = LIFNeuronParams(threshold=50, leak_rate=7, refractory_period=2)
    group = HWCoreGroup(group_id=0, params=params)

    # Set weight: neuron 0 → neuron 5 (weight=12, excitatory)
    group.set_weight(0, 5, 12, True)

    # Fire neuron 0
    for _ in range(4):
        group.push_spike(0, 15, True)
    fired = group.process_step()

    assert 0 in fired
    assert group.get_membrane(5) > 0, "Neuron 5 should receive intra-group spike"
    print(f"PASS: test_core_group_intra_recurrence (N5 membrane={group.get_membrane(5)})")


def test_core_group_chain_fire():
    """Chain firing: N0 → N1 → N2 via intra-group recurrence."""
    params = LIFNeuronParams(threshold=10, leak_rate=7, refractory_period=2)
    group = HWCoreGroup(group_id=0, params=params)

    group.set_weight(0, 1, 15, True)  # N0 → N1 (weight 15 > threshold 10)
    group.set_weight(1, 2, 15, True)  # N1 → N2 (weight 15 > threshold 10)

    # Fire N0
    group.push_spike(0, 15, True)
    fired = group.process_step()

    # All three should fire in the same step (FIFO-based recurrence)
    assert 0 in fired, f"N0 should fire, got {fired}"
    assert 1 in fired, f"N1 should fire (chain), got {fired}"
    assert 2 in fired, f"N2 should fire (chain), got {fired}"
    print("PASS: test_core_group_chain_fire")


def test_core_group_fifo_full():
    """FIFO full rejection when capacity exceeded."""
    params = LIFNeuronParams(threshold=10000, leak_rate=7)
    group = HWCoreGroup(group_id=0, params=params)

    # Fill FIFO past capacity
    accepted = 0
    for _ in range(100):
        if group.push_spike(0, 5, True):
            accepted += 1
    assert accepted == SPIKE_BUFFER_DEPTH - 2  # fifo_full threshold
    print(f"PASS: test_core_group_fifo_full (accepted={accepted})")


def test_core_group_weight_clipping():
    """Weights clip to MAX_WEIGHT (15)."""
    group = HWCoreGroup(group_id=0)
    group.set_weight(0, 1, 20, True)  # Exceeds 15
    assert group.weights[0, 1] == 15
    print("PASS: test_core_group_weight_clipping")


# ============================================================================
# Test Connectivity Table (matches synaptic_connectivity_table.v)
# ============================================================================

def test_ct_write_read():
    """Write and read CT entries."""
    ct = HWConnectivityTable(num_groups=16, neurons_per_group=128)
    ct.write(0, 5, 0, valid=True, dst_group=3, dst_neuron=10, weight=12, exc_inh=True)
    ct.write(0, 5, 1, valid=True, dst_group=7, dst_neuron=20, weight=8, exc_inh=False)
    ct.write(0, 5, 2, valid=False, dst_group=0, dst_neuron=0, weight=0, exc_inh=True)

    entry0 = ct.lookup(0, 5, 0)
    assert entry0.valid and entry0.dst_group == 3 and entry0.dst_neuron == 10
    assert entry0.weight == 12 and entry0.exc_inh is True

    entry1 = ct.lookup(0, 5, 1)
    assert entry1.valid and entry1.dst_group == 7 and entry1.dst_neuron == 20
    assert entry1.weight == 8 and entry1.exc_inh is False

    entry2 = ct.lookup(0, 5, 2)
    assert not entry2.valid  # Marks end of fanout list
    print("PASS: test_ct_write_read")


def test_ct_get_all_connections():
    """Get all valid connections, stop at first invalid."""
    ct = HWConnectivityTable()
    ct.write(0, 0, 0, True, 1, 0, 10, True)
    ct.write(0, 0, 1, True, 2, 5, 8, True)
    ct.write(0, 0, 2, True, 3, 10, 6, False)
    # fanout_idx=3 not written → default invalid → stops

    conns = ct.get_all_connections(0, 0)
    assert len(conns) == 3
    print("PASS: test_ct_get_all_connections")


def test_ct_empty_lookup():
    """Empty table returns invalid entries."""
    ct = HWConnectivityTable()
    entry = ct.lookup(0, 0, 0)
    assert not entry.valid
    conns = ct.get_all_connections(5, 50)
    assert len(conns) == 0
    print("PASS: test_ct_empty_lookup")


# ============================================================================
# Test Event Router (matches event_router_ng.v)
# ============================================================================

def test_router_delivery():
    """Router delivers spikes via CT to destination groups."""
    params = LIFNeuronParams(threshold=50, leak_rate=7, refractory_period=2)
    groups = [HWCoreGroup(g, params=params) for g in range(4)]
    ct = HWConnectivityTable(num_groups=4)
    ct.write(0, 5, 0, True, 2, 10, 12, True)   # G0:N5 → G2:N10

    router = HWEventRouter(num_groups=4, ct=ct)

    # Make G0:N5 fire
    for _ in range(4):
        groups[0].push_spike(5, 15, True)
    groups[0].process_step()

    # Route
    learn_events = router.route_spikes(groups)
    assert len(learn_events) > 0
    assert router.routed_spike_count > 0

    # G2:N10 should have received spike in its FIFO
    assert len(groups[2].fifo) > 0
    print("PASS: test_router_delivery")


def test_router_learn_observation():
    """Router forwards all spikes to learn observation port."""
    params = LIFNeuronParams(threshold=10, leak_rate=7)
    groups = [HWCoreGroup(g, params=params) for g in range(4)]
    ct = HWConnectivityTable(num_groups=4)
    router = HWEventRouter(num_groups=4, ct=ct)

    # Fire neurons in multiple groups
    groups[0].push_spike(0, 15, True)
    groups[0].process_step()
    groups[1].push_spike(3, 15, True)
    groups[1].process_step()

    learn_events = router.route_spikes(groups)
    assert len(learn_events) == 2  # Both spikes observed
    print("PASS: test_router_learn_observation")


# ============================================================================
# Test Full System Simulator
# ============================================================================

def test_system_global_id():
    """Global ↔ Local ID conversion is correct."""
    assert HWAccurateSNNSimulator.local_to_global(0, 0) == 0
    assert HWAccurateSNNSimulator.local_to_global(0, 127) == 127
    assert HWAccurateSNNSimulator.local_to_global(1, 0) == 128
    assert HWAccurateSNNSimulator.local_to_global(15, 127) == 2047
    assert HWAccurateSNNSimulator.global_to_local(0) == (0, 0)
    assert HWAccurateSNNSimulator.global_to_local(128) == (1, 0)
    assert HWAccurateSNNSimulator.global_to_local(2047) == (15, 127)
    print("PASS: test_system_global_id")


def test_system_intra_group():
    """System-level intra-group spike propagation."""
    sim = HWAccurateSNNSimulator(
        num_groups=2, neurons_per_group=128,
        neuron_params=LIFNeuronParams(threshold=50, leak_rate=7, refractory_period=2)
    )
    sim.set_intra_weight(0, 0, 5, weight=12, exc=True)
    ext = [(0, 15, True)] * 4  # G0:N0 = global 0
    fired = sim.tick(ext)
    g0_n0 = sim.local_to_global(0, 0)
    assert g0_n0 in fired
    assert sim.groups[0].get_membrane(5) > 0
    print("PASS: test_system_intra_group")


def test_system_inter_group():
    """System-level inter-group routing via CT."""
    sim = HWAccurateSNNSimulator(
        num_groups=4, neurons_per_group=128,
        neuron_params=LIFNeuronParams(threshold=50, leak_rate=7, refractory_period=2)
    )
    sim.set_inter_connection(0, 0, 0, dst_group=3, dst_neuron=10, weight=12, exc=True)
    ext = [(0, 15, True)] * 4
    sim.tick(ext)
    g3_n10_mem = sim.groups[3].get_membrane(10)
    assert g3_n10_mem > 0, f"G3:N10 should receive inter-group spike, got {g3_n10_mem}"
    print(f"PASS: test_system_inter_group (G3:N10={g3_n10_mem})")


def test_system_run():
    """Multi-cycle run with spike train."""
    sim = HWAccurateSNNSimulator(
        num_groups=2, neurons_per_group=128,
        neuron_params=LIFNeuronParams(threshold=30, leak_rate=7, refractory_period=2)
    )
    spike_train = {
        0: [(0, 15, True), (0, 15, True)],  # 30 → fires at threshold=30
        2: [(128, 15, True), (128, 15, True)],
    }
    result = sim.run(5, spike_train)
    assert result['total_spikes'] > 0
    assert result['total_cycles'] == 5
    print(f"PASS: test_system_run (spikes={result['total_spikes']})")


def test_system_neuron_state():
    """get_neuron_state returns correct info."""
    sim = HWAccurateSNNSimulator(num_groups=2, neurons_per_group=128)
    state = sim.get_neuron_state(128)  # G1:N0
    assert state['group_id'] == 1
    assert state['local_id'] == 0
    assert state['membrane_potential'] == 0
    print("PASS: test_system_neuron_state")


# ============================================================================
# Test STDP with 4-bit weights
# ============================================================================

def test_stdp_4bit_ltp():
    """STDP LTP with 4-bit weight range."""
    config = STDPConfig(a_plus=0.5, a_minus=0.5, stdp_window=100)
    stdp = HWAccurateSTDPEngine(config, max_neurons=256)
    weights = np.zeros((256, 256), dtype=np.int16)
    weights[0, 1] = 5
    stdp.set_weights(weights)
    stdp.add_synapse(0, 1)

    stdp.process_pre_spike(0, 100, [1])
    updates = stdp.process_post_spike(1, 105, [0])
    assert len(updates) > 0
    assert updates[0].delta > 0  # LTP = positive delta
    print(f"PASS: test_stdp_4bit_ltp (delta={updates[0].delta})")


def test_stdp_4bit_ltd():
    """STDP LTD with 4-bit weight range."""
    config = STDPConfig(a_plus=0.5, a_minus=0.5, stdp_window=100)
    stdp = HWAccurateSTDPEngine(config, max_neurons=256)
    weights = np.zeros((256, 256), dtype=np.int16)
    weights[0, 1] = 10
    stdp.set_weights(weights)
    stdp.add_synapse(0, 1)

    stdp.process_post_spike(1, 100, [0])
    updates = stdp.process_pre_spike(0, 105, [1])
    assert len(updates) > 0
    assert updates[0].delta < 0  # LTD = negative delta
    print(f"PASS: test_stdp_4bit_ltd (delta={updates[0].delta})")


def test_stdp_4bit_saturation():
    """Weight at max → no LTP update."""
    config = STDPConfig(a_plus=0.5, a_minus=0.5, stdp_window=100)
    stdp = HWAccurateSTDPEngine(config, max_neurons=256)
    weights = np.zeros((256, 256), dtype=np.int16)
    weights[0, 1] = MAX_WEIGHT  # Already at 15
    stdp.set_weights(weights)
    stdp.add_synapse(0, 1)

    stdp.process_pre_spike(0, 100, [1])
    updates = stdp.process_post_spike(1, 105, [0])
    # distance = w_max - w = 0 → no update
    assert len(updates) == 0 or updates[0].delta == 0
    print("PASS: test_stdp_4bit_saturation")


# ============================================================================
# Test neuron.py hw_mode
# ============================================================================

def test_neuron_hw_mode():
    """LIF neuron hw_mode uses 4-bit weights."""
    lif = LIF(hw_mode=True)
    assert lif.weight_bits == 4
    print("PASS: test_neuron_hw_mode")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    tests = [
        test_constants,
        test_lif_spike_threshold,
        test_lif_leak,
        test_lif_inhibitory,
        test_lif_refractory,
        test_lif_no_spike_on_inhibitory,
        test_core_group_basic,
        test_core_group_intra_recurrence,
        test_core_group_chain_fire,
        test_core_group_fifo_full,
        test_core_group_weight_clipping,
        test_ct_write_read,
        test_ct_get_all_connections,
        test_ct_empty_lookup,
        test_router_delivery,
        test_router_learn_observation,
        test_system_global_id,
        test_system_intra_group,
        test_system_inter_group,
        test_system_run,
        test_system_neuron_state,
        test_stdp_4bit_ltp,
        test_stdp_4bit_ltd,
        test_stdp_4bit_saturation,
        test_neuron_hw_mode,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{passed + failed} PASS, {failed} FAIL")
    print(f"{'=' * 60}")
    sys.exit(1 if failed > 0 else 0)
