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
    size = 40
    start = 0
    db = 1
    data = bytearray(40)
    testclient.db_write(db_number=db, start=start, data=data)
    # Execute test
    p_data = testclient.as_db_read(db, start, size)
    await asyncio.wait_for(testclient.wait_loop(check_status), 10)
    data_result = bytearray(p_data)
    if not data == data_result:
        logging.warning("Test result is not as expected")
        raise ValueError
    if pending_checked is False:
        logging.warning("Pending was never reached, because Server was to fast,"
                        " but request to server was successfull.")
