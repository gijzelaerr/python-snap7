"""Tests for snap7/logo.py to improve coverage of parse_address, read, and write."""

import logging
import unittest
from typing import Optional

import pytest

from snap7.logo import Logo, parse_address
from snap7.server import Server
from snap7.type import SrvArea, WordLen

logging.basicConfig(level=logging.WARNING)

ip = "127.0.0.1"
tcpport = 11102
db_number = 1


# ---------------------------------------------------------------------------
# parse_address() unit tests (no server needed)
# ---------------------------------------------------------------------------


@pytest.mark.logo
class TestParseAddress(unittest.TestCase):
    """Test every branch of parse_address()."""

    def test_byte_address(self) -> None:
        start, wl = parse_address("V10")
        self.assertEqual(start, 10)
        self.assertEqual(wl, WordLen.Byte)

    def test_byte_address_large(self) -> None:
        start, wl = parse_address("V999")
        self.assertEqual(start, 999)
        self.assertEqual(wl, WordLen.Byte)

    def test_word_address(self) -> None:
        start, wl = parse_address("VW20")
        self.assertEqual(start, 20)
        self.assertEqual(wl, WordLen.Word)

    def test_word_address_zero(self) -> None:
        start, wl = parse_address("VW0")
        self.assertEqual(start, 0)
        self.assertEqual(wl, WordLen.Word)

    def test_dword_address(self) -> None:
        start, wl = parse_address("VD30")
        self.assertEqual(start, 30)
        self.assertEqual(wl, WordLen.DWord)

    def test_bit_address(self) -> None:
        start, wl = parse_address("V10.3")
        # bit offset = 10*8 + 3 = 83
        self.assertEqual(start, 83)
        self.assertEqual(wl, WordLen.Bit)

    def test_bit_address_zero(self) -> None:
        start, wl = parse_address("V0.0")
        self.assertEqual(start, 0)
        self.assertEqual(wl, WordLen.Bit)

    def test_bit_address_high_bit(self) -> None:
        start, wl = parse_address("V0.7")
        self.assertEqual(start, 7)
        self.assertEqual(wl, WordLen.Bit)

    def test_invalid_address_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_address("INVALID")

    def test_invalid_address_empty(self) -> None:
        with self.assertRaises(ValueError):
            parse_address("")

    def test_invalid_address_wrong_prefix(self) -> None:
        with self.assertRaises(ValueError):
            parse_address("M10")


# ---------------------------------------------------------------------------
# Integration tests: Logo client against the built-in Server
# ---------------------------------------------------------------------------


@pytest.mark.logo
class TestLogoReadWrite(unittest.TestCase):
    """Test Logo read/write against a real server with DB1 registered."""

    server: Optional[Server] = None
    db_data: bytearray

    @classmethod
    def setUpClass(cls) -> None:
        cls.db_data = bytearray(256)
        cls.server = Server()
        cls.server.register_area(SrvArea.DB, 0, bytearray(256))
        cls.server.register_area(SrvArea.DB, 1, cls.db_data)
        cls.server.start(tcp_port=tcpport)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server:
            cls.server.stop()
            cls.server.destroy()

    def setUp(self) -> None:
        self.client = Logo()
        self.client.connect(ip, 0x1000, 0x2000, tcpport)

    def tearDown(self) -> None:
        self.client.disconnect()
        self.client.destroy()

    # -- read tests ---------------------------------------------------------

    def test_read_byte(self) -> None:
        """Write a known byte into DB1 via client, then read it back."""
        self.client.write("V5", 0xAB)
        result = self.client.read("V5")
        self.assertEqual(result, 0xAB)

    def test_read_word(self) -> None:
        """Write and read back a word (signed 16-bit big-endian)."""
        self.client.write("VW10", 1234)
        result = self.client.read("VW10")
        self.assertEqual(result, 1234)

    def test_read_word_negative(self) -> None:
        """Words are signed — negative values should round-trip."""
        self.client.write("VW12", -500)
        result = self.client.read("VW12")
        self.assertEqual(result, -500)

    def test_read_dword(self) -> None:
        """Write and read back a dword (signed 32-bit big-endian)."""
        self.client.write("VD20", 70000)
        result = self.client.read("VD20")
        self.assertEqual(result, 70000)

    def test_read_dword_negative(self) -> None:
        """DWords are signed — negative values should round-trip."""
        self.client.write("VD24", -123456)
        result = self.client.read("VD24")
        self.assertEqual(result, -123456)

    def test_read_bit_set(self) -> None:
        """Write bit=1, then read it back."""
        self.client.write("V50.2", 1)
        result = self.client.read("V50.2")
        self.assertEqual(result, 1)

    def test_read_bit_clear(self) -> None:
        """Write bit=0, then read it back."""
        # First set it so we know we're actually clearing
        self.client.write("V51.5", 1)
        self.assertEqual(self.client.read("V51.5"), 1)
        self.client.write("V51.5", 0)
        result = self.client.read("V51.5")
        self.assertEqual(result, 0)

    def test_read_bit_zero(self) -> None:
        """Read bit 0 of byte 0."""
        self.client.write("V60", 0)  # clear byte first
        self.client.write("V60.0", 1)
        self.assertEqual(self.client.read("V60.0"), 1)
        # Other bits should be 0
        self.assertEqual(self.client.read("V60.1"), 0)

    def test_read_bit_seven(self) -> None:
        """Read bit 7 of a byte."""
        self.client.write("V61", 0)  # clear byte
        self.client.write("V61.7", 1)
        self.assertEqual(self.client.read("V61.7"), 1)
        # Byte should be 0x80
        self.assertEqual(self.client.read("V61"), 0x80)

    # -- write tests --------------------------------------------------------

    def test_write_byte(self) -> None:
        """Write a byte and verify."""
        result = self.client.write("V70", 42)
        self.assertEqual(result, 0)
        self.assertEqual(self.client.read("V70"), 42)

    def test_write_word(self) -> None:
        """Write a word and verify."""
        result = self.client.write("VW80", 2000)
        self.assertEqual(result, 0)
        self.assertEqual(self.client.read("VW80"), 2000)

    def test_write_dword(self) -> None:
        """Write a dword and verify."""
        result = self.client.write("VD90", 100000)
        self.assertEqual(result, 0)
        self.assertEqual(self.client.read("VD90"), 100000)

    def test_write_bit_true(self) -> None:
        """Write a bit to True."""
        result = self.client.write("V100.4", 1)
        self.assertEqual(result, 0)
        self.assertEqual(self.client.read("V100.4"), 1)

    def test_write_bit_false(self) -> None:
        """Write a bit to False after setting it."""
        self.client.write("V101.6", 1)
        result = self.client.write("V101.6", 0)
        self.assertEqual(result, 0)
        self.assertEqual(self.client.read("V101.6"), 0)

    def test_write_bit_preserves_other_bits(self) -> None:
        """Setting one bit should not disturb other bits in the same byte."""
        # Write 0xFF to the byte
        self.client.write("V110", 0xFF)
        # Clear bit 3
        self.client.write("V110.3", 0)
        # Byte should now be 0xF7 (all bits set except bit 3)
        self.assertEqual(self.client.read("V110"), 0xF7)
        # Set bit 3 back
        self.client.write("V110.3", 1)
        self.assertEqual(self.client.read("V110"), 0xFF)

    def test_write_byte_boundary_values(self) -> None:
        """Test boundary values: 0 and 255."""
        self.client.write("V120", 0)
        self.assertEqual(self.client.read("V120"), 0)
        self.client.write("V120", 255)
        self.assertEqual(self.client.read("V120"), 255)

    def test_write_word_boundary_values(self) -> None:
        """Test word boundary values: max positive and max negative."""
        self.client.write("VW130", 32767)
        self.assertEqual(self.client.read("VW130"), 32767)
        self.client.write("VW130", -32768)
        self.assertEqual(self.client.read("VW130"), -32768)

    def test_write_dword_boundary_values(self) -> None:
        """Test dword boundary values."""
        self.client.write("VD140", 2147483647)
        self.assertEqual(self.client.read("VD140"), 2147483647)
        self.client.write("VD140", -2147483648)
        self.assertEqual(self.client.read("VD140"), -2147483648)

    def test_read_write_multiple_addresses(self) -> None:
        """Verify different address types can coexist."""
        self.client.write("V200", 0x42)
        self.client.write("VW202", 1000)
        self.client.write("VD204", 50000)
        self.client.write("V208.1", 1)

        self.assertEqual(self.client.read("V200"), 0x42)
        self.assertEqual(self.client.read("VW202"), 1000)
        self.assertEqual(self.client.read("VD204"), 50000)
        self.assertEqual(self.client.read("V208.1"), 1)


if __name__ == "__main__":
    unittest.main()
