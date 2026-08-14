"""Tests for the native async client (AsyncClient).

Uses the same Server fixture as test_client.py for integration tests.
"""

import asyncio
import logging
import struct
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from snap7.async_client import AsyncClient, AsyncISOTCPConnection
from snap7.error import S7ConnectionError
from snap7.server import Server
from snap7.type import Area, Parameter, SrvArea

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


@pytest.mark.asyncio
async def test_set_session_password_requires_connection() -> None:
    """set_session_password sends a USERDATA PDU and requires a connection."""
    c = AsyncClient()
    with pytest.raises(S7ConnectionError, match="Not connected"):
        await c.set_session_password("secret")


@pytest.mark.asyncio
async def test_clear_session_password_requires_connection() -> None:
    """clear_session_password sends a USERDATA PDU and requires a connection."""
    c = AsyncClient()
    with pytest.raises(S7ConnectionError, match="Not connected"):
        await c.clear_session_password()


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


@pytest.mark.asyncio
async def test_invalid_negotiated_pdu_length_uses_safe_default() -> None:
    client = AsyncClient()
    response = {"parameters": {"pdu_length": 0}}

    with patch.object(client, "_send_receive", new=AsyncMock(return_value=response)):
        await client._setup_communication()

    assert client.pdu_length == 240
    assert client._max_read_size() == 222
    assert client._max_write_size() == 205


@pytest.mark.parametrize(
    ("parameter", "expected"),
    [
        (struct.pack(">BBB", 0xC0, 1, 0x0A), 1024),
        (struct.pack(">BBH", 0xC0, 2, 2048), 2048),
    ],
)
def test_async_cotp_accepts_valid_pdu_sizes(parameter: bytes, expected: int) -> None:
    connection = AsyncISOTCPConnection("127.0.0.1")
    base = struct.pack(">BBHHB", 6 + len(parameter), 0xD0, 0x0001, 0x0001, 0x00)

    connection._parse_cotp_cc(base + parameter)

    assert connection.pdu_size == expected


@pytest.mark.parametrize(
    "parameter",
    [
        struct.pack(">BBB", 0xC0, 1, 0x00),
        struct.pack(">BBB", 0xC0, 1, 0xFF),
        struct.pack(">BBH", 0xC0, 2, 127),
        struct.pack(">BBH", 0xC0, 2, 8193),
    ],
)
def test_async_cotp_ignores_invalid_pdu_sizes(parameter: bytes) -> None:
    connection = AsyncISOTCPConnection("127.0.0.1")
    base = struct.pack(">BBHHB", 6 + len(parameter), 0xD0, 0x0001, 0x0001, 0x00)

    connection._parse_cotp_cc(base + parameter)

    assert connection.pdu_size == 240


# -------------------------------------------------------------------
# Block info / CPU info (against server)
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_blocks(client: AsyncClient) -> None:
    """AsyncClient.list_blocks must decode the same block-count struct as sync."""
    result = await client.list_blocks()
    # Server registers DB 0, 1 and various other areas; block counts match
    # what the sync test_client.test_list_blocks_server test observes.
    assert isinstance(result.DBCount, int)
    assert result.DBCount >= 2


@pytest.mark.asyncio
async def test_get_cpu_state(client: AsyncClient) -> None:
    state = await client.get_cpu_state()
    assert isinstance(state, str)


@pytest.mark.asyncio
async def test_get_cpu_info(client: AsyncClient) -> None:
    """AsyncClient.get_cpu_info must parse the same SZL offsets as sync client.

    Regression guard for discussion #700 where the async implementation
    kept the pre-#692 offsets (starting at 0) and returned empty fields
    against a real PLC and the fixed server emulator.
    """
    info = await client.get_cpu_info()
    expected = (
        ("ModuleTypeName", "CPU 315-2 PN/DP"),
        ("SerialNumber", "S C-C2UR28922012"),
        ("ASName", "SNAP7-SERVER"),
        ("Copyright", "Original Siemens Equipment"),
        ("ModuleName", "CPU 315-2 PN/DP"),
    )
    for field_name, value in expected:
        assert getattr(info, field_name).decode("utf-8") == value


@pytest.mark.asyncio
async def test_get_cp_info(client: AsyncClient) -> None:
    """Mirrors sync test_client.test_get_cp_info — guards SZL 0x0131 decoding."""
    result = await client.get_cp_info()
    assert result.MaxPduLength == 480
    assert result.MaxConnections == 32
    assert result.MaxMpiRate == 12
    assert result.MaxBusRate == 12


@pytest.mark.asyncio
async def test_get_order_code(client: AsyncClient) -> None:
    """Mirrors sync test — guards SZL 0x0011 decoding."""
    result = await client.get_order_code()
    assert b"6ES7" in result.OrderCode


@pytest.mark.asyncio
async def test_get_protection(client: AsyncClient) -> None:
    """Mirrors sync test — guards SZL 0x0232 decoding."""
    result = await client.get_protection()
    assert result.sch_schal == 1
    assert result.sch_par == 0
    assert result.sch_rel == 0
    assert result.bart_sch == 0
    assert result.anl_sch == 0


@pytest.mark.asyncio
async def test_get_block_info(client: AsyncClient) -> None:
    """Mirrors sync test — guards get_block_info dict→TS7BlockInfo conversion."""
    from snap7.type import Block

    info = await client.get_block_info(Block.DB, 1)
    assert info.BlkNumber == 1


@pytest.mark.asyncio
async def test_get_pdu_length_after_connect(client: AsyncClient) -> None:
    assert client.get_pdu_length() > 0


# -------------------------------------------------------------------
# Force I/O
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_force_bit(client: AsyncClient) -> None:
    """Force a single input bit and verify it reads back correctly."""
    await client.write_area(Area.PE, 0, 0, bytearray([0x00]))
    await client.force_bit(Area.PE, 0, 3, True)
    data = await client.read_area(Area.PE, 0, 0, 1)
    assert data[0] & (1 << 3)


@pytest.mark.asyncio
async def test_cancel_force(client: AsyncClient) -> None:
    """Cancel force clears the bit in the process image."""
    await client.write_area(Area.PA, 0, 0, bytearray([0x00]))
    await client.force_bit(Area.PA, 0, 2, True)
    data = await client.read_area(Area.PA, 0, 0, 1)
    assert data[0] & (1 << 2)
    await client.cancel_force(Area.PA, 0, 2)
    data = await client.read_area(Area.PA, 0, 0, 1)
    assert not (data[0] & (1 << 2))


@pytest.mark.asyncio
async def test_force_bit_invalid_area(client: AsyncClient) -> None:
    """Force should reject non-I/O areas."""
    with pytest.raises(ValueError):
        await client.force_bit(Area.MK, 0, 0, True)


@pytest.mark.asyncio
async def test_read_force_table(client: AsyncClient) -> None:
    """read_force_table should return a list (possibly empty)."""
    result = await client.read_force_table()
    assert isinstance(result, list)
