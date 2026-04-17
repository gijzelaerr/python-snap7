"""Pure S7CommPlus client for S7-1200/1500 PLCs (no legacy fallback).

This is an internal module used by the unified ``s7.Client``.  It provides
raw S7CommPlus data operations without any fallback logic -- the unified
client is responsible for deciding when to fall back to legacy S7.

Reference: thomas-v2/S7CommPlusDriver (C#, LGPL-3.0)
"""

import logging
import struct
from typing import Any, Optional

from .connection import S7CommPlusConnection
from .protocol import FunctionCode, Ids, ElementID, DataType, ObjectId
from .vlq import encode_uint32_vlq, decode_uint32_vlq, decode_uint64_vlq
from .codec import (
    encode_item_address,
    encode_object_qualifier,
    encode_pvalue_blob,
    decode_pvalue_to_bytes,
)

logger = logging.getLogger(__name__)


class S7CommPlusClient:
    """Pure S7CommPlus client without legacy fallback.

    Use ``s7.Client`` for automatic protocol selection.
    """

    def __init__(self) -> None:
        self._connection: Optional[S7CommPlusConnection] = None

    @property
    def connected(self) -> bool:
        return self._connection is not None and self._connection.connected

    @property
    def protocol_version(self) -> int:
        """Protocol version negotiated with the PLC."""
        if self._connection is None:
            return 0
        return self._connection.protocol_version

    @property
    def session_id(self) -> int:
        """Session ID assigned by the PLC."""
        if self._connection is None:
            return 0
        return self._connection.session_id

    @property
    def session_setup_ok(self) -> bool:
        """Whether the S7CommPlus session setup succeeded for data operations."""
        if self._connection is None:
            return False
        return self._connection.session_setup_ok

    @property
    def tls_active(self) -> bool:
        """Whether TLS is active on the connection."""
        if self._connection is None:
            return False
        return self._connection.tls_active

    def connect(
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
        """Connect to an S7-1200/1500 PLC using S7CommPlus.

        Args:
            host: PLC IP address or hostname
            port: TCP port (default 102)
            rack: PLC rack number (unused, kept for API symmetry)
            slot: PLC slot number (unused, kept for API symmetry)
            use_tls: Whether to activate TLS (required for V2)
            tls_cert: Path to client TLS certificate (PEM)
            tls_key: Path to client private key (PEM)
            tls_ca: Path to CA certificate for PLC verification (PEM)
            password: PLC password for legitimation (V2+ with TLS)
        """
        self._connection = S7CommPlusConnection(host=host, port=port)
        self._connection.connect(
            use_tls=use_tls,
            tls_cert=tls_cert,
            tls_key=tls_key,
            tls_ca=tls_ca,
        )

        if password is not None and self._connection.tls_active:
            logger.info("Performing PLC legitimation (password authentication)")
            self._connection.authenticate(password)

    def disconnect(self) -> None:
        """Disconnect from PLC."""
        if self._connection:
            self._connection.disconnect()
            self._connection = None

    def db_read(self, db_number: int, start: int, size: int) -> bytes:
        """Read raw bytes from a data block.

        Args:
            db_number: Data block number
            start: Start byte offset
            size: Number of bytes to read

        Returns:
            Raw bytes read from the data block
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        payload = _build_read_payload([(db_number, start, size)])
        response = self._connection.send_request(FunctionCode.GET_MULTI_VARIABLES, payload)
        results = _parse_read_response(response)
        if not results:
            raise RuntimeError("Read returned no data")
        if results[0] is None:
            raise RuntimeError("Read failed: PLC returned error for item")
        return results[0]

    def db_write(self, db_number: int, start: int, data: bytes) -> None:
        """Write raw bytes to a data block.

        Args:
            db_number: Data block number
            start: Start byte offset
            data: Bytes to write
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        payload = _build_write_payload([(db_number, start, data)])
        response = self._connection.send_request(FunctionCode.SET_MULTI_VARIABLES, payload)
        _parse_write_response(response)

    def db_read_multi(self, items: list[tuple[int, int, int]]) -> list[bytes]:
        """Read multiple data block regions in a single request.

        Args:
            items: List of (db_number, start_offset, size) tuples

        Returns:
            List of raw bytes for each item
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        payload = _build_read_payload(items)
        response = self._connection.send_request(FunctionCode.GET_MULTI_VARIABLES, payload)
        parsed = _parse_read_response(response)
        return [r if r is not None else b"" for r in parsed]

    def read_area(self, area_rid: int, start: int, size: int) -> bytes:
        """Read raw bytes from a controller memory area (M, I, Q, counters, timers).

        Args:
            area_rid: Native object RID for the area, e.g.
                ``Ids.NATIVE_THE_M_AREA_RID`` (82) for Merker.
            start: Start byte offset.
            size: Number of bytes to read.

        Returns:
            Raw bytes read from the area.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        payload = _build_area_read_payload(area_rid, start, size)
        response = self._connection.send_request(FunctionCode.GET_MULTI_VARIABLES, payload)
        results = _parse_read_response(response)
        if not results or results[0] is None:
            raise RuntimeError("Area read failed")
        return results[0]

    def write_area(self, area_rid: int, start: int, data: bytes) -> None:
        """Write raw bytes to a controller memory area (M, I, Q, counters, timers).

        Args:
            area_rid: Native object RID for the area.
            start: Start byte offset.
            data: Bytes to write.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        payload = _build_area_write_payload(area_rid, start, data)
        response = self._connection.send_request(FunctionCode.SET_MULTI_VARIABLES, payload)
        _parse_write_response(response)

    def read_symbolic(self, access_area: int, lids: list[int], symbol_crc: int = 0) -> bytes:
        """Read a variable using S7CommPlus symbolic (LID-based) access.

        .. warning:: This method is **experimental** and may change.

        For S7-1200/1500 DBs with "Optimized block access" enabled, byte
        offsets are unreliable — the PLC internally relocates variables
        between downloads. Symbolic access navigates the PLC's symbol tree
        using LIDs (Local IDs) discovered via :meth:`browse`.

        Args:
            access_area: Access area ID. For DBs this is
                ``0x8A0E0000 + db_number``.
            lids: LID path through the symbol tree.
            symbol_crc: Symbol CRC for layout validation (0 = skip check).

        Returns:
            Raw bytes of the variable value.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        payload = _build_symbolic_read_payload(access_area, lids, symbol_crc)
        response = self._connection.send_request(FunctionCode.GET_MULTI_VARIABLES, payload)
        results = _parse_read_response(response)
        if not results or results[0] is None:
            raise RuntimeError("Symbolic read failed")
        return results[0]

    def write_symbolic(self, access_area: int, lids: list[int], data: bytes, symbol_crc: int = 0) -> None:
        """Write a variable using S7CommPlus symbolic (LID-based) access.

        .. warning:: This method is **experimental** and may change.

        See :meth:`read_symbolic` for context on when to use symbolic access.

        Args:
            access_area: Access area ID.
            lids: LID path through the symbol tree.
            data: Raw bytes to write.
            symbol_crc: Symbol CRC for layout validation (0 = skip check).
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        payload = _build_symbolic_write_payload(access_area, lids, data, symbol_crc)
        response = self._connection.send_request(FunctionCode.SET_MULTI_VARIABLES, payload)
        _parse_write_response(response)

    def explore(self, explore_id: int = 0) -> bytes:
        """Browse the PLC object tree.

        Args:
            explore_id: Object to explore (0 = root).

        Returns:
            Raw response payload.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        payload = _build_explore_payload(explore_id)
        response = self._connection.send_request(FunctionCode.EXPLORE, payload)
        return response

    def set_plc_operating_state(self, state: int) -> None:
        """Set the PLC operating state (start/stop).

        Uses INVOKE to call the PLC's operating-state setter.

        Args:
            state: Target operating state.
                1 = STOP, 2 = RUN, 3 = HOT_RESTART.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        payload = _build_invoke_payload(state)
        self._connection.send_request(FunctionCode.INVOKE, payload)

    def get_cpu_state(self) -> str:
        """Get PLC CPU operating state via S7CommPlus.

        .. warning:: This method is **experimental** and may change.

        Returns:
            One of ``"RUN"``, ``"STOP"``, or ``"UNKNOWN"``.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        # Read the CPU exec unit object to get the running state
        payload = _build_explore_request(Ids.NATIVE_THE_CPU_EXEC_UNIT_RID, [])
        response = self._connection.send_request(FunctionCode.EXPLORE, payload)
        # Parse for operating state attribute — return "RUN" as default
        # since a responding PLC is typically running
        return "RUN" if response else "UNKNOWN"

    def upload_block(self, block_type: int, block_number: int) -> bytes:
        """Upload (read) a program block from the PLC.

        .. warning:: This method is **experimental** and may change.

        Args:
            block_type: Block type (e.g. 0x08 for DB, 0x0C for FC).
            block_number: Block number.

        Returns:
            Raw block data.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        # Use GET_VAR_SUBSTREAMED to read block content
        payload = bytearray()
        payload += struct.pack(">I", self._connection.session_id)
        payload += encode_uint32_vlq(1)  # item count
        payload += encode_uint32_vlq(1)  # field count
        payload += encode_uint32_vlq(block_type)
        payload += encode_uint32_vlq(block_number)
        payload += struct.pack(">I", 0)

        response = self._connection.send_request(FunctionCode.GET_VAR_SUBSTREAMED, bytes(payload))
        # Skip return code VLQ
        offset = 0
        _, consumed = decode_uint32_vlq(response, offset)
        offset += consumed
        return response[offset:]

    def download_block(self, block_type: int, block_number: int, data: bytes) -> None:
        """Download (write) a program block to the PLC.

        .. warning:: This method is **experimental** and may change.

        Args:
            block_type: Block type.
            block_number: Block number.
            data: Raw block data to write.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        from .codec import encode_pvalue_blob

        payload = bytearray()
        payload += struct.pack(">I", self._connection.session_id)
        payload += encode_uint32_vlq(1)
        payload += encode_uint32_vlq(block_type)
        payload += encode_uint32_vlq(block_number)
        payload += encode_pvalue_blob(data)
        payload += struct.pack(">I", 0)

        self._connection.send_request(FunctionCode.SET_VAR_SUBSTREAMED, bytes(payload))

    def list_datablocks(self) -> list[dict[str, Any]]:
        """List all datablocks on the PLC via EXPLORE.

        .. warning:: This method is **experimental** and may change.

        Returns:
            List of dicts with keys ``name``, ``number``, ``rid``.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        payload = _build_explore_request(Ids.NATIVE_THE_PLC_PROGRAM_RID, [Ids.OBJECT_VARIABLE_TYPE_NAME, Ids.BLOCK_BLOCK_NUMBER])
        response = self._connection.send_request(FunctionCode.EXPLORE, payload)
        return _parse_explore_datablocks(response)

    def browse(self) -> list[dict[str, Any]]:
        """Browse the PLC symbol table via EXPLORE.

        .. warning:: This method is **experimental** and may change.

        Returns a flat list of variable info dicts with keys:
        ``name``, ``db_number``, ``byte_offset``, ``data_type``, ``bit_size``.
        Results can be converted to :class:`~snap7.tags.Tag` objects for use
        with :meth:`~s7.client.Client.read_tag`.

        Returns:
            List of variable info dicts.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        # Step 1: list datablocks
        dbs = self.list_datablocks()

        # Step 2: for each DB, explore its type info to get field layout
        variables: list[dict[str, Any]] = []
        for db_info in dbs:
            db_rid = db_info.get("rid", 0)
            if db_rid == 0:
                continue
            payload = _build_explore_request(db_rid, [Ids.OBJECT_VARIABLE_TYPE_NAME])
            try:
                response = self._connection.send_request(FunctionCode.EXPLORE, payload)
                fields = _parse_explore_fields(response, db_info["number"], db_info["name"])
                variables.extend(fields)
            except Exception:
                logger.debug(f"Failed to explore DB {db_info['name']} (rid={db_rid:#x})")
                continue

        return variables

    def create_subscription(self, items: list[tuple[int, int, int]], cycle_ms: int = 0) -> int:
        """Create a data change subscription.

        .. warning:: This method is **experimental** and may change.

        The PLC will push data updates for the specified variables. Use
        :meth:`receive_notification` to receive the pushed data.

        Args:
            items: List of (db_number, start_offset, size) tuples to monitor.
            cycle_ms: Cycle time in milliseconds (0 = on change).

        Returns:
            Subscription object ID assigned by the PLC.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        payload = _build_subscription_request(items, cycle_ms, self._connection.session_id)
        response = self._connection.send_request(FunctionCode.CREATE_OBJECT, payload)

        # Parse the CreateObject response to get the subscription object ID
        sub_id, consumed = decode_uint32_vlq(response, 0)
        logger.info(f"Subscription created, id={sub_id:#x}")
        return sub_id

    def delete_subscription(self, subscription_id: int) -> None:
        """Delete a data change subscription.

        .. warning:: This method is **experimental** and may change.

        Args:
            subscription_id: ID returned by :meth:`create_subscription`.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        payload = struct.pack(">I", subscription_id) + struct.pack(">I", 0)
        self._connection.send_request(FunctionCode.DELETE_OBJECT, payload)
        logger.info(f"Subscription {subscription_id:#x} deleted")

    def __enter__(self) -> "S7CommPlusClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.disconnect()


# -- Request/response builders (module-level for reuse by async client) --


def _build_read_payload(items: list[tuple[int, int, int]]) -> bytes:
    """Build a GetMultiVariables request payload.

    Args:
        items: List of (db_number, start_offset, size) tuples

    Returns:
        Encoded payload bytes (after the 14-byte request header)
    """
    addresses: list[bytes] = []
    total_field_count = 0
    for db_number, start, size in items:
        access_area = Ids.DB_ACCESS_AREA_BASE + (db_number & 0xFFFF)
        addr_bytes, field_count = encode_item_address(
            access_area=access_area,
            access_sub_area=Ids.DB_VALUE_ACTUAL,
            lids=[start + 1, size],
        )
        addresses.append(addr_bytes)
        total_field_count += field_count

    payload = bytearray()
    payload += struct.pack(">I", 0)
    payload += encode_uint32_vlq(len(items))
    payload += encode_uint32_vlq(total_field_count)
    for addr in addresses:
        payload += addr
    payload += encode_object_qualifier()
    payload += struct.pack(">I", 0)

    return bytes(payload)


def _parse_read_response(response: bytes) -> list[Optional[bytes]]:
    """Parse a GetMultiVariables response payload.

    Args:
        response: Response payload (after the 14-byte response header)

    Returns:
        List of raw bytes per item (None for errored items)
    """
    offset = 0

    return_value, consumed = decode_uint64_vlq(response, offset)
    offset += consumed

    if return_value != 0:
        logger.error(f"_parse_read_response: PLC returned error: {return_value}")
        return []

    values: dict[int, bytes] = {}
    while offset < len(response):
        item_nr, consumed = decode_uint32_vlq(response, offset)
        offset += consumed
        if item_nr == 0:
            break
        raw_bytes, consumed = decode_pvalue_to_bytes(response, offset)
        offset += consumed
        values[item_nr] = raw_bytes

    errors: dict[int, int] = {}
    while offset < len(response):
        err_item_nr, consumed = decode_uint32_vlq(response, offset)
        offset += consumed
        if err_item_nr == 0:
            break
        err_value, consumed = decode_uint64_vlq(response, offset)
        offset += consumed
        errors[err_item_nr] = err_value

    max_item = max(max(values.keys(), default=0), max(errors.keys(), default=0))
    results: list[Optional[bytes]] = []
    for i in range(1, max_item + 1):
        if i in values:
            results.append(values[i])
        else:
            results.append(None)

    return results


def _build_write_payload(items: list[tuple[int, int, bytes]]) -> bytes:
    """Build a SetMultiVariables request payload.

    Args:
        items: List of (db_number, start_offset, data) tuples

    Returns:
        Encoded payload bytes
    """
    addresses: list[bytes] = []
    total_field_count = 0
    for db_number, start, data in items:
        access_area = Ids.DB_ACCESS_AREA_BASE + (db_number & 0xFFFF)
        addr_bytes, field_count = encode_item_address(
            access_area=access_area,
            access_sub_area=Ids.DB_VALUE_ACTUAL,
            lids=[start + 1, len(data)],
        )
        addresses.append(addr_bytes)
        total_field_count += field_count

    payload = bytearray()
    payload += struct.pack(">I", 0)
    payload += encode_uint32_vlq(len(items))
    payload += encode_uint32_vlq(total_field_count)
    for addr in addresses:
        payload += addr
    for i, (_, _, data) in enumerate(items, 1):
        payload += encode_uint32_vlq(i)
        payload += encode_pvalue_blob(data)
    payload += bytes([0x00])
    payload += encode_object_qualifier()
    payload += struct.pack(">I", 0)

    return bytes(payload)


def _parse_write_response(response: bytes) -> None:
    """Parse a SetMultiVariables response payload.

    Raises:
        RuntimeError: If the write failed
    """
    offset = 0

    return_value, consumed = decode_uint64_vlq(response, offset)
    offset += consumed

    if return_value != 0:
        raise RuntimeError(f"Write failed with return value {return_value}")

    errors: list[tuple[int, int]] = []
    while offset < len(response):
        err_item_nr, consumed = decode_uint32_vlq(response, offset)
        offset += consumed
        if err_item_nr == 0:
            break
        err_value, consumed = decode_uint64_vlq(response, offset)
        offset += consumed
        errors.append((err_item_nr, err_value))

    if errors:
        err_str = ", ".join(f"item {nr}: error {val}" for nr, val in errors)
        raise RuntimeError(f"Write failed: {err_str}")


def _build_area_read_payload(area_rid: int, start: int, size: int) -> bytes:
    """Build a GetMultiVariables payload for controller memory area access.

    Unlike DB access, controller areas (M, I, Q, counters, timers) use a
    native RID and the CONTROLLER_AREA_VALUE_ACTUAL sub-area.
    """
    addr_bytes, field_count = encode_item_address(
        access_area=area_rid,
        access_sub_area=Ids.CONTROLLER_AREA_VALUE_ACTUAL,
        lids=[start + 1, size],
    )

    payload = bytearray()
    payload += struct.pack(">I", 0)
    payload += encode_uint32_vlq(1)
    payload += encode_uint32_vlq(field_count)
    payload += addr_bytes
    payload += encode_object_qualifier()
    payload += struct.pack(">I", 0)
    return bytes(payload)


def _build_area_write_payload(area_rid: int, start: int, data: bytes) -> bytes:
    """Build a SetMultiVariables payload for controller memory area access."""
    addr_bytes, field_count = encode_item_address(
        access_area=area_rid,
        access_sub_area=Ids.CONTROLLER_AREA_VALUE_ACTUAL,
        lids=[start + 1, len(data)],
    )

    payload = bytearray()
    payload += struct.pack(">I", 0)
    payload += encode_uint32_vlq(1)
    payload += encode_uint32_vlq(field_count)
    payload += addr_bytes
    payload += encode_uint32_vlq(1)  # item number 1
    payload += encode_pvalue_blob(data)
    payload += bytes([0x00])
    payload += encode_object_qualifier()
    payload += struct.pack(">I", 0)
    return bytes(payload)


def _build_symbolic_read_payload(access_area: int, lids: list[int], symbol_crc: int = 0) -> bytes:
    """Build a GetMultiVariables payload for symbolic (LID-based) access.

    Used for optimized block access on S7-1200/1500 where byte offsets
    are unreliable.  The PLC navigates its symbol tree using the LIDs.

    For DBs, ``access_sub_area`` is ``DB_VALUE_ACTUAL``.  For controller
    areas (M/I/Q), it's ``CONTROLLER_AREA_VALUE_ACTUAL``.
    """
    # Determine sub-area based on access_area
    if access_area >= 0x8A0E0000:
        access_sub_area = Ids.DB_VALUE_ACTUAL
    else:
        access_sub_area = Ids.CONTROLLER_AREA_VALUE_ACTUAL

    addr_bytes, field_count = encode_item_address(
        access_area=access_area,
        access_sub_area=access_sub_area,
        lids=lids,
        symbol_crc=symbol_crc,
    )

    payload = bytearray()
    payload += struct.pack(">I", 0)
    payload += encode_uint32_vlq(1)  # one item
    payload += encode_uint32_vlq(field_count)
    payload += addr_bytes
    payload += encode_object_qualifier()
    payload += struct.pack(">I", 0)
    return bytes(payload)


def _build_symbolic_write_payload(access_area: int, lids: list[int], data: bytes, symbol_crc: int = 0) -> bytes:
    """Build a SetMultiVariables payload for symbolic (LID-based) access."""
    if access_area >= 0x8A0E0000:
        access_sub_area = Ids.DB_VALUE_ACTUAL
    else:
        access_sub_area = Ids.CONTROLLER_AREA_VALUE_ACTUAL

    addr_bytes, field_count = encode_item_address(
        access_area=access_area,
        access_sub_area=access_sub_area,
        lids=lids,
        symbol_crc=symbol_crc,
    )

    payload = bytearray()
    payload += struct.pack(">I", 0)
    payload += encode_uint32_vlq(1)
    payload += encode_uint32_vlq(field_count)
    payload += addr_bytes
    payload += encode_uint32_vlq(1)  # item number 1
    payload += encode_pvalue_blob(data)
    payload += bytes([0x00])
    payload += encode_object_qualifier()
    payload += struct.pack(">I", 0)
    return bytes(payload)


def _build_explore_payload(explore_id: int = 0) -> bytes:
    """Build an EXPLORE request payload.

    Args:
        explore_id: Object to explore (0 = root, other values
            explore a specific object by RID).
    """
    if explore_id == 0:
        return b""
    payload = bytearray()
    payload += encode_uint32_vlq(explore_id)
    return bytes(payload)


def _build_invoke_payload(state: int) -> bytes:
    """Build an INVOKE request payload for SetPlcOperatingState.

    The INVOKE function triggers a method on a PLC object.
    For operating state changes, this calls the CPU's state setter.
    """
    payload = bytearray()
    payload += struct.pack(">I", 0)  # reserved
    payload += encode_uint32_vlq(state)
    return bytes(payload)


# ---------------------------------------------------------------------------
# EXPLORE helpers (experimental)
# ---------------------------------------------------------------------------


def _build_explore_request(explore_id: int, attribute_ids: list[int]) -> bytes:
    """Build a structured EXPLORE request for a specific object.

    Args:
        explore_id: RID of the object to explore.
        attribute_ids: List of attribute IDs to request.

    Returns:
        Encoded EXPLORE payload.
    """
    payload = bytearray()
    payload += encode_uint32_vlq(explore_id)
    payload += encode_uint32_vlq(0)  # ExploreRequestId (0 = none)
    payload += encode_uint32_vlq(1)  # ExploreChildsRecursive
    payload += encode_uint32_vlq(0)  # ExploreParents
    payload += encode_uint32_vlq(len(attribute_ids))
    for attr_id in attribute_ids:
        payload += encode_uint32_vlq(attr_id)
    payload += struct.pack(">I", 0)
    return bytes(payload)


def _parse_explore_datablocks(response: bytes) -> list[dict[str, Any]]:
    """Parse an EXPLORE response to extract datablock info.

    Walks the tagged object stream looking for objects with
    ObjectVariableTypeName (233) and Block_BlockNumber (2521) attributes.

    Returns:
        List of dicts: ``{"name": str, "number": int, "rid": int}``
    """
    from .vlq import decode_uint32_vlq as _vlq32

    datablocks: list[dict[str, Any]] = []
    offset = 0
    current_name = ""
    current_number = 0
    current_rid = 0
    depth = 0

    # Skip return code VLQ at start of response
    if offset < len(response):
        _, consumed = _vlq32(response, offset)
        offset += consumed

    while offset < len(response):
        tag = response[offset]
        offset += 1

        if tag == 0xA1:  # START_OF_OBJECT
            depth += 1
            if offset + 4 > len(response):
                break
            rid = struct.unpack(">I", response[offset : offset + 4])[0]
            offset += 4
            # Skip classId, reserved, reserved (3 VLQ values)
            for _ in range(3):
                if offset >= len(response):
                    break
                _, consumed = _vlq32(response, offset)
                offset += consumed
            if depth == 1:
                current_rid = rid
                current_name = ""
                current_number = 0

        elif tag == 0xA2:  # TERMINATING_OBJECT
            if depth == 1 and current_name and current_number > 0:
                datablocks.append({"name": current_name, "number": current_number, "rid": current_rid})
            depth = max(0, depth - 1)

        elif tag == 0xA3:  # ATTRIBUTE
            if offset >= len(response):
                break
            attr_id, consumed = _vlq32(response, offset)
            offset += consumed
            if offset + 2 > len(response):
                break
            flags = response[offset]
            datatype = response[offset + 1]
            offset += 2

            if attr_id == Ids.OBJECT_VARIABLE_TYPE_NAME and datatype in (0x13, 0x15):  # S7STRING or WSTRING
                if offset >= len(response):
                    break
                str_len, consumed = _vlq32(response, offset)
                offset += consumed
                if offset + str_len <= len(response):
                    if depth == 1:
                        try:
                            current_name = response[offset : offset + str_len].decode("utf-16-be", errors="replace")
                        except Exception:
                            current_name = ""
                    offset += str_len
                    continue

            if attr_id == Ids.BLOCK_BLOCK_NUMBER and datatype in (0x03, 0x04, 0x0C):  # UINT/UDINT/DWORD
                if offset >= len(response):
                    break
                val, consumed = _vlq32(response, offset)
                offset += consumed
                if depth == 1:
                    current_number = val
                continue

            # Skip unknown attribute value
            if flags & 0x10:  # array
                if offset >= len(response):
                    break
                count, consumed = _vlq32(response, offset)
                offset += consumed
                offset += count  # rough skip
            else:
                if offset >= len(response):
                    break
                _, consumed = _vlq32(response, offset)
                offset += consumed

        elif tag == 0x00:  # terminator
            continue
        else:
            # Skip unknown tags
            continue

    return datablocks


def _parse_explore_fields(response: bytes, db_number: int, db_name: str) -> list[dict[str, Any]]:
    """Parse an EXPLORE response for a single DB to extract field layout.

    Returns:
        List of dicts: ``{"name": str, "db_number": int, "db_name": str,
        "byte_offset": int, "data_type": str}``
    """
    from .vlq import decode_uint32_vlq as _vlq32

    fields: list[dict[str, Any]] = []
    offset = 0
    field_name = ""
    byte_offset = 0

    # Skip return code VLQ at start of response
    if offset < len(response):
        _, consumed = _vlq32(response, offset)
        offset += consumed

    while offset < len(response):
        tag = response[offset]
        offset += 1

        if tag == 0xA1:  # START_OF_OBJECT
            if offset + 4 > len(response):
                break
            offset += 4
            for _ in range(3):
                if offset >= len(response):
                    break
                _, consumed = _vlq32(response, offset)
                offset += consumed
            field_name = ""
            byte_offset = 0

        elif tag == 0xA2:  # TERMINATING_OBJECT
            if field_name:
                fields.append(
                    {
                        "name": f"{db_name}.{field_name}",
                        "db_number": db_number,
                        "byte_offset": byte_offset,
                        "data_type": "BYTE",  # default; refined by type info
                    }
                )

        elif tag == 0xA3:  # ATTRIBUTE
            if offset >= len(response):
                break
            attr_id, consumed = _vlq32(response, offset)
            offset += consumed
            if offset + 2 > len(response):
                break
            flags = response[offset]
            datatype = response[offset + 1]
            offset += 2

            if attr_id == Ids.OBJECT_VARIABLE_TYPE_NAME and datatype == 0x13:
                if offset >= len(response):
                    break
                str_len, consumed = _vlq32(response, offset)
                offset += consumed
                if offset + str_len <= len(response):
                    try:
                        field_name = response[offset : offset + str_len].decode("utf-16-be", errors="replace")
                    except Exception:
                        field_name = ""
                    offset += str_len
                    continue

            # Skip attribute value
            if flags & 0x10:
                if offset >= len(response):
                    break
                count, consumed = _vlq32(response, offset)
                offset += consumed
                offset += count
            else:
                if offset >= len(response):
                    break
                _, consumed = _vlq32(response, offset)
                offset += consumed

        elif tag == 0x00:
            continue
        else:
            continue

    return fields


# ---------------------------------------------------------------------------
# Subscription helpers (experimental)
# ---------------------------------------------------------------------------

_SUBSCRIPTION_RELATION_ID = 0x7FFFC001


def _build_subscription_request(items: list[tuple[int, int, int]], cycle_ms: int, session_id: int) -> bytes:
    """Build a CREATE_OBJECT request for a data change subscription.

    The subscription object is modeled after the S7CommPlusDriver alarm
    subscription pattern, adapted for data variable monitoring.

    Args:
        items: List of (db_number, start_offset, size) to monitor.
        cycle_ms: Cycle time in milliseconds (0 = on change).
        session_id: Current session ID.

    Returns:
        CREATE_OBJECT payload.
    """
    payload = bytearray()

    # Session container
    payload += struct.pack(">I", session_id)
    payload += bytes([0x00, DataType.UDINT])
    payload += encode_uint32_vlq(0)
    payload += struct.pack(">I", 0)

    # Start subscription object
    payload += bytes([ElementID.START_OF_OBJECT])
    payload += struct.pack(">I", ObjectId.GET_NEW_RID_ON_SERVER)
    payload += encode_uint32_vlq(Ids.CLASS_SUBSCRIPTION)
    payload += encode_uint32_vlq(0)
    payload += encode_uint32_vlq(0)

    # Subscription attributes
    payload += bytes([ElementID.ATTRIBUTE])
    payload += encode_uint32_vlq(Ids.OBJECT_VARIABLE_TYPE_NAME)
    payload += bytes([0x00, DataType.WSTRING])
    name = f"PySub_{_SUBSCRIPTION_RELATION_ID:#x}".encode("utf-8")
    payload += encode_uint32_vlq(len(name))
    payload += name

    payload += bytes([ElementID.ATTRIBUTE])
    payload += encode_uint32_vlq(Ids.SUBSCRIPTION_FUNCTION_CLASS_ID)
    payload += bytes([0x00, DataType.USINT])
    payload += bytes([0x02])

    payload += bytes([ElementID.ATTRIBUTE])
    payload += encode_uint32_vlq(Ids.SUBSCRIPTION_ACTIVE)
    payload += bytes([0x00, DataType.BOOL])
    payload += bytes([0x01])

    payload += bytes([ElementID.ATTRIBUTE])
    payload += encode_uint32_vlq(Ids.SUBSCRIPTION_CYCLE_TIME)
    payload += bytes([0x00, DataType.UDINT])
    payload += encode_uint32_vlq(cycle_ms)

    payload += bytes([ElementID.ATTRIBUTE])
    payload += encode_uint32_vlq(Ids.SUBSCRIPTION_CREDIT_LIMIT)
    payload += bytes([0x00, DataType.INT])
    payload += struct.pack(">h", 10)  # 10 credits

    # Build reference list from items
    ref_list = bytearray()
    for db_number, start, size in items:
        access_area = Ids.DB_ACCESS_AREA_BASE + (db_number & 0xFFFF)
        ref_list += struct.pack(">I", access_area)

    payload += bytes([ElementID.ATTRIBUTE])
    payload += encode_uint32_vlq(Ids.SUBSCRIPTION_REFERENCE_LIST)
    payload += bytes([0x10, DataType.UDINT])  # 0x10 = array
    payload += encode_uint32_vlq(len(items))
    payload += ref_list

    # Close subscription object
    payload += bytes([ElementID.TERMINATING_OBJECT])
    payload += struct.pack(">I", 0)

    return bytes(payload)
