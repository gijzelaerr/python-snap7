import logging
import time
import unittest
from multiprocessing import Process
from os import kill

import snap7
from snap7.server import mainloop

logging.basicConfig(level=logging.WARNING)

ip = '127.0.0.1'
tcpport = 1102
db_number = 1
rack = 1
slot = 1


class TestClient(unittest.TestCase):

    process = None
    server_pid = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.process = Process(target=mainloop)
        cls.process.start()
        time.sleep(2)  # wait for server to start

    @classmethod
    def tearDownClass(cls):
        kill(cls.server_pid, 1)

    def setUp(self) -> None:
        self.client = snap7.client_async.ClientAsync()
        self.client.connect(ip, rack, slot, tcpport)

    def tearDown(self) -> None:
        self.client.disconnect()
        self.client.destroy()

    @unittest.skip("TODO: RuntimeWarning: coroutine 'TestClient.test_as_db_read' was never awaited")
    async def test_as_db_read(self) -> None:
        size = 40
        start = 0
        db = 1
        data = bytearray(40)
        self.client.db_write(db_number=db, start=start, data=data)
        result = await self.client.as_db_read(db, start, size)
        self.assertEqual(data, result)

    @unittest.skip("TODO: RuntimeWarning: coroutine 'TestClient.test_as_db_write' was never awaited")
    async def test_as_db_write(self) -> None:
        size = 40
        data = bytearray(size)
        check = await self.client.as_db_write(db_number=1, start=0, data=data)
        self.assertEqual(check, 0)

    @unittest.skip("TODO: crash client: FATAL: exception not rethrown")
    async def test_as_ab_read(self) -> None:
        start = 1
        size = 1
        await self.client.as_ab_read(start=start, size=size)

    @unittest.skip("TODO: not yet fully implemented")
    async def test_as_ab_write(self):
        start = 1
        size = 10
        data = bytearray(size)
        await self.client.as_ab_write(start=start, data=data)

    async def test_as_db_get(self):
        await self.client.as_db_get(db_number=db_number)

    @unittest.skip("TODO: RuntimeWarning: coroutine 'TestClient.test_as_download' was never awaited")
    async def test_as_download(self):
        data = bytearray(128)
        await self.client.as_download(block_num=-1, data=data)
