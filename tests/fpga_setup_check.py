#!/usr/bin/env python3
"""Helper script to fix PYNQ device access and test overlay loading."""
import os
import sys
import subprocess

def run(cmd):
    print(f">>> {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(f"  ERR: {result.stderr.strip()}")
    return result

# Check groups
run("groups xilinx")
run("id")

# Add to render and video groups
run("echo xilinx | sudo -S usermod -a -G render xilinx 2>&1")
run("echo xilinx | sudo -S usermod -a -G video xilinx 2>&1")

# Try loading overlay with sudo
print("\n=== Testing Overlay Load (sudo) ===")
result = run(
    'echo xilinx | sudo -S -E '
    '/usr/local/share/pynq-venv/bin/python3 -c "'
    'from pynq import Overlay; '
    'ol = Overlay(\\"/home/xilinx/snn_coverif/snn_integrated.bit\\"); '
    'print(\\\"Overlay loaded successfully!\\\"); '
    'print(\\\"IPs:\\\", list(ol.ip_dict.keys()))"'
)

if result.returncode != 0:
    print("\n=== Fallback: Direct fpga_manager + mmap ===")
    # Try loading bitstream via fpga_manager directly
    run("echo xilinx | sudo -S cp /home/xilinx/snn_coverif/snn_integrated.bit /lib/firmware/snn_integrated.bit")
    run("echo xilinx | sudo -S bash -c 'echo 0 > /sys/class/fpga_manager/fpga0/flags'")
    run("echo xilinx | sudo -S bash -c 'echo snn_integrated.bit > /sys/class/fpga_manager/fpga0/firmware'")
    run("cat /sys/class/fpga_manager/fpga0/state")
    
    # Try direct mmap MMIO
    print("\n=== Direct mmap test ===")
    try:
        import mmap
        fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
        mm = mmap.mmap(fd, 0x100, offset=0x43C10000)
        # Read VERSION register at offset 0x28
        mm.seek(0x28)
        data = int.from_bytes(mm.read(4), 'little')
        print(f"CFG_VERSION = 0x{data:08X}")
        # Read THRESHOLD at offset 0x10
        mm.seek(0x10)
        data = int.from_bytes(mm.read(4), 'little')
        print(f"CFG_THRESHOLD = 0x{data:08X}")
        mm.close()
        os.close(fd)
    except PermissionError:
        print("  Need root for /dev/mem access, trying with sudo...")
        run(
            'echo xilinx | sudo -S /usr/local/share/pynq-venv/bin/python3 -c "'
            'import os, mmap; '
            'fd = os.open(\\"/dev/mem\\", os.O_RDWR | os.O_SYNC); '
            'mm = mmap.mmap(fd, 0x100, offset=0x43C10000); '
            'mm.seek(0x28); d = int.from_bytes(mm.read(4), \\"little\\"); '
            'print(f\\"CFG_VERSION = 0x{d:08X}\\"); '
            'mm.seek(0x10); d = int.from_bytes(mm.read(4), \\"little\\"); '
            'print(f\\"CFG_THRESHOLD = 0x{d:08X}\\"); '
            'mm.close(); os.close(fd)"'
        )

print("\nDone.")
