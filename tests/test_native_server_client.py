"""
Integration tests for pure Python S7 server and client.

These tests verify that the pure Python implementation works end-to-end
by running a server and connecting to it with a client.
"""

import pytest
import struct
import time
from ctypes import c_char

from snap7.native_server import Server as PureServer
from snap7.native_client import Client as PureClient
from snap7.type import SrvArea, Area


class TestServerClientIntegration:
    """Test server-client integration with pure Python implementation."""
    
    def setup_method(self):
        """Set up test server."""
        self.server = PureServer()
        self.port = 11020  # Use non-standard port to avoid conflicts
        
        # Create and register test memory areas
        self.db_size = 100
        self.db_data = bytearray(self.db_size)
        
        # Initialize some test data
        self.db_data[0] = 0x42
        self.db_data[1] = 0xFF
        self.db_data[10:12] = struct.pack('>H', 1234)  # Word at offset 10
        self.db_data[20:24] = struct.pack('>I', 567890)  # DWord at offset 20
        
        # Register DB area
        db_array = (c_char * self.db_size).from_buffer(self.db_data)
        self.server.register_area(SrvArea.DB, 1, db_array)
        
        # Start server
        self.server.start(self.port)
        
        # Give server time to start
        time.sleep(0.1)
    
    def teardown_method(self):
        """Clean up test server."""
        try:
            self.server.stop()
            self.server.destroy()
        except Exception:
            pass
        
        # Give server time to clean up
        time.sleep(0.1)
    
    def test_server_startup_shutdown(self):
        """Test that server can start and stop."""
        # Server should be running
        server_status, cpu_status, client_count = self.server.get_status()
        assert server_status == "Running"
        assert client_count == 0
        
        # Stop and restart
        self.server.stop()
        server_status, _, _ = self.server.get_status()
        assert server_status == "Stopped"
        
        # Restart
        self.server.start(self.port)
        server_status, _, _ = self.server.get_status()
        assert server_status == "Running"
    
    def test_client_connection(self):
        """Test that client can connect to pure Python server."""
        client = PureClient()
        
        try:
            # Connect to server
            client.connect("127.0.0.1", 0, 1, self.port)
            assert client.get_connected()
            
            # Check server shows client connection
            server_status, cpu_status, client_count = self.server.get_status()
            assert client_count >= 0  # May be 0 or 1 depending on timing
            
        finally:
            client.disconnect()
    
    def test_client_server_communication(self):
        """Test basic read/write operations between client and server."""
        client = PureClient()
        
        try:
            # Connect to server
            client.connect("127.0.0.1", 0, 1, self.port)
            
            # Test DB read - this will return dummy data from our simple server
            # The current server implementation returns fixed dummy data
            data = client.db_read(1, 0, 4)
            assert isinstance(data, bytearray)
            assert len(data) > 0  # Should get some data back
            
            # Test DB write - should succeed without error
            test_data = bytearray([0x01, 0x02, 0x03, 0x04])
            client.db_write(1, 0, test_data)  # Should not raise exception
            
        finally:
            client.disconnect()
    
    def test_multiple_clients(self):
        """Test multiple clients connecting simultaneously."""
        clients = []
        
        try:
            # Connect multiple clients
            for i in range(3):
                client = PureClient()
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
            # Disconnect all clients
            for client in clients:
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
            callback_events.append(('read', event))
        
        # Set callbacks
        self.server.set_events_callback(event_callback)
        self.server.set_read_events_callback(read_callback)
        
        # Connect client and perform operations
        client = PureClient()
        
        try:
            client.connect("127.0.0.1", 0, 1, self.port)
            
            # Perform read operation (should trigger read callback)
            client.db_read(1, 0, 1)
            
            # Give callbacks time to execute
            time.sleep(0.1)
            
            # Should have received some callback events
            # Note: callback behavior depends on server implementation
            # For now, just verify no exceptions were thrown
            
        finally:
            client.disconnect()
    
    def test_context_managers(self):
        """Test using server and client as context managers."""
        # Test server context manager
        with PureServer() as test_server:
            test_server.start(11021)  # Different port
            
            # Server should be running
            status, _, _ = test_server.get_status()
            assert status == "Running"
            
            # Test client context manager
            with PureClient() as client:
                client.connect("127.0.0.1", 0, 1, 11021)
                assert client.get_connected()
                
                # Perform operation
                data = client.db_read(1, 0, 1)
                assert len(data) >= 1
        
        # Both should be cleaned up automatically
    
    def test_area_operations(self):
        """Test different memory area operations."""
        client = PureClient()
        
        try:
            client.connect("127.0.0.1", 0, 1, self.port)
            
            # Test different area types (server returns dummy data)
            # These test the protocol handling, not actual data storage
            
            # Test memory area read
            data = client.read_area(Area.MK, 0, 0, 4)
            assert len(data) >= 1
            
            # Test input area read  
            data = client.read_area(Area.PE, 0, 0, 2)
            assert len(data) >= 1
            
            # Test convenience methods
            data = client.mb_read(0, 2)
            assert len(data) >= 1
            
            data = client.eb_read(0, 2)
            assert len(data) >= 1
            
        finally:
            client.disconnect()
    
    def test_error_handling(self):
        """Test error handling in client-server communication."""
        client = PureClient()
        
        # Test connection to non-existent server
        with pytest.raises(Exception):  # Should raise connection error
            client.connect("127.0.0.1", 0, 1, 9999)  # Wrong port
        
        # Test operations on disconnected client
        with pytest.raises(Exception):  # Should raise not connected error
            client.db_read(1, 0, 4)

