//-----------------------------------------------------------------------------
// Title         : Spike Router Module
// Project       : PYNQ-Z2 SNN Accelerator
// File          : spike_router.v
// Author        : Jiwoon Lee (@metr0jw)
// Organization  : Kwangwoon University, Seoul, South Korea
// Contact       : jwlee@linux.com
// Description   : Routes spikes between neurons with configurable connectivity
//-----------------------------------------------------------------------------

`timescale 1ns / 1ps

module spike_router #(
    parameter NUM_NEURONS       = 64,
    parameter MAX_FANOUT        = 32,      // Max connections per neuron
    parameter WEIGHT_WIDTH      = 8,
    // Calculate log2 ceiling manually for Verilog-2001 compatibility
    parameter NEURON_ID_WIDTH   = (NUM_NEURONS <= 2) ? 1 :
                                 (NUM_NEURONS <= 4) ? 2 :
                                 (NUM_NEURONS <= 8) ? 3 :
                                 (NUM_NEURONS <= 16) ? 4 :
                                 (NUM_NEURONS <= 32) ? 5 :
                                 (NUM_NEURONS <= 64) ? 6 :
                                 (NUM_NEURONS <= 128) ? 7 :
                                 (NUM_NEURONS <= 256) ? 8 :
                                 (NUM_NEURONS <= 512) ? 9 : 10,
    parameter DELAY_WIDTH       = 8,
    parameter FIFO_DEPTH        = 256
)(
    input  wire                         clk,
    input  wire                         rst_n,
    
    // Input spike interface from neurons
    input  wire                         s_spike_valid,
    input  wire [NEURON_ID_WIDTH-1:0]   s_spike_neuron_id,
    output wire                         s_spike_ready,
    
    // Output spike interface to synapses
    output wire                         m_spike_valid,
    output wire [NEURON_ID_WIDTH-1:0]   m_spike_dest_id,
    output wire [WEIGHT_WIDTH-1:0]      m_spike_weight,
    output wire                         m_spike_exc_inh,
    input  wire                         m_spike_ready,
    
    // Configuration interface (from AXI)
    // Read path: config_addr -> config_readdata
    // Write path: either legacy config_we/config_addr/config_data OR
    //             queued config_cmd_valid/config_cmd_addr/config_cmd_data.
    input  wire                         config_we,
    input  wire [31:0]                  config_addr,
    input  wire [31:0]                  config_data,
    input  wire                         config_cmd_valid,
    input  wire [31:0]                  config_cmd_addr,
    input  wire [31:0]                  config_cmd_data,
    output reg  [31:0]                  config_readdata,
    
    // Status
    output wire [31:0]                  routed_spike_count,
    output wire                         router_busy,
    output wire                         fifo_overflow
);

    // Explicitly consume unused bits to suppress synthesis warnings
    // Upper bits reserved for future expansion
    wire unused_addr_bits_valid = |config_addr[23:12];  // Will be optimized away
    wire unused_data_bits_valid = |config_data[31:24];  // Will be optimized away

    // Queued command path has priority over legacy direct write path.
    wire        cfg_wr_en   = config_cmd_valid | config_we;
    wire [31:0] cfg_wr_addr = config_cmd_valid ? config_cmd_addr : config_addr;
    wire [31:0] cfg_wr_data = config_cmd_valid ? config_cmd_data : config_data;

    // State machine states
    localparam IDLE         = 3'd0;
    localparam WAIT_FIFO    = 3'd1;
    localparam FETCH_CONN   = 3'd2;
    localparam CHECK_DELAY  = 3'd3;
    localparam ROUTE_SPIKE  = 3'd4;
    localparam NEXT_CONN    = 3'd5;
    
    reg [2:0] state, next_state;
    
    // Connection memory structure
    // Format: [valid(1), exc/inh(1), weight(8), delay(8), dest_id(NEURON_ID_WIDTH)]
    // Total width = 18 + NEURON_ID_WIDTH bits
    localparam CONN_WIDTH = 18 + NEURON_ID_WIDTH;
    localparam CONN_DEPTH = NUM_NEURONS * MAX_FANOUT;
    localparam CONN_ADDR_WIDTH = (CONN_DEPTH <= 2) ? 1 :
                                 (CONN_DEPTH <= 4) ? 2 :
                                 (CONN_DEPTH <= 8) ? 3 :
                                 (CONN_DEPTH <= 16) ? 4 :
                                 (CONN_DEPTH <= 32) ? 5 :
                                 (CONN_DEPTH <= 64) ? 6 :
                                 (CONN_DEPTH <= 128) ? 7 :
                                 (CONN_DEPTH <= 256) ? 8 :
                                 (CONN_DEPTH <= 512) ? 9 :
                                 (CONN_DEPTH <= 1024) ? 10 :
                                 (CONN_DEPTH <= 2048) ? 11 :
                                 (CONN_DEPTH <= 4096) ? 12 :
                                 (CONN_DEPTH <= 8192) ? 13 :
                                 (CONN_DEPTH <= 16384) ? 14 : 15;

    //-------------------------------------------------------------------------
    // Connection memory: True Dual-Port BRAM inference pattern
    //   Port A: config write + config readback (same address)
    //   Port B: data-path read (operational fetches)
    // 1024 neurons * 32 fanout * 28 bits = 917 Kbit = ~32 BRAM18K
    //-------------------------------------------------------------------------
    (* ram_style = "block" *) reg [CONN_WIDTH-1:0] conn_memory [0:CONN_DEPTH-1];

    // Port B registered output (data-path fetch / config readback when idle)
    reg [CONN_WIDTH-1:0] conn_mem_dout_b;

    // Connection count per neuron.
    // This array has concurrent config read + datapath read + write, so
    // synthesis maps it to distributed RAM on xc7z020.
    (* ram_style = "distributed" *) reg [7:0] conn_count [0:NUM_NEURONS-1];

    // Initialize connection memory to 0 (for simulation)
    integer init_idx;
    integer init_cc_idx;
    initial begin
        for (init_idx = 0; init_idx < CONN_DEPTH; init_idx = init_idx + 1) begin
            conn_memory[init_idx] = {CONN_WIDTH{1'b0}};
        end
        for (init_cc_idx = 0; init_cc_idx < NUM_NEURONS; init_cc_idx = init_cc_idx + 1) begin
            conn_count[init_cc_idx] = 8'd0;
        end
    end
    
    // Spike event FIFO
    wire fifo_wr_en, fifo_rd_en;
    wire fifo_empty, fifo_full;
    wire [NEURON_ID_WIDTH-1:0] fifo_spike_id;
    wire [31:0] fifo_timestamp;
    reg [31:0] current_time;
    
    // Processing registers
    reg [NEURON_ID_WIDTH-1:0] current_neuron;
    reg [7:0] conn_index;
    reg [CONN_WIDTH-1:0] current_conn;
    reg [31:0] spike_timestamp;
    reg [7:0] current_conn_count;
    
    // Output registers
    reg out_valid;
    reg [NEURON_ID_WIDTH-1:0] out_dest_id;
    reg [WEIGHT_WIDTH-1:0] out_weight;
    reg out_exc_inh;
    
    // Statistics
    reg [31:0] spike_counter;
    reg overflow_flag;
    
    //-------------------------------------------------------------------------
    // Input spike FIFO
    //-------------------------------------------------------------------------
    wire fifo_almost_full;
    wire fifo_almost_empty;
    wire [$clog2(FIFO_DEPTH):0] fifo_count;
    wire fifo_underflow;
    
    fifo #(
        .DATA_WIDTH(NEURON_ID_WIDTH + 32),
        .DEPTH(FIFO_DEPTH)
    ) spike_fifo (
        .clk(clk),
        .rst_n(rst_n),
        .wr_en(s_spike_valid && s_spike_ready),
        .wr_data({current_time, s_spike_neuron_id}),
        .full(fifo_full),
        .almost_full(fifo_almost_full),
        .rd_en(fifo_rd_en),
        .rd_data({fifo_timestamp, fifo_spike_id}),
        .empty(fifo_empty),
        .almost_empty(fifo_almost_empty),
        .count(fifo_count),
        .overflow(fifo_overflow),
        .underflow(fifo_underflow)
    );
    
    assign s_spike_ready = !fifo_full;
    assign fifo_rd_en = (state == IDLE) && !fifo_empty;
    
    // Global timestamp counter
    always @(posedge clk) begin
        if (!rst_n)
            current_time <= 32'd0;
        else
            current_time <= current_time + 1'b1;
    end

    //-------------------------------------------------------------------------
    // conn_memory: True Dual-Port BRAM inference
    //   Port A: config write + config read (always block A)
    //   Port B: data-path read only   (always block B)
    //-------------------------------------------------------------------------

    wire [CONN_ADDR_WIDTH-1:0] cfg_wr_conn_addr = cfg_wr_addr[CONN_ADDR_WIDTH-1:0];
    wire [CONN_ADDR_WIDTH-1:0] cfg_rd_conn_addr = config_addr[CONN_ADDR_WIDTH-1:0];

    // Port A — config write only.
    // Port-A readback is intentionally removed to avoid extra BRAM read-port pressure.
    always @(posedge clk) begin
        if (cfg_wr_en && cfg_wr_addr[31:24] == 8'h00) begin
            conn_memory[cfg_wr_conn_addr] <= cfg_wr_data[CONN_WIDTH-1:0];
        end
    end

    // Port B — data-path read (FETCH_CONN)
    // Combinational address mux — address set in state BEFORE read is needed
    reg [CONN_ADDR_WIDTH-1:0] conn_rd_addr_b;
    always @(*) begin
        // Reuse Port-B for config readback only when router is fully idle.
        if ((state == IDLE) && fifo_empty && (config_addr[31:24] == 8'h00)) begin
            conn_rd_addr_b = cfg_rd_conn_addr;
        end else begin
            case (state)
                IDLE:      conn_rd_addr_b = fifo_spike_id * MAX_FANOUT;        // prep for FETCH after WAIT_FIFO
                WAIT_FIFO: conn_rd_addr_b = fifo_spike_id * MAX_FANOUT;        // read first connection
                NEXT_CONN: conn_rd_addr_b = current_neuron * MAX_FANOUT + conn_index + 1'b1; // read next connection
                default:   conn_rd_addr_b = current_neuron * MAX_FANOUT + conn_index;
            endcase
        end
    end
    always @(posedge clk) begin
        conn_mem_dout_b <= conn_memory[conn_rd_addr_b];
    end

    // conn_count: direct access (small LUTRAM, 8 Kbit)
    //   Write: config interface
    //   Read-A: config readback
    //   Read-B: state-machine datapath (registered to break long FIFO->mux paths)
    reg [7:0] conn_count_dout_a;
    (* keep = "true" *) reg [7:0] conn_count_dout_b;
    (* keep = "true" *) reg [NEURON_ID_WIDTH-1:0] conn_count_rd_addr_b;

    // Config write + readback for conn_count
    always @(posedge clk) begin
        if (!rst_n) begin
            conn_count_dout_a <= 8'd0;
        end else if (cfg_wr_en && cfg_wr_addr[31:24] == 8'h01) begin
            conn_count[cfg_wr_addr[NEURON_ID_WIDTH-1:0]] <= cfg_wr_data[7:0];
            conn_count_dout_a <= conn_count[cfg_wr_addr[NEURON_ID_WIDTH-1:0]];
        end else begin
            conn_count_dout_a <= conn_count[config_addr[NEURON_ID_WIDTH-1:0]];
        end
    end

    // Datapath read port (registered address + registered output).
    // This adds an explicit pipeline boundary so FIFO rd_data does not
    // directly feed the wide conn_count mux cone in the same cycle.
    always @(posedge clk) begin
        if (!rst_n) begin
            conn_count_rd_addr_b <= {NEURON_ID_WIDTH{1'b0}};
            conn_count_dout_b <= 8'd0;
        end else begin
            if (state == WAIT_FIFO) begin
                conn_count_rd_addr_b <= fifo_spike_id;
            end
            conn_count_dout_b <= conn_count[conn_count_rd_addr_b];
        end
    end

    //-------------------------------------------------------------------------
    // State machine
    //-------------------------------------------------------------------------
    always @(posedge clk) begin
        if (!rst_n)
            state <= IDLE;
        else
            state <= next_state;
    end
    
    always @(*) begin
        next_state = state;
        case (state)
            IDLE: begin
                if (!fifo_empty)
                    next_state = WAIT_FIFO;
            end
            
            WAIT_FIFO: begin
                // Wait one cycle for FIFO data + conn_count BRAM read
                next_state = FETCH_CONN;
            end
            
            FETCH_CONN: begin
                next_state = CHECK_DELAY;
            end
            
            CHECK_DELAY: begin
                if (current_conn[CONN_WIDTH-1] && // valid connection
                    ((current_time - spike_timestamp) >= current_conn[NEURON_ID_WIDTH+7:NEURON_ID_WIDTH])) // delay expired
                    next_state = ROUTE_SPIKE;
                else
                    next_state = NEXT_CONN;
            end
            
            ROUTE_SPIKE: begin
                if (m_spike_ready)
                    next_state = NEXT_CONN;
            end
            
            NEXT_CONN: begin
                if (conn_index >= current_conn_count)
                    next_state = IDLE;
                else
                    next_state = FETCH_CONN;
            end
            
            default: next_state = IDLE;
        endcase
    end
    
    //-------------------------------------------------------------------------
    // Connection processing (drives Port B addresses, uses Port B outputs)
    //-------------------------------------------------------------------------
    reg spike_counter_inc;
    
    always @(posedge clk) begin
        if (!rst_n) begin
            current_neuron <= 0;
            conn_index <= 0;
            current_conn <= 0;
            spike_timestamp <= 0;
            out_valid <= 1'b0;
            spike_counter_inc <= 1'b0;
            current_conn_count <= 0;
        end else begin
            spike_counter_inc <= 1'b0;
            
            case (state)
                IDLE: begin
                    out_valid <= 1'b0;
                    conn_index <= 0;
                end
                
                WAIT_FIFO: begin
                    // FIFO data valid, capture it
                    current_neuron <= fifo_spike_id;
                    spike_timestamp <= fifo_timestamp;
                end
                
                FETCH_CONN: begin
                    // Port-B reads are registered and become available here.
                    current_conn <= conn_mem_dout_b;
                end

                CHECK_DELAY: begin
                    // conn_count_dout_b corresponds to registered current_neuron.
                    current_conn_count <= conn_count_dout_b;
                end
                
                ROUTE_SPIKE: begin
                    if (!out_valid || m_spike_ready) begin
                        out_valid <= 1'b1;
                        out_dest_id <= current_conn[NEURON_ID_WIDTH-1:0];
                        out_weight <= current_conn[NEURON_ID_WIDTH+15:NEURON_ID_WIDTH+8];
                        out_exc_inh <= current_conn[CONN_WIDTH-2];
                        spike_counter_inc <= 1'b1;
                    end
                end
                
                NEXT_CONN: begin
                    out_valid <= 1'b0;
                    conn_index <= conn_index + 1'b1;
                end
            endcase
        end
    end
    
    // Output assignments
    assign m_spike_valid = out_valid;
    assign m_spike_dest_id = out_dest_id;
    assign m_spike_weight = out_weight;
    assign m_spike_exc_inh = out_exc_inh;
    
    //-------------------------------------------------------------------------
    // Spike counter management
    //-------------------------------------------------------------------------
    always @(posedge clk) begin
        if (!rst_n) begin
            spike_counter <= 32'd0;
        end else begin
            if (cfg_wr_en && cfg_wr_addr[31:24] == 8'h02 && cfg_wr_data[0]) begin
                spike_counter <= 32'd0;
            end else if (spike_counter_inc) begin
                spike_counter <= spike_counter + 1'b1;
            end
        end
    end
    
    // Configuration readback multiplexer (uses Port A outputs)
    always @(posedge clk) begin
        if (!rst_n) begin
            config_readdata <= 32'd0;
        end else begin
            case (config_addr[31:24])
                8'h00: config_readdata <= {{(32-CONN_WIDTH){1'b0}}, conn_mem_dout_b};
                8'h01: config_readdata <= {24'd0, conn_count_dout_a};
                8'h10: config_readdata <= spike_counter;
                8'h11: config_readdata <= {31'd0, fifo_overflow};
                default: config_readdata <= 32'hDEADBEEF;
            endcase
        end
    end
    
    // Status outputs
    assign routed_spike_count = spike_counter;
    assign router_busy = (state != IDLE) || !fifo_empty;

endmodule
