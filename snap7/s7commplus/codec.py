"""
S7CommPlus data encoding and decoding.

Provides serialization for the S7CommPlus wire format including:
- Fixed-width integers (big-endian)
- VLQ-encoded integers
- Floating point values
- Strings (UTF-8 encoded WStrings)
- Blobs (raw byte arrays)
- S7CommPlus frame header

Reference: thomas-v2/S7CommPlusDriver/Core/S7p.cs
"""

import struct
from typing import Any

from .protocol import PROTOCOL_ID, DataType, Ids
from .vlq import (
    encode_uint32_vlq,
    decode_uint32_vlq,
    encode_int32_vlq,
    encode_uint64_vlq,
    decode_uint64_vlq,
    encode_int64_vlq,
)


def encode_header(version: int, data_length: int) -> bytes:
    """Encode an S7CommPlus frame header.

    Header format (4 bytes)::

        [0]   Protocol ID: 0x72
        [1]   Protocol version
        [2-3] Data length (big-endian uint16)

    Args:
        version: Protocol version byte
        data_length: Length of data following the header

    Returns:
        4-byte header
    """
    return struct.pack(">BBH", PROTOCOL_ID, version, data_length)


def decode_header(data: bytes, offset: int = 0) -> tuple[int, int, int]:
    """Decode an S7CommPlus frame header.

    Args:
        data: Buffer containing the header
        offset: Starting position

    Returns:
        Tuple of (protocol_version, data_length, bytes_consumed)

    Raises:
        ValueError: If protocol ID is not 0x72
    """
    if len(data) - offset < 4:
        raise ValueError("Not enough data for S7CommPlus header")

    proto_id, version, length = struct.unpack_from(">BBH", data, offset)

    if proto_id != PROTOCOL_ID:
        raise ValueError(f"Invalid protocol ID: {proto_id:#04x}, expected {PROTOCOL_ID:#04x}")

    return version, length, 4


def encode_request_header(
    function_code: int,
    sequence_number: int,
    session_id: int = 0,
    transport_flags: int = 0x36,
) -> bytes:
    """Encode an S7CommPlus request header (after the frame header).

    Request header format::

        [0]     Opcode: 0x31 (Request)
        [1-2]   Reserved: 0x0000
        [3-4]   Function code (big-endian uint16)
        [5-6]   Reserved: 0x0000
        [7-8]   Sequence number (big-endian uint16)
        [9-12]  Session ID (big-endian uint32)
        [13]    Transport flags

    Args:
        function_code: S7CommPlus function code
        sequence_number: Request sequence number
        session_id: Session identifier (0 for initial connection)
        transport_flags: Transport flags byte

    Returns:
        14-byte request header
    """
    from .protocol import Opcode

    return struct.pack(
        ">BHHHHIB",
        Opcode.REQUEST,
        0x0000,  # Reserved
        function_code,
        0x0000,  # Reserved
        sequence_number,
        session_id,
        transport_flags,
    )


def decode_response_header(data: bytes, offset: int = 0) -> dict[str, Any]:
    """Decode an S7CommPlus response header.

    Args:
        data: Buffer containing the response
        offset: Starting position

    Returns:
        Dictionary with opcode, function_code, sequence_number, session_id,
        transport_flags, and bytes_consumed
    """
    if len(data) - offset < 14:
        raise ValueError("Not enough data for S7CommPlus response header")

    opcode, reserved1, function_code, reserved2, seq_num, session_id, transport_flags = struct.unpack_from(
        ">BHHHHIB", data, offset
    )

    return {
        "opcode": opcode,
        "function_code": function_code,
        "sequence_number": seq_num,
        "session_id": session_id,
        "transport_flags": transport_flags,
        "bytes_consumed": 14,
    }


# -- Fixed-width encoding (big-endian) --


def encode_uint8(value: int) -> bytes:
    return struct.pack(">B", value)


def decode_uint8(data: bytes, offset: int = 0) -> tuple[int, int]:
    return struct.unpack_from(">B", data, offset)[0], 1


def encode_uint16(value: int) -> bytes:
    return struct.pack(">H", value)


def decode_uint16(data: bytes, offset: int = 0) -> tuple[int, int]:
    return struct.unpack_from(">H", data, offset)[0], 2


def encode_uint32(value: int) -> bytes:
    return struct.pack(">I", value)


def decode_uint32(data: bytes, offset: int = 0) -> tuple[int, int]:
    return struct.unpack_from(">I", data, offset)[0], 4


def encode_uint64(value: int) -> bytes:
    return struct.pack(">Q", value)


def decode_uint64(data: bytes, offset: int = 0) -> tuple[int, int]:
    return struct.unpack_from(">Q", data, offset)[0], 8


def encode_int16(value: int) -> bytes:
    return struct.pack(">h", value)


def decode_int16(data: bytes, offset: int = 0) -> tuple[int, int]:
    return struct.unpack_from(">h", data, offset)[0], 2


def encode_int32(value: int) -> bytes:
    return struct.pack(">i", value)


def decode_int32(data: bytes, offset: int = 0) -> tuple[int, int]:
    return struct.unpack_from(">i", data, offset)[0], 4


def encode_int64(value: int) -> bytes:
    return struct.pack(">q", value)


def decode_int64(data: bytes, offset: int = 0) -> tuple[int, int]:
    return struct.unpack_from(">q", data, offset)[0], 8


def encode_float32(value: float) -> bytes:
    return struct.pack(">f", value)


def decode_float32(data: bytes, offset: int = 0) -> tuple[float, int]:
    return struct.unpack_from(">f", data, offset)[0], 4


def encode_float64(value: float) -> bytes:
    return struct.pack(">d", value)


def decode_float64(data: bytes, offset: int = 0) -> tuple[float, int]:
    return struct.unpack_from(">d", data, offset)[0], 8


# -- String encoding --


def encode_wstring(value: str) -> bytes:
    """Encode a string as UTF-8 (S7CommPlus WString wire format)."""
    return value.encode("utf-8")


def decode_wstring(data: bytes, offset: int, length: int) -> tuple[str, int]:
    """Decode a UTF-8 string.

    Args:
        data: Buffer
        offset: Start position
        length: Number of bytes to decode

    Returns:
        Tuple of (decoded_string, bytes_consumed)
    """
    return data[offset : offset + length].decode("utf-8"), length


# -- Typed value encoding --


def encode_typed_value(datatype: int, value: Any) -> bytes:
    """Encode a value with its type tag.

    This prepends the DataType byte before the encoded value, which is how
    attribute values are serialized in the S7CommPlus object model.

    Args:
        datatype: DataType enum value
        value: Value to encode

    Returns:
        Type-tagged encoded value
    """
    tag = struct.pack(">B", datatype)

    if datatype == DataType.NULL:
        return tag
    elif datatype == DataType.BOOL:
        return tag + struct.pack(">B", 1 if value else 0)
    elif datatype == DataType.USINT or datatype == DataType.BYTE:
        return tag + struct.pack(">B", value)
    elif datatype == DataType.UINT or datatype == DataType.WORD:
        return tag + struct.pack(">H", value)
    elif datatype == DataType.UDINT or datatype == DataType.DWORD:
        return tag + encode_uint32_vlq(value)
    elif datatype == DataType.ULINT or datatype == DataType.LWORD:
        return tag + encode_uint64_vlq(value)
    elif datatype == DataType.SINT:
        return tag + struct.pack(">b", value)
    elif datatype == DataType.INT:
        return tag + struct.pack(">h", value)
    elif datatype == DataType.DINT:
        return tag + encode_int32_vlq(value)
    elif datatype == DataType.LINT:
        return tag + encode_int64_vlq(value)
    elif datatype == DataType.REAL:
        return tag + struct.pack(">f", value)
    elif datatype == DataType.LREAL:
        return tag + struct.pack(">d", value)
    elif datatype == DataType.TIMESTAMP:
        return tag + struct.pack(">Q", value)
    elif datatype == DataType.TIMESPAN:
        return tag + encode_int64_vlq(value)
    elif datatype == DataType.RID:
        return tag + struct.pack(">I", value)
    elif datatype == DataType.AID:
        return tag + encode_uint32_vlq(value)
    elif datatype == DataType.WSTRING:
        encoded: bytes = value.encode("utf-8")
        return tag + encode_uint32_vlq(len(encoded)) + encoded
    elif datatype == DataType.BLOB:
        return bytes(tag + encode_uint32_vlq(len(value)) + value)
    else:
        raise ValueError(f"Unsupported DataType for encoding: {datatype:#04x}")


# -- S7CommPlus request/response payload helpers --


def encode_object_qualifier() -> bytes:
    """Encode the S7CommPlus ObjectQualifier structure.

    This fixed structure is appended to GetMultiVariables and
    SetMultiVariables requests.

    Reference: thomas-v2/S7CommPlusDriver/Core/S7p.cs EncodeObjectQualifier
    """
    result = bytearray()
    result += struct.pack(">I", Ids.OBJECT_QUALIFIER)
    # ParentRID = RID(0)
    result += encode_uint32_vlq(Ids.PARENT_RID)
    result += bytes([0x00, DataType.RID]) + struct.pack(">I", 0)
    # CompositionAID = AID(0)
    result += encode_uint32_vlq(Ids.COMPOSITION_AID)
    result += bytes([0x00, DataType.AID]) + encode_uint32_vlq(0)
    # KeyQualifier = UDInt(0)
    result += encode_uint32_vlq(Ids.KEY_QUALIFIER)
    result += bytes([0x00, DataType.UDINT]) + encode_uint32_vlq(0)
    # Terminator
    result += bytes([0x00])
    return bytes(result)


def encode_item_address(
    access_area: int,
    access_sub_area: int,
    lids: list[int] | None = None,
    symbol_crc: int = 0,
) -> tuple[bytes, int]:
    """Encode an S7CommPlus ItemAddress for variable access.

    Args:
        access_area: Access area ID (e.g., 0x8A0E0001 for DB1)
        access_sub_area: Sub-area ID (e.g., Ids.DB_VALUE_ACTUAL)
        lids: Additional LID values for sub-addressing
        symbol_crc: Symbol CRC (0 for no CRC check)

    Returns:
        Tuple of (encoded_bytes, field_count)

    Reference: thomas-v2/S7CommPlusDriver/ClientApi/ItemAddress.cs
    """
    if lids is None:
        lids = []
    result = bytearray()
    result += encode_uint32_vlq(symbol_crc)
    result += encode_uint32_vlq(access_area)
    result += encode_uint32_vlq(len(lids) + 1)  # +1 for AccessSubArea
    result += encode_uint32_vlq(access_sub_area)
    for lid in lids:
        result += encode_uint32_vlq(lid)
    field_count = 4 + len(lids)  # SymbolCrc + AccessArea + NumLIDs + AccessSubArea + LIDs
    return bytes(result), field_count


def encode_pvalue_blob(data: bytes) -> bytes:
    """Encode raw bytes as a BLOB PValue.

    PValue format: [flags:1][datatype:1][length:VLQ][data]
    """
    result = bytearray()
    result += bytes([0x00, DataType.BLOB])
    result += encode_uint32_vlq(len(data))
    result += data
    return bytes(result)


def decode_pvalue_to_bytes(data: bytes, offset: int) -> tuple[bytes, int]:
    """Decode a PValue from S7CommPlus response to raw bytes.

    Supports scalar types and BLOBs. Returns the raw big-endian bytes
    of the value regardless of type.

    Args:
        data: Response buffer
        offset: Position of the PValue

    Returns:
        Tuple of (raw_bytes, bytes_consumed)
    """
    if offset + 2 > len(data):
        raise ValueError("Not enough data for PValue header")

    flags = data[offset]
    datatype = data[offset + 1]
    consumed = 2

    is_array = bool(flags & 0x10)

    if is_array:
        # Array: read count then elements
        count, c = decode_uint32_vlq(data, offset + consumed)
        consumed += c
        elem_size = _pvalue_element_size(datatype)
        if elem_size > 0:
            raw = data[offset + consumed : offset + consumed + count * elem_size]
            consumed += count * elem_size
            return bytes(raw), consumed
        else:
            # Variable-length elements (VLQ encoded)
            result = bytearray()
            for _ in range(count):
                val, c = decode_uint32_vlq(data, offset + consumed)
                consumed += c
                result += encode_uint32_vlq(val)
            return bytes(result), consumed

    # Scalar types
    if datatype == DataType.NULL:
        return b"", consumed
    elif datatype == DataType.BOOL:
        return data[offset + consumed : offset + consumed + 1], consumed + 1
    elif datatype in (DataType.USINT, DataType.BYTE, DataType.SINT):
        return data[offset + consumed : offset + consumed + 1], consumed + 1
    elif datatype in (DataType.UINT, DataType.WORD, DataType.INT):
        return data[offset + consumed : offset + consumed + 2], consumed + 2
    elif datatype in (DataType.UDINT, DataType.DWORD):
        val, c = decode_uint32_vlq(data, offset + consumed)
        consumed += c
        return struct.pack(">I", val), consumed
    elif datatype in (DataType.DINT,):
        # Signed VLQ
        from .vlq import decode_int32_vlq

        val, c = decode_int32_vlq(data, offset + consumed)
        consumed += c
        return struct.pack(">i", val), consumed
    elif datatype == DataType.REAL:
        return data[offset + consumed : offset + consumed + 4], consumed + 4
    elif datatype == DataType.LREAL:
        return data[offset + consumed : offset + consumed + 8], consumed + 8
    elif datatype in (DataType.ULINT, DataType.LWORD):
        val, c = decode_uint64_vlq(data, offset + consumed)
        consumed += c
        return struct.pack(">Q", val), consumed
    elif datatype in (DataType.LINT,):
        from .vlq import decode_int64_vlq

        val, c = decode_int64_vlq(data, offset + consumed)
        consumed += c
        return struct.pack(">q", val), consumed
    elif datatype == DataType.TIMESTAMP:
        return data[offset + consumed : offset + consumed + 8], consumed + 8
    elif datatype == DataType.TIMESPAN:
        from .vlq import decode_int64_vlq

        val, c = decode_int64_vlq(data, offset + consumed)
        consumed += c
        return struct.pack(">q", val), consumed
    elif datatype == DataType.RID:
        return data[offset + consumed : offset + consumed + 4], consumed + 4
    elif datatype == DataType.AID:
        val, c = decode_uint32_vlq(data, offset + consumed)
        consumed += c
        return struct.pack(">I", val), consumed
    elif datatype == DataType.BLOB:
        length, c = decode_uint32_vlq(data, offset + consumed)
        consumed += c
        raw = data[offset + consumed : offset + consumed + length]
        consumed += length
        return bytes(raw), consumed
    elif datatype == DataType.WSTRING:
        length, c = decode_uint32_vlq(data, offset + consumed)
        consumed += c
        raw = data[offset + consumed : offset + consumed + length]
        consumed += length
        return bytes(raw), consumed
    elif datatype == DataType.STRUCT:
        # Struct: read count, then nested PValues
        count, c = decode_uint32_vlq(data, offset + consumed)
        consumed += c
        result = bytearray()
        for _ in range(count):
            val_bytes, c = decode_pvalue_to_bytes(data, offset + consumed)
            consumed += c
            result += val_bytes
        return bytes(result), consumed
    else:
        raise ValueError(f"Unsupported PValue datatype: {datatype:#04x}")


def _pvalue_element_size(datatype: int) -> int:
    """Return the fixed byte size for a PValue array element, or 0 for variable-length."""
    if datatype in (DataType.BOOL, DataType.USINT, DataType.BYTE, DataType.SINT):
        return 1
    elif datatype in (DataType.UINT, DataType.WORD, DataType.INT):
        return 2
    elif datatype in (DataType.REAL,):
        return 4
    elif datatype in (DataType.LREAL, DataType.TIMESTAMP):
        return 8
    elif datatype in (DataType.RID,):
        return 4
    else:
        return 0  # Variable-length (VLQ encoded)
