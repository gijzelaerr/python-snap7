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


@pytest.fixture(scope='module')
def testserver():
    process = Process(target=mainloop)
    process.start()
    time.sleep(2)  # wait for server to start
    yield process
    kill(process.pid, 1)


@pytest.fixture(scope='module')
def testclient():
    client_async = snap7.client_async.ClientAsync()
    client_async.set_as_check_mode(1)  # Todo: It should be possible to check all modes for all Tests in Future
    client_async.connect(ip, rack, slot, tcpport)
    yield client_async
    client_async.disconnect()
    client_async.destroy()


async def test_as_db_read(testserver, testclient):
    size = 40
    start = 0
    db = 1
    data = bytearray(40)
    await testclient.as_db_write(db_number=db, start=start, data=data)
    result = await testclient.as_db_read(db_number=db, start=start, size=size)
    assert data == result


async def test_as_db_write(testserver, testclient):
    size = 40
    data = bytearray(size)
    check = await testclient.as_db_write(db_number=1, start=0, data=data)
    assert check == 0


async def test_as_ab_read(testserver, testclient):
    start = 1
    size = 1
    data = bytearray(size)
    await testclient.as_ab_write(start=start, data=data)
    check = await testclient.as_ab_read(start=start, size=size)
    assert check == data


async def test_as_ab_write(testserver, testclient):
    start = 1
    size = 10
    data = bytearray(size)
    await testclient.as_ab_write(start=start, data=data)


@pytest.mark.skip("TODO FATAL: Segmentation ERROR -- Needs to be fixed")
async def test_as_db_get(testserver, testclient):
    await testclient.as_db_get(db_number=db_number)


async def test_as_download(testserver, testclient):
    data = bytearray(128)
    await testclient.as_download(block_num=-1, data=data)


async def test_as_read_area(testserver, testclient):
    amount = 1
    start = 1
    # Test read_area with a DB
    area = snap7.snap7types.areas.DB
    dbnumber = 1
    res = await testclient.as_read_area(area, dbnumber, start, amount)
    if res is None:
        raise TimeoutError
    # Test read_area with a TM
    area = snap7.snap7types.areas.TM
    dbnumber = 0
    res = await testclient.as_read_area(area, dbnumber, start, amount)
    if res is None:
        raise TimeoutError
    # Test read_area with a CT
    area = snap7.snap7types.areas.CT
    dbnumber = 0
    res = await testclient.as_read_area(area, dbnumber, start, amount)
    if res is None:
        raise TimeoutError


async def test_as_write_area(testserver, testclient):
    # Test write area with a DB
    area = snap7.snap7types.areas.DB
    dbnumber = 1
    size = 1
    start = 1
    data = bytearray(size)
    res = await testclient.as_write_area(area, dbnumber, start, data, 3)
    if res is None:
        raise TimeoutError
    # Test write area with a TM
    area = snap7.snap7types.areas.TM
    dbnumber = 0
    size = 2
    timer = bytearray(size)
    res = await testclient.as_write_area(area, dbnumber, start, timer, 3)
    if res is None:
        raise TimeoutError
    # Test write area with a CT
    area = snap7.snap7types.areas.CT
    dbnumber = 0
    size = 2
    timer = bytearray(size)
    res = await testclient.as_write_area(area, dbnumber, start, timer, 3)
    if res is None:
        raise TimeoutError
