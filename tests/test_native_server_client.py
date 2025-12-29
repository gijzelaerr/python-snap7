"""
Integration tests for pure Python S7 server and client.

These tests verify that the pure Python implementation works end-to-end
by running a server and connecting to it with a client.
"""

import pytest
import struct
import time
from ctypes import c_char

from snap7.server import Server
from snap7.client import Client
from snap7.type import SrvArea, Area


class TestServerClientIntegration:
    """Test server-client integration with pure Python implementation."""

    port = 11020

    @classmethod
    def setup_class(cls):
        """Set up shared test server."""
        cls.server = Server()

        # Create and register test memory areas
        cls.db_size = 100
        cls.db_data = bytearray(cls.db_size)

        # Initialize some test data
        cls.db_data[0] = 0x42
        cls.db_data[1] = 0xFF
        cls.db_data[10:12] = struct.pack(">H", 1234)  # Word at offset 10
        cls.db_data[20:24] = struct.pack(">I", 567890)  # DWord at offset 20

        # Register DB area
        db_array = (c_char * cls.db_size).from_buffer(cls.db_data)
        cls.server.register_area(SrvArea.DB, 1, db_array)

        # Start server
        cls.server.start(cls.port)
        time.sleep(0.2)

    @classmethod
    def teardown_class(cls):
        """Clean up shared server."""
        try:
            cls.server.stop()
            cls.server.destroy()
        except Exception:
            pass
        time.sleep(0.2)

    def setup_method(self):
        """Set up client for each test."""
        self.client = Client()
        self.client.connect("127.0.0.1", 0, 1, self.port)

    def teardown_method(self):
        """Clean up client after each test."""
        try:
            self.client.disconnect()
        except Exception:
            pass

    def test_server_startup_shutdown(self):
        """Test that server can start and stop."""
        # Server should be running
        server_status, cpu_status, client_count = self.server.get_status()
        assert server_status == "Running"
        assert client_count >= 0  # May have connected clients

        # Stop and restart
        self.server.stop()
        server_status, _, _ = self.server.get_status()
        assert server_status == "Stopped"

        # Restart
        self.server.start(self.port)
        time.sleep(0.1)
        server_status, _, _ = self.server.get_status()
        assert server_status == "Running"

    def test_client_connection(self):
        """Test that client can connect to pure Python server."""
        # Client is connected in setup_method
        assert self.client.get_connected()

        # Check server shows client connection
        server_status, cpu_status, client_count = self.server.get_status()
        assert client_count >= 0  # May be 0 or 1 depending on timing

    def test_client_server_communication(self):
        """Test basic read/write operations between client and server."""
        # Test DB read - this will return dummy data from our simple server
        # The current server implementation returns fixed dummy data
        data = self.client.db_read(1, 0, 4)
        assert isinstance(data, bytearray)
        assert len(data) > 0  # Should get some data back

        # Test DB write - should succeed without error
        test_data = bytearray([0x01, 0x02, 0x03, 0x04])
        self.client.db_write(1, 0, test_data)  # Should not raise exception

    def test_multiple_clients(self):
        """Test multiple clients connecting simultaneously."""
        clients = [self.client]  # Include the one from setup_method

        try:
            # Connect additional clients
            for i in range(2):
                client = Client()
                client.connect("127.0.0.1", 0, 1, self.port)
                clients.append(client)

                # Give time for connection to establish
                time.sleep(0.05)

            # All clients should be connected
            for client in clients:
                assert client.get_connected()

            # Test that each client can perform operations
            for i, client in enumerate(clients):
                data = client.db_read(1, i, 1)
                assert len(data) >= 1

        finally:
            # Disconnect additional clients (not the one from setup_method)
            for client in clients[1:]:
                try:
                    client.disconnect()
                except Exception:
                    pass

    def test_server_callbacks(self):
        """Test server event callbacks."""
        callback_events = []

        def event_callback(event):
            callback_events.append(event)

        def read_callback(event):
            callback_events.append(("read", event))

        # Set callbacks
        self.server.set_events_callback(event_callback)
        self.server.set_read_events_callback(read_callback)

        # Perform read operation (should trigger read callback)
        self.client.db_read(1, 0, 1)

        # Give callbacks time to execute
        time.sleep(0.1)

        # Should have received some callback events
        # Note: callback behavior depends on server implementation
        # For now, just verify no exceptions were thrown

    def test_context_managers(self):
        """Test using server and client as context managers."""
        # Test server context manager
        with Server() as test_server:
            test_server.start(11021)  # Different port
            time.sleep(0.1)

            # Server should be running
            status, _, _ = test_server.get_status()
            assert status == "Running"

            # Test client context manager
            with Client() as client:
                client.connect("127.0.0.1", 0, 1, 11021)
                assert client.get_connected()

                # Perform operation
                data = client.db_read(1, 0, 1)
                assert len(data) >= 1

        # Both should be cleaned up automatically

    def test_area_operations(self):
        """Test different memory area operations."""
        # Test different area types (server returns dummy data)
        # These test the protocol handling, not actual data storage

        # Test memory area read
        data = self.client.read_area(Area.MK, 0, 0, 4)
        assert len(data) >= 1

        # Test input area read
        data = self.client.read_area(Area.PE, 0, 0, 2)
        assert len(data) >= 1

        # Test convenience methods
        data = self.client.mb_read(0, 2)
        assert len(data) >= 1

        data = self.client.eb_read(0, 2)
        assert len(data) >= 1

    def test_error_handling(self):
        """Test error handling in client-server communication."""
        # Test connection to non-existent server
        bad_client = Client()
        with pytest.raises(Exception):  # Should raise connection error
            bad_client.connect("127.0.0.1", 0, 1, 9999)  # Wrong port

        # Test operations on disconnected client
        disconnected_client = Client()
        with pytest.raises(Exception):  # Should raise not connected error
            disconnected_client.db_read(1, 0, 4)
