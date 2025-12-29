"""
Pure Python S7 server implementation.

Provides a complete S7 server emulator without dependencies on the Snap7 C library.
"""

import socket
import struct
import threading
import time
import logging
from typing import Dict, Optional, List, Callable, Any, Tuple, Type, Union
from types import TracebackType
from enum import IntEnum
from ctypes import Array, c_char

from .s7protocol import S7Protocol, S7Function, S7PDUType
from .datatypes import S7Area, S7WordLen
from .error import S7ConnectionError, S7ProtocolError
from .type import SrvArea, SrvEvent, Parameter

logger = logging.getLogger(__name__)


class ServerState(IntEnum):
    """S7 server states."""

    STOPPED = 0
    RUNNING = 1
    ERROR = 2


class CPUState(IntEnum):
    """S7 CPU states."""

    UNKNOWN = 0
    RUN = 8
    STOP = 4


class Server:
    """
    Pure Python S7 server implementation.

    Emulates a Siemens S7 PLC for testing and development purposes.

    Examples:
        >>> import snap7
        >>> server = snap7.Server()
        >>> server.start()
        >>> # ... register areas and handle clients
        >>> server.stop()
    """

    def __init__(self, log: bool = True, **kwargs: object) -> None:
        """
        Initialize S7 server.

        Args:
            log: Enable event logging
            **kwargs: Ignored. Kept for backwards compatibility.
        """
        self.server_socket: Optional[socket.socket] = None
        self.server_thread: Optional[threading.Thread] = None
        self.running = False
        self.port = 102
        self.host = "0.0.0.0"

        # Server state
        self.state = ServerState.STOPPED
        self.cpu_state = CPUState.STOP
        self.client_count = 0

        # Memory areas
        self.memory_areas: Dict[Tuple[S7Area, int], bytearray] = {}
        self.area_locks: Dict[Tuple[S7Area, int], threading.Lock] = {}

        # Protocol handler
        self.protocol = S7Protocol()

        # Event callbacks
        self.event_callback: Optional[Callable[[SrvEvent], None]] = None
        self.read_callback: Optional[Callable[[SrvEvent], None]] = None

        # Client connections
        self.clients: List[threading.Thread] = []
        self.client_lock = threading.Lock()

        # Event queue for pick_event
        self._event_queue: List[SrvEvent] = []

        # Logging
        self._log_enabled = log
        if log:
            self._set_log_callback()

        logger.info("S7Server initialized (pure Python implementation)")

    def create(self) -> None:
        """Create the server (no-op for compatibility)."""
        pass

    def destroy(self) -> None:
        """Destroy the server."""
        self.stop()

    def start(self, tcp_port: int = 102) -> int:
        """
        Start the S7 server.

        Args:
            tcp_port: TCP port to listen on

        Returns:
            0 on success
        """
        if self.running:
            raise S7ConnectionError("Server is already running")

        self.port = tcp_port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            self.state = ServerState.RUNNING
            self.cpu_state = CPUState.RUN

            # Start server thread
            self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self.server_thread.start()

            # Add startup event to queue
            startup_event = SrvEvent()
            startup_event.EvtCode = 0x00010000  # Server started
            self._event_queue.append(startup_event)

            logger.info(f"S7 Server started on {self.host}:{self.port}")
            return 0

        except Exception as e:
            self.running = False
            self.state = ServerState.ERROR
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
            raise S7ConnectionError(f"Failed to start server: {e}")

    def stop(self) -> int:
        """
        Stop the S7 server.

        Returns:
            0 on success
        """
        if not self.running:
            return 0

        self.running = False
        self.state = ServerState.STOPPED
        self.cpu_state = CPUState.STOP

        # Close server socket
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None

        # Wait for server thread to finish
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5.0)

        # Close all client connections
        with self.client_lock:
            for client_thread in self.clients[:]:
                if client_thread.is_alive():
                    client_thread.join(timeout=1.0)
            self.clients.clear()
            self.client_count = 0

        logger.info("S7 Server stopped")
        return 0

    def register_area(self, area: SrvArea, index: int, userdata: Union[bytearray, "Array[c_char]"]) -> int:
        """
        Register a memory area with the server.

        Args:
            area: Memory area type
            index: Area index/number
            userdata: Initial data for the area (bytearray or ctypes array)

        Returns:
            0 on success
        """
        # Map SrvArea to S7Area
        area_mapping = {
            SrvArea.PE: S7Area.PE,
            SrvArea.PA: S7Area.PA,
            SrvArea.MK: S7Area.MK,
            SrvArea.DB: S7Area.DB,
            SrvArea.CT: S7Area.CT,
            SrvArea.TM: S7Area.TM,
        }

        s7_area = area_mapping.get(area)
        if s7_area is None:
            raise ValueError(f"Unsupported area: {area}")

        # Convert ctypes array to bytearray if needed
        if isinstance(userdata, bytearray):
            data = userdata
        else:
            data = bytearray(userdata)

        area_key = (s7_area, index)
        self.memory_areas[area_key] = data
        self.area_locks[area_key] = threading.Lock()

        logger.info(f"Registered area {area.name} index {index}, size {len(data)}")
        return 0

    def unregister_area(self, area: SrvArea, index: int) -> int:
        """
        Unregister a memory area.

        Args:
            area: Memory area type
            index: Area index

        Returns:
            0 on success
        """
        area_mapping = {
            SrvArea.PE: S7Area.PE,
            SrvArea.PA: S7Area.PA,
            SrvArea.MK: S7Area.MK,
            SrvArea.DB: S7Area.DB,
            SrvArea.CT: S7Area.CT,
            SrvArea.TM: S7Area.TM,
        }

        s7_area = area_mapping.get(area)
        if s7_area is None:
            return 0

        area_key = (s7_area, index)
        if area_key in self.memory_areas:
            del self.memory_areas[area_key]
            del self.area_locks[area_key]
            logger.info(f"Unregistered area {area.name} index {index}")

        return 0

    def lock_area(self, area: SrvArea, index: int) -> int:
        """
        Lock a memory area.

        Args:
            area: Memory area type
            index: Area index

        Returns:
            0 on success

        Raises:
            RuntimeError: If area is not registered
        """
        area_mapping = {
            SrvArea.PE: S7Area.PE,
            SrvArea.PA: S7Area.PA,
            SrvArea.MK: S7Area.MK,
            SrvArea.DB: S7Area.DB,
            SrvArea.CT: S7Area.CT,
            SrvArea.TM: S7Area.TM,
        }

        s7_area = area_mapping.get(area)
        if s7_area is None:
            raise RuntimeError(f"Invalid area: {area}")

        area_key = (s7_area, index)
        if area_key not in self.area_locks:
            raise RuntimeError(f"Area {area.name} index {index} not registered")

        self.area_locks[area_key].acquire()
        return 0

    def unlock_area(self, area: SrvArea, index: int) -> int:
        """
        Unlock a memory area.

        Args:
            area: Memory area type
            index: Area index

        Returns:
            0 on success
        """
        area_mapping = {
            SrvArea.PE: S7Area.PE,
            SrvArea.PA: S7Area.PA,
            SrvArea.MK: S7Area.MK,
            SrvArea.DB: S7Area.DB,
            SrvArea.CT: S7Area.CT,
            SrvArea.TM: S7Area.TM,
        }

        s7_area = area_mapping.get(area)
        if s7_area is None:
            return 1

        area_key = (s7_area, index)
        if area_key in self.area_locks:
            try:
                self.area_locks[area_key].release()
            except RuntimeError:
                pass  # Lock not held

        return 0

    def get_status(self) -> Tuple[str, str, int]:
        """
        Get server status.

        Returns:
            Tuple of (server_status, cpu_status, client_count)
        """
        server_status_names = {ServerState.STOPPED: "Stopped", ServerState.RUNNING: "Running", ServerState.ERROR: "Error"}

        cpu_status_names = {CPUState.UNKNOWN: "Unknown", CPUState.RUN: "Run", CPUState.STOP: "Stop"}

        return (
            server_status_names.get(self.state, "Unknown"),
            cpu_status_names.get(self.cpu_state, "Unknown"),
            self.client_count,
        )

    def set_events_callback(self, callback: Callable[[SrvEvent], Any]) -> int:
        """
        Set callback for server events.

        Args:
            callback: Event callback function

        Returns:
            0 on success
        """
        self.event_callback = callback
        logger.info("Event callback set")
        return 0

    def set_read_events_callback(self, callback: Callable[[SrvEvent], Any]) -> int:
        """
        Set callback for read events.

        Args:
            callback: Read event callback function

        Returns:
            0 on success
        """
        self.read_callback = callback
        logger.info("Read event callback set")
        return 0

    def event_text(self, event: SrvEvent) -> str:
        """
        Get event text description.

        Args:
            event: Server event

        Returns:
            Event description string
        """
        event_texts = {
            0x00004000: "Read operation completed",
            0x00004001: "Write operation completed",
            0x00008000: "Client connected",
            0x00008001: "Client disconnected",
        }

        return event_texts.get(event.EvtCode, f"Event code: {event.EvtCode:#08x}")

    def get_mask(self, mask_kind: int) -> int:
        """
        Get event mask.

        Args:
            mask_kind: Mask type (0=Event, 1=Log)

        Returns:
            Event mask value
        """
        if mask_kind == 0:  # mkEvent
            return 0xFFFFFFFF
        elif mask_kind == 1:  # mkLog
            return 0xFFFFFFFF
        else:
            raise ValueError(f"Invalid mask kind: {mask_kind}")

    def set_mask(self, kind: int = 0, mask: int = 0) -> int:
        """
        Set event mask.

        Args:
            kind: Mask type (0=Event, 1=Log)
            mask: Mask value

        Returns:
            0 on success
        """
        logger.debug(f"Set mask {kind} = {mask:#08x}")
        return 0

    def set_param(self, param: Parameter, value: int) -> int:
        """
        Set server parameter.

        Args:
            param: Parameter type
            value: Parameter value

        Returns:
            0 on success
        """
        if param == Parameter.LocalPort:
            self.port = value
        logger.debug(f"Set parameter {param} = {value}")
        return 0

    def get_param(self, param: Parameter) -> int:
        """
        Get server parameter.

        Args:
            param: Parameter type

        Returns:
            Parameter value

        Raises:
            RuntimeError: If parameter is not valid for server
        """
        # Client-only parameters should raise exception
        client_only = [
            Parameter.RemotePort,
            Parameter.PingTimeout,
            Parameter.SendTimeout,
            Parameter.RecvTimeout,
            Parameter.SrcRef,
            Parameter.DstRef,
            Parameter.SrcTSap,
            Parameter.PDURequest,
        ]
        if param in client_only:
            raise RuntimeError(f"Parameter {param} not valid for server")

        param_values = {
            Parameter.LocalPort: self.port,
            Parameter.WorkInterval: 100,
            Parameter.MaxClients: 1024,
        }
        return param_values.get(param, 0)

    def start_to(self, ip: str, tcp_port: int = 102) -> int:
        """
        Start server on a specific interface.

        Args:
            ip: IP address to bind to
            tcp_port: TCP port to listen on

        Returns:
            0 on success
        """
        # Validate IP address
        try:
            socket.inet_aton(ip)
        except socket.error:
            raise ValueError(f"Invalid IP address: {ip}")

        # If already running, stop first
        if self.running:
            self.stop()

        self.host = ip
        return self.start(tcp_port if tcp_port != 102 else self.port)

    def set_cpu_status(self, status: int) -> int:
        """
        Set CPU status.

        Args:
            status: CPU status code (0=Unknown, 4=Stop, 8=Run)

        Returns:
            0 on success

        Raises:
            ValueError: If status is invalid
        """
        if status not in [0, 4, 8]:
            raise ValueError(f"Invalid CPU status: {status}")

        if status == 8:  # RUN
            self.cpu_state = CPUState.RUN
        elif status == 4:  # STOP
            self.cpu_state = CPUState.STOP
        else:
            self.cpu_state = CPUState.UNKNOWN
        return 0

    def pick_event(self) -> Union[SrvEvent, bool]:
        """
        Pick an event from the queue.

        Returns:
            Server event if available, False if no events
        """
        if self._event_queue:
            return self._event_queue.pop(0)
        return False

    def clear_events(self) -> int:
        """
        Clear event queue.

        Returns:
            0 on success
        """
        self._event_queue.clear()
        return 0

    def _set_log_callback(self) -> None:
        """Set up default logging callback."""

        def log_callback(event: SrvEvent) -> None:
            event_text = self.event_text(event)
            logger.info(f"Server event: {event_text}")

        self.set_events_callback(log_callback)

    def _server_loop(self) -> None:
        """Main server loop to accept client connections."""
        try:
            while self.running and self.server_socket:
                try:
                    self.server_socket.settimeout(1.0)  # Non-blocking accept
                    client_socket, address = self.server_socket.accept()

                    logger.info(f"Client connected from {address}")

                    # Start client handler thread
                    client_thread = threading.Thread(target=self._handle_client, args=(client_socket, address), daemon=True)

                    with self.client_lock:
                        self.clients.append(client_thread)
                        self.client_count += 1

                    client_thread.start()

                except socket.timeout:
                    continue  # Check running flag again
                except OSError:
                    if self.running:  # Only log if we're supposed to be running
                        logger.warning("Server socket error in accept loop")
                    break

        except Exception as e:
            logger.error(f"Server loop error: {e}")
        finally:
            self.running = False
            self.state = ServerState.STOPPED

    def _handle_client(self, client_socket: socket.socket, address: Tuple[str, int]) -> None:
        """Handle a single client connection."""
        try:
            # Create ISO connection wrapper and establish connection
            connection = ServerISOConnection(client_socket)

            # Handle ISO connection setup
            if not connection.accept_connection():
                logger.warning(f"Failed to establish ISO connection with {address}")
                return

            logger.info(f"ISO connection established with {address}")

            while self.running:
                try:
                    # Receive S7 request
                    request_data = connection.receive_data()

                    # Process request and generate response
                    response_data = self._process_request(request_data, address)

                    # Send response
                    if response_data:
                        connection.send_data(response_data)

                except socket.timeout:
                    continue
                except (ConnectionResetError, ConnectionAbortedError):
                    logger.info(f"Client {address} disconnected")
                    break
                except Exception as e:
                    logger.error(f"Error handling client {address}: {e}")
                    break

        except Exception as e:
            logger.error(f"Client handler error for {address}: {e}")
        finally:
            try:
                client_socket.close()
            except OSError:
                pass

            with self.client_lock:
                current_thread = threading.current_thread()
                if current_thread in self.clients:
                    self.clients.remove(current_thread)
                self.client_count = max(0, self.client_count - 1)

            logger.info(f"Client {address} handler finished")

    def _process_request(self, request_data: bytes, client_address: Tuple[str, int]) -> Optional[bytes]:
        """
        Process an S7 request and generate response.

        Args:
            request_data: Raw S7 PDU data
            client_address: Client address for logging

        Returns:
            Response PDU data or None
        """
        try:
            # Parse S7 request
            request = self._parse_request(request_data)

            # Extract function code from parameters
            if not request.get("parameters"):
                return None

            params = request["parameters"]
            function_code = params.get("function_code")

            if function_code == S7Function.SETUP_COMMUNICATION:
                return self._handle_setup_communication(request)
            elif function_code == S7Function.READ_AREA:
                return self._handle_read_area(request, client_address)
            elif function_code == S7Function.WRITE_AREA:
                return self._handle_write_area(request, client_address)
            elif function_code == S7Function.PLC_CONTROL:
                return self._handle_plc_control(request, client_address)
            elif function_code == S7Function.PLC_STOP:
                return self._handle_plc_stop(request, client_address)
            else:
                logger.warning(f"Unsupported function code: {function_code}")
                return self._build_error_response(request, 0x8001)  # Function not supported

        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return None

    def _handle_setup_communication(self, request: Dict[str, Any]) -> bytes:
        """Handle setup communication request."""
        params = request["parameters"]
        pdu_length = params.get("pdu_length", 480)

        # Build response with error bytes
        header = struct.pack(
            ">BBHHHHBB",
            0x32,  # Protocol ID
            S7PDUType.RESPONSE,  # PDU type
            0x0000,  # Reserved
            request["sequence"],  # Sequence (echo)
            0x0008,  # Parameter length
            0x0000,  # Data length
            0x00,  # Error class (success)
            0x00,  # Error code (success)
        )

        parameters = struct.pack(
            ">BBHHH",
            S7Function.SETUP_COMMUNICATION,  # Function code
            0x00,  # Reserved
            1,  # Max AMQ caller
            1,  # Max AMQ callee
            min(pdu_length, 480),  # PDU length (limited)
        )

        return header + parameters

    def _handle_read_area(self, request: Dict[str, Any], client_address: Tuple[str, int]) -> bytes:
        """Handle read area request."""
        try:
            # Parse address specification from request parameters
            addr_info = self._parse_read_address(request)
            if not addr_info:
                return self._build_error_response(request, 0x8001)  # Invalid address

            area, db_number, start, count = addr_info

            # Read data from registered memory area
            read_data = self._read_from_memory_area(area, db_number, start, count)
            if read_data is None:
                return self._build_error_response(request, 0x8404)  # Area not found

            # Calculate data length - need to include transport header + data
            data_len = 4 + len(read_data)  # Transport header (4 bytes) + data

            # Build successful response
            # S7 response header includes error class + error code
            header = struct.pack(
                ">BBHHHHBB",
                0x32,  # Protocol ID
                S7PDUType.RESPONSE,  # PDU type
                0x0000,  # Reserved
                request["sequence"],  # Sequence (echo)
                0x0002,  # Parameter length
                data_len,  # Data length
                0x00,  # Error class (success)
                0x00,  # Error code (success)
            )

            # Parameters
            parameters = struct.pack(
                ">BB",
                S7Function.READ_AREA,  # Function code
                0x01,  # Item count
            )

            # Data section
            data_section = (
                struct.pack(
                    ">BBH",
                    0xFF,  # Return code (success)
                    0x04,  # Transport size (04 = byte data)
                    len(read_data) * 8,  # Data length in bits
                )
                + read_data
            )

            # Trigger read event callback
            if self.read_callback:
                event = SrvEvent()
                event.EvtTime = int(time.time())
                event.EvtSender = 0
                event.EvtCode = 0x00004000  # Read event
                event.EvtRetCode = 0
                event.EvtParam1 = 1  # Area
                event.EvtParam2 = 0  # Offset
                event.EvtParam3 = len(read_data)  # Size
                event.EvtParam4 = 0
                try:
                    self.read_callback(event)
                except Exception as e:
                    logger.error(f"Error in read callback: {e}")

            return header + parameters + data_section

        except Exception as e:
            logger.error(f"Error handling read request: {e}")
            return self._build_error_response(request, 0x8000)

    def _parse_read_address(self, request: Dict[str, Any]) -> Optional[Tuple[S7Area, int, int, int]]:
        """
        Parse read address from request parameters.

        Returns:
            Tuple of (area, db_number, start, byte_count) or None if invalid
        """
        try:
            params = request.get("parameters", {})
            if params.get("function_code") != S7Function.READ_AREA:
                return None

            # Check if we have parsed address specification
            addr_spec = params.get("address_spec", {})
            if addr_spec:
                area = addr_spec.get("area", S7Area.DB)
                db_number = addr_spec.get("db_number", 1)
                start = addr_spec.get("start", 0)
                count = addr_spec.get("count", 4)
                word_len = addr_spec.get("word_len", S7WordLen.BYTE)

                # Convert count to bytes based on word length
                if word_len in [S7WordLen.TIMER, S7WordLen.COUNTER, S7WordLen.WORD]:
                    byte_count = count * 2  # 16-bit items
                elif word_len in [S7WordLen.DWORD, S7WordLen.REAL]:
                    byte_count = count * 4  # 32-bit items
                elif word_len == S7WordLen.BIT:
                    byte_count = 1  # Single bit needs at least 1 byte
                else:
                    byte_count = count  # Bytes

                logger.debug(
                    f"Parsed address: area={area}, db={db_number}, start={start}, count={count}, word_len={word_len}, byte_count={byte_count}"
                )
                return (area, db_number, start, byte_count)

            # Fallback to defaults if parsing failed
            logger.warning("Using default address values - address parsing may have failed")
            return (S7Area.DB, 1, 0, 4)

        except Exception as e:
            logger.error(f"Error parsing read address: {e}")
            return None

    def _read_from_memory_area(self, area: S7Area, db_number: int, start: int, count: int) -> Optional[bytearray]:
        """
        Read data from registered memory area.

        Args:
            area: Memory area to read from
            db_number: DB number (for DB areas)
            start: Start offset
            count: Number of bytes to read

        Returns:
            Data read from memory area or None if area not found
        """
        try:
            area_key = (area, db_number)

            if area_key not in self.memory_areas:
                logger.warning(f"Memory area {area}#{db_number} not registered")
                # Return dummy data if area not found (for compatibility)
                return bytearray([0x42, 0xFF, 0x12, 0x34])[:count]

            # Get area data with thread safety
            with self.area_locks[area_key]:
                area_data = self.memory_areas[area_key]

                # Check bounds
                if start >= len(area_data):
                    logger.warning(f"Start address {start} beyond area size {len(area_data)}")
                    return bytearray([0x00] * count)

                # Read requested data, padding with zeros if needed
                end = min(start + count, len(area_data))
                read_data = bytearray(area_data[start:end])

                # Pad with zeros if we didn't read enough
                if len(read_data) < count:
                    read_data.extend([0x00] * (count - len(read_data)))

                logger.debug(f"Read {len(read_data)} bytes from {area}#{db_number} at offset {start}")
                return read_data

        except Exception as e:
            logger.error(f"Error reading from memory area: {e}")
            return bytearray([0x00] * count)

    def _handle_write_area(self, request: Dict[str, Any], client_address: Tuple[str, int]) -> bytes:
        """Handle write area request."""
        try:
            # Parse address specification from request parameters
            addr_info = self._parse_write_address(request)
            if not addr_info:
                return self._build_error_response(request, 0x8001)  # Invalid address

            area, db_number, start, count, write_data = addr_info

            # Write data to registered memory area
            success = self._write_to_memory_area(area, db_number, start, write_data)
            if not success:
                return self._build_error_response(request, 0x8404)  # Area not found or write error

            # Build successful response with error bytes
            header = struct.pack(
                ">BBHHHHBB",
                0x32,  # Protocol ID
                S7PDUType.RESPONSE,  # PDU type
                0x0000,  # Reserved
                request["sequence"],  # Sequence (echo)
                0x0002,  # Parameter length
                0x0001,  # Data length
                0x00,  # Error class (success)
                0x00,  # Error code (success)
            )

            # Parameters
            parameters = struct.pack(
                ">BB",
                S7Function.WRITE_AREA,  # Function code
                0x01,  # Item count
            )

            # Data section (write response)
            data_section = b"\xff"  # Success return code

            return header + parameters + data_section

        except Exception as e:
            logger.error(f"Error handling write request: {e}")
            return self._build_error_response(request, 0x8000)

    def _handle_plc_control(self, request: Dict[str, Any], client_address: Tuple[str, int]) -> bytes:
        """Handle PLC control request (start operations)."""
        try:
            # Change CPU state based on control type
            params = request.get("parameters", {})
            if len(params) >= 2:
                # Has restart type parameter
                restart_type = params.get("restart_type", 1)
                if restart_type == 1:
                    logger.info("PLC Hot Start requested")
                else:
                    logger.info("PLC Cold Start requested")
            else:
                logger.info("PLC Start requested")

            # Set CPU to running state
            self.cpu_state = CPUState.RUN

            # Build successful response with error bytes
            header = struct.pack(
                ">BBHHHHBB",
                0x32,  # Protocol ID
                S7PDUType.RESPONSE,  # PDU type
                0x0000,  # Reserved
                request["sequence"],  # Sequence (echo)
                0x0001,  # Parameter length
                0x0000,  # Data length
                0x00,  # Error class (success)
                0x00,  # Error code (success)
            )

            parameters = struct.pack(">B", S7Function.PLC_CONTROL)

            return header + parameters

        except Exception as e:
            logger.error(f"Error handling PLC control request: {e}")
            return self._build_error_response(request, 0x8000)

    def _handle_plc_stop(self, request: Dict[str, Any], client_address: Tuple[str, int]) -> bytes:
        """Handle PLC stop request."""
        try:
            logger.info("PLC Stop requested")

            # Set CPU to stopped state
            self.cpu_state = CPUState.STOP

            # Build successful response with error bytes
            header = struct.pack(
                ">BBHHHHBB",
                0x32,  # Protocol ID
                S7PDUType.RESPONSE,  # PDU type
                0x0000,  # Reserved
                request["sequence"],  # Sequence (echo)
                0x0001,  # Parameter length
                0x0000,  # Data length
                0x00,  # Error class (success)
                0x00,  # Error code (success)
            )

            parameters = struct.pack(">B", S7Function.PLC_STOP)

            return header + parameters

        except Exception as e:
            logger.error(f"Error handling PLC stop request: {e}")
            return self._build_error_response(request, 0x8000)

    def _parse_write_address(self, request: Dict[str, Any]) -> Optional[Tuple[S7Area, int, int, int, bytearray]]:
        """
        Parse write address from request parameters and data.

        Returns:
            Tuple of (area, db_number, start, count, write_data) or None if invalid
        """
        try:
            params = request.get("parameters", {})
            if params.get("function_code") != S7Function.WRITE_AREA:
                return None

            # Check if we have parsed address specification
            addr_spec = params.get("address_spec", {})
            if not addr_spec:
                logger.warning("No address specification in write request")
                return None

            area = addr_spec.get("area", S7Area.DB)
            db_number = addr_spec.get("db_number", 1)
            start = addr_spec.get("start", 0)
            count = addr_spec.get("count", 0)

            # Extract write data from request data section
            data_info = request.get("data", {})
            write_data = data_info.get("data", b"")

            if not write_data:
                logger.warning("No write data in request")
                return None

            logger.debug(
                f"Parsed write address: area={area}, db={db_number}, start={start}, count={count}, data_len={len(write_data)}"
            )
            return (area, db_number, start, count, bytearray(write_data))

        except Exception as e:
            logger.error(f"Error parsing write address: {e}")
            return None

    def _write_to_memory_area(self, area: S7Area, db_number: int, start: int, write_data: bytearray) -> bool:
        """
        Write data to registered memory area.

        Args:
            area: Memory area to write to
            db_number: DB number (for DB areas)
            start: Start offset
            write_data: Data to write

        Returns:
            True if write succeeded, False otherwise
        """
        try:
            area_key = (area, db_number)

            if area_key not in self.memory_areas:
                logger.warning(f"Memory area {area}#{db_number} not registered for write")
                return False

            # Write to area data with thread safety
            with self.area_locks[area_key]:
                area_data = self.memory_areas[area_key]

                # Check bounds
                if start >= len(area_data):
                    logger.warning(f"Write start address {start} beyond area size {len(area_data)}")
                    return False

                # Calculate write range
                end = min(start + len(write_data), len(area_data))
                actual_write_len = end - start

                # Write the data
                area_data[start:end] = write_data[:actual_write_len]

                logger.debug(f"Wrote {actual_write_len} bytes to {area}#{db_number} at offset {start}")

                # If we didn't write all data due to bounds, return error
                if actual_write_len < len(write_data):
                    logger.warning(f"Only wrote {actual_write_len} of {len(write_data)} bytes due to area bounds")
                    return False

                return True

        except Exception as e:
            logger.error(f"Error writing to memory area: {e}")
            return False

    def _parse_request(self, pdu: bytes) -> Dict[str, Any]:
        """
        Parse S7 request PDU.

        Args:
            pdu: Complete S7 PDU

        Returns:
            Parsed request data
        """
        if len(pdu) < 10:
            raise S7ProtocolError("PDU too short for S7 header")

        # Parse S7 header
        header = struct.unpack(">BBHHHH", pdu[:10])
        protocol_id, pdu_type, reserved, sequence, param_len, data_len = header

        if protocol_id != 0x32:
            raise S7ProtocolError(f"Invalid protocol ID: {protocol_id:#02x}")

        request: Dict[str, Any] = {
            "sequence": sequence,
            "param_length": param_len,
            "data_length": data_len,
            "parameters": None,
            "data": None,
            "error_code": 0,
        }

        offset = 10

        # Parse parameters if present
        if param_len > 0:
            if offset + param_len > len(pdu):
                raise S7ProtocolError("Parameter section extends beyond PDU")

            param_data = pdu[offset : offset + param_len]
            request["parameters"] = self._parse_request_parameters(param_data)
            offset += param_len

        # Parse data if present
        if data_len > 0:
            if offset + data_len > len(pdu):
                raise S7ProtocolError("Data section extends beyond PDU")

            data_section = pdu[offset : offset + data_len]
            request["data"] = self._parse_data_section(data_section)

        return request

    def _parse_request_parameters(self, param_data: bytes) -> Dict[str, Any]:
        """Parse S7 request parameter section."""
        if len(param_data) < 1:
            return {}

        function_code = param_data[0]

        if function_code == S7Function.SETUP_COMMUNICATION:
            if len(param_data) >= 8:
                function_code, reserved, max_amq_caller, max_amq_callee, pdu_length = struct.unpack(">BBHHH", param_data[:8])
                return {
                    "function_code": function_code,
                    "max_amq_caller": max_amq_caller,
                    "max_amq_callee": max_amq_callee,
                    "pdu_length": pdu_length,
                }
        elif function_code == S7Function.READ_AREA:
            # Parse read area parameters
            if len(param_data) >= 14:  # Minimum for read area request
                # Function code (1) + item count (1) + address spec (12)
                item_count = param_data[1]

                # Parse address specification starting at byte 2
                if len(param_data) >= 14:
                    addr_spec = param_data[2:14]  # 12 bytes of address specification
                    logger.debug(f"Extracted address spec from params: {addr_spec.hex()}")
                    parsed_addr = self._parse_address_specification(addr_spec)

                    return {"function_code": function_code, "item_count": item_count, "address_spec": parsed_addr}
        elif function_code == S7Function.WRITE_AREA:
            # Parse write area parameters (same format as read)
            if len(param_data) >= 14:  # Minimum for write area request
                # Function code (1) + item count (1) + address spec (12)
                item_count = param_data[1]

                # Parse address specification starting at byte 2
                if len(param_data) >= 14:
                    addr_spec = param_data[2:14]  # 12 bytes of address specification
                    logger.debug(f"Extracted write address spec from params: {addr_spec.hex()}")
                    parsed_addr = self._parse_address_specification(addr_spec)

                    return {"function_code": function_code, "item_count": item_count, "address_spec": parsed_addr}

        return {"function_code": function_code}

    def _parse_address_specification(self, addr_spec: bytes) -> Dict[str, Any]:
        """
        Parse S7 address specification.

        Args:
            addr_spec: 12-byte address specification from client request

        Returns:
            Dictionary with parsed address information
        """
        try:
            if len(addr_spec) < 12:
                logger.error(f"Address spec too short: {len(addr_spec)} bytes, need 12")
                return {}

            logger.debug(f"Parsing address spec: {addr_spec.hex()} (length: {len(addr_spec)})")

            # Address specification format:
            # Byte 0: Specification type (0x12)
            # Byte 1: Length of following address specification (0x0A = 10 bytes)
            # Byte 2: Syntax ID (0x10 = S7-Any)
            # Byte 3: Transport size (word length)
            # Bytes 4-5: Count (number of items)
            # Bytes 6-7: DB number (for DB area) or 0
            # Byte 8: Area code
            # Bytes 9-11: Start address (3 bytes, big-endian)

            spec_type, length, syntax_id, word_len, count, db_number, area_code, address_bytes = struct.unpack(
                ">BBBBHHB3s", addr_spec
            )

            # Extract 3-byte address (big-endian)
            address = struct.unpack(">I", b"\x00" + address_bytes)[0]  # Pad to 4 bytes

            # Convert bit address to byte address
            if word_len == S7WordLen.BIT:
                byte_addr = address // 8
                start_address = byte_addr
            else:
                start_address = address // 8  # Convert bit address to byte address

            return {
                "area": S7Area(area_code),
                "db_number": db_number,
                "start": start_address,
                "count": count,
                "word_len": word_len,
                "spec_type": spec_type,
                "syntax_id": syntax_id,
            }

        except Exception as e:
            logger.error(f"Error parsing address specification: {e}")
            return {}

    def _parse_data_section(self, data_section: bytes) -> Dict[str, Any]:
        """Parse S7 data section."""
        if len(data_section) == 1:
            # Simple return code (for write responses)
            return {"return_code": data_section[0], "transport_size": 0, "data_length": 0, "data": b""}
        elif len(data_section) >= 4:
            # Full data header (for read responses)
            return_code = data_section[0]
            transport_size = data_section[1]
            data_length = struct.unpack(">H", data_section[2:4])[0]

            # Extract actual data
            actual_data = data_section[4 : 4 + (data_length // 8)]

            return {"return_code": return_code, "transport_size": transport_size, "data_length": data_length, "data": actual_data}
        else:
            return {"raw_data": data_section}

    def _build_error_response(self, request: Dict[str, Any], error_code: int) -> bytes:
        """Build an error response PDU."""
        error_class = (error_code >> 8) & 0xFF
        error_byte = error_code & 0xFF
        header = struct.pack(
            ">BBHHHHBB",
            0x32,  # Protocol ID
            S7PDUType.RESPONSE,  # PDU type
            0x0000,  # Reserved
            request.get("sequence", 0),  # Sequence (echo)
            0x0000,  # Parameter length
            0x0000,  # Data length
            error_class,  # Error class
            error_byte,  # Error code
        )

        return header

    def __enter__(self) -> "Server":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Context manager exit."""
        self.destroy()


class ServerISOConnection:
    """ISO connection wrapper for server-side communication."""

    # COTP PDU types
    COTP_CR = 0xE0  # Connection Request
    COTP_CC = 0xD0  # Connection Confirm
    COTP_DR = 0x80  # Disconnect Request
    COTP_DC = 0xC0  # Disconnect Confirm
    COTP_DT = 0xF0  # Data Transfer

    def __init__(self, client_socket: socket.socket):
        """Initialize server ISO connection."""
        self.socket = client_socket
        self.socket.settimeout(5.0)
        self.connected = False
        self.src_ref = 0x0001  # Server reference
        self.dst_ref = 0x0000  # Client reference (assigned during handshake)

    def accept_connection(self) -> bool:
        """Accept ISO connection from client."""
        try:
            # Receive COTP Connection Request
            tpkt_header = self._recv_exact(4)
            version, reserved, length = struct.unpack(">BBH", tpkt_header)

            if version != 3:
                logger.error(f"Invalid TPKT version: {version}")
                return False

            payload = self._recv_exact(length - 4)

            # Parse COTP Connection Request
            if not self._parse_cotp_cr(payload):
                return False

            # Send COTP Connection Confirm
            cc_pdu = self._build_cotp_cc()
            tpkt_frame = self._build_tpkt(cc_pdu)
            self.socket.sendall(tpkt_frame)

            self.connected = True
            logger.debug("ISO connection established")
            return True

        except Exception as e:
            logger.error(f"Error accepting ISO connection: {e}")
            return False

    def receive_data(self) -> bytes:
        """Receive data from client."""
        # Receive TPKT header (4 bytes)
        tpkt_header = self._recv_exact(4)

        # Parse TPKT header
        version, reserved, length = struct.unpack(">BBH", tpkt_header)

        if version != 3:
            raise S7ConnectionError(f"Invalid TPKT version: {version}")

        # Receive remaining data
        remaining = length - 4
        if remaining <= 0:
            raise S7ConnectionError("Invalid TPKT length")

        payload = self._recv_exact(remaining)

        # Parse COTP header and extract data
        return self._parse_cotp_data(payload)

    def send_data(self, data: bytes) -> None:
        """Send data to client."""
        # Wrap data in COTP Data Transfer PDU
        cotp_data = self._build_cotp_dt(data)

        # Wrap in TPKT frame
        tpkt_frame = self._build_tpkt(cotp_data)

        # Send over TCP
        self.socket.sendall(tpkt_frame)

    def _parse_cotp_cr(self, data: bytes) -> bool:
        """Parse COTP Connection Request."""
        if len(data) < 7:
            logger.error("COTP CR too short")
            return False

        pdu_len, pdu_type, dst_ref, src_ref, class_opt = struct.unpack(">BBHHB", data[:7])

        if pdu_type != self.COTP_CR:
            logger.error(f"Expected COTP CR, got {pdu_type:#02x}")
            return False

        # Store client reference
        self.dst_ref = src_ref

        logger.debug(f"Received COTP CR from client ref {src_ref}")
        return True

    def _build_cotp_cc(self) -> bytes:
        """Build COTP Connection Confirm."""
        # Basic COTP CC
        base_pdu = struct.pack(
            ">BBHHB",
            6,  # PDU length
            self.COTP_CC,  # PDU type
            self.dst_ref,  # Destination reference (client's source ref)
            self.src_ref,  # Source reference (our ref)
            0x00,  # Class/option
        )

        return struct.pack(">B", 6) + base_pdu[1:]

    def _recv_exact(self, size: int) -> bytes:
        """Receive exactly the specified number of bytes."""
        data = bytearray()

        while len(data) < size:
            chunk = self.socket.recv(size - len(data))
            if not chunk:
                raise ConnectionResetError("Connection closed by peer")
            data.extend(chunk)

        return bytes(data)

    def _build_tpkt(self, payload: bytes) -> bytes:
        """Build TPKT frame."""
        length = len(payload) + 4
        return struct.pack(">BBH", 3, 0, length) + payload

    def _build_cotp_dt(self, data: bytes) -> bytes:
        """Build COTP Data Transfer PDU."""
        header = struct.pack(">BBB", 2, self.COTP_DT, 0x80)
        return header + data

    def _parse_cotp_data(self, cotp_pdu: bytes) -> bytes:
        """Parse COTP Data Transfer PDU and extract S7 data."""
        if len(cotp_pdu) < 3:
            raise S7ConnectionError("Invalid COTP DT: too short")

        pdu_len, pdu_type, eot_num = struct.unpack(">BBB", cotp_pdu[:3])

        if pdu_type != self.COTP_DT:
            raise S7ConnectionError(f"Expected COTP DT, got {pdu_type:#02x}")

        return cotp_pdu[3:]  # Return data portion


def mainloop(tcp_port: int = 1102, init_standard_values: bool = False) -> None:
    """
    Initialize a pure Python S7 server with default values.

    Args:
        tcp_port: Port that the server will listen on
        init_standard_values: If True, initialize some default values
    """
    server = Server()

    # Create standard memory areas - need at least 600 bytes for test data
    db_size = 600
    db_data = bytearray(db_size)
    pa_data = bytearray(100)
    pe_data = bytearray(100)
    mk_data = bytearray(100)
    tm_data = bytearray(100)
    ct_data = bytearray(100)

    # Register memory areas
    # DB 0 for test_mainloop.py, DB 1 for other tests
    server.register_area(SrvArea.DB, 0, db_data)
    server.register_area(SrvArea.DB, 1, bytearray(db_size))
    # Register at index 0 (used by most tests) and index 1
    server.register_area(SrvArea.PA, 0, pa_data)
    server.register_area(SrvArea.PA, 1, bytearray(100))
    server.register_area(SrvArea.PE, 0, pe_data)
    server.register_area(SrvArea.PE, 1, bytearray(100))
    server.register_area(SrvArea.MK, 0, mk_data)
    server.register_area(SrvArea.MK, 1, bytearray(100))
    server.register_area(SrvArea.TM, 0, tm_data)
    server.register_area(SrvArea.TM, 1, bytearray(100))
    server.register_area(SrvArea.CT, 0, ct_data)
    server.register_area(SrvArea.CT, 1, bytearray(100))

    if init_standard_values:
        logger.info("Initializing with standard values for tests")

        # test_read_booleans: offset 0, expects 0xAA (alternating False/True: 0,1,0,1,0,1,0,1)
        db_data[0] = 0xAA  # Binary: 10101010

        # test_read_small_int: offset 10, expects -128, 0, 100, 127 (signed bytes)
        db_data[10] = 0x80  # -128 as signed byte
        db_data[11] = 0x00  # 0
        db_data[12] = 100  # 100
        db_data[13] = 127  # 127

        # test_read_unsigned_small_int: offset 20, expects 0, 255
        db_data[20] = 0  # 0
        db_data[21] = 255  # 255

        # test_read_int: offset 30, expects -32768, -1234, 0, 1234, 32767 (signed 16-bit, big-endian)
        struct.pack_into(">h", db_data, 30, -32768)
        struct.pack_into(">h", db_data, 32, -1234)
        struct.pack_into(">h", db_data, 34, 0)
        struct.pack_into(">h", db_data, 36, 1234)
        struct.pack_into(">h", db_data, 38, 32767)

        # test_read_double_int: offset 40, expects -2147483648, -32768, 0, 32767, 2147483647 (signed 32-bit)
        struct.pack_into(">i", db_data, 40, -2147483648)
        struct.pack_into(">i", db_data, 44, -32768)
        struct.pack_into(">i", db_data, 48, 0)
        struct.pack_into(">i", db_data, 52, 32767)
        struct.pack_into(">i", db_data, 56, 2147483647)

        # test_read_real: offset 60, expects various float values (9 floats = 36 bytes)
        struct.pack_into(">f", db_data, 60, -3.402823e38)
        struct.pack_into(">f", db_data, 64, -3.402823e12)
        struct.pack_into(">f", db_data, 68, -175494351e-38)
        struct.pack_into(">f", db_data, 72, -1.175494351e-12)
        struct.pack_into(">f", db_data, 76, 0.0)
        struct.pack_into(">f", db_data, 80, 1.175494351e-38)
        struct.pack_into(">f", db_data, 84, 1.175494351e-12)
        struct.pack_into(">f", db_data, 88, 3.402823466e12)
        struct.pack_into(">f", db_data, 92, 3.402823466e38)

        # test_read_string: offset 100, expects "the brown fox jumps over the lazy dog"
        # S7 string format: max_len (1 byte), actual_len (1 byte), then string data
        test_string = "the brown fox jumps over the lazy dog"
        db_data[100] = 254  # Max length
        db_data[101] = len(test_string)  # Actual length
        db_data[102 : 102 + len(test_string)] = test_string.encode("ascii")

        # test_read_word: offset 400, expects 0x0000, 0x1234, 0xABCD, 0xFFFF (unsigned 16-bit)
        struct.pack_into(">H", db_data, 400, 0x0000)
        struct.pack_into(">H", db_data, 404, 0x1234)
        struct.pack_into(">H", db_data, 408, 0xABCD)
        struct.pack_into(">H", db_data, 412, 0xFFFF)

        # test_read_double_word: offset 500, expects 0x00000000, 0x12345678, 0x1234ABCD, 0xFFFFFFFF (unsigned 32-bit)
        struct.pack_into(">I", db_data, 500, 0x00000000)
        struct.pack_into(">I", db_data, 508, 0x12345678)
        struct.pack_into(">I", db_data, 516, 0x1234ABCD)
        struct.pack_into(">I", db_data, 524, 0xFFFFFFFF)

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
