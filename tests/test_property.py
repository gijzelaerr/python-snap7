"""Property-based tests using Hypothesis.

Verifies round-trip consistency for all getter/setter pairs: a value
written by set_X and read back by get_X should be the original value.
"""

import struct
from datetime import date, datetime, timedelta

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from snap7.util import (
    get_bool,
    set_bool,
    get_byte,
    set_byte,
    get_sint,
    set_sint,
    get_usint,
    set_usint,
    get_int,
    set_int,
    get_uint,
    set_uint,
    get_word,
    set_word,
    get_dint,
    set_dint,
    get_udint,
    set_udint,
    get_dword,
    set_dword,
    get_real,
    set_real,
    get_lreal,
    set_lreal,
    get_lword,
    set_lword,
    get_char,
    set_char,
    get_wchar,
    set_wchar,
    get_lint,
    set_lint,
    get_ulint,
    set_ulint,
    get_ltime,
    set_ltime,
    get_ltod,
    set_ltod,
    get_ldt,
    set_ldt,
    get_dtl,
    set_dtl,
    get_date,
    set_date,
    get_tod,
    set_tod,
)


@pytest.mark.hypothesis
class TestGetterSetterRoundtrip:
    """Every set_X / get_X pair must round-trip without loss."""

    @given(st.booleans())
    def test_bool(self, value: bool) -> None:
        data = bytearray(1)
        set_bool(data, 0, 0, value)
        assert get_bool(data, 0, 0) == value

    @given(st.integers(0, 255))
    def test_byte(self, value: int) -> None:
        data = bytearray(1)
        set_byte(data, 0, value)
        assert get_byte(data, 0) == value  # type: ignore[comparison-overlap]

    @given(st.integers(-128, 127))
    def test_sint(self, value: int) -> None:
        data = bytearray(1)
        set_sint(data, 0, value)
        assert get_sint(data, 0) == value

    @given(st.integers(0, 255))
    def test_usint(self, value: int) -> None:
        data = bytearray(1)
        set_usint(data, 0, value)
        assert get_usint(data, 0) == value

    @given(st.integers(-32768, 32767))
    def test_int(self, value: int) -> None:
        data = bytearray(2)
        set_int(data, 0, value)
        assert get_int(data, 0) == value

    @given(st.integers(0, 65535))
    def test_uint(self, value: int) -> None:
        data = bytearray(2)
        set_uint(data, 0, value)
        assert get_uint(data, 0) == value

    @given(st.integers(0, 65535))
    def test_word(self, value: int) -> None:
        data = bytearray(2)
        set_word(data, 0, value)
        assert get_word(data, 0) == value  # type: ignore[comparison-overlap]

    @given(st.integers(-2147483648, 2147483647))
    def test_dint(self, value: int) -> None:
        data = bytearray(4)
        set_dint(data, 0, value)
        assert get_dint(data, 0) == value

    @given(st.integers(0, 4294967295))
    def test_udint(self, value: int) -> None:
        data = bytearray(4)
        set_udint(data, 0, value)
        assert get_udint(data, 0) == value

    @given(st.integers(0, 4294967295))
    def test_dword(self, value: int) -> None:
        data = bytearray(4)
        set_dword(data, 0, value)
        assert get_dword(data, 0) == value

    @given(st.floats(min_value=-1e30, max_value=1e30, allow_nan=False, allow_infinity=False))
    def test_real(self, value: float) -> None:
        data = bytearray(4)
        set_real(data, 0, value)
        result = get_real(data, 0)
        # REAL is 32-bit float, so we lose precision
        expected = struct.unpack(">f", struct.pack(">f", value))[0]
        assert result == pytest.approx(expected, abs=1e-6)

    @given(st.floats(min_value=-1e100, max_value=1e100, allow_nan=False, allow_infinity=False))
    def test_lreal(self, value: float) -> None:
        data = bytearray(8)
        set_lreal(data, 0, value)
        assert get_lreal(data, 0) == pytest.approx(value)

    @given(st.integers(0, 2**64 - 1))
    def test_lword(self, value: int) -> None:
        data = bytearray(8)
        set_lword(data, 0, value)
        assert get_lword(data, 0) == value

    @given(st.integers(-(2**63), 2**63 - 1))
    def test_lint(self, value: int) -> None:
        data = bytearray(8)
        set_lint(data, 0, value)
        assert get_lint(data, 0) == value

    @given(st.integers(0, 2**64 - 1))
    def test_ulint(self, value: int) -> None:
        data = bytearray(8)
        set_ulint(data, 0, value)
        assert get_ulint(data, 0) == value

    @given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=1))
    def test_char(self, value: str) -> None:
        data = bytearray(1)
        set_char(data, 0, value)
        assert get_char(data, 0) == value

    @given(st.text(min_size=1, max_size=1))
    def test_wchar(self, value: str) -> None:
        assume(ord(value) < 65536)
        data = bytearray(2)
        set_wchar(data, 0, value)
        assert get_wchar(data, 0) == value

    @given(st.timedeltas(min_value=timedelta(0), max_value=timedelta(milliseconds=86399999)))
    def test_tod(self, value: timedelta) -> None:
        # Round to milliseconds (TOD precision)
        ms = int(value.total_seconds() * 1000)
        rounded = timedelta(milliseconds=ms)
        data = bytearray(4)
        set_tod(data, 0, rounded)
        assert get_tod(data, 0) == rounded

    # Note: set_time takes a string format, not timedelta — skip property test.

    @given(st.dates(min_value=date(1990, 1, 1), max_value=date(2168, 12, 31)))
    def test_date(self, value: date) -> None:
        data = bytearray(2)
        set_date(data, 0, value)
        assert get_date(data, 0) == value

    @given(st.timedeltas(min_value=timedelta(0), max_value=timedelta(hours=23, minutes=59, seconds=59)))
    @settings(max_examples=50)
    def test_ltime(self, value: timedelta) -> None:
        # Round to microseconds (LTIME stores nanoseconds but Python timedelta has microsecond precision)
        us = int(value.total_seconds() * 1_000_000)
        rounded = timedelta(microseconds=us)
        data = bytearray(8)
        set_ltime(data, 0, rounded)
        assert get_ltime(data, 0) == rounded

    @given(st.timedeltas(min_value=timedelta(0), max_value=timedelta(hours=23, minutes=59, seconds=59)))
    @settings(max_examples=50)
    def test_ltod(self, value: timedelta) -> None:
        us = int(value.total_seconds() * 1_000_000)
        rounded = timedelta(microseconds=us)
        data = bytearray(8)
        set_ltod(data, 0, rounded)
        assert get_ltod(data, 0) == rounded

    @given(st.datetimes(min_value=datetime(1970, 1, 1), max_value=datetime(2500, 1, 1)))
    @settings(max_examples=50)
    def test_ldt(self, value: datetime) -> None:
        # Round to microseconds
        us = int((value - datetime(1970, 1, 1)).total_seconds() * 1_000_000)
        rounded = datetime(1970, 1, 1) + timedelta(microseconds=us)
        data = bytearray(8)
        set_ldt(data, 0, rounded)
        result = get_ldt(data, 0)
        assert abs((result - rounded).total_seconds()) < 0.001

    @given(st.datetimes(min_value=datetime(2000, 1, 1), max_value=datetime(2554, 12, 31)))
    @settings(max_examples=50)
    def test_dtl(self, value: datetime) -> None:
        # DTL has second precision + nanoseconds
        rounded = value.replace(microsecond=0)
        data = bytearray(12)
        set_dtl(data, 0, rounded)
        result = get_dtl(data, 0)
        assert result.year == rounded.year
        assert result.month == rounded.month
        assert result.day == rounded.day
        assert result.hour == rounded.hour
        assert result.minute == rounded.minute
        assert result.second == rounded.second
