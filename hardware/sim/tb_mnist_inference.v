`timescale 1ns / 1ps

module tb_mnist_inference;
    parameter NUM_NEURONS       = 150;
    parameter NEURON_ID_WIDTH   = 10;
    parameter WEIGHT_WIDTH      = 8;

    reg clk;
    reg rst_n;
    reg enable;

    // Neuron Array Inputs (AXI-Stream Slave)
    reg                         s_valid;
    reg [NEURON_ID_WIDTH-1:0]   s_dest_id;
    reg [WEIGHT_WIDTH-1:0]      s_weight;
    reg                         s_exc_inh;
    wire                        s_ready;

    // Neuron Array Outputs (AXI-Stream Master)
    wire                        m_valid;
    wire [NEURON_ID_WIDTH-1:0]  m_neuron_id;
    reg                         m_ready;

    // DUT: Neuron Array
    lif_neuron_array #(
        .NUM_NEURONS(NUM_NEURONS),
        .NEURON_ID_WIDTH(NEURON_ID_WIDTH)
    ) u_neuron_array (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        // Input interface
        .s_axis_spike_valid(s_valid),
        .s_axis_spike_dest_id(s_dest_id),
        .s_axis_spike_weight(s_weight),
        .s_axis_spike_exc_inh(s_exc_inh),
        .s_axis_spike_ready(s_ready),
        // Output interface
        .m_axis_spike_valid(m_valid),
        .m_axis_spike_neuron_id(m_neuron_id),
        .m_axis_spike_ready(m_ready),
        // Config interface (unused in this simulation)
        .config_we(1'b0),
        .config_addr(10'd0),
        .config_data(32'd0),
        // Global parameters
        .global_threshold(16'd120), // HW Threshold
        .global_leak_rate(8'd0),
        .global_refrac_period(8'd0)
    );

    integer out_fd;
    integer cycle_count;
    integer image_id;

    initial begin
        clk = 0;
        cycle_count = 0;
        image_id = 0;
        out_fd = $fopen("sim_output_spikes.txt", "w");
        $fdisplay(out_fd, "Image_ID,Clock_Cycle,Neuron_ID");
    end

    always #5 clk = ~clk;
    always @(posedge clk) cycle_count = cycle_count + 1;

    // Memory array for hex file
    reg [31:0] spike_mem [0:499999];
    integer i;

    initial begin
        $readmemh("sim_input_spikes.hex", spike_mem);
        $dumpfile("mnist_inference.vcd");
        $dumpvars(0, tb_mnist_inference);

        rst_n = 0; enable = 0; s_valid = 0; m_ready = 1;
        #100;
        rst_n = 1; enable = 1;
        #100;

        for (i = 0; i < 500000; i = i + 1) begin
            if (spike_mem[i] === 32'hxxxxxxxx) begin
                $display("End of memory reached.");
                i = 500000; // Break loop
            end else if (spike_mem[i] == 32'hFFFFFFFF) begin
                $display("Image %0d complete.", image_id);
                // Wait for any remaining output spikes to drain before the next image
                #1000;
                image_id = image_id + 1;
                // Assert a soft reset to clear neuron potentials for the next image
                enable = 0; rst_n = 0; #20; rst_n = 1; enable = 1; #20;
            end else begin
                @(posedge clk);
                while (!s_ready) @(posedge clk);
                s_dest_id <= spike_mem[i][9:0];
                s_weight  <= spike_mem[i][17:10];
                s_exc_inh <= 1'b1;
                s_valid   <= 1'b1;
                @(posedge clk);
                s_valid <= 1'b0;
            end
        end

        $fclose(out_fd);
        $display("Simulation Complete.");
        $finish;
    end

    // Monitor the AXI-Stream master interface for output spikes
    always @(posedge clk) begin
        if (rst_n && enable) begin
            // If the array outputs a valid spike and the receiver is ready
            if (m_valid && m_ready) begin
                $fdisplay(out_fd, "%0d,%0d,%0d", image_id, cycle_count, m_neuron_id);
            end
        end
    end

endmodule