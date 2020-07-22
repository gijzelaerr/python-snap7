import ctypes
import struct
import unittest
import logging
import time
import mock

import aiounittest

from datetime import datetime
from subprocess import Popen
from os import path, kill
import snap7
from snap7.snap7exceptions import Snap7Exception
from snap7.snap7types import S7AreaDB, S7WLByte, S7DataItem
from snap7 import util


logging.basicConfig(level=logging.WARNING)

ip = '127.0.0.1'
tcpport = 1102
db_number = 1
rack = 1
slot = 1


class TestClient(aiounittest.AsyncTestCase):

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
