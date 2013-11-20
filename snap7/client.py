"""
Snap7 client used for connection to a siemens7 server.
"""
import re
from ctypes import c_int, c_char_p, byref, sizeof, c_uint16, c_int32
import logging

import snap7
from snap7.types import S7Object, buffer_type, buffer_size
from snap7.types import wordlen_to_ctypes, BlocksList
from snap7.common import check_error, load_library, ipv4
from snap7.exceptions import Snap7Exception

logger = logging.getLogger(__name__)


def error_wrap(func):
    """Parses a s7 error code returned the decorated function."""
    def f(*args, **kw):
        code = func(*args, **kw)
        check_error(code, context="client")
    return f


def bytearray_to_buffer(data):
    """Convert a byte arra to a ctypes / snap7 type
    """
    #TODO: find out how to do this better, this doesn't seem to work correctly

    assert isinstance(data, bytearray)
    # creates a 65535 ctypes.c_ubyte buffer

    _buffer = snap7.types.buffer_type()

    assert len(data) <= len(_buffer)

    for i in range(len(data)):
        _buffer[i] = data[i]

    return _buffer


class Client(object):
    """A snap7 client"""
    def __init__(self):
        """Create a Client

        :returns: A Snap7Client object
        """
        self.library = load_library()
        logger.info("creating snap7 client")
        self.pointer = S7Object(self.library.Cli_Create())
        # local buffer used by test for now..

    def destroy(self):
        """
        destroy a client.
        """
        logger.info("destroying snap7 client")
        return self.library.Cli_Destroy(byref(self.pointer))

    @error_wrap
    def disconnect(self):
        """
        disconnect a client.
        """
        logger.info("disconnecting snap7 client")
        return self.library.Cli_Disconnect(self.pointer)

    @error_wrap
    def connect(self, address, rack, slot):
        """
        Connect to a S7 server.

        :param address: IP address of server
        :param rack: rack on server
        :param slot: slot on server.
        """
        logger.info("connecting to %s rack %s slot %s" % (address, rack, slot))
        return self.library.Cli_ConnectTo(self.pointer, c_char_p(address),
                                  c_int(rack), c_int(slot))

    def db_read(self, db_number, start, size):
        """This is a lean function of Cli_ReadArea() to read PLC DB.

        :returns: user buffer.
        """
        logger.debug("db_read, db_number:%s, start:%s, size:%s" %
                     (db_number, start, size))

        type_ = snap7.types.wordlen_to_ctypes[snap7.types.S7WLByte]
        data = (type_ * size)()
        result = (self.library.Cli_DBRead(self.pointer, db_number, start, size,
                                  byref(data)))
        check_error(result, context="client")
        return bytearray(data)

    @error_wrap
    def db_write(self, db_number, start, size, data):
        """
        Writes to a DB object.

        :param data: bytearray
        """
        _buffer = bytearray_to_buffer(data)

        logger.debug("db_write db_number:%s start:%s size:%s data:%s" %
                     (db_number, start, size, data))

        return self.library.Cli_DBWrite(self.pointer, db_number, start, size,
                                byref(_buffer))

    def full_upload(self, _type, block_num):
        """
        Uploads a full block body from AG.
        The whole block (including header and footer) is copied into the user
        buffer.

        :param block_num: Number of Block
        """
        _buffer = buffer_type()
        size = c_int(sizeof(_buffer))
        block_type = snap7.types.block_types[_type]
        result = self.library.Cli_FullUpload(self.pointer, block_type,
                                             block_num, byref(_buffer),
                                             byref(size))
        check_error(result, context="client")
        return bytearray(_buffer), size.value


    def upload(self, block_num):
        """
        Uploads a block body from AG

        :param data: bytearray
        """
        logger.debug("db_upload block_num: %s" % (block_num))

        block_type = snap7.types.block_types['DB']
        _buffer = buffer_type()
        size = c_int(sizeof(_buffer))

        result = self.library.Cli_Upload(self.pointer, block_type, block_num,
                                         byref(_buffer), byref(size))

        check_error(result, context="client")
        logger.info('received %s bytes' % size)
        return bytearray(_buffer)

    @error_wrap
    def download(self, data, block_num=-1):
        """
        Downloads a DB data into the AG.
        A whole block (including header and footer) must be available into the
        user buffer.

        :param block_num: New Block number (or -1)
        :param data: the user buffer
        """
        _buffer = bytearray_to_buffer(data)
        size = c_int(sizeof(_buffer))
        result = self.library.Cli_Download(self.pointer, block_num,
                                           byref(_buffer), size)
        return result

    def db_get(self, db_number):
        """Uploads a DB from AG.
        """
        logging.debug("db_get db_number: %s" % db_number)
        _buffer = buffer_type()
        result = self.library.Cli_DBGet(self.pointer, db_number, byref(_buffer),
                                byref(c_int(buffer_size)))
        check_error(result, context="client")
        return bytearray(_buffer)

    def read_area(self, area, dbnumber, start, amount):
        """This is the main function to read data from a PLC.
        With it you can read DB, Inputs, Outputs, Merkers, Timers and Counters.
        """
        wordlen = snap7.types.S7WLByte
        logging.debug("reading area: %s dbnumber: %s start: %s: amount %s: "
                      "wordlen: %s" % (area, dbnumber, start, amount, wordlen))
        data = (wordlen_to_ctypes[wordlen] * amount)()
        result = self.library.Cli_ReadArea(self.pointer, area, dbnumber, start,
                                           amount, wordlen, byref(data))
        check_error(result, context="client")
        return data

    @error_wrap
    def write_area(self, area, dbnumber, start, amount, data):
        """This is the main function to write data into a PLC. It's the
        complementary function of Cli_ReadArea(), the parameters and their
        meanings are the same. The only difference is that the data is
        transferred from the buffer pointed by pUsrData into PLC.
        """
        wordlen = snap7.types.S7WLByte
        logging.debug("writing area: %s dbnumber: %s start: %s: amount %s: "
                      "wordlen: %s" % (area, dbnumber, start, amount, wordlen))

        _buffer = bytearray_to_buffer(data)

        return self.library.Cli_WriteArea(self.pointer, area, dbnumber, start,
                                          amount, wordlen, byref(_buffer))

    def list_blocks(self):
        """Returns the AG blocks amount divided by type.

        :returns: a snap7.types.BlocksList object.
        """
        logging.debug("listing blocks")
        blocksList = BlocksList()
        result = self.library.Cli_ListBlocks(self.pointer, byref(blocksList))
        check_error(result, context="client")
        logging.debug("blocks: %s" % blocksList)
        return blocksList

    def list_blocks_of_type(self, blocktype, size):
        """This function returns the AG list of a specified block type."""
        logging.debug("listing blocks of type: %s size: %s" %
                      (blocktype, size))
        data = (c_int * 10)()
        count = c_int(size)
        result = self.library.Cli_ListBlocksOfType(self.pointer, blocktype,
                                           byref(data),
                                           byref(count))

        logging.debug("number of items found: %s" % count)
        check_error(result, context="client")
        return data

    @error_wrap
    def set_session_password(self, password):
        """Send the password to the PLC to meet its security level."""
        assert len(password) <= 8, 'maximum password length is 8'
        return self.library.Cli_SetSessionPassword(self.pointer,
                                                   c_char_p(password))

    @error_wrap
    def clear_session_password(self):
        """Clears the password set for the current session (logout)."""
        return self.library.Cli_ClearSessionPassword(self.pointer)

    def set_connection_params(self, address, local_tsap, remote_tsap):
        """
        Sets internally (IP, LocalTSAP, RemoteTSAP) Coordinates.
        This function must be called just before Cli_Connect().

        :param address: PLC/Equipment IPV4 Address, for example "192.168.1.12"
        :param local_tsap: Local TSAP (PC TSAP)
        :param remote_tsap: Remote TSAP (PLC TSAP)
        """
        assert re.match(ipv4, address), '%s is invalid ipv4' % address
        result = self.library.Cli_SetConnectionParams(self.pointer, address,
                                                      c_uint16(local_tsap),
                                                      c_uint16(remote_tsap))
        if result != 0:
            raise Snap7Exception("The parameter was invalid")

    def set_connection_type(self, connection_type):
        """
        Sets the connection resource type, i.e the way in which the Clients
        connects to a PLC.

        :param connection_type: 1 for PG, 2 for OP, 3 to 10 for S7 Basic
        """
        result = self.library.Cli_SetConnectionType(self.pointer,
                                                    c_uint16(connection_type))
        if result != 0:
            raise Snap7Exception("The parameter was invalid")

    def get_connected(self):
        """
        Returns the connection status

        :returns: a boolean that indicates if connected.
        """
        connected = c_int32()
        result = self.library.Cli_GetConnected(self.pointer, byref(connected))
        check_error(result, context="client")
        return bool(connected)

    def ab_read(self):
        """
        This is a lean function of Cli_ReadArea() to read PLC process outputs.
        """
        return self.library.Cli_ABRead(self.pointer)

    def ab_write(self):
        """

        """
        return self.library.Cli_ABWrite(self.pointer)

    def as_ab_read(self):
        """

        """
        return self.library.Cli_AsABRead(self.pointer)

    def as_ab_write(self):
        """

        """
        return self.library.Cli_AsABWrite(self.pointer)

    def as_compress(self):
        """

        """
        return self.library.Cli_AsCompress(self.pointer)

    def copy_ram_to_rom(self):
        """

        """
        return self.library.Cli_AsCopyRamToRom(self.pointer)

    def as_ct_read(self):
        """

        """
        return self.library.Cli_AsCTRead(self.pointer)

    def as_ct_write(self):
        """

        """
        return self.library.Cli_AsCTWrite(self.pointer)

    def as_db_fill(self):
        """

        """
        return self.library.Cli_AsDBFill(self.pointer)

    def as_db_get(self):
        """

        """
        return self.library.Cli_AsDBGet(self.pointer)

    def as_db_read(self):
        """

        """
        return self.library.Cli_AsDBRead(self.pointer)

    def as_db_write(self):
        """

        """
        return self.library.Cli_AsDBWrite(self.pointer)

    @error_wrap
    def as_download(self, data, block_num=-1):
        """
        Downloads a DB data into the AG asynchronously.
        A whole block (including header and footer) must be available into the
        user buffer.

        :param block_num: New Block number (or -1)
        :param data: the user buffer
        """
        _buffer = bytearray_to_buffer(data)
        size = c_int(sizeof(_buffer))
        return self.library.Cli_AsDownload(self.pointer, block_num,
                                           byref(_buffer), size)
