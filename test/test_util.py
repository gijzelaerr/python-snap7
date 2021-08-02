import re
import unittest
import struct

from snap7 import util, types

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
29      tests5time   S5TIME
31      testdateandtime DATE_AND_TIME
43      testusint0      USINT
44      testsint0       SINT
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
44      testsint0       SINT
"""


_bytearray = bytearray([
    0, 0,  # test int
    4, 4, ord('t'), ord('e'), ord('s'), ord('t'),  # test string
    128 * 0 + 64 * 0 + 32 * 0 + 16 * 0
    + 8 * 1 + 4 * 1 + 2 * 1 + 1 * 1,                 # test bools
    68, 78, 211, 51,                               # test real
    255, 255, 255, 255,                            # test dword
    0, 0,                                          # test int 2
    128, 0, 0, 0,                                  # test dint
    255, 255,                                      # test word
    0, 16,                                         # test s5time, 0 is the time base,
                                                   # 16 is value, those two integers should be declared together
    32, 7, 18, 23, 50, 2, 133, 65,                 # these 8 values build the date and time 12 byte total
                                                   # data typ together, for details under this link
                                                   # https://support.industry.siemens.com/cs/document/36479/date_and_time-format-bei-s7-?dti=0&lc=de-DE
    254, 254, 254, 254, 254, 127,                  # test small int
    128,                                           # test set byte
])

_new_bytearray = bytearray(100)
_new_bytearray[41:41 + 1] = struct.pack("B", 128)       # byte_index=41, value=128, bytes=1
_new_bytearray[42:42 + 1] = struct.pack("B", 255)       # byte_index=41, value=255, bytes=1


class TestS7util(unittest.TestCase):

    def test_get_byte(self):
        test_array = bytearray(_new_bytearray)
        byte_ = util.get_byte(test_array, 41)
        self.assertEqual(byte_, 128)
        byte_ = util.get_byte(test_array, 42)
        self.assertEqual(byte_, 255)

    def test_set_byte(self):
        test_array = bytearray(_new_bytearray)
        util.set_byte(test_array, 41, 127)
        byte_ = util.get_byte(test_array, 41)
        self.assertEqual(byte_, 127)

    def test_get_s5time(self):
        """
        S5TIME extraction from bytearray
        """
        test_array = bytearray(_bytearray)

        row = util.DB_Row(test_array, test_spec, layout_offset=4)

        self.assertEqual(row['tests5time'], '0:00:00.100000')

    def test_get_dt(self):
        """
        DATE_AND_TIME extraction from bytearray
        """
        test_array = bytearray(_bytearray)

        row = util.DB_Row(test_array, test_spec, layout_offset=4)

        self.assertEqual(row['testdateandtime'], '2020-07-12T17:32:02.854000')

    def test_get_string(self):
        """
        Text extraction from string from bytearray
        """
        test_array = bytearray(_bytearray)

        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        self.assertEqual(row['NAME'], 'test')

    def test_write_string(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        row['NAME'] = 'abc'
        self.assertEqual(row['NAME'], 'abc')
        row['NAME'] = ''
        self.assertEqual(row['NAME'], '')
        try:
            row['NAME'] = 'waaaaytoobig'
        except ValueError:
            pass
        # value should still be empty
        self.assertEqual(row['NAME'], '')

    def test_get_int(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        x = row['ID']
        y = row['testint2']
        self.assertEqual(x, 0)
        self.assertEqual(y, 0)

    def test_set_int(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        row['ID'] = 259
        self.assertEqual(row['ID'], 259)

    def test_get_usint(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        value = row.get_value(43, 'USINT')  # get value
        self.assertEqual(value, 254)

    def test_set_usint(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        row['testusint0'] = 255
        self.assertEqual(row['testusint0'], 255)

    def test_get_sint(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        value = row.get_value(44, 'SINT')  # get value
        self.assertEqual(value, 127)

    def test_set_sint(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        row['testsint0'] = 127
        self.assertEqual(row['testsint0'], 127)

    def test_set_int_roundtrip(self):
        DB1 = (types.wordlen_to_ctypes[types.S7WLByte] * 4)()

        for i in range(-(2 ** 15) + 1, (2 ** 15) - 1):
            util.set_int(DB1, 0, i)
            result = util.get_int(DB1, 0)
            self.assertEqual(i, result)

    def test_get_int_values(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        for value in (
                -32768,
                -16385,
                -256,
                -128,
                -127,
                0,
                127,
                128,
                255,
                256,
                16384,
                32767):
            row['ID'] = value
            self.assertEqual(row['ID'], value)

    def test_get_bool(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        self.assertEqual(row['testbool1'], 1)
        self.assertEqual(row['testbool8'], 0)

    def test_set_bool(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        row['testbool8'] = True
        row['testbool1'] = False

        self.assertEqual(row['testbool8'], True)
        self.assertEqual(row['testbool1'], False)

    def test_db_creation(self):
        test_array = bytearray(_bytearray * 10)

        test_db = util.DB(1, test_array, test_spec,
                          row_size=len(_bytearray),
                          size=10,
                          layout_offset=4,
                          db_offset=0)

        self.assertEqual(len(test_db.index), 10)

        for i, row in test_db:
            # print row
            self.assertEqual(row['testbool1'], 1)
            self.assertEqual(row['testbool2'], 1)
            self.assertEqual(row['testbool3'], 1)
            self.assertEqual(row['testbool4'], 1)

            self.assertEqual(row['testbool5'], 0)
            self.assertEqual(row['testbool6'], 0)
            self.assertEqual(row['testbool7'], 0)
            self.assertEqual(row['testbool8'], 0)
            self.assertEqual(row['NAME'], 'test')

    def test_get_real(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        self.assertTrue(0.01 > (row['testReal'] - 827.3) > -0.1)

    def test_set_real(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        row['testReal'] = 1337.1337
        self.assertTrue(0.01 > (row['testReal'] - 1337.1337) > -0.01)

    def test_set_dword(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        # The range of numbers is 0 to 4294967295.
        row['testDword'] = 9999999
        self.assertEqual(row['testDword'], 9999999)

    def test_get_dword(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        self.assertEqual(row['testDword'], 4294967295)

    def test_set_dint(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        # The range of numbers is -2147483648 to 2147483647 +
        row.set_value(23, 'DINT', 2147483647)  # set value
        self.assertEqual(row['testDint'], 2147483647)

    def test_get_dint(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        value = row.get_value(23, 'DINT')  # get value
        self.assertEqual(value, -2147483648)

    def test_set_word(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        # The range of numbers is 0 to 65535
        row.set_value(27, 'WORD', 0)  # set value
        self.assertEqual(row['testWord'], 0)

    def test_get_word(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        value = row.get_value(27, 'WORD')  # get value
        self.assertEqual(value, 65535)

    def test_export(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        data = row.export()
        self.assertIn('testDword', data)
        self.assertIn('testbool1', data)
        self.assertEqual(data['testbool5'], 0)

    def test_indented_layout(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec_indented, layout_offset=4)
        x = row['ID']
        y_single_space = row['testbool1']
        y_multi_space = row['testbool2']
        y_single_indent = row['testint2']
        y_multi_indent = row['testbool8']

        with self.assertRaises(KeyError):
            fail_single_space = row['testbool4']
        with self.assertRaises(KeyError):
            fail_multiple_spaces = row['testbool5']
        with self.assertRaises(KeyError):
            fail_single_indent = row['testbool6']
        with self.assertRaises(KeyError):
            fail_multiple_indent = row['testbool7']

        self.assertEqual(x, 0)
        self.assertEqual(y_single_space, True)
        self.assertEqual(y_multi_space, True)
        self.assertEqual(y_single_indent, 0)
        self.assertEqual(y_multi_indent, 0)


def print_row(data):
    """print a single db row in chr and str
    """
    index_line = ""
    pri_line1 = ""
    chr_line2 = ""
    asci = re.compile('[a-zA-Z0-9 ]')

    for i, xi in enumerate(data):
        # index
        if not i % 5:
            diff = len(pri_line1) - len(index_line)
            i = str(i)
            index_line += diff * ' '
            index_line += i
            # i = i + (ws - len(i)) * ' ' + ','

        # byte array line
        str_v = str(xi)
        pri_line1 += str(xi) + ','
        # char line
        c = chr(xi)
        c = c if asci.match(c) else ' '
        # align white space
        w = len(str_v)
        c = c + (w - 1) * ' ' + ','
        chr_line2 += c

    print(index_line)
    print(pri_line1)
    print(chr_line2)


if __name__ == '__main__':
    unittest.main()
