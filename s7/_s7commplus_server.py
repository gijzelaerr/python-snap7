"""
S7CommPlus server emulator for testing.

Emulates an S7-1200/1500 PLC for integration testing without real hardware.
Handles the S7CommPlus protocol including:
- COTP connection setup (reuses ISOTCPConnection transport)
- CreateObject session handshake
- Explore (browse registered data blocks and variables)
- GetMultiVariables / SetMultiVariables (read/write by address)
- Internal PLC memory model with thread-safe access
- V2 protocol emulation with TLS and IntegrityId tracking

Supports both V1 (no TLS) and V2 (TLS + IntegrityId) emulation.

Usage::

    server = S7CommPlusServer()
    server.register_db(1, {"temperature": ("Real", 0), "pressure": ("Real", 4)})
    server.start(port=11020)

    # V2 server with TLS:
    server = S7CommPlusServer(protocol_version=ProtocolVersion.V2)
    server.start(port=11020, use_tls=True, tls_cert="cert.pem", tls_key="key.pem")
"""

import logging
import socket
import ssl
import struct
import threading
from enum import IntEnum
from typing import Any, Callable, Optional

from .protocol import (
    DataType,
    ElementID,
    FunctionCode,
    Ids,
    Opcode,
    ProtocolVersion,
    READ_FUNCTION_CODES,
    SoftDataType,
)
from .vlq import encode_uint32_vlq, decode_uint32_vlq, encode_uint64_vlq
from .codec import (
    encode_header,
    decode_header,
    encode_typed_value,
    encode_pvalue_blob,
    decode_pvalue_to_bytes,
)

logger = logging.getLogger(__name__)


class CPUState(IntEnum):
    """Emulated CPU operational state."""

    UNKNOWN = 0
    STOP = 1
    RUN = 2


# Mapping from SoftDataType to wire DataType and byte size
_SOFT_TO_WIRE: dict[int, tuple[int, int]] = {
    SoftDataType.BOOL: (DataType.BOOL, 1),
    SoftDataType.BYTE: (DataType.BYTE, 1),
    SoftDataType.CHAR: (DataType.BYTE, 1),
    SoftDataType.WORD: (DataType.WORD, 2),
    SoftDataType.INT: (DataType.INT, 2),
    SoftDataType.DWORD: (DataType.DWORD, 4),
    SoftDataType.DINT: (DataType.DINT, 4),
    SoftDataType.REAL: (DataType.REAL, 4),
    SoftDataType.LREAL: (DataType.LREAL, 8),
    SoftDataType.USINT: (DataType.USINT, 1),
    SoftDataType.UINT: (DataType.UINT, 2),
    SoftDataType.UDINT: (DataType.UDINT, 4),
    SoftDataType.SINT: (DataType.SINT, 1),
    SoftDataType.ULINT: (DataType.ULINT, 8),
    SoftDataType.LINT: (DataType.LINT, 8),
    SoftDataType.LWORD: (DataType.LWORD, 8),
    SoftDataType.STRING: (DataType.S7STRING, 256),
    SoftDataType.WSTRING: (DataType.WSTRING, 512),
}

# Map string type names to SoftDataType values
_TYPE_NAME_MAP: dict[str, int] = {
    "Bool": SoftDataType.BOOL,
    "Byte": SoftDataType.BYTE,
    "Char": SoftDataType.CHAR,
    "Word": SoftDataType.WORD,
    "Int": SoftDataType.INT,
    "DWord": SoftDataType.DWORD,
    "DInt": SoftDataType.DINT,
    "Real": SoftDataType.REAL,
    "LReal": SoftDataType.LREAL,
    "USInt": SoftDataType.USINT,
    "UInt": SoftDataType.UINT,
    "UDInt": SoftDataType.UDINT,
    "SInt": SoftDataType.SINT,
    "ULInt": SoftDataType.ULINT,
    "LInt": SoftDataType.LINT,
    "LWord": SoftDataType.LWORD,
    "String": SoftDataType.STRING,
    "WString": SoftDataType.WSTRING,
}


class DBVariable:
    """A variable in a data block."""

    def __init__(self, name: str, soft_datatype: int, byte_offset: int):
        self.name = name
        self.soft_datatype = soft_datatype
        self.byte_offset = byte_offset

        wire_info = _SOFT_TO_WIRE.get(soft_datatype, (DataType.BYTE, 1))
        self.wire_datatype = wire_info[0]
        self.byte_size = wire_info[1]

    def __repr__(self) -> str:
        return f"DBVariable({self.name!r}, type={self.soft_datatype}, offset={self.byte_offset})"


class DataBlock:
    """An emulated PLC data block with named variables."""

    def __init__(self, number: int, size: int = 1024):
        self.number = number
        self.data = bytearray(size)
        self.variables: dict[str, DBVariable] = {}
        self.lock = threading.Lock()
        # Assign a unique object ID for the S7CommPlus object tree
        self.object_id = 0x00010000 | (number & 0xFFFF)

    def add_variable(self, name: str, type_name: str, byte_offset: int) -> None:
        """Register a named variable in this data block.

        Args:
            name: Variable name (e.g. "temperature")
            type_name: PLC type name (e.g. "Real", "Int", "Bool")
            byte_offset: Byte offset within the data block
        """
        soft_type = _TYPE_NAME_MAP.get(type_name)
        if soft_type is None:
            raise ValueError(f"Unknown type name: {type_name!r}")
        self.variables[name] = DBVariable(name, soft_type, byte_offset)

    def read(self, offset: int, size: int) -> bytes:
        """Read bytes from the data block."""
        with self.lock:
            end = min(offset + size, len(self.data))
            result = bytes(self.data[offset:end])
            # Pad with zeros if reading past end
            if len(result) < size:
                result += b"\x00" * (size - len(result))
            return result

    def write(self, offset: int, data: bytes) -> None:
        """Write bytes to the data block."""
        with self.lock:
            end = min(offset + len(data), len(self.data))
            self.data[offset:end] = data[: end - offset]

    def read_variable(self, name: str) -> tuple[int, bytes]:
        """Read a named variable.

        Returns:
            Tuple of (wire_datatype, raw_bytes)
        """
        var = self.variables.get(name)
        if var is None:
            raise KeyError(f"Variable not found: {name!r}")
        raw = self.read(var.byte_offset, var.byte_size)
        return var.wire_datatype, raw

    def write_variable(self, name: str, data: bytes) -> None:
        """Write a named variable."""
        var = self.variables.get(name)
        if var is None:
            raise KeyError(f"Variable not found: {name!r}")
        self.write(var.byte_offset, data)


class S7CommPlusServer:
    """S7CommPlus PLC emulator for testing.

    Emulates an S7-1200/1500 PLC with:
    - Internal data block storage with named variables
    - S7CommPlus protocol handling (V1 and V2)
    - V2 TLS support with IntegrityId tracking
    - Multi-client support (threaded)
    - CPU state management
    """

    def __init__(self, protocol_version: int = ProtocolVersion.V1) -> None:
        self._data_blocks: dict[int, DataBlock] = {}
        self._cpu_state = CPUState.RUN
        self._protocol_version = protocol_version
        self._next_session_id = 1

        self._server_socket: Optional[socket.socket] = None
        self._server_thread: Optional[threading.Thread] = None
        self._client_threads: list[threading.Thread] = []
        self._running = False
        self._lock = threading.Lock()
        self._event_callback: Optional[Callable[..., None]] = None

        # TLS configuration (V2)
        self._ssl_context: Optional[ssl.SSLContext] = None
        self._use_tls: bool = False

    @property
    def cpu_state(self) -> CPUState:
        return self._cpu_state

    @cpu_state.setter
    def cpu_state(self, state: CPUState) -> None:
        self._cpu_state = state

    def register_db(self, db_number: int, variables: dict[str, tuple[str, int]], size: int = 1024) -> DataBlock:
        """Register a data block with named variables.

        Args:
            db_number: Data block number (e.g. 1 for DB1)
            variables: Dict mapping variable name to (type_name, byte_offset)
                       e.g. {"temperature": ("Real", 0), "count": ("Int", 4)}
            size: Data block size in bytes

        Returns:
            The created DataBlock

        Example::

            server.register_db(1, {
                "temperature": ("Real", 0),
                "pressure": ("Real", 4),
                "running": ("Bool", 8),
                "count": ("DInt", 10),
            })
        """
        db = DataBlock(db_number, size)
        for name, (type_name, offset) in variables.items():
            db.add_variable(name, type_name, offset)
        self._data_blocks[db_number] = db
        return db

    def register_raw_db(self, db_number: int, data: bytearray) -> DataBlock:
        """Register a data block with raw data (no named variables).

        Args:
            db_number: Data block number
            data: Initial data block content

        Returns:
            The created DataBlock
        """
        db = DataBlock(db_number, len(data))
        db.data = data
        self._data_blocks[db_number] = db
        return db

    def get_db(self, db_number: int) -> Optional[DataBlock]:
        """Get a registered data block."""
        return self._data_blocks.get(db_number)

    def start(
        self,
        host: str = "0.0.0.0",
        port: int = 11020,
        use_tls: bool = False,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        tls_ca: Optional[str] = None,
    ) -> None:
        """Start the server.

        Args:
            host: Bind address
            port: TCP port to listen on
            use_tls: Whether to wrap client sockets with TLS after InitSSL
            tls_cert: Path to server TLS certificate (PEM)
            tls_key: Path to server private key (PEM)
            tls_ca: Path to CA certificate for client verification (PEM)
        """
        if self._running:
            raise RuntimeError("Server is already running")

        self._use_tls = use_tls
        if use_tls:
            if not tls_cert or not tls_key:
                raise ValueError("TLS requires tls_cert and tls_key")
            self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self._ssl_context.minimum_version = ssl.TLSVersion.TLSv1_3
            self._ssl_context.load_cert_chain(tls_cert, tls_key)
            if tls_ca:
                self._ssl_context.load_verify_locations(tls_ca)
                self._ssl_context.verify_mode = ssl.CERT_REQUIRED
            else:
                self._ssl_context.verify_mode = ssl.CERT_NONE

        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.settimeout(1.0)
        self._server_socket.bind((host, port))
        self._server_socket.listen(5)

        self._running = True
        self._server_thread = threading.Thread(target=self._server_loop, daemon=True, name="s7commplus-server")
        self._server_thread.start()
        logger.info(f"S7CommPlus server started on {host}:{port} (TLS={use_tls}, V{self._protocol_version})")

    def stop(self) -> None:
        """Stop the server."""
        self._running = False

        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None

        if self._server_thread:
            self._server_thread.join(timeout=5.0)
            self._server_thread = None

        for t in self._client_threads:
            t.join(timeout=2.0)
        self._client_threads.clear()

        logger.info("S7CommPlus server stopped")

    def _server_loop(self) -> None:
        """Main server accept loop."""
        while self._running:
            try:
                if self._server_socket is None:
                    break
                client_sock, address = self._server_socket.accept()
                client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                logger.info(f"Client connected from {address}")
                t = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, address),
                    daemon=True,
                    name=f"s7commplus-client-{address}",
                )
                self._client_threads.append(t)
                t.start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _handle_client(self, client_sock: socket.socket, address: tuple[str, int]) -> None:
        """Handle a single client connection."""
        try:
            client_sock.settimeout(5.0)

            # Step 1: COTP handshake
            if not self._handle_cotp_connect(client_sock):
                return

            # Step 2: S7CommPlus session
            session_id = 0
            tls_activated = False
            # Per-client IntegrityId tracking (V2+)
            integrity_id_read = 0
            integrity_id_write = 0

            while self._running:
                try:
                    # Receive TPKT + COTP DT + S7CommPlus data
                    data = self._recv_s7commplus_frame(client_sock)
                    if data is None:
                        break

                    # Process the S7CommPlus request
                    response = self._process_request(data, session_id, integrity_id_read, integrity_id_write)

                    if response is not None:
                        # Check if session ID was assigned
                        if session_id == 0 and len(response) >= 14:
                            session_id = struct.unpack_from(">I", response, 9)[0]

                        self._send_s7commplus_frame(client_sock, response)

                    # After InitSSL response, activate TLS if configured
                    if (
                        not tls_activated
                        and self._use_tls
                        and self._ssl_context is not None
                        and data is not None
                        and len(data) >= 8
                    ):
                        # Check if this was an InitSSL request
                        try:
                            _, _, hdr_consumed = decode_header(data)
                            payload = data[hdr_consumed:]
                            if len(payload) >= 14:
                                func_code = struct.unpack_from(">H", payload, 3)[0]
                                if func_code == FunctionCode.INIT_SSL:
                                    client_sock = self._ssl_context.wrap_socket(client_sock, server_side=True)
                                    tls_activated = True
                                    logger.debug(f"TLS activated for client {address}")
                        except (ValueError, struct.error):
                            pass

                    # Update IntegrityId counters based on function code (V2+)
                    if self._protocol_version >= ProtocolVersion.V2 and session_id != 0:
                        try:
                            _, _, hdr_consumed = decode_header(data)
                            payload = data[hdr_consumed:]
                            if len(payload) >= 14:
                                func_code = struct.unpack_from(">H", payload, 3)[0]
                                if func_code in READ_FUNCTION_CODES:
                                    integrity_id_read = (integrity_id_read + 1) & 0xFFFFFFFF
                                elif func_code not in (
                                    FunctionCode.INIT_SSL,
                                    FunctionCode.CREATE_OBJECT,
                                ):
                                    integrity_id_write = (integrity_id_write + 1) & 0xFFFFFFFF
                        except (ValueError, struct.error):
                            pass

                except socket.timeout:
                    continue
                except (ConnectionError, OSError):
                    break

        except Exception as e:
            logger.debug(f"Client handler error: {e}")
        finally:
            try:
                client_sock.close()
            except Exception:
                pass
            logger.info(f"Client disconnected: {address}")

    def _handle_cotp_connect(self, sock: socket.socket) -> bool:
        """Handle COTP Connection Request / Confirm."""
        try:
            # Receive TPKT header
            tpkt_header = self._recv_exact(sock, 4)
            version, _, length = struct.unpack(">BBH", tpkt_header)
            if version != 3:
                return False

            # Receive COTP CR
            payload = self._recv_exact(sock, length - 4)
            if len(payload) < 7:
                return False

            _pdu_len, pdu_type = payload[0], payload[1]
            if pdu_type != 0xE0:  # COTP CR
                return False

            # Parse source ref from CR
            src_ref = struct.unpack_from(">H", payload, 4)[0]

            # Build COTP CC response
            cc_pdu = struct.pack(
                ">BBHHB",
                6,  # PDU length
                0xD0,  # COTP CC
                src_ref,  # Destination ref (client's src ref)
                0x0001,  # Source ref (our ref)
                0x00,  # Class 0
            )

            # Add PDU size parameter
            pdu_size_param = struct.pack(">BBB", 0xC0, 1, 0x0A)  # 1024 bytes
            cc_pdu = struct.pack(">B", 6 + len(pdu_size_param)) + cc_pdu[1:] + pdu_size_param

            # Send TPKT + CC
            tpkt = struct.pack(">BBH", 3, 0, 4 + len(cc_pdu)) + cc_pdu
            sock.sendall(tpkt)

            logger.debug("COTP connection established")
            return True

        except Exception as e:
            logger.debug(f"COTP handshake failed: {e}")
            return False

    def _recv_s7commplus_frame(self, sock: socket.socket) -> Optional[bytes]:
        """Receive a TPKT/COTP/S7CommPlus frame, return the S7CommPlus payload."""
        try:
            # TPKT header
            tpkt_header = self._recv_exact(sock, 4)
            version, _, length = struct.unpack(">BBH", tpkt_header)
            if version != 3 or length <= 4:
                return None

            # Remaining data
            payload = self._recv_exact(sock, length - 4)

            # Skip COTP DT header (3 bytes: length, type 0xF0, EOT)
            if len(payload) < 3 or payload[1] != 0xF0:
                return None

            return payload[3:]  # S7CommPlus data

        except Exception:
            return None

    def _send_s7commplus_frame(self, sock: socket.socket, data: bytes) -> None:
        """Send an S7CommPlus frame wrapped in TPKT/COTP."""
        # S7CommPlus header (4 bytes) + data + trailer (4 bytes)
        s7plus_frame = encode_header(self._protocol_version, len(data)) + data
        s7plus_frame += struct.pack(">BBH", 0x72, self._protocol_version, 0x0000)

        # COTP DT header
        cotp_dt = struct.pack(">BBB", 2, 0xF0, 0x80) + s7plus_frame

        # TPKT
        tpkt = struct.pack(">BBH", 3, 0, 4 + len(cotp_dt)) + cotp_dt
        sock.sendall(tpkt)

    def _process_request(
        self,
        data: bytes,
        session_id: int,
        integrity_id_read: int = 0,
        integrity_id_write: int = 0,
    ) -> Optional[bytes]:
        """Process an S7CommPlus request and return a response."""
        if len(data) < 4:
            return None

        # Parse S7CommPlus frame header
        try:
            version, data_length, consumed = decode_header(data)
        except ValueError:
            return None

        # Use data_length to exclude any trailer
        payload = data[consumed : consumed + data_length]
        if len(payload) < 14:
            return None

        # Parse request header
        opcode = payload[0]
        if opcode != Opcode.REQUEST:
            return None

        function_code = struct.unpack_from(">H", payload, 3)[0]
        seq_num = struct.unpack_from(">H", payload, 7)[0]
        req_session_id = struct.unpack_from(">I", payload, 9)[0]

        # For V2+, skip IntegrityId after the 14-byte header
        request_offset = 14
        if (
            self._protocol_version >= ProtocolVersion.V2
            and session_id != 0
            and function_code not in (FunctionCode.INIT_SSL, FunctionCode.CREATE_OBJECT)
        ):
            if request_offset < len(payload):
                _req_iid, iid_consumed = decode_uint32_vlq(payload, request_offset)
                request_offset += iid_consumed

        request_data = payload[request_offset:]

        if function_code == FunctionCode.INIT_SSL:
            return self._handle_init_ssl(seq_num)
        elif function_code == FunctionCode.CREATE_OBJECT:
            return self._handle_create_object(seq_num, request_data)
        elif function_code == FunctionCode.DELETE_OBJECT:
            return self._handle_delete_object(seq_num, req_session_id)
        elif function_code == FunctionCode.EXPLORE:
            return self._handle_explore(seq_num, req_session_id, request_data)
        elif function_code == FunctionCode.GET_MULTI_VARIABLES:
            return self._handle_get_multi_variables(seq_num, req_session_id, request_data)
        elif function_code == FunctionCode.SET_MULTI_VARIABLES:
            return self._handle_set_multi_variables(seq_num, req_session_id, request_data)
        else:
            return self._build_error_response(seq_num, req_session_id, function_code)

    def _build_response_header(
        self,
        function_code: int,
        seq_num: int,
        session_id: int,
        include_integrity_id: bool = False,
        integrity_id: int = 0,
    ) -> bytes:
        """Build a 14-byte response header, optionally with IntegrityId (V2+).

        Args:
            function_code: Response function code
            seq_num: Sequence number echoed from request
            session_id: Session ID
            include_integrity_id: If True, append VLQ IntegrityId after header
            integrity_id: IntegrityId value to include

        Returns:
            Response header bytes (14 bytes, or 14+VLQ for V2+)
        """
        header = struct.pack(
            ">BHHHHIB",
            Opcode.RESPONSE,
            0x0000,
            function_code,
            0x0000,
            seq_num,
            session_id,
            0x00,
        )
        if include_integrity_id:
            header += encode_uint32_vlq(integrity_id)
        return header

    def _handle_init_ssl(self, seq_num: int) -> bytes:
        """Handle InitSSL -- respond to SSL initialization (V1 emulation, no real TLS)."""
        response = bytearray()
        response += struct.pack(
            ">BHHHHIB",
            Opcode.RESPONSE,
            0x0000,
            FunctionCode.INIT_SSL,
            0x0000,
            seq_num,
            0x00000000,
            0x00,  # Transport flags
        )
        response += encode_uint32_vlq(0)  # Return code: success
        response += struct.pack(">I", 0)
        return bytes(response)

    def _handle_create_object(self, seq_num: int, request_data: bytes) -> bytes:
        """Handle CreateObject -- establish a session."""
        with self._lock:
            session_id = self._next_session_id
            self._next_session_id += 1

        # CreateObject response header is 10 bytes — there is no session_id
        # field; session IDs come from the ResponseSet body's ObjectIds list.
        # Reference: thomas-v2/S7CommPlusDriver CreateObjectResponse.Deserialize
        response = bytearray()

        response += struct.pack(
            ">BHHHHB",
            Opcode.RESPONSE,
            0x0000,  # Reserved
            FunctionCode.CREATE_OBJECT,
            0x0000,  # Reserved
            seq_num,
            0x00,  # Transport flags
        )

        # ResponseSet
        response += encode_uint32_vlq(0)  # ReturnValue
        response += bytes([1])  # ObjectIdCount
        response += encode_uint32_vlq(session_id)  # ObjectIds[0] = session id

        # Object with session info
        response += bytes([ElementID.START_OF_OBJECT])
        response += struct.pack(">I", 0x00000001)  # Relation ID
        response += encode_uint32_vlq(0x00000000)  # Class ID
        response += encode_uint32_vlq(0x00000000)  # Class flags
        response += encode_uint32_vlq(0x00000000)  # Attribute ID

        # Session ID attribute
        response += bytes([ElementID.ATTRIBUTE])
        response += encode_uint32_vlq(0x0131)  # ServerSession ID attribute
        response += encode_typed_value(DataType.UDINT, session_id)

        # Protocol version attribute
        response += bytes([ElementID.ATTRIBUTE])
        response += encode_uint32_vlq(0x0132)  # Protocol version attribute
        response += encode_typed_value(DataType.USINT, self._protocol_version)

        # ServerSessionVersion attribute (306) - required for session setup handshake
        from .protocol import ObjectId

        response += bytes([ElementID.ATTRIBUTE])
        response += encode_uint32_vlq(ObjectId.SERVER_SESSION_VERSION)
        response += bytes([0x00])  # flags
        response += encode_typed_value(DataType.UDINT, self._protocol_version)

        response += bytes([ElementID.TERMINATING_OBJECT])

        # Trailing zeros
        response += struct.pack(">I", 0)

        return bytes(response)

    def _handle_delete_object(self, seq_num: int, session_id: int) -> bytes:
        """Handle DeleteObject -- close a session."""
        response = bytearray()
        response += struct.pack(
            ">BHHHHIB",
            Opcode.RESPONSE,
            0x0000,
            FunctionCode.DELETE_OBJECT,
            0x0000,
            seq_num,
            session_id,
            0x00,
        )
        response += encode_uint32_vlq(0)  # Return code: success
        response += struct.pack(">I", 0)
        return bytes(response)

    def _handle_explore(self, seq_num: int, session_id: int, request_data: bytes) -> bytes:
        """Handle Explore -- return the object tree (registered data blocks)."""
        response = bytearray()
        response += struct.pack(
            ">BHHHHIB",
            Opcode.RESPONSE,
            0x0000,
            FunctionCode.EXPLORE,
            0x0000,
            seq_num,
            session_id,
            0x00,
        )
        response += encode_uint32_vlq(0)  # Return code: success

        # Return list of data blocks as objects using standard S7CommPlus IDs
        for db_num, db in sorted(self._data_blocks.items()):
            response += bytes([ElementID.START_OF_OBJECT])
            response += struct.pack(">I", db.object_id)  # Relation ID
            response += encode_uint32_vlq(0x00000100)  # Class: DataBlock
            response += encode_uint32_vlq(0x00000000)  # Class flags
            response += encode_uint32_vlq(0x00000000)  # Attribute ID

            # ObjectVariableTypeName (233) -- DB name as WSTRING
            response += bytes([ElementID.ATTRIBUTE])
            response += encode_uint32_vlq(Ids.OBJECT_VARIABLE_TYPE_NAME)
            name_bytes = f"DB{db_num}".encode("utf-16-be")
            response += bytes([0x00, DataType.WSTRING])
            response += encode_uint32_vlq(len(name_bytes))
            response += name_bytes

            # Block_BlockNumber (2521) -- DB number as UDINT
            response += bytes([ElementID.ATTRIBUTE])
            response += encode_uint32_vlq(Ids.BLOCK_BLOCK_NUMBER)
            response += bytes([0x00, DataType.UDINT])
            response += encode_uint32_vlq(db_num)

            # DB size attribute (non-standard, for backward compat)
            response += bytes([ElementID.ATTRIBUTE])
            response += encode_uint32_vlq(0x0002)
            response += bytes([0x00, DataType.UDINT])
            response += encode_uint32_vlq(len(db.data))

            # Variable list -- used by browse to resolve field names
            if db.variables:
                for var_name, var in db.variables.items():
                    response += bytes([ElementID.START_OF_OBJECT])
                    response += struct.pack(">I", 0)  # child RID
                    response += encode_uint32_vlq(0)
                    response += encode_uint32_vlq(0)
                    response += encode_uint32_vlq(0)

                    response += bytes([ElementID.ATTRIBUTE])
                    response += encode_uint32_vlq(Ids.OBJECT_VARIABLE_TYPE_NAME)
                    vname_bytes = var_name.encode("utf-16-be")
                    response += bytes([0x00, DataType.WSTRING])
                    response += encode_uint32_vlq(len(vname_bytes))
                    response += vname_bytes

                    response += bytes([ElementID.TERMINATING_OBJECT])

            response += bytes([ElementID.TERMINATING_OBJECT])

        # Final terminator
        response += struct.pack(">I", 0)
        return bytes(response)

    def _handle_get_multi_variables(self, seq_num: int, session_id: int, request_data: bytes) -> bytes:
        """Handle GetMultiVariables -- read variables from data blocks.

        Parses the S7CommPlus request format with ItemAddress structures.
        The server extracts db_number from AccessArea and byte offset/size
        from the LID values.

        Reference: thomas-v2/S7CommPlusDriver/Core/GetMultiVariablesRequest.cs
        """
        response = bytearray()
        response += struct.pack(
            ">BHHHHIB",
            Opcode.RESPONSE,
            0x0000,
            FunctionCode.GET_MULTI_VARIABLES,
            0x0000,
            seq_num,
            session_id,
            0x00,
        )

        # Parse request payload
        items = _server_parse_read_request(request_data)

        # ReturnValue: success
        response += encode_uint64_vlq(0)

        # Value list: ItemNumber (1-based) + PValue, terminated by ItemNumber=0
        for i, (db_num, byte_offset, byte_size) in enumerate(items, 1):
            db = self._data_blocks.get(db_num)
            if db is not None:
                data = db.read(byte_offset, byte_size)
                response += encode_uint32_vlq(i)  # ItemNumber
                response += encode_pvalue_blob(data)  # Value as BLOB
            # Errors handled in error list below

        # Terminate value list
        response += encode_uint32_vlq(0)

        # Error list
        for i, (db_num, byte_offset, byte_size) in enumerate(items, 1):
            db = self._data_blocks.get(db_num)
            if db is None:
                response += encode_uint32_vlq(i)  # ErrorItemNumber
                response += encode_uint64_vlq(0x8104)  # Error: object not found

        # Terminate error list
        response += encode_uint32_vlq(0)

        # IntegrityId
        response += encode_uint32_vlq(0)

        return bytes(response)

    def _handle_set_multi_variables(self, seq_num: int, session_id: int, request_data: bytes) -> bytes:
        """Handle SetMultiVariables -- write variables to data blocks.

        Reference: thomas-v2/S7CommPlusDriver/Core/SetMultiVariablesRequest.cs
        """
        response = bytearray()
        response += struct.pack(
            ">BHHHHIB",
            Opcode.RESPONSE,
            0x0000,
            FunctionCode.SET_MULTI_VARIABLES,
            0x0000,
            seq_num,
            session_id,
            0x00,
        )

        # Parse request payload
        items, values = _server_parse_write_request(request_data)

        # Write data
        errors: list[tuple[int, int]] = []
        for i, ((db_num, byte_offset, _), data) in enumerate(zip(items, values), 1):
            db = self._data_blocks.get(db_num)
            if db is not None:
                db.write(byte_offset, data)
            else:
                errors.append((i, 0x8104))  # Object not found

        # ReturnValue: success
        response += encode_uint64_vlq(0)

        # Error list
        for err_item, err_code in errors:
            response += encode_uint32_vlq(err_item)
            response += encode_uint64_vlq(err_code)

        # Terminate error list
        response += encode_uint32_vlq(0)

        # IntegrityId
        response += encode_uint32_vlq(0)

        return bytes(response)

    def _build_error_response(self, seq_num: int, session_id: int, function_code: int) -> bytes:
        """Build a generic error response for unsupported function codes."""
        response = bytearray()
        response += struct.pack(
            ">BHHHHIB",
            Opcode.RESPONSE,
            0x0000,
            FunctionCode.ERROR,
            0x0000,
            seq_num,
            session_id,
            0x00,
        )
        response += encode_uint32_vlq(0x04B1)  # Error function code
        response += struct.pack(">I", 0)
        return bytes(response)

    @staticmethod
    def _recv_exact(sock: socket.socket, size: int) -> bytes:
        """Receive exactly the specified number of bytes."""
        data = bytearray()
        while len(data) < size:
            chunk = sock.recv(size - len(data))
            if not chunk:
                raise ConnectionError("Connection closed")
            data.extend(chunk)
        return bytes(data)

    def __enter__(self) -> "S7CommPlusServer":
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()


# -- Server-side request parsers --


def _server_parse_read_request(request_data: bytes) -> list[tuple[int, int, int]]:
    """Parse a GetMultiVariables request payload on the server side.

    Extracts (db_number, byte_offset, byte_size) for each item from the
    S7CommPlus ItemAddress format.

    Returns:
        List of (db_number, byte_offset, byte_size) tuples
    """
    if not request_data:
        return []

    offset = 0
    items: list[tuple[int, int, int]] = []

    # LinkId (UInt32 fixed)
    if offset + 4 > len(request_data):
        return []
    offset += 4

    # ItemCount (VLQ)
    item_count, consumed = decode_uint32_vlq(request_data, offset)
    offset += consumed

    # FieldCount (VLQ)
    _field_count, consumed = decode_uint32_vlq(request_data, offset)
    offset += consumed

    # Parse each ItemAddress
    for _ in range(item_count):
        if offset >= len(request_data):
            break

        # SymbolCrc
        _symbol_crc, consumed = decode_uint32_vlq(request_data, offset)
        offset += consumed

        # AccessArea
        access_area, consumed = decode_uint32_vlq(request_data, offset)
        offset += consumed

        # NumberOfLIDs
        num_lids, consumed = decode_uint32_vlq(request_data, offset)
        offset += consumed

        # AccessSubArea (first LID)
        _access_sub_area, consumed = decode_uint32_vlq(request_data, offset)
        offset += consumed

        # Additional LIDs
        lids: list[int] = []
        for _ in range(num_lids - 1):  # -1 because AccessSubArea counts as one
            if offset >= len(request_data):
                break
            lid_val, consumed = decode_uint32_vlq(request_data, offset)
            offset += consumed
            lids.append(lid_val)

        # Extract db_number from AccessArea
        db_num = access_area & 0xFFFF

        # Extract byte offset and size from LIDs (LID offsets are 1-based)
        byte_offset = (lids[0] - 1) if len(lids) > 0 else 0
        byte_size = lids[1] if len(lids) > 1 else 1

        items.append((db_num, byte_offset, byte_size))

    return items


def _server_parse_write_request(request_data: bytes) -> tuple[list[tuple[int, int, int]], list[bytes]]:
    """Parse a SetMultiVariables request payload on the server side.

    Returns:
        Tuple of (items, values) where items is list of (db_number, byte_offset, byte_size)
        and values is list of raw bytes to write
    """
    if not request_data:
        return [], []

    offset = 0

    # InObjectId (UInt32 fixed)
    if offset + 4 > len(request_data):
        return [], []
    offset += 4

    # ItemCount (VLQ)
    item_count, consumed = decode_uint32_vlq(request_data, offset)
    offset += consumed

    # FieldCount (VLQ)
    _field_count, consumed = decode_uint32_vlq(request_data, offset)
    offset += consumed

    # Parse each ItemAddress
    items: list[tuple[int, int, int]] = []
    for _ in range(item_count):
        if offset >= len(request_data):
            break

        # SymbolCrc
        _symbol_crc, consumed = decode_uint32_vlq(request_data, offset)
        offset += consumed

        # AccessArea
        access_area, consumed = decode_uint32_vlq(request_data, offset)
        offset += consumed

        # NumberOfLIDs
        num_lids, consumed = decode_uint32_vlq(request_data, offset)
        offset += consumed

        # AccessSubArea
        _access_sub_area, consumed = decode_uint32_vlq(request_data, offset)
        offset += consumed

        # Additional LIDs
        lids: list[int] = []
        for _ in range(num_lids - 1):
            if offset >= len(request_data):
                break
            lid_val, consumed = decode_uint32_vlq(request_data, offset)
            offset += consumed
            lids.append(lid_val)

        db_num = access_area & 0xFFFF
        byte_offset = (lids[0] - 1) if len(lids) > 0 else 0  # LID offsets are 1-based
        byte_size = lids[1] if len(lids) > 1 else 1
        items.append((db_num, byte_offset, byte_size))

    # Parse value list: ItemNumber (VLQ, 1-based) + PValue
    values: list[bytes] = []
    for _ in range(item_count):
        if offset >= len(request_data):
            break
        item_nr, consumed = decode_uint32_vlq(request_data, offset)
        offset += consumed
        if item_nr == 0:
            break
        raw_bytes, consumed = decode_pvalue_to_bytes(request_data, offset)
        offset += consumed
        values.append(raw_bytes)

    return items, values
