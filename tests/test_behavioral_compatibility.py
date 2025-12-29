"""
Behavioral Compatibility Tests.

Verify that the native Python implementation behaves correctly according to
S7 protocol semantics - testing real operations, not just API existence.
"""

import time
from ctypes import c_char
from typing import Generator, Tuple

import pytest

from snap7 import Client, Server, Area, Block
from snap7.type import SrvArea


@pytest.fixture
def server_client_pair() -> Generator[Tuple[Server, Client], None, None]:
    """Fixture that provides a connected server and client."""
    server = Server()
    port = 11103

    # Create memory areas
    size = 200
    db_data = bytearray(size)
    mk_data = bytearray(100)
    pe_data = bytearray(100)
    pa_data = bytearray(100)

    # Initialize DB with test pattern
    for i in range(size):
        db_data[i] = i % 256

    db_array = (c_char * size).from_buffer(db_data)
    mk_array = (c_char * 100).from_buffer(mk_data)
    pe_array = (c_char * 100).from_buffer(pe_data)
    pa_array = (c_char * 100).from_buffer(pa_data)

    server.register_area(SrvArea.DB, 1, db_array)
    # Register MK/PE/PA at index 0 (used by client convenience methods)
    server.register_area(SrvArea.MK, 0, mk_array)
    server.register_area(SrvArea.PE, 0, pe_array)
    server.register_area(SrvArea.PA, 0, pa_array)

    server.start(port)
    time.sleep(0.2)

    client = Client()
    try:
        client.connect("127.0.0.1", 0, 1, port)
        yield server, client
    finally:
        try:
            client.disconnect()
        except Exception:
            pass
        try:
            server.stop()
            server.destroy()
        except Exception:
            pass
        time.sleep(0.1)


class TestReadWriteRoundtrip:
    """Verify data written can be read back correctly."""

    def test_db_write_read_roundtrip(self, server_client_pair: Tuple[Server, Client]) -> None:
        """Write data to DB and read it back."""
        server, client = server_client_pair
        test_data = bytearray([0xDE, 0xAD, 0xBE, 0xEF])

        client.db_write(1, 50, test_data)
        result = client.db_read(1, 50, 4)

        assert result == test_data

    def test_write_area_read_area_roundtrip(self, server_client_pair: Tuple[Server, Client]) -> None:
        """Write via write_area and read via read_area."""
        server, client = server_client_pair
        test_data = bytearray([0x11, 0x22, 0x33, 0x44, 0x55])

        client.write_area(Area.DB, 1, 100, test_data)
        result = client.read_area(Area.DB, 1, 100, 5)

        assert result == test_data

    def test_multiple_writes_accumulate(self, server_client_pair: Tuple[Server, Client]) -> None:
        """Multiple writes to adjacent areas preserve earlier data."""
        server, client = server_client_pair

        # Write to different offsets
        client.db_write(1, 0, bytearray([0x01, 0x02, 0x03]))
        client.db_write(1, 3, bytearray([0x04, 0x05, 0x06]))
        client.db_write(1, 6, bytearray([0x07, 0x08, 0x09]))

        # Read entire range
        result = client.db_read(1, 0, 9)

        assert result == bytearray([0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09])

    def test_overwrite_partial_data(self, server_client_pair: Tuple[Server, Client]) -> None:
        """Overwriting partial data preserves surrounding bytes."""
        server, client = server_client_pair

        # Write initial block
        client.db_write(1, 10, bytearray([0xAA, 0xBB, 0xCC, 0xDD, 0xEE]))
        # Overwrite middle bytes
        client.db_write(1, 12, bytearray([0xFF]))

        result = client.db_read(1, 10, 5)
        assert result == bytearray([0xAA, 0xBB, 0xFF, 0xDD, 0xEE])


class TestMultiAreaAccess:
    """Verify all memory areas work correctly."""

    def test_db_area_read_write(self, server_client_pair: Tuple[Server, Client]) -> None:
        """Data Block area read/write."""
        server, client = server_client_pair
        data = bytearray([0x12, 0x34])

        client.write_area(Area.DB, 1, 0, data)
        result = client.read_area(Area.DB, 1, 0, 2)
        assert result == data

    def test_mk_area_read_write(self, server_client_pair: Tuple[Server, Client]) -> None:
        """Marker area read/write."""
        server, client = server_client_pair
        data = bytearray([0x56, 0x78])

        # mb_write signature: (start, size, data)
        client.mb_write(0, len(data), data)
        result = client.mb_read(0, len(data))
        assert result == data

    def test_pe_area_read_write(self, server_client_pair: Tuple[Server, Client]) -> None:
        """Process Input area read/write."""
        server, client = server_client_pair
        data = bytearray([0x9A, 0xBC])

        # eb_write signature: (start, size, data)
        client.eb_write(0, len(data), data)
        result = client.eb_read(0, len(data))
        assert result == data

    def test_pa_area_read_write(self, server_client_pair: Tuple[Server, Client]) -> None:
        """Process Output area read/write."""
        server, client = server_client_pair
        data = bytearray([0xDE, 0xF0])

        # ab_write signature: (start, data) - no size param
        client.ab_write(0, data)
        result = client.ab_read(0, len(data))
        assert result == data


class TestDataIntegrity:
    """Verify data integrity for various patterns and sizes."""

    def test_all_byte_values(self, server_client_pair: Tuple[Server, Client]) -> None:
        """All 256 byte values transfer correctly."""
        server, client = server_client_pair
        # Write bytes 0-199 (test pattern was initialized this way)
        result = client.db_read(1, 0, 200)
        for i in range(200):
            assert result[i] == i % 256, f"Byte at offset {i} incorrect"

    def test_zero_bytes(self, server_client_pair: Tuple[Server, Client]) -> None:
        """Zero bytes transfer correctly."""
        server, client = server_client_pair
        data = bytearray([0x00, 0x00, 0x00, 0x00])

        client.db_write(1, 20, data)
        result = client.db_read(1, 20, 4)
        assert result == data

    def test_all_ones(self, server_client_pair: Tuple[Server, Client]) -> None:
        """0xFF bytes transfer correctly."""
        server, client = server_client_pair
        data = bytearray([0xFF, 0xFF, 0xFF, 0xFF])

        client.db_write(1, 30, data)
        result = client.db_read(1, 30, 4)
        assert result == data

    def test_alternating_bits(self, server_client_pair: Tuple[Server, Client]) -> None:
        """Alternating bit patterns transfer correctly."""
        server, client = server_client_pair
        data = bytearray([0xAA, 0x55, 0xAA, 0x55])

        client.db_write(1, 40, data)
        result = client.db_read(1, 40, 4)
        assert result == data


class TestConnectionBehavior:
    """Verify connection lifecycle behavior."""

    def test_disconnect_reconnect(self, server_client_pair: Tuple[Server, Client]) -> None:
        """Client can disconnect and reconnect."""
        server, client = server_client_pair

        # Write initial data
        client.db_write(1, 0, bytearray([0x42]))

        # Disconnect
        client.disconnect()
        assert client.get_connected() is False

        # Reconnect - server is on port 11103
        client.connect("127.0.0.1", 0, 1, 11103)
        assert client.get_connected() is True

        # Data should persist
        result = client.db_read(1, 0, 1)
        assert result[0] == 0x42

    def test_get_connected_reflects_state(self, server_client_pair: Tuple[Server, Client]) -> None:
        """get_connected() accurately reflects connection state."""
        server, client = server_client_pair

        assert client.get_connected() is True
        client.disconnect()
        assert client.get_connected() is False


class TestPDUBehavior:
    """Verify PDU-related behavior."""

    def test_get_pdu_length(self, server_client_pair: Tuple[Server, Client]) -> None:
        """PDU length is reported correctly."""
        server, client = server_client_pair
        pdu_length = client.get_pdu_length()

        assert pdu_length > 0
        assert pdu_length >= 240  # Minimum S7 PDU size

    def test_read_within_pdu(self, server_client_pair: Tuple[Server, Client]) -> None:
        """Single read within PDU size works."""
        server, client = server_client_pair
        pdu_length = client.get_pdu_length()

        # Read should work within PDU data limits
        result = client.db_read(1, 0, min(100, pdu_length - 18))  # 18 bytes overhead
        assert len(result) == min(100, pdu_length - 18)


class TestBlockOperations:
    """Verify block operation behavior."""

    def test_list_blocks(self, server_client_pair: Tuple[Server, Client]) -> None:
        """list_blocks returns valid structure."""
        server, client = server_client_pair
        blocks = client.list_blocks()

        # Should have DB count of at least 1
        assert hasattr(blocks, "DBCount")
        assert blocks.DBCount >= 1

    def test_db_get(self, server_client_pair: Tuple[Server, Client]) -> None:
        """db_get returns block data."""
        server, client = server_client_pair
        result = client.db_get(1)

        assert isinstance(result, bytearray)
        assert len(result) > 0

    def test_db_fill(self, server_client_pair: Tuple[Server, Client]) -> None:
        """db_fill fills entire DB with value."""
        server, client = server_client_pair

        # Fill DB with 0x42
        client.db_fill(1, 0x42)

        # Read back and verify
        result = client.db_read(1, 0, 10)
        for byte in result:
            assert byte == 0x42

    def test_delete_returns_zero(self, server_client_pair: Tuple[Server, Client]) -> None:
        """delete() returns success code."""
        server, client = server_client_pair
        result = client.delete(Block.DB, 1)
        assert result == 0

    def test_full_upload_returns_tuple(self, server_client_pair: Tuple[Server, Client]) -> None:
        """full_upload() returns (bytearray, int) tuple."""
        server, client = server_client_pair
        result = client.full_upload(Block.DB, 1)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bytearray)
        assert isinstance(result[1], int)
        assert result[1] > 0


class TestErrorBehavior:
    """Verify error handling behavior."""

    def test_error_text_returns_string(self) -> None:
        """error_text returns human-readable string."""
        client = Client()
        error_msg = client.error_text(0)

        assert isinstance(error_msg, str)

    def test_get_last_error(self, server_client_pair: Tuple[Server, Client]) -> None:
        """get_last_error returns integer."""
        server, client = server_client_pair
        error_code = client.get_last_error()

        assert isinstance(error_code, int)


class TestSystemInfo:
    """Verify system info retrieval."""

    def test_get_cpu_info(self, server_client_pair: Tuple[Server, Client]) -> None:
        """get_cpu_info returns valid structure."""
        server, client = server_client_pair
        info = client.get_cpu_info()

        assert hasattr(info, "ModuleTypeName")
        assert hasattr(info, "SerialNumber")
        assert hasattr(info, "Copyright")

    def test_get_cp_info(self, server_client_pair: Tuple[Server, Client]) -> None:
        """get_cp_info returns valid structure."""
        server, client = server_client_pair
        info = client.get_cp_info()

        assert hasattr(info, "MaxPduLength")
        assert info.MaxPduLength > 0

    def test_get_exec_time(self, server_client_pair: Tuple[Server, Client]) -> None:
        """get_exec_time returns integer."""
        server, client = server_client_pair
        exec_time = client.get_exec_time()

        assert isinstance(exec_time, int)
        assert exec_time >= 0


class TestConcurrentConnections:
    """Verify server handles multiple clients."""

    def test_two_clients_simultaneous(self) -> None:
        """Two clients can connect simultaneously."""
        server = Server()
        port = 11104

        db_data = bytearray(100)
        db_array = (c_char * 100).from_buffer(db_data)
        server.register_area(SrvArea.DB, 1, db_array)

        server.start(port)
        time.sleep(0.2)

        client1 = Client()
        client2 = Client()

        try:
            client1.connect("127.0.0.1", 0, 1, port)
            client2.connect("127.0.0.1", 0, 1, port)

            assert client1.get_connected() is True
            assert client2.get_connected() is True

            # Both can read/write
            client1.db_write(1, 0, bytearray([0x11]))
            client2.db_write(1, 1, bytearray([0x22]))

            # Both see consistent data
            result1 = client1.db_read(1, 0, 2)
            result2 = client2.db_read(1, 0, 2)

            assert result1 == result2
            assert result1 == bytearray([0x11, 0x22])

        finally:
            try:
                client1.disconnect()
            except Exception:
                pass
            try:
                client2.disconnect()
            except Exception:
                pass
            try:
                server.stop()
                server.destroy()
            except Exception:
                pass
            time.sleep(0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
