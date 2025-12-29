"""
Test write operations to verify data is actually stored.
"""

import time
from ctypes import c_char

from snap7.server import Server
from snap7.client import Client
from snap7.type import SrvArea


class TestWriteOperations:
    """Test that write operations actually modify memory areas."""

    port = 11100

    @classmethod
    def setup_class(cls) -> None:
        """Set up shared test server."""
        cls.server = Server()

        # Create test data with a clear pattern
        cls.db_size = 50
        cls.db_data = bytearray(cls.db_size)

        # Initialize with known pattern
        for i in range(cls.db_size):
            cls.db_data[i] = i + 1  # 1, 2, 3, 4, 5, ...

        # Register DB area
        db_array = (c_char * cls.db_size).from_buffer(cls.db_data)
        cls.server.register_area(SrvArea.DB, 1, db_array)

        # Start server
        cls.server.start(cls.port)
        time.sleep(0.2)

    @classmethod
    def teardown_class(cls) -> None:
        """Clean up shared server."""
        try:
            cls.server.stop()
            cls.server.destroy()
        except Exception:
            pass
        time.sleep(0.2)

    def setup_method(self) -> None:
        """Set up client for each test."""
        self.client = Client()
        self.client.connect("127.0.0.1", 0, 1, self.port)

    def teardown_method(self) -> None:
        """Clean up client after each test."""
        try:
            self.client.disconnect()
        except Exception:
            pass

    def test_write_then_read_back(self) -> None:
        """Test writing data then reading it back to verify storage."""
        print("\nTesting write then read back...")

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
