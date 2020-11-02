import pytest
import snap7
from multiprocessing import Process
from os import kill
import time

import logging

ip = '127.0.0.1'
tcpport = 1102
db_number = 1
rack = 1
slot = 1


@pytest.fixture
def testpartner():
    testpartner = snap7.partner.Partner()
    testpartner.start()
    yield testpartner
    testpartner.stop()
    testpartner.destroy()


@pytest.fixture
def testserver():
    process = Process(target=snap7.server.mainloop)
    process.start()
    time.sleep(2)  # wait for server to start
    yield process
    #process.terminate()
    try:
        process.close()
    except BaseException as e:
        logging.error(f"{e} happpened here --> try killing killing process")
        process.kill()
    # kill(process.pid, 1)


@pytest.fixture
def testclient():
    client = snap7.client.Client()
    client.connect(ip, rack, slot, tcpport)
    yield client
    client.disconnect()
    client.destroy()


@pytest.fixture
def testasyncclient():
    client_async = snap7.client_async.ClientAsync()
    client_async.connect(ip, rack, slot, tcpport)
    yield client_async
    client_async.disconnect()
    client_async.destroy()
