import asyncio
import ctypes
import logging
import time
import pytest
from multiprocessing import Process
from os import kill

import snap7
from snap7.server import mainloop

logging.basicConfig(level=logging.WARNING)

pytestmark = pytest.mark.asyncio


ip = '127.0.0.1'
tcpport = 1102
db_number = 1
rack = 1
slot = 1


@pytest.fixture
def testserver():
    process = Process(target=mainloop)
    process.start()
    time.sleep(2)  # wait for server to start
    yield process
    kill(process.pid, 1)


@pytest.fixture
def testclient():
    client_async = snap7.client_async.ClientAsync()
    client_async.connect(ip, rack, slot, tcpport)
    yield client_async
    client_async.disconnect()
    client_async.destroy()


async def test_wait_loop(testclient):
    check_status = ctypes.c_int(-1)
    pending_checked = False
    # preparing Server values
    amount = 1
    start = 1
    # Test read_area with a DB
    area = snap7.types.areas.DB
    dbnumber = 1
    data = bytearray(b'\x11')
    testclient.write_area(area, dbnumber, start, data)
    # Execute test
    wordlen, usrdata = testclient._prepare_as_read_area(snap7.types.S7AreaDB, amount)
    res = testclient.as_read_area(area, dbnumber, start, amount, wordlen, usrdata)
    if res != 0:
        pytest.fail(f"as_area_read was not succescull -- Errpr: {res}")
    await asyncio.wait_for(testclient.wait_loop(check_status), 10)
    data_result = bytearray(usrdata)
    if not data == data_result:
        logging.warning("Test result is not as expected")
        raise ValueError
    if pending_checked is False:
        logging.warning("Pending was never reached, because Server was to fast,"
                        " but request to server was successfull.")
