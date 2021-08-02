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
from snap7.common import ADict
import struct
import logging
import re
from datetime import date, timedelta, datetime
from collections import OrderedDict
from typing import Dict, Optional, Union
from snap7.types import Areas
from snap7.client import Client
from snap7.exceptions import Snap7Exception
import time

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


def get_byte(bytearray_: bytearray, byte_index: int) -> int:
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


def get_word(bytearray_: bytearray, byte_index: int) -> int:
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


def set_string(bytearray_: bytearray, byte_index: int, value: str, max_size: int):
    """Set string value

    Args:
        bytearray_: buffer to write to.
        byte_index: byte index to start writing from.
        value: string to write.
        max_size: maximum possible string size.

    Raises:
        :obj:`TypeError`: if the `value` is not a :obj:`str`.
        :obj:`ValueError`: if the length of the  `value` is larger than the `max_size`.

    Examples:
        >>> data = bytearray(20)
        >>> snap7.util.set_string(data, 0, "hello world", 255)
        >>> data
            bytearray(b'\\x00\\x0bhello world\\x00\\x00\\x00\\x00\\x00\\x00\\x00')
    """
    if not isinstance(value, str):
        raise TypeError(f"Value value:{value} is not from Type string")

    size = len(value)
    # FAIL HARD WHEN trying to write too much data into PLC
    if size > max_size:
        raise ValueError(f'size {size} > max_size {max_size} {value}')
    # set len count on first position
    bytearray_[byte_index + 1] = len(value)

    i = 0
    # fill array which chr integers
    for i, c in enumerate(value):
        bytearray_[byte_index + 2 + i] = ord(c)

    # fill the rest with empty space
    for r in range(i + 1, bytearray_[byte_index]):
        bytearray_[byte_index + 2 + r] = ord(' ')


def get_string(bytearray_: bytearray, byte_index: int, max_size: int) -> str:
    """Parse string from bytearray

    Notes:
        The first byte of the buffer will contain the max size posible for a string.
        The second byte contains the length of the string that contains.

    Args:
        bytearray_: buffer from where to get the string.
        byte_index: byte index from where to start reading.
        max_size: maximum possible string size.

    Returns:
        String value.

    Examples:
        >>> data = bytearray([254, len("hello world")] + [ord(letter) for letter in "hello world"])
        >>> snap7.util.get_string(data, 0, 255)
        'hello world'
    """
    size = bytearray_[byte_index + 1]

    if max_size < size:
        logger.error("the string is too big for the size encountered in specification")
        logger.error("WRONG SIZED STRING ENCOUNTERED")
        size = max_size

    data = map(chr, bytearray_[byte_index + 2:byte_index + 2 + size])
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
    # 1990 - 1999, 2000 - 2089
    micro_to_milli = 1000
    data_bytearray = bytearray_[byte_index:byte_index + 8]
    dt_lst = list(data_bytearray.hex())
    date_time_list = []
    for i in range(0, len(dt_lst), 2):
        # last two bytearrays are the miliseconds and workday, they must be parsed together
        if i != len(dt_lst) - 4:
            if i == 0 and dt_lst[i] == '9':
                date_time_list.append(int('19' + dt_lst[i] + dt_lst[i + 1]))
            elif i == 0 and dt_lst[i] != '9':
                date_time_list.append(int('20' + dt_lst[i] + dt_lst[i + 1]))
            else:
                date_time_list.append(int(dt_lst[i] + dt_lst[i + 1]))
        else:
            date_time_list.append(int(dt_lst[i] + dt_lst[i + 1] + dt_lst[i + 2]))
            break
    date_and_time = datetime(
        date_time_list[0],
        date_time_list[1],
        date_time_list[2],
        date_time_list[3],
        date_time_list[4],
        date_time_list[5],
        date_time_list[6] * micro_to_milli).isoformat(timespec='microseconds')
    return date_and_time


def set_usint(bytearray_: bytearray, byte_index: int, _int: int) -> bytearray:
    """set unsigned small int

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

    Attributes:
        bytearray_: buffer data from the PLC.
        specification: layout of the DB Rows.
        row_size: bytes size of a db row.
        layout_offset: at which byte in the row specificaion we
            start reading the data.
        db_offset: at which byte in the db starts reading.

    Examples:
        >>> db1[0]['testbool1'] = test
        >>> db1.write()   # puts data in plc
    """
    bytearray_: Optional[bytearray] = None  # data from plc
    specification: Optional[str] = None  # layout of db rows
    row_size: Optional[int] = None  # bytes size of a db row
    layout_offset: Optional[int] = None  # at which byte in row specification should
    # we start reading the data
    db_offset: Optional[int] = None  # at which byte in db should we start reading?

    # first fields could be be status data.
    # and only the last part could be control data
    # now you can be sure you will never overwrite
    # critical parts of db

    def __init__(self, db_number: int, bytearray_: bytearray,
                 specification: str, row_size: int, size: int, id_field: Optional[str] = None,
                 db_offset: Optional[int] = 0, layout_offset: Optional[int] = 0, row_offset: Optional[int] = 0, area: Optional[Areas] = Areas.DB):
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
        """ Make each row for the DB. """
        id_field = self.id_field
        row_size = self.row_size
        specification = self.specification
        layout_offset = self.layout_offset

        for i in range(self.size):
            # calculate where row in bytearray starts
            db_offset = i * row_size + self.db_offset
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
        return self.index.get(key, default)

    def __iter__(self):
        for key, row in self.index.items():
            yield key, row

    def __len__(self):
        return len(self.index)

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
        data = {}
        for key in self._specification:
            data[key] = self[key]
        return data

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
        if self.get_bytearray() == bytearray_:
            return True
        return False

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
            :obj:`Snap7Exception`: if reading a `string` when checking the lenght of the string.
            :obj:`ValueError`: if the `type_` is not handled.

        Returns:
            Value read according to the `type_`
        """

        bytearray_ = self.get_bytearray()

        if type_ == 'BOOL':
            byte_index, bool_index = str(byte_index).split('.')
            return get_bool(bytearray_, self.get_offset(byte_index),
                            int(bool_index))

        # remove 4 from byte index since
        # first 4 bytes are used by db
        byte_index = self.get_offset(byte_index)

        if type_.startswith('STRING'):
            max_size = re.search(r'\d+', type_)
            if max_size is None:
                raise Snap7Exception("Max size could not be determinate. re.search() returned None")
            max_size_grouped = max_size.group(0)
            max_size_int = int(max_size_grouped)
            return get_string(bytearray_, byte_index, max_size_int)

        elif type_ == 'REAL':
            return get_real(bytearray_, byte_index)

        elif type_ == 'DWORD':
            return get_dword(bytearray_, byte_index)

        elif type_ == 'DINT':
            return get_dint(bytearray_, byte_index)

        elif type_ == 'INT':
            return get_int(bytearray_, byte_index)

        elif type_ == 'WORD':
            return get_word(bytearray_, byte_index)

        elif type_ == 'S5TIME':
            data_s5time = get_s5time(bytearray_, byte_index)
            return data_s5time

        elif type_ == 'DATE_AND_TIME':
            data_dt = get_dt(bytearray_, byte_index)
            return data_dt

        elif type_ == 'USINT':
            return get_usint(bytearray_, byte_index)

        elif type_ == 'SINT':
            return get_sint(bytearray_, byte_index)

        # add these three not implemented data typ to avoid
        # 'Unable to get repr for class<snap7.util.DB_ROW>' error
        elif type_ == 'TIME':
            return 'read TIME not implemented'

        elif type_ == 'DATE':
            return 'read DATE not implemented'

        elif type_ == 'TIME_OF_DAY':
            return 'read TIME_OF_DAY not implemented'

        raise ValueError

    def set_value(self, byte_index: Union[str, int], type: str, value: Union[bool, str, int, float]) -> Union[bytearray, None]:
        """Sets the value for a specific type in the specified byte index.

        Args:
            byte_index: byte index to start writing to.
            type: type of value to write.
            value: value to write.

        Raises:
            :obj:`Snap7Exception`: if reading a `string` when checking the lenght of the string.
            :obj:`ValueError`: if the `type_` is not handled.

        Returns:
            Buffer data with the value written. Optional.
        """
        bytearray_ = self.get_bytearray()

        if type == 'BOOL' and isinstance(value, bool):
            byte_index, bool_index = str(byte_index).split(".")
            return set_bool(bytearray_, self.get_offset(byte_index),
                            int(bool_index), value)

        byte_index = self.get_offset(byte_index)

        if type.startswith('STRING') and isinstance(value, str):
            max_size = re.search(r'\d+', type)
            if max_size is None:
                raise Snap7Exception("Max size could not be determinate. re.search() returned None")
            max_size_grouped = max_size.group(0)
            max_size_int = int(max_size_grouped)
            return set_string(bytearray_, byte_index, value, max_size_int)

        elif type == 'REAL':
            return set_real(bytearray_, byte_index, value)

        elif type == 'DWORD' and isinstance(value, int):
            return set_dword(bytearray_, byte_index, value)

        elif type == 'DINT' and isinstance(value, int):
            return set_dint(bytearray_, byte_index, value)

        elif type == 'INT' and isinstance(value, int):
            return set_int(bytearray_, byte_index, value)

        elif type == 'WORD' and isinstance(value, int):
            return set_word(bytearray_, byte_index, value)

        elif type == 'USINT' and isinstance(value, int):
            return set_usint(bytearray_, byte_index, value)

        elif type == 'SINT' and isinstance(value, int):
            return set_sint(bytearray_, byte_index, value)

        if type == 'USINT' and isinstance(value, int):
            return set_usint(bytearray_, byte_index, value)

        if type == 'SINT' and isinstance(value, int):
            return set_sint(bytearray_, byte_index, value)

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
            bytearray_ = client.read_area(self.area, 0, 0, self.row_size)

        data = self.get_bytearray()
        # replace data in bytearray
        for i, b in enumerate(bytearray_):
            data[i + self.db_offset] = b
