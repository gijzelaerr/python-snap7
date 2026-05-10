"""HarpoFingerprint — challenge fingerprinting for session key derivation.

Produces an 8-byte fingerprint from a PLC challenge. Used by
DeriveSessionKey to build the HMAC-SHA256 input that yields the
24-byte session key.

Manual port of ``HarpoS7.Fingerprint.HarpoFingerprint`` +
``HarpoS7.Fingerprint.ContextMutator``.
"""

from __future__ import annotations

import struct

from .data import (
    FP_BIG_CONTEXT_INIT,
    FP_DATA1,
    FP_DATA2,
    FP_MUTATIONS,
    FP_XOR_MAGIC,
)

FINGERPRINT_LENGTH = 8
_SMALL_CTX_LEN = 272
_BIG_CTX_LEN_DWORDS = 47
_NUM_MUTATIONS = 20
_U32 = 0xFFFFFFFF


def _load_big_context_init() -> list[int]:
    return list(struct.unpack("<47I", FP_BIG_CONTEXT_INIT))


def _load_xor_magic() -> list[int]:
    return list(struct.unpack("<20I", FP_XOR_MAGIC))


def _load_collection(data: bytes) -> list[list[int]]:
    lengths = list(struct.unpack("<20I", data[:80]))
    offset = 80
    result = []
    for length in lengths:
        values = list(struct.unpack(f"<{length}H", data[offset:offset + length * 2]))
        result.append(values)
        offset += length * 2
    return result


def _load_mutations() -> list[list[tuple[int, int, int]]]:
    result = []
    offset = 0
    for _ in range(_NUM_MUTATIONS):
        n_ops = struct.unpack_from("<I", FP_MUTATIONS, offset)[0]
        offset += 4
        ops = []
        for _ in range(n_ops):
            idx, op, _pad, val = struct.unpack_from("<BBH I", FP_MUTATIONS, offset)
            ops.append((idx, op, val))
            offset += 8
        result.append(ops)
    return result


_BIG_CTX_INIT = _load_big_context_init()
_XOR_MAGIC = _load_xor_magic()
_DATA1 = _load_collection(FP_DATA1)
_DATA2 = _load_collection(FP_DATA2)
_MUTATIONS = _load_mutations()


def fingerprint_challenge(destination: bytearray, challenge: bytes) -> None:
    if len(destination) < FINGERPRINT_LENGTH:
        raise ValueError("destination must be at least 8 bytes")
    if len(challenge) < 18:
        raise ValueError("challenge must be at least 18 bytes")

    small_ctx = bytearray(_SMALL_CTX_LEN)
    big_ctx = list(_BIG_CTX_INIT)

    # Initialize: copy challenge[2:18] into small context
    small_ctx[:16] = challenge[2:18]

    for i in range(_NUM_MUTATIONS):
        _sub_procedure(_DATA1[i], _XOR_MAGIC[i], _DATA2[i], small_ctx, big_ctx)
        _mutate(big_ctx, i)

    _final_fingerprint(destination, small_ctx)


def _pwvar_mask(value: int) -> int:
    return (((value & 1) * -4) + 4) & 0x1F


def _pwvar_read(value: int, small_ctx: bytearray) -> int:
    return (small_ctx[value >> 1] >> _pwvar_mask(value & 0xFF)) & 0xFF


def _sub_procedure(
    data1: list[int],
    xor_magic: int,
    data2: list[int],
    small_ctx: bytearray,
    big_ctx: list[int],
) -> None:
    data2_bytes = struct.pack(f"<{len(data2)}H", *data2)

    index = 0
    ctx_offset = 0

    while index < len(data1):
        pw_var0 = _pwvar_read(data1[index], small_ctx)
        index += 1
        pw_var1 = _pwvar_read(data1[index], small_ctx)
        index += 1
        pw_var2 = data1[index]
        index += 1

        static3 = ((pw_var1 & 0xF) | (pw_var0 << 4)) & 0xFF

        t1 = (static3 >> 3) + (ctx_offset >> 2)
        mod = int(t1) % 0x2F
        t3 = big_ctx[mod]
        static6 = (t3 ^ xor_magic) & _U32

        t4 = ((0x7 - (pw_var1 & 0x7)) * 0x04) & 0x1F
        static5 = (static6 >> t4) & 0xFF

        b_var3 = (((pw_var2 & 0xFF) & 1) * (-4) + 4) & 0xFF
        ctx_buffer_index = pw_var2 >> 1

        t5 = b_var3 & 0x1F
        data2_index = ((static3 >> 1) + ctx_offset) & 0xFFFFFFFF

        if data2_index < len(data2_bytes):
            data2_byte = data2_bytes[data2_index]
        else:
            data2_byte = 0

        f_val = (
            (((data2_byte >> _pwvar_mask(pw_var1 & 0xFF)) ^ static5) & 0xF) << t5
            | ((0xF0 >> t5) & small_ctx[ctx_buffer_index])
        ) & 0xFF

        small_ctx[ctx_buffer_index] = f_val

        ctx_offset += 0x80


def _mutate(big_ctx: list[int], mutation_index: int) -> None:
    for idx, op, val in _MUTATIONS[mutation_index]:
        if op == 0:  # +=
            big_ctx[idx] = (big_ctx[idx] + val) & _U32
        elif op == 1:  # *=
            big_ctx[idx] = (big_ctx[idx] * val) & _U32
        elif op == 2:  # ^=
            big_ctx[idx] = (big_ctx[idx] ^ val) & _U32


def _final_fingerprint(fp: bytearray, sc: bytearray) -> None:
    fp[0] = ((sc[93] << 4) | (sc[224] >> 4)) & 0xFF
    fp[1] = ((((fp[1] ^ sc[189]) & 0xF ^ sc[189]) ^ sc[53]) & 0xF
             ^ ((fp[1] ^ sc[189]) & 0xF ^ sc[189])) & 0xFF
    fp[2] = (((fp[2] & 0xF | sc[119] << 4) ^ sc[86]) & 0xF
             ^ (fp[2] & 0xF | sc[119] << 4)) & 0xFF
    fp[3] = (((fp[3] ^ sc[83]) & 0xF ^ sc[83]) & 0xF0
             | (sc[33] >> 4)) & 0xFF
    fp[4] = ((((fp[4] ^ sc[229]) & 0xF ^ sc[229]) ^ sc[58]) & 0xF
             ^ ((fp[4] ^ sc[229]) & 0xF ^ sc[229])) & 0xFF
    fp[5] = ((((fp[5] ^ sc[69]) & 0xF ^ sc[69]) ^ sc[165]) & 0xF
             ^ ((fp[5] ^ sc[69]) & 0xF ^ sc[69])) & 0xFF
    fp[6] = (((fp[6] ^ sc[63]) & 0xF ^ sc[63]) & 0xF0
             | (sc[89] >> 4)) & 0xFF
    fp[7] = ((((fp[7] ^ sc[172]) & 0xF ^ sc[172]) ^ sc[247]) & 0xF
             ^ ((fp[7] ^ sc[172]) & 0xF ^ sc[172])) & 0xFF
