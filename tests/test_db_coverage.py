"""Tests for snap7.util.db — DB/Row dict-like interface, read/write with mocked client, type conversions."""

import datetime
import logging
import struct
import pytest
from unittest.mock import MagicMock

from snap7 import DB, Row
from snap7.type import Area
from snap7.util.db import print_row

# Reuse the test spec and bytearray from test_util.py
test_spec = """
4       ID           INT
6       NAME         STRING[4]

12.0    testbool1    BOOL
12.1    testbool2    BOOL
13      testReal     REAL
17      testDword    DWORD
21      testint2     INT
23      testDint     DINT
27      testWord     WORD
29      testS5time   S5TIME
31      testdateandtime DATE_AND_TIME
43      testusint0   USINT
44      testsint0    SINT
46      testTime     TIME
50      testByte     BYTE
51      testUint     UINT
53      testUdint    UDINT
57      testLreal    LREAL
65      testChar     CHAR
66      testWchar    WCHAR
68      testWstring  WSTRING[4]
80      testDate     DATE
82      testTod      TOD
86      testDtl      DTL
98      testFstring  FSTRING[8]
"""

_bytearray = bytearray(
    [
        0,
        0,  # test int
        4,
        4,
        ord("t"),
        ord("e"),
        ord("s"),
        ord("t"),  # test string
        0x0F,  # test bools
        68,
        78,
        211,
        51,  # test real
        255,
        255,
        255,
        255,  # test dword
        0,
        0,  # test int 2
        128,
        0,
        0,
        0,  # test dint
        255,
        255,  # test word
        0,
        16,  # test s5time
        32,
        7,
        18,
        23,
        50,
        2,
        133,
        65,  # date_and_time (8 bytes)
        254,
        254,
        254,
        254,
        254,  # padding
        127,  # usint
        128,  # sint
        143,
        255,
        255,
        255,  # time
        254,  # byte
        48,
        57,  # uint
        7,
        91,
        205,
        21,  # udint
        65,
        157,
        111,
        52,
        84,
        126,
        107,
        117,  # lreal
        65,  # char 'A'
        3,
        169,  # wchar
        0,
        4,
        0,
        4,
        3,
        169,
        0,
        ord("s"),
        0,
        ord("t"),
        0,
        196,  # wstring
        45,
        235,  # date
        2,
        179,
        41,
        128,  # tod
        7,
        230,
        3,
        9,
        4,
        12,
        34,
        45,
        0,
        0,
        0,
        0,  # dtl
        116,
        101,
        115,
        116,
        32,
        32,
        32,
        32,  # fstring 'test    '
    ]
)


class TestPrintRow:
    def test_print_row_output(self, caplog: pytest.LogCaptureFixture) -> None:
        data = bytearray([65, 66, 67, 68, 69])
        with caplog.at_level(logging.INFO, logger="snap7.util.db"):
            print_row(data)
        assert "65" in caplog.text
        assert "A" in caplog.text


class TestDBDictInterface:
    def setup_method(self) -> None:
        test_array = bytearray(_bytearray * 3)
        self.db = DB(1, test_array, test_spec, row_size=len(_bytearray), size=3, layout_offset=4, db_offset=0)

    def test_len(self) -> None:
        assert len(self.db) == 3

    def test_getitem(self) -> None:
        row = self.db["0"]
        assert row is not None

    def test_getitem_missing(self) -> None:
        row = self.db["999"]
        assert row is None

    def test_contains(self) -> None:
        assert "0" in self.db
        assert "999" not in self.db

    def test_keys(self) -> None:
        keys = list(self.db.keys())
        assert "0" in keys
        assert len(keys) == 3

    def test_items(self) -> None:
        items = list(self.db.items())
        assert len(items) == 3
        for key, row in items:
            assert isinstance(key, str)
            assert isinstance(row, Row)

    def test_iter(self) -> None:
        for key, row in self.db:
            assert isinstance(key, str)
            assert isinstance(row, Row)

    def test_get_bytearray(self) -> None:
        ba = self.db.get_bytearray()
        assert isinstance(ba, bytearray)


class TestDBWithIdField:
    def test_id_field_creates_named_index(self) -> None:
        test_array = bytearray(_bytearray * 2)
        # Set different ID values for each row
        struct.pack_into(">h", test_array, 0, 10)  # row 0, ID at offset 0 (spec offset 4, layout_offset 4)
        struct.pack_into(">h", test_array, len(_bytearray), 20)  # row 1
        db = DB(1, test_array, test_spec, row_size=len(_bytearray), size=2, id_field="ID", layout_offset=4, db_offset=0)
        assert "10" in db
        assert "20" in db


class TestDBSetData:
    def test_set_data_valid(self) -> None:
        test_array = bytearray(_bytearray)
        db = DB(1, test_array, test_spec, row_size=len(_bytearray), size=1, layout_offset=4, db_offset=0)
        new_data = bytearray(len(_bytearray))
        db.set_data(new_data)
        assert db.get_bytearray() is new_data

    def test_set_data_invalid_type(self) -> None:
        test_array = bytearray(_bytearray)
        db = DB(1, test_array, test_spec, row_size=len(_bytearray), size=1, layout_offset=4, db_offset=0)
        with pytest.raises(TypeError):
            db.set_data(b"not a bytearray")  # type: ignore[arg-type]


class TestDBReadWrite:
    """Test DB.read() and DB.write() with mocked client."""

    def test_read_db_area(self) -> None:
        test_array = bytearray(_bytearray)
        db = DB(1, test_array, test_spec, row_size=len(_bytearray), size=1, layout_offset=4, db_offset=0)
        mock_client = MagicMock()
        mock_client.db_read.return_value = bytearray(len(_bytearray))
        db.read(mock_client)
        mock_client.db_read.assert_called_once()

    def test_read_non_db_area(self) -> None:
        test_array = bytearray(_bytearray)
        db = DB(0, test_array, test_spec, row_size=len(_bytearray), size=1, layout_offset=4, db_offset=0, area=Area.MK)
        mock_client = MagicMock()
        mock_client.read_area.return_value = bytearray(len(_bytearray))
        db.read(mock_client)
        mock_client.read_area.assert_called_once()

    def test_read_negative_row_size(self) -> None:
        test_array = bytearray(_bytearray)
        db = DB(1, test_array, test_spec, row_size=len(_bytearray), size=1, layout_offset=4, db_offset=0)
        db.row_size = -1
        mock_client = MagicMock()
        with pytest.raises(ValueError, match="row_size"):
            db.read(mock_client)

    def test_write_db_area(self) -> None:
        test_array = bytearray(_bytearray)
        db = DB(1, test_array, test_spec, row_size=len(_bytearray), size=1, layout_offset=4, db_offset=0)
        mock_client = MagicMock()
        db.write(mock_client)
        mock_client.db_write.assert_called_once()

    def test_write_non_db_area(self) -> None:
        test_array = bytearray(_bytearray)
        db = DB(0, test_array, test_spec, row_size=len(_bytearray), size=1, layout_offset=4, db_offset=0, area=Area.MK)
        mock_client = MagicMock()
        db.write(mock_client)
        mock_client.write_area.assert_called_once()

    def test_write_negative_row_size(self) -> None:
        test_array = bytearray(_bytearray)
        db = DB(1, test_array, test_spec, row_size=len(_bytearray), size=1, layout_offset=4, db_offset=0)
        db.row_size = -1
        mock_client = MagicMock()
        with pytest.raises(ValueError, match="row_size"):
            db.write(mock_client)

    def test_write_with_row_offset(self) -> None:
        test_array = bytearray(_bytearray * 2)
        db = DB(1, test_array, test_spec, row_size=len(_bytearray), size=2, layout_offset=4, db_offset=0, row_offset=4)
        mock_client = MagicMock()
        db.write(mock_client)
        # Should write each row individually via Row.write()
        assert mock_client.db_write.call_count == 2


class TestRowRepr:
    def test_repr(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        r = repr(row)
        assert "ID" in r
        assert "NAME" in r


class TestRowUnchanged:
    def test_unchanged_true(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        assert row.unchanged(test_array) is True

    def test_unchanged_false(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        other = bytearray(len(_bytearray))
        assert row.unchanged(other) is False


class TestRowTypeError:
    def test_invalid_bytearray_type(self) -> None:
        with pytest.raises(TypeError):
            Row("not a bytearray", test_spec)  # type: ignore[arg-type]


class TestRowReadWrite:
    """Test Row.read() and Row.write() with mocked client through DB parent."""

    def test_row_write_db_area(self) -> None:
        test_array = bytearray(_bytearray)
        db = DB(1, test_array, test_spec, row_size=len(_bytearray), size=1, layout_offset=4, db_offset=0)
        row = db["0"]
        assert row is not None
        mock_client = MagicMock()
        row.write(mock_client)
        mock_client.db_write.assert_called_once()

    def test_row_write_non_db_area(self) -> None:
        test_array = bytearray(_bytearray)
        db = DB(0, test_array, test_spec, row_size=len(_bytearray), size=1, layout_offset=4, db_offset=0, area=Area.MK)
        row = db["0"]
        assert row is not None
        mock_client = MagicMock()
        row.write(mock_client)
        mock_client.write_area.assert_called_once()

    def test_row_write_not_db_parent(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        mock_client = MagicMock()
        with pytest.raises(TypeError):
            row.write(mock_client)

    def test_row_write_negative_row_size(self) -> None:
        test_array = bytearray(_bytearray)
        db = DB(1, test_array, test_spec, row_size=len(_bytearray), size=1, layout_offset=4, db_offset=0)
        row = db["0"]
        assert row is not None
        row.row_size = -1
        mock_client = MagicMock()
        with pytest.raises(ValueError, match="row_size"):
            row.write(mock_client)

    def test_row_read_db_area(self) -> None:
        test_array = bytearray(_bytearray)
        db = DB(1, test_array, test_spec, row_size=len(_bytearray), size=1, layout_offset=4, db_offset=0)
        row = db["0"]
        assert row is not None
        mock_client = MagicMock()
        mock_client.db_read.return_value = bytearray(len(_bytearray))
        row.read(mock_client)
        mock_client.db_read.assert_called_once()

    def test_row_read_non_db_area(self) -> None:
        test_array = bytearray(_bytearray)
        db = DB(0, test_array, test_spec, row_size=len(_bytearray), size=1, layout_offset=4, db_offset=0, area=Area.MK)
        row = db["0"]
        assert row is not None
        mock_client = MagicMock()
        mock_client.read_area.return_value = bytearray(len(_bytearray))
        row.read(mock_client)
        mock_client.read_area.assert_called_once()

    def test_row_read_not_db_parent(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        mock_client = MagicMock()
        with pytest.raises(TypeError):
            row.read(mock_client)

    def test_row_read_negative_row_size(self) -> None:
        test_array = bytearray(_bytearray)
        db = DB(1, test_array, test_spec, row_size=len(_bytearray), size=1, layout_offset=4, db_offset=0)
        row = db["0"]
        assert row is not None
        row.row_size = -1
        mock_client = MagicMock()
        with pytest.raises(ValueError, match="row_size"):
            row.read(mock_client)


class TestRowSetValueTypes:
    """Test set_value for various type branches."""

    def setup_method(self) -> None:
        self.test_array = bytearray(_bytearray)
        self.row = Row(self.test_array, test_spec, layout_offset=4)

    def test_set_int(self) -> None:
        self.row.set_value(4, "INT", 42)
        assert self.row.get_value(4, "INT") == 42

    def test_set_uint(self) -> None:
        self.row.set_value(51, "UINT", 1000)
        assert self.row.get_value(51, "UINT") == 1000

    def test_set_dint(self) -> None:
        self.row.set_value(23, "DINT", -100)
        assert self.row.get_value(23, "DINT") == -100

    def test_set_udint(self) -> None:
        self.row.set_value(53, "UDINT", 999999)
        assert self.row.get_value(53, "UDINT") == 999999

    def test_set_word(self) -> None:
        self.row.set_value(27, "WORD", 12345)
        assert self.row.get_value(27, "WORD") == 12345

    def test_set_usint(self) -> None:
        self.row.set_value(43, "USINT", 200)
        assert self.row.get_value(43, "USINT") == 200

    def test_set_sint(self) -> None:
        self.row.set_value(44, "SINT", -50)
        assert self.row.get_value(44, "SINT") == -50

    def test_set_time(self) -> None:
        self.row.set_value(46, "TIME", "1:2:3:4.5")
        assert self.row.get_value(46, "TIME") is not None

    def test_set_date(self) -> None:
        d = datetime.date(2024, 1, 15)
        self.row.set_value(80, "DATE", d)
        assert self.row.get_value(80, "DATE") == d

    def test_set_tod(self) -> None:
        td = datetime.timedelta(hours=5, minutes=30)
        self.row.set_value(82, "TOD", td)
        assert self.row.get_value(82, "TOD") == td

    def test_set_time_of_day(self) -> None:
        td = datetime.timedelta(hours=1)
        self.row.set_value(82, "TIME_OF_DAY", td)
        assert self.row.get_value(82, "TIME_OF_DAY") == td

    def test_set_dtl(self) -> None:
        dt = datetime.datetime(2024, 6, 15, 10, 20, 30)
        self.row.set_value(86, "DTL", dt)
        result = self.row.get_value(86, "DTL")
        assert result.year == 2024  # type: ignore[union-attr]

    def test_set_date_and_time(self) -> None:
        dt = datetime.datetime(2020, 7, 12, 17, 32, 2, 854000)
        self.row.set_value(31, "DATE_AND_TIME", dt)
        result = self.row.get_value(31, "DATE_AND_TIME")
        assert "2020" in str(result)

    def test_set_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError):
            self.row.set_value(4, "UNKNOWN_TYPE", 42)

    def test_set_string(self) -> None:
        self.row.set_value(6, "STRING[4]", "ab")
        assert self.row.get_value(6, "STRING[4]") == "ab"

    def test_set_wstring(self) -> None:
        self.row.set_value(68, "WSTRING[4]", "ab")
        assert self.row.get_value(68, "WSTRING[4]") == "ab"

    def test_set_fstring(self) -> None:
        self.row.set_value(98, "FSTRING[8]", "hi")
        assert self.row.get_value(98, "FSTRING[8]") == "hi"

    def test_set_real(self) -> None:
        self.row.set_value(13, "REAL", 3.14)
        assert abs(self.row.get_value(13, "REAL") - 3.14) < 0.01  # type: ignore[operator]

    def test_set_lreal(self) -> None:
        self.row.set_value(57, "LREAL", 2.718281828)
        assert abs(self.row.get_value(57, "LREAL") - 2.718281828) < 0.0001  # type: ignore[operator]

    def test_set_char(self) -> None:
        self.row.set_value(65, "CHAR", "Z")
        assert self.row.get_value(65, "CHAR") == "Z"

    def test_set_wchar(self) -> None:
        self.row.set_value(66, "WCHAR", "W")
        assert self.row.get_value(66, "WCHAR") == "W"


class TestRowGetValueEdgeCases:
    """Test get_value for edge cases."""

    def setup_method(self) -> None:
        self.test_array = bytearray(_bytearray)
        self.row = Row(self.test_array, test_spec, layout_offset=4)

    def test_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError):
            self.row.get_value(4, "NONEXISTENT")

    def test_string_no_max_size(self) -> None:
        spec = "4    test    STRING"
        row = Row(bytearray(20), spec, layout_offset=0)
        with pytest.raises(ValueError, match="Max size"):
            row.get_value(4, "STRING")

    def test_fstring_no_max_size(self) -> None:
        with pytest.raises(ValueError, match="Max size"):
            self.row.get_value(98, "FSTRING")

    def test_wstring_no_max_size(self) -> None:
        with pytest.raises(ValueError, match="Max size"):
            self.row.get_value(68, "WSTRING")


class TestRowSetValueEdgeCases:
    """Test set_value edge cases for string types."""

    def setup_method(self) -> None:
        self.test_array = bytearray(_bytearray)
        self.row = Row(self.test_array, test_spec, layout_offset=4)

    def test_fstring_no_max_size(self) -> None:
        with pytest.raises(ValueError, match="Max size"):
            self.row.set_value(98, "FSTRING", "test")

    def test_string_no_max_size(self) -> None:
        with pytest.raises(ValueError, match="Max size"):
            self.row.set_value(6, "STRING", "test")

    def test_wstring_no_max_size(self) -> None:
        with pytest.raises(ValueError, match="Max size"):
            self.row.set_value(68, "WSTRING", "test")


class TestRowWriteWithRowOffset:
    """Test Row.write() with row_offset set."""

    def test_write_with_row_offset(self) -> None:
        test_array = bytearray(_bytearray)
        db = DB(1, test_array, test_spec, row_size=len(_bytearray), size=1, layout_offset=4, db_offset=0, row_offset=10)
        row = db["0"]
        assert row is not None
        mock_client = MagicMock()
        row.write(mock_client)
        # The data written should start at db_offset + row_offset
        mock_client.db_write.assert_called_once()
