#!/usr/bin/env python3
"""Check PYNQ Overlay and DMA/CMA resources on board."""
import paramiko
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.40', 22, 'xilinx', 'xilinx', timeout=10)

# Upload and run a test script on the board
test_code = r'''
import sys, os, traceback

# Test 1: PYNQ Overlay
print("=== Test 1: PYNQ Overlay ===")
try:
    from pynq import Overlay
    ol = Overlay('/home/xilinx/snn_coverif/snn_integrated.bit', download=False)
    print(f"Overlay loaded! IPs: {list(ol.ip_dict.keys())}")
except Exception as e:
    print(f"Overlay failed: {e}")

# Test 2: CMA allocation
print("\n=== Test 2: CMA allocation ===")
try:
    from pynq import allocate
    import numpy as np
    buf = allocate(shape=(4,), dtype=np.uint32)
    print(f"CMA works! phys_addr=0x{buf.physical_address:08X}")
    buf.free()
except Exception as e:
    print(f"CMA failed: {e}")

# Test 3: PYNQ MMIO
print("\n=== Test 3: PYNQ MMIO ===")
try:
    from pynq import MMIO
    m = MMIO(0x43C10000, 0x100)
    v = m.read(0x28)
    print(f"MMIO version: 0x{v:08X}")
except Exception as e:
    print(f"MMIO failed: {e}")

# Test 4: DMA resources
print("\n=== Test 4: DMA resources ===")
for path in ['/dev/dma_heap/', '/proc/meminfo']:
    if os.path.exists(path):
        if os.path.isdir(path):
            print(f"  {path}: {os.listdir(path)}")
        elif 'meminfo' in path:
            with open(path) as f:
                for line in f:
                    if 'cma' in line.lower():
                        print(f"  {line.strip()}")

import glob
for dev in glob.glob('/dev/udmabuf*') + glob.glob('/dev/xlnk*'):
    print(f"  Found: {dev}")
'''

sftp = ssh.open_sftp()
with sftp.open('/home/xilinx/snn_coverif/check_test.py', 'w') as f:
    f.write(test_code)

print("Running PYNQ/DMA check on board...")
stdin, stdout, stderr = ssh.exec_command(
    '/usr/local/share/pynq-venv/bin/python3 /home/xilinx/snn_coverif/check_test.py',
    timeout=30
)
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    # Filter relevant errors
    for line in err.split('\n'):
        if any(k in line.lower() for k in ['error', 'fail', 'xrt', 'device']):
            print(f"  ERR: {line.strip()}")

sftp.close()
ssh.close()
