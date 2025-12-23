"""
Snap7 server base class and factory.
"""

from typing import Optional, Tuple, Any, Callable, Type
from types import TracebackType
from snap7.type import SrvEvent, Parameter, SrvArea, CDataArrayType



class Server:
    """
    Base class and factory for Snap7 server implementations.

    This class serves as both:
    1. An abstract base class defining the interface all servers must implement
    2. A factory that returns the appropriate concrete implementation

    When instantiated, returns either:
    - A ClibServer (ctypes-based, using Snap7 C library) when pure_python=False (default)
    - A PureServer (pure Python implementation) when pure_python=True

    Args:
        log: Enable event logging. Defaults to True.
        pure_python: If True, returns pure Python server. If False (default), returns ctypes server.

    Examples:
        >>> import snap7
        >>> # Get ctypes-based server (requires Snap7 C library)
        >>> server = snap7.Server()
        >>> server = snap7.Server(log=True)
        >>>
        >>> # Get pure Python server (no C library needed)
        >>> server = snap7.Server(pure_python=True)
    """

    def __new__(cls, log: bool = True, pure_python: bool = False):
        """
        Factory method to create the appropriate server instance.

        Args:
            log: Enable event logging to Python logging.
            pure_python: If True, return pure Python implementation; otherwise ctypes implementation.

        Returns:
            ClibServer or PureServer instance.
        """
        # Only use factory pattern when called on the base Server class
        if cls is Server:
            if pure_python:
                from snap7.native.server import Server as PureServer
                return object.__new__(PureServer)
            else:
                from snap7.clib.server import ClibServer
                return object.__new__(ClibServer)
        else:
            # For subclasses, use normal object creation
            return object.__new__(cls)

    def __init__(self, log: bool = True, pure_python: bool = False):
        """
        Initialize method for the Server base class.

        This is called by Python after __new__ returns. Since __new__ might return
        a different class (ClibServer or PureServer), those subclasses handle their own
        initialization. This method only needs to exist to satisfy Python's calling convention.

        Args:
            log: Enable event logging (passed to ClibServer or PureServer if applicable).
            pure_python: Factory parameter (handled in __new__).
        """
        # Subclasses handle their own initialization via their own __init__ methods
        # which accept **kwargs to ignore factory parameters like 'pure_python'
        pass

    def __enter__(self) -> "Server":
        """Context manager entry."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        """Context manager exit."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def event_text(self, event: SrvEvent) -> str:
        """Returns a textual explanation of a given event object."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def create(self) -> None:
        """Create the server."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def register_area(self, area: SrvArea, index: int, userdata: CDataArrayType) -> int:
        """Shares a memory area with the server."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def set_events_callback(self, call_back: Callable[..., Any]) -> int:
        """Sets the user callback that the Server object has to call when an event is created."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def set_read_events_callback(self, call_back: Callable[..., Any]) -> int:
        """Sets the user callback that the Server object has to call when a Read event is created."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def start(self, tcp_port: int = 102) -> int:
        """Starts the server."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def stop(self) -> int:
        """Stop the server."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def destroy(self) -> None:
        """Destroy the server."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def get_status(self) -> Tuple[str, str, int]:
        """Reads the server status, the Virtual CPU status and the number of the clients connected."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def unregister_area(self, area: SrvArea, index: int) -> int:
        """Unregisters a memory area previously registered with Srv_RegisterArea()."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def unlock_area(self, area: SrvArea, index: int) -> int:
        """Unlocks a previously locked shared memory area."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def lock_area(self, area: SrvArea, index: int) -> int:
        """Locks a shared memory area."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def start_to(self, ip: str, tcp_port: int = 102) -> int:
        """Start server on a specific interface."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def set_param(self, parameter: Parameter, value: int) -> int:
        """Sets an internal Server object parameter."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def set_mask(self, kind: int, mask: int) -> int:
        """Writes the specified filter mask."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def set_cpu_status(self, status: int) -> int:
        """Sets the Virtual CPU status."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def pick_event(self) -> Optional[SrvEvent]:
        """Extracts an event (if available) from the Events queue."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def get_param(self, number: int) -> int:
        """Reads an internal Server object parameter."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def get_mask(self, kind: int) -> int:
        """Reads the specified filter mask."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def clear_events(self) -> int:
        """Empties the Event queue."""
        raise NotImplementedError("This method must be implemented by subclasses")


def mainloop(tcp_port: int = 1102, init_standard_values: bool = False) -> None:
    """
    Init a fake Snap7 server with some default values.

    This is a convenience function that uses the ctypes-based server.
    For the pure Python version, use snap7.native.server.mainloop.

    Args:
        tcp_port: port that the server will listen.
        init_standard_values: if `True` will init some defaults values to be read on DB0.
    """
    # Import here to avoid circular imports
    from snap7.clib.server import mainloop as clib_mainloop
    clib_mainloop(tcp_port=tcp_port, init_standard_values=init_standard_values)
