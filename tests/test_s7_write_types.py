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
    if operation == "symbolic":
        # write_symbolic targets optimized/type-checked DBs -- the PLC validates
        # the declared scalar type, so the wire tag must match `datatype`.
        assert payload[offset : offset + 2 + len(wire_value)] == bytes((0, datatype)) + wire_value
    else:
        # write_area/db_write_multi use raw byte-offset ("classic blob") access,
        # which real S7-1500 hardware only accepts as a BLOB-tagged PValue --
        # confirmed: an explicit scalar-typed write was hard-rejected by the PLC
        # while the identical write encoded as BLOB succeeded and read back
        # correctly. `datatype` is still validated for size/type but not sent.
        expected = bytes((0, DataType.BLOB, 0x00, len(data))) + data
        assert payload[offset : offset + len(expected)] == expected


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


def test_substreamed_area_write_encodes_as_blob() -> None:
    """Substreamed raw area writes are also wire-untyped -- the classic-blob
    addressing mode only accepts BLOB PValues (see
    _build_substreamed_write_payload)."""
    client = S7CommPlusClient()
    connection = MagicMock()
    connection.requires_substreamed = True
    connection.session_id = 0x70000001
    client._connection = connection
    data = struct.pack(">I", 300)
    client.write_area(82, 0, data, datatype=DataType.UDINT)
    function, payload = connection.send_request.call_args.args
    assert function == FunctionCode.SET_VAR_SUBSTREAMED
    assert payload.endswith(bytes((0, DataType.BLOB, 0x00, len(data))) + data + bytes((1, 0, 0, 0, 0)))
