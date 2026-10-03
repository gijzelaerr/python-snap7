"""Tests for the on_operation instrumentation hook (sync Client and AsyncClient)."""

import unittest
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio

from snap7.async_client import AsyncClient
from snap7.client import Client
from snap7.error import S7ConnectionError
from snap7.server import Server
from snap7.type import Area, SrvArea

ip = "127.0.0.1"
sync_tcpport = 1105
async_tcpport = 1106
rack = 1
slot = 1


def _register_areas(server: Server) -> None:
    server.register_area(SrvArea.DB, 0, bytearray(600))
    server.register_area(SrvArea.DB, 1, bytearray(600))
    server.register_area(SrvArea.CT, 0, bytearray(100))
    server.register_area(SrvArea.TM, 0, bytearray(100))


class TestClientOperationHook(unittest.TestCase):
    server: Server = None  # type: ignore

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = Server()
        _register_areas(cls.server)
        cls.server.start(tcp_port=sync_tcpport)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server:
            cls.server.stop()
            cls.server.destroy()

    def setUp(self) -> None:
        self.calls: list[tuple[str, float, bool]] = []
        self.client = Client(on_operation=lambda name, seconds, error: self.calls.append((name, seconds, error)))
        self.client.connect(ip, rack, slot, sync_tcpport)

    def tearDown(self) -> None:
        self.client.disconnect()
        self.client.destroy()

    def test_db_read_reports_read_area(self) -> None:
        self.client.db_read(db_number=1, start=0, size=4)
        names = [name for name, _, _ in self.calls]
        assert "read_area" in names

    def test_db_write_reports_write_area(self) -> None:
        self.client.db_write(db_number=1, start=0, data=bytearray(4))
        names = [name for name, _, _ in self.calls]
        assert "write_area" in names

    def test_duration_is_non_negative(self) -> None:
        self.client.db_read(db_number=1, start=0, size=4)
        assert all(seconds >= 0 for _, seconds, _ in self.calls)

    def test_error_flag_set_on_failure(self) -> None:
        self.client.disconnect()
        with self.assertRaises(S7ConnectionError):
            self.client.read_area(Area.DB, 1, 0, 4)
        assert self.calls[-1] == ("read_area", self.calls[-1][1], True)

    def test_upload_and_download_reported(self) -> None:
        self.client.download(block_num=1, data=bytearray(b"\x11\x22\x33\x44"))
        self.client.upload(1)
        names = [name for name, _, _ in self.calls]
        assert "download" in names
        assert "upload" in names

    def test_multi_vars_reported(self) -> None:
        write_items = [{"area": Area.DB, "db_number": 1, "start": 0, "data": bytearray(b"\xaa\xbb")}]
        self.client.write_multi_vars(write_items)
        read_items = [{"area": Area.DB, "db_number": 1, "start": 0, "size": 2}]
        self.client.read_multi_vars(read_items)
        names = [name for name, _, _ in self.calls]
        assert "write_multi_vars" in names
        assert "read_multi_vars" in names

    def test_nested_calls_are_not_double_reported(self) -> None:
        self.client.use_optimizer = False
        write_items = [
            {"area": Area.DB, "db_number": 1, "start": 0, "data": bytearray(b"\xaa\xbb")},
            {"area": Area.DB, "db_number": 1, "start": 2, "data": bytearray(b"\xcc\xdd")},
        ]
        self.client.write_multi_vars(write_items)
        assert self.calls == [("write_multi_vars", self.calls[0][1], False)]

        self.calls.clear()
        read_items = [
            {"area": Area.DB, "db_number": 1, "start": 0, "size": 2},
            {"area": Area.DB, "db_number": 1, "start": 2, "size": 2},
        ]
        self.client.read_multi_vars(read_items)
        assert self.calls == [("read_multi_vars", self.calls[0][1], False)]

    def test_hook_raising_does_not_break_the_call(self) -> None:
        def bad_hook(name: str, seconds: float, error: bool) -> None:
            raise RuntimeError("boom")

        client = Client(on_operation=bad_hook)
        client.connect(ip, rack, slot, sync_tcpport)
        try:
            result = client.db_read(db_number=1, start=0, size=4)
            assert result == bytearray(4)
        finally:
            client.disconnect()
            client.destroy()

    def test_no_hook_is_unaffected(self) -> None:
        client = Client()
        client.connect(ip, rack, slot, sync_tcpport)
        try:
            client.db_read(db_number=1, start=0, size=4)
        finally:
            client.disconnect()
            client.destroy()


@pytest.fixture(scope="module")
def async_server() -> Generator[Server]:
    srv = Server()
    _register_areas(srv)
    srv.start(tcp_port=async_tcpport)
    yield srv
    srv.stop()
    srv.destroy()


@pytest_asyncio.fixture
async def async_client_with_hook(async_server: Server) -> AsyncGenerator[tuple[AsyncClient, list[tuple[str, float, bool]]]]:
    calls: list[tuple[str, float, bool]] = []
    c = AsyncClient(on_operation=lambda name, seconds, error: calls.append((name, seconds, error)))
    await c.connect(ip, rack, slot, async_tcpport)
    yield c, calls
    await c.disconnect()


@pytest.mark.asyncio
async def test_async_db_read_reports_read_area(
    async_client_with_hook: tuple[AsyncClient, list[tuple[str, float, bool]]],
) -> None:
    client, calls = async_client_with_hook
    await client.db_read(db_number=1, start=0, size=4)
    names = [name for name, _, _ in calls]
    assert "read_area" in names


@pytest.mark.asyncio
async def test_async_db_write_reports_write_area(
    async_client_with_hook: tuple[AsyncClient, list[tuple[str, float, bool]]],
) -> None:
    client, calls = async_client_with_hook
    await client.db_write(db_number=1, start=0, data=bytearray(4))
    names = [name for name, _, _ in calls]
    assert "write_area" in names


@pytest.mark.asyncio
async def test_async_error_flag_set_on_failure(async_server: Server) -> None:
    calls: list[tuple[str, float, bool]] = []
    client = AsyncClient(on_operation=lambda name, seconds, error: calls.append((name, seconds, error)))
    with pytest.raises(S7ConnectionError):
        await client.read_area(Area.DB, 1, 0, 4)
    assert calls[-1] == ("read_area", calls[-1][1], True)


@pytest.mark.asyncio
async def test_async_hook_raising_does_not_break_the_call(async_server: Server) -> None:
    def bad_hook(name: str, seconds: float, error: bool) -> None:
        raise RuntimeError("boom")

    client = AsyncClient(on_operation=bad_hook)
    await client.connect(ip, rack, slot, async_tcpport)
    try:
        result = await client.db_read(db_number=1, start=0, size=4)
        assert result == bytearray(4)
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_async_nested_calls_are_not_double_reported(
    async_client_with_hook: tuple[AsyncClient, list[tuple[str, float, bool]]],
) -> None:
    client, calls = async_client_with_hook
    write_items = [
        {"area": Area.DB, "db_number": 1, "start": 0, "data": bytearray(b"\xaa\xbb")},
        {"area": Area.DB, "db_number": 1, "start": 2, "data": bytearray(b"\xcc\xdd")},
    ]
    await client.write_multi_vars(write_items)
    assert calls == [("write_multi_vars", calls[0][1], False)]
