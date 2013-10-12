from ctypes import c_int, c_char_p, c_char
# from ctypes import sizeof

from loadlib import clib
from ctypes import pointer


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


def disconnect(client):
    # Cli_Disconnect(Client : S7Object) : integer;
    clib.Cli_Disconnect(client)


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
