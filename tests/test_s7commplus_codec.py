"""Tests for S7CommPlus codec (header encoding, typed values)."""

import struct
import pytest

from snap7.s7commplus.codec import (
    encode_header,
    decode_header,
    encode_request_header,
    decode_response_header,
    encode_typed_value,
    encode_uint16,
    decode_uint16,
    encode_uint32,
    decode_uint32,
    encode_float32,
    decode_float32,
    encode_float64,
    decode_float64,
    encode_wstring,
    decode_wstring,
)
from snap7.s7commplus.protocol import PROTOCOL_ID, DataType, Opcode, FunctionCode


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


class TestFixedWidth:
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

    def test_uint(self) -> None:
        encoded = encode_typed_value(DataType.UINT, 0x1234)
        assert encoded == bytes([DataType.UINT]) + struct.pack(">H", 0x1234)

    def test_real(self) -> None:
        encoded = encode_typed_value(DataType.REAL, 1.0)
        assert encoded == bytes([DataType.REAL]) + struct.pack(">f", 1.0)

    def test_lreal(self) -> None:
        encoded = encode_typed_value(DataType.LREAL, 3.14)
        assert encoded == bytes([DataType.LREAL]) + struct.pack(">d", 3.14)

    def test_wstring(self) -> None:
        encoded = encode_typed_value(DataType.WSTRING, "test")
        assert encoded[0] == DataType.WSTRING
        # Should contain VLQ length + UTF-8 data
        assert b"test" in encoded

    def test_blob(self) -> None:
        data = bytes([1, 2, 3, 4])
        encoded = encode_typed_value(DataType.BLOB, data)
        assert encoded[0] == DataType.BLOB
        assert encoded.endswith(data)

    def test_unsupported_type(self) -> None:
        with pytest.raises(ValueError, match="Unsupported DataType"):
            encode_typed_value(0xFF, None)
