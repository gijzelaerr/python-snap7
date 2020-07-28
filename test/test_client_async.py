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

    @classmethod
    def setUpClass(cls):
        cls.process = Process(target=mainloop)
        cls.process.start()
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

    @unittest.skip("TODO: RuntimeWarning: coroutine 'TestClient.test_as_db_read' was never awaited")
    async def test_as_db_read(self):
        size = 40
        start = 0
        db = 1
        data = bytearray(40)
        self.client.db_write(db_number=db, start=start, data=data)
        result = await self.client.as_db_read(db_number=db, start=start, size=size)
        self.assertEqual(data, result)

    @unittest.skip("TODO: RuntimeWarning: coroutine 'TestClient.test_as_db_write' was never awaited")
    async def test_as_db_write(self):
        size = 40
        data = bytearray(size)
        check = await self.client.as_db_write(db_number=1, start=0, data=data)
        self.assertEqual(check, 0)

    @unittest.skip("TODO: crash client: FATAL: exception not rethrown")
    async def test_as_ab_read(self):
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
        await self.client.db_get(db_number=db_number)

    @unittest.skip("TODO: RuntimeWarning: coroutine 'TestClient.test_as_download' was never awaited")
    async def test_as_download(self):
        data = bytearray(128)
        await self.client.as_download(block_num=-1, data=data)

    async def test_as_read_area(self):
        amount = 1
        start = 1
        # Test read_area with a DB
        area = snap7.snap7types.areas.DB
        dbnumber = 1
        res = await self.client.as_read_area(area, dbnumber, start, amount)
        if res is None:
            raise TimeoutError
        # Test read_area with a TM
        area = snap7.snap7types.areas.TM
        dbnumber = 0
        res = await self.client.as_read_area(area, dbnumber, start, amount)
        if res is None:
            raise TimeoutError
        # Test read_area with a CT
        area = snap7.snap7types.areas.CT
        dbnumber = 0
        res = await self.client.as_read_area(area, dbnumber, start, amount)
        if res is None:
            raise TimeoutError

    async def test_as_write_area(self):
        # Test write area with a DB
        area = snap7.snap7types.areas.DB
        dbnumber = 1
        size = 1
        start = 1
        data = bytearray(size)
        res = await self.client.as_write_area(area, dbnumber, start, data)
        if res is None:
            raise TimeoutError
        # Test write area with a TM
        area = snap7.snap7types.areas.TM
        dbnumber = 0
        size = 2
        timer = bytearray(size)
        res = await self.client.as_write_area(area, dbnumber, start, timer)
        if res is None:
            raise TimeoutError
        # Test write area with a CT
        area = snap7.snap7types.areas.CT
        dbnumber = 0
        size = 2
        timer = bytearray(size)
        res = await self.client.as_write_area(area, dbnumber, start, timer)
        if res is None:
            raise TimeoutError
