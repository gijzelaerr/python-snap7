"""Tests for the native async client (AsyncClient).

Uses the same Server fixture as test_client.py for integration tests.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio

from snap7.async_client import AsyncClient
from snap7.server import Server
from snap7.type import SrvArea, Area, Parameter

logging.basicConfig(level=logging.WARNING)

ip = "127.0.0.1"
tcpport = 1103  # Different port from sync tests to avoid conflicts
db_number = 1
rack = 1
slot = 1


@pytest.fixture(scope="module")
def server() -> Generator[Server]:
    srv = Server()
    srv.register_area(SrvArea.DB, 0, bytearray(600))
    srv.register_area(SrvArea.DB, 1, bytearray(600))
    srv.register_area(SrvArea.PA, 0, bytearray(100))
    srv.register_area(SrvArea.PA, 1, bytearray(100))
    srv.register_area(SrvArea.PE, 0, bytearray(100))
    srv.register_area(SrvArea.PE, 1, bytearray(100))
    srv.register_area(SrvArea.MK, 0, bytearray(100))
    srv.register_area(SrvArea.MK, 1, bytearray(100))
    srv.register_area(SrvArea.TM, 0, bytearray(100))
    srv.register_area(SrvArea.TM, 1, bytearray(100))
    srv.register_area(SrvArea.CT, 0, bytearray(100))
    srv.register_area(SrvArea.CT, 1, bytearray(100))
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


# -------------------------------------------------------------------
# Connection
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_disconnect(server: Server) -> None:
    c = AsyncClient()
    await c.connect(ip, rack, slot, tcpport)
    assert c.get_connected()
    await c.disconnect()
    assert not c.get_connected()


@pytest.mark.asyncio
async def test_context_manager(server: Server) -> None:
    async with AsyncClient() as c:
        await c.connect(ip, rack, slot, tcpport)
        assert c.get_connected()
    assert not c.get_connected()


# -------------------------------------------------------------------
# DB read / write
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_db_read(client: AsyncClient) -> None:
    data = bytearray(40)
    await client.db_write(db_number=1, start=0, data=data)
    result = await client.db_read(db_number=1, start=0, size=40)
    assert data == result


@pytest.mark.asyncio
async def test_db_write(client: AsyncClient) -> None:
    data = bytearray(b"\x01\x02\x03\x04")
    await client.db_write(db_number=1, start=0, data=data)
    result = await client.db_read(db_number=1, start=0, size=4)
    assert result == data


@pytest.mark.asyncio
async def test_db_get(client: AsyncClient) -> None:
    result = await client.db_get(db_number=1)
    assert isinstance(result, bytearray)
    assert len(result) > 0


# -------------------------------------------------------------------
# read_area / write_area
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_write_area(client: AsyncClient) -> None:
    data = bytearray(b"\xaa\xbb\xcc\xdd")
    await client.write_area(Area.DB, 1, 0, data)
    result = await client.read_area(Area.DB, 1, 0, 4)
    assert result == data


@pytest.mark.asyncio
async def test_read_area_large(client: AsyncClient) -> None:
    """Test chunked read for data larger than PDU."""
    size = 500  # Exceeds typical single-PDU payload
    data = bytearray(range(256)) * 2  # 512 bytes of pattern
    data = data[:size]
    await client.write_area(Area.DB, 1, 0, data)
    result = await client.read_area(Area.DB, 1, 0, size)
    assert result == data


# -------------------------------------------------------------------
# Memory area convenience methods
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ab_read_write(client: AsyncClient) -> None:
    data = bytearray(b"\x01\x02\x03\x04")
    await client.ab_write(0, data)
    result = await client.ab_read(0, 4)
    assert result == data


@pytest.mark.asyncio
async def test_eb_read_write(client: AsyncClient) -> None:
    data = bytearray(b"\x05\x06\x07\x08")
    await client.eb_write(0, 4, data)
    result = await client.eb_read(0, 4)
    assert result == data


@pytest.mark.asyncio
async def test_mb_read_write(client: AsyncClient) -> None:
    data = bytearray(b"\x0a\x0b\x0c\x0d")
    await client.mb_write(0, 4, data)
    result = await client.mb_read(0, 4)
    assert result == data


# -------------------------------------------------------------------
# Concurrent safety (the key fix)
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_reads(client: AsyncClient) -> None:
    """Verify asyncio.gather with multiple reads doesn't corrupt data.

    This is the critical test — it validates that the asyncio.Lock
    serializes send/receive cycles correctly.
    """
    # Write known data
    data1 = bytearray(b"\x11\x22\x33\x44")
    data2 = bytearray(b"\xaa\xbb\xcc\xdd")
    await client.db_write(1, 0, data1)
    await client.db_write(1, 10, data2)

    # Read concurrently
    results = await asyncio.gather(
        client.db_read(1, 0, 4),
        client.db_read(1, 10, 4),
    )

    assert results[0] == data1
    assert results[1] == data2


@pytest.mark.asyncio
async def test_concurrent_read_write(client: AsyncClient) -> None:
    """Verify concurrent read and write don't interfere."""
    write_data = bytearray(b"\xff\xfe\xfd\xfc")

    async def do_write() -> None:
        await client.db_write(1, 20, write_data)

    async def do_read() -> bytearray:
        return await client.db_read(1, 0, 4)

    await asyncio.gather(do_write(), do_read())

    # Verify write went through
    result = await client.db_read(1, 20, 4)
    assert result == write_data


@pytest.mark.asyncio
async def test_many_concurrent_reads(client: AsyncClient) -> None:
    """Stress test with many concurrent reads."""
    # Write test data
    for i in range(10):
        await client.db_write(1, i * 4, bytearray([i] * 4))

    # Read all concurrently
    tasks = [client.db_read(1, i * 4, 4) for i in range(10)]
    results = await asyncio.gather(*tasks)

    for i, result in enumerate(results):
        assert result == bytearray([i] * 4), f"Mismatch at index {i}"


# -------------------------------------------------------------------
# Multi-var
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_multi_vars(client: AsyncClient) -> None:
    await client.db_write(1, 0, bytearray(b"\x01\x02\x03\x04"))
    await client.db_write(1, 4, bytearray(b"\x05\x06\x07\x08"))

    items = [
        {"area": Area.DB, "db_number": 1, "start": 0, "size": 4},
        {"area": Area.DB, "db_number": 1, "start": 4, "size": 4},
    ]
    code, results = await client.read_multi_vars(items)
    assert code == 0
    assert results[0] == bytearray(b"\x01\x02\x03\x04")
    assert results[1] == bytearray(b"\x05\x06\x07\x08")


@pytest.mark.asyncio
async def test_write_multi_vars(client: AsyncClient) -> None:
    items = [
        {"area": Area.DB, "db_number": 1, "start": 0, "data": bytearray(b"\xaa\xbb")},
        {"area": Area.DB, "db_number": 1, "start": 2, "data": bytearray(b"\xcc\xdd")},
    ]
    result = await client.write_multi_vars(items)
    assert result == 0

    data = await client.db_read(1, 0, 4)
    assert data == bytearray(b"\xaa\xbb\xcc\xdd")


# -------------------------------------------------------------------
# Synchronous helpers (no I/O)
# -------------------------------------------------------------------


def test_get_pdu_length() -> None:
    c = AsyncClient()
    assert c.get_pdu_length() == 480


def test_error_text() -> None:
    c = AsyncClient()
    assert c.error_text(0) == "OK"
    assert "Not connected" in c.error_text(0x0003)


def test_set_clear_session_password() -> None:
    c = AsyncClient()
    assert c.session_password is None
    c.set_session_password("secret")
    assert c.session_password == "secret"
    c.clear_session_password()
    assert c.session_password is None


def test_set_connection_params() -> None:
    c = AsyncClient()
    c.set_connection_params("10.0.0.1", 0x0100, 0x0200)
    assert c.host == "10.0.0.1"
    assert c.local_tsap == 0x0100
    assert c.remote_tsap == 0x0200


def test_set_connection_type() -> None:
    c = AsyncClient()
    c.set_connection_type(2)
    assert c.connection_type == 2


def test_get_set_param() -> None:
    c = AsyncClient()
    c.set_param(Parameter.PDURequest, 960)
    assert c.get_param(Parameter.PDURequest) == 960
    assert c.pdu_length == 960


def test_get_param_non_client_raises() -> None:
    c = AsyncClient()
    with pytest.raises(RuntimeError):
        c.get_param(Parameter.LocalPort)


# -------------------------------------------------------------------
# Block info / CPU info (against server)
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_blocks(client: AsyncClient) -> None:
    result = await client.list_blocks()
    assert hasattr(result, "DBCount")


@pytest.mark.asyncio
async def test_get_cpu_state(client: AsyncClient) -> None:
    state = await client.get_cpu_state()
    assert isinstance(state, str)


@pytest.mark.asyncio
async def test_get_cpu_info(client: AsyncClient) -> None:
    info = await client.get_cpu_info()
    assert hasattr(info, "ModuleTypeName")


@pytest.mark.asyncio
async def test_get_pdu_length_after_connect(client: AsyncClient) -> None:
    assert client.get_pdu_length() > 0
