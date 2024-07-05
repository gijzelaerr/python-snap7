import datetime
import pytest
import unittest
import struct
from typing import cast

from snap7 import DB, Row
from snap7.util import get_byte, get_time, get_fstring, get_int
from snap7.util import set_byte, set_time, set_fstring, set_int
from snap7.type import WordLen

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
#    12.3	testbool4    BOOL
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
        try:
            row["NAME"] = "TrÖt"
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


if __name__ == "__main__":
    unittest.main()
