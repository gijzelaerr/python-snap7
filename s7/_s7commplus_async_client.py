"""Pure async S7CommPlus client for S7-1200/1500 PLCs (no legacy fallback).

This is an internal module used by the unified ``s7.AsyncClient``.  It provides
raw S7CommPlus data operations without any fallback logic -- the unified
client is responsible for deciding when to fall back to legacy S7.

Reference: thomas-v2/S7CommPlusDriver (C#, LGPL-3.0)
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
    ObjectId,
    Opcode,
    ProtocolVersion,
    READ_FUNCTION_CODES,
    S7COMMPLUS_LOCAL_TSAP,
    S7COMMPLUS_REMOTE_TSAP,
)
from .codec import encode_header, decode_header, encode_typed_value, encode_object_qualifier
from .vlq import encode_uint32_vlq, decode_uint32_vlq, decode_uint64_vlq
from ._s7commplus_client import (
    _build_read_payload,
    _parse_read_response,
    _build_write_payload,
    _parse_write_response,
    _build_area_read_payload,
    _build_area_write_payload,
    _build_explore_payload,
    _build_invoke_payload,
)

logger = logging.getLogger(__name__)

# COTP constants
_COTP_CR = 0xE0
_COTP_CC = 0xD0
_COTP_DT = 0xF0


class S7CommPlusAsyncClient:
    """Pure async S7CommPlus client without legacy fallback.

    Use ``s7.AsyncClient`` for automatic protocol selection.
    """

    def __init__(self) -> None:
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._session_id: int = 0
        self._sequence_number: int = 0
        self._protocol_version: int = 0
        self._connected = False
        self._lock = asyncio.Lock()

        # V2+ IntegrityId tracking
        self._integrity_id_read: int = 0
        self._integrity_id_write: int = 0
        self._with_integrity_id: bool = False

        # TLS state
        self._tls_active: bool = False
        self._oms_secret: Optional[bytes] = None
        self._server_session_version: Optional[int] = None
        self._session_setup_ok: bool = False

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def protocol_version(self) -> int:
        return self._protocol_version

    @property
    def session_id(self) -> int:
        return self._session_id

    @property
    def session_setup_ok(self) -> bool:
        """Whether the S7CommPlus session setup succeeded for data operations."""
        return self._session_setup_ok

    @property
    def tls_active(self) -> bool:
        """Whether TLS is active on the connection."""
        return self._tls_active

    @property
    def oms_secret(self) -> Optional[bytes]:
        """OMS exporter secret from TLS session (None if TLS not active)."""
        return self._oms_secret

    async def connect(
        self,
        host: str,
        port: int = 102,
        rack: int = 0,
        slot: int = 1,
        *,
        use_tls: bool = False,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        tls_ca: Optional[str] = None,
    ) -> None:
        """Connect to an S7-1200/1500 PLC using S7CommPlus.

        Args:
            host: PLC IP address or hostname
            port: TCP port (default 102)
            rack: PLC rack number (unused, kept for API symmetry)
            slot: PLC slot number (unused, kept for API symmetry)
            use_tls: Whether to activate TLS after InitSSL.
            tls_cert: Path to client TLS certificate (PEM)
            tls_key: Path to client private key (PEM)
            tls_ca: Path to CA certificate for PLC verification (PEM)
        """
        self._host = host

        # TCP connect
        self._reader, self._writer = await asyncio.open_connection(host, port)

        try:
            # Step 1: COTP handshake with S7CommPlus TSAP values
            await self._cotp_connect(S7COMMPLUS_LOCAL_TSAP, S7COMMPLUS_REMOTE_TSAP)

            # Step 2: InitSSL handshake
            await self._init_ssl()

            # Step 3: TLS activation (between InitSSL and CreateObject)
            if use_tls:
                await self._activate_tls(tls_cert=tls_cert, tls_key=tls_key, tls_ca=tls_ca)

            # Step 4: S7CommPlus session setup (CreateObject)
            await self._create_session()

            # Step 5: Version-specific validation
            if self._protocol_version >= ProtocolVersion.V3:
                if not use_tls:
                    logger.warning(
                        "PLC reports V3 protocol but TLS is not enabled. Connection may not work without use_tls=True."
                    )
            elif self._protocol_version == ProtocolVersion.V2:
                if not self._tls_active:
                    from snap7.error import S7ConnectionError

                    raise S7ConnectionError("PLC reports V2 protocol but TLS is not active. V2 requires TLS. Use use_tls=True.")
                self._with_integrity_id = True
                self._integrity_id_read = 0
                self._integrity_id_write = 0
                logger.info("V2 IntegrityId tracking enabled")

            self._connected = True

            # Step 6: Session setup - echo ServerSessionVersion back to PLC
            if self._server_session_version is not None:
                self._session_setup_ok = await self._setup_session()
            else:
                logger.warning("PLC did not provide ServerSessionVersion - session setup incomplete")
                self._session_setup_ok = False
            logger.info(
                f"Async S7CommPlus connected to {host}:{port}, "
                f"version=V{self._protocol_version}, session={self._session_id}, "
                f"tls={self._tls_active}"
            )

        except Exception:
            await self.disconnect()
            raise

    async def authenticate(self, password: str, username: str = "") -> None:
        """Perform PLC password authentication (legitimation).

        Args:
            password: PLC password
            username: Username for new-style auth (optional)

        Raises:
            S7ConnectionError: If not connected, TLS not active, or auth fails
        """
        if not self._connected:
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("Not connected")

        if not self._tls_active or self._oms_secret is None:
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("Legitimation requires TLS. Connect with use_tls=True.")

        challenge = await self._get_legitimation_challenge()
        logger.info(f"Received legitimation challenge ({len(challenge)} bytes)")

        from .legitimation import build_legacy_response, build_new_response

        if username:
            response_data = build_new_response(password, challenge, self._oms_secret, username)
            await self._send_legitimation_new(response_data)
        else:
            try:
                response_data = build_new_response(password, challenge, self._oms_secret, "")
                await self._send_legitimation_new(response_data)
            except NotImplementedError:
                response_data = build_legacy_response(password, challenge)
                await self._send_legitimation_legacy(response_data)

        logger.info("PLC legitimation completed successfully")

    async def _activate_tls(
        self,
        tls_cert: Optional[str] = None,
        tls_key: Optional[str] = None,
        tls_ca: Optional[str] = None,
    ) -> None:
        """Activate TLS 1.3 over the COTP connection."""
        if self._writer is None:
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("Cannot activate TLS: not connected")

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3

        if hasattr(ctx, "set_ciphersuites"):
            ctx.set_ciphersuites("TLS_AES_256_GCM_SHA384:TLS_AES_128_GCM_SHA256")

        if tls_cert and tls_key:
            ctx.load_cert_chain(tls_cert, tls_key)

        if tls_ca:
            ctx.load_verify_locations(tls_ca)
        else:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        transport = self._writer.transport
        loop = asyncio.get_event_loop()
        new_transport = await loop.start_tls(
            transport,
            transport.get_protocol(),
            ctx,
            server_hostname=self._host,
        )

        self._writer._transport = new_transport
        self._tls_active = True

        if new_transport is None:
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("TLS handshake failed: no transport returned")

        ssl_object = new_transport.get_extra_info("ssl_object")
        if ssl_object is not None:
            try:
                self._oms_secret = ssl_object.export_keying_material("EXPERIMENTAL_OMS", 32, None)
                logger.debug("OMS exporter secret extracted from TLS session")
            except (AttributeError, ssl.SSLError) as e:
                logger.warning(f"Could not extract OMS exporter secret: {e}")
                self._oms_secret = None

        logger.info("TLS 1.3 activated on async COTP connection")

    async def _get_legitimation_challenge(self) -> bytes:
        """Request legitimation challenge from PLC."""
        from .protocol import LegitimationId, DataType as DT

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
            from snap7.error import S7ConnectionError

            raise S7ConnectionError(f"GetVarSubStreamed for challenge failed: return_value={return_value}")

        if offset + 2 > len(resp_payload):
            from snap7.error import S7ConnectionError

            raise S7ConnectionError("Challenge response too short")

        _flags = resp_payload[offset]
        datatype = resp_payload[offset + 1]
        offset += 2

        if datatype == DT.BLOB:
            length, consumed = decode_uint32_vlq(resp_payload, offset)
            offset += consumed
            return bytes(resp_payload[offset : offset + length])
        else:
            count, consumed = decode_uint32_vlq(resp_payload, offset)
            offset += consumed
            return bytes(resp_payload[offset : offset + count])

    async def _send_legitimation_new(self, encrypted_response: bytes) -> None:
        """Send new-style legitimation response (AES-256-CBC encrypted)."""
        from .protocol import LegitimationId, DataType as DT

        payload = bytearray()
        payload += struct.pack(">I", self._session_id)
        payload += encode_uint32_vlq(1)
        payload += encode_uint32_vlq(LegitimationId.LEGITIMATE)
        payload += bytes([0x00, DT.BLOB])
        payload += encode_uint32_vlq(len(encrypted_response))
        payload += encrypted_response
        payload += struct.pack(">I", 0)

        resp_payload = await self._send_request(FunctionCode.SET_VARIABLE, bytes(payload))

        if len(resp_payload) >= 1:
            return_value, _ = decode_uint64_vlq(resp_payload, 0)
            if return_value < 0:
                from snap7.error import S7ConnectionError

                raise S7ConnectionError(f"Legitimation rejected by PLC: return_value={return_value}")
            logger.debug(f"New legitimation return_value={return_value}")

    async def _send_legitimation_legacy(self, response: bytes) -> None:
        """Send legacy legitimation response (SHA-1 XOR)."""
        from .protocol import LegitimationId, DataType as DT

        payload = bytearray()
        payload += struct.pack(">I", self._session_id)
        payload += encode_uint32_vlq(1)
        payload += encode_uint32_vlq(LegitimationId.SERVER_SESSION_RESPONSE)
        payload += bytes([0x10, DT.USINT])  # flags=0x10 (array)
        payload += encode_uint32_vlq(len(response))
        payload += response
        payload += struct.pack(">I", 0)

        resp_payload = await self._send_request(FunctionCode.SET_VARIABLE, bytes(payload))

        if len(resp_payload) >= 1:
            return_value, _ = decode_uint64_vlq(resp_payload, 0)
            if return_value < 0:
                from snap7.error import S7ConnectionError

                raise S7ConnectionError(f"Legacy legitimation rejected by PLC: return_value={return_value}")
            logger.debug(f"Legacy legitimation return_value={return_value}")

    async def disconnect(self) -> None:
        """Disconnect from PLC."""
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
        self._session_setup_ok = False

        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

    async def db_read(self, db_number: int, start: int, size: int) -> bytes:
        """Read raw bytes from a data block."""
        payload = _build_read_payload([(db_number, start, size)])
        response = await self._send_request(FunctionCode.GET_MULTI_VARIABLES, payload)

        results = _parse_read_response(response)
        if not results:
            raise RuntimeError("Read returned no data")
        if results[0] is None:
            raise RuntimeError("Read failed: PLC returned error for item")
        return results[0]

    async def db_write(self, db_number: int, start: int, data: bytes) -> None:
        """Write raw bytes to a data block."""
        payload = _build_write_payload([(db_number, start, data)])
        response = await self._send_request(FunctionCode.SET_MULTI_VARIABLES, payload)
        _parse_write_response(response)

    async def db_read_multi(self, items: list[tuple[int, int, int]]) -> list[bytes]:
        """Read multiple data block regions in a single request."""
        payload = _build_read_payload(items)
        response = await self._send_request(FunctionCode.GET_MULTI_VARIABLES, payload)
        parsed = _parse_read_response(response)
        return [r if r is not None else b"" for r in parsed]

    async def read_area(self, area_rid: int, start: int, size: int) -> bytes:
        """Read raw bytes from a controller memory area (M, I, Q, counters, timers)."""
        payload = _build_area_read_payload(area_rid, start, size)
        response = await self._send_request(FunctionCode.GET_MULTI_VARIABLES, payload)
        results = _parse_read_response(response)
        if not results or results[0] is None:
            raise RuntimeError("Area read failed")
        return results[0]

    async def write_area(self, area_rid: int, start: int, data: bytes) -> None:
        """Write raw bytes to a controller memory area (M, I, Q, counters, timers)."""
        payload = _build_area_write_payload(area_rid, start, data)
        response = await self._send_request(FunctionCode.SET_MULTI_VARIABLES, payload)
        _parse_write_response(response)

    async def explore(self, explore_id: int = 0) -> bytes:
        """Browse the PLC object tree."""
        payload = _build_explore_payload(explore_id)
        return await self._send_request(FunctionCode.EXPLORE, payload)

    async def set_plc_operating_state(self, state: int) -> None:
        """Set the PLC operating state (start/stop)."""
        payload = _build_invoke_payload(state)
        await self._send_request(FunctionCode.INVOKE, payload)

    # -- Internal methods --

    async def _send_request(self, function_code: int, payload: bytes) -> bytes:
        """Send an S7CommPlus request and receive the response."""
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

            integrity_id_bytes = b""
            if self._with_integrity_id and self._protocol_version >= ProtocolVersion.V2:
                is_read = function_code in READ_FUNCTION_CODES
                integrity_id = self._integrity_id_read if is_read else self._integrity_id_write
                integrity_id_bytes = encode_uint32_vlq(integrity_id)

            request = request_header + integrity_id_bytes + payload

            frame = encode_header(self._protocol_version, len(request)) + request
            frame += struct.pack(">BBH", 0x72, self._protocol_version, 0x0000)
            await self._send_cotp_dt(frame)

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

        base_pdu = struct.pack(">BBHHB", 6, _COTP_CR, 0x0000, 0x0001, 0x00)
        calling_tsap = struct.pack(">BBH", 0xC1, 2, local_tsap)
        called_tsap = struct.pack(">BB", 0xC2, len(remote_tsap)) + remote_tsap
        pdu_size_param = struct.pack(">BBB", 0xC0, 1, 0x0A)

        params = calling_tsap + called_tsap + pdu_size_param
        cr_pdu = struct.pack(">B", 6 + len(params)) + base_pdu[1:] + params

        tpkt = struct.pack(">BBH", 3, 0, 4 + len(cr_pdu)) + cr_pdu
        self._writer.write(tpkt)
        await self._writer.drain()

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
            0x30,
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

    async def _create_session(self) -> None:
        """Send CreateObject to establish S7CommPlus session."""
        seq_num = self._next_sequence_number()

        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,
            FunctionCode.CREATE_OBJECT,
            0x0000,
            seq_num,
            ObjectId.OBJECT_NULL_SERVER_SESSION,
            0x36,
        )

        request += struct.pack(">I", ObjectId.OBJECT_SERVER_SESSION_CONTAINER)
        request += bytes([0x00, DataType.UDINT]) + encode_uint32_vlq(0)
        request += struct.pack(">I", 0)

        request += bytes([ElementID.START_OF_OBJECT])
        request += struct.pack(">I", ObjectId.GET_NEW_RID_ON_SERVER)
        request += encode_uint32_vlq(ObjectId.CLASS_SERVER_SESSION)
        request += encode_uint32_vlq(0)
        request += encode_uint32_vlq(0)

        request += bytes([ElementID.ATTRIBUTE])
        request += encode_uint32_vlq(ObjectId.SERVER_SESSION_CLIENT_RID)
        request += encode_typed_value(DataType.RID, 0x80C3C901)

        request += bytes([ElementID.START_OF_OBJECT])
        request += struct.pack(">I", ObjectId.GET_NEW_RID_ON_SERVER)
        request += encode_uint32_vlq(ObjectId.CLASS_SUBSCRIPTIONS)
        request += encode_uint32_vlq(0)
        request += encode_uint32_vlq(0)
        request += bytes([ElementID.TERMINATING_OBJECT])

        request += bytes([ElementID.TERMINATING_OBJECT])
        request += struct.pack(">I", 0)

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

        self._parse_create_object_response(response[14:])

    def _parse_create_object_response(self, payload: bytes) -> None:
        """Parse CreateObject response to extract ServerSessionVersion (attribute 306)."""
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
                    if offset + 2 > len(payload):
                        break
                    _flags = payload[offset]
                    _dt = payload[offset + 1]
                    offset += 2
                    if offset < len(payload):
                        _, consumed = decode_uint32_vlq(payload, offset)
                        offset += consumed

            elif tag == ElementID.START_OF_OBJECT:
                offset += 1
                if offset + 4 > len(payload):
                    break
                offset += 4
                _, consumed = decode_uint32_vlq(payload, offset)
                offset += consumed
                _, consumed = decode_uint32_vlq(payload, offset)
                offset += consumed
                _, consumed = decode_uint32_vlq(payload, offset)
                offset += consumed

            elif tag == ElementID.TERMINATING_OBJECT:
                offset += 1
            elif tag == 0x00:
                offset += 1
            else:
                offset += 1

        logger.debug("ServerSessionVersion not found in CreateObject response")

    async def _setup_session(self) -> bool:
        """Echo ServerSessionVersion back to the PLC via SetMultiVariables."""
        if self._server_session_version is None:
            return False

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

        try:
            resp_payload = await self._send_request(FunctionCode.SET_MULTI_VARIABLES, bytes(payload))
            if len(resp_payload) >= 1:
                return_value, _ = decode_uint64_vlq(resp_payload, 0)
                if return_value != 0:
                    logger.warning(f"SetupSession: PLC returned error {return_value}")
                    return False
                else:
                    logger.info("Session setup completed successfully")
                    return True
            return False
        except Exception as e:
            logger.warning(f"SetupSession failed: {e}")
            return False

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
