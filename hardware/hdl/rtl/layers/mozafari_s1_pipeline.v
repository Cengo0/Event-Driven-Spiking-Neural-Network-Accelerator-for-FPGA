//-----------------------------------------------------------------------------
// Title         : Mozafari S1 Layer Preprocessing Pipeline V2
// Project       : PYNQ-Z2 SNN Accelerator
// File          : mozafari_s1_pipeline.v
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : Complete S1 layer preprocessing pipeline for Mozafari R-STDP
//
//                 Pipeline stages:
//                 1. DoG Filter Bank (6 filters: 3 scales × 2 polarities)
//                 2. Intensity-to-Latency Encoder V2 (bin-packing method)
//                    - CRITICAL: Zero intensity = NO spike (not late spike!)
//                    - Ranking-based temporal encoding
//                 3. Pointwise Inhibition V2 (with first-spike time recording)
//                    - Records first spike TIME for STDP learning
//                    - Provides memory interface for downstream STDP engine
//                 
//                 Input: 28×28 grayscale image
//                 Output: Temporal spike tensor (SPARSE, not all positions spike)
//                 
//                 Key fix: Implements SpykeTorch-compatible encoding where
//                 low-intensity positions do NOT spike, enabling proper
//                 discrimination between inputs.
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps

module mozafari_s1_pipeline #(
    parameter INPUT_HEIGHT  = 28,
    parameter INPUT_WIDTH   = 28,
    parameter NUM_DOG_FILTERS = 6,
    parameter DATA_WIDTH    = 8,          // Input pixel precision
    parameter DOG_OUT_WIDTH = 16,         // DoG output precision
    parameter TIME_STEPS    = 15,         // Temporal resolution
    parameter TIME_WIDTH    = 4,          // log2(TIME_STEPS)
    parameter DOG_THRESHOLD = 50,         // DoG filter threshold
    parameter LATENCY_THRESHOLD = 10      // Minimum for spike generation
)(
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         enable,
    
    //=========================================================================
    // Control Interface
    //=========================================================================
    input  wire                         start,
    output wire                         done,
    output wire                         busy,
    
    //=========================================================================
    // Image Input (AXI-Stream)
    //=========================================================================
    input  wire                         s_axis_tvalid,
    input  wire [DATA_WIDTH-1:0]        s_axis_tdata,
    input  wire                         s_axis_tlast,
    output wire                         s_axis_tready,
    
    //=========================================================================
    // Spike Output (AXI-Stream with temporal info)
    //=========================================================================
    output wire                         m_axis_tvalid,
    output wire [TIME_WIDTH-1:0]        m_axis_tdata_time,
    output wire [$clog2(NUM_DOG_FILTERS)-1:0] m_axis_tdata_ch,
    output wire [$clog2(INPUT_HEIGHT)-1:0] m_axis_tdata_row,
    output wire [$clog2(INPUT_WIDTH)-1:0]  m_axis_tdata_col,
    output wire                         m_axis_tdata_valid_spike,  // Actually spiked
    output wire                         m_axis_tlast,
    input  wire                         m_axis_tready,
    
    //=========================================================================
    // Spike Memory Interface (for bulk read by downstream layers)
    //=========================================================================
    output wire                         spike_mem_wen,
    output wire [$clog2(TIME_STEPS*INPUT_HEIGHT*INPUT_WIDTH*NUM_DOG_FILTERS)-1:0] spike_mem_addr,
    output wire                         spike_mem_data,
    
    //=========================================================================
    // Configuration
    //=========================================================================
    input  wire [DOG_OUT_WIDTH-1:0]     cfg_max_intensity,
    
    //=========================================================================
    // Debug/Status
    //=========================================================================
    output wire [31:0]                  stat_pixels_in,
    output wire [31:0]                  stat_spikes_out,
    output wire [31:0]                  stat_filtered_out,
    output wire [1:0]                   pipeline_stage   // 0=idle, 1=dog, 2=encode, 3=inhibit
);

    //=========================================================================
    // Internal Signals
    //=========================================================================
    
    // DoG Filter Bank outputs
    wire                         dog_done;
    wire                         dog_busy;
    wire                         dog_pixel_valid;
    wire [DOG_OUT_WIDTH-1:0]     dog_pixel_data;
    wire [$clog2(NUM_DOG_FILTERS)-1:0] dog_pixel_ch;
    wire                         dog_pixel_last;
    wire                         dog_frame_last;
    wire                         dog_pixel_ready;
    wire [31:0]                  dog_nonzero;
    
    // Intensity-to-Latency outputs
    wire                         latency_done;
    wire                         latency_busy;
    wire                         latency_spike_valid;
    wire [TIME_WIDTH-1:0]        latency_spike_time;
    wire [$clog2(NUM_DOG_FILTERS)-1:0] latency_spike_ch;
    wire [$clog2(INPUT_HEIGHT)-1:0] latency_spike_row;
    wire [$clog2(INPUT_WIDTH)-1:0]  latency_spike_col;
    wire                         latency_no_spike;
    wire                         latency_frame_last;
    wire                         latency_spike_ready;
    wire [31:0]                  latency_total_spikes;
    
    // Pointwise Inhibition outputs
    wire                         inhibit_done;
    wire                         inhibit_busy;
    wire                         inhibit_spike_valid;
    wire [TIME_WIDTH-1:0]        inhibit_spike_time;
    wire [$clog2(NUM_DOG_FILTERS)-1:0] inhibit_spike_ch;
    wire [$clog2(INPUT_HEIGHT)-1:0] inhibit_spike_row;
    wire [$clog2(INPUT_WIDTH)-1:0]  inhibit_spike_col;
    wire                         inhibit_was_first;
    wire                         inhibit_frame_last;
    
    // Spike memory write signals
    wire                         inhibit_mem_write_en;
    wire [$clog2(TIME_STEPS)-1:0] inhibit_mem_time;
    wire [$clog2(INPUT_HEIGHT)-1:0] inhibit_mem_row;
    wire [$clog2(INPUT_WIDTH)-1:0]  inhibit_mem_col;
    wire [$clog2(NUM_DOG_FILTERS)-1:0] inhibit_mem_ch;
    
    //=========================================================================
    // Pipeline Control
    //=========================================================================
    reg [1:0] current_stage;
    reg pipeline_done;
    
    assign done = pipeline_done;
    assign busy = dog_busy | latency_busy | inhibit_busy;
    assign pipeline_stage = current_stage;
    
    // Statistics
    wire [31:0] dog_pixels_processed;
    assign stat_pixels_in = dog_pixels_processed;
    assign stat_filtered_out = dog_nonzero;
    assign stat_spikes_out = latency_total_spikes;
    
    //=========================================================================
    // Stage 1: DoG Filter Bank
    //=========================================================================
    dog_filter_bank #(
        .INPUT_HEIGHT(INPUT_HEIGHT),
        .INPUT_WIDTH(INPUT_WIDTH),
        .NUM_FILTERS(NUM_DOG_FILTERS),
        .DATA_WIDTH(DATA_WIDTH),
        .OUTPUT_WIDTH(DOG_OUT_WIDTH),
        .THRESHOLD(DOG_THRESHOLD)
    ) u_dog_filter (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .start(start),
        .done(dog_done),
        .busy(dog_busy),
        // Input
        .s_pixel_valid(s_axis_tvalid),
        .s_pixel_data(s_axis_tdata),
        .s_pixel_last(s_axis_tlast),
        .s_frame_last(1'b0),
        .s_pixel_ready(s_axis_tready),
        // Output
        .m_pixel_valid(dog_pixel_valid),
        .m_pixel_data(dog_pixel_data),
        .m_pixel_ch(dog_pixel_ch),
        .m_pixel_last(dog_pixel_last),
        .m_frame_last(dog_frame_last),
        .m_pixel_ready(dog_pixel_ready),
        // Stats
        .pixels_processed(dog_pixels_processed),
        .nonzero_outputs(dog_nonzero)
    );
    
    //=========================================================================
    // Stage 2: Intensity-to-Latency Encoder
    //=========================================================================
    intensity_to_latency #(
        .HEIGHT(INPUT_HEIGHT),
        .WIDTH(INPUT_WIDTH),
        .CHANNELS(NUM_DOG_FILTERS),
        .DATA_WIDTH(DOG_OUT_WIDTH),
        .TIME_STEPS(TIME_STEPS),
        .TIME_WIDTH(TIME_WIDTH),
        .THRESHOLD(LATENCY_THRESHOLD),
        .MODE("LINEAR")
    ) u_latency_encoder (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .start(dog_done),  // Chain to DoG completion
        .done(latency_done),
        .busy(latency_busy),
        // Input from DoG
        .s_intensity_valid(dog_pixel_valid),
        .s_intensity_data(dog_pixel_data),
        .s_intensity_ch(dog_pixel_ch),
        .s_frame_last(dog_frame_last),
        .s_intensity_ready(dog_pixel_ready),
        // Output
        .m_spike_valid(latency_spike_valid),
        .m_spike_time(latency_spike_time),
        .m_spike_ch(latency_spike_ch),
        .m_spike_row(latency_spike_row),
        .m_spike_col(latency_spike_col),
        .m_no_spike(latency_no_spike),
        .m_frame_last(latency_frame_last),
        .m_spike_ready(latency_spike_ready),
        // Config
        .max_intensity(cfg_max_intensity),
        .alpha(8'd16),
        // Stats
        .total_spikes(latency_total_spikes)
    );
    
    //=========================================================================
    // Stage 3: Pointwise Inhibition
    //=========================================================================
    pointwise_inhibition #(
        .HEIGHT(INPUT_HEIGHT),
        .WIDTH(INPUT_WIDTH),
        .CHANNELS(NUM_DOG_FILTERS),
        .TIME_STEPS(TIME_STEPS),
        .TIME_WIDTH(TIME_WIDTH)
    ) u_pointwise_inhibit (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .start(latency_done),  // Chain to latency encoder completion
        .done(inhibit_done),
        .busy(inhibit_busy),
        // Input from Latency Encoder
        .s_spike_valid(latency_spike_valid & ~latency_no_spike),
        .s_spike_time(latency_spike_time),
        .s_spike_ch(latency_spike_ch),
        .s_spike_row(latency_spike_row),
        .s_spike_col(latency_spike_col),
        .s_frame_last(latency_frame_last),
        .s_spike_ready(latency_spike_ready),
        // Output
        .m_spike_valid(inhibit_spike_valid),
        .m_spike_time(inhibit_spike_time),
        .m_spike_ch(inhibit_spike_ch),
        .m_spike_row(inhibit_spike_row),
        .m_spike_col(inhibit_spike_col),
        .m_was_first(inhibit_was_first),
        .m_frame_last(inhibit_frame_last),
        .m_spike_ready(m_axis_tready)
    );
    
    //=========================================================================
    // Output Assignment
    //=========================================================================
    assign m_axis_tvalid = inhibit_spike_valid;
    assign m_axis_tdata_time = inhibit_spike_time;
    assign m_axis_tdata_ch = inhibit_spike_ch;
    assign m_axis_tdata_row = inhibit_spike_row;
    assign m_axis_tdata_col = inhibit_spike_col;
    assign m_axis_tdata_valid_spike = inhibit_was_first;  // Only first spikes pass
    assign m_axis_tlast = inhibit_frame_last;
    
    //=========================================================================
    // Spike Memory Write
    // Address = time * (H*W*C) + row * (W*C) + col * C + ch
    //=========================================================================
    assign spike_mem_wen = inhibit_spike_valid & inhibit_was_first & m_axis_tready;
    assign spike_mem_addr = inhibit_spike_time * (INPUT_HEIGHT * INPUT_WIDTH * NUM_DOG_FILTERS) +
                           inhibit_spike_row * (INPUT_WIDTH * NUM_DOG_FILTERS) +
                           inhibit_spike_col * NUM_DOG_FILTERS +
                           inhibit_spike_ch;
    assign spike_mem_data = 1'b1;
    
    //=========================================================================
    // Pipeline Stage Tracking
    //=========================================================================
    always @(posedge clk) begin
        if (!rst_n) begin
            current_stage <= 2'd0;
            pipeline_done <= 1'b0;
        end else if (enable) begin
            pipeline_done <= 1'b0;
            
            if (start) begin
                current_stage <= 2'd1;
            end else if (dog_done && !latency_busy) begin
                current_stage <= 2'd2;
            end else if (latency_done && !inhibit_busy) begin
                current_stage <= 2'd3;
            end else if (inhibit_done) begin
                current_stage <= 2'd0;
                pipeline_done <= 1'b1;
            end
        end
    end

endmodule


//-----------------------------------------------------------------------------
// Top-level Integration with AXI4-Lite Control
//-----------------------------------------------------------------------------
module mozafari_s1_axi_wrapper #(
    parameter INPUT_HEIGHT  = 28,
    parameter INPUT_WIDTH   = 28,
    parameter NUM_DOG_FILTERS = 6,
    parameter TIME_STEPS    = 15,
    parameter C_S_AXI_DATA_WIDTH = 32,
    parameter C_S_AXI_ADDR_WIDTH = 6
)(
    input  wire                         aclk,
    input  wire                         aresetn,
    
    //=========================================================================
    // AXI4-Lite Control Interface
    //=========================================================================
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]   s_axi_awaddr,
    input  wire                            s_axi_awvalid,
    output wire                            s_axi_awready,
    input  wire [C_S_AXI_DATA_WIDTH-1:0]   s_axi_wdata,
    input  wire [C_S_AXI_DATA_WIDTH/8-1:0] s_axi_wstrb,
    input  wire                            s_axi_wvalid,
    output wire                            s_axi_wready,
    output wire [1:0]                      s_axi_bresp,
    output wire                            s_axi_bvalid,
    input  wire                            s_axi_bready,
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]   s_axi_araddr,
    input  wire                            s_axi_arvalid,
    output wire                            s_axi_arready,
    output wire [C_S_AXI_DATA_WIDTH-1:0]   s_axi_rdata,
    output wire [1:0]                      s_axi_rresp,
    output wire                            s_axi_rvalid,
    input  wire                            s_axi_rready,
    
    //=========================================================================
    // AXI-Stream Input (Image pixels)
    //=========================================================================
    input  wire [7:0]                   s_axis_tdata,
    input  wire                         s_axis_tvalid,
    input  wire                         s_axis_tlast,
    output wire                         s_axis_tready,
    
    //=========================================================================
    // AXI-Stream Output (Temporal spikes)
    //=========================================================================
    output wire [31:0]                  m_axis_tdata,  // Packed spike info
    output wire                         m_axis_tvalid,
    output wire                         m_axis_tlast,
    input  wire                         m_axis_tready,
    
    //=========================================================================
    // Interrupt
    //=========================================================================
    output wire                         irq_done
);

    //=========================================================================
    // Register Map
    //=========================================================================
    // 0x00: Control (W) - bit0: start, bit1: enable, bit2: reset
    // 0x04: Status (R)  - bit0: done, bit1: busy, bit[3:2]: stage
    // 0x08: Config (RW) - max_intensity[15:0], thresholds
    // 0x0C: Stat0 (R)   - pixels_in
    // 0x10: Stat1 (R)   - spikes_out
    // 0x14: Stat2 (R)   - filtered_out
    
    reg [C_S_AXI_DATA_WIDTH-1:0] reg_control;
    reg [C_S_AXI_DATA_WIDTH-1:0] reg_config;
    wire [C_S_AXI_DATA_WIDTH-1:0] reg_status;
    wire [31:0] stat_pixels, stat_spikes, stat_filtered;
    wire [1:0] stage;
    
    wire core_start;
    wire core_enable;
    wire core_done;
    wire core_busy;
    
    assign core_start = reg_control[0];
    assign core_enable = reg_control[1];
    assign reg_status = {28'b0, stage, core_busy, core_done};
    assign irq_done = core_done;
    
    // Core outputs
    wire [3:0] spike_time;
    wire [2:0] spike_ch;
    wire [4:0] spike_row, spike_col;
    wire spike_valid_flag;
    
    //=========================================================================
    // S1 Pipeline Core
    //=========================================================================
    mozafari_s1_pipeline #(
        .INPUT_HEIGHT(INPUT_HEIGHT),
        .INPUT_WIDTH(INPUT_WIDTH),
        .NUM_DOG_FILTERS(NUM_DOG_FILTERS),
        .TIME_STEPS(TIME_STEPS)
    ) u_s1_pipeline (
        .clk(aclk),
        .rst_n(aresetn),
        .enable(core_enable),
        .start(core_start),
        .done(core_done),
        .busy(core_busy),
        // Image input
        .s_axis_tvalid(s_axis_tvalid),
        .s_axis_tdata(s_axis_tdata),
        .s_axis_tlast(s_axis_tlast),
        .s_axis_tready(s_axis_tready),
        // Spike output
        .m_axis_tvalid(m_axis_tvalid),
        .m_axis_tdata_time(spike_time),
        .m_axis_tdata_ch(spike_ch),
        .m_axis_tdata_row(spike_row),
        .m_axis_tdata_col(spike_col),
        .m_axis_tdata_valid_spike(spike_valid_flag),
        .m_axis_tlast(m_axis_tlast),
        .m_axis_tready(m_axis_tready),
        // Config
        .cfg_max_intensity(reg_config[15:0]),
        // Stats
        .stat_pixels_in(stat_pixels),
        .stat_spikes_out(stat_spikes),
        .stat_filtered_out(stat_filtered),
        .pipeline_stage(stage)
    );
    
    // Pack spike output
    // [31:28] = time, [27:25] = ch, [24:20] = row, [19:15] = col, [0] = valid
    assign m_axis_tdata = {spike_time, spike_ch, spike_row, spike_col, 14'b0, spike_valid_flag};
    
    //=========================================================================
    // AXI4-Lite Interface (Simplified)
    //=========================================================================
    reg axi_awready, axi_wready, axi_bvalid;
    reg axi_arready, axi_rvalid;
    reg [C_S_AXI_DATA_WIDTH-1:0] axi_rdata;
    reg [C_S_AXI_ADDR_WIDTH-1:0] axi_awaddr, axi_araddr;
    
    assign s_axi_awready = axi_awready;
    assign s_axi_wready = axi_wready;
    assign s_axi_bresp = 2'b00;
    assign s_axi_bvalid = axi_bvalid;
    assign s_axi_arready = axi_arready;
    assign s_axi_rdata = axi_rdata;
    assign s_axi_rresp = 2'b00;
    assign s_axi_rvalid = axi_rvalid;
    
    // Write logic
    always @(posedge aclk) begin
        if (!aresetn) begin
            axi_awready <= 1'b0;
            axi_wready <= 1'b0;
            axi_bvalid <= 1'b0;
            reg_control <= 0;
            reg_config <= 32'h00FF0032;  // Default: max=255, threshold=50
        end else begin
            // Write address ready
            if (~axi_awready && s_axi_awvalid && s_axi_wvalid) begin
                axi_awready <= 1'b1;
                axi_awaddr <= s_axi_awaddr;
            end else begin
                axi_awready <= 1'b0;
            end
            
            // Write data ready
            if (~axi_wready && s_axi_awvalid && s_axi_wvalid) begin
                axi_wready <= 1'b1;
            end else begin
                axi_wready <= 1'b0;
            end
            
            // Write response
            if (axi_awready && s_axi_awvalid && axi_wready && s_axi_wvalid && ~axi_bvalid) begin
                axi_bvalid <= 1'b1;
                
                // Register write
                case (axi_awaddr[5:2])
                    4'h0: reg_control <= s_axi_wdata;
                    4'h2: reg_config <= s_axi_wdata;
                endcase
            end else if (s_axi_bready && axi_bvalid) begin
                axi_bvalid <= 1'b0;
            end
            
            // Auto-clear start bit
            if (reg_control[0]) begin
                reg_control[0] <= 1'b0;
            end
        end
    end
    
    // Read logic
    always @(posedge aclk) begin
        if (!aresetn) begin
            axi_arready <= 1'b0;
            axi_rvalid <= 1'b0;
            axi_rdata <= 0;
        end else begin
            if (~axi_arready && s_axi_arvalid) begin
                axi_arready <= 1'b1;
                axi_araddr <= s_axi_araddr;
            end else begin
                axi_arready <= 1'b0;
            end
            
            if (axi_arready && s_axi_arvalid && ~axi_rvalid) begin
                axi_rvalid <= 1'b1;
                
                case (axi_araddr[5:2])
                    4'h0: axi_rdata <= reg_control;
                    4'h1: axi_rdata <= reg_status;
                    4'h2: axi_rdata <= reg_config;
                    4'h3: axi_rdata <= stat_pixels;
                    4'h4: axi_rdata <= stat_spikes;
                    4'h5: axi_rdata <= stat_filtered;
                    default: axi_rdata <= 0;
                endcase
            end else if (axi_rvalid && s_axi_rready) begin
                axi_rvalid <= 1'b0;
            end
        end
    end

endmodule
