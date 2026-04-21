"""Tests for the unified s7.Client and s7.Server using the server emulator.

No real PLC is needed — these tests exercise the full s7 package using the
built-in S7CommPlus and legacy server emulators.
"""

import struct
import time
from ctypes import c_char

import pytest

from s7 import Client, Server, Protocol
from s7._protocol import Protocol as Proto
from snap7.type import SrvArea

from .conftest import get_free_tcp_port


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

LEGACY_PORT = get_free_tcp_port()
S7PLUS_PORT = get_free_tcp_port()


@pytest.fixture(scope="module")
def unified_server():  # type: ignore[no-untyped-def]
    """Start a unified server with both legacy and S7CommPlus."""
    srv = Server()

    # Register DB1 on the legacy server
    db1_data = bytearray(100)
    struct.pack_into(">f", db1_data, 0, 23.5)
    struct.pack_into(">h", db1_data, 4, 42)
    db1_data[6] = 0xFF
    db1_array = (c_char * 100).from_buffer(db1_data)
    srv.legacy_server.register_area(SrvArea.DB, 1, db1_array)

    # Register DB2 on the legacy server (read-write)
    db2_data = bytearray(100)
    db2_array = (c_char * 100).from_buffer(db2_data)
    srv.legacy_server.register_area(SrvArea.DB, 2, db2_array)

    # Register Merker area
    mk_data = bytearray(100)
    mk_array = (c_char * 100).from_buffer(mk_data)
    srv.legacy_server.register_area(SrvArea.MK, 0, mk_array)

    # Register S7CommPlus DBs
    srv.register_raw_db(1, bytearray(db1_data))
    srv.register_raw_db(2, bytearray(100))

    srv.start(tcp_port=LEGACY_PORT, s7commplus_port=S7PLUS_PORT)
    time.sleep(0.2)

    yield srv

    srv.stop()


# ---------------------------------------------------------------------------
# Legacy protocol tests
# ---------------------------------------------------------------------------


class TestUnifiedClientLegacy:
    """Test s7.Client with legacy protocol via emulator."""

    def test_connect_legacy(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
        assert client.connected
        assert client.protocol == Protocol.LEGACY
        client.disconnect()

    def test_db_read(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
        try:
            data = client.db_read(1, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 23.5) < 0.01
        finally:
            client.disconnect()

    def test_db_write_read(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
        try:
            client.db_write(2, 0, bytearray(struct.pack(">f", 99.9)))
            data = client.db_read(2, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 99.9) < 0.01
        finally:
            client.disconnect()

    def test_db_read_multi(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
        try:
            results = client.db_read_multi([(1, 0, 4), (1, 4, 2)])
            assert len(results) == 2
            assert len(results[0]) == 4
            assert len(results[1]) == 2
        finally:
            client.disconnect()

    def test_read_tag_real(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
        try:
            value = client.read_tag("DB1.DBD0:REAL")
            assert abs(value - 23.5) < 0.01
        finally:
            client.disconnect()

    def test_read_tag_int(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
        try:
            value = client.read_tag("DB1.DBW4:INT")
            assert value == 42
        finally:
            client.disconnect()

    def test_write_tag_then_read(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
        try:
            client.write_tag("DB2.DBD0:REAL", 99.9)
            value = client.read_tag("DB2.DBD0:REAL")
            assert abs(value - 99.9) < 0.01
        finally:
            client.disconnect()

    def test_write_tag_bool(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
        try:
            client.write_tag("DB2.DBX10.3:BOOL", True)
            assert client.read_tag("DB2.DBX10.3:BOOL") is True
            client.write_tag("DB2.DBX10.3:BOOL", False)
            assert client.read_tag("DB2.DBX10.3:BOOL") is False
        finally:
            client.disconnect()

    def test_read_tags_batch(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
        try:
            values = client.read_tags(["DB1.DBD0:REAL", "DB1.DBW4:INT"])
            assert len(values) == 2
            assert abs(values[0] - 23.5) < 0.01
            assert values[1] == 42
        finally:
            client.disconnect()

    def test_read_tag_accepts_tag_instance(self, unified_server: Server) -> None:
        from s7 import Tag

        client = Client()
        client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
        try:
            tag = Tag.from_string("DB1.DBD0:REAL")
            value = client.read_tag(tag)
            assert abs(value - 23.5) < 0.01
        finally:
            client.disconnect()

    def test_list_datablocks(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
        try:
            dbs = client.list_datablocks()
            assert isinstance(dbs, list)
            # Legacy fallback returns list of dicts with "name", "number"
            numbers = [db["number"] for db in dbs]
            assert 1 in numbers
            assert 2 in numbers
        finally:
            client.disconnect()

    def test_context_manager(self, unified_server: Server) -> None:
        with Client() as client:
            client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
            assert client.connected
            data = client.db_read(1, 0, 4)
            assert len(data) == 4
        assert not client.connected

    def test_repr(self, unified_server: Server) -> None:
        client = Client()
        assert "disconnected" in repr(client)
        client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
        assert "127.0.0.1" in repr(client)
        client.disconnect()

    def test_delegated_methods(self, unified_server: Server) -> None:
        """Methods delegated via __getattr__ to legacy client."""
        client = Client()
        client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
        try:
            info = client.get_cpu_info()
            assert info is not None
            state = client.get_cpu_state()
            assert state is not None
        finally:
            client.disconnect()

    def test_read_diagnostic_buffer(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
        try:
            # Server emulator doesn't support SZL 0x00A0, so expect RuntimeError
            with pytest.raises(RuntimeError):
                client.read_diagnostic_buffer()
        finally:
            client.disconnect()

    def test_getattr_not_connected(self) -> None:
        client = Client()
        with pytest.raises(AttributeError):
            client.nonexistent_method()

    def test_getattr_private_raises(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
        try:
            with pytest.raises(AttributeError):
                client._private_method  # noqa: B018
        finally:
            client.disconnect()


# ---------------------------------------------------------------------------
# S7CommPlus protocol tests (via emulator)
# ---------------------------------------------------------------------------


class TestUnifiedClientS7CommPlus:
    """Test s7.Client with S7CommPlus protocol via emulator."""

    def test_connect_s7commplus(self, unified_server: Server) -> None:
        """Connect to the S7CommPlus emulator port directly."""
        client = Client()
        client.connect("127.0.0.1", 0, 0, S7PLUS_PORT, protocol=Protocol.S7COMMPLUS)
        assert client.connected
        assert client.protocol == Protocol.S7COMMPLUS
        client.disconnect()

    def test_s7commplus_db_read(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, S7PLUS_PORT, protocol=Protocol.S7COMMPLUS)
        try:
            data = client.db_read(1, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 23.5) < 0.01
        finally:
            client.disconnect()

    def test_s7commplus_db_write_read(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, S7PLUS_PORT, protocol=Protocol.S7COMMPLUS)
        try:
            client.db_write(2, 0, bytearray(struct.pack(">f", 77.7)))
            data = client.db_read(2, 0, 4)
            value = struct.unpack(">f", data)[0]
            assert abs(value - 77.7) < 0.01
        finally:
            client.disconnect()

    def test_s7commplus_db_read_multi(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, S7PLUS_PORT, protocol=Protocol.S7COMMPLUS)
        try:
            results = client.db_read_multi([(1, 0, 4), (1, 4, 2)])
            assert len(results) == 2
            assert len(results[0]) == 4
        finally:
            client.disconnect()

    def test_s7commplus_explore(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, S7PLUS_PORT, protocol=Protocol.S7COMMPLUS)
        try:
            result = client.explore()
            assert isinstance(result, bytes)
        finally:
            client.disconnect()

    def test_s7commplus_list_datablocks(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, S7PLUS_PORT, protocol=Protocol.S7COMMPLUS)
        try:
            dbs = client.list_datablocks()
            assert isinstance(dbs, list)
            assert len(dbs) >= 2
            numbers = [db["number"] for db in dbs]
            assert 1 in numbers
            assert 2 in numbers
            # Check names are populated
            names = [db["name"] for db in dbs]
            assert any("DB1" in n for n in names)
        finally:
            client.disconnect()

    def test_s7commplus_browse(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, S7PLUS_PORT, protocol=Protocol.S7COMMPLUS)
        try:
            variables = client.browse()
            assert isinstance(variables, list)
            # browse returns field info dicts (may be empty if server
            # doesn't support per-object explore filtering)
        finally:
            client.disconnect()

    def test_s7commplus_browse_returns_variables(self, unified_server: Server) -> None:
        """browse() returns a list of variable dicts."""
        client = Client()
        client.connect("127.0.0.1", 0, 0, S7PLUS_PORT, protocol=Protocol.S7COMMPLUS)
        try:
            variables = client.browse()
            assert isinstance(variables, list)
        finally:
            client.disconnect()

    def test_auto_protocol_with_s7commplus_server(self, unified_server: Server) -> None:
        """AUTO should detect S7CommPlus on the S7CommPlus port."""
        client = Client()
        client.connect("127.0.0.1", 0, 0, S7PLUS_PORT, protocol=Protocol.AUTO)
        assert client.connected
        assert client.protocol == Protocol.S7COMMPLUS
        client.disconnect()

    def test_force_s7commplus_fails_without_server(self) -> None:
        """Forcing S7CommPlus when no server is available raises."""
        client = Client()
        port = get_free_tcp_port()
        with pytest.raises(Exception):
            client.connect("127.0.0.1", 0, 0, port, protocol=Protocol.S7COMMPLUS)

    def test_browse_requires_s7commplus(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
        try:
            with pytest.raises(RuntimeError, match="requires S7CommPlus"):
                client.browse()
        finally:
            client.disconnect()

    def test_explore_requires_s7commplus(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
        try:
            with pytest.raises(RuntimeError, match="requires S7CommPlus"):
                client.explore()
        finally:
            client.disconnect()

    def test_subscription_requires_s7commplus(self, unified_server: Server) -> None:
        client = Client()
        client.connect("127.0.0.1", 0, 0, LEGACY_PORT, protocol=Protocol.LEGACY)
        try:
            with pytest.raises(RuntimeError, match="requires S7CommPlus"):
                client.create_subscription([(1, 0, 4)])
            with pytest.raises(RuntimeError, match="requires S7CommPlus"):
                client.delete_subscription(0x1234)
        finally:
            client.disconnect()


# ---------------------------------------------------------------------------
# Unified server tests
# ---------------------------------------------------------------------------


class TestUnifiedServer:
    """Test s7.Server features."""

    def test_server_context_manager(self) -> None:
        port = get_free_tcp_port()
        with Server() as srv:
            srv.legacy_server.register_area(SrvArea.DB, 1, (c_char * 10).from_buffer(bytearray(10)))
            srv.start(tcp_port=port)
            client = Client()
            client.connect("127.0.0.1", 0, 0, port, protocol=Protocol.LEGACY)
            data = client.db_read(1, 0, 4)
            assert len(data) == 4
            client.disconnect()

    def test_register_raw_db(self) -> None:
        srv = Server()
        db = srv.register_raw_db(5, bytearray(b"\x01\x02\x03\x04"))
        assert db.read(0, 4) == b"\x01\x02\x03\x04"

    def test_register_db(self) -> None:
        srv = Server()
        db = srv.register_db(3, {"temp": ("Real", 0), "count": ("Int", 4)})
        assert "temp" in db.variables
        assert "count" in db.variables

    def test_get_db(self) -> None:
        srv = Server()
        srv.register_raw_db(7, bytearray(10))
        db = srv.get_db(7)
        assert db is not None
        assert db.number == 7

    def test_get_db_missing(self) -> None:
        srv = Server()
        assert srv.get_db(999) is None

    def test_legacy_server_property(self) -> None:
        srv = Server()
        assert srv.legacy_server is not None

    def test_s7commplus_server_property(self) -> None:
        srv = Server()
        assert srv.s7commplus_server is not None


# ---------------------------------------------------------------------------
# Protocol enum tests
# ---------------------------------------------------------------------------


class TestProtocol:
    def test_protocol_values(self) -> None:
        assert Proto.AUTO.value == "auto"
        assert Proto.LEGACY.value == "legacy"
        assert Proto.S7COMMPLUS.value == "s7commplus"
