import unittest
import re

from snap7 import util


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
"""

_bytearray = bytearray([
    0, 0,                                          # test int
    4, 4, ord('t'), ord('e'), ord('s'), ord('t'),  # test string
    128*0 + 64*0 + 32*0 + 16*0 +
    8*1 + 4*1 + 2*1 + 1*1,                         # test bools
    68, 78, 211, 51,                               # test real
    255, 255, 255, 255                             # test dword
    ])


class TestS7util(unittest.TestCase):

    def test_get_string(self):
        """
        Text extraction from string from bytearray
        """
        test_array = bytearray(_bytearray)

        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        self.assertTrue(row['NAME'] == 'test')

    def test_write_string(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        row['NAME'] = 'abc'
        self.assertTrue(row['NAME'] == 'abc')
        row['NAME'] = ''
        self.assertTrue(row['NAME'] == '')
        try:
            row['NAME'] = 'waaaaytoobig'
        except ValueError:
            pass
        # value should still be empty
        self.assertTrue(row['NAME'] == '')

    def test_get_int(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        x = row['ID']
        self.assertTrue(x == 0)

    def test_set_int(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        row['ID'] = 259
        self.assertTrue(row['ID'] == 259)

    def test_get_bool(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        self.assertTrue(row['testbool1'] == 1)
        self.assertTrue(row['testbool8'] == 0)

    def test_set_bool(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        row['testbool8'] = 1
        row['testbool1'] = 0

        self.assertTrue(row['testbool8'] == 1)
        self.assertTrue(row['testbool1'] == 0)

    def test_db_creation(self):
        test_array = bytearray(_bytearray * 10)

        test_db = util.DB(1, test_array, test_spec,
                          row_size=len(_bytearray),
                          size=10,
                          layout_offset=4,
                          db_offset=0)

        self.assertTrue(len(test_db.index) == 10)

        for i, row in test_db:
            # print row
            self.assertTrue(row['testbool1'] == 1)
            self.assertTrue(row['testbool2'] == 1)
            self.assertTrue(row['testbool3'] == 1)
            self.assertTrue(row['testbool4'] == 1)

            self.assertTrue(row['testbool5'] == 0)
            self.assertTrue(row['testbool6'] == 0)
            self.assertTrue(row['testbool7'] == 0)
            self.assertTrue(row['testbool8'] == 0)
            self.assertTrue(row['NAME'] == 'test')

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
        self.assertTrue(row['testDword'] == 9999999)

    def test_get_dword(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        self.assertTrue(row['testDword'] == 4294967295)

    def test_export(self):
        test_array = bytearray(_bytearray)
        row = util.DB_Row(test_array, test_spec, layout_offset=4)
        data = row.export()
        self.assertTrue('testDword' in data)
        self.assertTrue('testbool1' in data)
        self.assertTrue(data['testbool5'] == 0)


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
