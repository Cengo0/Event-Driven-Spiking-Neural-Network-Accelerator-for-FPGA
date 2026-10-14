#!/usr/bin/env python3
"""
verify_cnn3_simulation.py
=========================
Compiles and simulates the CNN3 5-Group SNN Hardware Pipeline using Icarus Verilog.
Validates:
  1. Core Groups 0..3 (Layer 2) integration and firing at threshold 103
  2. Event Router arbitration and BRAM Connectivity Table lookup
  3. Core Group 4 (Layer 3) class neuron integration and firing
  4. Class Output Spike FIFO capture and rtl_spike_out_valid assertion
  5. Pin Y18 SCA trigger (snn_busy) assertion and clean return to IDLE
"""

import subprocess
import sys
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TB_FILE   = os.path.join(REPO_ROOT, "hardware/hdl/tb/tb_snn_cnn3.v")
SIM_BIN   = os.path.join(REPO_ROOT, "sim_cnn3")

def run_verification():
    print("=" * 65)
    print("  1. COMPILING CNN3 5-GROUP RTL & TESTBENCH WITH ICARUS VERILOG")
    print("=" * 65)
    cmd = [
        "iverilog", "-g2012",
        f"-I{REPO_ROOT}/config/generated",
        f"-I{REPO_ROOT}/hardware/hdl/rtl/core",
        "-o", SIM_BIN,
        TB_FILE,
        f"{REPO_ROOT}/hardware/hdl/rtl/core/event_router_ng.v",
        f"{REPO_ROOT}/hardware/hdl/rtl/core/core_group.v",
        f"{REPO_ROOT}/hardware/hdl/rtl/core/synaptic_connectivity_table.v"
    ]
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        print("[ERROR] Compilation failed:\n", res.stderr)
        sys.exit(1)
    print("  -> Compilation successful.")

    print("\n" + "=" * 65)
    print("  2. RUNNING CNN3 PIPELINE SIMULATION (VVP)")
    print("=" * 65)
    res = subprocess.run(["vvp", SIM_BIN], cwd=REPO_ROOT, capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0 or "SOME TESTS FAILED" in res.stdout:
        print("[ERROR] Simulation failed!")
        sys.exit(1)
    print("[SUCCESS] All CNN3 RTL hardware pipeline checks verified successfully!")

if __name__ == "__main__":
    run_verification()

