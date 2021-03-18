import ctypes
import logging
from multiprocessing.context import Process
from os import get_inheritable
import time
import unittest
from unittest import mock

import snap7.error
import snap7.server
import snap7.util
from snap7.util import get_bool, get_dint, get_dword, get_int, get_real, get_sint, get_string, get_usint, get_word
from snap7.client import Client
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
        cls.process = Process(target=snap7.server.mainloop, args=[tcpport, True])
        cls.process.start()
        time.sleep(2)  # wait for server to start

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        cls.process.join(1)
        if cls.process.is_alive():
            cls.process.kill()

    def setUp(self):
        self.client: Client = snap7.client.Client()
        self.client.connect(ip, rack, slot, tcpport)

    def tearDown(self):
        self.client.disconnect()
        self.client.destroy()

    @unittest.skip("TODO: only first test used")
    def test_read_prefill_db(self):
        data = self.client.db_read(0, 0, 7)
        boolean = snap7.util.get_bool(data, 0, 0)
        print(data)
        self.assertEqual(boolean, True)
        integer = snap7.util.get_int(data, 1)
        self.assertEqual(integer, 128)
        real = snap7.util.get_real(data, 3)
        self.assertEqual(real, -128)

    def test_read_booleans(self):
        data = self.client.db_read(0, 0, 1)
        self.assertEqual(False, get_bool(data, 0, 0))
        self.assertEqual(True, get_bool(data, 0, 1))
        self.assertEqual(False, get_bool(data, 0, 2))
        self.assertEqual(True, get_bool(data, 0, 3))
        self.assertEqual(False, get_bool(data, 0, 4))
        self.assertEqual(True, get_bool(data, 0, 5))
        self.assertEqual(False, get_bool(data, 0, 6))
        self.assertEqual(True, get_bool(data, 0, 7))

    def test_read_small_int(self):
        data = self.client.db_read(0, 10, 4)
        value_1 = get_sint(data, 0)
        value_2 = get_sint(data, 1)
        value_3 = get_sint(data, 2)
        value_4 = get_sint(data, 3)
        self.assertEqual(value_1, -128)
        self.assertEqual(value_2, 0)
        self.assertEqual(value_3, 100)
        self.assertEqual(value_4, 127)

    def test_read_unsigned_small_int(self):
        data = self.client.db_read(0, 20, 2)
        self.assertEqual(get_usint(data, 0), 0)
        self.assertEqual(get_usint(data, 1), 255)

    def test_read_int(self):
        data = self.client.db_read(0, 30, 10)
        self.assertEqual(get_int(data, 0), -32768)
        self.assertEqual(get_int(data, 2), -1234)
        self.assertEqual(get_int(data, 4), 0)
        self.assertEqual(get_int(data, 6), 1234)
        self.assertEqual(get_int(data, 8), 32767)

    def test_read_double_int(self):
        data = self.client.db_read(0, 40, 4 * 5)
        self.assertEqual(get_dint(data, 0), -2147483648)
        self.assertEqual(get_dint(data, 4), -32768)
        self.assertEqual(get_dint(data, 8), 0)
        self.assertEqual(get_dint(data, 12), 32767)
        self.assertEqual(get_dint(data, 16), 2147483647)

    def test_read_real(self):
        data = self.client.db_read(0, 60, 4 * 9)
        self.assertAlmostEqual(get_real(data, 0), -3.402823e38, delta=-3.402823e38 * -0.0000001)
        self.assertAlmostEqual(get_real(data, 4), -3.402823e12, delta=-3.402823e12 * -0.0000001)
        self.assertAlmostEqual(get_real(data, 8), -175494351e-38, delta=-175494351e-38 * -0.0000001)
        self.assertAlmostEqual(get_real(data, 12), -1.175494351e-12, delta=-1.175494351e-12 * -0.0000001)
        self.assertAlmostEqual(get_real(data, 16), 0.0)
        self.assertAlmostEqual(get_real(data, 20), 1.175494351e-38, delta=1.175494351e-38 * 0.0000001)
        self.assertAlmostEqual(get_real(data, 24), 1.175494351e-12, delta=1.175494351e-12 * 0.0000001)
        self.assertAlmostEqual(get_real(data, 28), 3.402823466e12, delta=3.402823466e12 * 0.0000001)
        self.assertAlmostEqual(get_real(data, 32), 3.402823466e38, delta=3.402823466e38 * 0.0000001)

    def test_read_string(self):
        data = self.client.db_read(0, 100, 254)
        self.assertEqual(get_string(data, 0, 254), "the brown fox jumps over the lazy dog")

    def test_read_word(self):
        data = self.client.db_read(0, 400, 4 * 4)
        self.assertEqual(get_word(data, 0), 0x0000)
        self.assertEqual(get_word(data, 4), 0x1234)
        self.assertEqual(get_word(data, 8), 0xABCD)
        self.assertEqual(get_word(data, 12), 0xFFFF)

    def test_read_double_word(self):
        data = self.client.db_read(0, 500, 8 * 4)
        self.assertEqual(get_dword(data, 0), 0x00000000)
        self.assertEqual(get_dword(data, 8), 0x12345678)
        self.assertEqual(get_dword(data, 16), 0x1234ABCD)
        self.assertEqual(get_dword(data, 24), 0xFFFFFFFF)


if __name__ == '__main__':
    import logging

    logging.basicConfig()
    unittest.main()
