"""HarpoHash — the proprietary 128-bit transform underpinning HarpoAesCtr.

Despite the name, this is **not** a cryptographic hash. It's a custom
pseudo-AES round function Siemens layered on top of standard AES-ECB
in ``OMSp_core_managed.dll``. Its purpose is twofold: produce the
ciphertext for the encrypted random seed in the SessionKey blob, and
chain into the integrity-MAC computation that ``HarpoAesCtr`` builds
on top.

Three primitives:

- ``lut1`` — one round of the transform. Updates a 16-byte state
  using a 512-byte fixed table (``LUT_SEED``).
- ``generate_lookup_table`` — derives a 4 KB working table from a
  16-byte key. Calls ``lut1`` six times, then xors-and-replicates the
  resulting state across the rest of the table.
- ``hash_block`` — runs the working table over a 16-byte input,
  producing a 16-byte output. Equivalent to ``HarpoHash.Hash``.

Ported from HarpoS7 (MIT) — ``HarpoS7.Aes.HarpoHash`` and
``HarpoS7.Aes.AesConsts``. The 512-byte ``LUT_SEED`` constant doubles
as the ``HarpoHashSeed`` ushort table by reinterpreting bytes as
little-endian uint16 pairs.
"""

from __future__ import annotations

import struct

#: 32-bit unsigned mask. Python ints don't wrap, so every shift-left
#: result is masked back into uint32 range.
_U32 = 0xFFFFFFFF

#: 512 bytes of constant table material, vendored verbatim from
#: ``HarpoS7.Aes.AesConsts.LutSeed`` (which is byte-identical to
#: ``HarpoHashSeed`` — the upstream library stores it twice for
#: ergonomic access as both ``byte[]`` and ``ushort[]``).
LUT_SEED = bytes.fromhex(
    "000001C203840246070806CA048C054E"
    "0E100FD20D940C56091808DA0A9C0B5E"
    "1C201DE21FA41E661B281AEA18AC196E"
    "123013F211B41076153814FA16BC177E"
    "384039823BC43A063F483E8A3CCC3D0E"
    "3650379235D434163158309A32DC331E"
    "246025A227E42626236822AA20EC212E"
    "2A702BB229F428362D782CBA2EFC2F3E"
    "70807142730472C67788764A740C75CE"
    "7E907F527D147CD67998785A7A1C7BDE"
    "6CA06D626F246EE66BA86A6A682C69EE"
    "62B06372613460F665B8647A663C67FE"
    "48C049024B444A864FC84E0A4C4C4D8E"
    "46D047124554449641D8401A425C439E"
    "54E05522576456A653E8522A506C51AE"
    "5AF05B32597458B65DF85C3A5E7C5FBE"
    "E100E0C2E284E346E608E7CAE58CE44E"
    "EF10EED2EC94ED56E818E9DAEB9CEA5E"
    "FD20FCE2FEA4FF66FA28FBEAF9ACF86E"
    "F330F2F2F0B4F176F438F5FAF7BCF67E"
    "D940D882DAC4DB06DE48DF8ADDCCDC0E"
    "D750D692D4D4D516D058D19AD3DCD21E"
    "C560C4A2C6E4C726C268C3AAC1ECC02E"
    "CB70CAB2C8F4C936CC78CDBACFFCCE3E"
    "91809042920493C69688974A950C94CE"
    "9F909E529C149DD69898995A9B1C9ADE"
    "8DA08C628E248FE68AA88B6A892C88EE"
    "83B08272803481F684B8857A873C86FE"
    "A9C0A802AA44AB86AEC8AF0AAD4CAC8E"
    "A7D0A612A454A596A0D8A11AA35CA29E"
    "B5E0B422B664B7A6B2E8B32AB16CB0AE"
    "BBF0BA32B874B9B6BCF8BD3ABF7CBEBE"
)
assert len(LUT_SEED) == 512


def _lut1_inplace(state: list[int], dst_off: int, src_off: int) -> None:
    """One ``Lut1`` step on a uint32-list state buffer.

    Reads four uints starting at ``src_off`` and writes four uints
    starting at ``dst_off``. Writes happen after all reads, so
    in-place use (``src_off == dst_off``) and overlapping ranges are
    safe.
    """
    a1 = state[src_off : src_off + 4]

    t1_initial = a1[3]
    seed_index = ((t1_initial >> 0x11) & 0x80808080) * 2 & _U32
    t2 = struct.unpack_from("<H", LUT_SEED, seed_index)[0]

    out = [0, 0, 0, 0]
    # Mirror the C# closure: each iteration captures whichever t1 was
    # most recently assigned. The order of `output[3], output[2],
    # output[1]` is deliberate — see HarpoS7 KeyExtensions.
    for slot, val_idx, t1_idx in [(3, 2, 3), (2, 1, 2), (1, 0, 1)]:
        t1 = a1[t1_idx]
        val = a1[val_idx]
        shifted = (val >> 0x11) | ((t1 << 0xF) & _U32)
        out[slot] = ((shifted ^ (t1 >> 1)) & 0x7F7F7F7F ^ shifted) & _U32

    t1 = a1[0]
    out[0] = ((((t1 << 0xF) & _U32) ^ (t1 >> 1)) & 0x7F7F7F7F ^ ((t1 << 0xF) & _U32) ^ t2) & _U32

    state[dst_off : dst_off + 4] = out


def lut1(state: bytes) -> bytes:
    """Compute one round of the proprietary transform on 16 bytes.

    Args:
        state: 16-byte input.

    Returns:
        16-byte output (one ``Lut1`` step's result).

    Raises:
        ValueError: If ``state`` is not exactly 16 bytes.
    """
    if len(state) != 16:
        raise ValueError(f"state must be 16 bytes, got {len(state)}")
    uints = list(struct.unpack("<IIII", state)) + [0, 0, 0, 0]
    _lut1_inplace(uints, dst_off=4, src_off=0)
    return struct.pack("<IIII", *uints[4:8])


def generate_lookup_table(key: bytes) -> bytes:
    """Derive the 4 KB working table from a 16-byte seed key.

    The result is fed into ``hash_block`` and into ``HarpoAesCtr``'s
    integrity accumulator. Output is 4096 bytes — a 1024-element
    little-endian uint32 array.

    Args:
        key: 16-byte input seed.

    Returns:
        4096 bytes — the working table.

    Raises:
        ValueError: If ``key`` is not exactly 16 bytes.
    """
    if len(key) != 16:
        raise ValueError(f"key must be 16 bytes, got {len(key)}")

    state: list[int] = [0] * 1024  # 4 KB / 4
    state[0x200 : 0x200 + 4] = list(struct.unpack("<IIII", key))

    # First loop: index = 64, 32, 16, 8, 4, 2, 1.
    # Lut1 reduces from offset (index*8) into offset (index*4), so the
    # 16-byte key at uint-index 0x200 cascades back through the table
    # to fill uints 4..8.
    index = 0x40
    while index != 0:
        _lut1_inplace(state, dst_off=index * 4, src_off=index * 8)
        index >>= 1

    # Second loop: index = 2, 4, 8, ..., 128.
    # XORs uint-aligned regions of the table with the 16-byte block at
    # uint indices 4..8 to fill out the rest of the table.
    index = 2
    while index < 0x100:
        if index > 1:
            j = index << 4  # bytes
            k = index - 1
            dest1 = (0x18 + j) // 4  # uint indices
            dest2 = 0x18 // 4
            src = j // 4

            for _ in range(k):
                state[dest1 - 2] = state[dest2 - 2] ^ state[src]
                state[dest1 - 1] = state[dest2 - 1] ^ state[src + 1]
                state[dest1] = state[dest2] ^ state[src + 2]
                state[dest1 + 1] = state[dest2 + 1] ^ state[src + 3]
                dest1 += 4
                dest2 += 4
        index *= 2

    return b"".join(struct.pack("<I", u) for u in state)


def hash_block(data: bytes, lut: bytes) -> bytes:
    """Run the working table over a 16-byte input.

    This is the inner per-block primitive used by ``HarpoAesCtr`` for
    its integrity-MAC computation. Treats the 4 KB ``lut`` as a
    1024-element little-endian uint32 array.

    Args:
        data: 16-byte input.
        lut: 4096-byte working table from ``generate_lookup_table``.

    Returns:
        16-byte output.

    Raises:
        ValueError: If buffer lengths are wrong.
    """
    if len(data) != 16:
        raise ValueError(f"data must be 16 bytes, got {len(data)}")
    if len(lut) != 4096:
        raise ValueError(f"lut must be 4096 bytes, got {len(lut)}")

    lut_uints = struct.unpack(f"<{len(lut) // 4}I", lut)

    t1 = t2 = t3 = t4 = 0
    for i in range(15, -1, -1):
        v1 = t3 >> 0x18
        v2 = t2 >> 0x18
        v3 = t1 >> 0x18
        v4 = data[i]
        t5 = v4 * 4

        # HarpoHashSeed is the same bytes as LUT_SEED, accessed as
        # an array of 256 little-endian ushorts.
        seed_val = struct.unpack_from("<H", LUT_SEED, (t4 >> 0x18) * 2)[0]

        t1 = (((t1 << 8) & _U32) ^ seed_val ^ lut_uints[t5]) & _U32
        t2 = ((((t2 << 8) & _U32) | v3) ^ lut_uints[t5 + 1]) & _U32
        t3 = ((((t3 << 8) & _U32) | v2) ^ lut_uints[t5 + 2]) & _U32
        t4 = ((((t4 << 8) & _U32) | v1) ^ lut_uints[t5 + 3]) & _U32

    return struct.pack("<IIII", t1, t2, t3, t4)
