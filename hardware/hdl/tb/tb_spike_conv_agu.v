`timescale 1ns / 1ps

module tb_spike_conv_agu;
    localparam KERNEL_SIZE = 2;
    localparam INPUT_WIDTH = 3;
    localparam INPUT_HEIGHT = 3;
    localparam NUM_CHANNELS = 1;
    localparam OUTPUT_CHANNELS = 1;
    localparam STRIDE = 1;
    localparam PADDING = 0;
    localparam KERNEL_WEIGHT_BITS = 8;
    localparam KERNEL_WORDS = OUTPUT_CHANNELS * NUM_CHANNELS * KERNEL_SIZE * KERNEL_SIZE;

    reg clk = 1'b0;
    always #6.25 clk = ~clk;

    reg rst_n;
    reg enable;
    reg s_axis_spike_tvalid;
    reg [31:0] s_axis_spike_tdata;
    wire s_axis_spike_tready;
    wire m_axis_spike_tvalid;
    wire [31:0] m_axis_spike_tdata;
    reg m_axis_spike_tready;
    wire [KERNEL_WEIGHT_BITS-1:0] kernel_weight_out;
    reg [(KERNEL_WORDS*KERNEL_WEIGHT_BITS)-1:0] kernel_weight_flat;
    wire [31:0] conv_spikes_processed;
    wire [31:0] conv_updates_generated;
    wire [31:0] conv_address_errors;

    integer pass_count = 0;
    integer fail_count = 0;
    integer outputs_seen;
    integer cycles;
    reg [15:0] expected_dest [0:3];
    reg [15:0] expected_weight_idx [0:3];
    reg [7:0] expected_weight [0:3];

    spike_conv_agu #(
        .KERNEL_SIZE(KERNEL_SIZE),
        .INPUT_WIDTH(INPUT_WIDTH),
        .INPUT_HEIGHT(INPUT_HEIGHT),
        .NUM_CHANNELS(NUM_CHANNELS),
        .OUTPUT_CHANNELS(OUTPUT_CHANNELS),
        .STRIDE(STRIDE),
        .PADDING(PADDING),
        .KERNEL_WEIGHT_BITS(KERNEL_WEIGHT_BITS)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .s_axis_spike_tvalid(s_axis_spike_tvalid),
        .s_axis_spike_tdata(s_axis_spike_tdata),
        .s_axis_spike_tready(s_axis_spike_tready),
        .m_axis_spike_tvalid(m_axis_spike_tvalid),
        .m_axis_spike_tdata(m_axis_spike_tdata),
        .m_axis_spike_tready(m_axis_spike_tready),
        .kernel_weight_out(kernel_weight_out),
        .kernel_weight_flat(kernel_weight_flat),
        .conv_spikes_processed(conv_spikes_processed),
        .conv_updates_generated(conv_updates_generated),
        .conv_address_errors(conv_address_errors)
    );

    task automatic check;
        input [255:0] desc;
        input cond;
        begin
            if (cond) begin
                pass_count = pass_count + 1;
                $display("[PASS] %0s", desc);
            end else begin
                fail_count = fail_count + 1;
                $display("[FAIL] %0s", desc);
            end
        end
    endtask

    task automatic reset_dut;
        begin
            rst_n = 1'b0;
            enable = 1'b0;
            s_axis_spike_tvalid = 1'b0;
            s_axis_spike_tdata = 32'd0;
            m_axis_spike_tready = 1'b0;
            repeat (4) @(posedge clk);
            @(negedge clk);
            rst_n = 1'b1;
            enable = 1'b1;
            @(posedge clk);
            @(negedge clk);
        end
    endtask

    task automatic send_spike;
        input [7:0] x;
        input [7:0] y;
        input [7:0] channel;
        begin
            @(negedge clk);
            s_axis_spike_tdata = {x, y, channel, 8'd0};
            s_axis_spike_tvalid = 1'b1;
            @(posedge clk);
            check("input spike accepted in idle", s_axis_spike_tready == 1'b1);
            @(negedge clk);
            s_axis_spike_tvalid = 1'b0;
        end
    endtask

    initial begin
        kernel_weight_flat = {8'd4, 8'd3, 8'd2, 8'd1};
        expected_dest[0] = 16'd3;
        expected_dest[1] = 16'd2;
        expected_dest[2] = 16'd1;
        expected_dest[3] = 16'd0;
        expected_weight_idx[0] = 16'd0;
        expected_weight_idx[1] = 16'd1;
        expected_weight_idx[2] = 16'd2;
        expected_weight_idx[3] = 16'd3;
        expected_weight[0] = 8'd1;
        expected_weight[1] = 8'd2;
        expected_weight[2] = 8'd3;
        expected_weight[3] = 8'd4;

        reset_dut();

        check("AGU starts idle-ready", s_axis_spike_tready == 1'b1);
        send_spike(8'd1, 8'd1, 8'd0);

        m_axis_spike_tready = 1'b1;
        outputs_seen = 0;
        cycles = 0;
        while (outputs_seen < 4 && cycles < 40) begin
            @(posedge clk);
            #1;
            if (m_axis_spike_tvalid) begin
                check("trace-locked destination id",
                      m_axis_spike_tdata[31:16] == expected_dest[outputs_seen]);
                check("trace-locked weight index",
                      m_axis_spike_tdata[15:0] == expected_weight_idx[outputs_seen]);
                check("selected shared-kernel weight",
                      kernel_weight_out == expected_weight[outputs_seen]);
                outputs_seen = outputs_seen + 1;
            end
            cycles = cycles + 1;
        end

        check("AGU emitted four trace updates", outputs_seen == 4);
        repeat (4) @(posedge clk);
        #1;
        check("AGU returns to idle after scan", s_axis_spike_tready == 1'b1 && !m_axis_spike_tvalid);
        check("input spike counter matches trace", conv_spikes_processed == 32'd1);
        check("generated update counter matches trace", conv_updates_generated == 32'd4);
        check("center tiny case has no address errors", conv_address_errors == 32'd0);

        $display("Results: %0d PASS, %0d FAIL", pass_count, fail_count);
        if (fail_count == 0) begin
            $display("*** ALL TESTS PASSED ***");
        end else begin
            $display("*** SOME TESTS FAILED ***");
            $fatal(1);
        end
        $finish;
    end
endmodule
