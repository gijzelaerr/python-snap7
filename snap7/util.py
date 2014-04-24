"""
Utility functions to work with DB objects

example:

see test code test_s7util

"""

from collections import OrderedDict
import struct
import logging


def parse_specification(db_specification):
    """
    create a db specification derived from a
    dataview of a db in which the byte layout
    is specified
    """
    parsed_db_specification = OrderedDict()
    for line in db_specification.split('\n'):
        if line and not line.startswith('#'):
            row = line.split('#')[0]  # remove trailing comment
            index, var_name, _type = row.split()
            parsed_db_specification[var_name] = (index, _type)

    return parsed_db_specification


def get_bool(_bytearray, byte_index, bool_index):
    """
    Get the boolean value from location in bytearray
    """
    index_value = 1 << bool_index
    byte_value = _bytearray[byte_index]
    current_value = byte_value & index_value
    return current_value == index_value


def set_bool(_bytearray, byte_index, bool_index, value):
    """
    Set boolean value on location in bytearray
    """
    assert value in [0, 1, True, False]
    current_value = get_bool(_bytearray, byte_index, bool_index)
    index_value = 1 << bool_index

    # check if bool already has correct value
    if current_value == value:
        return

    if value:
        # make sure index_v is IN current byte
        _bytearray[byte_index] += index_value
    else:
        # make sure index_v is NOT in current byte
        _bytearray[byte_index] -= index_value


def set_int(_bytearray, byte_index, _int):
    """
    Set value in bytearray to int
    """
    # make sure were dealing with an int
    _int = int(_int)
    # int needs two be two bytes.
    byte0 = _int >> 8
    byte1 = _int - (byte0 << 8)
    _bytearray[byte_index] = byte0
    _bytearray[byte_index + 1] = byte1


def get_int(_bytearray, byte_index):
    """
    Get int value from bytearray.

    int are represented in two bytes
    """
    byte1 = _bytearray[byte_index + 1]
    byte0 = _bytearray[byte_index]
    return byte1 + (byte0 << 8)


def set_real(_bytearray, byte_index, real):
    """
    Set Real value

    make 4 byte data from real

    """
    real = float(real)
    real = struct.pack('>f', real)
    _bytes = struct.unpack('4B', real)
    for i, b in enumerate(_bytes):
        _bytearray[byte_index + i] = b


def get_real(_bytearray, byte_index):
    """
    Get real value. create float from 4 bytes
    """
    x = _bytearray[byte_index:byte_index + 4]
    real = struct.unpack('>f', struct.pack('4B', *x))[0]
    return real


def set_string(_bytearray, byte_index, value):
    """
    Set string value

    :params value: string data
    :params size: total possible string size
    """
    assert isinstance(value, (str, unicode))
    # set len count
    _bytearray[byte_index + 1] = len(value)
    i = 0
    # fill array which chr integers
    for i, c in enumerate(value):
        _bytearray[byte_index + 2 + i] = ord(c)

    # fill the rest with empty space
    for r in range(i + 1, _bytearray[byte_index]):
        _bytearray[byte_index + 2 + r] = ord(' ')


def get_string(_bytearray, byte_index):
    """
    parse string from bytearray
    """
    size = _bytearray[byte_index + 1]
    data = map(chr, _bytearray[byte_index + 2:byte_index + 2 + size])
    return "".join(data)


def get_dword(_bytearray, byte_index):
    data = _bytearray[byte_index:byte_index + 4]
    dword = struct.unpack('I', struct.pack('4B', *data))[0]
    return dword


def set_dword(_bytearray, byte_index, dword):
    dword = int(dword)
    _bytes = struct.unpack('4B', struct.pack('I', dword))
    for i, b in enumerate(_bytes):
        _bytearray[byte_index + i] = b


class DB(object):
    """
    provide a simple API for a DB bytearray block given a row
    specification
    """
    _bytearray = None      # data from plc
    specification = None   # layout of db rows
    row_size = None        # bytes size of a db row
    layout_offset = None   # at which byte in row specification should
                           # we start reading the data
    db_offset = None       # at which byte in db should we start reading?
                           # first fields could be be status data.
                           # and only the last part could be control data
                           # now you can be sure you will never overwrite
                           # critical parts of db

    def __init__(self, db_number, _bytearray,
                 specification, row_size, size, id_field=None,
                 db_offset=0, layout_offset=0, row_offset=0):

        self.db_number = db_number
        self.size = size
        self.row_size = row_size
        self.id_field = id_field

        self.db_offset = db_offset
        self.layout_offset = layout_offset
        self.row_offset = row_offset

        self._bytearray = _bytearray
        self.specification = specification
        # loop over bytearray. make rowObjects
        # store index of id_field to row objects
        self.index = OrderedDict()
        self.make_rows()

    def make_rows(self):
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
                         row_offset=self.row_offset)

            # store row object
            key = row[id_field] if id_field else i
            if key and key in self.index:
                msg = '%s not unique!' % key
                logging.error(msg)
                print msg
            self.index[key] = row

    def __getitem__(self, key, default=None):
        return self.index.get(key, default)

    def __iter__(self):
        for key, row in self.index.items():
            yield key, row

    def __len__(self):
        return len(self.index)

    def set_data(self, _bytearray):
        assert(isinstance(_bytearray, bytearray))
        self._bytearray = _bytearray


class DB_Row(object):
    """
    Provide ROW API for DB bytearray
    """
    _bytearray = None      # data of reference to parent DB
    _specification = None  # row specification

    def __init__(self, _bytearray, _specification, row_size=0,
                 db_offset=0, layout_offset=0, row_offset=0):

        self.db_offset = db_offset          # start point of row data in db
        self.layout_offset = layout_offset  # start point of row data in layout
        self.row_size = row_size
        self.row_offset = row_offset        # start of writable part of row

        assert(isinstance(_bytearray, (bytearray, DB)))
        self._bytearray = _bytearray
        self._specification = parse_specification(_specification)

    def get_bytearray(self):
        """
        return bytearray from self or DB parent
        """
        if isinstance(self._bytearray, DB):
            return self._bytearray._bytearray
        return self._bytearray

    def export(self):
        """
        export dictionary with values
        """
        data = {}
        for key in self._specification:
            data[key] = self[key]
        return data

    def __getitem__(self, key):
        """
        Get a specific db field
        """
        assert key in self._specification
        index, _type = self._specification[key]
        return self.get_value(index, _type)

    def __setitem__(self, key, value):
        assert key in self._specification
        index, _type = self._specification[key]
        self.set_value(index, _type, value)

    def __repr__(self):

        string = ""
        for var_name, (index, _type) in self._specification.items():
            string = '%s\n%-20s %-10s' % (string, var_name,
                                          self.get_value(index, _type))
        return string

    def unchanged(self, _bytearray):
        if self.get_bytearray() == _bytearray:
            return True
        return False

    def get_offset(self, byte_index):
        """
        Calculate correct beginning position for a row
        the db_offset = row_size * index
        """
        return int(byte_index) - self.layout_offset + self.db_offset

    def get_value(self, byte_index, _type):
        _bytearray = self.get_bytearray()

        if _type == 'BOOL':
            byte_index, bool_index = byte_index.split('.')
            return get_bool(_bytearray, self.get_offset(byte_index),
                            int(bool_index))

        # remove 4 from byte index since
        # first 4 bytes are used by db
        byte_index = self.get_offset(byte_index)

        if _type.startswith('STRING'):
            return get_string(_bytearray, byte_index)

        if _type == 'REAL':
            return get_real(_bytearray, byte_index)

        if _type == 'DWORD':
            return get_dword(_bytearray, byte_index)

        if _type == 'INT':
            return get_int(_bytearray, byte_index)

        raise ValueError

    def set_value(self, byte_index, _type, value):
        _bytearray = self.get_bytearray()

        if _type == 'BOOL':
            byte_index, bool_index = byte_index.split('.')
            return set_bool(_bytearray, self.get_offset(byte_index),
                            int(bool_index), value)

        byte_index = self.get_offset(byte_index)

        if _type.startswith('STRING'):
            return set_string(_bytearray, byte_index, value)

        if _type == 'REAL':
            return set_real(_bytearray, byte_index, value)

        if _type == 'DWORD':
            return set_dword(_bytearray, byte_index, value)

        if _type == 'INT':
            return set_int(_bytearray, byte_index, value)

        raise ValueError

    def write(self, client):
        """
        Write current data to db in plc
        """
        assert(isinstance(self._bytearray, DB))
        assert(self.row_size >= 0)

        db_nr = self._bytearray.db_number
        offset = self.db_offset
        data = self.get_bytearray()[offset:offset+self.row_size]
        db_offset = self.db_offset

        # indicate start of write only area of row!
        if self.row_offset:
            data = data[self.row_offset:]
            db_offset += self.row_offset

        client.db_write(db_nr, db_offset, data)

    def read(self, client):
        """
        read current data of db row from plc
        """
        assert(isinstance(self._bytearray, DB))
        assert(self.row_size >= 0)
        db_nr = self._bytearray.db_number
        _bytearray = client.db_read(db_nr, self.db_offset, self.row_size)

        data = self.get_bytearray()
        # replace data in bytearray
        for i, b in enumerate(_bytearray):
            data[i + self.db_offset] = b
