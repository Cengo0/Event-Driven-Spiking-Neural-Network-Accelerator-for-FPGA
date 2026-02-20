#!/usr/bin/env python3
"""
INA226 Power Measurement for PYNQ-Z2
======================================
Measures power consumption during SNN FPGA inference and computes
energy-per-inference (mJ/inference) — **required for paper Section V**.

PYNQ-Z2 power topology
-----------------------
Three INA226 sensors monitor independent rails:
  Addr 0x40  →  VCC1V2  (PL fabric core)
  Addr 0x41  →  VCC1V8  (PS = ARM Cortex-A9)
  Addr 0x42  →  VCCV3V3 (3.3 V peripherals / I/O)

Shunt resistors: R_shunt = 0.010 Ω (10 mΩ) each rail.
I2C bus: /dev/i2c-0  (PS I2C master 0, default on PYNQ-Z2).

Usage (on PYNQ board as root):
    sudo python3 ina226_power_measure.py [--mode idle|inference|full]
    sudo python3 ina226_power_measure.py --mode full --duration 30

Output:
    Prints per-rail readings and saves JSON to /home/xilinx/snn/power_results.json.

Requires:
    pip install smbus2   (or apt-get install python3-smbus)

Author:  Jiwoon Lee
Date:    2026-02-21
"""

import argparse
import json
import os
import struct
import sys
import time
import traceback
from typing import Dict, List, Optional, Tuple

# I2C via smbus2 (preferred) or fallback smbus
try:
    import smbus2 as smbus_mod  # type: ignore[import]
    _SMBUS_CLASS = smbus_mod.SMBus
except ImportError:
    try:
        import smbus as smbus_mod  # type: ignore[import]
        _SMBUS_CLASS = smbus_mod.SMBus
    except ImportError:
        _SMBUS_CLASS = None

import ctypes
import fcntl

# =====================================================================
# INA226 Driver (raw I2C ioctl, no smbus2 dependency)
# =====================================================================

I2C_SLAVE = 0x0703

INA226_CONFIG   = 0x00
INA226_SHUNT_V  = 0x01
INA226_BUS_V    = 0x02
INA226_POWER    = 0x03
INA226_CURRENT  = 0x04
INA226_CALIB    = 0x05
INA226_MFID     = 0xFE
INA226_DIE_ID   = 0xFF

# Configuration: avg=16, Vbus_CT=1.1ms, Vsh_CT=1.1ms, continuous-both
INA226_CFG_DEFAULT = 0x4527


class INA226:
    """
    INA226 power/current/voltage monitor over I2C.

    Parameters
    ----------
    bus_id   : int   Linux I2C bus number  (0 for /dev/i2c-0)
    address  : int   7-bit I2C device address
    r_shunt  : float Shunt resistance in Ohms (default 10 mΩ)
    max_amps : float Maximum expected current in Amps (default 4.0 A)
    """

    def __init__(self, bus_id: int = 0, address: int = 0x40,
                 r_shunt: float = 0.010, max_amps: float = 4.0):
        self.address   = address
        self.r_shunt   = r_shunt
        self.max_amps  = max_amps

        # Calibration
        self.current_lsb = max_amps / 32768.0          # A/bit
        self.power_lsb   = 25.0 * self.current_lsb    # W/bit
        self._calib_val  = int(0.00512 / (self.current_lsb * r_shunt))

        # Open I2C bus (raw ioctl avoids smbus2 dependency)
        dev = f'/dev/i2c-{bus_id}'
        try:
            self._fd = os.open(dev, os.O_RDWR)
            fcntl.ioctl(self._fd, I2C_SLAVE, address)
        except OSError as e:
            raise OSError(f"Cannot open {dev} at addr 0x{address:02X}: {e}") from e

        # Verify manufacturer ID (should be 0x5449 = Texas Instruments)
        try:
            mfid = self._read_reg(INA226_MFID)
            if mfid != 0x5449:
                raise RuntimeError(
                    f"INA226 at 0x{address:02X}: unexpected MF ID 0x{mfid:04X} "
                    f"(expected 0x5449). Check I2C address."
                )
        except Exception as e:
            raise RuntimeError(f"INA226 at 0x{address:02X} not found: {e}") from e

        # Write calibration and configuration
        self._write_reg(INA226_CALIB, self._calib_val)
        self._write_reg(INA226_CONFIG, INA226_CFG_DEFAULT)
        time.sleep(0.010)  # let first conversion complete

    def close(self) -> None:
        os.close(self._fd)

    # ── Public measurement ──────────────────────────────────────────

    def voltage(self) -> float:
        """Bus voltage in Volts (LSB = 1.25 mV)."""
        raw = self._read_reg_signed(INA226_BUS_V)
        return raw * 1.25e-3

    def current(self) -> float:
        """Current in Amps."""
        raw = self._read_reg_signed(INA226_CURRENT)
        return raw * self.current_lsb

    def power(self) -> float:
        """Power register reading in Watts."""
        raw = self._read_reg(INA226_POWER)
        return raw * self.power_lsb

    def shunt_voltage(self) -> float:
        """Shunt voltage in mV (LSB = 2.5 μV)."""
        raw = self._read_reg_signed(INA226_SHUNT_V)
        return raw * 2.5e-3   # result in mV

    def read_all(self) -> Dict[str, float]:
        return {
            'voltage_V':    self.voltage(),
            'current_A':    self.current(),
            'power_W':      self.power(),
            'shunt_mV':     self.shunt_voltage(),
        }

    # ── I2C primitives ──────────────────────────────────────────────

    def _write_reg(self, reg: int, value: int) -> None:
        buf = struct.pack('>BH', reg, value & 0xFFFF)
        os.write(self._fd, buf)

    def _read_reg(self, reg: int) -> int:
        os.write(self._fd, bytes([reg]))
        raw = os.read(self._fd, 2)
        return struct.unpack('>H', raw)[0]

    def _read_reg_signed(self, reg: int) -> int:
        val = self._read_reg(reg)
        return val if val < 0x8000 else val - 0x10000


# =====================================================================
# Multi-rail monitor
# =====================================================================

RAIL_CONFIG = [
    {'name': 'VCC1V2_PL',   'addr': 0x40, 'r_shunt': 0.010, 'max_amps': 4.0},
    {'name': 'VCC1V8_PS',   'addr': 0x41, 'r_shunt': 0.010, 'max_amps': 4.0},
    {'name': 'VCC3V3_IO',   'addr': 0x42, 'r_shunt': 0.010, 'max_amps': 2.0},
]


def open_sensors(bus_id: int = 0) -> List[Tuple[str, INA226]]:
    """Open all available INA226 sensors.  Returns list of (name, sensor)."""
    sensors = []
    for cfg in RAIL_CONFIG:
        try:
            s = INA226(
                bus_id  = bus_id,
                address = cfg['addr'],
                r_shunt = cfg['r_shunt'],
                max_amps= cfg['max_amps'],
            )
            sensors.append((cfg['name'], s))
            print(f"  INA226 @ 0x{cfg['addr']:02X}  [{cfg['name']}]  "
                  f"V={s.voltage():.3f}V  "
                  f"I={s.current():.3f}A  "
                  f"P={s.power()*1000:.1f}mW")
        except Exception as e:
            print(f"  INA226 @ 0x{cfg['addr']:02X}  [{cfg['name']}]  "
                  f"NOT FOUND: {e}")
    return sensors


def sample_power(sensors: List[Tuple[str, INA226]],
                 n_samples: int = 100,
                 interval_s: float = 0.010) -> Dict:
    """
    Sample all rails for duration = n_samples × interval_s.

    Returns per-rail and total statistics.
    """
    all_samples: Dict[str, List[float]] = {name: [] for name, _ in sensors}

    for _ in range(n_samples):
        for name, sensor in sensors:
            all_samples[name].append(sensor.power())
        time.sleep(interval_s)

    # Compute statistics
    stats: Dict[str, Dict] = {}
    total_mean = 0.0
    for name, pw_list in all_samples.items():
        arr = sorted(pw_list)
        mean = sum(arr) / len(arr)
        p5  = arr[max(0, int(len(arr) * 0.05))]
        p95 = arr[min(len(arr)-1, int(len(arr) * 0.95))]
        stats[name] = {
            'mean_W':  round(mean, 4),
            'min_W':   round(arr[0], 4),
            'max_W':   round(arr[-1], 4),
            'p5_W':    round(p5, 4),
            'p95_W':   round(p95, 4),
            'samples': len(arr),
        }
        total_mean += mean

    stats['TOTAL'] = {'mean_W': round(total_mean, 4)}
    return stats


# =====================================================================
# Inference energy measurement
# =====================================================================

def measure_inference_energy(sensors: List[Tuple[str, INA226]],
                              inference_fn,
                              n_runs: int = 100,
                              pre_delay_s: float = 0.5) -> Dict:
    """
    Measure energy per inference.

    Parameters
    ----------
    sensors     : list of (name, INA226) from open_sensors()
    inference_fn: callable() → latency_s  (must return wall-clock seconds per call)
    n_runs      : number of inference calls to average over
    pre_delay_s : warmup / idle measurement duration

    Returns
    -------
    dict with mJ_per_inference, latency_ms, power_W_inference, power_W_idle
    """
    print(f"\n  [1/3] Measuring IDLE power ({pre_delay_s:.0f}s) ...")
    idle_stats = sample_power(sensors,
                              n_samples=int(pre_delay_s / 0.010),
                              interval_s=0.010)
    p_idle_W = idle_stats['TOTAL']['mean_W']
    print(f"        Idle total: {p_idle_W*1000:.1f} mW")

    print(f"\n  [2/3] Running {n_runs} inferences + sampling power ...")
    # Launch inference in background; sample power simultaneously
    import threading

    latencies: List[float] = []
    running = [True]
    power_during: Dict[str, List[float]] = {name: [] for name, _ in sensors}
    sample_times: List[float] = []

    def sampler():
        while running[0]:
            t = time.time()
            for name, sensor in sensors:
                power_during[name].append(sensor.power())
            sample_times.append(time.time() - t)
            time.sleep(0.005)   # 5 ms sampling rate

    t_thread = threading.Thread(target=sampler, daemon=True)
    t_thread.start()

    t0 = time.time()
    for _ in range(n_runs):
        t_call = time.time()
        inference_fn()
        latencies.append(time.time() - t_call)
    t_total = time.time() - t0

    running[0] = False
    t_thread.join(timeout=2.0)

    lat_mean = sum(latencies) / len(latencies)
    lat_ms   = lat_mean * 1000.0

    total_power_during: List[float] = []
    for name, pw_list in power_during.items():
        if total_power_during:
            for i, v in enumerate(pw_list):
                if i < len(total_power_during):
                    total_power_during[i] += v
        else:
            total_power_during = list(pw_list)

    p_inf_W = sum(total_power_during) / len(total_power_during) if total_power_during else 0.0
    p_dynamic_W = p_inf_W - p_idle_W

    # Energy = power × time  (total board power during inference)
    mj_total   = p_inf_W    * lat_mean * 1000.0
    mj_dynamic = p_dynamic_W * lat_mean * 1000.0 if p_dynamic_W > 0 else 0.0

    print(f"        Inference power: {p_inf_W*1000:.1f} mW")
    print(f"        Dynamic power:   {p_dynamic_W*1000:.1f} mW  (inference - idle)")
    print(f"        Mean latency:    {lat_ms:.2f} ms/inference")
    print(f"        Energy/infer:    {mj_total:.3f} mJ  (total board)")
    print(f"        Energy/infer:    {mj_dynamic:.3f} mJ  (dynamic only)")

    print(f"\n  [3/3] Measuring POST-inference idle ...")
    post_stats = sample_power(sensors, n_samples=50, interval_s=0.010)
    p_post_W = post_stats['TOTAL']['mean_W']
    print(f"        Post-idle total: {p_post_W*1000:.1f} mW")

    return {
        'n_runs':          n_runs,
        'p_idle_W':        round(p_idle_W, 4),
        'p_inference_W':   round(p_inf_W, 4),
        'p_dynamic_W':     round(p_dynamic_W, 4),
        'p_post_idle_W':   round(p_post_W, 4),
        'latency_ms':      round(lat_ms, 3),
        'mj_per_inference_total':   round(mj_total, 4),
        'mj_per_inference_dynamic': round(mj_dynamic, 4),
        'per_rail_idle':   {k: v for k, v in idle_stats.items() if k != 'TOTAL'},
        'per_rail_during': {
            name: {
                'mean_W': round(sum(pw) / len(pw), 4) if pw else 0.0
            }
            for name, pw in power_during.items()
        },
        'total_inf_s': round(t_total, 3),
    }


# =====================================================================
# Standalone measurement (no live inference function)
# =====================================================================

def run_standalone_measurement(sensors: List[Tuple[str, INA226]],
                                duration_s: float = 30.0,
                                interval_s: float = 0.010) -> Dict:
    """
    Continuously sample power and print / log results.
    Use this when the inference script runs separately (e.g., you trigger
    it in another SSH session and capture baseline + active power).
    """
    n_samples = int(duration_s / interval_s)
    print(f"\nSampling power for {duration_s:.0f}s ({n_samples} samples at {interval_s*1000:.0f}ms intervals) ...")
    print(f"{'Time':>8}", end='')
    for name, _ in sensors:
        print(f"  {name:>14}", end='')
    print(f"  {'TOTAL':>10}")

    all_pw: List[Dict] = []
    t0 = time.time()

    try:
        for i in range(n_samples):
            row: Dict[str, float] = {}
            total = 0.0
            for name, sensor in sensors:
                pw = sensor.power()
                row[name] = pw
                total += pw
            row['TOTAL'] = total
            all_pw.append(row)

            elapsed = time.time() - t0
            if i % max(1, n_samples // 50) == 0:  # print ~50 lines
                print(f"{elapsed:>7.1f}s", end='')
                for name, _ in sensors:
                    print(f"  {row[name]*1000:>13.1f}mW", end='')
                print(f"  {total*1000:>9.1f}mW")

            time.sleep(interval_s)
    except KeyboardInterrupt:
        print("\nInterrupted.")

    # Summary
    totals = [r['TOTAL'] for r in all_pw]
    result = {
        'duration_s':   duration_s,
        'n_samples':    len(totals),
        'mean_total_W': round(sum(totals) / len(totals), 4),
        'min_total_W':  round(min(totals), 4),
        'max_total_W':  round(max(totals), 4),
        'per_rail': {},
    }
    for name, _ in sensors:
        pws = [r[name] for r in all_pw]
        result['per_rail'][name] = {
            'mean_W': round(sum(pws) / len(pws), 4),
            'min_W':  round(min(pws), 4),
            'max_W':  round(max(pws), 4),
        }
    return result


# =====================================================================
# CLI
# =====================================================================

def parse_args():
    p = argparse.ArgumentParser(description="INA226 power measurement on PYNQ-Z2")
    p.add_argument('--bus',      type=int, default=0,
                   help='I2C bus number (default 0 → /dev/i2c-0)')
    p.add_argument('--mode',     choices=['idle', 'standalone', 'full'],
                   default='standalone',
                   help=(
                       'idle=30s idle-only measurement; '
                       'standalone=continuous sampling; '
                       'full=idle+inference+energy (requires --inference-cmd)'
                   ))
    p.add_argument('--duration', type=float, default=30.0,
                   help='Measurement duration in seconds (for idle/standalone)')
    p.add_argument('--interval', type=float, default=0.010,
                   help='Sampling interval in seconds (default 10ms)')
    p.add_argument('--output',   default='/home/xilinx/snn/power_results.json',
                   help='Output JSON path')
    return p.parse_args()


def main():
    args = parse_args()

    print('=' * 64)
    print("INA226 Power Measurement  —  PYNQ-Z2 SNN FPGA")
    print('=' * 64)

    # Open sensors
    print(f"\nOpening INA226 sensors on /dev/i2c-{args.bus} ...")
    sensors = open_sensors(bus_id=args.bus)

    if not sensors:
        print("ERROR: No INA226 sensors found!")
        print("Check:")
        print("  - i2cdetect -y 0  (should show 40, 41, 42)")
        print("  - /dev/i2c-0 accessible (run as root)")
        sys.exit(1)

    print(f"\nFound {len(sensors)} sensor(s): "
          f"{[n for n, _ in sensors]}")

    result: Dict = {'mode': args.mode}

    if args.mode in ('idle', 'standalone'):
        print(f"\nMode: {args.mode}  ({args.duration:.0f}s)")
        stats = run_standalone_measurement(
            sensors, args.duration, args.interval)
        result.update(stats)
        print(f"\nSummary:")
        print(f"  Mean total power: {stats['mean_total_W']*1000:.1f} mW")
        print(f"  Range:            [{stats['min_total_W']*1000:.1f}, "
              f"{stats['max_total_W']*1000:.1f}] mW")
        for rail, rs in stats['per_rail'].items():
            print(f"    {rail:16s}  mean={rs['mean_W']*1000:.1f}mW")

    elif args.mode == 'full':
        # Demonstration: measure idle first, then a dummy workload
        print("\nMode: full measurement")
        print("(For actual inference energy, run the inference script in a")
        print(" second SSH session while this script captures power.)")
        print("\nCapturing 10s idle baseline ...")
        idle = run_standalone_measurement(sensors, 10.0, args.interval)
        result['idle'] = idle
        print(f"  Idle power: {idle['mean_total_W']*1000:.1f} mW")

        # Busy-loop to simulate 'something running'
        print("\nCapturing 10s busy (CPU spin) for comparison ...")
        import threading
        spinning = [True]
        def spin():
            x = 0.0
            while spinning[0]:
                for _ in range(10000):
                    x += 1.567
        t = threading.Thread(target=spin)
        t.start()
        busy = run_standalone_measurement(sensors, 10.0, args.interval)
        spinning[0] = False
        t.join()
        result['busy'] = busy
        print(f"  Busy power:  {busy['mean_total_W']*1000:.1f} mW")
        pdyn = (busy['mean_total_W'] - idle['mean_total_W']) * 1000
        print(f"  Dynamic:     {pdyn:.1f} mW  (busy - idle)")

    # Save results
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved: {args.output}")

    # Paper-ready summary
    print("\n" + '─' * 64)
    print("Paper Table Values (mJ/inference):")
    print("  Measure with:")
    print("    Terminal 1: sudo python3 ina226_power_measure.py --mode standalone --duration 60")
    print("    Terminal 2: sudo python3 fpga_10class_inference.py --n 100")
    print("  Compute:  E = P_active × T_latency")
    print("            E_dynamic = (P_active - P_idle) × T_latency")

    for name, sensor in sensors:
        sensor.close()


if __name__ == '__main__':
    main()
