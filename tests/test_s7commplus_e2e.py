"""End-to-end tests for S7CommPlus client against a real Siemens S7-1200/1500 PLC.

These tests require a real PLC connection. Run with:

    pytest tests/test_s7commplus_e2e.py --e2e --plc-ip=YOUR_PLC_IP

Available options:
    --e2e           Enable e2e tests (required)
    --plc-ip        PLC IP address (default: 10.10.10.100)
    --plc-rack      PLC rack number (default: 0)
    --plc-slot      PLC slot number (default: 1)
    --plc-port      PLC TCP port (default: 102)
    --plc-db-read   Read-only DB number (default: 1)
    --plc-db-write  Read-write DB number (default: 2)

The PLC needs two data blocks configured with the same layout as the
regular S7 e2e tests:

DB1 "Read_only" - Read-only data block with predefined values:
    int1: Int = 10           (offset 0, 2 bytes)
    int2: Int = 255          (offset 2, 2 bytes)
    float1: Real = 123.45    (offset 4, 4 bytes)
    float2: Real = 543.21    (offset 8, 4 bytes)
    byte1: Byte = 0x0F       (offset 12, 1 byte)
    byte2: Byte = 0xF0       (offset 13, 1 byte)
    word1: Word = 0xABCD     (offset 14, 2 bytes)
    word2: Word = 0x1234     (offset 16, 2 bytes)
    dword1: DWord = 0x12345678 (offset 18, 4 bytes)
    dword2: DWord = 0x89ABCDEF (offset 22, 4 bytes)
    dint1: DInt = 2147483647 (offset 26, 4 bytes)
    dint2: DInt = 42         (offset 30, 4 bytes)
    char1: Char = 'F'        (offset 34, 1 byte)
    char2: Char = '-'        (offset 35, 1 byte)
    bool0-bool7: Bool        (offset 36, 1 byte, value: 0x01)

DB2 "Data_block_2" - Read/write data block with same structure.

Note: S7CommPlus targets S7-1200/1500 PLCs, which use optimized block
access. Ensure data blocks have "Optimized block access" disabled in
TIA Portal so that byte offsets match the layout above.
"""

import os
import struct
import unittest

import pytest

from snap7.s7commplus.client import S7CommPlusClient

# =============================================================================
# PLC Connection Configuration
# These can be overridden via pytest command line options or environment variables
# =============================================================================
PLC_IP = os.environ.get("PLC_IP", "10.10.10.100")
PLC_RACK = int(os.environ.get("PLC_RACK", "0"))
PLC_SLOT = int(os.environ.get("PLC_SLOT", "1"))
PLC_PORT = int(os.environ.get("PLC_PORT", "102"))

# Data block numbers
DB_READ_ONLY = int(os.environ.get("PLC_DB_READ", "1"))
DB_READ_WRITE = int(os.environ.get("PLC_DB_WRITE", "2"))


# =============================================================================
# DB Structure - Byte offsets for each variable (same as regular S7 e2e tests)
# =============================================================================
OFFSET_INT1 = 0  # Int (2 bytes)
OFFSET_INT2 = 2  # Int (2 bytes)
OFFSET_FLOAT1 = 4  # Real (4 bytes)
OFFSET_FLOAT2 = 8  # Real (4 bytes)
OFFSET_BYTE1 = 12  # Byte (1 byte)
OFFSET_BYTE2 = 13  # Byte (1 byte)
OFFSET_WORD1 = 14  # Word (2 bytes)
OFFSET_WORD2 = 16  # Word (2 bytes)
OFFSET_DWORD1 = 18  # DWord (4 bytes)
OFFSET_DWORD2 = 22  # DWord (4 bytes)
OFFSET_DINT1 = 26  # DInt (4 bytes)
OFFSET_DINT2 = 30  # DInt (4 bytes)
OFFSET_CHAR1 = 34  # Char (1 byte)
OFFSET_CHAR2 = 35  # Char (1 byte)
OFFSET_BOOLS = 36  # 8 Bools packed in 1 byte

# Total size of DB
DB_SIZE = 37

# =============================================================================
# Expected values from DB1 "Read_only"
# =============================================================================
EXPECTED_INT1 = 10
EXPECTED_INT2 = 255
EXPECTED_FLOAT1 = 123.45
EXPECTED_FLOAT2 = 543.21
EXPECTED_BYTE1 = 0x0F
EXPECTED_BYTE2 = 0xF0
EXPECTED_WORD1 = 0xABCD
EXPECTED_WORD2 = 0x1234
EXPECTED_DWORD1 = 0x12345678
EXPECTED_DWORD2 = 0x89ABCDEF
EXPECTED_DINT1 = 2147483647
EXPECTED_DINT2 = 42
EXPECTED_CHAR1 = "F"
EXPECTED_CHAR2 = "-"
EXPECTED_BOOL0 = True
EXPECTED_BOOL1 = False


# =============================================================================
# Test Classes
# =============================================================================


@pytest.mark.e2e
class TestS7CommPlusConnection(unittest.TestCase):
    """Tests for S7CommPlus connection."""

    def test_connect_disconnect(self) -> None:
        """Test connect() and disconnect()."""
        client = S7CommPlusClient()
        client.connect(PLC_IP, PLC_PORT, PLC_RACK, PLC_SLOT)
        self.assertTrue(client.connected)
        self.assertGreater(client.protocol_version, 0)
        self.assertGreater(client.session_id, 0)
        client.disconnect()
        self.assertFalse(client.connected)

    def test_context_manager(self) -> None:
        """Test S7CommPlusClient as context manager."""
        with S7CommPlusClient() as client:
            client.connect(PLC_IP, PLC_PORT, PLC_RACK, PLC_SLOT)
            self.assertTrue(client.connected)
        # After exiting context, client should be disconnected

    def test_properties_before_connect(self) -> None:
        """Test properties return defaults before connection."""
        client = S7CommPlusClient()
        self.assertFalse(client.connected)
        self.assertEqual(0, client.protocol_version)
        self.assertEqual(0, client.session_id)


@pytest.mark.e2e
class TestS7CommPlusDBRead(unittest.TestCase):
    """Tests for db_read() - reading from DB1 (read-only)."""

    client: S7CommPlusClient

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = S7CommPlusClient()
        cls.client.connect(PLC_IP, PLC_PORT, PLC_RACK, PLC_SLOT)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.client:
            cls.client.disconnect()

    def test_db_read_int(self) -> None:
        """Test db_read() for Int values."""
        data = self.client.db_read(DB_READ_ONLY, OFFSET_INT1, 2)
        value = struct.unpack(">h", data)[0]
        self.assertEqual(EXPECTED_INT1, value)

        data = self.client.db_read(DB_READ_ONLY, OFFSET_INT2, 2)
        value = struct.unpack(">h", data)[0]
        self.assertEqual(EXPECTED_INT2, value)

    def test_db_read_real(self) -> None:
        """Test db_read() for Real values."""
        data = self.client.db_read(DB_READ_ONLY, OFFSET_FLOAT1, 4)
        value = struct.unpack(">f", data)[0]
        self.assertAlmostEqual(EXPECTED_FLOAT1, value, places=2)

        data = self.client.db_read(DB_READ_ONLY, OFFSET_FLOAT2, 4)
        value = struct.unpack(">f", data)[0]
        self.assertAlmostEqual(EXPECTED_FLOAT2, value, places=2)

    def test_db_read_byte(self) -> None:
        """Test db_read() for Byte values."""
        data = self.client.db_read(DB_READ_ONLY, OFFSET_BYTE1, 1)
        self.assertEqual(EXPECTED_BYTE1, data[0])

        data = self.client.db_read(DB_READ_ONLY, OFFSET_BYTE2, 1)
        self.assertEqual(EXPECTED_BYTE2, data[0])

    def test_db_read_word(self) -> None:
        """Test db_read() for Word values."""
        data = self.client.db_read(DB_READ_ONLY, OFFSET_WORD1, 2)
        value = struct.unpack(">H", data)[0]
        self.assertEqual(EXPECTED_WORD1, value)

        data = self.client.db_read(DB_READ_ONLY, OFFSET_WORD2, 2)
        value = struct.unpack(">H", data)[0]
        self.assertEqual(EXPECTED_WORD2, value)

    def test_db_read_dword(self) -> None:
        """Test db_read() for DWord values."""
        data = self.client.db_read(DB_READ_ONLY, OFFSET_DWORD1, 4)
        value = struct.unpack(">I", data)[0]
        self.assertEqual(EXPECTED_DWORD1, value)

        data = self.client.db_read(DB_READ_ONLY, OFFSET_DWORD2, 4)
        value = struct.unpack(">I", data)[0]
        self.assertEqual(EXPECTED_DWORD2, value)

    def test_db_read_dint(self) -> None:
        """Test db_read() for DInt values."""
        data = self.client.db_read(DB_READ_ONLY, OFFSET_DINT1, 4)
        value = struct.unpack(">i", data)[0]
        self.assertEqual(EXPECTED_DINT1, value)

        data = self.client.db_read(DB_READ_ONLY, OFFSET_DINT2, 4)
        value = struct.unpack(">i", data)[0]
        self.assertEqual(EXPECTED_DINT2, value)

    def test_db_read_char(self) -> None:
        """Test db_read() for Char values."""
        data = self.client.db_read(DB_READ_ONLY, OFFSET_CHAR1, 1)
        self.assertEqual(EXPECTED_CHAR1, chr(data[0]))

        data = self.client.db_read(DB_READ_ONLY, OFFSET_CHAR2, 1)
        self.assertEqual(EXPECTED_CHAR2, chr(data[0]))

    def test_db_read_bool(self) -> None:
        """Test db_read() for Bool values (packed in byte)."""
        data = self.client.db_read(DB_READ_ONLY, OFFSET_BOOLS, 1)
        self.assertEqual(EXPECTED_BOOL0, bool(data[0] & 0x01))
        self.assertEqual(EXPECTED_BOOL1, bool(data[0] & 0x02))

    def test_db_read_entire_block(self) -> None:
        """Test db_read() for entire DB."""
        data = self.client.db_read(DB_READ_ONLY, 0, DB_SIZE)
        self.assertEqual(DB_SIZE, len(data))

        # Verify a few values
        int1 = struct.unpack(">h", data[OFFSET_INT1 : OFFSET_INT1 + 2])[0]
        self.assertEqual(EXPECTED_INT1, int1)

        float1 = struct.unpack(">f", data[OFFSET_FLOAT1 : OFFSET_FLOAT1 + 4])[0]
        self.assertAlmostEqual(EXPECTED_FLOAT1, float1, places=2)

        dword1 = struct.unpack(">I", data[OFFSET_DWORD1 : OFFSET_DWORD1 + 4])[0]
        self.assertEqual(EXPECTED_DWORD1, dword1)


@pytest.mark.e2e
class TestS7CommPlusDBWrite(unittest.TestCase):
    """Tests for db_write() - writing to DB2 (read/write)."""

    client: S7CommPlusClient

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = S7CommPlusClient()
        cls.client.connect(PLC_IP, PLC_PORT, PLC_RACK, PLC_SLOT)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.client:
            cls.client.disconnect()

    def test_db_write_int(self) -> None:
        """Test db_write() for Int values."""
        test_value = 10
        data = struct.pack(">h", test_value)
        self.client.db_write(DB_READ_WRITE, OFFSET_INT1, data)

        result = self.client.db_read(DB_READ_WRITE, OFFSET_INT1, 2)
        self.assertEqual(test_value, struct.unpack(">h", result)[0])

    def test_db_write_real(self) -> None:
        """Test db_write() for Real values."""
        test_value = 456.789
        data = struct.pack(">f", test_value)
        self.client.db_write(DB_READ_WRITE, OFFSET_FLOAT1, data)

        result = self.client.db_read(DB_READ_WRITE, OFFSET_FLOAT1, 4)
        self.assertAlmostEqual(test_value, struct.unpack(">f", result)[0], places=2)

    def test_db_write_byte(self) -> None:
        """Test db_write() for Byte values."""
        test_value = 0xAB
        self.client.db_write(DB_READ_WRITE, OFFSET_BYTE1, bytes([test_value]))

        result = self.client.db_read(DB_READ_WRITE, OFFSET_BYTE1, 1)
        self.assertEqual(test_value, result[0])

    def test_db_write_word(self) -> None:
        """Test db_write() for Word values."""
        test_value = 0x1234
        data = struct.pack(">H", test_value)
        self.client.db_write(DB_READ_WRITE, OFFSET_WORD1, data)

        result = self.client.db_read(DB_READ_WRITE, OFFSET_WORD1, 2)
        self.assertEqual(test_value, struct.unpack(">H", result)[0])

    def test_db_write_dword(self) -> None:
        """Test db_write() for DWord values."""
        test_value = 0xDEADBEEF
        data = struct.pack(">I", test_value)
        self.client.db_write(DB_READ_WRITE, OFFSET_DWORD1, data)

        result = self.client.db_read(DB_READ_WRITE, OFFSET_DWORD1, 4)
        self.assertEqual(test_value, struct.unpack(">I", result)[0])

    def test_db_write_dint(self) -> None:
        """Test db_write() for DInt values."""
        test_value = -123456789
        data = struct.pack(">i", test_value)
        self.client.db_write(DB_READ_WRITE, OFFSET_DINT1, data)

        result = self.client.db_read(DB_READ_WRITE, OFFSET_DINT1, 4)
        self.assertEqual(test_value, struct.unpack(">i", result)[0])

    def test_db_write_char(self) -> None:
        """Test db_write() for Char values."""
        test_value = "X"
        self.client.db_write(DB_READ_WRITE, OFFSET_CHAR1, test_value.encode("ascii"))

        result = self.client.db_read(DB_READ_WRITE, OFFSET_CHAR1, 1)
        self.assertEqual(test_value, chr(result[0]))

    def test_db_write_bool(self) -> None:
        """Test db_write() for Bool values (packed in byte)."""
        # Read current byte, set bit 0 and bit 7, write back
        data = bytearray(self.client.db_read(DB_READ_WRITE, OFFSET_BOOLS, 1))
        data[0] = data[0] | 0x01 | 0x80  # Set bit 0 and bit 7
        self.client.db_write(DB_READ_WRITE, OFFSET_BOOLS, bytes(data))

        result = self.client.db_read(DB_READ_WRITE, OFFSET_BOOLS, 1)
        self.assertTrue(bool(result[0] & 0x01))
        self.assertTrue(bool(result[0] & 0x80))


@pytest.mark.e2e
class TestS7CommPlusMultiRead(unittest.TestCase):
    """Tests for db_read_multi() - multiple reads in a single request."""

    client: S7CommPlusClient

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = S7CommPlusClient()
        cls.client.connect(PLC_IP, PLC_PORT, PLC_RACK, PLC_SLOT)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.client:
            cls.client.disconnect()

    def test_multi_read(self) -> None:
        """Test db_read_multi() reads multiple regions."""
        items = [
            (DB_READ_ONLY, OFFSET_INT1, 2),
            (DB_READ_ONLY, OFFSET_FLOAT1, 4),
            (DB_READ_ONLY, OFFSET_DWORD1, 4),
        ]
        results = self.client.db_read_multi(items)
        self.assertEqual(3, len(results))

        int_val = struct.unpack(">h", results[0])[0]
        self.assertEqual(EXPECTED_INT1, int_val)

        float_val = struct.unpack(">f", results[1])[0]
        self.assertAlmostEqual(EXPECTED_FLOAT1, float_val, places=2)

        dword_val = struct.unpack(">I", results[2])[0]
        self.assertEqual(EXPECTED_DWORD1, dword_val)

    def test_multi_read_across_dbs(self) -> None:
        """Test db_read_multi() across different data blocks."""
        # Write a known value to DB2 first
        test_int = 777
        self.client.db_write(DB_READ_WRITE, OFFSET_INT1, struct.pack(">h", test_int))

        items = [
            (DB_READ_ONLY, OFFSET_INT1, 2),
            (DB_READ_WRITE, OFFSET_INT1, 2),
        ]
        results = self.client.db_read_multi(items)
        self.assertEqual(2, len(results))

        self.assertEqual(EXPECTED_INT1, struct.unpack(">h", results[0])[0])
        self.assertEqual(test_int, struct.unpack(">h", results[1])[0])


@pytest.mark.e2e
class TestS7CommPlusExplore(unittest.TestCase):
    """Tests for explore() - browsing the PLC object tree."""

    client: S7CommPlusClient

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = S7CommPlusClient()
        cls.client.connect(PLC_IP, PLC_PORT, PLC_RACK, PLC_SLOT)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.client:
            cls.client.disconnect()

    def test_explore(self) -> None:
        """Test explore() returns data."""
        try:
            data = self.client.explore()
        except Exception as e:
            pytest.skip(f"Explore not supported: {e}")
        self.assertIsInstance(data, bytes)
        self.assertGreater(len(data), 0)
