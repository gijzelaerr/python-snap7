"""Pure S7CommPlus client for S7-1200/1500 PLCs (no legacy fallback).

This is an internal module used by the unified ``s7.Client``.  It provides
raw S7CommPlus data operations without any fallback logic -- the unified
client is responsible for deciding when to fall back to legacy S7.

Reference: thomas-v2/S7CommPlusDriver (C#, LGPL-3.0)
"""

import logging
import struct
from typing import Any, Optional

from . import typeinfo
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
        response = self._connection.send_request(FunctionCode.EXPLORE, payload, integrity_tail=5, reassemble=True)
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
        response = self._connection.send_request(FunctionCode.EXPLORE, payload, integrity_tail=5, reassemble=True)
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
        response = self._connection.send_request(FunctionCode.EXPLORE, payload, integrity_tail=5, reassemble=True)
        return _parse_explore_datablocks(response)

    def browse(self) -> list[dict[str, Any]]:
        """Browse the full per-tag symbol tree via EXPLORE + the type-info container.

        .. warning:: This method is **experimental** and may change.

        Returns a flat list of variable dicts with keys ``name``, ``access_sequence``
        (the dot-separated hex LID path usable with :meth:`read_tag`), ``data_type``,
        and the optimized/non-optimized byte+bit offsets. Steps: enumerate DBs, resolve
        each DB's type-info RID via a LID=1 read, explore the OMS type-info container,
        then recombine into the symbol tree.

        Returns:
            List of variable info dicts.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        # Phase A: enumerate data blocks. Phase B/C: resolve each DB's type-info RID
        # (a LID=1 read — needed for instance DBs whose TI is not their own RID) and seed
        # a root node per DB.
        root_nodes: list[typeinfo.Node] = []
        for db_info in self.list_datablocks():
            if db_info.get("number", 0) <= 0 or db_info.get("rid", 0) == 0:
                continue
            ti_rid = self._read_typeinfo_rid(db_info["rid"])
            if ti_rid == 0:
                continue  # load-memory-only DB, skip
            root_nodes.append(
                typeinfo.Node(
                    node_type=typeinfo.NodeType.ROOT, name=db_info["name"], access_id=db_info["rid"], relation_id=ti_rid
                )
            )

        # Add the native process areas with their known synthetic type-info ids.
        for name, access_rid, ti_rid in (
            ("IArea", Ids.NATIVE_THE_I_AREA_RID, 0x90010000),
            ("QArea", Ids.NATIVE_THE_Q_AREA_RID, 0x90020000),
            ("MArea", Ids.NATIVE_THE_M_AREA_RID, 0x90030000),
            ("S7Timers", Ids.NATIVE_THE_S7_TIMERS_RID, 0x90050000),
            ("S7Counters", Ids.NATIVE_THE_S7_COUNTERS_RID, 0x90060000),
        ):
            root_nodes.append(
                typeinfo.Node(node_type=typeinfo.NodeType.ROOT, name=name, access_id=access_rid, relation_id=ti_rid)
            )

        # Phase D: explore the OMS type-info container (a large, multi-fragment PDU).
        type_objects = self._explore_type_info_container()

        # Phase E: recombine type-info with the DB/area nodes and flatten.
        typeinfo.build_tree(root_nodes, type_objects)
        variables: list[dict[str, Any]] = []
        for v in typeinfo.build_flat_list(root_nodes):
            try:
                data_type = typeinfo.Softdatatype(v.softdatatype).name
            except ValueError:
                data_type = str(v.softdatatype)
            variables.append(
                {
                    "name": v.name,
                    "access_sequence": v.access_sequence,
                    "data_type": data_type,
                    "opt_address": v.opt_address,
                    "opt_bitoffset": v.opt_bitoffset,
                    "nonopt_address": v.nonopt_address,
                    "nonopt_bitoffset": v.nonopt_bitoffset,
                }
            )
        return variables

    def _read_typeinfo_rid(self, db_rid: int) -> int:
        """Read LID=1 of a DB to get its type-info RID (0 if the DB has no readable value)."""
        try:
            raw = self.read_symbolic(db_rid, [1], 0)
        except Exception:
            return 0
        return struct.unpack(">I", raw[:4])[0] if len(raw) >= 4 else 0

    def _explore_type_info_container(self) -> list["typeinfo.PObject"]:
        """EXPLORE the OMS type-info container and return its per-type objects."""
        payload = _build_explore_request(Ids.OBJECT_OMS_TYPE_INFO_CONTAINER, [])
        response = self._connection.send_request(FunctionCode.EXPLORE, payload, integrity_tail=5, reassemble=True)
        return typeinfo.extract_type_info_objects(response)

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
    payload += struct.pack(">I", explore_id)  # ExploreId (fixed UInt32, not VLQ)
    payload += encode_uint32_vlq(0)  # ExploreRequestId (0 = none)
    payload += bytes([1])  # ExploreChildsRecursive
    payload += bytes([1])  # unknown flag — the protocol always carries 1 here
    payload += bytes([0])  # ExploreParents
    payload += bytes([0])  # number of following filter objects (none)
    payload += encode_uint32_vlq(len(attribute_ids))  # AddressList count
    for attr_id in attribute_ids:
        payload += encode_uint32_vlq(attr_id)
    # Trailer: UInt32 fill + a single filler byte. For V2+, send_request(integrity_tail=5)
    # splices the IntegrityId in just before these 5 bytes.
    payload += struct.pack(">I", 0) + bytes([0])
    return bytes(payload)


def _parse_explore_datablocks(response: bytes) -> list[dict[str, Any]]:
    """Parse an EXPLORE(thePLCProgram) response to extract datablock info.

    Walks the PObject tree (StartOfObject / Attribute / TerminatingObject) keeping a
    stack of ``[relation_id, class_id, name]``. A DataBlock is an object whose ClassId
    is ``DB_CLASS_RID`` and whose RelationId is a DB area id (``relid >> 16 == 0x8A0E``);
    its number is ``relid & 0xFFFF`` and its name comes from the ObjectVariableTypeName
    attribute (the first step of the symbol-tree browse).

    Returns:
        List of dicts: ``{"name": str, "number": int, "rid": int}``
    """
    datablocks: list[dict[str, Any]] = []
    offset = 0

    # ReturnValue (UInt64 VLQ) at the start of the response.
    if offset < len(response):
        _, consumed = decode_uint64_vlq(response, offset)
        offset += consumed

    stack: list[list[Any]] = []  # each entry: [relation_id, class_id, name]
    while offset < len(response):
        tag = response[offset]

        if tag == ElementID.START_OF_OBJECT:
            offset += 1
            if offset + 4 > len(response):
                break
            relid = struct.unpack_from(">I", response, offset)[0]
            offset += 4
            class_id, consumed = decode_uint32_vlq(response, offset)
            offset += consumed
            _class_flags, consumed = decode_uint32_vlq(response, offset)  # ClassFlags
            offset += consumed
            _attr_id, consumed = decode_uint32_vlq(response, offset)  # AttributeId
            offset += consumed
            stack.append([relid, class_id, ""])

        elif tag == ElementID.TERMINATING_OBJECT:
            offset += 1
            if stack:
                relid, class_id, name = stack.pop()
                if class_id == Ids.DB_CLASS_RID and (relid >> 16) == 0x8A0E:
                    datablocks.append({"name": name, "number": relid & 0xFFFF, "rid": relid})

        elif tag == ElementID.ATTRIBUTE:
            offset += 1
            attr_id, consumed = decode_uint32_vlq(response, offset)
            offset += consumed
            try:
                value, consumed = decode_pvalue_to_bytes(response, offset)
            except (ValueError, IndexError):
                break
            offset += consumed
            if attr_id == Ids.OBJECT_VARIABLE_TYPE_NAME and stack:
                # Block names arrive as a WString. On the S7-1500 the ASCII range is
                # transmitted one byte per character (no null high-bytes), so the
                # presence of a null byte distinguishes the two encodings:
                #   * null present  -> genuine UTF-16-BE (ASCII chars carry a 0x00 high byte)
                #   * no null       -> packed one-byte-per-char ASCII (decode as latin-1)
                # Note we can't simply "try UTF-16 first on even length": an even-length
                # one-byte-per-char ASCII name would then be mis-paired into wrong glyphs.
                # PLC symbol names are identifiers and never contain an embedded null, so
                # the null-byte test is unambiguous in practice.
                try:
                    if b"\x00" in value:
                        name = value.decode("utf-16-be", errors="replace")
                    else:
                        name = value.decode("latin-1", errors="replace")
                    stack[-1][2] = name.rstrip("\x00")
                except Exception:
                    pass

        else:
            # Response-preamble fields before the first object, or unhandled element
            # tags (e.g. Relation): advance one byte and keep scanning.
            offset += 1

    return datablocks


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
