"""
Pure Python S7 partner implementation.

S7 peer-to-peer communication for bidirectional data exchange.
Unlike client-server where client requests and server responds,
partners have equal rights and can send data asynchronously.
"""

import socket
import struct
import logging
import threading
from typing import Optional, Tuple, Callable, Type
from queue import Queue, Empty
from datetime import datetime
from types import TracebackType
from ctypes import c_int32, c_uint32

from .connection import ISOTCPConnection
from .error import S7Error, S7ConnectionError
from .type import Parameter

logger = logging.getLogger(__name__)


class PartnerStatus:
    """Partner status constants."""

    STOPPED = 0
    RUNNING = 1
    CONNECTED = 2


class Partner:
    """
    Pure Python S7 partner implementation.

    Implements peer-to-peer S7 communication where both partners can
    send and receive data asynchronously. Supports both active (initiates
    connection) and passive (waits for connection) modes.

    Examples:
        >>> import snap7
        >>> partner = snap7.Partner(active=True)
        >>> partner.start_to("0.0.0.0", "192.168.1.10", 0x0100, 0x0102)
        >>> partner.set_send_data(b"Hello")
        >>> partner.b_send()
        >>> partner.stop()
    """

    def __init__(self, active: bool = False, **kwargs):
        """
        Initialize S7 partner.

        Args:
            active: If True, this partner initiates the connection.
                   If False, this partner waits for incoming connections.
            **kwargs: Ignored. Kept for backwards compatibility.
        """
        self.active = active
        self.connected = False
        self.running = False

        # Connection parameters
        self.local_ip = "0.0.0.0"
        self.remote_ip = ""
        self.local_tsap = 0x0100
        self.remote_tsap = 0x0102
        self.port = 102
        self.local_port = 0  # Let OS choose
        self.remote_port = 102

        # Socket and connection
        self._socket: Optional[socket.socket] = None
        self._server_socket: Optional[socket.socket] = None  # For passive mode
        self._connection: Optional[ISOTCPConnection] = None

        # Statistics
        self.bytes_sent = 0
        self.bytes_recv = 0
        self.send_errors = 0
        self.recv_errors = 0

        # Timing
        self.last_send_time = 0
        self.last_recv_time = 0

        # Callbacks
        self._recv_callback: Optional[Callable[[bytes], None]] = None
        self._send_callback_fn: Optional[Callable[[int], None]] = None

        # Async operation support
        self._async_send_queue: Queue = Queue()
        self._async_recv_queue: Queue = Queue()
        self._async_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Last error
        self.last_error = 0

        # Buffer for send/recv operations
        self._send_data: Optional[bytes] = None
        self._recv_data: Optional[bytes] = None
        self._async_send_in_progress = False
        self._async_send_result = 0

        logger.info(f"S7 Partner initialized (active={active}, pure Python implementation)")

    def create(self, active: bool = False) -> None:
        """
        Creates a Partner.

        Note: For pure Python implementation, the partner is created in __init__.
        This method exists for API compatibility.

        Args:
            active: If True, this partner initiates connections
        """
        pass

    def destroy(self) -> int:
        """
        Destroy the Partner.

        Returns:
            0 on success
        """
        self.stop()
        return 0

    def start(self) -> int:
        """
        Start the partner with default parameters.

        Returns:
            0 on success
        """
        return self.start_to(self.local_ip, self.remote_ip, self.local_tsap, self.remote_tsap)

    def start_to(self, local_ip: str, remote_ip: str, local_tsap: int, remote_tsap: int) -> int:
        """
        Start the partner with specific connection parameters.

        Args:
            local_ip: Local IP address to bind to
            remote_ip: Remote partner IP address (for active mode)
            local_tsap: Local TSAP
            remote_tsap: Remote TSAP

        Returns:
            0 on success
        """
        self.local_ip = local_ip
        self.remote_ip = remote_ip
        self.local_tsap = local_tsap
        self.remote_tsap = remote_tsap

        try:
            if self.active:
                # Active mode: initiate connection to remote partner
                self._connect_to_remote()
            else:
                # Passive mode: start listening for incoming connections
                self._start_listening()

            self.running = True

            # Start async processing thread
            self._stop_event.clear()
            self._async_thread = threading.Thread(target=self._async_processor, daemon=True)
            self._async_thread.start()

            logger.info(f"Partner started ({'active' if self.active else 'passive'} mode)")
            return 0

        except Exception as e:
            self.last_error = -1
            logger.error(f"Partner start failed: {e}")
            raise S7ConnectionError(f"Partner start failed: {e}")

    def stop(self) -> int:
        """
        Stop the partner and disconnect.

        Returns:
            0 on success
        """
        self._stop_event.set()

        if self._async_thread and self._async_thread.is_alive():
            self._async_thread.join(timeout=2.0)

        if self._connection:
            self._connection.disconnect()
            self._connection = None

        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None

        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

        self.connected = False
        self.running = False

        logger.info("Partner stopped")
        return 0

    def b_send(self) -> int:
        """
        Send data synchronously (blocking).

        Note: Call set_send_data() first to set the data to send.

        Returns:
            0 on success
        """
        if self._send_data is None:
            return -1

        if not self.connected:
            self.send_errors += 1
            raise S7ConnectionError("Not connected")

        start_time = datetime.now()

        try:
            # Build partner data PDU
            pdu = self._build_partner_data_pdu(self._send_data)

            # Send via ISO connection
            self._connection.send_data(pdu)

            # Wait for acknowledgment
            ack_data = self._connection.receive_data()
            self._parse_partner_ack(ack_data)

            self.bytes_sent += len(self._send_data)
            self.last_send_time = int((datetime.now() - start_time).total_seconds() * 1000)

            logger.debug(f"Sent {len(self._send_data)} bytes synchronously")
            return 0

        except Exception as e:
            self.send_errors += 1
            self.last_error = -1
            logger.error(f"Synchronous send failed: {e}")
            raise S7ConnectionError(f"Send failed: {e}")

    def b_recv(self) -> int:
        """
        Receive data synchronously (blocking).

        Returns:
            0 on success
        """
        if not self.connected:
            self.recv_errors += 1
            self._recv_data = None
            return -1

        start_time = datetime.now()

        try:
            # Receive partner data
            data = self._connection.receive_data()
            received = self._parse_partner_data_pdu(data)

            # Send acknowledgment
            ack = self._build_partner_ack()
            self._connection.send_data(ack)

            self.bytes_recv += len(received)
            self.last_recv_time = int((datetime.now() - start_time).total_seconds() * 1000)
            self._recv_data = received

            # Call receive callback if set
            if self._recv_callback:
                self._recv_callback(received)

            logger.debug(f"Received {len(received)} bytes synchronously")
            return 0

        except socket.timeout:
            self._recv_data = None
            return 1  # Timeout
        except Exception as e:
            self.recv_errors += 1
            self.last_error = -1
            self._recv_data = None
            logger.error(f"Synchronous receive failed: {e}")
            return -1

    def as_b_send(self) -> int:
        """
        Send data asynchronously (non-blocking).

        Note: Call set_send_data() first to set the data to send.

        Returns:
            0 on success (send initiated)
        """
        if self._send_data is None:
            return -1

        if not self.connected:
            self.send_errors += 1
            return -1

        self._async_send_in_progress = True
        self._async_send_result = 1  # In progress

        # Queue the send operation
        self._async_send_queue.put(self._send_data)

        logger.debug(f"Async send initiated for {len(self._send_data)} bytes")
        return 0

    def check_as_b_send_completion(self) -> Tuple[str, c_int32]:
        """
        Check if async send completed.

        Returns:
            Tuple of (status_string, operation_result)
        """
        if self._async_send_in_progress:
            return "job in progress", c_int32(0)

        return_values = {
            0: "job complete",
            1: "job in progress",
            -2: "invalid handled supplied",
        }

        result = self._async_send_result
        return return_values.get(0, "unknown"), c_int32(result)

    def wait_as_b_send_completion(self, timeout: int = 0) -> int:
        """
        Wait for async send to complete.

        Args:
            timeout: Timeout in milliseconds (0 for infinite)

        Returns:
            0 on success, non-zero on error/timeout

        Raises:
            RuntimeError: If no async operation is in progress
        """
        if not self._async_send_in_progress:
            raise RuntimeError("No async send operation in progress")

        # Wait for completion
        wait_time = timeout / 1000.0 if timeout > 0 else None
        start = datetime.now()

        while self._async_send_in_progress:
            if wait_time is not None:
                elapsed = (datetime.now() - start).total_seconds()
                if elapsed >= wait_time:
                    return -1  # Timeout
            threading.Event().wait(0.01)  # Small sleep

        return self._async_send_result

    def check_as_b_recv_completion(self) -> int:
        """
        Check if async receive completed.

        Returns:
            0 if data available, 1 if in progress
        """
        try:
            self._recv_data = self._async_recv_queue.get_nowait()
            return 0  # Data available
        except Empty:
            return 1  # No data yet

    def get_status(self) -> c_int32:
        """
        Get partner status.

        Returns:
            Status code (0=stopped, 1=running, 2=connected)
        """
        if self.connected:
            return c_int32(PartnerStatus.CONNECTED)
        elif self.running:
            return c_int32(PartnerStatus.RUNNING)
        else:
            return c_int32(PartnerStatus.STOPPED)

    def get_stats(self) -> Tuple[c_uint32, c_uint32, c_uint32, c_uint32]:
        """
        Get partner statistics.

        Returns:
            Tuple of (bytes_sent, bytes_recv, send_errors, recv_errors)
        """
        return (c_uint32(self.bytes_sent), c_uint32(self.bytes_recv), c_uint32(self.send_errors), c_uint32(self.recv_errors))

    def get_times(self) -> Tuple[c_int32, c_int32]:
        """
        Get last operation times.

        Returns:
            Tuple of (last_send_time_ms, last_recv_time_ms)
        """
        return c_int32(self.last_send_time), c_int32(self.last_recv_time)

    def get_last_error(self) -> c_int32:
        """
        Get last error code.

        Returns:
            Last error code
        """
        return c_int32(self.last_error)

    def get_param(self, parameter: Parameter) -> int:
        """
        Get partner parameter.

        Args:
            parameter: Parameter to read

        Returns:
            Parameter value
        """
        param_values = {
            Parameter.LocalPort: self.local_port,
            Parameter.RemotePort: self.remote_port,
            Parameter.PingTimeout: 750,
            Parameter.SendTimeout: 10,
            Parameter.RecvTimeout: 3000,
            Parameter.SrcRef: 256,
            Parameter.DstRef: 0,
            Parameter.PDURequest: 480,
            Parameter.WorkInterval: 100,
            Parameter.BSendTimeout: 3000,
            Parameter.BRecvTimeout: 3000,
            Parameter.RecoveryTime: 500,
            Parameter.KeepAliveTime: 5000,
        }
        value = param_values.get(parameter)
        if value is None:
            raise RuntimeError(f"Parameter {parameter} not supported")
        logger.debug(f"Getting parameter {parameter} = {value}")
        return value

    def set_param(self, parameter: Parameter, value: int) -> int:
        """
        Set partner parameter.

        Args:
            parameter: Parameter to set
            value: Value to set

        Returns:
            0 on success
        """
        # Some parameters cannot be set
        if parameter == Parameter.RemotePort:
            raise RuntimeError(f"Cannot set parameter {parameter}")

        if parameter == Parameter.LocalPort:
            self.local_port = value
        logger.debug(f"Setting parameter {parameter} to {value}")
        return 0

    def set_recv_callback(self) -> int:
        """
        Sets the user callback for incoming data.

        Returns:
            0 on success
        """
        logger.debug("set_recv_callback called")
        return 0

    def set_send_callback(self) -> int:
        """
        Sets the user callback for completed async sends.

        Returns:
            0 on success
        """
        logger.debug("set_send_callback called")
        return 0

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

    def _connect_to_remote(self) -> None:
        """Connect to remote partner (active mode)."""
        if not self.remote_ip:
            raise S7ConnectionError("Remote IP not specified for active partner")

        self._connection = ISOTCPConnection(
            host=self.remote_ip, port=self.port, local_tsap=self.local_tsap, remote_tsap=self.remote_tsap
        )

        self._connection.connect()
        self._socket = self._connection.socket
        self.connected = True

        logger.info(f"Connected to remote partner at {self.remote_ip}:{self.port}")

    def _start_listening(self) -> None:
        """Start listening for incoming connections (passive mode)."""
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.local_ip, self.port))
        self._server_socket.listen(1)
        self._server_socket.settimeout(1.0)  # Allow periodic check

        logger.info(f"Partner listening on {self.local_ip}:{self.port}")

        # Start accept thread
        accept_thread = threading.Thread(target=self._accept_connection, daemon=True)
        accept_thread.start()

    def _accept_connection(self) -> None:
        """Accept incoming connection in passive mode."""
        while self.running and not self._stop_event.is_set():
            try:
                client_sock, addr = self._server_socket.accept()

                # Create connection object
                self._socket = client_sock
                self._connection = ISOTCPConnection(
                    host=addr[0], port=addr[1], local_tsap=self.local_tsap, remote_tsap=self.remote_tsap
                )
                self._connection.socket = client_sock
                self._connection.connected = True
                self.connected = True

                logger.info(f"Partner connection accepted from {addr}")
                break

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Accept failed: {e}")
                break

    def _async_processor(self) -> None:
        """Background thread for processing async operations."""
        while not self._stop_event.is_set():
            # Process async sends
            try:
                data = self._async_send_queue.get(timeout=0.1)

                try:
                    # Temporarily set send data and call b_send
                    old_data = self._send_data
                    self._send_data = data
                    result = self.b_send()
                    self._send_data = old_data
                    self._async_send_result = result

                    if self._send_callback_fn:
                        self._send_callback_fn(result)

                except Exception as e:
                    self._async_send_result = -1
                    logger.error(f"Async send failed: {e}")
                finally:
                    self._async_send_in_progress = False

            except Empty:
                pass
            except Exception:
                break

    def _build_partner_data_pdu(self, data: bytes) -> bytes:
        """
        Build partner data PDU.

        Args:
            data: Data to send

        Returns:
            PDU bytes
        """
        # S7 partner data PDU format:
        # Header + Data
        header = struct.pack(
            ">BBHH",
            0x32,  # Protocol ID (S7)
            0x07,  # Partner PDU type
            len(data),  # Data length high
            0x0000,  # Reserved
        )
        return header + data

    def _parse_partner_data_pdu(self, pdu: bytes) -> bytes:
        """
        Parse partner data PDU.

        Args:
            pdu: PDU bytes

        Returns:
            Extracted data
        """
        if len(pdu) < 6:
            raise S7Error("Invalid partner PDU: too short")

        # Skip header
        return pdu[6:]

    def _build_partner_ack(self) -> bytes:
        """Build partner acknowledgment PDU."""
        return struct.pack(
            ">BBHH",
            0x32,  # Protocol ID
            0x08,  # ACK type
            0x0000,  # Reserved
            0x0000,  # Status OK
        )

    def _parse_partner_ack(self, pdu: bytes) -> None:
        """Parse partner acknowledgment PDU."""
        if len(pdu) < 6:
            raise S7Error("Invalid partner ACK: too short")

        protocol_id, pdu_type = struct.unpack(">BB", pdu[:2])

        if pdu_type != 0x08:
            raise S7Error(f"Expected partner ACK, got {pdu_type:#02x}")

    def __enter__(self) -> "Partner":
        """Context manager entry."""
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        """Context manager exit."""
        self.destroy()

    def __del__(self) -> None:
        """Destructor."""
        try:
            self.stop()
        except Exception:
            pass
