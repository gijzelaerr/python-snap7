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

    def explore(self) -> bytes:
        """Browse the PLC object tree.

        Returns:
            Raw response payload
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        response = self._connection.send_request(FunctionCode.EXPLORE, b"")
        return response

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
