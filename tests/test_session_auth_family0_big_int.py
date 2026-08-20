"""Vector tests for BigIntOperations.

Vendored from ``HarpoS7.Family0.Tests/BitOperations/BigIntOperationsTests.cs``
and the corresponding ``Blobs/BitOperations/`` binary fixtures.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from s7commplus.session_auth.family0.big_int_operations import (
    FINALIZE_DESTINATION_SIZE,
    PREPARE_DESTINATION_SIZE,
    finalize,
    prepare,
    prepare_finalize,
    rotate_left_31,
    rotate_right_30,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "family0" / "bit_operations"


def test_prepare_vector() -> None:
    src = (_FIXTURES / "prep_src.bin").read_bytes()
    expected = (_FIXTURES / "prep_dst.bin").read_bytes()
    dst = bytearray(PREPARE_DESTINATION_SIZE)
    prepare(dst, src)
    assert bytes(dst) == expected


def test_finalize_vector() -> None:
    src = (_FIXTURES / "finalize_src.bin").read_bytes()
    expected = (_FIXTURES / "finalize_dst.bin").read_bytes()
    dst = bytearray(FINALIZE_DESTINATION_SIZE)
    finalize(dst, src)
    assert bytes(dst) == expected


def test_prepare_finalize_vector() -> None:
    src = bytearray((_FIXTURES / "mixed_src.bin").read_bytes())
    expected = (_FIXTURES / "mixed_dst.bin").read_bytes()
    prepare_finalize(src)
    assert bytes(src) == expected


@pytest.mark.parametrize(
    "input_bytes,expected",
    [
        (
            bytes.fromhex("25" * 16),
            bytes.fromhex("92" * 15 + "F3"),
        ),
        (
            bytes.fromhex("92" * 15 + "F3"),
            bytes.fromhex("49" * 14 + "C9 79".replace(" ", "")),
        ),
    ],
)
def test_rotate_left_31_vectors(input_bytes: bytes, expected: bytes) -> None:
    buf = bytearray(input_bytes)
    rotate_left_31(buf)
    assert bytes(buf) == expected


def test_rotate_right_30_smoke() -> None:
    # Upstream has no direct vector test for rotate_right_30, so just
    # verify it runs without exception on a 24-byte buffer.
    buf = bytearray(b"\xaa" * 24)
    rotate_right_30(buf)
    assert len(buf) == 24
