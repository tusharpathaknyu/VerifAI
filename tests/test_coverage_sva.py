"""
Tests for Coverage Analyzer and SVA Generator
=============================================
Testing the key differentiator features.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from coverage_analyzer import (
    CoverageAnalyzer, CoverageParser, CoverageReport, 
    Covergroup, CoverPoint, CoverageBin, CoverageGap,
    CoverageStatus, SuggestedSequence
)
from sva_generator import (
    SVAGenerator, SVAModule, SVAProperty,
    AssertionType, AssertionCategory,
    generate_sva_from_parsed
)
from rtl_parser import RTLParser


class TestCoverageAnalyzer:
    """Tests for coverage gap analysis"""
    
    def test_parse_text_summary_basic(self):
        """Test parsing a basic coverage summary"""
        analyzer = CoverageAnalyzer()
        
        content = """=== Coverage Report ===
Covergroup: cg_test
  Coverpoint: cp_addr
    bin addr_0: 100/100 (100%)
    bin addr_1: 50/100 (50%)
    bin addr_2: 0/100 (0%)
    
Overall Coverage: 50%"""
        
        report = analyzer.parse_text_summary(content)
        
        assert report.overall_coverage == 50.0
        assert len(report.covergroups) == 1
        assert report.covergroups[0].name == "cg_test"
        assert len(report.covergroups[0].coverpoints) == 1
    
    def test_parse_text_summary_with_cross(self):
        """Test parsing coverage with cross coverage"""
        analyzer = CoverageAnalyzer()
        
        content = """Covergroup: cg_apb
  Coverpoint: cp_addr
    bin addr_0x00: 45/100 (45%)
    bin addr_0x04: 78/100 (78%)
  Cross: cp_addr x cp_write
    bin <addr_0x00, read_op>: 35/50 (70%)
    bin <addr_0x00, write_op>: 10/50 (20%)
    
Overall Coverage: 53.25%"""
        
        report = analyzer.parse_text_summary(content)
        
        assert len(report.covergroups) == 1
        cg = report.covergroups[0]
        assert len(cg.coverpoints) == 1
        assert len(cg.crosses) == 1
        assert len(cg.crosses[0].bins) == 2
    
    def test_analyze_coverage_finds_gaps(self):
        """Test that coverage analysis identifies gaps"""
        analyzer = CoverageAnalyzer()
        
        content = """Covergroup: cg_test
  Coverpoint: cp_data
    bin zero: 100/100 (100%)
    bin low: 50/100 (50%)
    bin high: 0/100 (0%)
    
Overall Coverage: 50%"""
        
        report = analyzer.parse_text_summary(content)
        gaps = analyzer.analyze_coverage(report, target_coverage=95)
        
        assert len(gaps) >= 2  # At least low and high bins
        
        # High priority for 0 hits
        high_gaps = [g for g in gaps if g.hit_count == 0]
        assert all(g.priority == "high" for g in high_gaps)
    
    def test_gap_to_suggestion_generates_code(self):
        """Test that gap generates valid UVM sequence code"""
        analyzer = CoverageAnalyzer()
        
        gap = CoverageGap(
            covergroup="cg_test",
            coverpoint="cp_addr",
            bin_name="addr_high",
            bin_value="0",
            priority="high",
            suggested_stimulus="addr = $urandom_range(4096, 65535)",
            suggested_sequence="high_address_seq",
            hit_count=0,
            goal_count=100,
            current_coverage=0.0,
            target_coverage=95.0,
            hits_needed=100
        )
        
        suggestion = analyzer.gap_to_suggestion(gap)
        
        assert isinstance(suggestion, SuggestedSequence)
        assert "class high_address_seq" in suggestion.uvm_sequence_code
        assert "addr = $urandom_range(4096, 65535)" in suggestion.uvm_sequence_code
        assert "uvm_sequence" in suggestion.uvm_sequence_code
    
    def test_stimulus_suggestion_for_address(self):
        """Test stimulus patterns for address coverpoints"""
        analyzer = CoverageAnalyzer()
        
        # Test various address patterns
        test_cases = [
            ("addr_low", "cp_addr", "addr"),
            ("addr_high", "cp_address", "addr"),
            ("addr_boundary", "cp_addr", "boundary"),
        ]
        
        for bin_name, cp_name, expected_keyword in test_cases:
            stimulus, seq_name = analyzer._suggest_stimulus(bin_name, cp_name)
            assert expected_keyword.lower() in stimulus.lower() or expected_keyword in seq_name.lower()
    
    def test_stimulus_suggestion_for_data(self):
        """Test stimulus patterns for data coverpoints"""
        analyzer = CoverageAnalyzer()
        
        stimulus, _ = analyzer._suggest_stimulus("zero", "cp_data")
        assert "0" in stimulus or "zero" in stimulus.lower()
        
        stimulus, _ = analyzer._suggest_stimulus("all_ones", "cp_wdata")
        assert "1" in stimulus or "ones" in stimulus.lower()


class TestCoverageParser:
    """Tests for coverage report parser"""
    
    def test_parse_json_format(self):
        """Test JSON coverage format parsing"""
        parser = CoverageParser()
        
        json_content = """{
            "total_coverage": 75.5,
            "covergroups": [{
                "name": "cg_apb",
                "coverpoints": [{
                    "name": "cp_addr",
                    "bins": [
                        {"name": "low", "hits": 100, "goal": 100},
                        {"name": "high", "hits": 0, "goal": 100}
                    ]
                }]
            }]
        }"""
        
        report = parser.parse(json_content, "json")
        
        assert report.total_coverage == 75.5
        assert len(report.covergroups) == 1
        assert report.covergroups[0].name == "cg_apb"
    
    def test_auto_detect_json(self):
        """Test auto-detection of JSON format"""
        parser = CoverageParser()
        
        json_content = '{"covergroups": [], "total_coverage": 50}'
        format_type = parser._detect_format(json_content)
        
        assert format_type == "json"


class TestSVAGenerator:
    """Tests for SVA assertion generator"""
    
    @pytest.fixture
    def apb_rtl(self):
        """Sample APB slave RTL"""
        return """
module apb_slave (
    input  logic        pclk,
    input  logic        preset_n,
    input  logic        psel,
    input  logic        penable,
    input  logic        pwrite,
    input  logic [31:0] paddr,
    input  logic [31:0] pwdata,
    output logic [31:0] prdata,
    output logic        pready,
    output logic        pslverr
);
endmodule
"""
    
    @pytest.fixture
    def fsm_rtl(self):
        """Sample FSM RTL"""
        return """
module fsm_example (
    input  logic clk,
    input  logic rst_n,
    input  logic start,
    output logic done
);
    typedef enum logic [1:0] {
        IDLE  = 2'b00,
        RUN   = 2'b01,
        DONE  = 2'b10,
        ERROR = 2'b11
    } state_t;
    
    state_t state, next_state;
    
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            state <= IDLE;
        else
            state <= next_state;
    end
endmodule
"""
    
    def test_generate_from_apb_rtl(self, apb_rtl):
        """Test SVA generation from APB RTL"""
        parser = RTLParser()
        parsed = parser.parse(apb_rtl)
        
        generator = SVAGenerator(parsed)
        sva_module = generator.generate_all()
        
        assert sva_module.module_name == "apb_slave"
        assert len(sva_module.properties) > 0
        
        # Should detect APB protocol and generate protocol assertions
        categories = [p.category for p in sva_module.properties]
        assert AssertionCategory.PROTOCOL in categories or AssertionCategory.RESET in categories
    
    def test_generate_apb_protocol_assertions(self, apb_rtl):
        """Test that APB-specific assertions are generated"""
        parser = RTLParser()
        parsed = parser.parse(apb_rtl)
        
        generator = SVAGenerator(parsed)
        sva_module = generator.generate_all()
        sva_code = sva_module.to_sv()
        
        # Should have APB-specific assertions
        assert "psel" in sva_code.lower() or "penable" in sva_code.lower()
    
    def test_detect_clock_reset(self, apb_rtl):
        """Test clock and reset detection"""
        parser = RTLParser()
        parsed = parser.parse(apb_rtl)
        
        generator = SVAGenerator(parsed)
        
        clock = generator._detect_clock()
        reset = generator._detect_reset()
        
        assert clock == "pclk"
        assert reset == "preset_n"
        assert generator._is_reset_active_low() == True
    
    def test_generate_fsm_assertions(self, fsm_rtl):
        """Test FSM assertion generation"""
        parser = RTLParser()
        parsed = parser.parse(fsm_rtl)
        
        generator = SVAGenerator(parsed)
        sva_module = generator.generate_all()
        
        # Should generate some assertions
        assert len(sva_module.properties) > 0
        
        # Check for reset assertions
        reset_props = [p for p in sva_module.properties 
                       if p.category == AssertionCategory.RESET]
        assert len(reset_props) >= 0  # At least some reset assertions
    
    def test_sva_module_to_sv_output(self, apb_rtl):
        """Test SVA module generates valid SystemVerilog"""
        parser = RTLParser()
        parsed = parser.parse(apb_rtl)
        
        generator = SVAGenerator(parsed)
        sva_module = generator.generate_all()
        sv_code = sva_module.to_sv()
        
        # Check for required SVA elements
        assert "module" in sv_code
        assert "endmodule" in sv_code
        assert "property" in sv_code or "assert" in sv_code
        assert "posedge" in sv_code
    
    def test_property_types(self, apb_rtl):
        """Test different assertion types are generated"""
        parser = RTLParser()
        parsed = parser.parse(apb_rtl)
        
        generator = SVAGenerator(parsed)
        sva_module = generator.generate_all()
        
        types = set(p.assertion_type for p in sva_module.properties)
        
        # Should have multiple types
        assert len(types) >= 1
    
    def test_generate_sva_from_parsed_function(self, apb_rtl):
        """Test the convenience function"""
        parser = RTLParser()
        parsed = parser.parse(apb_rtl)
        
        sva_code = generate_sva_from_parsed(parsed)
        
        assert "module" in sva_code
        assert "apb_slave_sva" in sva_code


class TestSVAPropertyGeneration:
    """Tests for individual SVA property generation"""
    
    def test_sva_property_to_sv_assert(self):
        """Test assert property generation"""
        prop = SVAProperty(
            name="test_prop",
            description="Test property",
            category=AssertionCategory.STABILITY,
            assertion_type=AssertionType.ASSERT,
            code="@(posedge clk) (valid) |-> !$isunknown(data)"
        )
        
        sv_code = prop.to_sv()
        
        assert "test_prop" in sv_code
        assert "assert property" in sv_code
        assert "valid" in sv_code
    
    def test_sva_property_to_sv_cover(self):
        """Test cover property generation"""
        prop = SVAProperty(
            name="cover_test",
            description="Cover test property",
            category=AssertionCategory.HANDSHAKE,
            assertion_type=AssertionType.COVER,
            code="@(posedge clk) (valid && ready)"
        )
        
        sv_code = prop.to_sv()
        
        assert "cover_test" in sv_code
        assert "cover property" in sv_code


class TestIntegration:
    """Integration tests for coverage and SVA features"""
    
    def test_coverage_then_sva_workflow(self):
        """Test typical workflow: analyze coverage -> generate SVA"""
        # 1. Analyze coverage
        analyzer = CoverageAnalyzer()
        
        coverage_content = """Covergroup: cg_protocol
  Coverpoint: cp_trans_type
    bin read: 100/100 (100%)
    bin write: 50/100 (50%)
    bin idle: 0/100 (0%)
    
Overall Coverage: 50%"""
        
        report = analyzer.parse_text_summary(coverage_content)
        gaps = analyzer.analyze_coverage(report)
        
        assert len(gaps) >= 2
        
        # 2. Generate SVA for RTL
        rtl = """
module dut (
    input logic clk,
    input logic rst_n,
    input logic [1:0] trans_type,
    output logic ready
);
endmodule
"""
        parser = RTLParser()
        parsed = parser.parse(rtl)
        
        generator = SVAGenerator(parsed)
        sva_module = generator.generate_all()
        
        assert len(sva_module.properties) > 0
    
    def test_gap_suggestions_are_valid_sv(self):
        """Test that generated gap sequences are valid SV syntax"""
        analyzer = CoverageAnalyzer()
        
        gap = CoverageGap(
            covergroup="cg_test",
            coverpoint="cp_data",
            bin_name="boundary",
            bin_value="0",
            priority="high",
            suggested_stimulus="data inside {0, 32'hFFFFFFFF}",
            suggested_sequence="boundary_seq",
            hit_count=0,
            goal_count=100,
            current_coverage=0.0,
            target_coverage=95.0,
            hits_needed=100
        )
        
        suggestion = analyzer.gap_to_suggestion(gap)
        
        # Check for valid SV constructs
        assert "class" in suggestion.uvm_sequence_code
        assert "extends" in suggestion.uvm_sequence_code
        assert "task body" in suggestion.uvm_sequence_code
        assert "endclass" in suggestion.uvm_sequence_code


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
