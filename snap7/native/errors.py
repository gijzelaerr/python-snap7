"""
S7 error handling and exception classes.

Maps S7 error codes to Python exceptions with meaningful messages.
"""

from typing import Optional


class S7Error(Exception):
    """Base exception for all S7 protocol errors."""
    
    def __init__(self, message: str, error_code: Optional[int] = None):
        super().__init__(message)
        self.error_code = error_code


class S7ConnectionError(S7Error):
    """Raised when connection to S7 device fails."""
    pass


class S7ProtocolError(S7Error):
    """Raised when S7 protocol communication fails."""
    pass


class S7TimeoutError(S7Error):
    """Raised when S7 operation times out."""
    pass


class S7AuthenticationError(S7Error):
    """Raised when S7 authentication fails."""
    pass


# S7 Error code mappings from original Snap7 C library
S7_ERROR_CODES = {
    0x00000000: "Success",
    0x00100000: "ISO connection failed",
    0x00200000: "S7 connection failed", 
    0x00300000: "Multi-variable operations not supported",
    0x00400000: "Wrong variable format",
    0x00500000: "Object not found",
    0x00600000: "Invalid item count",
    0x00700000: "Invalid area",
    0x00800000: "Invalid DB number",
    0x00900000: "Invalid start address",
    0x00A00000: "Invalid size",
    0x00B00000: "Invalid data type",
    0x00C00000: "Invalid PDU length",
    0x00D00000: "Invalid parameter",
    0x01000000: "Partial data written",
    0x02000000: "Buffer too small",
    0x03000000: "Function not available",
    0x04000000: "Data cannot be read",
    0x05000000: "Data cannot be written",
    0x06000000: "Data block is protected",
    0x07000000: "Address out of range",
    0x81000000: "TCP socket error",
    0x82000000: "TCP connection timeout",
    0x83000000: "TCP data send error",
    0x84000000: "TCP data receive error",
    0x85000000: "TCP disconnected by peer",
    0x86000000: "TCP generic socket error",
}


def get_error_message(error_code: int) -> str:
    """Get human-readable error message for S7 error code."""
    return S7_ERROR_CODES.get(error_code, f"Unknown error: {error_code:#08x}")


def check_error(error_code: int, context: str = "") -> None:
    """Check S7 error code and raise appropriate exception if error occurred."""
    if error_code == 0:
        return
        
    message = get_error_message(error_code)
    if context:
        message = f"{context}: {message}"
        
    # Map to specific exception types
    if (error_code & 0xFF000000) == 0x81000000:  # TCP socket errors
        raise S7ConnectionError(message, error_code)
    elif error_code in [0x00100000, 0x00200000]:  # Connection errors
        raise S7ConnectionError(message, error_code)
    elif error_code == 0x82000000:  # Timeout
        raise S7TimeoutError(message, error_code)
    else:
        raise S7ProtocolError(message, error_code)