`timescale 1ns / 1ps

module wide_control_decode #(
    parameter NUM_GROUPS = 16
)(
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  cfg_we,
    input  wire [31:0]           cfg_addr,
    input  wire [31:0]           cfg_wdata,
    output reg                   accumulate_only,
    output reg  [NUM_GROUPS-1:0] commit_group_mask,
    output reg                   commit_start_pulse,
    output reg  [NUM_GROUPS-1:0] clear_group_mask,
    output reg                   clear_start_pulse
);

    wire wide_commit_cmd = cfg_we && (cfg_addr[31:28] == 4'hB);
    wire wide_clear_cmd = cfg_we && (cfg_addr[31:28] == 4'hD);
    wire commit_start = cfg_wdata[2];
    wire clear_start = cfg_wdata[16];
    wire [NUM_GROUPS-1:0] commit_mask_field_base = cfg_wdata[19:16];
    wire [NUM_GROUPS-1:0] commit_mask_field = commit_mask_field_base << 2;
    wire [NUM_GROUPS-1:0] commit_start_group_mask = cfg_wdata[2] ? 2 : 0;
    wire [NUM_GROUPS-1:0] decoded_commit_group_mask =
        commit_mask_field | commit_start_group_mask;

    always @(posedge clk) begin
        if (!rst_n) begin
            accumulate_only <= 1'b0;
            commit_group_mask <= {NUM_GROUPS{1'b1}};
            commit_start_pulse <= 1'b0;
            clear_group_mask <= {NUM_GROUPS{1'b0}};
            clear_start_pulse <= 1'b0;
        end else begin
            commit_start_pulse <= 1'b0;
            clear_start_pulse <= 1'b0;

            if (wide_commit_cmd) begin
                if (commit_start) begin
                    commit_group_mask <= decoded_commit_group_mask;
                    commit_start_pulse <= 1'b1;
                    accumulate_only <= 1'b0;
                end else begin
                    accumulate_only <= cfg_wdata[0];
                end
            end

            if (wide_clear_cmd) begin
                clear_group_mask <= cfg_wdata[NUM_GROUPS-1:0];
                clear_start_pulse <= clear_start;
            end
        end
    end

endmodule
