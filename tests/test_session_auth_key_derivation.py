"""Vector tests for the SHA-256-based key derivation helpers.

All ground-truth bytes are reproduced verbatim from
``HarpoS7.Tests/Keys/KeyUtilitiesTests.cs``.
"""

from __future__ import annotations

import pytest

from s7.session_auth import (
    derive_challenge_encryption_key,
    derive_legitimation_challenge_key,
    derive_seed_encryption_key_and_iv,
)


class TestDeriveChallengeEncryptionKey:
    def test_repeating_dd(self) -> None:
        key = derive_challenge_encryption_key(b"\xdd" * 24)
        assert key == bytes.fromhex("4E001016DB625DCCE9105BDCD8A1B42C")

    def test_random_24_bytes(self) -> None:
        random_key = bytes.fromhex("D36E04F64F89C24E6CB9276D82409EE0E57B98F815063EF4")
        assert derive_challenge_encryption_key(random_key) == bytes.fromhex("B2B7DE6183FC1A97F8636952F1ABA0FD")

    def test_short_key_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least 24 bytes"):
            derive_challenge_encryption_key(b"\x00" * 23)


class TestDeriveSeedEncryptionKeyAndIv:
    def test_harpos7_vector(self) -> None:
        a2 = bytes.fromhex("B3420D0C6242B150D6862A4D61559E78A00DA5DC7B68551AD86DF007ABA5BBD9")
        a3 = bytes.fromhex(
            "18F124E0B4A6D964CEFC8453ED903D52"
            "F1B8C85258FE5B2459776C0630DC02FE"
            "F6D0B082D6D10B1EA728A50037AE69EB"
            "D7CCA10B1C73DA8AC3C287D2704BF325"
        )
        expected = bytes.fromhex(
            "43950F7B8B896E30457824DC8A591E328772ABB8B3C1937129642275610A4A4532687F19C02CA9EF361388943560918C"
        )
        assert derive_seed_encryption_key_and_iv(a2, a3) == expected

    def test_short_a2_rejected(self) -> None:
        with pytest.raises(ValueError, match="a2 must be at least 32 bytes"):
            derive_seed_encryption_key_and_iv(b"\x00" * 31, b"\x00" * 64)

    def test_short_a3_rejected(self) -> None:
        with pytest.raises(ValueError, match="a3 must be at least 64 bytes"):
            derive_seed_encryption_key_and_iv(b"\x00" * 32, b"\x00" * 63)


class TestDeriveLegitimationChallengeKey:
    def test_harpos7_vector(self) -> None:
        session_key = bytes.fromhex("4EAF8D971FFCF45A995947CC06BFF85B0A2DF1BA6F3AE94D")
        expected = bytes.fromhex("D36E04F64F89C24E6CB9276D82409EE0E57B98F815063EF4")
        assert derive_legitimation_challenge_key(session_key) == expected

    def test_short_session_key_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least 24 bytes"):
            derive_legitimation_challenge_key(b"\x00" * 23)
