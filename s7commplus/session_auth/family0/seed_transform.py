"""SeedTransform — generates the encrypted seed blob.

Uses Transform7 with random PRNG buffers, then chains
Monolith1.Loop -> Monolith2 (zero check) -> Monolith8 ->
Transform13 -> Monolith11 to produce the final 60-byte output.

Manual port of ``HarpoS7.Family0.Transforms.SeedTransform``.
"""

from __future__ import annotations

import os
import struct

from ._generated import monolith1, monolith2, monolith8, monolith11
from . import transform7, transform13
from ._generated.data import TRANSFORM7_DATA
from .pre_seed_transform import DESTINATION_SIZE as TRANSFORM1_SIZE

DESTINATION_SIZE = 0x3C
PUBLIC_KEY_LENGTH = 0x28


def _monolith1_loop(buf: bytearray) -> None:
    """Monolith1.Loop: execute until result is non-zero."""
    src = bytearray(buf[:0x48])
    result = monolith1.execute(buf, bytes(src))
    while result == 0:
        src[:0x48] = buf[:0x48]
        result = monolith1.execute(buf, bytes(src))


def execute(destination: bytearray, public_key: bytes, transform1: bytes) -> None:
    if len(destination) < DESTINATION_SIZE:
        raise ValueError(f"destination too small ({len(destination)}, need {DESTINATION_SIZE})")
    if len(public_key) < PUBLIC_KEY_LENGTH:
        raise ValueError(f"publicKey too small ({len(public_key)}, need {PUBLIC_KEY_LENGTH})")
    if len(transform1) < TRANSFORM1_SIZE:
        raise ValueError(f"transform1 too small ({len(transform1)}, need {TRANSFORM1_SIZE})")

    prng1 = bytearray(os.urandom(0x14))
    prng2 = bytearray(0x14)
    t7_dst = bytearray(transform7.DESTINATION_SIZE)
    work = bytearray(5 * 4)

    t7_loop = 0
    while t7_loop == 0:
        prng2 = bytearray(os.urandom(0x14))
        transform7.execute(t7_dst, prng1, prng2, TRANSFORM7_DATA[0xD8:])

        _monolith1_loop(t7_dst)
        monolith2.execute(work, bytes(t7_dst))

        t7_loop = 0
        for d in struct.unpack("<5I", work):
            t7_loop |= d

    destination[0x14:0x28] = work[:0x14]
    destination[0x28:0x3C] = prng1[:0x14]

    transform7.execute(t7_dst, prng1, prng2, public_key)
    _monolith1_loop(t7_dst)

    # Monolith8: src=72 bytes (t7_dst), dst=60 bytes
    # We allocate 92 bytes so it can also serve as Monolith11 destination
    m8_buf = bytearray(20 + 72)
    m8v = memoryview(m8_buf)
    monolith8.execute(m8v[20:], bytes(t7_dst))

    # Monolith11: src=120 bytes, dst=20 bytes
    m11_src = bytearray(0x1E * 4)
    m11v = memoryview(m11_src)

    # Transform13 output → m11_src[0x3C:]
    transform13.execute(m11v[0x3C:], bytes(m8_buf[20:]))

    # transform1 data → m11_src[0:0x3C]
    m11_src[:0x3C] = transform1[:0x3C]

    monolith11.execute(m8_buf, bytes(m11_src))

    destination[:0x14] = m8_buf[:0x14]
