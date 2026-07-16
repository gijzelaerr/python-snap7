"""Vector tests for the BigInt-arithmetic Transforms.

Vendored from
``HarpoS7.Family0.Tests/Transforms/TransformTests.cs``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from s7commplus.session_auth.family0.big_int_transforms import (
    DESTINATION_SIZE,
    big_int_addition,
    big_int_multiplication,
    big_int_square,
    big_int_subtraction,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "family0" / "transforms"


def _path(idx: int, postfix: str, sub: int | None = None) -> Path:
    suffix = f"_{sub}" if sub is not None else ""
    return _FIXTURES / f"transform{idx}{suffix}-{postfix}.bin"


@pytest.mark.parametrize("sub", [None, 2])
def test_big_int_addition(sub: int | None) -> None:
    s1 = _path(8, "source1", sub).read_bytes()
    s2 = _path(8, "source2", sub).read_bytes()
    expected = _path(8, "dst", sub).read_bytes()
    dst = bytearray(DESTINATION_SIZE)
    big_int_addition(dst, s1, s2)
    assert bytes(dst) == expected


@pytest.mark.parametrize("sub", [None, 2, 3])
def test_big_int_multiplication(sub: int | None) -> None:
    s1 = _path(9, "source1", sub).read_bytes()
    s2 = _path(9, "source2", sub).read_bytes()
    expected = _path(9, "dst", sub).read_bytes()
    dst = bytearray(DESTINATION_SIZE)
    big_int_multiplication(dst, s1, s2)
    assert bytes(dst) == expected


@pytest.mark.parametrize("sub", [None, 2])
def test_big_int_square(sub: int | None) -> None:
    src = _path(10, "src", sub).read_bytes()
    expected = _path(10, "dst", sub).read_bytes()
    dst = bytearray(DESTINATION_SIZE)
    big_int_square(dst, src)
    assert bytes(dst) == expected


@pytest.mark.parametrize("sub", [None, 2, 3, 4])
def test_big_int_subtraction(sub: int | None) -> None:
    s1 = _path(11, "source1", sub).read_bytes()
    s2 = _path(11, "source2", sub).read_bytes()
    expected = _path(11, "dst", sub).read_bytes()
    dst = bytearray(DESTINATION_SIZE)
    big_int_subtraction(dst, s1, s2)
    assert bytes(dst) == expected
