import logging
import struct
import pytest
import unittest
from typing import Optional

import snap7.error
import snap7.server
from snap7.server import Server
from snap7.type import SrvArea
from snap7.util import get_bool, get_dint, get_dword, get_int, get_real, get_sint, get_string, get_usint, get_word
from snap7.client import Client

logging.basicConfig(level=logging.WARNING)

ip = "127.0.0.1"
tcp_port = 1102
db_number = 1
rack = 1
slot = 1


def _init_standard_values(db_data: bytearray) -> None:
    """Initialize standard test values in DB0 (same as mainloop with init_standard_values=True)."""
    # test_read_booleans: offset 0, expects 0xAA (alternating False/True)
    db_data[0] = 0xAA

    # test_read_small_int: offset 10, expects -128, 0, 100, 127
    db_data[10] = 0x80
    db_data[11] = 0x00
    db_data[12] = 100
    db_data[13] = 127

    # test_read_unsigned_small_int: offset 20
    db_data[20] = 0
    db_data[21] = 255

    # test_read_int: offset 30
    struct.pack_into(">h", db_data, 30, -32768)
    struct.pack_into(">h", db_data, 32, -1234)
    struct.pack_into(">h", db_data, 34, 0)
    struct.pack_into(">h", db_data, 36, 1234)
    struct.pack_into(">h", db_data, 38, 32767)

    # test_read_double_int: offset 40
    struct.pack_into(">i", db_data, 40, -2147483648)
    struct.pack_into(">i", db_data, 44, -32768)
    struct.pack_into(">i", db_data, 48, 0)
    struct.pack_into(">i", db_data, 52, 32767)
    struct.pack_into(">i", db_data, 56, 2147483647)

    # test_read_real: offset 60
    struct.pack_into(">f", db_data, 60, -3.402823e38)
    struct.pack_into(">f", db_data, 64, -3.402823e12)
    struct.pack_into(">f", db_data, 68, -175494351e-38)
    struct.pack_into(">f", db_data, 72, -1.175494351e-12)
    struct.pack_into(">f", db_data, 76, 0.0)
    struct.pack_into(">f", db_data, 80, 1.175494351e-38)
    struct.pack_into(">f", db_data, 84, 1.175494351e-12)
    struct.pack_into(">f", db_data, 88, 3.402823466e12)
    struct.pack_into(">f", db_data, 92, 3.402823466e38)

    # test_read_string: offset 100
    test_string = "the brown fox jumps over the lazy dog"
    db_data[100] = 254
    db_data[101] = len(test_string)
    db_data[102 : 102 + len(test_string)] = test_string.encode("ascii")

    # test_read_word: offset 400
    struct.pack_into(">H", db_data, 400, 0x0000)
    struct.pack_into(">H", db_data, 404, 0x1234)
    struct.pack_into(">H", db_data, 408, 0xABCD)
    struct.pack_into(">H", db_data, 412, 0xFFFF)

    # test_read_double_word: offset 500
    struct.pack_into(">I", db_data, 500, 0x00000000)
    struct.pack_into(">I", db_data, 508, 0x12345678)
    struct.pack_into(">I", db_data, 516, 0x1234ABCD)
    struct.pack_into(">I", db_data, 524, 0xFFFFFFFF)


@pytest.mark.mainloop
class TestServer(unittest.TestCase):
    server: Optional[Server] = None
    client: Client

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = Server()
        # Create DB0 with standard test values
        db_data = bytearray(600)
        _init_standard_values(db_data)
        cls.server.register_area(SrvArea.DB, 0, db_data)
        cls.server.register_area(SrvArea.DB, 1, bytearray(600))
        cls.server.start(tcp_port=tcp_port)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server:
            cls.server.stop()
            cls.server.destroy()

    def setUp(self) -> None:
        self.client: Client = snap7.client.Client()
        self.client.connect(ip, rack, slot, tcp_port)

    def tearDown(self) -> None:
        if self.client:
            self.client.disconnect()
            self.client.destroy()

    def test_read_booleans(self) -> None:
        data = self.client.db_read(0, 0, 1)
        self.assertEqual(False, get_bool(data, 0, 0))
        self.assertEqual(True, get_bool(data, 0, 1))
        self.assertEqual(False, get_bool(data, 0, 2))
        self.assertEqual(True, get_bool(data, 0, 3))
        self.assertEqual(False, get_bool(data, 0, 4))
        self.assertEqual(True, get_bool(data, 0, 5))
        self.assertEqual(False, get_bool(data, 0, 6))
        self.assertEqual(True, get_bool(data, 0, 7))

    def test_read_small_int(self) -> None:
        data = self.client.db_read(0, 10, 4)
        value_1 = get_sint(data, 0)
        value_2 = get_sint(data, 1)
        value_3 = get_sint(data, 2)
        value_4 = get_sint(data, 3)
        self.assertEqual(value_1, -128)
        self.assertEqual(value_2, 0)
        self.assertEqual(value_3, 100)
        self.assertEqual(value_4, 127)

    def test_read_unsigned_small_int(self) -> None:
        data = self.client.db_read(0, 20, 2)
        self.assertEqual(get_usint(data, 0), 0)
        self.assertEqual(get_usint(data, 1), 255)

    def test_read_int(self) -> None:
        data = self.client.db_read(0, 30, 10)
        self.assertEqual(get_int(data, 0), -32768)
        self.assertEqual(get_int(data, 2), -1234)
        self.assertEqual(get_int(data, 4), 0)
        self.assertEqual(get_int(data, 6), 1234)
        self.assertEqual(get_int(data, 8), 32767)

    def test_read_double_int(self) -> None:
        data = self.client.db_read(0, 40, 4 * 5)
        self.assertEqual(get_dint(data, 0), -2147483648)
        self.assertEqual(get_dint(data, 4), -32768)
        self.assertEqual(get_dint(data, 8), 0)
        self.assertEqual(get_dint(data, 12), 32767)
        self.assertEqual(get_dint(data, 16), 2147483647)

    def test_read_real(self) -> None:
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

    def test_read_string(self) -> None:
        data = self.client.db_read(0, 100, 254)
        self.assertEqual(get_string(data, 0), "the brown fox jumps over the lazy dog")

    def test_read_word(self) -> None:
        data = self.client.db_read(0, 400, 4 * 4)
        self.assertEqual(get_word(data, 0), 0x0000)
        self.assertEqual(get_word(data, 4), 0x1234)
        self.assertEqual(get_word(data, 8), 0xABCD)
        self.assertEqual(get_word(data, 12), 0xFFFF)

    def test_read_double_word(self) -> None:
        data = self.client.db_read(0, 500, 8 * 4)
        self.assertEqual(get_dword(data, 0), 0x00000000)
        self.assertEqual(get_dword(data, 8), 0x12345678)
        self.assertEqual(get_dword(data, 16), 0x1234ABCD)
        self.assertEqual(get_dword(data, 24), 0xFFFFFFFF)


if __name__ == "__main__":
    import logging

    logging.basicConfig()
    unittest.main()
