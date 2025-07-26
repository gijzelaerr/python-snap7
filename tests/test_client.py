import gc
import logging
import struct
import time
from typing import Tuple

import pytest
import unittest
from ctypes import (
    c_uint8,
    c_uint16,
    c_int32,
    c_int,
    POINTER,
    sizeof,
    create_string_buffer,
    cast,
    pointer,
    Array,
)
from datetime import datetime, timedelta, timezone
from multiprocessing import Process
from unittest import mock
from typing import cast as typing_cast

from snap7.util import get_real, get_int, set_int
from snap7.error import check_error
from snap7.server import mainloop
from snap7.client import Client
from snap7.type import (
    S7DataItem,
    S7SZL,
    S7SZLList,
    buffer_type,
    buffer_size,
    Area,
    WordLen,
    Block,
    Parameter,
    CDataArrayType,
)

logging.basicConfig(level=logging.WARNING)

ip = "127.0.0.1"
tcpport = 1102
db_number = 1
rack = 1
slot = 1


def _prepare_as_read_area(area: Area, size: int) -> Tuple[WordLen, CDataArrayType]:
    wordlen = area.wordlen()
    usrdata = (wordlen.ctype * size)()
    return wordlen, usrdata


def _prepare_as_write_area(area: Area, data: bytearray) -> Tuple[WordLen, CDataArrayType]:
    if area not in Area:
        raise ValueError(f"{area} is not implemented in types")
    elif area == Area.TM:
        word_len = WordLen.Timer
    elif area == Area.CT:
        word_len = WordLen.Counter
    else:
        word_len = WordLen.Byte
    type_ = WordLen.Byte.ctype
    cdata = (type_ * len(data)).from_buffer_copy(data)
    return word_len, cdata


# noinspection PyTypeChecker,PyCallingNonCallable
@pytest.mark.client
class TestClient(unittest.TestCase):
    process = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.process = Process(target=mainloop)
        cls.process.start()
        time.sleep(2)  # wait for server to start

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.process:
            cls.process.terminate()
            cls.process.join(1)
            if cls.process.is_alive():
                cls.process.kill()

    def setUp(self) -> None:
        self.client = Client()
        self.client.connect(ip, rack, slot, tcpport)

    def tearDown(self) -> None:
        self.client.disconnect()
        self.client.destroy()

    def test_db_read(self) -> None:
        size = 40
        start = 0
        db = 1
        data = bytearray(40)
        self.client.db_write(db_number=db, start=start, data=data)
        result = self.client.db_read(db_number=db, start=start, size=size)
        self.assertEqual(data, result)

    def test_db_write(self) -> None:
        size = 40
        data = bytearray(size)
        self.client.db_write(db_number=1, start=0, data=data)

    def test_db_get(self) -> None:
        self.client.db_get(db_number=db_number)

    def test_read_multi_vars(self) -> None:
        db = 1

        # build and write test values
        test_value_1 = 129.5
        test_bytes_1 = bytearray(struct.pack(">f", test_value_1))
        self.client.db_write(db, 0, test_bytes_1)

        test_value_2 = -129.5
        test_bytes_2 = bytearray(struct.pack(">f", test_value_2))
        self.client.db_write(db, 4, test_bytes_2)

        test_value_3 = 123
        test_bytes_3 = bytearray([0, 0])
        set_int(test_bytes_3, 0, test_value_3)
        self.client.db_write(db, 8, test_bytes_3)

        test_values = [test_value_1, test_value_2, test_value_3]

        # build up our requests
        data_items = (S7DataItem * 3)()

        # build up our requests
        data_items = (S7DataItem * 3)()

        data_items[0].Area = c_int32(Area.DB.value)
        data_items[0].WordLen = c_int32(WordLen.Byte.value)
        data_items[0].Result = c_int32(0)
        data_items[0].DBNumber = c_int32(db)
        data_items[0].Start = c_int32(0)
        data_items[0].Amount = c_int32(4)  # reading a REAL, 4 bytes

        data_items[1].Area = c_int32(Area.DB.value)
        data_items[1].WordLen = c_int32(WordLen.Byte.value)
        data_items[1].Result = c_int32(0)
        data_items[1].DBNumber = c_int32(db)
        data_items[1].Start = c_int32(4)
        data_items[1].Amount = c_int32(4)  # reading a REAL, 4 bytes

        data_items[2].Area = c_int32(Area.DB.value)
        data_items[2].WordLen = c_int32(WordLen.Byte.value)
        data_items[2].Result = c_int32(0)
        data_items[2].DBNumber = c_int32(db)
        data_items[2].Start = c_int32(8)
        data_items[2].Amount = c_int32(2)  # reading an INT, 2 bytes

        # create buffers to receive the data
        # use the Amount attribute on each item to size the buffer
        for di in data_items:
            # create the buffer
            dataBuffer = create_string_buffer(di.Amount)
            # get a pointer to the buffer
            pBuffer = cast(pointer(dataBuffer), POINTER(c_uint8))
            di.pData = pBuffer

        result, data_items = self.client.read_multi_vars(data_items)

        result_values = []
        # function to cast bytes to match data_types[] above
        byte_to_value = [get_real, get_real, get_int]

        # unpack and test the result of each read
        for i, di in enumerate(data_items):
            btv = byte_to_value[i]
            value = btv(di.pData, 0)
            result_values.append(value)

        self.assertEqual(result_values[0], test_values[0])
        self.assertEqual(result_values[1], test_values[1])
        self.assertEqual(result_values[2], test_values[2])

    @unittest.skip("Not implemented by the snap7 server")
    def test_upload(self) -> None:
        """
        This is not implemented by the server and will always raise a RuntimeError (security error)
        """
        self.assertRaises(RuntimeError, self.client.upload, db_number)

    @unittest.skip("Not implemented by the snap7 server")
    def test_as_upload(self) -> None:
        """
        This is not implemented by the server and will always raise a RuntimeError (security error)
        """
        _buffer = typing_cast(Array[c_int32], buffer_type())
        size = sizeof(_buffer)
        self.client.as_upload(1, _buffer, size)
        self.assertRaises(RuntimeError, self.client.wait_as_completion, 500)

    @unittest.skip("Not implemented by the snap7 server")
    def test_download(self) -> None:
        """
        This is not implemented by the server and will always raise a RuntimeError (security error)
        """
        data = bytearray([0b11111111])
        self.client.download(block_num=0, data=data)

    def test_read_area(self) -> None:
        amount = 1
        start = 1

        # Test read_area with a DB
        area = Area.DB
        dbnumber = 1
        data = bytearray(b"\x11")
        self.client.write_area(area, dbnumber, start, data)
        res = self.client.read_area(area, dbnumber, start, amount)
        self.assertEqual(data, bytearray(res))

        # Test read_area with a TM
        area = Area.TM
        dbnumber = 0
        data = bytearray(b"\x12\x34")
        self.client.write_area(area, dbnumber, start, data)
        res = self.client.read_area(area, dbnumber, start, amount)
        self.assertEqual(data, bytearray(res))

        # Test read_area with a CT
        area = Area.CT
        dbnumber = 0
        data = bytearray(b"\x13\x35")
        self.client.write_area(area, dbnumber, start, data)
        res = self.client.read_area(area, dbnumber, start, amount)
        self.assertEqual(data, bytearray(res))

    def test_write_area(self) -> None:
        # Test write area with a DB
        area = Area.DB
        dbnumber = 1
        start = 1
        data = bytearray(b"\x11")
        self.client.write_area(area, dbnumber, start, data)
        res = self.client.read_area(area, dbnumber, start, 1)
        self.assertEqual(data, bytearray(res))

        # Test write area with a TM
        area = Area.TM
        dbnumber = 0
        timer = bytearray(b"\x12\x00")
        self.client.write_area(area, dbnumber, start, timer)
        res = self.client.read_area(area, dbnumber, start, 1)
        self.assertEqual(timer, bytearray(res))

        # Test write area with a CT
        area = Area.CT
        dbnumber = 0
        timer = bytearray(b"\x13\x00")
        self.client.write_area(area, dbnumber, start, timer)
        res = self.client.read_area(area, dbnumber, start, 1)
        self.assertEqual(timer, bytearray(res))

    def test_list_blocks(self) -> None:
        self.client.list_blocks()

    def test_list_blocks_of_type(self) -> None:
        self.client.list_blocks_of_type(Block.DB, 10)

    def test_get_block_info(self) -> None:
        self.client.get_block_info(Block.DB, 1)

    def test_get_cpu_state(self) -> None:
        self.client.get_cpu_state()

    def test_set_session_password(self) -> None:
        password = "abcdefgh"  # noqa: S105
        self.client.set_session_password(password)

    def test_clear_session_password(self) -> None:
        self.client.clear_session_password()

    def test_set_connection_params(self) -> None:
        self.client.set_connection_params("10.0.0.2", 10, 10)

    def test_set_connection_type(self) -> None:
        self.client.set_connection_type(1)
        self.client.set_connection_type(2)
        self.client.set_connection_type(3)
        self.client.set_connection_type(20)

    def test_get_connected(self) -> None:
        self.client.get_connected()

    def test_ab_read(self) -> None:
        start = 1
        size = 1
        data = bytearray(size)
        self.client.ab_write(start=start, data=data)
        self.client.ab_read(start=start, size=size)

    def test_ab_write(self) -> None:
        start = 1
        size = 10
        data = bytearray(size)
        result = self.client.ab_write(start=start, data=data)
        self.assertEqual(0, result)

    def test_as_ab_read(self) -> None:
        expected = b"\x10\x01"
        self.client.ab_write(0, bytearray(expected))

        type_ = WordLen.Byte.ctype
        buffer = (type_ * 2)()
        self.client.as_ab_read(0, 2, buffer)
        result = self.client.wait_as_completion(500)
        self.assertEqual(0, result)
        self.assertEqual(expected, bytearray(buffer))

    def test_as_ab_write(self) -> None:
        data = b"\x01\x11"
        response = self.client.as_ab_write(0, bytearray(data))
        result = self.client.wait_as_completion(500)
        self.assertEqual(0, response)
        self.assertEqual(0, result)
        self.assertEqual(data, self.client.ab_read(0, 2))

    def test_compress(self) -> None:
        time_ = 1000
        self.client.compress(time_)

    def test_as_compress(self) -> None:
        time_ = 1000
        response = self.client.as_compress(time_)
        result = self.client.wait_as_completion(500)
        self.assertEqual(0, response)
        self.assertEqual(0, result)

    def test_set_param(self) -> None:
        values = (
            (Parameter.PingTimeout, 800),
            (Parameter.SendTimeout, 15),
            (Parameter.RecvTimeout, 3500),
            (Parameter.SrcRef, 128),
            (Parameter.DstRef, 128),
            (Parameter.SrcTSap, 128),
            (Parameter.PDURequest, 470),
        )
        for param, value in values:
            self.client.set_param(param, value)

        self.assertRaises(Exception, self.client.set_param, Parameter.RemotePort, 1)

    def test_get_param(self) -> None:
        expected = (
            (Parameter.RemotePort, tcpport),
            (Parameter.PingTimeout, 750),
            (Parameter.SendTimeout, 10),
            (Parameter.RecvTimeout, 3000),
            (Parameter.SrcRef, 256),
            (Parameter.DstRef, 0),
            (Parameter.SrcTSap, 256),
            (Parameter.PDURequest, 480),
        )
        for param, value in expected:
            self.assertEqual(self.client.get_param(param), value)

        non_client = (
            Parameter.LocalPort,
            Parameter.WorkInterval,
            Parameter.MaxClients,
            Parameter.BSendTimeout,
            Parameter.BRecvTimeout,
            Parameter.RecoveryTime,
            Parameter.KeepAliveTime,
        )

        # invalid param for client
        for param in non_client:
            self.assertRaises(Exception, self.client.get_param, non_client)

    def test_as_copy_ram_to_rom(self) -> None:
        response = self.client.as_copy_ram_to_rom(timeout=2)
        self.client.wait_as_completion(2000)
        self.assertEqual(0, response)

    def test_as_ct_read(self) -> None:
        # Cli_AsCTRead
        expected = b"\x10\x01"
        self.client.ct_write(0, 1, bytearray(expected))
        type_ = WordLen.Counter.ctype
        buffer = (type_ * 1)()
        self.client.as_ct_read(0, 1, buffer)
        self.client.wait_as_completion(500)
        self.assertEqual(expected, bytearray(buffer))

    def test_as_ct_write(self) -> None:
        # Cli_CTWrite
        data = b"\x01\x11"
        response = self.client.as_ct_write(0, 1, bytearray(data))
        result = self.client.wait_as_completion(500)
        self.assertEqual(0, response)
        self.assertEqual(0, result)
        self.assertEqual(data, self.client.ct_read(0, 1))

    def test_as_db_fill(self) -> None:
        filler = 31
        expected = bytearray(filler.to_bytes(1, byteorder="big") * 100)
        self.client.db_fill(1, filler)
        self.client.wait_as_completion(500)
        self.assertEqual(expected, self.client.db_read(1, 0, 100))

    def test_as_db_get(self) -> None:
        _buffer = typing_cast(Array[c_int], buffer_type())
        self.client.as_db_get(db_number, _buffer, buffer_size)
        self.client.wait_as_completion(500)
        result = bytearray(_buffer)[:buffer_size]
        self.assertEqual(buffer_size, len(result))

    def test_as_db_read(self) -> None:
        size = 40
        start = 0
        db = 1
        expected = bytearray(40)
        self.client.db_write(db_number=db, start=start, data=expected)

        type_ = WordLen.Byte.ctype
        data = (type_ * size)()
        self.client.as_db_read(db, start, size, data)
        self.client.wait_as_completion(500)
        self.assertEqual(data, expected)

    def test_as_db_write(self) -> None:
        size = 40
        data = bytearray(size)
        type_ = WordLen.Byte.ctype
        size = len(data)
        result = (type_ * size).from_buffer_copy(data)
        self.client.as_db_write(db_number=1, start=0, size=size, data=result)
        self.client.wait_as_completion(500)
        self.assertEqual(data, result)

    @unittest.skip("Not implemented by the snap7 server")
    def test_as_download(self) -> None:
        data = bytearray(128)
        self.client.as_download(block_num=-1, data=data)

    def test_plc_stop(self) -> None:
        self.client.plc_stop()

    def test_plc_hot_start(self) -> None:
        self.client.plc_hot_start()

    def test_plc_cold_start(self) -> None:
        self.client.plc_cold_start()

    def test_get_pdu_length(self) -> None:
        pduRequested = self.client.get_param(Parameter.PDURequest)
        pduSize = self.client.get_pdu_length()
        self.assertEqual(pduSize, pduRequested)

    def test_get_cpu_info(self) -> None:
        expected = (
            ("ModuleTypeName", "CPU 315-2 PN/DP"),
            ("SerialNumber", "S C-C2UR28922012"),
            ("ASName", "SNAP7-SERVER"),
            ("Copyright", "Original Siemens Equipment"),
            ("ModuleName", "CPU 315-2 PN/DP"),
        )
        cpuInfo = self.client.get_cpu_info()
        for param, value in expected:
            self.assertEqual(getattr(cpuInfo, param).decode("utf-8"), value)

    def test_db_write_with_byte_literal_does_not_throw(self) -> None:
        mock_write = mock.MagicMock()
        mock_write.return_value = None
        original = self.client._lib.Cli_DBWrite
        self.client._lib.Cli_DBWrite = mock_write
        data = b"\xde\xad\xbe\xef"

        try:
            self.client.db_write(db_number=1, start=0, data=bytearray(data))
        except TypeError as e:
            self.fail(str(e))
        finally:
            self.client._lib.Cli_DBWrite = original

    def test_get_plc_time(self) -> None:
        self.assertAlmostEqual(datetime.now().replace(microsecond=0), self.client.get_plc_datetime(), delta=timedelta(seconds=1))

    def test_set_plc_datetime(self) -> None:
        new_dt = datetime(2011, 1, 1, 1, 1, 1, 0)
        self.client.set_plc_datetime(new_dt)
        # Can't actually set datetime in emulated PLC, get_plc_datetime always returns system time.
        # self.assertEqual(new_dt, self.client.get_plc_datetime())

    def test_wait_as_completion_pass(self, timeout: int = 1000) -> None:
        # Cli_WaitAsCompletion
        # prepare Server with values
        area = Area.DB
        dbnumber = 1
        size = 1
        start = 1
        data = bytearray(size)
        self.client.write_area(area, dbnumber, start, data)
        # start as_request and test
        wordlen, usrdata = _prepare_as_read_area(area, size)
        self.client.as_read_area(area, dbnumber, start, size, wordlen, usrdata)
        self.client.wait_as_completion(timeout)
        self.assertEqual(bytearray(usrdata), data)

    def test_wait_as_completion_timeout(self, timeout: int = 0, tries: int = 500) -> None:
        # Cli_WaitAsCompletion
        # prepare Server
        area = Area.DB
        dbnumber = 1
        size = 1
        start = 1
        wordlen, data = _prepare_as_read_area(area, size)
        self.client.write_area(area, dbnumber, start, bytearray(data))
        # start as_request and wait for zero seconds to try trigger timeout
        for i in range(tries):
            self.client.as_read_area(area, dbnumber, start, size, wordlen, data)
            res = None
            try:
                res = self.client.wait_as_completion(timeout)
                check_error(res)
            except RuntimeError as s7_err:
                if not s7_err.args[0] == b"CLI : Job Timeout":
                    self.fail(f"While waiting another error appeared: {s7_err}")
                # Wait for a thread to finish
                time.sleep(0.1)
                return
            except BaseException:
                self.fail(f"While waiting another error appeared:>>>>>>>> {res}")

        self.fail(
            f"After {tries} tries, no timout could be envoked by snap7. Either tests are passing to fast or"
            f"a problem is existing in the method. Fail test."
        )

    def test_check_as_completion(self, timeout: int = 5) -> None:
        # Cli_CheckAsCompletion
        check_status = c_int(-1)
        pending_checked = False
        # preparing Server values
        data = bytearray(b"\x01\xff")
        size = len(data)
        area = Area.DB
        db = 1
        start = 1
        self.client.write_area(area, db, start, data)

        # start as_request and test
        wordlen, cdata = _prepare_as_read_area(area, size)
        self.client.as_read_area(area, db, start, size, wordlen, cdata)
        for _ in range(10):
            self.client.check_as_completion(check_status)
            if check_status.value == 0:
                self.assertEqual(data, bytearray(cdata))
                break
            pending_checked = True
            time.sleep(1)
        else:
            self.fail(f"TimeoutError - Process pends for more than {timeout} seconds")
        if pending_checked is False:
            logging.warning("Pending was never reached, because Server was to fast," " but request to server was successfull.")

    def test_as_read_area(self) -> None:
        amount = 1
        start = 1

        # Test read_area with a DB
        area = Area.DB
        dbnumber = 1
        data = bytearray(b"\x11")
        self.client.write_area(area, dbnumber, start, data)
        wordlen, usrdata = _prepare_as_read_area(area, amount)
        self.client.as_read_area(area, dbnumber, start, amount, wordlen, usrdata)
        self.client.wait_as_completion(1000)
        self.assertEqual(bytearray(usrdata), data)

        # Test read_area with a TM
        area = Area.TM
        dbnumber = 0
        data = bytearray(b"\x12\x34")
        self.client.write_area(area, dbnumber, start, data)
        wordlen, usrdata = _prepare_as_read_area(area, amount)
        self.client.as_read_area(area, dbnumber, start, amount, wordlen, usrdata)
        self.client.wait_as_completion(1000)
        self.assertEqual(bytearray(usrdata), data)

        # Test read_area with a CT
        area = Area.CT
        dbnumber = 0
        data = bytearray(b"\x13\x35")
        self.client.write_area(area, dbnumber, start, data)
        wordlen, usrdata = _prepare_as_read_area(area, amount)
        self.client.as_read_area(area, dbnumber, start, amount, wordlen, usrdata)
        self.client.wait_as_completion(1000)
        self.assertEqual(bytearray(usrdata), data)

    def test_as_write_area(self) -> None:
        # Test write area with a DB
        area = Area.DB
        dbnumber = 1
        size = 1
        start = 1
        data = bytearray(b"\x11")
        wordlen, cdata = _prepare_as_write_area(area, data)
        self.client.as_write_area(area, dbnumber, start, size, wordlen, cdata)
        self.client.wait_as_completion(1000)
        res = self.client.read_area(area, dbnumber, start, 1)
        self.assertEqual(data, bytearray(res))

        # Test write area with a TM
        area = Area.TM
        dbnumber = 0
        size = 2
        timer = bytearray(b"\x12\x00")
        wordlen, cdata = _prepare_as_write_area(area, timer)
        self.client.as_write_area(area, dbnumber, start, size, wordlen, cdata)
        self.client.wait_as_completion(1000)
        res2 = self.client.read_area(area, dbnumber, start, 1)
        self.assertEqual(timer, bytearray(res2))

        # Test write area with a CT
        area = Area.CT
        dbnumber = 0
        size = 2
        timer = bytearray(b"\x13\x00")
        wordlen, cdata = _prepare_as_write_area(area, timer)
        self.client.as_write_area(area, dbnumber, start, size, wordlen, cdata)
        self.client.wait_as_completion(1000)
        res3 = self.client.read_area(area, dbnumber, start, 1)
        self.assertEqual(timer, bytearray(res3))

    def test_as_eb_read(self) -> None:
        # Cli_AsEBRead
        type_ = WordLen.Byte.ctype
        buffer = (type_ * 1)()
        response = self.client.as_eb_read(0, 1, buffer)
        self.assertEqual(0, response)
        self.assertRaises(RuntimeError, self.client.wait_as_completion, 500)

    def test_as_eb_write(self) -> None:
        # Cli_AsEBWrite
        response = self.client.as_eb_write(0, 1, bytearray(b"\x00"))
        self.assertEqual(0, response)
        self.assertRaises(RuntimeError, self.client.wait_as_completion, 500)

    def test_as_full_upload(self) -> None:
        # Cli_AsFullUpload
        self.client.as_full_upload(Block.DB, 1)
        self.assertRaises(RuntimeError, self.client.wait_as_completion, 500)

    def test_as_list_blocks_of_type(self) -> None:
        data = typing_cast(Array[c_int], (c_uint16 * 10)())
        self.client.as_list_blocks_of_type(Block.DB, data, 0)
        self.assertRaises(RuntimeError, self.client.wait_as_completion, 500)

    def test_as_mb_read(self) -> None:
        # Cli_AsMBRead
        type_ = WordLen.Byte.ctype
        data = (type_ * 1)()
        self.client.as_mb_read(0, 1, data)
        bytearray(data)
        self.assertRaises(RuntimeError, self.client.wait_as_completion, 500)

    def test_as_mb_write(self) -> None:
        # Cli_AsMBWrite
        response = self.client.as_mb_write(0, 1, bytearray(b"\x00"))
        self.assertEqual(0, response)
        self.assertRaises(RuntimeError, self.client.wait_as_completion, 500)

    def test_as_read_szl(self) -> None:
        # Cli_AsReadSZL
        expected = b"S C-C2UR28922012\x00\x00\x00\x00\x00\x00\x00\x00"
        ssl_id = 0x011C
        index = 0x0005
        s7_szl = S7SZL()
        self.client.as_read_szl(ssl_id, index, s7_szl, sizeof(s7_szl))
        self.client.wait_as_completion(100)
        result = bytes(s7_szl.Data)[2:26]
        self.assertEqual(expected, result)

    def test_as_read_szl_list(self) -> None:
        expected = b"\x00\x00\x00\x0f\x02\x00\x11\x00\x11\x01\x11\x0f\x12\x00\x12\x01"
        szl_list = S7SZLList()
        items_count = sizeof(szl_list)
        self.client.as_read_szl_list(szl_list, items_count)
        self.client.wait_as_completion(500)
        result = bytearray(szl_list.List)[:16]
        self.assertEqual(expected, result)

    def test_as_tm_read(self) -> None:
        expected = b"\x10\x01"
        self.client.tm_write(0, 1, bytearray(expected))
        type_ = WordLen.Timer.ctype
        buffer = (type_ * 1)()
        self.client.as_tm_read(0, 1, buffer)
        self.client.wait_as_completion(500)
        self.assertEqual(expected, bytearray(buffer))

    def test_as_tm_write(self) -> None:
        data = b"\x10\x01"
        response = self.client.as_tm_write(0, 1, bytearray(data))
        result = self.client.wait_as_completion(500)
        self.assertEqual(0, response)
        self.assertEqual(0, result)
        self.assertEqual(data, self.client.tm_read(0, 1))

    def test_copy_ram_to_rom(self) -> None:
        # Cli_CopyRamToRom
        self.assertEqual(0, self.client.copy_ram_to_rom(timeout=2))

    def test_ct_read(self) -> None:
        # Cli_CTRead
        data = b"\x10\x01"
        self.client.ct_write(0, 1, bytearray(data))
        result = self.client.ct_read(0, 1)
        self.assertEqual(data, result)

    def test_ct_write(self) -> None:
        # Cli_CTWrite
        data = b"\x01\x11"
        self.assertEqual(0, self.client.ct_write(0, 1, bytearray(data)))
        self.assertRaises(ValueError, self.client.ct_write, 0, 2, bytes(1))

    def test_db_fill(self) -> None:
        # Cli_DBFill
        filler = 31
        expected = bytearray(filler.to_bytes(1, byteorder="big") * 100)
        self.client.db_fill(1, filler)
        self.assertEqual(expected, self.client.db_read(1, 0, 100))

    def test_eb_read(self) -> None:
        # Cli_EBRead
        self.client._lib.Cli_EBRead = mock.Mock(return_value=0)
        response = self.client.eb_read(0, 1)
        self.assertTrue(isinstance(response, bytearray))
        self.assertEqual(1, len(response))

    def test_eb_write(self) -> None:
        # Cli_EBWrite
        self.client._lib.Cli_EBWrite = mock.Mock(return_value=0)
        response = self.client.eb_write(0, 1, bytearray(b"\x00"))
        self.assertEqual(0, response)

    def test_error_text(self) -> None:
        # Cli_ErrorText
        CPU_INVALID_PASSWORD = 0x01E00000
        CPU_INVLID_VALUE = 0x00D00000
        CANNOT_CHANGE_PARAM = 0x02600000
        self.assertEqual("CPU : Invalid password", self.client.error_text(CPU_INVALID_PASSWORD))
        self.assertEqual("CPU : Invalid value supplied", self.client.error_text(CPU_INVLID_VALUE))
        self.assertEqual("CLI : Cannot change this param now", self.client.error_text(CANNOT_CHANGE_PARAM))

    def test_get_cp_info(self) -> None:
        # Cli_GetCpInfo
        result = self.client.get_cp_info()
        self.assertEqual(2048, result.MaxPduLength)
        self.assertEqual(0, result.MaxConnections)
        self.assertEqual(1024, result.MaxMpiRate)
        self.assertEqual(0, result.MaxBusRate)

    def test_get_exec_time(self) -> None:
        # Cli_GetExecTime
        response = self.client.get_exec_time()
        self.assertTrue(isinstance(response, int))

    def test_get_last_error(self) -> None:
        # Cli_GetLastError
        self.assertEqual(0, self.client.get_last_error())

    def test_get_order_code(self) -> None:
        # Cli_GetOrderCode
        expected = b"6ES7 315-2EH14-0AB0 "
        result = self.client.get_order_code()
        self.assertEqual(expected, result.OrderCode)

    def test_get_protection(self) -> None:
        # Cli_GetProtection
        result = self.client.get_protection()
        self.assertEqual(1, result.sch_schal)
        self.assertEqual(0, result.sch_par)
        self.assertEqual(1, result.sch_rel)
        self.assertEqual(2, result.bart_sch)
        self.assertEqual(0, result.anl_sch)

    def test_get_pg_block_info(self) -> None:
        valid_db_block = (
            b"pp\x01\x01\x05\n\x00c\x00\x00\x00t\x00\x00\x00\x00\x01\x8d\xbe)2\xa1\x01"
            b"\x85V\x1f2\xa1\x00*\x00\x00\x00\x00\x00\x02\x01\x0f\x05c\x00#\x00\x00\x00"
            b"\x11\x04\x10\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01"
            b"\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x01\x04\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        )
        block_info = self.client.get_pg_block_info(bytearray(valid_db_block))
        self.assertEqual(10, block_info.BlkType)
        self.assertEqual(99, block_info.BlkNumber)
        self.assertEqual(2752512, block_info.SBBLength)
        self.assertEqual(
            bytes((datetime(2019, 6, 27, tzinfo=timezone.utc).astimezone().strftime("%Y/%m/%d")), encoding="utf-8"),
            block_info.CodeDate,
        )
        self.assertEqual(
            bytes((datetime(2019, 6, 27, tzinfo=timezone.utc).astimezone().strftime("%Y/%m/%d")), encoding="utf-8"),
            block_info.IntfDate,
        )

    def test_iso_exchange_buffer(self) -> None:
        # Cli_IsoExchangeBuffer
        self.client.db_write(1, 0, bytearray(b"\x11"))
        # PDU read DB1 1.0 BYTE
        data = b"\x32\x01\x00\x00\x01\x00\x00\x0e\x00\x00\x04\x01\x12\x0a\x10\x02\x00\x01\x00\x01\x84\x00\x00\x00"
        # PDU response
        expected = bytearray(b"2\x03\x00\x00\x01\x00\x00\x02\x00\x05\x00\x00\x04\x01\xff\x04\x00\x08\x11")
        self.assertEqual(expected, self.client.iso_exchange_buffer(bytearray(data)))

    def test_mb_read(self) -> None:
        # Cli_MBRead
        self.client._lib.Cli_MBRead = mock.Mock(return_value=0)
        response = self.client.mb_read(0, 10)
        self.assertTrue(isinstance(response, bytearray))
        self.assertEqual(10, len(response))

    def test_mb_write(self) -> None:
        # Cli_MBWrite
        self.client._lib.Cli_MBWrite = mock.Mock(return_value=0)
        response = self.client.mb_write(0, 1, bytearray(b"\x00"))
        self.assertEqual(0, response)

    def test_read_szl(self) -> None:
        # read_szl_partial_list
        expected_number_of_records = 10
        expected_length_of_record = 34
        ssl_id = 0x001C
        response = self.client.read_szl(ssl_id)
        self.assertEqual(expected_number_of_records, response.Header.NDR)
        self.assertEqual(expected_length_of_record, response.Header.LengthDR)
        # read_szl_single_data_record
        expected = b"S C-C2UR28922012\x00\x00\x00\x00\x00\x00\x00\x00"
        ssl_id = 0x011C
        index = 0x0005
        response = self.client.read_szl(ssl_id, index)
        result = bytes(response.Data)[2:26]
        self.assertEqual(expected, result)
        # read_szl_order_number
        expected = b"6ES7 315-2EH14-0AB0 "
        ssl_id = 0x0111
        index = 0x0001
        response = self.client.read_szl(ssl_id, index)
        result = bytes(response.Data[2:22])
        self.assertEqual(expected, result)
        # read_szl_invalid_id
        ssl_id = 0xFFFF
        index = 0xFFFF
        self.assertRaises(RuntimeError, self.client.read_szl, ssl_id)
        self.assertRaises(RuntimeError, self.client.read_szl, ssl_id, index)

    def test_read_szl_list(self) -> None:
        # Cli_ReadSZLList
        expected = b"\x00\x00\x00\x0f\x02\x00\x11\x00\x11\x01\x11\x0f\x12\x00\x12\x01"
        result = self.client.read_szl_list()
        self.assertEqual(expected, result[:16])

    def test_set_plc_system_datetime(self) -> None:
        # Cli_SetPlcSystemDateTime
        self.assertEqual(0, self.client.set_plc_system_datetime())

    def test_tm_read(self) -> None:
        # Cli_TMRead
        data = b"\x10\x01"
        self.client.tm_write(0, 1, bytearray(data))
        result = self.client.tm_read(0, 1)
        self.assertEqual(data, result)

    def test_tm_write(self) -> None:
        # Cli_TMWrite
        data = b"\x10\x01"
        self.assertEqual(0, self.client.tm_write(0, 1, bytearray(data)))
        self.assertEqual(data, self.client.tm_read(0, 1))
        self.assertRaises(RuntimeError, self.client.tm_write, 0, 100, bytes(200))
        self.assertRaises(ValueError, self.client.tm_write, 0, 2, bytes(2))

    def test_write_multi_vars(self) -> None:
        # Cli_WriteMultiVars
        items_count = 3
        items = []
        areas = [Area.DB, Area.CT, Area.TM]
        expected_list = []
        for i in range(items_count):
            item = S7DataItem()
            item.Area = c_int32(areas[i].value)
            wordlen = WordLen.Byte
            item.WordLen = c_int32(wordlen.value)
            item.DBNumber = c_int32(1)
            item.Start = c_int32(0)
            item.Amount = c_int32(4)
            data = (i + 1).to_bytes(1, byteorder="big") * 4
            array_class = c_uint8 * len(data)
            cdata = array_class.from_buffer_copy(data)
            item.pData = cast(cdata, POINTER(array_class)).contents
            items.append(item)
            expected_list.append(data)
        result = self.client.write_multi_vars(items)
        self.assertEqual(0, result)
        self.assertEqual(expected_list[0], self.client.db_read(db_number=1, start=0, size=4))
        self.assertEqual(expected_list[1], self.client.ct_read(0, 2))
        self.assertEqual(expected_list[2], self.client.tm_read(0, 2))

    def test_set_as_callback(self) -> None:
        def event_call_back(op_code: int, op_result: int) -> None:
            logging.info(f"callback event: {op_code} op_result: {op_result}")

        self.client.set_as_callback(event_call_back)


@pytest.mark.client
class TestClientBeforeConnect(unittest.TestCase):
    """
    Test suite of items that should run without an open connection.
    """

    def setUp(self) -> None:
        self.client = Client()

    def test_set_param(self) -> None:
        values = (
            (Parameter.RemotePort, 1102),
            (Parameter.PingTimeout, 800),
            (Parameter.SendTimeout, 15),
            (Parameter.RecvTimeout, 3500),
            (Parameter.SrcRef, 128),
            (Parameter.DstRef, 128),
            (Parameter.SrcTSap, 128),
            (Parameter.PDURequest, 470),
        )
        for param, value in values:
            self.client.set_param(param, value)


@pytest.mark.client
class TestLibraryIntegration(unittest.TestCase):
    def setUp(self) -> None:
        # replace the function load_library with a mock
        self.loadlib_patch = mock.patch("snap7.client.load_library")
        self.loadlib_func = self.loadlib_patch.start()

        # have load_library return another mock
        self.mocklib = mock.MagicMock()
        self.loadlib_func.return_value = self.mocklib

        # have the Cli_Create of the mock return None
        self.mocklib.Cli_Create.return_value = None
        self.mocklib.Cli_Destroy.return_value = None

    def tearDown(self) -> None:
        # restore load_library
        self.loadlib_patch.stop()

    def test_create(self) -> None:
        Client()
        self.mocklib.Cli_Create.assert_called_once()

    def test_gc(self) -> None:
        client = Client()
        del client
        gc.collect()
        self.mocklib.Cli_Destroy.assert_called_once()

    def test_context_manager(self) -> None:
        with Client() as _:
            pass
        self.mocklib.Cli_Destroy.assert_called_once()


if __name__ == "__main__":
    unittest.main()
