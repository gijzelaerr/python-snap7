
from snap7.s7util import db
import unittest

test_spec = """

4	    ID	         INT
6	    NAME	     STRING[4]

13.0	testbool1    BOOL
13.1	testbool2    BOOL
13.2	testbool3    BOOL
13.3	testbool4    BOOL
13.4	testbool5    BOOL
13.5	testbool6    BOOL
13.6	testbool7    BOOL
13.7	testbool8    BOOL
"""

_bytearray = bytearray([
    0, 0,                                          # test int
    4, 4, ord('t'), ord('e'), ord('s'), ord('t'),  # test string
    1, 1, 1, 1, 0, 0, 0, 0])                       # test bools


class TestS7util(unittest.TestCase):

    def test_get_string(self):
        """
        Text extraction from string from bytearray
        """
        test_array = bytearray(_bytearray)

        row = db.DB_Row(test_array, test_spec)
        self.assertTrue(row['NAME'] == 'test')

    def test_write_string(self):
        test_array = bytearray(_bytearray)
        row = db.DB_Row(test_array, test_spec)
        row['NAME'] = 'abc'
        self.assertTrue(row['NAME'] == 'abc')
        row['NAME'] = ''
        self.assertTrue(row['NAME'] == '')

    def test_get_int(self):
        test_array = bytearray(_bytearray)
        row = db.DB_Row(test_array, test_spec)
        x = row['ID']
        self.assertTrue(x == 0)

    def test_set_int(self):
        test_array = bytearray(_bytearray)
        row = db.DB_Row(test_array, test_spec)
        row['ID'] = 259
        self.assertTrue(row['ID'] == 259)

    def test_get_bool(self):
        test_array = bytearray(_bytearray)
        row = db.DB_Row(test_array, test_spec)
        self.assertTrue(row['testbool1'] == 1)
        self.assertTrue(row['testbool8'] == 0)

    def test_set_bool(self):
        test_array = bytearray(_bytearray)
        row = db.DB_Row(test_array, test_spec)
        row['testbool8'] = 1
        row['testbool1'] = 0

        self.assertTrue(row['testbool8'] == 1)
        self.assertTrue(row['testbool1'] == 0)


if __name__ == '__main__':
    unittest.main()
