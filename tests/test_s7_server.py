"""Integration tests for S7CommPlus server, client, and async client."""

import struct
import time
from collections.abc import Generator

import pytest
import asyncio

from s7._s7commplus_server import S7CommPlusServer, CPUState, DataBlock
from s7._s7commplus_client import S7CommPlusClient
from s7._s7commplus_async_client import S7CommPlusAsyncClient
from s7.protocol import DataType, ElementID, Ids, LegitimationId, ObjectId, ProtocolVersion
from s7.vlq import encode_uint32_vlq

# Use a high port to avoid conflicts
TEST_PORT = 11120

# SessionKey handshake tests use a separate port
SESSION_KEY_PORT = 11121

# A known S7-1200 public key fingerprint from the bundled key store
TEST_FINGERPRINT = "01:BD426B091F08731A"

# Fixed 20-byte challenge for deterministic tests
TEST_CHALLENGE = bytes(range(20))


@pytest.fixture()
def server() -> Generator[S7CommPlusServer, None, None]:
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
                return float(struct.unpack(">f", data)[0])

            results = await asyncio.gather(read_temp(), read_temp(), read_temp())
            assert len(results) == 3
            for r in results:
                assert isinstance(r, float)


class TestSessionKeyServer:
    """Test the server's SessionKey handshake emulation."""

    def test_session_key_server_construction(self) -> None:
        srv = S7CommPlusServer(
            public_key_fingerprint=TEST_FINGERPRINT,
            session_challenge=TEST_CHALLENGE,
        )
        assert srv._public_key_fingerprint == TEST_FINGERPRINT
        assert srv._session_challenge == TEST_CHALLENGE

    def test_create_object_response_contains_fingerprint_and_challenge(self) -> None:
        """Verify the CreateObject response includes attributes 233 and 303."""
        srv = S7CommPlusServer(
            public_key_fingerprint=TEST_FINGERPRINT,
            session_challenge=TEST_CHALLENGE,
        )
        response = srv._handle_create_object(seq_num=1, request_data=b"")

        # Attribute 233 (fingerprint): 0xA3 + VLQ(233) + 0x00 + 0x15(WSTRING) + VLQ(len) + utf-16-be
        attr_233_marker = bytes([ElementID.ATTRIBUTE]) + encode_uint32_vlq(Ids.OBJECT_VARIABLE_TYPE_NAME)
        assert attr_233_marker in response, "Attribute 233 not found"
        fp_bytes = TEST_FINGERPRINT.encode("utf-16-be")
        assert fp_bytes in response, "Fingerprint WString content not found"

        # Attribute 303 (challenge): 0xA3 + VLQ(303) + 0x10(array flag) + 0x02(USINT)
        attr_303_marker = bytes([ElementID.ATTRIBUTE]) + encode_uint32_vlq(LegitimationId.SERVER_SESSION_REQUEST)
        assert attr_303_marker in response, "Attribute 303 not found"
        assert TEST_CHALLENGE in response, "Session challenge bytes not found"

        # ServerSessionVersion (306) as Struct (type 0x17).
        # Note: attribute 0x0132 appears twice — once for protocol version (USINT)
        # and once for ServerSessionVersion (Struct). Find the Struct occurrence.
        attr_306_marker = bytes([ElementID.ATTRIBUTE]) + encode_uint32_vlq(ObjectId.SERVER_SESSION_VERSION)
        struct_marker = attr_306_marker + bytes([0x00, DataType.STRUCT])
        assert struct_marker in response, "ServerSessionVersion should be Struct type for SessionKey mode"

    def test_create_object_response_without_session_key(self) -> None:
        """Without fingerprint/challenge, ServerSessionVersion should be UDINT."""
        srv = S7CommPlusServer()
        response = srv._handle_create_object(seq_num=1, request_data=b"")

        # ServerSessionVersion should be UDINT (not Struct) when SessionKey is disabled.
        # Search for the specific byte pattern: attr marker + flags(0x00) + UDINT(0x04)
        attr_306_marker = bytes([ElementID.ATTRIBUTE]) + encode_uint32_vlq(ObjectId.SERVER_SESSION_VERSION)
        udint_marker = attr_306_marker + bytes([0x00, DataType.UDINT])
        struct_marker = attr_306_marker + bytes([0x00, DataType.STRUCT])
        assert udint_marker in response, "ServerSessionVersion should be UDINT without SessionKey"
        assert struct_marker not in response, "ServerSessionVersion should not be Struct without SessionKey"

        # Fingerprint attribute 233 should NOT be present
        attr_233_marker = bytes([ElementID.ATTRIBUTE]) + encode_uint32_vlq(Ids.OBJECT_VARIABLE_TYPE_NAME)
        assert attr_233_marker not in response, "Fingerprint should not be in non-SessionKey response"

    def test_get_var_substreamed_returns_challenge(self) -> None:
        """GetVarSubStreamed should return the session challenge as a BLOB."""
        srv = S7CommPlusServer(
            public_key_fingerprint=TEST_FINGERPRINT,
            session_challenge=TEST_CHALLENGE,
        )
        response = srv._handle_get_var_substreamed(seq_num=1, session_id=1, request_data=b"")
        assert len(response) > 0
        # The response should contain the challenge bytes
        assert TEST_CHALLENGE in response

    def test_set_var_substreamed_accepts_blob(self) -> None:
        """SetVarSubStreamed should accept any blob (legitimation response)."""
        srv = S7CommPlusServer(
            public_key_fingerprint=TEST_FINGERPRINT,
            session_challenge=TEST_CHALLENGE,
        )
        response = srv._handle_set_var_substreamed(seq_num=1, session_id=1, request_data=b"\x00" * 248)
        assert len(response) > 0


class TestSessionKeyIntegration:
    """Integration tests: client connecting to a SessionKey-enabled server.

    When the session_auth module is available (PR #761 branch), the full
    SessionKey handshake is exercised. When it's not available (master),
    the client falls back gracefully and the server still works for
    basic read/write after a partial session setup.
    """

    @pytest.fixture()
    def session_key_server(self) -> Generator[S7CommPlusServer, None, None]:
        srv = S7CommPlusServer(
            public_key_fingerprint=TEST_FINGERPRINT,
            session_challenge=TEST_CHALLENGE,
        )
        srv.register_db(1, {"temperature": ("Real", 0)})
        db1 = srv.get_db(1)
        assert db1 is not None
        struct.pack_into(">f", db1.data, 0, 23.5)
        srv.start(port=SESSION_KEY_PORT)
        time.sleep(0.1)
        yield srv
        srv.stop()

    def test_client_session_setup_with_struct_version(self, session_key_server: S7CommPlusServer) -> None:
        """Client parses Struct-type ServerSessionVersion and completes session setup."""
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=SESSION_KEY_PORT)
        assert client.connected
        assert client.session_id != 0
        assert client.session_setup_ok
        client.disconnect()

    def test_read_write_after_session_setup(self, session_key_server: S7CommPlusServer) -> None:
        """Read/write works after successful session setup with SessionKey server."""
        client = S7CommPlusClient()
        client.connect("127.0.0.1", port=SESSION_KEY_PORT)
        try:
            data = client.db_read(1, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 23.5) < 0.001

            client.db_write(1, 0, struct.pack(">f", 42.0))
            data = client.db_read(1, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 42.0) < 0.001
        finally:
            client.disconnect()
