`timescale 1ns / 1ps

module tb_snn_config_regs_output_diag;
    reg clk = 1'b0;
    always #6.25 clk = ~clk;

    reg rst_n;
    reg [6:0] awaddr;
    reg [2:0] awprot;
    reg awvalid;
    wire awready;
    reg [31:0] wdata;
    reg [3:0] wstrb;
    reg wvalid;
    wire wready;
    wire [1:0] bresp;
    wire bvalid;
    reg bready;
    reg [6:0] araddr;
    reg [2:0] arprot;
    reg arvalid;
    wire arready;
    wire [31:0] rdata;
    wire [1:0] rresp;
    wire rvalid;
    reg rready;

    reg [31:0] router_spike_count;
    reg [31:0] neuron_spike_count;
    reg fifo_overflow;
    reg [7:0] active_neurons;
    reg [31:0] throughput_counter;
    reg [31:0] service_cycles_counter;
    reg [31:0] pl_busy_cycles_counter;
    reg [31:0] output_drain_cycles_counter;
    reg [31:0] output_bridge_status;
    reg [31:0] output_bridge_drop_count;
    reg [31:0] output_bridge_event_count;
    reg [31:0] output_bridge_emit_count;

    wire router_config_we;
    wire [31:0] router_config_addr;
    wire [31:0] router_config_wdata;
    wire neuron_config_we;
    wire [9:0] neuron_config_addr;
    wire [31:0] neuron_config_wdata;
    wire [15:0] global_threshold;
    wire [7:0] global_leak_rate;
    wire [7:0] global_refrac_period;

    integer pass_count = 0;
    integer fail_count = 0;
    reg [31:0] read_value;

    snn_config_regs dut (
        .s_axi_aclk(clk),
        .s_axi_aresetn(rst_n),
        .s_axi_awaddr(awaddr),
        .s_axi_awprot(awprot),
        .s_axi_awvalid(awvalid),
        .s_axi_awready(awready),
        .s_axi_wdata(wdata),
        .s_axi_wstrb(wstrb),
        .s_axi_wvalid(wvalid),
        .s_axi_wready(wready),
        .s_axi_bresp(bresp),
        .s_axi_bvalid(bvalid),
        .s_axi_bready(bready),
        .s_axi_araddr(araddr),
        .s_axi_arprot(arprot),
        .s_axi_arvalid(arvalid),
        .s_axi_arready(arready),
        .s_axi_rdata(rdata),
        .s_axi_rresp(rresp),
        .s_axi_rvalid(rvalid),
        .s_axi_rready(rready),
        .router_config_we(router_config_we),
        .router_config_addr(router_config_addr),
        .router_config_wdata(router_config_wdata),
        .router_config_rdata(32'h11223344),
        .neuron_config_we(neuron_config_we),
        .neuron_config_addr(neuron_config_addr),
        .neuron_config_wdata(neuron_config_wdata),
        .global_threshold(global_threshold),
        .global_leak_rate(global_leak_rate),
        .global_refrac_period(global_refrac_period),
        .router_spike_count(router_spike_count),
        .neuron_spike_count(neuron_spike_count),
        .fifo_overflow(fifo_overflow),
        .active_neurons(active_neurons),
        .throughput_counter(throughput_counter),
        .service_cycles_counter(service_cycles_counter),
        .pl_busy_cycles_counter(pl_busy_cycles_counter),
        .output_drain_cycles_counter(output_drain_cycles_counter),
        .output_bridge_status(output_bridge_status),
        .output_bridge_drop_count(output_bridge_drop_count),
        .output_bridge_event_count(output_bridge_event_count),
        .output_bridge_emit_count(output_bridge_emit_count)
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

    task automatic axil_read;
        input [6:0] addr;
        output [31:0] value;
        begin
            @(negedge clk);
            araddr = addr;
            arvalid = 1'b1;
            rready = 1'b0;
            while (!arready) begin
                @(posedge clk);
            end
            @(posedge clk);
            @(negedge clk);
            arvalid = 1'b0;
            rready = 1'b1;
            while (!rvalid) begin
                @(posedge clk);
            end
            value = rdata;
            @(negedge clk);
            rready = 1'b0;
        end
    endtask

    initial begin
        rst_n = 1'b0;
        awaddr = 7'd0;
        awprot = 3'd0;
        awvalid = 1'b0;
        wdata = 32'd0;
        wstrb = 4'hF;
        wvalid = 1'b0;
        bready = 1'b0;
        araddr = 7'd0;
        arprot = 3'd0;
        arvalid = 1'b0;
        rready = 1'b0;
        router_spike_count = 32'd0;
        neuron_spike_count = 32'd0;
        fifo_overflow = 1'b1;
        active_neurons = 8'h5A;
        throughput_counter = 32'd0;
        service_cycles_counter = 32'd1234;
        pl_busy_cycles_counter = 32'd567;
        output_drain_cycles_counter = 32'd89;
        output_bridge_status = 32'h0000010B;
        output_bridge_drop_count = 32'd7;
        output_bridge_event_count = 32'd19;
        output_bridge_emit_count = 32'd12;

        repeat (3) @(posedge clk);
        @(negedge clk);
        rst_n = 1'b1;

        axil_read(7'h20, read_value);
        check("compatibility STATUS keeps router overflow at bit 0",
              read_value == {23'd0, active_neurons, fifo_overflow});

        axil_read(7'h2C, read_value);
        check("SERVICE_CYCLES returns service counter",
              read_value == service_cycles_counter);

        axil_read(7'h30, read_value);
        check("OUTPUT_BR_STATUS is a separate host-visible register",
              read_value == output_bridge_status);

        axil_read(7'h34, read_value);
        check("OUTPUT_BR_DROPS returns output bridge drop count",
              read_value == output_bridge_drop_count);

        axil_read(7'h38, read_value);
        check("OUTPUT_BR_EVENTS returns output bridge event count",
              read_value == output_bridge_event_count);

        axil_read(7'h3C, read_value);
        check("OUTPUT_BR_EMITS returns output bridge emit count",
              read_value == output_bridge_emit_count);

        axil_read(7'h40, read_value);
        check("PL_BUSY_CYCLES returns PL busy counter",
              read_value == pl_busy_cycles_counter);

        axil_read(7'h44, read_value);
        check("OUTPUT_DRAIN_CYCLES returns output drain counter",
              read_value == output_drain_cycles_counter);

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
