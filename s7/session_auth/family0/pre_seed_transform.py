"""PreSeedTransform — prepares the random key for seed encryption.

Uses Monolith9 three times with a 192-uint work buffer seeded from
``Transform1Data`` plus a 3-uint magic postfix. Each iteration feeds
two uint32s from the source key into the work buffer, runs Monolith9,
and copies 6 (or 3 for the last iteration) uints of the result to
the destination.

Manual port of ``HarpoS7.Family0.Transforms.PreSeedTransform``.
"""

from __future__ import annotations

import struct

from . import monolith9
from .data import TRANSFORM1_DATA

SOURCE_SIZE = 0x18
DESTINATION_SIZE = 0x3C

_MAGIC_POSTFIX = struct.pack("<III", 0x4F5BB379, 0x90BA725F, 0x36A4D7BB)


def execute(destination: bytearray, source: bytes) -> None:
    if len(destination) < DESTINATION_SIZE:
        raise ValueError(f"destination too small ({len(destination)}, need {DESTINATION_SIZE})")
    if len(source) < SOURCE_SIZE:
        raise ValueError(f"source too small ({len(source)}, need {SOURCE_SIZE})")

    work = bytearray(0xC5 * 4)
    work[: len(TRANSFORM1_DATA)] = TRANSFORM1_DATA

    magic_offset = 0xC2 * 4
    work[magic_offset : magic_offset + 12] = _MAGIC_POSTFIX

    src_dwords = struct.unpack(f"<{SOURCE_SIZE // 4}I", source[:SOURCE_SIZE])

    for i in range(3):
        struct.pack_into("<II", work, 0xC0 * 4, src_dwords[i * 2], src_dwords[i * 2 + 1])

        m9_dst = bytearray(24)  # 6 uints
        monolith9.execute(m9_dst, bytes(work))

        copy_len = 24 if i < 2 else 12  # 6 uints or 3 uints
        destination[i * 24 : i * 24 + copy_len] = m9_dst[:copy_len]
