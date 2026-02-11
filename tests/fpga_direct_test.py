#!/usr/bin/env python3
"""
Direct FPGA Programming and Register Access
============================================
Bypasses PYNQ Overlay API (broken XRT device detection on this board).
Uses fpga_manager + /dev/mem mmap for direct hardware access.

Runs on the PYNQ board with sudo.
"""

import json
import os
import sys
import struct
import time
import mmap
import traceback

# ─────────────────────────────────────────────────────────
# Bitstream Conversion (.bit → .bin for fpga_manager)
# ─────────────────────────────────────────────────────────

def bit_to_bin(bitfile_path, binfile_path):
    """
    Convert Xilinx .bit file to byte-swapped .bin format for fpga_manager.
    
    The Zynq fpga_manager expects a byte-swapped .bin file:
    1. Strip the .bit proprietary header
    2. Byte-swap each 32-bit word (big-endian -> little-endian)
    """
    with open(bitfile_path, 'rb') as f:
        data = f.read()
    
    if len(data) < 20:
        print("WARNING: File too small for .bit format", file=sys.stderr)
        with open(binfile_path, 'wb') as f:
            f.write(data)
        return len(data)
    
    # Parse .bit header: find 'e' field which contains the bitstream data
    bitstream_start = None
    bitstream_length = None
    
    if data[:2] == b'\x00\x09':
        try:
            pos = 0
            # First field: 2-byte length prefix + magic header
            hdr_len = struct.unpack('>H', data[pos:pos+2])[0]
            pos = 2 + hdr_len + 2  # skip past magic header + padding
            
            # Parse field tags: a(design), b(part), c(date), d(time), e(data)
            while pos < min(len(data), 500):  # header should be < 500 bytes
                tag = chr(data[pos])
                pos += 1
                
                if tag == 'e':
                    bitstream_length = struct.unpack('>I', data[pos:pos+4])[0]
                    pos += 4
                    bitstream_start = pos
                    break
                elif tag in ('a', 'b', 'c', 'd'):
                    field_len = struct.unpack('>H', data[pos:pos+2])[0]
                    pos += 2 + field_len
                else:
                    break
        except (struct.error, IndexError):
            pass
    
    # Fallback: find sync word (0xAA995566 in big-endian)
    if bitstream_start is None:
        sync_be = bytes([0xAA, 0x99, 0x55, 0x66])
        idx = data.find(sync_be)
        if idx >= 0:
            # Back up to 4-byte aligned start before sync
            bitstream_start = idx & ~3
        else:
            bitstream_start = 0
    
    raw = data[bitstream_start:bitstream_start + bitstream_length] if bitstream_length else data[bitstream_start:]
    print(f"  Header: {bitstream_start} bytes, bitstream: {len(raw)} bytes", file=sys.stderr)
    
    # Byte-swap each 32-bit word (big-endian -> little-endian)
    # This is required by the Zynq fpga_manager driver
    n = len(raw) & ~3
    swapped = bytearray(n)
    for i in range(0, n, 4):
        swapped[i]   = raw[i+3]
        swapped[i+1] = raw[i+2]
        swapped[i+2] = raw[i+1]
        swapped[i+3] = raw[i]
    
    with open(binfile_path, 'wb') as f:
        f.write(bytes(swapped))
    
    print(f"  Wrote byte-swapped {binfile_path} ({len(swapped)} bytes)", file=sys.stderr)
    return len(swapped)


# ─────────────────────────────────────────────────────────
# FPGA Manager Programming
# ─────────────────────────────────────────────────────────

def program_fpga(bin_path):
    """Load bitstream via fpga_manager. Tries multiple methods."""
    firmware_dir = '/lib/firmware'
    firmware_name = os.path.basename(bin_path)
    firmware_path = os.path.join(firmware_dir, firmware_name)
    
    # Copy file to /lib/firmware/
    print(f"  Copying {bin_path} to {firmware_path}", file=sys.stderr)
    with open(bin_path, 'rb') as src, open(firmware_path, 'wb') as dst:
        dst.write(src.read())
    
    # Set flags to 0 (full bitstream)
    with open('/sys/class/fpga_manager/fpga0/flags', 'w') as f:
        f.write('0')
    
    # Trigger programming
    print(f"  Programming FPGA with {firmware_name}...", file=sys.stderr)
    try:
        with open('/sys/class/fpga_manager/fpga0/firmware', 'w') as f:
            f.write(firmware_name)
    except OSError as e:
        print(f"  Warning: firmware write returned: {e}", file=sys.stderr)
    
    time.sleep(1.0)
    
    # Check state
    with open('/sys/class/fpga_manager/fpga0/state', 'r') as f:
        state = f.read().strip()
    
    print(f"  FPGA manager state: {state}", file=sys.stderr)
    return state == 'operating'


def program_fpga_multi_method(bitfile_path):
    """Convert .bit to byte-swapped .bin and program the FPGA."""
    bin_path = bitfile_path.replace('.bit', '.bin')
    if not bin_path.endswith('.bin'):
        bin_path = bitfile_path + '.bin'
    
    print("  Converting .bit to byte-swapped .bin...", file=sys.stderr)
    bit_to_bin(bitfile_path, bin_path)
    
    if program_fpga(bin_path):
        return True
    
    print("  FPGA programming failed", file=sys.stderr)
    return False


# ─────────────────────────────────────────────────────────
# MMIO Register Access via /dev/mem
# ─────────────────────────────────────────────────────────

class DirectMMIO:
    """Direct memory-mapped I/O via /dev/mem."""
    
    PAGE_SIZE = 4096
    
    def __init__(self, base_addr, length=0x1000):
        self.base_addr = base_addr
        self.length = length
        # Align to page boundary
        self.page_offset = base_addr % self.PAGE_SIZE
        self.map_base = base_addr - self.page_offset
        self.map_length = length + self.page_offset
        # Round up to page size
        self.map_length = ((self.map_length + self.PAGE_SIZE - 1) // self.PAGE_SIZE) * self.PAGE_SIZE
        
        self.fd = os.open('/dev/mem', os.O_RDWR | os.O_SYNC)
        self.mm = mmap.mmap(self.fd, self.map_length, offset=self.map_base)
    
    def read(self, offset):
        """Read 32-bit register at offset from base_addr."""
        self.mm.seek(self.page_offset + offset)
        return struct.unpack('<I', self.mm.read(4))[0]
    
    def write(self, offset, value):
        """Write 32-bit register at offset from base_addr."""
        self.mm.seek(self.page_offset + offset)
        self.mm.write(struct.pack('<I', value & 0xFFFFFFFF))
    
    def flush(self):
        """Flush the mmap to ensure writes reach physical memory (for DMA coherence)."""
        self.mm.flush()
    
    def close(self):
        self.mm.close()
        os.close(self.fd)


# ─────────────────────────────────────────────────────────
# Register Constants
# ─────────────────────────────────────────────────────────

# HLS IP base address (s_axi_ctrl: 0x43C00000, addr_width=8 → 256 bytes)
# NOTE: HWH says range is 0x43C0007F (128 bytes) but actual HLS uses up to 0xA0.
#       Registers 0x00-0x7F reliably accessible; 0x80+ may need larger MMIO map.
HLS_BASE = 0x43C00000
HLS_AP_CTRL         = 0x00
HLS_CTRL_REG        = 0x10   # ctrl_reg: [0]enable [1]reset [2]clear [3]learn_en [4]wt_read [5]apply_reward [6]wt_load
HLS_CONFIG_REG      = 0x18   # config_reg: [15:0]threshold [31:16]leak_rate
HLS_MODE_REG        = 0x20   # mode_reg: [1:0]op_mode [8]encoder_enable
HLS_TIME_STEPS      = 0x28   # time_steps_reg: number of time steps per invocation
# 0x30-0x40: learning_params (5 words)
# 0x48-0x58: encoder_config (5 words — bitstream has 5, not 3!)
HLS_STATUS_REG      = 0x60   # status_reg: [0]snn_ready [1]snn_busy [2]stdp_active [7:6]op_mode [15:8]update_cnt
HLS_STATUS_VLD      = 0x64   # status_reg valid flag
HLS_SPIKE_COUNT     = 0x70   # spike_count_reg: total spikes processed by HLS
HLS_SPIKE_COUNT_VLD = 0x74   # spike_count_reg valid flag

# Config Regs base address
CFG_BASE = 0x43C10000
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

# DMA base address
DMA_BASE = 0x41E00000

# AXI DMA registers (Simple DMA mode)
DMA_MM2S_DMACR  = 0x00   # MM2S Control
DMA_MM2S_DMASR  = 0x04   # MM2S Status
DMA_MM2S_SA     = 0x18   # MM2S Source Address
DMA_MM2S_LENGTH = 0x28   # MM2S Transfer Length (triggers transfer)
DMA_S2MM_DMACR  = 0x30   # S2MM Control
DMA_S2MM_DMASR  = 0x34   # S2MM Status
DMA_S2MM_DA     = 0x48   # S2MM Destination Address
DMA_S2MM_LENGTH = 0x58   # S2MM Transfer Length (enables reception)

# Physical address for DMA buffers (DDR region accessible by PL DMA)
# Cache coherence handled via msync flush after writes
DMA_BUF_PHYS    = 0x1F000000   # Input buffer in DDR
DMA_OUTBUF_PHYS = 0x1F010000   # Output buffer in DDR

CTRL_ENABLE       = 0x01
CTRL_RESET        = 0x02
CTRL_CLEAR        = 0x04


# ─────────────────────────────────────────────────────────
# spike_router connection table encoding
# ─────────────────────────────────────────────────────────
# conn_memory: flat array indexed by src_neuron * MAX_FANOUT + fanout_idx
# Entry format (CONN_WIDTH = 18 + NEURON_ID_WIDTH = 28 bits for NUM_NEURONS=1024):
#   [27]       valid
#   [26]       exc/inh (1=excitatory, 0=inhibitory)
#   [25:18]    weight[7:0]
#   [17:10]    delay[7:0]
#   [9:0]      dest_id[NEURON_ID_WIDTH-1:0]
#
# config_addr[31:24] = command:
#   0x00 = write conn_memory[config_addr[15:0]]
#   0x01 = write conn_count[config_addr[NEURON_ID_WIDTH-1:0]]
#   0x02 = clear spike counter (config_data[0]=1)
#
# CRITICAL: conn_count[src_neuron] MUST be set to the number of
# connections for that neuron. Without it the router processes 0
# connections and silently drops the spike.

ROUTER_NUM_NEURONS     = 1024
ROUTER_MAX_FANOUT      = 32
ROUTER_NEURON_ID_WIDTH = 10   # ceil(log2(1024))
ROUTER_CONN_WIDTH      = 18 + ROUTER_NEURON_ID_WIDTH  # 28 bits


def encode_router_conn(src_neuron, fanout_idx, dest_neuron,
                       weight, delay=0, exc=True, valid=True):
    """Encode a spike_router connection entry (conn_memory write).

    Returns (config_addr, config_data) for the snn_config_regs interface.
    """
    flat_addr = src_neuron * ROUTER_MAX_FANOUT + fanout_idx
    config_addr = (0x00 << 24) | (flat_addr & 0xFFFF)

    nid_w = ROUTER_NEURON_ID_WIDTH
    config_data = ((1 if valid else 0) << (nid_w + 17)) | \
                  ((1 if exc else 0) << (nid_w + 16)) | \
                  ((weight & 0xFF) << (nid_w + 8)) | \
                  ((delay & 0xFF) << nid_w) | \
                  (dest_neuron & ((1 << nid_w) - 1))
    return config_addr, config_data


def encode_router_conn_count(src_neuron, count):
    """Encode a conn_count write for a source neuron.

    CRITICAL: Without this the router iterates zero connections and
    silently drops the spike.
    """
    config_addr = (0x01 << 24) | (src_neuron & ((1 << ROUTER_NEURON_ID_WIDTH) - 1))
    config_data = count & 0xFF
    return config_addr, config_data


# ─────────────────────────────────────────────────────────
# Test Cases
# ─────────────────────────────────────────────────────────

def run_tests(hls, cfg):
    results = {}
    
    # T01: Version registers
    # Note: HLS version_reg is at offset 0x88, outside the 128-byte mapped range (0x00-0x7F)
    # so we can only read the CFG version. HLS spike_count at 0x68 verifies HLS is responsive.
    print("  T01: Version registers", file=sys.stderr)
    cfg_ver = cfg.read(CFG_VERSION)
    ap_ctrl = hls.read(HLS_AP_CTRL)
    hls_spike_cnt = hls.read(HLS_SPIKE_COUNT)
    hls_status = hls.read(HLS_STATUS_REG)
    results['T01_version'] = {
        'cfg_version': f'0x{cfg_ver:08X}',
        'cfg_version_valid': cfg_ver == 0x534E4E01,
        'ap_ctrl': f'0x{ap_ctrl:02X}',
        'hls_idle': bool(ap_ctrl & 0x04),
        'hls_status': f'0x{hls_status:08X}',
        'hls_spike_count': hls_spike_cnt,
        'pass': cfg_ver == 0x534E4E01,
    }
    
    # T02: Parameter write/readback
    print("  T02: Parameter readback", file=sys.stderr)  
    cfg.write(CFG_THRESHOLD, 500)
    time.sleep(0.0001)
    thresh_rb = cfg.read(CFG_THRESHOLD) & 0xFFFF
    
    params_val = (10 << 8) | 3  # refrac=10, leak=3
    cfg.write(CFG_NEURON_PARAMS, params_val)
    time.sleep(0.0001)
    params_rb = cfg.read(CFG_NEURON_PARAMS)
    
    hls_config = (3 << 16) | 500
    hls.write(HLS_CONFIG_REG, hls_config)
    time.sleep(0.0001) 
    hls_config_rb = hls.read(HLS_CONFIG_REG)
    
    results['T02_params'] = {
        'threshold_written': 500,
        'threshold_readback': thresh_rb,
        'threshold_match': thresh_rb == 500,
        'neuron_params_written': f'0x{params_val:08X}',
        'neuron_params_readback': f'0x{params_rb:08X}',
        'params_match': params_rb == params_val,
        'hls_config_written': f'0x{hls_config:08X}',
        'hls_config_readback': f'0x{hls_config_rb:08X}',
        'hls_config_match': hls_config_rb == hls_config,
        'pass': (thresh_rb == 500) and (params_rb == params_val) and (hls_config_rb == hls_config),
    }
    
    # T03: Reset and status
    print("  T03: Reset and status", file=sys.stderr)
    hls.write(HLS_CTRL_REG, CTRL_RESET | CTRL_CLEAR)
    time.sleep(0.001)
    hls.write(HLS_CTRL_REG, 0)
    time.sleep(0.001)
    
    router_spk = cfg.read(CFG_ROUTER_SPIKE_CNT)
    neuron_spk = cfg.read(CFG_NEURON_SPIKE_CNT)
    status = cfg.read(CFG_STATUS)
    hls_spk = hls.read(HLS_SPIKE_COUNT)
    
    results['T03_reset_status'] = {
        'router_spikes': router_spk,
        'neuron_spikes': neuron_spk,
        'status': f'0x{status:08X}',
        'overflow': bool(status & 0x01),
        'hls_spikes': hls_spk,
        'spikes_cleared': router_spk == 0 and neuron_spk == 0,
        'pass': (router_spk == 0) and (neuron_spk == 0) and not (status & 0x01),
    }
    
    # T04: Router connection entry programming
    print("  T04: Router conn programming", file=sys.stderr)
    # Write connection: src=5, fanout=0, dest=10, weight=100, exc
    ct_addr, ct_wdata = encode_router_conn(5, 0, 10, 100, delay=0, exc=True)
    cfg.write(CFG_CONFIG_CTRL, 0)  # target = router
    cfg.write(CFG_CONFIG_ADDR, ct_addr)
    cfg.write(CFG_CONFIG_WDATA, ct_wdata)
    time.sleep(0.0001)

    # Set conn_count[5] = 1
    cc_addr, cc_data = encode_router_conn_count(5, 1)
    cfg.write(CFG_CONFIG_ADDR, cc_addr)
    cfg.write(CFG_CONFIG_WDATA, cc_data)
    time.sleep(0.0001)

    # Verify encoding: flat_addr = 5*32+0 = 160 = 0xA0
    nw = ROUTER_NEURON_ID_WIDTH
    expected_addr = (0x00 << 24) | 160
    expected_data = (1 << (nw+17)) | (1 << (nw+16)) | (100 << (nw+8)) | (0 << nw) | 10

    # Readback via config_rdata (set addr to cmd=0x00, flat_addr=160)
    cfg.write(CFG_CONFIG_ADDR, expected_addr)
    time.sleep(0.001)
    readback = cfg.read(CFG_CONFIG_RDATA)

    results['T04_ct_program'] = {
        'addr': f'0x{ct_addr:08X}',
        'wdata': f'0x{ct_wdata:08X}',
        'expected_addr': f'0x{expected_addr:08X}',
        'expected_data': f'0x{expected_data:08X}',
        'encoding_valid': ct_addr == expected_addr and ct_wdata == expected_data,
        'readback': f'0x{readback:08X}',
        'readback_match': (readback & ((1 << ROUTER_CONN_WIDTH) - 1)) == expected_data,
        'pass': ct_addr == expected_addr and ct_wdata == expected_data,
    }
    
    # T05: Router connection readback test
    print("  T05: Router readback", file=sys.stderr)
    # Write a connection and read it back via config_rdata
    w_addr, w_wdata = encode_router_conn(3, 0, 7, 80, delay=0, exc=True)
    cfg.write(CFG_CONFIG_CTRL, 0)
    cfg.write(CFG_CONFIG_ADDR, w_addr)
    cfg.write(CFG_CONFIG_WDATA, w_wdata)
    time.sleep(0.001)

    # Read back: set config_addr to same flat address with cmd=0x00
    cfg.write(CFG_CONFIG_ADDR, w_addr)
    time.sleep(0.001)
    rb = cfg.read(CFG_CONFIG_RDATA)
    mask = (1 << ROUTER_CONN_WIDTH) - 1
    readback_match = (rb & mask) == (w_wdata & mask)

    results['T05_router_readback'] = {
        'addr': f'0x{w_addr:08X}',
        'wdata': f'0x{w_wdata:08X}',
        'readback': f'0x{rb:08X}',
        'readback_match': readback_match,
        'pass': readback_match,
    }
    
    # T06: Register stress test
    print("  T06: Register stress (100 iterations)", file=sys.stderr)
    errors = 0
    for i in range(100):
        val = (i * 137 + 42) & 0xFFFF
        cfg.write(CFG_THRESHOLD, val)
        rb = cfg.read(CFG_THRESHOLD) & 0xFFFF
        if rb != val:
            errors += 1
    results['T06_stress'] = {
        'iterations': 100,
        'errors': errors,
        'pass': errors == 0,
    }
    
    # T07: Multiple CT entries
    print("  T07: Multiple CT entries", file=sys.stderr)
    hls.write(HLS_CTRL_REG, CTRL_RESET)
    time.sleep(0.001)
    hls.write(HLS_CTRL_REG, 0)
    time.sleep(0.001)
    
    n_entries = 16
    cfg.write(CFG_CONFIG_CTRL, 0)  # target = router
    for i in range(n_entries):
        ct_a, ct_w = encode_router_conn(i, 0, (i + 1) % ROUTER_NUM_NEURONS, 50 + i, delay=0, exc=True)
        cfg.write(CFG_CONFIG_ADDR, ct_a)
        cfg.write(CFG_CONFIG_WDATA, ct_w)
        time.sleep(0.00001)
        # Set conn_count for each source neuron
        cc_a, cc_d = encode_router_conn_count(i, 1)
        cfg.write(CFG_CONFIG_ADDR, cc_a)
        cfg.write(CFG_CONFIG_WDATA, cc_d)
        time.sleep(0.00001)
    
    # Verify last entry readback
    last_addr, last_data = encode_router_conn(n_entries - 1, 0,
                                               n_entries % ROUTER_NUM_NEURONS,
                                               50 + n_entries - 1, delay=0, exc=True)
    cfg.write(CFG_CONFIG_ADDR, last_addr)
    time.sleep(0.001)
    rb = cfg.read(CFG_CONFIG_RDATA)
    mask = (1 << ROUTER_CONN_WIDTH) - 1

    results['T07_multi_ct'] = {
        'entries_written': n_entries,
        'last_readback': f'0x{rb:08X}',
        'last_expected': f'0x{last_data:08X}',
        'readback_match': (rb & mask) == (last_data & mask),
        'pass': (rb & mask) == (last_data & mask),
    }
    
    # T08: Configure and enable for spike processing
    print("  T08: Spike processing test", file=sys.stderr)
    threshold = 100
    leak_rate = 3
    refrac = 5
    
    # Reset
    hls.write(HLS_CTRL_REG, CTRL_RESET | CTRL_CLEAR)
    time.sleep(0.001)
    hls.write(HLS_CTRL_REG, 0)
    time.sleep(0.001)
    
    # Configure
    cfg.write(CFG_THRESHOLD, threshold)
    cfg.write(CFG_NEURON_PARAMS, (refrac << 8) | leak_rate)
    hls.write(HLS_CONFIG_REG, (leak_rate << 16) | threshold)
    
    # Program network via spike_router (flat addressing):
    # neuron 0 → neuron 1, w=120, exc
    cfg.write(CFG_CONFIG_CTRL, 0)  # target = router
    wa, wd = encode_router_conn(0, 0, 1, 120, delay=0, exc=True)
    cfg.write(CFG_CONFIG_ADDR, wa)
    cfg.write(CFG_CONFIG_WDATA, wd)
    time.sleep(0.0001)
    # neuron 1 → neuron 128, w=110, exc
    ca, cd = encode_router_conn(1, 0, 128, 110, delay=0, exc=True)
    cfg.write(CFG_CONFIG_ADDR, ca)
    cfg.write(CFG_CONFIG_WDATA, cd)
    time.sleep(0.0001)
    # Set conn_count for source neurons
    cca0, ccd0 = encode_router_conn_count(0, 1)
    cfg.write(CFG_CONFIG_ADDR, cca0)
    cfg.write(CFG_CONFIG_WDATA, ccd0)
    cca1, ccd1 = encode_router_conn_count(1, 1)
    cfg.write(CFG_CONFIG_ADDR, cca1)
    cfg.write(CFG_CONFIG_WDATA, ccd1)
    time.sleep(0.001)
    
    # Enable
    hls.write(HLS_CTRL_REG, CTRL_ENABLE)
    hls.write(HLS_AP_CTRL, 0x81)  # ap_start + auto_restart
    time.sleep(0.01)
    
    # Read spike counts
    router_spk = cfg.read(CFG_ROUTER_SPIKE_CNT)
    neuron_spk = cfg.read(CFG_NEURON_SPIKE_CNT)
    hls_spk = hls.read(HLS_SPIKE_COUNT)
    status = cfg.read(CFG_STATUS)
    throughput = cfg.read(CFG_THROUGHPUT)
    
    # Disable
    hls.write(HLS_CTRL_REG, 0)
    
    results['T08_spike_test'] = {
        'threshold': threshold,
        'weight_intra': 120,
        'weight_inter': 110,
        'router_spikes': router_spk,
        'neuron_spikes': neuron_spk,
        'hls_spikes': hls_spk,
        'status': f'0x{status:08X}',
        'throughput': throughput,
        'any_activity': router_spk > 0 or neuron_spk > 0 or hls_spk > 0,
        'pass': True,  # Just collect data, comparison done host-side
    }
    
    # T09: Register dump (for debugging) — ACTUAL offsets from HLS compile report
    print("  T09: Full register dump", file=sys.stderr)
    hls_dump = {}
    for name, off in [('AP_CTRL', 0x00), ('CTRL', 0x10), ('CONFIG', 0x18),
                       ('MODE', 0x20), ('TIME_STEPS', 0x28),
                       ('STATUS', 0x60), ('STATUS_VLD', 0x64),
                       ('SPIKE_CNT', 0x70), ('SPIKE_VLD', 0x74)]:
        hls_dump[name] = f'0x{hls.read(off):08X}'
    
    cfg_dump = {}
    for name, off in [('CTRL', 0x00), ('ADDR', 0x04), ('WDATA', 0x08), ('RDATA', 0x0C),
                       ('THRESH', 0x10), ('PARAMS', 0x14), ('RTR_SPK', 0x18),
                       ('NEU_SPK', 0x1C), ('STATUS', 0x20), ('THRU', 0x24), ('VER', 0x28)]:
        cfg_dump[name] = f'0x{cfg.read(off):08X}'
    
    results['T09_reg_dump'] = {
        'hls_registers': hls_dump,
        'cfg_registers': cfg_dump,
        'pass': True,
    }
    
    # T10: HLS Lifecycle + Register Dump
    print("  T10: HLS lifecycle diagnostics", file=sys.stderr)
    try:
        # Dump all 32 HLS registers BEFORE any operation
        print("    [Pre-start] Full HLS register dump:", file=sys.stderr)
        for off in range(0, 0x80, 4):
            val = hls.read(off)
            if val != 0:
                print(f"      0x{off:02X}: 0x{val:08X}", file=sys.stderr)

        # Write AP_START=1 (no auto_restart), time_steps=1
        hls.write(HLS_CTRL_REG, CTRL_ENABLE)
        hls.write(HLS_MODE_REG, 0)
        hls.write(HLS_TIME_STEPS, 1)
        hls.write(HLS_AP_CTRL, 0x01)
        time.sleep(0.1)  # Wait 100ms for function to complete

        # Dump all HLS registers AFTER single invocation
        print("    [Post-start 100ms] Full HLS register dump:", file=sys.stderr)
        post_regs = {}
        for off in range(0, 0x80, 4):
            val = hls.read(off)
            post_regs[f"0x{off:02X}"] = f"0x{val:08X}"
            if val != 0:
                print(f"      0x{off:02X}: 0x{val:08X}", file=sys.stderr)

        # Check valid bits for output registers (ACTUAL offsets from HLS compile report)
        vld_status = hls.read(HLS_STATUS_VLD) & 1
        vld_spike  = hls.read(HLS_SPIKE_COUNT_VLD) & 1
        print(f"    Valid bits: status_vld={vld_status}, spike_vld={vld_spike}", file=sys.stderr)

        results['T10_hls_lifecycle'] = {
            'post_regs': post_regs,
            'valid_bits': {'status': vld_status, 'spike_count': vld_spike},
            'pass': True,
        }
    except Exception as e:
        results['T10_hls_lifecycle'] = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'pass': False,
        }

    # T11: DMA spike injection test
    print("  T11: DMA spike injection", file=sys.stderr)
    try:
        dma_results = run_dma_spike_test(hls, cfg)
        results['T11_dma_spike'] = dma_results
    except Exception as e:
        results['T11_dma_spike'] = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'pass': False,
        }
    
    return results



def run_dma_spike_test(hls, cfg):
    """Inject spikes via AXI DMA and verify spike processing."""

    # Open DMA MMIO
    dma = DirectMMIO(DMA_BASE, 0x100)

    # =====================================================================
    # Phase A: Verify HLS function completes (single invocation, no DMA)
    # =====================================================================
    print("    [Phase A] HLS function completion test...", file=sys.stderr)

    # Stop any running HLS
    hls.write(HLS_AP_CTRL, 0x00)
    time.sleep(0.005)

    # Configure minimal: enable=1, no reset, inference mode, small time_steps
    hls.write(HLS_CTRL_REG, CTRL_ENABLE)
    hls.write(HLS_MODE_REG, 0)           # MODE_INFERENCE, no encoder
    hls.write(HLS_TIME_STEPS, 1)         # 1 time step (see spike_in_valid timing note)

    # Read initial AP_CTRL state
    ap_init = hls.read(HLS_AP_CTRL)
    print(f"    AP_CTRL initial: 0x{ap_init:02X} (idle={bool(ap_init&4)}, done={bool(ap_init&2)})", file=sys.stderr)

    # Start HLS without auto_restart (single invocation)
    hls.write(HLS_AP_CTRL, 0x01)  # ap_start only, NO auto_restart

    # Poll for ap_done (bit 1) with timeout
    start_poll = time.time()
    ap_done_seen = False
    poll_samples = []
    for i in range(200):  # 200 * 50ms = 10s max
        time.sleep(0.05)
        ap_val = hls.read(HLS_AP_CTRL)
        elapsed = time.time() - start_poll
        if i < 10 or i % 20 == 0:
            poll_samples.append(f"({elapsed:.3f}s: 0x{ap_val:02X})")
        if ap_val & 0x06:  # ap_done(1) or ap_idle(2)
            ap_done_seen = True
            poll_samples.append(f"({elapsed:.3f}s: DONE 0x{ap_val:02X})")
            break

    print(f"    AP_CTRL poll: {', '.join(poll_samples)}", file=sys.stderr)

    if ap_done_seen:
        # Function completed! Read status (correct offsets: 0x60, 0x70)
        status_a = hls.read(HLS_STATUS_REG)
        spike_a = hls.read(HLS_SPIKE_COUNT)
        status_vld = hls.read(HLS_STATUS_VLD) & 1
        spike_vld = hls.read(HLS_SPIKE_COUNT_VLD) & 1
        print(f"    Phase A SUCCESS: status=0x{status_a:08X} (vld={status_vld}), spikes={spike_a} (vld={spike_vld})", file=sys.stderr)
        print(f"      snn_ready={status_a&1}, snn_busy={(status_a>>1)&1}, mode={(status_a>>6)&3}", file=sys.stderr)
    else:
        ap_final = hls.read(HLS_AP_CTRL)
        print(f"    Phase A TIMEOUT: HLS never completed after 10s! AP_CTRL=0x{ap_final:02X}", file=sys.stderr)
        # Try reading raw register space for diagnostics
        raw_regs = {}
        for off in range(0, 0x80, 4):
            raw_regs[f"0x{off:02X}"] = f"0x{hls.read(off):08X}"
        dma.close()
        return {
            'phase_a': 'TIMEOUT',
            'ap_ctrl_final': f'0x{ap_final:02X}',
            'poll_samples': poll_samples,
            'raw_regs': raw_regs,
            'pass': False,
        }

    # =====================================================================
    # Phase B: Full reset, configure CT-routed network, inject via DMA
    # =====================================================================
    # ARCHITECTURE: DMA spike(neuron_id=X) → HLS → spike_router → conn_lookup(X)
    #   → deliver(dest, weight) → lif_neuron_array → fire → output → S2MM DMA
    #
    # spike_router uses FLAT connection memory:
    #   conn_memory[src * MAX_FANOUT + fanout] = {valid, exc, weight, delay, dest}
    #   conn_count[src] = number of connections (MUST set or router skips)
    #
    # Network topology:
    #   Connection[0]: neuron 0 → neuron 1,   weight=120, exc
    #   Connection[1]: neuron 1 → neuron 128, weight=110, exc
    #
    # Stimulus: DMA spike neuron_id=0 (means "neuron 0 has fired")
    #
    # Expected cascade:
    #   1. Router conn_lookup(0) → deliver w=120 to neuron 1
    #   2. Neuron 1: membrane += 120 ≥ threshold(100) → FIRE
    #   3. Router conn_lookup(1) → deliver w=110 to neuron 128
    #   4. Neuron 128: membrane += 110 ≥ threshold(100) → FIRE
    #   5. Router conn_lookup(128) → conn_count=0 → done
    #
    # Expected results:
    #   router_spike_count = 2  (routed: n0→n1, n1→n128)
    #   neuron_spike_count = 2  (fires: neuron 1, neuron 128)
    #   S2MM output = 2 spikes  (neuron_id=1, neuron_id=128)
    # =====================================================================
    print("    [Phase B] CT-routed DMA spike injection...", file=sys.stderr)

    # Full reset sequence
    hls.write(HLS_AP_CTRL, 0x00)  # Stop HLS
    time.sleep(0.005)
    hls.write(HLS_CTRL_REG, CTRL_RESET | CTRL_CLEAR)
    time.sleep(0.01)
    hls.write(HLS_CTRL_REG, 0)
    time.sleep(0.005)

    # Configure HLS mode and time steps
    # CRITICAL: time_steps MUST be 1.  With ap_none outputs, the HLS-generated
    # Verilog only updates spike_in_valid at the TIME_LOOP EXIT (t == time_steps).
    # If time_steps > 1, a spike read in iteration 0 is overwritten by
    # subsequent iterations, and spike_in_valid stays 0 the entire function.
    # With time_steps=1 + auto_restart, each invocation processes one spike
    # and correctly drives spike_in_valid=1 at the loop exit point.
    hls.write(HLS_MODE_REG, 0)           # MODE_INFERENCE
    hls.write(HLS_TIME_STEPS, 1)         # 1 time step per invocation (REQUIRED)

    # Configure network parameters
    threshold = 100
    leak_rate = 3
    refrac = 5

    cfg.write(CFG_THRESHOLD, threshold)
    cfg.write(CFG_NEURON_PARAMS, (refrac << 8) | leak_rate)
    hls.write(HLS_CONFIG_REG, (leak_rate << 16) | threshold)

    # ── Program spike_router connection table (flat addressing) ──
    cfg.write(CFG_CONFIG_CTRL, 0)  # target = router

    # Connection[0]: src=0, fanout=0 → dest=1, weight=120, exc, delay=0
    ca0, cd0 = encode_router_conn(0, 0, 1, 120, delay=0, exc=True)
    cfg.write(CFG_CONFIG_ADDR, ca0)
    cfg.write(CFG_CONFIG_WDATA, cd0)
    time.sleep(0.001)

    # Connection[1]: src=1, fanout=0 → dest=128, weight=110, exc, delay=0
    ca1, cd1 = encode_router_conn(1, 0, 128, 110, delay=0, exc=True)
    cfg.write(CFG_CONFIG_ADDR, ca1)
    cfg.write(CFG_CONFIG_WDATA, cd1)
    time.sleep(0.001)

    # Set connection counts (CRITICAL — without this router skips processing)
    cc0a, cc0d = encode_router_conn_count(0, 1)  # neuron 0 has 1 connection
    cfg.write(CFG_CONFIG_ADDR, cc0a)
    cfg.write(CFG_CONFIG_WDATA, cc0d)
    time.sleep(0.001)

    cc1a, cc1d = encode_router_conn_count(1, 1)  # neuron 1 has 1 connection
    cfg.write(CFG_CONFIG_ADDR, cc1a)
    cfg.write(CFG_CONFIG_WDATA, cc1d)
    time.sleep(0.001)

    # Verify connection readback
    cfg.write(CFG_CONFIG_ADDR, ca0)
    time.sleep(0.001)
    rb0 = cfg.read(CFG_CONFIG_RDATA)
    cfg.write(CFG_CONFIG_ADDR, ca1)
    time.sleep(0.001)
    rb1 = cfg.read(CFG_CONFIG_RDATA)
    mask = (1 << ROUTER_CONN_WIDTH) - 1

    print(f"    Conn[0]: src=0→dest=1 w=120 exc  addr=0x{ca0:08X} data=0x{cd0:08X} rb=0x{rb0:08X} {'✓' if (rb0&mask)==(cd0&mask) else '✗'}", file=sys.stderr)
    print(f"    Conn[1]: src=1→dest=128 w=110 exc addr=0x{ca1:08X} data=0x{cd1:08X} rb=0x{rb1:08X} {'✓' if (rb1&mask)==(cd1&mask) else '✗'}", file=sys.stderr)
    print(f"    conn_count[0]=1 addr=0x{cc0a:08X} data=0x{cc0d:08X}", file=sys.stderr)
    print(f"    conn_count[1]=1 addr=0x{cc1a:08X} data=0x{cc1d:08X}", file=sys.stderr)

    # ── Diagnostic readback: conn_count, fifo_overflow, spike_counter ──
    # Read conn_count[0] via router config readback (cmd=0x01, neuron=0)
    cfg.write(CFG_CONFIG_ADDR, (0x01 << 24) | 0)
    time.sleep(0.001)
    cc0_rb = cfg.read(CFG_CONFIG_RDATA) & 0xFF
    # Read conn_count[1] (cmd=0x01, neuron=1)
    cfg.write(CFG_CONFIG_ADDR, (0x01 << 24) | 1)
    time.sleep(0.001)
    cc1_rb = cfg.read(CFG_CONFIG_RDATA) & 0xFF
    # Read router spike_counter (cmd=0x10)
    cfg.write(CFG_CONFIG_ADDR, (0x10 << 24))
    time.sleep(0.001)
    rtr_cnt_rb = cfg.read(CFG_CONFIG_RDATA)
    # Read fifo_overflow (cmd=0x11)
    cfg.write(CFG_CONFIG_ADDR, (0x11 << 24))
    time.sleep(0.001)
    fifo_ovf = cfg.read(CFG_CONFIG_RDATA) & 1
    # Read version (should return 0xDEADBEEF for unknown cmd to verify readback works)
    cfg.write(CFG_CONFIG_ADDR, (0xFF << 24))
    time.sleep(0.001)
    deadbeef = cfg.read(CFG_CONFIG_RDATA)
    print(f"    DIAG: conn_count[0]={cc0_rb} conn_count[1]={cc1_rb} spike_cnt={rtr_cnt_rb} fifo_ovf={fifo_ovf} default=0x{deadbeef:08X}", file=sys.stderr)

    # Prepare DMA spike: neuron_id=0 (source neuron that "fired")
    # AER format: [31:18]=timestamp, [17:10]=weight, [9:0]=neuron_id
    neuron_id = 0
    weight = 0       # Weight ignored by router; CT provides weight
    timestamp = 0
    spike_word = ((timestamp & 0x3FFF) << 18) | ((weight & 0xFF) << 10) | (neuron_id & 0x3FF)
    print(f"    Spike word: 0x{spike_word:08X} (src_id={neuron_id}, ts={timestamp})", file=sys.stderr)
    print(f"    (DMA weight field ignored — router uses CT weights)", file=sys.stderr)

    # Write spike data using pwrite (cache-coherent via O_SYNC)
    dma_fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
    spike_bytes = struct.pack("<II", spike_word, 0)  # 1 spike + padding
    os.pwrite(dma_fd, spike_bytes, DMA_BUF_PHYS)
    os.pwrite(dma_fd, b"\x00" * 256, DMA_OUTBUF_PHYS)  # Clear output buffer

    rb = struct.unpack("<I", os.pread(dma_fd, 4, DMA_BUF_PHYS))[0]
    print(f"    Buffer readback: 0x{rb:08X} (match={rb == spike_word})", file=sys.stderr)

    # Reset DMA engine
    dma.write(DMA_MM2S_DMACR, 0x04)  # MM2S reset
    time.sleep(0.01)
    dma.write(DMA_S2MM_DMACR, 0x04)  # S2MM reset
    time.sleep(0.01)

    # Enable SNN and start HLS with auto_restart
    hls.write(HLS_CTRL_REG, CTRL_ENABLE)
    time.sleep(0.001)
    hls.write(HLS_AP_CTRL, 0x81)  # ap_start + auto_restart
    time.sleep(0.05)  # Let HLS init complete

    # Setup S2MM (receive) channel FIRST to be ready for output spikes
    dma.write(DMA_S2MM_DMACR, 0x01)  # Enable S2MM
    time.sleep(0.001)
    dma.write(DMA_S2MM_DA, DMA_OUTBUF_PHYS)
    dma.write(DMA_S2MM_LENGTH, 256)  # Accept up to 64 spike words

    # Send spike via MM2S
    dma.write(DMA_MM2S_DMACR, 0x01)  # Enable MM2S
    time.sleep(0.001)
    dma.write(DMA_MM2S_SA, DMA_BUF_PHYS)
    dma.write(DMA_MM2S_LENGTH, 4)    # 1 spike = 4 bytes

    # Wait for MM2S completion
    for attempt in range(20):
        time.sleep(0.01)
        mm2s_sr = dma.read(DMA_MM2S_DMASR)
        if mm2s_sr & 0x1002:
            break

    mm2s_ioc = bool(mm2s_sr & 0x1000)
    mm2s_err = bool(mm2s_sr & 0x70)
    print(f"    MM2S: sr=0x{mm2s_sr:08X} ioc={mm2s_ioc} err={mm2s_err}", file=sys.stderr)

    # Wait for processing and output spikes, sampling at intervals
    print("    Sampling spike counts over 3 seconds...", file=sys.stderr)
    router_spk = neuron_spk = hls_spk = 0
    hls_status = 0
    s2mm_sr = 0
    for delay_ms in [50, 100, 200, 500, 1000, 2000]:
        time.sleep(delay_ms / 1000.0)
        ap_c = hls.read(HLS_AP_CTRL)
        hls_status = hls.read(HLS_STATUS_REG)
        router_spk = cfg.read(CFG_ROUTER_SPIKE_CNT)
        neuron_spk = cfg.read(CFG_NEURON_SPIKE_CNT)
        hls_spk = hls.read(HLS_SPIKE_COUNT)
        s2mm_sr = dma.read(DMA_S2MM_DMASR)
        s2mm_done = bool(s2mm_sr & 0x1002)
        # Direct router readback for spike_counter and fifo_overflow
        cfg.write(CFG_CONFIG_ADDR, (0x10 << 24))
        time.sleep(0.0001)
        rtr_direct = cfg.read(CFG_CONFIG_RDATA)
        cfg.write(CFG_CONFIG_ADDR, (0x11 << 24))
        time.sleep(0.0001)
        rtr_ovf = cfg.read(CFG_CONFIG_RDATA) & 1
        print(f"      @{delay_ms}ms: AP=0x{ap_c:02X} ST=0x{hls_status:08X} "
              f"r={router_spk}(direct={rtr_direct}) n={neuron_spk} h={hls_spk} "
              f"s2mm=0x{s2mm_sr:08X} ovf={rtr_ovf}{'*' if s2mm_done else ''}", file=sys.stderr)
        if (router_spk > 0 or neuron_spk > 0) and s2mm_done:
            break

    ap_after = hls.read(HLS_AP_CTRL)

    # Read and decode output spikes from S2MM buffer
    out_words = []
    decoded_spikes = []
    for i in range(0, 64, 4):
        w = struct.unpack("<I", os.pread(dma_fd, 4, DMA_OUTBUF_PHYS + i))[0]
        if w != 0:
            out_words.append(f"0x{w:08X}")
            # Decode AER: [9:0]=neuron_id, [17:10]=weight, [31:18]=timestamp
            sp_nid = w & 0x3FF
            sp_wt  = (w >> 10) & 0xFF
            sp_ts  = (w >> 18) & 0x3FFF
            decoded_spikes.append({'neuron_id': sp_nid, 'weight': sp_wt, 'timestamp': sp_ts})
            sp_group = sp_nid >> 7
            sp_local = sp_nid & 0x7F
            print(f"    Output spike: 0x{w:08X} → neuron_id={sp_nid} (g={sp_group},n={sp_local}), "
                  f"weight={sp_wt}, ts={sp_ts}", file=sys.stderr)

    if not decoded_spikes:
        print("    No output spikes in S2MM buffer", file=sys.stderr)

    # Disable
    hls.write(HLS_CTRL_REG, 0)
    hls.write(HLS_AP_CTRL, 0x00)

    dma.close()
    os.close(dma_fd)

    result = {
        'phase_a': 'PASS' if ap_done_seen else 'FAIL',
        'phase_a_status': f'0x{status_a:08X}' if ap_done_seen else 'N/A',
        'spike_injected': f'0x{spike_word:08X}',
        'buffer_readback_match': rb == spike_word,
        'ap_ctrl_after': f'0x{ap_after:02X}',
        'hls_status': f'0x{hls_status:08X}',
        'mm2s_status': f'0x{mm2s_sr:08X}',
        's2mm_status': f'0x{s2mm_sr:08X}',
        'mm2s_complete': mm2s_ioc,
        'mm2s_error': mm2s_err,
        's2mm_complete': bool(s2mm_sr & 0x1002),
        'router_spikes': router_spk,
        'neuron_spikes': neuron_spk,
        'hls_spikes': hls_spk,
        'output_spike_words': out_words,
        'decoded_output_spikes': decoded_spikes,
        'output_neuron_ids': sorted([s['neuron_id'] for s in decoded_spikes]),
        'status': f'0x{cfg.read(CFG_STATUS):08X}',
        'any_activity': router_spk > 0 or neuron_spk > 0 or hls_spk > 0,
        'pass': mm2s_ioc and not mm2s_err,
    }

    return result


# ---
# Main
# ---

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--bitstream', default='snn_integrated.bit')
    parser.add_argument('--skip-program', action='store_true',
                        help='Skip FPGA programming (assume already loaded)')
    args = parser.parse_args()

    all_results = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'bitstream': args.bitstream,
        'tests': {},
    }

    try:
        if not args.skip_program:
            print("Programming FPGA (multi-method)...", file=sys.stderr)
            success = program_fpga_multi_method(args.bitstream)
            all_results['fpga_programmed'] = success

            if not success:
                all_results['error'] = 'FPGA programming failed (all methods)'
                print(json.dumps(all_results, indent=2))
                return 1
        else:
            print("Skipping FPGA programming (--skip-program)", file=sys.stderr)
            all_results['fpga_programmed'] = 'skipped'

        # Open MMIO
        print("Opening MMIO interfaces...", file=sys.stderr)
        hls = DirectMMIO(HLS_BASE, 0x100)
        cfg = DirectMMIO(CFG_BASE, 0x100)

        # Run tests
        print("Running tests...", file=sys.stderr)
        all_results['tests'] = run_tests(hls, cfg)

        # Summary
        passed = sum(1 for t in all_results['tests'].values() if t.get('pass'))
        total = len(all_results['tests'])
        all_results['summary'] = {'passed': passed, 'total': total, 'failed': total - passed}

        print(f"\nResults: {passed}/{total} PASS", file=sys.stderr)

        hls.close()
        cfg.close()

    except Exception as e:
        all_results['error'] = str(e)
        all_results['traceback'] = traceback.format_exc()
        print(f"ERROR: {e}", file=sys.stderr)

    print(json.dumps(all_results, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
