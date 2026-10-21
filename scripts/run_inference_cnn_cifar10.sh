#!/bin/bash
# run_inference_cnn_cifar10.sh
# Safely executes the PYNQ FPGA CIFAR-10 CNN3 inference script with root privileges
# while preserving the Python environment paths.

# Ensure the script is run with sudo
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root using: sudo ./run_inference_cnn_cifar10.sh"
  exit 1
fi

echo "Starting CIFAR-10 CNN3 Inference..."

# Execute Python, preserving the PYTHONPATH so the pynq library is found,
# and forward any command-line arguments (like --samples 100) to the script.
sudo -E env PATH=$PATH PYTHONPATH=$PYTHONPATH python3 fpga_cnn3_cifar10_inference.py "$@"

