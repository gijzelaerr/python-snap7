"""Tests for the session-auth low-level helpers.

The ``derive_key_id`` test vectors are reproduced verbatim from
HarpoS7's ``HarpoS7.Utilities.Tests/Extensions/KeyExtensionsTests.cs``,
which in turn was generated from the proprietary algorithm in
Siemens' ``OMSp_core_managed.dll``. Matching them gives us strong
ground-truth coverage that our port is byte-correct.
"""

from __future__ import annotations

import pytest

from s7commplus.session_auth import KEY_ID_LENGTH, derive_key_id, get_public_key, parse_fingerprint
from s7commplus.session_auth.keys import _PUBLIC_KEYS


class TestDeriveKeyId:
    def test_harpos7_vector_64_byte_key(self) -> None:
        # First TestCase from HarpoS7 KeyExtensionsTests — a 64-byte
        # PlcSim key (5A9B6B015F48D284 in family 3).
        key = bytes.fromhex(
            "eca6d799ddf03eaadd16b5d7245331e426c9e6ba8997877a"
            "7394f3286532a6b053e4229818085223432483fba4d5c43b"
            "d6c354c10febc903908ed271697f39e9"
        )
        assert derive_key_id(key) == bytes.fromhex("84d2485f016b9b5a")

    def test_harpos7_vector_repeating_11(self) -> None:
        # Second TestCase from HarpoS7 — 24 bytes of 0x11.
        key = b"\x11" * 24
        assert derive_key_id(key) == bytes.fromhex("06ddcee4adaec77a")

    def test_harpos7_vector_repeating_44(self) -> None:
        # Third TestCase from HarpoS7 — 24 bytes of 0x44.
        key = b"\x44" * 24
        assert derive_key_id(key) == bytes.fromhex("06d0ef4b10626822")

    def test_returns_eight_bytes(self) -> None:
        assert len(derive_key_id(b"\x00" * 32)) == KEY_ID_LENGTH

    def test_only_first_24_bytes_used(self) -> None:
        # Bytes past offset 24 must not affect the output.
        base = b"A" * 24
        assert derive_key_id(base + b"X" * 100) == derive_key_id(base + b"Y" * 100)

    def test_short_key_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least 24 bytes"):
            derive_key_id(b"\x00" * 23)


class TestKeyIdMatchesAdvertisedFingerprint:
    """Self-verifies: every bundled public key, when run through
    ``derive_key_id``, must produce the fingerprint it's keyed on.

    The fingerprint string is the big-endian hex display of the same
    8 bytes ``derive_key_id`` produces (in little-endian byte order).
    """

    def test_xbiggs_s7_1200_key(self) -> None:
        # The headline case: the PLC fingerprint @xBiggs reports in
        # #710 must round-trip through our key store + derive_key_id.
        key = get_public_key("01:BD426B091F08731A")
        assert derive_key_id(key) == bytes.fromhex("1A73081F096B42BD")

    def test_all_bundled_keys_round_trip(self) -> None:
        for (family, key_id), key in _PUBLIC_KEYS.items():
            expected_id_bytes = bytes.fromhex(key_id)[::-1]  # BE display → LE bytes
            assert derive_key_id(key) == expected_id_bytes, f"derive_key_id mismatch for {family.name}/{key_id}"

    def test_full_fingerprint_string_round_trip(self) -> None:
        # End-to-end: parse the fingerprint string, look up the key,
        # derive its id, and confirm the id reconstructs the original
        # post-colon hex.
        fp = "01:BD426B091F08731A"
        family, key_id = parse_fingerprint(fp)
        del family  # not asserted here
        key = get_public_key(fp)
        derived_le = derive_key_id(key)
        derived_be_hex = derived_le[::-1].hex().upper()
        assert derived_be_hex == key_id
