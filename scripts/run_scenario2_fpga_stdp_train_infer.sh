#!/usr/bin/env bash
set -euo pipefail

# Scenario 2 (native): FPGA STDP parity/train path -> FPGA inference
# Usage example:
#   ./scripts/run_scenario2_fpga_stdp_train_infer.sh \
#     --stdp-steps 100 \
#     --infer-output /home/xilinx/snn/mnist_10class_results_scenario2.json

DATA_DIR="/home/xilinx/snn"
PARITY_SCRIPT="/home/xilinx/snn/tests/fpga_stdp_parity.py"
INFER_SCRIPT="/home/xilinx/snn/tests/fpga_10class_inference.py"
STDP_STEPS=100
INFER_N=10000
PACKET_ID_WIDTH=13
PL_CLOCK_HZ=80000000
PARITY_OUTPUT="/home/xilinx/snn/stdp_parity_results_scenario2.json"
INFER_OUTPUT="/home/xilinx/snn/mnist_10class_results_scenario2.json"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --data-dir) DATA_DIR="$2"; shift 2 ;;
    --parity-script) PARITY_SCRIPT="$2"; shift 2 ;;
    --inference-script) INFER_SCRIPT="$2"; shift 2 ;;
    --stdp-steps) STDP_STEPS="$2"; shift 2 ;;
    --infer-n) INFER_N="$2"; shift 2 ;;
    --packet-id-width) PACKET_ID_WIDTH="$2"; shift 2 ;;
    --pl-clock-hz) PL_CLOCK_HZ="$2"; shift 2 ;;
    --parity-output) PARITY_OUTPUT="$2"; shift 2 ;;
    --infer-output) INFER_OUTPUT="$2"; shift 2 ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
done

parity_cmd=(
  sudo -E env PYTHONPATH=/home/xilinx/snn/software/python:${PYTHONPATH:-}
  /usr/local/share/pynq-venv/bin/python3 "$PARITY_SCRIPT"
  --data "$DATA_DIR"
  --n-steps "$STDP_STEPS"
  --checkpoint-every 0
  --run-chunk-steps 1
  --runtime-profile balanced
  --packet-id-width "$PACKET_ID_WIDTH"
  --assert-hls-reset
  --strict
  --no-cma-spike-buffer
  --post-flush-runs 4
  --sw-post-source synthetic
  --check-hls-version
)

echo "[Scenario2] STDP parity/training run"
echo "[Scenario2] Running: ${parity_cmd[*]}"
"${parity_cmd[@]}"

# Keep a scenario-specific copy when default output exists.
if [[ -f /home/xilinx/snn/stdp_parity_results.json ]]; then
  cp /home/xilinx/snn/stdp_parity_results.json "$PARITY_OUTPUT"
fi

infer_cmd=(
  sudo python3 "$INFER_SCRIPT"
  --data "$DATA_DIR"
  --n "$INFER_N"
  --packet-id-width "$PACKET_ID_WIDTH"
  --assert-hls-reset
  --strict-identical
  --pl-clock-hz "$PL_CLOCK_HZ"
  --benchmark-fast
  --output "$INFER_OUTPUT"
)

echo "[Scenario2] Post-training inference run"
echo "[Scenario2] Running: ${infer_cmd[*]}"
"${infer_cmd[@]}"

echo "[Scenario2] Done"
echo "  parity: $PARITY_OUTPUT"
echo "  infer : $INFER_OUTPUT"
python3 - <<PY
import json
p = "$INFER_OUTPUT"
d = json.load(open(p))
print("strict_failures_n:", len(d.get("strict_failures", [])))
print("hw_acc_ttfs:", d.get("hw_acc_ttfs"))
print("sw_acc_ttfs:", d.get("sw_acc_ttfs"))
print("pl_latency_cycles_mean:", d.get("pl_latency_cycles_mean"))
print("pl_service_cycles_mean:", d.get("pl_service_cycles_mean"))
print("ms_per_image:", d.get("ms_per_image"))
PY
