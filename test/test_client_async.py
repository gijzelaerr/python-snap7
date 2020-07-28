import unittest
import logging
import time

from subprocess import Popen
from os import path, kill
import snap7


logging.basicConfig(level=logging.WARNING)

ip = '127.0.0.1'
tcpport = 1102
db_number = 1
rack = 1
slot = 1


class TestClient(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        server_path = path.join(path.dirname(path.realpath(snap7.__file__)),
                                "bin/snap7-server.py")
        cls.server_pid = Popen([server_path]).pid
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

    async def test_as_db_read(self):
        size = 40
        start = 0
        db = 1
        data = bytearray(40)
        self.client.db_write(db_number=db, start=start, data=data)
        result = await self.client.as_db_read(db_number=db, start=start, size=size)
        self.assertEqual(data, result)

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

    async def test_as_download(self):
        data = bytearray(128)
        await self.client.as_download(block_num=-1, data=data)
