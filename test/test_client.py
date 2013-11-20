import unittest
import logging

import snap7


logging.basicConfig()
l = logging.getLogger()
l.setLevel(logging.INFO)

#ip = '192.168.200.24'
ip = '127.0.0.1'
db_number = 1
rack = 1
slot = 1


class TestClient(unittest.TestCase):

    def setUp(self):
        self.client = snap7.client.Client()
        self.client.connect(ip, rack, slot)

    def tearDown(self):
        self.client.disconnect()
        self.client.destroy()

    def test_db_read(self):
        size = 40
        start = 0
        db = 1
        data = bytearray(40)
        self.client.db_write(db_number=db, start=start, size=size, data=data)
        result = self.client.db_read(db_number=db, start=start, size=size)
        self.assertEqual(data, result)

    def test_db_write(self):
        size = 40
        data = (snap7.types.wordlen_to_ctypes[snap7.types.S7WLByte] * size)()
        data = bytearray(data)
        self.client.db_write(db_number=1, start=0, size=size, data=data)

    def test_db_get(self):
        self.client.db_get(db_number=db_number)

    @unittest.skip('authorization required?')
    def test_upload(self):
        self.client.upload(block_num=db_number)

    @unittest.skip("TODO: fix the download and upload buffer")
    def test_download(self):
        data = bytearray(128)
        self.client.download(block_num=db_number, data=data)

    def test_read_area(self):
        area = snap7.types.S7AreaDB
        dbnumber = 1
        amount = 10
        start = 1
        self.client.read_area(area, dbnumber, start, amount)

    def test_write_area(self):
        area = snap7.types.S7AreaDB
        dbnumber = 1
        amount = 10
        start = 1
        data = bytearray(10)
        self.client.write_area(area, dbnumber, start, amount, data)

    def test_list_blocks(self):
        blockList = self.client.list_blocks()
        print blockList

    def test_list_blocks_of_type(self):
        self.client.list_blocks_of_type(snap7.types.block_types['DB'], 10)

    def test_set_session_password(self):
        password = 'abcdefgh'
        self.client.set_session_password(password)

    def test_clear_session_password(self):
        self.client.clear_session_password()

    def test_set_connection_params(self):
        self.client.set_connection_params("10.0.0.2", 10, 10)

    def test_set_connection_type(self):
        self.client.set_connection_type(1)
        self.client.set_connection_type(2)
        self.client.set_connection_type(3)
        self.client.set_connection_type(20)

    def test_get_connected(self):
        self.client.get_connected()

    @unittest.skip("TODO: not yet fully implemented")
    def test_ab_read(self):
        self.client.ab_read()

    @unittest.skip("TODO: not yet fully implemented")
    def test_ab_write(self):
        self.client.ab_write()

    @unittest.skip("TODO: not yet fully implemented")
    def test_as_ab_read(self):
        self.client.as_ab_read()

    @unittest.skip("TODO: not yet fully implemented")
    def test_as_ab_write(self):
        self.client.as_ab_write()

    @unittest.skip("TODO: not yet fully implemented")
    def test_as_compress(self):
        self.client.as_compress()

    @unittest.skip("TODO: not yet fully implemented")
    def test_as_copy_ram_to_rom(self):
        self.client.copy_ram_to_rom()

    @unittest.skip("TODO: not yet fully implemented")
    def test_as_ct_read(self):
        self.client.as_ct_read()

    @unittest.skip("TODO: not yet fully implemented")
    def test_as_ct_write(self):
        self.client.as_ct_write()

    @unittest.skip("TODO: not yet fully implemented")
    def test_as_db_fill(self):
        self.client.as_db_fill()

    @unittest.skip("TODO: not yet fully implemented")
    def test_as_db_get(self):
        self.client.as_db_get()

    @unittest.skip("TODO: not yet fully implemented")
    def test_as_db_read(self):
        self.client.as_db_read()

    @unittest.skip("TODO: not yet fully implemented")
    def test_as_db_write(self):
        self.client.as_db_write()

    @unittest.skip("TODO: not yet fully implemented")
    def test_as_download(self):
        data = bytearray(128)
        self.client.as_download(block_num=-1, data=data)

    @unittest.skip("TODO: fix the download and upload buffer")
    def test_download(self):
        data = bytearray(128)
        self.client.download(block_num=db_number, data=data)


if __name__ == '__main__':
    unittest.main()


# TODO: implement
"""
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
Cli_Compress
Cli_Connect
Cli_CopyRamToRom
Cli_CTRead
Cli_CTWrite
Cli_DBFill
Cli_Delete
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
Cli_WaitAsCompletion
Cli_WriteMultiVars
"""
