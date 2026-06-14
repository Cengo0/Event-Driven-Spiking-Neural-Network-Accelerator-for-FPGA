`timescale 1ns / 1ps

module tb_wide_control_decode;
    localparam NUM_GROUPS = 4;

    reg clk = 1'b0;
    always #6.25 clk = ~clk;

    reg rst_n;
    reg cfg_we;
    reg [31:0] cfg_addr;
    reg [31:0] cfg_wdata;
    wire accumulate_only;
    wire [NUM_GROUPS-1:0] commit_group_mask;
    wire commit_start_pulse;
    wire [NUM_GROUPS-1:0] clear_group_mask;
    wire clear_start_pulse;

    integer pass_count = 0;
    integer fail_count = 0;

    wide_control_decode #(
        .NUM_GROUPS(NUM_GROUPS)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .cfg_we(cfg_we),
        .cfg_addr(cfg_addr),
        .cfg_wdata(cfg_wdata),
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

    task automatic write_cfg;
        input [31:0] addr;
        input [31:0] data;
        begin
            @(negedge clk);
            cfg_addr = addr;
            cfg_wdata = data;
            cfg_we = 1'b1;
            @(negedge clk);
            cfg_we = 1'b0;
        end
    endtask

    initial begin
        rst_n = 1'b0;
        cfg_we = 1'b0;
        cfg_addr = 32'd0;
        cfg_wdata = 32'd0;

        repeat (3) @(posedge clk);
        @(negedge clk);
        rst_n = 1'b1;
        @(posedge clk);

        check("reset clears accumulate_only", accumulate_only == 1'b0);
        check("reset defaults commit mask to all groups", commit_group_mask == 4'hF);
        check("reset clears clear mask", clear_group_mask == 4'h0);
        check("reset clears start pulses", commit_start_pulse == 1'b0 && clear_start_pulse == 1'b0);

        write_cfg(32'h2000_0000, 32'hFFFF_FFFF);
        @(posedge clk);
        check("non-wide command does not alter accumulate_only", accumulate_only == 1'b0);
        check("non-wide command does not pulse commit or clear", commit_start_pulse == 1'b0 && clear_start_pulse == 1'b0);

        write_cfg(32'hB000_0000, 32'h0000_0001);
        @(posedge clk);
        check("0xB sets accumulate_only", accumulate_only == 1'b1);
        check("0xB without start does not pulse commit", commit_start_pulse == 1'b0);

        write_cfg(32'hB000_0000, 32'h0002_0014);
        @(posedge clk);
        check("0xB updates commit group mask", commit_group_mask == 4'hA);
        check("0xB commit_start is one-cycle high", commit_start_pulse == 1'b1);
        check("0xB can clear accumulate_only for commit", accumulate_only == 1'b0);
        @(posedge clk);
        check("commit_start pulse deasserts after one cycle", commit_start_pulse == 1'b0);

        write_cfg(32'hD000_0000, 32'h0001_0005);
        @(posedge clk);
        check("0xD updates clear group mask", clear_group_mask == 4'h5);
        check("0xD clear_start is one-cycle high", clear_start_pulse == 1'b1);
        check("0xD does not pulse commit_start", commit_start_pulse == 1'b0);
        @(posedge clk);
        check("clear_start pulse deasserts after one cycle", clear_start_pulse == 1'b0);

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
