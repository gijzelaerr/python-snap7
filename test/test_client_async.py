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

