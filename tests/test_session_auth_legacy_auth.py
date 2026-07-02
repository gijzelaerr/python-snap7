"""End-to-end vector test for LegacyAuthenticationScheme.

Uses deterministic "random" bytes (matching HarpoS7's StaticFillSequence
test mode) to verify the full auth blob construction and session key
derivation against the C# test vectors.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from s7.session_auth.family0.fingerprint import fingerprint_challenge
from s7.session_auth.keys import KeyFamily


def test_fingerprint_challenge_vector() -> None:
    challenge = bytes(
        [
            184,
            13,
            177,
            179,
            217,
            72,
            76,
            110,
            66,
            64,
            64,
            63,
            99,
            198,
            181,
            1,
            44,
            197,
            46,
            127,
        ]
    )
    expected = bytes([0xE2, 0x87, 0xC1, 0xCB, 0x65, 0x9B, 0x9E, 0xDF])
    fp = bytearray(8)
    fingerprint_challenge(fp, challenge)
    assert bytes(fp) == expected


def _make_deterministic_urandom(fill_sequence: list[int]):
    """Create a mock urandom that fills each call with the next byte
    from the fill sequence, cycling through it."""
    index = [0]

    def mock_urandom(n: int) -> bytes:
        fill_byte = fill_sequence[index[0]]
        index[0] = (index[0] + 1) % len(fill_sequence)
        return bytes([fill_byte] * n)

    return mock_urandom


@pytest.mark.parametrize(
    "expected_blob_hex, expected_session_key_hex, challenge_hex, public_key_hex, fill_seq, family",
    [
        pytest.param(
            # S7-1500 test vector
            "adde e1fe b400 0000 0100 0000 0100 0000"
            "4e0c 313b 5e08 e43b 0100 0000 0000 0000"
            "9416 d147 087b 1b18 1000 0000 0000 0000"
            "793c 08f6 e8ed 43d9 aace 705e 868d 23df"
            "19b9 0751 9756 1ecb 1aa3 ef70 7a7a cf18"
            "a7d5 29fe 219d 55e7 2d2d 2d2d 2d2d 2d2d"
            "2d2d 2d2d 2d2d 2d2d 2d2d 2d2d 2525 2525"
            "2525 2525 2525 2525 2525 2525 05c6 087c"
            "f782 dba3 9e21 bafa 8f31 b324 bf58 0016"
            "4bbc 3dde 0d15 d69d b765 46f4 491c a34f"
            "ef12 f959 ec90 0f00 5f36 dd38 9040 761e"
            "f2b8 56d6",
            "65c4 f179 980a 43cb 60e1 194b a500 f5b9d04f 374b 5637 4866",
            "dddd dddd dddd dddd dddd dddd dddd dddd dddd dddd",
            "8456 a269 9612 2216 c921 c571 ff11 e0befafd b1d7 0b5d 4bc8 390f 5b0c c273 ec142a03 f2a0 4e6f 1593",
            [0x35, 0x35, 0x25, 0x2D, 0x2D],
            KeyFamily.S7_1500,
            id="s7_1500",
        ),
        pytest.param(
            # S7-1200 test vector
            "adde e1fe b400 0000 0100 0000 0100 0000"
            "4e0c 313b 5e08 e43b 0101 0000 0000 0000"
            "1a73 081f 096b 42bd 1001 0000 0000 0000"
            "4c53 13ae c968 10cc fe31 73f7 7a55 540d"
            "ef55 8e51 9756 1ecb 1aa3 ef70 7a7a cf18"
            "a7d5 29fe 219d 55e7 2d2d 2d2d 2d2d 2d2d"
            "2d2d 2d2d 2d2d 2d2d 2d2d 2d2d 2525 2525"
            "2525 2525 2525 2525 2525 2525 82af 96f4"
            "37c0 2816 4923 a36c 44d8 061d bf58 0016"
            "4bbc 3dde 0d15 d69d b765 46f4 491c a34f"
            "ef12 f959 791f 2d0e 30de 7be5 af11 234c"
            "6007 e47e",
            "f18c e220 f7ba 1754 42cf 1c4d ddb5 9e82eafa 62d5 dd09 6e1a",
            "5a5d 5ab4 4355 1d9f 2e68 0adf c44b 163468e4 2736",
            "e0e1 f04a 5ca3 f901 4817 8689 bd0c 930ab9db 867b 4f0a b109 6239 59aa 3231 6b7880ed 1b4f 9a9b 189f",
            [0x35, 0x35, 0x25, 0x2D, 0x2D],
            KeyFamily.S7_1200,
            id="s7_1200",
        ),
    ],
)
def test_authenticate_real_plc_vector(
    expected_blob_hex: str,
    expected_session_key_hex: str,
    challenge_hex: str,
    public_key_hex: str,
    fill_seq: list[int],
    family: KeyFamily,
) -> None:
    expected_blob = bytes.fromhex(expected_blob_hex.replace(" ", ""))
    expected_session_key = bytes.fromhex(expected_session_key_hex.replace(" ", ""))
    challenge = bytes.fromhex(challenge_hex.replace(" ", ""))
    public_key = bytes.fromhex(public_key_hex.replace(" ", ""))

    mock_urandom = _make_deterministic_urandom(fill_seq)

    with patch("os.urandom", mock_urandom):
        from s7.session_auth.legacy_auth import authenticate_real_plc

        blob, session_key = authenticate_real_plc(challenge, public_key, family)

    assert blob == expected_blob, f"Blob mismatch at byte {_first_diff(blob, expected_blob)}"
    assert session_key == expected_session_key


def _first_diff(a: bytes, b: bytes) -> int:
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return min(len(a), len(b))
