"""End-to-end tests for Client class against a real Siemens S7 PLC.

These tests require a real PLC connection. Run with:

    pytest tests/test_client_e2e.py --e2e --plc-ip=YOUR_PLC_IP

Available options:
    --e2e           Enable e2e tests (required)
    --plc-ip        PLC IP address (default: 10.10.10.100)
    --plc-rack      PLC rack number (default: 0)
    --plc-slot      PLC slot number (default: 1)
    --plc-port      PLC TCP port (default: 102)
    --plc-db-read   Read-only DB number (default: 1)
    --plc-db-write  Read-write DB number (default: 2)

The PLC needs two data blocks configured:

DB1 "Read_only" - Read-only data block with predefined values:
    int1: Int = 10
    int2: Int = 255
    float1: Real = 123.45
    float2: Real = 543.21
    byte1: Byte = 0x0F
    byte2: Byte = 0xF0
    word1: Word = 0xABCD
    word2: Word = 0x1234
    dword1: DWord = 0x12345678
    dword2: DWord = 0x89ABCDEF
    dint1: DInt = 2147483647
    dint2: DInt = 42
    char1: Char = 'F'
    char2: Char = '-'
    bool0-bool7: Bool (packed in 1 byte, value: 0x01 i.e. bool0=True, bool1-7=False)

DB2 "Data_block_2" - Read/write data block with same structure.
"""

import os
import pytest
import unittest
from ctypes import c_int32, POINTER, pointer, create_string_buffer, cast, c_uint8
from datetime import datetime

from snap7.client import Client
from snap7.type import Area, Block, S7DataItem, WordLen, Parameter
from snap7.util import (
    get_int,
    get_real,
    get_byte,
    get_word,
    get_dword,
    get_dint,
    get_char,
    get_bool,
    set_int,
    set_real,
    set_byte,
    set_word,
    set_dword,
    set_dint,
    set_char,
    set_bool,
)

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
# DB Structure - Byte offsets for each variable
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
EXPECTED_BOOL2 = False
EXPECTED_BOOL3 = False
EXPECTED_BOOL4 = False
EXPECTED_BOOL5 = False
EXPECTED_BOOL6 = False
EXPECTED_BOOL7 = False


# =============================================================================
# Test Classes
# =============================================================================


@pytest.mark.e2e
class TestClientConnection(unittest.TestCase):
    """Tests for Client connection methods."""

    def test_connect_disconnect(self) -> None:
        """Test connect() and disconnect() methods."""
        client = Client()
        client.connect(PLC_IP, PLC_RACK, PLC_SLOT, PLC_PORT)
        self.assertTrue(client.get_connected())
        client.disconnect()
        self.assertFalse(client.get_connected())

    def test_get_connected(self) -> None:
        """Test get_connected() method."""
        client = Client()
        self.assertFalse(client.get_connected())
        client.connect(PLC_IP, PLC_RACK, PLC_SLOT, PLC_PORT)
        self.assertTrue(client.get_connected())
        client.disconnect()
        self.assertFalse(client.get_connected())

    def test_context_manager(self) -> None:
        """Test Client as context manager."""
        with Client() as client:
            client.connect(PLC_IP, PLC_RACK, PLC_SLOT, PLC_PORT)
            self.assertTrue(client.get_connected())

    def test_create_destroy(self) -> None:
        """Test create() and destroy() methods."""
        client = Client()
        client.create()  # No-op for compatibility
        client.connect(PLC_IP, PLC_RACK, PLC_SLOT, PLC_PORT)
        self.assertTrue(client.get_connected())
        client.destroy()
        self.assertFalse(client.get_connected())


@pytest.mark.e2e
class TestClientDBRead(unittest.TestCase):
    """Tests for db_read() method - reading from DB1 (read-only)."""

    client: Client

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = Client()
        cls.client.connect(PLC_IP, PLC_RACK, PLC_SLOT, PLC_PORT)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.client:
            cls.client.disconnect()

    def test_db_read_int(self) -> None:
        """Test db_read() for Int values."""
        data = self.client.db_read(DB_READ_ONLY, OFFSET_INT1, 2)
        self.assertEqual(EXPECTED_INT1, get_int(data, 0))

        data = self.client.db_read(DB_READ_ONLY, OFFSET_INT2, 2)
        self.assertEqual(EXPECTED_INT2, get_int(data, 0))

    def test_db_read_real(self) -> None:
        """Test db_read() for Real values."""
        data = self.client.db_read(DB_READ_ONLY, OFFSET_FLOAT1, 4)
        self.assertAlmostEqual(EXPECTED_FLOAT1, get_real(data, 0), places=2)

        data = self.client.db_read(DB_READ_ONLY, OFFSET_FLOAT2, 4)
        self.assertAlmostEqual(EXPECTED_FLOAT2, get_real(data, 0), places=2)

    def test_db_read_byte(self) -> None:
        """Test db_read() for Byte values."""
        data = self.client.db_read(DB_READ_ONLY, OFFSET_BYTE1, 1)
        self.assertEqual(EXPECTED_BYTE1, get_byte(data, 0))

        data = self.client.db_read(DB_READ_ONLY, OFFSET_BYTE2, 1)
        self.assertEqual(EXPECTED_BYTE2, get_byte(data, 0))

    def test_db_read_word(self) -> None:
        """Test db_read() for Word values."""
        data = self.client.db_read(DB_READ_ONLY, OFFSET_WORD1, 2)
        self.assertEqual(EXPECTED_WORD1, get_word(data, 0))

        data = self.client.db_read(DB_READ_ONLY, OFFSET_WORD2, 2)
        self.assertEqual(EXPECTED_WORD2, get_word(data, 0))

    def test_db_read_dword(self) -> None:
        """Test db_read() for DWord values."""
        data = self.client.db_read(DB_READ_ONLY, OFFSET_DWORD1, 4)
        self.assertEqual(EXPECTED_DWORD1, get_dword(data, 0))

        data = self.client.db_read(DB_READ_ONLY, OFFSET_DWORD2, 4)
        self.assertEqual(EXPECTED_DWORD2, get_dword(data, 0))

    def test_db_read_dint(self) -> None:
        """Test db_read() for DInt values."""
        data = self.client.db_read(DB_READ_ONLY, OFFSET_DINT1, 4)
        self.assertEqual(EXPECTED_DINT1, get_dint(data, 0))

        data = self.client.db_read(DB_READ_ONLY, OFFSET_DINT2, 4)
        self.assertEqual(EXPECTED_DINT2, get_dint(data, 0))

    def test_db_read_char(self) -> None:
        """Test db_read() for Char values."""
        data = self.client.db_read(DB_READ_ONLY, OFFSET_CHAR1, 1)
        self.assertEqual(EXPECTED_CHAR1, get_char(data, 0))

        data = self.client.db_read(DB_READ_ONLY, OFFSET_CHAR2, 1)
        self.assertEqual(EXPECTED_CHAR2, get_char(data, 0))

    def test_db_read_bool(self) -> None:
        """Test db_read() for Bool values."""
        data = self.client.db_read(DB_READ_ONLY, OFFSET_BOOLS, 1)
        self.assertEqual(EXPECTED_BOOL0, get_bool(data, 0, 0))
        self.assertEqual(EXPECTED_BOOL1, get_bool(data, 0, 1))
        self.assertEqual(EXPECTED_BOOL2, get_bool(data, 0, 2))
        self.assertEqual(EXPECTED_BOOL3, get_bool(data, 0, 3))
        self.assertEqual(EXPECTED_BOOL4, get_bool(data, 0, 4))
        self.assertEqual(EXPECTED_BOOL5, get_bool(data, 0, 5))
        self.assertEqual(EXPECTED_BOOL6, get_bool(data, 0, 6))
        self.assertEqual(EXPECTED_BOOL7, get_bool(data, 0, 7))

    def test_db_read_entire_block(self) -> None:
        """Test db_read() for entire DB."""
        data = self.client.db_read(DB_READ_ONLY, 0, DB_SIZE)
        self.assertEqual(DB_SIZE, len(data))
        # Verify a few values
        self.assertEqual(EXPECTED_INT1, get_int(data, OFFSET_INT1))
        self.assertAlmostEqual(EXPECTED_FLOAT1, get_real(data, OFFSET_FLOAT1), places=2)
        self.assertEqual(EXPECTED_DWORD1, get_dword(data, OFFSET_DWORD1))


@pytest.mark.e2e
class TestClientDBWrite(unittest.TestCase):
    """Tests for db_write() method - writing to DB2 (read/write)."""

    client: Client

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = Client()
        cls.client.connect(PLC_IP, PLC_RACK, PLC_SLOT, PLC_PORT)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.client:
            cls.client.disconnect()

    def test_db_write_int(self) -> None:
        """Test db_write() for Int values."""
        test_value = 10
        data = bytearray(2)
        set_int(data, 0, test_value)
        self.client.db_write(DB_READ_WRITE, OFFSET_INT1, data)

        # Read back and verify
        result = self.client.db_read(DB_READ_WRITE, OFFSET_INT1, 2)
        self.assertEqual(test_value, get_int(result, 0))

    def test_db_write_real(self) -> None:
        """Test db_write() for Real values."""
        test_value = 456.789
        data = bytearray(4)
        set_real(data, 0, test_value)
        self.client.db_write(DB_READ_WRITE, OFFSET_FLOAT1, data)

        # Read back and verify
        result = self.client.db_read(DB_READ_WRITE, OFFSET_FLOAT1, 4)
        self.assertAlmostEqual(test_value, get_real(result, 0), places=2)

    def test_db_write_byte(self) -> None:
        """Test db_write() for Byte values."""
        test_value = 0xAB
        data = bytearray(1)
        set_byte(data, 0, test_value)
        self.client.db_write(DB_READ_WRITE, OFFSET_BYTE1, data)

        # Read back and verify
        result = self.client.db_read(DB_READ_WRITE, OFFSET_BYTE1, 1)
        self.assertEqual(test_value, get_byte(result, 0))

    def test_db_write_word(self) -> None:
        """Test db_write() for Word values."""
        test_value = 0x1234
        data = bytearray(2)
        set_word(data, 0, test_value)
        self.client.db_write(DB_READ_WRITE, OFFSET_WORD1, data)

        # Read back and verify
        result = self.client.db_read(DB_READ_WRITE, OFFSET_WORD1, 2)
        self.assertEqual(test_value, get_word(result, 0))

    def test_db_write_dword(self) -> None:
        """Test db_write() for DWord values."""
        test_value = 0xDEADBEEF
        data = bytearray(4)
        set_dword(data, 0, test_value)
        self.client.db_write(DB_READ_WRITE, OFFSET_DWORD1, data)

        # Read back and verify
        result = self.client.db_read(DB_READ_WRITE, OFFSET_DWORD1, 4)
        self.assertEqual(test_value, get_dword(result, 0))

    def test_db_write_dint(self) -> None:
        """Test db_write() for DInt values."""
        test_value = -123456789
        data = bytearray(4)
        set_dint(data, 0, test_value)
        self.client.db_write(DB_READ_WRITE, OFFSET_DINT1, data)

        # Read back and verify
        result = self.client.db_read(DB_READ_WRITE, OFFSET_DINT1, 4)
        self.assertEqual(test_value, get_dint(result, 0))

    def test_db_write_char(self) -> None:
        """Test db_write() for Char values."""
        test_value = "X"
        data = bytearray(1)
        set_char(data, 0, test_value)
        self.client.db_write(DB_READ_WRITE, OFFSET_CHAR1, data)

        # Read back and verify
        result = self.client.db_read(DB_READ_WRITE, OFFSET_CHAR1, 1)
        self.assertEqual(test_value, get_char(result, 0))

    def test_db_write_bool(self) -> None:
        """Test db_write() for Bool values."""
        # Read current byte, modify bits, write back
        data = self.client.db_read(DB_READ_WRITE, OFFSET_BOOLS, 1)
        set_bool(data, 0, 0, True)
        set_bool(data, 0, 7, True)
        self.client.db_write(DB_READ_WRITE, OFFSET_BOOLS, data)

        # Read back and verify
        result = self.client.db_read(DB_READ_WRITE, OFFSET_BOOLS, 1)
        self.assertTrue(get_bool(result, 0, 0))
        self.assertTrue(get_bool(result, 0, 7))


@pytest.mark.e2e
class TestClientReadArea(unittest.TestCase):
    """Tests for read_area() method."""

    client: Client

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = Client()
        cls.client.connect(PLC_IP, PLC_RACK, PLC_SLOT, PLC_PORT)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.client:
            cls.client.disconnect()

    def test_read_area_db(self) -> None:
        """Test read_area() for DB area."""
        data = self.client.read_area(Area.DB, DB_READ_ONLY, OFFSET_INT1, 2)
        self.assertEqual(EXPECTED_INT1, get_int(data, 0))


@pytest.mark.e2e
class TestClientWriteArea(unittest.TestCase):
    """Tests for write_area() method."""

    client: Client

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = Client()
        cls.client.connect(PLC_IP, PLC_RACK, PLC_SLOT, PLC_PORT)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.client:
            cls.client.disconnect()

    def test_write_area_db(self) -> None:
        """Test write_area() for DB area."""
        test_value = 9999
        data = bytearray(2)
        set_int(data, 0, test_value)
        self.client.write_area(Area.DB, DB_READ_WRITE, OFFSET_INT2, data)

        # Read back and verify
        result = self.client.read_area(Area.DB, DB_READ_WRITE, OFFSET_INT2, 2)
        self.assertEqual(test_value, get_int(result, 0))


@pytest.mark.e2e
class TestClientMultiVars(unittest.TestCase):
    """Tests for read_multi_vars() and write_multi_vars() methods."""

    client: Client

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = Client()
        cls.client.connect(PLC_IP, PLC_RACK, PLC_SLOT, PLC_PORT)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.client:
            cls.client.disconnect()

    def test_read_multi_vars(self) -> None:
        """Test read_multi_vars() method."""
        # Build S7DataItem array
        data_items = (S7DataItem * 2)()

        # Item 0: Read int1 from DB1
        data_items[0].Area = c_int32(Area.DB.value)
        data_items[0].WordLen = c_int32(WordLen.Byte.value)
        data_items[0].Result = c_int32(0)
        data_items[0].DBNumber = c_int32(DB_READ_ONLY)
        data_items[0].Start = c_int32(OFFSET_INT1)
        data_items[0].Amount = c_int32(2)

        # Item 1: Read float1 from DB1
        data_items[1].Area = c_int32(Area.DB.value)
        data_items[1].WordLen = c_int32(WordLen.Byte.value)
        data_items[1].Result = c_int32(0)
        data_items[1].DBNumber = c_int32(DB_READ_ONLY)
        data_items[1].Start = c_int32(OFFSET_FLOAT1)
        data_items[1].Amount = c_int32(4)

        # Create buffers
        for di in data_items:
            buffer = create_string_buffer(di.Amount)
            di.pData = cast(pointer(buffer), POINTER(c_uint8))

        result, items = self.client.read_multi_vars(data_items)
        self.assertEqual(0, result)

        # Verify values
        int_value = get_int(bytearray(items[0].pData[:2]), 0)
        self.assertEqual(EXPECTED_INT1, int_value)

        float_value = get_real(bytearray(items[1].pData[:4]), 0)
        self.assertAlmostEqual(EXPECTED_FLOAT1, float_value, places=2)


@pytest.mark.e2e
class TestClientDBOperations(unittest.TestCase):
    """Tests for db_get() and db_fill() methods."""

    client: Client

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = Client()
        cls.client.connect(PLC_IP, PLC_RACK, PLC_SLOT, PLC_PORT)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.client:
            cls.client.disconnect()

    def test_db_get(self) -> None:
        """Test db_get() method."""
        try:
            data = self.client.db_get(DB_READ_ONLY)
        except Exception as e:
            err_msg = str(e).lower()
            if "does not exist" in err_msg or "block info failed" in err_msg or "auto-detected size" in err_msg:
                pytest.skip(f"db_get with auto-detect not supported on this PLC: {e}")
            raise
        self.assertIsInstance(data, bytearray)
        self.assertGreater(len(data), 0)


@pytest.mark.e2e
class TestClientPLCInfo(unittest.TestCase):
    """Tests for PLC information methods."""

    client: Client

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = Client()
        cls.client.connect(PLC_IP, PLC_RACK, PLC_SLOT, PLC_PORT)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.client:
            cls.client.disconnect()

    def test_get_cpu_info(self) -> None:
        """Test get_cpu_info() method."""
        try:
            cpu_info = self.client.get_cpu_info()
        except Exception as e:
            if "does not exist" in str(e).lower():
                pytest.skip(f"SZL not available on this PLC: {e}")
            raise
        self.assertIsNotNone(cpu_info.ModuleTypeName)

    def test_get_cpu_state(self) -> None:
        """Test get_cpu_state() method."""
        state = self.client.get_cpu_state()
        self.assertIn(state, ["S7CpuStatusRun", "S7CpuStatusStop", "S7CpuStatusUnknown"])

    def test_get_pdu_length(self) -> None:
        """Test get_pdu_length() method."""
        pdu_len = self.client.get_pdu_length()
        self.assertGreater(pdu_len, 0)
        self.assertLessEqual(pdu_len, 960)

    def test_get_plc_datetime(self) -> None:
        """Test get_plc_datetime() method."""
        plc_time = self.client.get_plc_datetime()
        self.assertIsInstance(plc_time, datetime)
        # PLC time should be reasonably close to now
        self.assertAlmostEqual(
            plc_time.timestamp(),
            datetime.now().timestamp(),
            delta=3600,  # Within 1 hour
        )

    def test_get_cp_info(self) -> None:
        """Test get_cp_info() method."""
        try:
            cp_info = self.client.get_cp_info()
        except Exception as e:
            if "does not exist" in str(e).lower():
                pytest.skip(f"SZL not available on this PLC: {e}")
            raise
        self.assertGreater(cp_info.MaxPduLength, 0)

    def test_get_order_code(self) -> None:
        """Test get_order_code() method."""
        try:
            order_code = self.client.get_order_code()
        except Exception as e:
            if "does not exist" in str(e).lower():
                pytest.skip(f"SZL not available on this PLC: {e}")
            raise
        self.assertIsNotNone(order_code.OrderCode)

    def test_get_protection(self) -> None:
        """Test get_protection() method."""
        try:
            protection = self.client.get_protection()
        except Exception as e:
            if "does not exist" in str(e).lower():
                pytest.skip(f"SZL not available on this PLC: {e}")
            raise
        self.assertIsNotNone(protection)

    def test_get_exec_time(self) -> None:
        """Test get_exec_time() method."""
        # Perform an operation first
        self.client.db_read(DB_READ_ONLY, 0, 1)
        exec_time = self.client.get_exec_time()
        self.assertIsInstance(exec_time, int)
        self.assertGreaterEqual(exec_time, 0)

    def test_get_last_error(self) -> None:
        """Test get_last_error() method."""
        error = self.client.get_last_error()
        self.assertIsInstance(error, int)


@pytest.mark.e2e
class TestClientBlockOperations(unittest.TestCase):
    """Tests for block operation methods."""

    client: Client

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = Client()
        cls.client.connect(PLC_IP, PLC_RACK, PLC_SLOT, PLC_PORT)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.client:
            cls.client.disconnect()

    def test_list_blocks(self) -> None:
        """Test list_blocks() method."""
        try:
            blocks = self.client.list_blocks()
        except Exception as e:
            pytest.skip(f"list_blocks not supported on this PLC: {e}")
        self.assertIsNotNone(blocks)
        # Should have at least our test DBs
        self.assertGreaterEqual(blocks.DBCount, 2)

    def test_list_blocks_of_type(self) -> None:
        """Test list_blocks_of_type() method."""
        try:
            db_list = self.client.list_blocks_of_type(Block.DB, 100)
        except Exception as e:
            pytest.skip(f"list_blocks_of_type not supported on this PLC: {e}")
        self.assertIsInstance(db_list, list)
        # Should contain our test DBs
        self.assertIn(DB_READ_ONLY, db_list)
        self.assertIn(DB_READ_WRITE, db_list)

    def test_get_block_info(self) -> None:
        """Test get_block_info() method."""
        try:
            block_info = self.client.get_block_info(Block.DB, DB_READ_ONLY)
        except Exception as e:
            pytest.skip(f"get_block_info not supported on this PLC: {e}")
        self.assertEqual(DB_READ_ONLY, block_info.BlkNumber)


@pytest.mark.e2e
class TestClientSZL(unittest.TestCase):
    """Tests for SZL (System Status List) methods."""

    client: Client

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = Client()
        cls.client.connect(PLC_IP, PLC_RACK, PLC_SLOT, PLC_PORT)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.client:
            cls.client.disconnect()

    def test_read_szl(self) -> None:
        """Test read_szl() method."""
        try:
            # Read CPU identification (SZL 0x001C)
            szl = self.client.read_szl(0x001C, 0)
        except Exception as e:
            if "does not exist" in str(e).lower():
                pytest.skip(f"SZL not available on this PLC: {e}")
            raise
        self.assertIsNotNone(szl)

    def test_read_szl_list(self) -> None:
        """Test read_szl_list() method."""
        try:
            szl_list = self.client.read_szl_list()
        except Exception as e:
            if "does not exist" in str(e).lower():
                pytest.skip(f"SZL not available on this PLC: {e}")
            raise
        self.assertIsInstance(szl_list, bytes)
        self.assertGreater(len(szl_list), 0)


@pytest.mark.e2e
class TestClientParameters(unittest.TestCase):
    """Tests for parameter methods."""

    client: Client

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = Client()
        cls.client.connect(PLC_IP, PLC_RACK, PLC_SLOT, PLC_PORT)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.client:
            cls.client.disconnect()

    def test_get_param(self) -> None:
        """Test get_param() method."""
        pdu_request = self.client.get_param(Parameter.PDURequest)
        self.assertGreater(pdu_request, 0)

    def test_set_param(self) -> None:
        """Test set_param() method."""
        # Set ping timeout
        self.client.set_param(Parameter.PingTimeout, 1000)
        # Note: get_param may not reflect all changes

    def test_set_connection_params(self) -> None:
        """Test set_connection_params() method."""
        # This just sets internal values, doesn't affect current connection
        self.client.set_connection_params("192.168.1.1", 0x0100, 0x0102)

    def test_set_connection_type(self) -> None:
        """Test set_connection_type() method."""
        self.client.set_connection_type(1)  # PG
        self.client.set_connection_type(2)  # OP
        self.client.set_connection_type(3)  # S7Basic

    def test_set_session_password(self) -> None:
        """Test set_session_password() method."""
        result = self.client.set_session_password("testpass")
        self.assertEqual(0, result)

    def test_clear_session_password(self) -> None:
        """Test clear_session_password() method."""
        result = self.client.clear_session_password()
        self.assertEqual(0, result)


@pytest.mark.e2e
class TestClientMisc(unittest.TestCase):
    """Tests for miscellaneous methods."""

    client: Client

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = Client()
        cls.client.connect(PLC_IP, PLC_RACK, PLC_SLOT, PLC_PORT)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.client:
            cls.client.disconnect()

    def test_error_text(self) -> None:
        """Test error_text() method."""
        text = self.client.error_text(0)
        self.assertEqual("OK", text)

        text = self.client.error_text(0x01E00000)
        self.assertEqual("CPU : Invalid password", text)

    def test_iso_exchange_buffer(self) -> None:
        """Test iso_exchange_buffer() method."""
        # Write a value first
        self.client.db_write(DB_READ_WRITE, 0, bytearray(b"\x00\x01"))

        # Build a raw PDU to read DB2 offset 0, 1 byte
        pdu = bytearray(
            [
                0x32,
                0x01,  # Protocol ID, PDU type (request)
                0x00,
                0x00,  # Reserved
                0x00,
                0x01,  # Sequence
                0x00,
                0x0E,  # Parameter length
                0x00,
                0x00,  # Data length
                0x04,  # Function: Read Var
                0x01,  # Item count
                0x12,  # Var spec length
                0x0A,  # Var spec syntax ID
                0x10,  # Transport size (byte)
                0x02,  # Length: 2 bytes
                0x00,
                0x01,  # Amount: 1
                0x00,
                DB_READ_WRITE,  # DB number
                0x84,  # Area: DB
                0x00,
                0x00,
                0x00,  # Address: byte 0, bit 0
            ]
        )

        response = self.client.iso_exchange_buffer(pdu)
        self.assertIsInstance(response, bytearray)
        self.assertGreater(len(response), 0)
