"""WithCopy wrappers for Monoliths 3-7.

Each monolith has a flat ``execute(destination, source)`` entry point.
The ``with_copy`` variants concatenate multiple input spans into the
monolith's source buffer, run Execute, then split the destination
into multiple output spans. These are used by Transform7.

Ported from ``HarpoS7.Family0.Monoliths.Monolith{3..7}.WithCopy``.
"""

from __future__ import annotations

from ._generated import monolith3, monolith4, monolith5, monolith6, monolith7


def monolith3_with_copy(dst1: bytearray, dst2: bytearray, src1: bytes, src2: bytes, src3: bytes) -> None:
    """Monolith3.WithCopy: 3 inputs (0x48+0x48+0x18) → 2 outputs (0x48+0x48)."""
    mono_src = bytearray(0x48 + 0x48 + 0x18)
    mono_src[:0x48] = src1[:0x48]
    mono_src[0x48 : 0x48 + 0x48] = src2[:0x48]
    mono_src[0x90 : 0x90 + 0x18] = src3[:0x18]

    mono_dst = bytearray(0x90)
    monolith3.execute(mono_dst, bytes(mono_src))

    dst1[:0x48] = mono_dst[:0x48]
    dst2[:0x48] = mono_dst[0x48:0x90]


def monolith4_with_copy(dst: bytearray, src1: bytes, src2: bytes) -> None:
    """Monolith4.WithCopy: 2 inputs (0x48+0x48) → 1 output (72 bytes)."""
    mono_src = bytearray(0x48 + 0x48)
    mono_src[:0x48] = src1[:0x48]
    mono_src[0x48:0x90] = src2[:0x48]

    mono_dst = bytearray(72)
    monolith4.execute(mono_dst, bytes(mono_src))

    dst[:72] = mono_dst


def monolith5_with_copy(dst1: bytearray, dst2: bytearray, src1: bytes, src2: bytes, src3: bytes) -> None:
    """Monolith5.WithCopy: 3 inputs (0x48+0x48+0x48) → 2 outputs (0x18+0x18)."""
    mono_src = bytearray(0x48 * 3)
    mono_src[:0x48] = src1[:0x48]
    mono_src[0x48:0x90] = src2[:0x48]
    mono_src[0x90:0xD8] = src3[:0x48]

    mono_dst = bytearray(48)
    monolith5.execute(mono_dst, bytes(mono_src))

    dst1[:0x18] = mono_dst[:0x18]
    dst2[:0x18] = mono_dst[0x18:0x30]


def monolith6_with_copy(dst1: bytearray, dst2: bytearray, src1: bytes, src2: bytes, src3: bytes) -> None:
    """Monolith6.WithCopy: 3 inputs (0x48+0x48+0x48) → 2 outputs (0x48+0x48)."""
    mono_src = bytearray(0x48 * 3)
    mono_src[:0x48] = src1[:0x48]
    mono_src[0x48:0x90] = src2[:0x48]
    mono_src[0x90:0xD8] = src3[:0x48]

    mono_dst = bytearray(0x90)
    monolith6.execute(mono_dst, bytes(mono_src))

    dst1[:0x48] = mono_dst[:0x48]
    dst2[:0x48] = mono_dst[0x48:0x90]


def monolith7_with_copy(dst1: bytearray, dst2: bytearray, src1: bytes, src2: bytes) -> None:
    """Monolith7.WithCopy: 2 inputs (0x18+0x48) → 2 outputs (0x48+0x48)."""
    mono_src = bytearray(0x18 + 0x48)
    mono_src[:0x18] = src1[:0x18]
    mono_src[0x18 : 0x18 + 0x48] = src2[:0x48]

    mono_dst = bytearray(0x90)
    monolith7.execute(mono_dst, bytes(mono_src))

    dst1[:0x48] = mono_dst[:0x48]
    dst2[:0x48] = mono_dst[0x48:0x90]
