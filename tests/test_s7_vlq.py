"""Tests for S7CommPlus VLQ (Variable-Length Quantity) encoding."""

import pytest

from s7.vlq import (
    encode_uint32_vlq,
    decode_uint32_vlq,
    encode_int32_vlq,
    decode_int32_vlq,
    encode_uint64_vlq,
    decode_uint64_vlq,
    encode_int64_vlq,
    decode_int64_vlq,
)


class TestUInt32Vlq:
    """Test unsigned 32-bit VLQ encoding/decoding."""

    @pytest.mark.parametrize(
        "value, expected_bytes",
        [
            (0, bytes([0x00])),
            (1, bytes([0x01])),
            (0x7F, bytes([0x7F])),
            (0x80, bytes([0x81, 0x00])),
            (0xFF, bytes([0x81, 0x7F])),
            (0x100, bytes([0x82, 0x00])),
            (0x3FFF, bytes([0xFF, 0x7F])),
            (0x4000, bytes([0x81, 0x80, 0x00])),
        ],
    )
    def test_encode_known_values(self, value: int, expected_bytes: bytes) -> None:
        assert encode_uint32_vlq(value) == expected_bytes

    @pytest.mark.parametrize(
        "value",
        [0, 1, 127, 128, 255, 256, 16383, 16384, 0xFFFF, 0xFFFFFF, 0xFFFFFFFF],
    )
    def test_roundtrip(self, value: int) -> None:
        encoded = encode_uint32_vlq(value)
        decoded, consumed = decode_uint32_vlq(encoded)
        assert decoded == value
        assert consumed == len(encoded)

    def test_decode_with_offset(self) -> None:
        prefix = bytes([0xAA, 0xBB])
        encoded = encode_uint32_vlq(12345)
        data = prefix + encoded
        decoded, consumed = decode_uint32_vlq(data, offset=2)
        assert decoded == 12345

    def test_encode_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            encode_uint32_vlq(-1)
        with pytest.raises(ValueError):
            encode_uint32_vlq(0x100000000)

    def test_decode_truncated(self) -> None:
        # Continuation bit set but no more data
        with pytest.raises(ValueError):
            decode_uint32_vlq(bytes([0x80]))


class TestInt32Vlq:
    """Test signed 32-bit VLQ encoding/decoding."""

    @pytest.mark.parametrize(
        "value",
        [0, 1, -1, 63, -64, 64, -65, 127, -128, 0x7FFFFFFF, -0x80000000, 1234567, -1234567],
    )
    def test_roundtrip(self, value: int) -> None:
        encoded = encode_int32_vlq(value)
        decoded, consumed = decode_int32_vlq(encoded)
        assert decoded == value
        assert consumed == len(encoded)

    def test_negative_one(self) -> None:
        """Test that -1 encodes compactly."""
        encoded = encode_int32_vlq(-1)
        decoded, _ = decode_int32_vlq(encoded)
        assert decoded == -1

    def test_min_value(self) -> None:
        """Test INT32_MIN boundary."""
        encoded = encode_int32_vlq(-0x80000000)
        decoded, _ = decode_int32_vlq(encoded)
        assert decoded == -0x80000000

    def test_encode_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            encode_int32_vlq(-0x80000001)
        with pytest.raises(ValueError):
            encode_int32_vlq(0x80000000)


class TestUInt64Vlq:
    """Test unsigned 64-bit VLQ encoding/decoding."""

    @pytest.mark.parametrize(
        "value",
        [
            0,
            1,
            127,
            128,
            0xFFFF,
            0xFFFFFFFF,
            0xFFFFFFFFFF,
            0x00FFFFFFFFFFFFFF,  # Just below the special threshold
            0x00FFFFFFFFFFFFFF + 1,  # At the special threshold
            0xFFFFFFFFFFFFFFFF,  # Max uint64
        ],
    )
    def test_roundtrip(self, value: int) -> None:
        encoded = encode_uint64_vlq(value)
        decoded, consumed = decode_uint64_vlq(encoded)
        assert decoded == value
        assert consumed == len(encoded)

    def test_max_encoding_length(self) -> None:
        """Max uint64 should encode in at most 9 bytes."""
        encoded = encode_uint64_vlq(0xFFFFFFFFFFFFFFFF)
        assert len(encoded) <= 9

    def test_encode_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            encode_uint64_vlq(-1)
        with pytest.raises(ValueError):
            encode_uint64_vlq(0x10000000000000000)


class TestInt64Vlq:
    """Test signed 64-bit VLQ encoding/decoding."""

    @pytest.mark.parametrize(
        "value",
        [
            0,
            1,
            -1,
            63,
            -64,
            127,
            -128,
            0x7FFFFFFFFFFFFFFF,  # Max int64
            -0x8000000000000000,  # Min int64
            123456789012345,
            -123456789012345,
        ],
    )
    def test_roundtrip(self, value: int) -> None:
        encoded = encode_int64_vlq(value)
        decoded, consumed = decode_int64_vlq(encoded)
        assert decoded == value
        assert consumed == len(encoded)

    def test_max_encoding_length(self) -> None:
        """Max/min int64 should encode in at most 9 bytes."""
        assert len(encode_int64_vlq(0x7FFFFFFFFFFFFFFF)) <= 9
        assert len(encode_int64_vlq(-0x8000000000000000)) <= 9
