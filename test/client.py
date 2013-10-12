import unittest2
import time
import snap7



class Client(unittest2.TestCase):

    def test_create(self):

        client = snap7.client.create()

        # current test plc
        result = snap7.client.connect(client, '192.168.200.24', 0, 3)
        # default local.
        #client.connect('127.0.0.1', 0, 2)
        print result
        print 'did we connect?'
        #data = client.readDB(0)
        #print data
        time.sleep(1)
        snap7.client.disconnect(client)
        print "disconnected"
        snap7.client.destroy(client)


if __name__ == '__main__':
    unittest2.main()
