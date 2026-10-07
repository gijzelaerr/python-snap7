"""Tests for typed DB access and tag helpers on the AsyncClient."""

import logging
import struct
from collections.abc import AsyncGenerator, Generator
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from snap7.async_client import AsyncClient
from snap7.error import S7Error
from snap7.server import Server
from snap7.tags import Tag
from snap7.type import Area, S7SZL, SrvArea

logging.basicConfig(level=logging.WARNING)

ip = "127.0.0.1"
tcpport = 1107  # Distinct from the other test modules
rack = 1
slot = 1


@pytest.fixture(scope="module")
def server() -> Generator[Server]:
    srv = Server()
    srv.register_area(SrvArea.DB, 1, bytearray(600))
    srv.register_area(SrvArea.MK, 0, bytearray(100))
    srv.start(tcp_port=tcpport)
    yield srv
    srv.stop()
    srv.destroy()


@pytest_asyncio.fixture
async def client(server: Server) -> AsyncGenerator[AsyncClient]:
    c = AsyncClient()
    await c.connect(ip, rack, slot, tcpport)
    yield c
    await c.disconnect()


@pytest.mark.parametrize(
    "name, value",
    [
        ("byte", 200),
        ("int", -12345),
        ("uint", 54321),
        ("word", 0xBEEF),
        ("dint", -123456789),
        ("udint", 3000000000),
        ("dword", 0xDEADBEEF),
        ("real", 1.5),
        ("lreal", 3.141592653589793),
    ],
)
async def test_typed_round_trip(client: AsyncClient, name: str, value: Any) -> None:
    await getattr(client, f"db_write_{name}")(1, 10, value)
    assert await getattr(client, f"db_read_{name}")(1, 10) == value


async def test_bool_preserves_other_bits(client: AsyncClient) -> None:
    await client.db_write(1, 30, bytearray([0b10000001]))
    await client.db_write_bool(1, 30, 3, True)
    assert await client.db_read_bool(1, 30, 3) is True
    assert await client.db_read_bool(1, 30, 0) is True
    assert await client.db_read_bool(1, 30, 7) is True
    await client.db_write_bool(1, 30, 3, False)
    assert await client.db_read_bool(1, 30, 3) is False
    assert await client.db_read_byte(1, 30) == 0b10000001


async def test_string_round_trip(client: AsyncClient) -> None:
    await client.db_write_string(1, 40, "hello", max_length=20)
    assert await client.db_read_string(1, 40) == "hello"


async def test_wstring_round_trip(client: AsyncClient) -> None:
    await client.db_write_wstring(1, 100, "héllo", max_length=10)
    assert await client.db_read_wstring(1, 100) == "héllo"


async def test_array_round_trip(client: AsyncClient) -> None:
    await client.db_write_array(1, 200, [1.0, 2.5, -3.0], ">f")
    assert await client.db_read_array(1, 200, 3, ">f") == [1.0, 2.5, -3.0]
    await client.db_write_array(1, 220, [1, -2, 3], ">h")
    assert await client.db_read_array(1, 220, 3, ">h") == [1, -2, 3]


async def test_tag_round_trip(client: AsyncClient) -> None:
    await client.write_tag("DB1:300:INT", 4242)
    assert await client.read_tag("DB1:300:INT") == 4242
    await client.write_tag(Tag(Area.DB, 1, 304, "REAL"), 2.5)
    assert await client.read_tag("DB1.DBD304:REAL") == 2.5
    await client.write_tag("M10:DINT", 77)
    assert await client.read_tag("M10:DINT") == 77


async def test_tag_bool_preserves_other_bits(client: AsyncClient) -> None:
    await client.db_write(1, 320, bytearray([0b00000100]))
    await client.write_tag("DB1.DBX320.1:BOOL", True)
    assert await client.read_tag("DB1.DBX320.1:BOOL") is True
    assert await client.read_tag("DB1.DBX320.2:BOOL") is True


async def test_read_tags_preserves_order(client: AsyncClient) -> None:
    await client.write_tag("DB1:400:INT", 11)
    await client.write_tag("DB1:402:DINT", 22)
    await client.write_tag("DB1:406:REAL", 3.5)
    assert await client.read_tags(["DB1:406:REAL", "DB1:400:INT", "DB1:402:DINT"]) == [3.5, 11, 22]


async def test_symbolic_tag_not_supported(client: AsyncClient) -> None:
    tag = Tag(Area.DB, 1, 0, "INT", access_sequence=[1, 2])
    with pytest.raises(NotImplementedError):
        await client.read_tag(tag)
    with pytest.raises(NotImplementedError):
        await client.write_tag(tag, 1)


async def test_is_alive(server: Server) -> None:
    c = AsyncClient()
    assert not c.is_alive
    await c.connect(ip, rack, slot, tcpport)
    assert c.is_alive
    await c.disconnect()
    assert not c.is_alive


async def test_connect_routed() -> None:
    srv = Server()
    srv.register_area(SrvArea.DB, 1, bytearray(100))
    srv.start(tcp_port=11103)
    try:
        c = AsyncClient()
        result = await c.connect_routed(ip, 0, 2, subnet=0x0001, dest_rack=0, dest_slot=3, port=11103)
        assert result is c
        assert c.is_alive
        assert c.connection is not None
        assert c.connection._routing_tsap == 0x0100 | (0 << 5) | 3
        assert len(await c.db_read(1, 0, 10)) == 10
        await c.disconnect()
    finally:
        srv.stop()
        srv.destroy()


async def test_connect_routed_failure_raises(server: Server) -> None:
    c = AsyncClient()
    with pytest.raises(S7Error):
        await c.connect_routed(ip, 0, 2, subnet=1, dest_rack=0, dest_slot=3, port=11104, timeout=1.0)
    assert not c.is_alive


async def test_read_diagnostic_buffer(client: AsyncClient) -> None:
    entry = struct.pack(">H", 0x4302) + bytes([0x26, 0x10, 0x07, 0x12, 0x30, 0x45, 0x00, 0x00]) + bytes(10)
    szl = S7SZL()
    szl.Header.LengthDR = len(entry) * 2
    for i, b in enumerate(entry * 2):
        szl.Data[i] = b
    with patch.object(client, "read_szl", AsyncMock(return_value=szl)):
        entries = await client.read_diagnostic_buffer()
    assert [e["event_id"] for e in entries] == [0x4302, 0x4302]
    assert entries[0]["timestamp"] == datetime(2026, 10, 7, 12, 30, 45)
    assert entries[0]["info"] == bytes(10).hex()
