"""Tests for the SecurityKeyEncryptedKey blob metadata writer."""

from __future__ import annotations

import pytest

from s7commplus.session_auth import (
    ENCRYPTED_BLOB_LENGTH_PLCSIM,
    ENCRYPTED_BLOB_LENGTH_REAL_PLC,
    KeyFamily,
    derive_key_id,
    get_blob_length,
    get_public_key,
    get_public_key_flags,
    get_symmetric_key_flags,
    write_metadata,
)


class TestFamilyConstants:
    def test_blob_lengths(self) -> None:
        assert get_blob_length(KeyFamily.S7_1500) == ENCRYPTED_BLOB_LENGTH_REAL_PLC == 180
        assert get_blob_length(KeyFamily.S7_1200) == ENCRYPTED_BLOB_LENGTH_REAL_PLC == 180
        assert get_blob_length(KeyFamily.PLCSIM) == ENCRYPTED_BLOB_LENGTH_PLCSIM == 216

    def test_symmetric_key_flags(self) -> None:
        assert get_symmetric_key_flags(KeyFamily.S7_1500) == 0x001
        assert get_symmetric_key_flags(KeyFamily.S7_1200) == 0x101
        assert get_symmetric_key_flags(KeyFamily.PLCSIM) == 0x301

    def test_public_key_flags(self) -> None:
        assert get_public_key_flags(KeyFamily.S7_1500) == 0x010
        assert get_public_key_flags(KeyFamily.S7_1200) == 0x110
        assert get_public_key_flags(KeyFamily.PLCSIM) == 0x310


class TestWriteMetadata:
    def test_returns_metadata_length(self) -> None:
        blob = bytearray(180)
        n = write_metadata(blob, get_public_key("01:BD426B091F08731A"), b"\x11" * 24, KeyFamily.S7_1200)
        assert n == 48

    def test_xbiggs_s7_1200_layout(self) -> None:
        # End-to-end: build the metadata header for @xBiggs's PLC
        # (family 1, fingerprint BD426B091F08731A) using a deterministic
        # symmetric key. Compare against the expected wire bytes
        # field-by-field — these match the layout the dissector decodes
        # in TIA Portal frame 31 of TIAPortalV19AccessibleDevices.pcapng.
        blob = bytearray(180)
        public_key = get_public_key("01:BD426B091F08731A")
        symmetric_key = b"\x11" * 24

        write_metadata(blob, public_key, symmetric_key, KeyFamily.S7_1200)

        # Magic
        assert bytes(blob[0:4]) == bytes.fromhex("ad de e1 fe".replace(" ", ""))
        # Blob length (180 = 0xB4 LE)
        assert bytes(blob[4:8]) == bytes.fromhex("b4 00 00 00".replace(" ", ""))
        # Two unknown=1 fields
        assert bytes(blob[8:12]) == bytes.fromhex("01 00 00 00".replace(" ", ""))
        assert bytes(blob[12:16]) == bytes.fromhex("01 00 00 00".replace(" ", ""))
        # Symmetric key id — derive_key_id(0x11*24) = 06DDCEE4ADAEC77A (HarpoS7 vector)
        assert bytes(blob[16:24]) == bytes.fromhex("06 dd ce e4 ad ae c7 7a".replace(" ", ""))
        # Symmetric flags = 0x101 for family 1
        assert bytes(blob[24:28]) == bytes.fromhex("01 01 00 00".replace(" ", ""))
        # Symmetric flags_internal = 0
        assert bytes(blob[28:32]) == bytes.fromhex("00 00 00 00".replace(" ", ""))
        # Public key id = derive_key_id(xBiggs's public key) = 1A73081F096B42BD
        assert bytes(blob[32:40]) == bytes.fromhex("1a 73 08 1f 09 6b 42 bd".replace(" ", ""))
        # Public flags = 0x110 for family 1
        assert bytes(blob[40:44]) == bytes.fromhex("10 01 00 00".replace(" ", ""))
        # Public flags_internal = 0
        assert bytes(blob[44:48]) == bytes.fromhex("00 00 00 00".replace(" ", ""))

    def test_matches_tia_capture_modulo_session_key(self) -> None:
        # Regression test against the actual TIA Portal V19 capture
        # bytes from xBiggs's PLC (issue #710 / PR #713). We don't know
        # the random key1 TIA used, so the symmetric_key_id slot
        # (offsets 16–23) is whatever TIA picked that session. Verify
        # every other byte matches.
        blob = bytearray(180)
        write_metadata(
            blob,
            get_public_key("01:BD426B091F08731A"),
            b"\x00" * 24,  # placeholder — only the symmetric key id slot is affected
            KeyFamily.S7_1200,
        )

        tia_metadata = bytes.fromhex(
            # offsets 0-15: magic + length + two unknown=1 fields
            "ad de e1 fe b4 00 00 00 01 00 00 00 01 00 00 00"
            # offsets 16-23: TIA's symmetric_key_id (random per session, not asserted)
            "ce 9b 9f 3a 94 03 98 6b"
            # offsets 24-31: symmetric flags + flags_internal
            "01 01 00 00 00 00 00 00"
            # offsets 32-39: PLC's public_key_id — fixed for this PLC
            "1a 73 08 1f 09 6b 42 bd"
            # offsets 40-47: public flags + flags_internal
            "10 01 00 00 00 00 00 00".replace(" ", "")
        )
        assert len(tia_metadata) == 48

        # Compare every byte except the symmetric key id slot (16..24).
        assert bytes(blob[0:16]) == tia_metadata[0:16]
        assert bytes(blob[24:48]) == tia_metadata[24:48]

    def test_plcsim_uses_64_byte_key_and_216_byte_blob(self) -> None:
        blob = bytearray(216)
        public_key = get_public_key("03:09013727CCBFBF3C")
        write_metadata(blob, public_key, b"\x11" * 24, KeyFamily.PLCSIM)
        # Length field = 216 = 0xD8 LE
        assert bytes(blob[4:8]) == bytes.fromhex("d8 00 00 00")
        # Symmetric flags = 0x301 LE
        assert bytes(blob[24:28]) == bytes.fromhex("01 03 00 00")
        # Public flags = 0x310 LE
        assert bytes(blob[40:44]) == bytes.fromhex("10 03 00 00")
        # Public key id matches the family-3 fingerprint
        expected_pubkey_id = derive_key_id(public_key)
        assert bytes(blob[32:40]) == expected_pubkey_id

    def test_short_blob_rejected(self) -> None:
        blob = bytearray(40)
        with pytest.raises(ValueError, match="at least 48 bytes"):
            write_metadata(blob, b"\x00" * 40, b"\x00" * 24, KeyFamily.S7_1200)

    def test_short_public_key_rejected(self) -> None:
        blob = bytearray(180)
        with pytest.raises(ValueError, match="public_key must be at least 40"):
            write_metadata(blob, b"\x00" * 39, b"\x00" * 24, KeyFamily.S7_1200)

    def test_short_public_key_rejected_for_plcsim(self) -> None:
        blob = bytearray(216)
        with pytest.raises(ValueError, match="public_key must be at least 64"):
            write_metadata(blob, b"\x00" * 40, b"\x00" * 24, KeyFamily.PLCSIM)
