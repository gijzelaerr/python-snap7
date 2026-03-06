"""
S7CommPlus client for S7-1200/1500 PLCs.

Provides high-level operations over the S7CommPlus protocol, similar to
the existing snap7.Client but targeting S7-1200/1500 PLCs with full
engineering access (symbolic addressing, optimized data blocks, etc.).

Supports all S7CommPlus protocol versions (V1/V2/V3/TLS). The protocol
version is auto-detected from the PLC's CreateObject response during
connection setup.

Status: V1 connection is functional. V2/V3/TLS authentication planned.

Reference: thomas-v2/S7CommPlusDriver (C#, LGPL-3.0)
"""

import logging
import struct
from typing import Any, Optional

from .connection import S7CommPlusConnection
from .protocol import FunctionCode, Ids
from .vlq import encode_uint32_vlq, decode_uint32_vlq, decode_uint64_vlq
from .codec import (
    encode_item_address,
    encode_object_qualifier,
    encode_pvalue_blob,
    decode_pvalue_to_bytes,
)

logger = logging.getLogger(__name__)


class S7CommPlusClient:
    """S7CommPlus client for S7-1200/1500 PLCs.

    Supports all S7CommPlus protocol versions:
    - V1: S7-1200 FW V4.0+
    - V2: S7-1200/1500 with older firmware
    - V3: S7-1200/1500 pre-TIA Portal V17
    - V3 + TLS: TIA Portal V17+ (recommended)

    The protocol version is auto-detected during connection.

    Example::

        client = S7CommPlusClient()
        client.connect("192.168.1.10")

        # Read raw bytes from DB1
        data = client.db_read(1, 0, 4)

        # Write raw bytes to DB1
        client.db_write(1, 0, struct.pack(">f", 23.5))

        client.disconnect()
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
    ) -> None:
        """Connect to an S7-1200/1500 PLC using S7CommPlus.

        Args:
            host: PLC IP address or hostname
            port: TCP port (default 102)
            rack: PLC rack number
            slot: PLC slot number
            use_tls: Whether to attempt TLS (requires V3 PLC + certs)
            tls_cert: Path to client TLS certificate (PEM)
            tls_key: Path to client private key (PEM)
            tls_ca: Path to CA certificate for PLC verification (PEM)
        """
        self._connection = S7CommPlusConnection(
            host=host,
            port=port,
        )

        self._connection.connect(
            use_tls=use_tls,
            tls_cert=tls_cert,
            tls_key=tls_key,
            tls_ca=tls_ca,
        )

    def disconnect(self) -> None:
        """Disconnect from PLC."""
        if self._connection:
            self._connection.disconnect()
            self._connection = None

    # -- Data block read/write --

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
        logger.debug(f"db_read: db={db_number} start={start} size={size} payload={payload.hex(' ')}")

        response = self._connection.send_request(FunctionCode.GET_MULTI_VARIABLES, payload)
        logger.debug(f"db_read: response ({len(response)} bytes): {response.hex(' ')}")

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
        logger.debug(
            f"db_write: db={db_number} start={start} data_len={len(data)} "
            f"data={data.hex(' ')} payload={payload.hex(' ')}"
        )

        response = self._connection.send_request(FunctionCode.SET_MULTI_VARIABLES, payload)
        logger.debug(f"db_write: response ({len(response)} bytes): {response.hex(' ')}")

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
        logger.debug(f"db_read_multi: {len(items)} items: {items} payload={payload.hex(' ')}")

        response = self._connection.send_request(FunctionCode.GET_MULTI_VARIABLES, payload)
        logger.debug(f"db_read_multi: response ({len(response)} bytes): {response.hex(' ')}")

        results = _parse_read_response(response)
        return [r if r is not None else b"" for r in results]

    # -- Explore (browse PLC object tree) --

    def explore(self) -> bytes:
        """Browse the PLC object tree.

        Returns the raw Explore response payload for parsing.
        Full symbolic exploration will be implemented in a future version.

        Returns:
            Raw response payload
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        response = self._connection.send_request(FunctionCode.EXPLORE, b"")
        logger.debug(f"explore: response ({len(response)} bytes): {response.hex(' ')}")
        return response

    # -- Context manager --

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

    Reference: thomas-v2/S7CommPlusDriver/Core/GetMultiVariablesRequest.cs
    """
    # Encode all item addresses and compute total field count
    addresses: list[bytes] = []
    total_field_count = 0
    for db_number, start, size in items:
        access_area = Ids.DB_ACCESS_AREA_BASE + (db_number & 0xFFFF)
        addr_bytes, field_count = encode_item_address(
            access_area=access_area,
            access_sub_area=Ids.DB_VALUE_ACTUAL,
            lids=[start, size],
        )
        addresses.append(addr_bytes)
        total_field_count += field_count

    payload = bytearray()
    # LinkId (UInt32 fixed = 0, for reading variables)
    payload += struct.pack(">I", 0)
    # Item count
    payload += encode_uint32_vlq(len(items))
    # Total field count across all items
    payload += encode_uint32_vlq(total_field_count)
    # Item addresses
    for addr in addresses:
        payload += addr
    # ObjectQualifier
    payload += encode_object_qualifier()
    # Padding
    payload += struct.pack(">I", 0)

    return bytes(payload)


def _parse_read_response(response: bytes) -> list[Optional[bytes]]:
    """Parse a GetMultiVariables response payload.

    Args:
        response: Response payload (after the 14-byte response header)

    Returns:
        List of raw bytes per item (None for errored items)

    Reference: thomas-v2/S7CommPlusDriver/Core/GetMultiVariablesResponse.cs
    """
    offset = 0

    # ReturnValue (UInt64 VLQ)
    return_value, consumed = decode_uint64_vlq(response, offset)
    offset += consumed
    logger.debug(f"_parse_read_response: return_value={return_value}")

    if return_value != 0:
        logger.error(f"_parse_read_response: PLC returned error: {return_value}")
        return []

    # Value list: ItemNumber (VLQ) + PValue, terminated by ItemNumber=0
    values: dict[int, bytes] = {}
    while offset < len(response):
        item_nr, consumed = decode_uint32_vlq(response, offset)
        offset += consumed
        if item_nr == 0:
            break
        raw_bytes, consumed = decode_pvalue_to_bytes(response, offset)
        offset += consumed
        values[item_nr] = raw_bytes

    # Error list: ErrorItemNumber (VLQ) + ErrorReturnValue (UInt64 VLQ), terminated by 0
    errors: dict[int, int] = {}
    while offset < len(response):
        err_item_nr, consumed = decode_uint32_vlq(response, offset)
        offset += consumed
        if err_item_nr == 0:
            break
        err_value, consumed = decode_uint64_vlq(response, offset)
        offset += consumed
        errors[err_item_nr] = err_value
        logger.debug(f"_parse_read_response: error item {err_item_nr}: {err_value}")

    # Build result list (1-based item numbers)
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

    Reference: thomas-v2/S7CommPlusDriver/Core/SetMultiVariablesRequest.cs
    """
    # Encode all item addresses and compute total field count
    addresses: list[bytes] = []
    total_field_count = 0
    for db_number, start, data in items:
        access_area = Ids.DB_ACCESS_AREA_BASE + (db_number & 0xFFFF)
        addr_bytes, field_count = encode_item_address(
            access_area=access_area,
            access_sub_area=Ids.DB_VALUE_ACTUAL,
            lids=[start, len(data)],
        )
        addresses.append(addr_bytes)
        total_field_count += field_count

    payload = bytearray()
    # InObjectId (UInt32 fixed = 0, for plain variable writes)
    payload += struct.pack(">I", 0)
    # Item count
    payload += encode_uint32_vlq(len(items))
    # Total field count
    payload += encode_uint32_vlq(total_field_count)
    # Item addresses
    for addr in addresses:
        payload += addr
    # Value list: ItemNumber (1-based) + PValue
    for i, (_, _, data) in enumerate(items, 1):
        payload += encode_uint32_vlq(i)
        payload += encode_pvalue_blob(data)
    # Fill byte
    payload += bytes([0x00])
    # ObjectQualifier
    payload += encode_object_qualifier()
    # Padding
    payload += struct.pack(">I", 0)

    return bytes(payload)


def _parse_write_response(response: bytes) -> None:
    """Parse a SetMultiVariables response payload.

    Args:
        response: Response payload (after the 14-byte response header)

    Raises:
        RuntimeError: If the write failed

    Reference: thomas-v2/S7CommPlusDriver/Core/SetMultiVariablesResponse.cs
    """
    offset = 0

    # ReturnValue (UInt64 VLQ)
    return_value, consumed = decode_uint64_vlq(response, offset)
    offset += consumed
    logger.debug(f"_parse_write_response: return_value={return_value}")

    if return_value != 0:
        raise RuntimeError(f"Write failed with return value {return_value}")

    # Error list: ErrorItemNumber (VLQ) + ErrorReturnValue (UInt64 VLQ)
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
