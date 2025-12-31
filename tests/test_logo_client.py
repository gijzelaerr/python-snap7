import logging
import pytest
import unittest
from typing import Optional

import snap7
from snap7.server import Server
from snap7.type import Parameter, SrvArea

logging.basicConfig(level=logging.WARNING)

ip = "127.0.0.1"
tcpport = 1102
db_number = 1
rack = 0x1000
slot = 0x2000


@pytest.mark.logo
class TestLogoClient(unittest.TestCase):
    server: Optional[Server] = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = Server()
        cls.server.register_area(SrvArea.DB, 0, bytearray(600))
        cls.server.register_area(SrvArea.DB, 1, bytearray(600))
        cls.server.start(tcp_port=tcpport)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server:
            cls.server.stop()
            cls.server.destroy()

    def setUp(self) -> None:
        self.client = snap7.logo.Logo()
        self.client.connect(ip, rack, slot, tcpport)

    def tearDown(self) -> None:
        self.client.disconnect()
        self.client.destroy()

    def test_read(self) -> None:
        vm_address = "V40"
        value = 50
        self.client.write(vm_address, value)
        result = self.client.read(vm_address)
        self.assertEqual(value, result)

    def test_write(self) -> None:
        vm_address = "V20"
        value = 8
        self.client.write(vm_address, value)

    def test_get_connected(self) -> None:
        self.client.get_connected()

    def test_set_param(self) -> None:
        values = (
            (Parameter.PingTimeout, 800),
            (Parameter.SendTimeout, 15),
            (Parameter.RecvTimeout, 3500),
            (Parameter.SrcRef, 128),
            (Parameter.DstRef, 128),
            (Parameter.SrcTSap, 128),
            (Parameter.PDURequest, 470),
        )
        for param, value in values:
            self.client.set_param(param, value)

        self.assertRaises(Exception, self.client.set_param, Parameter.RemotePort, 1)

    def test_get_param(self) -> None:
        expected = (
            (Parameter.RemotePort, tcpport),
            (Parameter.PingTimeout, 750),
            (Parameter.SendTimeout, 10),
            (Parameter.RecvTimeout, 3000),
            (Parameter.SrcRef, 256),
            (Parameter.DstRef, 0),
            (Parameter.SrcTSap, 4096),
            (Parameter.PDURequest, 480),
        )
        for param, value in expected:
            self.assertEqual(self.client.get_param(param), value)

        non_client = (
            Parameter.LocalPort,
            Parameter.WorkInterval,
            Parameter.MaxClients,
            Parameter.BSendTimeout,
            Parameter.BRecvTimeout,
            Parameter.RecoveryTime,
            Parameter.KeepAliveTime,
        )

        # invalid param for client
        for param in non_client:
            self.assertRaises(Exception, self.client.get_param, param)


@pytest.mark.logo
class TestClientBeforeConnect(unittest.TestCase):
    """
    Test suite of items that should run without an open connection.
    """

    def setUp(self) -> None:
        self.client = snap7.client.Client()

    def test_set_param(self) -> None:
        values = (
            (Parameter.RemotePort, 1102),
            (Parameter.PingTimeout, 800),
            (Parameter.SendTimeout, 15),
            (Parameter.RecvTimeout, 3500),
            (Parameter.SrcRef, 128),
            (Parameter.DstRef, 128),
            (Parameter.SrcTSap, 128),
            (Parameter.PDURequest, 470),
        )
        for param, value in values:
            self.client.set_param(param, value)


if __name__ == "__main__":
    unittest.main()
