"""Transform13 — produces three 24-byte big-int segments from a source.

Calls Monolith10 with a static mask + source, then iterates Monolith9
three times (indices 6..8 of SharedData) to produce the output.

Manual port of ``HarpoS7.Family0.Transforms.Transform13``.
"""

from __future__ import annotations

import struct

from ._generated import monolith9, monolith10
from ._generated.data import SHARED_DATA

DESTINATION_SIZE = 0x3C
SOURCE_SIZE = 0x3C

_STATIC_MASK = bytes.fromhex("FFFFFFFFFFFFFFFFFFFFFFFF00000000")[:12]


def execute(destination: bytearray, source: bytes) -> None:
    if len(destination) < DESTINATION_SIZE:
        raise ValueError("destination too small")
    if len(source) < SOURCE_SIZE:
        raise ValueError("source too small")

    shared = struct.unpack("<36I", SHARED_DATA)

    m10_mask = bytearray(len(_STATIC_MASK) + SOURCE_SIZE)
    m10_mask[: len(_STATIC_MASK)] = _STATIC_MASK
    m10_mask[len(_STATIC_MASK) : len(_STATIC_MASK) + SOURCE_SIZE] = source[:SOURCE_SIZE]

    m10_dst = bytearray(0xC0 * 4 + 5 * 4)
    monolith10.execute(m10_dst, bytes(m10_mask))

    m9_dst = bytearray(24)

    for i in range(6, 9):
        struct.pack_into("<II", m10_dst, 0xC0 * 4, shared[i * 2], shared[i * 2 + 1])
        struct.pack_into("<III", m10_dst, 0xC2 * 4, 0x4F5BB379, 0x90BA725F, 0x36A4D7BB)

        monolith9.execute(m9_dst, bytes(m10_dst))

        dst_index = 0x18 * (i - 6)
        copy_len = 0x18 if i < 8 else 0x0C
        destination[dst_index : dst_index + copy_len] = m9_dst[:copy_len]

        if i == 7:
            m10_mask[: len(_STATIC_MASK)] = b"\x00" * len(_STATIC_MASK)
            monolith10.execute(m10_dst, bytes(m10_mask))
