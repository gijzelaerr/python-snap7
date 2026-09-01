"""Tests for S7CommPlus V2 protocol support.

Tests IntegrityId tracking, legitimation helpers, protocol constants,
and V2 connection behavior.
"""

import hashlib
import logging
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
    _log_create_object_return_value,
    _parse_get_var_substreamed_response,
    _parse_protection_level_response,
)
from s7commplus.legitimation import (
    LegitimationState,
    _build_legitimation_payload,
    build_legacy_response,
    derive_legitimation_key,
)
from s7commplus.protocol import (
    READ_FUNCTION_CODES,
    AccessLevel,
    DataType,
    FunctionCode,
    Ids,
    LegitimationId,
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
        # After struct header (flags=0x00, type=0x17, count VLQ), the first
        # element is flags=0x00, type=UDInt(0x04), then legit_type value
        # The exact structure: [0x00, 0x17, count, 0x00, 0x04, legit_type, ...]
        # legit_type=1 is at offset 5 (VLQ encoded)
        assert payload[4] == 0x04  # UDInt type for legit_type
        assert payload[5] == 0x01  # legit_type = 1

    def test_payload_legit_type_2_with_username(self) -> None:
        """With username, legitimation type should be 2 (new)."""
        payload = _build_legitimation_payload("password", "admin")
        assert payload[4] == 0x04  # UDInt type for legit_type
        assert payload[5] == 0x02  # legit_type = 2


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


class TestCreateObjectStatusLogging:
    """A CreateObject status alone does not identify a TLS requirement."""

    def test_plain_connection_does_not_recommend_tls(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.WARNING, logger="s7commplus.connection"):
            _log_create_object_return_value(0x4000800000000011, tls_active=False)

        assert "continuing to parse the returned session data" in caplog.text
        assert "TLS" not in caplog.text

    def test_success_is_silent(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.DEBUG, logger="s7commplus.connection"):
            _log_create_object_return_value(0, tls_active=False)

        assert caplog.text == ""
