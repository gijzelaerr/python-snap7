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
from typing import Optional, Tuple, Callable, Any
from queue import Queue, Empty
from datetime import datetime

from .connection import ISOTCPConnection
from .errors import S7Error, S7ConnectionError, S7TimeoutError

logger = logging.getLogger(__name__)


class PartnerStatus:
    """Partner status constants."""
    STOPPED = 0
    RUNNING = 1
    CONNECTED = 2


class WirePartner:
    """
    Pure Python S7 partner implementation.

    Implements peer-to-peer S7 communication where both partners can
    send and receive data asynchronously. Supports both active (initiates
    connection) and passive (waits for connection) modes.
    """

    def __init__(self, active: bool = False):
        """
        Initialize S7 partner.

        Args:
            active: If True, this partner initiates the connection.
                   If False, this partner waits for incoming connections.
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

        # Socket and connection
        self.socket: Optional[socket.socket] = None
        self.server_socket: Optional[socket.socket] = None  # For passive mode
        self.connection: Optional[ISOTCPConnection] = None

        # Statistics
        self.bytes_sent = 0
        self.bytes_recv = 0
        self.send_errors = 0
        self.recv_errors = 0

        # Timing
        self.last_send_time = 0
        self.last_recv_time = 0

        # Callbacks
        self.recv_callback: Optional[Callable[[bytes], None]] = None
        self.send_callback: Optional[Callable[[int], None]] = None

        # Async operation support
        self._async_send_queue: Queue = Queue()
        self._async_recv_queue: Queue = Queue()
        self._async_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Last error
        self.last_error = 0

        # Buffer for async operations
        self._send_buffer: Optional[bytes] = None
        self._recv_buffer: Optional[bytes] = None
        self._async_send_in_progress = False
        self._async_send_result = 0

        logger.info(f"S7 Partner initialized (active={active}, pure Python implementation)")

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

        if self.connection:
            self.connection.disconnect()
            self.connection = None

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None

        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None

        self.connected = False
        self.running = False

        logger.info("Partner stopped")
        return 0

    def b_send(self, data: bytes) -> int:
        """
        Send data synchronously (blocking).

        Args:
            data: Data to send

        Returns:
            0 on success
        """
        if not self.connected:
            self.send_errors += 1
            raise S7ConnectionError("Not connected")

        start_time = datetime.now()

        try:
            # Build partner data PDU
            pdu = self._build_partner_data_pdu(data)

            # Send via ISO connection
            self.connection.send_data(pdu)

            # Wait for acknowledgment
            ack_data = self.connection.receive_data()
            self._parse_partner_ack(ack_data)

            self.bytes_sent += len(data)
            self.last_send_time = int((datetime.now() - start_time).total_seconds() * 1000)

            logger.debug(f"Sent {len(data)} bytes synchronously")
            return 0

        except Exception as e:
            self.send_errors += 1
            self.last_error = -1
            logger.error(f"Synchronous send failed: {e}")
            raise S7ConnectionError(f"Send failed: {e}")

    def b_recv(self, timeout: int = 0) -> Tuple[int, bytes]:
        """
        Receive data synchronously (blocking).

        Args:
            timeout: Timeout in milliseconds (0 for infinite)

        Returns:
            Tuple of (result_code, received_data)
        """
        if not self.connected:
            self.recv_errors += 1
            return -1, b''

        start_time = datetime.now()

        try:
            # Set socket timeout if specified
            if timeout > 0:
                self.socket.settimeout(timeout / 1000.0)
            else:
                self.socket.settimeout(None)

            # Receive partner data
            data = self.connection.receive_data()
            received = self._parse_partner_data_pdu(data)

            # Send acknowledgment
            ack = self._build_partner_ack()
            self.connection.send_data(ack)

            self.bytes_recv += len(received)
            self.last_recv_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Call receive callback if set
            if self.recv_callback:
                self.recv_callback(received)

            logger.debug(f"Received {len(received)} bytes synchronously")
            return 0, received

        except socket.timeout:
            return 1, b''  # Timeout
        except Exception as e:
            self.recv_errors += 1
            self.last_error = -1
            logger.error(f"Synchronous receive failed: {e}")
            return -1, b''

    def as_b_send(self, data: bytes) -> int:
        """
        Send data asynchronously (non-blocking).

        Args:
            data: Data to send

        Returns:
            0 on success (send initiated)
        """
        if not self.connected:
            self.send_errors += 1
            return -1

        self._send_buffer = data
        self._async_send_in_progress = True
        self._async_send_result = 1  # In progress

        # Queue the send operation
        self._async_send_queue.put(data)

        logger.debug(f"Async send initiated for {len(data)} bytes")
        return 0

    def check_as_b_send_completion(self) -> Tuple[int, int]:
        """
        Check if async send completed.

        Returns:
            Tuple of (status_code, operation_result)
            Status: 0 = complete, 1 = in progress, -2 = invalid
        """
        if self._async_send_in_progress:
            return 1, 0  # Still in progress

        result = self._async_send_result
        return 0, result  # Complete

    def wait_as_b_send_completion(self, timeout: int = 0) -> int:
        """
        Wait for async send to complete.

        Args:
            timeout: Timeout in milliseconds (0 for infinite)

        Returns:
            0 on success, non-zero on error/timeout
        """
        if not self._async_send_in_progress:
            return self._async_send_result

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
            0 if data available, 1 if in progress, -2 on error
        """
        try:
            self._recv_buffer = self._async_recv_queue.get_nowait()
            return 0  # Data available
        except Empty:
            return 1  # No data yet

    def get_status(self) -> int:
        """
        Get partner status.

        Returns:
            Status code (0=stopped, 1=running, 2=connected)
        """
        if self.connected:
            return PartnerStatus.CONNECTED
        elif self.running:
            return PartnerStatus.RUNNING
        else:
            return PartnerStatus.STOPPED

    def get_stats(self) -> Tuple[int, int, int, int]:
        """
        Get partner statistics.

        Returns:
            Tuple of (bytes_sent, bytes_recv, send_errors, recv_errors)
        """
        return self.bytes_sent, self.bytes_recv, self.send_errors, self.recv_errors

    def get_times(self) -> Tuple[int, int]:
        """
        Get last operation times.

        Returns:
            Tuple of (last_send_time_ms, last_recv_time_ms)
        """
        return self.last_send_time, self.last_recv_time

    def get_last_error(self) -> int:
        """Get last error code."""
        return self.last_error

    def set_recv_callback(self, callback: Callable[[bytes], None]) -> int:
        """
        Set receive callback.

        Args:
            callback: Function to call when data is received

        Returns:
            0 on success
        """
        self.recv_callback = callback
        return 0

    def set_send_callback(self, callback: Callable[[int], None]) -> int:
        """
        Set send callback.

        Args:
            callback: Function to call when send completes

        Returns:
            0 on success
        """
        self.send_callback = callback
        return 0

    def _connect_to_remote(self) -> None:
        """Connect to remote partner (active mode)."""
        if not self.remote_ip:
            raise S7ConnectionError("Remote IP not specified for active partner")

        self.connection = ISOTCPConnection(
            host=self.remote_ip,
            port=self.port,
            local_tsap=self.local_tsap,
            remote_tsap=self.remote_tsap
        )

        self.connection.connect()
        self.socket = self.connection.socket
        self.connected = True

        logger.info(f"Connected to remote partner at {self.remote_ip}:{self.port}")

    def _start_listening(self) -> None:
        """Start listening for incoming connections (passive mode)."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.local_ip, self.port))
        self.server_socket.listen(1)
        self.server_socket.settimeout(1.0)  # Allow periodic check

        logger.info(f"Partner listening on {self.local_ip}:{self.port}")

        # Start accept thread
        accept_thread = threading.Thread(target=self._accept_connection, daemon=True)
        accept_thread.start()

    def _accept_connection(self) -> None:
        """Accept incoming connection in passive mode."""
        while self.running and not self._stop_event.is_set():
            try:
                client_sock, addr = self.server_socket.accept()

                # Create connection object
                self.socket = client_sock
                self.connection = ISOTCPConnection(
                    host=addr[0],
                    port=addr[1],
                    local_tsap=self.local_tsap,
                    remote_tsap=self.remote_tsap
                )
                self.connection.socket = client_sock
                self.connection.connected = True
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
                    result = self.b_send(data)
                    self._async_send_result = result

                    if self.send_callback:
                        self.send_callback(result)

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
        # For simplicity, using a basic structure
        header = struct.pack(
            '>BBHH',
            0x32,        # Protocol ID (S7)
            0x07,        # Partner PDU type
            len(data),   # Data length high
            0x0000       # Reserved
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
            '>BBHH',
            0x32,        # Protocol ID
            0x08,        # ACK type
            0x0000,      # Reserved
            0x0000       # Status OK
        )

    def _parse_partner_ack(self, pdu: bytes) -> None:
        """Parse partner acknowledgment PDU."""
        if len(pdu) < 6:
            raise S7Error("Invalid partner ACK: too short")

        protocol_id, pdu_type = struct.unpack('>BB', pdu[:2])

        if pdu_type != 0x08:
            raise S7Error(f"Expected partner ACK, got {pdu_type:#02x}")

    def __del__(self) -> None:
        """Destructor."""
        try:
            self.stop()
        except Exception:
            pass

    def __enter__(self) -> "WirePartner":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
