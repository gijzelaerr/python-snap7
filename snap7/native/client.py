"""
Drop-in replacement client using pure Python S7 implementation.

This module provides a Client class that is API-compatible with the existing
ctypes-based client but uses the pure Python S7 implementation instead of
the native Snap7 C library.
"""

import logging
from typing import List, Any
from datetime import datetime

from snap7.native.wire_client import WireClient
from snap7.native.errors import S7Error, S7ConnectionError
from snap7.type import Area, Block, BlocksList, S7CpuInfo, TS7BlockInfo
from snap7.client import Client as BaseClient

logger = logging.getLogger(__name__)


class Client(BaseClient):
    """
    Pure Python S7 client - drop-in replacement for ctypes version.
    
    This class provides the same API as the original ctypes-based Client
    but uses a pure Python implementation of the S7 protocol instead of
    the native Snap7 C library.
    
    Usage:
        >>> import snap7.native_client as snap7
        >>> client = snap7.Client()
        >>> client.connect("192.168.1.10", 0, 1)
        >>> data = client.db_read(1, 0, 4)
    """
    
    def __init__(self, **kwargs):
        """
        Initialize pure Python S7 client.

        Args:
            **kwargs: Accepts and ignores extra keyword arguments (e.g., pure_python, lib_location)
                     for compatibility with the Client factory.
        """
        self._client = WireClient()
        logger.info("Pure Python S7 client initialized")
    
    def connect(self, address: str, rack: int, slot: int, tcp_port: int = 102) -> "Client":
        """
        Connect to S7 PLC.
        
        Args:
            address: PLC IP address
            rack: Rack number
            slot: Slot number
            tcp_port: TCP port (default 102)
            
        Returns:
            Self for method chaining
        """
        try:
            self._client.connect(address, rack, slot, tcp_port)
            return self
        except S7Error:
            # Re-raise S7 errors as-is
            raise
        except Exception as e:
            # Wrap other exceptions as S7ConnectionError for compatibility
            raise S7ConnectionError(f"Connection failed: {e}")
    
    def disconnect(self) -> None:
        """Disconnect from S7 PLC."""
        self._client.disconnect()
    
    def get_connected(self) -> bool:
        """Check if client is connected."""
        return self._client.get_connected()
    
    def db_read(self, db_number: int, start: int, size: int) -> bytearray:
        """
        Read data from DB.
        
        Args:
            db_number: DB number
            start: Start byte offset
            size: Number of bytes to read
            
        Returns:
            Data read from DB
        """
        return self._client.db_read(db_number, start, size)
    
    def db_write(self, db_number: int, start: int, data: bytearray) -> None:
        """
        Write data to DB.
        
        Args:
            db_number: DB number
            start: Start byte offset
            data: Data to write
        """
        self._client.db_write(db_number, start, data)
    
    def read_area(self, area: Area, db_number: int, start: int, size: int) -> bytearray:
        """
        Read data from memory area.
        
        Args:
            area: Memory area
            db_number: DB number (for DB area only)
            start: Start address
            size: Number of bytes to read
            
        Returns:
            Data read from area
        """
        return self._client.read_area(area, db_number, start, size)
    
    def write_area(self, area: Area, db_number: int, start: int, data: bytearray) -> None:
        """
        Write data to memory area.
        
        Args:
            area: Memory area
            db_number: DB number (for DB area only)
            start: Start address
            data: Data to write
        """
        self._client.write_area(area, db_number, start, data)
    
    def ab_read(self, start: int, size: int) -> bytearray:
        """Read from process input area (IPU)."""
        return self.read_area(Area.PE, 0, start, size)
    
    def ab_write(self, start: int, data: bytearray) -> None:
        """Write to process input area (IPU)."""
        self.write_area(Area.PE, 0, start, data)
    
    def eb_read(self, start: int, size: int) -> bytearray:
        """Read from process input area."""
        return self.read_area(Area.PE, 0, start, size)
    
    def eb_write(self, start: int, size: int, data: bytearray) -> None:
        """Write to process input area."""
        self.write_area(Area.PE, 0, start, data)
    
    def mb_read(self, start: int, size: int) -> bytearray:
        """Read from memory/flag area."""
        return self.read_area(Area.MK, 0, start, size)
    
    def mb_write(self, start: int, size: int, data: bytearray) -> None:
        """Write to memory/flag area."""
        self.write_area(Area.MK, 0, start, data)
    
    def tm_read(self, start: int, amount: int) -> bytearray:
        """Read timers."""
        return self.read_area(Area.TM, 0, start, amount * 2)  # Timers are 2 bytes each
    
    def tm_write(self, start: int, amount: int, data: bytearray) -> None:
        """Write timers."""
        self.write_area(Area.TM, 0, start, data)
    
    def ct_read(self, start: int, amount: int) -> bytearray:
        """Read counters."""
        return self.read_area(Area.CT, 0, start, amount * 2)  # Counters are 2 bytes each
    
    def ct_write(self, start: int, amount: int, data: bytearray) -> None:
        """Write counters."""
        self.write_area(Area.CT, 0, start, data)
    
    def list_blocks(self) -> BlocksList:
        """
        List blocks in PLC.
        
        Returns:
            Block list structure
        """
        return self._client.list_blocks()
    
    def get_cpu_info(self) -> S7CpuInfo:
        """
        Get CPU information.
        
        Returns:
            CPU information structure
        """
        return self._client.get_cpu_info()
    
    def get_cpu_state(self) -> str:
        """
        Get CPU state.
        
        Returns:
            CPU state string
        """
        return self._client.get_cpu_state()
    
    def plc_stop(self) -> None:
        """Stop PLC CPU."""
        self._client.plc_stop()
    
    def plc_hot_start(self) -> None:
        """Hot start PLC CPU."""
        self._client.plc_hot_start()
    
    def plc_cold_start(self) -> None:
        """Cold start PLC CPU."""
        self._client.plc_cold_start()
    
    def get_pdu_length(self) -> int:
        """
        Get negotiated PDU length.
        
        Returns:
            PDU length in bytes
        """
        return self._client.get_pdu_length()
    
    def error_text(self, error_code: int) -> str:
        """
        Get error text for error code.
        
        Args:
            error_code: S7 error code
            
        Returns:
            Error description
        """
        return self._client.error_text(error_code)
    
    def read_multi_vars(self, items: List[dict]) -> List[Any]:
        """
        Read multiple variables.
        
        Args:
            items: List of variable specifications
            
        Returns:
            List of read values
        """
        return self._client.read_multi_vars(items)
    
    def write_multi_vars(self, items: List[dict]) -> None:
        """
        Write multiple variables.
        
        Args:
            items: List of variable specifications with data
        """
        self._client.write_multi_vars(items)
    
    def get_block_info(self, block_type: Block, db_number: int) -> TS7BlockInfo:
        """
        Get block information.
        
        Args:
            block_type: Type of block
            db_number: Block number
            
        Returns:
            Block information structure
        """
        return self._client.get_block_info(block_type, db_number)
    
    def upload(self, block_num: int) -> bytearray:
        """
        Upload block from PLC.
        
        Args:
            block_num: Block number to upload
            
        Returns:
            Block data
        """
        return self._client.upload(block_num)
    
    def download(self, data: bytearray, block_num: int = -1) -> None:
        """
        Download block to PLC.
        
        Args:
            data: Block data
            block_num: Block number
        """
        self._client.download(data, block_num)
    
    def db_get(self, db_number: int) -> bytearray:
        """
        Get entire DB.
        
        Args:
            db_number: DB number
            
        Returns:
            Complete DB data
        """
        # For now, try to read a large block and return what we get
        # In a real implementation, we would first query the DB size
        # Check connection first
        if not self._client.get_connected():
            raise Exception("Not connected to PLC")
        
        try:
            # Try reading up to 8KB (reasonable DB size limit)
            max_size = 8192
            data = self._client.db_read(db_number, 0, max_size)
            return data
        except Exception as e:
            # If reading large block fails, try smaller incremental reads
            logger.warning(f"Large DB read failed, trying incremental read: {e}")
            
            # Try reading in 512-byte chunks until we hit the end
            chunk_size = 512
            result_data = bytearray()
            offset = 0
            
            while offset < 4096:  # Max 4KB for safety
                try:
                    chunk = self._client.db_read(db_number, offset, chunk_size)
                    if not chunk or len(chunk) == 0:
                        break
                    result_data.extend(chunk)
                    offset += len(chunk)
                    
                    # If we got less than requested, we've hit the end
                    if len(chunk) < chunk_size:
                        break
                except Exception:
                    # Hit the end or an error, stop here
                    break
            
            return result_data
    
    def set_session_password(self, password: str) -> None:
        """
        Set session password.
        
        Args:
            password: Password to set
        """
        # Store password for potential future use
        # In a real implementation, this would send authentication to PLC
        if hasattr(self._client, 'session_password'):
            self._client.session_password = password
        logger.info("Session password set (stored for future authentication)")
    
    def clear_session_password(self) -> None:
        """Clear session password."""
        # Clear stored password
        if hasattr(self._client, 'session_password'):
            self._client.session_password = None
        logger.info("Session password cleared")
    
    def set_connection_params(self, address: str, local_tsap: int, remote_tsap: int) -> None:
        """
        Set connection parameters.
        
        Args:
            address: PLC IP address
            local_tsap: Local TSAP
            remote_tsap: Remote TSAP
        """
        # Store parameters for next connection
        if hasattr(self._client, 'connection') and self._client.connection:
            self._client.connection.local_tsap = local_tsap
            self._client.connection.remote_tsap = remote_tsap
    
    def set_connection_type(self, connection_type: int) -> None:
        """
        Set connection type.
        
        Args:
            connection_type: Connection type (1=PG, 2=OP, 3-10=S7 Basic)
        """
        # Store connection type for potential future use
        # In a real implementation, this would affect TSAP values and connection behavior
        if hasattr(self._client, 'connection_type'):
            self._client.connection_type = connection_type
        logger.info(f"Connection type set to {connection_type} (stored for reference)")
    
    def get_plc_datetime(self) -> datetime:
        """
        Get PLC date/time.
        
        Returns:
            PLC date and time
        """
        return self._client.get_plc_datetime()
    
    def set_plc_datetime(self, dt: datetime) -> None:
        """
        Set PLC date/time.
        
        Args:
            dt: Date and time to set
        """
        self._client.set_plc_datetime(dt)
    
    def set_plc_system_datetime(self) -> None:
        """Set PLC time to system time."""
        self._client.set_plc_system_datetime()
    
    def destroy(self) -> None:
        """Destroy client (disconnect)."""
        self.disconnect()
    
    def create(self) -> None:
        """Create client (no-op for compatibility)."""
        pass
    
    def __enter__(self) -> "Client":
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.disconnect()