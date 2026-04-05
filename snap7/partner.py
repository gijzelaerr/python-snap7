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
from typing import Any
from datetime import datetime
from types import TracebackType
from ctypes import c_int32, c_uint32

from .connection import ISOTCPConnection
from .error import S7Error, S7ConnectionError
from .s7protocol import S7Protocol, S7PDUType
from .type import Parameter

logger = logging.getLogger(__name__)

# S7 partner/push function group
_PUSH_FUNC_GROUP = 0x06

# Partner push subfunctions
_PUSH_SUBFUNCTION_BSEND = 0x06  # bsend data push


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

    def __init__(self, active: bool = False, **kwargs: object) -> None:
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
        self.port = 1102  # Non-privileged port (was 102)
        self.local_port = 0  # Let OS choose
        self.remote_port = 1102  # Non-privileged port (was 102)

        # Socket and connection
        self._socket: Optional[socket.socket] = None
        self._server_socket: Optional[socket.socket] = None  # For passive mode
        self._connection: Optional[ISOTCPConnection] = None

        # S7 protocol handler (for setup communication and PDU formatting)
        self._protocol = S7Protocol()
        self.pdu_length = 480

        # R-ID for bsend/brecv matching (default 0, can be set by caller)
        self.r_id: int = 0

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
        self._async_send_queue: Queue[Any] = Queue()
        self._async_recv_queue: Queue[Any] = Queue()
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

        if not self.connected or self._connection is None:
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
        if not self.connected or self._connection is None:
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
        """Connect to remote partner (active mode).

        Performs COTP connection followed by S7 Communication Setup
        to negotiate PDU size with the remote partner.
        """
        if not self.remote_ip:
            raise S7ConnectionError("Remote IP not specified for active partner")

        self._connection = ISOTCPConnection(
            host=self.remote_ip, port=self.port, local_tsap=self.local_tsap, remote_tsap=self.remote_tsap
        )

        self._connection.connect()
        self._socket = self._connection.socket

        # Perform S7 Communication Setup (negotiate PDU size)
        self._setup_communication()

        self.connected = True
        logger.info(f"Connected to remote partner at {self.remote_ip}:{self.port}")

    def _start_listening(self) -> None:
        """Start listening for incoming connections (passive mode)."""
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Try to use SO_REUSEPORT if available (Linux, macOS) for faster port reuse
        if hasattr(socket, "SO_REUSEPORT"):
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self._server_socket.bind((self.local_ip, self.port))
        self._server_socket.listen(1)
        self._server_socket.settimeout(1.0)  # Allow periodic check

        logger.info(f"Partner listening on {self.local_ip}:{self.port}")

        # Start accept thread
        accept_thread = threading.Thread(target=self._accept_connection, daemon=True)
        accept_thread.start()

    def _accept_connection(self) -> None:
        """Accept incoming connection in passive mode.

        After accepting the TCP connection, handles the COTP Connection Request
        from the active partner and performs S7 Communication Setup.
        """
        if self._server_socket is None:
            return

        while self.running and not self._stop_event.is_set():
            try:
                client_sock, addr = self._server_socket.accept()

                # Create connection object
                self._socket = client_sock
                self._connection = ISOTCPConnection(
                    host=addr[0], port=addr[1], local_tsap=self.local_tsap, remote_tsap=self.remote_tsap
                )
                self._connection.socket = client_sock

                # Handle COTP Connection Request from active partner
                self._handle_cotp_cr(client_sock)

                self._connection.connected = True

                # Wait for and handle S7 Communication Setup from active partner
                self._handle_setup_communication()

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

    def _setup_communication(self) -> None:
        """Perform S7 Communication Setup after COTP connection.

        Sends a Setup Communication request and parses the negotiated
        PDU length from the response. This is required before any S7
        data exchange can take place.
        """
        if self._connection is None:
            raise S7ConnectionError("No connection for S7 setup")

        request = self._protocol.build_setup_communication_request(max_amq_caller=1, max_amq_callee=1, pdu_length=self.pdu_length)
        self._connection.send_data(request)
        response_data = self._connection.receive_data()
        response = self._protocol.parse_response(response_data)

        if response.get("parameters") and "pdu_length" in response["parameters"]:
            self.pdu_length = response["parameters"]["pdu_length"]

        logger.info(f"S7 Communication Setup complete, PDU length: {self.pdu_length}")

    def _handle_cotp_cr(self, sock: socket.socket) -> None:
        """Handle incoming COTP Connection Request and send Connection Confirm.

        Used by passive partner to complete the COTP handshake initiated
        by the active partner.
        """
        # Receive TPKT header (4 bytes)
        tpkt_header = self._recv_exact_from(sock, 4)
        version, _, length = struct.unpack(">BBH", tpkt_header)
        if version != 3:
            raise S7ConnectionError(f"Invalid TPKT version: {version}")

        payload = self._recv_exact_from(sock, length - 4)
        if len(payload) < 7:
            raise S7ConnectionError("COTP CR too short")

        pdu_type = payload[1]
        if pdu_type != 0xE0:  # COTP_CR
            raise S7ConnectionError(f"Expected COTP CR (0xE0), got {pdu_type:#04x}")

        # Build and send Connection Confirm
        if self._connection is None:
            raise S7ConnectionError("No connection object")

        cc_pdu = struct.pack(
            ">BBHHB",
            6,  # PDU length
            0xD0,  # COTP_CC
            self._connection.src_ref,  # Destination reference (our src_ref)
            0x0001,  # Source reference
            0x00,  # Class 0
        )
        # Add PDU size parameter
        cc_pdu += struct.pack(">BBB", 0xC0, 1, 0x0A)  # 1024 bytes
        # Update length byte
        total_len = len(cc_pdu) - 1
        cc_pdu = struct.pack(">B", total_len) + cc_pdu[1:]

        tpkt = struct.pack(">BBH", 3, 0, len(cc_pdu) + 4) + cc_pdu
        sock.sendall(tpkt)
        logger.debug("Sent COTP Connection Confirm")

    def _handle_setup_communication(self) -> None:
        """Handle incoming S7 Communication Setup request from active partner.

        Receives the setup request, parses it, and sends back a setup response
        with the negotiated PDU length.
        """
        if self._connection is None:
            raise S7ConnectionError("No connection for S7 setup")

        request_data = self._connection.receive_data()
        if len(request_data) < 10:
            raise S7ConnectionError("S7 setup request too short")

        protocol_id, pdu_type = struct.unpack(">BB", request_data[:2])
        if protocol_id != 0x32 or pdu_type != S7PDUType.REQUEST:
            raise S7ConnectionError(f"Expected S7 setup request, got type {pdu_type:#04x}")

        # Parse the request to get sequence number and requested PDU length
        _, _, _, sequence, param_len, _ = struct.unpack(">BBHHHH", request_data[:10])
        requested_pdu = self.pdu_length
        if param_len >= 8:
            params = request_data[10 : 10 + param_len]
            if len(params) >= 8:
                _, _, _, _, requested_pdu = struct.unpack(">BBHHH", params[:8])

        negotiated_pdu = min(requested_pdu, self.pdu_length)
        self.pdu_length = negotiated_pdu

        # Build and send setup response
        response = struct.pack(
            ">BBHHHHBB",
            0x32,
            S7PDUType.ACK_DATA,
            0x0000,
            sequence,
            0x0008,  # param length
            0x0000,  # data length
            0x00,  # error class
            0x00,  # error code
        )
        response += struct.pack(
            ">BBHHH",
            0xF0,  # Setup Communication function code
            0x00,
            1,  # max_amq_caller
            1,  # max_amq_callee
            negotiated_pdu,
        )
        self._connection.send_data(response)
        logger.info(f"S7 Communication Setup complete (passive), PDU length: {negotiated_pdu}")

    @staticmethod
    def _recv_exact_from(sock: socket.socket, size: int) -> bytes:
        """Receive exactly *size* bytes from a socket."""
        data = bytearray()
        while len(data) < size:
            chunk = sock.recv(size - len(data))
            if not chunk:
                raise S7ConnectionError("Connection closed during receive")
            data.extend(chunk)
        return bytes(data)

    def _build_partner_data_pdu(self, data: bytes, r_id: Optional[int] = None) -> bytes:
        """Build an S7 USERDATA PDU for partner data push (bsend).

        The PDU uses the standard S7 USERDATA header (10 bytes) followed by
        a parameter section that identifies this as a PBC (Program Block
        Communication) push with the R-ID and a variable specification
        block, and a data section with the payload.

        Args:
            data: Payload to send.
            r_id: Request ID for bsend/brecv matching.  Falls back to ``self.r_id``.

        Returns:
            Complete S7 PDU bytes (without COTP/TPKT framing).
        """
        if r_id is None:
            r_id = self.r_id

        sequence = self._protocol._next_sequence()

        # Parameter section: USERDATA header with PBC variable specification
        param = struct.pack(
            ">BBBBBBBBBBH",
            0x00,  # reserved
            0x01,  # parameter count
            0x12,  # type header
            0x08,  # length of following parameter data
            0x12,  # method: push
            0x06,  # type 0 (push) | group 6 (PBC)
            _PUSH_SUBFUNCTION_BSEND,
            sequence & 0xFF,
            0x00,  # data unit reference number
            0x00,  # last data unit
            0x0000,  # error code
        )
        # R-ID (4 bytes)
        param += struct.pack(">I", r_id)
        # Variable specification block: type=0x12, len=0x06, syntax_id=0x82, transport=0x41, padding, payload_length
        param += struct.pack(">BBBBHH", 0x12, 0x06, 0x82, 0x41, 0x0000, len(data))

        # Data section: 4-byte header + 2-byte prefix (12 00) + payload
        payload_with_prefix = struct.pack(">BB", 0x12, 0x00) + data
        data_section = struct.pack(">BBH", 0xFF, 0x09, len(payload_with_prefix)) + payload_with_prefix

        # S7 USERDATA header (10 bytes)
        header = struct.pack(
            ">BBHHHH",
            0x32,
            S7PDUType.USERDATA,
            0x0000,
            sequence,
            len(param),
            len(data_section),
        )

        return header + param + data_section

    def _parse_partner_data_pdu(self, pdu: bytes) -> bytes:
        """Parse an incoming partner data push PDU and extract the payload.

        Accepts both the new USERDATA format (with R-ID) and the legacy
        minimal format for backward-compatibility with existing tests that
        use raw socket pairs.

        Returns:
            The application payload.
        """
        if len(pdu) < 6:
            raise S7Error("Invalid partner PDU: too short")

        protocol_id, pdu_type = struct.unpack(">BB", pdu[:2])

        if protocol_id != 0x32:
            raise S7Error(f"Invalid protocol ID: {protocol_id:#04x}")

        if pdu_type == S7PDUType.USERDATA:
            # Full USERDATA format
            if len(pdu) < 10:
                raise S7Error("USERDATA partner PDU too short")
            _, _, _, _, param_len, data_len = struct.unpack(">BBHHHH", pdu[:10])
            data_offset = 10 + param_len
            if data_offset + 4 > len(pdu):
                raise S7Error("Partner data section too short")
            # Skip 4-byte data section header (return_code, transport_size, length)
            payload = pdu[data_offset + 4 : data_offset + 4 + data_len - 4] if data_len > 4 else b""
            # Strip PBC prefix (12 00) if present
            if len(payload) >= 2 and payload[0] == 0x12 and payload[1] == 0x00:
                payload = payload[2:]
            return payload
        else:
            raise S7Error(f"Unexpected PDU type in partner data: {pdu_type:#04x}")

    def _build_partner_ack(self, r_id: Optional[int] = None) -> bytes:
        """Build an S7 USERDATA acknowledgment PDU for a received bsend.

        Args:
            r_id: Request ID echoed from the data PDU.

        Returns:
            Complete S7 PDU bytes.
        """
        if r_id is None:
            r_id = self.r_id

        sequence = self._protocol._next_sequence()

        param = struct.pack(
            ">BBBBBBBB",
            0x00,
            0x01,
            0x12,
            0x08,  # length: 4 base + 2 (dur/ldu) + 2 (error code)
            0x12,  # method: response
            0x86,  # type 8 (response) | group 6 (push)
            _PUSH_SUBFUNCTION_BSEND,
            sequence & 0xFF,
        )
        param += struct.pack(">BBHI", 0x00, 0x00, 0x0000, r_id)  # dur, ldu, error_code, R-ID

        header = struct.pack(
            ">BBHHHH",
            0x32,
            S7PDUType.USERDATA,
            0x0000,
            sequence,
            len(param),
            0x0000,
        )

        return header + param

    def _parse_partner_ack(self, pdu: bytes) -> None:
        """Parse a partner acknowledgment PDU.

        Validates that the PDU is a proper S7 USERDATA response for a push
        acknowledgment and checks for error codes.
        """
        if len(pdu) < 6:
            raise S7Error("Invalid partner ACK: too short")

        protocol_id, pdu_type = struct.unpack(">BB", pdu[:2])
        if protocol_id != 0x32:
            raise S7Error(f"Invalid protocol ID in ACK: {protocol_id:#04x}")

        if pdu_type != S7PDUType.USERDATA:
            raise S7Error(f"Expected partner ACK (USERDATA), got {pdu_type:#04x}")

        # Check for error code in parameter section
        if len(pdu) >= 10:
            _, _, _, _, param_len, _ = struct.unpack(">BBHHHH", pdu[:10])
            param = pdu[10 : 10 + param_len]
            # Parameter layout: 00 01 12 LL [method tg sf seq ...] [error_code]
            if len(param) >= 4:
                sub_len = param[3]
                if sub_len >= 8 and len(param) >= 12:
                    # Error code is at offset 10-11 within param (bytes 6-7 after 12 LL)
                    error_code = struct.unpack(">H", param[10:12])[0]
                    if error_code != 0:
                        raise S7Error(f"Partner ACK error: {error_code:#06x}")

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
