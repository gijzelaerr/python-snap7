import unittest
import logging
import time
#import mock

from subprocess import Popen
from os import path, kill
import snap7

logging.basicConfig(level=logging.WARNING)

ip = '127.0.0.1'
tcpport = 1102
db_number = 1
rack = 0x1000
slot = 0x2000


class TestLogoClient(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        server_path = path.join(path.dirname(path.realpath(snap7.__file__)),
                                "bin/snap7-server.py")
        cls.server_pid = Popen([server_path]).pid
        time.sleep(2)  # wait for server to start

    @classmethod
    def tearDownClass(cls):
        kill(cls.server_pid, 1)

    def setUp(self):
        self.client = snap7.logo.Logo()
        self.client.connect(ip, rack, slot, tcpport)

    def tearDown(self):
        self.client.disconnect()
        self.client.destroy()

    def test_read(self):
        vm_address = "V40"
        value = 50
        self.client.write(vm_address, value)
        result = self.client.read(vm_address)
        self.assertEqual(value, result)

    def test_write(self):
        vm_address = "V20"
        value = 8
        self.client.write(vm_address, value)

    def test_get_connected(self):
        self.client.get_connected()

    def test_set_param(self):
        values = (
            (snap7.snap7types.PingTimeout, 800),
            (snap7.snap7types.SendTimeout, 15),
            (snap7.snap7types.RecvTimeout, 3500),
            (snap7.snap7types.SrcRef, 128),
            (snap7.snap7types.DstRef, 128),
            (snap7.snap7types.SrcTSap, 128),
            (snap7.snap7types.PDURequest, 470),
        )
        for param, value in values:
            self.client.set_param(param, value)

        self.assertRaises(Exception, self.client.set_param,
                          snap7.snap7types.RemotePort, 1)

    def test_get_param(self):
        expected = (
            (snap7.snap7types.RemotePort, tcpport),
            (snap7.snap7types.PingTimeout, 750),
            (snap7.snap7types.SendTimeout, 10),
            (snap7.snap7types.RecvTimeout, 3000),
            (snap7.snap7types.SrcRef, 256),
            (snap7.snap7types.DstRef, 0),
            (snap7.snap7types.SrcTSap, 4096),
            (snap7.snap7types.PDURequest, 480),
        )
        for param, value in expected:
            self.assertEqual(self.client.get_param(param), value)

        non_client = snap7.snap7types.LocalPort, snap7.snap7types.WorkInterval,\
            snap7.snap7types.MaxClients, snap7.snap7types.BSendTimeout,\
            snap7.snap7types.BRecvTimeout, snap7.snap7types.RecoveryTime,\
            snap7.snap7types.KeepAliveTime

        # invalid param for client
        for param in non_client:
            self.assertRaises(Exception, self.client.get_param,  non_client)




class TestClientBeforeConnect(unittest.TestCase):
    """
    Test suite of items that should run without an open connection.
    """
    def setUp(self):
        self.client = snap7.client.Client()

    def test_set_param(self):
        values = (
            (snap7.snap7types.RemotePort, 1102),
            (snap7.snap7types.PingTimeout, 800),
            (snap7.snap7types.SendTimeout, 15),
            (snap7.snap7types.RecvTimeout, 3500),
            (snap7.snap7types.SrcRef, 128),
            (snap7.snap7types.DstRef, 128),
            (snap7.snap7types.SrcTSap, 128),
            (snap7.snap7types.PDURequest, 470),
        )
        for param, value in values:
            self.client.set_param(param, value)


if __name__ == '__main__':
    unittest.main()

