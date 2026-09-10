"""Batched symbolic read response accounting."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from s7commplus.async_client import S7CommPlusAsyncClient
from s7commplus.client import S7CommPlusClient
from s7commplus.codec import encode_pvalue_blob
from s7commplus.protocol import ProtocolVersion


ITEMS = [(0x8A0E0001, [1, 4]), (0x8A0E0001, [5, 4])]


@pytest.mark.parametrize("async_client", [False, True])
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (
            b"\x00\x02" + encode_pvalue_blob(b"second") + b"\x01" + encode_pvalue_blob(b"first") + b"\x00\x00",
            [b"first", b"second"],
        ),
        (b"\x00\x01" + encode_pvalue_blob(b"first") + b"\x00\x02\x01\x00", [b"first", None]),
    ],
)
async def test_symbolic_multi_preserves_item_order_and_errors(
    async_client: bool, response: bytes, expected: list[bytes | None]
) -> None:
    if async_client:
        client = S7CommPlusAsyncClient()
        client._send_request = AsyncMock(return_value=response)
        assert await client.read_symbolic_multi(ITEMS) == expected
        client._send_request.assert_awaited_once()
    else:
        sync = S7CommPlusClient()
        sync._connection = MagicMock(protocol_version=ProtocolVersion.V2)
        sync._connection.send_request.return_value = response
        assert sync.read_symbolic_multi(ITEMS) == expected
        sync._connection.send_request.assert_called_once()


@pytest.mark.parametrize("async_client", [False, True])
@pytest.mark.parametrize(
    "response",
    [
        b"\x00\x02" + encode_pvalue_blob(b"second") + b"\x00\x00",  # unanswered first item
        b"\x00\x03" + encode_pvalue_blob(b"extra") + b"\x00\x00",  # out of range
        b"\x00\x01" + encode_pvalue_blob(b"first") + b"\x01" + encode_pvalue_blob(b"duplicate") + b"\x00\x00",
        b"\x01",  # whole-request rejection
    ],
)
async def test_symbolic_multi_rejects_incomplete_or_invalid_replies(async_client: bool, response: bytes) -> None:
    with pytest.raises(RuntimeError, match="Symbolic multi-read failed"):
        if async_client:
            client = S7CommPlusAsyncClient()
            client._send_request = AsyncMock(return_value=response)
            await client.read_symbolic_multi(ITEMS)
        else:
            sync = S7CommPlusClient()
            sync._connection = MagicMock(protocol_version=ProtocolVersion.V2)
            sync._connection.send_request.return_value = response
            sync.read_symbolic_multi(ITEMS)
