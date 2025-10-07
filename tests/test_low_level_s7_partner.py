"""Unit tests for snap7.low_level.s7_partner module."""
import logging
import unittest
from unittest import mock

import pytest

from snap7.low_level.s7_partner import S7Partner

logging.basicConfig(level=logging.WARNING)


@pytest.mark.low_level_partner
class TestS7Partner(unittest.TestCase):
    """Test cases for S7Partner class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.partner = S7Partner()

    def tearDown(self) -> None:
        """Clean up after tests."""
        if self.partner._running:
            self.partner.stop()
        self.partner.destroy()

    def test_init(self) -> None:
        """Test S7Partner initialization."""
        self.assertIsNotNone(self.partner)
        self.assertEqual(self.partner.is_active, False)
        self.assertEqual(self.partner.pdu_length, 480)
        self.assertEqual(self.partner.max_pdu_length, 480)
        self.assertEqual(self.partner.local_ip, "0.0.0.0")
        self.assertEqual(self.partner.local_port, 102)
        self.assertEqual(self.partner.remote_ip, "")
        self.assertEqual(self.partner.remote_port, 102)
        self.assertEqual(self.partner.local_tsap, 0x0100)
        self.assertEqual(self.partner.remote_tsap, 0x0200)
        self.assertFalse(self.partner._connected)
        self.assertFalse(self.partner._running)
        self.assertEqual(self.partner._last_error, 0)
        self.assertEqual(self.partner._last_job_result, 0)

    def test_init_active(self) -> None:
        """Test S7Partner initialization as active partner."""
        partner = S7Partner(active=True)
        self.assertTrue(partner.is_active)
        partner.destroy()

    def test_create(self) -> None:
        """Test creating partner."""
        result = self.partner.create(active=False)
        self.assertEqual(result, 0)
        self.assertFalse(self.partner.is_active)

    def test_create_active(self) -> None:
        """Test creating active partner."""
        result = self.partner.create(active=True)
        self.assertEqual(result, 0)
        self.assertTrue(self.partner.is_active)

    def test_destroy(self) -> None:
        """Test destroying partner."""
        result = self.partner.destroy()
        self.assertEqual(result, 0)

    def test_start(self) -> None:
        """Test starting partner."""
        # For a passive partner without remote_ip, start() will attempt to bind
        # For active partner without remote_ip set, it returns errIsoInvalidParams (3)
        result = self.partner.start()
        # Passive partner without connection will either succeed or fail with socket error
        # Active partner will return error 3 (errIsoInvalidParams)
        self.assertIsInstance(result, int)

    def test_stop(self) -> None:
        """Test stopping partner."""
        self.partner.start()
        result = self.partner.stop()
        self.assertEqual(result, 0)
        self.assertFalse(self.partner._running)

    def test_get_status(self) -> None:
        """Test getting partner status."""
        connected, running, last_error = self.partner.get_status()

        self.assertIsInstance(connected, bool)
        self.assertIsInstance(running, bool)
        self.assertIsInstance(last_error, int)
        self.assertFalse(connected)
        self.assertFalse(running)
        self.assertEqual(last_error, 0)

    def test_get_last_error(self) -> None:
        """Test getting last error."""
        error = self.partner.get_last_error()
        self.assertEqual(error, 0)

    def test_get_stats(self) -> None:
        """Test getting statistics."""
        stats = self.partner.get_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn("bytes_sent", stats)
        self.assertIn("bytes_recv", stats)
        self.assertIn("send_errors", stats)
        self.assertIn("recv_errors", stats)
        self.assertEqual(stats["bytes_sent"], 0)
        self.assertEqual(stats["bytes_recv"], 0)
        self.assertEqual(stats["send_errors"], 0)
        self.assertEqual(stats["recv_errors"], 0)

    def test_get_times(self) -> None:
        """Test getting times."""
        times = self.partner.get_times()

        self.assertIsInstance(times, dict)
        self.assertIn("send_timeout", times)
        self.assertIn("recv_timeout", times)
        self.assertIn("ping_timeout", times)

    def test_get_param(self) -> None:
        """Test getting parameters."""
        # Test getting ping timeout (parameter 3)
        from snap7.low_level.s7_protocol import S7Protocol as S7
        param = self.partner.get_param(S7.p_i32_PingTimeout)
        self.assertIsInstance(param, int)
        self.assertEqual(param, 1000)

    def test_set_param(self) -> None:
        """Test setting parameters."""
        # Test setting send timeout (parameter 4)
        from snap7.low_level.s7_protocol import S7Protocol as S7
        result = self.partner.set_param(S7.p_i32_SendTimeout, 5000)
        self.assertEqual(result, 0)
        self.assertEqual(self.partner.send_timeout, 5000)

    def test_set_send_callback(self) -> None:
        """Test setting send callback."""
        def callback(event):
            pass

        result = self.partner.set_send_callback(callback)
        self.assertEqual(result, 0)
        self.assertEqual(self.partner.send_callback, callback)

    def test_set_recv_callback(self) -> None:
        """Test setting receive callback."""
        def callback(event):
            pass

        result = self.partner.set_recv_callback(callback)
        self.assertEqual(result, 0)
        self.assertEqual(self.partner.recv_callback, callback)

    def test_check_as_b_send_completion(self) -> None:
        """Test checking async send completion."""
        status, result = self.partner.check_as_b_send_completion()

        self.assertIsInstance(status, int)
        self.assertIsInstance(result, int)

    def test_check_as_b_recv_completion(self) -> None:
        """Test checking async receive completion."""
        result = self.partner.check_as_b_recv_completion()

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        status, error_code = result
        self.assertIsInstance(status, int)
        self.assertIsInstance(error_code, int)


@pytest.mark.low_level_partner
class TestS7PartnerBuffers(unittest.TestCase):
    """Test cases for S7Partner buffer operations."""

    def test_send_buffer_initialization(self) -> None:
        """Test send buffer initialization."""
        partner = S7Partner()
        self.assertEqual(len(partner.send_buffer), 2048)
        self.assertEqual(partner.send_size, 0)
        partner.destroy()

    def test_recv_buffer_initialization(self) -> None:
        """Test receive buffer initialization."""
        partner = S7Partner()
        self.assertEqual(len(partner.recv_buffer), 2048)
        self.assertEqual(partner.recv_size, 0)
        partner.destroy()

    def test_send_buffer_write(self) -> None:
        """Test writing to send buffer."""
        partner = S7Partner()
        test_data = b"Hello, Partner!"
        partner.send_buffer[:len(test_data)] = test_data
        partner.send_size = len(test_data)

        self.assertEqual(partner.send_size, len(test_data))
        self.assertEqual(bytes(partner.send_buffer[:partner.send_size]), test_data)
        partner.destroy()


if __name__ == "__main__":
    unittest.main()
