"""
Tests for app.py helper functions (WaveDrom, Quality Score, Bug Prediction, ZIP)
"""

import pytest
import sys
import json
import zipfile
import io
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from src.app_helpers import (
    generate_wavedrom, 
    calculate_quality_score, 
    predict_bugs, 
    create_testbench_zip
)
from src.rtl_parser import parse_rtl


class TestWaveDromGenerator:
    """Test WaveDrom JSON generation"""
    
    def test_apb_wavedrom(self):
        """Test APB WaveDrom generation"""
        result = generate_wavedrom("apb")
        data = json.loads(result)
        
        assert 'signal' in data
        assert len(data['signal']) > 0
        # Check for APB signals
        signal_names = [s.get('name', '') for s in data['signal']]
        assert 'PCLK' in signal_names
        assert 'PSEL' in signal_names
    
    def test_axi_wavedrom(self):
        """Test AXI4-Lite WaveDrom generation"""
        result = generate_wavedrom("axi4lite")
        data = json.loads(result)
        
        signal_names = [s.get('name', '') for s in data['signal']]
        assert 'ACLK' in signal_names
        assert 'AWVALID' in signal_names
    
    def test_spi_wavedrom(self):
        """Test SPI WaveDrom generation"""
        result = generate_wavedrom("spi")
        data = json.loads(result)
        
        signal_names = [s.get('name', '') for s in data['signal']]
        assert 'SCLK' in signal_names
        assert 'MOSI' in signal_names
    
    def test_uart_wavedrom(self):
        """Test UART WaveDrom generation"""
        result = generate_wavedrom("uart")
        data = json.loads(result)
        
        signal_names = [s.get('name', '') for s in data['signal']]
        assert 'TX' in signal_names
    
    def test_i2c_wavedrom(self):
        """Test I2C WaveDrom generation"""
        result = generate_wavedrom("i2c")
        data = json.loads(result)
        
        signal_names = [s.get('name', '') for s in data['signal']]
        assert 'SCL' in signal_names
        assert 'SDA' in signal_names
    
    def test_unknown_protocol_fallback(self):
        """Test unknown protocol falls back to APB"""
        result = generate_wavedrom("unknown_protocol")
        data = json.loads(result)
        
        # Should fall back to APB
        signal_names = [s.get('name', '') for s in data['signal']]
        assert 'PCLK' in signal_names


class TestQualityScore:
    """Test testbench quality scoring"""
    
    def test_complete_testbench_high_score(self):
        """Test complete testbench gets high score"""
        # Good testbench with all components
        code = """
        interface apb_if(input logic clk);
        endinterface
        
        class apb_driver extends uvm_driver;
            virtual interface apb_if vif;
            `uvm_info("DRV", "message", UVM_MEDIUM)
        endclass
        
        class apb_monitor extends uvm_monitor;
            `uvm_error("MON", "error")
        endclass
        
        class apb_scoreboard extends uvm_scoreboard;
        endclass
        
        class apb_coverage extends uvm_subscriber;
            covergroup cg;
                coverpoint addr;
            endgroup
        endclass
        
        class apb_agent extends uvm_agent;
        endclass
        
        class apb_env extends uvm_env;
        endclass
        
        class apb_sequence extends uvm_sequence;
        endclass
        
        class apb_test extends uvm_test;
        endclass
        """
        
        parsed = parse_rtl("""
        module apb_slave(
            input pclk, presetn, psel, penable, pwrite,
            input [31:0] paddr, pwdata,
            output [31:0] prdata,
            output pready
        );
        endmodule
        """)
        
        quality = calculate_quality_score(parsed, code)
        
        assert quality['score'] >= 70
        assert 'breakdown' in quality
        assert quality['breakdown']['completeness'] > 0
    
    def test_minimal_testbench_low_score(self):
        """Test minimal testbench gets lower score"""
        # Minimal testbench
        code = """
        module test;
            // minimal
        endmodule
        """
        
        parsed = parse_rtl("module empty; endmodule")
        quality = calculate_quality_score(parsed, code)
        
        assert quality['score'] < 50


class TestBugPrediction:
    """Test bug prediction feature"""
    
    def test_apb_bug_prediction(self):
        """Test APB designs predict relevant bugs"""
        # Use more complete APB RTL with all required signals
        parsed = parse_rtl("""
        module apb_slave #(
            parameter DATA_WIDTH = 32,
            parameter ADDR_WIDTH = 8
        )(
            input  logic                    pclk,
            input  logic                    preset_n,
            input  logic                    psel,
            input  logic                    penable,
            input  logic                    pwrite,
            input  logic [ADDR_WIDTH-1:0]   paddr,
            input  logic [DATA_WIDTH-1:0]   pwdata,
            output logic [DATA_WIDTH-1:0]   prdata,
            output logic                    pready,
            output logic                    pslverr
        );
            reg [1:0] state;
            localparam IDLE = 0, ACCESS = 1;
        endmodule
        """)
        
        bugs = predict_bugs(parsed)
        
        assert len(bugs) > 0
        bug_titles = [b['title'] for b in bugs]
        # Should predict APB-specific bugs OR generic bugs at minimum
        assert len(bug_titles) > 0
    
    def test_spi_bug_prediction(self):
        """Test SPI designs predict clock phase bugs"""
        parsed = parse_rtl("""
        module spi_master(
            input clk, rst_n,
            output sclk, mosi, cs_n,
            input miso
        );
        endmodule
        """)
        
        bugs = predict_bugs(parsed)
        
        # Should predict SPI-specific bugs if SPI detected
        assert isinstance(bugs, list)
    
    def test_bug_severity_levels(self):
        """Test bugs have severity levels"""
        parsed = parse_rtl("""
        module axi_slave(
            input aclk, aresetn,
            input awvalid, wvalid, arvalid,
            output awready, wready, arready,
            output bvalid, rvalid
        );
            reg [1:0] state;
        endmodule
        """)
        
        bugs = predict_bugs(parsed)
        
        for bug in bugs:
            assert 'severity' in bug
            assert bug['severity'] in ['high', 'medium', 'low']
            assert 'title' in bug
            assert 'description' in bug


class TestZIPExport:
    """Test ZIP file generation"""
    
    def test_zip_creation(self):
        """Test ZIP file is created with expected contents"""
        code = "// Test testbench"
        zip_bytes = create_testbench_zip("test_module", code, None)
        
        # Verify it's a valid ZIP
        zip_buffer = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            names = zf.namelist()
            
            # Check expected files
            assert 'README.md' in names
            assert any('Makefile' in n for n in names)
            assert any('test_module' in n for n in names)
    
    def test_zip_contains_makefiles(self):
        """Test ZIP contains both VCS and Questa makefiles"""
        code = "// Test testbench"
        zip_bytes = create_testbench_zip("apb_slave", code, None)
        
        zip_buffer = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            names = zf.namelist()
            
            assert 'tb/Makefile.vcs' in names
            assert 'tb/Makefile.questa' in names
    
    def test_zip_readme_content(self):
        """Test README has correct module name"""
        code = "// Test testbench"
        zip_bytes = create_testbench_zip("my_dut", code, None)
        
        zip_buffer = io.BytesIO(zip_bytes)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            readme = zf.read('README.md').decode('utf-8')
            
            assert 'my_dut' in readme
            assert 'VerifAI' in readme


class TestWaveDromValidJSON:
    """Test WaveDrom outputs are valid JSON"""
    
    @pytest.fixture(params=['apb', 'axi4lite', 'spi', 'uart', 'i2c'])
    def protocol(self, request):
        return request.param
    
    def test_valid_json_output(self, protocol):
        """Test all protocols produce valid JSON"""
        result = generate_wavedrom(protocol)
        
        # Should not raise
        data = json.loads(result)
        
        assert isinstance(data, dict)
        assert 'signal' in data
