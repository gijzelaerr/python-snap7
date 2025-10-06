"""Unit tests for snap7.low_level.s7_client module."""
import logging
import unittest
from unittest import mock

import pytest

from snap7.low_level.s7_client import S7Client, S7SZL, S7SZLHeader
from snap7.low_level.s7_protocol import S7Protocol as S7

logging.basicConfig(level=logging.WARNING)


@pytest.mark.low_level_client
class TestS7Client(unittest.TestCase):
    """Test cases for S7Client class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.client = S7Client()

    def tearDown(self) -> None:
        """Clean up after tests."""
        if self.client.connected:
            self.client.disconnect()

    def test_init(self) -> None:
        """Test S7Client initialization."""
        self.assertIsNotNone(self.client)
        self.assertEqual(self.client._last_error, 0)
        self.assertEqual(self.client._address_PLC, "")
        self.assertEqual(self.client._port_PLC, 102)
        self.assertEqual(self.client._rack, 0)
        self.assertEqual(self.client._slot, 0)
        self.assertEqual(self.client.conn_type, S7.CONNTYPE_PG)
        self.assertFalse(self.client.connected)

    def test_connected_property(self) -> None:
        """Test connected property."""
        self.assertFalse(self.client.connected)

    def test_set_connection_params(self) -> None:
        """Test setting connection parameters."""
        address = "192.168.1.100"
        local_tsap = 0x0100
        remote_tsap = 0x0200

        self.client.set_connection_params(address, local_tsap, remote_tsap)

        self.assertEqual(self.client._address_PLC, address)
        self.assertEqual(self.client.local_TSAP_high, 0x01)
        self.assertEqual(self.client.local_TSAP_low, 0x00)
        self.assertEqual(self.client.remote_TSAP_high, 0x02)
        self.assertEqual(self.client.remote_TSAP_low, 0x00)

    def test_get_last_error(self) -> None:
        """Test getting last error."""
        error = self.client.get_last_error()
        self.assertEqual(error, 0)

    def test_get_exec_time(self) -> None:
        """Test getting execution time."""
        exec_time = self.client.get_exec_time()
        self.assertIsInstance(exec_time, int)
        self.assertEqual(exec_time, 0)

    def test_get_param(self) -> None:
        """Test getting parameters."""
        # Test getting remote port
        param = self.client.get_param(S7.p_u16_RemotePort)
        self.assertIsInstance(param, int)
        self.assertEqual(param, 102)  # Default port

    def test_set_param(self) -> None:
        """Test setting parameters."""
        # Test setting receive timeout (parameter 5 according to s7_protocol.py)
        original_timeout = self.client._recv_timeout
        result = self.client.set_param(S7.p_i32_RecvTimeout, 5000)
        self.assertEqual(result, 0)
        self.assertEqual(self.client._recv_timeout, 5000)
        # Restore
        self.client.set_param(S7.p_i32_RecvTimeout, original_timeout)

    def test_disconnect_when_not_connected(self) -> None:
        """Test disconnect when not connected."""
        result = self.client.disconnect()
        self.assertTrue(result)  # disconnect always returns True


@pytest.mark.low_level_client
class TestS7SZL(unittest.TestCase):
    """Test cases for S7SZL class."""

    def test_init_default(self) -> None:
        """Test S7SZL initialization with default size."""
        szl = S7SZL()
        self.assertIsInstance(szl.Header, S7SZLHeader)
        self.assertEqual(len(szl.Data), 1024)

    def test_init_custom_size(self) -> None:
        """Test S7SZL initialization with custom size."""
        szl = S7SZL(data_size=2048)
        self.assertIsInstance(szl.Header, S7SZLHeader)
        self.assertEqual(len(szl.Data), 2048)


@pytest.mark.low_level_client
class TestS7SZLHeader(unittest.TestCase):
    """Test cases for S7SZLHeader class."""

    def test_init(self) -> None:
        """Test S7SZLHeader initialization."""
        header = S7SZLHeader()
        self.assertEqual(header.LENTHDR, 0)
        self.assertEqual(header.N_DR, 0)


if __name__ == "__main__":
    unittest.main()
