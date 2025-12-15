"""
UART Protocol Configuration
===========================
Configuration for UART (Universal Asynchronous Receiver-Transmitter) protocol.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class UARTConfig:
    """UART Protocol Configuration."""
    
    # Basic parameters
    data_bits: int = 8            # 5, 6, 7, or 8 data bits
    stop_bits: float = 1          # 1, 1.5, or 2 stop bits
    parity: str = 'none'          # 'none', 'even', 'odd', 'mark', 'space'
    baud_rate: int = 115200       # Common: 9600, 19200, 38400, 57600, 115200
    
    # Hardware flow control
    has_rts_cts: bool = False     # RTS/CTS hardware flow control
    has_dtr_dsr: bool = False     # DTR/DSR hardware flow control
    
    # FIFO options
    has_tx_fifo: bool = True      # Transmit FIFO
    has_rx_fifo: bool = True      # Receive FIFO
    fifo_depth: int = 16          # FIFO depth (commonly 16 or 64)
    
    # Features
    has_break_detect: bool = True    # Break condition detection
    has_frame_error: bool = True     # Framing error detection
    has_parity_error: bool = True    # Parity error detection
    has_overrun_error: bool = True   # Overrun error detection
    
    # DUT info
    dut_name: str = 'uart_dut'
    
    # Registers (typical UART register map)
    registers: List[Dict] = field(default_factory=lambda: [
        {'name': 'RBR_THR', 'address': '0x00', 'access': 'rw', 'description': 'Receive Buffer / Transmit Holding'},
        {'name': 'IER', 'address': '0x04', 'access': 'rw', 'description': 'Interrupt Enable Register'},
        {'name': 'IIR_FCR', 'address': '0x08', 'access': 'rw', 'description': 'Interrupt ID / FIFO Control'},
        {'name': 'LCR', 'address': '0x0C', 'access': 'rw', 'description': 'Line Control Register'},
        {'name': 'MCR', 'address': '0x10', 'access': 'rw', 'description': 'Modem Control Register'},
        {'name': 'LSR', 'address': '0x14', 'access': 'ro', 'description': 'Line Status Register'},
        {'name': 'MSR', 'address': '0x18', 'access': 'ro', 'description': 'Modem Status Register'},
        {'name': 'SCR', 'address': '0x1C', 'access': 'rw', 'description': 'Scratch Register'},
    ])
    
    @classmethod
    def from_dict(cls, config: dict) -> 'UARTConfig':
        """Create config from dictionary."""
        return cls(
            data_bits=config.get('data_bits', 8),
            stop_bits=config.get('stop_bits', 1),
            parity=config.get('parity', 'none'),
            baud_rate=config.get('baud_rate', 115200),
            has_rts_cts=config.get('has_rts_cts', False),
            has_dtr_dsr=config.get('has_dtr_dsr', False),
            has_tx_fifo=config.get('has_tx_fifo', True),
            has_rx_fifo=config.get('has_rx_fifo', True),
            fifo_depth=config.get('fifo_depth', 16),
            dut_name=config.get('dut_name', 'uart_dut'),
            registers=config.get('registers', cls.registers.default),
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            'protocol': 'uart',
            'data_bits': self.data_bits,
            'stop_bits': self.stop_bits,
            'parity': self.parity,
            'baud_rate': self.baud_rate,
            'has_rts_cts': self.has_rts_cts,
            'has_dtr_dsr': self.has_dtr_dsr,
            'has_tx_fifo': self.has_tx_fifo,
            'has_rx_fifo': self.has_rx_fifo,
            'fifo_depth': self.fifo_depth,
            'has_break_detect': self.has_break_detect,
            'has_frame_error': self.has_frame_error,
            'has_parity_error': self.has_parity_error,
            'has_overrun_error': self.has_overrun_error,
            'dut_name': self.dut_name,
            'registers': self.registers,
            # Computed fields
            'bit_period_ns': int(1e9 / self.baud_rate),
            'frame_bits': self.data_bits + 1 + (1 if self.parity != 'none' else 0) + int(self.stop_bits),
        }


# Default UART configuration
DEFAULT_UART_CONFIG = {
    'protocol': 'uart',
    'data_bits': 8,
    'stop_bits': 1,
    'parity': 'none',
    'baud_rate': 115200,
    'has_rts_cts': False,
    'has_dtr_dsr': False,
    'has_tx_fifo': True,
    'has_rx_fifo': True,
    'fifo_depth': 16,
    'has_break_detect': True,
    'has_frame_error': True,
    'has_parity_error': True,
    'has_overrun_error': True,
    'dut_name': 'uart_dut',
    'bit_period_ns': 8680,  # ~115200 baud
    'frame_bits': 10,       # 1 start + 8 data + 1 stop
    'registers': [
        {'name': 'RBR_THR', 'address': '0x00', 'access': 'rw'},
        {'name': 'IER', 'address': '0x04', 'access': 'rw'},
        {'name': 'IIR_FCR', 'address': '0x08', 'access': 'rw'},
        {'name': 'LCR', 'address': '0x0C', 'access': 'rw'},
        {'name': 'MCR', 'address': '0x10', 'access': 'rw'},
        {'name': 'LSR', 'address': '0x14', 'access': 'ro'},
        {'name': 'MSR', 'address': '0x18', 'access': 'ro'},
        {'name': 'SCR', 'address': '0x1C', 'access': 'rw'},
    ],
}
