"""
VerifAI - UVM Testbench Generator
"""

import streamlit as st
import os
import google.generativeai as genai
from src.templates import PROTOCOL_TEMPLATES
from src.rtl_parser import parse_rtl
from src.spec_import import SpecParser
from src.rtl_aware_gen import RTLAwareGenerator
from src.coverage_analyzer import CoverageAnalyzer
from src.sva_generator import SVAGenerator

st.set_page_config(
    page_title="VerifAI",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Vibrant modern CSS
st.markdown("""
<style>
    /* Hide defaults */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding: 2rem 3rem 6rem 3rem; max-width: 1400px;}
    
    /* Gradient background */
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    
    /* Animated gradient border effect */
    @keyframes gradient-shift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Navigation */
    .nav {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5rem 0 1.5rem;
        margin-bottom: 1rem;
    }
    .logo {
        font-size: 1.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #00d4ff, #7b2ff7, #f107a3);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
    }
    .nav-link {
        color: #888;
        text-decoration: none;
        font-size: 0.9rem;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.1);
        transition: all 0.3s;
    }
    .nav-link:hover {
        border-color: #7b2ff7;
        color: #fff;
    }
    
    /* Hero */
    .hero {
        text-align: center;
        padding: 2rem 0 2.5rem;
    }
    .hero h1 {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #fff 0%, #a0a0ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.8rem;
        letter-spacing: -1px;
    }
    .hero p {
        color: #8888aa;
        font-size: 1.1rem;
        max-width: 550px;
        margin: 0 auto;
        line-height: 1.6;
    }
    
    /* Protocol pills */
    .pills {
        display: flex;
        justify-content: center;
        gap: 0.5rem;
        margin: 1.5rem 0 2rem;
        flex-wrap: wrap;
    }
    .pill {
        background: rgba(123, 47, 247, 0.15);
        border: 1px solid rgba(123, 47, 247, 0.3);
        color: #b388ff;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    /* Tabs - colorful underline */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255,255,255,0.02);
        border-radius: 12px;
        padding: 0.5rem;
        gap: 0.5rem;
        justify-content: center;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #666;
        padding: 0.8rem 1.5rem;
        font-size: 0.9rem;
        border-radius: 8px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #7b2ff7 0%, #f107a3 100%) !important;
        color: white !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #aaa;
        background: rgba(255,255,255,0.05);
    }
    
    /* Cards */
    .card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.5rem;
    }
    
    /* Text area */
    .stTextArea textarea {
        background: rgba(0,0,0,0.3) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important;
        color: #e0e0e0 !important;
        font-family: 'JetBrains Mono', 'SF Mono', monospace !important;
        font-size: 0.85rem !important;
        padding: 1rem !important;
    }
    .stTextArea textarea:focus {
        border-color: #7b2ff7 !important;
        box-shadow: 0 0 20px rgba(123, 47, 247, 0.2) !important;
    }
    .stTextArea textarea::placeholder {
        color: #555 !important;
    }
    
    /* Primary buttons - gradient */
    .stButton > button[kind="primary"], 
    .stButton > button {
        background: linear-gradient(135deg, #7b2ff7 0%, #f107a3 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.8rem 2rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.3s !important;
        cursor: pointer !important;
        width: 100%;
        margin-top: 0.5rem;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(123, 47, 247, 0.4) !important;
    }
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* Secondary/sample buttons */
    div[data-testid="column"] .stButton > button {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        color: #aaa !important;
        padding: 0.5rem 1rem !important;
        font-size: 0.85rem !important;
    }
    div[data-testid="column"] .stButton > button:hover {
        background: rgba(255,255,255,0.1) !important;
        border-color: #7b2ff7 !important;
        color: #fff !important;
        box-shadow: none !important;
        transform: none !important;
    }
    
    /* Make the main generate button stand out */
    [data-testid="column"]:last-child .stButton > button,
    .element-container:last-child .stButton > button {
        background: linear-gradient(135deg, #7b2ff7 0%, #f107a3 100%) !important;
        color: white !important;
        border: none !important;
    }
    
    /* Download button */
    .stDownloadButton > button {
        background: rgba(0, 212, 255, 0.1) !important;
        border: 1px solid rgba(0, 212, 255, 0.3) !important;
        color: #00d4ff !important;
    }
    .stDownloadButton > button:hover {
        background: rgba(0, 212, 255, 0.2) !important;
        box-shadow: 0 4px 15px rgba(0, 212, 255, 0.2) !important;
    }
    
    /* Code blocks */
    .stCodeBlock {
        border-radius: 12px !important;
    }
    pre {
        background: rgba(0,0,0,0.4) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        background: linear-gradient(135deg, #00d4ff, #7b2ff7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2rem !important;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        color: #666;
    }
    
    /* Selectbox */
    .stSelectbox > div > div {
        background: rgba(0,0,0,0.3) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 10px !important;
    }
    .stSelectbox > div > div:hover {
        border-color: #7b2ff7 !important;
    }
    
    /* Slider */
    .stSlider > div > div > div {
        background: linear-gradient(135deg, #7b2ff7, #f107a3) !important;
    }
    .stSlider > div > div > div > div {
        background: #fff !important;
    }
    
    /* Radio */
    .stRadio > div {
        flex-direction: row;
        gap: 1rem;
    }
    .stRadio label span {
        color: #888 !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(255,255,255,0.03) !important;
        border-radius: 10px !important;
    }
    
    /* Success/warning */
    .stSuccess {
        background: rgba(0, 255, 136, 0.1) !important;
        border: 1px solid rgba(0, 255, 136, 0.2) !important;
        border-radius: 10px !important;
    }
    .stWarning {
        background: rgba(255, 193, 7, 0.1) !important;
        border: 1px solid rgba(255, 193, 7, 0.2) !important;
        border-radius: 10px !important;
    }
    .stInfo {
        background: rgba(123, 47, 247, 0.1) !important;
        border: 1px solid rgba(123, 47, 247, 0.2) !important;
        border-radius: 10px !important;
    }
    
    /* Footer */
    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 1rem 3rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.85rem;
        background: linear-gradient(transparent, rgba(26, 26, 46, 0.95));
        backdrop-filter: blur(10px);
    }
    .footer-left {
        color: #666;
    }
    .footer-right a {
        color: #7b2ff7;
        text-decoration: none;
        padding: 0.4rem 1rem;
        border: 1px solid rgba(123, 47, 247, 0.3);
        border-radius: 20px;
        transition: all 0.3s;
    }
    .footer-right a:hover {
        background: rgba(123, 47, 247, 0.1);
        border-color: #7b2ff7;
    }
    
    /* Placeholder text */
    .placeholder-text {
        color: #555;
        text-align: center;
        padding: 3rem;
        border: 2px dashed rgba(255,255,255,0.1);
        border-radius: 12px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Navigation
st.markdown("""
<div class="nav">
    <div class="logo">VerifAI</div>
    <a href="https://github.com/tusharpathaknyu/VerifAI" target="_blank" class="nav-link">GitHub</a>
</div>
""", unsafe_allow_html=True)

# Hero
st.markdown("""
<div class="hero">
    <h1>UVM Testbench Generator</h1>
    <p>Transform your RTL into production-ready verification components instantly</p>
</div>
<div class="pills">
    <span class="pill">APB</span>
    <span class="pill">AXI4-Lite</span>
    <span class="pill">UART</span>
    <span class="pill">SPI</span>
    <span class="pill">I2C</span>
</div>
""", unsafe_allow_html=True)

# LLM setup
def get_llm():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if api_key:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-1.5-flash')
    return None

def generate_with_llm(prompt: str) -> str:
    model = get_llm()
    if not model:
        return "Error: API key not configured."
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# Sample RTL
SAMPLE_APB = '''module apb_slave (
    input  wire        pclk,
    input  wire        presetn,
    input  wire        psel,
    input  wire        penable,
    input  wire        pwrite,
    input  wire [31:0] paddr,
    input  wire [31:0] pwdata,
    output reg  [31:0] prdata,
    output reg         pready,
    output reg         pslverr
);
    reg [31:0] mem [0:255];
    localparam IDLE = 2'b00, SETUP = 2'b01, ACCESS = 2'b10;
    reg [1:0] state, next_state;
    
    always @(posedge pclk or negedge presetn) begin
        if (!presetn) state <= IDLE;
        else state <= next_state;
    end
endmodule'''

SAMPLE_AXI = '''module axi_lite_slave (
    input  wire        aclk,
    input  wire        aresetn,
    input  wire        awvalid,
    output reg         awready,
    input  wire [31:0] awaddr,
    input  wire        wvalid,
    output reg         wready,
    input  wire [31:0] wdata,
    output reg         bvalid,
    input  wire        bready,
    output reg  [1:0]  bresp,
    input  wire        arvalid,
    output reg         arready,
    input  wire [31:0] araddr,
    output reg         rvalid,
    input  wire        rready,
    output reg  [31:0] rdata,
    output reg  [1:0]  rresp
);
    reg [31:0] registers [0:15];
endmodule'''

# Tabs
tabs = st.tabs(["RTL to Testbench", "Protocol Templates", "Coverage Analysis", "SVA Assertions"])

# Tab 1: RTL-Aware Generator
with tabs[0]:
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.markdown("##### Paste your RTL")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("Try APB", key="sample_apb"):
                st.session_state['rtl_input'] = SAMPLE_APB
        with c2:
            if st.button("Try AXI", key="sample_axi"):
                st.session_state['rtl_input'] = SAMPLE_AXI
        
        rtl_code = st.text_area(
            "RTL",
            value=st.session_state.get('rtl_input', ''),
            height=380,
            placeholder="module my_design (\n    input  wire clk,\n    input  wire rst_n,\n    // your signals...\n);",
            label_visibility="collapsed"
        )
        
        st.markdown("")  # spacing
        if st.button("Generate Testbench", type="primary", key="gen_rtl"):
            if rtl_code:
                with st.spinner("Generating..."):
                    try:
                        parsed = parse_rtl(rtl_code)
                        st.session_state['parsed'] = parsed
                        st.session_state['rtl_result'] = True
                        
                        generator = RTLAwareGenerator()
                        prompt = generator.generate_prompt(parsed)
                        result = generate_with_llm(prompt)
                        st.session_state['generated_code'] = result
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            else:
                st.warning("Paste RTL code first")
    
    with col2:
        st.markdown("##### Generated Output")
        
        if st.session_state.get('rtl_result') and st.session_state.get('parsed'):
            parsed = st.session_state['parsed']
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Inputs", len(parsed.inputs))
            c2.metric("Outputs", len(parsed.outputs))
            c3.metric("FSM", "Yes" if parsed.fsm else "No")
            
            if st.session_state.get('generated_code'):
                st.code(st.session_state['generated_code'], language="systemverilog")
                st.download_button("Download", st.session_state['generated_code'], 
                                   f"{parsed.module_name}_tb.sv", use_container_width=True)
        else:
            st.markdown("""
            <div class="placeholder-text">
                <p>Your generated testbench will appear here</p>
            </div>
            """, unsafe_allow_html=True)

# Tab 2: Protocol Templates
with tabs[1]:
    col1, col2 = st.columns([1, 2], gap="large")
    
    with col1:
        st.markdown("##### Configure Protocol")
        
        protocol = st.selectbox("Protocol", ["APB", "AXI4-Lite", "UART", "SPI", "I2C"])
        
        if protocol == "APB":
            addr_w = st.select_slider("Address Width", [8, 16, 32, 64], value=32)
            data_w = st.select_slider("Data Width", [8, 16, 32, 64], value=32)
            config = {"addr_width": addr_w, "data_width": data_w}
        elif protocol == "AXI4-Lite":
            addr_w = st.select_slider("Address Width", [8, 16, 32, 64], value=32)
            data_w = st.selectbox("Data Width", [32, 64])
            config = {"addr_width": addr_w, "data_width": data_w}
        elif protocol == "UART":
            baud = st.selectbox("Baud Rate", [9600, 19200, 38400, 57600, 115200])
            config = {"baud_rate": baud}
        elif protocol == "SPI":
            mode = st.selectbox("SPI Mode", ["Mode 0 (CPOL=0, CPHA=0)", "Mode 1", "Mode 2", "Mode 3"])
            config = {"mode": mode}
        else:
            speed = st.selectbox("Speed", ["Standard 100kHz", "Fast 400kHz", "Fast+ 1MHz"])
            config = {"speed": speed}
        
        st.markdown("")
        if st.button("Generate", type="primary", key="gen_proto"):
            with st.spinner("Generating..."):
                template = PROTOCOL_TEMPLATES.get(protocol.lower().replace("-", "_").replace("4_", "4"), 
                                                  PROTOCOL_TEMPLATES.get("apb", ""))
                prompt = f"""Generate a complete UVM testbench for {protocol}.
Config: {config}
Include: interface, sequence_item, driver, monitor, agent, scoreboard, env, test, coverage.
{template}"""
                result = generate_with_llm(prompt)
                st.session_state['proto_result'] = result
    
    with col2:
        st.markdown("##### Generated Testbench")
        if st.session_state.get('proto_result'):
            st.code(st.session_state['proto_result'], language="systemverilog")
            st.download_button("Download", st.session_state['proto_result'], 
                               f"{protocol.lower()}_tb.sv", use_container_width=True)
        else:
            st.markdown("""
            <div class="placeholder-text">
                <p>Select protocol and click Generate</p>
            </div>
            """, unsafe_allow_html=True)

# Tab 3: Coverage Analysis
with tabs[2]:
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.markdown("##### Paste Coverage Report")
        
        cov_text = st.text_area(
            "Coverage",
            height=350,
            placeholder="Functional Coverage: 75%\n  - read_cg: 80%\n  - write_cg: 70%\n\nUncovered bins:\n  - burst_read: 0 hits",
            label_visibility="collapsed"
        )
        
        st.markdown("")
        if st.button("Analyze", type="primary", key="analyze_cov"):
            if cov_text:
                with st.spinner("Analyzing..."):
                    try:
                        analyzer = CoverageAnalyzer()
                        analysis = analyzer.analyze(cov_text)
                        st.session_state['cov_result'] = analysis
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            else:
                st.warning("Paste coverage report first")
    
    with col2:
        st.markdown("##### Analysis")
        if st.session_state.get('cov_result'):
            analysis = st.session_state['cov_result']
            metrics = analysis.get('metrics', {})
            
            c1, c2 = st.columns(2)
            c1.metric("Functional", f"{metrics.get('functional', 0)}%")
            c2.metric("Code", f"{metrics.get('code', 0)}%")
            
            gaps = analysis.get('gaps', [])
            if gaps:
                st.markdown("**Gaps Found:**")
                for gap in gaps:
                    st.warning(gap)
            
            suggestions = analysis.get('suggestions', [])
            if suggestions:
                st.markdown("**Suggestions:**")
                for s in suggestions:
                    st.info(s)
        else:
            st.markdown("""
            <div class="placeholder-text">
                <p>Coverage analysis will appear here</p>
            </div>
            """, unsafe_allow_html=True)

# Tab 4: SVA Generator
with tabs[3]:
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        st.markdown("##### Input")
        
        mode = st.radio("Type", ["From RTL", "From Description"], horizontal=True, label_visibility="collapsed")
        
        if mode == "From RTL":
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if st.button("Try APB", key="sva_apb"):
                    st.session_state['sva_input'] = SAMPLE_APB
            with c2:
                if st.button("Try AXI", key="sva_axi"):
                    st.session_state['sva_input'] = SAMPLE_AXI
            
            sva_input = st.text_area(
                "SVA Input",
                value=st.session_state.get('sva_input', ''),
                height=300,
                placeholder="// Paste RTL...",
                label_visibility="collapsed"
            )
        else:
            sva_input = st.text_area(
                "SVA Input",
                height=330,
                placeholder="Describe assertions:\n- Request acknowledged in 4 cycles\n- Data valid only when enable high\n- Reset clears all outputs",
                label_visibility="collapsed"
            )
        
        st.markdown("")
        if st.button("Generate Assertions", type="primary", key="gen_sva"):
            if sva_input:
                with st.spinner("Generating..."):
                    try:
                        if mode == "From RTL":
                            parsed = parse_rtl(sva_input)
                            sva_gen = SVAGenerator()
                            assertions = sva_gen.generate_from_rtl(parsed)
                            combined = "\n\n".join([f"// {a['name']}\n{a['code']}" for a in assertions])
                            st.session_state['sva_result'] = combined
                            st.session_state['sva_module'] = parsed.module_name
                        else:
                            prompt = f"Generate SVA assertions for:\n{sva_input}\n\nUse ##, |=>, throughout syntax."
                            st.session_state['sva_result'] = generate_with_llm(prompt)
                            st.session_state['sva_module'] = "custom"
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            else:
                st.warning("Provide input first")
    
    with col2:
        st.markdown("##### Generated SVA")
        if st.session_state.get('sva_result'):
            st.code(st.session_state['sva_result'], language="systemverilog")
            st.download_button("Download", st.session_state['sva_result'], 
                               f"{st.session_state.get('sva_module', 'assertions')}_sva.sv", 
                               use_container_width=True)
        else:
            st.markdown("""
            <div class="placeholder-text">
                <p>Assertions will appear here</p>
            </div>
            """, unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="footer">
    <span class="footer-left">Built by Tushar Pathak</span>
    <span class="footer-right"><a href="https://github.com/tusharpathaknyu/VerifAI" target="_blank">View on GitHub</a></span>
</div>
""", unsafe_allow_html=True)
