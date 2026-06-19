//-----------------------------------------------------------------------------
// Title         : SpikeMold Configuration Register File (AXI4-Lite Slave)
// Project       : SpikeMold (HW) + SpikePress (SW)
// File          : spikemold_config_regs.v
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : AXI4-Lite slave register file for runtime configuration
//                 of the SpikeMold backend's RTL modules (event routing and
//                 LIF neuron array). Provides PS-accessible registers for:
//                 - Fabric/neuron connectivity programming
//                 - Global neuron parameter tuning
//                 - Performance monitoring and status readback
//
// Register Map (32-bit registers, byte-addressed):
//   0x00  CONFIG_CTRL     [W]  [1:0] config_target (0=router, 1=neuron)
//   0x04  CONFIG_ADDR     [W]  [31:0] config address for target module
//   0x08  CONFIG_WDATA    [W]  [31:0] config write data (triggers config_we)
//   0x0C  CONFIG_RDATA    [R]  [31:0] config read data from router
//   0x10  NEURON_THRESHOLD[RW] [15:0] global firing threshold
//   0x14  NEURON_PARAMS   [RW] [7:0] leak_rate, [15:8] refrac_period
//   0x18  ROUTER_SPIKE_CNT[R]  [31:0] routed spike count
//   0x1C  NEURON_SPIKE_CNT[R]  [31:0] neuron spike count
//   0x20  STATUS          [R]  [0] fifo_overflow, [8:1] active_neurons
//   0x24  THROUGHPUT      [R]  [31:0] first-spike latency counter
//   0x28  VERSION         [R]  [31:0] = 0x534D3031 ("SM01")
//   0x2C  SERVICE_CYCLES  [R]  [31:0] service-time counter
//   0x30  OUTPUT_BR_STATUS[R]  [0] output FIFO overflow, [8:1] FIFO level, [9] FIFO nonempty
//   0x34  OUTPUT_BR_DROPS [R]  [31:0] output bridge dropped-event count
//   0x38  OUTPUT_BR_EVENTS[R]  [31:0] output bridge observed-event count
//   0x3C  OUTPUT_BR_EMITS [R]  [31:0] output bridge emitted-word count
//   0x40  PL_BUSY_CYCLES [R]  [31:0] PL/fabric busy-cycle counter
//   0x44  OUTPUT_DRAIN_CYCLES[R] [31:0] output-drain busy-cycle counter
//   0x48  STATE_CHECKSUM  [R]  [31:0] running membrane-state checksum
//   0x4C  BACKEND_MODE    [RW] [1:0] 0=flat FC-LIF, 1=EventConv smoke
//   0x50  EVENTCONV_SHAPE0[RW] [7:0] input_w, [15:8] input_h,
//                              [23:16] kernel_size, [31:24] state_count
//   0x54  EVENTCONV_KERNEL0[RW] packed 2x2 int8 kernel weights
//   0x58  EVENTCONV_DESC_STATUS[R] descriptor support/readback flags
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps

module spikemold_config_regs #(
    parameter C_S_AXI_ADDR_WIDTH = 7,
    parameter C_S_AXI_DATA_WIDTH = 32
)(
    //=========================================================================
    // AXI4-Lite Slave Interface
    //=========================================================================
    (* X_INTERFACE_INFO = "xilinx.com:signal:clock:1.0 s_axi_aclk CLK" *)
    (* X_INTERFACE_PARAMETER = "ASSOCIATED_BUSIF s_axi, ASSOCIATED_RESET s_axi_aresetn" *)
    input  wire                              s_axi_aclk,

    (* X_INTERFACE_INFO = "xilinx.com:signal:reset:1.0 s_axi_aresetn RST" *)
    (* X_INTERFACE_PARAMETER = "POLARITY ACTIVE_LOW" *)
    input  wire                              s_axi_aresetn,

    // Write Address Channel
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi AWADDR" *)
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]     s_axi_awaddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi AWPROT" *)
    input  wire [2:0]                        s_axi_awprot,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi AWVALID" *)
    input  wire                              s_axi_awvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi AWREADY" *)
    output wire                              s_axi_awready,

    // Write Data Channel
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi WDATA" *)
    input  wire [C_S_AXI_DATA_WIDTH-1:0]     s_axi_wdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi WSTRB" *)
    input  wire [C_S_AXI_DATA_WIDTH/8-1:0]   s_axi_wstrb,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi WVALID" *)
    input  wire                              s_axi_wvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi WREADY" *)
    output wire                              s_axi_wready,

    // Write Response Channel
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi BRESP" *)
    output wire [1:0]                        s_axi_bresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi BVALID" *)
    output wire                              s_axi_bvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi BREADY" *)
    input  wire                              s_axi_bready,

    // Read Address Channel
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi ARADDR" *)
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]     s_axi_araddr,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi ARPROT" *)
    input  wire [2:0]                        s_axi_arprot,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi ARVALID" *)
    input  wire                              s_axi_arvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi ARREADY" *)
    output wire                              s_axi_arready,

    // Read Data Channel
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RDATA" *)
    output wire [C_S_AXI_DATA_WIDTH-1:0]     s_axi_rdata,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RRESP" *)
    output wire [1:0]                        s_axi_rresp,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RVALID" *)
    output wire                              s_axi_rvalid,
    (* X_INTERFACE_INFO = "xilinx.com:interface:aximm:1.0 s_axi RREADY" *)
    input  wire                              s_axi_rready,

    //=========================================================================
    // Configuration Output Ports (to RTL modules)
    //=========================================================================
    output wire                              router_config_we,
    output wire [31:0]                       router_config_addr,
    output wire [31:0]                       router_config_wdata,
    input  wire [31:0]                       router_config_rdata,

    output wire                              neuron_config_we,
    output wire [9:0]                        neuron_config_addr,
    output wire [31:0]                       neuron_config_wdata,

    output wire [15:0]                       global_threshold,
    output wire [7:0]                        global_leak_rate,
    output wire [7:0]                        global_refrac_period,
    output wire [1:0]                        backend_mode,
    output wire [31:0]                       eventconv_shape0,
    output wire [31:0]                       eventconv_kernel0,

    //=========================================================================
    // Status Input Ports (from RTL modules)
    //=========================================================================
    input  wire [31:0]                       router_spike_count,
    input  wire [31:0]                       neuron_spike_count,
    input  wire                              fifo_overflow,
    input  wire [7:0]                        active_neurons,
    input  wire [31:0]                       throughput_counter,
    input  wire [31:0]                       service_cycles_counter,
    input  wire [31:0]                       pl_busy_cycles_counter,
    input  wire [31:0]                       output_drain_cycles_counter,
    input  wire [31:0]                       output_bridge_status,
    input  wire [31:0]                       output_bridge_drop_count,
    input  wire [31:0]                       output_bridge_event_count,
    input  wire [31:0]                       output_bridge_emit_count,
    input  wire [31:0]                       state_checksum,
    input  wire [31:0]                       eventconv_desc_status
);

    // AXI4-Lite interface parameters
    (* X_INTERFACE_PARAMETER = "PROTOCOL AXI4LITE, DATA_WIDTH 32, ADDR_WIDTH 7" *)

    //=========================================================================
    // Register Address Decode (word-aligned, [6:2] selects register)
    //=========================================================================
    localparam [4:0] ADDR_CONFIG_CTRL         = 5'h00;  // 0x00
    localparam [4:0] ADDR_CONFIG_ADDR         = 5'h01;  // 0x04
    localparam [4:0] ADDR_CONFIG_WDATA        = 5'h02;  // 0x08
    localparam [4:0] ADDR_CONFIG_RDATA        = 5'h03;  // 0x0C
    localparam [4:0] ADDR_THRESHOLD           = 5'h04;  // 0x10
    localparam [4:0] ADDR_NEURON_PARAMS       = 5'h05;  // 0x14
    localparam [4:0] ADDR_ROUTER_SPIKE_CNT    = 5'h06;  // 0x18
    localparam [4:0] ADDR_NEURON_SPIKE_CNT    = 5'h07;  // 0x1C
    localparam [4:0] ADDR_STATUS              = 5'h08;  // 0x20
    localparam [4:0] ADDR_THROUGHPUT          = 5'h09;  // 0x24
    localparam [4:0] ADDR_VERSION             = 5'h0A;  // 0x28
    localparam [4:0] ADDR_SERVICE_CYCLES      = 5'h0B;  // 0x2C
    localparam [4:0] ADDR_OUTPUT_BR_STATUS    = 5'h0C;  // 0x30
    localparam [4:0] ADDR_OUTPUT_BR_DROPS     = 5'h0D;  // 0x34
    localparam [4:0] ADDR_OUTPUT_BR_EVENTS    = 5'h0E;  // 0x38
    localparam [4:0] ADDR_OUTPUT_BR_EMITS     = 5'h0F;  // 0x3C
    localparam [4:0] ADDR_PL_BUSY_CYCLES      = 5'h10;  // 0x40
    localparam [4:0] ADDR_OUTPUT_DRAIN_CYCLES = 5'h11;  // 0x44
    localparam [4:0] ADDR_STATE_CHECKSUM      = 5'h12;  // 0x48
    localparam [4:0] ADDR_BACKEND_MODE        = 5'h13;  // 0x4C
    localparam [4:0] ADDR_EVENTCONV_SHAPE0    = 5'h14;  // 0x50
    localparam [4:0] ADDR_EVENTCONV_KERNEL0   = 5'h15;  // 0x54
    localparam [4:0] ADDR_EVENTCONV_DESC_STATUS = 5'h16;  // 0x58
    localparam [31:0] SPIKEMOLD_CONFIG_VERSION = 32'h534D3031;  // "SM01"

    //=========================================================================
    // AXI4-Lite State Machine
    //=========================================================================
    reg  aw_ready;
    reg  w_ready;
    reg  [1:0] b_resp;
    reg  b_valid;
    reg  ar_ready;
    reg  [C_S_AXI_DATA_WIDTH-1:0] r_data;
    reg  [1:0] r_resp;
    reg  r_valid;

    reg  [C_S_AXI_ADDR_WIDTH-1:0] aw_addr;
    reg  [C_S_AXI_ADDR_WIDTH-1:0] ar_addr;
    reg  aw_en;

    assign s_axi_awready = aw_ready;
    assign s_axi_wready  = w_ready;
    assign s_axi_bresp   = b_resp;
    assign s_axi_bvalid  = b_valid;
    assign s_axi_arready = ar_ready;
    assign s_axi_rdata   = r_data;
    assign s_axi_rresp   = r_resp;
    assign s_axi_rvalid  = r_valid;

    //=========================================================================
    // Configuration Registers
    //=========================================================================
    reg  [31:0] reg_config_ctrl;      // [1:0] = target (0=router, 1=neuron)
    reg  [31:0] reg_config_addr;
    reg  [31:0] reg_config_wdata;
    reg  [15:0] reg_threshold;
    reg  [7:0]  reg_leak_rate;
    reg  [7:0]  reg_refrac_period;
    reg  [1:0]  reg_backend_mode;
    reg  [31:0] reg_eventconv_shape0;
    reg  [31:0] reg_eventconv_kernel0;

    // Config write enable pulse (one-cycle pulse on CONFIG_WDATA write)
    reg         config_we_pulse;
    reg  [1:0]  config_target;

    //=========================================================================
    // Output Assignments
    //=========================================================================
    assign router_config_we    = config_we_pulse & (config_target == 2'd0);
    assign router_config_addr  = reg_config_addr;
    assign router_config_wdata = reg_config_wdata;

    assign neuron_config_we    = config_we_pulse & (config_target == 2'd1);
    assign neuron_config_addr  = reg_config_addr[9:0];
    assign neuron_config_wdata = reg_config_wdata;

    assign global_threshold    = reg_threshold;
    assign global_leak_rate    = reg_leak_rate;
    assign global_refrac_period = reg_refrac_period;
    assign backend_mode        = reg_backend_mode;
    assign eventconv_shape0    = reg_eventconv_shape0;
    assign eventconv_kernel0   = reg_eventconv_kernel0;

    //=========================================================================
    // AXI Write Address Channel
    //=========================================================================
    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            aw_ready <= 1'b0;
            aw_en    <= 1'b1;
            aw_addr  <= {C_S_AXI_ADDR_WIDTH{1'b0}};
        end else begin
            if (~aw_ready && s_axi_awvalid && s_axi_wvalid && aw_en) begin
                aw_ready <= 1'b1;
                aw_addr  <= s_axi_awaddr;
                aw_en    <= 1'b0;
            end else if (s_axi_bready && b_valid) begin
                aw_en    <= 1'b1;
                aw_ready <= 1'b0;
            end else begin
                aw_ready <= 1'b0;
            end
        end
    end

    //=========================================================================
    // AXI Write Data Channel
    //=========================================================================
    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            w_ready <= 1'b0;
        end else begin
            if (~w_ready && s_axi_wvalid && s_axi_awvalid && aw_en) begin
                w_ready <= 1'b1;
            end else begin
                w_ready <= 1'b0;
            end
        end
    end

    //=========================================================================
    // Register Write Logic
    //=========================================================================
    wire write_en = aw_ready && s_axi_awvalid && w_ready && s_axi_wvalid;
    wire [4:0] write_addr = aw_addr[C_S_AXI_ADDR_WIDTH-1:2];  // Word address

    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            reg_config_ctrl  <= 32'd0;
            reg_config_addr  <= 32'd0;
            reg_config_wdata <= 32'd0;
            reg_threshold    <= 16'd100;        // Default: 100
            reg_leak_rate    <= 8'h03;          // Default: shift1=3 (tau≈0.875)
            reg_refrac_period <= 8'd10;         // Default: 10 cycles
            reg_backend_mode  <= 2'd0;
            reg_eventconv_shape0  <= 32'h04020303;  // state_count=4, kernel=2, input=3x3
            reg_eventconv_kernel0 <= 32'h04030201;  // k00=1, k01=2, k10=3, k11=4
            config_we_pulse  <= 1'b0;
            config_target    <= 2'd0;
        end else begin
            // Default: clear config_we pulse after one cycle
            config_we_pulse <= 1'b0;

            if (write_en) begin
                case (write_addr)
                    ADDR_CONFIG_CTRL: begin
                        if (s_axi_wstrb[0]) begin
                            reg_config_ctrl[7:0]   <= s_axi_wdata[7:0];
                            config_target          <= s_axi_wdata[1:0];
                        end
                    end

                    ADDR_CONFIG_ADDR: begin
                        if (s_axi_wstrb[0]) reg_config_addr[7:0]   <= s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) reg_config_addr[15:8]  <= s_axi_wdata[15:8];
                        if (s_axi_wstrb[2]) reg_config_addr[23:16] <= s_axi_wdata[23:16];
                        if (s_axi_wstrb[3]) reg_config_addr[31:24] <= s_axi_wdata[31:24];
                    end

                    ADDR_CONFIG_WDATA: begin
                        if (s_axi_wstrb[0]) reg_config_wdata[7:0]   <= s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) reg_config_wdata[15:8]  <= s_axi_wdata[15:8];
                        if (s_axi_wstrb[2]) reg_config_wdata[23:16] <= s_axi_wdata[23:16];
                        if (s_axi_wstrb[3]) reg_config_wdata[31:24] <= s_axi_wdata[31:24];
                        // Auto-trigger config_we on WDATA write
                        config_we_pulse <= 1'b1;
                    end

                    ADDR_THRESHOLD: begin
                        if (s_axi_wstrb[0]) reg_threshold[7:0]  <= s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) reg_threshold[15:8] <= s_axi_wdata[15:8];
                    end

                    ADDR_NEURON_PARAMS: begin
                        if (s_axi_wstrb[0]) reg_leak_rate      <= s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) reg_refrac_period   <= s_axi_wdata[15:8];
                    end

                    ADDR_BACKEND_MODE: begin
                        if (s_axi_wstrb[0]) reg_backend_mode <= s_axi_wdata[1:0];
                    end

                    ADDR_EVENTCONV_SHAPE0: begin
                        if (s_axi_wstrb[0]) reg_eventconv_shape0[7:0]   <= s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) reg_eventconv_shape0[15:8]  <= s_axi_wdata[15:8];
                        if (s_axi_wstrb[2]) reg_eventconv_shape0[23:16] <= s_axi_wdata[23:16];
                        if (s_axi_wstrb[3]) reg_eventconv_shape0[31:24] <= s_axi_wdata[31:24];
                    end

                    ADDR_EVENTCONV_KERNEL0: begin
                        if (s_axi_wstrb[0]) reg_eventconv_kernel0[7:0]   <= s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) reg_eventconv_kernel0[15:8]  <= s_axi_wdata[15:8];
                        if (s_axi_wstrb[2]) reg_eventconv_kernel0[23:16] <= s_axi_wdata[23:16];
                        if (s_axi_wstrb[3]) reg_eventconv_kernel0[31:24] <= s_axi_wdata[31:24];
                    end

                    default: ; // Read-only or reserved registers
                endcase
            end
        end
    end

    //=========================================================================
    // AXI Write Response
    //=========================================================================
    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            b_valid <= 1'b0;
            b_resp  <= 2'b00;
        end else begin
            if (write_en && ~b_valid) begin
                b_valid <= 1'b1;
                b_resp  <= 2'b00;   // OKAY
            end else if (s_axi_bready && b_valid) begin
                b_valid <= 1'b0;
            end
        end
    end

    //=========================================================================
    // AXI Read Address Channel
    //=========================================================================
    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            ar_ready <= 1'b0;
            ar_addr  <= {C_S_AXI_ADDR_WIDTH{1'b0}};
        end else begin
            if (~ar_ready && s_axi_arvalid) begin
                ar_ready <= 1'b1;
                ar_addr  <= s_axi_araddr;
            end else begin
                ar_ready <= 1'b0;
            end
        end
    end

    //=========================================================================
    // Register Read Logic
    //=========================================================================
    wire [4:0] read_addr = ar_addr[C_S_AXI_ADDR_WIDTH-1:2];

    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            r_data  <= 32'd0;
            r_valid <= 1'b0;
            r_resp  <= 2'b00;
        end else begin
            if (ar_ready && s_axi_arvalid && ~r_valid) begin
                r_valid <= 1'b1;
                r_resp  <= 2'b00;   // OKAY
                case (read_addr)
                    ADDR_CONFIG_CTRL:       r_data <= reg_config_ctrl;
                    ADDR_CONFIG_ADDR:       r_data <= reg_config_addr;
                    ADDR_CONFIG_WDATA:      r_data <= reg_config_wdata;
                    ADDR_CONFIG_RDATA:      r_data <= router_config_rdata;
                    ADDR_THRESHOLD:         r_data <= {16'd0, reg_threshold};
                    ADDR_NEURON_PARAMS:     r_data <= {16'd0, reg_refrac_period, reg_leak_rate};
                    ADDR_ROUTER_SPIKE_CNT:  r_data <= router_spike_count;
                    ADDR_NEURON_SPIKE_CNT:  r_data <= neuron_spike_count;
                    ADDR_STATUS:            r_data <= {23'd0, active_neurons, fifo_overflow};
                    ADDR_THROUGHPUT:        r_data <= throughput_counter;
                    ADDR_VERSION:           r_data <= SPIKEMOLD_CONFIG_VERSION;
                    ADDR_SERVICE_CYCLES:    r_data <= service_cycles_counter;
                    ADDR_OUTPUT_BR_STATUS:  r_data <= output_bridge_status;
                    ADDR_OUTPUT_BR_DROPS:   r_data <= output_bridge_drop_count;
                    ADDR_OUTPUT_BR_EVENTS:  r_data <= output_bridge_event_count;
                    ADDR_OUTPUT_BR_EMITS:   r_data <= output_bridge_emit_count;
                    ADDR_PL_BUSY_CYCLES:    r_data <= pl_busy_cycles_counter;
                    ADDR_OUTPUT_DRAIN_CYCLES: r_data <= output_drain_cycles_counter;
                    ADDR_STATE_CHECKSUM:     r_data <= state_checksum;
                    ADDR_BACKEND_MODE:       r_data <= {30'd0, reg_backend_mode};
                    ADDR_EVENTCONV_SHAPE0:   r_data <= reg_eventconv_shape0;
                    ADDR_EVENTCONV_KERNEL0:  r_data <= reg_eventconv_kernel0;
                    ADDR_EVENTCONV_DESC_STATUS: r_data <= eventconv_desc_status;
                    default:                r_data <= 32'hDEADBEEF;
                endcase
            end else if (r_valid && s_axi_rready) begin
                r_valid <= 1'b0;
            end
        end
    end

    // Suppress unused port warnings
    wire _unused = &{s_axi_awprot, s_axi_arprot, 1'b0};

endmodule
