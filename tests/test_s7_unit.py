"""Unit tests for S7CommPlus client payload builders, connection parsing, and error paths."""

import struct
import pytest

from s7commplus.client import (
    S7CommPlusClient,
    _build_read_payload,
    _parse_read_response,
    _build_write_payload,
    _parse_write_response,
    _build_explore_request,
    _parse_explore_datablocks,
    _build_area_read_payload,
    _build_area_write_payload,
    _build_symbolic_read_payload,
    _build_symbolic_write_payload,
)
from s7commplus.connection import S7CommPlusConnection
from s7commplus.codec import encode_object_qualifier, encode_pvalue_blob
from s7commplus.codec import _pvalue_element_size as _element_size
from s7commplus.codec import skip_typed_value, parse_server_session_version
from s7commplus.protocol import DataType, ElementID, ObjectId
from s7commplus.vlq import (
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

    def test_single_byte_scalar_bool_true(self) -> None:
        response = b"\x01\x00\x00\x04\x00\x00\x00\x00"
        results = _parse_read_response(response)
        assert results == [b"\x01"]

    def test_single_byte_scalar_bool_false(self) -> None:
        response = b"\x00\x00\x00\x04\x00\x00\x00\x00"
        results = _parse_read_response(response)
        assert results == [b"\x00"]

    def test_single_byte_scalar_usint(self) -> None:
        response = b"\x2a\x00\x00\x04\x00\x00\x00\x00"
        results = _parse_read_response(response)
        assert results == [b"\x2a"]


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


class TestSequenceNumber:
    """Verify all payload builders include a SequenceNumber after ObjectQualifier."""

    @staticmethod
    def _has_sequence_number(payload: bytes) -> bool:
        oq = encode_object_qualifier()
        idx = bytes(payload).find(oq)
        assert idx >= 0, "ObjectQualifier not found in payload"
        seq_offset = idx + len(oq)
        return payload[seq_offset : seq_offset + 1] == encode_uint32_vlq(1)

    def test_read_payload_has_sequence_number(self) -> None:
        payload = _build_read_payload([(1, 0, 4)])
        assert self._has_sequence_number(payload)

    def test_write_payload_has_sequence_number(self) -> None:
        payload = _build_write_payload([(1, 0, bytes([1, 2, 3, 4]))])
        assert self._has_sequence_number(payload)

    def test_area_read_payload_has_sequence_number(self) -> None:
        payload = _build_area_read_payload(82, 0, 4)
        assert self._has_sequence_number(payload)

    def test_area_write_payload_has_sequence_number(self) -> None:
        payload = _build_area_write_payload(82, 0, b"\x00\x00\x00\x00")
        assert self._has_sequence_number(payload)

    def test_symbolic_read_payload_has_sequence_number(self) -> None:
        payload = _build_symbolic_read_payload(0x8A0E0001, [1, 4])
        assert self._has_sequence_number(payload)

    def test_symbolic_write_payload_has_sequence_number(self) -> None:
        payload = _build_symbolic_write_payload(0x8A0E0001, [1, 4], b"\x01")
        assert self._has_sequence_number(payload)


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
    """Test codec.skip_typed_value with constructed byte buffers."""

    def test_null(self) -> None:
        assert skip_typed_value(b"", 0, DataType.NULL, 0x00) == 0

    def test_bool(self) -> None:
        data = bytes([0x01])
        assert skip_typed_value(data, 0, DataType.BOOL, 0x00) == 1

    def test_usint(self) -> None:
        data = bytes([42])
        assert skip_typed_value(data, 0, DataType.USINT, 0x00) == 1

    def test_byte(self) -> None:
        data = bytes([0xAB])
        assert skip_typed_value(data, 0, DataType.BYTE, 0x00) == 1

    def test_sint(self) -> None:
        data = bytes([0xD6])
        assert skip_typed_value(data, 0, DataType.SINT, 0x00) == 1

    def test_uint(self) -> None:
        data = struct.pack(">H", 1000)
        assert skip_typed_value(data, 0, DataType.UINT, 0x00) == 2

    def test_word(self) -> None:
        data = struct.pack(">H", 0xBEEF)
        assert skip_typed_value(data, 0, DataType.WORD, 0x00) == 2

    def test_int(self) -> None:
        data = struct.pack(">h", -1000)
        assert skip_typed_value(data, 0, DataType.INT, 0x00) == 2

    def test_udint(self) -> None:
        vlq = encode_uint32_vlq(100000)
        new_offset = skip_typed_value(vlq, 0, DataType.UDINT, 0x00)
        assert new_offset == len(vlq)

    def test_dword(self) -> None:
        # DWORD is fixed 4-byte (not VLQ).
        data = struct.pack(">I", 0xDEADBEEF)
        assert skip_typed_value(data, 0, DataType.DWORD, 0x00) == 4

    def test_aid(self) -> None:
        vlq = encode_uint32_vlq(306)
        new_offset = skip_typed_value(vlq, 0, DataType.AID, 0x00)
        assert new_offset == len(vlq)

    def test_dint(self) -> None:
        vlq = encode_int32_vlq(-100000)
        new_offset = skip_typed_value(vlq, 0, DataType.DINT, 0x00)
        assert new_offset == len(vlq)

    def test_ulint(self) -> None:
        vlq = encode_uint64_vlq(2**40)
        new_offset = skip_typed_value(vlq, 0, DataType.ULINT, 0x00)
        assert new_offset == len(vlq)

    def test_lword(self) -> None:
        # LWORD is fixed 8-byte (not VLQ).
        data = struct.pack(">Q", 0xCAFE)
        assert skip_typed_value(data, 0, DataType.LWORD, 0x00) == 8

    def test_lint(self) -> None:
        from s7commplus.vlq import encode_int64_vlq

        vlq = encode_int64_vlq(-(2**40))
        new_offset = skip_typed_value(vlq, 0, DataType.LINT, 0x00)
        assert new_offset == len(vlq)

    def test_real(self) -> None:
        data = struct.pack(">f", 3.14)
        assert skip_typed_value(data, 0, DataType.REAL, 0x00) == 4

    def test_lreal(self) -> None:
        data = struct.pack(">d", 2.718)
        assert skip_typed_value(data, 0, DataType.LREAL, 0x00) == 8

    def test_timestamp(self) -> None:
        data = struct.pack(">Q", 0x0001020304050607)
        assert skip_typed_value(data, 0, DataType.TIMESTAMP, 0x00) == 8

    def test_timespan(self) -> None:
        from s7commplus.vlq import encode_int64_vlq

        vlq = encode_int64_vlq(5000)
        # TIMESPAN uses uint64_vlq for skipping in _skip_typed_value
        new_offset = skip_typed_value(vlq, 0, DataType.TIMESPAN, 0x00)
        assert new_offset == len(vlq)

    def test_rid(self) -> None:
        data = struct.pack(">I", 0x12345678)
        assert skip_typed_value(data, 0, DataType.RID, 0x00) == 4

    def test_blob(self) -> None:
        blob_data = bytes([1, 2, 3, 4])
        vlq_len = encode_uint32_vlq(len(blob_data))
        data = vlq_len + blob_data
        new_offset = skip_typed_value(data, 0, DataType.BLOB, 0x00)
        assert new_offset == len(data)

    def test_wstring(self) -> None:
        text = "hello".encode("utf-8")
        vlq_len = encode_uint32_vlq(len(text))
        data = vlq_len + text
        new_offset = skip_typed_value(data, 0, DataType.WSTRING, 0x00)
        assert new_offset == len(data)

    def test_struct(self) -> None:
        # Normal-mode struct: UInt32 struct-id, then members [VLQ key][flags+type+value],
        # terminated by a 0x00 list-terminator byte (member keys never start with 0x00).
        struct_id = struct.pack(">I", 0x0000002A)
        member1 = encode_uint32_vlq(1) + bytes([0x00, DataType.USINT, 0x0A])
        member2 = encode_uint32_vlq(2) + bytes([0x00, DataType.USINT, 0x14])
        data = struct_id + member1 + member2 + bytes([0x00])
        new_offset = skip_typed_value(data, 0, DataType.STRUCT, 0x00)
        assert new_offset == len(data)

    def test_unknown_type(self) -> None:
        # Unknown type should return same offset (can't skip)
        assert skip_typed_value(bytes([0xFF]), 0, 0xFF, 0x00) == 0

    # -- Array tests --

    def test_array_fixed_size(self) -> None:
        count_vlq = encode_uint32_vlq(3)
        elements = bytes([10, 20, 30])
        data = count_vlq + elements
        new_offset = skip_typed_value(data, 0, DataType.USINT, 0x10)
        assert new_offset == len(data)

    def test_array_variable_length(self) -> None:
        count_vlq = encode_uint32_vlq(2)
        elem1 = encode_uint32_vlq(100)
        elem2 = encode_uint32_vlq(200)
        data = count_vlq + elem1 + elem2
        new_offset = skip_typed_value(data, 0, DataType.UDINT, 0x10)
        assert new_offset == len(data)

    def test_array_empty_data(self) -> None:
        # Edge case: array flag but no data
        assert skip_typed_value(b"", 0, DataType.USINT, 0x10) == 0


class TestParseCreateObjectResponse:
    """Test parse_server_session_version with constructed payloads.

    Returns the raw typed value (flags + datatype + value) to echo back verbatim —
    real S7-1500 PLCs send ServerSessionVersion as a Struct — or None if absent.
    """

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
        payload = self._build_create_response_with_session_version(3, DataType.UDINT)
        result = parse_server_session_version(payload)
        assert result == bytes([0x00, DataType.UDINT]) + encode_uint32_vlq(3)

    def test_parse_dword_version(self) -> None:
        payload = self._build_create_response_with_session_version(2, DataType.DWORD)
        result = parse_server_session_version(payload)
        assert result == bytes([0x00, DataType.DWORD]) + encode_uint32_vlq(2)

    def test_version_not_found(self) -> None:
        # Build payload with a different attribute, not ServerSessionVersion
        payload = bytearray()
        payload += bytes([ElementID.ATTRIBUTE])
        payload += encode_uint32_vlq(999)  # Some other attribute ID
        payload += bytes([0x00, DataType.USINT, 42])
        assert parse_server_session_version(bytes(payload)) is None

    def test_with_preceding_attributes(self) -> None:
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
        result = parse_server_session_version(bytes(payload))
        assert result == bytes([0x00, DataType.UDINT]) + encode_uint32_vlq(1)

    def test_with_start_of_object(self) -> None:
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
        result = parse_server_session_version(bytes(payload))
        assert result == bytes([0x00, DataType.UDINT]) + encode_uint32_vlq(3)


# -- Client error path tests --


class TestClientErrorPaths:
    def test_properties_not_connected(self) -> None:
        client = S7CommPlusClient()
        assert client.connected is False
        assert client.protocol_version == 0
        assert client.session_id == 0
        assert client.session_setup_ok is False

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

    def test_explore_xml_not_connected(self) -> None:
        client = S7CommPlusClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            client.explore_xml()

    def test_context_manager_not_connected(self) -> None:
        """Test that context manager works without connection (disconnect is a no-op)."""
        with S7CommPlusClient() as client:
            assert client.connected is False
        # Should not raise


class TestExploreDatablocks:
    """Test the EXPLORE(thePLCProgram) request format and DB-list parser."""

    def test_build_explore_request_format(self) -> None:
        # ExploreId as a fixed UInt32, then the marker bytes, address count + ids,
        # and a 5-byte trailer (UInt32 fill + filler byte) for the IntegrityId splice.
        from s7commplus.protocol import Ids

        payload = _build_explore_request(Ids.NATIVE_THE_PLC_PROGRAM_RID, [233, 2521])
        assert payload[:4] == struct.pack(">I", Ids.NATIVE_THE_PLC_PROGRAM_RID)
        assert payload[4] == 0  # ExploreRequestId
        assert payload[5:9] == bytes([1, 1, 0, 0])  # recursive, unknown, parents, following
        assert payload.endswith(bytes(5))  # UInt32 fill + filler byte

    def test_parse_explore_datablocks(self) -> None:
        from s7commplus.protocol import Ids

        r = bytearray()
        r += encode_uint64_vlq(0)  # ReturnValue
        # A DataBlock object: ClassId DB_CLASS_RID, RelationId in the DB area.
        r += bytes([ElementID.START_OF_OBJECT])
        r += struct.pack(">I", Ids.DB_ACCESS_AREA_BASE | 42)
        r += encode_uint32_vlq(Ids.DB_CLASS_RID)
        r += encode_uint32_vlq(0)  # ClassFlags
        r += encode_uint32_vlq(0)  # AttributeId
        r += bytes([ElementID.ATTRIBUTE])
        r += encode_uint32_vlq(Ids.OBJECT_VARIABLE_TYPE_NAME)
        name = b"DataBlock_1"  # single-byte WString content, as a real S7-1500 sends
        r += bytes([0x00, DataType.WSTRING]) + encode_uint32_vlq(len(name)) + name
        r += bytes([ElementID.TERMINATING_OBJECT])
        # A non-DB object (different ClassId) must be ignored.
        r += bytes([ElementID.START_OF_OBJECT])
        r += struct.pack(">I", 0x00000003)
        r += encode_uint32_vlq(2520)  # PLCProgram class, not a DB
        r += encode_uint32_vlq(0)
        r += encode_uint32_vlq(0)
        r += bytes([ElementID.TERMINATING_OBJECT])

        dbs = _parse_explore_datablocks(bytes(r))
        assert len(dbs) == 1
        assert dbs[0]["number"] == 42
        assert dbs[0]["rid"] == Ids.DB_ACCESS_AREA_BASE | 42
        assert dbs[0]["name"] == "DataBlock_1"


class TestReassembledPayload:
    """Test S7CommPlusConnection._recv_reassembled_payload (multi-PDU fragment reassembly)."""

    @staticmethod
    def _frag(data: bytes) -> bytes:
        return bytes([0x72, 0x02, (len(data) >> 8) & 0xFF, len(data) & 0xFF]) + data

    _TRAILER = bytes([0x72, 0x02, 0x00, 0x00])

    def _conn_yielding(self, chunks: list[bytes]) -> S7CommPlusConnection:
        conn = S7CommPlusConnection("127.0.0.1", 102)
        it = iter(chunks)

        def fake_recv() -> bytes:
            return next(it, b"")

        conn._recv_s7_data = fake_recv  # type: ignore[method-assign]
        return conn

    def test_single_fragment(self) -> None:
        conn = self._conn_yielding([self._frag(b"abc") + self._TRAILER])
        assert conn._recv_reassembled_payload() == b"abc"

    def test_multiple_fragments_split_across_reads(self) -> None:
        conn = self._conn_yielding([self._frag(b"abc"), self._frag(b"de"), self._TRAILER])
        assert conn._recv_reassembled_payload() == b"abcde"

    def test_bad_fragment_header_raises(self) -> None:
        from snap7.error import S7ConnectionError

        conn = self._conn_yielding([bytes([0x99, 0x02, 0x00, 0x01]) + b"x"])
        with pytest.raises(S7ConnectionError, match="fragment header"):
            conn._recv_reassembled_payload()

    def test_closed_connection_raises(self) -> None:
        from snap7.error import S7ConnectionError

        conn = self._conn_yielding([])  # immediate EOF
        with pytest.raises(S7ConnectionError, match="closed during"):
            conn._recv_reassembled_payload()

    def test_fragment_count_cap(self) -> None:
        from snap7.error import S7ConnectionError

        chunks = [self._frag(b"a"), self._frag(b"b"), self._frag(b"c"), self._TRAILER]
        conn = self._conn_yielding(chunks)
        conn._MAX_REASSEMBLED_FRAGMENTS = 2
        with pytest.raises(S7ConnectionError, match="exceeds limits"):
            conn._recv_reassembled_payload()
