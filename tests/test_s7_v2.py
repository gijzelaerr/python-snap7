"""Tests for S7CommPlus V2 protocol support.

Tests IntegrityId tracking, legitimation helpers, protocol constants,
and V2 connection behavior.
"""

import hashlib
import struct
from unittest.mock import AsyncMock, MagicMock

import pytest

from s7commplus.async_client import S7CommPlusAsyncClient
from s7commplus.codec import encode_header, encode_object_qualifier
from s7commplus.connection import (
    S7CommPlusConnection,
    _build_get_var_substreamed_payload,
    _build_set_variable_payload,
    _check_set_variable_response,
    _parse_get_var_substreamed_response,
    _parse_protection_level_response,
)
from s7commplus.legitimation import (
    LegitimationState,
    _build_legitimation_payload,
    build_legacy_response,
    derive_legitimation_key,
    extract_session_version_string,
)
from s7commplus.protocol import (
    FLAGS_34_FUNCTION_CODES,
    READ_FUNCTION_CODES,
    AccessLevel,
    DataType,
    FunctionCode,
    Ids,
    LegitimationId,
    ObjectId,
    Opcode,
    ProtocolVersion,
)
from s7commplus.vlq import decode_uint32_vlq, encode_uint32_vlq
from snap7.error import S7ConnectionError


class TestReadFunctionCodes:
    """Test READ_FUNCTION_CODES classification."""

    def test_get_multi_variables_is_read(self) -> None:
        assert FunctionCode.GET_MULTI_VARIABLES in READ_FUNCTION_CODES

    def test_explore_is_read(self) -> None:
        assert FunctionCode.EXPLORE in READ_FUNCTION_CODES

    def test_get_var_substreamed_is_read(self) -> None:
        assert FunctionCode.GET_VAR_SUBSTREAMED in READ_FUNCTION_CODES

    def test_get_link_is_read(self) -> None:
        assert FunctionCode.GET_LINK in READ_FUNCTION_CODES

    def test_get_variable_is_read(self) -> None:
        assert FunctionCode.GET_VARIABLE in READ_FUNCTION_CODES

    def test_get_variables_address_is_read(self) -> None:
        assert FunctionCode.GET_VARIABLES_ADDRESS in READ_FUNCTION_CODES

    def test_set_multi_variables_is_write(self) -> None:
        assert FunctionCode.SET_MULTI_VARIABLES not in READ_FUNCTION_CODES

    def test_set_variable_is_write(self) -> None:
        assert FunctionCode.SET_VARIABLE not in READ_FUNCTION_CODES

    def test_create_object_is_write(self) -> None:
        assert FunctionCode.CREATE_OBJECT not in READ_FUNCTION_CODES

    def test_delete_object_is_write(self) -> None:
        assert FunctionCode.DELETE_OBJECT not in READ_FUNCTION_CODES


class TestFlags34FunctionCodes:
    """Test FLAGS_34_FUNCTION_CODES classification."""

    def test_delete_object_uses_flags_34(self) -> None:
        assert FunctionCode.DELETE_OBJECT in FLAGS_34_FUNCTION_CODES

    def test_explore_uses_flags_34(self) -> None:
        assert FunctionCode.EXPLORE in FLAGS_34_FUNCTION_CODES

    def test_get_multi_variables_uses_flags_34(self) -> None:
        assert FunctionCode.GET_MULTI_VARIABLES in FLAGS_34_FUNCTION_CODES

    def test_get_var_substreamed_uses_flags_34(self) -> None:
        assert FunctionCode.GET_VAR_SUBSTREAMED in FLAGS_34_FUNCTION_CODES

    def test_set_multi_variables_uses_flags_34(self) -> None:
        assert FunctionCode.SET_MULTI_VARIABLES in FLAGS_34_FUNCTION_CODES

    def test_set_variable_uses_flags_34(self) -> None:
        assert FunctionCode.SET_VARIABLE in FLAGS_34_FUNCTION_CODES

    def test_create_object_uses_flags_36(self) -> None:
        assert FunctionCode.CREATE_OBJECT not in FLAGS_34_FUNCTION_CODES

    def test_init_ssl_uses_flags_36(self) -> None:
        assert FunctionCode.INIT_SSL not in FLAGS_34_FUNCTION_CODES

    def test_get_variable_uses_flags_36(self) -> None:
        assert FunctionCode.GET_VARIABLE not in FLAGS_34_FUNCTION_CODES

    def test_get_variables_address_uses_flags_36(self) -> None:
        assert FunctionCode.GET_VARIABLES_ADDRESS not in FLAGS_34_FUNCTION_CODES

    def test_get_link_uses_flags_36(self) -> None:
        assert FunctionCode.GET_LINK not in FLAGS_34_FUNCTION_CODES


class TestLegitimationId:
    """Test legitimation ID constants."""

    def test_server_session_request(self) -> None:
        assert int(LegitimationId.SERVER_SESSION_REQUEST) == 303

    def test_server_session_response(self) -> None:
        assert int(LegitimationId.SERVER_SESSION_RESPONSE) == 304

    def test_legitimate(self) -> None:
        assert int(LegitimationId.LEGITIMATE) == 1846


class TestDeriveKey:
    """Test OMS key derivation."""

    def test_derive_returns_32_bytes(self) -> None:
        secret = b"\x00" * 32
        key = derive_legitimation_key(secret)
        assert len(key) == 32

    def test_derive_is_sha256(self) -> None:
        secret = b"test_oms_secret_material_32byte!"
        key = derive_legitimation_key(secret)
        expected = hashlib.sha256(secret).digest()
        assert key == expected

    def test_different_secrets_different_keys(self) -> None:
        key1 = derive_legitimation_key(b"\x00" * 32)
        key2 = derive_legitimation_key(b"\x01" * 32)
        assert key1 != key2


class TestLegacyResponse:
    """Test legacy legitimation (SHA-1 XOR)."""

    def test_legacy_response_length(self) -> None:
        challenge = b"\x00" * 20
        response = build_legacy_response("password", challenge)
        assert len(response) == 20

    def test_legacy_response_xor(self) -> None:
        password = "test"
        challenge = b"\xff" * 20
        response = build_legacy_response(password, challenge)
        password_hash = hashlib.sha1(password.encode("utf-8")).digest()  # noqa: S324
        # XOR with 0xFF should flip all bits
        expected = bytes(h ^ 0xFF for h in password_hash)
        assert response == expected

    def test_legacy_response_zero_challenge(self) -> None:
        password = "hello"
        challenge = b"\x00" * 20
        response = build_legacy_response(password, challenge)
        # XOR with zeros = original hash
        expected = hashlib.sha1(password.encode("utf-8")).digest()  # noqa: S324
        assert response == expected

    def test_legacy_response_matches_reference_driver(self) -> None:
        """
        SHA-1(password) XOR challenge, against a vector computed by the C# driver.
        The challenge is a genuine 20-byte challenge from an S7-1512 (FW V2.9).
        """
        challenge = bytes.fromhex("7d8f8470d20590efc1d740416b4a073296bf463b")
        response = build_legacy_response("foobar", challenge)
        assert response == bytes.fromhex("f5cc5389f613b1f2283cf9229406e5b3b32c6e43")


class TestExtractSessionVersionString:
    """Test PAOM string extraction from a raw ServerSessionVersion value."""

    @pytest.mark.parametrize(
        "paom_string",
        [
            "1;6ES7 214-1AG40-0XB0 ;V4.5",  # S7-1214C, trailing space
            "1;6ES7 510-1DJ01-0AB0;V2.9",  # S7-1510SP
            "1;6ES7 672-7FC01-0YA0;V21.9",  # S7-1507SF
        ],
    )
    def test_extracts_paom_string(self, paom_string: str) -> None:
        """Device strings from thomas-v2/S7CommPlusDriver, plain and behind a decoy key."""
        text = paom_string.encode("utf-8")
        header = bytes([0x00, DataType.STRUCT]) + struct.pack(">I", ObjectId.SERVER_SESSION_VERSION)
        # [VLQ key][flags][WString][VLQ length][utf-8 text]
        element = encode_uint32_vlq(Ids.SESSION_VERSION_SYSTEM_PAOM_STRING)
        element += bytes([0x00, DataType.WSTRING]) + encode_uint32_vlq(len(text)) + text

        assert extract_session_version_string(header + element) == paom_string

        # The needle also matches payload bytes, so the search must continue past them.
        decoy = encode_uint32_vlq(Ids.EFFECTIVE_PROTECTION_LEVEL) + bytes([0x00, DataType.UDINT])
        decoy += encode_uint32_vlq(Ids.SESSION_VERSION_SYSTEM_PAOM_STRING)
        assert extract_session_version_string(header + decoy + element) == paom_string

    def test_returns_none_when_unusable(self) -> None:
        """Value truncated past the end of the buffer, or no element 319 at all."""
        text = b"1;6ES7 510-1DJ01-0AB0;V2.9"
        value = bytes([0x00, DataType.STRUCT]) + struct.pack(">I", ObjectId.SERVER_SESSION_VERSION)
        value += encode_uint32_vlq(Ids.SESSION_VERSION_SYSTEM_PAOM_STRING)
        value += bytes([0x00, DataType.WSTRING]) + encode_uint32_vlq(len(text)) + text

        assert extract_session_version_string(value[:-1]) is None
        assert extract_session_version_string(value[:2]) is None


class TestLegitimationPayload:
    """Test legitimation payload building."""

    def test_payload_without_username(self) -> None:
        payload = _build_legitimation_payload("password")
        assert len(payload) > 0
        # Should contain struct header
        assert payload[1] == 0x17  # DataType.STRUCT

    def test_payload_with_username(self) -> None:
        payload = _build_legitimation_payload("password", "admin")
        assert len(payload) > 0

    def test_payload_legit_type_1_without_username(self) -> None:
        """Without username, legitimation type should be 1 (legacy)."""
        payload = _build_legitimation_payload("password")
        # [flags=0x00, type=0x17, struct id (4 bytes), key VLQ (3 bytes),
        #  flags=0x00, type=UDInt(0x04), legit_type VLQ]
        assert payload[10] == 0x04  # UDInt type for legit_type
        assert payload[11] == 0x01  # legit_type = 1

    def test_payload_legit_type_2_with_username(self) -> None:
        """With username, legitimation type should be 2 (new)."""
        payload = _build_legitimation_payload("password", "admin")
        assert payload[10] == 0x04  # UDInt type for legit_type
        assert payload[11] == 0x02  # legit_type = 2


class TestLegitimationState:
    """Test LegitimationState tracker."""

    def test_initial_state_not_authenticated(self) -> None:
        state = LegitimationState()
        assert not state.authenticated

    def test_mark_authenticated(self) -> None:
        state = LegitimationState()
        state.mark_authenticated()
        assert state.authenticated

    def test_with_oms_secret(self) -> None:
        state = LegitimationState(oms_secret=b"\x00" * 32)
        assert not state.authenticated

    def test_rotate_key(self) -> None:
        state = LegitimationState(oms_secret=b"\x00" * 32)
        # Should not raise
        state.rotate_key()

    def test_rotate_key_without_secret(self) -> None:
        state = LegitimationState()
        # Should not raise even without OMS secret
        state.rotate_key()


class TestIntegrityIdTracking:
    """Test IntegrityId counter logic in S7CommPlusConnection."""

    def test_initial_counters_zero(self) -> None:
        conn = S7CommPlusConnection("127.0.0.1")
        assert conn.integrity_id_read == 0
        assert conn.integrity_id_write == 0

    def test_connection_attributes(self) -> None:
        conn = S7CommPlusConnection("127.0.0.1")
        assert conn.oms_secret is None
        assert not conn.tls_active

    def test_protocol_version_default(self) -> None:
        conn = S7CommPlusConnection("127.0.0.1")
        assert conn.protocol_version == 0

    def test_tls_v2_response_application_payload_is_not_stripped(self) -> None:
        conn = S7CommPlusConnection("127.0.0.1")
        conn._connected = True
        conn._protocol_version = ProtocolVersion.V2
        conn._session_id = 0x70000001
        conn._with_integrity_id = True

        application_payload = bytes.fromhex("000100100201")
        response = struct.pack(">BHHHHB", 0x32, 0, FunctionCode.GET_MULTI_VARIABLES, 0, 1, 0x34)
        response += application_payload
        frame = encode_header(ProtocolVersion.V2, len(response)) + response
        frame += struct.pack(">BBH", 0x72, ProtocolVersion.V2, 0)

        conn._send_s7_data = MagicMock()
        conn._recv_s7_data = MagicMock(return_value=frame)

        assert conn.send_request(FunctionCode.GET_MULTI_VARIABLES, bytes(4)) == application_payload

        # GetMultiVariables is in FLAGS_34_FUNCTION_CODES
        assert conn._send_s7_data.call_args[0][0][17] == 0x34


class TestIntegrityIdVlqEncoding:
    """Test VLQ encoding used for IntegrityId values."""

    def test_encode_zero(self) -> None:
        assert encode_uint32_vlq(0) == b"\x00"

    def test_encode_small(self) -> None:
        encoded = encode_uint32_vlq(42)
        value, _ = decode_uint32_vlq(encoded)
        assert value == 42

    def test_encode_large(self) -> None:
        encoded = encode_uint32_vlq(0xFFFFFFFF)
        value, _ = decode_uint32_vlq(encoded)
        assert value == 0xFFFFFFFF

    def test_roundtrip_integrity_range(self) -> None:
        """Test encoding/decoding typical IntegrityId counter values."""
        for val in [0, 1, 127, 128, 255, 1000, 65535, 0x7FFFFFFF]:
            encoded = encode_uint32_vlq(val)
            decoded, consumed = decode_uint32_vlq(encoded)
            assert decoded == val
            assert consumed == len(encoded)


class TestLegitimationWireFormat:
    """Protocol fixtures matching the upstream S7CommPlus driver."""

    def test_build_get_var_substreamed_payload(self) -> None:
        payload = _build_get_var_substreamed_payload(0x01020304, LegitimationId.SERVER_SESSION_REQUEST)

        expected = struct.pack(">I", 0x01020304)
        expected += bytes([0x20, 0x04, 0x01])
        expected += encode_uint32_vlq(LegitimationId.SERVER_SESSION_REQUEST)
        expected += encode_object_qualifier(protocol_version=ProtocolVersion.V2)
        expected += struct.pack(">H", 1)
        expected += struct.pack(">I", 0)
        assert payload == expected

    def test_parse_get_var_substreamed_usint_array(self) -> None:
        challenge = bytes(range(20))
        response = bytes([0x00, 0x00, 0x10, 0x02])
        response += encode_uint32_vlq(len(challenge)) + challenge
        response += encode_uint32_vlq(7)  # trailing IntegrityId

        assert _parse_get_var_substreamed_response(response) == challenge

    def test_parse_get_var_substreamed_blob(self) -> None:
        challenge = bytes(range(16))
        response = bytes([0x00, 0x00, 0x00, DataType.BLOB, 0x00])
        response += encode_uint32_vlq(len(challenge)) + challenge
        response += encode_uint32_vlq(3)

        assert _parse_get_var_substreamed_response(response) == challenge

    def test_parse_get_var_substreamed_error(self) -> None:
        with pytest.raises(S7ConnectionError, match="return_value=0x1234"):
            _parse_get_var_substreamed_response(encode_uint32_vlq(0x1234))

    def test_build_set_variable_payload(self) -> None:
        value = bytes([0x10, 0x02, 0x02, 0xAA, 0xBB])
        payload = _build_set_variable_payload(0x01020304, LegitimationId.SERVER_SESSION_RESPONSE, value)

        expected = struct.pack(">I", 0x01020304)
        expected += encode_uint32_vlq(1)
        expected += encode_uint32_vlq(LegitimationId.SERVER_SESSION_RESPONSE)
        expected += value
        expected += encode_object_qualifier()
        expected += bytes([0x00])
        expected += struct.pack(">I", 0)
        assert payload == expected

    def test_set_variable_response_rejects_nonzero_return(self) -> None:
        with pytest.raises(S7ConnectionError, match="return_value=0x8104"):
            _check_set_variable_response(encode_uint32_vlq(0x8104))

    def test_sync_challenge_uses_protocol_request_shape(self) -> None:
        challenge = bytes(range(20))
        response = bytes([0x00, 0x00, 0x10, 0x02, len(challenge)]) + challenge + bytes([0x00])
        conn = S7CommPlusConnection("127.0.0.1")
        conn._session_id = 0x01020304
        conn.send_request = MagicMock(return_value=response)

        assert conn._get_legitimation_challenge() == challenge
        conn.send_request.assert_called_once_with(
            FunctionCode.GET_VAR_SUBSTREAMED,
            _build_get_var_substreamed_payload(0x01020304, LegitimationId.SERVER_SESSION_REQUEST),
            integrity_tail=4,
        )

    @pytest.mark.asyncio
    async def test_async_challenge_uses_protocol_request_shape(self) -> None:
        challenge = bytes(range(20))
        response = bytes([0x00, 0x00, 0x10, 0x02, len(challenge)]) + challenge + bytes([0x00])
        client = S7CommPlusAsyncClient()
        client._session_id = 0x01020304
        client._send_request = AsyncMock(return_value=response)

        assert await client._get_legitimation_challenge() == challenge
        client._send_request.assert_awaited_once_with(
            FunctionCode.GET_VAR_SUBSTREAMED,
            _build_get_var_substreamed_payload(0x01020304, LegitimationId.SERVER_SESSION_REQUEST),
            integrity_tail=4,
        )

    @pytest.mark.conformance
    def test_challenge_request_frame(self) -> None:
        challenge = bytes.fromhex("7d8f8470d20590efc1d740416b4a073296bf463b")
        payload = bytes([0x00, 0x00, 0x10, DataType.USINT]) + encode_uint32_vlq(len(challenge)) + challenge + bytes([0x00])
        body = struct.pack(">BHHHHB", 0x32, 0, FunctionCode.GET_VAR_SUBSTREAMED, 0, 6, 0x34) + payload

        conn = S7CommPlusConnection("127.0.0.1")
        conn._connected = True
        conn._protocol_version = ProtocolVersion.V2
        conn._session_id = 0x70000CB7
        conn._sequence_number = 6
        conn._with_integrity_id = True
        conn._integrity_id_read = 3
        conn._send_s7_data = MagicMock()
        conn._recv_s7_data = MagicMock(
            return_value=encode_header(ProtocolVersion.V2, len(body)) + body + struct.pack(">BBH", 0x72, 0x02, 0)
        )

        assert conn._get_legitimation_challenge() == challenge
        conn._send_s7_data.assert_called_once_with(
            bytes.fromhex(
                "72020035"  # header, data length 0x35
                "310000058600000006"  # request, GetVarSubStreamed, seq 6
                "70000cb734"  # session id, transport flags
                "70000cb7"  # InObjectId
                "200401822f"  # address array header + id 303
                "000004e88969001200000000896a001300896b00040000"  # ObjectQualifier
                "0001"  # unknown
                "03"  # IntegrityId (read)
                "00000000"  # fill
                "72020000"  # trailer
            )
        )

    @pytest.mark.conformance
    def test_legitimation_request_frame(self) -> None:
        response = bytes.fromhex("f5cc5389f613b1f2283cf9229406e5b3b32c6e43")
        body = struct.pack(">BHHHHB", 0x32, 0, FunctionCode.SET_VARIABLE, 0, 7, 0x34) + encode_uint32_vlq(0)

        conn = S7CommPlusConnection("127.0.0.1")
        conn._connected = True
        conn._protocol_version = ProtocolVersion.V2
        conn._session_id = 0x70000CB7
        conn._sequence_number = 7
        conn._with_integrity_id = True
        conn._integrity_id_write = 1
        conn._send_s7_data = MagicMock()
        conn._recv_s7_data = MagicMock(
            return_value=encode_header(ProtocolVersion.V2, len(body)) + body + struct.pack(">BBH", 0x72, 0x02, 0)
        )

        conn._send_legitimation_legacy(response)

        conn._send_s7_data.assert_called_once_with(
            bytes.fromhex(
                "72020049"  # header, data length 0x49
                "31000004f200000007"  # request, SetVariable, seq 7
                "70000cb734"  # session id, transport flags
                "70000cb7"  # InObjectId
                "018230"  # always-1, address id 304
                "100214"  # USInt array of 20
            )
            + response
            + bytes.fromhex(
                "000004e88969001200000000896a001300896b00040000"  # ObjectQualifier
                "00"  # unknown
                "01"  # IntegrityId (write)
                "00000000"  # fill
                "72020000"  # trailer
            )
        )

    @pytest.mark.conformance
    def test_non_zero_return_value_is_accepted(self) -> None:
        """The PLC signals success with a non-zero status word. Response captured from an S7-1512."""
        _check_set_variable_response(bytes.fromhex("9381b0808099a68019"))

    @pytest.mark.conformance
    def test_refusal_is_invisible_in_the_return_value(self) -> None:
        """A refused password is indistinguishable from an accepted one here. Response captured from an S7-1512."""
        _check_set_variable_response(bytes.fromhex("9381b390809aca8016"))


class TestCreateSessionRequest:
    """The CreateObject request that opens an S7CommPlus session."""

    def test_sync_request_shape(self) -> None:
        conn = S7CommPlusConnection("127.0.0.1")
        conn._send_s7_data = MagicMock()
        # Frame header declaring a zero-length body: _create_session bails out on the
        # length check, by which point the request is already on the wire.
        conn._recv_s7_data = MagicMock(return_value=bytes.fromhex("72010000"))

        with pytest.raises(S7ConnectionError, match="CreateObject response too short"):
            conn._create_session()

        frame = conn._send_s7_data.call_args[0][0]
        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,
            FunctionCode.CREATE_OBJECT,
            0x0000,
            0,  # first sequence number on a fresh connection
            ObjectId.OBJECT_NULL_SERVER_SESSION,
            0x36,
        )
        request += struct.pack(">I", ObjectId.OBJECT_SERVER_SESSION_CONTAINER)
        expected = encode_header(ProtocolVersion.V1, len(frame) - 8) + request
        assert frame[: len(expected)] == expected
        assert frame[-4:] == struct.pack(">BBH", 0x72, ProtocolVersion.V1, 0x0000)

    @pytest.mark.asyncio
    async def test_async_request_shape(self) -> None:
        client = S7CommPlusAsyncClient()
        client._send_cotp_dt = AsyncMock()
        client._recv_cotp_dt = AsyncMock(return_value=bytes.fromhex("72010000"))

        with pytest.raises(RuntimeError, match="CreateObject response too short"):
            await client._create_session()

        client._send_cotp_dt.assert_awaited_once()
        assert client._send_cotp_dt.await_args is not None
        frame = client._send_cotp_dt.await_args[0][0]
        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,
            FunctionCode.CREATE_OBJECT,
            0x0000,
            0,
            ObjectId.OBJECT_NULL_SERVER_SESSION,
            0x36,
        )
        request += struct.pack(">I", ObjectId.OBJECT_SERVER_SESSION_CONTAINER)
        expected = encode_header(ProtocolVersion.V1, len(frame) - 8) + request
        assert frame[: len(expected)] == expected
        assert frame[-4:] == struct.pack(">BBH", 0x72, ProtocolVersion.V1, 0x0000)


class TestDeleteSessionRequest:
    """The DeleteObject request that closes an S7CommPlus session."""

    def test_sync_request_shape(self) -> None:
        conn = S7CommPlusConnection("127.0.0.1")
        conn._protocol_version = ProtocolVersion.V2
        conn._session_id = 0x70000001
        conn._send_s7_data = MagicMock()
        conn._recv_s7_data = MagicMock(side_effect=OSError("no reply"))

        conn._delete_session()

        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,
            FunctionCode.DELETE_OBJECT,
            0x0000,
            0,  # first sequence number on a fresh connection
            0x70000001,
            0x34,
        )
        request += struct.pack(">I", 0)
        expected = encode_header(ProtocolVersion.V2, len(request)) + request
        expected += struct.pack(">BBH", 0x72, ProtocolVersion.V2, 0x0000)
        conn._send_s7_data.assert_called_once_with(expected)

    @pytest.mark.asyncio
    async def test_async_request_shape(self) -> None:
        client = S7CommPlusAsyncClient()
        client._protocol_version = ProtocolVersion.V2
        client._session_id = 0x70000001
        client._send_cotp_dt = AsyncMock()
        client._recv_cotp_dt = AsyncMock(side_effect=OSError("no reply"))

        await client._delete_session()

        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,
            FunctionCode.DELETE_OBJECT,
            0x0000,
            0,
            0x70000001,
            0x34,
        )
        request += struct.pack(">I", 0)
        expected = encode_header(ProtocolVersion.V2, len(request)) + request
        expected += struct.pack(">BBH", 0x72, ProtocolVersion.V2, 0x0000)
        client._send_cotp_dt.assert_awaited_once_with(expected)


class TestProtectionLevel:
    """The effective protection level read that precedes legitimation."""

    # Captured from a password-protected S7-1512: UDInt(4), trailing IntegrityId 7.
    RESPONSE = bytes.fromhex("00000004040700000000")

    def test_parse_scalar_udint(self) -> None:
        assert _parse_protection_level_response(self.RESPONSE) == AccessLevel.NO_ACCESS

    def test_parse_rejects_nonzero_return(self) -> None:
        with pytest.raises(S7ConnectionError, match="return_value=4660"):
            _parse_protection_level_response(encode_uint32_vlq(0x1234))

    def test_parse_rejects_missing_response_marker(self) -> None:
        with pytest.raises(S7ConnectionError, match="missing response marker"):
            _parse_protection_level_response(bytes([0x00]))

    def test_parse_rejects_truncated_pvalue_header(self) -> None:
        with pytest.raises(S7ConnectionError, match="missing PValue header"):
            _parse_protection_level_response(bytes([0x00, 0x00, 0x00]))

    def test_parse_rejects_non_udint_datatype(self) -> None:
        response = bytes([0x00, 0x00, 0x00, DataType.USINT, 0x04])
        with pytest.raises(S7ConnectionError, match="expected a scalar UDInt, got flags=0x00 datatype=0x02"):
            _parse_protection_level_response(response)

    def test_parse_rejects_udint_array(self) -> None:
        response = bytes([0x00, 0x00, 0x10, DataType.UDINT, 0x01, 0x04])
        with pytest.raises(S7ConnectionError, match="expected a scalar UDInt, got flags=0x10 datatype=0x04"):
            _parse_protection_level_response(response)

    def test_parse_rejects_truncated_value(self) -> None:
        response = bytes([0x00, 0x00, 0x00, DataType.UDINT, 0x84])
        with pytest.raises(S7ConnectionError, match="Malformed protection level response"):
            _parse_protection_level_response(response)

    def test_sync_read_uses_protocol_request_shape(self) -> None:
        conn = S7CommPlusConnection("127.0.0.1")
        conn._session_id = 0x01020304
        conn.send_request = MagicMock(return_value=self.RESPONSE)

        assert conn._get_effective_protection_level() == AccessLevel.NO_ACCESS
        conn.send_request.assert_called_once_with(
            FunctionCode.GET_VAR_SUBSTREAMED,
            _build_get_var_substreamed_payload(0x01020304, Ids.EFFECTIVE_PROTECTION_LEVEL),
            integrity_tail=4,
        )

    @pytest.mark.asyncio
    async def test_async_read_uses_protocol_request_shape(self) -> None:
        client = S7CommPlusAsyncClient()
        client._session_id = 0x01020304
        client._send_request = AsyncMock(return_value=self.RESPONSE)

        assert await client._get_effective_protection_level() == AccessLevel.NO_ACCESS
        client._send_request.assert_awaited_once_with(
            FunctionCode.GET_VAR_SUBSTREAMED,
            _build_get_var_substreamed_payload(0x01020304, Ids.EFFECTIVE_PROTECTION_LEVEL),
            integrity_tail=4,
        )


class TestSessionKeyTransportFlags:
    """After SessionKey auth, requests use V3 HMAC framing and transport flags 0x34."""

    def test_session_key_request_frame_structure(self) -> None:
        conn = S7CommPlusConnection("127.0.0.1")
        conn._connected = True
        conn._protocol_version = ProtocolVersion.V2
        conn._session_id = 0x70000001
        conn._session_key = bytes(32)
        conn._send_s7_data = MagicMock()
        conn._recv_s7_data = MagicMock(side_effect=OSError("no reply"))

        with pytest.raises(OSError, match="no reply"):
            conn.send_request(FunctionCode.GET_VARIABLE, bytes(4))

        frame = conn._send_s7_data.call_args[0][0]
        request = struct.pack(
            ">BHHHHIB",
            Opcode.REQUEST,
            0x0000,
            FunctionCode.GET_VARIABLE,
            0x0000,
            0,  # first sequence number on a fresh connection
            0x70000001,
            0x34,  # the session key forces 0x34 even for a function code outside FLAGS_34_FUNCTION_CODES
        )
        request += bytes(4)
        assert frame[:4] == encode_header(ProtocolVersion.V3, len(frame) - 8)
        assert frame[4] == 0x20  # hash-length marker before the 32-byte HMAC digest
        assert frame[37:-4] == request
        assert frame[-4:] == struct.pack(">BBH", 0x72, ProtocolVersion.V3, 0x0000)


class TestSessionKeySelection:
    def test_tls_v2_does_not_attempt_session_key_auth(self) -> None:
        conn = S7CommPlusConnection("127.0.0.1")
        conn._tls_active = True
        conn._protocol_version = ProtocolVersion.V2
        conn._public_key_fingerprint = "01:BD426B091F08731A"
        conn._session_challenge = bytes(range(20))

        assert conn._try_session_key_auth() is None
        assert conn._session_key is None


class TestProtocolVersionV2:
    """Test V2 protocol version constant."""

    def test_v2_value(self) -> None:
        assert int(ProtocolVersion.V2) == 0x02

    def test_v2_greater_than_v1(self) -> None:
        assert ProtocolVersion.V2 > ProtocolVersion.V1

    def test_v2_less_than_v3(self) -> None:
        assert ProtocolVersion.V2 < ProtocolVersion.V3


try:
    import cryptography  # noqa: F401

    _has_cryptography = True
except ImportError:
    _has_cryptography = False


@pytest.mark.skipif(not _has_cryptography, reason="requires cryptography package")
class TestBuildNewResponse:
    """Test AES-256-CBC legitimation response building."""

    def test_new_response_returns_bytes(self) -> None:
        from s7commplus.legitimation import build_new_response

        result = build_new_response(
            password="test",
            challenge=b"\x00" * 16,
            oms_secret=b"\x00" * 32,
        )
        assert isinstance(result, bytes)

    def test_new_response_is_aes_block_aligned(self) -> None:
        from s7commplus.legitimation import build_new_response

        result = build_new_response(
            password="test",
            challenge=b"\x00" * 16,
            oms_secret=b"\x00" * 32,
        )
        # AES-CBC output is always a multiple of 16 bytes
        assert len(result) % 16 == 0

    def test_new_response_different_passwords_differ(self) -> None:
        from s7commplus.legitimation import build_new_response

        challenge = b"\xab" * 16
        oms = b"\xcd" * 32
        r1 = build_new_response("password1", challenge, oms)
        r2 = build_new_response("password2", challenge, oms)
        assert r1 != r2

    def test_new_response_different_secrets_differ(self) -> None:
        from s7commplus.legitimation import build_new_response

        challenge = b"\xab" * 16
        r1 = build_new_response("test", challenge, b"\x00" * 32)
        r2 = build_new_response("test", challenge, b"\x01" * 32)
        assert r1 != r2

    def test_new_response_with_username(self) -> None:
        from s7commplus.legitimation import build_new_response

        result = build_new_response(
            password="test",
            challenge=b"\x00" * 16,
            oms_secret=b"\x00" * 32,
            username="admin",
        )
        assert isinstance(result, bytes)
        assert len(result) % 16 == 0

    def test_new_response_decryptable(self) -> None:
        """Verify the response can be decrypted back to the original payload."""
        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        from s7commplus.legitimation import (
            _build_legitimation_payload,
            build_new_response,
            derive_legitimation_key,
        )

        challenge = b"\x12\x34\x56\x78" * 4  # 16-byte IV
        oms_secret = b"\xaa\xbb\xcc\xdd" * 8  # 32 bytes

        encrypted = build_new_response("mypassword", challenge, oms_secret)

        # Decrypt
        key = derive_legitimation_key(oms_secret)
        iv = challenge[:16]
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded = decryptor.update(encrypted) + decryptor.finalize()

        # Remove PKCS7 padding
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded) + unpadder.finalize()

        # Should match the payload
        expected = _build_legitimation_payload("mypassword")
        assert plaintext == expected


class TestAuthenticate:
    """Test connection.authenticate() preconditions."""

    def test_authenticate_requires_connection(self) -> None:
        import pytest

        from snap7.error import S7ConnectionError

        conn = S7CommPlusConnection("127.0.0.1")
        with pytest.raises(S7ConnectionError, match="Not connected"):
            conn.authenticate("password")

    def test_authenticate_requires_tls(self) -> None:
        import pytest

        from snap7.error import S7ConnectionError

        conn = S7CommPlusConnection("127.0.0.1")
        conn._connected = True
        conn._tls_active = False
        with pytest.raises(S7ConnectionError, match="requires TLS"):
            conn.authenticate("password")
