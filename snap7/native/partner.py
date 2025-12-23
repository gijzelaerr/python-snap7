"""
Drop-in replacement partner using pure Python S7 implementation.

This module provides a Partner class that is API-compatible with the existing
ctypes-based partner but uses the pure Python S7 implementation instead of
the native Snap7 C library.
"""

import logging
from typing import Optional, Tuple, Type
from ctypes import c_int32, c_uint32
from types import TracebackType

from snap7.native.wire_partner import WirePartner
from snap7.native.errors import S7Error, S7ConnectionError
from snap7.type import Parameter
from snap7.partner import Partner as BasePartner

logger = logging.getLogger(__name__)


class Partner(BasePartner):
    """
    Pure Python S7 partner - drop-in replacement for ctypes version.

    This class provides the same API as the original ctypes-based Partner
    but uses a pure Python implementation of the S7 protocol instead of
    the native Snap7 C library.

    Usage:
        >>> from snap7.native.partner import Partner
        >>> partner = Partner(active=True)
        >>> partner.start_to("0.0.0.0", "192.168.1.10", 0x0100, 0x0102)
        >>> partner.b_send(data)
        >>> partner.stop()
    """

    def __init__(self, active: bool = False, **kwargs):
        """
        Initialize pure Python S7 partner.

        Args:
            active: If True, this partner initiates the connection.
            **kwargs: Accepts and ignores extra keyword arguments (e.g., pure_python)
                     for compatibility with the Partner factory.
        """
        self._partner = WirePartner(active=active)
        logger.info("Pure Python S7 partner initialized")

    def __enter__(self) -> "Partner":
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        self.destroy()

    def __del__(self) -> None:
        try:
            self.destroy()
        except Exception:
            pass

    def as_b_send(self) -> int:
        """
        Sends a data packet to the partner asynchronously.

        Note: This is a simplified version. For full async support,
        use the WirePartner directly.

        Returns:
            0 on success
        """
        if self._send_data is None:
            return -1
        return self._partner.as_b_send(self._send_data)

    def b_recv(self) -> int:
        """
        Receives a data packet from the partner synchronously.

        Returns:
            0 on success
        """
        result, data = self._partner.b_recv()
        self._recv_data = data
        return result

    def b_send(self) -> int:
        """
        Sends a data packet to the partner synchronously.

        Note: Call set_send_data() first to set the data to send.

        Returns:
            0 on success
        """
        if self._send_data is None:
            return -1
        return self._partner.b_send(self._send_data)

    def check_as_b_recv_completion(self) -> int:
        """
        Checks if a packet was received.

        Returns:
            0 if data available, 1 if in progress
        """
        return self._partner.check_as_b_recv_completion()

    def check_as_b_send_completion(self) -> Tuple[str, c_int32]:
        """
        Checks if the current asynchronous send job was completed.

        Returns:
            Tuple of (status_string, operation_result)
        """
        status, result = self._partner.check_as_b_send_completion()
        return_values = {
            0: "job complete",
            1: "job in progress",
            -2: "invalid handled supplied",
        }

        if status == -2:
            raise ValueError("The partner parameter was invalid")

        return return_values.get(status, "unknown"), c_int32(result)

    def create(self, active: bool = False) -> None:
        """
        Creates a Partner.

        Note: For pure Python implementation, the partner is created in __init__.
        This method exists for API compatibility.

        Args:
            active: If True, this partner initiates connections
        """
        # Partner already created in __init__
        pass

    def destroy(self) -> Optional[int]:
        """
        Destroy the Partner.

        Returns:
            0 on success
        """
        if self._partner:
            self._partner.stop()
            self._partner = None
        return 0

    def get_last_error(self) -> c_int32:
        """
        Returns the last job result.

        Returns:
            Last error code
        """
        return c_int32(self._partner.get_last_error())

    def get_param(self, parameter: Parameter) -> int:
        """
        Reads an internal Partner object parameter.

        Args:
            parameter: Parameter to read

        Returns:
            Parameter value

        Note: Not all parameters are supported in pure Python implementation.
        """
        logger.debug(f"Getting parameter {parameter} (not fully implemented)")
        return 0

    def get_stats(self) -> Tuple[c_uint32, c_uint32, c_uint32, c_uint32]:
        """
        Returns partner statistics.

        Returns:
            Tuple of (bytes_sent, bytes_recv, send_errors, recv_errors)
        """
        sent, recv, send_errors, recv_errors = self._partner.get_stats()
        return c_uint32(sent), c_uint32(recv), c_uint32(send_errors), c_uint32(recv_errors)

    def get_status(self) -> c_int32:
        """
        Returns the Partner status.

        Returns:
            Status code (0=stopped, 1=running, 2=connected)
        """
        return c_int32(self._partner.get_status())

    def get_times(self) -> Tuple[c_int32, c_int32]:
        """
        Returns the last send and recv jobs execution time in milliseconds.

        Returns:
            Tuple of (send_time, recv_time)
        """
        send_time, recv_time = self._partner.get_times()
        return c_int32(send_time), c_int32(recv_time)

    def set_param(self, parameter: Parameter, value: int) -> int:
        """
        Sets an internal Partner object parameter.

        Args:
            parameter: Parameter to set
            value: Value to set

        Returns:
            0 on success

        Note: Not all parameters are supported in pure Python implementation.
        """
        logger.debug(f"Setting parameter {parameter} to {value} (not fully implemented)")
        return 0

    def set_recv_callback(self) -> int:
        """
        Sets the user callback for incoming data.

        Note: Use WirePartner.set_recv_callback() for actual callback support.

        Returns:
            0 on success
        """
        logger.debug("set_recv_callback called (use WirePartner for full callback support)")
        return 0

    def set_send_callback(self) -> int:
        """
        Sets the user callback for completed async sends.

        Note: Use WirePartner.set_send_callback() for actual callback support.

        Returns:
            0 on success
        """
        logger.debug("set_send_callback called (use WirePartner for full callback support)")
        return 0

    def start(self) -> int:
        """
        Starts the Partner with default parameters.

        Returns:
            0 on success
        """
        return self._partner.start()

    def start_to(self, local_ip: str, remote_ip: str, local_tsap: int, remote_tsap: int) -> int:
        """
        Starts the Partner with specific connection parameters.

        Args:
            local_ip: PC host IPV4 Address. "0.0.0.0" for default adapter
            remote_ip: Remote partner IPV4 Address
            local_tsap: Local TSAP
            remote_tsap: Remote TSAP

        Returns:
            0 on success
        """
        return self._partner.start_to(local_ip, remote_ip, local_tsap, remote_tsap)

    def stop(self) -> int:
        """
        Stops the Partner.

        Returns:
            0 on success
        """
        return self._partner.stop()

    def wait_as_b_send_completion(self, timeout: int = 0) -> int:
        """
        Waits until the current asynchronous send job is done.

        Args:
            timeout: Timeout in milliseconds (0 for infinite)

        Returns:
            0 on success
        """
        return self._partner.wait_as_b_send_completion(timeout)

    # Helper methods for data transfer
    _send_data: Optional[bytes] = None
    _recv_data: Optional[bytes] = None

    def set_send_data(self, data: bytes) -> None:
        """
        Set data to be sent by b_send() or as_b_send().

        Args:
            data: Data to send
        """
        self._send_data = data

    def get_recv_data(self) -> Optional[bytes]:
        """
        Get data received by b_recv().

        Returns:
            Received data or None
        """
        return self._recv_data

    # Direct access to underlying partner for advanced usage
    @property
    def wire_partner(self) -> WirePartner:
        """Get underlying WirePartner for advanced operations."""
        return self._partner
