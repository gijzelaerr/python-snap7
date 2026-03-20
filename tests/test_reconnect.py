"""Tests for connection heartbeat and automatic reconnection features."""

import logging
import threading
import time
import unittest

import pytest

from snap7.client import Client
from snap7.error import S7ConnectionError
from snap7.server import Server
from snap7.type import SrvArea

logging.basicConfig(level=logging.WARNING)

ip = "127.0.0.1"
tcpport = 1103  # Use different port to avoid conflict with test_client.py
db_number = 1
rack = 1
slot = 1


@pytest.mark.client
class TestAutoReconnectDefaults(unittest.TestCase):
    """Test that default behavior is unchanged when features are disabled."""

    server: Server

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = Server()
        cls.server.register_area(SrvArea.DB, 0, bytearray(100))
        cls.server.register_area(SrvArea.DB, 1, bytearray(100))
        cls.server.register_area(SrvArea.MK, 0, bytearray(100))
        cls.server.start(tcp_port=tcpport)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server:
            cls.server.stop()
            cls.server.destroy()

    def test_default_auto_reconnect_disabled(self) -> None:
        """Default client has auto_reconnect=False."""
        client = Client()
        assert client._auto_reconnect is False
        assert client._heartbeat_interval == 0

    def test_default_client_works_normally(self) -> None:
        """Default client connects and operates without new features interfering."""
        client = Client()
        client.connect(ip, rack, slot, tcpport)
        try:
            data = client.db_read(db_number, 0, 4)
            assert len(data) == 4
        finally:
            client.disconnect()

    def test_is_alive_without_heartbeat(self) -> None:
        """is_alive reflects connection state when heartbeat is disabled."""
        client = Client()
        assert client.is_alive is False

        client.connect(ip, rack, slot, tcpport)
        try:
            assert client.is_alive is True
        finally:
            client.disconnect()

        assert client.is_alive is False

    def test_auto_reconnect_params_stored(self) -> None:
        """Verify that auto-reconnect parameters are stored on the client."""
        client = Client(
            auto_reconnect=True,
            max_retries=5,
            retry_delay=0.5,
            backoff_factor=3.0,
            max_delay=60.0,
        )
        assert client._auto_reconnect is True
        assert client._max_retries == 5
        assert client._retry_delay == 0.5
        assert client._backoff_factor == 3.0
        assert client._max_delay == 60.0


@pytest.mark.client
class TestAutoReconnect(unittest.TestCase):
    """Test automatic reconnection on connection loss."""

    server: Server

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = Server()
        cls.server.register_area(SrvArea.DB, 0, bytearray(100))
        cls.server.register_area(SrvArea.DB, 1, bytearray(100))
        cls.server.register_area(SrvArea.MK, 0, bytearray(100))
        cls.server.start(tcp_port=tcpport)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server:
            cls.server.stop()
            cls.server.destroy()

    def test_reconnect_on_read_failure(self) -> None:
        """Client reconnects transparently when a db_read fails due to connection loss."""
        client = Client(auto_reconnect=True, max_retries=3, retry_delay=0.1)
        client.connect(ip, rack, slot, tcpport)

        try:
            # Verify initial read works
            data = client.db_read(db_number, 0, 4)
            assert len(data) == 4

            # Simulate connection loss by closing the socket
            if client.connection and client.connection.socket:
                client.connection.socket.close()
            client.connected = False

            # The next read should trigger reconnection and succeed
            data = client.db_read(db_number, 0, 4)
            assert len(data) == 4
            assert client.connected is True
        finally:
            client.disconnect()

    def test_reconnect_on_write_failure(self) -> None:
        """Client reconnects transparently when a db_write fails due to connection loss."""
        client = Client(auto_reconnect=True, max_retries=3, retry_delay=0.1)
        client.connect(ip, rack, slot, tcpport)

        try:
            # Verify initial write works
            client.db_write(db_number, 0, bytearray([1, 2, 3, 4]))

            # Simulate connection loss
            if client.connection and client.connection.socket:
                client.connection.socket.close()
            client.connected = False

            # The next write should trigger reconnection and succeed
            client.db_write(db_number, 0, bytearray([5, 6, 7, 8]))
            assert client.connected is True

            # Verify the data was written after reconnection
            data = client.db_read(db_number, 0, 4)
            assert data == bytearray([5, 6, 7, 8])
        finally:
            client.disconnect()

    def test_no_reconnect_when_disabled(self) -> None:
        """Without auto_reconnect, connection errors propagate immediately."""
        client = Client(auto_reconnect=False)
        client.connect(ip, rack, slot, tcpport)

        try:
            # Simulate connection loss
            if client.connection and client.connection.socket:
                client.connection.socket.close()
            client.connected = False

            with pytest.raises(S7ConnectionError):
                client.db_read(db_number, 0, 4)
        finally:
            client.disconnect()

    def test_reconnect_callbacks(self) -> None:
        """on_disconnect and on_reconnect callbacks are invoked."""
        disconnect_called = threading.Event()
        reconnect_called = threading.Event()

        def on_disconnect() -> None:
            disconnect_called.set()

        def on_reconnect() -> None:
            reconnect_called.set()

        client = Client(
            auto_reconnect=True,
            max_retries=3,
            retry_delay=0.1,
            on_disconnect=on_disconnect,
            on_reconnect=on_reconnect,
        )
        client.connect(ip, rack, slot, tcpport)

        try:
            # Simulate connection loss
            if client.connection and client.connection.socket:
                client.connection.socket.close()
            client.connected = False

            # Trigger reconnection via a read
            data = client.db_read(db_number, 0, 4)
            assert len(data) == 4

            assert disconnect_called.is_set(), "on_disconnect was not called"
            assert reconnect_called.is_set(), "on_reconnect was not called"
        finally:
            client.disconnect()

    def test_reconnect_max_retries_exhausted(self) -> None:
        """S7ConnectionError is raised after max_retries are exhausted."""
        client = Client(auto_reconnect=True, max_retries=2, retry_delay=0.05)
        client.connect(ip, rack, slot, tcpport)

        # Stop the server so reconnection will fail
        self.__class__.server.stop()

        try:
            # Simulate connection loss
            if client.connection and client.connection.socket:
                client.connection.socket.close()
            client.connected = False

            with pytest.raises(S7ConnectionError, match="Reconnection failed"):
                client.db_read(db_number, 0, 4)
        finally:
            client.disconnect()
            # Restart server for other tests
            self.__class__.server = Server()
            self.__class__.server.register_area(SrvArea.DB, 0, bytearray(100))
            self.__class__.server.register_area(SrvArea.DB, 1, bytearray(100))
            self.__class__.server.register_area(SrvArea.MK, 0, bytearray(100))
            self.__class__.server.start(tcp_port=tcpport)

    def test_connection_params_preserved_after_reconnect(self) -> None:
        """Host, port, rack, slot are preserved and reused during reconnection."""
        client = Client(auto_reconnect=True, max_retries=3, retry_delay=0.1)
        client.connect(ip, rack, slot, tcpport)

        try:
            original_host = client.host
            original_port = client.port
            original_rack = client.rack
            original_slot = client.slot

            # Simulate connection loss and trigger reconnect
            if client.connection and client.connection.socket:
                client.connection.socket.close()
            client.connected = False
            client.db_read(db_number, 0, 4)

            # Verify connection params are preserved
            assert client.host == original_host
            assert client.port == original_port
            assert client.rack == original_rack
            assert client.slot == original_slot
        finally:
            client.disconnect()


@pytest.mark.client
class TestHeartbeat(unittest.TestCase):
    """Test heartbeat/watchdog functionality."""

    server: Server

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = Server()
        cls.server.register_area(SrvArea.DB, 0, bytearray(100))
        cls.server.register_area(SrvArea.DB, 1, bytearray(100))
        cls.server.register_area(SrvArea.MK, 0, bytearray(100))
        cls.server.start(tcp_port=tcpport)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server:
            cls.server.stop()
            cls.server.destroy()

    def test_heartbeat_disabled_by_default(self) -> None:
        """Heartbeat thread does not start when interval=0."""
        client = Client()
        client.connect(ip, rack, slot, tcpport)
        try:
            assert client._heartbeat_thread is None
        finally:
            client.disconnect()

    def test_heartbeat_starts_and_stops(self) -> None:
        """Heartbeat thread starts on connect and stops on disconnect."""
        client = Client(heartbeat_interval=0.5)
        client.connect(ip, rack, slot, tcpport)

        try:
            assert client._heartbeat_thread is not None
            assert client._heartbeat_thread.is_alive()
            assert client._heartbeat_thread.daemon is True
            assert client.is_alive is True
        finally:
            client.disconnect()

        # After disconnect, thread should stop
        assert client._heartbeat_thread is None
        assert client.is_alive is False

    def test_heartbeat_detects_alive_connection(self) -> None:
        """Heartbeat correctly reports connection as alive."""
        client = Client(heartbeat_interval=0.3)
        client.connect(ip, rack, slot, tcpport)

        try:
            # Wait for at least one heartbeat cycle
            time.sleep(0.5)
            assert client.is_alive is True
        finally:
            client.disconnect()

    def test_heartbeat_detects_dead_connection(self) -> None:
        """Heartbeat sets is_alive=False when connection is lost."""
        client = Client(heartbeat_interval=0.3, auto_reconnect=False)
        client.connect(ip, rack, slot, tcpport)

        try:
            assert client.is_alive is True

            # Kill the connection without going through disconnect()
            if client.connection and client.connection.socket:
                client.connection.socket.close()

            # Wait for heartbeat to detect the failure
            time.sleep(1.0)
            assert client.is_alive is False
        finally:
            client.disconnect()

    def test_heartbeat_triggers_reconnect(self) -> None:
        """When heartbeat fails and auto_reconnect is enabled, it reconnects."""
        reconnect_called = threading.Event()

        def on_reconnect() -> None:
            reconnect_called.set()

        client = Client(
            heartbeat_interval=0.3,
            auto_reconnect=True,
            max_retries=3,
            retry_delay=0.1,
            on_reconnect=on_reconnect,
        )
        client.connect(ip, rack, slot, tcpport)

        try:
            # Kill the connection
            if client.connection and client.connection.socket:
                client.connection.socket.close()

            # Wait for heartbeat to detect and trigger reconnect
            reconnect_called.wait(timeout=3.0)
            assert reconnect_called.is_set(), "Heartbeat did not trigger reconnection"

            # Give some time for the reconnect to complete fully
            time.sleep(0.5)
            assert client.is_alive is True
            assert client.connected is True

            # Verify connection works after heartbeat-triggered reconnect
            data = client.db_read(db_number, 0, 4)
            assert len(data) == 4
        finally:
            client.disconnect()

    def test_context_manager_stops_heartbeat(self) -> None:
        """Heartbeat is properly stopped when using context manager."""
        with Client(heartbeat_interval=0.3) as client:
            client.connect(ip, rack, slot, tcpport)
            assert client._heartbeat_thread is not None

        # After context exit, heartbeat should be stopped
        assert client._heartbeat_thread is None


@pytest.mark.client
class TestBackwardCompatibility(unittest.TestCase):
    """Ensure the new features don't break backward compatibility."""

    server: Server

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = Server()
        cls.server.register_area(SrvArea.DB, 0, bytearray(100))
        cls.server.register_area(SrvArea.DB, 1, bytearray(100))
        cls.server.register_area(SrvArea.PA, 0, bytearray(100))
        cls.server.register_area(SrvArea.PE, 0, bytearray(100))
        cls.server.register_area(SrvArea.MK, 0, bytearray(100))
        cls.server.start(tcp_port=tcpport)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server:
            cls.server.stop()
            cls.server.destroy()

    def test_old_init_signature_still_works(self) -> None:
        """Client() and Client(lib_location=None) still work."""
        c1 = Client()
        assert c1._auto_reconnect is False

        c2 = Client(lib_location=None)
        assert c2._auto_reconnect is False

        c3 = Client(lib_location="/some/path")
        assert c3._auto_reconnect is False

    def test_read_write_without_reconnect(self) -> None:
        """Standard read/write operations work without reconnect enabled."""
        client = Client()
        client.connect(ip, rack, slot, tcpport)
        try:
            # Write
            client.db_write(db_number, 0, bytearray([10, 20, 30, 40]))
            # Read
            data = client.db_read(db_number, 0, 4)
            assert data == bytearray([10, 20, 30, 40])
        finally:
            client.disconnect()

    def test_get_connected(self) -> None:
        """get_connected still works correctly."""
        client = Client()
        assert client.get_connected() is False

        client.connect(ip, rack, slot, tcpport)
        try:
            assert client.get_connected() is True
        finally:
            client.disconnect()

        assert client.get_connected() is False

    def test_mb_read_write(self) -> None:
        """Marker area read/write works with reconnect-aware code path."""
        client = Client(auto_reconnect=True, max_retries=1, retry_delay=0.1)
        client.connect(ip, rack, slot, tcpport)
        try:
            client.mb_write(0, 4, bytearray([0xAA, 0xBB, 0xCC, 0xDD]))
            data = client.mb_read(0, 4)
            assert data == bytearray([0xAA, 0xBB, 0xCC, 0xDD])
        finally:
            client.disconnect()
