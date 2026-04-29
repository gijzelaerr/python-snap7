"""Tests for the S7CommPlus session-auth public-key store."""

from __future__ import annotations

import pytest

from s7.session_auth import (
    PUBLIC_KEY_LENGTH_PLCSIM,
    PUBLIC_KEY_LENGTH_REAL_PLC,
    KeyFamily,
    UnknownPublicKeyError,
    get_public_key,
    parse_fingerprint,
)
from s7.session_auth.keys import _PUBLIC_KEYS


class TestParseFingerprint:
    def test_s7_1500(self) -> None:
        assert parse_fingerprint("00:181B7B0847D11694") == (KeyFamily.S7_1500, "181B7B0847D11694")

    def test_s7_1200(self) -> None:
        assert parse_fingerprint("01:BD426B091F08731A") == (KeyFamily.S7_1200, "BD426B091F08731A")

    def test_plcsim(self) -> None:
        assert parse_fingerprint("03:E90B455D3CC46013") == (KeyFamily.PLCSIM, "E90B455D3CC46013")

    def test_lowercase_key_id_uppercased(self) -> None:
        # PLCs always send uppercase, but be tolerant on input.
        assert parse_fingerprint("01:bd426b091f08731a") == (KeyFamily.S7_1200, "BD426B091F08731A")

    def test_wrong_length(self) -> None:
        with pytest.raises(ValueError, match="shape"):
            parse_fingerprint("01:short")

    def test_missing_colon(self) -> None:
        with pytest.raises(ValueError, match="shape"):
            parse_fingerprint("01-BD426B091F08731A")

    def test_unsupported_family(self) -> None:
        # Family 0x02 has key files in HarpoS7 but is not yet supported.
        with pytest.raises(ValueError, match="Unsupported public-key family"):
            parse_fingerprint("02:1CE2E82CFB24A8BD")

    def test_invalid_family_hex(self) -> None:
        with pytest.raises(ValueError, match="Invalid family"):
            parse_fingerprint("zz:BD426B091F08731A")

    def test_invalid_key_id_hex(self) -> None:
        # 19-char shape (16 chars after the colon) with non-hex chars.
        bad = "01:" + "NOTAHEXVALUEZZZZ"
        assert len(bad) == 19
        with pytest.raises(ValueError, match="Invalid key id"):
            parse_fingerprint(bad)


class TestGetPublicKey:
    def test_xbiggs_s7_1200(self) -> None:
        # The fingerprint @xBiggs's PLC advertises in #710. Verify the
        # bytes match HarpoS7's BD426B091F08731A.bin verbatim.
        key = get_public_key("01:BD426B091F08731A")
        assert key == bytes.fromhex("e0e1f04a5ca3f90148178689bd0c930ab9db867b4f0ab109623959aa32316b7880ed1b4f9a9b189f")
        assert len(key) == PUBLIC_KEY_LENGTH_REAL_PLC

    def test_known_s7_1500_key(self) -> None:
        key = get_public_key("00:181B7B0847D11694")
        assert key == bytes.fromhex("8456a26996122216c921c571ff11e0befafdb1d70b5d4bc8390f5b0cc273ec142a03f2a04e6f1593")

    def test_known_plcsim_key(self) -> None:
        key = get_public_key("03:09013727CCBFBF3C")
        assert len(key) == PUBLIC_KEY_LENGTH_PLCSIM

    def test_unknown_key_id(self) -> None:
        with pytest.raises(UnknownPublicKeyError) as exc_info:
            get_public_key("00:0000000000000000")
        assert exc_info.value.fingerprint == "00:0000000000000000"

    def test_unknown_key_id_different_family(self) -> None:
        # Same key id as xBiggs's but in family 0 — should not silently
        # cross families.
        with pytest.raises(UnknownPublicKeyError):
            get_public_key("00:BD426B091F08731A")


class TestVendoredKeys:
    def test_real_plc_keys_are_40_bytes(self) -> None:
        real_plc_families = {KeyFamily.S7_1500, KeyFamily.S7_1200}
        real_plc_keys = [v for (f, _), v in _PUBLIC_KEYS.items() if f in real_plc_families]
        assert real_plc_keys, "expected at least one real-PLC key"
        assert all(len(k) == PUBLIC_KEY_LENGTH_REAL_PLC for k in real_plc_keys)

    def test_plcsim_keys_are_64_bytes(self) -> None:
        plcsim_keys = [v for (f, _), v in _PUBLIC_KEYS.items() if f == KeyFamily.PLCSIM]
        assert plcsim_keys, "expected at least one PlcSim key"
        assert all(len(k) == PUBLIC_KEY_LENGTH_PLCSIM for k in plcsim_keys)

    def test_key_ids_are_uppercase_16_hex(self) -> None:
        for _, key_id in _PUBLIC_KEYS:
            assert len(key_id) == 16
            assert key_id == key_id.upper()
            bytes.fromhex(key_id)  # raises if not hex
