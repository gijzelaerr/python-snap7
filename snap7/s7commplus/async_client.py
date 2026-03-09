"""
Async S7CommPlus client for S7-1200/1500 PLCs.

Provides the same API as S7CommPlusClient but using asyncio for
non-blocking I/O. Uses asyncio.Lock for concurrent safety.

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
import struct
from typing import Any, Optional

from .protocol import (
    DataType,
    ElementID,
    FunctionCode,
    ObjectId,
    Opcode,
    ProtocolVersion,
    S7COMMPLUS_LOCAL_TSAP,
    S7COMMPLUS_REMOTE_TSAP,
)
from .codec import encode_header, decode_header, encode_typed_value, encode_object_qualifier
from .vlq import encode_uint32_vlq, decode_uint64_vlq
from .client import _build_read_payload, _parse_read_response, _build_write_payload, _parse_write_response

logger = logging.getLogger(__name__)

# COTP constants
_COTP_CR = 0xE0
_COTP_CC = 0xD0
_COTP_DT = 0xF0


class S7CommPlusAsyncClient:
    """Async S7CommPlus client for S7-1200/1500 PLCs.

    Supports V1 protocol. V2/V3/TLS planned for future.

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

    async def connect(
        self,
        host: str,
        port: int = 102,
        rack: int = 0,
        slot: int = 1,
    ) -> None:
        """Connect to an S7-1200/1500 PLC.

        If the PLC does not support S7CommPlus data operations, a secondary
        legacy S7 connection is established transparently for data access.

        Args:
            host: PLC IP address or hostname
            port: TCP port (default 102)
            rack: PLC rack number
            slot: PLC slot number
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

            # S7CommPlus session setup
            await self._create_session()

            self._connected = True
            logger.info(
                f"Async S7CommPlus connected to {host}:{port}, version=V{self._protocol_version}, session={self._session_id}"
            )

            # Probe S7CommPlus data operations
            if not await self._probe_s7commplus_data():
                logger.info("S7CommPlus data operations not supported, falling back to legacy S7 protocol")
                await self._setup_legacy_fallback()

        except Exception:
            await self.disconnect()
            raise

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
        """Send an S7CommPlus request and receive the response."""
        async with self._lock:
            if not self._connected or self._writer is None or self._reader is None:
                raise RuntimeError("Not connected")

            seq_num = self._next_sequence_number()

            request = (
                struct.pack(
                    ">BHHHHIB",
                    Opcode.REQUEST,
                    0x0000,
                    function_code,
                    0x0000,
                    seq_num,
                    self._session_id,
                    0x36,
                )
                + payload
            )

            frame = encode_header(self._protocol_version, len(request)) + request
            frame += struct.pack(">BBH", 0x72, self._protocol_version, 0x0000)
            await self._send_cotp_dt(frame)

            response_data = await self._recv_cotp_dt()

            version, data_length, consumed = decode_header(response_data)
            response = response_data[consumed : consumed + data_length]

            if len(response) < 14:
                raise RuntimeError("Response too short")

            return response[14:]

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

        # Frame header + trailer
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
