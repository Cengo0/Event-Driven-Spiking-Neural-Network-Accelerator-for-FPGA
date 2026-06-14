`timescale 1ns / 1ps

module tb_spike_out_bridge;
    localparam HLS_NEURON_ID_WIDTH = 6;
    localparam HLS_MAX_NEURONS     = 16;
    localparam NEURON_ID_WIDTH     = 5;
    localparam WEIGHT_WIDTH        = 8;
    localparam FIFO_DEPTH          = 8;

    reg clk = 1'b0;
    always #6.25 clk = ~clk;

    reg rst_n;
    reg enable;
    reg clear;
    reg neuron_spike_valid;
    reg [NEURON_ID_WIDTH-1:0] neuron_spike_id;
    reg spike_out_ready_token;

    wire spike_out_valid;
    wire [HLS_NEURON_ID_WIDTH-1:0] spike_out_neuron_id;
    wire [WEIGHT_WIDTH-1:0] spike_out_weight;
    wire neuron_spike_event;
    wire fifo_overflow;
    wire [31:0] fifo_level;
    wire [31:0] output_event_count;
    wire [31:0] output_emit_count;
    wire [31:0] output_drop_count;
    reg axis_neuron_spike_valid;
    reg [NEURON_ID_WIDTH-1:0] axis_neuron_spike_id;
    reg axis_tready;
    wire axis_spike_out_valid;
    wire [HLS_NEURON_ID_WIDTH-1:0] axis_spike_out_neuron_id;
    wire [WEIGHT_WIDTH-1:0] axis_spike_out_weight;
    wire axis_neuron_spike_event;
    wire [31:0] axis_tdata;
    wire [3:0] axis_tkeep;
    wire [3:0] axis_tstrb;
    wire axis_tvalid;
    wire axis_tlast;
    wire axis_tid;
    wire axis_tdest;
    wire axis_tuser;
    wire axis_fifo_overflow;
    wire [31:0] axis_fifo_level;
    wire [31:0] axis_output_event_count;
    wire [31:0] axis_output_emit_count;
    wire [31:0] axis_output_drop_count;

    integer pass_count = 0;
    integer fail_count = 0;
    integer idx;

    reg [HLS_NEURON_ID_WIDTH-1:0] observed_id;
    reg [HLS_NEURON_ID_WIDTH-1:0] expected_id [0:FIFO_DEPTH-1];

    spike_out_bridge #(
        .HLS_NEURON_ID_WIDTH(HLS_NEURON_ID_WIDTH),
        .HLS_MAX_NEURONS    (HLS_MAX_NEURONS),
        .NEURON_ID_WIDTH    (NEURON_ID_WIDTH),
        .WEIGHT_WIDTH       (WEIGHT_WIDTH),
        .FIFO_DEPTH         (FIFO_DEPTH)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .clear(clear),
        .neuron_spike_valid(neuron_spike_valid),
        .neuron_spike_id(neuron_spike_id),
        .spike_out_ready_token(spike_out_ready_token),
        .neuron_spike_event(neuron_spike_event),
        .spike_out_valid(spike_out_valid),
        .spike_out_neuron_id(spike_out_neuron_id),
        .spike_out_weight(spike_out_weight),
        .fifo_overflow(fifo_overflow),
        .fifo_level(fifo_level),
        .output_event_count(output_event_count),
        .output_emit_count(output_emit_count),
        .output_drop_count(output_drop_count)
    );

    spike_out_bridge #(
        .HLS_NEURON_ID_WIDTH(HLS_NEURON_ID_WIDTH),
        .HLS_MAX_NEURONS    (HLS_MAX_NEURONS),
        .NEURON_ID_WIDTH    (NEURON_ID_WIDTH),
        .WEIGHT_WIDTH       (WEIGHT_WIDTH),
        .FIFO_DEPTH         (FIFO_DEPTH),
        .OUTPUT_AXIS_ENABLE (1)
    ) dut_axis (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .clear(clear),
        .neuron_spike_valid(axis_neuron_spike_valid),
        .neuron_spike_id(axis_neuron_spike_id),
        .spike_out_ready_token(1'b0),
        .neuron_spike_event(axis_neuron_spike_event),
        .spike_out_valid(axis_spike_out_valid),
        .spike_out_neuron_id(axis_spike_out_neuron_id),
        .spike_out_weight(axis_spike_out_weight),
        .m_axis_tdata(axis_tdata),
        .m_axis_tkeep(axis_tkeep),
        .m_axis_tstrb(axis_tstrb),
        .m_axis_tvalid(axis_tvalid),
        .m_axis_tlast(axis_tlast),
        .m_axis_tready(axis_tready),
        .m_axis_tid(axis_tid),
        .m_axis_tdest(axis_tdest),
        .m_axis_tuser(axis_tuser),
        .fifo_overflow(axis_fifo_overflow),
        .fifo_level(axis_fifo_level),
        .output_event_count(axis_output_event_count),
        .output_emit_count(axis_output_emit_count),
        .output_drop_count(axis_output_drop_count)
    );

    task automatic check;
        input integer tnum;
        input [255:0] desc;
        input cond;
        begin
            if (cond) begin
                pass_count = pass_count + 1;
                $display("[PASS] Test %0d: %0s", tnum, desc);
            end else begin
                fail_count = fail_count + 1;
                $display("[FAIL] Test %0d: %0s", tnum, desc);
            end
        end
    endtask

    task automatic reset_dut;
        begin
            rst_n = 1'b0;
            enable = 1'b0;
            clear = 1'b0;
            neuron_spike_valid = 1'b0;
            neuron_spike_id = {NEURON_ID_WIDTH{1'b0}};
            spike_out_ready_token = 1'b0;
            axis_neuron_spike_valid = 1'b0;
            axis_neuron_spike_id = {NEURON_ID_WIDTH{1'b0}};
            axis_tready = 1'b0;
            repeat (3) @(posedge clk);
            @(negedge clk);
            rst_n = 1'b1;
            enable = 1'b1;
            @(posedge clk);
            @(negedge clk);
        end
    endtask

    task automatic emit_spike_pulse;
        input [NEURON_ID_WIDTH-1:0] nid;
        begin
            @(negedge clk);
            neuron_spike_valid = 1'b1;
            neuron_spike_id = nid;
            @(posedge clk);
            @(negedge clk);
            neuron_spike_valid = 1'b0;
            @(posedge clk);
            @(negedge clk);
        end
    endtask

    task automatic hold_spike;
        input [NEURON_ID_WIDTH-1:0] nid;
        input integer cycles;
        integer c;
        begin
            @(negedge clk);
            neuron_spike_valid = 1'b1;
            neuron_spike_id = nid;
            for (c = 0; c < cycles; c = c + 1) begin
                @(posedge clk);
            end
            @(negedge clk);
            neuron_spike_valid = 1'b0;
            @(posedge clk);
            @(negedge clk);
        end
    endtask

    task automatic emit_dense_stream;
        input integer count;
        input integer start_id;
        integer c;
        begin
            @(negedge clk);
            neuron_spike_valid = 1'b1;
            neuron_spike_id = start_id[NEURON_ID_WIDTH-1:0];
            @(posedge clk);
            for (c = 1; c < count; c = c + 1) begin
                @(negedge clk);
                neuron_spike_id = start_id + c;
                @(posedge clk);
            end
            @(negedge clk);
            neuron_spike_valid = 1'b0;
            @(posedge clk);
            @(negedge clk);
        end
    endtask

    task automatic ack_once;
        begin
            @(negedge clk);
            spike_out_ready_token = ~spike_out_ready_token;
            @(posedge clk);
            @(negedge clk);
        end
    endtask

    task automatic expect_head;
        input integer tnum;
        input [255:0] desc;
        input [HLS_NEURON_ID_WIDTH-1:0] exp_id;
        begin
            check(tnum, desc,
                  spike_out_valid &&
                  spike_out_neuron_id == exp_id &&
                  spike_out_weight == {{(WEIGHT_WIDTH-1){1'b0}}, 1'b1});
        end
    endtask

    task automatic drain_expect_prefix;
        input integer base_testnum;
        input integer count;
        integer c;
        begin
            for (c = 0; c < count; c = c + 1) begin
                observed_id = spike_out_neuron_id;
                check(base_testnum + c,
                      "dense bridge drains in-order without silent loss",
                      spike_out_valid && observed_id == expected_id[c]);
                ack_once();
            end
        end
    endtask

    initial begin
        reset_dut();

        check(1, "bridge starts empty after reset",
              !spike_out_valid && !fifo_overflow &&
              fifo_level == 0 && output_event_count == 0 &&
              output_emit_count == 0 && output_drop_count == 0);

        emit_spike_pulse(5);
        expect_head(2, "single spike becomes visible at output", 5);
        check(39, "single spike updates event count and FIFO level",
              output_event_count == 1 && output_emit_count == 0 &&
              output_drop_count == 0 && fifo_level == 1);
        ack_once();
        check(3, "single spike is consumed after ready toggle",
              !spike_out_valid && output_emit_count == 1 && fifo_level == 0);

        emit_spike_pulse(2);
        emit_spike_pulse(7);
        expect_head(4, "backpressure keeps first queued spike on output", 2);
        repeat (3) @(posedge clk);
        expect_head(5, "head remains stable while consumer is stalled", 2);
        ack_once();
        expect_head(6, "second spike appears after first consume", 7);
        ack_once();
        check(7, "two queued spikes fully drain", !spike_out_valid);

        hold_spike(9, 4);
        expect_head(8, "holding same payload high only captures one event", 9);
        ack_once();
        check(9, "held payload does not duplicate events", !spike_out_valid);

        @(negedge clk);
        neuron_spike_valid = 1'b1;
        neuron_spike_id = 3;
        @(posedge clk);
        @(negedge clk);
        neuron_spike_id = 4;
        @(posedge clk);
        @(negedge clk);
        neuron_spike_valid = 1'b0;
        @(posedge clk);
        expect_head(10, "payload change while valid stays high creates a new event", 3);
        ack_once();
        expect_head(11, "second changed payload is retained in order", 4);
        ack_once();

        emit_spike_pulse(20);
        check(12, "out-of-range spike is filtered",
              !spike_out_valid && output_drop_count == 1);

        for (idx = 0; idx < FIFO_DEPTH; idx = idx + 1) begin
            expected_id[idx] = idx[HLS_NEURON_ID_WIDTH-1:0];
        end
        emit_dense_stream(FIFO_DEPTH, 0);
        expect_head(13, "dense burst enters FIFO without immediate loss", 0);
        drain_expect_prefix(14, FIFO_DEPTH);
        check(22, "dense burst prefix drains completely", !spike_out_valid && !fifo_overflow);

        emit_dense_stream(FIFO_DEPTH + 2, 0);
        check(23, "overflow flag is asserted when dense burst exceeds FIFO depth", fifo_overflow);
        check(40, "overflowed dense burst increments drop count",
              output_drop_count == 3);
        drain_expect_prefix(24, FIFO_DEPTH);
        check(32, "overflow drops only excess tail and leaves no phantom outputs",
              !spike_out_valid);

        emit_spike_pulse(6);
        emit_spike_pulse(7);
        check(33, "queue refills before clear", spike_out_valid);
        @(negedge clk);
        clear = 1'b1;
        @(posedge clk);
        @(negedge clk);
        clear = 1'b0;
        @(posedge clk);
        check(34, "clear flushes queued spikes and overflow state",
              !spike_out_valid && !fifo_overflow &&
              fifo_level == 0 && output_event_count == 0 &&
              output_emit_count == 0 && output_drop_count == 0);

        emit_spike_pulse(1);
        expect_head(35, "first spike visible before simultaneous push/pop", 1);
        @(negedge clk);
        neuron_spike_valid = 1'b1;
        neuron_spike_id = 2;
        spike_out_ready_token = ~spike_out_ready_token;
        @(posedge clk);
        @(negedge clk);
        neuron_spike_valid = 1'b0;
        @(posedge clk);
        expect_head(36, "simultaneous consume and enqueue preserves next spike", 2);
        ack_once();
        check(37, "queue drains after simultaneous push/pop case", !spike_out_valid);

        @(negedge clk);
        enable = 1'b0;
        emit_spike_pulse(3);
        check(38, "disabled bridge ignores incoming spikes", !spike_out_valid);
        @(negedge clk);
        enable = 1'b1;

        @(negedge clk);
        axis_neuron_spike_valid = 1'b1;
        axis_neuron_spike_id = 5;
        axis_tready = 1'b0;
        @(posedge clk);
        @(negedge clk);
        axis_neuron_spike_valid = 1'b0;
        @(posedge clk);
        #1;
        check(41, "AXIS mode emits standard spike packet weight/id layout",
              !axis_spike_out_valid &&
              axis_tvalid &&
              axis_tdata == ((32'd1 << HLS_NEURON_ID_WIDTH) | 32'd5) &&
              axis_tkeep == 4'hF && axis_tstrb == 4'hF && axis_tlast == 1'b0);
        @(negedge clk);
        axis_tready = 1'b1;
        @(posedge clk);
        @(negedge clk);
        axis_tready = 1'b0;
        @(posedge clk);
        #1;
        check(42, "AXIS mode pops on tvalid/tready handshake",
              !axis_tvalid && axis_output_emit_count == 1 && axis_fifo_level == 0);

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
