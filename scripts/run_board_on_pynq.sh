#!/bin/bash
# Run SpikeMold large-scale traces on PYNQ-Z2 board
# Usage: ssh pynq@pynq-z2.local "bash -s" < run_board_on_pynq.sh

set -e

echo "Running SpikeMold board execution on PYNQ-Z2"

# Check if PYNQ is installed
python3 -c "import pynq; print('PYNQ version:', pynq.__version__)" || {
    echo "ERROR: PYNQ not installed. Please install PYNQ first."
    exit 1
}

# Change to workspace directory
cd /home/xilinx/jupyter_notebooks

# Run the board execution script
python3 << 'PYTHON_EOF'
import json
from pathlib import Path
from spikepress.pynq_runtime import (
    SpikeMoldPynqRunConfig,
    run_spikemold_pynq_one_shot,
)

def load_trace(trace_path):
    return json.loads(Path(trace_path).read_text())

def trace_to_input_words(trace):
    inputs = trace.get("inputs", [])
    eventword64_inputs = []
    for inp in inputs:
        if inp.get("kind") == "input_spike":
            tick = inp.get("tick", 0)
            src_id = inp.get("src_id", 0)
            word = (0x1 << 60) | ((tick & 0xFFF) << 48) | (src_id & 0xFFFFFFF)
            eventword64_inputs.append(word)
    return eventword64_inputs

def run_trace_on_board(trace_path, bitstream_path, output_cap_words=1024):
    trace = load_trace(trace_path)
    input_words = trace_to_input_words(trace)

    print(f"Trace: {Path(trace_path).name}")
    print(f"  Input words: {len(input_words)}")
    print(f"  Updates: {trace['counters']['generated_update_count']}")
    print(f"  Commits: {trace['counters']['commit_count']}")

    config = SpikeMoldPynqRunConfig(
        bitstream_path=bitstream_path,
        ip_name="spikemold_top_hls_0",
        output_cap_words=output_cap_words,
    )

    result = run_spikemold_pynq_one_shot(input_words, config)
    return result.to_dict()

# Run MNIST trace
bitstream = "/home/xilinx/jupyter_notebooks/outputs/spikemold_pynq_z2_eventconv_20mhz.bit"
trace_path = "/home/xilinx/jupyter_notebooks/golden_traces/v1/mnist_fclif_784_512_10_v1.json"

result = run_trace_on_board(trace_path, bitstream)
print(f"\nResult: {'PASS' if result['ok'] else 'FAIL'}")
print(f"Input words: {result['input_word_count']}")
print(f"Output words: {result['output_word_count']}")
print(f"Counters: {result['counters']}")

# Save result
output_path = "/home/xilinx/jupyter_notebooks/outputs/board/mnist_fclif_784_512_10_board_result.json"
Path(output_path).parent.mkdir(parents=True, exist_ok=True)
Path(output_path).write_text(json.dumps(result, indent=2))
print(f"\nOutput saved to: {output_path}")
PYTHON_EOF
