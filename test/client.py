"""
Used to test against real plc
"""

import unittest2
import snap7

import logging

logging.basicConfig()
l = logging.getLogger()
l.setLevel(logging.INFO)

ip = '192.168.200.24'
db_number = 1
rack = 0
slot = 3


class Client(unittest2.TestCase):

    def setUp(self):
        self.client = snap7.client.Client()
        self.client.connect(ip, rack, slot)

    def tearDown(self):
        self.client.disconnect()
        self.client.destroy()

    def test_db_read(self):
        size = 40
        start = 0
        db = db_number
        type_ = snap7.types.wordlen_to_ctypes[snap7.types.S7WLByte]
        self.client.db_read(db_number=db, start=start, type_=type_,
                            size=size)

    def test_db_write(self):
        type_ = snap7.types.wordlen_to_ctypes[snap7.types.S7WLByte]
        data = self.client.db_read(db_number=db_number, start=0,
                                   type_=type_, size=100)
        self.client.db_write(db_number=db_number, start=0,
                             size=100, data=data)

    def test_db_get(self):
        self.client.db_get(db_number=db_number)

    def test_db_upload(self):
        data = self.client.db_get(db_number=db_number)
        print 'Upload', data[:100]
        self.client.db_upload(block_type=snap7.types.block_types['DB'],
                              block_num=db_number, data=data)

    def test_read_area(self):
        area = snap7.types.S7AreaDB
        dbnumber = 1
        amount = 128
        start = 1
        wordlen = snap7.types.S7WLByte
        data = self.client.read_area(area, dbnumber, start, amount, wordlen)
        print data

    def test_list_blocks(self):
        blockList = self.client.list_blocks()
        print blockList


if __name__ == '__main__':
    unittest2.main()
