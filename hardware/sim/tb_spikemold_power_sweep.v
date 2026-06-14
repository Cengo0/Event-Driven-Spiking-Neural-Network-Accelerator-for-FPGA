// hardware/sim/tb_spikemold_power_sweep.v
// Testbench for power analysis sweep (Spike Density vs Power)

`timescale 1ns / 1ps

module tb_spikemold_power_sweep;

    //-------------------------------------------------------------------------
    // Parameters
    //-------------------------------------------------------------------------
    parameter NUM_NEURONS       = 1024;    // Match implemented design
    parameter NEURON_ID_WIDTH   = 10;
    parameter WEIGHT_WIDTH      = 8;
    parameter MAX_FANOUT        = 32;

    //-------------------------------------------------------------------------
    // Signals
    //-------------------------------------------------------------------------
    reg clk;
    reg rst_n;
    reg enable;

    // Router input
    reg                         s_router_spike_valid;
    reg  [NEURON_ID_WIDTH-1:0]  s_router_spike_neuron_id;
    wire                        s_router_spike_ready;

    // Router to Neuron Array
    wire                        m_router_spike_valid;
    wire [NEURON_ID_WIDTH-1:0]  m_router_spike_dest_id;
    wire [WEIGHT_WIDTH-1:0]     m_router_spike_weight;
    wire                        m_router_spike_exc_inh;
    wire                        m_router_spike_ready;
    wire [31:0]                 router_cfg_readdata;

    //-------------------------------------------------------------------------
    // DUT 1: Spike Router
    //-------------------------------------------------------------------------
    spike_router #(
        .NUM_NEURONS(NUM_NEURONS),
        .MAX_FANOUT(MAX_FANOUT),
        .NEURON_ID_WIDTH(NEURON_ID_WIDTH)
    ) u_spike_router (
        .clk(clk),
        .rst_n(rst_n),
        .s_spike_valid(s_router_spike_valid),
        .s_spike_neuron_id(s_router_spike_neuron_id),
        .s_spike_ready(s_router_spike_ready),
        .m_spike_valid(m_router_spike_valid),
        .m_spike_dest_id(m_router_spike_dest_id),
        .m_spike_weight(m_router_spike_weight),
        .m_spike_exc_inh(m_router_spike_exc_inh),
        .m_spike_ready(m_router_spike_ready),
        .config_we(1'b0),
        .config_addr(32'b0),
        .config_data(32'b0),
        .config_cmd_valid(1'b0),
        .config_cmd_addr(32'b0),
        .config_cmd_data(32'b0),
        .config_readdata(router_cfg_readdata)
    );

    //-------------------------------------------------------------------------
    // DUT 2: Neuron Array
    //-------------------------------------------------------------------------
    lif_neuron_array #(
        .NUM_NEURONS(NUM_NEURONS),
        .NEURON_ID_WIDTH(NEURON_ID_WIDTH)
    ) u_neuron_array (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .s_axis_spike_valid(m_router_spike_valid),
        .s_axis_spike_dest_id(m_router_spike_dest_id),
        .s_axis_spike_weight(m_router_spike_weight),
        .s_axis_spike_exc_inh(m_router_spike_exc_inh),
        .s_axis_spike_ready(m_router_spike_ready),
        .global_threshold(16'd100),
        .global_leak_rate(8'd1),
        .global_refrac_period(8'd2)
    );

    //-------------------------------------------------------------------------
    // Stimulus
    //-------------------------------------------------------------------------
    initial clk = 0;
    always #5 clk = ~clk; // 100 MHz

    task generate_aer_stream;
        input real spike_prob;
        input integer n_steps;
        integer t, n;
        begin
            for (t = 0; t < n_steps; t = t + 1) begin
                for (n = 0; n < NUM_NEURONS; n = n + 1) begin
                    if ($urandom_range(0, 99) < spike_prob * 100) begin
                        @(posedge clk);
                        while (!s_router_spike_ready) @(posedge clk);
                        s_router_spike_neuron_id <= n;
                        s_router_spike_valid <= 1'b1;
                        @(posedge clk);
                        s_router_spike_valid <= 1'b0;
                    end
                end
                repeat(10) @(posedge clk); // inter-step gap
            end
        end
    endtask

    initial begin
        // Reset
        rst_n = 0;
        enable = 0;
        s_router_spike_valid = 0;
        s_router_spike_neuron_id = 0;
        #100;
        rst_n = 1;
        #100;
        enable = 1;
        #100;

        // VCD generation
        $dumpfile("power_sweep.vcd");
        $dumpvars(0, tb_spikemold_power_sweep);

        $display("--- Starting Spike Density Sweep: 10%% ---");
        generate_aer_stream(0.10, 50);

        #1000;
        $display("--- Starting Spike Density Sweep: 50%% ---");
        generate_aer_stream(0.50, 50);

        #1000;
        $display("--- Starting Spike Density Sweep: 90%% ---");
        generate_aer_stream(0.90, 50);

        #5000;
        $display("--- Simulation Complete ---");
        $finish;
    end

endmodule
