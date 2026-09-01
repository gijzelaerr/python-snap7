"""Tests for the AES-128-ECB primitive used by the session-key handshake."""

from __future__ import annotations

import pytest

from s7commplus.session_auth.harpo_aes import (
    AES_BLOCK_SIZE,
    AES_KEY_LENGTH,
    HarpoAes,
)

try:
    import cryptography  # noqa: F401

    _has_cryptography = True
except ImportError:
    _has_cryptography = False


@pytest.mark.skipif(not _has_cryptography, reason="requires cryptography package")
class TestHarpoAes:
    def test_nist_vector(self) -> None:
        # NIST FIPS-197 Appendix C.1 example vector: AES-128.
        # Key: 000102030405060708090a0b0c0d0e0f
        # PT:  00112233445566778899aabbccddeeff
        # CT:  69c4e0d86a7b0430d8cdb78070b4c55a
        cipher = HarpoAes(bytes.fromhex("000102030405060708090a0b0c0d0e0f"))
        ct = cipher.encrypt_ecb(bytes.fromhex("00112233445566778899aabbccddeeff"))
        assert ct == bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")

    def test_multi_block(self) -> None:
        # Two blocks of zeros under a zero key — verify the
        # block-mode wiring (ECB encrypts each block independently).
        cipher = HarpoAes(b"\x00" * AES_KEY_LENGTH)
        block_zero = cipher.encrypt_ecb(b"\x00" * AES_BLOCK_SIZE)
        two_blocks = cipher.encrypt_ecb(b"\x00" * AES_BLOCK_SIZE * 2)
        assert two_blocks == block_zero * 2

    def test_reusable_across_calls(self) -> None:
        cipher = HarpoAes(b"\x11" * AES_KEY_LENGTH)
        first = cipher.encrypt_ecb(b"\x22" * AES_BLOCK_SIZE)
        second = cipher.encrypt_ecb(b"\x22" * AES_BLOCK_SIZE)
        assert first == second  # ECB is deterministic

    def test_wrong_key_size(self) -> None:
        with pytest.raises(ValueError, match="must be 16 bytes"):
            HarpoAes(b"\x00" * 15)

    def test_wrong_plaintext_size(self) -> None:
        cipher = HarpoAes(b"\x00" * AES_KEY_LENGTH)
        with pytest.raises(ValueError, match="multiple of 16"):
            cipher.encrypt_ecb(b"\x00" * 15)
