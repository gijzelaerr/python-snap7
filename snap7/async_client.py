"""
Legacy async S7 client implementation.

Uses asyncio streams for non-blocking I/O with an asyncio.Lock() to serialize
send/receive cycles, ensuring safe concurrent use via asyncio.gather().

For new projects, use :class:`s7.AsyncClient` instead, which supports all PLC
models and automatically selects the best protocol.
"""

import asyncio
import logging
import struct
import time
from typing import List, Any, Optional, Tuple, Type
from types import TracebackType
from datetime import datetime

from .connection import TPDUSize
from .s7protocol import S7Protocol, get_return_code_description
from .datatypes import S7WordLen
from .error import S7Error, S7ConnectionError, S7ProtocolError, S7TimeoutError
from .client_base import ClientMixin
from .type import (
    Area,
    Block,
    BlocksList,
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
            if remaining <= 0:
                raise S7ConnectionError("Invalid TPKT length")

            payload = await self._recv_exact(remaining)

            # Parse COTP DT header
            if len(payload) < 3:
                raise S7ConnectionError("Invalid COTP DT: too short")
            pdu_len, pdu_type, eot_num = struct.unpack(">BBB", payload[:3])
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
                    self.pdu_size = 1 << param_data[0]
                elif param_len == 2:
                    self.pdu_size = struct.unpack(">H", param_data)[0]
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
    """
    Legacy async S7 client for classic PUT/GET communication.

    Uses asyncio streams for non-blocking I/O. An internal asyncio.Lock
    serializes each send+receive cycle so that concurrent coroutines
    (e.g. via asyncio.gather) never interleave on the same TCP socket.

    For new projects, use :class:`s7.AsyncClient` instead.

    Examples:
        >>> from s7 import AsyncClient
        >>> async with AsyncClient() as client:
        ...     await client.connect("192.168.1.10", 0, 1)
        ...     data = await client.db_read(1, 0, 4)
    """

    MAX_VARS = 20

    def __init__(self) -> None:
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

        self._lock = asyncio.Lock()

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
            await conn.send_data(request)

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

        self.remote_tsap = 0x0100 | (rack << 5) | slot

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

        max_chunk = self._max_read_size()
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
                area=s7_area, db_number=db_number, start=start + offset, word_len=word_len, count=chunk_size
            )
            response = await self._send_receive(request)
            values = self.protocol.extract_read_data(response, word_len, chunk_size)
            result.extend(values)
            offset += chunk_size
            remaining -= chunk_size

        self._exec_time = int((time.time() - start_time) * 1000)
        return result

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

        max_chunk = self._max_write_size()
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
                area=s7_area, db_number=db_number, start=start + offset, word_len=word_len, data=bytes(chunk_data)
            )
            response = await self._send_receive(request)
            self.protocol.check_write_response(response)
            offset += chunk_size
            remaining -= chunk_size

        self._exec_time = int((time.time() - start_time) * 1000)
        return 0

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

        data_info = response.get("data", {})
        return_code = data_info.get("return_code", 0xFF) if isinstance(data_info, dict) else 0xFF
        if return_code != 0xFF:
            desc = get_return_code_description(return_code)
            raise S7ProtocolError(f"List blocks failed: {desc} (0x{return_code:02x})")

        counts = self.protocol.parse_list_blocks_response(response)

        block_list = BlocksList()
        block_list.OBCount = counts.get("OBCount", 0)
        block_list.FBCount = counts.get("FBCount", 0)
        block_list.FCCount = counts.get("FCCount", 0)
        block_list.SFBCount = counts.get("SFBCount", 0)
        block_list.SFCCount = counts.get("SFCCount", 0)
        block_list.DBCount = counts.get("DBCount", 0)
        block_list.SDBCount = counts.get("SDBCount", 0)

        return block_list

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
                await conn.send_data(followup)
                response_data = await conn.receive_data()

            response = self.protocol.parse_response(response_data)

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

        data_info = response.get("data", {})
        return_code = data_info.get("return_code", 0xFF) if isinstance(data_info, dict) else 0xFF
        if return_code != 0xFF:
            desc = get_return_code_description(return_code)
            raise S7ProtocolError(f"Get block info failed: {desc} (0x{return_code:02x})")

        info = self.protocol.parse_get_block_info_response(response)

        block_info = TS7BlockInfo()
        block_info.BlkType = info["block_type"]
        block_info.BlkNumber = info["block_number"]
        block_info.BlkLang = info["block_lang"]
        block_info.BlkFlags = info["block_flags"]
        block_info.MC7Size = info["mc7_size"]
        block_info.LoadSize = info["load_size"]
        block_info.LocalData = info["local_data"]
        block_info.SBBLength = info["sbb_length"]
        block_info.CheckSum = info["checksum"]
        block_info.Version = info["version"]

        if info["code_date"]:
            block_info.CodeDate = info["code_date"][:10]
        if info["intf_date"]:
            block_info.IntfDate = info["intf_date"][:10]
        if info["author"]:
            block_info.Author = info["author"][:8]
        if info["family"]:
            block_info.Family = info["family"][:8]
        if info["header"]:
            block_info.Header = info["header"][:8]

        return block_info

    # ---------------------------------------------------------------
    # CPU info / state
    # ---------------------------------------------------------------

    async def get_cpu_info(self) -> S7CpuInfo:
        """Get CPU information.

        Uses read_szl(0x001C) to get component identification data. The
        SZL 0x001C response is a sequence of (index:2, data:N) records,
        not a flat struct, so fields sit at offsets relative to each
        record header. See the fix in #694 for the sync client — this
        mirrors those offsets.
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        szl = await self.read_szl(0x001C, 0)

        cpu_info = S7CpuInfo()
        data = bytes(szl.Data[: szl.Header.LengthDR])

        if len(data) >= 30:
            cpu_info.ASName = data[6:30].rstrip(b"\x00")
        if len(data) >= 64:
            cpu_info.ModuleName = data[40:64].rstrip(b"\x00")
        if len(data) >= 134:
            cpu_info.Copyright = data[108:134].rstrip(b"\x00")
        if len(data) >= 166:
            cpu_info.SerialNumber = data[142:166].rstrip(b"\x00")
        if len(data) >= 208:
            cpu_info.ModuleTypeName = data[176:208].rstrip(b"\x00")

        return cpu_info

    async def get_cpu_state(self) -> str:
        """Get CPU state (running/stopped)."""
        request = self.protocol.build_cpu_state_request()
        response = await self._send_receive(request)
        return self.protocol.extract_cpu_state(response)

    # ---------------------------------------------------------------
    # Upload / Download / Delete
    # ---------------------------------------------------------------

    async def upload(self, block_num: int) -> bytearray:
        """Upload block from PLC (3-step: START_UPLOAD, UPLOAD, END_UPLOAD)."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        block_type = 0x41  # DB

        request = self.protocol.build_start_upload_request(block_type, block_num)
        response = await self._send_receive(request)

        upload_info = self.protocol.parse_start_upload_response(response)
        upload_id = upload_info.get("upload_id", 1)

        request = self.protocol.build_upload_request(upload_id)
        response = await self._send_receive(request)

        block_data = self.protocol.parse_upload_response(response)

        request = self.protocol.build_end_upload_request(upload_id)
        response = await self._send_receive(request)

        logger.info(f"Uploaded {len(block_data)} bytes from block {block_num}")
        return bytearray(block_data)

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

        # Step 1: Request download
        request = self.protocol.build_download_request(block_type, block_num, bytes(data))
        await self._send_receive(request)

        # Step 2: Download block (send data)
        param_data = struct.pack(">BBB", 0x1B, 0x01, 0x00)
        data_section = struct.pack(">HH", len(data), 0x00FB) + bytes(data)
        header = struct.pack(
            ">BBHHHH",
            0x32,
            0x01,
            0x0000,
            self.protocol._next_sequence(),
            len(param_data),
            len(data_section),
        )

        async with self._lock:
            await conn.send_data(header + param_data + data_section)
            response_data = await conn.receive_data()
        self.protocol.parse_response(response_data)

        # Step 3: Download ended
        param_data = struct.pack(">B", 0x1C)
        header = struct.pack(
            ">BBHHHH",
            0x32,
            0x01,
            0x0000,
            self.protocol._next_sequence(),
            len(param_data),
            0x0000,
        )

        async with self._lock:
            await conn.send_data(header + param_data)
            response_data = await conn.receive_data()
        self.protocol.parse_response(response_data)

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
        upload_id = upload_info.get("upload_id", 1)

        request = self.protocol.build_upload_request(upload_id)
        response = await self._send_receive(request)
        block_data = self.protocol.parse_upload_response(response)

        request = self.protocol.build_end_upload_request(upload_id)
        response = await self._send_receive(request)

        block_header = struct.pack(
            ">BBHBBBBHH",
            0x70,
            block_type.value,
            block_num,
            0x00,
            0x00,
            0x00,
            0x00,
            len(block_data) + 14,
            len(block_data),
        )
        block_footer = b"\x00" * 4
        full_block = bytearray(block_header + block_data + block_footer)

        logger.info(f"Full upload of block {block_type.name} {block_num}: {len(full_block)} bytes")
        return full_block, len(full_block)

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
        return self.protocol.parse_get_clock_response(response)

    async def set_plc_datetime(self, dt: datetime) -> int:
        """Set PLC date/time."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        request = self.protocol.build_set_clock_request(dt)
        await self._send_receive(request)
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
                await conn.send_data(followup)
                response_data = await conn.receive_data()

            response = self.protocol.parse_response(response_data)

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
        """Get CP (Communication Processor) information."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        szl = await self.read_szl(0x0131, 0)

        cp_info = S7CpInfo()
        data = bytearray(b & 0xFF for b in szl.Data[: szl.Header.LengthDR])

        if len(data) >= 2:
            cp_info.MaxPduLength = struct.unpack(">H", data[0:2])[0]
        if len(data) >= 4:
            cp_info.MaxConnections = struct.unpack(">H", data[2:4])[0]
        if len(data) >= 6:
            cp_info.MaxMpiRate = struct.unpack(">H", data[4:6])[0]
        if len(data) >= 8:
            cp_info.MaxBusRate = struct.unpack(">H", data[6:8])[0]

        return cp_info

    async def get_order_code(self) -> S7OrderCode:
        """Get order code."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        szl = await self.read_szl(0x0011, 0)

        order_code = S7OrderCode()
        data = bytes(szl.Data[: szl.Header.LengthDR])

        if len(data) >= 20:
            order_code.OrderCode = data[0:20].rstrip(b"\x00")
        if len(data) >= 21:
            order_code.V1 = data[20]
        if len(data) >= 22:
            order_code.V2 = data[21]
        if len(data) >= 23:
            order_code.V3 = data[22]

        return order_code

    async def get_protection(self) -> S7Protection:
        """Get protection settings."""
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        szl = await self.read_szl(0x0232, 0)

        protection = S7Protection()
        data = bytes(szl.Data[: szl.Header.LengthDR])

        if len(data) >= 2:
            protection.sch_schal = struct.unpack(">H", data[0:2])[0]
        if len(data) >= 4:
            protection.sch_par = struct.unpack(">H", data[2:4])[0]
        if len(data) >= 6:
            protection.sch_rel = struct.unpack(">H", data[4:6])[0]
        if len(data) >= 8:
            protection.bart_sch = struct.unpack(">H", data[6:8])[0]
        if len(data) >= 10:
            protection.anl_sch = struct.unpack(">H", data[8:10])[0]

        return protection

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
            await conn.send_data(bytes(data))
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
                self.pdu_length = params["pdu_length"]
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
