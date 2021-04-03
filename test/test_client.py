import ctypes
import gc
import logging
import struct
import time
import unittest
import platform
from datetime import datetime, timedelta, date
from multiprocessing import Process
from unittest import mock


import snap7
from snap7 import util
from snap7.exceptions import Snap7Exception
from snap7.common import check_error
from snap7.server import mainloop
from snap7.types import S7AreaDB, S7WLByte, S7DataItem, S7SZL, S7SZLList, buffer_type, buffer_size, S7Object, Areas, WordLen


logging.basicConfig(level=logging.WARNING)

ip = '127.0.0.1'
tcpport = 1102
db_number = 1
rack = 1
slot = 1


class TestClient(unittest.TestCase):

    process = None

    @classmethod
    def setUpClass(cls):
        cls.process = Process(target=mainloop)
        cls.process.start()
        time.sleep(2)  # wait for server to start

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        cls.process.join(1)
        if cls.process.is_alive():
            cls.process.kill()

    def setUp(self):
        self.client = snap7.client.Client()
        self.client.connect(ip, rack, slot, tcpport)

    def tearDown(self):
        self.client.disconnect()
        self.client.destroy()

    def _as_check_loop(self, check_times=20) -> int:
        check_status = ctypes.c_int(-1)
        # preparing Server values
        for i in range(check_times):
            self.client.check_as_completion(ctypes.byref(check_status))
            if check_status.value == 0:
                break
            time.sleep(0.5)
        else:
            raise Snap7Exception(f"Async Request not finished after {check_times} times - Fail")
        return check_status.value

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
        data_items[0].WordLen = ctypes.c_int32(WordLen.Byte.value)
        data_items[0].Result = ctypes.c_int32(0)
        data_items[0].DBNumber = ctypes.c_int32(db)
        data_items[0].Start = ctypes.c_int32(0)
        data_items[0].Amount = ctypes.c_int32(4)  # reading a REAL, 4 bytes

        data_items[1].Area = ctypes.c_int32(S7AreaDB)
        data_items[1].WordLen = ctypes.c_int32(WordLen.Byte.value)
        data_items[1].Result = ctypes.c_int32(0)
        data_items[1].DBNumber = ctypes.c_int32(db)
        data_items[1].Start = ctypes.c_int32(4)
        data_items[1].Amount = ctypes.c_int32(4)  # reading a REAL, 4 bytes

        data_items[2].Area = ctypes.c_int32(S7AreaDB)
        data_items[2].WordLen = ctypes.c_int32(WordLen.Byte.value)
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
        for i in range(len(data_items)):
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

    def test_as_upload(self):
        _buffer = buffer_type()
        size = ctypes.c_int(ctypes.sizeof(_buffer))
        self.client.as_upload(1, _buffer, size)
        self.assertRaises(Snap7Exception, self.client.wait_as_completion, 500)

    @unittest.skip("TODO: invalid block size")
    def test_download(self):
        data = bytearray(1024)
        self.client.download(block_num=db_number, data=data)

    def test_read_area(self):
        amount = 1
        start = 1

        # Test read_area with a DB
        area = Areas.DB
        dbnumber = 1
        data = bytearray(b'\x11')
        self.client.write_area(area, dbnumber, start, data)
        res = self.client.read_area(area, dbnumber, start, amount)
        self.assertEqual(data, bytearray(res))

        # Test read_area with a TM
        area = Areas.TM
        dbnumber = 0
        data = bytearray(b'\x12\x34')
        self.client.write_area(area, dbnumber, start, data)
        res = self.client.read_area(area, dbnumber, start, amount)
        self.assertEqual(data, bytearray(res))

        # Test read_area with a CT
        area = Areas.CT
        dbnumber = 0
        data = bytearray(b'\x13\x35')
        self.client.write_area(area, dbnumber, start, data)
        res = self.client.read_area(area, dbnumber, start, amount)
        self.assertEqual(data, bytearray(res))

    def test_write_area(self):
        # Test write area with a DB
        area = Areas.DB
        dbnumber = 1
        size = 1
        start = 1
        data = bytearray(b'\x11')
        self.client.write_area(area, dbnumber, start, data)
        res = self.client.read_area(area, dbnumber, start, 1)
        self.assertEqual(data, bytearray(res))

        # Test write area with a TM
        area = Areas.TM
        dbnumber = 0
        size = 2
        timer = bytearray(b'\x12\x00')
        res = self.client.write_area(area, dbnumber, start, timer)
        res = self.client.read_area(area, dbnumber, start, 1)
        self.assertEqual(timer, bytearray(res))

        # Test write area with a CT
        area = Areas.CT
        dbnumber = 0
        size = 2
        timer = bytearray(b'\x13\x00')
        res = self.client.write_area(area, dbnumber, start, timer)
        res = self.client.read_area(area, dbnumber, start, 1)
        self.assertEqual(timer, bytearray(res))

    def test_list_blocks(self):
        blockList = self.client.list_blocks()

    def test_list_blocks_of_type(self):
        self.client.list_blocks_of_type('DB', 10)

        self.assertRaises(Snap7Exception, self.client.list_blocks_of_type, 'NOblocktype', 10)

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

    def test_ab_write(self):
        start = 1
        size = 10
        data = bytearray(size)
        result = self.client.ab_write(start=start, data=data)
        self.assertEqual(0, result)

    def test_as_ab_read(self):
        expected = b'\x10\x01'
        self.client.ab_write(0, bytearray(expected))

        wordlen = WordLen.Byte
        type_ = snap7.types.wordlen_to_ctypes[wordlen.value]
        buffer = (type_ * 2)()
        self.client.as_ab_read(0, 2, buffer)
        result = self.client.wait_as_completion(500)
        self.assertEqual(0, result)
        self.assertEqual(expected, bytearray(buffer))

    def test_as_ab_write(self):
        data = b'\x01\x11'
        response = self.client.as_ab_write(0, bytearray(data))
        result = self.client.wait_as_completion(500)
        self.assertEqual(0, response)
        self.assertEqual(0, result)
        self.assertEqual(data, self.client.ab_read(0, 2))

    def test_compress(self):
        time_ = 1000
        self.client.compress(time_)

    def test_as_compress(self):
        time_ = 1000
        response = self.client.as_compress(time_)
        result = self.client.wait_as_completion(500)
        self.assertEqual(0, response)
        self.assertEqual(0, result)

    def test_set_param(self):
        values = (
            (snap7.types.PingTimeout, 800),
            (snap7.types.SendTimeout, 15),
            (snap7.types.RecvTimeout, 3500),
            (snap7.types.SrcRef, 128),
            (snap7.types.DstRef, 128),
            (snap7.types.SrcTSap, 128),
            (snap7.types.PDURequest, 470),
        )
        for param, value in values:
            self.client.set_param(param, value)

        self.assertRaises(Exception, self.client.set_param,
                          snap7.types.RemotePort, 1)

    def test_get_param(self):
        expected = (
            (snap7.types.RemotePort, tcpport),
            (snap7.types.PingTimeout, 750),
            (snap7.types.SendTimeout, 10),
            (snap7.types.RecvTimeout, 3000),
            (snap7.types.SrcRef, 256),
            (snap7.types.DstRef, 0),
            (snap7.types.SrcTSap, 256),
            (snap7.types.PDURequest, 480),
        )
        for param, value in expected:
            self.assertEqual(self.client.get_param(param), value)

        non_client = (snap7.types.LocalPort, snap7.types.WorkInterval, snap7.types.MaxClients,
                      snap7.types.BSendTimeout, snap7.types.BRecvTimeout, snap7.types.RecoveryTime,
                      snap7.types.KeepAliveTime)

        # invalid param for client
        for param in non_client:
            self.assertRaises(Exception, self.client.get_param, non_client)

    def test_as_copy_ram_to_rom(self):
        response = self.client.as_copy_ram_to_rom(timeout=1)
        self.client.wait_as_completion(1100)
        self.assertEqual(0, response)

    def test_as_ct_read(self):
        # Cli_AsCTRead
        expected = b'\x10\x01'
        self.client.ct_write(0, 1, bytearray(expected))
        type_ = snap7.types.wordlen_to_ctypes[WordLen.Counter.value]
        buffer = (type_ * 1)()
        self.client.as_ct_read(0, 1, buffer)
        self.client.wait_as_completion(500)
        self.assertEqual(expected, bytearray(buffer))

    def test_as_ct_write(self):
        # Cli_CTWrite
        data = b'\x01\x11'
        response = self.client.as_ct_write(0, 1, bytearray(data))
        result = self.client.wait_as_completion(500)
        self.assertEqual(0, response)
        self.assertEqual(0, result)
        self.assertEqual(data, self.client.ct_read(0, 1))

    def test_as_db_fill(self):
        filler = 31
        expected = bytearray(filler.to_bytes(1, byteorder='big') * 100)
        response = self.client.db_fill(1, filler)
        result = self.client.wait_as_completion(500)
        self.assertEqual(expected, self.client.db_read(1, 0, 100))

    def test_as_db_get(self):
        _buffer = buffer_type()
        size = ctypes.c_int(buffer_size)
        self.client.as_db_get(db_number, _buffer, size)
        self.client.wait_as_completion(500)
        result = bytearray(_buffer)[:size.value]
        self.assertEqual(100, len(result))

    def test_as_db_read(self):
        size = 40
        start = 0
        db = 1
        expected = bytearray(40)
        self.client.db_write(db_number=db, start=start, data=expected)

        wordlen = WordLen.Byte
        type_ = snap7.types.wordlen_to_ctypes[wordlen.value]
        data = (type_ * size)()
        self.client.as_db_read(db, start, size, data)
        self.client.wait_as_completion(500)
        self.assertEqual(data, expected)

    def test_as_db_write(self):
        size = 40
        data = bytearray(size)
        wordlen = WordLen.Byte
        type_ = snap7.types.wordlen_to_ctypes[wordlen.value]
        size = len(data)
        result = (type_ * size).from_buffer_copy(data)
        self.client.as_db_write(db_number=1, start=0, size=size, data=result)
        self.client.wait_as_completion(500)
        self.assertEqual(data, result)

    @unittest.skip("TODO: not yet fully implemented")
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
        original = self.client._library.Cli_DBWrite
        self.client._library.Cli_DBWrite = mock_write
        data = b'\xDE\xAD\xBE\xEF'

        try:
            self.client.db_write(db_number=1, start=0, data=bytearray(data))
        except TypeError as e:
            self.fail(str(e))
        finally:
            self.client._library.Cli_DBWrite = original

    def test_download_with_byte_literal_does_not_throw(self):
        mock_download = mock.MagicMock()
        mock_download.return_value = None
        original = self.client._library.Cli_Download
        self.client._library.Cli_Download = mock_download
        data = b'\xDE\xAD\xBE\xEF'

        try:
            self.client.download(block_num=db_number, data=bytearray(data))
        except TypeError as e:
            self.fail(str(e))
        finally:
            self.client._library.Cli_Download = original

    def test_write_area_with_byte_literal_does_not_throw(self):
        mock_writearea = mock.MagicMock()
        mock_writearea.return_value = None
        original = self.client._library.Cli_WriteArea
        self.client._library.Cli_WriteArea = mock_writearea

        area = Areas.DB
        dbnumber = 1
        size = 4
        start = 1
        data = b'\xDE\xAD\xBE\xEF'

        try:
            self.client.write_area(area, dbnumber, start, bytearray(data))
        except TypeError as e:
            self.fail(str(e))
        finally:
            self.client._library.Cli_WriteArea = original

    def test_ab_write_with_byte_literal_does_not_throw(self):
        mock_write = mock.MagicMock()
        mock_write.return_value = None
        original = self.client._library.Cli_ABWrite
        self.client._library.Cli_ABWrite = mock_write

        start = 1
        data = b'\xDE\xAD\xBE\xEF'

        try:
            self.client.ab_write(start=start, data=bytearray(data))
        except TypeError as e:
            self.fail(str(e))
        finally:
            self.client._library.Cli_ABWrite = original

    @unittest.skip("TODO: not yet fully implemented")
    def test_as_ab_write_with_byte_literal_does_not_throw(self):
        mock_write = mock.MagicMock()
        mock_write.return_value = None
        original = self.client._library.Cli_AsABWrite
        self.client._library.Cli_AsABWrite = mock_write

        start = 1
        data = b'\xDE\xAD\xBE\xEF'

        try:
            self.client.as_ab_write(start=start, data=bytearray(data))
        except TypeError as e:
            self.fail(str(e))
        finally:
            self.client._library.Cli_AsABWrite = original

    @unittest.skip("TODO: not yet fully implemented")
    def test_as_db_write_with_byte_literal_does_not_throw(self):
        mock_write = mock.MagicMock()
        mock_write.return_value = None
        original = self.client._library.Cli_AsDBWrite
        self.client._library.Cli_AsDBWrite = mock_write
        data = b'\xDE\xAD\xBE\xEF'

        try:
            self.client.db_write(db_number=1, start=0, data=bytearray(data))
        except TypeError as e:
            self.fail(str(e))
        finally:
            self.client._library.Cli_AsDBWrite = original

    @unittest.skip("TODO: not yet fully implemented")
    def test_as_download_with_byte_literal_does_not_throw(self):
        mock_download = mock.MagicMock()
        mock_download.return_value = None
        original = self.client._library.Cli_AsDownload
        self.client._library.Cli_AsDownload = mock_download
        data = b'\xDE\xAD\xBE\xEF'

        try:
            self.client.as_download(block_num=db_number, data=bytearray(data))
        except TypeError as e:
            self.fail(str(e))
        finally:
            self.client._library.Cli_AsDownload = original

    def test_get_plc_time(self):
        self.assertAlmostEqual(datetime.now().replace(microsecond=0), self.client.get_plc_datetime(), delta=timedelta(seconds=1))

    def test_set_plc_datetime(self):
        new_dt = datetime(2011, 1, 1, 1, 1, 1, 0)
        self.client.set_plc_datetime(new_dt)
        # Can't actual set datetime in emulated PLC, get_plc_datetime always returns system time.
        # self.assertEqual(new_dt, self.client.get_plc_datetime())

    def test_wait_as_completion_pass(self, timeout=1000):
        # Cli_WaitAsCompletion
        # prepare Server with values
        area = Areas.DB
        dbnumber = 1
        size = 1
        start = 1
        data = bytearray(size)
        self.client.write_area(area, dbnumber, start, data)
        # start as_request and test
        wordlen, usrdata = self.client._prepare_as_read_area(area, size)
        pusrdata = ctypes.byref(usrdata)
        res = self.client.as_read_area(area, dbnumber, start, size, wordlen, pusrdata)
        self.client.wait_as_completion(timeout)
        self.assertEqual(bytearray(usrdata), data)

    def test_wait_as_completion_timeouted(self, timeout=0, tries=500):
        # Cli_WaitAsCompletion
        # prepare Server
        area = Areas.DB
        dbnumber = 1
        size = 1
        start = 1
        data = bytearray(size)
        wordlen, data = self.client._prepare_as_read_area(area, size)
        pdata = ctypes.byref(data)
        self.client.write_area(area, dbnumber, start, bytearray(data))
        # start as_request and wait for zero seconds to try trigger timeout
        for i in range(tries):
            res = self.client.as_read_area(area, dbnumber, start, size, wordlen, pdata)
            res2 = None
            try:
                res2 = self.client.wait_as_completion(timeout)
                check_error(res2)
            except Snap7Exception as s7_err:
                if not s7_err.args[0] == b'CLI : Job Timeout':
                    self.fail(f"While waiting another error appeared: {s7_err}")
                return
            except BaseException:
                self.fail(f"While waiting another error appeared:>>>>>>>> {res2}")

        self.fail(f"After {tries} tries, no timout could be envoked by snap7. Either tests are passing to fast or"
                  f"a problem is existing in the method. Fail test.")

    def test_check_as_completion(self, timeout=5):
        # Cli_CheckAsCompletion
        check_status = ctypes.c_int(-1)
        pending_checked = False
        # preparing Server values
        data = bytearray(b'\x01\xFF')
        size = len(data)
        area = Areas.DB
        db = 1
        start = 1
        self.client.write_area(area, db, start, data)

        # start as_request and test
        wordlen, cdata = self.client._prepare_as_read_area(area, size)
        pcdata = ctypes.byref(cdata)
        res = self.client.as_read_area(area, db, start, size, wordlen, pcdata)
        for i in range(10):
            self.client.check_as_completion(ctypes.byref(check_status))
            if check_status.value == 0:
                self.assertEqual(data, bytearray(cdata))
                break
            pending_checked = True
            time.sleep(1)
        else:
            self.fail(f"TimeoutError - Process pends for more than {timeout} seconds")
        if pending_checked is False:
            logging.warning("Pending was never reached, because Server was to fast,"
                            " but request to server was successfull.")

    def test_as_read_area(self):
        amount = 1
        start = 1

        # Test read_area with a DB
        area = Areas.DB
        dbnumber = 1
        data = bytearray(b'\x11')
        self.client.write_area(area, dbnumber, start, data)
        wordlen, usrdata = self.client._prepare_as_read_area(area, amount)
        pusrdata = ctypes.byref(usrdata)
        res = self.client.as_read_area(area, dbnumber, start, amount, wordlen, pusrdata)
        self.client.wait_as_completion(1000)
        self.assertEqual(bytearray(usrdata), data)

        # Test read_area with a TM
        area = Areas.TM
        dbnumber = 0
        data = bytearray(b'\x12\x34')
        self.client.write_area(area, dbnumber, start, data)
        wordlen, usrdata = self.client._prepare_as_read_area(area, amount)
        pusrdata = ctypes.byref(usrdata)
        res = self.client.as_read_area(area, dbnumber, start, amount, wordlen, pusrdata)
        self.client.wait_as_completion(1000)
        self.assertEqual(bytearray(usrdata), data)

        # Test read_area with a CT
        area = Areas.CT
        dbnumber = 0
        data = bytearray(b'\x13\x35')
        self.client.write_area(area, dbnumber, start, data)
        wordlen, usrdata = self.client._prepare_as_read_area(area, amount)
        pusrdata = ctypes.byref(usrdata)
        res = self.client.as_read_area(area, dbnumber, start, amount, wordlen, pusrdata)
        self.client.wait_as_completion(1000)
        self.assertEqual(bytearray(usrdata), data)

    def test_as_write_area(self):
        # Test write area with a DB
        area = Areas.DB
        dbnumber = 1
        size = 1
        start = 1
        data = bytearray(b'\x11')
        wordlen, cdata = self.client._prepare_as_write_area(area, data)
        res = self.client.as_write_area(area, dbnumber, start, size, wordlen, cdata)
        self.client.wait_as_completion(1000)
        res = self.client.read_area(area, dbnumber, start, 1)
        self.assertEqual(data, bytearray(res))

        # Test write area with a TM
        area = Areas.TM
        dbnumber = 0
        size = 2
        timer = bytearray(b'\x12\x00')
        wordlen, cdata = self.client._prepare_as_write_area(area, timer)
        res = self.client.as_write_area(area, dbnumber, start, size, wordlen, cdata)
        self.client.wait_as_completion(1000)
        res = self.client.read_area(area, dbnumber, start, 1)
        self.assertEqual(timer, bytearray(res))

        # Test write area with a CT
        area = Areas.CT
        dbnumber = 0
        size = 2
        timer = bytearray(b'\x13\x00')
        wordlen, cdata = self.client._prepare_as_write_area(area, timer)
        res = self.client.as_write_area(area, dbnumber, start, size, wordlen, cdata)
        self.client.wait_as_completion(1000)
        res = self.client.read_area(area, dbnumber, start, 1)
        self.assertEqual(timer, bytearray(res))

    def test_as_eb_read(self):
        # Cli_AsEBRead
        wordlen = WordLen.Byte
        type_ = snap7.types.wordlen_to_ctypes[wordlen.value]
        buffer = (type_ * 1)()
        response = self.client.as_eb_read(0, 1, buffer)
        self.assertEqual(0, response)
        self.assertRaises(Snap7Exception, self.client.wait_as_completion, 500)

    def test_as_eb_write(self):
        # Cli_AsEBWrite
        response = self.client.as_eb_write(0, 1, bytearray(b'\x00'))
        self.assertEqual(0, response)
        self.assertRaises(Snap7Exception, self.client.wait_as_completion, 500)

    def test_as_full_upload(self):
        # Cli_AsFullUpload
        response = self.client.as_full_upload('DB', 1)
        self.assertRaises(Snap7Exception, self.client.wait_as_completion, 500)

    def test_as_list_blocks_of_type(self):
        data = (ctypes.c_uint16 * 10)()
        count = ctypes.c_int()
        self.client.as_list_blocks_of_type('DB', data, count)
        self.assertRaises(Snap7Exception, self.client.wait_as_completion, 500)

    def test_as_mb_read(self):
        # Cli_AsMBRead
        wordlen = WordLen.Byte
        type_ = snap7.types.wordlen_to_ctypes[wordlen.value]
        data = (type_ * 1)()
        self.client.as_mb_read(0, 1, data)
        result = bytearray(data)
        self.assertRaises(Snap7Exception, self.client.wait_as_completion, 500)

    def test_as_mb_write(self):
        # Cli_AsMBWrite
        response = self.client.as_mb_write(0, 1, bytearray(b'\x00'))
        self.assertEqual(0, response)
        self.assertRaises(Snap7Exception, self.client.wait_as_completion, 500)

    def test_as_read_szl(self):
        # Cli_AsReadSZL
        expected = b'S C-C2UR28922012\x00\x00\x00\x00\x00\x00\x00\x00'
        ssl_id = 0x011c
        index = 0x0005
        s7_szl = S7SZL()
        size = ctypes.c_int(ctypes.sizeof(s7_szl))
        self.client.as_read_szl(ssl_id, index, s7_szl, size)
        self.client.wait_as_completion(100)
        result = bytes(s7_szl.Data)[2:26]
        self.assertEqual(expected, result)

    def test_as_read_szl_list(self):
        # Cli_AsReadSZLList
        expected = b'\x00\x00\x00\x0f\x02\x00\x11\x00\x11\x01\x11\x0f\x12\x00\x12\x01'
        szl_list = S7SZLList()
        items_count = ctypes.c_int(ctypes.sizeof(szl_list))
        self.client.as_read_szl_list(szl_list, items_count)
        self.client.wait_as_completion(500)
        result = bytearray(szl_list.List)[:16]
        self.assertEqual(expected, result)

    def test_as_tm_read(self):
        # Cli_AsMBRead
        expected = b'\x10\x01'
        wordlen = WordLen.Timer
        self.client.tm_write(0, 1, bytearray(expected))
        type_ = snap7.types.wordlen_to_ctypes[wordlen.value]
        buffer = (type_ * 1)()
        self.client.as_tm_read(0, 1, buffer)
        self.client.wait_as_completion(500)
        self.assertEqual(expected, bytearray(buffer))

    def test_as_tm_write(self):
        # Cli_AsMBWrite
        data = b'\x10\x01'
        response = self.client.as_tm_write(0, 1, bytearray(data))
        result = self.client.wait_as_completion(500)
        self.assertEqual(0, response)
        self.assertEqual(0, result)
        self.assertEqual(data, self.client.tm_read(0, 1))

    def test_copy_ram_to_rom(self):
        # Cli_CopyRamToRom
        self.assertEqual(0, self.client.copy_ram_to_rom(timeout=1))

    def test_ct_read(self):
        # Cli_CTRead
        data = b'\x10\x01'
        self.client.ct_write(0, 1, bytearray(data))
        result = self.client.ct_read(0, 1)
        self.assertEqual(data, result)

    def test_ct_write(self):
        # Cli_CTWrite
        data = b'\x01\x11'
        self.assertEqual(0, self.client.ct_write(0, 1, bytearray(data)))
        self.assertRaises(ValueError, self.client.ct_write, 0, 2, bytes(1))

    def test_db_fill(self):
        # Cli_DBFill
        filler = 31
        expected = bytearray(filler.to_bytes(1, byteorder='big') * 100)
        self.client.db_fill(1, filler)
        self.assertEqual(expected, self.client.db_read(1, 0, 100))

    def test_eb_read(self):
        # Cli_EBRead
        self.client._library.Cli_EBRead = mock.Mock(return_value=0)
        response = self.client.eb_read(0, 1)
        self.assertTrue(isinstance(response, bytearray))
        self.assertEqual(1, len(response))

    def test_eb_write(self):
        # Cli_EBWrite
        self.client._library.Cli_EBWrite = mock.Mock(return_value=0)
        response = self.client.eb_write(0, 1, bytearray(b'\x00'))
        self.assertEqual(0, response)

    def test_error_text(self):
        # Cli_ErrorText
        CPU_INVALID_PASSWORD = 0x01E00000
        CPU_INVLID_VALUE = 0x00D00000
        CANNOT_CHANGE_PARAM = 0x02600000
        self.assertEqual('CPU : Invalid password', self.client.error_text(CPU_INVALID_PASSWORD))
        self.assertEqual('CPU : Invalid value supplied', self.client.error_text(CPU_INVLID_VALUE))
        self.assertEqual('CLI : Cannot change this param now', self.client.error_text(CANNOT_CHANGE_PARAM))

    def test_get_cp_info(self):
        # Cli_GetCpInfo
        result = self.client.get_cp_info()
        self.assertEqual(2048, result.MaxPduLength)
        self.assertEqual(0, result.MaxConnections)
        self.assertEqual(1024, result.MaxMpiRate)
        self.assertEqual(0, result.MaxBusRate)

    def test_get_exec_time(self):
        # Cli_GetExecTime
        response = self.client.get_exec_time()
        self.assertTrue(isinstance(response, int))

    def test_get_last_error(self):
        # Cli_GetLastError
        self.assertEqual(0, self.client.get_last_error())

    def test_get_order_code(self):
        # Cli_GetOrderCode
        expected = b'6ES7 315-2EH14-0AB0 '
        result = self.client.get_order_code()
        self.assertEqual(expected, result.OrderCode)

    def test_get_protection(self):
        # Cli_GetProtection
        result = self.client.get_protection()
        self.assertEqual(1, result.sch_schal)
        self.assertEqual(0, result.sch_par)
        self.assertEqual(1, result.sch_rel)
        self.assertEqual(2, result.bart_sch)
        self.assertEqual(0, result.anl_sch)

    def test_get_pg_block_info(self):
        valid_db_block = b'pp\x01\x01\x05\n\x00c\x00\x00\x00t\x00\x00\x00\x00\x01\x8d\xbe)2\xa1\x01' \
                         b'\x85V\x1f2\xa1\x00*\x00\x00\x00\x00\x00\x02\x01\x0f\x05c\x00#\x00\x00\x00' \
                         b'\x11\x04\x10\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01' \
                         b'\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x00' \
                         b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
                         b'\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        block_info = self.client.get_pg_block_info(bytearray(valid_db_block))
        self.assertEqual(10, block_info.BlkType)
        self.assertEqual(99, block_info.BlkNumber)
        self.assertEqual(2752512, block_info.SBBLength)
        self.assertEqual(bytes((util.utc2local(date(2019, 6, 27)).strftime("%Y/%m/%d")), encoding="utf-8"), block_info.CodeDate)
        self.assertEqual(bytes((util.utc2local(date(2019, 6, 27)).strftime("%Y/%m/%d")), encoding="utf-8"), block_info.IntfDate)

    def test_iso_exchange_buffer(self):
        # Cli_IsoExchangeBuffer
        self.client.db_write(1, 0, bytearray(b'\x11'))
        # PDU read DB1 1.0 BYTE
        data = b'\x32\x01\x00\x00\x01\x00\x00\x0e\x00\x00\x04\x01\x12\x0a\x10\x02\x00\x01\x00\x01\x84\x00\x00\x00'
        # PDU response
        expected = bytearray(b'2\x03\x00\x00\x01\x00\x00\x02\x00\x05\x00\x00\x04\x01\xff\x04\x00\x08\x11')
        self.assertEqual(expected, self.client.iso_exchange_buffer(bytearray(data)))

    def test_mb_read(self):
        # Cli_MBRead
        self.client._library.Cli_MBRead = mock.Mock(return_value=0)
        response = self.client.mb_read(0, 10)
        self.assertTrue(isinstance(response, bytearray))
        self.assertEqual(10, len(response))

    def test_mb_write(self):
        # Cli_MBWrite
        self.client._library.Cli_MBWrite = mock.Mock(return_value=0)
        response = self.client.mb_write(0, 1, bytearray(b'\x00'))
        self.assertEqual(0, response)

    def test_read_szl(self):
        # read_szl_partial_list
        expected_number_of_records = 10
        expected_length_of_record = 34
        ssl_id = 0x001c
        response = self.client.read_szl(ssl_id)
        self.assertEqual(expected_number_of_records, response.Header.NDR)
        self.assertEqual(expected_length_of_record, response.Header.LengthDR)
        # read_szl_single_data_record
        expected = b'S C-C2UR28922012\x00\x00\x00\x00\x00\x00\x00\x00'
        ssl_id = 0x011c
        index = 0x0005
        response = self.client.read_szl(ssl_id, index)
        result = bytes(response.Data)[2:26]
        self.assertEqual(expected, result)
        # read_szl_order_number
        expected = b'6ES7 315-2EH14-0AB0 '
        ssl_id = 0x0111
        index = 0x0001
        response = self.client.read_szl(ssl_id, index)
        result = bytes(response.Data[2:22])
        self.assertEqual(expected, result)
        # read_szl_invalid_id
        ssl_id = 0xffff
        index = 0xffff
        self.assertRaises(Snap7Exception, self.client.read_szl, ssl_id)
        self.assertRaises(Snap7Exception, self.client.read_szl, ssl_id, index)

    def test_read_szl_list(self):
        # Cli_ReadSZLList
        expected = b'\x00\x00\x00\x0f\x02\x00\x11\x00\x11\x01\x11\x0f\x12\x00\x12\x01'
        result = self.client.read_szl_list()
        self.assertEqual(expected, result[:16])

    def test_set_plc_system_datetime(self):
        # Cli_SetPlcSystemDateTime
        self.assertEqual(0, self.client.set_plc_system_datetime())

    def test_tm_read(self):
        # Cli_TMRead
        data = b'\x10\x01'
        self.client.tm_write(0, 1, bytearray(data))
        result = self.client.tm_read(0, 1)
        self.assertEqual(data, result)

    def test_tm_write(self):
        # Cli_TMWrite
        data = b'\x10\x01'
        self.assertEqual(0, self.client.tm_write(0, 1, bytearray(data)))
        self.assertEqual(data, self.client.tm_read(0, 1))
        self.assertRaises(Snap7Exception, self.client.tm_write, 0, 100, bytes(200))
        self.assertRaises(ValueError, self.client.tm_write, 0, 2, bytes(2))

    def test_write_multi_vars(self):
        # Cli_WriteMultiVars
        items_count = 3
        items = []
        areas = [Areas.DB, Areas.CT, Areas.TM]
        expected_list = []
        for i in range(0, items_count):
            item = S7DataItem()
            item.Area = ctypes.c_int32(areas[i].value)
            wordlen = WordLen.Byte
            item.WordLen = ctypes.c_int32(wordlen.value)
            item.DBNumber = ctypes.c_int32(1)
            item.Start = ctypes.c_int32(0)
            item.Amount = ctypes.c_int32(4)
            data = (i + 1).to_bytes(1, byteorder='big') * 4
            array_class = ctypes.c_uint8 * len(data)
            cdata = array_class.from_buffer_copy(data)
            item.pData = ctypes.cast(cdata, ctypes.POINTER(array_class)).contents
            items.append(item)
            expected_list.append(data)
        result = self.client.write_multi_vars(items)
        self.assertEqual(0, result)
        self.assertEqual(expected_list[0], self.client.db_read(db_number=1, start=0, size=4))
        self.assertEqual(expected_list[1], self.client.ct_read(0, 2))
        self.assertEqual(expected_list[2], self.client.tm_read(0, 2))

    @unittest.skipIf(platform.system() in ['Windows', 'Darwin'], 'Access Violation error')
    def test_set_as_callback(self):
        expected = b"\x11\x11"
        self.callback_counter = 0
        cObj = ctypes.cast(ctypes.pointer(ctypes.py_object(self)), S7Object)

        def callback(FUsrPtr, JobOp, response):
            self = ctypes.cast(FUsrPtr, ctypes.POINTER(ctypes.py_object)).contents.value
            self.callback_counter += 1

        cfunc_type = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.POINTER(S7Object), ctypes.c_int, ctypes.c_int)
        self.client.set_as_callback(cfunc_type(callback), cObj)
        self.client.as_ct_write(0, 1, bytearray(expected))

        self._as_check_loop()
        self.assertEqual(expected, self.client.ct_read(0, 1))
        self.assertEqual(1, self.callback_counter)


class TestClientBeforeConnect(unittest.TestCase):
    """
    Test suite of items that should run without an open connection.
    """

    def setUp(self):
        self.client = snap7.client.Client()

    def test_set_param(self):
        values = (
            (snap7.types.RemotePort, 1102),
            (snap7.types.PingTimeout, 800),
            (snap7.types.SendTimeout, 15),
            (snap7.types.RecvTimeout, 3500),
            (snap7.types.SrcRef, 128),
            (snap7.types.DstRef, 128),
            (snap7.types.SrcTSap, 128),
            (snap7.types.PDURequest, 470),
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

    @mock.patch('snap7.client.byref')
    def test_gc(self, byref_mock):
        client = snap7.client.Client()
        client._pointer = 10
        del client
        gc.collect()
        self.mocklib.Cli_Destroy.assert_called_once()


if __name__ == '__main__':
    unittest.main()
