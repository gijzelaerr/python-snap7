"""BigInt-style operations on 5- and 6-uint arrays.

Ported manually from HarpoS7's
``HarpoS7.Family0.BitOperations.BigIntOperations``. The C# is short
and idiomatic; a manual port is clearer than running it through the
transpiler.

Used by the seed/key-derivation transforms to massage 192-bit
integers in and out of the funky 30-bits-per-limb / 26-bits-per-limb
packing the proprietary curve uses internally.
"""

from __future__ import annotations

import struct

#: Sizes (in bytes) of the various source/destination spans the
#: operations expect. All multiples of ``sizeof(uint) == 4``.
PREPARE_DESTINATION_SIZE = 0x05 * 4
PREPARE_SOURCE_SIZE = 0x06 * 4
FINALIZE_DESTINATION_SIZE = 0x06 * 4
FINALIZE_SOURCE_SIZE = 0x05 * 4

_U32 = 0xFFFFFFFF


def _carry_helper(a: int, b: int) -> int:
    """Return 1 if uint32 ``a`` is less than uint32 ``b``, else 0.

    Used to detect carry-out after an unsigned addition: after
    ``a = (a_orig + b) & _U32``, ``a < b`` indicates the addition
    overflowed past 32 bits.
    """
    return 1 if (a & _U32) < (b & _U32) else 0


def _to_uints(buf: bytes | bytearray, count: int) -> list[int]:
    return list(struct.unpack(f"<{count}I", bytes(buf[: count * 4])))


def _write_uints(buf: bytearray, values: list[int]) -> None:
    struct.pack_into(f"<{len(values)}I", buf, 0, *(v & _U32 for v in values))


def prepare(destination: bytearray, source: bytes) -> None:
    """Prepare 6 source uints into 5 destination uints.

    Reads 24 bytes from ``source`` (six little-endian uint32s) and
    writes 20 bytes to ``destination``.
    """
    if len(destination) < PREPARE_DESTINATION_SIZE:
        raise ValueError(f"destination must be at least {PREPARE_DESTINATION_SIZE} bytes, got {len(destination)}")
    if len(source) < PREPARE_SOURCE_SIZE:
        raise ValueError(f"source must be at least {PREPARE_SOURCE_SIZE} bytes, got {len(source)}")

    src = _to_uints(source, 6)
    dst = _to_uints(destination, 5)

    temp0 = src[0]
    temp1 = ((src[1] << 0x1A) + (temp0 >> 2)) & _U32
    dst[0] = temp1

    temp1 = ((_carry_helper(temp1, temp0) >> 2) + (src[1] >> 6)) & _U32
    temp0 = (src[2] * 0x400000 + temp1) & _U32
    dst[1] = temp0

    temp1 = (_carry_helper(temp0, temp1) + (src[2] >> 10)) & _U32
    temp0 = (src[3] * 0x40000 + temp1) & _U32
    dst[2] = temp0

    temp1 = (_carry_helper(temp0, temp1) + (src[3] >> 0xE)) & _U32
    temp0 = (src[4] * 0x4000 + temp1) & _U32
    dst[3] = temp0

    temp1 = (_carry_helper(temp0, temp1) + (src[4] >> 0x12)) & _U32
    temp0 = (src[5] * 0x400 + temp1) & _U32
    dst[4] = temp0

    temp0 = ((_carry_helper(temp0, temp1) + (src[5] >> 0x16)) * 0x2F) & _U32

    if temp0 != 0:
        dst[0] = (dst[0] + temp0) & _U32
        dst[1] = (dst[1] + _carry_helper(dst[0], temp0)) & _U32

        temp0 = _carry_helper(dst[1], _carry_helper(dst[0], temp0))
        dst[2] = (dst[2] + temp0) & _U32

        temp0 = _carry_helper(dst[2], temp0)
        dst[3] = (dst[3] + temp0) & _U32

        temp0 = _carry_helper(dst[3], temp0)
        dst[4] = (dst[4] + temp0) & _U32

        dst[0] = (dst[0] + _carry_helper(dst[4], temp0) * 0x2F) & _U32

    _write_uints(destination, dst)


def finalize(destination: bytearray, source: bytes) -> None:
    """Finalize 5 source uints into 6 destination uints.

    Reads 20 bytes from ``source`` (five uint32s) and writes 24
    bytes to ``destination``. Inverse of ``prepare``'s packing.
    """
    if len(destination) < FINALIZE_DESTINATION_SIZE:
        raise ValueError(f"destination must be at least {FINALIZE_DESTINATION_SIZE} bytes, got {len(destination)}")
    if len(source) == 0:
        raise ValueError("source must not be empty")

    real = bytearray(FINALIZE_SOURCE_SIZE)
    n = min(len(source), FINALIZE_SOURCE_SIZE)
    real[:n] = source[:n]

    src = _to_uints(real, 5)
    dst = [0] * 6
    dst[0] = ((src[0] & 0x0FFFFFFF) << 2) & _U32
    dst[1] = ((src[1] << 0x06 | src[0] >> 0x1A) & 0x3FFFFFFC) & _U32
    dst[2] = ((src[2] << 0x0A | src[1] >> 0x16) & 0x3FFFFFFC) & _U32
    dst[3] = ((src[2] >> 0x12 | src[3] << 0x0E) & 0x3FFFFFFC) & _U32
    dst[4] = ((src[4] << 0x12 | src[3] >> 0x0E) & 0x3FFFFFFC) & _U32
    dst[5] = (src[4] >> 0x0A & 0x3FFFFC) & _U32

    _write_uints(destination, dst)


def prepare_finalize(buffer: bytearray) -> None:
    """In-place ``Prepare`` followed by ``Finalize`` on the same buffer.

    Reads 6 uints from ``buffer`` and writes 6 uints back, fusing the
    two passes for efficiency. ``buffer`` must be at least 24 bytes.
    """
    if len(buffer) < FINALIZE_DESTINATION_SIZE:
        raise ValueError(f"buffer must be at least {FINALIZE_DESTINATION_SIZE} bytes, got {len(buffer)}")

    ds = _to_uints(buffer, 6)

    temp0 = (ds[1] * 0x4000000 + (ds[0] >> 2)) & _U32
    temp1 = (_carry_helper(temp0, ds[0] >> 2) + (ds[1] >> 6)) & _U32

    temp2 = (ds[2] * 0x400000 + temp1) & _U32
    temp1 = (_carry_helper(temp2, temp1) + (ds[2] >> 10)) & _U32

    temp3 = (ds[3] * 0x40000 + temp1) & _U32
    temp1 = (_carry_helper(temp3, temp1) + (ds[3] >> 0xE)) & _U32

    temp4 = (ds[4] * 0x4000 + temp1) & _U32
    temp1 = (_carry_helper(temp4, temp1) + (ds[4] >> 0x12)) & _U32

    temp5 = (ds[5] * 0x400 + temp1) & _U32
    temp1 = ((_carry_helper(temp5, temp1) + (ds[5] >> 0x16)) * 0x2F) & _U32

    if temp1 != 0:
        temp6 = _carry_helper((temp0 + temp1) & _U32, temp1)

        temp2 = (temp2 + temp6) & _U32
        temp6 = _carry_helper(temp2, temp6)

        temp3 = (temp3 + temp6) & _U32
        temp6 = _carry_helper(temp3, temp6)

        temp4 = (temp4 + temp6) & _U32
        temp6 = _carry_helper(temp4, temp6)

        temp5 = (temp5 + temp6) & _U32
        temp0 = (temp0 + temp1 + _carry_helper(temp5, temp6) * 0x2F) & _U32

    out = [0] * 6
    out[0] = ((temp0 & 0xFFFFFFF) << 2) & _U32
    out[1] = ((temp2 << 6 | temp0 >> 0x1A) & 0x3FFFFFFC) & _U32
    out[2] = ((temp3 << 10 | temp2 >> 0x16) & 0x3FFFFFFC) & _U32
    out[3] = ((temp4 << 0xE | temp3 >> 0x12) & 0x3FFFFFFC) & _U32
    out[4] = ((temp5 << 0x12 | temp4 >> 0xE) & 0x3FFFFFFC) & _U32
    out[5] = (temp5 >> 10 & 0x3FFFFC) & _U32

    _write_uints(buffer, out)


def rotate_right_30(buffer: bytearray) -> None:
    """Rotate the 6-uint buffer right by 30 bits."""
    ds = _to_uints(buffer, 6)
    ds[5] = (ds[4] >> 0x1E) & _U32
    for i in range(4, 0, -1):
        ds[i] = ((ds[i - 1] >> 0x1E) | ((ds[i] << 2) & _U32)) & _U32
    ds[0] = (ds[0] << 2) & _U32
    _write_uints(buffer, ds)


def rotate_left_31(buffer: bytearray) -> None:
    """Rotate the leading 4 uints left by 31 bits with a custom
    polynomial reduction on overflow."""
    ds = _to_uints(buffer, 4)
    first = ds[0]
    for i in range(3):
        ds[i] = (((ds[i + 1] << 0x1F) & _U32) | (ds[i] >> 1)) & _U32
    overflow_mask = 0xE1000000 if (first & 1) else 0
    ds[3] = ((ds[3] >> 1) ^ overflow_mask) & _U32
    _write_uints(buffer, ds)
