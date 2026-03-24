"""Tests for S7CommPlus codec (header encoding, typed values, payload builders)."""

import struct
import pytest

from snap7.s7commplus.codec import (
    encode_header,
    decode_header,
    encode_request_header,
    decode_response_header,
    encode_typed_value,
    encode_uint8,
    decode_uint8,
    encode_uint16,
    decode_uint16,
    encode_uint32,
    decode_uint32,
    encode_uint64,
    decode_uint64,
    encode_int16,
    decode_int16,
    encode_int32,
    decode_int32,
    encode_int64,
    decode_int64,
    encode_float32,
    decode_float32,
    encode_float64,
    decode_float64,
    encode_wstring,
    decode_wstring,
    encode_item_address,
    encode_pvalue_blob,
    decode_pvalue_to_bytes,
    encode_object_qualifier,
    _pvalue_element_size,
)
from snap7.s7commplus.protocol import PROTOCOL_ID, DataType, Opcode, FunctionCode, Ids
from snap7.s7commplus.vlq import encode_uint32_vlq, encode_int32_vlq, encode_uint64_vlq, encode_int64_vlq


class TestFrameHeader:
    def test_encode_header(self) -> None:
        header = encode_header(version=0x03, data_length=100)
        assert len(header) == 4
        assert header[0] == PROTOCOL_ID
        assert header[1] == 0x03
        assert struct.unpack(">H", header[2:4])[0] == 100

    def test_decode_header(self) -> None:
        header = encode_header(version=0x03, data_length=256)
        version, length, consumed = decode_header(header)
        assert version == 0x03
        assert length == 256
        assert consumed == 4

    def test_decode_header_with_offset(self) -> None:
        prefix = bytes([0x00, 0x00])
        header = encode_header(version=0x01, data_length=42)
        version, length, consumed = decode_header(prefix + header, offset=2)
        assert version == 0x01
        assert length == 42

    def test_decode_header_wrong_protocol_id(self) -> None:
        bad_header = bytes([0x32, 0x03, 0x00, 0x10])  # S7comm ID, not S7CommPlus
        with pytest.raises(ValueError, match="Invalid protocol ID"):
            decode_header(bad_header)

    def test_decode_header_too_short(self) -> None:
        with pytest.raises(ValueError, match="Not enough data"):
            decode_header(bytes([0x72, 0x03]))


class TestRequestHeader:
    def test_encode_request_header(self) -> None:
        header = encode_request_header(
            function_code=FunctionCode.CREATE_OBJECT,
            sequence_number=1,
            session_id=0,
            transport_flags=0x36,
        )
        assert len(header) == 14
        assert header[0] == Opcode.REQUEST

    def test_roundtrip_request_response_header(self) -> None:
        header = encode_request_header(
            function_code=FunctionCode.GET_MULTI_VARIABLES,
            sequence_number=42,
            session_id=0x12345678,
        )
        result = decode_response_header(header)
        assert result["function_code"] == FunctionCode.GET_MULTI_VARIABLES
        assert result["sequence_number"] == 42
        assert result["session_id"] == 0x12345678
        assert result["bytes_consumed"] == 14

    def test_decode_response_header_too_short(self) -> None:
        with pytest.raises(ValueError, match="Not enough data"):
            decode_response_header(bytes(10))


class TestFixedWidth:
    def test_uint8_roundtrip(self) -> None:
        for val in [0, 1, 127, 255]:
            encoded = encode_uint8(val)
            decoded, consumed = decode_uint8(encoded)
            assert decoded == val
            assert consumed == 1

    def test_uint16_roundtrip(self) -> None:
        for val in [0, 1, 0xFF, 0xFFFF]:
            encoded = encode_uint16(val)
            decoded, consumed = decode_uint16(encoded)
            assert decoded == val
            assert consumed == 2

    def test_uint32_roundtrip(self) -> None:
        for val in [0, 1, 0xFFFF, 0xFFFFFFFF]:
            encoded = encode_uint32(val)
            decoded, consumed = decode_uint32(encoded)
            assert decoded == val
            assert consumed == 4

    def test_uint64_roundtrip(self) -> None:
        for val in [0, 1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF]:
            encoded = encode_uint64(val)
            decoded, consumed = decode_uint64(encoded)
            assert decoded == val
            assert consumed == 8

    def test_int16_roundtrip(self) -> None:
        for val in [0, 1, -1, -32768, 32767]:
            encoded = encode_int16(val)
            decoded, consumed = decode_int16(encoded)
            assert decoded == val
            assert consumed == 2

    def test_int32_roundtrip(self) -> None:
        for val in [0, 1, -1, -2147483648, 2147483647]:
            encoded = encode_int32(val)
            decoded, consumed = decode_int32(encoded)
            assert decoded == val
            assert consumed == 4

    def test_int64_roundtrip(self) -> None:
        for val in [0, 1, -1, -(2**63), 2**63 - 1]:
            encoded = encode_int64(val)
            decoded, consumed = decode_int64(encoded)
            assert decoded == val
            assert consumed == 8

    def test_float32_roundtrip(self) -> None:
        for val in [0.0, 1.0, -1.0, 3.14]:
            encoded = encode_float32(val)
            decoded, consumed = decode_float32(encoded)
            assert abs(decoded - val) < 1e-6
            assert consumed == 4

    def test_float64_roundtrip(self) -> None:
        for val in [0.0, 1.0, -1.0, 3.141592653589793]:
            encoded = encode_float64(val)
            decoded, consumed = decode_float64(encoded)
            assert decoded == val
            assert consumed == 8

    def test_uint8_with_offset(self) -> None:
        data = bytes([0xFF, 42, 0xFF])
        decoded, consumed = decode_uint8(data, offset=1)
        assert decoded == 42

    def test_uint64_with_offset(self) -> None:
        prefix = bytes(4)
        data = prefix + encode_uint64(0x123456789ABCDEF0)
        decoded, consumed = decode_uint64(data, offset=4)
        assert decoded == 0x123456789ABCDEF0

    def test_int16_with_offset(self) -> None:
        prefix = bytes(3)
        data = prefix + encode_int16(-1000)
        decoded, consumed = decode_int16(data, offset=3)
        assert decoded == -1000

    def test_int32_with_offset(self) -> None:
        prefix = bytes(2)
        data = prefix + encode_int32(-100000)
        decoded, consumed = decode_int32(data, offset=2)
        assert decoded == -100000

    def test_int64_with_offset(self) -> None:
        prefix = bytes(5)
        data = prefix + encode_int64(-(2**50))
        decoded, consumed = decode_int64(data, offset=5)
        assert decoded == -(2**50)

    def test_float32_with_offset(self) -> None:
        prefix = bytes(1)
        data = prefix + encode_float32(2.5)
        decoded, consumed = decode_float32(data, offset=1)
        assert abs(decoded - 2.5) < 1e-6

    def test_float64_with_offset(self) -> None:
        prefix = bytes(3)
        data = prefix + encode_float64(1.23456789)
        decoded, consumed = decode_float64(data, offset=3)
        assert decoded == 1.23456789


class TestWString:
    def test_ascii(self) -> None:
        encoded = encode_wstring("hello")
        decoded, consumed = decode_wstring(encoded, 0, len(encoded))
        assert decoded == "hello"

    def test_unicode(self) -> None:
        encoded = encode_wstring("Ölprüfung")
        decoded, consumed = decode_wstring(encoded, 0, len(encoded))
        assert decoded == "Ölprüfung"

    def test_empty(self) -> None:
        encoded = encode_wstring("")
        assert encoded == b""
        decoded, consumed = decode_wstring(encoded, 0, 0)
        assert decoded == ""


class TestTypedValue:
    def test_null(self) -> None:
        encoded = encode_typed_value(DataType.NULL, None)
        assert encoded == bytes([DataType.NULL])

    def test_bool_true(self) -> None:
        encoded = encode_typed_value(DataType.BOOL, True)
        assert encoded == bytes([DataType.BOOL, 0x01])

    def test_bool_false(self) -> None:
        encoded = encode_typed_value(DataType.BOOL, False)
        assert encoded == bytes([DataType.BOOL, 0x00])

    def test_usint(self) -> None:
        encoded = encode_typed_value(DataType.USINT, 42)
        assert encoded == bytes([DataType.USINT, 42])

    def test_byte(self) -> None:
        encoded = encode_typed_value(DataType.BYTE, 0xAB)
        assert encoded == bytes([DataType.BYTE, 0xAB])

    def test_uint(self) -> None:
        encoded = encode_typed_value(DataType.UINT, 0x1234)
        assert encoded == bytes([DataType.UINT]) + struct.pack(">H", 0x1234)

    def test_word(self) -> None:
        encoded = encode_typed_value(DataType.WORD, 0xBEEF)
        assert encoded == bytes([DataType.WORD]) + struct.pack(">H", 0xBEEF)

    def test_udint(self) -> None:
        encoded = encode_typed_value(DataType.UDINT, 100000)
        assert encoded[0] == DataType.UDINT
        # Rest is VLQ-encoded
        assert len(encoded) > 1

    def test_dword(self) -> None:
        encoded = encode_typed_value(DataType.DWORD, 0xDEADBEEF)
        assert encoded[0] == DataType.DWORD

    def test_ulint(self) -> None:
        encoded = encode_typed_value(DataType.ULINT, 2**40)
        assert encoded[0] == DataType.ULINT

    def test_lword(self) -> None:
        encoded = encode_typed_value(DataType.LWORD, 0xCAFEBABE12345678)
        assert encoded[0] == DataType.LWORD

    def test_sint(self) -> None:
        encoded = encode_typed_value(DataType.SINT, -42)
        assert encoded == bytes([DataType.SINT]) + struct.pack(">b", -42)

    def test_int(self) -> None:
        encoded = encode_typed_value(DataType.INT, -1000)
        assert encoded == bytes([DataType.INT]) + struct.pack(">h", -1000)

    def test_dint(self) -> None:
        encoded = encode_typed_value(DataType.DINT, -100000)
        assert encoded[0] == DataType.DINT

    def test_lint(self) -> None:
        encoded = encode_typed_value(DataType.LINT, -(2**40))
        assert encoded[0] == DataType.LINT

    def test_real(self) -> None:
        encoded = encode_typed_value(DataType.REAL, 1.0)
        assert encoded == bytes([DataType.REAL]) + struct.pack(">f", 1.0)

    def test_lreal(self) -> None:
        encoded = encode_typed_value(DataType.LREAL, 3.14)
        assert encoded == bytes([DataType.LREAL]) + struct.pack(">d", 3.14)

    def test_timestamp(self) -> None:
        ts = 0x0001020304050607
        encoded = encode_typed_value(DataType.TIMESTAMP, ts)
        assert encoded == bytes([DataType.TIMESTAMP]) + struct.pack(">Q", ts)

    def test_timespan(self) -> None:
        encoded = encode_typed_value(DataType.TIMESPAN, -5000)
        assert encoded[0] == DataType.TIMESPAN

    def test_rid(self) -> None:
        encoded = encode_typed_value(DataType.RID, 0x12345678)
        assert encoded == bytes([DataType.RID]) + struct.pack(">I", 0x12345678)

    def test_aid(self) -> None:
        encoded = encode_typed_value(DataType.AID, 306)
        assert encoded[0] == DataType.AID

    def test_wstring(self) -> None:
        encoded = encode_typed_value(DataType.WSTRING, "test")
        assert encoded[0] == DataType.WSTRING
        assert b"test" in encoded

    def test_blob(self) -> None:
        data = bytes([1, 2, 3, 4])
        encoded = encode_typed_value(DataType.BLOB, data)
        assert encoded[0] == DataType.BLOB
        assert encoded.endswith(data)

    def test_unsupported_type(self) -> None:
        with pytest.raises(ValueError, match="Unsupported DataType"):
            encode_typed_value(0xFF, None)


class TestItemAddress:
    def test_basic_db_access(self) -> None:
        addr_bytes, field_count = encode_item_address(
            access_area=Ids.DB_ACCESS_AREA_BASE + 1,
            access_sub_area=Ids.DB_VALUE_ACTUAL,
        )
        assert isinstance(addr_bytes, bytes)
        assert len(addr_bytes) > 0
        # No LIDs, so field_count = 4 (SymbolCrc + AccessArea + NumLIDs + AccessSubArea)
        assert field_count == 4

    def test_with_lids(self) -> None:
        addr_bytes, field_count = encode_item_address(
            access_area=Ids.DB_ACCESS_AREA_BASE + 1,
            access_sub_area=Ids.DB_VALUE_ACTUAL,
            lids=[1, 4],
        )
        assert field_count == 6  # 4 + 2 LIDs

    def test_custom_symbol_crc(self) -> None:
        addr_bytes, field_count = encode_item_address(
            access_area=Ids.DB_ACCESS_AREA_BASE + 1,
            access_sub_area=Ids.DB_VALUE_ACTUAL,
            symbol_crc=0x1234,
        )
        # First bytes should be VLQ(0x1234) which is non-zero
        assert addr_bytes[0] != 0
        assert field_count == 4


class TestPValueBlob:
    def test_basic_blob(self) -> None:
        data = bytes([1, 2, 3, 4])
        encoded = encode_pvalue_blob(data)
        assert encoded[0] == 0x00  # flags
        assert encoded[1] == DataType.BLOB
        assert encoded.endswith(data)

    def test_empty_blob(self) -> None:
        encoded = encode_pvalue_blob(b"")
        assert encoded[0] == 0x00
        assert encoded[1] == DataType.BLOB

    def test_roundtrip_with_decode(self) -> None:
        data = bytes([0xDE, 0xAD, 0xBE, 0xEF])
        encoded = encode_pvalue_blob(data)
        decoded, consumed = decode_pvalue_to_bytes(encoded, 0)
        assert decoded == data
        assert consumed == len(encoded)


class TestDecodePValue:
    """Test decode_pvalue_to_bytes for all scalar and array type branches."""

    def test_null(self) -> None:
        data = bytes([0x00, DataType.NULL])
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == b""
        assert consumed == 2

    def test_bool_true(self) -> None:
        data = bytes([0x00, DataType.BOOL, 0x01])
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == bytes([0x01])
        assert consumed == 3

    def test_bool_false(self) -> None:
        data = bytes([0x00, DataType.BOOL, 0x00])
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == bytes([0x00])

    def test_usint(self) -> None:
        data = bytes([0x00, DataType.USINT, 42])
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == bytes([42])
        assert consumed == 3

    def test_byte(self) -> None:
        data = bytes([0x00, DataType.BYTE, 0xAB])
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == bytes([0xAB])

    def test_sint(self) -> None:
        data = bytes([0x00, DataType.SINT, 0xD6])  # -42 as unsigned byte
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == bytes([0xD6])

    def test_uint(self) -> None:
        raw = struct.pack(">H", 0x1234)
        data = bytes([0x00, DataType.UINT]) + raw
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == raw

    def test_word(self) -> None:
        raw = struct.pack(">H", 0xBEEF)
        data = bytes([0x00, DataType.WORD]) + raw
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == raw

    def test_int(self) -> None:
        raw = struct.pack(">H", 0xFC18)  # -1000 as unsigned
        data = bytes([0x00, DataType.INT]) + raw
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == raw

    def test_udint(self) -> None:
        vlq = encode_uint32_vlq(100000)
        data = bytes([0x00, DataType.UDINT]) + vlq
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == struct.pack(">I", 100000)

    def test_dword(self) -> None:
        vlq = encode_uint32_vlq(0xDEADBEEF)
        data = bytes([0x00, DataType.DWORD]) + vlq
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == struct.pack(">I", 0xDEADBEEF)

    def test_dint_positive(self) -> None:
        vlq = encode_int32_vlq(12345)
        data = bytes([0x00, DataType.DINT]) + vlq
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == struct.pack(">i", 12345)

    def test_dint_negative(self) -> None:
        vlq = encode_int32_vlq(-100000)
        data = bytes([0x00, DataType.DINT]) + vlq
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == struct.pack(">i", -100000)

    def test_real(self) -> None:
        raw = struct.pack(">f", 3.14)
        data = bytes([0x00, DataType.REAL]) + raw
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == raw

    def test_lreal(self) -> None:
        raw = struct.pack(">d", 2.718281828)
        data = bytes([0x00, DataType.LREAL]) + raw
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == raw

    def test_ulint(self) -> None:
        vlq = encode_uint64_vlq(2**40)
        data = bytes([0x00, DataType.ULINT]) + vlq
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == struct.pack(">Q", 2**40)

    def test_lword(self) -> None:
        vlq = encode_uint64_vlq(0xCAFEBABE12345678)
        data = bytes([0x00, DataType.LWORD]) + vlq
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == struct.pack(">Q", 0xCAFEBABE12345678)

    def test_lint_positive(self) -> None:
        vlq = encode_int64_vlq(2**50)
        data = bytes([0x00, DataType.LINT]) + vlq
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == struct.pack(">q", 2**50)

    def test_lint_negative(self) -> None:
        vlq = encode_int64_vlq(-(2**40))
        data = bytes([0x00, DataType.LINT]) + vlq
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == struct.pack(">q", -(2**40))

    def test_timestamp(self) -> None:
        ts = 0x0001020304050607
        raw = struct.pack(">Q", ts)
        data = bytes([0x00, DataType.TIMESTAMP]) + raw
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == raw
        assert consumed == 10  # 2 header + 8 bytes

    def test_timespan_positive(self) -> None:
        vlq = encode_int64_vlq(5000000)
        data = bytes([0x00, DataType.TIMESPAN]) + vlq
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == struct.pack(">q", 5000000)

    def test_timespan_negative(self) -> None:
        vlq = encode_int64_vlq(-5000000)
        data = bytes([0x00, DataType.TIMESPAN]) + vlq
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == struct.pack(">q", -5000000)

    def test_rid(self) -> None:
        raw = struct.pack(">I", 0x12345678)
        data = bytes([0x00, DataType.RID]) + raw
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == raw

    def test_aid(self) -> None:
        vlq = encode_uint32_vlq(306)
        data = bytes([0x00, DataType.AID]) + vlq
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == struct.pack(">I", 306)

    def test_blob(self) -> None:
        blob_data = bytes([0xDE, 0xAD, 0xBE, 0xEF])
        vlq_len = encode_uint32_vlq(len(blob_data))
        data = bytes([0x00, DataType.BLOB]) + vlq_len + blob_data
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == blob_data

    def test_wstring(self) -> None:
        text = "hello".encode("utf-8")
        vlq_len = encode_uint32_vlq(len(text))
        data = bytes([0x00, DataType.WSTRING]) + vlq_len + text
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == text

    def test_struct_nested(self) -> None:
        # Struct with 2 USINT elements
        vlq_count = encode_uint32_vlq(2)
        elem1 = bytes([0x00, DataType.USINT, 0x0A])
        elem2 = bytes([0x00, DataType.USINT, 0x14])
        data = bytes([0x00, DataType.STRUCT]) + vlq_count + elem1 + elem2
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == bytes([0x0A, 0x14])

    def test_unsupported_type(self) -> None:
        data = bytes([0x00, 0xFF])
        with pytest.raises(ValueError, match="Unsupported PValue datatype"):
            decode_pvalue_to_bytes(data, 0)

    def test_too_short_header(self) -> None:
        with pytest.raises(ValueError, match="Not enough data for PValue header"):
            decode_pvalue_to_bytes(bytes([0x00]), 0)

    def test_with_offset(self) -> None:
        prefix = bytes([0xFF, 0xFF, 0xFF])
        pvalue = bytes([0x00, DataType.USINT, 42])
        result, consumed = decode_pvalue_to_bytes(prefix + pvalue, 3)
        assert result == bytes([42])

    # -- Array tests --

    def test_array_fixed_size_usint(self) -> None:
        count_vlq = encode_uint32_vlq(3)
        elements = bytes([10, 20, 30])
        data = bytes([0x10, DataType.USINT]) + count_vlq + elements
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == elements

    def test_array_fixed_size_uint(self) -> None:
        count_vlq = encode_uint32_vlq(2)
        elements = struct.pack(">HH", 1000, 2000)
        data = bytes([0x10, DataType.UINT]) + count_vlq + elements
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == elements

    def test_array_fixed_size_real(self) -> None:
        count_vlq = encode_uint32_vlq(2)
        elements = struct.pack(">ff", 1.0, 2.0)
        data = bytes([0x10, DataType.REAL]) + count_vlq + elements
        result, consumed = decode_pvalue_to_bytes(data, 0)
        assert result == elements

    def test_array_variable_length_udint(self) -> None:
        # Variable-length array (VLQ-encoded elements)
        count_vlq = encode_uint32_vlq(2)
        elem1 = encode_uint32_vlq(100)
        elem2 = encode_uint32_vlq(200)
        data = bytes([0x10, DataType.UDINT]) + count_vlq + elem1 + elem2
        result, consumed = decode_pvalue_to_bytes(data, 0)
        # Result re-encodes each element as VLQ
        assert result == encode_uint32_vlq(100) + encode_uint32_vlq(200)


class TestPValueElementSize:
    def test_single_byte_types(self) -> None:
        for dt in (DataType.BOOL, DataType.USINT, DataType.BYTE, DataType.SINT):
            assert _pvalue_element_size(dt) == 1

    def test_two_byte_types(self) -> None:
        for dt in (DataType.UINT, DataType.WORD, DataType.INT):
            assert _pvalue_element_size(dt) == 2

    def test_four_byte_types(self) -> None:
        assert _pvalue_element_size(DataType.REAL) == 4
        assert _pvalue_element_size(DataType.RID) == 4

    def test_eight_byte_types(self) -> None:
        assert _pvalue_element_size(DataType.LREAL) == 8
        assert _pvalue_element_size(DataType.TIMESTAMP) == 8

    def test_variable_length_types(self) -> None:
        for dt in (DataType.UDINT, DataType.DWORD, DataType.BLOB, DataType.WSTRING, DataType.STRUCT):
            assert _pvalue_element_size(dt) == 0


class TestObjectQualifier:
    def test_encode(self) -> None:
        result = encode_object_qualifier()
        assert isinstance(result, bytes)
        assert len(result) > 0
        # Starts with ObjectQualifier ID (1256) as uint32 big-endian
        assert result[:4] == struct.pack(">I", Ids.OBJECT_QUALIFIER)
        # Ends with null terminator
        assert result[-1] == 0x00
