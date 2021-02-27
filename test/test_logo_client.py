import logging
import time
import unittest
from multiprocessing import Process

import snap7
from snap7.server import mainloop

logging.basicConfig(level=logging.WARNING)

ip = '127.0.0.1'
tcpport = 1102
db_number = 1
rack = 0x1000
slot = 0x2000


class TestLogoClient(unittest.TestCase):

    process = None

    @classmethod
    def setUpClass(cls):
        cls.process = Process(target=mainloop)
        cls.process.start()
        time.sleep(2)  # wait for server to start

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()

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
            (snap7.types.PingTimeout, 800),
            (snap7.types.SendTimeout, 15),
            (snap7.types.RecvTimeout, 3500),
            (snap7.types.SrcRef, 128),
            (snap7.types.DstRef, 128),
            (snap7.types.SrcTSap, 128),
            (snap7.types.PDURequest, 470),
        )
        for param, value in values:
            self.client.set_param(param, value)

        self.assertRaises(Exception, self.client.set_param,
                          snap7.types.RemotePort, 1)

    def test_get_param(self):
        expected = (
            (snap7.types.RemotePort, tcpport),
            (snap7.types.PingTimeout, 750),
            (snap7.types.SendTimeout, 10),
            (snap7.types.RecvTimeout, 3000),
            (snap7.types.SrcRef, 256),
            (snap7.types.DstRef, 0),
            (snap7.types.SrcTSap, 4096),
            (snap7.types.PDURequest, 480),
        )
        for param, value in expected:
            self.assertEqual(self.client.get_param(param), value)

        non_client = (snap7.types.LocalPort, snap7.types.WorkInterval, snap7.types.MaxClients,
                      snap7.types.BSendTimeout, snap7.types.BRecvTimeout, snap7.types.RecoveryTime,
                      snap7.types.KeepAliveTime)

        # invalid param for client
        for param in non_client:
            self.assertRaises(Exception, self.client.get_param, non_client)


class TestClientBeforeConnect(unittest.TestCase):
    """
    Test suite of items that should run without an open connection.
    """

    def setUp(self):
        self.client = snap7.client.Client()

    def test_set_param(self):
        values = (
            (snap7.types.RemotePort, 1102),
            (snap7.types.PingTimeout, 800),
            (snap7.types.SendTimeout, 15),
            (snap7.types.RecvTimeout, 3500),
            (snap7.types.SrcRef, 128),
            (snap7.types.DstRef, 128),
            (snap7.types.SrcTSap, 128),
            (snap7.types.PDURequest, 470),
        )
        for param, value in values:
            self.client.set_param(param, value)


if __name__ == '__main__':
    unittest.main()
