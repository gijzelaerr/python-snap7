"""Typed, name-based S7CommPlus tag catalog tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from snap7.error import S7ConnectionError
from s7commplus.async_client import S7CommPlusAsyncClient
from s7commplus.catalog import ArrayDimension, SymbolCatalog, SymbolicTag
from s7commplus.client import S7CommPlusClient, _build_multi_symbolic_write_payload
from s7commplus.protocol import DataType, ProtocolVersion
from s7commplus.typeinfo import Softdatatype
from s7commplus.vlq import encode_uint32_vlq, encode_uint64_vlq


def _browse_item(
    name: str = "DB1.Motor.Speed",
    *,
    crc: int = 0x12345678,
    access_sequence: str = "8A0E0001.A.2",
    data_type: str = "REAL",
) -> dict[str, object]:
    return {
        "name": name,
        "access_sequence": access_sequence,
        "data_type": data_type,
        "symbol_crc": crc,
        "array_dimensions": ((1, 4),),
        "string_length": 0,
        "opt_address": 12,
        "opt_bitoffset": 0,
        "nonopt_address": 20,
        "nonopt_bitoffset": 0,
    }


class TestSymbolCatalog:
    def test_descriptor_preserves_address_type_crc_and_array_metadata(self) -> None:
        catalog = SymbolCatalog.from_browse([_browse_item()])

        tag = catalog.resolve("DB1.Motor.Speed")

        assert tag.access_area == 0x8A0E0001
        assert tag.lids == (0xA, 0x2)
        assert tag.softdatatype is Softdatatype.REAL
        assert tag.datatype is DataType.REAL
        assert tag.symbol_crc == 0x12345678
        assert tag.array_dimensions == (ArrayDimension(1, 4),)
        assert tag.opt_address == 12
        assert tag.nonopt_address == 20

    def test_unknown_name_has_clear_error(self) -> None:
        with pytest.raises(KeyError, match="Unknown symbolic tag"):
            SymbolCatalog([]).resolve("missing")

    def test_duplicate_name_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="Duplicate symbolic tag"):
            SymbolCatalog.from_browse([_browse_item(), _browse_item()])


class TestNamedTagIO:
    def test_resolve_catalog_is_cached(self) -> None:
        client = S7CommPlusClient()
        client.browse = MagicMock(return_value=[_browse_item()])  # type: ignore[method-assign]

        assert client.resolve_tag("DB1.Motor.Speed") is client.resolve_tag("DB1.Motor.Speed")
        client.browse.assert_called_once()

    def test_read_tags_returns_per_item_results(self) -> None:
        client = S7CommPlusClient()
        client._symbol_catalog = SymbolCatalog.from_browse(
            [_browse_item("DB1.Good", crc=0), _browse_item("DB1.Bad", crc=0, access_sequence="8A0E0001.B")]
        )
        client.read_symbolic_multi = MagicMock(return_value=[b"\x00\x01", None])  # type: ignore[method-assign]

        results = client.read_tags(["DB1.Good", "DB1.Bad"])

        assert results[0].success and results[0].value == b"\x00\x01"
        assert not results[1].success and results[1].error is not None

    def test_failed_read_refreshes_and_retries_only_when_crc_changed(self) -> None:
        client = S7CommPlusClient()
        client.browse = MagicMock(  # type: ignore[method-assign]
            side_effect=[[_browse_item(crc=1, access_sequence="8A0E0001.A")], [_browse_item(crc=2, access_sequence="8A0E0001.B")]]
        )
        client.read_symbolic_multi = MagicMock(side_effect=[[None], [b"\x40\x49\x0f\xdb"]])  # type: ignore[method-assign]

        assert client.read_tag("DB1.Motor.Speed") == b"\x40\x49\x0f\xdb"
        assert client.read_symbolic_multi.call_args_list[0].args[0] == [(0x8A0E0001, [0xA], 1)]
        assert client.read_symbolic_multi.call_args_list[1].args[0] == [(0x8A0E0001, [0xB], 2)]

    def test_failed_read_is_not_retried_when_crc_is_unchanged(self) -> None:
        client = S7CommPlusClient()
        client.browse = MagicMock(return_value=[_browse_item(crc=1)])  # type: ignore[method-assign]
        client.read_symbolic_multi = MagicMock(return_value=[None])  # type: ignore[method-assign]

        with pytest.raises(RuntimeError, match="Symbolic read failed"):
            client.read_tag("DB1.Motor.Speed")
        client.read_symbolic_multi.assert_called_once()

    def test_write_uses_resolved_datatype_and_reports_item_errors(self) -> None:
        client = S7CommPlusClient()
        client._connection = MagicMock(protocol_version=ProtocolVersion.V2)
        client._symbol_catalog = SymbolCatalog.from_browse(
            [_browse_item("DB1.Real"), _browse_item("DB1.Count", data_type="DINT", access_sequence="8A0E0001.B")]
        )
        client._connection.send_request.return_value = (
            encode_uint64_vlq(0) + encode_uint32_vlq(2) + encode_uint64_vlq(0xDEAD) + encode_uint32_vlq(0)
        )

        with patch("s7commplus.client._build_multi_symbolic_write_payload", wraps=_build_multi_symbolic_write_payload) as build:
            results = client.write_tags({"DB1.Real": b"\x3f\x80\x00\x00", "DB1.Count": b"\x00\x00\x00\x01"})

        items = build.call_args.args[0]
        assert [item[4] for item in items] == [DataType.REAL, DataType.DINT]
        assert results[0].success
        assert not results[1].success

    def test_write_is_never_retried_after_ambiguous_transport_failure(self) -> None:
        client = S7CommPlusClient()
        client._connection = MagicMock(protocol_version=ProtocolVersion.V2)
        client._symbol_catalog = SymbolCatalog.from_browse([_browse_item()])
        client._connection.send_request.side_effect = S7ConnectionError("connection lost")

        with pytest.raises(S7ConnectionError, match="connection lost"):
            client.write_tag("DB1.Motor.Speed", b"\x3f\x80\x00\x00")
        client._connection.send_request.assert_called_once()

    def test_global_plc_write_error_is_reported_for_every_item(self) -> None:
        client = S7CommPlusClient()
        client._connection = MagicMock(protocol_version=ProtocolVersion.V2)
        client._symbol_catalog = SymbolCatalog.from_browse(
            [_browse_item("DB1.Real"), _browse_item("DB1.Count", data_type="DINT", access_sequence="8A0E0001.B")]
        )
        client._connection.send_request.return_value = encode_uint64_vlq(0x05A9)

        results = client.write_tags({"DB1.Real": b"\x3f\x80\x00\x00", "DB1.Count": b"\x00\x00\x00\x01"})

        assert len(results) == 2
        assert all(not result.success and result.error is not None for result in results)


@pytest.mark.asyncio
async def test_async_read_tag_refreshes_changed_crc_once() -> None:
    client = S7CommPlusAsyncClient()
    client.browse = AsyncMock(  # type: ignore[method-assign]
        side_effect=[[_browse_item(crc=1)], [_browse_item(crc=2, access_sequence="8A0E0001.B")]]
    )
    client.read_symbolic_multi = AsyncMock(side_effect=[[None], [b"ok"]])  # type: ignore[method-assign]

    assert await client.read_tag("DB1.Motor.Speed") == b"ok"
    assert client.read_symbolic_multi.await_count == 2


def test_public_descriptor_can_be_constructed_directly() -> None:
    tag = SymbolicTag(
        name="DB1.Value",
        access_area=0x8A0E0001,
        lids=(1,),
        softdatatype=Softdatatype.INT,
        datatype=DataType.INT,
    )
    assert tag.name == "DB1.Value"
