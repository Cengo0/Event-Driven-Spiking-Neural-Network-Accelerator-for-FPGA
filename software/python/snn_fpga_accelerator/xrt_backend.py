"""Minimal XRT/pyxrt helper for SNN accelerator.

This backend writes AXI-Lite registers (mode/time_steps/encoder/learning) via
pyxrt's register API. Streaming helpers are stubbed for now to keep imports
lightweight; DMA/stream handling can be extended once kernel stream names are
finalised.
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np

try:  # pyxrt is optional and only available on Xilinx platforms
    import xrt  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    xrt = None  # type: ignore

import logging
logger = logging.getLogger(__name__)

# Import custom exceptions
from .exceptions import (
    FPGAError,
    TimeoutError as AcceleratorTimeoutError,
    WeightLoadError,
    ConfigurationError,
    CommunicationError,
    BitstreamError,
    KernelExecutionError,
    validate_parameter
)


@dataclass
class RegisterMap:
    """Offsets (in bytes) for AXI-Lite registers of snn_top_hls.

    Extracted from hardware/hls/hls_output/hls/impl/ip/hdl/verilog/snn_top_hls_ctrl_s_axi.v
    All offsets verified from HLS-generated control interface.
    """

    # HLS standard control registers
    ap_ctrl: int = 0x00        # AP_CTRL (bit0=start, bit1=done, bit2=idle, bit3=ready)
    gie: int = 0x04            # Global Interrupt Enable
    ier: int = 0x08            # Interrupt Enable Register
    isr: int = 0x0C            # Interrupt Status Register
    
    # User scalar registers
    ctrl_reg: int = 0x10       # ctrl_reg[31:0]
    config_reg: int = 0x18     # config_reg[31:0]
    mode_reg: int = 0x20       # mode_reg[31:0] (bits[1:0]=mode, bit[8]=encoder_en)
    time_steps_reg: int = 0x28 # time_steps_reg[31:0]
    
    # Learning params struct (5 x 32-bit words, 144-bit packed total)
    learning_base: int = 0x30  # learning_params[31:0] ... learning_params[143:128]
    
    # Encoder config struct (3 x 32-bit words, 80-bit packed total)
    encoder_base: int = 0x48   # encoder_config[31:0], [63:32], [79:64]
    
    # Status/debug read-only registers
    status_reg: int = 0x58         # status_reg[31:0]
    spike_count_reg: int = 0x68    # spike_count_reg[31:0]
    weight_sum_reg: int = 0x78     # weight_sum_reg[31:0]
    version_reg: int = 0x88        # version_reg[31:0]
    
    # Reward signal (R-STDP)
    reward_signal: int = 0x98       # reward_signal[7:0]


def _q8_8(value: float) -> int:
    """Convert python float to signed Q8.8 (16-bit two's complement)."""
    raw = int(round(float(value) * 256.0))
    if raw > 32767:
        raw = 32767
    elif raw < -32768:
        raw = -32768
    return raw & 0xFFFF


def pack_learning_params_words(
    a_plus: float = 0.1,
    a_minus: float = 0.12,
    tau_plus: int = 20,
    tau_minus: int = 20,
    stdp_window: int = 50,
    learning_rate: float = 0.01,
    rstdp_enable: bool = False,
    trace_decay: float = 0.125,
    reward_scale: float = 1.0,
) -> Tuple[int, int, int, int, int]:
    """Pack learning_params_t into five 32-bit AXI-Lite words.

    Matches HLS struct layout:
      [15:0]    a_plus (Q8.8)
      [31:16]   a_minus (Q8.8)
      [47:32]   tau_plus
      [63:48]   tau_minus
      [79:64]   stdp_window
      [95:80]   learning_rate (Q8.8)
      [103:96]  rstdp_enable (bool stored in 8-bit slot)
      [111:104] padding
      [127:112] trace_decay (Q8.8)
      [143:128] reward_scale (Q8.8)
    """
    tau_plus_u16 = int(tau_plus) & 0xFFFF
    tau_minus_u16 = int(tau_minus) & 0xFFFF
    stdp_window_u16 = int(stdp_window) & 0xFFFF
    rstdp_u8 = 1 if rstdp_enable else 0

    a_plus_u16 = _q8_8(a_plus)
    a_minus_u16 = _q8_8(a_minus)
    learning_rate_u16 = _q8_8(learning_rate)
    trace_decay_u16 = _q8_8(trace_decay)
    reward_scale_u16 = _q8_8(reward_scale)

    w0 = a_plus_u16 | (a_minus_u16 << 16)
    w1 = tau_plus_u16 | (tau_minus_u16 << 16)
    w2 = stdp_window_u16 | (learning_rate_u16 << 16)
    w3 = (rstdp_u8 & 0xFF) | (trace_decay_u16 << 16)
    w4 = reward_scale_u16
    return w0, w1, w2, w3, w4


def pack_encoder_config_words(
    encoding_type: int = 0,
    delta_threshold: int = 1000,
    delta_decay: int = 10,
    num_channels: int = 784,
    default_weight: int = 127,
) -> Tuple[int, int, int]:
    """Pack encoder_config_t into three 32-bit AXI-Lite words.

    Matches synthesized bit extraction in snn_top_hls.v:
      encoding_type   = encoder_config[3:0]
      delta_threshold = encoder_config[31:16]
      delta_decay     = encoder_config[47:32]
      num_channels    = encoder_config[63:48]
      default_weight  = encoder_config[71:64]
    """
    enc_type_u4 = int(encoding_type) & 0xF
    dth_u16 = int(delta_threshold) & 0xFFFF
    ddec_u16 = int(delta_decay) & 0xFFFF
    nch_u16 = int(num_channels) & 0xFFFF
    dw_u8 = int(default_weight) & 0xFF

    w0 = enc_type_u4 | (dth_u16 << 16)
    w1 = ddec_u16 | (nch_u16 << 16)
    w2 = dw_u8
    return w0, w1, w2


class XRTBackend:
    """Wrapper over pyxrt for register and DMA operations."""

    AP_START = 0x01
    AP_DONE = 0x02
    AP_IDLE = 0x04
    AP_READY = 0x08

    def __init__(self, xclbin_path: str, device_index: int = 0, reg_map: Optional[RegisterMap] = None) -> None:
        if xrt is None:
            raise CommunicationError(
                "pyxrt is not installed; install Xilinx Runtime (XRT) to use this backend",
                error_code=1001
            )

        try:
            self.device = xrt.device(device_index)
        except Exception as e:
            raise CommunicationError(
                f"Failed to open XRT device {device_index}: {e}",
                device_index=device_index,
                error_code=1002
            ) from e

        try:
            xclbin = xrt.xclbin(xclbin_path)
        except Exception as e:
            raise BitstreamError(
                f"Failed to load XCLBIN file: {e}",
                bitstream_path=xclbin_path,
                error_code=2001
            ) from e

        try:
            self.device.load_xclbin(xclbin)
        except Exception as e:
            raise BitstreamError(
                f"Failed to program FPGA with XCLBIN: {e}",
                bitstream_path=xclbin_path,
                device_index=device_index,
                error_code=2002
            ) from e

        try:
            # Grab the first kernel; name is typically snn_top_hls:{snn_top_hls_1}
            kernels = xclbin.get_kernels()
            if not kernels:
                raise BitstreamError(
                    "No kernels found in XCLBIN",
                    bitstream_path=xclbin_path,
                    error_code=2003
                )
            kname = kernels[0].get_name()
            self.kernel = xrt.kernel(self.device, kname)
            logger.info(f"Loaded kernel: {kname}")
        except BitstreamError:
            raise
        except Exception as e:
            raise CommunicationError(
                f"Failed to instantiate kernel: {e}",
                error_code=1003
            ) from e

        self.regs = reg_map or RegisterMap()
        
        # Buffer cache for reuse (type: xrt.bo but annotated as Any to avoid import errors)
        self._spike_input_bo: Optional[Any] = None
        self._spike_output_bo: Optional[Any] = None
        self._raw_data_bo: Optional[Any] = None

    # ------------------------------------------------------------------
    # Register helpers
    # ------------------------------------------------------------------
    def write_reg(self, offset: int, value: int) -> None:
        try:
            self.kernel.write_register(offset, value)
        except Exception as e:
            raise CommunicationError(
                f"Failed to write register at offset {offset:#x}: {e}",
                error_code=1010
            ) from e
    
    def read_reg(self, offset: int) -> int:
        try:
            return self.kernel.read_register(offset)
        except Exception as e:
            raise CommunicationError(
                f"Failed to read register at offset {offset:#x}: {e}",
                error_code=1011
            ) from e

    def set_ctrl(self, ctrl: int) -> None:
        self.write_reg(self.regs.ctrl_reg, ctrl)

    def set_config(self, config: int) -> None:
        self.write_reg(self.regs.config_reg, config)

    def set_mode(self, mode: int, encoder_enable: bool = False) -> None:
        payload = mode & 0x3
        if encoder_enable:
            payload |= (1 << 8)
        self.write_reg(self.regs.mode_reg, payload)

    def set_time_steps(self, steps: int) -> None:
        self.write_reg(self.regs.time_steps_reg, steps)

    def set_reward(self, reward: int) -> None:
        self.write_reg(self.regs.reward_signal, reward & 0xFF)

    def set_learning_params(
        self,
        a_plus: float = 0.1,
        a_minus: float = 0.12,
        tau_plus: int = 20,
        tau_minus: int = 20,
        stdp_window: int = 50,
        learning_rate: float = 0.01,
        rstdp_enable: bool = False,
        trace_decay: float = 0.125,
        reward_scale: float = 1.0,
    ) -> None:
        """Write packed learning_params_t words to AXI-Lite registers."""
        words = pack_learning_params_words(
            a_plus=a_plus,
            a_minus=a_minus,
            tau_plus=tau_plus,
            tau_minus=tau_minus,
            stdp_window=stdp_window,
            learning_rate=learning_rate,
            rstdp_enable=rstdp_enable,
            trace_decay=trace_decay,
            reward_scale=reward_scale,
        )
        base = self.regs.learning_base
        for i, w in enumerate(words):
            self.write_reg(base + (i * 4), int(w) & 0xFFFFFFFF)
    
    def load_weights(self, weights: np.ndarray) -> None:
        """Load weights to FPGA weight memory via s_axis_weights stream.
        
        Args:
            weights: 2D numpy array of shape (num_neurons, num_neurons)
                    Values should be in range [0, 255] (8-bit weights)
        
        Raises:
            WeightLoadError: If weight matrix shape or values are invalid
            CommunicationError: If DMA transfer fails
        """
        if xrt is None:
            raise CommunicationError(
                "XRT not available",
                error_code=1001
            )
        
        # Validate weight shape
        if weights.ndim != 2:
            raise WeightLoadError(
                f"Weights must be 2D array, got {weights.ndim}D",
                weight_shape=weights.shape,
                error_code=3001
            )
        
        rows, cols = weights.shape
        if rows > 256 or cols > 256:
            raise WeightLoadError(
                f"Weight matrix too large: {rows}x{cols}, max 256x256",
                weight_shape=(rows, cols),
                expected_shape=(256, 256),
                error_code=3002
            )
        
        # Validate weight values
        if weights.min() < 0 or weights.max() > 255:
            raise WeightLoadError(
                f"Weight values out of range [0, 255]: [{weights.min()}, {weights.max()}]",
                weight_shape=weights.shape,
                error_code=3003
            )
        
        try:
            # Pack weights into AXI Stream format
            # Format: [23:16] = weight, [15:8] = col, [7:0] = row
            weight_data = bytearray()
            for i in range(rows):
                for j in range(cols):
                    weight_val = int(weights[i, j]) & 0xFF
                    word = (weight_val << 16) | (j << 8) | i
                    weight_data.extend(struct.pack('<I', word))
            
            # Enable weight load mode (ctrl_reg[6] = 1)
            ctrl = self.read_reg(self.regs.ctrl_reg)
            self.write_reg(self.regs.ctrl_reg, ctrl | (1 << 6))
            
            # Allocate and send weight data
            size = len(weight_data)
            bo_weights = self._allocate_bo(size)
            bo_weights.write(weight_data, 0)
            bo_weights.sync(xrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE, size, 0)
            
            # Disable weight load mode
            self.write_reg(self.regs.ctrl_reg, ctrl)
            
            logger.info(f"Loaded {rows}x{cols} weights to FPGA")
        except (WeightLoadError, CommunicationError):
            raise
        except Exception as e:
            raise WeightLoadError(
                f"Failed to load weights: {e}",
                weight_shape=weights.shape,
                error_code=3004
            ) from e
    
    def set_encoder_config(
        self,
        encoding_type: int = 0,  # 0=NONE, 1=DELTA_SIGMA (current HLS)
        delta_threshold: int = 1000,
        delta_decay: int = 10,
        num_channels: int = 784,
        default_weight: int = 127
    ) -> None:
        """Configure on-chip spike encoder parameters.
        
        Args:
            encoding_type: 4-bit encoding type (ENC_NONE=0, ENC_DELTA_SIGMA=1)
            delta_threshold: Delta-sigma integration threshold
            delta_decay: Delta-sigma decay rate
            num_channels: Number of input channels
            default_weight: Default spike weight (0-255)
        
        Raises:
            ConfigurationError: If parameters are out of valid ranges
        """
        # Validate encoding_type
        validate_parameter(
            encoding_type,
            valid_options=[0, 1],
            parameter_name="encoding_type"
        )

        if not (0 <= delta_threshold <= 65535):
            raise ConfigurationError(
                "delta_threshold must be in range [0, 65535]",
                parameter="delta_threshold",
                value=delta_threshold,
                valid_range=(0, 65535),
                error_code=4001
            )
        if not (0 <= delta_decay <= 65535):
            raise ConfigurationError(
                "delta_decay must be in range [0, 65535]",
                parameter="delta_decay",
                value=delta_decay,
                valid_range=(0, 65535),
                error_code=4002
            )
        if not (0 <= num_channels <= 65535):
            raise ConfigurationError(
                "num_channels must be in range [0, 65535]",
                parameter="num_channels",
                value=num_channels,
                valid_range=(0, 65535),
                error_code=4003
            )
        if not (0 <= default_weight <= 255):
            raise ConfigurationError(
                "default_weight must be in range [0, 255]",
                parameter="default_weight",
                value=default_weight,
                valid_range=(0, 255),
                error_code=4004
            )
        
        try:
            w0, w1, w2 = pack_encoder_config_words(
                encoding_type=encoding_type,
                delta_threshold=delta_threshold,
                delta_decay=delta_decay,
                num_channels=num_channels,
                default_weight=default_weight,
            )
            enc_base = self.regs.encoder_base
            self.write_reg(enc_base + 0x00, w0)
            self.write_reg(enc_base + 0x04, w1)
            self.write_reg(enc_base + 0x08, w2)
        except (ConfigurationError, CommunicationError):
            raise
        except Exception as e:
            raise ConfigurationError(
                f"Failed to configure encoder: {e}",
                error_code=4005
            ) from e

    # ------------------------------------------------------------------
    # DMA Stream Helpers
    # ------------------------------------------------------------------
    def _allocate_bo(self, size: int) -> Any:
        """Allocate XRT buffer object."""
        if xrt is None:
            raise RuntimeError("XRT not available")
        # Create buffer in device memory (bank 0 by default)
        return xrt.bo(self.device, size, xrt.bo.flags.normal, 0)
    
    def send_spike_stream(self, spike_data: bytes, run_kernel: bool = True) -> None:
        """Send spike stream to s_axis_spikes via DMA.
        
        Args:
            spike_data: Packed spike packets (32-bit AER format per spike)
            run_kernel: Whether to trigger kernel execution after transfer
            
        Raises:
            CommunicationError: If DMA transfer fails
        """
        if xrt is None:
            raise CommunicationError(
                "XRT not available",
                error_code=1001
            )
        
        size = len(spike_data)
        if size == 0:
            return
        
        try:
            # Allocate or reuse buffer
            if self._spike_input_bo is None or self._spike_input_bo.size() < size:
                self._spike_input_bo = self._allocate_bo(size)
            
            # Write data to buffer
            self._spike_input_bo.write(spike_data, 0)
            
            # Sync to device
            self._spike_input_bo.sync(xrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE, size, 0)
            
            if run_kernel:
                self.run_kernel()
        except (CommunicationError, AcceleratorTimeoutError, KernelExecutionError):
            raise
        except Exception as e:
            raise CommunicationError(
                f"Failed to send spike stream: {e}",
                error_code=1015
            ) from e
    
    def run_kernel(self, timeout_sec: float = 10.0) -> None:
        """Start kernel execution and wait for completion.
        
        Args:
            timeout_sec: Maximum time to wait for completion
            
        Raises:
            AcceleratorTimeoutError: If kernel doesn't complete within timeout
            KernelExecutionError: If kernel reports error status
            CommunicationError: If XRT communication fails
        """
        if xrt is None:
            raise CommunicationError(
                "XRT not available",
                error_code=1001
            )
        
        try:
            # Start kernel (set AP_START bit)
            self.write_reg(self.regs.ap_ctrl, self.AP_START)
            logger.debug("Kernel started")
        except CommunicationError:
            raise
        except Exception as e:
            raise KernelExecutionError(
                f"Failed to start kernel: {e}",
                kernel_name="snn_top_hls",
                error_code=5001
            ) from e
        
        # Wait for completion with timeout
        import time
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            try:
                status = self.kernel.read_register(self.regs.ap_ctrl)

                # HLS ap_ctrl semantics:
                #   bit0=ap_start, bit1=ap_done, bit2=ap_idle, bit3=ap_ready.
                # AP_READY is NOT an error bit; completion is AP_DONE.
                if status & self.AP_DONE:
                    logger.debug("Kernel completed successfully")
                    return
                    
                time.sleep(0.001)  # 1ms poll interval
            except (KernelExecutionError, CommunicationError):
                raise
            except Exception as e:
                raise CommunicationError(
                    f"Failed to poll kernel status: {e}",
                    error_code=1012
                ) from e
        
        raise AcceleratorTimeoutError(
            f"Kernel execution timeout after {timeout_sec}s",
            timeout_duration=timeout_sec,
            operation="kernel_execution",
            error_code=6001
        )
    
    def receive_spike_stream(self, max_size: int = 4096) -> bytes:
        """Receive spike output from m_axis_spikes via DMA.
        
        Args:
            max_size: Maximum buffer size to allocate
            
        Returns:
            Raw bytes from output spike stream
            
        Raises:
            CommunicationError: If DMA transfer fails
        """
        if xrt is None:
            raise CommunicationError(
                "XRT not available",
                error_code=1001
            )
        
        try:
            # Allocate or reuse buffer
            if self._spike_output_bo is None or self._spike_output_bo.size() < max_size:
                self._spike_output_bo = self._allocate_bo(max_size)
            
            # Wait for kernel completion (poll done bit)
            while True:
                status = self.kernel.read_register(self.regs.ap_ctrl)
                if status & 0x02:  # bit[1] = done
                    break
        
            # Sync from device
            self._spike_output_bo.sync(xrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE, max_size, 0)
            
            # Read actual data size from spike_count_reg
            spike_count = self.kernel.read_register(self.regs.spike_count_reg)
            actual_size = min(spike_count * 4, max_size)  # 4 bytes per spike (32-bit AER)
            
            # Read data from buffer
            data = bytearray(actual_size)
            self._spike_output_bo.read(data, 0)
            return bytes(data)
        except CommunicationError:
            raise
        except Exception as e:
            raise CommunicationError(
                f"Failed to receive spike stream: {e}",
                error_code=1013
            ) from e
    
    def send_raw_frame(self, raw_data: bytes, run_kernel: bool = False) -> None:
        """Send raw sensor data to s_axis_data for on-chip encoding.
        
        Args:
            raw_data: Raw pixel/sensor data (format depends on encoder config)
            run_kernel: Whether to trigger kernel execution (usually False, use send_spike_stream)
            
        Raises:
            CommunicationError: If DMA transfer fails
        """
        if xrt is None:
            raise CommunicationError(
                "XRT not available",
                error_code=1001
            )
        
        size = len(raw_data)
        if size == 0:
            return
        
        try:
            # Allocate or reuse buffer
            if self._raw_data_bo is None or self._raw_data_bo.size() < size:
                self._raw_data_bo = self._allocate_bo(size)
        
            # Write and sync
            self._raw_data_bo.write(raw_data, 0)
            self._raw_data_bo.sync(xrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE, size, 0)
            
            if run_kernel:
                self.write_reg(self.regs.ap_ctrl, 0x01)
        except CommunicationError:
            raise
        except Exception as e:
            raise CommunicationError(
                f"Failed to send raw frame: {e}",
                error_code=1014
            ) from e
