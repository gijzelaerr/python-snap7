"""Tests to close identified coverage gaps.

Covers CLI discover command integration and heartbeat with concurrent operations.
"""

import time
import unittest
from unittest.mock import MagicMock, patch

import pytest

from snap7.client import Client
from snap7.server import Server
from snap7.type import SrvArea


# ============================================================================
# CLI discover command
# ============================================================================

click = pytest.importorskip("click")
from click.testing import CliRunner  # noqa: E402
from snap7.cli import main  # noqa: E402


@pytest.mark.util
class TestCLIDiscoverCommand:
    """Test the CLI discover subcommand."""

    def test_discover_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["discover", "--help"])
        assert result.exit_code == 0
        assert "Discover PROFINET devices" in result.output

    def test_discover_no_devices(self) -> None:
        """Test discover command when no devices are found."""
        mock_discover = MagicMock(return_value=[])

        with patch("snap7.discovery.discover", mock_discover):
            runner = CliRunner()
            result = runner.invoke(main, ["discover", "192.168.1.1"])

        assert result.exit_code == 0
        assert "No devices found" in result.output

    def test_discover_with_devices(self) -> None:
        """Test discover command shows found devices."""
        from snap7.discovery import Device

        mock_devices = [
            Device(name="plc-1", ip="192.168.1.10", mac="00:1b:1b:12:34:56"),
            Device(name="plc-2", ip="192.168.1.11", mac="00:1b:1b:12:34:57"),
        ]
        mock_discover = MagicMock(return_value=mock_devices)

        with patch("snap7.discovery.discover", mock_discover):
            runner = CliRunner()
            result = runner.invoke(main, ["discover", "192.168.1.1"])

        assert result.exit_code == 0
        assert "2 device(s)" in result.output
        assert "plc-1" in result.output
        assert "192.168.1.10" in result.output

    def test_discover_with_timeout(self) -> None:
        """Test discover command passes timeout to discover function."""
        mock_discover = MagicMock(return_value=[])

        with patch("snap7.discovery.discover", mock_discover):
            runner = CliRunner()
            result = runner.invoke(main, ["discover", "192.168.1.1", "--timeout", "10"])

        assert result.exit_code == 0
        mock_discover.assert_called_once_with("192.168.1.1", 10.0)

    def test_discover_import_error(self) -> None:
        """Test discover command when pnio-dcp is not installed."""
        mock_discover = MagicMock(side_effect=ImportError("pnio-dcp is required"))

        with patch("snap7.discovery.discover", mock_discover):
            runner = CliRunner()
            result = runner.invoke(main, ["discover", "192.168.1.1"])

        assert result.exit_code != 0


# ============================================================================
# Heartbeat with concurrent operations
# ============================================================================

HEARTBEAT_PORT = 11126


@pytest.mark.client
class TestHeartbeatConcurrency(unittest.TestCase):
    """Test heartbeat doesn't interfere with concurrent read/write operations."""

    server: Server

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = Server()
        cls.server.register_area(SrvArea.DB, 0, bytearray(100))
        cls.server.register_area(SrvArea.DB, 1, bytearray(100))
        cls.server.register_area(SrvArea.MK, 0, bytearray(100))
        cls.server.start(tcp_port=HEARTBEAT_PORT)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server:
            cls.server.stop()
            cls.server.destroy()

    def test_rapid_reads_with_heartbeat(self) -> None:
        """Rapid sequential reads while heartbeat is active should not conflict."""
        client = Client(heartbeat_interval=0.2, auto_reconnect=True, max_retries=3, retry_delay=0.1)
        client.connect("127.0.0.1", 1, 1, HEARTBEAT_PORT)

        try:
            # Perform many rapid reads while heartbeat is running in the background
            for _ in range(20):
                data = client.db_read(1, 0, 4)
                assert len(data) == 4
                time.sleep(0.05)  # Give heartbeat a chance to fire between reads

            assert client.is_alive is True
        finally:
            client.disconnect()

    def test_write_during_heartbeat(self) -> None:
        """Write operations work while heartbeat is probing."""
        client = Client(heartbeat_interval=0.2)
        client.connect("127.0.0.1", 1, 1, HEARTBEAT_PORT)

        try:
            # Do several write/read cycles while heartbeat is running
            for i in range(10):
                client.db_write(1, 0, bytearray([i, i + 1, i + 2, i + 3]))
                data = client.db_read(1, 0, 4)
                assert data == bytearray([i, i + 1, i + 2, i + 3])
                time.sleep(0.1)  # Give heartbeat a chance to fire
        finally:
            client.disconnect()
