"""Unit tests for snap7.low_level.s7_server module."""
import logging
import unittest
from unittest import mock

import pytest

from snap7.low_level.s7_server import S7Server
from snap7.low_level.s7_protocol import S7Protocol as S7

logging.basicConfig(level=logging.WARNING)


@pytest.mark.low_level_server
class TestS7Server(unittest.TestCase):
    """Test cases for S7Server class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.server = S7Server()

    def tearDown(self) -> None:
        """Clean up after tests."""
        if self.server._running:
            self.server.stop()

    def test_init(self) -> None:
        """Test S7Server initialization."""
        self.assertIsNotNone(self.server)
        self.assertEqual(self.server.pdu_length, 480)
        self.assertEqual(self.server.max_pdu_length, 480)
        self.assertEqual(self.server.db_count, 0)
        self.assertEqual(self.server.db_limit, 100)
        self.assertEqual(self.server.cpu_state, S7.S7CpuStatusRun)
        self.assertEqual(self.server.server_status, 0)
        self.assertEqual(self.server.clients_count, 0)
        self.assertFalse(self.server._running)
        self.assertEqual(self.server._last_error, 0)

    def test_register_area(self) -> None:
        """Test registering a memory area."""
        area_code = S7.S7AreaDB
        index = 1
        data = bytearray(1024)

        result = self.server.register_area(area_code, index, data)
        self.assertEqual(result, 0)
        self.assertIn((area_code, index), self.server.memory_areas)

    def test_unregister_area(self) -> None:
        """Test unregistering a memory area."""
        area_code = S7.S7AreaDB
        index = 1
        data = bytearray(1024)

        # Register first
        self.server.register_area(area_code, index, data)
        self.assertIn((area_code, index), self.server.memory_areas)

        # Unregister
        result = self.server.unregister_area(area_code, index)
        self.assertEqual(result, 0)
        self.assertNotIn((area_code, index), self.server.memory_areas)

    def test_unregister_nonexistent_area(self) -> None:
        """Test unregistering a non-existent area."""
        area_code = S7.S7AreaDB
        index = 99

        result = self.server.unregister_area(area_code, index)
        self.assertEqual(result, S7.errCliItemNotAvailable)

    def test_get_status(self) -> None:
        """Test getting server status."""
        server_status, cpu_status, clients_count = self.server.get_status()

        self.assertIsInstance(server_status, int)
        self.assertIsInstance(cpu_status, int)
        self.assertIsInstance(clients_count, int)
        self.assertEqual(server_status, 0)  # Not started
        self.assertEqual(cpu_status, S7.S7CpuStatusRun)
        self.assertEqual(clients_count, 0)

    def test_set_cpu_status(self) -> None:
        """Test setting CPU status."""
        result = self.server.set_cpu_status(S7.S7CpuStatusStop)
        self.assertEqual(result, 0)
        self.assertEqual(self.server.cpu_state, S7.S7CpuStatusStop)

    def test_set_event_callback(self) -> None:
        """Test setting event callback."""
        def callback(event):
            pass

        result = self.server.set_event_callback(callback)
        self.assertEqual(result, 0)
        self.assertEqual(self.server.event_callback, callback)

    def test_get_param(self) -> None:
        """Test getting parameters."""
        # Test getting PDU length parameter
        param = self.server.get_param(1)
        self.assertIsInstance(param, int)

    def test_set_param(self) -> None:
        """Test setting parameters."""
        # Test setting max PDU length parameter
        result = self.server.set_param(S7.p_i32_PDURequest, 512)
        self.assertEqual(result, 0)
        self.assertEqual(self.server.max_pdu_length, 512)

    def test_get_last_error(self) -> None:
        """Test getting last error."""
        error = self.server.get_last_error()
        self.assertEqual(error, 0)


@pytest.mark.low_level_server
class TestS7ServerStartStop(unittest.TestCase):
    """Test cases for S7Server start/stop functionality."""

    def test_start_stop(self) -> None:
        """Test starting and stopping the server."""
        server = S7Server()

        # Start server on a non-standard port to avoid conflicts
        result = server.start("127.0.0.1", tcp_port=10102)
        self.assertEqual(result, 0)
        self.assertTrue(server._running)
        self.assertEqual(server.server_status, 1)

        # Stop server
        result = server.stop()
        self.assertEqual(result, 0)
        self.assertFalse(server._running)

    def test_start_already_running(self) -> None:
        """Test starting server when already running."""
        server = S7Server()
        server.start("127.0.0.1", tcp_port=10103)

        # Try to start again
        result = server.start("127.0.0.1", tcp_port=10103)
        self.assertEqual(result, 0)  # Should return success (already running)

        server.stop()


if __name__ == "__main__":
    unittest.main()
