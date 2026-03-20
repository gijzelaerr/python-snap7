"""Tests for S7CommPlus V2 protocol support.

Tests IntegrityId tracking, legitimation helpers, protocol constants,
and V2 connection behavior.
"""

import hashlib


from snap7.s7commplus.protocol import (
    FunctionCode,
    LegitimationId,
    ProtocolVersion,
    READ_FUNCTION_CODES,
)
from snap7.s7commplus.legitimation import (
    LegitimationState,
    build_legacy_response,
    derive_legitimation_key,
    _build_legitimation_payload,
)
from snap7.s7commplus.vlq import encode_uint32_vlq, decode_uint32_vlq
from snap7.s7commplus.connection import S7CommPlusConnection


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


class TestProtocolVersionV2:
    """Test V2 protocol version constant."""

    def test_v2_value(self) -> None:
        assert int(ProtocolVersion.V2) == 0x02

    def test_v2_greater_than_v1(self) -> None:
        assert ProtocolVersion.V2 > ProtocolVersion.V1

    def test_v2_less_than_v3(self) -> None:
        assert ProtocolVersion.V2 < ProtocolVersion.V3


class TestNewResponseNotImplemented:
    """Test that build_new_response raises NotImplementedError without cryptography."""

    def test_new_response_requires_cryptography(self) -> None:
        from snap7.s7commplus.legitimation import build_new_response

        # This may or may not raise depending on whether cryptography is installed
        # We test the function signature is correct
        try:
            result = build_new_response(
                password="test",
                challenge=b"\x00" * 16,
                oms_secret=b"\x00" * 32,
            )
            # If cryptography is installed, result should be bytes
            assert isinstance(result, bytes)
        except NotImplementedError:
            # Expected when cryptography is not installed
            pass
