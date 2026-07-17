"""Tests for typed data access methods on Client."""

import unittest

import pytest

from snap7.client import Client
from snap7.server import Server
from snap7.type import SrvArea

ip = "127.0.0.1"
tcpport = 1102
rack = 1
slot = 1


@pytest.mark.client
class TestTypedAccess(unittest.TestCase):
    server: Server = None  # type: ignore

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = Server()
        cls.server.register_area(SrvArea.DB, 0, bytearray(600))
        cls.server.register_area(SrvArea.DB, 1, bytearray(600))
        cls.server.register_area(SrvArea.PA, 0, bytearray(100))
        cls.server.register_area(SrvArea.PE, 0, bytearray(100))
        cls.server.register_area(SrvArea.MK, 0, bytearray(100))
        cls.server.register_area(SrvArea.TM, 0, bytearray(100))
        cls.server.register_area(SrvArea.CT, 0, bytearray(100))
        cls.server.start(tcp_port=tcpport)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server:
            cls.server.stop()
            cls.server.destroy()

    def setUp(self) -> None:
        self.client = Client()
        self.client.connect(ip, rack, slot, tcpport)

    def tearDown(self) -> None:
        self.client.disconnect()
        self.client.destroy()

    # Bool tests

    def test_bool_roundtrip(self) -> None:
        self.client.db_write_bool(1, 0, 0, True)
        self.assertTrue(self.client.db_read_bool(1, 0, 0))

        self.client.db_write_bool(1, 0, 0, False)
        self.assertFalse(self.client.db_read_bool(1, 0, 0))

    def test_bool_preserves_other_bits(self) -> None:
        # Write byte 0xFF first
        self.client.db_write_byte(1, 0, 0xFF)

        # Clear bit 3
        self.client.db_write_bool(1, 0, 3, False)
        self.assertFalse(self.client.db_read_bool(1, 0, 3))

        # Other bits should still be set
        self.assertTrue(self.client.db_read_bool(1, 0, 0))
        self.assertTrue(self.client.db_read_bool(1, 0, 1))
        self.assertTrue(self.client.db_read_bool(1, 0, 7))

    def test_bool_all_bits(self) -> None:
        self.client.db_write_byte(1, 0, 0)
        for bit in range(8):
            self.client.db_write_bool(1, 0, bit, True)
            self.assertTrue(self.client.db_read_bool(1, 0, bit))

    # Byte tests

    def test_byte_roundtrip(self) -> None:
        self.client.db_write_byte(1, 10, 42)
        self.assertEqual(42, self.client.db_read_byte(1, 10))

    def test_byte_min_max(self) -> None:
        self.client.db_write_byte(1, 10, 0)
        self.assertEqual(0, self.client.db_read_byte(1, 10))

        self.client.db_write_byte(1, 10, 255)
        self.assertEqual(255, self.client.db_read_byte(1, 10))

    # INT tests

    def test_int_roundtrip(self) -> None:
        self.client.db_write_int(1, 20, 12345)
        self.assertEqual(12345, self.client.db_read_int(1, 20))

    def test_int_negative(self) -> None:
        self.client.db_write_int(1, 20, -12345)
        self.assertEqual(-12345, self.client.db_read_int(1, 20))

    def test_int_min_max(self) -> None:
        self.client.db_write_int(1, 20, -32768)
        self.assertEqual(-32768, self.client.db_read_int(1, 20))

        self.client.db_write_int(1, 20, 32767)
        self.assertEqual(32767, self.client.db_read_int(1, 20))

    # UINT tests

    def test_uint_roundtrip(self) -> None:
        self.client.db_write_uint(1, 30, 50000)
        self.assertEqual(50000, self.client.db_read_uint(1, 30))

    def test_uint_min_max(self) -> None:
        self.client.db_write_uint(1, 30, 0)
        self.assertEqual(0, self.client.db_read_uint(1, 30))

        self.client.db_write_uint(1, 30, 65535)
        self.assertEqual(65535, self.client.db_read_uint(1, 30))

    # WORD tests

    def test_word_roundtrip(self) -> None:
        self.client.db_write_word(1, 40, 0xABCD)
        self.assertEqual(0xABCD, self.client.db_read_word(1, 40))

    # DINT tests

    def test_dint_roundtrip(self) -> None:
        self.client.db_write_dint(1, 50, 100000)
        self.assertEqual(100000, self.client.db_read_dint(1, 50))

    def test_dint_negative(self) -> None:
        self.client.db_write_dint(1, 50, -100000)
        self.assertEqual(-100000, self.client.db_read_dint(1, 50))

    def test_dint_min_max(self) -> None:
        self.client.db_write_dint(1, 50, -2147483648)
        self.assertEqual(-2147483648, self.client.db_read_dint(1, 50))

        self.client.db_write_dint(1, 50, 2147483647)
        self.assertEqual(2147483647, self.client.db_read_dint(1, 50))

    # UDINT tests

    def test_udint_roundtrip(self) -> None:
        self.client.db_write_udint(1, 60, 3000000000)
        self.assertEqual(3000000000, self.client.db_read_udint(1, 60))

    # DWORD tests

    def test_dword_roundtrip(self) -> None:
        self.client.db_write_dword(1, 70, 0xDEADBEEF)
        self.assertEqual(0xDEADBEEF, self.client.db_read_dword(1, 70))

    # REAL tests

    def test_real_roundtrip(self) -> None:
        self.client.db_write_real(1, 80, 3.14)
        self.assertAlmostEqual(3.14, self.client.db_read_real(1, 80), places=2)

    def test_real_zero(self) -> None:
        self.client.db_write_real(1, 80, 0.0)
        self.assertEqual(0.0, self.client.db_read_real(1, 80))

    def test_real_negative(self) -> None:
        self.client.db_write_real(1, 80, -273.15)
        self.assertAlmostEqual(-273.15, self.client.db_read_real(1, 80), places=2)

    # LREAL tests

    def test_lreal_roundtrip(self) -> None:
        self.client.db_write_lreal(1, 90, 3.141592653589793)
        self.assertAlmostEqual(3.141592653589793, self.client.db_read_lreal(1, 90), places=10)

    def test_lreal_zero(self) -> None:
        self.client.db_write_lreal(1, 90, 0.0)
        self.assertEqual(0.0, self.client.db_read_lreal(1, 90))

    # STRING tests

    def test_string_roundtrip(self) -> None:
        # First write a proper S7 string header
        self.client.db_write_string(1, 100, "Hello")
        result = self.client.db_read_string(1, 100)
        self.assertEqual("Hello", result)

    def test_string_empty(self) -> None:
        self.client.db_write_string(1, 100, "")
        result = self.client.db_read_string(1, 100)
        self.assertEqual("", result)

    # Combined test

    def test_multiple_types_coexist(self) -> None:
        """Write different types at different offsets and verify they don't interfere."""
        self.client.db_write_int(1, 400, 1234)
        self.client.db_write_real(1, 404, 5.678)
        self.client.db_write_bool(1, 408, 0, True)
        self.client.db_write_dint(1, 410, -99999)

        self.assertEqual(1234, self.client.db_read_int(1, 400))
        self.assertAlmostEqual(5.678, self.client.db_read_real(1, 404), places=2)
        self.assertTrue(self.client.db_read_bool(1, 408, 0))
        self.assertEqual(-99999, self.client.db_read_dint(1, 410))
