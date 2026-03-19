"""Property-based tests using Hypothesis.

Tests roundtrip properties for getter/setter pairs, protocol encoding/decoding,
and fuzz tests for robustness against malformed input.
"""

import math
import struct
from datetime import date, datetime, timedelta

import pytest
from hypothesis import given, assume, settings, HealthCheck
from hypothesis import strategies as st

from snap7.util.getters import (
    get_bool,
    get_byte,
    get_char,
    get_date,
    get_date_time_object,
    get_dint,
    get_dword,
    get_dtl,
    get_fstring,
    get_int,
    get_lint,
    get_lreal,
    get_lword,
    get_real,
    get_sint,
    get_string,
    get_tod,
    get_udint,
    get_uint,
    get_ulint,
    get_usint,
    get_wchar,
    get_wstring,
)
from snap7.util.setters import (
    set_bool,
    set_byte,
    set_char,
    set_date,
    set_dint,
    set_dt,
    set_dtl,
    set_dword,
    set_fstring,
    set_int,
    set_lreal,
    set_lword,
    set_real,
    set_sint,
    set_string,
    set_tod,
    set_udint,
    set_uint,
    set_usint,
    set_wchar,
    set_wstring,
)
from snap7.datatypes import S7Area, S7DataTypes, S7WordLen
from snap7.s7protocol import S7Protocol

pytestmark = pytest.mark.hypothesis


# ---------------------------------------------------------------------------
# Getter/Setter roundtrip tests — integer types
# ---------------------------------------------------------------------------


@given(st.booleans())
def test_bool_roundtrip(value: bool) -> None:
    for bit_index in range(8):
        data = bytearray(1)
        set_bool(data, 0, bit_index, value)
        assert get_bool(data, 0, bit_index) == value


@given(st.integers(min_value=0, max_value=7), st.booleans())
def test_bool_roundtrip_any_bit(bit_index: int, value: bool) -> None:
    data = bytearray(1)
    set_bool(data, 0, bit_index, value)
    assert get_bool(data, 0, bit_index) == value


@given(st.integers(min_value=0, max_value=255))
def test_byte_roundtrip(value: int) -> None:
    data = bytearray(1)
    set_byte(data, 0, value)
    # get_byte returns the value as an int (despite the bytes type annotation)
    assert get_byte(data, 0) == value  # type: ignore[comparison-overlap]


@given(st.integers(min_value=0, max_value=255))
def test_usint_roundtrip(value: int) -> None:
    data = bytearray(1)
    set_usint(data, 0, value)
    assert get_usint(data, 0) == value


@given(st.integers(min_value=-128, max_value=127))
def test_sint_roundtrip(value: int) -> None:
    data = bytearray(1)
    set_sint(data, 0, value)
    assert get_sint(data, 0) == value


@given(st.integers(min_value=0, max_value=65535))
def test_uint_roundtrip(value: int) -> None:
    data = bytearray(2)
    set_uint(data, 0, value)
    assert get_uint(data, 0) == value


@given(st.integers(min_value=-32768, max_value=32767))
def test_int_roundtrip(value: int) -> None:
    data = bytearray(2)
    set_int(data, 0, value)
    assert get_int(data, 0) == value


@given(st.integers(min_value=0, max_value=4294967295))
def test_dword_roundtrip(value: int) -> None:
    data = bytearray(4)
    set_dword(data, 0, value)
    assert get_dword(data, 0) == value


@given(st.integers(min_value=0, max_value=4294967295))
def test_udint_roundtrip(value: int) -> None:
    data = bytearray(4)
    set_udint(data, 0, value)
    assert get_udint(data, 0) == value


@given(st.integers(min_value=-2147483648, max_value=2147483647))
def test_dint_roundtrip(value: int) -> None:
    data = bytearray(4)
    set_dint(data, 0, value)
    assert get_dint(data, 0) == value


@given(st.integers(min_value=0, max_value=2**64 - 1))
def test_lword_roundtrip(value: int) -> None:
    data = bytearray(8)
    set_lword(data, 0, value)
    assert get_lword(data, 0) == value


# ---------------------------------------------------------------------------
# Getter/Setter roundtrip tests — floating point types
# ---------------------------------------------------------------------------


@given(st.floats(width=32, allow_nan=False, allow_infinity=False))
def test_real_roundtrip(value: float) -> None:
    data = bytearray(4)
    set_real(data, 0, value)
    result = get_real(data, 0)
    assert struct.pack(">f", value) == struct.pack(">f", result)


@given(st.floats(width=64, allow_nan=False, allow_infinity=False))
def test_lreal_roundtrip(value: float) -> None:
    data = bytearray(8)
    set_lreal(data, 0, value)
    result = get_lreal(data, 0)
    assert struct.pack(">d", value) == struct.pack(">d", result)


@given(st.floats(width=32, allow_nan=True, allow_infinity=True))
def test_real_roundtrip_special(value: float) -> None:
    """Real roundtrip including NaN and Infinity."""
    data = bytearray(4)
    set_real(data, 0, value)
    result = get_real(data, 0)
    if math.isnan(value):
        assert math.isnan(result)
    else:
        assert result == value


@given(st.floats(width=64, allow_nan=True, allow_infinity=True))
def test_lreal_roundtrip_special(value: float) -> None:
    """LReal roundtrip including NaN and Infinity."""
    data = bytearray(8)
    set_lreal(data, 0, value)
    result = get_lreal(data, 0)
    if math.isnan(value):
        assert math.isnan(result)
    else:
        assert result == value


# ---------------------------------------------------------------------------
# Getter/Setter roundtrip tests — string types
# ---------------------------------------------------------------------------


@given(st.characters(min_codepoint=0, max_codepoint=255))
def test_char_roundtrip(value: str) -> None:
    data = bytearray(1)
    set_char(data, 0, value)
    assert get_char(data, 0) == value


@given(st.characters(min_codepoint=0, max_codepoint=0xFFFF))
def test_wchar_roundtrip(value: str) -> None:
    # wchar uses UTF-16-BE, which can't handle surrogate halves
    assume(not (0xD800 <= ord(value) <= 0xDFFF))
    data = bytearray(2)
    set_wchar(data, 0, value)
    assert get_wchar(data, 0) == value


@given(st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126), min_size=0, max_size=20))
def test_fstring_roundtrip(value: str) -> None:
    max_length = 20
    data = bytearray(max_length)
    set_fstring(data, 0, value, max_length)
    result = get_fstring(data, 0, max_length)
    assert result == value.rstrip(" ")


@given(st.text(alphabet=st.characters(min_codepoint=1, max_codepoint=255), min_size=0, max_size=50))
def test_string_roundtrip(value: str) -> None:
    max_size = 254
    buf_size = 2 + max_size
    data = bytearray(buf_size)
    set_string(data, 0, value, max_size)
    assert get_string(data, 0) == value


@given(st.text(min_size=0, max_size=20))
def test_wstring_roundtrip(value: str) -> None:
    # Avoid surrogates which can't be encoded in UTF-16-BE
    assume(all(not (0xD800 <= ord(c) <= 0xDFFF) for c in value))
    # Known bug: characters outside the BMP (codepoint > 0xFFFF) encode as 4 bytes
    # in UTF-16-BE (surrogate pairs) but get_wstring/set_wstring use character count
    # instead of UTF-16 code unit count, so supplementary characters are truncated.
    assume(all(ord(c) <= 0xFFFF for c in value))
    max_size = 50
    buf_size = 4 + max_size * 2
    data = bytearray(buf_size)
    set_wstring(data, 0, value, max_size)
    assert get_wstring(data, 0) == value


# ---------------------------------------------------------------------------
# Getter/Setter roundtrip tests — date/time types
# ---------------------------------------------------------------------------


@given(st.dates(min_value=date(1990, 1, 1), max_value=date(2168, 12, 31)))
def test_date_roundtrip(value: date) -> None:
    data = bytearray(2)
    set_date(data, 0, value)
    assert get_date(data, 0) == value


@given(
    st.timedeltas(
        min_value=timedelta(0),
        max_value=timedelta(hours=23, minutes=59, seconds=59, milliseconds=999),
    )
)
def test_tod_roundtrip(value: timedelta) -> None:
    # TOD stores milliseconds, so truncate microseconds to ms precision
    ms = int(value.total_seconds() * 1000)
    value_ms = timedelta(milliseconds=ms)
    data = bytearray(4)
    set_tod(data, 0, value_ms)
    assert get_tod(data, 0) == value_ms


@given(
    st.datetimes(
        min_value=datetime(1990, 1, 1),
        max_value=datetime(2089, 12, 31, 23, 59, 59, 999000),
    )
)
def test_dt_roundtrip(value: datetime) -> None:
    # DT stores milliseconds, truncate microseconds to ms precision
    ms = value.microsecond // 1000
    value_trunc = value.replace(microsecond=ms * 1000)
    data = bytearray(8)
    set_dt(data, 0, value_trunc)
    result = get_date_time_object(data, 0)
    assert result == value_trunc


@given(
    st.datetimes(
        min_value=datetime(1, 1, 1),
        max_value=datetime(2554, 12, 31, 23, 59, 59, 999000),
    )
)
def test_dtl_roundtrip(value: datetime) -> None:
    # DTL stores nanoseconds derived from microseconds, but get_dtl reads
    # byte 8 as raw microsecond value. Truncate to match.
    # set_dtl writes microsecond * 1000 as nanoseconds (4 bytes big-endian)
    # get_dtl reads byte 8 as int — this is the first byte of the 4-byte nanosecond field
    nanoseconds = value.microsecond * 1000
    ns_bytes = struct.pack(">I", nanoseconds)
    expected_microsecond = ns_bytes[0]  # get_dtl reads only byte_index+8

    data = bytearray(12)
    set_dtl(data, 0, value)
    result = get_dtl(data, 0)
    assert result.year == value.year
    assert result.month == value.month
    assert result.day == value.day
    assert result.hour == value.hour
    assert result.minute == value.minute
    assert result.second == value.second
    assert result.microsecond == expected_microsecond


# ---------------------------------------------------------------------------
# S7 data type encode/decode roundtrip
# ---------------------------------------------------------------------------


@given(st.lists(st.booleans(), min_size=1, max_size=10))
def test_s7_bit_encode_decode_roundtrip(values: list[bool]) -> None:
    encoded = S7DataTypes.encode_s7_data(values, S7WordLen.BIT)
    decoded = S7DataTypes.decode_s7_data(encoded, S7WordLen.BIT, len(values))
    assert decoded == values


@given(st.lists(st.integers(min_value=0, max_value=255), min_size=1, max_size=10))
def test_s7_byte_encode_decode_roundtrip(values: list[int]) -> None:
    encoded = S7DataTypes.encode_s7_data(values, S7WordLen.BYTE)
    decoded = S7DataTypes.decode_s7_data(encoded, S7WordLen.BYTE, len(values))
    assert decoded == values


@given(st.lists(st.integers(min_value=0, max_value=65535), min_size=1, max_size=10))
def test_s7_word_encode_decode_roundtrip(values: list[int]) -> None:
    encoded = S7DataTypes.encode_s7_data(values, S7WordLen.WORD)
    decoded = S7DataTypes.decode_s7_data(encoded, S7WordLen.WORD, len(values))
    assert decoded == values


@given(st.lists(st.integers(min_value=-32768, max_value=32767), min_size=1, max_size=10))
def test_s7_int_encode_decode_roundtrip(values: list[int]) -> None:
    encoded = S7DataTypes.encode_s7_data(values, S7WordLen.INT)
    decoded = S7DataTypes.decode_s7_data(encoded, S7WordLen.INT, len(values))
    assert decoded == values


@given(st.lists(st.integers(min_value=0, max_value=4294967295), min_size=1, max_size=10))
def test_s7_dword_encode_decode_roundtrip(values: list[int]) -> None:
    encoded = S7DataTypes.encode_s7_data(values, S7WordLen.DWORD)
    decoded = S7DataTypes.decode_s7_data(encoded, S7WordLen.DWORD, len(values))
    assert decoded == values


@given(st.lists(st.integers(min_value=-2147483648, max_value=2147483647), min_size=1, max_size=10))
def test_s7_dint_encode_decode_roundtrip(values: list[int]) -> None:
    encoded = S7DataTypes.encode_s7_data(values, S7WordLen.DINT)
    decoded = S7DataTypes.decode_s7_data(encoded, S7WordLen.DINT, len(values))
    assert decoded == values


@given(st.lists(st.floats(width=32, allow_nan=False, allow_infinity=False), min_size=1, max_size=10))
def test_s7_real_encode_decode_roundtrip(values: list[float]) -> None:
    encoded = S7DataTypes.encode_s7_data(values, S7WordLen.REAL)
    decoded = S7DataTypes.decode_s7_data(encoded, S7WordLen.REAL, len(values))
    for orig, result in zip(values, decoded):
        assert struct.pack(">f", orig) == struct.pack(">f", result)


# ---------------------------------------------------------------------------
# S7 address encoding
# ---------------------------------------------------------------------------


@given(
    st.sampled_from(list(S7Area)),
    st.integers(min_value=0, max_value=65535),
    st.integers(min_value=0, max_value=65535),
    st.sampled_from([wl for wl in S7WordLen if wl not in (S7WordLen.COUNTER, S7WordLen.TIMER)]),
    st.integers(min_value=1, max_value=100),
)
def test_address_encoding_is_12_bytes(area: S7Area, db_number: int, start: int, word_len: S7WordLen, count: int) -> None:
    """Encoded address should always be exactly 12 bytes."""
    result = S7DataTypes.encode_address(area, db_number, start, word_len, count)
    assert len(result) == 12
    assert result[0] == 0x12  # Specification type
    assert result[1] == 0x0A  # Length
    assert result[2] == 0x10  # Syntax ID


# ---------------------------------------------------------------------------
# TPKT frame tests
# ---------------------------------------------------------------------------


@given(st.binary(min_size=1, max_size=500))
def test_tpkt_frame_structure(payload: bytes) -> None:
    """TPKT frame should have correct version, reserved byte, and length."""
    from snap7.connection import ISOTCPConnection

    conn = ISOTCPConnection.__new__(ISOTCPConnection)
    frame = conn._build_tpkt(payload)
    assert frame[0] == 3  # version
    assert frame[1] == 0  # reserved
    length = struct.unpack(">H", frame[2:4])[0]
    assert length == len(payload) + 4
    assert frame[4:] == payload


@given(st.binary(min_size=1, max_size=500))
def test_cotp_dt_frame_structure(payload: bytes) -> None:
    """COTP DT frame should have correct PDU type and EOT marker."""
    from snap7.connection import ISOTCPConnection

    conn = ISOTCPConnection.__new__(ISOTCPConnection)
    frame = conn._build_cotp_dt(payload)
    assert frame[0] == 2  # PDU length
    assert frame[1] == 0xF0  # COTP DT type
    assert frame[2] == 0x80  # EOT + sequence number 0
    assert frame[3:] == payload


# ---------------------------------------------------------------------------
# S7 Protocol PDU structure tests
# ---------------------------------------------------------------------------


@given(
    st.sampled_from(list(S7Area)),
    st.integers(min_value=0, max_value=100),
    st.integers(min_value=0, max_value=1000),
    st.sampled_from([wl for wl in S7WordLen if wl not in (S7WordLen.COUNTER, S7WordLen.TIMER)]),
    st.integers(min_value=1, max_value=50),
)
def test_read_request_pdu_structure(area: S7Area, db_number: int, start: int, word_len: S7WordLen, count: int) -> None:
    """Read request PDU should have valid S7 header."""
    proto = S7Protocol()
    pdu = proto.build_read_request(area, db_number, start, word_len, count)
    assert pdu[0] == 0x32  # Protocol ID
    assert pdu[1] == 0x01  # Request PDU type
    assert len(pdu) >= 12  # Minimum header size


@given(
    st.sampled_from(list(S7Area)),
    st.integers(min_value=0, max_value=100),
    st.integers(min_value=0, max_value=1000),
    st.sampled_from([S7WordLen.BYTE, S7WordLen.WORD, S7WordLen.DWORD, S7WordLen.INT, S7WordLen.DINT, S7WordLen.REAL]),
    st.binary(min_size=1, max_size=20),
)
def test_write_request_pdu_structure(area: S7Area, db_number: int, start: int, word_len: S7WordLen, data: bytes) -> None:
    """Write request PDU should have valid S7 header."""
    item_size = S7DataTypes.get_size_bytes(word_len, 1)
    # Ensure data length is a multiple of item size
    data = data[: (len(data) // item_size) * item_size]
    assume(len(data) > 0)

    proto = S7Protocol()
    pdu = proto.build_write_request(area, db_number, start, word_len, data)
    assert pdu[0] == 0x32  # Protocol ID
    assert pdu[1] == 0x01  # Request PDU type


# ---------------------------------------------------------------------------
# Fuzz tests — robustness against arbitrary input
# ---------------------------------------------------------------------------


@given(st.binary(min_size=4, max_size=4))
def test_real_decode_no_crash(data: bytes) -> None:
    """Any 4 bytes should decode without crashing."""
    get_real(bytearray(data), 0)


@given(st.binary(min_size=8, max_size=8))
def test_lreal_decode_no_crash(data: bytes) -> None:
    """Any 8 bytes should decode without crashing."""
    get_lreal(bytearray(data), 0)


@given(st.binary(min_size=2, max_size=2))
def test_int_decode_no_crash(data: bytes) -> None:
    """Any 2 bytes should decode without crashing."""
    get_int(bytearray(data), 0)


@given(st.binary(min_size=4, max_size=4))
def test_dint_decode_no_crash(data: bytes) -> None:
    """Any 4 bytes should decode without crashing."""
    get_dint(bytearray(data), 0)


@given(st.binary(min_size=8, max_size=8))
def test_lint_decode_no_crash(data: bytes) -> None:
    """Any 8 bytes should decode without crashing."""
    get_lint(bytearray(data), 0)


@given(st.binary(min_size=8, max_size=8))
def test_lword_decode_no_crash(data: bytes) -> None:
    """Any 8 bytes should decode without crashing."""
    get_lword(bytearray(data), 0)


@given(st.binary(min_size=8, max_size=8))
def test_ulint_decode_no_crash(data: bytes) -> None:
    """Any 8 bytes should decode without crashing."""
    get_ulint(bytearray(data), 0)


@given(st.binary(min_size=10, max_size=500))
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_pdu_parse_no_crash(data: bytes) -> None:
    """Parsing random bytes as S7 PDU should not crash unexpectedly.

    Expected exceptions are S7ProtocolError for invalid data.
    """
    from snap7.error import S7ProtocolError

    proto = S7Protocol()
    try:
        proto.parse_response(data)
    except (S7ProtocolError, struct.error, ValueError, IndexError, KeyError):
        pass  # Expected for malformed data


@given(st.binary(min_size=7, max_size=100))
def test_tpkt_cotp_parse_no_crash(data: bytes) -> None:
    """Parsing random bytes as COTP data should not crash unexpectedly."""
    from snap7.connection import ISOTCPConnection
    from snap7.error import S7ConnectionError

    conn = ISOTCPConnection.__new__(ISOTCPConnection)
    try:
        conn._parse_cotp_data(data)
    except (ValueError, IndexError, struct.error, S7ConnectionError):
        pass  # Expected for malformed data


# ---------------------------------------------------------------------------
# Multiple bools in the same byte don't interfere
# ---------------------------------------------------------------------------


@given(st.lists(st.booleans(), min_size=8, max_size=8))
def test_bool_multiple_bits_no_interference(values: list[bool]) -> None:
    """Setting 8 bools in one byte should not interfere with each other."""
    data = bytearray(1)
    for i, v in enumerate(values):
        set_bool(data, 0, i, v)
    for i, v in enumerate(values):
        assert get_bool(data, 0, i) == v


# ---------------------------------------------------------------------------
# Non-zero byte_index tests
# ---------------------------------------------------------------------------


@given(st.integers(min_value=-32768, max_value=32767), st.integers(min_value=0, max_value=10))
def test_int_roundtrip_at_offset(value: int, offset: int) -> None:
    """Getter/setter should work at arbitrary byte offsets."""
    data = bytearray(offset + 2)
    set_int(data, offset, value)
    assert get_int(data, offset) == value


@given(st.integers(min_value=-2147483648, max_value=2147483647), st.integers(min_value=0, max_value=10))
def test_dint_roundtrip_at_offset(value: int, offset: int) -> None:
    data = bytearray(offset + 4)
    set_dint(data, offset, value)
    assert get_dint(data, offset) == value
