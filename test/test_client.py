import ctypes
import gc
import logging
import struct
import time
import unittest
from datetime import datetime
from unittest import mock

import snap7
from snap7 import util
from snap7.exceptions import Snap7Exception
from snap7.types import S7AreaDB, S7WLByte, S7DataItem
import pytest

logging.basicConfig(level=logging.WARNING)

ip = '127.0.0.1'
tcpport = 1102
db_number = 1
rack = 1
slot = 1


def test_db_read(testclient, testserver):
    size = 40
    start = 0
    db = 1
    data = bytearray(40)
    testclient.db_write(db_number=db, start=start, data=data)
    result = testclient.db_read(db_number=db, start=start, size=size)
    assert data == result


def test_db_write(testclient, testserver):
    size = 40
    data = bytearray(size)
    testclient.db_write(db_number=1, start=0, data=data)


def test_db_get(testclient, testserver):
    testclient.db_get(db_number=db_number)


def test_read_multi_vars(testclient, testserver):
    db = 1

    # build and write test values
    test_value_1 = 129.5
    test_bytes_1 = bytearray(struct.pack('>f', test_value_1))
    testclient.db_write(db, 0, test_bytes_1)

    test_value_2 = -129.5
    test_bytes_2 = bytearray(struct.pack('>f', test_value_2))
    testclient.db_write(db, 4, test_bytes_2)

    test_value_3 = 123
    test_bytes_3 = bytearray([0, 0])
    util.set_int(test_bytes_3, 0, test_value_3)
    testclient.db_write(db, 8, test_bytes_3)

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

    result, data_items = testclient.read_multi_vars(data_items)

    result_values = []
    # function to cast bytes to match data_types[] above
    byte_to_value = [util.get_real, util.get_real, util.get_int]

    # unpack and test the result of each read
    for i in range(len(data_items)):
        btv = byte_to_value[i]
        di = data_items[i]
        value = btv(di.pData, 0)
        result_values.append(value)

    assert result_values[0] == test_values[0]
    assert result_values[1] == test_values[1]
    assert result_values[2] == test_values[2]


def test_upload(testclient, testserver):
    """
    this raises an exception due to missing authorization? maybe not
    implemented in server emulator
    """
    pytest.raises(Snap7Exception, testclient.upload, db_number)


@pytest.mark.skip("TODO: invalid block size")
def test_download(testclient, testserver):
    data = bytearray(1024)
    testclient.download(block_num=db_number, data=data)


def test_read_area(testclient, testserver):
    amount = 1
    start = 1
    # Test read_area with a DB
    area = snap7.types.areas.DB
    dbnumber = 1
    data = bytearray(b'\x11')
    testclient.write_area(area, dbnumber, start, data)
    res = testclient.read_area(area, dbnumber, start, amount)
    assert data == bytearray(res)

    # Test read_area with a TM
    area = snap7.types.areas.TM
    dbnumber = 0
    data = bytearray(b'\x12\x34')
    testclient.write_area(area, dbnumber, start, data)
    res = testclient.read_area(area, dbnumber, start, amount)
    assert data == bytearray(res)

    # Test read_area with a CT
    area = snap7.types.areas.CT
    dbnumber = 0
    data = bytearray(b'\x13\x35')
    testclient.write_area(area, dbnumber, start, data)
    res = testclient.read_area(area, dbnumber, start, amount)
    assert data == bytearray(res)


def test_write_area(testclient, testserver):
    # Test write area with a DB
    area = snap7.types.areas.DB
    dbnumber = 1
    size = 1
    start = 1
    data = bytearray(b'\x11')
    testclient.write_area(area, dbnumber, start, data)
    res = testclient.read_area(area, dbnumber, start, 1)
    assert data == bytearray(res)

    # Test write area with a TM
    area = snap7.types.areas.TM
    dbnumber = 0
    size = 2
    timer = bytearray(b'\x12\x00')
    res = testclient.write_area(area, dbnumber, start, timer)
    res = testclient.read_area(area, dbnumber, start, 1)
    assert timer == bytearray(res)

    # Test write area with a CT
    area = snap7.types.areas.CT
    dbnumber = 0
    size = 2
    timer = bytearray(b'\x13\x00')
    res = testclient.write_area(area, dbnumber, start, timer)
    res = testclient.read_area(area, dbnumber, start, 1)
    assert timer == bytearray(res)


def test_list_blocks(testclient, testserver):
    blockList = testclient.list_blocks()


def test_list_blocks_of_type(testclient, testserver):
    testclient.list_blocks_of_type('DB', 10)

    pytest.raises(Exception, testclient.list_blocks_of_type,
                  'NOblocktype', 10)


def test_get_block_info(testclient, testserver):
    """test Cli_GetAgBlockInfo"""
    testclient.get_block_info('DB', 1)

    pytest.raises(Exception, testclient.get_block_info,
                  'NOblocktype', 10)
    pytest.raises(Exception, testclient.get_block_info, 'DB', 10)


def test_get_cpu_state(testclient, testserver):
    """this tests the get_cpu_state function"""
    testclient.get_cpu_state()


def test_set_session_password(testclient, testserver):
    password = 'abcdefgh'
    testclient.set_session_password(password)


def test_clear_session_password(testclient, testserver):
    testclient.clear_session_password()


@pytest.mark.skip("TODO: Check how to parametrise this. set_connection_params() needs to be exec before client.connect()")
def test_set_connection_params(testclient, testserver):
    testclient.set_connection_params("10.0.0.2", 10, 10)


def test_set_connection_type(testclient, testserver):
    testclient.set_connection_type(1)
    testclient.set_connection_type(2)
    testclient.set_connection_type(3)
    testclient.set_connection_type(20)


def test_get_connected(testclient, testserver):
    testclient.get_connected()


def test_ab_read(testclient, testserver):
    start = 1
    size = 1
    data = bytearray(size)
    testclient.ab_write(start=start, data=data)
    testclient.ab_read(start=start, size=size)


@pytest.mark.skip("TODO: crash client: FATAL: exception not rethrown")
def test_ab_write(testclient, testserver):
    start = 1
    size = 10
    data = bytearray(size)
    testclient.ab_write(start=start, data=data)


@pytest.mark.skip("TODO: crash client: FATAL: exception not rethrown")
def test_as_ab_read(testclient, testserver):
    start = 1
    size = 1
    testclient.as_ab_read(start=start, size=size)


@pytest.mark.skip("TODO: not yet fully implemented")
def test_as_ab_write(testclient, testserver):
    start = 1
    size = 10
    data = bytearray(size)
    testclient.as_ab_write(start=start, data=data)


def test_compress(testclient, testserver):
    time = 1000
    testclient.compress(time)


@pytest.mark.skip("Skip async methods until checked correctly")
def test_as_compress(testclient, testserver):
    time = 1000
    testclient.as_compress(time)


def test_set_param(testclient, testserver):
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
        testclient.set_param(param, value)

    pytest.raises(Exception, testclient.set_param,
                  snap7.types.RemotePort, 1)


def test_get_param(testclient, testserver):
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
        assert testclient.get_param(param) == value

    non_client = (snap7.types.LocalPort, snap7.types.WorkInterval, snap7.types.MaxClients,
                  snap7.types.BSendTimeout, snap7.types.BRecvTimeout, snap7.types.RecoveryTime,
                  snap7.types.KeepAliveTime)

    # invalid param for client
    for param in non_client:
        pytest.raises(Exception, testclient.get_param, non_client)


@pytest.mark.skip("TODO: not yet fully implemented")
def test_as_copy_ram_to_rom(testclient, testserver):
    testclient.copy_ram_to_rom()


@pytest.mark.skip("TODO: not yet fully implemented")
def test_as_ct_read(testclient, testserver):
    testclient.as_ct_read()


@pytest.mark.skip("TODO: not yet fully implemented")
def test_as_ct_write(testclient, testserver):
    testclient.as_ct_write()


@pytest.mark.skip("TODO: not yet fully implemented")
def test_as_db_fill(testclient, testserver):
    testclient.as_db_fill()


@pytest.mark.skip("TODO: not yet fully implemented")
def test_as_db_get(testclient, testserver):
    testclient.as_db_get(db_number=db_number)


@pytest.mark.skip("TODO: crash client: FATAL: exception not rethrown")
def test_as_db_read(testclient, testserver):
    size = 40
    start = 0
    db = 1
    data = bytearray(40)
    testclient.db_write(db_number=db, start=start, data=data)
    result = testclient.as_db_read(db_number=db, start=start, size=size)
    assert data == result


@pytest.mark.skip("TODO: crash client: FATAL: exception not rethrown")
def test_as_db_write(testclient, testserver):
    size = 40
    data = bytearray(size)
    testclient.as_db_write(db_number=1, start=0, data=data)


@pytest.mark.skip("TODO: not yet fully implemented")
def test_as_download(testclient, testserver):
    data = bytearray(128)
    testclient.as_download(block_num=-1, data=data)


def test_plc_stop(testclient, testserver):
    testclient.plc_stop()


def test_plc_hot_start(testclient, testserver):
    testclient.plc_hot_start()


def test_plc_cold_start(testclient, testserver):
    testclient.plc_cold_start()


def test_get_pdu_length(testclient, testserver):
    pduRequested = testclient.get_param(10)
    pduSize = testclient.get_pdu_length()
    assert pduSize == pduRequested


def test_get_cpu_info(testclient, testserver):
    expected = (
        ('ModuleTypeName', 'CPU 315-2 PN/DP'),
        ('SerialNumber', 'S C-C2UR28922012'),
        ('ASName', 'SNAP7-SERVER'),
        ('Copyright', 'Original Siemens Equipment'),
        ('ModuleName', 'CPU 315-2 PN/DP')
    )
    cpuInfo = testclient.get_cpu_info()
    for param, value in expected:
        assert getattr(cpuInfo, param).decode('utf-8') == value


def test_db_write_with_byte_literal_does_not_throw(testclient, testserver):
    mock_write = mock.MagicMock()
    mock_write.return_value = None
    original = testclient._library.Cli_DBWrite
    testclient._library.Cli_DBWrite = mock_write
    data = b'\xDE\xAD\xBE\xEF'

    try:
        testclient.db_write(db_number=1, start=0, data=data)
    except TypeError as e:
        pytest.fail(str(e))
    finally:
        testclient._library.Cli_DBWrite = original


def test_download_with_byte_literal_does_not_throw(testclient, testserver):
    mock_download = mock.MagicMock()
    mock_download.return_value = None
    original = testclient._library.Cli_Download
    testclient._library.Cli_Download = mock_download
    data = b'\xDE\xAD\xBE\xEF'

    try:
        testclient.download(block_num=db_number, data=data)
    except TypeError as e:
        pytest.fail(str(e))
    finally:
        testclient._library.Cli_Download = original


def test_write_area_with_byte_literal_does_not_throw(testclient, testserver):
    mock_writearea = mock.MagicMock()
    mock_writearea.return_value = None
    original = testclient._library.Cli_WriteArea
    testclient._library.Cli_WriteArea = mock_writearea

    area = snap7.types.areas.DB
    dbnumber = 1
    size = 4
    start = 1
    data = b'\xDE\xAD\xBE\xEF'

    try:
        testclient.write_area(area, dbnumber, start, data)
    except TypeError as e:
        pytest.fail(str(e))
    finally:
        testclient._library.Cli_WriteArea = original


def test_ab_write_with_byte_literal_does_not_throw(testclient, testserver):
    mock_write = mock.MagicMock()
    mock_write.return_value = None
    original = testclient._library.Cli_ABWrite
    testclient._library.Cli_ABWrite = mock_write

    start = 1
    data = b'\xDE\xAD\xBE\xEF'

    try:
        testclient.ab_write(start=start, data=data)
    except TypeError as e:
        pytest.fail(str(e))
    finally:
        testclient._library.Cli_ABWrite = original


@pytest.mark.skip("TODO: not yet fully implemented")
def test_as_ab_write_with_byte_literal_does_not_throw(testclient, testserver):
    mock_write = mock.MagicMock()
    mock_write.return_value = None
    original = testclient._library.Cli_AsABWrite
    testclient._library.Cli_AsABWrite = mock_write

    start = 1
    data = b'\xDE\xAD\xBE\xEF'

    try:
        testclient.as_ab_write(start=start, data=data)
    except TypeError as e:
        pytest.fail(str(e))
    finally:
        testclient._library.Cli_AsABWrite = original


@pytest.mark.skip("TODO: not yet fully implemented")
def test_as_db_write_with_byte_literal_does_not_throw(testclient, testserver):
    mock_write = mock.MagicMock()
    mock_write.return_value = None
    original = testclient._library.Cli_AsDBWrite
    testclient._library.Cli_AsDBWrite = mock_write
    data = b'\xDE\xAD\xBE\xEF'

    try:
        testclient.db_write(db_number=1, start=0, data=data)
    except TypeError as e:
        pytest.fail(str(e))
    finally:
        testclient._library.Cli_AsDBWrite = original


@pytest.mark.skip("TODO: not yet fully implemented")
def test_as_download_with_byte_literal_does_not_throw(testclient, testserver):
    mock_download = mock.MagicMock()
    mock_download.return_value = None
    original = testclient._library.Cli_AsDownload
    testclient._library.Cli_AsDownload = mock_download
    data = b'\xDE\xAD\xBE\xEF'

    try:
        testclient.as_download(block_num=db_number, data=data)
    except TypeError as e:
        pytest.fail(str(e))
    finally:
        testclient._library.Cli_AsDownload = original


def test_get_plc_time(testclient, testserver):
    assert datetime.now().replace(microsecond=0) == testclient.get_plc_datetime()


def test_set_plc_datetime(testclient, testserver):
    new_dt = datetime(2011, 1, 1, 1, 1, 1, 0)
    testclient.set_plc_datetime(new_dt)
    # Can't actual set datetime in emulated PLC, get_plc_datetime always returns system time.
    # assert new_dt, testclient.get_plc_datetime())


def test_wait_as_completion_pass(testclient, testserver, timeout=10):
    # Cli_WaitAsCompletion
    # prepare Server with values
    area = snap7.types.areas.DB
    dbnumber = 1
    size = 1
    start = 1
    data = bytearray(size)
    testclient.write_area(area, dbnumber, start, data)
    # start as_request and test
    p_data = testclient.as_db_read(dbnumber, start, size)
    testclient.wait_as_completion(timeout)
    assert bytearray(p_data) == data


def test_wait_as_completion_timeouted(testclient, testserver, timeout=0, tries=500):
    # Cli_WaitAsCompletion
    # prepare Server
    area = snap7.types.areas.DB
    dbnumber = 1
    size = 1
    start = 1
    data = bytearray(size)
    testclient.write_area(area, dbnumber, start, data)
    # start as_request and wait for zero seconds to try trigger timeout
    for i in range(tries):
        testclient.as_db_read(dbnumber, start, size)
        try:
            testclient.wait_as_completion(timeout)
        except Snap7Exception as s7_err:
            if not s7_err.args[0] == b'CLI : Job Timeout':
                pytest.fail(f"While waiting another error appeared: {s7_err}")
            return
    pytest.fail(f"After {tries} tries, no timout could be envoked by snap7. Either tests are passing to fast or"
                f"a problem is existing in the method. Fail test.")


def test_check_as_completion(testclient, testserver, timeout=5):
    # Cli_CheckAsCompletion
    check_status = ctypes.c_int(-1)
    pending_checked = False
    # preparing Server values
    size = 40
    start = 0
    db = 1
    data = bytearray(40)
    testclient.db_write(db_number=db, start=start, data=data)
    # Execute test
    p_data = testclient.as_db_read(db, start, size)
    for i in range(10):
        testclient.check_as_completion(ctypes.byref(check_status))
        if check_status.value == 0:
            data_result = bytearray(p_data)
            assert data_result == data
            break
        pending_checked = True
        time.sleep(1)
    else:
        pytest.fail(f"TimeoutError - Process pends for more than {timeout} seconds")
    if pending_checked is False:
        logging.warning("Pending was never reached, because Server was to fast,"
                        " but request to server was successfull.")


def test_as_read_area(testclient, testserver):
    amount = 1
    start = 1

    # Test read_area with a DB
    area = snap7.types.areas.DB
    dbnumber = 1
    data = bytearray(b'\x11')
    testclient.write_area(area, dbnumber, start, data)
    res = testclient.as_read_area(area, dbnumber, start, amount)
    testclient.wait_as_completion(10)
    res2 = bytearray(res)
    assert res2 == data

    # Test read_area with a TM
    area = snap7.types.areas.TM
    dbnumber = 0
    data = bytearray(b'\x12\x34')
    testclient.write_area(area, dbnumber, start, data)
    res = testclient.as_read_area(area, dbnumber, start, amount)
    testclient.wait_as_completion(10)
    res2 = bytearray(res)
    assert res2 == data

    # Test read_area with a CT
    area = snap7.types.areas.CT
    dbnumber = 0
    data = bytearray(b'\x13\x35')
    testclient.write_area(area, dbnumber, start, data)
    res = testclient.as_read_area(area, dbnumber, start, amount)
    testclient.wait_as_completion(10)
    res2 = bytearray(res)
    assert res2 == data


def test_as_write_area(testclient, testserver):
    # Test write area with a DB
    area = snap7.types.areas.DB
    dbnumber = 1
    size = 1
    start = 1
    data = bytearray(b'\x11')
    testclient.as_write_area(area, dbnumber, start, data)
    testclient.wait_as_completion(10)
    res = testclient.read_area(area, dbnumber, start, 1)
    assert data == bytearray(res)

    # Test write area with a TM
    area = snap7.types.areas.TM
    dbnumber = 0
    size = 2
    timer = bytearray(b'\x12\x00')
    testclient.as_write_area(area, dbnumber, start, timer)
    testclient.wait_as_completion(10)
    res = testclient.read_area(area, dbnumber, start, 1)
    assert timer == bytearray(res)

    # Test write area with a CT
    area = snap7.types.areas.CT
    dbnumber = 0
    size = 2
    timer = bytearray(b'\x13\x00')
    testclient.as_write_area(area, dbnumber, start, timer)
    testclient.wait_as_completion(10)
    res = testclient.read_area(area, dbnumber, start, 1)
    assert timer == bytearray(res)


def test_asebread(testclient, testserver):
    # Cli_AsEBRead
    with pytest.raises(NotImplementedError):
        testclient.asebread()


def test_asebwrite(testclient, testserver):
    # Cli_AsEBWrite
    with pytest.raises(NotImplementedError):
        testclient.asebwrite()


def test_asfullupload(testclient, testserver):
    # Cli_AsFullUpload
    with pytest.raises(NotImplementedError):
        testclient.asfullupload()


def test_aslistblocksoftype(testclient, testserver):
    # Cli_AsListBlocksOfType
    with pytest.raises(NotImplementedError):
        testclient.aslistblocksoftype()


def test_asmbread(testclient, testserver):
    # Cli_AsMBRead
    with pytest.raises(NotImplementedError):
        testclient.asmbread()


def test_asmbwrite(testclient, testserver):
    # Cli_AsMBWrite
    with pytest.raises(NotImplementedError):
        testclient.asmbwrite()


def test_asreadszl(testclient, testserver):
    # Cli_AsReadSZL
    with pytest.raises(NotImplementedError):
        testclient.asreadszl()


def test_asreadszllist(testclient, testserver):
    # Cli_AsReadSZLList
    with pytest.raises(NotImplementedError):
        testclient.asreadszllist()


def test_astmread(testclient, testserver):
    # Cli_AsTMRead
    with pytest.raises(NotImplementedError):
        testclient.astmread()


def test_astmwrite(testclient, testserver):
    # Cli_AsTMWrite
    with pytest.raises(NotImplementedError):
        testclient.astmwrite()


def test_asupload(testclient, testserver):
    # Cli_AsUpload
    with pytest.raises(NotImplementedError):
        testclient.asupload()


def test_aswritearea(testclient, testserver):
    # Cli_AsWriteArea
    with pytest.raises(NotImplementedError):
        testclient.aswritearea()


def test_copyramtorom(testclient, testserver):
    # Cli_CopyRamToRom
    with pytest.raises(NotImplementedError):
        testclient.copyramtorom()


def test_ctread(testclient, testserver):
    # Cli_CTRead
    with pytest.raises(NotImplementedError):
        testclient.ctread()


def test_ctwrite(testclient, testserver):
    # Cli_CTWrite
    with pytest.raises(NotImplementedError):
        testclient.ctwrite()


def test_dbfill(testclient, testserver):
    # Cli_DBFill
    with pytest.raises(NotImplementedError):
        testclient.dbfill()


def test_ebread(testclient, testserver):
    # Cli_EBRead
    with pytest.raises(NotImplementedError):
        testclient.ebread()


def test_ebwrite(testclient, testserver):
    # Cli_EBWrite
    with pytest.raises(NotImplementedError):
        testclient.ebwrite()


def test_errortext(testclient, testserver):
    # Cli_ErrorText
    with pytest.raises(NotImplementedError):
        testclient.errortext()


def test_getagblockinfo(testclient, testserver):
    # Cli_GetAgBlockInfo
    with pytest.raises(NotImplementedError):
        testclient.getagblockinfo()


def test_getcpinfo(testclient, testserver):
    # Cli_GetCpInfo
    with pytest.raises(NotImplementedError):
        testclient.getcpinfo()


def test_getexectime(testclient, testserver):
    # Cli_GetExecTime
    with pytest.raises(NotImplementedError):
        testclient.getexectime()


def test_getlasterror(testclient, testserver):
    # Cli_GetLastError
    with pytest.raises(NotImplementedError):
        testclient.getlasterror()


def test_getordercode(testclient, testserver):
    # Cli_GetOrderCode
    with pytest.raises(NotImplementedError):
        testclient.getordercode()


def test_getpdulength(testclient, testserver):
    # Cli_GetPduLength
    with pytest.raises(NotImplementedError):
        testclient.getpdulength()


def test_getpgblockinfo(testclient, testserver):
    # Cli_GetPgBlockInfo
    with pytest.raises(NotImplementedError):
        testclient.getpgblockinfo()


def test_getplcstatus(testclient, testserver):
    # Cli_GetPlcStatus
    with pytest.raises(NotImplementedError):
        testclient.getplcstatus()


def test_getprotection(testclient, testserver):
    # Cli_GetProtection
    with pytest.raises(NotImplementedError):
        testclient.getprotection()


def test_isoexchangebuffer(testclient, testserver):
    # Cli_IsoExchangeBuffer
    with pytest.raises(NotImplementedError):
        testclient.isoexchangebuffer()


def test_mbread(testclient, testserver):
    # Cli_MBRead
    with pytest.raises(NotImplementedError):
        testclient.mbread()


def test_mbwrite(testclient, testserver):
    # Cli_MBWrite
    with pytest.raises(NotImplementedError):
        testclient.mbwrite()


def test_readarea(testclient, testserver):
    # Cli_ReadArea
    with pytest.raises(NotImplementedError):
        testclient.readarea()


def test_readmultivars(testclient, testserver):
    # Cli_ReadMultiVars
    with pytest.raises(NotImplementedError):
        testclient.readmultivars()


def test_readszl(testclient, testserver):
    # Cli_ReadSZL
    with pytest.raises(NotImplementedError):
        testclient.readszl()


def test_readszllist(testclient, testserver):
    # Cli_ReadSZLList
    with pytest.raises(NotImplementedError):
        testclient.readszllist()


def test_setparam(testclient, testserver):
    # Cli_SetParam
    with pytest.raises(NotImplementedError):
        testclient.setparam()


def test_setplcsystemdatetime(testclient, testserver):
    # Cli_SetPlcSystemDateTime
    with pytest.raises(NotImplementedError):
        testclient.setplcsystemdatetime()


def test_setsessionpassword(testclient, testserver):
    # Cli_SetSessionPassword
    with pytest.raises(NotImplementedError):
        testclient.setsessionpassword()


def test_tmread(testclient, testserver):
    # Cli_TMRead
    with pytest.raises(NotImplementedError):
        testclient.tmread()


def test_tmwrite(testclient, testserver):
    # Cli_TMWrite
    with pytest.raises(NotImplementedError):
        testclient.tmwrite()


def test_writemultivars(testclient, testserver):
    # Cli_WriteMultiVars
    with pytest.raises(NotImplementedError):
        testclient.writemultivars()


class TestClientBeforeConnect(unittest.TestCase):
    """
    Test suite of items that should run without an open connection.
    """

    def setUp(self):
        testclient = snap7.client.Client()

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
            self.testclient.set_param(param, value)


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
