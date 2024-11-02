import struct
from datetime import timedelta, datetime, date
from typing import NoReturn
from logging import getLogger

logger = getLogger(__name__)


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
    data = bytearray_[byte_index : byte_index + 1]
    data[0] = data[0] & 0xFF
    packed = struct.pack("B", *data)
    value: bytes = struct.unpack("B", packed)[0]
    return value


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
        >>> get_word(bytearray([0, 100]), 0)
            100
    """
    data = bytearray_[byte_index : byte_index + 2]
    data[1] = data[1] & 0xFF
    data[0] = data[0] & 0xFF
    packed = struct.pack("2B", *data)
    value: bytearray = struct.unpack(">H", packed)[0]
    return value


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
        >>> get_int(bytearray([0, 255]), 0)
            255
    """
    data = bytearray_[byte_index : byte_index + 2]
    data[1] = data[1] & 0xFF
    data[0] = data[0] & 0xFF
    packed = struct.pack("2B", *data)
    value: int = struct.unpack(">h", packed)[0]
    return value


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
        >>> get_uint(data, 0)
            65535
    """
    return int(get_word(bytearray_, byte_index))


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
        >>> get_real(data, 0)
            123.32099914550781
    """
    x = bytearray_[byte_index : byte_index + 4]
    real: float = struct.unpack(">f", struct.pack("4B", *x))[0]
    return real


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
        >>> get_fstring(data, 0, 15)
        'hello world'
        >>> get_fstring(data, 0, 15, remove_padding=False)
        'hello world    '
    """
    data = map(chr, bytearray_[byte_index : byte_index + max_length])
    string = "".join(data)

    if remove_padding:
        return string.rstrip(" ")
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
        >>> data = bytearray([254, len("hello world")] + [ord(l) for letter in "hello world"])
        >>> get_string(data, 0)
        'hello world'
    """

    str_length = int(bytearray_[byte_index + 1])
    max_string_size = int(bytearray_[byte_index])

    if str_length > max_string_size or max_string_size > 254:
        logger.error("The string is too big for the size encountered in specification")
        logger.error("WRONG SIZED STRING ENCOUNTERED")
        raise TypeError(
            "String contains {str_length} chars, but max. {max_string_size} chars are expected or is "
            "larger than 254. Bytearray doesn't seem to be a valid string."
        )
    data = map(chr, bytearray_[byte_index + 2 : byte_index + 2 + str_length])
    return "".join(data)


def get_dword(bytearray_: bytearray, byte_index: int) -> int:
    """Gets the dword from the buffer.

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
        >>> get_dword(data, 0)
            4294967295
    """
    data = bytearray_[byte_index : byte_index + 4]
    dword: int = struct.unpack(">I", struct.pack("4B", *data))[0]
    return dword


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
        >>> get_dint(data, 0)
            2147483647
    """
    data = bytearray_[byte_index : byte_index + 4]
    dint: int = struct.unpack(">i", struct.pack("4B", *data))[0]
    return dint


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
        >>> get_udint(data, 0)
            4294967295
    """
    data = bytearray_[byte_index : byte_index + 4]
    dint: int = struct.unpack(">I", struct.pack("4B", *data))[0]
    return dint


def get_s5time(bytearray_: bytearray, byte_index: int) -> str:
    micro_to_milli = 1000
    data_bytearray = bytearray_[byte_index : byte_index + 2]
    s5time_data_int_like = list(data_bytearray.hex())
    if s5time_data_int_like[0] == "0":
        # 10ms
        time_base = 10
    elif s5time_data_int_like[0] == "1":
        # 100ms
        time_base = 100
    elif s5time_data_int_like[0] == "2":
        # 1s
        time_base = 1000
    elif s5time_data_int_like[0] == "3":
        # 10s
        time_base = 10000
    else:
        raise ValueError("This value should not be greater than 3")

    s5time_bcd = int(s5time_data_int_like[1]) * 100 + int(s5time_data_int_like[2]) * 10 + int(s5time_data_int_like[3])
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
    return get_date_time_object(bytearray_, byte_index).isoformat(timespec="microseconds")


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
    microsec = (bcd_to_byte(bytearray_[byte_index + 6]) * 10 + bcd_to_byte(bytearray_[byte_index + 7] >> 4)) * 1000

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
        >>> get_time(data, 0)
            '24:20:31:23:647'
    """
    data_bytearray = bytearray_[byte_index : byte_index + 4]
    bits = 32
    sign = 1
    byte_str = data_bytearray.hex()
    val = int(byte_str, 16)
    if (val & (1 << (bits - 1))) != 0:
        sign = -1  # if sign bit is set e.g., 8bit: 128-255
        val -= 1 << bits  # compute negative value
        val *= sign

    milli_seconds = val % 1000
    seconds = val // 1000
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24

    sign_str = "" if sign >= 0 else "-"
    time_str = f"{sign_str}{days!s}:{hours % 24!s}:{minutes % 60!s}:{seconds % 60!s}.{milli_seconds!s}"

    return time_str


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
        >>> get_usint(data, 0)
            255
    """
    data = bytearray_[byte_index] & 0xFF
    packed = struct.pack("B", data)
    value: int = struct.unpack(">B", packed)[0]
    return value


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
        >>> get_sint(data, 0)
            127
    """
    data = bytearray_[byte_index]
    packed = struct.pack("B", data)
    value: int = struct.unpack(">b", packed)[0]
    return value


def get_lint(bytearray_: bytearray, byte_index: int) -> int:
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
        >>> from snap7 import Client
        >>> data = Client().db_read(db_number=1, start=10, size=8)
        >>> get_lint(data, 0)
            12345
    """

    raw_lint = bytearray_[byte_index : byte_index + 8]
    lint = struct.unpack(">q", struct.pack("8B", *raw_lint))[0]
    return int(lint)


def get_lreal(bytearray_: bytearray, byte_index: int) -> float:
    """Get the long real

    Datatype `lreal` (long real) consists in 8 bytes in the PLC.
    Negative Range: -1.7976931348623158e+308 to -2.2250738585072014e-308
    Positive Range: +2.2250738585072014e-308 to +1.7976931348623158e+308
    Zero: ±0

    Args:
        bytearray_: buffer to read from.
        byte_index: byte index from where to start reading.

    Returns:
        The real value.

    Examples:
        read lreal value (here as example 12345.12345) from DB1.10 of a PLC
        >>> from snap7 import Client
        >>> data = Client().db_read(db_number=1, start=10, size=8)
        >>> get_lreal(data, 0)
        12345.12345
    """
    return float(struct.unpack_from(">d", bytearray_, offset=byte_index)[0])


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
        >>> from snap7 import Client
        >>> data = Client().db_read(db_number=1, start=10, size=8)
        >>> get_lword(data, 0)
            bytearray(b"\\x00\\x00\\x00\\x00\\x00\\x00\\xAB\\xCD")
    """
    data = bytearray_[byte_index : byte_index + 4]
    dword = struct.unpack(">Q", struct.pack("8B", *data))[0]
    return bytearray(dword)


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
        >>> from snap7 import Client
        >>> data = Client().db_read(db_number=1, start=10, size=8)
        >>> get_ulint(data, 0)
            12345
    """
    raw_ulint = bytearray_[byte_index : byte_index + 8]
    lint: int = struct.unpack(">Q", struct.pack("8B", *raw_ulint))[0]
    return lint


def get_tod(bytearray_: bytearray, byte_index: int) -> timedelta:
    len_bytearray_ = len(bytearray_)
    byte_range = byte_index + 4
    if len_bytearray_ < byte_range:
        raise ValueError("Date can't be extracted from bytearray. bytearray_[Index:Index+16] would cause overflow.")
    time_val = timedelta(milliseconds=int.from_bytes(bytearray_[byte_index:byte_range], byteorder="big"))
    if time_val.days >= 1:
        raise ValueError("Time_Of_Date can't be extracted from bytearray. Bytearray contains unexpected values.")
    return time_val


def get_date(bytearray_: bytearray, byte_index: int = 0) -> date:
    len_bytearray_ = len(bytearray_)
    byte_range = byte_index + 2
    if len_bytearray_ < byte_range:
        raise ValueError("Date can't be extracted from bytearray. bytearray_[Index:Index+16] would cause overflow.")
    date_val = date(1990, 1, 1) + timedelta(days=int.from_bytes(bytearray_[byte_index:byte_range], byteorder="big"))
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
        year=int.from_bytes(bytearray_[byte_index : byte_index + 2], byteorder="big"),
        month=int(bytearray_[byte_index + 2]),
        day=int(bytearray_[byte_index + 3]),
        hour=int(bytearray_[byte_index + 5]),
        minute=int(bytearray_[byte_index + 6]),
        second=int(bytearray_[byte_index + 7]),
        microsecond=int(bytearray_[byte_index + 8]),
    )  # --- ? noch nicht genau genug
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
        >>> from snap7 import Client
        >>> data = Client().db_read(db_number=1, start=10, size=1)
        >>> get_char(data, 0)
        'C'
    """
    char = chr(bytearray_[byte_index])
    return char


def get_wchar(bytearray_: bytearray, byte_index: int) -> str:
    """Get wchar value from bytearray.

    Datatype `wchar` in the PLC is represented in 2 bytes. It has to be in utf-16-be format.

    Args:
        bytearray_: buffer to read from.
        byte_index: byte index to start reading from.

    Returns:
        Value read.

    Examples:
        Read 2 Bytes raw from DB1.10, where a wchar value is stored. Return Python compatible value.
        >>> from snap7 import Client
        >>> data = Client().db_read(db_number=1, start=10, size=2)
        >>> get_wchar(data, 0)
        'C'
    """
    if bytearray_[byte_index] == 0:
        return chr(bytearray_[1])
    return bytearray_[byte_index : byte_index + 2].decode("utf-16-be")


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
        >>> from snap7 import Client
        >>> data = Client().db_read(db_number=1, start=10, size=22)
        >>> get_wstring(data, 0)
        'hello world'
    """
    # Byte 0 + 1 --> total length of wstring, should be bytearray_ - 4
    # Byte 2, 3 --> used length of wstring
    wstring_start = byte_index + 4

    max_wstring_size = bytearray_[byte_index : byte_index + 2]
    packed = struct.pack("2B", *max_wstring_size)
    max_wstring_symbols = struct.unpack(">H", packed)[0] * 2

    wstr_length_raw = bytearray_[byte_index + 2 : byte_index + 4]
    wstr_symbols_amount = struct.unpack(">H", struct.pack("2B", *wstr_length_raw))[0] * 2

    if wstr_symbols_amount > max_wstring_symbols or max_wstring_symbols > 16382:
        logger.error("The wstring is too big for the size encountered in specification")
        logger.error("WRONG SIZED STRING ENCOUNTERED")
        raise TypeError(
            f"WString contains {wstr_symbols_amount} chars, but max {max_wstring_symbols} chars are "
            f"expected or is larger than 16382. Bytearray doesn't seem to be a valid string."
        )

    return bytearray_[wstring_start : wstring_start + wstr_symbols_amount].decode("utf-16-be")


def get_array(bytearray_: bytearray, byte_index: int) -> NoReturn:
    raise NotImplementedError
