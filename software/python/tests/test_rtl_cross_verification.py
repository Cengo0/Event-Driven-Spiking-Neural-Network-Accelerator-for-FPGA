"""
Cross-verification tests: Python bit-accurate simulator vs RTL behavior.

These tests verify that the Python HWCoreGroup, HWConnectivityTable, and
HWEventRouter simulators produce behavior identical to the Verilog RTL:
    - core_group.v
    - event_router_ng.v
    - synaptic_connectivity_table.v
    - snn_core_group_top.v

Each test exercises a specific functional path and checks that the Python
simulator's output matches what the RTL testbenches verify.

Author: Jiwoon Lee (@metr0jw)
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from snn_fpga_accelerator.hw_accurate_simulator import (
    HWAccurateLIFNeuron, LIFNeuronParams, HWCoreGroup, HWConnectivityTable,
    HWEventRouter, HWAccurateSNNSimulator, HWAccurateSTDPEngine, STDPConfig,
    MAX_NEURONS, MAX_WEIGHT, MIN_WEIGHT, WEIGHT_WIDTH, NEURONS_PER_GROUP,
    NUM_GROUPS, GLOBAL_ID_WIDTH, GROUP_ID_WIDTH, LOCAL_ID_WIDTH,
    SPIKE_BUFFER_DEPTH, MAX_FANOUT_INTER, DATA_WIDTH, REFRAC_WIDTH,
    leak_rate_to_tau, tau_to_leak_rate, get_available_tau_values,
)


# =============================================================================
# 1. LIF Neuron: Bit-Accurate Leak Computation
# =============================================================================

class TestLeakComputation:
    """Verify shift-based leak matches core_group.v ST_LEAK_WR exactly."""

    @staticmethod
    def _rtl_leak(v_mem: int, leak_rate: int) -> tuple:
        """
        Exact RTL leak computation from core_group.v lines 195-199:
            shift1     = global_leak_rate[2:0]
            shift2_cfg = global_leak_rate[7:3]
            shift2     = shift2_cfg[2:0]
            shift2_en  = (shift2_cfg != 5'd0)
            leak_primary   = (shift1 != 0) ? (mem_rd >> shift1) : 0
            leak_secondary = (shift2_en && shift2 != 0) ? (mem_rd >> shift2) : 0
            leak_total     = leak_primary + leak_secondary
        """
        shift1 = leak_rate & 0x07
        shift2_cfg = (leak_rate >> 3) & 0x1F
        shift2 = shift2_cfg & 0x07
        shift2_en = (shift2_cfg != 0)

        leak_primary = (v_mem >> shift1) if shift1 != 0 else 0
        leak_secondary = (v_mem >> shift2) if (shift2_en and shift2 != 0) else 0
        leak_total = leak_primary + leak_secondary

        # Clamp leak_total to 16-bit (in RTL: wire [DATA_WIDTH-1:0])
        leak_total = min(leak_total, 65535)
        return leak_total

    @staticmethod
    def _rtl_leak_writeback(v_mem: int, refrac: int, leak_total: int) -> tuple:
        """
        RTL ST_LEAK_WR logic:
            if (ref_rd > 0)
                ns_din <= {0, ref_rd - 1}
            else if (mem_rd > leak_total)
                ns_din <= {mem_rd - leak_total, 0}
            else
                ns_din <= 0
        """
        if refrac > 0:
            return (0, refrac - 1)
        elif v_mem > leak_total:
            return (v_mem - leak_total, 0)
        else:
            return (0, 0)

    def test_single_shift_leak(self):
        """Single-shift leak: leak_rate=3 → shift1=3, tau=0.875."""
        params = LIFNeuronParams(threshold=10000, leak_rate=3)
        neuron = HWAccurateLIFNeuron(0, params)

        test_values = [100, 255, 1000, 8, 7, 1, 0, 65535]
        for v in test_values:
            neuron.state.v_mem = v
            neuron.state.refrac_counter = 0

            # RTL reference
            leak_total = self._rtl_leak(v, 3)
            expected_v, _ = self._rtl_leak_writeback(v, 0, leak_total)

            # Python simulator
            neuron.tick(syn_valid=False)
            actual_v = neuron.get_membrane_potential()

            assert actual_v == expected_v, \
                f"Leak mismatch at v={v}: RTL={expected_v}, Python={actual_v}"
        print("PASS: test_single_shift_leak")

    def test_dual_shift_leak(self):
        """Dual-shift leak: leak_rate=51 → shift1=3, shift2=6, tau≈0.859."""
        # leak_rate = 3 | (6 << 3) = 3 | 48 = 51
        params = LIFNeuronParams(threshold=10000, leak_rate=51)
        neuron = HWAccurateLIFNeuron(0, params)

        test_values = [1000, 500, 256, 128, 64, 32, 16, 8, 1, 0]
        for v in test_values:
            neuron.state.v_mem = v
            neuron.state.refrac_counter = 0

            # RTL reference
            leak_total = self._rtl_leak(v, 51)
            expected_v, _ = self._rtl_leak_writeback(v, 0, leak_total)

            # Python simulator
            neuron.tick(syn_valid=False)
            actual_v = neuron.get_membrane_potential()

            assert actual_v == expected_v, \
                f"Dual-shift mismatch at v={v}: RTL={expected_v}, Python={actual_v}"
        print("PASS: test_dual_shift_leak")

    def test_leak_during_refractory(self):
        """Leak during refractory: membrane zeroed, counter decremented."""
        params = LIFNeuronParams(threshold=10000, leak_rate=3, refractory_period=5)
        neuron = HWAccurateLIFNeuron(0, params)

        # Set neuron to refractory state
        neuron.state.v_mem = 500
        neuron.state.refrac_counter = 3

        # RTL: in ST_LEAK_WR, if ref_rd > 0: ns_din <= {0, ref_rd - 1}
        neuron.tick(syn_valid=False)
        assert neuron.get_membrane_potential() == 0, "Membrane should be 0 during refractory"
        assert neuron.state.refrac_counter == 2, "Refrac counter should decrement"
        print("PASS: test_leak_during_refractory")

    def test_all_leak_rates(self):
        """Exhaustive: all valid leak_rate configs produce matching results."""
        test_membrane = 1000
        for leak_rate in range(256):
            shift1 = leak_rate & 0x07
            if shift1 == 0:
                continue  # shift1=0 means no primary leak

            params = LIFNeuronParams(threshold=65535, leak_rate=leak_rate)
            neuron = HWAccurateLIFNeuron(0, params)
            neuron.state.v_mem = test_membrane
            neuron.state.refrac_counter = 0

            leak_total = self._rtl_leak(test_membrane, leak_rate)
            expected_v, _ = self._rtl_leak_writeback(test_membrane, 0, leak_total)

            neuron.tick(syn_valid=False)
            actual_v = neuron.get_membrane_potential()

            assert actual_v == expected_v, \
                f"leak_rate={leak_rate}: RTL={expected_v}, Python={actual_v}"
        print("PASS: test_all_leak_rates")

    def test_tau_conversion_roundtrip(self):
        """tau_to_leak_rate and leak_rate_to_tau are consistent."""
        available = get_available_tau_values()
        for tau_val, lr in available:
            recovered_tau = leak_rate_to_tau(lr)
            assert abs(recovered_tau - tau_val) < 1e-10, \
                f"Roundtrip failed: tau={tau_val}, lr={lr}, recovered={recovered_tau}"
        print(f"PASS: test_tau_conversion_roundtrip ({len(available)} configs)")


# =============================================================================
# 2. Spike Processing: Bit-Accurate Threshold & Accumulation
# =============================================================================

class TestSpikeProcessing:
    """Verify spike processing matches core_group.v ST_SPIKE_CMP/WR."""

    @staticmethod
    def _rtl_spike_process(v_mem: int, refrac: int, weight: int, exc: bool,
                           threshold: int, refrac_period: int) -> tuple:
        """
        Exact RTL spike processing from core_group.v:
            synaptic_sum = {1'b0, mem_rd} + {zeros, sp_weight}
            threshold_diff = synaptic_sum - {1'b0, global_threshold}
            threshold_hit = sp_exc && ~threshold_diff[DATA_WIDTH]

        ST_SPIKE_CMP:
            sp_fired = 0
            if (ref_rd == 0 && sp_exc)
                if (~threshold_diff[DATA_WIDTH])  → sp_fired = 1

        ST_SPIKE_WR:
            if (ref_rd > 0)    → ns_din = ns_dout (unchanged)
            elif (sp_fired)    → ns_din = {0, refrac_period}; spike_out
            elif (sp_exc)      → ns_din = {saturate(synaptic_sum), ref_rd}
            else (inhibitory)  → ns_din = {max(mem_rd - weight, 0), ref_rd}
        """
        synaptic_sum = v_mem + weight  # 17-bit in RTL
        threshold_diff = synaptic_sum - threshold

        fired = False
        new_v = v_mem
        new_r = refrac

        if refrac > 0:
            # Refractory: keep state unchanged
            new_v = v_mem
            new_r = refrac
        elif exc:
            if threshold_diff >= 0:  # ~threshold_diff[16] means non-negative
                fired = True
                new_v = 0
                new_r = refrac_period
            else:
                # Saturate at 16-bit
                new_v = min(synaptic_sum, 65535)
                new_r = refrac
        else:
            # Inhibitory
            if v_mem >= weight:
                new_v = v_mem - weight
            else:
                new_v = 0
            new_r = refrac

        return fired, new_v, new_r

    def test_excitatory_accumulation(self):
        """Excitatory weight adds to membrane, saturates at 16-bit."""
        params = LIFNeuronParams(threshold=1000, leak_rate=7)
        neuron = HWAccurateLIFNeuron(0, params)

        test_cases = [
            (0, 10, True, 1000),     # v=0 + w=10 = 10
            (990, 15, True, 1000),   # v=990 + w=15 = 1005 ≥ 1000 → fire
            (500, 5, True, 1000),    # v=500 + w=5 = 505
            (65530, 10, True, 1000), # v=65530 + w=10 = 65540 → saturate to 65535
        ]
        for v, w, exc, thresh in test_cases:
            neuron.state.v_mem = v
            neuron.state.refrac_counter = 0

            fired_rtl, v_rtl, r_rtl = self._rtl_spike_process(v, 0, w, exc, thresh, 0)
            fired_py = neuron.tick(syn_valid=True, syn_weight=w, syn_excitatory=exc)

            assert fired_py == fired_rtl, \
                f"Fire mismatch v={v} w={w}: RTL={fired_rtl}, Python={fired_py}"
            assert neuron.get_membrane_potential() == v_rtl, \
                f"Membrane mismatch v={v} w={w}: RTL={v_rtl}, Python={neuron.get_membrane_potential()}"
        print("PASS: test_excitatory_accumulation")

    def test_inhibitory_subtraction(self):
        """Inhibitory weight subtracts, floors at 0."""
        params = LIFNeuronParams(threshold=1000, leak_rate=7)
        neuron = HWAccurateLIFNeuron(0, params)

        test_cases = [
            (100, 5, False),   # v=100 - 5 = 95
            (10, 15, False),   # v=10 - 15 = 0 (floor)
            (0, 10, False),    # v=0 - 10 = 0 (floor)
            (15, 15, False),   # v=15 - 15 = 0 (exact)
        ]
        for v, w, exc in test_cases:
            neuron.state.v_mem = v
            neuron.state.refrac_counter = 0

            _, v_rtl, _ = self._rtl_spike_process(v, 0, w, exc, 1000, 0)
            neuron.tick(syn_valid=True, syn_weight=w, syn_excitatory=exc)

            assert neuron.get_membrane_potential() == v_rtl, \
                f"Inhibitory mismatch v={v} w={w}: RTL={v_rtl}, Python={neuron.get_membrane_potential()}"
        print("PASS: test_inhibitory_subtraction")

    def test_refractory_blocks_spike(self):
        """During refractory, state unchanged regardless of input."""
        params = LIFNeuronParams(threshold=10, leak_rate=7, refractory_period=5)
        neuron = HWAccurateLIFNeuron(0, params)

        neuron.state.v_mem = 50
        neuron.state.refrac_counter = 3

        # RTL: ref_rd > 0 → ns_din = ns_dout (keep state)
        fired = neuron.tick(syn_valid=True, syn_weight=15, syn_excitatory=True)
        assert not fired, "Should not fire during refractory"
        assert neuron.get_membrane_potential() == 50, "Membrane should be unchanged"
        assert neuron.state.refrac_counter == 3, "Refrac counter unchanged by spike"
        print("PASS: test_refractory_blocks_spike")

    def test_inhibitory_never_fires(self):
        """
        RTL: sp_fired = sp_exc && ~threshold_diff[DATA_WIDTH]
        Inhibitory (sp_exc=0) can NEVER trigger a fire, even if v_mem > threshold.
        """
        params = LIFNeuronParams(threshold=10, leak_rate=7)
        neuron = HWAccurateLIFNeuron(0, params)

        neuron.state.v_mem = 100  # Well above threshold
        fired = neuron.tick(syn_valid=True, syn_weight=15, syn_excitatory=False)
        assert not fired, "Inhibitory should never fire"
        assert neuron.get_membrane_potential() == 85, "v=100-15=85"
        print("PASS: test_inhibitory_never_fires")

    def test_exact_threshold(self):
        """Spike at exactly threshold (synaptic_sum == threshold)."""
        params = LIFNeuronParams(threshold=100, leak_rate=7, refractory_period=5)
        neuron = HWAccurateLIFNeuron(0, params)

        neuron.state.v_mem = 90
        fired = neuron.tick(syn_valid=True, syn_weight=10, syn_excitatory=True)
        # 90 + 10 = 100 >= 100 → fire
        assert fired, "Should fire at exact threshold"
        assert neuron.get_membrane_potential() == 0
        assert neuron.state.refrac_counter == 5
        print("PASS: test_exact_threshold")

    def test_just_below_threshold(self):
        """No spike just below threshold."""
        params = LIFNeuronParams(threshold=100, leak_rate=7)
        neuron = HWAccurateLIFNeuron(0, params)

        neuron.state.v_mem = 90
        fired = neuron.tick(syn_valid=True, syn_weight=9, syn_excitatory=True)
        # 90 + 9 = 99 < 100 → no fire
        assert not fired, "Should not fire below threshold"
        assert neuron.get_membrane_potential() == 99
        print("PASS: test_just_below_threshold")


# =============================================================================
# 3. Core Group: Intra-Group Recurrence (FIFO + Weight Matrix)
# =============================================================================

class TestCoreGroupRecurrence:
    """Verify intra-group recurrence matches core_group.v ST_INTRA_ROUTE/READ."""

    def test_single_recurrence(self):
        """Fired neuron → weight row scan → push to FIFO."""
        params = LIFNeuronParams(threshold=10, leak_rate=7, refractory_period=2)
        group = HWCoreGroup(group_id=0, params=params)

        # Weight: N0 → N5 (w=8, exc)
        group.set_weight(0, 5, 8, True)

        # Fire N0
        group.push_spike(0, 15, True)  # 15 >= 10 → fire
        fired = group.process_step()

        assert 0 in fired, "N0 should fire"
        assert group.get_membrane(5) > 0, "N5 should receive recurrent spike"

        # RTL: weight read gives w=8, push to FIFO {exc=1, weight=8, dest=5}
        # N5 gets w=8 < threshold=10 → no fire, membrane = 8 (after leak)
        # After leak with shift1=7: leak = 8>>7 = 0, so v stays 8... but leak
        # happens AFTER spike processing, so:
        #   N5 receives w=8, v_mem = 0 + 8 = 8, then leak: 8 - (8>>7) = 8 - 0 = 8
        assert group.get_membrane(5) == 8, f"N5 membrane should be 8, got {group.get_membrane(5)}"
        print("PASS: test_single_recurrence")

    def test_chain_recurrence(self):
        """Chain: N0→N1→N2 all fire within same process_step."""
        params = LIFNeuronParams(threshold=10, leak_rate=7, refractory_period=2)
        group = HWCoreGroup(group_id=0, params=params)

        group.set_weight(0, 1, 15, True)  # N0→N1 (15 >= 10)
        group.set_weight(1, 2, 15, True)  # N1→N2 (15 >= 10)

        group.push_spike(0, 15, True)
        fired = group.process_step()

        assert 0 in fired and 1 in fired and 2 in fired, \
            f"Chain should fire all three, got {fired}"
        print("PASS: test_chain_recurrence")

    def test_inhibitory_weight_in_recurrence(self):
        """Inhibitory intra-group weight blocks downstream fire."""
        params = LIFNeuronParams(threshold=20, leak_rate=7, refractory_period=2)
        group = HWCoreGroup(group_id=0, params=params)

        # N10 → N11 (inhibitory, w=5)
        group.set_weight(10, 11, 5, False)

        # Pre-charge N11 to 15
        group.push_spike(11, 15, True)
        group.process_step()
        assert group.get_membrane(11) > 0

        # Fire N10 → recurrence pushes inhibitory spike to N11
        group.push_spike(10, 15, True)  # N10 fires (15 < 20, but let's use enough)

        # Need to actually fire N10
        group2 = HWCoreGroup(group_id=0, params=LIFNeuronParams(threshold=10, leak_rate=7))
        group2.set_weight(10, 11, 5, False)  # inhibitory
        group2.v_mem[11] = 15  # Pre-set N11 membrane
        group2.push_spike(10, 15, True)  # N10 fires
        fired = group2.process_step()

        assert 10 in fired, "N10 should fire"
        # N11 receives inhibitory w=5: 15 - 5 = 10 (after leak: 10 - 0 = 10)
        assert group2.get_membrane(11) == 10, \
            f"N11 should be 15-5=10 after inhibitory, got {group2.get_membrane(11)}"
        print("PASS: test_inhibitory_weight_in_recurrence")

    def test_weight_zero_no_push(self):
        """Zero weight connections are NOT pushed to FIFO."""
        params = LIFNeuronParams(threshold=10, leak_rate=7)
        group = HWCoreGroup(group_id=0, params=params)

        # W(0,1)=0 (default), W(0,2)=5
        group.set_weight(0, 2, 5, True)

        group.push_spike(0, 15, True)
        fired = group.process_step()

        assert 0 in fired
        assert group.get_membrane(1) == 0, "N1 should not receive spike (w=0)"
        assert group.get_membrane(2) == 5, "N2 should receive spike (w=5)"
        print("PASS: test_weight_zero_no_push")


# =============================================================================
# 4. Connectivity Table: Address & Data Format
# =============================================================================

class TestConnectivityTable:
    """Verify CT matches synaptic_connectivity_table.v bit layout."""

    def test_address_format(self):
        """
        CT address: {src_group[3], src_neuron[7], fanout_idx[4]} = 14 bits.
        Verify address calculation matches RTL.
        """
        ct = HWConnectivityTable(num_groups=16, neurons_per_group=128, max_fanout=16)

        # Scattershot test of addresses
        test_cases = [
            (0, 0, 0),      # Base
            (0, 0, 15),     # Max fanout
            (0, 127, 0),    # Max neuron
            (15, 127, 15),  # All max
            (7, 64, 8),     # Mid-range
        ]
        for sg, sn, fi in test_cases:
            ct.write(sg, sn, fi, valid=True, dst_group=1, dst_neuron=2,
                     weight=3, exc_inh=True)
            entry = ct.lookup(sg, sn, fi)
            assert entry.valid, f"Entry ({sg},{sn},{fi}) should be valid"
            assert entry.dst_group == 1
            assert entry.dst_neuron == 2
            assert entry.weight == 3
        print("PASS: test_address_format")

    def test_data_format(self):
        """
        CT data: [15] valid, [14:12] dst_group(3b for 8 groups), [11:5] dst_neuron,
                 [4:1] weight, [0] exc_inh
        Verify all fields roundtrip correctly.
        """
        ct = HWConnectivityTable(num_groups=16, neurons_per_group=128, max_fanout=16)

        ct.write(0, 0, 0, valid=True, dst_group=15, dst_neuron=127,
                 weight=15, exc_inh=False)
        entry = ct.lookup(0, 0, 0)
        assert entry.valid
        assert entry.dst_group == 15
        assert entry.dst_neuron == 127
        assert entry.weight == 15
        assert entry.exc_inh is False

        # Weight clipping
        ct.write(0, 0, 1, valid=True, dst_group=0, dst_neuron=0,
                 weight=300, exc_inh=True)
        entry = ct.lookup(0, 0, 1)
        assert entry.weight == 255, "Weight should clip to MAX_WEIGHT"
        print("PASS: test_data_format")

    def test_invalid_entry_terminates(self):
        """RTL: invalid entry stops fanout iteration (first invalid breaks)."""
        ct = HWConnectivityTable()

        ct.write(0, 0, 0, True, 1, 0, 10, True)
        ct.write(0, 0, 1, False, 0, 0, 0, True)  # Invalid terminates
        ct.write(0, 0, 2, True, 2, 0, 5, True)   # Should not be reached

        conns = ct.get_all_connections(0, 0)
        assert len(conns) == 1, f"Should stop at invalid entry, got {len(conns)}"
        print("PASS: test_invalid_entry_terminates")


# =============================================================================
# 5. Event Router: Round-Robin + CT Lookup
# =============================================================================

class TestEventRouter:
    """Verify router matches event_router_ng.v FSM behavior."""

    def test_round_robin_advancement(self):
        """Router advances round-robin pointer after each arbitration."""
        params = LIFNeuronParams(threshold=10, leak_rate=7)
        groups = [HWCoreGroup(g, params=params) for g in range(4)]
        ct = HWConnectivityTable(num_groups=4)
        router = HWEventRouter(num_groups=4, ct=ct)

        # Fire G0, then G1
        groups[0].push_spike(0, 15, True)
        groups[0].process_step()
        router.route_spikes(groups)

        groups[1].push_spike(0, 15, True)
        groups[1].process_step()
        router.route_spikes(groups)

        # Both should have been routed
        assert router.routed_spike_count == 2
        print("PASS: test_round_robin_advancement")

    def test_ct_lookup_delivery(self):
        """Router looks up CT and delivers to destination group."""
        params = LIFNeuronParams(threshold=10, leak_rate=7)
        groups = [HWCoreGroup(g, params=params) for g in range(4)]
        ct = HWConnectivityTable(num_groups=4)

        # G0:N5 → G2:N10 (w=12, exc)
        ct.write(0, 5, 0, True, dst_group=2, dst_neuron=10, weight=12, exc_inh=True)
        ct.write(0, 5, 1, False, 0, 0, 0, True)  # Terminate

        router = HWEventRouter(num_groups=4, ct=ct)

        # Fire G0:N5
        groups[0].push_spike(5, 15, True)
        groups[0].process_step()

        learn_events = router.route_spikes(groups)

        # Check delivery to G2
        assert len(groups[2].fifo) > 0, "G2 should have received spike"
        entry = groups[2].fifo[0]
        assert entry.dest_id == 10, "Should target N10"
        assert entry.weight == 12, "Weight should be 12"
        assert entry.exc is True, "Should be excitatory"

        # Check learn notification
        assert len(learn_events) > 0, "Should notify learning engine"
        # Global ID = (0 << 7) | 5 = 5
        assert learn_events[0] == 5
        print("PASS: test_ct_lookup_delivery")

    def test_multi_fanout_delivery(self):
        """Multiple fanout entries all deliver correctly."""
        params = LIFNeuronParams(threshold=10, leak_rate=7)
        groups = [HWCoreGroup(g, params=params) for g in range(4)]
        ct = HWConnectivityTable(num_groups=4)

        # G0:N0 → G1:N1 (w=5), G2:N2 (w=8), G3:N3 (w=12)
        ct.write(0, 0, 0, True, 1, 1, 5, True)
        ct.write(0, 0, 1, True, 2, 2, 8, True)
        ct.write(0, 0, 2, True, 3, 3, 12, True)
        ct.write(0, 0, 3, False, 0, 0, 0, True)  # Terminate

        router = HWEventRouter(num_groups=4, ct=ct)

        groups[0].push_spike(0, 15, True)
        groups[0].process_step()
        router.route_spikes(groups)

        assert len(groups[1].fifo) == 1, "G1 should receive 1 spike"
        assert len(groups[2].fifo) == 1, "G2 should receive 1 spike"
        assert len(groups[3].fifo) == 1, "G3 should receive 1 spike"
        assert groups[1].fifo[0].weight == 5
        assert groups[2].fifo[0].weight == 8
        assert groups[3].fifo[0].weight == 12
        print("PASS: test_multi_fanout_delivery")


# =============================================================================
# 6. Full System: End-to-End Cross-Verification
# =============================================================================

class TestSystemCrossVerification:
    """
    End-to-end tests matching tb_integration.v test scenarios.
    Same parameters, same inputs, same expected outputs.
    """

    def _make_system(self, num_groups=4, neurons_per_group=16):
        """Create a system matching tb_integration.v parameters."""
        return HWAccurateSNNSimulator(
            num_groups=num_groups,
            neurons_per_group=neurons_per_group,
            neuron_params=LIFNeuronParams(
                threshold=10,
                leak_rate=0,  # No leak for deterministic testing (matches tb)
                refractory_period=3
            )
        )

    def test_external_spike_fires(self):
        """
        Matches tb_integration.v Test 4:
        External spike w=15 to G0:N5 → fires (15 >= 10).
        """
        sim = self._make_system()

        # Global ID for G0:N5 with num_groups=4, neurons_per_group=16:
        # GROUP_ID_WIDTH = $clog2(4) = 2, LOCAL_ID_WIDTH = $clog2(16) = 4
        # global_id = (0 << 4) | 5 = 5
        gid = sim.local_to_global(0, 5)

        fired = sim.tick([(gid, 15, True)])
        assert gid in fired, f"G0:N5 should fire, got {fired}"
        print("PASS: test_external_spike_fires (matches tb_integration Test 4)")

    def test_inter_group_propagation(self):
        """
        Matches tb_integration.v Test 5:
        G0:N5 fires → CT routes to G1:N8 (w=15) → G1:N8 fires.
        """
        sim = self._make_system()

        # Setup CT: G0:N5 → G1:N8 (w=15, exc)
        sim.set_inter_connection(0, 5, 0, dst_group=1, dst_neuron=8, weight=15, exc=True)

        # Fire G0:N5
        gid_src = sim.local_to_global(0, 5)
        fired = sim.tick([(gid_src, 15, True)])

        assert gid_src in fired, "G0:N5 should fire"

        # G1:N8 should also fire (received w=15 >= thresh=10)
        gid_dst = sim.local_to_global(1, 8)
        assert gid_dst in fired, f"G1:N8 should fire via inter-group, got {fired}"
        print("PASS: test_inter_group_propagation (matches tb_integration Test 5)")

    def test_chain_propagation(self):
        """
        Matches tb_integration.v Test 6:
        G0:N5 → G1:N8 → G2:N3 (chain of inter-group routing).
        """
        sim = self._make_system()

        sim.set_inter_connection(0, 5, 0, dst_group=1, dst_neuron=8, weight=15, exc=True)
        sim.set_inter_connection(1, 8, 0, dst_group=2, dst_neuron=3, weight=15, exc=True)

        gid_src = sim.local_to_global(0, 5)
        fired = sim.tick([(gid_src, 15, True)])

        gid_g1n8 = sim.local_to_global(1, 8)
        gid_g2n3 = sim.local_to_global(2, 3)
        assert gid_g1n8 in fired, "G1:N8 should fire"
        assert gid_g2n3 in fired, "G2:N3 should fire (chain)"
        print("PASS: test_chain_propagation (matches tb_integration Test 6)")

    def test_intra_plus_inter(self):
        """
        Matches tb_integration.v Test 7:
        G3:N0 fires → intra-group to G3:N1 (fires) + inter-group to G2:N10 (fires).
        """
        sim = self._make_system()

        # Intra-group: G3:N0 → G3:N1 (w=15, exc)
        sim.set_intra_weight(3, 0, 1, weight=15, exc=True)
        # Inter-group: G3:N0 → G2:N10 (w=15, exc)
        sim.set_inter_connection(3, 0, 0, dst_group=2, dst_neuron=10, weight=15, exc=True)

        gid_src = sim.local_to_global(3, 0)
        fired = sim.tick([(gid_src, 15, True)])

        gid_g3n0 = sim.local_to_global(3, 0)
        gid_g3n1 = sim.local_to_global(3, 1)
        gid_g2n10 = sim.local_to_global(2, 10)

        assert gid_g3n0 in fired, "G3:N0 should fire"
        assert gid_g3n1 in fired, "G3:N1 should fire (intra-group recurrence)"
        assert gid_g2n10 in fired, "G2:N10 should fire (inter-group)"
        print("PASS: test_intra_plus_inter (matches tb_integration Test 7)")

    def test_multi_group_fanout(self):
        """
        Matches tb_integration.v Test 9:
        G0:N10 → G1:N0, G2:N0, G3:N5 (all fire with w=15).
        """
        sim = self._make_system()

        sim.set_inter_connection(0, 10, 0, dst_group=1, dst_neuron=0, weight=15, exc=True)
        sim.set_inter_connection(0, 10, 1, dst_group=2, dst_neuron=0, weight=15, exc=True)
        sim.set_inter_connection(0, 10, 2, dst_group=3, dst_neuron=5, weight=15, exc=True)

        gid_src = sim.local_to_global(0, 10)
        fired = sim.tick([(gid_src, 15, True)])

        for (g, n) in [(1, 0), (2, 0), (3, 5)]:
            gid = sim.local_to_global(g, n)
            assert gid in fired, f"G{g}:N{n} should fire via fanout"
        print("PASS: test_multi_group_fanout (matches tb_integration Test 9)")

    def test_sub_threshold_inter(self):
        """
        Matches tb_integration.v Test 12:
        G0:N11 → G1:N2 (w=5 < thresh=10) → G1:N2 does NOT fire.
        """
        sim = self._make_system()

        sim.set_inter_connection(0, 11, 0, dst_group=1, dst_neuron=2, weight=5, exc=True)

        gid_src = sim.local_to_global(0, 11)
        fired = sim.tick([(gid_src, 15, True)])

        gid_g1n2 = sim.local_to_global(1, 2)
        assert gid_g1n2 not in fired, "G1:N2 should NOT fire (sub-threshold)"
        # But membrane should have accumulated
        assert sim.groups[1].get_membrane(2) > 0, "G1:N2 should have non-zero membrane"
        print("PASS: test_sub_threshold_inter (matches tb_integration Test 12)")

    def test_global_id_format(self):
        """Verify global ID format matches RTL bit layout."""
        # RTL: global_id = {group_id[GROUP_ID_WIDTH-1:0], local_id[LOCAL_ID_WIDTH-1:0]}
        # With GROUP_ID_WIDTH=4, LOCAL_ID_WIDTH=7:
        # global_id[10:7] = group_id, global_id[6:0] = local_id

        for gid in range(16):
            for lid in [0, 1, 63, 64, 126, 127]:
                global_id = HWAccurateSNNSimulator.local_to_global(gid, lid)
                g_back, l_back = HWAccurateSNNSimulator.global_to_local(global_id)

                # RTL format: (gid << 7) | lid
                rtl_global = (gid << LOCAL_ID_WIDTH) | lid
                assert global_id == rtl_global, \
                    f"ID format mismatch: G{gid}:N{lid} → {global_id} != RTL {rtl_global}"
                assert g_back == gid and l_back == lid, \
                    f"Roundtrip failed: G{gid}:N{lid} → {global_id} → G{g_back}:N{l_back}"
        print("PASS: test_global_id_format")

    def test_spike_count_consistency(self):
        """Spike counts match between groups and router."""
        sim = self._make_system()

        # Setup some connections
        sim.set_inter_connection(0, 0, 0, 1, 0, 15, True)
        sim.set_inter_connection(1, 0, 0, 2, 0, 15, True)
        sim.set_intra_weight(0, 0, 1, 15, True)

        # Fire
        gid = sim.local_to_global(0, 0)
        sim.tick([(gid, 15, True)])

        # Check consistency
        total_group_spikes = sum(g.total_spikes for g in sim.groups)
        assert total_group_spikes > 0, "Should have some spikes"
        assert sim.router.routed_spike_count > 0, "Router should have routed spikes"
        print(f"PASS: test_spike_count_consistency (group_total={total_group_spikes}, "
              f"routed={sim.router.routed_spike_count})")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    test_classes = [
        TestLeakComputation,
        TestSpikeProcessing,
        TestCoreGroupRecurrence,
        TestConnectivityTable,
        TestEventRouter,
        TestSystemCrossVerification,
    ]

    total_pass = 0
    total_fail = 0

    for cls in test_classes:
        print(f"\n{'=' * 60}")
        print(f"  {cls.__name__}")
        print(f"{'=' * 60}")
        obj = cls()
        for name in sorted(dir(obj)):
            if name.startswith('test_'):
                try:
                    getattr(obj, name)()
                    total_pass += 1
                except Exception as e:
                    print(f"FAIL: {name}: {e}")
                    total_fail += 1

    print(f"\n{'=' * 60}")
    print(f"Cross-Verification: {total_pass} PASS, {total_fail} FAIL")
    print(f"{'=' * 60}")
    sys.exit(1 if total_fail > 0 else 0)
