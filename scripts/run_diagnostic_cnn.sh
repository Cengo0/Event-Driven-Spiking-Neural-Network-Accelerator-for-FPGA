#!/bin/bash
# run_diagnostic_cnn.sh
# Safely executes the CNN3 hardware diagnostic suite on PYNQ-Z2 with root privileges.

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root using: sudo ./run_diagnostic_cnn.sh"
  exit 1
fi

echo "Starting CNN3 Accelerator Diagnostic Suite..."
sudo -E env PATH=$PATH PYTHONPATH=$PYTHONPATH python3 diag_cnn3_hardware.py "$@"

