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

    12.0          test_bool1      BOOL
    12.1          test_bool2      BOOL
    12.2          test_bool3      BOOL
    12.3          test_bool4      BOOL
    12.4          test_bool5      BOOL
    12.5          test_bool6      BOOL
    12.6          test_bool7      BOOL
    12.7          test_bool8      BOOL
    13            testReal       REAL
    17            testDword      DWORD
    \"\"\"

    client = snap7.client.Client()
    client.connect('192.168.200.24', 0, 3)

    # this looks confusing but this means uploading from the PLC to YOU
    # so downloading in the PC world :)

    all_data = client.upload(db_number)

    simple:

    from snap7 import DB
    db1 = DB(
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
                                # reading. This could be that the specification
                                # does not start at 0
    )

    Now we can use db1 in python as a dict. if 'ID' contains
    the 'test' we can identify the 'test' row in the all_data bytearray

    To test of you layout matches the data from the plc you can
    just print db1[0] or db['test'] in the example

    db1['test']['test_bool1'] = 0

    If we do not specify an id_field this should work to read out the
    same data.

    db1[0]['test_bool1']

    to read and write a single Row from the plc. takes like 5ms!

    db1['test'].write()

    db1['test'].read(client)


"""

import re
from logging import getLogger
from datetime import datetime, date
from typing import Any, Optional, Union, Iterator, Tuple, Dict, Callable

from snap7 import Client
from snap7.type import Area, ValueType

from snap7.util import (
    set_bool,
    set_fstring,
    set_string,
    set_real,
    set_dword,
    set_udint,
    set_dint,
    set_uint,
    set_int,
    set_word,
    set_byte,
    set_usint,
    set_sint,
    set_time,
    set_lreal,
    set_date,
    get_bool,
    get_fstring,
    get_string,
    get_wstring,
    get_real,
    get_dword,
    get_udint,
    get_dint,
    get_uint,
    get_int,
    get_word,
    get_byte,
    get_s5time,
    get_dt,
    get_usint,
    get_sint,
    get_time,
    get_date,
    get_tod,
    get_lreal,
    get_char,
    get_wchar,
    get_dtl,
)

logger = getLogger(__name__)


def parse_specification(db_specification: str) -> Dict[str, Any]:
    """Create a db specification derived from a
        dataview of a db in which the byte layout
        is specified

    Args:
        db_specification: string formatted table with the indexes, aliases and types.

    Returns:
        Parsed DB specification.
    """
    parsed_db_specification = {}

    for line in db_specification.split("\n"):
        if line and not line.lstrip().startswith("#"):
            index, var_name, _type = line.lstrip().split("#")[0].split()
            parsed_db_specification[var_name] = (index, _type)

    return parsed_db_specification


def print_row(data: bytearray) -> None:
    """print a single db row in chr and str"""
    index_line = ""
    pri_line1 = ""
    chr_line2 = ""
    matcher = re.compile("[a-zA-Z0-9 ]")

    for i, xi in enumerate(data):
        # index
        if not i % 5:
            diff = len(pri_line1) - len(index_line)
            index_line += diff * " "
            index_line += str(i)
            # i = i + (ws - len(i)) * ' ' + ','

        # byte array line
        str_v = str(xi)
        pri_line1 += str(xi) + ","
        # char line
        c = chr(xi)
        c = c if matcher.match(c) else " "
        # align white space
        w = len(str_v)
        c = c + (w - 1) * " " + ","
        chr_line2 += c

    print(index_line)
    print(pri_line1)
    print(chr_line2)


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
        >>> db = DB()
        >>> db[0]['test_bool1'] = "test"
        >>> db.write(Client())   # puts data in plc
    """

    bytearray_: Optional[bytearray] = None  # data from plc
    specification: str  # layout of db rows
    id_field: Optional[str] = None  # ID field of the rows
    row_size: int = 0  # bytes size of a db row
    layout_offset: int = 0  # at which byte in row specification should
    db_offset: int = 0  # at which byte in db should we start reading?

    # first fields could be status data.
    # and only the last part could be control data
    # now you can be sure you will never overwrite
    # critical parts of db

    def __init__(
        self,
        db_number: int,
        bytearray_: bytearray,
        specification: str,
        row_size: int,
        size: int,
        id_field: Optional[str] = None,
        db_offset: int = 0,
        layout_offset: int = 0,
        row_offset: int = 0,
        area: Area = Area.DB,
    ):
        """Creates a new instance of the `Row` class.

        Args:
            db_number: number of the DB to read from. This value should be 0 if area!=Areas.DB.
            bytearray_: initial buffer read from the PLC.
            specification: layout of the PLC memory.
            row_size: bytes size of a db row.
            size: length of the memory area.
            id_field: name to reference the row. Optional.
            db_offset: at which byte in the db starts reading.
            layout_offset: at which byte in the row specification we
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
        self.index: Dict[str, Row] = {}
        self.make_rows()

    def make_rows(self) -> None:
        """Make each row for the DB."""
        id_field = self.id_field
        row_size = self.row_size
        specification = self.specification
        layout_offset = self.layout_offset
        row_offset = self.row_offset

        for i in range(self.size):
            # calculate where row in bytearray starts
            db_offset = i * (row_size + row_offset) + self.db_offset
            # create a row object
            row = Row(
                self,
                specification,
                row_size=row_size,
                db_offset=db_offset,
                layout_offset=layout_offset,
                row_offset=self.row_offset,
                area=self.area,
            )

            # store row object
            key = row[id_field] if id_field else i
            if key and key in self.index:
                msg = f"{key} not unique!"
                logger.error(msg)
            self.index[key] = row

    def __getitem__(self, key: str, default: Optional[None] = None) -> Union[None, "Row"]:
        """Access a row of the table through its index.

        Rows (values) are of type :class:`DB_Row`.

        Notes:
            This method has the same semantics as :class:`dict` access.
        """
        return self.index.get(key, default)

    def __iter__(self) -> Iterator[Tuple[str, Any]]:
        """Iterate over the items contained in the table, in the physical order they are contained
        in memory.

        Notes:
            This method does not have the same semantics as :class:`dict` iteration. Instead, it
            has the same semantics as the :func:`~DB.items` method, yielding ``(index, row)``
            tuples.
        """
        yield from self.index.items()

    def __len__(self) -> int:
        """Return the number of rows contained in the DB.

        Notes:
            If more than one row has the same index value, it is only counted once.
        """
        return len(self.index)

    def __contains__(self, key: str) -> bool:
        """Return whether the given key is the index of a row in the DB."""
        return key in self.index

    def keys(self) -> Iterator[str]:
        """Return a *view object* of the keys that are used as indices for the rows in the
        DB.
        """
        yield from self.index.keys()

    def items(self) -> Iterator[Tuple[str, Any]]:
        """Return a *view object* of the items (``(index, row)`` pairs) that are used as indices
        for the rows in the DB.
        """
        yield from self.index.items()

    def export(self) -> Dict[str, Any]:
        """Export the object to a dict, where each item in the dictionary
        has an index as the key, and the value of the DB row associated with that index
        as a value, represented itself as a :class:`dict` (as returned by :func:`DB_Row.export`).

        The outer dictionary contains the rows in the physical order they are contained in
        memory.

        Notes:
            This function effectively returns a snapshot of the DB.
        """
        ret = {}
        for k, v in self.items():
            ret[k] = v.export()
        return ret

    def set_data(self, bytearray_: bytearray) -> None:
        """Set the new buffer data from the PLC to the current instance.

        Args:
            bytearray_: buffer to save.

        Raises:
            :obj:`TypeError`: if `bytearray_` is not an instance of :obj:`bytearray`
        """
        if not isinstance(bytearray_, bytearray):
            raise TypeError(f"Value bytearray_: {bytearray_} is not from type bytearray")
        self._bytearray = bytearray_

    def read(self, client: Client) -> None:
        """Reads all the rows from the PLC to the :obj:`bytearray` of this instance.

        Args:
            client: :obj:`Client` snap7 instance.

        Raises:
            :obj:`ValueError`: if the `row_size` is less than 0.
        """
        if self.row_size < 0:
            raise ValueError("row_size must be greater equal zero.")

        total_size = self.size * (self.row_size + self.row_offset)
        if self.area == Area.DB:  # note: is it worth using the upload method?
            bytearray_ = client.db_read(self.db_number, self.db_offset, total_size)
        else:
            bytearray_ = client.read_area(self.area, 0, self.db_offset, total_size)

        # replace data in bytearray
        for i, b in enumerate(bytearray_):
            self._bytearray[i + self.db_offset] = b

        self.index.clear()
        self.make_rows()

    def write(self, client: Client) -> None:
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
        data = self._bytearray[self.db_offset : self.db_offset + total_size]

        if self.area == Area.DB:
            client.db_write(self.db_number, self.db_offset, data)
        else:
            client.write_area(self.area, 0, self.db_offset, data)

    def get_bytearray(self) -> bytearray:
        return self._bytearray


class Row:
    """
    Provide ROW API for DB bytearray

    Attributes:
        bytearray_: reference to the data of the parent DB.
        _specification: row specification layout.
    """

    bytearray_: bytearray  # data of reference to parent DB
    _specification: Dict[str, Any] = {}  # row specification

    def __init__(
        self,
        bytearray_: Union[bytearray, "DB"],
        _specification: str,
        row_size: int = 0,
        db_offset: int = 0,
        layout_offset: int = 0,
        row_offset: Optional[int] = 0,
        area: Area = Area.DB,
    ):
        """Creates a new instance of the `DB_Row` class.

        Args:
            bytearray_: reference to the data of the parent DB.
            _specification: row specification layout.
            row_size: Amount of bytes of the row.
            db_offset: at which byte in the db starts reading.
            layout_offset: at which byte in the row specification we
                start reading the data.
            row_offset: offset between rows.
            area: which memory area this row is representing.

        Raises:
            :obj:`TypeError`: if `bytearray_` is not an instance of :obj:`bytearray` or :obj:`DB`.
        """

        self.db_offset = db_offset  # start point of row data in db
        self.layout_offset = layout_offset  # start point of row data in layout
        self.row_size = row_size  # length of the read
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
            return self._bytearray.get_bytearray()
        return self._bytearray

    def export(self) -> Dict[str, Union[str, int, float, bool, datetime]]:
        """Export dictionary with values

        Returns:
            dictionary containing the values of each value of the row.
        """
        return {key: self[key] for key in self._specification}

    def __getitem__(self, key: str) -> Any:
        """
        Get a specific db field
        """
        index, _type = self._specification[key]
        return self.get_value(index, _type)

    def __setitem__(self, key: str, value: Any) -> None:
        index, _type = self._specification[key]
        self.set_value(index, _type, value)

    def __repr__(self) -> str:
        string = ""
        for var_name, (index, _type) in self._specification.items():
            string = f"{string}\n{var_name:<20} {self.get_value(index, _type)!r:<10}"
        return string

    def unchanged(self, bytearray_: bytearray) -> bool:
        """Checks if the bytearray is the same

        Args:
            bytearray_: buffer of data to check.

        Returns:
            True if the current `bytearray_` is equal to the new one. Otherwise, this is False.
        """
        return self.get_bytearray() == bytearray_

    def get_offset(self, byte_index: Union[str, int]) -> int:
        """Calculate correct beginning position for a row
            the db_offset = row_size * index

        Args:
            byte_index: byte index from where to start reading from.

        Returns:
            Amount of bytes to ignore.
        """
        # add float typ to avoid error because of
        # the variable address with decimal point(like 0.0 or 4.0)
        return int(float(byte_index)) - self.layout_offset + self.db_offset

    def get_value(self, byte_index: Union[str, int], type_: str) -> ValueType:
        """Gets the value for a specific type.

        Args:
            byte_index: byte index from where start reading.
            type_: type of data to read.

        Raises:
            :obj:`ValueError`: if reading a `string` when checking the length of the string.
            :obj:`ValueError`: if the `type_` is not handled.

        Returns:
            Value read according to the `type_`
        """
        bytearray_ = self.get_bytearray()

        # set parsing non case-sensitive
        type_ = type_.upper()

        if type_ == "BOOL":
            byte_index, bool_index = str(byte_index).split(".")
            return get_bool(bytearray_, self.get_offset(byte_index), int(bool_index))

        # remove 4 from byte index since
        # first 4 bytes are used by db
        byte_index = self.get_offset(byte_index)

        if type_.startswith("FSTRING"):
            max_size = re.search(r"\d+", type_)
            if max_size is None:
                raise ValueError("Max size could not be determinate. re.search() returned None")
            return get_fstring(bytearray_, byte_index, int(max_size[0]))
        elif type_.startswith("STRING"):
            max_size = re.search(r"\d+", type_)
            if max_size is None:
                raise ValueError("Max size could not be determinate. re.search() returned None")
            return get_string(bytearray_, byte_index)
        elif type_.startswith("WSTRING"):
            max_size = re.search(r"\d+", type_)
            if max_size is None:
                raise ValueError("Max size could not be determinate. re.search() returned None")
            return get_wstring(bytearray_, byte_index)
        else:
            type_to_func: Dict[str, Callable[[bytearray, int], ValueType]] = {
                "REAL": get_real,
                "DWORD": get_dword,
                "UDINT": get_udint,
                "DINT": get_dint,
                "UINT": get_uint,
                "INT": get_int,
                "WORD": get_word,
                "BYTE": get_byte,
                "S5TIME": get_s5time,
                "DATE_AND_TIME": get_dt,
                "USINT": get_usint,
                "SINT": get_sint,
                "TIME": get_time,
                "DATE": get_date,
                "TIME_OF_DAY": get_tod,
                "LREAL": get_lreal,
                "TOD": get_tod,
                "CHAR": get_char,
                "WCHAR": get_wchar,
                "DTL": get_dtl,
            }
            if type_ in type_to_func:
                return type_to_func[type_](bytearray_, byte_index)
        raise ValueError

    def set_value(self, byte_index: Union[str, int], type_: str, value: Union[bool, str, float]) -> Optional[bytearray]:
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

        if type_ == "BOOL" and isinstance(value, bool):
            byte_index, bool_index = str(byte_index).split(".")
            return set_bool(bytearray_, self.get_offset(byte_index), int(bool_index), value)

        byte_index = self.get_offset(byte_index)

        if type_.startswith("FSTRING") and isinstance(value, str):
            max_size = re.search(r"\d+", type_)
            if max_size is None:
                raise ValueError("Max size could not be determinate. re.search() returned None")
            max_size_grouped = max_size.group(0)
            max_size_int = int(max_size_grouped)
            set_fstring(bytearray_, byte_index, value, max_size_int)
            return None

        if type_.startswith("STRING") and isinstance(value, str):
            max_size = re.search(r"\d+", type_)
            if max_size is None:
                raise ValueError("Max size could not be determinate. re.search() returned None")
            max_size_grouped = max_size.group(0)
            max_size_int = int(max_size_grouped)
            set_string(bytearray_, byte_index, value, max_size_int)
            return None

        if type_ == "REAL":
            return set_real(bytearray_, byte_index, value)

        if type_ == "LREAL" and isinstance(value, float):
            return set_lreal(bytearray_, byte_index, value)

        if isinstance(value, int):
            type_to_func = {
                "DWORD": set_dword,
                "UDINT": set_udint,
                "DINT": set_dint,
                "UINT": set_uint,
                "INT": set_int,
                "WORD": set_word,
                "BYTE": set_byte,
                "USINT": set_usint,
                "SINT": set_sint,
            }
            if type_ in type_to_func:
                return type_to_func[type_](bytearray_, byte_index, value)

        if type_ == "TIME" and isinstance(value, str):
            return set_time(bytearray_, byte_index, value)

        if type_ == "DATE" and isinstance(value, date):
            return set_date(bytearray_, byte_index, value)

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
        data = self.get_bytearray()[offset : offset + self.row_size]
        db_offset = self.db_offset

        # indicate start of write only area of row!
        if self.row_offset:
            data = data[self.row_offset :]
            db_offset += self.row_offset

        if self.area == Area.DB:
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
        if self.area == Area.DB:
            bytearray_ = client.db_read(db_nr, self.db_offset, self.row_size)
        else:
            bytearray_ = client.read_area(self.area, 0, self.db_offset, self.row_size)

        data = self.get_bytearray()
        # replace data in bytearray
        for i, b in enumerate(bytearray_):
            data[i + self.db_offset] = b


# backwards compatible alias
DB_Row = Row
