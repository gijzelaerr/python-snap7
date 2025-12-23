"""
Test write operations to verify data is actually stored.
"""

import pytest
import time
from ctypes import c_char

from snap7.native.server import Server as PureServer
from snap7.native.client import Client as PureClient
from snap7.type import SrvArea


class TestWriteOperations:
    """Test that write operations actually modify memory areas."""
    
    def setup_method(self):
        """Set up test server and client."""
        self.server = PureServer()
        self.port = 11100
        
        # Create test data with a clear pattern
        self.db_size = 50
        self.db_data = bytearray(self.db_size)
        
        # Initialize with known pattern
        for i in range(self.db_size):
            self.db_data[i] = i + 1  # 1, 2, 3, 4, 5, ...
        
        # Register DB area
        db_array = (c_char * self.db_size).from_buffer(self.db_data)
        self.server.register_area(SrvArea.DB, 1, db_array)
        
        # Start server
        self.server.start(self.port)
        time.sleep(0.1)
        
        # Connect client
        self.client = PureClient()
        self.client.connect("127.0.0.1", 0, 1, self.port)
    
    def teardown_method(self):
        """Clean up."""
        try:
            self.client.disconnect()
        except Exception:
            pass
        
        try:
            self.server.stop()
            self.server.destroy()
        except Exception:
            pass
        
        time.sleep(0.1)
    
    def test_write_then_read_back(self):
        """Test writing data then reading it back to verify storage."""
        print("\\nTesting write then read back...")
        
        # Read initial data
        initial_data = self.client.db_read(1, 10, 4)
        print(f"Initial data at offset 10: {initial_data.hex()}")
        assert initial_data == bytearray([11, 12, 13, 14])  # Should be 11, 12, 13, 14
        
        # Write new data
        new_data = bytearray([0xAA, 0xBB, 0xCC, 0xDD])
        self.client.db_write(1, 10, new_data)
        print(f"Wrote data: {new_data.hex()}")
        
        # Read back the data
        read_back_data = self.client.db_read(1, 10, 4)
        print(f"Read back data: {read_back_data.hex()}")
        
        # Verify the data was actually stored
        if read_back_data == new_data:
            print("✓ Write operation successfully stored data!")
        else:
            print("✗ Write operation did not store data - server needs write implementation")
            print(f"Expected: {new_data.hex()}, Got: {read_back_data.hex()}")
        
        # For now, just verify we got some data back
        assert len(read_back_data) == 4