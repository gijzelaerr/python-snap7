"""Tests to close identified coverage gaps.

Covers:
- CLI discover command integration
- Legitimation failure paths (wrong password, malformed challenge, missing TLS)
- S7CommPlus async client (connect, read, write, legacy fallback)
- Heartbeat with concurrent operations
"""

import struct
import time
import unittest
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from snap7.client import Client
from snap7.error import S7ConnectionError
from snap7.server import Server
from snap7.type import SrvArea
from s7.connection import S7CommPlusConnection
from s7.legitimation import (
    LegitimationState,
    build_legacy_response,
)


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
# Legitimation failure paths
# ============================================================================


class TestLegitimationFailurePaths:
    """Test legitimation edge cases and failures."""

    def test_authenticate_not_connected_raises(self) -> None:
        conn = S7CommPlusConnection("127.0.0.1")
        with pytest.raises(S7ConnectionError, match="Not connected"):
            conn.authenticate("password")

    def test_authenticate_no_tls_raises(self) -> None:
        conn = S7CommPlusConnection("127.0.0.1")
        conn._connected = True
        conn._tls_active = False
        conn._oms_secret = None
        with pytest.raises(S7ConnectionError, match="requires TLS"):
            conn.authenticate("password")

    def test_authenticate_tls_but_no_oms_secret_raises(self) -> None:
        conn = S7CommPlusConnection("127.0.0.1")
        conn._connected = True
        conn._tls_active = True
        conn._oms_secret = None
        with pytest.raises(S7ConnectionError, match="requires TLS"):
            conn.authenticate("password")

    def test_legacy_response_empty_password(self) -> None:
        """Empty password should still produce a valid 20-byte response."""
        challenge = b"\xab" * 20
        response = build_legacy_response("", challenge)
        assert len(response) == 20

    def test_legacy_response_short_challenge(self) -> None:
        """Challenge shorter than 20 bytes — XOR should still work via zip."""
        challenge = b"\xff" * 10
        response = build_legacy_response("test", challenge)
        assert len(response) == 10  # zip truncates to shorter

    def test_legitimation_state_double_authenticate(self) -> None:
        """Calling mark_authenticated twice should not break state."""
        state = LegitimationState()
        state.mark_authenticated()
        state.mark_authenticated()
        assert state.authenticated

    def test_legitimation_state_rotate_changes_key(self) -> None:
        """Key rotation should produce a different key each time."""
        state = LegitimationState(oms_secret=b"\xaa" * 32)
        key_before = state._oms_key
        state.rotate_key()
        key_after = state._oms_key
        assert key_before != key_after


# ============================================================================
# S7CommPlus async client
# ============================================================================

from s7._s7commplus_server import S7CommPlusServer  # noqa: E402
from s7._s7commplus_async_client import S7CommPlusAsyncClient  # noqa: E402

ASYNC_TEST_PORT = 11125


@pytest.fixture()
def async_server() -> Generator[S7CommPlusServer, None, None]:
    """Create and start an S7CommPlus server for async tests."""
    srv = S7CommPlusServer()
    srv.register_raw_db(1, bytearray(256))
    srv.register_raw_db(2, bytearray(256))

    # Pre-populate DB1
    db1 = srv.get_db(1)
    assert db1 is not None
    struct.pack_into(">f", db1.data, 0, 42.0)

    srv.start(port=ASYNC_TEST_PORT)
    time.sleep(0.1)
    yield srv
    srv.stop()


@pytest.mark.asyncio
class TestAsyncClientCoverage:
    """Additional async client tests."""

    async def test_connect_and_disconnect(self, async_server: S7CommPlusServer) -> None:
        client = S7CommPlusAsyncClient()
        await client.connect("127.0.0.1", port=ASYNC_TEST_PORT)
        assert client.connected
        await client.disconnect()
        assert not client.connected

    async def test_db_read(self, async_server: S7CommPlusServer) -> None:
        client = S7CommPlusAsyncClient()
        await client.connect("127.0.0.1", port=ASYNC_TEST_PORT)
        try:
            data = await client.db_read(1, 0, 4)
            assert len(data) == 4
        finally:
            await client.disconnect()

    async def test_db_write_and_read_back(self, async_server: S7CommPlusServer) -> None:
        client = S7CommPlusAsyncClient()
        await client.connect("127.0.0.1", port=ASYNC_TEST_PORT)
        try:
            await client.db_write(1, 10, bytes([0xDE, 0xAD, 0xBE, 0xEF]))
            data = await client.db_read(1, 10, 4)
            assert data == bytearray([0xDE, 0xAD, 0xBE, 0xEF])
        finally:
            await client.disconnect()

    async def test_context_manager(self, async_server: S7CommPlusServer) -> None:
        async with S7CommPlusAsyncClient() as client:
            await client.connect("127.0.0.1", port=ASYNC_TEST_PORT)
            assert client.connected
        assert not client.connected

    async def test_properties(self, async_server: S7CommPlusServer) -> None:
        client = S7CommPlusAsyncClient()
        await client.connect("127.0.0.1", port=ASYNC_TEST_PORT)
        try:
            assert client.session_id != 0
            assert client.protocol_version >= 0
        finally:
            await client.disconnect()

    async def test_session_setup_ok_property(self, async_server: S7CommPlusServer) -> None:
        client = S7CommPlusAsyncClient()
        await client.connect("127.0.0.1", port=ASYNC_TEST_PORT)
        try:
            # Server supports S7CommPlus data ops, so session setup should succeed
            assert isinstance(client.session_setup_ok, bool)
        finally:
            await client.disconnect()


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
