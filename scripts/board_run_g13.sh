#!/usr/bin/env bash
set -euo pipefail

# Run G13 quantization ablation directly on PYNQ board.
# Expected location: /home/xilinx/snn/scripts/board_run_g13.sh

REMOTE_ROOT="/home/xilinx/snn"
N_IMAGES="10000"
PACKET_ID_WIDTH="13"
PL_CLOCK_HZ="80000000"
VARIANTS="8,4,2"

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --remote-root <path>           (default: ${REMOTE_ROOT})
  --n <images>                   (default: ${N_IMAGES})
  --packet-id-width <bits>       (default: ${PACKET_ID_WIDTH})
  --pl-clock-hz <hz>             (default: ${PL_CLOCK_HZ})
  --variants <csv>               (default: ${VARIANTS})
  -h, --help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote-root) REMOTE_ROOT="$2"; shift 2 ;;
    --n) N_IMAGES="$2"; shift 2 ;;
    --packet-id-width) PACKET_ID_WIDTH="$2"; shift 2 ;;
    --pl-clock-hz) PL_CLOCK_HZ="$2"; shift 2 ;;
    --variants) VARIANTS="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

mkdir -p "${REMOTE_ROOT}/ablation" "${REMOTE_ROOT}/ablation/results" "${REMOTE_ROOT}/scripts"

python3 "${REMOTE_ROOT}/scripts/make_quantized_variants.py" \
  --base-npz "${REMOTE_ROOT}/mnist_10class_deployment.npz" \
  --bits "${VARIANTS}" \
  --out-dir "${REMOTE_ROOT}/ablation" \
  --prefix mnist_10class_deployment \
  --summary-json "${REMOTE_ROOT}/ablation/g13_variants_summary.json"

python3 "${REMOTE_ROOT}/scripts/run_g13_quant_ablation.py" \
  --inference-script "${REMOTE_ROOT}/tests/fpga_10class_inference.py" \
  --data-dir "${REMOTE_ROOT}" \
  --weights-dir "${REMOTE_ROOT}/ablation" \
  --weights-prefix mnist_10class_deployment \
  --variants "${VARIANTS}" \
  --n "${N_IMAGES}" \
  --packet-id-width "${PACKET_ID_WIDTH}" \
  --pl-clock-hz "${PL_CLOCK_HZ}" \
  --out-dir "${REMOTE_ROOT}/ablation/results" \
  --sudo

echo "[DONE] G13 results:"
echo "  ${REMOTE_ROOT}/ablation/g13_variants_summary.json"
echo "  ${REMOTE_ROOT}/ablation/results/g13_quant_ablation_summary.json"
echo "  ${REMOTE_ROOT}/ablation/results/g13_quant_ablation_summary.md"
