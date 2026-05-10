"""Transform7 — the core elliptic-curve scalar multiplication.

Orchestrates MonolithWithCopy wrappers (3-7), Transform12 dispatch,
BigIntAddition, BigIntOperations, and a 600-uint work buffer to perform
the equivalent of a point multiplication on the proprietary curve.

Manual port of ``HarpoS7.Family0.Transforms.Transform7``.
"""

from __future__ import annotations

import struct

from . import big_int_operations, transform12
from .big_int_transforms import big_int_addition
from .data import TRANSFORM7_DATA
from .data._constants import TRANSFORM7_COUNTS_INTS, TRANSFORM7_INDEXES_INTS
from .monolith_wrappers import (
    monolith3_with_copy,
    monolith4_with_copy,
    monolith5_with_copy,
    monolith6_with_copy,
    monolith7_with_copy,
)

DESTINATION_SIZE = 72

_WORK_SIZE = 600 * 4


def execute(
    destination: bytearray,
    prng1: bytearray,
    prng2: bytearray,
    source: bytes,
) -> None:
    data = TRANSFORM7_DATA

    prng1_dwords = list(struct.unpack("<5I", bytes(prng1[:20])))
    prng2_dwords = list(struct.unpack("<5I", bytes(prng2[:20])))
    src_dwords = struct.unpack(f"<{len(source) // 4}I", bytes(source[: (len(source) // 4) * 4]))

    w = bytearray(_WORK_SIZE)
    wv = memoryview(w)

    # prng1[0:5] → work dwords [0xC:0x11], then OR 4 into [0xC]
    for i in range(5):
        struct.pack_into("<I", w, (0xC + i) * 4, prng1_dwords[i])
    struct.pack_into("<I", w, 0xC * 4, struct.unpack_from("<I", w, 0xC * 4)[0] | 4)

    # source[0:5] → work dwords [0:5]
    for i in range(5):
        struct.pack_into("<I", w, i * 4, src_dwords[i])

    # source[5:10] → work dwords [0x12:0x17], then OR 4 into [0x12]
    for i in range(5):
        struct.pack_into("<I", w, (0x12 + i) * 4, src_dwords[5 + i])
    struct.pack_into("<I", w, 0x12 * 4, struct.unpack_from("<I", w, 0x12 * 4)[0] | 4)

    # -- Monolith3 chain --
    monolith3_with_copy(wv[0xA8:], wv[0x60:], data, data[0x48:], wv[0x30:])
    monolith3_with_copy(wv[0x2A0:], wv[0x210:], data, data[0x48:], wv[0x48:])
    monolith3_with_copy(wv[0x1C8:], wv[0xF0:], wv[0xA8:], wv[0x60:], wv)
    monolith3_with_copy(wv[0x180:], wv[0x138:], wv[0x1C8:], wv[0xF0:], wv[0x48:])

    monolith4_with_copy(wv[0x4E0:], wv[0x180:], wv[0x138:])

    # -- Transform12 context --
    ctx = bytearray(transform12.CONTEXT_SIZE)
    cv = memoryview(ctx)

    monolith5_with_copy(cv[0x450:], wv[0x18:], wv[0x4E0:], wv[0x180:], wv[0x138:])

    big_int_addition(cv[0x450:], bytes(ctx[0x450 : 0x450 + 24]), bytes(w[0x18 : 0x18 + 24]))

    monolith3_with_copy(wv[0x498:], wv[0x768:], wv[0x180:], wv[0x138:], wv[0x30:])

    monolith4_with_copy(wv[0x648:], data, data[0x48:])
    monolith6_with_copy(wv[0x8D0:], wv[0x888:], wv[0x648:], wv[0xA8:], wv[0x60:])

    monolith4_with_copy(wv[0x570:], wv[0x498:], wv[0x768:])
    monolith6_with_copy(wv[0x330:], wv[0x690:], wv[0x570:], wv[0x2A0:], wv[0x210:])

    monolith4_with_copy(wv[0x840:], wv[0xA8:], wv[0x60:])
    monolith6_with_copy(wv[0x7F8:], wv[0x6D8:], wv[0x840:], wv[0x1C8:], wv[0xF0:])

    monolith4_with_copy(wv[0x5B8:], wv[0x7F8:], wv[0x6D8:])
    monolith6_with_copy(wv[0x3C0:], wv[0x450:], wv[0x5B8:], wv[0x2A0:], wv[0x210:])

    monolith4_with_copy(wv[0x600:], wv[0x3C0:], wv[0x450:])
    monolith5_with_copy(cv[0x690:], wv[0x18:], wv[0x600:], wv[0x3C0:], wv[0x450:])

    big_int_addition(cv[0x690:], bytes(ctx[0x690 : 0x690 + 24]), bytes(w[0x18 : 0x18 + 24]))

    monolith4_with_copy(wv[0x378:], wv[0x330:], wv[0x690:])
    monolith6_with_copy(wv[0x2E8:], wv[0x258:], wv[0x378:], wv[0x3C0:], wv[0x450:])

    monolith4_with_copy(wv[0x408:], wv[0x2E8:], wv[0x258:])
    monolith5_with_copy(cv[0x480:], wv[0x18:], wv[0x408:], wv[0x2E8:], wv[0x258:])

    big_int_addition(cv[0x480:], bytes(ctx[0x480 : 0x480 + 24]), bytes(w[0x18 : 0x18 + 24]))

    # RotateRight30 on first 6 uints of work buffer
    big_int_operations.rotate_right_30(w)

    monolith3_with_copy(wv[0xA8:], wv[0x60:], data, data, wv)
    monolith5_with_copy(cv[0x8D0:], wv[0x18:], data, wv[0xA8:], wv[0x60:])

    big_int_addition(cv[0x8D0:], bytes(ctx[0x8D0 : 0x8D0 + 24]), bytes(w[0x18 : 0x18 + 24]))

    # -- Transform12 dispatch loop 1: i = 0..0x9F (prng2 bits) --
    for i in range(0xA0):
        prng2_index = (0x9F - i) >> 5
        bit_pos = (0xFFFFFFFF - i) & 0x1F
        t12_idx = ((prng2_dwords[prng2_index] >> bit_pos) & 1) + i * 2
        transform12.execute(ctx, TRANSFORM7_INDEXES_INTS[t12_idx], TRANSFORM7_COUNTS_INTS[t12_idx])

    # -- Transform12 dispatch loop 2: i = 0xA0..0xF8 (prng1 bits from work buffer) --
    for i in range(0xA0, 0xF9):
        dword_index = ((i - 0xA0) >> 5) + 0xC
        w_dword = struct.unpack_from("<I", w, dword_index * 4)[0]
        t12_idx = ((w_dword >> (i & 0x1F)) & 1) + i * 2
        transform12.execute(ctx, TRANSFORM7_INDEXES_INTS[t12_idx], TRANSFORM7_COUNTS_INTS[t12_idx])

    # -- PrepareFinalize on four context regions --
    big_int_operations.prepare_finalize(cv[0x918:])
    big_int_operations.prepare_finalize(cv[0x6A8:])
    big_int_operations.prepare_finalize(cv[0x5B8:])
    big_int_operations.prepare_finalize(cv[0x288:])

    # -- Final monolith chain --
    monolith7_with_copy(wv[0x7B0:], wv[0x720:], cv[0x288:], data[0x90:])
    monolith4_with_copy(wv[0x528:], wv[0x7B0:], wv[0x720:])

    monolith7_with_copy(wv[0xA8:], wv[0x60:], cv[0x288:], wv[0x528:])
    monolith4_with_copy(wv[0x2A0:], wv[0xA8:], wv[0x60:])

    monolith7_with_copy(wv[0x210:], wv[0x1C8:], cv[0x5B8:], wv[0x2A0:])
    monolith4_with_copy(wv[0xF0:], wv[0x210:], wv[0x1C8:])

    monolith7_with_copy(wv[0x180:], wv[0x138:], cv[0x918:], wv[0xF0:])
    monolith7_with_copy(wv[0x4E0:], wv[0x498:], cv[0x6A8:], wv[0xF0:])

    monolith4_with_copy(wv[0x330:], wv[0x180:], wv[0x138:])

    monolith6_with_copy(wv[0x2E8:], wv[0x258:], wv[0x330:], wv[0xA8:], wv[0x60:])
    monolith6_with_copy(wv[0x378:], wv[0x408:], wv[0x528:], wv[0x2E8:], wv[0x258:])

    monolith4_with_copy(destination, wv[0x378:], wv[0x408:])
