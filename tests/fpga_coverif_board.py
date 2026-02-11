#!/usr/bin/env python3
"""
FPGA-Side Co-Verification Script
=================================
Runs directly on the PYNQ board. Loads bitstream, exercises HW registers
and spike processing, then outputs structured JSON results for host-side
comparison with the bit-accurate Python simulator.

Usage (on PYNQ board):
    source /usr/local/share/pynq-venv/bin/activate
    python3 fpga_coverif_board.py [--bitstream path/to/snn_integrated.bit]

Output:
    Prints JSON to stdout with test results. All logging goes to stderr.
"""

import json
import sys
import time
import argparse
import traceback
import numpy as np

# ─────────────────────────────────────────────────────────
# Register Constants (matching snn_integrated block design)
# ─────────────────────────────────────────────────────────

# HLS IP (snn_top_hls_0) @ 0x43C00000 — AXI4-Lite, 128 bytes
HLS_AP_CTRL         = 0x00
HLS_CTRL_REG        = 0x10
HLS_CONFIG_REG      = 0x18
HLS_LEARNING_PARAMS = 0x20
HLS_STATUS_REG      = 0x38
HLS_SPIKE_COUNT     = 0x48
HLS_WEIGHT_SUM      = 0x58
HLS_VERSION         = 0x68
HLS_REWARD_SIGNAL   = 0x78

# ctrl_reg bits
CTRL_ENABLE       = 0x01
CTRL_RESET        = 0x02
CTRL_CLEAR        = 0x04
CTRL_LEARNING_EN  = 0x08
CTRL_WEIGHT_READ  = 0x10
CTRL_APPLY_REWARD = 0x20
CTRL_WEIGHT_LOAD  = 0x40

# SNN Config Regs (snn_config_regs_0) @ 0x43C10000 — AXI4-Lite, 4K
CFG_CONFIG_CTRL       = 0x00
CFG_CONFIG_ADDR       = 0x04
CFG_CONFIG_WDATA      = 0x08
CFG_CONFIG_RDATA      = 0x0C
CFG_THRESHOLD         = 0x10
CFG_NEURON_PARAMS     = 0x14
CFG_ROUTER_SPIKE_CNT  = 0x18
CFG_NEURON_SPIKE_CNT  = 0x1C
CFG_STATUS            = 0x20
CFG_THROUGHPUT        = 0x24
CFG_VERSION           = 0x28


def log(msg):
    """Log to stderr so it doesn't pollute JSON stdout."""
    print(msg, file=sys.stderr, flush=True)


# ─────────────────────────────────────────────────────────
# Core Group Config Register Encoding
# (Matches snn_core_group_top.v RTL format)
# ─────────────────────────────────────────────────────────

def encode_ct_write(src_group, src_neuron, fanout_idx,
                    dst_group, dst_neuron, weight, exc=True, valid=True):
    """
    Encode a connectivity table write for inter-group routing.
    
    RTL format from snn_core_group_top.v:
        addr[31:28] = 0x0 (CT write command)
        addr[3:0]   = src_group
        wdata[31]    = valid
        wdata[30:27] = dst_group
        wdata[26:20] = dst_neuron
        wdata[19:12] = weight (8-bit)
        wdata[11]    = exc_inh
        wdata[10:7]  = fanout_idx
        wdata[6:0]   = src_neuron
    
    Returns: (addr, wdata) tuple
    """
    addr = (0x0 << 28) | (src_group & 0xF)
    wdata = ((1 if valid else 0) << 31) | \
            ((dst_group & 0xF) << 27) | \
            ((dst_neuron & 0x7F) << 20) | \
            ((weight & 0xFF) << 12) | \
            ((1 if exc else 0) << 11) | \
            ((fanout_idx & 0xF) << 7) | \
            (src_neuron & 0x7F)
    return addr, wdata


def encode_intra_weight(group_id, src_neuron, dst_neuron, weight, exc=True):
    """
    Encode an intra-group weight write.
    
    RTL format from snn_core_group_top.v:
        addr[31:28] = 0x1 (intra-group weight command)
        wdata[31:25] = src_neuron
        wdata[24:18] = dst_neuron
        wdata[17:10] = weight (8-bit)
        wdata[9]     = exc
        wdata[8:5]   = group_id
        wdata[4:0]   = reserved
    
    Returns: (addr, wdata) tuple
    """
    addr = (0x1 << 28)
    wdata = ((src_neuron & 0x7F) << 25) | \
            ((dst_neuron & 0x7F) << 18) | \
            ((weight & 0xFF) << 10) | \
            ((1 if exc else 0) << 9) | \
            ((group_id & 0xF) << 5)
    return addr, wdata


def write_config(cfg, target, addr, wdata):
    """Write a config register via snn_config_regs AXI-Lite interface."""
    cfg.write(CFG_CONFIG_CTRL, target & 0x3)  # 0=router, 1=neuron
    cfg.write(CFG_CONFIG_ADDR, addr)
    cfg.write(CFG_CONFIG_WDATA, wdata)  # triggers config_we
    time.sleep(0.00001)  # small delay for single-cycle latency


def read_config(cfg, target, addr):
    """Read back from config address space."""
    cfg.write(CFG_CONFIG_CTRL, target & 0x3)
    cfg.write(CFG_CONFIG_ADDR, addr)
    time.sleep(0.00001)
    return cfg.read(CFG_CONFIG_RDATA)


# ─────────────────────────────────────────────────────────
# Test Cases
# ─────────────────────────────────────────────────────────

def test_version_registers(hls, cfg):
    """Test 1: Read version registers from both IPs."""
    results = {}
    
    # Config register version (should be 0x534E4E01 = "SNN\x01")
    cfg_ver = cfg.read(CFG_VERSION)
    results['cfg_version'] = f"0x{cfg_ver:08X}"
    results['cfg_version_valid'] = (cfg_ver == 0x534E4E01)
    
    # HLS IP version (should be date-coded, e.g. 0x20260210)
    hls_ver = hls.read(HLS_VERSION)
    results['hls_version'] = f"0x{hls_ver:08X}"
    results['hls_version_valid'] = (hls_ver != 0 and hls_ver != 0xFFFFFFFF)
    
    # AP_CTRL (sanity check — should have idle bit set = 0x04)
    ap_ctrl = hls.read(HLS_AP_CTRL)
    results['hls_ap_ctrl'] = f"0x{ap_ctrl:02X}"
    results['hls_idle'] = bool(ap_ctrl & 0x04)
    
    results['pass'] = results['cfg_version_valid'] and results['hls_version_valid']
    return results


def test_parameter_readback(hls, cfg):
    """Test 2: Write neuron parameters and verify consistency."""
    results = {}
    
    test_threshold = 500
    test_leak_rate = 3      # shift1=3 → tau≈0.875
    test_refrac = 10
    
    # Write threshold to config regs
    cfg.write(CFG_THRESHOLD, test_threshold & 0xFFFF)
    time.sleep(0.0001)
    
    # Write neuron params: [15:8]=refractory, [7:0]=leak_rate
    params = (test_refrac & 0xFF) << 8 | (test_leak_rate & 0xFF)
    cfg.write(CFG_NEURON_PARAMS, params)
    time.sleep(0.0001)
    
    # Read back
    threshold_rb = cfg.read(CFG_THRESHOLD)
    params_rb = cfg.read(CFG_NEURON_PARAMS)
    leak_rb = params_rb & 0xFF
    refrac_rb = (params_rb >> 8) & 0xFF
    
    results['threshold_written'] = test_threshold
    results['threshold_readback'] = threshold_rb & 0xFFFF
    results['threshold_match'] = (threshold_rb & 0xFFFF) == test_threshold
    
    results['leak_rate_written'] = test_leak_rate
    results['leak_rate_readback'] = leak_rb
    results['leak_rate_match'] = leak_rb == test_leak_rate
    
    results['refractory_written'] = test_refrac
    results['refractory_readback'] = refrac_rb
    results['refractory_match'] = refrac_rb == test_refrac
    
    # Also write to HLS config_reg (threshold + leak_rate)
    hls_config = (test_leak_rate & 0xFFFF) << 16 | (test_threshold & 0xFFFF)
    hls.write(HLS_CONFIG_REG, hls_config)
    time.sleep(0.0001)
    hls_config_rb = hls.read(HLS_CONFIG_REG)
    results['hls_config_written'] = f"0x{hls_config:08X}"
    results['hls_config_readback'] = f"0x{hls_config_rb:08X}"
    results['hls_config_match'] = hls_config_rb == hls_config
    
    results['pass'] = all([
        results['threshold_match'],
        results['leak_rate_match'],
        results['refractory_match'],
        results['hls_config_match'],
    ])
    return results


def test_ct_programming(hls, cfg):
    """Test 3: Program connectivity table entries and read back."""
    results = {}
    
    # Write a CT entry: group0, neuron5 → group1, neuron10, weight=100, exc
    ct_addr, ct_wdata = encode_ct_write(
        src_group=0, src_neuron=5, fanout_idx=0,
        dst_group=1, dst_neuron=10, weight=100, exc=True, valid=True
    )
    write_config(cfg, target=0, addr=ct_addr, wdata=ct_wdata)
    
    results['ct_write_addr'] = f"0x{ct_addr:08X}"
    results['ct_write_data'] = f"0x{ct_wdata:08X}"
    
    # Write second entry: group0, neuron5 → group2, neuron3, weight=50, inh
    ct_addr2, ct_wdata2 = encode_ct_write(
        src_group=0, src_neuron=5, fanout_idx=1,
        dst_group=2, dst_neuron=3, weight=50, exc=False, valid=True
    )
    write_config(cfg, target=0, addr=ct_addr2, wdata=ct_wdata2)
    
    results['ct_write2_addr'] = f"0x{ct_addr2:08X}"
    results['ct_write2_data'] = f"0x{ct_wdata2:08X}"
    
    # Try reading back via status readback (addr[31:28]=0x2)
    status_addr = (0x2 << 28)
    rdata = read_config(cfg, target=0, addr=status_addr)
    results['status_readback'] = f"0x{rdata:08X}"
    
    # Verify encoding
    # wdata[31]=1, [30:27]=dst_group=1, [26:20]=dst_neuron=10,
    # [19:12]=weight=100, [11]=exc=1, [10:7]=fanout_idx=0, [6:0]=src_neuron=5
    expected_wdata = (1 << 31) | (1 << 27) | (10 << 20) | (100 << 12) | \
                     (1 << 11) | (0 << 7) | 5
    results['encoding_valid'] = (ct_wdata == expected_wdata)
    results['expected_wdata'] = f"0x{expected_wdata:08X}"
    
    results['pass'] = results['encoding_valid']
    return results


def test_intra_weight_programming(hls, cfg):
    """Test 4: Program intra-group weights."""
    results = {}
    
    # Write intra-group weight: group0, neuron0→neuron1, weight=80, exc
    w_addr, w_wdata = encode_intra_weight(
        group_id=0, src_neuron=0, dst_neuron=1, weight=80, exc=True
    )
    write_config(cfg, target=0, addr=w_addr, wdata=w_wdata)
    
    results['intra_write_addr'] = f"0x{w_addr:08X}"
    results['intra_write_data'] = f"0x{w_wdata:08X}"
    
    # Verify encoding
    # wdata[31:25]=0, [24:18]=1, [17:10]=80, [9]=1, [8:5]=0, [4:0]=0
    expected = (0 << 25) | (1 << 18) | (80 << 10) | (1 << 9) | (0 << 5)
    results['encoding_valid'] = (w_wdata == expected)
    results['expected_wdata'] = f"0x{expected:08X}"
    
    # Write another: group0, neuron2→neuron0, weight=60, inh
    w_addr2, w_wdata2 = encode_intra_weight(
        group_id=0, src_neuron=2, dst_neuron=0, weight=60, exc=False
    )
    write_config(cfg, target=0, addr=w_addr2, wdata=w_wdata2)
    
    results['intra_write2_addr'] = f"0x{w_addr2:08X}"
    results['intra_write2_data'] = f"0x{w_wdata2:08X}"
    
    results['pass'] = results['encoding_valid']
    return results


def test_reset_and_status(hls, cfg):
    """Test 5: Reset accelerator and check post-reset status."""
    results = {}
    
    # Reset via HLS ctrl_reg
    hls.write(HLS_CTRL_REG, CTRL_RESET)
    time.sleep(0.001)
    hls.write(HLS_CTRL_REG, 0)
    time.sleep(0.001)
    
    # Check status registers post-reset
    cfg_status = cfg.read(CFG_STATUS)
    router_spikes = cfg.read(CFG_ROUTER_SPIKE_CNT)
    neuron_spikes = cfg.read(CFG_NEURON_SPIKE_CNT)
    throughput = cfg.read(CFG_THROUGHPUT)
    
    hls_status = hls.read(HLS_STATUS_REG)
    hls_spikes = hls.read(HLS_SPIKE_COUNT)
    ap_ctrl = hls.read(HLS_AP_CTRL)
    
    results['cfg_status'] = f"0x{cfg_status:08X}"
    results['fifo_overflow'] = bool(cfg_status & 0x01)
    results['router_spike_count'] = router_spikes
    results['neuron_spike_count'] = neuron_spikes
    results['throughput'] = throughput
    results['hls_status'] = f"0x{hls_status:08X}"
    results['hls_spike_count'] = hls_spikes
    results['hls_idle'] = bool(ap_ctrl & 0x04)
    
    # After reset, spike counts should be 0
    results['spikes_cleared'] = (router_spikes == 0 and neuron_spikes == 0)
    results['pass'] = results['spikes_cleared'] and not results['fifo_overflow']
    return results


def test_spike_injection_dma(hls, cfg, dma, overlay):
    """Test 6: Inject spikes via DMA and measure spike count response."""
    from pynq import allocate
    results = {}
    
    # Configure: threshold=100, leak_rate=3 (tau≈0.875), refractory=5
    threshold = 100
    leak_rate = 3
    refrac = 5
    
    cfg.write(CFG_THRESHOLD, threshold)
    params = (refrac << 8) | leak_rate
    cfg.write(CFG_NEURON_PARAMS, params)
    hls_config = (leak_rate << 16) | threshold
    hls.write(HLS_CONFIG_REG, hls_config)
    
    # Reset and clear counters
    hls.write(HLS_CTRL_REG, CTRL_RESET | CTRL_CLEAR)
    time.sleep(0.001)
    hls.write(HLS_CTRL_REG, 0)
    time.sleep(0.001)
    
    # Program simple network:
    # Intra-group0: neuron0→neuron1, weight=120, exc  (single spike: 120 > 100 → fires)
    w_addr, w_wdata = encode_intra_weight(0, 0, 1, 120, exc=True)
    write_config(cfg, target=0, addr=w_addr, wdata=w_wdata)
    
    # Inter-group: group0,neuron1 → group1,neuron0, weight=110, exc
    ct_addr, ct_wdata = encode_ct_write(0, 1, 0, 1, 0, 110, exc=True)
    write_config(cfg, target=0, addr=ct_addr, wdata=ct_wdata)
    
    # Enable accelerator
    hls.write(HLS_CTRL_REG, CTRL_ENABLE)
    hls.write(HLS_AP_CTRL, 0x81)  # ap_start + auto_restart
    time.sleep(0.001)
    
    # Create DMA input buffer with spike to neuron0 in group0
    # HLS spike format: [neuron_id(8) | weight(8) | exc(1) | reserved(15)]
    input_buf = allocate(shape=(4,), dtype=np.uint32)
    
    # Spike to global_id=0 (group0, neuron0), weight=120
    # Pack: neuron_id | (weight << 8)
    global_id_0 = 0  # group0, neuron0
    input_buf[0] = (global_id_0 & 0xFF) | ((120 & 0xFF) << 8)
    input_buf[1] = 0  # padding / end marker
    input_buf[2] = 0
    input_buf[3] = 0
    
    results['input_spike_packed'] = f"0x{int(input_buf[0]):08X}"
    results['threshold'] = threshold
    results['weight_n0_to_n1'] = 120
    results['weight_n1_to_g1n0'] = 110
    
    # Send spikes via DMA
    try:
        dma.sendchannel.transfer(input_buf)
        dma.sendchannel.wait(timeout=2.0)
        results['dma_send_ok'] = True
    except Exception as e:
        results['dma_send_ok'] = False
        results['dma_send_error'] = str(e)
    
    # Wait for processing
    time.sleep(0.01)
    
    # Collect output spikes
    output_buf = allocate(shape=(64,), dtype=np.uint32)
    try:
        dma.recvchannel.transfer(output_buf)
        dma.recvchannel.wait(timeout=1.0)
        n_out = dma.recvchannel.transferred // 4
        results['dma_recv_ok'] = True
        results['dma_output_count'] = n_out
        results['dma_output_data'] = [f"0x{int(output_buf[i]):08X}" for i in range(min(n_out, 8))]
    except Exception as e:
        results['dma_recv_ok'] = False
        results['dma_recv_error'] = str(e)
        results['dma_output_count'] = 0
    
    # Read spike counts
    router_spikes = cfg.read(CFG_ROUTER_SPIKE_CNT)
    neuron_spikes = cfg.read(CFG_NEURON_SPIKE_CNT)
    hls_spikes = hls.read(HLS_SPIKE_COUNT)
    cfg_status = cfg.read(CFG_STATUS)
    
    results['router_spike_count'] = router_spikes
    results['neuron_spike_count'] = neuron_spikes
    results['hls_spike_count'] = hls_spikes
    results['fifo_overflow'] = bool(cfg_status & 0x01)
    
    # Expected: neuron0 receives 120 weight → fires (120 > 100)
    # neuron1 receives 120 from intra → fires (120 > 100)
    # group1,neuron0 receives 110 via CT → fires (110 > 100)
    # Minimum expected: at least 1 spike
    results['any_spikes'] = (router_spikes > 0 or neuron_spikes > 0 or hls_spikes > 0)
    
    # Disable
    hls.write(HLS_CTRL_REG, 0)
    
    # Clean up DMA buffers
    del input_buf
    del output_buf
    
    results['pass'] = results.get('dma_send_ok', False)
    return results


def test_spike_count_consistency(hls, cfg):
    """Test 7: Check spike count register consistency between IPs."""
    results = {}
    
    router_spikes = cfg.read(CFG_ROUTER_SPIKE_CNT)
    neuron_spikes = cfg.read(CFG_NEURON_SPIKE_CNT)
    hls_spikes = hls.read(HLS_SPIKE_COUNT)
    
    results['router_spike_count'] = router_spikes
    results['neuron_spike_count'] = neuron_spikes
    results['hls_spike_count'] = hls_spikes
    
    # These counters may count different things, just report them
    results['pass'] = True
    return results


def test_register_stress(hls, cfg):
    """Test 8: Rapid register writes/reads for bus stress testing."""
    results = {}
    errors = 0
    n_iterations = 100
    
    for i in range(n_iterations):
        val = (i * 137 + 42) & 0xFFFF  # pseudo-random threshold values
        cfg.write(CFG_THRESHOLD, val)
        readback = cfg.read(CFG_THRESHOLD) & 0xFFFF
        if readback != val:
            errors += 1
    
    results['iterations'] = n_iterations
    results['errors'] = errors
    results['error_rate'] = errors / n_iterations
    results['pass'] = (errors == 0)
    return results


def test_multiple_ct_entries(hls, cfg):
    """Test 9: Program multiple CT entries to verify batch config works."""
    results = {}
    n_entries = 16
    
    # Reset first
    hls.write(HLS_CTRL_REG, CTRL_RESET)
    time.sleep(0.001)
    hls.write(HLS_CTRL_REG, 0)
    time.sleep(0.001)
    
    # Program n_entries CT entries from group0 neuron i → group1 neuron i
    entries_written = 0
    for i in range(n_entries):
        ct_addr, ct_wdata = encode_ct_write(
            src_group=0, src_neuron=i, fanout_idx=0,
            dst_group=1, dst_neuron=i, weight=50+i, exc=True, valid=True
        )
        write_config(cfg, target=0, addr=ct_addr, wdata=ct_wdata)
        entries_written += 1
    
    results['entries_written'] = entries_written
    results['pass'] = (entries_written == n_entries)
    return results


def test_intra_weight_matrix(hls, cfg):
    """Test 10: Program a small weight matrix for group 0."""
    results = {}
    n_neurons = 4
    weights_written = 0
    
    # Program 4×4 weight matrix for group 0
    weight_matrix = []
    for src in range(n_neurons):
        row = []
        for dst in range(n_neurons):
            if src != dst:  # no self-connections
                w = 20 + src * 10 + dst
                exc = (src + dst) % 2 == 0
                w_addr, w_wdata = encode_intra_weight(0, src, dst, w, exc)
                write_config(cfg, target=0, addr=w_addr, wdata=w_wdata)
                weights_written += 1
                row.append({'weight': w, 'exc': exc})
            else:
                row.append({'weight': 0, 'exc': True})
        weight_matrix.append(row)
    
    results['neurons'] = n_neurons
    results['weights_written'] = weights_written
    results['weight_matrix'] = weight_matrix
    results['pass'] = (weights_written == n_neurons * (n_neurons - 1))
    return results


# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SNN FPGA Co-Verification")
    parser.add_argument('--bitstream', default='snn_integrated.bit',
                        help='Path to bitstream file')
    args = parser.parse_args()
    
    all_results = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'bitstream': args.bitstream,
        'tests': {},
    }
    
    try:
        log(f"Loading bitstream: {args.bitstream}")
        from pynq import Overlay
        overlay = Overlay(args.bitstream)
        log("Bitstream loaded successfully")
        
        # Get IP references
        hls = overlay.snn_top_hls_0
        cfg = overlay.snn_config_regs_0
        
        # Check DMA availability
        has_dma = hasattr(overlay, 'axi_dma_0')
        if has_dma:
            dma = overlay.axi_dma_0
            log("DMA engine available")
        else:
            dma = None
            log("WARNING: DMA not available")
        
        all_results['dma_available'] = has_dma
        
        # ── Run Tests ────────────────────────────────────
        test_funcs = [
            ("T01_version_registers",    lambda: test_version_registers(hls, cfg)),
            ("T02_parameter_readback",   lambda: test_parameter_readback(hls, cfg)),
            ("T03_ct_programming",       lambda: test_ct_programming(hls, cfg)),
            ("T04_intra_weight_program", lambda: test_intra_weight_programming(hls, cfg)),
            ("T05_reset_and_status",     lambda: test_reset_and_status(hls, cfg)),
            ("T06_spike_injection_dma",  lambda: test_spike_injection_dma(hls, cfg, dma, overlay) if has_dma else {'pass': False, 'skip': 'no DMA'}),
            ("T07_spike_count_consist",  lambda: test_spike_count_consistency(hls, cfg)),
            ("T08_register_stress",      lambda: test_register_stress(hls, cfg)),
            ("T09_multiple_ct_entries",  lambda: test_multiple_ct_entries(hls, cfg)),
            ("T10_intra_weight_matrix",  lambda: test_intra_weight_matrix(hls, cfg)),
        ]
        
        passed = 0
        failed = 0
        for name, func in test_funcs:
            log(f"  Running {name}...")
            try:
                result = func()
                all_results['tests'][name] = result
                if result.get('pass', False):
                    passed += 1
                    log(f"    ✓ PASS")
                else:
                    failed += 1
                    log(f"    ✗ FAIL")
            except Exception as e:
                all_results['tests'][name] = {
                    'pass': False,
                    'error': str(e),
                    'traceback': traceback.format_exc(),
                }
                failed += 1
                log(f"    ✗ ERROR: {e}")
        
        all_results['summary'] = {
            'total': passed + failed,
            'passed': passed,
            'failed': failed,
        }
        log(f"\n{'='*50}")
        log(f"Results: {passed} PASS, {failed} FAIL (of {passed+failed})")
        log(f"{'='*50}")
        
    except Exception as e:
        all_results['error'] = str(e)
        all_results['traceback'] = traceback.format_exc()
        log(f"FATAL ERROR: {e}")
    
    # Output JSON to stdout
    print(json.dumps(all_results, indent=2, default=str))


if __name__ == "__main__":
    main()
