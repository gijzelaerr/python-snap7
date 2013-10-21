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
        data = self.client.db_read(db_number=db_number, start=0, size=100)
        print data[:100]

    def test_db_write(self):
        data = self.client.db_read(db_number=db_number, start=0, size=100)
        self.client.db_write(db_number=db_number, start=0, size=100, data=data)

    def test_db_get(self):
        self.client.db_get(db_number=db_number)

    def test_db_upload(self):
        data = self.client._buffer
        print 'Upload', data[:100]

        self.client.db_upload(block_type=snap7.data.block_types['DB'],
                              block_num=db_number, data=data)


if __name__ == '__main__':
    unittest2.main()
