import ctypes
import struct
import unittest
import logging
import time
import mock

from datetime import datetime
from subprocess import Popen
from os import path, kill
import snap7
from snap7.snap7exceptions import Snap7Exception
from snap7.snap7types import S7AreaDB, S7WLByte, S7DataItem, S7AreaTM, S7AreaCT
from snap7 import util


logging.basicConfig(level=logging.WARNING)

ip = '127.0.0.1'
tcpport = 1102
db_number = 1
rack = 1
slot = 1


class TestClient(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        server_path = path.join(path.dirname(path.realpath(snap7.__file__)),
                                "bin/snap7-server.py")
        cls.server_pid = Popen([server_path]).pid
        time.sleep(2)  # wait for server to start

    @classmethod
    def tearDownClass(cls):
        kill(cls.server_pid, 1)

    def setUp(self):
        self.client = snap7.client.Client()
        self.client.connect(ip, rack, slot, tcpport)

    def tearDown(self):
        self.client.disconnect()
        self.client.destroy()

    def test_db_read(self):
        size = 40
        start = 0
        db = 1
        data = bytearray(40)
        self.client.db_write(db_number=db, start=start, data=data)
        result = self.client.db_read(db_number=db, start=start, size=size)
        self.assertEqual(data, result)

    def test_db_write(self):
        size = 40
        data = bytearray(size)
        self.client.db_write(db_number=1, start=0, data=data)

    def test_db_get(self):
        self.client.db_get(db_number=db_number)

    def test_read_multi_vars(self):
        db = 1

        # build and write test values
        test_value_1 = 129.5
        test_bytes_1 = bytearray(struct.pack('>f', test_value_1))
        self.client.db_write(db, 0, test_bytes_1)

        test_value_2 = -129.5
        test_bytes_2 = bytearray(struct.pack('>f', test_value_2))
        self.client.db_write(db, 4, test_bytes_2)

        test_value_3 = 123
        test_bytes_3 = bytearray([0, 0])
        util.set_int(test_bytes_3, 0, test_value_3)
        self.client.db_write(db, 8, test_bytes_3)

        test_values = [test_value_1, test_value_2, test_value_3]

        # build up our requests
        data_items = (S7DataItem * 3)()

        data_items[0].Area = ctypes.c_int32(S7AreaDB)
        data_items[0].WordLen = ctypes.c_int32(S7WLByte)
        data_items[0].Result = ctypes.c_int32(0)
        data_items[0].DBNumber = ctypes.c_int32(db)
        data_items[0].Start = ctypes.c_int32(0)
        data_items[0].Amount = ctypes.c_int32(4)  # reading a REAL, 4 bytes

        data_items[1].Area = ctypes.c_int32(S7AreaDB)
        data_items[1].WordLen = ctypes.c_int32(S7WLByte)
        data_items[1].Result = ctypes.c_int32(0)
        data_items[1].DBNumber = ctypes.c_int32(db)
        data_items[1].Start = ctypes.c_int32(4)
        data_items[1].Amount = ctypes.c_int32(4)  # reading a REAL, 4 bytes

        data_items[2].Area = ctypes.c_int32(S7AreaDB)
        data_items[2].WordLen = ctypes.c_int32(S7WLByte)
        data_items[2].Result = ctypes.c_int32(0)
        data_items[2].DBNumber = ctypes.c_int32(db)
        data_items[2].Start = ctypes.c_int32(8)
        data_items[2].Amount = ctypes.c_int32(2)  # reading an INT, 2 bytes

        # create buffers to receive the data
        # use the Amount attribute on each item to size the buffer
        for di in data_items:
            # create the buffer
            dataBuffer = ctypes.create_string_buffer(di.Amount)
            # get a pointer to the buffer
            pBuffer = ctypes.cast(ctypes.pointer(dataBuffer),
                                  ctypes.POINTER(ctypes.c_uint8))
            di.pData = pBuffer

        result, data_items = self.client.read_multi_vars(data_items)

        result_values = []
        # function to cast bytes to match data_types[] above
        byte_to_value = [util.get_real, util.get_real, util.get_int]

        # unpack and test the result of each read
        for i in range(0, len(data_items)):
            btv = byte_to_value[i]
            di = data_items[i]
            value = btv(di.pData, 0)
            result_values.append(value)

        self.assertEqual(result_values[0], test_values[0])
        self.assertEqual(result_values[1], test_values[1])
        self.assertEqual(result_values[2], test_values[2])

    def test_upload(self):
        """
        this raises an exception due to missing authorization? maybe not
        implemented in server emulator
        """
        self.assertRaises(Snap7Exception, self.client.upload, db_number)

    @unittest.skip("TODO: invalid block size")
    def test_download(self):
        data = bytearray(1024)
        self.client.download(block_num=db_number, data=data)

    def test_read_area(self):
        amount = 1
        start = 1
        # Test read_area with a DB
        area = snap7.snap7types.areas.DB
        dbnumber = 1
        self.client.read_area(area, dbnumber, start, amount)
        # Test read_area with a TM
        area = snap7.snap7types.areas.TM
        dbnumber = 0
        self.client.read_area(area, dbnumber, start, amount)
        # Test read_area with a CT
        area = snap7.snap7types.areas.CT
        dbnumber = 0
        self.client.read_area(area, dbnumber, start, amount)

    def test_write_area(self):
        # Test write area with a DB
        area = snap7.snap7types.areas.DB
        dbnumber = 1
        size = 1
        start = 1
        data = bytearray(size)
        self.client.write_area(area, dbnumber, start, data)
        # Test write area with a TM
        area = snap7.snap7types.areas.TM
        dbnumber = 0
        size = 2
        timer = bytearray(size)
        self.client.write_area(area, dbnumber, start, timer)
        # Test write area with a CT
        area = snap7.snap7types.areas.CT
        dbnumber = 0
        size = 2
        timer = bytearray(size)
        self.client.write_area(area, dbnumber, start, timer)

    def test_list_blocks(self):
        blockList = self.client.list_blocks()

    def test_list_blocks_of_type(self):
        self.client.list_blocks_of_type('DB', 10)

        self.assertRaises(Exception, self.client.list_blocks_of_type,
                          'NOblocktype', 10)

    def test_get_block_info(self):
        """test Cli_GetAgBlockInfo"""
        self.client.get_block_info('DB', 1)

        self.assertRaises(Exception, self.client.get_block_info,
                          'NOblocktype', 10)
        self.assertRaises(Exception, self.client.get_block_info, 'DB', 10)

    def test_get_cpu_state(self):
        """this tests the get_cpu_state function"""
        self.client.get_cpu_state()

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

    def test_ab_read(self):
        start = 1
        size = 1
        data = bytearray(size)
        self.client.ab_write(start=start, data=data)
        self.client.ab_read(start=start, size=size)

    @unittest.skip("TODO: crash client: FATAL: exception not rethrown")
    def test_ab_write(self):
        start = 1
        size = 10
        data = bytearray(size)
        self.client.ab_write(start=start, data=data)

    @unittest.skip("TODO: crash client: FATAL: exception not rethrown")
    def test_as_ab_read(self):
        start = 1
        size = 1
        self.client.as_ab_read(start=start, size=size)

    @unittest.skip("TODO: not yet fully implemented")
    def test_as_ab_write(self):
        start = 1
        size = 10
        data = bytearray(size)
        self.client.as_ab_write(start=start, data=data)

    def test_compress(self):
        time = 1000
        self.client.compress(time)

    def test_as_compress(self):
        time = 1000
        self.client.as_compress(time)

    def test_set_param(self):
        values = (
            (snap7.snap7types.PingTimeout, 800),
            (snap7.snap7types.SendTimeout, 15),
            (snap7.snap7types.RecvTimeout, 3500),
            (snap7.snap7types.SrcRef, 128),
            (snap7.snap7types.DstRef, 128),
            (snap7.snap7types.SrcTSap, 128),
            (snap7.snap7types.PDURequest, 470),
        )
        for param, value in values:
            self.client.set_param(param, value)

        self.assertRaises(Exception, self.client.set_param,
                          snap7.snap7types.RemotePort, 1)

    def test_get_param(self):
        expected = (
            (snap7.snap7types.RemotePort, tcpport),
            (snap7.snap7types.PingTimeout, 750),
            (snap7.snap7types.SendTimeout, 10),
            (snap7.snap7types.RecvTimeout, 3000),
            (snap7.snap7types.SrcRef, 256),
            (snap7.snap7types.DstRef, 0),
            (snap7.snap7types.SrcTSap, 256),
            (snap7.snap7types.PDURequest, 480),
        )
        for param, value in expected:
            self.assertEqual(self.client.get_param(param), value)

        non_client = snap7.snap7types.LocalPort, snap7.snap7types.WorkInterval,\
            snap7.snap7types.MaxClients, snap7.snap7types.BSendTimeout,\
            snap7.snap7types.BRecvTimeout, snap7.snap7types.RecoveryTime,\
            snap7.snap7types.KeepAliveTime

        # invalid param for client
        for param in non_client:
            self.assertRaises(Exception, self.client.get_param,  non_client)

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

    def test_as_db_get(self):
        self.client.db_get(db_number=db_number)

    @unittest.skip("TODO: crash client: FATAL: exception not rethrown")
    def test_as_db_read(self):
        size = 40
        start = 0
        db = 1
        data = bytearray(40)
        self.client.db_write(db_number=db, start=start, data=data)
        result = self.client.as_db_read(db_number=db, start=start, size=size)
        self.assertEqual(data, result)

    @unittest.skip("TODO: crash client: FATAL: exception not rethrown")
    def test_as_db_write(self):
        size = 40
        data = bytearray(size)
        self.client.as_db_write(db_number=1, start=0, data=data)

    def test_as_download(self):
        data = bytearray(128)
        self.client.as_download(block_num=-1, data=data)

    def test_plc_stop(self):
        self.client.plc_stop()

    def test_plc_hot_start(self):
        self.client.plc_hot_start()

    def test_plc_cold_start(self):
        self.client.plc_cold_start()


    def test_get_pdu_length(self):
        pduRequested = self.client.get_param(10)
        pduSize = self.client.get_pdu_length()
        self.assertEqual(pduSize, pduRequested)

    def test_get_cpu_info(self):
        expected = (
            ('ModuleTypeName', 'CPU 315-2 PN/DP'),
            ('SerialNumber', 'S C-C2UR28922012'),
            ('ASName', 'SNAP7-SERVER'),
            ('Copyright', 'Original Siemens Equipment'),
            ('ModuleName', 'CPU 315-2 PN/DP')
        )
        cpuInfo = self.client.get_cpu_info()
        for param, value in expected:
            self.assertEqual(getattr(cpuInfo, param).decode('utf-8'), value)

    def test_db_write_with_byte_literal_does_not_throw(self):
        mock_write = mock.MagicMock()
        mock_write.return_value = None
        original = self.client.library.Cli_DBWrite
        self.client.library.Cli_DBWrite = mock_write
        data = b'\xDE\xAD\xBE\xEF'

        try:
            self.client.db_write(db_number=1, start=0, data=data)
        except TypeError as e:
            self.fail(str(e))
        finally:
            self.client.library.Cli_DBWrite = original

    def test_download_with_byte_literal_does_not_throw(self):
        mock_download = mock.MagicMock()
        mock_download.return_value = None
        original = self.client.library.Cli_Download
        self.client.library.Cli_Download = mock_download
        data = b'\xDE\xAD\xBE\xEF'

        try:
            self.client.download(block_num=db_number, data=data)
        except TypeError as e:
            self.fail(str(e))
        finally:
            self.client.library.Cli_Download = original

    def test_write_area_with_byte_literal_does_not_throw(self):
        mock_writearea = mock.MagicMock()
        mock_writearea.return_value = None
        original = self.client.library.Cli_WriteArea
        self.client.library.Cli_WriteArea = mock_writearea

        area = snap7.snap7types.areas.DB
        dbnumber = 1
        size = 4
        start = 1
        data = b'\xDE\xAD\xBE\xEF'

        try:
            self.client.write_area(area, dbnumber, start, data)
        except TypeError as e:
            self.fail(str(e))
        finally:
            self.client.library.Cli_WriteArea = original

    def test_ab_write_with_byte_literal_does_not_throw(self):
        mock_write = mock.MagicMock()
        mock_write.return_value = None
        original = self.client.library.Cli_ABWrite
        self.client.library.Cli_ABWrite = mock_write

        start = 1
        data = b'\xDE\xAD\xBE\xEF'

        try:
            self.client.ab_write(start=start, data=data)
        except TypeError as e:
            self.fail(str(e))
        finally:
            self.client.library.Cli_ABWrite = original

    def test_as_ab_write_with_byte_literal_does_not_throw(self):
        mock_write = mock.MagicMock()
        mock_write.return_value = None
        original = self.client.library.Cli_AsABWrite
        self.client.library.Cli_AsABWrite = mock_write

        start = 1
        data = b'\xDE\xAD\xBE\xEF'

        try:
            self.client.as_ab_write(start=start, data=data)
        except TypeError as e:
            self.fail(str(e))
        finally:
            self.client.library.Cli_AsABWrite = original

    def test_as_db_write_with_byte_literal_does_not_throw(self):
        mock_write = mock.MagicMock()
        mock_write.return_value = None
        original = self.client.library.Cli_AsDBWrite
        self.client.library.Cli_AsDBWrite = mock_write
        data = b'\xDE\xAD\xBE\xEF'

        try:
            self.client.db_write(db_number=1, start=0, data=data)
        except TypeError as e:
            self.fail(str(e))
        finally:
            self.client.library.Cli_AsDBWrite = original

    def test_as_download_with_byte_literal_does_not_throw(self):
        mock_download = mock.MagicMock()
        mock_download.return_value = None
        original = self.client.library.Cli_AsDownload
        self.client.library.Cli_AsDownload = mock_download
        data = b'\xDE\xAD\xBE\xEF'

        try:
            self.client.as_download(block_num=db_number, data=data)
        except TypeError as e:
            self.fail(str(e))
        finally:
            self.client.library.Cli_AsDownload = original

    def test_get_plc_time(self):
        self.assertEqual(datetime.now().replace(microsecond=0), self.client.get_plc_datetime())

    def test_set_plc_datetime(self):
        new_dt = datetime(2011,1,1,1,1,1,0)
        self.client.set_plc_datetime(new_dt)
        # Can't actual set datetime in emulated PLC, get_plc_datetime always returns system time.
        #self.assertEqual(new_dt, self.client.get_plc_datetime())


class TestClientBeforeConnect(unittest.TestCase):
    """
    Test suite of items that should run without an open connection.
    """
    def setUp(self):
        self.client = snap7.client.Client()

    def test_set_param(self):
        values = (
            (snap7.snap7types.RemotePort, 1102),
            (snap7.snap7types.PingTimeout, 800),
            (snap7.snap7types.SendTimeout, 15),
            (snap7.snap7types.RecvTimeout, 3500),
            (snap7.snap7types.SrcRef, 128),
            (snap7.snap7types.DstRef, 128),
            (snap7.snap7types.SrcTSap, 128),
            (snap7.snap7types.PDURequest, 470),
        )
        for param, value in values:
            self.client.set_param(param, value)

class TestLibraryIntegration(unittest.TestCase):
    def setUp(self):
        # replace the function load_library with a mock
        self.loadlib_patch = mock.patch('snap7.client.load_library')
        self.loadlib_func = self.loadlib_patch.start()

        # have load_library return another mock
        self.mocklib = mock.MagicMock()
        self.loadlib_func.return_value = self.mocklib

        # have the Cli_Create of the mock return None
        self.mocklib.Cli_Create.return_value = None

    def tearDown(self):
        # restore load_library
        self.loadlib_patch.stop()

    def test_create(self):
        client = snap7.client.Client()
        self.mocklib.Cli_Create.assert_called_once()

    def test_gc(self):
        client = snap7.client.Client()
        del client
        self.mocklib.Cli_Destroy.assert_called_once()

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
Cli_GetExecTime
Cli_GetLastError
Cli_GetOrderCode
Cli_GetParam
Cli_GetPduLength
Cli_GetPgBlockInfo
Cli_GetPlcStatus
Cli_GetProtection
Cli_IsoExchangeBuffer
Cli_MBRead
Cli_MBWrite
Cli_ReadArea
Cli_ReadMultiVars
Cli_ReadSZL
Cli_ReadSZLList
Cli_SetAsCallback
Cli_SetParam
Cli_SetPlcSystemDateTime
Cli_SetSessionPassword
Cli_TMRead
Cli_TMWrite
Cli_WaitAsCompletion
Cli_WriteMultiVars
"""
