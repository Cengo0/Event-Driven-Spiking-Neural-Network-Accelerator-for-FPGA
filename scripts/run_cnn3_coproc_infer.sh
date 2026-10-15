#!/bin/bash
# =============================================================================
# Run CNN3 SNN Hardware Co-Processing Inference on PYNQ-Z2
# =============================================================================
set -e

BITSTREAM="${1:-snn_core_group_v3.bit}"
DATA="${2:-mnist_cnn3_deployment.npz}"
SAMPLES="${3:-1000}"
THRESHOLD="${4:-120}"
OUTPUT="${5:-mnist_cnn3_coproc_results.json}"

echo "================================================================="
echo "  Starting CNN3 Hardware Co-Processing Inference (Option A)"
echo "================================================================="
echo "  Bitstream : $BITSTREAM"
echo "  Payload   : $DATA"
echo "  Samples   : $SAMPLES"
echo "  Threshold : $THRESHOLD"
echo "  Output    : $OUTPUT"
echo "================================================================="

python3 tests/fpga_cnn3_coproc_inference.py \
    --bitstream "$BITSTREAM" \
    --data "$DATA" \
    --samples "$SAMPLES" \
    --threshold "$THRESHOLD" \
    --output-json "$OUTPUT"

echo "Evaluation finished successfully."

