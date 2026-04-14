#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

BOARD_USER="xilinx"
BOARD_HOST="192.168.0.48"
REMOTE_ROOT="/home/xilinx/snn"
N_IMAGES="10000"
PACKET_ID_WIDTH="13"
PL_CLOCK_HZ="80000000"
XPA_DYNAMIC_W=""
SKIP_ABLATION="0"
SKIP_BUNDLE="0"

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --board-host <ip_or_host>      (default: ${BOARD_HOST})
  --board-user <user>            (default: ${BOARD_USER})
  --remote-root <path>           (default: ${REMOTE_ROOT})
  --n <images>                   (default: ${N_IMAGES})
  --packet-id-width <bits>       (default: ${PACKET_ID_WIDTH})
  --pl-clock-hz <hz>             (default: ${PL_CLOCK_HZ})
  --xpa-dynamic-w <watts>        (optional, for energy recompute)
  --skip-ablation                (skip board G13 run)
  --skip-bundle                  (skip local G14 bundle generation)
  -h, --help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --board-host) BOARD_HOST="$2"; shift 2 ;;
    --board-user) BOARD_USER="$2"; shift 2 ;;
    --remote-root) REMOTE_ROOT="$2"; shift 2 ;;
    --n) N_IMAGES="$2"; shift 2 ;;
    --packet-id-width) PACKET_ID_WIDTH="$2"; shift 2 ;;
    --pl-clock-hz) PL_CLOCK_HZ="$2"; shift 2 ;;
    --xpa-dynamic-w) XPA_DYNAMIC_W="$2"; shift 2 ;;
    --skip-ablation) SKIP_ABLATION="1"; shift ;;
    --skip-bundle) SKIP_BUNDLE="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

BOARD="${BOARD_USER}@${BOARD_HOST}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOCAL_BOARD_DIR="${ROOT_DIR}/outputs/board_results_${TS}"
mkdir -p "${LOCAL_BOARD_DIR}"

echo "[INFO] Root: ${ROOT_DIR}"
echo "[INFO] Board: ${BOARD}"
echo "[INFO] Remote root: ${REMOTE_ROOT}"

echo "[1/4] Sync scripts to board"
scp \
  scripts/make_quantized_variants.py \
  scripts/run_g13_quant_ablation.py \
  scripts/compute_energy_metrics.py \
  "${BOARD}:${REMOTE_ROOT}/scripts/"

if [[ "${SKIP_ABLATION}" == "0" ]]; then
  echo "[2/4] Run G13 quantization ablation on board"
  ssh "${BOARD}" "bash -s" <<EOF
set -euo pipefail
mkdir -p ${REMOTE_ROOT}/ablation ${REMOTE_ROOT}/ablation/results ${REMOTE_ROOT}/scripts
python3 ${REMOTE_ROOT}/scripts/make_quantized_variants.py \\
  --base-npz ${REMOTE_ROOT}/mnist_10class_deployment.npz \\
  --bits 8,4,2 \\
  --out-dir ${REMOTE_ROOT}/ablation \\
  --prefix mnist_10class_deployment \\
  --summary-json ${REMOTE_ROOT}/ablation/g13_variants_summary.json

python3 ${REMOTE_ROOT}/scripts/run_g13_quant_ablation.py \\
  --inference-script ${REMOTE_ROOT}/tests/fpga_10class_inference.py \\
  --data-dir ${REMOTE_ROOT} \\
  --weights-dir ${REMOTE_ROOT}/ablation \\
  --weights-prefix mnist_10class_deployment \\
  --variants 8,4,2 \\
  --n ${N_IMAGES} \\
  --packet-id-width ${PACKET_ID_WIDTH} \\
  --pl-clock-hz ${PL_CLOCK_HZ} \\
  --out-dir ${REMOTE_ROOT}/ablation/results \\
  --sudo
EOF
else
  echo "[2/4] Skip G13 ablation (requested)"
fi

echo "[3/4] Collect board artifacts"
# G13 outputs
scp -r "${BOARD}:${REMOTE_ROOT}/ablation" "${LOCAL_BOARD_DIR}/" || true
# Canonical inference/energy outputs (if present)
scp "${BOARD}:${REMOTE_ROOT}/mnist_10class_results_pl_80m.json" "${LOCAL_BOARD_DIR}/" || true
scp "${BOARD}:${REMOTE_ROOT}/energy_metrics_g11_xpa.json" "${LOCAL_BOARD_DIR}/" || true
scp "${BOARD}:${REMOTE_ROOT}/power_active_g11.json" "${LOCAL_BOARD_DIR}/" || true

if [[ -n "${XPA_DYNAMIC_W}" ]]; then
  echo "[3.5/4] Recompute energy locally with explicit XPA dynamic power (${XPA_DYNAMIC_W} W)"
  if [[ -f "${LOCAL_BOARD_DIR}/mnist_10class_results_pl_80m.json" && -f "${LOCAL_BOARD_DIR}/power_active_g11.json" ]]; then
    python3 scripts/compute_energy_metrics.py \
      --inference-json "${LOCAL_BOARD_DIR}/mnist_10class_results_pl_80m.json" \
      --power-json "${LOCAL_BOARD_DIR}/power_active_g11.json" \
      --xpa-dynamic-w "${XPA_DYNAMIC_W}" \
      --output "${LOCAL_BOARD_DIR}/energy_metrics_g11_xpa_recomputed.json"
  else
    echo "[WARN] Missing local inference/power json; skip recompute"
  fi
fi

if [[ "${SKIP_BUNDLE}" == "0" ]]; then
  echo "[4/4] Create local reproducibility bundle (G14)"
  BUNDLE_CMD=(python3 scripts/make_repro_bundle.py --tar)

  [[ -f outputs/snn_integrated_v2.bit ]] && BUNDLE_CMD+=(--artifact outputs/snn_integrated_v2.bit)
  [[ -f outputs/snn_integrated_v2.hwh ]] && BUNDLE_CMD+=(--artifact outputs/snn_integrated_v2.hwh)
  [[ -f outputs/snn_integrated_v2_timing.rpt ]] && BUNDLE_CMD+=(--artifact outputs/snn_integrated_v2_timing.rpt)
  [[ -f outputs/snn_integrated_v2_utilization.rpt ]] && BUNDLE_CMD+=(--artifact outputs/snn_integrated_v2_utilization.rpt)
  [[ -f outputs/snn_integrated_v2_power.rpt ]] && BUNDLE_CMD+=(--artifact outputs/snn_integrated_v2_power.rpt)
  [[ -f ACCEPTANCE_CRITERIA.md ]] && BUNDLE_CMD+=(--artifact ACCEPTANCE_CRITERIA.md)
  [[ -f REPRODUCIBILITY.md ]] && BUNDLE_CMD+=(--artifact REPRODUCIBILITY.md)

  [[ -f "${LOCAL_BOARD_DIR}/mnist_10class_results_pl_80m.json" ]] && BUNDLE_CMD+=(--artifact "${LOCAL_BOARD_DIR}/mnist_10class_results_pl_80m.json")
  [[ -f "${LOCAL_BOARD_DIR}/energy_metrics_g11_xpa.json" ]] && BUNDLE_CMD+=(--artifact "${LOCAL_BOARD_DIR}/energy_metrics_g11_xpa.json")
  [[ -f "${LOCAL_BOARD_DIR}/energy_metrics_g11_xpa_recomputed.json" ]] && BUNDLE_CMD+=(--artifact "${LOCAL_BOARD_DIR}/energy_metrics_g11_xpa_recomputed.json")
  [[ -f "${LOCAL_BOARD_DIR}/ablation/results/g13_quant_ablation_summary.json" ]] && BUNDLE_CMD+=(--artifact "${LOCAL_BOARD_DIR}/ablation/results/g13_quant_ablation_summary.json")
  [[ -f "${LOCAL_BOARD_DIR}/ablation/results/g13_quant_ablation_summary.md" ]] && BUNDLE_CMD+=(--artifact "${LOCAL_BOARD_DIR}/ablation/results/g13_quant_ablation_summary.md")

  echo "[CMD] ${BUNDLE_CMD[*]}"
  "${BUNDLE_CMD[@]}"
else
  echo "[4/4] Skip reproducibility bundle (requested)"
fi

echo "[DONE] Board artifacts stored at: ${LOCAL_BOARD_DIR}"
