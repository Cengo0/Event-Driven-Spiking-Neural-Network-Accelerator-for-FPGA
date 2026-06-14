`timescale 1ns / 1ps

module tb_spikemold_scalar_id_guard;
    localparam HLS_NEURON_ID_WIDTH = 13;
    localparam GLOBAL_ID_WIDTH = 11;

    reg  [HLS_NEURON_ID_WIDTH-1:0] neuron_id;
    reg                            tvalid;
    wire [GLOBAL_ID_WIDTH-1:0]     global_id;
    wire [GLOBAL_ID_WIDTH-1:0]     direct_dest_id;
    wire                           id_in_range;
    wire                           invalid;
    wire                           flagged_compat_id;
    wire                           board_visible_compat_id;
    wire                           direct_id_accepted;
    wire                           routed_id_accepted;
    wire [GLOBAL_ID_WIDTH-1:0]     strict_global_id;
    wire [GLOBAL_ID_WIDTH-1:0]     strict_direct_dest_id;
    wire                           strict_id_in_range;
    wire                           strict_invalid;
    wire                           strict_flagged_compat_id;
    wire                           strict_board_visible_compat_id;
    wire                           strict_direct_id_accepted;
    wire                           strict_routed_id_accepted;

    integer pass_count = 0;
    integer fail_count = 0;

    spikemold_scalar_id_guard #(
        .HLS_NEURON_ID_WIDTH(HLS_NEURON_ID_WIDTH),
        .GLOBAL_ID_WIDTH(GLOBAL_ID_WIDTH),
        .HLS_DIRECT_TILE_COMPAT(1)
    ) dut (
        .neuron_id(neuron_id),
        .tvalid(tvalid),
        .global_id(global_id),
        .direct_dest_id(direct_dest_id),
        .id_in_range(id_in_range),
        .invalid(invalid),
        .flagged_compat_id(flagged_compat_id),
        .board_visible_compat_id(board_visible_compat_id),
        .direct_id_accepted(direct_id_accepted),
        .routed_id_accepted(routed_id_accepted)
    );

    spikemold_scalar_id_guard #(
        .HLS_NEURON_ID_WIDTH(HLS_NEURON_ID_WIDTH),
        .GLOBAL_ID_WIDTH(GLOBAL_ID_WIDTH),
        .HLS_DIRECT_TILE_COMPAT(1),
        .STRICT_PHYSICAL_ID_INGRESS(1)
    ) strict_dut (
        .neuron_id(neuron_id),
        .tvalid(tvalid),
        .global_id(strict_global_id),
        .direct_dest_id(strict_direct_dest_id),
        .id_in_range(strict_id_in_range),
        .invalid(strict_invalid),
        .flagged_compat_id(strict_flagged_compat_id),
        .board_visible_compat_id(strict_board_visible_compat_id),
        .direct_id_accepted(strict_direct_id_accepted),
        .routed_id_accepted(strict_routed_id_accepted)
    );

    task check;
        input [511:0] name;
        input condition;
        begin
            if (condition) begin
                pass_count = pass_count + 1;
                $display("[PASS] %0s", name);
            end else begin
                fail_count = fail_count + 1;
                $display("[FAIL] %0s", name);
            end
        end
    endtask

    initial begin
        $display("========================================");
        $display("HLS Scalar Spike ID Guard Testbench");
        $display("========================================");

        neuron_id = 0;
        tvalid = 1'b1;
        #1;
        check("id 0 in range", id_in_range == 1'b1);
        check("id 0 is board-visible direct", board_visible_compat_id == 1'b1 && direct_id_accepted == 1'b1);
        check("id 0 maps to dest 0", direct_dest_id == 0);
        check("id 0 does not route", routed_id_accepted == 1'b0);
        check("strict rejects scalar id 0", strict_invalid == 1'b1);
        check("strict id 0 is not accepted as in range", strict_id_in_range == 1'b0);
        check("strict id 0 reaches neither direct nor router", strict_direct_id_accepted == 1'b0 && strict_routed_id_accepted == 1'b0);

        neuron_id = 511;
        tvalid = 1'b1;
        #1;
        check("id 511 is board-visible direct", board_visible_compat_id == 1'b1 && direct_id_accepted == 1'b1);
        check("id 511 maps to dest 511", direct_dest_id == 511);
        check("strict rejects scalar id 511", strict_invalid == 1'b1);
        check("strict id 511 reaches neither direct nor router", strict_direct_id_accepted == 1'b0 && strict_routed_id_accepted == 1'b0);

        neuron_id = 512;
        tvalid = 1'b1;
        #1;
        check("id 512 is in range", id_in_range == 1'b1);
        check("id 512 is routed not direct", routed_id_accepted == 1'b1 && direct_id_accepted == 1'b0);
        check("strict rejects scalar id 512", strict_invalid == 1'b1);
        check("strict id 512 reaches neither direct nor router", strict_direct_id_accepted == 1'b0 && strict_routed_id_accepted == 1'b0);

        neuron_id = 1024;
        tvalid = 1'b1;
        #1;
        check("id 1024 is flagged direct", flagged_compat_id == 1'b1 && direct_id_accepted == 1'b1);
        check("id 1024 strips direct flag to dest 0", direct_dest_id == 0);
        check("strict rejects scalar id 1024", strict_invalid == 1'b1);
        check("strict disables scalar flagged form", strict_flagged_compat_id == 1'b0);

        neuron_id = 2047;
        tvalid = 1'b1;
        #1;
        check("id 2047 is in range", id_in_range == 1'b1);
        check("id 2047 direct maps to dest 1023", direct_id_accepted == 1'b1 && direct_dest_id == 1023);
        check("strict rejects scalar id 2047", strict_invalid == 1'b1);
        check("strict id 2047 reaches neither direct nor router", strict_direct_id_accepted == 1'b0 && strict_routed_id_accepted == 1'b0);

        neuron_id = 2048;
        tvalid = 1'b1;
        #1;
        check("id 2048 is invalid", invalid == 1'b1);
        check("id 2048 is rejected from direct", direct_id_accepted == 1'b0);
        check("id 2048 is rejected from router", routed_id_accepted == 1'b0);
        check("id 2048 does not alias to dest 0", !(direct_id_accepted && direct_dest_id == 0));
        check("strict rejects scalar id 2048", strict_invalid == 1'b1);
        check("strict id 2048 reaches neither direct nor router", strict_direct_id_accepted == 1'b0 && strict_routed_id_accepted == 1'b0);

        neuron_id = 4095;
        tvalid = 1'b1;
        #1;
        check("id 4095 is invalid", invalid == 1'b1);
        check("id 4095 is rejected", direct_id_accepted == 1'b0 && routed_id_accepted == 1'b0);
        check("strict rejects scalar id 4095", strict_invalid == 1'b1);
        check("strict id 4095 reaches neither direct nor router", strict_direct_id_accepted == 1'b0 && strict_routed_id_accepted == 1'b0);

        neuron_id = 2048;
        tvalid = 1'b0;
        #1;
        check("invalid held low when TVALID low", invalid == 1'b0);
        check("no routing when TVALID low", direct_id_accepted == 1'b0 && routed_id_accepted == 1'b0);
        check("strict invalid held low when TVALID low", strict_invalid == 1'b0);
        check("strict no routing when TVALID low", strict_direct_id_accepted == 1'b0 && strict_routed_id_accepted == 1'b0);

        $display("----------------------------------------");
        $display("Results: %0d PASS, %0d FAIL", pass_count, fail_count);
        if (fail_count == 0) begin
            $display("ALL TESTS PASSED");
        end else begin
            $display("SOME TESTS FAILED");
        end
        $finish;
    end
endmodule
