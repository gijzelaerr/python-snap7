from ctypes import c_int, c_char_p, byref, sizeof
from loadlib import clib
import logging

from types import S7Object, buffer_type, buffer_size
from data import block_types
from error import error_parse

logger = logging.getLogger(__name__)


def error_wrap(code):
    errors = error_parse(code, client=True)
    if errors:
        for error in errors:
            logger.error(error)
        raise Exception(", ".join(errors))


class Client(object):
    def __init__(self):
        """Create a server.

        :returns: A Snap7Client object
        """
        logger.info("creating snap7 client")
        self.pointer = S7Object(clib.Cli_Create())

    def destroy(self):
        logger.info("destroying snap7 client")
        clib.Cli_Destroy(byref(self.pointer))

    def disconnect(self):
        logger.info("disconnecting snap7 client")
        x = clib.Cli_Disconnect(self.pointer)

    def connect(self, address, rack, slot):
        logger.info("connecting to %s rack %s slot %s" % (address, rack, slot))
        return clib.Cli_ConnectTo(self.pointer, c_char_p(address),
                                  c_int(rack), c_int(slot))

    def db_read(self, db_number, start, size):
        """This is a lean function of Cli_ReadArea() to read PLC DB.

        :returns: A string?
        """
        logger.info("db_read, db_number:%s, start:%s, size:%s" % (db_number,
                                                                  start, size))
        buffer_ = buffer_type()
        error_wrap(clib.Cli_DBRead(self.pointer, db_number, start, size,
                                   byref(buffer_)))
        return bytearray(buffer_)

    def db_upload(self, block_type, block_num, data):
        """Uploads a block body from AG.
        """
        logger.info("db_upload block_type: %s, block_num: %s, data: %s" % 
                    (block_type, block_num, data))
        assert(block_type in block_types.values())
        size = c_int(sizeof(data))
        logger.info("requesting size: %s" % size)
        error_wrap(clib.Cli_Upload(self.pointer, block_type, block_num,
                                byref(data), byref(size)))
        logger.info('received %s bytes' % size)

    def db_get(self, db_number):
        """Uploads a DB from AG.
        """
        logging.info("db_get db_number: %s" % db_number)
        buffer_ = buffer_type()
        error_wrap(clib.Cli_DBGet(self.pointer, db_number, byref(buffer_),
                                  byref(c_int(buffer_size))))
        return bytearray(buffer_)





"""
Cli_ABRead
Cli_ABWrite
Cli_AsABRead
Cli_AsABWrite
Cli_AsCompress
Cli_AsCopyRamToRom
Cli_AsCTRead
Cli_AsCTWrite
Cli_AsDBFill
Cli_AsDBGet
Cli_AsDBRead
Cli_AsDBWrite
Cli_AsDownload
Cli_AsEBRead
Cli_AsEBWrite
Cli_AsFullUpload
Cli_AsListBlocksOfType
Cli_AsMBRead
Cli_AsMBWrite
Cli_AsReadArea
Cli_AsReadSZL
Cli_AsReadSZLList
Cli_AsTMRead
Cli_AsTMWrite
Cli_AsUpload
Cli_AsWriteArea
Cli_CheckAsCompletion
Cli_ClearSessionPassword
Cli_Compress
Cli_Connect
Cli_ConnectTo
Cli_CopyRamToRom
Cli_Create
Cli_CTRead
Cli_CTWrite
Cli_DBFill
Cli_DBGet
Cli_DBRead
Cli_DBWrite
Cli_Delete
Cli_Destroy
Cli_Disconnect
Cli_Download
Cli_EBRead
Cli_EBWrite
Cli_ErrorText
Cli_FullUpload
Cli_GetAgBlockInfo
Cli_GetCpInfo
Cli_GetCpuInfo
Cli_GetExecTime
Cli_GetLastError
Cli_GetOrderCode
Cli_GetParam
Cli_GetPduLength
Cli_GetPgBlockInfo
Cli_GetPlcDateTime
Cli_GetPlcStatus
Cli_GetProtection
Cli_IsoExchangeBuffer
Cli_ListBlocks
Cli_ListBlocksOfType
Cli_MBRead
Cli_MBWrite
Cli_PlcColdStart
Cli_PlcHotStart
Cli_PlcStop
Cli_ReadArea
Cli_ReadMultiVars
Cli_ReadSZL
Cli_ReadSZLList
Cli_SetAsCallback
Cli_SetParam
Cli_SetPlcDateTime
Cli_SetPlcSystemDateTime
Cli_SetSessionPassword
Cli_TMRead
Cli_TMWrite
Cli_Upload
Cli_WaitAsCompletion
Cli_WriteArea
Cli_WriteMultiVars
"""
