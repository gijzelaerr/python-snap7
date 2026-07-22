"""Tests for the custom AES-CTR-with-MAC primitive.

Vectors reproduced from ``HarpoS7.Tests/Aes/HarpoAesCtrTests.cs`` —
``TestInit`` and ``TestEncrypt2Times``. ``CalculateChecksumTest``
arrives in a follow-up slice.
"""

from __future__ import annotations

import pytest

from s7commplus.session_auth.harpo_aes_ctr import HarpoAesCtr

try:
    import cryptography  # noqa: F401

    _has_cryptography = True
except ImportError:
    _has_cryptography = False


_KEY = bytes.fromhex("4E001016DB625DCCE9105BDCD8A1B42C")


@pytest.mark.skipif(not _has_cryptography, reason="requires cryptography package")
class TestInit:
    def test_counter_after_init(self) -> None:
        # HarpoAesCtrTests.TestInit — Init with IV = 0xCC * 16 must
        # produce this specific 16-byte counter value.
        cipher = HarpoAesCtr(_KEY)
        cipher.init(b"\xcc" * 16)
        assert cipher.counter == bytes.fromhex("D478DE8B1A40ED2F89F80166EEFCD513")


@pytest.mark.skipif(not _has_cryptography, reason="requires cryptography package")
class TestEncryptCtr:
    def test_two_calls_back_to_back(self) -> None:
        # HarpoAesCtrTests.TestEncrypt2Times — encrypt 16 bytes then
        # 24 bytes back-to-back; both ciphertexts must match.
        cipher = HarpoAesCtr(_KEY)
        cipher.init(b"\xcc" * 16)

        data1 = bytes.fromhex("B1B3D9484C6E4240403F63C6B5012CC5")
        ct1 = cipher.encrypt_ctr(data1)
        assert ct1 == bytes.fromhex("CDF986A8C7975D5390535C1D7954FA7F")

        data2 = b"\xdd" * 24
        ct2 = cipher.encrypt_ctr(data2)
        assert ct2 == bytes.fromhex("33FF1BD50184486B897ADB64154B785FAB877A290783240A")

    def test_empty_plaintext(self) -> None:
        # Sanity: encrypting nothing returns nothing and doesn't
        # advance state.
        cipher = HarpoAesCtr(_KEY)
        cipher.init(b"\xcc" * 16)
        before = cipher.counter
        assert cipher.encrypt_ctr(b"") == b""
        assert cipher.counter == before


@pytest.mark.skipif(not _has_cryptography, reason="requires cryptography package")
class TestCalculateChecksum:
    def test_harpos7_vector(self) -> None:
        # HarpoAesCtrTests.CalculateChecksumTest — mocks every
        # piece of internal state directly, then verifies the
        # finalised MAC. Mirrors the C# test which uses reflection;
        # we just assign the bytearrays.
        cipher = HarpoAesCtr(bytes.fromhex("43950F7B8B896E30457824DC8A591E32"))

        # Mock _var1, _var2.
        cipher._var2 = 0x10
        cipher._var1 = 0x00

        # Mock LUT — load the 4096-byte fixture vendored from the
        # C# test's _mockChecksumLut literal.
        from pathlib import Path

        fixture = Path(__file__).parent / "fixtures" / "harpo_aes_ctr_mock_checksum_lut.bin"
        cipher._lut[:] = fixture.read_bytes()

        # Mock the three 16-byte slots the test pre-fills.
        cipher._aes3[:] = bytes.fromhex("738FA8A07EF0893A97CBF681250AD2FA")
        cipher._aes2[:] = bytes.fromhex("478FC2674E3EB1DD3DD9787103E92316")
        cipher._iv_extension[:] = bytes.fromhex("585CE8585DF132FA4C7FD9BECEB97461")

        checksum = cipher.calculate_checksum()
        assert checksum == bytes.fromhex("5A948DB51DC34FF25808ED3ABE15EB12")

    def test_invalid_length_too_large(self) -> None:
        cipher = HarpoAesCtr(_KEY)
        cipher.init(b"\xcc" * 16)
        with pytest.raises(ValueError, match="length must be 1..16"):
            cipher.calculate_checksum(17)

    def test_invalid_length_zero(self) -> None:
        cipher = HarpoAesCtr(_KEY)
        cipher.init(b"\xcc" * 16)
        with pytest.raises(ValueError, match="length must be 1..16"):
            cipher.calculate_checksum(0)


@pytest.mark.skipif(not _has_cryptography, reason="requires cryptography package")
class TestInitGuardClauses:
    def test_empty_iv_rejected(self) -> None:
        cipher = HarpoAesCtr(_KEY)
        with pytest.raises(ValueError, match="iv must not be empty"):
            cipher.init(b"")

    def test_12_byte_iv_not_implemented(self) -> None:
        cipher = HarpoAesCtr(_KEY)
        with pytest.raises(NotImplementedError, match="12-byte"):
            cipher.init(b"\x00" * 12)

    def test_unaligned_iv_not_implemented(self) -> None:
        cipher = HarpoAesCtr(_KEY)
        with pytest.raises(NotImplementedError, match="non-multiple-of-16"):
            cipher.init(b"\x00" * 17)
