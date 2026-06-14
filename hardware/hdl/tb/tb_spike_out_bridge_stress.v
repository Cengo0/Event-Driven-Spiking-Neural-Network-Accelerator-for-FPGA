`timescale 1ns / 1ps

module tb_spike_out_bridge_stress;
    localparam HLS_NEURON_ID_WIDTH = 6;
    localparam HLS_MAX_NEURONS     = 16;
    localparam NEURON_ID_WIDTH     = 5;
    localparam WEIGHT_WIDTH        = 8;
    localparam FIFO_DEPTH          = 8;
    localparam STRESS_CYCLES       = 200;

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

    integer pass_count = 0;
    integer fail_count = 0;
    integer cycle;
    integer qidx;
    integer next_rand;

    reg [HLS_NEURON_ID_WIDTH-1:0] model_queue [0:FIFO_DEPTH-1];
    integer model_count;
    integer model_wr_ptr;
    integer model_rd_ptr;
    reg model_overflow;
    reg [31:0] model_event_count;
    reg [31:0] model_emit_count;
    reg [31:0] model_drop_count;
    reg model_prev_ready_token;
    reg model_prev_spike_valid;
    reg [NEURON_ID_WIDTH-1:0] model_prev_spike_id;

    reg model_push;
    reg model_pop;
    reg model_event;
    reg model_in_range;
    reg [HLS_NEURON_ID_WIDTH-1:0] model_id_hls;
    integer model_wr_ptr_next;
    integer model_rd_ptr_next;

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

    task automatic check;
        input [255:0] desc;
        input cond;
        begin
            if (cond) begin
                pass_count = pass_count + 1;
            end else begin
                fail_count = fail_count + 1;
                $display("[FAIL] cycle=%0d: %0s", cycle, desc);
            end
        end
    endtask

    task automatic model_reset;
        integer i;
        begin
            model_count = 0;
            model_wr_ptr = 0;
            model_rd_ptr = 0;
            model_overflow = 1'b0;
            model_event_count = 32'd0;
            model_emit_count = 32'd0;
            model_drop_count = 32'd0;
            model_prev_ready_token = 1'b0;
            model_prev_spike_valid = 1'b0;
            model_prev_spike_id = {NEURON_ID_WIDTH{1'b0}};
            for (i = 0; i < FIFO_DEPTH; i = i + 1) begin
                model_queue[i] = {HLS_NEURON_ID_WIDTH{1'b0}};
            end
        end
    endtask

    task automatic drive_random_inputs;
        begin
            @(negedge clk);
            next_rand = $urandom;
            if (next_rand[1:0] == 2'b00) begin
                neuron_spike_valid = 1'b0;
            end else begin
                neuron_spike_valid = 1'b1;
                neuron_spike_id = next_rand[6:2];
            end
            if (next_rand[7]) begin
                spike_out_ready_token = ~spike_out_ready_token;
            end
            clear = 1'b0;
            enable = 1'b1;
        end
    endtask

    task automatic drive_idle_cycle;
        begin
            @(negedge clk);
            neuron_spike_valid = 1'b0;
            clear = 1'b0;
            enable = 1'b1;
        end
    endtask

    task automatic update_model;
        begin
            if (!rst_n || clear || !enable) begin
                model_reset();
            end else begin
                model_id_hls =
                    {{(HLS_NEURON_ID_WIDTH-NEURON_ID_WIDTH){1'b0}}, neuron_spike_id};
                model_in_range = (model_id_hls < HLS_MAX_NEURONS[HLS_NEURON_ID_WIDTH-1:0]);
                model_event = neuron_spike_valid &&
                              (~model_prev_spike_valid || (neuron_spike_id != model_prev_spike_id));
                model_push = model_event && model_in_range;
                model_pop = ((spike_out_ready_token ^ model_prev_ready_token) && (model_count != 0));
                model_wr_ptr_next = (model_wr_ptr == FIFO_DEPTH - 1) ? 0 : (model_wr_ptr + 1);
                model_rd_ptr_next = (model_rd_ptr == FIFO_DEPTH - 1) ? 0 : (model_rd_ptr + 1);

                model_prev_ready_token = spike_out_ready_token;
                model_prev_spike_valid = neuron_spike_valid;
                if (neuron_spike_valid) begin
                    model_prev_spike_id = neuron_spike_id;
                end

                if (model_push && (model_count < FIFO_DEPTH)) begin
                    model_queue[model_wr_ptr] = model_id_hls;
                    model_wr_ptr = model_wr_ptr_next;
                end

                if (model_push && (model_count >= FIFO_DEPTH)) begin
                    model_overflow = 1'b1;
                end

                if (model_event) begin
                    model_event_count = model_event_count + 1;
                    if (!model_in_range || (model_count >= FIFO_DEPTH)) begin
                        model_drop_count = model_drop_count + 1;
                    end
                end

                if (model_pop) begin
                    model_rd_ptr = model_rd_ptr_next;
                    model_emit_count = model_emit_count + 1;
                end

                case ({(model_push && (model_count < FIFO_DEPTH)), model_pop})
                    2'b10: model_count = model_count + 1;
                    2'b01: model_count = model_count - 1;
                    default: model_count = model_count;
                endcase
            end
        end
    endtask

    task automatic check_outputs;
        begin
            #1;
            check("overflow flag matches scoreboard", fifo_overflow == model_overflow);
            check("FIFO level matches scoreboard", fifo_level == model_count);
            check("event counter matches scoreboard", output_event_count == model_event_count);
            check("emit counter matches scoreboard", output_emit_count == model_emit_count);
            check("drop counter matches scoreboard", output_drop_count == model_drop_count);
            if (spike_out_valid != (model_count != 0)) begin
                $display("[DEBUG] cycle=%0d valid mismatch: dut_valid=%0d model_valid=%0d dut_count=%0d model_count=%0d push=%0d pop=%0d event=%0d ready_token=%0d prev_ready=%0d",
                         cycle, spike_out_valid, (model_count != 0), dut.fifo_count, model_count,
                         model_push, model_pop, model_event, spike_out_ready_token,
                         model_prev_ready_token);
            end
            check("valid flag matches scoreboard", spike_out_valid == (model_count != 0));
            if (model_count != 0) begin
                check("output neuron id matches scoreboard head",
                      spike_out_neuron_id == model_queue[model_rd_ptr]);
                check("output weight stays unit-valued for spike event",
                      spike_out_weight == {{(WEIGHT_WIDTH-1){1'b0}}, 1'b1});
            end
        end
    endtask

    initial begin
        rst_n = 1'b0;
        enable = 1'b0;
        clear = 1'b0;
        neuron_spike_valid = 1'b0;
        neuron_spike_id = {NEURON_ID_WIDTH{1'b0}};
        spike_out_ready_token = 1'b0;
        model_reset();

        repeat (3) @(posedge clk);
        @(negedge clk);
        rst_n = 1'b1;
        enable = 1'b1;

        for (cycle = 0; cycle < STRESS_CYCLES; cycle = cycle + 1) begin
            if (cycle == 40) begin
                @(negedge clk);
                clear = 1'b1;
                neuron_spike_valid = 1'b1;
                neuron_spike_id = 5'd7;
                spike_out_ready_token = ~spike_out_ready_token;
            end else if (cycle == 41) begin
                @(negedge clk);
                clear = 1'b0;
                neuron_spike_valid = 1'b0;
            end else if (cycle >= 80 && cycle < 90) begin
                @(negedge clk);
                enable = 1'b0;
                clear = 1'b0;
                neuron_spike_valid = 1'b1;
                neuron_spike_id = cycle[NEURON_ID_WIDTH-1:0];
            end else if (cycle == 90) begin
                @(negedge clk);
                enable = 1'b1;
                neuron_spike_valid = 1'b0;
            end else if (cycle == 120) begin
                @(negedge clk);
                rst_n = 1'b0;
                neuron_spike_valid = 1'b1;
                neuron_spike_id = 5'd3;
            end else if (cycle == 121) begin
                @(negedge clk);
                rst_n = 1'b1;
                neuron_spike_valid = 1'b0;
            end else begin
                drive_random_inputs();
            end

            @(posedge clk);
            update_model();
            check_outputs();
        end

        for (qidx = 0; qidx < FIFO_DEPTH + 2; qidx = qidx + 1) begin
            @(negedge clk);
            neuron_spike_valid = 1'b0;
            enable = 1'b1;
            clear = 1'b0;
            if (model_count != 0) begin
                spike_out_ready_token = ~spike_out_ready_token;
            end
            @(posedge clk);
            cycle = STRESS_CYCLES + qidx;
            update_model();
            check_outputs();
        end

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
