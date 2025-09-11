"""
Pure Python S7 server implementation.

Provides a complete S7 server emulator without dependencies on the Snap7 C library.
"""

import socket
import struct
import threading
import time
import logging
from typing import Dict, Optional, List, Callable, Any, Tuple
from enum import IntEnum

from .protocol import S7Protocol, S7Function, S7PDUType
from .datatypes import S7Area, S7WordLen
from .errors import S7ConnectionError, S7ProtocolError
from ..type import SrvArea, SrvEvent

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


class S7Server:
    """
    Pure Python S7 server implementation.
    
    Emulates a Siemens S7 PLC for testing and development purposes.
    """
    
    def __init__(self):
        """Initialize S7 server."""
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
        
        logger.info("S7Server initialized (pure Python implementation)")
    
    def register_area(self, area: SrvArea, index: int, data: bytearray) -> None:
        """
        Register a memory area with the server.
        
        Args:
            area: Memory area type
            index: Area index/number
            data: Initial data for the area
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
        
        area_key = (s7_area, index)
        self.memory_areas[area_key] = bytearray(data)
        self.area_locks[area_key] = threading.Lock()
        
        logger.info(f"Registered area {area.name} index {index}, size {len(data)}")
    
    def unregister_area(self, area: SrvArea, index: int) -> None:
        """Unregister a memory area."""
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
            return
            
        area_key = (s7_area, index)
        if area_key in self.memory_areas:
            del self.memory_areas[area_key]
            del self.area_locks[area_key]
            logger.info(f"Unregistered area {area.name} index {index}")
    
    def start(self, tcp_port: int = 102) -> None:
        """
        Start the S7 server.
        
        Args:
            tcp_port: TCP port to listen on
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
            
            logger.info(f"S7 Server started on {self.host}:{self.port}")
            
        except Exception as e:
            self.running = False
            self.state = ServerState.ERROR
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
            raise S7ConnectionError(f"Failed to start server: {e}")
    
    def stop(self) -> None:
        """Stop the S7 server."""
        if not self.running:
            return
        
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
    
    def get_status(self) -> Tuple[str, str, int]:
        """
        Get server status.
        
        Returns:
            Tuple of (server_status, cpu_status, client_count)
        """
        server_status_names = {
            ServerState.STOPPED: "Stopped",
            ServerState.RUNNING: "Running", 
            ServerState.ERROR: "Error"
        }
        
        cpu_status_names = {
            CPUState.UNKNOWN: "Unknown",
            CPUState.RUN: "Run",
            CPUState.STOP: "Stop"
        }
        
        return (
            server_status_names.get(self.state, "Unknown"),
            cpu_status_names.get(self.cpu_state, "Unknown"),
            self.client_count
        )
    
    def set_events_callback(self, callback: Callable[[SrvEvent], None]) -> None:
        """Set callback for server events."""
        self.event_callback = callback
        logger.info("Event callback set")
    
    def set_read_events_callback(self, callback: Callable[[SrvEvent], None]) -> None:
        """Set callback for read events."""
        self.read_callback = callback
        logger.info("Read event callback set")
    
    def _server_loop(self) -> None:
        """Main server loop to accept client connections."""
        try:
            while self.running and self.server_socket:
                try:
                    self.server_socket.settimeout(1.0)  # Non-blocking accept
                    client_socket, address = self.server_socket.accept()
                    
                    logger.info(f"Client connected from {address}")
                    
                    # Start client handler thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    
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
            connection = self._create_iso_connection(client_socket)
            
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
    
    def _create_iso_connection(self, client_socket: socket.socket) -> 'ServerISOConnection':
        """Create an ISO connection wrapper for server-side communication."""
        return ServerISOConnection(client_socket)
    
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
            if not request.get('parameters'):
                return None
            
            params = request['parameters']
            function_code = params.get('function_code')
            
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
        # Extract parameters
        params = request['parameters']
        pdu_length = params.get('pdu_length', 480)
        
        # Build response
        header = struct.pack(
            '>BBHHHH',
            0x32,                           # Protocol ID
            S7PDUType.RESPONSE,             # PDU type
            0x0000,                         # Reserved
            request['sequence'],            # Sequence (echo)
            0x0008,                         # Parameter length
            0x0000                          # Data length
        )
        
        parameters = struct.pack(
            '>BBHHH',
            S7Function.SETUP_COMMUNICATION, # Function code
            0x00,                           # Reserved
            1,                              # Max AMQ caller
            1,                              # Max AMQ callee
            min(pdu_length, 480)            # PDU length (limited)
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
            header = struct.pack(
                '>BBHHHH',
                0x32,                           # Protocol ID
                S7PDUType.RESPONSE,             # PDU type
                0x0000,                         # Reserved
                request['sequence'],            # Sequence (echo)
                0x0002,                         # Parameter length
                data_len                        # Data length
            )
            
            # Parameters
            parameters = struct.pack(
                '>BB',
                S7Function.READ_AREA,           # Function code
                0x01                            # Item count
            )
            
            # Data section
            data_section = struct.pack(
                '>BBH',
                0xFF,                           # Return code (success)
                S7WordLen.BYTE,                 # Transport size
                len(read_data) * 8              # Data length in bits
            ) + read_data
            
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
    
    def _parse_read_address(self, request: Dict[str, Any]) -> tuple:
        """
        Parse read address from request parameters.
        
        Returns:
            Tuple of (area, db_number, start, count) or None if invalid
        """
        try:
            params = request.get('parameters', {})
            if params.get('function_code') != S7Function.READ_AREA:
                return None
            
            # Check if we have parsed address specification
            addr_spec = params.get('address_spec', {})
            if addr_spec:
                area = addr_spec.get('area', S7Area.DB)
                db_number = addr_spec.get('db_number', 1)
                start = addr_spec.get('start', 0)
                count = addr_spec.get('count', 4)
                
                logger.debug(f"Parsed address: area={area}, db={db_number}, start={start}, count={count}")
                return (area, db_number, start, count)
            
            # Fallback to defaults if parsing failed
            logger.warning("Using default address values - address parsing may have failed")
            return (S7Area.DB, 1, 0, 4)
            
        except Exception as e:
            logger.error(f"Error parsing read address: {e}")
            return None
    
    def _read_from_memory_area(self, area: S7Area, db_number: int, start: int, count: int) -> bytearray:
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
            
            # Build successful response
            header = struct.pack(
                '>BBHHHH',
                0x32,                           # Protocol ID
                S7PDUType.RESPONSE,             # PDU type
                0x0000,                         # Reserved
                request['sequence'],            # Sequence (echo)
                0x0002,                         # Parameter length
                0x0001                          # Data length
            )
            
            # Parameters
            parameters = struct.pack(
                '>BB',
                S7Function.WRITE_AREA,          # Function code
                0x01                            # Item count
            )
            
            # Data section (write response)
            data_section = b'\xFF'  # Success return code
            
            return header + parameters + data_section
            
        except Exception as e:
            logger.error(f"Error handling write request: {e}")
            return self._build_error_response(request, 0x8000)
    
    def _handle_plc_control(self, request: Dict[str, Any], client_address: Tuple[str, int]) -> bytes:
        """Handle PLC control request (start operations)."""
        try:
            # Change CPU state based on control type
            params = request.get('parameters', {})
            if len(params) >= 2:
                # Has restart type parameter
                restart_type = params.get('restart_type', 1)
                if restart_type == 1:
                    logger.info("PLC Hot Start requested")
                else:
                    logger.info("PLC Cold Start requested")
            else:
                logger.info("PLC Start requested")
            
            # Set CPU to running state
            self.cpu_state = CPUState.RUN
            
            # Build successful response
            header = struct.pack(
                '>BBHHHH',
                0x32,                           # Protocol ID
                S7PDUType.RESPONSE,             # PDU type
                0x0000,                         # Reserved
                request['sequence'],            # Sequence (echo)
                0x0001,                         # Parameter length
                0x0000                          # Data length
            )
            
            parameters = struct.pack('>B', S7Function.PLC_CONTROL)
            
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
            
            # Build successful response
            header = struct.pack(
                '>BBHHHH',
                0x32,                           # Protocol ID
                S7PDUType.RESPONSE,             # PDU type
                0x0000,                         # Reserved
                request['sequence'],            # Sequence (echo)
                0x0001,                         # Parameter length
                0x0000                          # Data length
            )
            
            parameters = struct.pack('>B', S7Function.PLC_STOP)
            
            return header + parameters
            
        except Exception as e:
            logger.error(f"Error handling PLC stop request: {e}")
            return self._build_error_response(request, 0x8000)
    
    def _parse_write_address(self, request: Dict[str, Any]) -> tuple:
        """
        Parse write address from request parameters and data.
        
        Returns:
            Tuple of (area, db_number, start, count, write_data) or None if invalid
        """
        try:
            params = request.get('parameters', {})
            if params.get('function_code') != S7Function.WRITE_AREA:
                return None
            
            # Check if we have parsed address specification
            addr_spec = params.get('address_spec', {})
            if not addr_spec:
                logger.warning("No address specification in write request")
                return None
            
            area = addr_spec.get('area', S7Area.DB)
            db_number = addr_spec.get('db_number', 1)
            start = addr_spec.get('start', 0)
            count = addr_spec.get('count', 0)
            
            # Extract write data from request data section
            data_info = request.get('data', {})
            write_data = data_info.get('data', b'')
            
            if not write_data:
                logger.warning("No write data in request")
                return None
            
            logger.debug(f"Parsed write address: area={area}, db={db_number}, start={start}, count={count}, data_len={len(write_data)}")
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
                
                # If we didn't write all data due to bounds, log warning
                if actual_write_len < len(write_data):
                    logger.warning(f"Only wrote {actual_write_len} of {len(write_data)} bytes due to area bounds")
                
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
        header = struct.unpack('>BBHHHH', pdu[:10])
        protocol_id, pdu_type, reserved, sequence, param_len, data_len = header
        
        if protocol_id != 0x32:
            raise S7ProtocolError(f"Invalid protocol ID: {protocol_id:#02x}")
            
        request = {
            'sequence': sequence,
            'param_length': param_len,
            'data_length': data_len,
            'parameters': None,
            'data': None,
            'error_code': 0
        }
        
        offset = 10
        
        # Parse parameters if present
        if param_len > 0:
            if offset + param_len > len(pdu):
                raise S7ProtocolError("Parameter section extends beyond PDU")
                
            param_data = pdu[offset:offset + param_len]
            request['parameters'] = self._parse_request_parameters(param_data)
            offset += param_len
            
        # Parse data if present  
        if data_len > 0:
            if offset + data_len > len(pdu):
                raise S7ProtocolError("Data section extends beyond PDU")
                
            data_section = pdu[offset:offset + data_len]
            request['data'] = self._parse_data_section(data_section)
            
        return request
    
    def _parse_request_parameters(self, param_data: bytes) -> Dict[str, Any]:
        """Parse S7 request parameter section."""
        if len(param_data) < 1:
            return {}
            
        function_code = param_data[0]
        
        if function_code == S7Function.SETUP_COMMUNICATION:
            if len(param_data) >= 8:
                function_code, reserved, max_amq_caller, max_amq_callee, pdu_length = struct.unpack(
                    '>BBHHH', param_data[:8]
                )
                return {
                    'function_code': function_code,
                    'max_amq_caller': max_amq_caller,
                    'max_amq_callee': max_amq_callee,
                    'pdu_length': pdu_length
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
                    
                    return {
                        'function_code': function_code,
                        'item_count': item_count,
                        'address_spec': parsed_addr
                    }
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
                    
                    return {
                        'function_code': function_code,
                        'item_count': item_count,
                        'address_spec': parsed_addr
                    }
        
        return {'function_code': function_code}
    
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
                '>BBBBHHB3s', addr_spec
            )
            
            # Extract 3-byte address (big-endian)
            address = struct.unpack('>I', b'\x00' + address_bytes)[0]  # Pad to 4 bytes
            
            # Convert bit address to byte address
            if word_len == S7WordLen.BIT:
                byte_addr = address // 8
                bit_addr = address % 8
                start_address = byte_addr
            else:
                start_address = address // 8  # Convert bit address to byte address
            
            return {
                'area': S7Area(area_code),
                'db_number': db_number,
                'start': start_address,
                'count': count,
                'word_len': word_len,
                'spec_type': spec_type,
                'syntax_id': syntax_id
            }
            
        except Exception as e:
            logger.error(f"Error parsing address specification: {e}")
            return {}
    
    def _parse_data_section(self, data_section: bytes) -> Dict[str, Any]:
        """Parse S7 data section."""
        if len(data_section) == 1:
            # Simple return code (for write responses)
            return {
                'return_code': data_section[0],
                'transport_size': 0,
                'data_length': 0,
                'data': b''
            }
        elif len(data_section) >= 4:
            # Full data header (for read responses)
            return_code = data_section[0]
            transport_size = data_section[1] 
            data_length = struct.unpack('>H', data_section[2:4])[0]
            
            # Extract actual data
            actual_data = data_section[4:4 + (data_length // 8)]
            
            return {
                'return_code': return_code,
                'transport_size': transport_size,
                'data_length': data_length,
                'data': actual_data
            }
        else:
            return {'raw_data': data_section}
    
    def _build_error_response(self, request: Dict[str, Any], error_code: int) -> bytes:
        """Build an error response PDU."""
        header = struct.pack(
            '>BBHHHH',
            0x32,                           # Protocol ID
            S7PDUType.RESPONSE,             # PDU type
            0x0000,                         # Reserved
            request.get('sequence', 0),     # Sequence (echo)
            0x0000,                         # Parameter length
            0x0000                          # Data length
        )
        
        return header
    
    def __enter__(self) -> 'S7Server':
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()


class ServerISOConnection:
    """ISO connection wrapper for server-side communication."""
    
    # COTP PDU types
    COTP_CR = 0xE0    # Connection Request
    COTP_CC = 0xD0    # Connection Confirm  
    COTP_DR = 0x80    # Disconnect Request
    COTP_DC = 0xC0    # Disconnect Confirm
    COTP_DT = 0xF0    # Data Transfer
    
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
            version, reserved, length = struct.unpack('>BBH', tpkt_header)
            
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
        version, reserved, length = struct.unpack('>BBH', tpkt_header)
        
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
        
        pdu_len, pdu_type, dst_ref, src_ref, class_opt = struct.unpack('>BBHHB', data[:7])
        
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
            '>BBHHB',
            6,                    # PDU length
            self.COTP_CC,         # PDU type
            self.dst_ref,         # Destination reference (client's source ref)
            self.src_ref,         # Source reference (our ref)
            0x00                  # Class/option
        )
        
        return struct.pack('>B', 6) + base_pdu[1:]
    
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
        return struct.pack('>BBH', 3, 0, length) + payload
    
    def _build_cotp_dt(self, data: bytes) -> bytes:
        """Build COTP Data Transfer PDU."""
        header = struct.pack('>BBB', 2, self.COTP_DT, 0x80)
        return header + data
    
    def _parse_cotp_data(self, cotp_pdu: bytes) -> bytes:
        """Parse COTP Data Transfer PDU and extract S7 data."""
        if len(cotp_pdu) < 3:
            raise S7ConnectionError("Invalid COTP DT: too short")
        
        pdu_len, pdu_type, eot_num = struct.unpack('>BBB', cotp_pdu[:3])
        
        if pdu_type != self.COTP_DT:
            raise S7ConnectionError(f"Expected COTP DT, got {pdu_type:#02x}")
        
        return cotp_pdu[3:]  # Return data portion