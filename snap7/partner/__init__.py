"""
Snap7 partner base class and factory.

This module provides peer-to-peer S7 communication. Unlike the client-server model,
where the client makes a request and the server replies, the peer-to-peer model
has two components with equal rights, each of which can send data asynchronously.
The only difference between them is who initiates the connection.
"""

from typing import Optional, Tuple
from ctypes import c_int32, c_uint32

from snap7.type import Parameter


class Partner:
    """
    Base class and factory for Snap7 partner implementations.

    This class serves as both:
    1. An abstract base class defining the interface all partners must implement
    2. A factory that returns the appropriate concrete implementation

    When instantiated, returns either:
    - A ClibPartner (ctypes-based, using Snap7 C library) when pure_python=False (default)
    - A PurePartner (pure Python implementation) when pure_python=True

    Args:
        active: If True, this partner initiates the connection. If False, waits for connection.
        pure_python: If True, returns pure Python partner. If False (default), returns ctypes partner.

    Examples:
        >>> import snap7
        >>> # Get ctypes-based partner (requires Snap7 C library)
        >>> partner = snap7.Partner(active=True)
        >>>
        >>> # Get pure Python partner (no C library needed)
        >>> partner = snap7.Partner(active=True, pure_python=True)
    """

    def __new__(cls, active: bool = False, pure_python: bool = False):
        """
        Factory method to create the appropriate partner instance.

        Args:
            active: If True, this partner initiates the connection.
            pure_python: If True, return pure Python implementation; otherwise ctypes implementation.

        Returns:
            ClibPartner or PurePartner instance.
        """
        # Only use factory pattern when called on the base Partner class
        if cls is Partner:
            if pure_python:
                from snap7.native.partner import Partner as PurePartner
                return object.__new__(PurePartner)
            else:
                from snap7.clib.partner import ClibPartner
                return object.__new__(ClibPartner)
        else:
            # For subclasses, use normal object creation
            return object.__new__(cls)

    def __init__(self, active: bool = False, pure_python: bool = False):
        """
        Initialize method for the Partner base class.

        This is called by Python after __new__ returns. Since __new__ might return
        a different class (ClibPartner or PurePartner), those subclasses handle their own
        initialization. This method only needs to exist to satisfy Python's calling convention.

        Args:
            active: If True, this partner initiates the connection.
            pure_python: Factory parameter (handled in __new__).
        """
        # Subclasses handle their own initialization via their own __init__ methods
        # which accept **kwargs to ignore factory parameters like 'pure_python'
        pass

    def __del__(self) -> None:
        """Destructor."""
        self.destroy()

    # Connection management
    def create(self, active: bool = False) -> None:
        """Create the partner."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def destroy(self) -> Optional[int]:
        """Destroy the partner."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def start(self) -> int:
        """Start the partner."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def start_to(self, local_ip: str, remote_ip: str, local_tsap: int, remote_tsap: int) -> int:
        """Start the partner with specific connection parameters."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def stop(self) -> int:
        """Stop the partner."""
        raise NotImplementedError("This method must be implemented by subclasses")

    # Data transfer - synchronous
    def b_send(self) -> int:
        """Send data synchronously."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def b_recv(self) -> int:
        """Receive data synchronously."""
        raise NotImplementedError("This method must be implemented by subclasses")

    # Data transfer - asynchronous
    def as_b_send(self) -> int:
        """Send data asynchronously."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def check_as_b_send_completion(self) -> Tuple[str, c_int32]:
        """Check if async send completed."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def wait_as_b_send_completion(self, timeout: int = 0) -> int:
        """Wait for async send to complete."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def check_as_b_recv_completion(self) -> int:
        """Check if async receive completed."""
        raise NotImplementedError("This method must be implemented by subclasses")

    # Callbacks
    def set_recv_callback(self) -> int:
        """Set the receive callback."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def set_send_callback(self) -> int:
        """Set the send callback."""
        raise NotImplementedError("This method must be implemented by subclasses")

    # Status and statistics
    def get_status(self) -> c_int32:
        """Get partner status."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def get_stats(self) -> Tuple[c_uint32, c_uint32, c_uint32, c_uint32]:
        """Get partner statistics."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def get_times(self) -> Tuple[c_int32, c_int32]:
        """Get last send/recv times."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def get_last_error(self) -> c_int32:
        """Get last error."""
        raise NotImplementedError("This method must be implemented by subclasses")

    # Parameters
    def get_param(self, parameter: Parameter) -> int:
        """Get internal parameter."""
        raise NotImplementedError("This method must be implemented by subclasses")

    def set_param(self, parameter: Parameter, value: int) -> int:
        """Set internal parameter."""
        raise NotImplementedError("This method must be implemented by subclasses")