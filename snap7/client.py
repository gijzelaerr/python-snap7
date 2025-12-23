"""
Snap7 client base class and factory.
"""

from typing import Optional
from datetime import datetime
from snap7.type import Area, BlocksList, S7CpuInfo, TS7BlockInfo, Block


class Client:
    """
    Base class and factory for Snap7 client implementations.

    This class serves as both:
    1. An abstract base class defining the interface all clients must implement
    2. A factory that returns the appropriate concrete implementation

    When instantiated, returns either:
    - A ClibClient (ctypes-based, using Snap7 C library) when pure_python=False (default)
    - An S7Client (pure Python implementation) when pure_python=True

    Args:
        lib_location: Full path to the snap7.dll/.so file. Only used when pure_python=False.
        pure_python: If True, returns pure Python client. If False (default), returns ctypes client.

    Examples:
        >>> import snap7
        >>> # Get ctypes-based client (requires Snap7 C library)
        >>> client = snap7.Client()
        >>> client = snap7.Client(lib_location="/path/to/snap7.dll")
        >>>
        >>> # Get pure Python client (no C library needed)
        >>> client = snap7.Client(pure_python=True)
    """

    def __new__(cls, lib_location: Optional[str] = None, pure_python: bool = False):
        """
        Factory method to create the appropriate client instance.

        Args:
            lib_location: Path to Snap7 C library (ignored if pure_python=True).
            pure_python: If True, return pure Python implementation; otherwise ctypes implementation.

        Returns:
            ClibClient or S7Client instance.
        """
        # Only use factory pattern when called on the base Client class
        if cls is Client:
            if pure_python:
                from snap7.native.wire_client import WireClient
                return object.__new__(WireClient)
            else:
                from snap7.clib.client import ClibClient
                return object.__new__(ClibClient)
        else:
            # For subclasses, use normal object creation
            return object.__new__(cls)

    def __init__(self, lib_location: Optional[str] = None, pure_python: bool = False):
        """
        Initialize method for the Client base class.

        This is called by Python after __new__ returns. Since __new__ might return
        a different class (ClibClient or S7Client), those subclasses handle their own
        initialization. This method only needs to exist to satisfy Python's calling convention.

        Args:
            lib_location: Path to Snap7 C library (passed to ClibClient if applicable).
            pure_python: Factory parameter (handled in __new__).
        """
        # Subclasses handle their own initialization via their own __init__ methods
        # which accept **kwargs to ignore factory parameters like 'pure_python'
        pass

    # Connection management methods
    def connect(self, address: str, rack: int, slot: int, tcp_port: int = 102):
        """Connect to a PLC."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def disconnect(self) -> int:
        """Disconnect from the PLC."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def get_connected(self) -> bool:
        """Check if connected to the PLC."""
        raise NotImplementedError("This method must be implemented by subclasses")

    #  DB operations
    def db_read(self, db_number: int, start: int, size: int) -> bytearray:
        """Read data from a DB."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def db_write(self, db_number: int, start: int, data: bytearray) -> int:
        """Write data to a DB."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def db_get(self, db_number: int) -> bytearray:
        """Get entire DB."""
        raise NotImplementedError("This method must be implemented by subclasses")

    #  area operations
    def read_area(self, area: Area, db_number: int, start: int, size: int) -> bytearray:
        """Read from a memory area."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def write_area(self, area: Area, db_number: int, start: int, data: bytearray) -> int:
        """Write to a memory area."""
        raise NotImplementedError("This method must be implemented by subclasses")

    #  memory operations
    def ab_read(self, start: int, size: int) -> bytearray:
        """Read from process inputs."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def ab_write(self, start: int, data: bytearray) -> int:
        """Write to process inputs."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def eb_read(self, start: int, size: int) -> bytearray:
        """Read from process inputs."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def eb_write(self, start: int, size: int, data: bytearray) -> int:
        """Write to process inputs."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def mb_read(self, start: int, size: int) -> bytearray:
        """Read from memory bits."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def mb_write(self, start: int, size: int, data: bytearray) -> int:
        """Write to memory bits."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def tm_read(self, start: int, amount: int) -> bytearray:
        """Read timers."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def tm_write(self, start: int, amount: int, data: bytearray) -> int:
        """Write timers."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def ct_read(self, start: int, amount: int) -> bytearray:
        """Read counters."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def ct_write(self, start: int, amount: int, data: bytearray) -> int:
        """Write counters."""
        raise NotImplementedError("This method must be implemented by subclasses")

    #  block operations
    def list_blocks(self) -> BlocksList:
        """List all blocks."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def get_block_info(self, block_type: Block, db_number: int) -> TS7BlockInfo:
        """Get block information."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def upload(self, block_num: int) -> bytearray:
        """Upload a block from PLC."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def download(self, data: bytearray, block_num: int = -1) -> int:
        """Download a block to PLC."""
        raise NotImplementedError("This method must be implemented by subclasses")

    #  PLC control
    def plc_stop(self) -> int:
        """Stop the PLC."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def plc_hot_start(self) -> int:
        """Hot start the PLC."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def plc_cold_start(self) -> int:
        """Cold start the PLC."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def get_cpu_state(self) -> str:
        """Get CPU state."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def get_cpu_info(self) -> S7CpuInfo:
        """Get CPU information."""
        raise NotImplementedError("This method must be implemented by subclasses")

    #  configuration
    def set_connection_params(self, address: str, local_tsap: int, remote_tsap: int) -> None:
        """Set connection parameters."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def set_connection_type(self, connection_type: int) -> None:
        """Set connection type."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def get_pdu_length(self) -> int:
        """Get PDU length."""
        raise NotImplementedError("This method must be implemented by subclasses")

    #  date/time
    def get_plc_datetime(self) -> datetime:
        """Get PLC date/time."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def set_plc_datetime(self, dt: datetime) -> int:
        """Set PLC date/time."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def set_plc_system_datetime(self) -> int:
        """Set PLC to system date/time."""
        raise NotImplementedError("This method must be implemented by subclasses")

    #  security
    def set_session_password(self, password: str) -> int:
        """Set session password."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def clear_session_password(self) -> int:
        """Clear session password."""
        raise NotImplementedError("This method must be implemented by subclasses")

    #  error handling
    def error_text(self, error: int) -> str:
        """Get error text."""
        raise NotImplementedError("This method must be implemented by subclasses")
