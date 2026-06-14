`timescale 1ns / 1ps

module tb_wide_control_config_regs;
    localparam NUM_GROUPS = 4;

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

    wire router_config_we;
    wire [31:0] router_config_addr;
    wire [31:0] router_config_wdata;
    wire neuron_config_we;
    wire [9:0] neuron_config_addr;
    wire [31:0] neuron_config_wdata;
    wire [15:0] global_threshold;
    wire [7:0] global_leak_rate;
    wire [7:0] global_refrac_period;

    wire accumulate_only;
    wire [NUM_GROUPS-1:0] commit_group_mask;
    wire commit_start_pulse;
    wire [NUM_GROUPS-1:0] clear_group_mask;
    wire clear_start_pulse;

    reg saw_neuron_config_we;
    integer pass_count = 0;
    integer fail_count = 0;

    snn_config_regs u_regs (
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
        .router_config_rdata(32'h0),
        .neuron_config_we(neuron_config_we),
        .neuron_config_addr(neuron_config_addr),
        .neuron_config_wdata(neuron_config_wdata),
        .global_threshold(global_threshold),
        .global_leak_rate(global_leak_rate),
        .global_refrac_period(global_refrac_period),
        .router_spike_count(32'd0),
        .neuron_spike_count(32'd0),
        .fifo_overflow(1'b0),
        .active_neurons(8'd0),
        .throughput_counter(32'd0),
        .service_cycles_counter(32'd0),
        .pl_busy_cycles_counter(32'd0),
        .output_drain_cycles_counter(32'd0),
        .output_bridge_status(32'd0),
        .output_bridge_drop_count(32'd0),
        .output_bridge_event_count(32'd0),
        .output_bridge_emit_count(32'd0)
    );

    wide_control_decode #(
        .NUM_GROUPS(NUM_GROUPS)
    ) u_decode (
        .clk(clk),
        .rst_n(rst_n),
        .cfg_we(router_config_we),
        .cfg_addr(router_config_addr),
        .cfg_wdata(router_config_wdata),
        .accumulate_only(accumulate_only),
        .commit_group_mask(commit_group_mask),
        .commit_start_pulse(commit_start_pulse),
        .clear_group_mask(clear_group_mask),
        .clear_start_pulse(clear_start_pulse)
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

    task automatic axil_write;
        input [6:0] addr;
        input [31:0] value;
        begin
            @(negedge clk);
            awaddr = addr;
            wdata = value;
            awvalid = 1'b1;
            wvalid = 1'b1;
            bready = 1'b1;
            while (!awready || !wready) begin
                @(posedge clk);
            end
            @(negedge clk);
            awvalid = 1'b0;
            wvalid = 1'b0;
            while (!bvalid) begin
                @(posedge clk);
            end
            @(negedge clk);
            bready = 1'b0;
        end
    endtask

    always @(posedge clk) begin
        if (!rst_n) begin
            saw_neuron_config_we <= 1'b0;
        end else if (neuron_config_we) begin
            saw_neuron_config_we <= 1'b1;
        end
    end

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

        repeat (3) @(posedge clk);
        @(negedge clk);
        rst_n = 1'b1;
        @(posedge clk);

        check("reset leaves router target selected", !neuron_config_we);
        check("reset clears accumulate_only", accumulate_only == 1'b0);

        axil_write(7'h00, 32'h0000_0000);
        axil_write(7'h04, 32'hB000_0000);
        axil_write(7'h08, 32'h0000_0001);
        @(posedge clk);
        @(posedge clk);
        check("AXI writes route 0xB accumulate_only", accumulate_only == 1'b1);
        check("AXI 0xB without start has no commit pulse", commit_start_pulse == 1'b0);
        check("AXI 0xB keeps router_config address", router_config_addr == 32'hB000_0000);
        check("AXI 0xB keeps router_config data", router_config_wdata == 32'h0000_0001);
        check("router target does not assert neuron_config_we", saw_neuron_config_we == 1'b0);

        axil_write(7'h04, 32'hB000_0000);
        axil_write(7'h08, 32'h0002_0014);
        @(posedge clk);
        check("AXI 0xB commit mask reaches decoder", commit_group_mask == 4'hA);
        check("AXI 0xB commit_start pulses", commit_start_pulse == 1'b1);
        check("AXI 0xB clears accumulate_only for commit", accumulate_only == 1'b0);
        @(posedge clk);
        check("AXI 0xB commit_start deasserts", commit_start_pulse == 1'b0);

        axil_write(7'h04, 32'hD000_0000);
        axil_write(7'h08, 32'h0001_0005);
        @(posedge clk);
        check("AXI 0xD clear mask reaches decoder", clear_group_mask == 4'h5);
        check("AXI 0xD clear_start pulses", clear_start_pulse == 1'b1);
        check("AXI 0xD does not pulse commit_start", commit_start_pulse == 1'b0);
        @(posedge clk);
        check("AXI 0xD clear_start deasserts", clear_start_pulse == 1'b0);

        axil_write(7'h00, 32'h0000_0001);
        axil_write(7'h04, 32'hB000_0000);
        axil_write(7'h08, 32'h0002_0002);
        @(posedge clk);
        @(posedge clk);
        check("neuron target does not drive router commit pulse", commit_start_pulse == 1'b0);
        check("neuron target preserves previous router commit mask", commit_group_mask == 4'hA);
        check("neuron target asserts neuron_config_we path", saw_neuron_config_we == 1'b1);
        check("neuron target keeps low address bits for neuron path", neuron_config_addr == 10'h000);

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
