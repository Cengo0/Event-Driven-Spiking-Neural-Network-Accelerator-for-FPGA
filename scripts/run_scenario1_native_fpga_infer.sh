#!/usr/bin/env bash
set -euo pipefail

# Scenario 1 (native): GPU-trained/exported deployment -> FPGA inference
# Usage example:
#   ./scripts/run_scenario1_native_fpga_infer.sh \
#     --deployment /home/xilinx/snn/mnist_10class_deployment.npz \
#     --output /home/xilinx/snn/mnist_10class_results_scenario1.json

DATA_DIR="/home/xilinx/snn"
INFER_SCRIPT="/home/xilinx/snn/fpga_10class_inference.py"
DEPLOYMENT_NPZ="/home/xilinx/snn/mnist_10class_deployment.npz"
OUTPUT_JSON="/home/xilinx/snn/mnist_10class_results_scenario1.json"
N=10000
PACKET_ID_WIDTH=13
PL_CLOCK_HZ=80000000
BENCHMARK_FAST=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --data-dir) DATA_DIR="$2"; shift 2 ;;
    --inference-script) INFER_SCRIPT="$2"; shift 2 ;;
    --deployment|--weights) DEPLOYMENT_NPZ="$2"; shift 2 ;;
    --output) OUTPUT_JSON="$2"; shift 2 ;;
    --n) N="$2"; shift 2 ;;
    --packet-id-width) PACKET_ID_WIDTH="$2"; shift 2 ;;
    --pl-clock-hz) PL_CLOCK_HZ="$2"; shift 2 ;;
    --no-benchmark-fast) BENCHMARK_FAST=0; shift 1 ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
done

cmd=(
  sudo python3 "$INFER_SCRIPT"
  --data "$DATA_DIR"
  --weights "$DEPLOYMENT_NPZ"
  --n "$N"
  --packet-id-width "$PACKET_ID_WIDTH"
  --assert-hls-reset
  --strict-identical
  --pl-clock-hz "$PL_CLOCK_HZ"
  --output "$OUTPUT_JSON"
)

if [[ "$BENCHMARK_FAST" == "1" ]]; then
  cmd+=(--benchmark-fast)
fi

echo "[Scenario1] Running: ${cmd[*]}"
"${cmd[@]}"

echo "[Scenario1] Done: $OUTPUT_JSON"
python3 - <<PY
import json
p = "$OUTPUT_JSON"
d = json.load(open(p))
print("strict_failures_n:", len(d.get("strict_failures", [])))
print("hw_acc_ttfs:", d.get("hw_acc_ttfs"))
print("sw_acc_ttfs:", d.get("sw_acc_ttfs"))
print("pl_latency_cycles_mean:", d.get("pl_latency_cycles_mean"))
print("pl_service_cycles_mean:", d.get("pl_service_cycles_mean"))
print("ms_per_image:", d.get("ms_per_image"))
PY
