"""
Snap7 client used for connection to a siemens7 server.
"""
import logging
import re
from ctypes import c_int, c_char_p, byref, sizeof, c_uint16, c_int32, c_byte, c_ulong
from ctypes import c_void_p
from datetime import datetime

import snap7
from snap7.common import check_error, load_library, ipv4
from snap7.exceptions import Snap7Exception
from snap7.types import S7Object, buffer_type, buffer_size, BlocksList
from snap7.types import TS7BlockInfo, param_types, cpu_statuses, S7SZLHeader, S7SZL

logger = logging.getLogger(__name__)


def error_wrap(func):
    """Parses a s7 error code returned the decorated function."""

    def f(*args, **kw):
        code = func(*args, **kw)
        check_error(code, context="client")

    return f


class Client:
    """
    A snap7 client
    """

    def __init__(self):
        self._read_callback = None
        self._callback = None
        self._pointer = None
        self._library = load_library()
        self.create()

    def __del__(self):
        self.destroy()

    def create(self):
        """
        create a SNAP7 client.
        """
        logger.info("creating snap7 client")
        self._library.Cli_Create.restype = c_void_p
        self._pointer = S7Object(self._library.Cli_Create())

    def destroy(self):
        """
        destroy a client.
        """
        logger.info("destroying snap7 client")
        if self._pointer:
            return self._library.Cli_Destroy(byref(self._pointer))
        self._pointer = None

    def plc_stop(self):
        """
        stops a client
        """
        logger.info("stopping plc")
        return self._library.Cli_PlcStop(self._pointer)

    def plc_cold_start(self):
        """
        cold starts a client
        """
        logger.info("cold starting plc")
        return self._library.Cli_PlcColdStart(self._pointer)

    def plc_hot_start(self):
        """
        hot starts a client
        """
        logger.info("hot starting plc")
        return self._library.Cli_PlcHotStart(self._pointer)

    def get_cpu_state(self):
        """
        Retrieves CPU state from client
        """
        state = c_int(0)
        self._library.Cli_GetPlcStatus(self._pointer, byref(state))

        try:
            status_string = cpu_statuses[state.value]
        except KeyError:
            status_string = None

        if not status_string:
            raise Snap7Exception(f"The cpu state ({state.value}) is invalid")

        logger.debug(f"CPU state is {status_string}")
        return status_string

    def get_cpu_info(self):
        """
        Retrieves CPU info from client
        """
        info = snap7.types.S7CpuInfo()
        result = self._library.Cli_GetCpuInfo(self._pointer, byref(info))
        check_error(result, context="client")
        return info

    @error_wrap
    def disconnect(self):
        """
        disconnect a client.
        """
        logger.info("disconnecting snap7 client")
        return self._library.Cli_Disconnect(self._pointer)

    @error_wrap
    def connect(self, address, rack, slot, tcpport=102):
        """
        Connect to a S7 server.

        :param address: IP address of server
        :param rack: rack on server
        :param slot: slot on server.
        """
        logger.info(f"connecting to {address}:{tcpport} rack {rack} slot {slot}")

        self.set_param(snap7.types.RemotePort, tcpport)
        return self._library.Cli_ConnectTo(
            self._pointer, c_char_p(address.encode()),
            c_int(rack), c_int(slot))

    def db_read(self, db_number, start, size):
        """This is a lean function of Cli_ReadArea() to read PLC DB.

        :returns: user buffer.
        """
        logger.debug(f"db_read, db_number:{db_number}, start:{start}, size:{size}")

        type_ = snap7.types.wordlen_to_ctypes[snap7.types.S7WLByte]
        data = (type_ * size)()
        result = (self._library.Cli_DBRead(
            self._pointer, db_number, start, size,
            byref(data)))
        check_error(result, context="client")
        return bytearray(data)

    @error_wrap
    def db_write(self, db_number, start, data):
        """
        Writes to a DB object.

        :param start: write offset
        :param data: bytearray
        """
        wordlen = snap7.types.S7WLByte
        type_ = snap7.types.wordlen_to_ctypes[wordlen]
        size = len(data)
        cdata = (type_ * size).from_buffer_copy(data)
        logger.debug(f"db_write db_number:{db_number} start:{start} size:{size} data:{data}")
        return self._library.Cli_DBWrite(self._pointer, db_number, start, size,
                                         byref(cdata))

    def delete(self, block_type, block_num):
        """
        Deletes a block

        :param block_type: Type of block
        :param block_num: Bloc number
        """
        logger.info("deleting block")
        blocktype = snap7.types.block_types[block_type]
        result = self._library.Cli_Delete(self._pointer, blocktype, block_num)
        return result

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
        result = self._library.Cli_FullUpload(self._pointer, block_type,
                                              block_num, byref(_buffer),
                                              byref(size))
        check_error(result, context="client")
        return bytearray(_buffer)[:size.value], size.value

    def upload(self, block_num):
        """
        Uploads a block body from AG

        :param block_num: bytearray
        """
        logger.debug(f"db_upload block_num: {block_num}")
        block_type = snap7.types.block_types['DB']
        _buffer = buffer_type()
        size = c_int(sizeof(_buffer))

        result = self._library.Cli_Upload(self._pointer, block_type, block_num,
                                          byref(_buffer), byref(size))

        check_error(result, context="client")
        logger.info(f'received {size} bytes')
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
        type_ = c_byte
        size = len(data)
        cdata = (type_ * len(data)).from_buffer_copy(data)
        result = self._library.Cli_Download(self._pointer, block_num,
                                            byref(cdata), size)
        return result

    def db_get(self, db_number):
        """Uploads a DB from AG.
        """
        logger.debug(f"db_get db_number: {db_number}")
        _buffer = buffer_type()
        result = self._library.Cli_DBGet(
            self._pointer, db_number, byref(_buffer),
            byref(c_int(buffer_size)))
        check_error(result, context="client")
        return bytearray(_buffer)

    def read_area(self, area, dbnumber, start, size):
        """This is the main function to read data from a PLC.
        With it you can read DB, Inputs, Outputs, Merkers, Timers and Counters.

        :param dbnumber: The DB number, only used when area= S7AreaDB
        :param start: offset to start writing
        :param size: number of units to read
        """
        assert area in snap7.types.areas.values()
        if area == snap7.types.S7AreaTM:
            wordlen = snap7.types.S7WLTimer
        elif area == snap7.types.S7AreaCT:
            wordlen = snap7.types.S7WLCounter
        else:
            wordlen = snap7.types.S7WLByte
        type_ = snap7.types.wordlen_to_ctypes[wordlen]
        logger.debug(f"reading area: {area} dbnumber: {dbnumber} start: {start}: amount {size}: wordlen: {wordlen}")
        data = (type_ * size)()
        result = self._library.Cli_ReadArea(self._pointer, area, dbnumber, start,
                                            size, wordlen, byref(data))
        check_error(result, context="client")
        return bytearray(data)

    @error_wrap
    def write_area(self, area, dbnumber, start, data):
        """This is the main function to write data into a PLC. It's the
        complementary function of Cli_ReadArea(), the parameters and their
        meanings are the same. The only difference is that the data is
        transferred from the buffer pointed by pUsrData into PLC.

        :param dbnumber: The DB number, only used when area= S7AreaDB
        :param start: offset to start writing
        :param data: a bytearray containing the payload
        """
        if area == snap7.types.S7AreaTM:
            wordlen = snap7.types.S7WLTimer
        elif area == snap7.types.S7AreaCT:
            wordlen = snap7.types.S7WLCounter
        else:
            wordlen = snap7.types.S7WLByte
        type_ = snap7.types.wordlen_to_ctypes[snap7.types.S7WLByte]
        size = len(data)
        logger.debug(f"writing area: {area} dbnumber: {dbnumber} start: {start}: size {size}: "
                     f"wordlen {wordlen} type: {type_}")
        cdata = (type_ * len(data)).from_buffer_copy(data)
        return self._library.Cli_WriteArea(self._pointer, area, dbnumber, start,
                                           size, wordlen, byref(cdata))

    def read_multi_vars(self, items):
        """This function read multiple variables from the PLC.

        :param items: list of S7DataItem objects
        :returns: a tuple with the return code and a list of data items
        """
        result = self._library.Cli_ReadMultiVars(self._pointer, byref(items),
                                                 c_int32(len(items)))
        check_error(result, context="client")
        return result, items

    def list_blocks(self):
        """Returns the AG blocks amount divided by type.

        :returns: a snap7.types.BlocksList object.
        """
        logger.debug("listing blocks")
        blocksList = BlocksList()
        result = self._library.Cli_ListBlocks(self._pointer, byref(blocksList))
        check_error(result, context="client")
        logger.debug(f"blocks: {blocksList}")
        return blocksList

    def list_blocks_of_type(self, blocktype, size):
        """This function returns the AG list of a specified block type."""

        blocktype = snap7.types.block_types.get(blocktype)

        if not blocktype:
            raise Snap7Exception("The blocktype parameter was invalid")

        logger.debug(f"listing blocks of type: {blocktype} size: {size}")

        if size == 0:
            return 0

        data = (c_uint16 * size)()
        count = c_int(size)
        result = self._library.Cli_ListBlocksOfType(
            self._pointer, blocktype,
            byref(data),
            byref(count))

        logger.debug(f"number of items found: {count}")

        check_error(result, context="client")
        return data

    def get_block_info(self, blocktype, db_number):
        """Returns the block information for the specified block."""

        blocktype = snap7.types.block_types.get(blocktype)

        if not blocktype:
            raise Snap7Exception("The blocktype parameter was invalid")
        logger.debug(f"retrieving block info for block {db_number} of type {blocktype}")

        data = TS7BlockInfo()

        result = self._library.Cli_GetAgBlockInfo(
            self._pointer, blocktype,
            db_number, byref(data))
        check_error(result, context="client")
        return data

    @error_wrap
    def set_session_password(self, password):
        """Send the password to the PLC to meet its security level."""
        assert len(password) <= 8, 'maximum password length is 8'
        return self._library.Cli_SetSessionPassword(self._pointer,
                                                    c_char_p(password.encode()))

    @error_wrap
    def clear_session_password(self):
        """Clears the password set for the current session (logout)."""
        return self._library.Cli_ClearSessionPassword(self._pointer)

    def set_connection_params(self, address, local_tsap, remote_tsap):
        """
        Sets internally (IP, LocalTSAP, RemoteTSAP) Coordinates.
        This function must be called just before Cli_Connect().

        :param address: PLC/Equipment IPV4 Address, for example "192.168.1.12"
        :param local_tsap: Local TSAP (PC TSAP)
        :param remote_tsap: Remote TSAP (PLC TSAP)
        """
        assert re.match(ipv4, address), f'{address} is invalid ipv4'
        result = self._library.Cli_SetConnectionParams(self._pointer, address,
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
        result = self._library.Cli_SetConnectionType(self._pointer,
                                                     c_uint16(connection_type))
        if result != 0:
            raise Snap7Exception("The parameter was invalid")

    def get_connected(self):
        """
        Returns the connection status

        :returns: a boolean that indicates if connected.
        """
        connected = c_int32()
        result = self._library.Cli_GetConnected(self._pointer, byref(connected))
        check_error(result, context="client")
        return bool(connected)

    def ab_read(self, start, size):
        """
        This is a lean function of Cli_ReadArea() to read PLC process outputs.
        """
        wordlen = snap7.types.S7WLByte
        type_ = snap7.types.wordlen_to_ctypes[wordlen]
        data = (type_ * size)()
        logger.debug(f"ab_read: start: {start}: size {size}: ")
        result = self._library.Cli_ABRead(self._pointer, start, size,
                                          byref(data))
        check_error(result, context="client")
        return bytearray(data)

    def ab_write(self, start, data):
        """
        This is a lean function of Cli_WriteArea() to write PLC process
        outputs
        """
        wordlen = snap7.types.S7WLByte
        type_ = snap7.types.wordlen_to_ctypes[wordlen]
        size = len(data)
        cdata = (type_ * size).from_buffer_copy(data)
        logger.debug(f"ab write: start: {start}: size: {size}: ")
        return self._library.Cli_ABWrite(
            self._pointer, start, size, byref(cdata))

    def as_ab_read(self, start, size):
        """
        This is the asynchronous counterpart of client.ab_read().
        """
        wordlen = snap7.types.S7WLByte
        type_ = snap7.types.wordlen_to_ctypes[wordlen]
        data = (type_ * size)()
        logger.debug(f"ab_read: start: {start}: size {size}: ")
        result = self._library.Cli_AsABRead(self._pointer, start, size,
                                            byref(data))
        check_error(result, context="client")
        return bytearray(data)

    def as_ab_write(self, start, data):
        """
        This is the asynchronous counterpart of Cli_ABWrite.
        """
        wordlen = snap7.types.S7WLByte
        type_ = snap7.types.wordlen_to_ctypes[wordlen]
        size = len(data)
        cdata = (type_ * size).from_buffer_copy(data)
        logger.debug(f"ab write: start: {start}: size: {size}: ")
        return self._library.Cli_AsABWrite(
            self._pointer, start, size, byref(cdata))

    @error_wrap
    def as_compress(self, time):
        """
        This is the asynchronous counterpart of client.compress().
        """
        return self._library.Cli_AsCompress(self._pointer, time)

    def copy_ram_to_rom(self):
        """

        """
        return self._library.Cli_AsCopyRamToRom(self._pointer)

    def as_ct_read(self):
        """

        """
        return self._library.Cli_AsCTRead(self._pointer)

    def as_ct_write(self):
        """

        """
        return self._library.Cli_AsCTWrite(self._pointer)

    def as_db_fill(self):
        """

        """
        return self._library.Cli_AsDBFill(self._pointer)

    def as_db_get(self, db_number):
        """
        This is the asynchronous counterpart of Cli_DBGet.
        """
        logger.debug(f"db_get db_number: {db_number}")
        _buffer = buffer_type()
        result = self._library.Cli_AsDBGet(self._pointer, db_number,
                                           byref(_buffer),
                                           byref(c_int(buffer_size)))
        check_error(result, context="client")
        return bytearray(_buffer)

    def as_db_read(self, db_number, start, size):
        """
        This is the asynchronous counterpart of Cli_DBRead.

        :returns: user buffer.
        """
        logger.debug(f"db_read, db_number:{db_number}, start:{start}, size:{size}")

        type_ = snap7.types.wordlen_to_ctypes[snap7.types.S7WLByte]
        data = (type_ * size)()
        result = (self._library.Cli_AsDBRead(self._pointer, db_number, start, size, byref(data)))
        check_error(result, context="client")
        return data

    def as_db_write(self, db_number, start, data):
        """

        """
        wordlen = snap7.types.S7WLByte
        type_ = snap7.types.wordlen_to_ctypes[wordlen]
        size = len(data)
        cdata = (type_ * size).from_buffer_copy(data)
        logger.debug(f"db_write db_number:{db_number} start:{start} size:{size} data:{data}")
        return self._library.Cli_AsDBWrite(
            self._pointer, db_number, start, size,
            byref(cdata))

    @error_wrap
    def as_download(self, data, block_num=-1):
        """
        Downloads a DB data into the AG asynchronously.
        A whole block (including header and footer) must be available into the
        user buffer.

        :param block_num: New Block number (or -1)
        :param data: the user buffer
        """
        size = len(data)
        type_ = c_byte * len(data)
        cdata = type_.from_buffer_copy(data)
        return self._library.Cli_AsDownload(self._pointer, block_num,
                                            byref(cdata), size)

    @error_wrap
    def compress(self, time):
        """
        Performs the Memory compress action.

        :param time: Maximum time expected to complete the operation (ms).
        """
        return self._library.Cli_Compress(self._pointer, time)

    @error_wrap
    def set_param(self, number, value):
        """Sets an internal Server object parameter.
        """
        logger.debug(f"setting param number {number} to {value}")
        type_ = param_types[number]
        return self._library.Cli_SetParam(self._pointer, number,
                                          byref(type_(value)))

    def get_param(self, number):
        """Reads an internal Client object parameter.
        """
        logger.debug(f"retreiving param number {number}")
        type_ = param_types[number]
        value = type_()
        code = self._library.Cli_GetParam(self._pointer, c_int(number),
                                          byref(value))
        check_error(code)
        return value.value

    def get_pdu_length(self):
        """
        Returns info about the PDU length.
        """
        logger.info("getting PDU length")
        requested_ = c_uint16()
        negotiated_ = c_uint16()
        code = self._library.Cli_GetPduLength(self._pointer, byref(requested_), byref(negotiated_))
        check_error(code)

        return negotiated_.value

    def get_plc_datetime(self):
        """
        Get date and time from PLC.

        :return: date and time as datetime
        """
        type_ = c_int32
        buffer = (type_ * 9)()
        result = self._library.Cli_GetPlcDateTime(self._pointer, byref(buffer))
        check_error(result, context="client")

        return datetime(
            year=buffer[5] + 1900,
            month=buffer[4] + 1,
            day=buffer[3],
            hour=buffer[2],
            minute=buffer[1],
            second=buffer[0]
        )

    @error_wrap
    def set_plc_datetime(self, dt):
        """
        Set date and time in PLC

        :param dt: date and time as datetime
        """
        type_ = c_int32
        buffer = (type_ * 9)()
        buffer[0] = dt.second
        buffer[1] = dt.minute
        buffer[2] = dt.hour
        buffer[3] = dt.day
        buffer[4] = dt.month - 1
        buffer[5] = dt.year - 1900

        return self._library.Cli_SetPlcDateTime(self._pointer, byref(buffer))

    def check_as_completion(self, p_value) -> bool:
        """
        Method to check Status of an async request. Result contains if the check was successful,
        not the data value itself
        :param p_value: Pointer where result of this check shall be written.
        :return: 0 - Job is done successfully
        :return: 1 - Job is either pending or contains s7errors
        """
        result = self._library.Cli_CheckAsCompletion(self._pointer, p_value)
        check_error(result, context="client")
        return result

    def set_as_callback(self):
        # Cli_SetAsCallback
        raise NotImplementedError

    def wait_as_completion(self, timeout: int) -> int:
        """
        Snap7 Cli_WaitAsCompletion representative.
        :param timeout: ms to wait for async job
        :return: Result of request in int format
        """
        # Cli_WaitAsCompletion
        result = self._library.Cli_WaitAsCompletion(self._pointer, c_ulong(timeout))
        check_error(result, context="client")
        return result

    def _prepare_as_read_area(self, area, size):
        if area not in snap7.types.areas.values():
            raise NotImplementedError(f"{area} is not implemented in snap7.types")
        if area == snap7.types.S7AreaTM:
            wordlen = snap7.types.S7WLTimer
        elif area == snap7.types.S7AreaCT:
            wordlen = snap7.types.S7WLCounter
        else:
            wordlen = snap7.types.S7WLByte
        type_ = snap7.types.wordlen_to_ctypes[wordlen]
        usrdata = (type_ * size)()
        return wordlen, usrdata

    def as_read_area(self, area, dbnumber, start, size, wordlen, pusrdata):
        """This is the main function to read data from a PLC.
        With it you can read DB, Inputs, Outputs, Merkers, Timers and Counters.

        :param area: chosen memory_area
        :param dbnumber: The DB number, only used when area= S7AreaDB
        :param start: offset to start writing
        :param size: number of units to read
        :param pusrdata:
        :param wordlen:
        """
        logger.debug(f"reading area: {area} dbnumber: {dbnumber} start: {start}: amount {size}: wordlen: {wordlen}")
        result = self._library.Cli_AsReadArea(self._pointer, area, dbnumber, start, size, wordlen, pusrdata)
        check_error(result, context="client")
        return result

    def _prepare_as_write_area(self, area, data):
        if area not in snap7.types.areas.values():
            raise NotImplementedError(f"{area} is not implemented in snap7.types")
        if area == snap7.types.S7AreaTM:
            wordlen = snap7.types.S7WLTimer
        elif area == snap7.types.S7AreaCT:
            wordlen = snap7.types.S7WLCounter
        else:
            wordlen = snap7.types.S7WLByte
        type_ = snap7.types.wordlen_to_ctypes[snap7.types.S7WLByte]
        cdata = (type_ * len(data)).from_buffer_copy(data)
        return wordlen, cdata

    def as_write_area(self, area, dbnumber, start, size, wordlen, pusrdata):
        """This is the main function to write data into a PLC. It's the
        complementary function of Cli_ReadArea(), the parameters and their
        meanings are the same. The only difference is that the data is
        transferred from the buffer pointed by pUsrData into PLC.

        :param area: chosen memory_area
        :param dbnumber: The DB number, only used when area= S7AreaDB
        :param start: offset to start writing
        :param data: a bytearray containing the payload
        """
        type_ = snap7.types.wordlen_to_ctypes[snap7.types.S7WLByte]
        logger.debug(f"writing area: {area} dbnumber: {dbnumber} start: {start}: size {size}: "
                     f"wordlen {wordlen} type: {type_}")
        cdata = (type_ * len(pusrdata)).from_buffer_copy(pusrdata)
        res = self._library.Cli_AsWriteArea(self._pointer, area, dbnumber, start, size, wordlen, byref(cdata))
        check_error(res, context="client")
        return res

    def asebread(self):
        # Cli_AsEBRead
        raise NotImplementedError

    def asebwrite(self):
        # Cli_AsEBWrite
        raise NotImplementedError

    def asfullupload(self):
        # Cli_AsFullUpload
        raise NotImplementedError

    def aslistblocksoftype(self):
        # Cli_AsListBlocksOfType
        raise NotImplementedError

    def asmbread(self):
        # Cli_AsMBRead
        raise NotImplementedError

    def asmbwrite(self):
        # Cli_AsMBWrite
        raise NotImplementedError

    def asreadszl(self):
        # Cli_AsReadSZL
        raise NotImplementedError

    def asreadszllist(self):
        # Cli_AsReadSZLList
        raise NotImplementedError

    def astmread(self):
        # Cli_AsTMRead
        raise NotImplementedError

    def astmwrite(self):
        # Cli_AsTMWrite
        raise NotImplementedError

    def asupload(self):
        # Cli_AsUpload
        raise NotImplementedError

    def aswritearea(self):
        # Cli_AsWriteArea
        raise NotImplementedError

    def copyramtorom(self):
        # Cli_CopyRamToRom
        raise NotImplementedError

    def ctread(self):
        # Cli_CTRead
        raise NotImplementedError

    def ctwrite(self):
        # Cli_CTWrite
        raise NotImplementedError

    def dbfill(self):
        # Cli_DBFill
        raise NotImplementedError

    def ebread(self):
        # Cli_EBRead
        raise NotImplementedError

    def ebwrite(self):
        # Cli_EBWrite
        raise NotImplementedError

    def errortext(self):
        # Cli_ErrorText
        raise NotImplementedError

    def getagblockinfo(self):
        # Cli_GetAgBlockInfo
        raise NotImplementedError

    def getcpinfo(self):
        # Cli_GetCpInfo
        raise NotImplementedError

    def getexectime(self):
        # Cli_GetExecTime
        raise NotImplementedError

    def getlasterror(self):
        # Cli_GetLastError
        raise NotImplementedError

    def getordercode(self):
        # Cli_GetOrderCode
        raise NotImplementedError

    def getpdulength(self):
        # Cli_GetPduLength
        raise NotImplementedError

    def getpgblockinfo(self):
        # Cli_GetPgBlockInfo
        raise NotImplementedError

    def getplcstatus(self):
        # Cli_GetPlcStatus
        raise NotImplementedError

    def getprotection(self):
        # Cli_GetProtection
        raise NotImplementedError

    def isoexchangebuffer(self):
        # Cli_IsoExchangeBuffer
        raise NotImplementedError

    def mbread(self):
        # Cli_MBRead
        raise NotImplementedError

    def mbwrite(self):
        # Cli_MBWrite
        raise NotImplementedError

    def readarea(self):
        # Cli_ReadArea
        raise NotImplementedError

    def readmultivars(self):
        # Cli_ReadMultiVars
        raise NotImplementedError

    def readszl(self, ssl_id: int, index: int = 0x0000) -> S7SZL:
        # Cli_ReadSZL
        data = S7SZL()
        size = c_int(sizeof(data))
        result = self._library.Cli_ReadSZL(self._pointer, ssl_id, index, byref(data), byref(size))
        check_error(result, context="client")
        return data

    def readszllist(self):
        # Cli_ReadSZLList
        raise NotImplementedError

    def setparam(self):
        # Cli_SetParam
        raise NotImplementedError

    def setplcsystemdatetime(self):
        # Cli_SetPlcSystemDateTime
        raise NotImplementedError

    def setsessionpassword(self):
        # Cli_SetSessionPassword
        raise NotImplementedError

    def tmread(self):
        # Cli_TMRead
        raise NotImplementedError

    def tmwrite(self):
        # Cli_TMWrite
        raise NotImplementedError

    def writemultivars(self):
        # Cli_WriteMultiVars
        raise NotImplementedError
