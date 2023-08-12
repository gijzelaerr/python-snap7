"""
This module contains utility functions for working with PLC DB objects.
There are functions to work with the raw bytearray data snap7 functions return
In order to work with this data you need to make python able to work with the
PLC bytearray data.

For example code see test_util.py and example.py in the example folder.


example::

    spec/DB layout

    # Byte index    Variable name  Datatype
    layout=\"\"\"
    4	          ID             INT
    6             NAME	         STRING[6]

    12.0          testbool1      BOOL
    12.1          testbool2      BOOL
    12.2          testbool3      BOOL
    12.3          testbool4      BOOL
    12.4          testbool5      BOOL
    12.5          testbool6      BOOL
    12.6          testbool7      BOOL
    12.7          testbool8      BOOL
    13            testReal       REAL
    17            testDword      DWORD
    \"\"\"

    client = snap7.client.Client()
    client.connect('192.168.200.24', 0, 3)

    # this looks confusing but this means uploading from the PLC to YOU
    # so downloading in the PC world :)

    all_data = client.upload(db_number)

    simple:

    db1 = snap7.util.DB(
        db_number,              # the db we use
        all_data,               # bytearray from the plc
        layout,                 # layout specification DB variable data
                                # A DB specification is the specification of a
                                # DB object in the PLC you can find it using
                                # the dataview option on a DB object in PCS7

        17+2,                   # size of the specification 17 is start
                                # of last value
                                # which is a DWORD which is 2 bytes,

        1,                      # number of row's / specifications

        id_field='ID',          # field we can use to identify a row.
                                # default index is used
        layout_offset=4,        # sometimes specification does not start a 0
                                # like in our example
        db_offset=0             # At which point in 'all_data' should we start
                                # reading. if could be that the specification
                                # does not start at 0
    )

    Now we can use db1 in python as a dict. if 'ID' contains
    the 'test' we can identify the 'test' row in the all_data bytearray

    To test of you layout matches the data from the plc you can
    just print db1[0] or db['test'] in the example

    db1['test']['testbool1'] = 0

    If we do not specify a id_field this should work to read out the
    same data.

    db1[0]['testbool1']

    to read and write a single Row from the plc. takes like 5ms!

    db1['test'].write()

    db1['test'].read(client)


"""
import re
import time
import struct
import logging
from typing import Dict, Union, Callable, Optional, List
from datetime import date, datetime, timedelta
from collections import OrderedDict

from .types import Areas
from .client import Client

logger = logging.getLogger(__name__)


def utc2local(utc: Union[date, datetime]) -> Union[datetime, date]:
    """Returns the local datetime

    Args:
        utc: UTC type date or datetime.

    Returns:
        Local datetime.
    """
    epoch = time.mktime(utc.timetuple())
    offset = datetime.fromtimestamp(epoch) - datetime.utcfromtimestamp(epoch)
    return utc + offset


def get_bool(bytearray_: bytearray, byte_index: int, bool_index: int) -> bool:
    """Get the boolean value from location in bytearray

    Args:
        bytearray_: buffer data.
        byte_index: byte index to read from.
        bool_index: bit index to read from.

    Returns:
        True if the bit is 1, else 0.

    Examples:
        >>> buffer = bytearray([0b00000001])  # Only one byte length
        >>> get_bool(buffer, 0, 0)  # The bit 0 starts at the right.
            True
    """
    index_value = 1 << bool_index
    byte_value = bytearray_[byte_index]
    current_value = byte_value & index_value
    return current_value == index_value


def set_bool(bytearray_: bytearray, byte_index: int, bool_index: int, value: bool):
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
        return

    if value:
        # make sure index_v is IN current byte
        bytearray_[byte_index] += index_value
    else:
        # make sure index_v is NOT in current byte
        bytearray_[byte_index] -= index_value


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
    _bytes = struct.pack('B', _int)
    bytearray_[byte_index:byte_index + 1] = _bytes
    return bytearray_


def get_byte(bytearray_: bytearray, byte_index: int) -> bytes:
    """Get byte value from bytearray.

    Notes:
        WORD 8bit 1bytes Decimal number unsigned B#(0) to B#(255) => 0 to 255

    Args:
        bytearray_: buffer to be read from.
        byte_index: byte index to be read.

    Returns:
        value get from the byte index.
    """
    data = bytearray_[byte_index:byte_index + 1]
    data[0] = data[0] & 0xff
    packed = struct.pack('B', *data)
    value = struct.unpack('B', packed)[0]
    return value


def set_word(bytearray_: bytearray, byte_index: int, _int: int):
    """Set value in bytearray to word

    Notes:
        Word datatype is 2 bytes long.

    Args:
        bytearray_: buffer to be written.
        byte_index: byte index to start write from.
        _int: value to be write.

    Return:
        buffer with the written value
    """
    _int = int(_int)
    _bytes = struct.unpack('2B', struct.pack('>H', _int))
    bytearray_[byte_index:byte_index + 2] = _bytes
    return bytearray_


def get_word(bytearray_: bytearray, byte_index: int) -> bytearray:
    """Get word value from bytearray.

    Notes:
        WORD 16bit 2bytes Decimal number unsigned B#(0,0) to B#(255,255) => 0 to 65535

    Args:
        bytearray_: buffer to get the word from.
        byte_index: byte index from where start reading from.

    Returns:
        Word value.

    Examples:
        >>> data = bytearray([0, 100])  # two bytes for a word
        >>> snap7.util.get_word(data, 0)
            100
    """
    data = bytearray_[byte_index:byte_index + 2]
    data[1] = data[1] & 0xff
    data[0] = data[0] & 0xff
    packed = struct.pack('2B', *data)
    value = struct.unpack('>H', packed)[0]
    return value


def set_int(bytearray_: bytearray, byte_index: int, _int: int):
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
        >>> snap7.util.set_int(data, 0, 255)
            bytearray(b'\\x00\\xff')
    """
    # make sure were dealing with an int
    _int = int(_int)
    _bytes = struct.unpack('2B', struct.pack('>h', _int))
    bytearray_[byte_index:byte_index + 2] = _bytes
    return bytearray_


def get_int(bytearray_: bytearray, byte_index: int) -> int:
    """Get int value from bytearray.

    Notes:
        Datatype `int` in the PLC is represented in two bytes

    Args:
        bytearray_: buffer to read from.
        byte_index: byte index to start reading from.

    Returns:
        Value read.

    Examples:
        >>> data = bytearray([0, 255])
        >>> snap7.util.get_int(data, 0)
            255
    """
    data = bytearray_[byte_index:byte_index + 2]
    data[1] = data[1] & 0xff
    data[0] = data[0] & 0xff
    packed = struct.pack('2B', *data)
    value = struct.unpack('>h', packed)[0]
    return value


def set_uint(bytearray_: bytearray, byte_index: int, _int: int):
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
        >>> data = bytearray(2)
        >>> snap7.util.set_uint(data, 0, 65535)
            bytearray(b'\\xff\\xff')
    """
    # make sure were dealing with an int
    _int = int(_int)
    _bytes = struct.unpack('2B', struct.pack('>H', _int))
    bytearray_[byte_index:byte_index + 2] = _bytes
    return bytearray_


def get_uint(bytearray_: bytearray, byte_index: int) -> int:
    """Get unsigned int value from bytearray.

    Notes:
        Datatype `uint` in the PLC is represented in two bytes
        Maximum posible value is 65535.
        Lower posible value is 0.

    Args:
        bytearray_: buffer to read from.
        byte_index: byte index to start reading from.

    Returns:
        Value read.

    Examples:
        >>> data = bytearray([255, 255])
        >>> snap7.util.get_uint(data, 0)
            65535
    """
    data = bytearray_[byte_index:byte_index + 2]
    data[1] = data[1] & 0xff
    data[0] = data[0] & 0xff
    packed = struct.pack('2B', *data)
    value = struct.unpack('>H', packed)[0]
    return value


def set_real(bytearray_: bytearray, byte_index: int, real) -> bytearray:
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
        >>> snap7.util.set_real(data, 0, 123.321)
            bytearray(b'B\\xf6\\xa4Z')
    """
    real = float(real)
    real = struct.pack('>f', real)
    _bytes = struct.unpack('4B', real)
    for i, b in enumerate(_bytes):
        bytearray_[byte_index + i] = b
    return bytearray_


def get_real(bytearray_: bytearray, byte_index: int) -> float:
    """Get real value.

    Notes:
        Datatype `real` is represented in 4 bytes in the PLC.
        The packed representation uses the `IEEE 754 binary32`.

    Args:
        bytearray_: buffer to read from.
        byte_index: byte index to reading from.

    Returns:
        Real value.

    Examples:
        >>> data = bytearray(b'B\\xf6\\xa4Z')
        >>> snap7.util.get_real(data, 0)
            123.32099914550781
    """
    x = bytearray_[byte_index:byte_index + 4]
    real = struct.unpack('>f', struct.pack('4B', *x))[0]
    return real


def set_fstring(bytearray_: bytearray, byte_index: int, value: str, max_length: int):
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
        >>> snap7.util.set_fstring(data, 0, "hello world", 15)
        >>> data
            bytearray(b'hello world    \x00\x00\x00\x00\x00')
    """
    if not value.isascii():
        raise ValueError("Value contains non-ascii values.")
    # FAIL HARD WHEN trying to write too much data into PLC
    size = len(value)
    if size > max_length:
        raise ValueError(f'size {size} > max_length {max_length} {value}')

    i = 0

    # fill array which chr integers
    for i, c in enumerate(value):
        bytearray_[byte_index + i] = ord(c)

    # fill the rest with empty space
    for r in range(i + 1, max_length):
        bytearray_[byte_index + r] = ord(' ')


def set_string(bytearray_: bytearray, byte_index: int, value: str, max_size: int = 254):
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
        >>> data = bytearray(20)
        >>> snap7.util.set_string(data, 0, "hello world", 254)
        >>> data
            bytearray(b'\\xff\\x0bhello world\\x00\\x00\\x00\\x00\\x00\\x00\\x00')
    """
    if not isinstance(value, str):
        raise TypeError(f"Value value:{value} is not from Type string")

    if max_size > 254:
        raise ValueError(f'max_size: {max_size} > max. allowed 254 chars')
    if not value.isascii():
        raise ValueError("Value contains non-ascii values, which is not compatible with PLC Type STRING."
                         "Check encoding of value or try set_wstring() (utf-16 encoding needed).")
    size = len(value)
    # FAIL HARD WHEN trying to write too much data into PLC
    if size > max_size:
        raise ValueError(f'size {size} > max_size {max_size} {value}')

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
        bytearray_[byte_index + 2 + r] = ord(' ')


def get_fstring(bytearray_: bytearray, byte_index: int, max_length: int, remove_padding: bool = True) -> str:
    """Parse space-padded fixed-length string from bytearray

    Notes:
        This function supports fixed-length ASCII strings, right-padded with spaces.

    Args:
        bytearray_: buffer from where to get the string.
        byte_index: byte index from where to start reading.
        max_length: the maximum length of the string.
        remove_padding: whether to remove the right-padding.

    Returns:
        String value.

    Examples:
        >>> data = [ord(letter) for letter in "hello world    "]
        >>> snap7.util.get_fstring(data, 0, 15)
        'hello world'
        >>> snap7.util.get_fstring(data, 0, 15, remove_padding=false)
        'hello world    '
    """
    data = map(chr, bytearray_[byte_index:byte_index + max_length])
    string = "".join(data)

    if remove_padding:
        return string.rstrip(' ')
    else:
        return string


def get_string(bytearray_: bytearray, byte_index: int) -> str:
    """Parse string from bytearray

    Notes:
        The first byte of the buffer will contain the max size posible for a string.
        The second byte contains the length of the string that contains.

    Args:
        bytearray_: buffer from where to get the string.
        byte_index: byte index from where to start reading.

    Returns:
        String value.

    Examples:
        >>> data = bytearray([254, len("hello world")] + [ord(letter) for letter in "hello world"])
        >>> snap7.util.get_string(data, 0)
        'hello world'
    """

    str_length = int(bytearray_[byte_index + 1])
    max_string_size = int(bytearray_[byte_index])

    if str_length > max_string_size or max_string_size > 254:
        logger.error("The string is too big for the size encountered in specification")
        logger.error("WRONG SIZED STRING ENCOUNTERED")
        raise TypeError("String contains {} chars, but max. {} chars are expected or is larger than 254."
                        "Bytearray doesn't seem to be a valid string.".format(str_length, max_string_size))
    data = map(chr, bytearray_[byte_index + 2:byte_index + 2 + str_length])
    return "".join(data)


def get_dword(bytearray_: bytearray, byte_index: int) -> int:
    """ Gets the dword from the buffer.

    Notes:
        Datatype `dword` consists in 8 bytes in the PLC.
        The maximum value posible is `4294967295`

    Args:
        bytearray_: buffer to read.
        byte_index: byte index from where to start reading.

    Returns:
        Value read.

    Examples:
        >>> data = bytearray(8)
        >>> data[:] = b"\\x12\\x34\\xAB\\xCD"
        >>> snap7.util.get_dword(data, 0)
            4294967295
    """
    data = bytearray_[byte_index:byte_index + 4]
    dword = struct.unpack('>I', struct.pack('4B', *data))[0]
    return dword


def set_dword(bytearray_: bytearray, byte_index: int, dword: int):
    """Set a DWORD to the buffer.

    Notes:
        Datatype `dword` consists in 8 bytes in the PLC.
        The maximum value posible is `4294967295`

    Args:
        bytearray_: buffer to write to.
        byte_index: byte index from where to writing reading.
        dword: value to write.

    Examples:
        >>> data = bytearray(4)
        >>> snap7.util.set_dword(data,0, 4294967295)
        >>> data
            bytearray(b'\\xff\\xff\\xff\\xff')
    """
    dword = int(dword)
    _bytes = struct.unpack('4B', struct.pack('>I', dword))
    for i, b in enumerate(_bytes):
        bytearray_[byte_index + i] = b


def get_dint(bytearray_: bytearray, byte_index: int) -> int:
    """Get dint value from bytearray.

    Notes:
        Datatype `dint` consists in 4 bytes in the PLC.
        Maximum possible value is 2147483647.
        Lower posible value is -2147483648.

    Args:
        bytearray_: buffer to read.
        byte_index: byte index from where to start reading.

    Returns:
        Value read.

    Examples:
        >>> import struct
        >>> data = bytearray(4)
        >>> data[:] = struct.pack(">i", 2147483647)
        >>> snap7.util.get_dint(data, 0)
            2147483647
    """
    data = bytearray_[byte_index:byte_index + 4]
    dint = struct.unpack('>i', struct.pack('4B', *data))[0]
    return dint


def set_dint(bytearray_: bytearray, byte_index: int, dint: int):
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
        >>> snap7.util.set_dint(data, 0, 2147483647)
        >>> data
            bytearray(b'\\x7f\\xff\\xff\\xff')
    """
    dint = int(dint)
    _bytes = struct.unpack('4B', struct.pack('>i', dint))
    for i, b in enumerate(_bytes):
        bytearray_[byte_index + i] = b


def get_udint(bytearray_: bytearray, byte_index: int) -> int:
    """Get unsigned dint value from bytearray.

    Notes:
        Datatype `udint` consists in 4 bytes in the PLC.
        Maximum possible value is 4294967295.
        Minimum posible value is 0.

    Args:
        bytearray_: buffer to read.
        byte_index: byte index from where to start reading.

    Returns:
        Value read.

    Examples:
        >>> import struct
        >>> data = bytearray(4)
        >>> data[:] = struct.pack(">I", 4294967295)
        >>> snap7.util.get_udint(data, 0)
            4294967295
    """
    data = bytearray_[byte_index:byte_index + 4]
    dint = struct.unpack('>I', struct.pack('4B', *data))[0]
    return dint


def set_udint(bytearray_: bytearray, byte_index: int, udint: int):
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
        >>> snap7.util.set_udint(data, 0, 4294967295)
        >>> data
            bytearray(b'\\xff\\xff\\xff\\xff')
    """
    udint = int(udint)
    _bytes = struct.unpack('4B', struct.pack('>I', udint))
    for i, b in enumerate(_bytes):
        bytearray_[byte_index + i] = b


def get_s5time(bytearray_: bytearray, byte_index: int) -> str:
    micro_to_milli = 1000
    data_bytearray = bytearray_[byte_index:byte_index + 2]
    s5time_data_int_like = list(data_bytearray.hex())
    if s5time_data_int_like[0] == '0':
        # 10ms
        time_base = 10
    elif s5time_data_int_like[0] == '1':
        # 100ms
        time_base = 100
    elif s5time_data_int_like[0] == '2':
        # 1s
        time_base = 1000
    elif s5time_data_int_like[0] == '3':
        # 10s
        time_base = 10000
    else:
        raise ValueError('This value should not be greater than 3')

    s5time_bcd = \
        int(s5time_data_int_like[1]) * 100 + \
        int(s5time_data_int_like[2]) * 10 + \
        int(s5time_data_int_like[3])
    s5time_microseconds = time_base * s5time_bcd
    s5time = timedelta(microseconds=s5time_microseconds * micro_to_milli)
    # here we must return a string like variable, otherwise nothing will return
    return "".join(str(s5time))


def get_dt(bytearray_: bytearray, byte_index: int) -> str:
    """Get  DATE_AND_TIME Value from bytearray as ISO 8601 formatted Date String
    Notes:
        Datatype `DATE_AND_TIME` consists in 8 bytes in the PLC.
    Args:
        bytearray_: buffer to read.
        byte_index: byte index from where to start writing.
    Examples:
        >>> data = bytearray(8)
        >>> data[:] = [32, 7, 18, 23, 50, 2, 133, 65]  #'2020-07-12T17:32:02.854000'
        >>> get_dt(data,0)
            '2020-07-12T17:32:02.854000'
    """
    return get_date_time_object(bytearray_, byte_index).isoformat(timespec='microseconds')


def get_date_time_object(bytearray_: bytearray, byte_index: int) -> datetime:
    """Get  DATE_AND_TIME Value from bytearray as python datetime object
    Notes:
        Datatype `DATE_AND_TIME` consists in 8 bytes in the PLC.
    Args:
        bytearray_: buffer to read.
        byte_index: byte index from where to start writing.
    Examples:
        >>> data = bytearray(8)
        >>> data[:] = [32, 7, 18, 23, 50, 2, 133, 65]  #date '2020-07-12 17:32:02.854'
        >>> get_date_time_object(data,0)
            datetime.datetime(2020, 7, 12, 17, 32, 2, 854000)
    """

    def bcd_to_byte(byte: int) -> int:
        return (byte >> 4) * 10 + (byte & 0xF)

    year = bcd_to_byte(bytearray_[byte_index])
    # between 1990 and  2089, only last two digits are saved in DB 90 - 89
    year = 2000 + year if year < 90 else 1900 + year
    month = bcd_to_byte(bytearray_[byte_index + 1])
    day = bcd_to_byte(bytearray_[byte_index + 2])
    hour = bcd_to_byte(bytearray_[byte_index + 3])
    min_ = bcd_to_byte(bytearray_[byte_index + 4])
    sec = bcd_to_byte(bytearray_[byte_index + 5])
    # plc save miliseconds in two bytes with the most signifanct byte used only
    # in the last byte for microseconds the other for weekday
    # * 1000 because pythoin datetime needs microseconds not milli
    microsec = (bcd_to_byte(bytearray_[byte_index + 6]) * 10
                + bcd_to_byte(bytearray_[byte_index + 7] >> 4)) * 1000

    return datetime(year, month, day, hour, min_, sec, microsec)


def get_time(bytearray_: bytearray, byte_index: int) -> str:
    """Get time value from bytearray.

        Notes:
            Datatype `time` consists in 4 bytes in the PLC.
            Maximum possible value is T#24D_20H_31M_23S_647MS(2147483647).
            Lower posible value is T#-24D_20H_31M_23S_648MS(-2147483648).

        Args:
            bytearray_: buffer to read.
            byte_index: byte index from where to start reading.

        Returns:
            Value read.

        Examples:
            >>> import struct
            >>> data = bytearray(4)
            >>> data[:] = struct.pack(">i", 2147483647)
            >>> snap7.util.get_time(data, 0)
                '24:20:31:23:647'
        """
    data_bytearray = bytearray_[byte_index:byte_index + 4]
    bits = 32
    sign = 1
    byte_str = data_bytearray.hex()
    val = int(byte_str, 16)
    if (val & (1 << (bits - 1))) != 0:
        sign = -1  # if sign bit is set e.g., 8bit: 128-255
        val -= (1 << bits)  # compute negative value
        val *= sign

    milli_seconds = val % 1000
    seconds = val // 1000
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24

    sign_str = '' if sign >= 0 else '-'
    time_str = f"{sign_str}{days!s}:{hours % 24!s}:{minutes % 60!s}:{seconds % 60!s}.{milli_seconds!s}"

    return time_str


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

            >>> snap7.util.set_time(data, 0, '-22:3:57:28.192')

            >>> data
                bytearray(b'\x8d\xda\xaf\x00')
        """
    sign = 1
    if re.fullmatch(r"(-?(2[0-3]|1?\d):(2[0-3]|1?\d|\d):([1-5]?\d):[1-5]?\d.\d{1,3})|"
                    r"(-24:(20|1?\d):(3[0-1]|[0-2]?\d):(2[0-3]|1?\d).(64[0-8]|6[0-3]\d|[0-5]\d{1,2}))|"
                    r"(24:(20|1?\d):(3[0-1]|[0-2]?\d):(2[0-3]|1?\d).(64[0-7]|6[0-3]\d|[0-5]\d{1,2}))", time_string):
        data_list = re.split('[: .]', time_string)
        days: str = data_list[0]
        hours: int = int(data_list[1])
        minutes: int = int(data_list[2])
        seconds: int = int(data_list[3])
        milli_seconds: int = int(data_list[4].ljust(3, '0'))
        if re.match(r'^-\d{1,2}$', days):
            sign = -1

        time_int = (
            (int(days) * sign * 3600 * 24 + (hours % 24) * 3600 + (minutes % 60) * 60 + seconds % 60) * 1000 + milli_seconds
            ) * sign
        bytes_array = time_int.to_bytes(4, byteorder='big', signed=True)
        bytearray_[byte_index:byte_index + 4] = bytes_array
        return bytearray_
    else:
        raise ValueError('time value out of range, please check the value interval')


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
        >>> snap7.util.set_usint(data, 0, 255)
            bytearray(b'\\xff')
    """
    _int = int(_int)
    _bytes = struct.unpack('B', struct.pack('>B', _int))
    bytearray_[byte_index] = _bytes[0]
    return bytearray_


def get_usint(bytearray_: bytearray, byte_index: int) -> int:
    """Get the unsigned small int from the bytearray

    Notes:
        Datatype `usint` (Unsigned small int) consists on 1 byte in the PLC.
        Maximum posible value is 255.
        Lower posible value is 0.

    Args:
        bytearray_: buffer to read from.
        byte_index: byte index from where to start reading.

    Returns:
        Value read.

    Examples:
        >>> data = bytearray([255])
        >>> snap7.util.get_usint(data, 0)
            255
    """
    data = bytearray_[byte_index] & 0xff
    packed = struct.pack('B', data)
    value = struct.unpack('>B', packed)[0]
    return value


def set_sint(bytearray_: bytearray, byte_index: int, _int) -> bytearray:
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
        >>> snap7.util.set_sint(data, 0, 127)
            bytearray(b'\\x7f')
    """
    _int = int(_int)
    _bytes = struct.unpack('B', struct.pack('>b', _int))
    bytearray_[byte_index] = _bytes[0]
    return bytearray_


def get_sint(bytearray_: bytearray, byte_index: int) -> int:
    """Get the small int

    Notes:
        Datatype `sint` (Small int) consists in 1 byte in the PLC.
        Maximum value posible is 127.
        Lowest value posible is -128.

    Args:
        bytearray_: buffer to read from.
        byte_index: byte index from where to start reading.

    Returns:
        Value read.

    Examples:
        >>> data = bytearray([127])
        >>> snap7.util.get_sint(data, 0)
            127
    """
    data = bytearray_[byte_index]
    packed = struct.pack('B', data)
    value = struct.unpack('>b', packed)[0]
    return value


def get_lint(bytearray_: bytearray, byte_index: int):
    """Get the long int

    THIS VALUE IS NEITHER TESTED NOR VERIFIED BY A REAL PLC AT THE MOMENT

    Notes:
        Datatype `lint` (long int) consists in 8 bytes in the PLC.
        Maximum value posible is +9223372036854775807
        Lowest value posible is -9223372036854775808

    Args:
        bytearray_: buffer to read from.
        byte_index: byte index from where to start reading.

    Returns:
        Value read.

    Examples:
        read lint value (here as example 12345) from DB1.10 of a PLC
        >>> data = client.db_read(db_number=1, start=10, size=8)
        >>> snap7.util.get_lint(data, 0)
            12345
    """

    # raw_lint = bytearray_[byte_index:byte_index + 8]
    # lint = struct.unpack('>q', struct.pack('8B', *raw_lint))[0]
    # return lint
    return NotImplementedError


def get_lreal(bytearray_: bytearray, byte_index: int) -> float:
    """Get the long real

    Notes:
        Datatype `lreal` (long real) consists in 8 bytes in the PLC.
        Negative Range: -1.7976931348623158e+308 to -2.2250738585072014e-308
        Positive Range: +2.2250738585072014e-308 to +1.7976931348623158e+308
        Zero: ±0

    Args:
        bytearray_: buffer to read from.
        byte_index: byte index from where to start reading.

    Returns:
        Value read.

    Examples:
        read lreal value (here as example 12345.12345) from DB1.10 of a PLC
        >>> data = client.db_read(db_number=1, start=10, size=8)
        >>> snap7.util.get_lreal(data, 0)
            12345.12345
    """
    return struct.unpack_from(">d", bytearray_, offset=byte_index)[0]


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
        >>> data = snap7.util.set_lreal(data, 12345.12345)
        >>> client.db_write(db_number=1, start=10, data)

    """
    lreal = float(lreal)
    struct.pack_into(">d", bytearray_, byte_index, lreal)
    return bytearray_


def get_lword(bytearray_: bytearray, byte_index: int) -> bytearray:
    """Get the long word

    THIS VALUE IS NEITHER TESTED NOR VERIFIED BY A REAL PLC AT THE MOMENT

    Notes:
        Datatype `lword` (long word) consists in 8 bytes in the PLC.
        Maximum value posible is bytearray(b"\\xFF\\xFF\\xFF\\xFF\\xFF\\xFF\\xFF\\xFF")
        Lowest value posible is bytearray(b"\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00")

    Args:
        bytearray_: buffer to read from.
        byte_index: byte index from where to start reading.

    Returns:
        Value read.

    Examples:
        read lword value (here as example 0xAB\0xCD) from DB1.10 of a PLC
        >>> data = client.db_read(db_number=1, start=10, size=8)
        >>> snap7.util.get_lword(data, 0)
            bytearray(b"\\x00\\x00\\x00\\x00\\x00\\x00\\xAB\\xCD")
    """
    #  data = bytearray_[byte_index:byte_index + 4]
    #  dword = struct.unpack('>Q', struct.pack('8B', *data))[0]
    #  return bytearray(dword)
    raise NotImplementedError


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
        >>> data = snap7.util.set_lword(data, 0, bytearray(b"\\x00\\x00\\x00\\x00\\x00\\x00\\xAB\\xCD"))
        bytearray(b"\\x00\\x00\\x00\\x00\\x00\\x00\\xAB\\xCD")
        >>> client.db_write(db_number=1, start=10, data)
    """
    #  data = bytearray_[byte_index:byte_index + 4]
    #  dword = struct.unpack('8B', struct.pack('>Q', *data))[0]
    #  return bytearray(dword)
    raise NotImplementedError


def get_ulint(bytearray_: bytearray, byte_index: int) -> int:
    """Get ulint value from bytearray.

    Notes:
        Datatype `int` in the PLC is represented in 8 bytes

    Args:
        bytearray_: buffer to read from.
        byte_index: byte index to start reading from.

    Returns:
        Value read.

    Examples:
        Read 8 Bytes raw from DB1.10, where an ulint value is stored. Return Python compatible value.
        >>> data = client.db_read(db_number=1, start=10, size=8)
        >>> snap7.util.get_ulint(data, 0)
            12345
    """
    raw_ulint = bytearray_[byte_index:byte_index + 8]
    lint = struct.unpack('>Q', struct.pack('8B', *raw_ulint))[0]
    return lint


def get_tod(bytearray_: bytearray, byte_index: int) -> timedelta:
    len_bytearray_ = len(bytearray_)
    byte_range = byte_index + 4
    if len_bytearray_ < byte_range:
        raise ValueError("Date can't be extracted from bytearray. bytearray_[Index:Index+16] would cause overflow.")
    time_val = timedelta(milliseconds=int.from_bytes(bytearray_[byte_index:byte_range], byteorder='big'))
    if time_val.days >= 1:
        raise ValueError("Time_Of_Date can't be extracted from bytearray. Bytearray contains unexpected values.")
    return time_val


def get_date(bytearray_: bytearray, byte_index: int = 0) -> date:
    len_bytearray_ = len(bytearray_)
    byte_range = byte_index + 2
    if len_bytearray_ < byte_range:
        raise ValueError("Date can't be extracted from bytearray. bytearray_[Index:Index+16] would cause overflow.")
    date_val = date(1990, 1, 1) + timedelta(days=int.from_bytes(bytearray_[byte_index:byte_range], byteorder='big'))
    if date_val > date(2168, 12, 31):
        raise ValueError("date_val is higher than specification allows.")
    return date_val


def get_ltime(bytearray_: bytearray, byte_index: int) -> str:
    raise NotImplementedError


def get_ltod(bytearray_: bytearray, byte_index: int) -> str:
    raise NotImplementedError


def get_ldt(bytearray_: bytearray, byte_index: int) -> str:
    raise NotImplementedError


def get_dtl(bytearray_: bytearray, byte_index: int) -> datetime:
    time_to_datetime = datetime(
        year=int.from_bytes(bytearray_[byte_index:byte_index + 2], byteorder='big'),
        month=int(bytearray_[byte_index + 2]),
        day=int(bytearray_[byte_index + 3]),
        hour=int(bytearray_[byte_index + 5]),
        minute=int(bytearray_[byte_index + 6]),
        second=int(bytearray_[byte_index + 7]),
        microsecond=int(bytearray_[byte_index + 8]))  # --- ? noch nicht genau genug
    if time_to_datetime > datetime(2554, 12, 31, 23, 59, 59):
        raise ValueError("date_val is higher than specification allows.")
    return time_to_datetime


def get_char(bytearray_: bytearray, byte_index: int) -> str:
    """Get char value from bytearray.

    Notes:
        Datatype `char` in the PLC is represented in 1 byte. It has to be in ASCII-format.

    Args:
        bytearray_: buffer to read from.
        byte_index: byte index to start reading from.

    Returns:
        Value read.

    Examples:
        Read 1 Byte raw from DB1.10, where a char value is stored. Return Python compatible value.
        >>> data = client.db_read(db_number=1, start=10, size=1)
        >>> snap7.util.get_char(data, 0)
            'C'
    """
    char = chr(bytearray_[byte_index])
    return char


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
        >>> data = snap7.util.set_char(data, 0, 'C')
        >>> client.db_write(db_number=1, start=10, data)
            'bytearray('0x43')
    """
    if chr_.isascii():
        bytearray_[byte_index] = ord(chr_)
        return bytearray_
    raise ValueError(f"chr_ : {chr_} contains a None-Ascii value, but ASCII-only is allowed.")


def get_wchar(bytearray_: bytearray, byte_index: int) -> Union[ValueError, str]:
    """Get wchar value from bytearray.

    Notes:
        Datatype `wchar` in the PLC is represented in 2 bytes. It has to be in utf-16-be format.


    Args:
        bytearray_: buffer to read from.
        byte_index: byte index to start reading from.

    Returns:
        Value read.

    Examples:
        Read 2 Bytes raw from DB1.10, where a wchar value is stored. Return Python compatible value.
        >>> data = client.db_read(db_number=1, start=10, size=2)
        >>> snap7.util.get_wchar(data, 0)
            'C'
    """
    if bytearray_[byte_index] == 0:
        return chr(bytearray_[1])
    return bytearray_[byte_index:byte_index + 2].decode('utf-16-be')


def get_wstring(bytearray_: bytearray, byte_index: int) -> str:
    """Parse wstring from bytearray

    Notes:
        Byte 0 and 1 contains the max size posible for a string (2 Byte value).
        byte 2 and 3 contains the length of the string that contains (2 Byte value).
        The other bytes contain WCHARs (2Byte) in utf-16-be style.

    Args:
        bytearray_: buffer from where to get the string.
        byte_index: byte index from where to start reading.

    Returns:
        String value.

    Examples:
        Read from DB1.10 22, where the WSTRING is stored, the raw 22 Bytes and convert them to a python string
        >>> data = client.db_read(db_number=1, start=10, size=22)
        >>> snap7.util.get_wstring(data, 0)
        'hello world'
    """
    # Byte 0 + 1 --> total length of wstring, should be bytearray_ - 4
    # Byte 2, 3 --> used length of wstring
    wstring_start = byte_index + 4

    max_wstring_size = bytearray_[byte_index:byte_index + 2]
    packed = struct.pack('2B', *max_wstring_size)
    max_wstring_symbols = struct.unpack('>H', packed)[0] * 2

    wstr_length_raw = bytearray_[byte_index + 2:byte_index + 4]
    wstr_symbols_amount = struct.unpack('>H', struct.pack('2B', *wstr_length_raw))[0] * 2

    if wstr_symbols_amount > max_wstring_symbols or max_wstring_symbols > 16382:
        logger.error("The wstring is too big for the size encountered in specification")
        logger.error("WRONG SIZED STRING ENCOUNTERED")
        raise TypeError("WString contains {} chars, but max. {} chars are expected or is larger than 16382."
                        "Bytearray doesn't seem to be a valid string.".format(wstr_symbols_amount, max_wstring_symbols))

    return bytearray_[wstring_start:wstring_start + wstr_symbols_amount].decode('utf-16-be')


def get_array(bytearray_: bytearray, byte_index: int) -> List:
    raise NotImplementedError
# ---------------------------


def parse_specification(db_specification: str) -> OrderedDict:
    """Create a db specification derived from a
        dataview of a db in which the byte layout
        is specified

    Args:
        db_specification: string formatted table with the indexes, aliases and types.

    Returns:
        Parsed DB specification.
    """
    parsed_db_specification = OrderedDict()

    for line in db_specification.split('\n'):
        if line and not line.lstrip().startswith('#'):
            index, var_name, _type = line.split('#')[0].split()
            parsed_db_specification[var_name] = (index, _type)

    return parsed_db_specification


class DB:
    """
    Manage a DB bytearray block given a specification
    of the Layout.

    It is possible to have many repetitive instances of
    a specification this is called a "row".

    Probably most usecases there is just one row

    Note:
        This class has some of the semantics of a dict. In particular, the membership operators
        (``in``, ``not it``), the access operator (``[]``), as well as the :func:`~DB.keys()` and
        :func:`~DB.items()` methods work as usual. Iteration, on the other hand, happens on items
        instead of keys (much like :func:`~DB.items()` method).

    Attributes:
        bytearray_: buffer data from the PLC.
        specification: layout of the DB Rows.
        row_size: bytes size of a db row.
        layout_offset: at which byte in the row specificaion we
            start reading the data.
        db_offset: at which byte in the db starts reading.

    Examples:
        >>> db1[0]['testbool1'] = test
        >>> db1.write(client)   # puts data in plc
    """
    bytearray_: Optional[bytearray] = None  # data from plc
    specification: Optional[str] = None     # layout of db rows
    id_field: Optional[str] = None          # ID field of the rows
    row_size: int = 0                       # bytes size of a db row
    layout_offset: int = 0                  # at which byte in row specification should
    db_offset: int = 0                      # at which byte in db should we start reading?

    # first fields could be be status data.
    # and only the last part could be control data
    # now you can be sure you will never overwrite
    # critical parts of db

    def __init__(self, db_number: int, bytearray_: bytearray,
                 specification: str, row_size: int, size: int, id_field: Optional[str] = None,
                 db_offset: int = 0, layout_offset: int = 0, row_offset: int = 0,
                 area: Areas = Areas.DB):
        """ Creates a new instance of the `Row` class.

        Args:
            db_number: number of the DB to read from. This value should be 0 if area!=Areas.DB.
            bytearray_: initial buffer read from the PLC.
            specification: layout of the PLC memory.
            row_size: bytes size of a db row.
            size: lenght of the memory area.
            id_field: name to reference the row. Optional.
            db_offset: at which byte in the db starts reading.
            layout_offset: at which byte in the row specificaion we
                start reading the data.
            row_offset: offset between rows.
            area: which memory area this row is representing.
        """
        self.db_number = db_number
        self.size = size
        self.row_size = row_size
        self.id_field = id_field
        self.area = area

        self.db_offset = db_offset
        self.layout_offset = layout_offset
        self.row_offset = row_offset

        self._bytearray = bytearray_
        self.specification = specification
        # loop over bytearray. make rowObjects
        # store index of id_field to row objects
        self.index: OrderedDict = OrderedDict()
        self.make_rows()

    def make_rows(self):
        """ Make each row for the DB."""
        id_field = self.id_field
        row_size = self.row_size
        specification = self.specification
        layout_offset = self.layout_offset
        row_offset = self.row_offset

        for i in range(self.size):
            # calculate where row in bytearray starts
            db_offset = i * (row_size + row_offset) + self.db_offset
            # create a row object
            row = DB_Row(self,
                         specification,
                         row_size=row_size,
                         db_offset=db_offset,
                         layout_offset=layout_offset,
                         row_offset=self.row_offset,
                         area=self.area)

            # store row object
            key = row[id_field] if id_field else i
            if key and key in self.index:
                msg = f'{key} not unique!'
                logger.error(msg)
            self.index[key] = row

    def __getitem__(self, key: str, default: Optional[None] = None) -> Union[None, int, float, str, bool, datetime]:
        """Access a row of the table through its index.

        Rows (values) are of type :class:`DB_Row`.

        Notes:
            This method has the same semantics as :class:`dict` access.
        """
        return self.index.get(key, default)

    def __iter__(self):
        """Iterate over the items contained in the table, in the physical order they are contained
        in memory.

        Notes:
            This method does not have the same semantics as :class:`dict` iteration. Instead, it
            has the same semantics as the :func:`~DB.items` method, yielding ``(index, row)``
            tuples.
        """
        yield from self.index.items()

    def __len__(self):
        """Return the number of rows contained in the DB.

        Notes:
            If more than one row has the same index value, it is only counted once.
        """
        return len(self.index)

    def __contains__(self, key):
        """Return whether the given key is the index of a row in the DB."""
        return key in self.index

    def keys(self):
        """Return a *view object* of the keys that are used as indices for the rows in the
        DB.
        """
        yield from self.index.keys()

    def items(self):
        """Return a *view object* of the items (``(index, row)`` pairs) that are used as indices
        for the rows in the DB.
        """
        yield from self.index.items()

    def export(self):
        """Export the object to an :class:`OrderedDict`, where each item in the dictionary
        has an index as the key, and the value of the DB row associated with that index
        as a value, represented itself as a :class:`dict` (as returned by :func:`DB_Row.export`).

        The outer dictionary contains the rows in the physical order they are contained in
        memory.

        Notes:
            This function effectively returns a snapshot of the DB.
        """
        ret = OrderedDict()
        for (k, v) in self.items():
            ret[k] = v.export()
        return ret

    def set_data(self, bytearray_: bytearray):
        """Set the new buffer data from the PLC to the current instance.

        Args:
            bytearray_: buffer to save.

        Raises:
            :obj:`TypeError`: if `bytearray_` is not an instance of :obj:`bytearray`
        """
        if not isinstance(bytearray_, bytearray):
            raise TypeError(f"Value bytearray_: {bytearray_} is not from type bytearray")
        self._bytearray = bytearray_

    def read(self, client: Client):
        """Reads all the rows from the PLC to the :obj:`bytearray` of this instance.

        Args:
            client: :obj:`Client` snap7 instance.

        Raises:
            :obj:`ValueError`: if the `row_size` is less than 0.
        """
        if self.row_size < 0:
            raise ValueError("row_size must be greater equal zero.")

        total_size = self.size * (self.row_size + self.row_offset)
        if self.area == Areas.DB:  # note: is it worth using the upload method?
            bytearray_ = client.db_read(self.db_number, self.db_offset, total_size)
        else:
            bytearray_ = client.read_area(self.area, 0, self.db_offset, total_size)

        # replace data in bytearray
        for i, b in enumerate(bytearray_):
            self._bytearray[i + self.db_offset] = b

        # todo: optimize by only rebuilding the index instead of all the DB_Row objects
        self.index.clear()
        self.make_rows()

    def write(self, client):
        """Writes all the rows from the :obj:`bytearray` of this instance to the PLC

        Notes:
            When the row_offset property has been set to something other than None while
            constructing this object, this operation is not guaranteed to be atomic.

        Args:
            client: :obj:`Client` snap7 instance.

        Raises:
            :obj:`ValueError`: if the `row_size` is less than 0.
        """
        if self.row_size < 0:
            raise ValueError("row_size must be greater equal zero.")

        # special case: we have a row offset, so we must write each row individually
        # this is because we don't want to change the data before the offset
        if self.row_offset:
            for _, v in self.index.items():
                v.write(client)
            return

        total_size = self.size * (self.row_size + self.row_offset)
        data = self._bytearray[self.db_offset:self.db_offset + total_size]

        if self.area == Areas.DB:
            client.db_write(self.db_number, self.db_offset, data)
        else:
            client.write_area(self.area, 0, self.db_offset, data)


class DB_Row:
    """
    Provide ROW API for DB bytearray

    Attributes:
        bytearray_: reference to the data of the parent DB.
        _specification: row specification layout.
    """
    bytearray_: bytearray  # data of reference to parent DB
    _specification: OrderedDict = OrderedDict()  # row specification

    def __init__(
            self,
            bytearray_: bytearray,
            _specification: str,
            row_size: Optional[int] = 0,
            db_offset: int = 0,
            layout_offset: int = 0,
            row_offset: Optional[int] = 0,
            area: Optional[Areas] = Areas.DB
    ):
        """Creates a new instance of the `DB_Row` class.

        Args:
            bytearray_: reference to the data of the parent DB.
            _specification: row specification layout.
            row_size: Amount of bytes of the row.
            db_offset: at which byte in the db starts reading.
            layout_offset: at which byte in the row specificaion we
                start reading the data.
            row_offset: offset between rows.
            area: which memory area this row is representing.

        Raises:
            :obj:`TypeError`: if `bytearray_` is not an instance of :obj:`bytearray` or :obj:`DB`.
        """

        self.db_offset = db_offset  # start point of row data in db
        self.layout_offset = layout_offset  # start point of row data in layout
        self.row_size = row_size  # lenght of the read
        self.row_offset = row_offset  # start of writable part of row
        self.area = area

        if not isinstance(bytearray_, (bytearray, DB)):
            raise TypeError(f"Value bytearray_ {bytearray_} is not from type (bytearray, DB)")
        self._bytearray = bytearray_
        self._specification = parse_specification(_specification)

    def get_bytearray(self) -> bytearray:
        """Gets bytearray from self or DB parent

        Returns:
            Buffer data corresponding to the row.
        """
        if isinstance(self._bytearray, DB):
            return self._bytearray._bytearray
        return self._bytearray

    def export(self) -> Dict[str, Union[str, int, float, bool, datetime]]:
        """ Export dictionary with values

        Returns:
            dictionary containing the values of each value of the row.
        """
        return {key: self[key] for key in self._specification}

    def __getitem__(self, key):
        """
        Get a specific db field
        """
        index, _type = self._specification[key]
        return self.get_value(index, _type)

    def __setitem__(self, key, value):
        index, _type = self._specification[key]
        self.set_value(index, _type, value)

    def __repr__(self):

        string = ""
        for var_name, (index, _type) in self._specification.items():
            string = f'{string}\n{var_name:<20} {self.get_value(index, _type):<10}'
        return string

    def unchanged(self, bytearray_: bytearray) -> bool:
        """ Checks if the bytearray is the same

        Args:
            bytearray_: buffer of data to check.

        Returns:
            True if the current `bytearray_` is equal to the new one. Otherwise is False.
        """
        return self.get_bytearray() == bytearray_

    def get_offset(self, byte_index: Union[str, int]) -> int:
        """ Calculate correct beginning position for a row
            the db_offset = row_size * index

        Args:
            byte_index: byte index from where to start reading from.

        Returns:
            Amount of bytes to ignore.
        """
        # add float typ to avoid error because of
        # the variable address with decimal point(like 0.0 or 4.0)
        return int(float(byte_index)) - self.layout_offset + self.db_offset

    def get_value(self, byte_index: Union[str, int], type_: str) -> Union[ValueError, int, float, str, datetime]:
        """ Gets the value for a specific type.

        Args:
            byte_index: byte index from where start reading.
            type_: type of data to read.

        Raises:
            :obj:`ValueError`: if reading a `string` when checking the lenght of the string.
            :obj:`ValueError`: if the `type_` is not handled.

        Returns:
            Value read according to the `type_`
        """
        bytearray_ = self.get_bytearray()

        # set parsing non case-sensitive
        type_ = type_.upper()

        if type_ == 'BOOL':
            byte_index, bool_index = str(byte_index).split('.')
            return get_bool(bytearray_, self.get_offset(byte_index),
                            int(bool_index))

        # remove 4 from byte index since
        # first 4 bytes are used by db
        byte_index = self.get_offset(byte_index)

        if type_.startswith('FSTRING'):
            max_size = re.search(r'\d+', type_)
            if max_size is None:
                raise ValueError("Max size could not be determinate. re.search() returned None")
            return get_fstring(bytearray_, byte_index, int(max_size[0]))
        elif type_.startswith('STRING'):
            max_size = re.search(r'\d+', type_)
            if max_size is None:
                raise ValueError("Max size could not be determinate. re.search() returned None")
            return get_string(bytearray_, byte_index)
        elif type_.startswith('WSTRING'):
            max_size = re.search(r'\d+', type_)
            if max_size is None:
                raise ValueError("Max size could not be determinate. re.search() returned None")
            return get_wstring(bytearray_, byte_index)
        else:
            type_to_func: Dict[str, Callable] = {
                'REAL': get_real,
                'DWORD': get_dword,
                'UDINT': get_udint,
                'DINT': get_dint,
                'UINT': get_uint,
                'INT': get_int,
                'WORD': get_word,
                'BYTE': get_byte,
                'S5TIME': get_s5time,
                'DATE_AND_TIME': get_dt,
                'USINT': get_usint,
                'SINT': get_sint,
                'TIME': get_time,
                'DATE': get_date,
                'TIME_OF_DAY': get_tod,
                'LREAL': get_lreal,
                'TOD': get_tod,
                'CHAR': get_char,
                'WCHAR': get_wchar,
                'DTL': get_dtl
            }
            if type_ in type_to_func:
                return type_to_func[type_](bytearray_, byte_index)
        raise ValueError

    def set_value(self, byte_index: Union[str, int], type_: str, value: Union[bool, str, float]) -> Union[bytearray, None]:
        """Sets the value for a specific type in the specified byte index.

        Args:
            byte_index: byte index to start writing to.
            type_: type of value to write.
            value: value to write.

        Raises:
            :obj:`ValueError`: if reading a `string` when checking the length of the string.
            :obj:`ValueError`: if the `type_` is not handled.

        Returns:
            Buffer data with the value written. Optional.
        """

        bytearray_ = self.get_bytearray()

        if type_ == 'BOOL' and isinstance(value, bool):
            byte_index, bool_index = str(byte_index).split(".")
            return set_bool(bytearray_, self.get_offset(byte_index),
                            int(bool_index), value)

        byte_index = self.get_offset(byte_index)

        if type_.startswith('FSTRING') and isinstance(value, str):
            max_size = re.search(r'\d+', type_)
            if max_size is None:
                raise ValueError("Max size could not be determinate. re.search() returned None")
            max_size_grouped = max_size.group(0)
            max_size_int = int(max_size_grouped)
            return set_fstring(bytearray_, byte_index, value, max_size_int)

        if type_.startswith('STRING') and isinstance(value, str):
            max_size = re.search(r'\d+', type_)
            if max_size is None:
                raise ValueError("Max size could not be determinate. re.search() returned None")
            max_size_grouped = max_size.group(0)
            max_size_int = int(max_size_grouped)
            return set_string(bytearray_, byte_index, value, max_size_int)

        if type_ == 'REAL':
            return set_real(bytearray_, byte_index, value)

        if isinstance(value, int):
            type_to_func = {
                'DWORD': set_dword,
                'UDINT': set_udint,
                'DINT': set_dint,
                'UINT': set_uint,
                'INT': set_int,
                'WORD': set_word,
                'BYTE': set_byte,
                'USINT': set_usint,
                'SINT': set_sint,
            }
            if type_ in type_to_func:
                return type_to_func[type_](bytearray_, byte_index, value)

        if type_ == 'TIME' and isinstance(value, str):
            return set_time(bytearray_, byte_index, value)

        raise ValueError

    def write(self, client: Client) -> None:
        """Write current data to db in plc

        Args:
            client: :obj:`Client` snap7 instance.

        Raises:
            :obj:`TypeError`: if the `_bytearray` is not an instance of :obj:`DB` class.
            :obj:`ValueError`: if the `row_size` is less than 0.
        """
        if not isinstance(self._bytearray, DB):
            raise TypeError(f"Value self._bytearray: {self._bytearray} is not from type DB.")
        if self.row_size < 0:
            raise ValueError("row_size must be greater equal zero.")

        db_nr = self._bytearray.db_number
        offset = self.db_offset
        data = self.get_bytearray()[offset:offset + self.row_size]
        db_offset = self.db_offset

        # indicate start of write only area of row!
        if self.row_offset:
            data = data[self.row_offset:]
            db_offset += self.row_offset

        if self.area == Areas.DB:
            client.db_write(db_nr, db_offset, data)
        else:
            client.write_area(self.area, 0, db_offset, data)

    def read(self, client: Client) -> None:
        """Read current data of db row from plc.

        Args:
            client: :obj:`Client` snap7 instance.

        Raises:
            :obj:`TypeError`: if the `_bytearray` is not an instance of :obj:`DB` class.
            :obj:`ValueError`: if the `row_size` is less than 0.
        """
        if not isinstance(self._bytearray, DB):
            raise TypeError(f"Value self._bytearray:{self._bytearray} is not from type DB.")
        if self.row_size < 0:
            raise ValueError("row_size must be greater equal zero.")
        db_nr = self._bytearray.db_number
        if self.area == Areas.DB:
            bytearray_ = client.db_read(db_nr, self.db_offset, self.row_size)
        else:
            bytearray_ = client.read_area(self.area, 0, self.db_offset, self.row_size)

        data = self.get_bytearray()
        # replace data in bytearray
        for i, b in enumerate(bytearray_):
            data[i + self.db_offset] = b
