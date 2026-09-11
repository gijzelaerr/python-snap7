"""S7CommPlus client for S7-1200/1500 PLCs.

Reference: thomas-v2/S7CommPlusDriver (C#, LGPL-3.0)
"""

import logging
import struct
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Optional, TypeAlias, TypeVar

from snap7.error import S7ConnectionError, S7ProtocolError

from . import typeinfo
from .alarm import (
    Alarm,
    AlarmNotification,
    LanguageId,
    build_alarm_explore_request,
    build_alarm_subscription_request,
    build_delete_alarm_subscription_request,
    parse_alarm_explore_response,
    parse_alarm_notification,
)
from .blob_decompressor import find_and_decompress
from .codec import (
    decode_pvalue_to_bytes,
    encode_item_address,
    encode_object_qualifier,
    encode_pvalue_typed,
    parse_create_object_session_id,
)
from .catalog import SymbolCatalog, SymbolicTag, TagResult
from .connection import S7CommPlusConnection
from .protocol import DataType, ElementID, FunctionCode, Ids, ObjectId, ProtocolVersion
from .subscription import (
    SubscriptionItem,
    SubscriptionNotification,
    build_delete_subscription_request,
    build_subscription_request,
    parse_subscription_notification,
)
from .vlq import decode_uint32_vlq, decode_uint64_vlq, encode_uint32_vlq

logger = logging.getLogger(__name__)

_T = TypeVar("_T")
DBWriteItem: TypeAlias = tuple[int, int, bytes, DataType]
SymbolicReadItem: TypeAlias = tuple[int, list[int]] | tuple[int, list[int], int]
SymbolicWriteItem: TypeAlias = tuple[int, list[int], bytes, int, DataType]


def _normalize_write_item(item: DBWriteItem) -> tuple[int, int, bytes, DataType]:
    if len(item) != 4:
        raise ValueError("Write items require (db_number, start_offset, data, datatype); use the target PLC datatype")
    db_number, start, data, datatype = item
    return db_number, start, data, DataType(datatype)


def _normalize_symbolic_read_item(item: SymbolicReadItem) -> tuple[int, list[int], int]:
    if len(item) == 2:
        access_area, lids = item
        return access_area, lids, 0
    access_area, lids, symbol_crc = item
    return access_area, lids, symbol_crc


class S7CommPlusClient:
    """S7CommPlus client for S7-1200/1500 PLCs.

    Use ``from s7commplus import Client`` to instantiate.
    """

    def __init__(self) -> None:
        self._connection: Optional[S7CommPlusConnection] = None
        # Last-used connect() arguments, kept so operations can transparently
        # reconnect on firmware that RSTs the session after a symbolic read.
        self._connect_params: Optional[dict[str, Any]] = None
        self._subscription_change_counter = 1
        self._subscription_relation_id = 0x7FFFC001
        self._symbol_catalog: Optional[SymbolCatalog] = None

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

    @property
    def protection_level(self) -> Optional[int]:
        """Effective protection level reported by the PLC (see `AccessLevel`)."""
        if self._connection is None:
            return None
        return self._connection.protection_level

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
        self._symbol_catalog = None
        self._connect_params = {
            "host": host,
            "port": port,
            "use_tls": use_tls,
            "tls_cert": tls_cert,
            "tls_key": tls_key,
            "tls_ca": tls_ca,
            "password": password,
        }
        self._open_connection()

    def _open_connection(self) -> None:
        """(Re)open the connection using the stored ``connect()`` arguments."""
        if self._connect_params is None:
            raise RuntimeError("Not connected")
        p = self._connect_params
        self._connection = S7CommPlusConnection(host=p["host"], port=p["port"])
        self._connection.connect(
            use_tls=p["use_tls"],
            tls_cert=p["tls_cert"],
            tls_key=p["tls_key"],
            tls_ca=p["tls_ca"],
            password=p["password"] or "",
        )
        if p["password"] is not None and self._connection.tls_active and not self._connection.requires_substreamed:
            logger.info("Performing PLC legitimation (password authentication)")
            self._connection.authenticate(p["password"])

    def _reconnect(self) -> None:
        """Tear down and re-establish the connection with the same parameters.

        Some firmware (e.g. S7-1200 FW V4.1) sends a TCP RST after the first
        symbolic ``GetMultiVariables`` read per connection, so multi-step flows
        such as :meth:`browse` need a fresh session to continue.
        """
        if self._connection is not None:
            try:
                self._connection.disconnect()
            except Exception:
                pass
        self._open_connection()

    def _with_reconnect(self, op: Callable[[], "_T"]) -> "_T":
        """Run ``op``; if the socket was RST by the PLC, reconnect once and retry.

        Well-behaved firmware never triggers the retry (the first call succeeds);
        RST-happy firmware reconnects only when a send actually fails.
        """
        try:
            return op()
        except S7ConnectionError as exc:
            logger.info("Connection dropped by PLC (%s); reconnecting and retrying", exc)
            self._reconnect()
            return op()

    def disconnect(self) -> None:
        """Disconnect from PLC."""
        if self._connection:
            self._connection.disconnect()
            self._connection = None
        self._connect_params = None
        self._symbol_catalog = None

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

        if self._connection.requires_substreamed:
            return self._db_read_substreamed(db_number, start, size)

        payload = _build_read_payload([(db_number, start, size)], self._connection.protocol_version)
        response = self._connection.send_request(FunctionCode.GET_MULTI_VARIABLES, payload)
        results = _parse_read_response(response)
        if not results:
            raise RuntimeError("Read returned no data")
        if results[0] is None:
            raise RuntimeError("Read failed: PLC returned error for item")
        return results[0]

    def _db_read_substreamed(self, db_number: int, start: int, size: int) -> bytes:
        assert self._connection is not None
        access_area = Ids.DB_ACCESS_AREA_BASE + (db_number & 0xFFFF)
        payload = _build_substreamed_read_payload(
            self._connection.session_id, access_area, Ids.DB_VALUE_ACTUAL, [start + 1, size]
        )
        response = self._connection.send_request(FunctionCode.GET_VAR_SUBSTREAMED, payload)
        return _parse_substreamed_read_response(response)

    def db_write(self, db_number: int, start: int, data: bytes, datatype: DataType = DataType.BLOB) -> None:
        """Write raw bytes to a data block.

        Args:
            db_number: Data block number
            start: Start byte offset
            data: Bytes to write
            datatype: S7CommPlus PValue datatype for ``data``. Defaults to BLOB.
        """
        self.db_write_multi([(db_number, start, data, datatype)])

    def db_write_multi(self, items: list[DBWriteItem]) -> None:
        """Write multiple data block regions in a single request.

        Args:
            items: ``(db_number, start_offset, data, datatype)`` tuples.
                The datatype must match the target PLC variable. BLOB is not
                a generic replacement for scalar datatypes.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        if self._connection.requires_substreamed:
            normalized = [_normalize_write_item(item) for item in items]
            for _, _, data, datatype in normalized:
                encode_pvalue_typed(datatype, data)
            for db_number, start, data, datatype in normalized:
                self._db_write_substreamed(db_number, start, data, datatype)
            return

        payload = _build_write_payload(items, self._connection.protocol_version)
        response = self._connection.send_request(FunctionCode.SET_MULTI_VARIABLES, payload)
        _parse_write_response(response)

    def write_multi(self, items: list[DBWriteItem]) -> None:
        """Alias for :meth:`db_write_multi`."""
        self.db_write_multi(items)

    def _db_write_substreamed(self, db_number: int, start: int, data: bytes, datatype: DataType = DataType.BLOB) -> None:
        assert self._connection is not None
        access_area = Ids.DB_ACCESS_AREA_BASE + (db_number & 0xFFFF)
        payload = _build_substreamed_write_payload(
            self._connection.session_id, access_area, Ids.DB_VALUE_ACTUAL, [start + 1, len(data)], data, datatype
        )
        self._connection.send_request(FunctionCode.SET_VAR_SUBSTREAMED, payload)

    def db_read_multi(self, items: list[tuple[int, int, int]]) -> list[bytes]:
        """Read multiple data block regions in a single request.

        Args:
            items: List of (db_number, start_offset, size) tuples

        Returns:
            List of raw bytes for each item
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        if self._connection.requires_substreamed:
            return [self._db_read_substreamed(db, start, size) for db, start, size in items]

        payload = _build_read_payload(items, self._connection.protocol_version)
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

        if self._connection.requires_substreamed:
            payload = _build_substreamed_read_payload(
                self._connection.session_id, area_rid, Ids.CONTROLLER_AREA_VALUE_ACTUAL, [start + 1, size]
            )
            response = self._connection.send_request(FunctionCode.GET_VAR_SUBSTREAMED, payload)
            return _parse_substreamed_read_response(response)

        payload = _build_area_read_payload(area_rid, start, size, self._connection.protocol_version)
        response = self._connection.send_request(FunctionCode.GET_MULTI_VARIABLES, payload)
        results = _parse_read_response(response)
        if not results or results[0] is None:
            raise RuntimeError("Area read failed")
        return results[0]

    def write_area(self, area_rid: int, start: int, data: bytes, *, datatype: DataType = DataType.BLOB) -> None:
        """Write raw bytes to a controller memory area (M, I, Q, counters, timers).

        Args:
            area_rid: Native object RID for the area.
            start: Start byte offset.
            data: Bytes to write.
            datatype: Target PLC datatype. BLOB preserves legacy raw-byte calls;
                use an explicit scalar datatype when writing a scalar target.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        if self._connection.requires_substreamed:
            payload = _build_substreamed_write_payload(
                self._connection.session_id, area_rid, Ids.CONTROLLER_AREA_VALUE_ACTUAL, [start + 1, len(data)], data, datatype
            )
            self._connection.send_request(FunctionCode.SET_VAR_SUBSTREAMED, payload)
            return

        payload = _build_area_write_payload(area_rid, start, data, self._connection.protocol_version, datatype=datatype)
        response = self._connection.send_request(FunctionCode.SET_MULTI_VARIABLES, payload)
        _parse_write_response(response)

    def read_symbolic(self, access_area: int, lids: list[int], symbol_crc: int = 0) -> bytes:
        """Read a variable using S7CommPlus symbolic (LID-based) access.

        .. warning:: This method is **experimental** and may change.

        For S7-1200/1500 DBs with "Optimized block access" enabled, byte
        offsets are unreliable — the PLC internally relocates variables
        between downloads. Symbolic access navigates the PLC's symbol tree
        using LIDs (Local IDs) discovered via :meth:`browse`.

        .. note:: **I/Q/M area caveats** (observed on S7-1200 FW V4.5):

           - **Physical PAQ LIDs return error when value is 0x00.**
             Reading a physical Q-byte LID (e.g. QB0) when all outputs are
             OFF raises ``RuntimeError`` instead of returning ``b"\\x00"``.
             Callers should catch the exception and treat it as zero.
           - **TCP RST after first I/Q/M read.** The PLC sends a TCP RST
             after the first successful I/Q/M ``GetMultiVariables`` per
             connection. DB reads are unaffected. Workaround: reconnect
             before each I/Q/M read.
           - **Symbolic BOOL LIDs can be stale vs. physical PAQ.** A
             symbolic BOOL tag written via ``SetMultiVariables`` may not
             reflect later forced writes to the physical address. For
             reliable output state, read the physical byte LID instead.

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

        # TODO: Send the correct integrity id once available
        payload = _build_symbolic_read_payload(access_area, lids, symbol_crc, self._connection.protocol_version)
        response = self._connection.send_request(FunctionCode.GET_MULTI_VARIABLES, payload)
        results = _parse_read_response(response)
        if not results or results[0] is None:
            raise RuntimeError("Symbolic read failed")
        return results[0]

    def read_symbolic_multi(self, items: Sequence[SymbolicReadItem]) -> list[Optional[bytes]]:
        """Read multiple variables using S7CommPlus symbolic (LID-based) access.

        .. warning:: This method is **experimental** and may change.

        Args:
            items: ``(access_area, lids)`` tuples, or three-tuples adding a
                symbol CRC.

        Returns:
            One entry per requested item, in request order.

        Raises:
            RuntimeError: If the PLC does not answer every requested item.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")
        if not items:
            return []

        payload = _build_multi_symbolic_read_payload(items, self._connection.protocol_version)
        response = self._connection.send_request(FunctionCode.GET_MULTI_VARIABLES, payload)
        results = _parse_read_response(response, expected_count=len(items))
        if len(results) != len(items):
            raise RuntimeError(f"Symbolic multi-read failed: PLC returned {len(results)} of {len(items)} items")
        return results

    def write_symbolic(
        self, access_area: int, lids: list[int], data: bytes, symbol_crc: int = 0, *, datatype: DataType = DataType.BLOB
    ) -> None:
        """Write a variable using S7CommPlus symbolic (LID-based) access.

        .. warning:: This method is **experimental** and may change.

        See :meth:`read_symbolic` for context on when to use symbolic access
        and I/Q/M area caveats.

        .. note:: Writing a symbolic BOOL tag does **not** update the
           physical PAQ byte on some S7-1200 firmware versions. A
           subsequent read of the physical byte LID may show a different
           value than the symbolic BOOL LID.

        Args:
            access_area: Access area ID.
            lids: LID path through the symbol tree.
            data: Raw bytes to write.
            symbol_crc: Symbol CRC for layout validation (0 = skip check).
            datatype: Target PLC datatype, as reported by browse(). BLOB preserves
                legacy calls but is not a generic replacement for scalar types.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        payload = _build_symbolic_write_payload(
            access_area, lids, data, symbol_crc, protocol_version=self._connection.protocol_version, datatype=datatype
        )
        response = self._connection.send_request(FunctionCode.SET_MULTI_VARIABLES, payload)
        _parse_write_response(response)

    def refresh_tag_catalog(self) -> SymbolCatalog:
        """Browse the PLC and replace the cached symbolic tag catalog."""
        self._symbol_catalog = SymbolCatalog.from_browse(self.browse())
        return self._symbol_catalog

    def invalidate_tag_catalog(self) -> None:
        """Discard cached browse metadata after a PLC layout change."""
        self._symbol_catalog = None

    def resolve_tag(self, name: str) -> SymbolicTag:
        """Resolve a browsed tag name to its typed symbolic descriptor."""
        catalog = self._symbol_catalog or self.refresh_tag_catalog()
        return catalog.resolve(name)

    def read_tag(self, name: str) -> bytes:
        """Read one symbolic tag by name, refreshing once if its CRC changed."""
        result = self.read_tags([name])[0]
        if result.error is not None:
            raise result.error
        assert result.value is not None
        return result.value

    def read_tags(self, names: Sequence[str]) -> list[TagResult]:
        """Read names in one request and return a success/error for every item.

        A failed read with a non-zero SymbolCRC causes one catalog refresh. Only
        tags whose CRC actually changed are re-resolved and safely retried.
        """
        if not names:
            return []
        tags = [self.resolve_tag(name) for name in names]
        values = self.read_symbolic_multi([(tag.access_area, list(tag.lids), tag.symbol_crc) for tag in tags])
        results = [
            TagResult(tag=tag, value=value)
            if value is not None
            else TagResult(tag=tag, error=RuntimeError(f"Symbolic read failed for {tag.name!r}"))
            for tag, value in zip(tags, values)
        ]

        retry_indices = [index for index, result in enumerate(results) if not result.success and result.tag.symbol_crc]
        if not retry_indices:
            return results

        refreshed = self.refresh_tag_catalog()
        changed: list[tuple[int, SymbolicTag]] = []
        for index in retry_indices:
            try:
                tag = refreshed.resolve(results[index].tag.name)
            except KeyError:
                continue
            if tag.symbol_crc != results[index].tag.symbol_crc:
                changed.append((index, tag))
        if not changed:
            return results

        retry_values = self.read_symbolic_multi([(tag.access_area, list(tag.lids), tag.symbol_crc) for _, tag in changed])
        for (index, tag), value in zip(changed, retry_values):
            results[index] = (
                TagResult(tag=tag, value=value)
                if value is not None
                else TagResult(tag=tag, error=RuntimeError(f"Symbolic read failed for {tag.name!r} after CRC refresh"))
            )
        return results

    def write_tag(self, name: str, data: bytes) -> None:
        """Write one symbolic tag by name using its resolved PValue datatype."""
        result = self.write_tags({name: data})[0]
        if result.error is not None:
            raise result.error

    def write_tags(self, values: Mapping[str, bytes]) -> list[TagResult]:
        """Write names in one request and return a success/error per item.

        Writes are deliberately never retried: a transport failure can leave
        the caller unable to know whether the PLC applied the request.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")
        if not values:
            return []
        tags = [self.resolve_tag(name) for name in values]
        unsupported = [tag.name for tag in tags if tag.datatype is None]
        if unsupported:
            raise ValueError(f"No S7CommPlus wire datatype mapping for: {', '.join(unsupported)}")
        items: list[SymbolicWriteItem] = [
            (tag.access_area, list(tag.lids), data, tag.symbol_crc, tag.datatype)
            for tag, data in zip(tags, values.values())
            if tag.datatype is not None
        ]
        payload = _build_multi_symbolic_write_payload(items, self._connection.protocol_version)
        response = self._connection.send_request(FunctionCode.SET_MULTI_VARIABLES, payload)
        try:
            errors = _parse_write_response_errors(response, expected_count=len(tags))
        except RuntimeError as error:
            return [TagResult(tag=tag, error=error) for tag in tags]
        return [
            TagResult(tag=tag, error=RuntimeError(f"Symbolic write failed for {tag.name!r}: PLC error {errors[index]}"))
            if index in errors
            else TagResult(tag=tag)
            for index, tag in enumerate(tags, 1)
        ]

    def explore(self, explore_id: int = 0) -> bytes:
        """Browse the PLC object tree.

        Args:
            explore_id: Object to explore (0 = root).

        Returns:
            Raw response payload.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        if self._connection._session_key is not None:
            payload = _build_explore_payload_v3(explore_id if explore_id else 0x38)
        else:
            payload = _build_explore_payload(explore_id)
        response = self._connection.send_request(FunctionCode.EXPLORE, payload, integrity_tail=5, reassemble=True)
        return response

    def explore_xml(self, explore_id: int = 0) -> str | None:
        """EXPLORE a PLC object and decompress the XML metadata from the response.

        S7-1200/1500 PLCs (FW V4.5+) compress XML metadata — tag definitions,
        interface descriptions, line comments, etc. — using zlib with Siemens
        preset dictionaries. This method sends an EXPLORE request and
        decompresses the first zlib stream found in the response.

        .. warning:: This method is **experimental** and may change.

        Args:
            explore_id: Object to explore (0 = root).

        Returns:
            Decompressed XML as a UTF-8 string, or ``None`` if the response
            contains no recognisable zlib stream.
        """
        raw = self.explore(explore_id)
        return find_and_decompress(raw)

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
        return _parse_cpu_state(response)

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

        if self._connection._session_key is not None:
            # V1-initial PLCs: explore the DB wildcard address (0x8A11FFFF)
            # matching TIA Portal's browse pattern
            payload = _build_explore_payload_v3(0x8A11FFFF)
        else:
            payload = _build_explore_request(
                Ids.NATIVE_THE_PLC_PROGRAM_RID, [Ids.OBJECT_VARIABLE_TYPE_NAME, Ids.BLOCK_BLOCK_NUMBER]
            )
        response = self._connection.send_request(FunctionCode.EXPLORE, payload, integrity_tail=5, reassemble=True)
        return _parse_explore_datablocks(response)

    def browse(self) -> list[dict[str, Any]]:
        """Browse the full per-tag symbol tree via EXPLORE + the type-info container.

        .. warning:: This method is **experimental** and may change.

        Returns a flat list of variable dicts with keys ``name``, ``access_sequence``
        (the dot-separated hex path whose first component is the access area and
        remaining components are LIDs for :meth:`read_symbolic`), ``data_type``,
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
            # A symbolic read may prompt a TCP RST on RST-happy firmware; retry once
            # on a fresh session so the read still resolves.
            ti_rid = self._with_reconnect(lambda: self._read_typeinfo_rid(db_info["rid"]))
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
        # The symbolic reads above may have left the socket RST on some firmware;
        # reconnect and retry if so.
        type_objects = self._with_reconnect(self._explore_type_info_container)

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
                    "symbol_crc": v.symbol_crc,
                    "array_dimensions": v.array_dimensions,
                    "string_length": v.string_length,
                }
            )
        return variables

    def _read_typeinfo_rid(self, db_rid: int) -> int:
        """Read LID=1 of a DB to get its type-info RID (0 if the DB has no readable value)."""
        try:
            raw = self.read_symbolic(db_rid, [1], 0)
        except (S7ConnectionError, S7ProtocolError):
            # Connection failures are eligible for reconnect; protocol failures
            # must reach the caller instead of looking like an unreadable DB.
            raise
        except Exception:
            return 0
        return struct.unpack(">I", raw[:4])[0] if len(raw) >= 4 else 0

    def _explore_type_info_container(self) -> list["typeinfo.PObject"]:
        """EXPLORE the OMS type-info container and return its per-type objects."""
        if self._connection is None:
            raise RuntimeError("Not connected")
        payload = _build_explore_request(Ids.OBJECT_OMS_TYPE_INFO_CONTAINER, [])
        response = self._connection.send_request(FunctionCode.EXPLORE, payload, integrity_tail=5, reassemble=True)
        return typeinfo.extract_type_info_objects(response)

    def create_subscription(
        self,
        items: Sequence[SubscriptionItem | str],
        cycle_ms: int = 100,
        credit_limit: int = 10,
    ) -> int:
        """Create a data change subscription.

        .. warning:: This method is **experimental** and may change.

        The PLC pushes an initial value and subsequent changes. Access-sequence
        strings are returned by :meth:`browse`; explicit
        :class:`SubscriptionItem` objects can supply a symbol CRC, sub-area, or
        stable reference ID.

        Args:
            items: Symbolic access-sequence strings or subscription items.
            cycle_ms: Sampling cycle in milliseconds.
            credit_limit: Number of notification credits. The default of 10
                matches the value accepted by real S7-1500 PLCs.

        Returns:
            Subscription object ID assigned by the PLC.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")
        if self._connection.subscription_container_id == 0:
            raise RuntimeError("PLC did not provide a subscription container object")

        normalized = [SubscriptionItem.from_access_sequence(item) if isinstance(item, str) else item for item in items]
        payload, integrity_tail = build_subscription_request(
            self._connection.subscription_container_id,
            normalized,
            cycle_ms=cycle_ms,
            credit_limit=credit_limit,
            change_counter=self._subscription_change_counter,
            relation_id=self._subscription_relation_id,
        )
        response = self._connection.send_request(
            FunctionCode.CREATE_OBJECT,
            payload,
            integrity_tail=integrity_tail,
        )
        object_ids, _, return_value = parse_create_object_session_id(response)
        if return_value != 0 or not object_ids:
            raise RuntimeError(f"Subscription creation failed: PLC returned 0x{return_value:X}")

        self._subscription_change_counter = self._subscription_change_counter % 0xFF + 1
        self._subscription_relation_id = (self._subscription_relation_id + 1) & 0xFFFFFFFF
        subscription_id = object_ids[0]
        logger.info(f"Subscription created, id={subscription_id:#x}")
        return subscription_id

    def receive_subscription_notification(self) -> SubscriptionNotification:
        """Block until the PLC sends one data-subscription notification."""
        if self._connection is None:
            raise RuntimeError("Not connected")
        return parse_subscription_notification(self._connection.receive_notification())

    def delete_subscription(self, subscription_id: int) -> None:
        """Delete a data change subscription.

        .. warning:: This method is **experimental** and may change.

        Args:
            subscription_id: ID returned by :meth:`create_subscription`.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")
        if self._connection.subscription_container_id == 0:
            raise RuntimeError("PLC did not provide a subscription container object")

        # Subscription children are owned by the session's second CreateObject
        # result. The reference driver deletes that container, not the child ID.
        payload = build_delete_subscription_request(self._connection.subscription_container_id, self._connection.protocol_version)
        self._connection.send_request(FunctionCode.DELETE_OBJECT, payload)
        logger.info(f"Subscription {subscription_id:#x} deleted")

    def create_alarm_subscription(
        self,
        language_ids: Optional[list[LanguageId | int]] = None,
        domains: Optional[list[int]] = None,
        credit_limit: int = 10,
    ) -> int:
        """Subscribe to PLC alarm events.

        Args:
            language_ids: Windows LCIDs for texts included with notifications.
                ``None`` requests every configured language.
            domains: Alarm-domain IDs to include. ``None`` subscribes to all.
            credit_limit: Notification credit limit. The default of 10 matches
                the working S7-1500 reference trace.

        Returns:
            Subscription object ID assigned by the PLC.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")
        if self._connection.subscription_container_id == 0:
            raise RuntimeError("PLC did not provide a subscription container object")
        payload = build_alarm_subscription_request(
            self._connection.subscription_container_id, language_ids, domains, credit_limit
        )
        response = self._connection.send_request(
            FunctionCode.CREATE_OBJECT,
            payload,
            integrity_tail=len(payload) - 11,
        )
        object_ids, _, return_value = parse_create_object_session_id(response)
        if return_value != 0 or not object_ids:
            raise RuntimeError(f"Alarm subscription failed: PLC returned {return_value:#x}")
        return object_ids[0]

    def delete_alarm_subscription(self, subscription_id: int) -> None:
        """Delete an alarm subscription created by this client."""
        if self._connection is None:
            raise RuntimeError("Not connected")
        if self._connection.subscription_container_id == 0:
            raise RuntimeError("PLC did not provide a subscription container object")
        payload = build_delete_alarm_subscription_request(
            self._connection.subscription_container_id, self._connection.protocol_version
        )
        self._connection.send_request(FunctionCode.DELETE_OBJECT, payload)
        logger.info(f"Alarm subscription {subscription_id:#x} deleted")

    def receive_alarm_notification(self, language_ids: Optional[list[LanguageId | int]] = None) -> AlarmNotification:
        """Block until the PLC sends one alarm notification.

        Do not run this alongside a data-subscription receive loop on the same
        connection: mixed notification dispatch is not supported yet.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")
        return parse_alarm_notification(self._connection.receive_notification(), language_ids)

    def read_alarms(self, language_ids: Optional[list[LanguageId | int]] = None) -> list[Alarm]:
        """Return the PLC's current active alarm state.

        This is a snapshot read and does not create or consume a subscription,
        so it can be used before or while an alarm subscription exists.

        Args:
            language_ids: Optional Windows LCIDs used to filter returned texts.
                Omitting the filter retains every language sent by the PLC.
        """
        if self._connection is None:
            raise RuntimeError("Not connected")
        response = self._connection.send_request(
            FunctionCode.EXPLORE, build_alarm_explore_request(), integrity_tail=5, reassemble=True
        )
        return parse_alarm_explore_response(response, language_ids)

    def __enter__(self) -> "S7CommPlusClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.disconnect()


# -- Request/response builders (module-level for reuse by async client) --

# S7-1200 wraps a single BOOL/USINT in [value 0x00 | 00 04 00 00 00 00].
# The leading byte is misread by VLQ as a non-zero return code.
_SCALAR_RESPONSE_SUFFIX = bytes.fromhex("000400000000")


def _build_read_payload(items: list[tuple[int, int, int]], protocol_version: int = ProtocolVersion.V2) -> bytes:
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
    payload += encode_object_qualifier(protocol_version=protocol_version)
    payload += struct.pack(">I", 0)

    return bytes(payload)


def _parse_read_response(response: bytes, expected_count: Optional[int] = None) -> list[Optional[bytes]]:
    """Parse a GetMultiVariables response payload.

    Args:
        response: Response payload (after the 14-byte response header)

    Returns:
        List of raw bytes per item (None for errored items)
    """
    offset = 0

    # S7-1200 single-byte scalar: [value 0x00 | 00 04 00 00 00 00]
    if response.endswith(_SCALAR_RESPONSE_SUFFIX):
        body = response[: -len(_SCALAR_RESPONSE_SUFFIX)]
        if len(body) == 2 and body[1] == 0x00:
            return [bytes(body[:1])]

    return_value, consumed = decode_uint64_vlq(response, offset)
    offset += consumed

    if return_value != 0:
        logger.error(f"_parse_read_response: PLC returned error 0x{return_value:X}")
        return []

    values: dict[int, bytes] = {}
    while offset < len(response):
        item_nr, consumed = decode_uint32_vlq(response, offset)
        offset += consumed
        if item_nr == 0:
            break
        raw_bytes, consumed = decode_pvalue_to_bytes(response, offset)
        offset += consumed
        if expected_count is not None and (item_nr > expected_count or item_nr in values):
            raise RuntimeError(f"Symbolic multi-read failed: unexpected or duplicate item {item_nr}")
        values[item_nr] = raw_bytes

    errors: dict[int, int] = {}
    while offset < len(response):
        err_item_nr, consumed = decode_uint32_vlq(response, offset)
        offset += consumed
        if err_item_nr == 0:
            break
        err_value, consumed = decode_uint64_vlq(response, offset)
        offset += consumed
        if expected_count is not None and (err_item_nr > expected_count or err_item_nr in values or err_item_nr in errors):
            raise RuntimeError(f"Symbolic multi-read failed: unexpected or duplicate item {err_item_nr}")
        errors[err_item_nr] = err_value

    if expected_count is not None and len(values) + len(errors) != expected_count:
        raise RuntimeError(f"Symbolic multi-read failed: PLC answered {len(values) + len(errors)} of {expected_count} items")

    max_item = max(max(values.keys(), default=0), max(errors.keys(), default=0))
    results: list[Optional[bytes]] = []
    for i in range(1, max_item + 1):
        if i in values:
            results.append(values[i])
        else:
            results.append(None)

    return results


def _build_write_payload(items: list[DBWriteItem], protocol_version: int = ProtocolVersion.V2) -> bytes:
    """Build a SetMultiVariables request payload.

    Args:
        items: List of (db_number, start_offset, data) tuples

    Returns:
        Encoded payload bytes
    """
    addresses: list[bytes] = []
    total_field_count = 0
    normalized = [_normalize_write_item(item) for item in items]
    for db_number, start, data, _ in normalized:
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
    for i, (_, _, data, datatype) in enumerate(normalized, 1):
        payload += encode_uint32_vlq(i)
        payload += encode_pvalue_typed(datatype, data)
    payload += bytes([0x00])
    payload += encode_object_qualifier(protocol_version=protocol_version)
    payload += struct.pack(">I", 0)

    return bytes(payload)


def _parse_write_response(response: bytes) -> None:
    """Parse a SetMultiVariables response payload.

    Raises:
        RuntimeError: If the write failed
    """
    errors = _parse_write_response_errors(response)
    if errors:
        err_str = ", ".join(f"item {nr}: error {val}" for nr, val in errors.items())
        raise RuntimeError(f"Write failed: {err_str}")


def _parse_write_response_errors(response: bytes, expected_count: Optional[int] = None) -> dict[int, int]:
    """Return the per-item PLC errors in a SetMultiVariables response."""
    return_value, consumed = decode_uint64_vlq(response, 0)
    offset = consumed
    if return_value != 0:
        raise RuntimeError(f"Write failed with return value {return_value}")

    errors: dict[int, int] = {}
    while offset < len(response):
        err_item_nr, consumed = decode_uint32_vlq(response, offset)
        offset += consumed
        if err_item_nr == 0:
            break
        err_value, consumed = decode_uint64_vlq(response, offset)
        offset += consumed
        if expected_count is not None and (err_item_nr > expected_count or err_item_nr in errors):
            raise RuntimeError(f"Symbolic multi-write failed: unexpected or duplicate item {err_item_nr}")
        errors[err_item_nr] = err_value
    return errors


def _build_substreamed_read_payload(session_id: int, access_area: int, access_sub_area: int, lids: list[int]) -> bytes:
    """Build a GET_VAR_SUBSTREAMED payload for data access on V1-initial PLCs."""
    oq = encode_object_qualifier(protocol_version=ProtocolVersion.V1)
    payload = bytearray()
    payload += struct.pack(">I", session_id)
    payload += bytes([0x20, 0x04])
    num_fields = 4 + len(lids)
    payload += encode_uint32_vlq(num_fields)
    payload += encode_uint32_vlq(0)  # SymbolCRC
    payload += encode_uint32_vlq(access_area)
    payload += encode_uint32_vlq(len(lids) + 1)
    payload += encode_uint32_vlq(access_sub_area)
    for lid in lids:
        payload += encode_uint32_vlq(lid)
    payload += oq
    payload += bytes([0x00])
    payload += encode_uint32_vlq(1)
    payload += encode_uint32_vlq(1)
    payload += struct.pack(">I", 0)
    return bytes(payload)


def _build_substreamed_write_payload(
    session_id: int,
    access_area: int,
    access_sub_area: int,
    lids: list[int],
    data: bytes,
    datatype: DataType = DataType.BLOB,
) -> bytes:
    """Build a SET_VAR_SUBSTREAMED payload for data access on V1-initial PLCs."""
    oq = encode_object_qualifier(protocol_version=ProtocolVersion.V1)
    payload = bytearray()
    payload += struct.pack(">I", session_id)
    payload += bytes([0x20, 0x04])
    num_fields = 4 + len(lids)
    payload += encode_uint32_vlq(num_fields)
    payload += encode_uint32_vlq(0)  # SymbolCRC
    payload += encode_uint32_vlq(access_area)
    payload += encode_uint32_vlq(len(lids) + 1)
    payload += encode_uint32_vlq(access_sub_area)
    for lid in lids:
        payload += encode_uint32_vlq(lid)
    payload += oq
    payload += bytes([0x00])
    payload += encode_uint32_vlq(1)
    payload += encode_pvalue_typed(datatype, data)
    payload += encode_uint32_vlq(1)
    payload += struct.pack(">I", 0)
    return bytes(payload)


def _parse_substreamed_read_response(response: bytes) -> bytes:
    """Parse a GET_VAR_SUBSTREAMED response and extract the data bytes."""
    offset = 0
    return_value, consumed = decode_uint64_vlq(response, offset)
    offset += consumed
    if return_value != 0:
        raise RuntimeError(
            f"Substreamed read failed: PLC returned error 0x{return_value:X}. "
            f"This may indicate the addressed object does not exist or the PLC "
            f"does not support GET_VAR_SUBSTREAMED for data reads."
        )
    if offset >= len(response):
        raise RuntimeError("Substreamed read response empty")
    raw_bytes, consumed = decode_pvalue_to_bytes(response, offset)
    return raw_bytes


def _build_area_read_payload(area_rid: int, start: int, size: int, protocol_version: int = ProtocolVersion.V2) -> bytes:
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
    payload += encode_object_qualifier(protocol_version=protocol_version)
    payload += struct.pack(">I", 0)
    return bytes(payload)


def _build_area_write_payload(
    area_rid: int, start: int, data: bytes, protocol_version: int = ProtocolVersion.V2, *, datatype: DataType = DataType.BLOB
) -> bytes:
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
    payload += encode_pvalue_typed(datatype, data)
    payload += bytes([0x00])
    payload += encode_object_qualifier(protocol_version=protocol_version)
    payload += struct.pack(">I", 0)
    return bytes(payload)


def _build_symbolic_read_payload(
    access_area: int,
    lids: list[int],
    symbol_crc: int = 0,
    protocol_version: int = ProtocolVersion.V2,
) -> bytes:
    """Build a GetMultiVariables payload for symbolic (LID-based) access.

    Used for optimized block access on S7-1200/1500 where byte offsets
    are unreliable. The PLC navigates its symbol tree using the LIDs.

    For DBs, ``access_sub_area`` is ``DB_VALUE_ACTUAL``.  For controller
    areas (M/I/Q), it's ``CONTROLLER_AREA_VALUE_ACTUAL``.
    """
    return _build_multi_symbolic_read_payload([(access_area, lids, symbol_crc)], protocol_version=protocol_version)


def _build_multi_symbolic_read_payload(items: Sequence[SymbolicReadItem], protocol_version: int = ProtocolVersion.V2) -> bytes:
    """Build a GetMultiVariables payload for reading multiple symbolic LID addresses at once.

    Used for optimized block access on S7-1200/1500 where byte offsets
    are unreliable. The PLC navigates its symbol tree using the LIDs.

    For DBs, ``access_sub_area`` is ``DB_VALUE_ACTUAL``.  For controller
    areas (M/I/Q), it's ``CONTROLLER_AREA_VALUE_ACTUAL``.

    Args:
        items: List of ``(access_area, lids)`` tuples, or three-tuples adding a
            symbol CRC, one per variable.

    Returns:
        Encoded payload bytes.
    """
    addresses: list[bytes] = []
    total_field_count = 0
    for access_area, lids, symbol_crc in (_normalize_symbolic_read_item(item) for item in items):
        access_sub_area = Ids.DB_VALUE_ACTUAL if access_area >= 0x8A0E0000 else Ids.CONTROLLER_AREA_VALUE_ACTUAL
        addr_bytes, field_count = encode_item_address(
            access_area=access_area,
            access_sub_area=access_sub_area,
            lids=lids,
            symbol_crc=symbol_crc,
        )
        addresses.append(addr_bytes)
        total_field_count += field_count

    payload = bytearray()
    payload += struct.pack(">I", 0)
    payload += encode_uint32_vlq(len(items))
    payload += encode_uint32_vlq(total_field_count)
    for addr in addresses:
        payload += addr
    payload += encode_object_qualifier(protocol_version=protocol_version)
    payload += struct.pack(">I", 0)
    return bytes(payload)


def _build_symbolic_write_payload(
    access_area: int,
    lids: list[int],
    data: bytes,
    symbol_crc: int = 0,
    protocol_version: int = ProtocolVersion.V2,
    *,
    datatype: DataType = DataType.BLOB,
) -> bytes:
    """Build a SetMultiVariables payload for symbolic (LID-based) access."""
    return _build_multi_symbolic_write_payload(
        [(access_area, lids, data, symbol_crc, datatype)], protocol_version=protocol_version
    )


def _build_multi_symbolic_write_payload(items: Sequence[SymbolicWriteItem], protocol_version: int = ProtocolVersion.V2) -> bytes:
    """Build one typed SetMultiVariables payload for symbolic addresses."""
    addresses: list[bytes] = []
    total_field_count = 0
    for access_area, lids, _data, symbol_crc, _datatype in items:
        access_sub_area = Ids.DB_VALUE_ACTUAL if access_area >= 0x8A0E0000 else Ids.CONTROLLER_AREA_VALUE_ACTUAL
        address, field_count = encode_item_address(
            access_area=access_area,
            access_sub_area=access_sub_area,
            lids=lids,
            symbol_crc=symbol_crc,
        )
        addresses.append(address)
        total_field_count += field_count

    payload = bytearray()
    payload += struct.pack(">I", 0)
    payload += encode_uint32_vlq(len(items))
    payload += encode_uint32_vlq(total_field_count)
    for address in addresses:
        payload += address
    for index, (_access_area, _lids, data, _symbol_crc, datatype) in enumerate(items, 1):
        payload += encode_uint32_vlq(index)
        payload += encode_pvalue_typed(datatype, data)
    payload += bytes([0x00])
    payload += encode_object_qualifier(protocol_version=protocol_version)
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


def _build_explore_payload_v3(explore_id: int, sequence: int = 10) -> bytes:
    """Build a V3-style EXPLORE request payload matching TIA Portal format.

    V1-initial PLCs use a 4-byte big-endian InObjectId followed by
    fixed parameters, rather than the VLQ-based format.
    """
    payload = struct.pack(">I", explore_id)
    payload += bytes([0x00, 0x01, 0x00, 0x01, 0x00, 0x00])
    payload += bytes([sequence & 0xFF])
    payload += bytes([0x00, 0x00, 0x00, 0x00, 0x00])
    return payload


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


def _parse_cpu_state(response: bytes) -> str:
    """Parse corroborating execution-state attributes from a CPU EXPLORE reply.

    Real S7-1200/1500 captures show attributes 0x1F80 and 0x1F81 changing
    together across RUN/STOP transitions. Requiring both protects against
    confusing an absent or default-initialized attribute with STOP.
    """
    values: dict[int, set[int]] = {
        Ids.CPU_EXEC_UNIT_EXECUTING: set(),
        Ids.CPU_EXEC_UNIT_OPERATING_MODE: set(),
    }

    offset = 0
    while offset < len(response):
        found = response.find(bytes([ElementID.ATTRIBUTE]), offset)
        if found < 0:
            break
        offset = found + 1
        try:
            attribute_id, consumed = decode_uint32_vlq(response, offset)
        except (ValueError, IndexError):
            continue
        value_offset = offset + consumed
        if attribute_id not in values:
            continue
        # Both observed state attributes are scalar UINT values. Checking the
        # exact PValue header also makes a chance match inside opaque data inert.
        if value_offset + 4 > len(response) or response[value_offset : value_offset + 2] != bytes([0, DataType.UINT]):
            continue
        values[attribute_id].add(struct.unpack_from(">H", response, value_offset + 2)[0])

    executing = values[Ids.CPU_EXEC_UNIT_EXECUTING]
    operating_mode = values[Ids.CPU_EXEC_UNIT_OPERATING_MODE]
    if executing == {1} and operating_mode == {7}:
        return "RUN"
    if executing == {0} and operating_mode == {0}:
        return "STOP"
    return "UNKNOWN"


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
