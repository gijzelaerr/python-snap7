import re
import struct
from datetime import date
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
    _bytes = struct.pack("B", _int)
    bytearray_[byte_index : byte_index + 1] = _bytes
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
    _bytes = struct.unpack("2B", struct.pack(">H", _int))
    bytearray_[byte_index : byte_index + 2] = _bytes
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
    _bytes = struct.unpack("2B", struct.pack(">h", _int))
    bytearray_[byte_index : byte_index + 2] = _bytes
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
    _bytes = struct.unpack("2B", struct.pack(">H", _int))
    bytearray_[byte_index : byte_index + 2] = _bytes
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
    real_packed = struct.pack(">f", float(real))
    _bytes = struct.unpack("4B", real_packed)
    for i, b in enumerate(_bytes):
        bytearray_[byte_index + i] = b
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
        or 'max_size' is greater than 254 or 'value' contains non-ascii characters.

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
    if not value.isascii():
        raise ValueError(
            "Value contains non-ascii values, which is not compatible with PLC Type STRING."
            "Check encoding of value or try set_wstring() (utf-16 encoding needed)."
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
    _bytes = struct.unpack("4B", struct.pack(">I", dword))
    for i, b in enumerate(_bytes):
        bytearray_[byte_index + i] = b


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
    _bytes = struct.unpack("4B", struct.pack(">i", dint))
    for i, b in enumerate(_bytes):
        bytearray_[byte_index + i] = b


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
    _bytes = struct.unpack("4B", struct.pack(">I", udint))
    for i, b in enumerate(_bytes):
        bytearray_[byte_index + i] = b


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
    _bytes = struct.unpack("B", struct.pack(">B", _int))
    bytearray_[byte_index] = _bytes[0]
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
    _bytes = struct.unpack("B", struct.pack(">b", _int))
    bytearray_[byte_index] = _bytes[0]
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


def set_lword(bytearray_: bytearray, byte_index: int, lword: bytearray) -> bytearray:
    """Set the long word

    THIS VALUE IS NEITHER TESTED NOR VERIFIED BY A REAL PLC AT THE MOMENT

    Notes:
        Datatype `lword` (long word) consists in 8 bytes in the PLC.
        Maximum value posible is bytearray(b"\\xFF\\xFF\\xFF\\xFF\\xFF\\xFF\\xFF\\xFF")
        Lowest value posible is bytearray(b"\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00")

    Args:
        bytearray_: buffer to read from.
        byte_index: byte index from where to start reading.
        lword: Value to write

    Returns:
        Bytearray conform value.

    Examples:
        read lword value (here as example 0xAB\0xCD) from DB1.10 of a PLC
        >>> data = set_lword(data, 0, bytearray(b"\\x00\\x00\\x00\\x00\\x00\\x00\\xAB\\xCD"))
        bytearray(b"\\x00\\x00\\x00\\x00\\x00\\x00\\xAB\\xCD")
        >>> from snap7 import Client
        >>> Client().db_write(db_number=1, start=10, data=data)
    """
    #  data = bytearray_[byte_index:byte_index + 4]
    #  dword = struct.unpack('8B', struct.pack('>Q', *data))[0]
    #  return bytearray(dword)
    raise NotImplementedError


def set_char(bytearray_: bytearray, byte_index: int, chr_: str) -> Union[ValueError, bytearray]:
    """Set char value in a bytearray.

    Notes:
        Datatype `char` in the PLC is represented in 1 byte. It has to be in ASCII-format

    Args:
        bytearray_: buffer to read from.
        byte_index: byte index to start reading from.
        chr_: Char to be set

    Returns:
        Value read.

    Examples:
        Read 1 Byte raw from DB1.10, where a char value is stored. Return Python compatible value.
        >>> data = set_char(data, 0, 'C')
        >>> from snap7 import Client
        >>> Client().db_write(db_number=1, start=10, data=data)
            'bytearray('0x43')
    """
    if chr_.isascii():
        bytearray_[byte_index] = ord(chr_)
        return bytearray_
    raise ValueError(f"chr_ : {chr_} contains a None-Ascii value, but ASCII-only is allowed.")


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
    _bytes = struct.unpack("2B", struct.pack(">h", _days))
    bytearray_[byte_index : byte_index + 2] = _bytes
    return bytearray_
