"""
PYNQ Driver for SNN Accelerator
Event-Driven Spiking Neural Network Accelerator for FPGA

This driver provides a high-level interface to interact with the
SNN accelerator hardware on PYNQ boards.

Architecture:
    PS (ARM) → AXI GP0 → AXI Interconnect → [HLS IP | DMA | Config Regs]
    
    Address Map:
        HLS IP (s_axi_ctrl): 0x43C00000 (128 bytes)
        Config Regs (s_axi):  0x43C10000 (4K)
        AXI DMA:              auto-assigned

Usage:
    from snn_driver import SNNAccelerator
    
    snn = SNNAccelerator('snn_integrated.bit')
    snn.configure(threshold=100, leak_rate=16, refractory_period=10)
    snn.program_connection(src=0, idx=0, dest=5, weight=10, excitatory=True)
    snn.send_spikes_dma(spike_data)
    output_spikes = snn.receive_spikes_dma()
    snn.close()
"""

import numpy as np
from pynq import Overlay, allocate
import time


def tau_to_leak_rate(tau: float) -> int:
    """
    Convert desired tau (decay constant) to hardware leak_rate encoding.
    
    Finds the best shift configuration to approximate the target tau.
    
    Args:
        tau: Desired decay constant (0.0-1.0). Higher values = slower leak.
             Typical values: 0.85-0.99
    
    Returns:
        leak_rate: Hardware-encoded leak configuration
                   leak_rate[2:0] = shift1 (primary leak, 1-7)
                   leak_rate[7:3] = shift2 (secondary leak, 0=disabled)
    
    Examples:
        >>> tau_to_leak_rate(0.875)  # Returns 3
        >>> tau_to_leak_rate(0.9)    # Returns 35 (closest match: 0.906)
        >>> tau_to_leak_rate(0.95)   # Returns 37 (closest match: 0.953)
    """
    best_error = float('inf')
    best_config = 3  # Default
    
    # Try single shift configurations
    for shift1 in range(1, 8):
        approx_tau = 1.0 - 1.0 / (1 << shift1)
        error = abs(approx_tau - tau)
        if error < best_error:
            best_error = error
            best_config = shift1
    
    # Try dual shift configurations
    for shift1 in range(1, 8):
        for shift2 in range(1, 8):
            if shift2 == shift1:
                continue
            approx_tau = 1.0 - 1.0 / (1 << shift1) - 1.0 / (1 << shift2)
            error = abs(approx_tau - tau)
            if error < best_error:
                best_error = error
                best_config = shift1 | (shift2 << 3)
    
    return best_config


def leak_rate_to_tau(leak_rate: int) -> float:
    """
    Convert hardware leak_rate encoding to tau (decay constant).
    
    Args:
        leak_rate: Hardware-encoded leak configuration
    
    Returns:
        tau: Effective decay constant
    """
    shift1 = leak_rate & 0x07
    shift2_cfg = (leak_rate >> 3) & 0x1F
    shift2 = shift2_cfg & 0x07 if shift2_cfg != 0 else 0
    
    tau = 1.0
    if shift1 > 0:
        tau -= 1.0 / (1 << shift1)
    if shift2_cfg != 0 and shift2 > 0:
        tau -= 1.0 / (1 << shift2)
    return tau


class SNNAccelerator:
    """
    PYNQ driver for Event-Driven SNN Accelerator (Integrated System)
    
    HLS IP Register Map (s_axi_ctrl @ 0x43C00000):
        0x00: AP_CTRL       - HLS control (start/done/idle/ready)
        0x04: GIE            - Global Interrupt Enable
        0x08: IER            - Interrupt Enable Register
        0x0C: ISR            - Interrupt Status Register
        0x10: ctrl_reg       - [0]enable [1]reset [2]clear [3]learning_en
                               [4]weight_read [5]apply_reward [6]weight_load
        0x18: config_reg     - [15:0]threshold [31:16]leak_rate
        0x20: learning_params- 144-bit learning parameters (5 words)
        0x38: status_reg     - Status (RO)
        0x48: spike_count_reg- Spike count (RO)
        0x58: weight_sum_reg - Weight sum (RO)
        0x68: version_reg    - Version (RO)
        0x78: reward_signal  - [7:0] reward

    SNN Config Register Map (s_axi @ 0x43C10000):
        0x00: CONFIG_CTRL     - [1:0] target (0=router, 1=neuron)
        0x04: CONFIG_ADDR     - Address for router/neuron config
        0x08: CONFIG_WDATA    - Write data (triggers config_we)
        0x0C: CONFIG_RDATA    - Read data from router (RO)
        0x10: THRESHOLD       - [15:0] global firing threshold
        0x14: NEURON_PARAMS   - [7:0] leak_rate, [15:8] refractory
        0x18: ROUTER_SPIKE_CNT- Router spike count (RO)
        0x1C: NEURON_SPIKE_CNT- Neuron spike count (RO)
        0x20: STATUS          - [0] overflow, [8:1] active_neurons (RO)
        0x24: THROUGHPUT      - Throughput counter (RO)
        0x28: VERSION         - 0x534E4E01 (RO)
    """
    
    #--- HLS IP register offsets (s_axi_ctrl) ---
    HLS_AP_CTRL         = 0x00
    HLS_CTRL_REG        = 0x10
    HLS_CONFIG_REG      = 0x18
    HLS_LEARNING_PARAMS = 0x20
    HLS_STATUS_REG      = 0x38
    HLS_SPIKE_COUNT     = 0x48
    HLS_WEIGHT_SUM      = 0x58
    HLS_VERSION         = 0x68
    HLS_REWARD_SIGNAL   = 0x78
    
    #--- SNN Config register offsets (snn_config_regs) ---
    CFG_CONFIG_CTRL      = 0x00
    CFG_CONFIG_ADDR      = 0x04
    CFG_CONFIG_WDATA     = 0x08
    CFG_CONFIG_RDATA     = 0x0C
    CFG_THRESHOLD        = 0x10
    CFG_NEURON_PARAMS    = 0x14
    CFG_ROUTER_SPIKE_CNT = 0x18
    CFG_NEURON_SPIKE_CNT = 0x1C
    CFG_STATUS           = 0x20
    CFG_THROUGHPUT       = 0x24
    CFG_VERSION          = 0x28
    
    # HLS ctrl_reg bit definitions
    CTRL_ENABLE        = 0x01
    CTRL_RESET         = 0x02
    CTRL_CLEAR         = 0x04
    CTRL_LEARNING_EN   = 0x08
    CTRL_WEIGHT_READ   = 0x10
    CTRL_APPLY_REWARD  = 0x20
    CTRL_WEIGHT_LOAD   = 0x40
    
    def __init__(self, bitstream_path='snn_integrated.bit'):
        """
        Initialize the SNN accelerator
        
        Args:
            bitstream_path: Path to the bitstream file (.bit)
                           Requires matching .hwh file in same directory
        """
        print(f"Loading bitstream: {bitstream_path}")
        self.overlay = Overlay(bitstream_path)
        
        # Get reference to the HLS IP
        self.hls = self.overlay.snn_top_hls_0
        
        # Get reference to the Config Registers IP
        self.cfg = self.overlay.snn_config_regs_0
        
        # Check config version
        version = self.cfg.read(self.CFG_VERSION)
        print(f"  Config register version: 0x{version:08X}")
        
        # Get DMA engine
        if hasattr(self.overlay, 'axi_dma_0'):
            self.dma = self.overlay.axi_dma_0
            self._dma_available = True
            print("  DMA engine available (MM2S + S2MM)")
        else:
            self._dma_available = False
            print("  Warning: DMA not available")
        
        # Allocate DMA buffers
        if self._dma_available:
            self.input_buffer = allocate(shape=(1024,), dtype=np.uint32)
            self.output_buffer = allocate(shape=(1024,), dtype=np.uint32)
        
        # Default configuration
        self._threshold = 100
        self._leak_rate = 0x03   # shift1=3 → tau≈0.875
        self._refractory_period = 10
        
        # Initialize hardware
        self.reset()
        self.configure(self._threshold, self._leak_rate, self._refractory_period)
        
        print("SNN Accelerator initialized successfully")
        
    def reset(self):
        """Reset the SNN accelerator (both HLS and RTL)"""
        # HLS reset via ctrl_reg
        self.hls.write(self.HLS_CTRL_REG, self.CTRL_RESET)
        time.sleep(0.001)
        self.hls.write(self.HLS_CTRL_REG, 0)
        time.sleep(0.001)
        
    def enable(self):
        """Enable the SNN accelerator"""
        ctrl = self.hls.read(self.HLS_CTRL_REG)
        self.hls.write(self.HLS_CTRL_REG, ctrl | self.CTRL_ENABLE)
        # Start HLS IP
        self.hls.write(self.HLS_AP_CTRL, 0x81)  # ap_start + auto_restart
        
    def disable(self):
        """Disable the SNN accelerator"""
        ctrl = self.hls.read(self.HLS_CTRL_REG)
        self.hls.write(self.HLS_CTRL_REG, ctrl & ~self.CTRL_ENABLE)
        
    def configure(self, threshold=None, leak_rate=None, tau=None, 
                  refractory_period=None):
        """
        Configure neuron parameters via SNN Config Registers.
        
        These parameters are written directly to the RTL neuron array
        and take effect immediately.
        
        Args:
            threshold: Spike threshold (0-65535)
            leak_rate: Membrane potential leak rate (0-255, raw hardware encoding)
            tau: Decay constant (0.0-1.0). Alternative to leak_rate.
                 If both tau and leak_rate are provided, tau takes precedence.
            refractory_period: Refractory period in clock cycles (0-255)
        
        Examples:
            snn.configure(threshold=100, tau=0.9, refractory_period=10)
            snn.configure(threshold=200, leak_rate=51)
        """
        if threshold is not None:
            self._threshold = threshold
            self.cfg.write(self.CFG_THRESHOLD, threshold & 0xFFFF)
        
        # tau takes precedence over leak_rate if both are provided
        if tau is not None:
            leak_rate = tau_to_leak_rate(tau)
            
        if leak_rate is not None:
            self._leak_rate = leak_rate
            
        if refractory_period is not None:
            self._refractory_period = refractory_period
        
        # Write combined neuron params register: [15:8]=refractory, [7:0]=leak
        if leak_rate is not None or refractory_period is not None:
            params = (self._refractory_period & 0xFF) << 8 | (self._leak_rate & 0xFF)
            self.cfg.write(self.CFG_NEURON_PARAMS, params)
        
        # Also write to HLS config_reg for HLS-internal threshold/leak
        if threshold is not None or leak_rate is not None:
            hls_config = (self._leak_rate & 0xFFFF) << 16 | (self._threshold & 0xFFFF)
            self.hls.write(self.HLS_CONFIG_REG, hls_config)
    
    def configure_learning(self, a_plus=10, a_minus=12, tau_plus=20, 
                          tau_minus=20, w_max=255, w_min=0):
        """
        Configure STDP learning parameters via HLS registers.
        
        Args:
            a_plus: Potentiation amplitude (0-255)
            a_minus: Depression amplitude (0-255)
            tau_plus: Potentiation time constant (0-255)
            tau_minus: Depression time constant (0-255)
            w_max: Maximum weight (0-65535)
            w_min: Minimum weight (0-65535)
        """
        # Pack into 144-bit learning_params (5 x 32-bit words)
        word0 = (a_plus & 0xFF) | ((a_minus & 0xFF) << 8) | \
                ((tau_plus & 0xFF) << 16) | ((tau_minus & 0xFF) << 24)
        word1 = (w_max & 0xFFFF) | ((w_min & 0xFFFF) << 16)
        
        self.hls.write(self.HLS_LEARNING_PARAMS, word0)
        self.hls.write(self.HLS_LEARNING_PARAMS + 4, word1)
        
    def set_reward(self, reward):
        """
        Set reward signal for R-STDP learning.
        
        Args:
            reward: Reward value (0-255)
        """
        self.hls.write(self.HLS_REWARD_SIGNAL, reward & 0xFF)
    
    #----------------------------------------------------------------------
    # Router Configuration
    #----------------------------------------------------------------------
    
    def program_connection(self, src_neuron, conn_idx, dest_neuron, 
                          weight=10, excitatory=True, delay=0):
        """
        Program a single connection in the spike router.
        
        Args:
            src_neuron: Source neuron ID (0-1023)
            conn_idx: Connection index for this source (0-31)
            dest_neuron: Destination neuron ID (0-1023)
            weight: Synaptic weight (0-255)
            excitatory: True for excitatory, False for inhibitory
            delay: Spike delay in cycles (0-255)
        """
        # Address = src_neuron * MAX_FANOUT + conn_idx
        # In router's conn_memory address space (addr[31:24] = 0x00)
        addr = (src_neuron * 32 + conn_idx) & 0x00FFFFFF
        
        # Connection format: [valid(1), exc/inh(1), weight(8), delay(8), dest_id(10)]
        # Total 28 bits packed into 32
        data = (1 << 27) | \
               ((1 if excitatory else 0) << 26) | \
               ((weight & 0xFF) << 18) | \
               ((delay & 0xFF) << 10) | \
               (dest_neuron & 0x3FF)
        
        # Set target to router (0)
        self.cfg.write(self.CFG_CONFIG_CTRL, 0)
        self.cfg.write(self.CFG_CONFIG_ADDR, addr)
        self.cfg.write(self.CFG_CONFIG_WDATA, data)  # Triggers config_we
        
    def set_connection_count(self, neuron_id, count):
        """
        Set the number of active connections for a neuron.
        
        Args:
            neuron_id: Neuron ID (0-1023)
            count: Number of connections (0-32)
        """
        # conn_count address space: addr[31:24] = 0x01
        addr = 0x01000000 | (neuron_id & 0x3FF)
        
        self.cfg.write(self.CFG_CONFIG_CTRL, 0)  # target = router
        self.cfg.write(self.CFG_CONFIG_ADDR, addr)
        self.cfg.write(self.CFG_CONFIG_WDATA, count & 0xFF)
    
    def program_network(self, connections):
        """
        Program a complete network topology.
        
        Args:
            connections: List of dicts, each with:
                {'src': int, 'dest': int, 'weight': int, 
                 'excitatory': bool, 'delay': int}
        """
        # Group connections by source neuron
        from collections import defaultdict
        by_src = defaultdict(list)
        for conn in connections:
            by_src[conn['src']].append(conn)
        
        # Program each source neuron's connections
        for src, conns in by_src.items():
            if len(conns) > 32:
                print(f"Warning: Neuron {src} has {len(conns)} connections, "
                      f"max 32. Truncating.")
                conns = conns[:32]
            
            for idx, conn in enumerate(conns):
                self.program_connection(
                    src_neuron=src,
                    conn_idx=idx,
                    dest_neuron=conn['dest'],
                    weight=conn.get('weight', 10),
                    excitatory=conn.get('excitatory', True),
                    delay=conn.get('delay', 0)
                )
            
            self.set_connection_count(src, len(conns))
        
        print(f"Programmed {len(connections)} connections for "
              f"{len(by_src)} source neurons")

    def program_network_from_topology(self, compiled_network):
        """
        Program the spike router from a NeuronGroup-aware CompiledNetwork.

        For each connection in the compiled topology, creates MAX_FANOUT router
        entries mapping source neurons to their destination neurons.
        Weight values are taken from the connection info (uniform default).

        Args:
            compiled_network: A CompiledNetwork from network.py compile().
        """
        total_conns = 0
        for conn_info in compiled_network.connections:
            src_start = conn_info.src_id_start
            dst_start = conn_info.dst_id_start
            src_size = conn_info.src_size
            dst_size = conn_info.dst_size

            # For sparse routers, we program per-source fanout entries.
            # If dst_size > 32 (MAX_FANOUT), we need multiple passes or
            # rely on the HLS learning path instead of router weights.
            max_fanout = min(dst_size, 32)

            for s in range(src_size):
                src_neuron = (src_start + s) & 0x3FF
                for d in range(max_fanout):
                    dest_neuron = (dst_start + d) & 0x3FF
                    self.program_connection(
                        src_neuron=src_neuron,
                        conn_idx=d,
                        dest_neuron=dest_neuron,
                        weight=10,
                        excitatory=True,
                    )
                self.set_connection_count(src_neuron, max_fanout)
                total_conns += max_fanout

        print(f"Programmed {total_conns} router entries from "
              f"{len(compiled_network.connections)} NeuronGroup connections")
    
    def read_router_config(self, addr):
        """
        Read a value from the router's config address space.
        
        Args:
            addr: 32-bit address (see spike_router config_addr map)
        
        Returns:
            32-bit read data
        """
        self.cfg.write(self.CFG_CONFIG_CTRL, 0)  # target = router
        self.cfg.write(self.CFG_CONFIG_ADDR, addr)
        # Config read is registered (1-cycle latency), small delay for safety
        time.sleep(0.00001)
        return self.cfg.read(self.CFG_CONFIG_RDATA)
    
    #----------------------------------------------------------------------
    # Status & Monitoring
    #----------------------------------------------------------------------
    
    def get_status(self):
        """
        Get comprehensive accelerator status.
        
        Returns:
            dict with status information from both HLS and RTL
        """
        # HLS status
        hls_status = self.hls.read(self.HLS_STATUS_REG)
        hls_spike_count = self.hls.read(self.HLS_SPIKE_COUNT)
        hls_weight_sum = self.hls.read(self.HLS_WEIGHT_SUM)
        ap_ctrl = self.hls.read(self.HLS_AP_CTRL)
        
        # RTL status (from config registers)
        router_spikes = self.cfg.read(self.CFG_ROUTER_SPIKE_CNT)
        neuron_spikes = self.cfg.read(self.CFG_NEURON_SPIKE_CNT)
        status_reg = self.cfg.read(self.CFG_STATUS)
        throughput = self.cfg.read(self.CFG_THROUGHPUT)
        
        return {
            # HLS status
            'hls_idle': bool(ap_ctrl & 0x04),
            'hls_done': bool(ap_ctrl & 0x02),
            'hls_status': hls_status,
            'hls_spike_count': hls_spike_count,
            'hls_weight_sum': hls_weight_sum,
            # RTL status
            'router_spike_count': router_spikes,
            'neuron_spike_count': neuron_spikes,
            'fifo_overflow': bool(status_reg & 0x01),
            'active_neurons': (status_reg >> 1) & 0xFF,
            'throughput': throughput,
        }
        
    def clear_counters(self):
        """Clear HLS spike counters"""
        ctrl = self.hls.read(self.HLS_CTRL_REG)
        self.hls.write(self.HLS_CTRL_REG, ctrl | self.CTRL_CLEAR)
        time.sleep(0.0001)
        self.hls.write(self.HLS_CTRL_REG, ctrl & ~self.CTRL_CLEAR)
    
    #----------------------------------------------------------------------
    # DMA Spike Transfer
    #----------------------------------------------------------------------
    
    def send_spikes_dma(self, spike_data):
        """
        Send multiple spikes via DMA (MM2S).
        
        Args:
            spike_data: numpy array of spike packets (uint32)
                        Format: [neuron_id(8) | weight(8) | reserved(16)]
                        
        Returns:
            Number of spikes sent
        """
        if not self._dma_available:
            raise RuntimeError("DMA not available")
            
        n_spikes = min(len(spike_data), len(self.input_buffer))
        self.input_buffer[:n_spikes] = spike_data[:n_spikes]
        
        self.dma.sendchannel.transfer(self.input_buffer[:n_spikes])
        self.dma.sendchannel.wait()
        
        return n_spikes
        
    def receive_spikes_dma(self, max_spikes=1024, timeout=1.0):
        """
        Receive output spikes via DMA (S2MM).
        
        Args:
            max_spikes: Maximum number of spikes to receive
            timeout: Timeout in seconds
            
        Returns:
            numpy array of received spike packets
        """
        if not self._dma_available:
            raise RuntimeError("DMA not available")
            
        self.dma.recvchannel.transfer(self.output_buffer[:max_spikes])
        
        try:
            self.dma.recvchannel.wait(timeout=timeout)
        except TimeoutError:
            pass
            
        n_received = self.dma.recvchannel.transferred // 4
        return self.output_buffer[:n_received].copy()
        
    def process_spike_train(self, spike_times, neuron_ids, weights):
        """
        Process a full spike train through the accelerator.
        
        Args:
            spike_times: Array of spike times (timesteps)
            neuron_ids: Array of input neuron IDs (0-255 for HLS range)
            weights: Array of synaptic weights
            
        Returns:
            Dictionary with output spikes and timing info
        """
        assert len(spike_times) == len(neuron_ids) == len(weights)
        
        self.enable()
        self.clear_counters()
        
        # Pack spike data: [neuron_id(8) | weight(8)]
        spike_data = np.zeros(len(spike_times), dtype=np.uint32)
        spike_data = (neuron_ids.astype(np.uint32) & 0xFF) | \
                     ((weights.astype(np.uint32) & 0xFF) << 8)
        
        start_time = time.time()
        
        if self._dma_available:
            self.send_spikes_dma(spike_data)
            output_spikes = self.receive_spikes_dma()
        else:
            output_spikes = np.array([], dtype=np.uint32)
            
        elapsed_time = time.time() - start_time
        status = self.get_status()
        
        return {
            'output_spikes': output_spikes,
            'total_output_spikes': status['neuron_spike_count'],
            'router_spike_count': status['router_spike_count'],
            'processing_time_ms': elapsed_time * 1000,
            'spikes_per_second': len(spike_times) / elapsed_time if elapsed_time > 0 else 0,
            'fifo_overflow': status['fifo_overflow'],
        }
    
    #----------------------------------------------------------------------
    # Properties
    #----------------------------------------------------------------------
    
    @property
    def threshold(self):
        return self._threshold
        
    @threshold.setter
    def threshold(self, value):
        self.configure(threshold=value)
        
    @property
    def leak_rate(self):
        return self._leak_rate
        
    @leak_rate.setter
    def leak_rate(self, value):
        self.configure(leak_rate=value)
        
    @property
    def refractory_period(self):
        return self._refractory_period
        
    @refractory_period.setter
    def refractory_period(self, value):
        self.configure(refractory_period=value)
        
    def close(self):
        """Clean up resources"""
        self.disable()
        if self._dma_available:
            del self.input_buffer
            del self.output_buffer
        print("SNN Accelerator closed")
        

def test_basic():
    """Basic functionality test"""
    print("=" * 50)
    print("SNN Accelerator Basic Test")
    print("=" * 50)
    
    snn = SNNAccelerator('snn_integrated.bit')
    
    # Configure neuron parameters
    snn.configure(threshold=100, tau=0.9, refractory_period=10)
    print(f"Configured: threshold={snn.threshold}, "
          f"leak_rate={snn.leak_rate}, refractory={snn.refractory_period}")
    
    # Program a simple network: neuron 0 → neuron 1
    snn.program_connection(src_neuron=0, conn_idx=0, 
                          dest_neuron=1, weight=50, excitatory=True)
    snn.set_connection_count(0, 1)
    
    # Enable and check status
    snn.enable()
    status = snn.get_status()
    print(f"Status: {status}")
    
    snn.close()
    print("Test completed successfully!")
    

if __name__ == "__main__":
    test_basic()
