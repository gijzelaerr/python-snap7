import unittest
import snap7
import ctypes
import logging

logging.basicConfig()
l = logging.getLogger()
l.setLevel(logging.INFO)

#ip = '192.168.200.24'
ip = '127.0.0.1'
db_number = 1
rack = 0
slot = 3

class TestClient(unittest.TestCase):

    def setUp(self):
        self.client = snap7.client.Client()
        self.client.connect(ip, rack, slot)

    def tearDown(self):
        self.client.disconnect()
        self.client.destroy()

    def test_db_read(self):
        data = self.client.db_read(db_number=db_number, start=0, size=100)

    def test_db_get(self):
        result = self.client.db_get(db_number=db_number)

    def test_db_upload(self):
        data = snap7.client.buffer_type()
        self.client.db_upload(block_type=snap7.types.block_types['DB'],
                              block_num=db_number, data=data)

    def test_read_area(self):
        area = snap7.types.S7AreaDB
        dbnumber = 1
        amount = 10
        start = 1
        wordlen = snap7.types.S7WLByte
        self.client.read_area(area, dbnumber, start, amount, wordlen)

    def test_write_area(self):
        area = snap7.types.S7AreaDB
        dbnumber = 1
        amount = 10
        start = 1
        wordlen = snap7.types.S7WLByte
        data = (ctypes.c_int16 * amount)()
        self.client.write_area(area, dbnumber, start, amount, wordlen, data)
