"""Public-path regressions for Lean-derived findings #862 through #870.

Malformed vectors originate in the issue reproductions and lean-s7's pinned
30c36b91804620c88c0dde2f2f4053093828629a conformance/v1 corpus.
These are differential tests, not a formal verification of Python.
"""

import struct
from collections.abc import Callable
from ctypes import POINTER, c_uint8, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from snap7.async_client import AsyncClient, AsyncISOTCPConnection
from snap7.client import Client
from snap7.connection import ISOTCPConnection
from snap7.error import S7ConnectionError, S7ProtocolError
from snap7.type import Area, S7DataItem, WordLen


@pytest.mark.parametrize("connection_type", [ISOTCPConnection, AsyncISOTCPConnection])
@pytest.mark.parametrize("size", [0, 1, 2, 65532])
def test_tpkt_encode_rejects_out_of_bounds(
    connection_type: type[ISOTCPConnection] | type[AsyncISOTCPConnection], size: int
) -> None:
    with pytest.raises(S7ConnectionError, match="TPKT length"):
        connection_type("example.invalid")._build_tpkt(bytes(size))


@pytest.mark.parametrize("connection_type", [ISOTCPConnection, AsyncISOTCPConnection])
@pytest.mark.parametrize("size", [3, 65531])
def test_tpkt_encode_valid_boundaries(connection_type: type[ISOTCPConnection] | type[AsyncISOTCPConnection], size: int) -> None:
    payload = bytes(size)
    frame = connection_type("example.invalid")._build_tpkt(payload)
    assert int.from_bytes(frame[2:4], "big") == size + 4
    assert frame[4:] == payload


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("length", [0, 4, 5, 6])
async def test_receive_rejects_short_tpkt_before_body(asynchronous: bool, length: int) -> None:
    header = struct.pack(">BBH", 3, 0, length)
    if asynchronous:
        conn = AsyncISOTCPConnection("example.invalid")
        conn.connected = True
        receive = AsyncMock(return_value=header)
        conn._recv_exact = receive
        with pytest.raises(S7ConnectionError, match="TPKT length"):
            await conn.receive_data()
    else:
        sync_conn = ISOTCPConnection("example.invalid")
        sync_conn.connected = True
        receive = MagicMock(return_value=header)
        sync_conn._recv_exact = receive
        with pytest.raises(S7ConnectionError, match="TPKT length"):
            sync_conn.receive_data()
        sync_conn.connected = False
    receive.assert_called_once_with(4)


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("frame", ["03f08032", "01f08032", "02f08132", "02f07f32"])
async def test_cotp_rejects_invalid_header(asynchronous: bool, frame: str) -> None:
    payload = bytes.fromhex(frame)
    if asynchronous:
        conn = AsyncISOTCPConnection("example.invalid")
        conn.connected = True
        conn._recv_exact = AsyncMock(side_effect=[struct.pack(">BBH", 3, 0, len(payload) + 4), payload])
        with pytest.raises(S7ConnectionError):
            await conn.receive_data()
    else:
        with pytest.raises(S7ConnectionError):
            ISOTCPConnection("example.invalid")._parse_cotp_data(payload)


@pytest.mark.parametrize("eot", [0, 0x80])
def test_cotp_accepts_zero_tpdu_number(eot: int) -> None:
    assert ISOTCPConnection("example.invalid")._parse_cotp_data(bytes((2, 0xF0, eot, 0x32))) == b"\x32"


class Peer:
    """Replace transport only, preserving request construction and response parsing."""

    def __init__(self, reply: Callable[[bytes], tuple[bytes, bytes]]) -> None:
        self.reply = reply
        self.requests: list[bytes] = []

    def send_data(self, request: bytes) -> None:
        self.requests.append(request)

    def receive_data(self) -> bytes:
        request = self.requests[-1]
        params, data = self.reply(request)
        return b"\x32\x03\x00\x00" + request[4:6] + struct.pack(">HH", len(params), len(data)) + b"\x00\x00" + params + data

    def disconnect(self) -> None:
        pass


def client_for(peer: Peer, asynchronous: bool, pdu: int = 480) -> Client | AsyncClient:
    if asynchronous:
        client = AsyncClient()
        transport = MagicMock()
        transport.send_data = AsyncMock(side_effect=peer.send_data)
        transport.receive_data = AsyncMock(side_effect=peer.receive_data)
        client.connection = transport
        client.connected = True
        client.pdu_length = pdu
        return client
    sync_client = Client()
    sync_client.connection = peer  # type: ignore[assignment]
    sync_client.connected = True
    sync_client.pdu_length = pdu
    return sync_client


async def read(client: Client | AsyncClient, area: Area, start: int, count: int, word_len: WordLen) -> bytearray:
    if isinstance(client, Client):
        return client.read_area(area, 1, start, count, word_len)
    return await client.read_area(area, 1, start, count)


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("data", ["ff040020aa", "ff040008aa", "ff040028aabbccddee", "ff04001faabbccdd"])
async def test_short_or_wrong_size_read_is_not_success(asynchronous: bool, data: str) -> None:
    client = client_for(Peer(lambda _: (b"\x04\x01", bytes.fromhex(data))), asynchronous)
    with pytest.raises(S7ProtocolError):
        await read(client, Area.DB, 0, 4, WordLen.Byte)


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize(
    "params,data", [("0401", "ff040008aa"), ("0501", ""), ("0500", "ff"), ("0502", "ffff"), ("0501", "ffff"), ("", "")]
)
async def test_write_requires_matching_acknowledgement(asynchronous: bool, params: str, data: str) -> None:
    client = client_for(Peer(lambda _: (bytes.fromhex(params), bytes.fromhex(data))), asynchronous)
    with pytest.raises(S7ProtocolError):
        if isinstance(client, Client):
            client.db_write(1, 0, bytearray(b"\xbb"))
        else:
            await client.db_write(1, 0, bytearray(b"\xbb"))


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("params,data", [("0501", "ff"), ("0400", "ff040008aa"), ("0402", "ff040008aa")])
async def test_read_requires_matching_function_and_count(asynchronous: bool, params: str, data: str) -> None:
    client = client_for(Peer(lambda _: (bytes.fromhex(params), bytes.fromhex(data))), asynchronous)
    with pytest.raises(S7ProtocolError):
        await read(client, Area.DB, 0, 1, WordLen.Byte)


@pytest.mark.parametrize(
    "asynchronous,area,word_len,width",
    [
        (False, Area.DB, WordLen.Word, 2),
        (False, Area.DB, WordLen.DWord, 4),
        (False, Area.TM, WordLen.Timer, 2),
        (True, Area.TM, WordLen.Timer, 2),
        (True, Area.CT, WordLen.Counter, 2),
    ],
)
@pytest.mark.parametrize("pdu", [240, 480])
async def test_element_chunks_obey_budget_and_cover_exact_bytes(
    asynchronous: bool, area: Area, word_len: WordLen, width: int, pdu: int
) -> None:
    spans: list[tuple[int, int]] = []

    def reply(request: bytes) -> tuple[bytes, bytes]:
        count = int.from_bytes(request[16:18], "big")
        address = int.from_bytes(request[21:24], "big")
        start = address * width if area in (Area.TM, Area.CT) else address // 8
        spans.append((start, count))
        payload = bytes(i % 251 for i in range(start, start + count * width))
        assert 18 + len(payload) <= pdu
        return b"\x04\x01", b"\xff\x04" + struct.pack(">H", len(payload) * 8) + payload

    client = client_for(Peer(reply), asynchronous, pdu)
    result = await read(client, area, 0, 500, word_len)
    assert result == bytes(i % 251 for i in range(500 * width))
    max_count = (pdu - 18) // width
    assert spans == [(i * width, min(max_count, 500 - i)) for i in range(0, 500, max_count)]


@pytest.mark.parametrize("asynchronous", [False, True])
async def test_truncated_later_chunk_raises(asynchronous: bool) -> None:
    def reply(request: bytes) -> tuple[bytes, bytes]:
        count = int.from_bytes(request[16:18], "big")
        start = int.from_bytes(request[21:24], "big")
        payload = bytes(count if start == 0 else count - 1)
        return b"\x04\x01", b"\xff\x04" + struct.pack(">H", count * 8) + payload

    client = client_for(Peer(reply), asynchronous, 240)
    with pytest.raises(S7ProtocolError, match="truncated"):
        await read(client, Area.DB, 0, 500, WordLen.Byte)


@pytest.mark.parametrize(
    "word_len,payload",
    [
        (WordLen.Word, b"\x11\x22\x33\x44"),
        (WordLen.DWord, bytes(range(8))),
        (WordLen.Real, struct.pack(">ff", 1.0, 2.0)),
        (WordLen.Bit, b"\x01\x00"),
    ],
)
def test_ctypes_writes_keep_type_and_all_elements(word_len: WordLen, payload: bytes) -> None:
    peer = Peer(lambda _: (b"\x05\x01", b"\xff"))
    client = client_for(peer, False)
    assert isinstance(client, Client)
    buffer = (c_uint8 * len(payload))(*payload)
    item = S7DataItem()
    item.Area, item.DBNumber, item.Start = Area.DB, 1, 11
    item.WordLen, item.Amount = word_len, 2
    item.pData = cast(buffer, POINTER(c_uint8))
    assert client.write_multi_vars([item]) == 0
    assert b"".join(request[28:] for request in peer.requests) == payload
    assert all(request[15] == word_len for request in peer.requests)
    if word_len == WordLen.Bit:
        assert [int.from_bytes(r[21:24], "big") for r in peer.requests] == [11, 12]
        assert all(r[26:28] == b"\x00\x01" for r in peer.requests)
    else:
        assert peer.requests[0][16:18] == b"\x00\x02"
        expected_transport = 7 if word_len == WordLen.Real else 4
        expected_length = len(payload) if word_len == WordLen.Real else len(payload) * 8
        assert peer.requests[0][25] == expected_transport
        assert int.from_bytes(peer.requests[0][26:28], "big") == expected_length


def test_word_writes_do_not_split_elements() -> None:
    peer = Peer(lambda _: (b"\x05\x01", b"\xff"))
    client = client_for(peer, False, 240)
    assert isinstance(client, Client)
    payload = bytearray(i % 251 for i in range(1000))
    client.write_area(Area.DB, 1, 0, payload, WordLen.Word)
    assert b"".join(r[28:] for r in peer.requests) == payload
    offset = 0
    for request in peer.requests:
        assert len(request) <= 240
        assert int.from_bytes(request[21:24], "big") // 8 == offset
        assert len(request[28:]) % 2 == 0
        offset += len(request[28:])
    peer.requests.clear()
    with pytest.raises(ValueError, match="element width"):
        client.write_area(Area.DB, 1, 0, bytearray(3), WordLen.Word)
    assert not peer.requests


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("area", [Area.TM, Area.CT])
async def test_timer_counter_writes_advance_element_indices(asynchronous: bool, area: Area) -> None:
    peer = Peer(lambda _: (b"\x05\x01", b"\xff"))
    client = client_for(peer, asynchronous, 240)
    data = bytearray(i % 251 for i in range(600))
    if isinstance(client, Client):
        client.write_area(area, 0, 5, data)
    else:
        await client.write_area(area, 0, 5, data)
    assert b"".join(r[28:] for r in peer.requests) == data
    assert [int.from_bytes(r[21:24], "big") for r in peer.requests] == [5, 107, 209]
    assert all(r[25] == 9 and int.from_bytes(r[26:28], "big") == len(r[28:]) for r in peer.requests)


@pytest.mark.parametrize("asynchronous", [False, True])
async def test_pdu_too_small_for_element_fails_without_send(asynchronous: bool) -> None:
    peer = Peer(lambda _: (b"\x04\x01", b"\xff\x04\x00\x10\x00\x00"))
    client = client_for(peer, asynchronous, 19)
    with pytest.raises(S7ProtocolError, match="PDU"):
        await read(client, Area.TM, 0, 1, WordLen.Timer)
    assert not peer.requests
