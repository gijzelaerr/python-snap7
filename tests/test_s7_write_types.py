"""Check scalar write types at the public API's outgoing request boundary."""

import struct
from unittest.mock import AsyncMock, MagicMock

import pytest

from s7commplus.async_client import S7CommPlusAsyncClient
from s7commplus.client import S7CommPlusClient
from s7commplus.protocol import DataType, FunctionCode, ProtocolVersion
from s7commplus.vlq import decode_uint32_vlq


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("operation", ["symbolic", "area", "multi"])
@pytest.mark.parametrize(
    ("datatype", "data", "wire_value"),
    [
        (DataType.INT, struct.pack(">h", 77), b"\x00\x4d"),
        (DataType.WORD, struct.pack(">H", 512), b"\x02\x00"),
        (DataType.DINT, struct.pack(">i", -5), b"\x7b"),
        (DataType.UDINT, struct.pack(">I", 300), b"\x82\x2c"),
        (DataType.REAL, struct.pack(">f", 2.0), b"\x40\x00\x00\x00"),
    ],
)
async def test_scalar_write_wire_type(
    asynchronous: bool, operation: str, datatype: DataType, data: bytes, wire_value: bytes
) -> None:
    if asynchronous:
        client = S7CommPlusAsyncClient()
        send = AsyncMock(return_value=b"\x00\x00")
        client._send_request = send
        if operation == "symbolic":
            await client.write_symbolic(0x8A0E0001, [15], data, datatype=datatype)
        elif operation == "area":
            await client.write_area(82, 0, data, datatype=datatype)
        else:
            await client.db_write_multi([(1, 0, data, datatype)])
    else:
        sync_client = S7CommPlusClient()
        connection = MagicMock()
        connection.requires_substreamed = False
        connection.protocol_version = ProtocolVersion.V2
        send = connection.send_request
        send.return_value = b"\x00\x00"
        sync_client._connection = connection
        if operation == "symbolic":
            sync_client.write_symbolic(0x8A0E0001, [15], data, datatype=datatype)
        elif operation == "area":
            sync_client.write_area(82, 0, data, datatype=datatype)
        else:
            sync_client.db_write_multi([(1, 0, data, datatype)])

    function, payload = send.call_args.args
    assert function == FunctionCode.SET_MULTI_VARIABLES
    count, consumed = decode_uint32_vlq(payload, 4)
    assert count == 1
    offset = 4 + consumed
    fields, consumed = decode_uint32_vlq(payload, offset)
    offset += consumed
    for _ in range(fields):
        _, consumed = decode_uint32_vlq(payload, offset)
        offset += consumed
    index, consumed = decode_uint32_vlq(payload, offset)
    assert index == 1
    offset += consumed
    assert payload[offset : offset + 2 + len(wire_value)] == bytes((0, datatype)) + wire_value


@pytest.mark.parametrize("substreamed", [False, True])
def test_missing_multi_write_type_rejected_before_any_send(substreamed: bool) -> None:
    client = S7CommPlusClient()
    connection = MagicMock()
    connection.requires_substreamed = substreamed
    client._connection = connection
    with pytest.raises(ValueError, match="require.*datatype"):
        client.db_write_multi([(1, 0, b"\x00\x4d", DataType.INT), (1, 2, b"\x00\x01")])  # type: ignore[list-item]
    connection.send_request.assert_not_called()


async def test_async_missing_multi_write_type_rejected_before_send() -> None:
    client = S7CommPlusAsyncClient()
    send = AsyncMock()
    client._send_request = send
    with pytest.raises(ValueError, match="require.*datatype"):
        await client.db_write_multi([(1, 0, b"\x00\x4d")])  # type: ignore[list-item]
    send.assert_not_called()


@pytest.mark.parametrize("substreamed", [False, True])
def test_invalid_scalar_width_rejected_before_any_send(substreamed: bool) -> None:
    client = S7CommPlusClient()
    connection = MagicMock()
    connection.requires_substreamed = substreamed
    client._connection = connection
    with pytest.raises(ValueError):
        client.db_write_multi([(1, 0, b"\x00\x4d", DataType.INT), (1, 2, b"\x01", DataType.INT)])
    connection.send_request.assert_not_called()


def test_substreamed_area_write_keeps_explicit_type() -> None:
    client = S7CommPlusClient()
    connection = MagicMock()
    connection.requires_substreamed = True
    connection.session_id = 0x70000001
    client._connection = connection
    client.write_area(82, 0, struct.pack(">I", 300), datatype=DataType.UDINT)
    function, payload = connection.send_request.call_args.args
    assert function == FunctionCode.SET_VAR_SUBSTREAMED
    assert payload.endswith(bytes((0, DataType.UDINT, 0x82, 0x2C, 1, 0, 0, 0, 0)))
