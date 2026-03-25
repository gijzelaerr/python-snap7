"""
Async S7CommPlus client for S7-1200/1500 PLCs.

Provides the same API as S7CommPlusClient but using asyncio for
non-blocking I/O. Uses asyncio.Lock for concurrent safety.

Supports all S7CommPlus protocol versions (V1/V2/V3/TLS). The protocol
version is auto-detected from the PLC's CreateObject response during
connection setup.

When a PLC does not support S7CommPlus data operations, the client
transparently falls back to the legacy S7 protocol for data block
read/write operations (using synchronous calls in an executor).

Example::

    async with S7CommPlusAsyncClient() as client:
        await client.connect("192.168.1.10")
        data = await client.db_read(1, 0, 4)
        await client.db_write(1, 0, struct.pack(">f", 23.5))
"""

import asyncio
import logging
import ssl
import struct
from typing import Any, Optional

from .protocol import (
    DataType,
    ElementID,
    FunctionCode,
    LegitimationId,
    ObjectId,
    Opcode,
    ProtocolVersion,
    READ_FUNCTION_CODES,
    S7COMMPLUS_LOCAL_TSAP,
    S7COMMPLUS_REMOTE_TSAP,
)
from .codec import encode_header, decode_header, encode_typed_value, encode_object_qualifier
from .vlq import encode_uint32_vlq, decode_uint32_vlq, decode_uint64_vlq
from .client import _build_read_payload, _parse_read_response, _build_write_payload, _parse_write_response
from .connection import _element_size

logger = logging.getLogger(__name__)

# COTP constants
_COTP_CR = 0xE0
_COTP_CC = 0xD0
_COTP_DT = 0xF0


class S7CommPlusAsyncClient:
    """Async S7CommPlus client for S7-1200/1500 PLCs.

    Supports V1, V2, and V3 protocols (including TLS).

    Uses asyncio for all I/O operations and asyncio.Lock for
    concurrent safety when shared between multiple coroutines.

    When the PLC does not support S7CommPlus data operations, the client
    automatically falls back to legacy S7 protocol for db_read/db_write.
    """

    def __init__(self) -> None:
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._session_id: int = 0
        self._sequence_number: int = 0
        self._protocol_version: int = 0
        self._connected = False
        self._lock = asyncio.Lock()
        self._legacy_client: Optional[Any] = None
        self._use_legacy_data: bool = False
        self._host: str = ""
        self._port: int = 102
        self._rack: int = 0
        self._slot: int = 1

        # V2+ IntegrityId tracking
        self._integrity_id_read: int = 0
        self._integrity_id_write: int = 0
        self._with_integrity_id: bool = False

        # TLS state
        self._tls_active: bool = False
        self._oms_secret: Optional[bytes] = None

        # Session setup
        self._server_session_version: Optional[int] = None

    @property
    def connected(self) -> bool:
        if self._use_legacy_data and self._legacy_client is not None:
            return bool(self._legacy_client.connected)
        return self._connected

    @property
    def protocol_version(self) -> int:
        return self._protocol_version

    @property
    def session_id(self) -> int:
        return self._session_id

    @property
    def using_legacy_fallback(self) -> bool:
        """Whether the client is using legacy S7 protocol for data operations."""
        return self._use_legacy_data

    @property
    def tls_active(self) -> bool:
        """Whether TLS encryption is active on this connection."""
        return self._tls_active

    async def connect(
        self,
        host: str,
        port: int = 102,
        rack: int = 0,
        slot: int = 1,
        use_tls: bool = False,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        tls_ca: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        """Connect to an S7-1200/1500 PLC.

        If the PLC does not support S7CommPlus data operations, a secondary
        legacy S7 connection is established transparently for data access.

        Args:
            host: PLC IP address or hostname
            port: TCP port (default 102)
            rack: PLC rack number
            slot: PLC slot number
            use_tls: Whether to activate TLS (required for V2/V3)
            tls_cert: Path to client TLS certificate (PEM)
            tls_key: Path to client private key (PEM)
            tls_ca: Path to CA certificate for PLC verification (PEM)
            password: PLC password for legitimation (V2+ with TLS)
        """
        self._host = host
        self._port = port
        self._rack = rack
        self._slot = slot

        # TCP connect
        self._reader, self._writer = await asyncio.open_connection(host, port)

        try:
            # COTP handshake with S7CommPlus TSAP values
            await self._cotp_connect(S7COMMPLUS_LOCAL_TSAP, S7COMMPLUS_REMOTE_TSAP)

            # InitSSL handshake
            await self._init_ssl()

            # TLS activation (between InitSSL and CreateObject)
            if use_tls:
                await self._activate_tls(tls_cert=tls_cert, tls_key=tls_key, tls_ca=tls_ca)

            # S7CommPlus session setup
            await self._create_session()

            # Echo ServerSessionVersion back to complete handshake
            if self._server_session_version is not None:
                await self._setup_session()
            else:
                logger.warning("PLC did not provide ServerSessionVersion - session setup incomplete")

            # Version-specific post-setup
            if self._protocol_version >= ProtocolVersion.V2:
                if not self._tls_active:
                    raise RuntimeError(
                        f"PLC reports V{self._protocol_version} protocol but TLS is not active. "
                        "V2/V3 requires TLS. Use use_tls=True."
                    )
                self._with_integrity_id = True
                self._integrity_id_read = 0
                self._integrity_id_write = 0
                logger.info(f"V{self._protocol_version} IntegrityId tracking enabled")

            self._connected = True
            logger.info(
                f"Async S7CommPlus connected to {host}:{port}, "
                f"version=V{self._protocol_version}, session={self._session_id}, "
                f"tls={self._tls_active}"
            )

            # Handle legitimation for password-protected PLCs
            if password is not None and self._tls_active:
                logger.info("Performing PLC legitimation (password authentication)")
                await self.authenticate(password)

            # Probe S7CommPlus data operations
            if not await self._probe_s7commplus_data():
                logger.info("S7CommPlus data operations not supported, falling back to legacy S7 protocol")
                await self._setup_legacy_fallback()

        except Exception:
            await self.disconnect()
            raise

    async def authenticate(self, password: str, username: str = "") -> None:
        """Perform PLC password authentication (legitimation).

        Must be called after connect() and before data operations on
        password-protected PLCs. Requires TLS to be active (V2+).

        Args:
            password: PLC password
            username: Username for new-style auth (optional)
        """
        if not self._connected:
            raise RuntimeError("Not connected")

        if not self._tls_active:
            raise RuntimeError("Legitimation requires TLS. Connect with use_tls=True.")

        # Step 1: Get challenge from PLC
        challenge = await self._get_legitimation_challenge()
        logger.info(f"Received legitimation challenge ({len(challenge)} bytes)")

        # Step 2: Build response (auto-detect legacy vs new)
        from .legitimation import build_legacy_response, build_new_response

        if username and self._oms_secret is not None:
            response_data = build_new_response(password, challenge, self._oms_secret, username)
            await self._send_legitimation_new(response_data)
        elif self._oms_secret is not None:
            try:
                response_data = build_new_response(password, challenge, self._oms_secret, "")
                await self._send_legitimation_new(response_data)
            except NotImplementedError:
                response_data = build_legacy_response(password, challenge)
                await self._send_legitimation_legacy(response_data)
        else:
            logger.info("OMS secret not available, using legacy legitimation")
            response_data = build_legacy_response(password, challenge)
            await self._send_legitimation_legacy(response_data)

        logger.info("PLC legitimation completed successfully")

    async def _get_legitimation_challenge(self) -> bytes:
        """Request legitimation challenge from PLC."""
        payload = bytearray()
        payload += struct.pack(">I", self._session_id)
        payload += encode_uint32_vlq(1)
        payload += encode_uint32_vlq(1)
        payload += encode_uint32_vlq(LegitimationId.SERVER_SESSION_REQUEST)
        payload += struct.pack(">I", 0)

        resp_payload = await self._send_request(FunctionCode.GET_VAR_SUBSTREAMED, bytes(payload))

        offset = 0
        return_value, consumed = decode_uint64_vlq(resp_payload, offset)
        offset += consumed

        if return_value != 0:
            raise RuntimeError(f"GetVarSubStreamed for challenge failed: return_value={return_value}")

        if offset + 2 > len(resp_payload):
            raise RuntimeError("Challenge response too short")

        _flags = resp_payload[offset]
        datatype = resp_payload[offset + 1]
        offset += 2

        if datatype == DataType.BLOB:
            length, consumed = decode_uint32_vlq(resp_payload, offset)
            offset += consumed
            return bytes(resp_payload[offset : offset + length])
        else:
            count, consumed = decode_uint32_vlq(resp_payload, offset)
            offset += consumed
            return bytes(resp_payload[offset : offset + count])

    async def _send_legitimation_new(self, encrypted_response: bytes) -> None:
        """Send new-style legitimation response (AES-256-CBC encrypted)."""
        payload = bytearray()
        payload += struct.pack(">I", self._session_id)
        payload += encode_uint32_vlq(1)
        payload += encode_uint32_vlq(LegitimationId.LEGITIMATE)
        payload += bytes([0x00, DataType.BLOB])
        payload += encode_uint32_vlq(len(encrypted_response))
        payload += encrypted_response
        payload += struct.pack(">I", 0)

        resp_payload = await self._send_request(FunctionCode.SET_VARIABLE, bytes(payload))

        if len(resp_payload) >= 1:
            return_value, _ = decode_uint64_vlq(resp_payload, 0)
            if return_value < 0:
                raise RuntimeError(f"Legitimation rejected by PLC: return_value={return_value}")

    async def _send_legitimation_legacy(self, response: bytes) -> None:
        """Send legacy legitimation response (SHA-1 XOR)."""
        payload = bytearray()
        payload += struct.pack(">I", self._session_id)
        payload += encode_uint32_vlq(1)
        payload += encode_uint32_vlq(LegitimationId.SERVER_SESSION_RESPONSE)
        payload += bytes([0x10, DataType.USINT])
        payload += encode_uint32_vlq(len(response))
        payload += response
        payload += struct.pack(">I", 0)

        resp_payload = await self._send_request(FunctionCode.SET_VARIABLE, bytes(payload))

        if len(resp_payload) >= 1:
            return_value, _ = decode_uint64_vlq(resp_payload, 0)
            if return_value < 0:
                raise RuntimeError(f"Legacy legitimation rejected by PLC: return_value={return_value}")

    async def _probe_s7commplus_data(self) -> bool:
        """Test if the PLC supports S7CommPlus data operations."""
        try:
            payload = struct.pack(">I", 0) + encode_uint32_vlq(0) + encode_uint32_vlq(0)
            payload += encode_object_qualifier()
            payload += struct.pack(">I", 0)

            response = await self._send_request(FunctionCode.GET_MULTI_VARIABLES, payload)
            if len(response) < 1:
                return False
            return_value, _ = decode_uint64_vlq(response, 0)
            if return_value != 0:
                logger.debug(f"S7CommPlus probe: PLC returned error {return_value}")
                return False
            return True
        except Exception as e:
            logger.debug(f"S7CommPlus probe failed: {e}")
            return False

    async def _setup_legacy_fallback(self) -> None:
        """Establish a secondary legacy S7 connection for data operations."""
        from ..client import Client

        loop = asyncio.get_event_loop()
        client = Client()
        await loop.run_in_executor(None, lambda: client.connect(self._host, self._rack, self._slot, self._port))
        self._legacy_client = client
        self._use_legacy_data = True
        logger.info(f"Legacy S7 fallback connected to {self._host}:{self._port}")

    async def disconnect(self) -> None:
        """Disconnect from PLC."""
        if self._legacy_client is not None:
            try:
                self._legacy_client.disconnect()
            except Exception:
                pass
            self._legacy_client = None
            self._use_legacy_data = False

        if self._connected and self._session_id:
            try:
                await self._delete_session()
            except Exception:
                pass

        self._connected = False
        self._session_id = 0
        self._sequence_number = 0
        self._protocol_version = 0
        self._with_integrity_id = False
        self._integrity_id_read = 0
        self._integrity_id_write = 0
        self._tls_active = False
        self._oms_secret = None
        self._server_session_version = None

        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

    async def db_read(self, db_number: int, start: int, size: int) -> bytes:
        """Read raw bytes from a data block.

        Args:
            db_number: Data block number
            start: Start byte offset
            size: Number of bytes to read

        Returns:
            Raw bytes read from the data block
        """
        if self._use_legacy_data and self._legacy_client is not None:
            client = self._legacy_client
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: client.db_read(db_number, start, size))
            return bytes(data)

        payload = _build_read_payload([(db_number, start, size)])
        response = await self._send_request(FunctionCode.GET_MULTI_VARIABLES, payload)

        results = _parse_read_response(response)
        if not results:
            raise RuntimeError("Read returned no data")
        if results[0] is None:
            raise RuntimeError("Read failed: PLC returned error for item")
        return results[0]

    async def db_write(self, db_number: int, start: int, data: bytes) -> None:
        """Write raw bytes to a data block.

        Args:
            db_number: Data block number
            start: Start byte offset
            data: Bytes to write
        """
        if self._use_legacy_data and self._legacy_client is not None:
            client = self._legacy_client
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: client.db_write(db_number, start, bytearray(data)))
            return

        payload = _build_write_payload([(db_number, start, data)])
        response = await self._send_request(FunctionCode.SET_MULTI_VARIABLES, payload)
        _parse_write_response(response)

    async def db_read_multi(self, items: list[tuple[int, int, int]]) -> list[bytes]:
        """Read multiple data block regions in a single request.

        Args:
            items: List of (db_number, start_offset, size) tuples

        Returns:
            List of raw bytes for each item
        """
        if self._use_legacy_data and self._legacy_client is not None:
            client = self._legacy_client
            loop = asyncio.get_event_loop()
            multi_results: list[bytes] = []
            for db_number, start, size in items:

                def _read(db: int = db_number, s: int = start, sz: int = size) -> bytearray:
                    return bytearray(client.db_read(db, s, sz))

                data = await loop.run_in_executor(None, _read)
                multi_results.append(bytes(data))
            return multi_results

        payload = _build_read_payload(items)
        response = await self._send_request(FunctionCode.GET_MULTI_VARIABLES, payload)

        parsed = _parse_read_response(response)
        return [r if r is not None else b"" for r in parsed]

    async def explore(self) -> bytes:
        """Browse the PLC object tree.

        Returns:
            Raw response payload
        """
        return await self._send_request(FunctionCode.EXPLORE, b"")

    # -- Internal methods --

    async def _send_request(self, function_code: int, payload: bytes) -> bytes:
        """Send an S7CommPlus request and receive the response.

        For V2+ with IntegrityId tracking, inserts IntegrityId after the
        14-byte request header and strips it from the response.
        """
        async with self._lock:
            if not self._connected or self._writer is None or self._reader is None:
                raise RuntimeError("Not connected")

            seq_num = self._next_sequence_number()

            request_header = struct.pack(
                ">BHHHHIB",
                Opcode.REQUEST,
                0x0000,
                function_code,
                0x0000,
                seq_num,
                self._session_id,
                0x36,
            )

            # For V2+ with IntegrityId, insert after header
            integrity_id_bytes = b""
            if self._with_integrity_id and self._protocol_version >= ProtocolVersion.V2:
                is_read = function_code in READ_FUNCTION_CODES
                integrity_id = self._integrity_id_read if is_read else self._integrity_id_write
                integrity_id_bytes = encode_uint32_vlq(integrity_id)

            request = request_header + integrity_id_bytes + payload

            frame = encode_header(self._protocol_version, len(request)) + request
            frame += struct.pack(">BBH", 0x72, self._protocol_version, 0x0000)
            await self._send_cotp_dt(frame)

            # Increment appropriate IntegrityId counter
            if self._with_integrity_id and self._protocol_version >= ProtocolVersion.V2:
                if function_code in READ_FUNCTION_CODES:
                    self._integrity_id_read = (self._integrity_id_read + 1) & 0xFFFFFFFF
                else:
                    self._integrity_id_write = (self._integrity_id_write + 1) & 0xFFFFFFFF

            response_data = await self._recv_cotp_dt()

            version, data_length, consumed = decode_header(response_data)
            response = response_data[consumed : consumed + data_length]

            if len(response) < 14:
                raise RuntimeError("Response too short")

            # For V2+, skip IntegrityId in response
            resp_offset = 14
            if self._with_integrity_id and self._protocol_version >= ProtocolVersion.V2:
                if resp_offset < len(response):
                    _resp_iid, iid_consumed = decode_uint32_vlq(response, resp_offset)
                    resp_offset += iid_consumed

            return response[resp_offset:]

    async def _cotp_connect(self, local_tsap: int, remote_tsap: bytes) -> None:
        """Perform COTP Connection Request / Confirm handshake."""
        if self._writer is None or self._reader is None:
            raise RuntimeError("Not connected")

        # Build COTP CR
        base_pdu = struct.pack(">BBHHB", 6, _COTP_CR, 0x0000, 0x0001, 0x00)
        calling_tsap = struct.pack(">BBH", 0xC1, 2, local_tsap)
        called_tsap = struct.pack(">BB", 0xC2, len(remote_tsap)) + remote_tsap
        pdu_size_param = struct.pack(">BBB", 0xC0, 1, 0x0A)

        params = calling_tsap + called_tsap + pdu_size_param
        cr_pdu = struct.pack(">B", 6 + len(params)) + base_pdu[1:] + params

        # Send TPKT + CR
        tpkt = struct.pack(">BBH", 3, 0, 4 + len(cr_pdu)) + cr_pdu
        self._writer.write(tpkt)
        await self._writer.drain()

        # Receive TPKT + CC
        tpkt_header = await self._reader.readexactly(4)
        _, _, length = struct.unpack(">BBH", tpkt_header)
        payload = await self._reader.readexactly(length - 4)

        if len(payload) < 7 or payload[1] != _COTP_CC:
            raise RuntimeError(f"Expected COTP CC, got {payload[1]:#04x}")

    async def _init_ssl(self) -> None:
        """Send InitSSL request (required before CreateObject)."""
        seq_num = self._next_sequence_number()

        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,
            FunctionCode.INIT_SSL,
            0x0000,
            seq_num,
            0x00000000,
            0x30,  # Transport flags for InitSSL
        )
        request += struct.pack(">I", 0)

        frame = encode_header(ProtocolVersion.V1, len(request)) + request
        frame += struct.pack(">BBH", 0x72, ProtocolVersion.V1, 0x0000)
        await self._send_cotp_dt(frame)

        response_data = await self._recv_cotp_dt()
        version, data_length, consumed = decode_header(response_data)
        response = response_data[consumed : consumed + data_length]

        if len(response) < 14:
            raise RuntimeError("InitSSL response too short")

        logger.debug(f"InitSSL response received, version=V{version}")

    async def _activate_tls(
        self,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        tls_ca: Optional[str] = None,
    ) -> None:
        """Activate TLS 1.3 over the COTP connection.

        Called after InitSSL and before CreateObject. Wraps the underlying
        asyncio streams with TLS.
        """
        if self._writer is None:
            raise RuntimeError("Cannot activate TLS: not connected")

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        # TLS 1.3 cipher suites are auto-negotiated on modern OpenSSL;
        # set_ciphers() only controls TLS 1.2 and below.
        try:
            ctx.set_ciphers("TLS_AES_256_GCM_SHA384:TLS_AES_128_GCM_SHA256")
        except ssl.SSLError:
            pass

        if tls_cert and tls_key:
            ctx.load_cert_chain(tls_cert, tls_key)

        if tls_ca:
            ctx.load_verify_locations(tls_ca)
        else:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        # Upgrade the connection to TLS.
        # StreamWriter.start_tls() is the clean API (Python 3.11+).
        # For Python 3.10, fall back to loop.start_tls() with the existing protocol.
        if hasattr(self._writer, "start_tls"):
            await self._writer.start_tls(ctx, server_hostname=self._host)
        else:
            transport = self._writer.transport
            protocol = transport.get_protocol()
            loop = asyncio.get_event_loop()
            new_transport = await loop.start_tls(transport, protocol, ctx, server_hostname=self._host)
            # Update writer's internal transport reference
            self._writer._transport = new_transport

        self._tls_active = True

        # Extract OMS exporter secret for legitimation key derivation
        ssl_object = self._writer.transport.get_extra_info("ssl_object")
        if ssl_object is not None:
            try:
                self._oms_secret = ssl_object.export_keying_material("EXPERIMENTAL_OMS", 32, None)
                logger.debug("OMS exporter secret extracted from TLS session")
            except (AttributeError, ssl.SSLError) as e:
                logger.warning(f"Could not extract OMS exporter secret: {e}")
                self._oms_secret = None

        logger.info("TLS activated on async COTP connection")

    async def _create_session(self) -> None:
        """Send CreateObject to establish S7CommPlus session."""
        seq_num = self._next_sequence_number()

        # Build CreateObject request header
        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,
            FunctionCode.CREATE_OBJECT,
            0x0000,
            seq_num,
            ObjectId.OBJECT_NULL_SERVER_SESSION,  # SessionId = 288
            0x36,
        )

        # RequestId: ObjectServerSessionContainer (285)
        request += struct.pack(">I", ObjectId.OBJECT_SERVER_SESSION_CONTAINER)

        # RequestValue: ValueUDInt(0)
        request += bytes([0x00, DataType.UDINT]) + encode_uint32_vlq(0)

        # Unknown padding
        request += struct.pack(">I", 0)

        # RequestObject: NullServerSession PObject
        request += bytes([ElementID.START_OF_OBJECT])
        request += struct.pack(">I", ObjectId.GET_NEW_RID_ON_SERVER)
        request += encode_uint32_vlq(ObjectId.CLASS_SERVER_SESSION)
        request += encode_uint32_vlq(0)  # ClassFlags
        request += encode_uint32_vlq(0)  # AttributeId

        # Attribute: ServerSessionClientRID = 0x80c3c901
        request += bytes([ElementID.ATTRIBUTE])
        request += encode_uint32_vlq(ObjectId.SERVER_SESSION_CLIENT_RID)
        request += encode_typed_value(DataType.RID, 0x80C3C901)

        # Nested: ClassSubscriptions
        request += bytes([ElementID.START_OF_OBJECT])
        request += struct.pack(">I", ObjectId.GET_NEW_RID_ON_SERVER)
        request += encode_uint32_vlq(ObjectId.CLASS_SUBSCRIPTIONS)
        request += encode_uint32_vlq(0)
        request += encode_uint32_vlq(0)
        request += bytes([ElementID.TERMINATING_OBJECT])

        request += bytes([ElementID.TERMINATING_OBJECT])
        request += struct.pack(">I", 0)

        # Frame header + trailer (always V1 for CreateObject)
        frame = encode_header(ProtocolVersion.V1, len(request)) + request
        frame += struct.pack(">BBH", 0x72, ProtocolVersion.V1, 0x0000)
        await self._send_cotp_dt(frame)

        response_data = await self._recv_cotp_dt()
        version, data_length, consumed = decode_header(response_data)
        response = response_data[consumed : consumed + data_length]

        if len(response) < 14:
            raise RuntimeError("CreateObject response too short")

        self._session_id = struct.unpack_from(">I", response, 9)[0]
        self._protocol_version = version

        logger.debug(f"Session created: id=0x{self._session_id:08X}, version=V{version}")

        # Parse response payload to extract ServerSessionVersion
        self._parse_create_object_response(response[14:])

    def _parse_create_object_response(self, payload: bytes) -> None:
        """Parse CreateObject response to extract ServerSessionVersion."""
        offset = 0
        while offset < len(payload):
            tag = payload[offset]

            if tag == ElementID.ATTRIBUTE:
                offset += 1
                if offset >= len(payload):
                    break
                attr_id, consumed = decode_uint32_vlq(payload, offset)
                offset += consumed

                if attr_id == ObjectId.SERVER_SESSION_VERSION:
                    if offset + 2 > len(payload):
                        break
                    _flags = payload[offset]
                    datatype = payload[offset + 1]
                    offset += 2
                    if datatype in (DataType.UDINT, DataType.DWORD):
                        value, consumed = decode_uint32_vlq(payload, offset)
                        offset += consumed
                        self._server_session_version = value
                        logger.info(f"ServerSessionVersion = {value}")
                        return
                    else:
                        logger.debug(f"ServerSessionVersion has unexpected type {datatype:#04x}")
                else:
                    if offset + 2 > len(payload):
                        break
                    _flags = payload[offset]
                    datatype = payload[offset + 1]
                    offset += 2
                    offset = self._skip_typed_value(payload, offset, datatype, _flags)

            elif tag == ElementID.START_OF_OBJECT:
                offset += 1
                if offset + 4 > len(payload):
                    break
                offset += 4  # RelationId
                _, consumed = decode_uint32_vlq(payload, offset)
                offset += consumed  # ClassId
                _, consumed = decode_uint32_vlq(payload, offset)
                offset += consumed  # ClassFlags
                _, consumed = decode_uint32_vlq(payload, offset)
                offset += consumed  # AttributeId

            elif tag == ElementID.TERMINATING_OBJECT:
                offset += 1
            elif tag == 0x00:
                offset += 1
            else:
                offset += 1

        logger.debug("ServerSessionVersion not found in CreateObject response")

    def _skip_typed_value(self, data: bytes, offset: int, datatype: int, flags: int) -> int:
        """Skip over a typed value in the PObject tree."""
        is_array = bool(flags & 0x10)

        if is_array:
            if offset >= len(data):
                return offset
            count, consumed = decode_uint32_vlq(data, offset)
            offset += consumed
            elem_size = _element_size(datatype)
            if elem_size > 0:
                offset += count * elem_size
            else:
                for _ in range(count):
                    if offset >= len(data):
                        break
                    _, consumed = decode_uint32_vlq(data, offset)
                    offset += consumed
            return offset

        if datatype == DataType.NULL:
            return offset
        elif datatype in (DataType.BOOL, DataType.USINT, DataType.BYTE, DataType.SINT):
            return offset + 1
        elif datatype in (DataType.UINT, DataType.WORD, DataType.INT):
            return offset + 2
        elif datatype in (DataType.UDINT, DataType.DWORD, DataType.AID, DataType.DINT):
            _, consumed = decode_uint32_vlq(data, offset)
            return offset + consumed
        elif datatype in (DataType.ULINT, DataType.LWORD, DataType.LINT):
            _, consumed = decode_uint64_vlq(data, offset)
            return offset + consumed
        elif datatype == DataType.REAL:
            return offset + 4
        elif datatype == DataType.LREAL:
            return offset + 8
        elif datatype == DataType.TIMESTAMP:
            return offset + 8
        elif datatype == DataType.TIMESPAN:
            _, consumed = decode_uint64_vlq(data, offset)
            return offset + consumed
        elif datatype == DataType.RID:
            return offset + 4
        elif datatype in (DataType.BLOB, DataType.WSTRING):
            length, consumed = decode_uint32_vlq(data, offset)
            return offset + consumed + length
        elif datatype == DataType.STRUCT:
            count, consumed = decode_uint32_vlq(data, offset)
            offset += consumed
            for _ in range(count):
                if offset + 2 > len(data):
                    break
                sub_flags = data[offset]
                sub_type = data[offset + 1]
                offset += 2
                offset = self._skip_typed_value(data, offset, sub_type, sub_flags)
            return offset
        else:
            return offset

    async def _setup_session(self) -> None:
        """Send SetMultiVariables to echo ServerSessionVersion back to the PLC."""
        if self._server_session_version is None:
            return

        seq_num = self._next_sequence_number()

        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,
            FunctionCode.SET_MULTI_VARIABLES,
            0x0000,
            seq_num,
            self._session_id,
            0x36,
        )

        payload = bytearray()
        payload += struct.pack(">I", self._session_id)
        payload += encode_uint32_vlq(1)
        payload += encode_uint32_vlq(1)
        payload += encode_uint32_vlq(ObjectId.SERVER_SESSION_VERSION)
        payload += encode_uint32_vlq(1)
        payload += bytes([0x00, DataType.UDINT])
        payload += encode_uint32_vlq(self._server_session_version)
        payload += bytes([0x00])
        payload += encode_object_qualifier()
        payload += struct.pack(">I", 0)

        request += bytes(payload)

        frame = encode_header(self._protocol_version, len(request)) + request
        frame += struct.pack(">BBH", 0x72, self._protocol_version, 0x0000)
        await self._send_cotp_dt(frame)

        response_data = await self._recv_cotp_dt()
        version, data_length, consumed = decode_header(response_data)
        response = response_data[consumed : consumed + data_length]

        if len(response) < 14:
            raise RuntimeError("SetupSession response too short")

        resp_payload = response[14:]
        if len(resp_payload) >= 1:
            return_value, _ = decode_uint64_vlq(resp_payload, 0)
            if return_value != 0:
                logger.warning(f"SetupSession: PLC returned error {return_value}")
            else:
                logger.info("Session setup completed successfully")

    async def _delete_session(self) -> None:
        """Send DeleteObject to close the session."""
        seq_num = self._next_sequence_number()

        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,
            FunctionCode.DELETE_OBJECT,
            0x0000,
            seq_num,
            self._session_id,
            0x36,
        )
        request += struct.pack(">I", 0)

        frame = encode_header(self._protocol_version, len(request)) + request
        frame += struct.pack(">BBH", 0x72, self._protocol_version, 0x0000)
        await self._send_cotp_dt(frame)

        try:
            await asyncio.wait_for(self._recv_cotp_dt(), timeout=1.0)
        except Exception:
            pass

    async def _send_cotp_dt(self, data: bytes) -> None:
        """Send data wrapped in COTP DT + TPKT."""
        if self._writer is None:
            raise RuntimeError("Not connected")

        cotp_dt = struct.pack(">BBB", 2, _COTP_DT, 0x80) + data
        tpkt = struct.pack(">BBH", 3, 0, 4 + len(cotp_dt)) + cotp_dt
        self._writer.write(tpkt)
        await self._writer.drain()

    async def _recv_cotp_dt(self) -> bytes:
        """Receive TPKT + COTP DT and return the payload."""
        if self._reader is None:
            raise RuntimeError("Not connected")

        tpkt_header = await self._reader.readexactly(4)
        _, _, length = struct.unpack(">BBH", tpkt_header)
        payload = await self._reader.readexactly(length - 4)

        if len(payload) < 3 or payload[1] != _COTP_DT:
            raise RuntimeError(f"Expected COTP DT, got {payload[1]:#04x}")

        return payload[3:]

    def _next_sequence_number(self) -> int:
        seq = self._sequence_number
        self._sequence_number = (self._sequence_number + 1) & 0xFFFF
        return seq

    async def __aenter__(self) -> "S7CommPlusAsyncClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.disconnect()
