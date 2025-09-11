"""
Test address parsing in server to verify different sizes and offsets work.
"""

import pytest
import time
import struct
from ctypes import c_char

from snap7.native_server import Server as PureServer
from snap7.native_client import Client as PureClient
from snap7.type import SrvArea


class TestAddressParsing:
    """Test address parsing and memory access with different parameters."""
    
    def setup_method(self):
        """Set up test server and client."""
        self.server = PureServer()
        self.port = 11090
        
        # Create test data with a clear pattern
        self.db_size = 50
        self.db_data = bytearray(self.db_size)
        
        # Set incremental pattern for easy verification
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
    
    def test_different_read_sizes(self):
        """Test reading different sizes."""
        print("\\nTesting different read sizes...")
        
        # Test 1 byte
        data = self.client.db_read(1, 0, 1)
        print(f"Read 1 byte at offset 0: {data.hex()} (expected: 01)")
        assert len(data) == 1
        assert data[0] == 1
        
        # Test 2 bytes
        data = self.client.db_read(1, 0, 2)
        print(f"Read 2 bytes at offset 0: {data.hex()} (expected: 0102)")
        assert len(data) == 2
        assert data[0] == 1 and data[1] == 2
        
        # Test 10 bytes (this was failing before)
        data = self.client.db_read(1, 0, 10)
        print(f"Read 10 bytes at offset 0: {data.hex()} (expected: 0102030405060708090a)")
        assert len(data) == 10
        for i in range(10):
            assert data[i] == i + 1, f"Byte {i}: expected {i+1}, got {data[i]}"
    
    def test_different_offsets(self):
        """Test reading from different offsets."""
        print("\\nTesting different offsets...")
        
        # Test offset 5, read 4 bytes
        data = self.client.db_read(1, 5, 4)
        print(f"Read 4 bytes at offset 5: {data.hex()} (expected: 06070809)")
        assert len(data) == 4
        assert data[0] == 6 and data[1] == 7 and data[2] == 8 and data[3] == 9
        
        # Test offset 10, read 5 bytes
        data = self.client.db_read(1, 10, 5)
        print(f"Read 5 bytes at offset 10: {data.hex()} (expected: 0b0c0d0e0f)")
        assert len(data) == 5
        for i in range(5):
            assert data[i] == 11 + i, f"Byte {i}: expected {11+i}, got {data[i]}"
    
    def test_large_read(self):
        """Test reading larger amounts of data."""
        print("\\nTesting large read...")
        
        # Read 20 bytes
        data = self.client.db_read(1, 0, 20)
        print(f"Read 20 bytes: {data.hex()}")
        assert len(data) == 20
        
        # Verify the pattern
        for i in range(20):
            expected = i + 1
            assert data[i] == expected, f"Byte {i}: expected {expected}, got {data[i]}"
    
    def test_boundary_conditions(self):
        """Test reading at boundaries."""
        print("\\nTesting boundary conditions...")
        
        # Read near end of area
        data = self.client.db_read(1, 45, 5)
        print(f"Read 5 bytes at offset 45: {data.hex()}")
        assert len(data) == 5
        
        # Should get: 46, 47, 48, 49, 50 (for valid data), then padding if needed
        for i in range(min(5, self.db_size - 45)):
            expected = 46 + i
            assert data[i] == expected, f"Byte {i}: expected {expected}, got {data[i]}"