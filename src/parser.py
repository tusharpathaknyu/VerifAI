"""
Natural Language Parser - Converts user specifications to structured data
"""

import json
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from .llm_client import BaseLLMClient, get_llm_client


class AccessType(Enum):
    RO = "RO"  # Read-only
    RW = "RW"  # Read-write
    WO = "WO"  # Write-only
    W1C = "W1C"  # Write-1-to-clear
    W1S = "W1S"  # Write-1-to-set


@dataclass
class Register:
    """Represents a hardware register"""
    name: str
    address: int
    access: AccessType = AccessType.RW
    reset_value: int = 0
    width: int = 32
    description: str = ""
    fields: List[Dict] = field(default_factory=list)


@dataclass 
class ParsedSpec:
    """Parsed specification structure"""
    protocol: str
    module_name: str
    data_width: int = 32
    addr_width: int = 32
    registers: List[Register] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    clock_name: str = "clk"
    reset_name: str = "rst_n"
    reset_active_low: bool = True
    
    # Protocol-specific options
    axi_id_width: int = 4
    axi_outstanding: int = 4
    apb_version: int = 3  # APB3 or APB4
    
    # UART-specific options
    baud_rate: int = 115200
    data_bits: int = 8
    stop_bits: float = 1
    parity: str = "none"
    has_rts_cts: bool = False
    has_tx_fifo: bool = True
    has_rx_fifo: bool = True
    fifo_depth: int = 16
    
    # SPI-specific options
    spi_mode: int = 0  # 0-3 (CPOL/CPHA combinations)
    spi_num_slaves: int = 1
    spi_msb_first: bool = True
    spi_clock_divider: int = 2
    spi_cs_setup_time: int = 1
    spi_cs_hold_time: int = 1
    spi_supports_qspi: bool = False


SYSTEM_PROMPT = """You are an expert hardware verification engineer specializing in UVM (Universal Verification Methodology) and AMBA protocols.

Your task is to parse natural language specifications and extract structured information for generating UVM testbenches.

You must respond with ONLY a valid JSON object (no markdown, no explanation) with this structure:
{
    "protocol": "apb" or "axi4lite" or "axi4" or "ahb" or "uart" or "spi" or "i2c",
    "module_name": "string - derived from the spec or default to protocol_dut",
    "data_width": integer (default 32, for UART default 8),
    "addr_width": integer (default 32),
    "registers": [
        {
            "name": "REGISTER_NAME",
            "address": "0xNN" (hex string),
            "access": "RO" or "RW" or "WO" or "W1C" or "W1S",
            "reset_value": "0xNN" (hex string),
            "description": "optional description"
        }
    ],
    "features": ["scoreboard", "coverage", "sequences", "ral"],
    "clock_name": "clk" (default),
    "reset_name": "rst_n" (default),
    "reset_active_low": true (default),
    
    // UART-specific fields (only if protocol is "uart"):
    "baud_rate": 115200 (default),
    "data_bits": 8 (5, 6, 7, or 8),
    "stop_bits": 1 (1, 1.5, or 2),
    "parity": "none" or "even" or "odd" or "mark" or "space",
    "has_rts_cts": false (hardware flow control),
    "has_fifo": true (TX/RX FIFO),
    "fifo_depth": 16,
    
    // SPI-specific fields (only if protocol is "spi"):
    "spi_mode": 0 (0, 1, 2, or 3 - CPOL/CPHA combinations),
    "spi_num_slaves": 1 (number of slave devices),
    "spi_msb_first": true (MSB or LSB first transmission),
    "spi_clock_divider": 2 (system clock to SPI clock divider),
    "spi_supports_qspi": false (Quad SPI support)
}

Rules:
1. Infer the protocol from context (APB for simple registers, AXI for complex/high-performance, UART for serial)
2. Parse register addresses from hex (0x00) or decimal
3. Default access type is RW if not specified
4. Always include scoreboard, coverage, and sequences in features
5. Include "ral" in features if registers are specified
6. Use snake_case for module_name
7. Use UPPER_CASE for register names
8. For UART: detect baud rate, parity, data bits from specification
"""


class SpecParser:
    """Parses natural language specifications into structured data"""
    
    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm_client = llm_client or get_llm_client("auto")
    
    def parse(self, user_spec: str) -> ParsedSpec:
        """
        Parse a natural language specification.
        
        Args:
            user_spec: Natural language description of the testbench
            
        Returns:
            ParsedSpec object with extracted information
        """
        # Use LLM to parse the specification
        response = self.llm_client.generate(
            prompt=f"Parse this hardware specification:\n\n{user_spec}",
            system_prompt=SYSTEM_PROMPT
        )
        
        # Extract JSON from response
        json_data = self._extract_json(response.content)
        
        # Convert to ParsedSpec
        return self._to_parsed_spec(json_data)
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response (handles markdown code blocks)"""
        # Try to find JSON in code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            text = json_match.group(1)
        
        # Try to find raw JSON object
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            text = json_match.group(0)
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}\nResponse: {text}")
    
    def _to_parsed_spec(self, data: Dict[str, Any]) -> ParsedSpec:
        """Convert JSON dict to ParsedSpec object"""
        registers = []
        for reg_data in data.get("registers", []):
            # Parse address (handle hex strings)
            addr = reg_data.get("address", "0x0")
            if isinstance(addr, str):
                addr = int(addr, 16) if addr.startswith("0x") else int(addr)
            
            # Parse reset value
            reset_val = reg_data.get("reset_value", "0x0")
            if isinstance(reset_val, str):
                reset_val = int(reset_val, 16) if reset_val.startswith("0x") else int(reset_val)
            
            # Parse access type
            access_str = reg_data.get("access", "RW").upper()
            try:
                access = AccessType[access_str]
            except KeyError:
                access = AccessType.RW
            
            registers.append(Register(
                name=reg_data.get("name", "UNNAMED").upper(),
                address=addr,
                access=access,
                reset_value=reset_val,
                width=reg_data.get("width", 32),
                description=reg_data.get("description", "")
            ))
        
        # Ensure default features
        features = data.get("features", [])
        default_features = ["scoreboard", "coverage", "sequences"]
        for feat in default_features:
            if feat not in features:
                features.append(feat)
        if registers and "ral" not in features:
            features.append("ral")
        
        # Determine protocol and set defaults
        protocol = data.get("protocol", "apb").lower()
        data_width = data.get("data_width", 8 if protocol == "uart" else 32)
        
        return ParsedSpec(
            protocol=protocol,
            module_name=data.get("module_name", "dut"),
            data_width=data_width,
            addr_width=data.get("addr_width", 32),
            registers=registers,
            features=features,
            clock_name=data.get("clock_name", "clk"),
            reset_name=data.get("reset_name", "rst_n"),
            reset_active_low=data.get("reset_active_low", True),
            # UART-specific
            baud_rate=data.get("baud_rate", 115200),
            data_bits=data.get("data_bits", 8),
            stop_bits=data.get("stop_bits", 1),
            parity=data.get("parity", "none"),
            has_rts_cts=data.get("has_rts_cts", False),
            has_tx_fifo=data.get("has_tx_fifo", True),
            has_rx_fifo=data.get("has_rx_fifo", True),
            fifo_depth=data.get("fifo_depth", 16),
            # SPI-specific
            spi_mode=data.get("spi_mode", 0),
            spi_num_slaves=data.get("spi_num_slaves", 1),
            spi_msb_first=data.get("spi_msb_first", True),
            spi_clock_divider=data.get("spi_clock_divider", 2),
            spi_cs_setup_time=data.get("spi_cs_setup_time", 1),
            spi_cs_hold_time=data.get("spi_cs_hold_time", 1),
            spi_supports_qspi=data.get("spi_supports_qspi", False),
        )
    
    def parse_quick(self, user_spec: str) -> ParsedSpec:
        """
        Quick parse without LLM - uses regex patterns.
        Useful for simple specs or when LLM is unavailable.
        """
        spec = ParsedSpec(
            protocol="apb",
            module_name="dut"
        )
        
        # Detect protocol
        spec_lower = user_spec.lower()
        if "axi4-lite" in spec_lower or "axi4lite" in spec_lower or "axi lite" in spec_lower:
            spec.protocol = "axi4lite"
        elif "axi4" in spec_lower or "axi" in spec_lower:
            spec.protocol = "axi4lite"  # Default to lite
        elif "ahb" in spec_lower:
            spec.protocol = "ahb"
        elif "uart" in spec_lower or "serial" in spec_lower or "rs232" in spec_lower:
            spec.protocol = "uart"
            spec.data_width = 8  # UART is typically 8-bit
        elif "spi" in spec_lower or "serial peripheral" in spec_lower:
            spec.protocol = "spi"
            spec.data_width = 8  # SPI is typically 8-bit
        elif "i2c" in spec_lower or "iic" in spec_lower:
            spec.protocol = "i2c"
        else:
            spec.protocol = "apb"
        
        # Extract module name
        name_match = re.search(r'(?:for|named?)\s+["\']?(\w+)["\']?', spec_lower)
        if name_match:
            spec.module_name = name_match.group(1)
        else:
            spec.module_name = f"{spec.protocol}_dut"
        
        # Extract data width
        width_match = re.search(r'(\d+)\s*-?\s*bit', spec_lower)
        if width_match:
            spec.data_width = int(width_match.group(1))
        
        # Extract registers (pattern: NAME at 0xNN or NAME (0xNN))
        reg_pattern = r'(\w+)\s+(?:register\s+)?(?:at\s+|@\s*|\()(0x[0-9a-fA-F]+|\d+)\)?(?:\s*[\(,]\s*(RO|RW|WO|W1C|W1S|read[- ]?only|read[- ]?write|write[- ]?only))?'
        for match in re.finditer(reg_pattern, user_spec, re.IGNORECASE):
            name = match.group(1).upper()
            addr_str = match.group(2)
            access_str = match.group(3)
            
            addr = int(addr_str, 16) if addr_str.startswith("0x") else int(addr_str)
            
            access = AccessType.RW
            if access_str:
                access_str = access_str.upper().replace("-", "").replace(" ", "")
                if access_str in ["RO", "READONLY"]:
                    access = AccessType.RO
                elif access_str in ["WO", "WRITEONLY"]:
                    access = AccessType.WO
            
            spec.registers.append(Register(
                name=name,
                address=addr,
                access=access
            ))
        
        # Set default features
        spec.features = ["scoreboard", "coverage", "sequences"]
        if spec.registers:
            spec.features.append("ral")
        
        return spec
