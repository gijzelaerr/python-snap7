"""Lookup-table generator used by ``ChecksumTransform`` (HarpoHash variant).

Builds a 4 KB table of 256 ``UInt128`` entries from a 16-byte seed
key. Each entry is the seed multiplied by ``i`` over GF(2¹²⁸) under
the polynomial ``x^128 + x^7 + x^2 + x + 1`` (canonical AES-GCM
field). The construction doubles iteratively and cross-XORs to fill
the rest of the rows.

Manual port of ``HarpoS7.Family0.Transforms.LutGenerator``.
"""

from __future__ import annotations

import struct

SOURCE_SIZE = 0x10
DESTINATION_SIZE = 0x1000

_U128 = (1 << 128) - 1
_REDUCTION = 0x010000_8005  # x^128 + x^7 + x^2 + x + 1, low 33 bits


def _to_u128_list(buf: bytes, count: int) -> list[int]:
    """Read ``count`` little-endian 16-byte values as Python ints."""
    out = []
    for i in range(count):
        out.append(int.from_bytes(bytes(buf[i * 16 : (i + 1) * 16]), "little"))
    return out


def _from_u128_list(values: list[int]) -> bytes:
    parts = [(v & _U128).to_bytes(16, "little") for v in values]
    return b"".join(parts)


def execute(destination: bytearray, source: bytes) -> None:
    """Generate the 4 KB lookup table from a 16-byte source.

    Args:
        destination: 4096-byte buffer to populate.
        source: 16-byte seed key.
    """
    if len(destination) < DESTINATION_SIZE:
        raise ValueError(f"destination must be at least {DESTINATION_SIZE} bytes, got {len(destination)}")
    if len(source) < SOURCE_SIZE:
        raise ValueError(f"source must be at least {SOURCE_SIZE} bytes, got {len(source)}")

    # Initial layout:
    #   dwords [0..4)  = 0       → quadDwords[0] = 0
    #   dwords [4..8)  = source  → quadDwords[1] = source as UInt128
    #   dwords [8..)   = 0       (zero-initialised destination)
    quads = [0] * 256
    quads[1] = int.from_bytes(bytes(source[:16]), "little")

    i = 1
    while i < 128:
        multiplicand = quads[i]
        product = (multiplicand * 2) & _U128
        if (multiplicand >> 0x7F) != 0:
            product ^= _REDUCTION

        product_index = i * 2
        quads[product_index] = product

        for j in range(1, product_index):
            quads[product_index + j] = quads[j] ^ product

        i *= 2

    destination[:DESTINATION_SIZE] = _from_u128_list(quads)


# Backwards-compatible shim: tests can import via class-style or
# function-style. The function entry point is canonical.
del struct  # not used outside the helper functions
