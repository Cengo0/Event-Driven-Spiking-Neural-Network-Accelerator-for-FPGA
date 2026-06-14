`timescale 1ns / 1ps

module tb_direct_axis_id_decoder;
    localparam HLS_NEURON_ID_WIDTH = 13;
    localparam GLOBAL_ID_WIDTH = 11;

    reg  [HLS_NEURON_ID_WIDTH-1:0] neuron_id;
    reg                            tvalid;
    reg                            tuser;
    wire [GLOBAL_ID_WIDTH-1:0]     dest_id;
    wire                           explicit_id_accepted;
    wire                           explicit_invalid;
    wire                           ingress_invalid;
    wire                           compat_id_in_range;
    wire                           flagged_compat_id;
    wire                           board_visible_compat_id;
    wire                           compat_id_accepted;
    wire                           direct_id_accepted;
    wire [GLOBAL_ID_WIDTH-1:0]     strict_dest_id;
    wire                           strict_explicit_id_accepted;
    wire                           strict_explicit_invalid;
    wire                           strict_ingress_invalid;
    wire                           strict_compat_id_in_range;
    wire                           strict_flagged_compat_id;
    wire                           strict_board_visible_compat_id;
    wire                           strict_compat_id_accepted;
    wire                           strict_direct_id_accepted;

    integer pass_count = 0;
    integer fail_count = 0;

    direct_axis_id_decoder #(
        .HLS_NEURON_ID_WIDTH(HLS_NEURON_ID_WIDTH),
        .GLOBAL_ID_WIDTH(GLOBAL_ID_WIDTH),
        .HLS_DIRECT_TILE_COMPAT(1)
    ) dut (
        .neuron_id(neuron_id),
        .tvalid(tvalid),
        .tuser(tuser),
        .dest_id(dest_id),
        .explicit_id_accepted(explicit_id_accepted),
        .explicit_invalid(explicit_invalid),
        .ingress_invalid(ingress_invalid),
        .compat_id_in_range(compat_id_in_range),
        .flagged_compat_id(flagged_compat_id),
        .board_visible_compat_id(board_visible_compat_id),
        .compat_id_accepted(compat_id_accepted),
        .direct_id_accepted(direct_id_accepted)
    );

    direct_axis_id_decoder #(
        .HLS_NEURON_ID_WIDTH(HLS_NEURON_ID_WIDTH),
        .GLOBAL_ID_WIDTH(GLOBAL_ID_WIDTH),
        .HLS_DIRECT_TILE_COMPAT(1),
        .STRICT_PHYSICAL_ID_INGRESS(1)
    ) strict_dut (
        .neuron_id(neuron_id),
        .tvalid(tvalid),
        .tuser(tuser),
        .dest_id(strict_dest_id),
        .explicit_id_accepted(strict_explicit_id_accepted),
        .explicit_invalid(strict_explicit_invalid),
        .ingress_invalid(strict_ingress_invalid),
        .compat_id_in_range(strict_compat_id_in_range),
        .flagged_compat_id(strict_flagged_compat_id),
        .board_visible_compat_id(strict_board_visible_compat_id),
        .compat_id_accepted(strict_compat_id_accepted),
        .direct_id_accepted(strict_direct_id_accepted)
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

    task check_explicit_id;
        input integer id;
        begin
            neuron_id = id[HLS_NEURON_ID_WIDTH-1:0];
            tvalid = 1'b1;
            tuser = 1'b1;
            #1;
            check("explicit direct accepted", direct_id_accepted == 1'b1);
            check("explicit direct not invalid", explicit_invalid == 1'b0);
            check("explicit direct preserves dest", dest_id == id[GLOBAL_ID_WIDTH-1:0]);
            check("strict explicit direct accepted", strict_direct_id_accepted == 1'b1);
            check("strict explicit direct not invalid", strict_ingress_invalid == 1'b0);
            check("strict explicit direct preserves dest", strict_dest_id == id[GLOBAL_ID_WIDTH-1:0]);
        end
    endtask

    initial begin
        $display("========================================");
        $display("Direct AXIS ID Decoder Testbench");
        $display("========================================");

        check_explicit_id(0);
        check_explicit_id(511);
        check_explicit_id(512);
        check_explicit_id(1023);
        check_explicit_id(1024);
        check_explicit_id(2047);

        neuron_id = 2048;
        tvalid = 1'b1;
        tuser = 1'b1;
        #1;
        check("explicit 2048 is invalid", explicit_invalid == 1'b1);
        check("explicit 2048 is rejected", direct_id_accepted == 1'b0);
        check("strict explicit 2048 is invalid", strict_ingress_invalid == 1'b1);
        check("strict explicit 2048 is rejected", strict_direct_id_accepted == 1'b0);

        neuron_id = 4095;
        tvalid = 1'b1;
        tuser = 1'b1;
        #1;
        check("explicit 4095 is invalid", explicit_invalid == 1'b1);
        check("explicit 4095 is rejected", direct_id_accepted == 1'b0);
        check("strict explicit 4095 is invalid", strict_ingress_invalid == 1'b1);
        check("strict explicit 4095 is rejected", strict_direct_id_accepted == 1'b0);

        neuron_id = 511;
        tvalid = 1'b1;
        tuser = 1'b0;
        #1;
        check("compatibility board-visible 511 accepted", direct_id_accepted == 1'b1);
        check("compatibility board-visible 511 preserves dest", dest_id == 511);
        check("strict rejects unmarked board-visible 511", strict_direct_id_accepted == 1'b0);
        check("strict marks unmarked board-visible 511 invalid", strict_ingress_invalid == 1'b1);
        check("strict disables board-visible compatibility form", strict_board_visible_compat_id == 1'b0);

        neuron_id = 512;
        tvalid = 1'b1;
        tuser = 1'b0;
        #1;
        check("compatibility unmarked 512 is not direct", direct_id_accepted == 1'b0);
        check("strict rejects unmarked 512", strict_direct_id_accepted == 1'b0);
        check("strict marks unmarked 512 invalid", strict_ingress_invalid == 1'b1);

        neuron_id = 1024;
        tvalid = 1'b1;
        tuser = 1'b0;
        #1;
        check("compatibility flagged 1024 accepted", direct_id_accepted == 1'b1);
        check("compatibility flagged 1024 strips flag", dest_id == 0);
        check("strict rejects compatibility flagged 1024", strict_direct_id_accepted == 1'b0);
        check("strict marks compatibility flagged 1024 invalid", strict_ingress_invalid == 1'b1);
        check("strict disables flagged compatibility form", strict_flagged_compat_id == 1'b0);

        neuron_id = 1535;
        tvalid = 1'b1;
        tuser = 1'b0;
        #1;
        check("compatibility flagged 1535 accepted", direct_id_accepted == 1'b1);
        check("compatibility flagged 1535 maps to 511", dest_id == 511);
        check("strict rejects compatibility flagged 1535", strict_direct_id_accepted == 1'b0);
        check("strict marks compatibility flagged 1535 invalid", strict_ingress_invalid == 1'b1);

        neuron_id = 2048;
        tvalid = 1'b1;
        tuser = 1'b0;
        #1;
        check("compatibility 2048 is out of range", compat_id_in_range == 1'b0);
        check("compatibility 2048 is rejected", direct_id_accepted == 1'b0);
        check("strict rejects unmarked 2048", strict_direct_id_accepted == 1'b0);
        check("strict marks unmarked 2048 invalid", strict_ingress_invalid == 1'b1);

        neuron_id = 1024;
        tvalid = 1'b0;
        tuser = 1'b1;
        #1;
        check("invalid when TVALID low does not accept", direct_id_accepted == 1'b0);
        check("strict invalid held low when TVALID low", strict_ingress_invalid == 1'b0);
        check("strict does not accept when TVALID low", strict_direct_id_accepted == 1'b0);

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
