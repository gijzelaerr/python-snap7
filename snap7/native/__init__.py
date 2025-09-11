"""
Pure Python implementation of Snap7 S7 protocol.

This module provides a complete Python implementation of the Siemens S7 protocol,
eliminating the need for the native Snap7 C library and DLL dependencies.

Architecture:
- Application Layer: High-level S7 client API
- S7 Protocol Layer: S7 PDU encoding/decoding and operations  
- ISO on TCP Layer: TPKT/COTP frame handling (RFC 1006)
- Socket Layer: TCP socket connection management
- Platform Layer: Cross-platform compatibility

Components:
- S7Client: Main client interface (drop-in replacement for ctypes version)
- S7Protocol: S7 PDU message encoding/decoding
- ISOTCPConnection: ISO on TCP connection management
- S7DataTypes: S7 data type definitions and conversions
- S7Errors: Error handling and exception mapping
"""

from .client import S7Client
from .protocol import S7Protocol
from .connection import ISOTCPConnection
from .datatypes import S7DataTypes
from .errors import S7Error, S7ConnectionError, S7ProtocolError
from .server import S7Server

__all__ = [
    'S7Client',
    'S7Server',
    'S7Protocol', 
    'ISOTCPConnection',
    'S7DataTypes',
    'S7Error',
    'S7ConnectionError', 
    'S7ProtocolError'
]