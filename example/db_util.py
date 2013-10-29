

def get_bool(_bytearray, byte_index, bool_index):
    """
    Get the boolean value from location in bytearray
    """
    index_value = 2 ** bool_index
    byte_value = _bytearray[byte_index]
    current_value = byte_value & index_value
    return current_value == index_value


def set_bool(_bytearray, byte_index, bool_index, value):
    """
    Set boolean value on location in bytearray
    """
    assert value in [0, 1, True, False]

    current_value = get_bool(_bytearray, byte_index, bool_index)
    index_value = 2 ** bool_index

    # check if bool already has correct value
    if current_value == index_value:
        return

    if value:
        # make sure index_v is IN current byte
        if not current_value == index_value:
            _bytearray[byte_index] += index_value
    else:
        # make sure index_v is NOT in current byte
        if current_value == index_value:
            _bytearray[byte_index] -= index_value


def set_int(_bytearray, byte_index, _int):
    """
    Set value in bytearray to int
    """
    # int needs two bytes...
    if _int < 256:
        _bytearray[byte_index + 1] = _int


def set_reaL(_bytearray, byte_index, real):
    """
    Set Real value
    """
    pass


def set_string(_bytearray, byte_index, _string):
    """
    Set string value
    """
    pass
    # set len count

    # for each c set ord(c) in index

    # for


