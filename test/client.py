import unittest2

from snap7 import client

import time


class Client(unittest2.TestCase):

    def test_create(self):

        Client = client.create()

        # current test plc
        result = client.connect(Client, '192.168.200.24', 0, 3)
        # default local.
        #client.connect('127.0.0.1', 0, 2)
        print result
        print 'did we connect?'
        #data = client.readDB(0)
        #print data
        time.sleep(1)
        client.destroy(Client)


if __name__ == '__main__':
    unittest2.main()
