"""Unit tests for S7CommPlus client payload builders, connection parsing, and error paths."""

import struct
import pytest

from snap7.s7commplus.client import (
    S7CommPlusClient,
    _build_read_payload,
    _parse_read_response,
    _build_write_payload,
    _parse_write_response,
)
from snap7.s7commplus.codec import encode_pvalue_blob
from snap7.s7commplus.connection import S7CommPlusConnection, _element_size
from snap7.s7commplus.protocol import DataType, ElementID, ObjectId
from snap7.s7commplus.vlq import (
    encode_uint32_vlq,
    encode_uint64_vlq,
    encode_int32_vlq,
    decode_uint32_vlq,
)


# -- Payload builder / parser tests --


class TestBuildReadPayload:
    def test_single_item(self) -> None:
        payload = _build_read_payload([(1, 0, 4)])
        assert isinstance(payload, bytes)
        assert len(payload) > 0

    def test_multi_item(self) -> None:
        payload = _build_read_payload([(1, 0, 4), (2, 10, 8)])
        assert isinstance(payload, bytes)
        # Multi-item payload should be larger than single
        single = _build_read_payload([(1, 0, 4)])
        assert len(payload) > len(single)


class TestParseReadResponse:
    @staticmethod
    def _build_response(
        return_value: int = 0,
        items: list[bytes] | None = None,
        errors: list[tuple[int, int]] | None = None,
    ) -> bytes:
        """Build a synthetic GetMultiVariables response."""
        result = bytearray()
        # ReturnValue (UInt64 VLQ)
        result += encode_uint64_vlq(return_value)

        # Value list
        if items:
            for i, item_data in enumerate(items, 1):
                result += encode_uint32_vlq(i)  # ItemNumber
                result += encode_pvalue_blob(item_data)  # PValue
        result += encode_uint32_vlq(0)  # Terminator

        # Error list
        if errors:
            for err_item_nr, err_value in errors:
                result += encode_uint32_vlq(err_item_nr)
                result += encode_uint64_vlq(err_value)
        result += encode_uint32_vlq(0)  # Terminator

        return bytes(result)

    def test_single_item_success(self) -> None:
        data = bytes([1, 2, 3, 4])
        response = self._build_response(items=[data])
        results = _parse_read_response(response)
        assert len(results) == 1
        assert results[0] == data

    def test_multi_item_success(self) -> None:
        data1 = bytes([0x0A, 0x0B])
        data2 = bytes([0x0C, 0x0D, 0x0E])
        response = self._build_response(items=[data1, data2])
        results = _parse_read_response(response)
        assert len(results) == 2
        assert results[0] == data1
        assert results[1] == data2

    def test_error_return_value(self) -> None:
        response = self._build_response(return_value=0x05A9)
        results = _parse_read_response(response)
        assert results == []

    def test_empty_response(self) -> None:
        response = self._build_response()
        results = _parse_read_response(response)
        assert results == []

    def test_with_error_items(self) -> None:
        data1 = bytes([1, 2, 3, 4])
        response = self._build_response(items=[data1], errors=[(2, 0xDEAD)])
        results = _parse_read_response(response)
        assert len(results) == 2
        assert results[0] == data1
        assert results[1] is None  # Error item


class TestParseWriteResponse:
    @staticmethod
    def _build_response(return_value: int = 0, errors: list[tuple[int, int]] | None = None) -> bytes:
        result = bytearray()
        result += encode_uint64_vlq(return_value)
        if errors:
            for err_item_nr, err_value in errors:
                result += encode_uint32_vlq(err_item_nr)
                result += encode_uint64_vlq(err_value)
        result += encode_uint32_vlq(0)  # Terminator
        return bytes(result)

    def test_success(self) -> None:
        response = self._build_response(return_value=0)
        _parse_write_response(response)  # Should not raise

    def test_error_return_value(self) -> None:
        response = self._build_response(return_value=0x05A9)
        with pytest.raises(RuntimeError, match="Write failed"):
            _parse_write_response(response)

    def test_error_items(self) -> None:
        response = self._build_response(return_value=0, errors=[(1, 0xDEAD)])
        with pytest.raises(RuntimeError, match="Write failed"):
            _parse_write_response(response)


class TestBuildWritePayload:
    def test_single_item(self) -> None:
        payload = _build_write_payload([(1, 0, bytes([1, 2, 3, 4]))])
        assert isinstance(payload, bytes)
        assert len(payload) > 0

    def test_data_appears_in_payload(self) -> None:
        data = bytes([0xDE, 0xAD, 0xBE, 0xEF])
        payload = _build_write_payload([(1, 0, data)])
        # The raw data should appear in the payload (inside the BLOB PValue)
        assert data in payload


# -- Client/server payload agreement --


class TestPayloadAgreement:
    """Verify client payloads can be parsed by the server's request parser."""

    def test_read_payload_roundtrip(self) -> None:
        """Build a read payload, then manually verify it has expected structure."""
        payload = _build_read_payload([(1, 0, 4)])
        offset = 0

        # LinkId (4 bytes fixed)
        link_id = struct.unpack_from(">I", payload, offset)[0]
        offset += 4
        assert link_id == 0

        # Item count (VLQ)
        item_count, consumed = decode_uint32_vlq(payload, offset)
        offset += consumed
        assert item_count == 1

        # Total field count (VLQ)
        total_fields, consumed = decode_uint32_vlq(payload, offset)
        offset += consumed
        assert total_fields == 6  # 4 base + 2 LIDs

    def test_write_read_consistency(self) -> None:
        """Build write and read payloads for same address, verify both compile."""
        read_payload = _build_read_payload([(1, 0, 4)])
        write_payload = _build_write_payload([(1, 0, bytes([1, 2, 3, 4]))])
        assert isinstance(read_payload, bytes)
        assert isinstance(write_payload, bytes)


# -- Connection unit tests --


class TestConnectionElementSize:
    def test_single_byte(self) -> None:
        for dt in (DataType.BOOL, DataType.USINT, DataType.BYTE, DataType.SINT):
            assert _element_size(dt) == 1

    def test_two_byte(self) -> None:
        for dt in (DataType.UINT, DataType.WORD, DataType.INT):
            assert _element_size(dt) == 2

    def test_four_byte(self) -> None:
        for dt in (DataType.REAL, DataType.RID):
            assert _element_size(dt) == 4

    def test_eight_byte(self) -> None:
        for dt in (DataType.LREAL, DataType.TIMESTAMP):
            assert _element_size(dt) == 8

    def test_variable_length(self) -> None:
        for dt in (DataType.UDINT, DataType.BLOB, DataType.WSTRING, DataType.STRUCT):
            assert _element_size(dt) == 0


class TestSkipTypedValue:
    """Test S7CommPlusConnection._skip_typed_value with constructed byte buffers."""

    @pytest.fixture()
    def conn(self) -> S7CommPlusConnection:
        return S7CommPlusConnection("127.0.0.1")

    def test_null(self, conn: S7CommPlusConnection) -> None:
        assert conn._skip_typed_value(b"", 0, DataType.NULL, 0x00) == 0

    def test_bool(self, conn: S7CommPlusConnection) -> None:
        data = bytes([0x01])
        assert conn._skip_typed_value(data, 0, DataType.BOOL, 0x00) == 1

    def test_usint(self, conn: S7CommPlusConnection) -> None:
        data = bytes([42])
        assert conn._skip_typed_value(data, 0, DataType.USINT, 0x00) == 1

    def test_byte(self, conn: S7CommPlusConnection) -> None:
        data = bytes([0xAB])
        assert conn._skip_typed_value(data, 0, DataType.BYTE, 0x00) == 1

    def test_sint(self, conn: S7CommPlusConnection) -> None:
        data = bytes([0xD6])
        assert conn._skip_typed_value(data, 0, DataType.SINT, 0x00) == 1

    def test_uint(self, conn: S7CommPlusConnection) -> None:
        data = struct.pack(">H", 1000)
        assert conn._skip_typed_value(data, 0, DataType.UINT, 0x00) == 2

    def test_word(self, conn: S7CommPlusConnection) -> None:
        data = struct.pack(">H", 0xBEEF)
        assert conn._skip_typed_value(data, 0, DataType.WORD, 0x00) == 2

    def test_int(self, conn: S7CommPlusConnection) -> None:
        data = struct.pack(">h", -1000)
        assert conn._skip_typed_value(data, 0, DataType.INT, 0x00) == 2

    def test_udint(self, conn: S7CommPlusConnection) -> None:
        vlq = encode_uint32_vlq(100000)
        new_offset = conn._skip_typed_value(vlq, 0, DataType.UDINT, 0x00)
        assert new_offset == len(vlq)

    def test_dword(self, conn: S7CommPlusConnection) -> None:
        vlq = encode_uint32_vlq(0xDEADBEEF)
        new_offset = conn._skip_typed_value(vlq, 0, DataType.DWORD, 0x00)
        assert new_offset == len(vlq)

    def test_aid(self, conn: S7CommPlusConnection) -> None:
        vlq = encode_uint32_vlq(306)
        new_offset = conn._skip_typed_value(vlq, 0, DataType.AID, 0x00)
        assert new_offset == len(vlq)

    def test_dint(self, conn: S7CommPlusConnection) -> None:
        vlq = encode_int32_vlq(-100000)
        new_offset = conn._skip_typed_value(vlq, 0, DataType.DINT, 0x00)
        assert new_offset == len(vlq)

    def test_ulint(self, conn: S7CommPlusConnection) -> None:
        vlq = encode_uint64_vlq(2**40)
        new_offset = conn._skip_typed_value(vlq, 0, DataType.ULINT, 0x00)
        assert new_offset == len(vlq)

    def test_lword(self, conn: S7CommPlusConnection) -> None:
        vlq = encode_uint64_vlq(0xCAFE)
        new_offset = conn._skip_typed_value(vlq, 0, DataType.LWORD, 0x00)
        assert new_offset == len(vlq)

    def test_lint(self, conn: S7CommPlusConnection) -> None:
        from snap7.s7commplus.vlq import encode_int64_vlq

        vlq = encode_int64_vlq(-(2**40))
        new_offset = conn._skip_typed_value(vlq, 0, DataType.LINT, 0x00)
        assert new_offset == len(vlq)

    def test_real(self, conn: S7CommPlusConnection) -> None:
        data = struct.pack(">f", 3.14)
        assert conn._skip_typed_value(data, 0, DataType.REAL, 0x00) == 4

    def test_lreal(self, conn: S7CommPlusConnection) -> None:
        data = struct.pack(">d", 2.718)
        assert conn._skip_typed_value(data, 0, DataType.LREAL, 0x00) == 8

    def test_timestamp(self, conn: S7CommPlusConnection) -> None:
        data = struct.pack(">Q", 0x0001020304050607)
        assert conn._skip_typed_value(data, 0, DataType.TIMESTAMP, 0x00) == 8

    def test_timespan(self, conn: S7CommPlusConnection) -> None:
        from snap7.s7commplus.vlq import encode_int64_vlq

        vlq = encode_int64_vlq(5000)
        # TIMESPAN uses uint64_vlq for skipping in _skip_typed_value
        new_offset = conn._skip_typed_value(vlq, 0, DataType.TIMESPAN, 0x00)
        assert new_offset == len(vlq)

    def test_rid(self, conn: S7CommPlusConnection) -> None:
        data = struct.pack(">I", 0x12345678)
        assert conn._skip_typed_value(data, 0, DataType.RID, 0x00) == 4

    def test_blob(self, conn: S7CommPlusConnection) -> None:
        blob_data = bytes([1, 2, 3, 4])
        vlq_len = encode_uint32_vlq(len(blob_data))
        data = vlq_len + blob_data
        new_offset = conn._skip_typed_value(data, 0, DataType.BLOB, 0x00)
        assert new_offset == len(data)

    def test_wstring(self, conn: S7CommPlusConnection) -> None:
        text = "hello".encode("utf-8")
        vlq_len = encode_uint32_vlq(len(text))
        data = vlq_len + text
        new_offset = conn._skip_typed_value(data, 0, DataType.WSTRING, 0x00)
        assert new_offset == len(data)

    def test_struct(self, conn: S7CommPlusConnection) -> None:
        # Struct with 2 USINT sub-values
        vlq_count = encode_uint32_vlq(2)
        sub1 = bytes([0x00, DataType.USINT, 0x0A])  # flags + type + value
        sub2 = bytes([0x00, DataType.USINT, 0x14])
        data = vlq_count + sub1 + sub2
        new_offset = conn._skip_typed_value(data, 0, DataType.STRUCT, 0x00)
        assert new_offset == len(data)

    def test_unknown_type(self, conn: S7CommPlusConnection) -> None:
        # Unknown type should return same offset (can't skip)
        assert conn._skip_typed_value(bytes([0xFF]), 0, 0xFF, 0x00) == 0

    # -- Array tests --

    def test_array_fixed_size(self, conn: S7CommPlusConnection) -> None:
        count_vlq = encode_uint32_vlq(3)
        elements = bytes([10, 20, 30])
        data = count_vlq + elements
        new_offset = conn._skip_typed_value(data, 0, DataType.USINT, 0x10)
        assert new_offset == len(data)

    def test_array_variable_length(self, conn: S7CommPlusConnection) -> None:
        count_vlq = encode_uint32_vlq(2)
        elem1 = encode_uint32_vlq(100)
        elem2 = encode_uint32_vlq(200)
        data = count_vlq + elem1 + elem2
        new_offset = conn._skip_typed_value(data, 0, DataType.UDINT, 0x10)
        assert new_offset == len(data)

    def test_array_empty_data(self, conn: S7CommPlusConnection) -> None:
        # Edge case: array flag but no data
        assert conn._skip_typed_value(b"", 0, DataType.USINT, 0x10) == 0


class TestParseCreateObjectResponse:
    """Test _parse_create_object_response with constructed payloads."""

    def _build_create_response_with_session_version(self, version: int, datatype: int = DataType.UDINT) -> bytes:
        """Build a minimal CreateObject response containing ServerSessionVersion."""
        payload = bytearray()
        # Attribute tag
        payload += bytes([ElementID.ATTRIBUTE])
        # Attribute ID = ServerSessionVersion (306)
        payload += encode_uint32_vlq(ObjectId.SERVER_SESSION_VERSION)
        # Typed value: flags + datatype + VLQ value
        payload += bytes([0x00, datatype])
        payload += encode_uint32_vlq(version)
        return bytes(payload)

    def test_parse_udint_version(self) -> None:
        conn = S7CommPlusConnection("127.0.0.1")
        payload = self._build_create_response_with_session_version(3, DataType.UDINT)
        conn._parse_create_object_response(payload)
        assert conn._server_session_version == 3

    def test_parse_dword_version(self) -> None:
        conn = S7CommPlusConnection("127.0.0.1")
        payload = self._build_create_response_with_session_version(2, DataType.DWORD)
        conn._parse_create_object_response(payload)
        assert conn._server_session_version == 2

    def test_version_not_found(self) -> None:
        conn = S7CommPlusConnection("127.0.0.1")
        # Build payload with a different attribute, not ServerSessionVersion
        payload = bytearray()
        payload += bytes([ElementID.ATTRIBUTE])
        payload += encode_uint32_vlq(999)  # Some other attribute ID
        payload += bytes([0x00, DataType.USINT, 42])
        conn._parse_create_object_response(bytes(payload))
        assert conn._server_session_version is None

    def test_with_preceding_attributes(self) -> None:
        conn = S7CommPlusConnection("127.0.0.1")
        payload = bytearray()
        # First attribute: some random one with a UINT value
        payload += bytes([ElementID.ATTRIBUTE])
        payload += encode_uint32_vlq(100)  # Random attribute ID
        payload += bytes([0x00, DataType.UINT])
        payload += struct.pack(">H", 0x1234)
        # Second attribute: ServerSessionVersion
        payload += bytes([ElementID.ATTRIBUTE])
        payload += encode_uint32_vlq(ObjectId.SERVER_SESSION_VERSION)
        payload += bytes([0x00, DataType.UDINT])
        payload += encode_uint32_vlq(1)
        conn._parse_create_object_response(bytes(payload))
        assert conn._server_session_version == 1

    def test_with_start_of_object(self) -> None:
        conn = S7CommPlusConnection("127.0.0.1")
        payload = bytearray()
        # StartOfObject tag (needs RelationId + ClassId + ClassFlags + AttributeId)
        payload += bytes([ElementID.START_OF_OBJECT])
        payload += struct.pack(">I", 0)  # RelationId (4 bytes)
        payload += encode_uint32_vlq(100)  # ClassId
        payload += encode_uint32_vlq(0)  # ClassFlags
        payload += encode_uint32_vlq(0)  # AttributeId
        # TerminatingObject
        payload += bytes([ElementID.TERMINATING_OBJECT])
        # Now the attribute we want
        payload += bytes([ElementID.ATTRIBUTE])
        payload += encode_uint32_vlq(ObjectId.SERVER_SESSION_VERSION)
        payload += bytes([0x00, DataType.UDINT])
        payload += encode_uint32_vlq(3)
        conn._parse_create_object_response(bytes(payload))
        assert conn._server_session_version == 3


# -- Client error path tests --


class TestClientErrorPaths:
    def test_properties_not_connected(self) -> None:
        client = S7CommPlusClient()
        assert client.connected is False
        assert client.protocol_version == 0
        assert client.session_id == 0
        assert client.using_legacy_fallback is False

    def test_db_read_not_connected(self) -> None:
        client = S7CommPlusClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            client.db_read(1, 0, 4)

    def test_db_write_not_connected(self) -> None:
        client = S7CommPlusClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            client.db_write(1, 0, bytes([1, 2, 3, 4]))

    def test_db_read_multi_not_connected(self) -> None:
        client = S7CommPlusClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            client.db_read_multi([(1, 0, 4)])

    def test_explore_not_connected(self) -> None:
        client = S7CommPlusClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            client.explore()

    def test_context_manager_not_connected(self) -> None:
        """Test that context manager works without connection (disconnect is a no-op)."""
        with S7CommPlusClient() as client:
            assert client.connected is False
        # Should not raise
