from collections import OrderedDict
import struct


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
    byte1 = _bytearray[byte_index+1]
    byte0 = _bytearray[byte_index]
    return byte1 + (byte0 << 8)


def set_real(_bytearray, byte_index, real):
    """
    Set Real value

    make 4 byte data from real

    """
    real = struct.pack('>f', real)
    _bytes = struct.unpack('4B', real)
    for i, b in enumerate(_bytes):
        _bytearray[byte_index+i] = b


def get_real(_bytearray, byte_index):
    """
    Get real value. create float from 4 bytes
    """
    x = _bytearray[byte_index:byte_index+4]
    real = struct.unpack('>f', struct.pack('4B', *x))[0]
    return real


def set_string(_bytearray, byte_index, value):
    """
    Set string value

    :params value: string data
    :params size: total possible string size
    """
    # set len count
    _bytearray[byte_index+1] = len(value)
    i = 0
    # fill array which chr integers
    for i, c in enumerate(value):
        _bytearray[byte_index+2+i] = ord(c)

    # fill the rest with empty space
    for r in range(i + 1, _bytearray[byte_index]):
        _bytearray[byte_index+2+r] = ord(' ')


def get_string(_bytearray, byte_index):
    """
    parse string from bytearray
    """
    size = _bytearray[byte_index+1]
    data = map(chr, _bytearray[byte_index+2:byte_index+2+size])
    return "".join(data)


def get_dword(_bytearray, byte_index):
    data = _bytearray[byte_index:byte_index+4]
    dword = struct.unpack('I', struct.pack('4B', *data))[0]
    return dword


def set_dword(_bytearray, byte_index, dword):
    _bytes = struct.unpack('4B', struct.pack('I', dword))
    for i, b in enumerate(_bytes):
        _bytearray[byte_index+i] = b


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
    db_offset = None       # at which byte in db should we start reading
                           # first fields could be used for something else

    def __init__(self, _bytearray,
                 specification, row_size, size, id_field=None,
                 db_offset=0, layout_offset=0):

        self.db_offset = db_offset
        self.layout_offset = layout_offset  # if row layout does not start a 0
        self._bytearray = _bytearray
        self.row_size = row_size
        self.specification = specification
        # loop over bytearray. make rowObjects
        # store index of id_field to row objects
        self.index = OrderedDict()

        for i in range(size):
            # calculate where row in bytearray starts
            db_offset = i * row_size + self.db_offset
            # create a row object
            row = DB_Row(self._bytearray,
                         specification,
                         db_offset=db_offset,
                         layout_offset=layout_offset)
            # store row object
            key = row[id_field] if id_field else i
            self.index[key] = row

    def __getitem__(self, key):
        return self.index.get(key)

    def __iter__(self):
        for key, row in self.index.items():
            yield key, row

    def __len__(self):
        return len(self.index)


class DB_Row(object):
    """
    Provide ROW API for DB bytearray
    """

    def __init__(self, _bytearray, _specification,
                 db_offset=0, layout_offset=0):
        # if _bytearray contains many row we need a row offset
                                          # in layout spec
        self.db_offset = db_offset    # starintg point of db data
        self.layout_offset = layout_offset  # starign point of row data

        assert(isinstance(_bytearray, bytearray))
        self._bytearray = _bytearray
        self._specification = parse_specification(_specification)

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
        if self._bytearray == _bytearray:
            return True
        return False

    def get_offset(self, byte_index):
        """
        Calculate correct beginning position for a row
        the db_offset = row_size * index
        """
        return int(byte_index) - self.layout_offset + self.db_offset

    def get_value(self, byte_index, _type):
        _bytearray = self._bytearray

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
        _bytearray = self._bytearray

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
