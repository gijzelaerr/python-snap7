"""Vector tests for the Family-0 transforms.

Vendored from ``HarpoS7.Family0.Tests/Transforms/TransformTests.cs``
plus the corresponding ``Blobs/Transforms`` fixtures.
"""

from __future__ import annotations

from pathlib import Path

from s7commplus.session_auth.family0 import (
    checksum_transform,
    key_derivation_transform,
    lut_generator,
    pre_seed_transform,
    transform13,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "family0" / "transforms"


def test_pre_seed_transform_vector() -> None:
    src = (_FIXTURES / "transform1-src.bin").read_bytes()
    expected = (_FIXTURES / "transform1-dst.bin").read_bytes()
    dst = bytearray(pre_seed_transform.DESTINATION_SIZE)
    pre_seed_transform.execute(dst, src)
    assert bytes(dst) == expected


def test_key_derivation_transform_vector() -> None:
    src = (_FIXTURES / "transform2-src.bin").read_bytes()
    expected = (_FIXTURES / "transform2-dst.bin").read_bytes()
    dst = bytearray(key_derivation_transform.DESTINATION_SIZE)
    key_derivation_transform.execute(dst, src)
    assert bytes(dst) == expected


def test_lut_generator_vector() -> None:
    src = (_FIXTURES / "transform3-src.bin").read_bytes()
    expected = (_FIXTURES / "transform3-dst.bin").read_bytes()
    dst = bytearray(lut_generator.DESTINATION_SIZE)
    lut_generator.execute(dst, src)
    assert bytes(dst) == expected


def test_checksum_transform_vector() -> None:
    key = (_FIXTURES / "transform4-key.bin").read_bytes()
    lut = (_FIXTURES / "transform4-lut.bin").read_bytes()
    expected = (_FIXTURES / "transform4-dst.bin").read_bytes()
    dst = bytearray(checksum_transform.DESTINATION_SIZE)
    checksum_transform.execute(dst, key, lut)
    assert bytes(dst) == expected


def test_transform13_vector() -> None:
    src = (_FIXTURES / "transform13-src.bin").read_bytes()
    expected = (_FIXTURES / "transform13-dst.bin").read_bytes()
    dst = bytearray(transform13.DESTINATION_SIZE)
    transform13.execute(dst, src)
    assert bytes(dst) == expected
