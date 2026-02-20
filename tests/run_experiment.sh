#!/bin/bash
# Run the full comparison experiment with reliable output capture.
# Usage: bash tests/run_experiment.sh
#
# Output goes to:
#   logs/experiment_full_comparison_<timestamp>.log  (from DualLogger inside script)
#   logs/run_experiment_console_<timestamp>.txt       (stdout+stderr of this shell)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
CONSOLE_LOG="logs/run_experiment_console_${TIMESTAMP}.txt"
mkdir -p logs

echo "[$(date '+%H:%M:%S')] Starting experiment (PID $$)" | tee -a "$CONSOLE_LOG"
echo "[$(date '+%H:%M:%S')] Working dir: $REPO_ROOT"      | tee -a "$CONSOLE_LOG"
echo "[$(date '+%H:%M:%S')] Console log: $CONSOLE_LOG"    | tee -a "$CONSOLE_LOG"

# Activate conda env and run, redirecting output
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate fpga

echo "[$(date '+%H:%M:%S')] Python: $(python -c 'import sys; print(sys.executable)')" | tee -a "$CONSOLE_LOG"
echo "[$(date '+%H:%M:%S')] PyTorch: $(python -c 'import torch; print(torch.__version__, "| CUDA:", torch.cuda.is_available())')" | tee -a "$CONSOLE_LOG"
echo "" | tee -a "$CONSOLE_LOG"

# Run experiment; tee captures stdout+stderr to console log
python -u tests/experiment_full_comparison.py 2>&1 | tee -a "$CONSOLE_LOG"

echo "" | tee -a "$CONSOLE_LOG"
echo "[$(date '+%H:%M:%S')] Experiment finished." | tee -a "$CONSOLE_LOG"
