#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

set +u
source /home/jwlee/miniconda3/etc/profile.d/conda.sh
conda activate fpga
source /tools/Xilinx/2025.2/Vivado/settings64.sh
set -u

rtk vivado -mode batch -source "$ROOT/hardware/scripts/synth_eventconv_ooc_synthesis.tcl"
