#!/usr/bin/env bash
set -euo pipefail

# Scenario: TVLA Temporal Data Logging
# Executes inference strictly on the first 10 images with all-spikes capture mode enabled.

INFER_SCRIPT="/home/xilinx/snn/fpga_tvla_inference.py"

echo "[TVLA Logger] Running physical temporal capture for Side-Channel Analytics..."
sudo python3 "$INFER_SCRIPT"

echo "[TVLA Logger] Done. Please transfer physical_output_spikes.txt back to your host PC."