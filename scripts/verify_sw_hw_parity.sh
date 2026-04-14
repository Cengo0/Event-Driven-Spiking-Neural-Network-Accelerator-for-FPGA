#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

export PYTHONPATH="${ROOT_DIR}/software/python:${PYTHONPATH:-}"

echo "[1/3] Running SW/HW parity pytest set"
python3 -m pytest -q \
  software/python/tests/test_hls_stdp_trace_parity.py \
  software/python/tests/test_stdp_checkpoint_decode.py \
  software/python/tests/test_rtl_cross_verification.py \
  software/python/tests/test_hw_python_identity.py \
  software/python/tests/test_weight_index_cross_verify.py

echo "[2/3] Running XRT control-path regression tests"
python3 -m pytest -q \
  software/python/tests/test_xrt_backend_register_map.py \
  software/python/tests/test_xrt_backend_runtime.py \
  software/python/tests/test_accelerator_xrt_encoder.py

echo "[3/3] Running RTL top-level syntax check (iverilog)"
if command -v iverilog >/dev/null 2>&1; then
  iverilog -g2012 -tnull -i -Iconfig/generated \
    -s snn_core_group_top hardware/hdl/rtl/top/snn_core_group_top.v
  echo "iverilog syntax check passed"
else
  echo "iverilog not found: skipping RTL syntax check"
fi

echo "SW/HW parity verification completed"
