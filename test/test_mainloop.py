import ctypes
import logging
from multiprocessing.context import Process
import time
import unittest
from unittest import mock

import snap7.error
import snap7.server
import snap7.util
import snap7.types

logging.basicConfig(level=logging.WARNING)

ip = '127.0.0.1'
tcpport = 1102
db_number = 1
rack = 1
slot = 1


class TestServer(unittest.TestCase):
    
    process = None

    @classmethod
    def setUpClass(cls):
        cls.process = Process(target=snap7.server.mainloop)
        cls.process.start()
        time.sleep(2)  # wait for server to start

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        cls.process.join(1)
        if cls.process.is_alive():
            cls.process.kill()

    def setUp(self):
        self.client: snap7.client.Client = snap7.client.Client()
        self.client.connect(ip, rack, slot, tcpport)

    def tearDown(self):
        self.client.disconnect()
        self.client.destroy()

    def test_read_prefill_db(self):
        data = self.client.db_read(0, 0, 7)
        boolean = snap7.util.get_bool(data, 0, 0)
        print(data)
        self.assertEqual(boolean, True)
        integer = snap7.util.get_int(data, 1)
        self.assertEqual(integer, 100)
        real = snap7.util.get_real(data, 3)
        self.assertEqual(real, 127)

if __name__ == '__main__':
    import logging

    logging.basicConfig()
    unittest.main()
