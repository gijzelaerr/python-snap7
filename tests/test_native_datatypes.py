"""
Tests for S7 data types and conversion utilities.
"""

import pytest
import struct

from snap7.datatypes import S7Area, S7WordLen, S7DataTypes


class TestS7DataTypes:
    """Test S7 data type utilities."""

    def test_get_size_bytes(self):
        """Test size calculation for different word lengths."""
        assert S7DataTypes.get_size_bytes(S7WordLen.BIT, 1) == 1
        assert S7DataTypes.get_size_bytes(S7WordLen.BYTE, 1) == 1
        assert S7DataTypes.get_size_bytes(S7WordLen.WORD, 1) == 2
        assert S7DataTypes.get_size_bytes(S7WordLen.DWORD, 1) == 4
        assert S7DataTypes.get_size_bytes(S7WordLen.REAL, 1) == 4

        # Test with multiple items
        assert S7DataTypes.get_size_bytes(S7WordLen.WORD, 5) == 10
        assert S7DataTypes.get_size_bytes(S7WordLen.BYTE, 10) == 10

    def test_encode_address_db(self):
        """Test address encoding for DB area."""
        address = S7DataTypes.encode_address(area=S7Area.DB, db_number=1, start=10, word_len=S7WordLen.BYTE, count=5)

        assert len(address) == 12
        assert address[0] == 0x12  # Specification type
        assert address[1] == 0x0A  # Length
        assert address[2] == 0x10  # Syntax ID
        assert address[3] == S7WordLen.BYTE  # Word length

        # Verify count and DB number
        count_bytes = address[4:6]
        db_bytes = address[6:8]
        assert struct.unpack(">H", count_bytes)[0] == 5
        assert struct.unpack(">H", db_bytes)[0] == 1

        # Verify area code
        assert address[8] == S7Area.DB

    def test_encode_address_memory(self):
        """Test address encoding for memory areas."""
        address = S7DataTypes.encode_address(
            area=S7Area.MK,
            db_number=0,  # Should be ignored for non-DB areas
            start=20,
            word_len=S7WordLen.WORD,
            count=1,
        )

        assert len(address) == 12
        assert address[8] == S7Area.MK

        # DB number should be 0 for non-DB areas
        db_bytes = address[6:8]
        assert struct.unpack(">H", db_bytes)[0] == 0

    def test_encode_address_bit_access(self):
        """Test address encoding for bit access."""
        # Test bit access: bit 5 of byte 10 = bit 85
        address = S7DataTypes.encode_address(
            area=S7Area.MK,
            db_number=0,
            start=85,  # Bit 5 of byte 10
            word_len=S7WordLen.BIT,
            count=1,
        )

        # For bit access, address should be converted to byte.bit format
        address_bytes = address[9:12]
        bit_address = struct.unpack(">I", b"\x00" + address_bytes)[0]

        # Should be (10 << 3) | 5 = 85
        assert bit_address == 85

    def test_decode_s7_data_bytes(self):
        """Test decoding byte data."""
        data = b"\x01\x02\x03\x04"
        values = S7DataTypes.decode_s7_data(data, S7WordLen.BYTE, 4)

        assert len(values) == 4
        assert values == [1, 2, 3, 4]

    def test_decode_s7_data_words(self):
        """Test decoding word data."""
        # Big-endian 16-bit words: 0x0102, 0x0304
        data = b"\x01\x02\x03\x04"
        values = S7DataTypes.decode_s7_data(data, S7WordLen.WORD, 2)

        assert len(values) == 2
        assert values == [0x0102, 0x0304]

    def test_decode_s7_data_signed_int(self):
        """Test decoding signed integers."""
        # Big-endian signed 16-bit: -1, 1000
        data = b"\xff\xff\x03\xe8"
        values = S7DataTypes.decode_s7_data(data, S7WordLen.INT, 2)

        assert len(values) == 2
        assert values == [-1, 1000]

    def test_decode_s7_data_dwords(self):
        """Test decoding double words."""
        # Big-endian 32-bit: 0x01020304
        data = b"\x01\x02\x03\x04"
        values = S7DataTypes.decode_s7_data(data, S7WordLen.DWORD, 1)

        assert len(values) == 1
        assert values == [0x01020304]

    def test_decode_s7_data_real(self):
        """Test decoding IEEE float."""
        # Big-endian IEEE 754 float for 3.14159
        data = struct.pack(">f", 3.14159)
        values = S7DataTypes.decode_s7_data(data, S7WordLen.REAL, 1)

        assert len(values) == 1
        assert abs(values[0] - 3.14159) < 0.00001

    def test_decode_s7_data_bits(self):
        """Test decoding bit data."""
        data = b"\x01\x00\x01"
        values = S7DataTypes.decode_s7_data(data, S7WordLen.BIT, 3)

        assert len(values) == 3
        assert values == [True, False, True]

    def test_encode_s7_data_bytes(self):
        """Test encoding byte data."""
        values = [1, 2, 3, 255]
        data = S7DataTypes.encode_s7_data(values, S7WordLen.BYTE)

        assert data == b"\x01\x02\x03\xff"

    def test_encode_s7_data_words(self):
        """Test encoding word data."""
        values = [0x0102, 0x0304]
        data = S7DataTypes.encode_s7_data(values, S7WordLen.WORD)

        # Should be big-endian
        assert data == b"\x01\x02\x03\x04"

    def test_encode_s7_data_real(self):
        """Test encoding IEEE float."""
        values = [3.14159]
        data = S7DataTypes.encode_s7_data(values, S7WordLen.REAL)

        # Should be big-endian IEEE 754
        expected = struct.pack(">f", 3.14159)
        assert data == expected

    def test_encode_s7_data_bits(self):
        """Test encoding bit data."""
        values = [True, False, True, False]
        data = S7DataTypes.encode_s7_data(values, S7WordLen.BIT)

        assert data == b"\x01\x00\x01\x00"

    def test_parse_address_db(self):
        """Test parsing DB addresses."""
        # Test DB byte address
        area, db_num, offset = S7DataTypes.parse_address("DB1.DBB10")
        assert area == S7Area.DB
        assert db_num == 1
        assert offset == 10

        # Test DB word address
        area, db_num, offset = S7DataTypes.parse_address("DB5.DBW20")
        assert area == S7Area.DB
        assert db_num == 5
        assert offset == 20

        # Test DB bit address
        area, db_num, offset = S7DataTypes.parse_address("DB1.DBX10.5")
        assert area == S7Area.DB
        assert db_num == 1
        assert offset == 10 * 8 + 5  # Bit offset

    def test_parse_address_memory(self):
        """Test parsing memory addresses."""
        # Test memory byte
        area, db_num, offset = S7DataTypes.parse_address("M10")
        assert area == S7Area.MK
        assert db_num == 0
        assert offset == 10

        # Test memory word
        area, db_num, offset = S7DataTypes.parse_address("MW20")
        assert area == S7Area.MK
        assert db_num == 0
        assert offset == 20

        # Test memory bit
        area, db_num, offset = S7DataTypes.parse_address("M10.5")
        assert area == S7Area.MK
        assert db_num == 0
        assert offset == 10 * 8 + 5

    def test_parse_address_inputs(self):
        """Test parsing input addresses."""
        # Test input byte
        area, db_num, offset = S7DataTypes.parse_address("I5")
        assert area == S7Area.PE
        assert db_num == 0
        assert offset == 5

        # Test input word
        area, db_num, offset = S7DataTypes.parse_address("IW10")
        assert area == S7Area.PE
        assert db_num == 0
        assert offset == 10

        # Test input bit
        area, db_num, offset = S7DataTypes.parse_address("I0.7")
        assert area == S7Area.PE
        assert db_num == 0
        assert offset == 7

    def test_parse_address_outputs(self):
        """Test parsing output addresses."""
        # Test output byte
        area, db_num, offset = S7DataTypes.parse_address("Q3")
        assert area == S7Area.PA
        assert db_num == 0
        assert offset == 3

        # Test output word
        area, db_num, offset = S7DataTypes.parse_address("QW12")
        assert area == S7Area.PA
        assert db_num == 0
        assert offset == 12

    def test_parse_address_invalid(self):
        """Test parsing invalid addresses."""
        with pytest.raises(ValueError):
            S7DataTypes.parse_address("INVALID")

        with pytest.raises(ValueError):
            S7DataTypes.parse_address("X1.0")  # Unsupported area

    def test_parse_address_case_insensitive(self):
        """Test that address parsing is case insensitive."""
        area1, db1, offset1 = S7DataTypes.parse_address("db1.dbw10")
        area2, db2, offset2 = S7DataTypes.parse_address("DB1.DBW10")

        assert area1 == area2
        assert db1 == db2
        assert offset1 == offset2
