"""Transform12 — opcode-driven dispatcher over BigInt arithmetic.

Manual port of ``HarpoS7.Family0.Transforms.Transform12``. Reads a
metadata tape one uint32 at a time. Each entry encodes:

  - bits 30..31 → opcode (00=Mul, 01=Square, 10=Add, ≥11=Sub)
  - bits 22..29 → destination slot index (8 bits, ×24 bytes)
  - bits 11..20 → first source index (10 bits)
  - bits  0..9  → second source index (10 bits)

Source indices < 0x100 reference slots in the working ``context``
buffer. Indices ≥ 0x100 reference rows of the auxiliary
``Transform12Data.BigIntData`` constant table.
"""

from __future__ import annotations

import struct

from . import big_int_transforms as _bigint
from ._generated.data import TRANSFORM12_BIG_INT_DATA, TRANSFORM12_METADATA

CONTEXT_SIZE = 4 * 894  # 3576 bytes

_BIGINT_SLOT_BYTES = 24


def _slot_view(data: bytes | bytearray, index: int) -> bytes:
    """Return the 24-byte big-integer slot at ``index``."""
    start = index * _BIGINT_SLOT_BYTES
    return bytes(data[start : start + _BIGINT_SLOT_BYTES])


def execute(context: bytearray, index: int, count: int) -> None:
    """Run ``count`` opcodes starting from ``metadata[index]``.

    Mutates ``context`` in place.
    """
    if count == 0:
        return
    if len(context) < CONTEXT_SIZE:
        raise ValueError(f"context must be at least {CONTEXT_SIZE} bytes, got {len(context)}")

    metadata_view = TRANSFORM12_METADATA
    aux_data = TRANSFORM12_BIG_INT_DATA

    for i in range(count):
        word_offset = (index + i) * 4
        if word_offset + 4 > len(metadata_view):
            raise ValueError(f"metadata index {index + i} out of range (have {len(metadata_view) // 4} words)")
        meta_word = struct.unpack_from("<I", metadata_view, word_offset)[0]

        dst_slot = (meta_word >> 0x16) & 0xFF
        src1_slot = (meta_word >> 0x0B) & 0x3FF
        src2_slot = meta_word & 0x3FF
        opcode = meta_word >> 0x1E

        dst_offset = dst_slot * _BIGINT_SLOT_BYTES

        # Source slots <0x100 are local; ≥0x100 index into the
        # auxiliary big-int table (offset by 0x100).
        src1_buf = _slot_view(context, src1_slot) if src1_slot < 0x100 else _slot_view(aux_data, src1_slot - 0x100)
        src2_buf = _slot_view(context, src2_slot) if src2_slot < 0x100 else _slot_view(aux_data, src2_slot - 0x100)

        # We need a writable buffer for the output. Use a temporary
        # so we don't alias if dst overlaps src1 or src2.
        result = bytearray(_BIGINT_SLOT_BYTES)
        if opcode == 0:
            _bigint.big_int_multiplication(result, src1_buf, src2_buf)
        elif opcode == 1:
            _bigint.big_int_square(result, src1_buf)
        elif opcode == 2:
            _bigint.big_int_addition(result, src1_buf, src2_buf)
        else:
            _bigint.big_int_subtraction(result, src1_buf, src2_buf)
        context[dst_offset : dst_offset + _BIGINT_SLOT_BYTES] = result
