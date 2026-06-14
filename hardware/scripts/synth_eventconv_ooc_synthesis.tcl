# Vivado OOC synthesis for EventConv SpikeMold blocks.
#
# This is board-free evidence. It does not build a bitstream or prove board
# runtime correctness.

set part [expr {[info exists ::env(SPIKEMOLD_PART)] ? $::env(SPIKEMOLD_PART) : "xc7z020clg400-1"}]
set script_dir [file dirname [file normalize [info script]]]
set repo_root  [file normalize [file join $script_dir "../.."]]
set rtl_dir    "${repo_root}/hardware/hdl/rtl"
set include_dir "${repo_root}/config/generated"
set output_dir "${repo_root}/outputs/synthesis/eventconv_ooc"
# Conservative OOC target for early PYNQ-Z2 evidence. Override with
# SPIKEMOLD_SYNTH_CLK_NS=8.000 for 125 MHz stress checks.
set clock_period_ns [expr {[info exists ::env(SPIKEMOLD_SYNTH_CLK_NS)] ? $::env(SPIKEMOLD_SYNTH_CLK_NS) : "50.000"}]

file mkdir $output_dir

proc synth_eventconv_block {name top sources generics} {
    global part include_dir output_dir clock_period_ns

    puts "===== Synthesizing ${name} (${top}) ====="
    create_project -in_memory -part $part
    set_property include_dirs [list $include_dir] [current_fileset]
    foreach src $sources {
        read_verilog $src
    }

    if {[llength $generics] > 0} {
        synth_design -top $top -part $part -mode out_of_context -generic $generics
    } else {
        synth_design -top $top -part $part -mode out_of_context
    }
    create_clock -period $clock_period_ns -name clk [get_ports clk]

    report_utilization -file "${output_dir}/${name}_utilization.rpt"
    report_timing_summary -delay_type max -file "${output_dir}/${name}_timing.rpt"
    write_checkpoint -force "${output_dir}/${name}.dcp"
    close_project
    puts "===== ${name} synthesis complete ====="
}

set eventconv_agu_generics [list \
    KERNEL_SIZE=3 \
    INPUT_WIDTH=8 \
    INPUT_HEIGHT=8 \
    NUM_CHANNELS=1 \
    OUTPUT_CHANNELS=1 \
    STRIDE=1 \
    PADDING=1 \
    KERNEL_WEIGHT_BITS=8 \
]

set eventconv_state_generics [list \
    STATE_COUNT=64 \
    DEST_ID_WIDTH=16 \
    STATE_WIDTH=16 \
    WEIGHT_WIDTH=8 \
]

set eventconv_commit_generics [list \
    STATE_COUNT=64 \
    DEST_ID_WIDTH=16 \
    STATE_WIDTH=16 \
]

synth_eventconv_block \
    "eventconv_agu_c4" \
    "spike_conv_agu" \
    [list "${rtl_dir}/core/spike_conv_agu.v"] \
    $eventconv_agu_generics

synth_eventconv_block \
    "eventconv_state_update_c4" \
    "spike_conv_state_update" \
    [list "${rtl_dir}/core/spike_conv_state_update.v"] \
    $eventconv_state_generics

synth_eventconv_block \
    "eventconv_active_commit_c4" \
    "spike_conv_active_commit" \
    [list "${rtl_dir}/core/spike_conv_active_commit.v"] \
    $eventconv_commit_generics

puts "===== EVENTCONV OOC SYNTHESIS COMPLETE ====="
