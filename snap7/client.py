from ctypes import c_int, c_char_p, c_char
# from ctypes import sizeof

from loadlib import clib


class Snap7Client(object):
    def __init__(self, pointer):
        self.pointer = pointer


def create():
    """Create a server.

    :returns: A Snap7Client object

    """
    pointer = clib.Cli_Create()
    return Snap7Client(pointer)


def destroy(client):
    clib.Cli_Destroy(client.pointer)


def connect(client, address, rack, slot):
    print address, rack, slot
    return clib.Cli_ConnectTo(client.pointer, c_char_p(address),
                              c_int(rack), c_int(slot))


def readDB(client, db_number):
    """
    read a dataBlock from plc

    :returns: A string?
    """

    bufferData = c_char * 65000

    clib.readDB(client, db_number, bufferData)

    return bufferData


def uploadDB(client, db):
    """
    upload datablock to PLC
    """
    # int S7API Cli_Upload(S7Object Client,
    # int BlockType, int BlockNum, void *pUsrData, int *Size);

    # FIXME
    clib.Cli_Upload(client)
