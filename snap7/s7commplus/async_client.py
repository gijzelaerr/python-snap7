"""
Async S7CommPlus client for S7-1200/1500 PLCs.

Provides the same API as S7CommPlusClient but using asyncio for
non-blocking I/O. Uses asyncio.Lock for concurrent safety.

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

from .protocol import FunctionCode, Opcode, ProtocolVersion
from .codec import encode_header, decode_header
from .vlq import encode_uint32_vlq, decode_uint32_vlq

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
    """

    def __init__(self) -> None:
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._session_id: int = 0
        self._sequence_number: int = 0
        self._protocol_version: int = 0
        self._connected = False
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def protocol_version(self) -> int:
        return self._protocol_version

    @property
    def session_id(self) -> int:
        return self._session_id

    async def connect(
        self,
        host: str,
        port: int = 102,
        rack: int = 0,
        slot: int = 1,
    ) -> None:
        """Connect to an S7-1200/1500 PLC.

        Args:
            host: PLC IP address or hostname
            port: TCP port (default 102)
            rack: PLC rack number
            slot: PLC slot number
        """
        local_tsap = 0x0100
        remote_tsap = 0x0100 | (rack << 5) | slot

        # TCP connect
        self._reader, self._writer = await asyncio.open_connection(host, port)

        try:
            # COTP handshake
            await self._cotp_connect(local_tsap, remote_tsap)

            # S7CommPlus session setup
            await self._create_session()

            self._connected = True
            logger.info(
                f"Async S7CommPlus connected to {host}:{port}, "
                f"version=V{self._protocol_version}, session={self._session_id}"
            )
        except Exception:
            await self.disconnect()
            raise

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
        object_id = 0x00010000 | (db_number & 0xFFFF)
        payload = bytearray()
        payload += encode_uint32_vlq(1)
        payload += encode_uint32_vlq(object_id)
        payload += encode_uint32_vlq(start)
        payload += encode_uint32_vlq(size)

        response = await self._send_request(
            FunctionCode.GET_MULTI_VARIABLES, bytes(payload)
        )

        offset = 0
        _, consumed = decode_uint32_vlq(response, offset)
        offset += consumed
        item_count, consumed = decode_uint32_vlq(response, offset)
        offset += consumed

        if item_count == 0:
            return b""

        status, consumed = decode_uint32_vlq(response, offset)
        offset += consumed
        data_length, consumed = decode_uint32_vlq(response, offset)
        offset += consumed

        if status != 0:
            raise RuntimeError(f"Read failed with status {status}")

        return response[offset : offset + data_length]

    async def db_write(self, db_number: int, start: int, data: bytes) -> None:
        """Write raw bytes to a data block.

        Args:
            db_number: Data block number
            start: Start byte offset
            data: Bytes to write
        """
        object_id = 0x00010000 | (db_number & 0xFFFF)
        payload = bytearray()
        payload += encode_uint32_vlq(1)
        payload += encode_uint32_vlq(object_id)
        payload += encode_uint32_vlq(start)
        payload += encode_uint32_vlq(len(data))
        payload += data

        response = await self._send_request(
            FunctionCode.SET_MULTI_VARIABLES, bytes(payload)
        )

        offset = 0
        return_code, consumed = decode_uint32_vlq(response, offset)
        if return_code != 0:
            raise RuntimeError(f"Write failed with return code {return_code}")

    async def db_read_multi(
        self, items: list[tuple[int, int, int]]
    ) -> list[bytes]:
        """Read multiple data block regions in a single request.

        Args:
            items: List of (db_number, start_offset, size) tuples

        Returns:
            List of raw bytes for each item
        """
        payload = bytearray()
        payload += encode_uint32_vlq(len(items))
        for db_number, start, size in items:
            object_id = 0x00010000 | (db_number & 0xFFFF)
            payload += encode_uint32_vlq(object_id)
            payload += encode_uint32_vlq(start)
            payload += encode_uint32_vlq(size)

        response = await self._send_request(
            FunctionCode.GET_MULTI_VARIABLES, bytes(payload)
        )

        offset = 0
        _, consumed = decode_uint32_vlq(response, offset)
        offset += consumed
        item_count, consumed = decode_uint32_vlq(response, offset)
        offset += consumed

        results: list[bytes] = []
        for _ in range(item_count):
            status, consumed = decode_uint32_vlq(response, offset)
            offset += consumed
            data_length, consumed = decode_uint32_vlq(response, offset)
            offset += consumed
            if status == 0 and data_length > 0:
                results.append(response[offset : offset + data_length])
                offset += data_length
            else:
                results.append(b"")

        return results

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

            request = struct.pack(
                ">BHHHHIB",
                Opcode.REQUEST,
                0x0000,
                function_code,
                0x0000,
                seq_num,
                self._session_id,
                0x36,
            ) + payload

            frame = encode_header(self._protocol_version, len(request)) + request
            await self._send_cotp_dt(frame)

            response_data = await self._recv_cotp_dt()

            version, data_length, consumed = decode_header(response_data)
            response = response_data[consumed:]

            if len(response) < 14:
                raise RuntimeError("Response too short")

            return response[14:]

    async def _cotp_connect(self, local_tsap: int, remote_tsap: int) -> None:
        """Perform COTP Connection Request / Confirm handshake."""
        if self._writer is None or self._reader is None:
            raise RuntimeError("Not connected")

        # Build COTP CR
        base_pdu = struct.pack(">BBHHB", 6, _COTP_CR, 0x0000, 0x0001, 0x00)
        calling_tsap = struct.pack(">BBH", 0xC1, 2, local_tsap)
        called_tsap = struct.pack(">BBH", 0xC2, 2, remote_tsap)
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
            0x00000000,
            0x36,
        )
        request += struct.pack(">I", 0)

        frame = encode_header(ProtocolVersion.V1, len(request)) + request
        await self._send_cotp_dt(frame)

        response_data = await self._recv_cotp_dt()
        version, data_length, consumed = decode_header(response_data)
        response = response_data[consumed:]

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
