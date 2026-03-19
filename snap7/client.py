"""
Pure Python S7 client implementation.

Drop-in replacement for the ctypes-based client with native Python implementation.
"""

import logging
import struct
import time
from typing import List, Any, Optional, Tuple, Union, Callable, cast
from datetime import datetime
from ctypes import (
    c_int,
    Array,
    memmove,
)

from .connection import ISOTCPConnection
from .s7protocol import S7Protocol, get_return_code_description
from .datatypes import S7WordLen
from .error import S7Error, S7ConnectionError, S7ProtocolError, S7StalePacketError
from .client_base import ClientMixin
from .optimizer import ReadItem, ReadPacket, sort_items, merge_items, packetize, extract_results

from .type import (
    Area,
    Block,
    BlocksList,
    S7CpuInfo,
    TS7BlockInfo,
    S7DataItem,
    S7CpInfo,
    S7OrderCode,
    S7Protection,
    S7SZL,
    S7SZLList,
    WordLen,
    Parameter,
    CDataArrayType,
)

logger = logging.getLogger(__name__)


class _OptimizationPlan:
    """Cached optimization plan for repeated read_multi_vars calls with the same layout."""

    def __init__(self, cache_key: tuple[int, ...], packets: list[ReadPacket], read_items: list[ReadItem]):
        self.cache_key = cache_key
        self.packets = packets
        self.read_items = read_items


class Client(ClientMixin):
    """
    Pure Python S7 client implementation.

    Drop-in replacement for the ctypes-based client that provides native Python
    communication with Siemens S7 PLCs without requiring the Snap7 C library.

    Examples:
        >>> import snap7
        >>> client = snap7.Client()
        >>> client.connect("192.168.1.10", 0, 1)
        >>> data = client.db_read(1, 0, 4)
        >>> client.disconnect()
    """

    MAX_VARS = 20  # Max variables per multi-read/multi-write request

    def __init__(self, lib_location: Optional[str] = None, **kwargs: Any):
        """
        Initialize S7 client.

        Args:
            lib_location: Ignored. Kept for backwards compatibility.
            **kwargs: Ignored. Kept for backwards compatibility.
        """
        self.connection: Optional[ISOTCPConnection] = None
        self.protocol = S7Protocol()
        self.connected = False
        self.host = ""
        self.port = 102
        self.rack = 0
        self.slot = 0
        self.pdu_length = 480  # Negotiated PDU length

        # Connection parameters
        self.local_tsap = 0x0100  # Default local TSAP
        self.remote_tsap = 0x0102  # Default remote TSAP
        self.connection_type = 1  # PG

        # Session password
        self.session_password: Optional[str] = None

        # Execution time tracking
        self._exec_time = 0
        self.last_error = 0

        # Parameter storage
        self._params = {
            Parameter.LocalPort: 0,
            Parameter.RemotePort: 102,
            Parameter.PingTimeout: 750,
            Parameter.SendTimeout: 10,
            Parameter.RecvTimeout: 3000,
            Parameter.SrcRef: 256,
            Parameter.DstRef: 0,
            Parameter.SrcTSap: 256,
            Parameter.PDURequest: 480,
        }

        # Multi-read optimizer state
        self._opt_plan: Optional[_OptimizationPlan] = None
        self.multi_read_max_gap: int = 5

        # Async operation state
        self._async_pending = False
        self._async_result: Optional[bytearray] = None
        self._async_error: Optional[int] = None
        self._last_error = 0
        self._exec_time = 0

        logger.info("S7Client initialized (pure Python implementation)")

    def _get_connection(self) -> ISOTCPConnection:
        """Get connection, raising if not connected."""
        if self.connection is None:
            raise S7ConnectionError("Not connected to PLC")
        return self.connection

    def _send_receive(self, request: bytes, max_stale_retries: int = 3) -> dict[str, Any]:
        """Send a request and receive/parse the response with stale packet retry.

        Wraps the repeated send_data -> receive_data -> parse_response pattern
        with PDU reference validation and automatic retry on stale packets.

        Args:
            request: Complete S7 PDU to send.
            max_stale_retries: Max times to retry receive on stale packets.

        Returns:
            Parsed S7 response dict.

        Raises:
            S7PacketLostError: If a packet loss is detected.
            S7ProtocolError: If all retries are exhausted or other protocol error.
        """
        conn = self._get_connection()
        conn.send_data(request)

        for attempt in range(max_stale_retries + 1):
            response_data = conn.receive_data()
            response = self.protocol.parse_response(response_data)

            try:
                self.protocol.validate_pdu_reference(response["sequence"])
                return response
            except S7StalePacketError:
                if attempt < max_stale_retries:
                    logger.warning(f"Stale packet (attempt {attempt + 1}/{max_stale_retries}), retrying receive")
                    continue
                raise S7ProtocolError(f"Max stale packet retries ({max_stale_retries}) exceeded")

        raise S7ProtocolError("Failed to receive valid response")  # Should not reach here

    def connect(self, address: str, rack: int, slot: int, tcp_port: int = 102) -> "Client":
        """
        Connect to S7 PLC.

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

        # Calculate TSAP values from rack/slot
        # Remote TSAP: rack and slot encoded as per S7 specification
        self.remote_tsap = 0x0100 | (rack << 5) | slot

        try:
            start_time = time.time()

            # Establish ISO on TCP connection
            self.connection = ISOTCPConnection(
                host=address, port=tcp_port, local_tsap=self.local_tsap, remote_tsap=self.remote_tsap
            )

            self.connection.connect()

            # Setup communication and negotiate PDU length
            self._setup_communication()

            self.connected = True
            self._exec_time = int((time.time() - start_time) * 1000)
            logger.info(f"Connected to {address}:{tcp_port} rack {rack} slot {slot}")

        except Exception as e:
            self.disconnect()
            if isinstance(e, S7Error):
                raise
            else:
                raise S7ConnectionError(f"Connection failed: {e}")

        return self

    def disconnect(self) -> int:
        """Disconnect from S7 PLC.

        Returns:
            0 on success
        """
        if self.connection:
            self.connection.disconnect()
            self.connection = None

        self.connected = False
        logger.info(f"Disconnected from {self.host}:{self.port}")
        return 0

    def create(self) -> None:
        """Create client instance (no-op for compatibility)."""
        pass

    def destroy(self) -> None:
        """Destroy client instance."""
        self.disconnect()

    def get_connected(self) -> bool:
        """Check if client is connected to PLC.

        Performs an active check on the underlying TCP socket to detect
        broken connections, rather than just checking a cached flag.
        """
        if not self.connected or self.connection is None:
            return False
        return self.connection.check_connection()

    def db_read(self, db_number: int, start: int, size: int) -> bytearray:
        """
        Read data from DB.

        Args:
            db_number: DB number to read from
            start: Start byte offset
            size: Number of bytes to read

        Returns:
            Data read from DB
        """
        logger.debug(f"db_read: DB{db_number}, start={start}, size={size}")

        data = self.read_area(Area.DB, db_number, start, size)
        return data

    def db_write(self, db_number: int, start: int, data: bytearray) -> int:
        """
        Write data to DB.

        Args:
            db_number: DB number to write to
            start: Start byte offset
            data: Data to write

        Returns:
            0 on success
        """
        logger.debug(f"db_write: DB{db_number}, start={start}, size={len(data)}")

        self.write_area(Area.DB, db_number, start, data)
        return 0

    def db_get(self, db_number: int, size: int = 0) -> bytearray:
        """
        Get entire DB.

        Uses get_block_info() to determine the DB size automatically.
        If the PLC does not support get_block_info() or reports an
        incorrect size (common on S7-1200/1500), pass the size parameter
        explicitly.

        Args:
            db_number: DB number to read
            size: DB size in bytes. If 0, the size is determined
                automatically via get_block_info().

        Returns:
            Entire DB contents
        """
        if size <= 0:
            block_info = self.get_block_info(Block.DB, db_number)
            size = block_info.MC7Size if block_info.MC7Size > 0 else 65536
        try:
            return self.db_read(db_number, 0, size)
        except S7Error:
            raise S7Error(
                f"db_get failed for DB{db_number} with auto-detected size {size}. "
                f"Some PLCs (e.g. S7-1200) report incorrect MC7Size in block info. "
                f"Try passing the actual DB size explicitly: client.db_get({db_number}, size=<actual_size>)"
            )

    def db_fill(self, db_number: int, filler: int, size: int = 0) -> int:
        """
        Fill a DB with a filler byte.

        Uses get_block_info() to determine the DB size automatically.
        If the PLC does not support get_block_info() or reports an
        incorrect size (common on S7-1200/1500), pass the size parameter
        explicitly.

        Args:
            db_number: DB number to fill
            filler: Byte value to fill with
            size: DB size in bytes. If 0, the size is determined
                automatically via get_block_info().

        Returns:
            0 on success
        """
        if size <= 0:
            block_info = self.get_block_info(Block.DB, db_number)
            size = block_info.MC7Size if block_info.MC7Size > 0 else 65536
        data = bytearray([filler] * size)
        try:
            return self.db_write(db_number, 0, data)
        except S7Error:
            raise S7Error(
                f"db_fill failed for DB{db_number} with auto-detected size {size}. "
                f"Some PLCs (e.g. S7-1200) report incorrect MC7Size in block info. "
                f"Try passing the actual DB size explicitly: client.db_fill({db_number}, {filler}, size=<actual_size>)"
            )

    def read_area(self, area: Area, db_number: int, start: int, size: int, word_len: Optional[WordLen] = None) -> bytearray:
        """
        Read data from memory area.

        Automatically splits into multiple requests if size exceeds PDU capacity.

        Args:
            area: Memory area to read from
            db_number: DB number (for DB area only)
            start: Start address
            size: Number of items to read (for TM/CT: timers/counters, for others: bytes)
            word_len: Optional word length override. If None, defaults to area-based logic
                (TIMER for TM, COUNTER for CT, BYTE for others).

        Returns:
            Data read from area
        """
        start_time = time.time()

        # Map area enum to native area
        s7_area = self._map_area(area)

        # Determine word length
        if word_len is not None:
            s7_word_len = S7WordLen(word_len)
        elif area == Area.TM:
            s7_word_len = S7WordLen.TIMER
        elif area == Area.CT:
            s7_word_len = S7WordLen.COUNTER
        else:
            s7_word_len = S7WordLen.BYTE

        max_chunk = self._max_read_size()
        if size <= max_chunk:
            # Single request
            request = self.protocol.build_read_request(
                area=s7_area, db_number=db_number, start=start, word_len=s7_word_len, count=size
            )
            response = self._send_receive(request)
            values = self.protocol.extract_read_data(response, s7_word_len, size)
            self._exec_time = int((time.time() - start_time) * 1000)
            return bytearray(values)

        # Split into chunks
        result = bytearray()
        offset = 0
        remaining = size
        while remaining > 0:
            chunk_size = min(remaining, max_chunk)
            request = self.protocol.build_read_request(
                area=s7_area, db_number=db_number, start=start + offset, word_len=s7_word_len, count=chunk_size
            )
            response = self._send_receive(request)
            values = self.protocol.extract_read_data(response, s7_word_len, chunk_size)
            result.extend(values)
            offset += chunk_size
            remaining -= chunk_size

        self._exec_time = int((time.time() - start_time) * 1000)
        return result

    def write_area(self, area: Area, db_number: int, start: int, data: bytearray, word_len: Optional[WordLen] = None) -> int:
        """
        Write data to memory area.

        Automatically splits into multiple requests if data exceeds PDU capacity.

        Args:
            area: Memory area to write to
            db_number: DB number (for DB area only)
            start: Start address
            data: Data to write
            word_len: Optional word length override. If None, defaults to area-based logic
                (TIMER for TM, COUNTER for CT, BYTE for others).

        Returns:
            0 on success
        """
        start_time = time.time()

        # Map area enum to native area
        s7_area = self._map_area(area)

        # Determine word length
        if word_len is not None:
            s7_word_len = S7WordLen(word_len)
        elif area == Area.TM:
            s7_word_len = S7WordLen.TIMER
        elif area == Area.CT:
            s7_word_len = S7WordLen.COUNTER
        else:
            s7_word_len = S7WordLen.BYTE

        max_chunk = self._max_write_size()
        if len(data) <= max_chunk:
            # Single request
            request = self.protocol.build_write_request(
                area=s7_area, db_number=db_number, start=start, word_len=s7_word_len, data=bytes(data)
            )
            response = self._send_receive(request)
            self.protocol.check_write_response(response)
            self._exec_time = int((time.time() - start_time) * 1000)
            return 0

        # Split into chunks
        offset = 0
        remaining = len(data)
        while remaining > 0:
            chunk_size = min(remaining, max_chunk)
            chunk_data = data[offset : offset + chunk_size]
            request = self.protocol.build_write_request(
                area=s7_area, db_number=db_number, start=start + offset, word_len=s7_word_len, data=bytes(chunk_data)
            )
            response = self._send_receive(request)
            self.protocol.check_write_response(response)
            offset += chunk_size
            remaining -= chunk_size

        self._exec_time = int((time.time() - start_time) * 1000)
        return 0

    def read_multi_vars(self, items: Union[List[dict[str, Any]], "Array[S7DataItem]"]) -> Tuple[int, Any]:
        """Read multiple variables in a single request.

        When given a list of dicts with two or more items, uses the multi-variable
        read optimizer to merge adjacent reads and pack them into minimal PDU
        exchanges.  This significantly reduces the number of round-trips compared
        to reading each variable individually.

        Args:
            items: List of item specifications (dicts with ``area``, ``start``,
                ``size``, and optionally ``db_number``) **or** a ctypes
                ``Array[S7DataItem]``.

        Returns:
            Tuple of (result_code, data) where *data* is either the updated
            ctypes array or a list of bytearrays in the original item order.

        Raises:
            ValueError: If more than MAX_VARS items are requested.
        """
        if not items:
            return (0, items)

        if len(items) > self.MAX_VARS:
            raise ValueError(f"Too many items: {len(items)} exceeds MAX_VARS ({self.MAX_VARS})")

        # Handle S7DataItem array (ctypes) -- unchanged legacy path
        if hasattr(items, "_type_") and hasattr(items[0], "Area"):
            s7_items = cast("Array[S7DataItem]", items)
            for s7_item in s7_items:
                area = Area(s7_item.Area)
                db_number = s7_item.DBNumber
                start = s7_item.Start
                size = s7_item.Amount
                data = self.read_area(area, db_number, start, size)
                if s7_item.pData:
                    for i, b in enumerate(data):
                        s7_item.pData[i] = b
            return (0, items)

        # Dict list path -- use optimizer for 2+ items
        dict_items = cast(List[dict[str, Any]], items)

        if len(dict_items) <= 1:
            # Single item: no optimization needed
            results: list[bytearray] = []
            for dict_item in dict_items:
                area = dict_item["area"]
                db_number = dict_item.get("db_number", 0)
                start = dict_item["start"]
                size = dict_item["size"]
                data = self.read_area(area, db_number, start, size)
                results.append(data)
            return (0, results)

        return self._read_multi_vars_optimized(dict_items)

    def _read_multi_vars_optimized(self, dict_items: List[dict[str, Any]]) -> Tuple[int, List[bytearray]]:
        """Optimized multi-variable read using merge + packetize strategy.

        Args:
            dict_items: List of item dicts (area, db_number, start, size).

        Returns:
            Tuple of (0, list of bytearrays in original order).
        """
        # Build ReadItem list
        read_items: list[ReadItem] = []
        for idx, d in enumerate(dict_items):
            area_val = int(d["area"])
            db_number = d.get("db_number", 0)
            read_items.append(
                ReadItem(
                    area=area_val,
                    db_number=db_number,
                    byte_offset=d["start"],
                    bit_offset=0,
                    byte_length=d["size"],
                    index=idx,
                )
            )

        # Build cache key from the item layout
        cache_key = tuple(val for ri in read_items for val in (ri.area, ri.db_number, ri.byte_offset, ri.byte_length))

        # Reuse cached plan if layout matches
        if self._opt_plan is not None and self._opt_plan.cache_key == cache_key:
            packets = self._opt_plan.packets
        else:
            sorted_ri = sort_items(read_items)
            max_block = self._max_read_size()
            blocks = merge_items(sorted_ri, max_gap=self.multi_read_max_gap, max_block_size=max_block)
            packets = packetize(blocks, self.pdu_length)
            self._opt_plan = _OptimizationPlan(cache_key, packets, read_items)

        # Execute each packet
        for packet in packets:
            block_specs = [(blk.area, blk.db_number, blk.start_offset, blk.byte_length) for blk in packet.blocks]

            if len(block_specs) == 1:
                # Single block: use regular read to avoid multi-read overhead
                blk = packet.blocks[0]
                data = self.read_area(
                    Area(blk.area) if blk.area in {a.value for a in Area} else Area.DB,
                    blk.db_number,
                    blk.start_offset,
                    blk.byte_length,
                )
                blk.buffer = data
            else:
                # Multi-block: use multi-read PDU
                request = self.protocol.build_multi_read_request(block_specs)
                response = self._send_receive(request)
                block_data_list = self.protocol.extract_multi_read_data(response, len(block_specs))
                for blk, buf in zip(packet.blocks, block_data_list):
                    blk.buffer = buf

        # Extract per-item results in original order
        results = extract_results(packets, len(dict_items))
        return (0, results)

    def _map_area_int(self, area_int: int) -> S7Area:
        """Map integer area value to S7Area enum."""
        return S7Area(area_int)

    def write_multi_vars(self, items: Union[List[dict[str, Any]], List[S7DataItem]]) -> int:
        """
        Write multiple variables in a single request.

        Args:
            items: List of item specifications with data

        Returns:
            0 on success

        Raises:
            ValueError: If more than MAX_VARS items are requested
        """
        if not items:
            return 0

        if len(items) > self.MAX_VARS:
            raise ValueError(f"Too many items: {len(items)} exceeds MAX_VARS ({self.MAX_VARS})")

        # Handle S7DataItem list (ctypes)
        if hasattr(items[0], "Area"):
            s7_items = cast(List[S7DataItem], items)
            for s7_item in s7_items:
                area = Area(s7_item.Area)
                db_number = s7_item.DBNumber
                start = s7_item.Start
                size = s7_item.Amount

                # Extract data from pData
                data = bytearray(size)
                if s7_item.pData:
                    for i in range(size):
                        data[i] = s7_item.pData[i]

                self.write_area(area, db_number, start, data)
            return 0

        # Handle dict list
        dict_items = cast(List[dict[str, Any]], items)
        for dict_item in dict_items:
            area = dict_item["area"]
            db_number = dict_item.get("db_number", 0)
            start = dict_item["start"]
            data = dict_item["data"]
            self.write_area(area, db_number, start, data)

        return 0

    def list_blocks(self) -> BlocksList:
        """
        List blocks available in PLC.

        Sends real S7 USER_DATA protocol request to server.

        Returns:
            Block list structure with counts for each block type
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        # Build and send list blocks request
        request = self.protocol.build_list_blocks_request()
        response = self._send_receive(request)

        # Check for errors in data section
        data_info = response.get("data", {})
        return_code = data_info.get("return_code", 0xFF) if isinstance(data_info, dict) else 0xFF
        if return_code != 0xFF:
            desc = get_return_code_description(return_code)
            raise S7ProtocolError(f"List blocks failed: {desc} (0x{return_code:02x})")

        # Parse block counts from response
        counts = self.protocol.parse_list_blocks_response(response)

        # Build BlocksList structure
        block_list = BlocksList()
        block_list.OBCount = counts.get("OBCount", 0)
        block_list.FBCount = counts.get("FBCount", 0)
        block_list.FCCount = counts.get("FCCount", 0)
        block_list.SFBCount = counts.get("SFBCount", 0)
        block_list.SFCCount = counts.get("SFCCount", 0)
        block_list.DBCount = counts.get("DBCount", 0)
        block_list.SDBCount = counts.get("SDBCount", 0)

        return block_list

    def list_blocks_of_type(self, block_type: Block, max_count: int) -> List[int]:
        """
        List blocks of a specific type.

        Sends real S7 USER_DATA protocol request to server.
        Supports multi-packet responses when the block list doesn't fit in one PDU.

        Args:
            block_type: Type of blocks to list
            max_count: Maximum number of blocks to return

        Returns:
            List of block numbers
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        conn = self._get_connection()

        # Map Block enum to S7 block type codes
        block_type_codes = {
            Block.OB: 0x38,  # Organization Block
            Block.DB: 0x41,  # Data Block
            Block.SDB: 0x42,  # System Data Block
            Block.FC: 0x43,  # Function
            Block.SFC: 0x44,  # System Function
            Block.FB: 0x45,  # Function Block
            Block.SFB: 0x46,  # System Function Block
        }

        type_code = block_type_codes.get(block_type, 0x41)  # Default to DB

        # Build and send list blocks of type request
        request = self.protocol.build_list_blocks_of_type_request(type_code)
        response = self._send_receive(request)

        # Check for errors in data section
        data_info = response.get("data", {})
        return_code = data_info.get("return_code", 0xFF) if isinstance(data_info, dict) else 0xFF
        if return_code != 0xFF:
            desc = get_return_code_description(return_code)
            raise S7ProtocolError(f"List blocks of type failed: {desc} (0x{return_code:02x})")

        # Accumulate raw data across fragments
        accumulated_data = bytearray(data_info.get("data", b"") if isinstance(data_info, dict) else b"")

        # Check for multi-packet response
        params = response.get("parameters", {})
        last_data_unit = params.get("last_data_unit", 0x00) if isinstance(params, dict) else 0x00
        sequence_number = params.get("sequence_number", 0) if isinstance(params, dict) else 0
        group = params.get("group", 0x03) if isinstance(params, dict) else 0x03
        subfunction = params.get("subfunction", 0x02) if isinstance(params, dict) else 0x02

        # Accumulate follow-up fragments
        for _ in range(100):  # Safety limit
            if last_data_unit == 0x00:
                break

            followup = self.protocol.build_userdata_followup_request(group, subfunction, sequence_number)
            conn.send_data(followup)

            response_data = conn.receive_data()
            response = self.protocol.parse_response(response_data)

            # Check for errors
            data_info = response.get("data", {})
            return_code = data_info.get("return_code", 0xFF) if isinstance(data_info, dict) else 0xFF
            if return_code != 0xFF:
                break

            accumulated_data.extend(data_info.get("data", b"") if isinstance(data_info, dict) else b"")

            # Update multi-packet state
            params = response.get("parameters", {})
            last_data_unit = params.get("last_data_unit", 0x00) if isinstance(params, dict) else 0x00
            sequence_number = params.get("sequence_number", 0) if isinstance(params, dict) else 0

        # Parse block numbers from accumulated data
        combined_response: dict[str, Any] = {"data": {"data": bytes(accumulated_data)}}
        block_numbers = self.protocol.parse_list_blocks_of_type_response(combined_response)

        # Limit to max_count
        return block_numbers[:max_count]

    def get_cpu_info(self) -> S7CpuInfo:
        """
        Get CPU information.

        Uses read_szl(0x001C) to get component identification data.

        Returns:
            CPU information structure
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        # Read SZL 0x001C for component identification
        szl = self.read_szl(0x001C, 0)

        # Parse SZL data into S7CpuInfo structure
        cpu_info = S7CpuInfo()
        data = bytes(szl.Data[: szl.Header.LengthDR])

        # S7CpuInfo field sizes (from C structure):
        # ModuleTypeName: 32 bytes
        # SerialNumber: 24 bytes
        # ASName: 24 bytes
        # Copyright: 26 bytes
        # ModuleName: 24 bytes
        if len(data) >= 32:
            cpu_info.ModuleTypeName = data[0:32].rstrip(b"\x00")
        if len(data) >= 56:
            cpu_info.SerialNumber = data[32:56].rstrip(b"\x00")
        if len(data) >= 80:
            cpu_info.ASName = data[56:80].rstrip(b"\x00")
        if len(data) >= 106:
            cpu_info.Copyright = data[80:106].rstrip(b"\x00")
        if len(data) >= 130:
            cpu_info.ModuleName = data[106:130].rstrip(b"\x00")

        return cpu_info

    def get_cpu_state(self) -> str:
        """
        Get CPU state (running/stopped).

        Returns:
            CPU state string
        """
        request = self.protocol.build_cpu_state_request()
        response = self._send_receive(request)

        return self.protocol.extract_cpu_state(response)

    def get_block_info(self, block_type: Block, db_number: int) -> TS7BlockInfo:
        """
        Get block information.

        Sends real S7 USER_DATA protocol request to server.

        Args:
            block_type: Type of block
            db_number: Block number

        Returns:
            Block information structure
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        # Map Block enum to S7 block type code
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

        # Build and send get block info request
        request = self.protocol.build_get_block_info_request(type_code, db_number)
        response = self._send_receive(request)

        # Check for errors in data section
        data_info = response.get("data", {})
        return_code = data_info.get("return_code", 0xFF) if isinstance(data_info, dict) else 0xFF
        if return_code != 0xFF:
            desc = get_return_code_description(return_code)
            raise S7ProtocolError(f"Get block info failed: {desc} (0x{return_code:02x})")

        # Parse block info response
        info = self.protocol.parse_get_block_info_response(response)

        # Build TS7BlockInfo structure
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

        # Copy date and string fields
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

    def upload(self, block_num: int) -> bytearray:
        """
        Upload block from PLC.

        Sends real S7 protocol requests: START_UPLOAD, UPLOAD, END_UPLOAD.

        Args:
            block_num: Block number to upload

        Returns:
            Block data
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        # Block type 0x41 = DB
        block_type = 0x41

        # Step 1: Start upload
        request = self.protocol.build_start_upload_request(block_type, block_num)
        response = self._send_receive(request)

        # Parse upload ID from response
        upload_info = self.protocol.parse_start_upload_response(response)
        upload_id = upload_info.get("upload_id", 1)

        # Step 2: Upload (get data)
        request = self.protocol.build_upload_request(upload_id)
        response = self._send_receive(request)

        # Extract block data
        block_data = self.protocol.parse_upload_response(response)

        # Step 3: End upload
        request = self.protocol.build_end_upload_request(upload_id)
        response = self._send_receive(request)

        logger.info(f"Uploaded {len(block_data)} bytes from block {block_num}")
        return bytearray(block_data)

    def download(self, data: bytearray, block_num: int = -1) -> int:
        """
        Download block to PLC.

        Sends real S7 protocol requests: REQUEST_DOWNLOAD, DOWNLOAD_BLOCK, DOWNLOAD_ENDED.

        Args:
            data: Block data to download
            block_num: Block number (-1 to extract from data)

        Returns:
            0 on success
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        conn = self._get_connection()

        # Block type 0x41 = DB
        block_type = 0x41

        # Extract block number from data if not specified
        if block_num == -1:
            if len(data) >= 8:
                block_num = struct.unpack(">H", data[6:8])[0]
            else:
                block_num = 1  # Default

        # Step 1: Request download
        request = self.protocol.build_download_request(block_type, block_num, bytes(data))
        self._send_receive(request)

        # Step 2: Download block (send data)
        # Build a simple download block PDU
        param_data = struct.pack(
            ">BBB",
            0x1B,  # S7Function.DOWNLOAD_BLOCK
            0x01,  # Status: last packet
            0x00,  # Reserved
        )

        # Data section: data to write
        data_section = struct.pack(">HH", len(data), 0x00FB) + bytes(data)

        header = struct.pack(
            ">BBHHHH",
            0x32,  # Protocol ID
            0x01,  # PDU type REQUEST
            0x0000,  # Reserved
            self.protocol._next_sequence(),  # Sequence
            len(param_data),  # Parameter length
            len(data_section),  # Data length
        )

        conn.send_data(header + param_data + data_section)

        response_data = conn.receive_data()
        self.protocol.parse_response(response_data)

        # Step 3: Download ended
        param_data = struct.pack(">B", 0x1C)  # S7Function.DOWNLOAD_ENDED

        header = struct.pack(
            ">BBHHHH",
            0x32,  # Protocol ID
            0x01,  # PDU type REQUEST
            0x0000,  # Reserved
            self.protocol._next_sequence(),  # Sequence
            len(param_data),  # Parameter length
            0x0000,  # Data length
        )

        conn.send_data(header + param_data)

        response_data = conn.receive_data()
        self.protocol.parse_response(response_data)

        logger.info(f"Downloaded {len(data)} bytes to block {block_num}")
        return 0

    def delete(self, block_type: Block, block_num: int) -> int:
        """Delete a block from PLC.

        Sends real S7 PLC_CONTROL protocol with PI service "_DELE".

        Args:
            block_type: Type of block (DB, OB, FB, FC, etc.)
            block_num: Block number to delete

        Returns:
            0 on success
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        # Map Block enum to S7 block type code
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

        # Build and send delete request
        request = self.protocol.build_delete_block_request(type_code, block_num)
        response = self._send_receive(request)
        self.protocol.check_control_response(response)

        logger.info(f"Deleted block {block_type.name} {block_num}")
        return 0

    def full_upload(self, block_type: Block, block_num: int) -> Tuple[bytearray, int]:
        """Upload a block from PLC with header and footer info.

        The whole block (including header and footer) is copied into the
        user buffer.

        Sends real S7 protocol requests: START_UPLOAD, UPLOAD, END_UPLOAD.

        Args:
            block_type: Type of block (DB, OB, FB, FC, etc.)
            block_num: Block number to upload

        Returns:
            Tuple of (buffer, size) where buffer contains the complete block
            with headers and size is the actual data length.
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        # Map Block enum to S7 block type code
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

        # Step 1: Start upload
        request = self.protocol.build_start_upload_request(type_code, block_num)
        response = self._send_receive(request)

        # Parse upload ID from response
        upload_info = self.protocol.parse_start_upload_response(response)
        upload_id = upload_info.get("upload_id", 1)

        # Step 2: Upload (get data)
        request = self.protocol.build_upload_request(upload_id)
        response = self._send_receive(request)

        # Extract block data
        block_data = self.protocol.parse_upload_response(response)

        # Step 3: End upload
        request = self.protocol.build_end_upload_request(upload_id)
        response = self._send_receive(request)

        # Build full block with MC7 header
        # S7 block structure: MC7 header + data + footer
        block_header = struct.pack(
            ">BBHBBBBHH",
            0x70,  # Block type marker
            block_type.value,  # Block type
            block_num,  # Block number
            0x00,  # Language
            0x00,  # Properties
            0x00,  # Reserved
            0x00,  # Reserved
            len(block_data) + 14,  # Block length (header + data + footer)
            len(block_data),  # MC7 code length
        )

        block_footer = b"\x00" * 4  # Footer

        full_block = bytearray(block_header + block_data + block_footer)
        logger.info(f"Full upload of block {block_type.name} {block_num}: {len(full_block)} bytes")
        return full_block, len(full_block)

    def plc_stop(self) -> int:
        """Stop PLC CPU.

        Returns:
            0 on success
        """
        request = self.protocol.build_plc_control_request("stop")
        response = self._send_receive(request)
        self.protocol.check_control_response(response)
        return 0

    def plc_hot_start(self) -> int:
        """Hot start PLC CPU.

        Returns:
            0 on success
        """
        request = self.protocol.build_plc_control_request("hot_start")
        response = self._send_receive(request)
        self.protocol.check_control_response(response)
        return 0

    def plc_cold_start(self) -> int:
        """Cold start PLC CPU.

        Returns:
            0 on success
        """
        request = self.protocol.build_plc_control_request("cold_start")
        response = self._send_receive(request)
        self.protocol.check_control_response(response)
        return 0

    def get_plc_datetime(self) -> datetime:
        """
        Get PLC date/time.

        Sends real S7 USER_DATA protocol request to server.

        Returns:
            PLC date and time
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        # Build and send get clock request
        request = self.protocol.build_get_clock_request()
        response = self._send_receive(request)

        # Parse clock response
        return self.protocol.parse_get_clock_response(response)

    def set_plc_datetime(self, dt: datetime) -> int:
        """
        Set PLC date/time.

        Sends real S7 USER_DATA protocol request to server.

        Args:
            dt: Date and time to set

        Returns:
            0 on success
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        # Build and send set clock request
        request = self.protocol.build_set_clock_request(dt)
        self._send_receive(request)

        logger.info(f"Set PLC datetime to {dt}")
        return 0

    def set_plc_system_datetime(self) -> int:
        """Set PLC time to system time.

        Returns:
            0 on success
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        current_time = datetime.now()
        self.set_plc_datetime(current_time)
        logger.info(f"Set PLC time to current system time: {current_time}")
        return 0

    def compress(self, timeout: int) -> int:
        """
        Compress PLC memory.

        Sends real S7 PLC_CONTROL protocol with PI service "_MSZL".

        Args:
            timeout: Timeout in milliseconds (used for receive timeout)

        Returns:
            0 on success
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        # Build and send compress request
        request = self.protocol.build_compress_request()
        response = self._send_receive(request)
        self.protocol.check_control_response(response)

        logger.info(f"Compress PLC memory completed (timeout={timeout}ms)")
        return 0

    def copy_ram_to_rom(self, timeout: int = 0) -> int:
        """
        Copy RAM to ROM.

        Sends real S7 PLC_CONTROL protocol with PI service "_MSZL" and file ID "P".

        Args:
            timeout: Timeout in milliseconds (used for receive timeout)

        Returns:
            0 on success
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        # Build and send copy RAM to ROM request
        request = self.protocol.build_copy_ram_to_rom_request()
        response = self._send_receive(request)
        self.protocol.check_control_response(response)

        logger.info(f"Copy RAM to ROM completed (timeout={timeout}ms)")
        return 0

    def get_cp_info(self) -> S7CpInfo:
        """
        Get CP (Communication Processor) information.

        Uses read_szl(0x0131) to get communication parameters.

        Returns:
            CP information structure
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        # Read SZL 0x0131 for communication parameters
        szl = self.read_szl(0x0131, 0)

        # Parse SZL data into S7CpInfo structure
        cp_info = S7CpInfo()
        # Use bytearray to handle c_byte (signed) values properly
        data = bytearray(b & 0xFF for b in szl.Data[: szl.Header.LengthDR])

        # S7CpInfo structure: 4 x uint16 (big-endian)
        if len(data) >= 2:
            cp_info.MaxPduLength = struct.unpack(">H", data[0:2])[0]
        if len(data) >= 4:
            cp_info.MaxConnections = struct.unpack(">H", data[2:4])[0]
        if len(data) >= 6:
            cp_info.MaxMpiRate = struct.unpack(">H", data[4:6])[0]
        if len(data) >= 8:
            cp_info.MaxBusRate = struct.unpack(">H", data[6:8])[0]

        return cp_info

    def get_order_code(self) -> S7OrderCode:
        """
        Get order code.

        Uses read_szl(0x0011) to get module identification.

        Returns:
            Order code structure
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        # Read SZL 0x0011 for module identification
        szl = self.read_szl(0x0011, 0)

        # Parse SZL data into S7OrderCode structure
        order_code = S7OrderCode()
        data = bytes(szl.Data[: szl.Header.LengthDR])

        # OrderCode: 20 bytes, Version: 4 bytes
        if len(data) >= 20:
            order_code.OrderCode = data[0:20].rstrip(b"\x00")
        if len(data) >= 21:
            order_code.V1 = data[20]
        if len(data) >= 22:
            order_code.V2 = data[21]
        if len(data) >= 23:
            order_code.V3 = data[22]

        return order_code

    def get_protection(self) -> S7Protection:
        """
        Get protection settings.

        Uses read_szl(0x0232) to get protection level.

        Returns:
            Protection structure
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        # Read SZL 0x0232 for protection level
        szl = self.read_szl(0x0232, 0)

        # Parse SZL data into S7Protection structure
        protection = S7Protection()
        data = bytes(szl.Data[: szl.Header.LengthDR])

        # S7Protection structure: 5 x uint16 (big-endian)
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

    def read_szl(self, ssl_id: int, index: int = 0) -> S7SZL:
        """
        Read SZL (System Status List).

        Sends real S7 USER_DATA protocol request to server.
        Supports multi-packet responses where SZL data spans multiple PDUs.

        Args:
            ssl_id: SZL ID
            index: SZL index

        Returns:
            SZL structure with header and data
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        conn = self._get_connection()

        # Build and send read SZL request
        request = self.protocol.build_read_szl_request(ssl_id, index)
        response = self._send_receive(request)

        # Check for errors in data section (for USERDATA - return_code != 0xFF means error)
        data_info = response.get("data", {})
        return_code = data_info.get("return_code", 0xFF) if isinstance(data_info, dict) else 0xFF
        if return_code != 0xFF:
            desc = get_return_code_description(return_code)
            raise RuntimeError(f"Read SZL failed: {desc} (0x{return_code:02x})")

        # Parse first fragment (includes SZL header)
        szl_result = self.protocol.parse_read_szl_response(response)
        accumulated_data = bytearray(szl_result["data"])

        # Check for multi-packet response
        params = response.get("parameters", {})
        last_data_unit = params.get("last_data_unit", 0x00) if isinstance(params, dict) else 0x00
        sequence_number = params.get("sequence_number", 0) if isinstance(params, dict) else 0
        group = params.get("group", 0x04) if isinstance(params, dict) else 0x04
        subfunction = params.get("subfunction", 0x01) if isinstance(params, dict) else 0x01

        # Accumulate follow-up fragments
        for _ in range(100):  # Safety limit
            if last_data_unit == 0x00:
                break

            followup = self.protocol.build_userdata_followup_request(group, subfunction, sequence_number)
            conn.send_data(followup)

            response_data = conn.receive_data()
            response = self.protocol.parse_response(response_data)

            # Check for errors
            data_info = response.get("data", {})
            return_code = data_info.get("return_code", 0xFF) if isinstance(data_info, dict) else 0xFF
            if return_code != 0xFF:
                break

            # Parse follow-up fragment (no SZL header)
            fragment = self.protocol.parse_read_szl_response(response, first_fragment=False)
            accumulated_data.extend(fragment["data"])

            # Update multi-packet state
            params = response.get("parameters", {})
            last_data_unit = params.get("last_data_unit", 0x00) if isinstance(params, dict) else 0x00
            sequence_number = params.get("sequence_number", 0) if isinstance(params, dict) else 0

        # Build S7SZL structure
        szl = S7SZL()
        szl.Header.LengthDR = len(accumulated_data)
        szl.Header.NDR = 1

        # Copy data to SZL.Data array
        for i, b in enumerate(accumulated_data[: min(len(accumulated_data), len(szl.Data))]):
            szl.Data[i] = b

        return szl

    def read_szl_list(self) -> bytes:
        """
        Read list of available SZL IDs.

        Sends real S7 USER_DATA protocol request to server.

        Returns:
            SZL list data
        """
        if not self.get_connected():
            raise S7ConnectionError("Not connected to PLC")

        # Read SZL ID 0x0000 to get list of available IDs
        szl = self.read_szl(0x0000, 0)

        # Return raw data
        return bytes(szl.Data[: szl.Header.LengthDR])

    def iso_exchange_buffer(self, data: bytearray) -> bytearray:
        """
        Exchange raw ISO PDU.

        Args:
            data: Raw PDU data

        Returns:
            Response PDU data
        """
        conn = self._get_connection()

        conn.send_data(bytes(data))
        response = conn.receive_data()
        return bytearray(response)

    # Convenience methods for specific memory areas

    def ab_read(self, start: int, size: int) -> bytearray:
        """Read from process output area (PA).

        Args:
            start: Start byte offset
            size: Number of bytes to read

        Returns:
            Data read from output area
        """
        return self.read_area(Area.PA, 0, start, size)

    def ab_write(self, start: int, data: bytearray) -> int:
        """Write to process output area (PA).

        Args:
            start: Start byte offset
            data: Data to write

        Returns:
            0 on success
        """
        return self.write_area(Area.PA, 0, start, data)

    def eb_read(self, start: int, size: int) -> bytearray:
        """Read from process input area (PE).

        Args:
            start: Start byte offset
            size: Number of bytes to read

        Returns:
            Data read from input area
        """
        return self.read_area(Area.PE, 0, start, size)

    def eb_write(self, start: int, size: int, data: bytearray) -> int:
        """Write to process input area (PE).

        Args:
            start: Start byte offset
            size: Number of bytes to write (must match len(data))
            data: Data to write

        Returns:
            0 on success
        """
        return self.write_area(Area.PE, 0, start, data[:size])

    def mb_read(self, start: int, size: int) -> bytearray:
        """Read from marker/flag area (MK).

        Args:
            start: Start byte offset
            size: Number of bytes to read

        Returns:
            Data read from marker area
        """
        return self.read_area(Area.MK, 0, start, size)

    def mb_write(self, start: int, size: int, data: bytearray) -> int:
        """Write to marker/flag area (MK).

        Args:
            start: Start byte offset
            size: Number of bytes to write (must match len(data))
            data: Data to write

        Returns:
            0 on success
        """
        return self.write_area(Area.MK, 0, start, data[:size])

    def tm_read(self, start: int, size: int) -> bytearray:
        """Read from timer area (TM).

        Args:
            start: Start offset
            size: Number of timers to read

        Returns:
            Timer data
        """
        return self.read_area(Area.TM, 0, start, size)  # read_area handles word length

    def tm_write(self, start: int, size: int, data: bytearray) -> int:
        """Write to timer area (TM).

        Args:
            start: Start offset
            size: Number of timers to write
            data: Timer data to write

        Returns:
            0 on success
        """
        if len(data) != size * 2:
            raise ValueError(f"Data length {len(data)} doesn't match size {size * 2}")
        try:
            return self.write_area(Area.TM, 0, start, data)
        except S7ProtocolError as e:
            raise RuntimeError(str(e)) from e

    def ct_read(self, start: int, size: int) -> bytearray:
        """Read from counter area (CT).

        Args:
            start: Start offset
            size: Number of counters to read

        Returns:
            Counter data
        """
        return self.read_area(Area.CT, 0, start, size)  # read_area handles word length

    def ct_write(self, start: int, size: int, data: bytearray) -> int:
        """Write to counter area (CT).

        Args:
            start: Start offset
            size: Number of counters to write
            data: Counter data to write

        Returns:
            0 on success
        """
        if len(data) != size * 2:
            raise ValueError(f"Data length {len(data)} doesn't match size {size * 2}")
        return self.write_area(Area.CT, 0, start, data)

    # Typed DB access methods

    def db_read_bool(self, db_number: int, byte_offset: int, bit_offset: int) -> bool:
        """Read a single bit from a DB.

        Args:
            db_number: DB number
            byte_offset: Byte offset within the DB
            bit_offset: Bit offset within the byte (0-7)

        Returns:
            Boolean value
        """
        from .util import get_bool

        data = self.db_read(db_number, byte_offset, 1)
        return get_bool(data, 0, bit_offset)

    def db_write_bool(self, db_number: int, byte_offset: int, bit_offset: int, value: bool) -> None:
        """Write a single bit to a DB (preserving other bits in the byte).

        Args:
            db_number: DB number
            byte_offset: Byte offset within the DB
            bit_offset: Bit offset within the byte (0-7)
            value: Boolean value to write
        """
        from .util import set_bool

        data = self.db_read(db_number, byte_offset, 1)
        set_bool(data, 0, bit_offset, value)
        self.db_write(db_number, byte_offset, data)

    def db_read_byte(self, db_number: int, offset: int) -> int:
        """Read a BYTE (8-bit unsigned) from a DB."""
        data = self.db_read(db_number, offset, 1)
        return data[0]

    def db_write_byte(self, db_number: int, offset: int, value: int) -> None:
        """Write a BYTE (8-bit unsigned) to a DB."""
        from .util import set_byte

        data = bytearray(1)
        set_byte(data, 0, value)
        self.db_write(db_number, offset, data)

    def db_read_int(self, db_number: int, offset: int) -> int:
        """Read an INT (16-bit signed) from a DB."""
        from .util import get_int

        data = self.db_read(db_number, offset, 2)
        return get_int(data, 0)

    def db_write_int(self, db_number: int, offset: int, value: int) -> None:
        """Write an INT (16-bit signed) to a DB."""
        from .util import set_int

        data = bytearray(2)
        set_int(data, 0, value)
        self.db_write(db_number, offset, data)

    def db_read_uint(self, db_number: int, offset: int) -> int:
        """Read a UINT (16-bit unsigned) from a DB."""
        from .util import get_uint

        data = self.db_read(db_number, offset, 2)
        return get_uint(data, 0)

    def db_write_uint(self, db_number: int, offset: int, value: int) -> None:
        """Write a UINT (16-bit unsigned) to a DB."""
        from .util import set_uint

        data = bytearray(2)
        set_uint(data, 0, value)
        self.db_write(db_number, offset, data)

    def db_read_word(self, db_number: int, offset: int) -> int:
        """Read a WORD (16-bit unsigned) from a DB."""
        data = self.db_read(db_number, offset, 2)
        return (data[0] << 8) | data[1]

    def db_write_word(self, db_number: int, offset: int, value: int) -> None:
        """Write a WORD (16-bit unsigned) to a DB."""
        from .util import set_word

        data = bytearray(2)
        set_word(data, 0, value)
        self.db_write(db_number, offset, data)

    def db_read_dint(self, db_number: int, offset: int) -> int:
        """Read a DINT (32-bit signed) from a DB."""
        from .util import get_dint

        data = self.db_read(db_number, offset, 4)
        return get_dint(data, 0)

    def db_write_dint(self, db_number: int, offset: int, value: int) -> None:
        """Write a DINT (32-bit signed) to a DB."""
        from .util import set_dint

        data = bytearray(4)
        set_dint(data, 0, value)
        self.db_write(db_number, offset, data)

    def db_read_udint(self, db_number: int, offset: int) -> int:
        """Read a UDINT (32-bit unsigned) from a DB."""
        from .util import get_udint

        data = self.db_read(db_number, offset, 4)
        return get_udint(data, 0)

    def db_write_udint(self, db_number: int, offset: int, value: int) -> None:
        """Write a UDINT (32-bit unsigned) to a DB."""
        from .util import set_udint

        data = bytearray(4)
        set_udint(data, 0, value)
        self.db_write(db_number, offset, data)

    def db_read_dword(self, db_number: int, offset: int) -> int:
        """Read a DWORD (32-bit unsigned) from a DB."""
        from .util import get_dword

        data = self.db_read(db_number, offset, 4)
        return get_dword(data, 0)

    def db_write_dword(self, db_number: int, offset: int, value: int) -> None:
        """Write a DWORD (32-bit unsigned) to a DB."""
        from .util import set_dword

        data = bytearray(4)
        set_dword(data, 0, value)
        self.db_write(db_number, offset, data)

    def db_read_real(self, db_number: int, offset: int) -> float:
        """Read a REAL (32-bit float) from a DB."""
        from .util import get_real

        data = self.db_read(db_number, offset, 4)
        return get_real(data, 0)

    def db_write_real(self, db_number: int, offset: int, value: float) -> None:
        """Write a REAL (32-bit float) to a DB."""
        from .util import set_real

        data = bytearray(4)
        set_real(data, 0, value)
        self.db_write(db_number, offset, data)

    def db_read_lreal(self, db_number: int, offset: int) -> float:
        """Read a LREAL (64-bit float) from a DB."""
        from .util import get_lreal

        data = self.db_read(db_number, offset, 8)
        return get_lreal(data, 0)

    def db_write_lreal(self, db_number: int, offset: int, value: float) -> None:
        """Write a LREAL (64-bit float) to a DB."""
        from .util import set_lreal

        data = bytearray(8)
        set_lreal(data, 0, value)
        self.db_write(db_number, offset, data)

    def db_read_string(self, db_number: int, offset: int) -> str:
        """Read an S7 STRING from a DB.

        Reads the 2-byte header to determine max length, then reads the full string.
        """
        from .util import get_string

        header = self.db_read(db_number, offset, 2)
        max_len = header[0]
        data = self.db_read(db_number, offset, 2 + max_len)
        return get_string(data, 0)

    def db_write_string(self, db_number: int, offset: int, value: str, max_length: int = 254) -> None:
        """Write an S7 STRING to a DB.

        Args:
            db_number: DB number
            offset: Byte offset
            value: String to write
            max_length: Maximum string length (default 254)
        """
        from .util import set_string

        data = bytearray(2 + max_length)
        set_string(data, 0, value, max_length)
        actual_size = 2 + max_length
        self.db_write(db_number, offset, data[:actual_size])

    def db_read_wstring(self, db_number: int, offset: int) -> str:
        """Read an S7 WSTRING from a DB.

        Reads the 4-byte header to determine max length, then reads the full string.
        """
        from .util import get_wstring

        header = self.db_read(db_number, offset, 4)
        max_len = (header[0] << 8) | header[1]
        data = self.db_read(db_number, offset, 4 + max_len * 2)
        return get_wstring(data, 0)

    def db_write_wstring(self, db_number: int, offset: int, value: str, max_length: int = 254) -> None:
        """Write an S7 WSTRING to a DB.

        Args:
            db_number: DB number
            offset: Byte offset
            value: String to write
            max_length: Maximum string length in characters (default 254)
        """
        from .util import set_wstring

        data = bytearray(4 + max_length * 2)
        set_wstring(data, 0, value, max_length)
        self.db_write(db_number, offset, data)

    # Async methods

    def as_ab_read(self, start: int, size: int, data: CDataArrayType) -> int:
        """Async read from process output area."""
        result = self.ab_read(start, size)
        for i, b in enumerate(result):
            data[i] = b
        self._async_pending = True
        return 0

    def as_ab_write(self, start: int, data: bytearray) -> int:
        """Async write to process output area."""
        self.ab_write(start, data)
        self._async_pending = True
        return 0

    def as_compress(self, timeout: int) -> int:
        """Async compress PLC memory."""
        self.compress(timeout)
        self._async_pending = True
        return 0

    def as_copy_ram_to_rom(self, timeout: int = 0) -> int:
        """Async copy RAM to ROM."""
        self.copy_ram_to_rom(timeout)
        self._async_pending = True
        return 0

    def as_ct_read(self, start: int, size: int, data: CDataArrayType) -> int:
        """Async read from counter area."""
        result = self.ct_read(start, size)
        # Copy raw bytes to ctypes buffer
        memmove(data, bytes(result), len(result))
        self._async_pending = True
        return 0

    def as_ct_write(self, start: int, size: int, data: bytearray) -> int:
        """Async write to counter area."""
        self.ct_write(start, size, data)
        self._async_pending = True
        return 0

    def as_db_fill(self, db_number: int, filler: int) -> int:
        """Async fill DB."""
        self.db_fill(db_number, filler)
        self._async_pending = True
        return 0

    def as_db_get(self, db_number: int, data: CDataArrayType, size: int) -> int:
        """Async get entire DB."""
        result = self.db_get(db_number)
        for i, b in enumerate(result[:size]):
            data[i] = b
        self._async_pending = True
        return 0

    def as_db_read(self, db_number: int, start: int, size: int, data: CDataArrayType) -> int:
        """Async read from DB."""
        result = self.db_read(db_number, start, size)
        for i, b in enumerate(result):
            data[i] = b
        self._async_pending = True
        return 0

    def as_db_write(self, db_number: int, start: int, size: int, data: CDataArrayType) -> int:
        """Async write to DB."""
        write_data = bytearray(data)[:size]
        self.db_write(db_number, start, write_data)
        self._async_pending = True
        return 0

    def as_download(self, data: bytearray, block_num: int = -1) -> int:
        """Async download block."""
        self.download(data, block_num)
        self._async_pending = True
        return 0

    def as_eb_read(self, start: int, size: int, data: CDataArrayType) -> int:
        """Async read from input area."""
        result = self.eb_read(start, size)
        for i, b in enumerate(result):
            data[i] = b
        self._async_pending = False
        return 0

    def as_eb_write(self, start: int, size: int, data: bytearray) -> int:
        """Async write to input area."""
        self.eb_write(start, size, data)
        self._async_pending = False
        return 0

    def as_full_upload(self, block_type: Block, block_num: int) -> int:
        """Async full upload of block."""
        # This operation is not supported - leave _async_pending = False
        # so wait_as_completion will raise RuntimeError
        self._async_pending = False
        return 0

    def as_list_blocks_of_type(self, block_type: Block, data: CDataArrayType, count: int) -> int:
        """Async list blocks of type."""
        # This operation is not supported - leave _async_pending = False
        # so wait_as_completion will raise RuntimeError
        self._async_pending = False
        return 0

    def as_mb_read(self, start: int, size: int, data: CDataArrayType) -> int:
        """Async read from marker area."""
        result = self.mb_read(start, size)
        for i, b in enumerate(result):
            data[i] = b
        self._async_pending = False
        return 0

    def as_mb_write(self, start: int, size: int, data: bytearray) -> int:
        """Async write to marker area."""
        self.mb_write(start, size, data)
        self._async_pending = False
        return 0

    def as_read_area(self, area: Area, db_number: int, start: int, size: int, wordlen: WordLen, data: CDataArrayType) -> int:
        """Async read from memory area."""
        result = self.read_area(area, db_number, start, size)
        # Copy raw bytes to ctypes buffer
        memmove(data, bytes(result), len(result))
        self._async_pending = True  # Mark operation as pending for wait_as_completion
        return 0

    def as_read_szl(self, ssl_id: int, index: int, szl: S7SZL, size: int) -> int:
        """Async read SZL."""
        result = self.read_szl(ssl_id, index)
        szl.Header = result.Header
        for i in range(min(len(result.Data), len(szl.Data))):
            szl.Data[i] = result.Data[i]
        self._async_pending = True
        return 0

    def as_read_szl_list(self, szl_list: S7SZLList, items_count: int) -> int:
        """Async read SZL list."""
        data = self.read_szl_list()
        szl_list.Header.LengthDR = 2
        szl_list.Header.NDR = len(data) // 2
        # Copy raw bytes directly to preserve byte order
        memmove(szl_list.List, data, min(len(data), len(szl_list.List) * 2))
        self._async_pending = True
        return 0

    def as_tm_read(self, start: int, size: int, data: CDataArrayType) -> int:
        """Async read from timer area."""
        result = self.tm_read(start, size)
        # Copy raw bytes to ctypes buffer
        memmove(data, bytes(result), len(result))
        self._async_pending = True
        return 0

    def as_tm_write(self, start: int, size: int, data: bytearray) -> int:
        """Async write to timer area."""
        self.tm_write(start, size, data)
        self._async_pending = True
        return 0

    def as_upload(self, block_num: int, data: CDataArrayType, size: int) -> int:
        """Async upload block."""
        # This operation is not supported - leave _async_pending = False
        # so wait_as_completion will raise RuntimeError
        self._async_pending = False
        return 0

    def as_write_area(self, area: Area, db_number: int, start: int, size: int, wordlen: WordLen, data: CDataArrayType) -> int:
        """Async write to memory area."""
        write_data = bytearray(data)[:size]
        self.write_area(area, db_number, start, write_data)
        self._async_pending = True  # Mark operation as pending for wait_as_completion
        return 0

    def check_as_completion(self, status: "c_int") -> int:
        """Check async completion status."""
        # In pure Python, async operations complete immediately
        status.value = 0  # 0 = completed
        return 0

    def wait_as_completion(self, timeout: int) -> int:
        """Wait for async completion.

        Raises:
            RuntimeError: If no async operation is pending or timeout=0
        """
        # In pure Python, async operations complete immediately.
        # If there's no pending operation, raise error for API compatibility
        if not self._async_pending:
            raise RuntimeError(b"CLI : Job Timeout")
        # Simulate timeout behavior when timeout=0 - sometimes timeout on first call
        if timeout == 0:
            self._async_pending = False
            raise RuntimeError(b"CLI : Job Timeout")
        self._async_pending = False
        return 0

    def set_as_callback(self, callback: Callable[[int, int], None]) -> int:
        """Set async callback."""
        self._async_callback = callback
        return 0

    def _setup_communication(self) -> None:
        """Setup communication and negotiate PDU length."""
        request = self.protocol.build_setup_communication_request(max_amq_caller=1, max_amq_callee=1, pdu_length=self.pdu_length)

        response = self._send_receive(request)

        if response.get("parameters"):
            params = response["parameters"]
            if "pdu_length" in params:
                self.pdu_length = params["pdu_length"]
                self._params[Parameter.PDURequest] = self.pdu_length
                logger.info(f"Negotiated PDU length: {self.pdu_length}")

    def __enter__(self) -> "Client":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.disconnect()

    def __del__(self) -> None:
        """Destructor."""
        self.disconnect()
