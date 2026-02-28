import re
import struct
from datetime import date, datetime, timedelta
from typing import Union

from .getters import get_bool


def set_bool(bytearray_: bytearray, byte_index: int, bool_index: int, value: bool) -> bytearray:
    """Set boolean value on location in bytearray.

    Args:
        bytearray_: buffer to write to.
        byte_index: byte index to write to.
        bool_index: bit index to write to.
        value: value to write.

    Examples:
        >>> buffer = bytearray([0b00000000])
        >>> set_bool(buffer, 0, 0, True)
        >>> buffer
            bytearray(b"\\x01")
    """
    if value not in {0, 1, True, False}:
        raise TypeError(f"Value value:{value} is not a boolean expression.")

    current_value = get_bool(bytearray_, byte_index, bool_index)
    index_value = 1 << bool_index

    # check if bool already has correct value
    if current_value == value:
        return bytearray_

    if value:
        # make sure index_v is IN current byte
        bytearray_[byte_index] += index_value
    else:
        # make sure index_v is NOT in current byte
        bytearray_[byte_index] -= index_value
    return bytearray_


def set_byte(bytearray_: bytearray, byte_index: int, _int: int) -> bytearray:
    """Set value in bytearray to byte

    Args:
        bytearray_: buffer to write to.
        byte_index: byte index to write.
        _int: value to write.

    Returns:
        buffer with the written value.

    Examples:
        >>> buffer = bytearray([0b00000000])
        >>> set_byte(buffer, 0, 255)
            bytearray(b"\\xFF")
    """
    _int = int(_int)
    bytearray_[byte_index : byte_index + 1] = struct.pack("B", _int)
    return bytearray_


def set_word(bytearray_: bytearray, byte_index: int, _int: int) -> bytearray:
    """Set value in bytearray to word

    Notes:
        Word datatype is 2 bytes long.

    Args:
        bytearray_: buffer to be written.
        byte_index: byte index to start write from.
        _int: value to write.

    Return:
        buffer with the written value
    """
    _int = int(_int)
    bytearray_[byte_index : byte_index + 2] = struct.pack(">H", _int)
    return bytearray_


def set_int(bytearray_: bytearray, byte_index: int, _int: int) -> bytearray:
    """Set value in bytearray to int

    Notes:
        An datatype `int` in the PLC consists of two `bytes`.

    Args:
        bytearray_: buffer to write on.
        byte_index: byte index to start writing from.
        _int: int value to write.

    Returns:
        Buffer with the written value.

    Examples:
        >>> data = bytearray(2)
        >>> set_int(data, 0, 255)
            bytearray(b'\\x00\\xff')
    """
    # make sure were dealing with an int
    _int = int(_int)
    bytearray_[byte_index : byte_index + 2] = struct.pack(">h", _int)
    return bytearray_


def set_uint(bytearray_: bytearray, byte_index: int, _int: int) -> bytearray:
    """Set value in bytearray to unsigned int

    Notes:
        An datatype `uint` in the PLC consists of two `bytes`.

    Args:
        bytearray_: buffer to write on.
        byte_index: byte index to start writing from.
        _int: int value to write.

    Returns:
        Buffer with the written value.

    Examples:
        >>> from snap7.util import set_uint
        >>> data = bytearray(2)
        >>> set_uint(data, 0, 65535)
            bytearray(b'\\xff\\xff')
    """
    # make sure were dealing with an int
    _int = int(_int)
    bytearray_[byte_index : byte_index + 2] = struct.pack(">H", _int)
    return bytearray_


def set_real(bytearray_: bytearray, byte_index: int, real: Union[bool, str, float, int]) -> bytearray:
    """Set Real value

    Notes:
        Datatype `real` is represented in 4 bytes in the PLC.
        The packed representation uses the `IEEE 754 binary32`.

    Args:
        bytearray_: buffer to write to.
        byte_index: byte index to start writing from.
        real: value to be written.

    Returns:
        Buffer with the value written.

    Examples:
        >>> data = bytearray(4)
        >>> set_real(data, 0, 123.321)
            bytearray(b'B\\xf6\\xa4Z')
    """
    bytearray_[byte_index : byte_index + 4] = struct.pack(">f", float(real))
    return bytearray_


def set_fstring(bytearray_: bytearray, byte_index: int, value: str, max_length: int) -> None:
    """Set space-padded fixed-length string value

    Args:
        bytearray_: buffer to write to.
        byte_index: byte index to start writing from.
        value: string to write.
        max_length: maximum string length, i.e. the fixed size of the string.

    Raises:
        :obj:`TypeError`: if the `value` is not a :obj:`str`.
        :obj:`ValueError`: if the length of the `value` is larger than the `max_size`
        or 'value' contains non-ascii characters.

    Examples:
        >>> data = bytearray(20)
        >>> set_fstring(data, 0, "hello world", 15)
        >>> data
            bytearray(b'hello world    \x00\x00\x00\x00\x00')
    """
    if not value.isascii():
        raise ValueError("Value contains non-ascii values.")
    # FAIL HARD WHEN trying to write too much data into PLC
    size = len(value)
    if size > max_length:
        raise ValueError(f"size {size} > max_length {max_length} {value}")

    i = 0

    # fill array which chr integers
    for i, c in enumerate(value):
        bytearray_[byte_index + i] = ord(c)

    # fill the rest with empty space
    for r in range(i + 1, max_length):
        bytearray_[byte_index + r] = ord(" ")


def set_string(bytearray_: bytearray, byte_index: int, value: str, max_size: int = 254) -> None:
    """Set string value

    Args:
        bytearray_: buffer to write to.
        byte_index: byte index to start writing from.
        value: string to write.
        max_size: maximum possible string size, max. 254 as default.

    Raises:
        :obj:`TypeError`: if the `value` is not a :obj:`str`.
        :obj:`ValueError`: if the length of the `value` is larger than the `max_size`
        or 'max_size' is greater than 254 or 'value' contains ascii characters > 255.

    Examples:
        >>> from snap7.util import set_string
        >>> data = bytearray(20)
        >>> set_string(data, 0, "hello world", 254)
        >>> data
            bytearray(b'\\xff\\x0bhello world\\x00\\x00\\x00\\x00\\x00\\x00\\x00')
    """
    if not isinstance(value, str):
        raise TypeError(f"Value value:{value} is not from Type string")

    if max_size > 254:
        raise ValueError(f"max_size: {max_size} > max. allowed 254 chars")

    if any(ord(char) < 0 or ord(char) > 255 for char in value):
        raise ValueError(
            "Value contains ascii values > 255, which is not compatible with PLC Type STRING. "
            "Check encoding of value or try set_wstring()."
        )

    size = len(value)
    # FAIL HARD WHEN trying to write too much data into PLC
    if size > max_size:
        raise ValueError(f"size {size} > max_size {max_size} {value}")

    # set max string size
    bytearray_[byte_index] = max_size

    # set len count on first position
    bytearray_[byte_index + 1] = len(value)

    i = 0

    # fill array which chr integers
    for i, c in enumerate(value):
        bytearray_[byte_index + 2 + i] = ord(c)

    # fill the rest with empty space
    for r in range(i + 1, bytearray_[byte_index] - 2):
        bytearray_[byte_index + 2 + r] = ord(" ")


def set_dword(bytearray_: bytearray, byte_index: int, dword: int) -> None:
    """Set a DWORD to the buffer.

    Notes:
        Datatype `dword` consists in 8 bytes in the PLC.
        The maximum value posible is `4294967295`

    Args:
        bytearray_: buffer to write to.
        byte_index: byte index from where to write.
        dword: value to write.

    Examples:
        >>> data = bytearray(4)
        >>> set_dword(data,0, 4294967295)
        >>> data
            bytearray(b'\\xff\\xff\\xff\\xff')
    """
    dword = int(dword)
    bytearray_[byte_index : byte_index + 4] = struct.pack(">I", dword)


def set_dint(bytearray_: bytearray, byte_index: int, dint: int) -> None:
    """Set value in bytearray to dint

    Notes:
        Datatype `dint` consists in 4 bytes in the PLC.
        Maximum possible value is 2147483647.
        Lower posible value is -2147483648.

    Args:
        bytearray_: buffer to write.
        byte_index: byte index from where to start writing.
        dint: double integer value

    Examples:
        >>> data = bytearray(4)
        >>> set_dint(data, 0, 2147483647)
        >>> data
            bytearray(b'\\x7f\\xff\\xff\\xff')
    """
    dint = int(dint)
    bytearray_[byte_index : byte_index + 4] = struct.pack(">i", dint)


def set_udint(bytearray_: bytearray, byte_index: int, udint: int) -> None:
    """Set value in bytearray to unsigned dint

    Notes:
        Datatype `dint` consists in 4 bytes in the PLC.
        Maximum possible value is 4294967295.
        Minimum posible value is 0.

    Args:
        bytearray_: buffer to write.
        byte_index: byte index from where to start writing.
        udint: unsigned double integer value

    Examples:
        >>> data = bytearray(4)
        >>> set_udint(data, 0, 4294967295)
        >>> data
            bytearray(b'\\xff\\xff\\xff\\xff')
    """
    udint = int(udint)
    bytearray_[byte_index : byte_index + 4] = struct.pack(">I", udint)


def set_time(bytearray_: bytearray, byte_index: int, time_string: str) -> bytearray:
    """Set value in bytearray to time

    Notes:
        Datatype `time` consists in 4 bytes in the PLC.
        Maximum possible value is T#24D_20H_31M_23S_647MS(2147483647).
        Lower posible value is T#-24D_20H_31M_23S_648MS(-2147483648).

    Args:
        bytearray_: buffer to write.
        byte_index: byte index from where to start writing.
        time_string: time value in string

    Examples:
        >>> data = bytearray(4)

        >>> set_time(data, 0, '-22:3:57:28.192')

        >>> data
            bytearray(b'\x8d\xda\xaf\x00')
    """
    sign = 1
    if re.fullmatch(
        r"(-?(2[0-3]|1?\d):(2[0-3]|1?\d|\d):([1-5]?\d):[1-5]?\d.\d{1,3})|"
        r"(-24:(20|1?\d):(3[0-1]|[0-2]?\d):(2[0-3]|1?\d).(64[0-8]|6[0-3]\d|[0-5]\d{1,2}))|"
        r"(24:(20|1?\d):(3[0-1]|[0-2]?\d):(2[0-3]|1?\d).(64[0-7]|6[0-3]\d|[0-5]\d{1,2}))",
        time_string,
    ):
        data_list = re.split("[: .]", time_string)
        days: str = data_list[0]
        hours: int = int(data_list[1])
        minutes: int = int(data_list[2])
        seconds: int = int(data_list[3])
        milli_seconds: int = int(data_list[4].ljust(3, "0"))
        if re.match(r"^-\d{1,2}$", days):
            sign = -1

        time_int = (
            (int(days) * sign * 3600 * 24 + (hours % 24) * 3600 + (minutes % 60) * 60 + seconds % 60) * 1000 + milli_seconds
        ) * sign
        bytes_array = time_int.to_bytes(4, byteorder="big", signed=True)
        bytearray_[byte_index : byte_index + 4] = bytes_array
        return bytearray_
    else:
        raise ValueError("time value out of range, please check the value interval")


def set_usint(bytearray_: bytearray, byte_index: int, _int: int) -> bytearray:
    """Set unsigned small int

    Notes:
        Datatype `usint` (Unsigned small int) consists on 1 byte in the PLC.
        Maximum posible value is 255.
        Lower posible value is 0.

    Args:
         bytearray_: buffer to write.
        byte_index: byte index from where to start writing.
        _int: value to write.

    Returns:
        Buffer with the written value.

    Examples:
        >>> data = bytearray(1)
        >>> set_usint(data, 0, 255)
            bytearray(b'\\xff')
    """
    _int = int(_int)
    bytearray_[byte_index] = struct.pack(">B", _int)[0]
    return bytearray_


def set_sint(bytearray_: bytearray, byte_index: int, _int: int) -> bytearray:
    """Set small int to the buffer.

    Notes:
        Datatype `sint` (Small int) consists in 1 byte in the PLC.
        Maximum value posible is 127.
        Lowest value posible is -128.

    Args:
         bytearray_: buffer to write to.
        byte_index: byte index from where to start writing.
        _int: value to write.

    Returns:
        Buffer with the written value.

    Examples:
        >>> data = bytearray(1)
        >>> set_sint(data, 0, 127)
            bytearray(b'\\x7f')
    """
    _int = int(_int)
    bytearray_[byte_index] = struct.pack(">b", _int)[0]
    return bytearray_


def set_lreal(bytearray_: bytearray, byte_index: int, lreal: float) -> bytearray:
    """Set the long real

    Notes:
        Datatype `lreal` (long real) consists in 8 bytes in the PLC.
        Negative Range: -1.7976931348623158e+308 to -2.2250738585072014e-308
        Positive Range: +2.2250738585072014e-308 to +1.7976931348623158e+308
        Zero: ±0

    Args:
        bytearray_: buffer to read from.
        byte_index: byte index from where to start reading.
        lreal: float value to set

    Returns:
        Value to write.

    Examples:
        write lreal value (here as example 12345.12345) to DB1.10 of a PLC
        >>> data = set_lreal(data, 12345.12345)
        >>> from snap7 import Client
        >>> Client().db_write(db_number=1, start=10, data=data)

    """
    lreal = float(lreal)
    struct.pack_into(">d", bytearray_, byte_index, lreal)
    return bytearray_


def set_lword(bytearray_: bytearray, byte_index: int, lword: int) -> bytearray:
    """Set the long word

    Notes:
        Datatype `lword` (long word) consists in 8 bytes in the PLC.
        Maximum value is 18446744073709551615 (0xFFFFFFFFFFFFFFFF).
        Minimum value is 0.

    Args:
        bytearray_: buffer to write to.
        byte_index: byte index from where to start writing.
        lword: unsigned 64-bit value to write.

    Returns:
        Buffer with the written value.

    Examples:
        >>> data = bytearray(8)
        >>> set_lword(data, 0, 0xABCD)
        >>> data
        bytearray(b'\\x00\\x00\\x00\\x00\\x00\\x00\\xab\\xcd')
    """
    lword = int(lword)
    bytearray_[byte_index : byte_index + 8] = struct.pack(">Q", lword)
    return bytearray_


def set_char(bytearray_: bytearray, byte_index: int, chr_: str) -> bytearray:
    """Set char value in a bytearray.

    Notes:
        Datatype `char` in the PLC is represented in 1 byte. It has to be in ASCII-format

    Args:
        bytearray_: buffer to write to.
        byte_index: byte index from where to start writing.
        chr_: `char` to write.

    Returns:
        Buffer with the written value.

    Examples:
        write `char` (here as example 'C') to DB1.10 of a PLC
        >>> data = bytearray(1)
        >>> set_char(data, 0, 'C')
        >>> data
        bytearray('0x43')
    """
    if not isinstance(chr_, str):
        raise TypeError(f"Value value:{chr_} is not from Type string")

    if len(chr_) > 1:
        raise ValueError(f"size chr_ : {chr_} > 1")
    elif len(chr_) < 1:
        raise ValueError(f"size chr_ : {chr_} < 1")

    if 0 <= ord(chr_) <= 255:
        bytearray_[byte_index] = ord(chr_)
        return bytearray_
    else:
        raise ValueError(f"chr_ : {chr_} contains ascii value > 255, which is not compatible with PLC Type CHAR.")


def set_date(bytearray_: bytearray, byte_index: int, date_: date) -> bytearray:
    """Set value in bytearray to date
    Notes:
        Datatype `date` consists in the number of days elapsed from 1990-01-01.
        It is stored as an int (2 bytes) in the PLC.
    Args:
        bytearray_: buffer to write.
        byte_index: byte index from where to start writing.
        date_: date object
    Examples:
        >>> data = bytearray(2)
        >>> set_date(data, 0, date(2024, 3, 27))
        >>> data
            bytearray(b'\x30\xd8')
    """
    if date_ < date(1990, 1, 1):
        raise ValueError("date is lower than specification allows.")
    elif date_ > date(2168, 12, 31):
        raise ValueError("date is higher than specification allows.")
    _days = (date_ - date(1990, 1, 1)).days
    bytearray_[byte_index : byte_index + 2] = struct.pack(">h", _days)
    return bytearray_


def set_wchar(bytearray_: bytearray, byte_index: int, chr_: str) -> bytearray:
    """Set wchar value in a bytearray.

    Notes:
        Datatype `wchar` in the PLC is represented in 2 bytes as UTF-16-BE.

    Args:
        bytearray_: buffer to write to.
        byte_index: byte index from where to start writing.
        chr_: single character to write.

    Returns:
        Buffer with the written value.

    Examples:
        >>> data = bytearray(2)
        >>> set_wchar(data, 0, 'C')
        >>> data
        bytearray(b'\\x00C')
    """
    if not isinstance(chr_, str):
        raise TypeError(f"Value value:{chr_} is not from Type string")
    if len(chr_) != 1:
        raise ValueError(f"Expected single character, got length {len(chr_)}")
    encoded = chr_.encode("utf-16-be")
    bytearray_[byte_index : byte_index + 2] = encoded
    return bytearray_


def set_wstring(bytearray_: bytearray, byte_index: int, value: str, max_size: int = 16382) -> None:
    """Set wstring value

    Notes:
        Byte 0-1: max size (number of characters, 2-byte big-endian).
        Byte 2-3: current length (number of characters, 2-byte big-endian).
        Byte 4+: UTF-16-BE encoded characters (2 bytes each).

    Args:
        bytearray_: buffer to write to.
        byte_index: byte index to start writing from.
        value: string to write.
        max_size: maximum number of characters allowed (default 16382).

    Raises:
        TypeError: if the value is not a string.
        ValueError: if the string is too long or max_size exceeds 16382.

    Examples:
        >>> data = bytearray(26)
        >>> set_wstring(data, 0, "hello", 10)
    """
    if not isinstance(value, str):
        raise TypeError(f"Value value:{value} is not from Type string")

    if max_size > 16382:
        raise ValueError(f"max_size: {max_size} > max. allowed 16382 chars")

    size = len(value)
    if size > max_size:
        raise ValueError(f"size {size} > max_size {max_size}")

    # set max string size (2 bytes, big-endian)
    bytearray_[byte_index : byte_index + 2] = struct.pack(">H", max_size)

    # set current length (2 bytes, big-endian)
    bytearray_[byte_index + 2 : byte_index + 4] = struct.pack(">H", size)

    # encode and write UTF-16-BE characters
    encoded = value.encode("utf-16-be")
    bytearray_[byte_index + 4 : byte_index + 4 + len(encoded)] = encoded


def set_tod(bytearray_: bytearray, byte_index: int, tod: timedelta) -> bytearray:
    """Set TIME_OF_DAY value in bytearray.

    Notes:
        Datatype `TIME_OF_DAY` is stored as milliseconds since midnight in 4 bytes.
        Range: 0 to 86399999 ms (00:00:00.000 to 23:59:59.999).

    Args:
        bytearray_: buffer to write to.
        byte_index: byte index from where to start writing.
        tod: timedelta representing the time of day.

    Returns:
        Buffer with the written value.

    Examples:
        >>> from datetime import timedelta
        >>> data = bytearray(4)
        >>> set_tod(data, 0, timedelta(hours=12, minutes=30, seconds=15, milliseconds=500))
    """
    if tod.days >= 1 or tod < timedelta(0):
        raise ValueError("TIME_OF_DAY must be between 00:00:00.000 and 23:59:59.999")
    ms = int(tod.total_seconds() * 1000)
    bytearray_[byte_index : byte_index + 4] = ms.to_bytes(4, byteorder="big")
    return bytearray_


def set_dtl(bytearray_: bytearray, byte_index: int, dt_: datetime) -> bytearray:
    """Set DTL (Date and Time Long) value in bytearray.

    Notes:
        Datatype `DTL` consists of 12 bytes in the PLC:
        - Bytes 0-1: Year (uint16, big-endian)
        - Byte 2: Month (1-12)
        - Byte 3: Day (1-31)
        - Byte 4: Weekday (1=Sunday, 7=Saturday)
        - Byte 5: Hour (0-23)
        - Byte 6: Minute (0-59)
        - Byte 7: Second (0-59)
        - Bytes 8-11: Nanoseconds (uint32, big-endian)

    Args:
        bytearray_: buffer to write to.
        byte_index: byte index from where to start writing.
        dt_: datetime object to write.

    Returns:
        Buffer with the written value.

    Examples:
        >>> from datetime import datetime
        >>> data = bytearray(12)
        >>> set_dtl(data, 0, datetime(2024, 3, 27, 14, 30, 0))
    """
    if dt_ > datetime(2554, 12, 31, 23, 59, 59):
        raise ValueError("date_val is higher than specification allows.")

    # Year as 2-byte big-endian
    bytearray_[byte_index : byte_index + 2] = struct.pack(">H", dt_.year)
    bytearray_[byte_index + 2] = dt_.month
    bytearray_[byte_index + 3] = dt_.day
    # Weekday: isoweekday() returns 1=Monday..7=Sunday, S7 uses 1=Sunday..7=Saturday
    bytearray_[byte_index + 4] = (dt_.isoweekday() % 7) + 1
    bytearray_[byte_index + 5] = dt_.hour
    bytearray_[byte_index + 6] = dt_.minute
    bytearray_[byte_index + 7] = dt_.second
    # Nanoseconds from microseconds
    nanoseconds = dt_.microsecond * 1000
    bytearray_[byte_index + 8 : byte_index + 12] = struct.pack(">I", nanoseconds)
    return bytearray_


def set_dt(bytearray_: bytearray, byte_index: int, dt_: datetime) -> bytearray:
    """Set DATE_AND_TIME value in bytearray.

    Notes:
        Datatype `DATE_AND_TIME` consists of 8 bytes in BCD encoding:
        - Byte 0: Year (BCD, 0-99, 90-99 = 1990-1999, 0-89 = 2000-2089)
        - Byte 1: Month (BCD)
        - Byte 2: Day (BCD)
        - Byte 3: Hour (BCD)
        - Byte 4: Minute (BCD)
        - Byte 5: Second (BCD)
        - Byte 6-7: Milliseconds (BCD) + weekday

    Args:
        bytearray_: buffer to write to.
        byte_index: byte index from where to start writing.
        dt_: datetime object to write.

    Returns:
        Buffer with the written value.

    Examples:
        >>> from datetime import datetime
        >>> data = bytearray(8)
        >>> set_dt(data, 0, datetime(2020, 7, 12, 17, 32, 2, 854000))
    """

    def byte_to_bcd(val: int) -> int:
        return ((val // 10) << 4) | (val % 10)

    year = dt_.year
    if year < 1990 or year > 2089:
        raise ValueError("DATE_AND_TIME year must be between 1990 and 2089")

    year_bcd = year - 2000 if year >= 2000 else year - 1900
    bytearray_[byte_index] = byte_to_bcd(year_bcd)
    bytearray_[byte_index + 1] = byte_to_bcd(dt_.month)
    bytearray_[byte_index + 2] = byte_to_bcd(dt_.day)
    bytearray_[byte_index + 3] = byte_to_bcd(dt_.hour)
    bytearray_[byte_index + 4] = byte_to_bcd(dt_.minute)
    bytearray_[byte_index + 5] = byte_to_bcd(dt_.second)

    # Milliseconds: 3 BCD digits in byte 6 and upper nibble of byte 7
    ms = dt_.microsecond // 1000
    ms_hundreds = ms // 100
    ms_tens = (ms % 100) // 10
    ms_ones = ms % 10
    bytearray_[byte_index + 6] = byte_to_bcd(ms_hundreds * 10 + ms_tens)
    # Lower nibble of byte 7: weekday (1=Sunday..7=Saturday)
    weekday = (dt_.isoweekday() % 7) + 1
    bytearray_[byte_index + 7] = (ms_ones << 4) | weekday

    return bytearray_
