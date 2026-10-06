"""Asynchronous client for the classic S7 protocol.

Uses asyncio streams for non-blocking I/O with an asyncio.Lock() to serialize
send/receive cycles, ensuring safe concurrent use via asyncio.gather().

``s7.AsyncClient`` and ``snap7.AsyncClient`` expose this same implementation.
"""

import asyncio
import logging
import struct
import time
from collections.abc import Callable, Sequence
from contextvars import ContextVar
from typing import List, Any, Optional, Tuple, Type, Union
from types import TracebackType
from datetime import datetime

from .connection import TPDUSize
from .s7protocol import S7Protocol, S7UserDataGroup, S7UserDataSubfunction, get_return_code_description
from .datatypes import S7DataTypes, S7WordLen
from .error import S7Error, S7ConnectionError, S7ProtocolError, S7TimeoutError
from .client_base import ClientMixin, _instrumented
from .tags import Tag
from .client import _decode_tag, _encode_tag
from .szl import parse_cp_info_szl, parse_cpu_info_szl, parse_order_code_szl, parse_protection_szl
from .client import _parse_force_szl
from .rate_limiter import RateLimitAlgorithm, RateLimitBehavior, RequestRateLimiter
from .type import (
    Area,
    Block,
    BlocksList,
    ForceEntry,
    S7CpuInfo,
    TS7BlockInfo,
    S7CpInfo,
    S7OrderCode,
    S7Protection,
    S7SZL,
    Parameter,
)


logger = logging.getLogger(__name__)


class AsyncISOTCPConnection:
    """Async ISO on TCP connection using asyncio streams.

    Mirrors ISOTCPConnection but uses asyncio.open_connection() instead of
    blocking sockets for non-blocking I/O.
    """

    # COTP PDU types
    COTP_CR = 0xE0  # Connection Request
    COTP_CC = 0xD0  # Connection Confirm
    COTP_DR = 0x80  # Disconnect Request
    COTP_DT = 0xF0  # Data Transfer

    # COTP parameter codes (ISO 8073)
    COTP_PARAM_PDU_SIZE = 0xC0
    COTP_PARAM_CALLING_TSAP = 0xC1
    COTP_PARAM_CALLED_TSAP = 0xC2

    def __init__(
        self,
        host: str,
        port: int = 102,
        local_tsap: int = 0x0100,
        remote_tsap: int = 0x0102,
        tpdu_size: TPDUSize = TPDUSize.S_1024,
    ):
        self.host = host
        self.port = port
        self.local_tsap = local_tsap
        self.remote_tsap = remote_tsap
        self.tpdu_size = tpdu_size
        self.connected = False
        self.pdu_size = 240
        self.timeout = 5.0

        self.src_ref = 0x0001
        self.dst_ref = 0x0000

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    async def connect(self, timeout: float = 5.0) -> None:
        """Establish ISO on TCP connection."""
        self.timeout = timeout

        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
            logger.debug(f"TCP connected to {self.host}:{self.port}")

            await self._iso_connect()

            self.connected = True
            logger.info(f"Connected to {self.host}:{self.port}, PDU size: {self.pdu_size}")

        except Exception as e:
            await self.disconnect()
            if isinstance(e, (S7ConnectionError, S7TimeoutError)):
                raise
            elif isinstance(e, asyncio.TimeoutError):
                raise S7TimeoutError(f"Connection timeout: {e}")
            else:
                raise S7ConnectionError(f"Connection failed: {e}")

    async def disconnect(self) -> None:
        """Disconnect from S7 device."""
        if self._writer:
            try:
                if self.connected:
                    dr_pdu = struct.pack(
                        ">BBHHBB",
                        6,
                        self.COTP_DR,
                        self.dst_ref,
                        self.src_ref,
                        0x00,
                        0x00,
                    )
                    self._writer.write(self._build_tpkt(dr_pdu))
                    await self._writer.drain()
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            finally:
                self._reader = None
                self._writer = None
                self.connected = False
                logger.info(f"Disconnected from {self.host}:{self.port}")

    async def send_data(self, data: bytes) -> None:
        """Send data over ISO connection."""
        if not self.connected or self._writer is None:
            raise S7ConnectionError("Not connected")

        cotp_header = struct.pack(">BBB", 2, self.COTP_DT, 0x80)
        tpkt_frame = self._build_tpkt(cotp_header + data)

        try:
            self._writer.write(tpkt_frame)
            await self._writer.drain()
            logger.debug(f"Sent {len(tpkt_frame)} bytes")
        except (OSError, ConnectionError) as e:
            self.connected = False
            raise S7ConnectionError(f"Send failed: {e}")

    async def receive_data(self) -> bytes:
        """Receive data from ISO connection."""
        if not self.connected:
            raise S7ConnectionError("Not connected")

        try:
            tpkt_header = await self._recv_exact(4)
            version, reserved, length = struct.unpack(">BBH", tpkt_header)
            if version != 3:
                raise S7ConnectionError(f"Invalid TPKT version: {version}")

            remaining = length - 4
            if length < 7:
                raise S7ConnectionError("Invalid TPKT length")

            payload = await self._recv_exact(remaining)

            # Parse COTP DT header
            if len(payload) < 3:
                raise S7ConnectionError("Invalid COTP DT: too short")
            pdu_len, pdu_type, eot_num = struct.unpack(">BBB", payload[:3])
            if pdu_len != 2:
                raise S7ConnectionError("Invalid COTP DT header length")
            if eot_num & 0x7F:
                raise S7ConnectionError("Invalid Class 0 COTP TPDU number")
            if pdu_type != self.COTP_DT:
                raise S7ConnectionError(f"Expected COTP DT, got {pdu_type:#02x}")
            return payload[3:]

        except asyncio.TimeoutError:
            self.connected = False
            raise S7TimeoutError("Receive timeout")
        except (OSError, ConnectionError) as e:
            self.connected = False
            raise S7ConnectionError(f"Receive failed: {e}")

    async def _iso_connect(self) -> None:
        """Establish ISO connection using COTP handshake."""
        if self._writer is None or self._reader is None:
            raise S7ConnectionError("Stream not initialized")

        # Build and send COTP Connection Request
        base_pdu = struct.pack(
            ">BBHHB",
            6,
            self.COTP_CR,
            0x0000,
            self.src_ref,
            0x00,
        )
        calling_tsap = struct.pack(">BBH", self.COTP_PARAM_CALLING_TSAP, 2, self.local_tsap)
        called_tsap = struct.pack(">BBH", self.COTP_PARAM_CALLED_TSAP, 2, self.remote_tsap)
        pdu_size_param = struct.pack(">BBB", self.COTP_PARAM_PDU_SIZE, 1, self.tpdu_size)
        parameters = calling_tsap + called_tsap + pdu_size_param
        total_length = 6 + len(parameters)
        cr_pdu = struct.pack(">B", total_length) + base_pdu[1:] + parameters

        self._writer.write(self._build_tpkt(cr_pdu))
        await self._writer.drain()
        logger.debug("Sent COTP Connection Request")

        # Receive Connection Confirm
        tpkt_header = await self._recv_exact(4)
        version, reserved, length = struct.unpack(">BBH", tpkt_header)
        if version != 3:
            raise S7ConnectionError(f"Invalid TPKT version in response: {version}")

        payload = await self._recv_exact(length - 4)
        self._parse_cotp_cc(payload)
        logger.debug("Received COTP Connection Confirm")

    def _build_tpkt(self, payload: bytes) -> bytes:
        """Build TPKT frame."""
        length = len(payload) + 4
        if not 7 <= length <= 65535:
            raise S7ConnectionError("Invalid TPKT length: expected 7..65535 bytes")
        return struct.pack(">BBH", 3, 0, length) + payload

    def _parse_cotp_cc(self, data: bytes) -> None:
        """Parse COTP Connection Confirm PDU."""
        if len(data) < 7:
            raise S7ConnectionError("Invalid COTP CC: too short")

        pdu_len, pdu_type, dst_ref, src_ref, class_opt = struct.unpack(">BBHHB", data[:7])
        if pdu_type != self.COTP_CC:
            raise S7ConnectionError(f"Expected COTP CC, got {pdu_type:#02x}")

        self.dst_ref = dst_ref

        # Parse parameters
        offset = 7
        while offset < len(data):
            if offset + 2 > len(data):
                break
            param_code = data[offset]
            param_len = data[offset + 1]
            if offset + 2 + param_len > len(data):
                break
            param_data = data[offset + 2 : offset + 2 + param_len]
            if param_code == self.COTP_PARAM_PDU_SIZE:
                if param_len == 1:
                    exponent = param_data[0]
                    if 7 <= exponent <= 13:
                        self.pdu_size = 1 << exponent
                    else:
                        logger.warning(f"Invalid COTP PDU size exponent {exponent}, using default")
                elif param_len == 2:
                    raw = struct.unpack(">H", param_data)[0]
                    if 128 <= raw <= 8192:
                        self.pdu_size = raw
                    else:
                        logger.warning(f"Invalid COTP PDU size {raw}, using default")
                logger.debug(f"Negotiated PDU size: {self.pdu_size}")
            offset += 2 + param_len

    async def _recv_exact(self, size: int) -> bytes:
        """Receive exactly size bytes."""
        if self._reader is None:
            raise S7ConnectionError("Stream not initialized")
        try:
            return await asyncio.wait_for(
                self._reader.readexactly(size),
                timeout=self.timeout,
            )
        except asyncio.IncompleteReadError:
            self.connected = False
            raise S7ConnectionError("Connection closed by peer")
        except asyncio.TimeoutError:
            self.connected = False
            raise S7TimeoutError("Receive timeout")
        except (OSError, ConnectionError) as e:
            self.connected = False
            raise S7ConnectionError(f"Receive error: {e}")

    async def __aenter__(self) -> "AsyncISOTCPConnection":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.disconnect()


class AsyncClient(ClientMixin):
    """Asynchronous client for classic S7 communication.

    Uses asyncio streams for non-blocking I/O. An internal asyncio.Lock
    serializes each send+receive cycle so that concurrent coroutines
    (e.g. via asyncio.gather) never interleave on the same TCP socket.

    For new projects, use ``s7.AsyncClient`` instead.

    Examples:
        >>> from s7 import AsyncClient
        >>> async with AsyncClient() as client:
        ...     await client.connect("192.168.1.10", 0, 1)
        ...     data = await client.db_read(1, 0, 4)
    """

    MAX_VARS = 20

    def __init__(
        self,
        *,
        max_requests_per_second: float = 0,
        rate_limit_algorithm: RateLimitAlgorithm = "fixed",
        rate_limit_behavior: RateLimitBehavior = "block",
        rate_limit_burst: int | None = None,
        on_operation: Optional[Callable[[str, float, bool], None]] = None,
    ) -> None:
        self.connection: Optional[AsyncISOTCPConnection] = None
        self.protocol = S7Protocol()
        self.connected = False
        self.host = ""
        self.port = 102
        self.rack = 0
        self.slot = 0
        self.pdu_length = 480

        self.local_tsap = 0x0100
        self.remote_tsap = 0x0102
        self.connection_type = 1  # PG
        self.session_password: Optional[str] = None

        self._exec_time = 0
        self._last_error = 0
        self._on_operation = on_operation
        self._operation_depth: ContextVar[int] = ContextVar("snap7_async_client_operation_depth", default=0)

        self._lock = asyncio.Lock()
        self._rate_limiter = RequestRateLimiter(
            max_requests_per_second,
            algorithm=rate_limit_algorithm,
            behavior=rate_limit_behavior,
            burst_capacity=rate_limit_burst,
        )

        self._params = {
            Parameter.RemotePort: 102,
            Parameter.SendTimeout: 10,
            Parameter.RecvTimeout: 3000,
            Parameter.SrcRef: 256,
            Parameter.DstRef: 0,
            Parameter.SrcTSap: 256,
            Parameter.PDURequest: 480,
        }

        logger.info("AsyncClient initialized (native async implementation)")

    def _get_connection(self) -> AsyncISOTCPConnection:
        """Get connection, raising if not connected."""
        if self.connection is None:
            raise S7ConnectionError("Not connected to PLC")
        return self.connection

    async def _send_data(self, conn: AsyncISOTCPConnection, request: bytes) -> None:
        """Apply the per-client rate limit and send one S7 request PDU."""
        await self._rate_limiter.acquire_async()
        await conn.send_data(request)

    async def _send_receive(self, request: bytes, max_stale_retries: int = 3) -> dict[str, Any]:
        """Send a request and receive/parse the response, holding the lock.

        The lock ensures that concurrent coroutines never interleave
        send/receive on the same TCP socket.

        Unlike the sync client, we do NOT use protocol.validate_pdu_reference()
        because the protocol's shared sequence counter can be incremented by
        a concurrent coroutine between request building and lock acquisition.
        Instead, we extract the expected sequence directly from the request
        bytes (S7 header bytes 4-5).
        """
        conn = self._get_connection()

        # Extract the sequence number we embedded in this request's S7 header.
        # S7 header: 0x32 | pdu_type | reserved(2) | sequence(2) | ...
        expected_seq = struct.unpack(">H", request[4:6])[0]

        async with self._lock:
            await self._send_data(conn, request)

            for attempt in range(max_stale_retries + 1):
                response_data = await conn.receive_data()
                response = self.protocol.parse_response(response_data)

                resp_seq = response.get("sequence", 0)
                if resp_seq == expected_seq:
                    return response

                # Stale packet — response is for an older request
                if attempt < max_stale_retries:
                    logger.warning(
                        f"Stale packet: expected seq {expected_seq}, got {resp_seq} "
                        f"(attempt {attempt + 1}/{max_stale_retries}), retrying receive"
                    )
                    continue
                raise S7ProtocolError(f"Max stale packet retries ({max_stale_retries}) exceeded")

        raise S7ProtocolError("Failed to receive valid response")  # Should not reach here

    async def connect(self, address: str, rack: int, slot: int, tcp_port: int = 102) -> "AsyncClient":
        """Connect to S7 PLC.

        Args:
            address: PLC IP address
            rack: Rack number
            slot: Slot number
            tcp_port: TCP port (default 102)

        Returns:
            Self for method chaining
        """
        self.host = address
        self.port = tcp_port
        self.rack = rack
        self.slot = slot
        self._params[Parameter.RemotePort] = tcp_port

        self.remote_tsap = (self.connection_type << 8) | (rack << 5) | slot

        try:
            start_time = time.time()

            self.connection = AsyncISOTCPConnection(
                host=address, port=tcp_port, local_tsap=self.local_tsap, remote_tsap=self.remote_tsap
            )

            await self.connection.connect()

            await self._setup_communication()

            self.connected = True
            self._exec_time = int((time.time() - start_time) * 1000)
            logger.info(f"Connected to {address}:{tcp_port} rack {rack} slot {slot}")

        except Exception as e:
            await self.disconnect()
            if isinstance(e, S7Error):
                raise
            else:
                raise S7ConnectionError(f"Connection failed: {e}")

        return self

    async def disconnect(self) -> int:
        """Disconnect from S7 PLC.

        Returns:
            0 on success
        """
        if self.connection:
            await self.connection.disconnect()
            self.connection = None

        self.connected = False
        logger.info(f"Disconnected from {self.host}:{self.port}")
        return 0

    def get_connected(self) -> bool:
        """Check if client is connected."""
        return self.connected and self.connection is not None and self.connection.connected

    # ---------------------------------------------------------------
    # DB helpers
    # ---------------------------------------------------------------

    async def db_read(self, db_number: int, start: int, size: int) -> bytearray:
        """Read data from DB.

        Args:
            db_number: DB number to read from
            start: Start byte offset
            size: Number of bytes to read

        Returns:
            Data read from DB
        """
        logger.debug(f"db_read: DB{db_number}, start={start}, size={size}")
        return await self.read_area(Area.DB, db_number, start, size)

    async def db_write(self, db_number: int, start: int, data: bytearray) -> int:
        """Write data to DB.

        Args:
            db_number: DB number to write to
            start: Start byte offset
            data: Data to write

        Returns:
            0 on success
        """
        logger.debug(f"db_write: DB{db_number}, start={start}, size={len(data)}")
        await self.write_area(Area.DB, db_number, start, data)
        return 0

    # ---------------------------------------------------------------
    # Typed DB access and tag helpers (parity with the sync Client)
    # ---------------------------------------------------------------

    async def db_read_array(self, db_number: int, start: int, count: int, fmt: str = ">f") -> list[Any]:
        """Read *count* consecutive values of struct format *fmt* from a DB."""
        item_size = struct.calcsize(fmt)
        data = await self.db_read(db_number, start, item_size * count)
        return [struct.unpack_from(fmt, data, i * item_size)[0] for i in range(count)]

    async def db_write_array(self, db_number: int, start: int, values: list[Any], fmt: str = ">f") -> int:
        """Write *values* packed with struct format *fmt* to a DB. Returns 0 on success."""
        item_size = struct.calcsize(fmt)
        data = bytearray(item_size * len(values))
        for i, v in enumerate(values):
            struct.pack_into(fmt, data, i * item_size, v)
        return await self.db_write(db_number, start, data)

    async def db_read_bool(self, db_number: int, byte_offset: int, bit_offset: int) -> bool:
        """Read a single bit from a DB."""
        from .util import get_bool

        data = await self.db_read(db_number, byte_offset, 1)
        return get_bool(data, 0, bit_offset)

    async def db_write_bool(self, db_number: int, byte_offset: int, bit_offset: int, value: bool) -> None:
        """Write a single bit to a DB, preserving the other bits in the byte."""
        from .util import set_bool

        data = await self.db_read(db_number, byte_offset, 1)
        set_bool(data, 0, bit_offset, value)
        await self.db_write(db_number, byte_offset, data)

    async def db_read_byte(self, db_number: int, offset: int) -> int:
        """Read a BYTE (8-bit unsigned) from a DB."""
        data = await self.db_read(db_number, offset, 1)
        return data[0]

    async def db_write_byte(self, db_number: int, offset: int, value: int) -> None:
        """Write a BYTE (8-bit unsigned) to a DB."""
        from .util import set_byte

        data = bytearray(1)
        set_byte(data, 0, value)
        await self.db_write(db_number, offset, data)

    async def db_read_int(self, db_number: int, offset: int) -> int:
        """Read an INT (16-bit signed) from a DB."""
        from .util import get_int

        return get_int(await self.db_read(db_number, offset, 2), 0)

    async def db_write_int(self, db_number: int, offset: int, value: int) -> None:
        """Write an INT (16-bit signed) to a DB."""
        from .util import set_int

        data = bytearray(2)
        set_int(data, 0, value)
        await self.db_write(db_number, offset, data)

    async def db_read_uint(self, db_number: int, offset: int) -> int:
        """Read a UINT (16-bit unsigned) from a DB."""
        from .util import get_uint

        return get_uint(await self.db_read(db_number, offset, 2), 0)

    async def db_write_uint(self, db_number: int, offset: int, value: int) -> None:
        """Write a UINT (16-bit unsigned) to a DB."""
        from .util import set_uint

        data = bytearray(2)
        set_uint(data, 0, value)
        await self.db_write(db_number, offset, data)

    async def db_read_word(self, db_number: int, offset: int) -> int:
        """Read a WORD (16-bit unsigned) from a DB."""
        data = await self.db_read(db_number, offset, 2)
        return (data[0] << 8) | data[1]

    async def db_write_word(self, db_number: int, offset: int, value: int) -> None:
        """Write a WORD (16-bit unsigned) to a DB."""
        from .util import set_word

        data = bytearray(2)
        set_word(data, 0, value)
        await self.db_write(db_number, offset, data)

    async def db_read_dint(self, db_number: int, offset: int) -> int:
        """Read a DINT (32-bit signed) from a DB."""
        from .util import get_dint

        return get_dint(await self.db_read(db_number, offset, 4), 0)

    async def db_write_dint(self, db_number: int, offset: int, value: int) -> None:
        """Write a DINT (32-bit signed) to a DB."""
        from .util import set_dint

        data = bytearray(4)
        set_dint(data, 0, value)
        await self.db_write(db_number, offset, data)

    async def db_read_udint(self, db_number: int, offset: int) -> int:
        """Read a UDINT (32-bit unsigned) from a DB."""
        from .util import get_udint

        return get_udint(await self.db_read(db_number, offset, 4), 0)

    async def db_write_udint(self, db_number: int, offset: int, value: int) -> None:
        """Write a UDINT (32-bit unsigned) to a DB."""
        from .util import set_udint

        data = bytearray(4)
        set_udint(data, 0, value)
        await self.db_write(db_number, offset, data)

    async def db_read_dword(self, db_number: int, offset: int) -> int:
        """Read a DWORD (32-bit unsigned) from a DB."""
        from .util import get_dword

        return get_dword(await self.db_read(db_number, offset, 4), 0)

    async def db_write_dword(self, db_number: int, offset: int, value: int) -> None:
        """Write a DWORD (32-bit unsigned) to a DB."""
        from .util import set_dword

        data = bytearray(4)
        set_dword(data, 0, value)
        await self.db_write(db_number, offset, data)

    async def db_read_real(self, db_number: int, offset: int) -> float:
        """Read a REAL (32-bit float) from a DB."""
        from .util import get_real

        return get_real(await self.db_read(db_number, offset, 4), 0)

    async def db_write_real(self, db_number: int, offset: int, value: float) -> None:
        """Write a REAL (32-bit float) to a DB."""
        from .util import set_real

        data = bytearray(4)
        set_real(data, 0, value)
        await self.db_write(db_number, offset, data)

    async def db_read_lreal(self, db_number: int, offset: int) -> float:
        """Read a LREAL (64-bit float) from a DB."""
        from .util import get_lreal

        return get_lreal(await self.db_read(db_number, offset, 8), 0)

    async def db_write_lreal(self, db_number: int, offset: int, value: float) -> None:
        """Write a LREAL (64-bit float) to a DB."""
        from .util import set_lreal

        data = bytearray(8)
        set_lreal(data, 0, value)
        await self.db_write(db_number, offset, data)

    async def db_read_string(self, db_number: int, offset: int) -> str:
        """Read an S7 STRING from a DB (header first to learn the max length)."""
        from .util import get_string

        header = await self.db_read(db_number, offset, 2)
        data = await self.db_read(db_number, offset, 2 + header[0])
        return get_string(data, 0)

    async def db_write_string(self, db_number: int, offset: int, value: str, max_length: int = 254) -> None:
        """Write an S7 STRING with the given maximum length to a DB."""
        from .util import set_string

        data = bytearray(2 + max_length)
        set_string(data, 0, value, max_length)
        await self.db_write(db_number, offset, data)

    async def db_read_wstring(self, db_number: int, offset: int) -> str:
        """Read an S7 WSTRING from a DB (header first to learn the max length)."""
        from .util import get_wstring

        header = await self.db_read(db_number, offset, 4)
        max_len = (header[0] << 8) | header[1]
        data = await self.db_read(db_number, offset, 4 + max_len * 2)
        return get_wstring(data, 0)

    async def db_write_wstring(self, db_number: int, offset: int, value: str, max_length: int = 254) -> None:
        """Write an S7 WSTRING with the given maximum length (in characters) to a DB."""
        from .util import set_wstring

        data = bytearray(4 + max_length * 2)
        set_wstring(data, 0, value, max_length)
        await self.db_write(db_number, offset, data)

    async def read_tag(self, tag: "Union[Tag, str]", encoding: str = "latin-1") -> Any:
        """Read a typed value by :class:`~snap7.tags.Tag` or PLC4X-style address string."""
        resolved = Tag.from_string(tag) if isinstance(tag, str) else tag
        if resolved.is_symbolic:
            raise NotImplementedError("Symbolic (LID-based) tag access is not supported by the classic S7 client.")
        data = await self.read_area(Area(resolved.area), resolved.db_number, resolved.byte_offset, resolved.size)
        return _decode_tag(resolved, bytearray(data), encoding=encoding)

    async def write_tag(self, tag: "Union[Tag, str]", value: Any, encoding: str = "latin-1") -> int:
        """Write a typed value by :class:`~snap7.tags.Tag` or address string. Returns 0 on success."""
        resolved = Tag.from_string(tag) if isinstance(tag, str) else tag
        if resolved.is_symbolic:
            raise NotImplementedError("Symbolic (LID-based) tag access is not supported by the classic S7 client.")
        buf = bytearray(resolved.size)
        if resolved.datatype.upper() == "BOOL":
            # Preserve the other bits of the byte
            current = await self.read_area(Area(resolved.area), resolved.db_number, resolved.byte_offset, 1)
            buf[0] = current[0]
        _encode_tag(resolved, buf, value, encoding=encoding)
        return await self.write_area(Area(resolved.area), resolved.db_number, resolved.byte_offset, buf)

    async def read_tags(self, tags: "Sequence[Union[Tag, str]]", encoding: str = "latin-1") -> list[Any]:
        """Read multiple tags in a single optimized request, in input order."""
        resolved = [Tag.from_string(t) if isinstance(t, str) else t for t in tags]
        items = [{"area": Area(t.area), "db_number": t.db_number, "start": t.byte_offset, "size": t.size} for t in resolved]
        _code, data_list = await self.read_multi_vars(items)
        return [_decode_tag(t, bytearray(d), encoding=encoding) for t, d in zip(resolved, data_list)]

    async def db_get(self, db_number: int, size: int = 0) -> bytearray:
        """Get entire DB.

        Args:
            db_number: DB number to read
            size: DB size in bytes. If 0, determined via get_block_info().

        Returns:
            Entire DB contents
        """
        if size <= 0:
            block_info = await self.get_block_info(Block.DB, db_number)
            size = block_info.MC7Size if block_info.MC7Size > 0 else 65536
        return await self.db_read(db_number, 0, size)

    async def db_fill(self, db_number: int, filler: int, size: int = 0) -> int:
        """Fill a DB with a filler byte.

        Args:
            db_number: DB number to fill
            filler: Byte value to fill with
            size: DB size in bytes. If 0, determined via get_block_info().

        Returns:
            0 on success
        """
        if size <= 0:
            block_info = await self.get_block_info(Block.DB, db_number)
            size = block_info.MC7Size if block_info.MC7Size > 0 else 65536
        data = bytearray([filler] * size)
        return await self.db_write(db_number, 0, data)

    # ---------------------------------------------------------------
    # Core read / write
    # ---------------------------------------------------------------

    @_instrumented("read_area")
    async def read_area(self, area: Area, db_number: int, start: int, size: int) -> bytearray:
        """Read data from memory area.

        Automatically splits into multiple requests if size exceeds PDU capacity.
        """
        start_time = time.time()
        s7_area = self._map_area(area)

        if area == Area.TM:
            word_len = S7WordLen.TIMER
        elif area == Area.CT:
            word_len = S7WordLen.COUNTER
        else:
            word_len = S7WordLen.BYTE

        max_chunk = self._read_chunk_count(word_len)
        if size <= max_chunk:
            request = self.protocol.build_read_request(
                area=s7_area, db_number=db_number, start=start, word_len=word_len, count=size
            )
            response = await self._send_receive(request)
            values = self.protocol.extract_read_data(response, word_len, size)
            self._exec_time = int((time.time() - start_time) * 1000)
            return bytearray(values)

        result = bytearray()
        offset = 0
        remaining = size
        while remaining > 0:
            chunk_size = min(remaining, max_chunk)
            request = self.protocol.build_read_request(
                area=s7_area,
                db_number=db_number,
                start=start + offset * self._element_address_step(word_len),
                word_len=word_len,
                count=chunk_size,
            )
            response = await self._send_receive(request)
            values = self.protocol.extract_read_data(response, word_len, chunk_size)
            result.extend(values)
            offset += chunk_size
            remaining -= chunk_size

        self._exec_time = int((time.time() - start_time) * 1000)
        return result

    @_instrumented("write_area")
    async def write_area(self, area: Area, db_number: int, start: int, data: bytearray) -> int:
        """Write data to memory area.

        Automatically splits into multiple requests if data exceeds PDU capacity.
        """
        start_time = time.time()
        s7_area = self._map_area(area)

        if area == Area.TM:
            word_len = S7WordLen.TIMER
        elif area == Area.CT:
            word_len = S7WordLen.COUNTER
        else:
            word_len = S7WordLen.BYTE

        max_chunk = self._write_chunk_bytes(word_len, len(data))
        if len(data) <= max_chunk:
            request = self.protocol.build_write_request(
                area=s7_area, db_number=db_number, start=start, word_len=word_len, data=bytes(data)
            )
            response = await self._send_receive(request)
            self.protocol.check_write_response(response)
            self._exec_time = int((time.time() - start_time) * 1000)
            return 0

        offset = 0
        remaining = len(data)
        while remaining > 0:
            chunk_size = min(remaining, max_chunk)
            chunk_data = data[offset : offset + chunk_size]
            request = self.protocol.build_write_request(
                area=s7_area,
                db_number=db_number,
                start=start + offset // S7DataTypes.get_size_bytes(word_len) * self._element_address_step(word_len),
                word_len=word_len,
                data=bytes(chunk_data),
            )
            response = await self._send_receive(request)
            self.protocol.check_write_response(response)
            offset += chunk_size
            remaining -= chunk_size

        self._exec_time = int((time.time() - start_time) * 1000)
        return 0

    @_instrumented("read_multi_vars")
    async def read_multi_vars(self, items: List[dict[str, Any]]) -> Tuple[int, list[bytearray]]:
        """Read multiple variables (sequentially, one read_area per item).

        Args:
            items: List of item dicts with keys: area, db_number, start, size

        Returns:
            Tuple of (result_code, list_of_bytearrays)
        """
        if not items:
            return (0, [])
        if len(items) > self.MAX_VARS:
            raise ValueError(f"Too many items: {len(items)} exceeds MAX_VARS ({self.MAX_VARS})")

        results: list[bytearray] = []
        for item in items:
            area = item["area"]
            db_number = item.get("db_number", 0)
            start = item["start"]
            size = item["size"]
            data = await self.read_area(area, db_number, start, size)
            results.append(data)
        return (0, results)

    @_instrumented("write_multi_vars")
    async def write_multi_vars(self, items: List[dict[str, Any]]) -> int:
        """Write multiple variables (sequentially, one write_area per item).

        Args:
            items: List of item dicts with keys: area, db_number, start, data

        Returns:
            0 on success
        """
        if not items:
            return 0
        if len(items) > self.MAX_VARS:
            raise ValueError(f"Too many items: {len(items)} exceeds MAX_VARS ({self.MAX_VARS})")

        for item in items:
            area = item["area"]
            db_number = item.get("db_number", 0)
            start = item["start"]
            data = item["data"]
            await self.write_area(area, db_number, start, data)
        return 0

    # ---------------------------------------------------------------
    # Block operations
    # ---------------------------------------------------------------

    async def list_blocks(self) -> BlocksList:
        """List blocks available in PLC."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        request = self.protocol.build_list_blocks_request()
        response = await self._send_receive(request)
        self.protocol.check_userdata_response(response, S7UserDataGroup.BLOCK_INFO, S7UserDataSubfunction.LIST_ALL)

        data_info = response.get("data", {})
        return_code = data_info.get("return_code", 0xFF) if isinstance(data_info, dict) else 0xFF
        if return_code != 0xFF:
            desc = get_return_code_description(return_code)
            raise S7ProtocolError(f"List blocks failed: {desc} (0x{return_code:02x})")

        return self.protocol.parse_list_blocks(response)

    async def list_blocks_of_type(self, block_type: Block, max_count: int) -> List[int]:
        """List blocks of a specific type.

        Supports multi-packet responses.
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        conn = self._get_connection()

        block_type_codes = {
            Block.OB: 0x38,
            Block.DB: 0x41,
            Block.SDB: 0x42,
            Block.FC: 0x43,
            Block.SFC: 0x44,
            Block.FB: 0x45,
            Block.SFB: 0x46,
        }
        type_code = block_type_codes.get(block_type, 0x41)

        request = self.protocol.build_list_blocks_of_type_request(type_code)
        response = await self._send_receive(request)
        self.protocol.check_userdata_response(response, S7UserDataGroup.BLOCK_INFO, S7UserDataSubfunction.LIST_BLOCKS_OF_TYPE)

        data_info = response.get("data", {})
        return_code = data_info.get("return_code", 0xFF) if isinstance(data_info, dict) else 0xFF
        if return_code != 0xFF:
            desc = get_return_code_description(return_code)
            raise S7ProtocolError(f"List blocks of type failed: {desc} (0x{return_code:02x})")

        accumulated_data = bytearray(data_info.get("data", b"") if isinstance(data_info, dict) else b"")

        params = response.get("parameters", {})
        last_data_unit = params.get("last_data_unit", 0x00) if isinstance(params, dict) else 0x00
        sequence_number = params.get("sequence_number", 0) if isinstance(params, dict) else 0
        group = params.get("group", 0x03) if isinstance(params, dict) else 0x03
        subfunction = params.get("subfunction", 0x02) if isinstance(params, dict) else 0x02

        for _ in range(100):
            if last_data_unit == 0x00:
                break

            async with self._lock:
                followup = self.protocol.build_userdata_followup_request(group, subfunction, sequence_number)
                await self._send_data(conn, followup)
                response_data = await conn.receive_data()

            response = self.protocol.parse_response(response_data)
            self.protocol.check_userdata_response(response, S7UserDataGroup.BLOCK_INFO, S7UserDataSubfunction.LIST_BLOCKS_OF_TYPE)

            data_info = response.get("data", {})
            return_code = data_info.get("return_code", 0xFF) if isinstance(data_info, dict) else 0xFF
            if return_code != 0xFF:
                break

            accumulated_data.extend(data_info.get("data", b"") if isinstance(data_info, dict) else b"")

            params = response.get("parameters", {})
            last_data_unit = params.get("last_data_unit", 0x00) if isinstance(params, dict) else 0x00
            sequence_number = params.get("sequence_number", 0) if isinstance(params, dict) else 0

        combined_response: dict[str, Any] = {"data": {"data": bytes(accumulated_data)}}
        block_numbers = self.protocol.parse_list_blocks_of_type_response(combined_response)

        return block_numbers[:max_count]

    async def get_block_info(self, block_type: Block, db_number: int) -> TS7BlockInfo:
        """Get block information."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        block_type_map = {
            Block.OB: 0x38,
            Block.DB: 0x41,
            Block.SDB: 0x42,
            Block.FC: 0x43,
            Block.SFC: 0x44,
            Block.FB: 0x45,
            Block.SFB: 0x46,
        }
        type_code = block_type_map.get(block_type, 0x41)

        request = self.protocol.build_get_block_info_request(type_code, db_number)
        response = await self._send_receive(request)
        self.protocol.check_userdata_response(response, S7UserDataGroup.BLOCK_INFO, S7UserDataSubfunction.BLOCK_INFO)

        data_info = response.get("data", {})
        return_code = data_info.get("return_code", 0xFF) if isinstance(data_info, dict) else 0xFF
        if return_code != 0xFF:
            desc = get_return_code_description(return_code)
            raise S7ProtocolError(f"Get block info failed: {desc} (0x{return_code:02x})")

        return self.protocol.parse_get_block_info(response)

    # ---------------------------------------------------------------
    # CPU info / state
    # ---------------------------------------------------------------

    async def get_cpu_info(self) -> S7CpuInfo:
        """Get CPU component identification (SZL 0x001C)."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")
        return parse_cpu_info_szl(await self.read_szl(0x001C, 0))

    async def get_cpu_state(self) -> str:
        """Get CPU state (running/stopped)."""
        request = self.protocol.build_cpu_state_request()
        response = await self._send_receive(request)
        return self.protocol.extract_cpu_state(response)

    # ---------------------------------------------------------------
    # Upload / Download / Delete
    # ---------------------------------------------------------------

    @_instrumented("upload")
    async def upload(self, block_num: int) -> bytearray:
        """Upload block from PLC (3-step: START_UPLOAD, UPLOAD, END_UPLOAD)."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        block_type = 0x41  # DB

        request = self.protocol.build_start_upload_request(block_type, block_num)
        response = await self._send_receive(request)

        upload_info = self.protocol.parse_start_upload_response(response)
        upload_id = upload_info["upload_id"]

        block_data = bytearray()
        for fragment_index in range(1000):
            request = self.protocol.build_upload_request(upload_id)
            response = await self._send_receive(request)
            fragment, is_last = self.protocol.parse_upload_fragment(response, first_fragment=fragment_index == 0)
            block_data.extend(fragment)
            if is_last:
                break
        else:
            raise S7ProtocolError("Upload response exceeded fragment limit")

        request = self.protocol.build_end_upload_request(upload_id)
        response = await self._send_receive(request)
        self.protocol.check_end_upload_response(response)

        logger.info(f"Uploaded {len(block_data)} bytes from block {block_num}")
        return block_data

    @_instrumented("download")
    async def download(self, data: bytearray, block_num: int = -1) -> int:
        """Download block to PLC."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        conn = self._get_connection()
        block_type = 0x41  # DB

        if block_num == -1:
            if len(data) >= 8:
                block_num = struct.unpack(">H", data[6:8])[0]
            else:
                block_num = 1

        request = self.protocol.build_download_request(block_type, block_num, bytes(data))
        async with self._lock:
            await self._send_data(conn, request)
            response_data = await conn.receive_data()
            response = self.protocol.parse_response(response_data)
            if response["sequence"] != int.from_bytes(request[4:6], "big") or response.get("raw_parameters") != bytes((0x1A,)):
                raise S7ProtocolError("Invalid request-download acknowledgement")

            offset = 0
            max_slice = self.pdu_length - 18
            if max_slice <= 0:
                raise S7ProtocolError("Negotiated PDU is too small for download")
            for _ in range(1000):
                request_data = await conn.receive_data()
                sequence = self.protocol.parse_download_service_request(request_data, 0x1B, block_num)
                fragment = bytes(data[offset : offset + max_slice])
                offset += len(fragment)
                is_last = offset == len(data)
                await self._send_data(conn, self.protocol.build_download_fragment_response(sequence, is_last, fragment))
                if is_last:
                    break
            else:
                raise S7ProtocolError("Download exceeded fragment limit")

            request_data = await conn.receive_data()
            sequence = self.protocol.parse_download_service_request(request_data, 0x1C, block_num)
            await self._send_data(conn, self.protocol.build_download_ended_response(sequence))

        logger.info(f"Downloaded {len(data)} bytes to block {block_num}")
        return 0

    async def delete(self, block_type: Block, block_num: int) -> int:
        """Delete a block from PLC."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        block_type_map = {
            Block.OB: 0x38,
            Block.DB: 0x41,
            Block.SDB: 0x42,
            Block.FC: 0x43,
            Block.SFC: 0x44,
            Block.FB: 0x45,
            Block.SFB: 0x46,
        }
        type_code = block_type_map.get(block_type, 0x41)

        request = self.protocol.build_delete_block_request(type_code, block_num)
        response = await self._send_receive(request)
        self.protocol.check_control_response(response)

        logger.info(f"Deleted block {block_type.name} {block_num}")
        return 0

    async def full_upload(self, block_type: Block, block_num: int) -> Tuple[bytearray, int]:
        """Upload a block from PLC with header and footer info."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        block_type_map = {
            Block.OB: 0x38,
            Block.DB: 0x41,
            Block.SDB: 0x42,
            Block.FC: 0x43,
            Block.SFC: 0x44,
            Block.FB: 0x45,
            Block.SFB: 0x46,
        }
        type_code = block_type_map.get(block_type, 0x41)

        request = self.protocol.build_start_upload_request(type_code, block_num)
        response = await self._send_receive(request)

        upload_info = self.protocol.parse_start_upload_response(response)
        upload_id = upload_info["upload_id"]

        block_data = bytearray()
        for fragment_index in range(1000):
            request = self.protocol.build_upload_request(upload_id)
            response = await self._send_receive(request)
            fragment, is_last = self.protocol.parse_upload_fragment(
                response, first_fragment=fragment_index == 0, include_block_header=True
            )
            block_data.extend(fragment)
            if is_last:
                break
        else:
            raise S7ProtocolError("Upload response exceeded fragment limit")

        request = self.protocol.build_end_upload_request(upload_id)
        response = await self._send_receive(request)
        self.protocol.check_end_upload_response(response)

        logger.info(f"Full upload of block {block_type.name} {block_num}: {len(block_data)} bytes")
        return block_data, len(block_data)

    # ---------------------------------------------------------------
    # PLC control
    # ---------------------------------------------------------------

    async def plc_stop(self) -> int:
        """Stop PLC CPU."""
        request = self.protocol.build_plc_control_request("stop")
        response = await self._send_receive(request)
        self.protocol.check_control_response(response)
        return 0

    async def plc_hot_start(self) -> int:
        """Hot start PLC CPU."""
        request = self.protocol.build_plc_control_request("hot_start")
        response = await self._send_receive(request)
        self.protocol.check_control_response(response)
        return 0

    async def plc_cold_start(self) -> int:
        """Cold start PLC CPU."""
        request = self.protocol.build_plc_control_request("cold_start")
        response = await self._send_receive(request)
        self.protocol.check_control_response(response)
        return 0

    # ---------------------------------------------------------------
    # Date / time
    # ---------------------------------------------------------------

    async def get_plc_datetime(self) -> datetime:
        """Get PLC date/time."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        request = self.protocol.build_get_clock_request()
        response = await self._send_receive(request)
        self.protocol.check_userdata_response(response, S7UserDataGroup.TIME, S7UserDataSubfunction.GET_CLOCK)
        return self.protocol.parse_get_clock_response(response)

    async def set_plc_datetime(self, dt: datetime) -> int:
        """Set PLC date/time."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        request = self.protocol.build_set_clock_request(dt)
        response = await self._send_receive(request)
        self.protocol.check_userdata_response(response, S7UserDataGroup.TIME, S7UserDataSubfunction.SET_CLOCK)
        logger.info(f"Set PLC datetime to {dt}")
        return 0

    async def set_plc_system_datetime(self) -> int:
        """Set PLC time to system time."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        current_time = datetime.now()
        await self.set_plc_datetime(current_time)
        logger.info(f"Set PLC time to current system time: {current_time}")
        return 0

    # ---------------------------------------------------------------
    # SZL
    # ---------------------------------------------------------------

    async def read_szl(self, ssl_id: int, index: int = 0) -> S7SZL:
        """Read SZL (System Status List).

        Supports multi-packet responses.
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        conn = self._get_connection()

        request = self.protocol.build_read_szl_request(ssl_id, index)
        response = await self._send_receive(request)
        self.protocol.check_userdata_response(response, S7UserDataGroup.SZL, S7UserDataSubfunction.READ_SZL)

        data_info = response.get("data", {})
        return_code = data_info.get("return_code", 0xFF) if isinstance(data_info, dict) else 0xFF
        if return_code != 0xFF:
            desc = get_return_code_description(return_code)
            raise RuntimeError(f"Read SZL failed: {desc} (0x{return_code:02x})")

        szl_result = self.protocol.parse_read_szl_response(response)
        accumulated_data = bytearray(szl_result["data"])

        params = response.get("parameters", {})
        last_data_unit = params.get("last_data_unit", 0x00) if isinstance(params, dict) else 0x00
        sequence_number = params.get("sequence_number", 0) if isinstance(params, dict) else 0
        group = params.get("group", 0x04) if isinstance(params, dict) else 0x04
        subfunction = params.get("subfunction", 0x01) if isinstance(params, dict) else 0x01

        for _ in range(100):
            if last_data_unit == 0x00:
                break

            async with self._lock:
                followup = self.protocol.build_userdata_followup_request(group, subfunction, sequence_number)
                await self._send_data(conn, followup)
                response_data = await conn.receive_data()

            response = self.protocol.parse_response(response_data)
            self.protocol.check_userdata_response(response, S7UserDataGroup.SZL, S7UserDataSubfunction.READ_SZL)

            data_info = response.get("data", {})
            return_code = data_info.get("return_code", 0xFF) if isinstance(data_info, dict) else 0xFF
            if return_code != 0xFF:
                break

            fragment = self.protocol.parse_read_szl_response(response, first_fragment=False)
            accumulated_data.extend(fragment["data"])

            params = response.get("parameters", {})
            last_data_unit = params.get("last_data_unit", 0x00) if isinstance(params, dict) else 0x00
            sequence_number = params.get("sequence_number", 0) if isinstance(params, dict) else 0

        szl = S7SZL()
        szl.Header.LengthDR = len(accumulated_data)
        szl.Header.NDR = 1

        for i, b in enumerate(accumulated_data[: min(len(accumulated_data), len(szl.Data))]):
            szl.Data[i] = b

        return szl

    async def read_szl_list(self) -> bytes:
        """Read list of available SZL IDs."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        szl = await self.read_szl(0x0000, 0)
        return bytes(szl.Data[: szl.Header.LengthDR])

    # ---------------------------------------------------------------
    # Misc info
    # ---------------------------------------------------------------

    async def get_cp_info(self) -> S7CpInfo:
        """Get communication processor info (SZL 0x0131)."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")
        return parse_cp_info_szl(await self.read_szl(0x0131, 0))

    async def get_order_code(self) -> S7OrderCode:
        """Get module order code and firmware version (SZL 0x0011)."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")
        return parse_order_code_szl(await self.read_szl(0x0011, 0))

    async def get_protection(self) -> S7Protection:
        """Get protection settings (SZL 0x0232)."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")
        return parse_protection_szl(await self.read_szl(0x0232, 0))

    # ---------------------------------------------------------------
    # Force I/O
    # ---------------------------------------------------------------

    _FORCE_AREAS: frozenset[int] = frozenset({Area.PE, Area.PA})

    async def force_bit(self, area: Area, byte_offset: int, bit: int, value: bool) -> None:
        """Force a single I/O bit in the process image.

        Async equivalent of :meth:`snap7.client.Client.force_bit`.
        """
        if area not in self._FORCE_AREAS:
            raise ValueError(f"Force is only supported for PE (inputs) and PA (outputs), got {area!r}")
        if not 0 <= bit <= 7:
            raise ValueError(f"Bit must be 0-7, got {bit}")

        current = await self.read_area(area, 0, byte_offset, 1)
        if value:
            current[0] |= 1 << bit
        else:
            current[0] &= ~(1 << bit)
        await self.write_area(area, 0, byte_offset, current)
        logger.info(f"Forced {area.name} byte {byte_offset} bit {bit} = {value}")

    async def cancel_force(self, area: Area, byte_offset: int, bit: int) -> None:
        """Cancel a forced I/O bit by clearing it in the process image.

        Async equivalent of :meth:`snap7.client.Client.cancel_force`.
        """
        if area not in self._FORCE_AREAS:
            raise ValueError(f"Cancel force is only supported for PE (inputs) and PA (outputs), got {area!r}")
        if not 0 <= bit <= 7:
            raise ValueError(f"Bit must be 0-7, got {bit}")

        current = await self.read_area(area, 0, byte_offset, 1)
        current[0] &= ~(1 << bit)
        await self.write_area(area, 0, byte_offset, current)
        logger.info(f"Cancelled force on {area.name} byte {byte_offset} bit {bit}")

    async def read_force_table(self) -> list[ForceEntry]:
        """Read the PLC force table via SZL 0x0025.

        Async equivalent of :meth:`snap7.client.Client.read_force_table`.
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        try:
            szl = await self.read_szl(0x0025, 0x0000)
        except (S7ProtocolError, RuntimeError):
            logger.debug("SZL 0x0025 not available; returning empty force table")
            return []

        raw = bytes(szl.Data[: szl.Header.LengthDR])
        return _parse_force_szl(raw)

    async def set_session_password(self, password: str) -> int:
        """Set the session password to unlock a password-protected PLC.

        Sends an S7 USERDATA request (function group 5, subfunction 1)
        with the encoded password.

        Args:
            password: Plaintext password (max 8 ASCII characters).

        Returns:
            0 on success.

        Raises:
            ~snap7.error.S7ConnectionError: If not connected.
            ~snap7.error.S7ProtocolError: If the PLC rejects the password.
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        encoded = self.protocol.encode_password(password)
        request = self.protocol.build_set_session_password_request(encoded)
        response = await self._send_receive(request)
        self.protocol.check_userdata_response(response, S7UserDataGroup.SECURITY, S7UserDataSubfunction.SET_SESSION_PASSWORD)
        logger.info("Session password set successfully")
        return 0

    async def clear_session_password(self) -> int:
        """Clear the session password, returning to the default protection level.

        Sends an S7 USERDATA request (function group 5, subfunction 2).

        Returns:
            0 on success.

        Raises:
            ~snap7.error.S7ConnectionError: If not connected.
            ~snap7.error.S7ProtocolError: If the PLC rejects the request.
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        request = self.protocol.build_clear_session_password_request()
        response = await self._send_receive(request)
        self.protocol.check_userdata_response(response, S7UserDataGroup.SECURITY, S7UserDataSubfunction.CLEAR_SESSION_PASSWORD)
        logger.info("Session password cleared successfully")
        return 0

    async def compress(self, timeout: int) -> int:
        """Compress PLC memory."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        request = self.protocol.build_compress_request()
        response = await self._send_receive(request)
        self.protocol.check_control_response(response)
        logger.info(f"Compress PLC memory completed (timeout={timeout}ms)")
        return 0

    async def copy_ram_to_rom(self, timeout: int = 0) -> int:
        """Copy RAM to ROM."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        request = self.protocol.build_copy_ram_to_rom_request()
        response = await self._send_receive(request)
        self.protocol.check_control_response(response)
        logger.info(f"Copy RAM to ROM completed (timeout={timeout}ms)")
        return 0

    async def iso_exchange_buffer(self, data: bytearray) -> bytearray:
        """Exchange raw ISO PDU."""
        conn = self._get_connection()

        async with self._lock:
            await self._send_data(conn, bytes(data))
            response = await conn.receive_data()
        return bytearray(response)

    # ---------------------------------------------------------------
    # Convenience memory area methods
    # ---------------------------------------------------------------

    async def ab_read(self, start: int, size: int) -> bytearray:
        """Read from process output area (PA)."""
        return await self.read_area(Area.PA, 0, start, size)

    async def ab_write(self, start: int, data: bytearray) -> int:
        """Write to process output area (PA)."""
        return await self.write_area(Area.PA, 0, start, data)

    async def eb_read(self, start: int, size: int) -> bytearray:
        """Read from process input area (PE)."""
        return await self.read_area(Area.PE, 0, start, size)

    async def eb_write(self, start: int, size: int, data: bytearray) -> int:
        """Write to process input area (PE)."""
        return await self.write_area(Area.PE, 0, start, data[:size])

    async def mb_read(self, start: int, size: int) -> bytearray:
        """Read from marker/flag area (MK)."""
        return await self.read_area(Area.MK, 0, start, size)

    async def mb_write(self, start: int, size: int, data: bytearray) -> int:
        """Write to marker/flag area (MK)."""
        return await self.write_area(Area.MK, 0, start, data[:size])

    async def tm_read(self, start: int, size: int) -> bytearray:
        """Read from timer area (TM)."""
        return await self.read_area(Area.TM, 0, start, size)

    async def tm_write(self, start: int, size: int, data: bytearray) -> int:
        """Write to timer area (TM)."""
        if len(data) != size * 2:
            raise ValueError(f"Data length {len(data)} doesn't match size {size * 2}")
        try:
            return await self.write_area(Area.TM, 0, start, data)
        except S7ProtocolError as e:
            raise RuntimeError(str(e)) from e

    async def ct_read(self, start: int, size: int) -> bytearray:
        """Read from counter area (CT)."""
        return await self.read_area(Area.CT, 0, start, size)

    async def ct_write(self, start: int, size: int, data: bytearray) -> int:
        """Write to counter area (CT)."""
        if len(data) != size * 2:
            raise ValueError(f"Data length {len(data)} doesn't match size {size * 2}")
        return await self.write_area(Area.CT, 0, start, data)

    # ---------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------

    async def _setup_communication(self) -> None:
        """Setup communication and negotiate PDU length."""
        request = self.protocol.build_setup_communication_request(max_amq_caller=1, max_amq_callee=1, pdu_length=self.pdu_length)
        response = await self._send_receive(request)

        if response.get("parameters"):
            params = response["parameters"]
            if "pdu_length" in params:
                negotiated = params["pdu_length"]
                if negotiated < 64:
                    logger.warning(f"Server negotiated implausible PDU length {negotiated}, using minimum 240")
                    negotiated = 240
                self.pdu_length = negotiated
                self._params[Parameter.PDURequest] = self.pdu_length
                logger.info(f"Negotiated PDU length: {self.pdu_length}")

    # ---------------------------------------------------------------
    # Context manager
    # ---------------------------------------------------------------

    async def __aenter__(self) -> "AsyncClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
