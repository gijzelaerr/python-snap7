"""Integration tests for S7CommPlus server, client, and async client."""

import struct
import time
import pytest
import asyncio

from snap7.s7commplus.server import S7CommPlusServer, CPUState, DataBlock
from snap7.s7commplus.client import S7CommPlusClient
from snap7.s7commplus.async_client import S7CommPlusAsyncClient
from snap7.s7commplus.protocol import ProtocolVersion

# Use a high port to avoid conflicts
TEST_PORT = 11120


@pytest.fixture()
def server():
    """Create and start an S7CommPlus server with test data blocks."""
    srv = S7CommPlusServer()

    # Register DB1 with named variables
    srv.register_db(
        1,
        {
            "temperature": ("Real", 0),
            "pressure": ("Real", 4),
            "running": ("Bool", 8),
            "count": ("DInt", 10),
            "name": ("Int", 14),
        },
    )

    # Register DB2 with raw data
    srv.register_raw_db(2, bytearray(256))

    # Pre-populate some values in DB1
    db1 = srv.get_db(1)
    assert db1 is not None
    struct.pack_into(">f", db1.data, 0, 23.5)  # temperature
    struct.pack_into(">f", db1.data, 4, 1.013)  # pressure
    db1.data[8] = 1  # running = True
    struct.pack_into(">i", db1.data, 10, 42)  # count

    srv.start(port=TEST_PORT)
    time.sleep(0.1)  # Let server start

    yield srv

    srv.stop()


class TestServer:
    """Test the server emulator itself."""

    def test_register_db(self) -> None:
        srv = S7CommPlusServer()
        db = srv.register_db(1, {"temp": ("Real", 0)})
        assert db.number == 1
        assert "temp" in db.variables
        assert db.variables["temp"].byte_offset == 0

    def test_register_raw_db(self) -> None:
        srv = S7CommPlusServer()
        data = bytearray(b"\x01\x02\x03\x04")
        db = srv.register_raw_db(10, data)
        assert db.read(0, 4) == b"\x01\x02\x03\x04"

    def test_cpu_state(self) -> None:
        srv = S7CommPlusServer()
        assert srv.cpu_state == CPUState.RUN
        srv.cpu_state = CPUState.STOP
        assert srv.cpu_state == CPUState.STOP

    def test_data_block_read_write(self) -> None:
        db = DataBlock(1, 100)
        db.write(0, b"\x01\x02\x03\x04")
        assert db.read(0, 4) == b"\x01\x02\x03\x04"

    def test_data_block_named_variable(self) -> None:
        db = DataBlock(1, 100)
        db.add_variable("temp", "Real", 0)
        db.write(0, struct.pack(">f", 42.0))
        wire_type, raw = db.read_variable("temp")
        value = struct.unpack(">f", raw)[0]
        assert abs(value - 42.0) < 0.001

    def test_data_block_read_past_end(self) -> None:
        db = DataBlock(1, 4)
        db.write(0, b"\xff\xff\xff\xff")
        # Read past end should pad with zeros
        data = db.read(2, 4)
        assert data == b"\xff\xff\x00\x00"

    def test_unknown_variable_type(self) -> None:
        db = DataBlock(1, 100)
        with pytest.raises(ValueError, match="Unknown type name"):
            db.add_variable("bad", "NonExistentType", 0)


class TestClientServerIntegration:
    """Test client against the server emulator."""

    def test_connect_disconnect(self, server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=TEST_PORT)
        assert client.connected
        assert client.session_id != 0
        assert client.protocol_version == ProtocolVersion.V1
        client.disconnect()
        assert not client.connected

    def test_context_manager(self, server: S7CommPlusServer) -> None:
        with S7CommPlusClient() as client:
            client.connect("127.0.0.1", port=TEST_PORT)
            assert client.connected
        assert not client.connected

    def test_read_real(self, server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=TEST_PORT)
        try:
            data = client.db_read(1, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 23.5) < 0.001
        finally:
            client.disconnect()

    def test_read_multiple_values(self, server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=TEST_PORT)
        try:
            # Read temperature and pressure
            data = client.db_read(1, 0, 8)
            temp = struct.unpack_from(">f", data, 0)[0]
            pressure = struct.unpack_from(">f", data, 4)[0]
            assert abs(temp - 23.5) < 0.001
            assert abs(pressure - 1.013) < 0.001
        finally:
            client.disconnect()

    def test_write_and_read_back(self, server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=TEST_PORT)
        try:
            # Write a new temperature
            client.db_write(1, 0, struct.pack(">f", 99.9))

            # Read it back
            data = client.db_read(1, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 99.9) < 0.1
        finally:
            client.disconnect()

    def test_write_dint(self, server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=TEST_PORT)
        try:
            # Write count
            client.db_write(1, 10, struct.pack(">i", 12345))

            # Read it back
            data = client.db_read(1, 10, 4)
            value = struct.unpack(">i", data)[0]
            assert value == 12345
        finally:
            client.disconnect()

    def test_read_db2_raw(self, server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=TEST_PORT)
        try:
            # DB2 should be all zeros
            data = client.db_read(2, 0, 10)
            assert data == b"\x00" * 10
        finally:
            client.disconnect()

    def test_multi_read(self, server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=TEST_PORT)
        try:
            results = client.db_read_multi(
                [
                    (1, 0, 4),  # temperature from DB1
                    (1, 4, 4),  # pressure from DB1
                    (2, 0, 4),  # zeros from DB2
                ]
            )
            assert len(results) == 3
            temp = struct.unpack(">f", results[0])[0]
            assert abs(temp - 23.5) < 0.001
            assert results[2] == b"\x00\x00\x00\x00"
        finally:
            client.disconnect()

    def test_explore(self, server: S7CommPlusServer) -> None:
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=TEST_PORT)
        try:
            response = client.explore()
            # Response should contain data about registered DBs
            assert len(response) > 0
        finally:
            client.disconnect()

    def test_server_data_persists_across_clients(self, server: S7CommPlusServer) -> None:
        # Client 1 writes
        c1 = S7CommPlusClient()
        c1.connect("127.0.0.1", port=TEST_PORT)
        c1.db_write(2, 0, b"\xde\xad\xbe\xef")
        c1.disconnect()

        # Client 2 reads
        c2 = S7CommPlusClient()
        c2.connect("127.0.0.1", port=TEST_PORT)
        data = c2.db_read(2, 0, 4)
        c2.disconnect()

        assert data == b"\xde\xad\xbe\xef"

    def test_multiple_concurrent_clients(self, server: S7CommPlusServer) -> None:
        clients = []
        for _ in range(3):
            c = S7CommPlusClient()
            c.connect("127.0.0.1", port=TEST_PORT)
            clients.append(c)

        # All should have different session IDs
        session_ids = {c.session_id for c in clients}
        assert len(session_ids) == 3

        for c in clients:
            c.disconnect()


@pytest.mark.asyncio
class TestAsyncClientServerIntegration:
    """Test async client against the server emulator."""

    async def test_connect_disconnect(self, server: S7CommPlusServer) -> None:
        client = S7CommPlusAsyncClient()
        await client.connect("127.0.0.1", port=TEST_PORT)
        assert client.connected
        assert client.session_id != 0
        await client.disconnect()
        assert not client.connected

    async def test_async_context_manager(self, server: S7CommPlusServer) -> None:
        async with S7CommPlusAsyncClient() as client:
            await client.connect("127.0.0.1", port=TEST_PORT)
            assert client.connected
        assert not client.connected

    async def test_read_real(self, server: S7CommPlusServer) -> None:
        async with S7CommPlusAsyncClient() as client:
            await client.connect("127.0.0.1", port=TEST_PORT)
            data = await client.db_read(1, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 23.5) < 0.001

    async def test_write_and_read_back(self, server: S7CommPlusServer) -> None:
        async with S7CommPlusAsyncClient() as client:
            await client.connect("127.0.0.1", port=TEST_PORT)
            await client.db_write(1, 0, struct.pack(">f", 77.7))
            data = await client.db_read(1, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 77.7) < 0.1

    async def test_multi_read(self, server: S7CommPlusServer) -> None:
        async with S7CommPlusAsyncClient() as client:
            await client.connect("127.0.0.1", port=TEST_PORT)
            results = await client.db_read_multi(
                [
                    (1, 0, 4),
                    (1, 10, 4),
                ]
            )
            assert len(results) == 2
            temp = struct.unpack(">f", results[0])[0]
            assert abs(temp - 23.5) < 0.1  # May be modified by earlier test

    async def test_explore(self, server: S7CommPlusServer) -> None:
        async with S7CommPlusAsyncClient() as client:
            await client.connect("127.0.0.1", port=TEST_PORT)
            response = await client.explore()
            assert len(response) > 0

    async def test_concurrent_reads(self, server: S7CommPlusServer) -> None:
        """Test that asyncio.Lock prevents interleaved requests."""
        async with S7CommPlusAsyncClient() as client:
            await client.connect("127.0.0.1", port=TEST_PORT)

            async def read_temp() -> float:
                data = await client.db_read(1, 0, 4)
                return struct.unpack(">f", data)[0]

            results = await asyncio.gather(read_temp(), read_temp(), read_temp())
            assert len(results) == 3
            for r in results:
                assert isinstance(r, float)
