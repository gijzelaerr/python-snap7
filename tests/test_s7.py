import unittest

import pytest

from snap7.low_level.s7_client import S7Client
from snap7.low_level.s7_server import S7Server

@pytest.mark.s7
class TestS7(unittest.TestCase):

    def test_connect(self):
        s7_server = S7Server()
        s7_client = S7Client()
        s7_server.start(ip="0.0.0.0", tcp_port=102)
        s7_client.connect(host="localhost", rack=0, slot=2, tcp_port=102)
        s7_client.disconnect()
        s7_server.stop()
        assert True


