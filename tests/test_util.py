import datetime
import logging
import pytest
import unittest
import struct
from typing import cast
from unittest.mock import MagicMock

from snap7 import DB, Row
from snap7.type import Area, WordLen
from snap7.util import get_byte, get_time, get_fstring, get_int
from snap7.util import set_byte, set_time, set_fstring, set_int
from snap7.util.db import print_row

test_spec = """

4	    ID	         INT
6	    NAME	 STRING[4]

12.0	testbool1    BOOL
12.1	testbool2    BOOL
12.2	testbool3    BOOL
12.3	testbool4    BOOL
12.4	testbool5    BOOL
12.5	testbool6    BOOL
12.6	testbool7    BOOL
12.7	testbool8    BOOL
13      testReal     REAL
17      testDword    DWORD
21      testint2     INT
23      testDint     DINT
27      testWord     WORD
29      testS5time   S5TIME
31      testdateandtime DATE_AND_TIME
43      testusint0      USINT
44      testsint0       SINT
46      testTime     TIME
50      testByte    BYTE
51      testUint    UINT
53      testUdint   UDINT
57      testLreal   LREAL
65      testChar    CHAR
66      testWchar   WCHAR
68      testWstring WSTRING[4]
80      testDate    DATE
82      testTod     TOD
86      testDtl     DTL
98      testFstring FSTRING[8]
"""

test_spec_indented = """

    4	    ID	         INT
    6	    NAME	 STRING[4]

 12.0	testbool1    BOOL
       12.1	testbool2    BOOL
 12.2	testbool3    BOOL
#    12.3	test bool4    BOOL
 #  12.4	testbool5    BOOL
      #    12.5	testbool6    BOOL
    #   12.6	testbool7    BOOL
            12.7	testbool8    BOOL
        13      testReal     REAL
  17      testDword    DWORD
    21      testint2     INT
            23      testDint     DINT
27      testWord     WORD
    29      tests5time   S5TIME
31      testdateandtime DATE_AND_TIME
        43      testusint0      USINT
44        testsint0       SINT
        50      testByte    BYTE
    51      testUint    UINT
            53      testUdint   UDINT
57      testLreal   LREAL
        65      testChar    CHAR
66      testWchar   WCHAR
            68      testWstring WSTRING[4]
    80      testDate    DATE
82      testTod     TOD
    86      testDtl     DTL
            98      testFstring FSTRING[8]
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
        128 * 0 + 64 * 0 + 32 * 0 + 16 * 0 + 8 * 1 + 4 * 1 + 2 * 1 + 1 * 1,  # test bools
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
        16,  # test s5time, 0 is the time base,
        # 16 is value, those two integers should be declared together
        32,
        7,
        18,
        23,
        50,
        2,
        133,
        65,  # these 8 values build the date and time 12 byte total
        # data typ together, for details under this link
        # https://support.industry.siemens.com/cs/document/36479/date_and_time-format-bei-s7-?dti=0&lc=de-DE
        254,
        254,
        254,
        254,
        254,
        127,  # test small int
        128,  # test set byte
        143,
        255,
        255,
        255,  # test time
        254,  # test byte              0xFE
        48,
        57,  # test uint              12345
        7,
        91,
        205,
        21,  # test udint             123456789
        65,
        157,
        111,
        52,
        84,
        126,
        107,
        117,  # test lreal             123456789.123456789
        65,  # test char              A
        3,
        169,  # test wchar             Ω
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
        196,  # test wstring   Ω s t Ä
        45,
        235,  # test date              09.03.2022
        2,
        179,
        41,
        128,  # test tod               12:34:56
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
        0,  # test dtl               09.03.2022 12:34:56
        116,
        101,
        115,
        116,
        32,
        32,
        32,
        32,  # test fstring           'test    '
    ]
)

_new_bytearray = bytearray(100)
_new_bytearray[41 : 41 + 1] = struct.pack("B", 128)  # byte_index=41, value=128, bytes=1
_new_bytearray[42 : 42 + 1] = struct.pack("B", 255)  # byte_index=41, value=255, bytes=1
_new_bytearray[43 : 43 + 4] = struct.pack("I", 286331153)  # byte_index=43, value=286331153(T#3D_7H_32M_11S_153MS), bytes=4


@pytest.mark.util
class TestS7util(unittest.TestCase):
    def test_get_byte_new(self) -> None:
        test_array = bytearray(_new_bytearray)
        byte_ = get_byte(test_array, 41)
        self.assertEqual(byte_, 128)
        byte_ = get_byte(test_array, 42)
        self.assertEqual(byte_, 255)

    def test_set_byte_new(self) -> None:
        test_array = bytearray(_new_bytearray)
        set_byte(test_array, 41, 127)
        byte_ = get_byte(test_array, 41)
        self.assertEqual(byte_, 127)

    def test_get_byte(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        value = row.get_value(50, "BYTE")  # get value
        self.assertEqual(value, 254)

    def test_set_byte(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        row["testByte"] = 255
        self.assertEqual(row["testByte"], 255)

    def test_set_char(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        row["testChar"] = chr(65)
        self.assertEqual(row["testChar"], "A")

    def test_set_lreal(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        row["testLreal"] = 123.123
        self.assertEqual(row["testLreal"], 123.123)

    def test_get_s5time(self) -> None:
        """
        S5TIME extraction from bytearray
        """
        test_array = bytearray(_bytearray)

        row = Row(test_array, test_spec, layout_offset=4)

        self.assertEqual(row["testS5time"], "0:00:00.100000")

    def test_get_dt(self) -> None:
        """
        DATE_AND_TIME extraction from bytearray
        """
        test_array = bytearray(_bytearray)

        row = Row(test_array, test_spec, layout_offset=4)

        self.assertEqual(row["testdateandtime"], "2020-07-12T17:32:02.854000")

    def test_get_time(self) -> None:
        test_values = [
            (0, "0:0:0:0.0"),
            (1, "0:0:0:0.1"),  # T#1MS
            (1000, "0:0:0:1.0"),  # T#1S
            (60000, "0:0:1:0.0"),  # T#1M
            (3600000, "0:1:0:0.0"),  # T#1H
            (86400000, "1:0:0:0.0"),  # T#1D
            (2147483647, "24:20:31:23.647"),  # max range
            (-0, "0:0:0:0.0"),
            (-1, "-0:0:0:0.1"),  # T#-1MS
            (-1000, "-0:0:0:1.0"),  # T#-1S
            (-60000, "-0:0:1:0.0"),  # T#-1M
            (-3600000, "-0:1:0:0.0"),  # T#-1H
            (-86400000, "-1:0:0:0.0"),  # T#-1D
            (-2147483647, "-24:20:31:23.647"),  # min range
        ]

        data = bytearray(4)
        for value_to_test, expected_value in test_values:
            data[:] = struct.pack(">i", value_to_test)
            self.assertEqual(get_time(data, 0), expected_value)

    def test_set_time(self) -> None:
        test_array = bytearray(_new_bytearray)

        with self.assertRaises(ValueError):
            set_time(test_array, 43, "-24:25:30:23:193")
        with self.assertRaises(ValueError):
            set_time(test_array, 43, "-24:24:32:11.648")
        with self.assertRaises(ValueError):
            set_time(test_array, 43, "-25:23:32:11.648")
        with self.assertRaises(ValueError):
            set_time(test_array, 43, "24:24:30:23.620")

        set_time(test_array, 43, "24:20:31:23.647")
        byte_ = get_time(test_array, 43)
        self.assertEqual(byte_, "24:20:31:23.647")

        set_time(test_array, 43, "-24:20:31:23.648")
        byte_ = get_time(test_array, 43)
        self.assertEqual(byte_, "-24:20:31:23.648")

        set_time(test_array, 43, "3:7:32:11.153")
        byte_ = get_time(test_array, 43)
        self.assertEqual(byte_, "3:7:32:11.153")

    def test_get_string(self) -> None:
        """
        Text extraction from string from bytearray
        """
        test_array = bytearray(_bytearray)

        row = Row(test_array, test_spec, layout_offset=4)
        self.assertEqual(row["NAME"], "test")

    def test_write_string(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        row["NAME"] = "abc"
        self.assertEqual(row["NAME"], "abc")
        row["NAME"] = ""
        self.assertEqual(row["NAME"], "")
        try:
            row["NAME"] = "waaaaytoobig"
        except ValueError:
            pass
        # value should still be empty
        self.assertEqual(row["NAME"], "")
        row["NAME"] = "TrÖt"
        self.assertEqual(row["NAME"], "TrÖt")
        try:
            row["NAME"] = "TrĪt"
        except ValueError:
            pass

    def test_get_fstring(self) -> None:
        data = bytearray(ord(letter) for letter in "hello world    ")
        self.assertEqual(get_fstring(data, 0, 15), "hello world")
        self.assertEqual(get_fstring(data, 0, 15, remove_padding=False), "hello world    ")

    def test_get_fstring_name(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        value = row["testFstring"]
        self.assertEqual(value, "test")

    def test_get_fstring_index(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        value = row.get_value(98, "FSTRING[8]")  # get value
        self.assertEqual(value, "test")

    def test_set_fstring(self) -> None:
        data = bytearray(20)
        set_fstring(data, 0, "hello world", 15)
        self.assertEqual(data, bytearray(b"hello world    \x00\x00\x00\x00\x00"))

    def test_set_fstring_name(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        row["testFstring"] = "TSET"
        self.assertEqual(row["testFstring"], "TSET")

    def test_set_fstring_index(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        row.set_value(98, "FSTRING[8]", "TSET")
        self.assertEqual(row["testFstring"], "TSET")

    def test_get_int(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        x = row["ID"]
        y = row["testint2"]
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)

    def test_set_int(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        row["ID"] = 259
        self.assertEqual(row["ID"], 259)

    def test_get_usint(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        value = row.get_value(43, "USINT")  # get value
        self.assertEqual(value, 254)

    def test_set_usint(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        row["testusint0"] = 255
        self.assertEqual(row["testusint0"], 255)

    def test_get_sint(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        value = row.get_value(44, "SINT")  # get value
        self.assertEqual(value, 127)

    def test_set_sint(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        row["testsint0"] = 127
        self.assertEqual(row["testsint0"], 127)

    def test_set_int_roundtrip(self) -> None:
        DB1 = cast(bytearray, (WordLen.Byte.ctype * 4)())

        for i in range(-(2**15) + 1, (2**15) - 1):
            set_int(DB1, 0, i)
            result = get_int(DB1, 0)
            self.assertEqual(i, result)

    def test_get_int_values(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        for value in (-32768, -16385, -256, -128, -127, 0, 127, 128, 255, 256, 16384, 32767):
            row["ID"] = value
            self.assertEqual(row["ID"], value)

    def test_get_bool(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        self.assertEqual(row["testbool1"], 1)
        self.assertEqual(row["testbool8"], 0)

    def test_set_bool(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        row["testbool8"] = True
        row["testbool1"] = False

        self.assertEqual(row["testbool8"], True)
        self.assertEqual(row["testbool1"], False)

    def test_db_creation(self) -> None:
        test_array = bytearray(_bytearray * 10)

        test_db = DB(1, test_array, test_spec, row_size=len(_bytearray), size=10, layout_offset=4, db_offset=0)

        self.assertEqual(len(test_db.index), 10)

        for i, row in test_db:
            # print row
            self.assertEqual(row["testbool1"], 1)
            self.assertEqual(row["testbool2"], 1)
            self.assertEqual(row["testbool3"], 1)
            self.assertEqual(row["testbool4"], 1)
            self.assertEqual(row["testbool5"], 0)
            self.assertEqual(row["testbool6"], 0)
            self.assertEqual(row["testbool7"], 0)
            self.assertEqual(row["testbool8"], 0)
            self.assertEqual(row["NAME"], "test")

    def test_db_creation_vars_with_whitespace(self) -> None:
        test_array = bytearray(_bytearray * 1)
        test_spec = """
        50      testZeroSpaces    BYTE
        52      testOne Space    BYTE
        59      testTWo  Spaces   BYTE
"""

        test_db = DB(1, test_array, test_spec, row_size=len(_bytearray), size=1, layout_offset=0, db_offset=0)
        db_export = test_db.export()
        for i in db_export:
            self.assertTrue("testZeroSpaces" in db_export[i].keys())
            self.assertTrue("testOne Space" in db_export[i].keys())
            self.assertTrue("testTWo  Spaces" in db_export[i].keys())

    def test_db_export(self) -> None:
        test_array = bytearray(_bytearray * 10)
        test_db = DB(1, test_array, test_spec, row_size=len(_bytearray), size=10, layout_offset=4, db_offset=0)

        db_export = test_db.export()
        for i in db_export:
            self.assertEqual(db_export[i]["testbool1"], 1)
            self.assertEqual(db_export[i]["testbool2"], 1)
            self.assertEqual(db_export[i]["testbool3"], 1)
            self.assertEqual(db_export[i]["testbool4"], 1)

            self.assertEqual(db_export[i]["testbool5"], 0)
            self.assertEqual(db_export[i]["testbool6"], 0)
            self.assertEqual(db_export[i]["testbool7"], 0)
            self.assertEqual(db_export[i]["testbool8"], 0)
            self.assertEqual(db_export[i]["NAME"], "test")

    def test_get_real(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        self.assertTrue(0.01 > (row["testReal"] - 827.3) > -0.1)

    def test_set_real(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        row["testReal"] = 1337.1337
        self.assertTrue(0.01 > (row["testReal"] - 1337.1337) > -0.01)

    def test_set_dword(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        # The range of numbers is 0 to 4294967295.
        row["testDword"] = 9999999
        self.assertEqual(row["testDword"], 9999999)

    def test_get_dword(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        self.assertEqual(row["testDword"], 4294967295)

    def test_set_dint(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        # The range of numbers is -2147483648 to 2147483647 +
        row.set_value(23, "DINT", 2147483647)  # set value
        self.assertEqual(row["testDint"], 2147483647)

    def test_get_dint(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        value = row.get_value(23, "DINT")  # get value
        self.assertEqual(value, -2147483648)

    def test_set_word(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        # The range of numbers is 0 to 65535
        row.set_value(27, "WORD", 0)  # set value
        self.assertEqual(row["testWord"], 0)

    def test_get_word(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        value = row.get_value(27, "WORD")  # get value
        self.assertEqual(value, 65535)

    def test_export(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        data = row.export()
        self.assertIn("testDword", data)
        self.assertIn("testbool1", data)
        self.assertEqual(data["testbool5"], 0)

    def test_indented_layout(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec_indented, layout_offset=4)
        x = row["ID"]
        y_single_space = row["testbool1"]
        y_multi_space = row["testbool2"]
        y_single_indent = row["testint2"]
        y_multi_indent = row["testbool8"]

        with self.assertRaises(KeyError):
            fail_single_space = row["testbool4"]  # noqa: F841
        with self.assertRaises(KeyError):
            fail_multiple_spaces = row["testbool5"]  # noqa: F841
        with self.assertRaises(KeyError):
            fail_single_indent = row["testbool6"]  # noqa: F841
        with self.assertRaises(KeyError):
            fail_multiple_indent = row["testbool7"]  # noqa: F841

        self.assertEqual(x, 0)
        self.assertEqual(y_single_space, True)
        self.assertEqual(y_multi_space, True)
        self.assertEqual(y_single_indent, 0)
        self.assertEqual(y_multi_indent, 0)

    def test_get_uint(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec_indented, layout_offset=4)
        val = row["testUint"]
        self.assertEqual(val, 12345)

    def test_get_udint(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec_indented, layout_offset=4)
        val = row["testUdint"]
        self.assertEqual(val, 123456789)

    def test_get_lreal(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec_indented, layout_offset=4)
        val = row["testLreal"]
        self.assertEqual(val, 123456789.123456789)

    def test_get_char(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec_indented, layout_offset=4)
        val = row["testChar"]
        self.assertEqual(val, "A")

    def test_get_wchar(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec_indented, layout_offset=4)
        val = row["testWchar"]
        self.assertEqual(val, "Ω")

    def test_get_wstring(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec_indented, layout_offset=4)
        val = row["testWstring"]
        self.assertEqual(val, "ΩstÄ")

    def test_get_date(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec_indented, layout_offset=4)
        val = row["testDate"]
        self.assertEqual(val, datetime.date(day=9, month=3, year=2022))

    def test_get_tod(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec_indented, layout_offset=4)
        val = row["testTod"]
        self.assertEqual(val, datetime.timedelta(hours=12, minutes=34, seconds=56))

    def test_get_dtl(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec_indented, layout_offset=4)
        val = row["testDtl"]
        self.assertEqual(val, datetime.datetime(year=2022, month=3, day=9, hour=12, minute=34, second=45))

    def test_set_date(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec_indented, layout_offset=4)
        row["testDate"] = datetime.date(day=28, month=3, year=2024)
        self.assertEqual(row["testDate"], datetime.date(day=28, month=3, year=2024))


@pytest.mark.util
class TestNewSetters(unittest.TestCase):
    """Tests for the newly added setter functions."""

    def test_set_wstring(self) -> None:
        from snap7.util import set_wstring, get_wstring

        data = bytearray(30)
        set_wstring(data, 0, "hello", 10)
        self.assertEqual(get_wstring(data, 0), "hello")

    def test_set_wstring_unicode(self) -> None:
        from snap7.util import set_wstring, get_wstring

        data = bytearray(30)
        set_wstring(data, 0, "ΩstÄ", 10)
        self.assertEqual(get_wstring(data, 0), "ΩstÄ")

    def test_set_wstring_too_long(self) -> None:
        from snap7.util import set_wstring

        data = bytearray(30)
        with self.assertRaises(ValueError):
            set_wstring(data, 0, "toolong", 3)

    def test_set_wchar(self) -> None:
        from snap7.util import set_wchar

        from snap7.util.getters import get_wchar

        data = bytearray(2)
        set_wchar(data, 0, "C")
        self.assertEqual(get_wchar(data, 0), "C")

    def test_set_wchar_unicode(self) -> None:
        from snap7.util import set_wchar

        from snap7.util.getters import get_wchar

        data = bytearray(2)
        set_wchar(data, 0, "Ω")
        self.assertEqual(get_wchar(data, 0), "Ω")

    def test_set_lword(self) -> None:
        from snap7.util import set_lword, get_lword

        data = bytearray(8)
        set_lword(data, 0, 0xABCD)
        self.assertEqual(get_lword(data, 0), 0xABCD)

    def test_set_lword_max(self) -> None:
        from snap7.util import set_lword, get_lword

        data = bytearray(8)
        set_lword(data, 0, 0xFFFFFFFFFFFFFFFF)
        self.assertEqual(get_lword(data, 0), 0xFFFFFFFFFFFFFFFF)

    def test_set_tod(self) -> None:
        from snap7.util import set_tod

        from snap7.util.getters import get_tod

        data = bytearray(4)
        tod = datetime.timedelta(hours=12, minutes=34, seconds=56)
        set_tod(data, 0, tod)
        self.assertEqual(get_tod(data, 0), tod)

    def test_set_tod_out_of_range(self) -> None:
        from snap7.util import set_tod

        data = bytearray(4)
        with self.assertRaises(ValueError):
            set_tod(data, 0, datetime.timedelta(days=1))

    def test_set_dtl(self) -> None:
        from snap7.util import set_dtl

        from snap7.util.getters import get_dtl

        data = bytearray(12)
        dt = datetime.datetime(2024, 3, 27, 14, 30, 0)
        set_dtl(data, 0, dt)
        result = get_dtl(data, 0)
        self.assertEqual(result.year, dt.year)
        self.assertEqual(result.month, dt.month)
        self.assertEqual(result.day, dt.day)
        self.assertEqual(result.hour, dt.hour)
        self.assertEqual(result.minute, dt.minute)
        self.assertEqual(result.second, dt.second)

    def test_set_dt_roundtrip(self) -> None:
        from snap7.util import set_dt

        from snap7.util.getters import get_date_time_object

        data = bytearray(8)
        dt = datetime.datetime(2020, 7, 12, 17, 32, 2, 854000)
        set_dt(data, 0, dt)
        result = get_date_time_object(data, 0)
        self.assertEqual(result, dt)

    def test_set_dt_year_range(self) -> None:
        from snap7.util import set_dt

        data = bytearray(8)
        with self.assertRaises(ValueError):
            set_dt(data, 0, datetime.datetime(1989, 1, 1))
        with self.assertRaises(ValueError):
            set_dt(data, 0, datetime.datetime(2090, 1, 1))

    def test_get_ltime(self) -> None:
        from snap7.util.getters import get_ltime

        data = bytearray(8)
        # 1 second = 1_000_000_000 nanoseconds
        struct.pack_into(">q", data, 0, 1_000_000_000)
        result = get_ltime(data, 0)
        self.assertEqual(result, datetime.timedelta(seconds=1))

    def test_get_ltod(self) -> None:
        from snap7.util.getters import get_ltod

        data = bytearray(8)
        # 12 hours in nanoseconds
        ns = 12 * 3600 * 1_000_000_000
        struct.pack_into(">Q", data, 0, ns)
        result = get_ltod(data, 0)
        self.assertEqual(result, datetime.timedelta(hours=12))

    def test_get_ldt(self) -> None:
        from snap7.util.getters import get_ldt

        data = bytearray(8)
        # 2020-01-01 00:00:00 UTC in nanoseconds since epoch
        dt = datetime.datetime(2020, 1, 1)
        epoch = datetime.datetime(1970, 1, 1)
        ns = int((dt - epoch).total_seconds() * 1_000_000_000)
        struct.pack_into(">Q", data, 0, ns)
        result = get_ldt(data, 0)
        self.assertEqual(result, dt)

    def test_set_wstring_in_row(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        row["testWstring"] = "abcd"
        self.assertEqual(row["testWstring"], "abcd")

    def test_set_wchar_in_row(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        row["testWchar"] = "B"
        self.assertEqual(row["testWchar"], "B")

    def test_set_tod_in_row(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        tod = datetime.timedelta(hours=1, minutes=2, seconds=3)
        row["testTod"] = tod
        self.assertEqual(row["testTod"], tod)

    def test_set_dtl_in_row(self) -> None:
        test_array = bytearray(_bytearray)
        row = Row(test_array, test_spec, layout_offset=4)
        dt = datetime.datetime(2024, 6, 15, 10, 20, 30)
        row["testDtl"] = dt
        result = row["testDtl"]
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 15)
        self.assertEqual(result.hour, 10)
        self.assertEqual(result.minute, 20)
        self.assertEqual(result.second, 30)


class TestMemoryviewCompat(unittest.TestCase):
    """Test that setter and getter functions work with memoryview buffers."""

    def test_set_bool_memoryview(self) -> None:
        from snap7.util.setters import set_bool

        buf = bytearray(1)
        mv = memoryview(buf)
        set_bool(mv, 0, 0, True)
        self.assertEqual(buf[0], 1)

    def test_set_byte_memoryview(self) -> None:
        buf = bytearray(1)
        mv = memoryview(buf)
        set_byte(mv, 0, 42)
        self.assertEqual(buf[0], 42)

    def test_set_int_memoryview(self) -> None:
        buf = bytearray(2)
        mv = memoryview(buf)
        set_int(mv, 0, -1234)
        self.assertEqual(struct.unpack(">h", buf)[0], -1234)

    def test_set_word_memoryview(self) -> None:
        from snap7.util.setters import set_word

        buf = bytearray(2)
        mv = memoryview(buf)
        set_word(mv, 0, 65535)
        self.assertEqual(struct.unpack(">H", buf)[0], 65535)

    def test_set_real_memoryview(self) -> None:
        from snap7.util.setters import set_real

        buf = bytearray(4)
        mv = memoryview(buf)
        set_real(mv, 0, 123.456)
        val = struct.unpack(">f", buf)[0]
        self.assertAlmostEqual(val, 123.456, places=2)

    def test_set_dword_memoryview(self) -> None:
        from snap7.util.setters import set_dword

        buf = bytearray(4)
        mv = memoryview(buf)
        set_dword(mv, 0, 0xDEADBEEF)
        self.assertEqual(struct.unpack(">I", buf)[0], 0xDEADBEEF)

    def test_set_dint_memoryview(self) -> None:
        from snap7.util.setters import set_dint

        buf = bytearray(4)
        mv = memoryview(buf)
        set_dint(mv, 0, -100000)
        self.assertEqual(struct.unpack(">i", buf)[0], -100000)

    def test_set_usint_memoryview(self) -> None:
        from snap7.util.setters import set_usint

        buf = bytearray(1)
        mv = memoryview(buf)
        set_usint(mv, 0, 200)
        self.assertEqual(buf[0], 200)

    def test_set_sint_memoryview(self) -> None:
        from snap7.util.setters import set_sint

        buf = bytearray(1)
        mv = memoryview(buf)
        set_sint(mv, 0, -50)
        self.assertEqual(struct.unpack(">b", buf)[0], -50)

    def test_set_lreal_memoryview(self) -> None:
        from snap7.util.setters import set_lreal

        buf = bytearray(8)
        mv = memoryview(buf)
        set_lreal(mv, 0, 3.14159265358979)
        val = struct.unpack(">d", buf)[0]
        self.assertAlmostEqual(val, 3.14159265358979, places=10)

    def test_set_string_memoryview(self) -> None:
        from snap7.util.setters import set_string

        buf = bytearray(20)
        mv = memoryview(buf)
        set_string(mv, 0, "hello", 10)
        self.assertEqual(buf[1], 5)  # length byte

    def test_set_fstring_memoryview(self) -> None:
        buf = bytearray(10)
        mv = memoryview(buf)
        set_fstring(mv, 0, "hi", 5)
        self.assertEqual(chr(buf[0]), "h")
        self.assertEqual(chr(buf[1]), "i")

    def test_set_char_memoryview(self) -> None:
        from snap7.util.setters import set_char

        buf = bytearray(1)
        mv = memoryview(buf)
        set_char(mv, 0, "A")
        self.assertEqual(buf[0], ord("A"))

    def test_set_date_memoryview(self) -> None:
        from snap7.util.setters import set_date

        buf = bytearray(2)
        mv = memoryview(buf)
        set_date(mv, 0, datetime.date(2024, 3, 27))
        self.assertEqual(buf, bytearray(b"\x30\xd8"))

    def test_set_udint_memoryview(self) -> None:
        from snap7.util.setters import set_udint

        buf = bytearray(4)
        mv = memoryview(buf)
        set_udint(mv, 0, 4294967295)
        self.assertEqual(struct.unpack(">I", buf)[0], 4294967295)

    def test_set_uint_memoryview(self) -> None:
        from snap7.util.setters import set_uint

        buf = bytearray(2)
        mv = memoryview(buf)
        set_uint(mv, 0, 12345)
        self.assertEqual(struct.unpack(">H", buf)[0], 12345)

    def test_set_time_memoryview(self) -> None:
        buf = bytearray(4)
        mv = memoryview(buf)
        set_time(mv, 0, "1:2:3:4.567")
        self.assertNotEqual(buf, bytearray(4))


_db_test_spec = """
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

_db_bytearray = bytearray(
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
        test_array = bytearray(_db_bytearray * 3)
        self.db = DB(1, test_array, _db_test_spec, row_size=len(_db_bytearray), size=3, layout_offset=4, db_offset=0)

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
        test_array = bytearray(_db_bytearray * 2)
        # Set different ID values for each row
        struct.pack_into(">h", test_array, 0, 10)  # row 0, ID at offset 0 (spec offset 4, layout_offset 4)
        struct.pack_into(">h", test_array, len(_db_bytearray), 20)  # row 1
        db = DB(
            1, test_array, _db_test_spec, row_size=len(_db_bytearray), size=2, id_field="ID", layout_offset=4, db_offset=0
        )
        assert "10" in db
        assert "20" in db


class TestDBSetData:
    def test_set_data_valid(self) -> None:
        test_array = bytearray(_db_bytearray)
        db = DB(1, test_array, _db_test_spec, row_size=len(_db_bytearray), size=1, layout_offset=4, db_offset=0)
        new_data = bytearray(len(_db_bytearray))
        db.set_data(new_data)
        assert db.get_bytearray() is new_data

    def test_set_data_invalid_type(self) -> None:
        test_array = bytearray(_db_bytearray)
        db = DB(1, test_array, _db_test_spec, row_size=len(_db_bytearray), size=1, layout_offset=4, db_offset=0)
        with pytest.raises(TypeError):
            db.set_data(b"not a bytearray")  # type: ignore[arg-type]


class TestDBReadWrite:
    """Test DB.read() and DB.write() with mocked client."""

    def test_read_db_area(self) -> None:
        test_array = bytearray(_db_bytearray)
        db = DB(1, test_array, _db_test_spec, row_size=len(_db_bytearray), size=1, layout_offset=4, db_offset=0)
        mock_client = MagicMock()
        mock_client.db_read.return_value = bytearray(len(_db_bytearray))
        db.read(mock_client)
        mock_client.db_read.assert_called_once()

    def test_read_non_db_area(self) -> None:
        test_array = bytearray(_db_bytearray)
        db = DB(
            0, test_array, _db_test_spec, row_size=len(_db_bytearray), size=1, layout_offset=4, db_offset=0, area=Area.MK
        )
        mock_client = MagicMock()
        mock_client.read_area.return_value = bytearray(len(_db_bytearray))
        db.read(mock_client)
        mock_client.read_area.assert_called_once()

    def test_read_negative_row_size(self) -> None:
        test_array = bytearray(_db_bytearray)
        db = DB(1, test_array, _db_test_spec, row_size=len(_db_bytearray), size=1, layout_offset=4, db_offset=0)
        db.row_size = -1
        mock_client = MagicMock()
        with pytest.raises(ValueError, match="row_size"):
            db.read(mock_client)

    def test_write_db_area(self) -> None:
        test_array = bytearray(_db_bytearray)
        db = DB(1, test_array, _db_test_spec, row_size=len(_db_bytearray), size=1, layout_offset=4, db_offset=0)
        mock_client = MagicMock()
        db.write(mock_client)
        mock_client.db_write.assert_called_once()

    def test_write_non_db_area(self) -> None:
        test_array = bytearray(_db_bytearray)
        db = DB(
            0, test_array, _db_test_spec, row_size=len(_db_bytearray), size=1, layout_offset=4, db_offset=0, area=Area.MK
        )
        mock_client = MagicMock()
        db.write(mock_client)
        mock_client.write_area.assert_called_once()

    def test_write_negative_row_size(self) -> None:
        test_array = bytearray(_db_bytearray)
        db = DB(1, test_array, _db_test_spec, row_size=len(_db_bytearray), size=1, layout_offset=4, db_offset=0)
        db.row_size = -1
        mock_client = MagicMock()
        with pytest.raises(ValueError, match="row_size"):
            db.write(mock_client)

    def test_write_with_row_offset(self) -> None:
        test_array = bytearray(_db_bytearray * 2)
        db = DB(
            1, test_array, _db_test_spec, row_size=len(_db_bytearray), size=2, layout_offset=4, db_offset=0, row_offset=4
        )
        mock_client = MagicMock()
        db.write(mock_client)
        # Should write each row individually via Row.write()
        assert mock_client.db_write.call_count == 2


class TestRowRepr:
    def test_repr(self) -> None:
        test_array = bytearray(_db_bytearray)
        row = Row(test_array, _db_test_spec, layout_offset=4)
        r = repr(row)
        assert "ID" in r
        assert "NAME" in r


class TestRowUnchanged:
    def test_unchanged_true(self) -> None:
        test_array = bytearray(_db_bytearray)
        row = Row(test_array, _db_test_spec, layout_offset=4)
        assert row.unchanged(test_array) is True

    def test_unchanged_false(self) -> None:
        test_array = bytearray(_db_bytearray)
        row = Row(test_array, _db_test_spec, layout_offset=4)
        other = bytearray(len(_db_bytearray))
        assert row.unchanged(other) is False


class TestRowTypeError:
    def test_invalid_bytearray_type(self) -> None:
        with pytest.raises(TypeError):
            Row("not a bytearray", _db_test_spec)  # type: ignore[arg-type]


class TestRowReadWrite:
    """Test Row.read() and Row.write() with mocked client through DB parent."""

    def test_row_write_db_area(self) -> None:
        test_array = bytearray(_db_bytearray)
        db = DB(1, test_array, _db_test_spec, row_size=len(_db_bytearray), size=1, layout_offset=4, db_offset=0)
        row = db["0"]
        assert row is not None
        mock_client = MagicMock()
        row.write(mock_client)
        mock_client.db_write.assert_called_once()

    def test_row_write_non_db_area(self) -> None:
        test_array = bytearray(_db_bytearray)
        db = DB(
            0, test_array, _db_test_spec, row_size=len(_db_bytearray), size=1, layout_offset=4, db_offset=0, area=Area.MK
        )
        row = db["0"]
        assert row is not None
        mock_client = MagicMock()
        row.write(mock_client)
        mock_client.write_area.assert_called_once()

    def test_row_write_not_db_parent(self) -> None:
        test_array = bytearray(_db_bytearray)
        row = Row(test_array, _db_test_spec, layout_offset=4)
        mock_client = MagicMock()
        with pytest.raises(TypeError):
            row.write(mock_client)

    def test_row_write_negative_row_size(self) -> None:
        test_array = bytearray(_db_bytearray)
        db = DB(1, test_array, _db_test_spec, row_size=len(_db_bytearray), size=1, layout_offset=4, db_offset=0)
        row = db["0"]
        assert row is not None
        row.row_size = -1
        mock_client = MagicMock()
        with pytest.raises(ValueError, match="row_size"):
            row.write(mock_client)

    def test_row_read_db_area(self) -> None:
        test_array = bytearray(_db_bytearray)
        db = DB(1, test_array, _db_test_spec, row_size=len(_db_bytearray), size=1, layout_offset=4, db_offset=0)
        row = db["0"]
        assert row is not None
        mock_client = MagicMock()
        mock_client.db_read.return_value = bytearray(len(_db_bytearray))
        row.read(mock_client)
        mock_client.db_read.assert_called_once()

    def test_row_read_non_db_area(self) -> None:
        test_array = bytearray(_db_bytearray)
        db = DB(
            0, test_array, _db_test_spec, row_size=len(_db_bytearray), size=1, layout_offset=4, db_offset=0, area=Area.MK
        )
        row = db["0"]
        assert row is not None
        mock_client = MagicMock()
        mock_client.read_area.return_value = bytearray(len(_db_bytearray))
        row.read(mock_client)
        mock_client.read_area.assert_called_once()

    def test_row_read_not_db_parent(self) -> None:
        test_array = bytearray(_db_bytearray)
        row = Row(test_array, _db_test_spec, layout_offset=4)
        mock_client = MagicMock()
        with pytest.raises(TypeError):
            row.read(mock_client)

    def test_row_read_negative_row_size(self) -> None:
        test_array = bytearray(_db_bytearray)
        db = DB(1, test_array, _db_test_spec, row_size=len(_db_bytearray), size=1, layout_offset=4, db_offset=0)
        row = db["0"]
        assert row is not None
        row.row_size = -1
        mock_client = MagicMock()
        with pytest.raises(ValueError, match="row_size"):
            row.read(mock_client)


class TestRowSetValueTypes:
    """Test set_value for various type branches."""

    def setup_method(self) -> None:
        self.test_array = bytearray(_db_bytearray)
        self.row = Row(self.test_array, _db_test_spec, layout_offset=4)

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
        self.test_array = bytearray(_db_bytearray)
        self.row = Row(self.test_array, _db_test_spec, layout_offset=4)

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
        self.test_array = bytearray(_db_bytearray)
        self.row = Row(self.test_array, _db_test_spec, layout_offset=4)

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
        test_array = bytearray(_db_bytearray)
        db = DB(
            1, test_array, _db_test_spec, row_size=len(_db_bytearray), size=1, layout_offset=4, db_offset=0, row_offset=10
        )
        row = db["0"]
        assert row is not None
        mock_client = MagicMock()
        row.write(mock_client)
        # The data written should start at db_offset + row_offset
        mock_client.db_write.assert_called_once()


if __name__ == "__main__":
    unittest.main()
