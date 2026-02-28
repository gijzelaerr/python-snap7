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
from typing import Any, Optional

from .connection import S7CommPlusConnection
from .protocol import FunctionCode
from .vlq import encode_uint32_vlq, decode_uint32_vlq

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
        local_tsap = 0x0100
        remote_tsap = 0x0100 | (rack << 5) | slot

        self._connection = S7CommPlusConnection(
            host=host,
            port=port,
            local_tsap=local_tsap,
            remote_tsap=remote_tsap,
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

        # Build GetMultiVariables request payload
        object_id = 0x00010000 | (db_number & 0xFFFF)
        payload = bytearray()
        payload += encode_uint32_vlq(1)  # 1 item
        payload += encode_uint32_vlq(object_id)
        payload += encode_uint32_vlq(start)
        payload += encode_uint32_vlq(size)

        response = self._connection.send_request(
            FunctionCode.GET_MULTI_VARIABLES, bytes(payload)
        )

        # Parse response
        offset = 0
        # Skip return code
        _, consumed = decode_uint32_vlq(response, offset)
        offset += consumed

        # Item count
        item_count, consumed = decode_uint32_vlq(response, offset)
        offset += consumed

        if item_count == 0:
            return b""

        # First item: status + data_length + data
        status, consumed = decode_uint32_vlq(response, offset)
        offset += consumed

        data_length, consumed = decode_uint32_vlq(response, offset)
        offset += consumed

        if status != 0:
            raise RuntimeError(f"Read failed with status {status}")

        return response[offset : offset + data_length]

    def db_write(self, db_number: int, start: int, data: bytes) -> None:
        """Write raw bytes to a data block.

        Args:
            db_number: Data block number
            start: Start byte offset
            data: Bytes to write
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        object_id = 0x00010000 | (db_number & 0xFFFF)
        payload = bytearray()
        payload += encode_uint32_vlq(1)  # 1 item
        payload += encode_uint32_vlq(object_id)
        payload += encode_uint32_vlq(start)
        payload += encode_uint32_vlq(len(data))
        payload += data

        response = self._connection.send_request(
            FunctionCode.SET_MULTI_VARIABLES, bytes(payload)
        )

        # Parse response - check return code
        offset = 0
        return_code, consumed = decode_uint32_vlq(response, offset)
        offset += consumed

        if return_code != 0:
            raise RuntimeError(f"Write failed with return code {return_code}")

    def db_read_multi(
        self, items: list[tuple[int, int, int]]
    ) -> list[bytes]:
        """Read multiple data block regions in a single request.

        Args:
            items: List of (db_number, start_offset, size) tuples

        Returns:
            List of raw bytes for each item
        """
        if self._connection is None:
            raise RuntimeError("Not connected")

        payload = bytearray()
        payload += encode_uint32_vlq(len(items))
        for db_number, start, size in items:
            object_id = 0x00010000 | (db_number & 0xFFFF)
            payload += encode_uint32_vlq(object_id)
            payload += encode_uint32_vlq(start)
            payload += encode_uint32_vlq(size)

        response = self._connection.send_request(
            FunctionCode.GET_MULTI_VARIABLES, bytes(payload)
        )

        # Parse response
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

        return self._connection.send_request(FunctionCode.EXPLORE, b"")

    # -- Context manager --

    def __enter__(self) -> "S7CommPlusClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.disconnect()
