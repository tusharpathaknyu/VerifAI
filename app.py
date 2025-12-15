"""
VerifAI Web UI
==============
Streamlit-based web interface for VerifAI UVM testbench generator.
"""

import streamlit as st
import os
import sys
import tempfile
import zipfile
import io
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.parser import SpecParser, ParsedSpec
from src.generator import UVMGenerator
from src.llm_client import get_llm_client, MockLLMClient

# Page configuration
st.set_page_config(
    page_title="VerifAI - AI UVM Generator",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        text-align: center;
        color: #666;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    .stTextArea textarea {
        font-family: 'Monaco', 'Menlo', monospace;
    }
    .file-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 1rem;
        color: #155724;
    }
    .protocol-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: bold;
        margin: 0.25rem;
    }
    .protocol-apb { background: #e3f2fd; color: #1565c0; }
    .protocol-axi { background: #f3e5f5; color: #7b1fa2; }
    .protocol-uart { background: #fff3e0; color: #ef6c00; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">🚀 VerifAI</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">AI-Powered UVM Testbench Generator</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # LLM Selection
    llm_choice = st.selectbox(
        "🤖 LLM Provider",
        ["gemini", "openai", "anthropic", "ollama", "mock"],
        index=0,
        help="Select the AI model to parse your specification"
    )
    
    # API Key input (if needed)
    if llm_choice == "gemini":
        api_key = st.text_input(
            "Google API Key",
            type="password",
            value=os.getenv("GOOGLE_API_KEY", ""),
            help="Get your free API key from Google AI Studio"
        )
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
    elif llm_choice == "openai":
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=os.getenv("OPENAI_API_KEY", ""),
        )
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
    
    st.divider()
    
    # Protocol quick select
    st.header("📦 Protocol Templates")
    
    protocol_templates = {
        "APB Register Block": "Create a UVM testbench for an APB slave with STATUS register at 0x00 (read-only), CONTROL register at 0x04 (read-write), DATA register at 0x08 (read-write), and CONFIG register at 0x0C (read-write)",
        "AXI4-Lite Memory": "AXI4-Lite memory controller testbench with 1KB address space, 32-bit data width, and read-after-write verification",
        "UART 8N1": "UART controller testbench with 115200 baud rate, 8 data bits, no parity, 1 stop bit, with error injection support",
        "UART with Flow Control": "UART testbench with 9600 baud, even parity, RTS/CTS hardware flow control, 16-byte FIFO",
        "SPI Master Mode 0": "SPI master controller testbench in Mode 0 (CPOL=0, CPHA=0), 8-bit data width, single slave, MSB first",
        "SPI Multi-Slave": "SPI master with 4 slave devices, Mode 3, 16-bit transfers, with QSPI support",
    }
    
    selected_template = st.selectbox(
        "Quick Templates",
        ["Custom..."] + list(protocol_templates.keys())
    )
    
    st.divider()
    
    # Info
    st.header("ℹ️ About")
    st.markdown("""
    **VerifAI** transforms natural language 
    specifications into production-ready 
    UVM testbenches.
    
    **Supported Protocols:**
    - ✅ APB (APB3/APB4)
    - ✅ AXI4-Lite
    - ✅ UART
    - ✅ SPI (NEW!)
    - 🔜 I2C
    
    [GitHub](https://github.com/tusharpathaknyu/VerifAI) | 
    [Documentation](#)
    """)

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📝 Specification")
    
    # Pre-fill with template if selected
    default_spec = ""
    if selected_template != "Custom...":
        default_spec = protocol_templates.get(selected_template, "")
    
    user_spec = st.text_area(
        "Describe your testbench in natural language:",
        value=default_spec,
        height=200,
        placeholder="Example: Create a UVM testbench for an APB slave with STATUS and CONTROL registers..."
    )
    
    # Generate button
    generate_btn = st.button("🚀 Generate UVM Testbench", type="primary", use_container_width=True)

with col2:
    st.header("📊 Parsed Specification")
    spec_placeholder = st.empty()

# Results section
if generate_btn and user_spec:
    with st.spinner("🤖 Parsing specification with AI..."):
        try:
            # Get LLM client
            if llm_choice == "mock":
                llm_client = MockLLMClient()
            else:
                llm_client = get_llm_client(llm_choice)
            
            # Parse specification
            parser = SpecParser(llm_client=llm_client)
            parsed_spec = parser.parse(user_spec)
            
            # Display parsed spec
            with spec_placeholder.container():
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Protocol", parsed_spec.protocol.upper())
                    st.metric("Data Width", f"{parsed_spec.data_width} bits")
                with col_b:
                    st.metric("Module", parsed_spec.module_name)
                    st.metric("Registers", len(parsed_spec.registers))
                
                if parsed_spec.registers:
                    st.subheader("📋 Registers")
                    reg_data = []
                    for reg in parsed_spec.registers:
                        reg_data.append({
                            "Name": reg.name,
                            "Address": f"0x{reg.address:02X}",
                            "Access": reg.access.value
                        })
                    st.table(reg_data)
            
        except Exception as e:
            st.error(f"❌ Error parsing specification: {str(e)}")
            st.stop()
    
    with st.spinner("⚙️ Generating UVM files..."):
        try:
            # Generate files
            template_dir = Path(__file__).parent / "templates"
            generator = UVMGenerator(str(template_dir))
            
            # Use temp directory
            with tempfile.TemporaryDirectory() as temp_dir:
                generated_files = generator.generate(parsed_spec, temp_dir)
                
                st.success(f"✅ Generated {len(generated_files)} files!")
                
                # Create tabs for different views
                tab1, tab2, tab3 = st.tabs(["📁 Files", "👁️ Preview", "⬇️ Download"])
                
                with tab1:
                    # Display generated files
                    cols = st.columns(3)
                    for i, gf in enumerate(generated_files):
                        with cols[i % 3]:
                            icon = "📦" if "pkg" in gf.filename else \
                                   "🔌" if "if" in gf.filename else \
                                   "🤖" if any(x in gf.filename for x in ["driver", "monitor", "agent"]) else \
                                   "📊" if any(x in gf.filename for x in ["scoreboard", "coverage"]) else \
                                   "🧪" if "test" in gf.filename else "📄"
                            st.markdown(f"""
                            <div class="file-card">
                                {icon} <strong>{gf.filename}</strong><br>
                                <small>{gf.category}</small>
                            </div>
                            """, unsafe_allow_html=True)
                
                with tab2:
                    # File preview
                    file_to_preview = st.selectbox(
                        "Select file to preview:",
                        [gf.filename for gf in generated_files]
                    )
                    
                    for gf in generated_files:
                        if gf.filename == file_to_preview:
                            st.code(gf.content, language="systemverilog")
                            break
                
                with tab3:
                    # Create ZIP for download
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                        for gf in generated_files:
                            zf.writestr(gf.filename, gf.content)
                    
                    zip_buffer.seek(0)
                    
                    st.download_button(
                        label="📥 Download All Files (ZIP)",
                        data=zip_buffer,
                        file_name=f"{parsed_spec.module_name}_uvm_tb.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                    
                    st.markdown("---")
                    st.markdown("**Individual Files:**")
                    
                    for gf in generated_files:
                        st.download_button(
                            label=f"📄 {gf.filename}",
                            data=gf.content,
                            file_name=gf.filename,
                            mime="text/plain",
                            key=f"dl_{gf.filename}"
                        )
                
        except Exception as e:
            st.error(f"❌ Error generating files: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; padding: 1rem;">
    Made with ❤️ by <a href="https://github.com/tusharpathaknyu">Tushar Pathak</a> | 
    <a href="https://github.com/tusharpathaknyu/VerifAI">⭐ Star on GitHub</a>
</div>
""", unsafe_allow_html=True)
