#!/bin/bash
# run_inference.sh
# Safely executes the PYNQ FPGA inference script with root privileges
# while preserving the Python environment paths.

# Ensure the script is run with sudo
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root using: sudo ./run_inference.sh"
  exit 1
fi

echo "Starting FPGA Co-Processing Inference..."

# Execute Python, preserving the PYTHONPATH so the pynq library is found,
# and forward any command-line arguments (like --samples 100) to the script.
sudo -E env PATH=$PATH PYTHONPATH=$PYTHONPATH python3 fpga_3layer_inference.py "$@"