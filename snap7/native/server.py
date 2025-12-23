"""
Drop-in replacement server using pure Python S7 implementation.

This module provides a Server class that is API-compatible with the existing
ctypes-based server but uses the pure Python S7 implementation instead of
the native Snap7 C library.
"""

import logging
import struct
import time
from typing import Any, Callable, Tuple
from ctypes import Array, c_char

from snap7.native.wire_server import WireServer
from snap7.native.errors import S7Error, S7ConnectionError
from snap7.type import SrvArea, SrvEvent, Parameter
from snap7.server import Server as BaseServer

logger = logging.getLogger(__name__)


class Server(BaseServer):
    """
    Pure Python S7 server - drop-in replacement for ctypes version.
    
    This class provides the same API as the original ctypes-based Server
    but uses a pure Python implementation of the S7 protocol instead of
    the native Snap7 C library.
    
    Usage:
        >>> import snap7.native_server as snap7
        >>> server = snap7.Server()
        >>> server.start()
        >>> # ... register areas and handle clients
        >>> server.stop()
    """
    
    def __init__(self, log: bool = True, **kwargs):
        """
        Initialize pure Python S7 server.

        Args:
            log: Enable event logging (for compatibility)
            **kwargs: Accepts and ignores extra keyword arguments (e.g., pure_python)
                     for compatibility with the Server factory.
        """
        self._server = WireServer()
        self._log_enabled = log
        logger.info("Pure Python S7 server initialized")

        if log:
            self._set_log_callback()
    
    def create(self) -> None:
        """Create the server (no-op for compatibility)."""
        pass
    
    def destroy(self) -> None:
        """Destroy the server."""
        self._server.stop()
    
    def start(self, tcp_port: int = 102) -> int:
        """
        Start the server.
        
        Args:
            tcp_port: TCP port to listen on
            
        Returns:
            0 for success (for compatibility)
        """
        try:
            self._server.start(tcp_port)
            return 0
        except S7Error:
            # Re-raise S7 errors as-is
            raise
        except Exception as e:
            # Wrap other exceptions as S7ConnectionError for compatibility
            raise S7ConnectionError(f"Server start failed: {e}")
    
    def stop(self) -> int:
        """
        Stop the server.
        
        Returns:
            0 for success (for compatibility)
        """
        try:
            self._server.stop()
            return 0
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            return 1
    
    def register_area(self, area: SrvArea, index: int, userdata: Array[c_char]) -> int:
        """
        Register a memory area with the server.
        
        Args:
            area: Memory area type
            index: Area index
            userdata: Data buffer (ctypes array)
            
        Returns:
            0 for success (for compatibility)
        """
        try:
            # Convert ctypes array to bytearray
            data = bytearray(userdata)
            self._server.register_area(area, index, data)
            return 0
        except Exception as e:
            logger.error(f"Error registering area: {e}")
            return 1
    
    def unregister_area(self, area: SrvArea, index: int) -> int:
        """
        Unregister a memory area.
        
        Args:
            area: Memory area type
            index: Area index
            
        Returns:
            0 for success (for compatibility)
        """
        try:
            self._server.unregister_area(area, index)
            return 0
        except Exception as e:
            logger.error(f"Error unregistering area: {e}")
            return 1
    
    def lock_area(self, area: SrvArea, index: int) -> int:
        """
        Lock a memory area (placeholder for compatibility).
        
        Args:
            area: Memory area type
            index: Area index
            
        Returns:
            0 for success (for compatibility)
        """
        logger.debug(f"Lock area {area} index {index} (not implemented)")
        return 0
    
    def unlock_area(self, area: SrvArea, index: int) -> int:
        """
        Unlock a memory area (placeholder for compatibility).
        
        Args:
            area: Memory area type
            index: Area index
            
        Returns:
            0 for success (for compatibility)
        """
        logger.debug(f"Unlock area {area} index {index} (not implemented)")
        return 0
    
    def get_status(self) -> Tuple[str, str, int]:
        """
        Get server status.
        
        Returns:
            Tuple of (server_status, cpu_status, client_count)
        """
        return self._server.get_status()
    
    def set_events_callback(self, callback: Callable[[SrvEvent], Any]) -> int:
        """
        Set event callback.
        
        Args:
            callback: Event callback function
            
        Returns:
            0 for success (for compatibility)
        """
        try:
            self._server.set_events_callback(callback)
            return 0
        except Exception as e:
            logger.error(f"Error setting event callback: {e}")
            return 1
    
    def set_read_events_callback(self, callback: Callable[[SrvEvent], Any]) -> int:
        """
        Set read event callback.
        
        Args:
            callback: Read event callback function
            
        Returns:
            0 for success (for compatibility)
        """
        try:
            self._server.set_read_events_callback(callback)
            return 0
        except Exception as e:
            logger.error(f"Error setting read event callback: {e}")
            return 1
    
    def event_text(self, event: SrvEvent) -> str:
        """
        Get event text description.
        
        Args:
            event: Server event
            
        Returns:
            Event description string
        """
        # Simple event text generation for common events
        event_texts = {
            0x00004000: "Read operation completed",
            0x00004001: "Write operation completed", 
            0x00008000: "Client connected",
            0x00008001: "Client disconnected",
        }
        
        return event_texts.get(event.EvtCode, f"Event code: {event.EvtCode:#08x}")
    
    def get_mask(self, mask_kind: int) -> int:
        """
        Get event mask (placeholder for compatibility).
        
        Args:
            mask_kind: Mask type
            
        Returns:
            Event mask value
        """
        # Return default mask values for compatibility
        if mask_kind == 0:  # mkEvent
            return 0xFFFFFFFF
        elif mask_kind == 1:  # mkLog
            return 0xFFFFFFFF
        else:
            raise ValueError(f"Invalid mask kind: {mask_kind}")
    
    def set_mask(self, mask_kind: int, mask: int) -> int:
        """
        Set event mask (placeholder for compatibility).
        
        Args:
            mask_kind: Mask type
            mask: Mask value
            
        Returns:
            0 for success (for compatibility)
        """
        logger.debug(f"Set mask {mask_kind} = {mask:#08x} (not implemented)")
        return 0
    
    def set_param(self, param: Parameter, value: int) -> int:
        """
        Set server parameter (placeholder for compatibility).
        
        Args:
            param: Parameter type
            value: Parameter value
            
        Returns:
            0 for success (for compatibility)
        """
        logger.debug(f"Set parameter {param} = {value} (not implemented)")
        return 0
    
    def get_param(self, param: Parameter) -> int:
        """
        Get server parameter (placeholder for compatibility).

        Args:
            param: Parameter type

        Returns:
            Parameter value
        """
        # Return reasonable defaults for common parameters
        if param == Parameter.LocalPort:
            return self._server.port
        else:
            logger.debug(f"Get parameter {param} (not implemented)")
            return 0

    def start_to(self, ip: str, tcp_port: int = 102) -> int:
        """
        Start server on a specific interface (placeholder for compatibility).

        Args:
            ip: IP address to bind to
            tcp_port: TCP port to listen on

        Returns:
            0 for success (for compatibility)
        """
        logger.debug(f"start_to {ip}:{tcp_port} (not implemented, using default start)")
        return self.start(tcp_port)

    def set_cpu_status(self, status: int) -> int:
        """
        Set CPU status (placeholder for compatibility).

        Args:
            status: CPU status code

        Returns:
            0 for success (for compatibility)
        """
        logger.debug(f"set_cpu_status {status} (not implemented)")
        return 0

    def pick_event(self) -> SrvEvent:
        """
        Pick an event from the queue (placeholder for compatibility).

        Returns:
            Server event or None if no events available
        """
        logger.debug("pick_event (not implemented)")
        return None

    def clear_events(self) -> int:
        """
        Clear event queue (placeholder for compatibility).

        Returns:
            0 for success (for compatibility)
        """
        logger.debug("clear_events (not implemented)")
        return 0

    def _set_log_callback(self) -> None:
        """Set up default logging callback."""
        def log_callback(event: SrvEvent) -> None:
            event_text = self.event_text(event)
            logger.info(f"Server event: {event_text}")
        
        self.set_events_callback(log_callback)
    
    def __enter__(self) -> "Server":
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.destroy()


def mainloop(tcp_port: int = 1102, init_standard_values: bool = False) -> None:
    """
    Initialize a pure Python S7 server with default values.
    
    Args:
        tcp_port: Port that the server will listen on
        init_standard_values: If True, initialize some default values
    """
    server = Server()
    
    # Create standard memory areas
    size = 100
    db_data = bytearray(size)
    pa_data = bytearray(size)
    tm_data = bytearray(size)
    ct_data = bytearray(size)
    
    # Register memory areas
    from ctypes import c_char
    db_array = (c_char * size).from_buffer(db_data)
    pa_array = (c_char * size).from_buffer(pa_data)
    tm_array = (c_char * size).from_buffer(tm_data)
    ct_array = (c_char * size).from_buffer(ct_data)
    
    server.register_area(SrvArea.DB, 1, db_array)
    server.register_area(SrvArea.PA, 1, pa_array)
    server.register_area(SrvArea.TM, 1, tm_array)
    server.register_area(SrvArea.CT, 1, ct_array)
    
    if init_standard_values:
        logger.info("Initializing with standard values")
        # Set some test values
        db_data[0] = 0x42  # Test byte
        db_data[1] = 0xFF
        db_data[2:4] = struct.pack('>H', 1234)  # Test word
        db_data[4:8] = struct.pack('>I', 567890)  # Test dword
    
    # Start server
    server.start(tcp_port)
    
    try:
        logger.info(f"Pure Python S7 server running on port {tcp_port}")
        logger.info("Press Ctrl+C to stop")
        
        # Keep server running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Stopping server...")
    finally:
        server.stop()
        server.destroy()

