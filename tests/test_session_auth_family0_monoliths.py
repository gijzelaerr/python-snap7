"""Vector tests for the Family-0 monolith ports.

Each ``MonolithN.Execute`` is mechanically transpiled from the C#
source via ``tools/transpile_harpo_monolith.py``. To prove the port
is byte-correct, we replay the test fixtures HarpoS7 ships in
``HarpoS7.Family0.Tests/Blobs/Monoliths`` and compare destination
buffers byte-for-byte.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from s7.session_auth.family0 import (
    monolith1,
    monolith2,
    monolith3,
    monolith4,
    monolith5,
    monolith6,
    monolith7,
    monolith8,
    monolith9,
    monolith10,
    monolith11,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "family0" / "monoliths"


@pytest.mark.parametrize(
    "monolith,index",
    [
        (monolith1, 1),
        (monolith2, 2),
        (monolith3, 3),
        (monolith4, 4),
        (monolith5, 5),
        (monolith6, 6),
        (monolith7, 7),
        (monolith8, 8),
        (monolith11, 11),
    ],
)
def test_monolith_vector(monolith: object, index: int) -> None:
    src = (_FIXTURES / f"monolith{index}-src.bin").read_bytes()
    expected = (_FIXTURES / f"monolith{index}-dst.bin").read_bytes()
    dst = bytearray(len(expected))
    monolith.execute(dst, src)  # type: ignore[attr-defined]
    assert bytes(dst) == expected, f"monolith{index} output mismatch"


@pytest.mark.parametrize(
    "monolith,index",
    [
        (monolith9, 9),
        (monolith10, 10),
    ],
)
def test_monolith_orchestrator_vector(monolith: object, index: int) -> None:
    src = (_FIXTURES / f"monolith{index}-src.bin").read_bytes()
    expected = (_FIXTURES / f"monolith{index}-dst.bin").read_bytes()
    dst = bytearray(len(expected))
    monolith.execute(dst, src)  # type: ignore[attr-defined]
    assert bytes(dst) == expected, f"monolith{index} output mismatch"


def test_monolith9_and_10_at_least_run() -> None:
    """Smoke test: even though the byte-exact vectors don't pass yet
    (see the xfail above), neither orchestrator raises. This catches
    regressions in transpiler signature handling for the Part files."""
    for index, mod in [(9, monolith9), (10, monolith10)]:
        src = (_FIXTURES / f"monolith{index}-src.bin").read_bytes()
        expected = (_FIXTURES / f"monolith{index}-dst.bin").read_bytes()
        dst = bytearray(len(expected))
        mod.execute(dst, src)  # type: ignore[attr-defined]


def test_monolith1_returns_zero() -> None:
    # Monolith1 is the only monolith that returns a uint (rather than
    # void); the test vector expects 0.
    src = (_FIXTURES / "monolith1-src.bin").read_bytes()
    dst = bytearray(72)
    assert monolith1.execute(dst, src) == 0
