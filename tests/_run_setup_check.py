#!/usr/bin/env python3
"""Upload and run setup check on FPGA board."""
import paramiko
import sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.0.40', username='xilinx', password='xilinx', timeout=10)

# Upload setup check script
sftp = ssh.open_sftp()
sftp.put('tests/fpga_setup_check.py', '/home/xilinx/snn_coverif/fpga_setup_check.py')
sftp.close()
print("Uploaded fpga_setup_check.py")

# Run it
cmd = 'source /usr/local/share/pynq-venv/bin/activate && cd /home/xilinx/snn_coverif && python3 fpga_setup_check.py'
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
out = stdout.read().decode()
err = stderr.read().decode()
print(out)
if err:
    print('STDERR:', err)
ssh.close()
